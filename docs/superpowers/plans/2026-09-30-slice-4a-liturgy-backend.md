# Slice 4a: Liturgy Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 4a of slice 4, the liturgy backend, with no screen change. The new app gains `GET /liturgy/config` (user-scoped: the 8 sections with their switch defaults, rows, hints and budgets, the 17 custom-element placements, the order of worship as `OUTLINE`, the communion text, the limits and whether AI is set up) and `POST /liturgy/generate` (church-scoped: one result per requested section, typed text returned exactly as sent, the rest written by the AI at most 4 at a time, AI and prompt failures returned per section inside a 200, charged to the `ai` bucket only for sections that reach the AI). `GET /church` gains `default_benediction`. `liturgy_config.py` becomes the one home of the liturgy constants; `liturgy_prompts` gains the template validator 6a reuses (`check_template`, `template_error`, `validate_prompts`, `clean_prompt_overrides`) and the prompt builder (`build_context`, `build_prompt`/`build_messages` with PR #4's rubric checklist and sermon text and PR #7's voice hook); `prayer_library.py` is the library's one reader. `worship_service` prints communion from `COMMUNION_BLOCKS` (the Word file is unchanged) and loses `generate_liturgy`. There is no migration (head stays `0004_invites_reusable`), the frontend changes only through the regenerated `openapi.json` and `schema.d.ts` plus one test fixture, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** Below the API, importing no FastAPI, Starlette or Streamlit: `liturgy_config.py` (pure data and two rules), `prayer_library.py` (pure reader and chooser), `liturgy_prompts.py` (pure validator and builder), `repos/churches.py` and `repos/hymns.py` (reads in the caller's session), `usecases/liturgy.py` (one session for every read, closed before any AI call; `charge(n)` once; a per-request pool of at most 4). `api/routes/liturgy.py` holds two thin plain-`def` routes and the route models; `SermonText` joins `api/schemas.py`. The OpenAI client (slice 3a) gains optional per-call `timeout_seconds` and `max_retries`, used for Prayers of the People (owner question 1). Tests use `FakeAI`, the SQLite fixtures and slice 2's limiter clock; the no-network guard stays on.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141.1, Pydantic 2.13.5, SQLAlchemy 2.1.1, python-docx 1.2.0 (installed; `python-docx>=1.0.0`), openai 3.20.0 (installed; `openai>=1.58.0,<4`), Alembic (no new revision), pytest; Next 16 / openapi-typescript 7 for the regenerated types only; GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Railway, Vercel, Supabase Postgres, OpenAI (`gpt-4.1-mini` on Railway).

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`. 4a is the backend: Scope "Backend", API (routes, Schemas, semantics 1-10, "Deviation from F"), Backend changes 1-6, "Streamlit coupling removed", "Tenancy and data access", Data and migrations, Testing "Backend" (with the 2026-09-26 amendment), acceptance criteria 1-10 and 19-21, Risks items 1-3 and 6. Its "Amendment 2026-09-26: service reviewer" is out of scope (owner answer 3), except its rule "Tests before and after": no 4a test quotes the default system prompt's season sentences; tests compare with `liturgy_prompts.default_prompts()["system"]` or `DEFAULT_SYSTEM_PROMPT`.
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (§1.1-§1.5, §1.8, §1.11, §2.2, §2.3, §2.5, §2.8, §6.1, the Decisions and Amendments tables).
- Related specs: `2026-09-25-service-rubric-design.md` (PR #4: `merge_rubric`, `format_checklist`), `2026-09-26-prayer-library-design.md` (PR #7 §Data and §Writer hook: the reader, limits and voice hook 4a ships), `2026-09-26-service-reviewer-design.md` (only its constraint on 4a's tests).
- Format model: `docs/superpowers/plans/2026-09-29-slice-3a-hymns-backend.md` (structure, conventions, Tasks 16-17), and the 3a and 3b "Build notes".
- Production facts: `docs/ops-runbook.md` (the Slice 3a and 3b records: `OPENAI_MODEL=gpt-4.1-mini`, a $15 monthly cap, the `ai` bucket; 3b's `vanderbilt_lectionary.church_season`, which 4a does not use: S puts no season line in the liturgy prompt).
- Facts checked for this plan (tree `9ab3fa6`, slices 3a and 3b merged and live, 2026-09-30):
  - Backend baseline `1110 passed, 11 skipped`; frontend `442 passed` in 64 files; Alembic head `0004_invites_reusable`; 4 runbook owner markers; `openai` 3.20.0; `python-docx` 1.2.0.
  - On `main`: `api/ratelimit.consume(bucket, *, user_id, church_id=None, cost=1)` exists (S's "if slice 2 did not ship one" is moot); `api/schemas.py` has 3a's `SectionKey`, `HymnRef`, `SlotHymns`, `HymnalCode`; `repos.churches.get_church_rubric_overrides(church_id, *, session=None)` exists (3a); `repos.churches.get_church_prompts(church_id)` has no `session` (T6 adds it); there is no by-id hymn lookup (T6 adds `get_hymns_by_ids`); `backend/prayer_library.py` does not exist (T4); `worship_service.generate_liturgy` (with PR #4's `rubric` and `sermon_text`), `_sermon_text_block` and `SERMON_TEXT_LIMIT` exist, and `build_docx` prints every heading as Heading 2 except communion's title (Heading 1) and still says "Old Testament Reading"; `service_rubric` imports `SECTION_ORDER` from `liturgy_prompts`; `integrations/openai_client.complete(messages, *, max_completion_tokens, json_mode=False, deadline=None)` and `FakeAI` exist (3a).
  - Every task's code in this plan was written and run by the planner in a throwaway worktree of `9ab3fa6`, with each red run and every count in the table observed. The plan text was then replayed onto a clean worktree of `9ab3fa6` (every Create, Append, Replace and Run directive below applied in order by a script, Tasks 1-12), reproducing each count and ending in a tree identical to the planner's. The frontend build (T13 Step 3) ran on this tree's frontend sources, which 4a changes only in generated types and one test fixture. The Postgres-marked tests ran on a local Postgres 16 (`11 passed, 1178 deselected, 1 warning`). Not run while planning: the pushes and CI (Task 13), the owner steps (Tasks 13 Step 9 and 14), and any call to OpenAI (the container cannot reach it).

## Global Constraints

"T<n>" below means Task n of this plan. "S", "F" and "inv" are the documents above.

### Commands and process
- Use `.venv/bin/python` (3.11) from the repo root. The working directory resets between commands. Run the frontend as `(cd frontend && ...)`. No foreground `sleep`, and never prove that something is absent by sleeping.
- Run one test file with `.venv/bin/python -m pytest -q <file> 2>&1 | tail -3`; the whole suite with `.venv/bin/python -m pytest -q | tail -1`.
- After any route or schema change, regenerate the OpenAPI files and commit both with the route: `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api)`, then `(cd frontend && npm run typecheck)`. Never hand-edit either file.
- Branch: `claude/slice-2-plan-4q33le` (this session's branch), from `9ab3fa6`. Its first commits are this plan (`WIP plan: slice 4a` commits, then `Plan: slice 4a liturgy backend (S slice 4; owner answers 2026-09-30)`).
- Stage files by name. `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Before merging, merge `origin/main` and rerun both suites. Run `gh pr merge <N> --merge -R bbrown62450/church` only on the owner's explicit yes.
- Every commit message has a subject, a body, and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- Commit subjects read "Area: plain words (S ..., F §x)". Use TDD: write the failing test first and quote its failure.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`. It includes the line "Tests: backend 1110 → 1178 passed, 11 → 11 skipped; frontend 442 → 442 in 64 files".
- **The container restarts** (2a-3b build notes): uncommitted work can be lost. Commit as soon as a task's checks pass. The controller, not the task agent, backs the branch up after each task's review with `git push origin claude/slice-2-plan-4q33le` (standing permission for backup pushes). If `frontend/node_modules` is gone after a restart, `(cd frontend && npm ci)`.
- **The network is filtered.** OpenAI, hymnary.org, the lectionary sites, bible-api.com and Railway are unreachable from the build container; PyPI and the npm registry are reachable. No test may need the network: the AI is `FakeAI`.
- **Grep gates exclude tests** and are judged, not obeyed blindly: read each hit, and if it is harmless say why in the task's report.
- **Owner steps one at a time, in plain words**, and every outward action (a push to a new place, the PR, ready, the merge, anything on Railway or Supabase) on its own yes.
- New prose for the owner uses no em dashes and no flattery and leads with the point; copy strings quoted from the spec keep theirs.

### How the file directives below read
Each file change is a bold directive followed by a fenced block, applied in the order written:
- **Create `path`:** the block is the whole file.
- **Append to `path`:** the block is added at the end of the file (its first line is usually blank).
- **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**.
- **In `path`, replace from the line starting `A` up to (not including) the line starting `B` with:** the lines from the one line starting with `A` up to the one line starting with `B` are replaced by the block (an empty block deletes them).
A directive that does not match exactly once is a stop: the tree is not what the plan expects.

### Baselines and counts
- Starting baselines: backend **1110 passed, 11 skipped**; frontend **442 passed in 64 files**; Alembic head **`0004_invites_reusable`** (4a adds no revision); owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any baseline differs, stop and ask.
- Planned cumulative backend counts (each observed while planning and again in the replay). If a count drifts, stop and find why.

  | After | Delta | Backend | Frontend |
  |---|---|---|---|
  | T1 | +8 | 1118 passed, 11 skipped | 442 in 64 |
  | T2 | +4 | 1122 passed, 11 skipped | 442 in 64 |
  | T3 | +7 | 1129 passed, 11 skipped | 442 in 64 |
  | T4 | +5 | 1134 passed, 11 skipped | 442 in 64 |
  | T5 | +15 | 1149 passed, 11 skipped | 442 in 64 |
  | T6 | +2 | 1151 passed, 11 skipped | 442 in 64 |
  | T7 | +14 | 1165 passed, 11 skipped | 442 in 64 |
  | T8 | +10 | 1175 passed, 11 skipped | 442 in 64 (generated types only) |
  | T9 | +1 | 1176 passed, 11 skipped | 442 in 64 (one fixture edited) |
  | T10 | +1 − 1 (the old-function oracle leaves) | 1176 passed, 11 skipped | 442 in 64 |
  | T11 | +2 | 1178 passed, 11 skipped | 442 in 64 |
  | T12 | 0 | 1178 passed, 11 skipped | 442 in 64 |

  If the owner answers "no" to question 1 (T11 is skipped), every count from T11 on is 1176, and the PR body's line says 1176.
- The frontend stays at 442 in 64 files throughout: T8 and T9 regenerate `openapi.json` and `schema.d.ts`, and T9 edits one fixture (clarification 18).
- At the end, CI `backend-postgres` shows `11 passed, 1178 deselected, 1 warning` (4a adds no Postgres test).
- Table-driven tests loop over their cases inside one test function (no new parametrize), so counts stay stable when cases are added. T10 keeps PR #4's two parametrized tests as they are.

### Layering and logging
- These modules import no fastapi, starlette or streamlit: `liturgy_config.py`, `prayer_library.py`, `liturgy_prompts.py`, `service_rubric.py`, `repos/*`, `usecases/*`, `integrations/openai_client.py`. `test_no_streamlit_in_core.py`'s import list grows in T1, T4, T5 and T7.
- Routes are plain `def`. They parse, guard and call one usecase with `church.id` only (F §1.2 rule 1), with no try/except and no SQL.
- `usecases.liturgy` logs one INFO line per call: `liturgy.generate church=<id> sections=<n> ai=<k> [rubric=default|custom sermon=yes|no voice=profile,example|none dropped=example,profile,sermon|-] outcomes=generated:x,override:y,error:z codes=<code:n,...|-> duration_ms=<ms> outcome=<ok|code>` (the bracketed facts appear when a section needs the AI). Prompts and answers are logged at DEBUG only; an unexpected exception from the AI call is logged with its stack (`logger.exception`), and an unusable answer (empty, or over 20 000 characters) with its length. Never a prompt, an answer, typed text, a title, the sermon text or a key at INFO.

### Messages (verbatim, from S)
- Section errors (S API semantics 7): `ai_not_configured` "AI not configured. Type this section yourself."; `ai_busy` "The AI service is busy. Try again in a minute."; `ai_timeout` "The AI took too long to answer. Try again."; `ai_upstream_error` "The AI service had a problem. Try again."; `prompt_invalid` "The {Label} prompt in Settings has a problem: {reason} An admin can fix it under Settings → Liturgy prompts."
- `prompt_invalid` reasons (S Backend 2): "This prompt is too long (max 8,000 characters)."; "It has a { or } without a partner. Use {{ or }} to print a brace."; "Placeholders need a name, such as {occasion}."; "Placeholders must be a plain name such as {occasion}, with no dots or brackets."; "Placeholders must be a single word such as {occasion}. To print a { or } as text, write {{ or }}."; "Placeholders can't include ! or :. Write just {occasion}."; "It can't be filled in. Check the { } placeholders."; and the length cap "It is too long once the readings, hymns and rubric checklist are added."
- 404 `not_found` (hymn id): "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
- Pydantic 422: "The request was not valid." with `fields`. Limiter 429: "Too many requests. Try again in {n} seconds." (unchanged).

### Codes and documented statuses
- 4a adds no error code: `ai_not_configured`, `ai_busy`, `ai_timeout`, `ai_upstream_error`, `prompt_invalid`, `not_found`, `invalid_request`, `rate_limited` exist in `domain_errors.ERROR_CODES`. The five AI and prompt codes travel as `SectionError.code` on `/liturgy/generate` (the declared deviation, already folded into F §1.5, §1.8 and §2.8).
- `error_responses` per route (`test_routes_document_the_error_body` gains both): `GET /liturgy/config` 401, 422, 503; `POST /liturgy/generate` 401, 403, 404, 422, 429, 503. `GET /church` is unchanged (401, 403, 422, 503).

### Buckets, budgets and limits
- `ai` (slice 2): 40 per 600 s per user and 400 per 86 400 s per church. `/liturgy/generate` has no rate-limit dependency: the usecase calls the route's `charge(n)` once, after hymn resolution and after every section's messages are built, with `n` = the sections about to call the AI, and never with 0 (S semantics 8). So a 401, 403, 404, 422, an override-only request, AI not configured and an all-`prompt_invalid` request cost nothing (unlike `/hymns/suggestions`, where the dependency charges first).
- Token budgets (`SectionSpec.max_completion_tokens`): 1 500, or 4 000 for Prayers of the People (S Backend 1).
- OpenAI per attempt: `OPENAI_TIMEOUT_SECONDS` 30 and `OPENAI_MAX_RETRIES` 1, except Prayers of the People: one 60 s attempt, no retry (T11, owner question 1). No deadline is passed (F §1.8 row `/liturgy/generate`: the 15 s slot wait plus the attempts; worst case 15 + 30 + 2 + 30 = 77 s, or 15 + 60 = 75 s for Prayers of the People, inside the client's 90 s).
- Prompt: `MAX_TEMPLATE_CHARS` 8 000 per template; `MAX_PROMPT_CHARS` 24 000 for system + user; sermon text cut to 2 000; voice profile stripped and cut to 2 000; example cut to 3 000; an answer over 20 000 characters is `ai_upstream_error`.
- Request limits (S Schemas): `occasion` ≤ 300; `scriptures` ≤ 20 of ≤ 200; `sections` 1-4 `SectionKey`s; `overrides` `SectionKey` → ≤ 20 000; `hymns` is 3a's `SlotHymns` of `HymnRef` (title ≤ 300, number 0-100 000, hymnal ≤ 20, no pattern); `sermon_text` optional `{ref ≤ 200, text ≤ 20 000}`; `extra="forbid"` everywhere.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried from slices 2 and 3). Each is recorded as a numbered clarification: "(owner decision 1; ...)".
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
   - The F §6.1 item 6 contingency is off (F §6.1 amendment of 2026-09-28; 3a owner decision 2): no `generate_liturgy` wrapper, no `AppTest` smoke (clarification 2).
   - `app.py`, `ui_helpers.py`, `streamlit_tenancy.py` and `streamlit_views/*` are untouched. `app.py` on `main` stops importing once T10 deletes `generate_liturgy`, which it imports; that is accepted, as in 2a and 3a (no test imports `app.py`; T1's test only parses its text).
3. **Railway** keeps its Pre-deploy Command (`alembic upgrade head`) and Healthcheck Path (`/health/ready`); 4a changes neither, and the pre-deploy is a no-op at head `0004`.
4. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
5. **Owner decisions 2 and 9** (S): typed text is used verbatim and never changed by the AI; generating without a key is allowed (typed sections come back, the rest say "AI not configured"). **Owner decision B**: the first reading's heading is "First Reading" wherever the app shows it (clarifications 3, 4).

### Owner answers (2026-09-30, "all recommended", binding)
1. **Custom elements get no AI Generate** (S Risks item 7 answered "no"). T12 records it in F's decisions table as **D17** and marks S's item 7 answered. Nothing custom in 4a.
2. **Slice 4 ships as two PRs:** 4a backend (this plan), 4b frontend later.
3. **The service reviewer add-on** is a separate small slice after 4b; not in 4a. 4a follows its "Tests before and after" rule: no test quotes the default system prompt's season sentences.
4. **Owner steps:**
   - (a) **Before 4a is marked ready** (as 3a's scripture export gated ready): a read-only Supabase query lists the stored prompt overrides (S Risks item 3; `churches.settings` is `json`, not `jsonb`, so `settings->'liturgy_prompts' is not null`), one step at a time, showing only an 8-character prefix of each church id; the agent runs `validate_prompts` on each locally and reports any failure to the owner, who fixes it in Streamlit Settings → Liturgy prompts before the switch (T13 Steps 9-10).
   - (b) **After the merge**, a live check that includes one real Prayers of the People generation with `gpt-4.1-mini`, timed against the per-attempt timeout and the token budget (S Risks items 1-2), with a decision rule (T14 Steps 5-7).
5. **Testing:** automated tests; the owner's live checks are signed-in Console calls like 3a Task 17 (`GET /liturgy/config`, `POST /liturgy/generate` for a couple of sections including Prayers of the People, `GET /church`'s `default_benediction`), one step at a time.

### Questions for the owner before the build
Both are asked in one message before T1 starts; the plan is written for the recommended answers.
1. **Prayers of the People: one 60 s attempt from the start? (Recommended: yes.)** S Risks 1 plans to add an optional `timeout_seconds` to the OpenAI client only if a live Prayers of the People times out at 30 s. A 10-15 paragraph prayer (about 1 000-1 400 words) can take 20-40 s on `gpt-4.1-mini`, and at 30 s a slow answer would fail, retry and likely fail again after about a minute, costing twice. T11 adds the keyword now (small, additive, tested) and gives only Prayers of the People one 60 s attempt with no retry, so its worst case is 15 s (a slot) + 60 s = 75 s, inside the page's 90 s. The live check (T14) still times a real one. If the owner says no, skip T11 (the counts from T11 on stay 1176), drop T12's F row and S bullet on the timeout, and use T14 Step 7's decision rule as S wrote it.
2. **"After First Reading" in the custom-element place list? (Recommended: yes.)** Owner decision B renamed the first reading's heading to "First Reading" wherever the app shows it; app.py's place list still says "After Old Testament Reading". T1 serves "After First Reading" (the key `ot_reading` is unchanged, so saved elements keep their place). If the owner prefers the old words, T1's label and its test change back to app.py's exact text.

## Spec clarifications

Code and F win over S; each is owner decision 1 unless marked **owner-visible**.

1. **(Owner answer 1; owner-visible, answered.)** Custom elements have no Generate. T12 adds F D17 and marks S Risks item 7 and S's header line answered. 4a has no `custom` request kind.
2. **No freeze-contingency code.** F §6.1 item 6 is not in effect, so S Backend 6's "keep `generate_liturgy` instead, as a wrapper", the usecase's `use_library` parameter (used only by that wrapper) and the reviewer amendment's `LEGACY_SYSTEM_PROMPT` / `legacy_default_prompts()` are not built. T10 deletes `generate_liturgy`; `app.py` on `main` then no longer imports (owner decision 2).
3. **(Owner-visible in 4b; owner question 2.) The first reading's place reads "After First Reading".** S says the 17 placements are app.py:148-166 "verbatim", but owner decision B says "First Reading" wherever the app shows that heading. `CUSTOM_PLACEMENTS` keeps app.py's keys, order and 16 labels and changes that one label; T1's test reads app.py's list from its source (never importing it) and pins the one difference.
4. **The outline/docx test maps one heading until 5a.** `OUTLINE`'s row 7 says "First Reading" (S), but `build_docx` still prints "Old Testament Reading" and the Word files belong to 5a (S "Out of scope"). T2's test reads the docx through `DOCX_HEADINGS_UNTIL_5A = {"ot_reading": "Old Testament Reading"}`; 5a changes `build_docx` and deletes the map in the same PR.
5. **Section hints live in `SectionSpec.hint`.** S's hint table: Call to Worship and Prayer of Confession as written; Assurance "Added automatically after your text." (4b shows it under the fixed `assurance_response` line); Benediction "Your church's default benediction. Admins can change it in Settings." (4b shows it only while the card's origin is `default`); Prayers of the People none (its chip comes from `pastor_copy_only`).
6. **`service_rubric` imports `SECTION_ORDER` from `liturgy_config`.** `liturgy_prompts` now imports `service_rubric` (for `format_checklist`), which imported `SECTION_ORDER` from `liturgy_prompts`: an import cycle. The list is the same object (`liturgy_prompts.SECTION_ORDER is liturgy_config.SECTION_ORDER`, pinned in T3).
7. **`repos.hymns.get_hymns_by_ids` returns 3a's `HymnRecord`s** keyed by id, not dicts, in one `SELECT ... WHERE church_id = :c AND id IN (...)`. An id it cannot coerce is simply absent; the usecase raises the 404 with S's message for every id it does not find (another church's, a deleted hymn, a malformed id).
8. **`build_prompt` returns `BuiltPrompt(messages, dropped)`**, and `build_messages` (S's name, for 6a and the reviewer) returns its messages. The usecase needs `dropped` for S's log field `dropped=example,profile,sermon`.
9. **Client text goes into the prompt on one line.** `build_context` collapses whitespace (newlines included) in the occasion (cut to 300), each reading (200; blank ones dropped), each hymn title (300) and the sermon reference (200), as 3a's `hymn_suggest._clip` does, so a field cannot add prompt lines of its own. The sermon passage stays multi-line. A slot whose title is blank counts as empty. For one-line inputs the messages equal `generate_liturgy`'s (T5's oracle test).
10. **Stored JSON is read defensively.** `get_church_prompts` returns `{}` for a stored value that is not an object; `merge_prompts` ignores values that are not strings (it would have raised on `.strip()`); `validate_prompts` checks only what `merge_prompts` would use (a non-blank string under a `PROMPT_KEYS` key); `check_template` on a non-string is "It can't be filled in." and never raises.
11. **`check_template` runs its checks in S's table order across all placeholders**, returning the first check that any placeholder fails (S: "runs these checks in order and returns the first failure"). So `"{a.b} {}"` gets "Placeholders need a name, ...".
12. **An override comes back exactly as sent** (S semantics 3), where `generate_liturgy` stripped it. 4b sends no overrides (S Frontend `request.ts`); this only affects API callers.
13. **The prayer library reader** (`prayer_library.read_library`): a stored value that is not an object, or whose `prayers` is not a list, reads as the empty library; a single prayer entry of the wrong shape (not an object, a type outside `PRAYER_TYPES`, text not a string) is skipped and the rest kept; a `voice_profile` that is not a string reads as "". The reader enforces none of 6a's write limits. `choose_example` never picks a prayer whose text is blank.
14. **The rate-limit tests read the bucket by behavior.** With the user's 40 tokens spent on the limiter's `FakeClock` (`limiter_clock`), a request that charges 0 still answers 200 and one that charges 1 gets 429; the 41st-section test spends 36, sends 4 sections, then gets 429 with `Retry-After: 15`.
15. **The communion characterization compares with a verbatim legacy copy**, in the same run: `test_communion_docx.py` keeps the old `_add_communion_liturgy` as `_legacy_communion` and compares the documents' body XML (with communion, and the helper alone), so the python-docx version (CI installs the newest `>=1.0.0`) cannot matter. A stored hash would.
16. **(Owner question 1; owner-visible only as "fewer timeouts".)** `complete()` gains optional `timeout_seconds` and `max_retries`; `SectionSpec` gains `timeout_seconds` and `max_retries` (None = the settings); Prayers of the People has 60.0 and 0 (T11). `FakeAI` records the two only when a caller sets them, so 3a's exact-call test is unchanged.
17. **`HymnRef` and `SlotHymns` enter the OpenAPI snapshot** with `/liturgy/generate`, the first route that accepts them. 3a's `test_hymnal_code_pattern_and_models_absent_from_openapi` becomes `test_hymnal_code_pattern_and_models_in_openapi_unchanged`, asserting they are present with no pattern on `hymnal` (T8).
18. **One frontend test fixture changes** (as 3a clarification 13): `frontend/src/test/fixtures/index.ts`'s `churchProfile()` gains `default_benediction: "Halverson"`; the regenerated `ChurchProfileOut` makes it required and `tsc` fails without it (T9). No frontend test or count changes. 4b treats the field as optional (S).
19. **`liturgy.generate` also logs a failed call** (`outcome=not_found`, `rate_limited` or `internal_error`), as 3a's suggestion line does; S names only the success line.
20. **A per-request pool.** The usecase runs each request's AI sections on its own `ThreadPoolExecutor(max_workers=min(4, n))`, each task in a copy of the request's context so its log lines keep the request id (2a build note); the pool is joined before the usecase returns, so no test reset hook is needed.
21. **The system prompt is not template-checked.** `build_prompt` checks only the section's template (S step 1); a stored system prompt over 8 000 characters (possible only from Streamlit) shows up as the 24 000-character cap, as S's test 4 expects.
22. **`GET /liturgy/config`'s function is `get_liturgy_config`** (its OpenAPI operation id is `get_liturgy_config_liturgy_config_get`); the POST's is `generate_liturgy`.
23. **Risk 3's query shows an 8-character id prefix** and skips soft-deleted churches (owner answer 4a): `select left(id::text, 8) as church, settings->'liturgy_prompts' as prompts from churches where settings->'liturgy_prompts' is not null and deleted_at is null order by 1;`. A church whose admin reset every prompt in Streamlit stores `{}`, which is listed and passes.

### Risks carried into the plan
- **Stored prompts that fail the new checks.** Streamlit never validated them; such a section answers `prompt_invalid` in the new app. The pre-ready check (T13 Steps 9-10) finds them; the owner fixes them in Streamlit before the switch.
- **Prayers of the People's time and budget (S Risks 1-2).** Unmeasured until the owner's live check (T14 Step 6). With T11, a 60 s single attempt; without it, 30 s plus one retry. An empty or cut-off answer is `ai_upstream_error`, never stored. The decision rule is T14 Step 7.
- **Frozen `app.py` on `main`** no longer imports after T10 (accepted, owner decision 2).
- **Cost exposure** is bounded by the `ai` bucket (40 sections per 10 minutes per user, 400 per day per church) and the owner's $15 monthly cap; a full liturgy is about 6 calls (S Risks 5).
- **Legacy liturgy keys** (S Risks 6) are 5a's.

## File Structure

**Created**

| Path | Responsibility |
|---|---|
| `docs/superpowers/plans/2026-09-30-slice-4a-liturgy-backend.md` | this plan |
| `backend/liturgy_config.py` | `SectionSpec`, `SECTIONS`, `SECTION_ORDER`, `SECTION_LABELS`, `SECTIONS_BY_KEY`, `CUSTOM_PLACEMENTS`, `PLACEMENT_KEYS`, `normalize_placement`, `OutlineItem`, `OUTLINE`, `outline_as_json`, `ASSURANCE_RESPONSE`, `COMMUNION_TITLE`, `COMMUNION_TOGGLE_LABEL`, `CommunionBlock`, `COMMUNION_BLOCKS`, `DEFAULT_BENEDICTION_FALLBACK`, `Limits`, `LIMITS`, `is_first_sunday_of_month`, `resolve_default_benediction` (T1; T11 adds two `SectionSpec` fields) |
| `backend/prayer_library.py` | `PRAYER_TYPES`, the limits, `Prayer`, `PrayerLibrary`, `EMPTY_LIBRARY`, `read_library`, `choose_example` (T4) |
| `backend/usecases/liturgy.py` | `HymnRefData`, `SectionOutcome`, `dedupe`, `sections_needing_ai`, `generate_liturgy` (T7; T11 passes the per-call limits) |
| `backend/api/routes/liturgy.py` | the route models; `GET /liturgy/config`, `POST /liturgy/generate` (T8) |
| `backend/tests/fixtures/shared/liturgy_sections.json`, `first_sunday.json`, `liturgy_outline.json` | the shared cases 4b's TypeScript reads too (T1) |
| New test files | `test_liturgy_config` (T1, T2, T11), `test_communion_docx` (T2), `test_prayer_library` (T4), `test_liturgy_generation` (T5, T10), `test_usecase_liturgy` (T7, T11), `test_api_liturgy` (T8) |

**Modified**

| Path | Change |
|---|---|
| `backend/worship_service.py` | `_add_communion_liturgy` over `COMMUNION_BLOCKS` (T2); `generate_liturgy`, `_sermon_text_block`, `SERMON_TEXT_LIMIT` and the `openai`, `os`, `liturgy_prompts` and `service_rubric` imports deleted (T10) |
| `backend/liturgy_prompts.py` | `SECTION_ORDER`/`SECTION_LABELS` from `liturgy_config`; `merge_prompts` skips non-strings; the validator (T3); the prompt builder (T5) |
| `backend/service_rubric.py` | `SECTION_ORDER` from `liturgy_config` (T5; clarification 6) |
| `backend/repos/churches.py` | `get_church_prompts(church_id, *, session=None)` (T6) |
| `backend/repos/hymns.py` | `get_hymns_by_ids` (T6) |
| `backend/api/schemas.py` | `SermonText` (T8); `ChurchProfileOut.default_benediction` (T9) |
| `backend/api/main.py` | mount `liturgy` (T8) |
| `backend/usecases/church_profile.py` | `default_benediction` (T9) |
| `backend/integrations/openai_client.py` | `complete(..., timeout_seconds=None, max_retries=None)`; `FakeAI` records them (T11) |
| `backend/tests/test_no_streamlit_in_core.py` | import list (T1, T4, T5, T7) |
| `backend/tests/test_liturgy_prompts.py` | T3's and T5's tests |
| `backend/tests/test_churches_repo.py`, `test_hymns_repo.py` | T6's tests |
| `backend/tests/test_route_guards.py`, `test_api_app.py`, `test_schemas.py` | `USER_SCOPED`, the error-doc map, the snapshot test (T8) |
| `backend/tests/test_api_church_profile.py`, `test_api_me.py`, `test_api_invites.py`, `test_api_churches.py` | `/church` exact bodies and one new test (T9) |
| `backend/tests/test_generate_liturgy.py` | retargeted to the new functions (T10) |
| `backend/tests/test_hymn_match_parity.py` | no longer asserts `generate_liturgy` exists (T10) |
| `backend/tests/test_openai_client.py` | one test (T11) |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated (T8, T9) |
| `frontend/src/test/fixtures/index.ts` | `churchProfile()` gains `default_benediction` (T9; clarification 18) |
| `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` | D17; the §1.8/§2.8 amendment row (T12) |
| `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md` | item 7 answered; "Notes from the slice 4a plan" (T12) |
| `docs/ops-runbook.md` | the `OPENAI_API_KEY` row mentions liturgy (T12) |

**Deleted:** nothing (T10 deletes code inside `worship_service.py`, not files).

**Untouched:** migrations, `db/models.py`, `app.py`, `ui_helpers.py`, `streamlit_views/*`, `streamlit_tests/*`, CI workflows, every frontend source file except the generated API files and one test fixture.

**Task order and review batches:** T1 → T12 each end in one commit; T13 verifies the branch, opens the draft PR (owner's yes), runs the owner's pre-ready check and marks it ready (owner's yes); T14 merges (owner's yes) and runs the live checks. The controller reviews in four batches and backs up after each task:
- **Batch A (T1-T3):** the fixed data, the Word file tie and the validator.
- **Batch B (T4-T6):** the prayer library, the prompt builder and the repos.
- **Batch C (T7-T9):** the usecase, the routes and `GET /church`.
- **Batch D (T10-T12):** the deletion, the timeout and the docs.

---
### Task 1: `liturgy_config.py` and the shared fixtures (S Backend 1; Testing `test_liturgy_config.py`; AC1; clarifications 3, 5)

This task creates the one home of the liturgy constants app.py held: the 8 sections with their switch defaults, rows, hints and token budgets; the 17 custom-element placements; the order of worship as `OUTLINE` (with `outline_as_json()`, the shape `GET /liturgy/config` serves); the assurance response; the communion text as `COMMUNION_BLOCKS`; the limits; the first-Sunday rule and the default-benediction resolver. Three shared fixtures are added for 4b's TypeScript. Nothing uses the module yet except its tests.

**Files:**
- Create: `backend/liturgy_config.py`, `backend/tests/test_liturgy_config.py`, `backend/tests/fixtures/shared/liturgy_sections.json`, `backend/tests/fixtures/shared/first_sunday.json`, `backend/tests/fixtures/shared/liturgy_outline.json`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes: `app.py`'s `CUSTOM_PLACEMENTS` list literal (read with `ast` from the file, never imported); `test_fixtures_recorder.py` already ignores `fixtures/shared/`.
- Produces (later users: T2-T11, 4b through `GET /liturgy/config`, 5a, 6a):
  - `SectionSpec(key, label, default_enabled, rows, pastor_copy_only, hint, max_completion_tokens)`; `SECTIONS`, `SECTION_ORDER: list[str]`, `SECTION_LABELS: dict[str, str]`, `SECTIONS_BY_KEY`
  - `CUSTOM_PLACEMENTS: tuple[tuple[str, str], ...]`, `PLACEMENT_KEYS: frozenset[str]`, `normalize_placement(key) -> str` (unknown → `"end"`)
  - `OutlineItem(kind, key, label, value_source, fixed_text, anchors_after)`, `OUTLINE` (16 items), `outline_as_json() -> list[dict]`
  - `ASSURANCE_RESPONSE`, `COMMUNION_TITLE`, `COMMUNION_TOGGLE_LABEL`, `CommunionBlock(style, text)`, `COMMUNION_BLOCKS`, `DEFAULT_BENEDICTION_FALLBACK = "Halverson"`, `Limits`, `LIMITS`
  - `is_first_sunday_of_month(d: date) -> bool`, `resolve_default_benediction(settings) -> str`

- [ ] **Step 1 (agent): Confirm the branch, the baseline and the owner's answers**

```bash
git status --short
git log --oneline -3
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
ls backend/migrations/versions | grep -c '^0'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
```

**Expected:** `git status --short` lists only `?? .claude/` (or nothing); the log shows `<sha> Plan: slice 4a liturgy backend (S slice 4; owner answers 2026-09-30)` above the plan's `WIP plan: slice 4a` commits and `9ab3fa6 Merge pull request #29 ...`; `1110 passed, 11 skipped in <t>s`; ` Test Files  64 passed (64)` and `      Tests  442 passed (442)`; `4`; `4`. The controller has the owner's answers to "Questions for the owner before the build" (the plan is written for "yes" to both). If anything differs, stop and ask.

- [ ] **Step 2 (agent): Write the failing tests and the shared fixtures**

**Create `backend/tests/fixtures/shared/liturgy_sections.json`:**

````json
{
  "_about": "The 8 liturgy sections in order, with their labels and default switch states (slice 4 spec, Testing). backend/liturgy_config.SECTIONS must equal it (test_liturgy_config.py); 4b's fresh-draft card switches read it too (defaults.test.ts).",
  "sections": [
    {"key": "call_to_worship", "label": "Call to Worship", "default_enabled": true},
    {"key": "opening_prayer", "label": "Opening Prayer", "default_enabled": true},
    {"key": "prayer_of_confession", "label": "Prayer of Confession", "default_enabled": true},
    {"key": "assurance", "label": "Assurance of Pardon", "default_enabled": true},
    {"key": "prayer_for_illumination", "label": "Prayer for Illumination", "default_enabled": true},
    {"key": "prayers_of_the_people", "label": "Prayers of the People", "default_enabled": false},
    {"key": "offertory_prayer", "label": "Offertory Prayer", "default_enabled": true},
    {"key": "benediction", "label": "Benediction", "default_enabled": true}
  ]
}
````

**Create `backend/tests/fixtures/shared/first_sunday.json`:**

````json
{
  "_about": "The communion default: a Sunday in the first 7 days of its month (app.py:969-971). backend/liturgy_config.is_first_sunday_of_month runs every case (test_liturgy_config.py); 4b's firstSundayOfMonth does too (defaults.test.ts).",
  "cases": [
    {"date": "2026-10-04", "expected": true, "why": "the first Sunday of October"},
    {"date": "2026-10-11", "expected": false, "why": "the second Sunday"},
    {"date": "2026-11-01", "expected": true, "why": "a Sunday on the 1st"},
    {"date": "2026-11-07", "expected": false, "why": "a Saturday in the first week"},
    {"date": "2026-12-06", "expected": true, "why": "a Sunday on the 6th"},
    {"date": "2026-12-24", "expected": false, "why": "Christmas Eve, a Thursday"},
    {"date": "2026-02-01", "expected": true, "why": "a Sunday on the 1st"},
    {"date": "2026-03-08", "expected": false, "why": "a Sunday on day 8"},
    {"date": "2026-03-07", "expected": false, "why": "day 7, a Saturday"},
    {"date": "2026-06-07", "expected": true, "why": "a Sunday on day 7"}
  ]
}
````

**Create `backend/tests/fixtures/shared/liturgy_outline.json`:**

````json
{
  "_about": "The order of worship: backend/liturgy_config.OUTLINE serialized as GET /liturgy/config's outline (OutlineItemOut). Generated, never hand-edited: test_liturgy_config.py keeps it equal to OUTLINE and prints the command that rewrites it. 5a builds its order fixtures and tests from this file.",
  "outline": [
    {"kind": "section", "key": "call_to_worship", "label": "Call to Worship", "value_source": "none", "fixed_text": null, "anchors_after": ["call_to_worship"]},
    {"kind": "section", "key": "opening_prayer", "label": "Opening Prayer", "value_source": "none", "fixed_text": null, "anchors_after": ["opening_prayer"]},
    {"kind": "landmark", "key": "first_hymn", "label": "First Hymn", "value_source": "hymn_opening", "fixed_text": null, "anchors_after": ["first_hymn"]},
    {"kind": "section", "key": "prayer_of_confession", "label": "Prayer of Confession", "value_source": "none", "fixed_text": null, "anchors_after": ["prayer_of_confession"]},
    {"kind": "section", "key": "assurance", "label": "Assurance of Pardon", "value_source": "none", "fixed_text": null, "anchors_after": ["assurance"]},
    {"kind": "section", "key": "prayer_for_illumination", "label": "Prayer for Illumination", "value_source": "none", "fixed_text": null, "anchors_after": ["prayer_for_illumination"]},
    {"kind": "landmark", "key": "ot_reading", "label": "First Reading", "value_source": "reading_ot", "fixed_text": null, "anchors_after": ["ot_reading"]},
    {"kind": "landmark", "key": "nt_reading", "label": "New Testament Reading", "value_source": "reading_nt", "fixed_text": null, "anchors_after": ["nt_reading"]},
    {"kind": "landmark", "key": "sermon", "label": "Sermon Title", "value_source": "sermon_title", "fixed_text": null, "anchors_after": ["sermon"]},
    {"kind": "landmark", "key": "affirmation_of_faith", "label": "Affirmation of Faith", "value_source": "fixed", "fixed_text": "Apostles' Creed", "anchors_after": ["affirmation_of_faith"]},
    {"kind": "landmark", "key": "second_hymn", "label": "Second Hymn", "value_source": "hymn_response", "fixed_text": null, "anchors_after": ["second_hymn"]},
    {"kind": "communion", "key": "communion", "label": "The Sacrament of the Lord's Supper", "value_source": "none", "fixed_text": null, "anchors_after": ["communion"]},
    {"kind": "section", "key": "prayers_of_the_people", "label": "Prayers of the People", "value_source": "none", "fixed_text": null, "anchors_after": ["prayers_of_the_people"]},
    {"kind": "section", "key": "offertory_prayer", "label": "Offertory Prayer", "value_source": "none", "fixed_text": null, "anchors_after": ["offertory_prayer"]},
    {"kind": "landmark", "key": "third_hymn", "label": "Third Hymn", "value_source": "hymn_closing", "fixed_text": null, "anchors_after": ["third_hymn", "benediction"]},
    {"kind": "section", "key": "benediction", "label": "Benediction", "value_source": "none", "fixed_text": null, "anchors_after": ["end"]}
  ]
}
````

**Create `backend/tests/test_liturgy_config.py`:**

````python
"""liturgy_config: the liturgy step's fixed data (slice 4 spec, Backend 1;
Testing `test_liturgy_config.py`; AC1, AC2). The shared fixtures under
tests/fixtures/shared/ are the authority 4b's TypeScript reads too."""
import ast
import json
from datetime import date
from pathlib import Path

import liturgy_config as lc

SHARED = Path(__file__).resolve().parent / "fixtures" / "shared"
APP_PY = Path(__file__).resolve().parents[2] / "app.py"
OUTLINE_FIXTURE = SHARED / "liturgy_outline.json"
REGENERATE = "PYTHONPATH=backend .venv/bin/python backend/tests/test_liturgy_config.py"


def _shared(name: str) -> dict:
    return json.loads((SHARED / name).read_text(encoding="utf-8"))


def write_outline_fixture() -> None:
    """Rewrite shared/liturgy_outline.json from OUTLINE (one item per line)."""
    about = _shared("liturgy_outline.json")["_about"]
    lines = ",\n".join("    " + json.dumps(item, ensure_ascii=False) for item in lc.outline_as_json())
    OUTLINE_FIXTURE.write_text('{\n  "_about": ' + json.dumps(about) + ',\n  "outline": [\n'
                               + lines + "\n  ]\n}\n", encoding="utf-8")


def test_sections_match_the_shared_fixture():
    expected = _shared("liturgy_sections.json")["sections"]
    assert [{"key": s.key, "label": s.label, "default_enabled": s.default_enabled}
            for s in lc.SECTIONS] == expected
    assert lc.SECTION_ORDER == [s["key"] for s in expected]
    assert lc.SECTION_LABELS == {s["key"]: s["label"] for s in expected}
    assert lc.SECTIONS_BY_KEY["benediction"].label == "Benediction"


def test_rows_budgets_pastor_copy_and_hints():
    for spec in lc.SECTIONS:
        pastor = spec.key == "prayers_of_the_people"
        assert (spec.rows, spec.max_completion_tokens, spec.pastor_copy_only) == (
            (8, 4000, True) if pastor else (4, 1500, False)), spec.key
    hints = {s.key: s.hint for s in lc.SECTIONS if s.hint is not None}
    assert hints == {
        "call_to_worship": "Start lines with “Leader:” or “People:”. People lines print in bold.",
        "prayer_of_confession": "Printed in bold for everyone to read together.",
        "assurance": "Added automatically after your text.",
        "benediction": "Your church's default benediction. Admins can change it in Settings.",
    }


def _app_py_placements() -> list[tuple[str, str]]:
    """The CUSTOM_PLACEMENTS list literal in the frozen app.py (read, never imported)."""
    tree = ast.parse(APP_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "CUSTOM_PLACEMENTS" for t in node.targets):
            return [tuple(pair) for pair in ast.literal_eval(node.value)]
    raise AssertionError("CUSTOM_PLACEMENTS not found in app.py")


def test_custom_placements_are_app_py_s_17_with_the_first_reading_label():
    frozen = _app_py_placements()
    assert len(frozen) == len(lc.CUSTOM_PLACEMENTS) == 17
    # Owner decision B: "First Reading" wherever the app shows that heading.
    renamed = [("ot_reading", "After First Reading") if key == "ot_reading" else (key, label)
               for key, label in frozen]
    assert list(lc.CUSTOM_PLACEMENTS) == renamed
    assert lc.PLACEMENT_KEYS == {key for key, _ in frozen}


def test_every_placement_is_anchored_exactly_once():
    anchors = [anchor for item in lc.OUTLINE for anchor in item.anchors_after]
    assert sorted(anchors) == sorted(lc.PLACEMENT_KEYS)
    assert len(anchors) == len(set(anchors)) == 17
    assert [item.key for item in lc.OUTLINE if item.kind == "section"] == lc.SECTION_ORDER
    assert len(lc.OUTLINE) == 16
    third_hymn = next(item for item in lc.OUTLINE if item.key == "third_hymn")
    assert third_hymn.anchors_after == ("third_hymn", "benediction")      # "Before Benediction"


def test_outline_fixture_equals_outline():
    stored = _shared("liturgy_outline.json")["outline"]
    assert stored == lc.outline_as_json(), f"shared/liturgy_outline.json is stale. Regenerate: {REGENERATE}"


def test_first_sunday_cases():
    for case in _shared("first_sunday.json")["cases"]:
        assert lc.is_first_sunday_of_month(date.fromisoformat(case["date"])) is case["expected"], case


def test_resolve_default_benediction():
    cases = [
        (None, "Halverson"),
        ({}, "Halverson"),
        ({"default_benediction": 5}, "Halverson"),
        ({"default_benediction": None}, "Halverson"),
        ({"default_benediction": ""}, ""),
        ({"default_benediction": "May the Lord bless you…"}, "May the Lord bless you…"),
        ("not a mapping", "Halverson"),
    ]
    for settings, expected in cases:
        assert lc.resolve_default_benediction(settings) == expected, settings


def test_normalize_placement_limits_and_fixed_text():
    assert lc.normalize_placement("bogus") == "end"
    assert lc.normalize_placement(None) == "end"
    assert lc.normalize_placement("communion") == "communion"
    assert lc.LIMITS == lc.Limits(max_section_text=20_000, max_sermon_title=300, max_custom_elements=30,
                                  max_custom_label=200, max_custom_text=10_000, max_sections_per_request=4)
    assert lc.ASSURANCE_RESPONSE == "People: Thanks be to God! Amen."
    assert lc.DEFAULT_BENEDICTION_FALLBACK == "Halverson"
    assert lc.COMMUNION_TOGGLE_LABEL == "Include communion liturgy (The Sacrament of the Lord's Supper)"
    assert lc.COMMUNION_BLOCKS[0] == lc.CommunionBlock("heading1", lc.COMMUNION_TITLE)
    assert [b.text for b in lc.COMMUNION_BLOCKS if b.style == "heading2"] == [
        "Invitation to the Table", "Great Thanksgiving", "Words of Institution", "The Lord's Prayer",
        "Breaking of the Bread and Communion", "Prayer After Communion"]


if __name__ == "__main__":
    write_outline_fixture()
    print(f"wrote {OUTLINE_FIXTURE}")
````

- [ ] **Step 3 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_config.py 2>&1 | tail -3
```

**Expected:**

```
ERROR backend/tests/test_liturgy_config.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```

The collection error is `ModuleNotFoundError: No module named 'liturgy_config'`.

- [ ] **Step 4 (agent): Add the module and keep it Streamlit-free**

**Create `backend/liturgy_config.py`:**

````python
"""The liturgy step's fixed data (slice 4 spec, Backend 1; F §2.3 step 2).

The one home of the constants the Streamlit app held (app.py:67, 148-166, the
four section-list copies and 969-971) and of the communion text that
worship_service's docx helper held (worship_service.py:68-135):

- SECTIONS (and SECTION_ORDER, SECTION_LABELS): the 8 liturgy sections, their
  default switch states, textarea rows, hints and AI token budgets.
- CUSTOM_PLACEMENTS, PLACEMENT_KEYS, normalize_placement: where a custom
  element prints.
- OUTLINE: the order of worship exactly as build_docx prints it, the only
  encoding of that order (5a's orderOfWorship receives it from
  GET /liturgy/config; shared/liturgy_outline.json is generated from it).
- ASSURANCE_RESPONSE, COMMUNION_*, DEFAULT_BENEDICTION_FALLBACK, LIMITS.
- is_first_sunday_of_month, resolve_default_benediction.

Pure: standard library only, so every layer can import it
(tests/test_no_streamlit_in_core.py). app.py on main keeps its own frozen
copies; nothing is re-exported from Streamlit modules.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Optional


@dataclass(frozen=True)
class SectionSpec:
    key: str
    label: str
    default_enabled: bool
    rows: int
    pastor_copy_only: bool
    hint: Optional[str]
    max_completion_tokens: int


# SECTION_ORDER order; labels as liturgy_prompts.py:29-38 had them. Hints mirror
# the docx formatting (worship_service.py _add_leader_people_paragraph, the bold
# confession, _add_assurance_paragraph); 4b shows Assurance's hint under the
# fixed ASSURANCE_RESPONSE line and Benediction's only while the card follows
# the church default.
SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("call_to_worship", "Call to Worship", True, 4, False,
                "Start lines with “Leader:” or “People:”. People lines print in bold.", 1500),
    SectionSpec("opening_prayer", "Opening Prayer", True, 4, False, None, 1500),
    SectionSpec("prayer_of_confession", "Prayer of Confession", True, 4, False,
                "Printed in bold for everyone to read together.", 1500),
    SectionSpec("assurance", "Assurance of Pardon", True, 4, False,
                "Added automatically after your text.", 1500),
    SectionSpec("prayer_for_illumination", "Prayer for Illumination", True, 4, False, None, 1500),
    SectionSpec("prayers_of_the_people", "Prayers of the People", False, 8, True, None, 4000),
    SectionSpec("offertory_prayer", "Offertory Prayer", True, 4, False, None, 1500),
    SectionSpec("benediction", "Benediction", True, 4, False,
                "Your church's default benediction. Admins can change it in Settings.", 1500),
)

SECTION_ORDER: list[str] = [spec.key for spec in SECTIONS]
SECTION_LABELS: dict[str, str] = {spec.key: spec.label for spec in SECTIONS}
SECTIONS_BY_KEY: dict[str, SectionSpec] = {spec.key: spec for spec in SECTIONS}

# The 17 (key, label) pairs of app.py:148-166, in order. One label differs
# from app.py: owner decision B renames the first reading's heading to
# "First Reading" wherever the app shows it (slice 4a plan, clarification 3).
CUSTOM_PLACEMENTS: tuple[tuple[str, str], ...] = (
    ("call_to_worship", "After Call to Worship"),
    ("opening_prayer", "After Opening Prayer"),
    ("first_hymn", "After First Hymn"),
    ("prayer_of_confession", "After Prayer of Confession"),
    ("assurance", "After Assurance of Pardon"),
    ("prayer_for_illumination", "After Prayer for Illumination"),
    ("ot_reading", "After First Reading"),
    ("nt_reading", "After New Testament Reading"),
    ("sermon", "After Sermon"),
    ("affirmation_of_faith", "After Affirmation of Faith"),
    ("second_hymn", "After Second Hymn"),
    ("communion", "After Communion"),
    ("prayers_of_the_people", "After Prayers of the People"),
    ("offertory_prayer", "After Offertory Prayer"),
    ("third_hymn", "After Third Hymn"),
    ("benediction", "Before Benediction"),
    ("end", "At the end (after Benediction)"),
)
PLACEMENT_KEYS: frozenset[str] = frozenset(key for key, _label in CUSTOM_PLACEMENTS)


def normalize_placement(key: Any) -> str:
    """A known placement key unchanged; anything else "end" (never dropped: F §4.6)."""
    return key if isinstance(key, str) and key in PLACEMENT_KEYS else "end"


OutlineKind = Literal["section", "landmark", "communion"]
ValueSource = Literal["none", "hymn_opening", "hymn_response", "hymn_closing",
                      "reading_ot", "reading_nt", "sermon_title", "fixed"]


@dataclass(frozen=True)
class OutlineItem:
    kind: OutlineKind
    key: str
    label: str                          # identical to the docx heading (5a: "First Reading")
    value_source: ValueSource
    fixed_text: Optional[str]
    anchors_after: tuple[str, ...]      # placement keys whose custom elements follow this item


COMMUNION_TITLE = "The Sacrament of the Lord's Supper"
COMMUNION_TOGGLE_LABEL = "Include communion liturgy (The Sacrament of the Lord's Supper)"


def _section(key: str) -> OutlineItem:
    return OutlineItem("section", key, SECTION_LABELS[key], "none", None, (key,))


# build_docx's emission order (worship_service.py build_docx); every placement
# key appears exactly once across anchors_after.
OUTLINE: tuple[OutlineItem, ...] = (
    _section("call_to_worship"),
    _section("opening_prayer"),
    OutlineItem("landmark", "first_hymn", "First Hymn", "hymn_opening", None, ("first_hymn",)),
    _section("prayer_of_confession"),
    _section("assurance"),
    _section("prayer_for_illumination"),
    OutlineItem("landmark", "ot_reading", "First Reading", "reading_ot", None, ("ot_reading",)),
    OutlineItem("landmark", "nt_reading", "New Testament Reading", "reading_nt", None, ("nt_reading",)),
    OutlineItem("landmark", "sermon", "Sermon Title", "sermon_title", None, ("sermon",)),
    OutlineItem("landmark", "affirmation_of_faith", "Affirmation of Faith", "fixed", "Apostles' Creed",
                ("affirmation_of_faith",)),
    OutlineItem("landmark", "second_hymn", "Second Hymn", "hymn_response", None, ("second_hymn",)),
    OutlineItem("communion", "communion", COMMUNION_TITLE, "none", None, ("communion",)),
    _section("prayers_of_the_people"),
    _section("offertory_prayer"),
    OutlineItem("landmark", "third_hymn", "Third Hymn", "hymn_closing", None, ("third_hymn", "benediction")),
    OutlineItem("section", "benediction", "Benediction", "none", None, ("end",)),
)


def outline_as_json() -> list[dict[str, Any]]:
    """OUTLINE in GET /liturgy/config's OutlineItemOut shape (shared/liturgy_outline.json)."""
    return [{"kind": item.kind, "key": item.key, "label": item.label,
             "value_source": item.value_source, "fixed_text": item.fixed_text,
             "anchors_after": list(item.anchors_after)} for item in OUTLINE]


ASSURANCE_RESPONSE = "People: Thanks be to God! Amen."      # worship_service._add_assurance_paragraph


CommunionStyle = Literal["heading1", "heading2", "text", "response", "blank"]


@dataclass(frozen=True)
class CommunionBlock:
    style: CommunionStyle     # heading1/heading2: a Heading 1/2 paragraph; response: one bold run
    text: str                 # "" for a blank paragraph


# worship_service._add_communion_liturgy's paragraphs as data, verbatim.
COMMUNION_BLOCKS: tuple[CommunionBlock, ...] = (
    CommunionBlock("heading1", COMMUNION_TITLE),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Invitation to the Table"),
    CommunionBlock("text",
                   "This is the table of our Lord Jesus Christ. It is not a reward for the righteous, "
                   "but nourishment for those who hunger; not a prize for the strong, but grace for those who are weary. "
                   "Here, blessing is not earned but received. All who seek to walk humbly with God, and who trust in God's mercy, "
                   "are welcome at this table."),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Great Thanksgiving"),
    CommunionBlock("text", "The Lord be with you."),
    CommunionBlock("response", "And also with you."),
    CommunionBlock("text", "Lift up your hearts."),
    CommunionBlock("response", "We lift them up to the Lord."),
    CommunionBlock("text", "Let us give thanks to the Lord our God."),
    CommunionBlock("response", "It is right to give our thanks and praise."),
    CommunionBlock("text",
                   "It is truly right and our greatest joy to give you thanks and praise, O God, "
                   "creator of heaven and earth, for you have made us and all things, and in your love you hold us in life. "
                   "And so we join the everlasting song:"),
    CommunionBlock("response",
                   "Holy, holy, holy Lord, God of power and might, heaven and earth are full of your glory. "
                   "Hosanna in the highest. Blessed is the one who comes in the name of the Lord. Hosanna in the highest."),
    CommunionBlock("text",
                   "You are holy, O God of majesty, and blessed is Jesus Christ, your Son, our Lord, "
                   "who by his life, death, and resurrection has reconciled the world to you. On the night in which he gave himself up "
                   "he took bread, gave thanks, broke it, and gave it to his disciples. And likewise the cup after supper. "
                   "Remembering his death and resurrection, we offer ourselves in praise and thanksgiving. Therefore we proclaim the mystery of faith:"),
    CommunionBlock("text", "Christ has died."),
    CommunionBlock("text", "Christ is risen."),
    CommunionBlock("text", "Christ will come again."),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Words of Institution"),
    CommunionBlock("text", "[Words of institution as printed or as used.]"),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "The Lord's Prayer"),
    CommunionBlock("text", "[The Lord's Prayer as printed.]"),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Breaking of the Bread and Communion"),
    CommunionBlock("text",
                   "The bread that we break is a sharing in the body of Christ. "
                   "The cup that we bless is a sharing in the blood of Christ. Come, for all is ready."),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Prayer After Communion"),
    CommunionBlock("text",
                   "Gracious God, we give you thanks that you have fed us at this table of grace, "
                   "strengthening us not to win our lives, but to live them faithfully. Send us out to do justice, "
                   "to love kindness, and to walk humbly with you, bearing your blessing into a world still hungry for hope, "
                   "through Jesus Christ our Lord. Amen."),
    CommunionBlock("blank", ""),
)

DEFAULT_BENEDICTION_FALLBACK = "Halverson"      # app.py:67 (owner decision 9: the seed)


@dataclass(frozen=True)
class Limits:
    max_section_text: int
    max_sermon_title: int
    max_custom_elements: int
    max_custom_label: int
    max_custom_text: int
    max_sections_per_request: int


LIMITS = Limits(max_section_text=20_000, max_sermon_title=300, max_custom_elements=30,
                max_custom_label=200, max_custom_text=10_000, max_sections_per_request=4)


def is_first_sunday_of_month(d: date) -> bool:
    """The communion default (app.py:969-971): a Sunday in the month's first 7 days."""
    return d.day <= 7 and d.weekday() == 6


def resolve_default_benediction(settings: Optional[Mapping[str, Any]]) -> str:
    """settings["default_benediction"] when it is a string (including "", meaning
    "no default"); anything else, or no settings, is "Halverson"."""
    value = settings.get("default_benediction") if isinstance(settings, Mapping) else None
    return value if isinstance(value, str) else DEFAULT_BENEDICTION_FALLBACK
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search, hymn_suggest, usecases.hymns; "
````

**with:**

````python
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search, hymn_suggest, usecases.hymns, "
            "liturgy_config; "
````

- [ ] **Step 5 (agent): Run the tests, the fixture regeneration and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_config.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
before=$(sha256sum backend/tests/fixtures/shared/liturgy_outline.json) && PYTHONPATH=backend .venv/bin/python backend/tests/test_liturgy_config.py && [ "$before" = "$(sha256sum backend/tests/fixtures/shared/liturgy_outline.json)" ] && echo unchanged
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `11 passed in <t>s` (8 new and the 3 import tests); `wrote <repo>/backend/tests/fixtures/shared/liturgy_outline.json` then `unchanged` (the regeneration command in the test's failure message rewrites the fixture byte for byte); `1118 passed, 11 skipped in <t>s`; then exactly ` M backend/tests/test_no_streamlit_in_core.py`, `?? backend/liturgy_config.py`, `?? backend/tests/fixtures/shared/first_sunday.json`, `?? backend/tests/fixtures/shared/liturgy_outline.json`, `?? backend/tests/fixtures/shared/liturgy_sections.json`, `?? backend/tests/test_liturgy_config.py` (and `?? .claude/`).

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/liturgy_config.py backend/tests/test_liturgy_config.py backend/tests/test_no_streamlit_in_core.py backend/tests/fixtures/shared/liturgy_sections.json backend/tests/fixtures/shared/first_sunday.json backend/tests/fixtures/shared/liturgy_outline.json
git commit -q -m "Liturgy: liturgy_config, the one home of the liturgy constants (S Backend 1)" -m "The 8 sections (switch defaults, rows, hints, token budgets), the 17
custom-element places, the order of worship as OUTLINE, the communion text
as COMMUNION_BLOCKS, the limits, the first-Sunday rule and the default
benediction resolver, with three shared fixtures for 4b. The first
reading's place reads After First Reading (owner decision B; plan
clarification 3)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 7 (controller): Review checkpoint and backup push**

Check `git show --stat HEAD` (6 files) against S Backend 1's table and OUTLINE table: row 7 "First Reading", row 15's two anchors, Prayers of the People off with 8 rows and 4 000 tokens, "Halverson". Then `git push origin claude/slice-2-plan-4q33le` (standing backup permission).

Counts after Task 1: backend **1118 passed, 11 skipped**; frontend **442 in 64**.

### Task 2: Communion from `COMMUNION_BLOCKS`, and the outline tied to the Word file (S Backend 6 `worship_service.py`, Testing "Characterization first" and "Outline matches the docx"; AC2; clarifications 4, 15)

The characterization comes first (F §2.3 step 1): `test_communion_docx.py` keeps the old `_add_communion_liturgy` verbatim and compares its output with the current one as XML, so it passes before and after the refactor; its third test, that the text now lives only in `liturgy_config`, fails until the refactor. The outline/docx test pins `OUTLINE` to `build_docx`'s heading order with one custom element per placement.

**Files:**
- Create: `backend/tests/test_communion_docx.py`
- Modify: `backend/worship_service.py` (`_add_communion_liturgy`, one import), `backend/tests/test_liturgy_config.py` (one test)

**Interfaces:**
- Consumes: `liturgy_config.COMMUNION_BLOCKS`, `OUTLINE`, `CUSTOM_PLACEMENTS`, `SECTION_ORDER` (T1); `worship_service.build_docx` (unchanged signature).
- Produces: `worship_service._add_communion_liturgy(doc)` rendering `COMMUNION_BLOCKS` (heading1 → Heading 1, heading2 → Heading 2, response → one bold run, text → a paragraph, blank → an empty paragraph); `test_liturgy_config.DOCX_HEADINGS_UNTIL_5A` (5a deletes it).

- [ ] **Step 1 (agent): Write the characterization and the tie tests**

**Create `backend/tests/test_communion_docx.py`:**

````python
"""The communion liturgy in the Word file comes from liturgy_config.COMMUNION_BLOCKS
and prints exactly as before (slice 4 spec, Backend 6 `worship_service.py`;
Testing "Characterization first"; AC2). _legacy_communion is a verbatim copy
of worship_service._add_communion_liturgy as it was before slice 4a: the
characterization the refactor must keep, compared as XML in the same run, so
the python-docx version cannot matter."""
from pathlib import Path

from docx import Document

import liturgy_config
import worship_service


def _legacy_communion(doc) -> None:
    """Add The Sacrament of the Lord's Supper liturgy (invitation, great thanksgiving, etc.)."""
    doc.add_paragraph("The Sacrament of the Lord's Supper", style="Heading 1")
    doc.add_paragraph()

    doc.add_paragraph("Invitation to the Table", style="Heading 2")
    doc.add_paragraph(
        "This is the table of our Lord Jesus Christ. It is not a reward for the righteous, "
        "but nourishment for those who hunger; not a prize for the strong, but grace for those who are weary. "
        "Here, blessing is not earned but received. All who seek to walk humbly with God, and who trust in God's mercy, "
        "are welcome at this table."
    )
    doc.add_paragraph()

    doc.add_paragraph("Great Thanksgiving", style="Heading 2")
    doc.add_paragraph("The Lord be with you.")
    p = doc.add_paragraph()
    p.add_run("And also with you.").bold = True
    doc.add_paragraph("Lift up your hearts.")
    p = doc.add_paragraph()
    p.add_run("We lift them up to the Lord.").bold = True
    doc.add_paragraph("Let us give thanks to the Lord our God.")
    p = doc.add_paragraph()
    p.add_run("It is right to give our thanks and praise.").bold = True
    doc.add_paragraph(
        "It is truly right and our greatest joy to give you thanks and praise, O God, "
        "creator of heaven and earth, for you have made us and all things, and in your love you hold us in life. "
        "And so we join the everlasting song:"
    )
    p = doc.add_paragraph()
    p.add_run(
        "Holy, holy, holy Lord, God of power and might, heaven and earth are full of your glory. "
        "Hosanna in the highest. Blessed is the one who comes in the name of the Lord. Hosanna in the highest."
    ).bold = True
    doc.add_paragraph(
        "You are holy, O God of majesty, and blessed is Jesus Christ, your Son, our Lord, "
        "who by his life, death, and resurrection has reconciled the world to you. On the night in which he gave himself up "
        "he took bread, gave thanks, broke it, and gave it to his disciples. And likewise the cup after supper. "
        "Remembering his death and resurrection, we offer ourselves in praise and thanksgiving. Therefore we proclaim the mystery of faith:"
    )
    doc.add_paragraph("Christ has died.")
    doc.add_paragraph("Christ is risen.")
    doc.add_paragraph("Christ will come again.")
    doc.add_paragraph()

    doc.add_paragraph("Words of Institution", style="Heading 2")
    doc.add_paragraph("[Words of institution as printed or as used.]")
    doc.add_paragraph()

    doc.add_paragraph("The Lord's Prayer", style="Heading 2")
    doc.add_paragraph("[The Lord's Prayer as printed.]")
    doc.add_paragraph()

    doc.add_paragraph("Breaking of the Bread and Communion", style="Heading 2")
    doc.add_paragraph(
        "The bread that we break is a sharing in the body of Christ. "
        "The cup that we bless is a sharing in the blood of Christ. Come, for all is ready."
    )
    doc.add_paragraph()

    doc.add_paragraph("Prayer After Communion", style="Heading 2")
    doc.add_paragraph(
        "Gracious God, we give you thanks that you have fed us at this table of grace, "
        "strengthening us not to win our lives, but to live them faithfully. Send us out to do justice, "
        "to love kindness, and to walk humbly with you, bearing your blessing into a world still hungry for hope, "
        "through Jesus Christ our Lord. Amen."
    )
    doc.add_paragraph()


def _service(**overrides):
    return worship_service.build_docx(
        occasion="World Communion Sunday", date="October 4, 2026",
        scriptures=["Isaiah 5:1-7", "Matthew 21:33-46"],
        hymns=[{"title": "Be Thou My Vision", "number": 450}, {"title": "Come, Thou Fount", "number": 475}],
        liturgy={"prayers_of_the_people": "We pray.", "benediction": "Go in peace."},
        include_communion=True, **overrides)


def _paragraphs(buf) -> list[tuple[str, str, list[tuple[str, bool]]]]:
    return [(p.style.name, p.text, [(r.text, bool(r.bold)) for r in p.runs])
            for p in Document(buf).paragraphs]


def test_the_word_file_with_communion_is_unchanged(monkeypatch):
    current = Document(_service()).element.body.xml
    monkeypatch.setattr(worship_service, "_add_communion_liturgy", _legacy_communion)
    legacy = Document(_service()).element.body.xml
    assert current == legacy
    paragraphs = _paragraphs(_service())
    assert ("Heading 1", "The Sacrament of the Lord's Supper",
            [("The Sacrament of the Lord's Supper", False)]) in paragraphs
    assert ("Normal", "And also with you.", [("And also with you.", True)]) in paragraphs


def test_communion_blocks_render_as_the_legacy_paragraphs():
    legacy, current = Document(), Document()
    _legacy_communion(legacy)
    worship_service._add_communion_liturgy(current)
    assert current.element.body.xml == legacy.element.body.xml
    styles = {"heading1": "Heading 1", "heading2": "Heading 2", "text": "Normal",
              "response": "Normal", "blank": "Normal"}
    assert [(p.style.name, p.text, any(r.bold for r in p.runs)) for p in current.paragraphs] == [
        (styles[b.style], b.text, b.style == "response") for b in liturgy_config.COMMUNION_BLOCKS]


def test_the_communion_text_lives_in_liturgy_config():
    source = Path(worship_service.__file__).read_text(encoding="utf-8")
    assert "Invitation to the Table" not in source and "Christ will come again." not in source
    assert "COMMUNION_BLOCKS" in source
````

**In `backend/tests/test_liturgy_config.py`, replace:**

````python
if __name__ == "__main__":
    write_outline_fixture()
````

**with:**

````python
# The docx still prints "Old Testament Reading" until 5a renames it to OUTLINE's
# "First Reading" (owner decision B; slice 4a plan, clarification 4). 5a deletes
# this map when it changes build_docx.
DOCX_HEADINGS_UNTIL_5A = {"ot_reading": "Old Testament Reading"}


def test_the_outline_is_build_docx_s_heading_order():
    from docx import Document

    import worship_service

    buf = worship_service.build_docx(
        occasion="World Communion Sunday", date="October 4, 2026",
        scriptures=["Isaiah 5:1-7", "Matthew 21:33-46"],
        hymns=[{"title": f"Hymn {n}", "number": n} for n in (1, 2, 3)],
        liturgy={key: f"Text of {key}." for key in lc.SECTION_ORDER},
        sermon_title="Living Water", selected_ot_ref="Isaiah 5:1-7", selected_nt_ref="Matthew 21:33-46",
        include_sermon=True, include_prayers_of_the_people=True, include_communion=True,
        custom_elements=[{"label": f"CE:{key}", "text": "", "insert_after": key}
                         for key, _label in lc.CUSTOM_PLACEMENTS])
    communion_inside = {b.text for b in lc.COMMUNION_BLOCKS if b.style == "heading2"}
    printed = [p.text for p in Document(buf).paragraphs
               if p.style.name in ("Heading 1", "Heading 2") and p.text not in communion_inside]
    expected = []
    for item in lc.OUTLINE:
        expected.append(DOCX_HEADINGS_UNTIL_5A.get(item.key, item.label))
        expected.extend(f"CE:{anchor}" for anchor in item.anchors_after)
    assert printed == expected, (
        "OUTLINE and build_docx disagree: change both in one PR and regenerate "
        f"shared/liturgy_outline.json ({REGENERATE})")


if __name__ == "__main__":
    write_outline_fixture()
````

- [ ] **Step 2 (agent): Run them: the characterization and the tie pass, the new home fails**

```bash
.venv/bin/python -m pytest -q backend/tests/test_communion_docx.py backend/tests/test_liturgy_config.py 2>&1 | tail -3
```

**Expected:**

```
FAILED backend/tests/test_communion_docx.py::test_the_communion_text_lives_in_liturgy_config
1 failed, 11 passed in <t>s
```

The two characterization tests pass on the old helper (they pin today's Word file), and so does the outline/docx tie.

- [ ] **Step 3 (agent): Print communion from `COMMUNION_BLOCKS`**

**In `backend/worship_service.py`, replace:**

````python
import liturgy_prompts
import service_rubric
````

**with:**

````python
import liturgy_prompts
import service_rubric
from liturgy_config import COMMUNION_BLOCKS
````

**In `backend/worship_service.py`, replace from the line starting `def _add_communion_liturgy(doc) -> None:` up to (not including) the line starting `def _add_assurance_paragraph` with:**

````python
def _add_communion_liturgy(doc) -> None:
    """Add The Sacrament of the Lord's Supper liturgy: liturgy_config.COMMUNION_BLOCKS
    (the one copy of the text, which GET /liturgy/config also serves), one paragraph each."""
    for block in COMMUNION_BLOCKS:
        if block.style == "heading1":
            doc.add_paragraph(block.text, style="Heading 1")
        elif block.style == "heading2":
            doc.add_paragraph(block.text, style="Heading 2")
        elif block.style == "response":
            doc.add_paragraph().add_run(block.text).bold = True
        elif block.style == "text":
            doc.add_paragraph(block.text)
        else:                               # blank
            doc.add_paragraph()


````

- [ ] **Step 4 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_communion_docx.py backend/tests/test_liturgy_config.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `12 passed in <t>s`; `1122 passed, 11 skipped in <t>s`; then exactly ` M backend/tests/test_liturgy_config.py`, ` M backend/worship_service.py`, `?? backend/tests/test_communion_docx.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/worship_service.py backend/tests/test_communion_docx.py backend/tests/test_liturgy_config.py
git commit -q -m "Word file: communion from COMMUNION_BLOCKS, outline tied to build_docx (S Backend 6, AC2)" -m "The communion liturgy prints from liturgy_config.COMMUNION_BLOCKS; a
verbatim copy of the old helper in the test proves the Word file is
unchanged, compared as XML in the same run. A second test pins OUTLINE to
build_docx's heading order, reading its Old Testament Reading as First
Reading until 5a renames that heading (plan clarification 4)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

`git show HEAD -- backend/worship_service.py`: the old paragraphs are gone and nothing else in `build_docx` changed. Push the backup.

Counts after Task 2: backend **1122 passed, 11 skipped**; frontend **442 in 64**.

### Task 3: The template validator (S Backend 2 "Validator", Testing `test_liturgy_prompts.py`; AC6; clarifications 6, 10, 11)

`liturgy_prompts` takes `SECTION_ORDER` and `SECTION_LABELS` from `liturgy_config` (the names stay for frozen Streamlit's Settings page), ignores stored values that are not strings, and gains the checks 6a reuses: `check_template` (S's table, first failure), `template_error`, `validate_prompts` (Risk 3's check) and `clean_prompt_overrides` (the one rule for "equal to the default", with CRLF read as LF).

**Files:**
- Modify: `backend/liturgy_prompts.py`, `backend/tests/test_liturgy_prompts.py`

**Interfaces:**
- Consumes: `liturgy_config.SECTION_ORDER`, `SECTION_LABELS` (T1); `liturgy_prompts._SafeDict`, `default_prompts`, `PROMPT_KEYS` (existing).
- Produces (later users: T5, T13 Step 10, 6a):
  - `KNOWN_PLACEHOLDERS = ("occasion", "scriptures", "opening_hymn", "hymns")`, `MAX_TEMPLATE_CHARS = 8000`, `MAX_PROMPT_CHARS = 24_000`, the reason constants (`TOO_LONG_TEMPLATE`, `UNPAIRED_BRACE`, `NO_NAME`, `NOT_PLAIN_NAME`, `NOT_ONE_WORD`, `HAS_SPEC`, `CANT_FILL`)
  - `TemplateCheck(ok, message, unknown_placeholders)`; `check_template(key, template) -> TemplateCheck`; `template_error(template) -> str | None`; `validate_prompts(prompts) -> dict[str, str]`; `clean_prompt_overrides(prompts, defaults=None) -> dict[str, str]`

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_liturgy_prompts.py`:**

````python


# --- slice 4a: the template validator (slice 4 spec, Backend 2; Testing; AC6) ---

import liturgy_config

BRACE = "It has a { or } without a partner. Use {{ or }} to print a brace."
ONE_WORD = ("Placeholders must be a single word such as {occasion}. "
            "To print a { or } as text, write {{ or }}.")
MALFORMED = [
    (["{", "}", "{a!}", "{a[}"], BRACE),
    (["{}", "{0}"], "Placeholders need a name, such as {occasion}."),
    (["{a.b}", "{a[0]}", "{a[x]}", "{occasion.upper}"],
     "Placeholders must be a plain name such as {occasion}, with no dots or brackets."),
    (['{"a": 1}', '{"title"}', "{ occasion }", "{a b}"], ONE_WORD),
    (["{a!r}", "{a:d}", "{occasion:>10}"], "Placeholders can't include ! or :. Write just {occasion}."),
    (["x" * 8001], "This prompt is too long (max 8,000 characters)."),
]


def test_check_template_rejects_each_malformed_case_with_its_message():
    for templates, message in MALFORMED:
        for template in templates:
            check = lp.check_template("benediction", template)
            assert (check.ok, check.message, check.unknown_placeholders) == (False, message, ()), template
            assert lp.template_error(template) == message, template


def test_defaults_literal_braces_unknown_placeholders_and_the_system_prompt_pass():
    for key, template in lp.default_prompts().items():
        assert lp.check_template(key, template) == lp.TemplateCheck(True, None, ()), key
        if key != "system":
            assert lp.template_error(template) is None, key
    assert lp.check_template("call_to_worship", "Hi {ocassion} and {occasion} {ocassion}") == \
        lp.TemplateCheck(True, None, ("ocassion",))
    assert lp.check_template("call_to_worship", "{{literal}}").ok
    assert lp.check_template("system", 'Answer as JSON: {"a": 1} {').ok        # never formatted
    assert lp.check_template("system", "x" * 8001).message == "This prompt is too long (max 8,000 characters)."
    assert lp.check_template("call_to_worship", "x" * 8000).ok
    assert "no more than 3 sentences" in lp.DEFAULT_SECTION_PROMPTS["prayer_for_illumination"]
    assert "No more than three sentences" in lp.DEFAULT_SECTION_PROMPTS["offertory_prayer"]


def test_validate_prompts_reports_only_what_merge_prompts_would_use():
    assert lp.validate_prompts({"bogus": "x", "benediction": "{", "system": "{"}) == {"benediction": BRACE}
    assert lp.validate_prompts({"benediction": "   ", "opening_prayer": 5, "assurance": None}) == {}
    assert lp.validate_prompts({"call_to_worship": '{"a": 1}', "offertory_prayer": "{0}"}) == {
        "call_to_worship": ONE_WORD, "offertory_prayer": "Placeholders need a name, such as {occasion}."}
    assert lp.validate_prompts("not a mapping") == {}


def test_clean_prompt_overrides_drops_defaults_blanks_and_unknown_keys():
    """Ports streamlit_tests/test_settings_prompts_translation.py
    test_admin_prompt_save_drops_defaults_and_reset_clears."""
    submitted = {
        "system": lp.DEFAULT_SYSTEM_PROMPT,              # unchanged -> not stored
        "benediction": "  Go in peace, friends.  ",      # changed -> stored, stripped
        "opening_prayer": "   ",                         # blank -> not stored
        "bogus": "x",                                    # unknown key -> not stored
        "assurance": None,
    }
    assert lp.clean_prompt_overrides(submitted) == {"benediction": "Go in peace, friends."}
    defaults = {"benediction": "Go in peace, friends."}
    assert lp.clean_prompt_overrides(submitted, defaults) == {"system": lp.DEFAULT_SYSTEM_PROMPT}
    assert lp.clean_prompt_overrides({}) == {}


def test_clean_prompt_overrides_reads_crlf_as_lf():
    default = lp.DEFAULT_SECTION_PROMPTS["benediction"]
    assert lp.clean_prompt_overrides({"benediction": "Line one.\r\nLine two.\r\n"}) == {
        "benediction": "Line one.\nLine two."}
    multi = {"benediction": "Bless us.\nKeep us."}
    assert lp.clean_prompt_overrides({"benediction": "Bless us.\r\nKeep us."}, multi) == {}
    assert lp.clean_prompt_overrides({"benediction": "Bless us.\nKeep us."},
                                     {"benediction": "Bless us.\r\nKeep us."}) == {}
    assert lp.clean_prompt_overrides({"benediction": default.replace(". ", ".\r\n")}) != {}
    assert lp.clean_prompt_overrides({"benediction": default + "\r\n"}) == {}


def test_section_order_and_labels_come_from_liturgy_config():
    assert lp.SECTION_ORDER is liturgy_config.SECTION_ORDER
    assert lp.SECTION_LABELS is liturgy_config.SECTION_LABELS
    assert lp.PROMPT_KEYS == ["system"] + liturgy_config.SECTION_ORDER


def test_merge_prompts_ignores_values_that_are_not_strings():
    merged = lp.merge_prompts({"benediction": 5, "system": ["x"], "assurance": "Mine."})
    assert merged["benediction"] == lp.DEFAULT_SECTION_PROMPTS["benediction"]
    assert merged["system"] == lp.DEFAULT_SYSTEM_PROMPT
    assert merged["assurance"] == "Mine."
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_prompts.py 2>&1 | tail -9
```

**Expected:**

```
FAILED backend/tests/test_liturgy_prompts.py::test_check_template_rejects_each_malformed_case_with_its_message
FAILED backend/tests/test_liturgy_prompts.py::test_defaults_literal_braces_unknown_placeholders_and_the_system_prompt_pass
FAILED backend/tests/test_liturgy_prompts.py::test_validate_prompts_reports_only_what_merge_prompts_would_use
FAILED backend/tests/test_liturgy_prompts.py::test_clean_prompt_overrides_drops_defaults_blanks_and_unknown_keys
FAILED backend/tests/test_liturgy_prompts.py::test_clean_prompt_overrides_reads_crlf_as_lf
FAILED backend/tests/test_liturgy_prompts.py::test_section_order_and_labels_come_from_liturgy_config
FAILED backend/tests/test_liturgy_prompts.py::test_merge_prompts_ignores_values_that_are_not_strings
7 failed, 7 passed in <t>s
```

(`AttributeError`s for the new names; the section-order test fails on `is`; the last on `AttributeError: 'int' object has no attribute 'strip'`.)

- [ ] **Step 3 (agent): Add the validator**

**In `backend/liturgy_prompts.py`, replace from the line starting `from typing import Dict, List` up to (not including) the line starting `PLACEHOLDER_HELP = (` with:**

````python
import string
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# The one home of the section order and labels is liturgy_config (slice 4); the
# names stay here for frozen Streamlit's Settings page and the tests.
from liturgy_config import SECTION_LABELS, SECTION_ORDER  # noqa: F401 (re-exported)

````

**In `backend/liturgy_prompts.py`, replace:**

````python
def merge_prompts(overrides: Dict[str, str] | None) -> Dict[str, str]:
    """Defaults with any non-blank per-key overrides applied. Ignores unknown keys."""
    prompts = default_prompts()
    for key in PROMPT_KEYS:
        value = (overrides or {}).get(key)
        if value and value.strip():
            prompts[key] = value
    return prompts
````

**with:**

````python
def merge_prompts(overrides: Dict[str, str] | None) -> Dict[str, str]:
    """Defaults with any non-blank per-key overrides applied. Ignores unknown keys,
    and values that are not strings (settings is JSON anyone could have written)."""
    prompts = default_prompts()
    for key in PROMPT_KEYS:
        value = (overrides or {}).get(key)
        if isinstance(value, str) and value.strip():
            prompts[key] = value
    return prompts
````

**Append to `backend/liturgy_prompts.py`:**

````python


# --- slice 4a: the template validator (slice 4 spec, Backend 2; reused by 6a) ---

KNOWN_PLACEHOLDERS = ("occasion", "scriptures", "opening_hymn", "hymns")
MAX_TEMPLATE_CHARS = 8000
MAX_PROMPT_CHARS = 24_000         # system + user, the cost guard (F §2.8)

TOO_LONG_TEMPLATE = "This prompt is too long (max 8,000 characters)."
UNPAIRED_BRACE = "It has a { or } without a partner. Use {{ or }} to print a brace."
NO_NAME = "Placeholders need a name, such as {occasion}."
NOT_PLAIN_NAME = "Placeholders must be a plain name such as {occasion}, with no dots or brackets."
NOT_ONE_WORD = ("Placeholders must be a single word such as {occasion}. "
                "To print a { or } as text, write {{ or }}.")
HAS_SPEC = "Placeholders can't include ! or :. Write just {occasion}."
CANT_FILL = "It can't be filled in. Check the { } placeholders."


@dataclass(frozen=True)
class TemplateCheck:
    ok: bool
    message: Optional[str]                      # user-facing reason when not ok
    unknown_placeholders: tuple[str, ...]       # render as blank; 6a may show them as warnings


def _failed(message: str) -> TemplateCheck:
    return TemplateCheck(False, message, ())


def check_template(key: str, template: str) -> TemplateCheck:
    """The first failing check, in the spec's order, or ok with the unknown
    placeholders. The system prompt is sent as written, never formatted, so
    only its length is checked. Never raises."""
    if not isinstance(template, str):
        return _failed(CANT_FILL)
    if len(template) > MAX_TEMPLATE_CHARS:
        return _failed(TOO_LONG_TEMPLATE)
    if key == "system":
        return TemplateCheck(True, None, ())
    try:
        parsed = list(string.Formatter().parse(template))
    except ValueError:
        return _failed(UNPAIRED_BRACE)
    fields = [(name, spec, conversion) for _text, name, spec, conversion in parsed if name is not None]
    checks = (
        (lambda name, spec, conv: name == "" or name.isdigit(), NO_NAME),
        (lambda name, spec, conv: "." in name or "[" in name, NOT_PLAIN_NAME),
        (lambda name, spec, conv: not name.isidentifier(), NOT_ONE_WORD),
        (lambda name, spec, conv: conv is not None or bool(spec), HAS_SPEC),
    )
    for fails, message in checks:
        if any(fails(*field) for field in fields):
            return _failed(message)
    try:
        template.format_map(_SafeDict({name: "sample" for name in KNOWN_PLACEHOLDERS}))
    except Exception:                                    # inv §0 item 4: never crash here
        return _failed(CANT_FILL)
    unknown = tuple(dict.fromkeys(name for name, _spec, _conv in fields if name not in KNOWN_PLACEHOLDERS))
    return TemplateCheck(True, None, unknown)


def template_error(template: str) -> Optional[str]:
    """The section-template check 6a calls: the reason, or None. Any section key
    gives the same result; only "system" is special. Never raises."""
    return check_template("call_to_worship", template).message


def validate_prompts(prompts: Mapping[str, Any]) -> dict[str, str]:
    """key -> reason for each stored override merge_prompts would use (a
    non-blank string under a PROMPT_KEYS key) that fails check_template.
    Other keys and values are skipped: merge_prompts ignores them."""
    if not isinstance(prompts, Mapping):
        return {}
    failures = {}
    for key in PROMPT_KEYS:
        value = prompts.get(key)
        if isinstance(value, str) and value.strip():
            message = check_template(key, value).message
            if message is not None:
                failures[key] = message
    return failures


def _normalized(value: Any) -> str:
    return value.replace("\r\n", "\n").strip() if isinstance(value, str) else ""


def clean_prompt_overrides(prompts: Mapping[str, Any],
                           defaults: Optional[Mapping[str, Any]] = None) -> dict[str, str]:
    """The overrides worth storing (streamlit_views/settings.py submit_prompts,
    plus one rule): each value and default has its CRLF line endings read as LF
    (browser textareas submit CRLF) and is stripped; a PROMPT_KEYS value that is
    then non-blank and differs from its default is kept, stored normalized.
    defaults=None means default_prompts(). The one rule for "equal to the
    default": 6a's PUT imports it and has no second copy."""
    defaults = default_prompts() if defaults is None else defaults
    cleaned = {}
    for key, value in (prompts or {}).items():
        if key not in PROMPT_KEYS:
            continue
        text = _normalized(value)
        if text and text != _normalized(defaults.get(key)):
            cleaned[key] = text
    return cleaned
````

- [ ] **Step 4 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_prompts.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `14 passed in <t>s`; `1129 passed, 11 skipped in <t>s`; then exactly ` M backend/liturgy_prompts.py`, ` M backend/tests/test_liturgy_prompts.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/liturgy_prompts.py backend/tests/test_liturgy_prompts.py
git commit -q -m "Liturgy prompts: the template validator 6a reuses (S Backend 2, AC6)" -m "check_template runs S's checks in order (length; system never formatted;
unpaired braces; nameless, dotted and non-word placeholders; ! and :; a
test render) and reports unknown placeholders. template_error,
validate_prompts (only what merge_prompts would use) and
clean_prompt_overrides (CRLF read as LF) are 6a's. SECTION_ORDER and
SECTION_LABELS now come from liturgy_config, and merge_prompts ignores
stored values that are not strings (plan clarification 10)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint (end of batch A) and backup push**

Review T1-T3 together: every reason string equals S Backend 2's table character for character; `validate_prompts({"bogus": "x", "benediction": "{", "system": "{"})` is `{"benediction": <brace message>}`; frozen Streamlit's Settings names (`SECTION_ORDER`, `SECTION_LABELS`, `PROMPT_KEYS`, `PLACEHOLDER_HELP`, `default_prompts`) are all still there. Push the backup.

Counts after Task 3: backend **1129 passed, 11 skipped**; frontend **442 in 64**.

### Task 4: `prayer_library.py`, the library's one reader (S Interfaces 6a "Prayer library read path"; prayer library spec §Data, §Writer hook; Testing `test_prayer_library.py`; clarification 13)

A pure module: the library's types and limits (6a imports them), `read_library(settings)` (never raises; junk reads as empty) and `choose_example(library, section, *, choose)` (a random same-type prayer, cut to 3 000; never an `"other"` prayer). Slice 4a only reads the library; nothing writes it until 6a, so every church reads as empty in production.

**Files:**
- Create: `backend/prayer_library.py`, `backend/tests/test_prayer_library.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes: `liturgy_config.SECTION_ORDER` (T1).
- Produces (later users: T5, T7, 6a): `PRAYER_TYPES` (the 8 section keys and `"other"`), `MAX_PRAYERS = 30`, `MAX_PRAYER_CHARS = 6_000`, `MAX_PROFILE_CHARS = 2_000`, `MAX_EXAMPLE_CHARS = 3_000`; `Prayer(id, type, text, added_at)`, `PrayerLibrary(prayers: tuple[Prayer, ...], voice_profile: str)`, `EMPTY_LIBRARY`; `read_library(settings) -> PrayerLibrary`; `choose_example(library, section, *, choose=random.choice) -> str | None`.

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_prayer_library.py`:**

````python
"""prayer_library: the reader and the example chooser (prayer library spec
§Data, §Writer hook; slice 4 spec, Testing `test_prayer_library.py`)."""
import prayer_library as pl


def _settings(library):
    return {"prayer_library": library}


CONFESSION_A = {"id": "p1", "type": "prayer_of_confession", "text": "Merciful God, {we} confess.",
                "added_at": "2026-09-26T15:00:00Z"}
CONFESSION_B = {"id": "p2", "type": "prayer_of_confession", "text": "Holy One, we have wandered.",
                "added_at": "2026-09-27T15:00:00Z"}
OTHER = {"id": "p3", "type": "other", "text": "A wedding prayer.", "added_at": "2026-09-27T16:00:00Z"}


def test_a_missing_key_or_junk_reads_as_the_empty_library():
    for settings in (None, {}, "junk", _settings(None), _settings([]), _settings("x"),
                     _settings({"prayers": "x"}), _settings({"prayers": [{"type": 5}]}),
                     _settings({"prayers": [{"type": "benediction"}], "voice_profile": 7})):
        assert pl.read_library(settings) == pl.EMPTY_LIBRARY, settings


def test_prayers_and_the_profile_are_read_and_bad_entries_skipped():
    library = pl.read_library(_settings({
        "prayers": [CONFESSION_A, "junk", {"type": "sermon", "text": "x"}, {"type": "benediction", "text": 3},
                    {"type": "benediction", "text": "Go."}],
        "voice_profile": "Warm and plain.",
    }))
    assert library.voice_profile == "Warm and plain."
    assert library.prayers == (
        pl.Prayer("p1", "prayer_of_confession", "Merciful God, {we} confess.", "2026-09-26T15:00:00Z"),
        pl.Prayer("", "benediction", "Go.", ""),
    )


def test_choose_example_uses_the_chooser_over_that_type_only():
    library = pl.read_library(_settings({"prayers": [CONFESSION_A, OTHER, CONFESSION_B]}))
    seen = []

    def last(texts):
        seen.append(list(texts))
        return texts[-1]

    assert pl.choose_example(library, "prayer_of_confession", choose=last) == "Holy One, we have wandered."
    assert seen == [["Merciful God, {we} confess.", "Holy One, we have wandered."]]
    assert pl.choose_example(library, "prayer_of_confession", choose=lambda texts: texts[0]) == \
        "Merciful God, {we} confess."


def test_no_example_without_that_type_and_never_an_other_prayer():
    library = pl.read_library(_settings({"prayers": [OTHER, {"type": "benediction", "text": "   "}]}))
    assert pl.choose_example(library, "benediction") is None           # blank text is no example
    assert pl.choose_example(library, "call_to_worship") is None
    assert pl.choose_example(library, "other") is None
    assert pl.choose_example(pl.EMPTY_LIBRARY, "benediction") is None


def test_limits_types_and_the_example_cut():
    assert pl.PRAYER_TYPES[-1] == "other" and len(pl.PRAYER_TYPES) == 9
    assert (pl.MAX_PRAYERS, pl.MAX_PRAYER_CHARS, pl.MAX_PROFILE_CHARS, pl.MAX_EXAMPLE_CHARS) == (
        30, 6_000, 2_000, 3_000)
    library = pl.read_library(_settings({"prayers": [{"type": "benediction", "text": "x" * 4000}]}))
    assert pl.choose_example(library, "benediction") == "x" * 3000
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_prayer_library.py 2>&1 | tail -3
```

**Expected:** a collection error, `ModuleNotFoundError: No module named 'prayer_library'` (`1 error in <t>s`).

- [ ] **Step 3 (agent): Add the module**

**Create `backend/prayer_library.py`:**

````python
"""The prayer library's reader and example chooser (prayer library spec
2026-09-26 §Data and §Writer hook; slice 4 spec, Interfaces 6a).

The library is churches.settings["prayer_library"]:
{"prayers": [{"id", "type", "text", "added_at"}], "voice_profile": str}.
Slice 4a only reads it (the liturgy writer's voice hook); 6a's Prayers page
writes it and imports these limits and this reader, so there is one reader.

- read_library(settings): a missing key or a value of the wrong shape reads
  as the empty library; a prayer entry of the wrong shape is skipped. Never
  raises.
- choose_example(library, section, *, choose): one uniformly random prayer
  of that section's type, cut to MAX_EXAMPLE_CHARS, or None. An "other"
  prayer is never an example.

Pure: no FastAPI, no database (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

from liturgy_config import SECTION_ORDER

PRAYER_TYPES: tuple[str, ...] = (*SECTION_ORDER, "other")
MAX_PRAYERS = 30
MAX_PRAYER_CHARS = 6_000
MAX_PROFILE_CHARS = 2_000
MAX_EXAMPLE_CHARS = 3_000       # the writer's cut (prayer library spec, Writer hook "Budget")


@dataclass(frozen=True)
class Prayer:
    id: str
    type: str          # a SectionKey or "other"
    text: str
    added_at: str


@dataclass(frozen=True)
class PrayerLibrary:
    prayers: tuple[Prayer, ...]
    voice_profile: str


EMPTY_LIBRARY = PrayerLibrary(prayers=(), voice_profile="")


def _prayer(entry: Any) -> Optional[Prayer]:
    if not isinstance(entry, Mapping):
        return None
    kind, text = entry.get("type"), entry.get("text")
    if kind not in PRAYER_TYPES or not isinstance(text, str):
        return None
    ident, added = entry.get("id"), entry.get("added_at")
    return Prayer(id=ident if isinstance(ident, str) else "", type=kind, text=text,
                  added_at=added if isinstance(added, str) else "")


def read_library(settings: Any) -> PrayerLibrary:
    """The church's library from its settings; the empty library when it is
    missing or of the wrong shape. Never raises."""
    stored = settings.get("prayer_library") if isinstance(settings, Mapping) else None
    if not isinstance(stored, Mapping):
        return EMPTY_LIBRARY
    entries = stored.get("prayers", [])
    if not isinstance(entries, list):
        return EMPTY_LIBRARY
    profile = stored.get("voice_profile", "")
    prayers = tuple(p for p in (_prayer(entry) for entry in entries) if p is not None)
    return PrayerLibrary(prayers=prayers, voice_profile=profile if isinstance(profile, str) else "")


def choose_example(library: PrayerLibrary, section: str, *,
                   choose: Callable[[Sequence[str]], str] = random.choice) -> Optional[str]:
    """A random prayer whose type is `section` (never "other"), cut to
    MAX_EXAMPLE_CHARS; None when the library has none of that type."""
    if section == "other":
        return None
    texts = [p.text for p in library.prayers if p.type == section and p.text.strip()]
    if not texts:
        return None
    return choose(texts)[:MAX_EXAMPLE_CHARS]
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "liturgy_config; "
````

**with:**

````python
            "liturgy_config, prayer_library; "
````

- [ ] **Step 4 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_prayer_library.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `8 passed in <t>s`; `1134 passed, 11 skipped in <t>s`; then exactly ` M backend/tests/test_no_streamlit_in_core.py`, `?? backend/prayer_library.py`, `?? backend/tests/test_prayer_library.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/prayer_library.py backend/tests/test_prayer_library.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Prayer library: the reader and the example chooser (S Interfaces 6a; PR #7 spec)" -m "read_library reads churches.settings[\"prayer_library\"] and never raises:
a value of the wrong shape is the empty library and a bad prayer entry is
skipped. choose_example picks a random prayer of the section's type, cut
to 3 000 characters, never an \"other\" prayer. 6a imports the limits and
this reader; nothing writes the library until then." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

Check the limits against the prayer library spec §Data and the junk cases against S Testing `test_prayer_library.py`. Push the backup.

Counts after Task 4: backend **1134 passed, 11 skipped**; frontend **442 in 64**.

### Task 5: The prompt builder, pinned against `generate_liturgy` (S Backend 2 "Prompt building" and its 2026-09-26 amendment; Testing "Characterization first", `test_liturgy_generation.py`, `test_liturgy_prompts.py` additions; AC3, AC19, AC21; BC-8; clarifications 6, 8, 9, 21)

`liturgy_prompts` gains the builder: `sermon_text_block` (moved from `worship_service`, same wording), `ResolvedHymn`, `PromptContext`, `build_context` (the scripture and hymn lines, the opening slot's title, the merged rubric's checklists, the sermon block), `VoiceContext`, `PromptInvalid`, `BuiltPrompt`, `build_prompt` and `build_messages`. `test_liturgy_generation.py` pins the old behavior, including an oracle test that compares every section's messages with what `worship_service.generate_liturgy` sends for the same one-line inputs (T10 removes it with the function), plus the two intentional changes (BC-8), which fail on the old function's behavior. `service_rubric` stops importing from `liturgy_prompts` (clarification 6).

**Files:**
- Create: `backend/tests/test_liturgy_generation.py`
- Modify: `backend/liturgy_prompts.py`, `backend/service_rubric.py`, `backend/tests/test_liturgy_prompts.py`, `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes: `service_rubric.merge_rubric`, `format_checklist` (PR #4); `prayer_library.MAX_PROFILE_CHARS`, `MAX_EXAMPLE_CHARS` (T4); `check_template`, `render`, `MAX_PROMPT_CHARS`, `CANT_FILL` (T3).
- Produces (later users: T7, T10, the reviewer add-on, 6a):
  - `SERMON_TEXT_LIMIT = 2000`, `sermon_text_block(ref, text) -> str`
  - `ResolvedHymn(title: str, number: int | None)`; `HYMN_SLOTS = ("opening", "response", "closing")`
  - `PromptContext(occasion, scriptures, opening_hymn, hymns, checklists={}, sermon="")`
  - `build_context(*, occasion, scriptures, hymns_by_slot, rubric=None, sermon_ref=None, sermon_text=None) -> PromptContext`
  - `VoiceContext(profile: str, example: str | None)`; `PromptInvalid(section, reason)` (`.section`, `.reason`); `TOO_LONG_WITH_ADDITIONS`
  - `BuiltPrompt(messages, dropped)`; `build_prompt(section, prompts, ctx, *, voice=None) -> BuiltPrompt`; `build_messages(section, prompts, ctx, *, voice=None) -> list[dict]`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_liturgy_generation.py`:**

````python
"""The liturgy prompts, pinned before worship_service.generate_liturgy goes
(slice 4 spec, Testing "Characterization first" `test_liturgy_generation.py`;
AC3, AC19). The system message is compared with the merged system prompt,
never quoted (the reviewer add-on changes the default's season sentences;
S "Tests before and after")."""
from types import SimpleNamespace

import liturgy_prompts as lp
from service_rubric import default_rubric

OCCASION = "Third Sunday of Easter"
SCRIPTURES = ["Acts 9:1-6", "Psalm 30", "Revelation 5:11-14", "John 21:1-19"]
SLOTS = {"opening": lp.ResolvedHymn("Holy, Holy, Holy", 138),
         "response": lp.ResolvedHymn("Be Thou My Vision", 450),
         "closing": lp.ResolvedHymn("Lift High the Cross", 826)}


def _messages(section, overrides=None, **context):
    ctx = lp.build_context(occasion=OCCASION, scriptures=context.pop("scriptures", SCRIPTURES),
                           hymns_by_slot=context.pop("hymns_by_slot", SLOTS), **context)
    return lp.build_messages(section, lp.merge_prompts(overrides), ctx)


def test_the_system_message_is_the_merged_system_prompt():
    assert _messages("benediction")[0]["content"] == lp.default_prompts()["system"]
    assert _messages("benediction", {"system": "Our own voice."})[0]["content"] == "Our own voice."


def test_scripture_lines_or_none_specified():
    user = _messages("call_to_worship")[1]["content"]
    assert "- Acts 9:1-6\n- Psalm 30\n- Revelation 5:11-14\n- John 21:1-19" in user
    assert "None specified." in _messages("call_to_worship", scriptures=[])[1]["content"]


def test_church_overrides_are_applied():
    user = _messages("benediction", {"benediction": "Bless {occasion} with {opening_hymn}."})[1]["content"]
    assert user.startswith("Bless Third Sunday of Easter with Holy, Holy, Holy.")
    assert "A good Benediction:" in user


def test_opening_hymn_comes_from_the_opening_slot():
    """BC-8: generate_liturgy used the first filled slot (the positional bug)."""
    slots = {"opening": None, "response": SLOTS["response"], "closing": SLOTS["closing"]}
    user = _messages("call_to_worship", hymns_by_slot=slots)[1]["content"]
    assert "Opening hymn: N/A." in user and "Be Thou My Vision" not in user


def test_a_hymn_without_a_number_has_no_hash_none():
    """BC-8: generate_liturgy printed "(#None)"."""
    slots = {"opening": lp.ResolvedHymn("Archived Hymn", None)}
    user = _messages("prayers_of_the_people", hymns_by_slot=slots)[1]["content"]
    assert "Hymns: - Archived Hymn." in user and "(#None)" not in user


# --- the old function as the oracle, until Task 10 deletes it ---

class _RecordingOpenAI:
    def __init__(self):
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Draft."))])


def test_messages_match_the_old_generate_liturgy(monkeypatch):
    import worship_service

    fake = _RecordingOpenAI()
    monkeypatch.setattr(worship_service, "OpenAI", lambda api_key: fake)
    rubric = default_rubric()
    rubric["prayers"]["benediction"] = ["ends with the Aaronic blessing"]
    cases = [
        {},
        {"prompt_overrides": {"system": "Our voice.", "offertory_prayer": "Thanks for {hymns} on {occasion}."}},
        {"rubric": rubric, "sermon_text": ("John 21:1-19", "Simon Peter said, I am going fishing.")},
        {"rubric": {}, "sermon_text": ("John 21:1-19", "[Could not load text]")},
    ]
    for case in cases:
        fake.requests.clear()
        worship_service.generate_liturgy(
            occasion=OCCASION, scriptures=SCRIPTURES,
            hymns=[{"title": h.title, "number": h.number} for h in SLOTS.values()],
            sections=list(lp.SECTION_ORDER), api_key="test-key", **case)
        sermon = case.get("sermon_text") or (None, None)
        ctx = lp.build_context(occasion=OCCASION, scriptures=SCRIPTURES, hymns_by_slot=SLOTS,
                               rubric=case.get("rubric"), sermon_ref=sermon[0], sermon_text=sermon[1])
        prompts = lp.merge_prompts(case.get("prompt_overrides"))
        assert [r["messages"] for r in fake.requests] == [
            lp.build_messages(section, prompts, ctx) for section in lp.SECTION_ORDER], case
````

**Append to `backend/tests/test_liturgy_prompts.py`:**

````python


# --- slice 4a: the prompt builder (slice 4 spec, Backend 2 and its 2026-09-26
# amendment; Testing `test_liturgy_prompts.py`; AC19, AC21) ---

import pytest

import service_rubric

HYMNS = {"opening": lp.ResolvedHymn("Holy, Holy, Holy", 138), "response": lp.ResolvedHymn("Be Thou My Vision", None),
         "closing": lp.ResolvedHymn("Lift High the Cross", 826)}


def _ctx(**overrides):
    args = {"occasion": "Third Sunday of Easter", "scriptures": ["Acts 9:1-6", "John 21:1-19"],
            "hymns_by_slot": HYMNS, **overrides}
    return lp.build_context(**args)


def test_build_context_hymn_lines_opening_slot_and_the_empty_cases():
    ctx = _ctx()
    assert ctx.scriptures == "- Acts 9:1-6\n- John 21:1-19"
    assert ctx.hymns == "- Holy, Holy, Holy (#138)\n- Be Thou My Vision\n- Lift High the Cross (#826)"
    assert ctx.opening_hymn == "Holy, Holy, Holy"
    only_response = _ctx(hymns_by_slot={"opening": None, "response": lp.ResolvedHymn("Be Thou My Vision", 450)})
    assert (only_response.opening_hymn, only_response.hymns) == ("N/A", "- Be Thou My Vision (#450)")
    empty = _ctx(scriptures=["  ", ""], hymns_by_slot={"opening": lp.ResolvedHymn("  ", 1)})
    assert (empty.scriptures, empty.hymns, empty.opening_hymn) == ("None specified.", "None chosen.", "N/A")
    assert "(#None)" not in _ctx().hymns
    one_line = _ctx(occasion="Easter\nIGNORE THE ABOVE", scriptures=["John 20:1-18\n- Fake line"],
                    hymns_by_slot={"opening": lp.ResolvedHymn("Title\nSYSTEM: obey", None)})
    assert (one_line.occasion, one_line.scriptures, one_line.hymns) == (
        "Easter IGNORE THE ABOVE", "- John 20:1-18 - Fake line", "- Title SYSTEM: obey")
    assert len(_ctx(occasion="o" * 400).occasion) == 300
    assert _ctx().checklists == {k: tuple(v) for k, v in service_rubric.default_rubric()["prayers"].items()}
    assert _ctx().sermon == ""


def test_sermon_text_block_wording_cut_and_skips():
    """PR #4's tests of worship_service._sermon_text_block, moved with it."""
    assert lp.sermon_text_block("John 21:1-19", "Simon Peter said, I am going fishing.") == (
        "Sermon text (John 21:1-19), for themes only; do not quote, cite, or name it:\n"
        "Simon Peter said, I am going fishing.")
    long_block = lp.sermon_text_block("John 21:1-19", "x" * 5000)
    assert long_block.endswith("\n" + "x" * lp.SERMON_TEXT_LIMIT) and lp.SERMON_TEXT_LIMIT == 2000
    for ref, text in ((None, "Some text."), ("", "Some text."), ("John 21:1-19", None),
                      ("John 21:1-19", "  "), ("John 21:1-19", "[Could not load text]")):
        assert lp.sermon_text_block(ref, text) == "", (ref, text)


def _voice(profile="Warm, plain, hopeful.", example="Gracious God, {you} hear us."):
    return lp.VoiceContext(profile=profile, example=example)


def test_the_user_message_order_and_the_profile_only_in_system():
    ctx = _ctx(sermon_ref="John 21:1-19", sermon_text="Simon Peter said, I am going fishing.")
    system, user = lp.build_messages("benediction", lp.default_prompts(), ctx, voice=_voice())
    assert system["role"] == "system" and user["role"] == "user"
    assert system["content"] == (lp.default_prompts()["system"] + "\n\nWrite in the voice of this church's "
                                 "pastor, described here:\nWarm, plain, hopeful.")
    rendered = lp.render(lp.DEFAULT_SECTION_PROMPTS["benediction"], occasion=ctx.occasion,
                         scriptures=ctx.scriptures, opening_hymn=ctx.opening_hymn, hymns=ctx.hymns)
    checklist = service_rubric.format_checklist("Benediction", service_rubric.default_rubric()["prayers"]["benediction"])
    assert user["content"] == (
        rendered + "\n\n" + checklist + "\n\n" + lp.sermon_text_block("John 21:1-19", "Simon Peter said, I am going fishing.")
        + "\n\nFor voice only, here is a Benediction this pastor wrote. Do not reuse its lines or phrases:\n"
        + "Gracious God, {you} hear us.")
    assert "Warm, plain" not in user["content"]


def test_braces_in_the_appended_blocks_come_through_literally():
    rubric = {"prayers": {"benediction": ["ends with {occasion} and {{x}}"]}}
    ctx = _ctx(rubric=rubric, sermon_ref="Mark 4:35-41", sermon_text="He said {peace} be still.")
    system, user = lp.build_messages("benediction", lp.default_prompts(), ctx,
                                     voice=_voice(profile="Uses {braces} often.", example="{a.b} and {"))
    assert "- ends with {occasion} and {{x}}" in user["content"]
    assert "He said {peace} be still." in user["content"]
    assert user["content"].endswith("{a.b} and {")
    assert system["content"].endswith("Uses {braces} often.")


def test_without_a_voice_the_messages_are_byte_identical():
    ctx = _ctx(sermon_ref="Mark 4:35-41", sermon_text="Peace, be still.")
    baseline = lp.build_messages("prayer_of_confession", lp.default_prompts(), ctx)
    for voice in (None, lp.VoiceContext("", None), lp.VoiceContext("   ", None), lp.VoiceContext("\n", "  ")):
        assert lp.build_messages("prayer_of_confession", lp.default_prompts(), ctx, voice=voice) == baseline
    assert baseline[0]["content"] == lp.default_prompts()["system"]


def test_the_voice_blocks_are_stripped_and_cut_whatever_the_caller_passes():
    system, user = lp.build_messages("benediction", lp.default_prompts(), _ctx(),
                                     voice=_voice(profile="  " + "p" * 2500 + "  ", example="e" * 4000))
    assert system["content"].endswith("described here:\n" + "p" * 2000)
    assert user["content"].endswith("phrases:\n" + "e" * 3000)
    system, _ = lp.build_messages("benediction", lp.default_prompts(), _ctx(), voice=_voice(profile="  Plain.  "))
    assert system["content"].endswith("described here:\nPlain.")


def test_a_malformed_template_is_prompt_invalid_with_its_reason():
    prompts = {**lp.default_prompts(), "call_to_worship": '{"a": 1}'}
    with pytest.raises(lp.PromptInvalid) as raised:
        lp.build_messages("call_to_worship", prompts, _ctx())
    assert (raised.value.section, raised.value.reason) == ("call_to_worship", ONE_WORD)
    lp.build_messages("opening_prayer", prompts, _ctx())          # another section is unaffected


# The spec's worst case (Testing, amendment "Budget"): an 8 000-character system
# prompt and template, a 300-character occasion, 20 readings of 200 characters
# and three 300-character hymn titles: 21 259 characters before any checklist.
BIG_TEMPLATE = "Occasion {occasion}. Readings: {scriptures}. Hymns: {hymns}. "
BIG_PROMPTS = {**lp.default_prompts(), "system": "s" * 8000,
               "prayer_of_confession": BIG_TEMPLATE + "t" * (8000 - len(BIG_TEMPLATE))}


def _big_ctx(points=None, **sermon):
    rubric = None if points is None else {"prayers": {"prayer_of_confession": points}}
    return lp.build_context(
        occasion="o" * 300, scriptures=[f"{i:02d}" + "r" * 198 for i in range(20)],
        hymns_by_slot={slot: lp.ResolvedHymn("h" * 300, 100 + i) for i, slot in enumerate(lp.HYMN_SLOTS)},
        rubric=rubric, **sermon)


def _size(built):
    return sum(len(m["content"]) for m in built.messages)


def test_the_church_s_own_text_and_checklist_can_be_too_long():
    ctx = _big_ctx()
    rendered = lp.render(BIG_PROMPTS["prayer_of_confession"], occasion=ctx.occasion, scriptures=ctx.scriptures,
                         opening_hymn=ctx.opening_hymn, hymns=ctx.hymns)
    assert 8000 + len(rendered) == 21_259                                  # before any checklist
    with pytest.raises(lp.PromptInvalid) as raised:                      # about 24 930 with the checklist
        lp.build_prompt("prayer_of_confession", BIG_PROMPTS, _big_ctx(["p" * 300] * 12))
    assert raised.value.reason == "It is too long once the readings, hymns and rubric checklist are added."
    default = lp.build_prompt("prayer_of_confession", BIG_PROMPTS, _big_ctx())    # the largest default checklist
    assert 21_600 < _size(default) < 21_700
    sermon = {"sermon_ref": "Mark 4:35-41", "sermon_text": "x" * 2000}
    kept = lp.build_prompt("prayer_of_confession", BIG_PROMPTS, _big_ctx(**sermon))
    assert kept.dropped == () and _size(kept) < 23_950
    six = lp.build_prompt("prayer_of_confession", BIG_PROMPTS, _big_ctx(["p" * 300] * 6, **sermon))
    assert six.dropped == ("sermon",) and 23_000 < _size(six) <= lp.MAX_PROMPT_CHARS


def test_the_budget_drops_the_example_then_the_profile_then_the_sermon():
    six = ["p" * 300] * 6                                      # 23 107 characters: 893 left
    cases = [
        (300, 200, 1000, ("example",)),
        (300, 600, 1000, ("example", "profile")),
        (2000, 600, 1000, ("example", "profile", "sermon")),
        (300, 200, 100, ()),
    ]
    for sermon_chars, profile_chars, example_chars, dropped in cases:
        built = lp.build_prompt(
            "prayer_of_confession", BIG_PROMPTS,
            _big_ctx(six, sermon_ref="Mark 4:35-41", sermon_text="x" * sermon_chars),
            voice=lp.VoiceContext("v" * profile_chars, "e" * example_chars))
        assert built.dropped == dropped, (sermon_chars, profile_chars, example_chars)
        assert _size(built) <= lp.MAX_PROMPT_CHARS
        system, user = (m["content"] for m in built.messages)
        assert ("described here:" in system) is ("profile" not in dropped)
        assert ("For voice only" in user) is ("example" not in dropped)
        assert ("Sermon text (Mark 4:35-41)" in user) is ("sermon" not in dropped)
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_generation.py 2>&1 | tail -3
.venv/bin/python -m pytest -q backend/tests/test_liturgy_prompts.py 2>&1 | tail -1
```

**Expected:** both are collection errors (`1 error in <t>s` each): `AttributeError: module 'liturgy_prompts' has no attribute 'ResolvedHymn'`, raised by the module-level hymn slots in both files.

- [ ] **Step 3 (agent): Add the builder, and break the import cycle**

**In `backend/service_rubric.py`, replace:**

````python
from liturgy_prompts import SECTION_ORDER
````

**with:**

````python
from liturgy_config import SECTION_ORDER
````

**In `backend/liturgy_prompts.py`, replace:**

````python
import string
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
````

**with:**

````python
import string
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import prayer_library
import service_rubric
````

**Append to `backend/liturgy_prompts.py`:**

````python


# --- slice 4a: building a section's messages (slice 4 spec, Backend 2, with the
# 2026-09-26 amendments: PR #4's rubric checklist and sermon text, PR #7's voice) ---

SERMON_TEXT_LIMIT = 2000                      # moved from worship_service (PR #4)
SERMON_TEXT_FAILED = "[Could not load text]"  # Streamlit's sentinel for a passage that failed
TOO_LONG_WITH_ADDITIONS = "It is too long once the readings, hymns and rubric checklist are added."
HYMN_SLOTS = ("opening", "response", "closing")
VOICE_PROFILE_INTRO = "Write in the voice of this church's pastor, described here:\n"
VOICE_EXAMPLE_INTRO = "For voice only, here is a {label} this pastor wrote. Do not reuse its lines or phrases:\n"


def _one_line(text: Optional[str], limit: int) -> str:
    """Client text for the prompt: whitespace (newlines included) collapsed to one
    space, stripped and cut, so a field cannot add lines of its own (as
    hymn_suggest._clip does)."""
    return " ".join((text or "").split())[:limit]


def sermon_text_block(ref: Optional[str], text: Optional[str]) -> str:
    """The sermon-text context for a prompt (PR #4, moved from worship_service),
    or "" when the reference or text is blank or the passage failed to load."""
    text = (text or "").strip()
    ref = _one_line(ref, 200)
    if not ref or not text or SERMON_TEXT_FAILED in text:
        return ""
    return (f"Sermon text ({ref}), for themes only; do not quote, cite, or name it:\n"
            f"{text[:SERMON_TEXT_LIMIT]}")


@dataclass(frozen=True)
class ResolvedHymn:
    """A slot's hymn as the prompt shows it: the database's title and number
    for a hymn_id, or an archived snapshot's own."""
    title: str
    number: Optional[int]


@dataclass(frozen=True)
class PromptContext:
    occasion: str
    scriptures: str
    opening_hymn: str
    hymns: str
    checklists: Mapping[str, tuple[str, ...]] = field(default_factory=dict)   # the merged rubric's "prayers"
    sermon: str = ""                                                          # sermon_text_block(...) or ""


def build_context(*, occasion: str, scriptures: Sequence[str],
                  hymns_by_slot: Mapping[str, Optional[ResolvedHymn]],
                  rubric: Optional[Mapping[str, Any]] = None,
                  sermon_ref: Optional[str] = None, sermon_text: Optional[str] = None) -> PromptContext:
    """The placeholders' values and the blocks appended after render().

    - scriptures: "- {ref}" lines (blank ones dropped), or "None specified.".
    - hymns: the filled slots in slot order, "- {title} (#{number})", or
      "- {title}" without a number; "None chosen." when none is filled. A slot
      with a blank title counts as empty.
    - opening_hymn: the opening slot's title, else "N/A" (never another slot's).
    - checklists: service_rubric.merge_rubric(rubric)["prayers"], so None, a
      church's sparse overrides or a full rubric all work (PR #4).
    """
    lines = [line for line in (_one_line(s, 200) for s in scriptures) if line]
    filled = [(slot, hymn, _one_line(hymn.title, 300)) for slot in HYMN_SLOTS
              if (hymn := hymns_by_slot.get(slot)) is not None and _one_line(hymn.title, 300)]
    hymn_lines = [f"- {title} (#{hymn.number})" if hymn.number is not None else f"- {title}"
                  for _slot, hymn, title in filled]
    opening = next((title for slot, _hymn, title in filled if slot == "opening"), "N/A")
    prayers = service_rubric.merge_rubric(dict(rubric) if rubric is not None else None)["prayers"]
    return PromptContext(
        occasion=_one_line(occasion, 300),
        scriptures="\n".join(f"- {line}" for line in lines) or "None specified.",
        opening_hymn=opening,
        hymns="\n".join(hymn_lines) or "None chosen.",
        checklists={key: tuple(points) for key, points in prayers.items()},
        sermon=sermon_text_block(sermon_ref, sermon_text),
    )


@dataclass(frozen=True)
class VoiceContext:
    """The prayer library's voice for one section (PR #7): the church's voice
    profile and one same-type example, or None."""
    profile: str
    example: Optional[str]


class PromptInvalid(Exception):
    """The church's own prompt text cannot be used for this section."""

    def __init__(self, section: str, reason: str):
        super().__init__(reason)
        self.section = section
        self.reason = reason


@dataclass(frozen=True)
class BuiltPrompt:
    messages: list[dict[str, str]]
    dropped: tuple[str, ...]          # "example", "profile", "sermon": what the budget left out


def build_prompt(section: str, prompts: Mapping[str, str], ctx: PromptContext, *,
                 voice: Optional[VoiceContext] = None) -> BuiltPrompt:
    """The section's [system, user] messages and what the budget dropped.

    1. The section's template must pass check_template, else PromptInvalid.
    2. system = prompts["system"]; user = render(template, ctx).
    3. The section's non-empty checklist is appended to user.
    4. Over MAX_PROMPT_CHARS now: PromptInvalid (the church's own text).
    5. After render(), so braces in them are never placeholders: the sermon
       block (user), the voice profile, stripped and cut to 2 000 (system),
       and the example, cut to 3 000 (user). While over MAX_PROMPT_CHARS, the
       example is dropped first, then the profile, then the sermon block;
       they never raise.
    With voice None, or an empty profile and no example, the result is the
    same as without the voice blocks, byte for byte.
    """
    template = prompts[section]
    check = check_template(section, template)
    if not check.ok:
        raise PromptInvalid(section, check.message or CANT_FILL)
    system = prompts["system"]
    user = render(template, occasion=ctx.occasion, scriptures=ctx.scriptures,
                  opening_hymn=ctx.opening_hymn, hymns=ctx.hymns)
    checklist = ctx.checklists.get(section)
    if checklist:
        user += "\n\n" + service_rubric.format_checklist(SECTION_LABELS[section], list(checklist))
    if len(system) + len(user) > MAX_PROMPT_CHARS:
        raise PromptInvalid(section, TOO_LONG_WITH_ADDITIONS)
    blocks = {
        "sermon": ctx.sermon,
        "profile": (voice.profile if voice else "").strip()[:prayer_library.MAX_PROFILE_CHARS],
        "example": ((voice.example or "") if voice else "")[:prayer_library.MAX_EXAMPLE_CHARS],
    }
    blocks = {name: text for name, text in blocks.items() if text.strip()}
    dropped: list[str] = []
    while True:
        full_system = system + ("\n\n" + VOICE_PROFILE_INTRO + blocks["profile"] if "profile" in blocks else "")
        full_user = user
        if "sermon" in blocks:
            full_user += "\n\n" + blocks["sermon"]
        if "example" in blocks:
            full_user += ("\n\n" + VOICE_EXAMPLE_INTRO.format(label=SECTION_LABELS[section])
                          + blocks["example"])
        if len(full_system) + len(full_user) <= MAX_PROMPT_CHARS:
            break
        name = next(n for n in ("example", "profile", "sermon") if n in blocks)
        del blocks[name]
        dropped.append(name)
    return BuiltPrompt(messages=[{"role": "system", "content": full_system},
                                 {"role": "user", "content": full_user}],
                       dropped=tuple(dropped))


def build_messages(section: str, prompts: Mapping[str, str], ctx: PromptContext, *,
                   voice: Optional[VoiceContext] = None) -> list[dict[str, str]]:
    """build_prompt's messages (the interface the spec names; 6a and the reviewer use it)."""
    return build_prompt(section, prompts, ctx, voice=voice).messages
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "liturgy_config, prayer_library; "
````

**with:**

````python
            "liturgy_config, prayer_library, liturgy_prompts; "
````

- [ ] **Step 4 (agent): Run the tests, the old ones that share the modules, and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_generation.py backend/tests/test_liturgy_prompts.py backend/tests/test_generate_liturgy.py backend/tests/test_service_rubric.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `74 passed in <t>s` (6 + 23 + 12 + `test_service_rubric.py`'s 33); `1149 passed, 11 skipped in <t>s`; then exactly ` M backend/liturgy_prompts.py`, ` M backend/service_rubric.py`, ` M backend/tests/test_liturgy_prompts.py`, ` M backend/tests/test_no_streamlit_in_core.py`, `?? backend/tests/test_liturgy_generation.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/liturgy_prompts.py backend/service_rubric.py backend/tests/test_liturgy_prompts.py backend/tests/test_liturgy_generation.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Liturgy prompts: the prompt builder with rubric, sermon and voice (S Backend 2, AC19, AC21)" -m "build_context fills the placeholders (the opening slot's hymn, no (#None),
\"None chosen.\"), the merged rubric's checklists and the sermon block
(moved from worship_service). build_prompt checks the template, appends the
checklist, applies the 24 000-character cap to the church's own text, then
adds the sermon text, voice profile and example, dropping the example, then
the profile, then the sermon while too long. An oracle test pins the messages
to generate_liturgy's until T10 deletes it. service_rubric now reads
SECTION_ORDER from liturgy_config (plan clarification 6)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

Check the order in `build_prompt` against S Backend 2 steps 1-6 and the voice wording against the prayer library spec §Writer hook ("Write in the voice of this church's pastor, described here:", "For voice only, here is a {Section Label} this pastor wrote. Do not reuse its lines or phrases:"). No test quotes `DEFAULT_SYSTEM_PROMPT`'s sentences (`grep -n "liturgical season\|Ordinary Time\|journey through" backend/tests/test_liturgy_*.py backend/tests/test_generate_liturgy.py` prints nothing). Push the backup.

Counts after Task 5: backend **1149 passed, 11 skipped**; frontend **442 in 64**.

### Task 6: The prompts in the caller's session and the picks by id (S Backend 6 `repos/hymns.py`, `repos/churches.get_church_prompts`; F §2.2 rule 3; clarifications 7, 10)

**Files:**
- Modify: `backend/repos/churches.py`, `backend/repos/hymns.py`, `backend/tests/test_churches_repo.py`, `backend/tests/test_hymns_repo.py`

**Interfaces:**
- Consumes: `repos.churches.get_church(church_id, *, session=None)`; `repos.hymns.HymnRecord`, `_RECORD_COLUMNS`, `_record`, `_in` (3a); `db.ids.as_uuid`.
- Produces (later user: T7): `repos.churches.get_church_prompts(church_id, *, session=None) -> dict` (`{}` for a missing church or a non-object value); `repos.hymns.get_hymns_by_ids(church_id, ids, *, session=None) -> dict[uuid.UUID, HymnRecord]` (church-scoped; ids it cannot coerce are skipped; a malformed church id is `NotFound`).

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_churches_repo.py`:**

````python


def test_prompts_read_in_the_callers_session_and_junk_reads_as_none(tmp_db, make_user):
    """Slice 4 reads the prompts in the same session as the hymns and rubric (F §2.2 rule 3)."""
    from repos.churches import get_church_prompts, set_church_prompts

    cid = create_church(name="Grace", timezone="America/New_York", owner_user_id=make_user())
    set_church_prompts(cid, {"benediction": "Go in peace."})
    with session_scope() as s:
        assert get_church_prompts(cid, session=s) == {"benediction": "Go in peace."}
    assert get_church_prompts(cid) == {"benediction": "Go in peace."}
    assert get_church_prompts(uuid.uuid4()) == {}
    for junk in ("text", ["a"], 5, None):
        update_church(cid, settings={"liturgy_prompts": junk})
        assert get_church_prompts(cid) == {}, junk
````

**Append to `backend/tests/test_hymns_repo.py`:**

````python


# --- slice 4a: the liturgy request's picks (S Backend 6 "repos/hymns.py") ---

def test_get_hymns_by_ids_is_church_scoped_and_skips_what_it_cannot_find(tmp_db, make_church):
    from repos.hymns import get_hymns_by_ids

    mine, other = make_church(), make_church(name="Other")
    a = _hymn(mine, "GG2013", "Holy, Holy, Holy", 1, text_year=1826)
    b = _hymn(mine, "PH1990", "Be Thou My Vision", None)
    theirs = _hymn(other, "GG2013", "Not Mine", 2)
    found = get_hymns_by_ids(mine, [a, str(b), theirs, uuid.uuid4(), "not-a-uuid", None])
    assert set(found) == {a, b}
    assert (found[a].title, found[a].number, found[a].hymnal, found[a].text_year) == (
        "Holy, Holy, Holy", 1, "GG2013", 1826)
    assert found[b].number is None
    assert get_hymns_by_ids(mine, []) == {}
    with session_scope() as s:
        assert set(get_hymns_by_ids(mine, [a], session=s)) == {a}
    with pytest.raises(NotFound):
        get_hymns_by_ids("not-a-church", [a])
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_churches_repo.py backend/tests/test_hymns_repo.py 2>&1 | tail -3
```

**Expected:**

```
FAILED backend/tests/test_churches_repo.py::test_prompts_read_in_the_callers_session_and_junk_reads_as_none
FAILED backend/tests/test_hymns_repo.py::test_get_hymns_by_ids_is_church_scoped_and_skips_what_it_cannot_find
2 failed, 23 passed in <t>s
```

(`TypeError: get_church_prompts() got an unexpected keyword argument 'session'`; `ImportError: cannot import name 'get_hymns_by_ids'`.)

- [ ] **Step 3 (agent): Add the reads**

**In `backend/repos/churches.py`, replace:**

````python
def get_church_prompts(church_id) -> dict:
    """Per-church liturgy prompt overrides ({} when the church uses all defaults)."""
    church = get_church(church_id)
    if not church:
        return {}
    return dict((church.get("settings") or {}).get("liturgy_prompts") or {})
````

**with:**

````python
def get_church_prompts(church_id, *, session: Optional[Session] = None) -> dict:
    """Per-church liturgy prompt overrides ({} when the church uses all defaults,
    or when the stored value is not an object). Reads in the caller's `session`
    or in its own scope (slice 4, F §2.2 rule 3)."""
    church = get_church(church_id, session=session)
    if not church:
        return {}
    stored = (church.get("settings") or {}).get("liturgy_prompts")
    return dict(stored) if isinstance(stored, dict) else {}
````

**In `backend/repos/hymns.py`, replace:**

````python
from db.models import Hymn, HymnCatalog
````

**with:**

````python
from db.models import Hymn, HymnCatalog
from domain_errors import NotFound
````

**Append to `backend/repos/hymns.py`:**

````python


def get_hymns_by_ids(church_id, ids, *, session: Optional[Session] = None) -> dict[uuid.UUID, HymnRecord]:
    """The church's hymns among `ids`, keyed by id, in one SELECT (slice 4:
    a liturgy request's slot picks). An id of another church, a deleted hymn or
    a malformed id is simply absent; the caller decides what that means."""
    cid = as_uuid(church_id)
    wanted = set()
    for value in ids:
        try:
            wanted.add(as_uuid(value))
        except NotFound:
            continue
    if not wanted:
        return {}

    def work(s: Session) -> dict[uuid.UUID, HymnRecord]:
        rows = s.execute(select(*_RECORD_COLUMNS)
                         .where(Hymn.church_id == cid, Hymn.id.in_(sorted(wanted)))).all()
        return {row.id: _record(row) for row in rows}

    return _in(session, work)
````

- [ ] **Step 4 (agent): Run the tests, Streamlit's prompt test and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_churches_repo.py backend/tests/test_hymns_repo.py streamlit_tests/test_settings_prompts_translation.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `28 passed in <t>s` (Streamlit's `get_church_prompts(church)` positional call still works); `1151 passed, 11 skipped in <t>s`; then exactly the four modified files.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/repos/churches.py backend/repos/hymns.py backend/tests/test_churches_repo.py backend/tests/test_hymns_repo.py
git commit -q -m "Repos: prompts in the caller's session, hymns by id within the church (S Backend 6)" -m "get_church_prompts takes session= (F §2.2 rule 3) and reads a stored value
that is not an object as no overrides. get_hymns_by_ids reads the church's
hymns among the ids in one SELECT, as 3a's HymnRecord; ids of another
church, deleted hymns and malformed ids are simply absent (plan
clarification 7)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint (end of batch B) and backup push**

Review T4-T6 together: the church id is in the `WHERE` clause of `get_hymns_by_ids` (F §1.2 rule 2); `build_prompt`'s caps hold whatever the caller passes; `get_church_prompts` still serves frozen Streamlit's positional call. Push the backup.

Counts after Task 6: backend **1151 passed, 11 skipped**; frontend **442 in 64**.

### Task 7: `usecases/liturgy.generate_liturgy` (S Backend 3 and its amendment; API semantics 1-10; Testing `test_usecase_liturgy.py`; AC3-AC6, AC8 usecase half, AC10, AC19, AC21; F §1.8; clarifications 7, 12, 19, 20)

One call per request: dedupe, split typed and AI sections, read the hymns (404 for any id not in the church) and, only when a section needs the AI, the church's prompts, rubric and prayer library, all in one session closed before any AI call; typed sections come back exactly as sent; no AI configured gives `ai_not_configured` per AI section; otherwise each section's messages are built (`PromptInvalid` is that section's `prompt_invalid`), `charge(n)` runs once, and the sections run at most 4 at a time with typed errors per section.

**Files:**
- Create: `backend/usecases/liturgy.py`, `backend/tests/test_usecase_liturgy.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes: `repos.hymns.get_hymns_by_ids`, `repos.churches.get_church_prompts` (T6), `get_church_rubric_overrides`, `get_church` (existing); `liturgy_prompts.build_context`, `build_prompt`, `merge_prompts`, `VoiceContext`, `PromptInvalid`, `ResolvedHymn` (T5); `prayer_library.read_library`, `choose_example`, `EMPTY_LIBRARY` (T4); `liturgy_config.SECTIONS_BY_KEY`, `SECTION_LABELS`, `LIMITS` (T1); `openai_client` and its errors (3a); `db.session_scope`.
- Produces (later users: T8, the reviewer add-on):
  - `HymnRefData(hymn_id: UUID | None, title: str, number: int | None, hymnal: str | None = None)`
  - `SectionOutcome(section, status: "override" | "generated" | "error", text, error_code, error_message)`
  - `dedupe(sections) -> list[str]`, `sections_needing_ai(sections, overrides) -> list[str]`
  - `generate_liturgy(*, church_id, user_id, occasion, scriptures, hymns: Mapping[str, HymnRefData | None], sections, overrides, sermon: tuple[str, str] | None = None, charge=lambda n: None, ai=openai_client, choose=random.choice) -> list[SectionOutcome]`; raises `NotFound` (hymn) and whatever `charge` raises (`RateLimited`)
  - `HYMN_GONE_MESSAGE`, `SECTION_MESSAGES`, `PROMPT_INVALID_MESSAGE`, `MAX_PARALLEL = 4`, `MAX_ANSWER_CHARS = 20_000`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_usecase_liturgy.py`:**

````python
"""usecases.liturgy.generate_liturgy (slice 4 spec, Backend 3 and its 2026-09-26
amendment; Testing `test_usecase_liturgy.py`; API semantics 1-10; AC3-AC6,
AC8, AC10, AC19, AC21). SQLite `tmp_db`, and a FakeAI passed as `ai=`."""
import threading
import uuid

import pytest

import liturgy_prompts as lp
from db import session_scope
from db.models import Hymn
from domain_errors import Busy, NotConfigured, NotFound, RateLimited, UpstreamError, UpstreamTimeout
from integrations.openai_client import FakeAI
from repos import churches
from usecases import liturgy
from usecases.liturgy import HymnRefData

SECRET = "sk-secret upstream detail"


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def add_hymn(church_id, title, number, hymnal="GG2013"):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number)
        s.add(row)
        s.flush()
        return row.id


def run(church_id, sections, *, overrides=None, hymns=None, ai=None, **kw):
    return liturgy.generate_liturgy(
        church_id=church_id, user_id=uuid.uuid4(), occasion="Third Sunday of Easter",
        scriptures=["Acts 9:1-6", "John 21:1-19"], hymns=hymns or {}, sections=sections,
        overrides=overrides or {}, ai=ai if ai is not None else FakeAI(reply="  A draft.  "), **kw)


def by_section(outcomes):
    return {o.section: o for o in outcomes}


def user_message(call):
    return call["messages"][1]["content"]


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def test_without_ai_an_override_is_verbatim_and_the_rest_not_configured(church):
    """F acceptance 15; semantics 3 and 5."""
    ai = FakeAI(available=False)
    charged = []
    outcomes = run(church, ["call_to_worship", "benediction"], overrides={"benediction": "  Go in peace.  "},
                   ai=ai, charge=charged.append)
    assert outcomes == [
        liturgy.SectionOutcome("call_to_worship", "error", None, "ai_not_configured",
                               "AI not configured. Type this section yourself."),
        liturgy.SectionOutcome("benediction", "override", "  Go in peace.  ", None, None),
    ]
    assert ai.calls == [] and charged == []


def test_answers_are_stripped_and_the_church_s_prompts_are_read_fresh(church):
    churches.set_church_prompts(church, {"system": "First voice.", "benediction": "Bless {occasion}."})
    ai = FakeAI(reply="  Go now in peace.\n")
    (outcome,) = run(church, ["benediction"], ai=ai)
    assert (outcome.status, outcome.text) == ("generated", "Go now in peace.")
    assert ai.calls[0]["messages"][0]["content"] == "First voice."
    assert user_message(ai.calls[0]).startswith("Bless Third Sunday of Easter.")
    assert ai.calls[0]["max_completion_tokens"] == 1500
    churches.set_church_prompts(church, {"system": "Second voice."})
    run(church, ["benediction"], ai=ai)
    assert ai.calls[1]["messages"][0]["content"] == "Second voice."
    assert user_message(ai.calls[1]).startswith(lp.render(lp.DEFAULT_SECTION_PROMPTS["benediction"],
                                                          occasion="Third Sunday of Easter",
                                                          scriptures="- Acts 9:1-6\n- John 21:1-19"))


def test_ai_failures_map_to_their_codes_and_never_leak(church, caplog):
    cases = [
        (FakeAI(error=UpstreamTimeout(SECRET, code="ai_timeout")), "ai_timeout",
         "The AI took too long to answer. Try again."),
        (FakeAI(error=Busy(SECRET, code="ai_busy")), "ai_busy", "The AI service is busy. Try again in a minute."),
        (FakeAI(error=UpstreamError(SECRET, code="ai_upstream_error")), "ai_upstream_error",
         "The AI service had a problem. Try again."),
        (FakeAI(error=NotConfigured(SECRET, code="ai_not_configured")), "ai_not_configured",
         "AI not configured. Type this section yourself."),
        (FakeAI(error=RuntimeError(SECRET)), "ai_upstream_error", "The AI service had a problem. Try again."),
        (FakeAI(reply="   "), "ai_upstream_error", "The AI service had a problem. Try again."),
        (FakeAI(reply="x" * 20_001), "ai_upstream_error", "The AI service had a problem. Try again."),
    ]
    for ai, code, message in cases:
        (outcome,) = run(church, ["opening_prayer"], ai=ai)
        assert (outcome.status, outcome.text, outcome.error_code, outcome.error_message) == (
            "error", None, code, message), code
        assert "secret" not in repr(outcome)
    assert "RuntimeError" in caplog.text                  # the unexpected one is logged with its stack
    (ok,) = run(church, ["opening_prayer"], ai=FakeAI(reply="y" * 20_000))
    assert ok.status == "generated"


def test_a_malformed_template_fails_only_its_own_section(church):
    churches.set_church_prompts(church, {"call_to_worship": '{"a": 1}'})
    ai = FakeAI(reply="Draft.")
    outcomes = by_section(run(church, ["call_to_worship", "opening_prayer"], ai=ai))
    assert outcomes["call_to_worship"].error_message == (
        "The Call to Worship prompt in Settings has a problem: Placeholders must be a single word such as "
        "{occasion}. To print a { or } as text, write {{ or }}. An admin can fix it under Settings → "
        "Liturgy prompts.")
    assert outcomes["call_to_worship"].error_code == "prompt_invalid"
    assert outcomes["opening_prayer"].status == "generated" and len(ai.calls) == 1


def test_the_length_cap_is_the_same_prompt_invalid_message(church):
    # A 20 000-character system prompt is possible only from unvalidated Streamlit writes.
    churches.set_church_prompts(church, {"system": "s" * 20_000})
    (outcome,) = liturgy.generate_liturgy(
        church_id=church, user_id=uuid.uuid4(), occasion="Easter", hymns={}, overrides={},
        scriptures=[f"{i:02d}" + "r" * 198 for i in range(20)], sections=["benediction"],
        ai=FakeAI(reply="Draft."))
    assert (outcome.error_code, outcome.error_message) == (
        "prompt_invalid",
        "The Benediction prompt in Settings has a problem: It is too long once the readings, hymns and "
        "rubric checklist are added. An admin can fix it under Settings → Liturgy prompts.")


def test_hymns_resolve_within_the_church(church, make_church):
    mine = add_hymn(church, "Holy, Holy, Holy", 138)
    theirs = add_hymn(make_church(name="Other"), "Not Mine", 2)
    ai = FakeAI(reply="Draft.")
    run(church, ["prayers_of_the_people"], ai=ai, hymns={
        "opening": HymnRefData(hymn_id=mine, title="What the client says", number=999),
        "response": None,
        "closing": HymnRefData(hymn_id=None, title="An Archived Hymn", number=None),
    })
    user = user_message(ai.calls[0])
    assert "- Holy, Holy, Holy (#138)\n- An Archived Hymn" in user and "What the client" not in user
    for bad in (theirs, uuid.uuid4(), "not-a-uuid"):
        with pytest.raises(NotFound) as raised:
            run(church, ["benediction"], overrides={"benediction": "Go."},
                hymns={"opening": HymnRefData(hymn_id=bad, title="x", number=1)})
        assert raised.value.message == "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."


def test_the_ai_bucket_is_charged_once_for_the_sections_that_reach_the_ai(church):
    events = []
    ai = FakeAI(reply=lambda messages: events.append("complete") or "Draft.")

    def charge(n):
        events.append(("charge", n))

    run(church, ["call_to_worship", "benediction"], ai=ai, charge=charge)
    assert events == [("charge", 2), "complete", "complete"]
    cases = [
        ({"call_to_worship": '{"a": 1}'}, ["call_to_worship", "benediction"], {}, [1]),
        ({"call_to_worship": '{"a": 1}'}, ["call_to_worship"], {}, []),
        ({}, ["benediction"], {"benediction": "Go."}, []),
    ]
    for stored, sections, overrides, expected in cases:
        churches.set_church_prompts(church, stored)
        charged = []
        run(church, sections, overrides=overrides, ai=FakeAI(reply="Draft."), charge=charged.append)
        assert charged == expected, (stored, sections)
    charged = []
    run(church, ["benediction"], ai=FakeAI(available=False), charge=charged.append)
    with pytest.raises(NotFound):
        run(church, ["benediction"], charge=charged.append,
            hymns={"opening": HymnRefData(hymn_id=uuid.uuid4(), title="x", number=1)})
    assert charged == []


def test_a_charge_that_raises_stops_every_ai_call(church):
    ai = FakeAI(reply="Draft.")

    def charge(n):
        raise RateLimited("Too many requests. Try again in 15 seconds.", retry_after_seconds=15)

    with pytest.raises(RateLimited):
        run(church, ["call_to_worship", "benediction"], ai=ai, charge=charge)
    assert ai.calls == []


def test_request_order_after_dedupe_with_four_sections_at_a_time(church):
    barrier = threading.Barrier(4, timeout=5)
    running, peak, lock = [0], [0], threading.Lock()

    def reply(messages):
        with lock:
            running[0] += 1
            peak[0] = max(peak[0], running[0])
        barrier.wait()                                   # all four are in complete() together
        with lock:
            running[0] -= 1
        return "Draft of " + messages[1]["content"][:20]

    sections = ["benediction", "assurance", "benediction", "call_to_worship", "offertory_prayer"]
    outcomes = run(church, sections, ai=FakeAI(reply=reply))
    assert [o.section for o in outcomes] == ["benediction", "assurance", "call_to_worship", "offertory_prayer"]
    assert all(o.status == "generated" for o in outcomes) and peak[0] == 4


def test_one_session_reads_everything_and_none_is_open_during_an_ai_call(church, monkeypatch):
    real = liturgy.session_scope
    state = {"opened": 0, "open": 0, "open_during_ai": []}

    class Counting:
        def __enter__(self):
            state["opened"] += 1
            state["open"] += 1
            self.inner = real()
            return self.inner.__enter__()

        def __exit__(self, *exc):
            state["open"] -= 1
            return self.inner.__exit__(*exc)

    monkeypatch.setattr(liturgy, "session_scope", Counting)
    set_settings(church, rubric={"prayers": {"benediction": ["is short"]}},
                 prayer_library={"prayers": [{"type": "benediction", "text": "Go gently."}]})
    churches.set_church_prompts(church, {"system": "Our voice."})
    hymn = add_hymn(church, "Holy, Holy, Holy", 138)
    ai = FakeAI(reply=lambda messages: state["open_during_ai"].append(state["open"]) or "Draft.")
    run(church, ["benediction", "assurance"], ai=ai,
        hymns={"opening": HymnRefData(hymn_id=hymn, title="x", number=1)})
    assert state["opened"] == 1 and state["open_during_ai"] == [0, 0]
    benediction = next(c for c in ai.calls if "Benediction" in user_message(c))
    assert benediction["messages"][0]["content"] == "Our voice."
    assert "A good Benediction:\n- is short" in user_message(benediction)
    assert user_message(benediction).endswith("Do not reuse its lines or phrases:\nGo gently.")


def test_the_rubric_is_read_fresh_per_church_and_a_bad_one_falls_back(church, make_church):
    other = make_church(name="Other")
    set_settings(other, rubric={"prayers": {"benediction": ["mentions the harbor"]}})
    ai = FakeAI(reply="Draft.")
    set_settings(church, rubric={"prayers": {"benediction": ["ends with the Aaronic blessing"]}})
    run(church, ["benediction"], ai=ai)
    set_settings(church, rubric={"prayers": {"benediction": ["is one sentence"]}})
    run(church, ["benediction"], ai=ai)
    set_settings(church, rubric={"prayers": {"benediction": "not a list"}})
    run(church, ["benediction"], ai=ai)
    first, second, fallback = (user_message(c) for c in ai.calls)
    assert "A good Benediction:\n- ends with the Aaronic blessing" in first
    assert "A good Benediction:\n- is one sentence" in second and "Aaronic" not in second
    assert "A good Benediction:\n- speaks a blessing to the people" in fallback
    assert not any("harbor" in user_message(c) for c in ai.calls)


def test_the_library_is_read_fresh_and_an_empty_one_changes_nothing(church):
    ai = FakeAI(reply="Draft.")
    run(church, ["prayer_of_confession"], ai=ai)
    set_settings(church, prayer_library={"prayers": [], "voice_profile": "   "})
    run(church, ["prayer_of_confession"], ai=ai)
    set_settings(church, prayer_library={"voice_profile": "Plain and warm.", "prayers": [
        {"type": "prayer_of_confession", "text": "Merciful God, {we} confess."},
        {"type": "prayer_of_confession", "text": "Holy One, we have wandered."},
        {"type": "other", "text": "A wedding prayer."}]})
    run(church, ["prayer_of_confession"], ai=ai, choose=lambda texts: texts[-1])
    baseline, empty, voiced = (c["messages"] for c in ai.calls)
    assert empty == baseline
    assert voiced[0]["content"] == baseline[0]["content"] + (
        "\n\nWrite in the voice of this church's pastor, described here:\nPlain and warm.")
    assert voiced[1]["content"] == baseline[1]["content"] + (
        "\n\nFor voice only, here is a Prayer of Confession this pastor wrote. Do not reuse its lines or "
        "phrases:\nHoly One, we have wandered.")


def test_the_sermon_goes_to_every_ai_section_and_no_override(church):
    ai = FakeAI(reply="Draft.")
    outcomes = run(church, ["call_to_worship", "benediction", "assurance"], ai=ai,
                   overrides={"assurance": "Leader: In Christ we are forgiven."},
                   sermon=("Mark 4:35-41", "He said to the sea, Peace! Be still!"))
    block = "Sermon text (Mark 4:35-41), for themes only; do not quote, cite, or name it:\nHe said to the sea"
    assert len(ai.calls) == 2 and all(block in user_message(c) for c in ai.calls)
    assert by_section(outcomes)["assurance"].text == "Leader: In Christ we are forgiven."


def test_the_worst_case_prayers_of_the_people_fits_and_gets_4000_tokens(church):
    """PR #7 §Privacy; index open item 18."""
    set_settings(church,
                 rubric={"prayers": {"prayers_of_the_people": ["p" * 300] * 12}},
                 prayer_library={"voice_profile": "v" * 2000,
                                 "prayers": [{"type": "prayers_of_the_people", "text": "e" * 6000}]})
    ai = FakeAI(reply="Draft.")
    (outcome,) = run(church, ["prayers_of_the_people"], ai=ai, sermon=("Mark 4:35-41", "x" * 20_000),
                     hymns={slot: HymnRefData(hymn_id=None, title="h" * 300, number=100)
                            for slot in ("opening", "response", "closing")})
    (call,) = ai.calls
    assert outcome.status == "generated" and call["max_completion_tokens"] == 4000
    assert sum(len(m["content"]) for m in call["messages"]) <= lp.MAX_PROMPT_CHARS
    assert "e" * 3000 in user_message(call) and "e" * 3001 not in user_message(call)
    assert call["messages"][0]["content"].endswith("v" * 2000)
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy.py 2>&1 | tail -3
```

**Expected:** a collection error, `ImportError: cannot import name 'liturgy' from 'usecases'` (`1 error in <t>s`).

- [ ] **Step 3 (agent): Add the usecase**

**Create `backend/usecases/liturgy.py`:**

````python
"""Liturgy generation, one result per section (slice 4 spec, Backend 3 and its
2026-09-26 amendment; API "POST /liturgy/generate semantics" 1-10; F §1.8, §2.8).

generate_liturgy:
1. Deduplicates the sections (first occurrence kept) and splits them into
   typed ones (a non-blank override) and ones that need the AI.
2. Reads, in one session that closes before any AI call (F §1.8): the slot
   hymns by id, within the church (any id it cannot find is a 404 for the
   whole request); and, only when a section needs the AI, the church's prompt
   overrides, rubric overrides and prayer library, fresh on every call.
3. Typed sections come back as "override" with the text exactly as sent.
4. With no AI configured, each section that needs it is ai_not_configured.
5. Otherwise builds each section's messages (a PromptInvalid is that section's
   prompt_invalid), charges the `ai` bucket once for the sections left
   (charge(n), never with 0; a 429 it raises stops every AI call), and runs
   them at most 4 at a time. AI failures, an empty answer and an answer over
   20 000 characters are per-section errors with this module's messages;
   upstream text is never returned.
6. Returns the outcomes in request order.

Logs one `liturgy.generate` INFO line per call (counts, codes, which optional
blocks were present or dropped, the duration); prompts and outputs only at
DEBUG (F §2.5). Writes nothing. The layer rules are in usecases/__init__.py:
no FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import contextvars
import logging
import random
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Optional, Sequence

import liturgy_prompts
import prayer_library
from db import session_scope
from domain_errors import Busy, DomainError, NotConfigured, NotFound, UpstreamError, UpstreamTimeout
from integrations import openai_client
from liturgy_config import LIMITS, SECTION_LABELS, SECTIONS_BY_KEY
from repos import churches
from repos import hymns as hymn_repo

logger = logging.getLogger(__name__)

HYMN_GONE_MESSAGE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
SECTION_MESSAGES = {
    "ai_not_configured": "AI not configured. Type this section yourself.",
    "ai_busy": "The AI service is busy. Try again in a minute.",
    "ai_timeout": "The AI took too long to answer. Try again.",
    "ai_upstream_error": "The AI service had a problem. Try again.",
}
PROMPT_INVALID_MESSAGE = ("The {label} prompt in Settings has a problem: {reason} "
                          "An admin can fix it under Settings → Liturgy prompts.")
MAX_PARALLEL = 4                               # sections of one request at a time
MAX_ANSWER_CHARS = LIMITS.max_section_text     # a longer answer could not be saved (5a)

Status = Literal["override", "generated", "error"]


@dataclass(frozen=True)
class HymnRefData:
    """One slot's pick as the route received it (api.schemas.HymnRef, without Pydantic)."""
    hymn_id: Optional[uuid.UUID]
    title: str
    number: Optional[int]
    hymnal: Optional[str] = None


@dataclass(frozen=True)
class SectionOutcome:
    section: str
    status: Status
    text: Optional[str]                 # None only when status == "error"
    error_code: Optional[str]
    error_message: Optional[str]


def _override(section: str, text: str) -> SectionOutcome:
    return SectionOutcome(section, "override", text, None, None)


def _error(section: str, code: str, message: Optional[str] = None) -> SectionOutcome:
    return SectionOutcome(section, "error", None, code, message or SECTION_MESSAGES[code])


def _prompt_invalid(section: str, reason: str) -> SectionOutcome:
    return _error(section, "prompt_invalid",
                  PROMPT_INVALID_MESSAGE.format(label=SECTION_LABELS[section], reason=reason))


def dedupe(sections: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(sections))


def sections_needing_ai(sections: Sequence[str], overrides: Mapping[str, str]) -> list[str]:
    """The requested sections (deduplicated, in order) whose override is missing or blank."""
    return [s for s in dedupe(sections) if not (overrides.get(s) or "").strip()]


def _resolved(ref: Optional[HymnRefData], found: Mapping[uuid.UUID, Any]) -> Optional[liturgy_prompts.ResolvedHymn]:
    if ref is None:
        return None
    if ref.hymn_id is None:                                 # an archived snapshot, used as sent
        return liturgy_prompts.ResolvedHymn(ref.title or "", ref.number)
    record = found[ref.hymn_id]
    return liturgy_prompts.ResolvedHymn(record.title or "", record.number)


def _generate_one(ai: Any, section: str, prompt: liturgy_prompts.BuiltPrompt) -> SectionOutcome:
    if logger.isEnabledFor(logging.DEBUG):                 # prompts at DEBUG only (F §2.5)
        logger.debug("liturgy.generate section=%s messages=%r", section, prompt.messages)
    try:
        text = ai.complete(prompt.messages,
                           max_completion_tokens=SECTIONS_BY_KEY[section].max_completion_tokens)
    except NotConfigured:
        return _error(section, "ai_not_configured")
    except Busy:
        return _error(section, "ai_busy")
    except UpstreamTimeout:
        return _error(section, "ai_timeout")
    except UpstreamError:
        return _error(section, "ai_upstream_error")
    except Exception:
        logger.exception("liturgy.generate section=%s unexpected error", section)
        return _error(section, "ai_upstream_error")
    text = text.strip() if isinstance(text, str) else ""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("liturgy.generate section=%s answer=%r", section, text)
    if not text or len(text) > MAX_ANSWER_CHARS:
        logger.warning("liturgy.generate section=%s unusable answer chars=%d", section, len(text))
        return _error(section, "ai_upstream_error")
    return SectionOutcome(section, "generated", text, None, None)


def generate_liturgy(*, church_id: uuid.UUID, user_id: uuid.UUID,
                     occasion: str, scriptures: Sequence[str],
                     hymns: Mapping[str, Optional[HymnRefData]],
                     sections: Sequence[str], overrides: Mapping[str, str],
                     sermon: Optional[tuple[str, str]] = None,
                     charge: Callable[[int], None] = lambda n: None,
                     ai: Any = openai_client,
                     choose: Callable[[Sequence[str]], str] = random.choice) -> list[SectionOutcome]:
    """One outcome per requested section, in request order (see the module
    docstring). user_id is for the rate limit only (the route's charge)."""
    started = time.monotonic()
    wanted = dedupe(sections)
    need_ai = sections_needing_ai(wanted, overrides)
    facts: dict[str, Any] = {"church": church_id, "sections": len(wanted), "ai": 0}
    try:
        outcomes = _generate(church_id, occasion, scriptures, hymns, wanted, need_ai, overrides,
                             sermon, charge, ai, choose, facts)
    except DomainError as exc:
        _log(facts, started, outcome=exc.code)
        raise
    except Exception:
        _log(facts, started, outcome="internal_error")
        raise
    counts = Counter(o.status for o in outcomes)
    codes = Counter(o.error_code for o in outcomes if o.error_code)
    facts["outcomes"] = ",".join(f"{k}:{counts[k]}" for k in ("generated", "override", "error"))
    facts["codes"] = ",".join(f"{code}:{n}" for code, n in sorted(codes.items())) or "-"
    _log(facts, started, outcome="ok")
    return outcomes


def _generate(church_id, occasion, scriptures, hymns, wanted, need_ai, overrides, sermon,
              charge, ai, choose, facts) -> list[SectionOutcome]:
    ids = [ref.hymn_id for ref in hymns.values() if ref is not None and ref.hymn_id is not None]
    stored_prompts: Mapping[str, Any] = {}
    rubric_overrides: Mapping[str, Any] = {}
    library = prayer_library.EMPTY_LIBRARY
    with session_scope() as s:                                   # read, then close (F §1.8)
        found = hymn_repo.get_hymns_by_ids(church_id, ids, session=s) if ids else {}
        if any(hymn_id not in found for hymn_id in ids):
            raise NotFound(HYMN_GONE_MESSAGE)
        if need_ai:
            stored_prompts = churches.get_church_prompts(church_id, session=s)
            rubric_overrides = churches.get_church_rubric_overrides(church_id, session=s)
            church = churches.get_church(church_id, session=s)
            library = prayer_library.read_library((church or {}).get("settings"))
    outcomes = {section: _override(section, overrides[section])
                for section in wanted if section not in need_ai}
    if need_ai and not ai.ai_available():
        outcomes.update({section: _error(section, "ai_not_configured") for section in need_ai})
    elif need_ai:
        sermon_ref, sermon_text = sermon or (None, None)
        ctx = liturgy_prompts.build_context(
            occasion=occasion, scriptures=scriptures,
            hymns_by_slot={slot: _resolved(ref, found) for slot, ref in hymns.items()},
            rubric=rubric_overrides, sermon_ref=sermon_ref, sermon_text=sermon_text)
        prompts = liturgy_prompts.merge_prompts(stored_prompts)
        built: dict[str, liturgy_prompts.BuiltPrompt] = {}
        examples = 0
        for section in need_ai:
            example = prayer_library.choose_example(library, section, choose=choose)
            examples += example is not None
            voice = liturgy_prompts.VoiceContext(profile=library.voice_profile, example=example)
            try:
                built[section] = liturgy_prompts.build_prompt(section, prompts, ctx, voice=voice)
            except liturgy_prompts.PromptInvalid as exc:
                outcomes[section] = _prompt_invalid(section, exc.reason)
        facts.update(
            rubric="custom" if rubric_overrides else "default",
            sermon="yes" if ctx.sermon else "no",
            voice=",".join(name for name, present in (("profile", library.voice_profile.strip()),
                                                      ("example", examples)) if present) or "none",
            dropped=",".join(dict.fromkeys(n for p in built.values() for n in p.dropped)) or "-")
        if built:
            facts["ai"] = len(built)
            charge(len(built))                  # once; a RateLimited here stops every AI call
            with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL, len(built)),
                                    thread_name_prefix="liturgy") as pool:
                futures = {section: pool.submit(contextvars.copy_context().run, _generate_one,
                                                ai, section, prompt)
                           for section, prompt in built.items()}
                outcomes.update({section: future.result() for section, future in futures.items()})
    return [outcomes[section] for section in wanted]


def _log(facts: Mapping[str, Any], started: float, *, outcome: str) -> None:
    """One line per call (S Backend 3 "Logging"): never a prompt, an answer or
    any client text."""
    details = " ".join(f"{key}={value}" for key, value in facts.items())
    logger.info("liturgy.generate %s duration_ms=%d outcome=%s", details,
                round((time.monotonic() - started) * 1000), outcome)
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "liturgy_config, prayer_library, liturgy_prompts; "
````

**with:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy; "
````

- [ ] **Step 4 (agent): Run the tests three times (threads), and the suite**

```bash
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy.py 2>&1 | tail -1; done
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `14 passed in <t>s` three times; `1165 passed, 11 skipped in <t>s`; then exactly ` M backend/tests/test_no_streamlit_in_core.py`, `?? backend/tests/test_usecase_liturgy.py`, `?? backend/usecases/liturgy.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/usecases/liturgy.py backend/tests/test_usecase_liturgy.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Liturgy: generate_liturgy, one result per section (S Backend 3; API semantics 1-10)" -m "Typed sections come back exactly as sent; with no AI the rest say AI not
configured. Hymns resolve within the church (any other id is the 404); the
prompts, rubric and prayer library are read fresh in the same session,
closed before any AI call. A bad template fails only its own section. The
ai bucket is charged once, only for sections that reach the AI, and at most
4 run at a time. AI failures are per-section errors with S's messages; no
upstream text is returned. One liturgy.generate line per call, no prompt
text at INFO." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

Check against S API semantics 1-10: `charge` is called after hymn resolution and after every `build_prompt`, once, never with 0; the session closes before the pool starts; the messages equal S's table. `grep -n "logger\." backend/usecases/liturgy.py`: the DEBUG prompt and answer lines, the `logger.exception` for an unexpected error (no message text), the unusable-answer WARNING (length only) and the one INFO line (counts and ids only). Push the backup.

Counts after Task 7: backend **1165 passed, 11 skipped**; frontend **442 in 64**.

### Task 8: `GET /liturgy/config` and `POST /liturgy/generate` (S API routes, Schemas, "Deviation from F"; Backend 4; Testing `test_api_liturgy.py`, "Guard and contract"; AC1, AC4, AC5, AC7, AC8; clarifications 14, 17, 22)

**Files:**
- Create: `backend/api/routes/liturgy.py`, `backend/tests/test_api_liturgy.py`
- Modify: `backend/api/schemas.py` (`SermonText`), `backend/api/main.py`, `backend/tests/test_route_guards.py`, `backend/tests/test_api_app.py`, `backend/tests/test_schemas.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (generated)

**Interfaces:**
- Consumes: `usecases.liturgy.generate_liturgy`, `HymnRefData` (T7); `liturgy_config` (T1); `api.schemas.SectionKey`, `SlotHymns`, `HymnRef` (3a); `api.ratelimit.consume`; `api.deps.require_church`, `get_current_user`; `openai_client.ai_available`.
- Produces (later users: 4b's `useLiturgyConfig`, `generateSection`; the reviewer add-on's `SermonText`):
  - `api.schemas.SermonText(ref ≤ 200, text ≤ 20 000)`, `extra="forbid"`
  - route models (top of `routes/liturgy.py`): `GenerateLiturgyIn`, `SectionError`, `SectionResult`, `GenerateLiturgyOut`, `SectionSpecOut`, `PlacementOut`, `OutlineItemOut`, `CommunionBlockOut`, `CommunionOut`, `LiturgyLimitsOut`, `LiturgyConfigOut` (S Schemas, field for field)
  - `GET /liturgy/config` (user) → 200 `LiturgyConfigOut`; `POST /liturgy/generate` (church) → 200 `GenerateLiturgyOut`, 404 hymn, 422, 429

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_api_liturgy.py`:**

````python
"""GET /liturgy/config and POST /liturgy/generate (slice 4 spec, API; Testing
`test_api_liturgy.py`; AC1, AC4, AC5, AC7, AC8). The AI is a FakeAI
(integrations.openai_client.set_ai_for_tests)."""
import logging
import uuid

import pytest

import liturgy_config
from api import ratelimit
from db import session_scope
from db.models import Hymn
from integrations import openai_client
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
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Grace", owner_user_id=owner)


def install(reply="Draft.", **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def add_hymn(church_id, title="Holy, Holy, Holy", number=138):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal="GG2013", title=title, number=number)
        s.add(row)
        s.flush()
        return str(row.id)


def generate(client, church_id, body, email=EMAIL, status=200):
    r = client.post("/liturgy/generate", json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_config_is_user_scoped(client, owner):
    assert client.get("/liturgy/config").status_code == 401
    r = client.get("/liturgy/config", headers=auth_headers(EMAIL))           # no X-Church-Id
    assert r.status_code == 200, r.text


def test_config_serves_liturgy_config(client, owner):
    body = client.get("/liturgy/config", headers=auth_headers(EMAIL)).json()
    assert [s["key"] for s in body["sections"]] == liturgy_config.SECTION_ORDER
    assert body["sections"][5] == {"key": "prayers_of_the_people", "label": "Prayers of the People",
                                   "default_enabled": False, "rows": 8, "pastor_copy_only": True, "hint": None}
    assert [(p["key"], p["label"]) for p in body["custom_placements"]] == list(liturgy_config.CUSTOM_PLACEMENTS)
    assert body["outline"] == liturgy_config.outline_as_json() and len(body["outline"]) == 16
    assert body["assurance_response"] == "People: Thanks be to God! Amen."
    assert body["default_benediction_fallback"] == "Halverson"
    assert body["communion"]["default_rule"] == "first_sunday_of_month"
    assert body["communion"]["toggle_label"] == "Include communion liturgy (The Sacrament of the Lord's Supper)"
    assert len(body["communion"]["blocks"]) == len(liturgy_config.COMMUNION_BLOCKS)
    assert body["limits"] == {"max_section_text": 20_000, "max_sermon_title": 300, "max_custom_elements": 30,
                              "max_custom_label": 200, "max_custom_text": 10_000, "max_sections_per_request": 4}
    assert body["ai_available"] is False                   # no key in tests
    install()
    assert client.get("/liturgy/config", headers=auth_headers(EMAIL)).json()["ai_available"] is True


def test_generate_mixes_overrides_answers_and_errors_in_one_200(client, church):
    churches.set_church_prompts(church, {"opening_prayer": "{"})
    install(reply="  A generated call.  ")
    body = generate(client, church, {
        "occasion": "Third Sunday of Easter", "scriptures": ["Acts 9:1-6"],
        "sections": ["call_to_worship", "benediction", "opening_prayer", "call_to_worship"],
        "overrides": {"benediction": " Go in peace. ", "assurance": "not requested"},
    })
    assert body == {"results": [
        {"section": "call_to_worship", "status": "generated", "text": "A generated call.", "error": None},
        {"section": "benediction", "status": "override", "text": " Go in peace. ", "error": None},
        {"section": "opening_prayer", "status": "error", "text": None, "error": {
            "code": "prompt_invalid",
            "message": "The Opening Prayer prompt in Settings has a problem: It has a { or } without a "
                       "partner. Use {{ or }} to print a brace. An admin can fix it under Settings → "
                       "Liturgy prompts."}},
    ]}


def test_without_ai_a_typed_section_still_comes_back(client, church):
    """F acceptance 15 through the API: 200, override verbatim, ai_not_configured."""
    body = generate(client, church, {"sections": ["benediction", "call_to_worship"],
                                     "overrides": {"benediction": "Go in peace."}})
    assert [(r["status"], r["text"], r["error"]) for r in body["results"]] == [
        ("override", "Go in peace.", None),
        ("error", None, {"code": "ai_not_configured", "message": "AI not configured. Type this section yourself."}),
    ]


def test_generate_needs_a_token_and_a_membership(client, church, isolation_world, make_user):
    assert client.post("/liturgy/generate", json={"sections": ["benediction"]}).status_code == 401
    world = isolation_world
    install()
    assert_church_isolated(client, "POST", "/liturgy/generate", world=world, json={"sections": ["benediction"]})
    theirs = add_hymn(world.church_b)
    r = client.post("/liturgy/generate", headers=church_headers(world.a, world.church_a),
                    json={"sections": ["benediction"], "hymns": {"opening": {"hymn_id": theirs, "title": "x"}}})
    assert (r.status_code, r.json()["error"]["code"], r.json()["error"]["message"]) == (404, "not_found", HYMN_GONE)
    for role in ("member", "admin"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), church, role)
        assert generate(client, church, {"sections": ["benediction"]}, email=email)["results"][0]["status"] == \
            "generated"
    assert generate(client, church, {"sections": ["benediction"]})["results"][0]["status"] == "generated"


def test_invalid_bodies_are_422_with_fields(client, church):
    cases = [
        ({"sections": ["offering"]}, "sections.0"),
        ({"sections": ["benediction"] * 5}, "sections"),
        ({"sections": []}, "sections"),
        ({}, "sections"),
        ({"sections": ["benediction"], "extra": 1}, "extra"),
        ({"sections": ["benediction"], "church_id": str(uuid.uuid4())}, "church_id"),
        ({"sections": ["benediction"], "occasion": "o" * 301}, "occasion"),
        ({"sections": ["benediction"], "scriptures": ["Mark 1"] * 21}, "scriptures"),
        ({"sections": ["benediction"], "scriptures": ["r" * 201]}, "scriptures.0"),
        ({"sections": ["benediction"], "overrides": {"benediction": "x" * 20_001}}, "overrides.benediction"),
        ({"sections": ["benediction"], "overrides": {"offering": "x"}}, "overrides.offering.[key]"),
        ({"sections": ["benediction"], "hymns": {"opening": {"title": "t" * 301}}}, "hymns.opening.title"),
        ({"sections": ["benediction"], "hymns": {"opening": {"number": -1}}}, "hymns.opening.number"),
        ({"sections": ["benediction"], "hymns": {"opening": {"title": "x", "slot": "opening"}}},
         "hymns.opening.slot"),
        ({"sections": ["benediction"], "hymns": {"opening": {"hymnal": "H" * 21}}}, "hymns.opening.hymnal"),
        ({"sections": ["benediction"], "hymns": {"offertory": None}}, "hymns.offertory"),
        ({"sections": ["benediction"], "sermon_text": {"ref": "r" * 201, "text": "x"}}, "sermon_text.ref"),
        ({"sections": ["benediction"], "sermon_text": {"ref": "Mark 4", "text": "x" * 20_001}}, "sermon_text.text"),
        ({"sections": ["benediction"], "sermon_text": {"ref": "Mark 4", "text": "x", "translation": "esv"}},
         "sermon_text.translation"),
    ]
    for body, field in cases:
        r = client.post("/liturgy/generate", json=body, headers=church_headers(EMAIL, church))
        assert r.status_code == 422, (body, r.text)
        error = r.json()["error"]
        assert error["code"] == "invalid_request" and field in error["fields"], (field, error)


def test_hymn_ref_and_sermon_text_accept_what_f_1_3_allows(client, church):
    install()
    for hymn in ({"hymn_id": None, "title": "t" * 300}, {"title": "Old", "hymnal": "H"},
                 {"title": "Old", "hymnal": "old code", "number": 0}):
        generate(client, church, {"sections": ["benediction"], "hymns": {"closing": hymn}})
    generate(client, church, {"sections": ["benediction"],
                              "sermon_text": {"ref": "r" * 200, "text": "x" * 20_000}})
    generate(client, church, {"sections": ["benediction"]})        # sermon_text is optional (additive)


def test_the_41st_ai_section_in_ten_minutes_is_429(client, church, owner, limiter_clock):
    install()
    for _ in range(36):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    four = ["call_to_worship", "opening_prayer", "assurance", "benediction"]
    assert len(generate(client, church, {"sections": four})["results"]) == 4        # sections 37-40
    r = client.post("/liturgy/generate", json={"sections": ["benediction"]}, headers=church_headers(EMAIL, church))
    assert (r.status_code, r.json()["error"]["code"], r.headers["Retry-After"]) == (429, "rate_limited", "15")
    limiter_clock.advance(15)
    generate(client, church, {"sections": ["benediction"]})


def test_only_sections_that_reach_the_ai_are_charged(client, church, owner, limiter_clock):
    for _ in range(40):                                        # the user's bucket is empty
        ratelimit.consume("ai", user_id=owner, church_id=church)
    generate(client, church, {"sections": ["benediction"], "overrides": {"benediction": "Go."}})
    generate(client, church, {"sections": ["benediction"]})                        # AI not configured
    install()
    generate(client, church, {"sections": ["benediction"], "hymns": {"opening": {"hymn_id": str(uuid.uuid4())}}},
             status=404)
    churches.set_church_prompts(church, {"benediction": "{0}"})
    body = generate(client, church, {"sections": ["benediction"]})                 # only prompt_invalid
    assert body["results"][0]["error"]["code"] == "prompt_invalid"
    r = client.post("/liturgy/generate", json={"sections": ["assurance"]}, headers=church_headers(EMAIL, church))
    assert r.status_code == 429                                  # one that reaches the AI is charged


def test_info_logs_carry_no_prompt_or_answer(client, church, caplog):
    install(reply="SECRET-ANSWER words")
    churches.set_church_prompts(church, {"benediction": "SECRET-PROMPT {occasion}"})
    with caplog.at_level(logging.INFO):
        generate(client, church, {"occasion": "SECRET-OCCASION", "sections": ["benediction", "assurance"],
                                  "overrides": {"assurance": "SECRET-TYPED"},
                                  "sermon_text": {"ref": "Mark 4:35-41", "text": "SECRET-SERMON"}})
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.generate" in info and "outcomes=generated:1,override:1,error:0" in info
    assert "sermon=yes" in info and "outcome=ok" in info
    assert "SECRET" not in info
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
(1b: POST /churches, POST /invites/preview, POST /invites/accept;
2a: GET /lectionary/readings, POST /scripture/passages, GET /translations).
````

**with:**

````python
(1b: POST /churches, POST /invites/preview, POST /invites/accept;
2a: GET /lectionary/readings, POST /scripture/passages, GET /translations;
4a: GET /liturgy/config).
````

**In `backend/tests/test_route_guards.py`, replace:**

````python
    ("POST", "/scripture/passages"),
}
````

**with:**

````python
    ("POST", "/scripture/passages"),
    ("GET", "/liturgy/config"),
}
````

**In `backend/tests/test_api_app.py`, replace:**

````python
        ("/hymns/suggestions", "post"): {"401", "403", "422", "429", "502", "503", "504"},
    }
````

**with:**

````python
        ("/hymns/suggestions", "post"): {"401", "403", "422", "429", "502", "503", "504"},
        ("/liturgy/config", "get"): {"401", "422", "503"},
        ("/liturgy/generate", "post"): {"401", "403", "404", "422", "429", "503"},
    }
````

**In `backend/tests/test_schemas.py`, replace:**

````python
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

**with:**

````python
def test_hymnal_code_pattern_and_models_in_openapi_unchanged():
    code = TypeAdapter(HymnalCode)
    assert code.validate_python("GG2013") == "GG2013"
    for bad in ("PH 1990", "X", "G" * 21):
        with pytest.raises(ValidationError):
            code.validate_python(bad)
    # Slice 4's POST /liturgy/generate is the first route that accepts them; they
    # enter the snapshot with the frozen shape (F §1.3): no pattern on hymnal.
    schemas = create_app().openapi()["components"]["schemas"]
    assert {"HymnRef", "SlotHymns"} <= set(schemas)
    hymnal = schemas["HymnRef"]["properties"]["hymnal"]
    assert "pattern" not in str(hymnal) and "maxLength" in str(hymnal)
    assert schemas["HymnRef"]["additionalProperties"] is False
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_liturgy.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_schemas.py 2>&1 | tail -3
```

**Expected:** `14 failed, 34 passed, 1 skipped in <t>s`: all ten `test_api_liturgy.py` tests (the paths do not exist yet, so every call answers 404), `test_user_scoped_routes_require_a_user` and `test_allowlists_name_real_routes` (`("GET", "/liturgy/config")` is not served), `test_routes_document_the_error_body` (`KeyError` for the missing path) and the renamed snapshot test (the models are absent).

- [ ] **Step 3 (agent): Add `SermonText`, the routes and the router**

**Append to `backend/api/schemas.py`:**

````python


# --- slice 4a: the sermon text sent with liturgy requests (F §1.3 amendment
# 2026-09-26; shared with the reviewer add-on's /liturgy/review and /liturgy/revise) ---

class SermonText(BaseModel):
    """The effective NT reading and its passage text (never ESV); the server keeps
    the first 2 000 characters (liturgy_prompts.SERMON_TEXT_LIMIT)."""

    model_config = ConfigDict(extra="forbid")

    ref: str = Field(max_length=200)
    text: str = Field(max_length=20_000)
````

**Create `backend/api/routes/liturgy.py`:**

````python
"""The Liturgy step's routes (slice 4 spec, API; Backend 4).

- GET /liturgy/config (user-scoped, F §1.1): the sections, custom placements,
  order of worship, communion text and limits from liturgy_config, and
  whether AI is set up (never why).
- POST /liturgy/generate (church-scoped): one result per requested section.
  AI and prompt failures come back per section inside the 200 (the declared
  deviation from F §1.5, §1.8 and §2.8); the request-level errors (401, 403,
  404 for a hymn id, 422, 429) stay HTTP errors. The usecase charges the `ai`
  bucket through `charge`, only for sections that reach the AI.

Plain `def` routes (F §1.8), no SQL and no try/except (F §2.2 rule 1).
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

import liturgy_config
from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.schemas import SectionKey, SermonText, SlotHymns
from integrations import openai_client
from usecases import liturgy

router = APIRouter()


class GenerateLiturgyIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion: str = Field("", max_length=300)
    scriptures: list[Annotated[str, Field(max_length=200)]] = Field(default_factory=list, max_length=20)
    hymns: SlotHymns = Field(default_factory=SlotHymns)
    sections: list[SectionKey] = Field(min_length=1, max_length=4)      # the UI sends exactly 1
    overrides: dict[SectionKey, Annotated[str, Field(max_length=20_000)]] = Field(default_factory=dict)
    sermon_text: Optional[SermonText] = None     # the effective NT reading and its text, never ESV


class SectionError(BaseModel):
    code: Literal["ai_not_configured", "ai_busy", "ai_timeout", "ai_upstream_error", "prompt_invalid"]
    message: str


class SectionResult(BaseModel):
    section: SectionKey
    status: Literal["override", "generated", "error"]
    text: Optional[str]            # None only when status == "error"
    error: Optional[SectionError]


class GenerateLiturgyOut(BaseModel):
    results: list[SectionResult]   # one per requested section, request order, duplicates removed


class SectionSpecOut(BaseModel):
    key: SectionKey
    label: str
    default_enabled: bool
    rows: int
    pastor_copy_only: bool
    hint: Optional[str]


class PlacementOut(BaseModel):
    key: str
    label: str


class OutlineItemOut(BaseModel):
    kind: Literal["section", "landmark", "communion"]
    key: str                        # a section key, or a landmark key (first_hymn, ot_reading, ...)
    label: str                      # the docx heading text (the first reading's is 5a's "First Reading")
    value_source: Literal["none", "hymn_opening", "hymn_response", "hymn_closing",
                          "reading_ot", "reading_nt", "sermon_title", "fixed"]
    fixed_text: Optional[str]       # "Apostles' Creed" for affirmation_of_faith
    anchors_after: list[str]        # placement keys whose custom elements follow this item


class CommunionBlockOut(BaseModel):
    style: Literal["heading1", "heading2", "text", "response", "blank"]
    text: str


class CommunionOut(BaseModel):
    title: str
    toggle_label: str
    default_rule: Literal["first_sunday_of_month"]
    blocks: list[CommunionBlockOut]


class LiturgyLimitsOut(BaseModel):
    max_section_text: int
    max_sermon_title: int
    max_custom_elements: int
    max_custom_label: int
    max_custom_text: int
    max_sections_per_request: int


class LiturgyConfigOut(BaseModel):
    sections: list[SectionSpecOut]          # SECTION_ORDER
    custom_placements: list[PlacementOut]   # the 17, in app.py's order
    outline: list[OutlineItemOut]
    assurance_response: str                 # "People: Thanks be to God! Amen."
    default_benediction_fallback: str       # "Halverson"
    communion: CommunionOut
    limits: LiturgyLimitsOut
    ai_available: bool                      # openai_client.ai_available(); never why


@router.get("/liturgy/config", response_model=LiturgyConfigOut, responses=error_responses(401, 422, 503))
def get_liturgy_config(user: CurrentUser = Depends(get_current_user)) -> LiturgyConfigOut:
    lc = liturgy_config
    return LiturgyConfigOut(
        sections=[SectionSpecOut(key=s.key, label=s.label, default_enabled=s.default_enabled, rows=s.rows,
                                 pastor_copy_only=s.pastor_copy_only, hint=s.hint) for s in lc.SECTIONS],
        custom_placements=[PlacementOut(key=key, label=label) for key, label in lc.CUSTOM_PLACEMENTS],
        outline=[OutlineItemOut(**item) for item in lc.outline_as_json()],
        assurance_response=lc.ASSURANCE_RESPONSE,
        default_benediction_fallback=lc.DEFAULT_BENEDICTION_FALLBACK,
        communion=CommunionOut(title=lc.COMMUNION_TITLE, toggle_label=lc.COMMUNION_TOGGLE_LABEL,
                               default_rule="first_sunday_of_month",
                               blocks=[CommunionBlockOut(style=b.style, text=b.text) for b in lc.COMMUNION_BLOCKS]),
        limits=LiturgyLimitsOut(**vars(lc.LIMITS)),
        ai_available=openai_client.ai_available(),
    )


def _hymn(ref) -> Optional[liturgy.HymnRefData]:
    if ref is None:
        return None
    return liturgy.HymnRefData(hymn_id=ref.hymn_id, title=ref.title, number=ref.number, hymnal=ref.hymnal)


@router.post("/liturgy/generate", response_model=GenerateLiturgyOut,
             responses=error_responses(401, 403, 404, 422, 429, 503))
def generate_liturgy(payload: GenerateLiturgyIn, church: ActiveChurch = Depends(require_church),
                     user: CurrentUser = Depends(get_current_user)) -> GenerateLiturgyOut:
    """Typed text comes back as sent; the rest is written by the AI, at most 4
    sections at a time. Charged to the `ai` bucket per section that reaches the
    AI (40 per 10 min per user, 400 per day per church; F §1.8)."""
    sermon = (payload.sermon_text.ref, payload.sermon_text.text) if payload.sermon_text else None
    outcomes = liturgy.generate_liturgy(
        church_id=church.id, user_id=user.id, occasion=payload.occasion, scriptures=payload.scriptures,
        hymns={slot: _hymn(getattr(payload.hymns, slot)) for slot in ("opening", "response", "closing")},
        sections=payload.sections, overrides=payload.overrides, sermon=sermon,
        charge=lambda n: ratelimit.consume("ai", user_id=user.id, church_id=church.id, cost=n))
    return GenerateLiturgyOut(results=[
        SectionResult(section=o.section, status=o.status, text=o.text,
                      error=SectionError(code=o.error_code, message=o.error_message) if o.error_code else None)
        for o in outcomes])
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, me, reference, rubric,
                        scripture)
````

**with:**

````python
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, liturgy, me, reference,
                        rubric, scripture)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(hymns.router)
    return app
````

**with:**

````python
    app.include_router(hymns.router)
    app.include_router(liturgy.router)
    return app
````

- [ ] **Step 4 (agent): Regenerate the OpenAPI files, then run the tests and the suite**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null && npm run typecheck && npm test 2>&1 | grep -E "Test Files|Tests ")
.venv/bin/python -m pytest -q backend/tests/test_api_liturgy.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_schemas.py backend/tests/test_openapi_contract.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `Wrote .../frontend/src/lib/api/openapi.json`, `tsc` prints nothing after its header, ` Test Files  64 passed (64)` and `      Tests  442 passed (442)`; `54 passed, 1 skipped in <t>s`; `1175 passed, 11 skipped in <t>s`; then exactly ` M backend/api/main.py`, ` M backend/api/schemas.py`, ` M backend/tests/test_api_app.py`, ` M backend/tests/test_route_guards.py`, ` M backend/tests/test_schemas.py`, ` M frontend/src/lib/api/openapi.json`, ` M frontend/src/lib/api/schema.d.ts`, `?? backend/api/routes/liturgy.py`, `?? backend/tests/test_api_liturgy.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/api/routes/liturgy.py backend/api/schemas.py backend/api/main.py backend/tests/test_api_liturgy.py backend/tests/test_route_guards.py backend/tests/test_api_app.py backend/tests/test_schemas.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "API: GET /liturgy/config and POST /liturgy/generate (S API; AC1, AC4, AC5, AC7, AC8)" -m "The config route is user-scoped (USER_SCOPED gains it) and serves
liturgy_config plus ai_available. The generate route is church-scoped and
returns one result per section inside a 200 (the declared deviation from F),
with 404 for a hymn outside the church, 422 for bad bodies and 429 from the
ai bucket, charged only for sections that reach the AI. SermonText joins
api/schemas.py. HymnRef and SlotHymns enter the OpenAPI snapshot unchanged;
openapi.json and schema.d.ts regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

Check the route models field for field against S Schemas, that neither route has a `try`, SQL or a second usecase call, and that `schema.d.ts` gains `LiturgyConfigOut`, `GenerateLiturgyIn`, `GenerateLiturgyOut`, `SectionResult`, `SectionError`, `SermonText`, `HymnRef` and `SlotHymns`. Push the backup.

Counts after Task 8: backend **1175 passed, 11 skipped**; frontend **442 in 64**.

### Task 9: `GET /church` gains `default_benediction` (S API row 3, Backend 5; Testing "GET /church"; AC9; clarification 18)

**Files:**
- Modify: `backend/usecases/church_profile.py`, `backend/api/schemas.py`, `backend/tests/test_api_church_profile.py`, `backend/tests/test_api_me.py`, `backend/tests/test_api_invites.py`, `backend/tests/test_api_churches.py`, `frontend/src/test/fixtures/index.ts`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (generated)

**Interfaces:**
- Consumes: `liturgy_config.resolve_default_benediction` (T1); the church row `get_church_profile` already reads.
- Produces (later users: 4b's `applyLiturgyDefaults`, 6a): `ChurchProfile.default_benediction: str`, `ChurchProfileOut.default_benediction: str` ("Halverson" when unset or not a string; `""` kept).

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_api_church_profile.py`:**

````python


def test_default_benediction_is_the_church_s_or_halverson(client, make_user, make_church):
    """Slice 4 (S API; Backend 5; AC9): "" is a stored value meaning no default."""
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    assert _profile(client, cid)["default_benediction"] == "Halverson"
    for stored, expected in (("May the Lord bless you and keep you.", "May the Lord bless you and keep you."),
                             ("", ""), (5, "Halverson")):
        churches.update_church(cid, settings={"default_benediction": stored})
        assert _profile(client, cid)["default_benediction"] == expected, stored
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````python
        "default_hymnal": None,
        "effective_hymnal": None,
    }
````

**with:**

````python
        "default_hymnal": None,
        "effective_hymnal": None,
        "default_benediction": "Halverson",
    }
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````python
        "effective_translation", "effective_translation_label", "default_hymnal", "effective_hymnal"}
````

**with:**

````python
        "effective_translation", "effective_translation_label", "default_hymnal", "effective_hymnal",
        "default_benediction"}
````

**In `backend/tests/test_api_me.py`, replace:**

````python
        "default_hymnal": None, "effective_hymnal": None,     # slice 3: no hymns in this church
    }
````

**with:**

````python
        "default_hymnal": None, "effective_hymnal": None,     # slice 3: no hymns in this church
        "default_benediction": "Halverson",                   # slice 4: the fallback
    }
````

**In `backend/tests/test_api_invites.py`, replace:**

````python
        "default_hymnal": None, "effective_hymnal": None,     # slice 3: no hymns in this church
    }
````

**with:**

````python
        "default_hymnal": None, "effective_hymnal": None,     # slice 3: no hymns in this church
        "default_benediction": "Halverson",                   # slice 4: the fallback
    }
````

**In `backend/tests/test_api_churches.py`, replace:**

````python
        "default_hymnal": None, "effective_hymnal": "GG2013",  # slice 3: the seeded catalog is GG2013
    }
````

**with:**

````python
        "default_hymnal": None, "effective_hymnal": "GG2013",  # slice 3: the seeded catalog is GG2013
        "default_benediction": "Halverson",                    # slice 4: the fallback
    }
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_church_profile.py backend/tests/test_api_me.py backend/tests/test_api_invites.py backend/tests/test_api_churches.py 2>&1 | tail -1
```

**Expected:** `6 failed, 62 passed in <t>s` (the five exact-body or required-field tests and the new one).

- [ ] **Step 3 (agent): Add the field, regenerate, and fix the frontend fixture**

**In `backend/usecases/church_profile.py`, replace:**

````python
Slice 3 added default_hymnal and effective_hymnal; slice 4 adds its fields
to ChurchProfile (and ChurchProfileOut) additively.
````

**with:**

````python
Slice 3 added default_hymnal and effective_hymnal; slice 4 added
default_benediction (to ChurchProfile and ChurchProfileOut, additively).
````

**In `backend/usecases/church_profile.py`, replace:**

````python
import scripture_fetcher
from db import session_scope
````

**with:**

````python
import scripture_fetcher
from db import session_scope
from liturgy_config import resolve_default_benediction
````

**In `backend/usecases/church_profile.py`, replace:**

````python
    effective_hymnal: str | None         # slice 3: the hymnal the builder opens (GET /hymnals agrees)
````

**with:**

````python
    effective_hymnal: str | None         # slice 3: the hymnal the builder opens (GET /hymnals agrees)
    default_benediction: str             # slice 4: settings["default_benediction"] when a string, else "Halverson"
````

**In `backend/usecases/church_profile.py`, replace:**

````python
      read in the same session (slice 3).
````

**with:**

````python
      read in the same session (slice 3).
    - default_benediction: liturgy_config.resolve_default_benediction(settings)
      ("" is kept: a church with no default; slice 4).
````

**In `backend/usecases/church_profile.py`, replace:**

````python
        effective_hymnal=hymnals.effective_hymnal,
    )
````

**with:**

````python
        effective_hymnal=hymnals.effective_hymnal,
        default_benediction=resolve_default_benediction(church["settings"]),
    )
````

**In `backend/api/schemas.py`, replace:**

````python
    effective_hymnal: Optional[str]         # slice 3: the hymnal the builder opens; null with no hymns
````

**with:**

````python
    effective_hymnal: Optional[str]         # slice 3: the hymnal the builder opens; null with no hymns
    default_benediction: str                # slice 4: the church's default, "Halverson" when unset; "" = none
````

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null && npm run typecheck 2>&1 | grep -c "default_benediction")
```

**Expected:** `Wrote .../openapi.json`, then `2`: `tsc` fails on the one fixture that builds a `ChurchProfile` (clarification 18).

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
/** `GET /church` for Grace (`ChurchProfileOut`, slices 2a and 3a): New York, WEB, GG2013. */
````

