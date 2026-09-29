# Slice 3b: Hymns Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 3b of slice 3, the Hymns step, live. After it merges, a signed-in member who opens step 2 of the Service Builder (`/builder/hymns`) fills the Opening, Response and Closing hymns from the church's own hymnal by number or title, sees which hymns were sung (or are planned) within 12 weeks of the service and can hide them without losing a pick, sees the hymns that match the day's readings and adds one to a slot, and asks the AI for suggestions: empty slots get the top pick and every slot gets 2 to 4 one-tap "other ideas". Newer hymns show "Written {year}". The step bar counts Hymns ("n of 3", then "Complete"), Review lists each empty slot under "Still needed", and the summary lists the three hymns. Choosing a hymn or a hymnal now counts as unsaved work; the Exclude switch and the AI's other ideas do not (owner answer 1). Two small backend changes ride along: the AI prompt names the church season and asks the model to avoid hymns tied to another season or feast (owner answer 3), and, only if Task 1 finds the new code at fault, a fix to the recent-use read (owner answer 2). There is no migration, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** 3a built the four routes (`GET /hymnals`, `GET /hymns`, `POST /hymns/scripture-matches`, `POST /hymns/suggestions`) and their generated types; 3b adds the screen. Pure pieces live in `src/lib/hymns/`: `picks.ts` (`pickFromHymn`, `reconcilePick`, `setSlot`, `clearSlot`, `applySuggestions`, `swapAlternative`, `duplicateSlots`, `setHymnal`, `setExcludeRecent`), `hymnal.ts` (`selectHymnal`), `filter.ts` (`filterHymns`), `labels.ts` (slot copy, notices, `recentUseLabel`, `newerYearLabel`), `match-request.ts` (`cleanRefs`, `buildMatchRefs`) and `suggest-request.ts` (`buildSuggestionRequest`); `lib/dates.ts` gains `formatAbbrevDate`. `src/lib/queries/hymns.ts` holds `useHymnals`, `useHymnList`, `useHymnLists`, `useScriptureMatches` and `useSuggestHymns` (church-scoped, so every request carries `X-Church-Id`). The UI kit gains `components/ui/switch.tsx` and the generic long-list picker `components/app/search-combobox.tsx`. `src/components/builder/hymns/` holds the step: `HymnsStep` composes `HymnsToolbar` (hymnal `Select`, Exclude `Switch`, `SuggestHymnsButton`), three `HymnSlotCard`s (each a `HymnLabel` row or a `HymnPicker`, its notices, and `AlternativeChips`), `ScriptureMatches` and the Hymnary credit. Last, `SHIPPED_STEPS` gains `"hymns"`, the hymns route renders the step, `stillNeeded` lists empty slots and `SummaryPanel`'s Hymns block becomes `SummaryHymns`. Every page stays a client component (F §4.1). On the backend, `vanderbilt_lectionary.church_season(d)` names the season from the service date and `hymn_suggest.build_prompt` gains a `season` keyword.

**Tech Stack:** Next 16.3.6 (App Router, Turbopack), React 19.2.8, TypeScript 5, Tailwind 4, Base UI 1.8 (shadcn "base-nova"), TanStack Query 5, sonner, zod 4.6.5, Vitest 3.2.7 (`unit` node and `dom` jsdom projects) with Testing Library; Python 3.11, FastAPI, pytest (SQLite locally, Postgres in CI); GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Vercel (frontend), Railway (API), Supabase Postgres, OpenAI (`gpt-4.1-mini`).

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`. The 3b parts: "User experience" (all of it), "Interfaces with other slices" rows 2, 5a and 6a, "Frontend changes", "Behavior changes" 1-5, 10-13, 15, 16, 19 and 20 (the screen halves), "Testing → Frontend (Vitest)", the port-ledger table, "Manual checks", AC10-AC14, AC17 and AC20 (screen half), and every "(3a plan)" and "(3a build)" note.
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (§4.1, §4.4, §4.6 draft, §4.7 status, §4.8 errors, §4.9 Base UI, §4.10 dates, decision D16, the Amendments table).
- Slice 2c plan ("P2c"): `docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md`, its structure, conventions, "Build notes (2c build)" and "Lessons carried". Slice 3a plan ("P3a"): `docs/superpowers/plans/2026-09-29-slice-3a-hymns-backend.md` (the route bodies, Task 4 Step 1's owner-query format, Tasks 16 and 17).
- Production facts: `docs/ops-runbook.md` "Slice 2c record" and "Slice 3a record": one hymnal, GG2013, 853 hymns, 795 with scripture references, `default_hymnal` null and `effective_hymnal` GG2013; 244 hymns flagged newer than preferred; `gpt-4.1-mini`, a suggestion takes about 4 s; the Console check found no recent use around October 4, 2026 although `hymn_usage` holds 90 rows; the response slot got two Palm Sunday hymns on the Nineteenth Sunday after Pentecost.
- The real code at `b47abba` (slices 2a-2c and 3a merged): `frontend/src/lib/draft/*` (`schema.ts` `HymnPick` and the `hymns` block, `status.ts` `stepStatus`/`isPristine`/`withoutTranslation`/`stillNeeded`, `fingerprint.ts` `isDirty`, `mapping.ts` `draftToServicePayload`, `store.ts` `rollForward`, `steps.ts` `SHIPPED_STEPS`, `date-effects.ts`), `lib/queries/{client,keys,church,passages}.ts`, `lib/api/{client,errors,timeouts,types}.ts` and `schema.d.ts` (`HymnalListOut`, `Page_HymnOut_`, `HymnOut`, `ScriptureMatchIn`, `ScriptureMatchesOut`, `HymnMatchOut`, `HymnSuggestionIn`, `HymnSuggestionsOut`, `SuggestedHymnOut`), `lib/{dates,latest,storage,urls}.ts`, `components/builder/*`, `components/app/*`, `components/ui/*`, `test/{fake-api,render,mocks,setup-dom}.ts(x)`, `test/fixtures/index.ts`; and `backend/usecases/hymns.py`, `backend/hymn_suggest.py`, `backend/hymn_usage.py`, `backend/api/routes/hymns.py`, `backend/vanderbilt_lectionary.py`.
- Facts checked for this plan (tree `b47abba`, 2026-09-29):
  - Backend baseline `1106 passed, 11 skipped`; frontend `356 passed` in 55 files; `npm run typecheck` and `npm run lint` clean.
  - `components/ui/` has `combobox`, `badge`, `alert`, `select`, `dropdown-menu`, `collapsible`, `sonner`, but no `switch`; no generic `SearchCombobox` exists (slice 1's `TimezoneCombobox` uses the Combobox directly); `lib/dates.ts` already has a `formatShortDate` ("October 4"); `keys.hymns(id, params)` already exists; `stillNeeded` has no hymn rows yet; `isPristine` counts the slots but not `hymns.hymnal`; `schema.d.ts` already has every 3a type, so `npm run gen:api` changes nothing.
  - The build container reaches registry.npmjs.org, PyPI and raw.githubusercontent.com, but not ui.shadcn.com, Railway, OpenAI, Supabase or the reading sites. No test needs the network.
  - Every task's code below was written and run by the plan's writer in a throwaway worktree at `b47abba` (hard-linked `node_modules`, `cp -al`; `.venv` linked), one commit per task, with every stated count, every "see them fail" output and typecheck and lint observed. Not run while planning: a successful `shadcn add` (the registry is blocked; T7 records the failure), the pushes and CI (T14), and the OWNER steps (T1, T15).
  - Where S and the code or F disagreed, the code and F won unless an owner answer says otherwise; each case is a numbered clarification below.

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run the frontend as `(cd frontend && …)` from the repo root; the working directory resets between commands. Use absolute paths when a tool asks. No foreground `sleep`.
- Run one test file with `(cd frontend && npx vitest run <path> 2>&1 | tail -15)`. Run the whole suite with `(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")`, then `(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)`.
- Run the backend suite with `.venv/bin/python -m pytest -q | tail -1` from the repo root.
- `node_modules` exists. If it is missing after a container restart, run `(cd frontend && npm ci)` (the npm registry is reachable). Turbopack refuses a symlinked `node_modules`: `npm run build` runs in the real checkout (T14), and a throwaway worktree copies it with `cp -al`, never `ln -s`.
- Branch: `claude/slice-2-plan-4q33le`, at `origin/main` `b47abba` plus this plan's commit(s). The plan lives at `docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md`.
- Stage files by name (paths with parentheses in single quotes). `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Commits end with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`; when the session's attribution asks for it, a `Claude-Session: <url>` line stands immediately before or after that line (T14's trailer check matches the `Co-Authored-By` line anywhere in the message, and its commit-list check compares subjects only). Subjects read "Area: plain words (S …, owner answer …)". Use TDD: write the failing test first and quote its failure.
- **Backup push after every task** (standing rule, as in 2a-3a): the controller pushes the working branch after each task's commit and review with `git push origin claude/slice-2-plan-4q33le` (never `--force`; there is no open PR, so the push asks nobody; Vercel may build a preview). A fix asked for by a task's review is a new commit, `Fix: <what> (Task <n> review)`, pushed the same way, never an amend of a pushed commit; T14 lists it. The container can restart and lose uncommitted work, so commit as soon as a task's checks pass. If the push is refused because the remote moved, stop and ask the controller.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and includes the line given in T14 ("Tests: frontend 356 → … ; backend 1106 → … passed, 11 → 11 skipped").
- New prose for the owner has no em dashes and no flattery, and leads with the point. Copy quoted from S keeps its own punctuation (for example "Too many requests — try again in {n} s.", "After the sermon — responds to the scripture (NT reading)", "Still working — this can take up to a minute.", "No Opening hymn — Choose one", the Hymnary credit).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. The build of T2-T13 does not wait for T1's owner steps.

### Baselines and counts
- Starting baselines: frontend **356 passed in 55 files**, typecheck and lint clean; backend **1106 passed, 11 skipped**. If any baseline differs, stop and ask.
- Planned cumulative counts. Each frontend delta is exactly the number of `it(` blocks the task adds (an edited test counts 0). If a count drifts, stop and find why.

  | After | Frontend tests (delta) | Test files (delta) | Frontend count | Backend |
  |---|---|---|---|---|
  | T1 | 0 (no file changes; Task 1b, if added, states its own) | 0 | 356 in 55 | 1106 passed, 11 skipped |
  | T2 | 0 | 0 | 356 in 55 | **1110** passed, 11 skipped (`test_lectionary_domain.py` +2, `test_hymn_suggest.py` +1, `test_api_hymn_suggestions.py` +1) |
  | T3 | +3 (`draft/status.test.ts` +1, `draft/fingerprint.test.ts` +1, `draft/store.test.ts` +1) | 0 | 359 in 55 | unchanged |
  | T4 | +7 (`lib/hymns/picks.test.ts`, new) | +1 | 366 in 56 | unchanged |
  | T5 | +16 (`filter.test.ts` 6, `labels.test.ts` 4, `match-request.test.ts` 2, `suggest-request.test.ts` 3, `dates.test.ts` +1) | +4 | 382 in 60 | unchanged |
  | T6 | +6 (`queries/hymns.test.tsx`, new; `keys.test.ts` edited, 0) | +1 | 388 in 61 | unchanged |
  | T7 | +4 (`components/app/search-combobox.test.tsx`, new) | +1 | 392 in 62 | unchanged |
  | T8 | +11 (`hymn-label.test.tsx` 2, `hymns-step.test.tsx` 9, both new) | +2 | 403 in 64 | unchanged |
  | T9 | +4 (`hymns-step.test.tsx`) | 0 | 407 in 64 | unchanged |
  | T10 | +7 (`hymns-step.test.tsx`) | 0 | 414 in 64 | unchanged |
  | T11 | +5 (`hymns-step.test.tsx`) | 0 | 419 in 64 | unchanged |
  | T12 | +2 (`draft/status.test.ts` +1, `builder-shell.test.tsx` +1; two status tests and three shell tests edited, 0) | 0 | 421 in 64 | unchanged |
  | T13 | 0 | 0 | 421 in 64 | 1110 passed, 11 skipped (one assertion in `test_slice1_docs.py` edited) |
  | T14, T15 | 0 | 0 | 421 in 64 | 1110 passed, 11 skipped |

- CI `backend-postgres` shows `11 passed, 1110 deselected` after T2 (the Postgres tests are unchanged).
- The step tests fake only `Date` and wait on the app's real timers (the draft's 400 ms writes, the list and match requests), so `hymns-step.test.tsx` takes about 16 s; one test fakes `setTimeout` as well (the 8-second "Still working" line) and says why, and one waits out a real 1-second `Retry-After`.

### Code rules (F §4)
- Every file under `src/app/` that renders is a client component (`"use client"`, F §4.1). Pages and components never call `apiFetch` (F §4.4): the step uses the hooks in `lib/queries/hymns.ts`.
- Base UI rules (F §4.9): generated components only, hand edits limited to variants; no `asChild` (use `render`, or `buttonVariants` on the element); a Select gets `items`; toasts stay on sonner. The one recorded exception is clarification 4 (the registry is blocked, as in 2b and 2c).
- Date-only values stay `YYYY-MM-DD` strings; nothing outside `lib/dates.ts` calls `new Date(` on a date-only value (`dates.guard.test.ts`, F acceptance 12).
- Browser storage goes through `lib/storage.ts` only (F §4.3); 3b adds no storage key.
- Hymn titles, references and server messages render as React text only (`react/no-danger` is an error); links render only through `safeHttpsUrl` with `target="_blank" rel="noopener noreferrer"`.
- Inputs are `text-base md:text-sm` (the generated `Input`) so iOS does not zoom; primary actions and toggles are 44 px (`size="touch"`, `h-11`).
- DOM tests that depend on "today" fake only `Date` (`vi.useFakeTimers({ toFake: ["Date"] })` plus `vi.setSystemTime(DRAFT_NOW)`), so user-event's and the app's timers keep running. A test that must fake `setTimeout` too (the 8-second "Still working" line) calls `vi.useRealTimers()` first and says why.
- A test never proves that something did not happen by sleeping: it first waits for a positive condition that comes after it, then checks the absence.
- Grep gates exclude test files.

### Messages (verbatim, from S)
- Header: "Hymns"; "Choose an opening, response and closing hymn."
- Slots: "Opening hymn" / "Gathering / call to worship"; "Response hymn" / "After the sermon — responds to the scripture (NT reading)"; "Closing hymn" / "Joyful / sending". Buttons "Change"; ✕ aria-label "Remove {title}"; Listen link aria-label "Listen to {title} on Hymnary.org". Toast "Removed {title}." with "Undo".
- Notices: "Used on {September 7, 2026} — within 12 weeks of this service."; "Also planned for {October 18, 2026} — within 12 weeks of this service."; "Not in your hymnal. Choose a replacement."; "Also chosen as the {Opening|Response|Closing} hymn."; "No suggestion for this slot."
- Chips: group "Other ideas for the {slot} hymn"; chip "Use {title} as the {slot} hymn", or "Use {title}, written {text_year}, as the {slot} hymn"; badges "Used Sep 7", "Planned Oct 18", "Written {text_year}"; heading "Other ideas".
- Picker: placeholder "Search by title or number"; "Loading hymnal…"; hints "Type to search {n} hymns.", "Showing 50 of {n} — keep typing to narrow.", "No hymns match “{q}”.", "{k} more used within 12 weeks are hidden."
- Toolbar: "Hymnal"; item "{code} · {hymn_count} hymns"; "Which hymnal to choose hymns from for this service."; "{code} is no longer in your church's hymnals. Showing {effective} instead."; "{code} has no scripture references, so scripture matches and AI response picks will be weaker."; "Exclude hymns used within 12 weeks"; "Hides hymns sung in the 12 weeks before this service or planned in the 12 weeks after it."; "{n} hymns are hidden."; "Pick a valid date in step 1 to check recent use."
- Suggest: "Suggest hymns"; "Fills empty slots and shows other ideas under each hymn."; "Suggesting…"; "Still working — this can take up to a minute."; "Cancel"; "Tip: add the readings in step 1 first — suggestions use them."; "Suggestions ready. Tap an idea under a hymn to swap it in." (+ " {n} recently used hymns were left out."); "Suggestions favor older and familiar hymns. Newer hymns show the year their words were written."; "The AI didn't pick any hymns from this hymnal. Try again, or choose hymns yourself."; "The date changed while suggestions were loading. Try again."; errors "AI suggestions aren't set up on this app yet. You can still choose hymns yourself.", "The AI service is busy. Try again in a minute.", "The AI took too long to answer. Try again.", "The AI service had a problem. Try again in a moment.", the server's `invalid_request` message, "Too many requests — try again in {n} s." then "Try again now." (P2c owner answer D), "This is taking too long. Try again."
- Matches: "Hymns for the readings"; "Additional scripture" (placeholder "e.g. Matthew 17"), "Search"; groups "Matches the readings" and "Same chapter"; "Matches {refs}"; "Add" menu "Opening hymn / Response hymn / Closing hymn"; toast "{Slot} hymn changed to {title}." with "Undo"; "{k} recently used matches are hidden." with "Show them"; "Couldn't read “{text}” as a scripture reference."; "Add the readings in step 1, or type a scripture reference here." with "Go to readings"; "No hymns in {hymnal} match these readings. Try a shorter reference, such as “Matthew 17”."; "{code} has no scripture references, so it can't be searched by scripture."; "Couldn't search the hymnal." with "Retry"; credit "Hymn information and links courtesy of Hymnary.org. Individual hymns may carry their own copyright — see each hymn's page."
- Whole step: "Couldn't load this church's hymnal." with "Retry"; "This church's hymnal is empty"; "Add hymns in the current app under Settings → Hymns." (before 6a; after 6a "Add hymns on the Settings → Hymns page to choose hymns here." with "Open Settings → Hymns").
- Shell: Hymns status "{n} of 3" / "Complete"; "Still needed" rows "No Opening hymn — Choose one", "No Response hymn — Choose one", "No Closing hymn — Choose one"; summary rows "Opening · #403 Come, Thou Almighty King" ("Opening · {title}" with no number) or "No Opening hymn".

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried over from 2a-3a). Each use is recorded as a numbered clarification marked "(owner decision 1)".
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
3. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
4. **Spec decisions 3 and 9 and F D16:** AI fills only empty slots and gives every slot 2-4 other ideas; free-text hymns stay removed; the tightened scripture matcher (3a).
5. **Production:** frontend https://worship-service-builder.vercel.app (Vercel), API https://church-production-74ca.up.railway.app (Railway), Supabase project `worship-staging` (the one both the new app and, per the runbook, the backups use). The build container cannot reach Railway, OpenAI or Supabase; no test needs the network.

### Owner answers (2026-09-29, binding for the plan; "all recommended")
- **1. Unsaved work.** Changing a hymn slot or the hymnal counts as unsaved work: "New service" asks first, and the mount-time roll-forward keeps the date of such a draft. The Exclude switch and the AI's other ideas (`hymns.alternatives`) do not count. This is S "Draft usage". Today `isPristine` counts the slots but not `hymns.hymnal`, and the fingerprint payload already holds the slots and the hymnal but not the switch or the ideas; T3 adds the hymnal to `isPristine` and pins all four fields with tests (clarification 2).
- **2. Recent use.** The live 3a check found no recent use around October 4, 2026 although `hymn_usage` has 90 rows, and the owner has prepared services in the old app within the last 90 days. T1 investigates with read-only queries in the Supabase project the new app uses and a comparison with the new app's church; if the new code is wrong, a backend fix task lands in 3b; if it is data or the old app (another database or church), it is recorded and the controller asks the owner. The other tasks do not wait for it.
- **3. Church season in the AI prompt.** The prompt names the liturgical season, computed from the service date with the lectionary module's calendar, and asks the model to avoid hymns tied to another season or feast (Palm Sunday and Holy Week, Christmas, Easter, Advent hymns outside their season) unless the readings call for them. The clipping, `_field` sanitising and the 24 000-character budget stay; no API change (T2; clarification 21).
- **4. The "Written {year}" badge** stays as S designs it.
- **5. Testing:** automated tests, then a guided owner check on the phone one step at a time and a quick look on a computer, as in 2c (T15). T13 appends "## Slice 3" to `docs/manual-verification.md` from S "Manual checks".
- **Standing rules:** one PR for 3b; backup pushes to the working branch after each task are authorized (the controller does them); every other outward action asks first.

### The 3b scope (S "Frontend changes"; F §7.2)

| Piece | Task | Note |
|---|---|---|
| Recent-use investigation (owner answer 2) | T1 | owner queries, agent check, decision point; a fix task only if the code is wrong |
| Church season in the prompt (owner answer 3) | T2 | backend; `church_season`, `build_prompt(season=)` |
| `isPristine` counts the hymnal (owner answer 1) | T3 | the only change to 2b's draft rules |
| `lib/hymns/picks.ts`, `hymnal.ts` | T4 | S "Pure-function contracts" |
| `lib/hymns/filter.ts`, `labels.ts`, `match-request.ts`, `suggest-request.ts`; `formatAbbrevDate` | T5 | S Picker ranking, notices, `buildMatchRefs`, `buildSuggestionRequest` |
| `lib/queries/hymns.ts`, `keys.hymnMatches`, the suggestions timeout, `features.ts`, fixtures | T6 | S Queries |
| `components/ui/switch.tsx`, `components/app/search-combobox.tsx` | T7 | clarifications 3, 4 |
| `HymnsStep` states, `HymnLabel`, `HymnSlotCard`, `HymnPicker` | T8 | S Slot cards, Picker, Whole-step states |
| `HymnsToolbar`: hymnal Select, Exclude switch | T9 | S Toolbar |
| `SuggestHymnsButton`, `AlternativeChips` | T10 | S AI suggestion flow, chips |
| `ScriptureMatches` | T11 | S Hymns for the readings |
| `"hymns"` in `SHIPPED_STEPS`, the page, `SummaryHymns`, `stillNeeded` rows | T12 | S Builder shell |
| S and F "(3b plan)" notes, "## Slice 3" checklist, heading pin | T13 | S Manual checks |

## Spec clarifications

The code and F win over S's outline, and the owner's answers over both. Each item says whether the owner would notice it: **[owner-visible]** items are put to the owner in "Questions for the owner" at the end (confirm or change before T2 starts; T1 does not wait); the rest are owner decision 1 (no owner-visible change) or plain readings of S.

1. **The 3b scope and where the tests live.** The scope is the table above. S's Testing table extends `components/builder/summary-panel.test.tsx`, which does not exist: 2c tested the summary, the step bar and "Still needed" in `builder-shell.test.tsx`, so T12 extends that file. The queries get `lib/queries/hymns.test.tsx` (F §5.2: every query module is tested); S's `hymns-step.test.tsx` list is split across T8-T11 by block; `hymn-label.test.tsx` is T8's.
2. **[owner-visible] What counts as unsaved work (owner answer 1).** Choosing a hymn for a slot, or a hymnal in the Select, makes "New service" ask "Start a new service?" first and keeps the date of the draft when that Sunday passes (the mount-time roll-forward). The Exclude switch and the AI's other ideas never count. `isPristine` already counted the slots; T3 adds the hymnal. Choosing the church's own effective hymnal again stores `null` (T4's `setHymnal`, like 2c's translation), so switching away and back is not unsaved work, and a later change of the church's default flows through. The step never writes the hymnal by itself, even when the stored code has vanished.
3. **`SearchCombobox` is new.** S expected slice 1 to have built it under `TimezoneCombobox`; slice 1 used the Combobox directly. T7 creates `components/app/search-combobox.tsx`, where the caller ranks and caps the rows (`search`) and Base UI renders only those (`filteredItems`); `TimezoneCombobox` is left as it is.
4. **`switch.tsx` is rebuilt from the upstream shadcn source**, as 2b and 2c did for their components (the registry, ui.shadcn.com, is blocked from the container). T7 first tries `npx shadcn@latest add switch`, then writes shadcn-ui/ui@`db2db460` `apps/v4/registry/bases/base/ui/switch.tsx` through the installed shadcn 4.21.0 CLI's style transform and Prettier, the pipeline that reproduces 2c's `collapsible.tsx` exactly; the only change is a header comment. S's other "generated" components (`combobox`, `badge`, `alert`) exist already. (Owner decision 1; the exception the owner accepted for 2b and 2c.)
5. **`formatAbbrevDate`.** S's Files list adds `formatShortDate(iso) -> "Sep 7"` to `lib/dates.ts`, but 2b's `formatShortDate` already returns "October 4" and is used on screen. The new helper is `formatAbbrevDate(iso, contextIso?)`, adding the year only when it differs from the service date's.
6. **`useSuggestHymns` returns `suggest()`, and the stale checks live in it.** S puts the latest-request, church and mount checks in the mutation's `onSuccess`. T6's hook returns `{suggest, isPending}`; `suggest(body, signal)` resolves `ok`, `error` or `superseded` (never throws), so the button has one place to decide. The date check and the functional `update` stay in the button (T10), which has the draft.
7. **Loading order** (owner decision 1). The hymn lists are asked for only after `GET /hymnals` answers with at least one hymnal, so an empty church asks for none and its picks show "Not in your hymnal" at once. The toolbar shows skeletons until `GET /hymnals` answers (S: "and the hymnal list"), because a date change refetches the list, and a skeleton would unmount a pending Suggest; the pickers still read "Loading hymnal…" while a list loads.
8. **[owner-visible] Suggest's network and server errors show as a toast.** S says network errors and 500s "use the global handling (F §4.8)", which in this app is a toast ("Something went wrong. (Ref: …)"); the inline `Alert` holds only the AI and validation codes of S's table. After a 429 the Alert reads "Too many requests — try again in N s." and then "Try again now." once the wait has passed (2c's owner answer D).
9. **`picks.ts` signatures.** The draft recipes (`setSlot`, `clearSlot`, `setHymnal`, `setExcludeRecent`) take the whole draft, as 2c's readings recipes do, so the screen calls `update((d) => setSlot(d, …))`; the suggestion helpers take the `hymns` block as S names them. `reconcilePick` gets a third argument, the selected hymnal, for a pick with no hymnal (an archived one, 5a); `duplicateSlots` takes the slots.
10. **`buildSuggestionRequest` takes the church's translation** as a fourth argument (S reads `church.effective_translation` inside, but the function is pure), and the cache reader the button passes is `queryClient.getQueryData(["passage", translation, ref])`. It never fetches.
11. **[owner-visible] Where recent use shows.** The notice under a pick shows only with a valid service date. A picker row shows its "Used Sep 7" badge only while Exclude is off (while on, the row is hidden and counted). Other ideas always carry their badge. Matches: hidden while Exclude is on; shown with Exclude off, or after **Show them**, they carry their badge (S names the badge only for Exclude off).
12. **The picker also ignores punctuation**, not only accents and case, so "come thou" finds "Come, Thou Almighty King" (S Picker "Ranking" says accent- and case-insensitive).
13. **[owner-visible] Counts of one are singular**: "1 hymn is hidden.", "1 more used within 12 weeks is hidden.", "1 recently used match is hidden." and " 1 recently used hymn was left out." S writes only the plural.
14. **[owner-visible] Names screen readers hear.** Chips are "Use {title} as the opening hymn" and their group "Other ideas for the opening hymn" (the slot in lower case, S's `{slot}`); each match's **Add** button is named "Add {title}", so a list of buttons tells them apart (S names it "Add"); the step's heading is "Hymns" (level 2) with S's line under it.
15. **Undo toasts.** `useUndoToasts` (a file S does not list, `components/builder/hymns/use-undo-toasts.ts`) keeps the ids of the toasts it showed, dismisses them when the step unmounts, and ignores an Undo whose church is no longer the active one (S "Undo toasts never outlive the step"). A match's **Add** shows its toast only when the slot held a different hymn (S: "If the slot was filled").
16. **[owner-visible] What changes on screens 2b and 2c built** (S "Builder shell"): the step bar shows Hymns as "0 of 3" … "Complete" instead of "Soon"; Review's "Still needed" adds "No Opening hymn — Choose one" and the like for each empty slot; the summary's Hymns block lists the three slots instead of "Available soon". Liturgy keeps "Soon" and "Available soon".
17. **The manual checklist** (T13): S's ten checks as "## Slice 3" in `docs/manual-verification.md`, with check 11 for the church season (owner answer 3), check 12 for "New service" (owner answer 1) and "(owner, after 3b)" on the items the guided check covers (owner answer 5). `test_slice1_docs.py` pins the last four `##` headings instead of three.
18. **No API change.** `schema.d.ts` already has every 3a type, so `npm run gen:api` changes nothing; the only backend changes are T2's prompt line and T13's docs-test edit (and Task 1b's fix, only if T1 finds the code at fault).
19. **"Hymns for the readings" opens at `md+` as it first renders** (a media query read once), and a phone's rotation does not open or close it (owner decision 1). The request runs while it is closed, so the count shows on its title.
20. **Test helpers and the feature switch.** `test/fixtures/index.ts` gains `hymnId`, `hymn`, `suggested`, `hymnals` (T4) and `gg2013`, `ph1990`, `twoHymnals`, `hymnListRoute`, `hymnMatch`, `scriptureMatches`, `hymnSuggestions` (T6). `SETTINGS_HYMNS_READY` lives in a new `lib/features.ts` (S lists it); 6a flips it.
21. **[owner-visible] The church season in the AI prompt (owner answer 3; T2).** The server names the season from the service date (`church_season`: Advent, Christmas Eve, Christmas, Epiphany of the Lord, Season after the Epiphany, Lent, Holy Week, Easter, Day of Pentecost, Season after Pentecost) and adds one guidance line; nothing is read from the request, the clipping and the 24 000-character budget stay, and there is no API change. The member sees it only in which hymns are suggested.
22. **[owner-visible] What the counts count.** The toolbar's "{n} hymns are hidden." counts every recently used hymn with a title in the selected hymnal; the picker's footer counts only those matching what was typed.

### Risks carried into the plan
- **Recent use in production** (owner answer 2). Until T1's finding, the switch may hide nothing in production; the owner's check (T15 Step 6) expects what T1 found. 5a records use on every save in the new app.
- **Live AI.** The suggestions come from `gpt-4.1-mini` through Railway; the tests use fakes. The season line changes the prompt only; if the owner still sees out-of-season hymns (T15 Step 7), that is a follow-up for the prompt, not a 3b blocker.
- **Real-timer tests.** `hymns-step.test.tsx` waits on real 400 ms writes and one real 1-second `Retry-After`. T14 runs the suite three times and with the clock moved forward; a flaky run is fixed by making the test deterministic, never by retrying.
- **Turbopack refuses a symlinked `node_modules`**; `npm run build` runs in the real checkout (T14).
- **The registry stays blocked**; T7 records the attempt and uses clarification 4's file.

## File Structure

All paths are from the repo root. "(church)" means `frontend/src/app/(signed-in)/(church)`; "hymns/" means `frontend/src/components/builder/hymns/`; "lib/hymns/" means `frontend/src/lib/hymns/`.

**Created**

| Path | Responsibility | Task |
|---|---|---|
| `docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md` | this plan | 0 |
| `lib/hymns/picks.ts` (+ `picks.test.ts`) | `pickFromHymn`, the draft recipes, `reconcilePick`, `applySuggestions`, `swapAlternative`, `duplicateSlots` | T4 |
| `lib/hymns/hymnal.ts` | `selectHymnal` | T4 |
| `lib/hymns/filter.ts` (+ `.test.ts`) | `filterHymns`, `foldText`, `PICKER_LIMIT` | T5 |
| `lib/hymns/labels.ts` (+ `.test.ts`) | `SLOT_META`, notices, badges, `newerYearLabel`, `chipName` | T5 |
| `lib/hymns/match-request.ts` (+ `.test.ts`) | `cleanRefs`, `buildMatchRefs` | T5 |
| `lib/hymns/suggest-request.ts` (+ `.test.ts`) | `buildSuggestionRequest` | T5 |
| `frontend/src/lib/queries/hymns.ts` (+ `.test.tsx`) | `useHymnals`, `useHymnList`, `useHymnLists`, `useScriptureMatches`, `useSuggestHymns` | T6 |
| `frontend/src/lib/features.ts` | `SETTINGS_HYMNS_READY` | T6 |
| `frontend/src/components/ui/switch.tsx` | Base UI switch (clarification 4) | T7 |
| `frontend/src/components/app/search-combobox.tsx` (+ `.test.tsx`) | `SearchCombobox` (clarification 3) | T7 |
| `hymns/hymns-step.tsx` (+ `hymns-step.test.tsx`) | `HymnsStep` (grows in T9-T11) | T8 |
| `hymns/hymn-slot-card.tsx` | `HymnSlotCard` | T8 |
| `hymns/hymn-picker.tsx` | `HymnPicker`, `pickerSearch` | T8 |
| `hymns/hymn-label.tsx` (+ `hymn-label.test.tsx`) | `HymnLabel` | T8 |
| `hymns/use-undo-toasts.ts` | `useUndoToasts` | T8 |
| `hymns/hymns-toolbar.tsx` | `HymnsToolbar`, `ToolbarSkeleton`, `HymnalPicker`, `ExcludeSwitch` | T9 |
| `hymns/suggest-hymns-button.tsx` | `SuggestHymnsButton`, `suggestErrorMessage` | T10 |
| `hymns/alternative-chips.tsx` | `AlternativeChips` | T10 |
| `hymns/scripture-matches.tsx` | `ScriptureMatches` | T11 |
| `frontend/src/components/builder/summary-hymns.tsx` | `SummaryHymns` | T12 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/vanderbilt_lectionary.py`, `backend/hymn_suggest.py`, `backend/usecases/hymns.py` (+ `test_lectionary_domain.py`, `test_hymn_suggest.py`, `test_api_hymn_suggestions.py`) | `church_season`; the season lines in the prompt (owner answer 3) | T2 |
| `frontend/src/lib/draft/status.ts` (+ `status.test.ts`, `fingerprint.test.ts`, `store.test.ts`) | `isPristine` counts the hymnal (owner answer 1) | T3 |
| `frontend/src/lib/api/types.ts` | hymn type names | T4 |
| `frontend/src/test/fixtures/index.ts` | hymn builders (T4); lists, routes and bodies (T6) | T4, T6 |
| `frontend/src/lib/dates.ts` (+ `dates.test.ts`) | `formatAbbrevDate` | T5 |
| `frontend/src/lib/queries/keys.ts` (+ `keys.test.ts`), `frontend/src/lib/api/timeouts.ts` | `hymnMatches`; suggestions 90 s | T6 |
| `frontend/src/lib/draft/steps.ts`, `status.ts` (`stillNeeded`) (+ `status.test.ts`), `frontend/src/components/builder/summary-panel.tsx`, `step-placeholder.tsx` (comment), `builder-shell.test.tsx`, `(church)/builder/hymns/page.tsx` | `"hymns"` ships; the rows, the summary block and the page | T12 |
| `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` | "(3b plan)" notes, one F amendment row | T13 |
| `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | "## Slice 3"; the heading pin | T13 |
| `docs/ops-runbook.md` | "Slice 3b record" (the records PR after the merge) | T15 |

**Untouched:** `backend/requirements*.txt`, migrations, `frontend/package.json` and `package-lock.json` (no new dependency: `@base-ui/react` already has the switch), `frontend/src/lib/api/openapi.json` and `schema.d.ts`, `frontend/src/lib/draft/{schema,migrate,mapping,fingerprint,prune,date-effects,readings,store,context}.ts`, every other backend file (unless Task 1b), Streamlit files, CI workflows.

**Task order and checkpoints:** T1 (owner queries, in parallel) and T2 → T3 → … → T13 → T14 → T15. Each of T2-T13 ends in one commit, a review and a backup push. The review checkpoints are stops for the controller, not merges: everything ships in the one 3b PR.

---

### Task 1: Why no recent use shows (OWNER queries, agent check, decision point) (owner answer 2; S Backend 3.4; Slice 3a record "Follow-ups")

The 3a Console check asked `GET /hymns?hymnal=GG2013&recent_for_date=2026-10-04` and found no hymn with `recent_use_on` although `hymn_usage` holds 90 rows (all `YYYY-MM-DD`), and the owner has prepared services in the old app within the last 90 days. The new code reads correctly on inspection: `hymn_usage.usage_near` keeps rows of the active church whose date is within D-84 to D+84 days, D itself excluded, keyed by `usage_key(title)` (`backend/hymn_usage.py`; tests in `test_hymn_usage_window.py`). The frozen app (`origin/streamlit-frozen`, `app.py` lines 1018 and 1041) writes `hymn_usage` only on **Prepare bulletin copy** or **Prepare pastor's copy**, never on Save, with the church from its own session. So the suspects are: the rows belong to another church id than the new app's; the old app writes to another database; or no Word copy was prepared in the window. This task finds out with four read-only queries, run one at a time by the owner in the Supabase project the new app uses, and one Console look at the new app's church. It changes no file. **Nothing else waits for it:** T2-T13 are built meanwhile, and the decision in Step 7 either adds a fix task (Task 1b) to this branch or records a data question for the owner.

Church ids appear in this task only as their first 8 characters, and only in chat and the results file; nothing with a church id, an email or a token is committed or put in the runbook.

**Files:**
- Create (not committed): `<scratch>/slice3b-t1-results.md` (`<scratch>` is the session's scratchpad directory; write it out literally).
- No repository file changes, unless Step 7 outcome A adds Task 1b.

**Interfaces:**
- Consumes: `hymn_usage.usage_near`, `usecases.hymns.list_hymns_page` (3a); the production database (read only).
- Produces: the recent-use finding and its outcome (A-D below), written into the results file and, at T15, into "Slice 3b record" (without ids). Later users: T15 Step 11; Task 1b if outcome A.

- [ ] **Step 1 (agent): Check the reader once more, locally**

```bash
.venv/bin/python -m pytest -q backend/tests/test_hymn_usage_window.py 2>&1 | tail -1
grep -n "def usage_near" -A 40 backend/hymn_usage.py | grep "church_id ==\|date_iso <\|day == service_date"
git fetch -q origin streamlit-frozen && git show origin/streamlit-frozen:app.py | grep -n "record_usage" | head -3
```

**Expected:** `8 passed, 1 skipped in <t>s`; three lines of `usage_near`: `152-` (the church filter and the lower string bound), `154-` (the upper bound) and `173-` (the exact window, D itself excluded); three lines of the frozen app: `35:` (the import) and `1018:` and `1041:` (the two Prepare buttons). Start the results file with today's date and "Reader checked: OK".

- [ ] **Step 2 (OWNER): Query 1 of 4, recent use per church**

Send the owner exactly this and wait for the result:

> To find out why the new app shows no recently used hymns, could you run four short read-only queries, one at a time? They change nothing and show no names of people or emails.
> 1. Open https://supabase.com/dashboard, choose the project `worship-staging`, then **SQL Editor** on the left.
> 2. Click **New query**, paste this, and click **Run**:
>
> ```sql
> select left(u.church_id::text, 8) as church, c.name, count(*) as uses,
>        min(u.date_iso) as first_date, max(u.date_iso) as last_date,
>        max(u.recorded_at) as last_recorded
> from hymn_usage u left join churches c on c.id = u.church_id
> group by 1, 2 order by uses desc;
> ```
>
> 3. Please paste the rows here (or send a screenshot of them).

Write the rows into the results file. Then send Step 3.

- [ ] **Step 3 (OWNER): Query 2 of 4, the churches**

> Thanks. Next query, same way (New query, paste, Run), and paste the rows:
>
> ```sql
> select left(id::text, 8) as church, name, created_at, deleted_at
> from churches order by created_at;
> ```

Write the rows into the results file.

- [ ] **Step 4 (OWNER): Query 3 of 4, the ten most recent uses**

> Next one:
>
> ```sql
> select u.date_iso, u.hymn_number, u.hymn_title, left(u.church_id::text, 8) as church, u.recorded_at
> from hymn_usage u
> order by u.date_iso desc nulls last, u.recorded_at desc
> limit 10;
> ```

Write the rows into the results file (hymn titles and numbers are public hymn data).

- [ ] **Step 5 (OWNER): Query 4 of 4, the most recent saved services**

> Last query. It shows whether recent work in the old app reached this database at all:
>
> ```sql
> select s.service_date_iso, left(s.church_id::text, 8) as church, s.saved_at,
>        jsonb_array_length(coalesce(s.hymns::jsonb, '[]'::jsonb)) as hymns
> from services s
> order by s.saved_at desc
> limit 10;
> ```

Write the rows into the results file. If the query fails with `cannot get array length of a scalar` or `of an object`, ask the owner to run it again with the `jsonb_array_length(...) as hymns` part and the comma before it removed.

- [ ] **Step 6 (OWNER): The new app's church, from the Console**

> Thank you. One more look, in the new app this time. On https://worship-service-builder.vercel.app, signed in, open DevTools (⌥⌘I) → Console, paste this and press Return (type `allow pasting` first if Chrome asks). It reads your sign-in from this site, calls only the app's API, prints no token and changes nothing. Please paste the lines it prints.

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
  for (const c of me.churches) console.log(`member of ${c.id.slice(0, 8)} ${c.name} (${c.role})`);
  const churchId = localStorage.getItem("activeChurchId") || (me.churches[0] || {}).id;
  const headers = { Authorization: "Bearer " + token, "X-Church-Id": churchId };
  const church = await (await fetch(API + "/church", { headers })).json();
  console.log(`active church ${church.id.slice(0, 8)} ${church.name} effective_hymnal=${church.effective_hymnal}`);
  for (const day of ["2026-10-04", "2026-08-02", "2026-06-07"]) {
    const r = await fetch(`${API}/hymns?hymnal=${encodeURIComponent(church.effective_hymnal)}&limit=2000&recent_for_date=${day}`, { headers });
    const b = await r.json();
    const recent = (b.items || []).filter((h) => h.recent_use_on);
    console.log(`recent around ${day}: ${r.status} ${recent.length} ${JSON.stringify(recent.slice(0, 3).map((h) => [h.number, h.title, h.recent_use_on]))}`);
  }
})();
```

Write the lines into the results file.

- [ ] **Step 7 (agent): Compare, decide, and report**

Compare the active church's 8-character prefix (Step 6) with the `church` column of Steps 2-5, and the usage dates with the windows the Console asked about (October 4, 2026 covers July 12 to December 27, 2026; August 2 covers May 10 to October 25; June 7 covers March 15 to August 30). Then pick exactly one outcome and write it, with its evidence, into the results file:

| Outcome | What the rows show | What happens |
|---|---|---|
| **A. The new code is wrong** | The active church has usage rows inside a window (Step 2 or 4), but that window's Console line shows 0 recent hymns | The controller adds **Task 1b** to this plan (a "Plan: slice 3b recent-use fix (Task 1b)" commit): first a failing test in `backend/tests/test_hymn_usage_window.py` or `test_api_hymns.py` built from the row shapes found (titles, numbers, dates, anything unusual such as spaces or a hymnal-specific title), then the smallest fix in `backend/hymn_usage.py` or `backend/usecases/hymns.py`, with its count added to the table, reviewed and backed up like any task. Tell the owner in one line what was wrong. |
| **B. Another church** | The recent rows (Step 4) belong to a church prefix other than the active one (for example a second church of the same name, or one with `deleted_at` set) | No code change. Record it; the controller asks the owner (below). |
| **C. No Word copies prepared** | No usage rows after some date, although Step 5 shows services saved recently for the active church | No code change: the old app records use only when a Word copy is prepared. Record it; the controller asks the owner. |
| **D. Another database** | Neither usage (Step 4) nor saved services (Step 5) show the owner's recent work | No code change. Ask the owner to compare, without sending either value, the host part of `DATABASE_URL` in the liturgy-frozen app's Secrets (share.streamlit.io → the app → Settings → Secrets) and in Railway's Variables: does each contain `tbecmwtitsoxzkrvxxxu`? Record the answer; the controller asks the owner. |

For B, C and D, send the owner this, filled in, and wait (the build carries on):

> What I found about recent hymn use: <one or two plain sentences, for example "the old app last recorded hymns on July 5, and only when a Word copy is prepared, so nothing after that counts as used">. The new app reads the history correctly; no code change is needed for it. Options: (1) leave it, since slice 5a will record hymns every time a service is saved in the new app; (2) <an option that fits, for example "move the rows filed under the old church to the current one", which would be a small separate data task with its own review>. Which would you like?

Record the owner's answer in the results file. T15 carries the finding (without ids) into "Slice 3b record".

Counts after this task: unchanged (frontend 356 in 55 files; backend 1106 passed, 11 skipped), unless Task 1b is added.

### Task 2: The church season in the AI prompt (owner answer 3; S Backend 3.6 step 7, §6 "Tenancy"; clarification 21)

The live suggestion for "Nineteenth Sunday after Pentecost" (Matthew 21:33-46) put "All Glory, Laud, and Honor" and "Hosanna, loud hosanna" in the response slot. The prompt now names the church season, computed on the server from the service date with the lectionary module's own calendar (`easter_date`, `advent_sunday`, already tested), and adds one guidance line. `vanderbilt_lectionary.church_season(d)` returns exactly one of nine labels for every date: "Advent", "Christmas Eve", "Christmas", "Epiphany of the Lord", "Season after the Epiphany", "Lent", "Holy Week", "Easter", "Day of Pentecost" or "Season after Pentecost". `hymn_suggest.build_prompt` gains `season: str = ""` (keyword, default kept so every existing caller and test is unchanged); the user message gets `CHURCH SEASON: {season}` right after `OCCASION`, one line clipped to 60 characters ("Not specified" when empty), and `SEASON: {SEASON_GUIDANCE}` after the PREFERENCES line. The label comes from the server, never from the request, and goes through the same `_clip` as every other field; the 24 000-character budget is unchanged (candidates are trimmed first, as before). `usecases.hymns.suggest_hymns` passes `season=church_season(req.service_date)`. No API change, so `openapi.json` and `schema.d.ts` stay as they are.

**Files:**
- Modify: `backend/vanderbilt_lectionary.py` (`church_season`), `backend/hymn_suggest.py` (`SEASON_GUIDANCE`, `_render`, `build_prompt`), `backend/usecases/hymns.py` (one import, one argument)
- Test: `backend/tests/test_lectionary_domain.py` (+2), `backend/tests/test_hymn_suggest.py` (+1), `backend/tests/test_api_hymn_suggestions.py` (+1)

**Interfaces:**
- Consumes: `easter_date`, `advent_sunday` (slice 2a); `hymn_suggest._render`, `_clip`, `build_prompt` (3a).
- Produces:
  - `church_season(d: date) -> str` in `vanderbilt_lectionary.py` (pure).
  - `hymn_suggest.SEASON_GUIDANCE: str`; `build_prompt(candidates, *, occasion, scriptures, nt_ref, nt_text, rubric, season: str = "")`.

Counts after this task: backend **1110 passed, 11 skipped**; frontend unchanged (356 in 55 files).

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -3
grep -c "def church_season" backend/vanderbilt_lectionary.py
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected,** in order: nothing, or only `?? .claude/`; the plan's commits above `b47abba Merge pull request #27 from bbrown62450/claude/slice-2-plan-4q33le`; `0` (grep exits 1); `1106 passed, 11 skipped in <t>s`; ` Test Files  55 passed (55)` and `      Tests  356 passed (356)`. If `node_modules` is missing, run `(cd frontend && npm ci)` first. Any other baseline: stop and ask.

- [ ] **Step 2 (agent): Write the failing tests**

Run this edit script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("backend/tests/test_lectionary_domain.py", [
    ("    advent_sunday,\n    clean_cell,\n",
     "    advent_sunday,\n    church_season,\n    clean_cell,\n"),
    ("def test_lectio_set_name_precedence():",
     '''# --- slice 3b: the church season for the AI hymn prompt (owner answer 3, 2026-09-29) ---


def test_church_season_table():
    seasons = {
        date(2026, 10, 4): "Season after Pentecost",   # Nineteenth Sunday after Pentecost
        date(2026, 11, 22): "Season after Pentecost",  # Christ the King
        date(2026, 11, 28): "Season after Pentecost",  # the Saturday before Advent 1
        date(2026, 11, 29): "Advent",
        date(2026, 12, 23): "Advent",
        date(2026, 12, 24): "Christmas Eve",
        date(2026, 12, 25): "Christmas",
        date(2027, 1, 5): "Christmas",
        date(2027, 1, 6): "Epiphany of the Lord",
        date(2027, 1, 10): "Season after the Epiphany",  # Baptism of the Lord
        date(2027, 2, 7): "Season after the Epiphany",   # Transfiguration Sunday
        date(2027, 2, 10): "Lent",                       # Ash Wednesday
        date(2027, 3, 20): "Lent",
        date(2027, 3, 21): "Holy Week",                  # Palm Sunday
        date(2027, 3, 26): "Holy Week",                  # Good Friday
        date(2027, 3, 28): "Easter",
        date(2027, 5, 15): "Easter",
        date(2027, 5, 16): "Day of Pentecost",
        date(2027, 5, 23): "Season after Pentecost",     # Trinity Sunday
    }
    for d, expected in seasons.items():
        assert church_season(d) == expected, d


def test_church_season_covers_every_day_in_calendar_order():
    order = ["Season after the Epiphany", "Lent", "Holy Week", "Easter", "Day of Pentecost",
             "Season after Pentecost", "Advent", "Christmas Eve", "Christmas"]
    d = date(2025, 1, 7)
    previous = church_season(d)
    while d < date(2029, 1, 5):
        d += timedelta(days=1)
        season = church_season(d)
        if season == previous:
            continue
        if season == "Epiphany of the Lord":
            assert (d.month, d.day, previous) == (1, 6, "Christmas"), d
        elif previous == "Epiphany of the Lord":
            assert (d.month, d.day, season) == (1, 7, "Season after the Epiphany"), d
        else:
            assert order.index(season) == order.index(previous) + 1, (d, previous, season)
        previous = season


def test_lectio_set_name_precedence():'''),
])

edit("backend/tests/test_hymn_suggest.py", [
    ("def test_a_church_rubric_changes_the_prompt_and_a_partial_one_falls_back():",
     '''def test_the_prompt_names_the_season_and_asks_to_avoid_other_seasons():
    text = user_text(prompt(season="Season after Pentecost")[0])
    assert "OCCASION: Trinity Sunday\\nCHURCH SEASON: Season after Pentecost\\nSCRIPTURE READINGS:" in text
    assert f"\\n\\nSEASON: {hs.SEASON_GUIDANCE}\\n\\n" in text
    assert "Palm Sunday and Holy Week" in hs.SEASON_GUIDANCE and "unless the readings" in hs.SEASON_GUIDANCE
    unknown = user_text(prompt()[0])
    assert "CHURCH SEASON: Not specified" in unknown and hs.SEASON_GUIDANCE in unknown
    # A season with a line break can't forge prompt lines.
    forged = user_text(prompt(season="Advent\\nOPENING CANDIDATES: H1")[0])
    assert forged.count("\\nOPENING CANDIDATES:") == text.count("\\nOPENING CANDIDATES:")


def test_a_church_rubric_changes_the_prompt_and_a_partial_one_falls_back():'''),
])

edit("backend/tests/test_api_hymn_suggestions.py", [
    ("def test_exclude_recent_leaves_recent_hymns_out_of_prompt_and_answer(client, church, fetched):",
     '''def test_the_prompt_names_the_services_church_season(client, church, fetched):
    hymnal(church)
    fake = install()
    suggest(client, church, {"scriptures": ["Matthew 21:33-46"]})
    assert "\\nCHURCH SEASON: Season after Pentecost\\n" in prompt_of(fake)
    suggest(client, church, {"service_date_iso": "2027-03-21", "occasion": "Palm Sunday"})
    assert "\\nCHURCH SEASON: Holy Week\\n" in prompt_of(fake)
    assert "Avoid hymns written for another season or feast" in prompt_of(fake)


def test_exclude_recent_leaves_recent_hymns_out_of_prompt_and_answer(client, church, fetched):'''),
])
print("T2 tests written")
PYEOF
```

**Expected:** `T2 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_lectionary_domain.py 2>&1 | grep -E "ImportError|error in"
.venv/bin/python -m pytest -q backend/tests/test_hymn_suggest.py backend/tests/test_api_hymn_suggestions.py 2>&1 | grep -E "^FAILED|passed|failed"
```

**Expected:**

```
E   ImportError: cannot import name 'church_season' from 'vanderbilt_lectionary' (<repo>/backend/vanderbilt_lectionary.py)
1 error in <t>s
FAILED backend/tests/test_hymn_suggest.py::test_the_prompt_names_the_season_and_asks_to_avoid_other_seasons
FAILED backend/tests/test_api_hymn_suggestions.py::test_the_prompt_names_the_services_church_season
2 failed, 45 passed in <t>s
```

- [ ] **Step 4 (agent): Write `church_season` and the prompt lines**

Run this edit script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("backend/vanderbilt_lectionary.py", [
    ('''    return _EASTER_FEASTS.get((d - easter_date(d.year)).days)
''', '''    return _EASTER_FEASTS.get((d - easter_date(d.year)).days)


def church_season(d: date) -> str:
    """The church season of `d`, for the AI hymn prompt (slice 3b plan, owner answer 3).

    Date arithmetic only, from the same calendar as the occasion names: "Advent" from
    Advent 1 to December 23; "Christmas Eve"; "Christmas" from December 25 to January 5;
    "Epiphany of the Lord" (January 6); "Season after the Epiphany" to the day before
    Ash Wednesday (Transfiguration Sunday included); "Lent" to the Saturday before Palm
    Sunday; "Holy Week" from Palm Sunday to Holy Saturday; "Easter" from Easter Day to
    the day before Pentecost; "Day of Pentecost"; then "Season after Pentecost" to the
    day before Advent 1 (Christ the King included). Every date has exactly one.
    """
    if (d.month == 12 and d.day >= 25) or (d.month == 1 and d.day <= 5):
        return "Christmas"
    if d.month == 12 and d.day == 24:
        return "Christmas Eve"
    advent1 = advent_sunday(d.year)
    if d >= advent1:
        return "Advent"
    if d.month == 1 and d.day == 6:
        return "Epiphany of the Lord"
    easter = easter_date(d.year)
    pentecost = easter + timedelta(days=49)
    if d < easter - timedelta(days=46):
        return "Season after the Epiphany"
    if d < easter - timedelta(days=7):
        return "Lent"
    if d < easter:
        return "Holy Week"
    if d < pentecost:
        return "Easter"
    if d == pentecost:
        return "Day of Pentecost"
    return "Season after Pentecost"
'''),
])

edit("backend/hymn_suggest.py", [
    ('''SYSTEM_MESSAGE = "You help a church choose hymns for a worship service. Reply with JSON only."
''', '''SYSTEM_MESSAGE = "You help a church choose hymns for a worship service. Reply with JSON only."
# Owner answer 3 (2026-09-29, slice 3b plan): a hymn for another season or feast (for
# example Palm Sunday hymns in the Season after Pentecost) only when the readings call for it.
SEASON_GUIDANCE = ("Choose hymns that suit this church season and occasion. Avoid hymns written for "
                   "another season or feast (Advent, Christmas, Palm Sunday and Holy Week, or Easter "
                   "hymns outside their season) unless the readings or the occasion clearly call for them.")
'''),
    ('''def _render(lists: Mapping[str, list], *, occasion: str, scriptures: Sequence[str],
            nt_ref: Optional[str], nt_text: Optional[str],
            rubric: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:''',
     '''def _render(lists: Mapping[str, list], *, occasion: str, scriptures: Sequence[str],
            nt_ref: Optional[str], nt_text: Optional[str],
            rubric: Mapping[str, Any], season: str = "") -> tuple[list[dict], dict[str, Any]]:'''),
    ('''    user = (f"OCCASION: {_clip(occasion, 300) or 'Not specified'}\\n"
            f"SCRIPTURE READINGS:\\n{readings}\\n"''',
     '''    user = (f"OCCASION: {_clip(occasion, 300) or 'Not specified'}\\n"
            f"CHURCH SEASON: {_clip(season, 60) or 'Not specified'}\\n"
            f"SCRIPTURE READINGS:\\n{readings}\\n"'''),
    ('''            f"PREFERENCES: {_preferences(rubric)}\\n\\n"''',
     '''            f"PREFERENCES: {_preferences(rubric)}\\n\\n"
            f"SEASON: {SEASON_GUIDANCE}\\n\\n"'''),
    ('''def build_prompt(candidates: Candidates, *, occasion: str, scriptures: Sequence[str],
                 nt_ref: Optional[str], nt_text: Optional[str],
                 rubric: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    """(messages, {"H1": record, ...}), at most MAX_PROMPT_CHARS in all. While''',
     '''def build_prompt(candidates: Candidates, *, occasion: str, scriptures: Sequence[str],
                 nt_ref: Optional[str], nt_text: Optional[str],
                 rubric: Mapping[str, Any], season: str = "") -> tuple[list[dict], dict[str, Any]]:
    """(messages, {"H1": record, ...}), at most MAX_PROMPT_CHARS in all. `season` is
    the server's `church_season` label (one clipped line; "Not specified" when empty),
    followed in the prompt by SEASON_GUIDANCE (owner answer 3, slice 3b plan). While'''),
    ('''        messages, token_map = _render(lists, occasion=occasion, scriptures=scriptures,
                                      nt_ref=nt_ref, nt_text=nt_text, rubric=rubric)''',
     '''        messages, token_map = _render(lists, occasion=occasion, scriptures=scriptures,
                                      nt_ref=nt_ref, nt_text=nt_text, rubric=rubric, season=season)'''),
])

edit("backend/usecases/hymns.py", [
    ('''import scripture_fetcher
from service_rubric import merge_rubric
from usecases import passages
''', '''import scripture_fetcher
from service_rubric import merge_rubric
from usecases import passages
from vanderbilt_lectionary import church_season
'''),
    ('''            candidates, occasion=req.occasion, scriptures=req.scriptures, nt_ref=nt_ref,
            nt_text=nt_text, rubric=rubric)''',
     '''            candidates, occasion=req.occasion, scriptures=req.scriptures, nt_ref=nt_ref,
            nt_text=nt_text, rubric=rubric, season=church_season(req.service_date))'''),
])
print("T2 code written")
PYEOF
```

**Expected:** `T2 code written`.

- [ ] **Step 5 (agent): Run the tests and the suite**

```bash
for f in test_lectionary_domain test_hymn_suggest test_api_hymn_suggestions; do .venv/bin/python -m pytest -q backend/tests/$f.py 2>&1 | tail -1; done
.venv/bin/python -m pytest -q | tail -1
git status --short
```

**Expected:** `30 passed in <t>s`, `25 passed in <t>s`, `22 passed in <t>s`; `1110 passed, 11 skipped in <t>s`; ` M` for the six files named in **Files:** (and `?? .claude/` if present).

- [ ] **Step 6 (agent): Commit**

```bash
git add backend/vanderbilt_lectionary.py backend/hymn_suggest.py backend/usecases/hymns.py backend/tests/test_lectionary_domain.py backend/tests/test_hymn_suggest.py backend/tests/test_api_hymn_suggestions.py
git commit -m "Hymns: the AI prompt names the church season and avoids other seasons' hymns (owner answer 3)" -m "church_season(d) names one of nine seasons from the service date with
the lectionary calendar. build_prompt gains season= (default \"\"), adds
CHURCH SEASON after OCCASION and a SEASON guidance line after
PREFERENCES: avoid Advent, Christmas, Palm Sunday and Holy Week or Easter
hymns outside their season unless the readings or occasion call for them.
The label is server-made and clipped like every field; the 24 000-character
budget is unchanged. No API change. Backend 1106 -> 1110 passed.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 6 files changed. The controller reviews it and backs the branch up.

**Review checkpoint (T2):** every date maps to one label and the labels follow the calendar order (the coverage test walks 2025-2028); the season line is one clipped line; the guidance sits after PREFERENCES and before HYMNS; `build_prompt` still trims to 24 000 characters; the usecase passes the service date's season; nothing reads the season from the request.

### Task 3: A chosen hymnal is unsaved work; the Exclude switch and the other ideas are not (owner answer 1; S "Draft usage"; F §4.6 "Unsaved changes"; clarification 2)

Owner answer 1 makes S's "Draft usage" exact. What "New service" asks about (`isDirty`, which is `!isPristine` until 5a saves drafts, then a fingerprint of `draftToServicePayload`) and what holds a passed default date back on load (`rollForward`, through `isPristine`) must count a hymn slot and the hymnal, and never `exclude_recent` or `alternatives`. Checked on `b47abba`: `isPristine` already counts the slots but not `hymns.hymnal`; the payload already holds `hymns` (the three slots) and `hymnal`, but neither the switch nor the ideas. So the only code change is one line in `isPristine`. The three tests pin all four fields in all three places (the fingerprint test passes before the change: it pins what 2b already built).

**Files:**
- Modify: `frontend/src/lib/draft/status.ts` (`isPristine` and its comment)
- Test: `frontend/src/lib/draft/status.test.ts` (+1), `frontend/src/lib/draft/fingerprint.test.ts` (+1), `frontend/src/lib/draft/store.test.ts` (+1)

**Interfaces:**
- Consumes: `isPristine`, `isDirty`, `fingerprint`, `draftToServicePayload`, `DraftStore` roll-forward (2b, 2c).
- Produces: `isPristine(draft)` is also false when `draft.hymns.hymnal !== null`. Later users: T4's `setHymnal` (which stores `null` for the church's effective hymnal, clarification 2), T9 (the Select), and every "New service" and roll-forward.

Counts after this task: frontend **359 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "draft.hymns.hymnal === null" frontend/src/lib/draft/status.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  55 passed (55)`, `      Tests  356 passed (356)`.

- [ ] **Step 2 (agent): Write the failing tests**

Run this edit script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/lib/draft/status.test.ts", [
    ('''describe("stillNeeded (S Review \\"Still needed\\")", () => {''',
     '''describe("isPristine and the hymns step (owner answer 1, 2026-09-29)", () => {
  it("counts a hymn slot and a chosen hymnal, never the Exclude switch or the other ideas", () => {
    const hymns = (patch: Partial<DraftV1["hymns"]>) => testDraft((d) => ({ ...d, hymns: { ...d.hymns, ...patch } }));
    expect(isPristine(hymns({ hymnal: "PH1990" }))).toBe(false);
    expect(isPristine(hymns({ slots: { opening: null, response: HYMN, closing: null } }))).toBe(false);
    const ideas = { for_date_iso: "2026-10-04", by_slot: { opening: [HYMN], response: [], closing: [HYMN] } };
    expect(isPristine(hymns({ exclude_recent: false }))).toBe(true);
    expect(isPristine(hymns({ alternatives: ideas }))).toBe(true);
    expect(isPristine(hymns({ exclude_recent: false, alternatives: ideas }))).toBe(true);
  });
});

describe("stillNeeded (S Review \\"Still needed\\")", () => {'''),
])

edit("frontend/src/lib/draft/fingerprint.test.ts", [
    ('''    expect(isDirty(saved)).toBe(false);
    expect(isDirty(editOccasion(saved, "Harvest Home"))).toBe(true);
  });''', '''    expect(isDirty(saved)).toBe(false);
    expect(isDirty(editOccasion(saved, "Harvest Home"))).toBe(true);
  });

  it("after a save, a slot or hymnal change is unsaved; the Exclude switch and other ideas are not (owner answer 1)", () => {
    const pick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };
    const base = testDraft();
    const saved: DraftV1 = { ...base, saved_fingerprint: fingerprint(draftToServicePayload(base)) };
    const hymns = (patch: Partial<DraftV1["hymns"]>): DraftV1 => ({ ...saved, hymns: { ...saved.hymns, ...patch } });
    expect(isDirty(hymns({ slots: { ...saved.hymns.slots, closing: pick } }))).toBe(true);
    expect(isDirty(hymns({ hymnal: "PH1990" }))).toBe(true);
    expect(isDirty(hymns({ exclude_recent: false }))).toBe(false);
    const ideas = { for_date_iso: "2026-10-04", by_slot: { opening: [pick], response: [], closing: [] } };
    expect(isDirty(hymns({ alternatives: ideas }))).toBe(false);
  });'''),
])

edit("frontend/src/lib/draft/store.test.ts", [
    ('''describe("DraftStore changes (S store.ts)", () => {''',
     '''describe("DraftStore roll-forward and the hymns step (owner answer 1, 2026-09-29)", () => {
  it("keeps a passed default date when a hymnal was chosen, and rolls one with only the switch or ideas changed", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const hymns = (patch: Partial<DraftV1["hymns"]>) => testDraft((d) => ({ ...d, hymns: { ...d.hymns, ...patch } }));
    const load = (d: DraftV1) =>
      makeStore(memoryStorage({ [KEY]: JSON.stringify(d) }).storage, tenDaysLater.now).store.getSnapshot().draft;
    expect(load(hymns({ hymnal: "PH1990" })).readings.date_iso).toBe("2026-10-04");
    const pick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };
    const ideas = { for_date_iso: "2026-10-04", by_slot: { opening: [pick], response: [], closing: [] } };
    const rolled = load(hymns({ exclude_recent: false, alternatives: ideas }));
    expect(rolled.readings.date_iso).toBe("2026-10-11");
    expect(rolled.hymns).toMatchObject({ exclude_recent: false, alternatives: ideas }); // kept, and hidden by date
  });
});

describe("DraftStore changes (S store.ts)", () => {'''),
])
print("T3 tests written")
PYEOF
```

**Expected:** `T3 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "^ (FAIL|×)|TypeError|AssertionError|Tests ")
```

**Expected:**

```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/draft/status.test.ts > isPristine and the hymns step (owner answer 1, 2026-09-29) > counts a hymn slot and a chosen hymnal, never the Exclude switch or the other ideas
AssertionError: expected true to be false // Object.is equality
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore roll-forward and the hymns step (owner answer 1, 2026-09-29) > keeps a passed default date when a hymnal was chosen, and rolls one with only the switch or ideas changed
AssertionError: expected '2026-10-11' to be '2026-10-04' // Object.is equality
      Tests  2 failed | 23 passed (25)
```

(The new fingerprint test passes already; it pins the payload 2b built.)

- [ ] **Step 4 (agent): Count the hymnal in `isPristine`**

Run this edit script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/lib/draft/status.ts", [
    (''' * translation, so they look past it with `withoutTranslation` (owner answer
 * A, 2026-09-29).
 */''', ''' * translation, so they look past it with `withoutTranslation` (owner answer
 * A, 2026-09-29). A hymn in any slot and a chosen hymnal count too; the
 * Exclude switch and the AI's other ideas never do (owner answer 1,
 * 2026-09-29, slice 3b; the same fields the fingerprint payload holds).
 */'''),
    ('''    SLOTS.every((slot) => draft.hymns.slots[slot] === null) &&''',
     '''    SLOTS.every((slot) => draft.hymns.slots[slot] === null) &&
    draft.hymns.hymnal === null &&'''),
])
print("T3 code written")
PYEOF
```

**Expected:** `T3 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  3 passed (3)`, `      Tests  25 passed (25)`; the suite ` Test Files  55 passed (55)`, `      Tests  359 passed (359)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for the four files named in **Files:**.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/draft/fingerprint.test.ts frontend/src/lib/draft/store.test.ts
git commit -m "Draft: a chosen hymnal is unsaved work; the Exclude switch and other ideas are not (owner answer 1)" -m "isPristine is also false when hymns.hymnal is set, so New service asks
first and the roll-forward keeps the date of a draft with a chosen hymnal,
as it already did for a hymn in a slot. exclude_recent and alternatives
count nowhere: not in isPristine, not in the fingerprint payload, not in
the roll-forward (tests pin all four fields). Frontend 356 -> 359 tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 4 files changed.

**Review checkpoint (T1-T3, batch 1):** T1's queries are read only, one per step, with no email or full id; T1's decision table leaves the build unblocked; T2 as in its checkpoint; T3 changes one condition, the switch and the ideas count nowhere, and the counts match.

### Task 4: The step's draft transitions, the suggestion helpers and the selected hymnal (S "Pure-function contracts", Toolbar "selected hymnal", "Live data"; F D16; owner answer 1; clarifications 2, 9)

The pure core of the step, before any screen: what a pick stores (`pickFromHymn`), the four draft recipes the screen calls through `update` (`setSlot`, `clearSlot`, `setHymnal`, `setExcludeRecent`), how a pick meets its hymnal's loaded list (`reconcilePick`), how an AI answer lands (`applySuggestions`, empty slots only, F D16), a tap on an idea (`swapAlternative`), the "Also chosen as…" check (`duplicateSlots`) and the selected hymnal (`selectHymnal`). `setHymnal` stores `null` for the church's effective hymnal, like 2c's `setTranslation`, so switching away and back is not unsaved work (owner answer 1; clarification 2). `lib/api/types.ts` gains app-facing names for the 3a types, and the test fixtures gain `hymnId`, `hymn`, `suggested` and `hymnals`.

**Files:**
- Create: `frontend/src/lib/hymns/picks.ts`, `frontend/src/lib/hymns/hymnal.ts`
- Modify: `frontend/src/lib/api/types.ts` (hymn type names), `frontend/src/test/fixtures/index.ts` (hymn builders)
- Test: `frontend/src/lib/hymns/picks.test.ts` (new, 7; `selectHymnal`'s cases are here, as S's Testing table puts them)

**Interfaces:**
- Consumes: `HymnalListOut`, `HymnOut`, `Page_HymnOut_`, `ScriptureMatchIn`, `ScriptureMatchesOut`, `HymnMatchOut`, `HymnSuggestionIn`, `HymnSuggestionsOut`, `SuggestedHymnOut` (`schema.d.ts`, 3a); `DraftV1`, `HymnPick`, `Slot`, `SLOTS` (`lib/draft/schema.ts`).
- Produces:
  - `lib/api/types.ts`: `Hymnals`, `HymnalSummary`, `Hymn`, `HymnPage`, `ScriptureMatchBody`, `ScriptureMatches`, `HymnMatch`, `HymnSuggestionBody`, `HymnSuggestions`, `SuggestedHymn`.
  - `picks.ts`: `pickFromHymn(h) -> HymnPick`; `setSlot(d, slot, pick | null)`, `clearSlot(d, slot)`, `setHymnal(d, code, effective)`, `setExcludeRecent(d, on)` (each `DraftV1 -> DraftV1`, the same object when nothing changes); `type Reconciled = {status: "ok"; live: Hymn} | {status: "loading"} | {status: "missing"}`; `reconcilePick(pick, lists: ReadonlyMap<string, readonly Hymn[] | undefined>, fallbackHymnal: string | null)`; `applySuggestions(hymns, resp, dateIso) -> hymns`; `swapAlternative(hymns, slot, hymnId) -> hymns`; `duplicateSlots(slots) -> Record<Slot, Slot[]>`. Later users: T8-T11.
  - `hymnal.ts`: `type SelectedHymnal = {code: string | null; stale: boolean}`; `selectHymnal(stored, hymnals)`. Later users: T8, T9.
  - fixtures: `hymnId(n)` (a valid uuid ending in `n`), `hymn(overrides)` (#403 "Come, Thou Almighty King", GG2013), `suggested(overrides)` (`source: "ai"`), `hymnals(overrides)` (GG2013 only, 853 hymns, 795 with references). Later users: T5-T12.

Counts after this task: frontend **366 passed in 56 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/lib/hymns 2>&1 | head -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/lib/hymns': No such file or directory`; ` Test Files  55 passed (55)`, `      Tests  359 passed (359)`.

- [ ] **Step 2 (agent): Write the failing tests and the fixtures**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/test/fixtures/index.ts", [
    ('import type { ChurchProfile, InviteAccepted, InvitePreview, Lectionary, Translations } from "@/lib/api/types";',
     'import type {\n  ChurchProfile,\n  Hymn,\n  Hymnals,\n  InviteAccepted,\n  InvitePreview,\n  Lectionary,\n'
     '  SuggestedHymn,\n  Translations,\n} from "@/lib/api/types";'),
])
with open("frontend/src/test/fixtures/index.ts", "a", encoding="utf-8") as f:
    f.write('''
// --- slice 3b: hymns and hymnals ------------------------------------------------

/** A readable, valid hymn id: `hymnId(403)` is "00000000-0000-4000-8000-000000000403". */
export function hymnId(n: number): string {
  return `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
}

/** One `HymnOut` (slice 3a): #403 "Come, Thou Almighty King" in GG2013 unless overridden; the id follows the number. */
export function hymn(overrides: Partial<Hymn> = {}): Hymn {
  const number = overrides.number === undefined ? 403 : overrides.number;
  return {
    id: hymnId(number ?? 0),
    hymnal: "GG2013",
    title: "Come, Thou Almighty King",
    number,
    link: `https://hymnary.org/hymn/GG2013/${number ?? ""}`,
    scripture_refs: null,
    themes: [],
    recent_use_on: null,
    text_year: null,
    hymnal_count: null,
    newer_than_preferred: false,
    ...overrides,
  };
}

/** One `SuggestedHymnOut`: `hymn(overrides)` with `source` "ai" unless overridden. */
export function suggested(overrides: Partial<SuggestedHymn> = {}): SuggestedHymn {
  return { source: "ai", ...hymn(overrides), ...overrides };
}

/** `GET /hymnals` for Grace: GG2013 only (production, slice 3a record), no stored default. */
export function hymnals(overrides: Partial<Hymnals> = {}): Hymnals {
  return {
    items: [{ code: "GG2013", hymn_count: 853, scripture_ref_count: 795 }],
    default_hymnal: null,
    effective_hymnal: "GG2013",
    ...overrides,
  };
}
''')

Path("frontend/src/lib/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/lib/hymns/picks.test.ts").write_text('''import { describe, expect, it } from "vitest";

import type { Hymn, HymnSuggestions } from "@/lib/api/types";
import type { DraftV1, HymnPick } from "@/lib/draft/schema";
import { hymn, hymnals, suggested, testDraft } from "@/test/fixtures";

import { selectHymnal } from "./hymnal";
import {
  applySuggestions,
  clearSlot,
  duplicateSlots,
  pickFromHymn,
  reconcilePick,
  setExcludeRecent,
  setHymnal,
  setSlot,
  swapAlternative,
} from "./picks";

const HOLY = hymn({ number: 1, title: "Holy, Holy, Holy" });
const PRAISE = hymn({ number: 35, title: "Praise, My Soul, the King of Heaven" });
const GRACE = hymn({ number: 649, title: "Amazing Grace" });
const KING = hymn({ number: 403 });
const pick = (h: Hymn): HymnPick => pickFromHymn(h);

function answer(slots: Partial<HymnSuggestions["slots"]>): HymnSuggestions {
  return {
    hymnal: "GG2013",
    nt_ref: null,
    nt_text_used: false,
    excluded_recent_count: 0,
    slots: { opening: [], response: [], closing: [], ...slots },
  };
}

function withSlots(slots: Partial<DraftV1["hymns"]["slots"]>): DraftV1["hymns"] {
  const d = testDraft();
  return { ...d.hymns, slots: { ...d.hymns.slots, ...slots } };
}

describe("draft transitions (S Pure-function contracts)", () => {
  it("pickFromHymn keeps the id, title, number and hymnal; each setter returns the same draft when nothing changes", () => {
    expect(pickFromHymn(KING)).toEqual({
      hymn_id: KING.id,
      title: "Come, Thou Almighty King",
      number: 403,
      hymnal: "GG2013",
    });
    const d = testDraft();
    const opened = setSlot(d, "opening", pick(KING));
    expect(opened.hymns.slots.opening).toEqual(pick(KING));
    expect(setSlot(opened, "opening", pick(KING))).toBe(opened);
    expect(clearSlot(opened, "opening").hymns.slots.opening).toBeNull();
    expect(clearSlot(d, "closing")).toBe(d);
    // The church's effective hymnal is stored as null, so "New service" never counts it (clarification 2).
    expect(setHymnal(d, "GG2013", "GG2013")).toBe(d);
    const ph = setHymnal(d, "PH1990", "GG2013");
    expect(ph.hymns.hymnal).toBe("PH1990");
    expect(setHymnal(ph, "GG2013", "GG2013").hymns.hymnal).toBeNull();
    expect(setExcludeRecent(d, true)).toBe(d);
    expect(setExcludeRecent(d, false).hymns.exclude_recent).toBe(false);
    expect(setHymnal(opened, "PH1990", "GG2013").hymns.slots.opening).toEqual(pick(KING)); // picks are kept
  });
});

describe("applySuggestions (S AI suggestion flow; owner decision 3, F D16)", () => {
  it("fills only empty slots, gives filled slots ideas without their own pick, caps ideas at 4 and dates them", () => {
    const five = [HOLY, PRAISE, GRACE, KING, hymn({ number: 7 })].map((h) => suggested(h));
    const hymns = withSlots({ response: pick(GRACE) });
    const next = applySuggestions(hymns, answer({ opening: five, response: five, closing: [] }), "2026-10-04");
    expect(next.slots.opening).toEqual(pick(HOLY));
    expect(next.slots.response).toEqual(pick(GRACE)); // the member's pick stays
    expect(next.slots.closing).toBeNull(); // nothing returned for it
    expect(next.alternatives).toEqual({
      for_date_iso: "2026-10-04",
      by_slot: {
        opening: [PRAISE, GRACE, KING, hymn({ number: 7 })].map(pick),
        response: [HOLY, PRAISE, KING, hymn({ number: 7 })].map(pick),
        closing: [],
      },
    });
    expect(next.exclude_recent).toBe(hymns.exclude_recent);
  });

  it("gives at least 2 ideas from a 3-hymn answer: a pick plus 2 for an empty slot, 3 for a filled one", () => {
    const three = [HOLY, PRAISE, GRACE].map((h) => suggested(h));
    const next = applySuggestions(withSlots({ closing: pick(KING) }), answer({ opening: three, closing: three }), "2026-10-04");
    expect(next.slots.opening).toEqual(pick(HOLY));
    expect(next.alternatives?.by_slot.opening).toHaveLength(2);
    expect(next.alternatives?.by_slot.closing).toEqual([HOLY, PRAISE, GRACE].map(pick));
  });
});

describe("swapAlternative (S Other ideas)", () => {
  it("swaps an idea into the slot and the previous pick into its place, so a second tap swaps back", () => {
    const base = applySuggestions(
      withSlots({ opening: pick(KING) }),
      answer({ opening: [HOLY, PRAISE, GRACE].map((h) => suggested(h)) }),
      "2026-10-04",
    );
    const once = swapAlternative(base, "opening", HOLY.id);
    expect(once.slots.opening).toEqual(pick(HOLY));
    expect(once.alternatives?.by_slot.opening).toEqual([KING, PRAISE, GRACE].map(pick));
    const twice = swapAlternative(once, "opening", KING.id);
    expect(twice).toEqual(base);
    // Into an empty slot the idea just moves up; an unknown id or no ideas changes nothing.
    const empty = { ...base, slots: { ...base.slots, opening: null } };
    const moved = swapAlternative(empty, "opening", PRAISE.id);
    expect(moved.slots.opening).toEqual(pick(PRAISE));
    expect(moved.alternatives?.by_slot.opening).toEqual([HOLY, GRACE].map(pick));
    expect(swapAlternative(base, "opening", "nope")).toBe(base);
    const none = withSlots({});
    expect(swapAlternative(none, "opening", HOLY.id)).toBe(none);
  });
});

describe("reconcilePick and duplicateSlots (S Live data, notices)", () => {
  it("finds the live hymn, waits for a list still loading, and reports a missing one", () => {
    const lists = new Map<string, readonly Hymn[] | undefined>([
      ["GG2013", [KING, HOLY]],
      ["PH1990", undefined],
    ]);
    const renamed = { ...pick(KING), title: "Come, Thou Almighty King (old title)" };
    expect(reconcilePick(renamed, lists, "GG2013")).toEqual({ status: "ok", live: KING });
    expect(reconcilePick({ ...pick(KING), hymnal: "PH1990" }, lists, "GG2013")).toEqual({ status: "loading" });
    expect(reconcilePick({ ...pick(KING), hymn_id: null }, lists, "GG2013")).toEqual({ status: "missing" });
    expect(reconcilePick(pick(GRACE), lists, "GG2013")).toEqual({ status: "missing" });
    // A pick with no hymnal (an archived one, 5a) is looked up in the selected hymnal.
    expect(reconcilePick({ ...pick(HOLY), hymnal: null }, lists, "GG2013")).toEqual({ status: "ok", live: HOLY });
    expect(reconcilePick({ ...pick(HOLY), hymnal: "XX" }, lists, "GG2013")).toEqual({ status: "loading" });
  });

  it("names the other slots that hold the same hymn", () => {
    expect(duplicateSlots({ opening: pick(KING), response: pick(HOLY), closing: pick(KING) })).toEqual({
      opening: ["closing"],
      response: [],
      closing: ["opening"],
    });
    const archived = { ...pick(KING), hymn_id: null };
    expect(duplicateSlots({ opening: archived, response: archived, closing: null })).toEqual({
      opening: [],
      response: [],
      closing: [],
    });
  });
});

describe("selectHymnal (S Toolbar)", () => {
  it("uses the stored code when it is listed, the effective hymnal for null, and marks a vanished code stale", () => {
    const two = hymnals({
      items: [
        { code: "GG2013", hymn_count: 853, scripture_ref_count: 795 },
        { code: "PH1990", hymn_count: 605, scripture_ref_count: 0 },
      ],
    });
    expect(selectHymnal("PH1990", two)).toEqual({ code: "PH1990", stale: false });
    expect(selectHymnal(null, two)).toEqual({ code: "GG2013", stale: false });
    expect(selectHymnal("XX1900", two)).toEqual({ code: "GG2013", stale: true });
    expect(selectHymnal(null, hymnals({ items: [], effective_hymnal: null }))).toEqual({ code: null, stale: false });
  });
});
''', encoding="utf-8")
print("T4 tests written")
PYEOF
```

**Expected:** `T4 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/hymns/picks.test.ts 2>&1 | grep -E "^ (FAIL|×)|Error:|Tests |Test Files")
```

**Expected:**

```
 FAIL  |unit| src/lib/hymns/picks.test.ts [ src/lib/hymns/picks.test.ts ]
Error: Cannot find module './hymnal' imported from '<repo>/frontend/src/lib/hymns/picks.test.ts'
 Test Files  1 failed (1)
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the types, `picks.ts` and `hymnal.ts`**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path

types = Path("frontend/src/lib/api/types.ts")
text = types.read_text(encoding="utf-8")
text += '''
/** `GET /hymnals` (slice 3a): the church's hymnals with counts, the stored default and the effective one. */
export type Hymnals = components["schemas"]["HymnalListOut"];
export type HymnalSummary = components["schemas"]["HymnalOut"];
/** One hymn as every hymn route returns it (`HymnOut`, slice 3a). */
export type Hymn = components["schemas"]["HymnOut"];
/** `GET /hymns` (slice 3a): one page of hymns. */
export type HymnPage = components["schemas"]["Page_HymnOut_"];
/** `POST /hymns/scripture-matches` (slice 3a): the request body and the answer. */
export type ScriptureMatchBody = components["schemas"]["ScriptureMatchIn"];
export type ScriptureMatches = components["schemas"]["ScriptureMatchesOut"];
export type HymnMatch = components["schemas"]["HymnMatchOut"];
/** `POST /hymns/suggestions` (slice 3a): the request body and the answer. */
export type HymnSuggestionBody = components["schemas"]["HymnSuggestionIn"];
export type HymnSuggestions = components["schemas"]["HymnSuggestionsOut"];
export type SuggestedHymn = components["schemas"]["SuggestedHymnOut"];
'''
types.write_text(text, encoding="utf-8")

Path("frontend/src/lib/hymns/picks.ts").write_text('''/**
 * The Hymns step's draft transitions and selectors (S "Pure-function
 * contracts"; F §4.6). Pure: each returns the same object when nothing
 * changes, so `update(recipe)` stays a no-op. The draft recipes (`setSlot`,
 * `clearSlot`, `setHymnal`, `setExcludeRecent`) take the whole draft; the
 * suggestion helpers take the `hymns` block, as S names them.
 */
import type { Hymn, HymnSuggestions } from "@/lib/api/types";
import { SLOTS, type DraftV1, type HymnPick, type Slot } from "@/lib/draft/schema";

type HymnsBlock = DraftV1["hymns"];

/** What a slot stores for a hymn: its id and a snapshot of its title, number and hymnal. */
export function pickFromHymn(h: Pick<Hymn, "id" | "title" | "number" | "hymnal">): HymnPick {
  return { hymn_id: h.id, title: h.title, number: h.number, hymnal: h.hymnal };
}

function samePick(a: HymnPick | null, b: HymnPick | null): boolean {
  if (a === null || b === null) return a === b;
  return a.hymn_id === b.hymn_id && a.title === b.title && a.number === b.number && a.hymnal === b.hymnal;
}

function withHymns(d: DraftV1, patch: Partial<HymnsBlock>): DraftV1 {
  return { ...d, hymns: { ...d.hymns, ...patch } };
}

/** Sets one slot (the picker, a match's "Add", Undo). */
export function setSlot(d: DraftV1, slot: Slot, pick: HymnPick | null): DraftV1 {
  if (samePick(d.hymns.slots[slot], pick)) return d;
  return withHymns(d, { slots: { ...d.hymns.slots, [slot]: pick } });
}

/** The ✕ button. */
export function clearSlot(d: DraftV1, slot: Slot): DraftV1 {
  return setSlot(d, slot, null);
}

/**
 * The hymnal Select. The church's effective hymnal is stored as `null`, like
 * the translation (2c), so choosing it again is not unsaved work and a later
 * default change flows through (owner answer 1; clarification 2). Picks are
 * never touched.
 */
export function setHymnal(d: DraftV1, code: string, effective: string | null): DraftV1 {
  const hymnal = code === effective ? null : code;
  return d.hymns.hymnal === hymnal ? d : withHymns(d, { hymnal });
}

/** The Exclude switch. It never changes a slot or an idea (AC12). */
export function setExcludeRecent(d: DraftV1, on: boolean): DraftV1 {
  return d.hymns.exclude_recent === on ? d : withHymns(d, { exclude_recent: on });
}

export type Reconciled = { status: "ok"; live: Hymn } | { status: "loading" } | { status: "missing" };

/**
 * A pick against its hymnal's loaded list (S "Live data"): the live hymn, or
 * "loading" while that list is not loaded, or "missing" when the pick has no
 * id or its id is not in the list. A pick with no hymnal (an archived one,
 * 5a) is looked up in `fallbackHymnal`, the selected one.
 */
export function reconcilePick(
  pick: HymnPick,
  lists: ReadonlyMap<string, readonly Hymn[] | undefined>,
  fallbackHymnal: string | null,
): Reconciled {
  if (pick.hymn_id === null) return { status: "missing" };
  const code = pick.hymnal ?? fallbackHymnal;
  const list = code === null ? undefined : lists.get(code);
  if (list === undefined) return { status: "loading" };
  const live = list.find((h) => h.id === pick.hymn_id);
  return live ? { status: "ok", live } : { status: "missing" };
}

/**
 * The AI's answer applied to the latest hymns (S "AI suggestion flow" 2; F
 * D16): an empty slot takes the first hymn and its ideas are the next ones (2
 * to 4); a filled slot keeps its pick and its ideas are the answer without it
 * (3 to 4). The ideas are dated, so they hide when the service date changes.
 */
export function applySuggestions(hymns: HymnsBlock, resp: HymnSuggestions, dateIso: string): HymnsBlock {
  const slots = { ...hymns.slots };
  const bySlot = { opening: [], response: [], closing: [] } as Record<Slot, HymnPick[]>;
  for (const slot of SLOTS) {
    const list = resp.slots[slot];
    const current = slots[slot];
    if (current === null) {
      if (list.length > 0) slots[slot] = pickFromHymn(list[0]);
      bySlot[slot] = list.slice(1, 5).map(pickFromHymn);
    } else {
      bySlot[slot] = list.filter((h) => h.id !== current.hymn_id).slice(0, 4).map(pickFromHymn);
    }
  }
  return { ...hymns, slots, alternatives: { for_date_iso: dateIso, by_slot: bySlot } };
}

/**
 * A tap on an idea (S "Other ideas"): the slot takes it and the previous pick
 * takes its place among the ideas, unless there was none or it already is an
 * idea; so a second tap swaps back.
 */
export function swapAlternative(hymns: HymnsBlock, slot: Slot, hymnId: string): HymnsBlock {
  const ideas = hymns.alternatives?.by_slot[slot] ?? [];
  const at = ideas.findIndex((idea) => idea.hymn_id === hymnId);
  if (hymns.alternatives === null || at < 0) return hymns;
  const previous = hymns.slots[slot];
  const keepPrevious = previous !== null && !ideas.some((idea) => idea.hymn_id === previous.hymn_id);
  const next = keepPrevious ? ideas.map((idea, i) => (i === at ? previous : idea)) : ideas.filter((_, i) => i !== at);
  return {
    ...hymns,
    slots: { ...hymns.slots, [slot]: ideas[at] },
    alternatives: { ...hymns.alternatives, by_slot: { ...hymns.alternatives.by_slot, [slot]: next } },
  };
}

/** For each slot, the other slots holding the same hymn (the "Also chosen as…" notice). */
export function duplicateSlots(slots: DraftV1["hymns"]["slots"]): Record<Slot, Slot[]> {
  const result = { opening: [], response: [], closing: [] } as Record<Slot, Slot[]>;
  for (const slot of SLOTS) {
    const id = slots[slot]?.hymn_id ?? null;
    if (id === null) continue;
    result[slot] = SLOTS.filter((other) => other !== slot && slots[other]?.hymn_id === id);
  }
  return result;
}
''', encoding="utf-8")

Path("frontend/src/lib/hymns/hymnal.ts").write_text('''/**
 * The selected hymnal (S Toolbar): resolved only from a loaded `GET /hymnals`
 * answer, never from missing data. The step never writes the result back to
 * the draft, so a vanished code never marks a service dirty on its own.
 */
import type { Hymnals } from "@/lib/api/types";

export type SelectedHymnal = {
  /** The hymnal the list, matches and suggestions use; null only when the church has no hymnals. */
  code: string | null;
  /** True when the stored code is no longer one of the church's hymnals. */
  stale: boolean;
};

export function selectHymnal(stored: string | null, hymnals: Hymnals): SelectedHymnal {
  if (stored !== null && hymnals.items.some((item) => item.code === stored)) return { code: stored, stale: false };
  return { code: hymnals.effective_hymnal, stale: stored !== null };
}
''', encoding="utf-8")
print("T4 code written")
PYEOF
```

**Expected:** `T4 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/hymns/picks.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  1 passed (1)`, `      Tests  7 passed (7)`; ` Test Files  56 passed (56)`, `      Tests  366 passed (366)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `types.ts` and `fixtures/index.ts`, `?? frontend/src/lib/hymns/`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts frontend/src/lib/hymns/picks.ts frontend/src/lib/hymns/hymnal.ts frontend/src/lib/hymns/picks.test.ts
git commit -m "Hymns: the step's draft transitions, suggestion helpers and the selected hymnal (S Pure-function contracts)" -m "pickFromHymn, setSlot, clearSlot, setHymnal (the effective hymnal is
stored as null, owner answer 1), setExcludeRecent, reconcilePick (ok,
loading or missing, with the selected hymnal for a pick with none),
applySuggestions (empty slots only, F D16), swapAlternative (a second tap
swaps back) and duplicateSlots; selectHymnal (stored, effective, or stale).
Type names for the 3a routes and hymn fixtures. Frontend 359 -> 366.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 5 files changed.

### Task 5: The picker's search, the step's words, and the two request builders (S Picker "Ranking", Slot cards "Notices", "Newer-hymn year label", `buildMatchRefs`, `buildSuggestionRequest`; clarifications 5, 10, 12)

`filterHymns` is the picker's search: numbers by exact, then prefix, then titles containing the digits; words by title start, then word start, then anywhere, ignoring accents, case and punctuation (clarification 12); hymnal order within a group; blank titles never listed; at most 50 shown; with `excludeRecent`, recent hymns are left out and counted. `labels.ts` holds S's copy for slots, notices, badges, the newer-hymn label and the ideas' accessible names. `formatAbbrevDate` ("Sep 7", with the year when it differs from the service's) joins `lib/dates.ts`; S calls it `formatShortDate`, which 2b already uses for "October 4" (clarification 5). `buildMatchRefs` and `buildSuggestionRequest` keep every request inside the server's limits, and the suggestion request reads passage text only from the cache (clarification 10).

**Files:**
- Create: `frontend/src/lib/hymns/filter.ts`, `labels.ts`, `match-request.ts`, `suggest-request.ts`
- Modify: `frontend/src/lib/dates.ts` (`formatAbbrevDate`)
- Test: `frontend/src/lib/hymns/filter.test.ts` (new, 6), `labels.test.ts` (new, 4), `match-request.test.ts` (new, 2), `suggest-request.test.ts` (new, 3), `frontend/src/lib/dates.test.ts` (+1)

**Interfaces:**
- Consumes: `Hymn`, `HymnSuggestionBody`, `Passage` (T4, 2a); `passageText` (`lib/queries/passages.ts`, 2c); `formatServiceDate`, `parseIsoDate` (2b).
- Produces:
  - `formatAbbrevDate(iso, contextIso?) -> string` in `lib/dates.ts`.
  - `filter.ts`: `PICKER_LIMIT = 50`; `foldText(text)`; `type FilterResult = {shown: Hymn[]; totalMatches: number; hiddenRecent: number}`; `filterHymns(items, query, {excludeRecent})`. Later users: T7, T8.
  - `labels.ts`: `SLOT_META: Record<Slot, {title, caption, name}>`, `MISSING_NOTICE`, `hymnText(h)`, `recentUseLabel(dateIso, serviceIso)`, `recentUseNotice(dateIso, serviceIso)`, `duplicateNotice(others)`, `newerYearLabel(h)`, `chipName(h, slot)`. Later users: T8-T12.
  - `match-request.ts`: `MAX_REFS = 20`, `MAX_REF_LENGTH = 200`, `cleanRefs(list, {max, maxLen})`, `buildMatchRefs(scriptures, extraRef)`. Later user: T11.
  - `suggest-request.ts`: `buildSuggestionRequest(draft, selectedHymnal, getCachedPassage, churchTranslation) -> HymnSuggestionBody`. Later user: T10.

Counts after this task: frontend **382 passed in 60 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "formatAbbrevDate" frontend/src/lib/dates.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  56 passed (56)`, `      Tests  366 passed (366)`.

- [ ] **Step 2 (agent): Write the failing tests**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/lib/dates.test.ts", [
    ("  addDays,\n  formatLongDate,\n", "  addDays,\n  formatAbbrevDate,\n  formatLongDate,\n"),
    ('''  it("isFirstSundayOfMonth is true only for a Sunday on days 1-7", () => {''',
     '''  it("formatAbbrevDate gives the short month and day, with the year only when it differs (slice 3b)", () => {
    expect(formatAbbrevDate("2026-09-07", "2026-10-04")).toBe("Sep 7");
    expect(formatAbbrevDate("2026-10-18")).toBe("Oct 18");
    expect(formatAbbrevDate("2025-12-28", "2026-01-04")).toBe("Dec 28, 2025");
    expect(formatAbbrevDate("2027-01-03", "2026-12-27")).toBe("Jan 3, 2027");
    expect(formatAbbrevDate("2026-05-31", "not a date")).toBe("May 31");
    expect(formatAbbrevDate("2026-9-7", "2026-10-04")).toBe("");
  });

  it("isFirstSundayOfMonth is true only for a Sunday on days 1-7", () => {'''),
])

Path("frontend/src/lib/hymns/filter.test.ts").write_text('''import { describe, expect, it } from "vitest";

import type { Hymn } from "@/lib/api/types";
import { hymn, hymnId } from "@/test/fixtures";

import { filterHymns, PICKER_LIMIT } from "./filter";

const numbers = (r: { shown: Hymn[] }) => r.shown.map((h) => h.number);

describe("filterHymns (S Picker ranking)", () => {
  it("ranks an exact number first, then numbers that start with the digits, then titles containing them", () => {
    const items = [
      hymn({ number: 1403, title: "Lord, Speak to Me" }),
      hymn({ number: 40, title: "Hymn of Promise" }),
      hymn({ number: 403, title: "Come, Thou Almighty King" }),
      hymn({ number: 12, title: "Psalm 40: I Waited Patiently" }),
      hymn({ number: 4030, title: "Another" }),
    ];
    expect(numbers(filterHymns(items, "403", { excludeRecent: false }))).toEqual([403, 4030]);
    expect(numbers(filterHymns(items, " 40 ", { excludeRecent: false }))).toEqual([40, 403, 4030, 12]);
  });

  it("matches titles by start, then word start, then anywhere, ignoring accents, case and punctuation", () => {
    const items = [
      hymn({ number: 1, title: "Now Thank We All Our God" }),
      hymn({ number: 2, title: "Thanks to God Whose Word Was Spoken" }),
      hymn({ number: 3, title: "Unthankful Hearts" }),
      hymn({ number: 4, title: "Jésus, Joy of Our Desiring" }),
      hymn({ number: 5, title: "Come, Thou Almighty King" }),
    ];
    expect(numbers(filterHymns(items, "THANK", { excludeRecent: false }))).toEqual([2, 1, 3]);
    expect(numbers(filterHymns(items, "jesus", { excludeRecent: false }))).toEqual([4]);
    expect(numbers(filterHymns(items, "come thou", { excludeRecent: false }))).toEqual([5]);
    expect(numbers(filterHymns(items, "", { excludeRecent: false }))).toEqual([1, 2, 3, 4, 5]); // hymnal order
  });

  it("shows at most 50 and counts every match", () => {
    const items = Array.from({ length: 120 }, (_, i) => hymn({ number: i + 1, title: `Grace ${i + 1}` }));
    const all = filterHymns(items, "grace", { excludeRecent: false });
    expect(PICKER_LIMIT).toBe(50);
    expect(all.shown).toHaveLength(50);
    expect(all.totalMatches).toBe(120);
    expect(all.shown[0].number).toBe(1);
  });

  it("blank titles never listed", () => {
    const items = [hymn({ number: 1, title: "" }), hymn({ number: 2, title: "   " }), hymn({ number: 3, title: "Amazing Grace" })];
    expect(numbers(filterHymns(items, "", { excludeRecent: false }))).toEqual([3]);
    expect(numbers(filterHymns(items, "1", { excludeRecent: false }))).toEqual([]);
  });

  it("same title stays distinct by id", () => {
    const items = [
      hymn({ id: hymnId(9001), number: 188, title: "Jesus Loves Me" }),
      hymn({ id: hymnId(9002), number: 189, title: "Jesus Loves Me" }),
    ];
    const r = filterHymns(items, "jesus loves", { excludeRecent: false });
    expect(r.shown.map((h) => [h.id, h.number])).toEqual([
      [hymnId(9001), 188],
      [hymnId(9002), 189],
    ]);
  });

  it("with excludeRecent, hides recently used hymns and counts them", () => {
    const items = [
      hymn({ number: 1, title: "Holy, Holy, Holy", recent_use_on: "2026-09-06" }),
      hymn({ number: 2, title: "Holy Spirit, Truth Divine" }),
      hymn({ number: 3, title: "Holy God, We Praise Your Name", recent_use_on: "2026-10-18" }),
    ];
    const hidden = filterHymns(items, "holy", { excludeRecent: true });
    expect(numbers(hidden)).toEqual([2]);
    expect(hidden).toMatchObject({ totalMatches: 1, hiddenRecent: 2 });
    expect(filterHymns(items, "holy", { excludeRecent: false })).toMatchObject({ totalMatches: 3, hiddenRecent: 0 });
  });
});
''', encoding="utf-8")

Path("frontend/src/lib/hymns/labels.test.ts").write_text('''import { describe, expect, it } from "vitest";

import { hymn } from "@/test/fixtures";

import {
  chipName,
  duplicateNotice,
  hymnText,
  newerYearLabel,
  recentUseLabel,
  recentUseNotice,
  SLOT_META,
} from "./labels";

describe("hymn labels (S Slot cards, Newer-hymn year label)", () => {
  it("names the slots and shows a hymn as #number title", () => {
    expect(SLOT_META.opening).toEqual({ title: "Opening hymn", caption: "Gathering / call to worship", name: "Opening" });
    expect(SLOT_META.response.caption).toBe("After the sermon — responds to the scripture (NT reading)");
    expect(SLOT_META.closing).toEqual({ title: "Closing hymn", caption: "Joyful / sending", name: "Closing" });
    expect(hymnText({ number: 403, title: "Come, Thou Almighty King" })).toBe("#403 Come, Thou Almighty King");
    expect(hymnText({ number: null, title: "Were You There" })).toBe("Were You There");
  });

  it("says Used on for a date before the service and Also planned for after it", () => {
    expect(recentUseNotice("2026-09-07", "2026-10-04")).toBe("Used on September 7, 2026 — within 12 weeks of this service.");
    expect(recentUseNotice("2026-10-18", "2026-10-04")).toBe(
      "Also planned for October 18, 2026 — within 12 weeks of this service.",
    );
    expect(recentUseLabel("2026-09-07", "2026-10-04")).toBe("Used Sep 7");
    expect(recentUseLabel("2026-10-18", "2026-10-04")).toBe("Planned Oct 18");
    expect(recentUseLabel("2025-12-28", "2026-01-04")).toBe("Used Dec 28, 2025");
  });

  it("labels a newer hymn with its year, and names ideas for screen readers", () => {
    const newer = hymn({ title: "Here I Am, Lord", text_year: 1981, newer_than_preferred: true });
    expect(newerYearLabel(newer)).toBe("Written 1981");
    expect(newerYearLabel(hymn({ text_year: 1826 }))).toBeNull();
    expect(newerYearLabel(hymn({ text_year: null, newer_than_preferred: true }))).toBeNull();
    expect(chipName(newer, "response")).toBe("Use Here I Am, Lord, written 1981, as the response hymn");
    expect(chipName(hymn({ text_year: 1826 }), "opening")).toBe("Use Come, Thou Almighty King as the opening hymn");
  });

  it("names the other slots that hold the same hymn", () => {
    expect(duplicateNotice(["closing"])).toBe("Also chosen as the Closing hymn.");
    expect(duplicateNotice(["opening", "closing"])).toBe("Also chosen as the Opening and Closing hymns.");
    expect(duplicateNotice([])).toBeNull();
  });
});
''', encoding="utf-8")

Path("frontend/src/lib/hymns/match-request.test.ts").write_text('''import { describe, expect, it } from "vitest";

import { buildMatchRefs, cleanRefs } from "./match-request";

describe("cleanRefs and buildMatchRefs (S buildMatchRefs)", () => {
  it("trims, drops blanks, cuts each line to 200 and keeps at most the first max", () => {
    expect(cleanRefs(["  Mark 1:9-15 ", "", "   ", "Psalm 25"], { max: 20, maxLen: 200 })).toEqual(["Mark 1:9-15", "Psalm 25"]);
    const long = "Isaiah 40:1-11 " + "x".repeat(485);
    expect(cleanRefs([long], { max: 20, maxLen: 200 })[0]).toHaveLength(200);
    const many = Array.from({ length: 25 }, (_, i) => `Psalm ${i + 1}`);
    expect(cleanRefs(many, { max: 20, maxLen: 200 })).toHaveLength(20);
  });

  it("puts the extra reference last, keeps it with 25 readings, and never sends it twice", () => {
    const many = Array.from({ length: 25 }, (_, i) => `Psalm ${i + 1}`);
    const refs = buildMatchRefs(many, "  Matthew 17 ");
    expect(refs).toHaveLength(20);
    expect(refs.at(-1)).toBe("Matthew 17");
    expect(refs[18]).toBe("Psalm 19");
    expect(buildMatchRefs(["Mark 1:9-15", "Psalm 25"], "Psalm 25")).toEqual(["Mark 1:9-15", "Psalm 25"]);
    expect(buildMatchRefs(["Mark 1:9-15"], "   ")).toEqual(["Mark 1:9-15"]);
    expect(buildMatchRefs([], "x".repeat(500))).toEqual(["x".repeat(200)]);
  });
});
''', encoding="utf-8")

Path("frontend/src/lib/hymns/suggest-request.test.ts").write_text('''import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";
import { editOccasion, editScriptureLines, setPick, setTranslation } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { hymn, testDraft } from "@/test/fixtures";

import { pickFromHymn, setSlot } from "./picks";
import { buildSuggestionRequest } from "./suggest-request";

const LINES = "Isaiah 5:1-7\\nPsalm 80:7-15\\nPhilippians 3:4b-14\\nMatthew 21:33-46";

function passage(ref: string, text: string | null): Passage {
  return { reference: ref, status: text ? "ok" : "unavailable", sections: [{ reference: ref, status: text ? "ok" : "unavailable", text }] };
}

/** A cache holding the Matthew text in `translation` only. */
function cache(translation: string) {
  return (t: string, ref: string) => (t === translation && ref === "Matthew 21:33-46" ? passage(ref, "The parable of the tenants.") : undefined);
}

function draft(recipe: (d: DraftV1) => DraftV1 = (d) => d): DraftV1 {
  return recipe(editScriptureLines(editOccasion(testDraft(), "Nineteenth Sunday after Pentecost"), LINES));
}

describe("buildSuggestionRequest (S buildSuggestionRequest)", () => {
  it("sends the cached NT text only with a chosen NT reading, a translation other than ESV and text in the cache", () => {
    const picked = draft((d) => setPick(d, "nt", "Matthew 21:33-46"));
    expect(buildSuggestionRequest(picked, "GG2013", cache("web"), "web").nt_text).toBe("The parable of the tenants.");
    expect(buildSuggestionRequest(draft(), "GG2013", cache("web"), "web").nt_text).toBeUndefined(); // automatic NT
    expect(buildSuggestionRequest(picked, "GG2013", cache("web"), "esv")).not.toHaveProperty("nt_text"); // church ESV
    const esv = setTranslation(picked, "esv", "web");
    expect(buildSuggestionRequest(esv, "GG2013", cache("esv"), "web").nt_text).toBeUndefined(); // chosen ESV
    const kjv = setTranslation(picked, "kjv", "web");
    expect(buildSuggestionRequest(kjv, "GG2013", cache("kjv"), "web").nt_text).toBe("The parable of the tenants.");
    expect(buildSuggestionRequest(kjv, "GG2013", cache("web"), "web").nt_text).toBeUndefined(); // not cached in KJV
    const failed = (_t: string, ref: string) => passage(ref, null);
    expect(buildSuggestionRequest(picked, "GG2013", failed, "web").nt_text).toBeUndefined();
    const long = (_t: string, ref: string) => passage(ref, "y".repeat(25_000));
    expect(buildSuggestionRequest(picked, "GG2013", long, "web").nt_text).toHaveLength(20_000);
  });

  it("trims and caps the readings, the occasion and the NT reading; a blank NT reading is null", () => {
    const lines = ["  Mark 1:9-15  ", "", ...Array.from({ length: 24 }, (_, i) => `Psalm ${i + 1}`)].join("\\n");
    const d = editOccasion(editScriptureLines(testDraft(), lines), `  ${"o".repeat(400)}  `);
    const body = buildSuggestionRequest(d, "GG2013", () => undefined, "web");
    expect(body.scriptures).toHaveLength(20);
    expect(body.scriptures?.[0]).toBe("Mark 1:9-15");
    expect(body.occasion).toBe("o".repeat(300));
    expect(body.selected_nt_ref).toBeNull();
    const spaced = { ...d, readings: { ...d.readings, selected_nt_ref: "   " } };
    expect(buildSuggestionRequest(spaced, "GG2013", () => undefined, "web").selected_nt_ref).toBeNull();
    const longRef = { ...d, readings: { ...d.readings, selected_nt_ref: ` ${"M".repeat(250)} ` } };
    expect(buildSuggestionRequest(longRef, "GG2013", () => undefined, "web").selected_nt_ref).toBe("M".repeat(200));
  });

  it("sends the selected hymnal, the date, the Exclude switch and the slots' ids as exclusion hints", () => {
    const king = hymn({ number: 403 });
    const d = setSlot({ ...draft(), hymns: { ...draft().hymns, hymnal: "XX1900", exclude_recent: false } }, "response", pickFromHymn(king));
    expect(buildSuggestionRequest(d, "GG2013", () => undefined, "web")).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "Nineteenth Sunday after Pentecost",
      scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
      selected_nt_ref: null,
      hymnal: "GG2013",
      exclude_recent: false,
      current_picks: { opening: null, response: king.id, closing: null },
    });
  });
});
''', encoding="utf-8")
print("T5 tests written")
PYEOF
```

**Expected:** `T5 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/dates.test.ts src/lib/hymns 2>&1 | grep -E "^ (FAIL|×)|Error:|Tests |Test Files")
```

**Expected** (`<repo>` is the checkout's absolute path):

```
 FAIL  |unit| src/lib/hymns/filter.test.ts [ src/lib/hymns/filter.test.ts ]
Error: Cannot find module './filter' imported from '<repo>/frontend/src/lib/hymns/filter.test.ts'
 FAIL  |unit| src/lib/hymns/labels.test.ts [ src/lib/hymns/labels.test.ts ]
Error: Cannot find module './labels' imported from '<repo>/frontend/src/lib/hymns/labels.test.ts'
 FAIL  |unit| src/lib/hymns/match-request.test.ts [ src/lib/hymns/match-request.test.ts ]
Error: Cannot find module './match-request' imported from '<repo>/frontend/src/lib/hymns/match-request.test.ts'
 FAIL  |unit| src/lib/hymns/suggest-request.test.ts [ src/lib/hymns/suggest-request.test.ts ]
Error: Cannot find module './suggest-request' imported from '<repo>/frontend/src/lib/hymns/suggest-request.test.ts'
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/dates.test.ts > lib/dates > formatAbbrevDate gives the short month and day, with the year only when it differs (slice 3b)
TypeError: (0 , formatAbbrevDate) is not a function
 Test Files  5 failed | 1 passed (6)
      Tests  1 failed | 14 passed (15)
```

(Each "Cannot find module" is followed by a "Caused by:" line the grep also prints.)

- [ ] **Step 4 (agent): Write the four modules and `formatAbbrevDate`**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/lib/dates.ts", [
    ('''/** "October 4"; "" for an invalid date. */
export function formatShortDate(iso: string): string {
  const p = parseIsoDate(iso);
  return p ? `${MONTHS[p.m - 1]} ${p.d}` : "";
}
''', '''/** "October 4"; "" for an invalid date. */
export function formatShortDate(iso: string): string {
  const p = parseIsoDate(iso);
  return p ? `${MONTHS[p.m - 1]} ${p.d}` : "";
}

/**
 * "Sep 7" (slice 3b's recent-use badges); "Dec 28, 2025" when the year differs
 * from `contextIso`'s (the service date) and `contextIso` is a valid date; ""
 * for an invalid date.
 */
export function formatAbbrevDate(iso: string, contextIso?: string): string {
  const p = parseIsoDate(iso);
  if (!p) return "";
  const text = `${MONTHS[p.m - 1].slice(0, 3)} ${p.d}`;
  const context = contextIso === undefined ? null : parseIsoDate(contextIso);
  return context && context.y !== p.y ? `${text}, ${p.y}` : text;
}
'''),
])

Path("frontend/src/lib/hymns/filter.ts").write_text('''/**
 * The hymn picker's search (S Picker "Ranking"): pure, over one hymnal's list.
 *
 * - All digits: the exact number first, then numbers that start with the
 *   digits, then titles containing them.
 * - Otherwise: titles that start with the words, then titles with a word that
 *   starts with them, then titles containing them. Accents, case and
 *   punctuation are ignored ("come thou" finds "Come, Thou Almighty King";
 *   clarification 12).
 * - Within each group, hymnal order. Blank titles are never listed. With
 *   `excludeRecent`, hymns with a recent use are left out and counted.
 */
import type { Hymn } from "@/lib/api/types";

/** F §4.9 item 5: a long list renders at most this many matches. */
export const PICKER_LIMIT = 50;

export type FilterResult = {
  /** At most PICKER_LIMIT matches, best first. */
  shown: Hymn[];
  /** Every match after the exclusion. */
  totalMatches: number;
  /** Matches left out because they were used within 12 weeks. */
  hiddenRecent: number;
};

/** Lower case, accents removed, anything but letters and digits as one space. */
export function foldText(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/\\p{M}+/gu, "")
    .toLowerCase()
    .replace(/[^\\p{L}\\p{N}]+/gu, " ")
    .trim();
}

function rank(h: Hymn, q: string, digits: boolean): number {
  if (digits) {
    const number = h.number === null ? "" : String(h.number);
    if (number === q) return 0;
    if (number.startsWith(q)) return 1;
    return foldText(h.title).includes(q) ? 2 : -1;
  }
  const title = foldText(h.title);
  if (title.startsWith(q)) return 0;
  if (title.includes(` ${q}`)) return 1;
  return title.includes(q) ? 2 : -1;
}

export function filterHymns(items: readonly Hymn[], query: string, { excludeRecent }: { excludeRecent: boolean }): FilterResult {
  const trimmed = query.trim();
  const digits = /^[0-9]+$/.test(trimmed);
  const q = digits ? trimmed : foldText(trimmed);
  const groups: Hymn[][] = [[], [], []];
  let hiddenRecent = 0;
  for (const h of items) {
    if (h.title.trim() === "") continue;
    const group = q === "" ? 0 : rank(h, q, digits);
    if (group < 0) continue;
    if (excludeRecent && h.recent_use_on !== null) {
      hiddenRecent += 1;
      continue;
    }
    groups[group].push(h);
  }
  const matches = groups.flat();
  return { shown: matches.slice(0, PICKER_LIMIT), totalMatches: matches.length, hiddenRecent };
}
''', encoding="utf-8")

Path("frontend/src/lib/hymns/labels.ts").write_text('''/**
 * The Hymns step's words (S Slot cards, notices, chips, "Newer-hymn year
 * label"). Pure; dates go through `lib/dates.ts`.
 */
import type { Hymn } from "@/lib/api/types";
import { formatAbbrevDate, formatServiceDate } from "@/lib/dates";
import type { Slot } from "@/lib/draft/schema";

export const SLOT_META: Record<Slot, { title: string; caption: string; name: string }> = {
  opening: { title: "Opening hymn", caption: "Gathering / call to worship", name: "Opening" },
  response: { title: "Response hymn", caption: "After the sermon — responds to the scripture (NT reading)", name: "Response" },
  closing: { title: "Closing hymn", caption: "Joyful / sending", name: "Closing" },
};

export const MISSING_NOTICE = "Not in your hymnal. Choose a replacement.";

/** "#403 Come, Thou Almighty King", or the title alone when the number is null. */
export function hymnText(h: { number: number | null; title: string }): string {
  return h.number === null ? h.title : `#${h.number} ${h.title}`;
}

/** The badge on a picker row or idea: "Used Sep 7" before the service, "Planned Oct 18" after it. */
export function recentUseLabel(dateIso: string, serviceDateIso: string): string {
  return `${dateIso < serviceDateIso ? "Used" : "Planned"} ${formatAbbrevDate(dateIso, serviceDateIso)}`;
}

/** The notice under a pick (only when the service date is valid). */
export function recentUseNotice(dateIso: string, serviceDateIso: string): string {
  const day = formatServiceDate(dateIso);
  return dateIso < serviceDateIso
    ? `Used on ${day} — within 12 weeks of this service.`
    : `Also planned for ${day} — within 12 weeks of this service.`;
}

/** "Also chosen as the Closing hymn." / "… the Opening and Closing hymns."; null when no other slot. */
export function duplicateNotice(others: readonly Slot[]): string | null {
  if (others.length === 0) return null;
  const names = others.map((slot) => SLOT_META[slot].name);
  return others.length === 1
    ? `Also chosen as the ${names[0]} hymn.`
    : `Also chosen as the ${names.slice(0, -1).join(", ")} and ${names.at(-1)} hymns.`;
}

/** "Written 1985" for a hymn the server flags as newer than the church prefers; else null (amendment 2026-09-26). */
export function newerYearLabel(h: Pick<Hymn, "newer_than_preferred" | "text_year">): string | null {
  return h.newer_than_preferred && h.text_year !== null ? `Written ${h.text_year}` : null;
}

/** An idea's accessible name: "Use {title} as the opening hymn", with ", written {year}," for a flagged hymn. */
export function chipName(h: Pick<Hymn, "title" | "newer_than_preferred" | "text_year">, slot: Slot): string {
  const year = newerYearLabel(h) === null ? "" : `, written ${h.text_year},`;
  return `Use ${h.title}${year} as the ${slot} hymn`;
}
''', encoding="utf-8")

Path("frontend/src/lib/hymns/match-request.ts").write_text('''/**
 * The references a scripture-match request sends (S `buildMatchRefs`), within
 * `ScriptureMatchIn`'s limits (at most 20, each at most 200 characters), so a
 * long typed line can never cause a 422 that Retry cannot clear.
 */
export const MAX_REFS = 20;
export const MAX_REF_LENGTH = 200;

/** Each item trimmed, blanks dropped, each cut to `maxLen`, the first `max` kept. */
export function cleanRefs(list: readonly string[], { max, maxLen }: { max: number; maxLen: number }): string[] {
  return list
    .map((line) => line.trim().slice(0, maxLen).trim())
    .filter((line) => line !== "")
    .slice(0, max);
}

/** The cleaned draft scriptures (19 at most when there is an extra reference), then the extra one, never twice. */
export function buildMatchRefs(scriptures: readonly string[], extraRef: string): string[] {
  const [extra] = cleanRefs([extraRef], { max: 1, maxLen: MAX_REF_LENGTH });
  if (extra === undefined) return cleanRefs(scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH });
  const base = cleanRefs(scriptures, { max: MAX_REFS - 1, maxLen: MAX_REF_LENGTH });
  return base.includes(extra) ? base : [...base, extra];
}
''', encoding="utf-8")

Path("frontend/src/lib/hymns/suggest-request.ts").write_text('''/**
 * The `POST /hymns/suggestions` body (S `buildSuggestionRequest`). Pure: the
 * step passes a reader of the passage cache (`queryClient.getQueryData`), so
 * building a request never fetches a passage.
 */
import type { HymnSuggestionBody, Passage } from "@/lib/api/types";
import type { DraftV1 } from "@/lib/draft/schema";
import { passageText } from "@/lib/queries/passages";

import { cleanRefs, MAX_REF_LENGTH, MAX_REFS } from "./match-request";

export const MAX_OCCASION = 300;
export const MAX_NT_TEXT = 20_000;

/**
 * `nt_text` goes only when all hold: an NT reading was chosen in step 1, the
 * translation shown (`draft.readings.translation ?? churchTranslation`) is
 * not ESV (Crossway's terms), and that reading's text is already cached under
 * `["passage", translation, ref]` with `ref` exactly as stored.
 */
export function buildSuggestionRequest(
  draft: DraftV1,
  selectedHymnal: string,
  getCachedPassage: (translation: string, ref: string) => Passage | undefined,
  churchTranslation: string,
): HymnSuggestionBody {
  const r = draft.readings;
  const ntRef = r.selected_nt_ref.trim().slice(0, MAX_REF_LENGTH);
  const body: HymnSuggestionBody = {
    service_date_iso: r.date_iso,
    occasion: r.occasion.trim().slice(0, MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
    selected_nt_ref: ntRef === "" ? null : ntRef,
    hymnal: selectedHymnal,
    exclude_recent: draft.hymns.exclude_recent,
    current_picks: {
      opening: draft.hymns.slots.opening?.hymn_id ?? null,
      response: draft.hymns.slots.response?.hymn_id ?? null,
      closing: draft.hymns.slots.closing?.hymn_id ?? null,
    },
  };
  const translation = r.translation ?? churchTranslation;
  if (ntRef !== "" && translation !== "esv") {
    const cached = getCachedPassage(translation, r.selected_nt_ref);
    const text = cached ? passageText(cached) : null;
    if (text) body.nt_text = text.slice(0, MAX_NT_TEXT);
  }
  return body;
}
''', encoding="utf-8")
print("T5 code written")
PYEOF
```

**Expected:** `T5 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/dates.test.ts src/lib/hymns 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
(cd frontend && npx vitest run src/lib/dates.guard.test.ts 2>&1 | grep -E "Tests ")
```

**Expected:** ` Test Files  6 passed (6)`, `      Tests  30 passed (30)`; ` Test Files  60 passed (60)`, `      Tests  382 passed (382)`; `> tsc --noEmit` and `> eslint` with nothing after them; the date guard still passes (`Tests  <n> passed`).

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/dates.ts frontend/src/lib/dates.test.ts frontend/src/lib/hymns/filter.ts frontend/src/lib/hymns/filter.test.ts frontend/src/lib/hymns/labels.ts frontend/src/lib/hymns/labels.test.ts frontend/src/lib/hymns/match-request.ts frontend/src/lib/hymns/match-request.test.ts frontend/src/lib/hymns/suggest-request.ts frontend/src/lib/hymns/suggest-request.test.ts
git commit -m "Hymns: search ranking, labels, and the match and suggestion request builders (S Picker, Frontend)" -m "filterHymns ranks numbers (exact, prefix, then titles with the digits)
and words (start, word start, anywhere; accents, case and punctuation
ignored), keeps hymnal order within a group, never lists a blank title,
shows 50 and counts recent hymns it hides. labels.ts holds the slot copy,
notices, badges and \"Written {year}\". buildMatchRefs and
buildSuggestionRequest keep requests inside the server's limits; NT text
comes only from the passage cache, never ESV. formatAbbrevDate gives
\"Sep 7\". Frontend 366 -> 382 tests in 60 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 10 files changed.

**Review checkpoint (T4-T5, batch 2):** the draft recipes return the same object when nothing changes; `setHymnal` stores `null` for the effective hymnal; `applySuggestions` never touches a filled slot (F D16) and dates the ideas; `filterHymns` never lists a blank title and counts what exclusion hides; `buildMatchRefs` and `buildSuggestionRequest` stay inside `ScriptureMatchIn` and `HymnSuggestionIn`'s limits; nothing outside `lib/dates.ts` parses a date-only value; the counts match.

### Task 6: The hymn queries: hymnals, lists, scripture matches and suggestions, church-scoped (S Queries, "Stale and cross-church protection", "Client timeouts"; F §4.4, §1.8; clarifications 6, 20)

The step never calls `apiFetch` (F §4.4); it reads through five hooks in `lib/queries/hymns.ts`, all on the church client, so every request carries `X-Church-Id`. `useHymnals` is `GET /hymnals`; `useHymnList` and `useHymnLists` are `GET /hymns?hymnal=…&limit=2000&recent_for_date=…` under one key shape, so the selected hymnal and each pick's hymnal share the cache (at most four lists); `useScriptureMatches` posts the matches as a query keyed under the hymns prefix, so 6a's invalidation refreshes them. `useSuggestHymns` returns `suggest(body, signal)`, which resolves to `ok`, `error` or `superseded`: each call is tracked with `createLatestTracker` and records its church, so an older answer never overwrites a newer one and nothing reaches a step that unmounted or a church that changed (clarification 6). The suggestion call gets its 90 s client timeout, `lib/features.ts` holds `SETTINGS_HYMNS_READY = false` for the empty-hymnal state, and the fixtures gain the hymnal lists, a `GET /hymns` route and the match and suggestion bodies the step tests use (clarification 20).

**Files:**
- Create: `frontend/src/lib/queries/hymns.ts`, `frontend/src/lib/features.ts`
- Modify: `frontend/src/lib/queries/keys.ts` (`hymnMatches`), `frontend/src/lib/api/timeouts.ts` (90 s), `frontend/src/test/fixtures/index.ts` (hymn lists and bodies)
- Test: `frontend/src/lib/queries/hymns.test.tsx` (new, 6), `frontend/src/lib/queries/keys.test.ts` (one test edited, 0)

**Interfaces:**
- Consumes: `useApi`, `useChurchMutation` (`lib/queries/client.ts`), `useChurch`, `createLatestTracker` (`lib/latest.ts`), `keys.hymns`, `keys.hymnals`; the T4 type names.
- Produces:
  - `keys.hymnMatches(id, params)` → `["church", id, "hymns", "matches", params]`.
  - `HYMN_LIST_LIMIT = 2000`, `MAX_LISTS = 4`, `MATCH_RESULTS = 30`.
  - `useHymnals(): UseQueryResult<Hymnals, ApiError>`.
  - `useHymnList(hymnal | null, recentForDate | null): UseQueryResult<Hymn[], ApiError>` (the page's `items`).
  - `useHymnLists(hymnals: (string | null)[], recentForDate): {lists: Map<string, Hymn[] | undefined>; failed: ReadonlySet<string>; fetching: boolean; retry(): void}`.
  - `useScriptureMatches({refs, hymnal, recentForDate, enabled}): UseQueryResult<ScriptureMatches, ApiError>` (no request without refs or hymnal, or with `enabled` false).
  - `type SuggestOutcome = {status: "ok"; data} | {status: "error"; error: ApiError} | {status: "superseded"}`; `useSuggestHymns(): {suggest(body, signal?): Promise<SuggestOutcome>; isPending: boolean}`.
  - `SETTINGS_HYMNS_READY` in `lib/features.ts`.
  - fixtures: `gg2013()` (nine hymns in hymnal order: #1, #35 with no link, #403, #649 and #650 "Amazing Grace" (#650's link is `http:`), #700, #710 "Here I Am, Lord" written 1981 and flagged newer, #800 with a blank title, and "Sent Forth by God's Blessing" with no number), `ph1990()` (two hymns, no scripture references), `twoHymnals()`, `hymnListRoute(lists?, recent?)` (a `GET /hymns` handler that sets `recent_use_on` from a title → date map when `recent_for_date` is sent), `hymnMatch(h, strength, refs)`, `scriptureMatches(overrides)` (October 4, 2026's readings: one passage match, three chapter matches), `hymnSuggestions(slots, overrides)`.
  - Later users: T8-T12.

Counts after this task: frontend **388 passed in 61 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/lib/queries/hymns.ts frontend/src/lib/features.ts 2>&1 | head -2
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); two `No such file or directory` lines; ` Test Files  60 passed (60)`, `      Tests  382 passed (382)`.

- [ ] **Step 2 (agent): Write the failing tests and the fixtures**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


Path("frontend/src/lib/queries/hymns.test.tsx").write_text('''/**
 * The Hymns step's queries (S Queries, "Stale and cross-church protection";
 * F §4.4, §1.8): every request is church-scoped (`X-Church-Id`), every key
 * sits under ["church", id, "hymns"] or ["church", id, "hymnals"], the
 * suggestion call waits up to 90 s, and an older or orphaned answer is never
 * handed to the step.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { installFakeApi } from "@/test/fake-api";
import {
  church,
  CHURCH_IDS,
  gg2013,
  hymnals,
  hymnListRoute,
  hymnSuggestions,
  scriptureMatches,
} from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { useHymnals, useHymnList, useHymnLists, useScriptureMatches, useSuggestHymns } from "./hymns";
import { keys } from "./keys";

const GRACE = CHURCH_IDS.grace;
const BODY = { service_date_iso: "2026-10-04", occasion: "", exclude_recent: true };

function render<T>(hook: () => T, queryClient: QueryClient = makeQueryClient({ queries: { retry: false } })) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return { ...renderHook(hook, { wrapper: Wrapper }), queryClient };
}

/** A route that answers only when `release` is called. */
function held(answer: unknown) {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  return {
    handler: async () => {
      await gate;
      return answer;
    },
    release: () => release(),
  };
}

describe("hymn queries (S Queries)", () => {
  it("loads the hymnals and one hymnal's whole list for a service date, as the church", async () => {
    const api = installFakeApi({ "GET /hymnals": hymnals(), "GET /hymns": hymnListRoute() });
    const { result, queryClient } = render(() => ({ hymnals: useHymnals(), list: useHymnList("GG2013", "2026-10-04") }));
    await waitFor(() => expect(result.current.list.isSuccess && result.current.hymnals.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path).sort()).toEqual([
      "/hymnals",
      "/hymns?hymnal=GG2013&limit=2000&recent_for_date=2026-10-04",
    ]);
    expect(api.requests.every((r) => r.headers["X-Church-Id"] === GRACE)).toBe(true);
    expect(result.current.list.data).toEqual(gg2013());
    expect(queryClient.getQueryData(keys.hymnals(GRACE))).toEqual(hymnals());
    const listKey = keys.hymns(GRACE, { hymnal: "GG2013", limit: 2000, recent_for_date: "2026-10-04" });
    expect(queryClient.getQueryData(listKey)).toMatchObject({ total: gg2013().length });
  });

  it("sends no recent_for_date without a valid date, and nothing without a hymnal", async () => {
    const api = installFakeApi({ "GET /hymns": hymnListRoute() });
    const none = render(() => useHymnList(null, "2026-10-04"));
    expect(none.result.current.fetchStatus).toBe("idle");
    const { result } = render(() => useHymnList("GG2013", null));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path)).toEqual(["/hymns?hymnal=GG2013&limit=2000"]);
  });

  it("useHymnLists loads each distinct hymnal once, at most four, sharing the single list's cache", async () => {
    const api = installFakeApi({ "GET /hymns": hymnListRoute({ GG2013: gg2013(), PH1990: [], A: [], B: [], C: [] }) });
    const { result } = render(() => ({
      lists: useHymnLists(["GG2013", "PH1990", null, "GG2013", "A", "B", "C"], "2026-10-04"),
      single: useHymnList("GG2013", "2026-10-04"),
    }));
    await waitFor(() => expect([...result.current.lists.lists.values()].every((l) => l !== undefined)).toBe(true));
    expect([...result.current.lists.lists.keys()]).toEqual(["GG2013", "PH1990", "A", "B"]);
    expect(api.requests.filter((r) => r.path.includes("hymnal=GG2013"))).toHaveLength(1);
    expect(result.current.single.data).toEqual(result.current.lists.lists.get("GG2013"));
    expect(result.current.lists.failed.size).toBe(0);
  });

  it("posts the scripture matches with 30 results, keyed under the hymns prefix, and not without references", async () => {
    const api = installFakeApi({ "POST /hymns/scripture-matches": scriptureMatches() });
    const idle = render(() => useScriptureMatches({ refs: [], hymnal: "GG2013", recentForDate: null, enabled: true }));
    expect(idle.result.current.fetchStatus).toBe("idle");
    const params = { refs: ["Isaiah 5:1-7"], hymnal: "GG2013", recentForDate: "2026-10-04", enabled: true };
    const { result, queryClient } = render(() => useScriptureMatches(params));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests).toHaveLength(1);
    expect(api.requests[0].body).toEqual({
      refs: ["Isaiah 5:1-7"],
      hymnal: "GG2013",
      recent_for_date: "2026-10-04",
      max_results: 30,
    });
    expect(api.requests[0].headers["X-Church-Id"]).toBe(GRACE);
    const key = keys.hymnMatches(GRACE, { refs: ["Isaiah 5:1-7"], hymnal: "GG2013", recent_for_date: "2026-10-04" });
    expect(key.slice(0, 3)).toEqual(["church", GRACE, "hymns"]);
    expect(queryClient.getQueryData(key)).toEqual(scriptureMatches());
  });

  it("posts a suggestion as the church with a 90-second timeout; Cancel's signal ends it as aborted", async () => {
    const answer = hymnSuggestions({ opening: [], response: [], closing: [] });
    const api = installFakeApi({ "POST /hymns/suggestions": answer });
    const { result } = render(() => useSuggestHymns());
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.suggest(BODY, new AbortController().signal);
    });
    expect(outcome).toEqual({ status: "ok", data: answer });
    expect(api.requests[0].body).toEqual(BODY);
    expect(api.requests[0].headers["X-Church-Id"]).toBe(GRACE);
    const cancelled = new AbortController();
    cancelled.abort();
    await act(async () => {
      outcome = await result.current.suggest(BODY, cancelled.signal);
    });
    expect(outcome).toMatchObject({ status: "error", error: { code: "aborted" } });
    expect(timeoutFor("POST", "/hymns/suggestions")).toBe(90_000);
    expect(timeoutFor("GET", "/hymns?hymnal=GG2013")).toBe(20_000);
  });

  it("never hands over an older answer after a newer request, or any answer after the step unmounts", async () => {
    const first = held(hymnSuggestions({ opening: gg2013().slice(0, 1), response: [], closing: [] }));
    const second = hymnSuggestions({ opening: gg2013().slice(2, 3), response: [], closing: [] });
    const api = installFakeApi({ "POST /hymns/suggestions": first.handler });
    const { result, unmount } = render(() => useSuggestHymns());
    let older!: Promise<unknown>;
    act(() => {
      older = result.current.suggest(BODY);
    });
    await waitFor(() => expect(result.current.isPending).toBe(true));
    api.set("POST /hymns/suggestions", second);
    let newer: unknown;
    await act(async () => {
      newer = await result.current.suggest(BODY);
    });
    expect(newer).toEqual({ status: "ok", data: second });
    first.release();
    await act(async () => {
      expect(await older).toEqual({ status: "superseded" });
    });

    const late = held(second);
    api.set("POST /hymns/suggestions", late.handler);
    let orphan!: Promise<unknown>;
    act(() => {
      orphan = result.current.suggest(BODY);
    });
    await waitFor(() => expect(api.requests).toHaveLength(3));
    unmount();
    late.release();
    expect(await orphan).toEqual({ status: "superseded" });
  });
});
''', encoding="utf-8")

edit("frontend/src/lib/queries/keys.test.ts", [
    ('''      keys.hymns(id, { q: "grace" }),
      keys.hymnals(id),
''',
     '''      keys.hymns(id, { q: "grace" }),
      keys.hymnMatches(id, { refs: ["Mark 1"] }),
      keys.hymnals(id),
'''),
    ('''      ["hymns", { q: "grace" }],
      ["hymnals"],
''',
     '''      ["hymns", { q: "grace" }],
      ["hymns", "matches", { refs: ["Mark 1"] }],
      ["hymnals"],
'''),
])

edit("frontend/src/test/fixtures/index.ts", [
    ('''  Hymn,
  Hymnals,
  InviteAccepted,
''',
     '''  Hymn,
  HymnMatch,
  Hymnals,
  HymnPage,
  HymnSuggestions,
  InviteAccepted,
'''),
    ('''  Lectionary,
  SuggestedHymn,
''',
     '''  Lectionary,
  ScriptureMatches,
  SuggestedHymn,
'''),
])
with open("frontend/src/test/fixtures/index.ts", "a", encoding="utf-8") as f:
    f.write('''
/**
 * Grace's GG2013 list as `GET /hymns?hymnal=GG2013&limit=2000` returns it, in
 * hymnal order: #403 (`hymn()`), two hymns with the same title, one newer than
 * the church prefers (#710, written 1981), one with no number (last), one
 * with a link that is not https (#650), and one with a blank title (never listed).
 */
export function gg2013(): Hymn[] {
  return [
    hymn({ number: 1, title: "Holy, Holy, Holy! Lord God Almighty", scripture_refs: "Revelation 4:8-11", text_year: 1826 }),
    hymn({ number: 35, title: "Praise, My Soul, the King of Heaven", link: null, scripture_refs: "Psalm 103", text_year: 1834 }),
    hymn(),
    hymn({ number: 649, title: "Amazing Grace", scripture_refs: "Ephesians 2:8", text_year: 1779 }),
    hymn({ number: 650, title: "Amazing Grace", link: "http://hymnary.org/text/amazing_grace", text_year: 1779 }),
    hymn({ number: 700, title: "Great Is Thy Faithfulness", scripture_refs: "Lamentations 3:22-23", text_year: 1923 }),
    hymn({ number: 710, title: "Here I Am, Lord", scripture_refs: "Isaiah 6:8", text_year: 1981, newer_than_preferred: true }),
    hymn({ number: 800, title: " " }),
    hymn({ id: hymnId(9999), number: null, title: "Sent Forth by God's Blessing", link: null, text_year: 1964 }),
  ];
}

/** Grace's PH1990 list: no scripture references, as in production's PH1990. */
export function ph1990(): Hymn[] {
  return [
    hymn({ id: hymnId(10_001), hymnal: "PH1990", number: 1, title: "Come, Thou Long-Expected Jesus", link: null }),
    hymn({ id: hymnId(10_276), hymnal: "PH1990", number: 276, title: "Great Is Thy Faithfulness", link: null }),
  ];
}

/** `GET /hymnals` with GG2013 and PH1990 (605 hymns, none with scripture references). */
export function twoHymnals(): Hymnals {
  return hymnals({
    items: [
      { code: "GG2013", hymn_count: 853, scripture_ref_count: 795 },
      { code: "PH1990", hymn_count: 605, scripture_ref_count: 0 },
    ],
  });
}

/**
 * A fake-API handler for `GET /hymns`: each hymnal's list from `lists`, and,
 * when `recent_for_date` is sent, `recent_use_on` from `recent` (title → date).
 */
export function hymnListRoute(
  lists: Record<string, Hymn[]> = { GG2013: gg2013(), PH1990: ph1990() },
  recent: Record<string, string> = {},
) {
  return (req: { path: string }): HymnPage => {
    const query = new URL(req.path, "http://localhost").searchParams;
    const dated = query.get("recent_for_date") !== null;
    const items = (lists[query.get("hymnal") ?? ""] ?? []).map((h) => ({
      ...h,
      recent_use_on: dated ? (recent[h.title] ?? null) : null,
    }));
    return { items, total: items.length, limit: Number(query.get("limit") ?? 50), offset: 0 };
  };
}

/** A `HymnMatchOut`: a hymn with its strength and the query references it matched. */
export function hymnMatch(h: Hymn, strength: HymnMatch["strength"], matched: string[]): HymnMatch {
  return { ...h, strength, matched_refs: matched };
}

/** `POST /hymns/scripture-matches` for the readings of October 4, 2026, unless overridden. */
export function scriptureMatches(overrides: Partial<ScriptureMatches> = {}): ScriptureMatches {
  const [holy, , come, grace, , , here] = gg2013();
  const items = [
    hymnMatch(here, "passage", ["Isaiah 5:1-7"]),
    hymnMatch(come, "chapter", ["Isaiah 5:1-7"]),
    hymnMatch(holy, "chapter", ["Matthew 21:33-46"]),
    hymnMatch(grace, "chapter", ["Philippians 3:4b-14"]),
  ];
  return {
    hymnal: "GG2013",
    refs_used: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    unparsed_refs: [],
    total_matched: items.length,
    items,
    ...overrides,
  };
}

/** `POST /hymns/suggestions`: each slot's hymns in order, all `source: "ai"`, unless overridden. */
export function hymnSuggestions(
  slots: Record<"opening" | "response" | "closing", Hymn[]>,
  overrides: Partial<HymnSuggestions> = {},
): HymnSuggestions {
  const out = (list: Hymn[]): SuggestedHymn[] => list.map((h) => suggested(h));
  return {
    hymnal: "GG2013",
    nt_ref: "Philippians 3:4b-14",
    nt_text_used: false,
    excluded_recent_count: 0,
    slots: { opening: out(slots.opening), response: out(slots.response), closing: out(slots.closing) },
    ...overrides,
  };
}
''')

print("T6 tests written")
PYEOF
```

**Expected:** `T6 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/queries/hymns.test.tsx src/lib/queries/keys.test.ts 2>&1 | grep -E "^ (FAIL|×)|Error:|TypeError|Tests |Test Files")
```

**Expected:**

```
 FAIL  |dom| src/lib/queries/hymns.test.tsx [ src/lib/queries/hymns.test.tsx ]
Error: Failed to resolve import "./hymns" from "src/lib/queries/hymns.test.tsx". Does the file exist?
 FAIL  |unit| src/lib/queries/keys.test.ts > keys > starts every church-scoped key with ['church', id]
TypeError: keys.hymnMatches is not a function
 Test Files  2 failed (2)
      Tests  1 failed | 1 passed (2)
```

- [ ] **Step 4 (agent): Write the queries, the key, the timeout and the feature switch**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/lib/api/timeouts.ts", [
    ('''  "POST /scripture/passages": 30_000,
};
''',
     '''  "POST /scripture/passages": 30_000,
  // Slice 3 (S API; F §1.8): the server answers within its 75 s deadline.
  "POST /hymns/suggestions": 90_000,
};
'''),
])

Path("frontend/src/lib/features.ts").write_text('''/**
 * Switches for screens that ship in later slices (slice 3 S Interfaces row 6a).
 * The slice that ships a screen flips its switch in the same pull request.
 */

/** Settings → Hymns (slice 6a). Until then the empty-hymnal state names the current app instead of linking. */
export const SETTINGS_HYMNS_READY = false;
''', encoding="utf-8")

Path("frontend/src/lib/queries/hymns.ts").write_text('''/**
 * The Hymns step's queries (S Queries; F §4.4). All church-scoped
 * (`api.church`, so every request carries `X-Church-Id`), keyed under
 * ["church", id, "hymns"] or ["church", id, "hymnals"], with F §4.4's
 * defaults (30 s stale, refetch on focus, one retry for a retryable error).
 */
import { useQueries, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api/client";
import type {
  Hymn,
  Hymnals,
  HymnPage,
  HymnSuggestionBody,
  HymnSuggestions,
  ScriptureMatchBody,
  ScriptureMatches,
} from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { createLatestTracker } from "@/lib/latest";

import { useApi, useChurchMutation, type Api } from "./client";
import { keys } from "./keys";

/** A whole hymnal in one page (the largest has about 1 000 hymns; S API). */
export const HYMN_LIST_LIMIT = 2000;
/** At most this many hymnal lists at once: the selected one plus the picks' (S Queries). */
export const MAX_LISTS = 4;
/** Match results asked for (S Queries). */
export const MATCH_RESULTS = 30;

/** `GET /hymnals`: the church's hymnals, the stored default and the effective one. */
export function useHymnals(): UseQueryResult<Hymnals, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<Hymnals, ApiError>({
    queryKey: keys.hymnals(church.id),
    queryFn: ({ signal }) => api.church<Hymnals>("/hymnals", { signal }),
  });
}

function hymnListQuery(api: Api, churchId: string, hymnal: string, recentForDate: string | null) {
  const params = { hymnal, limit: HYMN_LIST_LIMIT, recent_for_date: recentForDate };
  const search = new URLSearchParams({ hymnal, limit: String(HYMN_LIST_LIMIT) });
  if (recentForDate !== null) search.set("recent_for_date", recentForDate);
  return {
    queryKey: keys.hymns(churchId, params),
    queryFn: ({ signal }: { signal: AbortSignal }) => api.church<HymnPage>(`/hymns?${search}`, { signal }),
    select: (page: HymnPage): Hymn[] => page.items,
  };
}

/**
 * One hymnal's whole list (`GET /hymns?hymnal=…&limit=2000&recent_for_date=…`).
 * No request without a hymnal; `recentForDate` is null when the draft's date
 * is not valid, and is then left out (S Queries).
 */
export function useHymnList(hymnal: string | null, recentForDate: string | null): UseQueryResult<Hymn[], ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery({ ...hymnListQuery(api, church.id, hymnal ?? "", recentForDate), enabled: hymnal !== null });
}

export type HymnLists = {
  /** Each hymnal's list; undefined while it loads or when it failed. */
  lists: Map<string, Hymn[] | undefined>;
  /** The hymnals whose list failed. */
  failed: ReadonlySet<string>;
  /** True while any of them is being fetched (a Retry's spinner). */
  fetching: boolean;
  /** Asks again for every list that failed. */
  retry: () => void;
};

/**
 * Several hymnals' lists (the selected one and every pick's), each distinct
 * non-null code once, at most `MAX_LISTS`, so a pick from another hymnal can
 * show its live title and be checked. The same keys as `useHymnList`, so the
 * two share the cache.
 */
export function useHymnLists(hymnals: readonly (string | null)[], recentForDate: string | null): HymnLists {
  const api = useApi();
  const church = useChurch();
  const codes = [...new Set(hymnals.filter((code): code is string => code !== null))].slice(0, MAX_LISTS);
  const results = useQueries({ queries: codes.map((code) => hymnListQuery(api, church.id, code, recentForDate)) });
  return {
    lists: new Map(codes.map((code, i) => [code, results[i].data] as const)),
    failed: new Set(codes.filter((_, i) => results[i].isError)),
    fetching: results.some((r) => r.isFetching),
    retry: () => {
      for (const r of results) if (r.isError) void r.refetch();
    },
  };
}

export type MatchParams = {
  /** From `buildMatchRefs`, never the raw draft lines. */
  refs: string[];
  /** The selected hymnal. */
  hymnal: string | null;
  recentForDate: string | null;
  /** False for a hymnal with no scripture references. */
  enabled: boolean;
};

/**
 * `POST /hymns/scripture-matches` as a query (S Queries): it runs again
 * whenever the references, the hymnal or the date change; nothing is sent
 * without references or a hymnal, or when `enabled` is false.
 */
export function useScriptureMatches({ refs, hymnal, recentForDate, enabled }: MatchParams): UseQueryResult<ScriptureMatches, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<ScriptureMatches, ApiError>({
    queryKey: keys.hymnMatches(church.id, { refs, hymnal, recent_for_date: recentForDate }),
    queryFn: ({ signal }) => {
      const json: Omit<ScriptureMatchBody, "limit_per_ref"> = { refs, hymnal, recent_for_date: recentForDate, max_results: MATCH_RESULTS };
      return api.church<ScriptureMatches>("/hymns/scripture-matches", { method: "POST", json, signal });
    },
    enabled: enabled && refs.length > 0 && hymnal !== null,
  });
}

export type SuggestOutcome =
  | { status: "ok"; data: HymnSuggestions }
  | { status: "error"; error: ApiError }
  /** A newer request started, the step unmounted or the church changed: apply nothing, show nothing. */
  | { status: "superseded" };

/**
 * `POST /hymns/suggestions` (S "Stale and cross-church protection"): a 90 s
 * timeout (`timeouts.ts`) and the caller's signal (Cancel). Each call is
 * tracked with `createLatestTracker` and records the church it was sent for,
 * so an older answer never overwrites a newer one and no answer reaches a
 * step that unmounted (a church switch remounts it). The caller still checks
 * the draft's date before applying. Nothing is invalidated: it writes nothing.
 */
export function useSuggestHymns(): {
  suggest: (body: HymnSuggestionBody, signal?: AbortSignal) => Promise<SuggestOutcome>;
  isPending: boolean;
} {
  const api = useApi();
  const church = useChurch();
  const [tracker] = useState(createLatestTracker);
  const mounted = useRef(false);
  const currentChurch = useRef(church.id);
  const mutation = useChurchMutation<HymnSuggestions, ApiError, { body: HymnSuggestionBody; signal?: AbortSignal }>({
    mutationFn: ({ body, signal }) =>
      api.church<HymnSuggestions>("/hymns/suggestions", { method: "POST", json: body, signal }),
  });
  const { mutateAsync } = mutation;

  useEffect(() => {
    currentChurch.current = church.id;
  }, [church.id]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const suggest = useCallback(
    async (body: HymnSuggestionBody, signal?: AbortSignal): Promise<SuggestOutcome> => {
      const isLatest = tracker.begin();
      const sentFor = church.id;
      const current = () => mounted.current && isLatest() && currentChurch.current === sentFor;
      try {
        const data = await mutateAsync({ body, signal });
        return current() ? { status: "ok", data } : { status: "superseded" };
      } catch (e) {
        if (!current()) return { status: "superseded" };
        const error = e instanceof ApiError ? e : new ApiError(0, "unknown", "Something went wrong.");
        return { status: "error", error };
      }
    },
    [tracker, church.id, mutateAsync],
  );

  return { suggest, isPending: mutation.isPending };
}
''', encoding="utf-8")

edit("frontend/src/lib/queries/keys.ts", [
    ('''  hymns: (id: string, params: object) => ["church", id, "hymns", params] as const,
  hymnals: (id: string) => ["church", id, "hymnals"] as const,
''',
     '''  hymns: (id: string, params: object) => ["church", id, "hymns", params] as const,
  /** Under the hymns prefix, so a hymn change (6a) refreshes the matches too (slice 3 S Queries). */
  hymnMatches: (id: string, params: object) => ["church", id, "hymns", "matches", params] as const,
  hymnals: (id: string) => ["church", id, "hymnals"] as const,
'''),
])

print("T6 code written")
PYEOF
```

**Expected:** `T6 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/queries/hymns.test.tsx src/lib/queries/keys.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  2 passed (2)`, `      Tests  8 passed (8)`; ` Test Files  61 passed (61)`, `      Tests  388 passed (388)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `keys.ts`, `keys.test.ts`, `timeouts.ts` and `fixtures/index.ts`, `??` for `hymns.ts`, `hymns.test.tsx` and `features.ts`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/queries/hymns.ts frontend/src/lib/queries/hymns.test.tsx frontend/src/lib/queries/keys.ts frontend/src/lib/queries/keys.test.ts frontend/src/lib/api/timeouts.ts frontend/src/lib/features.ts frontend/src/test/fixtures/index.ts
git commit -m "Queries: hymnals, hymn lists, scripture matches and suggestions, church-scoped (S Queries; F §4.4, §1.8)" -m "useHymnals, useHymnList and useHymnLists (one key shape, so the selected
hymnal and the picks' hymnals share the cache, at most four lists),
useScriptureMatches (a query under the hymns prefix, 30 results) and
useSuggestHymns, whose suggest() resolves ok, error or superseded: a
newer request, an unmounted step or another church drops the answer.
POST /hymns/suggestions gets 90 s; SETTINGS_HYMNS_READY is false until
6a. Fixtures for the step's tests. Frontend 382 -> 388 tests in 61 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 7 files changed. The controller reviews it and backs the branch up.

### Task 7: The Base UI switch and the generic long-list SearchCombobox (F §4.9 items 1 and 5; S Frontend changes "Files"; clarifications 3, 4)

The toolbar's Exclude toggle is a Base UI `Switch`, which the kit does not have yet, and the hymn picker needs the generic long-list component F §4.9 item 5 describes. S expected slice 1 to have built `SearchCombobox` under `TimezoneCombobox`; slice 1 used the Combobox directly, so this task creates `components/app/search-combobox.tsx` and leaves `TimezoneCombobox` alone (clarification 3). The caller ranks and caps the rows (`search`), so the list shows exactly the caller's order, Base UI renders only the rows it is given (`filteredItems`) and handles focus, highlight and the keyboard, and the footer shows the caller's hints. Escape, or focus leaving the field and its list, calls `onDismiss` ("Change" puts the row back). The registry is blocked from the container, so after trying `shadcn add switch` the task writes `switch.tsx` rebuilt from the upstream source exactly as 2b and 2c did (clarification 4). S also lists `combobox`, `badge` and `alert` as generated here; all three exist already (slice 1 and 2b).

**Files:**
- Create: `frontend/src/components/ui/switch.tsx` (generated, or clarification 4's file), `frontend/src/components/app/search-combobox.tsx`
- Test: `frontend/src/components/app/search-combobox.test.tsx` (new, 4). The switch is exercised by T9.

**Interfaces:**
- Consumes: `@base-ui/react/switch` (installed with `@base-ui/react` 1.8.0), `cn` from `"cn"` (as the other generated files import it), `Combobox`, `ComboboxInput`, `ComboboxContent`, `ComboboxList`, `ComboboxItem` (`components/ui/combobox.tsx`), `Label`.
- Produces:
  - `components/ui/switch.tsx`: `Switch` (Base UI `Switch.Root` props: `checked`, `onCheckedChange`, `disabled`, `id`; renders `role="switch"`, and `aria-disabled` when disabled; `size` `"sm" | "default"`). Later user: T9.
  - `components/app/search-combobox.tsx`: `type SearchResult<T> = {shown: readonly T[]; footer: readonly string[]}`; `SearchCombobox<T>({label, labelHidden?, items, search, itemKey, itemText, renderItem?, value, onValueChange, placeholder?, disabled?, autoFocus?, onDismiss?, id?})`. The input is 44 px (`h-11`) and `text-base md:text-sm` (the generated `ComboboxInput`); each row is 44 px below `md`. Later user: T8.

Counts after this task: frontend **392 passed in 62 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/ui/ | tr '\n' ' '; echo
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `alert-dialog.tsx alert.tsx avatar.tsx badge.tsx button.test.tsx button.tsx card.tsx collapsible.tsx combobox.tsx dropdown-menu.tsx input-group.tsx input.tsx label.tsx radio-group.tsx select.tsx sheet.tsx skeleton.tsx sonner.tsx tabs.tsx textarea.tsx tooltip.tsx` (no `switch.tsx`); ` Test Files  61 passed (61)`, `      Tests  388 passed (388)`.

- [ ] **Step 2 (agent): Write the failing test**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


Path("frontend/src/components/app/search-combobox.test.tsx").write_text('''/**
 * `SearchCombobox` (F §4.9 item 5; slice 3 S Testing
 * `components/app/search-combobox.test.tsx`): opens on click, shows the
 * caller's results and hints, selects with the keyboard, and gives the row
 * back on Escape or when focus leaves.
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { SearchCombobox, type SearchResult } from "./search-combobox";

type Item = { id: string; name: string };

const ITEMS: Item[] = Array.from({ length: 70 }, (_, i) => ({ id: `i${i}`, name: `Item ${String(i).padStart(2, "0")}` }));

/** The caller's rules: contains, at most 50, with the hints a hymn picker would give. */
function search(query: string): SearchResult<Item> {
  const q = query.trim().toLowerCase();
  const matches = ITEMS.filter((item) => item.name.toLowerCase().includes(q));
  const footer =
    q === "" ? [`Type to search ${ITEMS.length} items.`]
    : matches.length === 0 ? [`No items match “${query.trim()}”.`]
    : matches.length > 50 ? [`Showing 50 of ${matches.length}.`]
    : [];
  return { shown: matches.slice(0, 50), footer: q === "item 0" ? [...footer, "2 more are hidden."] : footer };
}

function Host({ onChange, onDismiss }: { onChange?: (item: Item) => void; onDismiss?: () => void }) {
  const [value, setValue] = useState<Item | null>(null);
  return (
    <>
      <SearchCombobox
        label="Opening hymn"
        items={ITEMS}
        search={search}
        itemKey={(item) => item.id}
        itemText={(item) => item.name}
        value={value}
        onValueChange={(item) => {
          setValue(item);
          onChange?.(item);
        }}
        placeholder="Search by title or number"
        onDismiss={onDismiss}
      />
      <button type="button">Elsewhere</button>
    </>
  );
}

describe("SearchCombobox", () => {
  it("opens on click and shows at most the caller's 50 with its hint", async () => {
    const user = userEvent.setup();
    render(<Host />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    expect(input).toHaveAttribute("placeholder", "Search by title or number");
    expect(screen.queryByRole("listbox")).toBeNull();
    await user.click(input);
    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option")).toHaveLength(50);
    expect(screen.getByText("Type to search 70 items.")).toBeInTheDocument();
  });

  it("shows the caller's order and footers: no match, and hidden ones", async () => {
    const user = userEvent.setup();
    render(<Host />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 0");
    const listbox = await screen.findByRole("listbox");
    expect(within(listbox).getAllByRole("option").map((o) => o.textContent)).toEqual(ITEMS.slice(0, 10).map((i) => i.name));
    expect(screen.getByText("2 more are hidden.")).toBeInTheDocument();
    await user.clear(input);
    await user.type(input, "zzz");
    expect(screen.queryByRole("option")).toBeNull();
    expect(screen.getByText("No items match “zzz”.")).toBeInTheDocument();
  });

  it("selects with the keyboard and shows the chosen item's text", async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onChange={onChange} />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 42");
    await screen.findByRole("option", { name: "Item 42" });
    await user.keyboard("{ArrowDown}{Enter}");
    expect(onChange).toHaveBeenCalledTimes(1);
    expect(onChange).toHaveBeenCalledWith({ id: "i42", name: "Item 42" });
    expect(input).toHaveValue("Item 42");
  });

  it("calls onDismiss on Escape and when focus leaves, but not when an option is clicked", async () => {
    const onDismiss = vi.fn();
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Host onDismiss={onDismiss} onChange={onChange} />);
    const input = screen.getByRole("combobox", { name: "Opening hymn" });
    await user.type(input, "item 07");
    await user.click(await screen.findByRole("option", { name: "Item 07" }));
    expect(onChange).toHaveBeenCalledWith({ id: "i7", name: "Item 07" });
    expect(onDismiss).not.toHaveBeenCalled();
    await user.click(input);
    await user.keyboard("{Escape}");
    expect(onDismiss).toHaveBeenCalledTimes(1);
    await user.click(input);
    // While the list is open the rest of the page is hidden from the accessibility tree, so find it by text.
    await user.click(screen.getByText("Elsewhere"));
    expect(onDismiss).toHaveBeenCalledTimes(2);
  });
});
''', encoding="utf-8")

print("T7 tests written")
PYEOF
```

**Expected:** `T7 tests written`.

- [ ] **Step 3 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/components/app/search-combobox.test.tsx 2>&1 | grep -E "^ (FAIL|×)|Error:|Tests |Test Files")
```

**Expected:**

```
 FAIL  |dom| src/components/app/search-combobox.test.tsx [ src/components/app/search-combobox.test.tsx ]
Error: Failed to resolve import "./search-combobox" from "src/components/app/search-combobox.test.tsx". Does the file exist?
 Test Files  1 failed (1)
      Tests  no tests
```

- [ ] **Step 4 (agent): Try to generate the switch (network)**

```bash
(cd frontend && timeout 120 npx shadcn@latest add switch < /dev/null 2>&1 | tail -8)
git status --short
```

`< /dev/null` means no prompt can wait for input. Never pass `--overwrite` (F §4.9 item 1).
- **It works** (the CLI lists `src/components/ui/switch.tsx` as created and `git status` shows that one new file besides the test; revert any change to an existing file with `git checkout -- <file>`): Step 5's script must then not write `switch.tsx`, so delete its `Path("frontend/src/components/ui/switch.tsx").write_text(...)` statement before running it, and note "generated" for the commit.
- **Network failure** (expected: this container cannot reach ui.shadcn.com; 2b's and 2c's attempts printed `Request to https://ui.shadcn.com/r/styles/base-nova/….json failed, reason: Request was cancelled.` and changed no file): run Step 5 as written.
- **Anything else** (the registry answers that the item does not exist, or the CLI changes other files): stop and ask the controller.

- [ ] **Step 5 (agent, clarification 4): Write the switch and SearchCombobox**

Provenance of `switch.tsx`: at shadcn-ui/ui commit `db2db460a26fa84fb65c8d903b213925fbdee9ed` (the commit 2b and 2c pinned), the plan's writer fetched `apps/v4/registry/bases/base/ui/switch.tsx` (sha256 `87aaf20b3209fabbcf0a9520c8b34733ddf2c91524c80ec72ed3dd3684f1bca3`) and `apps/v4/registry/styles/style-nova.css` (sha256 `5d5751579c015b61e77cf0822862a43ac79f3e6fed236a17624be8e6d1ebea1d`) from raw.githubusercontent.com, ran the file through the installed shadcn 4.21.0 CLI's `createStyleMap` and `transformStyle`, and formatted it with Prettier 3 and `prettier-plugin-tailwindcss` (`semi: false`, `trailingComma: "es5"`, `tailwindFunctions: ["cn", "cva"]`, `tailwindStylesheet: src/app/globals.css`), the pipeline that reproduces 2c's `collapsible.tsx` exactly after its header comment. The only change from that output is the header comment. Optional check that the upstream file is unchanged (skip it if the host is unreachable; the code below is the record):

```bash
curl -fsS "https://raw.githubusercontent.com/shadcn-ui/ui/db2db460a26fa84fb65c8d903b213925fbdee9ed/apps/v4/registry/bases/base/ui/switch.tsx" | sha256sum | cut -c1-64
```

**Expected:** `87aaf20b3209fabbcf0a9520c8b34733ddf2c91524c80ec72ed3dd3684f1bca3`.

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


Path("frontend/src/components/app/search-combobox.tsx").write_text('''"use client";

import { useId, useState, type ReactNode } from "react";

import {
  Combobox,
  ComboboxContent,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
} from "@/components/ui/combobox";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export type SearchResult<T> = {
  /** What the list shows for the query, best first (the caller caps it, F §4.9 item 5). */
  shown: readonly T[];
  /** Hint lines under the list ("Type to search 853 hymns.", "No hymns match …"). */
  footer: readonly string[];
};

export type SearchComboboxProps<T> = {
  label: string;
  /** Hide the label visually (a card heading already names the field); it stays the input's name. */
  labelHidden?: boolean;
  /** Every item; `search` picks what shows. */
  items: readonly T[];
  search: (query: string) => SearchResult<T>;
  itemKey: (item: T) => string;
  /** The text for the input once an item is chosen, and the option's name. */
  itemText: (item: T) => string;
  /** The option's content; defaults to `itemText`. */
  renderItem?: (item: T) => ReactNode;
  value: T | null;
  onValueChange: (item: T) => void;
  placeholder?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  /** Escape, or focus leaving the field and its list ("Change" puts the row back). */
  onDismiss?: () => void;
  id?: string;
};

/**
 * A searchable long list (F §4.9 item 5; slice 3's hymn picker). The caller
 * filters and ranks (`search`), so the list shows exactly its order; Base UI
 * only renders the items it is given (`filteredItems`) and handles focus,
 * highlight and keyboard selection. The footer holds the caller's hints.
 */
export function SearchCombobox<T>({
  label,
  labelHidden = false,
  items,
  search,
  itemKey,
  itemText,
  renderItem,
  value,
  onValueChange,
  placeholder,
  disabled = false,
  autoFocus = false,
  onDismiss,
  id,
}: SearchComboboxProps<T>) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  // What the user has typed since the list opened ("" = nothing yet).
  const [query, setQuery] = useState("");
  const result = search(query);

  return (
    <div className="grid gap-1.5">
      <Label htmlFor={inputId} className={cn(labelHidden && "sr-only")}>
        {label}
      </Label>
      <Combobox
        items={items}
        filteredItems={result.shown}
        itemToStringLabel={itemText}
        isItemEqualToValue={(a: T, b: T) => itemKey(a) === itemKey(b)}
        value={value}
        onValueChange={(next) => {
          if (next !== null) onValueChange(next as T);
        }}
        onInputValueChange={(next, details) => setQuery(details.reason === "input-change" ? next : "")}
        onOpenChange={(open) => {
          if (!open) setQuery("");
        }}
        disabled={disabled}
      >
        <ComboboxInput
          id={inputId}
          placeholder={placeholder}
          disabled={disabled}
          autoFocus={autoFocus}
          className="h-11 w-full *:data-[slot=input-group-control]:h-full"
          onKeyDown={(event) => {
            if (event.key === "Escape") onDismiss?.();
          }}
          onBlur={(event) => {
            const next = event.relatedTarget;
            const inList = next instanceof Element && next.closest("[data-slot=combobox-content]") !== null;
            if (!inList) onDismiss?.();
          }}
        />
        <ComboboxContent>
          <ComboboxList>
            {(item: T) => (
              <ComboboxItem key={itemKey(item)} value={item} className="min-h-11 md:min-h-8">
                {renderItem ? renderItem(item) : itemText(item)}
              </ComboboxItem>
            )}
          </ComboboxList>
          {result.footer.length > 0 ? (
            <div className="grid gap-0.5 border-t px-2 py-1.5 text-xs text-muted-foreground">
              {result.footer.map((line) => (
                <p key={line}>{line}</p>
              ))}
            </div>
          ) : null}
        </ComboboxContent>
      </Combobox>
    </div>
  );
}
''', encoding="utf-8")

Path("frontend/src/components/ui/switch.tsx").write_text('''"use client"

// Rebuilt from the upstream shadcn source (slice 3b plan clarification 4, as
// slices 2b and 2c did): shadcn-ui/ui@db2db460
// apps/v4/registry/bases/base/ui/switch.tsx with
// apps/v4/registry/styles/style-nova.css, through the shadcn 4.21.0 CLI's own
// style transform and Prettier's Tailwind class order. The only change from
// that output is this comment. Replace it with the file
// `npx shadcn@latest add switch` generates when the registry is reachable.

import { Switch as SwitchPrimitive } from "@base-ui/react/switch"
import { cn } from "cn"

function Switch({
  className,
  size = "default",
  ...props
}: SwitchPrimitive.Root.Props & {
  size?: "sm" | "default"
}) {
  return (
    <SwitchPrimitive.Root
      data-slot="switch"
      data-size={size}
      className={cn(
        "peer group/switch relative inline-flex shrink-0 items-center rounded-full border border-transparent transition-all outline-none group-has-[:focus-visible]/field-label:border-transparent group-has-[:focus-visible]/field-label:ring-0 after:absolute after:-inset-x-3 after:-inset-y-2 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 data-[size=default]:h-[18.4px] data-[size=default]:w-[32px] data-[size=sm]:h-[14px] data-[size=sm]:w-[24px] dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 data-checked:bg-primary data-unchecked:bg-input dark:data-unchecked:bg-input/80 data-disabled:cursor-not-allowed data-disabled:opacity-50",
        className
      )}
      {...props}
    >
      <SwitchPrimitive.Thumb
        data-slot="switch-thumb"
        className="pointer-events-none block rounded-full bg-background ring-0 transition-transform group-data-[size=default]/switch:size-4 group-data-[size=sm]/switch:size-3 group-data-[size=default]/switch:data-checked:translate-x-[calc(100%-2px)] group-data-[size=sm]/switch:data-checked:translate-x-[calc(100%-2px)] dark:data-checked:bg-primary-foreground group-data-[size=default]/switch:data-unchecked:translate-x-0 group-data-[size=sm]/switch:data-unchecked:translate-x-0 dark:data-unchecked:bg-foreground"
      />
    </SwitchPrimitive.Root>
  )
}

export { Switch }
''', encoding="utf-8")

print("T7 code written")
PYEOF
```

**Expected:** `T7 code written`.

- [ ] **Step 6 (agent): Run the test, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/app/search-combobox.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  1 passed (1)`, `      Tests  4 passed (4)`; ` Test Files  62 passed (62)`, `      Tests  392 passed (392)`; `> tsc --noEmit` and `> eslint` with nothing after them; three `??` files.

- [ ] **Step 7 (agent): Commit**

```bash
git add frontend/src/components/ui/switch.tsx frontend/src/components/app/search-combobox.tsx frontend/src/components/app/search-combobox.test.tsx
git commit -m "UI: the Base UI switch and the generic long-list SearchCombobox (F §4.9 items 1, 5; S Frontend changes)" -m "SearchCombobox renders the caller's ranked rows (at most what the caller
passes, F §4.9 item 5) with the caller's hints in the footer; Base UI
handles focus, highlight and the keyboard; Escape or focus leaving calls
onDismiss. switch.tsx is rebuilt from the upstream shadcn source
(base-nova, pinned commit) because the build container cannot reach the
registry (plan clarification 4). Frontend 388 -> 392 tests in 62 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

If Step 4 generated the switch, replace the sentence about the rebuild with "switch.tsx is generated from the base-nova registry." **Expected:** one commit, 3 files changed.

**Review checkpoint (T6-T7, batch 3):** every hook uses `api.church` and a key under `["church", id, …]`; `useSuggestHymns` never resolves `ok` for an older or orphaned call, and turns every failure into a value; `switch.tsx` differs from the upstream output only in its header; `SearchCombobox` holds no hymn logic.

### Task 8: The step: slot cards, the picker and the hymn label, with the loading, empty and error states (S Slot cards, Picker, "Newer-hymn year label", Whole-step states, "Undo toasts never outlive the step"; F §4.8; AC13, AC14, AC20; clarifications 7, 11, 13, 14, 15)

The first screen of the step, rendered by the tests inside the real builder layout (the route still shows the placeholder until T12). `HymnsStep` shows the heading and its line, then the three slot cards from the draft's snapshot at once. It asks for `GET /hymnals`, resolves the selected hymnal with `selectHymnal` (never writing it back), and then asks for the selected hymnal's list and each pick's hymnal's list (clarification 7). A card with a pick shows `HymnLabel` (the live hymn once its list has loaded, the snapshot until then; a rename never touches the draft), the ▶ Listen link for an https page only, ✕ and **Change**, which puts the focused picker in the row until Escape or focus leaves. An empty card shows `HymnPicker`: `SearchCombobox` over the selected list, ranked by `filterHymns`, with S's footer hints, "Loading hymnal…" while the list loads, and a recent-use badge on rows when Exclude is off. Under a pick sit the notices: recent use (only with a valid date), "Not in your hymnal. Choose a replacement." for a pick whose id is null or gone, and "Also chosen as…". ✕ clears the slot and shows "Removed {title}." with **Undo** through `useUndoToasts`, which dismisses every toast it showed when the step unmounts and ignores an Undo from another church (clarification 15). A failed `GET /hymnals` or selected list shows "Couldn't load this church's hymnal." with **Retry** in place of the pickers, never the empty state; a church with no hymnals shows the empty state, asks for no list, and marks each existing pick "Not in your hymnal". The Hymnary credit closes the step. The toolbar comes in T9, Suggest and the ideas in T10, the matches in T11.

**Files:**
- Create: `frontend/src/components/builder/hymns/hymns-step.tsx`, `hymn-slot-card.tsx`, `hymn-picker.tsx`, `hymn-label.tsx`, `use-undo-toasts.ts`
- Test: `frontend/src/components/builder/hymns/hymn-label.test.tsx` (new, 2), `frontend/src/components/builder/hymns/hymns-step.test.tsx` (new, 9)

**Interfaces:**
- Consumes: `useHymnals`, `useHymnLists` (T6); `SearchCombobox` (T7); `selectHymnal`, `pickFromHymn`, `setSlot`, `clearSlot`, `reconcilePick`, `duplicateSlots` (T4); `filterHymns`, `PICKER_LIMIT`, `SLOT_META`, `MISSING_NOTICE`, `hymnText`, `recentUseLabel`, `recentUseNotice`, `duplicateNotice`, `newerYearLabel` (T5); `SETTINGS_HYMNS_READY` (T6); `useDraft`, `EmptyState`, `ErrorState`, `Badge`, `Button`, `buttonVariants`, `safeHttpsUrl`, sonner's `toast`.
- Produces:
  - `HymnsStep()` (grows in T9-T11). Later users: T9-T12.
  - `HymnSlotCard({slot, pick, reconciled, list, pickerAvailable, excludeRecent, serviceDateIso, showHymnal, onChoose, onRemove, notices, children?})`: a `section` named by its title ("Opening hymn"); `children` go under the notices (T10's ideas).
  - `HymnPicker({label, list, excludeRecent, serviceDateIso, showHymnal, onChoose, autoFocus?, onDismiss?})` and `pickerSearch(items, query, excludeRecent): SearchResult<Hymn>`.
  - `HymnLabel({hymn: LabelHymn, showHymnal?, recentBadge?, listen?, truncate?})`: the title then badges that never shrink (hymnal, recent use, "Written {year}"), then the Listen link; `type LabelHymn` (a live `Hymn` or a draft `HymnPick`). Later users: T10, T11.
  - `useUndoToasts(): (message, undo) => void`. Later user: T11.

Counts after this task: frontend **403 passed in 64 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/builder/hymns 2>&1 | head -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/components/builder/hymns': No such file or directory`; ` Test Files  62 passed (62)`, `      Tests  392 passed (392)`.

- [ ] **Step 2 (agent): Write the failing tests**

The step tests render `<HymnsStep />` inside the real `BuilderLayout` with a `<Toaster />`, against the fake API (`GET /church`, `GET /lectionary/readings` answering "no readings", `GET /hymnals`, and `GET /hymns` with Grace's recent use around October 4, 2026: "Great Is Thy Faithfulness" sung September 6, "Praise, My Soul, the King of Heaven" planned October 18). They fake only `Date`. Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/hymn-label.test.tsx").write_text('''/** `HymnLabel` (S "Filled slot", "Newer-hymn year label"; Testing `hymn-label.test.tsx`; AC20). */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { hymn } from "@/test/fixtures";

import { HymnLabel } from "./hymn-label";

describe("HymnLabel", () => {
  it("shows #number and title, the hymnal when asked, and a Listen link only for an https page", () => {
    const { rerender } = render(<HymnLabel hymn={hymn()} showHymnal listen />);
    expect(screen.getByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    expect(screen.getByText("GG2013")).toBeInTheDocument();
    const listen = screen.getByRole("link", { name: "Listen to Come, Thou Almighty King on Hymnary.org" });
    expect(listen).toHaveAttribute("href", "https://hymnary.org/hymn/GG2013/403");
    expect(listen).toHaveAttribute("target", "_blank");
    expect(listen).toHaveAttribute("rel", "noopener noreferrer");
    rerender(<HymnLabel hymn={hymn({ number: null, link: "http://hymnary.org/x" })} listen />);
    expect(screen.getByText("Come, Thou Almighty King")).toBeInTheDocument();
    expect(screen.queryByRole("link")).toBeNull(); // not https: no link
    expect(screen.queryByText("GG2013")).toBeNull();
    rerender(<HymnLabel hymn={hymn({ link: "javascript:alert(1)" })} listen />);
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("adds Written {year} only for a flagged hymn, and at 375 px the title truncates while the badges stay whole", () => {
    const newer = hymn({ title: "Here I Am, Lord", number: 710, text_year: 1981, newer_than_preferred: true });
    const { rerender } = render(<HymnLabel hymn={newer} recentBadge="Used Sep 6" truncate />);
    expect(screen.getByText("#710 Here I Am, Lord")).toHaveClass("truncate", "min-w-0");
    expect(screen.getByText("Written 1981")).toHaveClass("shrink-0");
    expect(screen.getByText("Used Sep 6")).toHaveClass("shrink-0");
    rerender(<HymnLabel hymn={hymn({ text_year: 1757, newer_than_preferred: false })} />);
    expect(screen.queryByText(/^Written/)).toBeNull();
    rerender(<HymnLabel hymn={{ title: "Snapshot", number: 5, hymnal: "GG2013" }} />); // a draft pick has no year
    expect(screen.queryByText(/^Written/)).toBeNull();
  });
});
''', encoding="utf-8")

Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/hymns-step.test.tsx").write_text('''/**
 * The Hymns step (S "User experience", Testing `hymns-step.test.tsx`; F §4.6,
 * §4.8). The step runs inside the real builder layout against the fake API.
 * The clock is Tuesday, September 29, 2026 (only `Date` is faked), so a fresh
 * draft is dated Sunday, October 4, 2026, and the lectionary answers "no
 * readings", so the readings stay as each test seeds them.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import type { ChurchProfile } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import { editOccasion } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type HymnPick } from "@/lib/draft/schema";
import { pickFromHymn } from "@/lib/hymns/picks";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  CHURCH_IDS,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  hymnals,
  hymnListRoute,
  lectionaryRoute,
  me,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { HymnsStep } from "./hymns-step";

const KEY = draftKey(USER_ID, church().id);
const [HOLY, PRAISE, COME, GRACE, , FAITHFUL] = gg2013();
/** Grace's recent use around October 4, 2026: sung September 6, planned October 18. */
const RECENT = { "Great Is Thy Faithfulness": "2026-09-06", "Praise, My Soul, the King of Heaven": "2026-10-18" };

const pick = pickFromHymn;

function draftWith(hymns: Partial<DraftV1["hymns"]> = {}, readings: Partial<DraftV1["readings"]> = {}): DraftV1 {
  return testDraft((d) => ({ ...d, readings: { ...d.readings, ...readings }, hymns: { ...d.hymns, ...hymns } }));
}

function slots(opening: HymnPick | null, response: HymnPick | null = null, closing: HymnPick | null = null) {
  return { slots: { opening, response, closing } };
}

function stored(key = KEY): DraftV1 {
  return JSON.parse(window.localStorage.getItem(key) ?? "null") as DraftV1;
}

/** The step in the builder layout, with a Toaster for toast text; `routes` replace the defaults. */
function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}, extra: ReactNode = null) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(undefined, RECENT),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <HymnsStep />
        {extra}
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/hymns" },
  );
  return { ...view, api };
}

function card(slot: "Opening" | "Response" | "Closing") {
  return screen.getByRole("region", { name: `${slot} hymn` });
}

/** The slot's picker once its hymnal has loaded. */
async function readyPicker(slot: "Opening" | "Response" | "Closing") {
  const input = await within(await screen.findByRole("region", { name: `${slot} hymn` })).findByRole("combobox", {
    name: `${slot} hymn`,
  });
  await waitFor(() => expect(input).toBeEnabled());
  return input;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the Hymns step (S User experience)", () => {
  it("shows the draft's picks before the hymnal loads, with the pickers waiting, then the live hymn", async () => {
    let release!: () => void;
    const loaded = new Promise<void>((resolve) => (release = resolve));
    const listRoute = hymnListRoute(undefined, RECENT);
    const snapshot = { ...pick(COME), title: "Come, Thou Almighty King (old title)" };
    renderStep(draftWith(slots(snapshot)), {
      "GET /hymns": async (req: RecordedRequest) => {
        await loaded;
        return listRoute(req);
      },
    });
    expect(await screen.findByRole("heading", { level: 2, name: "Hymns" })).toBeInTheDocument();
    expect(screen.getByText("Choose an opening, response and closing hymn.")).toBeInTheDocument();
    const opening = card("Opening");
    expect(within(opening).getByText("Gathering / call to worship")).toBeInTheDocument();
    expect(within(opening).getByText("#403 Come, Thou Almighty King (old title)")).toBeInTheDocument();
    const response = within(card("Response")).getByRole("combobox", { name: "Response hymn" });
    expect(response).toBeDisabled();
    expect(response).toHaveAttribute("placeholder", "Loading hymnal…");
    expect(within(card("Response")).getByText("After the sermon — responds to the scripture (NT reading)")).toBeInTheDocument();
    expect(within(card("Closing")).getByText("Joyful / sending")).toBeInTheDocument();
    release();
    // The live title shows; the draft keeps its snapshot (a rename never marks it dirty).
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await waitFor(() => expect(response).toHaveAttribute("placeholder", "Search by title or number"));
    expect(stored().hymns.slots.opening?.title).toBe("Come, Thou Almighty King (old title)");
    expect(within(opening).getByRole("link", { name: "Listen to Come, Thou Almighty King on Hymnary.org" })).toHaveAttribute(
      "href",
      "https://hymnary.org/hymn/GG2013/403",
    );
    expect(
      screen.getByText(
        "Hymn information and links courtesy of Hymnary.org. Individual hymns may carry their own copyright — see each hymn's page.",
      ),
    ).toBeInTheDocument();
  });

  it("writes the chosen hymn to the draft, and every request names the church", async () => {
    const { user, api } = renderStep();
    const input = await readyPicker("Opening");
    await user.type(input, "403");
    await user.click(await screen.findByRole("option", { name: /#403 Come, Thou Almighty King/ }));
    expect(await within(card("Opening")).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.opening).toEqual(pick(COME)));
    const churchCalls = api.requests.filter((r) => !r.path.startsWith("/lectionary"));
    expect(churchCalls.map((r) => r.path)).toEqual(
      expect.arrayContaining(["/church", "/hymnals", "/hymns?hymnal=GG2013&limit=2000&recent_for_date=2026-10-04"]),
    );
    expect(churchCalls.every((r) => r.headers["X-Church-Id"] === church().id)).toBe(true);
  });

  it("shows the empty-hymnal state instead of the pickers; a pick still shows, as not in the hymnal", async () => {
    const { api } = renderStep(draftWith(slots(pick(COME))), { "GET /hymnals": hymnals({ items: [], effective_hymnal: null }) });
    expect(await screen.findByRole("heading", { name: "This church's hymnal is empty" })).toBeInTheDocument();
    expect(screen.getByText("Add hymns in the current app under Settings → Hymns.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Settings/ })).toBeNull(); // Settings → Hymns ships in 6a
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(within(card("Opening")).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    expect(within(card("Opening")).getByText("Not in your hymnal. Choose a replacement.")).toBeInTheDocument();
    expect(api.requests.some((r) => r.path.startsWith("/hymns"))).toBe(false);
  });

  it("shows Couldn't load this church's hymnal with Retry when the list fails, never the empty state", async () => {
    let fail = true;
    const listRoute = hymnListRoute(undefined, RECENT);
    const { user } = renderStep(draftWith(slots(pick(COME))), {
      "GET /hymns": (req: RecordedRequest) => (fail ? fakeError(500, "internal_error", "Something went wrong.") : listRoute(req)),
    });
    expect(await screen.findByText("Couldn't load this church's hymnal.")).toBeInTheDocument();
    expect(screen.queryByText("This church's hymnal is empty")).toBeNull();
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(within(card("Opening")).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument(); // the snapshot stays
    fail = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await readyPicker("Response")).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load this church's hymnal.")).toBeNull();
  });
});

describe("slot cards (S Slot cards, Notices)", () => {
  it("marks a deleted or unresolved pick Not in your hymnal, without crashing or dropping it", async () => {
    const gone = { ...pick(COME), hymn_id: "00000000-0000-4000-8000-000000009998" };
    const archived = { hymn_id: null, title: "Be Thou My Vision", number: 339, hymnal: "GG2013" };
    renderStep(draftWith(slots(gone, archived)));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    expect(await within(opening).findByText("Not in your hymnal. Choose a replacement.")).toBeInTheDocument();
    expect(within(opening).getByText("#403 Come, Thou Almighty King")).toBeInTheDocument(); // the snapshot
    expect(within(card("Response")).getByText("#339 Be Thou My Vision")).toBeInTheDocument();
    expect(within(card("Response")).getByText("Not in your hymnal. Choose a replacement.")).toBeInTheDocument();
    expect(stored().hymns.slots).toEqual(slots(gone, archived).slots);
  });

  it("notes a hymn used before or planned after the service, and the same hymn in two slots", async () => {
    renderStep(draftWith(slots(pick(PRAISE), pick(FAITHFUL), pick(PRAISE))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    expect(
      await within(opening).findByText("Also planned for October 18, 2026 — within 12 weeks of this service."),
    ).toBeInTheDocument();
    expect(within(opening).getByText("Also chosen as the Closing hymn.")).toBeInTheDocument();
    expect(within(card("Closing")).getByText("Also chosen as the Opening hymn.")).toBeInTheDocument();
    expect(
      within(card("Response")).getByText("Used on September 6, 2026 — within 12 weeks of this service."),
    ).toBeInTheDocument();
    expect(within(card("Response")).queryByText(/Also chosen/)).toBeNull();
  });

  it("Change puts a focused picker in the row until Escape; choosing replaces the hymn, and same titles are told apart", async () => {
    const { user } = renderStep(draftWith(slots(pick(COME))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await readyPicker("Response");
    await user.click(within(opening).getByRole("button", { name: "Change" }));
    const input = within(opening).getByRole("combobox", { name: "Opening hymn" });
    await waitFor(() => expect(input).toHaveFocus());
    await user.keyboard("{Escape}");
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    await user.click(within(opening).getByRole("button", { name: "Change" }));
    await user.type(within(opening).getByRole("combobox", { name: "Opening hymn" }), "amazing");
    const options = await screen.findAllByRole("option", { name: /Amazing Grace/ });
    expect(options.map((o) => o.textContent)).toEqual(["#649 Amazing Grace", "#650 Amazing Grace"]);
    await user.click(options[1]);
    expect(await within(opening).findByText("#650 Amazing Grace")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.opening?.number).toBe(650));
    // #650's link is not https, so it has no Listen link.
    expect(within(opening).queryByRole("link")).toBeNull();
  });

  it("✕ removes the hymn with a Removed toast whose Undo puts it back", async () => {
    const { user } = renderStep(draftWith(slots(pick(GRACE))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await user.click(await within(opening).findByRole("button", { name: "Remove Amazing Grace" }));
    expect(within(opening).getByRole("combobox", { name: "Opening hymn" })).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.opening).toBeNull());
    expect(await screen.findByText("Removed Amazing Grace.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" }));
    expect(await within(opening).findByText("#649 Amazing Grace")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.opening).toEqual(pick(GRACE)));
  });

  it("Undo after a church switch: the toast is dismissed and its handler changes no draft", async () => {
    const shown = vi.spyOn(toast, "message");
    const dismissed = vi.spyOn(toast, "dismiss");
    const hope: ChurchProfile = churchProfile({ id: CHURCH_IDS.hope, name: "Hope" });
    const hopeKey = draftKey(USER_ID, hope.id);
    window.localStorage.setItem(KEY, JSON.stringify(draftWith(slots(pick(HOLY)))));
    installFakeApi({
      "GET /church": (req: RecordedRequest) => (req.headers["X-Church-Id"] === hope.id ? hope : churchProfile()),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /hymnals": hymnals(),
      "GET /hymns": hymnListRoute(undefined, RECENT),
    });
    function Typist() {
      const { update } = useDraft();
      return (
        <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest at Hope"))}>
          Type an occasion
        </button>
      );
    }
    const tree = (c: ChurchProfile) => (
      <ChurchProvider key={c.id} value={c}>
        <BuilderLayout>
          <HymnsStep />
          <Typist />
        </BuilderLayout>
      </ChurchProvider>
    );
    const { user, rerender } = renderWithProviders(tree(churchProfile()), { me: me(), path: "/builder/hymns" });
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    await user.click(await within(opening).findByRole("button", { name: "Remove Holy, Holy, Holy! Lord God Almighty" }));
    await waitFor(() => expect(stored().hymns.slots.opening).toBeNull());
    const [, options] = shown.mock.calls[0];
    const undo = (options?.action as unknown as { onClick: () => void }).onClick;
    const id = shown.mock.results[0].value;

    rerender(tree(hope)); // the (church) layout remounts under the other church
    await screen.findByRole("region", { name: "Opening hymn" });
    expect(dismissed).toHaveBeenCalledWith(id);
    act(() => undo());
    // A later write in Hope lands after any write the Undo could have caused (the same 400 ms delay).
    await user.click(screen.getByRole("button", { name: "Type an occasion" }));
    await waitFor(() => expect(stored(hopeKey)?.readings.occasion).toBe("Harvest at Hope"));
    expect(stored(hopeKey).hymns.slots.opening).toBeNull();
    expect(stored().hymns.slots.opening).toBeNull(); // Grace's draft is not written either
  });
});
''', encoding="utf-8")

print("T8 tests written")
PYEOF
```

**Expected:** `T8 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/hymns 2>&1 | grep -E "^ (FAIL|×)|Error:|Tests |Test Files")
```

**Expected:**

```
 FAIL  |dom| src/components/builder/hymns/hymn-label.test.tsx [ src/components/builder/hymns/hymn-label.test.tsx ]
Error: Failed to resolve import "./hymn-label" from "src/components/builder/hymns/hymn-label.test.tsx". Does the file exist?
 FAIL  |dom| src/components/builder/hymns/hymns-step.test.tsx [ src/components/builder/hymns/hymns-step.test.tsx ]
Error: Failed to resolve import "./hymns-step" from "src/components/builder/hymns/hymns-step.test.tsx". Does the file exist?
 Test Files  2 failed (2)
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the step, the card, the picker, the label and the Undo toasts**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/hymn-label.tsx").write_text('''"use client";

import { PlayIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Hymn } from "@/lib/api/types";
import { hymnText, newerYearLabel } from "@/lib/hymns/labels";
import { safeHttpsUrl } from "@/lib/urls";
import { cn } from "@/lib/utils";

/** What a label needs: a live hymn, or a draft snapshot (no link, no year). */
export type LabelHymn = Pick<Hymn, "title" | "number"> & { hymnal: string | null } &
  Partial<Pick<Hymn, "link" | "text_year" | "newer_than_preferred">>;

/**
 * One hymn as the step shows it everywhere (S "Filled slot", "Newer-hymn year
 * label"): "#n Title", then small badges that never shrink (the hymnal when
 * the church has 2+, the recent use, "Written {year}" for a flagged hymn), so
 * at 375 px the title truncates first. With `listen`, a ▶ link to the hymn's
 * Hymnary.org page when the link is https (`safeHttpsUrl`), else none.
 */
export function HymnLabel({
  hymn,
  showHymnal = false,
  recentBadge = null,
  listen = false,
  truncate = false,
}: {
  hymn: LabelHymn;
  showHymnal?: boolean;
  recentBadge?: string | null;
  listen?: boolean;
  truncate?: boolean;
}) {
  const year =
    hymn.newer_than_preferred !== undefined && hymn.text_year !== undefined
      ? newerYearLabel({ newer_than_preferred: hymn.newer_than_preferred, text_year: hymn.text_year })
      : null;
  const href = listen ? safeHttpsUrl(hymn.link) : null;
  return (
    <span className="flex min-w-0 items-center gap-1.5">
      <span className={cn("min-w-0", truncate ? "truncate" : "wrap-anywhere")}>{hymnText(hymn)}</span>
      {showHymnal && hymn.hymnal ? (
        <Badge variant="outline" className="shrink-0">
          {hymn.hymnal}
        </Badge>
      ) : null}
      {recentBadge ? (
        <Badge variant="secondary" className="shrink-0">
          {recentBadge}
        </Badge>
      ) : null}
      {year ? (
        <Badge variant="outline" className="shrink-0 text-muted-foreground">
          {year}
        </Badge>
      ) : null}
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Listen to ${hymn.title} on Hymnary.org`}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:text-foreground md:size-8"
        >
          <PlayIcon aria-hidden="true" className="size-4" />
        </a>
      ) : null}
    </span>
  );
}
''', encoding="utf-8")

Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/hymn-picker.tsx").write_text('''"use client";

import { SearchCombobox, type SearchResult } from "@/components/app/search-combobox";
import type { Hymn } from "@/lib/api/types";
import { filterHymns, PICKER_LIMIT } from "@/lib/hymns/filter";
import { hymnText, recentUseLabel } from "@/lib/hymns/labels";

import { HymnLabel } from "./hymn-label";

/** The picker's rows and the hints in its footer (S Picker "Hints in the list footer"). */
export function pickerSearch(items: readonly Hymn[], query: string, excludeRecent: boolean): SearchResult<Hymn> {
  const result = filterHymns(items, query, { excludeRecent });
  const q = query.trim();
  const footer: string[] = [];
  if (q === "") footer.push(`Type to search ${result.totalMatches} hymns.`);
  else if (result.totalMatches === 0) footer.push(`No hymns match “${q}”.`);
  else if (result.totalMatches > PICKER_LIMIT) {
    footer.push(`Showing ${PICKER_LIMIT} of ${result.totalMatches} — keep typing to narrow.`);
  }
  if (result.hiddenRecent === 1) footer.push("1 more used within 12 weeks is hidden.");
  else if (result.hiddenRecent > 1) footer.push(`${result.hiddenRecent} more used within 12 weeks are hidden.`);
  return { shown: result.shown, footer };
}

/**
 * A slot's hymn picker (S "Picker"): the selected hymnal's list through
 * `SearchCombobox`, ranked by `filterHymns`. Rows show "#n Title", the year
 * badge of a newer hymn and, when Exclude is off, a "Used Sep 7" or "Planned
 * Oct 18" badge. While the list loads the input is disabled with "Loading hymnal…".
 */
export function HymnPicker({
  label,
  list,
  excludeRecent,
  serviceDateIso,
  showHymnal,
  onChoose,
  autoFocus = false,
  onDismiss,
}: {
  label: string;
  /** The selected hymnal's hymns; undefined while they load. */
  list: readonly Hymn[] | undefined;
  excludeRecent: boolean;
  serviceDateIso: string;
  showHymnal: boolean;
  onChoose: (h: Hymn) => void;
  autoFocus?: boolean;
  onDismiss?: () => void;
}) {
  const loading = list === undefined;
  return (
    <SearchCombobox<Hymn>
      label={label}
      labelHidden
      items={list ?? []}
      search={(query) => pickerSearch(list ?? [], query, excludeRecent)}
      itemKey={(h) => h.id}
      itemText={hymnText}
      renderItem={(h) => (
        <HymnLabel
          hymn={h}
          showHymnal={showHymnal}
          recentBadge={!excludeRecent && h.recent_use_on ? recentUseLabel(h.recent_use_on, serviceDateIso) : null}
        />
      )}
      value={null}
      onValueChange={onChoose}
      placeholder={loading ? "Loading hymnal…" : "Search by title or number"}
      disabled={loading}
      autoFocus={autoFocus}
      onDismiss={onDismiss}
    />
  );
}
''', encoding="utf-8")

Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/hymn-slot-card.tsx").write_text('''"use client";

import { InfoIcon, XIcon } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import type { HymnPick, Slot } from "@/lib/draft/schema";
import { SLOT_META } from "@/lib/hymns/labels";
import type { Reconciled } from "@/lib/hymns/picks";

import { HymnLabel } from "./hymn-label";
import { HymnPicker } from "./hymn-picker";

export type SlotCardProps = {
  slot: Slot;
  /** The draft's snapshot. */
  pick: HymnPick | null;
  /** The pick against the loaded lists (`reconcilePick`); the live hymn wins when found. */
  reconciled: Reconciled | null;
  /** The selected hymnal's list for the picker; undefined while it loads. */
  list: readonly Hymn[] | undefined;
  /** False when an error or the empty hymnal replaces the pickers. */
  pickerAvailable: boolean;
  excludeRecent: boolean;
  serviceDateIso: string;
  showHymnal: boolean;
  onChoose: (h: Hymn) => void;
  /** ✕: the step clears the slot and offers Undo. */
  onRemove: () => void;
  /** Under the pick, in muted text; none changes the pick (S "Notices"). */
  notices: readonly string[];
  /** Under the notices: "No suggestion for this slot." and the other ideas (slice 3b T10). */
  children?: ReactNode;
};

/**
 * One slot (S "Slot cards"): its title and caption; a filled slot shows the
 * hymn (live when its list has loaded, the draft's snapshot until then) with
 * its ▶ Listen link, ✕ and Change, which puts the focused picker in the row's
 * place until Escape or focus leaves; an empty slot shows the picker. The
 * notices sit under the pick.
 */
export function HymnSlotCard({
  slot,
  pick,
  reconciled,
  list,
  pickerAvailable,
  excludeRecent,
  serviceDateIso,
  showHymnal,
  onChoose,
  onRemove,
  notices,
  children,
}: SlotCardProps) {
  const meta = SLOT_META[slot];
  const [changing, setChanging] = useState(false);
  const headingId = `slot-${slot}-title`;
  const live = reconciled?.status === "ok" ? reconciled.live : null;
  const picker = (autoFocus: boolean) => (
    <HymnPicker
      label={meta.title}
      list={list}
      excludeRecent={excludeRecent}
      serviceDateIso={serviceDateIso}
      showHymnal={showHymnal}
      autoFocus={autoFocus}
      onDismiss={autoFocus ? () => setChanging(false) : undefined}
      onChoose={(h) => {
        setChanging(false);
        onChoose(h);
      }}
    />
  );

  return (
    <section aria-labelledby={headingId} className="grid gap-3 rounded-lg border p-4">
      <div>
        <h3 id={headingId} className="text-base font-medium">
          {meta.title}
        </h3>
        <p className="text-sm text-muted-foreground">{meta.caption}</p>
      </div>
      {pick === null ? (
        pickerAvailable ? picker(false) : null
      ) : changing && pickerAvailable ? (
        picker(true)
      ) : (
        <div className="grid gap-2">
          <div className="flex min-w-0 items-center gap-1">
            <div className="min-w-0 flex-1 font-medium">
              <HymnLabel hymn={live ?? pick} showHymnal={showHymnal} listen />
            </div>
            <Button
              variant="ghost"
              size="icon-lg"
              className="size-11 shrink-0 md:size-8"
              aria-label={`Remove ${(live ?? pick).title}`}
              onClick={() => onRemove()}
            >
              <XIcon aria-hidden="true" />
            </Button>
          </div>
          {pickerAvailable ? (
            <div>
              <Button variant="outline" size="touch" onClick={() => setChanging(true)}>
                Change
              </Button>
            </div>
          ) : null}
        </div>
      )}
      {notices.length > 0 ? (
        <ul className="grid gap-1 text-sm text-muted-foreground">
          {notices.map((notice) => (
            <li key={notice} className="flex gap-1.5">
              <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span>{notice}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {children}
    </section>
  );
}
''', encoding="utf-8")

Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/hymns-step.tsx").write_text('''"use client";

import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { buttonVariants } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { SLOTS, type Slot } from "@/lib/draft/schema";
import { SETTINGS_HYMNS_READY } from "@/lib/features";
import { selectHymnal } from "@/lib/hymns/hymnal";
import { duplicateNotice, MISSING_NOTICE, recentUseNotice } from "@/lib/hymns/labels";
import { clearSlot, duplicateSlots, pickFromHymn, reconcilePick, setSlot, type Reconciled } from "@/lib/hymns/picks";
import { useHymnals, useHymnLists } from "@/lib/queries/hymns";

import { HymnSlotCard } from "./hymn-slot-card";
import { useUndoToasts } from "./use-undo-toasts";

/** The empty-hymnal state (S "Whole-step states"); the link waits for Settings → Hymns (6a). */
function EmptyHymnal() {
  return (
    <EmptyState
      title="This church's hymnal is empty"
      description={
        SETTINGS_HYMNS_READY
          ? "Add hymns on the Settings → Hymns page to choose hymns here."
          : "Add hymns in the current app under Settings → Hymns."
      }
      action={
        SETTINGS_HYMNS_READY ? (
          <a href="/settings/hymns" className={buttonVariants({ size: "touch" })}>
            Open Settings → Hymns
          </a>
        ) : undefined
      }
    />
  );
}

const MISSING: Reconciled = { status: "missing" };

/**
 * Step 2, Hymns (S "User experience"). It reads and writes only the draft
 * (F §4.6). The slot cards show the draft's picks at once; the pickers wait
 * for `GET /hymnals` and the selected hymnal's list, with no full-page
 * spinner. The selected hymnal is resolved only from a loaded `GET /hymnals`
 * and never written back (S Toolbar). Removing a hymn offers Undo in a toast
 * that never outlives the step.
 */
export function HymnsStep() {
  const { draft, update } = useDraft();
  const hymnalsQuery = useHymnals();
  const hymns = draft.hymns;
  const dateIso = draft.readings.date_iso;
  const dateValid = isValidDateIso(dateIso);
  const recentForDate = dateValid ? dateIso : null;
  const hymnals = hymnalsQuery.data;
  const empty = hymnals !== undefined && hymnals.items.length === 0;
  const selected = hymnals && !empty ? selectHymnal(hymns.hymnal, hymnals) : null;
  const code = selected?.code ?? null;
  // The picks' hymnals too (a pick keeps its own), once GET /hymnals has answered with some.
  const listed = selected === null ? [] : [code, ...SLOTS.map((slot) => hymns.slots[slot]?.hymnal ?? null)];
  const lists = useHymnLists(listed, recentForDate);
  const showUndo = useUndoToasts();

  const selectedList = code === null ? undefined : lists.lists.get(code);
  const failed = hymnalsQuery.isError || (code !== null && lists.failed.has(code));
  const pickers = !failed && !empty;
  const showHymnal = (hymnals?.items.length ?? 0) >= 2;
  const excludeRecent = hymns.exclude_recent && dateValid;
  const duplicates = duplicateSlots(hymns.slots);

  function notices(slot: Slot, reconciled: Reconciled | null): string[] {
    const out: string[] = [];
    if (reconciled?.status === "ok" && dateValid && reconciled.live.recent_use_on) {
      out.push(recentUseNotice(reconciled.live.recent_use_on, dateIso));
    }
    if (reconciled?.status === "missing") out.push(MISSING_NOTICE);
    const duplicate = duplicateNotice(duplicates[slot]);
    if (duplicate) out.push(duplicate);
    return out;
  }

  function choose(slot: Slot, h: Hymn) {
    update((d) => setSlot(d, slot, pickFromHymn(h)));
  }

  function remove(slot: Slot, title: string) {
    const previous = hymns.slots[slot];
    if (!previous) return;
    update((d) => clearSlot(d, slot));
    showUndo(`Removed ${title}.`, () => update((d) => setSlot(d, slot, previous)));
  }

  return (
    <section aria-labelledby="hymns-step-title" className="grid gap-6">
      <div>
        <h2 id="hymns-step-title" className="text-lg font-semibold">
          Hymns
        </h2>
        <p className="text-sm text-muted-foreground">Choose an opening, response and closing hymn.</p>
      </div>
      {failed ? (
        <ErrorState
          error={hymnalsQuery.error}
          message="Couldn't load this church's hymnal."
          retrying={hymnalsQuery.isFetching || lists.fetching}
          onRetry={() => {
            if (hymnalsQuery.isError) void hymnalsQuery.refetch();
            else lists.retry();
          }}
        />
      ) : empty ? (
        <EmptyHymnal />
      ) : null}
      {SLOTS.map((slot) => {
        const pick = hymns.slots[slot];
        const reconciled = pick === null ? null : empty ? MISSING : reconcilePick(pick, lists.lists, code);
        const title = reconciled?.status === "ok" ? reconciled.live.title : (pick?.title ?? "");
        return (
          <HymnSlotCard
            key={slot}
            slot={slot}
            pick={pick}
            reconciled={reconciled}
            notices={notices(slot, reconciled)}
            list={selectedList}
            pickerAvailable={pickers}
            excludeRecent={excludeRecent}
            serviceDateIso={dateIso}
            showHymnal={showHymnal}
            onChoose={(h) => choose(slot, h)}
            onRemove={() => remove(slot, title)}
          />
        );
      })}
      <p className="text-xs text-muted-foreground">
        Hymn information and links courtesy of Hymnary.org. Individual hymns may carry their own copyright — see each
        hymn&apos;s page.
      </p>
    </section>
  );
}
''', encoding="utf-8")

Path("frontend/src/components/builder/hymns").mkdir(parents=True, exist_ok=True)
Path("frontend/src/components/builder/hymns/use-undo-toasts.ts").write_text('''"use client";

import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";

import { useChurch } from "@/lib/church-context";

/**
 * Toasts with Undo that never outlive the step (S "Undo toasts never outlive
 * the step"). Sonner's toasts live outside the `(church)` layout, so a closure
 * over `update` could act after a church switch. Two guards: every toast this
 * step showed is dismissed when it unmounts, and each Undo checks that the step
 * is still mounted for the church it was shown in.
 */
export function useUndoToasts(): (message: string, undo: () => void) => void {
  const church = useChurch();
  const shown = useRef(new Set<string | number>());
  const mounted = useRef(false);
  const currentChurch = useRef(church.id);

  useEffect(() => {
    currentChurch.current = church.id;
  }, [church.id]);

  useEffect(() => {
    const ids = shown.current;
    mounted.current = true;
    return () => {
      mounted.current = false;
      for (const id of ids) toast.dismiss(id);
      ids.clear();
    };
  }, []);

  return useCallback(
    (message: string, undo: () => void) => {
      const captured = church.id;
      const id = toast.message(message, {
        action: {
          label: "Undo",
          onClick: () => {
            if (mounted.current && currentChurch.current === captured) undo();
          },
        },
      });
      shown.current.add(id);
    },
    [church.id],
  );
}
''', encoding="utf-8")

print("T8 code written")
PYEOF
```

**Expected:** `T8 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/hymns 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  2 passed (2)`, `      Tests  11 passed (11)`; ` Test Files  64 passed (64)`, `      Tests  403 passed (403)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; `?? frontend/src/components/builder/hymns/`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/hymns
git commit -m "Hymns: the step's slot cards, picker and hymn label, with loading, empty and error states (S Slot cards, Picker, Whole-step states; AC13, AC14)" -m "HymnsStep shows the three cards from the draft at once; the pickers wait
for GET /hymnals and the selected hymnal's list (Loading hymnal...).
A pick shows its live title, number, Listen link (https only), Written
{year} for a newer hymn, and its notices: recent use, Not in your
hymnal, Also chosen as. Change swaps in a focused picker; the remove
button offers Undo in a toast dismissed when the step unmounts and
ignored after a church switch. A failed load shows Retry, an empty
hymnal the empty state. Frontend 392 -> 403 tests in 64 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 7 files changed.

### Task 9: The toolbar: the hymnal select and the Exclude switch; exclusion never clears a pick (S Toolbar, Behavior changes 3, 11, 19; AC12; owner answer 1; clarifications 2, 7, 13, 22)

`HymnsToolbar` sits between the heading and the cards once `GET /hymnals` has answered (skeletons until then; clarification 7). `HymnalPicker` shows the Base UI `Select` (with an `items` map, F §4.9) only when the church has two or more hymnals, labelled "{code} · {hymn_count} hymns" with S's helper; choosing calls `setHymnal`, which stores `null` for the effective hymnal (owner answer 1, clarification 2), and the picks keep their own hymnal. Its notes show whatever the Select: a stored code the church no longer has ("… Showing {effective} instead.", with nothing written) and a hymnal with no scripture references. `ExcludeSwitch` writes only `exclude_recent`, shows "{n} hymns are hidden." for the selected hymnal's recent hymns when on (clarifications 13, 22), and is disabled with "Pick a valid date in step 1 to check recent use." for an invalid date. The picker already hides recent hymns while it is on (T8); this task's test is the port ledger's "exclusion never clears a pick".

**Files:**
- Create: `frontend/src/components/builder/hymns/hymns-toolbar.tsx`
- Modify: `frontend/src/components/builder/hymns/hymns-step.tsx`
- Test: `frontend/src/components/builder/hymns/hymns-step.test.tsx` (+4)

**Interfaces:**
- Consumes: `Switch` (T7), `Select` and its parts, `Skeleton`, `Label`; `setHymnal`, `setExcludeRecent` (T4).
- Produces: `HymnsToolbar({children})`, `ToolbarSkeleton()`, `HymnalPicker({hymnals, selected, stale, storedCode, onChange})`, `ExcludeSwitch({on, hidden, dateValid, onChange})`, `hiddenCountText(n)`. Later user: T10 (Suggest joins the toolbar).

Counts after this task: frontend **407 passed in 64 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/builder/hymns/hymns-toolbar.tsx 2>&1 | head -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/components/builder/hymns/hymns-toolbar.tsx': No such file or directory`; ` Test Files  64 passed (64)`, `      Tests  403 passed (403)`.

- [ ] **Step 2 (agent): Write the failing tests**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/components/builder/hymns/hymns-step.test.tsx", [
    ('''import { useDraft } from "@/lib/draft/context";
import { editOccasion } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type HymnPick } from "@/lib/draft/schema";
''',
     '''import { useDraft } from "@/lib/draft/context";
import { editOccasion, setDate } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type HymnPick } from "@/lib/draft/schema";
'''),
    ('''  testDraft,
  USER_ID,
''',
     '''  testDraft,
  twoHymnals,
  USER_ID,
'''),
])
with open("frontend/src/components/builder/hymns/hymns-step.test.tsx", "a", encoding="utf-8") as f:
    f.write('''
describe("the toolbar (S Toolbar)", () => {
  it("switches hymnals from the select, keeping the picks, and notes a hymnal with no scripture references", async () => {
    // One hymnal (production today): no select.
    const one = renderStep(draftWith(slots(pick(COME))));
    await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(screen.queryByRole("combobox", { name: "Hymnal" })).toBeNull();
    expect(within(card("Opening")).queryByText("GG2013")).toBeNull();
    one.unmount();

    const { user, api } = renderStep(draftWith(slots(pick(COME))), { "GET /hymnals": twoHymnals() });
    const select = await screen.findByRole("combobox", { name: "Hymnal" });
    expect(select).toHaveTextContent("GG2013 · 853 hymns");
    expect(screen.getByText("Which hymnal to choose hymns from for this service.")).toBeInTheDocument();
    expect(within(card("Opening")).getByText("GG2013")).toBeInTheDocument(); // 2+ hymnals: each pick shows its hymnal
    await user.click(select);
    await user.click(await screen.findByRole("option", { name: "PH1990 · 605 hymns" }));
    await waitFor(() => expect(stored().hymns.hymnal).toBe("PH1990"));
    expect(stored().hymns.slots.opening).toEqual(pick(COME)); // picks keep their own hymnal
    await waitFor(() =>
      expect(api.requests.map((r) => r.path)).toContain("/hymns?hymnal=PH1990&limit=2000&recent_for_date=2026-10-04"),
    );
    expect(
      await screen.findByText("PH1990 has no scripture references, so scripture matches and AI response picks will be weaker."),
    ).toBeInTheDocument();
    const input = await readyPicker("Response");
    await user.type(input, "long");
    expect(await screen.findByRole("option", { name: /#1 Come, Thou Long-Expected Jesus/ })).toBeInTheDocument();
    // Choosing the effective hymnal again stores null, so it is not unsaved work (owner answer 1).
    await user.keyboard("{Escape}");
    await user.click(screen.getByRole("combobox", { name: "Hymnal" }));
    await user.click(await screen.findByRole("option", { name: "GG2013 · 853 hymns" }));
    await waitFor(() => expect(stored().hymns.hymnal).toBeNull());
  });

  it("keeps a vanished stored hymnal in the draft and shows the effective one, writing nothing, also while GET /hymnals fails", async () => {
    const saved = draftWith({ hymnal: "HYMNAL1982" });
    const first = renderStep(saved, { "GET /hymnals": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByText("Couldn't load this church's hymnal.")).toBeInTheDocument();
    expect(first.api.requests.some((r) => r.path.startsWith("/hymns"))).toBe(false);
    first.unmount();
    expect(stored().hymns).toEqual(saved.hymns);
    expect(stored().updated_at).toBe(saved.updated_at);

    const { api } = renderStep(saved);
    expect(
      await screen.findByText("HYMNAL1982 is no longer in your church's hymnals. Showing GG2013 instead."),
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(api.requests.map((r) => r.path)).toContain("/hymns?hymnal=GG2013&limit=2000&recent_for_date=2026-10-04"),
    );
    expect(stored().hymns.hymnal).toBe("HYMNAL1982");
    expect(stored().updated_at).toBe(saved.updated_at); // no write, so not dirty
  });

  it("the Exclude switch counts the hidden hymns, and is off without a valid date", async () => {
    const { user, unmount } = renderStep();
    const exclude = await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(exclude).toBeChecked();
    expect(
      screen.getByText("Hides hymns sung in the 12 weeks before this service or planned in the 12 weeks after it. 2 hymns are hidden."),
    ).toBeInTheDocument();
    await user.click(exclude);
    await waitFor(() => expect(stored().hymns.exclude_recent).toBe(false));
    expect(screen.queryByText(/hymns are hidden/)).toBeNull();
    unmount();

    const { api } = renderStep(setDate(testDraft(), ""));
    const off = await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(off).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Pick a valid date in step 1 to check recent use.")).toBeInTheDocument();
    expect(api.requests.map((r) => r.path)).toContain("/hymns?hymnal=GG2013&limit=2000"); // no recent_for_date
  });

  it("exclusion never clears a pick: the switch hides recent hymns from the picker and keeps a recent pick with its notice", async () => {
    const { user } = renderStep(draftWith(slots(pick(FAITHFUL))));
    const opening = await screen.findByRole("region", { name: "Opening hymn" });
    expect(
      await within(opening).findByText("Used on September 6, 2026 — within 12 weeks of this service."),
    ).toBeInTheDocument();
    const input = await readyPicker("Response");
    await user.type(input, "great");
    expect(await screen.findByText("No hymns match “great”.")).toBeInTheDocument();
    expect(screen.getByText("1 more used within 12 weeks is hidden.")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    const exclude = screen.getByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    await user.click(exclude);
    await waitFor(() => expect(stored().hymns.exclude_recent).toBe(false));
    await user.clear(input);
    await user.type(input, "great");
    const option = await screen.findByRole("option", { name: /#700 Great Is Thy Faithfulness/ });
    expect(within(option).getByText("Used Sep 6")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    await user.click(exclude);
    await waitFor(() => expect(stored().hymns.exclude_recent).toBe(true));
    expect(stored().hymns.slots).toEqual(slots(pick(FAITHFUL)).slots); // AC12: toggling never touched a slot
    expect(within(opening).getByText("#700 Great Is Thy Faithfulness")).toBeInTheDocument();
    expect(within(opening).getByText("Used on September 6, 2026 — within 12 weeks of this service.")).toBeInTheDocument();
  });
});
''')

print("T9 tests written")
PYEOF
```

**Expected:** `T9 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/hymns/hymns-step.test.tsx 2>&1 | grep -E "^ +×|Tests ")
```

**Expected** (each waits about a second for a switch or a note that is not there yet):

```
   × the toolbar (S Toolbar) > switches hymnals from the select, keeping the picks, and notes a hymnal with no scripture references <t>ms
   × the toolbar (S Toolbar) > keeps a vanished stored hymnal in the draft and shows the effective one, writing nothing, also while GET /hymnals fails <t>ms
   × the toolbar (S Toolbar) > the Exclude switch counts the hidden hymns, and is off without a valid date <t>ms
   × the toolbar (S Toolbar) > exclusion never clears a pick: the switch hides recent hymns from the picker and keeps a recent pick with its notice <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 4 ⎯⎯⎯⎯⎯⎯⎯
      Tests  4 failed | 9 passed (13)
```

- [ ] **Step 4 (agent): Write the toolbar and put it in the step**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/components/builder/hymns/hymns-step.tsx", [
    ('''import { duplicateNotice, MISSING_NOTICE, recentUseNotice } from "@/lib/hymns/labels";
import { clearSlot, duplicateSlots, pickFromHymn, reconcilePick, setSlot, type Reconciled } from "@/lib/hymns/picks";
import { useHymnals, useHymnLists } from "@/lib/queries/hymns";
''',
     '''import { duplicateNotice, MISSING_NOTICE, recentUseNotice } from "@/lib/hymns/labels";
import {
  clearSlot,
  duplicateSlots,
  pickFromHymn,
  reconcilePick,
  setExcludeRecent,
  setHymnal,
  setSlot,
  type Reconciled,
} from "@/lib/hymns/picks";
import { useHymnals, useHymnLists } from "@/lib/queries/hymns";
'''),
    ('''import { HymnSlotCard } from "./hymn-slot-card";
import { useUndoToasts } from "./use-undo-toasts";
''',
     '''import { HymnSlotCard } from "./hymn-slot-card";
import { ExcludeSwitch, HymnalPicker, HymnsToolbar, ToolbarSkeleton } from "./hymns-toolbar";
import { useUndoToasts } from "./use-undo-toasts";
'''),
    (''' * spinner. The selected hymnal is resolved only from a loaded `GET /hymnals`
 * and never written back (S Toolbar). Removing a hymn offers Undo in a toast
 * that never outlives the step.
 */
''',
     ''' * spinner. The selected hymnal is resolved only from a loaded `GET /hymnals`
 * and never written back (S Toolbar); the toolbar's Select and Exclude switch
 * are the only writers of the hymnal and the switch. Removing a hymn offers
 * Undo in a toast that never outlives the step.
 */
'''),
    ('''  const duplicates = duplicateSlots(hymns.slots);

''',
     '''  const duplicates = duplicateSlots(hymns.slots);
  const hiddenRecent = (selectedList ?? []).filter((h) => h.title.trim() !== "" && h.recent_use_on !== null).length;

'''),
    ('''        <EmptyHymnal />
      ) : null}
      {SLOTS.map((slot) => {
''',
     '''        <EmptyHymnal />
      ) : hymnals === undefined || code === null || selected === null ? (
        <ToolbarSkeleton />
      ) : (
        <HymnsToolbar>
          <HymnalPicker
            hymnals={hymnals}
            selected={code}
            stale={selected.stale}
            storedCode={hymns.hymnal}
            onChange={(next) => update((d) => setHymnal(d, next, hymnals.effective_hymnal))}
          />
          <ExcludeSwitch
            on={hymns.exclude_recent}
            hidden={hiddenRecent}
            dateValid={dateValid}
            onChange={(on) => update((d) => setExcludeRecent(d, on))}
          />
        </HymnsToolbar>
      )}
      {SLOTS.map((slot) => {
'''),
])

Path("frontend/src/components/builder/hymns/hymns-toolbar.tsx").write_text('''"use client";

import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import type { Hymnals } from "@/lib/api/types";

/** "4 hymns are hidden." (S Toolbar); "1 hymn is hidden." for one (plan clarification 13). */
export function hiddenCountText(n: number): string {
  return n === 1 ? "1 hymn is hidden." : `${n} hymns are hidden.`;
}

/** The toolbar while `GET /hymnals` loads (S "Whole-step states": skeletons, no spinner; plan clarification 7). */
export function ToolbarSkeleton() {
  return (
    <div role="status" aria-label="Loading the hymnal" className="grid gap-3">
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-11 w-full" />
    </div>
  );
}

/**
 * The Hymnal select, shown only with 2+ hymnals, and the notes that go with
 * the selected hymnal (S Toolbar): a stored code the church no longer has
 * (shown even when the select is hidden), and a hymnal with no scripture
 * references. Choosing writes the draft's hymnal; picks keep their own.
 */
export function HymnalPicker({
  hymnals,
  selected,
  stale,
  storedCode,
  onChange,
}: {
  hymnals: Hymnals;
  selected: string;
  stale: boolean;
  storedCode: string | null;
  onChange: (code: string) => void;
}) {
  const items: Record<string, string> = Object.fromEntries(
    hymnals.items.map((h) => [h.code, `${h.code} · ${h.hymn_count} hymns`]),
  );
  const current = hymnals.items.find((h) => h.code === selected);
  return (
    <div className="grid gap-2">
      {hymnals.items.length >= 2 ? (
        <>
          <Label id="hymnal-label">Hymnal</Label>
          <Select
            value={selected}
            items={items}
            onValueChange={(value) => {
              if (typeof value === "string") onChange(value);
            }}
          >
            <SelectTrigger
              aria-labelledby="hymnal-label"
              aria-describedby="hymnal-help"
              className="h-11 w-full sm:w-80 data-[size=default]:h-11"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {hymnals.items.map((h) => (
                <SelectItem key={h.code} value={h.code}>
                  {items[h.code]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p id="hymnal-help" className="text-sm text-muted-foreground">
            Which hymnal to choose hymns from for this service.
          </p>
        </>
      ) : null}
      {stale && storedCode ? (
        <p className="text-sm">
          {storedCode} is no longer in your church&apos;s hymnals. Showing {selected} instead.
        </p>
      ) : null}
      {current && current.scripture_ref_count === 0 ? (
        <p className="text-sm text-muted-foreground">
          {current.code} has no scripture references, so scripture matches and AI response picks will be weaker.
        </p>
      ) : null}
    </div>
  );
}

/**
 * "Exclude hymns used within 12 weeks" (S Toolbar). It writes only
 * `exclude_recent`; it never changes a slot or an idea (AC12). Disabled when
 * the draft's date is not valid.
 */
export function ExcludeSwitch({
  on,
  hidden,
  dateValid,
  onChange,
}: {
  on: boolean;
  /** Hymns in the selected hymnal used within 12 weeks of the service. */
  hidden: number;
  dateValid: boolean;
  onChange: (on: boolean) => void;
}) {
  return (
    <div className="grid gap-1">
      <div className="flex min-h-11 items-center gap-3">
        <Switch
          id="exclude-recent"
          checked={on}
          disabled={!dateValid}
          onCheckedChange={(checked) => onChange(checked)}
          aria-describedby="exclude-recent-help"
        />
        <Label htmlFor="exclude-recent">Exclude hymns used within 12 weeks</Label>
      </div>
      <p id="exclude-recent-help" className="text-sm text-muted-foreground">
        {dateValid
          ? "Hides hymns sung in the 12 weeks before this service or planned in the 12 weeks after it."
          : "Pick a valid date in step 1 to check recent use."}
        {dateValid && on && hidden > 0 ? ` ${hiddenCountText(hidden)}` : null}
      </p>
    </div>
  );
}

/** The toolbar's frame: the hymnal, the switch, then Suggest (slice 3b T10). */
export function HymnsToolbar({ children }: { children: ReactNode }) {
  return <div className="grid gap-4 rounded-lg border p-4">{children}</div>;
}
''', encoding="utf-8")

print("T9 code written")
PYEOF
```

**Expected:** `T9 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/hymns 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  2 passed (2)`, `      Tests  15 passed (15)`; ` Test Files  64 passed (64)`, `      Tests  407 passed (407)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `hymns-step.tsx` and `hymns-step.test.tsx`, `??` for `hymns-toolbar.tsx`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/hymns/hymns-toolbar.tsx frontend/src/components/builder/hymns/hymns-step.tsx frontend/src/components/builder/hymns/hymns-step.test.tsx
git commit -m "Hymns: the toolbar's hymnal select and Exclude switch; exclusion never clears a pick (S Toolbar; AC12)" -m "The Hymnal select shows with 2+ hymnals and writes the draft's hymnal
(null for the church's effective one, owner answer 1); picks keep
their own. A vanished stored code is noted and never written; a hymnal
with no scripture references is noted. The Exclude switch writes only
exclude_recent, counts the hidden hymns, and waits for a valid date.
Toggling it never changes a slot (AC12). Frontend 403 -> 407 tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 3 files changed.

**Review checkpoint (T8-T9, batch 4):** the step writes the draft only through `update` with T4's recipes and only on a member's action (nothing on load, even for a vanished hymnal); no request goes out before `GET /hymnals` answers, and none for an empty church; a failed load never shows the empty state; titles and links render as text, links only through `safeHttpsUrl`; every Undo toast is dismissed on unmount and checks the church; the switch never touches a slot.

### Task 10: Suggest hymns and the other ideas (S AI suggestion flow, "Other ideas (AI chips)", "Newer-hymn year label", "Stale and cross-church protection"; F D16, §4.8; owner decision 4; AC11, AC20; clarifications 6, 8, 10, 13, 14)

**Suggest hymns** joins the toolbar: a full-width touch button with the Sparkles icon and S's helper, disabled while pending, for a hymnal with no hymns and for an invalid date, with the readings tip when the draft has no scriptures and no occasion. A tap builds the body with `buildSuggestionRequest` (the NT text only from the passage cache, never fetched; clarification 10) and calls T6's `suggest`. While it waits the button reads "Suggesting…", **Cancel** aborts the wait, and after 8 s "Still working — this can take up to a minute." shows. An `ok` answer is applied only if the draft's date is still the request's, with a functional `update` of the latest draft (`applySuggestions`: empty slots only, F D16), so a pick made during the wait is kept; otherwise "The date changed while suggestions were loading. Try again." A `superseded` answer and a cancel change nothing. The outcome lines (ready, with the left-out count; the newer-hymn note when a returned hymn is flagged; nothing picked; the date changed) sit in a `role="status"` region; each error code's copy shows in an `Alert`, a 429 turning to "Try again now." once its wait passes, and a network or server error goes to a toast (clarification 8). A slot the answer left empty says "No suggestion for this slot." for that date. Under each card `AlternativeChips` shows the ideas for the draft's date only: touch-size chips with the live label (recent use, "Written {year}"), named "Use {title} as the opening hymn" (clarification 14), hidden when their hymnal's list no longer has them; a tap is `swapAlternative`.

**Files:**
- Create: `frontend/src/components/builder/hymns/suggest-hymns-button.tsx`, `frontend/src/components/builder/hymns/alternative-chips.tsx`
- Modify: `frontend/src/components/builder/hymns/hymns-step.tsx`
- Test: `frontend/src/components/builder/hymns/hymns-step.test.tsx` (+7)

**Interfaces:**
- Consumes: `useSuggestHymns`, `keys.passage` (T6, 2c); `buildSuggestionRequest` (T5); `applySuggestions`, `swapAlternative`, `reconcilePick` (T4); `chipName`, `recentUseLabel` (T5); `HymnLabel` (T8); `rateLimitMessage`, `useWaitOver` (2c's `readings/use-wait-over.ts`); `PendingButton`, `Alert`, `errorToastMessage`, `cleanLines`, `useChurchProfile` (the church's translation).
- Produces:
  - `SuggestHymnsButton({selectedHymnal, hymnalEmpty, churchTranslation, onNoSuggestion})`; `suggestErrorMessage(error, waitOver?)`; `STILL_WORKING_MS = 8000`, `DATE_CHANGED`, `NOTHING_PICKED`, `NEWER_NOTE`.
  - `AlternativeChips({slot, ideas, lists, fallbackHymnal, serviceDateIso, showHymnal, onSwap})`.
  - `HymnsStep` renders `null` until the church profile is loaded (the shell loads it first, as for `ReadingsStep`).

Counts after this task: frontend **414 passed in 64 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/builder/hymns | tr '\n' ' '; echo
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `hymn-label.test.tsx hymn-label.tsx hymn-picker.tsx hymn-slot-card.tsx hymns-step.test.tsx hymns-step.tsx hymns-toolbar.tsx use-undo-toasts.ts `; ` Test Files  64 passed (64)`, `      Tests  407 passed (407)`.

- [ ] **Step 2 (agent): Write the failing tests**

One test fakes `setTimeout` too, for the 8-second line, and says why (Code rules). Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/components/builder/hymns/hymns-step.test.tsx", [
    ('''import { Toaster } from "@/components/ui/sonner";
import type { ChurchProfile } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
''',
     '''import { Toaster } from "@/components/ui/sonner";
import type { ChurchProfile, HymnSuggestionBody } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
'''),
    ('''import { pickFromHymn } from "@/lib/hymns/picks";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
''',
     '''import { pickFromHymn } from "@/lib/hymns/picks";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
'''),
    ('''  hymnListRoute,
  lectionaryRoute,
''',
     '''  hymnListRoute,
  hymnSuggestions,
  lectionaryRoute,
'''),
    ('''const KEY = draftKey(USER_ID, church().id);
const [HOLY, PRAISE, COME, GRACE, , FAITHFUL] = gg2013();
/** Grace's recent use around October 4, 2026: sung September 6, planned October 18. */
''',
     '''const KEY = draftKey(USER_ID, church().id);
const [HOLY, PRAISE, COME, GRACE, , FAITHFUL, HERE, , SENT] = gg2013();
/** Grace's recent use around October 4, 2026: sung September 6, planned October 18. */
'''),
])
with open("frontend/src/components/builder/hymns/hymns-step.test.tsx", "a", encoding="utf-8") as f:
    f.write('''
// --- AI suggestions (S "AI suggestion flow"; owner decision 4, F D16) -----------------------

/** A button that moves the draft's date, as step 1 would. */
function DateProbe() {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
      Move to October 11
    </button>
  );
}

/** A route that answers only when `release` is called. */
function held(answer: () => unknown) {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  return {
    handler: async () => {
      await gate;
      return answer();
    },
    release: () => release(),
  };
}

/** Three hymns for each slot, 4 recently used ones left out. */
const THREE_EACH = () =>
  hymnSuggestions(
    { opening: [HOLY, COME, HERE], response: [FAITHFUL, COME, HOLY], closing: [PRAISE, HERE, SENT] },
    { excluded_recent_count: 4 },
  );

function ideaNames(slot: "Opening" | "Response" | "Closing"): string[] {
  const group = within(card(slot)).queryByRole("group", { name: `Other ideas for the ${slot.toLowerCase()} hymn` });
  return group ? within(group).getAllByRole("button").map((b) => b.getAttribute("aria-label") ?? "") : [];
}

async function suggestButton() {
  const button = await screen.findByRole("button", { name: "Suggest hymns" });
  await waitFor(() => expect(button).toBeEnabled());
  return button;
}

describe("Suggest hymns (S AI suggestion flow)", () => {
  it("fills only the empty slots, keeps the member's pick, and shows at least 2 ideas under every slot", async () => {
    const readings = {
      scriptures: ["Isaiah 5:1-7", "Philippians 3:4b-14"],
      occasion: "Nineteenth Sunday after Pentecost",
      selected_nt_ref: "Philippians 3:4b-14",
    };
    const { user, api, queryClient } = renderStep(draftWith(slots(null, pick(GRACE)), readings), {
      "POST /hymns/suggestions": THREE_EACH(),
    });
    queryClient.setQueryData(keys.passage("web", "Philippians 3:4b-14"), {
      reference: "Philippians 3:4b-14",
      status: "ok",
      sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
    });
    expect(await screen.findByText("Fills empty slots and shows other ideas under each hymn.")).toBeInTheDocument();
    expect(screen.queryByText(/^Tip:/)).toBeNull();
    await user.click(await suggestButton());
    expect(
      await screen.findByText("Suggestions ready. Tap an idea under a hymn to swap it in. 4 recently used hymns were left out."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Suggestions favor older and familiar hymns. Newer hymns show the year their words were written."),
    ).toBeInTheDocument();
    const body = api.requests.find((r) => r.path === "/hymns/suggestions")?.body as HymnSuggestionBody;
    expect(body).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "Nineteenth Sunday after Pentecost",
      scriptures: ["Isaiah 5:1-7", "Philippians 3:4b-14"],
      selected_nt_ref: "Philippians 3:4b-14",
      hymnal: "GG2013",
      exclude_recent: true,
      current_picks: { opening: null, response: GRACE.id, closing: null },
      nt_text: "I press on toward the goal.",
    });
    await waitFor(() => expect(stored().hymns.slots).toEqual(slots(pick(HOLY), pick(GRACE), pick(PRAISE)).slots));
    expect(stored().hymns.alternatives?.for_date_iso).toBe("2026-10-04");
    expect(ideaNames("Opening")).toEqual([
      "Use Come, Thou Almighty King as the opening hymn",
      "Use Here I Am, Lord, written 1981, as the opening hymn",
    ]);
    expect(ideaNames("Response")).toHaveLength(3); // a filled slot: 3 ideas, its own pick left out
    expect(ideaNames("Closing")).toEqual([
      "Use Here I Am, Lord, written 1981, as the closing hymn",
      "Use Sent Forth by God's Blessing as the closing hymn",
    ]);
    expect(within(card("Response")).getByText("#649 Amazing Grace")).toBeInTheDocument();
    expect(within(card("Response")).getByText("Used Sep 6")).toBeInTheDocument(); // a recently used idea
    expect(within(card("Opening")).getAllByText("Written 1981")).toHaveLength(1);
  });

  it("a tap swaps an idea with the pick and a second tap swaps back; the ideas hide when the date changes", async () => {
    const { user } = renderStep(testDraft(), { "POST /hymns/suggestions": THREE_EACH() }, <DateProbe />);
    await user.click(await suggestButton());
    await screen.findByText(/^Suggestions ready/);
    const opening = card("Opening");
    await user.click(within(opening).getByRole("button", { name: "Use Come, Thou Almighty King as the opening hymn" }));
    expect(await within(opening).findByText("#403 Come, Thou Almighty King")).toBeInTheDocument();
    expect(ideaNames("Opening")).toEqual([
      "Use Holy, Holy, Holy! Lord God Almighty as the opening hymn",
      "Use Here I Am, Lord, written 1981, as the opening hymn",
    ]);
    await user.click(
      within(opening).getByRole("button", { name: "Use Holy, Holy, Holy! Lord God Almighty as the opening hymn" }),
    );
    expect(await within(opening).findByText("#1 Holy, Holy, Holy! Lord God Almighty")).toBeInTheDocument();
    expect(ideaNames("Opening")).toEqual([
      "Use Come, Thou Almighty King as the opening hymn",
      "Use Here I Am, Lord, written 1981, as the opening hymn",
    ]);
    await user.click(screen.getByRole("button", { name: "Move to October 11" }));
    await waitFor(() => expect(ideaNames("Opening")).toEqual([]));
    expect(within(opening).getByText("#1 Holy, Holy, Holy! Lord God Almighty")).toBeInTheDocument(); // the pick stays
  });

  it("a pick made while the request runs is kept and gets ideas", async () => {
    const answer = held(THREE_EACH);
    const { user } = renderStep(testDraft(), { "POST /hymns/suggestions": answer.handler });
    await user.click(await suggestButton());
    expect(await screen.findByRole("button", { name: "Suggesting…" })).toBeDisabled();
    const input = await readyPicker("Response");
    await user.type(input, "650");
    await user.click(await screen.findByRole("option", { name: /#650 Amazing Grace/ }));
    await waitFor(() => expect(stored().hymns.slots.response?.number).toBe(650));
    answer.release();
    await screen.findByText(/^Suggestions ready/);
    await waitFor(() => expect(stored().hymns.slots.opening?.title).toBe("Holy, Holy, Holy! Lord God Almighty"));
    expect(stored().hymns.slots.response?.number).toBe(650);
    expect(ideaNames("Response")).toHaveLength(3);
  });

  it("drops the answer when the date changed during the wait", async () => {
    const answer = held(THREE_EACH);
    const { user } = renderStep(testDraft(), { "POST /hymns/suggestions": answer.handler }, <DateProbe />);
    await user.click(await suggestButton());
    await screen.findByRole("button", { name: "Suggesting…" });
    await user.click(screen.getByRole("button", { name: "Move to October 11" }));
    await waitFor(() => expect(stored().readings.date_iso).toBe("2026-10-11"));
    answer.release();
    expect(await screen.findByText("The date changed while suggestions were loading. Try again.")).toBeInTheDocument();
    expect(stored().hymns.slots).toEqual(testDraft().hymns.slots);
    expect(stored().hymns.alternatives).toBeNull();
  });

  it("Cancel stops waiting and returns to idle; after 8 s it says it is still working", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const answer = held(THREE_EACH);
    const { user, api } = renderStep(testDraft(), { "POST /hymns/suggestions": answer.handler });
    await user.click(await suggestButton());
    await screen.findByRole("button", { name: "Suggesting…" });
    expect(screen.queryByText("Still working — this can take up to a minute.")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(screen.getByText("Still working — this can take up to a minute.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(await screen.findByRole("button", { name: "Suggest hymns" })).toBeEnabled();
    expect(api.requests.filter((r) => r.path === "/hymns/suggestions")).toHaveLength(1);
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.queryByText(/^Suggestions ready/)).toBeNull();
    answer.release();
  });

  it("shows each failure's own copy under the button, and a server error as a toast", async () => {
    const cases: [ReturnType<typeof fakeError>, string][] = [
      [
        fakeError(503, "ai_not_configured", "AI suggestions aren't set up on this app yet."),
        "AI suggestions aren't set up on this app yet. You can still choose hymns yourself.",
      ],
      [fakeError(503, "ai_busy", "The AI service is busy. Try again in a minute."), "The AI service is busy. Try again in a minute."],
      [fakeError(504, "ai_timeout", "The AI took too long to answer. Try again."), "The AI took too long to answer. Try again."],
      [
        fakeError(502, "ai_upstream_error", "The AI service had a problem. Try again."),
        "The AI service had a problem. Try again in a moment.",
      ],
      [
        fakeError(422, "invalid_request", "This hymnal has no hymns to suggest from."),
        "This hymnal has no hymns to suggest from.",
      ],
    ];
    for (const [response, copy] of cases) {
      const { user, unmount } = renderStep(testDraft(), { "POST /hymns/suggestions": response });
      await user.click(await suggestButton());
      expect(await screen.findByRole("alert")).toHaveTextContent(copy);
      expect(stored().hymns.slots).toEqual(testDraft().hymns.slots); // nothing stored
      unmount();
    }
    const limited = renderStep(testDraft(), {
      "POST /hymns/suggestions": {
        ...fakeError(429, "rate_limited", "Too many requests.", { details: { retry_after_seconds: 1 } }),
        headers: { "Retry-After": "1" },
      },
    });
    await limited.user.click(await suggestButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests — try again in 1 s.");
    expect(await screen.findByText("Try again now.", {}, { timeout: 3_000 })).toBeInTheDocument();
    limited.unmount();

    const { user } = renderStep(testDraft(), {
      "POST /hymns/suggestions": fakeError(500, "internal_error", "Something went wrong."),
    });
    await user.click(await suggestButton());
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("says when a slot or every slot got nothing, and waits for a valid date; the tip asks for readings first", async () => {
    const partly = hymnSuggestions({ opening: [HOLY, COME, GRACE], response: [], closing: [PRAISE, GRACE, SENT] });
    const one = renderStep(testDraft(), { "POST /hymns/suggestions": partly });
    expect(await screen.findByText("Tip: add the readings in step 1 first — suggestions use them.")).toBeInTheDocument();
    await one.user.click(await suggestButton());
    expect(await within(card("Response")).findByText("No suggestion for this slot.")).toBeInTheDocument();
    expect(within(card("Opening")).queryByText("No suggestion for this slot.")).toBeNull();
    expect(screen.queryByText(/Suggestions favor older/)).toBeNull(); // no flagged hymn returned
    one.unmount();

    const none = renderStep(testDraft(), {
      "POST /hymns/suggestions": hymnSuggestions({ opening: [], response: [], closing: [] }),
    });
    await none.user.click(await suggestButton());
    expect(
      await screen.findByText("The AI didn't pick any hymns from this hymnal. Try again, or choose hymns yourself."),
    ).toBeInTheDocument();
    none.unmount();

    renderStep(setDate(testDraft(), ""));
    await screen.findByRole("switch", { name: "Exclude hymns used within 12 weeks" });
    expect(screen.getByRole("button", { name: "Suggest hymns" })).toBeDisabled();
  });
});
''')

print("T10 tests written")
PYEOF
```

**Expected:** `T10 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/hymns/hymns-step.test.tsx 2>&1 | grep -E "^ +×|Tests ")
```

**Expected** (each waits about a second for a button that is not there yet):

```
   × Suggest hymns (S AI suggestion flow) > fills only the empty slots, keeps the member's pick, and shows at least 2 ideas under every slot <t>ms
   × Suggest hymns (S AI suggestion flow) > a tap swaps an idea with the pick and a second tap swaps back; the ideas hide when the date changes <t>ms
   × Suggest hymns (S AI suggestion flow) > a pick made while the request runs is kept and gets ideas <t>ms
   × Suggest hymns (S AI suggestion flow) > drops the answer when the date changed during the wait <t>ms
   × Suggest hymns (S AI suggestion flow) > Cancel stops waiting and returns to idle; after 8 s it says it is still working <t>ms
   × Suggest hymns (S AI suggestion flow) > shows each failure's own copy under the button, and a server error as a toast <t>ms
   × Suggest hymns (S AI suggestion flow) > says when a slot or every slot got nothing, and waits for a valid date; the tip asks for readings first <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 7 ⎯⎯⎯⎯⎯⎯⎯
      Tests  7 failed | 13 passed (20)
```

- [ ] **Step 4 (agent): Write Suggest and the ideas, and put them in the step**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


Path("frontend/src/components/builder/hymns/alternative-chips.tsx").write_text('''"use client";

import { Button } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import type { HymnPick, Slot } from "@/lib/draft/schema";
import { chipName, recentUseLabel } from "@/lib/hymns/labels";
import { reconcilePick } from "@/lib/hymns/picks";

import { HymnLabel } from "./hymn-label";

/**
 * "Other ideas" under a slot (S "Other ideas (AI chips)"): the AI's other
 * hymns for this date, each a touch-size chip. A chip shows its live hymn
 * once its hymnal's list has loaded (with "Used Sep 7" and "Written {year}"
 * badges), and is hidden when that list no longer has it. A tap swaps it with
 * the slot's pick, so a second tap swaps back.
 */
export function AlternativeChips({
  slot,
  ideas,
  lists,
  fallbackHymnal,
  serviceDateIso,
  showHymnal,
  onSwap,
}: {
  slot: Slot;
  ideas: readonly HymnPick[];
  lists: ReadonlyMap<string, readonly Hymn[] | undefined>;
  fallbackHymnal: string | null;
  serviceDateIso: string;
  showHymnal: boolean;
  onSwap: (hymnId: string) => void;
}) {
  const shown = ideas.flatMap((idea) => {
    const reconciled = reconcilePick(idea, lists, fallbackHymnal);
    if (reconciled.status === "missing" || idea.hymn_id === null) return [];
    return [{ idea, hymnId: idea.hymn_id, live: reconciled.status === "ok" ? reconciled.live : null }];
  });
  if (shown.length === 0) return null;
  return (
    <div className="grid gap-1.5">
      <p className="text-sm font-medium">Other ideas</p>
      <div role="group" aria-label={`Other ideas for the ${slot} hymn`} className="flex flex-wrap gap-2">
        {shown.map(({ idea, hymnId, live }) => (
          <Button
            key={hymnId}
            variant="secondary"
            size="touch"
            className="max-w-full min-w-0"
            aria-label={chipName(live ?? { title: idea.title, newer_than_preferred: false, text_year: null }, slot)}
            onClick={() => onSwap(hymnId)}
          >
            <HymnLabel
              hymn={live ?? idea}
              showHymnal={showHymnal}
              recentBadge={live?.recent_use_on ? recentUseLabel(live.recent_use_on, serviceDateIso) : null}
              truncate
            />
          </Button>
        ))}
      </div>
    </div>
  );
}
''', encoding="utf-8")

edit("frontend/src/components/builder/hymns/hymns-step.tsx", [
    ('''"use client";

''',
     '''"use client";

import { useState } from "react";

'''),
    ('''import type { Hymn } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
''',
     '''import type { Hymn } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { isValidDateIso } from "@/lib/dates";
'''),
    ('''  setSlot,
  type Reconciled,
} from "@/lib/hymns/picks";
import { useHymnals, useHymnLists } from "@/lib/queries/hymns";

import { HymnSlotCard } from "./hymn-slot-card";
import { ExcludeSwitch, HymnalPicker, HymnsToolbar, ToolbarSkeleton } from "./hymns-toolbar";
import { useUndoToasts } from "./use-undo-toasts";
''',
     '''  setSlot,
  swapAlternative,
  type Reconciled,
} from "@/lib/hymns/picks";
import { useChurchProfile } from "@/lib/queries/church";
import { useHymnals, useHymnLists } from "@/lib/queries/hymns";

import { AlternativeChips } from "./alternative-chips";
import { HymnSlotCard } from "./hymn-slot-card";
import { ExcludeSwitch, HymnalPicker, HymnsToolbar, ToolbarSkeleton } from "./hymns-toolbar";
import { SuggestHymnsButton } from "./suggest-hymns-button";
import { useUndoToasts } from "./use-undo-toasts";
'''),
    (''' * are the only writers of the hymnal and the switch. Removing a hymn offers
 * Undo in a toast that never outlives the step.
 */
export function HymnsStep() {
  const { draft, update } = useDraft();
''',
     ''' * are the only writers of the hymnal and the switch. Removing a hymn offers
 * Undo in a toast that never outlives the step. Suggest fills the empty slots
 * and puts other ideas under each hymn; the ideas show only for the date they
 * were suggested for.
 */
export function HymnsStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { draft, update } = useDraft();
'''),
    ('''  const showUndo = useUndoToasts();

''',
     '''  const showUndo = useUndoToasts();
  // "No suggestion for this slot." after the last answer, for its date only (component state).
  const [unsuggested, setUnsuggested] = useState<{ dateIso: string; slots: Slot[] }>({ dateIso: "", slots: [] });
  if (!profile) return null;

'''),
    ('''  const hiddenRecent = (selectedList ?? []).filter((h) => h.title.trim() !== "" && h.recent_use_on !== null).length;

''',
     '''  const hiddenRecent = (selectedList ?? []).filter((h) => h.title.trim() !== "" && h.recent_use_on !== null).length;
  const ideas = hymns.alternatives?.for_date_iso === dateIso ? hymns.alternatives.by_slot : null;
  const selectedCount = hymnals?.items.find((h) => h.code === code)?.hymn_count ?? 0;

'''),
    ('''          />
        </HymnsToolbar>
''',
     '''          />
          <SuggestHymnsButton
            selectedHymnal={code}
            hymnalEmpty={selectedCount === 0}
            churchTranslation={profile.effective_translation}
            onNoSuggestion={(noneFor, forDate) => setUnsuggested({ dateIso: forDate, slots: noneFor })}
          />
        </HymnsToolbar>
'''),
    ('''            onRemove={() => remove(slot, title)}
          />
        );
''',
     '''            onRemove={() => remove(slot, title)}
          >
            {unsuggested.dateIso === dateIso && unsuggested.slots.includes(slot) ? (
              <p className="text-sm text-muted-foreground">No suggestion for this slot.</p>
            ) : null}
            {ideas ? (
              <AlternativeChips
                slot={slot}
                ideas={ideas[slot]}
                lists={lists.lists}
                fallbackHymnal={code}
                serviceDateIso={dateIso}
                showHymnal={showHymnal}
                onSwap={(hymnId) => update((d) => ({ ...d, hymns: swapAlternative(d.hymns, slot, hymnId) }))}
              />
            ) : null}
          </HymnSlotCard>
        );
'''),
])

Path("frontend/src/components/builder/hymns/suggest-hymns-button.tsx").write_text('''"use client";

import { useQueryClient } from "@tanstack/react-query";
import { SparklesIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { rateLimitMessage, useWaitOver } from "@/components/builder/readings/use-wait-over";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ApiError } from "@/lib/api/client";
import { errorToastMessage } from "@/lib/api/errors";
import type { HymnSuggestions, Passage } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { SLOTS, type Slot } from "@/lib/draft/schema";
import { applySuggestions } from "@/lib/hymns/picks";
import { buildSuggestionRequest } from "@/lib/hymns/suggest-request";
import { useSuggestHymns } from "@/lib/queries/hymns";
import { keys } from "@/lib/queries/keys";
import { cleanLines } from "@/lib/scripture-refs";

/** After this long the pending button adds "Still working — this can take up to a minute." (F §4.8). */
export const STILL_WORKING_MS = 8_000;

export const DATE_CHANGED = "The date changed while suggestions were loading. Try again.";
export const NOTHING_PICKED = "The AI didn't pick any hymns from this hymnal. Try again, or choose hymns yourself.";
export const NEWER_NOTE =
  "Suggestions favor older and familiar hymns. Newer hymns show the year their words were written.";

/**
 * The inline copy for a failed suggestion (S "AI suggestion flow" 5), keyed on
 * the error code; null for the errors the app handles globally (network, 500:
 * a toast, F §4.8). A cancel never reaches here.
 */
export function suggestErrorMessage(e: ApiError, waitOver = false): string | null {
  switch (e.code) {
    case "ai_not_configured":
      return "AI suggestions aren't set up on this app yet. You can still choose hymns yourself.";
    case "ai_busy":
      return "The AI service is busy. Try again in a minute.";
    case "ai_timeout":
      return "The AI took too long to answer. Try again.";
    case "ai_upstream_error":
      return "The AI service had a problem. Try again in a moment.";
    case "invalid_request":
      return e.message;
    case "rate_limited":
      return rateLimitMessage(e, waitOver);
    case "timeout":
      return "This is taking too long. Try again.";
    default:
      return null;
  }
}

type Outcome =
  | { kind: "ready"; text: string; newer: boolean }
  | { kind: "none" }
  | { kind: "date_changed" }
  | { kind: "error"; error: ApiError };

/** "Suggestions ready…", with " {n} recently used hymns were left out." (plan clarification 13 for one). */
function readyText(resp: HymnSuggestions): string {
  const n = resp.excluded_recent_count;
  const left = n === 0 ? "" : n === 1 ? " 1 recently used hymn was left out." : ` ${n} recently used hymns were left out.`;
  return `Suggestions ready. Tap an idea under a hymn to swap it in.${left}`;
}

function SuggestError({ error }: { error: ApiError }) {
  const over = useWaitOver(error.code === "rate_limited" ? error : null);
  return (
    <Alert variant="destructive">
      <AlertTitle>{suggestErrorMessage(error, over)}</AlertTitle>
    </Alert>
  );
}

/**
 * "Suggest hymns" (S "AI suggestion flow"). The answer is applied with a
 * functional update of the latest draft (`applySuggestions`: only empty slots
 * are filled, F D16), so a pick made during the wait counts. It is dropped when
 * `useSuggestHymns` reports it superseded (a newer request, the step
 * unmounted, another church) or the draft's date changed meanwhile. Cancel
 * aborts the wait; the server finishes and discards it (F §1.8). Messages and
 * errors live in component state, never in the draft.
 */
export function SuggestHymnsButton({
  selectedHymnal,
  hymnalEmpty,
  churchTranslation,
  onNoSuggestion,
}: {
  selectedHymnal: string;
  /** The selected hymnal has no hymns. */
  hymnalEmpty: boolean;
  churchTranslation: string;
  /** The slots the answer left empty, for "No suggestion for this slot." ([] when a request starts). */
  onNoSuggestion: (slots: Slot[], dateIso: string) => void;
}) {
  const { draft, update } = useDraft();
  const queryClient = useQueryClient();
  const { suggest, isPending } = useSuggestHymns();
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [slow, setSlow] = useState(false);
  const latest = useRef(draft);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    latest.current = draft;
  }, [draft]);

  useEffect(() => () => controller.current?.abort(), []);

  useEffect(() => {
    if (!isPending) return;
    const timer = setTimeout(() => setSlow(true), STILL_WORKING_MS);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [isPending]);

  const dateValid = isValidDateIso(draft.readings.date_iso);
  const noReadings = cleanLines(draft.readings.scriptures).length === 0 && draft.readings.occasion.trim() === "";

  async function run() {
    const body = buildSuggestionRequest(
      latest.current,
      selectedHymnal,
      (translation, ref) => queryClient.getQueryData<Passage>(keys.passage(translation, ref)),
      churchTranslation,
    );
    const date = body.service_date_iso;
    const own = new AbortController();
    controller.current = own;
    setOutcome(null);
    onNoSuggestion([], date);
    const result = await suggest(body, own.signal);
    if (controller.current === own) controller.current = null;
    if (result.status === "superseded") return;
    if (result.status === "error") {
      if (result.error.code === "aborted") return;
      if (suggestErrorMessage(result.error) === null) toast.error(errorToastMessage(result.error));
      else setOutcome({ kind: "error", error: result.error });
      return;
    }
    const resp = result.data;
    if (latest.current.readings.date_iso !== date) {
      setOutcome({ kind: "date_changed" });
      return;
    }
    update((d) => (d.readings.date_iso === date ? { ...d, hymns: applySuggestions(d.hymns, resp, date) } : d));
    const empty = SLOTS.filter((slot) => resp.slots[slot].length === 0);
    if (empty.length === SLOTS.length) {
      setOutcome({ kind: "none" });
      return;
    }
    onNoSuggestion(empty, date);
    const newer = SLOTS.some((slot) => resp.slots[slot].some((h) => h.newer_than_preferred));
    setOutcome({ kind: "ready", text: readyText(resp), newer });
  }

  return (
    <div className="grid gap-2">
      <PendingButton
        size="touch"
        className="w-full"
        pending={isPending}
        pendingLabel="Suggesting…"
        disabled={hymnalEmpty || !dateValid}
        onClick={() => void run()}
      >
        <SparklesIcon data-icon="inline-start" aria-hidden="true" />
        Suggest hymns
      </PendingButton>
      {isPending ? (
        <div className="flex flex-wrap items-center gap-x-3 text-sm text-muted-foreground">
          {slow ? <p>Still working — this can take up to a minute.</p> : null}
          <Button variant="link" className="h-11 px-0" onClick={() => controller.current?.abort()}>
            Cancel
          </Button>
        </div>
      ) : null}
      <p className="text-sm text-muted-foreground">Fills empty slots and shows other ideas under each hymn.</p>
      {noReadings ? (
        <p className="text-sm text-muted-foreground">Tip: add the readings in step 1 first — suggestions use them.</p>
      ) : null}
      <div role="status" className="grid gap-1 text-sm">
        {outcome?.kind === "ready" ? <p>{outcome.text}</p> : null}
        {outcome?.kind === "ready" && outcome.newer ? <p className="text-muted-foreground">{NEWER_NOTE}</p> : null}
        {outcome?.kind === "none" ? <p>{NOTHING_PICKED}</p> : null}
        {outcome?.kind === "date_changed" ? <p>{DATE_CHANGED}</p> : null}
      </div>
      {outcome?.kind === "error" ? <SuggestError error={outcome.error} /> : null}
    </div>
  );
}
''', encoding="utf-8")

print("T10 code written")
PYEOF
```

**Expected:** `T10 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/hymns 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  2 passed (2)`, `      Tests  22 passed (22)`; ` Test Files  64 passed (64)`, `      Tests  414 passed (414)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `hymns-step.tsx` and `hymns-step.test.tsx`, `??` for the two new files.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/hymns/suggest-hymns-button.tsx frontend/src/components/builder/hymns/alternative-chips.tsx frontend/src/components/builder/hymns/hymns-step.tsx frontend/src/components/builder/hymns/hymns-step.test.tsx
git commit -m "Hymns: Suggest fills empty slots and offers other ideas, with Cancel, the date check and each error's copy (S AI suggestion flow; F D16; AC11)" -m "Suggest sends buildSuggestionRequest's body (NT text from the passage
cache only) and applies the answer to the latest draft with
applySuggestions, empty slots only, when the date has not changed; a
superseded answer or a cancel changes nothing. Suggesting..., Cancel,
Still working after 8 s; each AI error's copy inline, Try again now.
after a 429's wait, a server error as a toast. Other ideas show for the
draft's date only, with their badges; a tap swaps, a second swaps back.
Frontend 407 -> 414 tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 4 files changed.

### Task 11: Hymns for the readings (S "Hymns for the readings", Behavior changes 9, 10, 19; AC20; clarifications 11, 13, 14, 15, 19)

`ScriptureMatches` sits under the cards whenever the pickers do. It is a `Collapsible` titled "Hymns for the readings", closed below `md` and open from `md` as it first renders (clarification 19), with the count once loaded, even while closed, because the query lives outside the collapsed content. Its references are `buildMatchRefs(draft scriptures, extra)`; the **Additional scripture** input (`maxLength={200}`, "e.g. Matthew 17") with **Search** or Enter sets the extra reference (component state only). The query runs by itself whenever the references, the selected hymnal or the date change. Results come in "Matches the readings" and "Same chapter", each row a `HymnLabel` with Listen, "Matches {refs}" and an **Add** menu (Opening, Response, Closing hymn; the button is named "Add {title}", clarification 14). Adding over a different hymn shows "{Slot} hymn changed to {title}." with **Undo** through T8's `useUndoToasts` (clarification 15). With Exclude on, recently used matches are hidden behind "{k} recently used matches are hidden." and **Show them**; shown ones carry their badge (clarification 11). Unreadable references, no matches, no references (with **Go to readings**), a hymnal with no scripture references (no request) and a failed search (**Retry**) each have S's copy.

**Files:**
- Create: `frontend/src/components/builder/hymns/scripture-matches.tsx`
- Modify: `frontend/src/components/builder/hymns/hymns-step.tsx`
- Test: `frontend/src/components/builder/hymns/hymns-step.test.tsx` (+5; `renderStep` also answers `POST /hymns/scripture-matches` from now on, since a draft with readings asks for matches)

**Interfaces:**
- Consumes: `useScriptureMatches` (T6), `buildMatchRefs`, `MAX_REF_LENGTH`, `recentUseLabel`, `SLOT_META` (T5), `HymnLabel`, `useUndoToasts` (T8), `setSlot`, `pickFromHymn` (T4); `Collapsible` (2c), `DropdownMenu`, `Input`, `ErrorState`, `Skeleton`, `Badge`, `next/link`.
- Produces: `ScriptureMatches({scriptures, hymnal: HymnalSummary, recentForDate, serviceDateIso, excludeRecent, showHymnal, onAdd(slot, match)})`.

Counts after this task: frontend **419 passed in 64 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/builder/hymns/scripture-matches.tsx 2>&1 | head -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/components/builder/hymns/scripture-matches.tsx': No such file or directory`; ` Test Files  64 passed (64)`, `      Tests  414 passed (414)`.

- [ ] **Step 2 (agent): Write the failing tests**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/components/builder/hymns/hymns-step.test.tsx", [
    ('''  hymnListRoute,
  hymnSuggestions,
''',
     '''  hymnListRoute,
  hymnMatch,
  hymnSuggestions,
'''),
    ('''  me,
  testDraft,
''',
     '''  me,
  scriptureMatches,
  testDraft,
'''),
    ('''    "GET /hymns": hymnListRoute(undefined, RECENT),
    ...routes,
''',
     '''    "GET /hymns": hymnListRoute(undefined, RECENT),
    "POST /hymns/scripture-matches": scriptureMatches(),
    ...routes,
'''),
])
with open("frontend/src/components/builder/hymns/hymns-step.test.tsx", "a", encoding="utf-8") as f:
    f.write(r'''
// --- Hymns for the readings (S "Hymns for the readings") ------------------------------------

const LINES = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

/** The section, opened (it starts closed below md, and jsdom's window is narrow). */
async function openMatches(user: { click: (el: Element) => Promise<void> }) {
  const trigger = await screen.findByRole("button", { name: /^Hymns for the readings/ });
  await user.click(trigger);
  return trigger.closest("[data-slot=collapsible]") as HTMLElement;
}

describe("Hymns for the readings (S ScriptureMatches)", () => {
  it("asks for the draft's readings in the selected hymnal; Add → Response hymn sets the slot and Undo restores it", async () => {
    const { user, api } = renderStep(draftWith(slots(null, pick(GRACE)), { scriptures: LINES }));
    const trigger = await screen.findByRole("button", { name: "Hymns for the readings 4" }); // the count, while closed
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    const matchCalls = api.requests.filter((r) => r.path === "/hymns/scripture-matches");
    expect(matchCalls.map((r) => r.body)).toEqual([
      { refs: LINES, hymnal: "GG2013", recent_for_date: "2026-10-04", max_results: 30 },
    ]);
    const section = await openMatches(user);
    const passage = within(section).getByRole("heading", { name: "Matches the readings" }).nextElementSibling as HTMLElement;
    expect(within(passage).getByText("#710 Here I Am, Lord")).toBeInTheDocument();
    expect(within(passage).getByText("Written 1981")).toBeInTheDocument();
    expect(within(passage).getByText("Matches Isaiah 5:1-7")).toBeInTheDocument();
    const chapter = within(section).getByRole("heading", { name: "Same chapter" }).nextElementSibling as HTMLElement;
    expect(within(chapter).getAllByRole("listitem")).toHaveLength(3);
    await user.click(within(section).getByRole("button", { name: "Add Holy, Holy, Holy! Lord God Almighty" }));
    await user.click(await screen.findByRole("menuitem", { name: "Response hymn" }));
    expect(await within(card("Response")).findByText("#1 Holy, Holy, Holy! Lord God Almighty")).toBeInTheDocument();
    await waitFor(() => expect(stored().hymns.slots.response).toEqual(pick(HOLY)));
    expect(await screen.findByText("Response hymn changed to Holy, Holy, Holy! Lord God Almighty.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Undo" }));
    await waitFor(() => expect(stored().hymns.slots.response).toEqual(pick(GRACE)));
    // Into an empty slot: no toast.
    await user.click(within(section).getByRole("button", { name: "Add Here I Am, Lord" }));
    await user.click(await screen.findByRole("menuitem", { name: "Closing hymn" }));
    await waitFor(() => expect(stored().hymns.slots.closing).toEqual(pick(HERE)));
    expect(screen.queryByText(/^Closing hymn changed/)).toBeNull();
  });

  it("searches an extra reference with the readings, and says when one can't be read or nothing matches", async () => {
    const { user, api } = renderStep(draftWith({}, { scriptures: LINES }), {
      "POST /hymns/scripture-matches": (req: RecordedRequest) => {
        const refs = (req.body as { refs: string[] }).refs;
        return refs.includes("Transfiguration")
          ? scriptureMatches({ refs_used: refs, unparsed_refs: ["Transfiguration"], total_matched: 0, items: [] })
          : scriptureMatches();
      },
    });
    const section = await openMatches(user);
    const extra = within(section).getByLabelText("Additional scripture");
    expect(extra).toHaveAttribute("placeholder", "e.g. Matthew 17");
    expect(extra).toHaveAttribute("maxLength", "200");
    await user.type(extra, "Transfiguration{Enter}");
    expect(
      await within(section).findByText("Couldn't read “Transfiguration” as a scripture reference."),
    ).toBeInTheDocument();
    expect(
      within(section).getByText("No hymns in GG2013 match these readings. Try a shorter reference, such as “Matthew 17”."),
    ).toBeInTheDocument();
    const last = api.requests.filter((r) => r.path === "/hymns/scripture-matches").at(-1);
    expect((last?.body as { refs: string[] }).refs).toEqual([...LINES, "Transfiguration"]);
  });

  it("links to step 1 without references, and never searches a hymnal with no scripture references", async () => {
    const first = renderStep();
    const section = await openMatches(first.user);
    expect(within(section).getByText(/^Add the readings in step 1, or type a scripture reference here\./)).toBeInTheDocument();
    expect(within(section).getByRole("link", { name: "Go to readings" })).toHaveAttribute("href", "/builder/readings");
    first.unmount();

    const { user, api } = renderStep(draftWith({ hymnal: "PH1990" }, { scriptures: LINES }), { "GET /hymnals": twoHymnals() });
    const ph = await openMatches(user);
    expect(within(ph).getByText("PH1990 has no scripture references, so it can't be searched by scripture.")).toBeInTheDocument();
    expect(api.requests.some((r) => r.path === "/hymns/scripture-matches")).toBe(false);
    expect(first.api.requests.some((r) => r.path === "/hymns/scripture-matches")).toBe(false);
  });

  it("shows Couldn't search the hymnal with Retry when the search fails", async () => {
    let fail = true;
    const { user } = renderStep(draftWith({}, { scriptures: LINES }), {
      "POST /hymns/scripture-matches": () => (fail ? fakeError(500, "internal_error", "Something went wrong.") : scriptureMatches()),
    });
    const section = await openMatches(user);
    expect(await within(section).findByText("Couldn't search the hymnal.")).toBeInTheDocument();
    fail = false;
    await user.click(within(section).getByRole("button", { name: "Retry" }));
    expect(await within(section).findByRole("heading", { name: "Matches the readings" })).toBeInTheDocument();
  });

  it("with Exclude on hides recently used matches behind Show them; shown, they carry their badge", async () => {
    const [holy, , come] = gg2013();
    const recentMatches = scriptureMatches({
      items: [
        hymnMatch({ ...holy, recent_use_on: "2026-09-06" }, "passage", ["Isaiah 5:1-7"]),
        hymnMatch(come, "chapter", ["Isaiah 5:1-7"]),
        hymnMatch({ ...FAITHFUL, recent_use_on: "2026-10-18" }, "chapter", ["Matthew 21:33-46"]),
      ],
    });
    const { user } = renderStep(draftWith({}, { scriptures: LINES }), { "POST /hymns/scripture-matches": recentMatches });
    const section = await openMatches(user);
    expect(await within(section).findByText("2 recently used matches are hidden.")).toBeInTheDocument();
    expect(within(section).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Hymns for the readings 1" })).toBeInTheDocument();
    await user.click(within(section).getByRole("button", { name: "Show them" }));
    expect(within(section).getAllByRole("listitem")).toHaveLength(3);
    expect(within(section).getByText("Used Sep 6")).toBeInTheDocument();
    expect(within(section).getByText("Planned Oct 18")).toBeInTheDocument();
    expect(within(section).queryByText(/recently used matches are hidden/)).toBeNull();
  });
});
''')

print("T11 tests written")
PYEOF
```

**Expected:** `T11 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/hymns/hymns-step.test.tsx 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × Hymns for the readings (S ScriptureMatches) > asks for the draft's readings in the selected hymnal; Add → Response hymn sets the slot and Undo restores it <t>ms
   × Hymns for the readings (S ScriptureMatches) > searches an extra reference with the readings, and says when one can't be read or nothing matches <t>ms
   × Hymns for the readings (S ScriptureMatches) > links to step 1 without references, and never searches a hymnal with no scripture references <t>ms
   × Hymns for the readings (S ScriptureMatches) > shows Couldn't search the hymnal with Retry when the search fails <t>ms
   × Hymns for the readings (S ScriptureMatches) > with Exclude on hides recently used matches behind Show them; shown, they carry their badge <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯
      Tests  5 failed | 20 passed (25)
```

- [ ] **Step 4 (agent): Write the matches section and put it in the step**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/components/builder/hymns/hymns-step.tsx", [
    ('''import { buttonVariants } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
''',
     '''import { buttonVariants } from "@/components/ui/button";
import type { Hymn, HymnMatch } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
'''),
    ('''import { selectHymnal } from "@/lib/hymns/hymnal";
import { duplicateNotice, MISSING_NOTICE, recentUseNotice } from "@/lib/hymns/labels";
import {
''',
     '''import { selectHymnal } from "@/lib/hymns/hymnal";
import { duplicateNotice, MISSING_NOTICE, recentUseNotice, SLOT_META } from "@/lib/hymns/labels";
import {
'''),
    ('''import { ExcludeSwitch, HymnalPicker, HymnsToolbar, ToolbarSkeleton } from "./hymns-toolbar";
import { SuggestHymnsButton } from "./suggest-hymns-button";
''',
     '''import { ExcludeSwitch, HymnalPicker, HymnsToolbar, ToolbarSkeleton } from "./hymns-toolbar";
import { ScriptureMatches } from "./scripture-matches";
import { SuggestHymnsButton } from "./suggest-hymns-button";
'''),
    (''' * and puts other ideas under each hymn; the ideas show only for the date they
 * were suggested for.
 */
''',
     ''' * and puts other ideas under each hymn; the ideas show only for the date they
 * were suggested for. "Hymns for the readings" matches the draft's scriptures
 * in the selected hymnal; adding one over another hymn offers Undo too.
 */
'''),
    ('''  const ideas = hymns.alternatives?.for_date_iso === dateIso ? hymns.alternatives.by_slot : null;
  const selectedCount = hymnals?.items.find((h) => h.code === code)?.hymn_count ?? 0;

''',
     '''  const ideas = hymns.alternatives?.for_date_iso === dateIso ? hymns.alternatives.by_slot : null;
  const selectedInfo = hymnals?.items.find((h) => h.code === code);
  const selectedCount = selectedInfo?.hymn_count ?? 0;

'''),
    ('''    showUndo(`Removed ${title}.`, () => update((d) => setSlot(d, slot, previous)));
  }
''',
     '''    showUndo(`Removed ${title}.`, () => update((d) => setSlot(d, slot, previous)));
  }

  function addMatch(slot: Slot, match: HymnMatch) {
    const previous = hymns.slots[slot];
    update((d) => setSlot(d, slot, pickFromHymn(match)));
    if (previous && previous.hymn_id !== match.id) {
      showUndo(`${SLOT_META[slot].title} changed to ${match.title}.`, () => update((d) => setSlot(d, slot, previous)));
    }
  }
'''),
    ('''      })}
      <p className="text-xs text-muted-foreground">
''',
     '''      })}
      {pickers && selectedInfo ? (
        <ScriptureMatches
          scriptures={draft.readings.scriptures}
          hymnal={selectedInfo}
          recentForDate={recentForDate}
          serviceDateIso={dateIso}
          excludeRecent={excludeRecent}
          showHymnal={showHymnal}
          onAdd={addMatch}
        />
      ) : null}
      <p className="text-xs text-muted-foreground">
'''),
])

Path("frontend/src/components/builder/hymns/scripture-matches.tsx").write_text('''"use client";

import { ChevronDownIcon } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import type { HymnalSummary, HymnMatch } from "@/lib/api/types";
import { SLOTS, type Slot } from "@/lib/draft/schema";
import { recentUseLabel, SLOT_META } from "@/lib/hymns/labels";
import { buildMatchRefs, MAX_REF_LENGTH } from "@/lib/hymns/match-request";
import { useScriptureMatches } from "@/lib/queries/hymns";
import { cn } from "@/lib/utils";

import { HymnLabel } from "./hymn-label";

/** Open from `md` (48rem), closed below it, as the section first renders (S; plan clarification 19). */
function openAtFirst(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(min-width: 48rem)").matches;
}

/** "{k} recently used matches are hidden." (S); "1 recently used match is hidden." for one (plan clarification 13). */
function hiddenMatchesText(k: number): string {
  return k === 1 ? "1 recently used match is hidden." : `${k} recently used matches are hidden.`;
}

/** One match: its label (with "Used Sep 7" when it is shown although recently used), what it matched, and Add. */
function MatchRow({
  match,
  serviceDateIso,
  showHymnal,
  onAdd,
}: {
  match: HymnMatch;
  serviceDateIso: string;
  showHymnal: boolean;
  onAdd: (slot: Slot) => void;
}) {
  const recent = match.recent_use_on ? recentUseLabel(match.recent_use_on, serviceDateIso) : null;
  return (
    <li className="flex items-center gap-2 py-1.5">
      <div className="grid min-w-0 flex-1 gap-0.5">
        <HymnLabel hymn={match} showHymnal={showHymnal} recentBadge={recent} listen />
        <p className="text-xs text-muted-foreground wrap-anywhere">Matches {match.matched_refs.join(", ")}</p>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Add ${match.title}`}
          className={cn(buttonVariants({ variant: "outline", size: "touch" }), "shrink-0")}
        >
          Add
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-auto min-w-44">
          {SLOTS.map((slot) => (
            <DropdownMenuItem key={slot} onClick={() => onAdd(slot)} className="min-h-11 md:min-h-8">
              {SLOT_META[slot].title}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}

/**
 * "Hymns for the readings" (S `ScriptureMatches`): the draft's scriptures and
 * an extra reference typed here (component state only), matched in the
 * selected hymnal. The request runs by itself whenever the references, the
 * hymnal or the date change, also while the section is closed, so its count
 * shows. Results come in two groups; each row's Add puts the hymn in a slot.
 * With Exclude on, recently used matches are hidden behind "Show them".
 */
export function ScriptureMatches({
  scriptures,
  hymnal,
  recentForDate,
  serviceDateIso,
  excludeRecent,
  showHymnal,
  onAdd,
}: {
  scriptures: readonly string[];
  /** The selected hymnal, with its scripture count. */
  hymnal: HymnalSummary;
  recentForDate: string | null;
  serviceDateIso: string;
  excludeRecent: boolean;
  showHymnal: boolean;
  onAdd: (slot: Slot, match: HymnMatch) => void;
}) {
  const [open, setOpen] = useState(openAtFirst);
  const [typed, setTyped] = useState("");
  const [extra, setExtra] = useState("");
  const [showRecent, setShowRecent] = useState(false);
  const refs = buildMatchRefs(scriptures, extra);
  const searchable = hymnal.scripture_ref_count > 0;
  const query = useScriptureMatches({ refs, hymnal: hymnal.code, recentForDate, enabled: searchable });
  const data = searchable && refs.length > 0 ? query.data : undefined;
  const hideRecent = excludeRecent && !showRecent;
  const all = data?.items ?? [];
  const items = hideRecent ? all.filter((m) => m.recent_use_on === null) : all;
  const hidden = all.length - items.length;
  const groups = [
    { title: "Matches the readings", items: items.filter((m) => m.strength === "passage") },
    { title: "Same chapter", items: items.filter((m) => m.strength === "chapter") },
  ].filter((g) => g.items.length > 0);

  function submit(event: FormEvent) {
    event.preventDefault();
    setExtra(typed);
  }

  let body;
  if (!searchable) {
    body = (
      <p className="text-sm text-muted-foreground">
        {hymnal.code} has no scripture references, so it can&apos;t be searched by scripture.
      </p>
    );
  } else if (refs.length === 0) {
    body = (
      <p className="text-sm text-muted-foreground">
        Add the readings in step 1, or type a scripture reference here.{" "}
        <Link href="/builder/readings" className="font-medium text-foreground underline underline-offset-4">
          Go to readings
        </Link>
      </p>
    );
  } else if (query.isError && !data) {
    body = (
      <ErrorState
        error={query.error}
        message="Couldn't search the hymnal."
        retrying={query.isFetching}
        onRetry={() => void query.refetch()}
      />
    );
  } else if (!data) {
    body = (
      <div role="status" aria-label="Searching the hymnal" className="grid gap-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  } else {
    body = (
      <div className="grid gap-3">
        {data.unparsed_refs.map((ref) => (
          <p key={ref} className="text-sm text-muted-foreground wrap-anywhere">
            Couldn&apos;t read “{ref}” as a scripture reference.
          </p>
        ))}
        {all.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hymns in {hymnal.code} match these readings. Try a shorter reference, such as “Matthew 17”.
          </p>
        ) : null}
        {groups.map((group) => (
          <div key={group.title} className="grid gap-1">
            <h4 className="text-sm font-medium">{group.title}</h4>
            <ul className="divide-y">
              {group.items.map((match) => (
                <MatchRow
                  key={match.id}
                  match={match}
                  serviceDateIso={serviceDateIso}
                  showHymnal={showHymnal}
                  onAdd={(slot) => onAdd(slot, match)}
                />
              ))}
            </ul>
          </div>
        ))}
        {hidden > 0 ? (
          <p className="text-sm text-muted-foreground">
            {hiddenMatchesText(hidden)}{" "}
            <Button variant="link" className="h-11 px-0" onClick={() => setShowRecent(true)}>
              Show them
            </Button>
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="grid gap-3 rounded-lg border p-4">
      <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-base font-medium">
        <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
        <span>Hymns for the readings</span>
        {data ? <Badge variant="secondary">{items.length}</Badge> : null}
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-3">
        <form onSubmit={submit} className="grid gap-1.5">
          <Label htmlFor="extra-scripture">Additional scripture</Label>
          <div className="flex gap-2">
            <Input
              id="extra-scripture"
              value={typed}
              maxLength={MAX_REF_LENGTH}
              placeholder="e.g. Matthew 17"
              className="h-11"
              onChange={(event) => setTyped(event.target.value)}
            />
            <Button type="submit" variant="outline" size="touch">
              Search
            </Button>
          </div>
        </form>
        {body}
      </CollapsibleContent>
    </Collapsible>
  );
}
''', encoding="utf-8")

print("T11 code written")
PYEOF
```

**Expected:** `T11 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/hymns 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  2 passed (2)`, `      Tests  27 passed (27)`; ` Test Files  64 passed (64)`, `      Tests  419 passed (419)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `hymns-step.tsx` and `hymns-step.test.tsx`, `??` for `scripture-matches.tsx`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/hymns/scripture-matches.tsx frontend/src/components/builder/hymns/hymns-step.tsx frontend/src/components/builder/hymns/hymns-step.test.tsx
git commit -m "Hymns: Hymns for the readings, grouped, with an extra reference and Add to a slot (S ScriptureMatches; Behavior changes 9, 10, 19)" -m "The draft's readings plus a typed reference (buildMatchRefs) are matched
in the selected hymnal whenever they, the hymnal or the date change, and
shown as Matches the readings and Same chapter. Add puts a hymn in a
slot, with Undo when it replaced another. Recently used matches hide
behind Show them while Exclude is on. Unreadable references, no matches,
no references (Go to readings), a hymnal with no scripture references
and a failed search each have their copy. Frontend 414 -> 419 tests.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 3 files changed.

**Review checkpoint (T10-T11, batch 5):** an AI answer is applied only through `applySuggestions` in a functional update and only for the request's date; a superseded or cancelled request changes nothing and shows nothing; no error text from the server's 5xx is shown inline; the ideas show only for the draft's date and hide when their hymn is gone; the matches never send more than 20 references of 200 characters and never search a hymnal with no scripture references; every Undo goes through `useUndoToasts`.

### Task 12: Turn the step on: `"hymns"` ships, its route renders the step, Still needed and the summary list the hymns (S "Builder shell", "Builder shell: Hymns status and summary"; F §4.7; AC10; clarifications 1, 16)

`SHIPPED_STEPS` gains `"hymns"`, so the step bar shows Hymns as "n of 3" (filled slots; a pick shown as "Not in your hymnal" still counts), then "Complete", instead of "Soon" (`stepStatus` already counts the slots, 2b). `stillNeeded` adds one row per empty slot in slot order, "No Opening hymn — Choose one" and so on, each linking to `/builder/hymns`. The summary's Hymns block becomes `SummaryHymns`: three rows from the draft's snapshot only ("Opening · #403 Come, Thou Almighty King", or muted "No Opening hymn"), so the shell never loads a hymnal on other steps; Liturgy keeps "Available soon". `/builder/hymns` renders `HymnsStep` instead of `StepPlaceholder`, which stays for Liturgy and Review. S puts the summary cases in `summary-panel.test.tsx`; 2c tested the summary in `builder-shell.test.tsx`, so this task extends that file (clarification 1). The shell tests now answer `GET /hymnals` and `GET /hymns`, since the hymns route loads the real step.

**Files:**
- Create: `frontend/src/components/builder/summary-hymns.tsx`
- Modify: `frontend/src/lib/draft/steps.ts`, `frontend/src/lib/draft/status.ts` (`stillNeeded`), `frontend/src/components/builder/summary-panel.tsx`, `frontend/src/components/builder/step-placeholder.tsx` (comment), `frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx`
- Test: `frontend/src/lib/draft/status.test.ts` (+1; two tests edited), `frontend/src/components/builder/builder-shell.test.tsx` (+1; three tests edited)

**Interfaces:**
- Consumes: `HymnsStep` (T8-T11), `SLOT_META`, `hymnText` (T5), `stepStatus`, `StepProgress`, `StillNeeded`, `SummaryPanel` (2b, 2c).
- Produces: `SHIPPED_STEPS = new Set(["readings", "hymns"])`; `stillNeeded` hymn rows `{step: "hymns", message: "No {Opening|Response|Closing} hymn", action: "Choose one"}`; `SummaryHymns()`. Later users: slice 4 (adds `"liturgy"`), 5a (`"review"`).

Counts after this task: frontend **421 passed in 64 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);`; ` Test Files  64 passed (64)`, `      Tests  419 passed (419)`.

- [ ] **Step 2 (agent): Write the failing tests**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/components/builder/builder-shell.test.tsx", [
    ('''import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi } from "@/test/fake-api";
''',
     '''import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { installFakeApi } from "@/test/fake-api";
'''),
    ('''  DRAFT_NOW,
  lectionary,
''',
     '''  DRAFT_NOW,
  gg2013,
  hymnals,
  hymnListRoute,
  lectionary,
'''),
    ('''function renderBuilder(page: ReactElement, path: string, lookup = lectionaryRoute()) {
  installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lookup, "GET /translations": translations() });
  return renderWithProviders(<BuilderLayout>{page}</BuilderLayout>, { me: me(), church: church(), path });
''',
     '''function renderBuilder(page: ReactElement, path: string, lookup = lectionaryRoute()) {
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lookup,
    "GET /translations": translations(),
    "GET /hymnals": hymnals(),
    "GET /hymns": hymnListRoute(),
  });
  return renderWithProviders(<BuilderLayout>{page}</BuilderLayout>, { me: me(), church: church(), path });
'''),
    ('''        "1 Date & readings 1 of 3", // shipped in 2c: a date, no occasion, no readings
        "2 Hymns Soon",
        "3 Liturgy Soon",
''',
     '''        "1 Date & readings 1 of 3", // shipped in 2c: a date, no occasion, no readings
        "2 Hymns 0 of 3", // shipped in 3b: no hymn chosen
        "3 Liturgy Soon",
'''),
    ('''        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else {
''',
     '''        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else if (number === 2) {
        // Hymns is the real step from slice 3b.
        expect(within(card).getByText("Choose an opening, response and closing hymn.")).toBeInTheDocument();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else {
'''),
    ('''      expect(links.map((link) => link.textContent)).toEqual(footer);
      // Review lists what the shipped step still needs; the other steps do not.
      if (number === 4) {
''',
     '''      expect(links.map((link) => link.textContent)).toEqual(footer);
      // Review lists what the shipped steps still need; the other steps do not.
      if (number === 4) {
'''),
    ('''          "No scripture readings — Add one",
        ]);
      } else {
''',
     '''          "No scripture readings — Add one",
          "No Opening hymn — Choose one",
          "No Response hymn — Choose one",
          "No Closing hymn — Choose one",
        ]);
        const links = within(needed).getAllByRole("link").map((link) => link.getAttribute("href"));
        expect(links).toEqual(["/builder/readings", "/builder/readings", "/builder/hymns", "/builder/hymns", "/builder/hymns"]);
      } else {
'''),
    ('''
  it("shows the summary: the date and occasion, the readings, Available soon for the rest, and where the draft is kept", async () => {
    // A controllable (min-width: 64rem) query, so the test can widen the window past lg.
''',
     '''
  it("shows the summary: the date and occasion, the readings, the hymns, Available soon for liturgy, and where the draft is kept", async () => {
    // A controllable (min-width: 64rem) query, so the test can widen the window past lg.
'''),
    ('''    expect(readings?.nextElementSibling).toHaveTextContent(/^No readings yet$/);
    for (const block of ["Hymns", "Liturgy"]) {
      const heading = within(aside).getByRole("link", { name: block }).closest("h3");
      expect(heading?.nextElementSibling).toHaveTextContent(/^Available soon$/);
    }
    expect(within(aside).getByRole("link", { name: "Date" })).toHaveAttribute("href", "/builder/readings");
''',
     '''    expect(readings?.nextElementSibling).toHaveTextContent(/^No readings yet$/);
    const hymnsBlock = within(aside).getByRole("link", { name: "Hymns" }).closest("h3");
    expect(hymnsBlock?.nextElementSibling).toHaveTextContent(/^No Opening hymnNo Response hymnNo Closing hymn$/);
    const liturgy = within(aside).getByRole("link", { name: "Liturgy" }).closest("h3");
    expect(liturgy?.nextElementSibling).toHaveTextContent(/^Available soon$/);
    expect(within(aside).getByRole("link", { name: "Date" })).toHaveAttribute("href", "/builder/readings");
'''),
    ('''    expect(within(aside).getByText("Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    expect(within(aside).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Isaiah 5:1-7OT (auto)",
''',
     '''    expect(within(aside).getByText("Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    const readingsBlock = within(aside).getByRole("link", { name: "Readings" }).closest("h3")?.nextElementSibling as HTMLElement;
    expect(within(readingsBlock).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Isaiah 5:1-7OT (auto)",
'''),
])
with open("frontend/src/components/builder/builder-shell.test.tsx", "a", encoding="utf-8") as f:
    f.write('''
describe("the shell with Hymns shipped (slice 3b)", () => {
  it("counts Hymns n of 3, then Complete, and the summary lists the three slots in the column and the sheet", async () => {
    const [, praise, come, grace] = gg2013();
    seed(setSlot(setSlot(testDraft(), "opening", pickFromHymn(come)), "closing", pickFromHymn(praise)));
    function FillResponse() {
      const { update } = useDraft();
      return (
        <button type="button" onClick={() => update((d) => setSlot(d, "response", pickFromHymn(grace)))}>
          Fill Response
        </button>
      );
    }
    const { user } = renderBuilder(
      <>
        <ReviewStepPage />
        <FillResponse />
      </>,
      "/builder/review",
    );
    const progress = await screen.findByRole("navigation", { name: "Steps" });
    expect(within(progress).getAllByRole("link")[1]).toHaveTextContent("2 Hymns 2 of 3");
    const aside = screen.getByRole("complementary", { name: "Summary" });
    const hymnsBlock = within(aside).getByRole("link", { name: "Hymns" }).closest("h3")?.nextElementSibling as HTMLElement;
    expect(within(hymnsBlock).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Opening · #403 Come, Thou Almighty King",
      "No Response hymn",
      "Closing · #35 Praise, My Soul, the King of Heaven",
    ]);
    expect(within(aside).getByRole("link", { name: "Hymns" })).toHaveAttribute("href", "/builder/hymns");
    expect(hymnsBlock).not.toHaveTextContent("Available soon");
    const needed = screen.getByRole("region", { name: "Still needed" });
    expect(within(needed).getAllByRole("listitem").map((li) => li.textContent)).toContain("No Response hymn — Choose one");

    await user.click(screen.getByRole("button", { name: "Fill Response" }));
    await waitFor(() => expect(within(progress).getAllByRole("link")[1]).toHaveTextContent("2 Hymns Complete"));
    expect(within(needed).queryByText(/hymn — Choose one/)).toBeNull();
    // Below lg the same rows show in the bottom sheet.
    await user.click(screen.getByRole("button", { name: "Summary" }));
    const sheet = await screen.findByRole("dialog", { name: "Summary" });
    expect(within(sheet).getByText("Response · #649 Amazing Grace")).toBeInTheDocument();
    expect(within(sheet).getByText("Opening · #403 Come, Thou Almighty King")).toBeInTheDocument();
  });
});
''')

edit("frontend/src/lib/draft/status.test.ts", [
    ('''describe("steps (S steps.ts)", () => {
  it("lists the four steps in order, ships Date & readings (2c), and reads a step from its path", () => {
    expect(STEPS.map((s) => [s.number, s.label, s.href, s.previous, s.next])).toEqual([
''',
     '''describe("steps (S steps.ts)", () => {
  it("lists the four steps in order, ships Date & readings (2c) and Hymns (3b), and reads a step from its path", () => {
    expect(STEPS.map((s) => [s.number, s.label, s.href, s.previous, s.next])).toEqual([
'''),
    ('''    ]);
    expect([...SHIPPED_STEPS]).toEqual(["readings"]);
    expect(stepById("liturgy").label).toBe("Liturgy");
''',
     '''    ]);
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns"]);
    expect(stepById("liturgy").label).toBe("Liturgy");
'''),
    ('''    const d = testDraft();
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "soon", "soon", "not_in_archive"]);
    expect(stepStatus(d, "readings", new Set())).toEqual({ kind: "soon" });
''',
     '''    const d = testDraft();
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "incomplete", "soon", "not_in_archive"]);
    expect(stepStatus(d, "readings", new Set())).toEqual({ kind: "soon" });
'''),
    ('''    expect(stillNeeded(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), READINGS)).toEqual([]);
  });
});
''',
     '''    expect(stillNeeded(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), READINGS)).toEqual([]);
  });

  it("counts the hymns step n of 3 and lists each empty slot once it ships (slice 3b)", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const withSlots = (slots: Partial<DraftV1["hymns"]["slots"]>) => ({
      ...filled,
      hymns: { ...filled.hymns, slots: { ...filled.hymns.slots, ...slots } },
    });
    expect(stepStatus(filled, "hymns")).toEqual({ kind: "incomplete", done: 0, total: 3 });
    expect(stepStatus(withSlots({ opening: HYMN, closing: HYMN }), "hymns")).toEqual({ kind: "incomplete", done: 2, total: 3 });
    const archived = { ...HYMN, hymn_id: null }; // shown as "Not in your hymnal", still a pick
    const all = withSlots({ opening: HYMN, response: archived, closing: HYMN });
    expect(stepStatus(all, "hymns")).toEqual({ kind: "complete" });
    expect(stillNeeded(filled)).toEqual([
      { step: "hymns", message: "No Opening hymn", action: "Choose one" },
      { step: "hymns", message: "No Response hymn", action: "Choose one" },
      { step: "hymns", message: "No Closing hymn", action: "Choose one" },
    ]);
    expect(stillNeeded(withSlots({ response: HYMN }))).toEqual([
      { step: "hymns", message: "No Opening hymn", action: "Choose one" },
      { step: "hymns", message: "No Closing hymn", action: "Choose one" },
    ]);
    expect(stillNeeded(all)).toEqual([]);
    expect(stillNeeded(filled, READINGS)).toEqual([]); // before 3b: no hymn rows
    expect(stillNeeded(filled).some((item) => item.step === "liturgy")).toBe(false); // liturgy not shipped
  });
});
'''),
])

print("T12 tests written")
PYEOF
```

**Expected:** `T12 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × steps (S steps.ts) > lists the four steps in order, ships Date & readings (2c) and Hymns (3b), and reads a step from its path <t>ms
   × stepStatus (F §4.7) > shows Soon for unshipped steps and Not in archive for Review <t>ms
   × stillNeeded (S Review "Still needed") > counts the hymns step n of 3 and lists each empty slot once it ships (slice 3b) <t>ms
   × builder shell (F §4.7) > renders each step route inside the shell: progress, the step or its placeholder card, and the footer links <t>ms
   × builder shell (F §4.7) > shows the summary: the date and occasion, the readings, the hymns, Available soon for liturgy, and where the draft is kept <t>ms
   × the shell with Hymns shipped (slice 3b) > counts Hymns n of 3, then Complete, and the summary lists the three slots in the column and the sheet <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 6 ⎯⎯⎯⎯⎯⎯⎯
      Tests  6 failed | 14 passed (20)
```

- [ ] **Step 4 (agent): Ship the step**

Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path


def edit(path: str, pairs: list[tuple[str, str]]) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")


edit("frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx", [
    ('''
import { StepPlaceholder } from "@/components/builder/step-placeholder";

/** Step: Hymns. Slice 3 replaces the placeholder. */
export default function HymnsStepPage() {
  return <StepPlaceholder step="hymns" />;
}
''',
     '''
import { HymnsStep } from "@/components/builder/hymns/hymns-step";

/** Step: Hymns (slice 3b). */
export default function HymnsStepPage() {
  return <HymnsStep />;
}
'''),
])

edit("frontend/src/components/builder/step-placeholder.tsx", [
    (''' * F §4.7). Slice 2b also used it for Date & readings until slice 2c (owner
 * answer Q1, 2026-09-28). Slices 3, 4 and 5a each replace their step's use,
 * and 5a deletes this component. No link to the old app (owner answer Q2).
 */
''',
     ''' * F §4.7). Slice 2b also used it for Date & readings until slice 2c (owner
 * answer Q1, 2026-09-28), and Hymns used it until slice 3b. Slices 4 and 5a
 * replace their steps' use, and 5a deletes this component. No link to the old
 * app (owner answer Q2).
 */
'''),
])

Path("frontend/src/components/builder/summary-hymns.tsx").write_text('''"use client";

import { useDraft } from "@/lib/draft/context";
import { SLOTS } from "@/lib/draft/schema";
import { hymnText, SLOT_META } from "@/lib/hymns/labels";

/**
 * The summary's Hymns block (slice 3 S "Builder shell"; F §4.7): the three
 * slots in order, "Opening · #403 Come, Thou Almighty King" or, muted, "No
 * Opening hymn". It reads only the draft's snapshot, so the shell never loads
 * a hymnal on other steps.
 */
export function SummaryHymns() {
  const { draft } = useDraft();
  return (
    <ul className="grid gap-1">
      {SLOTS.map((slot) => {
        const pick = draft.hymns.slots[slot];
        const name = SLOT_META[slot].name;
        return pick ? (
          <li key={slot} className="wrap-anywhere text-foreground">
            {name} · {hymnText(pick)}
          </li>
        ) : (
          <li key={slot}>No {name} hymn</li>
        );
      })}
    </ul>
  );
}
''', encoding="utf-8")

edit("frontend/src/components/builder/summary-panel.tsx", [
    ('''import { splitAlternatives } from "@/lib/scripture-refs";

''',
     '''import { splitAlternatives } from "@/lib/scripture-refs";

import { SummaryHymns } from "./summary-hymns";

'''),
    (''' * `lg`, the bottom sheet below it. Each block links to its step. The Readings
 * block and the occasion line show once "readings" ships (slice 2c); slices 3
 * and 4 replace the Hymns and Liturgy blocks, and 5a wires the archive half
 * of the status line.
 */
''',
     ''' * `lg`, the bottom sheet below it. Each block links to its step. The Readings
 * block and the occasion line show once "readings" ships (slice 2c), the three
 * hymns once "hymns" ships (slice 3b); slice 4 replaces the Liturgy block, and
 * 5a wires the archive half of the status line.
 */
'''),
    ('''  const readingsShipped = shipped.has("readings");
  const lines = cleanScriptures(draft);
''',
     '''  const readingsShipped = shipped.has("readings");
  const hymnsShipped = shipped.has("hymns");
  const lines = cleanScriptures(draft);
'''),
    ('''      <Block title="Hymns" step="hymns" onNavigate={onNavigate}>
        <Soon />
      </Block>
''',
     '''      <Block title="Hymns" step="hymns" onNavigate={onNavigate}>
        {hymnsShipped ? <SummaryHymns /> : <Soon />}
      </Block>
'''),
])

edit("frontend/src/lib/draft/status.ts", [
    ('''
import { SECTION_KEYS, SLOTS, type DraftV1, type StepId } from "./schema";
import { SHIPPED_STEPS } from "./steps";
''',
     '''
import { SECTION_KEYS, SLOTS, type DraftV1, type Slot, type StepId } from "./schema";
import { SHIPPED_STEPS } from "./steps";
'''),
    ('''
export type NeededItem = {
''',
     '''
/** The slot names in "No Opening hymn" (the same words as `lib/hymns/labels.ts` `SLOT_META`). */
const SLOT_NAMES: Record<Slot, string> = { opening: "Opening", response: "Response", closing: "Closing" };

export type NeededItem = {
'''),
    ('''
/** What Review lists under "Still needed", from shipped steps only; slices 3 and 4 add their rows. */
export function stillNeeded(draft: DraftV1, shipped: ReadonlySet<StepId> = SHIPPED_STEPS): NeededItem[] {
''',
     '''
/**
 * What Review lists under "Still needed", from shipped steps only: the
 * readings' gaps (2c), then one row per empty hymn slot in slot order (3b,
 * F §4.7's wording). Slice 4 adds the liturgy's rows.
 */
export function stillNeeded(draft: DraftV1, shipped: ReadonlySet<StepId> = SHIPPED_STEPS): NeededItem[] {
'''),
    ('''  }
  return items;
''',
     '''  }
  if (shipped.has("hymns")) {
    for (const slot of SLOTS) {
      if (draft.hymns.slots[slot] !== null) continue;
      items.push({ step: "hymns", message: `No ${SLOT_NAMES[slot]} hymn`, action: "Choose one" });
    }
  }
  return items;
'''),
])

edit("frontend/src/lib/draft/steps.ts", [
    (''' * in archive"), and `stillNeeded` ignores it. Slice 2b shipped none (owner
 * answer Q1, 2026-09-28); slice 2c ships "readings". Slice 3 adds "hymns",
 * slice 4 "liturgy", 5a "review".
 */
''',
     ''' * in archive"), and `stillNeeded` ignores it. Slice 2b shipped none (owner
 * answer Q1, 2026-09-28); slice 2c ships "readings" and slice 3b "hymns".
 * Slice 4 adds "liturgy", 5a "review".
 */
'''),
    ('''
export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);

''',
     '''
export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns"]);

'''),
])

print("T12 code written")
PYEOF
```

**Expected:** `T12 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/components/builder 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  7 passed (7)`, `      Tests  87 passed (87)`; ` Test Files  64 passed (64)`, `      Tests  421 passed (421)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; seven ` M` files and `?? frontend/src/components/builder/summary-hymns.tsx`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/draft/steps.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/components/builder/summary-hymns.tsx frontend/src/components/builder/summary-panel.tsx frontend/src/components/builder/step-placeholder.tsx frontend/src/components/builder/builder-shell.test.tsx 'frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx'
git commit -m "Builder: Hymns ships; the step bar, Still needed and the summary show the three hymns (F §4.7; S Builder shell; AC10)" -m "SHIPPED_STEPS holds \"hymns\", so the step bar counts the filled slots
(n of 3, then Complete), Review lists No Opening hymn and the like for
each empty slot, and the summary lists Opening, Response and Closing
from the draft's snapshot (No ... hymn when empty). /builder/hymns
renders the Hymns step; Liturgy and Review keep Available soon.
Frontend 419 -> 421 tests in 64 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 8 files changed.

**Review checkpoint (T12):** only `"readings"` and `"hymns"` are shipped; Liturgy still shows "Soon" and "Available soon" with no link; `SummaryHymns` reads the draft only (no query); the shell tests assert the new rows rather than dropping the old checks.

### Task 13: Docs: the "(3b plan)" notes in S, one F amendment row, the slice 3 checklist and its heading pin (S top, Toolbar, Hymns for the readings, Backend 3.6, Frontend changes, Testing, Manual checks; F Amendments, §4.7; owner answers 1, 3, 5; clarifications 1-7, 9, 10, 13, 14, 17, 21)

S and F are what slices 4, 5a and 6a will read, so they must say what 3b built. S gains the marker sentence and fourteen "(3b plan)" notes; F gains one amendment row and a note in §4.7. `docs/manual-verification.md` gains "## Slice 3" (S's ten checks, check 11 for the church season, check 12 for "New service", and "(owner, after 3b)" on the items the guided check covers), and `backend/tests/test_slice1_docs.py`, which pins the file's last three `##` headings, pins the last four (clarification 17). No code changes.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`
- Test: none new; `backend/tests/test_ops_workflows.py`, `test_slice1_docs.py` and `test_docs.py` must still pass (89).

**Interfaces:**
- Consumes: the clarifications above and the code of T2-T12.
- Produces: S and F as later slices read them; the checklist T15 runs from.

Counts after this task: frontend **421 passed in 64 files**; backend **1110 passed, 11 skipped**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "(3b plan" docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md
grep -c "^## Slice 3$" docs/manual-verification.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); `0` (grep exits 1); `89 passed in <t>s`.

- [ ] **Step 2 (agent): Apply the S, F and docs-test edits**

Each anchor must match exactly once, or the script stops before writing that file. Run this script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path

S = Path("docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md")
F = Path("docs/superpowers/specs/2026-09-25-migration-foundations-design.md")
T1DOCS = Path("backend/tests/test_slice1_docs.py")


def edit(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


edit(S, [
    ('Changes made while building 3a (the plan\'s "Build notes (3a build)") are marked "(3a build)".\n',
     'Changes made while building 3a (the plan\'s "Build notes (3a build)") are marked "(3a build)". Notes from '
     'planning 3b (`docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md`, 2026-09-29) are marked "(3b plan)"; '
     'the owner\'s answers of that day are its owner answers 1-5.\n'),
    ("while it loads the toolbar shows skeletons, and on error the `ErrorState` below applies, so nothing is resolved "
     "from missing data.\n",
     "while it loads the toolbar shows skeletons, and on error the `ErrorState` below applies, so nothing is resolved "
     "from missing data. (3b plan: the skeletons show until `GET /hymnals` answers; the hymn lists are asked for only "
     "after it, and not at all for a church with no hymnals, whose picks show \"Not in your hymnal\" at once. A date "
     "change refetches the list without hiding the toolbar, so a pending suggestion is not lost.)\n"),
    ('  - When on and `n > 0` hidden hymns in the selected hymnal: "{n} hymns are hidden."\n',
     '  - When on and `n > 0` hidden hymns in the selected hymnal: "{n} hymns are hidden." (3b plan: "1 hymn is '
     'hidden." for one; likewise "1 more used within 12 weeks is hidden.", "1 recently used match is hidden." and '
     '" 1 recently used hymn was left out.")\n'),
    ('If the slot was filled, the toast "{Slot} hymn changed to {title}." offers **Undo**.\n',
     'If the slot was filled, the toast "{Slot} hymn changed to {title}." offers **Undo**. (3b plan: the button is '
     'named "Add {title}" for screen readers, and the toast shows only when the slot held another hymn.)\n'),
    ('"{k} recently used matches are hidden. [Show them]", a local toggle. With exclusion off, they show a badge.\n',
     '"{k} recently used matches are hidden. [Show them]", a local toggle. With exclusion off, they show a badge. '
     '(3b plan: matches shown with **Show them** carry the badge too.)\n'),
    ("     - `OCCASION`, `SCRIPTURE READINGS`, `NEW TESTAMENT READING` and `NT PASSAGE TEXT (excerpt)` (parity fields); "
     "(3a build: the NT reading is put on one line and clipped to 200 characters, so a reference cannot add lines to "
     "the prompt);\n",
     "     - `OCCASION`, `SCRIPTURE READINGS`, `NEW TESTAMENT READING` and `NT PASSAGE TEXT (excerpt)` (parity fields); "
     "(3a build: the NT reading is put on one line and clipped to 200 characters, so a reference cannot add lines to "
     "the prompt); (3b plan, owner answer 3: `CHURCH SEASON: {season}` follows `OCCASION`, computed on the server "
     "from the service date by `vanderbilt_lectionary.church_season`, and a `SEASON:` line after PREFERENCES asks the "
     "model to avoid Advent, Christmas, Palm Sunday and Holy Week or Easter hymns outside their season unless the "
     "readings or occasion call for them; the 24 000-character budget is unchanged);\n"),
    ("src/components/ui/{combobox,switch,badge,alert}.tsx   generated: npx shadcn@latest add combobox switch badge alert\n",
     "src/components/ui/{combobox,switch,badge,alert}.tsx   generated: npx shadcn@latest add combobox switch badge alert\n"
     "                                                      (3b plan: combobox, badge and alert exist already; switch\n"
     "                                                      is rebuilt from the upstream source, the registry being\n"
     "                                                      blocked, as in 2b and 2c)\n"),
    ("                                                      The timezone picker is slice 1's TimezoneCombobox (6a reuses that), not\n"
     "                                                      this component\n",
     "                                                      The timezone picker is slice 1's TimezoneCombobox (6a reuses that), not\n"
     "                                                      this component (3b plan: slice 1 used the Combobox directly,\n"
     "                                                      so 3b creates it; the caller ranks the rows)\n"),
    ('src/lib/dates.ts            + formatShortDate(iso) -> "Sep 7" (adds the year when it differs from the service year)\n',
     'src/lib/dates.ts            + formatShortDate(iso) -> "Sep 7" (adds the year when it differs from the service year)\n'
     '                            (3b plan: named formatAbbrevDate(iso, contextIso); 2b\'s formatShortDate already\n'
     '                            returns "October 4")\n'),
    ("- Changing `slots` or `hymnal` does mark it dirty, which is correct because both are archived in 5a. Only user "
     "actions change them.\n",
     "- Changing `slots` or `hymnal` does mark it dirty, which is correct because both are archived in 5a. Only user "
     "actions change them. (3b plan, owner answer 1: `isPristine` now counts `hymnal` as it counted the slots, so "
     "\"New service\" asks first and the roll-forward keeps the date; `setHymnal` stores `null` when the member "
     "chooses the church's effective hymnal, so switching away and back is not unsaved work. `exclude_recent` and "
     "`alternatives` count nowhere.)\n"),
    ("- `reconcilePick(pick, lists: Map<hymnal, HymnOut[] | undefined>)` returns one of:\n",
     "- `reconcilePick(pick, lists: Map<hymnal, HymnOut[] | undefined>)` returns one of (3b plan: a third argument, "
     "the selected hymnal, is used for a pick with no hymnal; the draft recipes `setSlot`, `clearSlot`, `setHymnal` "
     "and `setExcludeRecent` take the whole draft):\n"),
    ("### `buildSuggestionRequest(draft, selectedHymnal, getCachedPassage)`\n",
     "### `buildSuggestionRequest(draft, selectedHymnal, getCachedPassage)`\n\n"
     "(3b plan: a fourth argument, the church's `effective_translation`, since the function is pure.)\n"),
    ("- The client uses `createLatestTracker` (`src/lib/latest.ts`), so an older response never overwrites a newer one.\n",
     "- The client uses `createLatestTracker` (`src/lib/latest.ts`), so an older response never overwrites a newer one.\n"
     "- (3b plan: the tracker, the church check and the mount check live in `useSuggestHymns`, whose `suggest()` "
     "resolves `ok`, `error` or `superseded`; the button checks the date and applies.)\n"),
    ("| dom `components/builder/summary-panel.test.tsx` (slice 2's file, extended) |",
     "| dom `components/builder/summary-panel.test.tsx` (slice 2's file, extended) (3b plan: slice 2 tests the summary "
     "in `builder-shell.test.tsx`, which 3b extends) |"),
    ("### Manual checks (appended to `docs/manual-verification.md`, F §5.5)\n",
     "### Manual checks (appended to `docs/manual-verification.md`, F §5.5)\n\n"
     "(3b plan: appended as \"## Slice 3\" with check 11 for the church season (owner answer 3) and check 12 for "
     "\"New service\" (owner answer 1); `test_slice1_docs.py` pins the last four `##` headings. The owner's guided "
     "check after the merge runs the items marked \"(owner, after 3b)\".)\n"),
])

ROW_3A = "`normalize_title`, which resolves an AI answer's exact title, is unchanged. | 3a |\n"
edit(F, [
    (ROW_3A,
     ROW_3A
     + "| §4.6, §4.7, §4.9 | *(2026-09-29, slice 3b plan)* `isPristine` also counts a chosen hymnal (owner answer 1), "
     "so \"New service\" asks after a hymn or a hymnal is chosen and the roll-forward keeps that draft's date; choosing "
     "the church's effective hymnal stores `null`. The Exclude switch and the AI's other ideas never count. Hymns ships "
     "(`SHIPPED_STEPS` holds \"readings\" and \"hymns\"): the step bar counts it, Review lists each empty slot, and the "
     "summary lists the three hymns. The generic long-list picker is `components/app/search-combobox.tsx` (slice 1's "
     "time-zone picker uses the Combobox directly), and the kit gains `switch`. | 3b |\n"),
    ("*(2026-09-29, slice 2c plan: step 1 ships in 2c.)*",
     "*(2026-09-29, slice 2c plan: step 1 ships in 2c.)* *(2026-09-29, slice 3b plan: step 2 ships in 3b.)*"),
])

edit(T1DOCS, [
    ('    # Slice 2c appends "## Slice 2" after this section (slice 2 spec, Manual checks).\n'
     '    assert re.findall(r"^## .+$", text, re.MULTILINE)[-3:] == ["## Ops slice", "## Slice 1", "## Slice 2"]\n',
     '    # Slices 2c and 3b append "## Slice 2" and "## Slice 3" after this section (their specs, Manual checks).\n'
     '    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-4:]\n'
     '    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3"]\n'),
])
print("docs edited")
PYEOF
```

**Expected:** `docs edited`. An `AssertionError` names the anchor that moved: read that part of the file, fix the anchor in this step (not the file's other text), and run the step again from a clean file (`git checkout -- <file>`).

- [ ] **Step 3 (agent): Append the slice 3 checklist**

Append to `docs/manual-verification.md` (the block starts with one empty line):

```markdown

## Slice 3

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop) and
https://liturgy-frozen.streamlit.app, the production Streamlit app. These are
the slice 3 spec's manual checks 1-10 (slice 3 spec → Manual checks), with
check 11 for the church season in the AI prompt (owner answer 3, 2026-09-29)
and check 12 for "New service" (owner answer 1). After the 3b merge the
owner's guided check (owner answer 5: about six steps on the phone, given one
at a time, then a quick look on a computer) covers the items marked "(owner,
after 3b)", some of them in part; its result goes into `docs/ops-runbook.md` →
"Slice 3b record", which says what ran. The rest can be run at any time and
recorded the same way. Hymn titles, numbers and suggestions come from the
church's own hymnal and the live AI, so record what the page shows, never an
email address or a church id.

- [ ] (owner, after 3b) **1.** Open Hymns with readings for a real Sunday. "Hymns for the readings" shows matches in "Matches the readings" and "Same chapter". **Add** → **Opening hymn** fills the Opening card.
- [ ] (owner, after 3b) **2.** Search a picker by number and by part of a title. Two hymns with the same title are both listed, with different numbers, and either can be chosen.
- [ ] (owner, after 3b) **3.** Turn **Exclude hymns used within 12 weeks** off and on. A recently used pick stays, with its "Used on …" notice. The "… hymns are hidden." count changes with the switch.
- [ ] (owner, after 3b) **4.** **Suggest hymns**: empty slots fill and every slot shows at least 2 ideas. Tap an idea, then tap the hymn it replaced: they swap back. Choose a slot yourself, suggest again: your pick stays.
- [ ] **5.** Tap **Cancel** during a suggestion: the button is back to "Suggest hymns". Suggest 41 times quickly (or lower the limit in a local run): "Too many requests — try again in … s.", then "Try again now." once the wait has passed.
- [ ] **6.** In a church with two hymnals: switch hymnals with **Hymnal**; the picks keep their hymnal badges. With PH1990 the "no scripture references" notes show.
- [ ] (owner, after 3b) **7.** Refresh the page mid-step: picks, ideas and the switch survive. Switch church and back: each church keeps its own draft. The step bar shows "n of 3", then "Complete", for Hymns, and the summary (bottom sheet at 375 px, right column on desktop) lists the three hymns or "No {Slot} hymn", with no "Available soon" in its Hymns block. Review lists each empty slot under "Still needed".
- [ ] (owner, after 3b) **8.** At 375 px: no sideways scroll, the ideas wrap, a picker's list is usable with the keyboard open, and the sticky footer does not cover the last card.
- [ ] **9.** Regression: sign in, switch church, open every shipped nav item; the Streamlit smoke check on https://liturgy-frozen.streamlit.app: load the church, load an archived service, open Settings (F §6.3).
- [ ] (owner, after 3b) **10.** In GG2013, **Suggest hymns** for a real Sunday: the ideas lean older and familiar, and any hymn written in 1970 or later shows "Written {year}". A picker search for a known modern hymn shows the badge; a nineteenth-century hymn does not.
- [ ] (owner, after 3b) **11.** On a Sunday in the Season after Pentecost (for example 2026-10-04), **Suggest hymns** offers no Palm Sunday, Holy Week, Easter, Advent or Christmas hymns unless the readings call for one.
- [ ] (owner, after 3b) **12.** After choosing a hymn or a hymnal, **New service** asks "Start a new service?". Turning the Exclude switch or getting ideas alone does not make it ask.
```

- [ ] **Step 4 (agent): Check the result**

```bash
grep -c "(3b plan" docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md
grep -c "slice 3b plan" docs/superpowers/specs/2026-09-25-migration-foundations-design.md
sed -n '/^## Slice 3$/,$p' docs/manual-verification.md | grep -cE "^- \[ \] "
grep -c "^- \[ \] (owner, after 3b) " docs/manual-verification.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git diff -U0 docs backend | grep '^+' | grep -v '^+++' | grep -c '—'
git diff --stat
```

**Expected:** `15` (the marker sentence and fourteen notes); `2`; `12`; `9`; `89 passed in <t>s`; `1110 passed, 11 skipped in <t>s`; `2` (the only em dashes on added lines are S's own copy "Too many requests — try again in … s." in check 5 and F §4.7's existing "Available soon — keep using the current app for this part" on the line that gains a note; the new prose has none); `4 files changed, 55 insertions(+), 13 deletions(-)`.

- [ ] **Step 5 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -m "Docs: slice 3b notes in S and F, and the slice 3 manual checklist (S Manual checks; F §4.6, §4.7, §4.9)" -m "Marks \"(3b plan)\" in the slice 3 spec where 3b built something more
precisely than written: the toolbar's loading, the singular counts, the
Add button's name and the matches' badge, the church season in the
prompt (owner answer 3), the switch and SearchCombobox, formatAbbrevDate,
what isPristine counts (owner answer 1), reconcilePick's and
buildSuggestionRequest's extra arguments, where the latest tracker lives,
the summary tests' file and the checklist. F gains an amendment row and a
§4.7 note. docs/manual-verification.md gains \"## Slice 3\", and
test_slice1_docs.py pins its last four headings.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** one commit, 4 files changed.

**Review checkpoint (T13):** every S note says "(3b plan)" and matches the code; nothing else in S or F changed; the checklist items read as the owner will run them; `git show --stat HEAD` lists the four files only.

### Task 14: Whole-branch verification and the slice 3b pull request (owner's yes before the PR is opened and before it is marked ready) (S Testing "Frontend (Vitest)", AC10-AC14, AC20; F §4.1, §4.3, §4.4, §4.9, §4.10, §5.2, §5.4; owner decisions 3, 5; standing rules; clarifications 4, 18)

The whole branch is checked in one place before anyone reviews it: the frontend suite three times and twice more with the clock moved forward, types, lint, the production build and its routes, the backend suite, the generated API files (unchanged), the gates (client components, no link to the old app, no `apiFetch` in components, storage only through `lib/storage.ts`, no raw HTML, `SHIPPED_STEPS` holding `"readings"` and `"hymns"`, only the planned Python changes), the exact list of changed paths, and the exact list of commits against this plan. The branch is already on GitHub from the backup pushes, but no PR exists; on the owner's first yes the agent opens it as a **draft**, so CI runs. When CI is green, the agent reports and, on the owner's second yes, marks it ready. Merging is Task 15, with its own yes.

Below, `<scratch>` is the absolute path of the session's scratchpad directory, and `<N>` is the PR number Step 10 prints; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never run a bare `git push` or `--force`. If T1 ended in outcome A, Task 1b's commit and files are part of the branch: add them where Steps 6-8 say so, and its tests to every count (name them in the Step 9 message).

**Files:** none changed. A local or CI failure is fixed in its owning task's files (Step 14).

**Interfaces:**
- Consumes: everything from T2-T13, in particular each task's commit subject (Step 8 reads them from this plan between `### Task 1:` and `### Task 14:`), the cumulative counts (Baselines and counts), `SHIPPED_STEPS` (T12), and CI (`.github/workflows/ci.yml`, unchanged: `backend`, `backend-postgres`, `frontend` with lint, typecheck, `API types match the OpenAPI snapshot (F §5.4)`, test and build).
- Produces: PR `<N>` (`claude/slice-2-plan-4q33le` → `main`), titled `Slice 3b: the Hymns step`, not a draft after Step 13, CI green on the branch head, its body holding the line `Tests: frontend 356 → 421 in 55 → 64 files; backend 1106 → 1110 passed, 11 → 11 skipped` and ending with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Later user: T15.

- [ ] **Step 1 (agent): Bring the branch up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
git log --oneline --grep '^Plan: slice 3b hymns step' -1
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected,** in order: nothing (or `?? .claude/`); the fetch prints nothing or only updated refs; `0`; `b47abba Merge pull request #27 from bbrown62450/claude/slice-2-plan-4q33le` (or a later merge the owner made); `<sha> Plan: slice 3b hymns step (S slice 3; owner answers 2026-09-29)`; `0` (every commit was backed up).
- If the first count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 14)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. On a conflict, run `git merge --abort`, stop and tell the owner which files conflict. Without one, continue: Steps 2-8 run on the merged tree, and any new tests the merge brought change the totals by exactly those (name them in the Step 9 message).
- If `git status --short` shows anything else, stop: commit it in its owning task or ask.

- [ ] **Step 2 (agent): Run the frontend suite three times and with the clock moved forward, then types and lint**

```bash
for i in 1 2 3; do (cd frontend && npm test 2>&1 | grep -E "Test Files|Tests |FAIL"); done
cat > "<scratch>/shift-clock.mjs" <<'JSEOF'
// Moves the real clock forward by WSB_CLOCK_SHIFT_DAYS days (loaded with NODE_OPTIONS=--import).
// A test that fakes Date (vi.useFakeTimers + vi.setSystemTime) is unaffected; one that forgot to is caught.
const offset = Number(process.env.WSB_CLOCK_SHIFT_DAYS ?? "0") * 24 * 60 * 60 * 1000;
const RealDate = Date;
function ShiftedDate(...args) {
  if (!new.target) return new RealDate(RealDate.now() + offset).toString();
  return args.length === 0 ? new RealDate(RealDate.now() + offset) : new RealDate(...args);
}
Object.setPrototypeOf(ShiftedDate, RealDate);
ShiftedDate.prototype = RealDate.prototype;
ShiftedDate.now = () => RealDate.now() + offset;
globalThis.Date = ShiftedDate;
JSEOF
for d in 8 400; do echo "clock +$d days"; (cd frontend && WSB_CLOCK_SHIFT_DAYS=$d NODE_OPTIONS="--import <scratch>/shift-clock.mjs" npm test 2>&1 | grep -E "Test Files|Tests |FAIL"); done
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** three times ` Test Files  64 passed (64)` and `      Tests  421 passed (421)` (baseline 356 in 55; after T3-T12: 359, 366, 382, 388, 392, 403, 407, 414, 419, 421) and no `FAIL`; then `clock +8 days` and `clock +400 days`, each followed by the same two lines and no `FAIL`; `0`; `> tsc --noEmit` and `> eslint` with nothing after. Any other number: find the task whose count drifted. A run that fails even once is a failure (Step 14): make the test deterministic (fake only `Date`, set to `DRAFT_NOW`; await the UI with `findBy`/`waitFor`) rather than retrying it.

- [ ] **Step 3 (agent): Run the backend suite and the Postgres marker count**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
```

**Expected:** `1110 passed, 11 skipped in <t>s` (T2 added four tests; T13 edits one assertion); `11 skipped, 1110 deselected in <t>s`.

- [ ] **Step 4 (agent): Build the frontend with CI's placeholder environment**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder")
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

**Expected:** `✓ Compiled successfully in <t>s`, the route table's five builder lines (`├ ○ /builder`, `├ ○ /builder/hymns`, `├ ○ /builder/liturgy`, `├ ○ /builder/readings`, `├ ○ /builder/review`) and no `Error` line; then exactly:

```
/ /_global-error /_not-found /auth/callback /builder /builder/hymns /builder/liturgy /builder/readings /builder/review /favicon.ico /join /login /welcome
```

(3b adds no route.) The build must run in the real checkout: Turbopack refuses a symlinked `node_modules`. If it fails only with `Failed to fetch` for a Geist font (no network), say so in the Step 9 message and rely on CI's `frontend` job.

- [ ] **Step 5 (agent): Check the generated API files did not change**

```bash
(cd frontend && npm run gen:api >/dev/null) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
git diff --name-only origin/main...HEAD -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | wc -l
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
git status --short
```

**Expected:** `schema diff exit 0`; `0` (3b changes no API; T2 changes only the prompt; clarification 18); `<n> passed in <t>s`; nothing (or `?? .claude/`).

- [ ] **Step 6 (agent): Run the gates**

```bash
find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) -exec sh -c 'head -1 "$1" | grep -qx "\"use client\";" || echo "not a client component: $1"' _ {} \; ; echo "client components checked: $(find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) | wc -l)"
grep -rniE "streamlit|liturgy-frozen" frontend/src --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "old app grep exit $?"
grep -rn "apiFetch" frontend/src/components frontend/src/app --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "apiFetch in UI grep exit $?"
grep -rnE "window\.(local|session)Storage|(local|session)Storage\.(getItem|setItem|removeItem|key|clear)" frontend/src --include=*.ts --include=*.tsx | grep -vE "^frontend/src/lib/storage\.ts:|\.test\.tsx?:|^frontend/src/test/"; echo "storage grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
grep -rn "new Date(" frontend/src/components/builder/hymns frontend/src/lib/hymns --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "date grep exit $?"
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
grep -rn "Available soon" frontend/src --include=*.tsx | grep -v "\.test\.tsx:" | wc -l
git diff --name-only origin/main...HEAD -- '*.py' backend/requirements.txt requirements-dev.txt backend/migrations .github frontend/package.json frontend/package-lock.json docs/ops-runbook.md
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected,** in order:
- `client components checked: 10` with no "not a client component" line before it (F §4.1; 3b replaces the hymns page's body);
- `old app grep exit 1`; `apiFetch in UI grep exit 1` (F §4.4); `storage grep exit 1` (F §4.3; 3b adds no storage key); `raw html grep exit 1`; `date grep exit 1` (F §4.10: the step and `lib/hymns` never parse a date);
- `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns"]);`;
- `2` (`wc` pads it; "Available soon" lives in `step-placeholder.tsx` and `summary-panel.tsx` only, now for Liturgy and Review);
- exactly these seven lines, in this order: `backend/hymn_suggest.py`, `backend/tests/test_api_hymn_suggestions.py`, `backend/tests/test_hymn_suggest.py`, `backend/tests/test_lectionary_domain.py`, `backend/tests/test_slice1_docs.py`, `backend/usecases/hymns.py`, `backend/vanderbilt_lectionary.py` (T2 and T13; with Task 1b, also its files; no requirement, migration, workflow, package or runbook change);
- only `trailer check done`.

Any other output: stop, find the owning task (Step 14) and fix it there. A grep hit may be a false positive (a comment): read the line, and if it is harmless, say why in the Step 9 message rather than bending the code to silence it.

- [ ] **Step 7 (agent): Check the exact list of changed paths**

```bash
LC_ALL=C sort > "<scratch>/slice3b-expected-paths.txt" <<'EOF'
backend/hymn_suggest.py
backend/tests/test_api_hymn_suggestions.py
backend/tests/test_hymn_suggest.py
backend/tests/test_lectionary_domain.py
backend/tests/test_slice1_docs.py
backend/usecases/hymns.py
backend/vanderbilt_lectionary.py
docs/manual-verification.md
docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md
frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx
frontend/src/components/app/search-combobox.test.tsx
frontend/src/components/app/search-combobox.tsx
frontend/src/components/builder/builder-shell.test.tsx
frontend/src/components/builder/hymns/alternative-chips.tsx
frontend/src/components/builder/hymns/hymn-label.test.tsx
frontend/src/components/builder/hymns/hymn-label.tsx
frontend/src/components/builder/hymns/hymn-picker.tsx
frontend/src/components/builder/hymns/hymn-slot-card.tsx
frontend/src/components/builder/hymns/hymns-step.test.tsx
frontend/src/components/builder/hymns/hymns-step.tsx
frontend/src/components/builder/hymns/hymns-toolbar.tsx
frontend/src/components/builder/hymns/scripture-matches.tsx
frontend/src/components/builder/hymns/suggest-hymns-button.tsx
frontend/src/components/builder/hymns/use-undo-toasts.ts
frontend/src/components/builder/step-placeholder.tsx
frontend/src/components/builder/summary-hymns.tsx
frontend/src/components/builder/summary-panel.tsx
frontend/src/components/ui/switch.tsx
frontend/src/lib/api/timeouts.ts
frontend/src/lib/api/types.ts
frontend/src/lib/dates.test.ts
frontend/src/lib/dates.ts
frontend/src/lib/draft/fingerprint.test.ts
frontend/src/lib/draft/status.test.ts
frontend/src/lib/draft/status.ts
frontend/src/lib/draft/steps.ts
frontend/src/lib/draft/store.test.ts
frontend/src/lib/features.ts
frontend/src/lib/hymns/filter.test.ts
frontend/src/lib/hymns/filter.ts
frontend/src/lib/hymns/hymnal.ts
frontend/src/lib/hymns/labels.test.ts
frontend/src/lib/hymns/labels.ts
frontend/src/lib/hymns/match-request.test.ts
frontend/src/lib/hymns/match-request.ts
frontend/src/lib/hymns/picks.test.ts
frontend/src/lib/hymns/picks.ts
frontend/src/lib/hymns/suggest-request.test.ts
frontend/src/lib/hymns/suggest-request.ts
frontend/src/lib/queries/hymns.test.tsx
frontend/src/lib/queries/hymns.ts
frontend/src/lib/queries/keys.test.ts
frontend/src/lib/queries/keys.ts
frontend/src/test/fixtures/index.ts
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice3b-actual-paths.txt"
wc -l < "<scratch>/slice3b-expected-paths.txt"
wc -l < "<scratch>/slice3b-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice3b-expected-paths.txt" "<scratch>/slice3b-actual-paths.txt"
git diff --name-status --no-renames origin/main...HEAD | cut -c1 | sort | uniq -c
```

**Expected:** `56`; `56`; `comm` prints nothing; then `  29 A` and `  27 M`. These are the File Structure's paths: 29 created (the plan and 28 frontend files) and 27 modified (17 frontend files, 7 backend files, the two specs and the checklist). With Task 1b, add its paths to the list and to the counts. An indented `comm` line (changed, not listed) means a task touched a file its **Files:** does not name: find it with `git log --format='%h %s' origin/main..HEAD -- '<path>'`; anything under `backend/` other than T2's, T13's and Task 1b's files, `frontend/src/lib/api/openapi.json`, `schema.d.ts`, `package*.json` or `.github/` is a stop. An unindented line means a task's commit is missing.

- [ ] **Step 8 (agent): Check the exact list of commits against this plan**

```bash
.venv/bin/python - docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md > "<scratch>/slice3b-plan-subjects.txt" <<'EOF'
import pathlib, re, sys
text = "\n" + pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
lines = text.split("\n### Task 1:", 1)[1].split("\n### Task 14:", 1)[0].splitlines()
for line in lines:
    m = re.match(r'\s*git commit -m "((?:[^"\\]|\\.)*)"', line)
    if m:
        print(re.sub(r"\\(.)", r"\1", m.group(1)))
EOF
PLAN=$(git log --format=%H --grep '^Plan: slice 3b hymns step' -1)
git log --reverse --no-merges --format=%s "$PLAN"..HEAD > "<scratch>/slice3b-branch-subjects.txt"
wc -l < "<scratch>/slice3b-plan-subjects.txt"
diff "<scratch>/slice3b-plan-subjects.txt" "<scratch>/slice3b-branch-subjects.txt"; echo "commit list diff exit $?"
git log --reverse --format='%h %s' origin/main..HEAD
```

**Expected:** `12` (one commit for each of T2-T13; T1 changes no file); `commit list diff exit 0` with no output before it; the branch's commits oldest first: the plan's own commits (`WIP plan: slice 3b` several times, then `Plan: slice 3b hymns step (S slice 3; owner answers 2026-09-29)`), then the twelve task commits from `<sha> Hymns: the AI prompt names the church season and avoids other seasons' hymns (owner answer 3)` to `<sha> Docs: slice 3b notes in S and F, and the slice 3 manual checklist (S Manual checks; F §4.6, §4.7, §4.9)` (plus a Step 1 merge, if any). A `diff` line is a failure unless it is a `>` line `Fix: … (Task <n> review)` (a review fix), `Fix: … (Task <n>, slice 3b final verification)` (Step 14), `Plan: …` (a plan correction the controller committed) or Task 1b's commit, each named in the Step 9 message.

- [ ] **Step 9 (agent → OWNER): Ask for the go-ahead to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
git rev-list --count origin/main..HEAD
```

**Expected:** one `✓ Logged in to github.com account <login> (keyring)` line; `[]` (no open PR from this branch; PRs #26 and #27 are merged); the branch's commit count. If `gh` is not logged in, ask the owner to run `gh auth login`. If an open PR exists, stop and ask.

Send the owner exactly this, with `<count>` filled in, and wait for a clear yes:

> Slice 3b is verified locally: frontend 421 tests in 64 files, passing three runs in a row and with the clock moved 8 and 400 days ahead (356 in 55 before); typecheck, lint and the production build are clean; the backend has 1110 passed, 11 skipped (1106 before: the church season in the AI prompt added four tests); the API types did not change; the checks are clean (every page is a client component, no link to the old app, the screens use the query hooks, no new browser storage, Date & readings and Hymns are the steps switched on); changed files (56) and commits (<count>) are as planned, and every commit is already backed up on the branch. May I open the pull request as a **draft** titled "Slice 3b: the Hymns step", so the checks run? I will come back with the results and ask again before marking it ready. Merging stays with you (Task 15).

Add one line per note from Steps 1-8 (a merge from `main`, a skipped font download, a `Fix:` commit, Task 1b, how the switch was made). A no leaves the branch as it is.

- [ ] **Step 10 (agent, on the owner's yes): Write the PR body and open the draft PR**

```bash
cat > "<scratch>/slice3b-pr-body.md" <<'EOF'
PR 3b of slice 3: the Hymns step. After it merges, a signed-in member fills the Opening, Response and Closing hymns from the church's hymnal on step 2 of the Service Builder. Spec: docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md (3b). Plan: docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md. No migration and no API change; one backend change to the AI prompt.

The step
- Three slot cards, each with a searchable picker (by number or title; two hymns with the same title are told apart) or the chosen hymn with its Listen link, Change and remove with Undo. Notices: used or planned within 12 weeks, not in your hymnal, chosen twice.
- The toolbar: the hymnal (when the church has two or more), "Exclude hymns used within 12 weeks" (on by default; it hides hymns but never clears a pick), and Suggest hymns: empty slots get the AI's top pick and every slot gets 2 to 4 one-tap other ideas; Cancel; each AI error has its own message.
- Hymns for the readings: the day's readings matched in the hymnal, grouped, with an extra reference and Add to a slot.
- Newer hymns show "Written {year}".
- The step bar counts Hymns (n of 3, then Complete), Review lists each empty slot, and the summary lists the three hymns. Liturgy and Review keep "Available soon".

Backend: the AI prompt now names the church season (from the service date) and asks the model to avoid hymns for another season or feast unless the readings call for them (owner answer 3). @@T1B_LINE@@

Owner answers (2026-09-29): choosing a hymn or a hymnal is unsaved work, the Exclude switch and the ideas are not (1); the recent-use finding is in the plan's Task 1 (2); the church season in the prompt (3); "Written {year}" as designed (4); a guided phone check after the merge (5). @@SWITCH_LINE@@

Tests: frontend 356 → 421 in 55 → 64 files; backend 1106 → 1110 passed, 11 → 11 skipped

After merge (Task 15): a guided check on the owner's phone (about six steps) and a quick look on a computer, then a short "Slice 3b record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Replace `@@SWITCH_LINE@@` with `The switch is generated from the base-nova registry.` or `The switch is rebuilt from the upstream shadcn source (base-nova, pinned commit), because the build container cannot reach the registry (plan clarification 4).` (T7's commit body says which), and `@@T1B_LINE@@` with `Recent use: <one sentence from Task 1b>.` if T1 ended in outcome A, else delete it (and the space before it). With Task 1b, also change the `Tests:` line to the real counts. Then:

```bash
grep -c '@@' "<scratch>/slice3b-pr-body.md"
grep -cx 'Tests: frontend 356 → 421 in 55 → 64 files; backend 1106 → 1110 passed, 11 → 11 skipped' "<scratch>/slice3b-pr-body.md"
git fetch origin && test "$(git rev-list --count HEAD..origin/main)" = 0 && test "$(git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD)" = 0 && echo "branch is current and backed up"
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 3b: the Hymns step" \
  --body-file "<scratch>/slice3b-pr-body.md"
gh pr view claude/slice-2-plan-4q33le -R bbrown62450/church --json number,isDraft,headRefOid,url --jq '"#\(.number) draft=\(.isDraft) \(.headRefOid) \(.url)"'
git rev-parse HEAD
```

**Expected:** `0` (grep exits 1); `1`; `branch is current and backed up` (if not: push with `git push origin claude/slice-2-plan-4q33le`, or go back to Step 1 if `main` moved); the PR URL; `#<N> draft=true <sha> https://github.com/bbrown62450/church/pull/<N>` with the same `<sha>` as `git rev-parse HEAD`.

- [ ] **Step 11 (agent): Watch the checks**

Run with `run_in_background: true`:

```bash
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

**Expected** when it exits: exit code 0 and every check `pass`: `backend`, `backend-postgres`, `frontend`, and the Vercel preview. `no checks reported`: run it again. Any `fail`: Step 14.

- [ ] **Step 12 (agent): Read the CI logs and compare**

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan-4q33le --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan-4q33le --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan-4q33le --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "frontend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "Test Files +[0-9]+ passed|Tests +[0-9]+ passed|Compiled successfully|/builder"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan-4q33le --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "[0-9]+ passed"
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch claude/slice-2-plan-4q33le --commit "$(git rev-parse HEAD)" --limit 1 --json databaseId --jq '.[0].databaseId'); JOB=$(gh run view "$RUN" -R bbrown62450/church --json jobs --jq '.jobs[] | select(.name == "backend-postgres") | .databaseId'); gh run view -R bbrown62450/church --job "$JOB" --log | grep -E "pg_smoke: OK|[0-9]+ (passed|failed)"
```

**Expected:** `run <id>`; `backend: success`, `backend-postgres: success`, `frontend: success`; frontend `Test Files  64 passed (64)`, `Tests  421 passed (421)`, `✓ Compiled successfully` and the five `/builder` route lines; backend `1110 passed, 11 skipped in …s`; backend-postgres `pg_smoke: OK` and `11 passed, 1110 deselected` (with any warning count the 3a runs showed). If a required job failed on or after 2026-10-19, first check the runner image (`Image: ubuntu-24.04` expected; GitHub moves `ubuntu-latest` then) and report a setup failure on a new image to the owner before changing any 3b file.

- [ ] **Step 13 (agent → OWNER): Report CI and ask to mark the PR ready**

Send exactly this, with the values filled in, and wait for a clear yes:

> PR #<N> (<url>) is green (run <run id>): frontend 421 tests in 64 files, build OK; backend 1110 passed, 11 skipped; the Postgres job clean; the Vercel preview built. May I mark it ready for review? Merging stays with you (Task 15).

On the yes:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft,state --jq '"draft=\(.isDraft) \(.state)"'
```

**Expected:** `✓ Pull request bbrown62450/church#<N> is marked as "ready for review"`, then `draft=false OPEN`. Tell the owner in one line: "PR #<N> is ready for review. Next: Task 15, the merge on your yes, then a guided check on your phone, one step at a time."

- [ ] **Step 14 (agent): Fix any failure in its owning task**

Read the failure (for CI: `gh run view <run-id> -R bbrown62450/church --log-failed | tail -80`), reproduce it locally, and fix it in the task that owns it:

| Failing check or test | Owning task |
|---|---|
| `test_lectionary_domain.py` (`church_season`), `test_hymn_suggest.py`, `test_api_hymn_suggestions.py` (the season line) | T2 |
| `draft/status.test.ts` (`isPristine`), `draft/fingerprint.test.ts`, `draft/store.test.ts` | T3 |
| `lib/hymns/picks.test.ts`, `lib/api/types.ts`, the `hymn`/`suggested`/`hymnals` fixtures | T4 |
| `lib/hymns/{filter,labels,match-request,suggest-request}.test.ts`, `dates.test.ts` (`formatAbbrevDate`) | T5 |
| `queries/hymns.test.tsx`, `keys.test.ts`, `timeouts.ts`, `features.ts`, the list and body fixtures | T6 |
| `search-combobox.test.tsx`, `switch.tsx` lint or types | T7 |
| `hymn-label.test.tsx`, `hymns-step.test.tsx` "the Hymns step" and "slot cards" blocks | T8 |
| its "the toolbar" block | T9 |
| its "Suggest hymns" block | T10 |
| its "Hymns for the readings" block | T11 |
| `status.test.ts` (steps, `stepStatus`, `stillNeeded`), `builder-shell.test.tsx`, the `SHIPPED_STEPS` gate, the hymns route in the build | T12 |
| the spec or F text, `docs/manual-verification.md`, `test_slice1_docs.py` | T13 |
| a flaky run in Step 2, or a failure only with the clock moved | the task owning the test: fake only `Date` (set to `DRAFT_NOW`), await the UI with `findBy`/`waitFor`, never sleep in place of a condition |
| any other existing test, the Vercel preview only | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-8; commit with the subject `Fix: <what> (Task <n>, slice 3b final verification)` and the trailer; have that task re-reviewed; push with `git push origin claude/slice-2-plan-4q33le` (a backup before Step 10; after it, covered by the owner's first yes); after Step 10, repeat Steps 11-12 and send Step 13's message with the new run. An infrastructure failure with no test output gets one `gh run rerun <run-id> -R bbrown62450/church --failed` first.

Expected counts after this task: frontend `421 passed` in 64 files (CI the same); backend `1110 passed, 11 skipped` (CI `backend-postgres`: `11 passed, 1110 deselected`). No commit unless Step 14 needed a fix.

### Task 15: Merge and after (OWNER + agent): the merge, the deploy, a guided check on the phone and a look on a computer, the slice 3b record (S Manual checks, AC10, AC11, AC17, AC20; F §5.5; owner decisions 2, 3, 5; owner answers 2, 5)

3b changes the API's prompt text only (T2) and no migration or Python requirement, so the merge's Railway deploy builds the API with the season line and its pre-deploy `alembic upgrade head` finds the database at head (`0004_invites_reusable`) and runs nothing; no Railway, Supabase or branch-protection setting changes. The Vercel production deploy is the one members see: after it, step 2 of the builder is the real Hymns step. Merges never reach https://liturgy-frozen.streamlit.app/ (owner decision 2). Owner answer 5: a guided check on the phone of six short steps, then a quick look on a computer, given **one at a time** (give one OWNER step, wait for the owner's report or "next", then give the next). The agent writes each result, with its date, into `<scratch>/slice3b-t15-results.md` (not committed); Step 11 fills the record from it, together with T1's finding (without ids). Hymn titles, numbers and suggestions come from the church's hymnal and the live AI, so they may differ from the examples; the owner reports what the page shows.

Below, `<N>` is the PR number (T14), `<merge sha>` the merge commit Step 2 prints, `<scratch>` the scratchpad path; write them out literally. Every `gh` command uses `-R bbrown62450/church`. Pushing, merging, and any settings change each need the owner's explicit yes, asked separately. No token, email address or church id is recorded anywhere.

**Files:**
- Merge (Steps 1-2): no file changes.
- Create (not committed): `<scratch>/slice3b-t15-results.md`.
- Modify (records PR, Step 11, on `claude/slice-2-plan-4q33le` fast-forwarded to `origin/main` after the merge): `docs/ops-runbook.md`: insert `### Slice 3b record` right after `### Slice 3a record`'s table (its last row starts `| Follow-ups | 3b: the Hymns step UI,`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins the `##` list.
- Test: none new.

**Interfaces:**
- Consumes: PR `<N>` ready and green (T14); the production URLs (owner decision 5); the "## Slice 3" checklist (T13); T1's results file.
- Produces: 3b live on `main` and in production; the "Slice 3b record" in `docs/ops-runbook.md`. Later user: slice 4's plan (starts from `main` after this).

- [ ] **Step 1 (agent): Check the PR can merge**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,headRefOid --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus) \(.headRefOid)"'
git rev-parse HEAD
git rev-list --count HEAD..origin/main
```

**Expected:** `OPEN draft=false MERGEABLE CLEAN <sha>` with `<sha>` equal to `git rev-parse HEAD`; `0`. If `main` moved (count not `0`, or `BEHIND`): merge it as in T14 Step 1, rerun T14 Steps 2-3 (`421 passed` in 64 files, plus any tests the merge brought; `1110 passed, 11 skipped`), push with the owner's yes, wait for green checks, and run this step again. `BLOCKED`: a required check is not green; fix it (T14 Step 14). Never merge with `--admin`.

- [ ] **Step 2 (agent → OWNER): Ask to merge, then merge**

Send: "PR #<N> is ready, green and up to date with main. May I merge it with a merge commit? After that members see the real Hymns step (Liturgy and Review stay 'Available soon'), and the AI's hymn suggestions name the church season; the database does not change." On a clear yes:

```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
```

**Expected:** `MERGED <merge sha> <UTC time>`. Write the sha and time (UTC and Eastern) into the results file.

- [ ] **Step 3 (agent): Check CI on `main` and the two deployments**

Run the watch with `run_in_background: true`:

```bash
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit <merge sha> --limit 1 --json databaseId --jq '.[0].databaseId'); echo "run $RUN"; gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

Then:

```bash
gh api "repos/bbrown62450/church/deployments?sha=<merge sha>" --jq '.[] | "\(.id) \(.environment)"'
for id in $(gh api "repos/bbrown62450/church/deployments?sha=<merge sha>" --jq '.[].id'); do gh api "repos/bbrown62450/church/deployments/$id/statuses" --jq '"'"$id"' \(.[0].state)"'; done
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" --max-time 15 https://worship-service-builder.vercel.app/builder/hymns || echo "vercel not reachable from here"
```

**Expected:** `run <id>` and `ci exit 0`; one deployment per environment (a Vercel `Production` one, and Railway's if it reports one) each ending `success` (a `pending` or `in_progress` state: run the loop again a minute later); the `curl` line either a redirect to sign-in (for example `307 https://worship-service-builder.vercel.app/login?next=%2Fbuilder%2Fhymns`) or `vercel not reachable from here` (the container's network policy; then Step 4 is the check). A `failure` state or a `404`: stop and tell the owner (Step R if the site cannot serve). Ask the owner, once, to glance at Railway's Deploy Logs for the merge's deploy: a health check 200, `AI: configured (model=gpt-4.1-mini)`, and no Traceback or ERROR line. Record the answer.

- [ ] **Step 4 (OWNER, then agent): Phone, step 1 of 6: the step and the readings' hymns**

Send the owner this, and wait for the report:

> On your phone, open https://worship-service-builder.vercel.app (signed in). If next Sunday's readings are not filled in on step 1, tap **⋮** next to Summary, choose **New service**, and wait for them. Then tap **2 Hymns** in the step bar. You should see "Hymns" with three cards (Opening, Response, Closing), each with a search box, and below them **Hymns for the readings** with a number next to it. Tap it: hymns matching the readings appear under "Matches the readings" and "Same chapter". Tap **Add** on one of them and choose **Opening hymn**: it appears in the Opening card. Does it?

Record the answer (and the phone and browser, the Sunday, and the hymn added). Anything wrong: note it, ask for a screenshot, and decide with the owner whether it is a follow-up or needs a fix before going on. "Couldn't load this church's hymnal." here means the API or the database is not answering: record it, check Step 3's deploy, and try again before going on.

- [ ] **Step 5 (OWNER, then agent): Phone, step 2 of 6: searching by number and by title**

> In the **Response** card, tap the search box and type a hymn number you know. That hymn should be first in the list, shown as "#number Title". Then clear it and type part of a title, for example "grace": the matching hymns show with their numbers. Choose one: it fills the Response card, with a ▶ Listen link when Hymnary has a page for it. Did that work?

Record the answer.

- [ ] **Step 6 (OWNER, then agent): Phone, step 3 of 6: recently used hymns**

> Near the top, **Exclude hymns used within 12 weeks** should be on. Under it, does it say how many hymns are hidden? Turn it off, then on again: the hymns you chose stay in their cards. If a chosen hymn was used within 12 weeks, its card says "Used on …" or "Also planned for …". What do you see?

Record the answer, and compare it with T1's finding (recent use exists or not for this church). No hidden count when T1 found no recent use in the window is the expected result, not a failure; note it.

- [ ] **Step 7 (OWNER, then agent): Phone, step 4 of 6: Suggest hymns**

> Tap **Suggest hymns**. It says "Suggesting…" and takes a few seconds. Then the Closing card, which was empty, gets a hymn, and under every card there is "Other ideas" with at least two hymns; any hymn written in 1970 or later shows "Written" and its year. The hymns you chose yourself stay. Tap one of the ideas: it swaps into that card; tap the hymn that went into the ideas: they swap back. Last, look at the suggestions: for a Sunday in the Season after Pentecost there should be no Palm Sunday, Easter, Advent or Christmas hymns. Is that what you see? If any seem out of season, please tell me which.

Record the answer, including any out-of-season hymn by title (owner answer 3). "AI suggestions aren't set up on this app yet." means Railway lost the key: record it and ask the owner to check the variables before going on.

- [ ] **Step 8 (OWNER, then agent): Phone, step 5 of 6: removing with Undo, and the summary**

> On the Opening card, tap the **✕**: the hymn goes and a message says "Removed …" with **Undo**. Tap **Undo**: it comes back. Now the step bar should show Hymns as done, and tapping **Summary** at the top should list "Opening · …", "Response · …" and "Closing · …". Is that right?

Record the answer.

- [ ] **Step 9 (OWNER, then agent): Phone, step 6 of 6: New service asks first**

> Tap **⋮** next to Summary, then **New service**. Because you chose hymns, it should ask "Start a new service?" before clearing anything. Tap **Cancel**: your hymns are still there. Did it ask?

Record the answer.

- [ ] **Step 10 (OWNER, then agent): A quick look on a computer**

> On a computer, open the same address in a wide window and go to Hymns. The summary on the right should list the three hymns, and the step bar should read "1 Date & readings Complete · 2 Hymns Complete · 3 Liturgy Soon · 4 Review & send Not in archive". Remove one hymn with ✕, then click **4 Review & send**: under "Still needed" it should say "No … hymn — Choose one" for that slot. Does it look right?

Record the answer. Optional, only if the owner offers: the liturgy-frozen smoke (sign in, the church and a saved service open). Otherwise record "Not run: 3b changes no data, and merges never reach liturgy-frozen."

- [ ] **Step 11 (agent): Write the slice 3b record**

```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
git log --oneline -1
grep -n '^### Slice 3a record$\|^| Follow-ups | 3b: the Hymns step UI\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); `<merge sha> Merge pull request #<N> from bbrown62450/claude/slice-2-plan-4q33le`; three lines in that order (the 3a record's heading, its last table row, `## Backups`). Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Slice 3b record

Slice 3b (the Hymns step: three slots filled by number or title, recent use
within 12 weeks, hymns for the readings, AI suggestions with other ideas,
"Written {year}" on newer hymns, and the step in the step bar, Review and
the summary) merged as PR #<N>. The API's AI prompt now names the church
season; no database change, so production stays at `0004_invites_reusable`
(head). The owner's check was a guided check on a phone and a look on a
computer (owner answer 5, 2026-09-29), covering the "(owner, after 3b)"
items of `docs/manual-verification.md` → "Slice 3" in part. No token, email
address or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Recent use (Task 1) | <The finding in one or two sentences, without ids: outcome A (fixed in Task 1b), B, C or D, and the owner's choice.> | <date> |
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` for the merge commit (run <run id>): success. Deployments: <Vercel Production success; Railway success / what the loop showed>. Deploy Logs: <health 200, AI configured (model=gpt-4.1-mini), no Traceback / what the owner saw> | <date> |
| 1. The step and the readings' hymns (phone: <phone and browser>) | <Three cards; matches grouped; Add → Opening worked. / What the owner saw instead.> | <date> |
| 2. Search by number and title | <Number first; title search; Response filled; Listen link. / …> | <date> |
| 3. Recently used hymns | <Switch on; "<n> hymns are hidden." / no hidden count (as Task 1 expects); picks stayed. / …> | <date> |
| 4. Suggest hymns | <Empty slot filled; at least 2 ideas per slot; swap and swap back; Written {year} shown; no out-of-season hymns. / …> | <date> |
| 5. Remove, Undo and the summary | <Removed … with Undo; step bar done; summary lists the three hymns. / …> | <date> |
| 6. New service | <Asked first; Cancel kept the hymns. / …> | <date> |
| Computer | <Summary column with the hymns; step bar; Still needed row after a removal. / …> | <date> |
| Streamlit smoke on liturgy-frozen | <OK: sign-in, the church and a saved service. / Not run: 3b changes no data, and merges never reach liturgy-frozen.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Slice 4: the Liturgy step. 5a: recording hymn use on every save (the new app does not write `hymn_usage` yet). 6a: Settings → Hymns flips `SETTINGS_HYMNS_READY`. | <date> |
```

Replace every `<…>` from the results files, keeping one alternative where a cell offers two (separated by ` / `). Then:

```bash
sed -n '/^### Slice 3b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 3b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git diff --stat
git add docs/ops-runbook.md
git commit -m "Runbook: slice 3b record (merged; the Hymns step is live; owner's guided phone check)" -m "Records the slice 3b merge (PR #<N>): the church season in the AI
prompt, no database change; CI on main and the deployments; the recent-
use finding (Task 1); the owner's guided check on a phone (the readings'
hymns, search, recent use, Suggest, remove and Undo, New service) and a
look on a computer; the liturgy-frozen smoke or why it was skipped. No
token, email or church id is recorded.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** `0`; `0`; `89 passed in <t>s`; ` docs/ops-runbook.md | <n> +`; one commit.

- [ ] **Step 12 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 3b record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 3b record" \
  --body "Records slice 3b (PR #<N>) in docs/ops-runbook.md → Slice 3b record: the recent-use finding, the merge and deployments, and the owner's guided check on a phone and look on a computer. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the push; the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`, then `gh pr view claude/slice-2-plan-4q33le -R bbrown62450/church --json state --jq .state` → `MERGED`. Report: "Slice 3 is complete and recorded: the Hymns step is live; <n> follow-ups. Slice 4 can start from `main`."

- [ ] **Step R (only if the 3b release must come out): Revert**

Use this only when the production site cannot serve, or the builder breaks sign-in or the church pages, after the merge, and a fix would take too long. 3b wrote nothing to the database and changed no API shape, so a revert is code only; drafts in members' browsers stay valid for 2c's code (3b changed no draft field, and a hymn pick stays in the draft for the Hymns step to show again later). On the owner's yes for each command that leaves this machine:

```bash
git fetch origin
git switch -c claude/revert-slice-3b origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 3b (PR #<N>): back to the 3a release" -m "The 3b merge <what failed>. 3b changed no database, API shape or draft
shape, so nothing else needs undoing; the AI prompt loses its season line.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
.venv/bin/python -m pytest -q | tail -1
git push -u origin claude/revert-slice-3b
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-3b --title "Revert slice 3b" \
  --body "Reverts the slice 3b merge (PR #<N>) because <what failed>. No database change to undo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/revert-slice-3b -R bbrown62450/church --watch
```

**Expected:** Vitest `Test Files  55 passed (55)`, `Tests  356 passed (356)` (if anything else merged after 3b, it differs by exactly those tests); `1106 passed, 11 skipped`; every check passes. Merge on the owner's yes, then the owner checks that the site signs in and shows the builder with Hymns "Available soon". Record the revert as a row of the slice 3b record (or its own records PR if Step 12 already merged).

Expected counts after this task: frontend `421 passed` in 64 files on `main`; backend `1110 passed, 11 skipped` (CI `backend-postgres`: `11 passed, 1110 deselected`). The records PR adds no test.

---

## Lessons carried from the slice 2 and 3a builds (P2c, P3a "Build notes")

- **The container restarts.** Uncommitted work can be lost: commit as soon as a task's checks pass, and back the branch up with `git push origin claude/slice-2-plan-4q33le` after every task's review. If `node_modules` is gone after a restart, `(cd frontend && npm ci)`.
- **The network is filtered.** The npm registry, PyPI and raw.githubusercontent.com are reachable; ui.shadcn.com, Railway, OpenAI, Supabase and the reading sites are not. No test may need the network (the fake API fails a test on any unhandled request, which is why T11 and T12 add the matches and hymn answers to existing tests); T7 plans for the blocked registry, T14 Step 4 for a font fetch failure, and T15 Step 3 for an unreachable Vercel.
- **Tests that depend on the date fake `Date`** (`DRAFT_NOW`, Tuesday, September 29, 2026). T14 runs the suite with the real clock moved 8 and 400 days forward. Calling `vi.useFakeTimers` a second time keeps the first call's `toFake` list: call `vi.useRealTimers()` first (T10's "Still working" test).
- **Don't prove absence by sleeping.** Wait for a positive condition that comes after, then check the absence (T8's church-switch Undo test waits for a later write in the other church).
- **Turbopack refuses a symlinked `node_modules`**; a throwaway worktree copies it with `cp -al`.
- **Grep gates exclude tests** and are judged, not obeyed blindly: a hit may be a comment; read the line and explain it in the report.
- **Counts are exact.** Every task states its cumulative count; a drift means a missing or extra test, found before moving on.
- **Owner steps one at a time, in plain words**, and every outward action (PR, ready, merge, settings) on its own yes.

## Build notes (3b build)

Filled in while Tasks 1-13 are built: each change from the plan as written, its reason, and whether the owner saw it. Task 13 (or a follow-up docs commit before Task 14) writes those that alter S or F as "(3b build)" notes.

**Plan fixes made while finishing this plan (2026-09-29, before the build):**
- The plan was written in two sessions. The first wrote the header, Global Constraints, Owner decisions and Tasks 1-5, but not the "Baselines and counts" table, the "Spec clarifications" that Tasks 2-5 cite (2, 5, 9, 10, 12, 21), the risks or the File Structure; the second added them without changing Tasks 1-5, keeping the numbers those tasks already cite. It also added T4-T5's review checkpoint.
- Tasks 2-13 were then replayed mechanically from this document onto a clean worktree at `b47abba` (every script in order); see "Facts checked for this plan".

**T1's finding (owner answer 2):** <outcome A, B, C or D, in one sentence, without ids; the owner's choice; Task 1b's commit if any.>

**Review fixes under owner decision 1 (no owner-visible change unless marked):**
- <none yet>

**Owner answers during the build:**
- <none yet>

**Carried to later slices:**
- (4) The Liturgy step adds `"liturgy"` to `SHIPPED_STEPS` and replaces the summary's Liturgy block; `SummaryHymns` is its model.
- (5a) The new app records hymn use on every save (`hymn_usage`), so the recent-use window no longer depends on the old app's Word copies; archived picks with `hymn_id: null` show "Not in your hymnal" until 5a maps them.
- (6a) Settings → Hymns flips `SETTINGS_HYMNS_READY`, invalidates the hymns, hymnals and profile keys on every hymn change, and reuses `SearchCombobox` if it wants a long list.

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-3-hymns-design.md`; F = foundations. Items owned by 3a or later slices are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1-9, 15, 16, 18, 19 | The four routes, the OpenAI client, the matcher, the window, errors, rate limit, isolation, deletions, gzip, deadline, rubric | 3a (done); T2 adds the season line to 19's prompt |
| 10 | `/builder/hymns` replaces the placeholder; "n of 3", then ✓; three slots at 375 px; the summary lists the slots; "Still needed" lists each empty one | T8-T11 (the step), T12 (the shell), T15 Steps 4-10 (deployed) |
| 11 | Suggest fills only empty slots, 2-4 ideas per slot, a tap swaps both ways, ideas hide after a date change | T4 (`applySuggestions`, `swapAlternative`), T10 (the flow), T15 Step 7 |
| 12 | Toggling exclusion never changes `draft.hymns.slots`; a recent pick shows its notice | T9 ("exclusion never clears a pick"), T8 (notices) |
| 13 | A deleted or `hymn_id: null` pick shows "Not in your hymnal…", never crashes or disappears | T4 (`reconcilePick`), T8 |
| 14 | A load failure shows Retry, not the empty state; an empty hymnal shows the empty state | T8 |
| 17 | The manual checklist on production at 375 px and on desktop; the Streamlit smoke | T13 (checklist), T15 (guided owner check, optional smoke) |
| 20 | "Written {year}" on exactly the flagged hymns in the picker, cards, chips and matches | T5 (`newerYearLabel`, `chipName`), T8 (`HymnLabel`), T10, T11, T15 Step 7 |

### S sections

| S item | Task(s) |
|---|---|
| Layout (375 px), Slot cards (titles, filled, empty, live data, remove, Undo toasts, notices) | T8 |
| Other ideas (AI chips) | T10 |
| Picker (`HymnPicker` over `SearchCombobox`), ranking and hints | T5 (`filterHymns`), T7, T8 |
| Toolbar (hymnal Select, selected hymnal, notes, Exclude switch) | T4 (`selectHymnal`), T9 |
| Toolbar (Suggest), AI suggestion flow 1-5 | T6 (`useSuggestHymns`), T10 |
| Hymns for the readings | T5 (`buildMatchRefs`), T6, T11 |
| Newer-hymn year label | T5, T8, T10, T11 |
| Whole-step states | T8 (loading, failed, empty), T9 (toolbar skeleton) |
| Builder shell: Hymns status and summary; Frontend "Builder shell" | T12 |
| Frontend Files | T4-T12 (clarifications 3-5) |
| Queries; "Client timeouts" | T6 |
| Draft usage | T3 (owner answer 1), T4 |
| Pure-function contracts, `buildMatchRefs`, `buildSuggestionRequest` | T4, T5 (clarifications 9, 10) |
| Stale and cross-church protection | T6, T8 (`useUndoToasts`), T10 |
| Behavior changes 1-5, 10-13, 15, 16, 19, 20 (screen halves) | T8-T12 |
| Backend 3.6 step 7 (the prompt) | T2 (owner answer 3) |
| Backend 3.4 (the recent-use window, as found in production) | T1 (owner answer 2) |
| Testing "Frontend (Vitest)" and the port-ledger rows | T4-T12 (clarification 1) |
| Manual checks 1-10 | T13 (appended with 11 and 12), T15 (owner) |
| Interfaces rows 2, 5a, 6a (the screen's halves) | T12 (row 2), T4 and T9 (row 5a: the hymnal is sent as stored), T6 (row 6a: `SETTINGS_HYMNS_READY`, the matches key under the hymns prefix) |

## Questions for the owner

The owner's answers of 2026-09-29 (1-5, "all recommended") are binding and already in the plan. These plan choices are visible to the owner; each has a recommendation. They do not hold up the build: the plan is written as recommended, and a different answer changes the named task before or during its build.

1. **Suggest's network and server errors show as a pop-up message** ("Something went wrong. (Ref: …)"), as everywhere else in the app, while the AI's own problems show in the box under the button (clarification 8). Recommended: as written.
2. **Where "used within 12 weeks" shows** (clarification 11): under a chosen hymn only when the service date is valid; on picker rows only while Exclude is off; always on other ideas; on hymns for the readings whenever they are shown, also after **Show them**. Recommended: as written.
3. **Counts of one read naturally**: "1 hymn is hidden.", "1 more used within 12 weeks is hidden.", "1 recently used match is hidden." and "1 recently used hymn was left out." (clarification 13). Recommended: accept.
4. **Screen-reader names** (clarification 14): the ideas are read as "Use Amazing Grace as the opening hymn", and each **Add** button in Hymns for the readings as "Add Amazing Grace". Recommended: accept.
5. **Screens already built now include Hymns** (clarification 16): the step bar counts Hymns, Review lists "No Opening hymn — Choose one" and the like, and the summary lists the three hymns. Recommended: as written (this is what the slice 3 spec asks).
6. **The two hidden counts** (clarification 22): the toolbar counts every recently used hymn in the hymnal; the picker's list counts only those matching what was typed. Recommended: as written.
7. **What makes "New service" ask, and the church season** (clarifications 2 and 21): these follow owner answers 1 and 3 exactly; they are listed so the phone check (T15 Steps 7 and 9) can confirm them.
