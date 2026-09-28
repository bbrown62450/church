# Slice 2a — Readings Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 2a of slice 2, the readings backend, with no user-visible page yet. The new app gains `GET /lectionary/readings?date=YYYY-MM-DD` (the reading sets for exactly that date, from lectio-api.org and Vanderbilt fetched in parallel, merged, cached and named per owner decision A), `POST /scripture/passages` (passage text by planned sections and parts with per-part statuses, a 7-day part cache, process-wide upstream budgets and a 20 s deadline), `GET /translations`, and the `GET /church` profile fields (`timezone`, `timezone_valid`, `bible_translation`, `effective_translation`, `effective_translation_label`). Underneath: one outbound HTTP client, a TTL cache, a token-bucket rate limiter (every F §1.8 bucket; `church_create` is wired on `POST /churches` now), `scripture_refs.py` with a shared Python/TypeScript fixture for 2b, and the recorded upstream fixtures. The old dict-cached lectionary lookup is deleted. There is no migration (head stays `0004_invites_reusable`), the frontend changes only through the regenerated `openapi.json` and `schema.d.ts`, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** Below the API, and importing no FastAPI, Starlette or Streamlit: `integrations/http.py` (the one `httpx.Client`: User-Agent, https-only hook on every hop, per-call read timeout, `httpx`/`httpcore` loggers at WARNING), `integrations/budget.py` (process-wide `bible_api` and `esv` budgets), `cache.py` (`TTLCache` with ok/failure TTLs, LRU and single-flight; only `CacheableFailure` is cached as a failure), `token_bucket.py`, `scripture_refs.py` (books, classifier, pickers, `resolve_readings`, fetch normalization), `vanderbilt_lectionary.py` (dates, names, parsing, the draft-limit guard, merge, fetchers and loaders), `scripture_fetcher.py` (plans, parts, statuses, part cache), and the usecases `usecases/lectionary.py` (two cached sources on a 4-worker pool with a 20 s source deadline, status rules, one `lectionary_lookup` log line), `usecases/passages.py` (validation, planning, a shared 4-worker pool with a 20 s deadline, `translation_options`, the `get_passage_text` re-export) and `usecases/church_profile.py`. `api/ratelimit.py` holds the per-user and per-church buckets, `consume` and the `rate_limit(name)` dependency. Each new route is a plain `def` that parses, guards and calls one usecase; `/scripture/passages` alone plans, then `consume`s its cost, then loads. Tests replay the recorded fixtures through respx or `httpx.MockTransport`; the no-network guard stays on.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141.1, Pydantic 2.13.5, httpx 0.28.1, respx ≥ 0.22 (new dev dependency, owner Q1a), SQLAlchemy 2.1.1, Alembic (no new revision), tzdata, pytest (SQLite locally; `postgres:17` in CI, `-m postgres`); Next 16 / openapi-typescript 7 for the regenerated types only; GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Railway, Vercel, Supabase Postgres.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md` (the 2a parts: Scope "Platform", New and changed modules, Lectionary domain, Passages, API, Schemas, Status rules, Rate-limit buckets, Upstream budgets, Testing, AC1–AC9, AC13).
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`.
- Slice 1b plan ("P1b"): `docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md` (conventions; 1b minors are cited as 1b T<n>-m<k>). Slice 1a plan: `docs/superpowers/plans/2026-09-26-slice-1a-platform.md`.
- Production facts: `docs/ops-runbook.md`.
- Facts checked for this plan (tree `55f1b11`, slices 1a and 1b merged and live):
  - Backend baseline `798 passed, 9 skipped`, frontend `221 passed` in 34 files, Alembic head `0004_invites_reusable`, 4 runbook owner markers, httpx 0.28.1, respx not installed.
  - Every task's code was run by its writer in a throwaway worktree at `55f1b11`, with stand-ins built to the earlier tasks' interfaces where those were not yet written, and synthetic fixtures in place of the recordings. Not run while planning: the fixture recording (network; T1 Step 8), respx itself (T7 ran against a MockTransport stand-in), the pushes and CI (T14), and the OWNER steps (T15).
  - Where the code and the outline disagreed, the code won; each case is stated in its task (the "T<n>-k" notes at the top of each task).

## Global Constraints

"T<n>" below means Task n of this plan. "NB", "ND" and "NC" are the planning notes on the backend, the domain and carried-over items; their findings are folded into the clarifications.

### Commands and process
- Use `.venv/bin/python` (3.11) from the repo root. The working directory resets between commands. Run the frontend as `(cd frontend && …)`. No foreground `sleep`.
- Run one test file with `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`.
- Run the whole suite with `.venv/bin/python -m pytest -q | tail -1`.
- After any route or schema change, regenerate the OpenAPI files and commit both with the route:
  `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)`
  Then run `(cd frontend && npm run typecheck)`. Run `(cd frontend && npm test && npm run typecheck && npm run lint)` in T14.
- Branch: `claude/slice-2-plan` from `55f1b11`. The first commit is the plan, at `docs/superpowers/plans/2026-09-28-slice-2a-backend.md`.
- Stage files by name. `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Before merging, merge `origin/main` and rerun both suites. Run `gh pr merge <N> --merge -R bbrown62450/church` only on the owner's explicit yes.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commit subjects read "Area: plain words (F §x, S …)". Use TDD: write the failing test first and quote its failure.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. It includes the line "Tests: backend 798 → N passed, 9 → 9 skipped; frontend 221 → 221 in 34 files".

### Baselines and counts
- Starting baselines: backend **798 passed, 9 skipped**; frontend **221 passed in 34 files**; Alembic head **`0004_invites_reusable`** (2a adds no revision); owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any baseline differs, stop and ask.
- Planned cumulative backend counts, all with 9 skipped. These are the exact numbers the tasks as written produce (each task's new `def test_` count was recounted at assembly). If a count drifts, stop and find why.

  | After | Delta | Count |
  |---|---|---|
  | T1 | +2 | 800 |
  | T2 | +16 | 816 |
  | T3 | +21 | 837 |
  | T4 | +4 | 841 |
  | T5 | +15 | 856 |
  | T6a | +10 | 866 |
  | T6b | +18 | 884 |
  | T7 | +28 | 912 |
  | T8 | +9 | 921 |
  | T9 | +22 − 5 (the deleted `test_scripture_translations.py`) | 938 |
  | T10 | +22 | 960 |
  | T11 | +11 | 971 |
  | T12 | 0 | 971 |

  Each delta equals the number of tests the task lists.

- The frontend stays at 221/34 throughout.
- At the end, CI `backend-postgres` shows `9 passed, 971 deselected, 1 warning`.
- Fixture-driven tests loop over their cases inside one test function (no parametrize). That keeps the counts stable when 5a adds cases.

### Layering and logging
- These modules import no fastapi, starlette or streamlit: `usecases/*`, `scripture_refs.py`, `vanderbilt_lectionary.py`, `scripture_fetcher.py`, `cache.py`, `token_bucket.py`, `integrations/*`. `api/ratelimit.py` may import fastapi.
- Routes are plain `def`. They parse, guard and call one usecase, with no try/except for domain errors. `/scripture/passages` is the exception S and F §1.8 sanction: plan, then consume, then load.
- Logs never contain payloads, bodies, tokens or query strings. Root logging runs at INFO (`api/logging_config.py:41`) and httpx 0.28 logs every request's full URL, query string included, at INFO, so `integrations/http.py` sets the `httpx` and `httpcore` loggers to WARNING at import (clarification 32).

### Messages (verbatim)
- Lectionary 502/504: "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."
- Date out of range (`fields.date`): "Enter a date between 1900 and 2199."
- Pydantic `fields` messages:
  - "Not a valid value." (bad date format, more than 4 refs, an extra key)
  - "Required." (missing `date`)
  - "Too long (max 200 characters)." (`fields["refs.0"]`)
  - "Too long (max 20 characters)." (`fields.translation`)
- Scripture requests:
  - "Enter a scripture reference." (`fields.refs`)
  - "Too many passages in one request." (`fields.refs`)
  - "Unknown or unavailable translation." (`fields.translation`)
- Limiter: "Too many requests. Try again in {n} seconds." The copy is F's and is kept even when n = 1.
- The slice 1 cap message is unchanged: "You've created 5 churches in the last 24 hours. Try again later."
- A church deleted after the guard gets the same 403 as `require_church`: `forbidden`, "You don't have access to this church.", `details: {"reason": "no_church_access"}` (clarification 8).

### Codes and documented statuses
- 2a adds no error code. `upstream_error` (502), `upstream_timeout` (504), `rate_limited` (429) and `invalid_request` (422) already exist.
- `error_responses` per route:

  | Route | Statuses |
  |---|---|
  | `GET /lectionary/readings` | 401, 422, 429, 502, 503, 504 |
  | `GET /translations` | 401, 422, 503 |
  | `POST /scripture/passages` | 401, 422, 429, 503 |
  | `GET /church` | unchanged: 401, 403, 422, 503 |
  | `POST /churches` | unchanged: 401, 422, 429, 503 |

### Buckets, budgets and caches
- Buckets, all per user (capacity / window):
  - `lectionary`: 120 / 300 s
  - `scripture`: 60 / 300 s, charged per part
  - `church_create`: 3 / 60 s
  - `ai`: 40 / 600 s per user **and** 400 / 86 400 s per church
  - `email`: 10 / 3 600 s
- Refill is continuous. For example, `church_create` returns one token every 20 s, so a 4th create at t=0 waits 20 s.
- Upstream budgets (process-wide):
  - `bible_api`: 15 / 30 s
  - `esv`: 60 / 60 s **and** 1 000 / 3 600 s **and** 5 000 / 86 400 s
- Caches:

  | Cache | Key | maxsize | ttl_ok | ttl_fail |
  |---|---|---|---|---|
  | `_LECTIO` | a `date` | 512 | 86 400 s | 300 s |
  | `_VANDERBILT` | a year string such as `"2025-26"` | 8 | 86 400 s | 300 s |
  | bible-api parts | `(translation, normalized part)` | 2 000 | 604 800 s | 0 (transient failures never cached; `NOT_FOUND` cached as a value) |

- ESV is never cached.

### Timeouts and HTTP
- Client default: `httpx.Timeout(10.0, connect=5.0)`, `follow_redirects=True`, User-Agent `WorshipServiceBuilder/1.0`, https only (including redirect hops).
- Read timeouts: Lectio 10 s, Vanderbilt 15 s, bible-api part 10 s, ESV part 10 s.
- Passages: 20 s deadline per request, injectable (`load_passages(plan, deadline=…)`).
- Lectionary: a 20 s deadline on the two source futures (`usecases.lectionary.DEADLINE_SECONDS`, monkeypatched in tests). A source unfinished at the deadline is `SourceFailed(timeout=True)` for this request and is not cached (clarification 31).
- Thread pools: `ThreadPoolExecutor(max_workers=4)` in each of `usecases/lectionary.py` and `usecases/passages.py`.
- URLs are kept from the code: `LECTIO_API_URL`, `VANDERBILT_YEAR_URL`, `BIBLE_API_BASE`, `ESV_API_BASE`. ESV params stay as at `scripture_fetcher.py:91-98`, with `q=` the normalized part.

### Limits
- A reading set has 1–20 lines, each 1–200 characters, and a name of 1–300 characters (the Occasion field's limit, S :142; clarification 34).
- `PassagesIn`:
  - `refs`: at most 4 items, each at most 200 characters;
  - `translation`: at most 20 characters;
  - at most 20 parts per request;
  - `extra="forbid"`.
- Dates must fall between 1900 and 2199.

### Occasion names (owner decision A)
- Named days win over the computed ordinal:
  - Trinity Sunday;
  - All Saints Day (Nov 1 on a Sunday);
  - Reign of Christ (the Sunday before Advent 1);
  - Baptism of the Lord;
  - Transfiguration Sunday.

  Advent and Lent are checked before the Pentecost computation.
- After Pentecost: "{Ordinal} Sunday after Pentecost", where Ordinal = n and n = (d − (easter + 49)) // 7. n = 0 is "Day of Pentecost".
- After the Epiphany: "{Ordinal} Sunday after the Epiphany", where Ordinal = n + 1 and n = 0 is the Baptism of the Lord.
- The ordinal words run from "First" to "Twenty-Eighth".
- Lectio fallback: "{season} — Year {year}" (em dash). A duplicate name gets " (2)", " (3)".
- The Vanderbilt rename applies only when the whole cell is `Proper \d+ \(\d+\)` on a Sunday. When `sunday_name(d)` is "All Saints Day" for a Proper row, the row takes the computed ordinal instead ("Twenty-Third Sunday after Pentecost" on 2026-11-01), as S's merge table and AC1 require (clarification 30).
- The Proper number is never shown.
- Owner answer Q3: `sunday_name` also returns "First Sunday after Christmas Day" (a Sunday Dec 26–Jan 1) and "Second Sunday after Christmas Day" (Jan 2–5); a Sunday Dec 25 or Jan 6 has `sunday_name(d) is None`, and `lectio_set_name` falls back to `weekday_feast_name(d)` ("Nativity of the Lord", "Epiphany of the Lord") (T6a).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change. Each one is recorded as a numbered clarification: "(owner decision 1; deviation from S …)".
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/. It is frozen, and merges never reach it.
   - The F §6.1 item 6 contingency is off: no shim, and no `test_legacy_lectionary_shim.py`.
   - `app.py`, `ui_helpers.py`, `streamlit_tenancy.py`, `streamlit_views/*` and `worship_service.py` are untouched.
   - `app.py` on main stops importing once `get_readings_for_date_string` is deleted. That is accepted: no test imports it, and 1b's removed `accept_invite` set the precedent.
3. **Railway** keeps its Pre-deploy Command (`alembic upgrade head`) and Healthcheck Path (`/health/ready`) in the Railway UI. 2a changes neither, and the pre-deploy is a no-op at head `0004`.
4. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
5. **Spec decision 1:** the step builder and summary panel. This is 2b/2c, and 2a only keeps the API additive.
6. **Spec decision 8:** any date is looked up as itself, with a manual fallback. That means no normalization and no nearest row, and `no_readings` is a normal 200.
7. **Spec decision 9:** readings fixes, including Psalm-as-NT. `resolve_readings` never returns a Psalm as the automatic NT.
8. **Spec decision A:** descriptive ordinary-time names, with named days always winning (§2).

### Owner answers (2026-09-28, binding for the plan)

The owner accepted every recommendation ("yes"):
- **Q1a: yes.** In T1 the implementer may run `pip install "respx>=0.22"` from PyPI into `.venv` (the dev dependency S requires); add it to requirements-dev.
- **Q1b: yes.** In T1 the implementer may run `backend/scripts/record_fixtures.py` once, making GET requests only to lectio-api.org, lectionary.library.vanderbilt.edu and bible-api.com (no ESV, no key), to record the fixtures (including the verbatim Easter Vigil row and real Content-Type headers). Recorded fixtures are committed; no secrets in them.
- **Q2 (FYI): accepted** as decided in clarification 30 (a Proper row whose sunday_name(d) is "All Saints Day" takes the computed ordinal, e.g. "Twenty-Third Sunday after Pentecost").
- **Q3: yes.** On Sundays also try `weekday_feast_name` (Dec 25 -> "Nativity of the Lord", Jan 6 -> "Epiphany of the Lord"), and add "First Sunday after Christmas Day" and "Second Sunday after Christmas Day" to `sunday_name` (T6a).
- **Q4: no early draft PR.** T13 is dropped; push once in T14 (owner's yes before pushing).
- **Q5: yes.** A short "Slice 2a record" in docs/ops-runbook.md after the merge (merge SHA, deploy check, whether ESV is configured, fixtures recorded or synthetic), via a docs-only records PR in T15.
- Also binding: the spec's open question 2 (Saturday vigil one-tap) is a 2c UI question; 2a provides nothing for it.

## Spec clarifications

Code wins over the outline; each is owner decision 1 unless noted.

1. **The spec names the wrong slice 1 test.** `test_cap_429_not_replayed` stays unchanged, because it makes its 5 creates through the repo and then only 2 POSTs. `test_blank_then_corrected_with_new_key_201` makes 4 POSTs, so it advances the limiter clock. (Deviation from S :302, :897.)
2. The `/church` exact-body asserts in `test_api_me.py:79`, `test_api_churches.py:79` and `test_api_invites.py:202` gain the new fields. (S gap.)
3. The `?date=` parameter is strict `YYYY-MM-DD` (`IsoDate`), because Pydantic's `date` accepts "0" and datetimes. This keeps "never normalized" and "Not a valid value.". (Verified.)
4. Every new route documents 422 and 503 as well, or `test_routes_document_the_error_body` fails. For `/translations` that means 401, 422 and 503, not S's 401 alone.
5. Error call forms use message first and `code=` as a keyword: `UpstreamError(msg, code="upstream_error")`, `InvalidInput(msg, field=…)`. (S snippets.)
6. `api/schemas.py` imports `date as DateType`, because the existing `from datetime import datetime` would make `datetime.date` a method.
7. The `GET /church` route supplies `id`, `name` and `role` from `ActiveChurch`. The usecase takes only the id (F §1.2 rule 1).
8. If the church is deleted between the guard and the read, the usecase raises the guard's own 403 `forbidden` / `no_church_access`. This adds no new documented status.
9. The ordinal table runs to "Twenty-Eighth". The maximum n over 1900–2199 is 28, which lands on Reign of Christ.
10. The compound-cell split happens only when the prefix's book is not a Psalm and the prefix does not end in " or". Otherwise `"Psalm 105:1-11, 45b or Psalm 128"` would split. (Verified in ND.)
11. The Proper regex must match the whole cell. If `sunday_name(d)` is None, the raw text is kept (defensive).
12. For Vanderbilt `ReadingSet`, `first`, `psalm`, `second` and `gospel` hold the cleaned cell text unsplit; `scriptures` holds the split lines.
13. `NOT_FOUND` lives 7 days in the same part cache (S: "use the same cache"). A bible-api 200 that can't be decoded is `unavailable`; empty text is `not_found`.
14. The "cached" part of the log line comes from a flag in the loader lambda, not from the cache API.
15. `parse_lectio_payload` raises only `ValueError` or `TypeError` on a bad shape, so the loader's `except` covers it.
16. `resolve_readings` compares whole lines (`e != ot`). A fixture case pins this for the TS port.
17. The limiter computes `n = max(1, ceil(wait))` once and uses it for both the message and the header.
18. Fetchers catch only `httpx.HTTPError` and a JSON `ValueError`. The no-network guard's `RuntimeError` surfaces as a bug.
19. Media types are compared without their parameters. The accepted Vanderbilt types stay S's (`text/plain`, `text/csv`) until a recording shows otherwise. That is UNVERIFIED (A3), and T1's meta sidecar settles it.
20. Fixture-driven tests loop inside one function, so counts stay stable.
21. The shared fixture carries a `books` section and one section per TS-ported function.
22. `shared/next_sunday.json` is created by 2b, not 2a.
23. No shim. `app.py` on main can no longer be imported after T7 (owner decision 2).
24. The https hook raises `httpx.UnsupportedProtocol`, so a redirect to http is a source failure and not a 500.
25. `TokenBucket` gains `wait_for(n)` for the all-or-nothing check across rules. `try_take(n > capacity)` raises `ValueError`.
26. Test hooks: `reset_for_tests(clock=…)` on each module that owns a cache; `set_http_for_tests(None)` restores the default client. Autouse fixtures use the deferred `sys.modules.get` pattern.
27. `fetch_passage` and `get_passage_text` fetch parts one after another. Only `load_passages` uses the pool and the deadline. `fetch_part` and `assemble_passage` are shared, so the statuses are derived once.
28. `normalize_book_text` also maps `iv`, `fourth`, `1st`–`4th`, and the digit-glue rule generalizes to `^[1-4](?=[a-z])`. No change is visible today: both "unknown" and "ot" sit on the OT picker side. 2c's testament badge will show "OT" rather than "?" for these spellings, which the shared fixture pins. (ND A9.)
29. 1b T6-m2: "usecase" is dropped from `CreateChurchIn`'s OpenAPI description, since 2a regenerates both files anyway.
30. **The All Saints Proper rename (decided under AC1; was Q2).** S :454 and AC4 say a Proper row takes `sunday_name(d)`, which on 2026-11-01 is "All Saints Day", while S's merge table (:504), which AC1 requires, expects "Twenty-Third Sunday after Pentecost". The merge table wins: when `sunday_name(d)` is "All Saints Day" for a Proper row, the row takes `_ordinary_time_name(d)` (the computed ordinal, ignoring named days). The match is on our own computed name, not on Vanderbilt's spelling of its All Saints row, so "All Saints' Day" variants cannot cause a duplicate. Reign of Christ is the only other named day on a Proper Sunday, and there the rename is intended. (S internal contradiction; T12 corrects S :454 and AC4.)
31. **Lectionary source deadline.** `readings_for_date` waits on its two futures with `wait(timeout=DEADLINE_SECONDS)` (20 s). A source unfinished at the deadline is `SourceFailed(timeout=True)` for this request; its loader keeps running and caches its own outcome. Reason: single-flight waiters for one Vanderbilt year sit inside the 4 pool workers, so concurrent cold lookups could queue Lectio tasks past the 25 s client timeout; S's "~15 s worst case" holds only for an idle pool. This keeps S's pool literally ("in parallel, on a module-level `ThreadPoolExecutor(max_workers=4)`") and mirrors the passages deadline. (Owner decision 1; S silent.)
32. `integrations/http.py` sets the `httpx` and `httpcore` loggers to WARNING, so the upstream URLs and query strings (the date, the ESV `q=`) never reach the logs, and pool threads emit no `request_id=-` lines. No secret leaked before (the ESV key is a header). (Owner decision 1; F §2.5.)
33. **Zero-part refs.** `split_parts` drops empty `;` pieces (the old code at `scripture_fetcher.py:167`), so `";"` would pass the blank check with cost 0 and render as an `ok` row with no text. `plan_parts` drops empty alternatives and parts; `plan_passages` rejects a ref with no parts as "Enter a scripture reference."; `consume` rejects `cost < 1` with `ValueError`. (Owner decision 1.)
34. `fits_draft_limits` also requires a set name of 1–300 characters, the Occasion field's limit (S :142), for Vanderbilt sets. `merge` applies the same check to each Lectio-only set after `lectio_set_name` names it. A pathological upstream name drops the set with the usual warning rather than giving the user a "Too long" error they did not cause. (Owner decision 1; extends S's limit guarantee.)
35. `rate_limit(name)` checks `name in BUCKETS` when called, so a misspelled bucket fails app start-up instead of turning every request on the route into a 500.
36. **Cache loader contract.** Only `CacheableFailure` is cached (for `ttl_fail`). Any other exception is re-raised to the loader's caller and to every waiter of the same flight, and nothing is stored, so the next call runs the loader again (S :888). The part cache's loader signals transient failures and budget misses by raising a private `_Transient`, which `fetch_part` turns into `unavailable`; returning an `unavailable` `Part` from the loader would cache it for 7 days.
37. Clock hooks: `set_clock_for_tests` empties the buckets or budgets it governs, `reset_for_tests` also restores `time.monotonic`, and `TokenBucket` clamps elapsed time at 0. A bucket created under one clock and read under another would otherwise lose tokens.
38. A 422 on `GET /lectionary/readings` spends a `lectionary` token, because FastAPI resolves the dependency before query validation fails. This is consistent with F §1.8 (as for `church_create`, S :302); S is silent for this bucket.
39. **Test thread hygiene.** Tests that block pool workers use a `threading.Event`, set in `finally`. The autouse resets for `usecases.lectionary` and `usecases.passages` first join their pool (`shutdown(wait=True)`) and then build a new pool and new cache objects, so no straggler holds a worker or writes into the next test's cache.
40. The shared fixture documents its encodings in a top-level `"_about"` key: `split_book` → `{"book": name, "rest": str}` or `null`; `picker_options` → `{"ot": [...], "nt": [...]}`; `resolve_readings` expected keys stay snake_case, and 2b's Vitest maps them to camelCase.
41. S's Palm Sunday JSON example (the names "Liturgy of the Palms" and "Liturgy of the Passion", and the Palms scriptures) is unverified Vanderbilt text. If the recording differs, `test_palm_sunday_200_shape` asserts the recorded equivalent and T12 corrects S's example, marked "(2a plan)".

### Risks carried into the plan

- **Fixture fidelity.** Any fixture the recorder cannot get (T1 Step 9) is hand-built, so the tests that use it run against a reconstruction, and live-shape surprises surface only after deploy. `fits_draft_limits` and the 5-minute failure TTL limit the damage.
- **Vanderbilt Content-Type mismatch.** Every production fetch would count as failed; T15's live check catches it.
- **ESV in production.** With no ESV key on Railway, ESV stays hidden until the owner sets the key.
- **Frozen `app.py` on main** is no longer importable. This is accepted.
- **Lectionary pool saturation.** Several concurrent cold lookups can queue a source behind single-flight waiters. The 20 s source deadline (clarification 31) keeps each request inside the 25 s client timeout, at the cost of a `partial` 200 or a 504 under that load. It is unlikely at today's traffic.
- **Process-wide bible-api budget.** 15 parts per 30 s is shared by every user, so one "Show all text" on a long service can leave a second user's parts `unavailable` for up to 30 s. That is S's design (Upstream budgets). An `unavailable` part is never cached on the server, 2b's `usePassage` refetches it (`staleTime` 0, S :808), and 2c's "Try again" covers it.

Controller notes (2026-09-28, final plan check, both Minor):
- If Vanderbilt fails on an All Saints Sunday (e.g. 2026-11-01), the Lectio-only set is named "All Saints Day". Accepted: named days win (decision A); clarification 30 applies only to Vanderbilt's Proper row on that date.
- S :605 still says "24 h is enough" for NOT_FOUND caching; clarification 13 (7 days) governs. Left as a known spec wording mismatch for a later docs pass.

## File Structure

**Created**

| Path | Responsibility |
|---|---|
| `docs/superpowers/plans/2026-09-28-slice-2a-backend.md` | the plan (first commit) |
| `backend/integrations/__init__.py` | package marker |
| `backend/integrations/http.py` | the one outbound `httpx.Client`: https-only hook, per-call read timeout, `set_http_for_tests` |
| `backend/integrations/budget.py` | process-wide `bible_api` and `esv` token budgets (`try_acquire`) |
| `backend/cache.py` | `TTLCache` (ok and failure TTLs, LRU, single-flight per key) and `CacheableFailure` |
| `backend/token_bucket.py` | pure continuous-refill `TokenBucket` |
| `backend/api/ratelimit.py` | per-user and per-church buckets, `consume`, the `rate_limit(name)` dependency, test hooks |
| `backend/scripture_refs.py` | book table, classifier, pickers, `resolve_readings`, fetch normalization, keys |
| `backend/usecases/lectionary.py` | `readings_for_date`: parallel cached sources, merge, status rules, one log line |
| `backend/usecases/passages.py` | `plan_passages`, `load_passages` (shared pool, deadline), `translation_options`, `get_passage_text` re-export |
| `backend/usecases/church_profile.py` | `get_church_profile(church_id)` |
| `backend/api/routes/lectionary.py` | `GET /lectionary/readings` |
| `backend/api/routes/reference.py` | `GET /translations` |
| `backend/api/routes/scripture.py` | `POST /scripture/passages` |
| `backend/scripts/record_fixtures.py` | manual recorder, never run in CI. It writes each body plus a `.meta.json` (`{"status", "content_type", "url", "recorded_at", "synthetic"}`), trims the Vanderbilt CSV to the fixture dates, has `--synthetic`, `--only` and `--list` modes, and rewrites `backend/tests/fixtures/README.md` (T1) |
| `backend/tests/fixtures/README.md` | written by the recorder: how fixtures were made (recorded or synthetic, per file), how to refresh, and the `## shared/` section |
| `backend/tests/fixtures/lectio/*.json` + `.meta.json` | 9 × 200: 2025-12-24, 2025-12-25, 2026-02-18, 2026-03-29, 2026-04-05, 2026-05-14, 2026-05-31, 2026-10-04, 2026-11-01. 4 × 404: 2026-04-03, 2026-01-01, 2026-11-26, 2026-09-29. `html_200` and `error_500` (synthetic). |
| `backend/tests/fixtures/vanderbilt/*` | `2025-26.csv`, trimmed but keeping the preamble, header, file order and the full Vigil row; `2026-27.csv` and `2027-28.csv` stubs with the Advent 1 rows; `404.html` (1999-00); `html_200.html` (2045-46); meta sidecars |
| `backend/tests/fixtures/bible_api/*` | `isaiah_50_4-9` (200), `isaiah_50_4-9a` (404), `luke_2_1-14_15-20` (comma list) |
| `backend/tests/fixtures/esv/*` | `success.json` (synthetic text "For God so loved the world. (ESV)"), `empty.json` (`{"passages": []}`) |
| `backend/tests/fixtures/shared/scripture_refs.json` | Python↔TS cases: sections per function, plus `books` |
| `backend/tests/upstream_fixtures.py` | `FIXTURES_DIR`, `FIXTURE_DATES`, `load(kind, name \| date) -> Recorded(status, content_type, body)` (T1), plus `LECTIO_URL`, `VANDERBILT_URL`, `as_response`, `answer`, `route_lectio`, `route_vanderbilt` (T7) |
| New test files (§5) | `test_fixtures_recorder`, `test_http_client`, `test_cache`, `test_ratelimit`, `test_budget`, `test_scripture_refs`, `test_lectionary_domain`, `test_usecase_lectionary`, `test_api_lectionary`, `test_scripture_fetcher`, `test_usecase_passages`, `test_api_scripture`, `test_api_translations`, `test_api_church_profile` |

**Modified**

| Path | Change |
|---|---|
| `requirements-dev.txt` | add `respx>=0.22`, with a comment that it is the httpx 0.28-compatible floor |
| `backend/vanderbilt_lectionary.py` | refactor (T6a and T6b additive, T7 replaces and deletes) |
| `backend/scripture_fetcher.py` | refactor; public names kept |
| `backend/api/main.py` | mount the `lectionary`, `reference` and `scripture` routers |
| `backend/api/schemas.py` | the 2a models, `IsoDate`, `ChurchProfileOut`; drop the word "usecase" from `CreateChurchIn`'s docstring (1b T6-m2) |
| `backend/api/routes/me.py` | `GET /church` → `ChurchProfileOut` |
| `backend/api/routes/churches.py` | `Depends(rate_limit("church_create"))` after `user`, before `key`; docstring |
| `backend/tests/conftest.py` | autouse resets: `_fresh_http_client` (T2), `_fresh_rate_limits` (limiter and budgets, T3), `_fresh_lectionary_caches` (T7), `_fresh_passage_cache` (T9), `_fresh_passages_pool` (T10) (deferred `sys.modules.get`, as at `conftest.py:151`). The lectionary and passages resets first join their module pool (`shutdown(wait=True)`), then rebuild the pool and the caches as new objects (clarification 39). Fixtures: `limiter_clock` and `budget_clock`, each a `FakeClock` |
| `backend/tests/test_no_streamlit_in_core.py` | extend the import list (grows each task) |
| `backend/tests/test_route_guards.py` | three routes in `USER_SCOPED`; docstring line "2a: …" |
| `backend/tests/test_api_app.py` | the `test_routes_document_the_error_body` map gains the three routes |
| `backend/tests/test_api_churches.py` | `test_blank_then_corrected_with_new_key_201` advances the limiter clock; 4 burst tests (T4); the `/church` exact-body check (`:80` on main, `:87` after T4) gains the new fields (T11) |
| `backend/tests/test_api_me.py` (:80), `backend/tests/test_api_invites.py` (:202) | `/church` exact-body checks pin the whole new body (T11) |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated (T4, T8, T10, T11) |
| `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` | amendment rows (T12) |
| `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md` | corrections (T12) |
| `docs/ops-runbook.md` | one line: the new app reads `ESV_API_KEY` on Railway, and while it is unset ESV is hidden (T12; no owner marker) |

**Deleted:** `backend/tests/test_scripture_translations.py` (5 tests, ported in T9).

**Untouched:** `backend/requirements.txt`, migrations, `app.py`, `worship_service.py`, `streamlit_views/*`, `streamlit_tests/*`, CI workflows.

**Task order and checkpoints:** T1 → T2 → T3 → T4 → T5 → T6a → T6b → T7 → T8 → T9 → T10 → T11 → T12 → T14 → T15. There is no Task 13 (owner answer Q4: no early draft PR). Each task ends in one commit (T1 also commits this plan as the branch's first commit, so the branch carries 14 commits before T14), and the review checkpoints at the end of T4, T6a, T6b, T9, T10, T11 and T12 are stops for the controller, not merges: everything ships in the one 2a PR.

---
### Task 1: Preflight, respx, the fixture recorder and the upstream fixtures (S Testing "Fixtures"; F §5; owner Q1a, Q1b)

This task commits the plan, checks the baseline, installs the one new dev dependency (`respx`, owner Q1a: yes), and records the upstream answers every later lectionary and passage test replays (owner Q1b: yes). Nothing in the app changes: the recorder is a manual script that CI never runs, and the tests added here only read the files it wrote. The four fixtures that cannot be recorded (no ESV key; Lectio cannot be made to send an HTML 200 or a 500) are always hand-built. Any other fixture the recorder cannot get (a site is down, or it answers with a status or shape the tests do not expect) is hand-built from S "Upstream facts" 1–6 with `--synthetic`, and its sidecar and the README say so. The frontend does not change.

**Files:**
- Commit (Step 0): `docs/superpowers/plans/2026-09-28-slice-2a-backend.md` (this plan; the branch's first commit)
- Modify: `requirements-dev.txt` (append three lines after line 4, `PyYAML>=6.0`)
- Create: `backend/scripts/record_fixtures.py`
- Create: `backend/tests/upstream_fixtures.py`
- Create, written only by the recorder (Steps 8–9), never by hand: `backend/tests/fixtures/README.md` and 25 fixtures, each a body plus a `<name>.meta.json` sidecar (51 files):
  - `backend/tests/fixtures/lectio/`: `2025-12-24.json`, `2025-12-25.json`, `2026-01-01.json`, `2026-02-18.json`, `2026-03-29.json`, `2026-04-03.json`, `2026-04-05.json`, `2026-05-14.json`, `2026-05-31.json`, `2026-09-29.json`, `2026-10-04.json`, `2026-11-01.json`, `2026-11-26.json`, `html_200.html`, `error_500.json`
  - `backend/tests/fixtures/vanderbilt/`: `2025-26.csv`, `2026-27.csv`, `2027-28.csv`, `404.html`, `html_200.html`
  - `backend/tests/fixtures/bible_api/`: `isaiah_50_4-9.json`, `isaiah_50_4-9a.json`, `luke_2_1-14_15-20.json`
  - `backend/tests/fixtures/esv/`: `success.json`, `empty.json`
- Test: `backend/tests/test_fixtures_recorder.py` (new, 2 tests)

**Interfaces:**
- Consumes:
  - The upstream URLs as they are in the code today, copied into the recorder as literals (the recorder imports nothing from `backend/`): `backend/vanderbilt_lectionary.py:16` `LECTIO_API_URL = "https://lectio-api.org/api/v1/readings"`, `:19` `VANDERBILT_YEAR_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv"`; `backend/scripture_fetcher.py:20` `BIBLE_API_BASE = "https://bible-api.com"`, `:21` `ESV_API_BASE = "https://api.esv.org/v3/passage/text/"`. The Lectio query is `date=<iso>&tradition=rcl` (`vanderbilt_lectionary.py:267`); the bible-api query is `translation=<id>` (`scripture_fetcher.py:75`).
  - The by-path loading of a script in `backend/scripts/` (`backend/tests/test_openapi_contract.py:19-24`, `_load_export_openapi`).
  - `pytest.ini` `pythonpath = . backend`, so `from tests.upstream_fixtures import …` resolves as `from tests.api_helpers import …` does (`backend/tests/test_api_churches.py:17`).
- Produces:
  - `tests.upstream_fixtures.FIXTURES_DIR: Path` = `backend/tests/fixtures`.
  - `tests.upstream_fixtures.FIXTURE_DATES: tuple[date, ...]`: the 13 merge-table dates in ascending order: 2025-12-24, 2025-12-25, 2026-01-01, 2026-02-18, 2026-03-29, 2026-04-03, 2026-04-05, 2026-05-14, 2026-05-31, 2026-09-29, 2026-10-04, 2026-11-01, 2026-11-26. Every one falls in liturgical year `2025-26`.
  - `tests.upstream_fixtures.Recorded(status: int, content_type: str, body: bytes)`, a frozen dataclass. `content_type` is the full header value, parameters included (for example `application/json; charset=utf-8`).
  - `tests.upstream_fixtures.load(kind: str, name: str | date) -> Recorded`. `kind` is `lectio`, `vanderbilt`, `bible_api` or `esv`; `name` is a file stem listed under **Files** (a `date` is turned into its ISO string, so `load("lectio", d)` works for every `d` in `FIXTURE_DATES`). An unknown name raises `FileNotFoundError`. Later users: T6b (parsing, `test_merge_table`, `test_every_fixture_date_fits_limits`), T7 (adds its respx helpers to this module), T8, T9.
  - The sidecar format: `<kind>/<name>.meta.json` holds exactly `{"content_type": str, "recorded_at": str, "status": int, "synthetic": bool, "url": str}` (sorted keys, two-space indent). `backend/tests/fixtures/README.md` lists every fixture with its status, Content-Type and "recorded YYYY-MM-DD" or "synthetic".
  - Status per fixture (a recording that differs is a FAIL and is replaced by the hand-built one, Step 9): the nine Lectio data dates, `lectio/html_200`, the three Vanderbilt years, `vanderbilt/html_200`, `bible_api/isaiah_50_4-9`, `bible_api/luke_2_1-14_15-20`, `esv/success` and `esv/empty` are 200; `lectio/2026-01-01`, `2026-04-03`, `2026-09-29`, `2026-11-26`, `vanderbilt/404` and `bible_api/isaiah_50_4-9a` are 404; `lectio/error_500` is 500.
  - The fixture content facts the hand-built versions carry, from S "Merge" and "Upstream facts". A recording that differs from them prints a `DIFF` line that Step 13 reports:

    | Date | Vanderbilt rows (file order) | Lectio gospels (non-alternative, in order) |
    |---|---|---|
    | 2025-12-24 | Nativity of the Lord - Proper I | Luke 2:1-14 (15-20) |
    | 2025-12-25 | Nativity of the Lord - Proper II; Nativity of the Lord - Proper III | John 1:1-14 |
    | 2026-01-01 | Holy Name of Jesus; New Year's Day | 404 |
    | 2026-02-18 | Ash Wednesday | Matthew 6:1-6, 16-21 |
    | 2026-03-29 | Liturgy of the Palms; Liturgy of the Passion | Matthew 26:14-27:66 |
    | 2026-04-03 | Good Friday | 404 |
    | 2026-04-05 | Easter Vigil (the one 513–517-character `" - "` cell, other reading cells empty); Resurrection of the Lord; Easter Evening | John 20:1-18 |
    | 2026-05-14 | Ascension of the Lord (gospel Luke 24:44-53) | Matthew 28:16-20 |
    | 2026-05-31 | Visitation; Trinity Sunday | Matthew 7:21-29, then Matthew 28:16-20 (two groups) |
    | 2026-09-29 | none | 404 |
    | 2026-10-04 | Proper 22 (27), two-track cells | Matthew 21:33-46 |
    | 2026-11-01 | All Saints Day; Proper 26 (31) | Matthew 23:1-12 |
    | 2026-11-26 | Thanksgiving Day (First reading `"Deuteronomy 8:7-18 Psalm 65"`) | 404 |

    `vanderbilt/2026-27.csv` holds only the 2026-11-29 Advent 1 row and `vanderbilt/2027-28.csv` only the 2027-11-28 one, each after the file's preamble and header. The row *names* above are S's where S gives them; the recorded names are whatever Vanderbilt sends, so later tasks assert a recorded name only after reading it from the fixture (clarification 41).
  - Recorder module names, read by `test_fixtures_recorder.py`: `LECTIO_DATES`, `LECTIO_OK_DATES`, `LECTIO_404_DATES` (ISO strings), `VANDERBILT_KEEP: dict[str, tuple[str, ...]]`, `all_names() -> list[str]` (the 25 `kind/name` keys), `main(argv: list[str] | None = None) -> int`.
  - `respx>=0.22` in `requirements-dev.txt` and installed in `.venv` (used from T7 and T9 on; CI installs it from `requirements-dev.txt`, `ci.yml:16,47`).

Counts after this task: backend **800 passed, 9 skipped** (798 + 2); frontend **221 passed in 34 files** (unchanged).

- [ ] **Step 0 (agent): Commit this plan (the branch's first commit)**

Skip this step if `git log --oneline origin/main..HEAD -- docs/superpowers/plans/2026-09-28-slice-2a-backend.md` already prints a line (the controller may commit the plan before dispatching Task 1).

```bash
git status --short
git add docs/superpowers/plans/2026-09-28-slice-2a-backend.md
git commit -m "Plan: slice 2a backend (F, S slice 2; owner answers 2026-09-28)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

**Expected:** before the commit, `git status --short` lists exactly `?? .claude/` and `?? docs/superpowers/plans/2026-09-28-slice-2a-backend.md` (`.claude/` stays untracked and is never staged). Afterwards the last line is `<sha> Plan: slice 2a backend (F, S slice 2; owner answers 2026-09-28)`.

- [ ] **Step 1 (agent): Check the branch and the baseline**

```bash
git fetch origin
git status -sb | head -1
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD
test ! -e backend/integrations && test ! -e backend/cache.py && test ! -e backend/scripts/record_fixtures.py && test ! -e backend/tests/fixtures && echo "no 2a files yet"
ls backend/migrations/versions/*.py | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
cat requirements-dev.txt
.venv/bin/python --version
.venv/bin/python -c "import httpx; print(httpx.__version__)"
.venv/bin/python -c "import respx" 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npx vitest run 2>&1 | grep -E '^ +(Test Files|Tests) ')
```

**Expected,** in order:
- `## claude/slice-2-plan...origin/main [ahead 1]` (only the plan commit on this branch);
- `55f1b11 Merge pull request #19 from bbrown62450/claude/slice-1b-records`;
- exactly one line, the plan commit from Step 0;
- `no 2a files yet`;
- `backend/migrations/versions/0004_invites_reusable.py` (2a adds no migration);
- `4` (`wc` pads it with spaces; 2a adds no owner marker);
- the four lines `-r requirements.txt`, `pytest>=8.0`, `# backend/tests/test_ops_workflows.py parses workflow YAML`, `PyYAML>=6.0`;
- `Python 3.11.<n>`;
- `0.28.1`;
- `ModuleNotFoundError: No module named 'respx'`;
- `798 passed, 9 skipped in <t>s`;
- ` Test Files  34 passed (34)` and `      Tests  221 passed (221)`.

If the branch line shows `behind`, run `git diff --name-only 55f1b11 origin/main`. When every listed path is under `docs/`, merge it now: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"` (the branch holds only the plan, so no conflict), then rerun this step and expect `[ahead 2]`, two lines from `git log --oneline origin/main..HEAD` and the same counts. If any other path is listed, a count differs, or any other line differs, stop and ask the owner.

- [ ] **Step 2 (agent; owner approved Q1a on 2026-09-28): Add respx and install it**

Replace the whole of `requirements-dev.txt` with:

```text
-r requirements.txt
pytest>=8.0
# backend/tests/test_ops_workflows.py parses workflow YAML
PyYAML>=6.0
# backend/tests mock the upstream HTTP calls with respx (slice 2);
# 0.22 is the first respx release that works with httpx 0.28
respx>=0.22
```

Then install it into `.venv` (one download from PyPI; this is the only package this task installs):

```bash
.venv/bin/python -m pip install "respx>=0.22" 2>&1 | tail -1
.venv/bin/python -c "import respx, httpx; print(respx.__version__, httpx.__version__)"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `Successfully installed respx-0.22.0` (a later `0.2x` release is fine); then `0.22.0 0.28.1` (the respx version as installed; httpx must still be `0.28.1`); then `798 passed, 9 skipped in <t>s`. If pip reports installing, upgrading or uninstalling `httpx`, stop and report. If pip cannot reach PyPI, report it and go on with Step 3: this task's tests do not use respx, but T7 and T9 need it installed.

- [ ] **Step 3 (agent): Write the failing tests**

Create `backend/tests/test_fixtures_recorder.py`:

```python
"""The upstream fixtures and their recorder agree (S Testing "Fixtures"; F §5).

backend/scripts/record_fixtures.py writes backend/tests/fixtures/; these
tests only read what it wrote. They never run the recorder's network code.
"""
import importlib.util
import json
from datetime import date
from pathlib import Path

from tests.upstream_fixtures import FIXTURE_DATES, FIXTURES_DIR, load

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "record_fixtures.py"
ALWAYS_SYNTHETIC = {"lectio/html_200", "lectio/error_500", "esv/success", "esv/empty"}


def _load_recorder():
    """backend/scripts is not a package: load the script by path, as test_openapi_contract does."""
    spec = importlib.util.spec_from_file_location("record_fixtures_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _meta_files() -> list[Path]:
    return sorted(FIXTURES_DIR.glob("*/*.meta.json"))


def test_recorder_dates_match_fixture_files():
    recorder = _load_recorder()
    recorder_dates = {date.fromisoformat(d) for d in recorder.LECTIO_DATES}
    lectio_files = {date.fromisoformat(p.name.removesuffix(".meta.json"))
                    for p in (FIXTURES_DIR / "lectio").glob("*.meta.json") if p.name[:1].isdigit()}
    assert len(FIXTURE_DATES) == 13
    assert recorder_dates == lectio_files == set(FIXTURE_DATES)
    assert set(recorder.VANDERBILT_KEEP["2025-26"]) == set(recorder.LECTIO_DATES)
    not_found = {d for d in FIXTURE_DATES if load("lectio", d).status == 404}
    assert not_found == {date.fromisoformat(d) for d in recorder.LECTIO_404_DATES}
    assert sorted(recorder.all_names()) == sorted(
        f"{p.parent.name}/{p.name.removesuffix('.meta.json')}" for p in _meta_files())


def test_every_fixture_has_status_and_content_type():
    metas = _meta_files()
    assert metas, "no fixtures: run backend/scripts/record_fixtures.py (see backend/tests/fixtures/README.md)"
    readme = (FIXTURES_DIR / "README.md").read_text(encoding="utf-8")
    for meta_path in metas:
        kind, name = meta_path.parent.name, meta_path.name.removesuffix(".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        assert set(meta) == {"status", "content_type", "url", "recorded_at", "synthetic"}, meta_path
        assert isinstance(meta["status"], int) and 100 <= meta["status"] <= 599, meta_path
        assert isinstance(meta["content_type"], str) and meta["content_type"].strip(), meta_path
        assert meta["url"].startswith("https://"), meta_path
        assert isinstance(meta["synthetic"], bool), meta_path
        if f"{kind}/{name}" in ALWAYS_SYNTHETIC:
            assert meta["synthetic"] is True, meta_path
        recorded = load(kind, name)
        assert (recorded.status, recorded.content_type) == (meta["status"], meta["content_type"])
        assert recorded.body, meta_path
        assert f"`{kind}/{name}`" in readme, f"README.md does not list {kind}/{name}"
    bodies = {p for p in FIXTURES_DIR.glob("*/*") if not p.name.endswith(".meta.json")
              and not p.name.startswith(".") and p.parent.name != "shared"}
    stems = {(p.parent.name, p.name.split(".", 1)[0]) for p in bodies}
    assert len(stems) == len(bodies) == len(metas), "a body file without a sidecar, or two bodies for one"
```

- [ ] **Step 4 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_fixtures_recorder.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_fixtures_recorder.py 2>&1 | grep -m1 ModuleNotFoundError
```

**Expected:**

```text
ERROR backend/tests/test_fixtures_recorder.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

then `E   ModuleNotFoundError: No module named 'tests.upstream_fixtures'`.

- [ ] **Step 5 (agent): Write the fixture loader**

Create `backend/tests/upstream_fixtures.py`:

```python
"""Load the recorded upstream answers in backend/tests/fixtures/ (S Testing "Fixtures").

`load("lectio", "2026-03-29")` returns the status, Content-Type and raw body
that backend/scripts/record_fixtures.py saved, ready to replay through respx
or httpx.MockTransport. Nothing here touches the network.
"""
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# The merge-table dates (S "Merge"): Lectio has data for nine of them and
# answers 404 for 2026-01-01, 2026-04-03, 2026-09-29 and 2026-11-26.
FIXTURE_DATES: tuple[date, ...] = tuple(date.fromisoformat(d) for d in (
    "2025-12-24", "2025-12-25", "2026-01-01", "2026-02-18", "2026-03-29",
    "2026-04-03", "2026-04-05", "2026-05-14", "2026-05-31", "2026-09-29",
    "2026-10-04", "2026-11-01", "2026-11-26",
))


@dataclass(frozen=True)
class Recorded:
    status: int
    content_type: str
    body: bytes


def load(kind: str, name: str | date) -> Recorded:
    """The fixture `<kind>/<name>`: its sidecar's status and Content-Type, and the body bytes."""
    stem = name.isoformat() if isinstance(name, date) else name
    folder = FIXTURES_DIR / kind
    meta = json.loads((folder / f"{stem}.meta.json").read_text(encoding="utf-8"))
    bodies = [p for p in folder.glob(f"{stem}.*") if not p.name.endswith(".meta.json")]
    if len(bodies) != 1:
        raise FileNotFoundError(f"{kind}/{stem}: expected one body file, found {sorted(p.name for p in bodies)}")
    return Recorded(status=meta["status"], content_type=meta["content_type"], body=bodies[0].read_bytes())
```

- [ ] **Step 6 (agent): Write the recorder**

Create `backend/scripts/record_fixtures.py`. It needs no `chmod`: it is always run as `.venv/bin/python backend/scripts/record_fixtures.py`.

```python
"""Record the upstream test fixtures in backend/tests/fixtures/ (S Testing "Fixtures"; F §5).

Manual only: CI never runs this, and the test suite never touches the network.
Run it from the repo root, and only with the owner's permission, because it
makes GET requests to lectio-api.org, lectionary.library.vanderbilt.edu and
bible-api.com (never ESV, and no key is sent anywhere):

    .venv/bin/python backend/scripts/record_fixtures.py

Every fixture is a body file plus a sidecar `<name>.meta.json` holding
{"status", "content_type", "url", "recorded_at", "synthetic"}. The Vanderbilt
year files are trimmed to the fixture dates; the trim keeps the preamble, the
header line and the file's own row order, and copies each kept row verbatim.
Four fixtures are always synthetic, because they cannot be recorded (no ESV
key; Lectio cannot be made to send an HTML 200 or a 500): lectio/html_200,
lectio/error_500, esv/success and esv/empty. Every run writes them.

Each run prints one line per fixture:
  OK   <kind/name> ...  recorded as the tests expect;
  DIFF <kind/name> ...  recorded and written, but it differs from the spec's
                        upstream facts: report the line;
  FAIL <kind/name> ...  not written (site down, or the wrong status or shape);
  SYN  <kind/name> ...  written hand-built.
The exit status is 1 when any FAIL line was printed. For each FAIL, write the
hand-built version of just that fixture instead, built from the spec's
upstream facts and marked "synthetic": true:

    .venv/bin/python backend/scripts/record_fixtures.py --synthetic lectio/2026-03-29

`--synthetic all` writes every fixture hand-built (offline). `--only NAME ...`
records just those fixtures. `--list` prints every fixture name. Every run
rewrites backend/tests/fixtures/README.md from the sidecars.

This script imports nothing from backend/, so it runs without the app's settings.
"""
import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

# Kept in step with integrations/http.py and the fetchers (S Global constraints).
USER_AGENT = "WorshipServiceBuilder/1.0"
LECTIO_API_URL = "https://lectio-api.org/api/v1/readings"
VANDERBILT_YEAR_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv"
BIBLE_API_BASE = "https://bible-api.com"
ESV_API_BASE = "https://api.esv.org/v3/passage/text/"
# Generous: this is a manual run, not a request path.
TIMEOUT = httpx.Timeout(20.0, connect=5.0)

# The merge-table dates (S "Merge"). Lectio answers the first nine with data
# and the last four with a JSON 404 (S Upstream facts 1).
LECTIO_OK_DATES = (
    "2025-12-24", "2025-12-25", "2026-02-18", "2026-03-29", "2026-04-05",
    "2026-05-14", "2026-05-31", "2026-10-04", "2026-11-01",
)
LECTIO_404_DATES = ("2026-01-01", "2026-04-03", "2026-09-29", "2026-11-26")
LECTIO_DATES = tuple(sorted(LECTIO_OK_DATES + LECTIO_404_DATES))

# The rows each Vanderbilt year file keeps: every merge-table date in 2025-26,
# and the Advent 1 row of the next two years (the boundary tests' stubs).
VANDERBILT_KEEP = {
    "2025-26": LECTIO_DATES,
    "2026-27": ("2026-11-29",),
    "2027-28": ("2027-11-28",),
}

# How many Vanderbilt rows S's merge table expects on each date.
VANDERBILT_ROWS = {
    "2025-12-24": 1, "2025-12-25": 2, "2026-01-01": 2, "2026-02-18": 1,
    "2026-03-29": 2, "2026-04-03": 1, "2026-04-05": 3, "2026-05-14": 1,
    "2026-05-31": 2, "2026-09-29": 0, "2026-10-04": 1, "2026-11-01": 2,
    "2026-11-26": 1, "2026-11-29": 1, "2027-11-28": 1,
}

# The gospel S's merge table expects Lectio to send (the merge matches on it).
LECTIO_GOSPELS = {
    "2025-12-24": ("Luke 2:1-14 (15-20)",),
    "2025-12-25": ("John 1:1-14",),
    "2026-02-18": ("Matthew 6:1-6, 16-21",),
    "2026-03-29": ("Matthew 26:14-27:66",),
    "2026-04-05": ("John 20:1-18",),
    "2026-05-14": ("Matthew 28:16-20",),
    "2026-05-31": ("Matthew 7:21-29", "Matthew 28:16-20"),
    "2026-10-04": ("Matthew 21:33-46",),
    "2026-11-01": ("Matthew 23:1-12",),
}

VIGIL_HEADINGS = ("Old Testament Readings and Psalms", "New Testament Reading and Psalm", "Gospel")
CSV_HEADER = ("Liturgical Date", "Calendar Date", "First reading", "Psalm",
              "Second reading", "Gospel", "Art", "Prayer")

ALWAYS_SYNTHETIC = ("lectio/html_200", "lectio/error_500", "esv/success", "esv/empty")


@dataclass(frozen=True)
class Target:
    """One recordable fixture: where it is fetched from and what the tests expect."""
    key: str                 # "kind/name"
    ext: str                 # body file extension
    url: str
    params: dict | None
    status: int              # the status the tests expect


def _bible_api_url(part: str) -> str:
    # The request T9's fetcher sends: the lower-cased part, quoted with ":,-" kept.
    return f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"


def targets() -> list[Target]:
    out = [Target(f"lectio/{d}", ".json", LECTIO_API_URL, {"date": d, "tradition": "rcl"},
                  404 if d in LECTIO_404_DATES else 200) for d in LECTIO_DATES]
    out += [Target(f"vanderbilt/{y}", ".csv", VANDERBILT_YEAR_URL.format(year=y), None, 200)
            for y in VANDERBILT_KEEP]
    out += [
        Target("vanderbilt/404", ".html", VANDERBILT_YEAR_URL.format(year="1999-00"), None, 404),
        Target("vanderbilt/html_200", ".html", VANDERBILT_YEAR_URL.format(year="2045-46"), None, 200),
        Target("bible_api/isaiah_50_4-9", ".json", _bible_api_url("Isaiah 50:4-9"), {"translation": "web"}, 200),
        Target("bible_api/isaiah_50_4-9a", ".json", _bible_api_url("Isaiah 50:4-9a"), {"translation": "web"}, 404),
        Target("bible_api/luke_2_1-14_15-20", ".json", _bible_api_url("Luke 2:1-14, 15-20"),
               {"translation": "web"}, 200),
    ]
    return out


def all_names() -> list[str]:
    return [t.key for t in targets()] + list(ALWAYS_SYNTHETIC)


# --- helpers ---------------------------------------------------------------

def media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _full_url(url: str, params: dict | None) -> str:
    return f"{url}?{urlencode(params)}" if params else url


def _parse_calendar_date(cell: str) -> date | None:
    text = cell.strip().strip('"')
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _records(lines: list[str]) -> list[list[str]]:
    """Group physical lines into CSV records: a quoted cell may hold a line break."""
    groups, current, quotes = [], [], 0
    for line in lines:
        current.append(line)
        quotes += line.count('"')
        if quotes % 2 == 0:
            groups.append(current)
            current, quotes = [], 0
    if current:
        groups.append(current)
    return groups


def trim_vanderbilt(text: str, keep: tuple[str, ...]) -> tuple[str, dict[str, list[list[str]]]]:
    """The preamble, the header line and the rows dated in `keep`, verbatim and in file order."""
    lines = text.splitlines(keepends=True)
    header_at = next((i for i, line in enumerate(lines)
                      if "Calendar Date" in line and "Liturgical Date" in line), None)
    if header_at is None:
        raise ValueError("no header line with 'Calendar Date' and 'Liturgical Date'")
    wanted = {date.fromisoformat(d): d for d in keep}
    kept = lines[: header_at + 1]
    rows: dict[str, list[list[str]]] = {d: [] for d in keep}
    for group in _records(lines[header_at + 1:]):
        raw = "".join(group)
        if not raw.strip():
            continue
        cells = next(csv.reader(io.StringIO(raw)), [])
        on = _parse_calendar_date(cells[1]) if len(cells) > 1 else None
        if on in wanted:
            kept.extend(group)
            rows[wanted[on]].append(cells)
    return "".join(kept), rows


def write_fixture(key: str, ext: str, *, status: int, content_type: str, url: str,
                  body: bytes, synthetic: bool) -> None:
    kind, name = key.split("/", 1)
    folder = FIXTURES / kind
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{name}.*"):
        old.unlink()
    (folder / f"{name}{ext}").write_bytes(body)
    meta = {
        "status": status,
        "content_type": content_type,
        "url": url,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "synthetic": synthetic,
    }
    (folder / f"{name}.meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8")


# --- checks against the spec's upstream facts ---------------------------------

def _lectio_gospels(payload: dict) -> list[str]:
    readings = payload["data"]["readings"]
    return [r.get("citation", "").strip() for r in readings
            if r.get("type") == "gospel" and not r.get("isAlternative")]


def check(target: Target, response: httpx.Response) -> tuple[bytes, list[str], list[str]]:
    """Return (body to write, FAIL reasons, DIFF notes)."""
    fails: list[str] = []
    diffs: list[str] = []
    body = response.content
    ctype = media_type(response.headers.get("content-type", ""))
    kind, name = target.key.split("/", 1)
    if response.status_code != target.status:
        return body, [f"status {response.status_code}, expected {target.status}"], diffs
    if kind == "lectio" and target.status == 200:
        if ctype != "application/json" and not ctype.endswith("+json"):
            fails.append(f"content type {ctype!r} is not JSON")
            return body, fails, diffs
        try:
            payload = response.json()
            gospels = _lectio_gospels(payload)
        except (ValueError, KeyError, TypeError) as exc:
            return body, [f"unexpected JSON shape: {exc!r}"], diffs
        if gospels == []:
            fails.append("no readings")
        expected = list(LECTIO_GOSPELS[name])
        if gospels != expected:
            diffs.append(f"gospels {gospels}, S expects {expected}")
    elif kind == "vanderbilt" and name in VANDERBILT_KEEP:
        if ctype not in ("text/plain", "text/csv"):
            diffs.append(f"Content-Type {response.headers.get('content-type')!r}: "
                         "S's fetch_vanderbilt_year accepts only text/plain and text/csv")
        try:
            trimmed, rows = trim_vanderbilt(response.text, VANDERBILT_KEEP[name])
        except ValueError as exc:
            return body, [str(exc)], diffs
        body = trimmed.encode(response.encoding or "utf-8")
        for d, found in rows.items():
            if len(found) != VANDERBILT_ROWS[d]:
                names = [cells[0] for cells in found]
                diffs.append(f"{d}: {len(found)} rows {names}, S expects {VANDERBILT_ROWS[d]}")
        if name == "2025-26":
            vigil = [cells for cells in rows["2026-04-05"] if len(cells) > 5 and " - " in cells[2]]
            if len(vigil) != 1:
                diffs.append(f"2026-04-05: {len(vigil)} rows with a ' - ' First-reading cell, S expects 1")
            else:
                cell = vigil[0][2]
                missing = [h for h in VIGIL_HEADINGS if h not in cell]
                empty = all(not c.strip() for c in vigil[0][3:6])
                print(f"     Easter Vigil cell: {len(cell)} characters; headings missing: {missing}; "
                      f"other reading cells empty: {empty}")
                if not 513 <= len(cell) <= 517 or missing or not empty:
                    diffs.append("the Easter Vigil cell differs from S Upstream facts 5")
    elif target.key == "vanderbilt/html_200" and ctype != "text/html":
        fails.append(f"content type {ctype!r}, expected text/html")
    elif kind == "bible_api" and target.status == 200:
        try:
            text = (response.json().get("text") or "").strip()
        except ValueError as exc:
            return body, [f"body is not JSON: {exc!r}"], diffs
        if not text:
            fails.append("no 'text' in the body")
    return body, fails, diffs


def record(names: list[str]) -> int:
    failed = 0
    wanted = [t for t in targets() if t.key in names]
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": USER_AGENT}) as client:
        for target in wanted:
            url = _full_url(target.url, target.params)
            try:
                response = client.get(target.url, params=target.params)
            except httpx.HTTPError as exc:
                print(f"FAIL {target.key}: {type(exc).__name__}: {exc}")
                failed += 1
                continue
            body, fails, diffs = check(target, response)
            if fails:
                print(f"FAIL {target.key}: {'; '.join(fails)}")
                failed += 1
                continue
            content_type = response.headers.get("content-type", "")
            write_fixture(target.key, target.ext, status=response.status_code,
                          content_type=content_type, url=url, body=body, synthetic=False)
            for note in diffs:
                print(f"DIFF {target.key}: {note}")
            if not diffs:
                print(f"OK   {target.key}: {response.status_code} {content_type} {len(body)} bytes")
    return failed


# --- hand-built fixtures (S Upstream facts 1-6) -----------------------------

JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
CSV_TYPE = "text/csv; charset=utf-8"

# date -> (season, groups of (first, psalm, second, gospel), alternatives)
LECTIO_SYNTHETIC = {
    "2025-12-24": ("Christmas", [("Isaiah 9:2-7", "Psalm 96", "Titus 2:11-14", "Luke 2:1-14 (15-20)")], []),
    "2025-12-25": ("Christmas", [("Isaiah 52:7-10", "Psalm 98", "Hebrews 1:1-4 (5-12)", "John 1:1-14")], []),
    "2026-02-18": ("Lent", [("Joel 2:1-2, 12-17", "Psalm 51:1-17", "2 Corinthians 5:20b-6:10",
                             "Matthew 6:1-6, 16-21")], [("first", "Isaiah 58:1-12")]),
    "2026-03-29": ("Lent", [("Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11",
                             "Matthew 26:14-27:66")], [("gospel", "Matthew 27:11-54")]),
    "2026-04-05": ("Easter", [("Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18")],
                   [("first", "Jeremiah 31:1-6"), ("gospel", "Matthew 28:1-10")]),
    "2026-05-14": ("Easter", [("Acts 1:1-11", "Psalm 47", "Ephesians 1:15-23", "Matthew 28:16-20")],
                   [("psalm", "Psalm 93")]),
    "2026-05-31": ("Ordinary Time", [
        ("Genesis 6:9-22; 7:24; 8:14-19", "Psalm 46", "Romans 1:16-17; 3:22b-28 (29-31)", "Matthew 7:21-29"),
        ("Genesis 1:1-2:4a", "Psalm 8", "2 Corinthians 13:11-13", "Matthew 28:16-20"),
    ], []),
    "2026-10-04": ("Ordinary Time", [("Exodus 20:1-4, 7-9, 12-20", "Psalm 19", "Philippians 3:4b-14",
                                      "Matthew 21:33-46")], [("first", "Isaiah 5:1-7")]),
    "2026-11-01": ("Ordinary Time", [("Joshua 3:7-17", "Psalm 107:1-7, 33-37", "1 Thessalonians 2:9-13",
                                      "Matthew 23:1-12")], [("first", "Micah 3:5-12")]),
}

VIGIL_CELL = " - ".join((
    "Old Testament Readings and Psalms",
    "Genesis 1:1-2:4a and Psalm 136:1-9, 23-26",
    "Genesis 7:1-5, 11-18; 8:6-18; 9:8-13 and Psalm 46",
    "Genesis 22:1-18 and Psalm 16",
    "Exodus 14:10-31; 15:20-21 and Exodus 15:1b-13, 17-18",
    "Isaiah 55:1-11 and Isaiah 12:2-6",
    "Baruch 3:9-15, 3:32-4:4 or Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19",
    "Ezekiel 36:24-28 and Psalm 42 and 43",
    "Ezekiel 37:1-14 and Psalm 143",
    "Zephaniah 3:14-20 and Psalm 98",
    "New Testament Reading and Psalm",
    "Romans 6:3-11 and Psalm 114",
    "Gospel",
    "Matthew 28:1-10",
))

# Year file -> rows in file order. The Nativity rows come after the January
# rows, as in the real 2025-26 file (S Upstream facts 4).
VANDERBILT_SYNTHETIC = {
    "2025-26": [
        ("Holy Name of Jesus", "Jan 01, 2026", "Numbers 6:22-27", "Psalm 8",
         "Galatians 4:4-7 or Philippians 2:5-11", "Luke 2:15-21"),
        ("New Year's Day", "Jan 01, 2026", "Ecclesiastes 3:1-13", "Psalm 8", "Revelation 21:1-6a",
         "Matthew 25:31-46"),
        ("Nativity of the Lord - Proper I", "Dec 24, 2025", "Isaiah 9:2-7", "Psalm 96", "Titus 2:11-14",
         "Luke 2:1-14 (15-20)"),
        ("Nativity of the Lord - Proper II", "Dec 25, 2025", "Isaiah 62:6-12", "Psalm 97", "Titus 3:4-7",
         "Luke 2:(1-7) 8-20"),
        ("Nativity of the Lord - Proper III", "Dec 25, 2025", "Isaiah 52:7-10", "Psalm 98",
         "Hebrews 1:1-4 (5-12)", "John 1:1-14"),
        ("Ash Wednesday", "Feb 18, 2026", "Joel 2:1-2, 12-17 or Isaiah 58:1-12", "Psalm 51:1-17",
         "2 Corinthians 5:20b-6:10", "Matthew 6:1-6, 16-21"),
        ("Liturgy of the Palms", "Mar 29, 2026", "", "Psalm 118:1-2, 19-29", "", "Matthew 21:1-11"),
        ("Liturgy of the Passion", "Mar 29, 2026", "Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11",
         "Matthew 26:14-27:66 or Matthew 27:11-54"),
        ("Good Friday", "Apr 03, 2026", "Isaiah 52:13-53:12", "Psalm 22",
         "Hebrews 10:16-25 or Hebrews 4:14-16; 5:7-9", "John 18:1-19:42"),
        ("Easter Vigil", "Apr 05, 2026", VIGIL_CELL, "", "", ""),
        ("Resurrection of the Lord", "Apr 05, 2026", "* Acts 10:34-43 or Jeremiah 31:1-6",
         "* Psalm 118:1-2, 14-24", "* Colossians 3:1-4 or Acts 10:34-43", "* John 20:1-18 or Matthew 28:1-10"),
        ("Easter Evening", "Apr 05, 2026", "* Isaiah 25:6-9", "* Psalm 114", "* 1 Corinthians 5:6b-8",
         "* Luke 24:13-49"),
        ("Ascension of the Lord", "May 14, 2026", "* Acts 1:1-11", "* Psalm 47 or Psalm 93",
         "* Ephesians 1:15-23", "* Luke 24:44-53"),
        ("Visitation", "May 31, 2026", "1 Samuel 2:1-10", "Psalm 113", "Romans 12:9-16b", "Luke 1:39-57"),
        ("Trinity Sunday", "May 31, 2026", "Genesis 1:1-2:4a", "Psalm 8", "2 Corinthians 13:11-13",
         "Matthew 28:16-20"),
        ("Proper 22 (27)", "Oct 04, 2026", "Exodus 20:1-4, 7-9, 12-20 Psalm 19", "Isaiah 5:1-7 Psalm 80:7-15",
         "Philippians 3:4b-14", "Matthew 21:33-46"),
        ("All Saints Day", "Nov 01, 2026", "Revelation 7:9-17", "Psalm 34:1-10, 22", "1 John 3:1-3",
         "Matthew 5:1-12"),
        ("Proper 26 (31)", "Nov 01, 2026", "Joshua 3:7-17 Psalm 107:1-7, 33-37", "Micah 3:5-12 Psalm 43",
         "1 Thessalonians 2:9-13", "Matthew 23:1-12"),
        ("Thanksgiving Day", "Nov 26, 2026", "Deuteronomy 8:7-18 Psalm 65", "", "2 Corinthians 9:6-15",
         "Luke 17:11-19"),
    ],
    "2026-27": [
        ("First Sunday of Advent", "Nov 29, 2026", "Isaiah 64:1-9", "Psalm 80:1-7, 17-19",
         "1 Corinthians 1:3-9", "Mark 13:24-37"),
    ],
    "2027-28": [
        ("First Sunday of Advent", "Nov 28, 2027", "Jeremiah 33:14-16", "Psalm 25:1-10",
         "1 Thessalonians 3:9-13", "Luke 21:25-36"),
    ],
}

YEAR_LETTER = {"2025-26": "A", "2026-27": "B", "2027-28": "C"}


def _lectio_payload(d: str) -> bytes:
    season, groups, alternatives = LECTIO_SYNTHETIC[d]
    readings = []
    for group in groups:
        readings += [{"type": t, "citation": c, "isAlternative": False}
                     for t, c in zip(("first", "psalm", "second", "gospel"), group)]
    readings += [{"type": t, "citation": c, "isAlternative": True} for t, c in alternatives]
    payload = {"data": {"date": d, "tradition": "rcl", "season": season, "year": "A",
                        "dayName": None, "readings": readings}}
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _vanderbilt_csv(year: str) -> bytes:
    out = io.StringIO()
    out.write(f"Revised Common Lectionary, Year {YEAR_LETTER[year]} ({year})\r\n")
    out.write("Vanderbilt Divinity Library\r\n\r\n")
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for row in VANDERBILT_SYNTHETIC[year]:
        writer.writerow(row + ("", ""))
    return out.getvalue().encode("utf-8")


def _bible_api_body(reference: str) -> bytes:
    text = f"Synthetic verse text for {reference}.\n"
    body = {"reference": reference, "text": text, "translation_id": "web",
            "translation_name": "World English Bible", "verses": []}
    return (json.dumps(body, indent=2) + "\n").encode("utf-8")


def synthetic(key: str) -> tuple[str, int, str, str, bytes]:
    """(ext, status, content_type, url, body) for one hand-built fixture."""
    kind, name = key.split("/", 1)
    target = {t.key: t for t in targets()}.get(key)
    url = _full_url(target.url, target.params) if target else ""
    if key == "lectio/html_200":
        body = b"<!DOCTYPE html>\n<html><head><title>Maintenance</title></head>" \
               b"<body><p>This site is down for maintenance.</p></body></html>\n"
        return ".html", 200, HTML_TYPE, _full_url(LECTIO_API_URL, {"date": "2026-03-29", "tradition": "rcl"}), body
    if key == "lectio/error_500":
        body = b'{"error": "Internal Server Error"}\n'
        return ".json", 500, JSON_TYPE, _full_url(LECTIO_API_URL, {"date": "2026-03-29", "tradition": "rcl"}), body
    if key == "esv/success":
        body = {"query": "John 3:16", "canonical": "John 3:16",
                "passages": ["For God so loved the world. (ESV)"]}
        return ".json", 200, JSON_TYPE, _full_url(ESV_API_BASE, {"q": "John 3:16"}), \
            (json.dumps(body, indent=2) + "\n").encode("utf-8")
    if key == "esv/empty":
        return ".json", 200, JSON_TYPE, _full_url(ESV_API_BASE, {"q": "Hezekiah 1:1"}), b'{"passages": []}\n'
    if kind == "lectio" and name in LECTIO_404_DATES:
        body = {"success": False, "error": {"code": "NOT_FOUND", "message": f"No readings found for {name}"}}
        return ".json", 404, JSON_TYPE, url, (json.dumps(body) + "\n").encode("utf-8")
    if kind == "lectio":
        return ".json", 200, JSON_TYPE, url, _lectio_payload(name)
    if kind == "vanderbilt" and name in VANDERBILT_SYNTHETIC:
        return ".csv", 200, CSV_TYPE, url, _vanderbilt_csv(name)
    if key == "vanderbilt/404":
        body = b"<!DOCTYPE html>\n<html><head><title>404 Not Found</title></head>" \
               b"<body><h1>Not Found</h1></body></html>\n"
        return ".html", 404, HTML_TYPE, url, body
    if key == "vanderbilt/html_200":
        body = b"<!DOCTYPE html>\n<html><head><title>Lectionary Calendar</title></head>" \
               b"<body><p>No calendar is available for this year.</p></body></html>\n"
        return ".html", 200, HTML_TYPE, url, body
    if key == "bible_api/isaiah_50_4-9":
        return ".json", 200, JSON_TYPE, url, _bible_api_body("Isaiah 50:4-9")
    if key == "bible_api/isaiah_50_4-9a":
        return ".json", 404, JSON_TYPE, url, b'{"error": "not found"}\n'
    if key == "bible_api/luke_2_1-14_15-20":
        return ".json", 200, JSON_TYPE, url, _bible_api_body("Luke 2:1-14, 15-20")
    raise KeyError(key)


def write_synthetic(names: list[str]) -> None:
    for key in names:
        ext, status, content_type, url, body = synthetic(key)
        write_fixture(key, ext, status=status, content_type=content_type, url=url, body=body, synthetic=True)
        print(f"SYN  {key}: {status} {content_type} {len(body)} bytes")


# --- README ------------------------------------------------------------------

README_HEAD = """# Upstream test fixtures

Recorded or hand-built answers from the four upstreams the lectionary and
passage code calls. Tests replay them with respx or `httpx.MockTransport`
(`backend/tests/upstream_fixtures.py`); no test touches the network.

Each fixture is a body file plus `<name>.meta.json`:
`{"status", "content_type", "url", "recorded_at", "synthetic"}`.
The Vanderbilt year files are trimmed to the fixture dates (preamble, header
and file order kept; each kept row verbatim).

`shared/` holds the hand-written Python/TypeScript cases (not recorded).

This file is rewritten by the recorder. To refresh the fixtures (network;
owner's permission; never in CI), from the repo root:

    .venv/bin/python backend/scripts/record_fixtures.py

and for any fixture it reports as FAIL, the hand-built version:

    .venv/bin/python backend/scripts/record_fixtures.py --synthetic <kind/name>

| Fixture | Status | Content-Type | Made |
|---|---|---|---|
"""

# Kept in the recorder so a re-recording never drops it (Task 5 checks for it).
README_SHARED = """
## shared/

- `shared/scripture_refs.json` is hand-written, not recorded, so it has no `.meta.json` sidecar. It is the authority for `backend/scripture_refs.py` and for 2b's `frontend/src/lib/scripture-refs.ts`: change a case here first, then both ports. `backend/tests/test_scripture_refs.py` runs it in pytest; 2b's `lib/scripture-refs.test.ts` reads it with `fs` from `../backend/tests/fixtures/shared/`. The top-level `"_about"` key documents each section's encoding. Slice 5a adds its `doc_readings` cases to the `resolve_readings` section.
"""


def write_readme() -> None:
    lines = [README_HEAD]
    for meta_path in sorted(FIXTURES.glob("*/*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        key = f"{meta_path.parent.name}/{meta_path.name.removesuffix('.meta.json')}"
        made = "synthetic" if meta["synthetic"] else f"recorded {meta['recorded_at'][:10]}"
        lines.append(f"| `{key}` | {meta['status']} | `{meta['content_type']}` | {made} |\n")
    lines.append(README_SHARED)
    (FIXTURES / "README.md").write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--only", nargs="+", metavar="KIND/NAME", help="record just these fixtures")
    group.add_argument("--synthetic", nargs="+", metavar="KIND/NAME",
                       help="write the hand-built version of these fixtures ('all' for every one)")
    group.add_argument("--list", action="store_true", help="print every fixture name")
    args = parser.parse_args(argv)
    names = all_names()
    if args.list:
        print("\n".join(names))
        return 0
    chosen = args.synthetic or args.only or []
    if chosen == ["all"]:
        chosen = names
    unknown = [n for n in chosen if n not in names]
    if unknown:
        parser.error(f"unknown fixture(s): {', '.join(unknown)}; see --list")
    if args.synthetic:
        write_synthetic(chosen)
        failed = 0
    else:
        recordable = [t.key for t in targets()]
        failed = record(chosen or recordable)
        write_synthetic([n for n in ALWAYS_SYNTHETIC if not chosen or n in chosen])
    write_readme()
    if failed:
        print(f"{failed} fixture(s) failed: write each with --synthetic <kind/name>.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
```

Notes for the reviewer:
- `check()` decides FAIL versus DIFF. FAIL means the tests cannot use the answer (unreachable, wrong status, not JSON where JSON is required, no CSV header, HTML where HTML is not expected), so nothing is written and Step 9 writes the hand-built fixture. DIFF means the answer is usable but differs from S's upstream facts (the Vanderbilt Content-Type, a row count, a Lectio gospel, the Vigil cell), so the recorded file is kept and the difference is reported.
- `trim_vanderbilt` groups physical lines by quote parity before parsing, so a quoted cell holding a line break stays inside one kept record, and it copies each kept record's lines unchanged (line endings included). The trimmed text is re-encoded with the response's own encoding, so the recorded Content-Type still describes the bytes.
- The bible-api URLs are the ones T9's fetcher will send: the lower-cased part quoted with `:`, `,` and `-` kept (`https://bible-api.com/isaiah%2050:4-9a?translation=web`).

- [ ] **Step 7 (agent): Run the tests again: they fail only because nothing is recorded yet**

```bash
.venv/bin/python -m pytest -q backend/tests/test_fixtures_recorder.py 2>&1 | tail -3
.venv/bin/python backend/scripts/record_fixtures.py --list | wc -l
.venv/bin/python backend/scripts/record_fixtures.py --synthetic lectio/nope; echo "exit=$?"
test ! -e backend/tests/fixtures && echo clean
```

**Expected:**
- `FAILED backend/tests/test_fixtures_recorder.py::test_recorder_dates_match_fixture_files`, `FAILED backend/tests/test_fixtures_recorder.py::test_every_fixture_has_status_and_content_type` and `2 failed in <t>s`. The full output shows why: the first fails at `assert recorder_dates == lectio_files == set(FIXTURE_DATES)` (there is no `backend/tests/fixtures/lectio/` yet), the second at `AssertionError: no fixtures: run backend/scripts/record_fixtures.py …`;
- `25` (`wc` pads it);
- two `usage: record_fixtures.py …` lines, then `record_fixtures.py: error: unknown fixture(s): lectio/nope; see --list`, then `exit=2`;
- `clean` (a refused run writes nothing).

- [ ] **Step 8 (agent; owner approved Q1b on 2026-09-28; network): Record the fixtures**

This makes exactly 21 GET requests: 13 to lectio-api.org, 5 to lectionary.library.vanderbilt.edu and 3 to bible-api.com, with the User-Agent `WorshipServiceBuilder/1.0`. It sends no key and never calls ESV. Run it once:

```bash
.venv/bin/python backend/scripts/record_fixtures.py; echo "exit=$?"
```

**Expected:**
- 21 lines that start with `OK` or `DIFF`, one or more per recorded fixture, in the order `lectio/2025-12-24` … `lectio/2026-11-26`, `vanderbilt/2025-26`, `vanderbilt/2026-27`, `vanderbilt/2027-28`, `vanderbilt/404`, `vanderbilt/html_200`, `bible_api/isaiah_50_4-9`, `bible_api/isaiah_50_4-9a`, `bible_api/luke_2_1-14_15-20` (a fixture with two differences prints two `DIFF` lines);
- before the `vanderbilt/2025-26` line, one line of the form `     Easter Vigil cell: <n> characters; headings missing: []; other reading cells empty: True` with `<n>` from 513 to 517;
- four lines `SYN  lectio/html_200: …`, `SYN  lectio/error_500: …`, `SYN  esv/success: …`, `SYN  esv/empty: …`;
- `exit=0`.

Copy every line the script printed into your notes for Step 13. If any line starts with `FAIL`, the last lines are `<k> fixture(s) failed: write each with --synthetic <kind/name>.` and `exit=1`: go to Step 9. Otherwise skip Step 9.

- [ ] **Step 9 (agent; only after a FAIL line): The synthetic fallback**

1. If every FAIL line names a network error (`ConnectError`, `ConnectTimeout`, `ReadTimeout`, `RemoteProtocolError`) or a 5xx or 429 status, the site may be briefly down. Retry just those fixtures once, naming each one as the FAIL line did, for example:

   ```bash
   .venv/bin/python backend/scripts/record_fixtures.py --only lectio/2026-03-29 vanderbilt/2025-26; echo "exit=$?"
   ```

   **Expected:** one `OK` or `DIFF` line per name and `exit=0`. The four always-synthetic fixtures are not rewritten by an `--only` run.
2. For every fixture that still fails, write its hand-built version, again naming each one:

   ```bash
   .venv/bin/python backend/scripts/record_fixtures.py --synthetic lectio/2026-03-29 vanderbilt/2025-26; echo "exit=$?"
   ```

   **Expected:** one `SYN  <kind/name>: <status> <content type> <n> bytes` line per name and `exit=0`. Its sidecar says `"synthetic": true`, and `backend/tests/fixtures/README.md` (rewritten by every run) says "synthetic" on its row.
3. If the machine has no network at all (every one of the 21 lines is a network FAIL), run `.venv/bin/python backend/scripts/record_fixtures.py --synthetic all` instead; it prints 25 `SYN` lines. The Easter Vigil and Content-Type facts then stay UNVERIFIED until T15's live check (outline Q1b-no path).
4. A FAIL on a site that answered (for example `FAIL lectio/2026-04-03: status 200, expected 404`) means the upstream no longer matches S "Upstream facts". Write the hand-built fixture as in 2, and report the FAIL line in Step 13; T15's live check looks at it again.

- [ ] **Step 10 (agent): Look at what was written**

```bash
ls backend/tests/fixtures/*/ | grep -c '\.meta\.json$'
grep -h '"content_type"' backend/tests/fixtures/*/*.meta.json | sort | uniq -c
grep -l '"synthetic": true' backend/tests/fixtures/*/*.meta.json
grep -rIn -E -i 'authorization:|api[_-]?key|set-cookie|bearer [a-z0-9._-]{8,}|token [a-z0-9]{20,}' backend/tests/fixtures || echo "no secrets"
cat backend/tests/fixtures/*/* | wc -c
cut -c1-160 backend/tests/fixtures/vanderbilt/2025-26.csv
```

**Expected:**
- `25`;
- a count per distinct Content-Type header value; the recorded Vanderbilt year files show the real header (S does not record it: A3, clarification 19);
- at least the four sidecars `backend/tests/fixtures/esv/empty.meta.json`, `backend/tests/fixtures/esv/success.meta.json`, `backend/tests/fixtures/lectio/error_500.meta.json` and `backend/tests/fixtures/lectio/html_200.meta.json`, plus one per fixture Step 9 wrote;
- `no secrets`;
- a byte total under `200000` (the Vanderbilt files are trimmed; a larger total means a year file was not);
- the file's preamble line(s), the header line containing `"Liturgical Date"` and `"Calendar Date"`, then only rows dated on the 13 fixture dates, in the file's own order (S says the Nativity rows come after the January rows).

A match inside a Vanderbilt `Prayer` cell is liturgical text, not a secret: report the line in Step 13 and go on.

If `no secrets` is not printed and any matching line is outside a `Prayer` cell, stop and report the matching lines: nothing is committed until the owner has seen them.

- [ ] **Step 11 (agent): Run the tests: they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_fixtures_recorder.py 2>&1 | tail -3
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `2 passed in <t>s`; then `800 passed, 9 skipped in <t>s`; then exactly:

```text
 M requirements-dev.txt
?? .claude/
?? backend/scripts/record_fixtures.py
?? backend/tests/fixtures/
?? backend/tests/test_fixtures_recorder.py
?? backend/tests/upstream_fixtures.py
```

- [ ] **Step 12 (agent): Commit**

```bash
git add requirements-dev.txt backend/scripts/record_fixtures.py backend/tests/upstream_fixtures.py backend/tests/test_fixtures_recorder.py backend/tests/fixtures/README.md backend/tests/fixtures/lectio backend/tests/fixtures/vanderbilt backend/tests/fixtures/bible_api backend/tests/fixtures/esv
git status --short
git commit -m 'Tests: upstream fixtures, their recorder and respx (F §5, S Testing "Fixtures")' -m "backend/tests/fixtures/README.md lists which fixtures were recorded (owner Q1b, 2026-09-28) and which are synthetic. respx>=0.22 joins requirements-dev.txt (owner Q1a)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

**Expected:** after `git add`, `git status --short` shows `M  requirements-dev.txt`, `A  ` lines for the three Python files, `A  backend/tests/fixtures/README.md` and the 50 fixture files, and `?? .claude/` as its only untracked line. The last line is `<sha> Tests: upstream fixtures, their recorder and respx (F §5, S Testing "Fixtures")`.

- [ ] **Step 13 (agent): Report the recording to the controller**

```bash
.venv/bin/python -c "import respx; print('respx', respx.__version__)"
grep -n 'Mar 29, 2026' backend/tests/fixtures/vanderbilt/2025-26.csv | cut -c1-220
.venv/bin/python -c "import json; d = json.load(open('backend/tests/fixtures/lectio/2026-03-29.json')); print([(r.get('type'), r.get('citation'), r.get('isAlternative')) for r in d['data']['readings']])"
```

Report, verbatim: every `DIFF`, `FAIL` and `SYN` line from Steps 8 and 9, the Easter Vigil line, the Content-Type counts and the synthetic list from Step 10, the respx version, and the output of the last two commands (the 2026-03-29 rows and readings, which T8's `test_palm_sunday_200_shape` asserts; clarification 41). How later tasks use the report:
- a `DIFF` on a Vanderbilt Content-Type: T7's `fetch_vanderbilt_year` must accept the recorded media type as well as `text/plain` and `text/csv` (clarification 19), and T12 records it in S;
- a `DIFF` on row counts, row names, a Lectio gospel or the Vigil cell: the tests that assert them (T6b `test_merge_table` and the Vigil test, T7, T8) assert the recorded equivalent, and T12 corrects S (clarification 41);
- a hand-built fixture: T15's live check is its first real-data check.
### Task 2: Outbound HTTP client and TTL cache (S New modules rows 1–2, Testing `test_cache.py` / `test_http_client.py`; F §2.7; AC3, AC13; 2a clarifications 24, 32, 36)

This task adds the two platform pieces every later backend task builds on. `integrations/http.py` holds the one outbound `httpx.Client` (F §2.7): the `WorshipServiceBuilder/1.0` User-Agent, redirects followed but only to https, a 5 s connect timeout and a read timeout chosen per call. It also sets the `httpx` and `httpcore` loggers to WARNING, so upstream URLs and query strings never reach the logs (clarification 32). `cache.py` holds `TTLCache`, which keeps values for `ttl_ok` and `CacheableFailure`s for `ttl_fail`, evicts the least recently used entry, and loads single-flight per key; any other loader exception is shared with that flight's waiters and never stored (clarification 36). Nothing calls either module yet: Task 3 builds `integrations/budget.py` in the package made here, Task 7 moves the lectionary fetchers onto `http.get` and `TTLCache`, and Task 9 does the same for passages. No route changes, so the OpenAPI files are not regenerated, and the frontend does not change.

**Files:**
- Create: `backend/integrations/__init__.py` (package marker)
- Create: `backend/integrations/http.py`
- Create: `backend/cache.py`
- Modify: `backend/tests/conftest.py` (insert after line 187, the `yield` that ends `_fresh_idempotency_store`: autouse `_fresh_http_client`)
- Modify: `backend/tests/test_no_streamlit_in_core.py:19-21` (the import list gains `cache` and `integrations.http`; no count change)
- Test: `backend/tests/test_http_client.py` (new, 7 tests)
- Test: `backend/tests/test_cache.py` (new, 9 tests)

**Interfaces:**
- Consumes:
  - `tests.conftest.FakeClock(start: float = 1000.0)` with `.now() -> float` and `.advance(seconds: float) -> None` (`backend/tests/conftest.py:14-24`).
  - The autouse `_no_network` guard (`backend/tests/conftest.py:195`), unchanged and active for every test here (AC13); every request in this task's tests is answered by `httpx.MockTransport`, and the https hook refuses plain http before any transport runs.
  - The deferred `sys.modules.get(...)` autouse pattern (`backend/tests/conftest.py:141-187`).
  - httpx 0.28.1 (in `.venv`; `backend/requirements.txt` already has `httpx>=0.25.0`): `httpx.Client`, `httpx.MockTransport`, `httpx.Timeout`, `httpx.UnsupportedProtocol` (an `httpx.TransportError`, so an `httpx.HTTPError`). httpx 0.28 runs `event_hooks["request"]` for every redirect hop (`httpx/_client.py`, `_send_handling_redirects`) and puts the per-call timeout in `request.extensions["timeout"]` as `{"connect", "read", "write", "pool"}`.
- Produces:
  - `integrations` package (`backend/integrations/__init__.py`). Task 3 adds `integrations/budget.py` to it; slice 3 adds `integrations/openai_client.py`.
  - `integrations.http.USER_AGENT = "WorshipServiceBuilder/1.0"`, `integrations.http.CONNECT_TIMEOUT = 5.0`, `integrations.http.DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)`.
  - `integrations.http.build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`: a client with the module's settings (default timeout, `follow_redirects=True`, the User-Agent header, the https-only request hook). Tests pass `transport=httpx.MockTransport(handler)`; None uses httpx's real transport. (Addition to the outline's interface; see the deviation note in Step 4.)
  - `integrations.http.get(url: str, *, params: Mapping[str, str] | None = None, headers: Mapping[str, str] | None = None, read_timeout: float) -> httpx.Response`. `read_timeout` is required (keyword-only). The call uses `httpx.Timeout(read_timeout, connect=5.0)`. A 4xx or 5xx is returned, not raised; transport problems raise `httpx.HTTPError` subclasses; a non-https URL (first hop or any redirect hop) raises `httpx.UnsupportedProtocol` whose message names only the scheme ("Only https upstream URLs are allowed, not 'http'."), never the URL or its query. Later users: Task 7 (`fetch_lectio`, `fetch_vanderbilt_year` with `read_timeout=10.0` / `15.0`), Task 9 (`fetch_part`, bible-api and ESV with `read_timeout=10.0`), slice 3.
  - `integrations.http.set_http_for_tests(client: httpx.Client | None) -> None`: routes `get()` through `client`; None restores the module's default client (built once at import).
  - Importing `integrations.http` sets `logging.getLogger("httpx")` and `logging.getLogger("httpcore")` to `logging.WARNING` (clarification 32).
  - `cache.CacheableFailure(Exception)`: Task 7's `vanderbilt_lectionary.SourceFailed(CacheableFailure)` subclasses it.
  - `cache.TTLCache(Generic[K, V])`, built as `TTLCache(maxsize: int, ttl_ok: float, ttl_fail: float, clock: Callable[[], float] = time.monotonic)`; `maxsize < 1` raises `ValueError`. Methods: `.get_or_load(key: K, loader: Callable[[], V]) -> V` and `.clear() -> None`. Contract (clarification 36):
    - an ok hit returns the stored value (`None` and `[]` are values; a private `cache._MISSING` sentinel marks "no value");
    - a failure hit re-raises the stored `CacheableFailure` (the same object, with a fresh traceback, so repeated hits never grow it);
    - a miss is single-flight per key; other keys load in parallel (no lock is held while a loader runs);
    - the leader's return value is stored for `ttl_ok`; a `CacheableFailure` it raises is stored for `ttl_fail` and re-raised to the leader and every waiter; any other exception is stored nowhere and is re-raised (the same object) to the leader and every waiter of that flight, and the next call runs the loader again;
    - an entry expires when `clock() >= stored_at + ttl`; a TTL of 0 stores nothing (Task 9's part cache uses `ttl_fail=0`);
    - `clear()` drops every stored entry; a load already in flight still stores its result. Modules that own a cache rebuild it as a new object in their `reset_for_tests` (Tasks 7 and 9, clarification 39).
    Later users: Task 7 (`_LECTIO`, `_VANDERBILT`), Task 9 (the bible-api part cache), slice 3.
  - Autouse fixture `_fresh_http_client` in `backend/tests/conftest.py`: calls `integrations.http.set_http_for_tests(None)` before every test when `integrations.http` is already in `sys.modules`. It is the anchor for the next autouse fixture (Task 3's `_fresh_rate_limits`).
  - `test_usecases_package_imports_no_fastapi_or_streamlit`'s import list ends with the string line `"cache, integrations.http; "` after this task; later tasks (Task 3: `token_bucket`, `integrations.budget`) extend that line.

Counts after this task: backend **816 passed, 9 skipped** (800 + 16: `test_http_client.py` 7, `test_cache.py` 9); frontend **221 passed in 34 files** (unchanged; not rerun here).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline origin/main..HEAD | wc -l
test ! -e backend/cache.py && test ! -e backend/integrations && echo "no T2 modules yet"
grep -n 'idempotency.reset_idempotency_for_tests()' backend/tests/conftest.py
grep -n 'db.ids, timezones; "' backend/tests/test_no_streamlit_in_core.py
.venv/bin/python -c "import httpx; print(httpx.__version__)"
.venv/bin/python -m pytest -q | tail -1
```

**Expected,** in order:
- exactly `?? .claude/` (Task 1 is committed);
- `2` or more, padded by `wc` (the plan commit and Task 1's commit);
- `no T2 modules yet`;
- `186:        idempotency.reset_idempotency_for_tests()` (line 187 is the `yield` this task inserts after);
- `21:    code = ("import sys, usecases, usecases.onboarding, domain_errors, db.ids, timezones; "`;
- `0.28.1`;
- `800 passed, 9 skipped in <t>s` (Task 1's count).

If the suite line differs, or a grep line number differs, stop and find why before editing (the replacement blocks below are anchored on these lines).

- [ ] **Step 2 (agent): Write the failing HTTP client tests, the autouse restore and the import gate**

Create `backend/tests/test_http_client.py`:

```python
"""integrations.http: the one outbound client (F §2.7; S New modules
"integrations/http.py", Testing "test_http_client.py"; 2a clarifications 24, 32).

Every test answers through httpx.MockTransport installed with
set_http_for_tests, so nothing leaves the process (the _no_network guard in
conftest.py stays active); the autouse _fresh_http_client fixture restores
the default client before the next test."""
import logging

import httpx
import pytest

from integrations import http


def _install(handler):
    """Answer get() with `handler` behind the module's own client settings;
    returns the list of requests the transport saw, in order."""
    seen = []

    def record(request):
        seen.append(request)
        return handler(request)

    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(record)))
    return seen


def test_user_agent_sent():
    seen = _install(lambda request: httpx.Response(200, text="ok"))
    r = http.get("https://api.example.test/v1/passage",
                 headers={"Authorization": "Token abc"}, read_timeout=10.0)
    assert r.status_code == 200 and r.text == "ok"
    assert http.USER_AGENT == "WorshipServiceBuilder/1.0"
    assert seen[0].headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    assert seen[0].headers["Authorization"] == "Token abc"   # per-call headers are added


def test_plain_http_refused():
    seen = _install(lambda request: httpx.Response(200, text="should not be reached"))
    with pytest.raises(httpx.UnsupportedProtocol) as refused:
        http.get("http://api.example.test/v1/passage", params={"q": "John 3:16"},
                 read_timeout=10.0)
    assert seen == []                                   # refused before the transport
    assert isinstance(refused.value, httpx.HTTPError)   # fetchers catch HTTPError (clarification 24)
    assert "John" not in str(refused.value) and "api.example.test" not in str(refused.value)


def test_redirect_to_http_refused():
    def handler(request):
        return httpx.Response(302, headers={"Location": "http://api.example.test/plain"})

    seen = _install(handler)
    with pytest.raises(httpx.UnsupportedProtocol):
        http.get("https://api.example.test/start", read_timeout=10.0)
    assert [str(request.url) for request in seen] == ["https://api.example.test/start"]


def test_https_redirect_followed():
    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(301, headers={"Location": "https://cdn.example.test/final"})
        return httpx.Response(200, text="done")

    seen = _install(handler)
    r = http.get("https://api.example.test/start", read_timeout=10.0)
    assert (r.status_code, r.text) == (200, "done")
    assert str(r.url) == "https://cdn.example.test/final"
    assert [str(request.url) for request in seen] == [
        "https://api.example.test/start", "https://cdn.example.test/final"]
    assert seen[1].headers["User-Agent"] == "WorshipServiceBuilder/1.0"


def test_per_call_read_timeout_connect_5s():
    seen = _install(lambda request: httpx.Response(200))
    http.get("https://lectio.example.test/day", read_timeout=15.0)
    http.get("https://lectio.example.test/day", read_timeout=10.0)
    assert [request.extensions["timeout"] for request in seen] == [
        {"connect": 5.0, "read": 15.0, "write": 15.0, "pool": 15.0},
        {"connect": 5.0, "read": 10.0, "write": 10.0, "pool": 10.0},
    ]
    assert http.DEFAULT_TIMEOUT == httpx.Timeout(10.0, connect=5.0)
    assert http.build_client().timeout == http.DEFAULT_TIMEOUT
    with pytest.raises(TypeError):
        http.get("https://lectio.example.test/day")     # read_timeout is required


def test_set_http_for_tests_swaps_and_none_restores():
    # A bare client (no https hook) makes the swap visible from outside.
    bare = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(204)))
    http.set_http_for_tests(bare)
    assert http.get("http://plain.example.test/", read_timeout=1.0).status_code == 204
    http.set_http_for_tests(None)
    with pytest.raises(httpx.UnsupportedProtocol):     # the default client's hook, before any I/O
        http.get("http://plain.example.test/", read_timeout=1.0)


def test_httpx_request_logs_silenced(caplog):
    caplog.set_level(logging.INFO)
    _install(lambda request: httpx.Response(200, json={"ok": True}))
    http.get("https://lectio.example.test/day", params={"date": "2026-03-29"}, read_timeout=10.0)
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    leaked = [record for record in caplog.records
              if record.name.split(".")[0] in ("httpx", "httpcore")]
    assert leaked == []
```

In `backend/tests/conftest.py`, replace this block (lines 184-187, the end of `_fresh_idempotency_store`):

```python
    idempotency = sys.modules.get("api.idempotency")
    if idempotency is not None:
        idempotency.reset_idempotency_for_tests()
    yield
```

with:

```python
    idempotency = sys.modules.get("api.idempotency")
    if idempotency is not None:
        idempotency.reset_idempotency_for_tests()
    yield


@pytest.fixture(autouse=True)
def _fresh_http_client():
    """integrations.http keeps one module-level client, and a test may swap in
    a MockTransport client with set_http_for_tests (slice 2, F §2.7). Every
    test starts with the default client restored, so a fake installed by an
    earlier test, or left there when it failed, never answers for this one.

    Restores only when integrations.http is already imported: a swapped
    client can exist only then (the deferred-import rule at the top of this
    file)."""
    import sys

    http = sys.modules.get("integrations.http")
    if http is not None:
        http.set_http_for_tests(None)
    yield
```

(The two blank lines before `# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---` stay as they are.)

In `backend/tests/test_no_streamlit_in_core.py`, replace lines 19-21:

```python
    # usecases (including usecases.onboarding), domain_errors, db.ids and
    # timezones are below the API layer (F §2.2).
    code = ("import sys, usecases, usecases.onboarding, domain_errors, db.ids, timezones; "
```

with:

```python
    # usecases (including usecases.onboarding), domain_errors, db.ids,
    # timezones and slice 2's platform modules (cache, integrations.http) are
    # below the API layer (F §2.2).
    code = ("import sys, usecases, usecases.onboarding, domain_errors, db.ids, timezones, "
            "cache, integrations.http; "
```

(`cache` is listed before `integrations.http`, so until Step 8 the subprocess fails on `cache` even after Step 4 creates the package.)

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_http_client.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_http_client.py 2>&1 | grep -m1 '^E '
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | grep -m1 ModuleNotFoundError
```

**Expected:**
- `ERROR backend/tests/test_http_client.py`, `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in <t>s`;
- `E   ModuleNotFoundError: No module named 'integrations'`;
- `=========================== short test summary info ============================`, `FAILED backend/tests/test_no_streamlit_in_core.py::test_usecases_package_imports_no_fastapi_or_streamlit`, `1 failed, 2 passed in <t>s`;
- `E         ModuleNotFoundError: No module named 'cache'` (the subprocess's stderr in the assert message).

- [ ] **Step 4 (agent): Create the `integrations` package and `integrations/http.py`**

Create `backend/integrations/__init__.py`:

```python
"""Outbound calls to other services (F §2.7): integrations.http (slice 2),
integrations.budget (slice 2), integrations.openai_client (slice 3).

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py)."""
```

Create `backend/integrations/http.py`:

```python
"""The one outbound HTTP client (F §2.7; S New modules "integrations/http.py").

Every upstream call the new app makes (Lectio, Vanderbilt, bible-api, ESV)
goes through get(). One module-level httpx.Client carries the settings F §2.7
fixes, so no caller picks its own:
- User-Agent "WorshipServiceBuilder/1.0";
- follow_redirects=True, but only to https: a request event hook refuses any
  non-https URL, and httpx runs that hook for every redirect hop too;
- connect timeout 5 s; the read timeout is chosen per call (S Timeouts).

A refused URL raises httpx.UnsupportedProtocol, an httpx.HTTPError, so a
fetcher that catches httpx.HTTPError reports it as an upstream failure rather
than a 500 (2a clarification 24). The message names the scheme only, never
the URL or its query string.

httpx logs every request's full URL, query string included, at INFO, and the
API's root logger runs at INFO (api/logging_config.py). Importing this module
sets the "httpx" and "httpcore" loggers to WARNING, so upstream URLs, dates
and ESV queries never reach the logs (F §2.5; 2a clarification 32).

Tests swap the client with set_http_for_tests(build_client(transport=...));
set_http_for_tests(None) restores the default, and an autouse fixture in
tests/conftest.py does that before every test.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
import logging
from typing import Mapping

import httpx

USER_AGENT = "WorshipServiceBuilder/1.0"
CONNECT_TIMEOUT = 5.0
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=CONNECT_TIMEOUT)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


def _require_https(request: httpx.Request) -> None:
    """Request event hook: refuse any URL that is not https, redirect hops included."""
    if request.url.scheme != "https":
        raise httpx.UnsupportedProtocol(
            f"Only https upstream URLs are allowed, not {request.url.scheme!r}.",
            request=request,
        )


def build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    """A client with this module's settings. `transport` is for tests
    (httpx.MockTransport); None uses httpx's real transport."""
    return httpx.Client(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        event_hooks={"request": [_require_https]},
        transport=transport,
    )


_DEFAULT_CLIENT = build_client()
_client = _DEFAULT_CLIENT


def get(url: str, *, params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None, read_timeout: float) -> httpx.Response:
    """GET `url` with the shared client; `read_timeout` seconds to read, 5 s to connect.

    Raises httpx.HTTPError subclasses only for transport problems (a timeout,
    a refused URL, a connection error); a 4xx or 5xx is returned, not raised,
    so each fetcher decides what a status means."""
    return _client.get(
        url,
        params=params,
        headers=headers,
        timeout=httpx.Timeout(read_timeout, connect=CONNECT_TIMEOUT),
    )


def set_http_for_tests(client: httpx.Client | None) -> None:
    """Route get() through `client`; None restores the module's default client."""
    global _client
    _client = _DEFAULT_CLIENT if client is None else client
```

Notes for the reviewer:
- `build_client(transport=None)` is public although the outline lists only `get` and `set_http_for_tests`. The tests need the module's own settings (User-Agent, https hook, redirects, timeout) in front of a `MockTransport`; a bare `httpx.Client(transport=...)` would test httpx, not this module. It is additive. (Deviation from the outline's interface list, owner decision 1.)
- The hook raises `httpx.UnsupportedProtocol`, an `httpx.HTTPError`, so Task 7's and Task 9's fetchers, which catch only `httpx.HTTPError` (clarification 18), report a refused redirect as an upstream failure, not a 500 (clarification 24). Its message names the scheme only, because an exception message can end up in a log line.
- The default client is built once at import and never closed; `set_http_for_tests(None)` puts that same object back. respx (Tasks 7 and 9) patches httpx's transport layer globally, so it intercepts the default client too, including calls made from pool threads.

- [ ] **Step 5 (agent): Run the HTTP client tests to verify they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_http_client.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | grep -m1 ModuleNotFoundError
```

**Expected:** `7 passed in <t>s`; then `E         ModuleNotFoundError: No module named 'cache'` (the import gate waits for Step 8).

- [ ] **Step 6 (agent): Write the failing cache tests**

Create `backend/tests/test_cache.py`:

```python
"""cache.TTLCache: TTLs for values and CacheableFailures, LRU, single-flight
per key, uncached exceptions (F §2.7; S New modules "cache.py", Testing
"test_cache.py"; 2a clarification 36).

Threaded tests gate the loader on a threading.Event (never time.sleep), set
it in `finally`, and join their threads before returning."""
import threading
import traceback

import pytest

from cache import CacheableFailure, TTLCache
from tests.conftest import FakeClock


class Down(CacheableFailure):
    """A failure the cache stores for ttl_fail."""


class Boom(Exception):
    """An unexpected loader error: never stored."""


def _counting(result):
    """A loader returning `result` (or raising it, if it is an exception) and
    counting its calls in .calls."""
    def loader():
        loader.calls += 1
        if isinstance(result, BaseException):
            raise result
        return result
    loader.calls = 0
    return loader


def _run(results, name, cache, key, loader):
    """Thread body: store get_or_load's value, or the exception it raised."""
    try:
        results[name] = cache.get_or_load(key, loader)
    except BaseException as exc:   # the test asserts on it
        results[name] = exc


def test_ok_value_cached_until_ttl_ok():
    clock = FakeClock()
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=clock.now)
    first, second = _counting("v1"), _counting("v2")
    assert cache.get_or_load("k", first) == "v1"
    clock.advance(99.5)
    assert cache.get_or_load("k", second) == "v1"      # still fresh
    assert (first.calls, second.calls) == (1, 0)
    clock.advance(0.5)                                  # exactly ttl_ok after the store
    assert cache.get_or_load("k", second) == "v2"
    assert second.calls == 1


def test_none_and_empty_values_cached():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    none_loader, empty_loader = _counting(None), _counting([])
    for _ in range(3):
        assert cache.get_or_load("none", none_loader) is None
        assert cache.get_or_load("empty", empty_loader) == []
    assert (none_loader.calls, empty_loader.calls) == (1, 1)


def test_cacheable_failure_cached_for_ttl_fail_and_reraised():
    clock = FakeClock()
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=clock.now)
    failure = Down("upstream 500")
    failing, fine = _counting(failure), _counting("ok")
    with pytest.raises(Down) as first:
        cache.get_or_load("k", failing)
    assert first.value is failure
    depths = []
    for _ in range(2):
        clock.advance(4)                                # 4 s, then 8 s: inside ttl_fail
        with pytest.raises(Down) as hit:
            cache.get_or_load("k", fine)
        assert hit.value is failure
        depths.append(len(traceback.extract_tb(hit.value.__traceback__)))
    assert depths[0] == depths[1]                       # a hit never grows the traceback
    assert (failing.calls, fine.calls) == (1, 0)
    clock.advance(2)                                    # 10 s: ttl_fail is over
    assert cache.get_or_load("k", fine) == "ok"
    assert fine.calls == 1

    # ttl_fail=0 (the bible-api part cache) never stores a failure.
    uncached = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=0, clock=clock.now)
    for _ in range(2):
        with pytest.raises(Down):
            uncached.get_or_load("k", failing)
    assert failing.calls == 3


def test_other_exception_not_cached():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    boom, fine = _counting(Boom("bug")), _counting("fine")
    with pytest.raises(Boom):
        cache.get_or_load("k", boom)
    assert cache.get_or_load("k", fine) == "fine"       # the next call loads again
    assert (boom.calls, fine.calls) == (1, 1)


def test_lru_evicts_least_recent():
    with pytest.raises(ValueError):
        TTLCache(maxsize=0, ttl_ok=100, ttl_fail=10)
    cache = TTLCache(maxsize=2, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    cache.get_or_load("a", _counting("A"))
    cache.get_or_load("b", _counting("B"))
    cache.get_or_load("a", _counting("unused"))         # a hit makes "a" most recent
    cache.get_or_load("c", _counting("C"))              # evicts "b"
    kept, evicted = _counting("A2"), _counting("B2")
    assert cache.get_or_load("a", kept) == "A"
    assert cache.get_or_load("b", evicted) == "B2"
    assert (kept.calls, evicted.calls) == (0, 1)


def test_single_flight_one_loader_per_key():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    started, release = threading.Event(), threading.Event()

    def slow():
        slow.calls += 1
        started.set()
        release.wait(5)
        return "v"
    slow.calls = 0
    second = _counting("second loader")
    results = {}
    leader = threading.Thread(target=_run, args=(results, "leader", cache, "k", slow))
    waiter = threading.Thread(target=_run, args=(results, "waiter", cache, "k", second))
    try:
        leader.start()
        assert started.wait(5)
        waiter.start()
        waiter.join(0.2)
        assert waiter.is_alive()                        # waiting on the leader's flight
    finally:
        release.set()
        leader.join(5)
        waiter.join(5)
    assert results == {"leader": "v", "waiter": "v"}
    assert (slow.calls, second.calls) == (1, 0)


def test_different_keys_load_concurrently():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    started, release = threading.Event(), threading.Event()

    def slow():
        started.set()
        release.wait(5)
        return "A"
    results = {}
    a = threading.Thread(target=_run, args=(results, "a", cache, "a", slow))
    b = threading.Thread(target=_run, args=(results, "b", cache, "b", _counting("B")))
    try:
        a.start()
        assert started.wait(5)
        b.start()
        b.join(5)
        assert not b.is_alive()                         # "b" did not wait for "a"
        assert results == {"b": "B"}
    finally:
        release.set()
        a.join(5)
        b.join(5)
    assert results == {"a": "A", "b": "B"}


def test_uncached_exception_shared_by_waiters_then_retried():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    started, release = threading.Event(), threading.Event()

    def slow():
        slow.calls += 1
        started.set()
        release.wait(5)
        raise Boom("bug")
    slow.calls = 0
    second = _counting("second loader")
    results = {}
    leader = threading.Thread(target=_run, args=(results, "leader", cache, "k", slow))
    waiter = threading.Thread(target=_run, args=(results, "waiter", cache, "k", second))
    try:
        leader.start()
        assert started.wait(5)
        waiter.start()
        waiter.join(0.2)
        assert waiter.is_alive()                        # waiting on the leader's flight
    finally:
        release.set()
        leader.join(5)
        waiter.join(5)
    assert isinstance(results["leader"], Boom)
    assert results["waiter"] is results["leader"]       # the leader's exception, shared
    assert (slow.calls, second.calls) == (1, 0)
    third = _counting("third")
    assert cache.get_or_load("k", third) == "third"     # nothing was stored
    assert third.calls == 1


def test_clear():
    cache = TTLCache(maxsize=4, ttl_ok=100, ttl_fail=10, clock=FakeClock().now)
    cache.get_or_load("a", _counting("A"))
    with pytest.raises(Down):
        cache.get_or_load("b", _counting(Down("down")))
    cache.clear()
    again_a, again_b = _counting("A2"), _counting("B2")
    assert cache.get_or_load("a", again_a) == "A2"
    assert cache.get_or_load("b", again_b) == "B2"
    assert (again_a.calls, again_b.calls) == (1, 1)
```

The threaded tests gate every loader on a `threading.Event` and set it in `finally`, so a failing assertion never leaves a thread blocked; they join their threads before returning. `waiter.join(0.2)` followed by `assert waiter.is_alive()` is a bounded check that the waiter is blocked on the leader's flight (without single-flight, the waiter would run its own non-blocking loader and finish at once); it is not a sleep, and the loader never waits on time.

- [ ] **Step 7 (agent): Run the cache tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_cache.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_cache.py 2>&1 | grep -m1 '^E '
```

**Expected:** `ERROR backend/tests/test_cache.py`, `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in <t>s`; then `E   ModuleNotFoundError: No module named 'cache'`.

- [ ] **Step 8 (agent): Create `backend/cache.py`**

```python
"""TTL cache with single-flight loading (F §2.7; S New modules "cache.py").

TTLCache(maxsize, ttl_ok, ttl_fail, clock) is thread-safe, evicts the least
recently used entry beyond `maxsize`, and loads through get_or_load(key,
loader):
- an ok hit returns the stored value (None and [] are values too);
- a failure hit re-raises the stored CacheableFailure;
- a miss is single-flight per key: one caller (the leader) runs the loader
  while later callers for the same key wait for it; other keys load in
  parallel. The leader's return value is stored for ttl_ok seconds. A
  CacheableFailure it raises is stored for ttl_fail seconds and re-raised.
  Any other exception is stored nowhere: it is re-raised to the leader and to
  every waiter of that flight, and the next call runs the loader again
  (S :888; 2a clarification 36).
A TTL of 0 stores nothing (the bible-api part cache uses ttl_fail=0).

An error is never stored as an empty success (F §2.7): a loader reports a
failure worth remembering by raising a CacheableFailure subclass
(vanderbilt_lectionary.SourceFailed, slice 2).

A loader must not call get_or_load for its own key (it would wait on itself).
clear() drops every stored entry; a load already in flight still stores its
result when it finishes. Modules that own a cache rebuild it as a new object
in their reset_for_tests (2a clarification 39).

Not api/identity_cache.py: that cache compares the incoming profile before it
decides to load, which get_or_load does not fit.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
import threading
import time
from collections import OrderedDict
from typing import Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")

_MISSING = object()   # "no value": lets None and [] be stored as values


class CacheableFailure(Exception):
    """A loader failure to remember for the cache's ttl_fail (for example an
    upstream answering 500), so the upstream is not asked again at once."""


class _Flight:
    """One in-progress load of one key; waiters block on `done`."""

    __slots__ = ("done", "value", "error")

    def __init__(self) -> None:
        self.done = threading.Event()
        self.value: object = _MISSING
        self.error: BaseException | None = None


class TTLCache(Generic[K, V]):
    """Thread-safe LRU cache with separate TTLs for values and CacheableFailures."""

    def __init__(self, maxsize: int, ttl_ok: float, ttl_fail: float,
                 clock: Callable[[], float] = time.monotonic):
        if maxsize < 1:
            raise ValueError("maxsize must be >= 1")
        self._maxsize = maxsize
        self._ttl_ok = ttl_ok
        self._ttl_fail = ttl_fail
        self._clock = clock
        self._lock = threading.Lock()
        # key -> (expires_at, value, failure); failure is None for a stored value
        self._entries: "OrderedDict[K, tuple[float, object, CacheableFailure | None]]" = OrderedDict()
        self._flights: dict[K, _Flight] = {}

    def get_or_load(self, key: K, loader: Callable[[], V]) -> V:
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None:
                expires_at, value, failure = entry
                if self._clock() < expires_at:
                    self._entries.move_to_end(key)
                    if failure is not None:
                        # A fresh traceback each time: re-raising the stored
                        # object would otherwise grow its traceback on every hit.
                        raise failure.with_traceback(None)
                    return value  # type: ignore[return-value]
                del self._entries[key]
            flight = self._flights.get(key)
            leader = flight is None
            if leader:
                flight = _Flight()
                self._flights[key] = flight

        if not leader:
            flight.done.wait()
            if flight.error is not None:
                raise flight.error
            return flight.value  # type: ignore[return-value]

        try:
            value = loader()
        except CacheableFailure as failure:
            self._settle(key, flight, error=failure, ttl=self._ttl_fail)
            raise
        except BaseException as exc:
            self._settle(key, flight, error=exc, ttl=0)
            raise
        self._settle(key, flight, value=value, ttl=self._ttl_ok)
        return value

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _settle(self, key: K, flight: _Flight, *, value: object = _MISSING,
                error: BaseException | None = None, ttl: float) -> None:
        """Record the leader's outcome, store it when ttl > 0, end the flight."""
        flight.value = value
        flight.error = error
        with self._lock:
            if ttl > 0:
                self._entries[key] = (self._clock() + ttl, value, error)
                self._entries.move_to_end(key)
                while len(self._entries) > self._maxsize:
                    self._entries.popitem(last=False)
            if self._flights.get(key) is flight:
                del self._flights[key]
        flight.done.set()
```

Notes for the reviewer:
- A stored failure is re-raised with `failure.with_traceback(None)`. Re-raising the same exception object prepends the raising frames to its `__traceback__` each time, so a failure hit 120 times inside its 5-minute `ttl_fail` would otherwise pin a growing chain of frames. `test_cacheable_failure_cached_for_ttl_fail_and_reraised` checks two hits have the same traceback depth. (Owner decision 1; S silent.)
- A TTL of 0 stores nothing rather than storing an already-expired entry, so Task 9's part cache (`ttl_fail=0`) never spends an LRU slot on a failure. (Owner decision 1; matches the outline's "0 (transient failures never cached)".)
- The leader records its outcome on the flight before `done.set()`, and removes the flight under the lock in the same step that stores the entry, so a caller arriving after that sees either the stored entry or (for an uncached exception) no entry and no flight, and runs the loader again (S :888).

- [ ] **Step 9 (agent): Run the three files and the whole suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_cache.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_http_client.py backend/tests/test_cache.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `9 passed in <t>s`; then `19 passed in <t>s` (7 + 9 + 3); then `816 passed, 9 skipped in <t>s` (800 + 16); then exactly:

```
 M backend/tests/conftest.py
 M backend/tests/test_no_streamlit_in_core.py
?? .claude/
?? backend/cache.py
?? backend/integrations/
?? backend/tests/test_cache.py
?? backend/tests/test_http_client.py
```

If the suite line is not `816 passed, 9 skipped`, stop and find why (the plan's rule: each task's delta equals its listed tests).

- [ ] **Step 10 (agent): Commit**

```bash
git add backend/integrations/__init__.py backend/integrations/http.py backend/cache.py \
        backend/tests/test_http_client.py backend/tests/test_cache.py \
        backend/tests/conftest.py backend/tests/test_no_streamlit_in_core.py
git commit -m "Platform: outbound HTTP client and TTL cache (F §2.7, S New modules)

integrations.http holds the one outbound httpx.Client: User-Agent
WorshipServiceBuilder/1.0, redirects followed but only to https (a
request hook that httpx runs on every hop raises UnsupportedProtocol,
an HTTPError), connect 5 s and a read timeout chosen per call. Importing
it sets the httpx and httpcore loggers to WARNING, so upstream URLs and
query strings never reach the logs (2a clarification 32).

cache.TTLCache stores values for ttl_ok and CacheableFailures for
ttl_fail, evicts the least recently used entry, and loads single-flight
per key; any other loader exception is shared with the flight's waiters
and never stored, so the next call loads again (2a clarification 36).
An autouse fixture restores the default HTTP client before each test,
and the no-FastAPI import gate covers both modules.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> Platform: outbound HTTP client and TTL cache (F §2.7, S New modules)`; then `git status --short` lists only `?? .claude/` (`backend/integrations/__pycache__/` is ignored by `.gitignore`'s `__pycache__/`).
### Task 3: Token bucket, rate limiter and upstream budgets (S Rate-limit buckets, Upstream budgets; F §1.8; AC7 unit half, AC13; clarifications 17, 25, 33, 35, 37)

This task adds the three pieces every later 429 and every upstream call goes through. No route uses them yet: T4 wires
`church_create`, T8 `lectionary`, T9 the budgets and T10 `scripture`.

- `backend/token_bucket.py` is pure arithmetic on an injected clock. Refill is continuous. Rates are applied as
  `capacity / per_seconds` and waits as `missing * per_seconds / capacity`, so whole-number limits give exact waits
  (20 s for one `church_create` token, 2.5 s for `lectionary`, 5 s for `scripture`, 216 s for the `ai` church rule).
  `wait_for(n)` (clarification 25) lets an owner check every rule before it takes from any. Elapsed time is clamped at 0
  (clarification 37).
- `backend/api/ratelimit.py` keeps a `RateLimiter(clock)` (S's name) with one lock. Its buckets are keyed by
  `(bucket, rule index, scope id)` rather than F's `(bucket, scope_id)`, so the `ai` user rule and church rule can never
  share an entry. `consume` checks every rule, then takes from every rule, all under the lock. When a rule is short it
  computes `n = max(1, ceil(max wait))` once and raises `RateLimited(MESSAGE.format(n=n), retry_after_seconds=n)`, so the
  message, the header and `details` agree (clarification 17). It raises `KeyError` for an unknown bucket, and
  `ValueError` for a church rule with no `church_id`, for `cost < 1` (clarification 33) and for a cost above a rule's
  capacity. `rate_limit(name)` looks the name up when it is called (clarification 35). Idle entries are swept at most once
  per 60 s of the clock, and only full buckets are dropped, so pruning never gives anyone tokens.
- `backend/integrations/budget.py` holds the process-wide `bible_api` and `esv` budgets on the same `TokenBucket`, behind
  one lock. `try_acquire` never waits and is all-or-nothing across the ESV rules. It imports no FastAPI, so
  `scripture_fetcher.py` can call it (T9).
- Test hooks (clarification 37): each module's `set_clock_for_tests(clock)` drops every bucket, so every caller starts
  full, and `reset_for_tests()` does the same on `time.monotonic`. The conftest gets an autouse reset for both modules
  (the deferred `sys.modules.get` pattern) and two fixtures, `limiter_clock` and `budget_clock`. Each returns a
  `FakeClock` that nothing but the test moves.

Test counts: `test_ratelimit.py` has 14 tests and `test_budget.py` has 7, so the suite goes from 816 to 837 (9 skipped).
The budget table check and the budget hook checks are folded into `test_unknown_upstream_raises` and
`test_bible_api_fifteen_then_sixteenth_fails_then_refills`, so the count stays the outline's 21. The frontend is untouched
(221 in 34 files).

**Files:**
- Create: `backend/token_bucket.py`, `backend/api/ratelimit.py`, `backend/integrations/budget.py`,
  `backend/tests/test_ratelimit.py` (14 tests), `backend/tests/test_budget.py` (7 tests)
- Modify: `backend/tests/conftest.py` (a new block above the `# --- slice 1: network-free tests …` comment:
  autouse `_fresh_rate_limits`, fixtures `limiter_clock` and `budget_clock`)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (`test_usecases_package_imports_no_fastapi_or_streamlit`: the
  import string gains `token_bucket, integrations.budget` after T2's `cache, integrations.http`)
- Test: `backend/tests/test_ratelimit.py`, `backend/tests/test_budget.py`, `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes:
  - T2: the package `backend/integrations/` (`__init__.py`). T2's `_fresh_http_client` autouse fixture and its
    `test_no_streamlit_in_core.py` import-list edit (`cache, integrations.http`) are already in.
  - Slice 1: `domain_errors.RateLimited(message: str, *, retry_after_seconds: float)`, a 429 `rate_limited` that stores
    `max(1, ceil(n))` in `.retry_after_seconds` and in `details == {"retry_after_seconds": n}`
    (`backend/domain_errors.py:133-147`). `api.errors.domain_error_response` adds `Retry-After`
    (`backend/api/errors.py:144-149`). `api.errors.ApiError` (`:38`) is the class the limiter must never raise.
  - Slice 1: `api.deps.get_current_user(...) -> CurrentUser` (`.id: uuid.UUID`),
    `api.deps.require_church(...) -> ActiveChurch` (`.id: uuid.UUID`), and `api.deps.get_verifier`.
  - Tests: `tests.conftest.FakeClock(start=1000.0)` (`.now()`, `.advance(seconds)`, `.value`), `tmp_db`,
    `tests.jwt_helpers.{ISSUER, SIGNING_KEY, make_token}`, `api.security.TokenVerifier`,
    `api.settings.get_settings.cache_clear()` (the CORS pattern of `test_api_app.py:73-84`).
- Produces:
  - `token_bucket.TokenBucket(capacity: float, per_seconds: float, clock: Callable[[], float])`:
    - `.wait_for(n: float = 1) -> float`: 0.0, or the seconds until n tokens are available; takes none.
    - `.try_take(n: float = 1) -> float`: takes n and returns 0.0, or takes nothing and returns the wait.
    - `.is_full() -> bool`.
    - `.capacity: float`, `.per_seconds: float`.
    - `ValueError` for `n <= 0` or `n > capacity`, and for a non-positive `capacity` or `per_seconds`.
  - `api.ratelimit`:
    - `Rule(scope: Literal["user", "church"], capacity: int, per_seconds: float)`, a frozen dataclass.
    - `BUCKETS: dict[str, tuple[Rule, ...]]` = `lectionary` 120/300, `scripture` 60/300, `church_create` 3/60,
      `ai` 40/600 per user and 400/86 400 per church, `email` 10/3 600.
    - `MESSAGE = "Too many requests. Try again in {n} seconds."`, `PRUNE_EVERY_SECONDS = 60.0`.
    - `RateLimiter(clock: Callable[[], float] = time.monotonic)`, with `.consume(...)` (same signature as below),
      `.clock` and `len(limiter)` (the number of buckets held).
    - `consume(bucket: str, *, user_id: uuid.UUID, church_id: uuid.UUID | None = None, cost: int = 1) -> None`. T10's
      route calls `ratelimit.consume("scripture", user_id=user.id, cost=len(plan.parts))`. Slices 3/4/5b and PR #7/#8
      use `lambda n=1: consume("ai", user_id=u, church_id=c, cost=n)`.
    - `rate_limit(name: str) -> Callable[..., None]`, a FastAPI dependency that charges one token.
      - Every bucket without a church rule gets `user_rate_limit(user: CurrentUser = Depends(get_current_user))`.
      - `ai` gets `church_rate_limit(user = Depends(get_current_user), church: ActiveChurch = Depends(require_church))`.
      - T4 uses `rl: None = Depends(rate_limit("church_create"))` and T8 `_rl: None = Depends(rate_limit("lectionary"))`.
      - An unknown name raises `KeyError` when `rate_limit` is called.
    - `reset_for_tests() -> None` and `set_clock_for_tests(clock: Callable[[], float]) -> None`. `_limiter` is read on
      every call.
  - `integrations.budget`:
    - `Upstream = Literal["bible_api", "esv"]`.
    - `BUDGETS: dict[str, tuple[tuple[int, float], ...]]`, each rule `(capacity, per_seconds)`:
      `{"bible_api": ((15, 30.0),), "esv": ((60, 60.0), (1_000, 3_600.0), (5_000, 86_400.0))}`.
    - `try_acquire(upstream: Upstream) -> bool`, with `KeyError` for an unknown upstream. T9 calls it as
      `budget.try_acquire(...)` on the imported module (`from integrations import budget`), so T10's
      `monkeypatch.setattr(budget, "try_acquire", lambda u: True)` takes effect.
    - `reset_for_tests() -> None`, `set_clock_for_tests(clock: Callable[[], float]) -> None`, and the module attribute
      `_clock`.
  - `backend/tests/conftest.py`:
    - `_fresh_rate_limits`, autouse. It runs `reset_for_tests()` on `api.ratelimit` and on `integrations.budget`, each
      only when that module is already imported.
    - `limiter_clock -> FakeClock`, used by T4, T8 and T10.
    - `budget_clock -> FakeClock`, used by T9 and T10.
    - Both clock fixtures are function-scoped and return the clock. The autouse reset runs first, and the next test's
      reset restores `time.monotonic`.

- [ ] **Step 1 (agent): Check that T2 is in**

```bash
git log --oneline -3
ls backend/integrations/
grep -n "def _fresh_http_client\|# --- slice 1: network-free" backend/tests/conftest.py
grep -n 'cache, integrations.http; "' backend/tests/test_no_streamlit_in_core.py
ls backend/token_bucket.py backend/api/ratelimit.py backend/integrations/budget.py 2>&1 | grep -c "No such file"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- T2's commit on top.
- `__init__.py` and `http.py` (plus `__pycache__`) in `backend/integrations/`.
- Two conftest lines: `def _fresh_http_client` and `# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---`.
- One import-list line `            "cache, integrations.http; "` (the second line of T2's two-line import list).
- `3` (none of this task's modules exist yet).
- `816 passed, 9 skipped in <t>s`.

If the count differs, stop and ask.

- [ ] **Step 2 (agent): Add the conftest resets and clock fixtures**

In `backend/tests/conftest.py`, insert this block immediately above the line
`# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---`. That line is unique; T2's
`_fresh_http_client` stays wherever T2 put it. End the block with two blank lines before that comment.

```python
# --- slice 2a: rate limits and upstream budgets (F §1.8; S "Rate-limit buckets", "Upstream budgets") ---

@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """The limiter's buckets and the upstream budgets are process-wide, and a
    test's users or parts must never spend another test's tokens (slice 2a).
    Both forget every spent token and go back on time.monotonic.

    Resets only a module already imported: its state can exist only then (the
    deferred-import rule at the top of this file)."""
    import sys

    for name in ("api.ratelimit", "integrations.budget"):
        module = sys.modules.get(name)
        if module is not None:
            module.reset_for_tests()
    yield


@pytest.fixture
def limiter_clock():
    """Put api.ratelimit on a FakeClock (every caller starts full) and return the clock.

    Nothing moves it but the test (clock.advance), so every wait is exact;
    _fresh_rate_limits puts the next test back on time.monotonic."""
    from api import ratelimit

    clock = FakeClock()
    ratelimit.set_clock_for_tests(clock.now)
    return clock


@pytest.fixture
def budget_clock():
    """Put integrations.budget on a FakeClock (every budget starts full) and return the clock."""
    from integrations import budget

    clock = FakeClock()
    budget.set_clock_for_tests(clock.now)
    return clock
```

- [ ] **Step 3 (agent): Run the suite; the new fixtures change nothing yet**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `816 passed, 9 skipped in <t>s`. The autouse fixture finds neither module imported, and no test asks for the
two clock fixtures yet.

- [ ] **Step 4 (agent): Write the failing limiter tests**

Create `backend/tests/test_ratelimit.py`:

```python
"""api.ratelimit and token_bucket (F §1.8; S "Rate-limit buckets", Testing; AC7, AC13; slice 2a).

Every test runs on the `limiter_clock` FakeClock (conftest.py), which never
moves unless a test advances it, so each wait below is exact.
"""
import time
import uuid

import pytest
from fastapi import Depends
from fastapi.dependencies.utils import get_dependant
from fastapi.testclient import TestClient

from api import ratelimit
from api import settings as settings_mod
from api.deps import get_current_user, get_verifier, require_church
from api.errors import ApiError
from api.main import create_app
from api.ratelimit import BUCKETS, MESSAGE, RateLimiter, Rule, consume, rate_limit
from api.security import TokenVerifier
from domain_errors import RateLimited
from tests.conftest import FakeClock
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token
from token_bucket import TokenBucket


def _user() -> uuid.UUID:
    return uuid.uuid4()


def _rate_limited(bucket: str, **kwargs) -> RateLimited:
    with pytest.raises(RateLimited) as caught:
        consume(bucket, **kwargs)
    return caught.value


def test_buckets_match_f_1_8():
    assert BUCKETS == {
        "lectionary": (Rule("user", 120, 300),),
        "scripture": (Rule("user", 60, 300),),
        "church_create": (Rule("user", 3, 60),),
        "ai": (Rule("user", 40, 600), Rule("church", 400, 86_400)),
        "email": (Rule("user", 10, 3_600),),
    }
    assert MESSAGE == "Too many requests. Try again in {n} seconds."


def test_refill_is_continuous(limiter_clock):
    user = _user()
    for _ in range(3):
        consume("church_create", user_id=user)
    assert _rate_limited("church_create", user_id=user).retry_after_seconds == 20
    limiter_clock.advance(10)                    # half a token back: 10 s still to wait
    assert _rate_limited("church_create", user_id=user).retry_after_seconds == 10
    limiter_clock.advance(10)                    # one whole token, 20 s after the 3rd create
    consume("church_create", user_id=user)
    assert _rate_limited("church_create", user_id=user).retry_after_seconds == 20


def test_per_user_isolation(limiter_clock):
    first, second = _user(), _user()
    for _ in range(3):
        consume("church_create", user_id=first)
    _rate_limited("church_create", user_id=first)
    for _ in range(3):
        consume("church_create", user_id=second)     # the first user's bucket is not the second's


def test_ai_church_rule_shared_across_users(limiter_clock):
    church, other_church = uuid.uuid4(), uuid.uuid4()
    for _ in range(10):                              # 10 users x 40 = the church's 400 per day
        user = _user()
        for _ in range(40):
            consume("ai", user_id=user, church_id=church)
    newcomer = _user()
    limited = _rate_limited("ai", user_id=newcomer, church_id=church)
    assert limited.retry_after_seconds == 216        # one church token: 86 400 s / 400
    consume("ai", user_id=newcomer, church_id=other_church)


def test_ai_without_church_id_is_value_error(limiter_clock):
    with pytest.raises(ValueError, match="church_id"):
        consume("ai", user_id=_user())


def test_exhausted_raises_rate_limited_with_ceiling(limiter_clock):
    user = _user()
    for _ in range(120):
        consume("lectionary", user_id=user)
    limited = _rate_limited("lectionary", user_id=user)
    assert not isinstance(limited, ApiError)
    assert (limited.status, limited.code) == (429, "rate_limited")
    assert limited.message == "Too many requests. Try again in 3 seconds."   # 2.5 s rounded up
    assert limited.retry_after_seconds == 3
    assert limited.details == {"retry_after_seconds": 3}
    limiter_clock.advance(1)                         # 1.5 s still to wait: rounded up to 2
    limited = _rate_limited("lectionary", user_id=user)
    assert (limited.message, limited.retry_after_seconds) == (
        "Too many requests. Try again in 2 seconds.", 2)
    limiter_clock.advance(1.5)
    consume("lectionary", user_id=user)


def test_cost_three_charges_three(limiter_clock):
    user = _user()
    consume("scripture", user_id=user, cost=3)
    for _ in range(57):                              # 60 - 3
        consume("scripture", user_id=user)
    assert _rate_limited("scripture", user_id=user).retry_after_seconds == 5
    limiter_clock.advance(15)                        # three tokens back: 5 s each
    consume("scripture", user_id=user, cost=3)


def test_failed_charge_takes_nothing_across_rules(limiter_clock):
    church = uuid.uuid4()
    spender = _user()
    for _ in range(40):
        consume("ai", user_id=spender, church_id=church)
    for _ in range(400):                             # each fails on the user rule...
        _rate_limited("ai", user_id=spender, church_id=church)
    other = _user()
    for _ in range(40):                              # ...and took no church token
        consume("ai", user_id=other, church_id=church)

    full_church = uuid.uuid4()
    for _ in range(10):
        user = _user()
        for _ in range(40):
            consume("ai", user_id=user, church_id=full_church)
    late = _user()
    for _ in range(40):                              # each fails on the church rule...
        _rate_limited("ai", user_id=late, church_id=full_church)
    for _ in range(40):                              # ...and took no user token
        consume("ai", user_id=late, church_id=uuid.uuid4())


def test_cost_below_one_or_above_capacity_is_value_error(limiter_clock):
    user = _user()
    for cost in (0, -1):
        with pytest.raises(ValueError, match="at least 1"):
            consume("church_create", user_id=user, cost=cost)
    with pytest.raises(ValueError, match="capacity"):
        consume("church_create", user_id=user, cost=4)
    with pytest.raises(ValueError, match="capacity"):
        consume("scripture", user_id=user, cost=61)
    for _ in range(3):                               # nothing was charged
        consume("church_create", user_id=user)
    with pytest.raises(ValueError):
        TokenBucket(3, 60, FakeClock().now).try_take(4)
    with pytest.raises(KeyError):
        consume("lectionry", user_id=user)


def test_idle_entries_pruned():
    clock = FakeClock()
    limiter = RateLimiter(clock.now)
    a, b, c, d = (_user() for _ in range(4))
    limiter.consume("church_create", user_id=a)                  # t=1000
    clock.advance(30)
    limiter.consume("church_create", user_id=b, cost=3)          # t=1030: no sweep yet
    assert len(limiter) == 2
    clock.advance(40)
    limiter.consume("church_create", user_id=c)                  # t=1070: sweep; a is full again
    assert len(limiter) == 2                                     # b (2 tokens) and c
    with pytest.raises(RateLimited) as caught:                   # b kept its state
        limiter.consume("church_create", user_id=b, cost=3)
    assert caught.value.retry_after_seconds == 20
    clock.advance(30)
    limiter.consume("church_create", user_id=d)                  # t=1100: 30 s since the sweep
    assert len(limiter) == 3                                     # b, c, d: no second sweep yet


def _app_with(dependency) -> TestClient:
    app = create_app()

    @app.get("/limited")
    def limited(_rl: None = Depends(dependency)) -> dict:
        return {"ok": True}

    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


def test_dependency_429_has_retry_after_and_details(tmp_db, limiter_clock, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://church.example.app")
    settings_mod.get_settings.cache_clear()
    try:
        client = _app_with(rate_limit("church_create"))
        headers = {"Authorization": f"Bearer {make_token(email='a@example.com')}",
                   "Origin": "https://church.example.app"}
        for _ in range(3):
            assert client.get("/limited", headers=headers).status_code == 200
        r = client.get("/limited", headers=headers)
        assert r.status_code == 429
        assert r.json() == {"error": {
            "code": "rate_limited",
            "message": "Too many requests. Try again in 20 seconds.",
            "request_id": r.headers["x-request-id"],
            "details": {"retry_after_seconds": 20},
        }}
        assert r.headers["retry-after"] == "20"
        assert r.headers["access-control-allow-origin"] == "https://church.example.app"
        limiter_clock.advance(20)
        assert client.get("/limited", headers=headers).status_code == 200
    finally:
        settings_mod.get_settings.cache_clear()


def _calls(dependency) -> set:
    found, stack = set(), list(get_dependant(path="/", call=dependency).dependencies)
    while stack:
        dep = stack.pop()
        found.add(dep.call)
        stack.extend(dep.dependencies)
    return found


def test_dependency_trees():
    for name in ("lectionary", "scripture", "church_create", "email"):
        calls = _calls(rate_limit(name))
        assert get_current_user in calls, name
        assert require_church not in calls, name     # user-scoped routes stay user-scoped
    assert {get_current_user, require_church} <= _calls(rate_limit("ai"))
    with pytest.raises(KeyError):
        rate_limit("lectionry")


def test_reset_and_set_clock():
    user = _user()
    clock = FakeClock()
    ratelimit.set_clock_for_tests(clock.now)
    assert ratelimit._limiter.clock == clock.now
    for _ in range(3):
        consume("church_create", user_id=user)
    _rate_limited("church_create", user_id=user)
    ratelimit.set_clock_for_tests(clock.now)             # empties the buckets
    for _ in range(3):
        consume("church_create", user_id=user)
    ratelimit.reset_for_tests()                          # empties them and restores the clock
    assert ratelimit._limiter.clock is time.monotonic
    for _ in range(3):
        consume("church_create", user_id=user)


def test_token_bucket_clamps_negative_elapsed():
    clock = FakeClock(start=5000.0)
    bucket = TokenBucket(3, 60, clock.now)
    assert bucket.try_take(2) == 0.0
    clock.value = 10.0                                   # a swapped clock: far behind
    assert bucket.wait_for(1) == 0.0                     # the one token left is still there
    assert bucket.try_take(1) == 0.0
    assert bucket.wait_for(1) == 20.0
    clock.advance(20)
    assert bucket.try_take(1) == 0.0
```

- [ ] **Step 5 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ratelimit.py 2>&1 | grep -m1 '^E '
.venv/bin/python -m pytest -q backend/tests/test_ratelimit.py 2>&1 | tail -1
```

**Expected:** `E   ImportError: cannot import name 'ratelimit' from 'api' (<repo>/backend/api/__init__.py)`, then
`1 error in <t>s` (a collection error: neither `api/ratelimit.py` nor `token_bucket.py` exists).

- [ ] **Step 6 (agent): Write `token_bucket.py` and `api/ratelimit.py`**

Create `backend/token_bucket.py`:

```python
"""A continuous-refill token bucket (S "Rate-limit buckets", "Upstream budgets"; slice 2).

Pure arithmetic on an injected clock. api/ratelimit.py (per-user and
per-church buckets) and integrations/budget.py (process-wide upstream
budgets) both build on it. It holds no lock: each owner takes its own lock
around wait_for and try_take, so a check across several buckets is
all-or-nothing. Imports no FastAPI, Starlette or Streamlit.
"""
from collections.abc import Callable


class TokenBucket:
    """`capacity` tokens, refilled continuously at capacity per `per_seconds`.

    A new bucket is full. Elapsed time is clamped at 0, so a clock that moves
    backwards (a test that swaps clocks) never removes tokens. Rates are
    applied as capacity / per_seconds and waits as missing * per_seconds /
    capacity, so whole-number limits give whole-number waits (3 per 60 s:
    exactly 20 s for one token).
    """

    def __init__(self, capacity: float, per_seconds: float, clock: Callable[[], float]):
        if capacity <= 0 or per_seconds <= 0:
            raise ValueError("capacity and per_seconds must be positive")
        self.capacity = float(capacity)
        self.per_seconds = float(per_seconds)
        self._clock = clock
        self._tokens = self.capacity
        self._last = clock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._last)
        self._tokens = min(self.capacity, self._tokens + elapsed * self.capacity / self.per_seconds)
        self._last = now

    def _check(self, n: float) -> None:
        if n <= 0 or n > self.capacity:
            raise ValueError(f"n must be between 0 (exclusive) and the capacity {self.capacity:g}")

    def wait_for(self, n: float = 1) -> float:
        """0.0 when n tokens are available now, else the seconds until they are. Takes none."""
        self._check(n)
        self._refill()
        missing = n - self._tokens
        return 0.0 if missing <= 0 else missing * self.per_seconds / self.capacity

    def try_take(self, n: float = 1) -> float:
        """Take n tokens and return 0.0, or take nothing and return the wait (wait_for)."""
        wait = self.wait_for(n)
        if wait == 0.0:
            self._tokens -= n
        return wait

    def is_full(self) -> bool:
        """True when the bucket has refilled to capacity (the limiter prunes these)."""
        self._refill()
        return self._tokens >= self.capacity
```

Create `backend/api/ratelimit.py`:

```python
"""Per-user and per-church rate limits (F §1.8; S "Rate-limit buckets"; slice 2).

In-memory token buckets keyed by (bucket, rule index, scope id), in this one
process: backend/Procfile runs a single uvicorn worker. Refill is continuous
(backend/token_bucket.py).

- consume(bucket, *, user_id, church_id=None, cost=1) charges every rule of
  the bucket all-or-nothing. When a rule is short it charges nothing and
  raises domain_errors.RateLimited, never ApiError (F §1.5, §2.2). The
  DomainError handler adds Retry-After and details.retry_after_seconds, and
  run_idempotent never stores it, so a limiter 429 is never replayed.
- rate_limit(name) is the FastAPI dependency that calls consume(name,
  cost=1). It depends on get_current_user, plus require_church when the
  bucket has a church rule (only `ai`), so user-scoped routes stay free of
  require_church (test_route_guards). The church id comes from the resolved
  ActiveChurch, never the raw header. Routes whose cost depends on the
  request (/scripture/passages) call consume themselves after validation.
- reset_for_tests() and set_clock_for_tests(clock): backend/tests/conftest.py.

This is the one API-layer module of the slice 2 platform: it may import
FastAPI (the dependency); consume itself needs none of it.
"""
import math
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from fastapi import Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from domain_errors import RateLimited
from token_bucket import TokenBucket


@dataclass(frozen=True)
class Rule:
    """One limit of a bucket: `capacity` tokens per `per_seconds`, per user or per church."""

    scope: Literal["user", "church"]
    capacity: int
    per_seconds: float


# F §1.8 plus S's `lectionary` addition. Wired in 2a: lectionary, scripture,
# church_create. ai: slices 3 and 4, PR #7, PR #8. email: slice 5b.
BUCKETS: dict[str, tuple[Rule, ...]] = {
    "lectionary": (Rule("user", 120, 300),),
    "scripture": (Rule("user", 60, 300),),
    "church_create": (Rule("user", 3, 60),),
    "ai": (Rule("user", 40, 600), Rule("church", 400, 86_400)),
    "email": (Rule("user", 10, 3_600),),
}

MESSAGE = "Too many requests. Try again in {n} seconds."

# At most one sweep of idle (full) buckets per this many seconds of the clock.
PRUNE_EVERY_SECONDS = 60.0


class RateLimiter:
    """Token buckets keyed by (bucket, rule index, scope id), behind one lock."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self.clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[tuple[str, int, uuid.UUID], TokenBucket] = {}
        self._last_prune = clock()

    def __len__(self) -> int:
        """How many buckets are held (pruning drops full ones)."""
        with self._lock:
            return len(self._buckets)

    def consume(self, bucket: str, *, user_id: uuid.UUID,
                church_id: uuid.UUID | None = None, cost: int = 1) -> None:
        rules = BUCKETS[bucket]                          # KeyError: no such bucket
        if cost < 1:
            raise ValueError("cost must be at least 1")
        keys: list[tuple[tuple[str, int, uuid.UUID], Rule]] = []
        for index, rule in enumerate(rules):
            scope_id = user_id if rule.scope == "user" else church_id
            if scope_id is None:
                raise ValueError(f"the {bucket!r} bucket has a church rule: pass church_id")
            if cost > rule.capacity:
                raise ValueError(f"cost {cost} exceeds the {bucket!r} capacity {rule.capacity}")
            keys.append(((bucket, index, scope_id), rule))
        with self._lock:
            self._prune_if_due()
            held = [self._bucket(key, rule) for key, rule in keys]
            wait = max(b.wait_for(cost) for b in held)
            if wait > 0:
                n = max(1, math.ceil(wait))              # once: message and header agree
                raise RateLimited(MESSAGE.format(n=n), retry_after_seconds=n)
            for b in held:
                b.try_take(cost)

    def _bucket(self, key: tuple[str, int, uuid.UUID], rule: Rule) -> TokenBucket:
        found = self._buckets.get(key)
        if found is None:
            found = self._buckets[key] = TokenBucket(rule.capacity, rule.per_seconds, self.clock)
        return found

    def _prune_if_due(self) -> None:
        now = self.clock()
        if now - self._last_prune < PRUNE_EVERY_SECONDS:
            return
        self._last_prune = now
        for key in [key for key, b in self._buckets.items() if b.is_full()]:
            del self._buckets[key]


# Read as a module attribute on every call, so the test hooks can swap it.
_limiter = RateLimiter()


def consume(bucket: str, *, user_id: uuid.UUID,
            church_id: uuid.UUID | None = None, cost: int = 1) -> None:
    """Charge `cost` tokens to every rule of `bucket`, or raise RateLimited and charge nothing.

    KeyError: an unknown bucket. ValueError: a church rule without
    church_id, cost < 1, or cost above a rule's capacity.
    """
    _limiter.consume(bucket, user_id=user_id, church_id=church_id, cost=cost)


def rate_limit(name: str) -> Callable[..., None]:
    """A dependency that charges one token of `name` to the caller (and church).

    Raises KeyError now for an unknown name, so a misspelled bucket fails when
    the route module is imported, not on every request.
    """
    rules = BUCKETS[name]
    if any(rule.scope == "church" for rule in rules):
        def church_rate_limit(
            user: CurrentUser = Depends(get_current_user),
            church: ActiveChurch = Depends(require_church),
        ) -> None:
            consume(name, user_id=user.id, church_id=church.id)

        return church_rate_limit

    def user_rate_limit(user: CurrentUser = Depends(get_current_user)) -> None:
        consume(name, user_id=user.id)

    return user_rate_limit


def set_clock_for_tests(clock: Callable[[], float]) -> None:
    """Tests: a new limiter on `clock` (a FakeClock's `now`) that holds no buckets,
    so every caller starts full. A bucket made under one clock is never read
    under another."""
    global _limiter
    _limiter = RateLimiter(clock)


def reset_for_tests() -> None:
    """Tests: a new limiter on time.monotonic that holds no buckets."""
    set_clock_for_tests(time.monotonic)
```

- [ ] **Step 7 (agent): Run the limiter tests**

```bash
.venv/bin/python -m pytest -q backend/tests/test_ratelimit.py 2>&1 | tail -3
```

**Expected:** `14 passed in <t>s`.

- [ ] **Step 8 (agent): Write the failing budget tests**

Create `backend/tests/test_budget.py`:

```python
"""integrations.budget: process-wide upstream budgets (S "Upstream budgets", Testing; AC13; slice 2a).

Every test runs on the `budget_clock` FakeClock (conftest.py), which never
moves unless a test advances it.
"""
import threading
import time

import pytest

from integrations import budget


def _acquired_at_pace(clock, seconds_between: float, attempts: int) -> int:
    """How many ESV acquires succeed, one every `seconds_between`, before the first refusal."""
    for count in range(attempts):
        if not budget.try_acquire("esv"):
            return count
        clock.advance(seconds_between)
    return attempts


def test_bible_api_fifteen_then_sixteenth_fails_then_refills(budget_clock):
    assert [budget.try_acquire("bible_api") for _ in range(16)] == [True] * 15 + [False]
    budget_clock.advance(1)                      # half a token: one takes 2 s (30 s / 15)
    assert budget.try_acquire("bible_api") is False
    budget_clock.advance(1)
    assert budget.try_acquire("bible_api") is True
    assert budget.try_acquire("bible_api") is False
    budget_clock.advance(30)
    assert [budget.try_acquire("bible_api") for _ in range(16)] == [True] * 15 + [False]
    budget.set_clock_for_tests(budget_clock.now)         # the hook forgets the spent budget
    assert all(budget.try_acquire("bible_api") for _ in range(15))
    budget.reset_for_tests()                             # ...and reset restores the real clock
    assert budget._clock is time.monotonic


def test_esv_minute_rule(budget_clock):
    assert [budget.try_acquire("esv") for _ in range(61)] == [True] * 60 + [False]
    budget_clock.advance(1)                      # 60 per minute: one token a second
    assert budget.try_acquire("esv") is True
    assert budget.try_acquire("esv") is False


def test_esv_hour_rule(budget_clock):
    # One a second never runs out the minute rule (it refills one a second), so
    # the hour rule stops it: before call m it holds 1000 - (m - 1) * (1 - 1000/3600).
    assert _acquired_at_pace(budget_clock, 1.0, 5_000) == 1_384
    budget_clock.advance(3.6)                    # one hour token: 3 600 s / 1 000
    assert budget.try_acquire("esv") is True


def test_esv_day_rule(budget_clock):
    # One every 4 s never runs out the minute or the hour rule, so the day rule
    # stops it: before call m it holds 5000 - (m - 1) * (1 - 4 * 5000/86400).
    assert _acquired_at_pace(budget_clock, 4.0, 10_000) == 6_505
    budget_clock.advance(17.28)                  # one day token: 86 400 s / 5 000
    assert budget.try_acquire("esv") is True


def test_failed_acquire_takes_nothing(budget_clock):
    assert all(budget.try_acquire("esv") for _ in range(60))
    assert not any(budget.try_acquire("esv") for _ in range(1_000))   # the minute rule refuses...
    budget_clock.advance(60)
    assert all(budget.try_acquire("esv") for _ in range(60))        # ...and the hour rule lost nothing


def test_threads_get_exactly_fifteen(budget_clock):
    start = threading.Barrier(32)
    results: list[bool] = []
    results_lock = threading.Lock()

    def acquire() -> None:
        start.wait(timeout=10)
        got = budget.try_acquire("bible_api")
        with results_lock:
            results.append(got)

    threads = [threading.Thread(target=acquire) for _ in range(32)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)
    assert len(results) == 32
    assert results.count(True) == 15


def test_unknown_upstream_raises(budget_clock):
    assert budget.BUDGETS == {                           # S "Upstream budgets"
        "bible_api": ((15, 30.0),),
        "esv": ((60, 60.0), (1_000, 3_600.0), (5_000, 86_400.0)),
    }
    with pytest.raises(KeyError):
        budget.try_acquire("openai")
```

The two paced tests pin exact counts. The margins are wide: before the 1 385th call the hour rule holds about 0.44 of a
token, and the 1 384.2 limit is nowhere near a whole number. Before the 6 506th call the day rule holds a fraction of a
token too. So floating-point rounding cannot move either count.

- [ ] **Step 9 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_budget.py 2>&1 | grep -m1 '^E '
.venv/bin/python -m pytest -q backend/tests/test_budget.py 2>&1 | tail -1
```

**Expected:** `E   ImportError: cannot import name 'budget' from 'integrations' (<repo>/backend/integrations/__init__.py)`,
then `1 error in <t>s`.

- [ ] **Step 10 (agent): Write `integrations/budget.py`**

Create `backend/integrations/budget.py`:

```python
"""Process-wide upstream budgets (S "Upstream budgets"; F §2.7, §7.4; slice 2).

Every user shares the Railway IP (bible-api's per-IP limit) and the one ESV
key, so per-user buckets alone do not protect the upstreams. One token
bucket per rule, shared by every request in this process (backend/Procfile
runs a single uvicorn worker). scripture_fetcher calls try_acquire before
each uncached part; a part that finds no token is not sent and becomes
`unavailable`. Imports no FastAPI, Starlette or Streamlit.
"""
import threading
import time
from collections.abc import Callable
from typing import Literal

from token_bucket import TokenBucket

Upstream = Literal["bible_api", "esv"]

# (capacity, per_seconds) for each rule; an acquire needs a token from every rule.
BUDGETS: dict[str, tuple[tuple[int, float], ...]] = {
    "bible_api": ((15, 30.0),),                                   # bible-api.com, per IP
    "esv": ((60, 60.0), (1_000, 3_600.0), (5_000, 86_400.0)),     # Crossway, per key
}

_lock = threading.Lock()
_clock: Callable[[], float] = time.monotonic
_buckets: dict[str, tuple[TokenBucket, ...]] = {}


def try_acquire(upstream: Upstream) -> bool:
    """Take one token from every rule of `upstream` and return True, or take none and return False.

    Never waits. KeyError: an unknown upstream.
    """
    with _lock:
        buckets = _buckets.get(upstream)
        if buckets is None:
            buckets = _buckets[upstream] = tuple(
                TokenBucket(capacity, per_seconds, _clock) for capacity, per_seconds in BUDGETS[upstream]
            )
        if any(b.wait_for(1) > 0 for b in buckets):
            return False
        for b in buckets:
            b.try_take(1)
        return True


def set_clock_for_tests(clock: Callable[[], float]) -> None:
    """Tests: forget every budget (each starts full again) and run them on `clock`
    (a FakeClock's `now`), so a bucket made under one clock is never read under
    another."""
    global _clock
    with _lock:
        _clock = clock
        _buckets.clear()


def reset_for_tests() -> None:
    """Tests: forget every budget (each starts full again) and run them on time.monotonic."""
    set_clock_for_tests(time.monotonic)
```

- [ ] **Step 11 (agent): Run the budget tests**

```bash
.venv/bin/python -m pytest -q backend/tests/test_budget.py 2>&1 | tail -3
```

**Expected:** `7 passed in <t>s`.

- [ ] **Step 12 (agent): Extend the layering gate**

In `backend/tests/test_no_streamlit_in_core.py`, `test_usecases_package_imports_no_fastapi_or_streamlit`, T2 left the
import list as these two lines:

```python
    code = ("import sys, usecases, usecases.onboarding, domain_errors, db.ids, timezones, "
            "cache, integrations.http; "
```

Replace the second of them, `            "cache, integrations.http; "`, with:

```python
            "cache, integrations.http, "
            "token_bucket, integrations.budget; "
```

If T2 wrote that line differently, keep T2's modules and append `token_bucket, integrations.budget` at the end of the
same import list, before the `; `, as its own string line `            "token_bucket, integrations.budget; "` (Task 5
anchors on that exact line). `api/ratelimit.py` is deliberately not added: it is the one slice 2 platform module
that may import FastAPI (§2 "Layering and logging").

```bash
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
grep -n "fastapi\|starlette\|streamlit" backend/token_bucket.py backend/integrations/budget.py
```

**Expected:** `3 passed in <t>s`. The grep prints nothing. This gate is a guard, not a new test: it passes as soon as it
is written, because neither module imports FastAPI.

- [ ] **Step 13 (agent): Run the whole suite, and the new files three more times**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_ratelimit.py backend/tests/test_budget.py 2>&1 | tail -1; done
git status --short
```

**Expected:**
- `837 passed, 9 skipped in <t>s` (816 + 14 + 7).
- `21 passed in <t>s`, three times. The threaded budget test must not flake.
- `git status --short` lists:
  - ` M backend/tests/conftest.py`
  - ` M backend/tests/test_no_streamlit_in_core.py`
  - `?? .claude/`
  - `?? backend/api/ratelimit.py`
  - `?? backend/integrations/budget.py`
  - `?? backend/tests/test_budget.py`
  - `?? backend/tests/test_ratelimit.py`
  - `?? backend/token_bucket.py`

If the count is not 837, stop and find why.

- [ ] **Step 14 (agent): Commit**

```bash
git add backend/token_bucket.py backend/api/ratelimit.py backend/integrations/budget.py \
        backend/tests/test_ratelimit.py backend/tests/test_budget.py \
        backend/tests/conftest.py backend/tests/test_no_streamlit_in_core.py
git commit -m "Platform: token bucket, rate limiter and upstream budgets (F §1.8; S Rate-limit buckets, Upstream budgets)

token_bucket.TokenBucket is a pure continuous-refill bucket with
wait_for, so a check across several rules is all-or-nothing. It clamps
elapsed time at 0 (2a clarifications 25, 37).

api/ratelimit.py defines every F §1.8 bucket plus lectionary. consume
charges all of a bucket's rules or none. When a rule is short it raises
domain_errors.RateLimited with n = max(1, ceil(wait)), computed once, so
the message, Retry-After and details agree (clarification 17). It raises
ValueError for cost < 1 (clarification 33). rate_limit(name) fails on an
unknown name when it is called (clarification 35), and depends on
require_church only for ai.

integrations/budget.py holds the process-wide bible_api (15/30 s) and
esv (60/min, 1000/h, 5000/day) budgets; try_acquire never waits.

The conftest resets both per test and adds limiter_clock and
budget_clock (FakeClock). No route is wired yet (T4, T8, T10).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> Platform: token bucket, rate limiter and upstream budgets (F §1.8; S Rate-limit buckets, Upstream budgets)`,
then `git status --short` lists only `?? .claude/`.
### Task 4: Wire the `church_create` burst guard on `POST /churches` (S Hand-offs row 3, Rate-limit buckets :302; F §1.8; AC7 church_create half; P1b hand-off; clarifications 1, 29)

`POST /churches` gains one dependency, `Depends(rate_limit("church_create"))`, declared after `user` and before `key`. The bucket is Task 3's: 3 tokens per 60 s per user, continuous refill, so one token comes back every 20 s and a 4th request at the same instant waits exactly 20 s. Because FastAPI runs the dependencies in declaration order and validates the body after all of them:
- no token (or an expired one) is 401 from `get_current_user`, before any charge;
- a malformed `Idempotency-Key` (raised inside `idempotency_key()`), a body 422 and an idempotent replay each spend a token, as S :302 and F :290 require;
- with no token left, the guard's 429 comes first, ahead of a malformed key's 422.

The guard's 429 is raised by the dependency, before `run_idempotent`, so it is never stored under the key (the cap's 429 was already never stored). Slice 1's durable cap (5 creates per user per rolling 24 h) is untouched and still answers the 6th create when creates are spread over more than a minute. The same commit also drops the word "usecase" from `CreateChurchIn`'s docstring (1b T6-m2), which is the only change in the regenerated OpenAPI files: the new dependency adds no parameter, because its only sub-dependency, `get_current_user`, is already on the route (checked by regenerating on a scratch copy: `1 1` and `2 2` line changes, the description only).

**Decisions recorded in this task (code wins over the outline and S; owner decision 1):**
- **T4-1 (clarification 1). S names the wrong slice 1 test.** S :302 and its Testing row for `test_api_churches.py` say slice 1's 6th-create test is updated to advance the limiter clock. That test, `test_cap_429_not_replayed` (`backend/tests/test_api_churches.py:203-226`), makes its five creates through `repos.churches.create_church` and then only 2 HTTP POSTs, so it stays **unchanged**, as its own docstring promises. The test the guard breaks is `test_blank_then_corrected_with_new_key_201` (`:183-200`), which makes 4 POSTs as one user; it now takes `limiter_clock` and advances it 60 s before the 4th. S's HTTP 6th-create behavior is covered by the new `test_creates_spaced_a_minute_apart_meet_the_cap_message`. Task 12 corrects S :302 and the Testing row.
- **T4-2 (clarification 29). 1b T6-m2.** `CreateChurchIn`'s docstring, which is its OpenAPI description and a comment in `schema.d.ts`, no longer names the internal "usecase" layer. The meaning is unchanged: a blank name, or a blank or unknown time zone, passes the model and gets a 422 that names the field.
- **T4-3. A body that is not JSON at all spends no token.** FastAPI parses the JSON before it solves any dependency and answers a parse failure with its own 422 at once (checked on FastAPI 0.141.1 on a scratch copy: four unparseable bodies, then three creates all 201, the fourth 429). S :302's "a 422 … also costs a token" holds for every 422 the route itself can produce (a Pydantic field error, an extra key, a blank name, an unknown time zone, a malformed key), which is what the new tests pin. The route docstring states the exception; no test pins FastAPI's own order.
- **T4-4. 1b T3-m2 needs no code.** The cap has no lock, so a concurrent burst could pass it. The guard now lets at most 3 requests per user per minute reach the cap check, so a burst can overshoot the cap by at most 2. This is recorded in the commit message.
- **T4-5. Two of the five touched tests are green before the route changes.** The edited `test_blank_then_corrected_with_new_key_201` and the new `test_creates_spaced_a_minute_apart_meet_the_cap_message` pin behavior that must survive the change (4 spaced requests succeed; the guard never pre-empts the cap), so they pass both before and after. The red step is the other three new tests.
- **T4-6. The cap's wait is asserted as "more than 23 h, at most 24 h".** The cap reads the real clock (`usecases/onboarding.py:118`), not the limiter's fake one, so five creates made within a second leave a wait of 86 400 s or a second less.

**Files:**
- Modify: `backend/api/routes/churches.py` (whole file shown: the module docstring `:1-10`, one import after `:19`, one parameter after `:30`)
- Modify: `backend/api/schemas.py:59-60` (the `CreateChurchIn` docstring)
- Test: `backend/tests/test_api_churches.py` (module docstring `:1-7`; imports and constants `:13-21`; `test_blank_then_corrected_with_new_key_201` `:183-200`; 4 new tests, a `cors_origin` fixture and a `_create` helper appended after `:226`)
- Modify (generated, never by hand): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes:
  - Task 3: `api.ratelimit.rate_limit(name: str) -> Callable[..., None]`. For `"church_create"` it returns a dependency that depends on `api.deps.get_current_user` only (never `require_church`, so `test_route_guards.py` keeps `("POST", "/churches")` user-scoped) and calls `consume("church_create", user_id=user.id)`, which raises `domain_errors.RateLimited(MESSAGE.format(n=n), retry_after_seconds=n)` with `n = max(1, ceil(wait))`.
  - Task 3: `api.ratelimit.BUCKETS["church_create"]`, one `Rule(scope="user", capacity=3, per_seconds=60)`; `api.ratelimit.MESSAGE == "Too many requests. Try again in {n} seconds."`.
  - Task 3 (`backend/tests/conftest.py`): the autouse `_fresh_rate_limits` (calls `api.ratelimit.reset_for_tests()` and `integrations.budget.reset_for_tests()` when imported), and the `limiter_clock` fixture, a `FakeClock` (`.now`, `.advance(seconds)`, start 1000.0) installed with `ratelimit.set_clock_for_tests(clock.now)`, which also empties the buckets.
  - Existing: `domain_errors.RateLimited` (`domain_errors.py:133-147`); `api.errors.domain_error_response` copies `retry_after_seconds` into `Retry-After` (`api/errors.py:144-149`); `CORSMiddleware` exposes `Retry-After` (`api/main.py:53`); `api.idempotency.idempotency_key()` raises `InvalidInput("Idempotency-Key must be a UUID.")`; `api.settings.get_settings` (an `lru_cache`, cleared around `CORS_ORIGINS` changes as in `test_middleware.py:82-88`); `tests.jwt_helpers.make_token(*, email=…, expires_in=3600, …)` (`expires_in=-120` is past the 30 s leeway, `api/security.py:18`); `tests.api_helpers.make_api_client()`, `auth_headers(email)`; fixtures `tmp_db`, `make_user`.
- Produces:
  - `api.routes.churches.create_church(payload: CreateChurchIn, user: CurrentUser = Depends(get_current_user), rl: None = Depends(rate_limit("church_create")), key: uuid.UUID | None = Depends(idempotency_key())) -> Response`; decorator, `error_responses(401, 422, 429, 503)` and operation id `create_church_churches_post` unchanged; no new OpenAPI parameter.
  - `CreateChurchIn` OpenAPI description: `"The body of POST /churches. A blank name, or a blank or unknown time\nzone, passes this model and gets a 422 that names the field."`
  - In `backend/tests/test_api_churches.py`: constants `BURST_MESSAGE = "Too many requests. Try again in 20 seconds."` and `ALLOWED_ORIGIN = "https://church.example.app"`; a module-local `cors_origin` fixture; `_create(client, name="Grace Church", headers=None)`. Task 11 edits the same file: after this task, `test_create_201_listed_in_me_and_usable`'s `assert usable.json() == body` is at `:87` (it was `:80`).

- [ ] **Step 1 (agent): Confirm Task 3's hand-off and the baseline**

```bash
git status --short
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from api import ratelimit as r; (rule,) = r.BUCKETS['church_create']; assert (rule.scope, rule.capacity, rule.per_seconds) == ('user', 3, 60); assert r.MESSAGE == 'Too many requests. Try again in {n} seconds.'; r.rate_limit('church_create'); print('ok')"
grep -n "def limiter_clock\|def _fresh_rate_limits" backend/tests/conftest.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `git status --short` lists only `?? .claude/`; the one-liner prints `ok`; the grep prints two lines (`def _fresh_rate_limits` and `def limiter_clock`); then `837 passed, 9 skipped in <t>s` (Task 3's count). If the one-liner fails, Task 3's names differ from its Interfaces: stop and reconcile before editing anything. If the count differs, stop and find why.

- [ ] **Step 2 (agent): Write the failing tests (`backend/tests/test_api_churches.py`)**

Replace the end of the module docstring (`:5-7`):

```python
contract: statuses, the error body, X-Church-Id ignored, the dependency
order, and Idempotency-Key replay through run_idempotent.
"""
```

with:

```python
contract: statuses, the error body, X-Church-Id ignored, the dependency
order, and Idempotency-Key replay through run_idempotent. Slice 2 adds the
church_create burst guard (3 per minute per user, F §1.8): a test that makes
more than 3 requests as one user takes `limiter_clock` and advances it.
"""
```

Replace the imports and constants (`:13-21`):

```python
from db import session_scope
from db.models import Church, Hymn, Membership
from repos.churches import create_church as repo_create_church
from repos.memberships import add_membership
from tests.api_helpers import auth_headers, church_headers, make_api_client

EMAIL = "pastor@example.com"
BODY = {"name": "Grace Church", "timezone": "America/Chicago"}
CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."
```

with:

```python
from api import settings as settings_mod
from db import session_scope
from db.models import Church, Hymn, Membership
from repos.churches import create_church as repo_create_church
from repos.memberships import add_membership
from tests.api_helpers import auth_headers, church_headers, make_api_client
from tests.jwt_helpers import make_token

EMAIL = "pastor@example.com"
BODY = {"name": "Grace Church", "timezone": "America/Chicago"}
CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."
# The limiter's copy (F §1.8) for church_create's wait: one token back every 20 s.
BURST_MESSAGE = "Too many requests. Try again in 20 seconds."
ALLOWED_ORIGIN = "https://church.example.app"
```

In `test_blank_then_corrected_with_new_key_201` (`:183-185`), replace:

```python
def test_blank_then_corrected_with_new_key_201(client):
    """The client's flow (S Idempotency): a 4xx is stored under its key, so the
    corrected body goes out under a new key."""
```

with:

```python
def test_blank_then_corrected_with_new_key_201(client, limiter_clock):
    """The client's flow (S Idempotency): a 4xx is stored under its key, so the
    corrected body goes out under a new key. Four requests, so the clock moves
    a minute before the fourth: the burst guard allows 3 per minute (slice 2)."""
```

and in the same test (`:195-197`) replace:

```python
    assert _count(Church) == 0

    fixed = client.post("/churches", json=BODY, headers=_key_headers(uuid.uuid4()))
```

with:

```python
    assert _count(Church) == 0

    limiter_clock.advance(60)
    fixed = client.post("/churches", json=BODY, headers=_key_headers(uuid.uuid4()))
```

`test_cap_429_not_replayed` stays exactly as it is (T4-1).

Append after the file's last line (`:226`, `    assert _count(Church) == 5`), with two blank lines before the block:

```python
# --- slice 2: the church_create burst guard (F §1.8; S Rate-limit buckets; AC7) ---
# Each test takes `limiter_clock` (a FakeClock) and never advances it during a
# burst, so the waits are exact: one token comes back every 20 s.

@pytest.fixture
def cors_origin(monkeypatch):
    """CORS_ORIGINS is exactly ALLOWED_ORIGIN for apps created in this test
    (test_middleware.py's pattern)."""
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    yield ALLOWED_ORIGIN
    settings_mod.get_settings.cache_clear()


def _create(client, name: str = "Grace Church", headers: dict[str, str] | None = None):
    return client.post("/churches", json={**BODY, "name": name},
                       headers=headers if headers is not None else auth_headers(EMAIL))


def test_fourth_create_within_a_minute_is_burst_429(tmp_db, cors_origin, limiter_clock):
    """AC7: the 4th create in a minute is the limiter's 429, with Retry-After,
    details and CORS headers. It is raised before run_idempotent, so it is
    never stored: the same key succeeds once the minute has passed."""
    client = make_api_client()           # after cors_origin, so the app allows ALLOWED_ORIGIN
    for n in range(3):
        assert _create(client, f"Church {n}").status_code == 201
    headers = {**_key_headers(uuid.uuid4()), "Origin": cors_origin}

    fourth = _create(client, headers=headers)
    assert fourth.status_code == 429, fourth.text
    error = fourth.json()["error"]
    assert (error["code"], error["message"]) == ("rate_limited", BURST_MESSAGE)
    assert error["details"] == {"retry_after_seconds": 20}
    assert "fields" not in error
    assert fourth.headers["Retry-After"] == "20"
    assert fourth.headers["access-control-allow-origin"] == cors_origin
    assert "Idempotent-Replayed" not in fourth.headers
    assert _count(Church) == 3

    limiter_clock.advance(60)
    later = _create(client, headers=headers)
    assert later.status_code == 201, later.text
    assert "Idempotent-Replayed" not in later.headers
    assert _count(Church) == 4


def test_creates_spaced_a_minute_apart_meet_the_cap_message(client, limiter_clock):
    """S :302, AC7: the bucket never pre-empts the durable cap. Five creates a
    minute apart all succeed, and the 6th gets slice 1's cap message with the
    cap's wait (about 24 h), not the limiter's."""
    for n in range(5):
        assert _create(client, f"Church {n}").status_code == 201
        limiter_clock.advance(60)

    sixth = _create(client)
    assert sixth.status_code == 429, sixth.text
    error = sixth.json()["error"]
    assert (error["code"], error["message"]) == ("rate_limited", CAP_MESSAGE)
    seconds = error["details"]["retry_after_seconds"]
    assert 23 * 60 * 60 < seconds <= 24 * 60 * 60
    assert sixth.headers["Retry-After"] == str(seconds)
    assert _count(Church) == 5


def test_burst_tokens_spent_by_422_and_replay(client, limiter_clock):
    """S :302, F §1.8: the guard runs before idempotency_key() and before body
    validation, so a replay, a body 422 and a malformed key each spend a token."""
    key = uuid.uuid4()
    assert _create(client, headers=_key_headers(key)).status_code == 201   # token 1
    replay = _create(client, headers=_key_headers(key))                      # token 2
    assert (replay.status_code, replay.headers.get("Idempotent-Replayed")) == (201, "true")
    too_long = _create(client, "x" * 201)                                    # token 3
    assert too_long.status_code == 422
    assert too_long.json()["error"]["fields"] == {"name": "Too long (max 200 characters)."}

    blocked = _create(client)
    assert blocked.status_code == 429, blocked.text
    assert blocked.json()["error"]["message"] == BURST_MESSAGE
    bad_key = {**auth_headers(EMAIL), "Idempotency-Key": "not-a-uuid"}
    # The guard runs before idempotency_key(): with no token left, a bad key is 429 too.
    assert _create(client, headers=bad_key).status_code == 429

    limiter_clock.advance(20)                                                # one token back
    spent = _create(client, headers=bad_key)
    assert spent.status_code == 422
    assert spent.json()["error"]["message"] == "Idempotency-Key must be a UUID."
    after = _create(client)
    assert after.status_code == 429, after.text
    assert after.headers["Retry-After"] == "20"
    assert _count(Church) == 1


def test_no_token_is_401_and_spends_nothing(client, limiter_clock):
    """get_current_user runs before the guard: a missing or expired token is
    401 and charges nobody, so the signed-in user keeps the minute's 3 creates."""
    assert _create(client, "First").status_code == 201                      # token 1
    expired = {"Authorization": f"Bearer {make_token(email=EMAIL, expires_in=-120)}"}
    for headers in ({}, expired, {**expired, "Idempotency-Key": "not-a-uuid"}) * 2:
        r = _create(client, headers=headers)
        assert r.status_code == 401
        assert r.json()["error"]["code"] == "unauthenticated"

    assert [_create(client, n).status_code for n in ("Second", "Third")] == [201, 201]
    fourth = _create(client, "Fourth")
    assert fourth.status_code == 429, fourth.text
    assert fourth.json()["error"]["message"] == BURST_MESSAGE
    assert _count(Church) == 3
```

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_churches.py 2>&1 | tail -4
```

**Expected:**

```
FAILED backend/tests/test_api_churches.py::test_fourth_create_within_a_minute_is_burst_429
FAILED backend/tests/test_api_churches.py::test_burst_tokens_spent_by_422_and_replay
FAILED backend/tests/test_api_churches.py::test_no_token_is_401_and_spends_nothing
3 failed, 15 passed in <t>s
```

Each of the three fails with `assert 201 == 429` (the message is the created church's JSON): nothing guards the route yet, so the 4th request in the minute creates a church (`fourth.status_code == 429`, `blocked.status_code == 429`, `fourth.status_code == 429`). The 15 that pass are the 14 slice 1 tests (including the edited `test_blank_then_corrected_with_new_key_201`) and `test_creates_spaced_a_minute_apart_meet_the_cap_message`, which pins behavior the change must keep (T4-5). If the new tests error with `fixture 'limiter_clock' not found`, Task 3's conftest change is missing: go back to Step 1.

- [ ] **Step 4 (agent): Wire the guard (`backend/api/routes/churches.py`)**

Replace the whole file with:

```python
"""POST /churches: create a church; the caller becomes its owner (S API, Idempotency).

User-scoped: the route depends on get_current_user and never on
require_church, so X-Church-Id is ignored (F §1.2). The dependencies run in
order: get_current_user, then the church_create burst guard (3 per minute per
user; F §1.8, slice 2), then idempotency_key(). So no token is 401 and spends
no token, and no token plus a malformed key is 401, not 422. A malformed key,
a body 422 and a replay each spend one (FastAPI validates the body after the
dependencies), and with none left the guard's 429 comes first. A body that is
not JSON at all is refused before any dependency runs, so it spends nothing.
The guard only stops scripted bursts: the real limit is the usecase's durable
cap (5 creates per user per rolling 24 h), which creates a minute apart reach.
The usecase runs inside run_idempotent's `call`: an Idempotency-Key replays
the first response. Neither 429 is ever stored (F §1.6): the guard's is raised
before run_idempotent, and run_idempotent never stores the cap's. Plain `def`,
because run_idempotent blocks on a lock.
"""
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.idempotency import idempotency_key, run_idempotent
from api.ratelimit import rate_limit
from api.schemas import ChurchOut, CreateChurchIn
from usecases import onboarding

router = APIRouter()


@router.post("/churches", status_code=201, response_model=ChurchOut,
             responses=error_responses(401, 422, 429, 503))
def create_church(
    payload: CreateChurchIn,
    user: CurrentUser = Depends(get_current_user),
    rl: None = Depends(rate_limit("church_create")),
    key: uuid.UUID | None = Depends(idempotency_key()),
) -> Response:
    return run_idempotent(
        user_id=user.id,
        route="/churches",
        key=key,
        payload=payload,
        status_code=201,
        call=lambda: ChurchOut(**asdict(onboarding.create_church(
            user_id=user.id, name=payload.name, timezone=payload.timezone))),
    )
```

The only code changes are the `from api.ratelimit import rate_limit` import and the `rl` parameter between `user` and `key`; the rest is the docstring.

- [ ] **Step 5 (agent): Drop "usecase" from `CreateChurchIn`'s docstring (`backend/api/schemas.py:59-60`; T4-2)**

Replace:

```python
    """The body of POST /churches. A blank name or time zone is left to the
    usecase, whose 422 names the field."""
```

with:

```python
    """The body of POST /churches. A blank name, or a blank or unknown time
    zone, passes this model and gets a 422 that names the field."""
```

- [ ] **Step 6 (agent): Run the tests to verify they pass; see the stale OpenAPI file fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_churches.py backend/tests/test_route_guards.py backend/tests/test_api_app.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -2
```

**Expected:** `49 passed, 1 skipped in <t>s` (18 in `test_api_churches.py`; `test_user_scoped_routes_require_a_user` still passes because the guard depends on `get_current_user` and never on `require_church`; the skip is `test_api_app.py`'s Postgres test). Then:

```
FAILED backend/tests/test_openapi_contract.py::test_committed_openapi_matches_the_live_schema
1 failed, 2 passed in <t>s
```

The committed `openapi.json` still has the old `CreateChurchIn` description; the next step regenerates it. If `test_fourth_create_within_a_minute_is_burst_429` gets `Retry-After: 21` instead of `20`, Task 3's `TokenBucket` wait lost float exactness (with 0 tokens and capacity 3 per 60 s the wait must be exactly `20.0`; `60 / 3` and `1 / (3 / 60)` both give `20.0`): fix `token_bucket.py`, not this test.

- [ ] **Step 7 (agent): Regenerate `openapi.json` and `schema.d.ts`**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git diff --numstat -- frontend/src/lib/api
grep -c "left to the" frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
```

**Expected:** `Wrote <repo>/frontend/src/lib/api/openapi.json`; openapi-typescript prints `src/lib/api/openapi.json → src/lib/api/schema.d.ts`; the numstat is exactly:

```
1	1	frontend/src/lib/api/openapi.json
2	2	frontend/src/lib/api/schema.d.ts
```

(the `CreateChurchIn` description line in `openapi.json`, and its two `@description` comment lines in `schema.d.ts`; no parameter, path or response changes); the grep prints `frontend/src/lib/api/openapi.json:0` and `frontend/src/lib/api/schema.d.ts:0`; then `3 passed in <t>s`. Never hand-edit either file. If the numstat shows more lines, the dependency added a parameter: read `git diff -- frontend/src/lib/api/openapi.json` and check that Task 3's `rate_limit` dependency declares no parameter of its own besides `get_current_user`.

- [ ] **Step 8 (agent): Recount the other `/churches` callers**

```bash
grep -rln '"/churches"' backend/tests | sort
```

**Expected:** exactly these four files:

```
backend/tests/test_api_app.py
backend/tests/test_api_churches.py
backend/tests/test_onboarding_postgres.py
backend/tests/test_route_guards.py
```

`test_api_app.py` and `test_route_guards.py` only name the route (the error-doc map and `USER_SCOPED`); `test_onboarding_postgres.py:209` makes 1 POST (Postgres job only). In `test_api_churches.py`, no slice 1 test except the edited one makes more than 3 POSTs as one user: `test_name_too_long` 3, `test_x_church_id_is_ignored` 2, `test_duplicate_names_and_second_church_allowed` 2 (plus 1 as another user), `test_key_replay_one_church_same_body` 2, `test_key_mismatch_422` 2, `test_cap_429_not_replayed` 2, `test_bad_key_without_token_is_401` 1 charged (its 401 charges nothing), the rest 1. Step 9's green suite is the proof; if any `/churches` test turns 429 there, it makes more than 3 requests as one user and takes `limiter_clock` like `test_blank_then_corrected_with_new_key_201`.

- [ ] **Step 9 (agent): Run both suites, typecheck and lint**

```bash
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test && npm run typecheck && npm run lint)
git status --short
```

**Expected:** `841 passed, 9 skipped in <t>s` (837 after Task 3 + 4); Vitest `Test Files  34 passed (34)` and `Tests  221 passed (221)`; `tsc --noEmit` and `eslint` print no errors; then exactly:

```
 M backend/api/routes/churches.py
 M backend/api/schemas.py
 M backend/tests/test_api_churches.py
 M frontend/src/lib/api/openapi.json
 M frontend/src/lib/api/schema.d.ts
?? .claude/
```

If `typecheck` fails, the generated schema is stale: rerun Step 7's first command; never hand-edit `schema.d.ts`.

- [ ] **Step 10 (agent): Commit**

```bash
git add backend/api/routes/churches.py backend/api/schemas.py backend/tests/test_api_churches.py \
        frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: church_create burst guard on POST /churches (F §1.8; S Rate-limit buckets; AC7)

Depends(rate_limit(\"church_create\")) sits between get_current_user and
idempotency_key(): 3 per minute per user, one token back every 20 s. No
token is 401 and spends nothing; a malformed key, a body 422 and a replay
each spend a token; with none left the limiter's 429 (Retry-After, details,
CORS) comes first and is never stored under the key. Slice 1's durable cap
still answers the 6th create when creates are a minute apart.

test_cap_429_not_replayed is unchanged (its five creates bypass HTTP);
test_blank_then_corrected_with_new_key_201 makes 4 requests, so it advances
the limiter clock (2a clarification 1). 1b T3-m2 needs no code: the guard
now lets at most 3 requests per user per minute reach the lock-free cap
check. CreateChurchIn's docstring drops \"usecase\" (1b T6-m2, clarification
29); that description is the only change in openapi.json and schema.d.ts.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> API: church_create burst guard on POST /churches (F §1.8; S Rate-limit buckets; AC7)`; `git status --short` then lists only `?? .claude/`.

- [ ] **Step 11 (agent): Review checkpoint**

Read `git show --stat HEAD` (5 files) and `git show HEAD -- backend/api/routes/churches.py`. Check against this task: the `rl` parameter is between `user` and `key`; the decorator and `error_responses(401, 422, 429, 503)` are unchanged (`test_api_app.py:275` still expects exactly those); `test_cap_429_not_replayed` has no diff; AC7's `church_create` half (the 4th create within one minute is 429 `rate_limited` with `Retry-After`, `details.retry_after_seconds` and CORS headers; creates spaced a minute apart reach the cap message on the 6th) is pinned by the four new tests. Record T4-1 for Task 12 (S :302 and the `test_api_churches.py` Testing row name the wrong test).

Counts after Task 4: backend **841 passed, 9 skipped**; frontend **221 passed in 34 files** (unchanged; schema regenerated, typecheck green).
### Task 5: `scripture_refs.py` and the shared fixture (S `scripture_refs.py`; spec decision 9; AC8 Python half; clarifications 16, 21, 28, 40)

This task adds `backend/scripture_refs.py`, the one pure module for scripture references: the book table (`BOOKS`), the classifier, the two bulletin pickers, **`resolve_readings`** (the only bulletin-reading rule, which fixes Psalm-as-NT), and the fetch-only normalization that Task 9 uses. It also adds `backend/tests/fixtures/shared/scripture_refs.json`, the fixture that slice 2b's `lib/scripture-refs.test.ts` will read with `fs`, so the Python and TypeScript ports cannot drift (F §5.3). Nothing here does I/O, and nothing imports FastAPI, Starlette, Streamlit or httpx. `app.py`'s frozen copies (`_NT_BOOKS`, `_expand_ref_options`, `_is_nt_ref`, `_is_ot_ref`, `app.py:75-107`) stay untouched (owner decision 2). The frontend does not change.

**Decisions recorded in this task (code wins over the outline; owner decision 1 unless noted):**
- **T5-1. Aliases are stored normalized.** Each alias is kept in `normalize_book_text` form (lower-case, no period, arabic numerals, single spaces), and the input is normalized before the lookup, so "Gen", "Gen." and "gen" all match the alias `gen`. This is how the outline's "aliases stored with and without the period" is met without listing every alias twice. The canonical name also matches and is not repeated in `aliases`. `test_fixture_books_match_BOOKS` checks that every alias is already normalized and that no lookup key names two books; `_alias_index()` also raises `ValueError` at import on a duplicate.
- **T5-2. `BOOKS` has 84 entries:** the 66 books plus the 18 deuterocanon entries S lists (Tobit, Judith, Additions to Esther, Wisdom of Solomon, Sirach, Baruch, Letter of Jeremiah, Song of the Three, Susanna, Bel and the Dragon, 1–4 Maccabees, 1–2 Esdras, Prayer of Manasseh, Psalm 151). Slice 3's extra deuterocanon aliases (`ws`, `wisdom`, `tob`, `tb`, `jdt`, `jth`, `mc`, `pr azar`, `ep jer`, `sus`, `bel`, `esd`, `pr man`, `add esth`, `ecclesiasticus`) are included now (ND A9), so there is one book table and slice 3 does not change the fixture. `"Is"` is not an alias (S lists only `Isa`); the fixture pins `split_book("Is 9:6")` as `null`, which is the slice 3 hymn-matching fix S :48 points at.
- **T5-3. `normalize_book_text` maps `iv`, `fourth` and `1st`–`4th` as well**, and the digit glue is `^[1-4](?=[a-z])` (clarification 28). A roman or ordinal prefix counts only when a space follows it, so "Isaiah" is untouched.
- **T5-4. `split_book`'s `rest` is the rest of the normalized text** (lower-case, periods removed), trimmed: `split_book("* Acts 2:14a, 22-32")` gives `(Acts, "2:14a, 22-32")`. S shows only "17:1-9". Every 2a caller uses only the book; `_about` documents the encoding for the TypeScript port.
- **T5-5. `split_alternatives` drops empty pieces** (as `app.py:89` and `scripture_fetcher.py:157` did). `split_joined`'s `\s+and\s+` is case-sensitive, as S writes it; it is Python-only.
- **T5-6. `expand_ref_options` now de-duplicates and splits without regard to case.** S requires it; `app.py:84-92` did neither. (Deviation from `app.py`, not from S.)
- **T5-7. `split_parts` is copied here unchanged, quirks included** ("Psalm 42; 43" leaves "43" bare; a first part with no chapter:verse never sets the book). `backend/scripture_fetcher.py` is not touched in this task: its private `_book_name_from_ref` and `_expand_part` stay until Task 9 switches `fetch_passage` to `scripture_refs.split_parts` and deletes them.
- **T5-8. `normalize_for_fetch`'s verse-part rule** removes one letter directly after a digit when no letter follows it (`9a`, `4b`, `35b`); `1ff` and a glued book such as `1Chr` are left alone. The comma is inserted only between two digits separated by whitespace (`1-14 15-20`), so `1 John` and `Psalm 42 and 43` are untouched.
- **T5-9. The fixture tests loop inside one test function** (clarification 20), so 5a's later `doc_readings` cases do not change the count. `test_every_spec_example_is_in_the_fixture` also requires case names for every category S Testing and 5a's `doc_readings.json` list, so a case cannot be deleted silently. Every `resolve_readings` case asserts that an automatic NT's first alternative is NT (never a Psalm).
- **T5-10. `backend/tests/fixtures/README.md`** gains a short `## shared/` section (hand-written, authoritative, no `.meta.json` sidecar) unless Task 1 already wrote one. Task 1's recorder writes exactly this section (`README_SHARED`, so a re-recording never drops it), so the conditional append below normally does nothing and the README is unchanged; the guarded append stays only as a fallback. `shared/` is not an upstream recording, so Task 1's per-recording checks do not apply to it.

**Files:**
- Create: `backend/scripture_refs.py`
- Create: `backend/tests/fixtures/shared/scripture_refs.json`
- Modify: `backend/tests/fixtures/README.md` (append a `## shared/` section when it has none)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (`test_usecases_package_imports_no_fastapi_or_streamlit`: the import list gains `scripture_refs`; no count change)
- Test: `backend/tests/test_scripture_refs.py` (new, 15 tests)

**Interfaces:**
- Consumes:
  - `backend/tests/fixtures/` (created by Task 1). Nothing else from Tasks 1–4.
  - The import-list line Task 3 left in `backend/tests/test_no_streamlit_in_core.py`: `            "token_bucket, integrations.budget; "`.
  - `pytest.ini`: `pythonpath = . backend`, so tests import `scripture_refs` by its bare name.
- Produces (all in `backend/scripture_refs.py`; the TypeScript port in 2b copies every name above "Fetch only"):
  - `Testament = Literal["ot", "psalm", "nt"]`
  - `@dataclass(frozen=True) class Book: name: str; testament: Testament; aliases: tuple[str, ...] = ()`
  - `BOOKS: tuple[Book, ...]` (84 entries, in canonical order: OT, deuterocanon, NT). Later users: slice 3 (adds a defaulted single-chapter field), 2b (the `books` fixture section).
  - `normalize_book_text(s: str) -> str`
  - `clean_lines(lines: list[str]) -> list[str]`
  - `split_alternatives(ref: str) -> list[str]`. Later users: slice 3, 2b, 2c (one badge per alternative).
  - `split_book(ref: str) -> tuple[Book, str] | None`. Later users: Task 6b (`clean_cell`), `split_joined`, slice 3.
  - `classify(ref: str) -> Literal["ot", "psalm", "nt", "unknown"]`. Later users: slice 3 (`== "nt"`), 2c's testament badge.
  - `is_nt_ref(ref: str) -> bool`. Later user: 5a.
  - `expand_ref_options(refs: list[str]) -> list[str]`
  - `picker_options(scriptures: list[str]) -> dict[str, list[str]]` with exactly the keys `"ot"` and `"nt"`
  - `@dataclass(frozen=True) class ReadingPair: ot: str | None; nt: str | None; ot_auto: bool; nt_auto: bool`
  - `resolve_readings(scriptures: list[str], ot_pick: str | None = "", nt_pick: str | None = "") -> ReadingPair`. Later users: 2b/2c (`effectivePicks` through the TS port), 5a (`resolve_doc_readings`).
  - `default_reading_pair(scriptures: list[str]) -> ReadingPair` (= `resolve_readings(scriptures, "", "")`)
  - `default_nt_ref(scriptures: list[str]) -> str | None` (= `default_reading_pair(scriptures).nt`). Later user: slice 3.
  - Fetch only (Python only, S :722): `normalize_for_fetch(ref: str) -> str`, `split_parts(ref: str) -> list[str]`, `split_joined(ref: str) -> list[str]`. Later user: Task 9 (`plan_parts`, the bible-api URL).
  - `scripture_key(ref: str) -> str`. Later users: Task 6b, Task 9, 2b.
  - `backend/tests/fixtures/shared/scripture_refs.json`: a top-level `"_about"` object (one string per section, plus `normalize_book_text`) and the sections `books`, `split_alternatives`, `split_book`, `classify`, `is_nt_ref`, `expand_ref_options`, `clean_lines`, `picker_options`, `resolve_readings`, `default_reading_pair`, `default_nt_ref`, `scripture_key`. Encodings (clarification 40): `split_book` → `{"book": name, "rest": str}` or `null`; `picker_options` → `{"ot": [...], "nt": [...]}`; `resolve_readings` / `default_reading_pair` expected keys `ot`, `nt`, `ot_auto`, `nt_auto` in snake_case, which 2b's Vitest maps to `otAuto` / `ntAuto`. Later users: 2b (`lib/scripture-refs.test.ts`), 5a (adds its `doc_readings` cases to `resolve_readings`).

Counts after this task: backend **856 passed, 9 skipped** (841 + 15, all in `test_scripture_refs.py`); frontend **221 passed in 34 files** (unchanged; not rerun here).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e backend/scripture_refs.py && test ! -e backend/tests/fixtures/shared && echo "no T5 files yet"
test -d backend/tests/fixtures && echo "fixtures folder present"
grep -n 'token_bucket, integrations.budget; "' backend/tests/test_no_streamlit_in_core.py
grep -rn 'scripture_refs' backend --include='*.py' | wc -l
.venv/bin/python -m pytest -q | tail -1
```

**Expected,** in order:
- exactly `?? .claude/` (Task 4 is committed);
- `no T5 files yet`;
- `fixtures folder present`;
- one line ending `            "token_bucket, integrations.budget; "` (Task 3's import-list line; its line number does not matter);
- `0` (padded by `wc`);
- `841 passed, 9 skipped in <t>s` (Task 4's count).

If the suite line differs, stop and find why before editing. If the `grep` for Task 3's line prints nothing, read `test_usecases_package_imports_no_fastapi_or_streamlit` and, in Step 4, add `scripture_refs` as the last module of that import list, before the `; `, instead of using the replacement block.

- [ ] **Step 2 (agent): Write the shared fixture**

Create `backend/tests/fixtures/shared/scripture_refs.json` with exactly this content (one case per line; the en and em dashes are written as `–` and `—` escapes on purpose):

```json
{
  "_about": {
    "books": "BOOKS in order: {name, testament, aliases}. Aliases are stored normalized (lower-case, no periods, arabic numerals); the canonical name also matches and is not repeated in aliases.",
    "split_alternatives": "{ref, expected: [str]}",
    "split_book": "{ref, expected}: expected is {\"book\": canonical name, \"rest\": str} or null. The longest key (a normalized name or an alias) at the start of normalize_book_text(ref), followed by the end, a space or a digit 0-9, wins; rest is the remaining normalized text, trimmed.",
    "normalize_book_text": "Not a section; pinned through split_book. Lower-case; drop a leading \"*\" and whitespace; remove \".\"; collapse whitespace to one space and trim; a leading i|ii|iii|iv|first|second|third|fourth|1st|2nd|3rd|4th followed by a space becomes 1-4; a leading 1-4 glued to a letter gets a space (\"1john\" -> \"1 john\").",
    "classify": "{ref, expected}: \"ot\" | \"psalm\" | \"nt\" | \"unknown\"",
    "is_nt_ref": "{ref, expected: bool}",
    "expand_ref_options": "{refs: [str], expected: [str]}",
    "clean_lines": "{lines: [str], expected: [str]}",
    "picker_options": "{scriptures: [str], expected: {\"ot\": [str], \"nt\": [str]}}",
    "resolve_readings": "{name, scriptures, ot_pick, nt_pick, expected: {ot, nt, ot_auto, nt_auto}}. Keys stay snake_case; the TypeScript test maps ot_auto/nt_auto to otAuto/ntAuto. ot and nt are str or null.",
    "default_reading_pair": "{scriptures, expected: {ot, nt, ot_auto, nt_auto}} (snake_case, as resolve_readings)",
    "default_nt_ref": "{scriptures, expected: str or null}",
    "scripture_key": "{ref, expected: str}: one case per normalize_for_fetch rule; equal keys mean the same passage."
  },
  "books": [
    {"name": "Genesis", "testament": "ot", "aliases": ["gen"]},
    {"name": "Exodus", "testament": "ot", "aliases": ["ex", "exod"]},
    {"name": "Leviticus", "testament": "ot", "aliases": ["lev"]},
    {"name": "Numbers", "testament": "ot", "aliases": ["num"]},
    {"name": "Deuteronomy", "testament": "ot", "aliases": ["deut"]},
    {"name": "Joshua", "testament": "ot", "aliases": ["josh"]},
    {"name": "Judges", "testament": "ot", "aliases": ["judg"]},
    {"name": "Ruth", "testament": "ot", "aliases": []},
    {"name": "1 Samuel", "testament": "ot", "aliases": ["1 sam"]},
    {"name": "2 Samuel", "testament": "ot", "aliases": ["2 sam"]},
    {"name": "1 Kings", "testament": "ot", "aliases": ["1 kgs"]},
    {"name": "2 Kings", "testament": "ot", "aliases": ["2 kgs"]},
    {"name": "1 Chronicles", "testament": "ot", "aliases": ["1 chr", "1 chron"]},
    {"name": "2 Chronicles", "testament": "ot", "aliases": ["2 chr", "2 chron"]},
    {"name": "Ezra", "testament": "ot", "aliases": []},
    {"name": "Nehemiah", "testament": "ot", "aliases": ["neh"]},
    {"name": "Esther", "testament": "ot", "aliases": ["esth"]},
    {"name": "Job", "testament": "ot", "aliases": []},
    {"name": "Psalms", "testament": "psalm", "aliases": ["ps", "psa", "psalm", "pss"]},
    {"name": "Proverbs", "testament": "ot", "aliases": ["prov"]},
    {"name": "Ecclesiastes", "testament": "ot", "aliases": ["eccl"]},
    {"name": "Song of Songs", "testament": "ot", "aliases": ["canticles", "song", "song of solomon"]},
    {"name": "Isaiah", "testament": "ot", "aliases": ["isa"]},
    {"name": "Jeremiah", "testament": "ot", "aliases": ["jer"]},
    {"name": "Lamentations", "testament": "ot", "aliases": ["lam"]},
    {"name": "Ezekiel", "testament": "ot", "aliases": ["ezek"]},
    {"name": "Daniel", "testament": "ot", "aliases": ["dan"]},
    {"name": "Hosea", "testament": "ot", "aliases": ["hos"]},
    {"name": "Joel", "testament": "ot", "aliases": []},
    {"name": "Amos", "testament": "ot", "aliases": []},
    {"name": "Obadiah", "testament": "ot", "aliases": ["obad"]},
    {"name": "Jonah", "testament": "ot", "aliases": []},
    {"name": "Micah", "testament": "ot", "aliases": ["mic"]},
    {"name": "Nahum", "testament": "ot", "aliases": ["nah"]},
    {"name": "Habakkuk", "testament": "ot", "aliases": ["hab"]},
    {"name": "Zephaniah", "testament": "ot", "aliases": ["zeph"]},
    {"name": "Haggai", "testament": "ot", "aliases": ["hag"]},
    {"name": "Zechariah", "testament": "ot", "aliases": ["zech"]},
    {"name": "Malachi", "testament": "ot", "aliases": ["mal"]},
    {"name": "Tobit", "testament": "ot", "aliases": ["tb", "tob"]},
    {"name": "Judith", "testament": "ot", "aliases": ["jdt", "jth"]},
    {"name": "Additions to Esther", "testament": "ot", "aliases": ["add esth"]},
    {"name": "Wisdom of Solomon", "testament": "ot", "aliases": ["wis", "wisdom", "ws"]},
    {"name": "Sirach", "testament": "ot", "aliases": ["ecclesiasticus", "ecclus", "sir"]},
    {"name": "Baruch", "testament": "ot", "aliases": ["bar"]},
    {"name": "Letter of Jeremiah", "testament": "ot", "aliases": ["ep jer"]},
    {"name": "Song of the Three", "testament": "ot", "aliases": ["pr azar", "prayer of azariah", "song of the three jews", "song of the three young men"]},
    {"name": "Susanna", "testament": "ot", "aliases": ["sus"]},
    {"name": "Bel and the Dragon", "testament": "ot", "aliases": ["bel"]},
    {"name": "1 Maccabees", "testament": "ot", "aliases": ["1 macc", "1 mc"]},
    {"name": "2 Maccabees", "testament": "ot", "aliases": ["2 macc", "2 mc"]},
    {"name": "3 Maccabees", "testament": "ot", "aliases": ["3 macc", "3 mc"]},
    {"name": "4 Maccabees", "testament": "ot", "aliases": ["4 macc", "4 mc"]},
    {"name": "1 Esdras", "testament": "ot", "aliases": ["1 esd"]},
    {"name": "2 Esdras", "testament": "ot", "aliases": ["2 esd"]},
    {"name": "Prayer of Manasseh", "testament": "ot", "aliases": ["pr man"]},
    {"name": "Psalm 151", "testament": "psalm", "aliases": []},
    {"name": "Matthew", "testament": "nt", "aliases": ["matt", "mt"]},
    {"name": "Mark", "testament": "nt", "aliases": ["mk"]},
    {"name": "Luke", "testament": "nt", "aliases": ["lk"]},
    {"name": "John", "testament": "nt", "aliases": ["jn"]},
    {"name": "Acts", "testament": "nt", "aliases": []},
    {"name": "Romans", "testament": "nt", "aliases": ["rom"]},
    {"name": "1 Corinthians", "testament": "nt", "aliases": ["1 cor"]},
    {"name": "2 Corinthians", "testament": "nt", "aliases": ["2 cor"]},
    {"name": "Galatians", "testament": "nt", "aliases": ["gal"]},
    {"name": "Ephesians", "testament": "nt", "aliases": ["eph"]},
    {"name": "Philippians", "testament": "nt", "aliases": ["phil"]},
    {"name": "Colossians", "testament": "nt", "aliases": ["col"]},
    {"name": "1 Thessalonians", "testament": "nt", "aliases": ["1 thess"]},
    {"name": "2 Thessalonians", "testament": "nt", "aliases": ["2 thess"]},
    {"name": "1 Timothy", "testament": "nt", "aliases": ["1 tim"]},
    {"name": "2 Timothy", "testament": "nt", "aliases": ["2 tim"]},
    {"name": "Titus", "testament": "nt", "aliases": ["tit"]},
    {"name": "Philemon", "testament": "nt", "aliases": ["philem", "phlm"]},
    {"name": "Hebrews", "testament": "nt", "aliases": ["heb"]},
    {"name": "James", "testament": "nt", "aliases": ["jas"]},
    {"name": "1 Peter", "testament": "nt", "aliases": ["1 pet"]},
    {"name": "2 Peter", "testament": "nt", "aliases": ["2 pet"]},
    {"name": "1 John", "testament": "nt", "aliases": ["1 jn"]},
    {"name": "2 John", "testament": "nt", "aliases": ["2 jn"]},
    {"name": "3 John", "testament": "nt", "aliases": ["3 jn"]},
    {"name": "Jude", "testament": "nt", "aliases": []},
    {"name": "Revelation", "testament": "nt", "aliases": ["rev"]}
  ],
  "split_alternatives": [
    {"ref": "John 20:1-18 or Matthew 28:1-10", "expected": ["John 20:1-18", "Matthew 28:1-10"]},
    {"ref": "John 20:1-18 OR Matthew 28:1-10", "expected": ["John 20:1-18", "Matthew 28:1-10"]},
    {"ref": "John 20:1-18 Or Matthew 28:1-10", "expected": ["John 20:1-18", "Matthew 28:1-10"]},
    {"ref": "Jeremiah 1:4-10 or  Isaiah 6:1-8 or Ezekiel 2:1-7", "expected": ["Jeremiah 1:4-10", "Isaiah 6:1-8", "Ezekiel 2:1-7"]},
    {"ref": "Psalm 105:1-11, 45b or Psalm 128", "expected": ["Psalm 105:1-11, 45b", "Psalm 128"]},
    {"ref": "Baruch 3:9-15, 3:32-4:4 or Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19", "expected": ["Baruch 3:9-15, 3:32-4:4", "Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19"]},
    {"ref": "  Luke 24:13-35  ", "expected": ["Luke 24:13-35"]},
    {"ref": "Song of the Three 35-65 or Psalm 148", "expected": ["Song of the Three 35-65", "Psalm 148"]},
    {"ref": "", "expected": []}
  ],
  "split_book": [
    {"ref": "Matthew 17:1-9", "expected": {"book": "Matthew", "rest": "17:1-9"}},
    {"ref": "1 John 3:1-7", "expected": {"book": "1 John", "rest": "3:1-7"}},
    {"ref": "John 3:1-17", "expected": {"book": "John", "rest": "3:1-17"}},
    {"ref": "1john 4:7-21", "expected": {"book": "1 John", "rest": "4:7-21"}},
    {"ref": "1John4:7", "expected": {"book": "1 John", "rest": "4:7"}},
    {"ref": "I Cor. 13:1-13", "expected": {"book": "1 Corinthians", "rest": "13:1-13"}},
    {"ref": "Song of Songs 2:8-13", "expected": {"book": "Song of Songs", "rest": "2:8-13"}},
    {"ref": "Song 2:8-13", "expected": {"book": "Song of Songs", "rest": "2:8-13"}},
    {"ref": "Song of the Three 35-65", "expected": {"book": "Song of the Three", "rest": "35-65"}},
    {"ref": "Isaiah 9:2-7", "expected": {"book": "Isaiah", "rest": "9:2-7"}},
    {"ref": "Is 9:6", "expected": null},
    {"ref": "Philemon 1:1-21", "expected": {"book": "Philemon", "rest": "1:1-21"}},
    {"ref": "Phil 4:4-7", "expected": {"book": "Philippians", "rest": "4:4-7"}},
    {"ref": "Ecclesiasticus 27:4-7", "expected": {"book": "Sirach", "rest": "27:4-7"}},
    {"ref": "Ecclesiastes 3:1-13", "expected": {"book": "Ecclesiastes", "rest": "3:1-13"}},
    {"ref": "Judges 4:1-7", "expected": {"book": "Judges", "rest": "4:1-7"}},
    {"ref": "Jude 1:17-25", "expected": {"book": "Jude", "rest": "1:17-25"}},
    {"ref": "Johnny 3:16", "expected": null},
    {"ref": "John", "expected": {"book": "John", "rest": ""}},
    {"ref": "* Acts 2:14a, 22-32", "expected": {"book": "Acts", "rest": "2:14a, 22-32"}},
    {"ref": "Gen. 1:1-5", "expected": {"book": "Genesis", "rest": "1:1-5"}},
    {"ref": "II Kings 2:1-12", "expected": {"book": "2 Kings", "rest": "2:1-12"}},
    {"ref": "III John 1:1-8", "expected": {"book": "3 John", "rest": "1:1-8"}},
    {"ref": "IV Maccabees 1:1", "expected": {"book": "4 Maccabees", "rest": "1:1"}},
    {"ref": "First Samuel 3:1-10", "expected": {"book": "1 Samuel", "rest": "3:1-10"}},
    {"ref": "Second Corinthians 5:17", "expected": {"book": "2 Corinthians", "rest": "5:17"}},
    {"ref": "Third John 1:11", "expected": {"book": "3 John", "rest": "1:11"}},
    {"ref": "Fourth Maccabees 1:1", "expected": {"book": "4 Maccabees", "rest": "1:1"}},
    {"ref": "1st Peter 2:9", "expected": {"book": "1 Peter", "rest": "2:9"}},
    {"ref": "2nd Timothy 1:5", "expected": {"book": "2 Timothy", "rest": "1:5"}},
    {"ref": "3rd John 1:2", "expected": {"book": "3 John", "rest": "1:2"}},
    {"ref": "4th Maccabees 1:1", "expected": {"book": "4 Maccabees", "rest": "1:1"}},
    {"ref": "1  John   3:16", "expected": {"book": "1 John", "rest": "3:16"}},
    {"ref": "Psalm 23", "expected": {"book": "Psalms", "rest": "23"}},
    {"ref": "Pss. 42", "expected": {"book": "Psalms", "rest": "42"}},
    {"ref": "Psalm 151", "expected": {"book": "Psalm 151", "rest": ""}},
    {"ref": "Wisdom of Solomon 1:13-15; 2:23-24", "expected": {"book": "Wisdom of Solomon", "rest": "1:13-15; 2:23-24"}},
    {"ref": "Bel and the Dragon 1:1-22", "expected": {"book": "Bel and the Dragon", "rest": "1:1-22"}},
    {"ref": "3:1-7", "expected": null},
    {"ref": "", "expected": null}
  ],
  "classify": [
    {"ref": "Matthew 21:33-46", "expected": "nt"},
    {"ref": "Mt 5:1-12", "expected": "nt"},
    {"ref": "Matt. 5:1-12", "expected": "nt"},
    {"ref": "Mk 1:1-8", "expected": "nt"},
    {"ref": "Lk 2:1-20", "expected": "nt"},
    {"ref": "Jn 3:16", "expected": "nt"},
    {"ref": "1 Jn 4:7", "expected": "nt"},
    {"ref": "I Cor. 12:1-11", "expected": "nt"},
    {"ref": "First Corinthians 13:1-13", "expected": "nt"},
    {"ref": "2 Tim 1:1-14", "expected": "nt"},
    {"ref": "Tit 2:11-14", "expected": "nt"},
    {"ref": "Phlm 1:1-21", "expected": "nt"},
    {"ref": "Rev 21:1-6a", "expected": "nt"},
    {"ref": "Acts 2:1-21", "expected": "nt"},
    {"ref": "Psalm 23", "expected": "psalm"},
    {"ref": "Ps 23", "expected": "psalm"},
    {"ref": "Psa. 1", "expected": "psalm"},
    {"ref": "Psalms 1", "expected": "psalm"},
    {"ref": "Psalm 151", "expected": "psalm"},
    {"ref": "Isaiah 5:1-7", "expected": "ot"},
    {"ref": "Isa 9:2-7", "expected": "ot"},
    {"ref": "Exod 12:1-14", "expected": "ot"},
    {"ref": "1 Kgs 19:1-15", "expected": "ot"},
    {"ref": "Canticles 2:8-13", "expected": "ot"},
    {"ref": "Sirach 10:12-18", "expected": "ot"},
    {"ref": "Sir 27:4-7", "expected": "ot"},
    {"ref": "Ecclus 27:4", "expected": "ot"},
    {"ref": "Wis 2:23", "expected": "ot"},
    {"ref": "Baruch 5:1-9", "expected": "ot"},
    {"ref": "Bar 5:5", "expected": "ot"},
    {"ref": "Tobit 8:5-8", "expected": "ot"},
    {"ref": "Judith 9:11", "expected": "ot"},
    {"ref": "1 Macc 2:1", "expected": "ot"},
    {"ref": "2 Maccabees 7:1", "expected": "ot"},
    {"ref": "Prayer of Azariah 1:1", "expected": "ot"},
    {"ref": "Letter of Jeremiah 1:1", "expected": "ot"},
    {"ref": "Susanna 1:1", "expected": "ot"},
    {"ref": "1 Esdras 1:1", "expected": "ot"},
    {"ref": "Prayer of Manasseh 1:1", "expected": "ot"},
    {"ref": "Additions to Esther 1:1", "expected": "ot"},
    {"ref": "Hymn of Praise", "expected": "unknown"},
    {"ref": "Didache 1:1", "expected": "unknown"},
    {"ref": "Is 9:6", "expected": "unknown"},
    {"ref": "", "expected": "unknown"}
  ],
  "is_nt_ref": [
    {"ref": "Romans 8:1-11", "expected": true},
    {"ref": "1john 4:7-21", "expected": true},
    {"ref": "Psalm 118:1-2, 14-24", "expected": false},
    {"ref": "Isaiah 5:1-7", "expected": false},
    {"ref": "Call to Worship", "expected": false}
  ],
  "expand_ref_options": [
    {"refs": ["Isaiah 5:1-7", "Matthew 21:33-46 or Mark 12:1-12"], "expected": ["Isaiah 5:1-7", "Matthew 21:33-46", "Mark 12:1-12"]},
    {"refs": ["John 20:1-18 OR Matthew 28:1-10"], "expected": ["John 20:1-18", "Matthew 28:1-10"]},
    {"refs": ["Acts 10:34-43 or Jeremiah 31:1-6", "Colossians 3:1-4 or Acts 10:34-43"], "expected": ["Acts 10:34-43", "Jeremiah 31:1-6", "Colossians 3:1-4"]},
    {"refs": ["", "  Psalm 23  ", "   "], "expected": ["Psalm 23"]},
    {"refs": [], "expected": []}
  ],
  "clean_lines": [
    {"lines": [" Isaiah 5:1-7 ", "", "   ", "Psalm 80:7-15"], "expected": ["Isaiah 5:1-7", "Psalm 80:7-15"]},
    {"lines": ["Acts 10:34-43 or Jeremiah 31:1-6"], "expected": ["Acts 10:34-43 or Jeremiah 31:1-6"]},
    {"lines": [], "expected": []}
  ],
  "picker_options": [
    {"scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "expected": {"ot": ["Isaiah 5:1-7", "Psalm 80:7-15"], "nt": ["Philippians 3:4b-14", "Matthew 21:33-46"]}},
    {"scriptures": ["Acts 10:34-43 or Jeremiah 31:1-6", "Psalm 118:1-2, 14-24", "Colossians 3:1-4 or Acts 10:34-43", "John 20:1-18 or Matthew 28:1-10"], "expected": {"ot": ["Jeremiah 31:1-6", "Psalm 118:1-2, 14-24"], "nt": ["Acts 10:34-43", "Colossians 3:1-4", "John 20:1-18", "Matthew 28:1-10"]}},
    {"scriptures": ["Call to Worship", "Romans 1:1-7"], "expected": {"ot": ["Call to Worship"], "nt": ["Romans 1:1-7"]}},
    {"scriptures": ["", "  "], "expected": {"ot": [], "nt": []}}
  ],
  "resolve_readings": [
    {"name": "S: Isaiah lines, no picks (5a: RCL order, NT is the second reading, not the Psalm)", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"name": "S: Easter lines, no picks (5a: Easter order, Acts first)", "scriptures": ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Acts 10:34-43", "nt": "Colossians 3:1-4", "ot_auto": true, "nt_auto": true}},
    {"name": "S mixed: Easter lines, OT pick Psalm 118, automatic NT is Acts", "scriptures": ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"], "ot_pick": "Psalm 118:1-2, 14-24", "nt_pick": "", "expected": {"ot": "Psalm 118:1-2, 14-24", "nt": "Acts 10:34-43", "ot_auto": false, "nt_auto": true}},
    {"name": "S mixed: a list starting with an epistle, OT pick Psalm 23, automatic NT is Romans", "scriptures": ["Romans 8:1-11", "Psalm 23", "John 10:1-10"], "ot_pick": "Psalm 23", "nt_pick": "", "expected": {"ot": "Psalm 23", "nt": "Romans 8:1-11", "ot_auto": false, "nt_auto": true}},
    {"name": "S mixed: Isaiah lines, NT pick Matthew, automatic OT", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "", "nt_pick": "Matthew 21:33-46", "expected": {"ot": "Isaiah 5:1-7", "nt": "Matthew 21:33-46", "ot_auto": true, "nt_auto": false}},
    {"name": "S stale: OT pick that is no longer a line", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "Isaiah 5:1-8", "nt_pick": "", "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"name": "S stale: a Psalm sent as the NT pick (5a: Psalm sent as NT pick)", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "", "nt_pick": "Psalm 80:7-15", "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"name": "S: only OT and Psalm, NT is None (5a: only OT and Psalm)", "scriptures": ["Isaiah 9:2-7", "Psalm 96"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Isaiah 9:2-7", "nt": null, "ot_auto": true, "nt_auto": true}},
    {"name": "5a stale: NT pick that is no longer a line", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "", "nt_pick": "Matthew 21:33-40", "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"name": "5a: gospel-only NT", "scriptures": ["Isaiah 60:1-6", "Psalm 72:1-7, 10-14", "Matthew 2:1-12"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Isaiah 60:1-6", "nt": "Matthew 2:1-12", "ot_auto": true, "nt_auto": true}},
    {"name": "5a: an ' or ' entry is the automatic NT and prints whole", "scriptures": ["Isaiah 9:2-7", "Psalm 96", "Luke 2:1-14 or Luke 2:1-20"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Isaiah 9:2-7", "nt": "Luke 2:1-14 or Luke 2:1-20", "ot_auto": true, "nt_auto": true}},
    {"name": "5a: selected refs win on both sides", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "Psalm 80:7-15", "nt_pick": "Matthew 21:33-46", "expected": {"ot": "Psalm 80:7-15", "nt": "Matthew 21:33-46", "ot_auto": false, "nt_auto": false}},
    {"name": "5a: blank entries are ignored", "scriptures": ["", "  ", "Isaiah 5:1-7", "", "Philippians 3:4b-14"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"name": "A13: whole-line compare; OT pick is an alternative of the first line, so that whole line is the automatic NT", "scriptures": ["Acts 10:34-43 or Jeremiah 31:1-6", "Psalm 118:1-2, 14-24", "Colossians 3:1-4 or Acts 10:34-43", "John 20:1-18 or Matthew 28:1-10"], "ot_pick": "Jeremiah 31:1-6", "nt_pick": "", "expected": {"ot": "Jeremiah 31:1-6", "nt": "Acts 10:34-43 or Jeremiah 31:1-6", "ot_auto": false, "nt_auto": true}},
    {"name": "case-insensitive or: NT pick is one alternative of an OR line", "scriptures": ["Isaiah 9:2-7", "Psalm 96", "Titus 2:11-14", "Luke 2:1-14 OR Luke 2:1-20"], "ot_pick": "", "nt_pick": "Luke 2:1-20", "expected": {"ot": "Isaiah 9:2-7", "nt": "Luke 2:1-20", "ot_auto": true, "nt_auto": false}},
    {"name": "picks are trimmed before the option check", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": " Psalm 80:7-15 ", "nt_pick": "", "expected": {"ot": "Psalm 80:7-15", "nt": "Philippians 3:4b-14", "ot_auto": false, "nt_auto": true}},
    {"name": "stale: an NT line sent as the OT pick is automatic", "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "ot_pick": "Matthew 21:33-46", "nt_pick": "", "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"name": "unknown first line is the automatic OT", "scriptures": ["Call to Worship", "Romans 8:1-11"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Call to Worship", "nt": "Romans 8:1-11", "ot_auto": true, "nt_auto": true}},
    {"name": "deuterocanon first reading", "scriptures": ["Wisdom of Solomon 1:13-15; 2:23-24", "Psalm 30", "2 Corinthians 8:7-15", "Mark 5:21-43"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Wisdom of Solomon 1:13-15; 2:23-24", "nt": "2 Corinthians 8:7-15", "ot_auto": true, "nt_auto": true}},
    {"name": "abbreviations and roman numerals", "scriptures": ["Isaiah 62:1-5", "Psalm 36:5-10", "I Cor. 12:1-11", "Jn 2:1-11"], "ot_pick": "", "nt_pick": "", "expected": {"ot": "Isaiah 62:1-5", "nt": "I Cor. 12:1-11", "ot_auto": true, "nt_auto": true}},
    {"name": "no lines", "scriptures": [], "ot_pick": "", "nt_pick": "", "expected": {"ot": null, "nt": null, "ot_auto": true, "nt_auto": true}},
    {"name": "only blank lines, picks ignored", "scriptures": ["", "   "], "ot_pick": "Psalm 23", "nt_pick": "John 3:16", "expected": {"ot": null, "nt": null, "ot_auto": true, "nt_auto": true}}
  ],
  "default_reading_pair": [
    {"scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "expected": {"ot": "Isaiah 5:1-7", "nt": "Philippians 3:4b-14", "ot_auto": true, "nt_auto": true}},
    {"scriptures": ["Acts 10:34-43 or Jeremiah 31:1-6", "Psalm 118:1-2, 14-24", "Colossians 3:1-4 or Acts 10:34-43", "John 20:1-18 or Matthew 28:1-10"], "expected": {"ot": "Acts 10:34-43 or Jeremiah 31:1-6", "nt": "Colossians 3:1-4 or Acts 10:34-43", "ot_auto": true, "nt_auto": true}},
    {"scriptures": ["Psalm 23"], "expected": {"ot": "Psalm 23", "nt": null, "ot_auto": true, "nt_auto": true}}
  ],
  "default_nt_ref": [
    {"scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"], "expected": "Philippians 3:4b-14"},
    {"scriptures": ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"], "expected": "Colossians 3:1-4"},
    {"scriptures": ["Isaiah 9:2-7", "Psalm 96"], "expected": null},
    {"scriptures": ["Psalm 23", "Psalm 24"], "expected": null}
  ],
  "scripture_key": [
    {"ref": "Luke 2:1-14 (15-20)", "expected": "luke2:1-1415-20"},
    {"ref": "Luke 2:1-14, (15-20)", "expected": "luke2:1-1415-20"},
    {"ref": "Isaiah 50:4-9a", "expected": "isaiah50:4-9"},
    {"ref": "Philippians 3:4b-14", "expected": "philippians3:4-14"},
    {"ref": "Luke 24:13-35b", "expected": "luke24:13-35"},
    {"ref": "John 1:1\u201314", "expected": "john1:1-14"},
    {"ref": "John 1:1\u201414", "expected": "john1:1-14"},
    {"ref": "John 1:(1-9), 10-18", "expected": "john1:1-910-18"},
    {"ref": "* Acts 2:14a, 22-32", "expected": "acts2:1422-32"},
    {"ref": "Luke 2:1-14 15-20", "expected": "luke2:1-1415-20"},
    {"ref": "Luke  2:1-14,, 15-20", "expected": "luke2:1-1415-20"},
    {"ref": "Gen. 1:1-5", "expected": "gen1:1-5"}
  ]
}
```

Then add the fixture's provenance to the fixtures README, unless Task 1 already wrote a `## shared/` section:

```bash
grep -q '^## shared/' backend/tests/fixtures/README.md || cat >> backend/tests/fixtures/README.md <<'README'

## shared/

- `shared/scripture_refs.json` is hand-written, not recorded, so it has no `.meta.json` sidecar. It is the authority for `backend/scripture_refs.py` and for 2b's `frontend/src/lib/scripture-refs.ts`: change a case here first, then both ports. `backend/tests/test_scripture_refs.py` runs it in pytest; 2b's `lib/scripture-refs.test.ts` reads it with `fs` from `../backend/tests/fixtures/shared/`. The top-level `"_about"` key documents each section's encoding. Slice 5a adds its `doc_readings` cases to the `resolve_readings` section.
README
tail -4 backend/tests/fixtures/README.md
```

**Expected:** the last lines of the README are its `## shared/` section (Task 1's own, or the one above).

- [ ] **Step 3 (agent): Write the failing tests**

Create `backend/tests/test_scripture_refs.py`:

```python
"""scripture_refs (S `scripture_refs.py`; spec decision 9; AC8, Python half).

The shared fixture pins everything slice 2b's lib/scripture-refs.ts ports, and
2b's Vitest file reads the same JSON. Fixture tests loop over their cases inside
one test, so the count stays stable when 5a adds cases. The fetch-only helpers
(normalize_for_fetch, split_parts, split_joined) are Python-only (S :722).
"""
import dataclasses
import json
from pathlib import Path

import pytest

import scripture_refs as sr

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "shared" / "scripture_refs.json"
SECTIONS = (
    "books", "split_alternatives", "split_book", "classify", "is_nt_ref",
    "expand_ref_options", "clean_lines", "picker_options", "resolve_readings",
    "default_reading_pair", "default_nt_ref", "scripture_key",
)

ISAIAH = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"]
EASTER = ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"]

# Every resolve_readings example in S `scripture_refs.py`, verbatim:
# (scriptures, ot_pick, nt_pick, (ot, nt, ot_auto, nt_auto)).
SPEC_RESOLVE_EXAMPLES = [
    (ISAIAH, "", "", ("Isaiah 5:1-7", "Philippians 3:4b-14", True, True)),
    (EASTER, "", "", ("Acts 10:34-43", "Colossians 3:1-4", True, True)),
    (EASTER, "Psalm 118:1-2, 14-24", "", ("Psalm 118:1-2, 14-24", "Acts 10:34-43", False, True)),
    (["Romans 8:1-11", "Psalm 23", "John 10:1-10"], "Psalm 23", "",
     ("Psalm 23", "Romans 8:1-11", False, True)),
    (ISAIAH, "", "Matthew 21:33-46", ("Isaiah 5:1-7", "Matthew 21:33-46", True, False)),
    (ISAIAH, "Isaiah 5:1-8", "", ("Isaiah 5:1-7", "Philippians 3:4b-14", True, True)),
    (ISAIAH, "", "Psalm 80:7-15", ("Isaiah 5:1-7", "Philippians 3:4b-14", True, True)),
    (["Isaiah 9:2-7", "Psalm 96"], "", "", ("Isaiah 9:2-7", None, True, True)),
]

# Case-name needles for the categories S Testing and 5a's doc_readings.json require.
REQUIRED_RESOLVE_CASES = (
    "S mixed: Easter lines, OT pick Psalm 118",
    "S mixed: a list starting with an epistle",
    "S mixed: Isaiah lines, NT pick Matthew",
    "S stale: OT pick that is no longer a line",
    "5a: RCL order",
    "5a: only OT and Psalm",
    "5a: gospel-only NT",
    "5a: an ' or ' entry",
    "5a: selected refs win",
    "5a: Easter order",
    "5a: blank entries",
    "5a stale: NT pick that is no longer a line",
    "5a: Psalm sent as NT pick",
    "A13: whole-line compare",
    "case-insensitive or",
    "deuterocanon",
    "abbreviations and roman numerals",
    "unknown first line",
)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _pair(pair: sr.ReadingPair) -> dict:
    return dataclasses.asdict(pair)


def test_fixture_books_match_BOOKS():
    assert _fixture()["books"] == [
        {"name": b.name, "testament": b.testament, "aliases": list(b.aliases)} for b in sr.BOOKS
    ]
    assert len(sr.BOOKS) == 66 + 18                       # the canon plus the S deuterocanon list
    assert sum(b.testament == "nt" for b in sr.BOOKS) == 27
    assert {b.name for b in sr.BOOKS if b.testament == "psalm"} == {"Psalms", "Psalm 151"}
    keys = [sr.normalize_book_text(b.name) for b in sr.BOOKS] + [a for b in sr.BOOKS for a in b.aliases]
    assert len(keys) == len(set(keys))                    # every lookup key names one book
    assert all(a == sr.normalize_book_text(a) for b in sr.BOOKS for a in b.aliases)
    with pytest.raises(dataclasses.FrozenInstanceError):
        sr.BOOKS[0].name = "Changed"


def test_fixture_split_alternatives():
    for case in _fixture()["split_alternatives"]:
        assert sr.split_alternatives(case["ref"]) == case["expected"], case["ref"]


def test_fixture_split_book():
    for case in _fixture()["split_book"]:
        hit = sr.split_book(case["ref"])
        got = None if hit is None else {"book": hit[0].name, "rest": hit[1]}
        assert got == case["expected"], case["ref"]


def test_fixture_classify_and_is_nt_ref():
    data = _fixture()
    for case in data["classify"]:
        assert sr.classify(case["ref"]) == case["expected"], case["ref"]
        assert sr.is_nt_ref(case["ref"]) is (case["expected"] == "nt"), case["ref"]
    for case in data["is_nt_ref"]:
        assert sr.is_nt_ref(case["ref"]) is case["expected"], case["ref"]


def test_fixture_expand_ref_options_and_clean_lines():
    data = _fixture()
    for case in data["expand_ref_options"]:
        assert sr.expand_ref_options(case["refs"]) == case["expected"], case["refs"]
    for case in data["clean_lines"]:
        assert sr.clean_lines(case["lines"]) == case["expected"], case["lines"]


def test_fixture_picker_options():
    for case in _fixture()["picker_options"]:
        assert sr.picker_options(case["scriptures"]) == case["expected"], case["scriptures"]


def test_fixture_resolve_readings():
    for case in _fixture()["resolve_readings"]:
        got = sr.resolve_readings(case["scriptures"], case["ot_pick"], case["nt_pick"])
        assert _pair(got) == case["expected"], case["name"]
        if got.nt_auto and got.nt is not None:            # never a Psalm as the automatic NT
            assert sr.is_nt_ref(sr.split_alternatives(got.nt)[0]), case["name"]


def test_fixture_default_reading_pair_and_default_nt_ref():
    data = _fixture()
    for case in data["default_reading_pair"]:
        assert _pair(sr.default_reading_pair(case["scriptures"])) == case["expected"], case["scriptures"]
    for case in data["default_nt_ref"]:
        assert sr.default_nt_ref(case["scriptures"]) == case["expected"], case["scriptures"]
    for case in data["resolve_readings"]:
        s = case["scriptures"]
        assert sr.default_reading_pair(s) == sr.resolve_readings(s, "", ""), case["name"]
        assert sr.default_nt_ref(s) == sr.resolve_readings(s).nt, case["name"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        sr.default_reading_pair(ISAIAH).nt = "John 3:16"


def test_fixture_scripture_key():
    for case in _fixture()["scripture_key"]:
        assert sr.scripture_key(case["ref"]) == case["expected"], case["ref"]


def test_normalize_book_text():
    cases = {
        "  *1 John 3:1-3": "1 john 3:1-3",
        "* Acts 2:14a": "acts 2:14a",
        "Gen.  1:1": "gen 1:1",
        "I Cor. 13:1": "1 cor 13:1",
        "II Kings 2:1-12": "2 kings 2:1-12",
        "III John 1": "3 john 1",
        "IV Maccabees 1:1": "4 maccabees 1:1",
        "First Samuel 3": "1 samuel 3",
        "Second Corinthians 5": "2 corinthians 5",
        "Third John": "3 john",
        "Fourth Maccabees": "4 maccabees",
        "1st Peter 2": "1 peter 2",
        "2nd Timothy": "2 timothy",
        "3rd John": "3 john",
        "4th Maccabees": "4 maccabees",
        "1john 3:16": "1 john 3:16",
        "Isaiah 9:2": "isaiah 9:2",
        "Iv": "iv",
        "  Psalm   23  ": "psalm 23",
    }
    for raw, expected in cases.items():
        assert sr.normalize_book_text(raw) == expected, raw


def test_fixture_has_every_section_and_about():
    data = _fixture()
    about = data["_about"]
    assert set(SECTIONS) <= set(data)
    for name in data:
        if name == "_about":
            continue
        assert data[name], f"{name} is empty"
        assert isinstance(about.get(name), str) and about[name], f"_about does not document {name}"
    assert '"book"' in about["split_book"] and "null" in about["split_book"]
    assert '"ot"' in about["picker_options"] and '"nt"' in about["picker_options"]
    assert "snake_case" in about["resolve_readings"] and "otAuto" in about["resolve_readings"]


def test_normalize_for_fetch():
    cases = {
        "Isaiah 50:4-9a": "Isaiah 50:4-9",
        "Philippians 3:4b-14": "Philippians 3:4-14",
        "Luke 24:13-35b": "Luke 24:13-35",
        "John 1:1–14": "John 1:1-14",
        "John 1:1—14": "John 1:1-14",
        "Luke 2:1-14 (15-20)": "Luke 2:1-14, 15-20",
        "Luke 2:1-14, (15-20)": "Luke 2:1-14, 15-20",
        "John 1:(1-9), 10-18": "John 1:1-9, 10-18",
        "* Acts 2:14a, 22-32": "Acts 2:14, 22-32",
        "*Acts 2:14a": "Acts 2:14",
        "Luke 2:1-14 15-20": "Luke 2:1-14, 15-20",
        "Luke 2:1-14,, 15-20": "Luke 2:1-14, 15-20",
        "Luke  2:1-14": "Luke 2:1-14",
        "1 John 3:1-7": "1 John 3:1-7",
        "Genesis 2:15-17; 3:1-7": "Genesis 2:15-17; 3:1-7",
        "Proverbs 8:1-8, 19-21; 9:4b-6": "Proverbs 8:1-8, 19-21; 9:4-6",
    }
    for raw, expected in cases.items():
        assert sr.normalize_for_fetch(raw) == expected, raw


def test_split_parts_carries_book_and_keeps_quirks():
    assert sr.split_parts("Genesis 2:15-17; 3:1-7") == ["Genesis 2:15-17", "Genesis 3:1-7"]
    assert sr.split_parts("2 Kings 2:1-12") == ["2 Kings 2:1-12"]
    assert sr.split_parts("Proverbs 8:1-8, 19-21; 9:4b-6") == ["Proverbs 8:1-8, 19-21", "Proverbs 9:4b-6"]
    assert sr.split_parts("Wisdom of Solomon 1:13-15; 2:23-24") == [
        "Wisdom of Solomon 1:13-15", "Wisdom of Solomon 2:23-24"]
    assert sr.split_parts(" Isaiah 9:1-4; ; 9:5-7; ") == ["Isaiah 9:1-4", "Isaiah 9:5-7"]
    # Quirks kept from scripture_fetcher.fetch_passage: a bare chapter is not carried,
    # and a first part with no chapter:verse never sets the book.
    assert sr.split_parts("Psalm 42; 43") == ["Psalm 42", "43"]
    assert sr.split_parts("Psalm 42; 43:1-5") == ["Psalm 42", "43:1-5"]
    assert sr.split_parts(";") == []
    assert sr.split_parts("") == []


def test_split_joined():
    assert sr.split_joined("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26") == [
        "Genesis 1:1-2:4a", "Psalm 136:1-9, 23-26"]
    assert sr.split_joined("Psalm 42 and 43") == ["Psalm 42 and 43"]
    assert sr.split_joined("Ezekiel 36:24-28 and Psalm 42 and 43") == ["Ezekiel 36:24-28", "Psalm 42 and 43"]
    assert sr.split_joined("Romans 6:3-11 and Psalm 114") == ["Romans 6:3-11", "Psalm 114"]
    assert sr.split_joined("Bel and the Dragon 1:1-22") == ["Bel and the Dragon 1:1-22"]
    assert sr.split_joined("  Luke 24:1-12  ") == ["Luke 24:1-12"]
    assert sr.split_joined("") == []


def test_every_spec_example_is_in_the_fixture():
    data = _fixture()
    resolve = [(c["scriptures"], c["ot_pick"], c["nt_pick"], c["expected"]) for c in data["resolve_readings"]]
    for scriptures, ot_pick, nt_pick, (ot, nt, ot_auto, nt_auto) in SPEC_RESOLVE_EXAMPLES:
        expected = {"ot": ot, "nt": nt, "ot_auto": ot_auto, "nt_auto": nt_auto}
        assert (scriptures, ot_pick, nt_pick, expected) in resolve, (scriptures, ot_pick, nt_pick)
    names = " | ".join(c["name"] for c in data["resolve_readings"])
    for needle in REQUIRED_RESOLVE_CASES:
        assert needle in names, needle
    # S Testing: split_book's longest alias, "1 John" vs "John", "1john", "I Cor.", "Song of Songs"
    split_book_refs = {c["ref"] for c in data["split_book"]}
    for ref in ("Matthew 17:1-9", "1 John 3:1-7", "John 3:1-17", "1john 4:7-21",
                "I Cor. 13:1-13", "Song of Songs 2:8-13", "Song of the Three 35-65"):
        assert ref in split_book_refs, ref
    # S :881: abbreviations, roman numerals, deuterocanon and unknown all classified
    assert {c["expected"] for c in data["classify"]} == {"ot", "psalm", "nt", "unknown"}
    # S normalize_for_fetch examples and the scripture_key equality
    keys = {c["ref"]: c["expected"] for c in data["scripture_key"]}
    assert keys["Luke 2:1-14 (15-20)"] == keys["Luke 2:1-14, (15-20)"] == "luke2:1-1415-20"
    assert keys["Isaiah 50:4-9a"] == "isaiah50:4-9"
```

- [ ] **Step 4 (agent): Extend the layering gate**

In `backend/tests/test_no_streamlit_in_core.py`, `test_usecases_package_imports_no_fastapi_or_streamlit`, replace Task 3's line

```python
            "token_bucket, integrations.budget; "
```

with

```python
            "token_bucket, integrations.budget, scripture_refs; "
```

(If Step 1 found no such line, add `scripture_refs` as the last module of the same import list, before the `; `.) The comment above the `code` string is unchanged.

- [ ] **Step 5 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_scripture_refs.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_scripture_refs.py 2>&1 | grep -m1 ModuleNotFoundError
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected,** in order:
- `ERROR backend/tests/test_scripture_refs.py`, `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in <t>s`;
- a line ending `ModuleNotFoundError: No module named 'scripture_refs'` (the module does not exist yet; the fixture itself loads);
- `1 failed, 2 passed in <t>s` (the import gate fails with the same `ModuleNotFoundError` in its subprocess).

- [ ] **Step 6 (agent): Create `backend/scripture_refs.py`**

```python
"""Scripture references: the book table, the OT/NT classifier, the reading
pickers, the one bulletin-reading rule, and fetch normalization
(S `scripture_refs.py`; spec decision 9; F §5.3).

Pure: no I/O, no FastAPI, no Streamlit. `lib/scripture-refs.ts` (slice 2b)
ports everything above "Fetch only" and runs the same shared fixture,
`backend/tests/fixtures/shared/scripture_refs.json`. The fixture is
authoritative: change it first, then both ports.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional

Testament = Literal["ot", "psalm", "nt"]


@dataclass(frozen=True)
class Book:
    """A canonical book. `aliases` are stored normalized (see
    `normalize_book_text`: lower-case, no periods, arabic numerals), so
    "Gen" and "Gen." both match the alias "gen". The canonical name also
    matches and is not repeated in `aliases`."""

    name: str
    testament: Testament
    aliases: tuple[str, ...] = ()


BOOKS: tuple[Book, ...] = (
    # Old Testament
    Book("Genesis", "ot", ("gen",)),
    Book("Exodus", "ot", ("ex", "exod")),
    Book("Leviticus", "ot", ("lev",)),
    Book("Numbers", "ot", ("num",)),
    Book("Deuteronomy", "ot", ("deut",)),
    Book("Joshua", "ot", ("josh",)),
    Book("Judges", "ot", ("judg",)),
    Book("Ruth", "ot"),
    Book("1 Samuel", "ot", ("1 sam",)),
    Book("2 Samuel", "ot", ("2 sam",)),
    Book("1 Kings", "ot", ("1 kgs",)),
    Book("2 Kings", "ot", ("2 kgs",)),
    Book("1 Chronicles", "ot", ("1 chr", "1 chron")),
    Book("2 Chronicles", "ot", ("2 chr", "2 chron")),
    Book("Ezra", "ot"),
    Book("Nehemiah", "ot", ("neh",)),
    Book("Esther", "ot", ("esth",)),
    Book("Job", "ot"),
    Book("Psalms", "psalm", ("ps", "psa", "psalm", "pss")),
    Book("Proverbs", "ot", ("prov",)),
    Book("Ecclesiastes", "ot", ("eccl",)),
    Book("Song of Songs", "ot", ("canticles", "song", "song of solomon")),
    Book("Isaiah", "ot", ("isa",)),
    Book("Jeremiah", "ot", ("jer",)),
    Book("Lamentations", "ot", ("lam",)),
    Book("Ezekiel", "ot", ("ezek",)),
    Book("Daniel", "ot", ("dan",)),
    Book("Hosea", "ot", ("hos",)),
    Book("Joel", "ot"),
    Book("Amos", "ot"),
    Book("Obadiah", "ot", ("obad",)),
    Book("Jonah", "ot"),
    Book("Micah", "ot", ("mic",)),
    Book("Nahum", "ot", ("nah",)),
    Book("Habakkuk", "ot", ("hab",)),
    Book("Zephaniah", "ot", ("zeph",)),
    Book("Haggai", "ot", ("hag",)),
    Book("Zechariah", "ot", ("zech",)),
    Book("Malachi", "ot", ("mal",)),
    # Deuterocanon: "ot", except Psalm 151, which is a psalm
    Book("Tobit", "ot", ("tb", "tob")),
    Book("Judith", "ot", ("jdt", "jth")),
    Book("Additions to Esther", "ot", ("add esth",)),
    Book("Wisdom of Solomon", "ot", ("wis", "wisdom", "ws")),
    Book("Sirach", "ot", ("ecclesiasticus", "ecclus", "sir")),
    Book("Baruch", "ot", ("bar",)),
    Book("Letter of Jeremiah", "ot", ("ep jer",)),
    Book("Song of the Three", "ot", ("pr azar", "prayer of azariah",
                                     "song of the three jews", "song of the three young men")),
    Book("Susanna", "ot", ("sus",)),
    Book("Bel and the Dragon", "ot", ("bel",)),
    Book("1 Maccabees", "ot", ("1 macc", "1 mc")),
    Book("2 Maccabees", "ot", ("2 macc", "2 mc")),
    Book("3 Maccabees", "ot", ("3 macc", "3 mc")),
    Book("4 Maccabees", "ot", ("4 macc", "4 mc")),
    Book("1 Esdras", "ot", ("1 esd",)),
    Book("2 Esdras", "ot", ("2 esd",)),
    Book("Prayer of Manasseh", "ot", ("pr man",)),
    Book("Psalm 151", "psalm"),
    # New Testament
    Book("Matthew", "nt", ("matt", "mt")),
    Book("Mark", "nt", ("mk",)),
    Book("Luke", "nt", ("lk",)),
    Book("John", "nt", ("jn",)),
    Book("Acts", "nt"),
    Book("Romans", "nt", ("rom",)),
    Book("1 Corinthians", "nt", ("1 cor",)),
    Book("2 Corinthians", "nt", ("2 cor",)),
    Book("Galatians", "nt", ("gal",)),
    Book("Ephesians", "nt", ("eph",)),
    Book("Philippians", "nt", ("phil",)),
    Book("Colossians", "nt", ("col",)),
    Book("1 Thessalonians", "nt", ("1 thess",)),
    Book("2 Thessalonians", "nt", ("2 thess",)),
    Book("1 Timothy", "nt", ("1 tim",)),
    Book("2 Timothy", "nt", ("2 tim",)),
    Book("Titus", "nt", ("tit",)),
    Book("Philemon", "nt", ("philem", "phlm")),
    Book("Hebrews", "nt", ("heb",)),
    Book("James", "nt", ("jas",)),
    Book("1 Peter", "nt", ("1 pet",)),
    Book("2 Peter", "nt", ("2 pet",)),
    Book("1 John", "nt", ("1 jn",)),
    Book("2 John", "nt", ("2 jn",)),
    Book("3 John", "nt", ("3 jn",)),
    Book("Jude", "nt"),
    Book("Revelation", "nt", ("rev",)),
)


def _alias_index() -> tuple[tuple[str, Book], ...]:
    """Every lookup key (the normalized name and each alias), longest first.
    A key that maps to two books is a table bug, so it fails at import."""
    index: dict[str, Book] = {}
    for book in BOOKS:
        for key in (normalize_book_text(book.name), *book.aliases):
            if key in index:
                raise ValueError(f"alias {key!r} is used by {index[key].name} and {book.name}")
            index[key] = book
    return tuple(sorted(index.items(), key=lambda kv: (-len(kv[0]), kv[0])))


_ORDINAL_PREFIX = re.compile(r"^(iii|ii|iv|i|first|second|third|fourth|1st|2nd|3rd|4th) ")
_ORDINAL_DIGIT = {
    "i": "1", "ii": "2", "iii": "3", "iv": "4",
    "first": "1", "second": "2", "third": "3", "fourth": "4",
    "1st": "1", "2nd": "2", "3rd": "3", "4th": "4",
}


def normalize_book_text(s: str) -> str:
    """Lower-case; drop a leading "*" and whitespace; remove "."; collapse
    spaces; map a roman or ordinal prefix followed by a space
    (i|ii|iii|iv|first|second|third|fourth|1st|2nd|3rd|4th) to 1–4, so
    "Isaiah" is untouched; then put a space after a leading 1–4 glued to a
    letter ("1john" → "1 john")."""
    s = s.lower()
    s = re.sub(r"^\s*\*?\s*", "", s)
    s = s.replace(".", "")
    s = re.sub(r"\s+", " ", s).strip()
    s = _ORDINAL_PREFIX.sub(lambda m: _ORDINAL_DIGIT[m.group(1)] + " ", s, count=1)
    s = re.sub(r"^([1-4])(?=[a-z])", r"\1 ", s)
    return s


_ALIASES = _alias_index()


def clean_lines(lines: list[str]) -> list[str]:
    """Trim each line and drop the blank ones."""
    return [line.strip() for line in lines if line and line.strip()]


def split_alternatives(ref: str) -> list[str]:
    """Split on " or " (any case, any whitespace around it) and trim; empty
    pieces are dropped. Fixes the case-sensitive split (inv. C9)."""
    return [p.strip() for p in re.split(r"\s+or\s+", ref, flags=re.IGNORECASE) if p.strip()]


def split_book(ref: str) -> Optional[tuple[Book, str]]:
    """The longest book name or alias at the start of the normalized text,
    followed by the end, a space or a digit. Returns the canonical book and
    the rest of the normalized text, trimmed ("Matthew 17:1-9" →
    (Matthew, "17:1-9")), or None."""
    text = normalize_book_text(ref)
    for key, book in _ALIASES:
        if text.startswith(key):
            after = text[len(key):]
            if after == "" or after[0] == " " or after[0] in "0123456789":
                return book, after.strip()
    return None


def classify(ref: str) -> Literal["ot", "psalm", "nt", "unknown"]:
    """The testament of one alternative's book, or "unknown"."""
    hit = split_book(ref)
    return hit[0].testament if hit else "unknown"


def is_nt_ref(ref: str) -> bool:
    """classify(ref) == "nt" (the name app.py used; slice 5a uses it)."""
    return classify(ref) == "nt"


def expand_ref_options(refs: list[str]) -> list[str]:
    """Clean the lines, expand every alternative, and de-duplicate in
    first-seen order (app.py's version was case-sensitive and kept
    duplicates)."""
    out: list[str] = []
    for line in clean_lines(refs):
        for alt in split_alternatives(line):
            if alt not in out:
                out.append(alt)
    return out


def picker_options(scriptures: list[str]) -> dict[str, list[str]]:
    """The two bulletin pickers: "nt" holds the NT options; "ot" holds
    everything else (ot, psalm and unknown), as app.py did."""
    options = expand_ref_options(scriptures)
    return {
        "ot": [o for o in options if classify(o) != "nt"],
        "nt": [o for o in options if classify(o) == "nt"],
    }


@dataclass(frozen=True)
class ReadingPair:
    ot: Optional[str]
    nt: Optional[str]
    ot_auto: bool
    nt_auto: bool


def _first_alternative_is_nt(line: str) -> bool:
    alternatives = split_alternatives(line)
    return bool(alternatives) and is_nt_ref(alternatives[0])


def resolve_readings(scriptures: list[str], ot_pick: Optional[str] = "",
                     nt_pick: Optional[str] = "") -> ReadingPair:
    """The only bulletin-reading rule (S `resolve_readings`; spec decision 9).

    A pick counts only when it is one of the current options for its side;
    otherwise that side is automatic. The automatic OT is the first line;
    the automatic NT is the first line other than the effective OT (whole-line
    comparison) whose first alternative is NT, so a Psalm is never the
    automatic NT. Lines are returned as written.
    """
    entries = clean_lines(scriptures)
    options = picker_options(entries)
    ot_pick = (ot_pick or "").strip()
    if ot_pick not in options["ot"]:
        ot_pick = ""
    nt_pick = (nt_pick or "").strip()
    if nt_pick not in options["nt"]:
        nt_pick = ""
    ot = ot_pick or (entries[0] if entries else None)
    nt = nt_pick or next((e for e in entries if e != ot and _first_alternative_is_nt(e)), None)
    return ReadingPair(ot=ot, nt=nt, ot_auto=not ot_pick, nt_auto=not nt_pick)


def default_reading_pair(scriptures: list[str]) -> ReadingPair:
    """resolve_readings with no picks."""
    return resolve_readings(scriptures, "", "")


def default_nt_ref(scriptures: list[str]) -> Optional[str]:
    """The automatic NT reading (slice 3's hymn matching uses it)."""
    return default_reading_pair(scriptures).nt


# ---- Fetch only (Python only; the displayed text never changes) ----------


def normalize_for_fetch(ref: str) -> str:
    """The text sent upstream: drop a leading "*"; en and em dashes → "-";
    drop a verse-part letter after a digit ("9a" → "9"); remove parentheses;
    put a comma between two verse groups separated only by whitespace
    ("1-14 15-20" → "1-14, 15-20"); collapse doubled commas and spaces."""
    s = re.sub(r"^\s*\*\s*", "", ref)
    s = s.replace("–", "-").replace("—", "-")
    s = re.sub(r"(?<=\d)[A-Za-z](?![A-Za-z])", "", s)
    s = s.replace("(", "").replace(")", "")
    s = re.sub(r"(?<=\d)\s+(?=\d)", ", ", s)
    s = re.sub(r",(\s*,)+", ",", s)
    return re.sub(r"\s+", " ", s).strip()


def _book_name_from_ref(ref: str) -> Optional[str]:
    """The book in "Genesis 2:15-17" or "2 Kings 2:1-12"; None without a
    chapter:verse."""
    m = re.match(r"^(.+?)\s+\d+:\d+", ref.strip())
    if not m:
        return None
    return m.group(1).strip()


def _expand_part(part: str, last_book: Optional[str]) -> str:
    """Prefix a bare "3:1-7" with the carried book."""
    part = part.strip()
    if re.match(r"^\d+:\d+", part) and last_book:
        return f"{last_book} {part}"
    return part


def split_parts(ref: str) -> list[str]:
    """Split on ";" (dropping empty pieces) and carry the book into parts
    shaped like "3:1-7". Moved unchanged from scripture_fetcher.fetch_passage,
    quirks included: "Psalm 42; 43" leaves "43" bare, and a first part with
    no chapter:verse never sets the book."""
    last_book: Optional[str] = None
    parts: list[str] = []
    for raw in (p.strip() for p in ref.strip().split(";")):
        if not raw:
            continue
        full = _expand_part(raw, last_book)
        if not last_book:
            last_book = _book_name_from_ref(full)
        parts.append(full)
    return parts


_AND = re.compile(r"\s+and\s+")


def split_joined(ref: str) -> list[str]:
    """Split on " and " only where the text after it starts with a known book
    (the Easter Vigil's paired lines), and trim. "Psalm 42 and 43" stays
    whole."""
    text = ref.strip()
    pieces: list[str] = []
    start = 0
    for m in _AND.finditer(text):
        if split_book(text[m.end():]) is not None:
            pieces.append(text[start:m.start()].strip())
            start = m.end()
    pieces.append(text[start:].strip())
    return [p for p in pieces if p]


def scripture_key(ref: str) -> str:
    """A comparison key: normalize_for_fetch, lower-case, then remove
    whitespace, commas, periods and parentheses."""
    return re.sub(r"[\s,.()]", "", normalize_for_fetch(ref).lower())
```

- [ ] **Step 7 (agent): Run the tests to verify they pass, and the whole suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_scripture_refs.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py backend/tests/test_fixtures_recorder.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected,** in order:
- `15 passed in <t>s`;
- `5 passed in <t>s` (the 3 import-gate tests, and Task 1's 2 fixture tests still pass with `shared/` present);
- `856 passed, 9 skipped in <t>s` (841 + 15).

If `test_fixtures_recorder.py` fails naming `shared/scripture_refs.json`, Task 1's check walks every fixture folder: stop and ask the controller (the shared fixture is not an upstream recording and must not get a fake `.meta.json`). If the suite line is not `856 passed, 9 skipped`, stop and find why (each task's delta equals its listed tests).

- [ ] **Step 8 (agent): Check the layering and the untouched files**

```bash
grep -nE '^(import|from) ' backend/scripture_refs.py
grep -cE 'fastapi|starlette|streamlit|httpx' backend/scripture_refs.py
git diff --quiet HEAD -- app.py backend/scripture_fetcher.py streamlit_views && echo "frozen files and scripture_fetcher untouched"
.venv/bin/python -c "import json; d = json.load(open('backend/tests/fixtures/shared/scripture_refs.json')); print(sorted(k for k in d if k != '_about')); print(len(d['books']), len(d['resolve_readings']))"
git status --short
```

**Expected,** in order:
- exactly `10:from __future__ import annotations`, `12:import re`, `13:from dataclasses import dataclass`, `14:from typing import Literal, Optional`;
- `0`;
- `frozen files and scripture_fetcher untouched`;
- `['books', 'classify', 'clean_lines', 'default_nt_ref', 'default_reading_pair', 'expand_ref_options', 'is_nt_ref', 'picker_options', 'resolve_readings', 'scripture_key', 'split_alternatives', 'split_book']` and `84 22`;
- `?? .claude/`, ` M backend/tests/test_no_streamlit_in_core.py`, `?? backend/scripture_refs.py`, `?? backend/tests/fixtures/shared/`, `?? backend/tests/test_scripture_refs.py`, and ` M backend/tests/fixtures/README.md` when Step 2 appended the section (in `git status` order).

- [ ] **Step 9 (agent): Commit**

```bash
git add backend/scripture_refs.py backend/tests/fixtures/shared/scripture_refs.json \
        backend/tests/fixtures/README.md backend/tests/test_scripture_refs.py \
        backend/tests/test_no_streamlit_in_core.py
git commit -m "Scripture refs: book table, classifier, resolve_readings and the shared fixture (S scripture_refs.py; decision 9)

scripture_refs.py is the one pure module for scripture references:
BOOKS (the 66 books and the deuterocanon, aliases stored normalized),
normalize_book_text, split_alternatives (any case), split_book (longest
alias), classify and is_nt_ref, expand_ref_options (de-duplicated),
picker_options, and resolve_readings, the only bulletin-reading rule: a
pick counts only when it is a current option for its side, and the
automatic NT is the first line other than the effective OT whose first
alternative is NT, so a Psalm is never the automatic NT (decision 9).
The fetch-only helpers normalize_for_fetch, split_parts (copied
unchanged; scripture_fetcher.py switches to it in Task 9), split_joined
and scripture_key are Python-only.

tests/fixtures/shared/scripture_refs.json pins every ported function for
2b's TypeScript port, with an _about key for its encodings (2a
clarification 40), every S example, the mixed and stale-pick cases, the
whole-line compare (clarification 16) and 5a's doc_readings categories.
The import gate now covers scripture_refs.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

**Expected:** `<sha> Scripture refs: book table, classifier, resolve_readings and the shared fixture (S scripture_refs.py; decision 9)`.
### Task 6a: Lectionary calendar and occasion names (S Lectionary domain "Year file" and "Names for Lectio-only sets", "Ordinary-time occasion names"; decision A; owner answer Q3; AC4 names half; clarifications 9, 30)

This task adds the pure calendar and the occasion names to `backend/vanderbilt_lectionary.py`: `easter_date`, `advent_sunday`, `liturgical_year_for` (the Advent-boundary fix, inv. C2), the ordinal words, `sunday_name`, `weekday_feast_name`, `_ordinary_time_name`, the two Lectio types and `lectio_set_name`. It is date arithmetic only: no fixtures, no network, no clock, no logging. The change is **additive**: the new names sit in a new section at the end of the file, and every line of the Streamlit-era code above it stays byte-for-byte as it is (Task 7 deletes that code, including the private `_easter_date`, which `easter_date` replaces). T6 is split into two review checkpoints (critique 21); Task 6b appends the parsing and merge to the same module and the same test file, and both halves ship in the one 2a PR.

**Owner answer Q3 (2026-09-28, binding) lands here.** `sunday_name` also names the Christmas-season Sundays: a Sunday from Dec 26 to Jan 1 is "First Sunday after Christmas Day", and a Sunday from Jan 2 to Jan 5 is "Second Sunday after Christmas Day". A Sunday Dec 25 or Jan 6 keeps `sunday_name(d) is None`, and `lectio_set_name` then tries `weekday_feast_name(d)`, so it is named "Nativity of the Lord" or "Epiphany of the Lord". With Q3, every Sunday from 1900 to 2199 gets a name from `sunday_name(d) or weekday_feast_name(d)`, so a Lectio-only Sunday set never falls back to "{season} — Year {year}". This is visible only when Vanderbilt fails, because Vanderbilt names these rows itself.

**Decisions recorded in this task (code wins over the outline; owner decision 1):**
- **T6a-1. `lectio_set_name` step 4 needs both `season` and `year`.** S lists `"{season} — Year {year}"` unconditionally; an empty season would give " — Year A". When either is blank, step 5 (the weekday's name) answers. Today's code does the same in its fallback branch (`vanderbilt_lectionary.py:295`).
- **T6a-2. `weekday_feast_name` is date-only.** It names Dec 24, Dec 25, Jan 1, Jan 6 and Nov 1 on any weekday, Sunday included (S's list says "otherwise `None`" with no weekday condition). Q3 relies on this. The Easter-relative feasts never fall on a Sunday.
- **T6a-3. `_ordinary_time_name(d)`** returns "{Ordinal} Sunday after the Epiphany" for Sundays from the Baptism of the Lord ("First") through Transfiguration Sunday, and "{Ordinal} Sunday after Pentecost" for Sundays from Trinity Sunday ("First") through Reign of Christ, with the same `n` as S. It returns None for every other date, including the Day of Pentecost. `sunday_name` checks the named days before calling it; Task 6b calls it directly for a Proper row on All Saints Day (clarification 30), where it gives "Twenty-Third Sunday after Pentecost" on 2026-11-01.
- **T6a-4. The old `_easter_date` stays until Task 7.** `easter_date` is a new public copy of the same algorithm, so the old path keeps working unchanged and Task 7's deletion list (which names `_easter_date`) still applies. The new tests never import `_easter_date`, so Task 7's deletion cannot break them.
- **T6a-5. `test_every_ordinary_sunday_named` is broader than the outline's wording.** With Q3 there is no Christmas-season gap left, so it checks every Sunday of every liturgical year from Advent 1900 to Advent 2199 (not only 2025-26 … 2027-28): each has a name without "Proper", except a Sunday Dec 25 or Jan 6, which has a feast name; and no Sunday name repeats within one liturgical year. The test count is unchanged (10).
- **T6a-6. `LectioDay.season` and `LectioDay.year` are `str`, `""` when missing.** Task 6b's `parse_lectio_payload` must coerce a missing or null value to `""` (for example `str(payload.get("season") or "")`), not `str(None)`, which would name a set "None — Year A".

**Files:**
- Modify: `backend/vanderbilt_lectionary.py:8-10` (the import block gains `from dataclasses import dataclass`) and append a new section after the last line (`:396`, `    return result`).
- Test: `backend/tests/test_lectionary_domain.py` (new, 10 tests; Task 6b appends to it).

**Interfaces:**
- Consumes:
  - nothing from Tasks 1–5. The autouse `_no_network` fixture (`backend/tests/conftest.py:195-196`) applies as usual; nothing here opens a socket.
  - `pytest.ini`: `pythonpath = . backend`, so tests import `vanderbilt_lectionary` by its bare name (as `test_timezones.py` imports `timezones`).
- Produces (all in `backend/vanderbilt_lectionary.py`):
  - `easter_date(year: int) -> date`: Easter Sunday (Anonymous Gregorian algorithm; the body of `_easter_date :54-70`).
  - `advent_sunday(year: int) -> date`: the Sunday from Nov 27 to Dec 3.
  - `liturgical_year_for(d: date) -> str`: `f"{y}-{(y + 1) % 100:02d}"`, `y = d.year if d >= advent_sunday(d.year) else d.year - 1`. Later users: Task 7 (`_VANDERBILT` cache key and the fetched file).
  - `ORDINALS: tuple[str, ...]`: 28 words, `"First"` … `"Twenty-Eighth"` (hyphenated, each part capitalized: `"Twenty-Third"`).
  - `ordinal_word(n: int) -> str`: `ORDINALS[n - 1]`; raises `ValueError` outside 1–28.
  - `_ordinary_time_name(d: date) -> str | None`: see T6a-3. Later user: Task 6b (`vanderbilt_sets_on`, the All Saints Proper rename).
  - `sunday_name(d: date) -> str | None`: None for any non-Sunday and for a Sunday Dec 25 or Jan 6. Exact strings: `"First Sunday after Christmas Day"`, `"Second Sunday after Christmas Day"`, `"{Ordinal} Sunday of Advent"` (First–Fourth), `"Baptism of the Lord"`, `"{Ordinal} Sunday after the Epiphany"`, `"Transfiguration Sunday"`, `"{Ordinal} Sunday in Lent"` (First–Fifth), `"Palm Sunday"`, `"Easter Sunday"`, `"{Ordinal} Sunday of Easter"` (Second–Seventh), `"Day of Pentecost"`, `"Trinity Sunday"`, `"{Ordinal} Sunday after Pentecost"`, `"All Saints Day"`, `"Reign of Christ"`. Later users: Task 6b (the Proper rename), `lectio_set_name`.
  - `weekday_feast_name(d: date) -> str | None`: `"Ash Wednesday"` (Easter −46), `"Maundy Thursday"` (−3), `"Good Friday"` (−2), `"Holy Saturday"` (−1), `"Ascension of the Lord"` (+39), `"Christmas Eve"` (Dec 24), `"Nativity of the Lord"` (Dec 25), `"New Year's Day"` (Jan 1, ASCII apostrophe), `"Epiphany of the Lord"` (Jan 6), `"All Saints Day"` (Nov 1); otherwise None.
  - `@dataclass(frozen=True) class LectioGroup(first: str, psalm: str, second: str, gospel: str, scriptures: tuple[str, ...])`. Later users: Task 6b (`parse_lectio_payload`, `fits_draft_limits`, `merge`), Task 7 (`load_lectio`).
  - `@dataclass(frozen=True) class LectioDay(groups: tuple[LectioGroup, ...], season: str, year: str, day_name: str | None)`. See T6a-6.
  - `lectio_set_name(day: LectioDay, d: date) -> str`: 1. `day.day_name` stripped, when non-empty; 2. `sunday_name(d) or weekday_feast_name(d)`; 3. `f"{season} — Year {year}"` (em dash U+2014) when both, stripped, are non-empty; 4. the English weekday name (`"Sunday"` … `"Saturday"`, never `strftime`, so no locale dependence). No de-duplication here: Task 6b's `merge` adds " (2)", " (3)".
  - `backend/tests/test_lectionary_domain.py`, with this import header, which Task 6b extends (it adds names to the `from vanderbilt_lectionary import (...)` list and its own imports below `import pytest`):

    ```python
    from datetime import date, timedelta

    import pytest

    from vanderbilt_lectionary import (
        ORDINALS,
        LectioDay,
        LectioGroup,
        _ordinary_time_name,
        advent_sunday,
        easter_date,
        lectio_set_name,
        liturgical_year_for,
        ordinal_word,
        sunday_name,
        weekday_feast_name,
    )
    ```

    and a module-level helper `_sundays(start: date, end: date)` (yields every Sunday from `start` to `end` inclusive) and constants `FIRST_YEAR, LAST_YEAR = 1900, 2199`, which Task 6b may reuse.

Counts after this task: backend **866 passed, 9 skipped** (856 + 10, all in `test_lectionary_domain.py`); frontend **221 passed in 34 files** (unchanged).

- [ ] **Step 1 (agent): Write the failing tests**

Create `backend/tests/test_lectionary_domain.py`:

```python
"""The pure lectionary domain (S Lectionary domain; decision A; AC1, AC4).

Task 6a: the calendar (Easter, Advent, the year file) and the occasion names.
Task 6b appends the Vanderbilt and Lectio parsing and the merge tests.
Everything here is date arithmetic: no fixtures, no network, no clock.
"""
from datetime import date, timedelta

import pytest

from vanderbilt_lectionary import (
    ORDINALS,
    LectioDay,
    LectioGroup,
    _ordinary_time_name,
    advent_sunday,
    easter_date,
    lectio_set_name,
    liturgical_year_for,
    ordinal_word,
    sunday_name,
    weekday_feast_name,
)

FIRST_YEAR, LAST_YEAR = 1900, 2199  # the API's date range (S Limits)


def _sundays(start: date, end: date):
    d = start + timedelta(days=(6 - start.weekday()) % 7)
    while d <= end:
        yield d
        d += timedelta(days=7)


# --- Dates ---


def test_easter_date_known_years():
    known = {
        1900: date(1900, 4, 15),
        1943: date(1943, 4, 25),
        2008: date(2008, 3, 23),
        2024: date(2024, 3, 31),
        2025: date(2025, 4, 20),
        2026: date(2026, 4, 5),
        2027: date(2027, 3, 28),
        2028: date(2028, 4, 16),
        2038: date(2038, 4, 25),
    }
    for year, expected in known.items():
        assert easter_date(year) == expected, year
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        e = easter_date(year)
        assert e.weekday() == 6, year
        assert date(year, 3, 22) <= e <= date(year, 4, 25), year


def test_advent_sunday_2025_to_2028():
    assert advent_sunday(2025) == date(2025, 11, 30)
    assert advent_sunday(2026) == date(2026, 11, 29)
    assert advent_sunday(2027) == date(2027, 11, 28)
    assert advent_sunday(2028) == date(2028, 12, 3)
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        a = advent_sunday(year)
        assert a.weekday() == 6, year
        assert date(year, 11, 27) <= a <= date(year, 12, 3), year


def test_liturgical_year_for_boundaries():
    cases = {
        date(2027, 11, 27): "2026-27",
        date(2027, 11, 28): "2027-28",  # AC4: Advent 1 2027 starts the new file
        date(2026, 11, 28): "2025-26",  # AC4: the day before Advent 1 2026 (the C2 bug)
        date(2026, 11, 29): "2026-27",
        date(2025, 12, 24): "2025-26",
        date(2099, 12, 25): "2099-00",  # the two-digit suffix wraps
        date(1900, 1, 1): "1899-00",
    }
    for d, expected in cases.items():
        assert liturgical_year_for(d) == expected, d


# --- Names ---


def test_sunday_name_table():
    table = {
        # S "Ordinary-time occasion names" fixture (all 11 rows)
        date(2026, 5, 24): "Day of Pentecost",
        date(2026, 5, 31): "Trinity Sunday",
        date(2026, 6, 7): "Second Sunday after Pentecost",
        date(2026, 10, 4): "Nineteenth Sunday after Pentecost",
        date(2026, 11, 1): "All Saints Day",
        date(2026, 11, 22): "Reign of Christ",
        date(2027, 11, 21): "Reign of Christ",
        date(2025, 11, 23): "Reign of Christ",
        date(2026, 1, 11): "Baptism of the Lord",
        date(2026, 1, 18): "Second Sunday after the Epiphany",
        date(2026, 2, 15): "Transfiguration Sunday",
        # the kept seasonal wording
        date(2025, 11, 30): "First Sunday of Advent",
        date(2025, 12, 21): "Fourth Sunday of Advent",
        date(2026, 2, 22): "First Sunday in Lent",
        date(2026, 3, 22): "Fifth Sunday in Lent",
        date(2026, 3, 29): "Palm Sunday",
        date(2026, 4, 5): "Easter Sunday",
        date(2026, 4, 12): "Second Sunday of Easter",
        date(2026, 5, 17): "Seventh Sunday of Easter",
        # the Christmas season (owner answer Q3)
        date(2025, 12, 28): "First Sunday after Christmas Day",
        date(2023, 1, 1): "First Sunday after Christmas Day",
        date(2026, 1, 4): "Second Sunday after Christmas Day",
        date(2022, 12, 25): None,  # a Sunday Christmas Day: the feast name comes from weekday_feast_name
        date(2019, 1, 6): None,  # a Sunday Epiphany: likewise
        date(2019, 1, 13): "Baptism of the Lord",  # Jan 6 was the Sunday, so the Baptism is a week later
    }
    for d, expected in table.items():
        assert sunday_name(d) == expected, d


def test_sunday_name_none_for_weekdays():
    assert sunday_name(date(2026, 5, 14)) is None  # Ascension Thursday, once "Sixth Sunday of Easter"
    assert sunday_name(date(2026, 2, 18)) is None  # Ash Wednesday
    assert sunday_name(date(2025, 12, 25)) is None  # Christmas Day on a Thursday
    d = date(2025, 11, 30)
    while d <= date(2028, 12, 2):
        if d.weekday() != 6:
            assert sunday_name(d) is None, d
        d += timedelta(days=1)


def test_named_days_win_2025_to_2028():
    """AC4: each named day beats the computed ordinal in every fixture year."""
    all_saints_sundays = 0
    for year in range(2025, 2029):
        easter = easter_date(year)
        named = {
            easter + timedelta(days=56): ("Trinity Sunday", "First Sunday after Pentecost"),
            advent_sunday(year) - timedelta(days=7): ("Reign of Christ", " Sunday after Pentecost"),
            easter - timedelta(days=49): ("Transfiguration Sunday", " Sunday after the Epiphany"),
        }
        jan6 = date(year, 1, 6)
        baptism = jan6 + timedelta(days=(6 - jan6.weekday()) % 7 or 7)
        named[baptism] = ("Baptism of the Lord", "First Sunday after the Epiphany")
        nov1 = date(year, 11, 1)
        if nov1.weekday() == 6:
            all_saints_sundays += 1
            named[nov1] = ("All Saints Day", " Sunday after Pentecost")
        for d, (name, computed_suffix) in named.items():
            assert d.weekday() == 6, d
            assert sunday_name(d) == name, d
            computed = _ordinary_time_name(d)
            assert computed is not None and computed.endswith(computed_suffix), (d, computed)
    assert all_saints_sundays == 1  # 2026-11-01
    assert _ordinary_time_name(date(2026, 11, 1)) == "Twenty-Third Sunday after Pentecost"  # clarification 30
    assert _ordinary_time_name(date(2026, 11, 22)) == "Twenty-Sixth Sunday after Pentecost"
    assert _ordinary_time_name(date(2027, 11, 21)) == "Twenty-Seventh Sunday after Pentecost"
    assert _ordinary_time_name(date(2025, 11, 23)) == "Twenty-Fourth Sunday after Pentecost"
    assert _ordinary_time_name(date(2026, 5, 24)) is None  # the Day of Pentecost is not ordinary time
    assert _ordinary_time_name(date(2026, 12, 6)) is None  # Advent
    assert _ordinary_time_name(date(2026, 10, 6)) is None  # a Tuesday


def test_every_ordinary_sunday_named():
    """Every Sunday from 1900 to 2199 has a name; none says "Proper" (decision A).

    Only a Sunday Dec 25 or Jan 6 has no Sunday name, and those take the feast name
    (owner answer Q3). Within one liturgical year no Sunday name repeats.
    """
    for year in range(FIRST_YEAR, LAST_YEAR):
        start, end = advent_sunday(year), advent_sunday(year + 1) - timedelta(days=1)
        seen = set()
        for d in _sundays(start, end):
            name = sunday_name(d)
            if (d.month, d.day) in {(12, 25), (1, 6)}:
                assert name is None, d
                assert weekday_feast_name(d) in {"Nativity of the Lord", "Epiphany of the Lord"}, d
                continue
            assert name, d
            assert "Proper" not in name, (d, name)
            assert name not in seen, (d, name)
            seen.add(name)


def test_ordinal_words_reach_twenty_eighth():
    assert len(ORDINALS) == 28
    assert ORDINALS[0] == "First"
    assert ORDINALS[18] == "Nineteenth"
    assert ORDINALS[20] == "Twenty-First"
    assert ORDINALS[22] == "Twenty-Third"
    assert ORDINALS[27] == "Twenty-Eighth"
    assert ordinal_word(1) == "First"
    assert ordinal_word(28) == "Twenty-Eighth"
    for bad in (0, 29, -1):
        with pytest.raises(ValueError):
            ordinal_word(bad)
    # clarification 9: over 1900-2199 the largest n after Pentecost is 28, on Reign of Christ
    largest = max(
        (advent_sunday(y) - timedelta(days=7) - (easter_date(y) + timedelta(days=49))).days // 7
        for y in range(FIRST_YEAR, LAST_YEAR + 1)
    )
    assert largest == 28
    assert _ordinary_time_name(date(2008, 11, 23)) == "Twenty-Eighth Sunday after Pentecost"
    assert sunday_name(date(2008, 11, 23)) == "Reign of Christ"


def test_weekday_feast_name():
    feasts = {
        date(2026, 2, 18): "Ash Wednesday",
        date(2026, 4, 2): "Maundy Thursday",
        date(2026, 4, 3): "Good Friday",
        date(2026, 4, 4): "Holy Saturday",
        date(2026, 5, 14): "Ascension of the Lord",
        date(2025, 12, 24): "Christmas Eve",
        date(2025, 12, 25): "Nativity of the Lord",
        date(2026, 1, 1): "New Year's Day",
        date(2026, 1, 6): "Epiphany of the Lord",
        date(2025, 11, 1): "All Saints Day",
        date(2026, 11, 1): "All Saints Day",  # a Sunday: the fixed feasts are date-only
        date(2022, 12, 25): "Nativity of the Lord",  # a Sunday (owner answer Q3)
        date(2019, 1, 6): "Epiphany of the Lord",  # a Sunday (owner answer Q3)
    }
    for d, expected in feasts.items():
        assert weekday_feast_name(d) == expected, d
    for d in (date(2026, 9, 29), date(2026, 11, 26), date(2026, 4, 5), date(2026, 9, 14)):
        assert weekday_feast_name(d) is None, d


def test_lectio_set_name_precedence():
    group = LectioGroup(
        first="Acts 10:34-43",
        psalm="Psalm 118:1-2, 14-24",
        second="Colossians 3:1-4",
        gospel="John 20:1-18",
        scriptures=("Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"),
    )

    def day(season="Ordinary Time", year="A", day_name=None):
        return LectioDay(groups=(group,), season=season, year=year, day_name=day_name)

    # 1. dayName wins, even over a computed Sunday name; a blank one is ignored
    assert lectio_set_name(day(season="Easter", day_name="Resurrection of the Lord"), date(2026, 4, 5)) == (
        "Resurrection of the Lord"
    )
    assert lectio_set_name(day(season="Easter", day_name="  "), date(2026, 4, 5)) == "Easter Sunday"
    # 2. a Sunday takes sunday_name, never "{season} — Year {year}"
    assert lectio_set_name(day(), date(2026, 10, 4)) == "Nineteenth Sunday after Pentecost"
    # 2. a Sunday Dec 25 or Jan 6 falls back to the feast name (owner answer Q3)
    assert lectio_set_name(day(season="Christmas"), date(2022, 12, 25)) == "Nativity of the Lord"
    assert lectio_set_name(day(season="Christmas"), date(2019, 1, 6)) == "Epiphany of the Lord"
    # 2. the Sunday name wins over a fixed feast on the same Sunday
    assert lectio_set_name(day(season="Christmas"), date(2023, 1, 1)) == "First Sunday after Christmas Day"
    # 3. another day takes weekday_feast_name, never a Sunday name
    assert lectio_set_name(day(season="Easter"), date(2026, 5, 14)) == "Ascension of the Lord"
    # 4. otherwise "{season} — Year {year}", with an em dash
    assert lectio_set_name(day(), date(2026, 9, 29)) == "Ordinary Time — Year A"
    # 5. the weekday's name when season or year is missing
    assert lectio_set_name(day(season="", year=""), date(2026, 9, 29)) == "Tuesday"
    assert lectio_set_name(day(season="Ordinary Time", year=""), date(2026, 9, 29)) == "Tuesday"
    # the types are frozen
    with pytest.raises(AttributeError):
        group.first = "Genesis 1:1"
```

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | grep -m1 'ImportError:'
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | tail -1
```

**Expected:** `E   ImportError: cannot import name 'ORDINALS' from 'vanderbilt_lectionary' (<repo>/backend/vanderbilt_lectionary.py)`, then `1 error in <t>s` (the module has none of the new names yet).

- [ ] **Step 3 (agent): Add the import**

In `backend/vanderbilt_lectionary.py`, replace lines 8-10:

```python
import csv
import logging
from datetime import date, datetime, timedelta
```

with:

```python
import csv
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
```

Leave line 11 (`from typing import Optional, List, Dict, Any`) and everything else above the new section unchanged.

- [ ] **Step 4 (agent): Append the calendar and names section**

Append this block to the end of `backend/vanderbilt_lectionary.py`, after the current last line (`    return result`, the end of `get_readings_for_date_string`). The block starts with two blank lines:

```python


# --- Slice 2 domain: the calendar and occasion names (S Lectionary domain; decision A) ---
#
# Pure date arithmetic: no I/O and no clock. Names come from the date alone, never from
# Lectio's season string. The code above is the Streamlit-era path; Task 7 deletes it
# (including the private `_easter_date`, which `easter_date` below replaces).

ORDINALS: tuple[str, ...] = (
    "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh",
    "Eighth", "Ninth", "Tenth", "Eleventh", "Twelfth", "Thirteenth", "Fourteenth",
    "Fifteenth", "Sixteenth", "Seventeenth", "Eighteenth", "Nineteenth", "Twentieth",
    "Twenty-First", "Twenty-Second", "Twenty-Third", "Twenty-Fourth",
    "Twenty-Fifth", "Twenty-Sixth", "Twenty-Seventh", "Twenty-Eighth",
)

_SUNDAY = 6  # date.weekday()
_WEEKDAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_FIXED_FEASTS = {
    (12, 24): "Christmas Eve",
    (12, 25): "Nativity of the Lord",
    (1, 1): "New Year's Day",
    (1, 6): "Epiphany of the Lord",
    (11, 1): "All Saints Day",
}
_EASTER_FEASTS = {  # days from Easter Sunday
    -46: "Ash Wednesday",
    -3: "Maundy Thursday",
    -2: "Good Friday",
    -1: "Holy Saturday",
    39: "Ascension of the Lord",
}


def easter_date(year: int) -> date:
    """Easter Sunday for `year` (Anonymous Gregorian algorithm)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def advent_sunday(year: int) -> date:
    """The First Sunday of Advent in `year`: the Sunday from Nov 27 to Dec 3."""
    nov27 = date(year, 11, 27)
    return nov27 + timedelta(days=(_SUNDAY - nov27.weekday()) % 7)


def liturgical_year_for(d: date) -> str:
    """The Vanderbilt year file that holds `d`, e.g. "2025-26" (fixes inv. C2).

    A year file runs from Advent 1 to the day before the next Advent 1.
    """
    y = d.year if d >= advent_sunday(d.year) else d.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def ordinal_word(n: int) -> str:
    """1 -> "First" ... 28 -> "Twenty-Eighth"; ValueError outside 1-28.

    28 is the largest count after Pentecost in any year (clarification 9).
    """
    if not 1 <= n <= len(ORDINALS):
        raise ValueError(f"no ordinal word for {n}")
    return ORDINALS[n - 1]


def _baptism_of_the_lord(year: int) -> date:
    """The first Sunday after Jan 6 (Jan 7-13). A Sunday Jan 6 is the Epiphany itself."""
    jan6 = date(year, 1, 6)
    return jan6 + timedelta(days=(_SUNDAY - jan6.weekday()) % 7 or 7)


def _ordinary_time_name(d: date) -> str | None:
    """The computed ordinary-time name of a Sunday, ignoring the named days.

    "{Ordinal} Sunday after the Epiphany" from the Baptism of the Lord ("First") to
    Transfiguration Sunday, and "{Ordinal} Sunday after Pentecost" from Trinity Sunday
    ("First") to Reign of Christ. None for any other date. `sunday_name` checks the
    named days first; the Vanderbilt Proper rename (Task 6b) uses this directly when
    `sunday_name(d)` is "All Saints Day" (clarification 30).
    """
    if d.weekday() != _SUNDAY:
        return None
    easter = easter_date(d.year)
    baptism = _baptism_of_the_lord(d.year)
    transfiguration = easter - timedelta(days=49)
    if baptism <= d <= transfiguration:
        return f"{ordinal_word((d - baptism).days // 7 + 1)} Sunday after the Epiphany"
    pentecost = easter + timedelta(days=49)
    if pentecost < d < advent_sunday(d.year):
        return f"{ordinal_word((d - pentecost).days // 7)} Sunday after Pentecost"
    return None


def sunday_name(d: date) -> str | None:
    """The occasion name of a Sunday, from the date alone; None for any other day.

    Checked in this order: the Christmas season (owner answer Q3), Advent, Lent, Palm
    Sunday, Easter and its Sundays, the Day of Pentecost; then the named days, which
    always win over the computed ordinal (decision A); then `_ordinary_time_name`.
    A Sunday Dec 25 or Jan 6 returns None: `lectio_set_name` then takes
    "Nativity of the Lord" or "Epiphany of the Lord" from `weekday_feast_name`.
    """
    if d.weekday() != _SUNDAY:
        return None
    y = d.year
    if (d.month == 12 and d.day >= 26) or (d.month == 1 and d.day == 1):
        return "First Sunday after Christmas Day"
    if d.month == 1 and 2 <= d.day <= 5:
        return "Second Sunday after Christmas Day"
    advent1 = advent_sunday(y)
    if advent1 <= d <= date(y, 12, 24):
        return f"{ORDINALS[(d - advent1).days // 7]} Sunday of Advent"
    easter = easter_date(y)
    palm = easter - timedelta(days=7)
    lent1 = easter - timedelta(days=42)
    if lent1 <= d < palm:
        return f"{ORDINALS[(d - lent1).days // 7]} Sunday in Lent"
    if d == palm:
        return "Palm Sunday"
    if d == easter:
        return "Easter Sunday"
    pentecost = easter + timedelta(days=49)
    if easter < d < pentecost:
        return f"{ORDINALS[(d - easter).days // 7]} Sunday of Easter"
    if d == pentecost:
        return "Day of Pentecost"
    if d == _baptism_of_the_lord(y):
        return "Baptism of the Lord"
    if d == easter - timedelta(days=49):
        return "Transfiguration Sunday"
    if d == pentecost + timedelta(days=7):
        return "Trinity Sunday"
    if d.month == 11 and d.day == 1:
        return "All Saints Day"
    if d == advent1 - timedelta(days=7):
        return "Reign of Christ"
    return _ordinary_time_name(d)


def weekday_feast_name(d: date) -> str | None:
    """The feast on `d`, or None. Date-only: a fixed feast on a Sunday is still named."""
    fixed = _FIXED_FEASTS.get((d.month, d.day))
    if fixed is not None:
        return fixed
    return _EASTER_FEASTS.get((d - easter_date(d.year)).days)


@dataclass(frozen=True)
class LectioGroup:
    """One Lectio reading group; `scriptures` is the four lines minus blanks (Task 6b parses)."""

    first: str
    psalm: str
    second: str
    gospel: str
    scriptures: tuple[str, ...]


@dataclass(frozen=True)
class LectioDay:
    """One Lectio date: its groups, plus `season` and `year` ("" when missing) and `dayName`."""

    groups: tuple[LectioGroup, ...]
    season: str
    year: str
    day_name: str | None


def lectio_set_name(day: LectioDay, d: date) -> str:
    """The name of a Lectio-only set on `d` (S "Names for Lectio-only sets").

    1. Lectio's dayName, when present;
    2. `sunday_name(d)`, then `weekday_feast_name(d)`: so a weekday never gets a Sunday
       name, and a Sunday Dec 25 or Jan 6 gets its feast name (owner answer Q3);
    3. "{season} — Year {year}", when both are present;
    4. the weekday's name ("Sunday" for a Sunday).
    `merge` (Task 6b) adds " (2)", " (3)" when several sets share a name.
    """
    day_name = (day.day_name or "").strip()
    if day_name:
        return day_name
    computed = sunday_name(d) or weekday_feast_name(d)
    if computed:
        return computed
    season, year = day.season.strip(), day.year.strip()
    if season and year:
        return f"{season} — Year {year}"
    return _WEEKDAY_NAMES[d.weekday()]
```

- [ ] **Step 5 (agent): Run the tests, check the change is additive, run the whole suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | tail -1
git diff -U0 backend/vanderbilt_lectionary.py | grep '^-' | grep -vc '^---'
git diff --stat
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `10 passed in <t>s`;
- `0` (no line of the old code is removed or changed);
- `backend/vanderbilt_lectionary.py | 203 +++…` and `1 file changed, 203 insertions(+)`;
- `866 passed, 9 skipped in <t>s` (856 + 10). If the count differs, stop and find why before committing.

- [ ] **Step 6 (agent): Commit**

```bash
git status --short
git add backend/vanderbilt_lectionary.py backend/tests/test_lectionary_domain.py
git commit -m "Lectionary: calendar and occasion names from the date alone (S Lectionary domain; decision A; owner answer Q3)

easter_date, advent_sunday and liturgical_year_for (the year file now
turns over on Advent 1, inv. C2). sunday_name is date-only and None on
weekdays: named days (Trinity, All Saints on a Sunday, Reign of Christ,
Baptism, Transfiguration) win over the computed '{Ordinal} Sunday after
Pentecost' / 'after the Epiphany', ordinals run to Twenty-Eighth, and the
Christmas-season Sundays are named (owner answer Q3). weekday_feast_name,
the frozen LectioGroup and LectioDay types, and lectio_set_name. Additive:
the old path stays until Task 7 deletes it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** the first `git status --short` prints exactly:

```
 M backend/vanderbilt_lectionary.py
?? .claude/
?? backend/tests/test_lectionary_domain.py
```

then `<sha> Lectionary: calendar and occasion names from the date alone (S Lectionary domain; decision A; owner answer Q3)`, then only `?? .claude/`.

- [ ] **Step 7 (agent): Review checkpoint**

Stop for the task review before Task 6b. The reviewer checks: the diff of `vanderbilt_lectionary.py` has no `-` lines; the 11 S table rows and the six Q3 rows in `test_sunday_name_table` match the strings in this task's Interfaces exactly; `lectio_set_name` step 2 is `sunday_name(d) or weekday_feast_name(d)`; and nothing in the new section does I/O, reads a clock or logs.
### Task 6b: Lectionary parsing, the draft-limit guard and the merge (S Lectionary domain "Vanderbilt parsing", "Lectio parsing", "Merge", "Ordinary-time occasion names" rename; AC1 domain half, AC4 rename half; clarifications 10, 11, 12, 15, 30, 34)

This task appends the second half of the pure lectionary domain to `backend/vanderbilt_lectionary.py`: the Vanderbilt CSV parser (`parse_vanderbilt_csv`, `VRow`, `LectionaryFormatError`), cell cleanup (`clean_cell`), the draft-limit guard (`fits_draft_limits`), the exact-date Vanderbilt sets with the Proper rename (`vanderbilt_sets_on`, `ReadingSet`), the Lectio parser (`parse_lectio_payload`) and `merge`. Everything is pure: no I/O, no clock. The only logging is the one WARNING `fits_draft_limits` writes when it drops a set. The change stays **additive**: the Streamlit-era path above Task 6a's section (`fetch_lectionary_year`, `get_readings_for_date`, `get_readings_for_date_string`, …) keeps working unchanged until Task 7 deletes it. The only existing line that changes is the `typing` import, which gains `Literal`. The frontend does not change.

The tests are fixture-driven where S says "recorded": the Easter Vigil cell, the merge table and the limits invariant read Task 1's `backend/tests/fixtures/vanderbilt/2025-26.csv` and `lectio/<date>.json` through `tests.upstream_fixtures.load`. Every other test builds its input inline, so a parsing rule is pinned even if a recording changes.

Facts from the code and the earlier tasks that shape this task:
- After Task 6a, `backend/vanderbilt_lectionary.py:8-13` is the import block (`import csv` … `import httpx`). Task 6a's section ends the file with `    return _WEEKDAY_NAMES[d.weekday()]` (the last line of `lectio_set_name`). The module already has `logger = logging.getLogger(__name__)` (`:14` today, `:15` after Task 6a) and `csv`, `date` and `datetime` imported.
- Task 6a's `LectioGroup(first, psalm, second, gospel, scriptures)` and `LectioDay(groups, season, year, day_name)` are frozen dataclasses. T6a-6: `season` and `year` are `""` when missing, never `"None"`.
- Task 6a's `sunday_name(d)` returns exactly `"All Saints Day"` for a Sunday Nov 1 and `"Reign of Christ"` for the Sunday before Advent 1. `_ordinary_time_name(d)` gives the computed "{Ordinal} Sunday after Pentecost" (2026-11-01 → "Twenty-Third Sunday after Pentecost"; 2026-10-04 → "Nineteenth Sunday after Pentecost"). `lectio_set_name(day, d)` does no de-duplication; this task's `merge` adds " (2)", " (3)".
- Task 5's `split_book(ref) -> tuple[Book, str] | None` finds the longest alias at the start, and `Book.testament` is `"ot" | "psalm" | "nt"`. The headings "Old Testament Readings and Psalms", "New Testament Reading and Psalm" and "Gospel" start with no book, so `split_book` returns None for them. `scripture_key("Luke 2:1-14 (15-20)") == scripture_key("Luke 2:1-14, (15-20)")`. `split_alternatives` splits on " or " without regard to case.
- Task 1's `tests.upstream_fixtures.load(kind, name) -> Recorded(status, content_type, body)` takes a file stem (`"2025-26"`, `"404"`, `"html_200"`, `"2026-03-29"`). `FIXTURE_DATES` is a `tuple[date, ...]` of the 13 merge-table dates. The Vanderbilt year file is trimmed to those dates, keeping its preamble, header and file order (the Nativity rows come after the January rows). The trimmed text is re-encoded in the response's own encoding, so the test decodes it with the charset its recorded Content-Type names (UTF-8 when none, as httpx does).
- Today's `fetch_lectionary_year` (`:168-190`) finds the header line, drops blank lines and runs `csv.DictReader` over the remaining lines with the fixed field names at `:179-182`. If there is no header it silently parses from line 0. The new parser keeps the line handling (a quoted Prayer cell that spans lines still parses; the test pins it) and raises `LectionaryFormatError` instead.

**Decisions recorded in this task (code wins over the outline; owner decision 1):**
- **T6b-1. `VRow` cells are the raw cell text, trimmed and unquoted** (`.strip().strip('"').strip()`, parity with `_row_to_reading :196-199`); `clean_cell` does the rest. A Vanderbilt `ReadingSet`'s `first`, `psalm`, `second` and `gospel` hold the cleaned cell text, unsplit, and `scriptures` holds the split lines (clarification 12). Only `gospel` is read after this, by `merge`.
- **T6b-2. A leading star is dropped with or without a space after it** (`^\*\s*`). S says "a leading `* `"; with Vanderbilt's `"* Acts …"` cells both rules give the same line, and a `"*Acts"` cell would otherwise print its star.
- **T6b-3. The Proper rename** applies only when the whole trimmed name matches `Proper \d+ \(\d+\)` and the date is a Sunday. The name is then `sunday_name(d)`, except that `"All Saints Day"` becomes `_ordinary_time_name(d)` (clarification 30). If either returns None, the raw text is kept (clarification 11, defensive; no Sunday in 1900–2199 hits it).
- **T6b-4. `parse_lectio_payload`** raises `TypeError` for a non-object payload, `data`, `readings` list or reading, and for a non-string citation, so Task 7's `except (KeyError, TypeError, ValueError)` covers every bad shape (clarification 15). `season`, `year` and `dayName` are coerced with `str(x or "").strip()` (T6a-6; outline A12). A reading whose `type` is not one of `first`, `psalm`, `second`, `gospel` is ignored: it neither joins a group nor starts one (the old code read only those four types, `:306-309`). A payload whose readings leave no group (all alternatives, or `readings: []`) is None.
- **T6b-5. `fits_draft_limits`' WARNING** is `reading_set_dropped name=<repr, first 80 characters> name_chars=<n> lines=<n> line_chars=[…]`. A Lectio group has no name before `merge`, so it logs `name='(lectio group)' name_chars=0`. The function takes no date, so the line has none; Task 7's `lectionary_lookup` line carries the date. It never logs a reading's text.
- **T6b-6. `merge` treats a `LectioDay` with no groups like None.** Task 7 passes None when `fits_draft_limits` drops every Lectio group; the guard makes the other form safe too.
- **T6b-7. Lectio-only names are numbered by position** (all groups share `lectio_set_name(day, d)`), and then each named set is checked with `fits_draft_limits` (clarification 34). A set dropped for its name does not renumber the others. `default_index` is the last set kept, or None when none is kept.
- **T6b-8. `_parse_calendar_date`** is new and returns a `date`. The old `_parse_csv_date` (returns a `datetime`) stays for the old path, and Task 7 deletes it as superseded.
- **T6b-9. How the fixture-driven asserts match names.** A name this code computes ("Nineteenth Sunday after Pentecost", "Twenty-Third Sunday after Pentecost") is compared exactly. A name Vanderbilt writes is matched with a case-insensitive pattern ("palms", "proper iii\b", …), because Task 1 records whatever Vanderbilt sends (its clarification 41 note). S's Lectio gospels, the Vigil lines and the Thanksgiving lines are compared exactly. **If a fixture-driven test fails on a recorded fixture while every inline test passes, do not edit the fixture and do not loosen the assert. Stop and report the failing assert together with Task 1's `DIFF` lines for that fixture.** The owner decides, as in clarification 41.

**Files:**
- Modify: `backend/vanderbilt_lectionary.py`: the import block (`:8-13` after Task 6a); append a new section after the last line (`    return _WEEKDAY_NAMES[d.weekday()]`, the end of Task 6a's `lectio_set_name`).
- Modify: `backend/tests/test_lectionary_domain.py`: the header (the docstring's last two lines and the import block); append 18 tests after Task 6a's last test (`test_lectio_set_name_precedence`).
- Test: `backend/tests/test_lectionary_domain.py` (10 → 28 tests).

**Interfaces:**
- Consumes:
  - Task 1: `tests.upstream_fixtures.load(kind: str, name: str | date) -> Recorded` (`status: int`, `content_type: str`, `body: bytes`) and `FIXTURE_DATES: tuple[date, ...]`. Fixtures used: `vanderbilt/2025-26`, `vanderbilt/404`, `vanderbilt/html_200` and `lectio/<each FIXTURE_DATES date>`.
  - Task 5 (`backend/scripture_refs.py`): `split_book(ref: str) -> tuple[Book, str] | None`, `Book.testament`, `split_alternatives(ref: str) -> list[str]`, `scripture_key(ref: str) -> str`.
  - Task 6a (`backend/vanderbilt_lectionary.py`): `sunday_name(d) -> str | None`, `_ordinary_time_name(d) -> str | None`, `lectio_set_name(day: LectioDay, d: date) -> str`, `LectioGroup`, `LectioDay`.
  - The existing module-level `logger`, `csv`, `date` and `datetime` in `backend/vanderbilt_lectionary.py`.
- Produces (all in `backend/vanderbilt_lectionary.py`):
  - `MAX_SET_LINES = 20`, `MAX_LINE_CHARS = 200`, `MAX_NAME_CHARS = 300`.
  - `class LectionaryFormatError(ValueError)`. Later user: Task 7 (`load_vanderbilt_year` turns it into `SourceFailed(timeout=False)`).
  - `@dataclass(frozen=True) class VRow(liturgical_date: str, calendar_date: date, first: str, psalm: str, second: str, gospel: str)`.
  - `@dataclass(frozen=True) class ReadingSet(name: str, first: str, psalm: str, second: str, gospel: str, scriptures: tuple[str, ...], source: Literal["lectio", "vanderbilt", "merged"])`. Later users: Task 7 (`LectionaryResult.reading_sets`) and Task 8 (`ReadingSetOut` from `name`, `list(scriptures)`, `source`).
  - `parse_vanderbilt_csv(text: str) -> list[VRow]`: raises `LectionaryFormatError` when no line holds both "Calendar Date" and "Liturgical Date" without a `<` (a markup line is never the header). Later user: Task 7 (`load_vanderbilt_year`).
  - `clean_cell(cell: str) -> list[str]`.
  - `fits_draft_limits(item: ReadingSet | LectioGroup) -> bool`. Later user: Task 7 (filters both sources before `merge`).
  - `vanderbilt_sets_on(rows: list[VRow], d: date) -> list[ReadingSet]`: the rows dated exactly `d`, in file order, `source="vanderbilt"`, Proper rename applied. Later user: Task 7.
  - `parse_lectio_payload(payload: object) -> LectioDay | None`. Later user: Task 7 (`load_lectio`).
  - `merge(lectio: LectioDay | None, v_sets: list[ReadingSet], d: date) -> tuple[list[ReadingSet], int | None]`. Later user: Task 7 (`readings_for_date`).
  - Private helpers, not for other modules: `_parse_calendar_date`, `_field`, `_clean_text`, `_vanderbilt_name`, `_lectio_group`, `_set_from_group`, `_lectio_only_sets`, and the patterns `_PROPER_ROW`, `_COMPOUND_PSALM`, `_LEADING_STAR`.
  - The WARNING line `reading_set_dropped …` (T6b-5).

Counts after this task: backend **884 passed, 9 skipped** (866 + 18, all in `test_lectionary_domain.py`); frontend **221 passed in 34 files** (unchanged; not rerun here).

- [ ] **Step 1 (agent): Preflight**

```bash
git log --oneline -1
grep -c '^def split_book\|^def scripture_key\|^def split_alternatives' backend/scripture_refs.py
grep -c '^def sunday_name\|^def _ordinary_time_name\|^def lectio_set_name\|^class LectioGroup\|^class LectioDay' backend/vanderbilt_lectionary.py
sed -n 8,13p backend/vanderbilt_lectionary.py
tail -1 backend/vanderbilt_lectionary.py
ls backend/tests/fixtures/vanderbilt/ | tr '\n' ' '; echo
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `<sha> Lectionary: calendar and occasion names from the date alone (S Lectionary domain; decision A; owner answer Q3)`;
- `3`, then `5`;
- exactly these six lines:

```
import csv
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
```

- `    return _WEEKDAY_NAMES[d.weekday()]`;
- `2025-26.csv 2025-26.meta.json 2026-27.csv 2026-27.meta.json 2027-28.csv 2027-28.meta.json 404.html 404.meta.json html_200.html html_200.meta.json`;
- `866 passed, 9 skipped in <t>s`.

If any line differs, stop and ask: this task's replacement blocks are written against exactly that state.

- [ ] **Step 2 (agent): Write the failing tests**

In `backend/tests/test_lectionary_domain.py`, replace the header (the module docstring and the import block, from the first line down to the `)` that closes the `from vanderbilt_lectionary import (` list), which is exactly:

```python
"""The pure lectionary domain (S Lectionary domain; decision A; AC1, AC4).

Task 6a: the calendar (Easter, Advent, the year file) and the occasion names.
Task 6b appends the Vanderbilt and Lectio parsing and the merge tests.
Everything here is date arithmetic: no fixtures, no network, no clock.
"""
from datetime import date, timedelta

import pytest

from vanderbilt_lectionary import (
    ORDINALS,
    LectioDay,
    LectioGroup,
    _ordinary_time_name,
    advent_sunday,
    easter_date,
    lectio_set_name,
    liturgical_year_for,
    ordinal_word,
    sunday_name,
    weekday_feast_name,
)
```

with:

```python
"""The pure lectionary domain (S Lectionary domain; decision A; AC1, AC4).

Task 6a: the calendar (Easter, Advent, the year file) and the occasion names.
Task 6b: the Vanderbilt and Lectio parsing, the draft-limit guard and the merge.
Task 6a's tests are date arithmetic; Task 6b's also read the recorded fixtures
(`tests.upstream_fixtures`). No network, no clock.
"""
import dataclasses
import functools
import json
import logging
import re
from datetime import date, timedelta

import pytest

from scripture_refs import scripture_key
from tests import upstream_fixtures
from vanderbilt_lectionary import (
    ORDINALS,
    LectionaryFormatError,
    LectioDay,
    LectioGroup,
    ReadingSet,
    VRow,
    _ordinary_time_name,
    advent_sunday,
    clean_cell,
    easter_date,
    fits_draft_limits,
    lectio_set_name,
    liturgical_year_for,
    merge,
    ordinal_word,
    parse_lectio_payload,
    parse_vanderbilt_csv,
    sunday_name,
    vanderbilt_sets_on,
    weekday_feast_name,
)
```

Leave `FIRST_YEAR, LAST_YEAR = 1900, 2199`, `_sundays` and Task 6a's ten tests unchanged. Then append this block to the end of the file, after the last line of `test_lectio_set_name_precedence` (`        group.first = "Genesis 1:1"`). The block starts with two blank lines:

```python


# ---------------------------------------------------------------------------
# Task 6b: Vanderbilt and Lectio parsing, the draft-limit guard, the merge.
# ---------------------------------------------------------------------------

_PROPER_ROW = re.compile(r"Proper \d+ \(\d+\)")


def _rs(name="Set", lines=("Isaiah 5:1-7",), gospel="", source="vanderbilt"):
    return ReadingSet(
        name=name, first="", psalm="", second="", gospel=gospel, scriptures=tuple(lines), source=source
    )


def _group(first="", psalm="", second="", gospel=""):
    return LectioGroup(
        first=first,
        psalm=psalm,
        second=second,
        gospel=gospel,
        scriptures=tuple(s for s in (first, psalm, second, gospel) if s),
    )


def _vrow(liturgical_date, on, first="", psalm="", second="", gospel=""):
    return VRow(
        liturgical_date=liturgical_date, calendar_date=on, first=first, psalm=psalm, second=second, gospel=gospel
    )


def _text(recorded):
    """The body decoded as its Content-Type says (UTF-8 when it names no charset, as httpx does)."""
    charset = "utf-8"
    for param in recorded.content_type.split(";")[1:]:
        key, _, value = param.strip().partition("=")
        if key.lower() == "charset" and value.strip('"'):
            charset = value.strip('"')
    return recorded.body.decode(charset)


@functools.cache
def _fixture_rows():
    recorded = upstream_fixtures.load("vanderbilt", "2025-26")
    assert recorded.status == 200
    return tuple(parse_vanderbilt_csv(_text(recorded)))


def _fixture_lectio(on):
    recorded = upstream_fixtures.load("lectio", on.isoformat())
    if recorded.status == 404:
        return None
    assert recorded.status == 200
    return parse_lectio_payload(json.loads(recorded.body))


def _merge_on(on):
    """What usecases.lectionary (Task 7) does after fetching: drop what fails the limits, then merge."""
    v_sets = [s for s in vanderbilt_sets_on(list(_fixture_rows()), on) if fits_draft_limits(s)]
    lectio = _fixture_lectio(on)
    if lectio is not None:
        groups = tuple(g for g in lectio.groups if fits_draft_limits(g))
        lectio = dataclasses.replace(lectio, groups=groups) if groups else None
    return merge(lectio, v_sets, on)


def _name_matches(expected, actual):
    if isinstance(expected, re.Pattern):
        return expected.search(actual) is not None
    return expected == actual


def _has(text):
    return re.compile(text, re.IGNORECASE)


# S "Merge" table. A str is a name this code computes (exact); a pattern is Vanderbilt's own row text,
# matched loosely so a recorded apostrophe or suffix does not matter. The last column is the Lectio
# gospel that the merged set carries (S upstream facts), or None when nothing merges.
_MERGE_TABLE = [
    (date(2026, 10, 4), [("Nineteenth Sunday after Pentecost", "merged")], 0, "Matthew 21:33-46"),
    (date(2026, 3, 29), [(_has("palms"), "vanderbilt"), (_has("passion"), "merged")], 1, "Matthew 26:14-27:66"),
    (
        date(2026, 4, 5),
        [(_has("vigil"), "vanderbilt"), (_has("resurrection"), "merged"), (_has("evening"), "vanderbilt")],
        1,
        "John 20:1-18",
    ),
    (date(2026, 5, 31), [(_has("visitation"), "vanderbilt"), (_has("trinity"), "merged")], 1, "Matthew 28:16-20"),
    (date(2026, 5, 14), [(_has("ascension"), "vanderbilt")], 0, None),
    (date(2026, 2, 18), [(_has("ash wednesday"), "merged")], 0, "Matthew 6:1-6, 16-21"),
    (date(2025, 12, 24), [(_has(r"nativity.*proper i\b"), "merged")], 0, "Luke 2:1-14 (15-20)"),
    (date(2025, 12, 25), [(_has(r"proper ii\b"), "vanderbilt"), (_has(r"proper iii\b"), "merged")], 1, "John 1:1-14"),
    (date(2026, 4, 3), [(_has("good friday"), "vanderbilt")], 0, None),
    (date(2026, 1, 1), [(_has("holy name"), "vanderbilt"), (_has("new year"), "vanderbilt")], 1, None),
    (date(2026, 11, 26), [(_has("thanksgiving"), "vanderbilt")], 0, None),
    (
        date(2026, 11, 1),
        [(_has("all saints"), "vanderbilt"), ("Twenty-Third Sunday after Pentecost", "merged")],
        1,
        "Matthew 23:1-12",
    ),
    (date(2026, 9, 29), [], None, None),
]
_MERGE_DATES = [row[0] for row in _MERGE_TABLE]

_CSV_WITH_PREAMBLE = (
    "Revised Common Lectionary, Year A\n"
    "Vanderbilt Divinity Library\n"
    "\n"
    "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
    '"Liturgy of the Palms","Mar 29, 2026","","Psalm 118:1-2, 19-29","","Matthew 21:1-11",'
    '"https://example.org/art/1","Almighty God,\n\nwe praise you."\n'
    '"Thanksgiving Day","November 26, 2026","Deuteronomy 8:7-18 Psalm 65","","2 Corinthians 9:6-15",'
    '"Luke 17:11-19","",""\n'
)


def test_parse_csv_finds_header_after_preamble():
    # The Palms row's Prayer cell spans lines, blank line included: the next row still parses.
    assert parse_vanderbilt_csv(_CSV_WITH_PREAMBLE) == [
        VRow("Liturgy of the Palms", date(2026, 3, 29), "", "Psalm 118:1-2, 19-29", "", "Matthew 21:1-11"),
        VRow(
            "Thanksgiving Day",
            date(2026, 11, 26),
            "Deuteronomy 8:7-18 Psalm 65",
            "",
            "2 Corinthians 9:6-15",
            "Luke 17:11-19",
        ),
    ]
    header_only = "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
    assert parse_vanderbilt_csv(header_only) == []
    # The recorded file keeps Vanderbilt's preamble; every merge-table date with a row is found.
    recorded_dates = {row.calendar_date for row in _fixture_rows()}
    assert set(_MERGE_DATES) - recorded_dates == {date(2026, 9, 29)}


def test_parse_csv_html_raises():
    assert issubclass(LectionaryFormatError, ValueError)
    table = "<table><tr><th>Liturgical Date</th><th>Calendar Date</th></tr></table>\n"
    for text in ("<!DOCTYPE html>\n<html><body>Page not found</body></html>\n", table, "", "\n\n"):
        with pytest.raises(LectionaryFormatError):
            parse_vanderbilt_csv(text)
    # The recorded 404 page (1999-00) and the HTML served as 200 (2045-46) are not CSV either.
    for name in ("404", "html_200"):
        body = upstream_fixtures.load("vanderbilt", name).body.decode("utf-8", errors="replace")
        with pytest.raises(LectionaryFormatError):
            parse_vanderbilt_csv(body)


def test_parse_csv_skips_unparseable_dates():
    text = (
        "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
        '"Season of Lent","","","","","","",""\n'
        '"Undated","TBD","Isaiah 1:1","","","","",""\n'
        '"No such day","Feb 30, 2026","Isaiah 1:1","","","","",""\n'
        '"Ash Wednesday","Feb 18, 2026","Joel 2:1-2, 12-17","Psalm 51:1-17","2 Corinthians 5:20b-6:10",'
        '"Matthew 6:1-6, 16-21","",""\n'
        '"Epiphany of the Lord","January 06, 2027","Isaiah 60:1-6","Psalm 72:1-7, 10-14","Ephesians 3:1-12",'
        '"Matthew 2:1-12","",""\n'
    )
    rows = parse_vanderbilt_csv(text)
    assert [(row.liturgical_date, row.calendar_date) for row in rows] == [
        ("Ash Wednesday", date(2026, 2, 18)),
        ("Epiphany of the Lord", date(2027, 1, 6)),
    ]


def test_clean_cell_compound_star_and_http():
    assert clean_cell("Deuteronomy 8:7-18 Psalm 65") == ["Deuteronomy 8:7-18", "Psalm 65"]
    assert clean_cell("Genesis 12:1-9 Psalm 33:1-12") == ["Genesis 12:1-9", "Psalm 33:1-12"]
    assert clean_cell('"Hosea 5:15-6:6 Psalm 50:7-15"') == ["Hosea 5:15-6:6", "Psalm 50:7-15"]
    assert clean_cell("* Acts 2:14a, 22-32") == ["Acts 2:14a, 22-32"]
    assert clean_cell('  "* 1 Peter 1:3-9"  ') == ["1 Peter 1:3-9"]
    assert clean_cell("Luke 17:11-19") == ["Luke 17:11-19"]
    assert clean_cell("Psalm 23") == ["Psalm 23"]
    assert clean_cell("https://lectionary.library.vanderbilt.edu/art.php?id=1") == []
    for blank in ("", '""', "   "):
        assert clean_cell(blank) == []
    # Nothing is split unless the text before "Psalm <n>" starts with a book.
    assert clean_cell("See the note Psalm 23") == ["See the note Psalm 23"]
    # S's Thanksgiving Day example: the cleaned cells, in column order.
    row = _vrow(
        "Thanksgiving Day",
        date(2026, 11, 26),
        first="Deuteronomy 8:7-18 Psalm 65",
        second="2 Corinthians 9:6-15",
        gospel="Luke 17:11-19",
    )
    (thanksgiving,) = vanderbilt_sets_on([row], date(2026, 11, 26))
    assert thanksgiving == ReadingSet(
        name="Thanksgiving Day",
        first="Deuteronomy 8:7-18 Psalm 65",
        psalm="",
        second="2 Corinthians 9:6-15",
        gospel="Luke 17:11-19",
        scriptures=("Deuteronomy 8:7-18", "Psalm 65", "2 Corinthians 9:6-15", "Luke 17:11-19"),
        source="vanderbilt",
    )


def test_clean_cell_alternative_psalm_kept_whole():
    # A two-track cell splits once, before the first "Psalm"; the alternative psalm stays whole.
    assert clean_cell("Genesis 29:15-28 Psalm 105:1-11, 45b or Psalm 128") == [
        "Genesis 29:15-28",
        "Psalm 105:1-11, 45b or Psalm 128",
    ]
    # A standalone alternative psalm is one line (its head is a Psalm), clarification 10.
    assert clean_cell("Psalm 105:1-11, 45b or Psalm 128") == ["Psalm 105:1-11, 45b or Psalm 128"]
    # A head ending in " or" is an alternative, not a reading followed by its psalm.
    assert clean_cell("Isaiah 55:1-5 or Psalm 145:8-9") == ["Isaiah 55:1-5 or Psalm 145:8-9"]


def test_clean_cell_easter_vigil_eleven_lines():
    rows = _fixture_rows()
    multi = [row for row in rows if any(" - " in cell for cell in (row.first, row.psalm, row.second, row.gospel))]
    assert len(multi) == 1  # S upstream fact 5: the Vigil's First-reading cell is the only " - " cell
    vigil = multi[0]
    assert vigil.calendar_date == date(2026, 4, 5)
    assert (vigil.psalm, vigil.second, vigil.gospel) == ("", "", "")
    lines = clean_cell(vigil.first)
    assert len(lines) == 11
    assert not any(line.startswith(("Old Testament", "New Testament", "Gospel")) for line in lines)
    longest = max(lines, key=len)
    assert longest == "Baruch 3:9-15, 3:32-4:4 or Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19"
    assert len(longest) == 69
    assert "Ezekiel 36:24-28 and Psalm 42 and 43" in lines
    assert "Genesis 1:1-2:4a and Psalm 136:1-9, 23-26" in lines
    assert "Romans 6:3-11 and Psalm 114" in lines
    (vigil_set,) = [s for s in vanderbilt_sets_on(list(rows), date(2026, 4, 5)) if s.name == vigil.liturgical_date]
    assert vigil_set.scriptures == tuple(lines)
    assert vigil_set.gospel == ""  # so the Vigil never matches a Lectio group


def test_fits_draft_limits(caplog):
    ok = ["Isaiah 5:1-7"]
    assert fits_draft_limits(_rs(lines=ok))
    assert fits_draft_limits(_rs(lines=["x" * 200] * 20))
    assert fits_draft_limits(_rs(name="n" * 300, lines=ok))
    assert fits_draft_limits(_group(first="Isaiah 5:1-7", gospel="Matthew 21:33-46"))
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert not fits_draft_limits(_rs(name="Too many", lines=["Psalm 1"] * 21))
        assert not fits_draft_limits(_rs(lines=["x" * 201]))
        assert not fits_draft_limits(_rs(lines=[]))
        assert not fits_draft_limits(_rs(lines=["Psalm 1", ""]))
        assert not fits_draft_limits(_rs(name="n" * 301, lines=ok))
        assert not fits_draft_limits(_rs(name="", lines=ok))
        assert not fits_draft_limits(_group())
        assert not fits_draft_limits(_group(first="x" * 201))
    dropped = [r.getMessage() for r in caplog.records if r.getMessage().startswith("reading_set_dropped ")]
    assert len(dropped) == 8
    assert dropped[0] == (
        "reading_set_dropped name='Too many' name_chars=8 lines=21 line_chars=[7, 7, 7, 7, 7, 7, 7, 7, 7, 7, "
        "7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7]"
    )
    assert dropped[1] == "reading_set_dropped name='Set' name_chars=3 lines=1 line_chars=[201]"
    assert f"name='{'n' * 80}' name_chars=301 " in dropped[4]
    assert dropped[7] == "reading_set_dropped name='(lectio group)' name_chars=0 lines=1 line_chars=[201]"


def test_rejected_set_dropped_before_merge_default_without_it():
    on = date(2026, 3, 29)
    palms = _rs(
        name="Liturgy of the Palms", lines=["Psalm 118:1-2, 19-29", "Matthew 21:1-11"], gospel="Matthew 21:1-11"
    )
    passion = _rs(
        name="Liturgy of the Passion", lines=["Isaiah 50:4-9a"] * 21, gospel="Matthew 26:14-27:66 or Matthew 27:11-54"
    )
    lectio = LectioDay(
        groups=(_group("Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11", "Matthew 26:14-27:66"),),
        season="Lent",
        year="A",
        day_name=None,
    )
    # Unfiltered, the Passion set would take the Lectio readings and be the default.
    assert merge(lectio, [palms, passion], on)[1] == 1
    kept = [s for s in (palms, passion) if fits_draft_limits(s)]
    assert kept == [palms]
    # Filtered first: the Lectio group matches nothing left, and the default is computed without Passion.
    assert merge(lectio, kept, on) == ([palms], 0)


def test_vanderbilt_sets_on_exact_date_only():
    rows = [
        _vrow("Holy Name of Jesus", date(2026, 1, 1), gospel="Luke 2:15-21"),
        _vrow("New Year's Day", date(2026, 1, 1), gospel="Matthew 25:31-46"),
        _vrow("Liturgy of the Palms", date(2026, 3, 29), psalm="Psalm 118:1-2, 19-29", gospel="Matthew 21:1-11"),
        _vrow("Nativity of the Lord - Proper I", date(2025, 12, 24), gospel="Luke 2:1-14, (15-20)"),
    ]
    assert [s.name for s in vanderbilt_sets_on(rows, date(2026, 1, 1))] == ["Holy Name of Jesus", "New Year's Day"]
    # A row after later-dated rows is still found (the file is not in date order).
    assert [s.name for s in vanderbilt_sets_on(rows, date(2025, 12, 24))] == ["Nativity of the Lord - Proper I"]
    # No row on the date: [] (no nearest-previous fallback), weekday or Sunday alike.
    assert vanderbilt_sets_on(rows, date(2026, 3, 31)) == []
    assert vanderbilt_sets_on(rows, date(2026, 4, 12)) == []
    assert vanderbilt_sets_on([], date(2026, 3, 29)) == []
    # S upstream fact 4: the recorded file is not in date order (Nativity rows after January rows).
    recorded = [row.calendar_date for row in _fixture_rows()]
    assert recorded != sorted(recorded)


def test_proper_row_renamed_named_rows_kept():
    rows = [
        _vrow("Proper 22 (27)", date(2026, 10, 4), gospel="Matthew 21:33-46"),
        _vrow("Proper 22 (27), alternate", date(2026, 10, 4), gospel="Matthew 21:33-46"),
        _vrow("Visitation", date(2026, 5, 31), gospel="Luke 1:39-57"),
        _vrow("Trinity Sunday", date(2026, 5, 31), gospel="Matthew 28:16-20"),
        _vrow("All Saints Day", date(2026, 11, 1), gospel="Matthew 5:1-12"),
        _vrow("Proper 26 (31)", date(2026, 11, 1), gospel="Matthew 23:1-12"),
        _vrow("Proper 29 (34)", date(2026, 11, 22), gospel="Matthew 25:31-46"),
        _vrow("Proper 22 (27)", date(2026, 10, 6), gospel="Matthew 21:33-46"),
    ]

    def names(on):
        return [s.name for s in vanderbilt_sets_on(rows, on)]

    # The whole cell must be "Proper N (M)"; anything else is kept as written.
    assert names(date(2026, 10, 4)) == ["Nineteenth Sunday after Pentecost", "Proper 22 (27), alternate"]
    assert names(date(2026, 5, 31)) == ["Visitation", "Trinity Sunday"]
    # The All Saints row keeps its name; the Proper row takes the computed ordinal (clarification 30).
    assert names(date(2026, 11, 1)) == ["All Saints Day", "Twenty-Third Sunday after Pentecost"]
    # Reign of Christ is the rename's intended result for the last Proper.
    assert names(date(2026, 11, 22)) == ["Reign of Christ"]
    # Sundays only: a weekday Proper row keeps its text.
    assert names(date(2026, 10, 6)) == ["Proper 22 (27)"]


def test_lectio_alternatives_skipped():
    payload = {
        "data": {
            "season": "Ordinary Time",
            "year": "A",
            "dayName": None,
            "readings": [
                {"type": "first", "citation": "Exodus 20:1-4, 7-9, 12-20", "isAlternative": False},
                {"type": "first", "citation": "Isaiah 5:1-7", "isAlternative": True},
                {"type": "psalm", "citation": "Psalm 19", "isAlternative": False},
                {"type": "psalm", "citation": "Psalm 80:7-15", "isAlternative": True},
                {"type": "second", "citation": "Philippians 3:4b-14"},
                {"type": "gospel", "citation": " Matthew 21:33-46 ", "isAlternative": False},
            ],
        }
    }
    assert parse_lectio_payload(payload) == LectioDay(
        groups=(
            LectioGroup(
                first="Exodus 20:1-4, 7-9, 12-20",
                psalm="Psalm 19",
                second="Philippians 3:4b-14",
                gospel="Matthew 21:33-46",
                scriptures=("Exodus 20:1-4, 7-9, 12-20", "Psalm 19", "Philippians 3:4b-14", "Matthew 21:33-46"),
            ),
        ),
        season="Ordinary Time",
        year="A",
        day_name=None,
    )
    # A missing type leaves a blank field and no line; dayName is kept, trimmed.
    day = parse_lectio_payload(
        {
            "data": {
                "dayName": " Holy Cross ",
                "readings": [{"type": "first", "citation": "Numbers 21:4b-9"}, {"type": "gospel", "citation": "John 3:13-17"}],
            }
        }
    )
    assert day.groups == (_group(first="Numbers 21:4b-9", gospel="John 3:13-17"),)
    assert (day.season, day.year, day.day_name) == ("", "", "Holy Cross")
    # The recorded 2026-10-04 response: one group, S's gospel.
    recorded = _fixture_lectio(date(2026, 10, 4))
    assert len(recorded.groups) == 1
    assert scripture_key(recorded.groups[0].gospel) == scripture_key("Matthew 21:33-46")


def test_lectio_trinity_two_groups():
    payload = {
        "data": {
            "season": "Ordinary Time",
            "year": "A",
            "dayName": None,
            "readings": [
                {"type": "first", "citation": "Genesis 6:9-22; 7:24; 8:14-19"},
                {"type": "psalm", "citation": "Psalm 46"},
                {"type": "second", "citation": "Romans 1:16-17; 3:22b-28, (29-31)"},
                {"type": "gospel", "citation": "Matthew 7:21-29"},
                {"type": "first", "citation": "Genesis 1:1-2:4a"},
                {"type": "psalm", "citation": "Psalm 8"},
                {"type": "second", "citation": "2 Corinthians 13:11-13"},
                {"type": "gospel", "citation": "Matthew 28:16-20"},
            ],
        }
    }
    day = parse_lectio_payload(payload)
    assert [g.gospel for g in day.groups] == ["Matthew 7:21-29", "Matthew 28:16-20"]
    assert day.groups[1].scriptures == ("Genesis 1:1-2:4a", "Psalm 8", "2 Corinthians 13:11-13", "Matthew 28:16-20")
    # S upstream fact 3: the recorded Trinity response carries Proper 4 then Trinity.
    recorded = _fixture_lectio(date(2026, 5, 31))
    assert [scripture_key(g.gospel) for g in recorded.groups] == [
        scripture_key("Matthew 7:21-29"),
        scripture_key("Matthew 28:16-20"),
    ]


def test_lectio_empty_is_none():
    for payload in (
        {},
        {"data": None},
        {"data": {}},
        {"data": {"readings": []}},
        {"data": {"readings": None}},
        {"data": {"readings": [{"type": "gospel", "citation": "John 3:16", "isAlternative": True}]}},
    ):
        assert parse_lectio_payload(payload) is None, payload


def test_lectio_bad_shape_raises():
    for payload in (
        [],
        "text",
        None,
        {"data": "x"},
        {"data": ["x"]},
        {"data": {"readings": "x"}},
        {"data": {"readings": ["x"]}},
        {"data": {"readings": [{"type": "gospel", "citation": 316}]}},
    ):
        with pytest.raises((TypeError, ValueError)):
            parse_lectio_payload(payload)
    # A number for season or year is coerced, not an error (clarification 15).
    day = parse_lectio_payload(
        {"data": {"season": 7, "year": 2026, "readings": [{"type": "gospel", "citation": "John 3:16"}]}}
    )
    assert (day.season, day.year, day.day_name) == ("7", "2026", None)


def test_lectio_names_deduplicated():
    on = date(2026, 5, 31)
    g1 = _group(first="Genesis 6:9-22", gospel="Matthew 7:21-29")
    g2 = _group(first="Genesis 1:1-2:4a", gospel="Matthew 28:16-20")
    g3 = _group(first="Isaiah 6:1-8", gospel="John 3:1-17")
    day = LectioDay(groups=(g1, g2, g3), season="Ordinary Time", year="A", day_name=None)
    sets, default = merge(day, [], on)
    assert [(s.name, s.source) for s in sets] == [
        ("Trinity Sunday", "lectio"),
        ("Trinity Sunday (2)", "lectio"),
        ("Trinity Sunday (3)", "lectio"),
    ]
    assert default == 2
    assert (sets[1].first, sets[1].gospel, sets[1].scriptures) == (g2.first, g2.gospel, g2.scriptures)
    named = dataclasses.replace(day, groups=(g1, g2), day_name="Holy Trinity")
    assert [s.name for s in merge(named, [], on)[0]] == ["Holy Trinity", "Holy Trinity (2)"]
    # Each named set is checked again (clarification 34): a 300-character name fits, " (2)" does not.
    long_name = dataclasses.replace(day, groups=(g1, g2), day_name="n" * 300)
    sets, default = merge(long_name, [], on)
    assert [s.name for s in sets] == ["n" * 300]
    assert default == 0
    too_long = dataclasses.replace(day, groups=(g1,), day_name="n" * 301)
    assert merge(too_long, [], on) == ([], None)


def test_merge_table():
    for on, expected, default, lectio_gospel in _MERGE_TABLE:
        sets, got_default = _merge_on(on)
        assert len(sets) == len(expected), (on, [s.name for s in sets])
        for reading_set, (name, source) in zip(sets, expected):
            assert _name_matches(name, reading_set.name), (on, reading_set.name)
            assert reading_set.source == source, (on, reading_set.name, reading_set.source)
            assert not _PROPER_ROW.fullmatch(reading_set.name), (on, reading_set.name)
        assert got_default == default, on
        merged = [s for s in sets if s.source == "merged"]
        if lectio_gospel is None:
            assert merged == [], on
            continue
        (merged_set,) = merged
        assert sets.index(merged_set) == default, on
        group = next(
            g for g in _fixture_lectio(on).groups if scripture_key(g.gospel) == scripture_key(lectio_gospel)
        )
        assert (merged_set.gospel, merged_set.scriptures) == (group.gospel, group.scriptures), on
    by_date = {on: _merge_on(on)[0] for on in _MERGE_DATES}
    # Easter: the Vigil keeps 11 lines and no headings.
    assert len(by_date[date(2026, 4, 5)][0].scriptures) == 11
    # Ascension: Lectio's Matthew 28 matches nothing, so Vanderbilt's Luke 24:44-53 stays.
    assert scripture_key("Luke 24:44-53") in {scripture_key(s) for s in by_date[date(2026, 5, 14)][0].scriptures}
    # Thanksgiving Day: the compound cell is split (S's example).
    assert by_date[date(2026, 11, 26)][0].scriptures == (
        "Deuteronomy 8:7-18",
        "Psalm 65",
        "2 Corinthians 9:6-15",
        "Luke 17:11-19",
    )
    # Each Lectio group replaces at most one set: a second set with the same gospel stays Vanderbilt's.
    twin_a = _rs(name="A", gospel="John 20:1-18 or Matthew 28:1-10")
    twin_b = _rs(name="B", gospel="John 20:1-18")
    one_group = LectioDay(groups=(_group(gospel="John 20:1-18"),), season="", year="", day_name=None)
    sets, default = merge(one_group, [twin_a, twin_b], date(2026, 4, 5))
    assert [(s.name, s.source) for s in sets] == [("A", "merged"), ("B", "vanderbilt")]
    assert default == 0


def test_merge_empty_and_single_source_defaults():
    on = date(2026, 10, 4)
    no_groups = LectioDay(groups=(), season="Ordinary Time", year="A", day_name=None)
    assert merge(None, [], on) == ([], None)
    assert merge(no_groups, [], on) == ([], None)
    # Vanderbilt down: the Lectio group alone, named by lectio_set_name, source "lectio", default last.
    group = _group("Exodus 20:1-4, 7-9, 12-20", "Psalm 19", "Philippians 3:4b-14", "Matthew 21:33-46")
    lectio = LectioDay(groups=(group,), season="Ordinary Time", year="A", day_name=None)
    sets, default = merge(lectio, [], on)
    assert [(s.name, s.source, s.scriptures) for s in sets] == [
        ("Nineteenth Sunday after Pentecost", "lectio", group.scriptures)
    ]
    assert default == 0
    # Lectio none (404) or no groups: the Vanderbilt sets as they are, default last (parity).
    holy_name = _rs(name="Holy Name of Jesus", lines=["Luke 2:15-21"], gospel="Luke 2:15-21")
    new_year = _rs(name="New Year's Day", lines=["Matthew 25:31-46"], gospel="Matthew 25:31-46")
    assert merge(None, [holy_name, new_year], date(2026, 1, 1)) == ([holy_name, new_year], 1)
    assert merge(no_groups, [holy_name, new_year], date(2026, 1, 1)) == ([holy_name, new_year], 1)
    # A Lectio group without a gospel never matches; unmatched groups are dropped.
    no_gospel = LectioDay(groups=(_group(first="Isaiah 5:1-7"),), season="", year="", day_name=None)
    assert merge(no_gospel, [holy_name, new_year], date(2026, 1, 1)) == ([holy_name, new_year], 1)


def test_every_fixture_date_fits_limits():
    assert sorted(_MERGE_DATES) == sorted(upstream_fixtures.FIXTURE_DATES)
    rows = list(_fixture_rows())
    for on in _MERGE_DATES:
        for reading_set in vanderbilt_sets_on(rows, on):
            assert fits_draft_limits(reading_set), (on, reading_set.name)
        lectio = _fixture_lectio(on)
        for group in lectio.groups if lectio else ():
            assert fits_draft_limits(group), (on, group.gospel)
        sets, default = _merge_on(on)
        assert (default is None) == (sets == [])
        for reading_set in sets:
            assert 1 <= len(reading_set.name) <= 300, (on, reading_set.name)
            assert 1 <= len(reading_set.scriptures) <= 20, (on, reading_set.name)
            assert all(1 <= len(line) <= 200 for line in reading_set.scriptures), (on, reading_set.name)
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | grep -m1 'ImportError:'
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | tail -1
```

**Expected:** `E   ImportError: cannot import name 'LectionaryFormatError' from 'vanderbilt_lectionary' (<repo>/backend/vanderbilt_lectionary.py)`, then `1 error in <t>s`. The module fails at collection, so Task 6a's ten tests do not run either. That is expected here and is fixed by Step 5.

- [ ] **Step 4 (agent): Extend the import block**

In `backend/vanderbilt_lectionary.py`, replace lines 8-13:

```python
import csv
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any
import httpx
```

with:

```python
import csv
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

import httpx

from scripture_refs import scripture_key, split_alternatives, split_book
```

The old names `Any`, `Dict`, `List` and `Optional` are still imported, because the old path uses them until Task 7. `scripture_refs` imports nothing from this module, so there is no import cycle.

- [ ] **Step 5 (agent): Append the parsing and merge section**

Append this block to the end of `backend/vanderbilt_lectionary.py`, after the current last line (`    return _WEEKDAY_NAMES[d.weekday()]`). The block starts with two blank lines:

```python


# ---------------------------------------------------------------------------
# Slice 2a (Task 6b): Vanderbilt and Lectio parsing, the draft-limit guard and
# the merge (S "Lectionary domain": Vanderbilt parsing, Lectio parsing, Merge).
# Pure: no I/O. Task 7 adds the fetchers and loaders and deletes the old code.
# ---------------------------------------------------------------------------

MAX_SET_LINES = 20        # ServiceDraft's scripture limit (S "Draft-limit guard")
MAX_LINE_CHARS = 200      # ServiceDraft's per-line limit
MAX_NAME_CHARS = 300      # the Occasion field's limit (S :142; clarification 34)

_VANDERBILT_FIELDS = [
    "Liturgical Date", "Calendar Date", "First reading", "Psalm",
    "Second reading", "Gospel", "Art", "Prayer",
]
_PROPER_ROW = re.compile(r"Proper \d+ \(\d+\)")
_COMPOUND_PSALM = re.compile(r"\sPsalms?\s+\d")
_LEADING_STAR = re.compile(r"^\*\s*")
_LECTIO_TYPES = ("first", "psalm", "second", "gospel")


class LectionaryFormatError(ValueError):
    """The Vanderbilt body is not the year CSV (for example an HTML page served as 200)."""


@dataclass(frozen=True)
class VRow:
    """One Vanderbilt CSV row. The reading cells are the raw cell text, trimmed and unquoted."""

    liturgical_date: str
    calendar_date: date
    first: str
    psalm: str
    second: str
    gospel: str


@dataclass(frozen=True)
class ReadingSet:
    """One reading set. `first`..`gospel` feed matching; the API exposes `name`, `scriptures` and `source`.

    For a Vanderbilt set each of the four fields is the cleaned cell text, unsplit; `scriptures` holds the
    split lines (clarification 12). For a Lectio or merged set they are the Lectio group's citations.
    """

    name: str
    first: str
    psalm: str
    second: str
    gospel: str
    scriptures: tuple[str, ...]
    source: Literal["lectio", "vanderbilt", "merged"]


def _parse_calendar_date(cell: str) -> date | None:
    """A Vanderbilt calendar date such as "Feb 15, 2026" or "January 06, 2027"; None when it does not parse."""
    text = (cell or "").strip().strip('"').strip()
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _field(raw: dict, name: str) -> str:
    return (raw.get(name) or "").strip().strip('"').strip()


def parse_vanderbilt_csv(text: str) -> list[VRow]:
    """Parse a Vanderbilt year CSV: skip the preamble, use the fixed field names, keep rows whose date parses.

    Raises LectionaryFormatError when no header line exists (an HTML page, an empty body). A line holding
    markup (`<`) is never the header, so an HTML calendar table with both labels on one line still raises.
    """
    lines = [line for line in text.splitlines() if line.strip()]
    header = next(
        (i for i, line in enumerate(lines) if "Calendar Date" in line and "Liturgical Date" in line and "<" not in line),
        None,
    )
    if header is None:
        raise LectionaryFormatError("no Vanderbilt CSV header line")
    rows: list[VRow] = []
    for raw in csv.DictReader(lines[header + 1:], fieldnames=_VANDERBILT_FIELDS):
        calendar_date = _parse_calendar_date(raw.get("Calendar Date") or "")
        if calendar_date is None:
            continue
        rows.append(
            VRow(
                liturgical_date=_field(raw, "Liturgical Date"),
                calendar_date=calendar_date,
                first=_field(raw, "First reading"),
                psalm=_field(raw, "Psalm"),
                second=_field(raw, "Second reading"),
                gospel=_field(raw, "Gospel"),
            )
        )
    return rows


def _clean_text(cell: str) -> str:
    """A reading cell's text: quotes and whitespace stripped, a link dropped, a leading "* " removed."""
    text = (cell or "").strip().strip('"').strip()
    if text.startswith("http"):
        return ""
    return _LEADING_STAR.sub("", text)


def clean_cell(cell: str) -> list[str]:
    """The scripture lines in one Vanderbilt reading cell (S "Cell cleanup")."""
    text = _clean_text(cell)
    if not text:
        return []
    if " - " in text:
        # The Easter Vigil: " - "-separated segments with headings. Keep every segment that starts with a
        # book, whole, so each vigil reading stays next to its psalm (11 lines; splitting pairs gives 21).
        segments = (segment.strip() for segment in text.split(" - "))
        return [segment for segment in segments if segment and split_book(segment) is not None]
    match = _COMPOUND_PSALM.search(text)
    if match:
        head = text[: match.start()].strip()
        found = split_book(head)
        # Split a two-track cell "<reading> Psalm <n>" only when the head is a non-Psalm reading and does
        # not end in " or", so "Psalm 105:1-11, 45b or Psalm 128" stays whole (clarification 10).
        if found is not None and found[0].testament != "psalm" and not head.lower().endswith(" or"):
            return [head, text[match.start():].strip()]
    return [text]


def fits_draft_limits(item: ReadingSet | LectioGroup) -> bool:
    """True when the set fits the draft: 1-20 lines of 1-200 characters, and a 1-300-character name.

    The name check applies to a ReadingSet only (a Lectio group has no name until `merge` names it).
    A rejected set is logged at WARNING with its name and lengths, never its readings; it is never truncated.
    """
    lines = item.scriptures
    name = item.name if isinstance(item, ReadingSet) else None
    fits = (
        1 <= len(lines) <= MAX_SET_LINES
        and all(1 <= len(line) <= MAX_LINE_CHARS for line in lines)
        and (name is None or 1 <= len(name) <= MAX_NAME_CHARS)
    )
    if not fits:
        logger.warning(
            "reading_set_dropped name=%r name_chars=%d lines=%d line_chars=%s",
            "(lectio group)" if name is None else name[:80],
            0 if name is None else len(name),
            len(lines),
            [len(line) for line in lines],
        )
    return fits


def _vanderbilt_name(raw: str, d: date) -> str:
    """A row's set name: its own text, except a whole-cell "Proper N (M)" on a Sunday (owner decision A)."""
    if d.weekday() != 6 or not _PROPER_ROW.fullmatch(raw):
        return raw
    name = sunday_name(d)
    if name == "All Saints Day":
        # The All Saints row keeps that name; the Proper row takes the computed ordinal (clarification 30).
        name = _ordinary_time_name(d)
    return name or raw


def vanderbilt_sets_on(rows: list[VRow], d: date) -> list[ReadingSet]:
    """The Vanderbilt sets for exactly `d`, in file order; [] when no row has that date (no nearest row)."""
    sets: list[ReadingSet] = []
    for row in rows:
        if row.calendar_date != d:
            continue
        cells = (row.first, row.psalm, row.second, row.gospel)
        sets.append(
            ReadingSet(
                name=_vanderbilt_name(row.liturgical_date, d),
                first=_clean_text(row.first),
                psalm=_clean_text(row.psalm),
                second=_clean_text(row.second),
                gospel=_clean_text(row.gospel),
                scriptures=tuple(line for cell in cells for line in clean_cell(cell)),
                source="vanderbilt",
            )
        )
    return sets


def _lectio_group(by_type: dict[str, str]) -> LectioGroup:
    first, psalm, second, gospel = (by_type.get(kind, "") for kind in _LECTIO_TYPES)
    return LectioGroup(
        first=first,
        psalm=psalm,
        second=second,
        gospel=gospel,
        scriptures=tuple(s for s in (first, psalm, second, gospel) if s),
    )


def parse_lectio_payload(payload: object) -> LectioDay | None:
    """A Lectio response body as a LectioDay; None when `data` is missing or has no usable readings.

    Alternatives are skipped (parity) and a new group starts when a reading type repeats (Trinity 2026).
    An unexpected shape raises TypeError, so the loader's except clause covers it (clarification 15);
    `season` and `year` are coerced with str().
    """
    if not isinstance(payload, dict):
        raise TypeError("Lectio payload is not a JSON object")
    data = payload.get("data")
    if not data:
        return None
    if not isinstance(data, dict):
        raise TypeError("Lectio 'data' is not an object")
    readings = data.get("readings") or []
    if not isinstance(readings, list):
        raise TypeError("Lectio 'readings' is not a list")
    groups: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for reading in readings:
        if not isinstance(reading, dict):
            raise TypeError("a Lectio reading is not an object")
        if reading.get("isAlternative"):
            continue
        kind = reading.get("type")
        if kind not in _LECTIO_TYPES:
            continue
        citation = reading.get("citation") or ""
        if not isinstance(citation, str):
            raise TypeError("a Lectio citation is not a string")
        if kind in current:
            groups.append(current)
            current = {}
        current[kind] = citation.strip()
    if current:
        groups.append(current)
    if not groups:
        return None
    day_name = str(data.get("dayName") or "").strip()
    return LectioDay(
        groups=tuple(_lectio_group(group) for group in groups),
        season=str(data.get("season") or "").strip(),
        year=str(data.get("year") or "").strip(),
        day_name=day_name or None,
    )


def _set_from_group(group: LectioGroup, name: str, source: Literal["lectio", "merged"]) -> ReadingSet:
    return ReadingSet(
        name=name,
        first=group.first,
        psalm=group.psalm,
        second=group.second,
        gospel=group.gospel,
        scriptures=group.scriptures,
        source=source,
    )


def _lectio_only_sets(lectio: LectioDay, d: date) -> list[ReadingSet]:
    """Every Lectio group as a set, named by lectio_set_name, the second and later with " (2)", " (3)".

    Each named set is checked again with fits_draft_limits, now that it has a name (clarification 34).
    """
    base = lectio_set_name(lectio, d)
    sets: list[ReadingSet] = []
    for index, group in enumerate(lectio.groups):
        name = base if index == 0 else f"{base} ({index + 1})"
        candidate = _set_from_group(group, name, "lectio")
        if fits_draft_limits(candidate):
            sets.append(candidate)
    return sets


def merge(
    lectio: LectioDay | None, v_sets: list[ReadingSet], d: date
) -> tuple[list[ReadingSet], int | None]:
    """Merge the day's Lectio groups into its Vanderbilt sets (S "Merge"); returns (sets, default_index).

    Both inputs have already passed fits_draft_limits. A Lectio group replaces at most one Vanderbilt set,
    matched by scripture_key(gospel) against each of the set's gospel alternatives, and keeps that set's
    name; unmatched groups are dropped when Vanderbilt has rows. default_index is None only when sets is [].
    """
    has_lectio = lectio is not None and bool(lectio.groups)
    if not v_sets:
        if not has_lectio:
            return [], None
        sets = _lectio_only_sets(lectio, d)
        return sets, (len(sets) - 1 if sets else None)
    sets = list(v_sets)
    if not has_lectio:
        return sets, len(sets) - 1
    matched: set[int] = set()
    for group in lectio.groups:
        key = scripture_key(group.gospel)
        if not key:
            continue
        for index, v_set in enumerate(sets):
            if index in matched:
                continue
            if key in {scripture_key(alt) for alt in split_alternatives(v_set.gospel)}:
                sets[index] = _set_from_group(group, v_set.name, "merged")
                matched.add(index)
                break
    return sets, (max(matched) if matched else len(sets) - 1)
```

- [ ] **Step 6 (agent): Run the tests, check the change is additive, run the whole suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | tail -1
git diff -U0 backend/vanderbilt_lectionary.py | grep '^-' | grep -v '^---'
git diff -U0 backend/tests/test_lectionary_domain.py | grep '^-' | grep -v '^---'
grep -c '^def get_readings_for_date_string\|^def fetch_lectionary_year\|^def _parse_csv_date\|^_cache: ' backend/vanderbilt_lectionary.py
git diff --stat
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `28 passed in <t>s`;
- exactly one removed line in the module, `-from typing import Optional, List, Dict, Any`;
- exactly two removed lines in the test file, `-Task 6b appends the Vanderbilt and Lectio parsing and the merge tests.` and `-Everything here is date arithmetic: no fixtures, no network, no clock.`;
- `4` (the old path is still there for Task 7 to delete);
- `backend/tests/test_lectionary_domain.py | 561 ++++…-` and `backend/vanderbilt_lectionary.py | 308 ++++…-`, then `2 files changed, 866 insertions(+), 3 deletions(-)` (a few lines more or less is fine if Task 6a's final text differs by a line; the removed-line checks above are the ones that matter);
- `884 passed, 9 skipped in <t>s` (866 + 18). If the count differs, stop and find why before committing.

If only fixture-driven tests fail (`test_parse_csv_finds_header_after_preamble`, `test_parse_csv_html_raises`, `test_clean_cell_easter_vigil_eleven_lines`, `test_vanderbilt_sets_on_exact_date_only`, `test_lectio_alternatives_skipped`, `test_lectio_trinity_two_groups`, `test_merge_table`, `test_every_fixture_date_fits_limits`) and the failing line reads a recorded value, follow T6b-9: stop and report. Do not change the code, the fixture or the assert to make it pass.

- [ ] **Step 7 (agent): Commit**

```bash
git status --short
git add backend/vanderbilt_lectionary.py backend/tests/test_lectionary_domain.py
git commit -m "Lectionary: Vanderbilt and Lectio parsing, draft-limit guard and merge (S Lectionary domain; AC1, AC4)

parse_vanderbilt_csv finds the header after the preamble and raises
LectionaryFormatError on HTML. vanderbilt_sets_on returns only the rows
dated exactly d (no nearest-previous row) and renames a whole-cell
'Proper N (M)' Sunday to its occasion name; the All Saints Proper row
takes the computed ordinal (clarification 30). clean_cell splits two-track
cells and keeps each Easter Vigil reading with its psalm (11 lines).
fits_draft_limits guarantees 1-20 lines of 1-200 characters and a
1-300-character name (clarification 34). parse_lectio_payload skips
alternatives and starts a group when a type repeats (Trinity 2026).
merge matches Lectio groups to Vanderbilt sets by gospel key and picks
the default. Additive: the old path stays until Task 7 deletes it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** the first `git status --short` prints exactly:

```
 M backend/tests/test_lectionary_domain.py
 M backend/vanderbilt_lectionary.py
?? .claude/
```

then `<sha> Lectionary: Vanderbilt and Lectio parsing, draft-limit guard and merge (S Lectionary domain; AC1, AC4)`, then only `?? .claude/`.

- [ ] **Step 8 (agent): Review checkpoint**

Stop for the task review before Task 7. The reviewer checks:
- the module diff removes only the old `typing` line;
- nothing in the new section does I/O or reads a clock, and its only log line is `reading_set_dropped`, which carries no reading text;
- `clean_cell` splits a compound cell only when the head starts with a non-Psalm book and does not end in " or" (clarification 10), and splits the Vigil on `" - "` without splitting its pairs;
- `_vanderbilt_name` uses `fullmatch`, runs only on Sundays, and maps `"All Saints Day"` to `_ordinary_time_name(d)` (clarification 30);
- `merge` follows S's pseudocode line by line (each group replaces at most one set; unmatched groups are dropped when Vanderbilt has rows; `default = max(matched)` or the last set);
- `test_merge_table` has one row for each dated row of S's merge table (13), and the "Vanderbilt down" row is covered by `test_merge_empty_and_single_source_defaults`.
### Task 7: Fetchers, loaders and `usecases/lectionary.py`; delete the old lectionary code (S Fetchers, Loaders, `usecases/lectionary.py`, Deleted; AC1–AC3; clarifications 14, 18, 19, 23, 31, 39)

This task wires T6a/T6b's pure lectionary domain to the network and to the API layer's future caller. It appends the two fetchers and the two loaders to `backend/vanderbilt_lectionary.py`, creates `backend/usecases/lectionary.py` (`readings_for_date`: both sources in parallel on one module pool, each through its own `TTLCache`, a 20 s source deadline, the S status rules and one log line), and then deletes the old lookup: the module-level dict cache, the nearest-previous-row search, the Sunday normalization and `get_readings_for_date_string`.

T6a and T6b were additive: the old code still sits, verbatim, beside their new names, but where they inserted their code is theirs to choose. So the new code is appended at the end of the file (after every T6 name it uses), the two imports are anchored on the unique `logger = logging.getLogger(__name__)` line, and the old code is removed **by name** with a short `ast` script that stops, changing nothing, if any old name is still referenced by the new code. The script also replaces the module docstring and prunes imports the deletions left unused.

After this task `app.py` on `main` can no longer be imported (`app.py:28` imports `get_readings_for_date_string`). That is accepted (clarification 23; owner decision 2): production Streamlit runs from `streamlit-frozen`, no test imports `app.py`, and there is no shim.

The tests use respx (T1, owner Q1a) over the T1 recordings. Tests that block a pool worker use a `threading.Event` or `threading.Barrier`, never `time.sleep`, release it in `finally`, and join the workers before their respx mock closes (clarification 39).

**Files:**
- Create: `backend/usecases/lectionary.py`
- Create: `backend/tests/test_usecase_lectionary.py` (28 tests)
- Modify: `backend/vanderbilt_lectionary.py` (two imports; fetchers and loaders appended; the old lookup and its helpers deleted; new module docstring; unused imports pruned)
- Modify: `backend/tests/upstream_fixtures.py` (respx helpers appended; T8 uses them)
- Modify: `backend/tests/conftest.py` (autouse `_fresh_lectionary_caches`)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (the import string in `test_usecases_package_imports_no_fastapi_or_streamlit` gains `usecases.lectionary` and `vanderbilt_lectionary`)
- Test: `backend/tests/test_usecase_lectionary.py`, `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes:
  - T1: `tests.upstream_fixtures.load(kind: str, name: str) -> Recorded` (`status: int`, `content_type: str`, `body: bytes`). Names used: `lectio/2026-03-29`, `lectio/2026-04-05`, `lectio/2026-10-04` (200s); `lectio/2026-04-03`, `lectio/2026-09-29` (404s); `lectio/html_200`, `lectio/error_500`; `vanderbilt/2025-26`, `vanderbilt/2026-27` (Advent 1 row, 2026-11-29), `vanderbilt/2027-28` (Advent 1 row, 2027-11-28), `vanderbilt/404`, `vanderbilt/html_200`. `respx>=0.22` is installed in `.venv`.
  - T2: `integrations.http.get(url: str, *, params: Mapping[str, str] | None = None, headers: Mapping[str, str] | None = None, read_timeout: float) -> httpx.Response` (User-Agent `WorshipServiceBuilder/1.0`; the https-only hook raises `httpx.UnsupportedProtocol`, an `httpx.HTTPError`, clarification 24); `cache.CacheableFailure`; `cache.TTLCache(maxsize: int, ttl_ok: float, ttl_fail: float, clock: Callable[[], float] = time.monotonic)` with `.get_or_load(key, loader)` (a `CacheableFailure` is stored for `ttl_fail` and re-raised; any other exception is re-raised to the caller and every waiter of the flight and stored nowhere, clarification 36); T2's autouse `_fresh_http_client`.
  - T6a: `liturgical_year_for(d: date) -> str`; `LectioGroup`; `LectioDay(groups: tuple[LectioGroup, ...], season: str, year: str, day_name: str | None)` (frozen dataclass, so `dataclasses.replace` works); `lectio_set_name` (through `merge`).
  - T6b: `LectionaryFormatError(ValueError)`; `VRow`; `ReadingSet` (frozen dataclass: `name`, `first`, `psalm`, `second`, `gospel`, `scriptures`, `source`); `parse_vanderbilt_csv(text: str) -> list[VRow]`; `clean_cell(cell: str) -> list[str]`; `fits_draft_limits(item: ReadingSet | LectioGroup) -> bool`; `vanderbilt_sets_on(rows: list[VRow], d: date) -> list[ReadingSet]`; `parse_lectio_payload(payload: object) -> LectioDay | None` (raises `ValueError` or `TypeError` on a bad shape); `merge(lectio: LectioDay | None, v_sets: list[ReadingSet], d: date) -> tuple[list[ReadingSet], int | None]`.
  - 1a: `domain_errors.InvalidInput(message, *, field=...)` (422 `invalid_request`), `domain_errors.UpstreamError(message, *, code="upstream_error")` (502), `domain_errors.UpstreamTimeout(message, *, code="upstream_timeout")` (504); both codes are already in `ERROR_CODES` (clarification 5). `tests.conftest.FakeClock` (`now()`, `advance(seconds)`).
  - Kept from the current file: `LECTIO_API_URL = "https://lectio-api.org/api/v1/readings"` (`:16`), `VANDERBILT_YEAR_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv"` (`:19`), `logger` (`:14`).
- Produces:
  - `vanderbilt_lectionary`:
    - `class SourceFailed(CacheableFailure)`, built as `SourceFailed(*, timeout: bool)`, with the attribute `timeout: bool`
    - `LECTIO_READ_TIMEOUT = 10.0`, `VANDERBILT_READ_TIMEOUT = 15.0`, `VANDERBILT_MEDIA_TYPES = frozenset({"text/plain", "text/csv"})`
    - `fetch_lectio(d: date) -> Optional[dict]`: 404 → `None`; 200 with `application/json` or a `+json` media type (parameters ignored) whose body decodes to a JSON object → the payload; anything else → `SourceFailed`. Catches only `httpx.HTTPError` (→ `SourceFailed(timeout=isinstance(e, httpx.TimeoutException))`) and a JSON `ValueError` (clarification 18).
    - `fetch_vanderbilt_year(year: str) -> Optional[str]`: 404 → `None`; 200 `text/plain` or `text/csv` (parameters ignored) → the text; anything else → `SourceFailed`.
    - `load_vanderbilt_year(year: str) -> list[VRow]` and `load_lectio(d: date) -> Optional[LectioDay]`, verbatim S "Loaders".
    - Deleted: `_cache`, `fetch_lectionary_year`, `get_readings_for_date`, `_normalize_date_for_match`, `_liturgical_year_for_date`, `_liturgical_sunday_name`, `get_readings_for_date_string`, `_get_readings_from_lectio`, `_row_to_reading`, `_ordinal_sunday_label`, `_easter_date`. `_parse_csv_date` is deleted only when no remaining code calls it (T6b's `parse_vanderbilt_csv` may reuse it).
  - `usecases.lectionary`:
    - `LECTIONARY_UNREACHABLE = "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."`
    - `DATE_OUT_OF_RANGE = "Enter a date between 1900 and 2199."`, `MIN_YEAR = 1900`, `MAX_YEAR = 2199`
    - `DEADLINE_SECONDS = 20.0` (read at call time; tests monkeypatch it), `OK_TTL_SECONDS = 86_400.0`, `FAIL_TTL_SECONDS = 300.0`, `MAX_WORKERS = 4`
    - `_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lectionary")`; `_LECTIO: TTLCache[date, Optional[LectioDay]]` (maxsize 512); `_VANDERBILT: TTLCache[str, list[VRow]]` (maxsize 8, keyed by `liturgical_year_for(d)`)
    - `@dataclass(frozen=True) class LectionaryResult: date: date; status: Literal["ok", "no_readings"]; partial: bool; reading_sets: list[ReadingSet]; default_index: Optional[int]`
    - `readings_for_date(d: date) -> LectionaryResult`; raises `InvalidInput(DATE_OUT_OF_RANGE, field="date")`, `UpstreamError(LECTIONARY_UNREACHABLE, code="upstream_error")`, `UpstreamTimeout(LECTIONARY_UNREACHABLE, code="upstream_timeout")`; any other exception from a loader propagates (a 500, never cached)
    - `reset_for_tests(clock: Callable[[], float] = time.monotonic) -> None`: `_POOL.shutdown(wait=True, cancel_futures=True)`, then a new pool and new `_LECTIO` and `_VANDERBILT` objects on `clock` (clarification 39)
    - One INFO line per lookup that finds sets or none (not on a bug), on logger `usecases.lectionary`: `lectionary_lookup date=<iso> lectio=<ok|none|failed> vanderbilt=<ok|none|failed> lectio_cached=<True|False> vanderbilt_cached=<True|False> sets=<n> duration_ms=<n>`. `cached` is `True` when this request ran no loader (a cache hit or a shared flight), from a flag in the loader wrapper (clarification 14). `vanderbilt=none` covers both a 404 file and a file with no row on the date.
  - `tests.upstream_fixtures` (appended; T8 reuses these): `LECTIO_URL = "https://lectio-api.org/api/v1/readings"`, `VANDERBILT_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/"`, `as_response(recorded: Recorded) -> httpx.Response`, `answer(recorded: Recorded) -> Callable[[httpx.Request], httpx.Response]`, `route_lectio(router: respx.MockRouter, d: date, name: Optional[str] = None) -> respx.Route`, `route_vanderbilt(router: respx.MockRouter, year: str, name: Optional[str] = None) -> respx.Route`
  - `tests/conftest.py`: autouse `_fresh_lectionary_caches` (deferred `sys.modules.get`, as `_fresh_identity_cache`)

**Decisions recorded here (code wins over the outline; owner decision 1):**
- The old code is deleted by name with an `ast` script (Step 9), not by exact replacement blocks, because the file's layout after T6a/T6b depends on where those tasks put their code. The script is exact about *what* goes and refuses to run if any old name is still referenced.
- A source unfinished at the deadline is reported as `SourceFailed(timeout=True)` for this request only, and its future is **not** cancelled: a queued load still runs later and warms the cache for the next request (clarification 31: "its loader keeps running and caches its own outcome").
- `fetch_lectio` also treats a JSON body that is not an object (a list, a string) as `SourceFailed`, so its `-> Optional[dict]` holds.
- `_fresh_lectionary_caches` resets before each test only, like the other autouse resets. Autouse teardowns run after `_no_network` and the test's respx mock are gone, so a test that blocks a worker joins it itself in `finally` (`test_source_unfinished_at_deadline_is_timeout` calls `reset_for_tests()` there).

- [ ] **Step 1 (agent): Check the starting state**

```bash
git status --short
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -c "import respx; print('respx', respx.__version__)"
PYTHONPATH=backend .venv/bin/python -c "import httpx, respx
with respx.mock() as m:
    a = m.get('https://x.test/a', params={'d': '1'}).respond(200)
    b = m.get('https://x.test/b').mock(side_effect=httpx.ReadTimeout)
    httpx.get('https://x.test/a?d=1&t=rcl')
    try: httpx.get('https://x.test/b?q=1')
    except httpx.ReadTimeout: pass
    assert (a.call_count, b.call_count) == (1, 1)
print('respx ok')"
.venv/bin/python -c "import sys; sys.path[:0] = ['backend']; import vanderbilt_lectionary as v, cache, integrations.http; print([n for n in ('easter_date', 'advent_sunday', 'liturgical_year_for', 'VRow', 'ReadingSet', 'LectioGroup', 'LectioDay', 'LectionaryFormatError', 'parse_vanderbilt_csv', 'clean_cell', 'fits_draft_limits', 'vanderbilt_sets_on', 'parse_lectio_payload', 'lectio_set_name', 'sunday_name', 'merge') if not hasattr(v, n)])"
.venv/bin/python -c "import sys; sys.path[:0] = ['.', 'backend']; from tests.upstream_fixtures import load; [print(k, n, load(k, n).status, load(k, n).content_type) for k, n in [('lectio', '2026-03-29'), ('lectio', '2026-04-03'), ('lectio', 'html_200'), ('lectio', 'error_500'), ('vanderbilt', '2025-26'), ('vanderbilt', '2026-27'), ('vanderbilt', '2027-28'), ('vanderbilt', '404'), ('vanderbilt', 'html_200')]]"
```

**Expected:**
- `git status --short` lists only `?? .claude/`.
- The suite line is `884 passed, 9 skipped in …` (the T6b count). If it differs, stop and find why.
- `respx 0.22.0` or later.
- `respx ok`: the installed respx matches a `params=` route by containment, lets a query-less route match a URL with a query, and counts a side-effect exception in `call_count`; the tests below rely on all three. If it prints anything else (an `AssertionError` or a respx error), stop and report the output: Step 8 would otherwise fail in a way that looks like a usecase bug.
- The missing-names list is `[]`.
- The fixture lines show `lectio 2026-03-29 200 application/json…`, `lectio 2026-04-03 404 …`, `lectio html_200 200 text/html…`, `lectio error_500 500 …`, `vanderbilt 2025-26 200 …`, `vanderbilt 2026-27 200 …`, `vanderbilt 2027-28 200 …`, `vanderbilt 404 404 text/html…`, `vanderbilt html_200 200 text/html…`.
- The three Vanderbilt CSV media types (the part before any `;`) are `text/csv` or `text/plain`. **If a recording shows another type** (for example `application/csv` or `application/octet-stream`), that is the A3 case (clarification 19): in Step 5, add exactly that media type to `VANDERBILT_MEDIA_TYPES`, and write one line in the task report, "Vanderbilt serves `<type>` (recorded <date>); added to VANDERBILT_MEDIA_TYPES (owner decision 1; clarification 19)", which T12 copies into S's corrections. Likewise a Lectio 200 recorded with a type that is neither `application/json` nor `…+json` stops the task: report it.

- [ ] **Step 2 (agent): Append the respx helpers to `backend/tests/upstream_fixtures.py`**

Append this block to the **end** of `backend/tests/upstream_fixtures.py`, after two blank lines, leaving T1's code above it unchanged. It uses T1's `Recorded` and `load`, which are defined above it.

```python
# --- respx routes over the recordings (slice 2a T7) --------------------------
# The imports sit here, beside the only code that needs them (`date` is T1's
# top-level import).
from typing import Callable, Optional  # noqa: E402

import httpx  # noqa: E402
import respx  # noqa: E402

LECTIO_URL = "https://lectio-api.org/api/v1/readings"
VANDERBILT_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/"


def as_response(recorded: Recorded) -> httpx.Response:
    """A new httpx.Response with the recording's status, Content-Type and body."""
    return httpx.Response(
        recorded.status, content=recorded.body, headers={"Content-Type": recorded.content_type}
    )


def answer(recorded: Recorded) -> Callable[[httpx.Request], httpx.Response]:
    """A respx side effect that answers every call with a new copy of `recorded`."""
    return lambda request: as_response(recorded)


def route_lectio(router: respx.MockRouter, d: date, name: Optional[str] = None) -> respx.Route:
    """Lectio for exactly `d` answers with lectio/<name>; by default d's own recording."""
    return router.get(LECTIO_URL, params={"date": d.isoformat()}).mock(
        side_effect=answer(load("lectio", name or d.isoformat()))
    )


def route_vanderbilt(router: respx.MockRouter, year: str, name: Optional[str] = None) -> respx.Route:
    """The Vanderbilt file for `year` ("2025-26") answers with vanderbilt/<name>;
    by default the year's own recording."""
    return router.get(VANDERBILT_URL.format(year=year)).mock(
        side_effect=answer(load("vanderbilt", name or year))
    )
```

- [ ] **Step 3 (agent): Write the failing tests**

Create `backend/tests/test_usecase_lectionary.py`:

```python
"""usecases.lectionary and the lectionary fetchers and loaders (S "Fetchers",
"Loaders", `usecases/lectionary.py`; AC1–AC3; clarifications 18, 19, 31, 39).

respx answers from the T1 recordings (tests/fixtures/lectio, vanderbilt), so
nothing leaves the machine (F §5.3). The autouse _fresh_lectionary_caches
fixture gives every test a new pool and empty caches. Threaded tests block on
threading primitives, never time.sleep, and release them in `finally`.
"""
import json
import logging
import re
import threading
import types
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

import usecases.lectionary as lectionary
import vanderbilt_lectionary as vl
from domain_errors import InvalidInput, UpstreamError, UpstreamTimeout
from integrations import http
from tests.conftest import FakeClock
from tests.upstream_fixtures import (
    LECTIO_URL,
    VANDERBILT_URL,
    as_response,
    load,
    route_lectio,
    route_vanderbilt,
)

PALM_SUNDAY = date(2026, 3, 29)
EASTER = date(2026, 4, 5)
GOOD_FRIDAY = date(2026, 4, 3)
TUESDAY = date(2026, 9, 29)
PROPER_22 = date(2026, 10, 4)
ADVENT_1_2026 = date(2026, 11, 29)
YEAR = "2025-26"
LECTIO_404 = "2026-09-29"          # a recorded Lectio 404, reused for dates with no recording
UNREACHABLE = ("The lectionary couldn't be reached. Enter readings yourself, "
               "or try again in a few minutes.")


@pytest.fixture
def router():
    with respx.mock(assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def clock():
    """The lectionary caches rebuilt on a FakeClock (the autouse reset joined the pool)."""
    fake = FakeClock()
    lectionary.reset_for_tests(clock=fake.now)
    return fake


def _status(code):
    return lambda request: httpx.Response(code, text="")


def _expected(d, lectio_name=None, year=YEAR):
    """The sets and default the domain functions give for `d` from the recordings.
    T6b's tests own the domain rules; these tests own the orchestration."""
    day = None
    if lectio_name is not None:
        day = vl.parse_lectio_payload(json.loads(load("lectio", lectio_name).body))
    rows = vl.parse_vanderbilt_csv(as_response(load("vanderbilt", year)).text)
    v_sets = [s for s in vl.vanderbilt_sets_on(rows, d) if vl.fits_draft_limits(s)]
    return vl.merge(day, v_sets, d)


def _result(d, status, partial, sets, default_index):
    return lectionary.LectionaryResult(date=d, status=status, partial=partial,
                                       reading_sets=sets, default_index=default_index)


# --- outcomes -----------------------------------------------------------------

def test_both_ok_merged(router):
    lectio = route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR)
    result = lectionary.readings_for_date(PALM_SUNDAY)
    sets, default_index = _expected(PALM_SUNDAY, "2026-03-29")
    assert result == _result(PALM_SUNDAY, "ok", False, sets, default_index)
    assert [s.source for s in result.reading_sets] == ["vanderbilt", "merged"]
    assert result.default_index == 1
    assert (lectio.call_count, vanderbilt.call_count) == (1, 1)


def test_lectio_404_with_vanderbilt_row_ok_not_partial(router):
    route_lectio(router, GOOD_FRIDAY)                  # recorded 404
    route_vanderbilt(router, YEAR)
    result = lectionary.readings_for_date(GOOD_FRIDAY)
    sets, default_index = _expected(GOOD_FRIDAY)
    assert result == _result(GOOD_FRIDAY, "ok", False, sets, default_index)
    assert [s.source for s in result.reading_sets] == ["vanderbilt"]
    assert result.default_index == 0


def test_both_none_no_readings(router):
    route_lectio(router, TUESDAY)                      # recorded 404
    route_vanderbilt(router, YEAR)                     # no row on 2026-09-29
    assert lectionary.readings_for_date(TUESDAY) == _result(TUESDAY, "no_readings", False, [], None)


def test_one_failed_with_sets_partial(router):
    # Vanderbilt down: the Lectio group alone, named by lectio_set_name.
    route_lectio(router, PROPER_22)
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=_status(503))
    result = lectionary.readings_for_date(PROPER_22)
    assert (result.status, result.partial, result.default_index) == ("ok", True, 0)
    assert [(s.name, s.source) for s in result.reading_sets] == [
        ("Nineteenth Sunday after Pentecost", "lectio")]
    # Lectio down: the Vanderbilt sets alone (the 2026-27 stub's Advent 1 row).
    route_lectio(router, ADVENT_1_2026, "error_500")
    route_vanderbilt(router, "2026-27")
    result = lectionary.readings_for_date(ADVENT_1_2026)
    assert (result.status, result.partial, result.default_index) == ("ok", True, 0)
    assert [s.source for s in result.reading_sets] == ["vanderbilt"]


def test_both_failed_upstream_error(router):
    route_lectio(router, PALM_SUNDAY, "error_500")
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=_status(503))
    with pytest.raises(UpstreamError) as caught:
        lectionary.readings_for_date(PALM_SUNDAY)
    assert (caught.value.code, caught.value.message) == ("upstream_error", UNREACHABLE)
    assert lectionary.LECTIONARY_UNREACHABLE == UNREACHABLE


def test_all_timeouts_upstream_timeout(router):
    router.get(LECTIO_URL).mock(side_effect=httpx.ReadTimeout)
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=httpx.ConnectTimeout)
    with pytest.raises(UpstreamTimeout) as caught:
        lectionary.readings_for_date(PALM_SUNDAY)
    assert (caught.value.code, caught.value.message) == ("upstream_timeout", UNREACHABLE)


def test_timeout_plus_none_is_timeout(router):
    router.get(LECTIO_URL).mock(side_effect=httpx.ReadTimeout)
    route_vanderbilt(router, YEAR, "404")              # a definitive none
    with pytest.raises(UpstreamTimeout):
        lectionary.readings_for_date(PALM_SUNDAY)


def test_timeout_plus_error_is_upstream_error(router):
    router.get(LECTIO_URL).mock(side_effect=httpx.ReadTimeout)
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=_status(503))
    with pytest.raises(UpstreamError) as caught:
        lectionary.readings_for_date(PALM_SUNDAY)
    assert caught.value.code == "upstream_error"


def test_all_sets_over_limits_is_no_readings(router):
    too_many = " - ".join(f"Genesis {n}:1-5" for n in range(1, 22))
    assert len(vl.clean_cell(too_many)) == 21          # one line more than the draft allows
    body = ('"Revised Common Lectionary"\n'
            '"Liturgical Date","Calendar Date","First reading","Psalm","Second reading",'
            '"Gospel","Art","Prayer"\n'
            f'"Test Day","Sep 29, 2026","{too_many}","","","","",""\n')
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(
        side_effect=lambda request: httpx.Response(
            200, text=body, headers={"Content-Type": "text/csv; charset=utf-8"}))
    route_lectio(router, TUESDAY)                      # recorded 404
    assert lectionary.readings_for_date(TUESDAY) == _result(TUESDAY, "no_readings", False, [], None)


# --- failure classification -----------------------------------------------------

def test_lectio_html_200_failed(router):
    assert load("lectio", "html_200").status == 200
    route_lectio(router, PALM_SUNDAY, "html_200")
    with pytest.raises(vl.SourceFailed) as caught:
        vl.fetch_lectio(PALM_SUNDAY)
    assert caught.value.timeout is False
    with pytest.raises(vl.SourceFailed):
        vl.load_lectio(PALM_SUNDAY)


def test_lectio_undecodable_json_failed(router):
    route = router.get(LECTIO_URL).mock(side_effect=lambda request: httpx.Response(
        200, content=b'{"data": ', headers={"Content-Type": "application/json; charset=utf-8"}))
    with pytest.raises(vl.SourceFailed) as caught:
        vl.fetch_lectio(PALM_SUNDAY)
    assert caught.value.timeout is False
    with pytest.raises(vl.SourceFailed):
        vl.load_lectio(PALM_SUNDAY)
    # A "+json" media type with parameters is still JSON (clarification 19).
    route.mock(side_effect=lambda request: httpx.Response(
        200, content=b'{"data": null}',
        headers={"Content-Type": "application/vnd.api+json; charset=utf-8"}))
    assert vl.fetch_lectio(PALM_SUNDAY) == {"data": None}
    assert vl.load_lectio(PALM_SUNDAY) is None


def test_vanderbilt_html_200_failed(router):
    assert load("vanderbilt", "html_200").status == 200
    route = route_vanderbilt(router, YEAR, "html_200")
    with pytest.raises(vl.SourceFailed) as caught:
        vl.fetch_vanderbilt_year(YEAR)
    assert caught.value.timeout is False
    # An HTML page served as text/plain passes the type check, then fails for its missing header.
    route.mock(side_effect=lambda request: httpx.Response(200, text="<html><body>Gone</body></html>"))
    assert vl.fetch_vanderbilt_year(YEAR).startswith("<html>")
    with pytest.raises(vl.SourceFailed) as caught:
        vl.load_vanderbilt_year(YEAR)
    assert isinstance(caught.value.__cause__, vl.LectionaryFormatError)


def test_vanderbilt_404_none(router):
    route_vanderbilt(router, "1999-00", "404")
    assert vl.fetch_vanderbilt_year("1999-00") is None
    assert vl.load_vanderbilt_year("1999-00") == []


# --- caching ---------------------------------------------------------------------

def test_second_call_within_24h_no_request(router, clock):
    lectio = route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR)
    first = lectionary.readings_for_date(PALM_SUNDAY)
    clock.advance(86_399)
    assert lectionary.readings_for_date(PALM_SUNDAY) == first
    assert (lectio.call_count, vanderbilt.call_count) == (1, 1)
    clock.advance(2)
    lectionary.readings_for_date(PALM_SUNDAY)
    assert (lectio.call_count, vanderbilt.call_count) == (2, 2)


def test_vanderbilt_404_cached_24h(router, clock):
    route_lectio(router, TUESDAY)
    vanderbilt = route_vanderbilt(router, YEAR, "404")
    lectionary.readings_for_date(TUESDAY)
    clock.advance(86_399)
    assert lectionary.readings_for_date(TUESDAY).status == "no_readings"
    assert vanderbilt.call_count == 1
    clock.advance(2)
    lectionary.readings_for_date(TUESDAY)
    assert vanderbilt.call_count == 2


def test_vanderbilt_html_cached_5_min(router, clock):
    route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR, "html_200")
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    clock.advance(299)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    assert vanderbilt.call_count == 1
    clock.advance(2)
    lectionary.readings_for_date(PALM_SUNDAY)
    assert vanderbilt.call_count == 2


def test_lectio_500_cached_5_min_then_retried(router, clock):
    lectio = route_lectio(router, PALM_SUNDAY, "error_500")
    route_vanderbilt(router, YEAR)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    clock.advance(299)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    assert lectio.call_count == 1
    lectio.mock(side_effect=lambda request: as_response(load("lectio", "2026-03-29")))
    clock.advance(2)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is False
    assert lectio.call_count == 2


def test_lectio_404_cached_24h(router, clock):
    lectio = route_lectio(router, GOOD_FRIDAY)         # recorded 404
    route_vanderbilt(router, YEAR)
    lectionary.readings_for_date(GOOD_FRIDAY)
    clock.advance(86_399)
    lectionary.readings_for_date(GOOD_FRIDAY)
    assert lectio.call_count == 1
    clock.advance(2)
    lectionary.readings_for_date(GOOD_FRIDAY)
    assert lectio.call_count == 2


def test_unexpected_loader_exception_not_cached(router, clock):
    lectio = router.get(LECTIO_URL).mock(side_effect=RuntimeError("bug"))
    route_vanderbilt(router, YEAR)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="bug"):
            lectionary.readings_for_date(PALM_SUNDAY)
    assert lectio.call_count == 2                      # nothing was cached between the calls


def test_two_dates_same_year_one_vanderbilt_request(router):
    palm = route_lectio(router, PALM_SUNDAY)
    easter = route_lectio(router, EASTER)
    vanderbilt = route_vanderbilt(router, YEAR)
    lectionary.readings_for_date(PALM_SUNDAY)
    lectionary.readings_for_date(EASTER)
    assert vanderbilt.call_count == 1                  # keyed by liturgical year, not by date
    assert (palm.call_count, easter.call_count) == (1, 1)


def test_advent_boundary_fetches_next_year_file(router):
    saturday, advent_1_2027 = date(2026, 11, 28), date(2027, 11, 28)
    for d in (saturday, ADVENT_1_2026, advent_1_2027):
        route_lectio(router, d, LECTIO_404)
    y2526 = route_vanderbilt(router, "2025-26")
    y2627 = route_vanderbilt(router, "2026-27")
    y2728 = route_vanderbilt(router, "2027-28")
    assert lectionary.readings_for_date(saturday).status == "no_readings"
    assert (y2526.call_count, y2627.call_count, y2728.call_count) == (1, 0, 0)
    advent_1 = lectionary.readings_for_date(ADVENT_1_2026)
    assert (advent_1.status, [s.source for s in advent_1.reading_sets]) == ("ok", ["vanderbilt"])
    assert (y2526.call_count, y2627.call_count, y2728.call_count) == (1, 1, 0)
    assert lectionary.readings_for_date(advent_1_2027).status == "ok"
    assert (y2526.call_count, y2627.call_count, y2728.call_count) == (1, 1, 1)


# --- concurrency -------------------------------------------------------------------

class _SpyCache:
    """Wraps a TTLCache; `entered` is set once `calls` lookups have begun."""

    def __init__(self, inner, calls):
        self.inner, self.calls, self.count = inner, calls, 0
        self.entered, self.lock = threading.Event(), threading.Lock()

    def get_or_load(self, key, loader):
        with self.lock:
            self.count += 1
            if self.count == self.calls:
                self.entered.set()
        return self.inner.get_or_load(key, loader)


def test_single_flight_two_threads_one_call(router, monkeypatch):
    started, release = threading.Event(), threading.Event()
    recorded = load("lectio", "2026-03-29")

    def held(request):
        started.set()
        release.wait(5)
        return as_response(recorded)

    lectio = router.get(LECTIO_URL).mock(side_effect=held)
    vanderbilt = route_vanderbilt(router, YEAR)
    spy = _SpyCache(lectionary._LECTIO, calls=2)
    monkeypatch.setattr(lectionary, "_LECTIO", spy)
    results = []
    threads = [threading.Thread(target=lambda: results.append(lectionary.readings_for_date(PALM_SUNDAY)))
               for _ in range(2)]
    try:
        threads[0].start()
        assert started.wait(5)                         # the first lookup is inside Lectio
        threads[1].start()
        assert spy.entered.wait(5)                     # the second has reached the cache
    finally:
        release.set()
        for t in threads:
            if t.ident is not None:
                t.join(10)
    assert len(results) == 2 and results[0] == results[1]
    assert (lectio.call_count, vanderbilt.call_count) == (1, 1)


def test_sources_requested_concurrently(router):
    both_in_flight = threading.Barrier(2, timeout=5)   # breaks if the sources run one after the other

    def meet(recorded):
        def side_effect(request):
            both_in_flight.wait()
            return as_response(recorded)
        return side_effect

    router.get(LECTIO_URL).mock(side_effect=meet(load("lectio", "2026-03-29")))
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=meet(load("vanderbilt", YEAR)))
    result = lectionary.readings_for_date(PALM_SUNDAY)
    assert (result.status, result.partial) == ("ok", False)


def test_source_unfinished_at_deadline_is_timeout(router, monkeypatch):
    release = threading.Event()

    def held(request):
        release.wait(10)
        return httpx.Response(404, json={"error": "not found"})

    router.get(LECTIO_URL).mock(side_effect=held)
    route_vanderbilt(router, YEAR)
    router.get(VANDERBILT_URL.format(year="2026-27")).mock(side_effect=held)
    # Warm the 2025-26 file under the real deadline, so only Lectio is slow below.
    lectionary._VANDERBILT.get_or_load(YEAR, lambda: vl.load_vanderbilt_year(YEAR))
    monkeypatch.setattr(lectionary, "DEADLINE_SECONDS", 0.5)   # margin for a cold pool on a busy CI runner
    try:
        partial = lectionary.readings_for_date(GOOD_FRIDAY)
        assert (partial.status, partial.partial) == ("ok", True)
        assert [s.source for s in partial.reading_sets] == ["vanderbilt"]
        with pytest.raises(UpstreamTimeout) as caught:
            lectionary.readings_for_date(ADVENT_1_2026)   # both sources held
        assert caught.value.code == "upstream_timeout"
    finally:
        release.set()
        lectionary.reset_for_tests()                   # join the held workers while respx answers


# --- other ---------------------------------------------------------------------------

def test_year_out_of_range_invalid_input(router):
    for d in (date(1899, 12, 31), date(2200, 1, 1)):
        with pytest.raises(InvalidInput) as caught:
            lectionary.readings_for_date(d)
        assert (caught.value.code, caught.value.field, caught.value.message) == (
            "invalid_request", "date", "Enter a date between 1900 and 2199.")
    assert router.calls.call_count == 0
    router.get(LECTIO_URL).respond(404)
    router.get(url__startswith="https://lectionary.library.vanderbilt.edu/").respond(404)
    for d in (date(1900, 1, 1), date(2199, 12, 31)):
        assert lectionary.readings_for_date(d).status == "no_readings"


def test_fetch_urls_params_and_read_timeouts(router, monkeypatch):
    lectio = route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR)
    seen = []
    real_get = http.get

    def spy(url, **kwargs):
        seen.append((url, kwargs.get("params"), kwargs["read_timeout"]))
        return real_get(url, **kwargs)

    monkeypatch.setattr(http, "get", spy)
    lectionary.readings_for_date(PALM_SUNDAY)
    assert {url: (params, read) for url, params, read in seen} == {
        "https://lectio-api.org/api/v1/readings": ({"date": "2026-03-29", "tradition": "rcl"}, 10.0),
        "https://lectionary.library.vanderbilt.edu/calendar/2025-26/?season=all&download=csv": (None, 15.0),
    }
    assert (vl.LECTIO_READ_TIMEOUT, vl.VANDERBILT_READ_TIMEOUT) == (10.0, 15.0)
    sent = lectio.calls.last.request
    assert (sent.url.scheme, sent.url.host, sent.url.path) == ("https", "lectio-api.org", "/api/v1/readings")
    assert dict(sent.url.params) == {"date": "2026-03-29", "tradition": "rcl"}
    assert sent.headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    got = vanderbilt.calls.last.request
    assert (got.url.path, dict(got.url.params)) == ("/calendar/2025-26/", {"season": "all", "download": "csv"})


def test_old_names_and_dict_cache_gone():
    # AC3 as a test: the old lookups and the module-level dict cache are gone.
    for name in ("_cache", "fetch_lectionary_year", "get_readings_for_date",
                 "_normalize_date_for_match", "_liturgical_year_for_date",
                 "_liturgical_sunday_name", "get_readings_for_date_string",
                 "_get_readings_from_lectio", "_row_to_reading", "_ordinal_sunday_label",
                 "_easter_date"):
        assert not hasattr(vl, name), name
    module_state = {n: v for n, v in vars(vl).items() if not n.startswith("__")}
    assert not [n for n, v in module_state.items() if isinstance(v, (dict, list, set)) and not v]
    assert not [n for n, v in module_state.items()           # a cache is data, not a class
                if "cache" in n.lower() and not callable(v) and not isinstance(v, types.ModuleType)]
    source = Path(vl.__file__).read_text()
    assert "httpx.get(" not in source and "TTLCache" not in source


def test_log_line_outcomes_no_payload(router, caplog):
    route_lectio(router, PALM_SUNDAY, "error_500")
    route_vanderbilt(router, YEAR)
    route_lectio(router, TUESDAY)                      # recorded 404
    caplog.set_level(logging.INFO, logger="usecases.lectionary")

    def lines():
        found = [r.getMessage() for r in caplog.records if r.name == "usecases.lectionary"]
        caplog.clear()
        return found

    result = lectionary.readings_for_date(PALM_SUNDAY)
    (first,) = lines()
    assert first.startswith(
        "lectionary_lookup date=2026-03-29 lectio=failed vanderbilt=ok lectio_cached=False "
        f"vanderbilt_cached=False sets={len(result.reading_sets)} duration_ms=")
    assert re.fullmatch(r".* duration_ms=\d+", first)
    lectionary.readings_for_date(PALM_SUNDAY)
    (again,) = lines()
    assert " lectio=failed vanderbilt=ok lectio_cached=True vanderbilt_cached=True " in again
    lectionary.readings_for_date(TUESDAY)
    (none,) = lines()
    assert " lectio=none vanderbilt=none lectio_cached=False vanderbilt_cached=True sets=0 " in none
    for line in (first, again, none):                  # never a payload, a URL or a query string
        assert "http" not in line and "tradition" not in line
        for s in result.reading_sets:
            for ref in s.scriptures:
                assert ref not in line
```

- [ ] **Step 4 (agent): Run the new tests and watch them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_lectionary.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_usecase_lectionary.py 2>&1 | grep -m1 "ModuleNotFoundError"
```

**Expected:** FAIL at collection, because the usecase module does not exist yet:
```
ERROR backend/tests/test_usecase_lectionary.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in …s
```
and the grep prints `E   ModuleNotFoundError: No module named 'usecases.lectionary'`.

- [ ] **Step 5 (agent): Add the fetchers and loaders to `backend/vanderbilt_lectionary.py`**

First, the two imports, in the same first-party group as T6b's `scripture_refs` import. Replace the one line (T6b Step 4 added it)

```python
from scripture_refs import scripture_key, split_alternatives, split_book
```

with

```python
from cache import CacheableFailure
from integrations import http
from scripture_refs import scripture_key, split_alternatives, split_book
```

Then append this block to the **end** of the file, after two blank lines and after all of T6a's and T6b's code (the annotations name `VRow` and `LectioDay`, and the loaders call `parse_vanderbilt_csv` and `parse_lectio_payload`, so they must already be defined above). It uses the file's existing `httpx`, `date` and `Optional` imports.

```python
# --- Fetchers and loaders (S "Fetchers", "Loaders"; slice 2a T7) -------------
# One outbound client (integrations.http). Only httpx.HTTPError and a JSON
# ValueError are caught (clarification 18): anything else, such as the test
# suite's no-network RuntimeError, is a bug and surfaces as one.

LECTIO_READ_TIMEOUT = 10.0
VANDERBILT_READ_TIMEOUT = 15.0

# Media types are compared without their parameters ("; charset=utf-8").
# Lectio: application/json or any "+json" type. Vanderbilt: S's two types
# (clarification 19); T1's recorded sidecar is the evidence.
VANDERBILT_MEDIA_TYPES = frozenset({"text/plain", "text/csv"})


class SourceFailed(CacheableFailure):
    """An expected lectionary source failure: a network error, a timeout, a
    403/5xx/429, a wrong content type, undecodable JSON or a CSV with no
    header. The usecase's caches keep it for 5 minutes (S "Loaders").

    `timeout` is True only for an httpx timeout (or the usecase's source
    deadline), so an all-timeout lookup is a 504 rather than a 502."""

    def __init__(self, *, timeout: bool):
        super().__init__("lectionary source timed out" if timeout else "lectionary source failed")
        self.timeout = timeout


def _media_type(response: httpx.Response) -> str:
    """The response's media type, lower-cased, without parameters ("" if absent)."""
    return response.headers.get("content-type", "").split(";", 1)[0].strip().lower()


def _get(url: str, *, params: Optional[dict[str, str]], read_timeout: float) -> httpx.Response:
    try:
        return http.get(url, params=params, read_timeout=read_timeout)
    except httpx.HTTPError as e:     # includes the https-only hook's UnsupportedProtocol
        raise SourceFailed(timeout=isinstance(e, httpx.TimeoutException)) from e


def fetch_lectio(d: date) -> Optional[dict]:
    """GET Lectio for exactly `d`. 404 → None (a definitive none); a 200 JSON
    object → the payload; anything else → SourceFailed (S "Fetchers")."""
    response = _get(
        LECTIO_API_URL,
        params={"date": d.isoformat(), "tradition": "rcl"},
        read_timeout=LECTIO_READ_TIMEOUT,
    )
    if response.status_code == 404:
        return None
    media = _media_type(response)
    if response.status_code != 200 or not (media == "application/json" or media.endswith("+json")):
        raise SourceFailed(timeout=False)
    try:
        payload = response.json()
    except ValueError as e:          # JSONDecodeError and UnicodeDecodeError are ValueErrors
        raise SourceFailed(timeout=False) from e
    if not isinstance(payload, dict):
        raise SourceFailed(timeout=False)
    return payload


def fetch_vanderbilt_year(year: str) -> Optional[str]:
    """GET one liturgical-year CSV ("2025-26"). 404 → None; a 200 text/plain or
    text/csv → the text; anything else (an HTML 200 included) → SourceFailed."""
    response = _get(
        VANDERBILT_YEAR_URL.format(year=year),
        params=None,
        read_timeout=VANDERBILT_READ_TIMEOUT,
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200 or _media_type(response) not in VANDERBILT_MEDIA_TYPES:
        raise SourceFailed(timeout=False)
    return response.text


def load_vanderbilt_year(year: str) -> list[VRow]:
    """What the Vanderbilt cache stores: rows (24 h), [] for a 404 (24 h), or a
    SourceFailed (5 min). An exception that escapes is a bug: not cached."""
    text = fetch_vanderbilt_year(year)                        # raises SourceFailed
    if text is None:                                          # 404: definitive none
        return []
    try:
        return parse_vanderbilt_csv(text)
    except LectionaryFormatError as e:                        # e.g. HTML served as 200
        raise SourceFailed(timeout=False) from e


def load_lectio(d: date) -> Optional[LectioDay]:
    """What the Lectio cache stores: a LectioDay or None (24 h), or a
    SourceFailed (5 min). An exception that escapes is a bug: not cached."""
    payload = fetch_lectio(d)                                 # raises SourceFailed
    if payload is None:                                       # 404: definitive none
        return None
    try:
        return parse_lectio_payload(payload)                  # None when data/readings are empty
    except (KeyError, TypeError, ValueError) as e:            # unexpected JSON shape
        raise SourceFailed(timeout=False) from e
```

If Step 1 found another Vanderbilt media type, the constant becomes, for example, `VANDERBILT_MEDIA_TYPES = frozenset({"text/plain", "text/csv", "application/csv"})`, and the comment above it names the recording.

- [ ] **Step 6 (agent): Create `backend/usecases/lectionary.py`**

```python
"""Readings for one date from the two lectionary sources (S `usecases/lectionary.py`).

Lectio (keyed by the date) and Vanderbilt (keyed by the liturgical-year file)
load in parallel on one module-level pool, each through its own TTLCache: a
success, including a definitive 404, is kept 24 h; a SourceFailed 5 min;
anything else is a bug and is not kept (cache.py). Both sources share one
20 s deadline (clarification 31). Any date is looked up as itself: no
normalization and no nearest row (spec decision 8). No database access.
"""
from __future__ import annotations

import dataclasses
import logging
import time
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import date
from typing import Callable, Literal, Optional, TypeVar

from cache import TTLCache
from domain_errors import InvalidInput, UpstreamError, UpstreamTimeout
from vanderbilt_lectionary import (
    LectioDay,
    ReadingSet,
    SourceFailed,
    VRow,
    fits_draft_limits,
    liturgical_year_for,
    load_lectio,
    load_vanderbilt_year,
    merge,
    vanderbilt_sets_on,
)

logger = logging.getLogger(__name__)

LECTIONARY_UNREACHABLE = (
    "The lectionary couldn't be reached. Enter readings yourself, "
    "or try again in a few minutes."
)
DATE_OUT_OF_RANGE = "Enter a date between 1900 and 2199."
MIN_YEAR = 1900
MAX_YEAR = 2199

DEADLINE_SECONDS = 20.0       # read at call time, so tests can monkeypatch it
OK_TTL_SECONDS = 86_400.0     # 24 h
FAIL_TTL_SECONDS = 300.0      # 5 min
MAX_WORKERS = 4

T = TypeVar("T")


def _new_pool() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="lectionary")


def _new_lectio_cache(clock: Callable[[], float]) -> TTLCache[date, Optional[LectioDay]]:
    return TTLCache(maxsize=512, ttl_ok=OK_TTL_SECONDS, ttl_fail=FAIL_TTL_SECONDS, clock=clock)


def _new_vanderbilt_cache(clock: Callable[[], float]) -> TTLCache[str, list[VRow]]:
    return TTLCache(maxsize=8, ttl_ok=OK_TTL_SECONDS, ttl_fail=FAIL_TTL_SECONDS, clock=clock)


_POOL = _new_pool()
_LECTIO = _new_lectio_cache(time.monotonic)
_VANDERBILT = _new_vanderbilt_cache(time.monotonic)


@dataclass(frozen=True)
class LectionaryResult:
    date: date                                   # the requested date, never normalized
    status: Literal["ok", "no_readings"]
    partial: bool                                # sets found, but one source failed
    reading_sets: list[ReadingSet]               # [] when status == "no_readings"
    default_index: Optional[int]                 # None iff reading_sets == []


@dataclass(frozen=True)
class _Outcome:
    value: object                                # what the cache returned; None on failure
    failure: Optional[SourceFailed]
    cached: bool                                 # True when this request ran no loader


def _load(cache: TTLCache, key: object, loader: Callable[[], T]) -> _Outcome:
    """Run in a pool worker. Only SourceFailed becomes an outcome; any other
    exception is re-raised by Future.result() in the request thread (a 500)."""
    ran = False

    def run() -> T:
        nonlocal ran
        ran = True
        return loader()

    try:
        value = cache.get_or_load(key, run)
    except SourceFailed as e:
        return _Outcome(value=None, failure=e, cached=not ran)
    return _Outcome(value=value, failure=None, cached=not ran)


def _outcome(future: Future) -> _Outcome:
    """The source's outcome, or a timeout failure for this request only when
    the source is unfinished at the deadline. The running loader carries on
    and caches its own outcome (clarification 31)."""
    if future.done():
        return future.result()
    return _Outcome(value=None, failure=SourceFailed(timeout=True), cached=False)


def readings_for_date(d: date) -> LectionaryResult:
    """The reading sets for exactly `d` (S Status rules).

    Raises InvalidInput for a year outside 1900–2199, UpstreamTimeout when no
    set was found and every failed source timed out, and UpstreamError when
    no set was found and a source failed otherwise."""
    if not MIN_YEAR <= d.year <= MAX_YEAR:
        raise InvalidInput(DATE_OUT_OF_RANGE, field="date")
    started = time.monotonic()
    year = liturgical_year_for(d)
    lectio_future = _POOL.submit(_load, _LECTIO, d, lambda: load_lectio(d))
    vanderbilt_future = _POOL.submit(_load, _VANDERBILT, year, lambda: load_vanderbilt_year(year))
    wait((lectio_future, vanderbilt_future), timeout=DEADLINE_SECONDS)
    lectio = _outcome(lectio_future)
    vanderbilt = _outcome(vanderbilt_future)

    day: Optional[LectioDay] = lectio.value  # type: ignore[assignment]
    groups = tuple(g for g in day.groups if fits_draft_limits(g)) if day is not None else ()
    fitting_day = dataclasses.replace(day, groups=groups) if groups else None
    on_date = vanderbilt_sets_on(vanderbilt.value or [], d)  # type: ignore[arg-type]
    v_sets = [s for s in on_date if fits_draft_limits(s)]
    sets, default_index = merge(fitting_day, v_sets, d)
    failures = [o.failure for o in (lectio, vanderbilt) if o.failure is not None]

    logger.info(
        "lectionary_lookup date=%s lectio=%s vanderbilt=%s lectio_cached=%s "
        "vanderbilt_cached=%s sets=%d duration_ms=%d",
        d.isoformat(),
        "failed" if lectio.failure else ("ok" if day is not None else "none"),
        "failed" if vanderbilt.failure else ("ok" if on_date else "none"),
        lectio.cached,
        vanderbilt.cached,
        len(sets),
        round((time.monotonic() - started) * 1000),
    )

    if sets:
        return LectionaryResult(d, "ok", bool(failures), sets, default_index)
    if failures:
        if all(f.timeout for f in failures):
            raise UpstreamTimeout(LECTIONARY_UNREACHABLE, code="upstream_timeout")
        raise UpstreamError(LECTIONARY_UNREACHABLE, code="upstream_error")
    return LectionaryResult(d, "no_readings", False, [], None)


def reset_for_tests(clock: Callable[[], float] = time.monotonic) -> None:
    """Join the pool, then start over with a new pool and new, empty caches on
    `clock` (clarification 39). Queued work is cancelled; a running worker is
    waited for, so no straggler from an earlier test holds a worker or writes
    into this test's caches."""
    global _POOL, _LECTIO, _VANDERBILT
    _POOL.shutdown(wait=True, cancel_futures=True)
    _POOL = _new_pool()
    _LECTIO = _new_lectio_cache(clock)
    _VANDERBILT = _new_vanderbilt_cache(clock)
```

- [ ] **Step 7 (agent): Reset the pool and caches before each test**

In `backend/tests/conftest.py`, insert the fixture directly above the existing line
`# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---`
(that line stays; the fixtures T2 and T3 added above it stay too). Replace

```python
# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
```

with

```python
@pytest.fixture(autouse=True)
def _fresh_lectionary_caches():
    """usecases.lectionary keeps two process-wide TTL caches and a thread pool
    (slice 2a). Each test starts with the pool joined and a new pool and new,
    empty caches, so no cached reading and no straggling worker crosses tests
    (clarification 39). A test that blocks a worker releases it and calls
    reset_for_tests() itself in `finally`, while its respx mock still answers.

    Resets only when usecases.lectionary is already imported (the
    deferred-import rule at the top of this file)."""
    import sys

    lectionary = sys.modules.get("usecases.lectionary")
    if lectionary is not None:
        lectionary.reset_for_tests()
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
```

- [ ] **Step 8 (agent): Run the tests: only the deletion check fails**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_lectionary.py 2>&1 | tail -3
```

**Expected:** FAIL, because the old code is still there:
```
=========================== short test summary info ============================
FAILED backend/tests/test_usecase_lectionary.py::test_old_names_and_dict_cache_gone - AssertionError: _cache
1 failed, 27 passed in …s
```

If anything else fails, fix it before deleting code: a failure here is in the new code (or in how a T1 recording differs from S; see Step 1), not in the deletion.

- [ ] **Step 9 (agent): Delete the old lookup, its dict cache and its helpers**

Write the script to the scratchpad (it is not committed) and run it from the repo root:

```bash
mkdir -p "${TMPDIR:-/tmp}/slice2a" && cat > "${TMPDIR:-/tmp}/slice2a/drop_old_lectionary.py" <<'PYEOF'
import ast
import pathlib
import sys

PATH = pathlib.Path("backend/vanderbilt_lectionary.py")
OLD = {
    "_cache", "fetch_lectionary_year", "get_readings_for_date", "_normalize_date_for_match",
    "_liturgical_year_for_date", "_liturgical_sunday_name", "get_readings_for_date_string",
    "_get_readings_from_lectio", "_row_to_reading", "_ordinal_sunday_label", "_easter_date",
}
IF_UNUSED = {"_parse_csv_date"}
DOCSTRING = '''"""
Revised Common Lectionary readings for one date (slice 2).

Two sources, looked up for exactly the date asked: Lectio (lectio-api.org, by
date) and the Vanderbilt Divinity Library liturgical-year CSV. This module is
pure parsing, naming and merging plus the two fetchers and loaders; caching,
the parallel lookup and the status rules live in usecases/lectionary.py.
"""
'''


def bound_names(node):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, ast.Assign):
        return {t.id for t in node.targets if isinstance(t, ast.Name)}
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return {node.target.id}
    return set()


def used_names(tree, skip):
    """Every Name read anywhere except inside the top-level nodes in `skip`."""
    seen = set()
    for node in tree.body:
        if node in skip:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name):
                seen.add(sub.id)
    return seen


def drop(lines, nodes):
    for node in sorted(nodes, key=lambda n: n.lineno, reverse=True):
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]) - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#") and not lines[start - 1].startswith("#!"):
            start -= 1                                   # the comment block directly above
        del lines[start:node.end_lineno]


src = PATH.read_text()
tree = ast.parse(src)
old_nodes = [n for n in tree.body if bound_names(n) & OLD]
missing = OLD - set().union(*(bound_names(n) for n in old_nodes))
if missing:
    sys.exit(f"not found (already deleted?): {sorted(missing)}")
still_used = used_names(tree, set(old_nodes)) & OLD
if still_used:
    sys.exit(f"still referenced by the new code, stop: {sorted(still_used)}")
lines = src.splitlines(keepends=True)
drop(lines, old_nodes)

tree = ast.parse("".join(lines))
optional = [n for n in tree.body if bound_names(n) & IF_UNUSED]
unused = [n for n in optional if not (bound_names(n) & used_names(tree, set(optional)))]
drop(lines, unused)
kept = sorted(IF_UNUSED - set().union(set(), *(bound_names(n) for n in unused)))

tree = ast.parse("".join(lines))
names = used_names(tree, set()) | {a.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) for a in [n.value] if isinstance(a, ast.Name)}
for node in sorted([n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))], key=lambda n: n.lineno, reverse=True):
    if node.lineno != node.end_lineno or (isinstance(node, ast.ImportFrom) and node.module == "__future__"):
        continue
    keep = [a for a in node.names if (a.asname or a.name).split(".")[0] in names]
    if len(keep) == len(node.names):
        continue
    text = ", ".join(a.name + (f" as {a.asname}" if a.asname else "") for a in keep)
    new = (f"from {node.module} import {text}\n" if isinstance(node, ast.ImportFrom) else f"import {text}\n")
    lines[node.lineno - 1:node.end_lineno] = [new] if keep else []

doc = tree.body[0]
if isinstance(doc, ast.Expr) and isinstance(doc.value, ast.Constant) and isinstance(doc.value.value, str):
    lines[doc.lineno - 1:doc.end_lineno] = [DOCSTRING]

out = "".join(lines)
while "\n\n\n\n" in out:
    out = out.replace("\n\n\n\n", "\n\n\n")
STALE = {  # T6a's and T6b's section comments name the code this script just deleted
    "# Lectio's season string. The code above is the Streamlit-era path; Task 7 deletes it\n"
    "# (including the private `_easter_date`, which `easter_date` below replaces).\n":
        "# Lectio's season string.\n",
    "# Pure: no I/O. Task 7 adds the fetchers and loaders and deletes the old code.\n":
        "# Pure: no I/O. The fetchers and loaders follow at the end of the file.\n",
}
for old_comment, new_comment in STALE.items():
    if out.count(old_comment) != 1:
        sys.exit(f"stale comment not found exactly once, stop: {old_comment!r}")
    out = out.replace(old_comment, new_comment)
PATH.write_text(out)
print("removed:", sorted(OLD | (IF_UNUSED - set(kept))))
print("kept (still used by the new code):", kept)
PYEOF
.venv/bin/python "${TMPDIR:-/tmp}/slice2a/drop_old_lectionary.py"
```

**Expected output** (the second line depends on T6b):
```
removed: ['_cache', '_easter_date', '_get_readings_from_lectio', '_liturgical_sunday_name', '_liturgical_year_for_date', '_normalize_date_for_match', '_ordinal_sunday_label', '_parse_csv_date', '_row_to_reading', 'fetch_lectionary_year', 'get_readings_for_date', 'get_readings_for_date_string']
kept (still used by the new code): []
```
or, when T6b's `parse_vanderbilt_csv` calls `_parse_csv_date`, `_parse_csv_date` is missing from `removed` and the second line is `kept (still used by the new code): ['_parse_csv_date']`. Both are correct.

The script changes nothing and exits 1 in three cases:
- `not found (already deleted?): [...]`: a name was removed or renamed earlier. Check `git diff backend/vanderbilt_lectionary.py`; if T6a renamed `_easter_date` to `easter_date` in place, remove `"_easter_date"` from `OLD` and rerun.
- `still referenced by the new code, stop: [...]`: T6a/T6b code calls an old helper. The one expected case is T6a's `easter_date` delegating to `_easter_date` (for example `easter_date = _easter_date`, or `return _easter_date(year)`). Fix it by hand: rename `def _easter_date(year: int) -> date:` to `def easter_date(year: int) -> date:` with its docstring `"""Easter Sunday for `year` (Anonymous Gregorian algorithm)."""`, delete T6a's delegating `easter_date`, and rerun. Any other name: stop and report.
- `stale comment not found exactly once, stop: ...`: T6a's or T6b's section comment is not the text their parts give. Stop and report.

Then look at the new head of the file:

```bash
sed -n 1,25p backend/vanderbilt_lectionary.py
```

**Expected:** the shebang, the new docstring (`Revised Common Lectionary readings for one date (slice 2).` …), the remaining imports (`csv`, `logging`, `from datetime import …` without any name the old code alone used, `from typing import Optional` plus whatever T6a/T6b use, `httpx`, and any imports T6a/T6b added), then one first-party group of three lines (`from cache import CacheableFailure`, `from integrations import http`, `from scripture_refs import scripture_key, split_alternatives, split_book`), `logger = …`, `LECTIO_API_URL = …`, and `VANDERBILT_YEAR_URL = …` with its comment. No `_cache`.

- [ ] **Step 10 (agent): Run the tests: all pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_lectionary.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | tail -1
```

**Expected:** `28 passed in …s`, and T6a/T6b's domain file still passes (`28 passed in …s`: T6a's 10 plus T6b's 18).

- [ ] **Step 11 (agent): The usecase and the domain module import no FastAPI or Streamlit**

In `backend/tests/test_no_streamlit_in_core.py`, the subprocess import string in `test_usecases_package_imports_no_fastapi_or_streamlit` is the only place the text `usecases.onboarding, ` (with the comma and space) occurs; the comment above it reads `usecases.onboarding),`. Check, then replace that one occurrence:

```bash
grep -c "usecases.onboarding, " backend/tests/test_no_streamlit_in_core.py
```

**Expected:** `1`. Replace the text

```
usecases.onboarding, 
```

with

```
usecases.onboarding, usecases.lectionary, vanderbilt_lectionary, 
```

leaving everything else on that line (the modules T2, T3 and T5 added, and `domain_errors, db.ids, timezones; `) unchanged.

```bash
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected:** `3 passed in …s` (the same three tests; the count does not change).

- [ ] **Step 12 (agent): The AC3 grep gate and the whole suite**

```bash
grep -nE "httpx\.get|^_cache|TTLCache|get_readings_for_date|fetch_lectionary_year" backend/vanderbilt_lectionary.py; echo "exit=$?"
grep -rnE "get_readings_for_date|fetch_lectionary_year|_liturgical_sunday_name|_normalize_date_for_match" backend --include='*.py' --exclude-dir=tests; echo "exit=$?"
grep -n "get_readings_for_date_string" app.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- The first two greps print nothing and then `exit=1` (no raw `httpx.get`, no dict cache, no old lookup anywhere in `backend/` outside the tests' gone-list).
- The third prints `28:from vanderbilt_lectionary import get_readings_for_date_string` and `442:                readings_list = get_readings_for_date_string(service_date_str)`: the frozen `app.py`, left untouched (owner decision 2; clarification 23).
- The suite line is `912 passed, 9 skipped in …s` (884 + 28). The frontend is untouched (221 in 34 files).

- [ ] **Step 13 (agent): Commit**

```bash
git add backend/vanderbilt_lectionary.py backend/usecases/lectionary.py \
        backend/tests/test_usecase_lectionary.py backend/tests/upstream_fixtures.py \
        backend/tests/conftest.py backend/tests/test_no_streamlit_in_core.py
git commit -m "Lectionary: fetchers, loaders and readings_for_date; the old lookup is deleted (S Fetchers, Loaders, usecases/lectionary.py; AC1-AC3)

vanderbilt_lectionary gains SourceFailed, fetch_lectio, fetch_vanderbilt_year,
load_lectio and load_vanderbilt_year on the one outbound client. Only
httpx.HTTPError and a JSON ValueError become SourceFailed; media types are
compared without parameters (clarifications 18, 19).
usecases.lectionary.readings_for_date looks up exactly the date asked: both
sources in parallel on a 4-worker pool, each through a TTLCache (24 h ok,
5 min SourceFailed, bugs never cached), a 20 s source deadline, the S status
rules (ok / no_readings / 502 / 504) and one lectionary_lookup log line with
no payload (clarifications 14, 31). An autouse fixture joins the pool and
rebuilds the caches before each test (clarification 39).
Deleted: the module-level dict cache, fetch_lectionary_year,
get_readings_for_date and its nearest-previous-row fallback, the Sunday
normalization, the season-based Sunday names and get_readings_for_date_string.
The frozen app.py on main no longer imports; production Streamlit runs from
streamlit-frozen (owner decision 2; clarification 23).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> Lectionary: fetchers, loaders and readings_for_date; the old lookup is deleted (S Fetchers, Loaders, usecases/lectionary.py; AC1-AC3)`; `git status --short` then lists only `?? .claude/`.
### Task 8: `GET /lectionary/readings` (S API row 1, Schemas, Status rules; AC1, AC2, AC7, AC9; clarifications 3, 4, 6, 38, 41)

This task puts Task 7's usecase on the API. It adds three things to `backend/api/schemas.py`: the strict `IsoDate` query type, `ReadingSetOut` and `LectionaryOut`. It also adds a thin route module, `backend/api/routes/lectionary.py`, and mounts that router. The route is user-scoped: it depends on `get_current_user` through `rate_limit("lectionary")`, never on `require_church`, so `X-Church-Id` is ignored. It is a plain `def`, because the usecase blocks on upstream HTTP. It has no try/except: the slice 1 `DomainError` handler renders `InvalidInput`, `UpstreamError`, `UpstreamTimeout` and `RateLimited`. The route's `error_responses` are 401, 422, 429, 502, 503 and 504 (clarification 4). The OpenAPI snapshot and `schema.d.ts` are regenerated in the same commit.

**How the tests reach the upstreams.** `test_api_lectionary.py` runs the real stack: route → Task 7's usecase and caches → Task 6b's parsing and merge → `integrations.http`. Only the transport is fake. Each test installs an `httpx.MockTransport` with `integrations.http.set_http_for_tests` (Task 2). The Palm Sunday and Ascension tests serve Task 1's recorded fixtures, and the other tests build their responses inline. The autouse fixtures `_fresh_http_client` (Task 2), `_fresh_rate_limits` (Task 3) and `_fresh_lectionary_caches` (Task 7) restore the real client, full buckets and new caches before every test.

**Decisions recorded in this task (code wins over the outline; owner decision 1):**
- **T8-1. The fakes are a MockTransport, not respx.** The outline names no respx helper for this task, and Task 7's helpers in `tests/upstream_fixtures.py` are not a fixed interface. `set_http_for_tests` is Task 2's fixed interface and needs nothing else. F §5 prefers injection over mocking.
- **T8-2. `_ISO_DATE` is `[0-9]{4}-[0-9]{2}-[0-9]{2}`, not `\d{4}-\d{2}-\d{2}`.** In a Python `str` pattern, `\d` also matches non-ASCII digits such as "２０２６". That input would still fail later in Pydantic's parsing, so the user sees no difference. The class just says exactly what the parameter accepts. This was verified in `.venv` (FastAPI 0.141.1, Pydantic 2.13.5):
  - The OpenAPI parameter stays `{"type": "string", "format": "date"}`.
  - "0", "2026-03-29T00:00:00", "2026-3-29", "2026-03-29 ", "20260329" and "２０２６-03-29" give `value_error`.
  - "2026-02-30" gives `date_from_datetime_parsing`, and "0000-01-01" gives `date_parsing`. Every one of these maps to "Not a valid value." (`api/errors.py:114-120`).
  - A missing `date` gives `missing`, which maps to "Required.".
  - "0001-01-01" parses, and the usecase answers it with the range message.
- **T8-3. The dependency runs before query validation (clarification 38; verified).** The same probe counted the dependency's calls: all 11 requests ran it, including every 422. `test_bad_date_422_fields_date` proves the spend through the limiter. After five 422s, exactly 115 of 120 tokens are left.
- **T8-4. "A weekday" in `test_date_echoed_never_normalized` is Ascension Thursday 2026-05-14, from the recorded fixtures.** The test asserts three things: the response `date` equals the request; the Lectio request carried `date=2026-05-14`, not the Sunday before (2026-05-10); and no set is named for a Sunday. That third check is the S Behavior-changes row 3 bug: a weekday such as Ascension was labelled "Sixth Sunday of Easter".
- **T8-5. The `X-Church-Id` test sends the id of a real church the caller does not belong to** (`make_church`). A random id would pass too, but a real church is the stronger check: `require_church` would answer it with 403. The test also checks with `/me` that the caller has zero churches.
- **T8-6. `test_no_streamlit_in_core.py` is not edited.** Its `_EVERY_ROUTER` check (`unmounted: []`) already fails if `api/routes/lectionary.py` exists but is not mounted.

**Files:**
- Create: `backend/api/routes/lectionary.py`
- Modify: `backend/api/schemas.py:1-6` (the import block) and append after the last line (`:89`, `    message: str`, the end of `InviteAcceptOut`).
- Modify: `backend/api/main.py:12` (the routes import) and `:61` (mount after `invites`).
- Modify: `backend/tests/test_route_guards.py:17-18` (docstring) and `:41-42` (`USER_SCOPED`).
- Modify: `backend/tests/test_api_app.py:277-278` (the `test_routes_document_the_error_body` map).
- Modify (regenerated): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`.
- Test: `backend/tests/test_api_lectionary.py` (new, 9 tests).

**Interfaces:**
- Consumes:
  - Task 7:
    - `usecases.lectionary.readings_for_date(d: date) -> LectionaryResult`. The result has `.date: date`, `.status: Literal["ok", "no_readings"]`, `.partial: bool`, `.reading_sets: list[ReadingSet]` and `.default_index: int | None`.
    - It raises `InvalidInput("Enter a date between 1900 and 2199.", field="date")`, `UpstreamError(LECTIONARY_UNREACHABLE, code="upstream_error")` and `UpstreamTimeout(LECTIONARY_UNREACHABLE, code="upstream_timeout")`.
    - The autouse `_fresh_lectionary_caches`.
    - The upstream URLs are kept from the code (`vanderbilt_lectionary.py:16,19`): Lectio is `https://lectio-api.org/api/v1/readings` with the params `date` and `tradition=rcl`, and Vanderbilt is `https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv`.
    - A 404 from either source is a definitive none (S Fetchers). A 5xx is `SourceFailed(timeout=False)`. An `httpx.TimeoutException` is `SourceFailed(timeout=True)`.
  - Task 6b: `vanderbilt_lectionary.ReadingSet`, with `.name: str`, `.scriptures: tuple[str, ...]` and `.source: Literal["lectio", "vanderbilt", "merged"]`.
  - Task 3:
    - `api.ratelimit.rate_limit(name: str) -> Callable[..., None]`. The `lectionary` bucket allows 120 per 300 s per user and depends on `get_current_user` only.
    - `api.ratelimit.consume(bucket: str, *, user_id: uuid.UUID, church_id: uuid.UUID | None = None, cost: int = 1) -> None`.
    - The conftest `limiter_clock` fixture (a `FakeClock`) and the autouse `_fresh_rate_limits`.
  - Task 2: `integrations.http.set_http_for_tests(client: httpx.Client | None) -> None`, and the autouse `_fresh_http_client`.
  - Task 1: `tests.upstream_fixtures.load(kind: str, name: str) -> Recorded`, which returns `.status: int`, `.content_type: str` and `.body: bytes`.
    - `name` is the fixture file's stem, as the outline's fixture list names the files.
    - This task calls `load("lectio", "2026-03-29")`, `load("lectio", "2026-05-14")` and `load("vanderbilt", "2025-26")`.
  - Slice 1:
    - From `tests.api_helpers`: `auth_headers(email)` and `make_api_client()`.
    - The conftest fixtures `tmp_db` and `make_church`.
    - `api.errors.error_responses(*statuses)`, `domain_errors.RateLimited` and `api.settings.get_settings` (lru-cached; `CORS_ORIGINS`).
    - The response header `X-Request-Id` (`RequestIdMiddleware`).
- Produces:
  - `api.schemas`:
    - `IsoDate = Annotated[DateType, BeforeValidator(_iso_date_only)]`, where `_iso_date_only(value: object) -> object` passes only a `str` that fully matches `[0-9]{4}-[0-9]{2}-[0-9]{2}` and otherwise raises `ValueError`.
    - `ReadingSetOut(name: str, scriptures: list[str], source: Literal["lectio", "vanderbilt", "merged"])`.
    - `LectionaryOut(date: DateType, status: Literal["ok", "no_readings"], partial: bool, reading_sets: list[ReadingSetOut], default_index: Optional[int])`.
    - The module now imports `re`, `date as DateType`, `Annotated` and `BeforeValidator`. Tasks 10 and 11 extend these same import lines rather than adding them again.
  - `api.routes.lectionary`:
    - `router`.
    - `lectionary_readings(on: Annotated[IsoDate, Query(alias="date")], _rl: None = Depends(rate_limit("lectionary"))) -> LectionaryOut`, with `responses=error_responses(401, 422, 429, 502, 503, 504)`.
  - OpenAPI:
    - The path `/lectionary/readings` (GET, query `date`, `format: date`).
    - The components `LectionaryOut` and `ReadingSetOut`. 2b consumes these as `components["schemas"]["LectionaryOut"]` and `components["schemas"]["ReadingSetOut"]`.
  - `test_route_guards.USER_SCOPED` gains `("GET", "/lectionary/readings")`. Tasks 10 and 11 add their routes to the same set and extend the docstring's "2a:" line.

Counts after this task:
- Backend: **921 passed, 9 skipped** (912 + 9, all in `test_api_lectionary.py`).
- Frontend: **221 passed in 34 files** (unchanged; only generated types change, and `typecheck` passes).

- [ ] **Step 1 (agent): Write the failing API tests**

Create `backend/tests/test_api_lectionary.py`:

```python
"""GET /lectionary/readings over HTTP (S API, Status rules, Testing; AC1, AC2, AC7, AC9).

The merge, the caches and the status derivation are pinned in
test_usecase_lectionary.py. These tests pin the HTTP contract: the token,
the strict `date` parameter, the exact bodies, the `lectionary` bucket and
X-Church-Id being ignored. The two upstreams are a MockTransport put behind
integrations.http with set_http_for_tests (F §5: injection over mocking).
The autouse fixtures in conftest.py restore the real client, full buckets
and empty lectionary caches before every test.
"""
from collections.abc import Callable

import httpx
import pytest
from sqlalchemy import select

from api import ratelimit
from api import settings as settings_mod
from db import session_scope
from db.models import User
from domain_errors import RateLimited
from integrations import http
from tests import upstream_fixtures
from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"
ORIGIN = "https://church.example.app"
LECTIO_HOST = "lectio-api.org"
VANDERBILT_HOST = "lectionary.library.vanderbilt.edu"
UNREACHABLE = ("The lectionary couldn't be reached. "
               "Enter readings yourself, or try again in a few minutes.")
RANGE = "Enter a date between 1900 and 2199."

# S "Example": both sources answer; Vanderbilt alone has the Palms set, and the
# Passion set is in both (merged) and is the default.
PALM_SUNDAY = {
    "date": "2026-03-29",
    "status": "ok",
    "partial": False,
    "default_index": 1,
    "reading_sets": [
        {"name": "Liturgy of the Palms", "source": "vanderbilt",
         "scriptures": ["Psalm 118:1-2, 19-29", "Matthew 21:1-11"]},
        {"name": "Liturgy of the Passion", "source": "merged",
         "scriptures": ["Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11",
                        "Matthew 26:14-27:66"]},
    ],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _upstream(answer: Callable[[httpx.Request], httpx.Response]) -> list[httpx.Request]:
    """Put a fake Lectio and Vanderbilt behind integrations.http: `answer`
    builds each response. Returns the list every outbound request lands in."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host in (LECTIO_HOST, VANDERBILT_HOST), request.url.host
        seen.append(request)
        return answer(request)

    http.set_http_for_tests(httpx.Client(transport=httpx.MockTransport(handler)))
    return seen


def _not_found(request: httpx.Request) -> httpx.Response:
    """Neither source has anything for the date: a definitive none (S Status rules)."""
    if request.url.host == LECTIO_HOST:
        return httpx.Response(404, json={"error": "No readings found"})
    return httpx.Response(404, text="<html><body>Not Found</body></html>",
                          headers={"Content-Type": "text/html"})


def _server_error(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="Internal Server Error")


def _timeout(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("The read operation timed out", request=request)


def _recorded(request: httpx.Request) -> httpx.Response:
    """The recorded fixtures (T1): Lectio by its `date` parameter, Vanderbilt
    by the year in its path (/calendar/2025-26/)."""
    if request.url.host == LECTIO_HOST:
        recorded = upstream_fixtures.load("lectio", request.url.params["date"])
    else:
        recorded = upstream_fixtures.load("vanderbilt", request.url.path.split("/")[2])
    return httpx.Response(recorded.status, content=recorded.body,
                          headers={"Content-Type": recorded.content_type})


def _readings(client, day: str, headers: dict[str, str]):
    return client.get("/lectionary/readings", params={"date": day}, headers=headers)


def _user_id(email: str = EMAIL):
    with session_scope() as s:
        return s.execute(select(User.id).where(User.email == email)).scalar_one()


def test_requires_token_401(client):
    seen = _upstream(_not_found)
    r = client.get("/lectionary/readings", params={"date": "2026-03-29"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    assert seen == []


def test_palm_sunday_200_shape(client):
    """AC1 and S's example, end to end over the recorded fixtures. If the
    recording differs from S's example, the expected value is the recorded
    result and T12 corrects S (2a clarification 41)."""
    _upstream(_recorded)
    r = _readings(client, "2026-03-29", auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    assert r.json() == PALM_SUNDAY


def test_church_header_ignored_zero_church_user_200(client, make_church):
    seen = _upstream(_not_found)
    someone_elses = make_church(name="Someone Else's")
    headers = {**auth_headers(EMAIL), "X-Church-Id": str(someone_elses)}
    r = _readings(client, "2026-09-29", headers)
    assert r.status_code == 200, r.text
    assert r.json() == {"date": "2026-09-29", "status": "no_readings", "partial": False,
                        "reading_sets": [], "default_index": None}
    assert {request.url.host for request in seen} == {LECTIO_HOST, VANDERBILT_HOST}
    assert client.get("/me", headers=auth_headers(EMAIL)).json()["churches"] == []


def test_bad_date_422_fields_date(client, limiter_clock):
    seen = _upstream(_not_found)
    headers = auth_headers(EMAIL)
    for bad in ("2026-3-29", "0", "2026-03-29T00:00:00", "2026-02-30"):
        r = _readings(client, bad, headers)
        assert r.status_code == 422, bad
        assert r.json()["error"]["code"] == "invalid_request", bad
        assert r.json()["error"]["message"] == "The request was not valid.", bad
        assert r.json()["error"]["fields"] == {"date": "Not a valid value."}, bad
    missing = client.get("/lectionary/readings", headers=headers)
    assert missing.status_code == 422
    assert missing.json()["error"]["fields"] == {"date": "Required."}
    assert seen == []
    # The bucket's dependency runs before FastAPI validates the query, so each
    # of the five 422s spent a token: exactly 115 of 120 are left (2a clarification 38).
    ratelimit.consume("lectionary", user_id=_user_id(), cost=115)
    with pytest.raises(RateLimited):
        ratelimit.consume("lectionary", user_id=_user_id())


def test_out_of_range_422_exact_message(client):
    seen = _upstream(_not_found)
    headers = auth_headers(EMAIL)
    for outside in ("1899-12-31", "2200-01-01", "0001-01-01"):
        r = _readings(client, outside, headers)
        assert r.status_code == 422, outside
        assert r.json() == {"error": {
            "code": "invalid_request",
            "message": RANGE,
            "request_id": r.headers["x-request-id"],
            "fields": {"date": RANGE},
        }}, outside
    assert seen == []                                   # no lookup runs
    for edge in ("1900-01-01", "2199-12-31"):
        r = _readings(client, edge, headers)
        assert r.status_code == 200, (edge, r.text)
        assert r.json()["date"] == edge


def test_502_exact_message(client):
    seen = _upstream(_server_error)
    r = _readings(client, "2026-10-04", auth_headers(EMAIL))
    assert r.status_code == 502
    assert r.json() == {"error": {
        "code": "upstream_error",
        "message": UNREACHABLE,
        "request_id": r.headers["x-request-id"],
    }}
    assert {request.url.host for request in seen} == {LECTIO_HOST, VANDERBILT_HOST}


def test_504_exact_message(client):
    seen = _upstream(_timeout)
    r = _readings(client, "2026-10-04", auth_headers(EMAIL))
    assert r.status_code == 504
    assert r.json() == {"error": {
        "code": "upstream_timeout",
        "message": UNREACHABLE,
        "request_id": r.headers["x-request-id"],
    }}
    assert {request.url.host for request in seen} == {LECTIO_HOST, VANDERBILT_HOST}


def test_121st_call_429_with_headers_and_cors(tmp_db, limiter_clock, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", ORIGIN)
    settings_mod.get_settings.cache_clear()
    try:
        client = make_api_client()
        seen = _upstream(_not_found)
        headers = {**auth_headers(EMAIL), "Origin": ORIGIN}
        for n in range(120):                    # limiter_clock never moves: no token comes back
            r = _readings(client, "2026-09-29", headers)
            assert r.status_code == 200, (n, r.text)
        assert len(seen) == 2                   # the first call filled both caches; the rest were hits
        r = _readings(client, "2026-09-29", headers)
        assert r.status_code == 429
        assert r.json() == {"error": {
            "code": "rate_limited",
            "message": "Too many requests. Try again in 3 seconds.",
            "request_id": r.headers["x-request-id"],
            "details": {"retry_after_seconds": 3},
        }}
        assert r.headers["retry-after"] == "3"  # one token per 2.5 s, rounded up
        assert r.headers["access-control-allow-origin"] == ORIGIN
        assert len(seen) == 2                   # the 429 never reached the usecase
        limiter_clock.advance(2.5)
        assert _readings(client, "2026-09-29", headers).status_code == 200
    finally:
        settings_mod.get_settings.cache_clear()


def test_date_echoed_never_normalized(client):
    """Ascension Thursday is looked up as itself, not as the Sunday before
    (2026-05-10), and none of its sets is named for a Sunday (S Behavior changes row 3)."""
    seen = _upstream(_recorded)
    r = _readings(client, "2026-05-14", auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["date"] == "2026-05-14"
    assert body["status"] == "ok"
    assert body["reading_sets"]
    assert not any("Sunday" in s["name"] for s in body["reading_sets"])
    assert [request.url.params["date"] for request in seen
            if request.url.host == LECTIO_HOST] == ["2026-05-14"]
```

- [ ] **Step 2 (agent): Add the route to the two route maps**

In `backend/tests/test_route_guards.py`, replace the docstring's last paragraph (lines 17-18):

```python
Every slice that adds a user-scoped route adds it to USER_SCOPED in the same PR
(1b: POST /churches, POST /invites/preview, POST /invites/accept).
```

with:

```python
Every slice that adds a user-scoped route adds it to USER_SCOPED in the same PR
(1b: POST /churches, POST /invites/preview, POST /invites/accept;
2a: GET /lectionary/readings).
```

and in the same file replace the end of `USER_SCOPED` (lines 41-42):

```python
    ("POST", "/invites/accept"),
}
```

with:

```python
    ("POST", "/invites/accept"),
    ("GET", "/lectionary/readings"),
}
```

In `backend/tests/test_api_app.py`, inside `test_routes_document_the_error_body`, replace the map's last entry and its closing brace (lines 277-278):

```python
        ("/invites/accept", "post"): {"400", "401", "422", "503"},
    }
```

with:

```python
        ("/invites/accept", "post"): {"400", "401", "422", "503"},
        ("/lectionary/readings", "get"): {"401", "422", "429", "502", "503", "504"},
    }
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_lectionary.py backend/tests/test_route_guards.py backend/tests/test_api_app.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_api_lectionary.py 2>&1 | grep -m2 '^E '
```

**Expected:**
- The first command ends with `12 failed, 28 passed, 1 skipped in <t>s`. The skip is `test_api_app.py:390`, which needs `TEST_DATABASE_URL`. The 12 failures are:
  - all 9 tests in `test_api_lectionary.py`;
  - `test_route_guards.py::test_user_scoped_routes_require_a_user` (`KeyError: ('GET', '/lectionary/readings')`);
  - `test_route_guards.py::test_allowlists_name_real_routes`;
  - `test_api_app.py::test_routes_document_the_error_body` (`KeyError: '/lectionary/readings'`).
- The second command prints `E       assert 404 == 401` and then the `+  where 404 = <Response [404 Not Found]>.status_code` line. The route does not exist yet, so every call is Starlette's 404.

- [ ] **Step 4 (agent): Add the schemas**

In `backend/api/schemas.py`, replace lines 1-6:

```python
"""Request and response models (also documented at /docs)."""
import uuid
from datetime import datetime
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field
```

with:

```python
"""Request and response models (also documented at /docs)."""
import re
import uuid
from datetime import date as DateType   # `datetime.date` would be a method here (2a clarification 6)
from datetime import datetime
from typing import Annotated, Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
```

Then append the following after the file's last line (`    message: str`, the end of `InviteAcceptOut`). Two blank lines separate it from that class:

```python


# --- slice 2a: readings (S Schemas) ---

_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")


def _iso_date_only(value: object) -> object:
    """Let only a whole YYYY-MM-DD string through to Pydantic's date parsing.

    Pydantic's lax `date` reads "0" as 1970-01-01 and "2026-03-29T00:00:00"
    as its day, which would answer for a date nobody asked about. A string of
    the right shape that is no real date ("2026-02-30") still fails in
    Pydantic's own parsing. Every failure is "Not a valid value." (api/errors.py).
    """
    if isinstance(value, str) and _ISO_DATE.fullmatch(value):
        return value
    raise ValueError("Expected a YYYY-MM-DD date.")


# A strict calendar date for a query parameter; OpenAPI still says `format: date`.
IsoDate = Annotated[DateType, BeforeValidator(_iso_date_only)]


class ReadingSetOut(BaseModel):
    """One set of readings. `scriptures` is in display order (first, psalm,
    second, gospel) with compound cells split; the usecase guarantees 1-20
    lines of 1-200 characters and a name of 1-300 (fits_draft_limits)."""

    name: str
    scriptures: list[str]
    source: Literal["lectio", "vanderbilt", "merged"]


class LectionaryOut(BaseModel):
    """GET /lectionary/readings. `date` echoes the request and is never
    normalized; `partial` means sets were found but one source failed;
    `default_index` is None exactly when `reading_sets` is empty."""

    date: DateType
    status: Literal["ok", "no_readings"]
    partial: bool
    reading_sets: list[ReadingSetOut]
    default_index: Optional[int]
```

- [ ] **Step 5 (agent): Write the route**

Create `backend/api/routes/lectionary.py`:

```python
"""GET /lectionary/readings: the reading sets for one date (S API, Status rules).

User-scoped: the lectionary is global data, so the route depends on
get_current_user (through the lectionary bucket's dependency) and never on
require_church, and X-Church-Id is ignored (F §1.2). `date` must be a whole
YYYY-MM-DD (IsoDate) and is looked up as itself, never moved to a Sunday.
The bucket's dependency runs before FastAPI validates the query, so a 422
also spends a token, as on POST /churches (F §1.8). Plain `def`: the usecase
blocks on upstream HTTP.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import IsoDate, LectionaryOut, ReadingSetOut
from usecases import lectionary

router = APIRouter()


@router.get("/lectionary/readings", response_model=LectionaryOut,
            responses=error_responses(401, 422, 429, 502, 503, 504))
def lectionary_readings(
    on: Annotated[IsoDate, Query(alias="date")],
    _rl: None = Depends(rate_limit("lectionary")),
) -> LectionaryOut:
    result = lectionary.readings_for_date(on)
    return LectionaryOut(
        date=result.date,
        status=result.status,
        partial=result.partial,
        reading_sets=[ReadingSetOut(name=s.name, scriptures=list(s.scriptures), source=s.source)
                      for s in result.reading_sets],
        default_index=result.default_index,
    )
```

- [ ] **Step 6 (agent): Mount the router**

In `backend/api/main.py`, replace line 12:

```python
from api.routes import churches, health, invites, me, rubric
```

with:

```python
from api.routes import churches, health, invites, lectionary, me, rubric
```

and replace line 61:

```python
    app.include_router(invites.router)
```

with:

```python
    app.include_router(invites.router)
    app.include_router(lectionary.router)
```

- [ ] **Step 7 (agent): Run the tests**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_lectionary.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3
```

**Expected:** `43 passed, 1 skipped in <t>s`. That is 9 + 31 + 3: `test_route_guards.py` and `test_api_app.py` have 31 passing tests between them, and `test_no_streamlit_in_core.py` has 3, and its `unmounted: []` check now covers `api.routes.lectionary`.

Two outcomes need action:
- If the only failure is `test_palm_sunday_200_shape`, do Step 8.
- If anything else fails, stop and find why. For example, `test_date_echoed_never_normalized` failing means Task 6b or 7 returned the wrong sets for 2026-05-14.

Otherwise, skip Step 8.

- [ ] **Step 8 (agent; only if Step 7's one failure is `test_palm_sunday_200_shape`): Assert the recorded Palm Sunday (clarification 41)**

S's Palm Sunday names and scriptures are Vanderbilt text that nobody has verified. Print the actual body:

```bash
.venv/bin/python -m pytest -q -vv backend/tests/test_api_lectionary.py::test_palm_sunday_200_shape 2>&1 | sed -n '/^E /,/^$/p' | head -60
```

Replace `PALM_SUNDAY` with the actual body only when **all** of the following hold:
- `status` is `"ok"` and `partial` is `False`;
- there are two sets, in the order `"vanderbilt"` then `"merged"`, and `default_index` is `1`;
- `test_usecase_lectionary.py` and `test_lectionary_domain.py` pass on the same fixtures;
- every differing `name` or `scriptures` string appears verbatim in `backend/tests/fixtures/vanderbilt/2025-26.csv` or `backend/tests/fixtures/lectio/2026-03-29.json`, after `clean_cell`'s split.

If any of these fails, stop and report it. That is a Task 6b or Task 7 bug, not a recording difference.

When you replace it, change the comment above `PALM_SUNDAY` to:

```python
# The recorded Palm Sunday (2a clarification 41): it differs from S's example,
# which Task 12 corrects. Vanderbilt alone has the Palms set, and the Passion
# set is in both (merged) and is the default.
```

Then rerun Step 7's command and expect `43 passed, 1 skipped in <t>s`. Step 11's commit message gains a line (shown there) that names each difference, so Task 12 can correct S :266-275.

- [ ] **Step 9 (agent): Regenerate the OpenAPI files and typecheck**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api) && (cd frontend && npm run typecheck)
git diff --stat -- frontend/src/lib/api
grep -n '"/lectionary/readings"\|LectionaryOut: {\|ReadingSetOut: {' frontend/src/lib/api/schema.d.ts
```

**Expected:**
- `Wrote <repo>/frontend/src/lib/api/openapi.json`, then openapi-typescript's `🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts`, then `tsc --noEmit` with no errors.
- The diff stat is `2 files changed, 323 insertions(+)`: 187 lines in `openapi.json` and 136 in `schema.d.ts`. Insertions only: the change is additive.
- The grep finds the path `"/lectionary/readings": {` and the two components, `LectionaryOut: {` and `ReadingSetOut: {`.

- [ ] **Step 10 (agent): Run the whole suite**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `921 passed, 9 skipped in <t>s`. Before Step 9, `test_openapi_contract.py::test_committed_openapi_matches_the_live_schema` failed. If it still fails, rerun Step 9.

- [ ] **Step 11 (agent): Commit**

```bash
git status --short
git add backend/api/routes/lectionary.py backend/api/schemas.py backend/api/main.py \
  backend/tests/test_api_lectionary.py backend/tests/test_route_guards.py backend/tests/test_api_app.py \
  frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: GET /lectionary/readings with a strict date and the lectionary bucket (S API, Schemas; AC1, AC2, AC7, AC9)

A thin, user-scoped route over usecases.lectionary: X-Church-Id is
ignored, and rate_limit(\"lectionary\") (120 per 5 min per user) runs
before the query is validated, so a 422 also spends a token (2a
clarification 38). ?date= is IsoDate, a whole YYYY-MM-DD, so '0' and
datetimes are 'Not a valid value.' and the date is never normalized
(clarification 3). LectionaryOut and ReadingSetOut as in S; errors
401, 422, 429, 502, 503 and 504 documented (clarification 4). OpenAPI
and schema.d.ts regenerated.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

If Step 8 ran, add this line to the message body, after the paragraph and before the blank line and `Co-Authored-By`. Name each difference with the recorded text:

```
Palm Sunday: the recording differs from S's example (<S's text> -> <recorded text>, for each difference); Task 12 corrects S (2a clarification 41).
```

**Expected:**
- The first `git status --short` prints exactly:

  ```
   M backend/api/main.py
   M backend/api/schemas.py
   M backend/tests/test_api_app.py
   M backend/tests/test_route_guards.py
   M frontend/src/lib/api/openapi.json
   M frontend/src/lib/api/schema.d.ts
  ?? .claude/
  ?? backend/api/routes/lectionary.py
  ?? backend/tests/test_api_lectionary.py
  ```

- Then `<sha> API: GET /lectionary/readings with a strict date and the lectionary bucket (S API, Schemas; AC1, AC2, AC7, AC9)`.
- Then only `?? .claude/`.
### Task 9: Passages in `scripture_fetcher.py`: planned sections, part cache, upstream budgets and statuses (S Passages, Status rules, Testing `test_scripture_fetcher.py`; AC5 domain half; F §2.3.3, §2.7; 2a clarifications 13, 27, 33, 36, 39)

This task turns `scripture_fetcher.py` from "text or None" into structured passages. `fetch_passage` returns a `Passage` whose `Section`s (one per " or " alternative, split in any case) each carry a status (`ok`, `not_found` or `unavailable`) and the text of the parts that loaded; `assemble_passage` is the one place those statuses are derived (S Status rules), and Task 10's `load_passages` reuses it. Each alternative is planned into normalized parts with Task 5's `split_joined`, `split_parts` and `normalize_for_fetch`, so "Isaiah 50:4-9a" is fetched as `/isaiah%2050:4-9` (AC5). `fetch_part` makes at most one upstream call through `integrations.http` (10 s read): bible-api parts go through a 7-day `TTLCache` keyed by `(translation, normalized part)`, a not-found answer is cached as the `NOT_FOUND` value, and transient failures and budget misses are raised inside the loader as a private `_Transient`, so nothing transient is ever stored (clarification 36). Every uncached part first takes a token from Task 3's process-wide budget; ESV is never cached. `get_passage_text` returns the `ok` sections' text or `None`, never a sentinel. The public names used by frozen code and `streamlit_views/settings.py:28` stay: `TRANSLATIONS`, `DEFAULT_TRANSLATION`, `BIBLE_API_BASE`, `ESV_API_BASE`, `esv_configured()`, the zero-argument `available_translations()`, `translation_label()` and `get_passage_text()`. The ESV key is still read from the environment by `_esv_key()` (S "Configuration exception", until slice 7).

`test_scripture_fetcher.py` replaces `test_scripture_translations.py`, whose five tests are ported first (S Testing). They moved off `monkeypatch.setattr(sf.httpx, "get", …)`, which is no longer the call site, onto Task 2's seam: an `httpx.MockTransport` installed behind `integrations.http`'s own client settings with `set_http_for_tests`, as Task 8 does. No route changes, so the OpenAPI files are not regenerated, and the frontend does not change.

**Files:**
- Modify: `backend/scripture_fetcher.py` (the whole file is replaced; every public name listed above is kept)
- Modify: `backend/tests/conftest.py` (autouse `_fresh_passage_cache`, inserted directly above the line `# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---`, below Task 7's `_fresh_lectionary_caches`)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (the import list gains `scripture_fetcher`; no count change)
- Delete: `backend/tests/test_scripture_translations.py` (5 tests, all ported)
- Test: `backend/tests/test_scripture_fetcher.py` (new, 22 tests)

**Interfaces:**
- Consumes:
  - Task 1: `tests.upstream_fixtures.load(kind: str, name: str | date) -> Recorded` and `tests.upstream_fixtures.Recorded(status: int, content_type: str, body: bytes)`. Fixtures used: `bible_api/isaiah_50_4-9` (200), `bible_api/isaiah_50_4-9a` (404, used as the body of every bible-api 404), `bible_api/luke_2_1-14_15-20` (200, the comma list), `esv/success` (200, `"passages": ["For God so loved the world. (ESV)"]`), `esv/empty` (200, `{"passages": []}`).
  - Task 2: `integrations.http.get(url: str, *, params: Mapping[str, str] | None = None, headers: Mapping[str, str] | None = None, read_timeout: float) -> httpx.Response` (a 4xx or 5xx is returned; transport problems raise `httpx.HTTPError` subclasses, a timeout an `httpx.TimeoutException`), `integrations.http.build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`, `integrations.http.set_http_for_tests(client: httpx.Client | None) -> None`; `cache.TTLCache(maxsize: int, ttl_ok: float, ttl_fail: float, clock: Callable[[], float] = time.monotonic)` with `.get_or_load(key, loader)` (a returned value, sentinel included, is stored for `ttl_ok`; any exception that is not a `CacheableFailure` is re-raised to the leader and every waiter of that flight and stored nowhere; a TTL of 0 stores nothing); the autouse `_fresh_http_client`.
  - Task 3: `integrations.budget.try_acquire(upstream: Literal["bible_api", "esv"]) -> bool` (`bible_api` 15 / 30 s; `esv` 60 / 60 s, 1 000 / 3 600 s and 5 000 / 86 400 s; never waits), called as `budget.try_acquire(...)` on the imported module; the autouse `_fresh_rate_limits`; the fixture `budget_clock -> FakeClock`.
  - Task 5: `scripture_refs.split_alternatives(ref: str) -> list[str]` (splits on `\s+or\s+` in any case, trims, drops empty pieces), `scripture_refs.split_joined(ref: str) -> list[str]`, `scripture_refs.split_parts(ref: str) -> list[str]` (moved unchanged from `scripture_fetcher.py:124-140`), `scripture_refs.normalize_for_fetch(ref: str) -> str`.
  - `tests.conftest.FakeClock(start: float = 1000.0)` with `.now()` and `.advance(seconds)`.
  - Callers that must keep working: `streamlit_views/settings.py:28` (`available_translations`, `translation_label`, `DEFAULT_TRANSLATION`; `streamlit_tests/test_settings_prompts_translation.py` runs it); frozen `app.py:29-34` (`get_passage_text`, `available_translations`, `translation_label`, `DEFAULT_TRANSLATION`; not imported by any test).
- Produces (all in `backend/scripture_fetcher.py`):
  - Kept unchanged: `BIBLE_API_BASE = "https://bible-api.com"`, `ESV_API_BASE = "https://api.esv.org/v3/passage/text/"`, `DEFAULT_TRANSLATION = "web"`, `TRANSLATIONS: Dict[str, Tuple[str, str]]` (web, kjv, asv, ylt, dra, darby, bbe, oeb-us, webbe, esv), `_esv_key() -> str`, `esv_configured() -> bool`, `available_translations() -> List[Tuple[str, str]]`, `translation_label(translation_id: Optional[str]) -> str`.
  - `BIBLE_API_READ_TIMEOUT = 10.0`, `ESV_READ_TIMEOUT = 10.0`, `PART_CACHE_MAXSIZE = 2000`, `PART_CACHE_TTL_SECONDS = 604800` (7 days).
  - `PartStatus = Literal["ok", "not_found", "unavailable"]`.
  - Frozen dataclasses `Part(reference: str, status: PartStatus, text: Optional[str])` (the normalized part that was fetched), `Section(reference: str, status: PartStatus, text: Optional[str])` (the alternative as written) and `Passage(reference: str, status: PartStatus, sections: Tuple[Section, ...])` (the reference trimmed, every section always present).
  - `NOT_FOUND`: the part-cache sentinel (`repr` is `NOT_FOUND`); never returned by a public function.
  - `plan_sections(reference: str) -> List[Tuple[str, List[str]]]`: `[(alternative as written, [normalized parts])]`, one pair per section, empty alternatives and parts dropped (`";"`, `" ; "` and `""` plan to `[]`, clarification 33). (Addition to the outline's interface; see the note under Step 5.)
  - `plan_parts(reference: str) -> List[List[str]]`: `[parts for _, parts in plan_sections(reference)]`. `sum(len(p) for p in plan_parts(ref))` is Task 10's rate-limit cost for that ref.
  - `fetch_part(part: str, translation: str) -> Part`: bible-api: the part cache, then `budget.try_acquire("bible_api")`, then one `GET f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"` with `params={"translation": translation}`; 404 → `not_found`; 200 with empty text → `not_found`; 200 that does not decode to a JSON object, any other status, a timeout or a transport error → `unavailable`. ESV (`TRANSLATIONS[translation][1] == "esv"`): no key → `unavailable` with no call and no token; then `budget.try_acquire("esv")`; the S params (`scripture_fetcher.py:91-98` today) with `q=` the normalized part and `Authorization: Token {key}`; `passages: []` → `not_found`; never cached. An unknown translation id is routed to bible-api (as today). Never raises for an upstream failure. Logs `passage_part_skipped reason=budget upstream=<bible_api|esv>` or `reason=no_key` at INFO, and `passage_part_failed reason=<timeout|network|status_NNN|bad_json> upstream=<…>` at WARNING; no reference, body or query string.
  - `assemble_passage(reference: str, alternatives: List[str], parts: List[List[Part]]) -> Passage`: `alternatives[i]` names the section built from `parts[i]` (`zip(..., strict=True)`, so a length mismatch is a `ValueError`). Section: `ok` when every part is `ok`, else `unavailable` if any part is, else `not_found`; text = the `ok` parts' texts joined with `"\n\n"`, or `None`. Passage: the same rule over its sections. No items at all is `not_found`, never `ok`.
  - `fetch_passage(reference: str, translation: str = DEFAULT_TRANSLATION) -> Passage`: parts fetched one after another, no pool and no deadline (clarification 27).
  - `get_passage_text(reference: str, translation: str = DEFAULT_TRANSLATION) -> Optional[str]`: the text of the `ok` sections joined with `"\n\n"`, or `None`; never a sentinel. Task 10 re-exports it from `usecases.passages` under the same name.
  - `reset_for_tests(clock: Callable[[], float] = time.monotonic) -> None`: a new, empty part-cache object on `clock` (clarification 39).
  - Autouse fixture `_fresh_passage_cache` in `backend/tests/conftest.py`: before every test it calls `reset_for_tests()` on `usecases.passages` and then on `scripture_fetcher`, each only when already in `sys.modules`. `usecases.passages` does not exist until Task 10; Task 10's `reset_for_tests()` (join `_POOL`, build a new pool) is then picked up here with no conftest edit, and runs before the part cache is replaced, so a straggling worker writes into the orphaned cache.
  - For Task 10: `load_passages` submits `fetch_part(part, plan.translation)` for every part, builds `Part(part, "unavailable", None)` for a part unfinished at the deadline, and reassembles each ref with `assemble_passage(ref, [alt for alt, _ in plan_sections(ref)], parts)`; `monkeypatch.setattr(budget, "try_acquire", lambda u: True)` reaches `fetch_part` because it calls the module attribute.
  - `test_usecases_package_imports_no_fastapi_or_streamlit`'s import list ends `"token_bucket, integrations.budget, scripture_refs, scripture_fetcher; "` after this task.

Counts after this task: backend **938 passed, 9 skipped** (921 + 22 − 5); frontend **221 passed in 34 files** (unchanged; not rerun here).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e backend/tests/test_scripture_fetcher.py && echo "no T9 test file yet"
grep -n "_fresh_lectionary_caches\|_fresh_passage_cache\|^# --- slice 1: network-free" backend/tests/conftest.py
grep -n 'scripture_refs; "' backend/tests/test_no_streamlit_in_core.py
PYTHONPATH=backend .venv/bin/python -c "import scripture_refs as r; print(r.normalize_for_fetch('Isaiah 50:4-9a'), r.split_joined('Genesis 1:1-2:4a and Psalm 136:1-9, 23-26'), r.split_parts('Genesis 2:15-17; 3:1-7'), r.split_alternatives('John 3:1-17 OR Matthew 17:1-9'))"
PYTHONPATH=backend .venv/bin/python -c "from tests import upstream_fixtures as u; print([u.load(k, n).status for k, n in (('bible_api', 'isaiah_50_4-9'), ('bible_api', 'isaiah_50_4-9a'), ('bible_api', 'luke_2_1-14_15-20'), ('esv', 'success'), ('esv', 'empty'))])"
.venv/bin/python -m pytest -q | tail -1
```

**Expected,** in order:
- exactly `?? .claude/` (Tasks 1–8 are committed);
- `no T9 test file yet`;
- two lines, `<n>:def _fresh_lectionary_caches():` and `<m>:# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---` (Task 7's fixture sits directly above the slice 1 comment), and no `_fresh_passage_cache`;
- `24:            "token_bucket, integrations.budget, scripture_refs; "` (Tasks 2, 3 and 5: T2 made the list two lines at 22-23 and T3 split off line 24);
- `Isaiah 50:4-9 ['Genesis 1:1-2:4a', 'Psalm 136:1-9, 23-26'] ['Genesis 2:15-17', 'Genesis 3:1-7'] ['John 3:1-17', 'Matthew 17:1-9']`;
- `[200, 404, 200, 200, 200]`;
- `921 passed, 9 skipped in <t>s` (Task 8's count).

If the suite line differs, stop and find why. If a fixture name raises `FileNotFoundError`, Task 1 recorded it under another stem: use Task 1's stem in the five `upstream_fixtures.load(...)` lines at the top of the Step 2 test file, and change nothing else. If the gate line differs, Step 7 says how to adapt.

- [ ] **Step 2 (agent): Write the failing tests**

Create `backend/tests/test_scripture_fetcher.py`:

```python
"""scripture_fetcher: translations, planning, part fetching, statuses and
caching (S "Passages", Status rules, Testing "test_scripture_fetcher.py";
AC5 domain half; F §2.3.3, §2.7; 2a clarifications 13, 27, 33, 36, 39).

Replaces test_scripture_translations.py: its five tests come first, ported
from monkeypatching sf.httpx.get (no longer the call site) to the T2 seam.
Every upstream answer comes from an httpx.MockTransport installed behind
integrations.http's own client settings (set_http_for_tests), so nothing
leaves the process and the _no_network guard stays active (AC13). Recorded
bodies come from tests/fixtures/bible_api and tests/fixtures/esv (T1).

The autouse _fresh_passage_cache fixture gives each test a new part cache,
_fresh_rate_limits full upstream budgets, and _fresh_http_client the
default client back afterwards."""
import inspect
import json
import logging

import httpx

import scripture_fetcher as sf
from integrations import budget, http
from tests import upstream_fixtures
from tests.conftest import FakeClock

WEEK = 7 * 24 * 60 * 60

BIBLE_OK = upstream_fixtures.load("bible_api", "isaiah_50_4-9")
BIBLE_404 = upstream_fixtures.load("bible_api", "isaiah_50_4-9a")
BIBLE_COMMA = upstream_fixtures.load("bible_api", "luke_2_1-14_15-20")
ESV_OK = upstream_fixtures.load("esv", "success")
ESV_EMPTY = upstream_fixtures.load("esv", "empty")
ESV_PATH = "/v3/passage/text/"


def _replay(recorded):
    return httpx.Response(recorded.status, content=recorded.body,
                          headers={"Content-Type": recorded.content_type})


def _text_of(recorded):
    return json.loads(recorded.body)["text"].strip()


def _read_timeout(request):
    raise httpx.ReadTimeout("read timed out", request=request)


def _install(answers):
    """Answer every upstream call by its decoded URL path (for example
    "/genesis 2:15-17", or ESV_PATH). The value decides the answer:
    - a str: a bible-api 200 whose "text" is that string plus a newline;
    - a recorded fixture: replayed as recorded;
    - 404: bible-api's recorded 404; any other int: that status, no body;
    - a callable: called with the request (it may raise).
    The dict is read on every call, so a test can change an answer between
    calls. A path not in `answers` raises KeyError out of the call and fails
    the test. Returns the list of requests the transport saw, in order."""
    seen = []

    def handler(request):
        seen.append(request)
        answer = answers[request.url.path]
        if isinstance(answer, str):
            return httpx.Response(200, json={"reference": request.url.path, "text": answer + "\n"})
        if isinstance(answer, upstream_fixtures.Recorded):
            return _replay(answer)
        if answer == 404:
            return _replay(BIBLE_404)
        if isinstance(answer, int):
            return httpx.Response(answer)
        return answer(request)

    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(handler)))
    return seen


def _skips_and_failures(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == "scripture_fetcher" and r.getMessage().startswith("passage_part_")]


# --- ported from test_scripture_translations.py ---

def test_esv_excluded_without_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    ids = [tid for tid, _ in sf.available_translations()]
    assert "web" in ids and "kjv" in ids
    assert "esv" not in ids            # hidden until a key is configured
    assert sf.esv_configured() is False


def test_esv_included_last_with_key(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    ids = [tid for tid, _ in sf.available_translations()]
    assert ids == list(sf.TRANSLATIONS)          # display order, every translation
    assert ids[0] == sf.DEFAULT_TRANSLATION == "web"
    assert ids[-1] == "esv"


def test_translation_label():
    assert "World English Bible" in sf.translation_label("web")
    assert "ESV" in sf.translation_label("esv")
    assert sf.translation_label(None) == sf.translation_label("web")
    assert sf.translation_label("unknown-id") == "unknown-id"


def test_esv_routing_token_header(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = _install({ESV_PATH: ESV_OK})
    assert sf.get_passage_text("John 3:16", translation="esv") == "For God so loved the world. (ESV)"
    (request,) = seen
    assert str(request.url.copy_with(query=None)) == sf.ESV_API_BASE
    assert dict(request.url.params) == {
        "q": "John 3:16",
        "include-headings": "false",
        "include-footnotes": "false",
        "include-verse-numbers": "false",
        "include-passage-references": "false",
        "include-short-copyright": "true",
    }
    assert request.headers["Authorization"] == "Token test-key"
    assert request.headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    assert request.extensions["timeout"]["read"] == sf.ESV_READ_TIMEOUT == 10.0


def test_bible_api_routing_translation_param():
    seen = _install({"/genesis 1:1": "In the beginning..."})
    assert sf.get_passage_text("Genesis 1:1", translation="kjv") == "In the beginning..."
    (request,) = seen
    assert str(request.url).startswith(sf.BIBLE_API_BASE + "/")
    assert dict(request.url.params) == {"translation": "kjv"}
    assert "Authorization" not in request.headers
    assert request.extensions["timeout"]["read"] == sf.BIBLE_API_READ_TIMEOUT == 10.0
    assert request.extensions["timeout"]["connect"] == 5.0


# --- planning and URLs ---

def test_url_quotes_normalized_part():
    seen = _install({"/isaiah 50:4-9": BIBLE_OK, "/luke 2:1-14, 15-20": BIBLE_COMMA})
    isaiah = sf.fetch_passage("Isaiah 50:4-9a", "web")
    luke = sf.fetch_passage("Luke 2:1-14, (15-20)", "web")
    assert [r.url.raw_path for r in seen] == [
        b"/isaiah%2050:4-9?translation=web",             # AC5: the "a" is dropped for the fetch
        b"/luke%202:1-14,%2015-20?translation=web",
    ]
    assert isaiah == sf.Passage("Isaiah 50:4-9a", "ok", (
        sf.Section("Isaiah 50:4-9a", "ok", _text_of(BIBLE_OK)),))   # the displayed text never changes
    assert luke.status == "ok" and luke.sections[0].text == _text_of(BIBLE_COMMA)


def test_plan_parts_alternatives_joined_semicolons():
    assert sf.plan_parts("Genesis 2:15-17; 3:1-7 or Matthew 4:1-11") == [
        ["Genesis 2:15-17", "Genesis 3:1-7"], ["Matthew 4:1-11"]]
    assert sf.plan_parts("John 3:1-17 OR Matthew 17:1-9") == [["John 3:1-17"], ["Matthew 17:1-9"]]
    assert sf.plan_parts("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26") == [
        ["Genesis 1:1-2:4", "Psalm 136:1-9, 23-26"]]
    assert sf.plan_parts("Isaiah 50:4-9a") == [["Isaiah 50:4-9"]]
    assert sf.plan_sections("John 3:1-17 or Matthew 17:1-9") == [
        ("John 3:1-17", ["John 3:1-17"]), ("Matthew 17:1-9", ["Matthew 17:1-9"])]
    for empty in (";", " ; ", "", "   "):
        assert sf.plan_parts(empty) == []                 # 2a clarification 33
        assert sf.plan_sections(empty) == []


def test_alternatives_become_sections():
    seen = _install({"/john 3:1-17": "Nicodemus came by night.",
                     "/matthew 17:1-9": "Jesus was transfigured."})
    passage = sf.fetch_passage("  John 3:1-17 or Matthew 17:1-9 ", "web")
    assert passage == sf.Passage("John 3:1-17 or Matthew 17:1-9", "ok", (
        sf.Section("John 3:1-17", "ok", "Nicodemus came by night."),
        sf.Section("Matthew 17:1-9", "ok", "Jesus was transfigured."),
    ))
    text = sf.get_passage_text("John 3:1-17 or Matthew 17:1-9")
    assert text == "Nicodemus came by night.\n\nJesus was transfigured."   # no "--- alt ---" headers
    assert len(seen) == 2                                  # the second call came from the cache


def test_semicolon_parts_joined_with_blank_line():
    seen = _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": "The serpent."})
    passage = sf.fetch_passage("Genesis 2:15-17; 3:1-7", "web")
    assert [r.url.path for r in seen] == ["/genesis 2:15-17", "/genesis 3:1-7"]   # in order
    assert passage == sf.Passage("Genesis 2:15-17; 3:1-7", "ok", (
        sf.Section("Genesis 2:15-17; 3:1-7", "ok", "The garden.\n\nThe serpent."),))


def test_split_joined_parts_fetched_separately():
    seen = _install({"/genesis 1:1-2:4": "Creation.", "/psalm 136:1-9, 23-26": "His love endures.",
                     "/psalm 42 and 43": 404})
    vigil = sf.fetch_passage("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26", "web")
    assert [r.url.path for r in seen] == ["/genesis 1:1-2:4", "/psalm 136:1-9, 23-26"]
    assert vigil.sections == (
        sf.Section("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26", "ok", "Creation.\n\nHis love endures."),)
    whole = sf.fetch_passage("Psalm 42 and 43", "web")   # "43" is not a book: one part, S :403
    assert [r.url.path for r in seen][2:] == ["/psalm 42 and 43"]
    assert whole.status == "not_found"


# --- statuses (S Status rules) ---

def test_status_all_ok():
    _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": "The serpent.",
              "/matthew 4:1-11": "The temptation."})
    assert sf.fetch_part("Genesis 2:15-17", "web") == sf.Part("Genesis 2:15-17", "ok", "The garden.")
    passage = sf.fetch_passage("Genesis 2:15-17; 3:1-7 or Matthew 4:1-11", "web")
    assert passage.status == "ok"
    assert [(s.reference, s.status) for s in passage.sections] == [
        ("Genesis 2:15-17; 3:1-7", "ok"), ("Matthew 4:1-11", "ok")]
    assert sf.get_passage_text("Genesis 2:15-17; 3:1-7 or Matthew 4:1-11") == (
        "The garden.\n\nThe serpent.\n\nThe temptation.")


def test_one_semicolon_part_404_section_not_found_keeps_text():
    _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": 404})
    passage = sf.fetch_passage("Genesis 2:15-17; 3:1-7", "web")
    assert sf.fetch_part("Genesis 3:1-7", "web") == sf.Part("Genesis 3:1-7", "not_found", None)
    assert passage == sf.Passage("Genesis 2:15-17; 3:1-7", "not_found", (
        sf.Section("Genesis 2:15-17; 3:1-7", "not_found", "The garden."),))


def test_one_part_500_section_unavailable_keeps_text(caplog):
    _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": 500, "/genesis 3:8-15": _read_timeout})
    with caplog.at_level(logging.INFO, logger="scripture_fetcher"):
        failed = sf.fetch_passage("Genesis 2:15-17; 3:1-7", "web")
        timed_out = sf.fetch_passage("Genesis 2:15-17; 3:8-15", "web")
    assert failed == sf.Passage("Genesis 2:15-17; 3:1-7", "unavailable", (
        sf.Section("Genesis 2:15-17; 3:1-7", "unavailable", "The garden."),))
    assert timed_out.sections == (
        sf.Section("Genesis 2:15-17; 3:8-15", "unavailable", "The garden."),)
    assert _skips_and_failures(caplog) == [
        "passage_part_failed reason=status_500 upstream=bible_api",
        "passage_part_failed reason=timeout upstream=bible_api",
    ]
    assert "Genesis" not in caplog.text and "genesis" not in caplog.text   # no reference in the logs


def test_one_alternative_unavailable_passage_unavailable():
    _install({"/john 3:1-17": "Nicodemus came by night.", "/matthew 17:1-9": 503,
              "/hezekiah 1:1": 404})
    passage = sf.fetch_passage("John 3:1-17 or Matthew 17:1-9", "web")
    assert passage == sf.Passage("John 3:1-17 or Matthew 17:1-9", "unavailable", (
        sf.Section("John 3:1-17", "ok", "Nicodemus came by night."),
        sf.Section("Matthew 17:1-9", "unavailable", None),
    ))
    assert sf.get_passage_text("John 3:1-17 or Matthew 17:1-9") == "Nicodemus came by night."
    mixed = sf.fetch_passage("John 3:1-17 or Hezekiah 1:1", "web")
    assert (mixed.status, [s.status for s in mixed.sections]) == ("not_found", ["ok", "not_found"])
    # assemble_passage is the one derivation (T10 reuses it); nothing at all is not_found, never ok
    ok = sf.Part("John 3:1-17", "ok", "Nicodemus came by night.")
    gone = sf.Part("Matthew 17:1-9", "unavailable", None)
    assert sf.assemble_passage("R", ["A", "B"], [[ok], [ok, gone]]) == sf.Passage("R", "unavailable", (
        sf.Section("A", "ok", "Nicodemus came by night."),
        sf.Section("B", "unavailable", "Nicodemus came by night."),
    ))
    assert sf.assemble_passage(";", [], []) == sf.Passage(";", "not_found", ())


def test_all_404_not_found_text_none():
    seen = _install({"/hezekiah 1:1": 404, "/hezekiah 2:2": 404})
    passage = sf.fetch_passage("Hezekiah 1:1; 2:2", "web")
    assert [r.url.path for r in seen] == ["/hezekiah 1:1", "/hezekiah 2:2"]
    assert passage == sf.Passage("Hezekiah 1:1; 2:2", "not_found", (
        sf.Section("Hezekiah 1:1; 2:2", "not_found", None),))
    assert sf.get_passage_text("Hezekiah 1:1; 2:2") is None


def test_esv_empty_passages_not_found(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = _install({ESV_PATH: ESV_EMPTY})
    passage = sf.fetch_passage("Hezekiah 1:1", "esv")
    assert passage == sf.Passage("Hezekiah 1:1", "not_found", (
        sf.Section("Hezekiah 1:1", "not_found", None),))
    assert len(seen) == 1
    monkeypatch.delenv("ESV_API_KEY")
    assert sf.fetch_part("John 3:16", "esv") == sf.Part("John 3:16", "unavailable", None)
    assert len(seen) == 1                                  # no key: nothing is sent


# --- budget and caching ---

def test_budget_exhausted_unavailable_not_sent_not_cached_cache_hit_served(budget_clock, caplog, monkeypatch):
    seen = _install({"/isaiah 50:4-9": BIBLE_OK, "/isaiah 51:1-3": "Listen to me."})
    assert sf.fetch_part("Isaiah 50:4-9", "web").status == "ok"          # 1 of the 15 tokens
    for _ in range(14):
        assert budget.try_acquire("bible_api")
    with caplog.at_level(logging.INFO, logger="scripture_fetcher"):
        skipped = sf.fetch_part("Isaiah 51:1-3", "web")
    assert skipped == sf.Part("Isaiah 51:1-3", "unavailable", None)
    assert [r.url.path for r in seen] == ["/isaiah 50:4-9"]              # not sent
    assert _skips_and_failures(caplog) == ["passage_part_skipped reason=budget upstream=bible_api"]
    assert sf.fetch_part("Isaiah 50:4-9", "web") == sf.Part("Isaiah 50:4-9", "ok", _text_of(BIBLE_OK))
    assert len(seen) == 1                                                # a cache hit takes no token
    budget_clock.advance(2)                                              # 15 per 30 s: one token back
    assert sf.fetch_part("Isaiah 51:1-3", "web") == sf.Part("Isaiah 51:1-3", "ok", "Listen to me.")
    assert [r.url.path for r in seen] == ["/isaiah 50:4-9", "/isaiah 51:1-3"]   # the miss was not cached
    # ESV draws on its own budget, through the module attribute T10 patches
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    monkeypatch.setattr(budget, "try_acquire", lambda upstream: False)
    assert sf.fetch_part("John 3:16", "esv") == sf.Part("John 3:16", "unavailable", None)
    assert len(seen) == 2


def test_bible_api_cached_7_days():
    assert (sf.PART_CACHE_MAXSIZE, sf.PART_CACHE_TTL_SECONDS) == (2000, 604_800)
    clock = FakeClock()
    before = sf._PART_CACHE
    sf.reset_for_tests(clock.now)
    assert sf._PART_CACHE is not before                  # a new object (2a clarification 39)
    seen = _install({"/isaiah 50:4-9": BIBLE_OK})
    first = sf.fetch_part("Isaiah 50:4-9", "web")
    assert first == sf.Part("Isaiah 50:4-9", "ok", _text_of(BIBLE_OK))
    clock.advance(WEEK - 1)
    assert sf.fetch_part("Isaiah 50:4-9", "web") == first
    assert len(seen) == 1
    assert sf.fetch_part("Isaiah 50:4-9", "kjv").status == "ok"   # keyed by translation too
    assert len(seen) == 2
    clock.advance(1)                                     # 7 days after the first fetch
    assert sf.fetch_part("Isaiah 50:4-9", "web") == first
    assert len(seen) == 3


def test_not_found_cached():
    clock = FakeClock()
    sf.reset_for_tests(clock.now)
    seen = _install({"/hezekiah 1:1": 404, "/hezekiah 2:2": ""})
    assert sf.fetch_part("Hezekiah 1:1", "web") == sf.Part("Hezekiah 1:1", "not_found", None)
    assert sf.fetch_part("Hezekiah 2:2", "web") == sf.Part("Hezekiah 2:2", "not_found", None)  # empty text
    clock.advance(WEEK - 1)
    assert sf.fetch_part("Hezekiah 1:1", "web").status == "not_found"
    assert sf.fetch_part("Hezekiah 2:2", "web").status == "not_found"
    assert len(seen) == 2


def test_transient_failure_not_cached():
    answers = {"/isaiah 50:4-9": 500}
    seen = _install(answers)
    failures = [500, 429, 403, _read_timeout,
                lambda request: httpx.Response(200, text="<html>busy</html>"),
                lambda request: httpx.Response(200, json=["not", "an", "object"])]
    for failure in failures:
        answers["/isaiah 50:4-9"] = failure
        assert sf.fetch_part("Isaiah 50:4-9", "web") == sf.Part("Isaiah 50:4-9", "unavailable", None)
    assert len(seen) == len(failures)                    # every failure was asked again
    answers["/isaiah 50:4-9"] = BIBLE_OK
    assert sf.fetch_part("Isaiah 50:4-9", "web").status == "ok"
    assert sf.fetch_part("Isaiah 50:4-9", "web").status == "ok"
    assert len(seen) == len(failures) + 1                # only the success was stored


def test_esv_never_cached(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = _install({ESV_PATH: ESV_OK})
    for _ in range(2):
        assert sf.fetch_part("John 3:16", "esv") == sf.Part(
            "John 3:16", "ok", "For God so loved the world. (ESV)")
    assert len(seen) == 2


def test_get_passage_text_none_never_sentinel_ignores_non_ok():
    seen = _install({"/hezekiah 1:1": 404, "/john 3:16": "For God so loved the world.",
                     "/matthew 17:1-9": 503, "/genesis 2:15-17": "The garden.", "/genesis 3:1-7": 404})
    assert sf.get_passage_text("Hezekiah 1:1") is None
    assert sf.get_passage_text("") is None and sf.get_passage_text(";") is None
    assert sf.get_passage_text("John 3:16 or Matthew 17:1-9") == "For God so loved the world."
    assert sf.get_passage_text("Genesis 2:15-17; 3:1-7") is None      # a not_found section's text is left out
    assert {r.url.params["translation"] for r in seen} == {"web"}     # the default translation
    assert "[Could not load text]" not in inspect.getsource(sf)
    assert repr(sf.NOT_FOUND) == "NOT_FOUND"
```

Notes for the reviewer:
- The 22 tests are the outline's list, in its order: 5 ported, 5 planning and URLs, 6 statuses, 5 budget and caching, and `test_get_passage_text_none_never_sentinel_ignores_non_ok`.
- The ported five keep every assertion of `test_scripture_translations.py:15-59` (`"web"` and `"kjv"` listed and `"esv"` hidden without a key; `"esv"` listed with it; the four `translation_label` checks; the ESV URL, `Token test-key` and the synthetic ESV text; bible-api's URL prefix and `translation=kjv`). They add the ESV display order (esv last), the exact ESV params, the User-Agent and the 10 s read timeouts.
- `_install` keys answers by the decoded path (`request.url.path`), so a test reads like the reference; `test_url_quotes_normalized_part` pins the bytes on the wire with `request.url.raw_path` (AC5).
- The "Hezekiah" references name no real book, so their 404s are realistic; "Psalm 42 and 43" stays one part because "43" is not a book (S :403).
- `test_one_alternative_unavailable_passage_unavailable` also calls `assemble_passage` directly: Task 10 builds its passages with it, so the derivation is pinned where both callers share it.
- No test blocks a thread, so no `threading.Event` is needed; `fetch_passage` is sequential (clarification 27).

- [ ] **Step 3 (agent): Run the tests to verify they fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_scripture_fetcher.py 2>&1 | tail -3
```

**Expected:** `19 failed, 3 passed in <t>s`. The three ported translation tests pass against today's module (`test_esv_excluded_without_key`, `test_esv_included_last_with_key`, `test_translation_label`). The other 19 fail on the names this task adds (`AttributeError: module 'scripture_fetcher' has no attribute 'fetch_part'`, and likewise `'plan_parts'`, `'Passage'`, `'reset_for_tests'`, `'PART_CACHE_MAXSIZE'`, `'NOT_FOUND'`), or on today's results: `fetch_passage` returns a dict or `None`, and the two routing tests get `None` because today's code calls `httpx.get` directly, which the MockTransport never sees, and the `_no_network` guard refuses the real connection (the captured log shows `Failed to fetch … Tests must not open network connections`, or a DNS error when offline). Nothing reaches the network. Step 4's autouse fixture is added only after this run: with it in place, every test would error in setup on the missing `reset_for_tests` instead.

- [ ] **Step 4 (agent): Add the autouse part-cache reset**

In `backend/tests/conftest.py`, replace the line

```python
# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
```

with

```python
# --- slice 2a: passages (S "Passages"; 2a clarification 39) ---

@pytest.fixture(autouse=True)
def _fresh_passage_cache():
    """scripture_fetcher keeps one process-wide bible-api part cache (7 days),
    and usecases.passages (Task 10) one worker pool (slice 2a). Each test
    starts with a new, empty part cache on time.monotonic, so text or a
    not-found stored by an earlier test never answers here.

    usecases.passages goes first: its reset joins the pool, so a part still
    running from an earlier test finishes before the cache is replaced, and
    writes into the old, orphaned cache (2a clarification 39). Resets only a
    module already imported: its state can exist only then (the
    deferred-import rule at the top of this file)."""
    import sys

    for name in ("usecases.passages", "scripture_fetcher"):
        module = sys.modules.get(name)
        if module is not None:
            module.reset_for_tests()
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
```

The fixtures Tasks 2, 3 and 7 added above that line stay where they are, and the two blank lines before the slice 1 comment are kept.

- [ ] **Step 5 (agent): Replace `backend/scripture_fetcher.py`**

Replace the whole file with:

```python
#!/usr/bin/env python3
"""Fetch full Bible passage text by reference (S "Passages"; F §2.3.3, §2.7).

Two sources:
  * bible-api.com — no key, several public-domain translations (default: WEB).
  * api.esv.org   — the ESV, when ESV_API_KEY is configured (register free at
                    https://api.esv.org). ESV text is © Crossway; the short
                    "(ESV)" copyright is kept on the returned text.

A reference is planned into sections and parts (plan_sections, plan_parts):
one section per " or " alternative, and one part per upstream call inside it
(" and "-joined readings and ";" pieces are fetched separately, each
normalized for fetching by scripture_refs.normalize_for_fetch). fetch_part
makes at most one upstream call; assemble_passage derives every section and
passage status and text from the parts (S Status rules), so fetch_passage
here and usecases.passages.load_passages (which runs parts on a pool under a
deadline) report the same statuses.

bible-api parts are cached for 7 days by (translation, normalized part); a
not-found answer is cached too, as NOT_FOUND. Transient failures and budget
misses are never cached, so "Try again" works. ESV text is never cached
(Crossway terms, F §2.7). Every uncached part first takes a token from the
process-wide upstream budget (integrations.budget); with none left it is not
sent and is `unavailable`.

Configuration exception (S; until slice 7): _esv_key() reads ESV_API_KEY from
the environment at call time, not from api/settings.py.

Logs name the upstream and a reason, never the reference, a body or a query
string (F §2.5). No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Tuple
from urllib.parse import quote

import httpx

from cache import TTLCache
from integrations import budget, http
from scripture_refs import normalize_for_fetch, split_alternatives, split_joined, split_parts

logger = logging.getLogger(__name__)

# bible-api.com: GET https://bible-api.com/{passage}?translation=web
BIBLE_API_BASE = "https://bible-api.com"
ESV_API_BASE = "https://api.esv.org/v3/passage/text/"

BIBLE_API_READ_TIMEOUT = 10.0
ESV_READ_TIMEOUT = 10.0

PART_CACHE_MAXSIZE = 2000
PART_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60   # 604 800

DEFAULT_TRANSLATION = "web"

# translation id -> (human label, source). Order here is the display order.
TRANSLATIONS: Dict[str, Tuple[str, str]] = {
    "web": ("World English Bible (WEB)", "bible-api"),
    "kjv": ("King James Version (KJV)", "bible-api"),
    "asv": ("American Standard Version (ASV)", "bible-api"),
    "ylt": ("Young's Literal Translation (YLT)", "bible-api"),
    "dra": ("Douay-Rheims 1899 (DRA)", "bible-api"),
    "darby": ("Darby Bible", "bible-api"),
    "bbe": ("Bible in Basic English (BBE)", "bible-api"),
    "oeb-us": ("Open English Bible, US (OEB)", "bible-api"),
    "webbe": ("World English Bible, British (WEBBE)", "bible-api"),
    "esv": ("English Standard Version (ESV)", "esv"),
}

PartStatus = Literal["ok", "not_found", "unavailable"]


@dataclass(frozen=True)
class Part:
    """One upstream call: `reference` is the normalized part that was fetched."""
    reference: str
    status: PartStatus
    text: Optional[str]


@dataclass(frozen=True)
class Section:
    """One " or " alternative, as written; `text` joins its ok parts."""
    reference: str
    status: PartStatus
    text: Optional[str]


@dataclass(frozen=True)
class Passage:
    """One reference as sent (trimmed), with every section, always."""
    reference: str
    status: PartStatus
    sections: Tuple[Section, ...]


class _NotFound:
    """The part-cache value for a reference the upstream does not have."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "NOT_FOUND"


NOT_FOUND = _NotFound()


class _Transient(Exception):
    """Raised inside the part-cache loader for an upstream failure or a budget
    miss. TTLCache stores only values and CacheableFailures, so this is never
    cached; fetch_part turns it into `unavailable` (2a clarification 36)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


_SKIP_REASONS = ("budget", "no_key")   # the part was never sent

_PART_CACHE: "TTLCache[Tuple[str, str], object]" = TTLCache(
    maxsize=PART_CACHE_MAXSIZE, ttl_ok=PART_CACHE_TTL_SECONDS, ttl_fail=0)


def reset_for_tests(clock=time.monotonic) -> None:
    """Tests: a new, empty part cache on `clock`. A new object rather than
    clear(), so a part still loading from an earlier test writes into the old,
    orphaned cache (2a clarification 39)."""
    global _PART_CACHE
    _PART_CACHE = TTLCache(maxsize=PART_CACHE_MAXSIZE, ttl_ok=PART_CACHE_TTL_SECONDS,
                           ttl_fail=0, clock=clock)


def _esv_key() -> str:
    return os.getenv("ESV_API_KEY", "").strip()


def esv_configured() -> bool:
    return bool(_esv_key())


def available_translations() -> List[Tuple[str, str]]:
    """[(id, label), ...] usable on this deployment. ESV only when its key is set."""
    out = []
    for tid, (label, source) in TRANSLATIONS.items():
        if source == "esv" and not esv_configured():
            continue
        out.append((tid, label))
    return out


def translation_label(translation_id: Optional[str]) -> str:
    """Human label for a translation id (falls back gracefully)."""
    tid = (translation_id or DEFAULT_TRANSLATION)
    entry = TRANSLATIONS.get(tid)
    return entry[0] if entry else tid


# --- planning (pure) ---

def plan_sections(reference: str) -> List[Tuple[str, List[str]]]:
    """[(alternative as written, [normalized parts])], one pair per section.

    Alternatives and parts that come out empty are dropped, so ";" plans to []
    and a section never has zero parts (2a clarification 33)."""
    sections = []
    for alternative in split_alternatives(reference):
        if not alternative.strip():
            continue
        parts = [normalize_for_fetch(piece)
                 for joined in split_joined(alternative)
                 for piece in split_parts(joined)]
        parts = [part for part in parts if part]
        if parts:
            sections.append((alternative, parts))
    return sections


def plan_parts(reference: str) -> List[List[str]]:
    """The normalized parts of each section, in order (S "Planning"). The same
    plan drives fetching, the rate-limit cost and reassembly."""
    return [parts for _alternative, parts in plan_sections(reference)]


# --- one part: one upstream call at most ---

def _bible_api_part(part: str, translation: str) -> object:
    """The part-cache loader: text, or NOT_FOUND; raises _Transient otherwise."""
    if not budget.try_acquire("bible_api"):
        raise _Transient("budget")
    url = f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"
    try:
        response = http.get(url, params={"translation": translation},
                            read_timeout=BIBLE_API_READ_TIMEOUT)
    except httpx.TimeoutException:
        raise _Transient("timeout") from None
    except httpx.HTTPError:
        raise _Transient("network") from None
    if response.status_code == 404:
        return NOT_FOUND
    if response.status_code != 200:
        raise _Transient(f"status_{response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise _Transient("bad_json") from None
    if not isinstance(data, dict):
        raise _Transient("bad_json")
    text = data.get("text")
    text = text.strip() if isinstance(text, str) else ""
    return text or NOT_FOUND


def _esv_part(part: str) -> object:
    """Text or NOT_FOUND from the ESV API; raises _Transient otherwise. Never cached."""
    key = _esv_key()
    if not key:
        raise _Transient("no_key")
    if not budget.try_acquire("esv"):
        raise _Transient("budget")
    params = {
        "q": part,
        "include-headings": "false",
        "include-footnotes": "false",
        "include-verse-numbers": "false",
        "include-passage-references": "false",
        "include-short-copyright": "true",   # keeps the required "(ESV)" credit
    }
    try:
        response = http.get(ESV_API_BASE, params=params,
                            headers={"Authorization": f"Token {key}"},
                            read_timeout=ESV_READ_TIMEOUT)
    except httpx.TimeoutException:
        raise _Transient("timeout") from None
    except httpx.HTTPError:
        raise _Transient("network") from None
    if response.status_code != 200:
        raise _Transient(f"status_{response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise _Transient("bad_json") from None
    passages = data.get("passages") if isinstance(data, dict) else None
    if passages is None:
        passages = []
    if not isinstance(passages, list):
        raise _Transient("bad_json")
    text = "\n\n".join(p.strip() for p in passages if isinstance(p, str) and p.strip())
    return text or NOT_FOUND


def fetch_part(part: str, translation: str) -> Part:
    """One normalized part: the cache (bible-api only), then the budget, then
    one upstream call. Never raises for an upstream failure (S Status rules)."""
    source = (TRANSLATIONS.get(translation) or (None, "bible-api"))[1]
    upstream = "esv" if source == "esv" else "bible_api"
    try:
        if upstream == "esv":
            result = _esv_part(part)
        else:
            result = _PART_CACHE.get_or_load(
                (translation, part.lower()), lambda: _bible_api_part(part, translation))
    except _Transient as exc:
        if exc.reason in _SKIP_REASONS:
            logger.info("passage_part_skipped reason=%s upstream=%s", exc.reason, upstream)
        else:
            logger.warning("passage_part_failed reason=%s upstream=%s", exc.reason, upstream)
        return Part(part, "unavailable", None)
    if result is NOT_FOUND:
        return Part(part, "not_found", None)
    return Part(part, "ok", result)


# --- statuses and texts (S Status rules; the one derivation) ---

def _combined_status(statuses: List[PartStatus]) -> PartStatus:
    """ok when every item is ok; else unavailable if any is; else not_found.
    No items at all is not_found, so an empty plan never reads as ok."""
    if statuses and all(s == "ok" for s in statuses):
        return "ok"
    if "unavailable" in statuses:
        return "unavailable"
    return "not_found"


def _joined(texts: List[Optional[str]]) -> Optional[str]:
    return "\n\n".join(t for t in texts if t) or None


def assemble_passage(reference: str, alternatives: List[str],
                     parts: List[List[Part]]) -> Passage:
    """Sections and passage from each alternative's fetched parts, in plan
    order. `alternatives` and `parts` come from the same plan_sections call."""
    sections = tuple(
        Section(
            reference=alternative,
            status=_combined_status([p.status for p in section_parts]),
            text=_joined([p.text for p in section_parts if p.status == "ok"]),
        )
        for alternative, section_parts in zip(alternatives, parts, strict=True)
    )
    return Passage(reference=reference,
                   status=_combined_status([s.status for s in sections]),
                   sections=sections)


def fetch_passage(reference: str, translation: str = DEFAULT_TRANSLATION) -> Passage:
    """Fetch every part of `reference`, one after another (no pool, no
    deadline; 2a clarification 27), and derive the statuses."""
    ref = reference.strip()
    sections = plan_sections(ref)
    parts = [[fetch_part(part, translation) for part in section_parts]
             for _alternative, section_parts in sections]
    return assemble_passage(ref, [alternative for alternative, _parts in sections], parts)


def get_passage_text(reference: str, translation: str = DEFAULT_TRANSLATION) -> Optional[str]:
    """The text of the `ok` sections joined with blank lines, or None. Never a
    sentinel (S; fixes inv. C9). usecases.passages re-exports it for slice 3."""
    passage = fetch_passage(reference, translation=translation)
    return _joined([s.text for s in passage.sections if s.status == "ok"])
```

Notes for the reviewer:
- Removed: `_reference_to_api_param` (the `%20`-only encoding, S "replaces … lines 65-69"), `_fetch_bible_api`, `_fetch_esv`, `_fetch_one_passage`, `_book_name_from_ref` and `_expand_part` (now `scripture_refs.split_parts`, Task 5), and the dict-returning `fetch_passage` with its `--- alt ---` text. `git grep` finds no caller of any of them outside this file; `fetch_passage` had no external caller (NB §7).
- `plan_sections` is an addition to the outline's interface: `assemble_passage` needs each section's reference, and `plan_parts` alone cannot say which alternatives it kept once an empty one is dropped. `plan_parts` is derived from it, so the two never disagree. (Owner decision 1; S names only `plan_parts`.)
- An empty plan is `not_found`, not `ok`: S's rule ("`ok` when every part is `ok`") would otherwise make zero parts an `ok` row with no text, the gap clarification 33 closes. The route never sends one (Task 10 rejects a ref with no parts); this covers direct callers such as slice 3's `get_passage_text("")`. (Owner decision 1.)
- ESV without a key is `unavailable` with no call and no token. Only an ESV id stored before the key was removed can reach it (Task 10 rejects the translation, and Task 11's profile falls back to "web"). Today it returns `None`, the same for a caller of `get_passage_text`. (Owner decision 1.)
- A bible-api 200 whose body is not a JSON object is `unavailable`; a 200 with empty text is `not_found` and cached (clarification 13). Status codes other than 200 and 404 (403, 429, 5xx) are `unavailable` (S Status rules).
- `_Transient` is raised inside the part-cache loader, so `TTLCache` stores nothing for it and every waiter of the same flight gets it (clarification 36); `fetch_part` turns it into `unavailable` and logs it. The budget token is taken inside the loader, so a cache hit takes none and one flight takes one token.
- `except httpx.TimeoutException` comes before `except httpx.HTTPError` (its base class), so a read timeout logs `reason=timeout`; Task 2's https-only refusal (`httpx.UnsupportedProtocol`) logs `reason=network`.
- Only `httpx.HTTPError` and a JSON `ValueError` are caught (clarification 18). Anything else, such as a test transport's `KeyError` for an unexpected URL, propagates, so a wrong URL fails loudly.

- [ ] **Step 6 (agent): Run the tests to verify they pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_scripture_fetcher.py 2>&1 | tail -3
```

**Expected:** `22 passed in <t>s`.

- [ ] **Step 7 (agent): Delete the replaced test file and extend the layering gate**

```bash
git rm -q backend/tests/test_scripture_translations.py
```

In `backend/tests/test_no_streamlit_in_core.py`, `test_usecases_package_imports_no_fastapi_or_streamlit`, replace the line

```python
            "token_bucket, integrations.budget, scripture_refs; "
```

with

```python
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher; "
```

(If Step 1 showed a different last line of that import list, add `, scripture_fetcher` at its end, before the closing `; "`, and change nothing else.) `scripture_fetcher` now imports `cache`, `integrations` and `scripture_refs`, so the gate checks that chain too.

```bash
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py streamlit_tests/test_settings_prompts_translation.py 2>&1 | tail -1
```

**Expected:** `6 passed in <t>s` (the gate file's 3 tests and the Streamlit translation file's 3). The gate is a guard, not a new test.

- [ ] **Step 8 (agent): Grep gates and the whole suite**

```bash
grep -nE 'httpx\.get|_cache = \{|Could not load text' backend/scripture_fetcher.py
grep -nE '^(import|from) ' backend/scripture_fetcher.py
git grep -n "test_scripture_translations" -- backend streamlit_tests .github
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected,** in order:
- nothing (AC3's grep target is gone from this module; T14 repeats it);
- exactly these ten lines:
  ```
  33:import logging
  34:import os
  35:import time
  36:from dataclasses import dataclass
  37:from typing import Dict, List, Literal, Optional, Tuple
  38:from urllib.parse import quote
  40:import httpx
  42:from cache import TTLCache
  43:from integrations import budget, http
  44:from scripture_refs import normalize_for_fetch, split_alternatives, split_joined, split_parts
  ```
- nothing (no file, workflow or test names the deleted file; only the specs and plans under `docs/` mention it);
- `938 passed, 9 skipped in <t>s` (921 + 22 − 5; `streamlit_tests/test_settings_prompts_translation.py` included);
- ```
   M backend/scripture_fetcher.py
   M backend/tests/conftest.py
   M backend/tests/test_no_streamlit_in_core.py
  D  backend/tests/test_scripture_translations.py
  ?? .claude/
  ?? backend/tests/test_scripture_fetcher.py
  ```

If the suite line is not `938 passed, 9 skipped`, stop and find why (each task's delta equals its listed tests). Run the new file twice more (`.venv/bin/python -m pytest -q backend/tests/test_scripture_fetcher.py 2>&1 | tail -1`, expected `22 passed` each time): it must not depend on the order of the process-wide budget or cache.

- [ ] **Step 9 (agent): Commit**

```bash
git add backend/scripture_fetcher.py backend/tests/test_scripture_fetcher.py \
        backend/tests/conftest.py backend/tests/test_no_streamlit_in_core.py
git commit -m "Passages: sections, statuses, part cache and budgets in scripture_fetcher (F §2.3.3, §2.7; S Passages; AC5)

fetch_passage returns a Passage of Sections, one per \" or \" alternative
(split in any case), with ok / not_found / unavailable derived once in
assemble_passage (S Status rules); get_passage_text returns the ok
sections' text or None, never a sentinel. plan_sections / plan_parts plan
each alternative into normalized parts (split_joined, split_parts,
normalize_for_fetch) and drop empty ones, so \";\" plans to nothing
(clarification 33); \"Isaiah 50:4-9a\" is fetched as /isaiah%2050:4-9.

fetch_part makes at most one call through integrations.http (10 s read).
bible-api parts use a 7-day TTLCache keyed by (translation, part.lower()); a
not-found is cached as NOT_FOUND; transient failures and budget misses are
raised in the loader as _Transient, so nothing transient is stored
(clarification 36). Every uncached part takes an integrations.budget token
first; ESV is never cached and without a key is unavailable with no call.
Logs carry the upstream and a reason only.

test_scripture_fetcher.py replaces test_scripture_translations.py (its 5
tests ported to the MockTransport seam, 17 new). conftest gains
_fresh_passage_cache, which also resets usecases.passages first once
Task 10 adds it (clarification 39). Public names used by streamlit_views
and frozen app.py are kept; ESV_API_KEY is still read from the environment
until slice 7.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> Passages: sections, statuses, part cache and budgets in scripture_fetcher (F §2.3.3, §2.7; S Passages; AC5)`; `git status --short` then lists only `?? .claude/`. (The deletion was staged by `git rm` in Step 7.)

- [ ] **Step 10 (agent): Review checkpoint**

Read `git show --stat HEAD` (5 files: 2 modified sources plus the gate, 1 added, 1 deleted) and `git show HEAD -- backend/scripture_fetcher.py`. Check against this task:
- every public name in S's list is still defined with the same signature (`TRANSLATIONS`, `DEFAULT_TRANSLATION`, `esv_configured()`, the zero-argument `available_translations()`, `translation_label()`, `get_passage_text()`), and `_esv_key()` still reads `ESV_API_KEY` at call time (the configuration exception T12 records);
- `_combined_status` and `assemble_passage` implement S's Status rules (S :284-287), and `get_passage_text` ignores non-`ok` sections;
- cache: `maxsize=2000`, `ttl_ok=604800`, `ttl_fail=0`, keyed `(translation, part.lower())` (the URL lower-cases the part, so one URL is one entry); ESV never touches it;
- the budget is taken inside the loader (cache hits take none) and through `budget.try_acquire` (Task 10 patches it);
- the URL is `f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"` with `params={"translation": t}`, and ESV's params are today's six with `q=` the normalized part;
- no log line carries a reference, body or query string.

AC5's domain half is pinned by `test_url_quotes_normalized_part` (the "a" dropped on the wire), the six status tests and `test_get_passage_text_none_never_sentinel_ignores_non_ok`; the route half is Task 10's. Task 12 corrects S Testing :890 for this: S says the ported assertions move to `respx`; Task 9 uses Task 2's `set_http_for_tests` + `httpx.MockTransport` seam instead (as Task 8 does; F §5 "injection over mocking"), and `respx` stays for Task 7.

Counts after Task 9: backend **938 passed, 9 skipped**; frontend **221 passed in 34 files** (unchanged; no route or schema change, so no OpenAPI regeneration).
### Task 10: `usecases/passages.py` and `POST /scripture/passages` (S Passages, API row 3, Rate-limit buckets `scripture`, Upstream budgets; F §1.8, §2.7; AC5, AC7, AC9; clarifications 33, 39)

This task puts T9's passage fetcher behind the API. `backend/usecases/passages.py` validates and plans a request (`plan_passages`, pure), loads it on one module-level `ThreadPoolExecutor(max_workers=4)` shared by every request with a 20 s deadline per request (`load_passages`), lists the translations (`translation_options`, used by T11) and re-exports `get_passage_text` for slice 3. `POST /scripture/passages` is the one route that charges its bucket itself (S; F §1.8): it plans (a 422 charges nothing), then calls `ratelimit.consume("scripture", user_id=user.id, cost=len(plan.parts))` (a 429 fetches nothing), then loads. Upstream failures never become 5xx; every passage and section carries its own status, derived once by T9's `assemble_passage`.

Test counts: `test_usecase_passages.py` has 9 tests and `test_api_scripture.py` has 13, so the backend goes from **938 to 960 passed, 9 skipped** (947 after the usecase half). The frontend stays at **221 passed in 34 files**; only the generated `openapi.json` and `schema.d.ts` change, and `npm run typecheck` stays green.

Every upstream call in these tests is answered by `httpx.MockTransport` installed with `integrations.http.set_http_for_tests(http.build_client(transport=...))`, T2's pattern, so the `_no_network` guard stays active (AC13) and no respx route is needed. Threaded tests gate the transport on a `threading.Event`, never on `time.sleep`, set it in `finally`, and join their threads (and, in the deadline test, the pool) before asserting (clarification 39).

Notes for the reviewer (each is owner decision 1; no owner-visible change):
- **`PassagePlan` gains a fifth field, `alternatives`** (after the outline's four, so their positions are unchanged). T9's `assemble_passage(reference, alternatives, parts)` needs the section names, and `plan_parts` drops an alternative with no parts (clarification 33: `"Psalm 23 or ;"` plans to one section), so `split_alternatives(ref)` alone could misalign with `plans[i]`. `_sections(ref)` uses T9's `plan_sections(ref)` (the pairs `plan_parts` is derived from), so `alternatives[i]` and `plans[i]` always line up, and `test_plan_parts_count` pins `plans[i] == scripture_fetcher.plan_parts(refs[i])`.
- **The pool reset is its own autouse fixture, `_fresh_passages_pool`,** placed with T3's and T7's blocks above the `# --- slice 1: network-free tests …` comment. T9's `_fresh_passage_cache` already calls `usecases.passages.reset_for_tests()` once this module exists, so this fixture is a deliberate, harmless duplicate (it joins an idle pool a second time) that keeps T10's pool reset visible in T10's own diff. `usecases.passages.reset_for_tests()` joins the pool and then calls `scripture_fetcher.reset_for_tests()` itself, so a straggling part can never write into the next test's part cache whichever order pytest runs the autouse fixtures in.
- **One log line is added:** `passages_deadline unfinished=<n> of=<m>` at WARNING when a request reaches its deadline. It carries counts only, never a reference or a translation (F §2.5).
- Module constants `REFS_MESSAGE`, `TOO_MANY_MESSAGE`, `TRANSLATION_MESSAGE` and `POOL_WORKERS = 4` are additive names.
- `PartStatus` is declared again in `api/schemas.py` (`Literal["ok", "not_found", "unavailable"]`), so the API models import nothing from the domain module; the OpenAPI enum is the one 2b consumes.
- These tests ran green (5 repeated runs of both new files) in a throwaway worktree against T2, T3 and T5's code taken from their plan parts and a stand-in for T9 written to the outline's T9 interface. If T9's real module differs from that interface (`Part(reference, status, text)`, `assemble_passage(reference, alternatives, parts)`, `plan_parts`, `fetch_part`, `reset_for_tests()`), adapt this task's calls, not the tests' expected JSON.

**Files:**
- Create: `backend/usecases/passages.py`
- Create: `backend/api/routes/scripture.py`
- Modify: `backend/api/schemas.py` (the `from pydantic import …` line; append the passages models after T8's `LectionaryOut`)
- Modify: `backend/api/main.py` (the `from api.routes import …` line; mount `scripture.router` after `lectionary.router`)
- Modify: `backend/tests/conftest.py` (a new autouse `_fresh_passages_pool` immediately above `# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---`)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (the layering import string gains `usecases.passages`)
- Modify: `backend/tests/test_route_guards.py` (docstring "2a:" line; `USER_SCOPED` gains `("POST", "/scripture/passages")`)
- Modify: `backend/tests/test_api_app.py` (`test_routes_document_the_error_body` map gains `("/scripture/passages", "post")`)
- Modify (generated): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`
- Test: `backend/tests/test_usecase_passages.py` (new, 9 tests), `backend/tests/test_api_scripture.py` (new, 13 tests)

**Interfaces:**
- Consumes:
  - T9, `scripture_fetcher`: `Part(reference: str, status: PartStatus, text: str | None)`, `Passage(reference, status, sections: tuple[Section, ...])` with `Section(reference, status, text)`; `plan_sections(reference: str) -> list[tuple[str, list[str]]]` (each alternative as written beside its normalized parts; drops alternatives and parts that are empty, so `";"` → `[]`) and `plan_parts(reference: str) -> list[list[str]]` (its parts only); `fetch_part(part: str, translation: str) -> Part` (cache, then `budget.try_acquire`, then one upstream call; never raises for an upstream failure); `assemble_passage(reference: str, alternatives: list[str], parts: list[list[Part]]) -> Passage`; `get_passage_text(reference, translation) -> str | None`; `reset_for_tests(clock=time.monotonic) -> None` (a new part-cache object); and the kept `DEFAULT_TRANSLATION = "web"`, `esv_configured()`, `available_translations() -> list[tuple[str, str]]`, `translation_label(tid) -> str`. The bible-api URL is `f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"` with `params={"translation": t}`, so a MockTransport handler sees the lower-cased part as `request.url.path[1:]` (httpx decodes `%20`).
  - T5's `scripture_refs` only through T9's `plan_sections` (this module does not import `scripture_refs`).
  - T3: `api.ratelimit.consume(bucket: str, *, user_id: uuid.UUID, church_id: uuid.UUID | None = None, cost: int = 1) -> None` (raises `domain_errors.RateLimited(MESSAGE.format(n=n), retry_after_seconds=n)`; `scripture` is 60 per 300 s, so one token returns every 5 s); `integrations.budget.try_acquire` (patched in two tests with `monkeypatch.setattr(budget, "try_acquire", lambda upstream: True)`, which works because T9 calls it through the module); conftest fixtures `limiter_clock` and `budget_clock` (each a `FakeClock`, never moved but by the test) and the autouse `_fresh_rate_limits`.
  - T2: `integrations.http.build_client(transport: httpx.BaseTransport | None = None) -> httpx.Client`, `set_http_for_tests(client | None)`, and the autouse `_fresh_http_client`.
  - T8: `api/schemas.py` already imports `Annotated` from `typing` and has `from pydantic import BaseModel, BeforeValidator, ConfigDict, Field`; `api/main.py` imports `lectionary` and mounts `lectionary.router` after `invites.router`; `test_route_guards.py` has the docstring line `2a: GET /lectionary/readings).` and `("GET", "/lectionary/readings"),` as `USER_SCOPED`'s last entry; `test_api_app.py`'s map ends with the `("/lectionary/readings", "get")` entry.
  - T7: the layering import string contains `usecases.onboarding, usecases.lectionary, vanderbilt_lectionary, `.
  - Slice 1: `domain_errors.InvalidInput(message, *, field=…)` (422 `invalid_request`; the handler puts `{field: message}` in `fields`); `api.deps.CurrentUser`, `get_current_user`; `api.errors.error_responses`; `tests.api_helpers.auth_headers`, `make_api_client`; `api.settings.get_settings.cache_clear()` (the CORS pattern of `test_api_app.py:73-84`); the Pydantic field messages "Not a valid value.", "Required.", "Too long (max N characters)." (`api/errors.py:108-114`).
- Produces:
  - `usecases.passages`:
    - `MAX_PARTS = 20`, `DEADLINE_SECONDS = 20.0`, `POOL_WORKERS = 4`, `REFS_MESSAGE = "Enter a scripture reference."`, `TOO_MANY_MESSAGE = "Too many passages in one request."`, `TRANSLATION_MESSAGE = "Unknown or unavailable translation."`
    - `PassagePlan(translation: str, refs: tuple[str, ...], plans: tuple[list[list[str]], ...], parts: tuple[str, ...], alternatives: tuple[tuple[str, ...], ...])`, a frozen dataclass. `len(plan.parts)` is the rate-limit cost, always 1–20.
    - `PassagesResult(translation: str, translation_label: str, passages: list[Passage])`, frozen.
    - `TranslationOptions(default: str, esv_available: bool, items: list[tuple[str, str]])`, frozen. T11's `GET /translations` builds `TranslationsOut` from it.
    - `plan_passages(refs: list[str], translation: str) -> PassagePlan`. Order: refs (no refs, a blank ref, or a ref with no parts → `InvalidInput(REFS_MESSAGE, field="refs")`), then translation (not in `available_translations()` → `InvalidInput(TRANSLATION_MESSAGE, field="translation")`), then parts (more than 20 → `InvalidInput(TOO_MANY_MESSAGE, field="refs")`).
    - `load_passages(plan: PassagePlan, *, deadline: float = DEADLINE_SECONDS) -> PassagesResult`: one flat `fetch_part` task list on `_POOL`, `concurrent.futures.wait(timeout=deadline)`, unfinished parts `Part(reference=part, status="unavailable", text=None)`, not-started futures cancelled, reassembled in order through `assemble_passage`.
    - `translation_options() -> TranslationOptions` (`default="web"`, `esv_available=esv_configured()`, `items=available_translations()`).
    - `get_passage_text = scripture_fetcher.get_passage_text` (the same object; slice 3's import path).
    - `reset_for_tests() -> None`: `_POOL.shutdown(wait=True, cancel_futures=True)`, a new pool, then `scripture_fetcher.reset_for_tests()`.
  - `api.schemas`: `PartStatus = Literal["ok", "not_found", "unavailable"]`; `PassagesIn` (`extra="forbid"`; `refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(max_length=4)`, required; `translation: str = Field(max_length=20)`, required); `PassageSectionOut(reference: str, status: PartStatus, text: Optional[str])` (`text` required and nullable, so `schema.d.ts` reads `text: string | null`); `PassageOut(reference: str, status: PartStatus, sections: list[PassageSectionOut])`; `PassagesOut(translation: str, translation_label: str, passages: list[PassageOut])`. 2b consumes the components `PassagesIn`, `PassagesOut`, `PassageOut` and `PassageSectionOut`.
  - Route: `POST /scripture/passages`, `@router.post("/scripture/passages", response_model=PassagesOut, responses=error_responses(401, 422, 429, 503))`, `def scripture_passages(payload: PassagesIn, user: CurrentUser = Depends(get_current_user)) -> PassagesOut`. 200 on success. User-scoped: X-Church-Id is ignored.
  - `backend/tests/conftest.py`: autouse `_fresh_passages_pool`.

- [ ] **Step 1 (agent): Check that T9 is in and find the anchors**

```bash
git status --short
git log --oneline -3
ls backend/usecases/passages.py backend/api/routes/scripture.py backend/tests/test_usecase_passages.py backend/tests/test_api_scripture.py 2>&1 | grep -c "No such file"
grep -n "^def plan_sections\|^def plan_parts\|^def fetch_part\|^def assemble_passage\|^def get_passage_text\|^def reset_for_tests\|^class Part\|^class Section\|^class Passage" backend/scripture_fetcher.py
grep -n "^from pydantic import\|^from typing import\|^class LectionaryOut" backend/api/schemas.py
grep -n "^from api.routes import\|include_router(lectionary.router)" backend/api/main.py
grep -n "2a: GET /lectionary/readings).\|(\"GET\", \"/lectionary/readings\")," backend/tests/test_route_guards.py
grep -n '("/lectionary/readings", "get")' backend/tests/test_api_app.py
grep -c "usecases.lectionary, " backend/tests/test_no_streamlit_in_core.py
grep -n "^# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---$" backend/tests/conftest.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `?? .claude/` only.
- T9's commit on top.
- `4` (none of this task's new files exist yet).
- One line each for `plan_sections`, `plan_parts`, `fetch_part`, `assemble_passage`, `get_passage_text` and `reset_for_tests`, and one `class` line each for `Part`, `Section` and `Passage`. Read the three classes and confirm the fields are `reference, status, text` (`Part`, `Section`) and `reference, status, sections` (`Passage`).
- `from typing import Annotated, Generic, Literal, Optional, TypeVar`, `from pydantic import BaseModel, BeforeValidator, ConfigDict, Field`, and one `class LectionaryOut(BaseModel):` line.
- `from api.routes import churches, health, invites, lectionary, me, rubric` and `    app.include_router(lectionary.router)`.
- Two lines in `test_route_guards.py`: `2a: GET /lectionary/readings).` and `    ("GET", "/lectionary/readings"),`.
- One line in `test_api_app.py`: `        ("/lectionary/readings", "get"): {"401", "422", "429", "502", "503", "504"},`.
- `1`.
- One conftest line number.
- `938 passed, 9 skipped in <t>s`.

If the count differs, stop and ask. If an anchor line differs only because an earlier task wrote it differently, apply this task's change to the line as it is (the intent of each edit is stated with it) and record that in the Step 13 review.

- [ ] **Step 2 (agent): Write the failing usecase tests**

Create `backend/tests/test_usecase_passages.py`:

```python
"""usecases.passages: validation, planning, the shared pool and the deadline
(S "Passages", Testing "test_usecase_passages.py"; AC5; 2a clarifications 33, 39).

Every upstream call is answered by httpx.MockTransport through
integrations.http.set_http_for_tests, so nothing leaves the process (the
_no_network guard stays active). Threaded tests gate the transport on a
threading.Event, never on time.sleep, set it in `finally`, and join their
threads and the pool before they assert.
"""
import logging
import threading
import time

import httpx
import pytest

import scripture_fetcher
from domain_errors import InvalidInput
from integrations import budget, http
from usecases import passages

REFS_MESSAGE = "Enter a scripture reference."
TOO_MANY_MESSAGE = "Too many passages in one request."
TRANSLATION_MESSAGE = "Unknown or unavailable translation."


def _ref(book: str, n: int) -> str:
    """'{book} 1:1; 1:2; …; 1:n': n parts, the book carried into each (split_parts)."""
    return "; ".join([f"{book} 1:1"] + [f"1:{verse}" for verse in range(2, n + 1)])


def _install(handler) -> None:
    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(handler)))


def _text_of(request: httpx.Request) -> httpx.Response:
    """bible-api's shape: the decoded path, lower-cased by fetch_part, becomes the text."""
    return httpx.Response(200, json={"text": f"Text of {request.url.path[1:]}."})


@pytest.fixture(autouse=True)
def _no_esv_key(monkeypatch):
    """ESV is offered only with a key; these tests set one where they need it."""
    monkeypatch.delenv("ESV_API_KEY", raising=False)


def _invalid(refs, translation="web") -> InvalidInput:
    with pytest.raises(InvalidInput) as caught:
        passages.plan_passages(refs, translation)
    return caught.value


def test_empty_refs_and_blank_ref():
    for refs in ([], ["John 3:16", "   "], [""], [";"], [" ; "], ["John 3:16", "; ;"]):
        error = _invalid(refs)
        assert (error.field, error.message, error.code) == ("refs", REFS_MESSAGE, "invalid_request"), refs
    # refs are checked before the translation
    assert _invalid([], "klingon").field == "refs"


def test_twenty_one_parts_too_many():
    twenty = [_ref("Genesis", 5), _ref("Exodus", 5), _ref("Leviticus", 5), _ref("Numbers", 5)]
    assert len(passages.plan_passages(twenty, "web").parts) == passages.MAX_PARTS == 20
    twenty_one = twenty[:3] + [_ref("Numbers", 6)]
    error = _invalid(twenty_one)
    assert (error.field, error.message) == ("refs", TOO_MANY_MESSAGE)
    # alternatives count too: 20 parts plus one alternative's part
    error = _invalid(twenty[:3] + [_ref("Numbers", 5) + " or Mark 1:1"])
    assert (error.field, error.message) == ("refs", TOO_MANY_MESSAGE)


def test_unknown_or_unavailable_translation(monkeypatch):
    for translation in ("klingon", "esv", "WEB", ""):
        error = _invalid(["John 3:16"], translation)
        assert (error.field, error.message) == ("translation", TRANSLATION_MESSAGE), translation
    # the translation is checked before the part count
    too_many = [_ref("Genesis", 6), _ref("Exodus", 5), _ref("Leviticus", 5), _ref("Numbers", 5)]
    assert _invalid(too_many, "klingon").field == "translation"

    monkeypatch.setenv("ESV_API_KEY", "test-key")
    assert passages.plan_passages(["John 3:16"], "esv").translation == "esv"


def test_plan_parts_count():
    refs = ["  Romans 6:3-11 and Psalm 114 or Isaiah 50:4-9a; 51:1-3  ", "John 3:16", "Psalm 23 or ;"]
    plan = passages.plan_passages(refs, "kjv")

    assert plan.translation == "kjv"
    assert plan.refs == ("Romans 6:3-11 and Psalm 114 or Isaiah 50:4-9a; 51:1-3", "John 3:16", "Psalm 23 or ;")
    assert plan.alternatives == (
        ("Romans 6:3-11 and Psalm 114", "Isaiah 50:4-9a; 51:1-3"),
        ("John 3:16",),
        ("Psalm 23",),                       # the ";" alternative has no parts, so it is no section
    )
    assert plan.plans == (
        [["Romans 6:3-11", "Psalm 114"], ["Isaiah 50:4-9", "Isaiah 51:1-3"]],
        [["John 3:16"]],
        [["Psalm 23"]],
    )
    assert plan.plans == tuple(scripture_fetcher.plan_parts(ref) for ref in plan.refs)
    # alternatives × joined × ";" parts: the cost the route charges
    assert plan.parts == ("Romans 6:3-11", "Psalm 114", "Isaiah 50:4-9", "Isaiah 51:1-3", "John 3:16", "Psalm 23")


def test_order_preserved():
    """The first ref's part answers last, yet it stays first."""
    last_seen = threading.Event()

    def handler(request):
        if "john" in request.url.path:
            last_seen.wait(timeout=5)
        if "psalm" in request.url.path:
            last_seen.set()
        return _text_of(request)

    _install(handler)
    plan = passages.plan_passages(["John 3:16", "Genesis 1:1", "Psalm 23"], "web")
    try:
        result = passages.load_passages(plan)
    finally:
        last_seen.set()

    assert (result.translation, result.translation_label) == ("web", "World English Bible (WEB)")
    assert [(p.reference, p.status, p.sections[0].text) for p in result.passages] == [
        ("John 3:16", "ok", "Text of john 3:16."),
        ("Genesis 1:1", "ok", "Text of genesis 1:1."),
        ("Psalm 23", "ok", "Text of psalm 23."),
    ]


def test_two_concurrent_requests_never_exceed_four_in_flight(monkeypatch):
    """24 distinct parts (so the part cache's single flight merges none) from
    two requests at once: the shared pool keeps at most 4 upstream calls in
    flight. The budget is patched open, or the process-wide 15 per 30 s
    bible-api budget would answer 9 parts `unavailable` without a call."""
    monkeypatch.setattr(budget, "try_acquire", lambda upstream: True)
    changed = threading.Condition()
    state = {"in_flight": 0, "peak": 0, "calls": 0}
    release = threading.Event()

    def handler(request):
        with changed:
            state["in_flight"] += 1
            state["calls"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
            changed.notify_all()
        try:
            release.wait(timeout=10)
            return _text_of(request)
        finally:
            with changed:
                state["in_flight"] -= 1

    _install(handler)
    plans = [
        passages.plan_passages([_ref(book, 3) for book in ("Genesis", "Exodus", "Leviticus", "Numbers")], "web"),
        passages.plan_passages([_ref(book, 3) for book in ("Joshua", "Judges", "Ruth", "Esther")], "web"),
    ]
    assert len(set(plans[0].parts + plans[1].parts)) == 24
    results: dict[int, passages.PassagesResult] = {}

    def run(index: int) -> None:
        results[index] = passages.load_passages(plans[index])

    threads = [threading.Thread(target=run, args=(index,)) for index in (0, 1)]
    try:
        for thread in threads:
            thread.start()
        with changed:
            assert changed.wait_for(lambda: state["in_flight"] == 4, timeout=5)
        release.set()
        for thread in threads:
            thread.join(timeout=10)
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=10)

    assert state["peak"] == 4
    assert state["calls"] == 24
    for index in (0, 1):
        assert [p.status for p in results[index].passages] == ["ok"] * 4
        assert [p.reference for p in results[index].passages] == list(plans[index].refs)


def test_deadline_unfinished_unavailable_and_cancelled(monkeypatch, caplog):
    """Two requests of 4 parts share 4 workers that never finish: at a 0.2 s
    deadline both answer, every part `unavailable`, and the 4 parts still
    queued are cancelled, so they never reach the transport."""
    monkeypatch.setattr(budget, "try_acquire", lambda upstream: True)
    caplog.set_level(logging.WARNING, logger="usecases.passages")
    release = threading.Event()
    calls: list[str] = []
    lock = threading.Lock()

    def handler(request):
        with lock:
            calls.append(request.url.path)
        release.wait(timeout=10)
        return _text_of(request)

    _install(handler)
    plans = [passages.plan_passages([_ref("Genesis", 4)], "web"),
             passages.plan_passages([_ref("Exodus", 4)], "web")]
    results: dict[int, passages.PassagesResult] = {}
    elapsed: dict[int, float] = {}

    def run(index: int) -> None:
        started = time.monotonic()
        results[index] = passages.load_passages(plans[index], deadline=0.2)
        elapsed[index] = time.monotonic() - started

    threads = [threading.Thread(target=run, args=(index,)) for index in (0, 1)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=5)
        passages.reset_for_tests()        # joins the pool: the 4 running parts finish, cancelled ones never run

    for index in (0, 1):
        assert elapsed[index] < 0.2 + 0.5
        passage = results[index].passages[0]
        assert (passage.status, passage.sections[0].status, passage.sections[0].text) == (
            "unavailable", "unavailable", None)
    assert len(calls) == 4
    assert [r.getMessage() for r in caplog.records if r.name == "usecases.passages"] == [
        "passages_deadline unfinished=4 of=4"] * 2


def test_translation_options(monkeypatch):
    options = passages.translation_options()
    assert (options.default, options.esv_available) == ("web", False)
    assert options.items == scripture_fetcher.available_translations()
    assert [tid for tid, _label in options.items] == [
        "web", "kjv", "asv", "ylt", "dra", "darby", "bbe", "oeb-us", "webbe"]

    monkeypatch.setenv("ESV_API_KEY", "test-key")
    options = passages.translation_options()
    assert options.esv_available is True
    assert options.items[-1] == ("esv", "English Standard Version (ESV)")


def test_get_passage_text_reexported():
    assert passages.get_passage_text is scripture_fetcher.get_passage_text

    def handler(request):
        if "nahum" in request.url.path:
            return httpx.Response(404, json={"error": "not found"})
        return _text_of(request)

    _install(handler)
    assert passages.get_passage_text("John 3:16", "web") == "Text of john 3:16."
    assert passages.get_passage_text("Nahum 9:9", "web") is None
```

In `backend/tests/conftest.py`, insert this block immediately above the line
`# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---` (below T3's, T7's and T9's blocks), and end it with two blank lines before that comment:

```python
# --- slice 2a: the passages pool (S "Passages"; clarification 39) ---

@pytest.fixture(autouse=True)
def _fresh_passages_pool():
    """usecases.passages runs every part on one module-level pool. Each test
    starts with that pool joined (a part blocked by an earlier test's event
    has finished) and replaced, and with a new part cache, which
    reset_for_tests() rebuilds after the join, so no straggler writes into
    this test's cache whatever order the autouse fixtures run in.

    Resets only when usecases.passages is already imported (the
    deferred-import rule at the top of this file)."""
    import sys

    passages = sys.modules.get("usecases.passages")
    if passages is not None:
        passages.reset_for_tests()
    yield
```

In `backend/tests/test_no_streamlit_in_core.py`, in `test_usecases_package_imports_no_fastapi_or_streamlit`, replace the one occurrence of the text

```
usecases.lectionary, 
```

with

```
usecases.lectionary, usecases.passages, 
```

leaving the rest of that import string unchanged.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_passages.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_usecase_passages.py 2>&1 | grep -m1 '^E '
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected:**
- `ERROR backend/tests/test_usecase_passages.py`, `!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!`, `1 error in <t>s`;
- `E   ImportError: cannot import name 'passages' from 'usecases' (…/backend/usecases/__init__.py)`;
- `1 failed, 2 passed in <t>s` (the layering subprocess cannot import `usecases.passages`).

- [ ] **Step 4 (agent): Write `backend/usecases/passages.py`**

```python
"""Passage text for the readings step (S "Passages", API row 3; F §1.8, §2.7; slice 2a).

plan_passages validates and plans; it is pure, so the route can charge the
`scripture` bucket one token per upstream part (len(plan.parts)) before any
work, and a 422 charges nothing. load_passages then fetches every part of
every ref on one module-level pool shared by all requests, with a deadline
per request: a part not finished by then is `unavailable`, and a part that
has not started is cancelled. So a request answers within ~20 s however
busy the pool is, inside the client's 30 s timeout (S :315).

The part, section and passage statuses are derived once, by
scripture_fetcher.assemble_passage; get_passage_text (slice 3) is
scripture_fetcher's, re-exported under the same name.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py). Exact
messages come from DomainErrors (usecases/__init__.py).
"""
import logging
from concurrent.futures import Future, ThreadPoolExecutor, wait
from dataclasses import dataclass

import scripture_fetcher
from domain_errors import InvalidInput
from scripture_fetcher import Part, Passage

logger = logging.getLogger(__name__)

MAX_PARTS = 20
DEADLINE_SECONDS = 20.0
POOL_WORKERS = 4

REFS_MESSAGE = "Enter a scripture reference."
TOO_MANY_MESSAGE = "Too many passages in one request."
TRANSLATION_MESSAGE = "Unknown or unavailable translation."

# Slice 3 imports it from here (S Hand-offs row 3).
get_passage_text = scripture_fetcher.get_passage_text

_POOL = ThreadPoolExecutor(max_workers=POOL_WORKERS, thread_name_prefix="passages")


@dataclass(frozen=True)
class PassagePlan:
    """The validated request. `plans[i]` is scripture_fetcher.plan_parts(refs[i]):
    one list of parts per alternative that has parts, and `alternatives[i]` names
    those alternatives, index for index. `parts` is every part of every
    alternative of every ref, in order; its length is the rate-limit cost."""

    translation: str
    refs: tuple[str, ...]
    plans: tuple[list[list[str]], ...]
    parts: tuple[str, ...]
    alternatives: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class PassagesResult:
    translation: str
    translation_label: str
    passages: list[Passage]          # same order as the plan's refs


@dataclass(frozen=True)
class TranslationOptions:
    default: str
    esv_available: bool
    items: list[tuple[str, str]]     # (id, label), scripture_fetcher.TRANSLATIONS order


def _sections(ref: str) -> tuple[tuple[str, ...], list[list[str]]]:
    """The alternatives of `ref` that have parts, and their parts.

    scripture_fetcher.plan_sections drops an alternative with no parts (";"),
    so alternatives[i] always names plan[i], and plan == plan_parts(ref)."""
    sections = scripture_fetcher.plan_sections(ref)
    return tuple(alternative for alternative, _parts in sections), [parts for _alternative, parts in sections]


def plan_passages(refs: list[str], translation: str) -> PassagePlan:
    """Check the request and plan it (S "plan_passages"). Checks run in this
    order: refs, then translation, then the part count.

    - no refs, a blank ref, or a ref with no parts (";") → "Enter a scripture
      reference." on `refs`, so the cost is always at least 1 (2a clarification 33);
    - a translation this deployment does not offer (ESV without its key) →
      "Unknown or unavailable translation." on `translation`;
    - more than MAX_PARTS parts in all → "Too many passages in one request." on `refs`.
    """
    trimmed = tuple(ref.strip() for ref in refs)
    if not trimmed or any(not ref for ref in trimmed):
        raise InvalidInput(REFS_MESSAGE, field="refs")
    planned = [_sections(ref) for ref in trimmed]
    if any(not plan for _alternatives, plan in planned):
        raise InvalidInput(REFS_MESSAGE, field="refs")
    if translation not in {tid for tid, _label in scripture_fetcher.available_translations()}:
        raise InvalidInput(TRANSLATION_MESSAGE, field="translation")
    parts = tuple(part for _alternatives, plan in planned for section in plan for part in section)
    if len(parts) > MAX_PARTS:
        raise InvalidInput(TOO_MANY_MESSAGE, field="refs")
    return PassagePlan(
        translation=translation,
        refs=trimmed,
        plans=tuple(plan for _alternatives, plan in planned),
        parts=parts,
        alternatives=tuple(alternatives for alternatives, _plan in planned),
    )


def _part_result(future: Future, part: str) -> Part:
    """A finished part's own result; an unfinished or cancelled one is `unavailable`.

    fetch_part never raises for an upstream failure, so an exception here is
    a bug, and result() lets it surface as a 500."""
    if future.done() and not future.cancelled():
        return future.result()
    return Part(reference=part, status="unavailable", text=None)


def load_passages(plan: PassagePlan, *, deadline: float = DEADLINE_SECONDS) -> PassagesResult:
    """Fetch every part of the plan on the shared pool and reassemble in order.

    The tasks are one flat list (no nested submission to the same pool, which
    could deadlock). After `deadline` seconds, unfinished parts are
    `unavailable` and parts not yet started are cancelled; a running part
    finishes in the background, and its own cache entry (if any) still helps
    the next request. The deadline is counted from submission; planning and
    the rate-limit charge before it take microseconds."""
    futures = [_POOL.submit(scripture_fetcher.fetch_part, part, plan.translation) for part in plan.parts]
    _done, not_done = wait(futures, timeout=deadline)
    for future in not_done:
        future.cancel()
    if not_done:
        logger.warning("passages_deadline unfinished=%d of=%d", len(not_done), len(futures))
    results = iter([_part_result(future, part) for future, part in zip(futures, plan.parts)])
    passages = []
    for ref, alternatives, sections in zip(plan.refs, plan.alternatives, plan.plans):
        parts = [[next(results) for _part in section] for section in sections]
        passages.append(scripture_fetcher.assemble_passage(ref, list(alternatives), parts))
    return PassagesResult(
        translation=plan.translation,
        translation_label=scripture_fetcher.translation_label(plan.translation),
        passages=passages,
    )


def translation_options() -> TranslationOptions:
    """What GET /translations offers: "web" by default, ESV only when its key is set."""
    return TranslationOptions(
        default=scripture_fetcher.DEFAULT_TRANSLATION,
        esv_available=scripture_fetcher.esv_configured(),
        items=scripture_fetcher.available_translations(),
    )


def reset_for_tests() -> None:
    """Join the pool, then start a new one and a new part cache (2a clarification 39).

    Joining first lets a straggler from an earlier test (a part blocked on a
    test's event) finish before the part cache is rebuilt, so it cannot write
    into the next test's cache. Called by an autouse fixture in tests/conftest.py."""
    global _POOL
    _POOL.shutdown(wait=True, cancel_futures=True)
    _POOL = ThreadPoolExecutor(max_workers=POOL_WORKERS, thread_name_prefix="passages")
    scripture_fetcher.reset_for_tests()
```

- [ ] **Step 5 (agent): Run the usecase tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_passages.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
grep -n "fastapi\|starlette\|streamlit" backend/usecases/passages.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `12 passed in <t>s` (9 + 3); the grep prints nothing; `947 passed, 9 skipped in <t>s`.

- [ ] **Step 6 (agent): Write the failing API tests and the allowlist entries**

Create `backend/tests/test_api_scripture.py`:

```python
"""POST /scripture/passages over HTTP (S API row 3, Status rules, Rate-limit
buckets `scripture`, Upstream budgets, Testing "test_api_scripture.py"; AC5, AC7, AC9).

Upstream calls are answered by httpx.MockTransport through
integrations.http.set_http_for_tests (the _no_network guard stays active).
Rate-limit tests take `limiter_clock` (a FakeClock) and never advance it
during a burst, so every wait is exact: one `scripture` token comes back
every 5 s.
"""
import httpx
import pytest

from api import settings as settings_mod
from integrations import http
from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"
ALLOWED_ORIGIN = "https://church.example.app"
PATH = "/scripture/passages"


def _ref(book: str, n: int) -> str:
    """'{book} 1:1; 1:2; …; 1:n': n parts, the book carried into each (split_parts)."""
    return "; ".join([f"{book} 1:1"] + [f"1:{verse}" for verse in range(2, n + 1)])


TWENTY_PARTS = [_ref("Genesis", 5), _ref("Exodus", 5), _ref("Leviticus", 5), _ref("Numbers", 5)]
TWENTY_ONE_PARTS = TWENTY_PARTS[:3] + [_ref("Numbers", 6)]


@pytest.fixture(autouse=True)
def _no_esv_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)


@pytest.fixture
def calls():
    """Install a bible-api fake and return the decoded paths it was asked for.

    Nahum is not in the fake's Bible (404); chapter 99 is a server error (500);
    anything else is "Text of {path}."."""
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path[1:]
        seen.append(path)
        if "nahum" in path:
            return httpx.Response(404, json={"error": "not found"})
        if " 99:" in path:
            return httpx.Response(500)
        return httpx.Response(200, json={"text": f"Text of {path}."})

    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(handler)))
    return seen


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def cors_client(tmp_db, monkeypatch):
    """A client whose app allows exactly ALLOWED_ORIGIN (test_api_app's pattern)."""
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    yield make_api_client()
    settings_mod.get_settings.cache_clear()


def _post(client, refs, translation="web", email=EMAIL, **extra):
    return client.post(PATH, json={"refs": refs, "translation": translation, **extra},
                       headers=auth_headers(email))


def _invalid(response) -> dict:
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    return error


def _assert_rate_limited(response, seconds: int) -> None:
    assert response.status_code == 429, response.text
    error = response.json()["error"]
    assert (error["code"], error["message"]) == (
        "rate_limited", f"Too many requests. Try again in {seconds} seconds.")
    assert error["details"] == {"retry_after_seconds": seconds}
    assert response.headers["Retry-After"] == str(seconds)
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_requires_token_401(client, calls):
    r = client.post(PATH, json={"refs": ["John 3:16"], "translation": "web"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"
    assert calls == []


def test_200_statuses(client, calls):
    refs = ["  John 3:16  ", "Nahum 9:9", "Luke 1:1-4; 99:1 or Mark 1:1", "Isaiah 50:4-9a; Nahum 1:1"]
    r = _post(client, refs)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "translation": "web",
        "translation_label": "World English Bible (WEB)",
        "passages": [
            {"reference": "John 3:16", "status": "ok",
             "sections": [{"reference": "John 3:16", "status": "ok", "text": "Text of john 3:16."}]},
            {"reference": "Nahum 9:9", "status": "not_found",
             "sections": [{"reference": "Nahum 9:9", "status": "not_found", "text": None}]},
            {"reference": "Luke 1:1-4; 99:1 or Mark 1:1", "status": "unavailable",
             "sections": [
                 {"reference": "Luke 1:1-4; 99:1", "status": "unavailable", "text": "Text of luke 1:1-4."},
                 {"reference": "Mark 1:1", "status": "ok", "text": "Text of mark 1:1."}]},
            {"reference": "Isaiah 50:4-9a; Nahum 1:1", "status": "not_found",
             "sections": [{"reference": "Isaiah 50:4-9a; Nahum 1:1", "status": "not_found",
                           "text": "Text of isaiah 50:4-9."}]},
        ],
    }
    assert sorted(calls) == sorted(["john 3:16", "nahum 9:9", "luke 1:1-4", "luke 99:1", "mark 1:1",
                                    "isaiah 50:4-9", "nahum 1:1"])


def test_422_five_refs(client, calls):
    error = _invalid(_post(client, ["John 3:16"] * 5))
    assert error["fields"] == {"refs": "Not a valid value."}


def test_422_ref_201_chars(client, calls):
    error = _invalid(_post(client, ["J" * 201]))
    assert error["fields"] == {"refs.0": "Too long (max 200 characters)."}
    assert _post(client, ["John 3:16"], translation="x" * 21).json()["error"]["fields"] == {
        "translation": "Too long (max 20 characters)."}


def test_422_empty_refs(client, calls):
    error = _invalid(_post(client, []))
    assert error["message"] == "Enter a scripture reference."
    assert error["fields"] == {"refs": "Enter a scripture reference."}


def test_422_blank_ref(client, calls):
    for refs in (["John 3:16", "   "], [";"], [" ; "]):
        error = _invalid(_post(client, refs))
        assert error["fields"] == {"refs": "Enter a scripture reference."}, refs
    assert calls == []


def test_422_twenty_one_parts(client, calls):
    error = _invalid(_post(client, TWENTY_ONE_PARTS))
    assert error["message"] == "Too many passages in one request."
    assert error["fields"] == {"refs": "Too many passages in one request."}
    assert calls == []


def test_422_unknown_translation(client, calls):
    for translation in ("klingon", "esv"):             # ESV without its key is unavailable
        error = _invalid(_post(client, ["John 3:16"], translation=translation))
        assert error["fields"] == {"translation": "Unknown or unavailable translation."}, translation


def test_422_extra_field(client, calls):
    error = _invalid(_post(client, ["John 3:16"], church_id="x"))
    assert error["fields"] == {"church_id": "Not a valid value."}
    missing = _invalid(client.post(PATH, json={"refs": ["John 3:16"]}, headers=auth_headers(EMAIL)))
    assert missing["fields"] == {"translation": "Required."}


def test_61st_one_part_call_429(cors_client, calls, limiter_clock):
    """60 parts per 5 minutes: the 61st one-part call waits 5 s for one token.
    Only the first call reaches bible-api (the rest are cache hits), and the
    429 fetches nothing."""
    headers = {**auth_headers(EMAIL), "Origin": ALLOWED_ORIGIN}
    body = {"refs": ["John 3:16"], "translation": "web"}
    for n in range(60):
        assert cors_client.post(PATH, json=body, headers=headers).status_code == 200, n
    _assert_rate_limited(cors_client.post(PATH, json=body, headers=headers), 5)
    assert calls == ["john 3:16"]


def test_21st_three_part_call_429(cors_client, calls, limiter_clock):
    """Charged per part: after 20 three-part calls the 21st needs 3 tokens, 15 s."""
    headers = {**auth_headers(EMAIL), "Origin": ALLOWED_ORIGIN}
    body = {"refs": [_ref("Genesis", 3)], "translation": "web"}
    for n in range(20):
        assert cors_client.post(PATH, json=body, headers=headers).status_code == 200, n
    _assert_rate_limited(cors_client.post(PATH, json=body, headers=headers), 15)

    limiter_clock.advance(15)
    assert cors_client.post(PATH, json=body, headers=headers).status_code == 200


def test_budget_shared_across_users(client, calls, budget_clock):
    """The bible-api budget (15 per 30 s) is process-wide (S :892): user A's 15
    parts spend it, so user B's uncached part is `unavailable` with no upstream
    call, while a part A already loaded is still served from the cache."""
    a_refs = [_ref("Genesis", 4), _ref("Exodus", 4), _ref("Leviticus", 4), _ref("Numbers", 3)]
    a = _post(client, a_refs, email="a@example.com")
    assert a.status_code == 200, a.text
    assert [p["status"] for p in a.json()["passages"]] == ["ok"] * 4
    assert len(calls) == 15

    b = _post(client, ["Ruth 1:1", "Genesis 1:1"], email="b@example.com")
    assert b.status_code == 200, b.text
    ruth, genesis = b.json()["passages"]
    assert ruth == {"reference": "Ruth 1:1", "status": "unavailable",
                    "sections": [{"reference": "Ruth 1:1", "status": "unavailable", "text": None}]}
    assert genesis["status"] == "ok"
    assert genesis["sections"][0]["text"] == "Text of genesis 1:1."
    assert len(calls) == 15                              # nothing sent for B

    budget_clock.advance(2)                              # one bible-api token back (15 per 30 s)
    assert _post(client, ["Ruth 1:1"], email="b@example.com").json()["passages"][0]["status"] == "ok"
    assert calls[-1] == "ruth 1:1"


def test_422_charges_nothing(cors_client, calls, limiter_clock):
    """Validation runs before the charge: after one of each 422, the whole 60
    tokens are still there (three 20-part calls), and only then is a call 429."""
    headers = {**auth_headers(EMAIL), "Origin": ALLOWED_ORIGIN}
    invalid_bodies = [
        {"refs": ["John 3:16"] * 5, "translation": "web"},          # Pydantic: more than 4 refs
        {"refs": ["J" * 201], "translation": "web"},                # Pydantic: a ref over 200 characters
        {"refs": ["John 3:16"], "translation": "web", "extra": 1},  # Pydantic: extra="forbid"
        {"refs": [], "translation": "web"},                         # usecase: no refs
        {"refs": [";"], "translation": "web"},                      # usecase: a ref with no parts
        {"refs": ["John 3:16"], "translation": "klingon"},          # usecase: translation
        {"refs": TWENTY_ONE_PARTS, "translation": "web"},           # usecase: 21 parts
    ]
    for body in invalid_bodies:
        assert cors_client.post(PATH, json=body, headers=headers).status_code == 422, body
    assert calls == []

    for n in range(3):
        r = cors_client.post(PATH, json={"refs": TWENTY_PARTS, "translation": "web"}, headers=headers)
        assert r.status_code == 200, (n, r.text)
    _assert_rate_limited(
        cors_client.post(PATH, json={"refs": ["John 3:16"], "translation": "web"}, headers=headers), 5)
```

In `backend/tests/test_route_guards.py`, replace the docstring line

```python
2a: GET /lectionary/readings).
```

with

```python
2a: GET /lectionary/readings, POST /scripture/passages).
```

and replace the end of `USER_SCOPED`

```python
    ("GET", "/lectionary/readings"),
}
```

with

```python
    ("GET", "/lectionary/readings"),
    ("POST", "/scripture/passages"),
}
```

In `backend/tests/test_api_app.py`, inside `test_routes_document_the_error_body`, replace

```python
        ("/lectionary/readings", "get"): {"401", "422", "429", "502", "503", "504"},
```

with

```python
        ("/lectionary/readings", "get"): {"401", "422", "429", "502", "503", "504"},
        ("/scripture/passages", "post"): {"401", "422", "429", "503"},
```

- [ ] **Step 7 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_scripture.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_api_scripture.py 2>&1 | grep -m2 '^E '
.venv/bin/python -m pytest -q backend/tests/test_route_guards.py backend/tests/test_api_app.py 2>&1 | grep '^FAILED'
```

**Expected:**
- `13 failed in <t>s` (the route does not exist, so every request is a 404);
- `E       assert 404 == 401` and `E        +  where 404 = <Response [404 Not Found]>.status_code`;
- three `FAILED` lines: `test_route_guards.py::test_user_scoped_routes_require_a_user`, `test_route_guards.py::test_allowlists_name_real_routes`, and `test_api_app.py::test_routes_document_the_error_body` (`KeyError: '/scripture/passages'`).

- [ ] **Step 8 (agent): Add the schemas, the route and the mount**

In `backend/api/schemas.py`, replace

```python
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
```

with

```python
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints
```

and append this at the end of the file, after T8's `LectionaryOut` (two blank lines before it):

```python
# --- slice 2a: passages (S Schemas; POST /scripture/passages) ---

PartStatus = Literal["ok", "not_found", "unavailable"]


class PassagesIn(BaseModel):
    """POST /scripture/passages. An empty list, a blank ref and more than 20
    parts in all are the usecase's 422s, with its exact messages (S Schemas)."""

    model_config = ConfigDict(extra="forbid")

    refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(max_length=4)   # the UI sends 1
    translation: str = Field(max_length=20)


class PassageSectionOut(BaseModel):
    """One " or " alternative: `ok` only when every part loaded; `text` joins the
    parts that did, or is null when none did (S Status rules)."""

    reference: str
    status: PartStatus
    text: Optional[str]


class PassageOut(BaseModel):
    """One ref as sent (trimmed), with every section, whatever loaded."""

    reference: str
    status: PartStatus
    sections: list[PassageSectionOut]


class PassagesOut(BaseModel):
    translation: str
    translation_label: str
    passages: list[PassageOut]          # same order as the request's refs
```

Create `backend/api/routes/scripture.py`:

```python
"""POST /scripture/passages (S API row 3, "Passages", Rate-limit buckets
`scripture`; F §1.8; slice 2a).

The one route that charges its bucket itself, because the cost is the number
of upstream parts and is known only after validation (S; F §1.8). It plans
(a 422 charges nothing), then consumes one `scripture` token per part (a 429
fetches nothing), then loads. Upstream failures never become 5xx: every
passage and section carries its own status. X-Church-Id is ignored.
"""
from fastapi import APIRouter, Depends

from api import ratelimit
from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import PassageOut, PassageSectionOut, PassagesIn, PassagesOut
from usecases.passages import load_passages, plan_passages

router = APIRouter()


@router.post("/scripture/passages", response_model=PassagesOut,
             responses=error_responses(401, 422, 429, 503))
def scripture_passages(payload: PassagesIn, user: CurrentUser = Depends(get_current_user)) -> PassagesOut:
    plan = plan_passages(payload.refs, payload.translation)
    ratelimit.consume("scripture", user_id=user.id, cost=len(plan.parts))
    result = load_passages(plan)
    return PassagesOut(
        translation=result.translation,
        translation_label=result.translation_label,
        passages=[
            PassageOut(
                reference=passage.reference,
                status=passage.status,
                sections=[PassageSectionOut(reference=s.reference, status=s.status, text=s.text)
                          for s in passage.sections],
            )
            for passage in result.passages
        ],
    )
```

In `backend/api/main.py`, replace

```python
from api.routes import churches, health, invites, lectionary, me, rubric
```

with

```python
from api.routes import churches, health, invites, lectionary, me, rubric, scripture
```

and replace

```python
    app.include_router(lectionary.router)
```

with

```python
    app.include_router(lectionary.router)
    app.include_router(scripture.router)
```

- [ ] **Step 9 (agent): Run the API tests; the snapshot is now stale**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_scripture.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
```

**Expected:** `47 passed, 1 skipped in <t>s` (13 new, plus the 34 passed and 1 skipped the other three files already had; the skip is an existing Postgres-only test); `1 failed, 2 passed in <t>s` for the contract (`test_committed_openapi_matches_the_live_schema`: "frontend/src/lib/api/openapi.json is stale").

- [ ] **Step 10 (agent): Regenerate the OpenAPI files and typecheck**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
(cd frontend && npm run typecheck)
git diff --stat -- frontend/src/lib/api/
grep -n "PassageSectionOut: {" -A10 frontend/src/lib/api/schema.d.ts | grep "status:\|text:"
```

**Expected:**
- `Wrote …/frontend/src/lib/api/openapi.json`, then openapi-typescript's success line for `src/lib/api/schema.d.ts`;
- `tsc --noEmit` with no errors;
- both files changed, additions only (the path `/scripture/passages` and the components `PassageOut`, `PassageSectionOut`, `PassagesIn`, `PassagesOut`);
- `status: "ok" | "not_found" | "unavailable";` and `text: string | null;`.

- [ ] **Step 11 (agent): Run the whole suite, and the new files three more times**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_usecase_passages.py backend/tests/test_api_scripture.py 2>&1 | tail -1; done
```

**Expected:** `960 passed, 9 skipped in <t>s`, then `22 passed in <t>s` three times. A flaky run of either threaded test is a bug (an event not set, a thread not joined, a pool not reset); stop and find it rather than rerunning.

- [ ] **Step 12 (agent): Layering and log checks**

```bash
grep -n "fastapi\|starlette\|streamlit" backend/usecases/passages.py; echo "exit=$?"
grep -n "logger\.\(info\|warning\|error\|exception\)" backend/usecases/passages.py
grep -n "try:\|except" backend/api/routes/scripture.py; echo "exit=$?"
git status --short
```

**Expected:**
- `exit=1` (no match);
- one line, the `passages_deadline unfinished=%d of=%d` warning (counts only, no reference or translation);
- `exit=1` (the route has no try/except: domain errors reach the app's handler);
- in this order: ` M backend/api/main.py`, ` M backend/api/schemas.py`, ` M backend/tests/conftest.py`, ` M backend/tests/test_api_app.py`, ` M backend/tests/test_no_streamlit_in_core.py`, ` M backend/tests/test_route_guards.py`, ` M frontend/src/lib/api/openapi.json`, ` M frontend/src/lib/api/schema.d.ts`, then `?? .claude/`, `?? backend/api/routes/scripture.py`, `?? backend/tests/test_api_scripture.py`, `?? backend/tests/test_usecase_passages.py`, `?? backend/usecases/passages.py`. Nothing else.

- [ ] **Step 13 (agent): Commit**

```bash
git add backend/usecases/passages.py backend/api/routes/scripture.py backend/api/schemas.py backend/api/main.py \
        backend/tests/conftest.py backend/tests/test_usecase_passages.py backend/tests/test_api_scripture.py \
        backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py \
        frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "$(cat <<'EOF'
Passages: POST /scripture/passages, charged per part, on a shared pool with a 20 s deadline (S Passages, API row 3; F §1.8)

usecases/passages.py plans a request (refs, then translation, then at most
20 parts; a ref with no parts is "Enter a scripture reference."), and loads
every part on one 4-worker pool shared by all requests. A part unfinished at
the 20 s deadline is unavailable and a queued one is cancelled, so each
request answers inside the client's 30 s timeout. The route plans, charges
one scripture token per part, then loads: a 422 charges nothing and a 429
fetches nothing. get_passage_text is re-exported for slice 3, and
translation_options feeds GET /translations (Task 11).

PassagePlan also carries each ref's alternatives, so sections line up with
plan_parts when an alternative has no parts. OpenAPI files regenerated.

Tests: backend 938 -> 960 passed, 9 skipped; frontend unchanged.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
git show --stat HEAD | tail -14
```

**Expected:** one commit; 12 files changed (4 new).

- [ ] **Step 14 (agent): Review the task against the spec**

Read `git show HEAD -- backend/usecases/passages.py backend/api/routes/scripture.py backend/api/schemas.py`. Check:
- The route runs `plan_passages`, then `ratelimit.consume("scripture", user_id=user.id, cost=len(plan.parts))`, then `load_passages(plan)`, is a plain `def`, and declares `error_responses(401, 422, 429, 503)`.
- The exact messages: "Enter a scripture reference." (`fields.refs`, also for `[]`, a blank ref, `";"` and `" ; "`), "Too many passages in one request." (`fields.refs`), "Unknown or unavailable translation." (`fields.translation`, also for `esv` without `ESV_API_KEY`); Pydantic's "Not a valid value." for 5 refs and an extra key, "Too long (max 200 characters)." on `fields["refs.0"]`, "Too long (max 20 characters)." on `fields.translation`, "Required." for a missing translation.
- The limiter 429s: the 61st one-part call and the 21st three-part call, with `Retry-After` 5 and 15, the matching `details.retry_after_seconds`, and `access-control-allow-origin`; `test_422_charges_nothing` shows every 422 kind leaves all 60 tokens.
- AC5's usecase half: two concurrent 12-part requests never exceed 4 upstream calls in flight; a 0.2 s deadline answers both within 0.7 s with every part `unavailable` and the 4 queued parts never sent; the bible-api budget is shared across users while a cached part is still served.
- `get_passage_text` in `usecases.passages` is `scripture_fetcher.get_passage_text` itself.
Record anything that differs for the T12 docs pass (none is expected: the S passages text already matches, apart from clarification 33, which T12 already covers).
### Task 11: `GET /translations` and the `GET /church` profile fields (S API rows 2 and 4, Schemas, `usecases/church_profile.py`; AC6, AC9; clarifications 2, 4, 7, 8)

Two additive API changes, one commit.

- **`GET /translations`** (new `api/routes/reference.py`) lists the Bible translations this deployment offers. It is user-scoped: it depends on `get_current_user` only, never on `require_church`, so `X-Church-Id` is ignored. The body comes from Task 10's `usecases.passages.translation_options()`. `default` is `"web"`, and `items` follow `scripture_fetcher.TRANSLATIONS` order, with `"esv"` listed last and only while `ESV_API_KEY` is set (the configuration exception until slice 7).
- **`GET /church`** returns `ChurchProfileOut`, a subclass of `ChurchOut` that adds `timezone`, `timezone_valid`, `bible_translation`, `effective_translation` and `effective_translation_label`.
  - The fields come from the new `usecases.church_profile.get_church_profile(active.id)`. The route passes the id only (F §1.2 rule 1) and supplies `id`, `name` and `role` from `ActiveChurch`.
  - `/me`'s church list keeps `ChurchOut`.
  - The route's documented statuses do not change (401, 403, 422, 503), and the change is additive (F §1.11). The deployed frontend types `/church` as `components["schemas"]["ChurchOut"]` (`frontend/src/lib/api/types.ts:7`) and does no strict parsing, so it keeps compiling and working. 2b widens it to `ChurchProfileOut`.

**Decisions recorded in this task (code wins over the outline and S; owner decision 1):**
- **T11-1 (clarification 2). Three slice 1 tests pin the exact `/church` body.** They are `test_api_me.py::test_church_returns_the_active_church_for_a_member` (at `:80` on main; the outline says `:79`), `test_api_churches.py::test_create_201_listed_in_me_and_usable` (`assert usable.json() == body`, at `:87` after Task 4 and `:80` on main) and `test_api_invites.py::test_after_accept_get_church_200` (`:202`). S's test list misses them. Each one now asserts the **whole** new body rather than a subset, so it still catches an extra or missing key. None of these churches stores a translation, so every expected body has `bible_translation: None` and `effective_translation` `"web"`, whatever `ESV_API_KEY` is.
- **T11-2 (clarification 8). A church deleted after the guard.** `require_church` checks the church through `tenancy.validate_active_church`, and `get_church_profile` reads it again through `repos.churches.get_church`. If the church is soft-deleted between those two reads, `get_church` returns None and the usecase raises `Forbidden("You don't have access to this church.", details={"reason": "no_church_access"})`. That produces the guard's own 403 body (`tests/api_helpers.NO_CHURCH_ACCESS`), so the route documents no new status. The test simulates the race by wrapping `repos.churches.get_church` so it soft-deletes the church first. This works because `validate_active_church` never calls `get_church` (`backend/tenancy.py:33-54`).
- **T11-3 (clarification 4). `/translations` documents 401, 422 and 503; S lists only 401.**
  - The `Authorization` header parameter makes FastAPI add a default 422. `test_routes_document_the_error_body` rejects that default (it requires `HTTPValidationError` to be absent from the components), so 422 must be listed.
  - `get_current_user` can also answer 503 `auth_unavailable`, and `/me` documents the same set.
  - Task 12 records the S correction.
- **T11-4. What `bible_translation` means.** S says "`settings.get("bible_translation")` if it is a non-empty string, else `None`". The tests pin each case:
  - a missing key, `""`, a JSON `null` and a non-string (`7`) all give `null`;
  - a stored id that is not offered is reported **as stored**, with `effective_translation` `"web"`. That covers `"esv"` without the key, and `"klingon"`, which is never offered.
  - Values are not trimmed or case-folded (S is silent). The frozen Streamlit Settings writes only ids from `available_translations()`.
- **T11-5. The model docstrings name no internal module.** `ChurchProfileOut`'s and `TranslationsOut`'s docstrings become OpenAPI descriptions and `schema.d.ts` comments, so they describe the API only (the 1b T6-m2 rule that Task 4 applied to `CreateChurchIn`). The field comments are Python comments and never reach the schema.
- **T11-6. Two isolation checks, on purpose.** `test_api_church_profile.py::test_assert_church_isolated` repeats `test_isolation.py::test_get_church_is_isolated` (`:25`), because S's Testing row for this file lists it. Both stay. Now that `/church` reads the church row a second time, the repeat guards against a regression in that read.
- **T11-7. Coordination.** Task 8 wrote the `test_route_guards.py` docstring line `2a: GET /lectionary/readings).` and Task 10 extended it to `2a: GET /lectionary/readings, POST /scripture/passages).`; this task appends `GET /translations` to that line and adds the `USER_SCOPED` entry.

**Files:**
- Create: `backend/usecases/church_profile.py`
- Create: `backend/api/routes/reference.py`
- Modify: `backend/api/schemas.py`. One insert after `class ChurchOut` (`:20-23` on main) and one after `class InviteAcceptOut` (`:86-89` on main). Both are anchored on the class text, not on line numbers, because Tasks 4, 8 and 10 also edit this file.
- Modify: `backend/api/routes/me.py` (whole file shown)
- Modify: `backend/api/main.py`: the `from api.routes import …` line (`:12` on main) and one `include_router` line after `app.include_router(invites.router)` (`:61` on main)
- Test (create): `backend/tests/test_api_translations.py`, `backend/tests/test_api_church_profile.py`
- Test (modify):
  - `backend/tests/test_api_me.py:80`
  - `backend/tests/test_api_churches.py:87` (after Task 4)
  - `backend/tests/test_api_invites.py:202`
  - `backend/tests/test_route_guards.py`: `USER_SCOPED`, after `:41`
  - `backend/tests/test_api_app.py`: `test_routes_document_the_error_body`'s map, after `:277`
  - `backend/tests/test_no_streamlit_in_core.py`: the import string at `:21`, and one assert after `:57`
- Modify (generated, never by hand): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes:
  - Task 10: `usecases.passages.translation_options() -> TranslationOptions`, a value with:
    - `default: str`, which is `"web"`;
    - `esv_available: bool`, which is `scripture_fetcher.esv_configured()`;
    - `items: list[tuple[str, str]]`, which is `scripture_fetcher.available_translations()`: `(id, label)` pairs in `TRANSLATIONS` order, with `("esv", "English Standard Version (ESV)")` last and only when configured.

    The route calls it through the module (`from usecases import passages`).
  - Task 9, names kept from main:
    - `scripture_fetcher.available_translations() -> list[tuple[str, str]]`: no arguments; it reads `ESV_API_KEY` at call time.
    - `scripture_fetcher.translation_label(translation_id: str | None) -> str`.
    - `scripture_fetcher.DEFAULT_TRANSLATION == "web"`.
  - Existing:
    - `repos.churches.get_church(church_id, *, session=None) -> dict | None`. It returns `{"id", "name", "timezone", "settings"}`, or None when the church is missing or soft-deleted (`repos/churches.py:58-78`). `Church.timezone` and `Church.settings` are NOT NULL, and `settings` defaults to `{}` (`db/models.py:55-56`).
    - `timezones.is_valid_timezone(name: str) -> bool`: exact and case-sensitive.
    - `domain_errors.Forbidden`: status 403, default code `forbidden`, takes a `details=` keyword. `api.errors.domain_error_response` renders `details`.
    - `api.deps.require_church -> ActiveChurch(id: uuid.UUID, name: str, role: str)`; `api.deps.get_current_user -> CurrentUser`; `api.errors.error_responses(*statuses)`.
    - Test helpers (`tests.api_helpers`): `NO_CHURCH_ACCESS`, `assert_church_isolated`, the `isolation_world` fixture, `auth_headers(email)`, `church_headers(email, church_id)`, `make_api_client()`.
    - Repo functions used by the tests: `repos.churches.set_church_translation(church_id, translation_id)`, `update_church(church_id, *, settings=…)` (replaces the whole settings object), `soft_delete_church(church_id)`, and `repos.memberships.add_membership(user_id, church_id, role)`.
    - Fixtures: `tmp_db`, `make_user(email=…)`, `make_church(name=…, timezone="America/New_York", owner_user_id=None)`.
- Produces:
  - `usecases.church_profile.ChurchProfile`: a frozen dataclass with `timezone: str`, `timezone_valid: bool`, `bible_translation: str | None`, `effective_translation: str` and `effective_translation_label: str`. Slices 3 and 4 extend it additively.
  - `usecases.church_profile.get_church_profile(church_id: uuid.UUID) -> ChurchProfile`. It raises `Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})` when `get_church` returns None.
  - `usecases.church_profile.NO_ACCESS_MESSAGE == "You don't have access to this church."`
  - `api.schemas.ChurchProfileOut(ChurchOut)`, which adds `timezone: str`, `timezone_valid: bool`, `bible_translation: Optional[str]` (required and nullable), `effective_translation: str` and `effective_translation_label: str`. It is the model slices 3 and 4 extend.
  - `api.schemas.TranslationOut(id: str, label: str)`; `api.schemas.TranslationsOut(default: str, esv_available: bool, items: list[TranslationOut])`.
  - `api.routes.reference.router`, with `translations(user: CurrentUser = Depends(get_current_user)) -> TranslationsOut`:
    - route: `GET /translations`, `response_model=TranslationsOut`, `responses=error_responses(401, 422, 503)`;
    - operation id: `translations_translations_get`.
  - `api.routes.me.church(active: ActiveChurch = Depends(require_church)) -> ChurchProfileOut`:
    - `response_model=ChurchProfileOut`;
    - responses unchanged (401, 403, 422, 503);
    - operation id unchanged (`church_church_get`).
  - For 2b in `schema.d.ts`:
    - `components["schemas"]["ChurchProfileOut"]`, with `bible_translation: string | null`;
    - `components["schemas"]["TranslationsOut"]` and `["TranslationOut"]`;
    - `/church`'s 200 is typed `ChurchProfileOut`, while `/me`'s items stay `ChurchOut`.

- [ ] **Step 1 (agent): Confirm Task 10's hand-off, the anchors and the baseline**

```bash
git status --short
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from usecases import passages as p; import scripture_fetcher as sf; o = p.translation_options(); assert o.default == 'web' and isinstance(o.esv_available, bool) and o.items[0] == ('web', 'World English Bible (WEB)'); assert sf.DEFAULT_TRANSLATION == 'web' and sf.translation_label('kjv') == 'King James Version (KJV)'; print('ok')"
ls backend/usecases/church_profile.py backend/api/routes/reference.py 2>&1 | grep -c "No such file"
grep -c "me, rubric" backend/api/main.py
grep -c "    app.include_router(invites.router)" backend/api/main.py
grep -n 'assert usable.json() == body' backend/tests/test_api_churches.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `git status --short` lists only `?? .claude/`.
- The one-liner prints `ok`.
- Then `2`, `1` and `1`.
- `87:    assert usable.json() == body`.
- `960 passed, 9 skipped in <t>s` (Task 10's count).

If the one-liner fails, Task 10's names differ from its Interfaces: stop and reconcile before editing anything. If a count differs, stop and find why.

- [ ] **Step 2 (agent): Write the failing tests**

Create `backend/tests/test_api_translations.py`:

```python
"""GET /translations over HTTP (S API row 2, Testing `test_api_translations.py`; AC6).

User-scoped reference data: a token is required, X-Church-Id is ignored, and
"esv" is offered, last, only while ESV_API_KEY is set (the configuration
exception: scripture_fetcher reads the key from the environment until slice 7).
"""
import pytest

from tests.api_helpers import auth_headers, make_api_client

EMAIL = "pastor@example.com"
PUBLIC_DOMAIN = [
    {"id": "web", "label": "World English Bible (WEB)"},
    {"id": "kjv", "label": "King James Version (KJV)"},
    {"id": "asv", "label": "American Standard Version (ASV)"},
    {"id": "ylt", "label": "Young's Literal Translation (YLT)"},
    {"id": "dra", "label": "Douay-Rheims 1899 (DRA)"},
    {"id": "darby", "label": "Darby Bible"},
    {"id": "bbe", "label": "Bible in Basic English (BBE)"},
    {"id": "oeb-us", "label": "Open English Bible, US (OEB)"},
    {"id": "webbe", "label": "World English Bible, British (WEBBE)"},
]
ESV = {"id": "esv", "label": "English Standard Version (ESV)"}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def test_requires_token_401(client):
    r = client.get("/translations")
    assert r.status_code == 401
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("unauthenticated", "Please sign in.")


def test_without_esv_key(client, monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    # X-Church-Id is ignored: a malformed one is neither checked nor a 403.
    r = client.get("/translations", headers={**auth_headers(EMAIL), "X-Church-Id": "not-a-uuid"})
    assert r.status_code == 200, r.text
    assert r.json() == {"default": "web", "esv_available": False, "items": PUBLIC_DOMAIN}


def test_with_esv_key_esv_last(client, monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    r = client.get("/translations", headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    assert r.json() == {"default": "web", "esv_available": True, "items": [*PUBLIC_DOMAIN, ESV]}
    assert "test-key" not in r.text                         # the key never leaves the backend
```

Create `backend/tests/test_api_church_profile.py`:

```python
"""GET /church's profile fields over HTTP (S API row 4, `usecases/church_profile.py`,
Testing `test_api_church_profile.py`; AC6).

GET /church returns ChurchProfileOut: ChurchOut's id, name and role (from
require_church) plus timezone, timezone_valid, bible_translation,
effective_translation and effective_translation_label (from
usecases.church_profile). /me's church items stay ChurchOut.
"""
import pytest

from api.main import create_app
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    NO_CHURCH_ACCESS,
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
WEB = ("web", "World English Bible (WEB)")


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def no_esv_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)


def _profile(client, church_id, email=EMAIL) -> dict:
    r = client.get("/church", headers=church_headers(email, church_id))
    assert r.status_code == 200, r.text
    return r.json()


def _effective(body: dict) -> tuple[str, str]:
    return body["effective_translation"], body["effective_translation_label"]


def test_new_fields_including_label(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", timezone="America/Chicago",
                      owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "kjv")
    assert _profile(client, cid) == {
        "id": str(cid),
        "name": "Grace",
        "role": "owner",
        "timezone": "America/Chicago",
        "timezone_valid": True,
        "bible_translation": "kjv",
        "effective_translation": "kjv",
        "effective_translation_label": "King James Version (KJV)",
    }


def test_timezone_valid_exact_and_case_sensitive(client, make_user, make_church):
    owner = make_user(email=EMAIL)
    cases = [("Eastern", False), ("america/new_york", False), ("America/New_York", True)]
    for timezone, valid in cases:
        cid = make_church(name=f"Church {timezone}", timezone=timezone, owner_user_id=owner)
        body = _profile(client, cid)
        assert (body["timezone"], body["timezone_valid"]) == (timezone, valid), timezone


def test_stored_esv_without_key_effective_web(client, make_user, make_church, monkeypatch):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "esv")
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    body = _profile(client, cid)
    assert body["bible_translation"] == "esv"                # the stored value, unchanged
    assert _effective(body) == WEB

    churches.set_church_translation(cid, "klingon")           # never offered anywhere
    body = _profile(client, cid)
    assert (body["bible_translation"], _effective(body)) == ("klingon", WEB)

    churches.set_church_translation(cid, "esv")
    monkeypatch.setenv("ESV_API_KEY", "test-key")            # control: offered once configured
    body = _profile(client, cid)
    assert _effective(body) == ("esv", "English Standard Version (ESV)")
    assert "test-key" not in str(body)


def test_unset_translation_null_effective_web(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    body = _profile(client, cid)                               # settings == {}: never set
    assert (body["bible_translation"], _effective(body)) == (None, WEB)

    for stored in ("", 7, None):                               # not a non-empty string: unset
        churches.update_church(cid, settings={"bible_translation": stored})
        body = _profile(client, cid)
        assert (body["bible_translation"], _effective(body)) == (None, WEB), stored


def test_assert_church_isolated(client, isolation_world):
    assert_church_isolated(client, "GET", "/church", world=isolation_world)


def test_every_role_200(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", timezone="America/Denver",
                      owner_user_id=make_user(email="owner@example.com"))
    add_membership(make_user(email="admin@example.com"), cid, "admin")
    add_membership(make_user(email="member@example.com"), cid, "member")
    for role in ("owner", "admin", "member"):
        body = _profile(client, cid, email=f"{role}@example.com")
        assert (body["role"], body["timezone"], body["timezone_valid"]) == (
            role, "America/Denver", True), role
        assert _effective(body) == WEB, role


def test_me_church_items_unchanged(client, make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "kjv")
    r = client.get("/me", headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    assert r.json()["churches"] == [{"id": str(cid), "name": "Grace", "role": "owner"}]

    schema = create_app().openapi()
    components = schema["components"]["schemas"]
    assert components["MeOut"]["properties"]["churches"]["items"] == {
        "$ref": "#/components/schemas/ChurchOut"}
    assert set(components["ChurchOut"]["properties"]) == {"id", "name", "role"}
    ok = schema["paths"]["/church"]["get"]["responses"]["200"]["content"]["application/json"]
    assert ok["schema"] == {"$ref": "#/components/schemas/ChurchProfileOut"}
    assert set(components["ChurchProfileOut"]["required"]) == {
        "id", "name", "role", "timezone", "timezone_valid", "bible_translation",
        "effective_translation", "effective_translation_label"}


def test_church_deleted_after_guard_is_403(client, make_user, make_church, monkeypatch):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    real_get_church = churches.get_church

    def deleted_then_read(church_id, **kwargs):
        churches.soft_delete_church(church_id)       # after require_church passed, before the read
        return real_get_church(church_id, **kwargs)

    monkeypatch.setattr(churches, "get_church", deleted_then_read)
    r = client.get("/church", headers=church_headers(EMAIL, cid))
    assert r.status_code == 403, r.text
    error = dict(r.json()["error"])
    error.pop("request_id")
    assert error == NO_CHURCH_ACCESS
```

In `backend/tests/test_api_me.py`, in `test_church_returns_the_active_church_for_a_member`, replace (`:80`):

```python
    assert r.json() == {"id": str(cid), "name": "Grace", "role": "owner"}
```

with:

```python
    # Slice 2 adds the profile fields (ChurchProfileOut); make_church's zone is America/New_York.
    assert r.json() == {
        "id": str(cid), "name": "Grace", "role": "owner",
        "timezone": "America/New_York", "timezone_valid": True, "bible_translation": None,
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
    }
```

In `backend/tests/test_api_churches.py`, in `test_create_201_listed_in_me_and_usable`, replace (`:87`):

```python
    assert usable.json() == body
```

with:

```python
    assert usable.json() == {                           # ChurchOut plus slice 2's profile fields
        **body, "timezone": "America/Chicago", "timezone_valid": True, "bible_translation": None,
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
    }
```

In `backend/tests/test_api_invites.py`, in `test_after_accept_get_church_200`, replace (`:202`):

```python
    assert r.json() == {"id": church_id, "name": "Grace", "role": "member"}
```

with:

```python
    assert r.json() == {                                # ChurchOut plus slice 2's profile fields
        "id": church_id, "name": "Grace", "role": "member",
        "timezone": "America/New_York", "timezone_valid": True, "bible_translation": None,
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
    }
```

In `backend/tests/test_route_guards.py`, in `USER_SCOPED`, replace (`:41`):

```python
    ("POST", "/invites/accept"),
```

with:

```python
    ("POST", "/invites/accept"),
    ("GET", "/translations"),
```

(Tasks 8 and 10 may already have added lines after `("POST", "/invites/accept"),`. They stay, and order does not matter in a set.)

In the same file's module docstring, replace the line Task 10 left:

```python
2a: GET /lectionary/readings, POST /scripture/passages).
```

with:

```python
2a: GET /lectionary/readings, POST /scripture/passages, GET /translations).
```

In `backend/tests/test_api_app.py`, in `test_routes_document_the_error_body`, replace (`:277`):

```python
        ("/invites/accept", "post"): {"400", "401", "422", "503"},
```

with:

```python
        ("/invites/accept", "post"): {"400", "401", "422", "503"},
        ("/translations", "get"): {"401", "422", "503"},
```

(Tasks 8 and 10's entries for `/lectionary/readings` and `/scripture/passages` stay where they are.)

In `backend/tests/test_no_streamlit_in_core.py`, in `test_usecases_package_imports_no_fastapi_or_streamlit`, change the `code` string's import list (`:21`). Replace the text `usecases.onboarding,` (it occurs once in the file: the comment above says `usecases.onboarding),`) with `usecases.onboarding, usecases.church_profile,`. The rest of the string, including the modules Tasks 2 to 10 appended, is kept. On main the line

```python
    code = ("import sys, usecases, usecases.onboarding, domain_errors, db.ids, timezones; "
```

becomes

```python
    code = ("import sys, usecases, usecases.onboarding, usecases.church_profile, domain_errors, db.ids, timezones; "
```

and on Task 10's tree only the same insertion happens.

In the same file, in `test_api_main_with_every_router_does_not_import_streamlit`, replace (`:57`):

```python
    assert "'api.routes.invites'" in result.stdout
```

with:

```python
    assert "'api.routes.invites'" in result.stdout
    assert "'api.routes.reference'" in result.stdout
```

- [ ] **Step 3 (agent): Run the tests and watch them fail**

```bash
.venv/bin/python -m pytest -q --tb=line backend/tests/test_api_translations.py backend/tests/test_api_church_profile.py backend/tests/test_api_me.py backend/tests/test_api_churches.py backend/tests/test_api_invites.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | grep -E "^FAILED|passed|failed"
```

**Expected:** `18 failed, 86 passed, 1 skipped in <t>s`. The skip is `test_api_app.py`'s Postgres test. The FAILED lines are exactly these, with these reasons (from `--tb=line`):
- `test_api_translations.py`: `test_requires_token_401` (`assert 404 == 401`); `test_without_esv_key` and `test_with_esv_key_esv_last` (`AssertionError: {"error":{"code":"not_found","message":"Not Found",…`). The route does not exist yet.
- `test_api_church_profile.py`:
  - `test_new_fields_including_label` (`assert {'id': …, 'role': 'owner'} == {…'America/Chicago', ...}`);
  - `test_timezone_valid_exact_and_case_sensitive` and `test_every_role_200` (`KeyError: 'timezone'`);
  - `test_stored_esv_without_key_effective_web` and `test_unset_translation_null_effective_web` (`KeyError: 'bible_translation'`);
  - `test_me_church_items_unchanged` (`assert {'$ref': '#/c...as/ChurchOut'} == {'$ref': '#/c...chProfileOut'}`);
  - `test_church_deleted_after_guard_is_403` (`AssertionError: {"id":"…","name":"Grace","role":"owner"}`: the route answered 200 without reading the church).
- `test_api_me.py::test_church_returns_the_active_church_for_a_member`, `test_api_churches.py::test_create_201_listed_in_me_and_usable` and `test_api_invites.py::test_after_accept_get_church_200`: each fails with `assert {'id': …, 'role': …} == {…}`.
- `test_route_guards.py`: `test_user_scoped_routes_require_a_user` (`KeyError: ('GET', '/translations')`) and `test_allowlists_name_real_routes` (`assert {('GET', '/translations')} == set()`).
- `test_api_app.py::test_routes_document_the_error_body` (`KeyError: '/translations'`).
- `test_no_streamlit_in_core.py`: `test_usecases_package_imports_no_fastapi_or_streamlit` (an `AssertionError` whose message is the subprocess's `ModuleNotFoundError: No module named 'usecases.church_profile'` traceback) and `test_api_main_with_every_router_does_not_import_streamlit` (`assert "'api.routes.reference'" in "modules: [...`).

`test_api_church_profile.py::test_assert_church_isolated` passes already: `/church` was isolated before this task, and the test pins that it stays so. The 86 passes are 1 in the new files plus 85 in the six edited files: 17, 18, 24, 5, 27 and 3 tests, minus the 8 failures and the 1 skip. If the FAILED list differs, stop and find why.

- [ ] **Step 4 (agent): Write the usecase (`backend/usecases/church_profile.py`)**

```python
"""The active church's profile for GET /church (S `usecases/church_profile.py`; slice 2 AC6).

get_church_profile reads the church row once and derives the fields the
builder needs: the stored time zone and whether it is a real IANA name, and
the stored default translation and the one passage text actually uses.
Slices 3 and 4 add fields to ChurchProfile (and ChurchProfileOut) additively.

The route passes only ActiveChurch.id (F §1.2 rule 1) and supplies the id,
name and role itself. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). The repo and
scripture_fetcher are called through their modules, so a test can patch one
function.
"""
import uuid
from dataclasses import dataclass

import scripture_fetcher
from domain_errors import Forbidden
from repos import churches
from timezones import is_valid_timezone

# require_church's own 403 (api/deps.py, api/errors.forbidden): a church
# soft-deleted between the guard and this read looks exactly like one the
# caller never belonged to (2a plan clarification 8).
NO_ACCESS_MESSAGE = "You don't have access to this church."


@dataclass(frozen=True)
class ChurchProfile:
    timezone: str
    timezone_valid: bool
    bible_translation: str | None
    effective_translation: str
    effective_translation_label: str


def get_church_profile(church_id: uuid.UUID) -> ChurchProfile:
    """The profile of a live church.

    - timezone_valid: timezones.is_valid_timezone, exact and case-sensitive
      (so "america/new_york" is False, as 6a's PATCH /church will reject it).
    - bible_translation: settings["bible_translation"] when it is a non-empty
      string, else None.
    - effective_translation: that value when this deployment offers it
      (available_translations(), so "esv" only with ESV_API_KEY set), else
      "web"; effective_translation_label is its human label.

    Raises Forbidden (403 forbidden, details.reason no_church_access) when the
    church is missing or soft-deleted.
    """
    church = churches.get_church(church_id)
    if church is None:
        raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
    timezone = church["timezone"]
    stored = (church["settings"] or {}).get("bible_translation")
    bible_translation = stored if isinstance(stored, str) and stored else None
    offered = {tid for tid, _label in scripture_fetcher.available_translations()}
    effective = (bible_translation if bible_translation in offered
                 else scripture_fetcher.DEFAULT_TRANSLATION)
    return ChurchProfile(
        timezone=timezone,
        timezone_valid=is_valid_timezone(timezone),
        bible_translation=bible_translation,
        effective_translation=effective,
        effective_translation_label=scripture_fetcher.translation_label(effective),
    )
```

- [ ] **Step 5 (agent): Add the models (`backend/api/schemas.py`)**

Replace the `ChurchOut` class (`:20-23` on main; the text is unchanged by Tasks 4, 8 and 10):

```python
class ChurchOut(BaseModel):
    id: uuid.UUID
    name: str
    role: Literal["owner", "admin", "member"]
```

with:

```python
class ChurchOut(BaseModel):
    id: uuid.UUID
    name: str
    role: Literal["owner", "admin", "member"]


class ChurchProfileOut(ChurchOut):
    """GET /church: the active church and its profile. A superset of ChurchOut,
    which the church list in GET /me keeps."""

    timezone: str
    timezone_valid: bool                    # an exact, case-sensitive IANA name
    bible_translation: Optional[str]        # the stored default, or null when unset
    effective_translation: str              # the stored default if offered here, else "web"
    effective_translation_label: str        # its label, for when GET /translations fails
```

Replace the `InviteAcceptOut` class (`:86-89` on main; Tasks 8 and 10's models may follow it, and they stay):

```python
class InviteAcceptOut(BaseModel):
    church: ChurchOut
    already_member: bool
    message: str
```

with:

```python
class InviteAcceptOut(BaseModel):
    church: ChurchOut
    already_member: bool
    message: str


class TranslationOut(BaseModel):
    id: str
    label: str


class TranslationsOut(BaseModel):
    """GET /translations: the translations this deployment offers, in display
    order. "default" is "web"; "esv" is listed, last, only when it is configured."""

    default: str
    esv_available: bool
    items: list[TranslationOut]
```

`Optional` and `Literal` are already imported at `:4`.

- [ ] **Step 6 (agent): Write the `/translations` route, switch `/church`, and mount the router**

Create `backend/api/routes/reference.py`:

```python
"""GET /translations: the Bible translations this deployment offers (S API row 2).

User-scoped reference data: the route depends on get_current_user and never
on require_church, so X-Church-Id is ignored (F §1.2). It reads no church data.
"esv" is listed, last, only while ESV_API_KEY is set (until slice 7 this
is the configuration exception). Plain `def`, like every route here.
"""
from fastapi import APIRouter, Depends

from api.deps import CurrentUser, get_current_user
from api.errors import error_responses
from api.schemas import TranslationOut, TranslationsOut
from usecases import passages

router = APIRouter()


@router.get("/translations", response_model=TranslationsOut,
            responses=error_responses(401, 422, 503))
def translations(user: CurrentUser = Depends(get_current_user)) -> TranslationsOut:
    options = passages.translation_options()
    return TranslationsOut(
        default=options.default,
        esv_available=options.esv_available,
        items=[TranslationOut(id=tid, label=label) for tid, label in options.items],
    )
```

Replace the whole of `backend/api/routes/me.py` with:

```python
from dataclasses import asdict

from fastapi import APIRouter, Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
from usecases import church_profile

router = APIRouter()


@router.get("/me", response_model=MeOut, responses=error_responses(401, 422, 503))
def me(user: CurrentUser = Depends(get_current_user)) -> MeOut:
    return MeOut(
        user=UserOut(id=user.id, email=user.email, name=user.name, picture=user.picture),
        churches=[ChurchOut(**church) for church in list_user_churches(user.id)],
    )


@router.get("/church", response_model=ChurchProfileOut,
            responses=error_responses(401, 403, 422, 503))
def church(active: ActiveChurch = Depends(require_church)) -> ChurchProfileOut:
    # The usecase gets the id only (F §1.2 rule 1); id, name and role come from the guard.
    profile = church_profile.get_church_profile(active.id)
    return ChurchProfileOut(id=active.id, name=active.name, role=active.role, **asdict(profile))
```

In `backend/api/main.py`, change the `from api.routes import …` line by replacing its text `me, rubric` with `me, reference, rubric`. The rest of the line stays. On Task 10's tree the line is

```python
from api.routes import churches, health, invites, lectionary, me, rubric, scripture
```

and becomes

```python
from api.routes import churches, health, invites, lectionary, me, reference, rubric, scripture
```

In `create_app`, replace:

```python
    app.include_router(invites.router)
```

with:

```python
    app.include_router(invites.router)
    app.include_router(reference.router)
```

(Tasks 8 and 10's `include_router` lines for `lectionary` and `scripture` stay where they are.)

- [ ] **Step 7 (agent): Run the tests and watch them pass**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_translations.py backend/tests/test_api_church_profile.py backend/tests/test_api_me.py backend/tests/test_api_churches.py backend/tests/test_api_invites.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected:** `104 passed, 1 skipped in <t>s` (the 18 from Step 3 now pass).

- [ ] **Step 8 (agent): Regenerate the OpenAPI files and typecheck**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
(cd frontend && npm run typecheck)
git diff --stat -- frontend/src/lib/api
grep -c 'components\["schemas"\]\["ChurchProfileOut"\]' frontend/src/lib/api/schema.d.ts
grep -c '"/translations": {' frontend/src/lib/api/schema.d.ts
grep -c 'bible_translation: string | null;' frontend/src/lib/api/schema.d.ts
grep -c '"operationId": "translations_translations_get"' frontend/src/lib/api/openapi.json
```

**Expected:**
- `Wrote <repo root>/frontend/src/lib/api/openapi.json`, then `gen:api`'s openapi-typescript output.
- `tsc --noEmit` with no errors. `Church` in `frontend/src/lib/api/types.ts:7` is still `components["schemas"]["ChurchOut"]`, which still exists.
- `git diff --stat` shows the 2 files `openapi.json` and `schema.d.ts`. On a scratch copy of main this was about 175 and 117 lines changed.
- Then `1`, `1`, `1`, `1`.

If `typecheck` fails, the generated schema is stale: rerun this step's first command. Never hand-edit `schema.d.ts`.

- [ ] **Step 9 (agent): Run the whole suite**

```bash
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `971 passed, 9 skipped in <t>s` (960 after Task 10, plus 11: 3 in `test_api_translations.py` and 8 in `test_api_church_profile.py`; the edited tests add none). `test_openapi_contract.py` passes because Step 8 regenerated the snapshot. Then exactly:

```
 M backend/api/main.py
 M backend/api/routes/me.py
 M backend/api/schemas.py
 M backend/tests/test_api_app.py
 M backend/tests/test_api_churches.py
 M backend/tests/test_api_invites.py
 M backend/tests/test_api_me.py
 M backend/tests/test_no_streamlit_in_core.py
 M backend/tests/test_route_guards.py
 M frontend/src/lib/api/openapi.json
 M frontend/src/lib/api/schema.d.ts
?? .claude/
?? backend/api/routes/reference.py
?? backend/tests/test_api_church_profile.py
?? backend/tests/test_api_translations.py
?? backend/usecases/church_profile.py
```

- [ ] **Step 10 (agent): Commit**

```bash
git add backend/usecases/church_profile.py backend/api/routes/reference.py \
        backend/api/schemas.py backend/api/routes/me.py backend/api/main.py \
        backend/tests/test_api_translations.py backend/tests/test_api_church_profile.py \
        backend/tests/test_api_me.py backend/tests/test_api_churches.py backend/tests/test_api_invites.py \
        backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py \
        frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: GET /translations and the GET /church profile fields (S API rows 2 and 4; AC6)

GET /translations lists the translations this deployment offers from
usecases.passages.translation_options(): user-scoped, X-Church-Id ignored,
esv last and only while ESV_API_KEY is set. It documents 401, 422 and 503,
because the Authorization header makes FastAPI emit a 422 (2a clarification
4; S lists 401 only).

GET /church now returns ChurchProfileOut, a superset of ChurchOut:
timezone, timezone_valid (timezones.is_valid_timezone, exact and
case-sensitive), bible_translation, effective_translation and
effective_translation_label, from usecases.church_profile.get_church_profile,
which gets the church id only (F §1.2 rule 1). /me keeps ChurchOut. A church
soft-deleted between require_church and the read gets the guard's own 403
no_church_access (clarification 8).

The three slice 1 tests that pinned the exact /church body now pin the new
fields too (clarification 2). openapi.json and schema.d.ts regenerated.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
git status --short
```

**Expected:** `<sha> API: GET /translations and the GET /church profile fields (S API rows 2 and 4; AC6)`. Then `git status --short` lists only `?? .claude/`.

- [ ] **Step 11 (agent): Review checkpoint**

Read `git show --stat HEAD` (15 files) and `git show HEAD -- backend/api/routes/me.py backend/usecases/church_profile.py`. Check against this task:
- The `/church` decorator still has `error_responses(401, 403, 422, 503)`.
- The usecase is called with `active.id` only.
- `usecases/church_profile.py` imports no fastapi or starlette (`test_usecases_package_imports_no_fastapi_or_streamlit` checks this).
- `/me` still builds `ChurchOut`.
- AC6 is pinned:
  - `GET /translations` hides ESV without a key (`test_without_esv_key`) and lists it last with one (`test_with_esv_key_esv_last`);
  - `GET /church` returns the five fields (`test_new_fields_including_label`);
  - `timezone_valid` is false for "america/new_york" (`test_timezone_valid_exact_and_case_sensitive`);
  - `/me`'s items are unchanged in the body and in OpenAPI (`test_me_church_items_unchanged`).
- AC9 for these two routes is pinned by `test_routes_document_the_error_body` and the regenerated snapshot.

For Task 12, record: T11-3 (S's `/translations` row lists 401 only; it is 401, 422 and 503), and T11-1 (S's Testing rows miss the three exact-body tests).

Counts after Task 11: backend **971 passed, 9 skipped**; frontend **221 passed in 34 files** (unchanged: only the generated schema changed, and typecheck is green).
### Task 12: Docs: the F amendment rows, the S corrections and the runbook's ESV line (F §1.8, §2.3, §2.7, §7.4, acceptance 13; S API, Rate-limit buckets, Lectionary domain, `usecases/lectionary.py`, Passages, Testing, AC4; owner answer Q3; clarifications 1, 3, 4, 5, 19, 23, 30, 31, 34, 41)

Docs only, in one commit, following the slice 1b plan's Task 19 pattern: an amendment row in F's table for each foundation rule 2a changes, with the section body stating the amended rule (the table's own contract: "The sections named below already state the amended rule; this table is the index"), and each S correction made in place, marked "(2a plan)". F gains four rows: the process-wide upstream budgets and the two 20 s deadlines (§1.8, §2.7, §7.4; clarification 31); the `ESV_API_KEY` exception to §2.3 item 5 until slice 7; `integrations/budget.py` in acceptance criterion 13; and the `church_create` test rule counting requests, not creates (F :290; clarification 1). S is corrected where the code the earlier tasks wrote disagrees with it: the 6th-create test (S :302, :897; clarification 1), the `DomainError` call forms (clarification 5), the strict `?date=` and the 422/503 every route documents (clarifications 3, 4), the 300-character set-name limit (clarification 34), owner answer Q3's Christmas-season names, the All Saints Proper rename (S :454, AC4; clarification 30, owner answer Q2), the lectionary source deadline (clarification 31) and the contingency marked not in force (owner decision 2; clarification 23). Two corrections depend on what Task 1 recorded, and a script makes them from the recordings themselves: Vanderbilt's media type (clarification 19) and the Palm Sunday example (clarification 41). The runbook's `ESV_API_KEY` row says what the new app does with the key. No code changes, no test is added, and the counts stay at 971/9 and 221/34.

Line numbers are at `55f1b11`. Tasks 1–11 change none of the three files (File Structure; Step 1 proves it), so every line number and replacement block below still holds when this task runs.

**Decisions recorded in this task (code wins over the outline; owner decision 1):**
- **T12-1. No pytest test is added.** The outline fixes Task 12 at +0 (971), so the red/green check is a script kept outside the repo (`${TMPDIR:-/tmp}/slice2a_t12_docs_check.py`, Step 2), run before and after the edits and deleted before the commit. The committed guards are the existing `test_docs.py`, `test_slice1_docs.py` (its `test_foundations_records_the_join_tap_amendment` still sees exactly one `| §4.3 |` row) and `test_ops_workflows.py`, plus the owner-marker count.
- **T12-2. F's §1.8 timeouts table changes too, so amendment row 1 names §1.8, §2.7 and §7.4** (the outline says "§2.7 / §7.4"). The lectionary row's "Server worst case" said 15 s; with the source deadline it is "15 s on an idle pool; at most 20 s", and the passages row gains the shared pool, the deadline and the budgets. Without this the §1.8 table would contradict the §2.7 body the new row indexes.
- **T12-3. The call-form fix also covers S :891** (the `test_usecase_passages.py` row), which repeats the two positional-after-keyword forms of :608 and :610. The shorthand `InvalidInput(field="date")` (:888) and `InvalidInput(field="translation")` (:891) stay: they are shorthand for the expected exception and its field in a test description, not calls.
- **T12-4. "Every route documents 422 and 503" is stated once** (clarification 4), in the new strict-date paragraph above S's API table, and only the `/translations` row changes, because it is the only row that listed 401 alone. `GET /church` and `POST /churches` are unchanged (Global Constraints, "Codes and documented statuses").
- **T12-5. The recording-dependent corrections are made by a script** (Step 5): it compares `vanderbilt_lectionary.VANDERBILT_MEDIA_TYPES` (Task 7) with S's two types, and S's Palm Sunday example with what `usecases.lectionary.readings_for_date(2026-03-29)` returns from the Task 1 fixtures through Task 7's respx helpers. Each difference is written into S in S's own layout, marked "(2a plan)"; when nothing differs, S is left alone. Any other recording difference (a merge-table row, the Vigil cell) is not corrected here: Task 6b stops on it for the owner (its T6b-9). If the owner's decision at that stop changed S's wording, the controller passes that exact text, and it is applied in Step 5 and named in the commit message.
- **T12-6. The outline's list is the scope.** Clarification 13's 7-day `NOT_FOUND` (S :605 says "24 h is enough"), clarification 33's zero-part refs and clarification 38's 422 token are left to the plan's clarifications; the 1b final review's T7-m3 citation fix does not apply, because none of these three files carries that citation.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`: the amendments table (four rows after :82); the §1.8 timeouts table, lectionary and passages rows (:262, :263); the §1.8 `church_create` paragraph (:290); §2.3 item 5 (after :425); §2.7 (after :494); the §7.4 bible-api row (:1290); acceptance criterion 13 (:1333)
- Modify: `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`: the header (after :8); API (after :204; the `/translations` row :209; `ReadingSetOut` :222); Rate-limit buckets (:302); Lectionary domain (:431, :440, :447, :454); the contingency paragraph (:544); `usecases/lectionary.py` steps 1, 2 and 4 (:579, :584, :587, :588); Passages (:608, :609, :610); Testing (:889, :890, :891, :897); AC4 (:942); and, only when Step 5 finds a difference, the `fetch_vanderbilt_year` 200 line (:517) and the Palm Sunday example (:266-275)
- Modify: `docs/ops-runbook.md`: the `ESV_API_KEY` row of "Environments and variables" (:42)
- Test: none added. Temporary, never committed: `${TMPDIR:-/tmp}/slice2a_t12_docs_check.py`

**Interfaces:**
- Consumes (names quoted in the docs or run by Step 5, as the earlier tasks define them):
  - Task 1: `tests.upstream_fixtures.FIXTURES_DIR: Path`; the sidecars `backend/tests/fixtures/<kind>/<name>.meta.json` with `recorded_at` (an ISO timestamp) and `synthetic: bool`; the fixtures `lectio/2026-03-29.json` and `vanderbilt/2025-26.csv`.
  - Task 3: `integrations.budget.try_acquire(upstream: Literal["bible_api", "esv"]) -> bool` (never waits); budgets `bible_api` 15/30 s, `esv` 60/60 s, 1 000/3 600 s and 5 000/86 400 s.
  - Task 4: the tests `test_cap_429_not_replayed` (unchanged), `test_blank_then_corrected_with_new_key_201` (advances `limiter_clock` 60 s before its 4th POST) and `test_creates_spaced_a_minute_apart_meet_the_cap_message`; `api.ratelimit.set_clock_for_tests`.
  - Task 6a: `sunday_name(d)` ("First Sunday after Christmas Day", "Second Sunday after Christmas Day"; None for a Sunday Dec 25 or Jan 6), `weekday_feast_name(d)`, `lectio_set_name(day, d)` step 2 = `sunday_name(d) or weekday_feast_name(d)`, `_ordinary_time_name(d)`.
  - Task 6b: `fits_draft_limits(item: ReadingSet | LectioGroup) -> bool` (1–20 lines of 1–200 characters; a `ReadingSet` name of 1–300 characters); `merge` checks each Lectio-only set's name after naming it; the All Saints Proper rename in `vanderbilt_sets_on`; `ReadingSet(name, first, psalm, second, gospel, scriptures, source)`.
  - Task 7: `vanderbilt_lectionary.VANDERBILT_MEDIA_TYPES: frozenset[str]` (`{"text/plain", "text/csv"}` plus any recorded type); `SourceFailed(timeout=True)`; `usecases.lectionary.DEADLINE_SECONDS = 20.0`, `readings_for_date(d: date) -> LectionaryResult(date, status, partial, reading_sets, default_index)`; `tests.upstream_fixtures.route_lectio(router, d, name=None)` and `route_vanderbilt(router, year, name=None)`.
  - Task 8: `api.schemas.IsoDate`; `GET /lectionary/readings` documents 401, 422, 429, 502, 503, 504.
  - Tasks 9–11: `scripture_fetcher._esv_key()` still reads `ESV_API_KEY`; `usecases.passages.load_passages(plan, deadline=…)` with its 20 s default; `GET /translations` with `error_responses(401, 422, 503)` and `esv_available`.
- Produces: documentation only. F's amendments table ends with four rows whose first cells are `| §1.8, §2.7, §7.4 |`, `| §2.3 |`, `| Acceptance 13 |` and `| §1.8 |`, each dated `*(2026-09-28, slice 2a)*` with Source `2, 2a` or `2a`; S carries "(2a plan)" markers; the runbook's `ESV_API_KEY` row names `scripture_fetcher._esv_key()` and `esv_available: false`.
- Later users: Task 14 (the PR body lists these amendments; its grep gates do not read these files); Task 15 (the "Slice 2a record" states whether `ESV_API_KEY` is set on Railway, which this row explains); slices 2b and 2c read S's corrected API section and names; slice 7 moves the key, as F §2.3 now says.

Counts before this task: backend **971 passed, 9 skipped** (Task 11); frontend **221 passed in 34 files**. After: unchanged (no code, no test).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
git diff --stat 55f1b11 HEAD -- docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/superpowers/specs/2026-09-25-slice-2-readings-design.md docs/ops-runbook.md
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); import vanderbilt_lectionary as v; from usecases import lectionary as l; print(sorted(v.VANDERBILT_MEDIA_TYPES), l.DEADLINE_SECONDS)"
```

**Expected:** only `?? .claude/`; `971 passed, 9 skipped in <t>s`; `89 passed in <t>s`; `4`; the `git diff --stat` prints nothing (the three files are as at `55f1b11`, so every block below applies); then `['text/csv', 'text/plain'] 20.0` (a third media type here is the clarification 19 case, which Step 5 writes into S). If a count differs, or the `git diff` prints a file, stop and ask: the replacement blocks are written against exactly that state.

- [ ] **Step 2 (agent): Write the docs check and see it fail**

Write the check outside the repo (Step 8 deletes it), then run it from the repo root:

```bash
cat > "${TMPDIR:-/tmp}/slice2a_t12_docs_check.py" <<'PY'
"""Task 12's docs check: run from the repo root. Not committed; not a pytest test."""
import sys
from pathlib import Path

F = Path("docs/superpowers/specs/2026-09-25-migration-foundations-design.md").read_text(encoding="utf-8")
S = Path("docs/superpowers/specs/2026-09-25-slice-2-readings-design.md").read_text(encoding="utf-8")
RB = Path("docs/ops-runbook.md").read_text(encoding="utf-8")

PRESENT = [
    ("F", F, "| §1.8, §2.7, §7.4 | *(2026-09-28, slice 2a)* Process-wide upstream budgets"),
    ("F", F, "| §2.3 | *(2026-09-28, slice 2a)* Item 5's one recorded exception"),
    ("F", F, "| Acceptance 13 | *(2026-09-28, slice 2a)* The upstream budgets"),
    ("F", F, "| §1.8 | *(2026-09-28, slice 2a)* The `church_create` test rule counts requests"),
    ("F", F, "| 15 s on an idle pool; at most 20 s | 25 000 |"),
    ("F", F, "inside a 20 s deadline per request; process-wide upstream budgets (§2.7)."),
    ("F", F, "tests that make more than 3 `POST /churches` requests as one user"),
    ("F", F, "   - One recorded exception (*amendment 2026-09-28, slice 2a*)"),
    ("F", F, "- **Upstream budgets** (*amendment 2026-09-28, slice 2a*)"),
    ("F", F, "- **Deadlines on the shared pools** (*amendment 2026-09-28, slice 2a*)"),
    ("F", F, "`scripture` bucket; process-wide `bible_api` and `esv` budgets"),
    ("F", F, "13. The rate limiter, the upstream budgets (`integrations/budget.py`)"),
    ("S", S, "are marked \"(2a plan)\" where they are made."),
    ("S", S, "**The `date` parameter is strict (2a plan).**"),
    ("S", S, "| 401; 422 and 503 are documented as on every signed-in route (2a plan) |"),
    ("S", S, "and a 1–300-char name (fits_draft_limits; 2a plan)"),
    ("S", S, "That test, `test_cap_429_not_replayed`, makes its five creates through the repo"),
    ("S", S, "and a set name of 1–300 characters, the Occasion field's limit (2a plan)."),
    ("S", S, "(a Sunday Dec 25 or Jan 6) `weekday_feast_name(d)`"),
    ("S", S, "**First Sunday after Christmas Day** (a Sunday from Dec 26 to Jan 1)"),
    ("S", S, "**Except on All Saints Day (2a plan):**"),
    ("S", S, "**Contingency shim: not in force (2a plan).**"),
    ("S", S, "**Source deadline (2a plan).**"),
    ("S", S, "**Not written: the contingency is not in force (2a plan).**"),
    ("S", S, "(`test_cap_429_not_replayed`) is unchanged**"),
    ("S", S, "or by the computed ordinal when `sunday_name(d)` is \"All Saints Day\" (2a plan)"),
    ("S", S, "with an `httpx.MockTransport` (2a plan), because `sf.httpx.get` is no longer the call site."),
    ("runbook", RB, "while it is unset, `GET /translations` returns `esv_available: false`"),
]
ABSENT = [
    ("F", F, "tests that create more than 3 churches"),
    ("S", S, "slice 2 updates it to advance the limiter's fake clock"),
    ("S", S, "it advances the limiter clock 60 s between creates"),
    ("S", S, "| 200 `TranslationsOut` | 401 |"),
    ("S", S, "InvalidInput(field=\"date\", message="),
    ("S", S, "InvalidInput(field=\"refs\", \""),
    ("S", S, "InvalidInput(field=\"translation\", \""),
    ("S", S, "UpstreamError(\"upstream_error\""),
    ("S", S, "UpstreamTimeout(\"upstream_timeout\""),
    ("S", S, "its assertions move to `respx` because"),
    ("runbook", RB, "| `ESV_API_KEY` | optional: enables the ESV translation (secret) | ops-1 |"),
]

failing = [f"MISSING in {name}: {needle}" for name, text, needle in PRESENT if needle not in text]
failing += [f"STILL in {name}: {needle}" for name, text, needle in ABSENT if needle in text]
for line in failing:
    print(line)
if failing:
    print(f"docs check: {len(failing)} of {len(PRESENT) + len(ABSENT)} failing")
    sys.exit(1)
print(f"docs check: ok ({len(PRESENT) + len(ABSENT)} needles)")
PY
.venv/bin/python "${TMPDIR:-/tmp}/slice2a_t12_docs_check.py" | head -1
.venv/bin/python "${TMPDIR:-/tmp}/slice2a_t12_docs_check.py" | tail -1
.venv/bin/python "${TMPDIR:-/tmp}/slice2a_t12_docs_check.py" > /dev/null; echo "exit=$?"
```

**Expected:** `MISSING in F: | §1.8, §2.7, §7.4 | *(2026-09-28, slice 2a)* Process-wide upstream budgets`, then `docs check: 39 of 39 failing` (every new text is missing and every old text is still there), then `exit=1`.

- [ ] **Step 3 (agent): Amend F (the four rows, and the bodies they index)**

Apply these eight replacements to `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`. Each `old` occurs exactly once; replacing a substring leaves the rest of its line as it is. The rows are dated 2026-09-28, the day the owner accepted the 2a outline, in the table's `*(date, slice)*` form; "owner" is left out because these are plan decisions under owner decision 1, not owner answers.

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, amendments table, four new rows after the last row (:82). Replace:

````markdown
Postgres race tests cover both. | 1b |
````

with:

````markdown
Postgres race tests cover both. | 1b |
| §1.8, §2.7, §7.4 | *(2026-09-28, slice 2a)* Process-wide upstream budgets in `integrations/budget.py`: `bible_api` 15 per 30 s; `esv` 60 per minute, 1 000 per hour and 5 000 per day. `try_acquire` never waits, and a part that gets no token is `unavailable` and never cached. `POST /scripture/passages` has a 20 s deadline per request on the pool all requests share. `GET /lectionary/readings` has a 20 s deadline on its two sources: a source still running then counts as timed out for that request. | 2, 2a |
| §2.3 | *(2026-09-28, slice 2a)* Item 5's one recorded exception: `scripture_fetcher._esv_key()` keeps reading `ESV_API_KEY` from the environment until slice 7 moves the key into `api/settings.py`, because frozen Streamlit's Settings code and its test call the zero-argument `available_translations()`. | 2, 2a |
| Acceptance 13 | *(2026-09-28, slice 2a)* The upstream budgets (`integrations/budget.py`) join the rate limiter, `TTLCache` and `integrations/http.py`. | 2, 2a |
| §1.8 | *(2026-09-28, slice 2a)* The `church_create` test rule counts requests, not creates: a test that makes more than 3 `POST /churches` requests as one user (422s and replays count) advances the limiter's test clock or resets it. Slice 1's 6th-create test makes its five creates through the repo, so it is unchanged. | 2a |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §1.8 timeouts table, the lectionary row (:262). Replace:

````markdown
TTL cache: success 24 h, failure 5 min. | 15 s | 25 000 |
````

with:

````markdown
TTL cache: success 24 h, failure 5 min. A 20 s deadline on the two sources (§2.7). | 15 s on an idle pool; at most 20 s | 25 000 |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §1.8 timeouts table, the passages row (:263). Replace:

````markdown
| 10 s per part, ≤ 4 parts in parallel. Public-domain text cached 7 days; ESV never cached. |
````

with:

````markdown
| 10 s per part, ≤ 4 parts in parallel on a pool all requests share, inside a 20 s deadline per request; process-wide upstream budgets (§2.7). Public-domain text cached 7 days; ESV never cached. |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §1.8 `church_create` paragraph (:290). Replace:

````markdown
(tests that create more than 3 churches advance the limiter's test clock or reset it between creates)
````

with:

````markdown
(tests that make more than 3 `POST /churches` requests as one user, 422s and replays included, advance the limiter's test clock or reset it between requests; *amendment 2026-09-28, slice 2a*)
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §2.3 item 5 (:425). Replace:

````markdown
   - `load_dotenv()` runs only in entry points: `api/main.py` and the CLIs.
````

with:

````markdown
   - `load_dotenv()` runs only in entry points: `api/main.py` and the CLIs.
   - One recorded exception (*amendment 2026-09-28, slice 2a*): `scripture_fetcher._esv_key()` keeps reading `ESV_API_KEY` from the environment until slice 7 moves the key into `api/settings.py`. Frozen Streamlit's Settings code and its test call the zero-argument `available_translations()`, and slice 7 deletes both. The key never leaves the backend.
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §2.7 (:494). Replace:

````markdown
  Parallel upstream calls use a `ThreadPoolExecutor(max_workers=4)` owned by the usecase.
````

with:

````markdown
  Parallel upstream calls use a `ThreadPoolExecutor(max_workers=4)` owned by the usecase.
- **Upstream budgets** (*amendment 2026-09-28, slice 2a*): `integrations/budget.py` keeps one token budget per upstream for the whole process, shared by every user and request: `bible_api` 15 per 30 s; `esv` 60 per minute **and** 1 000 per hour **and** 5 000 per day. `try_acquire(upstream) -> bool` never waits. A part that gets no token is not sent, comes back `unavailable` and is never cached. Cache hits take no token.
- **Deadlines on the shared pools** (*amendment 2026-09-28, slice 2a*): `POST /scripture/passages` waits at most 20 s per request for its parts; parts unfinished by then are `unavailable`, and parts not yet started are cancelled. `GET /lectionary/readings` waits at most 20 s for its two sources; a source still running then counts as timed out for that request, and its loader finishes and caches its own outcome. Either way a request answers inside its client timeout however busy the pool is.
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, §7.4 bible-api row (:1290). Replace:

````markdown
| Concurrency 4, 7-day public-domain cache, no ESV cache, `scripture` bucket |
````

with:

````markdown
| Concurrency 4, 7-day public-domain cache, no ESV cache, `scripture` bucket; process-wide `bible_api` and `esv` budgets and a 20 s deadline per request (§2.7, *amendment 2026-09-28, slice 2a*) |
````

`docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, acceptance criterion 13 (:1333). Replace:

````markdown
13. The rate limiter, `TTLCache` and `integrations/http.py` exist
````

with:

````markdown
13. The rate limiter, the upstream budgets (`integrations/budget.py`), `TTLCache` and `integrations/http.py` exist
````

- [ ] **Step 4 (agent): Correct S**

Apply these twenty-two replacements to `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`. Each `old` occurs exactly once (the :608 and :610 anchors include the words before the arrow, because :891 repeats the same calls).

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, header, after the "2a deploys first" line (:8). Replace:

````markdown
2a deploys first; every change is additive (foundations §1.11).
````

with:

````markdown
2a deploys first; every change is additive (foundations §1.11).

Corrections made while planning 2a (`docs/superpowers/plans/2026-09-28-slice-2a-backend.md`, 2026-09-28) are marked "(2a plan)" where they are made.
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, API, after the `query.` paragraph (:204). Replace:

````markdown
(No client-side error code is added: an upstream passage failure is data, not an error; see Queries.)
````

with:

````markdown
(No client-side error code is added: an upstream passage failure is data, not an error; see Queries.)

**The `date` parameter is strict (2a plan).** `?date=` takes only `YYYY-MM-DD`: `IsoDate` in `api/schemas.py` passes a string only when it matches `\d{4}-\d{2}-\d{2}` in full, and then parses it as a `date`. Pydantic's plain `date` would also take "0" and datetimes such as `2026-03-29T00:00:00`, which breaks "never normalized". Every other form, and an impossible date such as `2026-02-30`, gets `fields.date` "Not a valid value."; a missing `date` gets "Required.". The OpenAPI schema still says `format: date`. Every route below also documents 422 and 503, as every signed-in route does (`test_routes_document_the_error_body`).
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, API table, the `/translations` row (:209). Replace:

````markdown
| GET | `/translations` | user | – | 200 `TranslationsOut` | 401 |
````

with:

````markdown
| GET | `/translations` | user | – | 200 `TranslationsOut` | 401; 422 and 503 are documented as on every signed-in route (2a plan) |
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `ReadingSetOut` (:222). Replace:

````markdown
# guaranteed: 1–20 items, each 1–200 chars (fits_draft_limits)
````

with:

````markdown
# guaranteed: 1–20 items, each 1–200 chars, and a 1–300-char name (fits_draft_limits; 2a plan)
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Rate-limit buckets, `church_create` paragraph (:302). Replace:

````markdown
Slice 1's 6th-create test must still see the cap message: slice 2 updates it to advance the limiter's fake clock (`set_clock_for_tests`) 60 s between creates, so the cap, not the bucket, answers the 6th.
````

with:

````markdown
Slice 1's 6th-create test must still see the cap message. That test, `test_cap_429_not_replayed`, makes its five creates through the repo and then only 2 POSTs, so it is unchanged. The slice 1 test that makes 4 POSTs as one user, `test_blank_then_corrected_with_new_key_201`, advances the limiter's fake clock (`set_clock_for_tests`) 60 s before its 4th, and `test_creates_spaced_a_minute_apart_meet_the_cap_message` checks over HTTP that creates 60 s apart meet the cap message on the 6th (2a plan).
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Lectionary domain, the draft-limit guard (:431). Replace:

````markdown
- **Draft-limit guard, `fits_draft_limits(set) -> bool`:** 1–20 lines, each 1–200 characters (the draft's and 5a's `ServiceDraft` limits, inv. §2.1).
````

with:

````markdown
- **Draft-limit guard, `fits_draft_limits(set) -> bool`:** 1–20 lines, each 1–200 characters (the draft's and 5a's `ServiceDraft` limits, inv. §2.1), and a set name of 1–300 characters, the Occasion field's limit (2a plan). A Lectio group has no name until `merge` names it, so `merge` applies the name check to each Lectio-only set after `lectio_set_name`.
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Names for Lectio-only sets, item 2 (:440). Replace:

````markdown
2. for a Sunday, `sunday_name(d)`;
````

with:

````markdown
2. for a Sunday, `sunday_name(d)`, and when that is None (a Sunday Dec 25 or Jan 6) `weekday_feast_name(d)`, so the day is "Nativity of the Lord" or "Epiphany of the Lord" (owner answer Q3, 2a plan);
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `sunday_name` coverage (:447). Replace:

````markdown
**Reign of Christ** (the Sunday before Advent 1). The existing wording stays
````

with:

````markdown
**Reign of Christ** (the Sunday before Advent 1); **First Sunday after Christmas Day** (a Sunday from Dec 26 to Jan 1) and **Second Sunday after Christmas Day** (a Sunday from Jan 2 to Jan 5) (owner answer Q3, 2a plan). A Sunday Dec 25 or Jan 6 has no Sunday name. The existing wording stays
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Vanderbilt row rename (:454). Replace:

````markdown
so this never falls back to the raw text).
````

with:

````markdown
so this never falls back to the raw text). **Except on All Saints Day (2a plan):** when `sunday_name(d)` is "All Saints Day", the Proper row takes the computed ordinal instead ("Twenty-Third Sunday after Pentecost" on 2026-11-01), as the merge table below and AC1 require. This rule and the merge table disagreed on that date, and the owner accepted the merge table's name on 2026-09-28. The check is on the computed name, not on how Vanderbilt spells its own All Saints row.
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Contingency shim (:544). Replace:

````markdown
**Contingency shim** (only if the F §6.1 item 6 contingency is in force, i.e. Streamlit still runs from `main`).
````

with:

````markdown
**Contingency shim: not in force (2a plan).** F §6.1 records that item 6's contingency is not in effect (production Streamlit is https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`), so 2a writes neither the shim nor `test_legacy_lectionary_shim.py`, and `app.py` on `main` no longer imports once `get_readings_for_date_string` is deleted. The design is kept for the record: **Contingency shim** (only if the F §6.1 item 6 contingency is in force, i.e. Streamlit still runs from `main`).
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `usecases/lectionary.py` step 1 (:579). Replace:

````markdown
raise `InvalidInput(field="date", message="Enter a date between 1900 and 2199.")`.
````

with:

````markdown
raise `InvalidInput("Enter a date between 1900 and 2199.", field="date")` (message first, as `DomainError` takes it; 2a plan).
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `usecases/lectionary.py` step 2, the worst case (:584). Replace:

````markdown
The worst case is ~15 s, down from ~35 s sequential (inv. C1).
````

with:

````markdown
The worst case is ~15 s, down from ~35 s sequential (inv. C1).

   **Source deadline (2a plan).** Both futures are awaited with `concurrent.futures.wait(..., timeout=DEADLINE_SECONDS)`, 20 s. A source still running then is `SourceFailed(timeout=True)` for this request; its loader keeps running and caches its own outcome. The ~15 s worst case holds only for an idle pool: single-flight waiters for one Vanderbilt year sit inside the 4 workers, so concurrent cold lookups can queue a Lectio task, and the deadline keeps every request inside the 25 s client timeout, at the cost of a `partial` 200 or a 504 under that load.
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `usecases/lectionary.py` step 4, the 502 (:587). Replace:

````markdown
`UpstreamError("upstream_error", "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.")`
````

with:

````markdown
`UpstreamError("The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.", code="upstream_error")` (2a plan: message first, `code=` by keyword)
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `usecases/lectionary.py` step 4, the 504 (:588). Replace:

````markdown
`UpstreamTimeout("upstream_timeout", <same message>)`
````

with:

````markdown
`UpstreamTimeout(<same message>, code="upstream_timeout")`
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `plan_passages`, the refs check (:608). Replace:

````markdown
any ref blank after trimming → `InvalidInput(field="refs", "Enter a scripture reference.")`;
````

with:

````markdown
any ref blank after trimming → `InvalidInput("Enter a scripture reference.", field="refs")` (2a plan: message first, `field=` by keyword);
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `plan_passages`, the translation check (:609). Replace:

````markdown
→ `InvalidInput(field="translation", "Unknown or unavailable translation.")`;
````

with:

````markdown
→ `InvalidInput("Unknown or unavailable translation.", field="translation")`;
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `plan_passages`, the parts check (:610). Replace:

````markdown
more than 20 parts in total → `InvalidInput(field="refs", "Too many passages in one request.")`;
````

with:

````markdown
more than 20 parts in total → `InvalidInput("Too many passages in one request.", field="refs")`;
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Testing, the `test_usecase_passages.py` row (:891). Replace:

````markdown
and a blank ref → `InvalidInput(field="refs", "Enter a scripture reference.")`; 21 parts → `InvalidInput(field="refs", "Too many passages in one request.")`;
````

with:

````markdown
and a blank ref → `InvalidInput("Enter a scripture reference.", field="refs")`; 21 parts → `InvalidInput("Too many passages in one request.", field="refs")` (2a plan: message first);
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Testing, the `test_scripture_fetcher.py` row (:890). Replace:

````markdown
its assertions move to `respx` because `sf.httpx.get` is no longer the call site.
````

with:

````markdown
its assertions move to `integrations.http.set_http_for_tests` with an `httpx.MockTransport` (2a plan), because `sf.httpx.get` is no longer the call site.
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Testing, the shim row (:889). Replace:

````markdown
| `test_legacy_lectionary_shim.py` | **Only if the F §6.1 item 6 contingency is in force**
````

with:

````markdown
| `test_legacy_lectionary_shim.py` | **Not written: the contingency is not in force (2a plan).** **Only if the F §6.1 item 6 contingency is in force**
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, Testing, the `test_api_churches.py` row (:897). Replace:

````markdown
**Slice 1's 6th-create test is kept passing:** it advances the limiter clock 60 s between creates, and the 6th create in 24 h still returns slice 1's cap message
````

with:

````markdown
**Slice 1's 6th-create test (`test_cap_429_not_replayed`) is unchanged**, because its five creates go through the repo and it makes only 2 POSTs; `test_blank_then_corrected_with_new_key_201` makes 4 POSTs, so it advances the limiter clock 60 s before the 4th (2a plan). With creates spaced 60 s apart over HTTP, the 6th create in 24 h still returns slice 1's cap message
````

`docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, AC4 (:942). Replace:

````markdown
A Vanderbilt "Proper N (M)" row name is replaced by `sunday_name(d)`; a specifically named Vanderbilt row is not.
````

with:

````markdown
A Vanderbilt "Proper N (M)" row name is replaced by `sunday_name(d)`, or by the computed ordinal when `sunday_name(d)` is "All Saints Day" (2a plan); a specifically named Vanderbilt row is not.
````

- [ ] **Step 5 (agent): Make the corrections that depend on the recordings (clarifications 19 and 41; T12-5)**

Run from the repo root (respx answers from the Task 1 fixtures; nothing leaves the machine):

```bash
.venv/bin/python - <<'PY'
"""Task 12: S corrections that depend on the recordings (clarifications 19 and 41).
Run from the repo root. Nothing leaves the machine: respx answers every call
from the Task 1 fixtures, and an unmatched request raises."""
import json
import sys
from datetime import date
from pathlib import Path

sys.path[:0] = [".", "backend"]

import respx  # noqa: E402

import vanderbilt_lectionary as vl  # noqa: E402
from tests.upstream_fixtures import FIXTURES_DIR, route_lectio, route_vanderbilt  # noqa: E402
from usecases import lectionary  # noqa: E402

SPEC = Path("docs/superpowers/specs/2026-09-25-slice-2-readings-design.md")
text = SPEC.read_text(encoding="utf-8")
changed = False


def meta(kind: str, name: str) -> dict:
    return json.loads((FIXTURES_DIR / kind / f"{name}.meta.json").read_text(encoding="utf-8"))


vanderbilt_meta = meta("vanderbilt", "2025-26")
recorded_on = vanderbilt_meta["recorded_at"][:10]

# Clarification 19: a Vanderbilt media type that Task 7 added to VANDERBILT_MEDIA_TYPES.
extra = sorted(vl.VANDERBILT_MEDIA_TYPES - {"text/plain", "text/csv"})
if extra:
    old = "  - 200 `text/plain` or `text/csv` → the text;"
    types = ", ".join(f"`{t}`" for t in extra)
    new = (f"  - 200 `text/plain`, `text/csv` or {types} → the text ({types}: what Vanderbilt served "
           f"when the fixtures were recorded on {recorded_on}; 2a plan);")
    assert text.count(old) == 1, "the fetch_vanderbilt_year 200 line is not as Task 12 expects"
    text = text.replace(old, new)
    changed = True
    print(f"media types: S now lists {types}")
else:
    print("media types: text/plain and text/csv only: no edit")

# Clarification 41: S's Palm Sunday example against the recording.
HEAD = "**Example** (`GET /lectionary/readings?date=2026-03-29`):"
if vanderbilt_meta["synthetic"] or meta("lectio", "2026-03-29")["synthetic"]:
    print("palm sunday: a fixture is synthetic (built from S): no edit")
else:
    d = date(2026, 3, 29)
    with respx.mock(assert_all_called=True) as mock:
        route_lectio(mock, d)
        route_vanderbilt(mock, "2025-26")
        result = lectionary.readings_for_date(d)
    recorded = {
        "date": result.date.isoformat(), "status": result.status, "partial": result.partial,
        "default_index": result.default_index,
        "reading_sets": [{"name": s.name, "source": s.source, "scriptures": list(s.scriptures)}
                         for s in result.reading_sets],
    }
    before, rest = text.split(HEAD + "\n\n```json\n", 1)
    block, after = rest.split("\n```\n", 1)
    if json.loads(block) == recorded:
        print("palm sunday: S's example matches the recording: no edit")
    else:
        def j(value):
            return json.dumps(value, ensure_ascii=False)

        first = (f'{{"date": {j(recorded["date"])}, "status": {j(recorded["status"])}, '
                 f'"partial": {j(recorded["partial"])}, "default_index": {j(recorded["default_index"])},')
        sets = ",\n".join(f'   {{"name": {j(s["name"])}, "source": {j(s["source"])},\n'
                          f'    "scriptures": {j(s["scriptures"])}}}' for s in recorded["reading_sets"])
        head = (f"**Example** (`GET /lectionary/readings?date=2026-03-29`, as the fixtures recorded on "
                f"{recorded_on} answer it; 2a plan):")
        text = before + head + "\n\n```json\n" + first + '\n "reading_sets": [\n' + sets + "]}\n```\n" + after
        changed = True
        print("palm sunday: S's example replaced by the recorded answer")

if changed:
    SPEC.write_text(text, encoding="utf-8")
PY
git diff --stat -- docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
```

**Expected:** two lines, one per check. With Task 1's recordings as S describes them: `media types: text/plain and text/csv only: no edit` and `palm sunday: S's example matches the recording: no edit` (or `palm sunday: a fixture is synthetic (built from S): no edit`). If Task 7 added a media type, the first line is `media types: S now lists <types>`, and S :517 names the type with the recording date. If the recorded Palm Sunday answer differs from S's example (the case where Task 8's `test_palm_sunday_200_shape` asserts the recorded equivalent), the second line is `palm sunday: S's example replaced by the recorded answer`, and S's example becomes the recorded JSON in the same layout under the heading `**Example** (`GET /lectionary/readings?date=2026-03-29`, as the fixtures recorded on <YYYY-MM-DD> answer it; 2a plan):`. In every case `git diff --stat` shows the one S file. If the controller passed owner-approved S text from a Task 6b stop (T12-5), apply it now, add "(2a plan)" at its end, and name it in Step 8's commit message.

If the script fails with `AllMockedAssertionError` or an unmatched-request error, Task 7's respx helpers no longer match the fetch URLs: stop and report; do not edit S by hand.

- [ ] **Step 6 (agent): The runbook's `ESV_API_KEY` row**

Apply this replacement to `docs/ops-runbook.md` (the row occurs once; no `[owner` marker is added):

`docs/ops-runbook.md`, Environments and variables, the `ESV_API_KEY` row (:42). Replace:

````markdown
| `ESV_API_KEY` | optional: enables the ESV translation (secret) | ops-1 |
````

with:

````markdown
| `ESV_API_KEY` | optional: enables the ESV translation (secret). The new app reads it from the environment (`scripture_fetcher._esv_key()`) until slice 7 moves it into `api/settings.py`; while it is unset, `GET /translations` returns `esv_available: false` and ESV is hidden. | ops-1; read by the new app since slice 2a |
````

- [ ] **Step 7 (agent): Run the docs check, the docs tests, the whole backend suite and the owner-marker check**

```bash
.venv/bin/python "${TMPDIR:-/tmp}/slice2a_t12_docs_check.py"
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
grep -c '^| §4.3 |' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
git diff --stat
```

**Expected:** `docs check: ok (39 needles)`; `89 passed in <t>s`; `971 passed, 9 skipped in <t>s`; `4`; `1`; `git diff --stat` lists exactly `docs/ops-runbook.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` and `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md` (about `3 files changed, 38 insertions(+), 25 deletions(-)`, a few more on S if Step 5 edited it). The frontend is not rerun, because no frontend file changed: it stays at `221 passed` in 34 files. If the backend count is not 971 + 9 skipped, stop and find why.

- [ ] **Step 8 (agent): Commit, and delete the check script**

```bash
git add docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/superpowers/specs/2026-09-25-slice-2-readings-design.md docs/ops-runbook.md
git commit -m "Docs: slice 2a amendments to F and corrections to S (F §1.8, §2.3, §2.7, §7.4, acceptance 13; S API, Lectionary domain, Passages, Testing, AC4)" -m "F gains four amendment rows, each stated in its section: the process-wide bible_api and esv budgets and the 20 s passages and lectionary deadlines (§1.8 table, §2.7, §7.4); the ESV_API_KEY environment exception to §2.3 item 5 until slice 7; integrations/budget.py in acceptance 13; and the church_create test rule counting requests, not creates (F :290). S, marked (2a plan): test_cap_429_not_replayed is unchanged and the 4-POST key test advances the limiter clock (:302, :897); DomainError call forms put the message first; ?date= is strict YYYY-MM-DD and every route documents 422 and 503; set names are 1-300 characters; the Christmas-season Sunday names and the Sunday feast fallback (owner answer Q3); a Proper row on All Saints Day takes the computed ordinal (:454, AC4); the 20 s lectionary source deadline; the contingency shim is not in force; the scripture_fetcher test row names Task 2's MockTransport seam, not respx (:890). The runbook says the new app reads ESV_API_KEY and hides ESV while it is unset." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
rm -f "${TMPDIR:-/tmp}/slice2a_t12_docs_check.py"
git log --oneline -1
git status --short
```

**Expected:** `<sha> Docs: slice 2a amendments to F and corrections to S (F §1.8, §2.3, §2.7, §7.4, acceptance 13; S API, Lectionary domain, Passages, Testing, AC4)`, one commit with three files changed; then only `?? .claude/`. If Step 5 changed S, add one sentence to the second `-m` before running it: "Step 5 corrected S from the recordings: " followed by Step 5's printed line(s) that are not "no edit".

- [ ] **Step 9 (agent): Review checkpoint**

Read `git show --stat HEAD` (3 files) and `git show HEAD -- docs/superpowers/specs/2026-09-25-migration-foundations-design.md`. Check against this task: F's table ends with the four 2a rows and still has exactly one `| §4.3 |` row; the §1.8 table, the `church_create` paragraph, §2.3 item 5, §2.7, the §7.4 bible-api row and acceptance 13 each state what their row says; no F text says "tests that create more than 3 churches". In S, every correction carries "(2a plan)" (or "owner answer Q3, 2a plan"), no `DomainError` call puts a keyword before a positional argument, and S :302 and :897 name `test_cap_429_not_replayed` as unchanged. The runbook adds no `[owner` marker.

Counts after Task 12: backend **971 passed, 9 skipped**; frontend **221 passed in 34 files** (unchanged; docs only).
### Task 13: dropped (owner answer Q4: no early draft PR)
### Task 14: Whole-branch verification and the slice 2a pull request (owner's yes before the push and before ready) (S Testing, Acceptance criteria 3, 9, 13; F §2.2, §2.5, §2.7, §5.4; owner decisions 2 and 4; owner answers Q4, Q5; clarifications 23, 32)

The whole branch is checked in one place before anyone reviews it: both suites (and the threaded tests three times over, so a flaky test is caught here and not in CI), the Postgres marker count, types, lint, the frontend build, the two generated API files and the shape 2b will consume, the AC3 / AC13 / layering / log / route gates, the exact list of changed paths, and the exact list of commits against this plan. Then, on the owner's first yes, the agent pushes `claude/slice-2-plan` for the first time and opens the PR as a draft, so CI runs without asking anyone to review yet (owner answer Q4: no early draft PR, so this is the first push). When CI is green, the agent reports the CI numbers and, on the owner's second yes, marks the PR ready for review. Merging is not part of this task (Task 15, its own yes).

`origin/main` may have moved since the branch was cut from `55f1b11`. Step 1 merges it if the branch is behind, and every later step runs on the merged tree.

Below, `<scratch>` is the absolute path of the session's scratchpad directory (any empty temp directory will do); write it out literally in each command. `<N>` is the PR number that Step 10 prints. Every `gh` command uses `-R bbrown62450/church`.

The local branch's upstream is `origin/main` (it was cut from it), so never run a bare `git push`: Step 10 pushes with an explicit `origin claude/slice-2-plan` and `-u`, which also moves the upstream to `origin/claude/slice-2-plan`.

**Files:** none changed (the plan is already the branch's first commit). A local or CI failure is fixed in the owning task's files (Step 14), never here.

**Interfaces:**
- Consumes:
  - Everything from Tasks 1–12, in particular:
    - this plan's commit steps: each task's `git commit -m` subject (Step 8 reads them from `docs/superpowers/plans/2026-09-28-slice-2a-backend.md`, between `### Task 1:` and `### Task 14:`);
    - the cumulative counts each task's last run step states: 800, 816, 837, 841, 856, 866, 884, 912, 921, 938, 960, 971, 971 (Tasks 1, 2, 3, 4, 5, 6a, 6b, 7, 8, 9, 10, 11, 12);
    - `backend/tests/test_route_guards.py::USER_SCOPED` and `CHURCH_SCOPED_TODAY` (Tasks 8, 10, 11);
    - `api.ratelimit.BUCKETS: dict[str, tuple[Rule, ...]]` with `Rule(scope, capacity, per_seconds)` and `integrations.budget.BUDGETS: dict[str, tuple[tuple[int, float], ...]]` (Task 3);
    - the log calls `reading_set_dropped` (Task 6b, `backend/vanderbilt_lectionary.py`), `lectionary_lookup` (Task 7, `backend/usecases/lectionary.py`), `passage_part_skipped` and `passage_part_failed` (Task 9, `backend/scripture_fetcher.py`), `passages_deadline` (Task 10, `backend/usecases/passages.py`);
    - the fixture sidecars `backend/tests/fixtures/<kind>/<name>.meta.json` with `"synthetic": bool` and `"recorded_at": str` (Task 1);
    - the OpenAPI components 2b consumes: `LectionaryOut`, `ReadingSetOut` (Task 8), `PassagesIn`, `PassagesOut`, `PassageOut`, `PassageSectionOut` (Task 10), `TranslationsOut`, `TranslationOut`, `ChurchProfileOut` (Task 11);
    - `backend/scripts/export_openapi.py` (prints `Wrote <path>`) and `npm run gen:api` (1a Tasks 13 and 15).
  - CI (`.github/workflows/ci.yml`, unchanged by 2a): jobs `backend` (`pip install -r requirements-dev.txt`, which now brings respx; `python -m pytest -q`), `backend-postgres` (steps `Migrate the empty database to head`, `The models match the migrated schema`, `Every revision downgrades`, `Migrate to head again`, `Identity smoke (ops-2)`, `Postgres-only tests`), `frontend` (lint, typecheck, `API types match the OpenAPI snapshot (F §5.4)`, test, build). `pull_request` uses the default activity types, so CI runs when the draft is opened and does not rerun when it is marked ready.
- Produces:
  - PR `<N>` (`claude/slice-2-plan` → `main`), titled `Slice 2a readings backend: lectionary, passages, translations, rate limits`, not a draft after Step 13, CI green on the branch head, its body holding the fixtures line (recorded or hand-built, from the sidecars), the line `Tests: backend 798 → 971 passed, 9 → 9 skipped; frontend 221 → 221 in 34 files` and ending with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Later user: Task 15 (the pre-merge gate, the merge on the owner's yes, the deploy check and the "Slice 2a record").

- [ ] **Step 1: Bring the branch up to date with `origin/main` (agent)**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD | tail -1
```

**Expected,** in order: `?? .claude/`; the fetch prints nothing or only updated refs; `0`; `55f1b11 Merge pull request #19 from bbrown62450/claude/slice-1b-records` (or a later merge the owner made); the branch's oldest commit, `<sha> Plan: slice 2a backend (F, S slice 2; owner answers 2026-09-28)`.
- If the count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan (Task 14)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. On a conflict, run `git merge --abort`, stop and tell the owner which files conflict (dated records on `main` are never edited by a merge resolution the owner has not seen). Without a conflict, continue: Steps 2–8 run on the merged tree. If the merge brought new tests, the Step 2 and Step 3 totals differ by exactly those; name them in the Step 9 message. Any other difference: stop and ask.
- If `git status --short` shows anything besides `?? .claude/`, stop: commit it in its owning task or ask the owner.

- [ ] **Step 2: Run the backend suite, the Postgres marker count and the threaded tests three times (agent)**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_cache.py backend/tests/test_usecase_lectionary.py backend/tests/test_usecase_passages.py 2>&1 | tail -1; done
```

**Expected:**
- `971 passed, 9 skipped in <t>s` (baseline 798 passed, 9 skipped; after Tasks 1, 2, 3, 4, 5, 6a, 6b, 7, 8, 9, 10, 11, 12: 800, 816, 837, 841, 856, 866, 884, 912, 921, 938 (Task 9 adds 22 and deletes the 5 tests of `test_scripture_translations.py`), 960, 971, 971). The `streamlit_tests/` folder is in `testpaths` (`pytest.ini`), so this run also proves `streamlit_tests/test_settings_prompts_translation.py` still passes against the refactored `scripture_fetcher` (S "Configuration exception").
- `9 skipped, 971 deselected in <t>s` (exactly nine tests carry the `postgres` marker, 1a's five and 1b's four; 2a adds none, and there is no `TEST_DATABASE_URL` here).
- `46 passed in <t>s`, three times (`test_cache.py` 9, `test_usecase_lectionary.py` 28, `test_usecase_passages.py` 9: the files whose tests block pool workers, race single-flight loads or wait on deadlines, clarification 39).

Any other number: stop and find the task whose count drifted (each task's last run step states its cumulative total). A threaded run that fails even once is a failure (Step 14): CI runs each test once, and a test that fails one time in three would block the merge at random.

- [ ] **Step 3: Run the frontend tests, types and lint (agent)**

```bash
(cd frontend && npm test && npm run typecheck && npm run lint)
```

**Expected:** Vitest's summary ` Test Files  34 passed (34)` and `      Tests  221 passed (221)` (unchanged since `55f1b11`: 2a changes no frontend source, only the two generated API files in Tasks 4, 8, 10 and 11); no `stderr` block with `act(` or `Warning:`; `tsc --noEmit` prints nothing; `eslint` prints nothing. The command exits 0.

- [ ] **Step 4: Build the frontend with CI's placeholder environment (agent)**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

**Expected:** the build prints `✓ Compiled successfully`, runs `tsc`, generates the static pages and ends with its route table, with no `Error:` line; then exactly:

```
/ /_global-error /_not-found /auth/callback /favicon.ico /join /login /welcome
```

(the same eight routes as after slice 1b: `/builder` and its steps are 2b). The build downloads the Geist fonts through `next/font/google`; if it fails only with `Failed to fetch` for a font (no network), say so in the Step 9 message and rely on CI's `frontend` job, which runs the same build (Step 12 checks it).

- [ ] **Step 5: Check that the generated files match the code, and the API shape 2b consumes (agent)**

```bash
.venv/bin/python backend/scripts/export_openapi.py && git diff --exit-code --stat frontend/src/lib/api/openapi.json; echo "openapi diff exit $?"
(cd frontend && npm run gen:api) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
grep -cE '"/(lectionary/readings|translations|scripture/passages)"' frontend/src/lib/api/openapi.json
grep -cE '^    "/(lectionary/readings|translations|scripture/passages)": \{' frontend/src/lib/api/schema.d.ts
grep -cE '^        (ChurchProfileOut|LectionaryOut|ReadingSetOut|TranslationsOut|TranslationOut|PassagesIn|PassagesOut|PassageOut|PassageSectionOut): \{' frontend/src/lib/api/schema.d.ts
git status --short
```

**Expected:** `Wrote /Users/…/frontend/src/lib/api/openapi.json` and `openapi diff exit 0`; openapi-typescript's `🚀 src/lib/api/openapi.json → src/lib/api/schema.d.ts` line and `schema diff exit 0`; `3` (the three new paths, one key each); `3`; `9` (the nine new components, each declared once); then only `?? .claude/`. A non-zero diff exit means an API change was committed without regenerating: run the same two commands, commit both generated files in the task that changed the API (Task 4, 8, 10 or 11; Step 14's rule), and start again at Step 2.

Then the shape, read from the committed snapshot:

```bash
.venv/bin/python - <<'EOF'
import json
spec = json.load(open("frontend/src/lib/api/openapi.json", encoding="utf-8"))
paths, schemas = spec["paths"], spec["components"]["schemas"]
for path, method in [("/lectionary/readings", "get"), ("/translations", "get"),
                     ("/scripture/passages", "post"), ("/church", "get"), ("/churches", "post")]:
    op = paths.get(path, {}).get(method)
    print(method.upper(), path, sorted(op["responses"]) if op else "MISSING")
op = paths.get("/lectionary/readings", {}).get("get") or {}
print("date param:", [(p["name"], p["in"], p.get("required"), p["schema"].get("format"))
                      for p in op.get("parameters", [])])
print("/church 200:", paths["/church"]["get"]["responses"]["200"]["content"]["application/json"]["schema"])
print("/me churches:", schemas["MeOut"]["properties"]["churches"]["items"])
for name in ["ChurchOut", "ChurchProfileOut", "LectionaryOut", "ReadingSetOut", "TranslationsOut",
             "TranslationOut", "PassagesIn", "PassagesOut", "PassageOut", "PassageSectionOut"]:
    print(name, sorted(schemas[name]["properties"]) if name in schemas else "MISSING")
BEFORE = {"ChurchOut", "CreateChurchIn", "ErrorBody", "ErrorDetail", "InviteAcceptOut", "InviteCodeIn",
          "InvitePreviewOut", "MeOut", "ReadyOut", "RubricModel", "RubricOut", "UserOut"}
NEW = {"ChurchProfileOut", "LectionaryOut", "ReadingSetOut", "TranslationsOut", "TranslationOut",
       "PassagesIn", "PassagesOut", "PassageOut", "PassageSectionOut"}
print("extra components:", sorted(set(schemas) - BEFORE - NEW))
print("paths:", len(paths))
EOF
```

**Expected,** exactly:

```
GET /lectionary/readings ['200', '401', '422', '429', '502', '503', '504']
GET /translations ['200', '401', '422', '503']
POST /scripture/passages ['200', '401', '422', '429', '503']
GET /church ['200', '401', '403', '422', '503']
POST /churches ['201', '401', '422', '429', '503']
date param: [('date', 'query', True, 'date')]
/church 200: {'$ref': '#/components/schemas/ChurchProfileOut'}
/me churches: {'$ref': '#/components/schemas/ChurchOut'}
ChurchOut ['id', 'name', 'role']
ChurchProfileOut ['bible_translation', 'effective_translation', 'effective_translation_label', 'id', 'name', 'role', 'timezone', 'timezone_valid']
LectionaryOut ['date', 'default_index', 'partial', 'reading_sets', 'status']
ReadingSetOut ['name', 'scriptures', 'source']
TranslationsOut ['default', 'esv_available', 'items']
TranslationOut ['id', 'label']
PassagesIn ['refs', 'translation']
PassagesOut ['passages', 'translation', 'translation_label']
PassageOut ['reference', 'sections', 'status']
PassageSectionOut ['reference', 'status', 'text']
extra components: []
paths: 11
```

These are the Global Constraints' documented statuses (`/church` and `/churches` unchanged), the strict `?date=` that keeps `format: date` (clarification 3), the additive `/church` with `/me` still on `ChurchOut` (AC6), S's Schemas field names, and the eight 1a/1b paths plus three. A line that differs names its owning task (Step 14): `/lectionary/readings`, `date param`, `LectionaryOut`, `ReadingSetOut` → Task 8; `/scripture/passages`, `Passage*` → Task 10; `/translations`, `/church`, `/me`, `ChurchProfileOut`, `Translation*` → Task 11; `/churches` → Task 4. An extra component is expected only when that task's **Interfaces** names it; otherwise stop and find why.

- [ ] **Step 6: Run the acceptance gates (agent)**

The AC3 / AC13 greps, the deletions and what stays untouched:

```bash
grep -nE 'httpx\.get|^_cache|get_readings_for_date|fetch_lectionary_year' backend/vanderbilt_lectionary.py; echo "vanderbilt grep exit $?"
grep -nE 'httpx\.get|^_cache|\[Could not load text\]' backend/scripture_fetcher.py backend/usecases/passages.py; echo "passages grep exit $?"
grep -nE '^\w+\s*(:[^=]*)?=\s*(\{|dict\(|defaultdict\(|OrderedDict\()' backend/vanderbilt_lectionary.py backend/scripture_fetcher.py backend/usecases/lectionary.py backend/usecases/passages.py | grep -i cache; echo "dict cache grep exit $?"
grep -nE 'httpx\.(get|post|put|patch|delete|head|request|stream|Client|AsyncClient)\(' backend/vanderbilt_lectionary.py backend/scripture_fetcher.py backend/scripture_refs.py backend/cache.py backend/token_bucket.py backend/integrations/budget.py backend/api/ratelimit.py backend/api/routes/lectionary.py backend/api/routes/reference.py backend/api/routes/scripture.py backend/usecases/lectionary.py backend/usecases/passages.py backend/usecases/church_profile.py; echo "outbound grep exit $?"
grep -c 'httpx.Client(' backend/integrations/http.py
grep -rnE 'get_readings_for_date|fetch_lectionary_year|_liturgical_sunday_name|_normalize_date_for_match|_liturgical_year_for_date' backend --include='*.py' --exclude-dir=tests; echo "old lookup grep exit $?"
grep -n "get_readings_for_date_string" app.py
test ! -e backend/tests/test_legacy_lectionary_shim.py && echo "no shim test"
test ! -e backend/tests/test_scripture_translations.py && echo "test_scripture_translations.py is gone"
grep -rnE 'os\.(getenv|environ)' backend/scripture_fetcher.py backend/vanderbilt_lectionary.py backend/scripture_refs.py backend/cache.py backend/token_bucket.py backend/integrations backend/usecases/lectionary.py backend/usecases/passages.py backend/usecases/church_profile.py backend/api/ratelimit.py backend/api/routes/lectionary.py backend/api/routes/reference.py backend/api/routes/scripture.py
(cd backend && env -u ESV_API_KEY ../.venv/bin/python -c "from scripture_fetcher import available_translations, translation_label, DEFAULT_TRANSLATION; print(DEFAULT_TRANSLATION, len(available_translations()), available_translations()[-1], translation_label('esv'))")
ls backend/api/ratelimit.py backend/integrations/budget.py backend/integrations/http.py backend/cache.py
grep -n "^class TTLCache" backend/cache.py
grep -n -A1 "^@pytest.fixture(autouse=True)" backend/tests/conftest.py | grep "def _no_network"
grep -n '^respx' requirements-dev.txt
.venv/bin/python -c "import respx, httpx; print(respx.__version__, httpx.__version__)"
git diff --quiet origin/main...HEAD -- app.py ui_helpers.py streamlit_tenancy.py streamlit_views streamlit_tests backend/worship_service.py; echo "streamlit files diff exit $?"
git diff --name-only origin/main...HEAD -- backend/requirements.txt backend/migrations backend/db backend/repos backend/alembic.ini .github docs/manual-verification.md | wc -l
(cd backend && ../.venv/bin/alembic heads)
grep -rIn -E -i 'authorization:|api[_-]?key|set-cookie|bearer [a-z0-9._-]{8,}|token [a-z0-9]{20,}' backend/tests/fixtures || echo "no secrets"
```

**Expected,** in order:
- `vanderbilt grep exit 1` (no output before it: no raw `httpx.get`, no `_cache` dict, no old lookup; AC3; Task 7);
- `passages grep exit 1` (no raw `httpx.get`, no `_cache`, no `[Could not load text]` sentinel; `get_passage_text` returns `None`; Tasks 9 and 10);
- `dict cache grep exit 1` (no module-level dict whose name mentions a cache in the four lectionary and passage modules; the caches are `TTLCache` objects, S "Streamlit coupling removed"; the other module-level dicts, `TRANSLATIONS` and Task 6a's feast tables, do not match);
- `outbound grep exit 1` (no 2a module calls httpx or builds a client itself: every upstream call goes through `integrations.http.get`, F §2.7; the legacy scripts such as `backend/worship_service.py` and `backend/notion_hymns.py` are outside 2a and not listed);
- `1` (`integrations/http.py` builds the one client, in `build_client`; Task 2);
- `old lookup grep exit 1` (no output before it; S "Deleted"; the tests folder is excluded because a test may name a deleted function to prove it is gone; Task 7);
- exactly `28:from vanderbilt_lectionary import get_readings_for_date_string` and `442:                readings_list = get_readings_for_date_string(service_date_str)` (the frozen `app.py` keeps its lines and cannot be imported on `main` any more; production Streamlit runs from `streamlit-frozen`; owner decision 2, clarification 23);
- `no shim test` (the F §6.1 item 6 contingency is off, owner decision 2);
- `test_scripture_translations.py is gone` (its 5 tests live in `test_scripture_fetcher.py`, Task 9);
- exactly one line, `backend/scripture_fetcher.py:<n>:    return os.getenv("ESV_API_KEY", "").strip()` (the recorded F §2.3.5 configuration exception until slice 7; no other 2a module reads the environment);
- `web 9 ('webbe', 'World English Bible, British (WEBBE)') English Standard Version (ESV)` (the zero-argument helpers the frozen `streamlit_views/settings.py:28` imports still work, with ESV hidden when `ESV_API_KEY` is unset; Task 9);
- the four paths, then `<n>:class TTLCache(Generic[K, V]):` (AC13, Tasks 2 and 3);
- one line ending `-def _no_network(monkeypatch):` (the autouse no-network guard is still active, AC13; F §5.3);
- `7:respx>=0.22` (Task 1), then `0.22.0 0.28.1` (a later `0.2x` respx is fine; httpx must still be `0.28.1`);
- `streamlit files diff exit 0` (`app.py`, `ui_helpers.py`, `streamlit_tenancy.py`, `streamlit_views/`, `streamlit_tests/` and `backend/worship_service.py` untouched; owner decision 2);
- `0` (`wc` pads it with spaces: 2a changes no runtime requirement, migration, model, repo, Alembic config, workflow or manual-check list; S "Data and migrations"; 2c owns the slice 2 manual checks);
- `0004_invites_reusable (head)` (no Alembic revision in 2a);
- `no secrets` (the recorded fixtures carry no header or key; Task 1). A match inside a Vanderbilt `Prayer` cell is liturgical text, not a secret: report it and go on.

Then the layering, log, route and configuration gates:

```bash
grep -rnE '^\s*(from|import) (fastapi|starlette|streamlit)' backend/usecases backend/integrations backend/cache.py backend/token_bucket.py backend/scripture_refs.py backend/vanderbilt_lectionary.py backend/scripture_fetcher.py; echo "layering grep exit $?"
(cd backend && ../.venv/bin/python -c "import sys, usecases.lectionary, usecases.passages, usecases.church_profile, integrations.http, integrations.budget, cache, token_bucket, scripture_refs, vanderbilt_lectionary, scripture_fetcher; print(sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}))")
(cd backend && ../.venv/bin/python -c "import sys, api.main; print(sorted(m for m in sys.modules if m.split('.')[0] == 'streamlit'))")
.venv/bin/python - <<'EOF'
import ast, pathlib
FILES = ["backend/integrations/http.py", "backend/integrations/budget.py", "backend/cache.py",
         "backend/token_bucket.py", "backend/api/ratelimit.py", "backend/scripture_refs.py",
         "backend/vanderbilt_lectionary.py", "backend/scripture_fetcher.py",
         "backend/usecases/lectionary.py", "backend/usecases/passages.py",
         "backend/usecases/church_profile.py", "backend/api/routes/lectionary.py",
         "backend/api/routes/reference.py", "backend/api/routes/scripture.py",
         "backend/api/routes/me.py", "backend/api/routes/churches.py"]
FORBIDDEN = {"url", "params", "headers", "body", "content", "payload", "token", "authorization",
             "api_key", "esv_key", "_esv_key", "query", "q", "text", "ref", "refs", "reference",
             "part", "parts"}
LEVELS = {"debug", "info", "warning", "error", "exception", "critical"}
RECEIVERS = {"logger", "log", "logging", "_log", "_logger", "LOGGER"}

def used(node):
    """Names and attribute names an argument reads; len(...) and type(...) only measure."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"len", "type"}:
        return set()
    if isinstance(node, ast.Attribute):
        return {node.attr} | (set() if isinstance(node.value, ast.Name) else used(node.value))
    if isinstance(node, ast.Name):
        return {node.id}
    out = set()
    for child in ast.iter_child_nodes(node):
        out |= used(child)
    return out

rows = []
for p in FILES:
    path = pathlib.Path(p)
    if not path.exists():
        rows.append(f"{p} MISSING")
        continue
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        f = getattr(node, "func", None)
        if (isinstance(node, ast.Call) and isinstance(f, ast.Attribute) and f.attr in LEVELS
                and isinstance(f.value, ast.Name) and f.value.id in RECEIVERS):
            names = set()
            for arg in list(node.args[1:]) + [k.value for k in node.keywords]:
                names |= used(arg)
            first = (node.args[0].value.split()[0] if node.args and isinstance(node.args[0], ast.Constant)
                     and isinstance(node.args[0].value, str) and node.args[0].value.split() else "<not a literal>")
            rows.append(f"{p} {f.attr} {first} forbidden={sorted(names & FORBIDDEN) or 'none'}")
print("\n".join(sorted(rows)) or "no log calls")
EOF
grep -nE '^\s*(async def |try:|except( |:))' backend/api/routes/lectionary.py backend/api/routes/reference.py backend/api/routes/scripture.py backend/api/routes/me.py backend/api/routes/churches.py; echo "routes grep exit $?"
grep -nE '^\s*(from|import) (httpx|integrations|vanderbilt_lectionary|scripture_fetcher|scripture_refs|cache|token_bucket|repos|db|sqlalchemy)([ .]|$)' backend/api/routes/lectionary.py backend/api/routes/reference.py backend/api/routes/scripture.py; echo "new routes import grep exit $?"
LC_ALL=C grep -rhoE 'rate_limit\("[a-z_]+"\)|consume\("[a-z_]+"' backend/api/routes | LC_ALL=C sort
(cd backend && ../.venv/bin/python -c "from tests.test_route_guards import USER_SCOPED, CHURCH_SCOPED_TODAY; print(len(USER_SCOPED), sorted(USER_SCOPED)); print(sorted(CHURCH_SCOPED_TODAY))")
(cd backend && ../.venv/bin/python -c "from api.ratelimit import BUCKETS; from integrations.budget import BUDGETS; print({k: [(r.scope, r.capacity, r.per_seconds) for r in v] for k, v in BUCKETS.items()}); print(BUDGETS)")
for r in origin/main HEAD; do git show "$r:docs/ops-runbook.md" | grep -n '\[owner' | grep -v 'An entry marked' | wc -l; done
git diff --name-only origin/main...HEAD | grep -E '(^|/)\.env' ; echo "env files: $?"
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -qx 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected,** in order:
- `layering grep exit 1` (no output before it: the usecases, the domain modules, `integrations/`, `cache.py` and `token_bucket.py` import no FastAPI, Starlette or Streamlit; F §2.2; Global Constraints "Layering and logging"; `api/ratelimit.py` may import FastAPI and is not listed);
- `[]` (none of them loads one of the three, even indirectly);
- `[]` (`api.main` with the `lectionary`, `reference` and `scripture` routers loads no Streamlit);
- exactly these five lines (the only log calls in 2a's modules; none passes a URL, query, header, body, token, key or a reference or part, which is the request payload and the ESV `q=` query; `len(...)` and `type(...)` only measure and are not counted; F §2.5, Global Constraints "Layering and logging", clarification 32):
  ```
  backend/scripture_fetcher.py info passage_part_skipped forbidden=none
  backend/scripture_fetcher.py warning passage_part_failed forbidden=none
  backend/usecases/lectionary.py info lectionary_lookup forbidden=none
  backend/usecases/passages.py warning passages_deadline forbidden=none
  backend/vanderbilt_lectionary.py warning reading_set_dropped forbidden=none
  ```
  A `MISSING` row means a planned module is absent (its task's commit is missing: Step 7). A row with a name other than `none` after `forbidden=` breaks the Global Constraints: fix the log call in its owning task (Step 14). A further row is expected only when its task's plan section shows that log call; the lectionary usecase must keep exactly one `info` row (S `usecases/lectionary.py` step 5: "Log one line");
- `routes grep exit 1` (no output before it: plain `def` routes, no `try`/`except` for domain errors; Global Constraints "Layering and logging");
- `new routes import grep exit 1` (the three new routes reach the upstreams, the caches and the database only through a usecase or `api.ratelimit`);
- exactly:
  ```
  consume("scripture"
  rate_limit("church_create")
  rate_limit("lectionary")
  ```
  (`/scripture/passages` charges per part after validation; `POST /churches` and `GET /lectionary/readings` use the dependency; `/translations` and `/church` are not rate-limited; S Rate-limit buckets; Tasks 4, 8, 10);
- `7 [('GET', '/lectionary/readings'), ('GET', '/me'), ('GET', '/translations'), ('POST', '/churches'), ('POST', '/invites/accept'), ('POST', '/invites/preview'), ('POST', '/scripture/passages')]` and then `[('GET', '/church'), ('GET', '/rubric'), ('PATCH', '/rubric')]` (AC9: the three new routes are user-scoped; `/church` stays church-guarded; Tasks 8, 10, 11);
- `{'lectionary': [('user', 120, 300)], 'scripture': [('user', 60, 300)], 'church_create': [('user', 3, 60)], 'ai': [('user', 40, 600), ('church', 400, 86400)], 'email': [('user', 10, 3600)]}` and then `{'bible_api': ((15, 30.0),), 'esv': ((60, 60.0), (1000, 3600.0), (5000, 86400.0))}` (Global Constraints "Buckets, budgets and caches"; Task 3; slices 3, 4, 5b and PRs #7 and #8 rely on `ai` and `email` as defined here);
- `4` twice (the runbook's `[owner` markers are unchanged; Task 12's ESV line carries no marker, and the "Slice 2a record" goes in Task 15's records PR; `wc` pads the number with spaces);
- `env files: 1` (grep found nothing: no `.env` file is on the branch);
- only `trailer check done` (every commit on the branch, a Step 1 merge included, ends with the trailer).

Any other output: stop, find the owning task (Step 14's table) and fix it there.

- [ ] **Step 7: Check the exact list of changed paths (agent)**

```bash
LC_ALL=C sort > "<scratch>/slice2a-expected-paths.txt" <<'EOF'
backend/api/main.py
backend/api/ratelimit.py
backend/api/routes/churches.py
backend/api/routes/lectionary.py
backend/api/routes/me.py
backend/api/routes/reference.py
backend/api/routes/scripture.py
backend/api/schemas.py
backend/cache.py
backend/integrations/__init__.py
backend/integrations/budget.py
backend/integrations/http.py
backend/scripts/record_fixtures.py
backend/scripture_fetcher.py
backend/scripture_refs.py
backend/tests/conftest.py
backend/tests/fixtures/README.md
backend/tests/fixtures/bible_api/isaiah_50_4-9.json
backend/tests/fixtures/bible_api/isaiah_50_4-9.meta.json
backend/tests/fixtures/bible_api/isaiah_50_4-9a.json
backend/tests/fixtures/bible_api/isaiah_50_4-9a.meta.json
backend/tests/fixtures/bible_api/luke_2_1-14_15-20.json
backend/tests/fixtures/bible_api/luke_2_1-14_15-20.meta.json
backend/tests/fixtures/esv/empty.json
backend/tests/fixtures/esv/empty.meta.json
backend/tests/fixtures/esv/success.json
backend/tests/fixtures/esv/success.meta.json
backend/tests/fixtures/lectio/2025-12-24.json
backend/tests/fixtures/lectio/2025-12-24.meta.json
backend/tests/fixtures/lectio/2025-12-25.json
backend/tests/fixtures/lectio/2025-12-25.meta.json
backend/tests/fixtures/lectio/2026-01-01.json
backend/tests/fixtures/lectio/2026-01-01.meta.json
backend/tests/fixtures/lectio/2026-02-18.json
backend/tests/fixtures/lectio/2026-02-18.meta.json
backend/tests/fixtures/lectio/2026-03-29.json
backend/tests/fixtures/lectio/2026-03-29.meta.json
backend/tests/fixtures/lectio/2026-04-03.json
backend/tests/fixtures/lectio/2026-04-03.meta.json
backend/tests/fixtures/lectio/2026-04-05.json
backend/tests/fixtures/lectio/2026-04-05.meta.json
backend/tests/fixtures/lectio/2026-05-14.json
backend/tests/fixtures/lectio/2026-05-14.meta.json
backend/tests/fixtures/lectio/2026-05-31.json
backend/tests/fixtures/lectio/2026-05-31.meta.json
backend/tests/fixtures/lectio/2026-09-29.json
backend/tests/fixtures/lectio/2026-09-29.meta.json
backend/tests/fixtures/lectio/2026-10-04.json
backend/tests/fixtures/lectio/2026-10-04.meta.json
backend/tests/fixtures/lectio/2026-11-01.json
backend/tests/fixtures/lectio/2026-11-01.meta.json
backend/tests/fixtures/lectio/2026-11-26.json
backend/tests/fixtures/lectio/2026-11-26.meta.json
backend/tests/fixtures/lectio/error_500.json
backend/tests/fixtures/lectio/error_500.meta.json
backend/tests/fixtures/lectio/html_200.html
backend/tests/fixtures/lectio/html_200.meta.json
backend/tests/fixtures/shared/scripture_refs.json
backend/tests/fixtures/vanderbilt/2025-26.csv
backend/tests/fixtures/vanderbilt/2025-26.meta.json
backend/tests/fixtures/vanderbilt/2026-27.csv
backend/tests/fixtures/vanderbilt/2026-27.meta.json
backend/tests/fixtures/vanderbilt/2027-28.csv
backend/tests/fixtures/vanderbilt/2027-28.meta.json
backend/tests/fixtures/vanderbilt/404.html
backend/tests/fixtures/vanderbilt/404.meta.json
backend/tests/fixtures/vanderbilt/html_200.html
backend/tests/fixtures/vanderbilt/html_200.meta.json
backend/tests/test_api_app.py
backend/tests/test_api_church_profile.py
backend/tests/test_api_churches.py
backend/tests/test_api_invites.py
backend/tests/test_api_lectionary.py
backend/tests/test_api_me.py
backend/tests/test_api_scripture.py
backend/tests/test_api_translations.py
backend/tests/test_budget.py
backend/tests/test_cache.py
backend/tests/test_fixtures_recorder.py
backend/tests/test_http_client.py
backend/tests/test_lectionary_domain.py
backend/tests/test_no_streamlit_in_core.py
backend/tests/test_ratelimit.py
backend/tests/test_route_guards.py
backend/tests/test_scripture_fetcher.py
backend/tests/test_scripture_refs.py
backend/tests/test_scripture_translations.py
backend/tests/test_usecase_lectionary.py
backend/tests/test_usecase_passages.py
backend/tests/upstream_fixtures.py
backend/token_bucket.py
backend/usecases/church_profile.py
backend/usecases/lectionary.py
backend/usecases/passages.py
backend/vanderbilt_lectionary.py
docs/ops-runbook.md
docs/superpowers/plans/2026-09-28-slice-2a-backend.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
frontend/src/lib/api/openapi.json
frontend/src/lib/api/schema.d.ts
requirements-dev.txt
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice2a-actual-paths.txt"
wc -l < "<scratch>/slice2a-expected-paths.txt"
wc -l < "<scratch>/slice2a-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice2a-expected-paths.txt" "<scratch>/slice2a-actual-paths.txt"
git diff --name-status --no-renames origin/main...HEAD | cut -c1 | sort | uniq -c
```

**Expected:** `102`; `102`; `comm` prints nothing; then `  82 A`, `   1 D` (`backend/tests/test_scripture_translations.py`, Task 9) and `  19 M`. The 102 are this plan's File Structure: 30 created code, test and plan files; 52 fixture files (Task 1's README and 25 bodies with their 25 sidecars, plus Task 5's `shared/scripture_refs.json`); 19 modified files (13 under `backend/`, `requirements-dev.txt`, the two generated API files, the two specs and `docs/ops-runbook.md`); and the one deletion. `docs/manual-verification.md` is not among them (2c appends the slice 2 checks). Any `comm` line:
- a tab-indented line (changed on the branch, not in the list): find the path in the **Files:** section of the task that touched it (`git log --format='%h %s' origin/main..HEAD -- '<that path>'` names the commit). If that task's **Files:** names it (for example a fixture whose recorded body Task 1 had to save under another name), it is expected: count it and continue. Anything else, in particular `app.py`, `ui_helpers.py`, `streamlit_tenancy.py`, `streamlit_views/…`, `streamlit_tests/…`, `backend/worship_service.py`, `backend/requirements.txt`, `backend/migrations/…`, `backend/db/…`, `backend/repos/…`, `.github/workflows/…` or any `frontend/src/` file other than the two generated ones: stop and find why the task touched it;
- an unindented line (in the list, not changed): the owning task's commit is missing; stop and find it.

- [ ] **Step 8: Check the exact list of commits against this plan (agent)**

```bash
.venv/bin/python - docs/superpowers/plans/2026-09-28-slice-2a-backend.md > "<scratch>/slice2a-plan-subjects.txt" <<'EOF'
import pathlib, re, sys
text = "\n" + pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
lines = text.split("\n### Task 1:", 1)[1].split("\n### Task 14:", 1)[0].splitlines()
for n, line in enumerate(lines):
    m = re.match(r"\s*git commit -m ([\"'])(.*)$", line)
    if not m:
        continue
    quote, rest = m.groups()
    if rest.startswith("$(cat <<"):
        print(lines[n + 1].strip())
        continue
    out, i = [], 0
    while i < len(rest):
        if quote == '"' and rest[i] == "\\" and i + 1 < len(rest):
            out.append(rest[i + 1])
            i += 2
            continue
        if rest[i] == quote:
            break
        out.append(rest[i])
        i += 1
    print("".join(out))
EOF
git log --reverse --no-merges --format=%s origin/main..HEAD > "<scratch>/slice2a-branch-subjects.txt"
wc -l < "<scratch>/slice2a-plan-subjects.txt"
wc -l < "<scratch>/slice2a-branch-subjects.txt"
diff "<scratch>/slice2a-plan-subjects.txt" "<scratch>/slice2a-branch-subjects.txt"; echo "commit list diff exit $?"
git log --reverse --format='%h %s' origin/main..HEAD
```

**Expected:** the same number twice (`14`: the plan commit and the fixtures commit from Task 1, then one commit each from Tasks 2, 3, 4, 5, 6a, 6b, 7, 8, 9, 10, 11 and 12); `commit list diff exit 0` with no output before it; then the 14 commits in task order, oldest first (plus a Step 1 merge, if there was one), beginning:

```
<sha> Plan: slice 2a backend (F, S slice 2; owner answers 2026-09-28)
<sha> Tests: upstream fixtures, their recorder and respx (F §5, S Testing "Fixtures")
<sha> Platform: outbound HTTP client and TTL cache (F §2.7, S New modules)
<sha> Platform: token bucket, rate limiter and upstream budgets (F §1.8; S Rate-limit buckets, Upstream budgets)
<sha> API: church_create burst guard on POST /churches (F §1.8; S Rate-limit buckets; AC7)
<sha> Scripture refs: book table, classifier, resolve_readings and the shared fixture (S scripture_refs.py; decision 9)
<sha> Lectionary: calendar and occasion names from the date alone (S Lectionary domain; decision A; owner answer Q3)
<sha> Lectionary: Vanderbilt and Lectio parsing, draft-limit guard and merge (S Lectionary domain; AC1, AC4)
<sha> Lectionary: fetchers, loaders and readings_for_date; the old lookup is deleted (S Fetchers, Loaders, usecases/lectionary.py; AC1-AC3)
<sha> API: GET /lectionary/readings with a strict date and the lectionary bucket (S API, Schemas; AC1, AC2, AC7, AC9)
<sha> Passages: sections, statuses, part cache and budgets in scripture_fetcher (F §2.3.3, §2.7; S Passages; AC5)
<sha> Passages: POST /scripture/passages, charged per part, on a shared pool with a 20 s deadline (S Passages, API row 3; F §1.8)
<sha> API: GET /translations and the GET /church profile fields (S API rows 2 and 4; AC6)
```

and ending with Task 12's docs commit, exactly as its commit step spells it. `diff` output is a failure unless it is one of these, each named in the Step 9 message:
- a `>` line `Fix: … (Task <n>, slice 2a final verification)` (a Step 14 fix);
- a `<` / `>` pair on the first line only, when the controller committed the plan before Task 1 under another subject (Task 1, Step 0 was then skipped);
- a `>` line `Plan: …` (a plan correction the controller committed during execution).

Anything else (a missing task commit, a commit the plan does not describe, two tasks squashed into one): stop and find why before asking the owner anything.

- [ ] **Step 9 (agent → OWNER): Ask for the go-ahead to push and open the draft PR**

Pushing is outward-facing, and owner answer Q4 dropped the early checkpoint, so nothing is on GitHub yet. Check the remote branch, the CLI login and the commit count:

```bash
git ls-remote --heads origin claude/slice-2-plan
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan --state all --json number,state,url
git rev-list --count origin/main..HEAD
```

**Expected:** nothing (the branch is not on GitHub yet); one `✓ Logged in to github.com account <login> (keyring)` line; `[]` (no PR from this branch, open or closed); the Step 8 count (14, plus 1 for a Step 1 merge, plus any Step 14 fixes). If `ls-remote` prints a sha or the list is not `[]`, someone pushed or opened a PR already: stop and ask the owner. If `gh` is not logged in, ask the owner to run `gh auth login` themselves.

Send the owner exactly this message, with `<count>` replaced by the value above, and wait for a clear yes:

> Slice 2a is verified locally: backend 971 passed, 9 skipped (798 before); frontend 221 passed in 34 files; typecheck, lint and build clean; OpenAPI and API types in sync, with the nine new response and request types 2b needs; the gates are clean (no dict cache or raw `httpx.get` left in the lectionary and passage code, no `[Could not load text]`, nothing below the API layer imports FastAPI or Streamlit, no URLs, queries or references in the logs, `get_readings_for_date_string` gone from `backend/`, `app.py` and the other Streamlit files untouched); no migration (head `0004_invites_reusable`); changed paths (102) and commits (<count>) as planned. May I push `claude/slice-2-plan` to GitHub and open it as a **draft** PR titled "Slice 2a readings backend: lectionary, passages, translations, rate limits", so CI runs? I will come back with the CI results and ask again before marking it ready for review. Merging stays with you (Task 15).

If Steps 1–8 needed any note (a merge from `main`, an expected extra path, a skipped font download, a `Fix:` commit), add it to the message as one line each. Do only what the owner approves: a no leaves everything local.

- [ ] **Step 10 (agent, on the owner's yes): Write the PR body, push, open the draft PR**

Write the body (quoted heredoc, so the backticks stay literal); the command after it replaces `@FIXTURES_LINE@` with what the fixture sidecars say:

```bash
cat > "<scratch>/slice2a-pr-body.md" <<'EOF'
PR 2a of slice 2: the backend for the Date & readings step. It adds the outbound HTTP client, a TTL cache, the rate limiter and upstream budgets, `scripture_refs`, the lectionary and passage refactors, and four API changes: `GET /lectionary/readings`, `POST /scripture/passages`, `GET /translations` and new fields on `GET /church`. The frontend changes only in the two generated API files; 2b and 2c build the UI on these routes. Spec: docs/superpowers/specs/2026-09-25-slice-2-readings-design.md (2a). Plan: docs/superpowers/plans/2026-09-28-slice-2a-backend.md. No migration: head stays `0004_invites_reusable`, so the merge deploy's pre-deploy `alembic upgrade head` is a no-op.

Platform
- `integrations/http.py`: the one outbound `httpx.Client` (User-Agent `WorshipServiceBuilder/1.0`; https only, redirect hops included; 5 s connect, a read timeout per call). The `httpx` and `httpcore` loggers run at WARNING, so upstream URLs and query strings never reach the logs.
- `cache.py`: `TTLCache` (a TTL for values and one for `CacheableFailure`s, LRU, single-flight per key; any other loader exception reaches every waiter of that load, is never stored, and the next call retries).
- `token_bucket.py` and `api/ratelimit.py`: every F §1.8 bucket plus `lectionary` (lectionary 120 per 5 min; scripture 60 parts per 5 min; church_create 3 per minute; ai 40 per 10 min per user and 400 per day per church; email 10 per hour), `consume(...)` and the `rate_limit(name)` dependency. The 429 is slice 1's `rate_limited` with `Retry-After` and `details.retry_after_seconds`.
- `integrations/budget.py`: process-wide upstream budgets (bible-api 15 per 30 s; ESV 60 per minute, 1 000 per hour, 5 000 per day); `try_acquire` never waits.
- `POST /churches` gains the `church_create` burst guard; slice 1's cap of 5 creates per 24 hours still answers the 6th create.

Readings
- `scripture_refs.py`: the one book table, the OT/NT classifier (a Psalm is never the automatic NT reading), the pickers, `resolve_readings`, fetch normalization and keys; `backend/tests/fixtures/shared/scripture_refs.json` pins every behavior 2b's TypeScript port must copy.
- `vanderbilt_lectionary.py`: the Advent year boundary fixed (`liturgical_year_for`); descriptive occasion names ("Nineteenth Sunday after Pentecost"; Trinity, All Saints on a Sunday, Reign of Christ, Baptism of the Lord and Transfiguration win; a Vanderbilt "Proper N (M)" row is renamed, and the Proper number is never shown); Vanderbilt and Lectio parsing; the draft-limit guard (1-20 lines of 1-200 characters and a 1-300-character name, or the set is dropped with a warning); the merge. Deleted: the module-level dict cache, the nearest-previous-Sunday lookup and `get_readings_for_date_string`.
- `usecases/lectionary.py`: `readings_for_date` looks up exactly the date asked. Both sources run in parallel on a 4-worker pool, each through a `TTLCache` (24 hours for an answer, including a definitive 404; 5 minutes for a failure), with a 20 s source deadline. Status: `ok`, `no_readings`, `partial`, or 502 `upstream_error` / 504 `upstream_timeout` "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."
- `scripture_fetcher.py` and `usecases/passages.py`: each part, section and passage is `ok`, `not_found` or `unavailable`, with the text of every part that loaded; public-domain parts are cached 7 days and ESV never; each request has a 20 s deadline on a shared 4-worker pool; `get_passage_text` returns `None`, never the old "[Could not load text]" sentinel.
- `usecases/church_profile.py`: the profile fields, re-read on every request.

API (additive; the three new routes are user-scoped, ignore `X-Church-Id` and are in `USER_SCOPED`)
- `GET /lectionary/readings?date=YYYY-MM-DD` → `LectionaryOut`; 401, 422, 429, 502, 503, 504.
- `POST /scripture/passages` → `PassagesOut`; charges the `scripture` bucket one token per upstream part, after validation; 401, 422, 429, 503.
- `GET /translations` → `TranslationsOut`; ESV is listed only when `ESV_API_KEY` is set; 401, 422, 503.
- `GET /church` → `ChurchProfileOut`: `ChurchOut` plus `timezone`, `timezone_valid`, `bible_translation`, `effective_translation` and `effective_translation_label`. `/me` keeps `ChurchOut`.
- The OpenAPI snapshot and `schema.d.ts` are regenerated.

Fixtures and tests: respx joins requirements-dev.txt (owner Q1a). @FIXTURES_LINE@ backend/tests/fixtures/README.md says how each one was made. The no-network test guard stays on.

Docs: F amendment rows (the upstream budgets and the two 20 s deadlines, the `ESV_API_KEY` deviation until slice 7, AC13 adds `integrations/budget.py`, the §1.8 test wording), S corrections marked "(2a plan)", and one runbook line: the new app reads `ESV_API_KEY` on Railway, and while it is unset ESV is hidden.

Owner answers (2026-09-28): respx installed and fixtures recorded (Q1a, Q1b); a Proper row on All Saints Sunday takes the computed ordinal, "Twenty-Third Sunday after Pentecost" on 2026-11-01 (Q2); Christmas-season Sunday names when Vanderbilt is down ("Nativity of the Lord", "Epiphany of the Lord", "First Sunday after Christmas Day", "Second Sunday after Christmas Day"; Q3); no early draft PR (Q4); a short "Slice 2a record" in docs/ops-runbook.md after the merge (Q5).

Standing-permission fixes (owner decision 1: safety or reliability, no owner-visible change) that differ from S's text:
- Clarification 1: slice 1's `test_blank_then_corrected_with_new_key_201` advances the limiter clock; `test_cap_429_not_replayed`, which S named, needs no change.
- Clarification 3: `?date=` is strict `YYYY-MM-DD`, because Pydantic's `date` alone accepts "0" and datetimes.
- Clarification 4: every new route also documents 422 and 503, so `/translations` lists 401, 422 and 503.
- Clarification 8: a church deleted between the guard and the profile read gets the guard's own 403.
- Clarification 28: book names also accept "iv", "fourth" and "1st"-"4th".
- Clarification 29: "usecase" dropped from `CreateChurchIn`'s description (1b T6-m2).
- Clarification 30: the All Saints Proper rename follows S's merge table, not S :454 (owner Q2).
- Clarification 31: the lectionary waits at most 20 s for its sources; a source still running then counts as a timeout for that request and is not cached.
- Clarification 32: the `httpx` and `httpcore` loggers at WARNING.
- Clarification 33: a ref with no parts (for example ";") gets "Enter a scripture reference.", and `consume` refuses a cost below 1.
- Clarification 34: the 1-300-character set-name limit.
- Clarification 35: `rate_limit(name)` checks the bucket name when the app starts.
- Clarification 36: only `CacheableFailure` is cached.
- Clarification 38: a 422 on `/lectionary/readings` spends a `lectionary` token, since the dependency runs before query validation (as for `church_create`).

Recorded deviation kept: `scripture_fetcher` still reads `ESV_API_KEY` from the environment until slice 7 moves it into `api/settings.py` (S "Configuration exception"; F §2.3.5).

Known limits: the frozen `app.py` on `main` no longer imports (production Streamlit runs from `streamlit-frozen`); several concurrent cold lectionary lookups can answer `partial` or 504 rather than wait past 20 s; the bible-api budget is shared by every user, so a long "Show all text" can leave another user's rows `unavailable` for up to 30 s (never cached; "Try again" in 2c); with no `ESV_API_KEY` on Railway, ESV stays hidden.

Tests: backend 798 → 971 passed, 9 → 9 skipped; frontend 221 → 221 in 34 files

After merge (Task 15): the Railway deploy log shows the pre-deploy `alembic upgrade head` with no `Running upgrade` line and a passing `/health/ready`; signed-in calls from the existing app's devtools to `GET /church`, `/translations`, `/lectionary/readings` (the fixture dates, compared with the recordings) and `/scripture/passages`; the Streamlit smoke on https://liturgy-frozen.streamlit.app/; then a docs-only "Slice 2a record" PR. S's manual checks are UI checks and wait for 2c. Production Streamlit runs from `streamlit-frozen` and is not deployed by this PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
.venv/bin/python - "<scratch>/slice2a-pr-body.md" <<'EOF'
import json, pathlib, sys
body_path = pathlib.Path(sys.argv[1])
metas = sorted(pathlib.Path("backend/tests/fixtures").glob("*/*.meta.json"))
loaded = [(f"{p.parent.name}/{p.name.removesuffix('.meta.json')}", json.loads(p.read_text(encoding="utf-8")))
          for p in metas]
synthetic = [name for name, meta in loaded if meta["synthetic"]]
recorded = [meta for _, meta in loaded if not meta["synthetic"]]
days = sorted({meta["recorded_at"][:10] for meta in recorded})
if recorded:
    line = (f"{len(recorded)} of the {len(loaded)} upstream fixtures were recorded from lectio-api.org, "
            f"lectionary.library.vanderbilt.edu and bible-api.com on {', '.join(days)} (owner Q1b); "
            f"{len(synthetic)} are hand-built ({', '.join(synthetic)}).")
else:
    line = (f"All {len(loaded)} upstream fixtures are hand-built from S \"Upstream facts\" (no recording "
            "was possible), so the Easter Vigil row and the real Content-Type headers stay UNVERIFIED "
            "until the live check after merge (Task 15).")
text = body_path.read_text(encoding="utf-8")
assert text.count("@FIXTURES_LINE@") == 1, "the @FIXTURES_LINE@ marker is missing or repeated"
body_path.write_text(text.replace("@FIXTURES_LINE@", line), encoding="utf-8")
print(line)
EOF
grep -c '@FIXTURES_LINE@' "<scratch>/slice2a-pr-body.md"
grep -cx 'Tests: backend 798 → 971 passed, 9 → 9 skipped; frontend 221 → 221 in 34 files' "<scratch>/slice2a-pr-body.md"
tail -1 "<scratch>/slice2a-pr-body.md"
```

**Expected:** one fixtures line, normally `<r> of the 25 upstream fixtures were recorded from lectio-api.org, lectionary.library.vanderbilt.edu and bible-api.com on <YYYY-MM-DD> (owner Q1b); <s> are hand-built (esv/empty, esv/success, lectio/error_500, lectio/html_200).` with `<r> + <s> = 25` and at least those four hand-built (Task 1: no ESV key, and Lectio cannot be made to send an HTML 200 or a 500); any further hand-built name is a fixture Task 1 could not record, which Task 1's Step 13 report already named. Then `0` (the marker is replaced; `grep -c` exits 1, which is expected); `1`; `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

Push and open the PR:

```bash
git fetch origin
test "$(git rev-list --count HEAD..origin/main)" = 0 && git push -u origin claude/slice-2-plan || echo "not pushed"
```

**Expected:** `* [new branch]      claude/slice-2-plan -> claude/slice-2-plan` and `branch 'claude/slice-2-plan' set up to track 'origin/claude/slice-2-plan'.` On `not pushed`, run `git rev-list --count HEAD..origin/main`: if it is not `0` (`main` moved after Step 1), go back to Step 1 (merge, then Steps 2–8) and push afterwards (the owner's yes still covers it); if it is `0`, the push was rejected: stop and tell the owner. Never force-push.

```bash
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan \
  --title "Slice 2a readings backend: lectionary, passages, translations, rate limits" \
  --body-file "<scratch>/slice2a-pr-body.md"
gh pr view claude/slice-2-plan -R bbrown62450/church --json number,title,isDraft,headRefOid,url --jq '"#\(.number) \(.title) | draft=\(.isDraft) | \(.headRefOid) | \(.url)"'
git rev-parse HEAD
```

**Expected:** `https://github.com/bbrown62450/church/pull/<N>`; then `#<N> Slice 2a readings backend: lectionary, passages, translations, rate limits | draft=true | <sha> | https://github.com/bbrown62450/church/pull/<N>`, and `git rev-parse HEAD` prints the same `<sha>`. Use this `<N>` from here on.

- [ ] **Step 11: Watch the checks (agent)**

Run with the Bash tool's `run_in_background: true` (the watch can outlast the 10-minute foreground limit; the tool re-invokes the agent when it exits):

```bash
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

**Expected** when it exits: exit code 0 and every check `pass`: `backend`, `backend-postgres`, `frontend`, and the Vercel preview deployment. If it exits at once with `no checks reported` (the run has not registered yet), run it again. Any `fail` goes to Step 14.

- [ ] **Step 12: Read the CI logs and compare (agent)**

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres" or .name == "frontend") | .name as $j | .steps[] | "\($j) / \(.name): \(.conclusion)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Successfully installed .*respx|[0-9]+ passed"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Running (upgrade|downgrade)|No new upgrade operations detected|pg_smoke: OK|[0-9]+ (passed|failed|errors?)( |,)"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "frontend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Test Files +[0-9]+ passed|Tests +[0-9]+ passed|Compiled successfully"
```

(Shell variables do not carry between commands, so each line sets `$RUN` and `$JOB` itself. If the first line prints `run ` with no id, the run is not listed yet: run it again.)

**Expected:**
- `run <id>` (keep the id for the Step 13 message);
- jobs: `backend: success`, `backend-postgres: success`, `frontend: success`;
- steps: every step `success`, including `backend-postgres / Migrate the empty database to head`, `… / The models match the migrated schema`, `… / Every revision downgrades`, `… / Migrate to head again`, `… / Identity smoke (ops-2)`, `… / Postgres-only tests`, and `frontend / API types match the OpenAPI snapshot (F §5.4)`;
- backend: a `Successfully installed …` line naming `respx-0.2x` (among the other packages), then `971 passed, 9 skipped in …s`;
- backend-postgres, in this order: the four `Running upgrade` lines (`  -> 0001_baseline` … `0003_lockdown -> 0004_invites_reusable`; 2a adds no revision), `No new upgrade operations detected.`, the four `Running downgrade` lines (`0004_invites_reusable -> 0003_lockdown` … `0001_baseline -> `), the four upgrades again, `pg_smoke: OK`, then `9 passed, 971 deselected, 1 warning in …s` (the warning is 1b's hymn-seed timing line; 2a's new tests are all deselected there);
- frontend: `Test Files  34 passed (34)`, `Tests  221 passed (221)`, `✓ Compiled successfully`.

If a required job failed and the date is 2026-10-19 or later, first read the runner image (GitHub moves `ubuntu-latest` to Ubuntu 26 that day; 1a minor T14-m2):

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .databaseId' | head -1); gh run view -R bbrown62450/church --job "$JOB" --log | grep -m2 -E "Image: |Version: "
```

**Expected:** `Image: ubuntu-24.04` (and its version); if it shows `ubuntu-26.04` and the failure is in setup (Python or Node install, the Postgres service), report it to the owner before changing any 2a file. Otherwise go to Step 14.

- [ ] **Step 13 (agent → OWNER): Report CI and ask for the go-ahead to mark the PR ready**

Only when Steps 11 and 12 matched. Send the owner exactly this message, with `<N>`, `<url>` and `<run id>` replaced, and wait for a clear yes:

> PR #<N> (<url>) is green on CI (run <run id>): backend 971 passed, 9 skipped; backend-postgres Alembic cycle clean, pg_smoke OK, 9 passed, 971 deselected; frontend 221 passed in 34 files, API types match the snapshot, build OK; Vercel preview OK. May I mark it ready for review? Merging stays with you (Task 15).

On the owner's yes:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft,state,url --jq '"draft=\(.isDraft) \(.state) \(.url)"'
```

**Expected:** `✓ Pull request bbrown62450/church#<N> is marked as "ready for review"`, then `draft=false OPEN https://github.com/bbrown62450/church/pull/<N>`. (CI does not rerun: `ci.yml`'s `pull_request` trigger uses the default activity types, which do not include `ready_for_review`.)

Report to the owner in one line: "PR #<N> (<url>) is ready for review. Next: Task 15, the merge on your yes (no database change), then the Railway deploy check, the Streamlit smoke and the Slice 2a record." If the owner says no, the PR stays a draft; ask again when they want it.

- [ ] **Step 14: Fix any failure in its owning task (agent)**

If Steps 2–8 or 11–12 did not match, read the failure (for CI: `gh run view <run-id> -R bbrown62450/church --log-failed | tail -80`) and fix it in the task that owns it:

| Failing check or test | Owning task (files) |
|---|---|
| `test_fixtures_recorder.py`, a fixture body or sidecar, `upstream_fixtures.py`'s `load` / `FIXTURE_DATES` / `Recorded`, the `respx` line or install, the fixture secrets grep, the Step 10 fixtures line | Task 1 |
| `test_http_client.py`, `test_cache.py`, `_fresh_http_client`, the `httpx.Client(` count | Task 2 |
| `test_ratelimit.py`, `test_budget.py`, `_fresh_rate_limits`, `limiter_clock`, `budget_clock`, the `BUCKETS` / `BUDGETS` line | Task 3 |
| `test_api_churches.py` (the burst tests, `test_blank_then_corrected_with_new_key_201`), `rate_limit("church_create")`, the `POST /churches` line in Step 5 | Task 4 (regenerate with `.venv/bin/python backend/scripts/export_openapi.py`, then `(cd frontend && npm run gen:api)`, and commit both) |
| `test_scripture_refs.py`, `backend/tests/fixtures/shared/scripture_refs.json` | Task 5 |
| `test_lectionary_domain.py`: the calendar and name tests | Task 6a |
| `test_lectionary_domain.py`: the parsing, draft-limit and merge tests; the `reading_set_dropped` log row | Task 6b |
| `test_usecase_lectionary.py`, `_fresh_lectionary_caches`, the vanderbilt, dict-cache and old-lookup greps, the `lectionary_lookup` log row | Task 7 |
| `test_api_lectionary.py`, the `/lectionary/readings` rows in `test_route_guards.py` and `test_api_app.py`, the `/lectionary/readings`, `date param`, `LectionaryOut` and `ReadingSetOut` lines in Step 5, `rate_limit("lectionary")` | Task 8 (same regeneration) |
| `test_scripture_fetcher.py`, `_fresh_passage_cache`, the passages grep on `scripture_fetcher.py`, the Streamlit Settings helper line, `test_scripture_translations.py` still present, `streamlit_tests/test_settings_prompts_translation.py`, the `passage_part_*` log rows | Task 9 |
| `test_usecase_passages.py`, `test_api_scripture.py`, `_fresh_passages_pool`, the `/scripture/passages` rows and `Passage*` lines, `consume("scripture"`, the `passages_deadline` log row | Task 10 (same regeneration) |
| `test_api_translations.py`, `test_api_church_profile.py`, the edited `test_api_me.py`, `test_api_churches.py` and `test_api_invites.py` body checks, the `/translations` and `/church` rows and lines, `ChurchProfileOut`, `Translation*` | Task 11 (same regeneration) |
| `test_docs.py`, `test_slice1_docs.py`, the owner-marker count, the two specs, `docs/ops-runbook.md` | Task 12 |
| `test_no_streamlit_in_core.py` or the layering gates | the task that added the failing module (`git log --format='%h %s' -S'<module name>' origin/main..HEAD -- backend/tests/test_no_streamlit_in_core.py` names it) |
| a failing threaded run in Step 2 (even one in three) | the task that owns the test file (Task 2, 7 or 10); make the test deterministic (clarification 39: a `threading.Event` set in `finally`, no sleeps as synchronization) rather than retrying it |
| a 1a or 1b test outside this list (`test_migrations.py`, `test_identity.py`, `test_ops_workflows.py`, the nine Postgres tests, any other `streamlit_tests/` file, any frontend test) | 2a should not affect them: report to the owner before changing anything |
| the Vercel preview only | report the preview's build log to the owner before changing anything |

For each fix:
1. Reproduce it locally first where SQLite, pytest or the build can show it.
2. Change only the owning task's files.
3. Rerun Steps 2–8 (`971 passed, 9 skipped`, or the Task's documented count plus any Step 1 merge's tests; `221 passed` in 34 files; clean types, lint, build, generated files, shape, gates, paths and commits).
4. Commit with the subject `Fix: <what> (Task <n>, slice 2a final verification)` and the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`, staging files by name.
5. Have that task re-reviewed (its plan section against the fix's diff).
6. Before Step 10 (no push yet): continue with Step 9 and name the fix in its message. After the push: `git push origin claude/slice-2-plan` (covered by the owner's first yes; never `--force`), then repeat Steps 11–12 and send Step 13's message with the new run.

An infrastructure failure with no test output (a service container that never became healthy, a timed-out `npm ci` or `pip install`) gets one `gh run rerun <run-id> -R bbrown62450/church --failed` before it counts as a failure.

Expected counts after this task: backend `971 passed, 9 skipped` locally (CI `backend`: the same; CI `backend-postgres`: `9 passed, 971 deselected, 1 warning`); frontend `221 passed` in 34 files. No commit unless Step 14 needed a fix.
### Task 15: Merge and after (OWNER + agent): merge, the no-op deploy, live checks of the four API changes, ESV on Railway, the Streamlit smoke check, the slice 2a record (S API, Status rules, Upstream budgets; AC1, AC5, AC6, AC9, AC18 Streamlit half; owner decisions 2, 3 and 4; owner answer Q5)

2a changes no schema. `backend/migrations/versions/` still ends at `0004_invites_reusable`, and `backend/requirements.txt`, `backend/Procfile` and `backend/railway.toml` are untouched, so the merge deploy builds the same image dependencies and its pre-deploy `alembic upgrade head` (set in the Railway UI, owner decision 3) finds the database at head and runs nothing. That means no backup gate, no stamping, no laptop `alembic` step, and no Railway, Supabase or branch-protection change. Merges never reach https://liturgy-frozen.streamlit.app/ (owner decision 2).

No page in the new app calls the three new routes until 2b and 2c, so the live checks are API calls: signed out with `curl` (agent), and signed in from the production site's DevTools with the owner's own account (OWNER). `GET /church` is already called by every church page, so its new fields are read in the Network tab. The other three routes are called by one Console snippet that reads the Supabase session from this site's own cookies, exactly as the app does, sends it only to the app's own API, and never prints it. The snippet uses three dates that have recorded fixtures (2026-10-04, 2026-11-01, 2026-03-29), so Step 8 can compare the live answers with the merged code's answers over the recorded fixtures: this is the first check that the recorded Lectio and Vanderbilt data (owner answer Q1b) and the accepted Content-Types still match production (outline risks "Fixture fidelity" and "Vanderbilt Content-Type mismatch"). The task ends with the short "Slice 2a record" in a docs-only records PR (owner answer Q5). Nothing is appended to `docs/manual-verification.md`: its last two `##` headings are pinned by `test_slice1_docs.py::test_manual_verification_has_the_slice_1_section`, and 2c adds the Slice 2 checklist.

Below, `<N>` is PR 2a's number (Task 14 opened it and marked it ready), `<merge sha>` is the merge commit Step 2 prints, and `<scratch>` is the absolute path of the session's scratchpad directory. Write all three out literally in each command. Every `gh` command names the repository with `-R bbrown62450/church`. Pushing, commenting on or merging a PR, running a workflow, and any Railway, Supabase or GitHub settings change each need the owner's explicit yes, asked separately. The agent never sees a token, a key, a database URL or any other secret, and nothing below is recorded with an email address, a church id or a token. The owner prefers small steps (one OWNER step per message): give one OWNER step, wait for the report (or "next"), then give the next. While the owner reports, the agent writes each result, with its date, into `<scratch>/slice2a-t15-results.md` (not committed). Step 11 fills the record from that file.

**Files:**
- Merge (Steps 1–2): no file changes. PR `<N>` (`claude/slice-2-plan` → `main`) merges with a merge commit.
- Create (not committed): `<scratch>/slice2a-t15-results.md` (dated results, Steps 2–10), `<scratch>/slice2a-t15-live.txt` (the owner's pasted Console lines, Step 7), `<scratch>/slice2a-live-openapi.json` (Step 4), `<scratch>/slice2a-t15-compare.py` (Step 8).
- Modify (records PR, Step 11, branch `claude/slice-2a-records` from `origin/main` after the merge): `docs/ops-runbook.md`. Insert `### Slice 2a record` right after `### Slice 1b record`'s table (its last row starts `| Follow-ups | Slice 6b: run checks 2, 3, 4 and 8`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins the `##` list.
- Revert path only (Step R): a branch `claude/revert-slice-2a` from `origin/main` holding `git revert -m 1` of the merge commit.
- Test: none new. Dated records are not pinned by tests, as with the 1a and 1b records PRs (#17, #19).

**Interfaces:**
- Consumes:
  - PR `<N>` from Task 14: ready for review, all checks green, its body containing the line `Tests: backend 798 → 971 passed, 9 → 9 skipped; frontend 221 → 221 in 34 files`.
  - Routes (Tasks 8, 10, 11): `GET /lectionary/readings?date=YYYY-MM-DD` → `LectionaryOut {date, status, partial, reading_sets: [{name, scriptures, source}], default_index}`; `POST /scripture/passages` with `PassagesIn {refs, translation}` → `PassagesOut {translation, translation_label, passages: [{reference, status, sections: [{reference, status, text}]}]}`; `GET /translations` → `TranslationsOut {default, esv_available, items: [{id, label}]}`; `GET /church` → `ChurchProfileOut {id, name, role, timezone, timezone_valid, bible_translation, effective_translation, effective_translation_label}`; `/me`'s church items stay `ChurchOut {id, name, role}`.
  - Messages (Global Constraints, verbatim): `fields.date` "Not a valid value."; `fields.translation` "Unknown or unavailable translation."; 401 body `{"error":{"code":"unauthenticated","message":"Please sign in.","request_id":…}}`.
  - Task 7's log line on logger `usecases.lectionary`: `lectionary_lookup date=<iso> lectio=<ok|none|failed> vanderbilt=<ok|none|failed> lectio_cached=<True|False> vanderbilt_cached=<True|False> sets=<n> duration_ms=<n>`; Task 9's `passage_part_skipped reason=budget`; Task 2's silencing of the `httpx` and `httpcore` INFO lines (clarification 32).
  - Task 1: `tests.upstream_fixtures.load(kind, name) -> Recorded(status, content_type, body)`; each `backend/tests/fixtures/<kind>/<name>.meta.json` holds `{"content_type", "recorded_at", "status", "synthetic", "url"}`.
  - Task 2: `integrations.http.set_http_for_tests(client: httpx.Client | None)`. Task 7: `usecases.lectionary.readings_for_date(d: date) -> LectionaryResult`. Task 8: `api.schemas.LectionaryOut`, `ReadingSetOut` and the route's mapping (`ReadingSetOut(name=s.name, scriptures=list(s.scriptures), source=s.source)`).
  - `scripture_fetcher.TRANSLATIONS` order and labels: `web` "World English Bible (WEB)", `kjv` "King James Version (KJV)", `asv` "American Standard Version (ASV)", `ylt` "Young's Literal Translation (YLT)", `dra` "Douay-Rheims 1899 (DRA)", `darby` "Darby Bible", `bbe` "Bible in Basic English (BBE)", `oeb-us` "Open English Bible, US (OEB)", `webbe` "World English Bible, British (WEBBE)", `esv` "English Standard Version (ESV)" (only when `ESV_API_KEY` is set).
  - `docs/ops-runbook.md` → `### Slice 1b record` (the insertion point) and Task 12's `ESV_API_KEY` line.
  - The Railway UI settings: Pre-deploy Command `alembic upgrade head`, Healthcheck Path `/health/ready` (owner decision 3). The frontend stores the session in the `sb-<ref>-auth-token` cookie, chunked `.0`, `.1`, … with a `base64-` prefix (`@supabase/ssr` 0.12.7, `frontend/src/lib/auth.ts` `AUTH_COOKIE`).
- Produces:
  - The 2a merge commit on `main`: the Railway API serves the three new routes and the widened `GET /church`, still at `0004_invites_reusable (head)`; Vercel serves the same pages (only the generated API types changed).
  - Records PR `claude/slice-2a-records` with `### Slice 2a record`: the deploy, CI, the public endpoints, ESV on Railway, the signed-in route checks, live versus recorded fixtures, the API log lines, the fixture provenance and the Streamlit smoke check.
  - Follow-ups only if seen: a live lectionary answer that differs from the recorded fixtures (refresh the fixtures, owner's yes for the network), a `vanderbilt=failed` in production (the Content-Type risk, clarification 19), or an `HTTP Request` log line (clarification 32).
  - Later users: 2b starts from this `main` and consumes the components listed in the outline §1.6.

- [ ] **Step 1 (agent): Pre-merge gate**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,baseRefName,headRefName,headRefOid --jq '[.state, .isDraft, .mergeable, .mergeStateStatus, .baseRefName, .headRefName, .headRefOid] | @tsv'
git rev-parse origin/claude/slice-2-plan
git log --oneline origin/claude/slice-2-plan..origin/main | wc -l
gh pr checks <N> -R bbrown62450/church
gh api repos/bbrown62450/church/branches/main/protection/required_status_checks --jq '.contexts | sort | join(",")'
gh pr view <N> -R bbrown62450/church --json body --jq .body | grep -F 'Tests: backend 798 → 971 passed, 9 → 9 skipped; frontend 221 → 221 in 34 files'
git diff --quiet origin/main origin/claude/slice-2-plan -- backend/migrations/env.py backend/migrations/versions backend/db/models.py backend/requirements.txt backend/Procfile backend/railway.toml; echo "exit $?"
git ls-tree --name-only origin/claude/slice-2-plan backend/migrations/versions/ | grep -c '\.py$'
git ls-tree -r --name-only origin/claude/slice-2-plan backend/tests/fixtures | grep -c '\.meta\.json$'
date -u '+%Y-%m-%d'
```

**Expected:**
- `OPEN	false	MERGEABLE	CLEAN	main	claude/slice-2-plan	<sha>`, and the next line prints the same `<sha>`.
- `0` (the branch already contains `main`).
- Every check `pass`: `backend`, `backend-postgres`, `frontend`, and the Vercel preview.
- `backend,backend-postgres,frontend`.
- The `Tests: backend 798 → 971 passed, …` line, printed once.
- `exit 0`: no revision, `env.py`, model, requirements, Procfile or `railway.toml` change, so the deploy installs the same packages and its pre-deploy step has nothing to run.
- `4` (`0001_baseline.py` … `0004_invites_reusable.py`).
- `25` (Task 1's fixtures, one `.meta.json` sidecar each: `record_fixtures.all_names()`).
- Today's date. If it is 2026-10-19 or later and a required job failed, check the job's runner image (`ubuntu-latest` becomes Ubuntu 26 on that date) before blaming 2a.

If `gh api …/required_status_checks` answers 404 or 403 instead of the three names, ask the owner to confirm in GitHub → Settings → Branches → the `main` rule that `backend`, `backend-postgres` and `frontend` are required.

If `main` moved (a count other than `0`), merge it into the branch and rerun both suites:

```bash
git switch claude/slice-2-plan
git merge origin/main -m "Merge origin/main into claude/slice-2-plan (Task 15)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test && npm run typecheck && npm run lint)
```

Expected: `971 passed, 9 skipped in <t>s` (if the merge brought new tests, the count differs by exactly those; stop and ask the owner if it differs in any other way); Vitest `Test Files  34 passed (34)`, `Tests  221 passed (221)`; `tsc` and `eslint` print nothing beyond their banners. On a merge conflict, stop and tell the owner. Then ask the owner's yes for `git push origin claude/slice-2-plan` (never force), wait for green checks (`gh pr checks <N> -R bbrown62450/church --watch`), and run this step again. If `mergeStateStatus` is `BLOCKED`, a required check is not green: fix it in the owning task's files. Never merge with `--admin`. If `isDraft` is `true`, Task 14's last step is missing: it runs first.

Then ask the owner, in one message: "PR #<N> (slice 2a, the readings backend) is green, includes `main`, and changes no database schema and no Python requirements, so the deploy runs no migration. No page uses the new routes yet, and liturgy-frozen is not affected. May I merge it now with a merge commit?"

- [ ] **Step 2 (agent, on the owner's yes): Merge**

```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergedAt,mergeCommit --jq '[.state, .mergedAt, .mergeCommit.oid] | @tsv'
git fetch origin
git log -1 --format='%h %s' origin/main
```

Expected: `MERGED	<UTC time>	<merge sha>`, then `<short merge sha> Merge pull request #<N> from bbrown62450/claude/slice-2-plan`. Use a merge commit (`--merge`), not squash. Write the merge time (UTC and Eastern) and the sha into `<scratch>/slice2a-t15-results.md`. Then tell the owner: "Merged at <time> (<short merge sha>). Railway and Vercel are deploying it now. Step 3 is next: watching that deploy."

- [ ] **Step 3 (OWNER): Watch the merge deploy**

1. Railway → project `talented-nourishment` → the API service (`church`) → **Deployments** → the deployment whose message starts `Merge pull request #<N>` → open it → **Deploy Logs** (if the pre-deploy lines are not there, look in **Build Logs**). Alembic writes to stderr, so Railway may colour its lines red. That alone is not an error.
2. Check the **pre-deploy** part: `INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.` and `INFO  [alembic.runtime.migration] Will assume transactional DDL.`, and **no** line containing `Running upgrade`.
3. Check the health check: it used `/health/ready` and passed, and the deployment is **Active**.
4. Check the app's startup lines: no line contains `schema revision`, `Row-level security`, `Traceback` or `ERROR`.
5. Vercel → the `church` project (production domain worship-service-builder.vercel.app) → **Deployments**: the **Production** deployment for the merge commit is **Ready**.

Tell the agent: the date; "no Running upgrade line" (or the lines you saw, with anything after `host=` replaced by `…`); "health check passed, Active" (or what you saw); "no schema/RLS/Traceback/ERROR lines" (or the lines); Vercel Ready or not. If you would rather skip the log reading, say "skip": Step 4 checks the deployment status from GitHub instead, and the record says the log lines were not read.

If something went wrong (in each case the previous release keeps serving):
- A `Running upgrade` line: unexpected, since Step 1 showed no revision change. Stop and send the agent the lines.
- The health check failed: send the agent the startup lines (never a URL with a secret). The fix is a PR, or Step R if it cannot wait.
- Vercel's production build failed: send the agent the build log's error lines. Production keeps the previous frontend, and the fix is a PR.

- [ ] **Step 4 (agent): CI on `main`, the deployment statuses and the public endpoints**

```bash
gh run list --workflow ci --branch main --limit 3 -R bbrown62450/church --json databaseId,headSha,status,conclusion --jq '.[] | select(.headSha == "<merge sha>") | [.databaseId, .status, .conclusion] | @tsv'
```

The push run can take a few seconds to appear. If nothing prints, run the line again (no `sleep`). Then, with its `databaseId`:

```bash
gh run watch <run-id> --exit-status -R bbrown62450/church
gh run view <run-id> -R bbrown62450/church --log | grep -E '[0-9]+ passed' | sed -E 's/^.*Z //'
gh api "repos/bbrown62450/church/deployments?sha=<merge sha>" --jq '.[] | [.id, .environment] | @tsv'
```

For each deployment id printed:

```bash
gh api "repos/bbrown62450/church/deployments/<deployment id>/statuses" --jq '.[0] | [.state, .created_at] | @tsv'
```

Then the public, token-free requests:

```bash
API=https://church-production-74ca.up.railway.app
curl -s "$API/health"; echo
curl -s "$API/health/ready"; echo
curl -s -w ' %{http_code}\n' "$API/lectionary/readings?date=2026-10-04"
curl -s -w ' %{http_code}\n' "$API/translations"
curl -s -w ' %{http_code}\n' -X POST "$API/scripture/passages" -H 'Content-Type: application/json' -d '{"refs":["John 3:16"],"translation":"web"}'
curl -s "$API/openapi.json" | .venv/bin/python -c 'import json, sys; sys.stdout.write(json.dumps(json.load(sys.stdin), sort_keys=True, indent=2) + "\n")' > <scratch>/slice2a-live-openapi.json
git show <merge sha>:frontend/src/lib/api/openapi.json | diff -q - <scratch>/slice2a-live-openapi.json && echo same
.venv/bin/python -c 'import json, sys; p = json.load(open(sys.argv[1])); print(sorted(k for k in p["paths"] if k in ("/lectionary/readings", "/scripture/passages", "/translations"))); print(p["paths"]["/church"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"])' <scratch>/slice2a-live-openapi.json
```

**Expected:**
- The run completes successfully (`backend`, `backend-postgres`, `frontend`).
- Among the `passed` lines: `971 passed, 9 skipped in <t>s` (`backend`), `9 passed, 971 deselected, 1 warning in <t>s` (`backend-postgres`), and Vitest's `Tests  221 passed (221)` (`frontend`).
- At least two deployments for the merge sha, one whose environment names the Railway project or service and one named `Production` (Vercel); each latest status is `success`. A `pending` or `in_progress` status means the deploy is still running: run the statuses line again.
- `{"ok":true}`.
- `{"ok":true,"db":"ok"}`. A 503 body with `"reason":"schema_behind"` would mean a release behind head, which 2a cannot cause: stop and tell the owner.
- Three times `{"error":{"code":"unauthenticated","message":"Please sign in.","request_id":"<32 hex>"}} 401`, with no `fields` or `details` keys: every new route is user-guarded, and the guard runs before the query or body is validated.
- `same`: the live API serves exactly the merged schema. If `diff` reports a difference instead, the old release may still be serving: wait for the Railway status to be `success`, then run the last three lines again. If it still differs, stop and show the owner the output of `diff <(git show <merge sha>:frontend/src/lib/api/openapi.json) <scratch>/slice2a-live-openapi.json | head -40`.
- `['/lectionary/readings', '/scripture/passages', '/translations']`, then `#/components/schemas/ChurchProfileOut`.

These are public, read-only requests with no token. Write the results into `<scratch>/slice2a-t15-results.md`. Then give the owner Step 5.

- [ ] **Step 5 (OWNER): Is `ESV_API_KEY` set on Railway? (names only)**

1. Railway → project `talented-nourishment` → the API service (`church`) → **Variables**.
2. Look down the list of names for `ESV_API_KEY`. Do not reveal its value (leave the eye icon alone).
3. Check that the top of the page shows no banner about staged changes waiting to be deployed.

Tell the agent: "ESV_API_KEY listed" or "ESV_API_KEY not listed", and whether a staged-changes banner showed.

Optional, only if you want ESV in the new app now (it can wait; while the key is unset, the new app simply hides ESV): **+ New Variable** → name `ESV_API_KEY`, value your Crossway ESV API key → **Add** → **Deploy** (Railway stages variable edits until you deploy) → wait until the new deployment is **Active**. Tell the agent "ESV key added and deployed" (never the key itself). The agent then reruns Step 4's `curl "$API/health/ready"` line before you continue.

- [ ] **Step 6 (OWNER): `GET /church` shows the new fields; `/me` is unchanged (AC6)**

In your normal Chrome window, signed in with your own account, at desktop width:

1. Open https://worship-service-builder.vercel.app → home shows your church.
2. Open DevTools (⌥⌘I) → the **Network** tab → click **Fetch/XHR** in the row of type buttons. In its filter box type `church`. Reload the page (⌘R).
3. Two rows may be named `church`: click the one whose **Type** is `fetch` (the other is its `preflight`). Its **Headers** show Request Method `GET` and Status Code `200`.
4. Open its **Preview** tab. Besides `id`, `name` and `role` it now has five more fields: `timezone`, `timezone_valid`, `bible_translation`, `effective_translation` and `effective_translation_label`.
5. Change the filter to `me` → click the `me` row whose Type is `fetch` → **Preview** → expand `churches` → expand the first item: it has only `id`, `name` and `role`.

Tell the agent: the date; the values of the five new fields (not the `id`); and "me items: only id, name, role" (or what you saw). Keep this tab and DevTools open for Step 7.

The agent checks the report: `timezone_valid` is `true` for a real time-zone name such as `America/Indianapolis` (exact spelling and case); `effective_translation` equals `bible_translation` when that is one of the ids Step 7 lists, and is `"web"` when `bible_translation` is `null` or is `"esv"` without the key; `effective_translation_label` is that id's label from the Interfaces list. Anything else: stop and look at `usecases/church_profile.py` with the owner's values before Step 7.

- [ ] **Step 7 (OWNER): The three new routes, signed in, from the Console (AC1, AC5, AC6, AC9)**

This snippet reads your sign-in from this site's own cookies, exactly as the app does, and sends it only to the app's API (https://church-production-74ca.up.railway.app). It prints no token and changes nothing: it asks for the lectionary on three dates and one bad date, the translation list, and John 3:16 in WEB and in ESV. The first lectionary call can take up to about 15 seconds.

1. In the same tab (the new app's home, signed in), in DevTools open the **Console** tab.
2. Click in the Console and paste the snippet below, then press Return. If Chrome warns about pasting, type `allow pasting`, press Return, and paste again.

```js
(async () => {
  const API = "https://church-production-74ca.up.railway.app";
  const jar = {};
  for (const pair of document.cookie.split("; ")) {
    const i = pair.indexOf("=");
    if (i > 0) jar[pair.slice(0, i)] = decodeURIComponent(pair.slice(i + 1));
  }
  const names = Object.keys(jar).filter((k) => /^sb-.+-auth-token(\.\d+)?$/.test(k));
  const whole = names.find((k) => !/\.\d+$/.test(k));
  let raw = whole
    ? jar[whole]
    : names.sort((a, b) => Number(a.split(".").pop()) - Number(b.split(".").pop())).map((k) => jar[k]).join("");
  if (!raw) {
    console.log("No sign-in found. Sign in on this site, reload the page, then run this again.");
    return;
  }
  if (raw.startsWith("base64-")) {
    const bytes = Uint8Array.from(atob(raw.slice(7).replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
    raw = new TextDecoder().decode(bytes);
  }
  const token = JSON.parse(raw).access_token;
  const call = async (method, path, body) => {
    const headers = { Authorization: "Bearer " + token };
    if (body) headers["Content-Type"] = "application/json";
    const started = performance.now();
    const r = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    return [r.status, await r.json(), Math.round(performance.now() - started)];
  };
  const say = (line) => console.log(line);
  const fields = (b) => JSON.stringify((b.error || {}).fields || (b.error || {}).code || null);
  let [s, b, ms] = await call("GET", "/translations");
  say(`translations ${s} default=${b.default} esv_available=${b.esv_available} items=${(b.items || []).map((t) => t.id).join(",")}`);
  for (const d of ["2026-10-04", "2026-11-01", "2026-03-29"]) {
    [s, b, ms] = await call("GET", "/lectionary/readings?date=" + d);
    say(`lectionary ${d} ${s} ${ms}ms ${JSON.stringify(b)}`);
  }
  [s, b, ms] = await call("GET", "/lectionary/readings?date=2026-3-29");
  say(`lectionary bad-date ${s} ${fields(b)}`);
  for (const translation of ["web", "esv"]) {
    [s, b, ms] = await call("POST", "/scripture/passages", { refs: ["John 3:16"], translation });
    if (s !== 200) {
      say(`passages ${translation} ${s} ${fields(b)}`);
      continue;
    }
    const p = b.passages[0];
    const text = p.sections[0].text || "";
    const shown = translation === "web" ? JSON.stringify(text.slice(0, 26)) : `esv_mark=${text.includes("(ESV)")}`;
    say(`passages ${translation} ${s} ${ms}ms translation=${b.translation} label=${b.translation_label} ref=${p.reference} status=${p.status} sections=${p.sections.length} ${shown}`);
  }
  say("done");
})();
```

3. Wait for the line `done`. Select everything from the first line starting `translations` down to `done`, copy it (⌘C) and paste it into the chat. It holds no token and no personal data.

If a line shows `401`, your sign-in had expired: reload the page (⌘R) and run the snippet again (press ↑ in the Console to bring it back). If the Console shows a red `Failed to fetch` or a CORS error, send the agent that red line.

**Expected** (the agent checks; the owner only pastes):
- `translations 200 default=web esv_available=false items=web,kjv,asv,ylt,dra,darby,bbe,oeb-us,webbe` without the key, or `translations 200 default=web esv_available=true items=web,kjv,asv,ylt,dra,darby,bbe,oeb-us,webbe,esv` with it. It must agree with Step 5 (listed ⇔ `true`). Listed but `false` means the value is blank or the change is staged and not deployed.
- `lectionary 2026-10-04 200 <ms>ms {…}` with `"status":"ok"`, `"partial":false`, one set named `Nineteenth Sunday after Pentecost` with `"source":"merged"`, its last scripture `Matthew 21:33-46`, and `"default_index":0`.
- `lectionary 2026-11-01 200 <ms>ms {…}` with `"status":"ok"`, `"partial":false`, two sets: first Vanderbilt's All Saints row (`"source":"vanderbilt"`), then `Twenty-Third Sunday after Pentecost` (`"source":"merged"`, last scripture `Matthew 23:1-12`), and `"default_index":1` (clarification 30, owner answer Q2).
- `lectionary 2026-03-29 200 <ms>ms {…}` equal to `PALM_SUNDAY` in `backend/tests/test_api_lectionary.py` (S's example, or its recorded equivalent under clarification 41).
- `lectionary bad-date 422 {"date":"Not a valid value."}`.
- `passages web 200 <ms>ms translation=web label=World English Bible (WEB) ref=John 3:16 status=ok sections=1 "For God so loved the world"`.
- Without the key: `passages esv 422 {"translation":"Unknown or unavailable translation."}`. With it: `passages esv 200 <ms>ms translation=esv label=English Standard Version (ESV) ref=John 3:16 status=ok sections=1 esv_mark=true`.
- `done`.

The agent saves the pasted text, unchanged, as `<scratch>/slice2a-t15-live.txt` and notes the first lectionary call's `<ms>` (the cold lookup) in the results file.

- [ ] **Step 8 (agent): Compare the live lectionary answers with the recorded fixtures**

Check out the merged code (the working tree is the agent's own; `.claude/` stays untracked):

```bash
git fetch origin
git switch --detach <merge sha>
```

Write `<scratch>/slice2a-t15-compare.py` (not committed):

```python
"""Slice 2a Task 15: compare the owner's live GET /lectionary/readings lines
with the merged code's answers over the recorded fixtures. Run from the repo
root: .venv/bin/python <this file> <the pasted console text>. Not committed."""
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "backend"))

import httpx  # noqa: E402

from api.schemas import LectionaryOut, ReadingSetOut  # noqa: E402
from integrations import http  # noqa: E402
from tests import upstream_fixtures  # noqa: E402
from usecases import lectionary  # noqa: E402

DATES = ("2026-10-04", "2026-11-01", "2026-03-29")
LINE = re.compile(r"lectionary (\d{4}-\d{2}-\d{2}) 200 \d+ms (\{.*\})")


def recorded(request: httpx.Request) -> httpx.Response:
    """Lectio by its `date` parameter, Vanderbilt by the year in its path."""
    if request.url.host == "lectio-api.org":
        fixture = upstream_fixtures.load("lectio", request.url.params["date"])
    else:
        fixture = upstream_fixtures.load("vanderbilt", request.url.path.split("/")[2])
    return httpx.Response(fixture.status, content=fixture.body,
                          headers={"Content-Type": fixture.content_type})


def expected(iso: str) -> dict:
    """The route's own mapping (Task 8) of the usecase's answer."""
    result = lectionary.readings_for_date(date.fromisoformat(iso))
    return LectionaryOut(
        date=result.date,
        status=result.status,
        partial=result.partial,
        reading_sets=[ReadingSetOut(name=s.name, scriptures=list(s.scriptures), source=s.source)
                      for s in result.reading_sets],
        default_index=result.default_index,
    ).model_dump(mode="json")


http.set_http_for_tests(httpx.Client(transport=httpx.MockTransport(recorded)))
live = {}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    match = LINE.search(line)
    if match:
        live[match.group(1)] = json.loads(match.group(2))
for iso in DATES:
    want = expected(iso)
    if iso not in live:
        print(f"{iso}: no live 200 line")
    elif live[iso] == want:
        print(f"{iso}: same as the recorded fixtures")
    else:
        print(f"{iso}: DIFFERENT")
        print("  live:     " + json.dumps(live[iso], sort_keys=True))
        print("  fixtures: " + json.dumps(want, sort_keys=True))
```

Then:

```bash
.venv/bin/python <scratch>/slice2a-t15-compare.py <scratch>/slice2a-t15-live.txt
.venv/bin/python - <<'EOF'
import json
from pathlib import Path

root = Path("backend/tests/fixtures")
metas = {str(p.relative_to(root))[: -len(".meta.json")]: json.loads(p.read_text(encoding="utf-8"))
         for p in sorted(root.glob("*/*.meta.json"))}
synthetic = [name for name, meta in metas.items() if meta["synthetic"]]
days = sorted({meta["recorded_at"][:10] for meta in metas.values() if not meta["synthetic"]})
print(f"{len(metas)} fixtures; {len(metas) - len(synthetic)} recorded on {', '.join(days)}; synthetic: {', '.join(synthetic)}")
EOF
git switch claude/slice-2-plan
```

**Expected:**
- `2026-10-04: same as the recorded fixtures`, `2026-11-01: same as the recorded fixtures`, `2026-03-29: same as the recorded fixtures`.
- `25 fixtures; <m> recorded on <date>; synthetic: esv/empty, esv/success, lectio/error_500, lectio/html_200` (Task 1's four always-synthetic fixtures; any other name there is one the recorder could not get, and Task 1's README says why).
- The switch back prints `Switched to branch 'claude/slice-2-plan'`.

The agent also checks Step 7's other lines against Step 7's Expected list and Step 6's report against Step 6's rules.

If a date is `DIFFERENT`:
- Both answers `"status":"ok"` and `"partial":false` but the names or scriptures differ: an upstream changed its data after the recording. Production is right by definition. Record it as a follow-up ("refresh the fixtures with `backend/scripts/record_fixtures.py`", which needs the owner's yes for the network) and continue.
- The live answer is `"partial":true`, or a line shows `502`/`504` instead of `200`: a source failed in production. Step 9's `lectionary_lookup` lines name it. `vanderbilt=failed` with `lectio=ok` on every date is most likely the Content-Type risk (clarification 19: the served type is not `text/plain` or `text/csv`). Stop and tell the owner; the fix is a small PR to the accepted types, with a test over a sidecar holding the served type.

Write the results into `<scratch>/slice2a-t15-results.md`, then give the owner Step 9.

- [ ] **Step 9 (OWNER): The API's log lines for those calls**

1. Railway → the API service (`church`) → **Deployments** → the **Active** deployment → **Deploy Logs**.
2. In the search box type `lectionary_lookup`. There is one line per date from Step 7 (three lines; six if you ran the snippet twice). Each looks like `lectionary_lookup date=2026-10-04 lectio=ok vanderbilt=ok lectio_cached=False vanderbilt_cached=False sets=1 duration_ms=…`.
3. Replace the search with `HTTP Request`: no line after the merge time matches.
4. Replace the search with `passage_part_skipped`: no line matches.
5. Replace the search with `Traceback`, then with `ERROR`: no line after the merge time matches.

Tell the agent: the date; the three `lectionary_lookup` lines exactly as shown (they hold only dates, outcomes and times); and "no HTTP Request, no passage_part_skipped, no Traceback, no ERROR" (or the lines you saw, with any `host=` value replaced by `…`).

**Expected** (the agent checks): every line `lectio=ok vanderbilt=ok`; `sets=1` for 2026-10-04 and `sets=2` for 2026-11-01 and 2026-03-29; on the first run, `vanderbilt_cached=False` on the first line and `True` on the other two (all three dates are in the liturgical year 2025-26, whose file is fetched once), and `lectio_cached=False` on all three. An `HTTP Request` line would mean clarification 32's logger silencing is not in effect: record it as a follow-up (the lines carry upstream URLs, and ESV's `q=`).

- [ ] **Step 10 (OWNER): Streamlit smoke check on liturgy-frozen (AC18, Streamlit half)**

1. In your normal window open https://liturgy-frozen.streamlit.app/ → reload; you are signed in (or sign in); **your own church** and its hymnal load.
2. Open a saved service → it loads, with its readings as saved.
3. **Settings** opens.
4. Streamlit Cloud → `liturgy-frozen` → **Manage app** → logs: after the merge time from Step 2 there is no `Pulling code changes from Github` or `Updated app!` line and no restart. **⋮** → **Settings** still shows branch `streamlit-frozen`.

Tell the agent: the date and, for each of 1–4, OK or what differed. If you would rather skip this check, say "skip": the record says "Not run: skipped by the owner". If any Streamlit page fails, send the error text. The frozen app does not run 2a's code, and 2a changes no table, so a failure there is not caused by this merge: stop, and the agent investigates before anything else.

- [ ] **Step 11 (agent): Records PR: the slice 2a record**

```bash
git fetch origin
git switch -c claude/slice-2a-records origin/main
git show origin/main:docs/ops-runbook.md | grep '\[owner' | grep -vc 'An entry marked'
grep -n '^| Follow-ups | Slice 6b: run checks 2, 3, 4 and 8' docs/ops-runbook.md
```

Expected: `4` (the owner markers before this edit; Task 12 added none); one line number. In `docs/ops-runbook.md`, use Edit to replace the last row of `### Slice 1b record` plus the blank line and `## Backups` after it:

```markdown
| Follow-ups | Slice 6b: run checks 2, 3, 4 and 8, the desktop pass of 2–3 and the S Risk 8 chooser observation once the new app has its invite UI. Seed timing: none (under 5 s) | 2026-09-28 |

## Backups
```

with that same row, one blank line, the block below, one blank line and `## Backups`:

```markdown
### Slice 2a record

Slice 2a (the readings backend: `GET /lectionary/readings`,
`POST /scripture/passages`, `GET /translations` and the new `GET /church`
profile fields) merged as PR #<N> with no database change and no Python
requirement change, so production stays at `0004_invites_reusable` (head).
No page calls the new routes until slices 2b and 2c, so the checks were API
calls: signed out with curl, and signed in with the owner's account from the
production site's DevTools (the Network tab for `GET /church`, a Console
snippet for the three new routes). No token, key, email address, church id
or database URL is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. <Pre-deploy `alembic upgrade head`: `Context impl PostgresqlImpl.`, `Will assume transactional DDL.`, no `Running upgrade` line; no `schema revision`, `Row-level security`, `Traceback` or `ERROR` line. / The pre-deploy and startup log lines were not read (owner).> The `/health/ready` health check passed and the deployment is Active; GitHub deployment statuses for the merge commit: Railway success, Vercel Production success | <date> |
| CI and public endpoints | CI on the merge commit green (run <run id>): `backend` 971 passed, 9 skipped; `backend-postgres` 9 passed, 971 deselected; `frontend` 221 passed in 34 files. `/health/ready` → `{"ok":true,"db":"ok"}`; signed out, `GET /lectionary/readings`, `GET /translations` and `POST /scripture/passages` → 401 `unauthenticated`; the live `/openapi.json` equals the committed `frontend/src/lib/api/openapi.json`, with `GET /church` returning `ChurchProfileOut` | <date> |
| ESV on Railway | <`ESV_API_KEY` is set on the API service (<already set / added and deployed by the owner on this date>): `GET /translations` lists `esv` last with `esv_available: true`, and John 3:16 in ESV came back `ok` with "(ESV)". / `ESV_API_KEY` is not set on the API service, so the new app hides ESV: `GET /translations` has no `esv` and `esv_available: false`, and an ESV passage request answers 422 "Unknown or unavailable translation.".> | <date> |
| `GET /church` (signed in, AC6) | The owner's church: `timezone` <zone>, `timezone_valid` <true or false>, `bible_translation` <value or null>, `effective_translation` <value>, `effective_translation_label` "<label>". `/me`'s church items still have only `id`, `name` and `role` | <date> |
| `GET /translations` (signed in) | `default` "web", `esv_available` <true or false>, items <the ids in order> | <date> |
| `GET /lectionary/readings` (signed in, AC1) | 2026-10-04: "Nineteenth Sunday after Pentecost" (merged), `default_index` 0. 2026-11-01: <Vanderbilt's All Saints name> (vanderbilt) and "Twenty-Third Sunday after Pentecost" (merged), `default_index` 1. 2026-03-29: <the two names> (vanderbilt, merged), `default_index` 1. All `partial: false`. <Each equals the merged code's answer over the recorded fixtures. / Differences from the recorded fixtures: <what>.> The first (cold) lookup took <ms> ms. `?date=2026-3-29` → 422 `fields.date` "Not a valid value." | <date> |
| `POST /scripture/passages` (signed in, AC5) | John 3:16 in WEB: `ok`, one section, the text starts "For God so loved the world". <ESV: `ok` with "(ESV)". / ESV: 422 "Unknown or unavailable translation." (no key).> | <date> |
| API logs | Three `lectionary_lookup` lines, all `lectio=ok vanderbilt=ok` (sets 1, 2, 2; the 2025-26 Vanderbilt file fetched once, then cached; the cold lookup `duration_ms=<ms>`); no `HTTP Request` line (clarification 32), no `passage_part_skipped`, no `Traceback` or `ERROR` after the merge | <date> |
| Fixtures | <n> fixtures in `backend/tests/fixtures`: <m> recorded on <date> (owner answer Q1b); synthetic: esv/empty, esv/success, lectio/error_500, lectio/html_200<, plus …> | <date> |
| Streamlit smoke on https://liturgy-frozen.streamlit.app/ (AC18) | <Sign-in, the owner's church and hymnal, a saved service and Settings OK; no code pull in its logs after the merge, branch still `streamlit-frozen`. / Not run: skipped by the owner. Merges never reach liturgy-frozen, and 2a changes no table.> | <date> |
| Follow-ups | <None. / One line per follow-up: what, and which step found it.> | <date> |
```

Replace every `<…>` with the values from `<scratch>/slice2a-t15-results.md` and Steps 1–10, keeping only the matching alternative where a cell offers two (the alternatives are separated by ` / `). A check that went differently records what happened instead of the expected text. Then:

```bash
sed -n '/^### Slice 2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 2a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|password|pooler\.supabase\.com|[0-9a-f]{8}-[0-9a-f]{4}-'
grep '\[owner' docs/ops-runbook.md | grep -vc 'An entry marked'
git diff --stat origin/main
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:**
- `0` (no `<…>` left; the record never uses `<`).
- `0` (no email, token, database URL, pooler host or church id).
- `4`, the same as before (2a adds no `[owner` marker).
- ` docs/ops-runbook.md | <n> +` and ` 1 file changed, <n> insertions(+)`.
- `89 passed in <t>s` (the same as on `55f1b11`: 2a adds no docs test). `test_runbook_has_the_seven_sections_in_order` still passes, because the new heading is `###`.
- `971 passed, 9 skipped in <t>s`.

No new test.

```bash
git add docs/ops-runbook.md
git commit -m "Runbook: slice 2a record: readings API live with no schema change, signed-in route checks, ESV status (S API, Status rules; AC1, AC5, AC6, AC18; owner answer Q5)" -m "Records the slice 2a merge (PR #<N>): the pre-deploy alembic upgrade head
ran no upgrade (production stays at 0004_invites_reusable), the health check
passed, CI and the public endpoints are green, and the live OpenAPI equals
the committed one; whether ESV_API_KEY is set on Railway; GET /church's new
profile fields and the three new routes called signed in, with the live
lectionary answers compared against the recorded fixtures; the API's
lectionary_lookup log lines; the fixture provenance; and the Streamlit smoke
check on liturgy-frozen. No token, key, email or church id is recorded.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 12 (agent, on the owner's yes): Push, open and merge the records PR**

Ask the owner: "The slice 2a record is written (docs/ops-runbook.md only). May I push `claude/slice-2a-records` and open its PR?" On the yes:

```bash
git push -u origin claude/slice-2a-records
gh pr create -R bbrown62450/church --base main --head claude/slice-2a-records \
  --title "Runbook: slice 2a deploy and live-check record" \
  --body "Records slice 2a (PR #<N>) in docs/ops-runbook.md → Slice 2a record: a merge deploy with no schema or requirements change (the pre-deploy alembic upgrade head ran no upgrade; production stays at 0004_invites_reusable), CI, the public endpoints and the live OpenAPI, whether ESV_API_KEY is set on Railway, GET /church's new profile fields, the three new routes called signed in (lectionary answers compared with the recorded fixtures), the lectionary_lookup log lines, the fixture provenance, and the Streamlit smoke check on liturgy-frozen. No token, key, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/slice-2a-records -R bbrown62450/church --watch
```

Expected: `* [new branch]      claude/slice-2a-records -> claude/slice-2a-records`; the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes:

```bash
gh pr merge claude/slice-2a-records --merge -R bbrown62450/church
gh pr view claude/slice-2a-records -R bbrown62450/church --json state,mergeCommit --jq '[.state, .mergeCommit.oid] | @tsv'
```

Expected: `MERGED	<sha>`. This merge redeploys the API and the frontend. Its pre-deploy step is again a no-op (no `Running upgrade` line) and `/health/ready` passes; the in-memory lectionary and passage caches start empty again, which is harmless. The owner may glance at that deployment. Anything else there goes back to Step 3's list. If Step 8 or Step 9 found a follow-up, offer it as its own branch and PR (not in this records PR). Then report to the owner: "Slice 2a is live and recorded: the lectionary, passages and translations routes and the church profile fields; no schema change; ESV is <set / not set> on Railway; <n> follow-ups. Slice 2b can start from `main`."

- [ ] **Step R (only if the 2a release must come out): Revert**

Use this only when the release cannot serve (Step 3's health check) or breaks sign-in or the church pages (for example `GET /church` failing), and a fix PR would take too long. No database step is needed: 2a adds no revision, so after the revert the 1b code runs on the same `0004_invites_reusable` schema, and the Railway Pre-deploy Command `alembic upgrade head` stays valid. Leave both Railway settings and any `ESV_API_KEY` as they are (1b reads the key the same way). 2a writes no rows, so there is no data to roll back. The revert brings back the old `vanderbilt_lectionary.py` and `scripture_fetcher.py` and `backend/tests/test_scripture_translations.py`, and removes the new modules, routes, fixtures and the `respx` line.

Agent, on the owner's yes for each command that leaves this machine:

```bash
git fetch origin
git switch -c claude/revert-slice-2a origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 2a (PR #<N>): back to the 1b release; no schema change to undo" -m "The 2a merge deploy <what failed>. 2a added no Alembic revision and wrote
no rows, so the 1b code runs on the same 0004_invites_reusable schema and
Railway's pre-deploy command and health check stay as they are.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test)
git push -u origin claude/revert-slice-2a
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-2a \
  --title "Revert slice 2a" \
  --body "Reverts the slice 2a merge (PR #<N>) because <what failed>. 2a changed no schema and wrote no rows, so nothing is downgraded: production stays at 0004_invites_reusable and the Railway settings are unchanged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/revert-slice-2a -R bbrown62450/church --watch
```

Replace `<merge sha>`, `<N>` and `<what failed>` first. **Expected:**
- `798 passed, 9 skipped in <t>s` (1b's suite; if anything else merged after 2a, the count differs by exactly its tests).
- Vitest `Tests  221 passed (221)` in 34 files (2a changed only the generated API types).
- The PR URL, and every check passes.

Merge on the owner's explicit yes (`gh pr merge claude/revert-slice-2a --merge -R bbrown62450/church`). The OWNER then checks that deployment: a pre-deploy step with no `Running upgrade` line, the `/health/ready` health check passed, Active; and https://worship-service-builder.vercel.app signs in and shows the church. Record the revert as a row of `### Slice 2a record` (Step 11), or in its own records PR if Step 12 already merged.

Expected counts after this task: backend `971 passed, 9 skipped` on `main` (CI `backend-postgres`: `9 passed, 971 deselected, 1 warning`); frontend `221 passed` in 34 files. The records PR adds no test.

---

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`; F = foundations. Items owned by 2b or 2c are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1 | Merge-table results for every recorded date, weekday feasts, `no_readings` for 2026-09-29, date never normalized, every set within the draft limits | T6a, T6b (`test_merge_table`, `test_every_fixture_date_fits_limits`), T7 (outcome tests), T8 (`test_palm_sunday_200_shape`, `test_date_echoed_never_normalized`), T15 Step 8 (live compare) |
| 2 | 502 `upstream_error` / 504 `upstream_timeout` with the exact message; one failed source with sets → 200 `partial: true` | T7 (`test_both_failed_upstream_error`, `test_all_timeouts_upstream_timeout`, `test_one_failed_with_sets_partial`, deadline test), T8 (`test_502_exact_message`, `test_504_exact_message`) |
| 3 | 24 h success / 5 min failure caching per source, single-flight, `SourceFailed`; no module-level dict cache, no raw `httpx.get` | T2 (`TTLCache`, `integrations.http`), T7 (caching tests, `test_old_names_and_dict_cache_gone`, Step 12 grep), T14 Step 6 gates |
| 4 | `liturgical_year_for` boundaries; `sunday_name` names; Proper rename (All Saints case per clarification 30) | T6a (dates and names, owner answer Q3), T6b (`test_proper_row_renamed_named_rows_kept`), T12 (S :454 and AC4 corrected) |
| 5 | Passage statuses per passage and section, `isaiah 50:4-9` URL, ESV never cached, 7-day public-domain cache, budgets | T5 (`normalize_for_fetch`), T9 (`test_scripture_fetcher.py`), T10 (`test_usecase_passages.py`, `test_api_scripture.py`) |
| 6 | `/translations` hides ESV without a key; `/church` profile fields; `/me` unchanged | T10 (`translation_options`), T11 (`test_api_translations.py`, `test_api_church_profile.py`, the three exact-body edits), T15 Steps 6–7 |
| 7 | 429 `rate_limited` with `Retry-After`, `details.retry_after_seconds` and CORS for the 121st lectionary call, the passages call over 60 parts, the 4th create in a minute | T3 (limiter unit tests), T4 (`church_create`), T8 (`test_121st_call_429_with_headers_and_cors`), T10 (`test_61st_one_part_call_429`, `test_21st_three_part_call_429`) |
| 8 | `scripture_refs` Python and TypeScript pass one shared fixture; `resolve_readings` rules | T5 (Python half and `shared/scripture_refs.json`); TypeScript half is 2b |
| 9 | Three routes in `USER_SCOPED`; route-guard, OpenAPI-contract and `gen:api` checks pass | T8, T10, T11 (allowlists, regenerated files), T14 Step 5 (regeneration diff) and CI |
| 10, 11, 12 | Draft store, builder shell, next-Sunday default | 2b (2a provides nothing; clarification 22) |
| 13 | `ratelimit.py`, `integrations/budget.py`, `cache.TTLCache`, `integrations/http.py` exist; no-network guard active | T2, T3, T14 Step 6 (AC13 gate) |
| 14, 15, 16, 17 | Auto-fill, set switcher, passage UI, builder routing | 2b / 2c |
| 18 | Manual checklist on production; Streamlit still loads | 2c for the checklist; T15 Step 10 (Streamlit smoke on liturgy-frozen) |

### S sections and behavior changes

| S item | Task(s) |
|---|---|
| Scope "Platform": `integrations/http.py`, `cache.py` | T2 |
| `token_bucket.py`, `api/ratelimit.py` (every F §1.8 bucket), Rate-limit buckets | T3 |
| Upstream budgets (`integrations/budget.py`) | T3 (module), T9 (used), T10 (`test_budget_shared_across_users`) |
| Hand-offs row 3: `church_create` burst guard; 1b T6-m2 docstring; 1b T3-m2 note | T4 |
| `scripture_refs.py`, shared fixture, OT/NT classification, `resolve_readings` (Python), spec decision 9 | T5 |
| Lectionary domain: Year file, Names for Lectio-only sets, Ordinary-time occasion names (decision A, owner Q3) | T6a |
| Lectionary domain: Vanderbilt parsing, Lectio parsing, Merge, draft-limit guard (clarification 34) | T6b |
| Fetchers, Loaders, `usecases/lectionary.py`, the "Deleted" list, the log line | T7 |
| API row 1 `GET /lectionary/readings`, `IsoDate`, `LectionaryOut`, `ReadingSetOut` | T8 |
| Passages: planning, part cache, statuses, ESV, `get_passage_text` | T9 |
| API row 3 `POST /scripture/passages`, `PassagesIn`/`PassagesOut`/`PassageOut`/`PassageSectionOut`, `usecases/passages.py` | T10 |
| API rows 2 and 4 `GET /translations`, `GET /church` → `ChurchProfileOut`, `usecases/church_profile.py` | T11 |
| Testing "Fixtures" (recorder, recorded and synthetic fixtures, respx) | T1 (owner Q1a, Q1b) |
| S corrections and F amendment rows; runbook `ESV_API_KEY` line | T12 |
| Behavior changes 3 (exact date), 4 (visible, 5-min failures) | T6b, T7, T8 |
| Behavior change 7 (merge rule), 8 (occasion names), 9 (year boundary), 10 (Vanderbilt cells) | T6a, T6b, T7 |
| Behavior change 11 (parallel sources) | T7 |
| Behavior change 12 (passage text) | T5, T9, T10 |
| Behavior change 13 (translation, backend half) | T11 |
| Behavior changes 14, 15 (Python halves) | T5 |
| Behavior change 17 (limits) | T6b (clarification 34), T10 (`PassagesIn`) |
| Behavior change 18 (deliberately unchanged) | T5, T6b |
| Behavior changes 1, 2, 5, 6, 16, UI halves of 13 and 15; Manual checks 1–13 | 2b / 2c |
| F §6.1 item 6 contingency shim | not written (owner decision 2; T12 marks it "not in force") |
| Whole-branch verification, PR, CI (`9 passed, 971 deselected, 1 warning`) | T14 |
| Merge, no-op deploy, live checks, ESV status, Streamlit smoke, Slice 2a record (owner Q5) | T15 |
| Early draft-PR checkpoint | dropped (owner Q4; Task 13) |