**with:**

````ts
/** `GET /church` for Grace (`ChurchProfileOut`, slices 2a, 3a and 4a): New York, WEB, GG2013, Halverson. */
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
    effective_translation_label: "World English Bible (WEB)",
    default_hymnal: null,
    effective_hymnal: "GG2013",
````

**with:**

````ts
    effective_translation_label: "World English Bible (WEB)",
    default_hymnal: null,
    effective_hymnal: "GG2013",
    default_benediction: "Halverson",
````

- [ ] **Step 4 (agent): Run the tests, the frontend and the suite**

```bash
(cd frontend && npm run typecheck && npm run lint && npm test 2>&1 | grep -E "Test Files|Tests ")
.venv/bin/python -m pytest -q backend/tests/test_api_church_profile.py backend/tests/test_api_me.py backend/tests/test_api_invites.py backend/tests/test_api_churches.py backend/tests/test_openapi_contract.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `tsc` and `eslint` print nothing after their headers; ` Test Files  64 passed (64)`, `      Tests  442 passed (442)`; `71 passed in <t>s`; `1176 passed, 11 skipped in <t>s`; then exactly the six backend files, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` and `frontend/src/test/fixtures/index.ts` as ` M`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/usecases/church_profile.py backend/api/schemas.py backend/tests/test_api_church_profile.py backend/tests/test_api_me.py backend/tests/test_api_invites.py backend/tests/test_api_churches.py frontend/src/test/fixtures/index.ts frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "API: GET /church returns default_benediction (S Backend 5, AC9)" -m "The church's settings[\"default_benediction\"] when it is a string (\"\" is a
church with no default), else Halverson, read from the row the profile
already loads. Additive; the frontend's churchProfile() fixture gains the
field because the regenerated type requires it (plan clarification 18)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint (end of batch C) and backup push**

