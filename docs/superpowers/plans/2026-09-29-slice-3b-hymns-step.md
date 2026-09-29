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

