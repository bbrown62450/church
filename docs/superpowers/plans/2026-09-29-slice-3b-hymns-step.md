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

