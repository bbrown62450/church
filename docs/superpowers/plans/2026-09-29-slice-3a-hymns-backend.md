# Slice 3a: Hymns Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 3a of slice 3, the hymns backend, with no screen change. The new app gains four church-scoped routes: `GET /hymnals` (the church's hymnals with counts, its stored default and the effective one), `GET /hymns` (a page of `HymnOut`, filtered by hymnal and by number or title, with each hymn's recent use around a service date), `POST /hymns/scripture-matches` (hymns whose scripture references match the day's readings, tiered "passage" and "chapter", on a new book/chapter/verse parser) and `POST /hymns/suggestions` (AI suggestions through the new OpenAI client, rate limited by the `ai` bucket, inside a 75 s server deadline). `GET /church` gains `default_hymnal` and `effective_hymnal`. Every hymn carries its year, hymnal count and the rubric's "newer" flag (PR #4). The shared `HymnRef`, `SlotHymns` and `SectionKey` models (frozen in F §1.3) are created for slices 4 and 5a. `GZipMiddleware` joins the stack innermost. The old Streamlit-era matcher, suggester, display helper, audio resolver and Notion path in `worship_service.py` are deleted with `lxml`. There is no migration (head stays `0004_invites_reusable`), the frontend changes only through the regenerated `openapi.json` and `schema.d.ts` plus one test fixture, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** Below the API, and importing no FastAPI, Starlette or Streamlit: `integrations/openai_client.py` (settings, `ai_available()`, `complete(...)` with its own capped retry, a deadline, a process-wide semaphore and F §2.8's error mapping, `FakeAI`), `scripture_refs.py` (gains `parse_refs`, `RefSpan`, `spans_overlap`, `same_chapter`, parse-only aliases and the single-chapter books), `hymn_search.py` (pure: `normalize_title`, `usage_key`, `parse_themes`, `match_hymns`, `evenly_spaced`), `hymn_suggest.py` (pure: candidates, prompt, parsing, resolution, final slots), `hymn_ranking.py` (PR #4's ranking, generalized with accessors), `repos/hymns.py` (typed `HymnRecord` reads), `hymn_usage.usage_near` (the recent-use window), and `usecases/hymns.py` (the four usecases, each reading in one session, the suggestion usecase closing it before the NT fetch and the AI call). `api/routes/hymnals.py` and `api/routes/hymns.py` are thin plain-`def` routes. Tests use a `FakeAI`, a fake SDK client built with the SDK's own error types, a patched NT fetcher and the SQLite fixtures; the no-network guard stays on, and the three Postgres-marked tests run in CI's `backend-postgres` job.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.1.1, openai (installed 3.20.0, built on `httpx2`; the requirement becomes `openai>=1.58.0,<4`), Alembic (no new revision), pytest (SQLite locally; `postgres:17` in CI, `-m postgres`); Next 16 / openapi-typescript 7 for the regenerated types only; GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Railway, Vercel, Supabase Postgres, OpenAI.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md` (3a is the backend half: API, Models, Backend changes 1-6, Data and migrations, Testing "Backend", AC1-AC9, AC16, AC18-AC20 and the 2026-09-26 rubric amendments).
- Service rubric spec: `docs/superpowers/specs/2026-09-25-service-rubric-design.md` (PR #4; `service_rubric`, `hymn_ranking`).
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (§1.2, §1.3, §1.5, §1.8, §2.5, §2.7, §2.8, the Decisions and Amendments tables).
- Inventory ("inv"): `docs/superpowers/specs/2026-09-25-streamlit-migration-inventory.md` §1 D1-D10, §3.
- Slice 2a plan ("P2a"): `docs/superpowers/plans/2026-09-28-slice-2a-backend.md`, its structure, conventions and "Build notes"; the 2b and 2c plans' build notes and lessons.
- Production facts: `docs/ops-runbook.md`.
- Facts checked for this plan (tree `720a8b2`, slices 2a, 2b and 2c merged and live, 2026-09-29):
  - Backend baseline `971 passed, 9 skipped`; `-m postgres` on a local Postgres 16: `9 passed, 971 deselected`; frontend `356 passed` in 55 files; Alembic head `0004_invites_reusable`; 4 runbook owner markers; `openai` 3.20.0 (its `chat.completions.create` takes `max_completion_tokens`), `lxml` 6.1.3 installed.
  - `api/ratelimit.py` already defines the `ai` bucket (40 per 600 s per user and 400 per 86 400 s per church) and `rate_limit("ai")` already depends on `require_church`; `scripture_refs.py` already has the deuterocanon, `split_alternatives` and `default_nt_ref`; `usecases/passages.get_passage_text` exists; `Page[T]` exists in `api/schemas.py`.
  - Review fixes (2026-09-29, after the owner's answers A-D): the plan text was replayed again, Tasks 1-15, onto a clean worktree of `720a8b2`, with the full suite after every task matching the count table, the red runs of the changed tests observed, and the OpenAPI files regenerated and typechecked.
  - Every task's code in this plan was written and run by the planner in a throwaway worktree of `720a8b2`, one commit per task, with every stated count and every red and green run observed. The three Postgres-marked tests ran against a local Postgres 16. The plan text was then replayed onto a clean worktree of `720a8b2`: every Create, Replace, Append, Delete and Run directive below applied in order reproduces each task's tree exactly. Not run while planning: the pushes and CI (Task 16), the owner steps (Tasks 4 Step 1 and 17), and any call to OpenAI (the container cannot reach it).

## Global Constraints

"T<n>" below means Task n of this plan. "S", "F" and "inv" are the documents above.

### Commands and process
- Use `.venv/bin/python` (3.11) from the repo root. The working directory resets between commands. Run the frontend as `(cd frontend && ...)`. No foreground `sleep`, and never prove that something is absent by sleeping.
- Run one test file with `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`.
- Run the whole suite with `.venv/bin/python -m pytest -q | tail -1`.
- After any route or schema change, regenerate the OpenAPI files and commit both with the route:
  `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)`
  Then run `(cd frontend && npm run typecheck)`. Never hand-edit either file.
- Branch: `claude/slice-2-plan-4q33le` (this session's branch), from `720a8b2`. Its first two commits are this plan, at `docs/superpowers/plans/2026-09-29-slice-3a-hymns-backend.md`, and its review fixes (`Plan: slice 3a review fixes`).
- Stage files by name. `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Before merging, merge `origin/main` and rerun both suites. Run `gh pr merge <N> --merge -R bbrown62450/church` only on the owner's explicit yes.
- Commit messages end with these two lines (the session's attribution):
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- Commit subjects read "Area: plain words (F §x, S ...)". Use TDD: write the failing test first and quote its failure.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`. It includes the line "Tests: backend 971 → 1103 passed, 9 → 11 skipped; frontend 356 → 356 in 55 files".
- **The container restarts** (2a, 2b and 2c build notes): uncommitted work can be lost. Commit as soon as a task's checks pass, and after each task's review back the branch up with `git push origin claude/slice-2-plan-4q33le` (owner answer Q5: standing permission for backup pushes, as in slice 2). If `frontend/node_modules` is gone after a restart, `(cd frontend && npm ci)`.
- **The network is filtered.** OpenAI, hymnary.org, lectio-api.org, Vanderbilt, bible-api.com and Railway are not reachable from the build container; the npm registry and PyPI are. No test may need the network: the AI is `FakeAI` or a fake SDK client, and the NT fetch is patched.
- **Grep gates exclude tests** and are judged, not obeyed blindly: a hit may be a comment or a test asserting absence. Read the line, and if it is harmless say why in the task's report.
- **Owner steps one at a time, in plain words**, and every outward action (push to a new place, PR, ready, merge, Railway settings) on its own yes.
- New prose for the owner uses no em dashes; copy strings quoted from the spec keep theirs.

### Baselines and counts
- Starting baselines: backend **971 passed, 9 skipped**; frontend **356 passed in 55 files**; Alembic head **`0004_invites_reusable`** (3a adds no revision); owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any baseline differs, stop and ask.
- Planned cumulative backend counts. These are the exact numbers the tasks as written produce (each was observed while planning). If a count drifts, stop and find why.

  | After | Delta | Count |
  |---|---|---|
  | T1 | +7 | 978 passed, 9 skipped |
  | T2 | +9 | 987 passed, 9 skipped |
  | T3 | +14, +1 (3a build review of T1-T3) | 1002 passed, 9 skipped |
  | T4 | +14 | 1016 passed, 9 skipped |
  | T5 | +11, +1 (3a build review of T4-T9) | 1028 passed, 9 skipped |
  | T6 | +9 | 1037 passed, 9 skipped |
  | T7 | +8, +1 skipped (Postgres) | 1045 passed, 10 skipped |
  | T8 | +7 | 1052 passed, 10 skipped |
  | T9 | +10, +1 skipped (Postgres) | 1062 passed, 11 skipped |
  | T10 | +11 | 1073 passed, 11 skipped |
  | T11 | +9 | 1082 passed, 11 skipped |
  | T12 | +15 | 1097 passed, 11 skipped |
  | T13 | +18 | 1115 passed, 11 skipped |
  | T14 | +1 − 13 (the deleted `test_suggest_hymns.py`) | 1103 passed, 11 skipped |
  | T15 | 0 | 1103 passed, 11 skipped |

  Each delta equals the number of tests the task adds (or deletes). The two "3a build review" rows are the review fixes recorded under "Build notes (3a build)"; the numbers after them are the observed counts.
- The frontend stays at 356 in 55 files throughout (T8 edits one test fixture; no test is added).
- At the end, CI `backend-postgres` shows `11 passed, 1103 deselected, 1 warning` (the 9 existing Postgres tests plus T7's and T9's).
- Table-driven tests loop over their cases inside one test function (no parametrize), so counts stay stable when cases are added.

### Layering and logging
- These modules import no fastapi, starlette or streamlit: `integrations/openai_client.py`, `scripture_refs.py`, `hymn_search.py`, `hymn_suggest.py`, `hymn_ranking.py`, `hymn_usage.py`, `repos/*`, `usecases/*`. `test_no_streamlit_in_core.py`'s import list grows in T2, T5 and T13.
- Routes are plain `def`. They parse, guard and call one usecase with `church.id` only (F §1.2 rule 1), with no try/except for domain errors.
- Logs never contain prompts (except at DEBUG), `nt_text`, titles, keys or error text from OpenAI. The client logs one `ai_call` line per attempt outcome (model, duration, token counts, outcome); the suggestion usecase logs one `hymn_suggestions` line per call (counts, modes, `nt_source`, model, duration, outcome); `usage_near` logs its skipped-row count at DEBUG. Startup logs exactly one `AI: ...` line.

### Messages (verbatim)
- Hymnal not in the church (`fields.hymnal`): "That hymnal isn't in this church's library."
- No references after trimming (`fields.refs`): "Enter at least one scripture reference."
- Empty pool (`fields.hymnal`): "This hymnal has no hymns to suggest from."
- Everything recent (no field): "Every hymn in this hymnal was used within 12 weeks of this service. Turn off “Exclude” and try again."
- `ai_not_configured` (503) on `/hymns/suggestions`: "AI suggestions aren't set up on this app yet." (also for an exhausted quota and for a model OpenAI does not offer, owner answer A). The client's own generic copy is "AI isn't set up on this app yet." (clarification 7).
- `ai_busy` (503): "The AI service is busy. Try again in a minute."
- `ai_timeout` (504): "The AI took too long to answer. Try again."
- `ai_upstream_error` (502): "The AI service had a problem. Try again." or "The AI gave an answer we couldn't use. Try again."
- Pydantic 422: "The request was not valid." with `fields` ("Not a valid value.", "Required.", "Too long (max N characters).").
- Limiter 429: "Too many requests. Try again in {n} seconds." (F §1.8; unchanged).

### Codes and documented statuses
- 3a adds no error code: `invalid_request`, `rate_limited`, `ai_not_configured`, `ai_busy`, `ai_timeout`, `ai_upstream_error` and `prompt_invalid` already exist in `domain_errors.ERROR_CODES`.
- `error_responses` per route (the `test_routes_document_the_error_body` map in `test_api_app.py` gains each):

  | Route | Statuses |
  |---|---|
  | `GET /hymnals` | 401, 403, 422, 503 |
  | `GET /hymns` | 401, 403, 422, 503 |
  | `POST /hymns/scripture-matches` | 401, 403, 422, 503 |
  | `POST /hymns/suggestions` | 401, 403, 422, 429, 502, 503, 504 |
  | `GET /church` | unchanged: 401, 403, 422, 503 |

### Buckets, budgets and limits
- `ai` (already defined by 2a): 40 per 600 s per user and 400 per 86 400 s per church, charged once per `POST /hymns/suggestions` by `Depends(rate_limit("ai"))`, which resolves `require_church` (a 403 is never charged). One token comes back every 15 s per user.
- **Rejected requests still spend an `ai` token** (F §1.8's dependency convention): FastAPI resolves the `rate_limit("ai")` dependency before it validates the body and before the usecase runs, so a Pydantic 422 (for example an extra field) and the usecase's own 422s (an unknown hymnal, an empty pool, everything recent) each cost one token, as does a 503 or 502 from the AI. Only a 401 or 403 (the guard fails first) and a 429 itself cost nothing. `test_a_rejected_request_still_spends_a_token` (T13) pins it. This is accepted: a well-behaved client sends few invalid requests, and charging them keeps a bad client from probing for free.
- Suggestion budgets: `SUGGEST_BUDGET_S = 75` from the usecase's entry; `NT_FETCH_BUDGET_S = 10` on a 4-worker `nt-fetch` pool; OpenAI: `OPENAI_TIMEOUT_SECONDS` 30 per attempt, `OPENAI_MAX_RETRIES` 1, backoff `min(Retry-After or 1 s, 2 s)`, a retry only with at least 5 s left, 15 s (or remaining − 5 s) to get one of `OPENAI_MAX_CONCURRENCY` 4 slots; `max_completion_tokens` 1 200; prompt at most 24 000 characters.
- Candidates: `SLOT_CAP` 50 per slot, `NEWER_RESERVE` 10 (owner, 2026-09-26), pad a list below 15 focused hymns to 40; 30 matches per reference for the response slot; `MIN_PER_SLOT` 3, `MAX_PER_SLOT` 5.
- Request limits: `GET /hymns` `hymnal` ≤ 20, `q` ≤ 100, `limit` 1-2000 (default 50), `offset` ≥ 0, `recent_for_date` strict `YYYY-MM-DD`; `ScriptureMatchIn` refs ≤ 20 of ≤ 200, `hymnal` ≤ 20, `limit_per_ref` 1-100 (50), `max_results` 1-100 (20); `HymnSuggestionIn` `occasion` ≤ 300, `scriptures` ≤ 20 of ≤ 200, `selected_nt_ref` ≤ 200, `nt_text` ≤ 20 000, `hymnal` ≤ 20; `extra="forbid"` everywhere.
- Recent use: usage dates in [D − 84, D + 84] around the service date D, D itself excluded, keyed by the normalized title alone (owner answer Q2).

### Model (owner answer Q3; UNVERIFIED)
The owner has an OpenAI account with a separate key for this app. After the merge (T17) the owner sets `OPENAI_API_KEY` and `OPENAI_MODEL` on Railway and a monthly budget cap in OpenAI's dashboard; the key is never pasted into chat. S's constraints: a non-reasoning, inexpensive chat model that accepts `response_format: {"type": "json_object"}` and `max_completion_tokens` (a reasoning model can spend the 1 200-token budget on hidden reasoning and answer empty, which becomes `ai_upstream_error`).
- **Recommendation: `gpt-4.1-mini`** (a non-reasoning chat model; third-party price lists found on 2026-09-29 give $0.40 per million input tokens and $1.60 per million output tokens). One suggestion call is at most about 6 000 input tokens (24 000 characters) plus up to 1 200 output tokens, so roughly $0.005 or less. The owner's cap of $15 a month (owner answer B) covers about three thousand suggestions; the `ai` bucket (400 per church per day) is the other bound.
- **Fallback: `gpt-4o-mini`**, also non-reasoning and cheaper, if the first is not offered to the owner's project.
- **Second fallback: `gpt-5-mini` with `OPENAI_REASONING_EFFORT=minimal`** (UNVERIFIED: third-party docs found on 2026-09-29 say the GPT-5 family takes `reasoning_effort` on Chat Completions and that `gpt-5-mini` accepts `minimal`; newer GPT-5.x minis may also accept `none`). The GPT-5 "mini" and "nano" models are reasoning models by default; without a low effort they can spend the 1 200-token budget on hidden reasoning and answer empty (`ai_upstream_error`). The client sends `reasoning_effort` only when `OPENAI_REASONING_EFFORT` is set (T2, T3), like `temperature`, so the non-reasoning models above never receive it.
- **A retired model.** OpenAI retires models on its own schedule, possibly after the merge. Then every suggestion answers 503 `ai_not_configured` ("AI suggestions aren't set up on this app yet.", owner answer A) and the log has `ERROR AI: model not available (OPENAI_MODEL=<m>)`; the fix is a new `OPENAI_MODEL` on Railway (no code change).
- **UNVERIFIED.** The build container could not open openai.com or developers.openai.com (egress blocked); the recommendation rests on web search results. One result said GPT-4.1 was retired from the API in February 2026, while OpenAI's retirement notice as quoted elsewhere concerned ChatGPT only. The controller confirms with the owner before T17 Step 4: the owner opens platform.openai.com → the project for this app → Limits (model access) and checks that `gpt-4.1-mini` is listed. The first live suggestion in T17 is the real check. `backend/.env.example` carries `OPENAI_MODEL=gpt-4.1-mini` from T2; if the owner picks another model, T17 Step 4 changes that one line in the records PR.

### Scripture references data (owner answer Q4)
The repository holds no real `scripture_refs` data: `data/hymnals/PH1990_hymns.csv` has only `number,title,tune`; no migration seeds `hymn_catalog`; the test fixtures' catalog rows are synthetic ("John 1:1-3"). So S's 98 % parse test needs a production sample. T4 Step 1 asks the owner for a read-only export (hymnal, number, title and scripture_refs only) and gives the exact query. Until it arrives, T4 commits a synthetic stand-in of 100 rows in Hymnary.org's shape (link texts joined by "; ", which `fill_from_hymnary.py` stores), marked SYNTHETIC in its README, so the build is never blocked. When the export arrives, it replaces the file in its own small commit (T4 Step 10), and the 98 % test must still pass on it; if it does not, the agent stops and reports the unparsed shapes to the controller before changing the parser.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried from slice 2, owner answer Q5). Each is recorded as a numbered clarification: "(owner decision 1; deviation from S ...)".
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
   - The F §6.1 item 6 contingency is off: no wrappers for `hymns_by_scripture`, `suggest_hymns_for_service` or `hymn_display_info`, and no `AppTest` smoke.
   - `app.py`, `ui_helpers.py`, `streamlit_tenancy.py` and `streamlit_views/*` are untouched. `app.py` on `main` stops importing once T14 deletes three names it imports from `worship_service`; that is accepted, as in 2a (no test imports `app.py`).
3. **Railway** keeps its Pre-deploy Command (`alembic upgrade head`) and Healthcheck Path (`/health/ready`); 3a changes neither, and the pre-deploy is a no-op at head `0004`.
4. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
5. **Spec decision 3** (AI suggestions: a top pick plus 2-4 alternatives) and **decision 9** (tightened scripture matching; no free-text hymns).

### Owner answers (2026-09-29, binding for the plan)
- **Q1 (S open question 2, decision 3): only empty slots.** AI suggestions fill only empty slots; a chosen hymn is never overwritten; filled slots get chips. `finalize_slots` is built as S §3.6 step 9 specifies, and T15 records the answer in F's decisions table as D16.
- **Q2 (S open question 1): the title alone.** Recent use across hymnals matches on the normalized title alone: `usage_key(title)` replaces `(number, normalized title)` (T5, T7). Glory to God often titles hymns by first line; first-line matching is deferred because no first-line data is stored. Follow-up (recorded in S by T15 and in the slice 3a record): research whether Hymnary.org can supply first lines. `hymnary_facts.py` already calls Hymnary's scripture API, whose results are keyed by first line, so first lines may be reachable for hymns that have scripture references; unverified for the others, and unverified whether a per-hymn lookup exists.
- **Q3: the owner's OpenAI key and model.** Set on Railway after the merge as owner steps (T17), with a monthly budget cap in OpenAI's dashboard; never pasted into chat. Model: see "Model" above (UNVERIFIED). `backend/.env.example`'s stale `gpt-3.5-turbo` default is replaced (T2).
- **Q4: the scripture_refs sample.** See "Scripture references data" above: an owner export at T4 Step 1, with a synthetic fallback.
- **Q5: process as in slice 2.** Subagent-driven, reviews, backup pushes, one PR for 3a (and later one for 3b); ask before the PR, before ready and before the merge. The standing permission for invisible safety fixes carries over.
- The container cannot reach OpenAI or hymnary.org, so every test is network-free (a fake OpenAI client).

### Owner answers to the plan review (2026-09-29, "all recommended", binding)
- **A: a retired or unknown model reads "not set up".** `NotFoundError` or an error with `code == "model_not_found"` maps to 503 `ai_not_configured` (the route's "AI suggestions aren't set up on this app yet."; 3b's screen adds "You can still choose hymns yourself." per S's copy table), with `ERROR AI: model not available (OPENAI_MODEL=<m>)` in the log and no retry (T3; clarification 26).
- **B: a $15 monthly budget cap.** The owner sets $15 a month in OpenAI's dashboard (T17 Step 5). When the cap is reached, AI reads "not set up" until the next month; the client does not retry (`insufficient_quota`, T3). The runbook's `OPENAI_API_KEY` row says so (T15).
- **C: clarification 9 accepted.** The same "other idea" chip may appear under two slots; top picks are always distinct.
- **D: the real scripture export gates "ready".** T16 walks the owner through the read-only export (T4 Step 1) one step at a time, swaps it in (T4 Step 10) and needs the 98 % check to pass on it before asking to mark the PR ready.

## Spec clarifications

Code and F win over the outline; each is owner decision 1 unless marked **owner-visible**.

1. **(Owner answer Q2; owner-visible.)** `hymn_search.usage_key(title)` is `normalize_title(title)` alone, and `hymn_usage.usage_near` returns `dict[str, date]`. S §3.4's "(number, normalized title)", its Out-of-scope row for 5a and "Unchanged on purpose" are corrected by T15. 5a keeps writing `hymn_usage` rows with number and title; the reader ignores the number. More hymns are flagged "recently used", including two different hymns that share a title (accepted by the owner).
2. **(Owner answer Q1; owner-visible, answered.)** `finalize_slots` fills only empty slots; T15 records D16 in F's decisions table.
3. **Parse-only aliases live beside `BOOKS`.** S §1 says `BOOKS` gains a single-chapter flag and `_BOOK_ABBREVS`' missing aliases, with "one book table". Changing `BOOKS` would change the shared fixture's `books` section, which the frontend's `scripture-refs.test.ts` compares with the TypeScript port, so 3a (whose frontend change is generated files only) would have to edit the TS port. Instead `scripture_refs.PARSE_ALIASES` (30 abbreviations, each checked at import against `BOOKS` names and keys) and `SINGLE_CHAPTER_BOOKS` sit next to `BOOKS`, and `parse_refs` reads both; `classify` and `split_book` are unchanged. So `parse_refs("Is 9:6")` reads Isaiah while `classify("Is 9:6")` stays "unknown" (2a T5-2, pinned by the shared fixture). The deuterocanon aliases S lists are already in `BOOKS` (2a).
4. **Sample path and format (owner answer Q4).** `backend/tests/hymn_fixtures/scripture_refs_sample.csv` (columns `hymnal,number,title,scripture_refs`), not `backend/tests/fixtures/hymns/scripture_refs_sample.txt`: `test_fixtures_recorder.py` requires every file under `backend/tests/fixtures/*/` to have a recorder sidecar. The 98 % test counts segments with `scripture_refs.split_segments` and unparsed entries with `parse_refs`.
5. **Settings live in the client.** The `OPENAI_*` settings are read by `integrations/openai_client.ai_settings()` (an `lru_cache` over `load_settings(os.environ)`), not `api/settings.py`, so the integration imports nothing from the API layer (F §2.2; the ESV key's precedent). A number that does not parse, or is below its minimum, falls back to its default with a WARNING naming the variable.
6. **Per-attempt timeout.** Each attempt passes `timeout=openai.Timeout(t, connect=min(5, t))` to `create()` instead of `with_options(timeout=httpx.Timeout(...))`; the effect is the same. The installed SDK (openai 3.20.0) is built on `httpx2`, so `httpx.Timeout` would not be its type; `openai.Timeout` always is. The tests build real SDK exceptions with the SDK's own HTTP module, read from the SDK's annotation of `APIStatusError.response`.
7. **Client messages are generic.** `openai_client` raises `NotConfigured("AI isn't set up on this app yet.")` and S's busy, timeout and upstream copy; `usecases.hymns` re-raises `NotConfigured` with S's "AI suggestions aren't set up on this app yet.", so the route's copy is exact and slice 4 can use its own ("AI not configured. Type this section yourself.").
8. **`HymnalCode` is not used on `GET /hymns`.** F §1.3's body names `GET /hymns?hymnal=` as a `HymnalCode` use; S (and F's own amendment row "`hymnal` has no pattern") say slice 3's read filters accept any stored code. S wins: a pattern would hide a CLI-imported code such as `PH 1990`. T15 corrects F's sentence and adds an amendment row. `HymnalCode` is defined for 6a and used by no 3a field.
9. **(Owner-visible, minor; accepted, owner answer C.) The same "other idea" can appear under two slots.** S Testing says that when the AI returns the same five ids for all three slots, "opening keeps them" and the others are topped up "with no id repeated across slots". S §3.6 step 9, the precise rule, blocks only the reserved hymns (the current picks and the top picks) from other slots, so alternatives may repeat across slots, and the opening slot loses the hymns that became the other slots' top picks. The algorithm wins; the test pins its result (tops distinct, never another slot's idea). The owner accepted it on 2026-09-29 (owner answer C).
10. `hymnal: ""` in a match or suggestion request is a code the church lacks, so it is the hymnal 422 (not "use the effective hymnal"); only `null` asks for the effective one.
11. `service_date_iso`, `recent_for_date` (query and body) use slice 2's strict `IsoDate`, so `2026-10-4` is a 422 "Not a valid value.", as for `?date=`.
12. **`GET /church` reads in one session.** `get_church_profile` opens one `session_scope` for the church row and `resolve_default_hymnal`. The four exact-body `/church` tests gain the two fields; `test_api_churches.py`'s create test expects `effective_hymnal: "GG2013"`, because its catalog seed is GG2013.
13. **One frontend test fixture changes.** `frontend/src/test/fixtures/index.ts`'s `churchProfile()` gains `default_hymnal: null, effective_hymnal: "GG2013"`: the regenerated `ChurchProfileOut` type makes both required, and `tsc` fails without them. No frontend test or count changes. (Deviation from "only the generated files change on the frontend".)
14. **AC9's grep is scoped.** `NotionHymnsDB` stays in the migration-only CLIs (`notion_hymns.py`, `migrate_to_db.py`, `fill_from_hymnary.py`), which slice 7 deletes; AC9's gate is `worship_service.py` plus the new modules, and `test_the_old_hymn_code_is_gone` pins it. `load_dotenv` leaves `worship_service.py` only; `api/main.py`, the CLIs and `app.py` keep theirs.
15. **Deleted `test_suggest_hymns.py` (13 tests) and its equivalents** (AC19): default checklists and preferences → `test_the_prompt_carries_checklists_preferences_and_facts`; facts and older-familiar first → the same and `test_focused_lists_are_ranked_by_the_rubric`; a church rubric changes the prompt and a partial rubric falls back (3 tests) → `test_a_church_rubric_changes_the_prompt_and_a_partial_one_falls_back` and `test_the_rubric_is_read_fresh_and_a_bad_one_falls_back`; no fixed role hints → `test_candidate_headings_add_no_fixed_role_hints`; the church's year decides the era, familiarity off keeps the order, response ranked by the rubric → `test_focused_lists_are_ranked_by_the_rubric`; a long list keeps places for newer hymns (2 tests) → `test_a_long_ranked_list_keeps_ten_places_for_newer_hymns`; results carry the year and the flag, and no preference never flags → `test_happy_path_distinct_tops_at_most_five_with_facts` and `test_is_newer_than_preferred`.
16. **`limit_per_ref` counts after tier ordering.** `match_hymns` sorts all matches (tier, first matching ref, pool order) and then caps each ref's share, so the cap keeps a ref's passage matches before its chapter matches. S says only that it "caps matches attributed to each query ref".
17. **A date such as `2026-8-2` never reaches Python.** It sorts after the SQL range's upper bound, so SQL drops it; S's "skipped (DEBUG count)" happens for values inside the string range that do not parse, such as `2026-10-1`, which the test uses. Neither raises.
18. **`prompt_invalid` is kept but unreachable.** If trimming empties every candidate list and the prompt is still over 24 000 characters, `build_prompt` raises `InvalidInput("This prompt is too long.", code="prompt_invalid")` (F §2.8's cost guard). Within the request limits the fixed text is at most about 17 000 characters, so this never fires.
19. **The NT fetch keeps the request id.** It runs through `contextvars.copy_context().run` on the `nt-fetch` pool (2a build note); `usecases.hymns.reset_for_tests()` joins and rebuilds the pool, called by the autouse `_fresh_ai` fixture from T13.
20. The root `.env.example` (frozen Streamlit's) keeps `gpt-3.5-turbo`; only `backend/.env.example` changes. `worship_service.generate_liturgy` keeps its own `gpt-3.5-turbo` default until slice 4 replaces it.
21. The rate-limit tests spend the bucket with `ratelimit.consume(...)` directly (40 for the user; 399 for other users of the church) and then make the HTTP call, rather than 40 or 400 HTTP calls.
22. The GZip test lives in `test_api_hymns.py` (it needs hymns); `test_middleware.py` only updates the order test.
23. `repos.hymns` adds `HymnalSummary(code, hymn_count, scripture_ref_count)`, which S does not name, for `hymnal_summaries`. Blank hymnal codes are left out, as `list_church_hymnals` does. Titles sort by `lower(coalesce(title, ''))`, so NULL titles sort like "" on both databases.
24. `ScriptureMatchesOut.hymnal` is `null` only when the church has no hymns; the route then answers 200 with no items (S step 2).
25. `HymnRecord.link` holds `hymns.hymnary_link`; `audio_url` is never read (inv D8's dead audio).
26. **(Owner answer A; owner-visible only as the existing "not set up" copy.) A model OpenAI does not offer is `ai_not_configured`.** F §2.8's table has no row for `NotFoundError` (404) or `code == "model_not_found"`, which a retired or mistyped `OPENAI_MODEL` returns; without a row it would be `ai_upstream_error` ("had a problem"), which invites a retry that can never work. `_mapped` checks it after the timeout, quota and rate-limit rows, logs `ERROR AI: model not available (OPENAI_MODEL=<m>)` (the model name is configuration, not a secret) and never retries it (a 4xx). T15 adds the row to F's amendments.
27. **(Owner decision 1.) `OPENAI_REASONING_EFFORT`, optional.** S says the model must be non-reasoning. The setting keeps a GPT-5-family model usable if the non-reasoning ones are retired: when set (a lowercase word such as `minimal`, `low` or `none`), `complete()` sends `reasoning_effort`; when unset nothing is sent, exactly as for `temperature`. Anything else logs a WARNING and is ignored. `reasoning_effort` first appears in `chat.completions.create` in openai 1.58.0, so the pin is `openai>=1.58.0,<4` (the upper bound keeps a future major release from arriving unreviewed; the installed 3.20.0 satisfies it). While planning, `test_openai_client.py`'s 23 tests also passed with openai 1.58.0 itself on the path (httpx 0.28), so the floor is real, not only the installed release.
28. **(Owner decision 1.) The parser rejects impossible chapters and dotted verses.** No book has more than 150 chapters, so a chapter above `MAX_CHAPTER = 150` makes the segment unparsed. (A chapter-only `ff` once ran to a whole-book sentinel; since the 3a build it is that chapter only, owner answer B in "Build notes (3a build)".) `normalize_book_text` drops periods, so "John 3.16" would read as chapter 316 and "Ps 1.1" as Psalm 11; a segment with a period between digits is therefore unparsed too, and the text fallback still sees it. "Esd 1" stays unparsed: "esd" alone is ambiguous between 1 and 2 Esdras, so no alias is added. `test_impossible_chapters_and_dotted_verses_are_unparsed` (T4) pins all three; the synthetic sample's rate is unchanged.
29. **(Owner decision 1.) One DEBUG line per scripture-matches call**, counts only (S Risks, "Unknown `scripture_refs` formats in production"): `hymn_matches refs=<n> refs_unparsed=<n> hymns=<n> hymns_with_unparsed=<n> matched=<n>`, computed only when DEBUG is on. Never a title or a reference.
30. **(Owner decision 1.) The 75 s deadline can be overrun by a few seconds.** httpx applies `openai.Timeout` per phase (connect, each read, write, pool wait), not to a whole attempt, so a response that trickles in can run somewhat past the attempt's timeout. The 15 s between the 75 s server deadline and the 90 s client timeout covers it. T15 adds this note to S §3.7.
31. **(Owner decision 1; 3a build.) `GET /hymns` caps `offset` at 1 000 000** (`le=1_000_000`, 422 `invalid_request` above it). S gives no upper bound; an unbounded offset only makes the database walk past rows no church has (the largest hymnal is about 1 000 hymns), and a cap keeps the parameter inside what every database accepts. `test_limit_offset_and_total` pins 1 000 000 as 200 and 1 000 001 as 422.

### Risks carried into the plan
- **Model availability (UNVERIFIED).** If `gpt-4.1-mini` is not offered to the project, every suggestion answers `ai_not_configured` until the owner changes `OPENAI_MODEL` (T17 checks with one live suggestion; fallbacks in "Model").
- **Model retirement after the merge.** OpenAI can retire the chosen model at any time, weeks or months after 3a ships, with no deploy on our side. It shows up as every suggestion answering 503 "AI suggestions aren't set up on this app yet." (owner answer A) and one `ERROR AI: model not available (OPENAI_MODEL=<m>)` line per call in Railway's logs; the startup line still says `AI: configured (model=<m>)`, because startup makes no call. The fix is an `OPENAI_MODEL` change on Railway (a fallback from "Model", with `OPENAI_REASONING_EFFORT` for a GPT-5-family one); no code change. The runbook's `OPENAI_MODEL` row says this (T15).
- **Synthetic scripture sample.** Until the owner's export replaces it, the 98 % test proves the parser only against hand-written Hymnary-shaped rows. The export gates marking the PR ready (owner answer D; T16 Step 11).
- **Frozen `app.py` on `main`** no longer imports after T14 (accepted, owner decision 2).
- **Same-title false positives** in recent use (owner answer Q2, accepted).
- **Cost exposure** is bounded by the `ai` bucket (400 per church per day, rejected requests included) and the owner's $15 monthly cap (owner answer B); a reached cap reads "not set up" until the next month, with an ERROR log line and no retry.

## File Structure

**Created**

| Path | Responsibility |
|---|---|
| `docs/superpowers/plans/2026-09-29-slice-3a-hymns-backend.md` | this plan (first commit) |
| `backend/integrations/openai_client.py` | settings, `ai_available`, `complete` (retry, deadline, slots, mapping), `log_startup_state`, `FakeAI`, test hooks (T2, T3) |
| `backend/hymn_search.py` | `normalize_title`, `usage_key`, `parse_themes`, `match_hymns`, `evenly_spaced` (T5) |
| `backend/hymn_suggest.py` | `build_candidates`, `build_prompt`, `parse_suggestion_json`, `resolve_suggestions`, `finalize_slots`, the theme keywords (T11, T12) |
| `backend/usecases/hymns.py` | `resolve_default_hymnal`, `hymnal_overview` (T8), `list_hymns_page` (T9), `scripture_matches` (T10), `suggest_hymns` (T13) |
| `backend/api/routes/hymnals.py` | `GET /hymnals` (T8) |
| `backend/api/routes/hymns.py` | `GET /hymns` (T9), `POST /hymns/scripture-matches` (T10), `POST /hymns/suggestions` (T13) |
| `backend/tests/hymn_fixtures/scripture_refs_sample.csv`, `README.md` | the 98 % sample (synthetic until the owner's export) (T4) |
| New test files | `test_schemas`, `test_openai_client`, `test_scripture_refs_parse`, `test_hymn_search`, `test_hymn_match_parity`, `test_hymn_usage_window`, `test_api_hymnals`, `test_api_hymns`, `test_api_hymn_matches`, `test_hymn_suggest`, `test_api_hymn_suggestions` |

**Modified**

| Path | Change |
|---|---|
| `backend/api/schemas.py` | `SectionKey`, `HymnRef`, `SlotHymns`, `HymnalCode` (T1); `ChurchProfileOut` + 2 fields (T8) |
| `backend/api/main.py` | the startup AI line (T2); mount `hymnals` (T8) and `hymns` (T9); `GZipMiddleware` innermost (T9) |
| `backend/requirements.txt` | `openai>=1.58.0,<4` (T2); `lxml` removed (T14) |
| `backend/.env.example` | the `OPENAI_*` block (T2) |
| `backend/scripture_refs.py` | the parser section (T4) |
| `backend/repos/hymns.py` | `HymnRecord`, `HymnalSummary`, `hymnal_summaries`, `query_hymns`, `list_hymnal_records` (T6) |
| `backend/repos/churches.py` | `get_church_rubric_overrides(church_id, *, session=None)` (T6) |
| `backend/hymn_ranking.py` | accessors and `is_newer_than_preferred` (T6); docstring (T14) |
| `backend/hymn_usage.py` | `RECENT_WEEKS`, `usage_near` (T7) |
| `backend/usecases/church_profile.py` | the two hymnal fields, one session (T8) |
| `backend/worship_service.py` | the hymn code deleted (T14) |
| `backend/tests/conftest.py` | autouse `_fresh_ai` (T2; `usecases.hymns` added in T13) |
| `backend/tests/test_no_streamlit_in_core.py` | import list (T2, T5, T13) |
| `backend/tests/test_api_app.py` | the error-doc map (T8, T9, T10, T13) |
| `backend/tests/test_api_church_profile.py`, `test_api_churches.py`, `test_api_invites.py`, `test_api_me.py` | `/church` exact bodies (T8) |
| `backend/tests/test_hymns_repo.py`, `test_hymn_ranking.py`, `test_churches_repo.py` | T6's tests |
| `backend/tests/test_middleware.py` | the order test expects GZip innermost (T9) |
| `backend/tests/test_hymn_match_parity.py` | the old half removed, the AC9 test added (T14) |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated (T8, T9, T10, T13) |
| `frontend/src/test/fixtures/index.ts` | `churchProfile()` gains the two fields (T8; clarification 13) |
| `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` | D16; three amendment rows; the §1.3 sentence (T15) |
| `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md` | "(3a plan)" notes; open questions answered; the follow-up (T15) |
| `docs/ops-runbook.md` | the `OPENAI_*` rows (T15) |

**Deleted:** `backend/tests/test_suggest_hymns.py` (13 tests; equivalents in clarification 15).

**Untouched:** migrations, `app.py`, `ui_helpers.py`, `streamlit_views/*`, `streamlit_tests/*`, CI workflows, every frontend source file except the generated API files and one test fixture.

**Task order and checkpoints:** T1 → T2 → ... → T15 → T16 → T17. Each of T1-T15 ends in one commit (T4 may add a second, the owner's sample), so with the plan's two commits (the plan and its review fixes) the branch carries 17 commits (18 with the export) before T16. The review checkpoints at the end of every task are stops for the controller, not merges: everything ships in the one 3a PR.

---
### Task 1: Commit the plan, check the baseline, and add the shared hymn models (F §1.3 frozen; S API Models, Testing "Contract and guards"; clarification 8)

This task commits the plan and adds the three models F §1.3 froze, `SectionKey`, `HymnRef` and `SlotHymns`, plus S's `HymnalCode`, to `backend/api/schemas.py`. Slice 3 lands first, so it creates them; no 3a route uses them, so the OpenAPI snapshot does not change for them, and slices 4 and 5a import them unchanged. `Page[T]` already exists (slice 1). The frontend does not change.

**Files:**
- Create: `docs/superpowers/plans/2026-09-29-slice-3a-hymns-backend.md` (this plan; already the branch's first commit when the controller hands it over)
- Modify: `backend/api/schemas.py` (append after the last line, `passages: list[PassageOut] ...`)
- Test: `backend/tests/test_schemas.py` (new)

**Interfaces:**
- Consumes: `api.schemas` imports (`Annotated`, `Literal`, `Optional`, `uuid`, `BaseModel`, `ConfigDict`, `Field`, `StringConstraints`, all already imported at `schemas.py:1-9`); `api.main.create_app`.
- Produces (F §1.3, frozen; later users: slices 4 and 5a):
  - `api.schemas.SectionKey = Literal["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance", "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]`
  - `api.schemas.HymnRef(hymn_id: UUID | None = None, title: str = "" (≤300), number: int | None (0..100 000), hymnal: str | None (≤20, no pattern))`, `extra="forbid"`
  - `api.schemas.SlotHymns(opening, response, closing: HymnRef | None = None)`, `extra="forbid"`
  - `api.schemas.HymnalCode = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{2,20}$")]` (6a only)

- [ ] **Step 1 (agent): Confirm the branch and the baseline**

```bash
git status --short
git log --oneline -3
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -c "import openai, inspect; from openai.resources.chat.completions import Completions; p = inspect.signature(Completions.create).parameters; print(openai.__version__, 'max_completion_tokens' in p and 'reasoning_effort' in p)"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
```

**Expected:** `git status --short` lists only `?? .claude/` (or nothing); the log shows `<sha> Plan: slice 3a review fixes` over `6218180 Plan: slice 3a hymns backend (S slice 3; owner answers 2026-09-29)` over `720a8b2 Merge pull request #25 ...`; `971 passed, 9 skipped in <t>s`; `3.20.0 True` (any version ≥ 1.58.0 prints `True`); ` Test Files  55 passed (55)` and `      Tests  356 passed (356)`; `4`. If any differs, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `backend/tests/test_schemas.py`:**

````python
"""The shared hymn and liturgy models, frozen in F §1.3 and created by slice 3
(S "API Models", Testing "Contract and guards"). Slices 4 and 5a import them
unchanged and keep their own tests; these pin the frozen shape."""
import uuid

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from api.main import create_app
from api.schemas import HymnalCode, HymnRef, SectionKey, SlotHymns


def test_extra_fields_rejected_on_hymn_ref_and_slot_hymns():
    with pytest.raises(ValidationError):
        HymnRef(title="Holy, Holy, Holy", audio_url="https://example.org/a.mp3")
    with pytest.raises(ValidationError):
        SlotHymns(opening=None, offertory={"title": "Doxology"})
    with pytest.raises(ValidationError):        # extra inside a nested HymnRef too
        SlotHymns(opening={"title": "Doxology", "slot": "opening"})


def test_title_300_accepted_301_rejected():
    assert len(HymnRef(title="t" * 300).title) == 300
    with pytest.raises(ValidationError):
        HymnRef(title="t" * 301)


def test_number_bounds():
    assert HymnRef(number=0).number == 0
    assert HymnRef(number=100_000).number == 100_000
    for bad in (-1, 100_001):
        with pytest.raises(ValidationError):
            HymnRef(number=bad)


def test_hymnal_length_capped_but_no_pattern():
    with pytest.raises(ValidationError):
        HymnRef(hymnal="H" * 21)
    # Codes that break HymnalCode's pattern are accepted (F §1.3: no pattern on HymnRef).
    for code in ("PH 1990", "X", "gg.2013"):
        assert HymnRef(hymnal=code).hymnal == code


def test_null_hymn_id_and_defaults_accepted():
    ref = HymnRef(hymn_id=None, title="Archived Hymn", number=None, hymnal=None)
    assert ref.hymn_id is None
    assert HymnRef().model_dump() == {"hymn_id": None, "title": "", "number": None, "hymnal": None}
    hymn_id = uuid.uuid4()
    slots = SlotHymns(opening={"hymn_id": str(hymn_id), "title": "x", "number": 1, "hymnal": "GG2013"})
    assert slots.opening.hymn_id == hymn_id
    assert (slots.response, slots.closing) == (None, None)


def test_section_key_rejects_an_unknown_section():
    class Section(BaseModel):
        key: SectionKey

    assert Section(key="prayers_of_the_people").key == "prayers_of_the_people"
    with pytest.raises(ValidationError):
        Section(key="offering")


def test_hymnal_code_pattern_and_models_absent_from_openapi():
    code = TypeAdapter(HymnalCode)
    assert code.validate_python("GG2013") == "GG2013"
    for bad in ("PH 1990", "X", "G" * 21):
        with pytest.raises(ValidationError):
            code.validate_python(bad)
    # No slice-3 route uses them, so the committed snapshot does not change for them.
    schemas = create_app().openapi()["components"]["schemas"]
    assert not {"HymnRef", "SlotHymns"} & set(schemas)
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_schemas.py 2>&1 | tail -3
```

**Expected:**

```
ERROR backend/tests/test_schemas.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

The collection error is `ImportError: cannot import name 'HymnalCode' from 'api.schemas'`.

- [ ] **Step 4 (agent): Add the models**

**Append to `backend/api/schemas.py`:**

````python


# --- slice 3a: shared hymn and liturgy models (F §1.3, frozen; S "API Models") ---
# Created here because slice 3 lands first. No slice-3 route uses them, so they
# stay out of the OpenAPI snapshot until slice 4 adds a route that does. Slices
# 4 and 5a import them unchanged and never redefine, tighten or loosen them.

SectionKey = Literal["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer",
                     "benediction"]


class HymnRef(BaseModel):
    """One slot's hymn (F §1.3). hymn_id null = an archived snapshot, used as
    sent; for a non-null id the server reads title, number and hymnal from
    the database and ignores the client's copy."""

    model_config = ConfigDict(extra="forbid")

    hymn_id: Optional[uuid.UUID] = None
    title: str = Field(default="", max_length=300)
    number: Optional[int] = Field(default=None, ge=0, le=100_000)
    # No pattern: a pick echoes hymns.hymnal from the database, and codes written
    # by CLI imports were never pattern-checked (F §1.3).
    hymnal: Optional[str] = Field(default=None, max_length=20)


class SlotHymns(BaseModel):
    """The three hymn slots (F §1.3): slice 4's GenerateLiturgyIn.hymns, 5a's ServiceDraft.hymns."""

    model_config = ConfigDict(extra="forbid")

    opening: Optional[HymnRef] = None
    response: Optional[HymnRef] = None
    closing: Optional[HymnRef] = None


# Only for parameters that name a NEW or admin-managed hymnal code (6a). Never
# on HymnRef and never on slice 3's read filters, which accept any stored code.
HymnalCode = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{2,20}$")]
````

- [ ] **Step 5 (agent): Run the tests, the contract test and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_schemas.py backend/tests/test_openapi_contract.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `10 passed in <t>s` (7 new, and the 3 contract tests pass without regenerating: no route uses the new models); `978 passed, 9 skipped in <t>s`; then exactly ` M backend/api/schemas.py`, `?? backend/tests/test_schemas.py` (and `?? .claude/`).

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/api/schemas.py backend/tests/test_schemas.py
git commit -m "API: the shared HymnRef, SlotHymns and SectionKey models (F §1.3 frozen; S API Models)" -m "Slice 3 lands first, so it creates the three models F §1.3 froze, with
exactly that shape: HymnRef forbids extra fields, caps title at 300 and
number at 0..100000, and takes any hymnal code up to 20 characters (no
pattern: CLI-imported codes were never checked). HymnalCode is defined for
6a's new or admin-managed codes; no 3a field uses it (clarification 8). No
route uses the models yet, so the OpenAPI snapshot is unchanged.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check `git show --stat HEAD` (2 files) against F §1.3's code block: the four definitions match it field for field, `hymnal` has no pattern, and the test proves `"PH 1990"` and `"X"` are accepted. Then `git push origin claude/slice-2-plan-4q33le` (standing backup permission, owner answer Q5).

Counts after Task 1: backend **978 passed, 9 skipped**; frontend **356 in 55 files**.

### Task 2: The OpenAI client's settings, availability, startup line and fake (F §2.8; S Backend 1 rows 1-2, 3.7 "Startup", Module map `requirements.txt` and `.env.example`; owner answer Q3; AC5 half, AC15 half; clarifications 5, 20)

This task creates `backend/integrations/openai_client.py` without the network call: the settings (`ai_settings()`, read once per process from the environment), `ai_available()`, the startup log line (exactly one of four, never the key), `FakeAI` and `set_ai_for_tests()`, the test hooks, and the module-level `complete()` that routes to a fake or to `_complete`. Here `_complete` only raises `NotConfigured`; Task 3 replaces it with the real call. The lifespan in `api/main.py` logs the AI state once. `requirements.txt` raises the pin to `openai>=1.58.0,<4`, the first release whose `create()` takes both `max_completion_tokens` and `reasoning_effort`, below the next major release (installed: 3.20.0), and `backend/.env.example` drops the stale `gpt-3.5-turbo` default for the recommended model (see "Model"; UNVERIFIED) and lists the new settings. An autouse fixture resets the module between tests.

**Decisions recorded in this task:**
- **T2-1 (clarification 5).** Settings live in the client, not `api/settings.py`.
- **T2-2.** `AISettings.problem` checks the key first, then ASCII, then the model, so a missing key is reported even when the model is missing too. A non-ASCII key logs ERROR; the other two WARNING (S 3.7).
- **T2-3.** `OPENAI_TEMPERATURE` must be a number ≥ 0; anything else is ignored with a WARNING and no temperature is sent.
- **T2-4 (clarification 27).** `OPENAI_REASONING_EFFORT` is optional: stripped and lower-cased, it must be one word of letters (`minimal`, `low`, `none`, ...); anything else is ignored with a WARNING. Task 3 sends it only when set.

**Files:**
- Create: `backend/integrations/openai_client.py`
- Modify: `backend/api/main.py` (one import after `from db.schema_check import run_startup_checks`; one line at the end of the lifespan's startup half)
- Modify: `backend/requirements.txt` (`openai>=1.0.0` → a comment and `openai>=1.58.0,<4`)
- Modify: `backend/.env.example` (the `OPENAI_*` block)
- Modify: `backend/tests/conftest.py` (autouse `_fresh_ai`, before the slice 1 network-guard section)
- Modify: `backend/tests/test_no_streamlit_in_core.py` (import list)
- Test: `backend/tests/test_openai_client.py` (new; 9 tests here, 14 more in Task 3)

**Interfaces:**
- Consumes: `domain_errors.Busy`, `NotConfigured`, `UpstreamError`, `UpstreamTimeout`; the `openai` package (`openai.OpenAI`, `openai.Timeout`); `api.main.lifespan`; `tests.conftest` patterns (`sys.modules.get` deferred resets).
- Produces (later users: Task 3, Task 13, slice 4):
  - `integrations.openai_client.AISettings(api_key, model, timeout_seconds=30.0, max_retries=1, max_concurrency=4, temperature=None, reasoning_effort=None)` with `.problem -> str | None`; `load_settings(environ) -> AISettings`; `ai_settings()` (cached).
  - `ai_available() -> bool`; `complete(messages, *, max_completion_tokens: int, json_mode: bool = False, deadline: float | None = None) -> str`.
  - `log_startup_state() -> None`: `INFO AI: configured (model=<m>)`, or `WARNING AI: not configured (OPENAI_API_KEY missing)` / `(OPENAI_MODEL missing)`, or `ERROR AI: not configured (OPENAI_API_KEY is not ASCII)`.
  - `FakeAI(reply="{}", available=True, error=None)` with `.calls` (`[{"messages", "max_completion_tokens", "json_mode", "deadline"}]`); `set_ai_for_tests(fake | None)`; `configure_for_tests(*, settings=None, sdk_client=None, semaphore=None, clock=None, sleep=None)`; `reset_for_tests()`.
  - Constants `NOT_CONFIGURED_MESSAGE`, `BUSY_MESSAGE`, `TIMEOUT_MESSAGE`, `UPSTREAM_MESSAGE`, `SEMAPHORE_WAIT_SECONDS = 15.0`, `DEADLINE_MARGIN_SECONDS = 5.0`, `MIN_RETRY_SECONDS = 5.0`, `MAX_BACKOFF_SECONDS = 2.0`, `CONNECT_TIMEOUT_SECONDS = 5.0`.
  - `backend/tests/conftest.py`: autouse `_fresh_ai` (calls `integrations.openai_client.reset_for_tests()` when imported).

- [ ] **Step 1 (agent): Confirm Task 1's commit and the count**

```bash
git log --oneline -1
.venv/bin/python -m pytest -q | tail -1
grep -n "openai\|lxml" backend/requirements.txt
```

**Expected:** `<sha> API: the shared HymnRef, SlotHymns and SectionKey models ...`; `978 passed, 9 skipped in <t>s`; `17:lxml>=4.9.0` and `19:openai>=1.0.0`.

- [ ] **Step 2 (agent): Write the failing tests and the reset fixture**

**In `backend/tests/conftest.py`, replace:**

````python
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
````

**with:**

````python
    yield


# --- slice 3a: the OpenAI client (F §2.8; S Backend 3.7) ---

@pytest.fixture(autouse=True)
def _fresh_ai():
    """integrations.openai_client keeps its settings, SDK client, slots and any
    FakeAI installed by set_ai_for_tests for the whole process (slice 3a). Each
    test starts with no fake and the settings read again from the environment,
    so a fake or a configured key never leaks from an earlier test.

    Resets only when the module is already imported (the deferred-import rule
    at the top of this file)."""
    import sys

    module = sys.modules.get("integrations.openai_client")
    if module is not None:
        module.reset_for_tests()
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
````

**with:**

````python
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
````

**Create `backend/tests/test_openai_client.py`:**

````python
"""integrations.openai_client (F §2.8 as refined by slice 3; S Backend 3.7,
Testing `test_openai_client.py`; AC5, AC6, AC18).

No test reaches OpenAI: the settings come from a dict, and the SDK client is
a stand-in whose chat.completions.create records each call and answers from a
script of replies and SDK exceptions (built with the SDK's own HTTP types).
"""
import inspect
import logging
from pathlib import Path

import openai
import pytest

from domain_errors import Busy
from integrations import openai_client as ai

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
MESSAGES = [{"role": "system", "content": "Reply with JSON only."},
            {"role": "user", "content": "Pick hymns."}]


def settings(**overrides) -> ai.AISettings:
    return ai.AISettings(**{"api_key": "sk-test", "model": "test-model", **overrides})


# --- T2: settings, availability, the startup line, the fake ---------------------------


def test_no_key_is_not_configured_with_a_warning(caplog):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    loaded = ai.load_settings({"OPENAI_MODEL": "test-model", "OPENAI_API_KEY": "   "})
    assert loaded.api_key == "" and loaded.problem == "OPENAI_API_KEY missing"
    ai.configure_for_tests(settings=loaded)
    assert ai.ai_available() is False
    ai.ai_settings.cache_clear()
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("OPENAI_API_KEY", raising=False)
        mp.setenv("OPENAI_MODEL", "test-model")
        ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("WARNING", "AI: not configured (OPENAI_API_KEY missing)")]


def test_key_without_model_is_not_configured(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    ai.reset_for_tests()
    assert ai.ai_available() is False
    ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("WARNING", "AI: not configured (OPENAI_MODEL missing)")]
    assert "sk-secret-value" not in caplog.text


def test_non_ascii_key_is_not_configured_and_never_logged(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-‑pasted key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    ai.reset_for_tests()
    assert ai.ai_available() is False
    ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("ERROR", "AI: not configured (OPENAI_API_KEY is not ASCII)")]
    assert "pasted" not in caplog.text


def test_configured_logs_the_model_only(caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    monkeypatch.setenv("OPENAI_API_KEY", "  sk-secret-value  ")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    ai.reset_for_tests()
    assert ai.ai_settings().api_key == "sk-secret-value"          # stripped
    assert ai.ai_available() is True
    ai.log_startup_state()
    assert [(r.levelname, r.getMessage()) for r in caplog.records] == [
        ("INFO", "AI: configured (model=test-model)")]
    assert "sk-secret" not in caplog.text


def test_settings_defaults_overrides_and_bad_values(caplog):
    defaults = ai.load_settings({"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"})
    assert (defaults.timeout_seconds, defaults.max_retries, defaults.max_concurrency,
            defaults.temperature) == (30.0, 1, 4, None)
    custom = ai.load_settings({"OPENAI_API_KEY": "k", "OPENAI_MODEL": " m ",
                               "OPENAI_TIMEOUT_SECONDS": "20", "OPENAI_MAX_RETRIES": "0",
                               "OPENAI_MAX_CONCURRENCY": "2", "OPENAI_TEMPERATURE": "0.3"})
    assert (custom.model, custom.timeout_seconds, custom.max_retries, custom.max_concurrency,
            custom.temperature) == ("m", 20.0, 0, 2, 0.3)
    bad = ai.load_settings({"OPENAI_TIMEOUT_SECONDS": "soon", "OPENAI_MAX_RETRIES": "-1",
                            "OPENAI_MAX_CONCURRENCY": "0", "OPENAI_TEMPERATURE": "warm"})
    assert (bad.timeout_seconds, bad.max_retries, bad.max_concurrency, bad.temperature) == (
        30.0, 1, 4, None)
    assert caplog.text.count("is not valid") == 4


def test_reasoning_effort_is_read_only_when_set(caplog):
    assert ai.load_settings({"OPENAI_API_KEY": "k", "OPENAI_MODEL": "m"}).reasoning_effort is None
    assert ai.load_settings({"OPENAI_REASONING_EFFORT": "  "}).reasoning_effort is None
    assert ai.load_settings({"OPENAI_REASONING_EFFORT": " Minimal "}).reasoning_effort == "minimal"
    assert ai.load_settings({"OPENAI_REASONING_EFFORT": "very high"}).reasoning_effort is None
    assert caplog.text.count("is not valid") == 1


def test_fake_ai_records_calls_and_takes_over_until_reset():
    fake = ai.FakeAI(reply='{"opening": []}', available=True)
    ai.set_ai_for_tests(fake)
    assert ai.ai_available() is True
    assert ai.complete(MESSAGES, max_completion_tokens=50, json_mode=True, deadline=12.5) == '{"opening": []}'
    assert fake.calls == [{"messages": MESSAGES, "max_completion_tokens": 50,
                           "json_mode": True, "deadline": 12.5}]
    ai.set_ai_for_tests(ai.FakeAI(available=False, error=Busy(ai.BUSY_MESSAGE, code="ai_busy")))
    assert ai.ai_available() is False
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=50)
    ai.reset_for_tests()
    ai.configure_for_tests(settings=settings(api_key=""))
    assert ai.ai_available() is False                    # the real client again


def test_the_lifespan_logs_the_ai_state_once(tmp_db, caplog, monkeypatch):
    from fastapi.testclient import TestClient

    from api.main import create_app

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    ai.reset_for_tests()
    caplog.set_level(logging.INFO)
    with TestClient(create_app()):
        pass
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("AI:")]
    assert lines == ["AI: not configured (OPENAI_API_KEY missing)"]


def test_installed_sdk_takes_max_completion_tokens_and_requirements_pin():
    # openai>=1.58.0 is the first release whose create() takes both max_completion_tokens
    # and reasoning_effort; <4 keeps the next major release out until it is reviewed.
    create = openai.OpenAI(api_key="sk-test").chat.completions.create
    assert {"max_completion_tokens", "reasoning_effort"} <= set(inspect.signature(create).parameters)
    lines = [line.strip() for line in REQUIREMENTS.read_text().splitlines()]
    assert "openai>=1.58.0,<4" in lines
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_openai_client.py 2>&1 | tail -3
```

**Expected:**

```
ERROR backend/tests/test_openai_client.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

(`ImportError: cannot import name 'openai_client' from 'integrations'`.)

- [ ] **Step 4 (agent): Write the client, the startup line, the pin and `.env.example`**

**In `backend/.env.example`, replace:**

````bash
ESV_API_KEY=

# Carried over for later slices (liturgy generation, Gmail sending).
OPENAI_API_KEY=
OPENAI_MODEL=gpt-3.5-turbo
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
````

**with:**

````bash
ESV_API_KEY=

# AI: hymn suggestions (slice 3) and liturgy (slice 4). Read by
# integrations/openai_client.py; the key stays on the backend. OPENAI_MODEL has no
# default in code: with no model (or no key) AI is off and the startup log says why.
# Use a non-reasoning, inexpensive chat model that accepts response_format
# json_object and max_completion_tokens (slice 3 plan, "Model").
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
OPENAI_TIMEOUT_SECONDS=30
OPENAI_MAX_RETRIES=1
OPENAI_MAX_CONCURRENCY=4
# Sent only when set; reasoning models reject a non-default temperature.
# OPENAI_TEMPERATURE=
# Sent only when set: only for a reasoning (GPT-5-family) model, e.g. minimal or low.
# OPENAI_REASONING_EFFORT=

# Carried over for a later slice (Gmail sending).
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
````

**In `backend/api/main.py`, replace:**

````python
from db import get_engine
from db.schema_check import run_startup_checks

load_dotenv()
````

**with:**

````python
from db import get_engine
from db.schema_check import run_startup_checks
from integrations import openai_client

load_dotenv()
````

**In `backend/api/main.py`, replace:**

````python
        logger.warning("SUPABASE_URL is not set; every authenticated request will return 503.")
    yield
````

**with:**

````python
        logger.warning("SUPABASE_URL is not set; every authenticated request will return 503.")
    openai_client.log_startup_state()                       # one "AI: ..." line, never the key
    yield
````

**Create `backend/integrations/openai_client.py`:**

````python
"""The one OpenAI client (F §2.8, with slice 3's refinements; S Backend 3.7).

- ai_settings(): OPENAI_API_KEY (stripped), OPENAI_MODEL (required, no
  default), OPENAI_TIMEOUT_SECONDS (30), OPENAI_MAX_RETRIES (1),
  OPENAI_MAX_CONCURRENCY (4), OPENAI_TEMPERATURE (unset),
  OPENAI_REASONING_EFFORT (unset). A missing key or model, or a key that is
  not ASCII, means "not configured".
- ai_available() and complete(messages, *, max_completion_tokens,
  json_mode=False, deadline=None) -> str. complete() always sends
  max_completion_tokens, sends response_format json_object in json_mode, and
  temperature and reasoning_effort only when they are set. It holds one of OPENAI_MAX_CONCURRENCY
  slots per call and retries itself (the SDK client has max_retries=0).
- log_startup_state(): the lifespan's one "AI: ..." line. The key is never
  logged, and no member ever sees configuration detail.
- FakeAI and set_ai_for_tests(): no test reaches OpenAI (F §5.3).

There is no hymn-specific code here. Callers that want their own wording for
ai_not_configured catch NotConfigured and raise their own (usecases.hymns).
No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Callable, Mapping, Optional, Sequence

import openai

from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout

logger = logging.getLogger(__name__)

NOT_CONFIGURED_MESSAGE = "AI isn't set up on this app yet."
BUSY_MESSAGE = "The AI service is busy. Try again in a minute."
TIMEOUT_MESSAGE = "The AI took too long to answer. Try again."
UPSTREAM_MESSAGE = "The AI service had a problem. Try again."

SEMAPHORE_WAIT_SECONDS = 15.0      # F §2.8: waiting longer for a slot is ai_busy
DEADLINE_MARGIN_SECONDS = 5.0      # with a deadline: wait at most remaining - 5 s for a slot
MIN_RETRY_SECONDS = 5.0            # a retry starts only with at least this much time left
MAX_BACKOFF_SECONDS = 2.0          # min(Retry-After or 1 s, 2 s)
CONNECT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class AISettings:
    api_key: str = ""
    model: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 1
    max_concurrency: int = 4
    temperature: Optional[float] = None
    reasoning_effort: Optional[str] = None     # e.g. "minimal"; only for a reasoning model

    @property
    def problem(self) -> Optional[str]:
        """Why AI is not configured (for the startup log), or None when it is."""
        if not self.api_key:
            return "OPENAI_API_KEY missing"
        if not self.api_key.isascii():
            return "OPENAI_API_KEY is not ASCII"
        if not self.model:
            return "OPENAI_MODEL missing"
        return None


def _number(environ: Mapping[str, str], name: str, default, cast, minimum):
    raw = (environ.get(name) or "").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        value = None
    if value is None or value < minimum:
        logger.warning("AI: %s=%r is not valid; using %s", name, raw, default)
        return default
    return value


def _reasoning_effort(environ: Mapping[str, str]) -> Optional[str]:
    raw = (environ.get("OPENAI_REASONING_EFFORT") or "").strip()
    if not raw:
        return None
    if not re.fullmatch(r"[a-z]+", raw.lower()):
        logger.warning("AI: %s=%r is not valid; using %s", "OPENAI_REASONING_EFFORT", raw, None)
        return None
    return raw.lower()


def load_settings(environ: Mapping[str, str] = os.environ) -> AISettings:
    temperature = _number(environ, "OPENAI_TEMPERATURE", None, float, 0.0)
    return AISettings(
        api_key=(environ.get("OPENAI_API_KEY") or "").strip(),
        model=(environ.get("OPENAI_MODEL") or "").strip(),
        timeout_seconds=_number(environ, "OPENAI_TIMEOUT_SECONDS", 30.0, float, 1.0),
        max_retries=_number(environ, "OPENAI_MAX_RETRIES", 1, int, 0),
        max_concurrency=_number(environ, "OPENAI_MAX_CONCURRENCY", 4, int, 1),
        temperature=temperature,
        reasoning_effort=_reasoning_effort(environ),
    )


@lru_cache
def ai_settings() -> AISettings:
    """The settings, read once per process (reset_for_tests clears them)."""
    return load_settings()


def log_startup_state() -> None:
    """Exactly one line (S Backend 3.7). Never the key."""
    settings = ai_settings()
    problem = settings.problem
    if problem is None:
        logger.info("AI: configured (model=%s)", settings.model)
    elif problem == "OPENAI_API_KEY is not ASCII":
        logger.error("AI: not configured (%s)", problem)
    else:
        logger.warning("AI: not configured (%s)", problem)


# --- the fake (tests) ----------------------------------------------------------


@dataclass
class FakeAI:
    """complete() records each call and returns `reply` (a str, or a callable
    taking the messages), or raises `error`. ai_available() returns `available`."""

    reply: Any = "{}"
    available: bool = True
    error: Optional[BaseException] = None
    calls: list[dict] = field(default_factory=list)

    def ai_available(self) -> bool:
        return self.available

    def complete(self, messages, *, max_completion_tokens: int, json_mode: bool = False,
                 deadline: Optional[float] = None) -> str:
        self.calls.append({"messages": [dict(m) for m in messages],
                           "max_completion_tokens": max_completion_tokens,
                           "json_mode": json_mode, "deadline": deadline})
        if self.error is not None:
            raise self.error
        return self.reply(messages) if callable(self.reply) else self.reply


_override: Optional[FakeAI] = None


def set_ai_for_tests(fake: Optional[FakeAI]) -> None:
    """Tests: route ai_available() and complete() to `fake` (None restores the real client)."""
    global _override
    _override = fake


# --- the real client -------------------------------------------------------------


class _State:
    """The SDK client, the concurrency slots, the clock and the sleep, for the current settings."""

    def __init__(self, settings: AISettings, *, sdk_client: Any = None, semaphore: Any = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.settings = settings
        self._sdk_client = sdk_client
        self.semaphore = semaphore or threading.BoundedSemaphore(settings.max_concurrency)
        self.clock = clock
        self.sleep = sleep

    @property
    def sdk_client(self):
        if self._sdk_client is None:
            # max_retries=0: complete() retries itself (the SDK honors Retry-After
            # for up to 60 s while holding a slot; S Backend 3.7).
            self._sdk_client = openai.OpenAI(
                api_key=self.settings.api_key, max_retries=0,
                timeout=openai.Timeout(self.settings.timeout_seconds,
                                       connect=CONNECT_TIMEOUT_SECONDS))
        return self._sdk_client


_state: Optional[_State] = None
_state_lock = threading.Lock()


def _current() -> _State:
    global _state
    with _state_lock:
        if _state is None:
            _state = _State(ai_settings())
        return _state


def configure_for_tests(*, settings: Optional[AISettings] = None, sdk_client: Any = None,
                        semaphore: Any = None, clock: Optional[Callable[[], float]] = None,
                        sleep: Optional[Callable[[float], None]] = None) -> None:
    """Tests: the real complete() over a fake SDK client, clock, sleep and semaphore."""
    global _state
    with _state_lock:
        _state = _State(settings or ai_settings(), sdk_client=sdk_client, semaphore=semaphore,
                        clock=clock or time.monotonic, sleep=sleep or time.sleep)


def reset_for_tests() -> None:
    """Tests: no fake, settings read again from the environment, a new client and slots."""
    global _state, _override
    ai_settings.cache_clear()
    with _state_lock:
        _state = None
    _override = None


def ai_available() -> bool:
    if _override is not None:
        return _override.ai_available()
    return _current().settings.problem is None


def complete(messages: Sequence[Mapping[str, str]], *, max_completion_tokens: int,
             json_mode: bool = False, deadline: Optional[float] = None) -> str:
    """The reply's text. Raises NotConfigured, Busy, UpstreamTimeout or
    UpstreamError (F §2.8's codes, this module's messages); never an SDK error."""
    if _override is not None:
        return _override.complete(messages, max_completion_tokens=max_completion_tokens,
                                  json_mode=json_mode, deadline=deadline)
    return _complete(_current(), messages, max_completion_tokens, json_mode, deadline)



def _complete(state: _State, messages, max_completion_tokens: int, json_mode: bool,
              deadline: Optional[float]) -> str:
    """Task 3 replaces this with the call, the error mapping, the retries and the deadline."""
    raise NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
````

**In `backend/requirements.txt`, replace:**

````text
playwright>=1.40.0
openai>=1.0.0
python-docx>=1.0.0
````

**with:**

````text
playwright>=1.40.0
# 1.58.0 is the first release whose chat.completions.create takes both
# max_completion_tokens (always sent) and reasoning_effort (sent when
# OPENAI_REASONING_EFFORT is set); <4 keeps the next major release out until
# it is reviewed (integrations/openai_client.py).
openai>=1.58.0,<4
python-docx>=1.0.0
````

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_openai_client.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_foundation_setup.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `12 passed in <t>s` (9 new, 3 import-guard tests); `100 passed in <t>s` (the `.env.example` readers still pass); `987 passed, 9 skipped in <t>s`; then exactly:

```
 M backend/.env.example
 M backend/api/main.py
 M backend/requirements.txt
 M backend/tests/conftest.py
 M backend/tests/test_no_streamlit_in_core.py
?? backend/integrations/openai_client.py
?? backend/tests/test_openai_client.py
```

(and `?? .claude/`). The installed SDK already satisfies the new pin, so no `pip install` is needed; CI installs the latest release.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/.env.example backend/api/main.py backend/requirements.txt backend/tests/conftest.py \
        backend/tests/test_no_streamlit_in_core.py backend/integrations/openai_client.py backend/tests/test_openai_client.py
git commit -m "AI: the OpenAI client's settings, startup line and fake (F §2.8; S Backend 3.7; owner answer Q3)" -m "integrations/openai_client.py reads OPENAI_API_KEY (stripped), OPENAI_MODEL
(required, no default), OPENAI_TIMEOUT_SECONDS, OPENAI_MAX_RETRIES,
OPENAI_MAX_CONCURRENCY, OPENAI_TEMPERATURE and OPENAI_REASONING_EFFORT itself
(clarifications 5, 27), and
the lifespan logs exactly one AI line, never the key. A missing key or
model, or a non-ASCII key, means not configured. FakeAI and
set_ai_for_tests keep every test off the network; the autouse _fresh_ai
fixture resets the module. The real call comes in Task 3. requirements.txt
pins openai>=1.58.0,<4 (max_completion_tokens, reasoning_effort); .env.example replaces the
stale gpt-3.5-turbo default with the plan's recommended model.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check that no line of the module or the tests prints or logs the key (`grep -n "api_key" backend/integrations/openai_client.py` shows only the settings field, `problem` and the SDK constructor), that `log_startup_state` has exactly four outcomes, and that the model in `.env.example` is the one in "Model" (UNVERIFIED; the controller confirms it with the owner before Task 17). Push the backup.

Counts after Task 2: backend **987 passed, 9 skipped**; frontend **356 in 55 files**.

### Task 3: `complete()`: the call, the error mapping, the capped retry and the deadline (F §2.8 as amended; S Backend 3.7 "Retries", "Deadline", "Error mapping"; AC5, AC6, AC18; clarification 6)

This task replaces Task 2's placeholder `_complete` with the real path. A call takes one of `OPENAI_MAX_CONCURRENCY` slots (waiting at most 15 s, or remaining − 5 s with a deadline; `ai_busy` otherwise), sends `max_completion_tokens` always, `response_format` json_object in JSON mode, and `temperature` and `reasoning_effort` only when set, with each attempt's timeout `min(OPENAI_TIMEOUT_SECONDS, remaining)`. It retries itself (the SDK client has `max_retries=0`) at most `OPENAI_MAX_RETRIES` times, on connection errors (timeouts included), rate limits other than `insufficient_quota` and 5xx, after `min(Retry-After or 1 s, 2 s)`, and only with at least 5 s left. Errors map in F §2.8's order, subclasses first; `insufficient_quota` is `ai_not_configured` with an ERROR line and no retry, and so is a model OpenAI does not offer (`NotFoundError` or `code == "model_not_found"`; owner answer A, clarification 26), whose ERROR line names `OPENAI_MODEL`. No SDK text ever reaches a message. The tests drive a fake SDK client built with the SDK's own exceptions, a `FakeClock`, a recording `sleep` and a recording semaphore.

**Decisions recorded in this task:**
- **T3-1 (clarification 6).** The per-attempt timeout is `create(timeout=openai.Timeout(t, connect=min(5, t)))`.
- **T3-2.** An attempt with no time left (remaining ≤ 0) is `ai_timeout` without a call. The retry rule "at least 5 s left after the backoff" uses the clock after the failed attempt.
- **T3-3.** One `ai_call ... outcome=ok` INFO line per successful attempt (model, duration, prompt and completion token counts), one WARNING line with the mapped code and the SDK class name per failure, one INFO line per retry (F §2.8 "Logs").
- **T3-4.** Two of the 14 new tests pass before this change: `test_real_sdk_client_is_built_with_max_retries_zero` (Task 2's `_State` already builds the client) and `test_not_configured_raises_before_any_call` (the placeholder already raises it). They pin behavior the change must keep.
- **T3-5 (owner answer A; clarification 26).** `NotFoundError` (404) and any SDK error whose `code` is `model_not_found` map to `ai_not_configured` after the timeout, quota and rate-limit rows and before the key rows, with `ERROR AI: model not available (OPENAI_MODEL=<m>)`. To make it `ai_upstream_error` instead (the other answer the owner was offered), `_mapped` would return `UpstreamError(UPSTREAM_MESSAGE, code="ai_upstream_error")` there and the test's expected code would change; nothing else.

**Files:**
- Modify: `backend/integrations/openai_client.py` (replace the placeholder `_complete`, the file's last function)
- Test: `backend/tests/test_openai_client.py` (the import block; 14 tests appended)

**Interfaces:**
- Consumes: Task 2's `_State` (`settings`, `sdk_client`, `semaphore`, `clock`, `sleep`), `configure_for_tests`, `AISettings`, the message constants; `openai.APITimeoutError`, `APIConnectionError`, `RateLimitError`, `AuthenticationError`, `PermissionDeniedError`, `BadRequestError`, `NotFoundError`, `APIStatusError`, `InternalServerError`, `OpenAIError`, `openai.Timeout`; `tests.conftest.FakeClock`.
- Produces: `complete(...)` as specified above, raising only `NotConfigured("ai_not_configured")`, `Busy("ai_busy")`, `UpstreamTimeout("ai_timeout")` or `UpstreamError("ai_upstream_error")` (later users: Task 13, slice 4).

- [ ] **Step 1 (agent): Confirm Task 2's hand-off**

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from integrations import openai_client as ai; s = ai.AISettings(api_key='k', model='m'); ai.configure_for_tests(settings=s); print(ai._current().settings.model, ai.SEMAPHORE_WAIT_SECONDS, ai.MAX_BACKOFF_SECONDS)"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `m 15.0 2.0`; `987 passed, 9 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `backend/tests/test_openai_client.py`, replace:**

````python
"""
import inspect
````

**with:**

````python
"""
import importlib
import inspect
````

**In `backend/tests/test_openai_client.py`, replace:**

````python
import logging
from pathlib import Path

import openai
````

**with:**

````python
import logging
from pathlib import Path
from types import SimpleNamespace

import openai
````

**In `backend/tests/test_openai_client.py`, replace:**

````python
import pytest

from domain_errors import Busy
from integrations import openai_client as ai

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
MESSAGES = [{"role": "system", "content": "Reply with JSON only."},
````

**with:**

````python
import pytest

from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout
from integrations import openai_client as ai
from tests.conftest import FakeClock

# The HTTP library this SDK is built on (httpx in openai 1.x, httpx2 in 3.x), read
# from the SDK's own annotation of an error's `response`, so the tests build real
# SDK exceptions whichever version is installed.
SDK_HTTP = importlib.import_module(
    str(openai.APIStatusError.__init__.__annotations__["response"]).split(".")[0])
URL = "https://api.openai.com/v1/chat/completions"
REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
MESSAGES = [{"role": "system", "content": "Reply with JSON only."},
````

**Append to `backend/tests/test_openai_client.py`:**

````python


# --- T3: the call, error mapping, retries and the deadline ------------------------------


def _response(status: int, headers: dict | None = None):
    return SDK_HTTP.Response(status, headers=headers or {}, request=SDK_HTTP.Request("POST", URL))


def sdk_error(kind: str, **kw) -> Exception:
    """One SDK exception of each class F §2.8 maps."""
    request = SDK_HTTP.Request("POST", URL)
    if kind == "timeout":
        return openai.APITimeoutError(request=request)
    if kind == "connection":
        return openai.APIConnectionError(request=request)
    classes = {"rate_limit": (openai.RateLimitError, 429), "auth": (openai.AuthenticationError, 401),
               "permission": (openai.PermissionDeniedError, 403),
               "bad_request": (openai.BadRequestError, 400), "not_found": (openai.NotFoundError, 404),
               "server": (openai.InternalServerError, 500),
               "status_502": (openai.APIStatusError, 502)}
    cls, status = classes[kind]
    body = {"code": kw["code"]} if "code" in kw else None
    return cls(f"upstream said {kind}", response=_response(status, kw.get("headers")), body=body)


class FakeSDK:
    """Stands in for openai.OpenAI: create() records kwargs and answers from `script`."""

    def __init__(self, *script):
        self.script = list(script) or ['{"ok": true}']
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, BaseException):
            raise item
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=item))],
                               usage=usage)


class RecordingSemaphore:
    def __init__(self, free: bool = True):
        self.free = free
        self.waits: list = []

    def acquire(self, blocking=True, timeout=None):
        self.waits.append(timeout if blocking else "no-wait")
        return self.free

    def release(self):
        pass


def setup(*script, clock=None, **settings_overrides):
    sdk, sleeps = FakeSDK(*script), []
    ai.configure_for_tests(settings=settings(**settings_overrides), sdk_client=sdk,
                           clock=clock or FakeClock().now, sleep=sleeps.append)
    return sdk, sleeps


def test_real_sdk_client_is_built_with_max_retries_zero():
    ai.configure_for_tests(settings=settings(timeout_seconds=30.0))
    client = ai._current().sdk_client
    assert isinstance(client, openai.OpenAI)
    assert client.max_retries == 0


def test_complete_sends_tokens_json_mode_and_temperature_only_when_set():
    sdk, _ = setup('{"opening": ["H1"]}')
    assert ai.complete(MESSAGES, max_completion_tokens=1200, json_mode=True) == '{"opening": ["H1"]}'
    (call,) = sdk.calls
    assert call["model"] == "test-model"
    assert call["messages"] == MESSAGES
    assert call["max_completion_tokens"] == 1200
    assert "max_tokens" not in call
    assert call["response_format"] == {"type": "json_object"}
    assert "temperature" not in call
    assert (call["timeout"].read, call["timeout"].connect) == (30.0, 5.0)

    sdk, _ = setup("plain", temperature=0.3)
    ai.complete(MESSAGES, max_completion_tokens=10)
    (call,) = sdk.calls
    assert call["temperature"] == 0.3
    assert "response_format" not in call


def test_complete_sends_reasoning_effort_only_when_set():
    sdk, _ = setup("plain")
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert "reasoning_effort" not in sdk.calls[0]
    sdk, _ = setup("plain", reasoning_effort="minimal")
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert sdk.calls[0]["reasoning_effort"] == "minimal"


def test_not_configured_raises_before_any_call():
    sdk, _ = setup("unused", model="")
    with pytest.raises(NotConfigured) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert (caught.value.code, caught.value.message) == ("ai_not_configured", ai.NOT_CONFIGURED_MESSAGE)
    assert sdk.calls == []


def test_every_sdk_error_class_maps_to_its_code():
    expected = {"timeout": (UpstreamTimeout, "ai_timeout", ai.TIMEOUT_MESSAGE),
                "rate_limit": (Busy, "ai_busy", ai.BUSY_MESSAGE),
                "auth": (NotConfigured, "ai_not_configured", ai.NOT_CONFIGURED_MESSAGE),
                "permission": (NotConfigured, "ai_not_configured", ai.NOT_CONFIGURED_MESSAGE),
                "bad_request": (UpstreamError, "ai_upstream_error", ai.UPSTREAM_MESSAGE),
                "connection": (UpstreamError, "ai_upstream_error", ai.UPSTREAM_MESSAGE),
                "server": (UpstreamError, "ai_upstream_error", ai.UPSTREAM_MESSAGE)}
    for kind, (cls, code, message) in expected.items():
        setup(sdk_error(kind), max_retries=0)
        with pytest.raises(cls) as caught:
            ai.complete(MESSAGES, max_completion_tokens=10)
        assert (caught.value.code, caught.value.message) == (code, message), kind
        assert "upstream said" not in caught.value.message            # never the SDK's text


def test_api_timeout_error_is_ai_timeout_not_its_base_class():
    # APITimeoutError subclasses APIConnectionError, which maps to ai_upstream_error.
    assert issubclass(openai.APITimeoutError, openai.APIConnectionError)
    setup(sdk_error("timeout"), sdk_error("timeout"))
    with pytest.raises(UpstreamTimeout) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert caught.value.code == "ai_timeout"


def test_insufficient_quota_is_not_configured_after_one_attempt(caplog):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    sdk, sleeps = setup(sdk_error("rate_limit", code="insufficient_quota"), '{"ok": true}')
    with pytest.raises(NotConfigured) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert caught.value.code == "ai_not_configured"
    assert len(sdk.calls) == 1 and sleeps == []
    assert ("ERROR", "AI: quota exhausted (insufficient_quota)") in [
        (r.levelname, r.getMessage()) for r in caplog.records]


def test_a_model_openai_does_not_offer_is_not_configured(caplog):
    caplog.set_level(logging.INFO, logger="integrations.openai_client")
    for error in (sdk_error("not_found"), sdk_error("not_found", code="model_not_found"),
                  sdk_error("bad_request", code="model_not_found")):
        caplog.clear()
        sdk, sleeps = setup(error, '{"ok": true}', model="retired-model")
        with pytest.raises(NotConfigured) as caught:
            ai.complete(MESSAGES, max_completion_tokens=10)
        assert (caught.value.code, caught.value.message) == ("ai_not_configured", ai.NOT_CONFIGURED_MESSAGE)
        assert len(sdk.calls) == 1 and sleeps == []
        assert ("ERROR", "AI: model not available (OPENAI_MODEL=retired-model)") in [
            (r.levelname, r.getMessage()) for r in caplog.records]


def test_a_500_then_success_retries_once():
    sdk, sleeps = setup(sdk_error("server"), '{"ok": true}')
    assert ai.complete(MESSAGES, max_completion_tokens=10) == '{"ok": true}'
    assert len(sdk.calls) == 2
    assert sleeps == [1.0]                                       # no Retry-After: 1 s


def test_retry_after_60_waits_only_2_seconds():
    sdk, sleeps = setup(sdk_error("rate_limit", headers={"retry-after": "60"}), '{"ok": true}')
    assert ai.complete(MESSAGES, max_completion_tokens=10) == '{"ok": true}'
    assert sleeps == [2.0]


def test_bad_request_is_never_retried_and_retries_stop_at_the_maximum():
    sdk, sleeps = setup(sdk_error("bad_request"), '{"ok": true}')
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert len(sdk.calls) == 1 and sleeps == []

    sdk, sleeps = setup(sdk_error("status_502"), sdk_error("server"), '{"ok": true}')
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10)
    assert len(sdk.calls) == 2 and sleeps == [1.0]               # OPENAI_MAX_RETRIES = 1


def test_the_deadline_shrinks_each_attempt_and_skips_a_late_retry():
    clock = FakeClock()
    sdk, sleeps = setup('{"ok": true}', clock=clock.now)
    ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 12.0)
    assert (sdk.calls[0]["timeout"].read, sdk.calls[0]["timeout"].connect) == (12.0, 5.0)

    def fail_late(**kwargs):            # the attempt uses up time until 4 s remain
        clock.advance(8.0)
        raise sdk_error("server")

    sdk, sleeps = setup(clock=clock.now)
    sdk.chat.completions.create = fail_late
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 12.0)
    assert sleeps == []                                          # 4 s - 1 s backoff < 5 s: no retry


def test_the_slot_wait_is_bounded_by_the_deadline():
    clock = FakeClock()
    busy = RecordingSemaphore(free=False)
    sdk = FakeSDK()
    ai.configure_for_tests(settings=settings(), sdk_client=sdk, semaphore=busy, clock=clock.now)
    with pytest.raises(Busy) as caught:
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 5.5)
    assert (caught.value.code, caught.value.message) == ("ai_busy", ai.BUSY_MESSAGE)
    assert busy.waits == [pytest.approx(0.5)]                   # min(15, remaining - 5)
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=10)         # no deadline: 15 s
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 3.0)
    assert busy.waits[1:] == [15.0, "no-wait"]
    assert sdk.calls == []


def test_a_real_semaphore_times_out_as_ai_busy():
    import threading

    slots = threading.BoundedSemaphore(1)
    slots.acquire()                                              # the one slot is taken
    clock = FakeClock()
    ai.configure_for_tests(settings=settings(), sdk_client=FakeSDK(), semaphore=slots, clock=clock.now)
    with pytest.raises(Busy):
        ai.complete(MESSAGES, max_completion_tokens=10, deadline=clock.now() + 5.05)
    slots.release()
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_openai_client.py 2>&1 | tail -12
```

**Expected:** these twelve fail, and the other eleven (Task 2's nine, and the two named in T3-4) pass:

```
FAILED backend/tests/test_openai_client.py::test_complete_sends_tokens_json_mode_and_temperature_only_when_set
FAILED backend/tests/test_openai_client.py::test_complete_sends_reasoning_effort_only_when_set
FAILED backend/tests/test_openai_client.py::test_every_sdk_error_class_maps_to_its_code
FAILED backend/tests/test_openai_client.py::test_api_timeout_error_is_ai_timeout_not_its_base_class
FAILED backend/tests/test_openai_client.py::test_insufficient_quota_is_not_configured_after_one_attempt
FAILED backend/tests/test_openai_client.py::test_a_model_openai_does_not_offer_is_not_configured
FAILED backend/tests/test_openai_client.py::test_a_500_then_success_retries_once
FAILED backend/tests/test_openai_client.py::test_retry_after_60_waits_only_2_seconds
FAILED backend/tests/test_openai_client.py::test_bad_request_is_never_retried_and_retries_stop_at_the_maximum
FAILED backend/tests/test_openai_client.py::test_the_deadline_shrinks_each_attempt_and_skips_a_late_retry
FAILED backend/tests/test_openai_client.py::test_the_slot_wait_is_bounded_by_the_deadline
FAILED backend/tests/test_openai_client.py::test_a_real_semaphore_times_out_as_ai_busy
12 failed, 11 passed in <t>s
```

Each fails on the placeholder's `NotConfigured` (or on `pytest.raises(Busy)` getting `NotConfigured`; the model test because the placeholder makes no call and logs nothing).

- [ ] **Step 4 (agent): Write the call, the mapping, the retry and the deadline**

**In `backend/integrations/openai_client.py`, replace:**

````python
    return _complete(_current(), messages, max_completion_tokens, json_mode, deadline)



def _complete(state: _State, messages, max_completion_tokens: int, json_mode: bool,
              deadline: Optional[float]) -> str:
````

**with:**

````python
    return _complete(_current(), messages, max_completion_tokens, json_mode, deadline)


def _remaining(state: _State, deadline: Optional[float]) -> Optional[float]:
    return None if deadline is None else deadline - state.clock()


def _is_quota(exc: BaseException) -> bool:
    return isinstance(exc, openai.RateLimitError) and getattr(exc, "code", None) == "insufficient_quota"


def _retryable(exc: BaseException) -> bool:
    if _is_quota(exc):
        return False
    if isinstance(exc, (openai.APIConnectionError, openai.RateLimitError)):
        return True                                   # APITimeoutError is an APIConnectionError
    return isinstance(exc, openai.APIStatusError) and exc.status_code >= 500


def _backoff(exc: BaseException) -> float:
    """min(Retry-After or 1 s, 2 s)."""
    seconds = 1.0
    response = getattr(exc, "response", None)
    raw = response.headers.get("retry-after") if response is not None else None
    if raw:
        try:
            seconds = max(0.0, float(raw))
        except ValueError:
            seconds = 1.0
    return min(seconds, MAX_BACKOFF_SECONDS)


def _is_missing_model(exc: BaseException) -> bool:
    return isinstance(exc, openai.NotFoundError) or getattr(exc, "code", None) == "model_not_found"


def _mapped(exc: BaseException, model: str) -> Exception:
    """F §2.8's mapping, subclasses before their bases (S Backend 3.7), plus a
    model OpenAI does not offer (slice 3a plan, clarification 26)."""
    name = type(exc).__name__
    if isinstance(exc, openai.APITimeoutError):
        return UpstreamTimeout(TIMEOUT_MESSAGE, code="ai_timeout")
    if _is_quota(exc):
        logger.error("AI: quota exhausted (insufficient_quota)")
        return NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
    if isinstance(exc, openai.RateLimitError):
        return Busy(BUSY_MESSAGE, code="ai_busy")
    if _is_missing_model(exc):                        # retired or mistyped OPENAI_MODEL
        logger.error("AI: model not available (OPENAI_MODEL=%s)", model)
        return NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
    if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
        logger.error("AI: the OpenAI key was refused (%s)", name)
        return NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
    # BadRequestError, APIConnectionError, any other APIStatusError, and
    # anything else the SDK raises.
    return UpstreamError(UPSTREAM_MESSAGE, code="ai_upstream_error")


def _attempt(state: _State, messages, max_completion_tokens: int, json_mode: bool,
             timeout: float) -> str:
    settings = state.settings
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "messages": [dict(m) for m in messages],
        "max_completion_tokens": max_completion_tokens,
        "timeout": openai.Timeout(timeout, connect=min(CONNECT_TIMEOUT_SECONDS, timeout)),
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    if settings.temperature is not None:
        kwargs["temperature"] = settings.temperature
    if settings.reasoning_effort is not None:
        kwargs["reasoning_effort"] = settings.reasoning_effort
    started = state.clock()
    response = state.sdk_client.chat.completions.create(**kwargs)
    usage = getattr(response, "usage", None)
    logger.info("ai_call model=%s duration_ms=%d prompt_tokens=%s completion_tokens=%s outcome=ok",
                settings.model, round((state.clock() - started) * 1000),
                getattr(usage, "prompt_tokens", "-"), getattr(usage, "completion_tokens", "-"))
    return response.choices[0].message.content or ""


def _complete(state: _State, messages, max_completion_tokens: int, json_mode: bool,
              deadline: Optional[float]) -> str:
````

**In `backend/integrations/openai_client.py`, replace:**

````python
              deadline: Optional[float]) -> str:
    """Task 3 replaces this with the call, the error mapping, the retries and the deadline."""
    raise NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
````

**with:**

````python
              deadline: Optional[float]) -> str:
    settings = state.settings
    if settings.problem is not None:
        raise NotConfigured(NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
    remaining = _remaining(state, deadline)
    wait = (SEMAPHORE_WAIT_SECONDS if remaining is None
            else min(SEMAPHORE_WAIT_SECONDS, remaining - DEADLINE_MARGIN_SECONDS))
    acquired = (state.semaphore.acquire(timeout=wait) if wait > 0
                else state.semaphore.acquire(blocking=False))
    if not acquired:
        logger.warning("ai_call model=%s outcome=ai_busy (no free slot)", settings.model)
        raise Busy(BUSY_MESSAGE, code="ai_busy")
    try:
        retries = 0
        while True:
            remaining = _remaining(state, deadline)
            timeout = settings.timeout_seconds if remaining is None else min(settings.timeout_seconds, remaining)
            if timeout <= 0:
                raise UpstreamTimeout(TIMEOUT_MESSAGE, code="ai_timeout")
            try:
                return _attempt(state, messages, max_completion_tokens, json_mode, timeout)
            except openai.OpenAIError as exc:
                mapped_later = retries >= settings.max_retries or not _retryable(exc)
                backoff = 0.0 if mapped_later else _backoff(exc)
                remaining = _remaining(state, deadline)
                if not mapped_later and remaining is not None and remaining - backoff < MIN_RETRY_SECONDS:
                    mapped_later = True
                if mapped_later:
                    error = _mapped(exc, settings.model)
                    logger.warning("ai_call model=%s outcome=%s error=%s attempts=%d",
                                   settings.model, error.code, type(exc).__name__, retries + 1)
                    raise error from None
                logger.info("ai_call model=%s retry error=%s backoff_s=%.1f",
                            settings.model, type(exc).__name__, backoff)
                state.sleep(backoff)
                retries += 1
    finally:
        state.semaphore.release()
````

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_openai_client.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `23 passed in <t>s` (under 3 s: `test_a_real_semaphore_times_out_as_ai_busy` waits 0.05 s on a real semaphore, and nothing else waits); `1001 passed, 9 skipped in <t>s`; then ` M backend/integrations/openai_client.py` and ` M backend/tests/test_openai_client.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/integrations/openai_client.py backend/tests/test_openai_client.py
git commit -m "AI: complete() with its own capped retry, a deadline and F §2.8's error mapping (F §2.8; S Backend 3.7; AC5, AC6, AC18)" -m "One of OPENAI_MAX_CONCURRENCY slots per call (15 s, or remaining - 5 s,
then ai_busy); max_completion_tokens always, json_object in JSON mode,
temperature and reasoning_effort only when set; each attempt's timeout
min(30 s, remaining).
The SDK client has max_retries=0: complete() retries once on connection
errors, rate limits other than insufficient_quota and 5xx, after
min(Retry-After or 1 s, 2 s), only with 5 s left. APITimeoutError is
ai_timeout before its APIConnectionError base; insufficient_quota is
ai_not_configured with an ERROR line and no retry, as is a model OpenAI
does not offer (NotFoundError or model_not_found; owner answer A), whose
ERROR line names OPENAI_MODEL. No SDK text reaches a message. Tests build real SDK exceptions with the SDK's HTTP module.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Walk F §2.8's mapping table against `_mapped` in order (the ordering test pins `APITimeoutError`; the model-not-available row is clarification 26), and S 3.7's worst-case arithmetic against `_complete` (slot wait ≤ 15 s, attempt ≤ 30 s, backoff ≤ 2 s, second attempt only with ≥ 5 s left, all inside the caller's deadline). Push the backup.

Counts after Task 3: backend **1001 passed, 9 skipped**; frontend **356 in 55 files**.

### Task 4: The scripture reference parser (S Backend 2 "Parsing"; owner decision 9; owner answer Q4; AC3 parser half; clarifications 3, 4)

This task adds `parse_refs(text) -> ParsedRefs(spans, unparsed)` to `backend/scripture_refs.py`, the one parser for query references and hymns' `scripture_refs` fields: NFKC and dash normalization, the case-insensitive " or " split, segments on ";", newlines and a comma followed by a book, the longest book key (BOOKS plus `PARSE_ALIASES`), book carry-forward, the location list (`C`, `C-C`, `C:V`, `C:V-V`, `C:V-C:V`, verse letters a-d ignored, `f`/`ff` open-ended, bare numbers as verses after a verse item, single-chapter books), whole books, and `RefSpan`, `spans_overlap`, `same_chapter`. It is pure and `lru_cache`d on the raw string. The section sits after "Fetch only" and is Python only, so the shared fixture and the TypeScript port do not change (clarification 3). It also adds the sample file for S's 98 % test (owner answer Q4; clarification 4).

**Decisions recorded in this task:**
- **T4-1 (clarification 3).** `PARSE_ALIASES` holds the 30 `_BOOK_ABBREVS` variants `BOOKS` lacks (computed while planning with `normalize_book_text`); `_parse_index()` raises at import if one collides with a `BOOKS` key or names no book. `book_keys(name)` gives every key of a book, for Task 5's text fallback.
- **T4-2.** A segment is all or nothing: if any item of its location list does not read, the whole segment goes to `unparsed` (normalized text, original case). A range that runs backwards (`5-3`), chapter 0, a chapter above `MAX_CHAPTER` (150; the `ff` whole-book end excepted) and a period between digits (`John 3.16`, which would otherwise read as chapter 316) do not read (clarification 28).
- **T4-3.** A book carries forward only within one " or " alternative.
- **T4-4.** `split_segments(alternative)` is public, so the 98 % test counts segments the way the parser splits them.
- **T4-5 (owner answer Q4; clarification 4).** The sample is synthetic until the owner's export replaces it (Step 1 and Step 10).

**Files:**
- Modify: `backend/scripture_refs.py` (two imports; the parser section appended after `scripture_key`)
- Create: `backend/tests/hymn_fixtures/scripture_refs_sample.csv`, `backend/tests/hymn_fixtures/README.md`
- Test: `backend/tests/test_scripture_refs_parse.py` (new)

**Interfaces:**
- Consumes: `scripture_refs.BOOKS`, `Book`, `_ALIASES`, `normalize_book_text`, `split_alternatives`, `classify` (slice 2a).
- Produces (later users: Tasks 5, 11, 12):
  - `RefSpan(book: str, start: tuple[int, int], end: tuple[int, int])` (frozen; a whole chapter is verse 0..999, a whole book 1:0..999:999); `ParsedRefs(spans: tuple[RefSpan, ...], unparsed: tuple[str, ...])`.
  - `parse_refs(text: str) -> ParsedRefs` (`lru_cache(maxsize=4096)`); `split_segments(alternative: str) -> list[str]`; `spans_overlap(a, b) -> bool`; `same_chapter(a, b) -> bool`; `book_keys(book_name: str) -> tuple[str, ...]`.
  - `PARSE_ALIASES: dict[str, str]`, `SINGLE_CHAPTER_BOOKS: frozenset[str]`, `WHOLE_CHAPTER_START = 0`, `WHOLE_CHAPTER_END = 999`, `WHOLE_BOOK_END = 999`, `MAX_CHAPTER = 150`.

- [ ] **Step 1 (OWNER; the build does not wait, but marking the 3a PR ready does, owner answer D): Export a sample of real scripture references**

Ask the owner, in these words:

"To test the new scripture matcher against your real hymn data, could you run one read-only query and send me the result? It lists public hymn information only (hymnal, number, title and scripture references), no names or emails.
1. Open https://supabase.com/dashboard, choose the project `worship-staging`, then SQL Editor on the left.
2. Click New query, paste the text below, and click Run:

```sql
select hymnal, number, title, scripture_refs
from hymn_catalog
where coalesce(trim(scripture_refs), '') <> ''
order by md5(coalesce(title, '') || coalesce(number::text, ''))
limit 400;
```

3. Under the results, choose Export, then Download CSV. Please attach that file here (or paste its contents).
4. While you are there, please also run this second query and tell me the rows it shows (it only counts how dates are stored, for the pull request):

```sql
select length(coalesce(date_iso, '')) as len, count(*) from hymn_usage group by 1 order by 1;
```

Nothing is changed by either query. I will carry on with a made-up sample in the meantime."

The `order by md5(...)` spreads the 400 rows across the whole catalog instead of the first 400 numbers. Carry on with Step 2 whether or not the file has arrived; Step 10 swaps it in when it does. Record the second query's rows for the PR body (Task 16).

- [ ] **Step 2 (agent): Confirm Task 3's count and the fixture layout**

```bash
.venv/bin/python -m pytest -q | tail -1
ls backend/tests/fixtures
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); import scripture_refs as s; print(len(s.BOOKS), s.classify('Is 9:6'), s.split_book('Bar 5:5')[0].name)"
```

**Expected:** `1001 passed, 9 skipped in <t>s`; `README.md`, `bible_api`, `esv`, `lectio`, `shared`, `vanderbilt`, one per line (the recorder's folders: every file there needs a sidecar, which is why the sample goes to `backend/tests/hymn_fixtures/`); `84 unknown Baruch`.

- [ ] **Step 3 (agent): Write the sample and the failing tests**

**Create `backend/tests/hymn_fixtures/README.md`:**

````markdown
# Hymn test data

`scripture_refs_sample.csv` (columns `hymnal,number,title,scripture_refs`) feeds
`test_scripture_refs_parse.py::test_sample_parses_at_least_98_percent_of_segments`
(slice 3 spec, "Data and migrations"; AC3).

Status: SYNTHETIC. Written by hand for the slice 3a plan in Hymnary.org's shape
(link texts joined by "; "), because the repository holds no real
`scripture_refs` data. Replace it with the owner's read-only export of
`hymn_catalog` (slice 3a plan, Task 4 Step 1) and change this line to say
"EXPORTED on <date>". It is public hymn metadata with no personal data.
````

**Create `backend/tests/hymn_fixtures/scripture_refs_sample.csv`:**

````csv
hymnal,number,title,scripture_refs
SYNTHETIC,1,"Holy, Holy, Holy! Lord God Almighty",Isaiah 6:3; Revelation 4:8-11
SYNTHETIC,2,Praise to the Lord the Almighty,Psalm 103:1-6; Psalm 150
SYNTHETIC,3,All People That on Earth Do Dwell,Psalm 100
SYNTHETIC,4,O God Our Help in Ages Past,Psalm 90:1-5
SYNTHETIC,5,A Mighty Fortress Is Our God,Psalm 46
SYNTHETIC,6,The Lord's My Shepherd,Psalm 23
SYNTHETIC,7,Joyful Joyful We Adore Thee,Psalm 148; Luke 2:10-11
SYNTHETIC,8,Come Thou Long-Expected Jesus,Haggai 2:7; Isaiah 40:1-5
SYNTHETIC,9,O Come O Come Emmanuel,Isaiah 7:14; Matthew 1:23
SYNTHETIC,10,Hark the Herald Angels Sing,Luke 2:8-14
SYNTHETIC,11,Silent Night,Luke 2:1-20
SYNTHETIC,12,Joy to the World,Psalm 98:4-9
SYNTHETIC,13,O Little Town of Bethlehem,Micah 5:2; Matthew 2:1-6
SYNTHETIC,14,We Three Kings,Matthew 2:1-12
SYNTHETIC,15,Songs of Thankfulness and Praise,Matthew 3:13-17; John 2:1-11
SYNTHETIC,16,Beneath the Cross of Jesus,Galatians 6:14; Isaiah 32:2
SYNTHETIC,17,When I Survey the Wondrous Cross,Galatians 6:14; Philippians 3:7-8
SYNTHETIC,18,Were You There,John 19:16-42
SYNTHETIC,19,Christ the Lord Is Risen Today,Matthew 28:1-10; 1 Corinthians 15:55-57
SYNTHETIC,20,The Strife Is O'er,1 Corinthians 15:54-57
SYNTHETIC,21,Come Ye Faithful Raise the Strain,Exodus 15:1-21
SYNTHETIC,22,Crown Him with Many Crowns,Revelation 19:12
SYNTHETIC,23,Come Down O Love Divine,Romans 5:5
SYNTHETIC,24,Spirit of the Living God,Acts 2:1-4; Galatians 5:22-23
SYNTHETIC,25,Breathe on Me Breath of God,John 20:22; Ezekiel 37:1-14
SYNTHETIC,26,The Church's One Foundation,1 Corinthians 3:11; Ephesians 5:25-27
SYNTHETIC,27,Be Thou My Vision,Psalm 119:105
SYNTHETIC,28,Amazing Grace,Ephesians 2:8-9; 1 Chronicles 17:16-17
SYNTHETIC,29,Great Is Thy Faithfulness,Lamentations 3:22-23
SYNTHETIC,30,It Is Well with My Soul,Philippians 4:7; 2 Kings 4:26
SYNTHETIC,31,Guide Me O Thou Great Jehovah,Exodus 13:21-22; Psalm 78:24
SYNTHETIC,32,Lift High the Cross,1 Corinthians 1:18; John 12:32
SYNTHETIC,33,For All the Saints,Hebrews 12:1-2; Revelation 7:9-17
SYNTHETIC,34,The King of Love My Shepherd Is,Psalm 23; John 10:11
SYNTHETIC,35,Let All Mortal Flesh Keep Silence,Habakkuk 2:20
SYNTHETIC,36,Now Thank We All Our God,Sirach 50:22-24
SYNTHETIC,37,Here I Am Lord,Isaiah 6:8; 1 Samuel 3:1-10
SYNTHETIC,38,Lord of the Dance,John 1:14
SYNTHETIC,39,Morning Has Broken,Lamentations 3:22-23
SYNTHETIC,40,All Creatures of Our God and King,Psalm 148
SYNTHETIC,41,Take My Life and Let It Be,Romans 12:1-2
SYNTHETIC,42,My Hope Is Built on Nothing Less,Matthew 7:24-27; 1 Corinthians 3:11
SYNTHETIC,43,Blessed Assurance,Hebrews 10:22
SYNTHETIC,44,What a Friend We Have in Jesus,John 15:13-15; Philippians 4:6
SYNTHETIC,45,Rock of Ages,Exodus 33:22; Isaiah 26:4
SYNTHETIC,46,Abide with Me,Luke 24:29
SYNTHETIC,47,Of the Father's Love Begotten,Revelation 1:8; John 1:1-5
SYNTHETIC,48,Love Divine All Loves Excelling,1 John 4:7-21; 2 Corinthians 3:18
SYNTHETIC,49,O for a Thousand Tongues to Sing,Psalm 35:28; Acts 2:4
SYNTHETIC,50,Jesus Shall Reign,Psalm 72:8-19
SYNTHETIC,51,Lead On O King Eternal,Psalm 24:7-10
SYNTHETIC,52,O Jesus I Have Promised,Matthew 16:24; John 12:26
SYNTHETIC,53,The God of Abraham Praise,Exodus 3:6; Revelation 4:8
SYNTHETIC,54,Tell Out My Soul,Luke 1:46-55
SYNTHETIC,55,My Soul Gives Glory to My God,Luke 1:46b-55
SYNTHETIC,56,Canticle of the Turning,Luke 1:46-55; Isaiah 61:1-3
SYNTHETIC,57,By the Babylonian Rivers,Psalm 137:1-6
SYNTHETIC,58,Out of the Depths,Psalm 130
SYNTHETIC,59,Wake Awake for Night Is Flying,Matthew 25:1-13
SYNTHETIC,60,Lo He Comes with Clouds Descending,Revelation 1:7
SYNTHETIC,61,Arise Your Light Is Come,Isaiah 60:1-6
SYNTHETIC,62,Christ Is Made the Sure Foundation,Ephesians 2:20-22; 1 Peter 2:4-7
SYNTHETIC,63,Sing Praise to God Who Reigns Above,Deuteronomy 32:3-4
SYNTHETIC,64,Song of Hope,Romans 15:13
SYNTHETIC,65,God of Grace and God of Glory,Joshua 1:9; 2 Timothy 1:7
SYNTHETIC,66,We Are One in the Spirit,John 17:20-23; Ephesians 4:4-6
SYNTHETIC,67,Go Tell It on the Mountain,Luke 2:8-20; Isaiah 40:9
SYNTHETIC,68,Hosanna Loud Hosanna,Matthew 21:1-11; Mark 11:1-11; Luke 19:28-40
SYNTHETIC,69,Ah Holy Jesus,Isaiah 53:4-6
SYNTHETIC,70,O Sacred Head Now Wounded,Isaiah 53:3-6; Matthew 27:27-31
SYNTHETIC,71,Jesus Christ Is Risen Today,Mark 16:1-8
SYNTHETIC,72,Thine Is the Glory,1 Corinthians 15:55-57; John 20:1-18
SYNTHETIC,73,Alleluia Sing to Jesus,Revelation 5:9
SYNTHETIC,74,Hail Thee Festival Day,Acts 1:9-11
SYNTHETIC,75,Holy Spirit Truth Divine,John 16:13
SYNTHETIC,76,Come Holy Ghost Our Souls Inspire,Acts 2:1-21; Romans 8:26
SYNTHETIC,77,Glorious Things of Thee Are Spoken,Psalm 87:3; Isaiah 33:20-21
SYNTHETIC,78,This Is My Father's World,Psalm 24:1; Psalm 50:10-12
SYNTHETIC,79,We Gather Together,Psalm 106:47
SYNTHETIC,80,Come Ye Thankful People Come,Mark 4:26-29; Matthew 13:24-30
SYNTHETIC,81,Let Us Break Bread Together,Acts 2:42-47; 1 Corinthians 11:23-26
SYNTHETIC,82,Una Espiga,John 6:35; Matthew 26:26-29
SYNTHETIC,83,Baptized in Water,Romans 6:3-11; Galatians 3:27
SYNTHETIC,84,Wash O God Our Sons and Daughters,Titus 3:5
SYNTHETIC,85,Where Charity and Love Prevail,1 John 4:16; John 13:34-35
SYNTHETIC,86,Blest Be the Tie That Binds,Ephesians 4:1-3; Colossians 3:12-15
SYNTHETIC,87,The Lord Bless You and Keep You,Numbers 6:24-26
SYNTHETIC,88,Go My Children with My Blessing,Numbers 6:24-26; Matthew 28:20
SYNTHETIC,89,God Be with You Till We Meet Again,2 Corinthians 13:11-14
SYNTHETIC,90,Savior Again to Thy Dear Name,Luke 24:36
SYNTHETIC,91,In the Bleak Midwinter,Luke 2:7; Matthew 2:11
SYNTHETIC,92,Wisdom Freely Calling,Wisdom of Solomon 7:22-30; Proverbs 8
SYNTHETIC,93,Song of the Three Children,Song of the Three 35-65
SYNTHETIC,94,Traditional Doxology,Traditional
SYNTHETIC,95,Bless the Lord My Soul,Psalm 103:1-5
SYNTHETIC,96,Shall We Gather at the River,Revelation 22:1-5
SYNTHETIC,97,I Love to Tell the Story,Psalm 66:16; Mark 16:15
SYNTHETIC,98,Lord Speak to Me,Romans 14:7; Isaiah 50:4
SYNTHETIC,99,Here O My Lord I See Thee,1 Corinthians 13:12; Luke 22:14-20
SYNTHETIC,100,Christ Be Beside Me,Psalm 139:5-12; Matthew 28:20
````

**Create `backend/tests/test_scripture_refs_parse.py`:**

````python
"""scripture_refs.parse_refs and the span tests (slice 3 spec, Backend 2
"Parsing"; Testing `test_scripture_refs_parse.py`; owner decision 9; AC3).

Slice 2's shared fixture (test_scripture_refs.py) still pins BOOKS, split_book
and classify; parse_refs adds PARSE_ALIASES and SINGLE_CHAPTER_BOOKS on top.
"""
import csv
from pathlib import Path

import pytest

import scripture_refs as sr
from scripture_refs import RefSpan, parse_refs, same_chapter, spans_overlap

SAMPLE = Path(__file__).resolve().parent / "hymn_fixtures" / "scripture_refs_sample.csv"


def spans(text):
    """(book, start, end) for each span; asserts nothing was left unparsed."""
    parsed = parse_refs(text)
    assert parsed.unparsed == (), (text, parsed.unparsed)
    return [(s.book, s.start, s.end) for s in parsed.spans]


def test_every_alias_maps_to_its_book():
    for book in sr.BOOKS:
        for key in (sr.normalize_book_text(book.name), *book.aliases):
            assert parse_refs(f"{key} 1:1").spans[0].book == book.name, key
    for alias, name in sr.PARSE_ALIASES.items():
        assert parse_refs(f"{alias} 1:1").spans[0].book == name, alias
        assert alias in sr.book_keys(name)
    # The old matcher's abbreviations work in both directions (inventory D4).
    assert spans("Matt 17:1-8") == spans("Matthew 17:1-8")
    assert spans("Is 9:6") == [("Isaiah", (9, 6), (9, 6))]
    assert sr.classify("Is 9:6") == "unknown"                  # the shared fixture is unchanged


def test_ordinals_and_no_space_forms():
    expected = [("1 Corinthians", (13, 1), (13, 13))]
    for text in ("1 Cor 13:1-13", "I Cor. 13:1-13", "First Corinthians 13:1-13",
                 "1st Corinthians 13:1-13", "1Cor 13:1-13", "1cor13:1-13"):
        assert spans(text) == expected, text
    assert spans("II Kings 2:1-12") == [("2 Kings", (2, 1), (2, 12))]
    assert spans("3 Jn 2") == [("3 John", (1, 2), (1, 2))]


def test_psalm_forms():
    for text in ("Ps 99", "Pss 99", "Psalm 99", "Psalms 99", "Psa. 99"):
        assert spans(text) == [("Psalms", (99, 0), (99, 999))], text


def test_ranges_suffixes_and_ff():
    assert spans("Genesis 12:1-4a") == [("Genesis", (12, 1), (12, 4))]
    assert spans("Mark 1:9b-15") == [("Mark", (1, 9), (1, 15))]
    assert spans("John 1:1-2:3") == [("John", (1, 1), (2, 3))]
    assert spans("Isaiah 40-42") == [("Isaiah", (40, 0), (42, 999))]
    assert spans("Luke 4:14ff") == [("Luke", (4, 14), (4, 999))]
    assert spans("Luke 4:14f") == [("Luke", (4, 14), (4, 999))]
    assert spans("Matthew 5:3c") == [("Matthew", (5, 3), (5, 3))]


def test_semicolon_carry_forward_and_commas():
    assert spans("Isaiah 9:2-7; 11:1") == [("Isaiah", (9, 2), (9, 7)), ("Isaiah", (11, 1), (11, 1))]
    assert spans("Psalm 42; 43") == [("Psalms", (42, 0), (42, 999)), ("Psalms", (43, 0), (43, 999))]
    # A comma continues the location list unless a book follows it.
    assert spans("Romans 4:1-5, 13-17") == [("Romans", (4, 1), (4, 5)), ("Romans", (4, 13), (4, 17))]
    assert spans("Isaiah 6:1-8, Revelation 4:8") == [("Isaiah", (6, 1), (6, 8)),
                                                     ("Revelation", (4, 8), (4, 8))]
    assert spans("Psalm 23:1\nJohn 10:11") == [("Psalms", (23, 1), (23, 1)), ("John", (10, 11), (10, 11))]
    assert spans("John 1:1-2:3, 5") == [("John", (1, 1), (2, 3)), ("John", (2, 5), (2, 5))]


def test_single_chapter_books():
    assert spans("Jude 24-25") == [("Jude", (1, 24), (1, 25))]
    assert spans("Philemon 1:4-7") == [("Philemon", (1, 4), (1, 7))]
    assert spans("Obadiah 15") == [("Obadiah", (1, 15), (1, 15))]
    assert spans("2 John 4") == [("2 John", (1, 4), (1, 4))]


def test_en_dash_case_insensitive_or_and_whole_books():
    assert spans("Mark 1:9–15") == [("Mark", (1, 9), (1, 15))]
    assert spans("Mark 1:9—15") == [("Mark", (1, 9), (1, 15))]
    assert spans("Luke 24:13-35 OR Mark 16:1-8") == [("Luke", (24, 13), (24, 35)),
                                                     ("Mark", (16, 1), (16, 8))]
    assert spans("Ruth") == [("Ruth", (1, 0), (999, 999))]


def test_garbage_goes_to_unparsed():
    assert parse_refs("Transfiguration") == sr.ParsedRefs((), ("Transfiguration",))
    parsed = parse_refs("Psalm 23; see the preface; 5-3")
    assert [s.book for s in parsed.spans] == ["Psalms"]
    assert parsed.unparsed == ("see the preface", "5-3")          # a range that runs backwards
    assert parse_refs("  ") == sr.ParsedRefs((), ())
    assert parse_refs("Psalm 0").unparsed == ("Psalm 0",)


def test_impossible_chapters_and_dotted_verses_are_unparsed():
    # normalize_book_text drops periods, so "John 3.16" would read as John 316.
    for text in ("John 3.16", "Ps 1.1", "Ps 23. 1", "John 316", "Genesis 151", "Isaiah 40-160",
                 "John 3:16-200:1"):
        assert parse_refs(text) == sr.ParsedRefs((), (text,)), text
    assert spans("Psalm 150") == [("Psalms", (150, 0), (150, 999))]
    assert spans("Psalm 119:105") == [("Psalms", (119, 105), (119, 105))]
    assert spans("Psalm 148ff") == [("Psalms", (148, 0), (999, 999))]
    assert spans("I Cor. 13:1") == [("1 Corinthians", (13, 1), (13, 1))]
    # "Esd" alone could be 1 or 2 Esdras, so it names no book.
    assert parse_refs("Esd 1").unparsed == ("Esd 1",)
    assert spans("2 Esd 7:1") == [("2 Esdras", (7, 1), (7, 1))]


def test_deuterocanon_parses_and_classifies_as_ot():
    cases = {
        "Baruch 5:1-9": ("Baruch", (5, 1), (5, 9)),
        "Bar 5:5": ("Baruch", (5, 5), (5, 5)),
        "Wis 2:23": ("Wisdom of Solomon", (2, 23), (2, 23)),
        "Sirach 10:12-18": ("Sirach", (10, 12), (10, 18)),
        "Sir 27:4-7": ("Sirach", (27, 4), (27, 7)),
        "Ecclesiasticus 27:4": ("Sirach", (27, 4), (27, 4)),
        "Tobit 8:5-8": ("Tobit", (8, 5), (8, 8)),
        "Judith 9:11": ("Judith", (9, 11), (9, 11)),
        "1 Macc 2:1": ("1 Maccabees", (2, 1), (2, 1)),
        "2 Maccabees 7:1": ("2 Maccabees", (7, 1), (7, 1)),
        "Song of the Three 35-65": ("Song of the Three", (1, 35), (1, 65)),
    }
    for text, expected in cases.items():
        assert spans(text) == [expected], text
        assert sr.classify(text) == "ot", text
    assert spans("Wisdom of Solomon 1:13-15; 2:23-24") == [
        ("Wisdom of Solomon", (1, 13), (1, 15)), ("Wisdom of Solomon", (2, 23), (2, 24))]


def test_the_longest_alias_wins():
    assert spans("Song 2:8-13") == [("Song of Songs", (2, 8), (2, 13))]
    assert spans("Song of Solomon 2:10") == [("Song of Songs", (2, 10), (2, 10))]
    assert spans("Song of the Three Jews 35") == [("Song of the Three", (1, 35), (1, 35))]


def test_spans_overlap_and_same_chapter():
    def one(text):
        (span,) = parse_refs(text).spans
        return span

    assert spans_overlap(one("Matthew 17"), one("Matt 17:1-8"))
    assert spans_overlap(one("Genesis 12:1-4a"), one("Genesis 12:1"))
    assert not spans_overlap(one("Mark 1:9-15"), one("Mark 1:1-8"))
    assert same_chapter(one("Mark 1:9-15"), one("Mark 1:1-8"))
    assert not same_chapter(one("Mark 1:9-15"), one("Mark 10:45"))
    assert not same_chapter(one("Isaiah 9:6"), one("Genesis 9:6"))
    assert not same_chapter(one("Psalm 1"), one("Psalm 119"))
    assert not same_chapter(one("John 3:1-17"), one("1 John 3:16"))
    assert RefSpan("John", (3, 1), (3, 17)) == one("John 3:1-17")


def test_parse_refs_is_cached_on_the_raw_string():
    parse_refs.cache_clear()
    first = parse_refs("Psalm 23")
    assert parse_refs("Psalm 23") is first
    assert parse_refs.cache_info().hits == 1
    assert parse_refs.cache_info().maxsize == 4096


def test_sample_parses_at_least_98_percent_of_segments():
    """AC3 on the committed sample (backend/tests/hymn_fixtures/README.md says
    whether it is the owner's export or the synthetic stand-in)."""
    with SAMPLE.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 100
    assert set(rows[0]) == {"hymnal", "number", "title", "scripture_refs"}
    segments = unparsed = 0
    for row in rows:
        for alternative in sr.split_alternatives(row["scripture_refs"]):
            segments += len(sr.split_segments(alternative))
        unparsed += len(parse_refs(row["scripture_refs"]).unparsed)
    assert segments > 0
    assert (segments - unparsed) / segments >= 0.98, (segments, unparsed)
````

- [ ] **Step 4 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_scripture_refs_parse.py 2>&1 | tail -3
```

**Expected:**

```
ERROR backend/tests/test_scripture_refs_parse.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

(`ImportError: cannot import name 'RefSpan' from 'scripture_refs'`.)

- [ ] **Step 5 (agent): Write the parser**

**In `backend/scripture_refs.py`, replace:**

````python
import re
from dataclasses import dataclass
from typing import Literal, Optional
````

**with:**

````python
import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Optional
````

**Append to `backend/scripture_refs.py`:**

````python


# ---- Parsing for hymn matching (slice 3; Python only) ------------------------
#
# parse_refs reads a query reference or a hymn's scripture_refs field into
# book/chapter/verse spans (S Backend 2, owner decision 9). It reads the same
# BOOKS as classify, plus PARSE_ALIASES: the old matcher's abbreviations
# (worship_service._BOOK_ABBREVS) that BOOKS lacks. They live here, not in
# BOOKS, so the shared fixture and the TypeScript port stay unchanged (slice 3a
# plan, clarification 3); "is" (Isaiah) is one, which split_book and classify
# still do not accept.

PARSE_ALIASES: dict[str, str] = {
    "ge": "Genesis", "gn": "Genesis", "nm": "Numbers", "dt": "Deuteronomy",
    "jos": "Joshua", "est": "Esther", "prv": "Proverbs", "ecc": "Ecclesiastes",
    "sos": "Song of Songs", "is": "Isaiah", "jr": "Jeremiah", "ezk": "Ezekiel",
    "dnl": "Daniel", "ob": "Obadiah", "jon": "Jonah", "zep": "Zephaniah",
    "zec": "Zechariah", "mrk": "Mark", "luk": "Luke", "jhn": "John", "joh": "John",
    "1 thes": "1 Thessalonians", "2 thes": "2 Thessalonians", "phm": "Philemon",
    "jm": "James", "1 jhn": "1 John", "2 jhn": "2 John", "3 jhn": "3 John",
    "jud": "Jude", "rv": "Revelation",
}

# N and N-M are verses of chapter 1 in these books.
SINGLE_CHAPTER_BOOKS = frozenset({
    "Obadiah", "Philemon", "2 John", "3 John", "Jude", "Song of the Three",
    "Letter of Jeremiah", "Susanna", "Bel and the Dragon", "Prayer of Manasseh",
})

WHOLE_CHAPTER_START = 0     # verse 0: from the start of the chapter
WHOLE_CHAPTER_END = 999     # verse 999: to the end of the chapter
WHOLE_BOOK_END = 999        # chapter 999: to the end of the book
MAX_CHAPTER = 150           # no book has more chapters (Psalms); a larger one is unparsed

# A period between digits ("John 3.16"): normalize_book_text drops periods, so
# the segment would read as chapter 316 (or "Ps 1.1" as Psalm 11). Unparsed.
_DOTTED_VERSE = re.compile(r"\d\s*\.\s*\d")


def _parse_index() -> tuple[tuple[str, Book], ...]:
    by_name = {book.name: book for book in BOOKS}
    index = dict(_ALIASES)
    for alias, name in PARSE_ALIASES.items():
        if alias in index:
            raise ValueError(f"parse alias {alias!r} is already a BOOKS key")
        index[alias] = by_name[name]                 # KeyError: not a BOOKS name
    for name in SINGLE_CHAPTER_BOOKS:
        by_name[name]                                # KeyError: not a BOOKS name
    return tuple(sorted(index.items(), key=lambda kv: (-len(kv[0]), kv[0])))


_PARSE_INDEX = _parse_index()


def book_keys(book_name: str) -> tuple[str, ...]:
    """Every normalized key that names the book (BOOKS and PARSE_ALIASES), longest first."""
    return tuple(key for key, book in _PARSE_INDEX if book.name == book_name)


@dataclass(frozen=True)
class RefSpan:
    """One passage: canonical book, (chapter, verse) start and end, inclusive.
    A whole chapter runs from verse 0 to verse 999; a whole book from 1:0 to 999:999."""

    book: str
    start: tuple[int, int]
    end: tuple[int, int]


@dataclass(frozen=True)
class ParsedRefs:
    spans: tuple[RefSpan, ...]
    unparsed: tuple[str, ...]        # normalized text of segments that could not be read


def _match_book(segment: str) -> Optional[tuple[Book, str]]:
    """The longest book key at the start of the normalized segment, followed by
    the end, a space or a digit, and the rest (normalized, trimmed)."""
    text = normalize_book_text(segment)
    for key, book in _PARSE_INDEX:
        if text.startswith(key):
            after = text[len(key):]
            if after == "" or after[0] == " " or after[0] in "0123456789":
                return book, after.strip()
    return None


_ITEM = re.compile(
    r"(?P<a>\d+)[a-d]?"
    r"(?::(?P<b>\d+)[a-d]?)?"
    r"(?:(?P<ff>ff?)|-(?P<c>\d+)[a-d]?(?::(?P<d>\d+)[a-d]?)?)?"
)


def _item_span(book: Book, item: str, context: Optional[int]) -> Optional[tuple[RefSpan, Optional[int]]]:
    """One location item and the chapter a following bare number belongs to (or None)."""
    m = _ITEM.fullmatch(item.replace(" ", ""))
    if not m:
        return None
    a, b, c, d = (int(g) if g else None for g in m.group("a", "b", "c", "d"))
    ff = bool(m.group("ff"))
    if b is not None:                                       # C:V, C:V-V, C:V-C:V, C:Vff
        start = (a, b)
        if ff:
            end = (a, WHOLE_CHAPTER_END)
        elif c is None:
            end = (a, b)
        elif d is None:
            end = (a, c)
        else:
            end = (c, d)
    elif d is not None:                                     # C-C:V
        start, end = (a, WHOLE_CHAPTER_START), (c, d)
    elif book.name in SINGLE_CHAPTER_BOOKS or context is not None:   # verses
        chapter = 1 if book.name in SINGLE_CHAPTER_BOOKS else context
        start = (chapter, a)
        end = (chapter, WHOLE_CHAPTER_END if ff else (c if c is not None else a))
    else:                                                   # C, C-C, Cff
        start = (a, WHOLE_CHAPTER_START)
        end = (WHOLE_BOOK_END if ff else (c if c is not None else a), WHOLE_CHAPTER_END)
    last_chapter = start[0] if (ff and end[0] == WHOLE_BOOK_END) else end[0]
    if start[0] < 1 or start > end or max(start[0], last_chapter) > MAX_CHAPTER:
        return None
    has_verses = b is not None or d is not None or context is not None
    return RefSpan(book.name, start, end), (end[0] if has_verses else None)


def _segment_spans(book: Book, location: str) -> Optional[list[RefSpan]]:
    if not location:
        return [RefSpan(book.name, (1, WHOLE_CHAPTER_START), (WHOLE_BOOK_END, WHOLE_CHAPTER_END))]
    spans: list[RefSpan] = []
    context: Optional[int] = None
    for item in location.split(","):
        found = _item_span(book, item.strip(), context)
        if found is None:
            return None
        span, context = found
        spans.append(span)
    return spans


def split_segments(alternative: str) -> list[str]:
    """Split on ";" and newlines, and on "," when the text after it starts with a book."""
    out: list[str] = []
    for piece in re.split(r"[;\n]", alternative):
        piece = re.sub(r"\s+", " ", piece).strip()
        start = 0
        for m in re.finditer(",", piece):
            if _match_book(piece[m.end():]) is not None:
                out.append(piece[start:m.start()].strip())
                start = m.end()
        out.append(piece[start:].strip())
    return [s for s in out if s]


@lru_cache(maxsize=4096)
def parse_refs(text: str) -> ParsedRefs:
    """Every passage in `text` (S Backend 2 steps 1-7). Pure and cached on the raw string."""
    text = unicodedata.normalize("NFKC", text or "").replace("–", "-").replace("—", "-")
    spans: list[RefSpan] = []
    unparsed: list[str] = []
    for alternative in split_alternatives(text):
        book: Optional[Book] = None
        for segment in split_segments(alternative):
            if _DOTTED_VERSE.search(segment):
                unparsed.append(segment)
                continue
            hit = _match_book(segment)
            if hit is not None:
                book, location = hit
            elif book is not None:
                location = normalize_book_text(segment)
            else:
                unparsed.append(segment)
                continue
            found = _segment_spans(book, location)
            if found is None:
                unparsed.append(segment)
            else:
                spans.extend(found)
    return ParsedRefs(tuple(spans), tuple(unparsed))


def spans_overlap(a: RefSpan, b: RefSpan) -> bool:
    """Same book and the passages share at least one verse."""
    return a.book == b.book and a.start <= b.end and b.start <= a.end


def same_chapter(a: RefSpan, b: RefSpan) -> bool:
    """Same book and the chapter ranges intersect."""
    return a.book == b.book and a.start[0] <= b.end[0] and b.start[0] <= a.end[0]
````

- [ ] **Step 6 (agent): Run the tests, slice 2's shared fixture tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_scripture_refs_parse.py backend/tests/test_scripture_refs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `29 passed in <t>s` (14 new, and slice 2's 15 unchanged: `BOOKS` and the fixture did not move); `1015 passed, 9 skipped in <t>s`; then ` M backend/scripture_refs.py`, `?? backend/tests/hymn_fixtures/`, `?? backend/tests/test_scripture_refs_parse.py`.

- [ ] **Step 7 (agent): Measure the sample's parse rate**

```bash
.venv/bin/python -c "
import csv, sys; sys.path.insert(0, 'backend')
import scripture_refs as s
rows = list(csv.DictReader(open('backend/tests/hymn_fixtures/scripture_refs_sample.csv', newline='')))
seg = sum(len(s.split_segments(a)) for r in rows for a in s.split_alternatives(r['scripture_refs']))
bad = [u for r in rows for u in s.parse_refs(r['scripture_refs']).unparsed]
print(len(rows), seg, len(bad), round(1 - len(bad) / seg, 4), bad[:10])"
```

**Expected** on the synthetic sample: `100 153 1 0.9935 ['Traditional']`.

- [ ] **Step 8 (agent): Commit**

```bash
git add backend/scripture_refs.py backend/tests/hymn_fixtures/scripture_refs_sample.csv \
        backend/tests/hymn_fixtures/README.md backend/tests/test_scripture_refs_parse.py
git commit -m "Scripture: parse references into book, chapter and verse spans (S Backend 2; decision 9; AC3)" -m "parse_refs reads query references and hymns' scripture_refs alike: NFKC,
dashes, the case-insensitive ' or ' split, segments on ';', newlines and a
comma before a book, the longest book key with carry-forward, chapter and
verse lists with a-d suffixes, f/ff, single-chapter books and whole books.
It reads BOOKS plus PARSE_ALIASES, the old matcher's 30 missing
abbreviations kept beside BOOKS so the shared fixture and the TypeScript
port do not change (clarification 3). The 98 % sample is synthetic until
the owner's export replaces it (owner answer Q4; clarification 4).

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 9 (controller): Review checkpoint and backup push**

Check every row of S's "Required results" parser inputs appears in the tests, that `BOOKS` and `backend/tests/fixtures/shared/scripture_refs.json` have no diff (`git diff HEAD~1 --stat` lists 4 files), and that the README says SYNTHETIC. Push the backup.

- [ ] **Step 10 (agent, when the owner's export arrives, at any later point, and at the latest in Task 16 Step 11 before the PR is marked ready): Swap in the real sample**

Save the owner's CSV over `backend/tests/hymn_fixtures/scripture_refs_sample.csv`. Keep only the four columns in the order `hymnal,number,title,scripture_refs`, with the header row; if the export has fewer than 100 rows, keep them all and change the `len(rows) >= 100` assertion to the real count in the same commit. In `backend/tests/hymn_fixtures/README.md`, replace the paragraph beginning "Status: SYNTHETIC." with "Status: EXPORTED on <date> from production `hymn_catalog` by the owner (read-only query in the slice 3a plan, Task 4 Step 1). Public hymn metadata only." Then run Step 7's command and `.venv/bin/python -m pytest -q backend/tests/test_scripture_refs_parse.py 2>&1 | tail -1`.
- If the rate is at least 0.98 and `14 passed`: commit both files with `git commit -m "Tests: the owner's scripture_refs export replaces the synthetic sample (S Data and migrations; AC3; owner answer Q4)"` plus the two trailer lines, and push the backup. Record the rate and the ten most common unparsed shapes for the PR body.
- If the rate is below 0.98: do not commit and do not change the parser. Report the unparsed list to the controller, who decides with the owner whether to extend `PARSE_ALIASES` or the location grammar (a new clarification) before the PR.

Counts after Task 4: backend **1015 passed, 9 skipped**; frontend **356 in 55 files**.

### Task 5: `hymn_search`: the matcher, the title key, themes and the even sample; the characterization test (S Backend 1 row 4, Backend 2 "Matching" and "Required results", Testing "Characterization first", `test_hymn_search.py`; owner answer Q2; decision 9; AC3; clarifications 1, 16)

This task adds the pure module `backend/hymn_search.py`: `normalize_title` and `usage_key` (the normalized title alone, owner answer Q2), `parse_themes` (None, lists, comma or semicolon strings and Postgres array literals such as `{A,"B c"}`), `evenly_spaced`, and `match_hymns(pool, refs, *, limit_per_ref=50, max_results=20) -> MatchResult`. A hymn matches a query ref at "passage" strength when some spans overlap in the same book and at "chapter" strength when only the chapter ranges meet; hymn segments the parser could not read fall back to a boundary-aware text test that gives at most "chapter" and never lets "Psalm 1" hit "Psalm 119" or "John 3" hit "1 John 3". Characterization comes first (F §2.3.1): `test_hymn_match_parity.py` runs the pairs that match today through the old `worship_service.hymns_by_scripture` and the new matcher, and asserts that the four verified over-matches match the old one and not the new. Task 14 deletes the old function and that half.

**Decisions recorded in this task:**
- **T5-1 (clarification 16).** The per-ref cap counts after sorting by tier, first matching ref and pool order; `total_matched` is counted after the cap and before `max_results`.
- **T5-2.** A query ref with no readable span goes to `unparsed_refs` and matches nothing. A hymn with a blank title or blank `scripture_refs` is skipped.
- **T5-3.** `parse_themes` drops repeats case-insensitively, keeping the first spelling.

**Files:**
- Create: `backend/hymn_search.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py` (import list)
- Test: `backend/tests/test_hymn_search.py`, `backend/tests/test_hymn_match_parity.py` (new)

**Interfaces:**
- Consumes: Task 4's `parse_refs`, `RefSpan`, `ParsedRefs`, `spans_overlap`, `same_chapter`, `book_keys`, `normalize_book_text`; `worship_service.hymns_by_scripture(db, ref, limit=50, all_hymns=[...])` (the parity test only).
- Produces (later users: Tasks 7, 9, 10, 11, 12, 13):
  - `normalize_title(title) -> str`; `usage_key(title) -> str`; `parse_themes(theme) -> list[str]`; `evenly_spaced(items, k) -> list` (`items[floor(i * n / k)]`).
  - `HymnMatch(record, strength: "passage" | "chapter", matched_refs: tuple[str, ...])`; `MatchResult(items: tuple[HymnMatch, ...], total_matched: int, refs_used: tuple[str, ...], unparsed_refs: tuple[str, ...])`.
  - `match_hymns(pool, refs, *, limit_per_ref=50, max_results=20) -> MatchResult`, where `pool` holds records with `title` and `scripture_refs` in hymnal order and `refs` are already trimmed and split on " or ".

- [ ] **Step 1 (agent): Confirm Task 4's hand-off**

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); import scripture_refs as s; print(s.parse_refs('Matt 17:1-8').spans[0], s.book_keys('John'))"
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `RefSpan(book='Matthew', start=(17, 1), end=(17, 8)) ('john', 'jhn', 'joh', 'jn')`; `1015 passed, 9 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `backend/tests/test_hymn_match_parity.py`:**

````python
"""Characterization of the scripture matcher (F §2.3.1; slice 3 spec, Testing
"Characterization first"): what matches today must still match, and the four
verified over-matches (inventory §0 item 5) must stop matching.

The old half calls worship_service.hymns_by_scripture with the in-memory pool;
Task 14 deletes that function and this file's old half in the same commit.
"""
from dataclasses import dataclass

import worship_service
from hymn_search import match_hymns

# (query, hymn scripture_refs) pairs that match under the old substring matcher.
STILL_MATCH = [
    ("Isaiah 6:1-8", "Isaiah 6:1-8"),             # the exact reference
    ("Matthew 17:1-9", "Matthew 17"),             # book + chapter
    ("Romans 8:28-39", "Romans 8:28"),            # the first verse
    ("Genesis 12:1-4a", "Genesis 12:1-4"),        # an a/b suffix dropped
    ("Luke 24:13-35 or Mark 16:1-8", "Mark 16:1-8"),   # the " or " alternative
    ("Psalm 23", "Psalm 23"),
]

# Verified over-matches: the old matcher says yes, the new one no.
OVER_MATCHES = [
    ("Isaiah 9:6", "Genesis 9:6"),
    ("Mark 1:9-15", "Mark 10:45"),
    ("Psalm 1", "Psalm 119"),
    ("John 3:1-17", "1 John 3:16"),
]


@dataclass(frozen=True)
class H:
    title: str
    scripture_refs: str


def _old(query: str, refs: str) -> bool:
    hymn = {"id": "h1", "Hymn Title": "Hymn", "Scripture References": refs}
    return bool(worship_service.hymns_by_scripture(None, query, all_hymns=[hymn]))


def _new(query: str, refs: str) -> bool:
    queries = [part.strip() for part in query.split(" or ")]
    return bool(match_hymns([H("Hymn", refs)], queries).items)


def test_pairs_that_match_today_still_match():
    for query, refs in STILL_MATCH:
        assert _old(query, refs), ("old", query, refs)
        assert _new(query, refs), ("new", query, refs)


def test_the_four_over_matches_no_longer_match():
    for query, refs in OVER_MATCHES:
        assert _old(query, refs), ("old", query, refs)          # the bug, as it is today
        assert not _new(query, refs), ("new", query, refs)
````

**Create `backend/tests/test_hymn_search.py`:**

````python
"""hymn_search: the scripture matcher and its helpers (slice 3 spec, Backend 2
"Matching" and "Required results"; Testing `test_hymn_search.py`; owner
decision 9; owner answer Q2: the recent-use key is the title alone; AC3)."""
from dataclasses import dataclass

from hymn_search import evenly_spaced, match_hymns, normalize_title, parse_themes, usage_key


@dataclass(frozen=True)
class H:
    title: str
    scripture_refs: str | None
    id: str = ""


def pool(*refs):
    return [H(title=f"Hymn {i}", scripture_refs=r, id=f"h{i}") for i, r in enumerate(refs)]


def strengths(result):
    return [(m.record.id, m.strength) for m in result.items]


# The spec's required-results table (S Backend 2); the first four are the
# verified over-matches of inventory §0 item 5.
REQUIRED = [
    ("Isaiah 9:6", "Genesis 9:6", None),
    ("Mark 1:9-15", "Mark 10:45", None),
    ("Psalm 1", "Psalm 119", None),
    ("John 3:1-17", "1 John 3:16", None),
    ("Matthew 17", "Matt 17:1-8", "passage"),
    ("Psalm 99", "Psalms 99", "passage"),
    ("Genesis 12:1-4a", "Genesis 12:1", "passage"),
    ("Mark 1:9-15", "Mark 1:1-8", "chapter"),
    ("Isaiah 9:2-7; 11:1", "Isaiah 11:1-9", "passage"),
    ("Luke 24:13-35 or Mark 16:1-8", "Mark 16:6", "passage"),
    ("Jude 24-25", "Jude 24", "passage"),
    ("Baruch 5:1-9", "Bar 5:5", "passage"),
    ("Wisdom of Solomon 1:13-15; 2:23-24", "Wis 2:23", "passage"),
    ("Sirach 27:4-7", "Ecclesiasticus 27:4", "passage"),
    ("Song of Solomon 2:8-13", "Song 2:10", "passage"),
    ("Transfiguration", "Matthew 17:1-9", None),
]


def test_required_results_table():
    for query, hymn_refs, expected in REQUIRED:
        result = match_hymns(pool(hymn_refs), [query])
        got = result.items[0].strength if result.items else None
        assert got == expected, (query, hymn_refs, got)
    assert match_hymns(pool("Matthew 17"), ["Transfiguration"]).unparsed_refs == ("Transfiguration",)
    assert match_hymns(pool("Bar 5:5"), ["Baruch 5:1-9"]).unparsed_refs == ()


def test_passage_tier_first_then_first_ref_then_pool_order():
    hymns = pool("Mark 1:1-8",          # h0: chapter for ref 0
                  "Psalm 23",           # h1: passage for ref 1
                  "Mark 1:12",          # h2: passage for ref 0
                  "Psalm 23:4; Mark 1:10")   # h3: passage for both
    result = match_hymns(hymns, ["Mark 1:9-15", "Psalm 23:1-6"])
    assert strengths(result) == [("h2", "passage"), ("h3", "passage"), ("h1", "passage"),
                                 ("h0", "chapter")]


def test_limit_per_ref_max_results_and_total():
    hymns = pool(*["John 3:16"] * 5, *["Psalm 23"] * 5)
    result = match_hymns(hymns, ["John 3", "Psalm 23"], limit_per_ref=3, max_results=4)
    assert result.total_matched == 6                      # 3 per ref, before max_results
    assert [m.record.id for m in result.items] == ["h0", "h1", "h2", "h5"]


def test_a_hymn_counts_once_and_lists_every_matching_ref():
    result = match_hymns(pool("John 3:16; Psalm 23:1"), ["Psalm 23", "John 3:1-17", "Mark 1"])
    (match,) = result.items
    assert match.matched_refs == ("Psalm 23", "John 3:1-17")
    assert result.total_matched == 1
    assert result.refs_used == ("Psalm 23", "John 3:1-17", "Mark 1")


def test_unparsed_hymn_text_falls_back_on_word_boundaries():
    hymns = pool("Psalm 1 (paraphrase)", "Psalm 119 (paraphrase)", "1 John 3 (echo)",
                 "John 3 (echo)")
    assert strengths(match_hymns(hymns, ["Psalm 1"])) == [("h0", "chapter")]
    assert strengths(match_hymns(hymns, ["John 3:16"])) == [("h3", "chapter")]
    # The fallback never yields more than "chapter".
    assert strengths(match_hymns(pool("Psalm 23 (metrical)"), ["Psalm 23:1"])) == [("h0", "chapter")]


def test_blank_titles_and_blank_refs_are_skipped():
    hymns = [H("", "John 3:16", "blank-title"), H("  ", "John 3:16", "space-title"),
             H("Ok", None, "no-refs"), H("Ok", "   ", "blank-refs"), H("Kept", "John 3:16", "kept")]
    assert [m.record.id for m in match_hymns(hymns, ["John 3"]).items] == ["kept"]
    assert match_hymns(hymns, []).items == ()


def test_parse_themes():
    assert parse_themes(None) == []
    assert parse_themes(["Praise", " grace ", "", None, "praise"]) == ["Praise", "grace"]
    assert parse_themes('{Praise,"Call to Worship","Joy, Hope"}') == [
        "Praise", "Call to Worship", "Joy, Hope"]
    assert parse_themes("praise, grace; joy") == ["praise", "grace", "joy"]
    assert parse_themes("  ") == []


def test_normalize_title_and_usage_key_is_the_title_alone():
    assert normalize_title("  Holy,  Holy,\tHoly ") == "holy, holy, holy"
    assert normalize_title(None) == ""
    assert normalize_title("ＡＢＣ") == "abc"                       # NFKC
    # Owner answer Q2 (2026-09-29): the same title matches across numbers and hymnals.
    assert usage_key("Amazing Grace") == usage_key(" amazing  grace ")


def test_evenly_spaced_is_deterministic_and_in_range():
    items = list(range(120))
    sample = evenly_spaced(items, 50)
    assert sample == evenly_spaced(items, 50)
    assert len(sample) == 50 and len(set(sample)) == 50
    assert sample[0] == 0 and sample[-1] >= 80                       # reaches the last third
    assert sample == [items[(i * 120) // 50] for i in range(50)]
    assert evenly_spaced(items[:3], 40) == [0, 1, 2]
    assert evenly_spaced(items, 0) == []
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
````

**with:**

````python
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_search.py backend/tests/test_hymn_match_parity.py 2>&1 | tail -4
```

**Expected:**

```
ERROR backend/tests/test_hymn_match_parity.py
ERROR backend/tests/test_hymn_search.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
2 errors in <t>s
```

(`ModuleNotFoundError: No module named 'hymn_search'`, twice.)

- [ ] **Step 4 (agent): Write `hymn_search.py`**

**Create `backend/hymn_search.py`:**

````python
"""Pure hymn helpers for slice 3 (S Backend 1 and 2; owner decision 9; owner
answer Q2 of 2026-09-29):

- normalize_title and usage_key: the recent-use key is the normalized title
  alone, so a hymn sung from one hymnal is recognized when it is picked from
  another under a different number (owner answer Q2).
- parse_themes: a hymn's theme field (None, a list, "A, B", "A; B" or a
  Postgres array literal '{A,"B c"}') as a clean list.
- match_hymns: scripture matching on parsed book/chapter/verse spans, in two
  tiers, "passage" and "chapter".
- evenly_spaced: a deterministic even sample.

No I/O, no FastAPI, no Streamlit. Records are anything with `title` and
`scripture_refs` attributes (repos.hymns.HymnRecord).
"""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal, Optional, Sequence

import scripture_refs
from scripture_refs import RefSpan, parse_refs, same_chapter, spans_overlap

Strength = Literal["passage", "chapter"]
_TIER = {"passage": 0, "chapter": 1}


def normalize_title(title: Optional[str]) -> str:
    """NFKC, whitespace collapsed, stripped and casefolded."""
    text = unicodedata.normalize("NFKC", title or "")
    return re.sub(r"\s+", " ", text).strip().casefold()


def usage_key(title: Optional[str]) -> str:
    """The recent-use key: the normalized title alone (owner answer Q2)."""
    return normalize_title(title)


def _split_array_literal(body: str) -> list[str]:
    """The items of a Postgres array literal body: commas split, double quotes group."""
    items, current, quoted, escaped = [], [], False, False
    for ch in body:
        if escaped:
            current.append(ch)
            escaped = False
        elif ch == "\\" and quoted:
            escaped = True
        elif ch == '"':
            quoted = not quoted
        elif ch == "," and not quoted:
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    return items


def parse_themes(theme: Any) -> list[str]:
    """Clean theme strings in first-seen order, blanks and repeats dropped."""
    if theme is None:
        raw: list[str] = []
    elif isinstance(theme, (list, tuple)):
        raw = [str(t) for t in theme if t is not None]
    else:
        text = str(theme).strip()
        if text.startswith("{") and text.endswith("}"):
            raw = _split_array_literal(text[1:-1])
        else:
            raw = re.split(r"[,;]", text)
    out: list[str] = []
    for item in raw:
        cleaned = re.sub(r"\s+", " ", item).strip().strip('"').strip()
        if cleaned and cleaned.casefold() not in {o.casefold() for o in out}:
            out.append(cleaned)
    return out


def evenly_spaced(items: Sequence[Any], k: int) -> list[Any]:
    """items[floor(i * len / k)] for i in 0..k-1; the whole list when k >= len."""
    n = len(items)
    if k >= n:
        return list(items)
    if k <= 0:
        return []
    return [items[math.floor(i * n / k)] for i in range(k)]


@dataclass(frozen=True)
class HymnMatch:
    record: Any
    strength: Strength
    matched_refs: tuple[str, ...]


@dataclass(frozen=True)
class MatchResult:
    items: tuple[HymnMatch, ...]
    total_matched: int
    refs_used: tuple[str, ...]
    unparsed_refs: tuple[str, ...]


def _text_fallback(query: RefSpan, hymn_text: str) -> bool:
    """A boundary-aware test on a hymn segment the parser could not read: the
    query's book (any key) and first chapter, never inside a longer number or
    after "1 " (so "Psalm 1" never hits "Psalm 119", "John 3" never "1 John 3")."""
    text = scripture_refs.normalize_book_text(hymn_text)
    chapter = str(query.start[0])
    for key in scripture_refs.book_keys(query.book):
        pattern = r"(?<![0-9a-z])(?<!\d )" + re.escape(key) + r"\s*" + chapter + r"(?![0-9])"
        if re.search(pattern, text):
            return True
    return False


def _strength(query: tuple[RefSpan, ...], hymn: scripture_refs.ParsedRefs) -> Optional[Strength]:
    if any(spans_overlap(q, h) for q in query for h in hymn.spans):
        return "passage"
    if any(same_chapter(q, h) for q in query for h in hymn.spans):
        return "chapter"
    if any(_text_fallback(q, text) for q in query for text in hymn.unparsed):
        return "chapter"
    return None


def match_hymns(pool: Sequence[Any], refs: Sequence[str], *, limit_per_ref: int = 50,
                max_results: int = 20) -> MatchResult:
    """Hymns in `pool` whose scripture_refs match any of `refs` (already trimmed
    and split on " or "). Passage tier first, then chapter; within a tier by
    the first matching ref, then pool order. `limit_per_ref` caps the hymns
    attributed to each ref (a hymn counts once, at its first ref);
    `total_matched` is counted after that cap and before `max_results`."""
    queries: list[tuple[str, tuple[RefSpan, ...]]] = []
    unparsed: list[str] = []
    for ref in refs:
        parsed = parse_refs(ref)
        if parsed.spans:
            queries.append((ref, parsed.spans))
        else:
            unparsed.append(ref)
    found = []
    for position, hymn in enumerate(pool):
        title = (getattr(hymn, "title", None) or "").strip()
        text = (getattr(hymn, "scripture_refs", None) or "").strip()
        if not title or not text or not queries:
            continue
        parsed = parse_refs(text)
        best: Optional[Strength] = None
        first: Optional[int] = None
        matched: list[str] = []
        for index, (ref, spans) in enumerate(queries):
            strength = _strength(spans, parsed)
            if strength is None:
                continue
            matched.append(ref)
            first = index if first is None else first
            if best is None or _TIER[strength] < _TIER[best]:
                best = strength
        if best is not None:
            found.append((_TIER[best], first, position, HymnMatch(hymn, best, tuple(matched))))
    found.sort(key=lambda row: row[:3])
    per_ref: dict[int, int] = {}
    kept: list[HymnMatch] = []
    for _tier, first, _position, match in found:
        if per_ref.get(first, 0) >= limit_per_ref:
            continue
        per_ref[first] = per_ref.get(first, 0) + 1
        kept.append(match)
    return MatchResult(items=tuple(kept[:max_results]), total_matched=len(kept),
                       refs_used=tuple(refs), unparsed_refs=tuple(unparsed))
````

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_search.py backend/tests/test_hymn_match_parity.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `14 passed in <t>s` (9 + 2 new; 3 import-guard tests); `1026 passed, 9 skipped in <t>s`; then `?? backend/hymn_search.py`, `?? backend/tests/test_hymn_match_parity.py`, `?? backend/tests/test_hymn_search.py`, ` M backend/tests/test_no_streamlit_in_core.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/hymn_search.py backend/tests/test_hymn_search.py backend/tests/test_hymn_match_parity.py \
        backend/tests/test_no_streamlit_in_core.py
git commit -m "Hymns: the tiered scripture matcher, the title-only usage key, themes and even samples (S Backend 2; decision 9; owner answer Q2; AC3)" -m "match_hymns compares parsed spans: passage when they overlap in the same
book, chapter when only the chapters meet, and a word-boundary text test
(at most chapter) for hymn segments the parser cannot read. Passage tier
first, then by first matching ref and hymnal order; limit_per_ref counts
after that order (clarification 16). The four verified over-matches no
longer match; test_hymn_match_parity.py runs today's matching pairs through
the old hymns_by_scripture too (F §2.3.1). usage_key is the normalized title
alone (owner answer Q2, clarification 1).

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Compare `REQUIRED` in `test_hymn_search.py` with S's "Required results" table row by row (16 rows), and check that `hymn_search.py` imports only `scripture_refs` and the standard library. Push the backup.

Counts after Task 5: backend **1026 passed, 9 skipped**; frontend **356 in 55 files**.

### Task 6: Typed hymn reads, the ranking accessors and the rubric in the caller's session (S Backend 1 rows `repos/hymns.py`, `hymn_ranking.py`, `repos/churches.py` and their 2026-09-26 amendments; F §1.4, §2.2 rule 3 and item 5; AC19 half; clarification 23)

This task adds what the usecases read. `repos/hymns.py` gains `HymnRecord` (the columns a hymn DTO needs, including `text_year` and `hymnal_count`), `HymnalSummary`, `hymnal_summaries` (codes with hymn and scripture-reference counts), `query_hymns` (S's ordering, `q` rule with `autoescape`, and total) and `list_hymnal_records` (one hymnal in hymnal order). Each runs in the caller's session or its own and coerces the id with `db.ids.as_uuid`. `hymn_ranking.rank_candidates`, `shortlist` and `facts_note` gain keyword-only `year_of` and `count_of` accessors whose defaults read the flat dicts, so PR #4's tests pass unchanged, plus `is_newer_than_preferred` (PR #4's `hymn_display_info` rule, moved before T14 deletes that function). `repos.churches.get_church_rubric_overrides` takes `session=None`.

**Decisions recorded in this task:**
- **T6-1 (clarification 23).** `HymnalSummary` and the blank-code rule; titles order by `lower(coalesce(title, ''))`.
- **T6-2.** `q` of 1-6 digits matches `number = int(q)` or the title; 7 or more digits use the title only, so a 30-digit `q` never binds an integer that overflows SQLite (S API notes).
- **T6-3.** `is_newer_than_preferred(year, None)` is False (no preference, no flag), as `hymn_display_info` without `prefer_before_year` was.

**Files:**
- Modify: `backend/repos/hymns.py` (imports; the slice 3a section appended)
- Modify: `backend/hymn_ranking.py` (whole file shown)
- Modify: `backend/repos/churches.py` (`get_church_rubric_overrides`)
- Test: `backend/tests/test_hymns_repo.py` (imports; 6 tests appended), `backend/tests/test_hymn_ranking.py` (imports; 2 tests appended), `backend/tests/test_churches_repo.py` (1 test appended)

**Interfaces:**
- Consumes: `db.session_scope`, `db.ids.as_uuid` (a malformed id is `NotFound`), `db.models.Hymn`; `repos.churches.get_church(church_id, *, session=None)`; `hymn_utils.get_property_value`.
- Produces (later users: Tasks 7-13):
  - `repos.hymns.HymnRecord(id: UUID, hymnal: str, title: str | None, number: int | None, link: str | None, scripture_refs: str | None, theme: str | None, text_year: int | None, hymnal_count: int | None)` (frozen).
  - `repos.hymns.HymnalSummary(code: str, hymn_count: int, scripture_ref_count: int)`.
  - `hymnal_summaries(church_id, *, session=None) -> list[HymnalSummary]` (ORDER BY code); `query_hymns(church_id, *, hymnal=None, q=None, limit=50, offset=0, session=None) -> tuple[list[HymnRecord], int]`; `list_hymnal_records(church_id, hymnal, *, session=None) -> list[HymnRecord]`.
  - `hymn_ranking.rank_candidates(hymns, *, prefer_before_year, prefer_familiar, year_of=..., count_of=...)`, `shortlist(ranked, *, limit, prefer_before_year, reserve, year_of=...)`, `facts_note(hymn, *, year_of=..., count_of=...)`, `is_newer_than_preferred(year, prefer_before_year) -> bool`.
  - `repos.churches.get_church_rubric_overrides(church_id, *, session=None) -> dict`.

- [ ] **Step 1 (agent): Confirm Task 5's count**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q backend/tests/test_hymn_ranking.py backend/tests/test_hymns_repo.py backend/tests/test_churches_repo.py 2>&1 | tail -1
```

**Expected:** `1026 passed, 9 skipped in <t>s`; `25 passed in <t>s` (9 + 8 + 8 before this task).

- [ ] **Step 2 (agent): Write the failing tests**

**Append to `backend/tests/test_churches_repo.py`:**

````python


def test_rubric_overrides_read_in_the_callers_session(tmp_db, make_user):
    """Slice 3 reads the rubric in the same session as the hymns (F §2.2 rule 3)."""
    from repos.churches import get_church_rubric_overrides, update_church_rubric

    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=make_user())
    update_church_rubric(cid, {"prefer_before_year": 1900})
    with session_scope() as s:
        assert get_church_rubric_overrides(cid, session=s) == {"prefer_before_year": 1900}
    assert get_church_rubric_overrides(cid) == {"prefer_before_year": 1900}
    assert get_church_rubric_overrides(uuid.uuid4()) == {}
````

**In `backend/tests/test_hymn_ranking.py`, replace:**

````python
from hymn_ranking import facts_note, rank_candidates, shortlist


def h(name, year=None, count=None):
````

**with:**

````python
from dataclasses import dataclass

from hymn_ranking import facts_note, is_newer_than_preferred, rank_candidates, shortlist


def h(name, year=None, count=None):
````

**Append to `backend/tests/test_hymn_ranking.py`:**

````python


# --- slice 3a: accessors for typed records, and the newer-than-preferred rule ---

@dataclass(frozen=True)
class Rec:
    name: str
    text_year: int | None = None
    hymnal_count: int | None = None


def test_accessors_over_records_give_the_same_order_as_flat_dicts():
    rows = [("Newer", 1995, 40), ("Unknown", None, None), ("Old rare", 1850, 5),
            ("Old common", 1840, 900), ("Unknown common", None, 3000)]
    flat = [h(n, y, c) for n, y, c in rows]
    records = [Rec(n, y, c) for n, y, c in rows]
    year_of, count_of = (lambda r: r.text_year), (lambda r: r.hymnal_count)
    for familiar in (True, False):
        want = titles(rank_candidates(flat, prefer_before_year=1970, prefer_familiar=familiar))
        got = rank_candidates(records, prefer_before_year=1970, prefer_familiar=familiar,
                              year_of=year_of, count_of=count_of)
        assert [r.name for r in got] == want
    ranked = rank_candidates(records, prefer_before_year=1970, prefer_familiar=True,
                             year_of=year_of, count_of=count_of)
    assert [r.name for r in shortlist(ranked, limit=3, prefer_before_year=1970, reserve=1,
                                      year_of=year_of)] == ["Old common", "Old rare", "Unknown common"]
    assert facts_note(Rec("x", 1826, 1322), year_of=year_of, count_of=count_of) == (
        "(written 1826, in 1,322 hymnals)")
    assert facts_note(Rec("x"), year_of=year_of, count_of=count_of) == ""


def test_is_newer_than_preferred():
    assert is_newer_than_preferred(None, 1970) is False
    assert is_newer_than_preferred(1969, 1970) is False
    assert is_newer_than_preferred(1970, 1970) is True
    assert is_newer_than_preferred(1985, 1970) is True
    assert is_newer_than_preferred(1985, None) is False     # no preference: never flagged
````

**In `backend/tests/test_hymns_repo.py`, replace:**

````python
from sqlalchemy import event, select
````

**with:**

````python
import uuid

import pytest
from sqlalchemy import event, select
````

**In `backend/tests/test_hymns_repo.py`, replace:**

````python
from db.models import Hymn, HymnCatalog
from repos.hymns import (
    add_hymn,
    delete_hymn,
    list_hymns,
    seed_church_from_catalog,
````

**with:**

````python
from db.models import Hymn, HymnCatalog
from domain_errors import NotFound
from repos.hymns import (
    HymnalSummary,
    HymnRecord,
    add_hymn,
    delete_hymn,
    hymnal_summaries,
    list_hymnal_records,
    list_hymns,
    query_hymns,
    seed_church_from_catalog,
````

**Append to `backend/tests/test_hymns_repo.py`:**

````python


# --- slice 3a: typed reads (S Backend 1 "repos/hymns.py"; F §1.4) -------------------

def _hymn(church_id, hymnal, title, number=None, refs=None, **extra):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number,
                   scripture_refs=refs, **extra)
        s.add(row)
        s.flush()
        return row.id


def _titles(records):
    return [(r.hymnal, r.number, r.title) for r in records]


def test_query_hymns_maps_records_and_orders_nulls_last(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "PH1990", "Zion", 5)
    _hymn(cid, "GG2013", "no number b")
    _hymn(cid, "GG2013", "Holy", 2, refs="Isaiah 6:3", theme="Praise",
          hymnary_link="https://hymnary.org/hymn/GG2013/2", text_year=1826, hymnal_count=1322)
    _hymn(cid, "GG2013", "No number A")
    _hymn(cid, "GG2013", "Abide", 10)
    records, total = query_hymns(cid, limit=2000)
    assert total == 5
    assert _titles(records) == [("GG2013", 2, "Holy"), ("GG2013", 10, "Abide"),
                                ("GG2013", None, "No number A"), ("GG2013", None, "no number b"),
                                ("PH1990", 5, "Zion")]
    holy = records[0]
    assert isinstance(holy, HymnRecord) and isinstance(holy.id, uuid.UUID)
    assert (holy.link, holy.scripture_refs, holy.theme, holy.text_year, holy.hymnal_count) == (
        "https://hymnary.org/hymn/GG2013/2", "Isaiah 6:3", "Praise", 1826, 1322)


def test_query_hymns_filters_by_hymnal_number_and_escaped_title(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "GG2013", "Joy to the World", 134)
    _hymn(cid, "GG2013", "Psalm 134", 999)
    _hymn(cid, "GG2013", "100% Sure", 1)
    _hymn(cid, "GG2013", "100 Sure", 2)
    _hymn(cid, "GG2013", "snake_case", 3)
    _hymn(cid, "GG2013", "snakeXcase", 4)
    _hymn(cid, "PH1990", "Joy to the World", 40)
    assert _titles(query_hymns(cid, hymnal="PH1990")[0]) == [("PH1990", 40, "Joy to the World")]
    assert query_hymns(cid, hymnal="NOPE") == ([], 0)
    assert {r.number for r in query_hymns(cid, q="134")[0]} == {134, 999}     # number or title
    assert [r.title for r in query_hymns(cid, q=" JOY ", hymnal="GG2013")[0]] == ["Joy to the World"]
    assert [r.title for r in query_hymns(cid, q="100%")[0]] == ["100% Sure"]
    assert [r.title for r in query_hymns(cid, q="e_c")[0]] == ["snake_case"]
    assert query_hymns(cid, q="   ")[1] == 7                                     # blank q: no filter


def test_long_digit_q_uses_the_title_branch_only(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "GG2013", "Hymn 123456", 123456)
    _hymn(cid, "GG2013", "Other", 7)
    assert [r.number for r in query_hymns(cid, q="123456")[0]] == [123456]    # 6 digits: number too
    assert query_hymns(cid, q="9" * 30) == ([], 0)                             # no OverflowError
    assert [r.number for r in query_hymns(cid, q="1234567")[0]] == []


def test_query_hymns_pages_counts_blank_titles_and_is_church_scoped(tmp_db, make_church):
    a, b = make_church(name="A"), make_church(name="B")
    for n in range(1, 6):
        _hymn(a, "GG2013", f"Hymn {n}", n)
    _hymn(a, "GG2013", None, 6)
    _hymn(a, "GG2013", "  ", 7)
    _hymn(b, "GG2013", "Church B only", 1)
    page, total = query_hymns(a, limit=2, offset=2)
    assert total == 7
    assert [r.number for r in page] == [3, 4]
    assert [r.number for r in query_hymns(a, limit=10, offset=5)[0]] == [6, 7]
    assert "Church B only" not in [r.title for r in query_hymns(a, limit=100)[0]]
    with pytest.raises(NotFound):
        query_hymns("not-a-uuid")


def test_hymnal_summaries_count_hymns_and_scripture_refs(tmp_db, make_church):
    cid, other = make_church(name="A"), make_church(name="B")
    _hymn(cid, "PH1990", "One", 1)
    _hymn(cid, "GG2013", "Two", 2, refs="John 3:16")
    _hymn(cid, "GG2013", "Three", 3, refs="   ")
    _hymn(cid, "GG2013", "Four", 4)
    _hymn(cid, "", "Blank code", 5)
    _hymn(other, "ZZ", "Other church", 1)
    assert hymnal_summaries(cid) == [HymnalSummary("GG2013", 3, 1), HymnalSummary("PH1990", 1, 0)]
    assert hymnal_summaries(make_church(name="Empty")) == []


def test_list_hymnal_records_in_hymnal_order_in_the_callers_session(tmp_db, make_church):
    cid = make_church()
    _hymn(cid, "GG2013", "B", 2)
    _hymn(cid, "GG2013", "A", None)
    _hymn(cid, "GG2013", "C", 1)
    _hymn(cid, "PH1990", "D", 1)
    with session_scope() as s:
        records = list_hymnal_records(cid, "GG2013", session=s)
        assert [r.title for r in records] == ["C", "B", "A"]
        assert hymnal_summaries(cid, session=s)[0].code == "GG2013"
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_ranking.py backend/tests/test_hymns_repo.py 2>&1 | tail -4
.venv/bin/python -m pytest -q backend/tests/test_churches_repo.py 2>&1 | tail -2
```

**Expected:**

```
ERROR backend/tests/test_hymn_ranking.py
ERROR backend/tests/test_hymns_repo.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
2 errors in <t>s
```

(`ImportError: cannot import name 'is_newer_than_preferred'` and `... 'HymnalSummary'`), then `FAILED backend/tests/test_churches_repo.py::test_rubric_overrides_read_in_the_callers_session` (a `TypeError`: `get_church_rubric_overrides()` got an unexpected keyword argument `session`) and `1 failed, 8 passed in <t>s`.

- [ ] **Step 4 (agent): Write the reads, the accessors and the session parameter**

**Replace the whole of `backend/hymn_ranking.py` with:**

````python
#!/usr/bin/env python3
"""Order hymn candidates by the rubric's preferences: older first, then more
familiar. Preferences, not filters: ranking never removes a hymn, and cutting a
ranked list short keeps places for newer hymns.

The hymns are flat Notion-key dicts by default ("Text Year", "Hymnal Count").
Slice 3 passes typed records with the keyword-only accessors `year_of` and
`count_of` (for example `lambda r: r.text_year`), so there is one
implementation for both shapes."""
import statistics
from itertools import zip_longest
from typing import Any, Callable, List, Optional

from hymn_utils import get_property_value

_OLDER, _UNKNOWN, _NEWER = 0, 1, 2

Accessor = Callable[[Any], Optional[int]]


def _flat_year(hymn: Any) -> Optional[int]:
    return get_property_value(hymn, "Text Year")


def _flat_count(hymn: Any) -> Optional[int]:
    return get_property_value(hymn, "Hymnal Count")


def is_newer_than_preferred(year: Optional[int], prefer_before_year: Optional[int]) -> bool:
    """True when the words' year is known and not before the preferred year
    (the rule PR #4's hymn_display_info used for its newer_than_preferred)."""
    return year is not None and prefer_before_year is not None and year >= prefer_before_year


def _era(hymn: Any, before_year: int, year_of: Accessor) -> int:
    year = year_of(hymn)
    if year is None:
        return _UNKNOWN
    return _OLDER if year < before_year else _NEWER


def rank_candidates(hymns: List[Any], *, prefer_before_year: int, prefer_familiar: bool,
                    year_of: Accessor = _flat_year, count_of: Accessor = _flat_count) -> List[Any]:
    """A new list: hymns written before `prefer_before_year` first, then
    unknown years, then newer ones. Within each group, when `prefer_familiar`
    is on, hymns in more hymnals come first. An unknown count ranks as the
    median of the known counts, so it is neither pushed up nor down. The sort
    is stable, so ties keep their original order."""
    counts = [c for x in hymns if (c := count_of(x)) is not None]
    median = statistics.median(counts) if counts else 0

    def key(hymn):
        era = _era(hymn, prefer_before_year, year_of)
        if not prefer_familiar:
            return (era, 0)
        count = count_of(hymn)
        return (era, -(median if count is None else count))

    return sorted(hymns, key=key)


def shortlist(ranked: List[Any], *, limit: int, prefer_before_year: int,
              reserve: int, year_of: Accessor = _flat_year) -> List[Any]:
    """At most `limit` hymns from a list already ordered by `rank_candidates`,
    still in that order. Up to `reserve` places go to the best-ranked hymns of
    unknown year and newer hymns, taken from each group in turn, so a long run
    of older hymns cannot push them out of view; places they do not need go
    back to the older hymns."""
    if len(ranked) <= limit:
        return list(ranked)
    by_era = {_UNKNOWN: [], _NEWER: []}
    for i, hymn in enumerate(ranked):
        era = _era(hymn, prefer_before_year, year_of)
        if era in by_era:
            by_era[era].append(i)
    alternating = [i for pair in zip_longest(by_era[_UNKNOWN], by_era[_NEWER])
                   for i in pair if i is not None]
    keep = set(alternating[:min(reserve, limit)])
    for i in range(len(ranked)):
        if len(keep) >= limit:
            break
        keep.add(i)
    return [ranked[i] for i in sorted(keep)]


def facts_note(hymn: Any, *, year_of: Accessor = _flat_year,
               count_of: Accessor = _flat_count) -> str:
    """'(written 1826, in 1,322 hymnals)' with whichever facts are known, or ''."""
    year = year_of(hymn)
    count = count_of(hymn)
    parts = []
    if year is not None:
        parts.append(f"written {year}")
    if count is not None:
        parts.append(f"in {count:,} hymnals")
    return f"({', '.join(parts)})" if parts else ""
````

**In `backend/repos/churches.py`, replace:**

````python
    _merge_settings(church_id, {"liturgy_prompts": cleaned})


def get_church_rubric_overrides(church_id) -> dict:
    """The church's stored rubric overrides ({} when it uses all defaults)."""
    church = get_church(church_id)
    if not church:
        return {}
    stored = (church.get("settings") or {}).get("rubric")
````

**with:**

````python
    _merge_settings(church_id, {"liturgy_prompts": cleaned})


def get_church_rubric_overrides(church_id, *, session: Optional[Session] = None) -> dict:
    """The church's stored rubric overrides ({} when it uses all defaults).
    Reads in the caller's `session` or in its own scope (slice 3, F §2.2 rule 3)."""
    church = get_church(church_id, session=session)
    if not church:
        return {}
    stored = (church.get("settings") or {}).get("rubric")
````

**In `backend/repos/hymns.py`, replace:**

````python
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session
````

**with:**

````python
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import case, delete, func, insert, or_, select
from sqlalchemy.orm import Session
````

**In `backend/repos/hymns.py`, replace:**

````python
from db import session_scope
from db.models import Hymn, HymnCatalog
````

**with:**

````python
from db import session_scope
from db.ids import as_uuid
from db.models import Hymn, HymnCatalog
````

**Append to `backend/repos/hymns.py`:**

````python


# --- slice 3a: typed reads for the new app (S Backend 1 "repos/hymns.py") ----------
# Church-scoped, ids through db.ids.as_uuid (F §2.2 item 5), each in the
# caller's session or its own. list_hymns and list_church_hymnals above stay
# for the CLI and frozen Streamlit.


@dataclass(frozen=True)
class HymnRecord:
    id: uuid.UUID
    hymnal: str
    title: Optional[str]
    number: Optional[int]
    link: Optional[str]
    scripture_refs: Optional[str]
    theme: Optional[str]
    text_year: Optional[int]
    hymnal_count: Optional[int]


@dataclass(frozen=True)
class HymnalSummary:
    code: str
    hymn_count: int
    scripture_ref_count: int      # hymns whose scripture_refs is not blank


_RECORD_COLUMNS = (Hymn.id, Hymn.hymnal, Hymn.title, Hymn.number, Hymn.hymnary_link,
                   Hymn.scripture_refs, Hymn.theme, Hymn.text_year, Hymn.hymnal_count)

# hymnal, number (NULLs last on SQLite and Postgres alike), title, id (F §1.4).
_ORDER = (Hymn.hymnal.asc(), Hymn.number.asc().nulls_last(),
          func.lower(func.coalesce(Hymn.title, "")).asc(), Hymn.id.asc())


def _record(row) -> HymnRecord:
    return HymnRecord(id=row.id, hymnal=row.hymnal, title=row.title, number=row.number,
                      link=row.hymnary_link, scripture_refs=row.scripture_refs, theme=row.theme,
                      text_year=row.text_year, hymnal_count=row.hymnal_count)


def _in(session: Optional[Session], work):
    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def hymnal_summaries(church_id, *, session: Optional[Session] = None) -> list[HymnalSummary]:
    """Each hymnal code in the church (blank codes left out), ORDER BY code."""
    cid = as_uuid(church_id)
    has_refs = case((func.trim(func.coalesce(Hymn.scripture_refs, "")) != "", 1), else_=0)

    def work(s: Session) -> list[HymnalSummary]:
        rows = s.execute(
            select(Hymn.hymnal, func.count(), func.coalesce(func.sum(has_refs), 0))
            .where(Hymn.church_id == cid, Hymn.hymnal != "")
            .group_by(Hymn.hymnal).order_by(Hymn.hymnal)
        ).all()
        return [HymnalSummary(code, int(count), int(refs)) for code, count, refs in rows]

    return _in(session, work)


def query_hymns(church_id, *, hymnal: Optional[str] = None, q: Optional[str] = None,
                limit: int = 50, offset: int = 0,
                session: Optional[Session] = None) -> tuple[list[HymnRecord], int]:
    """One page of the church's hymns and the total matching the filter.

    `hymnal` filters exactly. `q` (trimmed; empty = no filter) of 1-6 digits
    also matches `number`; otherwise, and always as well, lower(title)
    contains lower(q), with % and _ escaped. Blank titles are included.
    """
    cid = as_uuid(church_id)
    conditions = [Hymn.church_id == cid]
    if hymnal is not None:
        conditions.append(Hymn.hymnal == hymnal)
    text = (q or "").strip()
    if text:
        title_match = func.lower(Hymn.title).contains(text.lower(), autoescape=True)
        if text.isdigit() and len(text) <= 6:       # 7+ digits could overflow an integer bind
            conditions.append(or_(Hymn.number == int(text), title_match))
        else:
            conditions.append(title_match)

    def work(s: Session) -> tuple[list[HymnRecord], int]:
        total = s.execute(select(func.count()).select_from(Hymn).where(*conditions)).scalar_one()
        rows = s.execute(select(*_RECORD_COLUMNS).where(*conditions)
                         .order_by(*_ORDER).limit(limit).offset(offset)).all()
        return [_record(r) for r in rows], int(total)

    return _in(session, work)


def list_hymnal_records(church_id, hymnal: str, *,
                        session: Optional[Session] = None) -> list[HymnRecord]:
    """Every hymn of one hymnal of the church, in hymnal order."""
    cid = as_uuid(church_id)

    def work(s: Session) -> list[HymnRecord]:
        rows = s.execute(select(*_RECORD_COLUMNS)
                         .where(Hymn.church_id == cid, Hymn.hymnal == hymnal)
                         .order_by(*_ORDER)).all()
        return [_record(r) for r in rows]

    return _in(session, work)
````

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_ranking.py backend/tests/test_hymns_repo.py backend/tests/test_churches_repo.py backend/tests/test_suggest_hymns.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `47 passed in <t>s` (34 in the three files, and PR #4's 13 `test_suggest_hymns.py` tests unchanged, so the flat-dict defaults still hold); `1035 passed, 9 skipped in <t>s`; then ` M` for `backend/hymn_ranking.py`, `backend/repos/churches.py`, `backend/repos/hymns.py`, `backend/tests/test_churches_repo.py`, `backend/tests/test_hymn_ranking.py`, `backend/tests/test_hymns_repo.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/hymn_ranking.py backend/repos/churches.py backend/repos/hymns.py \
        backend/tests/test_churches_repo.py backend/tests/test_hymn_ranking.py backend/tests/test_hymns_repo.py
git commit -m "Repos: typed hymn reads, ranking accessors and the rubric in the caller's session (S Backend 1; F §1.4, §2.2)" -m "repos.hymns gains HymnRecord, HymnalSummary, hymnal_summaries, query_hymns
(hymnal, number nulls last, title, id; q of 1-6 digits also matches the
number; % and _ escaped) and list_hymnal_records, each church-scoped and in
the caller's session or its own. hymn_ranking's rank_candidates, shortlist
and facts_note take year_of/count_of accessors (flat-dict defaults keep PR
#4's tests), and is_newer_than_preferred moves PR #4's display rule out of
worship_service. get_church_rubric_overrides takes session=None.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check that `hymn_ranking.py`'s default accessors give PR #4's behavior (its 9 existing tests unchanged) and that each new repo function filters `Hymn.church_id`. Push the backup.

Counts after Task 6: backend **1035 passed, 9 skipped**; frontend **356 in 55 files**.

### Task 7: The recent-use window around the service date (S Backend 1 row `hymn_usage.py`, 3.4; Testing `test_hymn_usage_window.py`, postgres; owner answer Q2; AC4 window half; clarifications 1, 17)

This task adds `RECENT_WEEKS = 12` and `usage_near(church_id, service_date, *, weeks=12, session=None) -> dict[str, date]` to `backend/hymn_usage.py`: every usage in [D − 84, D + 84] with D itself excluded, keyed by `hymn_search.usage_key(title)` (the title alone, owner answer Q2), valued by the date nearest D (ties to the earlier). Because Notion imports stored `""` or datetimes in `date_iso`, SQL applies a deliberately wide string range and Python the exact window on `date_iso[:10]`; a value that still does not parse is skipped and counted at DEBUG. Nothing raises on stored data. `get_recently_used_identifiers` and `record_usage` stay for frozen Streamlit.

**Files:**
- Modify: `backend/hymn_usage.py` (the import block; the slice 3a section appended)
- Test: `backend/tests/test_hymn_usage_window.py` (new; 8 tests and 1 Postgres test)

**Interfaces:**
- Consumes: `hymn_search.usage_key` (Task 5); `db.ids.as_uuid`; `db.models.HymnUsage` (`date_iso`, `hymn_number`, `hymn_title`; index `ix_hymn_usage_church_date`); the `pg_db` fixture (CI).
- Produces (later users: Tasks 9, 10, 13): `hymn_usage.RECENT_WEEKS = 12`; `hymn_usage.usage_near(church_id, service_date: date, *, weeks=12, session=None) -> dict[str, date]`.

- [ ] **Step 1 (agent): Confirm Task 6's count**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `1035 passed, 9 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `backend/tests/test_hymn_usage_window.py`:**

````python
"""hymn_usage.usage_near: the recent-use window around the service date
(slice 3 spec, Backend 3.4; Testing `test_hymn_usage_window.py`; AC4 window
half; owner answer Q2 of 2026-09-29: the key is the normalized title alone)."""
import logging
import uuid
from datetime import date

import pytest

from db import session_scope
from db.models import Church, HymnUsage, User
from hymn_usage import RECENT_WEEKS, usage_near

D = date(2026, 10, 4)                     # a Sunday; D - 84 = 2026-07-12, D + 84 = 2026-12-27


def _use(church_id, date_iso, title="Holy, Holy, Holy", number=1):
    with session_scope() as s:
        s.add(HymnUsage(church_id=church_id, date_iso=date_iso, hymn_number=number, hymn_title=title))


def test_window_is_84_days_each_side_inclusive_and_excludes_the_service_date(tmp_db, make_church):
    cid = make_church()
    assert RECENT_WEEKS == 12
    _use(cid, "2026-07-12", "Edge before")
    _use(cid, "2026-12-27", "Edge after")
    _use(cid, "2026-07-11", "Too early")
    _use(cid, "2026-12-28", "Too late")
    _use(cid, "2026-10-04", "Same day")
    assert usage_near(cid, D) == {"edge before": date(2026, 7, 12), "edge after": date(2026, 12, 27)}


def test_nearest_date_wins_and_ties_go_to_the_earlier_date(tmp_db, make_church):
    cid = make_church()
    _use(cid, "2026-08-02", "A")
    _use(cid, "2026-09-20", "A")
    _use(cid, "2026-10-18", "A")          # 14 days after; 2026-09-20 is 14 days before
    _use(cid, "2026-11-01", "B")
    _use(cid, "2026-10-11", "B")
    assert usage_near(cid, D) == {"a": date(2026, 9, 20), "b": date(2026, 10, 11)}


def test_the_key_is_the_title_alone_across_numbers_and_hymnals(tmp_db, make_church):
    """Owner answer Q2: a hymn sung as GG2013 #403 is recent when picked as PH1990 #138."""
    cid = make_church()
    _use(cid, "2026-09-27", "Come, Thou Almighty King", number=403)
    _use(cid, "2026-09-13", "Nameless", number=None)
    near = usage_near(cid, D)
    assert near["come, thou almighty king"] == date(2026, 9, 27)
    assert near["nameless"] == date(2026, 9, 13)


def test_title_whitespace_and_case_are_tolerated(tmp_db, make_church):
    cid = make_church()
    _use(cid, "2026-09-27", "  Come,  Thou ALMIGHTY King ")
    _use(cid, "2026-09-20", "")
    _use(cid, "2026-09-20", None)
    assert usage_near(cid, D) == {"come, thou almighty king": date(2026, 9, 27)}


def test_usage_is_church_scoped(tmp_db, make_church):
    a, b = make_church(name="A"), make_church(name="B")
    _use(b, "2026-09-27", "Only in B")
    assert usage_near(a, D) == {}
    assert usage_near(b, D) == {"only in b": date(2026, 9, 27)}


def test_null_and_blank_dates_are_ignored(tmp_db, make_church):
    cid = make_church()
    _use(cid, None, "Null date")
    _use(cid, "", "Blank date")
    assert usage_near(cid, D) == {}


def test_datetime_shaped_dates_count_as_their_day(tmp_db, make_church):
    cid = make_church()
    _use(cid, "2026-08-02T10:00:00.000-05:00", "Inside")
    _use(cid, "2026-12-27T10:00:00.000-05:00", "On the last day")
    _use(cid, "2026-10-04T10:00:00.000-05:00", "On the service date")
    assert usage_near(cid, D) == {"inside": date(2026, 8, 2), "on the last day": date(2026, 12, 27)}


def test_malformed_dates_are_skipped_and_counted_at_debug(tmp_db, make_church, caplog):
    cid = make_church()
    _use(cid, "2026-8-2", "Unpadded")             # sorts after "2026-12-28": SQL drops it
    _use(cid, "2026-10-1", "Malformed")           # inside the SQL range, then fails to parse
    _use(cid, "2026-09-3x", "Also malformed")
    _use(cid, "2026-09-27", "Good")
    caplog.set_level(logging.DEBUG, logger="hymn_usage")
    assert usage_near(cid, D) == {"good": date(2026, 9, 27)}
    assert "usage_near skipped 2 usage rows" in caplog.text


@pytest.mark.postgres
def test_usage_near_on_postgres(pg_db):
    """The string range and the datetime-shaped value on Postgres (S Testing "postgres")."""
    user_id, church_id = uuid.uuid4(), uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=user_id, email="pg@example.com"))
        s.add(Church(id=church_id, name="PG", timezone="America/New_York", settings={}))
    _use(church_id, "2026-12-27T10:00:00.000-05:00", "Last day")
    _use(church_id, "2026-12-28", "Too late")
    _use(church_id, "2026-8-2", "Malformed")
    _use(church_id, "2026-10-04", "Same day")
    _use(church_id, "2026-07-12", "First day")
    assert usage_near(church_id, D) == {"last day": date(2026, 12, 27),
                                        "first day": date(2026, 7, 12)}
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_usage_window.py 2>&1 | tail -3
```

**Expected:**

```
ERROR backend/tests/test_hymn_usage_window.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

(`ImportError: cannot import name 'RECENT_WEEKS' from 'hymn_usage'`.)

- [ ] **Step 4 (agent): Write `usage_near`**

**In `backend/hymn_usage.py`, replace:**

````python
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
````

**with:**

````python
"""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
````

**In `backend/hymn_usage.py`, replace:**

````python
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select

from db import session_scope
from db.models import HymnUsage


def _as_uuid(value: Any) -> uuid.UUID:
````

**with:**

````python
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import HymnUsage
from hymn_search import usage_key

logger = logging.getLogger(__name__)


def _as_uuid(value: Any) -> uuid.UUID:
````

**Append to `backend/hymn_usage.py`:**

````python


# --- slice 3a: the recent-use window around a service date (S Backend 3.4) --------

RECENT_WEEKS = 12


def usage_near(church_id, service_date: date, *, weeks: int = RECENT_WEEKS,
               session: Optional[Session] = None) -> Dict[str, date]:
    """{usage_key(title): the usage date nearest `service_date`} for the church's
    usage in [D - weeks, D + weeks], both ends inclusive, D itself excluded.

    The key is the normalized title alone (owner answer Q2, 2026-09-29), so a
    hymn sung from one hymnal counts when it is picked from another. Ties go
    to the earlier date. date_iso is not always YYYY-MM-DD (Notion imports
    stored "" or a datetime), so SQL keeps a deliberately wide string range and
    Python applies the exact window to date_iso[:10]; a value that still does
    not parse is skipped and counted at DEBUG. Nothing here raises on stored data.
    """
    cid = as_uuid(church_id)
    low = service_date - timedelta(days=7 * weeks)
    high = service_date + timedelta(days=7 * weeks)

    def work(s: Session):
        return s.execute(
            select(HymnUsage.date_iso, HymnUsage.hymn_title).where(
                HymnUsage.church_id == cid,
                HymnUsage.date_iso >= low.isoformat(),
                HymnUsage.date_iso < (high + timedelta(days=1)).isoformat(),
            )
        ).all()

    if session is not None:
        rows = work(session)
    else:
        with session_scope() as own:
            rows = work(own)

    nearest: Dict[str, date] = {}
    skipped = 0
    for date_iso, title in rows:
        try:
            day = date.fromisoformat((date_iso or "")[:10])
        except ValueError:
            skipped += 1
            continue
        if not (low <= day <= high) or day == service_date:
            continue
        key = usage_key(title)
        if not key:
            continue
        best = nearest.get(key)
        distance = abs((day - service_date).days)
        if (best is None or distance < abs((best - service_date).days)
                or (distance == abs((best - service_date).days) and day < best)):
            nearest[key] = day
    if skipped:
        logger.debug("usage_near skipped %d usage rows with an unreadable date_iso", skipped)
    return nearest
````

- [ ] **Step 5 (agent): Run the tests (and the Postgres one, if a local Postgres is available) and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_usage_window.py backend/tests/test_hymn_usage.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `12 passed, 1 skipped in <t>s` (8 new and slice 1's 4; the skip is the Postgres test); `1043 passed, 10 skipped in <t>s`; then ` M backend/hymn_usage.py` and `?? backend/tests/test_hymn_usage_window.py`. With a local throwaway Postgres (for example `TEST_DATABASE_URL=postgresql://postgres:ci-throwaway@localhost:5432/postgres`), `-m postgres backend/tests/test_hymn_usage_window.py` gives `1 passed, 8 deselected`; otherwise CI's `backend-postgres` runs it (Task 16).

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/hymn_usage.py backend/tests/test_hymn_usage_window.py
git commit -m "Usage: the 12-week window around the service date, keyed by title (S Backend 3.4; owner answer Q2; AC4)" -m "usage_near reads the church's usage in [D-84, D+84] without D itself and
returns the nearest date per normalized title (ties to the earlier).
date_iso may be '' or a Notion datetime, so SQL keeps a wide string range
and Python the exact window on date_iso[:10]; unreadable values are skipped
and counted at DEBUG, never raised. The key is the title alone (owner
answer Q2, clarification 1). A Postgres test covers the string range.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check the window bounds against S 3.4 (D − 84 and D + 84 kept, D − 85, D + 85 and D dropped) and that nothing in `usage_near` can raise on a stored value. Push the backup.

Counts after Task 7: backend **1043 passed, 10 skipped**; frontend **356 in 55 files**.

### Task 8: `GET /hymnals` and the `GET /church` hymnal fields (S API rows 1 and 5, Models `HymnalOut`/`HymnalListOut`, Backend 3.1-3.2; Testing `test_api_hymnals.py`; AC1, AC2, AC8; clarifications 12, 13)

This task creates `backend/usecases/hymns.py` with `resolve_default_hymnal` (the stored `default_hymnal` when it is a non-blank string; effective = the stored code if the church has it, else the alphabetically first, else null) and `hymnal_overview`, and the route `GET /hymnals` in `backend/api/routes/hymnals.py`. `GET /church` (`usecases/church_profile.get_church_profile`, now one session) calls `resolve_default_hymnal` and returns `default_hymnal` and `effective_hymnal`, so the two routes never disagree. The four exact-body `/church` tests and the error-doc map change with it; the OpenAPI files are regenerated, and the frontend's `churchProfile()` test fixture gains the two fields that the regenerated type now requires.

**Decisions recorded in this task:**
- **T8-1 (clarification 12).** One session for the church row and the hymnals; the "church deleted after the guard" test still sees a 403.
- **T8-2 (clarification 13).** `frontend/src/test/fixtures/index.ts` changes; no frontend count changes.
- **T8-3.** `default_hymnal` is returned verbatim (not stripped) when non-blank, and compared verbatim with the codes.

**Files:**
- Create: `backend/usecases/hymns.py`, `backend/api/routes/hymnals.py`
- Modify: `backend/api/main.py` (the routes import; mount `hymnals.router`)
- Modify: `backend/api/schemas.py` (`ChurchProfileOut` + 2 fields)
- Modify: `backend/usecases/church_profile.py` (whole file shown)
- Modify (tests): `backend/tests/test_api_app.py` (map), `backend/tests/test_api_church_profile.py` (exact body; required set), `backend/tests/test_api_churches.py`, `backend/tests/test_api_invites.py`, `backend/tests/test_api_me.py` (exact bodies), `frontend/src/test/fixtures/index.ts`
- Test: `backend/tests/test_api_hymnals.py` (new)
- Modify (generated, never by hand): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes: Task 6's `hymnal_summaries(church_id, *, session)`; `repos.churches.get_church(church_id, *, session)`, `update_church`; `api.deps.ActiveChurch`, `require_church`; `api.errors.error_responses`; `tests.api_helpers.assert_church_isolated`, `isolation_world`, `church_headers`, `make_api_client`; `repos.memberships.add_membership(user_id, church_id, role)`.
- Produces (later users: Tasks 9, 10, 13; slices 3b, 5a, 6a):
  - `usecases.hymns.DefaultHymnal(default_hymnal, effective_hymnal)`; `resolve_default_hymnal(church_id, *, session=None) -> DefaultHymnal`; `HymnalOverview(items, default_hymnal, effective_hymnal)`; `hymnal_overview(church_id) -> HymnalOverview`; private `_resolve(settings, codes)` and `_settings(church_id, session)` reused by Task 10.
  - `GET /hymnals` → `HymnalListOut {items: [HymnalOut {code, hymn_count, scripture_ref_count}], default_hymnal, effective_hymnal}`.
  - `ChurchProfileOut` and `usecases.church_profile.ChurchProfile` gain `default_hymnal: str | None` and `effective_hymnal: str | None`.

- [ ] **Step 1 (agent): Confirm Task 7's count and the `/church` body tests**

```bash
.venv/bin/python -m pytest -q | tail -1
grep -n '"effective_translation": "web", "effective_translation_label"' backend/tests/test_api_churches.py backend/tests/test_api_invites.py backend/tests/test_api_me.py
```

**Expected:** `1043 passed, 10 skipped in <t>s`; three lines, at `test_api_churches.py:89`, `test_api_invites.py:205` and `test_api_me.py:84`.

- [ ] **Step 2 (agent): Write the failing tests and the fixture change**

**In `backend/tests/test_api_app.py`, replace:**

````python
        ("/scripture/passages", "post"): {"401", "422", "429", "503"},
    }
````

**with:**

````python
        ("/scripture/passages", "post"): {"401", "422", "429", "503"},
        ("/hymnals", "get"): {"401", "403", "422", "503"},
    }
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````python
        "effective_translation_label": "King James Version (KJV)",
    }
````

**with:**

````python
        "effective_translation_label": "King James Version (KJV)",
        "default_hymnal": None,
        "effective_hymnal": None,
    }
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````python
    assert ok["schema"] == {"$ref": "#/components/schemas/ChurchProfileOut"}
    assert set(components["ChurchProfileOut"]["required"]) == {
        "id", "name", "role", "timezone", "timezone_valid", "bible_translation",
        "effective_translation", "effective_translation_label"}


def test_church_deleted_after_guard_is_403(client, make_user, make_church, monkeypatch):
````

**with:**

````python
    assert ok["schema"] == {"$ref": "#/components/schemas/ChurchProfileOut"}
    assert set(components["ChurchProfileOut"]["required"]) == {
        "id", "name", "role", "timezone", "timezone_valid", "bible_translation",
        "effective_translation", "effective_translation_label", "default_hymnal", "effective_hymnal"}


def test_church_deleted_after_guard_is_403(client, make_user, make_church, monkeypatch):
````

**In `backend/tests/test_api_churches.py`, replace:**

````python
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
    }
````

**with:**

````python
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
        "default_hymnal": None, "effective_hymnal": "GG2013",  # slice 3: the seeded catalog is GG2013
    }
````

**Create `backend/tests/test_api_hymnals.py`:**

````python
"""GET /hymnals and GET /church's hymnal fields (slice 3 spec, API row 1 and
row 5, Models `HymnalOut`/`HymnalListOut`, Backend 3.1-3.2; Testing
`test_api_hymnals.py`; AC1, AC2, AC8)."""
import pytest

from db import session_scope
from db.models import Hymn
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _hymns(church_id, hymnal, count, *, refs_every=0):
    with session_scope() as s:
        for n in range(1, count + 1):
            refs = "John 3:16" if refs_every and n % refs_every == 0 else None
            s.add(Hymn(church_id=church_id, hymnal=hymnal, title=f"{hymnal} {n}", number=n,
                       scripture_refs=refs))


def _set_default(church_id, value):
    church = churches.get_church(church_id)
    churches.update_church(church_id, settings={**(church["settings"] or {}), "default_hymnal": value})


def _get(client, church_id, path="/hymnals", email=EMAIL):
    r = client.get(path, headers=church_headers(email, church_id))
    assert r.status_code == 200, r.text
    return r.json()


def _church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def test_counts_and_scripture_ref_counts_ordered_by_code(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "PH1990", 3)
    _hymns(cid, "GG2013", 4, refs_every=2)
    assert _get(client, cid) == {
        "items": [{"code": "GG2013", "hymn_count": 4, "scripture_ref_count": 2},
                  {"code": "PH1990", "hymn_count": 3, "scripture_ref_count": 0}],
        "default_hymnal": None,
        "effective_hymnal": "GG2013",
    }


def test_a_stored_default_the_church_has_is_effective(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "GG2013", 1)
    _hymns(cid, "PH1990", 1)
    _set_default(cid, "PH1990")
    body = _get(client, cid)
    assert (body["default_hymnal"], body["effective_hymnal"]) == ("PH1990", "PH1990")


def test_a_stored_default_the_church_lacks_falls_back_alphabetically(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "PH1990", 1)
    _hymns(cid, "GG2013", 1)
    _set_default(cid, "UMH")
    body = _get(client, cid)
    assert (body["default_hymnal"], body["effective_hymnal"]) == ("UMH", "GG2013")


def test_a_stored_default_that_is_not_a_string_or_is_blank_is_unset(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _hymns(cid, "PH1990", 1)
    for value in (7, "   ", "", None, ["PH1990"]):
        _set_default(cid, value)
        body = _get(client, cid)
        assert (body["default_hymnal"], body["effective_hymnal"]) == (None, "PH1990"), value


def test_a_church_with_no_hymns_has_no_hymnal(client, make_user, make_church):
    cid = _church(make_user, make_church)
    _set_default(cid, "GG2013")
    assert _get(client, cid) == {"items": [], "default_hymnal": "GG2013", "effective_hymnal": None}


def test_get_church_returns_the_same_two_values(client, make_user, make_church):
    cid = _church(make_user, make_church)
    for setup in (lambda: None, lambda: _hymns(cid, "PH1990", 2), lambda: _hymns(cid, "GG2013", 2),
                  lambda: _set_default(cid, "PH1990"), lambda: _set_default(cid, "UMH")):
        setup()
        hymnals, profile = _get(client, cid), _get(client, cid, "/church")
        assert (profile["default_hymnal"], profile["effective_hymnal"]) == (
            hymnals["default_hymnal"], hymnals["effective_hymnal"])


def test_church_isolation_and_every_role(client, isolation_world, make_user):
    world = isolation_world
    _hymns(world.church_a, "GG2013", 2)
    _hymns(world.church_b, "ZZB", 2)
    assert_church_isolated(client, "GET", "/hymnals", world=world)
    assert [i["code"] for i in _get(client, world.church_a, email=world.a)["items"]] == ["GG2013"]
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        assert _get(client, world.church_a, email=email)["effective_hymnal"] == "GG2013"
````

**In `backend/tests/test_api_invites.py`, replace:**

````python
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
    }
````

**with:**

````python
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
        "default_hymnal": None, "effective_hymnal": None,     # slice 3: no hymns in this church
    }
````

**In `backend/tests/test_api_me.py`, replace:**

````python
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
    }
````

**with:**

````python
        "effective_translation": "web", "effective_translation_label": "World English Bible (WEB)",
        "default_hymnal": None, "effective_hymnal": None,     # slice 3: no hymns in this church
    }
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
// --- slice 2b: the church profile, drafts and lectionary answers ------------------

/** `GET /church` for Grace (slice 2a's `ChurchProfileOut`): New York, WEB. */
export function churchProfile(overrides: Partial<ChurchProfile> = {}): ChurchProfile {
  return {
````

**with:**

````ts
// --- slice 2b: the church profile, drafts and lectionary answers ------------------

/** `GET /church` for Grace (`ChurchProfileOut`, slices 2a and 3a): New York, WEB, GG2013. */
export function churchProfile(overrides: Partial<ChurchProfile> = {}): ChurchProfile {
  return {
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
    effective_translation_label: "World English Bible (WEB)",
    ...overrides,
````

**with:**

````ts
    effective_translation_label: "World English Bible (WEB)",
    default_hymnal: null,
    effective_hymnal: "GG2013",
    ...overrides,
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymnals.py backend/tests/test_api_app.py backend/tests/test_api_church_profile.py \
  backend/tests/test_api_churches.py backend/tests/test_api_invites.py backend/tests/test_api_me.py 2>&1 | grep -E "^FAILED|passed|failed" | cut -c1-110
```

**Expected:**

```
FAILED backend/tests/test_api_app.py::test_routes_document_the_error_body - K...
FAILED backend/tests/test_api_church_profile.py::test_new_fields_including_label
FAILED backend/tests/test_api_church_profile.py::test_me_church_items_unchanged
FAILED backend/tests/test_api_churches.py::test_create_201_listed_in_me_and_usable
FAILED backend/tests/test_api_hymnals.py::test_counts_and_scripture_ref_counts_ordered_by_code
FAILED backend/tests/test_api_hymnals.py::test_a_stored_default_the_church_has_is_effective
FAILED backend/tests/test_api_hymnals.py::test_a_stored_default_the_church_lacks_falls_back_alphabetically
FAILED backend/tests/test_api_hymnals.py::test_a_stored_default_that_is_not_a_string_or_is_blank_is_unset
FAILED backend/tests/test_api_hymnals.py::test_a_church_with_no_hymns_has_no_hymnal
FAILED backend/tests/test_api_hymnals.py::test_get_church_returns_the_same_two_values
FAILED backend/tests/test_api_hymnals.py::test_church_isolation_and_every_role
FAILED backend/tests/test_api_invites.py::test_after_accept_get_church_200 - ...
FAILED backend/tests/test_api_me.py::test_church_returns_the_active_church_for_a_member
13 failed, 87 passed, 1 skipped in <t>s
```

`/hymnals` answers 404 `not_found` (no route yet); the map's `KeyError: '/hymnals'`; the `/church` bodies lack the two fields.

- [ ] **Step 4 (agent): Write the usecase, the route and the profile fields**

**In `backend/api/main.py`, replace:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import churches, health, invites, lectionary, me, reference, rubric, scripture
from api.settings import get_settings
````

**with:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import (churches, health, hymnals, invites, lectionary, me, reference, rubric,
                        scripture)
from api.settings import get_settings
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(scripture.router)
    return app
````

**with:**

````python
    app.include_router(scripture.router)
    app.include_router(hymnals.router)
    return app
````

**Create `backend/api/routes/hymnals.py`:**

````python
"""GET /hymnals: the active church's hymnals and its default (slice 3 spec,
API row 1 and Models; Backend 3.1-3.2). Any member; a thin route (F §2.2.1)."""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.deps import ActiveChurch, require_church
from api.errors import error_responses
from usecases import hymns

router = APIRouter()


class HymnalOut(BaseModel):
    code: str                          # e.g. "GG2013"
    hymn_count: int
    scripture_ref_count: int           # hymns with non-blank scripture_refs


class HymnalListOut(BaseModel):
    items: list[HymnalOut]             # ORDER BY code
    default_hymnal: Optional[str]      # churches.settings["default_hymnal"] verbatim, or null
    effective_hymnal: Optional[str]    # default_hymnal if it is in items; else items[0].code; else null


@router.get("/hymnals", response_model=HymnalListOut, responses=error_responses(401, 403, 422, 503))
def list_hymnals(church: ActiveChurch = Depends(require_church)) -> HymnalListOut:
    overview = hymns.hymnal_overview(church.id)
    return HymnalListOut(
        items=[HymnalOut(code=i.code, hymn_count=i.hymn_count, scripture_ref_count=i.scripture_ref_count)
               for i in overview.items],
        default_hymnal=overview.default_hymnal,
        effective_hymnal=overview.effective_hymnal,
    )
````

**In `backend/api/schemas.py`, replace:**

````python
    bible_translation: Optional[str]        # the stored default, or null when unset
    effective_translation: str              # the stored default if offered here, else "web"
    effective_translation_label: str        # its label, for when GET /translations fails


class MeOut(BaseModel):
````

**with:**

````python
    bible_translation: Optional[str]        # the stored default, or null when unset
    effective_translation: str              # the stored default if offered here, else "web"
    effective_translation_label: str        # its label, for when GET /translations fails
    default_hymnal: Optional[str]           # slice 3: the stored default hymnal (read only), or null
    effective_hymnal: Optional[str]         # slice 3: the hymnal the builder opens; null with no hymns


class MeOut(BaseModel):
````

**Replace the whole of `backend/usecases/church_profile.py` with:**

````python
"""The active church's profile for GET /church (S `usecases/church_profile.py`; slice 2 AC6).

get_church_profile reads the church row once and derives the fields the
builder needs: the stored time zone and whether it is a real IANA name, and
the stored default translation and the one passage text actually uses.
Slice 3 added default_hymnal and effective_hymnal; slice 4 adds its fields
to ChurchProfile (and ChurchProfileOut) additively.

The route passes only ActiveChurch.id (F §1.2 rule 1) and supplies the id,
name and role itself. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). The repo and
scripture_fetcher are called through their modules, so a test can patch one
function.
"""
import uuid
from dataclasses import dataclass

import scripture_fetcher
from db import session_scope
from domain_errors import Forbidden
from repos import churches
from timezones import is_valid_timezone
from usecases import hymns

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
    default_hymnal: str | None           # slice 3: settings["default_hymnal"], when a non-blank string
    effective_hymnal: str | None         # slice 3: the hymnal the builder opens (GET /hymnals agrees)


def get_church_profile(church_id: uuid.UUID) -> ChurchProfile:
    """The profile of a live church.

    - timezone_valid: timezones.is_valid_timezone, exact and case-sensitive
      (so "america/new_york" is False, as 6a's PATCH /church will reject it).
    - bible_translation: settings["bible_translation"] when it is a non-empty
      string, else None.
    - effective_translation: that value when this deployment offers it
      (available_translations(), so "esv" only with ESV_API_KEY set), else
      "web"; effective_translation_label is its human label.
    - default_hymnal, effective_hymnal: usecases.hymns.resolve_default_hymnal,
      read in the same session (slice 3).

    Raises Forbidden (403 forbidden, details.reason no_church_access) when the
    church is missing or soft-deleted.
    """
    with session_scope() as s:
        church = churches.get_church(church_id, session=s)
        if church is None:
            raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
        hymnals = hymns.resolve_default_hymnal(church_id, session=s)
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
        default_hymnal=hymnals.default_hymnal,
        effective_hymnal=hymnals.effective_hymnal,
    )
````

**Create `backend/usecases/hymns.py`:**

````python
"""The Hymns step's reads and the AI suggestions (slice 3 spec, Backend 3;
owner decisions 3 and 9; owner answers of 2026-09-29).

- resolve_default_hymnal: the stored default_hymnal and the effective one
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
one session. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). Repos are called
through their modules, so a test can patch one function.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy.orm import Session

from db import session_scope
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary


@dataclass(frozen=True)
class DefaultHymnal:
    default_hymnal: Optional[str]      # settings["default_hymnal"] verbatim, when a non-blank string
    effective_hymnal: Optional[str]    # the default if the church has it, else the first code, else None


@dataclass(frozen=True)
class HymnalOverview:
    items: list[HymnalSummary]
    default_hymnal: Optional[str]
    effective_hymnal: Optional[str]


def _stored_default(settings: Any) -> Optional[str]:
    value = (settings or {}).get("default_hymnal") if isinstance(settings, dict) else None
    return value if isinstance(value, str) and value.strip() else None


def _resolve(settings: Any, codes: list[str]) -> DefaultHymnal:
    stored = _stored_default(settings)
    effective = stored if stored in codes else (codes[0] if codes else None)
    return DefaultHymnal(default_hymnal=stored, effective_hymnal=effective)


def _settings(church_id: uuid.UUID, session: Session) -> Any:
    church = churches.get_church(church_id, session=session)
    return church["settings"] if church else None


def resolve_default_hymnal(church_id: uuid.UUID, *, session: Optional[Session] = None) -> DefaultHymnal:
    """S Backend 3.1: the alphabetical fallback matches Streamlit (app.py:650)."""
    def work(s: Session) -> DefaultHymnal:
        codes = [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=s)]
        return _resolve(_settings(church_id, s), codes)

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def hymnal_overview(church_id: uuid.UUID) -> HymnalOverview:
    """S Backend 3.2: the hymnals (ORDER BY code) and the default, in one session."""
    with session_scope() as s:
        items = hymn_repo.hymnal_summaries(church_id, session=s)
        resolved = _resolve(_settings(church_id, s), [item.code for item in items])
    return HymnalOverview(items=items, default_hymnal=resolved.default_hymnal,
                          effective_hymnal=resolved.effective_hymnal)
````

- [ ] **Step 5 (agent): Run the tests; see the stale OpenAPI file fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymnals.py backend/tests/test_api_app.py backend/tests/test_api_church_profile.py \
  backend/tests/test_api_churches.py backend/tests/test_api_invites.py backend/tests/test_api_me.py \
  backend/tests/test_route_guards.py 2>&1 | tail -1
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -2
```

**Expected:** `105 passed, 1 skipped in <t>s` (the route guard walk finds `GET /hymnals` behind `require_church`, so `USER_SCOPED` is unchanged); then `FAILED backend/tests/test_openapi_contract.py::test_committed_openapi_matches_the_live_schema` and `1 failed, 2 passed in <t>s`.

- [ ] **Step 6 (agent): Regenerate `openapi.json` and `schema.d.ts`, then typecheck**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git diff --numstat -- frontend/src/lib/api
(cd frontend && npm run typecheck)
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
```

**Expected:** `Wrote <repo>/frontend/src/lib/api/openapi.json`; openapi-typescript prints `src/lib/api/openapi.json → src/lib/api/schema.d.ts`; the numstat is exactly `180	1	frontend/src/lib/api/openapi.json` and `98	0	frontend/src/lib/api/schema.d.ts`; `tsc --noEmit` prints nothing (it fails with `Object literal may only specify known properties` in `src/test/fixtures/index.ts` if the generation step was skipped); `3 passed in <t>s`.

- [ ] **Step 7 (agent): Run both suites**

```bash
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
git status --short
```

**Expected:** `1050 passed, 10 skipped in <t>s`; ` Test Files  55 passed (55)` and `      Tests  356 passed (356)`; then ` M` for `backend/api/main.py`, `backend/api/schemas.py`, `backend/tests/test_api_app.py`, `backend/tests/test_api_church_profile.py`, `backend/tests/test_api_churches.py`, `backend/tests/test_api_invites.py`, `backend/tests/test_api_me.py`, `backend/usecases/church_profile.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`, `frontend/src/test/fixtures/index.ts`, and `??` for `backend/api/routes/hymnals.py`, `backend/tests/test_api_hymnals.py`, `backend/usecases/hymns.py`.

- [ ] **Step 8 (agent): Commit**

```bash
git add backend/api/main.py backend/api/schemas.py backend/api/routes/hymnals.py backend/usecases/hymns.py \
        backend/usecases/church_profile.py backend/tests/test_api_app.py backend/tests/test_api_church_profile.py \
        backend/tests/test_api_churches.py backend/tests/test_api_invites.py backend/tests/test_api_me.py \
        backend/tests/test_api_hymnals.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts \
        frontend/src/test/fixtures/index.ts
git commit -m "API: GET /hymnals and the church's default and effective hymnal (S API rows 1 and 5, Backend 3.1-3.2; AC1, AC2)" -m "usecases.hymns.resolve_default_hymnal reads settings.default_hymnal (a
non-blank string, verbatim) and the church's hymnal codes: the effective
hymnal is the stored code when the church has it, else the alphabetically
first, else null. GET /hymnals lists the codes with hymn and scripture-
reference counts; GET /church returns the same two values from the same
function, in one session (clarification 12). The /church exact-body tests
gain the fields; the frontend's churchProfile() fixture gains them because
the regenerated type requires them (clarification 13).

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 9 (controller): Review checkpoint and backup push**

Check `GET /hymnals` against S's `HymnalListOut` field for field, that `test_route_guards.py` needed no allowlist change, and that the OpenAPI diff adds `/hymnals`, `HymnalOut`, `HymnalListOut` and the two `ChurchProfileOut` properties and nothing else. Push the backup.

Counts after Task 8: backend **1050 passed, 10 skipped**; frontend **356 in 55 files**.

### Task 9: `GET /hymns`, the `HymnOut` read model and GZip (S API row 2, Models `HymnOut`, API notes "ordering" and `q`, Backend 1 row `api/main.py`, 3.3, 3.8 "Read"; F §2.5 as amended; Testing `test_api_hymns.py`, GZip, postgres; AC1, AC8, AC16, AC20; clarifications 11, 22, 25)

This task adds the one hymn read model and the list route. `usecases.hymns.HymnView` carries `HymnOut`'s fields; `hymn_view(record, *, usage, prefer_before_year)` strips the title (`""` for NULL), keeps the link verbatim, normalizes the themes, looks up `recent_use_on` by `usage_key` and computes `newer_than_preferred` with the church's merged rubric. `list_hymns_page` reads the page, the usage window (only when a date is given) and the rubric in one session. `GET /hymns` in the new `backend/api/routes/hymns.py` returns `Page[HymnOut]`. `GZipMiddleware(minimum_size=1024)` is added first in `create_app`, so it is innermost (F §2.5 as amended), and the ops middleware-order test now expects CORS, RequestId, UnhandledError, GZip.

**Decisions recorded in this task:**
- **T9-1 (clarification 11).** `recent_for_date` is slice 2's strict `IsoDate`.
- **T9-2.** The rubric read uses `merge_rubric`, so an invalid stored rubric (`{"prefer_before_year": "x"}`) gives the default 1970 and a 200 (S 3.8).
- **T9-3 (clarification 22).** The GZip test is in `test_api_hymns.py`; responses under 1024 bytes are not compressed.

**Files:**
- Create: `backend/api/routes/hymns.py`
- Modify: `backend/usecases/hymns.py` (docstring, imports; `HymnView`, `HymnPage`, `church_rubric`, `hymn_view`, `list_hymns_page` appended)
- Modify: `backend/api/main.py` (the GZip import; the middleware comment and `add_middleware(GZipMiddleware, ...)`; mount `hymns.router`)
- Modify (tests): `backend/tests/test_api_app.py` (map), `backend/tests/test_middleware.py` (the order test)
- Test: `backend/tests/test_api_hymns.py` (new; 10 tests and 1 Postgres test)
- Modify (generated): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes: Task 6's `query_hymns`, `HymnRecord`; Task 7's `usage_near`; Task 5's `parse_themes`, `usage_key`; Task 6's `is_newer_than_preferred`; `repos.churches.get_church_rubric_overrides(..., session=)`; `service_rubric.merge_rubric`; `api.schemas.IsoDate`, `Page`.
- Produces (later users: Tasks 10, 13; slices 3b, 5a, 6a):
  - `usecases.hymns.HymnView(id, hymnal, title, number, link, scripture_refs, themes, recent_use_on, text_year, hymnal_count, newer_than_preferred)`; `HymnPage(items, total, limit, offset)`; `church_rubric(church_id, session) -> dict`; `hymn_view(record, *, usage, prefer_before_year) -> HymnView`; `list_hymns_page(church_id, *, hymnal, q, limit, offset, recent_for_date) -> HymnPage`.
  - `api.routes.hymns.HymnOut` and `hymn_out(view)`; `GET /hymns?hymnal=&q=&limit=&offset=&recent_for_date=` → `Page[HymnOut]`.
  - `create_app().user_middleware` classes, outermost first: `CORSMiddleware`, `RequestIdMiddleware`, `UnhandledErrorMiddleware`, `GZipMiddleware`.

- [ ] **Step 1 (agent): Confirm Task 8's count**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `1050 passed, 10 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `backend/tests/test_api_app.py`, replace:**

````python
        ("/hymnals", "get"): {"401", "403", "422", "503"},
    }
````

**with:**

````python
        ("/hymnals", "get"): {"401", "403", "422", "503"},
        ("/hymns", "get"): {"401", "403", "422", "503"},
    }
````

**Create `backend/tests/test_api_hymns.py`:**

````python
"""GET /hymns (slice 3 spec, API row 2, Models `HymnOut`, API notes "ordering"
and `q`, Backend 3.3; Testing `test_api_hymns.py`, GZip, postgres; AC1, AC8,
AC16, AC20). Includes the `HymnOut` mapping test that 6b's port ledger names
for Streamlit's hymn_display_from_flat."""
import uuid

import pytest

from api import settings as settings_mod
from db import session_scope
from db.models import Church, Hymn, HymnUsage, User
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
ALLOWED_ORIGIN = "https://church.example.app"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def add(church_id, title, number=None, hymnal="GG2013", **columns):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number, **columns)
        s.add(row)
        s.flush()
        return str(row.id)


def get(client, church_id, email=EMAIL, **params):
    r = client.get("/hymns", params=params, headers=church_headers(email, church_id))
    assert r.status_code == 200, r.text
    return r.json()


def listed(body):
    return [(h["hymnal"], h["number"], h["title"]) for h in body["items"]]


def test_ordering_is_hymnal_number_nulls_last_title_id(client, church):
    add(church, "Zion", 5, hymnal="PH1990")
    add(church, "b no number")
    add(church, "Holy", 2)
    add(church, "A no number")
    add(church, "Abide", 10)
    body = get(client, church, limit=2000)
    assert listed(body) == [("GG2013", 2, "Holy"), ("GG2013", 10, "Abide"), ("GG2013", None, "A no number"),
                            ("GG2013", None, "b no number"), ("PH1990", 5, "Zion")]
    assert (body["total"], body["limit"], body["offset"]) == (5, 2000, 0)


def test_hymnal_filter_unknown_code_and_a_code_off_the_pattern(client, church):
    add(church, "Holy", 1)
    add(church, "Doxology", 1, hymnal="PH 1990")          # breaks HymnalCode's pattern
    assert listed(get(client, church, hymnal="PH 1990")) == [("PH 1990", 1, "Doxology")]
    assert get(client, church, hymnal="UNKNOWN") == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_q_matches_number_or_title_with_percent_and_underscore_escaped(client, church):
    add(church, "Joy to the World", 134)
    add(church, "Psalm 134", 900)
    add(church, "100% Sure", 1)
    add(church, "snake_case", 2)
    add(church, "snakeXcase", 3)
    assert {h["number"] for h in get(client, church, q="134")["items"]} == {134, 900}
    assert [h["title"] for h in get(client, church, q="JOY")["items"]] == ["Joy to the World"]
    assert [h["title"] for h in get(client, church, q="100%")["items"]] == ["100% Sure"]
    assert [h["title"] for h in get(client, church, q="e_c")["items"]] == ["snake_case"]


def test_a_30_digit_q_is_200_and_a_6_digit_q_still_matches_numbers(client, church):
    add(church, "Six digits", 123456)
    assert get(client, church, q="9" * 30)["total"] == 0          # the title branch only: no OverflowError
    assert [h["number"] for h in get(client, church, q="123456")["items"]] == [123456]


def test_limit_offset_and_total(client, church):
    for n in range(1, 8):
        add(church, f"Hymn {n}", n)
    assert get(client, church, limit=2000)["total"] == 7
    page = get(client, church, limit=3, offset=3)
    assert ([h["number"] for h in page["items"]], page["total"]) == ([4, 5, 6], 7)
    r = client.get("/hymns", params={"limit": 2001}, headers=church_headers(EMAIL, church))
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["message"], r.json()["error"]["fields"]) == (
        "The request was not valid.", {"limit": "Not a valid value."})
    for bad in ({"limit": 0}, {"offset": -1}, {"recent_for_date": "2026-10-4"},
                {"recent_for_date": "2026-02-30"}, {"q": "x" * 101}, {"hymnal": "H" * 21}):
        r = client.get("/hymns", params=bad, headers=church_headers(EMAIL, church))
        assert r.status_code == 422, (bad, r.text)
        assert r.json()["error"]["fields"], bad


def test_recent_for_date_sets_recent_use_on_and_tolerates_bad_stored_dates(client, church):
    add(church, "Come, Thou Almighty King", 403)
    add(church, "Holy", 1)
    with session_scope() as s:
        for date_iso, title in (("2026-09-27", "come, thou almighty KING"), ("2026-10-1", "Holy"),
                                ("", "Holy"), ("2026-08-02T10:00:00.000-05:00", "Holy")):
            s.add(HymnUsage(church_id=church, date_iso=date_iso, hymn_number=None, hymn_title=title))
    body = get(client, church, recent_for_date="2026-10-04")
    assert {h["title"]: h["recent_use_on"] for h in body["items"]} == {
        "Come, Thou Almighty King": "2026-09-27", "Holy": "2026-08-02"}
    assert all(h["recent_use_on"] is None for h in get(client, church)["items"])


def test_hymn_out_mapping(client, church):
    """Port-ledger target for Streamlit's hymn_display_from_flat (S Testing)."""
    add(church, "  Amazing Grace  ", 378, scripture_refs="Eph 2:8",
        theme='{Grace,"Call to Worship"}', hymnary_link="javascript:alert(1)")
    add(church, None, None)
    items = get(client, church)["items"]
    grace = items[0]
    assert grace == {
        "id": grace["id"], "hymnal": "GG2013", "title": "Amazing Grace", "number": 378,
        "link": "javascript:alert(1)",                   # verbatim: the client decides what is safe
        "scripture_refs": "Eph 2:8", "themes": ["Grace", "Call to Worship"], "recent_use_on": None,
        "text_year": None, "hymnal_count": None, "newer_than_preferred": False,
    }
    blank = items[1]
    assert (blank["title"], blank["number"], blank["themes"], blank["link"]) == ("", None, [], None)


def test_newer_than_preferred_follows_the_church_rubric(client, church):
    add(church, "Newer", 1, text_year=1985, hymnal_count=40)
    add(church, "Older", 2, text_year=1826, hymnal_count=1322)
    add(church, "Unknown", 3)

    def flags():
        return {h["title"]: (h["text_year"], h["hymnal_count"], h["newer_than_preferred"])
                for h in get(client, church)["items"]}

    assert flags() == {"Newer": (1985, 40, True), "Older": (1826, 1322, False),
                       "Unknown": (None, None, False)}
    churches.update_church_rubric(church, {"prefer_before_year": 1800})
    assert flags()["Older"] == (1826, 1322, True)
    stored = churches.get_church(church)["settings"]
    churches.update_church(church, settings={**stored, "rubric": {"prefer_before_year": "x"}})
    assert flags()["Newer"][2] is True and flags()["Older"][2] is False     # invalid: the default 1970


def test_isolation_and_every_role(client, isolation_world, make_user):
    world = isolation_world
    add(world.church_a, "A's hymn", 1)
    add(world.church_b, "B's hymn", 1)
    assert_church_isolated(client, "GET", "/hymns", world=world)
    assert [h["title"] for h in get(client, world.church_a, email=world.a)["items"]] == ["A's hymn"]
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        assert get(client, world.church_a, email=email)["total"] == 1
    assert client.get("/hymns").status_code == 401


def test_a_whole_hymnal_is_gzipped_with_cors_and_request_id(tmp_db, church, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    try:
        client = make_api_client()
        for n in range(1, 301):
            add(church, f"A long enough hymn title number {n}", n, scripture_refs="Psalm 23")
        r = client.get("/hymns", params={"limit": 2000},
                       headers={**church_headers(EMAIL, church), "Accept-Encoding": "gzip",
                                "Origin": ALLOWED_ORIGIN})
        assert r.status_code == 200
        assert r.headers["content-encoding"] == "gzip"
        assert r.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
        assert r.headers["x-request-id"]
        assert r.json()["total"] == 300                          # the client decoded it
        small = client.get("/hymns", params={"limit": 1}, headers={**church_headers(EMAIL, church),
                                                                  "Accept-Encoding": "gzip"})
        assert "content-encoding" not in small.headers           # under 1024 bytes
    finally:
        settings_mod.get_settings.cache_clear()


@pytest.mark.postgres
def test_ordering_and_q_escaping_on_postgres(pg_db):
    user_id, church_id = uuid.uuid4(), uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=user_id, email=EMAIL))
        s.add(Church(id=church_id, name="PG", timezone="America/New_York", settings={}))
    add_membership(user_id, church_id, "owner")
    add(church_id, "b no number")
    add(church_id, "Holy", 2)
    add(church_id, "A no number")
    add(church_id, "100% Sure", 1)
    add(church_id, "100 Sure", 3)
    client = make_api_client()
    assert client.get("/me", headers=auth_headers(EMAIL)).status_code == 200
    body = get(client, church_id, limit=2000)
    assert listed(body) == [("GG2013", 1, "100% Sure"), ("GG2013", 2, "Holy"), ("GG2013", 3, "100 Sure"),
                            ("GG2013", None, "A no number"), ("GG2013", None, "b no number")]
    assert [h["title"] for h in get(client, church_id, q="100%")["items"]] == ["100% Sure"]
    assert get(client, church_id, q="9" * 30)["total"] == 0
````

**In `backend/tests/test_middleware.py`, replace:**

````python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
````

**with:**

````python
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.testclient import TestClient
````

**In `backend/tests/test_middleware.py`, replace:**

````python
        asyncio.run(UnhandledErrorMiddleware(app)(scope, receive, send))
    assert [m["type"] for m in sent] == ["http.response.start"]


def test_middleware_order_is_cors_then_request_id_then_unhandled_error():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 appends GZip innermost).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware,
    ]


# --- CORS header lists (F §1.10) and no trailing-slash redirect (F §1.1) --------
````

**with:**

````python
        asyncio.run(UnhandledErrorMiddleware(app)(scope, receive, send))
    assert [m["type"] for m in sent] == ["http.response.start"]


def test_middleware_order_is_cors_then_request_id_then_unhandled_error_then_gzip():
    # Starlette makes the last middleware added the outermost; user_middleware
    # lists them outermost first (F §2.5; slice 3 added GZip innermost).
    app = create_app()
    assert [m.cls for m in app.user_middleware] == [
        CORSMiddleware, RequestIdMiddleware, UnhandledErrorMiddleware, GZipMiddleware,
    ]


# --- CORS header lists (F §1.10) and no trailing-slash redirect (F §1.1) --------
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymns.py backend/tests/test_api_app.py backend/tests/test_middleware.py 2>&1 | grep -E "^FAILED|passed|failed" | cut -c1-110
```

**Expected:**

```
FAILED backend/tests/test_api_app.py::test_routes_document_the_error_body - K...
FAILED backend/tests/test_api_hymns.py::test_ordering_is_hymnal_number_nulls_last_title_id
FAILED backend/tests/test_api_hymns.py::test_hymnal_filter_unknown_code_and_a_code_off_the_pattern
FAILED backend/tests/test_api_hymns.py::test_q_matches_number_or_title_with_percent_and_underscore_escaped
FAILED backend/tests/test_api_hymns.py::test_a_30_digit_q_is_200_and_a_6_digit_q_still_matches_numbers
FAILED backend/tests/test_api_hymns.py::test_limit_offset_and_total - Asserti...
FAILED backend/tests/test_api_hymns.py::test_recent_for_date_sets_recent_use_on_and_tolerates_bad_stored_dates
FAILED backend/tests/test_api_hymns.py::test_hymn_out_mapping - AssertionErro...
FAILED backend/tests/test_api_hymns.py::test_newer_than_preferred_follows_the_church_rubric
FAILED backend/tests/test_api_hymns.py::test_isolation_and_every_role - Asser...
FAILED backend/tests/test_api_hymns.py::test_a_whole_hymnal_is_gzipped_with_cors_and_request_id
FAILED backend/tests/test_middleware.py::test_middleware_order_is_cors_then_request_id_then_unhandled_error_then_gzip
12 failed, 57 passed, 2 skipped in <t>s
```

(`/hymns` is a 404; the order test sees three middlewares.)

- [ ] **Step 4 (agent): Write the read model, the route and the middleware**

**In `backend/api/main.py`, replace:**

````python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import install_error_handlers
````

**with:**

````python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api.errors import install_error_handlers
````

**In `backend/api/main.py`, replace:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import (churches, health, hymnals, invites, lectionary, me, reference, rubric,
                        scripture)
````

**with:**

````python
from api.middleware import RequestIdMiddleware, UnhandledErrorMiddleware
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, me, reference, rubric,
                        scripture)
````

**In `backend/api/main.py`, replace:**

````python
    # The last middleware added is the outermost: CORS → RequestId → UnhandledError
    # (F §2.5), so CORS decorates the 500s that UnhandledError produces.
    app.add_middleware(UnhandledErrorMiddleware)
````

**with:**

````python
    # The last middleware added is the outermost: CORS → RequestId → UnhandledError
    # → GZip (F §2.5), so CORS decorates the 500s that UnhandledError produces, and
    # GZip (slice 3; GET /hymns?limit=2000 is ~200 KB of JSON) is innermost.
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(UnhandledErrorMiddleware)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(hymnals.router)
    return app
````

**with:**

````python
    app.include_router(hymnals.router)
    app.include_router(hymns.router)
    return app
````

**Create `backend/api/routes/hymns.py`:**

````python
"""The Hymns step's church-scoped routes (slice 3 spec, API; Backend 4).
Plain `def` routes that each make one usecase call with church.id only
(F §1.2 rule 1, §2.2.1). Any member may call them."""
import uuid
from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.deps import ActiveChurch, require_church
from api.errors import error_responses
from api.schemas import IsoDate, Page
from usecases import hymns

router = APIRouter()


class HymnOut(BaseModel):
    id: uuid.UUID
    hymnal: str
    title: str                          # stripped; "" when NULL
    number: Optional[int]
    link: Optional[str]                 # hymnary_link verbatim; the client renders it only via safeHttpsUrl
    scripture_refs: Optional[str]
    themes: list[str]                   # hymn_search.parse_themes(theme)
    recent_use_on: Optional[date]       # nearest usage date in the recent window; null when no date given
    text_year: Optional[int]            # the year the words were written; null = unknown
    hymnal_count: Optional[int]         # hymnals that include the text; null = unknown
    newer_than_preferred: bool          # text_year is not null and >= the rubric's prefer_before_year


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
def list_hymns(
    church: ActiveChurch = Depends(require_church),
    hymnal: Optional[str] = Query(None, max_length=20),
    q: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    recent_for_date: Optional[IsoDate] = Query(None),
) -> Page[HymnOut]:
    """Ordered by hymnal, number (nulls last), title, id. `q` of 1-6 digits also
    matches the number. An unknown hymnal is an empty page."""
    page = hymns.list_hymns_page(church.id, hymnal=hymnal, q=q, limit=limit, offset=offset,
                                 recent_for_date=recent_for_date)
    return Page[HymnOut](items=[hymn_out(v) for v in page.items], total=page.total,
                         limit=page.limit, offset=page.offset)
````

**In `backend/usecases/hymns.py`, replace:**

````python
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
````

**with:**

````python
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.
- list_hymns_page: GET /hymns, each hymn as a HymnView with its recent use
  and the rubric's newer-than-preferred flag.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
````

**In `backend/usecases/hymns.py`, replace:**

````python
from dataclasses import dataclass
from typing import Any, Optional
````

**with:**

````python
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional
````

**In `backend/usecases/hymns.py`, replace:**

````python
from typing import Any, Optional

from sqlalchemy.orm import Session

from db import session_scope
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary


@dataclass(frozen=True)
class DefaultHymnal:
````

**with:**

````python
from typing import Any, Optional

from sqlalchemy.orm import Session

import hymn_usage
from db import session_scope
from hymn_ranking import is_newer_than_preferred
from hymn_search import parse_themes, usage_key
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary, HymnRecord
from service_rubric import merge_rubric


@dataclass(frozen=True)
class DefaultHymnal:
````

**Append to `backend/usecases/hymns.py`:**

````python


@dataclass(frozen=True)
class HymnView:
    """HymnOut's fields (S API Models): one read model for every route that returns hymns."""

    id: uuid.UUID
    hymnal: str
    title: str                         # stripped; "" when NULL
    number: Optional[int]
    link: Optional[str]                # hymnary_link verbatim; the client renders it only via safeHttpsUrl
    scripture_refs: Optional[str]
    themes: list[str]
    recent_use_on: Optional[date]      # the usage date nearest the service date; None without a date
    text_year: Optional[int]
    hymnal_count: Optional[int]
    newer_than_preferred: bool         # text_year known and >= the rubric's prefer_before_year


@dataclass(frozen=True)
class HymnPage:
    items: list[HymnView]
    total: int
    limit: int
    offset: int


def church_rubric(church_id: uuid.UUID, session: Session) -> dict:
    """The church's merged rubric, read fresh (S Backend 3.8). merge_rubric
    falls back to the defaults for any invalid stored value."""
    return merge_rubric(churches.get_church_rubric_overrides(church_id, session=session))


def hymn_view(record: HymnRecord, *, usage: Optional[dict[str, date]],
              prefer_before_year: int) -> HymnView:
    return HymnView(
        id=record.id,
        hymnal=record.hymnal,
        title=(record.title or "").strip(),
        number=record.number,
        link=record.link,
        scripture_refs=record.scripture_refs,
        themes=parse_themes(record.theme),
        recent_use_on=usage.get(usage_key(record.title)) if usage is not None else None,
        text_year=record.text_year,
        hymnal_count=record.hymnal_count,
        newer_than_preferred=is_newer_than_preferred(record.text_year, prefer_before_year),
    )


def list_hymns_page(church_id: uuid.UUID, *, hymnal: Optional[str], q: Optional[str], limit: int,
                    offset: int, recent_for_date: Optional[date]) -> HymnPage:
    """S Backend 3.3: one session for the page, the usage window and the rubric."""
    with session_scope() as s:
        records, total = hymn_repo.query_hymns(church_id, hymnal=hymnal, q=q, limit=limit,
                                               offset=offset, session=s)
        usage = (hymn_usage.usage_near(church_id, recent_for_date, session=s)
                 if recent_for_date is not None else None)
        year = church_rubric(church_id, s)["prefer_before_year"]
    return HymnPage(items=[hymn_view(r, usage=usage, prefer_before_year=year) for r in records],
                    total=total, limit=limit, offset=offset)
````

- [ ] **Step 5 (agent): Run the tests; regenerate and typecheck; run the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymns.py backend/tests/test_api_app.py backend/tests/test_middleware.py backend/tests/test_route_guards.py 2>&1 | tail -1
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git diff --numstat -- frontend/src/lib/api
(cd frontend && npm run typecheck)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `74 passed, 2 skipped in <t>s` (the skips: this task's Postgres test and `test_api_app.py`'s); the generation lines; numstat exactly `308	0	frontend/src/lib/api/openapi.json` and `125	0	frontend/src/lib/api/schema.d.ts`; `tsc` prints nothing; `1060 passed, 11 skipped in <t>s`; then ` M` for `backend/api/main.py`, `backend/tests/test_api_app.py`, `backend/tests/test_middleware.py`, `backend/usecases/hymns.py`, the two generated files, and `??` for `backend/api/routes/hymns.py`, `backend/tests/test_api_hymns.py`. With a local throwaway Postgres, `-m postgres backend/tests/test_api_hymns.py` gives `1 passed, 10 deselected`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/api/main.py backend/api/routes/hymns.py backend/usecases/hymns.py backend/tests/test_api_app.py \
        backend/tests/test_api_hymns.py backend/tests/test_middleware.py \
        frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: GET /hymns with the HymnOut read model, and GZip innermost (S API row 2, Backend 3.3, 3.8; F §2.5; AC1, AC16, AC20)" -m "GET /hymns pages the church's hymns (hymnal, number nulls last, title, id;
q of 1-6 digits also matches the number; % and _ escaped; limit up to 2000)
as HymnOut: title stripped, link verbatim, themes normalized, recent_use_on
around recent_for_date (strict YYYY-MM-DD), and text_year, hymnal_count and
newer_than_preferred from the church's merged rubric, read in the same
session. GZipMiddleware(minimum_size=1024) is innermost, so a whole hymnal
is gzipped and still carries CORS and X-Request-Id; the ops order test now
expects CORS, RequestId, UnhandledError, GZip.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check `HymnOut` against S's model field for field, that `test_hymn_out_mapping` is named as 6b's port-ledger target in its module docstring, and that the middleware order in `create_app` is GZip, UnhandledError, RequestId, CORS (added in that order). Push the backup.

Counts after Task 9: backend **1060 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 10: `POST /hymns/scripture-matches` (S API row 3, Models `ScriptureMatchIn`/`HymnMatchOut`/`ScriptureMatchesOut`, API notes "Hymnal resolution", Backend 3.5; Testing `test_api_hymn_matches.py`; AC1, AC3, AC8, AC20; clarifications 10, 24)

This task adds the matches usecase and route. `scripture_matches` trims each ref and splits it on " or " (`clean_refs`); none left is the 422 "Enter at least one scripture reference." on `fields.refs`. `selected_hymnal` resolves `null` to the effective hymnal and refuses a code the church lacks with one message whatever the reason; a church with no hymns answers 200 with no items. In one session it reads the hymnal's records, the usage window when a date is given and the rubric; then `match_hymns` runs and each match becomes a `HymnMatchView` (a `HymnView` plus `strength` and `matched_refs`). One DEBUG line per call counts the parsed and unparsed references and the hymns with unparsed `scripture_refs` (clarification 29).

**Files:**
- Modify: `backend/usecases/hymns.py` (docstring; imports and the module `logger`; the two messages; `HymnMatchView`, `ScriptureMatches`, `clean_refs`, `selected_hymnal`, `scripture_matches` appended)
- Modify: `backend/api/routes/hymns.py` (imports; `ScriptureMatchIn`, `HymnMatchOut`, `ScriptureMatchesOut`; the route appended)
- Modify (tests): `backend/tests/test_api_app.py` (map)
- Test: `backend/tests/test_api_hymn_matches.py` (new)
- Modify (generated): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes: Task 5's `match_hymns`; Task 6's `list_hymnal_records`, `hymnal_summaries`; Task 8's `_resolve`, `_settings`; Task 9's `HymnView`, `hymn_view`, `church_rubric`, `HymnOut`; `scripture_refs.split_alternatives`; `domain_errors.InvalidInput`.
- Produces (later users: Task 13; slice 3b):
  - `usecases.hymns.REFS_MESSAGE`, `HYMNAL_MESSAGE`; `HymnMatchView(HymnView + strength, matched_refs)`; `ScriptureMatches(hymnal, refs_used, unparsed_refs, total_matched, items)`; `clean_refs(refs) -> list[str]`; `selected_hymnal(church_id, requested, session) -> str | None`; `scripture_matches(church_id, *, refs, hymnal, recent_for_date, limit_per_ref, max_results) -> ScriptureMatches`.
  - `POST /hymns/scripture-matches` (`ScriptureMatchIn` → `ScriptureMatchesOut`).

- [ ] **Step 1 (agent): Confirm Task 9's count**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `1060 passed, 11 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `backend/tests/test_api_app.py`, replace:**

````python
        ("/hymns", "get"): {"401", "403", "422", "503"},
    }
````

**with:**

````python
        ("/hymns", "get"): {"401", "403", "422", "503"},
        ("/hymns/scripture-matches", "post"): {"401", "403", "422", "503"},
    }
````

**Create `backend/tests/test_api_hymn_matches.py`:**

````python
"""POST /hymns/scripture-matches (slice 3 spec, API row 3, Models
`ScriptureMatchIn`/`HymnMatchOut`/`ScriptureMatchesOut`, API notes "Hymnal
resolution", Backend 3.5; Testing `test_api_hymn_matches.py`; AC1, AC3, AC8,
AC20)."""
import logging

import pytest

from db import session_scope
from db.models import Hymn, HymnUsage
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def add(church_id, title, refs, number=None, hymnal="GG2013", **columns):
    with session_scope() as s:
        s.add(Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number,
                   scripture_refs=refs, **columns))


def post(client, church_id, body, email=EMAIL, status=200):
    r = client.post("/hymns/scripture-matches", json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_happy_path_grouped_by_strength(client, church):
    add(church, "Transfiguration Hymn", "Matt 17:1-8", 10)
    add(church, "Same Chapter", "Mark 1:1-8", 11)
    add(church, "Baptism Hymn", "Mark 1:9", 12)
    add(church, "Over-match Bait", "Mark 10:45", 13)
    add(church, "Emmaus", "Luke 24:13-35", 14)
    body = post(client, church, {"refs": [" Mark 1:9-15 ", "", "Matthew 17 OR Luke 24:30"]})
    assert body["hymnal"] == "GG2013"
    assert body["refs_used"] == ["Mark 1:9-15", "Matthew 17", "Luke 24:30"]
    assert body["unparsed_refs"] == []
    assert body["total_matched"] == 4
    assert [(h["title"], h["strength"], h["matched_refs"]) for h in body["items"]] == [
        ("Baptism Hymn", "passage", ["Mark 1:9-15"]),
        ("Transfiguration Hymn", "passage", ["Matthew 17"]),
        ("Emmaus", "passage", ["Luke 24:30"]),
        ("Same Chapter", "chapter", ["Mark 1:9-15"]),
    ]
    assert set(body["items"][0]) >= {"id", "number", "link", "themes", "recent_use_on",
                                     "text_year", "hymnal_count", "newer_than_preferred"}


def test_refs_blank_after_trimming_is_422(client, church):
    add(church, "Any", "John 3:16")
    for refs in ([], ["", "   "], [" or "]):
        error = post(client, church, {"refs": refs}, status=422)["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "Enter at least one scripture reference.")
        assert error["fields"] == {"refs": "Enter at least one scripture reference."}


def test_a_hymnal_the_church_lacks_is_422_with_one_message(client, isolation_world):
    world = isolation_world
    add(world.church_a, "A", "John 3:16")
    add(world.church_b, "B", "John 3:16", hymnal="BONLY")
    for code in ("BONLY", "NOWHERE", ""):
        error = post(client, world.church_a, {"refs": ["John 3"], "hymnal": code},
                     email=world.a, status=422)["error"]
        assert (error["message"], error["fields"]) == (HYMNAL_MESSAGE, {"hymnal": HYMNAL_MESSAGE}), code


def test_unreadable_references_are_reported(client, church):
    add(church, "Mountain", "Matthew 17:1-9")
    body = post(client, church, {"refs": ["Transfiguration", "Matthew 17"]})
    assert body["unparsed_refs"] == ["Transfiguration"]
    assert [h["title"] for h in body["items"]] == ["Mountain"]


def test_recent_use_on_is_set_for_the_date(client, church):
    add(church, "Recent", "Psalm 23")
    add(church, "Not recent", "Psalm 23:1")
    with session_scope() as s:
        s.add(HymnUsage(church_id=church, date_iso="2026-09-20", hymn_number=5, hymn_title="recent"))
    body = post(client, church, {"refs": ["Psalm 23"], "recent_for_date": "2026-10-04"})
    assert {h["title"]: h["recent_use_on"] for h in body["items"]} == {
        "Recent": "2026-09-20", "Not recent": None}
    assert all(h["recent_use_on"] is None for h in post(client, church, {"refs": ["Psalm 23"]})["items"])


def test_one_debug_line_counts_parsed_and_unparsed(client, church, caplog):
    # S Risks, "Unknown scripture_refs formats": counts only, never a title or a reference.
    add(church, "Readable", "John 3:16")
    add(church, "Odd", "Genesis 1.1; see the preface")
    caplog.set_level(logging.DEBUG, logger="usecases.hymns")
    post(client, church, {"refs": ["John 3", "Transfiguration"]})
    lines = [r.getMessage() for r in caplog.records if r.getMessage().startswith("hymn_matches")]
    assert lines == ["hymn_matches refs=2 refs_unparsed=1 hymns=2 hymns_with_unparsed=1 matched=1"]


def test_an_empty_church_hymnal_is_200_and_empty(client, church):
    assert post(client, church, {"refs": ["John 3:16"]}) == {
        "hymnal": None, "refs_used": ["John 3:16"], "unparsed_refs": [], "total_matched": 0, "items": []}


def test_null_hymnal_is_the_effective_one_and_a_named_one_is_used(client, church):
    add(church, "Green", "John 3:16", hymnal="GG2013")
    add(church, "Blue", "John 3:16", hymnal="PH1990")
    stored = churches.get_church(church)["settings"] or {}
    churches.update_church(church, settings={**stored, "default_hymnal": "PH1990"})
    assert [h["title"] for h in post(client, church, {"refs": ["John 3"]})["items"]] == ["Blue"]
    body = post(client, church, {"refs": ["John 3"], "hymnal": "GG2013"})
    assert (body["hymnal"], [h["title"] for h in body["items"]]) == ("GG2013", ["Green"])


def test_matches_carry_the_facts_and_the_newer_flag(client, church):
    add(church, "Newer", "John 3:16", text_year=1985, hymnal_count=40)
    add(church, "Older", "John 3:17", text_year=1826, hymnal_count=1322)
    items = post(client, church, {"refs": ["John 3"]})["items"]
    assert {h["title"]: (h["text_year"], h["hymnal_count"], h["newer_than_preferred"]) for h in items} == {
        "Newer": (1985, 40, True), "Older": (1826, 1322, False)}


def test_body_limits_and_extra_fields_are_422(client, church):
    for body in ({"refs": ["John 3"], "extra": 1}, {"refs": ["x" * 201]}, {"refs": ["John 3"] * 21},
                 {"refs": ["John 3"], "hymnal": "H" * 21}, {"refs": ["John 3"], "limit_per_ref": 0},
                 {"refs": ["John 3"], "max_results": 101}, {"refs": ["John 3"], "recent_for_date": "2026-10-4"}):
        error = post(client, church, body, status=422)["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid."), body


def test_isolation_and_every_role(client, isolation_world, make_user):
    world = isolation_world
    add(world.church_a, "A's hymn", "John 3:16")
    add(world.church_b, "B's hymn", "John 3:16")
    assert_church_isolated(client, "POST", "/hymns/scripture-matches", world=world, json={"refs": ["John 3"]})
    assert [h["title"] for h in post(client, world.church_a, {"refs": ["John 3"]}, email=world.a)["items"]] == [
        "A's hymn"]
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        assert post(client, world.church_a, {"refs": ["John 3"]}, email=email)["total_matched"] == 1
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymn_matches.py backend/tests/test_api_app.py 2>&1 | grep -E "^FAILED|passed|failed" | cut -c1-110
```

**Expected:** `FAILED` for `test_api_app.py::test_routes_document_the_error_body` and all eleven tests of `test_api_hymn_matches.py`, then `12 failed, 25 passed, 1 skipped in <t>s` (the route is a 404).

- [ ] **Step 4 (agent): Write the usecase and the route**

**In `backend/api/routes/hymns.py`, replace:**

````python
from dataclasses import asdict
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from api.deps import ActiveChurch, require_church
````

**with:**

````python
from dataclasses import asdict
from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api.deps import ActiveChurch, require_church
````

**In `backend/api/routes/hymns.py`, replace:**

````python
    text_year: Optional[int]            # the year the words were written; null = unknown
    hymnal_count: Optional[int]         # hymnals that include the text; null = unknown
    newer_than_preferred: bool          # text_year is not null and >= the rubric's prefer_before_year


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
````

**with:**

````python
    text_year: Optional[int]            # the year the words were written; null = unknown
    hymnal_count: Optional[int]         # hymnals that include the text; null = unknown
    newer_than_preferred: bool          # text_year is not null and >= the rubric's prefer_before_year


class ScriptureMatchIn(BaseModel):
    """POST /hymns/scripture-matches. Refs blank after trimming are the usecase's
    422 "Enter at least one scripture reference." (fields.refs)."""

    model_config = ConfigDict(extra="forbid")

    refs: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymnal: Optional[Annotated[str, StringConstraints(max_length=20)]] = None   # null = effective_hymnal
    recent_for_date: Optional[IsoDate] = None
    limit_per_ref: int = Field(50, ge=1, le=100)
    max_results: int = Field(20, ge=1, le=100)


class HymnMatchOut(HymnOut):
    strength: Literal["passage", "chapter"]
    matched_refs: list[str]            # the query references (after the " or " split) that matched


class ScriptureMatchesOut(BaseModel):
    hymnal: Optional[str]
    refs_used: list[str]               # trimmed, non-blank, after the " or " split, in order
    unparsed_refs: list[str]           # query refs that could not be read as scripture
    total_matched: int                 # before max_results truncation
    items: list[HymnMatchOut]          # passage tier first, then chapter tier


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
````

**Append to `backend/api/routes/hymns.py`:**

````python


@router.post("/hymns/scripture-matches", response_model=ScriptureMatchesOut,
             responses=error_responses(401, 403, 422, 503))
def scripture_matches(payload: ScriptureMatchIn,
                      church: ActiveChurch = Depends(require_church)) -> ScriptureMatchesOut:
    found = hymns.scripture_matches(church.id, refs=payload.refs, hymnal=payload.hymnal,
                                    recent_for_date=payload.recent_for_date,
                                    limit_per_ref=payload.limit_per_ref, max_results=payload.max_results)
    return ScriptureMatchesOut(hymnal=found.hymnal, refs_used=found.refs_used,
                               unparsed_refs=found.unparsed_refs, total_matched=found.total_matched,
                               items=[HymnMatchOut(**asdict(m)) for m in found.items])
````

**Replace the whole of `backend/usecases/hymns.py` with:**

````python
"""The Hymns step's reads and the AI suggestions (slice 3 spec, Backend 3;
owner decisions 3 and 9; owner answers of 2026-09-29).

- resolve_default_hymnal: the stored default_hymnal and the effective one
  (GET /hymnals and GET /church both use it, so they never disagree).
- hymnal_overview: GET /hymnals.
- list_hymns_page: GET /hymns, each hymn as a HymnView with its recent use
  and the rubric's newer-than-preferred flag.
- scripture_matches: POST /hymns/scripture-matches.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
one session. The layer rules are in usecases/__init__.py: no FastAPI,
Starlette or Streamlit here (test_no_streamlit_in_core.py). Repos are called
through their modules, so a test can patch one function.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session

import hymn_usage
from db import session_scope
from domain_errors import InvalidInput
from hymn_ranking import is_newer_than_preferred
from hymn_search import match_hymns, parse_themes, usage_key
from repos import churches
from repos import hymns as hymn_repo
from repos.hymns import HymnalSummary, HymnRecord
from scripture_refs import parse_refs, split_alternatives
from service_rubric import merge_rubric

logger = logging.getLogger(__name__)


REFS_MESSAGE = "Enter at least one scripture reference."
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."


@dataclass(frozen=True)
class DefaultHymnal:
    default_hymnal: Optional[str]      # settings["default_hymnal"] verbatim, when a non-blank string
    effective_hymnal: Optional[str]    # the default if the church has it, else the first code, else None


@dataclass(frozen=True)
class HymnalOverview:
    items: list[HymnalSummary]
    default_hymnal: Optional[str]
    effective_hymnal: Optional[str]


def _stored_default(settings: Any) -> Optional[str]:
    value = (settings or {}).get("default_hymnal") if isinstance(settings, dict) else None
    return value if isinstance(value, str) and value.strip() else None


def _resolve(settings: Any, codes: list[str]) -> DefaultHymnal:
    stored = _stored_default(settings)
    effective = stored if stored in codes else (codes[0] if codes else None)
    return DefaultHymnal(default_hymnal=stored, effective_hymnal=effective)


def _settings(church_id: uuid.UUID, session: Session) -> Any:
    church = churches.get_church(church_id, session=session)
    return church["settings"] if church else None


def resolve_default_hymnal(church_id: uuid.UUID, *, session: Optional[Session] = None) -> DefaultHymnal:
    """S Backend 3.1: the alphabetical fallback matches Streamlit (app.py:650)."""
    def work(s: Session) -> DefaultHymnal:
        codes = [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=s)]
        return _resolve(_settings(church_id, s), codes)

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def hymnal_overview(church_id: uuid.UUID) -> HymnalOverview:
    """S Backend 3.2: the hymnals (ORDER BY code) and the default, in one session."""
    with session_scope() as s:
        items = hymn_repo.hymnal_summaries(church_id, session=s)
        resolved = _resolve(_settings(church_id, s), [item.code for item in items])
    return HymnalOverview(items=items, default_hymnal=resolved.default_hymnal,
                          effective_hymnal=resolved.effective_hymnal)


@dataclass(frozen=True)
class HymnView:
    """HymnOut's fields (S API Models): one read model for every route that returns hymns."""

    id: uuid.UUID
    hymnal: str
    title: str                         # stripped; "" when NULL
    number: Optional[int]
    link: Optional[str]                # hymnary_link verbatim; the client renders it only via safeHttpsUrl
    scripture_refs: Optional[str]
    themes: list[str]
    recent_use_on: Optional[date]      # the usage date nearest the service date; None without a date
    text_year: Optional[int]
    hymnal_count: Optional[int]
    newer_than_preferred: bool         # text_year known and >= the rubric's prefer_before_year


@dataclass(frozen=True)
class HymnPage:
    items: list[HymnView]
    total: int
    limit: int
    offset: int


def church_rubric(church_id: uuid.UUID, session: Session) -> dict:
    """The church's merged rubric, read fresh (S Backend 3.8). merge_rubric
    falls back to the defaults for any invalid stored value."""
    return merge_rubric(churches.get_church_rubric_overrides(church_id, session=session))


def hymn_view(record: HymnRecord, *, usage: Optional[dict[str, date]],
              prefer_before_year: int) -> HymnView:
    return HymnView(
        id=record.id,
        hymnal=record.hymnal,
        title=(record.title or "").strip(),
        number=record.number,
        link=record.link,
        scripture_refs=record.scripture_refs,
        themes=parse_themes(record.theme),
        recent_use_on=usage.get(usage_key(record.title)) if usage is not None else None,
        text_year=record.text_year,
        hymnal_count=record.hymnal_count,
        newer_than_preferred=is_newer_than_preferred(record.text_year, prefer_before_year),
    )


def list_hymns_page(church_id: uuid.UUID, *, hymnal: Optional[str], q: Optional[str], limit: int,
                    offset: int, recent_for_date: Optional[date]) -> HymnPage:
    """S Backend 3.3: one session for the page, the usage window and the rubric."""
    with session_scope() as s:
        records, total = hymn_repo.query_hymns(church_id, hymnal=hymnal, q=q, limit=limit,
                                               offset=offset, session=s)
        usage = (hymn_usage.usage_near(church_id, recent_for_date, session=s)
                 if recent_for_date is not None else None)
        year = church_rubric(church_id, s)["prefer_before_year"]
    return HymnPage(items=[hymn_view(r, usage=usage, prefer_before_year=year) for r in records],
                    total=total, limit=limit, offset=offset)


@dataclass(frozen=True)
class HymnMatchView(HymnView):
    strength: str                      # "passage" or "chapter"
    matched_refs: list[str]            # the query refs (after the " or " split) that matched


@dataclass(frozen=True)
class ScriptureMatches:
    hymnal: Optional[str]
    refs_used: list[str]
    unparsed_refs: list[str]
    total_matched: int
    items: list[HymnMatchView]


def clean_refs(refs: list[str]) -> list[str]:
    """Trimmed, blanks dropped, each split on " or " (any case), in order."""
    return [alternative for ref in refs for alternative in split_alternatives(ref or "")]


def selected_hymnal(church_id: uuid.UUID, requested: Optional[str], session: Session) -> Optional[str]:
    """None asks for the effective hymnal (None when the church has none). A code
    the church lacks is InvalidInput on `hymnal`, with the same message whether
    it exists in another church or nowhere (S API notes)."""
    codes = [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=session)]
    if requested is None:
        return _resolve(_settings(church_id, session), codes).effective_hymnal
    if requested not in codes:
        raise InvalidInput(HYMNAL_MESSAGE, field="hymnal")
    return requested


def scripture_matches(church_id: uuid.UUID, *, refs: list[str], hymnal: Optional[str],
                      recent_for_date: Optional[date], limit_per_ref: int,
                      max_results: int) -> ScriptureMatches:
    """S Backend 3.5: passage tier first, then chapter; every hymn a HymnView."""
    refs_used = clean_refs(refs)
    if not refs_used:
        raise InvalidInput(REFS_MESSAGE, field="refs")
    with session_scope() as s:
        code = selected_hymnal(church_id, hymnal, s)
        if code is None:
            return ScriptureMatches(hymnal=None, refs_used=refs_used, unparsed_refs=[],
                                    total_matched=0, items=[])
        records = hymn_repo.list_hymnal_records(church_id, code, session=s)
        usage = (hymn_usage.usage_near(church_id, recent_for_date, session=s)
                 if recent_for_date is not None else None)
        year = church_rubric(church_id, s)["prefer_before_year"]
    result = match_hymns(records, refs_used, limit_per_ref=limit_per_ref, max_results=max_results)
    if logger.isEnabledFor(logging.DEBUG):       # counts only (S Risks; clarification 29)
        logger.debug("hymn_matches refs=%d refs_unparsed=%d hymns=%d hymns_with_unparsed=%d matched=%d",
                     len(result.refs_used), len(result.unparsed_refs), len(records),
                     sum(1 for r in records if parse_refs(r.scripture_refs or "").unparsed),
                     result.total_matched)
    items = [HymnMatchView(**asdict(hymn_view(m.record, usage=usage, prefer_before_year=year)),
                           strength=m.strength, matched_refs=list(m.matched_refs))
             for m in result.items]
    return ScriptureMatches(hymnal=code, refs_used=list(result.refs_used),
                            unparsed_refs=list(result.unparsed_refs),
                            total_matched=result.total_matched, items=items)
````

- [ ] **Step 5 (agent): Run the tests; regenerate and typecheck; run the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymn_matches.py backend/tests/test_api_app.py backend/tests/test_route_guards.py 2>&1 | tail -1
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git diff --numstat -- frontend/src/lib/api
(cd frontend && npm run typecheck)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `42 passed, 1 skipped in <t>s`; numstat exactly `333	0	frontend/src/lib/api/openapi.json` and `151	0	frontend/src/lib/api/schema.d.ts`; `tsc` prints nothing; `1071 passed, 11 skipped in <t>s`; then ` M` for `backend/api/routes/hymns.py`, `backend/tests/test_api_app.py`, `backend/usecases/hymns.py`, the two generated files, and `?? backend/tests/test_api_hymn_matches.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/api/routes/hymns.py backend/usecases/hymns.py backend/tests/test_api_app.py \
        backend/tests/test_api_hymn_matches.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: POST /hymns/scripture-matches, tiered passage then chapter (S API row 3, Backend 3.5; decision 9; AC3)" -m "Refs are trimmed and split on ' or '; none left is 422 'Enter at least one
scripture reference.' A null hymnal is the effective one; a code the church
lacks is one 422 message whether it exists elsewhere or nowhere; a church
with no hymns gets an empty 200. Each match is a HymnOut plus strength and
matched_refs, with recent_use_on for the date and the rubric's newer flag.
One DEBUG line per call counts unparsed refs and hymns (clarification 29).

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check the three models against S, the exact messages, and that a B hymnal code in A's request gets the same message as a code that exists nowhere. Push the backup.

Counts after Task 10: backend **1071 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 11: `hymn_suggest.build_candidates`: ranked, capped, padded candidate lists (S Backend 1 row `hymn_suggest.py`, 3.6 step 6, 3.8 "Ranking and cut"; owner decision 3; AC19; clarification 15)

This task starts the pure module `backend/hymn_suggest.py` with the candidate lists. For each slot, the other two slots' current picks are left out first. The response list is `match_hymns` over the eligible hymns with the NT reading's alternatives first (`response_refs`), 30 per reference; the opening and closing lists are the hymns whose themes match `_OPENING_THEMES` / `_CLOSING_THEMES` at word starts (moved here from `worship_service.py`). When ranking has a signal (a known year, or familiarity on and a known count) the list is ranked by the church's rubric and cut with `shortlist(limit=50, reserve=10)`; otherwise the response list is truncated to 50 and the theme lists are sampled evenly to 50. A list with fewer than 15 focused hymns gets an even sample of the rest of the hymnal, ranked, after the focused hymns, up to 40.

**Decisions recorded in this task:**
- **T11-1.** The module's imports already include what Task 12 adds (`json`, `service_rubric`, `InvalidInput`, `UpstreamError`, `normalize_title`); Task 12 uses them.
- **T11-2.** `Candidates.modes` records "ranked" or "sampled" per slot for the logs (S 3.8 "Logs").
- **T11-3.** With no references at all, the response list has no focused hymns and is all pad.

**Files:**
- Create: `backend/hymn_suggest.py`
- Test: `backend/tests/test_hymn_suggest.py` (new; 9 tests here, 15 more in Task 12)

**Interfaces:**
- Consumes: Task 5's `match_hymns`, `evenly_spaced`, `parse_themes`; Task 6's `hymn_ranking` accessors and `HymnRecord`; `scripture_refs.split_alternatives`; `service_rubric.default_rubric`, `merge_rubric` (tests).
- Produces (later users: Tasks 12, 13): constants `SLOTS`, `SLOT_CAP = 50`, `NEWER_RESERVE = 10`, `PAD_BELOW = 15`, `PAD_TO = 40`, `RESPONSE_LIMIT_PER_REF = 30`, `MAX_PROMPT_CHARS = 24_000`, `NT_EXCERPT_CHARS = 1_500`, `MIN_PER_SLOT = 3`, `MAX_PER_SLOT = 5`, `UNUSABLE_MESSAGE`, `PROMPT_TOO_LONG_MESSAGE`, `SYSTEM_MESSAGE`, `INSTRUCTION`; `matches_theme(record, keywords)`; `response_refs(nt_ref, scriptures)`; `Candidates(by_slot, modes)`; `build_candidates(eligible, scriptures, *, nt_ref, current_picks, rubric) -> Candidates`.

- [ ] **Step 1 (agent): Confirm Task 10's count**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `1071 passed, 11 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `backend/tests/test_hymn_suggest.py`:**

````python
"""hymn_suggest: candidates, the prompt, parsing, resolution and the final
slots (slice 3 spec, Backend 3.6 steps 6-9 and 3.8; Testing
`test_hymn_suggest.py` and "Rubric"; owner decision 3; owner answer Q1 of
2026-09-29; AC11, AC19).

The rubric cases port PR #4's test_suggest_hymns.py to the new pipeline
(Task 14 deletes that file with suggest_hymns_for_service)."""
import uuid

import hymn_suggest as hs
from repos.hymns import HymnRecord
from service_rubric import default_rubric

RUBRIC = default_rubric()
NO_PICKS = {"opening": None, "response": None, "closing": None}


def rec(title, number=None, *, theme=None, refs=None, year=None, count=None, hymnal="GG2013"):
    return HymnRecord(id=uuid.uuid5(uuid.NAMESPACE_URL, f"{hymnal}/{number}/{title}"), hymnal=hymnal,
                      title=title, number=number, link=None, scripture_refs=refs, theme=theme,
                      text_year=year, hymnal_count=count)


def rubric_with(**settings):
    rubric = default_rubric()
    rubric.update(settings)
    return rubric


def titles(records):
    return [r.title for r in records]


def build(eligible, scriptures=(), *, nt_ref=None, picks=None, rubric=RUBRIC):
    return hs.build_candidates(eligible, list(scriptures), nt_ref=nt_ref,
                               current_picks=picks or NO_PICKS, rubric=rubric)


# --- T11: build_candidates -------------------------------------------------------------


def test_themes_match_at_word_starts():
    joyful, enjoy = rec("Joyful", 1, theme="joyful praise"), rec("Enjoy", 2, theme="enjoy")
    gathering = rec("Gathering", 3, theme='{"Call to Worship",Gathering}')
    assert hs.matches_theme(joyful, hs._CLOSING_THEMES)        # "joy" matches "joyful" ...
    assert not hs.matches_theme(enjoy, hs._CLOSING_THEMES)     # ... but not "enjoy"
    assert hs.matches_theme(gathering, hs._OPENING_THEMES)
    candidates = build([joyful, enjoy, gathering, rec("Plain", 4, theme="grace")])
    assert titles(candidates.by_slot["closing"][:1]) == ["Joyful"]      # focused, then the pad
    assert titles(candidates.by_slot["opening"][:1]) == ["Gathering"]


def test_a_short_list_is_padded_to_40_with_an_even_sample_in_hymnal_order():
    hymns = [rec(f"Hymn {n}", n) for n in range(1, 201)]
    hymns[99] = rec("Gathering Song", 100, theme="gathering")
    opening = build(hymns).by_slot["opening"]
    assert len(opening) == 40
    assert opening[0].title == "Gathering Song"                 # focused first
    rest = [h for h in hymns if h.title != "Gathering Song"]
    assert opening[1:] == [rest[(i * 199) // 39] for i in range(39)]   # no facts: the plain sample
    assert opening[-1].number > 180                             # not the first 40 (the Advent bias)


def test_response_is_the_passage_tier_then_the_chapter_tier_capped_at_50():
    hymns = [rec(f"Chapter {n}", n, refs="Mark 1:1") for n in range(1, 31)]
    hymns += [rec(f"Passage {n}", 100 + n, refs="John 3:16") for n in range(1, 31)]
    response = build(hymns, ["John 3:14-21", "Mark 1:9"]).by_slot["response"]
    assert len(response) == 50
    assert titles(response[:30]) == [f"Passage {n}" for n in range(1, 31)]
    assert titles(response[30:]) == [f"Chapter {n}" for n in range(1, 21)]


def test_the_nt_reading_leads_the_response_list_and_survives_the_cap():
    hymns = [rec(f"OT {n}", n, refs="Isaiah 6:3") for n in range(1, 31)]
    hymns += [rec(f"Psalm {n}", 100 + n, refs="Psalm 23") for n in range(1, 31)]
    hymns += [rec(f"Gospel {n}", 200 + n, refs="Mark 1:10") for n in range(1, 6)]
    scriptures = ["Isaiah 6:1-8", "Psalm 23", "Romans 8:12-17", "Mark 1:9-15"]
    response = build(hymns, scriptures, nt_ref="Mark 1:9-15").by_slot["response"]
    assert titles(response[:5]) == [f"Gospel {n}" for n in range(1, 6)]
    assert len(response) == 50
    assert hs.response_refs("Mark 1:9-15", scriptures) == [
        "Mark 1:9-15", "Isaiah 6:1-8", "Psalm 23", "Romans 8:12-17"]


def test_a_long_theme_list_without_facts_is_sampled_evenly():
    hymns = [rec(f"Joy {n}", n, theme="joy") for n in range(1, 121)]
    candidates = build(hymns)
    closing = candidates.by_slot["closing"]
    assert len(closing) == 50 and candidates.modes["closing"] == "sampled"
    assert [h.number for h in closing] == [1 + (i * 120) // 50 for i in range(50)]
    assert any(h.number > 80 for h in closing)                  # hymns from the last third


def test_other_slots_picks_are_left_out_and_a_slots_own_pick_stays():
    hymns = [rec(f"Praise {n}", n, theme="gathering, joy", refs="Psalm 23") for n in range(1, 6)]
    picked = hymns[2]
    picks = {"opening": None, "response": picked.id, "closing": None}
    candidates = build(hymns, ["Psalm 23"], picks=picks)
    assert picked in candidates.by_slot["response"]
    assert picked not in candidates.by_slot["opening"]
    assert picked not in candidates.by_slot["closing"]


def test_focused_lists_are_ranked_by_the_rubric():
    hymns = [rec("Newer", 1, theme="joy", year=1995, count=40),
             rec("Unknown", 2, theme="joy"),
             rec("Old rare", 3, theme="joy", year=1850, count=5),
             rec("Old common", 4, theme="joy", year=1840, count=3000),
             rec("Old median", 5, theme="joy", year=1800)]          # unknown count: the median
    closing = build(hymns).by_slot["closing"][:5]
    assert titles(closing) == ["Old common", "Old median", "Old rare", "Unknown", "Newer"]
    unfamiliar = build(hymns, rubric=rubric_with(prefer_familiar=False)).by_slot["closing"][:5]
    assert titles(unfamiliar) == ["Old rare", "Old common", "Old median", "Unknown", "Newer"]
    by_1845 = build(hymns, rubric=rubric_with(prefer_before_year=1845)).by_slot["closing"][:5]
    # 1850 now counts as newer; within the newer hymns the more familiar leads.
    assert titles(by_1845) == ["Old common", "Old median", "Unknown", "Newer", "Old rare"]


def test_a_long_ranked_list_keeps_ten_places_for_newer_hymns():
    hymns = [rec(f"Old {n}", n, theme="joy", year=1800 + n, count=10) for n in range(60)]
    hymns += [rec(f"New {n}", 100 + n, theme="joy", year=1990 + n % 10, count=10) for n in range(20)]
    candidates = build(hymns)
    closing = candidates.by_slot["closing"]
    assert len(closing) == 50 and candidates.modes["closing"] == "ranked"
    assert sum(h.title.startswith("New") for h in closing) == 10
    assert closing[0].title == "Old 0" and closing[-1].title.startswith("New")


def test_the_pad_follows_the_focused_hymns_and_is_ranked():
    hymns = [rec(f"Pad {n}", n, year=(1990 if n % 2 else 1850), count=n) for n in range(1, 101)]
    hymns[0] = rec("Gathering A", 1, theme="gathering", year=1995)
    hymns[1] = rec("Gathering B", 2, theme="gathering", year=1800)
    hymns[2] = rec("Gathering C", 3, theme="gathering")
    opening = build(hymns).by_slot["opening"]
    assert len(opening) == 40
    assert titles(opening[:3]) == ["Gathering B", "Gathering C", "Gathering A"]
    pad = opening[3:]
    assert len(pad) == 37
    older = [h for h in pad if h.text_year == 1850]
    assert pad[:len(older)] == older                           # older first within the pad
    assert [h.hymnal_count for h in older] == sorted((h.hymnal_count for h in older), reverse=True)
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_suggest.py 2>&1 | tail -3
```

**Expected:** `ERROR backend/tests/test_hymn_suggest.py`, `Interrupted: 1 error during collection` and `1 error in <t>s` (`ModuleNotFoundError: No module named 'hymn_suggest'`).

- [ ] **Step 4 (agent): Write `build_candidates`**

**Create `backend/hymn_suggest.py`:**

````python
"""Pure pieces of the AI hymn suggestions (slice 3 spec, Backend 3.6 steps 6-9
and 3.8; owner decision 3; owner answer Q1 of 2026-09-29: AI fills only empty
slots, a chosen hymn is never overwritten, filled slots get alternatives).

- build_candidates: each slot's candidate list, ranked by the church's
  rubric, cut to SLOT_CAP with NEWER_RESERVE places kept for newer and
  unknown-year hymns, and padded with an even sample of the hymnal.
- build_prompt: the messages and the H1..Hn token map, at most 24 000 characters.
- parse_suggestion_json, resolve_suggestions: the AI's answer as records.
- finalize_slots: distinct top picks for the empty slots and at least
  MIN_PER_SLOT hymns per slot when the candidates allow.

No I/O, no FastAPI, no Streamlit. Records are repos.hymns.HymnRecord.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

import hymn_ranking
import service_rubric
from domain_errors import InvalidInput, UpstreamError
from hymn_search import evenly_spaced, match_hymns, normalize_title, parse_themes
from scripture_refs import split_alternatives

SLOTS = ("opening", "response", "closing")
SLOT_CAP = 50               # candidates per slot shown to the AI
NEWER_RESERVE = 10          # of those, places kept for newer and unknown-year hymns (owner, 2026-09-26)
PAD_BELOW = 15              # a slot with fewer focused hymns than this ...
PAD_TO = 40                 # ... is padded to this many with an even sample of the hymnal
RESPONSE_LIMIT_PER_REF = 30  # parity: worship_service.py:460-464
MAX_PROMPT_CHARS = 24_000   # F §2.8
NT_EXCERPT_CHARS = 1_500    # parity: worship_service.py:497
MIN_PER_SLOT = 3            # a top pick plus 2 alternatives (owner decision 3)
MAX_PER_SLOT = 5

UNUSABLE_MESSAGE = "The AI gave an answer we couldn't use. Try again."
PROMPT_TOO_LONG_MESSAGE = "This prompt is too long."

# Theme keywords that pre-filter opening and closing candidates (moved from
# worship_service.py:367-368; matched at word starts, so "joy" finds
# "joyful" but not "enjoy"). They match the default slot checklists.
_OPENING_THEMES = {"gathering", "opening", "call to worship", "invitation", "welcome", "entrance"}
_CLOSING_THEMES = {"joy", "rejoice", "sending", "benediction", "mission", "dismissal", "praise",
                   "thanksgiving"}
_THEMES = {"opening": _OPENING_THEMES, "closing": _CLOSING_THEMES}

SYSTEM_MESSAGE = "You help a church choose hymns for a worship service. Reply with JSON only."
INSTRUCTION = ('Return {"opening": [ids], "response": [ids], "closing": [ids]}, with exactly 5 ids '
               "per slot (all of that slot's ids if it lists fewer than 5), best first, using only "
               "ids listed for that slot, and never the same hymn in two slots.")


def _year(record) -> Optional[int]:
    return record.text_year


def _count(record) -> Optional[int]:
    return record.hymnal_count


def matches_theme(record, keywords: set[str]) -> bool:
    text = " ".join(parse_themes(record.theme)).lower()
    return any(re.search(r"\b" + re.escape(keyword), text) for keyword in keywords)


def response_refs(nt_ref: Optional[str], scriptures: Sequence[str]) -> list[str]:
    """The NT reading's alternatives first, then every reading's, without repeats."""
    out: list[str] = []
    for ref in [*split_alternatives(nt_ref or ""),
                *(alt for line in scriptures for alt in split_alternatives(line or ""))]:
        if ref not in out:
            out.append(ref)
    return out


def _has_signal(records: Sequence[Any], prefer_familiar: bool) -> bool:
    """False when ranking could change nothing (no year known, and familiarity
    off or no count known): then lists are sampled, not ranked (S 3.8 item 3)."""
    return (any(r.text_year is not None for r in records)
            or (prefer_familiar and any(r.hymnal_count is not None for r in records)))


def _rank(records: list, rubric: Mapping[str, Any]) -> list:
    return hymn_ranking.rank_candidates(records, prefer_before_year=rubric["prefer_before_year"],
                                        prefer_familiar=rubric["prefer_familiar"],
                                        year_of=_year, count_of=_count)


@dataclass(frozen=True)
class Candidates:
    by_slot: dict[str, list]           # each at most SLOT_CAP focused hymns, then any pad
    modes: dict[str, str]              # "ranked" or "sampled" per slot (for the logs)


def build_candidates(eligible: Sequence[Any], scriptures: Sequence[str], *, nt_ref: Optional[str],
                     current_picks: Mapping[str, Optional[uuid.UUID]],
                     rubric: Mapping[str, Any]) -> Candidates:
    """S Backend 3.6 step 6 with 3.8's ranking. `eligible` is in hymnal order.
    Each slot's list leaves out the other two slots' current picks (a slot's
    own pick may stay), is ranked by the rubric and cut with shortlist when
    ranking has a signal, and otherwise truncated (response) or evenly sampled
    (opening, closing). A list with fewer than PAD_BELOW focused hymns gets an
    even sample of the rest, ranked, after the focused hymns, up to PAD_TO."""
    refs = response_refs(nt_ref, scriptures)
    by_slot: dict[str, list] = {}
    modes: dict[str, str] = {}
    for slot in SLOTS:
        others = {pick for other, pick in current_picks.items() if other != slot and pick is not None}
        pool = [h for h in eligible if h.id not in others]
        if slot == "response":
            focused = [m.record for m in match_hymns(pool, refs, limit_per_ref=RESPONSE_LIMIT_PER_REF,
                                                     max_results=200).items] if refs else []
        else:
            focused = [h for h in pool if matches_theme(h, _THEMES[slot])]
        if _has_signal(focused, rubric["prefer_familiar"]):
            modes[slot] = "ranked"
            focused = hymn_ranking.shortlist(_rank(focused, rubric), limit=SLOT_CAP,
                                             prefer_before_year=rubric["prefer_before_year"],
                                             reserve=NEWER_RESERVE, year_of=_year)
        else:
            modes[slot] = "sampled"
            if len(focused) > SLOT_CAP:
                focused = focused[:SLOT_CAP] if slot == "response" else evenly_spaced(focused, SLOT_CAP)
        if len(focused) < PAD_BELOW:
            chosen = {h.id for h in focused}
            rest = [h for h in pool if h.id not in chosen]
            pad = evenly_spaced(rest, PAD_TO - len(focused))
            if _has_signal(pad, rubric["prefer_familiar"]):
                pad = _rank(pad, rubric)
            focused = focused + pad
        by_slot[slot] = focused
    return Candidates(by_slot=by_slot, modes=modes)
````

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_suggest.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `9 passed in <t>s`; `1080 passed, 11 skipped in <t>s`; then `?? backend/hymn_suggest.py` and `?? backend/tests/test_hymn_suggest.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/hymn_suggest.py backend/tests/test_hymn_suggest.py
git commit -m "Hymns: suggestion candidates ranked by the rubric, cut to 50 with 10 kept for newer hymns, padded evenly (S Backend 3.6 step 6, 3.8)" -m "Each slot drops the other slots' current picks, then takes scripture
matches (response, the NT reading first, 30 per ref) or theme matches at
word starts (opening, closing). With a year or familiarity signal the list
is ranked by the church's rubric and shortlisted to 50 with 10 places for
newer and unknown-year hymns; without one it is truncated (response) or
sampled evenly (opening, closing), so PH1990 no longer means Advent only.
Fewer than 15 focused hymns are padded to 40 with a ranked even sample.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check S 3.8 items 1-4 against `build_candidates` (rank, cut, no-signal exception, ranked pad after the focused hymns) and that the theme sets equal `worship_service.py:367-368`. Push the backup.

Counts after Task 11: backend **1080 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 12: The prompt, the answer's parsing and resolution, and the final slots (S Backend 3.6 steps 7 and 9, 3.8 "Prompt"; owner decision 3; owner answer Q1; AC11 server half, AC19; clarifications 2, 9, 15, 18)

This task completes `hymn_suggest.py`. `build_prompt` renders a system message and one user message: the occasion, the readings, the NT reference and a 1 500-character excerpt, the ROLE REQUIREMENTS block from the church's three slot checklists (`format_checklist`, as PR #4 builds it), PR #4's PREFERENCES line verbatim, one `HYMNS` catalogue listing each candidate once as `H{k} | title | #number | (facts) | themes | scripture`, the three `CANDIDATES` lines in ranked order and the instruction to return exactly five ids per slot. Over 24 000 characters it drops the last candidate of the longest list and renders again; checklist points are never dropped. `parse_suggestion_json` strips code fences and requires an object whose slot values are lists. `resolve_suggestions` maps `H\d+` tokens in any case, and any other string only by exact normalized title (the slot's candidates first, then the lowest number), dropping unknown values; nothing resolved anywhere is `ai_upstream_error`. `finalize_slots` implements S step 9 (owner answer Q1): distinct top picks for the empty slots only, AI alternatives in AI order, the minimum top-up from the slot's own candidates, at most five.

**Decisions recorded in this task:**
- **T12-1 (clarification 9).** The "same five ids" test pins S step 9's algorithm, not S Testing's sentence.
- **T12-2 (clarification 18).** `prompt_invalid` "This prompt is too long." only when every list is empty and the fixed text is still too long.
- **T12-3.** A missing slot key in the AI's answer counts as `[]`; a present non-list value makes the whole answer unusable.
- **T12-4.** The catalogue shows "#–" (an en dash) for a hymn with no number, as S writes it.

**Files:**
- Modify: `backend/hymn_suggest.py` (the prompt, parsing, resolution and final-slots sections appended)
- Test: `backend/tests/test_hymn_suggest.py` (imports; 15 tests appended)

**Interfaces:**
- Consumes: Task 11's `Candidates`, `build_candidates`, constants; `service_rubric.format_checklist`, `HYMN_SLOTS`, `HYMN_SLOT_LABELS`; `hymn_ranking.facts_note`; `hymn_search.normalize_title`, `parse_themes`.
- Produces (later user: Task 13): `build_prompt(candidates, *, occasion, scriptures, nt_ref, nt_text, rubric) -> (messages, token_map)`; `prompt_size(messages) -> int`; `parse_suggestion_json(raw) -> dict[str, list]`; `resolve_suggestions(parsed, token_map, eligible, candidates) -> dict[str, list]`; `Suggested(record, source: "ai" | "candidates")`; `finalize_slots(resolved, current_picks, candidates) -> dict[str, list[Suggested]]`.

- [ ] **Step 1 (agent): Confirm Task 11's count**

```bash
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `1080 passed, 11 skipped in <t>s`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `backend/tests/test_hymn_suggest.py`, replace:**

````python
import uuid

import hymn_suggest as hs
from repos.hymns import HymnRecord
from service_rubric import default_rubric

RUBRIC = default_rubric()
````

**with:**

````python
import uuid

import pytest

import hymn_suggest as hs
from domain_errors import UpstreamError
from repos.hymns import HymnRecord
from service_rubric import default_rubric, merge_rubric

RUBRIC = default_rubric()
````

**Append to `backend/tests/test_hymn_suggest.py`:**

````python


# --- T12: build_prompt ----------------------------------------------------------------

HYMNS = [rec("Newer Gathering Song", 1, theme="gathering", refs="Isaiah 6:3", year=1995, count=40),
         rec("Holy, Holy, Holy", 2, theme="gathering, praise", refs="Isaiah 6:3", year=1826, count=1322),
         rec("Go Forth Rejoicing", 3, theme="sending, joy", refs="Isaiah 6:3", year=1985, count=20),
         rec("Rejoice, the Lord Is King", 4, theme="joy, praise", refs="Isaiah 6:3", year=1744, count=900)]


def prompt(hymns=HYMNS, rubric=RUBRIC, **kwargs):
    candidates = build(hymns, ["Isaiah 6:1-8"], rubric=rubric)
    options = {"occasion": "Trinity Sunday", "scriptures": ["Isaiah 6:1-8"], "nt_ref": None,
               "nt_text": None, "rubric": rubric, **kwargs}
    return hs.build_prompt(candidates, **options)


def user_text(messages):
    assert messages[0] == {"role": "system", "content": hs.SYSTEM_MESSAGE}
    return messages[1]["content"]


def slot_tokens(text, slot):
    line = next(line for line in text.splitlines() if line.startswith(f"{slot.upper()} CANDIDATES: "))
    return line.split(": ", 1)[1].split(", ")


def slot_titles(text, token_map, slot):
    return [token_map[t].title for t in slot_tokens(text, slot)]


def test_the_prompt_stays_under_24000_characters_and_trims_deterministically():
    long = [rec(f"{'Very long hymn title ' * 6} {n}", n, theme="gathering, joy, praise, sending",
                refs="Isaiah 6:1-8; Psalm 29; Romans 8:12-17; John 3:1-17") for n in range(1, 2001)]
    first, first_map = prompt(long, scriptures=["Isaiah 6:1-8", "John 3:1-17"])
    again, _ = prompt(long, scriptures=["Isaiah 6:1-8", "John 3:1-17"])
    assert hs.prompt_size(first) <= hs.MAX_PROMPT_CHARS
    assert first == again
    text = user_text(first)
    catalogue = [line for line in text.splitlines() if line.startswith("H") and " | " in line]
    assert len(catalogue) == len(first_map)
    for slot in hs.SLOTS:
        assert set(slot_tokens(text, slot)) <= set(first_map)          # every listed token is in the catalogue


def test_the_prompt_lists_each_hymn_once_and_asks_for_exactly_five_ids():
    messages, token_map = prompt(nt_ref="Isaiah 6:1-8", nt_text="Holy, holy, holy is the Lord. " * 100)
    text = user_text(messages)
    assert sorted(token_map) == sorted(f"H{n}" for n in range(1, len(token_map) + 1))
    assert len({r.id for r in token_map.values()}) == len(token_map)
    assert hs.INSTRUCTION in text and "exactly 5 ids per slot" in text
    assert "OCCASION: Trinity Sunday" in text
    assert "SCRIPTURE READINGS:\n- Isaiah 6:1-8" in text
    assert "NEW TESTAMENT READING (for the response hymn): Isaiah 6:1-8" in text
    excerpt = text.split("NT PASSAGE TEXT (excerpt): ")[1].split("\n")[0]
    assert len(excerpt) == hs.NT_EXCERPT_CHARS
    assert "(no text loaded)" in user_text(prompt()[0])


def test_the_prompt_carries_checklists_preferences_and_facts():
    text = user_text(prompt()[0])
    assert "A good Opening (Gathering) Hymn:" in text
    assert "A good Response Hymn (after the sermon):" in text
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in text
    assert "- sends people out to serve others and share God's love" in text
    assert ("PREFERENCES: Prefer hymns written before 1970 and hymns found in many hymnals; "
            "choose a newer hymn only when it fits clearly better. Each candidate shows when its "
            "words were written and how many hymnals include it, when known.") in text
    assert " | Holy, Holy, Holy | #2 | (written 1826, in 1,322 hymnals) | themes: gathering, praise | " in text
    unknown = user_text(prompt([rec("Mystery", None, theme="joy")])[0])
    assert " | Mystery | #– | themes: joy | scripture: " in unknown       # no facts field
    opening = slot_titles(text, prompt()[1], "opening")
    assert opening.index("Holy, Holy, Holy") < opening.index("Newer Gathering Song")


def test_a_church_rubric_changes_the_prompt_and_a_partial_one_falls_back():
    rubric = default_rubric()
    rubric["hymns"]["closing"] = ["ends with a rousing doxology"]
    rubric.update(prefer_before_year=1900, prefer_familiar=False)
    text = user_text(prompt(rubric=rubric)[0])
    assert "A good Closing (Sending) Hymn:\n- ends with a rousing doxology" in text
    assert "is joyful and upbeat" not in text
    assert "Prefer hymns written before 1900; choose a newer hymn" in text
    assert "hymns found in many hymnals" not in text
    partial = user_text(prompt(rubric=merge_rubric({"prefer_before_year": 1900}))[0])
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in partial
    assert "Prefer hymns written before 1900 and hymns found in many hymnals" in partial


def test_candidate_headings_add_no_fixed_role_hints():
    rubric = default_rubric()
    rubric["hymns"]["closing"] = ["is quiet and reflective"]
    text = user_text(prompt(rubric=rubric)[0])
    headings = [line.split(":")[0] for line in text.splitlines() if "CANDIDATES" in line]
    assert headings == ["OPENING CANDIDATES", "RESPONSE CANDIDATES", "CLOSING CANDIDATES"]
    assert "joyful" not in text.split("HYMNS:")[0].lower()
    assert "Must be joyful, upbeat, or sending" not in text


def test_a_maximum_rubric_drops_candidates_never_checklist_points():
    rubric = default_rubric()
    for slot in hs.SLOTS:
        rubric["hymns"][slot] = [f"{slot} point {i} " + "x" * 280 for i in range(12)]
    hymns = [rec(f"Joyful Gathering {n} " + "y" * 60, n, theme="gathering, joy", refs="Isaiah 6:3")
             for n in range(1, 151)]
    messages, token_map = prompt(hymns, rubric=rubric)
    text = user_text(messages)
    assert hs.prompt_size(messages) <= hs.MAX_PROMPT_CHARS
    assert all(f"{slot} point {i} " in text for slot in hs.SLOTS for i in range(12))
    listed = sum(len(slot_tokens(text, slot)) for slot in hs.SLOTS)
    assert listed < 150 and len(token_map) <= listed                  # candidates were dropped


# --- T12: parse, resolve, finalize ---------------------------------------------------------


def test_parse_suggestion_json():
    assert hs.parse_suggestion_json('{"opening": ["H1"], "response": [], "closing": ["H2"]}') == {
        "opening": ["H1"], "response": [], "closing": ["H2"]}
    assert hs.parse_suggestion_json('```json\n{"opening": ["H1"]}\n```') == {
        "opening": ["H1"], "response": [], "closing": []}
    for bad in ("not json", "[]", '"H1"', '{"opening": "H1"}', "", None):
        with pytest.raises(UpstreamError) as caught:
            hs.parse_suggestion_json(bad)
        assert (caught.value.code, caught.value.message) == ("ai_upstream_error", hs.UNUSABLE_MESSAGE)


def resolved_titles(resolved):
    return {slot: titles(records) for slot, records in resolved.items()}


def test_resolve_maps_tokens_in_any_case_and_drops_unknown_values():
    candidates = build(HYMNS, ["Isaiah 6:1-8"])
    _, token_map = hs.build_prompt(candidates, occasion="", scriptures=[], nt_ref=None, nt_text=None,
                                   rubric=RUBRIC)
    by_title = {r.title: t for t, r in token_map.items()}
    parsed = {"opening": [by_title["Holy, Holy, Holy"].lower(), "H999", 7, None, "",
                          by_title["Holy, Holy, Holy"]],
              "response": [], "closing": [by_title["Go Forth Rejoicing"]]}
    assert resolved_titles(hs.resolve_suggestions(parsed, token_map, HYMNS, candidates)) == {
        "opening": ["Holy, Holy, Holy"], "response": [], "closing": ["Go Forth Rejoicing"]}


def test_resolve_by_exact_title_only_preferring_the_slots_candidates():
    twin_a = rec("Holy Ground", 20, theme="praise")
    twin_b = rec("Holy Ground", 10, theme="gathering")
    eligible = [*HYMNS, twin_a, twin_b]
    candidates = build(eligible)
    parsed = {"opening": ["  holy   ground ", "Holy"], "closing": ["Holy Ground"], "response": []}
    resolved = hs.resolve_suggestions(parsed, {}, eligible, candidates)
    assert [r.number for r in resolved["opening"]] == [10]         # "Holy" alone is no match
    closing_ids = {r.id for r in candidates.by_slot["closing"]}
    assert twin_a.id in closing_ids and twin_b.id in closing_ids
    assert [r.number for r in resolved["closing"]] == [10]         # both candidates: the lower number


def test_nothing_resolved_in_any_slot_is_upstream_error():
    candidates = build(HYMNS)
    with pytest.raises(UpstreamError) as caught:
        hs.resolve_suggestions({"opening": ["H99", "Unknown"], "response": [], "closing": []}, {},
                               HYMNS, candidates)
    assert caught.value.message == hs.UNUSABLE_MESSAGE


def big_hymnal():
    return [rec(f"Hymn {n}", n, theme="gathering, joy", refs="Psalm 23") for n in range(1, 31)]


def final_titles(final):
    return {slot: [(s.record.title, s.source) for s in items] for slot, items in final.items()}


def test_distinct_tops_other_picks_excluded_own_pick_kept_and_cap_five():
    hymns = big_hymnal()
    by = {h.title: h for h in hymns}
    picks = {"opening": None, "response": by["Hymn 9"].id, "closing": None}
    candidates = build(hymns, ["Psalm 23"], picks=picks)
    resolved = {"opening": [by[f"Hymn {n}"] for n in (9, 1, 2, 3, 4, 5, 6)],
                "response": [by[f"Hymn {n}"] for n in (1, 9, 7)],
                "closing": [by[f"Hymn {n}"] for n in (1, 2, 8)]}
    final = hs.finalize_slots(resolved, picks, candidates)
    # Hymn 9 is response's pick and Hymn 2 closing's top, so neither is an opening idea.
    assert final_titles(final)["opening"] == [("Hymn 1", "ai"), ("Hymn 3", "ai"), ("Hymn 4", "ai"),
                                              ("Hymn 5", "ai"), ("Hymn 6", "ai")]
    assert final_titles(final)["closing"][0] == ("Hymn 2", "ai")        # Hymn 1 is opening's top
    assert ("Hymn 1", "ai") not in final_titles(final)["closing"]        # another slot's top is never an idea
    assert final_titles(final)["response"][:2] == [("Hymn 9", "ai"), ("Hymn 7", "ai")]
    assert all(s.record.title != "Hymn 9" for slot in ("opening", "closing") for s in final[slot])
    assert all(len(items) <= hs.MAX_PER_SLOT for items in final.values())


def test_one_id_per_slot_is_topped_up_to_three_from_each_slots_candidates():
    hymns = big_hymnal()
    by = {h.title: h for h in hymns}
    candidates = build(hymns, ["Psalm 23"])
    resolved = {"opening": [by["Hymn 5"]], "response": [by["Hymn 6"]], "closing": [by["Hymn 7"]]}
    final = hs.finalize_slots(resolved, NO_PICKS, candidates)
    for slot, top in (("opening", "Hymn 5"), ("response", "Hymn 6"), ("closing", "Hymn 7")):
        items = final_titles(final)[slot]
        assert items[0] == (top, "ai") and [s for _, s in items] == ["ai", "candidates", "candidates"]
        expected = [h.title for h in candidates.by_slot[slot]
                    if h.title not in ("Hymn 5", "Hymn 6", "Hymn 7")][:2]
        assert [t for t, _ in items[1:]] == expected                   # in candidate order


def test_the_same_five_ids_for_every_slot_give_distinct_tops():
    """Clarification 9: tops are distinct and never another slot's idea; the
    same idea may appear under two slots (S Backend 3.6 step 9 as written)."""
    hymns = big_hymnal()
    by = {h.title: h for h in hymns}
    same = [by[f"Hymn {n}"] for n in range(1, 6)]
    candidates = build(hymns, ["Psalm 23"])
    final = hs.finalize_slots({"opening": same, "response": same, "closing": same}, NO_PICKS, candidates)
    assert final_titles(final) == {
        "opening": [("Hymn 1", "ai"), ("Hymn 4", "ai"), ("Hymn 5", "ai")],
        "response": [("Hymn 2", "ai"), ("Hymn 4", "ai"), ("Hymn 5", "ai")],
        "closing": [("Hymn 3", "ai"), ("Hymn 4", "ai"), ("Hymn 5", "ai")],
    }
    for slot in hs.SLOTS:
        others = {final[o][0].record.id for o in hs.SLOTS if o != slot}
        assert not others & {s.record.id for s in final[slot]}


def test_a_filled_slot_gets_three_ideas_besides_its_own_pick():
    hymns = big_hymnal()
    by = {h.title: h for h in hymns}
    picks = {"opening": by["Hymn 3"].id, "response": None, "closing": None}
    candidates = build(hymns, ["Psalm 23"], picks=picks)
    final = hs.finalize_slots({"opening": [by["Hymn 3"]], "response": [by["Hymn 4"]],
                               "closing": [by["Hymn 5"]]}, picks, candidates)
    opening = final["opening"]
    assert opening[0].record.title == "Hymn 3"                         # its own pick, kept in the list
    assert sum(1 for s in opening if s.record.id != by["Hymn 3"].id) >= 3


def test_a_tiny_pool_ends_below_the_minimum_without_error():
    hymns = [rec(f"Only {n}", n, theme="joy", refs="Psalm 23") for n in range(1, 5)]
    by = {h.title: h for h in hymns}
    candidates = build(hymns, ["Psalm 23"])
    final = hs.finalize_slots({"opening": [by["Only 1"]], "response": [by["Only 2"]],
                               "closing": [by["Only 3"]]}, NO_PICKS, candidates)
    tops = {final[slot][0].record.id for slot in hs.SLOTS}
    assert len(tops) == 3
    assert all(1 <= len(final[slot]) <= 2 for slot in hs.SLOTS)        # 4 hymns, 3 tops reserved
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_suggest.py 2>&1 | tail -1
```

**Expected:** `15 failed, 9 passed in <t>s` (each new test fails with `AttributeError: module 'hymn_suggest' has no attribute 'build_prompt'` or `... 'parse_suggestion_json'`, `'resolve_suggestions'`, `'finalize_slots'`).

- [ ] **Step 4 (agent): Write the prompt, the parsing, the resolution and the final slots**

**Append to `backend/hymn_suggest.py`:**

````python


# --- the prompt (S Backend 3.6 step 7, 3.8 "Prompt") -------------------------------


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit]


def _catalogue_line(token: str, record) -> str:
    number = record.number if record.number is not None else "–"
    facts = hymn_ranking.facts_note(record, year_of=_year, count_of=_count)
    return (f"{token} | {_clip(record.title, 80)} | #{number}"
            + (f" | {facts}" if facts else "")
            + f" | themes: {_clip(', '.join(parse_themes(record.theme)), 60)}"
            + f" | scripture: {_clip(record.scripture_refs or '', 60)}")


def _preferences(rubric: Mapping[str, Any]) -> str:
    """PR #4's PREFERENCES line, verbatim (worship_service.py:545-551)."""
    return (f"Prefer hymns written before {rubric['prefer_before_year']}"
            + (" and hymns found in many hymnals" if rubric["prefer_familiar"] else "")
            + "; choose a newer hymn only when it fits clearly better. Each candidate shows when "
              "its words were written and how many hymnals include it, when known.")


def _render(lists: Mapping[str, list], *, occasion: str, scriptures: Sequence[str],
            nt_ref: Optional[str], nt_text: Optional[str],
            rubric: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    tokens: dict[uuid.UUID, str] = {}
    token_map: dict[str, Any] = {}
    catalogue: list[str] = []
    for slot in SLOTS:
        for record in lists[slot]:
            if record.id not in tokens:
                token = f"H{len(tokens) + 1}"
                tokens[record.id] = token
                token_map[token] = record
                catalogue.append(_catalogue_line(token, record))
    readings = "\n".join(f"- {_clip(s, 200)}" for s in scriptures if (s or "").strip()) or "None"
    excerpt = _clip(nt_text or "", NT_EXCERPT_CHARS) or "(no text loaded)"
    checklists = "\n\n".join(
        service_rubric.format_checklist(service_rubric.HYMN_SLOT_LABELS[slot], rubric["hymns"][slot])
        for slot in service_rubric.HYMN_SLOTS)
    slot_lines = "\n".join(f"{slot.upper()} CANDIDATES: " + ", ".join(tokens[r.id] for r in lists[slot])
                           for slot in SLOTS)
    user = (f"OCCASION: {_clip(occasion, 300) or 'Not specified'}\n"
            f"SCRIPTURE READINGS:\n{readings}\n"
            f"NEW TESTAMENT READING (for the response hymn): {nt_ref or 'Not specified'}\n"
            f"NT PASSAGE TEXT (excerpt): {excerpt}\n\n"
            f"ROLE REQUIREMENTS (what makes a good hymn for each slot):\n\n{checklists}\n\n"
            f"PREFERENCES: {_preferences(rubric)}\n\n"
            "HYMNS:\n" + "\n".join(catalogue) + "\n\n"
            f"{slot_lines}\n\n{INSTRUCTION}")
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}, {"role": "user", "content": user}]
    return messages, token_map


def prompt_size(messages: Sequence[Mapping[str, str]]) -> int:
    return sum(len(m["content"]) for m in messages)


def build_prompt(candidates: Candidates, *, occasion: str, scriptures: Sequence[str],
                 nt_ref: Optional[str], nt_text: Optional[str],
                 rubric: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    """(messages, {"H1": record, ...}), at most MAX_PROMPT_CHARS in all. While
    it is longer, the last candidate of the longest slot list (the first such
    slot on a tie) is dropped, with its catalogue line when no other list uses
    it. Checklist points are never dropped. Deterministic."""
    lists = {slot: list(candidates.by_slot[slot]) for slot in SLOTS}
    while True:
        messages, token_map = _render(lists, occasion=occasion, scriptures=scriptures,
                                      nt_ref=nt_ref, nt_text=nt_text, rubric=rubric)
        if prompt_size(messages) <= MAX_PROMPT_CHARS:
            return messages, token_map
        longest = max(SLOTS, key=lambda slot: len(lists[slot]))
        if not lists[longest]:
            raise InvalidInput(PROMPT_TOO_LONG_MESSAGE, code="prompt_invalid")
        lists[longest].pop()


# --- the answer (S Backend 3.6 step 9) ---------------------------------------------


def parse_suggestion_json(raw: str) -> dict[str, list]:
    """The AI's JSON object, code fences stripped (parity, worship_service.py:531-535).
    Each slot's value must be a list; a missing slot is []. Anything else is
    UpstreamError ai_upstream_error "The AI gave an answer we couldn't use. Try again."."""
    content = (raw or "").strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.lower().startswith("json"):
            content = content[4:]
    try:
        data = json.loads(content.strip())
    except (ValueError, TypeError):
        raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error") from None
    if not isinstance(data, dict):
        raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error")
    out: dict[str, list] = {}
    for slot in SLOTS:
        value = data.get(slot, [])
        if not isinstance(value, list):
            raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error")
        out[slot] = value
    return out


_TOKEN = re.compile(r"^H\d+$", re.IGNORECASE)


def _number_key(record) -> tuple[int, int]:
    return (record.number is None, record.number or 0)


def resolve_suggestions(parsed: Mapping[str, list], token_map: Mapping[str, Any],
                        eligible: Sequence[Any], candidates: Candidates) -> dict[str, list]:
    """Each slot's answer as records, in AI order, without repeats. "H12" (any
    case) is a candidate token; any other string counts only on an exact
    normalized-title match within `eligible` (no substring or fuzzy match),
    preferring that slot's candidates, then the lowest number. Unknown values
    are dropped. Nothing resolved in any slot is UpstreamError."""
    by_title: dict[str, list] = {}
    for record in eligible:
        by_title.setdefault(normalize_title(record.title), []).append(record)
    resolved: dict[str, list] = {}
    for slot in SLOTS:
        in_slot = {r.id for r in candidates.by_slot.get(slot, [])}
        out: list = []
        for value in parsed.get(slot, []):
            if not isinstance(value, str) or not value.strip():
                continue
            text = value.strip()
            if _TOKEN.match(text):
                record = token_map.get(text.upper())
            else:
                matches = by_title.get(normalize_title(text), [])
                record = min(matches, key=lambda r: (r.id not in in_slot, *_number_key(r)),
                             default=None)
            if record is not None and all(r.id != record.id for r in out):
                out.append(record)
        resolved[slot] = out
    if not any(resolved.values()):
        raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error")
    return resolved


@dataclass(frozen=True)
class Suggested:
    record: Any
    source: str                         # "ai", or "candidates" when added by the minimum top-up


def finalize_slots(resolved: Mapping[str, list], current_picks: Mapping[str, Optional[uuid.UUID]],
                   candidates: Candidates) -> dict[str, list[Suggested]]:
    """S Backend 3.6 step 9 (owner decision 3; owner answer Q1: only empty
    slots get a top pick). Top picks are distinct and never another slot's
    current pick; each slot then lists its AI hymns and, when that leaves
    fewer than MIN_PER_SLOT hymns other than its own pick, the next hymns of
    its own candidate list; at most MAX_PER_SLOT."""
    reserved = {pick for pick in current_picks.values() if pick is not None}
    tops: dict[str, Optional[Suggested]] = {}
    for slot in SLOTS:
        tops[slot] = None
        if current_picks.get(slot) is not None:
            continue
        top = next((Suggested(r, "ai") for r in resolved.get(slot, []) if r.id not in reserved), None)
        if top is None:
            top = next((Suggested(r, "candidates") for r in candidates.by_slot.get(slot, [])
                        if r.id not in reserved), None)
        if top is not None:
            tops[slot] = top
            reserved.add(top.record.id)
    final: dict[str, list[Suggested]] = {}
    for slot in SLOTS:
        own = current_picks.get(slot)
        top = tops[slot]
        blocked = reserved - {own, top.record.id if top else None}
        listed: list[Suggested] = [top] if top else []
        seen = {s.record.id for s in listed}
        for record in resolved.get(slot, []):
            if record.id not in blocked and record.id not in seen:
                listed.append(Suggested(record, "ai"))
                seen.add(record.id)
        for record in candidates.by_slot.get(slot, []):
            if sum(1 for s in listed if s.record.id != own) >= MIN_PER_SLOT:
                break
            if record.id not in blocked and record.id not in seen:
                listed.append(Suggested(record, "candidates"))
                seen.add(record.id)
        final[slot] = listed[:MAX_PER_SLOT]
    return final
````

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_suggest.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `24 passed in <t>s`; `1097 passed, 11 skipped in <t>s`; then ` M backend/hymn_suggest.py` and ` M backend/tests/test_hymn_suggest.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/hymn_suggest.py backend/tests/test_hymn_suggest.py
git commit -m "Hymns: the suggestion prompt, the answer by candidate token, and top picks for empty slots only (S Backend 3.6 steps 7, 9, 3.8; decision 3; owner answer Q1)" -m "build_prompt lists each candidate once as H1..Hn with its facts, carries the
church's three slot checklists and PR #4's PREFERENCES line, asks for
exactly 5 ids per slot and trims candidates (never checklist points) to
24 000 characters. The answer resolves by token, or by exact title only;
nothing usable is ai_upstream_error. finalize_slots gives only empty slots
a top pick (owner answer Q1), keeps tops distinct and never another slot's
idea, and tops each slot up to 3 from its own candidates (clarification 9).
The PR #4 rubric cases are ported here (clarification 15).

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Walk S step 9 items 1-4 against `finalize_slots`, the PREFERENCES line against `worship_service.py:545-551` (still on the branch until Task 14), and clarification 15's mapping against the tests present. Push the backup.

Counts after Task 12: backend **1097 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 13: `POST /hymns/suggestions` (S API row 4, Models, Backend 3.6-3.8, 4, 6; F §1.8; Testing `test_api_hymn_suggestions.py`, "Isolation and roles", "Rate limit", "Rubric"; owner decision 3; owner answer Q1; AC4-AC8, AC11, AC18-AC20; clarifications 7, 10, 19, 21)

This task adds the suggestion usecase and route. `suggest_hymns` sets its 75 s deadline on entry, reads the hymnal, the pool (blank titles dropped), the usage window around the service date and the rubric in one session and closes it; refuses an empty pool (`fields.hymnal`) and a pool that is all recent when exclusion is on; checks `ai.ai_available()` before any external call; takes the client's NT text, or fetches WEB for `selected_nt_ref` or `default_nt_ref(scriptures)` on the `nt-fetch` pool within 10 s (a timeout, failure or no text means none); builds the candidates and the prompt; makes one `complete(..., max_completion_tokens=1200, json_mode=True, deadline=...)` call; and parses, resolves and finalizes. Every hymn in the answer is a `HymnView` plus `source`, with `recent_use_on` always computed for the service date. One `hymn_suggestions` log line per call, success or error. The route depends on `rate_limit("ai")`; `current_picks` are exclusion hints only, never resolved or echoed, so another church's id is ignored (S's declared exception to F §1.2 rules 2 and 5).

**Decisions recorded in this task:**
- **T13-1 (clarification 7).** `NotConfigured` from the client is re-raised with "AI suggestions aren't set up on this app yet."
- **T13-2 (clarification 19).** The NT pool copies the request context; `reset_for_tests()` joins and rebuilds it, and `_fresh_ai` calls it first. The conftest change therefore lands in Step 4 with `reset_for_tests`, not with the tests.
- **T13-3 (clarification 21).** The rate-limit tests pre-spend tokens with `ratelimit.consume`. `test_a_rejected_request_still_spends_a_token` pins "Buckets": a Pydantic 422 and the usecase's 422 each spend one.
- **T13-4.** The usecase takes `ai=openai_client` and `fetch_text=None` (resolved at call time to `usecases.passages.get_passage_text`, so a test's `monkeypatch.setattr(passages, "get_passage_text", ...)` reaches it) and `clock=time.monotonic`.

**Files:**
- Modify: `backend/usecases/hymns.py` (docstring; imports; messages and budgets; the suggestion section appended)
- Modify: `backend/api/routes/hymns.py` (imports; `SlotPicks`, `HymnSuggestionIn`, `SuggestedHymnOut`, `SuggestedSlots`, `HymnSuggestionsOut`; the route appended)
- Modify: `backend/tests/conftest.py` (`_fresh_ai` also resets `usecases.hymns`)
- Modify (tests): `backend/tests/test_api_app.py` (map), `backend/tests/test_no_streamlit_in_core.py` (import list)
- Test: `backend/tests/test_api_hymn_suggestions.py` (new)
- Modify (generated): `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`

**Interfaces:**
- Consumes: Tasks 11-12 (`hymn_suggest.*`); Task 10's `selected_hymnal`; Task 9's `hymn_view`, `HymnView`, `HymnOut`; Task 7's `usage_near`; Task 5's `usage_key`; Tasks 2-3's `openai_client` (`ai_available`, `complete`, `ai_settings`, `FakeAI`, `set_ai_for_tests`); `usecases.passages.get_passage_text(ref, translation)`; `scripture_refs.default_nt_ref`; `api.ratelimit.rate_limit("ai")`, `consume`; `api.deps.CurrentUser`, `get_current_user`; the `limiter_clock` fixture.
- Produces (later users: slice 3b; slice 4 reuses the client and the bucket):
  - `usecases.hymns.SuggestionRequest(service_date, occasion="", scriptures=[], selected_nt_ref=None, nt_text=None, hymnal=None, exclude_recent=True, current_picks={...})`; `SuggestedView(HymnView + source)`; `HymnSuggestions(hymnal, nt_ref, nt_text_used, excluded_recent_count, slots)`; `suggest_hymns(church_id, user_id, req, *, ai=openai_client, fetch_text=None, clock=time.monotonic)`; `reset_for_tests()`; constants `SUGGEST_BUDGET_S = 75.0`, `NT_FETCH_BUDGET_S = 10.0`, `NT_TRANSLATION = "web"`, `MAX_COMPLETION_TOKENS = 1200`, `EMPTY_POOL_MESSAGE`, `ALL_RECENT_MESSAGE`, `AI_NOT_CONFIGURED_MESSAGE`.
  - `POST /hymns/suggestions` (`HymnSuggestionIn` → `HymnSuggestionsOut`), `error_responses(401, 403, 422, 429, 502, 503, 504)`.

- [ ] **Step 1 (agent): Confirm Task 12's count and the `ai` bucket**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -c "import sys; sys.path.insert(0, 'backend'); from api import ratelimit as r; print(r.BUCKETS['ai'])"
```

**Expected:** `1097 passed, 11 skipped in <t>s`; `(Rule(scope='user', capacity=40, per_seconds=600), Rule(scope='church', capacity=400, per_seconds=86400))`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `backend/tests/test_api_app.py`, replace:**

````python
        ("/hymns/scripture-matches", "post"): {"401", "403", "422", "503"},
    }
````

**with:**

````python
        ("/hymns/scripture-matches", "post"): {"401", "403", "422", "503"},
        ("/hymns/suggestions", "post"): {"401", "403", "422", "429", "502", "503", "504"},
    }
````

**Create `backend/tests/test_api_hymn_suggestions.py`:**

````python
"""POST /hymns/suggestions (slice 3 spec, API row 4, Models, Backend 3.6-3.8;
Testing `test_api_hymn_suggestions.py`, "Isolation and roles", "Rate limit",
"Rubric"; owner decision 3; owner answer Q1 of 2026-09-29; AC4-AC8, AC11,
AC18-AC20). The AI is a FakeAI (integrations.openai_client.set_ai_for_tests);
the NT text fetcher is patched on usecases.passages."""
import json
import re
import threading
import time
import uuid

import pytest

from api import ratelimit
from db import session_scope
from db.models import Hymn, HymnUsage
from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout
from integrations import openai_client
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)
from usecases import hymns as hymns_usecase
from usecases import passages

EMAIL = "pastor@example.com"
DATE = "2026-10-04"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Grace", owner_user_id=owner)


@pytest.fixture
def fetched(monkeypatch):
    """The NT fetcher: records (ref, translation) and returns the passage text."""
    calls = []

    def fetch(ref, translation):
        calls.append((ref, translation))
        return f"Text of {ref}."

    monkeypatch.setattr(passages, "get_passage_text", fetch)
    return calls


def add(church_id, title, number, *, theme=None, refs=None, year=None, count=None, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number, theme=theme,
                   scripture_refs=refs, text_year=year, hymnal_count=count)
        s.add(row)
        s.flush()
        return str(row.id)


def hymnal(church_id, n=30, **kw):
    return [add(church_id, f"Hymn {i}", i, theme="gathering, joy", refs="Psalm 23", **kw)
            for i in range(1, n + 1)]


def use(church_id, title, date_iso):
    with session_scope() as s:
        s.add(HymnUsage(church_id=church_id, date_iso=date_iso, hymn_number=None, hymn_title=title))


def tokens_for(prompt, slot, n=5):
    line = next(line for line in prompt.splitlines() if line.startswith(f"{slot.upper()} CANDIDATES: "))
    return line.split(": ", 1)[1].split(", ")[:n]


def first_tokens(messages):
    """A FakeAI reply: each slot's first five candidate tokens."""
    prompt = messages[1]["content"]
    return json.dumps({slot: tokens_for(prompt, slot) for slot in ("opening", "response", "closing")})


def install(reply=first_tokens, **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def suggest(client, church_id, body=None, email=EMAIL, status=200):
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE, **(body or {})},
                    headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def slot_titles(body):
    return {slot: [h["title"] for h in items] for slot, items in body["slots"].items()}


def prompt_of(fake, call=-1):
    return fake.calls[call]["messages"][1]["content"]


def test_happy_path_distinct_tops_at_most_five_with_facts(client, church, fetched):
    hymnal(church, year=1985, count=40)
    add(church, "Holy, Holy, Holy", 100, theme="gathering", refs="Psalm 23", year=1826, count=1322)
    fake = install()
    body = suggest(client, church, {"scriptures": ["Psalm 23"]})
    assert body["hymnal"] == "GG2013" and body["excluded_recent_count"] == 0
    assert all(1 <= len(items) <= 5 for items in body["slots"].values())
    tops = [items[0]["id"] for items in body["slots"].values()]
    assert len(set(tops)) == 3
    first = body["slots"]["opening"][0]
    assert first["title"] == "Holy, Holy, Holy"                    # older and familiar ranks first
    assert (first["text_year"], first["hymnal_count"], first["newer_than_preferred"], first["source"]) == (
        1826, 1322, False, "ai")
    assert body["slots"]["opening"][1]["newer_than_preferred"] is True      # 1985
    (call,) = fake.calls
    assert (call["max_completion_tokens"], call["json_mode"]) == (1200, True)


def test_ai_errors_return_their_code_and_exact_message(client, church, fetched):
    hymnal(church)
    cases = [
        (install, {"available": False}, 503, "ai_not_configured", "AI suggestions aren't set up on this app yet."),
        (install, {"error": NotConfigured("quota", code="ai_not_configured")}, 503, "ai_not_configured",
         "AI suggestions aren't set up on this app yet."),
        (install, {"error": UpstreamTimeout(openai_client.TIMEOUT_MESSAGE, code="ai_timeout")}, 504,
         "ai_timeout", "The AI took too long to answer. Try again."),
        (install, {"error": Busy(openai_client.BUSY_MESSAGE, code="ai_busy")}, 503, "ai_busy",
         "The AI service is busy. Try again in a minute."),
        (install, {"error": UpstreamError(openai_client.UPSTREAM_MESSAGE, code="ai_upstream_error")}, 502,
         "ai_upstream_error", "The AI service had a problem. Try again."),
        (install, {"reply": "Sorry, I can't help with that."}, 502, "ai_upstream_error",
         "The AI gave an answer we couldn't use. Try again."),
        (install, {"reply": '{"opening": ["H999"], "response": [], "closing": []}'}, 502,
         "ai_upstream_error", "The AI gave an answer we couldn't use. Try again."),
    ]
    for setup, kw, status, code, message in cases:
        setup(**kw)
        error = suggest(client, church, status=status)["error"]
        assert (error["code"], error["message"]) == (code, message), kw
        assert set(error) == {"code", "message", "request_id"}, kw


def test_client_nt_text_skips_the_fetch(client, church, fetched):
    hymnal(church)
    fake = install()
    body = suggest(client, church, {"selected_nt_ref": "Mark 1:9-15", "nt_text": "Client text " * 300})
    assert fetched == [] and body["nt_text_used"] is True and body["nt_ref"] == "Mark 1:9-15"
    excerpt = prompt_of(fake).split("NT PASSAGE TEXT (excerpt): ")[1].split("\n")[0]
    assert excerpt.startswith("Client text") and len(excerpt) == 1500


def test_the_fetch_is_web_for_the_selected_or_the_default_nt_reading(client, church, fetched):
    hymnal(church)
    install()
    suggest(client, church, {"selected_nt_ref": " Mark 1:9-15 ", "scriptures": ["Isaiah 6:1-8"]})
    body = suggest(client, church, {"scriptures": ["Isaiah 6:1-8", "Psalm 29", "Romans 8:12-17",
                                                   "John 3:1-17"]})
    assert fetched == [("Mark 1:9-15", "web"), ("Romans 8:12-17", "web")]
    assert (body["nt_ref"], body["nt_text_used"]) == ("Romans 8:12-17", True)


def test_a_failed_or_empty_fetch_is_tolerated(client, church, monkeypatch):
    hymnal(church)
    install()
    for fetch in (lambda ref, tr: None, lambda ref, tr: 1 / 0):
        monkeypatch.setattr(passages, "get_passage_text", fetch)
        body = suggest(client, church, {"selected_nt_ref": "Mark 1:9-15"})
        assert body["nt_text_used"] is False


def test_a_hung_fetch_is_cut_off_by_its_budget(client, church, monkeypatch):
    hymnal(church)
    fake = install()
    release = threading.Event()
    monkeypatch.setattr(passages, "get_passage_text", lambda ref, tr: release.wait(5) and "late")
    monkeypatch.setattr(hymns_usecase, "NT_FETCH_BUDGET_S", 0.05)
    try:
        started = time.monotonic()
        body = suggest(client, church, {"selected_nt_ref": "Mark 1:9-15"})
        assert time.monotonic() - started < 1.0
        assert body["nt_text_used"] is False and len(fake.calls) == 1
    finally:
        release.set()


def test_the_ai_gets_the_75_second_deadline(client, church, fetched, monkeypatch):
    hymnal(church)
    fake = install()
    before = time.monotonic()
    suggest(client, church)
    after = time.monotonic()
    deadline = fake.calls[0]["deadline"]
    assert before + hymns_usecase.SUGGEST_BUDGET_S <= deadline <= after + hymns_usecase.SUGGEST_BUDGET_S


def test_one_token_per_slot_is_topped_up_to_three(client, church, fetched):
    hymnal(church)

    def one_each(messages):             # one different hymn per slot
        prompt = messages[1]["content"]
        return json.dumps({slot: [tokens_for(prompt, slot)[i]]
                           for i, slot in enumerate(("opening", "response", "closing"))})

    install(reply=one_each)
    body = suggest(client, church, {"scriptures": ["Psalm 23"]})
    for slot, items in body["slots"].items():
        assert [h["source"] for h in items] == ["ai", "candidates", "candidates"], slot


def test_the_nt_readings_matches_lead_the_response_candidates(client, church, fetched):
    for i in range(1, 31):
        add(church, f"OT {i}", i, refs="Isaiah 6:3")
    for i in range(1, 4):
        add(church, f"Gospel {i}", 100 + i, refs="Mark 1:10")
    fake = install()
    suggest(client, church, {"scriptures": ["Isaiah 6:1-8", "Mark 1:9-15"], "selected_nt_ref": "Mark 1:9-15"})
    prompt = prompt_of(fake)
    lines = {line.split(" | ")[0]: line.split(" | ")[1] for line in prompt.splitlines()
             if re.match(r"^H\d+ \| ", line)}
    assert [lines[t] for t in tokens_for(prompt, "response", n=3)] == ["Gospel 1", "Gospel 2", "Gospel 3"]


def test_exclude_recent_leaves_recent_hymns_out_of_prompt_and_answer(client, church, fetched):
    hymnal(church, n=20)
    use(church, "hymn 1", "2026-09-27")              # within 12 weeks before
    use(church, "Hymn 2", "2026-12-27")              # the last day after
    use(church, "Hymn 3", DATE)                      # the service date itself: not excluded
    use(church, "Hymn 4", "2026-07-11")              # one day too early
    fake = install()
    body = suggest(client, church, {"scriptures": ["Psalm 23"]})
    assert body["excluded_recent_count"] == 2
    prompt = prompt_of(fake)
    assert "| Hymn 1 |" not in prompt and "| Hymn 2 |" not in prompt
    assert "| Hymn 3 |" in prompt and "| Hymn 4 |" in prompt
    returned = {t for titles in slot_titles(body).values() for t in titles}
    assert not {"Hymn 1", "Hymn 2"} & returned


def test_without_exclusion_recent_hymns_may_appear_with_their_date(client, church, fetched):
    hymnal(church, n=3)
    use(church, "Hymn 1", "2026-09-27")
    install()
    body = suggest(client, church, {"exclude_recent": False, "scriptures": ["Psalm 23"]})
    recent = {h["title"]: h["recent_use_on"] for items in body["slots"].values() for h in items}
    assert recent["Hymn 1"] == "2026-09-27" and body["excluded_recent_count"] == 0


def test_empty_pool_and_everything_recent_are_422(client, church, make_church, fetched):
    install()
    error = suggest(client, church, status=422)["error"]
    assert (error["message"], error["fields"]) == (
        "This hymnal has no hymns to suggest from.", {"hymnal": "This hymnal has no hymns to suggest from."})
    add(church, "   ", 1)                                            # blank titles never count
    assert suggest(client, church, status=422)["error"]["message"] == "This hymnal has no hymns to suggest from."
    add(church, "Only", 2)
    use(church, "Only", "2026-09-27")
    error = suggest(client, church, status=422)["error"]
    assert error["message"] == ("Every hymn in this hymnal was used within 12 weeks of this service. "
                                "Turn off “Exclude” and try again.")
    assert "fields" not in error
    for code in ("NOWHERE", ""):
        error = suggest(client, church, {"hymnal": code}, status=422)["error"]
        assert error["fields"] == {"hymnal": "That hymnal isn't in this church's library."}


def test_body_limits_and_extra_fields_are_422(client, church, fetched):
    hymnal(church, n=3)
    install()
    for body in ({"surprise": 1}, {"occasion": "o" * 301}, {"scriptures": ["x" * 201]},
                 {"scriptures": ["John 3"] * 21}, {"nt_text": "t" * 20_001},
                 {"current_picks": {"offertory": None}}, {"service_date_iso": "2026-10-4"}):
        error = suggest(client, church, body, status=422)["error"]
        assert (error["code"], error["message"]) == ("invalid_request", "The request was not valid."), body
    r = client.post("/hymns/suggestions", json={}, headers=church_headers(EMAIL, church))
    assert r.json()["error"]["fields"] == {"service_date_iso": "Required."}


def test_the_rubric_is_read_fresh_and_a_bad_one_falls_back(client, church, fetched):
    hymnal(church, n=5)
    fake = install()
    suggest(client, church)
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in prompt_of(fake)
    churches.update_church_rubric(church, {"hymns": {"closing": ["ends with a rousing doxology"]},
                                           "prefer_before_year": 1900})
    suggest(client, church)
    assert "A good Closing (Sending) Hymn:\n- ends with a rousing doxology" in prompt_of(fake)
    assert "Prefer hymns written before 1900" in prompt_of(fake)
    stored = churches.get_church(church)["settings"]
    churches.update_church(church, settings={**stored, "rubric": {"prefer_before_year": "x"}})
    suggest(client, church)
    assert "Prefer hymns written before 1970" in prompt_of(fake)


def test_isolation_roles_and_another_churchs_ids(client, isolation_world, make_user, fetched):
    world = isolation_world
    for i in range(1, 6):
        add(world.church_a, f"A {i}", i, theme="joy", refs="Psalm 23")
    b_id = add(world.church_b, "B's secret hymn", 1, theme="joy", refs="Psalm 23", hymnal="BONLY")
    churches.update_church_rubric(world.church_b, {"hymns": {"closing": ["B's own checklist"]}})
    fake = install()
    assert_church_isolated(client, "POST", "/hymns/suggestions", world=world,
                           json={"service_date_iso": DATE})
    body = suggest(client, world.church_a, {"current_picks": {"opening": b_id}}, email=world.a)
    everything = json.dumps(body) + prompt_of(fake)
    assert b_id not in everything and "B's secret hymn" not in everything
    assert "B's own checklist" not in prompt_of(fake)
    assert suggest(client, world.church_a, {"hymnal": "BONLY"}, email=world.a, status=422)["error"][
        "message"] == "That hymnal isn't in this church's library."
    use(world.church_b, "A 1", "2026-09-27")                      # B's usage never marks A's hymns
    body = suggest(client, world.church_a, email=world.a)
    assert body["excluded_recent_count"] == 0
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        suggest(client, world.church_a, email=email)


def test_the_41st_call_by_a_user_in_ten_minutes_is_429(client, church, owner, fetched, limiter_clock):
    hymnal(church, n=3)
    install()
    for _ in range(40):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429, r.text
    assert r.json()["error"]["code"] == "rate_limited"
    assert r.headers["Retry-After"] == "15"                      # 40 per 600 s: one token every 15 s
    limiter_clock.advance(15)
    assert suggest(client, church)["hymnal"] == "GG2013"


def test_the_401st_call_by_a_church_in_a_day_is_429(client, church, make_user, make_church, fetched,
                                                     limiter_clock):
    hymnal(church, n=3)
    install()
    for _ in range(399):
        ratelimit.consume("ai", user_id=uuid.uuid4(), church_id=church)
    assert suggest(client, church)["hymnal"] == "GG2013"         # the church's 400th today
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429, r.text
    other = make_church(name="Other", owner_user_id=make_user(email="other@example.com"))
    hymnal(other, n=3)
    assert suggest(client, other, email="other@example.com")["hymnal"] == "GG2013"


def test_a_rejected_request_still_spends_a_token(client, church, owner, fetched, limiter_clock):
    # F §1.8: rate_limit("ai") is a dependency, resolved before the body is validated
    # and before the usecase runs, so both kinds of 422 cost a token (plan, "Buckets").
    hymnal(church, n=3)
    fake = install()
    for _ in range(38):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    suggest(client, church, {"extra": 1}, status=422)              # Pydantic: the 39th token
    suggest(client, church, {"hymnal": "NOWHERE"}, status=422)     # the usecase: the 40th
    r = client.post("/hymns/suggestions", json={"service_date_iso": DATE}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429, r.text
    assert fake.calls == []
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
````

**with:**

````python
            "cache, integrations.http, "
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search, hymn_suggest, usecases.hymns; "
            "bad = sorted({m.split('.')[0] for m in sys.modules} & {'fastapi', 'starlette', 'streamlit'}); "
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymn_suggestions.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
```

**Expected:** `19 failed, 28 passed, 1 skipped in <t>s`: all 18 new tests (the route is a 404) and `test_routes_document_the_error_body`. The import-guard tests already pass: `hymn_suggest` and `usecases.hymns` exist.

- [ ] **Step 4 (agent): Write the usecase, the route and the pool reset**

**In `backend/api/routes/hymns.py`, replace:**

````python
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api.deps import ActiveChurch, require_church
from api.errors import error_responses
from api.schemas import IsoDate, Page
from usecases import hymns
````

**with:**

````python
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import IsoDate, Page
from usecases import hymns
````

**In `backend/api/routes/hymns.py`, replace:**

````python
    unparsed_refs: list[str]           # query refs that could not be read as scripture
    total_matched: int                 # before max_results truncation
    items: list[HymnMatchOut]          # passage tier first, then chapter tier


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
````

**with:**

````python
    unparsed_refs: list[str]           # query refs that could not be read as scripture
    total_matched: int                 # before max_results truncation
    items: list[HymnMatchOut]          # passage tier first, then chapter tier


class SlotPicks(BaseModel):
    """Exclusion hints only: never resolved, loaded or echoed, so an id from
    another church or a deleted hymn is ignored, not a 404 (S API notes; the
    declared exception to F §1.2 rules 2 and 5)."""

    model_config = ConfigDict(extra="forbid")

    opening: Optional[uuid.UUID] = None
    response: Optional[uuid.UUID] = None
    closing: Optional[uuid.UUID] = None


class HymnSuggestionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_date_iso: IsoDate
    occasion: Annotated[str, StringConstraints(max_length=300)] = ""
    scriptures: list[Annotated[str, StringConstraints(max_length=200)]] = Field(default_factory=list, max_length=20)
    selected_nt_ref: Optional[Annotated[str, StringConstraints(max_length=200)]] = None
    nt_text: Optional[Annotated[str, StringConstraints(max_length=20_000)]] = None
    hymnal: Optional[Annotated[str, StringConstraints(max_length=20)]] = None
    exclude_recent: bool = True
    current_picks: SlotPicks = Field(default_factory=SlotPicks)


class SuggestedHymnOut(HymnOut):
    source: Literal["ai", "candidates"]   # "candidates" = added by the minimum top-up; the UI ignores it


class SuggestedSlots(BaseModel):
    opening: list[SuggestedHymnOut]       # at most 5, best first
    response: list[SuggestedHymnOut]
    closing: list[SuggestedHymnOut]


class HymnSuggestionsOut(BaseModel):
    hymnal: str
    nt_ref: Optional[str]                 # the NT reference used for context
    nt_text_used: bool
    excluded_recent_count: int
    slots: SuggestedSlots


def hymn_out(view: hymns.HymnView) -> HymnOut:
    return HymnOut(**asdict(view))


@router.get("/hymns", response_model=Page[HymnOut], responses=error_responses(401, 403, 422, 503))
````

**Append to `backend/api/routes/hymns.py`:**

````python


@router.post("/hymns/suggestions", response_model=HymnSuggestionsOut,
             dependencies=[Depends(rate_limit("ai"))],
             responses=error_responses(401, 403, 422, 429, 502, 503, 504))
def suggest_hymns(payload: HymnSuggestionIn, church: ActiveChurch = Depends(require_church),
                  user: CurrentUser = Depends(get_current_user)) -> HymnSuggestionsOut:
    """AI fills each empty slot with its top pick and gives every slot 2-4 other
    ideas (owner decision 3; owner answer Q1). Charged to the `ai` bucket
    (40 per 10 min per user, 400 per day per church; F §1.8)."""
    request = hymns.SuggestionRequest(
        service_date=payload.service_date_iso, occasion=payload.occasion, scriptures=payload.scriptures,
        selected_nt_ref=payload.selected_nt_ref, nt_text=payload.nt_text, hymnal=payload.hymnal,
        exclude_recent=payload.exclude_recent, current_picks=payload.current_picks.model_dump())
    result = hymns.suggest_hymns(church.id, user.id, request)
    return HymnSuggestionsOut(
        hymnal=result.hymnal, nt_ref=result.nt_ref, nt_text_used=result.nt_text_used,
        excluded_recent_count=result.excluded_recent_count,
        slots=SuggestedSlots(**{slot: [SuggestedHymnOut(**asdict(v)) for v in views]
                                for slot, views in result.slots.items()}))
````

**In `backend/tests/conftest.py`, replace:**

````python
    FakeAI installed by set_ai_for_tests for the whole process (slice 3a). Each
    test starts with no fake and the settings read again from the environment,
    so a fake or a configured key never leaks from an earlier test.

    Resets only when the module is already imported (the deferred-import rule
````

**with:**

````python
    FakeAI installed by set_ai_for_tests for the whole process (slice 3a). Each
    test starts with no fake and the settings read again from the environment,
    so a fake or a configured key never leaks from an earlier test. From Task 13,
    usecases.hymns first joins and rebuilds its NT-fetch pool, so no fetch an
    earlier test blocked (and released) is still running.

    Resets only when the module is already imported (the deferred-import rule
````

**In `backend/tests/conftest.py`, replace:**

````python
    Resets only when the module is already imported (the deferred-import rule
    at the top of this file)."""
    import sys

    module = sys.modules.get("integrations.openai_client")
    if module is not None:
        module.reset_for_tests()
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
````

**with:**

````python
    Resets only when the module is already imported (the deferred-import rule
    at the top of this file)."""
    import sys

    for name in ("usecases.hymns", "integrations.openai_client"):
        module = sys.modules.get(name)
        if module is not None:
            module.reset_for_tests()
    yield


# --- slice 1: network-free tests and the Postgres test database (F §5.1, §5.3) ---
````

**In `backend/usecases/hymns.py`, replace:**

````python
  and the rubric's newer-than-preferred flag.
- scripture_matches: POST /hymns/scripture-matches.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
````

**with:**

````python
  and the rubric's newer-than-preferred flag.
- scripture_matches: POST /hymns/scripture-matches.
- suggest_hymns: POST /hymns/suggestions. Reads in one session that closes
  before any external call (F §1.8), then the NT text (10 s budget on its
  own pool), then one OpenAI call, all inside a 75 s deadline.

Every function takes the active church's id only (F §1.2 rule 1) and reads in
````

**In `backend/usecases/hymns.py`, replace:**

````python
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Optional

from sqlalchemy.orm import Session
````

**with:**

````python
from __future__ import annotations

import contextvars
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session
````

**In `backend/usecases/hymns.py`, replace:**

````python
from sqlalchemy.orm import Session

import hymn_usage
from db import session_scope
from domain_errors import InvalidInput
from hymn_ranking import is_newer_than_preferred
from hymn_search import match_hymns, parse_themes, usage_key
````

**with:**

````python
from sqlalchemy.orm import Session

import hymn_suggest
import hymn_usage
from db import session_scope
from domain_errors import DomainError, InvalidInput, NotConfigured
from hymn_ranking import is_newer_than_preferred
from hymn_search import match_hymns, parse_themes, usage_key
from integrations import openai_client
````

**In `backend/usecases/hymns.py`, replace:**

````python
from repos.hymns import HymnalSummary, HymnRecord
from scripture_refs import parse_refs, split_alternatives
from service_rubric import merge_rubric

logger = logging.getLogger(__name__)
````

**with:**

````python
from repos.hymns import HymnalSummary, HymnRecord
from scripture_refs import default_nt_ref, parse_refs, split_alternatives
from service_rubric import merge_rubric
from usecases import passages

logger = logging.getLogger(__name__)
````

**In `backend/usecases/hymns.py`, replace:**

````python
logger = logging.getLogger(__name__)


REFS_MESSAGE = "Enter at least one scripture reference."
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."


@dataclass(frozen=True)
class DefaultHymnal:
    default_hymnal: Optional[str]      # settings["default_hymnal"] verbatim, when a non-blank string
````

**with:**

````python
logger = logging.getLogger(__name__)


REFS_MESSAGE = "Enter at least one scripture reference."
HYMNAL_MESSAGE = "That hymnal isn't in this church's library."
EMPTY_POOL_MESSAGE = "This hymnal has no hymns to suggest from."
ALL_RECENT_MESSAGE = ("Every hymn in this hymnal was used within 12 weeks of this service. "
                      "Turn off \u201cExclude\u201d and try again.")
AI_NOT_CONFIGURED_MESSAGE = "AI suggestions aren't set up on this app yet."

SUGGEST_BUDGET_S = 75.0            # the server deadline for POST /hymns/suggestions (F §1.8)
NT_FETCH_BUDGET_S = 10.0           # the NT text fetch's share of it
NT_TRANSLATION = "web"             # never ESV on the server (S Behavior change 8)
MAX_COMPLETION_TOKENS = 1200

# The NT fetch runs here so its 10 s budget holds although get_passage_text
# takes no deadline (up to 20 s). An abandoned fetch finishes in the
# background and still fills slice 2's passage cache.
_NT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nt-fetch")


@dataclass(frozen=True)
class DefaultHymnal:
    default_hymnal: Optional[str]      # settings["default_hymnal"] verbatim, when a non-blank string
````

**Append to `backend/usecases/hymns.py`:**

````python


# --- AI suggestions (S Backend 3.6-3.8) ---------------------------------------------


@dataclass(frozen=True)
class SuggestionRequest:
    service_date: date
    occasion: str = ""
    scriptures: list[str] = field(default_factory=list)
    selected_nt_ref: Optional[str] = None
    nt_text: Optional[str] = None
    hymnal: Optional[str] = None
    exclude_recent: bool = True
    current_picks: dict[str, Optional[uuid.UUID]] = field(
        default_factory=lambda: {"opening": None, "response": None, "closing": None})


@dataclass(frozen=True)
class SuggestedView(HymnView):
    source: str                        # "ai", or "candidates" (the minimum top-up)


@dataclass(frozen=True)
class HymnSuggestions:
    hymnal: str
    nt_ref: Optional[str]
    nt_text_used: bool
    excluded_recent_count: int
    slots: dict[str, list[SuggestedView]]


def reset_for_tests() -> None:
    """Tests: join the NT pool (every blocked fetch released first) and build a new one."""
    global _NT_EXECUTOR
    _NT_EXECUTOR.shutdown(wait=True)
    _NT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nt-fetch")


def _nt_context(client_text: Optional[str], nt_ref: Optional[str], fetch_text: Callable,
                deadline: float, clock: Callable[[], float]) -> tuple[Optional[str], str]:
    """(text, source): the client's text, else WEB fetched within NT_FETCH_BUDGET_S
    and the deadline. A timeout, a failure or no text is (None, ...), never raised."""
    if (client_text or "").strip():
        return client_text, "client"
    if not nt_ref:
        return None, "none"
    future = _NT_EXECUTOR.submit(contextvars.copy_context().run, fetch_text, nt_ref, NT_TRANSLATION)
    try:
        text = future.result(timeout=max(0.0, min(NT_FETCH_BUDGET_S, deadline - clock())))
    except FutureTimeout:
        return None, "timeout"
    except Exception as exc:                      # the fetch must never fail the suggestions
        logger.warning("hymn_suggestions nt_fetch_failed error=%s", type(exc).__name__)
        return None, "none"
    return (text, "fetched") if (text or "").strip() else (None, "none")


def _per_slot(values: dict[str, Any]) -> str:
    return "/".join(str(values[slot]) for slot in hymn_suggest.SLOTS)


def suggest_hymns(church_id: uuid.UUID, user_id: uuid.UUID, req: SuggestionRequest, *,
                  ai: Any = openai_client, fetch_text: Optional[Callable] = None,
                  clock: Callable[[], float] = time.monotonic) -> HymnSuggestions:
    """S Backend 3.6 steps 0-10. user_id is for the rate limit only (the route's
    dependency charges it); nothing here writes."""
    started = clock()
    deadline = started + SUGGEST_BUDGET_S
    fetch = fetch_text or passages.get_passage_text
    facts: dict[str, Any] = {"hymnal": "-", "pool": 0, "excluded": 0, "nt_source": "-"}
    try:
        with session_scope() as s:                                   # step 1: read, then close
            code = selected_hymnal(church_id, req.hymnal, s)
            pool = hymn_repo.list_hymnal_records(church_id, code, session=s) if code else []
            usage = hymn_usage.usage_near(church_id, req.service_date, session=s)
            overrides = churches.get_church_rubric_overrides(church_id, session=s)
        rubric = merge_rubric(overrides)
        pool = [h for h in pool if (h.title or "").strip()]
        facts.update(hymnal=code or "-", pool=len(pool))
        if not pool:                                                  # step 2
            raise InvalidInput(EMPTY_POOL_MESSAGE, field="hymnal")
        eligible = ([h for h in pool if usage_key(h.title) not in usage]   # step 3
                    if req.exclude_recent else pool)
        excluded = len(pool) - len(eligible)
        facts["excluded"] = excluded
        if not eligible:
            raise InvalidInput(ALL_RECENT_MESSAGE)
        if not ai.ai_available():                                     # step 4
            raise NotConfigured(AI_NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
        nt_ref = (req.selected_nt_ref or "").strip() or default_nt_ref(req.scriptures)   # step 5
        nt_text, facts["nt_source"] = _nt_context(req.nt_text, nt_ref, fetch, deadline, clock)
        candidates = hymn_suggest.build_candidates(eligible, req.scriptures, nt_ref=nt_ref,  # step 6
                                                   current_picks=req.current_picks, rubric=rubric)
        messages, token_map = hymn_suggest.build_prompt(                                  # step 7
            candidates, occasion=req.occasion, scriptures=req.scriptures, nt_ref=nt_ref,
            nt_text=nt_text, rubric=rubric)
        logger.debug("hymn_suggestions prompt=%r", messages)
        try:
            raw = ai.complete(messages, max_completion_tokens=MAX_COMPLETION_TOKENS,     # step 8
                              json_mode=True, deadline=deadline)
        except NotConfigured:
            raise NotConfigured(AI_NOT_CONFIGURED_MESSAGE, code="ai_not_configured") from None
        parsed = hymn_suggest.parse_suggestion_json(raw)                                  # step 9
        resolved = hymn_suggest.resolve_suggestions(parsed, token_map, eligible, candidates)
        final = hymn_suggest.finalize_slots(resolved, req.current_picks, candidates)
    except DomainError as exc:
        _log(facts, started, clock, outcome=exc.code)
        raise
    year = rubric["prefer_before_year"]
    slots = {slot: [SuggestedView(**asdict(hymn_view(item.record, usage=usage, prefer_before_year=year)),
                                  source=item.source) for item in items]
             for slot, items in final.items()}
    facts.update(
        candidates=_per_slot({k: len(v) for k, v in candidates.by_slot.items()}),
        resolved=_per_slot({k: len(v) for k, v in resolved.items()}),
        topped_up=_per_slot({k: sum(i.source == "candidates" for i in v) for k, v in final.items()}),
        modes=_per_slot(candidates.modes),
        newer_or_unknown=_per_slot({k: sum(r.text_year is None or r.text_year >= year for r in v)
                                    for k, v in candidates.by_slot.items()}),
        prefer_before_year=year, prefer_familiar=rubric["prefer_familiar"],
        rubric_customized=bool(overrides))
    _log(facts, started, clock, outcome="ok")
    return HymnSuggestions(hymnal=code, nt_ref=nt_ref, nt_text_used=nt_text is not None,
                           excluded_recent_count=excluded, slots=slots)


def _log(facts: dict[str, Any], started: float, clock: Callable[[], float], *, outcome: str) -> None:
    """One line per call (S Backend 3.6 step 10, 3.8 "Logs"): counts, modes,
    the model, the duration and the outcome. Never the prompt, nt_text or titles."""
    details = " ".join(f"{key}={value}" for key, value in facts.items())
    logger.info("hymn_suggestions %s model=%s duration_ms=%d outcome=%s", details,
                openai_client.ai_settings().model or "-", round((clock() - started) * 1000), outcome)
````

- [ ] **Step 5 (agent): Run the tests; regenerate and typecheck; run the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_hymn_suggestions.py backend/tests/test_api_app.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_route_guards.py 2>&1 | tail -1
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git diff --numstat -- frontend/src/lib/api
(cd frontend && npm run typecheck)
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `52 passed, 1 skipped in <t>s` (the hung-fetch test takes about 0.05 s; the whole file runs in a few seconds); numstat exactly `441	0	frontend/src/lib/api/openapi.json` and `207	0	frontend/src/lib/api/schema.d.ts`; `tsc` prints nothing; `1115 passed, 11 skipped in <t>s`; then ` M` for `backend/api/routes/hymns.py`, `backend/tests/conftest.py`, `backend/tests/test_api_app.py`, `backend/tests/test_no_streamlit_in_core.py`, `backend/usecases/hymns.py`, the two generated files, and `?? backend/tests/test_api_hymn_suggestions.py`.

- [ ] **Step 6 (agent): Run the threaded tests three times**

```bash
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_api_hymn_suggestions.py backend/tests/test_openai_client.py 2>&1 | tail -1; done
```

**Expected:** `42 passed in <t>s`, three times. A failure even once is a failure (CI runs each test once).

- [ ] **Step 7 (agent): Commit**

```bash
git add backend/api/routes/hymns.py backend/usecases/hymns.py backend/tests/conftest.py backend/tests/test_api_app.py \
        backend/tests/test_no_streamlit_in_core.py backend/tests/test_api_hymn_suggestions.py \
        frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -m "API: POST /hymns/suggestions inside a 75 s deadline, rate limited by the ai bucket (S API row 4, Backend 3.6-3.8; F §1.8; decision 3; AC4-AC8, AC11, AC18)" -m "One read session (hymnal, pool, usage around the service date, rubric)
closes before any external call. An empty pool or an all-recent pool is a
422; no AI is 503 ai_not_configured before any call. The NT text is the
client's, or WEB fetched within 10 s on its own pool; then one OpenAI call
with max_completion_tokens 1200, JSON mode and the deadline. current_picks
are exclusion hints only, never resolved or echoed. Only empty slots get a
top pick (owner answer Q1). One hymn_suggestions log line per call, never
the prompt, nt_text or titles. 40 per 10 min per user, 400 per day per
church.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 8 (controller): Review checkpoint and backup push**

Walk S 3.6 steps 0-10 against `suggest_hymns` (the order of the 422s and the 503, the read session closed before `_nt_context`, the deadline passed to `complete`), the error table in S API against `test_ai_errors_return_their_code_and_exact_message`, and S 3.7's worst case (75 s deadline; the client leaves about 14 s of the 90 s client timeout). Push the backup.

Counts after Task 13: backend **1115 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 14: Delete the Streamlit-era hymn code and `lxml` (S Backend 1 row `worship_service.py`, `requirements.txt`, 5 "Streamlit coupling removed"; F §2.3; AC9, AC19; owner decision 2; clarifications 14, 15)

Everything the old hymn code did now lives in `hymn_search`, `hymn_suggest`, `hymn_ranking` and `usecases.hymns`, with tests, so it is deleted: from `worship_service.py`, `_BOOK_ABBREVS`, `_scripture_search_variants`, `hymns_by_scripture` (with the Notion path), `_OPENING_THEMES`, `_CLOSING_THEMES`, `_CANDIDATES_PER_SLOT`, `_CANDIDATES_KEPT_FOR_NEWER`, `_hymn_matches_theme`, `suggest_hymns_for_service`, `hymn_display_info`, `_hymnary_audio_url`, `resolve_hymnary_audio_url`, `_hymnary_audio_resolve_cache`, the `NotionHymnsDB` `TYPE_CHECKING` import, `load_dotenv()` at import, and the imports only they used (`urlparse`, `urlunparse`, `get_property_value`, `hymn_ranking`, `TYPE_CHECKING`). `generate_liturgy` and `build_docx` stay until slices 4 and 5a. `lxml` leaves `requirements.txt` (its only runtime user was the audio resolver; `beautifulsoup4` stays for `fill_from_hymnary.py`). PR #4's `test_suggest_hymns.py` (13 tests) is deleted with the function it tested; clarification 15 maps each of its cases to its equivalent. The parity test loses its old half, and a new test pins AC9.

**Files:**
- Modify: `backend/worship_service.py` (a Run block: the module docstring and imports, and the hymn block from `# Common Bible book abbreviations` to the line before `SERMON_TEXT_LIMIT = 2000`)
- Modify: `backend/requirements.txt` (`lxml>=4.9.0` removed), `backend/hymn_ranking.py` (one docstring line)
- Modify (test): `backend/tests/test_hymn_match_parity.py` (whole file shown)
- Delete: `backend/tests/test_suggest_hymns.py`

**Interfaces:**
- Consumes: every equivalent listed in clarification 15 (Tasks 6, 11, 12, 13).
- Produces: `worship_service` without the hymn helpers (`generate_liturgy`, `build_docx` and the docx helpers remain); `test_hymn_match_parity.py::test_the_old_hymn_code_is_gone`.

- [ ] **Step 1 (agent): Confirm the equivalents exist and nothing else imports the old names**

```bash
.venv/bin/python -m pytest -q | tail -1
grep -rnE "hymns_by_scripture|suggest_hymns_for_service|hymn_display_info|resolve_hymnary_audio_url|_hymnary_audio_url" --include=*.py backend streamlit_tests streamlit_views app.py ui_helpers.py | grep -v "^backend/worship_service.py"
```

**Expected:** `1115 passed, 11 skipped in <t>s`; then exactly these hits, and nothing else:
- `app.py:24`, `:25`, `:26` (the three imported names) and `app.py:690`, `:707`, `:769` (their calls): frozen Streamlit's copy on `main`, which no test imports and which stops importing after this task (owner decision 2);
- `backend/hymn_ranking.py:31` (a docstring naming `hymn_display_info`; this task rewords it);
- `backend/tests/test_hymn_suggest.py:7` (a docstring);
- `backend/tests/test_hymn_match_parity.py:5` and `:40` (the old half this task removes);
- `backend/tests/test_suggest_hymns.py:48`, `:70`, `:193`, `:194`, `:206` (the file this task deletes).

Any other file: stop and ask.

- [ ] **Step 2 (agent): Write the failing test, drop the old half and delete PR #4's test file**

**Replace the whole of `backend/tests/test_hymn_match_parity.py` with:**

````python
"""Characterization of the scripture matcher (F §2.3.1; slice 3 spec, Testing
"Characterization first"): what matched under the old substring matcher still
matches, and the four verified over-matches (inventory §0 item 5) do not.

Task 5 ran each pair through worship_service.hymns_by_scripture as well; Task
14 deleted that function and this file's old half in the same commit.
"""
from dataclasses import dataclass

from hymn_search import match_hymns

# (query, hymn scripture_refs) pairs that matched under the old substring matcher.
STILL_MATCH = [
    ("Isaiah 6:1-8", "Isaiah 6:1-8"),             # the exact reference
    ("Matthew 17:1-9", "Matthew 17"),             # book + chapter
    ("Romans 8:28-39", "Romans 8:28"),            # the first verse
    ("Genesis 12:1-4a", "Genesis 12:1-4"),        # an a/b suffix dropped
    ("Luke 24:13-35 or Mark 16:1-8", "Mark 16:1-8"),   # the " or " alternative
    ("Psalm 23", "Psalm 23"),
]

# Verified over-matches: the old matcher said yes; the new one says no.
OVER_MATCHES = [
    ("Isaiah 9:6", "Genesis 9:6"),
    ("Mark 1:9-15", "Mark 10:45"),
    ("Psalm 1", "Psalm 119"),
    ("John 3:1-17", "1 John 3:16"),
]


@dataclass(frozen=True)
class H:
    title: str
    scripture_refs: str


def _new(query: str, refs: str) -> bool:
    queries = [part.strip() for part in query.split(" or ")]
    return bool(match_hymns([H("Hymn", refs)], queries).items)


def test_pairs_that_matched_before_still_match():
    for query, refs in STILL_MATCH:
        assert _new(query, refs), (query, refs)


def test_the_four_over_matches_no_longer_match():
    for query, refs in OVER_MATCHES:
        assert not _new(query, refs), (query, refs)


def test_the_old_hymn_code_is_gone():
    """AC9: the Streamlit-era matcher, suggester, display helper, audio
    resolver and Notion path are deleted, with lxml, their only user's package."""
    from pathlib import Path

    import worship_service

    for name in ("_BOOK_ABBREVS", "_scripture_search_variants", "hymns_by_scripture", "_OPENING_THEMES",
                 "_CLOSING_THEMES", "_hymn_matches_theme", "suggest_hymns_for_service",
                 "hymn_display_info", "_hymnary_audio_url", "resolve_hymnary_audio_url",
                 "_hymnary_audio_resolve_cache", "_CANDIDATES_PER_SLOT", "_CANDIDATES_KEPT_FOR_NEWER"):
        assert not hasattr(worship_service, name), name
    source = Path(worship_service.__file__).read_text()
    assert "load_dotenv" not in source and "NotionHymnsDB" not in source
    requirements = (Path(worship_service.__file__).parent / "requirements.txt").read_text()
    assert "lxml" not in requirements
    assert callable(worship_service.generate_liturgy) and callable(worship_service.build_docx)
````

**Delete `backend/tests/test_suggest_hymns.py`.**

```bash
git rm -q backend/tests/test_suggest_hymns.py
```

- [ ] **Step 3 (agent): Run it to see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_match_parity.py 2>&1 | tail -2
```

**Expected:** `FAILED backend/tests/test_hymn_match_parity.py::test_the_old_hymn_code_is_gone - AssertionError: _BOOK_ABBREVS` and `1 failed, 2 passed in <t>s`.

- [ ] **Step 4 (agent): Delete the code and `lxml`**

**Run from the repo root (edits `backend/worship_service.py`):**

````python
from pathlib import Path

path = Path("backend/worship_service.py")
source = path.read_text()
# The hymn code: from the book-abbreviation table to the line before SERMON_TEXT_LIMIT.
start = source.index("# Common Bible book abbreviations (full name -> variants to try)")
end = source.index("SERMON_TEXT_LIMIT = 2000")
source = source[:start] + source[end:]
old_header = '''"""
Worship service generator: hymn suggestions by scripture, OpenAI liturgy,
and Word document export.
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING, Dict, Any, List, Optional
from io import BytesIO
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from hymn_utils import get_property_value
import hymn_ranking
import liturgy_prompts
import service_rubric

if TYPE_CHECKING:  # notion-client is migration-only; only needed for type hints here
    from notion_hymns import NotionHymnsDB

load_dotenv()

logger = logging.getLogger(__name__)

# Cache for resolved Hymnary audio URLs (number -> url) to avoid re-fetching
_hymnary_audio_resolve_cache: Dict[int, Optional[str]] = {}
'''
new_header = '''"""
Worship service generator: OpenAI liturgy and Word document export (the
hymn helpers moved to hymn_search, hymn_suggest and usecases.hymns in slice 3).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

import liturgy_prompts
import service_rubric

logger = logging.getLogger(__name__)
'''
assert source.count(old_header) == 1
path.write_text(source.replace(old_header, new_header))
print("worship_service.py:", len(path.read_text().splitlines()), "lines")
````

**Expected** output of the Run block: `worship_service.py: 447 lines`.

**In `backend/hymn_ranking.py`, replace:**

````python
    """True when the words' year is known and not before the preferred year
    (the rule PR #4's hymn_display_info used for its newer_than_preferred)."""
    return year is not None and prefer_before_year is not None and year >= prefer_before_year
````

**with:**

````python
    """True when the words' year is known and not before the preferred year
    (PR #4's rule for newer_than_preferred, moved here from worship_service)."""
    return year is not None and prefer_before_year is not None and year >= prefer_before_year
````

**In `backend/requirements.txt`, replace:**

````text
httpx>=0.25.0
lxml>=4.9.0
playwright>=1.40.0
````

**with:**

````text
httpx>=0.25.0
playwright>=1.40.0
````

- [ ] **Step 5 (agent): Run the tests, the AC9 gates and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_match_parity.py backend/tests/test_generate_liturgy.py 2>&1 | tail -1
grep -rnE "hymns_by_scripture|suggest_hymns_for_service|hymn_display_info|_hymnary_audio|resolve_hymnary_audio_url" --include=*.py backend | grep -v "^backend/tests/"
grep -nE "NotionHymnsDB|load_dotenv" backend/worship_service.py backend/hymn_search.py backend/hymn_suggest.py backend/usecases/hymns.py backend/integrations/openai_client.py
grep -n "lxml" backend/requirements.txt
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `15 passed in <t>s` (3 in the parity file and `test_generate_liturgy.py`'s 12, unchanged); the three greps print nothing (clarification 14: `NotionHymnsDB` remains only in the migration-only CLIs); `1103 passed, 11 skipped in <t>s` (1115 + 1 − 13); then ` M backend/hymn_ranking.py`, ` M backend/requirements.txt`, ` M backend/tests/test_hymn_match_parity.py`, `D  backend/tests/test_suggest_hymns.py`, ` M backend/worship_service.py`.

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/worship_service.py backend/requirements.txt backend/hymn_ranking.py backend/tests/test_hymn_match_parity.py
git commit -m "Cleanup: delete the Streamlit-era hymn matcher, suggester, display helper, audio resolver and lxml (S Backend 1, 5; F §2.3; AC9, AC19)" -m "hymns_by_scripture (and its Notion path), suggest_hymns_for_service,
hymn_display_info, the Hymnary audio resolver and its cache, the theme and
candidate constants, the NotionHymnsDB import and load_dotenv() at import
leave worship_service.py; generate_liturgy and build_docx stay for slices 4
and 5a. lxml leaves requirements.txt. PR #4's test_suggest_hymns.py goes
with the function it tested: each case has an equivalent against the new
code (clarification 15). app.py on main no longer imports, as accepted in
2a (owner decision 2).

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Read `git show --stat HEAD` (5 files, about 830 lines deleted) and check that `generate_liturgy`'s tests still pass and clarification 15's mapping holds. Push the backup.

Counts after Task 14: backend **1103 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 15: Docs: F's decision D16 and amendment rows, S's "(3a plan)" notes and answers, the runbook's OpenAI rows (S open questions 1 and 2; F Decisions, Amendments, §1.3; owner answers Q1-Q3, A, B; clarifications 1-4, 8, 26, 27, 30)

This task writes the owner's answers and the plan's corrections where the next planner will read them. F's decisions table gains D16 (owner answer Q1), as S asks. F's amendments table gains three rows (the §1.3 `HymnalCode` scope, the §2.8 client details, the title-only usage key), and §1.3's sentence naming `GET /hymns?hymnal=` is corrected. S gains a header note, its usage key, its 5a row, its sample path and "Unchanged on purpose" corrected, both open questions marked answered, the first-lines follow-up, and a §3.7 note that httpx timeouts are per phase (clarification 30). The runbook's variables table gets the `OPENAI_*` rows, with the $15 cap, the retired-model symptom and `OPENAI_REASONING_EFFORT` (owner answers A and B; no owner marker). No test changes.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, `docs/ops-runbook.md`

- [ ] **Step 1 (agent): Confirm the anchors**

```bash
grep -c '^| D15 | Slice order' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -c '(for example `GET /hymns?hymnal=`)' docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -c '^1\. \*\*Recent use across hymnals' docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md
grep -c '^| `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`' docs/ops-runbook.md
grep -c 'leaves about 14 s under the 90 000 ms client timeout' docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md
```

**Expected:** `1` five times.

- [ ] **Step 2 (agent): Write the edits**

**In `docs/ops-runbook.md`, replace:**

````markdown
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3` and `3` (see Platform limits) | ops-1; read since ops-2 |
| `ESV_API_KEY` | optional: enables the ESV translation (secret). The new app reads it from the environment (`scripture_fetcher._esv_key()`) until slice 7 moves it into `api/settings.py`; while it is unset, `GET /translations` returns `esv_available: false` and ESV is hidden. | ops-1; read by the new app since slice 2a |
| `OPENAI_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` | carried over for later slices (secrets) | slice 0 |

Checked against Railway → the API service → Variables (names only) and Settings → Deploy → Healthcheck Path:
````

**with:**

````markdown
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | `3` and `3` (see Platform limits) | ops-1; read since ops-2 |
| `ESV_API_KEY` | optional: enables the ESV translation (secret). The new app reads it from the environment (`scripture_fetcher._esv_key()`) until slice 7 moves it into `api/settings.py`; while it is unset, `GET /translations` returns `esv_available: false` and ESV is hidden. | ops-1; read by the new app since slice 2a |
| `OPENAI_API_KEY` | the new app's own OpenAI key (secret), separate from the Streamlit app's, with a monthly budget cap of $15 set in the OpenAI dashboard (owner, 2026-09-29). Read by `integrations/openai_client.py` since slice 3a. Without it, or without `OPENAI_MODEL`, hymn suggestions answer 503 `ai_not_configured` and the startup log says `AI: not configured (...)`. When the cap is reached, suggestions read "not set up" until the next month, with `ERROR AI: quota exhausted (insufficient_quota)` in the log and no retries. | slice 0; read since slice 3a |
| `OPENAI_MODEL` | required with the key; no default in code. A non-reasoning, inexpensive chat model that accepts `response_format` json_object and `max_completion_tokens` (slice 3a plan, "Model"). The startup log names it: `AI: configured (model=...)`. If OpenAI retires the model (possible at any time after a deploy), suggestions read "not set up" and each call logs `ERROR AI: model not available (OPENAI_MODEL=...)`: set a model the project offers and redeploy. | slice 3a |
| `OPENAI_TIMEOUT_SECONDS`, `OPENAI_MAX_RETRIES`, `OPENAI_MAX_CONCURRENCY`, `OPENAI_TEMPERATURE` | optional: defaults 30, 1 and 4, and no temperature sent | slice 3a |
| `OPENAI_REASONING_EFFORT` | optional; unset by default, and then nothing is sent. Set it (for example `minimal` or `low`) only for a reasoning (GPT-5-family) model, which otherwise can spend its answer budget on hidden reasoning and answer "had a problem". | slice 3a |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` | carried over for a later slice (secrets) | slice 0 |

Checked against Railway → the API service → Variables (names only) and Settings → Deploy → Healthcheck Path:
````

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
| D14 | Invite links | The frontend builds `https://<origin>/join?code=…` itself. `/join` is a public route that keeps the code in sessionStorage across sign-in. Joining then takes a preview and an explicit **Join** tap (§4.3): Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6). | Works on localhost and in production with no backend config (owner decision 6). |
| D15 | Slice order | ops → 1 → 2 → 3 → 4 → 5a → 5b → (tester moves) → 6a → 6b → 7. 6b may run in parallel any time after 1. | This is the inventory §5 order. Two changes: the three deferred slice-0 backend fixes move from 1 into ops, and slice 1 also carries the platform foundations (§7). |

---
````

**with:**

````markdown
| D14 | Invite links | The frontend builds `https://<origin>/join?code=…` itself. `/join` is a public route that keeps the code in sessionStorage across sign-in. Joining then takes a preview and an explicit **Join** tap (§4.3): Preview then Join approved by the owner on 2026-09-26 (amendment to decision 6). | Works on localhost and in production with no backend config (owner decision 6). |
| D15 | Slice order | ops → 1 → 2 → 3 → 4 → 5a → 5b → (tester moves) → 6a → 6b → 7. 6b may run in parallel any time after 1. | This is the inventory §5 order. Two changes: the three deferred slice-0 backend fixes move from 1 into ops, and slice 1 also carries the platform foundations (§7). |
| D16 | AI hymn suggestions (slice 3; owner decision 3) | **Suggest fills only empty slots.** A hymn the member already chose is never overwritten; every slot, filled or empty, gets 2-4 other ideas (chips) under it. Owner answer Q1, 2026-09-29, recorded here as slice 3's open question 2 asked. | The member's own choice always wins, and the AI's top pick stays one tap away as a chip. |

---
````

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
| §4.6, §4.7, §4.8 | *(2026-09-29, slice 2c plan)* `isPristine` also counts a date the user picked, a reading set chosen in the switcher (which makes a default date the user's) and a translation override (owner answer Q2), so "New service" asks after them; the roll-forward keeps a picked or chosen date but not for a translation alone, which "New service" keeps (review answer A). Date & readings counts as done only with no field showing an error (review answer E). The lectionary fills only in the tab on screen, and a tab shown again first re-reads the stored draft and adopts it when newer. Date & readings ships (`SHIPPED_STEPS` holds "readings"). `ErrorState` takes a screen's own `message`, `retryLabel` and `retryDisabled`, and `ConfirmDialog` a `cancelLabel`, for the slice spec's "Try again" and "Keep mine". | 2c |
| §4.6, §4.8 | *(2026-09-29, slice 2c build)* "New service" leaves the translation override out of its question, since the fresh draft keeps it; `isPristine` still counts it. The lectionary's automatic fill is stamped 1 ms after the draft it changes (`DraftStore.autoUpdate`), not now, and a flush that finds a strictly newer stored draft adopts it instead of writing over it, so an automatic change never outranks another tab's edit. A lookup rate limited by a 429 is not asked again on focus, reconnect or mount before its `Retry-After`. `ConfirmDialog` also takes `onCancel` (called by its cancel button only) and `finalFocus`. | 2c |

---
````

**with:**

````markdown
| §4.6, §4.7, §4.8 | *(2026-09-29, slice 2c plan)* `isPristine` also counts a date the user picked, a reading set chosen in the switcher (which makes a default date the user's) and a translation override (owner answer Q2), so "New service" asks after them; the roll-forward keeps a picked or chosen date but not for a translation alone, which "New service" keeps (review answer A). Date & readings counts as done only with no field showing an error (review answer E). The lectionary fills only in the tab on screen, and a tab shown again first re-reads the stored draft and adopts it when newer. Date & readings ships (`SHIPPED_STEPS` holds "readings"). `ErrorState` takes a screen's own `message`, `retryLabel` and `retryDisabled`, and `ConfirmDialog` a `cancelLabel`, for the slice spec's "Try again" and "Keep mine". | 2c |
| §4.6, §4.8 | *(2026-09-29, slice 2c build)* "New service" leaves the translation override out of its question, since the fresh draft keeps it; `isPristine` still counts it. The lectionary's automatic fill is stamped 1 ms after the draft it changes (`DraftStore.autoUpdate`), not now, and a flush that finds a strictly newer stored draft adopts it instead of writing over it, so an automatic change never outranks another tab's edit. A lookup rate limited by a 429 is not asked again on focus, reconnect or mount before its `Retry-After`. `ConfirmDialog` also takes `onCancel` (called by its cancel button only) and `finalFocus`. | 2c |
| §1.3 | *(2026-09-29, slice 3a plan)* `HymnalCode` is not used on `GET /hymns?hymnal=` after all: slice 3's read filters (`GET /hymns`, `ScriptureMatchIn.hymnal`, `HymnSuggestionIn.hymnal`) take any stored code up to 20 characters, as the slice 3 spec says, so a CLI-imported code such as `PH 1990` can still be listed. `HymnalCode` stays for 6a's new or admin-managed codes. | 3a |
| §2.8 | *(2026-09-29, slice 3a plan)* The `OPENAI_*` settings are read in `integrations/openai_client.py` (`ai_settings()`), not `api/settings.py`, so the integration imports nothing from the API layer; a bad number falls back to its default with a WARNING. Each attempt's timeout is passed to `create(timeout=openai.Timeout(t, connect=min(5, t)))`. The client's own messages are generic; a caller that wants its own `ai_not_configured` wording (hymn suggestions: "AI suggestions aren't set up on this app yet.") catches `NotConfigured` and raises its own. A model OpenAI does not offer (`NotFoundError`, or `code == "model_not_found"`) maps to `ai_not_configured` with an ERROR line naming `OPENAI_MODEL`, and is not retried (owner answer A). An optional `OPENAI_REASONING_EFFORT` is sent as `reasoning_effort` only when set, for a reasoning model; the pin is `openai>=1.58.0,<4`. | 3a |
| §4.4 | *(2026-09-29, owner answer Q2, slice 3a plan)* Recent use is matched on the normalized hymn title alone (`hymn_search.usage_key`), across numbers and hymnals. 5a keeps writing `hymn_usage` rows with number and title; the reader ignores the number. | 3a |

---
````

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
  ```

  - **No pattern on `HymnRef.hymnal`.** The value echoes `hymns.hymnal` from the database, and CLI-imported codes were never pattern-checked. A pattern would make a pick from such a hymnal fail with 422 on `/liturgy/generate`, `/services`, `/documents` and `/bulletin-emails`. Slice 3's `HymnalCode` type (`^[A-Za-z0-9_-]{2,20}$`) is used only on the query and path parameters that need it (for example `GET /hymns?hymnal=`), never inside `HymnRef`.
  - **`title` ≤300** everywhere, on the server and in every client-side cut. A 200-character limit anywhere would reject titles that another slice's client allows.
  - `hymn_id: null` is accepted only to carry an archived snapshot that no longer matches the hymnal. The UI can never create one (owner decision 9).
````

**with:**

````markdown
  ```

  - **No pattern on `HymnRef.hymnal`.** The value echoes `hymns.hymnal` from the database, and CLI-imported codes were never pattern-checked. A pattern would make a pick from such a hymnal fail with 422 on `/liturgy/generate`, `/services`, `/documents` and `/bulletin-emails`. Slice 3's `HymnalCode` type (`^[A-Za-z0-9_-]{2,20}$`) is used only on the path and body parameters that name a new or admin-managed code (6a), never inside `HymnRef` and never on slice 3's read filters such as `GET /hymns?hymnal=` (amended 2026-09-29, slice 3a plan).
  - **`title` ≤300** everywhere, on the server and in every client-side cut. A 200-character limit anywhere would reject titles that another slice's client allows.
  - `hymn_id: null` is accepted only to carry an archived snapshot that no longer matches the hymnal. The UI can never create one (owner decision 9).
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
- Owner decisions 3 and 9.
- **Amendment 2026-09-26: the service rubric (PR #4).** `docs/superpowers/specs/2026-09-25-service-rubric-design.md`, merged to `main` on 2026-09-26, changed `worship_service.suggest_hymns_for_service`, which this slice replaces. Its behavior is now current behavior (inv §1 D10, D8 amendment) and is **carried over, not dropped**: rubric-aware ranking, the rubric's slot checklists and the year/familiarity facts in the prompt, and year and familiarity on every hymn DTO. PR #4 left one screen change to this slice: the "newer hymn" year label. The additions are marked "Amendment 2026-09-26" below; the main ones are §Backend 3.8, §User experience "Newer-hymn year label", the `HymnOut` fields in §API Models, and the Testing and Acceptance additions.

---
````

**with:**

````markdown
- Owner decisions 3 and 9.
- **Amendment 2026-09-26: the service rubric (PR #4).** `docs/superpowers/specs/2026-09-25-service-rubric-design.md`, merged to `main` on 2026-09-26, changed `worship_service.suggest_hymns_for_service`, which this slice replaces. Its behavior is now current behavior (inv §1 D10, D8 amendment) and is **carried over, not dropped**: rubric-aware ranking, the rubric's slot checklists and the year/familiarity facts in the prompt, and year and familiarity on every hymn DTO. PR #4 left one screen change to this slice: the "newer hymn" year label. The additions are marked "Amendment 2026-09-26" below; the main ones are §Backend 3.8, §User experience "Newer-hymn year label", the `HymnOut` fields in §API Models, and the Testing and Acceptance additions.
- **Notes from planning 3a** (`docs/superpowers/plans/2026-09-29-slice-3a-hymns-backend.md`, 2026-09-29) are marked "(3a plan)" where they are made. The owner answered open questions 1 and 2 on 2026-09-29 (answers Q1 and Q2 below).

---
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
|---|---|---|
| Hymn usage recording ("replace that date's usage on Save") | 5a | The exclusion reads `hymn_usage` with the `(number, normalized title)` key in §Backend 3.4, and 5a writes rows with the same key. |
| `services.hymns` slot storage, the `services.hymnal` column, the docx "First/Second/Third Hymn" labels, `#None` | 5a | `draft.hymns.slots` and `draft.hymns.hymnal` (F §4.6). The payload hymnal rule is in "Interfaces with other slices", row 5a. |
````

**with:**

````markdown
|---|---|---|
| Hymn usage recording ("replace that date's usage on Save") | 5a | The exclusion reads `hymn_usage` by the normalized title alone (§Backend 3.4; owner answer Q2, 3a plan), and 5a keeps writing rows with number and title. |
| `services.hymns` slot storage, the `services.hymnal` column, the docx "First/Second/Third Hymn" labels, `#None` | 5a | `draft.hymns.slots` and `draft.hymns.hymnal` (F §4.6). The payload hymnal rule is in "Interfaces with other slices", row 5a. |
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
  Nothing in this path raises on bad stored data, so a stray row can never turn `GET /hymns?recent_for_date=` or a suggestion call into a 500.
- **Key:** `usage_key(number, title) = (number, normalize_title(title))`. `normalize_title` collapses whitespace, strips and casefolds. The key is the same as `is_hymn_recently_used` today (hymn_usage.py:45-47), just more tolerant of whitespace.
- **Value:** the usage date nearest D; ties go to the earlier date. The UI labels a date before D "Used on …" and a date after D "Also planned for …".
````

**with:**

````markdown
  Nothing in this path raises on bad stored data, so a stray row can never turn `GET /hymns?recent_for_date=` or a suggestion call into a 500.
- **Key:** `usage_key(title) = normalize_title(title)`, the title alone (owner answer Q2, 2026-09-29; 3a plan). `normalize_title` applies NFKC, collapses whitespace, strips and casefolds. So a hymn sung from GG2013 is flagged when the same title is picked from PH1990 under another number; two different hymns with the same title are also flagged, which the owner accepted. `usage_near` returns `dict[str, date]`.
- **Value:** the usage date nearest D; ties go to the earlier date. The UI labels a date before D "Used on …" and a date after D "Also planned for …".
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
The total is about 76 s, which matches F §1.8's "~75 s" and leaves about 14 s under the 90 000 ms client timeout. The concurrency slot is held only for the attempts and the backoff, all inside the deadline.
````

**with:**

````markdown
The total is about 76 s, which matches F §1.8's "~75 s" and leaves about 14 s under the 90 000 ms client timeout. The concurrency slot is held only for the attempts and the backoff, all inside the deadline. (3a plan: httpx applies an attempt's timeout per phase, to the connect, each read, the write and the pool wait, not to the attempt as a whole, so a response that arrives slowly in pieces can run a few seconds past the 75 s deadline; the gap under the 90 s client timeout covers that.)
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
  - Usage rows written by Streamlit's Prepare (ISO `date_iso` from `record_usage`) are read correctly.
  - Streamlit ignores `default_hymnal`, and its settings merge preserves unknown keys (F §6.2).
- **Production data assumption to verify before building the parser.** Nobody has checked the actual `scripture_refs` formats in production. Before implementing §2, the owner runs a read-only query against production and commits the output as `backend/tests/fixtures/hymns/scripture_refs_sample.txt`:

  ```sql
````

**with:**

````markdown
  - Usage rows written by Streamlit's Prepare (ISO `date_iso` from `record_usage`) are read correctly.
  - Streamlit ignores `default_hymnal`, and its settings merge preserves unknown keys (F §6.2).
- **Production data assumption to verify before building the parser.** Nobody has checked the actual `scripture_refs` formats in production. Before implementing §2, the owner runs a read-only query against production and commits the output as `backend/tests/fixtures/hymns/scripture_refs_sample.txt` (3a plan: `backend/tests/hymn_fixtures/scripture_refs_sample.csv`, columns `hymnal,number,title,scripture_refs`, because every file under `backend/tests/fixtures/*/` needs a recorder sidecar; the plan's Task 4 gives the owner's query, and a synthetic stand-in keeps the build moving until the export arrives):

  ```sql
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
- the slot captions;
- free-text hymns stay removed (owner decision 9);
- the usage key stays `(number, title)`, with no hymnal dimension (see Risks).

---
````

**with:**

````markdown
- the slot captions;
- free-text hymns stay removed (owner decision 9);
- the usage key has no hymnal dimension. (3a plan: it is now the title alone, owner answer Q2; see Open question 1.)

---
````

**In `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, replace:**

````markdown
**Open questions:**
1. **Recent use across hymnals.** Usage is matched on `(number, normalized title)`, as today, so a hymn sung from GG2013 is not flagged when the same text is picked from PH1990 under a different number. Should the match use the normalized title alone, with more matches but occasional false positives for different hymns with the same title? This spec keeps the current key until the owner decides. It is a one-line change in `usage_key`.
2. **"Fill each slot" versus "fill each empty slot" (decision 3).** Decision 3 says "fill each slot with the top pick". This spec reads that as "fill each *empty* slot": a hymn the user already chose is never overwritten, and a filled slot gains 3–4 chips instead, so the AI's top pick is one tap away. This is an interpretation, not a confirmed decision.
   - **When it is decided:** the question is put to the owner **before 3b starts** (together with slice 4's question on Generate for custom elements, which must be answered before 4b). The answer is recorded in F's decisions table, and this spec follows that entry.
````

**with:**

````markdown
**Open questions:**
1. **Recent use across hymnals.** *Answered 2026-09-29 (owner answer Q2): match on the normalized title alone; `usage_key` changed in 3a.* Follow-up (owner): Glory to God often titles hymns by their first line, so a first-line match would catch more; no first-line data is stored today. Research later whether Hymnary.org can supply first lines (its scripture API, which `hymnary_facts.py` already calls, keys results by first line; unverified for hymns without scripture references). The original question: Usage is matched on `(number, normalized title)`, as today, so a hymn sung from GG2013 is not flagged when the same text is picked from PH1990 under a different number. Should the match use the normalized title alone, with more matches but occasional false positives for different hymns with the same title? This spec keeps the current key until the owner decides. It is a one-line change in `usage_key`.
2. **"Fill each slot" versus "fill each empty slot" (decision 3).** *Answered 2026-09-29 (owner answer Q1): only empty slots; recorded in F's decisions table as D16.* Decision 3 says "fill each slot with the top pick". This spec reads that as "fill each *empty* slot": a hymn the user already chose is never overwritten, and a filled slot gains 3–4 chips instead, so the AI's top pick is one tap away. This is an interpretation, not a confirmed decision.
   - **When it is decided:** the question is put to the owner **before 3b starts** (together with slice 4's question on Generate for custom elements, which must be answered before 4b). The answer is recorded in F's decisions table, and this spec follows that entry.
````

- [ ] **Step 3 (agent): Check the docs tests, the owner markers and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
git diff --stat
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `89 passed in <t>s`; `4`; three files, 18 insertions and 9 deletions; `1103 passed, 11 skipped in <t>s`.

- [ ] **Step 4 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-migration-foundations-design.md \
        docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md docs/ops-runbook.md
git commit -m "Docs: D16 (Suggest fills only empty slots), the title-only usage key, 3a plan notes and the OpenAI variables (F Decisions, Amendments; S; owner answers Q1-Q3)" -m "F's decisions table records owner answer Q1 as D16, as the slice 3 spec
asked; three amendment rows record the HymnalCode scope, the OpenAI
client's settings and messages, and the title-only usage key (owner answer
Q2), and §1.3's sentence stops naming GET /hymns as a HymnalCode user. The
slice 3 spec marks both open questions answered, corrects the usage key,
the 5a row and the sample path, records the first-lines follow-up, and
notes in §3.7 that httpx timeouts are per phase (the 15 s gap covers a small
overrun). The runbook lists OPENAI_API_KEY (with the $15 cap), OPENAI_MODEL
(with the retired-model symptom) and the optional settings, including
OPENAI_REASONING_EFFORT.

Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git log --oneline -1
```

- [ ] **Step 5 (controller): Review checkpoint and backup push**

Read the three diffs: no em dash in new prose outside quoted spec copy, D16's wording matches owner answer Q1, and the follow-up says the first-lines source is unverified. Push the backup.

Counts after Task 15: backend **1103 passed, 11 skipped**; frontend **356 in 55 files**.

### Task 16: Whole-branch verification and the slice 3a pull request (owner's yes before the PR is opened and before it is marked ready) (S Testing, AC1-AC9, AC16, AC18-AC20; F §2.2, §2.5, §5.4; owner decisions 2, 4; owner answers Q3-Q5, D)

The whole branch is checked in one place: both suites, the Postgres marker count, the threaded tests three times, types, lint, the frontend build, the generated API files, the layering, log and AC9 gates, the exact changed paths and the exact commits. The branch is already on `origin` (the backup pushes), so on the owner's first yes the agent opens the PR as a draft, waits for CI and reports. **The PR is not marked ready until the owner's real scripture export has replaced the synthetic sample and passes the 98 % check** (owner answer D; Step 11); then, on the second yes, the agent marks it ready. Merging is Task 17.

Below, `<scratch>` is the session's scratchpad directory and `<N>` the PR number Step 9 prints; write both out literally. Every `gh` command uses `-R bbrown62450/church`.

**Files:** none changed. A local or CI failure is fixed in the owning task's files (a new commit in that task's area), never here.

- [ ] **Step 1 (agent): Bring the branch up to date**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline origin/main..HEAD | tail -1
```

**Expected:** only `?? .claude/`; `0`; the branch's oldest commit, `<sha> Plan: slice 3a hymns backend (S slice 3; owner answers 2026-09-29)`. If the count is not `0`, `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 16)"` with the two trailer lines as a second `-m`; on a conflict `git merge --abort` and stop. New tests from `main` change the Step 2 totals by exactly their number; name them in Step 8's message.

- [ ] **Step 2 (agent): Backend suite, Postgres marker count, threaded tests three times**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_api_hymn_suggestions.py backend/tests/test_openai_client.py backend/tests/test_usecase_passages.py 2>&1 | tail -1; done
```

**Expected:** `1103 passed, 11 skipped in <t>s`; `11 skipped, 1103 deselected in <t>s` (no `TEST_DATABASE_URL` here; nine earlier Postgres tests plus Task 7's and Task 9's); `<n> passed in <t>s` three times with no failure. If a local throwaway Postgres is available, `TEST_DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres .venv/bin/python -m pytest -q -m postgres` gives `11 passed, 1103 deselected, 1 warning`.

- [ ] **Step 3 (agent): Frontend tests, types, lint and build**

```bash
(cd frontend && npm test && npm run typecheck && npm run lint)
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build)
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

**Expected:** ` Test Files  55 passed (55)`, `      Tests  356 passed (356)`; `tsc` and `eslint` print nothing; the build ends with its route table and no `Error:`; then exactly:

```
/ /_global-error /_not-found /auth/callback /builder /builder/hymns /builder/liturgy /builder/readings /builder/review /favicon.ico /join /login /welcome
```

(the same routes as after 2c: 3a adds no page). A font `Failed to fetch` only: say so and rely on CI's build.

- [ ] **Step 4 (agent): The generated files are current and hold what 3b needs**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)
git status --short -- frontend
.venv/bin/python -c "import json; p = json.load(open('frontend/src/lib/api/openapi.json')); print(sorted(k for k in p['paths'] if 'hymn' in k)); print(sorted(k for k in p['components']['schemas'] if 'Hymn' in k or 'Page' in k or k in ('SlotPicks', 'SuggestedSlots', 'ScriptureMatchIn', 'ScriptureMatchesOut')))"
```

**Expected:** nothing from `git status` (regenerating changes nothing); `['/hymnals', '/hymns', '/hymns/scripture-matches', '/hymns/suggestions']`; `['HymnMatchOut', 'HymnOut', 'HymnSuggestionIn', 'HymnSuggestionsOut', 'HymnalListOut', 'HymnalOut', 'Page_HymnOut_', 'ScriptureMatchIn', 'ScriptureMatchesOut', 'SlotPicks', 'SuggestedHymnOut', 'SuggestedSlots']` (`Page_HymnOut_` is Pydantic's name for `Page[HymnOut]`, which 3b's `schema.d.ts` types use).

- [ ] **Step 5 (agent): Gates (judged, not obeyed blindly; tests excluded)**

```bash
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/integrations/openai_client.py backend/hymn_search.py backend/hymn_suggest.py backend/hymn_ranking.py backend/hymn_usage.py backend/scripture_refs.py backend/usecases/hymns.py backend/repos/hymns.py
grep -nE "logger\.(info|warning|error|debug)" backend/usecases/hymns.py backend/integrations/openai_client.py backend/hymn_usage.py
grep -rnE "hymns_by_scripture|suggest_hymns_for_service|hymn_display_info|_hymnary_audio|resolve_hymnary_audio_url" --include=*.py backend | grep -v "^backend/tests/"
grep -rn "api_key" backend/integrations/openai_client.py
```

**Expected:** the first grep prints nothing. The second lists every log call: in `usecases/hymns.py` the DEBUG `hymn_matches` counts line, the NT-fetch failure warning (class name only), the DEBUG prompt line and the one `hymn_suggestions` INFO line; in `openai_client.py` the two settings warnings (numbers, reasoning effort), the four startup lines, the quota, model-not-available (it names `OPENAI_MODEL`, which is configuration, not a secret) and key-refused ERROR lines, and the `ai_call` lines (model, counts, class names); in `hymn_usage.py` the DEBUG skipped count. Read each: none formats a title, `nt_text`, a key, a prompt at INFO or an SDK message. The third prints nothing. The fourth shows only the settings field, `problem`, `load_settings` and the SDK constructor.

- [ ] **Step 6 (agent): The exact changed paths**

```bash
git diff --stat origin/main -- . ':!docs/superpowers/plans' | tail -1
git diff --name-status origin/main | sort -k2
```

**Expected:** the File Structure's Created, Modified and Deleted lists and nothing else (plus this plan): `A` for the 5 new backend modules and routes, the 11 new test files and the 2 `hymn_fixtures` files; `D` for `backend/tests/test_suggest_hymns.py`; `M` for the rest. Anything else: find its task or stop.

- [ ] **Step 7 (agent): The exact commits**

```bash
git log --reverse --format=%s origin/main..HEAD
```

**Expected:** the plan's two commits (`Plan: slice 3a hymns backend ...`, `Plan: slice 3a review fixes`), then the fifteen subjects of Tasks 1-15 in order (plus Task 4 Step 10's, if the export arrived, and any fix commits the reviews made, each named in Step 8's message).

- [ ] **Step 8 (agent): Ask the owner to open the pull request**

Tell the owner, in one message: "Slice 3a (the hymns backend) is ready for a pull request: four new church-scoped routes (hymnals, hymns, scripture matches, AI suggestions), two new fields on the church profile, the OpenAI client, and the old Streamlit-era hymn code removed. Nothing changes on screen, there is no database change, and liturgy-frozen is not affected. Tests: backend 971 → 1103 passed, 9 → 11 skipped; frontend 356 → 356. The scripture sample is <still the made-up (synthetic) one, so before I ask to mark the PR ready I will walk you through exporting your real one / your export of <date>, <rate> parsed>. May I open the pull request as a draft so CI runs?"

- [ ] **Step 9 (agent, on the owner's yes): Open the draft PR**

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 3a hymns backend: hymnals, hymns, scripture matches, AI suggestions" \
  --body-file <scratch>/slice3a-pr-body.md
```

Write `<scratch>/slice3a-pr-body.md` first. While the sample is synthetic, its first lines, above the summary, are exactly:

```
> **Scripture sample: SYNTHETIC.** The 98 % parse test (AC3) currently runs on 100 hand-written rows in Hymnary.org's shape, not on production data. This PR stays a draft until the owner's read-only export of `hymn_catalog` replaces `backend/tests/hymn_fixtures/scripture_refs_sample.csv` and passes the 98 % check (owner answer D; plan Task 16 Step 11).
```

(When the export has already been swapped in, the first line instead reads `> **Scripture sample: EXPORTED on <date>**, <rows> rows, <rate> of segments parsed.`) Then: a summary (the Goal paragraph in plain words); the four routes and the two `/church` fields; the owner answers Q1-Q4 and A-D and where each landed; the owner-visible clarifications (1, 2, 9, 26) and the model recommendation with its fallbacks (UNVERIFIED, confirmed in Task 17); the scripture sample line (synthetic, or the export's date, row count and parse rate); the owner's `hymn_usage.date_iso` length counts from Task 4 Step 1 (or "not run"); the line `Tests: backend 971 → 1103 passed, 9 → 11 skipped; frontend 356 → 356 in 55 files`; "No migration; production stays at 0004_invites_reusable. After the merge the owner sets OPENAI_API_KEY and OPENAI_MODEL on Railway (Task 17)."; then `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS` on the last lines.

**Expected:** the push prints `Everything up-to-date` or the new commits; `gh` prints the PR URL. Record `<N>`.

- [ ] **Step 10 (agent): Wait for CI**

```bash
gh pr checks <N> -R bbrown62450/church --watch
gh run view $(gh run list --branch claude/slice-2-plan-4q33le --workflow ci --limit 1 -R bbrown62450/church --json databaseId --jq '.[0].databaseId') -R bbrown62450/church --log | grep -E '[0-9]+ passed' | sed -E 's/^.*Z //'
```

**Expected:** `backend`, `backend-postgres`, `frontend` and the Vercel preview pass; the log lines include `1103 passed, 11 skipped` (`backend`), `11 passed, 1103 deselected, 1 warning` (`backend-postgres`) and `Tests  356 passed (356)` (`frontend`). A CI-only failure is fixed in the owning task's files, pushed on the standing backup permission, and this step reruns.

- [ ] **Step 11 (agent + OWNER): The owner's scripture export gates "ready" (owner answer D)**

Skip this step only if Task 4 Step 10 has already swapped in the owner's export and it passed. Otherwise walk the owner through Task 4 Step 1's two read-only queries **one step at a time**, waiting for each reply before sending the next:
1. "Before I ask to mark the pull request ready, I need a sample of your real hymn scripture references (public hymn information only: hymnal, number, title and references; no names or emails). Please open https://supabase.com/dashboard and choose the project `worship-staging`. Tell me when you see it."
2. "Click SQL Editor on the left, then New query. Tell me when you have an empty query box."
3. "Paste this and click Run. It only reads; nothing is changed:" followed by Task 4 Step 1's first query, then "Tell me how many rows it shows."
4. "Under the results, choose Export, then Download CSV, and attach the file here (or paste its contents)."
5. "One more read-only query, for the pull request: click New query, paste this and click Run, then tell me the rows it shows:" followed by Task 4 Step 1's second query.

Then run Task 4 Step 10. If the rate is at least 0.98 and `test_scripture_refs_parse.py` passes, push the commit (standing backup permission), wait for CI as in Step 10, and edit the PR body's first line to the EXPORTED form (`gh pr edit <N> -R bbrown62450/church --body-file <scratch>/slice3a-pr-body.md`). If the rate is below 0.98, stop: Task 4 Step 10 says what to report, and the PR stays a draft until the controller and the owner decide. The PR is marked ready on the synthetic sample only if the owner explicitly says so in reply to a question that names the risk ("the parser has only been tested on made-up references"); record that answer in the PR body.

- [ ] **Step 12 (agent): Ask, then mark ready**

Tell the owner: "PR #<N> is green on CI (backend 1103 passed, 11 skipped; Postgres 11 passed; frontend 356), and the scripture test passes on your real export (<rate> of <segments> references read). May I mark it ready for review?" On the yes:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft --jq .isDraft
```

**Expected:** `false`.

### Task 17: Merge and after (OWNER + agent): the merge, the deploy, the OpenAI key and model, live checks, the slice 3a record (S AC1, AC2, AC15, AC16; owner decisions 2-4; owner answers Q3, Q5)

3a changes no schema, so the merge deploy's pre-deploy `alembic upgrade head` runs nothing. `requirements.txt` changes (the `openai` floor rises, `lxml` leaves), so Railway builds new dependencies; the startup log gains one `AI: ...` line. No page calls the new routes until 3b, so the live checks are the owner's: a Console snippet on the production site that reads the owner's own sign-in from the site's cookies, sends it only to the app's API, and never prints it. The build container cannot reach Railway or OpenAI, so every live look is the owner's. The owner prefers small steps: give one OWNER step, wait for the report, then the next. The agent writes each result with its date into `<scratch>/slice3a-t17-results.md` (not committed). The key is never pasted into chat, and nothing is recorded with an email address, a church id, a token or a key.

- [ ] **Step 1 (agent): Pre-merge gate**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,headRefOid --jq '[.state, .isDraft, .mergeable, .mergeStateStatus, .headRefOid] | @tsv'
git log --oneline origin/claude/slice-2-plan-4q33le..origin/main | wc -l
gh pr checks <N> -R bbrown62450/church
git diff --quiet origin/main origin/claude/slice-2-plan-4q33le -- backend/migrations backend/db/models.py backend/Procfile backend/railway.toml; echo "exit $?"
```

**Expected:** `OPEN	false	MERGEABLE	CLEAN	<sha>`; `0`; every check `pass`; `exit 0` (no migration or model change). If `main` moved, merge it, rerun both suites, push on the owner's yes and wait for green. Then ask: "PR #<N> (slice 3a, the hymns backend) is green and includes `main`. It adds no database change and changes nothing on screen; liturgy-frozen is not affected. After the merge I will guide you through adding the new OpenAI key and model on Railway. May I merge it now with a merge commit?"

- [ ] **Step 2 (agent, on the owner's yes): Merge**

```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergedAt,mergeCommit --jq '[.state, .mergedAt, .mergeCommit.oid] | @tsv'
```

**Expected:** `MERGED	<UTC time>	<merge sha>`. Tell the owner the time and that Railway and Vercel are deploying.

- [ ] **Step 3 (OWNER): Watch the deploy**

"Please open Railway → the API service (`church`) → Deployments → the one whose message starts `Merge pull request #<N>` → Deploy Logs. Check: no line containing `Running upgrade`; the health check passed and the deployment is Active; one line starting `AI:`. Tell me what the `AI:` line says (it should be `AI: not configured (OPENAI_API_KEY missing)` or `AI: not configured (OPENAI_MODEL missing)`, since the new key and model come next), and whether you see `Traceback` or `ERROR` anywhere. Also open https://church-production-74ca.up.railway.app/health/ready in a browser tab and tell me what it shows (it should be `{"ok":true,"db":"ok"}`)."

- [ ] **Step 4 (agent): CI on `main` and the deployment statuses**

```bash
gh run list --workflow ci --branch main --limit 3 -R bbrown62450/church --json databaseId,headSha,conclusion --jq '.[] | select(.headSha == "<merge sha>") | [.databaseId, .conclusion] | @tsv'
gh api "repos/bbrown62450/church/deployments?sha=<merge sha>" --jq '.[] | [.id, .environment] | @tsv'
```

**Expected:** the run's conclusion `success` (rerun the line if it has not appeared yet; no `sleep`); a Railway and a Vercel `Production` deployment, whose latest statuses (`gh api repos/bbrown62450/church/deployments/<id>/statuses --jq '.[0].state'`) are `success`.

- [ ] **Step 5 (OWNER): The OpenAI key, the budget cap and the model**

"In OpenAI, for this app:
1. Go to https://platform.openai.com and choose the project you use for this app (top left).
2. Settings → Limits (or Billing → Limits): set the monthly budget to $15, as you chose. When it is reached, suggestions will say 'not set up' until the next month; the app does not keep retrying.
3. On the same Limits page, find the list of models this project may use, and tell me whether `gpt-4.1-mini` is listed. If it is not, tell me whether `gpt-4o-mini` is, and if neither is, whether `gpt-5-mini` is.
4. API keys: create a new secret key for this app (or use the separate one you already made). Copy it somewhere safe for the next step. Please do not paste it here."

Record which model is available, in the plan's order: `gpt-4.1-mini`, then `gpt-4o-mini`, then **`gpt-5-mini` with `OPENAI_REASONING_EFFORT=minimal`** (a reasoning model: without the low effort it can spend its whole answer budget thinking and answer "had a problem"; UNVERIFIED, from third-party docs of 2026-09-29, so the first live suggestion in Step 7 is the check, and `low` is the value to try if `minimal` is refused). If none is listed, stop and ask the controller (the plan's "Model" note is UNVERIFIED).

- [ ] **Step 6 (OWNER): Set the two variables on Railway**

"Railway → the API service (`church`) → Variables:
1. If `OPENAI_API_KEY` is already there, open its menu → Edit and paste your new key as the value; otherwise + New Variable, name `OPENAI_API_KEY`, value your new key.
2. + New Variable, name `OPENAI_MODEL`, value `<the model from Step 5>`.
   (Only if the model is `gpt-5-mini`: + New Variable, name `OPENAI_REASONING_EFFORT`, value `minimal`.)
3. Click Deploy (Railway holds variable edits until you deploy) and wait for the new deployment to be Active.
4. In its Deploy Logs, find the `AI:` line. Tell me exactly what it says. It should be `AI: configured (model=<the model>)`, and it must not show any part of the key."

If it says `not configured (OPENAI_API_KEY is not ASCII)`, the key was mangled when pasted: repeat Step 6.1.

- [ ] **Step 7 (OWNER): The four routes, signed in, from the Console (AC1, AC2, AC15, AC16)**

"On https://worship-service-builder.vercel.app, signed in, open DevTools (⌥⌘I) → Console, paste this and press Return (type `allow pasting` first if Chrome asks). It reads your sign-in from this site, calls only the app's API, prints no token and changes nothing. The last call asks the AI once."

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
  let raw = whole ? jar[whole]
    : names.sort((a, b) => Number(a.split(".").pop()) - Number(b.split(".").pop())).map((k) => jar[k]).join("");
  if (!raw) { console.log("No sign-in found. Sign in, reload, then run this again."); return; }
  if (raw.startsWith("base64-")) {
    const bytes = Uint8Array.from(atob(raw.slice(7).replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
    raw = new TextDecoder().decode(bytes);
  }
  const token = JSON.parse(raw).access_token;
  const me = await (await fetch(API + "/me", { headers: { Authorization: "Bearer " + token } })).json();
  const churchId = localStorage.getItem("activeChurchId") || (me.churches[0] || {}).id;
  const call = async (method, path, body) => {
    const headers = { Authorization: "Bearer " + token, "X-Church-Id": churchId };
    if (body) headers["Content-Type"] = "application/json";
    const started = performance.now();
    const r = await fetch(API + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    return [r.status, await r.json(), Math.round(performance.now() - started)];
  };
  const say = (line) => console.log(line);
  let [s, b, ms] = await call("GET", "/church");
  say(`church ${s} default_hymnal=${b.default_hymnal} effective_hymnal=${b.effective_hymnal}`);
  [s, b, ms] = await call("GET", "/hymnals");
  say(`hymnals ${s} ${JSON.stringify(b)}`);
  const hymnal = b.effective_hymnal;
  [s, b, ms] = await call("GET", `/hymns?hymnal=${encodeURIComponent(hymnal)}&limit=2000&recent_for_date=2026-10-04`);
  const recent = (b.items || []).filter((h) => h.recent_use_on).length;
  const newer = (b.items || []).filter((h) => h.newer_than_preferred).length;
  say(`hymns ${s} ${ms}ms total=${b.total} recent=${recent} newer=${newer} first=${JSON.stringify((b.items || [])[0])}`);
  const refs = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];
  [s, b, ms] = await call("POST", "/hymns/scripture-matches", { refs, hymnal, recent_for_date: "2026-10-04" });
  say(`matches ${s} ${ms}ms total=${b.total_matched} unparsed=${JSON.stringify(b.unparsed_refs)} top=${JSON.stringify((b.items || []).slice(0, 5).map((h) => [h.number, h.title, h.strength]))}`);
  [s, b, ms] = await call("POST", "/hymns/suggestions", {
    service_date_iso: "2026-10-04", occasion: "Nineteenth Sunday after Pentecost", scriptures: refs,
    selected_nt_ref: "Matthew 21:33-46", hymnal, exclude_recent: true });
  if (s !== 200) { say(`suggestions ${s} ${ms}ms ${JSON.stringify(b.error)}`); return; }
  for (const slot of ["opening", "response", "closing"]) {
    say(`suggestions ${slot}: ${b.slots[slot].map((h) => `#${h.number} ${h.title} (${h.source})`).join(" | ")}`);
  }
  say(`suggestions ${s} ${ms}ms nt_ref=${b.nt_ref} nt_text_used=${b.nt_text_used} excluded_recent=${b.excluded_recent_count}`);
})();
```

"Then, in the Network tab, click the row whose name starts `hymns?hymnal=` → Headers → Response Headers, and tell me whether `content-encoding: gzip` is there. Please copy all the Console lines to me (they hold hymn titles and counts only)."

The agent checks: `/church`'s two values equal `/hymnals`' (AC2); `/hymns` status 200 with `total` equal to that hymnal's `hymn_count`; `content-encoding: gzip` (AC16); matches 200 with `unparsed=[]`; suggestions 200 with 3-5 hymns per slot, distinct first hymns, and the model's answer used (`source` mostly `ai`). A 502 `ai_upstream_error` means the model answered unusably (a reasoning model without `OPENAI_REASONING_EFFORT`, or bad JSON): ask the controller, and suggest the next model from Step 5 in Step 6. A 503 `ai_not_configured` means the key or model is missing, refused, out of budget or not offered: ask the owner whether Deploy Logs show `AI: model not available (OPENAI_MODEL=...)` (pick the next model from Step 5), `AI: quota exhausted` (the cap) or `AI: the OpenAI key was refused` (repeat Step 6.1), and check the `AI:` startup line. The snippet takes the church the app has selected (`localStorage["activeChurchId"]`, `ACTIVE_CHURCH_KEY` in `frontend/src/lib/storage.ts`), or the first church from `/me` when none is stored.

- [ ] **Step 8 (OWNER, optional): Streamlit smoke on liturgy-frozen**

"If you have a minute: open https://liturgy-frozen.streamlit.app/, sign in, check that your church and hymnal load and that Suggest hymns still works there. Merges never reach it, so this is only a comfort check."

- [ ] **Step 9 (agent): The slice 3a record (records PR, on the owner's yes)**

On a branch `claude/slice-3a-records` from `origin/main`, insert `### Slice 3a record` after `### Slice 2c record`'s table and before `## Backups` in `docs/ops-runbook.md`: a short paragraph (3a merged as PR #<N> with no database change; no page calls the routes until 3b; the checks were the owner's) and a table with dated rows for: Merge and deploy (merge sha, pre-deploy with no upgrade, health check, the first `AI:` line); CI on `main` (the three jobs' counts); OpenAI (a separate project key set on Railway, the $15 monthly cap set, the model chosen, whether it was the plan's recommendation, and `OPENAI_REASONING_EFFORT` if set; never the key); `AI: configured (model=...)`; the Console results (hymnals and counts, `/hymns` total and time, gzip, matches, one suggestion's outcome); the scripture sample (synthetic, or exported on <date> with its parse rate) and the `date_iso` counts; the Streamlit smoke (run or skipped); Follow-ups: first-line matching research on Hymnary.org (owner answer Q2), 3b (the Hymns step UI and the owner's question on whether hymnal changes and alternatives count as unsaved work), and anything the checks found. If the owner chose a model other than `gpt-4.1-mini`, change `backend/.env.example`'s `OPENAI_MODEL=` line in the same PR (and, for `gpt-5-mini`, uncomment `OPENAI_REASONING_EFFORT=minimal`). Check the section has no `<`, no email, token, key or church id (`grep -Eic '@|bearer|eyJ|sk-|[0-9a-f]{8}-[0-9a-f]{4}-'` prints 0), and that `test_docs.py`, `test_slice1_docs.py` and `test_ops_workflows.py` still pass (`89 passed`). Commit with the two trailer lines. Ask the owner before pushing and opening the PR, and again before merging it.

- [ ] **Step R (only if the 3a release must come out): Revert**

Use this only if the release cannot serve or breaks the church pages (for example `GET /church` failing) and a fix would take too long. No database step: 3a adds no revision and writes nothing. On the owner's yes for each outward action: `git switch -c claude/revert-slice-3a origin/main`, `git revert -m 1 <merge sha>` (commit with the two trailer lines), run both suites (expected `971 passed, 9 skipped`, and 356 frontend tests), push, open a PR titled "Revert slice 3a", wait for green, merge on the yes. The OpenAI variables can stay on Railway; the reverted code does not read them. Record the revert in the slice 3a record.

Expected counts after this task: backend `1103 passed, 11 skipped` on `main` (CI `backend-postgres`: `11 passed, 1103 deselected, 1 warning`); frontend `356 passed` in 55 files. The records PR adds no test.

---

## Lessons carried from the slice 2 builds (P2a, P2b, P2c "Build notes")

- **The container restarts.** Commit as soon as a task's checks pass and push the backup after each review (owner answer Q5). If `frontend/node_modules` is gone, `(cd frontend && npm ci)`.
- **The network is filtered.** OpenAI, hymnary.org, the lectionary sites, bible-api.com and Railway are unreachable from the build container, so every test fakes them and every live check is the owner's (Task 17). The npm registry and PyPI are reachable.
- **Don't prove absence by sleeping.** Waits in tests use events or injected clocks (the hung-fetch test releases its `threading.Event` in `finally`; the OpenAI tests use a `FakeClock` and a recording `sleep`), and CI or deployment polling reruns a command instead of sleeping.
- **Grep gates exclude tests** and are read, not obeyed blindly (Task 14 Step 1 lists its expected hits; Task 16 Step 5 names every log call).
- **Counts are exact.** Every task states its cumulative count; a drift means a missing or extra test, found before moving on.
- **Commit trailers.** Every commit ends with the `Claude-Session:` and `Co-Authored-By:` lines (Global Constraints).
- **Owner steps one at a time, in plain words**, and every outward action on its own yes.

## Build notes (3a build)

Filled in while Tasks 1-15 are built: each change from the plan as written, its reason, and whether the owner saw it. Task 15 (or a follow-up docs commit before Task 16) writes those that alter S or F as "(3a build)" notes.

- **Review of T1-T3 (owner decision 1, not owner-visible).** The key is left out of `AISettings`' repr; a `nan` or `inf` numeric `OPENAI_*` setting falls back to its default; a reply with no choices is `ai_upstream_error`; a deadline already passed logs its `ai_call` line. +1 test (T3's row).
- **Review of T4-T9: owner answers of 2026-09-29 (owner-visible).**
  - **A. The recent-use key ignores punctuation.** `hymn_search.usage_key` is now: NFKC; `’` and `‘` as `'`; hyphens and dashes (`- ‐ ‑ – —`) as a space; everything matching `[^\w\s]` removed; whitespace collapsed; casefolded; a leading `oh ` as `o `. Leading articles are kept ("The Church's One Foundation" and "Church's One Foundation" stay two hymns). So "Come, Thou Long-Expected Jesus" / "…Long Expected…", "The Lord's My Shepherd" / "The Lord’s…", "Holy, Holy, Holy! Lord…" / "Holy, Holy, Holy, Lord…", "Amazing Grace" / "Amazing Grace!" and "O God, Our Help…" / "Oh God Our Help…" are one hymn for recent use. `normalize_title` is unchanged, because exact-title resolution of an AI answer uses it. `usage_near`'s keys change accordingly (`"come thou almighty king"`), which S §3.4's "the usage key" covers.
  - **B. A whole-book tag and a chapter-only `ff` tag rank "chapter" at most.** `RefSpan` gains `broad` (default false, left out of equality). It is set on a whole-book span of a book with more than one chapter ("Psalms"; "Jude" alone stays a passage-capable span, since the book is one chapter) and on a chapter-only `ff` ("Psalm 148ff"), which now means that chapter only, `(148, 0)-(148, 999)`, instead of chapter 148 to the end of the book. `match_hymns` never gives a broad hymn span "passage". A verse `ff` ("Luke 4:14ff", "Jude 3ff") is unchanged. S Backend 2 step 5 ("`ff` … to the end of the chapter") already reads this way for verses; T15 adds the chapter-only and whole-book rules to S.
- **Review of T4-T9: invisible fixes (owner decision 1, not owner-visible).**
  - The text fallback reads a dotted verse ("John 3.16") as `3:16` before normalizing, so it still names chapter 3; it tries each of the query's chapters from the first up to ten more (a range's middle chapters now match); an ordinal inside the text (`i ii iii first second third 1st 2nd 3rd` before a letter) becomes its digit, so "see I John 3" is 1 John and never John 3; and book keys of 2 characters or fewer ("is", "jn", "ps", …) are not tried, so "this is 9" is not Isaiah 9.
  - Psalm 151 joins `SINGLE_CHAPTER_BOOKS`, and a book key may be followed by `:` (dropped), so "Psalm 151:1" is Psalm 151 verse 1 instead of an unparsed Psalm chapter 151.
  - `query_hymns` matches `number` only for ASCII digits: `q=²` was a 500 (`int("²")`), and Arabic-Indic digits matched numbers.
  - `usage_near` clamps its ±84-day window at `date.min` and `date.max`, and at `date.max` drops the SQL upper bound, so `recent_for_date=9999-12-31` or `0001-01-01` is a 200, not a 500.
  - `GET /hymns` caps `offset` at 1 000 000 (clarification 31).
  - `hymnal_summaries` sorts codes in Python (codepoint order, as Streamlit's `sorted()`), so the effective-hymnal fallback no longer depends on the Postgres collation (an `en` collation put "ab" before "Zz"). SQLite has no "C" collation, so `.collate("C")` was not used. The Postgres test was seen failing on an ICU `en` database before the fix. `GET /hymns`' own `ORDER BY hymnal` still uses the database collation (unchanged).
  - `test_isolation_and_every_role` pins that church A asking for church B's hymnal code gets exactly the response for a code that does not exist.
- **Not fixed here: NUL characters.** A `\x00` in a query value or body is an app-wide concern (Postgres rejects it in text), left to a separate follow-up across all routes.
- **Review of T4-T9: left for the owner's export.** Shapes the synthetic sample cannot show and the parser does not read yet: "vv.", "(paraphrase)", "and" or "&" between references, and a book carried across " or ". They are judged against the real export (T4 Step 10, T16 Step 11), whose Task 4 Step 1 also has the second read-only query (the `hymn_usage.date_iso` shapes). A parity test over a real corpus is a minor follow-up for the same point.
- **Review of T10-T12 (owner decision 1, not owner-visible).** The prompt's NEW TESTAMENT READING line is put on one line and clipped to 200 characters (`_clip`), so `selected_nt_ref` cannot add lines to the prompt; a `|` in a catalogue line's title, themes or scripture field becomes `/` (`_field`), so a hymn field cannot fake the number or facts field; `parse_suggestion_json` also catches `RecursionError`, so a deeply nested answer is 502 `ai_upstream_error`, not a 500. No test count change (assertions added to existing tests).
- **Review of T10-T12: owner answer of 2026-09-29 (owner-visible in which hymns are offered).** Ranking the whole response list by era and familiarity before the 50-hymn cut could drop every hymn matching the NT reading. The owner chose: in a ranked response list, hymns matching the NT reading come first, ranked among themselves (at most 50), and the rest are ranked and cut with `shortlist` into the remaining places, with a reserve of `min(NEWER_RESERVE, remaining places)`. Opening, closing and a sampled (no-signal) response list are unchanged. Commit `5eb0f43`, with assertions added to an existing `test_hymn_suggest.py` test (no count change). S §3.8 item 1 carries it as a "(3a build)" note.
- **Counts in the task prose.** The count table was updated with the two review rows; the prose of Tasks 12-17 (the PR body and the owner message included) and the PR-body line in Global Constraints kept the plan's first numbers (1095, 1113, 1101, and 41 for the threaded pair in T13 Step 6). Task 15 corrected them to the table's 1097, 1115, 1103 and 42.
- **Written to S and F by Task 15.** S carries "(3a build)" notes for answers A and B (§3.4 key; §2 step 5 and "Matching"), the text-fallback fixes and Psalm 151 (§2), the codepoint hymnal order (§3.1), `q`'s ASCII digits and the `offset` cap (API notes), the date clamp (§3.4), the prompt hardening (§3.6 steps 7 and 9), the client hardening (§3.7, with owner answer A's retired-model row as a "(3a plan)" note), the NT-first response candidates (§3.8 item 1), the export gate and the deferred shapes (Risks), and the NUL follow-up (Risks). F's amendments gain a §2.8 row (client hardening) and a §4.4 row (answer A's key). So Task 15's commit is larger than Step 3's "three files, 18 insertions and 9 deletions", which counts the plan's own edits only, and it also changes this plan.

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`; F = foundations. Items owned by 3b or later slices are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1 | The four routes exist, depend on `require_church`, match S's models, are in the OpenAPI snapshot and `schema.d.ts`; no allowlist change | T8, T9, T10, T13 (routes, regenerated files, `test_route_guards.py` unchanged), T16 Step 4 |
| 2 | `GET /church`'s two fields equal `GET /hymnals`' | T8 (`test_get_church_returns_the_same_two_values`), T17 Step 7 |
| 3 | The required-results table; ≥ 98 % of the production sample parses | T4 (parser, sample), T5 (`test_required_results_table`); the real export at T4 Step 10 (owner answer Q4), required before the PR is marked ready (owner answer D; T16 Step 11) |
| 4 | With exclusion on, nothing in [D − 84, D + 84] minus {D} reaches the prompt or response; D excludes nothing | T7 (window), T13 (`test_exclude_recent_leaves_recent_hymns_out_of_prompt_and_answer`) |
| 5 | Every OpenAI call through `complete`, with `max_completion_tokens` and `json_mode`; `FakeAI` tests; the seven SDK classes and `insufficient_quota` mapped in order; `openai>=1.58.0,<4`; no socket | T2, T3, T13 (`FakeAI`), the no-network guard |
| 6 | Exact codes and messages; no upstream text or configuration detail | T3 (`test_every_sdk_error_class_maps_to_its_code`), T10, T13 (`test_ai_errors_return_their_code_and_exact_message`, 422 tests) |
| 7 | The 41st suggestion by a user in 10 minutes is 429 with `Retry-After` | T13 (`test_the_41st_call_by_a_user_in_ten_minutes_is_429`, and the church's 401st) |
| 8 | Church isolation on all four routes | T8, T9, T10, T13 (isolation tests; `current_picks` from B ignored and never echoed) |
| 9 | The old names are gone from `backend/`, no `load_dotenv` in `worship_service.py`, no `lxml` | T14 (`test_the_old_hymn_code_is_gone`, Step 5 gates; clarification 14) |
| 10-14 | The Hymns step on screen: shipped step, progress, summary, slots, chips, notices, error and empty states | 3b |
| 11 (server half) | Distinct top picks for empty slots only; at least 3 hymns per slot when the candidates allow | T12 (`finalize_slots` tests), T13 (`test_one_token_per_slot_is_topped_up_to_three`); owner answer Q1 |
| 15 | Railway has the separate key and the model; the startup log shows `AI: configured (model=...)` with no key | T2 (the line), T17 Steps 5-6 (owner) |
| 16 | `GET /hymns?limit=2000` gzipped with CORS and request id | T9 (`test_a_whole_hymnal_is_gzipped_with_cors_and_request_id`), T17 Step 7 |
| 17 | The manual checklist on production | 3b (the Hymns step's checklist) |
| 18 | The suggestion answers inside 75 s even with a hung fetch or a long `Retry-After` | T3 (`test_retry_after_60_waits_only_2_seconds`, deadline tests), T13 (`test_a_hung_fetch_is_cut_off_by_its_budget`, `test_the_ai_gets_the_75_second_deadline`) |
| 19 | Rubric-aware candidates, the 10-of-50 reserve, even sampling without facts, ranked pad, checklists and facts in the prompt; PR #4's tests ported | T6 (accessors), T11, T12 (clarification 15), T14 (the old file deleted) |
| 20 (server half) | Every `HymnOut` carries `text_year`, `hymnal_count`, `newer_than_preferred` from the church's year | T9 (`test_newer_than_preferred_follows_the_church_rubric`), T10, T13; the "Written {year}" label is 3b |

### S sections

| S item | Task(s) |
|---|---|
| API Models (`HymnRef`, `SlotHymns`, `SectionKey`, `HymnalCode`) | T1 |
| Backend 1: `openai_client`, settings, `requirements.txt`, `.env.example` | T2, T3 (clarification 5) |
| Backend 2: parsing | T4 (clarification 3) |
| Backend 2: matching and required results; `hymn_search` | T5 |
| Backend 1: `repos/hymns.py`, `hymn_ranking.py`, `repos/churches.py` | T6 |
| Backend 3.4: `usage_near` | T7 (owner answer Q2) |
| Backend 3.1, 3.2; `GET /church` extension | T8 |
| Backend 3.3; `GET /hymns`; GZip and the ops middleware test | T9 |
| Backend 3.5; `POST /hymns/scripture-matches` | T10 |
| Backend 3.6 step 6, 3.8 ranking | T11 |
| Backend 3.6 steps 7, 9, 3.8 prompt | T12 |
| Backend 3.6 steps 0-5, 8, 10, 3.7 worst case, 4, 6; `POST /hymns/suggestions`; the `ai` bucket | T13 |
| Backend 1 `worship_service.py` deletions; 5 "Streamlit coupling removed" | T14 |
| Data and migrations: no revision; the two read-only checks | T4 Step 1 (owner), T16 Step 9 (PR body) |
| Open questions 1 and 2 | answered (owner answers Q2, Q1); recorded by T15 |
| Testing "Backend" rows | T1-T14 (each row's file is created in the task named in the File Structure) |
| Frontend changes, UX, Manual checks, Frontend tests | 3b |
| Interfaces row 6a (`SETTINGS_HYMNS_READY`, invalidations) | 3b and 6a |

## Questions for the owner

None open. The owner's answers of 2026-09-29 (Q1-Q5, and A-D to the plan review) are binding and recorded under "Owner decisions". Owner steps still to come: the scripture export (T4 Step 1, gating "ready" in T16 Step 11) and the OpenAI key, $15 cap and model (T17 Steps 5-6).