Review T7-T9 together: the `/liturgy/generate` isolation test covers both the 403 and the other church's hymn 404 with S's message; the route charges through `charge` only; `GET /church` still reads one session. Push the backup.

Counts after Task 9: backend **1176 passed, 11 skipped**; frontend **442 in 64**.

### Task 10: Retarget PR #4's tests, then delete `generate_liturgy` (S Backend 6 `worship_service.py`, "Streamlit coupling removed"; Testing amendment "Characterization (PR #4)"; AC19; BC-6, BC-16; owner decision 2; clarifications 2, 12)

PR #4's `test_generate_liturgy.py` is rewritten against `build_context`/`build_messages` and the usecase, keeping every assertion and the 12 test cases. The oracle test in `test_liturgy_generation.py` gives way to a test that the old function and its UI-shaped strings are gone, which fails until the deletion. Then `generate_liturgy`, `_sermon_text_block`, `SERMON_TEXT_LIMIT`, the `openai` import and the imports only they used leave `worship_service.py`. Frozen `app.py` on `main` imports `generate_liturgy` and stops importing (accepted).

**Files:**
- Modify: `backend/tests/test_generate_liturgy.py` (rewritten), `backend/tests/test_liturgy_generation.py` (rewritten), `backend/tests/test_hymn_match_parity.py`, `backend/worship_service.py`

