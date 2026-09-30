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
  - Every task's code in this plan was written and run by the planner in a throwaway worktree of `9ab3fa6`, with each red run and every count in the table observed. The plan text was then replayed onto a clean worktree of `9ab3fa6` (every Create, Append, Replace and Run directive below applied in order by a script, Tasks 1-12), reproducing each count. Not run while planning: the pushes and CI (Task 13), the owner steps (Tasks 13 Step 9 and 14), and any call to OpenAI (the container cannot reach it).

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
- **In `path`, replace from the line starting `A` up to (not including) the line starting `B` with:** the lines from the one line starting with `A` up to the one line starting with `B` are replaced by the block.
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