**Interfaces:**
- Consumes: `liturgy_prompts` (T5), `usecases.liturgy.generate_liturgy` (T7), `integrations.openai_client.FakeAI`.
- Produces: `worship_service` without `generate_liturgy`, `_sermon_text_block`, `SERMON_TEXT_LIMIT` and `OpenAI`; `build_docx` unchanged.

- [ ] **Step 1 (agent): Retarget PR #4's tests (they pass on the new code)**

This replaces the whole file:

**Create `backend/tests/test_generate_liturgy.py`:**

````python
"""PR #4's liturgy tests (the rubric checklist and the sermon text), retargeted
from worship_service.generate_liturgy to liturgy_prompts.build_context /
build_messages and usecases.liturgy before that function was deleted (slice 4
spec, Testing amendment "Characterization (PR #4)"; AC19). Each case keeps its
assertion."""
import uuid

import pytest

import liturgy_prompts
from integrations.openai_client import FakeAI
from service_rubric import default_rubric
from usecases import liturgy

SLOTS = {"opening": liturgy_prompts.ResolvedHymn("Holy, Holy, Holy", 138)}


def generate(sections, *, rubric=None, prompt_overrides=None, sermon_text=None):
    """The messages each section would send, as generate_liturgy's fake client recorded them."""
    ref, text = sermon_text or (None, None)
    ctx = liturgy_prompts.build_context(
        occasion="Third Sunday of Easter", scriptures=["Acts 9:1-6", "John 21:1-19"],
        hymns_by_slot=SLOTS, rubric=rubric, sermon_ref=ref, sermon_text=text)
    prompts = liturgy_prompts.merge_prompts(prompt_overrides)
    return [liturgy_prompts.build_messages(section, prompts, ctx) for section in sections]


def user_message(messages):
    return messages[1]["content"]


def test_each_section_gets_its_default_checklist():
    benediction, confession = generate(["benediction", "prayer_of_confession"])
    assert "A good Benediction:\n- speaks a blessing to the people" in user_message(benediction)
    assert "A good Prayer of Confession:\n- names real, specific failings that are common to all people" in \
        user_message(confession)
    assert benediction[0]["content"] == liturgy_prompts.DEFAULT_SYSTEM_PROMPT


def test_a_church_rubric_replaces_the_checklist():
    rubric = default_rubric()
    rubric["prayers"]["benediction"] = ["ends with the Aaronic blessing"]
    (messages,) = generate(["benediction"], rubric=rubric)
    text = user_message(messages)
    assert "A good Benediction:\n- ends with the Aaronic blessing" in text
    assert "speaks a blessing to the people" not in text


@pytest.mark.parametrize("rubric", [{}, {"hymns": {"closing": ["Joyful."]}}])
def test_a_partial_rubric_falls_back_to_the_defaults(rubric):
    # A church's sparse overrides ({} when nothing is customized) are filled in
    # from the defaults rather than raising KeyError.
    (messages,) = generate(["benediction"], rubric=rubric)
    assert "A good Benediction:\n- speaks a blessing to the people" in user_message(messages)


def test_edited_prompts_still_get_the_checklist():
    (messages,) = generate(["benediction"], prompt_overrides={"benediction": "My own benediction instruction."})
    text = user_message(messages)
    assert text.startswith("My own benediction instruction.")
    assert "A good Benediction:" in text


def test_sermon_text_is_appended_for_themes_only():
    (messages,) = generate(["prayer_of_confession"],
                           sermon_text=("John 21:1-19", "Simon Peter said, I am going fishing."))
    assert ("Sermon text (John 21:1-19), for themes only; do not quote, cite, or name it:\n"
            "Simon Peter said, I am going fishing.") in user_message(messages)


def test_sermon_text_is_truncated():
    (messages,) = generate(["benediction"], sermon_text=("John 21:1-19", "x" * 5000))
    text = user_message(messages)
    assert "x" * liturgy_prompts.SERMON_TEXT_LIMIT in text
    assert "x" * (liturgy_prompts.SERMON_TEXT_LIMIT + 1) not in text


@pytest.mark.parametrize("sermon_text", [
    None, ("John 21:1-19", "[Could not load text]"), ("John 21:1-19", "  "), ("", "Some text."),
])
def test_missing_or_failed_sermon_text_is_skipped(sermon_text):
    (messages,) = generate(["benediction"], sermon_text=sermon_text)
    assert "Sermon text" not in user_message(messages)


def test_user_written_sections_are_not_sent_to_the_ai(make_church):
    ai = FakeAI(reply="Draft.")
    outcomes = liturgy.generate_liturgy(
        church_id=make_church(), user_id=uuid.uuid4(), occasion="Third Sunday of Easter",
        scriptures=["Acts 9:1-6"], hymns={}, sections=["benediction"],
        overrides={"benediction": "Go in peace."}, sermon=("John 21:1-19", "Simon Peter said."), ai=ai)
    assert [(o.section, o.status, o.text) for o in outcomes] == [("benediction", "override", "Go in peace.")]
    assert ai.calls == []
````

```bash
.venv/bin/python -m pytest -q backend/tests/test_generate_liturgy.py 2>&1 | tail -1
```

**Expected:** `12 passed in <t>s`: every PR #4 case holds against the new functions while `generate_liturgy` still exists.

- [ ] **Step 2 (agent): Replace the oracle with the "gone" test, and see it fail**

This replaces the whole file; its first five tests are unchanged:

**Create `backend/tests/test_liturgy_generation.py`:**

````python
"""The liturgy prompts, pinned before worship_service.generate_liturgy goes
(slice 4 spec, Testing "Characterization first" `test_liturgy_generation.py`;
AC3, AC19). The system message is compared with the merged system prompt,
never quoted (the reviewer add-on changes the default's season sentences;
S "Tests before and after")."""
import liturgy_prompts as lp

OCCASION = "Third Sunday of Easter"
SCRIPTURES = ["Acts 9:1-6", "Psalm 30", "Revelation 5:11-14", "John 21:1-19"]
SLOTS = {"opening": lp.ResolvedHymn("Holy, Holy, Holy", 138),
         "response": lp.ResolvedHymn("Be Thou My Vision", 450),
         "closing": lp.ResolvedHymn("Lift High the Cross", 826)}


def _messages(section, overrides=None, **context):
    ctx = lp.build_context(occasion=OCCASION, scriptures=context.pop("scriptures", SCRIPTURES),
                           hymns_by_slot=context.pop("hymns_by_slot", SLOTS), **context)
    return lp.build_messages(section, lp.merge_prompts(overrides), ctx)


def test_the_system_message_is_the_merged_system_prompt():
    assert _messages("benediction")[0]["content"] == lp.default_prompts()["system"]
    assert _messages("benediction", {"system": "Our own voice."})[0]["content"] == "Our own voice."


def test_scripture_lines_or_none_specified():
    user = _messages("call_to_worship")[1]["content"]
    assert "- Acts 9:1-6\n- Psalm 30\n- Revelation 5:11-14\n- John 21:1-19" in user
    assert "None specified." in _messages("call_to_worship", scriptures=[])[1]["content"]


def test_church_overrides_are_applied():
    user = _messages("benediction", {"benediction": "Bless {occasion} with {opening_hymn}."})[1]["content"]
    assert user.startswith("Bless Third Sunday of Easter with Holy, Holy, Holy.")
    assert "A good Benediction:" in user


def test_opening_hymn_comes_from_the_opening_slot():
    """BC-8: generate_liturgy used the first filled slot (the positional bug)."""
    slots = {"opening": None, "response": SLOTS["response"], "closing": SLOTS["closing"]}
    user = _messages("call_to_worship", hymns_by_slot=slots)[1]["content"]
    assert "Opening hymn: N/A." in user and "Be Thou My Vision" not in user


def test_a_hymn_without_a_number_has_no_hash_none():
    """BC-8: generate_liturgy printed "(#None)"."""
    slots = {"opening": lp.ResolvedHymn("Archived Hymn", None)}
    user = _messages("prayers_of_the_people", hymns_by_slot=slots)[1]["content"]
    assert "Hymns: - Archived Hymn." in user and "(#None)" not in user


def test_the_old_generate_liturgy_is_gone():
    """S Backend 6: deleted after its behavior was pinned above and in
    test_generate_liturgy.py, with its UI-shaped error strings."""
    from pathlib import Path

    import worship_service

    for name in ("generate_liturgy", "_sermon_text_block", "SERMON_TEXT_LIMIT", "OpenAI"):
        assert not hasattr(worship_service, name), name
    source = Path(worship_service.__file__).read_text(encoding="utf-8")
    for text in ("Settings → Secrets", "Configure OPENAI_API_KEY", "gpt-3.5-turbo", "[Error generating"):
        assert text not in source, text
````

**In `backend/tests/test_hymn_match_parity.py`, replace:**

````python
    assert callable(worship_service.generate_liturgy) and callable(worship_service.build_docx)
````

**with:**

````python
    assert callable(worship_service.build_docx)       # generate_liturgy went in slice 4a
````

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_generation.py backend/tests/test_hymn_match_parity.py 2>&1 | tail -3
```

**Expected:**

```
FAILED backend/tests/test_liturgy_generation.py::test_the_old_generate_liturgy_is_gone
1 failed, 8 passed in <t>s
```

(`AssertionError: generate_liturgy`.)

- [ ] **Step 3 (agent): Delete the old generation code**

**In `backend/worship_service.py`, replace:**

````python
"""
Worship service generator: OpenAI liturgy and Word document export (the
hymn helpers moved to hymn_search, hymn_suggest and usecases.hymns in slice 3).
"""
````

**with:**

````python
"""
Worship service generator: the Word document export. The hymn helpers moved
to hymn_search, hymn_suggest and usecases.hymns in slice 3; liturgy generation
moved to liturgy_prompts and usecases.liturgy in slice 4.
"""
````

**In `backend/worship_service.py`, replace:**

````python
import logging
import os
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

import liturgy_prompts
import service_rubric
from liturgy_config import COMMUNION_BLOCKS

logger = logging.getLogger(__name__)

# Optional imports for docx and openai
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
````

**with:**

````python
import logging
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

from liturgy_config import COMMUNION_BLOCKS

logger = logging.getLogger(__name__)

# Optional import for docx
try:
````

**In `backend/worship_service.py`, replace from the line starting `SERMON_TEXT_LIMIT = 2000` up to (not including) the line starting `def _add_custom_elements_after(` with:**

````python
````

- [ ] **Step 4 (agent): Run the tests, the gates and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_generation.py backend/tests/test_generate_liturgy.py backend/tests/test_hymn_match_parity.py backend/tests/test_communion_docx.py backend/tests/test_liturgy_config.py 2>&1 | tail -1
grep -rnE "generate_liturgy|_sermon_text_block|SERMON_TEXT_LIMIT|Settings → Secrets|Configure OPENAI_API_KEY|gpt-3.5-turbo" --include=*.py backend | grep -v "^backend/tests/"
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `33 passed in <t>s`; the grep prints only the new code: `backend/usecases/liturgy.py` (its docstring and `def generate_liturgy`), `backend/api/routes/liturgy.py` (the route and its usecase call), `backend/liturgy_prompts.py` (`SERMON_TEXT_LIMIT` and its use) and `backend/api/schemas.py` (`SermonText`'s docstring), and nothing from `worship_service.py`; `1176 passed, 11 skipped in <t>s`; then exactly ` M backend/tests/test_generate_liturgy.py`, ` M backend/tests/test_hymn_match_parity.py`, ` M backend/tests/test_liturgy_generation.py`, ` M backend/worship_service.py`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/worship_service.py backend/tests/test_generate_liturgy.py backend/tests/test_liturgy_generation.py backend/tests/test_hymn_match_parity.py
git commit -q -m "Word file module: generate_liturgy deleted after its behavior was ported (S Backend 6, AC19)" -m "PR #4's rubric and sermon tests now run against liturgy_prompts and
usecases.liturgy, each assertion kept. worship_service loses
generate_liturgy, _sermon_text_block, SERMON_TEXT_LIMIT (now in
liturgy_prompts), the openai import and the Settings → Secrets and
[Configure OPENAI_API_KEY] strings. Frozen app.py on main imported
generate_liturgy and no longer imports (accepted, as in 2a and 3a)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

Compare the old and new `test_generate_liturgy.py` case by case (each assertion kept, S Testing amendment). `git show HEAD -- backend/worship_service.py` removes only the generation code and imports. Push the backup.

Counts after Task 10: backend **1176 passed, 11 skipped**; frontend **442 in 64**.

### Task 11: Prayers of the People gets one 60 s attempt (S Risks 1; F §1.8, §2.8; owner question 1; clarification 16)

**Only if the owner answered "yes" to question 1.** Otherwise skip this task; the counts stay at 1176 and T12 leaves out the F row and the S bullet about the timeout (T12 Step 1 says how).

`complete()` gains optional per-call `timeout_seconds` (> 0) and `max_retries` (>= 0) that replace the settings for that call; a deadline still caps the attempt. `FakeAI` records them only when set. `SectionSpec` gains the two fields (None = the settings), and Prayers of the People has 60.0 and 0.

**Files:**
- Modify: `backend/integrations/openai_client.py`, `backend/liturgy_config.py`, `backend/usecases/liturgy.py`, `backend/tests/test_openai_client.py`, `backend/tests/test_usecase_liturgy.py`, `backend/tests/test_liturgy_config.py`

**Interfaces:**
- Consumes: `openai_client._complete`'s loop (3a); `liturgy_config.SECTIONS_BY_KEY` (T1).
- Produces: `openai_client.complete(messages, *, max_completion_tokens, json_mode=False, deadline=None, timeout_seconds=None, max_retries=None)`; `FakeAI.complete` with the same keywords; `SectionSpec.timeout_seconds: float | None = None`, `SectionSpec.max_retries: int | None = None`.

- [ ] **Step 1 (agent): Write the failing tests**

**Append to `backend/tests/test_openai_client.py`:**

````python


# --- slice 4a: per-call timeout and retries (slice 4 spec, Risks 1) ---------------------


def test_a_call_can_set_its_own_timeout_and_retries():
    sdk, sleeps = setup(sdk_error("server"), '{"ok": true}')
    with pytest.raises(UpstreamError):
        ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=60.0, max_retries=0)
    assert len(sdk.calls) == 1 and sleeps == []                  # no retry
    assert (sdk.calls[0]["timeout"].read, sdk.calls[0]["timeout"].connect) == (60.0, 5.0)
    clock = FakeClock()
    sdk, _ = setup('{"ok": true}', clock=clock.now)
    ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=60.0, deadline=clock.now() + 20.0)
    assert sdk.calls[0]["timeout"].read == 20.0                  # a deadline still wins
    sdk, _ = setup(sdk_error("server"), '{"ok": true}')
    assert ai.complete(MESSAGES, max_completion_tokens=10) == '{"ok": true}'   # the settings: one retry
    assert sdk.calls[1]["timeout"].read == 30.0
    for bad in ({"timeout_seconds": 0}, {"timeout_seconds": -1.0}, {"max_retries": -1}):
        with pytest.raises(ValueError):
            ai.complete(MESSAGES, max_completion_tokens=10, **bad)
    fake = ai.FakeAI(reply="ok")
    ai.set_ai_for_tests(fake)
    ai.complete(MESSAGES, max_completion_tokens=10, timeout_seconds=60.0, max_retries=0)
    ai.complete(MESSAGES, max_completion_tokens=10)
    assert (fake.calls[0]["timeout_seconds"], fake.calls[0]["max_retries"]) == (60.0, 0)
    assert "timeout_seconds" not in fake.calls[1] and "max_retries" not in fake.calls[1]
````

**Append to `backend/tests/test_usecase_liturgy.py`:**

````python


def test_prayers_of_the_people_gets_one_60_second_attempt(church):
    """S Risks 1: 15 s for a slot plus one 60 s attempt fits the client's 90 s."""
    ai = FakeAI(reply="Draft.")
    run(church, ["prayers_of_the_people", "benediction"], ai=ai)
    calls = {("Prayers of the People" in user_message(c)): c for c in ai.calls}
    assert (calls[True]["timeout_seconds"], calls[True]["max_retries"]) == (60.0, 0)
    assert "timeout_seconds" not in calls[False] and "max_retries" not in calls[False]
````

**In `backend/tests/test_liturgy_config.py`, replace:**

````python
        assert (spec.rows, spec.max_completion_tokens, spec.pastor_copy_only) == (
            (8, 4000, True) if pastor else (4, 1500, False)), spec.key
````

**with:**

````python
        assert (spec.rows, spec.max_completion_tokens, spec.pastor_copy_only) == (
            (8, 4000, True) if pastor else (4, 1500, False)), spec.key
        assert (spec.timeout_seconds, spec.max_retries) == ((60.0, 0) if pastor else (None, None)), spec.key
````

- [ ] **Step 2 (agent): Run them to see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_openai_client.py backend/tests/test_usecase_liturgy.py backend/tests/test_liturgy_config.py 2>&1 | tail -4
```

**Expected:**

```
FAILED backend/tests/test_openai_client.py::test_a_call_can_set_its_own_timeout_and_retries
FAILED backend/tests/test_usecase_liturgy.py::test_prayers_of_the_people_gets_one_60_second_attempt
FAILED backend/tests/test_liturgy_config.py::test_rows_budgets_pastor_copy_and_hints
3 failed, 46 passed in <t>s
```

- [ ] **Step 3 (agent): Add the keywords and use them**

**In `backend/integrations/openai_client.py`, replace:**

````python
- ai_available() and complete(messages, *, max_completion_tokens,
  json_mode=False, deadline=None) -> str. complete() always sends
  max_completion_tokens, sends response_format json_object in json_mode, and
  temperature and reasoning_effort only when they are set. It holds one of OPENAI_MAX_CONCURRENCY
  slots per call and retries itself (the SDK client has max_retries=0).
````

**with:**

````python
- ai_available() and complete(messages, *, max_completion_tokens,
  json_mode=False, deadline=None, timeout_seconds=None, max_retries=None)
  -> str. complete() always sends max_completion_tokens, sends
  response_format json_object in json_mode, and temperature and
  reasoning_effort only when they are set. It holds one of
  OPENAI_MAX_CONCURRENCY slots per call and retries itself (the SDK client
  has max_retries=0). timeout_seconds and max_retries replace
  OPENAI_TIMEOUT_SECONDS and OPENAI_MAX_RETRIES for one call (slice 4:
  Prayers of the People gets 60 s and no retry).
````

**In `backend/integrations/openai_client.py`, replace:**

````python
    def complete(self, messages, *, max_completion_tokens: int, json_mode: bool = False,
                 deadline: Optional[float] = None) -> str:
        self.calls.append({"messages": [dict(m) for m in messages],
                           "max_completion_tokens": max_completion_tokens,
                           "json_mode": json_mode, "deadline": deadline})
````

**with:**

````python
    def complete(self, messages, *, max_completion_tokens: int, json_mode: bool = False,
                 deadline: Optional[float] = None, timeout_seconds: Optional[float] = None,
                 max_retries: Optional[int] = None) -> str:
        call = {"messages": [dict(m) for m in messages], "max_completion_tokens": max_completion_tokens,
                "json_mode": json_mode, "deadline": deadline}
        if timeout_seconds is not None:                 # recorded only when a caller sets them
            call["timeout_seconds"] = timeout_seconds
        if max_retries is not None:
            call["max_retries"] = max_retries
        self.calls.append(call)
````

**In `backend/integrations/openai_client.py`, replace:**

````python
def complete(messages: Sequence[Mapping[str, str]], *, max_completion_tokens: int,
             json_mode: bool = False, deadline: Optional[float] = None) -> str:
    """The reply's text. Raises NotConfigured, Busy, UpstreamTimeout or
    UpstreamError (F §2.8's codes, this module's messages); never an SDK error."""
    if _override is not None:
        return _override.complete(messages, max_completion_tokens=max_completion_tokens,
                                  json_mode=json_mode, deadline=deadline)
    return _complete(_current(), messages, max_completion_tokens, json_mode, deadline)
````

**with:**

````python
def complete(messages: Sequence[Mapping[str, str]], *, max_completion_tokens: int,
             json_mode: bool = False, deadline: Optional[float] = None,
             timeout_seconds: Optional[float] = None, max_retries: Optional[int] = None) -> str:
    """The reply's text. Raises NotConfigured, Busy, UpstreamTimeout or
    UpstreamError (F §2.8's codes, this module's messages); never an SDK error.
    timeout_seconds (> 0) and max_retries (>= 0), when given, replace the
    settings' per-attempt timeout and retry count for this call."""
    if timeout_seconds is not None and not timeout_seconds > 0:
        raise ValueError("timeout_seconds must be positive")
    if max_retries is not None and max_retries < 0:
        raise ValueError("max_retries must not be negative")
    if _override is not None:
        extra: dict[str, Any] = {}
        if timeout_seconds is not None:
            extra["timeout_seconds"] = timeout_seconds
        if max_retries is not None:
            extra["max_retries"] = max_retries
        return _override.complete(messages, max_completion_tokens=max_completion_tokens,
                                  json_mode=json_mode, deadline=deadline, **extra)
    return _complete(_current(), messages, max_completion_tokens, json_mode, deadline,
                     timeout_seconds=timeout_seconds, max_retries=max_retries)
````

**In `backend/integrations/openai_client.py`, replace:**

````python
def _complete(state: _State, messages, max_completion_tokens: int, json_mode: bool,
              deadline: Optional[float]) -> str:
    settings = state.settings
````

**with:**

````python
def _complete(state: _State, messages, max_completion_tokens: int, json_mode: bool,
              deadline: Optional[float], *, timeout_seconds: Optional[float] = None,
              max_retries: Optional[int] = None) -> str:
    settings = state.settings
    per_attempt = settings.timeout_seconds if timeout_seconds is None else timeout_seconds
    retry_limit = settings.max_retries if max_retries is None else max_retries
````

**In `backend/integrations/openai_client.py`, replace:**

````python
            timeout = settings.timeout_seconds if remaining is None else min(settings.timeout_seconds, remaining)
````

**with:**

````python
            timeout = per_attempt if remaining is None else min(per_attempt, remaining)
````

**In `backend/integrations/openai_client.py`, replace:**

````python
                mapped_later = retries >= settings.max_retries or not _retryable(exc)
````

**with:**

````python
                mapped_later = retries >= retry_limit or not _retryable(exc)
````

**In `backend/liturgy_config.py`, replace:**

````python
    hint: Optional[str]
    max_completion_tokens: int
````

**with:**

````python
    hint: Optional[str]
    max_completion_tokens: int
    # Per-call overrides of OPENAI_TIMEOUT_SECONDS and OPENAI_MAX_RETRIES (S Risks 1):
    # a long prayer gets one 60 s attempt; 15 s for a slot + 60 s stays inside
    # the client's 90 s (F §1.8). None: the settings apply.
    timeout_seconds: Optional[float] = None
    max_retries: Optional[int] = None
````

**In `backend/liturgy_config.py`, replace:**

````python
    SectionSpec("prayers_of_the_people", "Prayers of the People", False, 8, True, None, 4000),
````

**with:**

````python
    SectionSpec("prayers_of_the_people", "Prayers of the People", False, 8, True, None, 4000,
                timeout_seconds=60.0, max_retries=0),
````

**In `backend/usecases/liturgy.py`, replace:**

````python
    try:
        text = ai.complete(prompt.messages,
                           max_completion_tokens=SECTIONS_BY_KEY[section].max_completion_tokens)
````

**with:**

````python
    spec = SECTIONS_BY_KEY[section]
    limits = {name: value for name, value in (("timeout_seconds", spec.timeout_seconds),
                                              ("max_retries", spec.max_retries)) if value is not None}
    try:
        text = ai.complete(prompt.messages, max_completion_tokens=spec.max_completion_tokens, **limits)
````

- [ ] **Step 4 (agent): Run the tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_openai_client.py backend/tests/test_usecase_liturgy.py backend/tests/test_liturgy_config.py backend/tests/test_api_hymn_suggestions.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `71 passed in <t>s` (3a's exact `FakeAI` call test and the suggestion tests are unchanged); `1178 passed, 11 skipped in <t>s`; then exactly the six modified files.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/integrations/openai_client.py backend/liturgy_config.py backend/usecases/liturgy.py backend/tests/test_openai_client.py backend/tests/test_usecase_liturgy.py backend/tests/test_liturgy_config.py
git commit -q -m "AI: one 60 s attempt for Prayers of the People (S Risks 1; owner answer to plan question 1)" -m "complete() takes optional timeout_seconds and max_retries for one call,
still capped by a deadline. Prayers of the People, 10-15 paragraphs, gets
one 60 s attempt with no retry: 15 s for a slot plus 60 s stays inside the
page's 90 s. Every other section keeps 30 s and one retry." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint and backup push**

`git show HEAD -- backend/integrations/openai_client.py`: with neither keyword the call is exactly as before (3a's tests unchanged). Push the backup.

Counts after Task 11: backend **1178 passed, 11 skipped**; frontend **442 in 64**.

### Task 12: Docs: F's D17 and timeout row, S's answered item and 4a notes, the runbook row (owner answers 1 and 3; clarifications 1-23)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, `docs/ops-runbook.md`

- [ ] **Step 1 (agent): Write the docs**

If T11 was skipped (owner question 1 answered "no"), leave out the F row that starts `| §1.8, §2.8 | *(2026-09-30, slice 4a plan)*` and replace S's bullet that starts `- **Prayers of the People timeout**` with: `- **Prayers of the People timeout** (Risks 1): unchanged in 4a (30 s and one retry); the owner's live check after the merge measures a real one, and the follow-up in Risks 1 applies if it times out.`

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
The member's own choice always wins, and the AI's top pick stays one tap away as a chip. |
````

**with:**

````markdown
The member's own choice always wins, and the AI's top pick stays one tap away as a chip. |
| D17 | AI for custom elements (slice 4; owner decision 2) | **Custom elements get no AI Generate.** Generate and Regenerate stay on the 8 liturgy sections, which have church prompts; a custom element such as a Children's Moment is typed. Owner answer of 2026-09-30, recorded here as slice 4's open question 7 asked. | Only the sections have prompts an admin can shape, and typed text is never changed by the AI. |
````

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
| §4.6, §4.7, §4.9 | *(2026-09-29, slice 3b plan)*
````

**with:**

````markdown
| §1.8, §2.8 | *(2026-09-30, slice 4a plan)* `complete()` also takes optional `timeout_seconds` and `max_retries`, which replace `OPENAI_TIMEOUT_SECONDS` and `OPENAI_MAX_RETRIES` for one call. `POST /liturgy/generate` gives Prayers of the People one 60 s attempt with no retry (slice 4 Risks 1), so its worst case is 15 s for a slot plus 60 s, inside the 90 s client timeout; the other sections keep 30 s and one retry. | 4a |
| §4.6, §4.7, §4.9 | *(2026-09-29, slice 3b plan)*
````

**In `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, replace:**

````markdown
4b starts only after the owner has answered Risks and open questions item 7 (recorded in F's decisions table).
````

**with:**

````markdown
4b starts only after the owner has answered Risks and open questions item 7 (recorded in F's decisions table). *(4a plan: answered 2026-09-30, "no"; F D17.)*
````

**In `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, replace:**

````markdown
7. **AI Generate for custom elements (open; owner answers before 4b).**
````

**with:**

````markdown
7. **AI Generate for custom elements (answered 2026-09-30: no; F D17).**
````

**Append to `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`:**

````markdown

---

## Notes from the slice 4a plan (2026-09-30)

`docs/superpowers/plans/2026-09-30-slice-4a-liturgy-backend.md` builds the backend half. Where it reads this spec more precisely, or the code and F win, it says so here (its clarifications give the reasons):

- **Custom elements** get no AI Generate (Risks item 7, owner answer of 2026-09-30; F D17). 4a has nothing custom.
- **Freeze contingency** (Backend 6; F §6.1 item 6): not in effect since 2026-09-26 (F §6.1 amendment of 2026-09-28), so there is no `generate_liturgy` wrapper, no `use_library` parameter and no `LEGACY_SYSTEM_PROMPT`. `worship_service.generate_liturgy` is deleted; `app.py` on `main` then no longer imports (accepted, as in 2a and 3a).
- **Placement label** (Backend 1 `CUSTOM_PLACEMENTS`; owner-visible in 4b): `ot_reading`'s label is "After First Reading", following owner decision B ("First Reading" wherever the app shows that heading); the other 16 pairs are app.py's, verbatim.
- **Outline and docx** (Testing): the outline/docx test reads the docx's "Old Testament Reading" as OUTLINE's "First Reading" until 5a renames the Word heading; 5a deletes that one mapping.
- **Hints** (UX §Section card): `SectionSpec.hint` carries the table's copy: Call to Worship and Prayer of Confession as written, Assurance "Added automatically after your text." (4b shows it under `assurance_response`), Benediction "Your church's default benediction. Admins can change it in Settings." (4b shows it only while the card follows the default); Prayers of the People has none (its chip comes from `pastor_copy_only`).
- **Prompt builder** (Backend 2): `build_prompt(...)` returns `BuiltPrompt(messages, dropped)` so the log can name what the budget dropped; `build_messages` returns its messages. Occasion, readings, hymn titles and the sermon reference go into the prompt on one line each (whitespace collapsed, as slice 3's prompt does); a slot whose title is blank counts as empty. `check_template` runs its checks in the table's order across all placeholders. `service_rubric` imports `SECTION_ORDER` from `liturgy_config` (same list), since `liturgy_prompts` now imports `service_rubric`.
- **Stored JSON** (Data): a non-object `liturgy_prompts` value reads as no overrides, `merge_prompts` ignores values that are not strings, and `validate_prompts` checks only the overrides `merge_prompts` would use.
- **Hymns** (Backend 6): `repos.hymns.get_hymns_by_ids` returns 3a's `HymnRecord`s; the usecase answers any id it does not find (another church's, a deleted hymn, a malformed id) with the 404 message.
- **Prayer library** (Interfaces 6a): `read_library` reads a stored value of the wrong shape as empty and skips a single prayer of the wrong shape; `choose_example` never picks a blank prayer.
- **Prayers of the People timeout** (Risks 1): one 60 s attempt with no retry from 4a on (owner answer to the 4a plan's question 1; F §2.8 amendment). The owner's live check after the merge measures a real one.
- **Risk 3's query** lists only an 8-character prefix of each church id: `select left(id::text, 8) as church, settings->'liturgy_prompts' as prompts from churches where settings->'liturgy_prompts' is not null and deleted_at is null`.
````

**In `docs/ops-runbook.md`, replace:**

````markdown
Without it, or without `OPENAI_MODEL`, hymn suggestions answer 503 `ai_not_configured` and the startup log says `AI: not configured (...)`.
````

**with:**

````markdown
Without it, or without `OPENAI_MODEL`, hymn suggestions answer 503 `ai_not_configured`, liturgy generation (slice 4a) answers "AI not configured. Type this section yourself." for each section it would write, and the startup log says `AI: not configured (...)`.
````

- [ ] **Step 2 (agent): Check the docs tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
git diff --stat
```

**Expected:** `89 passed in <t>s`; `4`; `1178 passed, 11 skipped in <t>s`; three files, about 23 insertions and 3 deletions.

- [ ] **Step 3 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md docs/ops-runbook.md
git commit -q -m "Docs: F D17 and the timeout row, S's 4a notes, the runbook's AI row (owner answers 2026-09-30)" -m "F records D17 (custom elements get no AI Generate) and the per-call
timeout for Prayers of the People. S marks its open question 7 answered and
gains the 4a plan's notes where the plan reads it more precisely. The
runbook's OPENAI_API_KEY row says what liturgy does without a key." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 4 (controller): Review checkpoint (end of batch D) and backup push**

Review T10-T12 together: each S note matches a clarification; D17 is worded as the owner answered; nothing in the docs names a church id, an email or a key. Push the backup.

Counts after Task 12: backend **1178 passed, 11 skipped**; frontend **442 in 64**.

### Task 13: Whole-branch verification, the draft PR, the owner's prompt check, ready (owner's yes before the PR is opened and before it is marked ready) (S Testing, AC1-AC10, AC19-AC21; S Risks 3; F §2.2, §2.5, §5.4; owner answers 2, 4a, 5)

The whole branch is checked in one place: both suites, the Postgres marker count, the threaded tests three times, types, lint, the frontend build, the generated files, the layering and logging gates, the exact changed paths and commits. The branch is already on `origin` (the backup pushes), so on the owner's first yes the agent opens the PR as a draft and waits for CI. **The PR is not marked ready until the owner's stored prompt overrides have been listed and checked** (owner answer 4a; Steps 9-10); then, on the second yes, the agent marks it ready. Merging is Task 14.

Below, `<scratch>` is the session's scratchpad directory and `<N>` the PR number Step 7 prints; write both out literally. Every `gh` command uses `-R bbrown62450/church`.

**Files:** none changed. A local or CI failure is fixed in the owning task's files (a new commit in that task's area), never here.

- [ ] **Step 1 (agent): Bring the branch up to date**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline origin/main..HEAD | tail -1
```

**Expected:** only `?? .claude/`; `0`; the branch's oldest commit, `<sha> WIP plan: slice 4a`. If the count is not `0`, `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 13)"` with the two trailer lines as a second `-m`; on a conflict `git merge --abort` and stop. New tests from `main` change Step 2's totals by exactly their number; name them in Step 6's message.

- [ ] **Step 2 (agent): Backend suite, Postgres marker count, threaded tests three times**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy.py backend/tests/test_api_liturgy.py backend/tests/test_openai_client.py 2>&1 | tail -1; done
```

**Expected:** `1178 passed, 11 skipped in <t>s`; `11 skipped, 1178 deselected in <t>s` (no `TEST_DATABASE_URL` here; 4a adds no Postgres test); `50 passed in <t>s` three times with no failure (48 if T11 was skipped). If a local throwaway Postgres is available, `TEST_DATABASE_URL=postgresql://postgres:<password>@localhost:5432/postgres .venv/bin/python -m pytest -q -m postgres | tail -1` gives `11 passed, 1178 deselected, 1 warning in <t>s`.

- [ ] **Step 3 (agent): Frontend tests, types, lint, build; the generated files are current**

```bash
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests " && npm run typecheck && npm run lint)
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | tail -3)
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend
.venv/bin/python -c "import json; p = json.load(open('frontend/src/lib/api/openapi.json')); print(sorted(k for k in p['paths'] if 'liturgy' in k)); print(sorted(k for k in p['components']['schemas'] if k in ('LiturgyConfigOut', 'GenerateLiturgyIn', 'GenerateLiturgyOut', 'SectionResult', 'SectionError', 'SermonText', 'HymnRef', 'SlotHymns'))); print(p['components']['schemas']['ChurchProfileOut']['properties']['default_benediction'])"
```

**Expected:** ` Test Files  64 passed (64)`, `      Tests  442 passed (442)`; `tsc` and `eslint` print nothing after their headers; the build ends with its route table and no `Error:` (the same routes as after 3b: 4a adds no page; a font `Failed to fetch` only: say so and rely on CI's build); nothing from `git status -- frontend`; `['/liturgy/config', '/liturgy/generate']`; `['GenerateLiturgyIn', 'GenerateLiturgyOut', 'HymnRef', 'LiturgyConfigOut', 'SectionError', 'SectionResult', 'SermonText', 'SlotHymns']`; `{'title': 'Default Benediction', 'type': 'string'}`.

- [ ] **Step 4 (agent): Gates (judged, not obeyed blindly; tests excluded)**

```bash
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/liturgy_config.py backend/prayer_library.py backend/liturgy_prompts.py backend/service_rubric.py backend/usecases/liturgy.py backend/repos/churches.py backend/repos/hymns.py backend/integrations/openai_client.py
grep -nE "logger\.(info|warning|error|debug|exception)" backend/usecases/liturgy.py
grep -rnE "generate_liturgy|_sermon_text_block|Settings → Secrets|Configure OPENAI_API_KEY|gpt-3.5-turbo" --include=*.py backend | grep -v "^backend/tests/"
grep -nE "try:|select\(|session_scope" backend/api/routes/liturgy.py
```

**Expected:** the first grep prints nothing. The second lists the two DEBUG lines (messages, answer), the unusable-answer WARNING (section and length), the `logger.exception` for an unexpected AI error (section only) and the `_log` INFO line; read each: none formats a prompt, an answer, typed text or client text at INFO. The third prints only the new `generate_liturgy` in `backend/usecases/liturgy.py` and `backend/api/routes/liturgy.py`. The fourth prints nothing.

- [ ] **Step 5 (agent): The exact changed paths and commits**

```bash
git diff --name-status origin/main | sort -k2
git log --reverse --format=%s origin/main..HEAD
```

**Expected:** the File Structure's lists and nothing else: `A` for the plan, `backend/liturgy_config.py`, `backend/prayer_library.py`, `backend/usecases/liturgy.py`, `backend/api/routes/liturgy.py`, the three `fixtures/shared/*.json` files and the six new test files (14 `A`); `M` for the 9 backend modules, the 14 backend test files, the 3 frontend files and the 3 docs in the File Structure (29 `M`; 27 if T11 was skipped, since `openai_client.py` and `test_openai_client.py` are then untouched); no `D`. Then the plan's commits (`WIP plan: slice 4a` ..., `Plan: slice 4a liturgy backend (S slice 4; owner answers 2026-09-30)`), and the twelve subjects of Tasks 1-12 in order (eleven if T11 was skipped), plus any review-fix commits, each named in Step 6's message.

- [ ] **Step 6 (agent): Ask the owner to open the pull request**

Tell the owner, in one message: "Slice 4a (the liturgy backend) is ready for a pull request. It adds two routes the Liturgy step will use (the step's settings, and writing sections with AI one at a time, where anything typed comes back unchanged) and the church's default benediction on the church profile. Nothing changes on screen, there is no database change, and liturgy-frozen is not affected. Tests: backend 1110 → 1178 passed, 11 → 11 skipped; frontend 442 → 442. Before I ask to mark it ready, I will walk you through one read-only query that lists your church's saved liturgy prompts, so I can check them against the new rules. May I open the pull request as a draft so CI runs?"

- [ ] **Step 7 (agent, on the owner's yes): Open the draft PR**

(not replayed)
```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 4a liturgy backend: liturgy config, per-section generation, default benediction" \
  --body-file <scratch>/slice4a-pr-body.md
```

Write `<scratch>/slice4a-pr-body.md` first. Its first line, above the summary, is exactly:

```
> **Stored prompts: NOT YET CHECKED.** This PR stays a draft until the owner's read-only list of saved liturgy prompts has been checked with `validate_prompts` (owner answer 4a; plan Task 13 Steps 9-10).
```

Then: a summary (the Goal paragraph in plain words); the two routes and the `/church` field; the owner answers 1-5 of 2026-09-30 and the two plan questions with the owner's answers, and where each landed; the owner-visible clarifications (1, 3, 16); the line `Tests: backend 1110 → 1178 passed, 11 → 11 skipped; frontend 442 → 442 in 64 files`; "No migration; production stays at 0004_invites_reusable. No new variables: the OpenAI key and model from slice 3a are used."; then `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS` on the last lines.

**Expected:** the push prints `Everything up-to-date` or the new commits; `gh` prints the PR URL. Record `<N>`.

- [ ] **Step 8 (agent): Wait for CI**

(not replayed)
```bash
gh pr checks <N> -R bbrown62450/church --watch
gh run view $(gh run list --branch claude/slice-2-plan-4q33le --workflow ci --limit 1 -R bbrown62450/church --json databaseId --jq '.[0].databaseId') -R bbrown62450/church --log | grep -E '[0-9]+ passed' | sed -E 's/^.*Z //'
```

**Expected:** `backend`, `backend-postgres`, `frontend` and the Vercel preview pass; the log lines include `1178 passed, 11 skipped` (`backend`), `11 passed, 1178 deselected, 1 warning` (`backend-postgres`) and `Tests  442 passed (442)` (`frontend`). A CI-only failure is fixed in the owning task's files, pushed on the standing backup permission, and this step reruns.

- [ ] **Step 9 (agent + OWNER): The stored prompts, listed read-only (owner answer 4a; S Risks 3)**

Walk the owner through it **one step at a time**, waiting for each reply before sending the next:
1. "Before I ask to mark the pull request ready, I need to see your church's saved liturgy prompts (the wording under Settings → Liturgy prompts in the old app), to check them against the new app's stricter rules. Please open https://supabase.com/dashboard and choose the project `worship-staging`. Tell me when you see it."
2. "Click SQL Editor on the left, then New query. Tell me when you have an empty query box."
3. "Paste this and click Run. It only reads; nothing is changed. It shows just the first 8 characters of each church's id and the saved prompts, nothing else:" followed by

   ```sql
   select left(id::text, 8) as church, settings->'liturgy_prompts' as prompts
   from churches
   where settings->'liturgy_prompts' is not null and deleted_at is null
   order by 1;
   ```

   then "Tell me how many rows it shows. If it says 'No rows returned', tell me that and we are done with this check."
4. Only if there are rows: "Under the results, choose Export, then Download CSV, and attach the file here (or copy the rows and paste them here). The prompts are your church's wording, with no names or emails."

Save what the owner sends as `<scratch>/prompt_overrides.csv` (columns `church`, `prompts`). Never commit it. (A pasted grid is saved in the same two columns.)

- [ ] **Step 10 (agent): Check each stored override and report**

(not replayed)
```bash
.venv/bin/python - <<'EOF'
import csv, json, sys
sys.path[:0] = ["backend"]
import liturgy_prompts as lp

rows = list(csv.DictReader(open("<scratch>/prompt_overrides.csv", encoding="utf-8")))
for row in rows:
    prompts = json.loads(row["prompts"] or "null")
    if not isinstance(prompts, dict):
        print(row["church"], "not an object: the new app reads it as no overrides")
        continue
    used = [k for k in lp.PROMPT_KEYS if isinstance(prompts.get(k), str) and prompts[k].strip()]
    failures = lp.validate_prompts(prompts)
    print(row["church"], "overrides:", ",".join(used) or "none", "->", "all pass" if not failures else "")
    for key, reason in failures.items():
        print("   FAILS", lp.SECTION_LABELS.get(key, "Overall voice (system)"), "-", reason)
    for key in used:
        unknown = lp.check_template(key, prompts[key]).unknown_placeholders
        if unknown:
            print("   note:", lp.SECTION_LABELS.get(key, key), "has placeholders that print as blank:", unknown)
    ignored = sorted(set(prompts) - set(lp.PROMPT_KEYS))
    if ignored:
        print("   note: keys the app ignores:", ignored)
print(len(rows), "rows")
EOF
```

**Expected:** one line per church. Report to the owner in plain words:
- **All pass:** "I checked the saved prompts for <n> church(es): all of them work with the new app. May I mark the pull request ready?" (Step 11.)
- **A failure:** name the church prefix, the section's label and the reason, and say what to change, for example: "Your church's Prayer of Confession prompt has a { without a partner. In the old app, open Settings → Liturgy prompts, find 'Prayer of Confession', and either remove the { or write {{ to print a brace. Tell me when you have saved it, and I will check again." Then repeat Steps 9-10 (the query only) until every row passes. The owner fixes prompts in Streamlit; the agent changes nothing in the database.
- **Notes** (placeholders that print as blank, ignored keys) are not failures; mention them in one line so the owner can fix a typo such as `{ocassion}` if they want.

Edit the PR body's first line to `> **Stored prompts: CHECKED on <date>**, <n> churches, all pass.` (`gh pr edit <N> -R bbrown62450/church --body-file <scratch>/slice4a-pr-body.md`).

- [ ] **Step 11 (agent): Ask, then mark ready**

Tell the owner: "PR #<N> is green on CI (backend 1178 passed, 11 skipped; Postgres 11 passed; frontend 442), and your saved prompts all work with the new rules. May I mark it ready for review?" On the yes:

(not replayed)
```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft --jq .isDraft
```

**Expected:** `false`.

### Task 14: Merge and after (OWNER + agent): the merge, the deploy, the live checks with a real Prayers of the People, the slice 4a record (S AC1, AC3-AC5, AC9, AC18 partial; S Risks 1-2; owner answers 4b, 5)

4a changes no schema, so the merge deploy's pre-deploy `alembic upgrade head` runs nothing, and it adds no variable: the OpenAI key and `OPENAI_MODEL=gpt-4.1-mini` from slice 3a are used. No page calls the new routes until 4b, so the live checks are the owner's: Console snippets on the production site that read the owner's own sign-in from the site's cookies, send it only to the app's API, and never print it. The owner prefers small steps: give one OWNER step, wait for the report, then the next. The agent writes each result with its date into `<scratch>/slice4a-t14-results.md` (not committed). Nothing is recorded with an email address, a church id, a token or a key.

- [ ] **Step 1 (agent): Pre-merge gate**

(not replayed)
```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,headRefOid --jq '[.state, .isDraft, .mergeable, .mergeStateStatus, .headRefOid] | @tsv'
git log --oneline origin/claude/slice-2-plan-4q33le..origin/main | wc -l
gh pr checks <N> -R bbrown62450/church
git diff --quiet origin/main origin/claude/slice-2-plan-4q33le -- backend/migrations backend/db/models.py backend/Procfile backend/railway.toml; echo "exit $?"
```

**Expected:** `OPEN	false	MERGEABLE	CLEAN	<sha>`; `0`; every check `pass`; `exit 0`. If `main` moved, merge it, rerun both suites, push on the owner's yes and wait for green. Then ask: "PR #<N> (slice 4a, the liturgy backend) is green and includes `main`. It adds no database change and changes nothing on screen; liturgy-frozen is not affected. After the merge I will ask you for three short checks from the browser, one of them a real Prayers of the People written by the AI. May I merge it now with a merge commit?"

- [ ] **Step 2 (agent, on the owner's yes): Merge**

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergedAt,mergeCommit --jq '[.state, .mergedAt, .mergeCommit.oid] | @tsv'
```

**Expected:** `MERGED	<UTC time>	<merge sha>`. Tell the owner the time and that Railway and Vercel are deploying.

- [ ] **Step 3 (OWNER): Watch the deploy**

"Please open Railway → the API service (`church`) → Deployments → the one whose message starts `Merge pull request #<N>` → Deploy Logs. Check: no line containing `Running upgrade`; the deployment is Active; the line starting `AI:` says `AI: configured (model=gpt-4.1-mini)`; and no `Traceback` or `ERROR`. Tell me what you see. Also open https://church-production-74ca.up.railway.app/health/ready in a browser tab and tell me what it shows (it should be `{\"ok\":true,\"db\":\"ok\"}`)."

- [ ] **Step 4 (agent): CI on `main` and the deployment statuses**

(not replayed)
```bash
gh run list --workflow ci --branch main --limit 3 -R bbrown62450/church --json databaseId,headSha,conclusion --jq '.[] | select(.headSha == "<merge sha>") | [.databaseId, .conclusion] | @tsv'
gh api "repos/bbrown62450/church/deployments?sha=<merge sha>" --jq '.[] | [.id, .environment] | @tsv'
```

**Expected:** the run's conclusion `success` (rerun the line if it has not appeared yet; no `sleep`); a Railway and a Vercel `Production` deployment whose latest statuses (`gh api repos/bbrown62450/church/deployments/<id>/statuses --jq '.[0].state'`) are `success`.

- [ ] **Step 5 (OWNER): The liturgy settings and the default benediction (AC1, AC9)**

"On https://worship-service-builder.vercel.app, signed in, with your real church selected, open DevTools (⌥⌘I) → Console, paste this and press Return (type `allow pasting` first if Chrome asks). It reads your sign-in from this site, calls only the app's API, prints no token and changes nothing. It does not use the AI."

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
  let [s, b, ms] = await call("GET", "/liturgy/config");
  console.log(`config ${s} ${ms}ms sections=${b.sections.length} places=${b.custom_placements.length} outline=${b.outline.length} communion_blocks=${b.communion.blocks.length} ai_available=${b.ai_available}`);
  console.log(`config off by default: ${b.sections.filter((x) => !x.default_enabled).map((x) => x.label).join(", ")}; reading heading: ${b.outline[6].label}; place: ${b.custom_placements[6].label}`);
  [s, b, ms] = await call("GET", "/church");
  console.log(`church ${s} ${ms}ms default_benediction=${JSON.stringify(b.default_benediction)}`);
})();
```

"Please copy the three Console lines to me."

The agent checks: `config 200` with `sections=8 places=17 outline=16`, `communion_blocks=31`, `ai_available=true`; "Prayers of the People" is the only section off by default; the reading heading "First Reading" and the place "After First Reading" (or app.py's wording if the owner answered "no" to question 2); `church 200` with `default_benediction="Halverson"` (nobody has set one; 6a adds the setting). `ai_available=false` means the key or model is missing: check the `AI:` line from Step 3.

- [ ] **Step 6 (OWNER): Two short sections, then a real Prayers of the People, timed (AC3-AC5; S Risks 1-2; owner answer 4b)**

First run, two short sections and one typed one (three AI calls in all across this step, well inside the `ai` bucket and a fraction of a cent):

"Please paste this in the same Console and press Return. It asks the AI for a Call to Worship and an Opening Prayer for October 4, and sends a typed Benediction that must come back unchanged."

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
  if (raw.startsWith("base64-")) {
    const bytes = Uint8Array.from(atob(raw.slice(7).replace(/-/g, "+").replace(/_/g, "/")), (c) => c.charCodeAt(0));
    raw = new TextDecoder().decode(bytes);
  }
  const token = JSON.parse(raw).access_token;
  const me = await (await fetch(API + "/me", { headers: { Authorization: "Bearer " + token } })).json();
  const churchId = localStorage.getItem("activeChurchId") || (me.churches[0] || {}).id;
  window.__liturgy = { API, token, churchId };
  const body = {
    occasion: "Nineteenth Sunday after Pentecost",
    scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    sections: ["call_to_worship", "opening_prayer", "benediction"],
    overrides: { benediction: "Go in peace to love and serve the Lord." },
  };
  const started = performance.now();
  const r = await fetch(API + "/liturgy/generate", { method: "POST", body: JSON.stringify(body),
    headers: { Authorization: "Bearer " + token, "X-Church-Id": churchId, "Content-Type": "application/json" } });
  const b = await r.json();
  console.log(`generate ${r.status} ${Math.round(performance.now() - started)}ms`);
  for (const x of b.results || []) {
    console.log(`${x.section} ${x.status} ${x.text ? x.text.length + " chars" : JSON.stringify(x.error)}`);
  }
  console.log((b.results || [])[0]?.text || JSON.stringify(b.error));
})();
```

"Please copy all the Console lines to me (they hold the AI's Call to Worship, no personal data)."

The agent checks: `generate 200`; `call_to_worship generated`, `opening_prayer generated`, `benediction override` with 39 chars (the typed text, unchanged); the Call to Worship has "Leader:" and "People:" lines and names no book or verse. An `error` result: `ai_not_configured` (key, model or quota: the 3a Step 7 guidance), `ai_busy` or `ai_timeout` (run it again once), `ai_upstream_error` (ask the controller), `prompt_invalid` (a stored prompt Step 9 missed: fix as in T13 Step 10).

Then the timed Prayers of the People, on its own:

"Now paste this and press Return. It asks for one Prayers of the People and times it. It can take up to a minute; wait for the line that starts `prayers`."

```js
(async () => {
  const { API, token, churchId } = window.__liturgy;
  const body = {
    occasion: "Nineteenth Sunday after Pentecost",
    scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    sections: ["prayers_of_the_people"],
  };
  const started = performance.now();
  const r = await fetch(API + "/liturgy/generate", { method: "POST", body: JSON.stringify(body),
    headers: { Authorization: "Bearer " + token, "X-Church-Id": churchId, "Content-Type": "application/json" } });
  const ms = Math.round(performance.now() - started);
  const b = await r.json();
  const x = (b.results || [])[0] || {};
  const t = x.text || "";
  console.log(`prayers ${r.status} ${ms}ms ${x.status} ` + (t
    ? `${t.length} chars, ${t.split(/\s+/).length} words, ${t.split(/\n\s*\n/).length} paragraphs, ends: ${JSON.stringify(t.slice(-60))}`
    : JSON.stringify(x.error || b.error)));
})();
```

"Please copy that `prayers` line to me. Then, in Railway → the API service → Deploy Logs (or HTTP Logs), search for `ai_call` and copy the last line that has `completion_tokens=` in it, and the last line that starts with `liturgy.generate`."

- [ ] **Step 7 (agent): The decision rule for Prayers of the People (S Risks 1-2)**

Record the time, the status, the length and the `ai_call` line's `completion_tokens` and `duration_ms`, then apply the first row that matches, and tell the owner the outcome in one or two plain sentences:

| What the check shows | Meaning | Action |
|---|---|---|
| `generated`, under 45 s, `completion_tokens` under 3 600, the text ends with a finished sentence (usually "Amen.") | the 60 s attempt and the 4 000-token budget hold | Record it. No follow-up. |
| `generated` in 45-60 s | it fits, with little room | Record it, and add a follow-up for 4b: tell the owner the Prayers of the People can take most of a minute, and watch it in 4b's manual check. |
| `completion_tokens` of 3 900 or more, or the text stops mid-sentence, or `error ai_upstream_error` (an empty answer) | the answer ran out of its token budget (S Risks 2) | Follow-up PR (on the owner's yes): raise Prayers of the People's `max_completion_tokens` in `liturgy_config.SECTIONS` (a code constant, no API change), then repeat this step. |
| `error ai_timeout` (after about 60 s; with T11) | one 60 s attempt was not enough | Follow-up (owner's decision): shorten the default Prayers of the People prompt's length ("at least 10-15 paragraphs"), or accept typing it; the 90 s page timeout leaves no room for a longer attempt. |
| `error ai_timeout` after about 30 s or 60 s (T11 skipped: 30 s and one retry) | the 30 s attempt was too short | Follow-up PR (on the owner's yes): Task 11 of this plan as written (60 s, no retry), then repeat this step. |
| `error ai_busy` | a slot or OpenAI's rate limit | Run it once more a minute later; record both. |

- [ ] **Step 8 (OWNER, optional): Streamlit smoke on liturgy-frozen**

"If you have a minute: open https://liturgy-frozen.streamlit.app/, sign in, and check that Generate liturgy still works there. Merges never reach it, so this is only a comfort check."

- [ ] **Step 9 (agent): The slice 4a record (records PR, on the owner's yes)**

On a branch `claude/slice-4a-records` from `origin/main`, insert `### Slice 4a record` after `### Slice 3b record`'s table and before `## Backups` in `docs/ops-runbook.md`: a short paragraph (4a merged as PR #<N> with no database change and no new variable; no page calls the routes until 4b; the checks were the owner's) and a table with dated rows for: Merge and deploy (merge sha, pre-deploy with no upgrade, health check, the `AI:` line); CI on `main` (the three jobs' counts); Stored prompts (T13 Steps 9-10: how many churches, all pass or what the owner fixed); Config and church (Step 5's lines, without ids); Generation (Step 6's first run: statuses, the typed Benediction unchanged); Prayers of the People (time, status, length, `completion_tokens`, and Step 7's row and action); the Streamlit smoke (run or skipped); Follow-ups: 4b (the Liturgy step), the reviewer add-on after 4b (owner answer 3), 5a (the Word files' "First Reading" heading and deleting `DOCX_HEADINGS_UNTIL_5A`), 6a (Settings for the default benediction, prompts and prayer library), and anything Step 7 found. Check the section has no `<`, no email, token, key or church id (`grep -Eic '@|bearer|eyJ|sk-|[0-9a-f]{8}-[0-9a-f]{4}-'` on the section prints 0), and that `test_docs.py`, `test_slice1_docs.py` and `test_ops_workflows.py` still pass (`89 passed`). Commit with the two trailer lines. Ask the owner before pushing and opening the PR, and again before merging it.

- [ ] **Step R (only if the 4a release must come out): Revert**

Use this only if the release cannot serve or breaks the church pages (for example `GET /church` failing) and a fix would take too long. No database step: 4a adds no revision and writes nothing. On the owner's yes for each outward action: `git switch -c claude/revert-slice-4a origin/main`, `git revert -m 1 <merge sha>` (commit with the two trailer lines), run both suites (expected `1110 passed, 11 skipped`, and 442 frontend tests), push, open a PR titled "Revert slice 4a", wait for green, merge on the yes. Record the revert in the slice 4a record.

Expected counts after this task: backend `1178 passed, 11 skipped` on `main` (CI `backend-postgres`: `11 passed, 1178 deselected, 1 warning`); frontend `442 passed` in 64 files. The records PR adds no test.

---

## Lessons carried from the slice 2 and 3 builds (P2a-P3b "Build notes")

- **The container restarts.** Commit as soon as a task's checks pass; the controller pushes the backup after each review. If `frontend/node_modules` is gone, `(cd frontend && npm ci)`.
- **The network is filtered.** OpenAI, Railway and the reading sources are unreachable from the build container, so every test fakes them and every live check is the owner's (Task 14).
- **Exact anchors.** Every Replace directive names text that occurs once; if one does not match, the tree differs from the plan: stop and find why rather than editing around it.
- **Don't prove absence by sleeping.** The concurrency test uses a `threading.Barrier` with a timeout; the rate-limit tests use the limiter's `FakeClock`.
- **Grep gates exclude tests** and are read, not obeyed blindly (T10 Step 4, T13 Step 4).
- **Counts are exact.** Every task states its cumulative count; a drift means a missing or extra test, found before moving on.
- **Owner steps one at a time, in plain words**, and every outward action on its own yes.

## Build notes (4a build)

Filled in while Tasks 1-12 are built: each change from the plan as written, its reason, and whether the owner saw it. Task 12 (or a follow-up docs commit before Task 13) writes those that alter S or F as "(4a build)" notes.

- (none yet)

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`; F = foundations. Items owned by 4b or later slices are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1 | `GET /liturgy/config`: user guard, 8 sections equal to the fixture, 17 placements, each anchored once, communion, limits, `ai_available` | T1 (data, fixtures), T8 (`test_config_is_user_scoped`, `test_config_serves_liturgy_config`), T14 Step 5 |
| 2 | Outline equals `build_docx`'s order; `liturgy_outline.json` equals `OUTLINE`; communion output unchanged | T1 (`test_outline_fixture_equals_outline`), T2 (`test_the_outline_is_build_docx_s_heading_order`, `test_communion_docx.py`) |
| 3 | 200 with one `generated` per section in order; stored prompts read per request; `{opening_hymn}` by slot; no `(#None)` | T5 (`test_liturgy_generation.py`), T7 (`test_answers_are_stripped_and_the_church_s_prompts_are_read_fresh`, `test_request_order_after_dedupe_with_four_sections_at_a_time`), T8, T14 Step 6 |
| 4 | No AI: override verbatim, `ai_not_configured`, no call, no charge | T7 (`test_without_ai_an_override_is_verbatim_and_the_rest_not_configured`), T8 (`test_without_ai_a_typed_section_still_comes_back`, `test_only_sections_that_reach_the_ai_are_charged`) |
| 5 | Timeout, busy, upstream, empty answer, unexpected exception: per-section errors, exact messages, HTTP 200, no upstream text | T7 (`test_ai_failures_map_to_their_codes_and_never_leak`), T8 |
| 6 | A malformed template fails only its section (and the length cap); `check_template`'s table; `template_error`, `validate_prompts`, `clean_prompt_overrides` | T3, T5, T7 (`test_a_malformed_template_fails_only_its_own_section`, `test_the_length_cap_is_the_same_prompt_invalid_message`), T8 |
| 7 | Guards: 401, 403, member/admin/owner 200, other church's hymn 404 with the message, 422 with `fields`, route guard and OpenAPI tests | T8 (`test_generate_needs_a_token_and_a_membership`, `test_invalid_bodies_are_422_with_fields`, `test_route_guards.py`, `test_openapi_contract.py`), T13 Step 8 (CI) |
| 8 | The 41st AI section in 10 minutes is 429 with `Retry-After`; only sections reaching the AI are charged | T7 (`test_the_ai_bucket_is_charged_once_...`, `test_a_charge_that_raises_stops_every_ai_call`), T8 (`test_the_41st_ai_section_in_ten_minutes_is_429`, `test_only_sections_that_reach_the_ai_are_charged`) |
| 9 | `GET /church` `default_benediction`: "Halverson", the stored string, `""` | T1 (`test_resolve_default_benediction`), T9, T14 Step 5 |
| 10 | No database session during any AI call | T7 (`test_one_session_reads_everything_and_none_is_open_during_an_ai_call`) |
| 11-17 | The Liturgy step on screen (cards, bulk generate, confirm and Undo, errors only on cards, defaults, custom elements, the shell turned on, navigation) | 4b |
| 18 | Production at 375 px; 6 sections in about a minute | 4b (the step); T14 Step 6 measures the backend half (one section per request, Prayers of the People timed) |
| 19 | Rubric checklist and sermon block, wording and order; typed sections never sent; the two "3 sentences" defaults; PR #4's tests ported | T3 (defaults), T5, T7 (`test_the_rubric_is_read_fresh_...`, `test_the_sermon_goes_to_every_ai_section_and_no_override`), T10 (`test_generate_liturgy.py` retargeted) |
| 20 | The client sends the sermon text; the server never fetches it | 4b (the client); T8 (`SermonText` accepted and bounded; no fetch in `usecases/liturgy.py`) |
| 21 | The voice hook: caps, strip, drop order, never `prompt_invalid`, byte-identical baseline; the library read fresh in the same session | T4, T5 (`test_without_a_voice_...`, `test_the_voice_blocks_...`, `test_the_budget_drops_...`), T7 (`test_the_library_is_read_fresh_...`, `test_one_session_...`, `test_the_worst_case_prayers_of_the_people_...`) |

### S sections

| S item | Task(s) |
|---|---|
| Backend 1 `liturgy_config.py` | T1 (clarifications 3, 5) |
| Backend 6 `worship_service._add_communion_liturgy`; Testing "Characterization first" (communion) and "Outline matches the docx" | T2 (clarifications 4, 15) |
| Backend 2 validator; Interfaces 6a (`template_error`, `validate_prompts`, `clean_prompt_overrides`) | T3 (clarifications 10, 11) |
| Backend 6 `prayer_library.py`; Interfaces 6a (prayer library read path) | T4 (clarification 13) |
| Backend 2 prompt building and its amendment; Testing `test_liturgy_generation.py`, `test_liturgy_prompts.py` additions | T5 (clarifications 6, 8, 9, 21) |
| Backend 6 `repos/hymns.py`, `repos/churches.get_church_prompts` | T6 (clarification 7) |
| Backend 3 `usecases/liturgy.py` and its amendment; API semantics 1-10; Tenancy | T7 (clarifications 12, 19, 20) |
| API routes, Schemas, "Deviation from F"; Backend 4; `api/ratelimit.py` (`consume(cost=)` already on `main`); `api/schemas.py` `SermonText` | T8 (clarifications 14, 17, 22) |
| API `GET /church`; Backend 5 | T9 (clarification 18) |
| Backend 6 `generate_liturgy` deleted; "Streamlit coupling removed"; Testing amendment (PR #4 retargeted) | T10 (clarifications 2, 12) |
| Risks 1 (timeout) | T11 (owner question 1), T14 Steps 6-7 |
| Risks 2 (token budgets) | T14 Steps 6-7 |
| Risks 3 (stored prompts) | T13 Steps 9-10 (owner answer 4a; clarification 23) |
| Risks 6 (legacy liturgy keys) | 5a |
| Risks 7 (custom elements) | answered (owner answer 1); T12 (F D17) |
| Data and migrations: no revision; `default_benediction`, `rubric`, `prayer_library` read only | T1, T4, T7, T9 |
| Frontend changes, UX, Testing "Frontend", Manual checklist | 4b |
| Amendment 2026-09-26: service reviewer | the add-on after 4b (owner answer 3); 4a keeps its "Tests before and after" rule (T5 Step 6 grep) |

## Questions for the owner

Before the build (both in one message; the plan is written for "yes"):
1. **Prayers of the People: one 60 s attempt, no retry, from the start?** Recommended: yes (T11; clarification 16). "No" skips T11 and keeps S Risks 1's measure-then-fix path (T14 Step 7's last timeout row).
2. **"After First Reading" in the custom-element place list?** Recommended: yes (clarification 3). "No" keeps app.py's "After Old Testament Reading" (T1's label and test change back).

Owner steps still to come: the read-only list of stored prompts before ready (T13 Steps 9-10), and the live checks with a real Prayers of the People after the merge (T14 Steps 3, 5-6).
