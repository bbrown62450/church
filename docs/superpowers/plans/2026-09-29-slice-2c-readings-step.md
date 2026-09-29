# Slice 2c: Date & readings Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 2c of slice 2, the Date & readings step, live. After it merges, a signed-in member who opens https://worship-service-builder.vercel.app lands on step 1 of the Service Builder with next Sunday (in the church's time zone) already filled in: the occasion and the lectionary readings, looked up 400 ms after the date settles. The member can pick any date (weekday feasts are found; any other date falls back to typing), choose between several reading sets, type their own occasion and readings without the app ever overwriting them, read the passage text in a chosen translation, and pick the bulletin's Old and New Testament readings, where a Psalm is never the automatic New Testament reading. The step bar counts Date & readings ("1 of 3", then "Complete"), Review lists what is still needed, and the summary shows the occasion and readings with their OT and NT marks. Hymns, Liturgy and Review keep the "Available soon" card with no link to the old app. "New service" now asks first after the member picked a date, chose a reading set or chose a translation (owner answer Q2). The backend does not change (one docs test pins one more heading), there is no migration, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** 2b built every pure piece (the draft store, the readings transitions and selectors, `lib/dates.ts`, `lib/scripture-refs.ts`); 2c adds the queries and the screen. `src/lib/queries/` gains `lectionary.ts` (`useLectionary`), `reference.ts` (`useTranslations`) and `passages.ts` (`usePassage`, the 3-at-a-time `passageLimiter`, `passageText` for slice 3). `src/lib/use-debounced-value.ts` trails a value by 400 ms. `src/components/builder/lectionary-sync.tsx` holds `useLectionarySync()`: `BuilderShell` renders `<LectionarySync>` inside `DraftProvider`, so on every step the draft's date is looked up once it settles and empty or older lectionary fields are filled, in the visible tab only (a tab shown again first re-reads the stored draft, `DraftStore.syncFromStorage()`, so it never fills over another tab's newer typing); the step reads the same lookup through `useLectionaryLookup()`. `src/components/builder/readings/` holds the step: `ReadingsStep` stacks `ServiceDateField`, `LectionaryStatus` (loading, the set switcher `ReadingSetPicker`, no readings, unavailable, rate limited, partial, stale fields, the "Readings … are available" banner and `ReplaceReadingsDialog`), `OccasionField`, `ScriptureLinesField`, `ReadingsList` (`TranslationSelect`, `ReadingRow`, `PassageText`) and `BulletinReadingsPicker`. `readings.ts` gains `chooseReadingSet` and `status.ts`'s `isPristine` counts a picked date, a chosen set and a translation (owner answer Q2). Base UI's `radio-group`, `collapsible` and `tooltip` are added; the slice 1 kit's `ErrorState` and `ConfirmDialog` gain label options. Last, `SHIPPED_STEPS` gains `"readings"` and the readings route renders the step. Every page stays a client component (F §4.1).

**Tech Stack:** Next 16.3.6 (App Router, Turbopack), React 19.2.8, TypeScript 5, Tailwind 4, Base UI 1.8 (shadcn "base-nova"), TanStack Query 5, sonner, zod 4.6.5, Vitest 3.2.7 (`unit` node and `dom` jsdom projects) with Testing Library; the backend (Python 3.11, FastAPI) is not changed; GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Vercel (frontend), Railway (API), Supabase Postgres.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`. The 2c parts: the slice split at the top (lines 5 and 7), Hand-offs rows for 3 ("Passages", `passageText`) and 5a ("Readings"), User experience "Step 1 — Date & readings" items 1-8 and "Other states and messages", API "Status rules" (the bodies the client reads), "Client timeouts", Frontend changes ("Routes and files" readings components, "Draft store" `readings.ts`, `useLectionarySync()`, `status.ts`, "Queries"), Behavior changes 3-6 and 12-17, Testing "Frontend" (`use-debounced-value`, `queries/passages`, `readings-step`), "Manual checks", AC14-AC16 and AC18, open question 2, and every "(2a plan)", "(2a build)", "(2b plan)" and "(2b build)" note.
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (§1.8 timeouts and buckets, §4.1, §4.4 queries, §4.6 draft rules, §4.7, §4.8 error states and copy, §4.9 Base UI and mobile, §4.10, §5.2, §5.5).
- Slice 2b plan ("P2b"): `docs/superpowers/plans/2026-09-28-slice-2b-frontend.md`, its structure and conventions, its "Build notes (2b build)" (carried items below) and "Lessons carried". Slice 2a plan ("P2a"): `docs/superpowers/plans/2026-09-28-slice-2a-backend.md` (the route bodies).
- The real code at `0f6fcbc` (slices 2a and 2b merged): `frontend/src/lib/draft/*` (`readings.ts` transitions and selectors, `status.ts`, `store.ts` roll-forward, `context.tsx`), `lib/dates.ts`, `lib/scripture-refs.ts`, `lib/queries/{client,keys,church}.ts` (`keys.lectionary`, `keys.translations` and `keys.passage` already exist), `lib/api/{client,errors,timeouts,types}.ts` and `schema.d.ts` (`LectionaryOut`, `TranslationsOut`, `PassagesOut`, `PassageOut`, `PassageSectionOut`, `ChurchProfileOut`), `components/builder/*`, `components/app/{error-state,confirm-dialog,empty-state}.tsx`, `components/ui/*`, `test/{fake-api,render,mocks,setup-dom}.ts(x)`, `test/fixtures/index.ts`; and the backend routes `backend/api/routes/{lectionary,scripture,reference}.py` with `domain_errors.RateLimited`, `UpstreamError`, `UpstreamTimeout` and `InvalidInput`.
- Production facts: frontend https://worship-service-builder.vercel.app (Vercel), API https://church-production-74ca.up.railway.app (Railway, ESV key set, so `GET /translations` lists ESV); `docs/ops-runbook.md` "Slice 2a record" and "Slice 2b record".
- Facts checked for this plan (tree `0f6fcbc`, slices 2a and 2b merged and live):
  - Frontend baseline `299 passed` in 49 files; `npm run typecheck` and `npm run lint` clean; backend baseline `971 passed, 9 skipped`.
  - The route bodies the client reads: `GET /lectionary/readings` answers 200 `LectionaryOut` (`status` `ok` or `no_readings`), 422 `invalid_request` (`fields.date`), 429 `rate_limited` (`Retry-After`, `details.retry_after_seconds`), 502 `upstream_error` / 504 `upstream_timeout` with "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."; `POST /scripture/passages` answers 200 with per-passage and per-section `ok`/`not_found`/`unavailable` (upstream failures are data, never 5xx), 422 with `fields.refs` ("Too many passages in one request." for more than 20 parts), 429 as above; `GET /translations` lists `web` first and `esv` last when configured. `apiFetch` already reads `Retry-After` (or `details.retry_after_seconds`) into `ApiError.retryAfterSeconds`.
  - The build container reaches registry.npmjs.org and raw.githubusercontent.com (checked 2026-09-29) but not ui.shadcn.com (`CONNECT tunnel failed, response 403`), Railway or the reading sites. No test needs the network.
  - Every task's code below was written and run by the plan's writer in a throwaway worktree at `0f6fcbc` (hard-linked `node_modules`, `cp -al`). Then T1-T12 were replayed mechanically from this document onto two further clean worktrees at `0f6fcbc` (every "Create", "Replace" and "Append" block, each import-block replacement and each edit script, in order): after each task the suite gave exactly the count in the table below with typecheck and lint clean, each "see them fail" step printed the output quoted in it (timings shown as `<t>`), and the two replays produced the same tree. On the replayed tree the full suite ran three times at `346 passed` in 55 files, and with the real clock moved 0, 8 and 400 days forward, with no `act` warnings; `next build` compiled and listed the five builder routes; `npm run gen:api` changed nothing; T13's gates and T12's checks gave their stated outputs; the backend suite stayed at `971 passed, 9 skipped`. Not run while planning: a successful `shadcn add` (the registry is blocked; T4 records the failure message), the pushes and CI (T13), and the OWNER steps (T14).
  - After the plan review (2026-09-29, the "Plan: slice 2c review fixes and owner answers" commit), T1-T12 were replayed again the same way onto a clean worktree at `0f6fcbc`: every task gave the count in the table, typecheck and lint stayed clean, and the replayed `frontend/src` was identical to the tree the fixes were written in; the full suite passed at `346 passed` in 55 files three times, including with the real clock moved 8 and 400 days forward, with no `act` warnings, and `next build` compiled and listed the five builder routes. The review's changes are clarifications 7, 8, 10, 13-15 and 21, the accepted translation case in clarification 2, the test rule in "Code rules", and the review questions at the end.
  - Where S and the code or F disagreed, the code and F won; each case is a numbered clarification below.

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run the frontend as `(cd frontend && …)` from the repo root; the working directory resets between commands. Use absolute paths when a tool asks. No foreground `sleep`.
- Run one test file with `(cd frontend && npx vitest run <path> 2>&1 | tail -15)`. Run the whole suite with `(cd frontend && npm test 2>&1 | tail -6)`, then `(cd frontend && npm run typecheck && npm run lint)`.
- Run the backend suite only where a step says so: `.venv/bin/python -m pytest -q | tail -1` (expected `971 passed, 9 skipped` at every point; 2c changes no backend code, and T12's one docs-test edit changes an assertion, not the count).
- `node_modules` exists. If it is missing after a container restart, run `(cd frontend && npm ci)` (the npm registry is reachable). Turbopack refuses a symlinked `node_modules`: `npm run build` runs in the real checkout (T13), and a throwaway worktree copies it with `cp -al`, never `ln -s`.
- Branch: `claude/slice-2-plan-4q33le`, at `origin/main` `0f6fcbc` plus this plan's commit. The first commit is this plan, at `docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md`.
- Stage files by name (paths with parentheses in single quotes). `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Commits end with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. When the session's attribution asks for it, a `Claude-Session: <url>` line stands immediately before that final `Co-Authored-By` line (every commit template below allows it; T13 Step 6's trailer check matches the `Co-Authored-By` line anywhere in the message, and Step 8 compares subjects only). Subjects read "Area: plain words (F §x, S …)". Use TDD: write the failing test first and quote its failure.
- **Backup push after every task** (owner answer Q4, as in 2a and 2b): right after each task's commit, `git push origin claude/slice-2-plan-4q33le` (never `--force`; there is no open PR, so the push asks nobody; Vercel may build a preview). A fix asked for by the task's review is a new commit, `Fix: <what> (Task <n> review)`, pushed the same way (never an amend of a pushed commit); T13 Step 8 lists it. The container can restart and lose uncommitted work, so commit as soon as a task's checks pass. If the push is refused because the remote moved, stop and ask the controller.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and includes the line "Tests: frontend 299 → 346 in 49 → 55 files; backend 971 → 971 passed, 9 → 9 skipped".
- New prose for the owner has no em dashes. Code strings copied from S (for example "Too many requests — try again in N s.", "None — choose one", "Still working — this can take up to a minute.") keep theirs.

### Baselines and counts
- Starting baselines: frontend **299 passed in 49 files**, typecheck and lint clean; backend **971 passed, 9 skipped**. If any baseline differs, stop and ask.
- Planned cumulative frontend counts. Each delta is exactly the number of `it(` blocks the task adds (a modified test counts 0). If a count drifts, stop and find why.

  | After | Tests (delta) | Test files (delta) | Count |
  |---|---|---|---|
  | T1 | +3 (`draft/readings.test.ts` +1, `draft/status.test.ts` +1, `draft/store.test.ts` +1) | 0 | 302 in 49 |
  | T2 | +7 (`use-debounced-value.test.tsx` 3, `queries/lectionary.test.tsx` 3, `queries/reference.test.tsx` 1) | +3 | 309 in 52 |
  | T3 | +3 (`queries/passages.test.ts`) | +1 | 312 in 53 |
  | T4 | +2 (`error-state.test.tsx` +1, `confirm-dialog.test.tsx` +1) | 0 | 314 in 53 |
  | T5 | +6 (`builder/lectionary-sync.test.tsx`; `builder-shell.test.tsx`, `church-switch.test.tsx` and `draft/store.test.ts` edited, 0) | +1 | 320 in 54 |
  | T6 | +5 (`builder/readings/readings-step.test.tsx`, new) | +1 | 325 in 55 |
  | T7 | +5 (`readings-step.test.tsx`) | 0 | 330 in 55 |
  | T8 | +5 (`readings-step.test.tsx`) | 0 | 335 in 55 |
  | T9 | +7 (`readings-step.test.tsx`) | 0 | 342 in 55 |
  | T10 | +3 (`readings-step.test.tsx`) | 0 | 345 in 55 |
  | T11 | +1 (`builder-shell.test.tsx` +1; `status.test.ts` and two shell tests edited, 0) | 0 | 346 in 55 |
  | T12 | 0 | 0 | 346 in 55 |

- The backend stays at 971 passed, 9 skipped throughout. T12 edits one assertion in `backend/tests/test_slice1_docs.py` (the last `##` headings of `docs/manual-verification.md`); no test is added or removed. CI `backend-postgres` shows `9 passed, 971 deselected, 1 warning`.
- The readings-step tests fake only `Date` and run the 400 ms lookup delay, the draft's 400 ms writes, the list's 400 ms trail and two 1-second rate-limit waits on real timers, so `readings-step.test.tsx` takes about 6 s. One test fakes `setTimeout` as well (the 8-second "Still working" line) and says why.

### Code rules (F §4)
- Every file under `src/app/` that renders is a client component (`"use client"`, F §4.1). Pages and components never call `apiFetch` (F §4.4): the step uses the hooks in `lib/queries/`.
- Base UI rules (F §4.9): generated components only, hand edits limited to variants; no `asChild` (use `render`, or `buttonVariants` on the element); a Select gets `items` and shows "no selection" as `null` plus a placeholder, never a sentinel item; toasts stay on sonner. The one recorded exception is clarification 4 (the registry is blocked, as in 2b).
- Date-only values stay `YYYY-MM-DD` strings; nothing outside `lib/dates.ts` calls `new Date(` on a date-only value (`dates.guard.test.ts`, F acceptance 12). "Today" in the step is `todayIn(churchZone(profile))`.
- Browser storage goes through `lib/storage.ts` only (F §4.3); 2c adds no storage.
- User text, passage text and server messages render as React text only (`react/no-danger` is an error); passage text keeps its line breaks with `whitespace-pre-wrap`.
- Inputs are `text-base md:text-sm` (the generated `Input`, `Textarea`) so iOS does not zoom; primary actions and toggles are 44 px (`size="touch"`, `h-11`).
- DOM tests that depend on "today" fake only `Date` (`vi.useFakeTimers({ toFake: ["Date"] })` plus `vi.setSystemTime(DRAFT_NOW)`), so user-event's and the app's timers keep running. A test that must fake `setTimeout` too calls `vi.useRealTimers()` first: a second `useFakeTimers` call keeps the first call's Date-only fake.
- Grep gates exclude test files (P2b build notes).
- A test never proves that something did not happen by sleeping: it first waits for a positive condition that comes after it (a later request, the lookup's settled date, the draft's write), then checks the absence.

### Messages (verbatim, from S and F)
- Service date: label "Service date"; help "Readings and the occasion load automatically for this date."; "Choose a service date."; "Enter a date between 1900 and 2199."; "This date has passed."; "Not a Sunday. We'll look for this day's own readings, such as Ash Wednesday, Christmas Eve or Good Friday."; button "Use next Sunday ({Month D})".
- Lectionary: "Looking up the lectionary…"; after 8 s "Still working — this can take up to a minute."; legend "This date has more than one set of readings"; "No lectionary readings for {Weekday, Month D, YYYY}." with "Enter the occasion and readings below." and button "Enter readings"; "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes." with "Try again"; "Too many requests — try again in N s." with "Try again"; "One lectionary source didn't respond, so other reading options for this date may be missing."; "These readings are from {set name} ({Month D, YYYY}), not {Month D, YYYY}." with "Clear readings".
- Banner and dialog: "Readings for {Month D, YYYY} are available." with "Use them"; title "Replace your readings?", body "Your occasion and scripture list will be replaced with “{set name}” from the lectionary.", confirm "Replace readings", cancel "Keep mine".
- Occasion: label "Occasion"; help "Printed as the bulletin's title. Filled from the lectionary; edit if needed."; placeholder "e.g. Third Sunday of Easter"; "Too long (max 300 characters)."; captions "From the Revised Common Lectionary: {set name}", "Edited from the lectionary ({set name})", "Entered by you", "From the saved service".
- Scripture readings: label "Scripture readings"; help "One reference per line, for example Matthew 17:1-9. Filled from the lectionary; edit if needed."; placeholder "Matthew 17:1-9"; "Up to 20 readings."; "Line {n} is too long (max 200 characters)."
- Readings list: heading "Readings"; "Bible translation"; help "For the passage text shown here. The bulletin lists the references, not the verse text."; "Passage text shown in {label}."; "Show all text"; "Show text" / "Hide text"; badges "OT", "Psalm", "NT", "?" ("Book not recognized"); "Loading text…"; "Couldn't load {reference}."; "Part of this passage couldn't be loaded."; "Couldn't find this passage. Check the reference, for example “Matthew 17:1-9”."; "Passage text isn't available right now."; the server's 422 message "Too many passages in one request."; empty "Add a reading above to see its text and choose the bulletin readings."
- Bulletin readings: heading "Bulletin readings"; help "The bulletin prints one Old Testament and one New Testament reading."; "Old Testament reading", "New Testament reading"; placeholder "Automatic: {ref}" or "None — choose one"; "Use automatic".
- Unchanged from 2b: "Available soon" / "Keep using the current app for this part." (Hymns, Liturgy, Review; no link); "Still needed" rows "No service date — Choose one", "No occasion — Add one", "No scripture readings — Add one"; "Start a new service?" / "This clears the current draft on this device." / "Start new service".

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried over from 2a and 2b, owner answer Q4). Each use is recorded as a numbered clarification marked "(owner decision 1)".
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
3. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
4. **Spec decisions 1, 8 and 9:** the step builder (2b shipped the shell); any date, with manual entry when there are no readings; the readings fixes (Psalm never the automatic NT, stale lectionary fields kept and offered for clearing).
5. **Production:** frontend https://worship-service-builder.vercel.app (Vercel), API https://church-production-74ca.up.railway.app (Railway; the ESV key is set, so ESV is offered). The build container cannot reach Railway or the reading sites; no frontend test needs the network.

### Owner answers (2026-09-29, binding for the plan)
- **Q1: no Saturday vigil one-tap.** A Saturday service date falls back to manual entry like any date without readings. S open question 2 is closed as "no" (T12 notes it in S; clarification 3).
- **Q2: "New service" asks when the member has done any of three things:** picked a date (`date_origin: "user"`), chosen a reading set, or chosen a translation (`readings.translation` not null). The exact rule (clarification 2): `isPristine` also requires `date_origin !== "user"` and `translation === null`, and choosing a set in the switcher (`chooseReadingSet`) makes a `default` date the user's, so a chosen set counts without a new draft field. The mount-time roll-forward still requires a pristine draft whose `date_origin` is `default`, so it now also keeps the date of a draft with a translation override (T1 tests it). T12 notes the rule in S and F as "(2c plan)".
- **Q3: after the merge, a guided owner check on the phone of about six steps, then a quick look on a computer, given one step at a time:** next Sunday fills; a date with two sets; a weekday with no readings; typing your own reading; opening Bible text; choosing the bulletin readings (with "New service"). S requires the checklist in `docs/manual-verification.md` (its "Manual checks" heading says "append to"), so T12 appends "## Slice 2" and updates `backend/tests/test_slice1_docs.py`, which pins that file's last `##` headings (P2b clarification 29).
- **Q4: same process as 2a and 2b.** Subagent-driven, one task at a time with review, a backup push after each task, one PR; the owner is asked before the PR is opened, before it is marked ready, and before it is merged. The standing permission (owner decision 1) carries over.
- **Carried from the 2b build notes (binding):** the automatic fill runs only in the visible tab (`document.visibilityState === "visible"`), because adopting another tab's newer draft drops up to 400 ms of this tab's unwritten typing (T5); `"readings"` joins `SHIPPED_STEPS` and the readings route renders the step instead of `StepPlaceholder` (T11); Hymns, Liturgy and Review keep "Available soon" with no link to the old app. The 5a question (an archived service edited on its own date raises the banner) stays with 5a.

### The 2c scope (S lines 5 and 7 are authoritative)
S line 7 (a 2b plan note) gives 2c "the three query modules (`lectionary.ts`, `reference.ts`, `passages.ts`), `use-debounced-value.ts`, `useLectionarySync()`, the step's components, `radio-group`, `collapsible` and `tooltip`, and adds `"readings"` to `SHIPPED_STEPS`".

| Piece | Task | Note |
|---|---|---|
| `isPristine` (Q2) and `chooseReadingSet` | T1 | the only change to 2b's pure modules |
| `use-debounced-value.ts`, `queries/lectionary.ts`, `queries/reference.ts`, the two `timeouts.ts` entries | T2 | S Queries, "Client timeouts" |
| `queries/passages.ts` (`createLimiter`, `passageLimiter`, `passageText`, `usePassage`) | T3 | S Queries; `passageText` is slice 3's hand-off |
| `radio-group`, `collapsible`, `tooltip`; `ErrorState` and `ConfirmDialog` label options | T4 | clarifications 4 and 5 |
| `useLectionarySync()` in `BuilderShell` | T5 | S "useLectionarySync"; visible tab only |
| `ReadingsStep` and its twelve components | T6-T10 | S "Routes and files" |
| `"readings"` in `SHIPPED_STEPS`, the readings page | T11 | S steps.ts; turns on the status, "Still needed" and the summary blocks 2b built |
| S and F "(2c plan)" notes, the "## Slice 2" checklist, `test_slice1_docs.py` | T12 | S Manual checks |

## Spec clarifications

The code and F win over S's outline. Each item says whether the owner would notice it: **[owner-visible]** items are put to the owner in "Questions for the owner" at the end (confirm or change before T1 starts); the rest are owner decision 1 (no owner-visible change) or plain readings of S.

1. **The 2c scope** is the table above. S's Testing table names `use-debounced-value.test.ts`; it is `use-debounced-value.test.tsx`, because it renders the hook in jsdom (the `dom` project runs `*.test.tsx`). T2 also adds `queries/lectionary.test.tsx` and `queries/reference.test.tsx` (F §5.2: every query module is tested), and T5 puts the fill and debounce cases of S's `readings-step.test.tsx` into `builder/lectionary-sync.test.tsx`, since the sync lives in the shell and runs on every step.
2. **[owner-visible] What counts as unsaved work (owner answer Q2).** `isPristine` (and so `isDirty` until 5a saves drafts) is false after: a date the member picked (typed or picked in the date field; `date_origin: "user"`); a reading set chosen in the switcher (`chooseReadingSet` makes a `default` date the user's; the draft shape does not change); a translation other than the church's (`readings.translation` not null; choosing the church's own translation again stores `null` and counts as untouched). Not counted: "Use next Sunday", which puts back the default date with `date_origin: "default"`; the automatic fill; "Use them" on the banner (it only appears after a picked date or typed readings, which already count); "Clear readings" of stale lectionary fields. Consequences: "New service" asks "Start a new service?" in those cases, and a draft with any of them keeps its date after that Sunday passes (it shows "This date has passed." instead of moving to the next Sunday). Card toggles, hymnal overrides and hymn alternatives are slices 3 and 4's to decide (P2b build notes). Accepted, not fixed: a stored translation override that the translations list no longer offers (for example ESV after the server loses its key) still counts as work, although the screen shows the church's translation (`effectiveTranslation`). `isPristine` is a pure function of the draft, used by the store's mount-time roll-forward before any list is loaded and by `isDirty`; letting it see the list would mean passing the list through the store and `fingerprint.ts`. The effect is only that "New service" asks once more than needed, and such a draft keeps its date (owner decision 1).
3. **[owner-visible] No Saturday one-tap (owner answer Q1).** A Saturday finds no readings (Vanderbilt lists the Vigil on the Sunday), so it shows "No lectionary readings for Saturday, …" with "Enter readings". S open question 2 is closed as "no" (T12).
4. **`radio-group`, `collapsible` and `tooltip` are rebuilt from the upstream shadcn source**, as 2b did for `sheet` and `badge` (P2b clarification 3, owner answer A): T4 first runs `npx shadcn@latest add radio-group collapsible tooltip`; the registry (ui.shadcn.com) is blocked from the container (`CONNECT tunnel failed, response 403`, checked 2026-09-29), so T4 uses the files in this plan: shadcn-ui/ui@`db2db460` `apps/v4/registry/bases/base/ui/{radio-group,collapsible,tooltip}.tsx` with `style-nova.css` (sha256 recorded in T4), through the installed shadcn 4.21.0 CLI's `transformStyle` and Prettier 3 with `prettier-plugin-tailwindcss` (`tailwindFunctions: ["cn", "cva"]`). The same pipeline reproduces 2b's `badge.tsx` byte for byte (after its header comment). Each file's only change is a header comment. A later `shadcn add` can replace them. (Owner decision 1; the same exception the owner accepted for 2b.)
5. **`ErrorState` gains `message`, `retryLabel` and `retryDisabled`; `ConfirmDialog` gains `cancelLabel`** (slice 1's kit, defaults unchanged). S's copy needs "Try again" (F §4.8 says "Retry"), the lectionary's own sentence (a 502's `describeError` would read "Something went wrong. (Ref: …)"), a disabled button without a spinner while a rate limit's wait runs, and "Keep mine". The kit's existing tests are unchanged; one new test each.
6. **`useLectionarySync` lives in `components/builder/lectionary-sync.tsx`**, with `<LectionarySync>` (rendered by `BuilderShell` inside `DraftProvider`) sharing one lookup (one debounce, one query) with the step through `useLectionaryLookup()`. S puts the hook in `BuilderShell` and gives it no file. The fill's effect depends on "an automatic fill is due" computed from the current draft, so it also refills after "New service" on the same date; the recipe checks `shouldAutoApply` again against the latest draft (S).
7. **Only the tab on screen fills** (2b build notes; binding). `usePageVisible()` reads `document.visibilityState` through `useSyncExternalStore`; a hidden tab keeps the answer and fills when it is shown (T5 tests it). A tab that is shown again could fill its stale copy before the other tab's `storage` event arrives, and its fill, stamped later, would then outrank and overwrite the typing the other tab wrote as it was hidden. So `DraftProvider`'s `visibilitychange` listener, which already flushes on hide, calls the new `DraftStore.syncFromStorage()` on show: it re-reads the stored draft and adopts it when strictly newer, in the same event and before React renders the fill's effect (T5 tests a storage event that arrives only after the tab is shown). This touches `store.ts` and `context.tsx`, which 2c otherwise leaves alone. (Owner decision 1.)
8. **Any failure other than a 429 shows the lectionary's "couldn't be reached" copy** (S names 502, 504, network and timeout; a 422 cannot happen for a date the client sends, and a 500 is the same to the member). An answer already on screen wins over a failed background refetch (a partial answer is refetched after 5 minutes). The stale-fields note shows with "No readings" and "Unavailable", as S says, and also with the rate-limit card and for an empty or out-of-range date (where it is the only thing the status area shows); without a valid date to name, the sentence ends after the set: "These readings are from {set name} ({Month D, YYYY})." (Owner decision 1.)
9. **[owner-visible] The rate-limit number does not count down.** "Too many requests — try again in N s." shows the server's `Retry-After` as sent, and "Try again" turns on after N seconds (for the lectionary and for passage text). A live countdown would be announced every second by screen readers.
10. **[owner-visible] Occasion caption while the lookup is not loaded.** "Edited from the lectionary ({set name})" needs the set's name from that date's lookup; right after a refresh, before the lookup answers, the caption reads "Edited from the lectionary". The name is found with `selectedSetIndex` (the set equal to the draft's lines, else the stored index), so a refetch that lists the sets in another order never names the wrong set; a lectionary-filled occasion's caption uses the occasion itself, which is the set's name (owner decision 1).
11. **[owner-visible] The date field keeps the browser's picker within 1900-2199** (`min`/`max`); a typed year outside still shows "Enter a date between 1900 and 2199." and looks nothing up. An impossible date (a five-digit year) is stored as `""` (2b build) and asks "Choose a service date.".
12. **[owner-visible] Scripture line messages.** "Up to 20 readings." when more than 20 non-blank lines; for lines over 200 characters, the first one is named ("Line 3 is too long (max 200 characters)."), not every one.
13. **[owner-visible] The "?" badge on phones.** Base UI tooltips open on hover and keyboard focus, not on a tap, so on a phone the badge shows "?" only; "Book not recognized" is also its accessible name, so screen readers say it. Its target is at least 24 by 24 px on phones (`h-6 min-w-6`, back to the badge's 20 px from `sm`).
14. **Readings rows.** The list trails the textarea by 400 ms (S "debounced 400 ms"). Rows are keyed by position and text; open rows are remembered by reference text in component state, so leaving the step closes them, and "Show all text" is disabled while there are no readings. A closed row unmounts its text, so its request is cancelled (and dropped from the limiter's queue if it had not started). A line over 200 characters has its toggle `aria-disabled` (Base UI keeps a disabled trigger focusable) and is never sent. Each row's buttons are named with the reference ("Show text: Mark 1:1-8", "Hide text: …", "Try again: …"), so a screen reader's button list tells them apart. (Owner decision 1.)
15. **"Use them" uses `applyReadingSet`, the switcher `chooseReadingSet`.** The banner's set is the one the switcher shows (`selectedSetIndex`), else the lookup's default. A dialog confirmed after the date moved does nothing, and neither does a switcher choice that lands after it (both recipes check the date, so `chooseReadingSet` never sees another date's lookup). "Keep mine" hides the banner for this date in component state (S).
16. **The translation select is disabled until the list loads**, as well as when it fails (S names the failure), showing the church's `effective_translation_label`. It never stores the church's own translation (2b's `setTranslation`).
17. **Test helpers.** `test/fixtures/index.ts` gains `translations()` (T2), `noReadings(date)` and `lectionaryRoute(answer)` (T5). From T5 every builder test answers `GET /lectionary/readings` (the fake API fails a test on an unhandled request); the 2b shell and church-switch tests answer "no readings", so their drafts keep what they type. From T11 the shell tests also answer `GET /translations`.
18. **[owner-visible] What changes on screens 2b built** (the owner accepted this for 2c with 2b's owner answer Q1): the step bar shows Date & readings as "1 of 3", "2 of 3" or "Complete"; Review shows "Still needed" with the missing readings rows; the summary's Date block adds the occasion ("No occasion yet") and its Readings block lists the readings with "OT (auto)" / "NT" marks instead of "Available soon".
19. **The manual checklist** (T12): S's thirteen checks as "## Slice 2" in `docs/manual-verification.md`, with a Saturday added to check 2 (Q1), check 14 for "New service" (Q2), and "(owner, after 2c)" on the items the guided check covers (Q3). `test_slice1_docs.py` pins the last three `##` headings (`## Ops slice`, `## Slice 1`, `## Slice 2`) instead of two; its slice 1 section checks are unchanged (its `_section` stops at the next `##`).
20. **No backend change.** S's 2c items are all frontend; `schema.d.ts` already has every type (2a), so `npm run gen:api` changes nothing. T12's only Python edit is the docs test's heading assertion.
21. **Screen-reader roles and names** (owner decision 1). The "No lectionary readings" callout and the "Readings … are available" banner are information, so they use `role="status"` (polite) instead of the `Alert` component's default `role="alert"`; the lectionary's failure and rate-limit states keep `alert` (`ErrorState`). "Use automatic" is named for its side ("Use automatic Old Testament reading", "Use automatic New Testament reading"); the row buttons as in clarification 14.

### Risks carried into the plan
- **Live data.** The fixtures are synthetic (2a build); the lectionary and Bible sites are reached only from Railway. The owner's guided check (T14) is the first look at real answers in the new screen; a data surprise is a follow-up, not a 2c blocker, unless the step cannot be used.
- **Real-timer tests.** `readings-step.test.tsx` waits on real 400 ms and 1 s timers (the lookup delay, the list's trail, two rate-limit waits). T13 runs the suite three times and with the clock moved forward; a flaky run is fixed by making the test deterministic, never by retrying.
- **The module-level passage limiter** is shared by every test in a file; every fake passage handler settles, and a closed row's request is cancelled, so a slot is never held across tests.
- **Turbopack refuses a symlinked `node_modules`** (P2b); `npm run build` runs in the real checkout (T13).
- **The owner's phone check needs live readings.** If the lectionary is down during T14, the owner sees "The lectionary couldn't be reached."; T14 then records it and retries later rather than failing the slice.

## File Structure

All paths are from the repo root. "(church)" means `frontend/src/app/(signed-in)/(church)`; "readings/" means `frontend/src/components/builder/readings/`.

**Created**

| Path | Responsibility | Task |
|---|---|---|
| `docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md` | this plan (first commit) | 0 |
| `frontend/src/lib/use-debounced-value.ts` (+ `.test.tsx`) | `useDebouncedValue` | T2 |
| `frontend/src/lib/queries/lectionary.ts` (+ `.test.tsx`) | `useLectionary`, `canLookUp`, `lectionaryStaleTime` | T2 |
| `frontend/src/lib/queries/reference.ts` (+ `.test.tsx`) | `useTranslations` | T2 |
| `frontend/src/lib/queries/passages.ts` (+ `.test.ts`) | `createLimiter`, `passageLimiter`, `passageText`, `passageStaleTime`, `usePassage` | T3 |
| `frontend/src/components/ui/radio-group.tsx`, `collapsible.tsx`, `tooltip.tsx` | Base UI components (clarification 4) | T4 |
| `frontend/src/components/builder/lectionary-sync.tsx` (+ `.test.tsx`) | `useLectionarySync`, `LectionarySync`, `useLectionaryLookup`, `usePageVisible`, `LOOKUP_DELAY_MS` | T5 |
| `readings/service-date-field.tsx` | the "Service date" card | T6 |
| `readings/occasion-field.tsx` | Occasion, `occasionCaption`, `readingSetName` | T6 |
| `readings/scripture-lines-field.tsx` | Scripture readings, `scriptureProblems`, `MAX_READINGS`, `MAX_LINE` | T6 |
| `readings/readings-step.tsx` (+ `readings-step.test.tsx`) | `ReadingsStep` (grows in T7, T9, T10) | T6 |
| `readings/lectionary-status.tsx` | `LectionaryStatus` (T7), with the sets and banner (T8) | T7, T8 |
| `readings/use-wait-over.ts` | `useWaitOver`, `retryAfter`, `rateLimitMessage` | T7 |
| `readings/reading-set-picker.tsx` | `ReadingSetPicker` | T8 |
| `readings/replace-readings-dialog.tsx` | `ReplaceReadingsDialog` | T8 |
| `readings/translation-select.tsx` | `TranslationSelect` | T9 |
| `readings/passage-text.tsx` | `PassageText` | T9 |
| `readings/reading-row.tsx` | `ReadingRow` and its testament badges | T9 |
| `readings/readings-list.tsx` | `ReadingsList` | T9 |
| `readings/bulletin-readings-picker.tsx` | `BulletinReadingsPicker` | T10 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `frontend/src/lib/draft/readings.ts`, `status.ts` (+ `readings.test.ts`, `status.test.ts`, `store.test.ts`) | `chooseReadingSet`; `isPristine` (owner answer Q2) | T1 |
| `frontend/src/lib/api/timeouts.ts` | lectionary 25 s, passages 30 s | T2 |
| `frontend/src/test/fixtures/index.ts` | `translations()` (T2); `noReadings`, `lectionaryRoute` (T5) | T2, T5 |
| `frontend/src/lib/api/types.ts` | `Passages`, `Passage`, `PassageSection` | T3 |
| `frontend/src/components/app/error-state.tsx`, `confirm-dialog.tsx` (+ tests) | label options (clarification 5) | T4 |
| `frontend/src/components/builder/builder-shell.tsx` | renders `<LectionarySync>` | T5 |
| `frontend/src/lib/draft/store.ts`, `context.tsx` (+ `store.test.ts`) | `syncFromStorage()`, called when the tab is shown again (clarification 7) | T5 |
| `frontend/src/components/builder/builder-shell.test.tsx` | answers the lookup (T5); the shipped step, `GET /translations`, one new test (T11) | T5, T11 |
| `frontend/src/components/builder/church-switch.test.tsx` | answers the lookup | T5 |
| `frontend/src/lib/draft/steps.ts`, `(church)/builder/readings/page.tsx`, `frontend/src/components/builder/step-placeholder.tsx` | `"readings"` shipped; the page renders the step | T11 |
| `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` | "(2c plan)" notes, one F amendment row | T12 |
| `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | "## Slice 2"; the heading pin | T12 |

**Untouched:** every Python file except `backend/tests/test_slice1_docs.py`, `backend/requirements*.txt`, migrations, `frontend/package.json` and `package-lock.json` (no new dependency: `@base-ui/react` already has radio, collapsible and tooltip), `frontend/src/lib/api/openapi.json` and `schema.d.ts`, `frontend/src/lib/draft/{schema,migrate,mapping,fingerprint,prune,date-effects}.ts`, `docs/ops-runbook.md` until T14's record, Streamlit files, CI workflows.

**Task order and checkpoints:** T1 → T2 → … → T12 → T13 → T14. Each of T1-T12 ends in one commit, a review and a backup push (owner answer Q4). With the plan commit, the branch carries 13 commits before T13. The review checkpoints are stops for the controller, not merges: everything ships in the one 2c PR.

---

### Task 1: "New service" asks after a picked date, a chosen reading set or a translation (owner answer Q2; S "status.ts" `isPristine`, "Mount-time roll-forward"; AC17; clarification 2)

`isPristine` decides whether "New service" asks first (through `isDirty` while nothing is saved) and whether the mount-time roll-forward may move a passed default date. Owner answer Q2 adds three kinds of work to it. A picked date already has `date_origin: "user"`; a translation override is `readings.translation !== null`; a set chosen in the switcher gets a new transition, `chooseReadingSet`, which applies the set like `applyReadingSet` and makes a `default` date the user's. The automatic fill keeps using `applyReadingSet`, so a fresh draft filled by the lectionary stays pristine. Nothing on screen changes yet (the step arrives in T6-T11).

**Files:**
- Modify: `frontend/src/lib/draft/readings.ts` (`chooseReadingSet`), `frontend/src/lib/draft/status.ts` (`isPristine`)
- Test: `frontend/src/lib/draft/readings.test.ts` (+1), `frontend/src/lib/draft/status.test.ts` (+1, and four cases added to an existing test), `frontend/src/lib/draft/store.test.ts` (+1)

**Interfaces:**
- Consumes: `applyReadingSet`, `withReadings`, `setDate`, `setTranslation` (`readings.ts`, 2b); `rollForward` (`store.ts`, 2b; unchanged).
- Produces:
  - `chooseReadingSet(d: DraftV1, lect: Lectionary, i: number): DraftV1`: `applyReadingSet(d, lect, i)`, then `date_origin: "user"` when it was `default` and the draft changed; returns `d` itself when nothing changes. Later user: T8 (the set switcher).
  - `isPristine(draft)` is also false for `date_origin === "user"` or `translation !== null`.

Counts after this task: frontend **302 passed in 49 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -2
grep -c "chooseReadingSet" frontend/src/lib/draft/readings.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
.venv/bin/python -m pytest -q | tail -1
```

**Expected,** in order: nothing, or only `?? .claude/`; the plan commit `<sha> Plan: slice 2c Date & readings step (S slice 2; owner answers 2026-09-29)` above `0f6fcbc Merge pull request #23 from bbrown62450/claude/slice-2-plan-4q33le`; `0` (grep exits 1); ` Test Files  49 passed (49)` and `      Tests  299 passed (299)`; `> tsc --noEmit` and `> eslint` with nothing after them; `971 passed, 9 skipped in <t>s`. If `node_modules` is missing, run `(cd frontend && npm ci)` first. Any other baseline: stop and ask.

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


edit("frontend/src/lib/draft/readings.test.ts", [
    ("import {\n  applyReadingSet,\n  clearReadings,",
     "import {\n  applyReadingSet,\n  chooseReadingSet,\n  clearReadings,"),
    ('''  it("shouldAutoApply replaces empty fields''',
     '''  it("chooseReadingSet applies the chosen set and makes a default date the user's (owner answer Q2)", () => {
    const chosen = chooseReadingSet(filled(), lectionary(OCT_4), 1);
    expect(chosen.readings).toMatchObject({
      occasion: "Resurrection of the Lord",
      fields_origin: "lectionary",
      reading_set: { date_iso: OCT_4, index: 1 },
      date_origin: "user",
    });
    const shown = filled();
    expect(chooseReadingSet(shown, lectionary(OCT_4), 0)).toBe(shown); // already shown: nothing changes
    const archivedDate = testDraft((d) => ({ ...d, readings: { ...d.readings, date_origin: "archive" } }));
    expect(chooseReadingSet(archivedDate, lectionary(OCT_4), 0).readings.date_origin).toBe("archive");
  });

  it("shouldAutoApply replaces empty fields'''),
])

edit("frontend/src/lib/draft/status.test.ts", [
    ('import { applyReadingSet, editOccasion, editScriptureLines, setDate, setPick } from "./readings";',
     'import {\n  applyReadingSet,\n  chooseReadingSet,\n  editOccasion,\n  editScriptureLines,\n  setDate,\n'
     '  setPick,\n  setTranslation,\n} from "./readings";'),
    ('''      ["archive fields", testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "archive" } }))],
    ];''',
     '''      ["archive fields", testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "archive" } }))],
      // Owner answer Q2 (2026-09-29): a picked date, a chosen reading set and a translation override.
      ["a picked date", setDate(testDraft(), "2026-10-11")],
      ["the same date picked by hand", setDate(testDraft(), "2026-10-04")],
      [
        "a chosen reading set",
        chooseReadingSet(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), lectionary("2026-10-04"), 1),
      ],
      ["a translation", setTranslation(testDraft(), "kjv", "web")],
    ];'''),
    ('''describe("stillNeeded''',
     '''describe("isPristine and the date and translation defaults (owner answer Q2)", () => {
  it("stays true for the default date, a lectionary fill of it, Use next Sunday and the church's own translation", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    expect(isPristine(filled)).toBe(true);
    // "Use next Sunday" sets the date with origin "default"; the church's translation is stored as null.
    expect(isPristine(setDate(setDate(testDraft(), "2026-10-11"), "2026-10-04", "default"))).toBe(true);
    expect(isPristine(setTranslation(testDraft(), "web", "web"))).toBe(true);
    expect(isPristine(setTranslation(setTranslation(testDraft(), "kjv", "web"), "web", "web"))).toBe(true);
    const archivedDate = testDraft((d) => ({ ...d, readings: { ...d.readings, date_origin: "archive" } }));
    expect(isPristine(archivedDate)).toBe(true);
  });
});

describe("stillNeeded'''),
])

edit("frontend/src/lib/draft/store.test.ts", [
    ('import { applyReadingSet, editOccasion, editScriptureLines, setPick, shouldAutoApply } from "./readings";',
     'import {\n  applyReadingSet,\n  chooseReadingSet,\n  editOccasion,\n  editScriptureLines,\n  setPick,\n'
     '  setTranslation,\n  shouldAutoApply,\n} from "./readings";'),
    ('''describe("DraftStore changes (S store.ts)", () => {''',
     '''describe("DraftStore roll-forward and owner answer Q2", () => {
  it("keeps a passed default date when a reading set was chosen or a translation picked", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const cases: [string, DraftV1][] = [
      ["a chosen set", chooseReadingSet(filled, lectionary("2026-10-04"), 1)],
      ["a translation", setTranslation(filled, "kjv", "web")],
    ];
    for (const [name, draft] of cases) {
      const { store } = makeStore(memoryStorage({ [KEY]: JSON.stringify(draft) }).storage, tenDaysLater.now);
      expect(store.getSnapshot().draft.readings.date_iso, name).toBe("2026-10-04");
    }
    const { store } = makeStore(memoryStorage({ [KEY]: JSON.stringify(filled) }).storage, tenDaysLater.now);
    expect(store.getSnapshot().draft.readings.date_iso).toBe("2026-10-11"); // the automatic fill alone rolls
  });
});

describe("DraftStore changes (S store.ts)", () => {'''),
])
print("T1 tests written")
PYEOF
```

**Expected:** `T1 tests written`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/readings.test.ts src/lib/draft/status.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "^ (FAIL|×)|TypeError|AssertionError|Tests ")
```

**Expected:**

```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/draft/readings.test.ts > readings transitions (S readings.ts) > chooseReadingSet applies the chosen set and makes a default date the user's (owner answer Q2)
TypeError: (0 , chooseReadingSet) is not a function
 FAIL  |unit| src/lib/draft/status.test.ts > isPristine (S status.ts) > is false once anything the user would lose is there
TypeError: (0 , chooseReadingSet) is not a function
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore roll-forward and owner answer Q2 > keeps a passed default date when a reading set was chosen or a translation picked
TypeError: (0 , chooseReadingSet) is not a function
      Tests  3 failed | 27 passed (30)
```

- [ ] **Step 4 (agent): Write `chooseReadingSet` and the new `isPristine` rule**

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


edit("frontend/src/lib/draft/readings.ts", [
    ('''/** Auto-fill applies only to empty fields, or to lectionary fields from another date. */''',
     '''/**
 * The set switcher's choice (S UX item 2): applies set `i` like
 * `applyReadingSet`, and a choice that changes the draft also makes a
 * `default` date the user's (owner answer Q2, 2026-09-29), so "New service"
 * asks first and the mount-time roll-forward keeps the date.
 */
export function chooseReadingSet(d: DraftV1, lect: Lectionary, i: number): DraftV1 {
  const next = applyReadingSet(d, lect, i);
  if (next === d || next.readings.date_origin !== "default") return next;
  return withReadings(next, { date_origin: "user" });
}

/** Auto-fill applies only to empty fields, or to lectionary fields from another date. */'''),
])

edit("frontend/src/lib/draft/status.ts", [
    ('''/**
 * "Nothing the user would lose" (S "status.ts"), decided by origins rather
 * than text, so defaults that later slices fill in (slice 4's benediction)
 * never make a fresh draft look edited.
 */
export function isPristine(draft: DraftV1): boolean {
  const r = draft.readings;
  const l = draft.liturgy;
  return (
    (r.fields_origin === "empty" || r.fields_origin === "lectionary") &&''',
     '''/**
 * "Nothing the user would lose" (S "status.ts"), decided by origins rather
 * than text, so defaults that later slices fill in (slice 4's benediction)
 * never make a fresh draft look edited. A date the user picked, a reading set
 * chosen in the switcher (which makes the date the user's, `chooseReadingSet`)
 * and a translation override count as work (owner answer Q2, 2026-09-29).
 */
export function isPristine(draft: DraftV1): boolean {
  const r = draft.readings;
  const l = draft.liturgy;
  return (
    r.date_origin !== "user" &&
    r.translation === null &&
    (r.fields_origin === "empty" || r.fields_origin === "lectionary") &&'''),
])
print("T1 code written")
PYEOF
```

**Expected:** `T1 code written`.

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/readings.test.ts src/lib/draft/status.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  3 passed (3)`, `Tests  30 passed (30)`; the suite ` Test Files  49 passed (49)`, `      Tests  302 passed (302)`; `> tsc --noEmit` and `> eslint` with nothing after them; `git status` shows ` M` for the five files named in **Files:** (and `?? .claude/` if present).

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/lib/draft/readings.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/readings.test.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/draft/store.test.ts
git commit -m "Draft: a picked date, a chosen reading set or a translation is unsaved work (owner answer Q2; S status.ts)" -m "isPristine is also false for date_origin \"user\" and a translation
override, and chooseReadingSet (the set switcher's transition) makes a
default date the user's, so New service asks first and the mount-time
roll-forward keeps the date. The automatic fill still uses
applyReadingSet, so a fresh draft stays pristine. Frontend 299 -> 302
tests in 49 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 5 files changed; the push prints `<old>..<new>  claude/slice-2-plan-4q33le -> claude/slice-2-plan-4q33le`.

**Review checkpoint (T1):** the reviewer checks that `chooseReadingSet` returns `d` itself when nothing changes and never touches an `archive` date origin, that the fresh and lectionary-filled drafts stay pristine, that `rollForward` is unchanged (it already requires `date_origin === "default"`), and the counts.

### Task 2: The debounced value, and the lectionary and translation queries (S Queries, "Client timeouts", Testing `use-debounced-value`; F §1.8, §4.4; clarifications 1, 17)

`useDebouncedValue` gives the builder a date that trails the draft's by 400 ms, so a date typed segment by segment is looked up once (S). `useLectionary(dateIso)` is `GET /lectionary/readings?date=` through `api.user` (no `X-Church-Id`), keyed `["lectionary", dateIso]`, disabled for a date the lookup refuses, never retried, kept 24 h (5 minutes when `partial`). `useTranslations()` is `GET /translations`, never stale. `timeouts.ts` gains S's two client timeouts. The fixtures gain `translations()`. Nothing uses them on screen yet.

**Files:**
- Create: `frontend/src/lib/use-debounced-value.ts`, `frontend/src/lib/queries/lectionary.ts`, `frontend/src/lib/queries/reference.ts`
- Modify: `frontend/src/lib/api/timeouts.ts`, `frontend/src/test/fixtures/index.ts`
- Test: `frontend/src/lib/use-debounced-value.test.tsx` (new, 3 tests), `frontend/src/lib/queries/lectionary.test.tsx` (new, 3 tests), `frontend/src/lib/queries/reference.test.tsx` (new, 1 test)

**Interfaces:**
- Consumes: `useApi` (`queries/client.ts`), `keys.lectionary`, `keys.translations` (`queries/keys.ts`, slice 1), `isValidDateIso`, `inSupportedRange` (`lib/dates.ts`, 2b), `Lectionary`, `Translations` (`lib/api/types.ts`, 2b), `makeQueryClient`, `installFakeApi`, `fakeError`.
- Produces:
  - `useDebouncedValue<T>(value: T, delayMs: number): T`. Later users: T5 (the date), T9 (the readings list).
  - `canLookUp(dateIso: string): boolean`, `lectionaryStaleTime(data?: Lectionary): number`, `LECTIONARY_STALE_MS`, `PARTIAL_LECTIONARY_STALE_MS`, `useLectionary(dateIso: string): UseQueryResult<Lectionary, ApiError>`. Later users: T5, T7.
  - `useTranslations(): UseQueryResult<Translations, ApiError>`. Later user: T9.
  - `timeoutFor("GET", "/lectionary/readings?…") === 25_000`, `timeoutFor("POST", "/scripture/passages") === 30_000`. Later user: T3.
  - `translations(overrides?)` in `@/test/fixtures` (WEB, KJV, ESV; `esv_available: true`, as production). Later users: T6-T11.

Counts after this task: frontend **309 passed in 52 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/use-debounced-value.ts && test ! -e frontend/src/lib/queries/lectionary.ts && test ! -e frontend/src/lib/queries/reference.ts && echo "no T2 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T2 files yet`; `Test Files  49 passed (49)`, `Tests  302 passed (302)`.

- [ ] **Step 2 (agent): Add the `translations()` fixture**

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


edit("frontend/src/test/fixtures/index.ts", [
    ('import type { ChurchProfile, InviteAccepted, InvitePreview, Lectionary } from "@/lib/api/types";',
     'import type { ChurchProfile, InviteAccepted, InvitePreview, Lectionary, Translations } from "@/lib/api/types";'),
])
print("fixtures import edited")
PYEOF
```

**Expected:** `fixtures import edited`.

Append to `frontend/src/test/fixtures/index.ts`:

```ts

// --- slice 2c: reference data and lookups for the Date & readings step ---------

/** `GET /translations` with ESV configured (production has the key): WEB, KJV and ESV. */
export function translations(overrides: Partial<Translations> = {}): Translations {
  return {
    default: "web",
    esv_available: true,
    items: [
      { id: "web", label: "World English Bible (WEB)" },
      { id: "kjv", label: "King James Version (KJV)" },
      { id: "esv", label: "English Standard Version (ESV)" },
    ],
    ...overrides,
  };
}
```

- [ ] **Step 3 (agent): Write the failing tests**

Create `frontend/src/lib/use-debounced-value.test.tsx`:

```tsx
/** `useDebouncedValue` (S Testing `use-debounced-value.test.ts`), with fake timers. */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDebouncedValue } from "./use-debounced-value";

function renderDebounced(initial: string) {
  const seen: string[] = [];
  const hook = renderHook(
    ({ value }: { value: string }) => {
      const debounced = useDebouncedValue(value, 400);
      seen.push(debounced);
      return debounced;
    },
    { initialProps: { value: initial } },
  );
  return { ...hook, seen };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useDebouncedValue", () => {
  it("starts at the current value with no delay", () => {
    const { result } = renderDebounced("2026-10-04");
    expect(result.current).toBe("2026-10-04");
  });

  it("trails a change by 400 ms", () => {
    const { result, rerender } = renderDebounced("2026-10-04");
    rerender({ value: "2026-10-11" });
    act(() => vi.advanceTimersByTime(399));
    expect(result.current).toBe("2026-10-04");
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("2026-10-11");
  });

  it("lets only the last of several quick changes through", () => {
    const { result, rerender, seen } = renderDebounced("2026-10-04");
    rerender({ value: "0002-10-18" });
    act(() => vi.advanceTimersByTime(200));
    rerender({ value: "0020-10-18" });
    act(() => vi.advanceTimersByTime(200));
    rerender({ value: "2026-10-18" });
    act(() => vi.advanceTimersByTime(399));
    expect(result.current).toBe("2026-10-04");
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("2026-10-18");
    expect(new Set(seen)).toEqual(new Set(["2026-10-04", "2026-10-18"]));
  });
});
```

Create `frontend/src/lib/queries/lectionary.test.tsx`:

```tsx
/** `useLectionary` (S Queries; F §4.4): the key, the client, when it asks, and how long an answer keeps. */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { church, lectionary } from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { keys } from "./keys";
import { LECTIONARY_STALE_MS, PARTIAL_LECTIONARY_STALE_MS, lectionaryStaleTime, useLectionary } from "./lectionary";

/** Inside a church, so the test also shows the lookup never sends X-Church-Id. The app's own retry default. */
function renderLectionary(dateIso: string, queryClient: QueryClient = makeQueryClient()) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return { ...renderHook(() => useLectionary(dateIso), { wrapper: Wrapper }), queryClient };
}

describe("useLectionary", () => {
  it("looks the date up as the user, with no church header, under the lectionary key and a 25 s timeout", async () => {
    const api = installFakeApi({ "GET /lectionary/readings": lectionary("2026-10-04") });
    const { result, queryClient } = renderLectionary("2026-10-04");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path)).toEqual(["/lectionary/readings?date=2026-10-04"]);
    expect(api.requests[0].headers["X-Church-Id"]).toBeUndefined();
    expect(queryClient.getQueryData(keys.lectionary("2026-10-04"))).toEqual(lectionary("2026-10-04"));
    expect(timeoutFor("GET", "/lectionary/readings?date=2026-10-04")).toBe(25_000);
    expect(timeoutFor("POST", "/scripture/passages")).toBe(30_000);
  });

  it("sends nothing for an empty, impossible or out-of-range date", async () => {
    const api = installFakeApi({});
    for (const date of ["", "2026-02-30", "1899-12-31", "2200-01-01"]) {
      const { result, unmount } = renderLectionary(date);
      expect(result.current.fetchStatus).toBe("idle");
      unmount();
    }
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.requests).toEqual([]);
  });

  it("never retries a failure, and keeps a full answer a day but a partial one 5 minutes", async () => {
    const api = installFakeApi({
      "GET /lectionary/readings": fakeError(502, "upstream_error", "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."),
    });
    const { result } = renderLectionary("2026-10-04");
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.code).toBe("upstream_error");
    expect(api.requests).toHaveLength(1);

    expect(lectionaryStaleTime(lectionary("2026-10-04"))).toBe(LECTIONARY_STALE_MS);
    expect(lectionaryStaleTime(lectionary("2026-10-04", { partial: true }))).toBe(PARTIAL_LECTIONARY_STALE_MS);
    expect(lectionaryStaleTime(undefined)).toBe(LECTIONARY_STALE_MS);
    expect([LECTIONARY_STALE_MS, PARTIAL_LECTIONARY_STALE_MS]).toEqual([86_400_000, 300_000]);
  });
});
```

Create `frontend/src/lib/queries/reference.test.tsx`:

```tsx
/** `useTranslations` (S Queries): user-scoped reference data that never goes stale. */
import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ChurchProvider } from "@/lib/church-context";
import { installFakeApi } from "@/test/fake-api";
import { church, translations } from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { useTranslations } from "./reference";

describe("useTranslations", () => {
  it("asks once, as the user, and a second reader uses the cached list", async () => {
    const api = installFakeApi({ "GET /translations": translations() });
    const queryClient = makeQueryClient();
    function Wrapper({ children }: { children: ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          <ChurchProvider value={church()}>{children}</ChurchProvider>
        </QueryClientProvider>
      );
    }
    const first = renderHook(() => useTranslations(), { wrapper: Wrapper });
    await waitFor(() => expect(first.result.current.data).toEqual(translations()));
    const second = renderHook(() => useTranslations(), { wrapper: Wrapper });
    expect(second.result.current.data).toEqual(translations());
    expect(second.result.current.isStale).toBe(false);
    expect(api.requests.map((r) => [r.method, r.path, r.headers["X-Church-Id"]])).toEqual([["GET", "/translations", undefined]]);
  });
});
```

- [ ] **Step 4 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/use-debounced-value.test.tsx src/lib/queries/lectionary.test.tsx src/lib/queries/reference.test.tsx 2>&1 | grep -E "^ FAIL|Error:|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/lib/use-debounced-value.test.tsx [ src/lib/use-debounced-value.test.tsx ]
Error: Failed to resolve import "./use-debounced-value" from "src/lib/use-debounced-value.test.tsx". Does the file exist?
 FAIL  |dom| src/lib/queries/lectionary.test.tsx [ src/lib/queries/lectionary.test.tsx ]
Error: Failed to resolve import "./lectionary" from "src/lib/queries/lectionary.test.tsx". Does the file exist?
 FAIL  |dom| src/lib/queries/reference.test.tsx [ src/lib/queries/reference.test.tsx ]
Error: Failed to resolve import "./reference" from "src/lib/queries/reference.test.tsx". Does the file exist?
      Tests  no tests
```

- [ ] **Step 5 (agent): Write the hook, the two queries and the timeouts**

Create `frontend/src/lib/use-debounced-value.ts`:

```ts
"use client";

/**
 * `value`, trailing its changes by `delayMs` (S "useLectionarySync"): it
 * starts at the current value, with no delay on mount, and only the last of
 * several quick changes comes through. The builder looks up the lectionary
 * for the debounced date, so a date typed segment by segment is looked up
 * (and charged to the rate limit) once.
 */
import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
```

Create `frontend/src/lib/queries/lectionary.ts`:

```ts
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Lectionary } from "@/lib/api/types";
import { inSupportedRange, isValidDateIso } from "@/lib/dates";

import { useApi } from "./client";
import { keys } from "./keys";

/** A complete answer keeps for a day; a partial one (a source failed) is looked up again after 5 minutes. */
export const LECTIONARY_STALE_MS = 24 * 3_600_000;
export const PARTIAL_LECTIONARY_STALE_MS = 5 * 60_000;

export function lectionaryStaleTime(data: Lectionary | undefined): number {
  return data?.partial ? PARTIAL_LECTIONARY_STALE_MS : LECTIONARY_STALE_MS;
}

/** A date the lookup accepts: a real `YYYY-MM-DD` in 1900-2199 (S UX item 1). */
export function canLookUp(dateIso: string): boolean {
  return isValidDateIso(dateIso) && inSupportedRange(dateIso);
}

/**
 * `GET /lectionary/readings?date=` (S Queries; F §4.4): user-scoped, so no
 * `X-Church-Id`; key `["lectionary", dateIso]`; no request for a date the
 * lookup refuses; never retried (a failure shows "Try again", and the server
 * caches a failed source for 5 minutes); a 25 s timeout (`timeouts.ts`).
 */
export function useLectionary(dateIso: string): UseQueryResult<Lectionary, ApiError> {
  const api = useApi();
  return useQuery<Lectionary, ApiError>({
    queryKey: keys.lectionary(dateIso),
    queryFn: ({ signal }) => api.user<Lectionary>(`/lectionary/readings?date=${encodeURIComponent(dateIso)}`, { signal }),
    enabled: canLookUp(dateIso),
    staleTime: (query) => lectionaryStaleTime(query.state.data),
    retry: 0,
  });
}
```

Create `frontend/src/lib/queries/reference.ts`:

```ts
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Translations } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** `GET /translations` (S Queries): user-scoped reference data, key `["ref", "translations"]`, never stale. */
export function useTranslations(): UseQueryResult<Translations, ApiError> {
  const api = useApi();
  return useQuery<Translations, ApiError>({
    queryKey: keys.translations(),
    queryFn: ({ signal }) => api.user<Translations>("/translations", { signal }),
    staleTime: Infinity,
  });
}
```

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


edit("frontend/src/lib/api/timeouts.ts", [
    ('''  "POST /churches": 30_000,
};''', '''  "POST /churches": 30_000,
  // Slice 2 (S "Client timeouts"): the lectionary's two sources answer within its 20 s deadline;
  // passages have a 20 s server deadline per request, and the clock starts when the limiter sends it.
  "GET /lectionary/readings": 25_000,
  "POST /scripture/passages": 30_000,
};'''),
])
print("timeouts edited")
PYEOF
```

**Expected:** `timeouts edited`.

- [ ] **Step 6 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/use-debounced-value.test.tsx src/lib/queries/lectionary.test.tsx src/lib/queries/reference.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  3 passed (3)`, `Tests  7 passed (7)`; the suite ` Test Files  52 passed (52)`, `      Tests  309 passed (309)`; `> tsc --noEmit` and `> eslint` with nothing after them; `git status` shows ` M frontend/src/lib/api/timeouts.ts`, ` M frontend/src/test/fixtures/index.ts` and six `??` files (the three modules and their tests).

- [ ] **Step 7 (agent): Commit and back up**

```bash
git add frontend/src/lib/use-debounced-value.ts frontend/src/lib/use-debounced-value.test.tsx frontend/src/lib/queries/lectionary.ts frontend/src/lib/queries/lectionary.test.tsx frontend/src/lib/queries/reference.ts frontend/src/lib/queries/reference.test.tsx frontend/src/lib/api/timeouts.ts frontend/src/test/fixtures/index.ts
git commit -m "Queries: the lectionary and translations, and a debounced value (F §4.4; S Queries, Client timeouts)" -m "useLectionary looks a date up as the user (no church header) under
[\"lectionary\", date], never for a date outside 1900-2199, never retried,
kept a day (5 minutes when partial), with a 25 s timeout. useTranslations
reads GET /translations once. useDebouncedValue trails a value by a delay
and starts with no delay. Passages get their 30 s timeout. Frontend
302 -> 309 tests in 52 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 8 files changed; the push line.

**Review checkpoint (T2):** the reviewer checks that both queries use `api.user` (no `X-Church-Id`), the lectionary key and `enabled` rule, `retry: 0` for the lectionary only, `staleTime: Infinity` for translations, and that the debounce starts at the current value.

### Task 3: Passage text queries, three at a time (S Queries `usePassage`, `passageLimiter`, Hand-offs row 3 `passageText`, Testing `lib/queries/passages.test.ts`; AC16 limiter half)

`usePassage(ref, translation, enabled)` posts `{refs: [ref], translation}` to `/scripture/passages` through `api.user`, keyed `["passage", translation, ref]`. Every 200 is data, even a `not_found` or `unavailable` passage (the row decides what to show, T9). Requests go through `passageLimiter`, a module-level queue of at most 3 in flight, so "Show all text" on 20 rows never floods the server's shared pool; the 30 s timeout starts when a request leaves the queue, and a request whose signal aborts while it waits (its row closed) never starts. `passageText` is slice 3's reader for the cached `PassageOut`.

**Files:**
- Create: `frontend/src/lib/queries/passages.ts`
- Modify: `frontend/src/lib/api/types.ts` (`Passages`, `Passage`, `PassageSection`)
- Test: `frontend/src/lib/queries/passages.test.ts` (new, 3 tests; `unit` project)

**Interfaces:**
- Consumes: `useApi`, `keys.passage` (slice 1), the generated `PassagesOut`, `PassageOut`, `PassageSectionOut` (2a).
- Produces:
  - `Passages`, `Passage`, `PassageSection` in `lib/api/types.ts`.
  - `createLimiter(max: number): <T>(task: () => Promise<T>, signal?: AbortSignal) => Promise<T>`; `passageLimiter = createLimiter(3)`.
  - `passageText(p: Passage): string | null` (the `ok` sections' text joined with blank lines; S Hand-offs row 3). Later user: slice 3.
  - `passageStaleTime(data?: Passage): number` (0 for `unavailable`, else a day), `PASSAGE_STALE_MS`.
  - `usePassage(ref: string, translation: string, enabled: boolean): UseQueryResult<Passage, ApiError>`. Later user: T9 (`PassageText`).

Counts after this task: frontend **312 passed in 53 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/queries/passages.ts && echo "no T3 files yet"
grep -c "PassagesOut" frontend/src/lib/api/schema.d.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T3 files yet`; a count of at least `2` (2a generated the types); `Test Files  52 passed (52)`, `Tests  309 passed (309)`.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/lib/queries/passages.test.ts`:

```ts
/** The passage limiter and `passageText` (S Testing `lib/queries/passages.test.ts`). */
import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";

import { createLimiter, passageStaleTime, passageText, PASSAGE_STALE_MS } from "./passages";

/** A task the test settles by hand. */
function deferred() {
  let resolve!: (value: string) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<string>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function tick(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

describe("createLimiter", () => {
  it("runs at most 3 tasks; a 4th waits until one settles", async () => {
    const limit = createLimiter(3);
    const tasks = [deferred(), deferred(), deferred(), deferred()];
    const started: number[] = [];
    const results = tasks.map((t, i) =>
      limit(() => {
        started.push(i);
        return t.promise;
      }),
    );
    await tick();
    expect(started).toEqual([0, 1, 2]);
    tasks[1].resolve("second");
    await expect(results[1]).resolves.toBe("second");
    await tick();
    expect(started).toEqual([0, 1, 2, 3]);
    for (const t of [tasks[0], tasks[2], tasks[3]]) t.resolve("done");
    await expect(Promise.all(results)).resolves.toEqual(["done", "second", "done", "done"]);
  });

  it("a rejection frees its slot, and a waiting task whose signal aborts never starts", async () => {
    const limit = createLimiter(1);
    const first = deferred();
    const started: string[] = [];
    const a = limit(() => {
      started.push("a");
      return first.promise;
    });
    const controller = new AbortController();
    const b = limit(async () => {
      started.push("b");
      return "b";
    }, controller.signal);
    const c = limit(async () => {
      started.push("c");
      return "c";
    });
    controller.abort(new Error("collapsed"));
    await expect(b).rejects.toThrow("collapsed");
    first.reject(new Error("network"));
    await expect(a).rejects.toThrow("network");
    await expect(c).resolves.toBe("c");
    expect(started).toEqual(["a", "c"]);
    await expect(limit(async () => "d", controller.signal)).rejects.toThrow("collapsed");
  });
});

describe("passageText and passageStaleTime", () => {
  it("joins only the sections that loaded, is null when none did, and asks again after an unavailable answer", () => {
    const passage: Passage = {
      reference: "Matthew 26:14-27:66 or Matthew 27:11-54",
      status: "unavailable",
      sections: [
        { reference: "Matthew 26:14-27:66", status: "unavailable", text: "Part one." },
        { reference: "Matthew 27:11-54", status: "ok", text: "Jesus stood before the governor." },
        { reference: "Matthew 28:1", status: "ok", text: "After the Sabbath." },
      ],
    };
    expect(passageText(passage)).toBe("Jesus stood before the governor.\n\nAfter the Sabbath.");
    const none: Passage = { reference: "Hezekiah 1:1", status: "not_found", sections: [{ reference: "Hezekiah 1:1", status: "not_found", text: null }] };
    expect(passageText(none)).toBeNull();
    expect(passageStaleTime(passage)).toBe(0);
    expect(passageStaleTime(none)).toBe(PASSAGE_STALE_MS);
    expect(passageStaleTime(undefined)).toBe(PASSAGE_STALE_MS);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/queries/passages.test.ts 2>&1 | grep -E "^ FAIL|Error:|Tests ")
```

**Expected:**

```
 FAIL  |unit| src/lib/queries/passages.test.ts [ src/lib/queries/passages.test.ts ]
Error: Cannot find module './passages' imported from '…/frontend/src/lib/queries/passages.test.ts'
Caused by: Error: Failed to load url ./passages (resolved id: ./passages) in …/frontend/src/lib/queries/passages.test.ts. Does the file exist?
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the types and the passage module**

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


edit("frontend/src/lib/api/types.ts", [
    ('''/** `GET /translations` (slice 2a). */
export type Translations = components["schemas"]["TranslationsOut"];''',
     '''/** `GET /translations` (slice 2a). */
export type Translations = components["schemas"]["TranslationsOut"];
/** `POST /scripture/passages` (slice 2a): one passage per ref sent, each with a section per " or " alternative. */
export type Passages = components["schemas"]["PassagesOut"];
export type Passage = components["schemas"]["PassageOut"];
export type PassageSection = components["schemas"]["PassageSectionOut"];'''),
])
print("types edited")
PYEOF
```

**Expected:** `types edited`.

Create `frontend/src/lib/queries/passages.ts`:

```ts
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Passage, Passages } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** Passage text keeps for a day, except an `unavailable` answer, which is asked again on the next expand or focus. */
export const PASSAGE_STALE_MS = 24 * 3_600_000;

export function passageStaleTime(data: Passage | undefined): number {
  return data?.status === "unavailable" ? 0 : PASSAGE_STALE_MS;
}

/**
 * A promise queue that runs at most `max` tasks at once (S Queries
 * `passageLimiter`). A task starts when a slot frees; one whose `signal`
 * aborts while it waits never starts and rejects with the signal's reason.
 * A settled task, fulfilled or rejected, frees its slot.
 */
export function createLimiter(max: number) {
  let active = 0;
  const waiting: (() => void)[] = [];

  function pump(): void {
    while (active < max && waiting.length > 0) waiting.shift()?.();
  }

  return function limit<T>(task: () => Promise<T>, signal?: AbortSignal): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const abortReason = () => signal?.reason ?? new DOMException("This operation was aborted", "AbortError");
      if (signal?.aborted) {
        reject(abortReason());
        return;
      }
      const start = () => {
        signal?.removeEventListener("abort", onAbort);
        active += 1;
        Promise.resolve()
          .then(task)
          .then(resolve, reject)
          .finally(() => {
            active -= 1;
            pump();
          });
      };
      const onAbort = () => {
        const at = waiting.indexOf(start);
        if (at >= 0) waiting.splice(at, 1);
        reject(abortReason());
      };
      signal?.addEventListener("abort", onAbort, { once: true });
      waiting.push(start);
      pump();
    });
  };
}

/** At most 3 passage requests in flight from this tab, so "Show all text" on 20 rows never floods the server's pool. */
export const passageLimiter = createLimiter(3);

/** The text of the sections that loaded (`ok`), joined with blank lines; null when none did. For slice 3's `nt_text`. */
export function passageText(p: Passage): string | null {
  const texts = p.sections.filter((s) => s.status === "ok" && s.text).map((s) => s.text as string);
  return texts.length > 0 ? texts.join("\n\n") : null;
}

/**
 * `POST /scripture/passages` for one reference (S Queries): key
 * `["passage", translation, ref]`, user-scoped, through `passageLimiter`, so
 * the 30 s timeout starts when the request is sent. Every 200 is data, even
 * a `not_found` or `unavailable` passage; the row shows it (S UX item 6).
 * Real request errors (network, timeout, 5xx, 429, 422) keep the defaults.
 */
export function usePassage(ref: string, translation: string, enabled: boolean): UseQueryResult<Passage, ApiError> {
  const api = useApi();
  return useQuery<Passage, ApiError>({
    queryKey: keys.passage(translation, ref),
    queryFn: ({ signal }) =>
      passageLimiter(async () => {
        const body = await api.user<Passages>("/scripture/passages", {
          method: "POST",
          json: { refs: [ref], translation },
          signal,
        });
        return body.passages[0];
      }, signal),
    enabled,
    staleTime: (query) => passageStaleTime(query.state.data),
  });
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/queries/passages.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  1 passed (1)`, `Tests  3 passed (3)`; the suite ` Test Files  53 passed (53)`, `      Tests  312 passed (312)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M frontend/src/lib/api/types.ts`, `?? frontend/src/lib/queries/passages.test.ts`, `?? frontend/src/lib/queries/passages.ts`.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/queries/passages.ts frontend/src/lib/queries/passages.test.ts
git commit -m "Queries: passage text through a 3-at-a-time limiter, and passageText for slice 3 (S Queries; AC16)" -m "usePassage posts one reference in one translation as the user, under
[\"passage\", translation, ref]; every 200 is data, an unavailable answer
is asked again on the next open or focus, and requests wait in
passageLimiter (3 in flight; a request whose row closed while it waited
never starts). passageText joins the sections that loaded. Frontend
309 -> 312 tests in 53 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 3 files changed; the push line.

**Review checkpoint (T3):** the reviewer checks that a settled task (fulfilled or rejected) frees its slot, that an aborted waiting task is removed from the queue and rejects with the signal's reason, that the request's `signal` reaches `apiFetch` (so its timeout starts when it leaves the queue), and that `passageText` ignores non-`ok` sections.

### Task 4: Base UI radio group, collapsible and tooltip; label options for `ErrorState` and `ConfirmDialog` (F §4.8, §4.9 items 1, 3, 6; S "Frontend changes" Base UI list, UX items 2, 3 and 6; clarifications 4, 5)

The set switcher needs `radio-group`, the reading rows `collapsible`, and the "?" badge `tooltip` (S lists all three as 2c's). The registry is blocked from the container, so after trying `shadcn add` this task writes the three files rebuilt from the upstream source, exactly as 2b did for `sheet` and `badge` (clarification 4). The slice 1 kit's `ErrorState` gains `message`, `retryLabel` and `retryDisabled`, and `ConfirmDialog` gains `cancelLabel`, with their defaults unchanged, for S's "Try again", the lectionary's own sentence and "Keep mine" (clarification 5).

**Files:**
- Create: `frontend/src/components/ui/radio-group.tsx`, `frontend/src/components/ui/collapsible.tsx`, `frontend/src/components/ui/tooltip.tsx` (generated, or clarification 4's files)
- Modify: `frontend/src/components/app/error-state.tsx`, `frontend/src/components/app/confirm-dialog.tsx`
- Test: `frontend/src/components/app/error-state.test.tsx` (+1), `frontend/src/components/app/confirm-dialog.test.tsx` (+1). The three components are exercised by T8 and T9.

**Interfaces:**
- Consumes: `@base-ui/react/radio`, `@base-ui/react/radio-group`, `@base-ui/react/collapsible`, `@base-ui/react/tooltip` (installed with `@base-ui/react` 1.8.0), `cn` from `"cn"` (as the other generated files import it), `PendingButton`, `describeError`.
- Produces:
  - `components/ui/radio-group.tsx`: `RadioGroup` (Base UI `RadioGroup` props: `value`, `onValueChange`, `aria-labelledby`), `RadioGroupItem` (a `Radio.Root` with its indicator). Later user: T8.
  - `components/ui/collapsible.tsx`: `Collapsible` (`open`, `onOpenChange`, `disabled`), `CollapsibleTrigger` (a `<button>`; when disabled it stays focusable and is `aria-disabled`), `CollapsibleContent` (unmounted while closed). Later user: T9.
  - `components/ui/tooltip.tsx`: `TooltipProvider`, `Tooltip`, `TooltipTrigger` (a `<button>`), `TooltipContent`. Later user: T9.
  - `ErrorState` props `message?: string` (instead of `describeError`), `retryLabel?: string` (default "Retry"), `retryDisabled?: boolean`. Later users: T7.
  - `ConfirmDialog` prop `cancelLabel?: string` (default "Cancel"). Later user: T8.

Counts after this task: frontend **314 passed in 53 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/ui/
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `alert-dialog.tsx alert.tsx avatar.tsx badge.tsx button.test.tsx button.tsx card.tsx combobox.tsx dropdown-menu.tsx input-group.tsx input.tsx label.tsx select.tsx sheet.tsx skeleton.tsx sonner.tsx tabs.tsx textarea.tsx` (no `radio-group.tsx`, `collapsible.tsx` or `tooltip.tsx`); `Test Files  53 passed (53)`, `Tests  312 passed (312)`.

- [ ] **Step 2 (agent): Try to generate the three components (network)**

```bash
(cd frontend && timeout 120 npx shadcn@latest add radio-group collapsible tooltip < /dev/null 2>&1 | tail -8)
git status --short
```

`< /dev/null` means no prompt can wait for input. Never pass `--overwrite` (F §4.9 item 1).
- **It works** (the CLI lists the three files as created and `git status` shows exactly those three new files; revert any change to an existing file with `git checkout -- <file>`): skip Step 3 and note "generated" for the commit.
- **Network failure** (expected: this container cannot reach ui.shadcn.com; while planning, `curl https://ui.shadcn.com/r/styles/base-nova/radio-group.json` failed with `CONNECT tunnel failed, response 403`, and 2b's attempt printed `Request to https://ui.shadcn.com/r/styles/base-nova/sheet.json failed, reason: Request was cancelled.` and changed no file): go to Step 3.
- **Anything else** (the registry answers that an item does not exist, or the CLI changes other files): stop and ask the controller.

- [ ] **Step 3 (agent, clarification 4): Write the three components as rebuilt from the upstream shadcn source**

Only after a network failure in Step 2. Provenance: at shadcn-ui/ui commit `db2db460a26fa84fb65c8d903b213925fbdee9ed` (the commit 2b pinned), the plan's writer fetched `apps/v4/registry/bases/base/ui/radio-group.tsx`, `collapsible.tsx` and `tooltip.tsx` and `apps/v4/registry/styles/style-nova.css` from raw.githubusercontent.com, ran each through the installed shadcn CLI's `createStyleMap` and `transformStyle` (`shadcn/utils`, 4.21.0: every `cn-*` class is replaced by its `@apply` classes from `style-nova.css`), and formatted with Prettier 3.9.9 and `prettier-plugin-tailwindcss` 0.8.1 (`semi: false`, `trailingComma: "es5"`, `tailwindFunctions: ["cn", "cva"]`, `tailwindStylesheet: src/app/globals.css`). The same pipeline gives 2b's `badge.tsx` byte for byte after its header comment. None of the three files uses an icon or the heading font, so the CLI's icon and font transforms change nothing. The only change from that output is the header comment.

Optional check that the upstream files are unchanged at that commit (skip it if the host is unreachable; the code below is the record):

```bash
C=db2db460a26fa84fb65c8d903b213925fbdee9ed
for f in apps/v4/registry/bases/base/ui/radio-group.tsx apps/v4/registry/bases/base/ui/collapsible.tsx apps/v4/registry/bases/base/ui/tooltip.tsx apps/v4/registry/styles/style-nova.css; do curl -fsS "https://raw.githubusercontent.com/shadcn-ui/ui/$C/$f" | sha256sum | cut -c1-64; done
```

**Expected:** `c27fecb49f924d324d8c3d1354434508be0b59f202878d9713b8c1af1ebf5afa`, `ead4349ff7b01d696ef89294a81d18ee1d3f732321398896462c834ab9b9e065`, `dc5ec917d8276af9d66e7c951b0608d67c149bcb311072166bc8ce67ee2b7488`, `5d5751579c015b61e77cf0822862a43ac79f3e6fed236a17624be8e6d1ebea1d`.

Create `frontend/src/components/ui/radio-group.tsx`:

```tsx
"use client"

// Rebuilt from the upstream shadcn source (slice 2c plan clarification 4,
// as slice 2b's owner answer A): shadcn-ui/ui@db2db460
// apps/v4/registry/bases/base/ui/radio-group.tsx with
// apps/v4/registry/styles/style-nova.css, through the shadcn 4.21.0 CLI's own
// style transform and Prettier's Tailwind class order. The only change from
// that output is this comment. Replace it with the file
// `npx shadcn@latest add radio-group` generates when the registry is reachable.

import { Radio as RadioPrimitive } from "@base-ui/react/radio"
import { RadioGroup as RadioGroupPrimitive } from "@base-ui/react/radio-group"
import { cn } from "cn"

function RadioGroup({ className, ...props }: RadioGroupPrimitive.Props) {
  return (
    <RadioGroupPrimitive
      data-slot="radio-group"
      className={cn("grid w-full gap-2", className)}
      {...props}
    />
  )
}

function RadioGroupItem({ className, ...props }: RadioPrimitive.Root.Props) {
  return (
    <RadioPrimitive.Root
      data-slot="radio-group-item"
      className={cn(
        "group/radio-group-item peer relative flex aspect-square size-4 shrink-0 rounded-full border border-input outline-none group-has-[:focus-visible]/field-label:ring-0 group-has-[:focus-visible]/field-label:not-data-checked:border-input after:absolute after:-inset-x-3 after:-inset-y-2 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 aria-invalid:aria-checked:border-primary dark:bg-input/30 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 data-checked:border-primary data-checked:bg-primary data-checked:text-primary-foreground group-has-[:focus-visible]/field-label:data-checked:border-primary dark:data-checked:bg-primary",
        className
      )}
      {...props}
    >
      <RadioPrimitive.Indicator
        data-slot="radio-group-indicator"
        className="flex size-4 items-center justify-center"
      >
        <span className="absolute top-1/2 left-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-primary-foreground" />
      </RadioPrimitive.Indicator>
    </RadioPrimitive.Root>
  )
}

export { RadioGroup, RadioGroupItem }
```

Create `frontend/src/components/ui/collapsible.tsx`:

```tsx
"use client"

// Rebuilt from the upstream shadcn source (slice 2c plan clarification 4,
// as slice 2b's owner answer A): shadcn-ui/ui@db2db460
// apps/v4/registry/bases/base/ui/collapsible.tsx with
// apps/v4/registry/styles/style-nova.css, through the shadcn 4.21.0 CLI's own
// style transform and Prettier's Tailwind class order. The only change from
// that output is this comment. Replace it with the file
// `npx shadcn@latest add collapsible` generates when the registry is reachable.

import { Collapsible as CollapsiblePrimitive } from "@base-ui/react/collapsible"

function Collapsible({ ...props }: CollapsiblePrimitive.Root.Props) {
  return <CollapsiblePrimitive.Root data-slot="collapsible" {...props} />
}

function CollapsibleTrigger({ ...props }: CollapsiblePrimitive.Trigger.Props) {
  return (
    <CollapsiblePrimitive.Trigger data-slot="collapsible-trigger" {...props} />
  )
}

function CollapsibleContent({ ...props }: CollapsiblePrimitive.Panel.Props) {
  return (
    <CollapsiblePrimitive.Panel data-slot="collapsible-content" {...props} />
  )
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
```

Create `frontend/src/components/ui/tooltip.tsx`:

```tsx
"use client"

// Rebuilt from the upstream shadcn source (slice 2c plan clarification 4,
// as slice 2b's owner answer A): shadcn-ui/ui@db2db460
// apps/v4/registry/bases/base/ui/tooltip.tsx with
// apps/v4/registry/styles/style-nova.css, through the shadcn 4.21.0 CLI's own
// style transform and Prettier's Tailwind class order. The only change from
// that output is this comment. Replace it with the file
// `npx shadcn@latest add tooltip` generates when the registry is reachable.

import { Tooltip as TooltipPrimitive } from "@base-ui/react/tooltip"
import { cn } from "cn"

function TooltipProvider({
  delay = 0,
  ...props
}: TooltipPrimitive.Provider.Props) {
  return (
    <TooltipPrimitive.Provider
      data-slot="tooltip-provider"
      delay={delay}
      {...props}
    />
  )
}

function Tooltip({ ...props }: TooltipPrimitive.Root.Props) {
  return <TooltipPrimitive.Root data-slot="tooltip" {...props} />
}

function TooltipTrigger({ ...props }: TooltipPrimitive.Trigger.Props) {
  return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />
}

function TooltipContent({
  className,
  side = "top",
  sideOffset = 4,
  align = "center",
  alignOffset = 0,
  children,
  ...props
}: TooltipPrimitive.Popup.Props &
  Pick<
    TooltipPrimitive.Positioner.Props,
    "align" | "alignOffset" | "side" | "sideOffset"
  >) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Positioner
        align={align}
        alignOffset={alignOffset}
        side={side}
        sideOffset={sideOffset}
        className="isolate z-50"
      >
        <TooltipPrimitive.Popup
          data-slot="tooltip-content"
          className={cn(
            "z-50 inline-flex w-fit max-w-xs origin-(--transform-origin) items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-xs text-background has-data-[slot=kbd]:pr-1.5 data-[side=bottom]:slide-in-from-top-2 data-[side=inline-end]:slide-in-from-left-2 data-[side=inline-start]:slide-in-from-right-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 **:data-[slot=kbd]:relative **:data-[slot=kbd]:isolate **:data-[slot=kbd]:z-50 **:data-[slot=kbd]:rounded-sm data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0 data-[state=delayed-open]:zoom-in-95 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
            className
          )}
          {...props}
        >
          {children}
          <TooltipPrimitive.Arrow className="z-50 size-2.5 translate-y-[calc(-50%-2px)] rotate-45 rounded-[2px] bg-foreground fill-foreground data-[side=bottom]:top-1 data-[side=inline-end]:top-1/2! data-[side=inline-end]:-left-1 data-[side=inline-end]:-translate-y-1/2 data-[side=inline-start]:top-1/2! data-[side=inline-start]:-right-1 data-[side=inline-start]:-translate-y-1/2 data-[side=left]:top-1/2! data-[side=left]:-right-1 data-[side=left]:-translate-y-1/2 data-[side=right]:top-1/2! data-[side=right]:-left-1 data-[side=right]:-translate-y-1/2 data-[side=top]:-bottom-2.5" />
        </TooltipPrimitive.Popup>
      </TooltipPrimitive.Positioner>
    </TooltipPrimitive.Portal>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
```

- [ ] **Step 4 (agent): Write the failing kit tests**

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

edit("frontend/src/components/app/error-state.test.tsx", [
    ('''    expect(screen.getByRole("button", { name: "Retry" })).not.toHaveAttribute("aria-busy");
  });
});
''', '''    expect(screen.getByRole("button", { name: "Retry" })).not.toHaveAttribute("aria-busy");
  });

  it("shows a screen's own sentence and button label, and can hold the button disabled without the spinner", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const props = {
      error: new ApiError(502, "upstream_error", "Bad gateway", { requestId: "0123456789abcdef" }),
      onRetry,
      message: "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.",
      retryLabel: "Try again",
    };
    const { rerender } = render(<ErrorState {...props} retryDisabled />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.",
    );
    expect(screen.getByRole("alert")).not.toHaveTextContent("Ref:");
    const button = screen.getByRole("button", { name: "Try again" });
    expect(button).toBeDisabled();
    expect(button).not.toHaveAttribute("aria-busy");
    rerender(<ErrorState {...props} />);
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
'''),
])

edit("frontend/src/components/app/confirm-dialog.test.tsx", [
    ('''    expect(openChanges).toEqual([false]);
    expect(onConfirm).not.toHaveBeenCalled();
  });
});
''', '''    expect(openChanges).toEqual([false]);
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("names the cancel button when the screen's copy asks for it", async () => {
    const user = userEvent.setup();
    const onOpenChange = vi.fn();
    render(
      <ConfirmDialog
        open
        onOpenChange={onOpenChange}
        title="Replace your readings?"
        confirmLabel="Replace readings"
        cancelLabel="Keep mine"
        onConfirm={() => {}}
      />,
    );
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(within(dialog).queryByRole("button", { name: "Cancel" })).toBeNull();
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
'''),
])
print("T4 tests written")
PYEOF
```

**Expected:** `T4 tests written`.

- [ ] **Step 5 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/app/error-state.test.tsx src/components/app/confirm-dialog.test.tsx 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × ErrorState > shows a screen's own sentence and button label, and can hold the button disabled without the spinner <t>ms
   × ConfirmDialog > names the cancel button when the screen's copy asks for it <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
      Tests  2 failed | 6 passed (8)
```

- [ ] **Step 6 (agent): Add the label options**

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

edit("frontend/src/components/app/error-state.tsx", [
    ('''  /** True while the retry runs: Retry is disabled, busy and spinning, so a repeat tap does nothing. */
  retrying?: boolean;
};''', '''  /** True while the retry runs: Retry is disabled, busy and spinning, so a repeat tap does nothing. */
  retrying?: boolean;
  /** A screen's own sentence instead of `describeError`'s (slice 2c: the lectionary's copy). */
  message?: string;
  /** The button's label: "Retry" unless the screen's copy names it ("Try again"). */
  retryLabel?: string;
  /** Disables the button without the spinner, for example while a rate limit's wait runs. */
  retryDisabled?: boolean;
};'''),
    ('''export function ErrorState({ error, onRetry, title, retrying = false }: ErrorStateProps) {
  const message = describeError(error);''', '''export function ErrorState({
  error,
  onRetry,
  title,
  retrying = false,
  message: ownMessage,
  retryLabel = "Retry",
  retryDisabled = false,
}: ErrorStateProps) {
  const message = ownMessage ?? describeError(error);'''),
    ('''        pending={retrying}
        pendingLabel="Retry"
        onClick={() => onRetry()}
      >
        Retry
      </PendingButton>''', '''        pending={retrying}
        pendingLabel={retryLabel}
        disabled={retryDisabled}
        onClick={() => onRetry()}
      >
        {retryLabel}
      </PendingButton>'''),
])

edit("frontend/src/components/app/confirm-dialog.tsx", [
    ('''  /** Names the action ("Delete service"), never "OK" (F §4.8). */
  confirmLabel: string;''', '''  /** Names the action ("Delete service"), never "OK" (F §4.8). */
  confirmLabel: string;
  /** "Cancel" unless the screen's copy says otherwise ("Keep mine"). */
  cancelLabel?: string;'''),
    ('''  confirmLabel,
  onConfirm,''', '''  confirmLabel,
  cancelLabel = "Cancel",
  onConfirm,'''),
    ('''          <AlertDialogCancel>Cancel</AlertDialogCancel>''', '''          <AlertDialogCancel>{cancelLabel}</AlertDialogCancel>'''),
])
print("T4 kit options written")
PYEOF
```

**Expected:** `T4 kit options written`.

- [ ] **Step 7 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/app/error-state.test.tsx src/components/app/confirm-dialog.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  2 passed (2)`, `Tests  8 passed (8)`; the suite ` Test Files  53 passed (53)`, `      Tests  314 passed (314)`; `> tsc --noEmit` and `> eslint` with nothing after them; four ` M` kit files and three `??` ui files.

- [ ] **Step 8 (agent): Commit and back up**

```bash
git add frontend/src/components/ui/radio-group.tsx frontend/src/components/ui/collapsible.tsx frontend/src/components/ui/tooltip.tsx frontend/src/components/app/error-state.tsx frontend/src/components/app/error-state.test.tsx frontend/src/components/app/confirm-dialog.tsx frontend/src/components/app/confirm-dialog.test.tsx
git commit -m "UI: radio group, collapsible and tooltip; label options for ErrorState and ConfirmDialog (F §4.8, §4.9; S Base UI list)" -m "radio-group, collapsible and tooltip are rebuilt from the upstream shadcn
source (base-nova, shadcn-ui/ui@db2db460) through the installed CLI's style
transform and Prettier, because the container cannot reach the registry
(plan clarification 4; as 2b's sheet and badge). ErrorState takes a
screen's own message, button label and a disabled state without the
spinner; ConfirmDialog takes a cancel label. Defaults are unchanged.
Frontend 312 -> 314 tests in 53 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

If Step 2 generated the files, replace the body's first sentence with "radio-group, collapsible and tooltip are generated from the base-nova registry." **Expected:** one commit, 7 files changed; the push line.

**Review checkpoint (T4):** the reviewer checks the three files against the provenance (only the header comment added), that the kit's defaults are unchanged (the existing kit tests pass untouched), and that `retryDisabled` does not set `aria-busy`.

### Task 5: The lectionary lookup and automatic fill on every step, in the visible tab only (S "useLectionarySync", UX item 2 "400 ms", AC14; F §4.6 "Never destroy typed input"; 2b build notes; clarifications 6, 7, 17)

`BuilderShell` renders `<LectionarySync>` inside `DraftProvider`. It debounces the draft's date by 400 ms, runs `useLectionary` for the debounced date, and when an answer for the current date arrives and `shouldAutoApply` says so (empty fields, or lectionary fields from another date), it applies the default set with `update(recipe)`, re-checking against the latest draft inside the recipe. It fills only while the tab is on screen; a hidden tab fills when it is shown (the 2b build note: adopting another tab's newer draft drops up to 400 ms of this tab's typing), after `DraftProvider` has re-read the stored draft on that same `visibilitychange` (`DraftStore.syncFromStorage()`, clarification 7), so a tab shown again never fills over the typing another tab wrote as it was hidden. `useLectionaryLookup()` hands the step the same lookup (T6-T8). The 2b shell and church-switch tests start answering the lookup with "no readings", so their drafts keep their fields.

**Files:**
- Create: `frontend/src/components/builder/lectionary-sync.tsx`
- Modify: `frontend/src/components/builder/builder-shell.tsx`, `frontend/src/test/fixtures/index.ts` (`noReadings`, `lectionaryRoute`), `frontend/src/lib/draft/store.ts` (`syncFromStorage`), `frontend/src/lib/draft/context.tsx` (calls it when the tab is shown)
- Test: `frontend/src/components/builder/lectionary-sync.test.tsx` (new, 6 tests); `frontend/src/components/builder/builder-shell.test.tsx` and `church-switch.test.tsx` (answer the lookup; 0 new); `frontend/src/lib/draft/store.test.ts` (assertions added to the storage-event test; 0 new)

**Interfaces:**
- Consumes: `useDraft`, `DraftStore` (2b), `applyReadingSet`, `shouldAutoApply` (2b), `useLectionary` (T2), `useDebouncedValue` (T2).
- Produces:
  - `DraftStore.syncFromStorage(): void` (re-reads the stored draft and adopts it when strictly newer, like a `storage` event); `DraftProvider` calls it on `visibilitychange` to visible.
  - `LOOKUP_DELAY_MS = 400`; `usePageVisible(): boolean`; `useLectionarySync(): LectionaryLookup`; `<LectionarySync>{children}</LectionarySync>`; `useLectionaryLookup(): LectionaryLookup` (throws outside `<LectionarySync>`), where `LectionaryLookup = { lookupDate: string; settled: boolean; query: UseQueryResult<Lectionary, ApiError> }` (`settled` is false while the draft's date is ahead of `lookupDate`). Later users: T6-T8.
  - `noReadings(date): Lectionary` and `lectionaryRoute(answer = noReadings)` (a fake-API handler answering each `?date=`) in `@/test/fixtures`. Later users: T6-T11.

Counts after this task: frontend **320 passed in 54 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder/lectionary-sync.tsx && echo "no T5 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T5 files yet`; `Test Files  53 passed (53)`, `Tests  314 passed (314)`.

- [ ] **Step 2 (agent): Add the lookup fixtures, and answer the lookup in the 2b builder tests**

Append to `frontend/src/test/fixtures/index.ts`:

```ts

/** `GET /lectionary/readings` for a date with no readings (an ordinary weekday). */
export function noReadings(date: string): Lectionary {
  return lectionary(date, { status: "no_readings", reading_sets: [], default_index: null });
}

/** A fake-API handler for `GET /lectionary/readings` that answers each date with `answer(date)`. */
export function lectionaryRoute(answer: (date: string) => Lectionary = noReadings) {
  return (req: { path: string }) => answer(new URL(req.path, "http://localhost").searchParams.get("date") ?? "");
}
```

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

edit("frontend/src/components/builder/builder-shell.test.tsx", [
    (''' * fresh draft is dated Sunday, October 4, 2026.
 */''', ''' * fresh draft is dated Sunday, October 4, 2026. The lectionary answers "no
 * readings" unless a test says otherwise, so drafts keep their fields
 * (`lectionary-sync.test.tsx` tests the fill).
 */'''),
    ('import { church, churchProfile, DRAFT_NOW, lectionary, me, testDraft, USER_ID } from "@/test/fixtures";',
     'import { church, churchProfile, DRAFT_NOW, lectionary, lectionaryRoute, me, testDraft, USER_ID } from "@/test/fixtures";'),
    ('''function renderBuilder(page: ReactElement, path: string) {
  installFakeApi({ "GET /church": churchProfile() });''', '''function renderBuilder(page: ReactElement, path: string) {
  installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lectionaryRoute() });'''),
    ('''    installFakeApi({ "GET /church": async () => churchProfile() });''',
     '''    installFakeApi({ "GET /church": async () => churchProfile(), "GET /lectionary/readings": lectionaryRoute() });'''),
])
path = "frontend/src/components/builder/builder-shell.test.tsx"
text = Path(path).read_text(encoding="utf-8")
old = '''    installFakeApi({ "GET /church": churchProfile() });'''
assert text.count(old) == 2, text.count(old)
Path(path).write_text(
    text.replace(old, '''    installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lectionaryRoute() });'''),
    encoding="utf-8",
)

edit("frontend/src/components/builder/church-switch.test.tsx", [
    ('import { CHURCH_IDS, church, churchProfile, DRAFT_NOW, me, USER_ID } from "@/test/fixtures";',
     'import { CHURCH_IDS, church, churchProfile, DRAFT_NOW, lectionaryRoute, me, USER_ID } from "@/test/fixtures";'),
    ('''      "GET /church": (req: RecordedRequest) => (req.headers["X-Church-Id"] === HOPE.id ? HOPE : GRACE),
    });''', '''      "GET /church": (req: RecordedRequest) => (req.headers["X-Church-Id"] === HOPE.id ? HOPE : GRACE),
      "GET /lectionary/readings": lectionaryRoute(), // no readings: the drafts keep what the test types
    });'''),
])
print("T5 shell tests edited")
PYEOF
```

**Expected:** `T5 shell tests edited`. Those two files still pass before the shell changes (they now answer a request nobody makes yet); after Step 6 they need the answer, because the fake API fails a test on any unhandled request.

- [ ] **Step 3 (agent): Write the failing tests**

Create `frontend/src/components/builder/lectionary-sync.test.tsx`:

```tsx
/**
 * `useLectionarySync()` in the shell (S "useLectionarySync", Testing
 * `readings-step.test.tsx` fill and debounce cases; AC14). Only `Date` is
 * faked (Tuesday, September 29, 2026), so a fresh draft is dated Sunday,
 * October 4, and the 400 ms debounce runs on real timers.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setDate } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, lectionary, lectionaryRoute, me, testDraft, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { useLectionaryLookup } from "./lectionary-sync";

const KEY = draftKey(USER_ID, church().id);

/** What a step would show: the draft's readings and the lookup's date. */
function Probe() {
  const { draft, update } = useDraft();
  const { lookupDate, settled } = useLectionaryLookup();
  const r = draft.readings;
  return (
    <div>
      <p>Occasion: {r.occasion || "none"}</p>
      <p>Filled for: {r.reading_set?.date_iso ?? "nothing"}</p>
      <p>Lookup: {lookupDate} {settled ? "settled" : "waiting"}</p>
      <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
        October 11
      </button>
      <button type="button" onClick={() => update((d) => setDate(d, "2026-10-18"))}>
        October 18
      </button>
    </div>
  );
}

function renderSync(lookup: FakeHandler, seed?: DraftV1) {
  if (seed) window.localStorage.setItem(KEY, JSON.stringify(seed));
  const api = installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lookup });
  const view = renderWithProviders(
    <BuilderLayout>
      <Probe />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/readings" },
  );
  const lookups = () => api.requests.filter((r) => r.path.startsWith("/lectionary/"));
  return { ...view, api, lookups };
}

/** October 18's own answer, so the test can tell which date filled the fields. */
function byDate(date: string): Lectionary {
  const answer = lectionary(date);
  return date === "2026-10-18"
    ? { ...answer, reading_sets: [{ ...answer.reading_sets[0], name: "Twenty-First Sunday after Pentecost" }] }
    : answer;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("useLectionarySync (S useLectionarySync)", () => {
  it("fills a fresh draft from next Sunday's lectionary, looked up as the user with no church header", async () => {
    const { lookups } = renderSync(lectionaryRoute(byDate));
    expect(await screen.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    expect(screen.getByText("Filled for: 2026-10-04")).toBeInTheDocument();
    expect(lookups().map((r) => r.path)).toEqual(["/lectionary/readings?date=2026-10-04"]);
    expect(lookups()[0].headers["X-Church-Id"]).toBeUndefined();
  });

  it("looks up only the last of two dates set within 400 ms, and refills the older date's lectionary fields", async () => {
    const { user, lookups } = renderSync(lectionaryRoute(byDate));
    await screen.findByText("Filled for: 2026-10-04");
    await user.click(screen.getByRole("button", { name: "October 11" }));
    await user.click(screen.getByRole("button", { name: "October 18" }));
    expect(screen.getByText("Lookup: 2026-10-04 waiting")).toBeInTheDocument();
    expect(await screen.findByText("Occasion: Twenty-First Sunday after Pentecost")).toBeInTheDocument();
    expect(screen.getByText("Filled for: 2026-10-18")).toBeInTheDocument();
    expect(screen.getByText("Lookup: 2026-10-18 settled")).toBeInTheDocument();
    expect(lookups().map((r) => r.path)).toEqual([
      "/lectionary/readings?date=2026-10-04",
      "/lectionary/readings?date=2026-10-18",
    ]);
  });

  it("never replaces typed fields", async () => {
    const { lookups } = renderSync(lectionaryRoute(byDate), testDraft((d) => editOccasion(d, "Harvest Sunday")));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await act(async () => {});
    expect(screen.getByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(screen.getByText("Filled for: nothing")).toBeInTheDocument();
  });

  it("leaves an older date's lectionary fields alone when the lookup fails or finds nothing", async () => {
    // Filled for October 4, then moved to Tuesday, September 29.
    const stale = setDate(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), "2026-09-29");
    for (const answer of [
      fakeError(502, "upstream_error", "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."),
      lectionaryRoute(),
    ]) {
      const { lookups, unmount } = renderSync(answer, stale);
      await waitFor(() => expect(lookups()).toHaveLength(1));
      await act(async () => {});
      expect(screen.getByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
      expect(screen.getByText("Filled for: 2026-10-04")).toBeInTheDocument();
      unmount();
    }
  });

  it("fills only in the visible tab: a hidden tab waits until it is shown", async () => {
    let state: DocumentVisibilityState = "hidden";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => state);
    const { lookups } = renderSync(lectionaryRoute(byDate));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await act(async () => {});
    expect(screen.getByText("Occasion: none")).toBeInTheDocument();

    state = "visible";
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(await screen.findByText("Occasion: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
  });

  it("a tab shown again first takes another tab's newer draft, so its fill never overwrites that tab's typing", async () => {
    let state: DocumentVisibilityState = "hidden";
    vi.spyOn(document, "visibilityState", "get").mockImplementation(() => state);
    const { lookups } = renderSync(lectionaryRoute(byDate));
    await waitFor(() => expect(lookups()).toHaveLength(1));
    await waitFor(() => expect(window.localStorage.getItem(KEY)).not.toBeNull()); // this tab's first write
    expect(screen.getByText("Occasion: none")).toBeInTheDocument();

    // The other tab typed an occasion and wrote it as it was hidden; its storage event comes
    // only after this tab's visibilitychange. This tab's clock is later, so a fill here would win.
    const theirs = JSON.stringify({
      ...editOccasion(testDraft(), "Harvest Sunday"),
      updated_at: new Date(DRAFT_NOW.getTime() + 1_000).toISOString(),
    });
    window.localStorage.setItem(KEY, theirs);
    vi.setSystemTime(DRAFT_NOW.getTime() + 2_000);
    state = "visible";
    act(() => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: theirs }));
    });
    expect(await screen.findByText("Occasion: Harvest Sunday")).toBeInTheDocument();
    expect(screen.getByText("Filled for: nothing")).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(KEY) ?? "{}").readings.occasion).toBe("Harvest Sunday");
  });
});
```

Then run this edit script from the repo root (the store's half of the visible-tab rule, clarification 7):

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


edit("frontend/src/lib/draft/store.test.ts", [
    ('''  it("adopts another tab's strictly newer draft (normalized) and ignores equal, foreign or broken ones", () => {
    const base = testDraft();
    const { storage, writes } = memoryStorage({ [KEY]: JSON.stringify(base) });''',
     '''  it("adopts another tab's strictly newer draft (normalized) and ignores equal, foreign or broken ones", () => {
    const base = testDraft();
    const { storage, writes, data } = memoryStorage({ [KEY]: JSON.stringify(base) });'''),
    ('''    store.handleStorageEvent(KEY, null);
    expect(store.getSnapshot().draft).toBe(mine);
''', '''    store.handleStorageEvent(KEY, null);
    store.syncFromStorage(); // shown again: the stored draft (base) is older than mine
    expect(store.getSnapshot().draft).toBe(mine);
'''),
    ('''    vi.runAllTimers();
    expect(writes).toEqual([]); // my pending write was dropped: theirs is newer
  });''', '''    vi.runAllTimers();
    expect(writes).toEqual([]); // my pending write was dropped: theirs is newer

    // Shown again (slice 2c): the stored draft is read directly, before its storage event arrives.
    const typed = {
      ...editOccasion(theirs, "Typed in the other tab"),
      updated_at: new Date(Date.parse(theirs.updated_at) + 1).toISOString(),
    };
    data.set(KEY, JSON.stringify(typed));
    store.syncFromStorage();
    expect(store.getSnapshot().draft.readings.occasion).toBe("Typed in the other tab");
    store.handleStorageEvent(KEY, JSON.stringify(typed)); // the late event is not newer
    expect(notices).toEqual(["adopted", "adopted"]);
  });'''),
])
print("T5 store test edited")
PYEOF
```

**Expected:** `T5 store test edited`.

- [ ] **Step 4 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/lectionary-sync.test.tsx src/lib/draft/store.test.ts 2>&1 | grep -E "^ FAIL|^ +×|Error:|Tests ")
```

**Expected:**

```
   × DraftStore changes (S store.ts) > adopts another tab's strictly newer draft (normalized) and ignores equal, foreign or broken ones <t>ms
 FAIL  |dom| src/components/builder/lectionary-sync.test.tsx [ src/components/builder/lectionary-sync.test.tsx ]
Error: Failed to resolve import "./lectionary-sync" from "src/components/builder/lectionary-sync.test.tsx". Does the file exist?
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore changes (S store.ts) > adopts another tab's strictly newer draft (normalized) and ignores equal, foreign or broken ones
TypeError: store.syncFromStorage is not a function
      Tests  1 failed | 11 passed (12)
```

- [ ] **Step 5 (agent): Write the sync**

Create `frontend/src/components/builder/lectionary-sync.tsx`:

```tsx
"use client";

/**
 * `useLectionarySync()` (S "useLectionarySync"; F §4.6 "Never destroy typed
 * input"), mounted by `BuilderShell` through `<LectionarySync>`, so it runs on
 * every step. It looks up the draft's date 400 ms after the date last changed
 * (a date typed segment by segment is looked up once) and, when the answer
 * arrives, fills empty fields or an older date's lectionary fields with the
 * default set. The check runs inside the `update` recipe, against the latest
 * draft, so a keystroke in the same tick is never overwritten; typed and
 * archived fields are never touched.
 *
 * Only the visible tab fills (2b build notes): a fill in a hidden tab would
 * write a newer draft, and the visible tab adopting it would drop up to 400 ms
 * of its own unwritten typing. A hidden tab fills when it becomes visible,
 * after `DraftProvider` has re-read the stored draft on that same
 * `visibilitychange` (`syncFromStorage`), so the fill never acts on a stale
 * copy and outranks the other tab's just-written typing.
 *
 * `useLectionaryLookup()` gives the step the same lookup (one query, one
 * debounce) for its status area.
 */
import type { UseQueryResult } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useSyncExternalStore, type ReactNode } from "react";

import type { ApiError } from "@/lib/api/client";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, shouldAutoApply } from "@/lib/draft/readings";
import { useLectionary } from "@/lib/queries/lectionary";
import { useDebouncedValue } from "@/lib/use-debounced-value";

/** How long the date must stay unchanged before it is looked up. */
export const LOOKUP_DELAY_MS = 400;

export type LectionaryLookup = {
  /** The date the query is for: the draft's date, up to 400 ms behind while it changes. */
  lookupDate: string;
  /** False while the draft's date is ahead of `lookupDate`; the step shows Loading meanwhile. */
  settled: boolean;
  query: UseQueryResult<Lectionary, ApiError>;
};

function subscribeVisibility(onChange: () => void): () => void {
  document.addEventListener("visibilitychange", onChange);
  return () => document.removeEventListener("visibilitychange", onChange);
}

/** True while this tab is the one on screen (always true on the server). */
export function usePageVisible(): boolean {
  return useSyncExternalStore(
    subscribeVisibility,
    () => document.visibilityState === "visible",
    () => true,
  );
}

export function useLectionarySync(): LectionaryLookup {
  const { draft, update } = useDraft();
  const dateIso = draft.readings.date_iso;
  const lookupDate = useDebouncedValue(dateIso, LOOKUP_DELAY_MS);
  const query = useLectionary(lookupDate);
  const visible = usePageVisible();
  const data = query.data;
  const due = data !== undefined && shouldAutoApply(draft, data);

  useEffect(() => {
    if (!due || !visible || data === undefined) return;
    update((d) =>
      shouldAutoApply(d, data) && data.default_index !== null ? applyReadingSet(d, data, data.default_index) : d,
    );
  }, [due, visible, data, update]);

  return { lookupDate, settled: lookupDate === dateIso, query };
}

const LectionaryContext = createContext<LectionaryLookup | null>(null);

/** Runs the sync for everything inside it and shares its lookup. Render it inside `DraftProvider`. */
export function LectionarySync({ children }: { children: ReactNode }) {
  const lookup = useLectionarySync();
  return <LectionaryContext value={lookup}>{children}</LectionaryContext>;
}

/** The builder's lookup for the draft's date. Throws outside `<LectionarySync>`. */
export function useLectionaryLookup(): LectionaryLookup {
  const lookup = useContext(LectionaryContext);
  if (!lookup) throw new Error("useLectionaryLookup() must be used inside <LectionarySync>.");
  return lookup;
}
```

Then run this edit script from the repo root. `DraftProvider` already listens for `visibilitychange` (to flush when hidden); when the tab is shown it now calls `syncFromStorage()`, which re-reads the stored draft and adopts it when it is strictly newer. Both listeners run in the same event, before React renders, so the fill's effect sees the adopted draft:

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


edit("frontend/src/lib/draft/store.ts", [
    (''' * - Another tab's write for this key is adopted when its `updated_at` is
 *   strictly newer ("adopted").''', ''' * - Another tab's write for this key is adopted when its `updated_at` is
 *   strictly newer ("adopted"), from its `storage` event or, when this tab is
 *   shown again, from a direct read (`syncFromStorage`, slice 2c).'''),
    (''' * `context.tsx`. This class touches storage only in `start`, `flush` and the
 * constructor's single read, so it can be built during a render.''', ''' * `context.tsx`. This class touches storage only in `start`, `flush`,
 * `syncFromStorage` and the constructor's single read, so it can be built
 * during a render.'''),
    ('''  /** A `storage` event: adopt another tab's strictly newer draft for this key. */
  handleStorageEvent = (key: string | null, newValue: string | null): void => {
    if (key !== this.key || newValue === null) return;
    let stored: DraftV1;
    try {
      stored = parseStoredDraft(newValue, { userId: this.userId, churchId: this.churchId });
    } catch {
      return;
    }
    if (!isNewer(stored.updated_at, this.snapshot.draft.updated_at)) return;
    this.cancelWrite();
    this.set(normalizePicks(stored));
    this.notify("adopted");
  };
''', '''  /** A `storage` event: adopt another tab's strictly newer draft for this key. */
  handleStorageEvent = (key: string | null, newValue: string | null): void => {
    if (key !== this.key) return;
    this.adoptIfNewer(newValue);
  };

  /**
   * The tab is shown again: read the stored draft now and adopt it when it is
   * strictly newer, before anything on screen (the lectionary fill) acts on
   * this tab's copy. The other tab's `storage` event may not have arrived yet,
   * and a fill stamped now would outrank that tab's just-written typing.
   */
  syncFromStorage = (): void => {
    this.adoptIfNewer(this.storage.read(this.key));
  };
'''),
    ('''  private schedule(): void {''', '''  private adoptIfNewer(raw: string | null): void {
    if (raw === null) return;
    let stored: DraftV1;
    try {
      stored = parseStoredDraft(raw, { userId: this.userId, churchId: this.churchId });
    } catch {
      return;
    }
    if (!isNewer(stored.updated_at, this.snapshot.draft.updated_at)) return;
    this.cancelWrite();
    this.set(normalizePicks(stored));
    this.notify("adopted");
  }

  private schedule(): void {'''),
])

edit("frontend/src/lib/draft/context.tsx", [
    (''' * writes (`storage` events), a flush when the page is hidden or left, a flush
 * on unmount (a church switch), and the three toasts.''', ''' * writes (`storage` events, and a direct read when the page is shown again), a
 * flush when the page is hidden or left, a flush on unmount (a church switch),
 * and the three toasts.'''),
    ('''    const onVisibility = () => {
      if (document.visibilityState === "hidden") store.flush();
    };''', '''    // Hidden: write now. Shown: take another tab's newer draft before this tab's
    // lectionary fill can act on a stale copy (its storage event may still be on the way).
    const onVisibility = () => {
      if (document.visibilityState === "hidden") store.flush();
      else store.syncFromStorage();
    };'''),
])
print("T5 store and provider edited")
PYEOF
```

**Expected:** `T5 store and provider edited`.

- [ ] **Step 6 (agent): Mount it in the shell**

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

edit("frontend/src/components/builder/builder-shell.tsx", [
    ('''    <DraftProvider key={`${me.user.id}:${church.id}`} userId={me.user.id} church={profile.data}>
      <BuilderFrame church={profile.data}>{children}</BuilderFrame>
    </DraftProvider>''', '''    <DraftProvider key={`${me.user.id}:${church.id}`} userId={me.user.id} church={profile.data}>
      <LectionarySync>
        <BuilderFrame church={profile.data}>{children}</BuilderFrame>
      </LectionarySync>
    </DraftProvider>'''),
    ('''import { useNewService } from "./new-service-menu-item";''', '''import { LectionarySync } from "./lectionary-sync";
import { useNewService } from "./new-service-menu-item";'''),
    (''' * The church profile is already loaded by the `(church)` layout; until the
 * query has data (tests, a cold cache) a step-shaped skeleton shows.
 */''', ''' * The church profile is already loaded by the `(church)` layout; until the
 * query has data (tests, a cold cache) a step-shaped skeleton shows.
 * `<LectionarySync>` looks up the draft's date and fills the readings on
 * every step (slice 2c).
 */'''),
])
print("T5 shell edited")
PYEOF
```

**Expected:** `T5 shell edited`.

- [ ] **Step 7 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  3 passed (3)`, `Tests  15 passed (15)` (8 shell, 1 church switch, 6 sync); the suite ` Test Files  54 passed (54)`, `      Tests  320 passed (320)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; seven ` M` files (the shell, its test, the church-switch test, the fixtures, `store.ts`, `context.tsx`, `store.test.ts`) and two `??` files.

- [ ] **Step 8 (agent): Commit and back up**

```bash
git add frontend/src/components/builder/lectionary-sync.tsx frontend/src/components/builder/lectionary-sync.test.tsx frontend/src/components/builder/builder-shell.tsx frontend/src/components/builder/builder-shell.test.tsx frontend/src/components/builder/church-switch.test.tsx frontend/src/test/fixtures/index.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/context.tsx frontend/src/lib/draft/store.test.ts
git commit -m "Builder: look up the draft's date and fill the readings on every step, in the visible tab only (S useLectionarySync; AC14)" -m "LectionarySync, inside the shell's DraftProvider, looks the date up 400 ms
after it last changed and fills empty fields, or an older date's
lectionary fields, with the default set; the recipe re-checks against the
latest draft, and typed or archived fields are never touched. A hidden tab
waits until it is shown, so it never writes a draft that would make the
visible tab drop its typing (2b build notes); when it is shown, the draft
store first re-reads the stored draft (syncFromStorage), so it never fills
over another tab's newer typing. The step reads the same lookup through
useLectionaryLookup. Frontend 314 -> 320 tests in 54 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 9 files changed; the push line.

**Review checkpoint (T5):** the reviewer checks that the effect re-checks `shouldAutoApply` inside the recipe, that nothing fills while `document.visibilityState` is not `visible`, that a tab shown again adopts a newer stored draft before it fills (`syncFromStorage`, and the new test's late storage event), that a failure or `no_readings` never changes the fields, and that the lookup sends no `X-Church-Id`.

### Task 6: The Date & readings step: service date, occasion and scripture lines (S UX items 1, 4 and 5; F §4.8 "Mobile", §4.10; clarifications 10-12)

The step component starts here, rendered by the tests inside the real builder layout (the readings route keeps its placeholder until T11). `ServiceDateField` is the "Service date" card: a native date input (any date; `min`/`max` keep the picker in 1900-2199), the long date, "Choose a service date.", "Enter a date between 1900 and 2199.", "This date has passed." (in the church's zone), the "Not a Sunday" line and "Use next Sunday (October 4)", which puts the default date back with `date_origin: "default"` (owner answer Q2). `OccasionField` stores typed text as the user's, shows "Too long (max 300 characters)." past 300 characters, and captions where the text came from. `ScriptureLinesField` keeps the raw lines while typing, shows "Up to 20 readings." and the first too-long line, and drops a stale bulletin pick when it loses focus (`commitScriptureLines`, 2b).

**Files:**
- Create: `frontend/src/components/builder/readings/service-date-field.tsx`, `occasion-field.tsx`, `scripture-lines-field.tsx`, `readings-step.tsx`
- Test: `frontend/src/components/builder/readings/readings-step.test.tsx` (new, 5 tests)

**Interfaces:**
- Consumes: `useDraft`, `setDate`, `editOccasion`, `editScriptureLines`, `commitScriptureLines` (2b); `formatLongDate`, `formatShortDate`, `isSunday`, `isValidDateIso`, `inSupportedRange`, `nextSunday`, `todayIn` (2b); `churchZone` (2b); `useChurch`, `useChurchProfile`; `useLectionaryLookup` (T5); `Input`, `Label`, `Textarea`, `Button`.
- Produces (in `frontend/src/components/builder/readings/`):
  - `ServiceDateField({ today }: { today: string })`.
  - `OCCASION_MAX = 300`, `readingSetName(d, lect?): string | null`, `occasionCaption(d, lect?): string | null`, `OccasionField({ lect, inputRef })`. Later user: T7 ("Enter readings" focuses it through `inputRef`).
  - `MAX_READINGS = 20`, `MAX_LINE = 200`, `scriptureProblems(lines): string[]`, `ScriptureLinesField()`. Later user: T9 (`MAX_LINE`).
  - `ReadingsStep()`: a `<section aria-label="Date & readings">`, extended by T7, T9 and T10 and routed by T11.
  - `readings-step.test.tsx` helpers used by T7-T10: `renderStep({ lookup?, translations?, passages? }, seed?)` (returns the render result plus `api` and `lookups()`), `step()` (queries inside the step, away from the summary), `probe()` (the draft's `date_origin/fields_origin/ot=…/nt=…/t=…`), `KEY`, `ISAIAH`.

Counts after this task: frontend **325 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder/readings && echo "no readings folder yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no readings folder yet`; `Test Files  54 passed (54)`, `Tests  320 passed (320)`.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/components/builder/readings/readings-step.test.tsx`:

```tsx
/**
 * The Date & readings step (S UX "Step 1", Testing `readings-step.test.tsx`;
 * AC14-AC16). The step renders inside the real builder layout against the fake
 * API. Only `Date` is faked (Tuesday, September 29, 2026 at noon in New York),
 * so a fresh draft is dated Sunday, October 4, and the 400 ms lookup delay and
 * the draft's writes run on real timers.
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  lectionary,
  lectionaryRoute,
  me,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { occasionCaption } from "./occasion-field";
import { ReadingsStep } from "./readings-step";
const KEY = draftKey(USER_ID, church().id);
const ISAIAH = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

/** The draft's picks and origins, and the date the lookup has settled on, which the step does not print. */
function DraftProbe() {
  const { draft } = useDraft();
  const { lookupDate } = useLectionaryLookup();
  const r = draft.readings;
  return (
    <>
      <p data-testid="probe">
        {r.date_origin}/{r.fields_origin}/ot={r.selected_ot_ref || "auto"}/nt={r.selected_nt_ref || "auto"}/t=
        {r.translation ?? "church"}
      </p>
      <p data-testid="lookup-date">{lookupDate}</p>
    </>
  );
}

type Routes = { lookup?: FakeHandler; translations?: FakeHandler; passages?: FakeHandler };

function renderStep(
  { lookup = lectionaryRoute(), translations: list = translations(), passages }: Routes = {},
  seed?: DraftV1,
) {
  if (seed) window.localStorage.setItem(KEY, JSON.stringify(seed));
  const handlers: Record<string, FakeHandler> = {
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lookup,
    "GET /translations": list,
  };
  if (passages !== undefined) handlers["POST /scripture/passages"] = passages;
  const api = installFakeApi(handlers);
  const view = renderWithProviders(
    <BuilderLayout>
      <ReadingsStep />
      <DraftProbe />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/readings" },
  );
  const lookups = () => api.requests.filter((r) => r.path.startsWith("/lectionary/")).map((r) => r.path);
  return { ...view, api, lookups };
}

/** Queries inside the step, away from the summary (which also shows the date and readings). */
function step() {
  return within(screen.getByRole("region", { name: "Date & readings" }));
}

function probe(): string {
  return screen.getByTestId("probe").textContent ?? "";
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("service date (S UX item 1)", () => {
  it("shows next Sunday; a weekday says it looks for that day's readings; Use next Sunday puts the default back", async () => {
    const { lookups } = renderStep();
    const input = await screen.findByLabelText("Service date");
    expect(input).toHaveValue("2026-10-04");
    expect(step().getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    expect(screen.getByText("Readings and the occasion load automatically for this date.")).toBeInTheDocument();
    expect(screen.queryByText(/^Not a Sunday\./)).toBeNull();
    expect(screen.queryByRole("button", { name: /^Use next Sunday/ })).toBeNull();

    fireEvent.change(input, { target: { value: "2026-09-27" } });
    expect(step().getByText("Sunday, September 27, 2026")).toBeInTheDocument();
    expect(screen.getByText("This date has passed.")).toBeInTheDocument();
    expect(probe()).toMatch(/^user\//);

    fireEvent.change(input, { target: { value: "2026-09-29" } });
    expect(step().getByText("Tuesday, September 29, 2026")).toBeInTheDocument();
    expect(screen.queryByText("This date has passed.")).toBeNull(); // today is not past
    expect(
      screen.getByText(
        "Not a Sunday. We'll look for this day's own readings, such as Ash Wednesday, Christmas Eve or Good Friday.",
      ),
    ).toBeInTheDocument();

    screen.getByRole("button", { name: "Use next Sunday (October 4)" }).click();
    await waitFor(() => expect(input).toHaveValue("2026-10-04"));
    expect(probe()).toMatch(/^default\//);
    await waitFor(() => expect(lookups()).toContain("/lectionary/readings?date=2026-10-04"));
  });

  it("asks for a date when it is empty, and looks nothing up for it or for a year outside 1900-2199", async () => {
    const { lookups } = renderStep();
    const input = await screen.findByLabelText("Service date");
    await waitFor(() => expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-04"]));

    fireEvent.change(input, { target: { value: "" } });
    expect(screen.getByText("Choose a service date.")).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("button", { name: "Use next Sunday (October 4)" })).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "1850-06-02" } });
    expect(screen.getByText("Enter a date between 1900 and 2199.")).toBeInTheDocument();
    expect(step().getByText("Sunday, June 2, 1850")).toBeInTheDocument();
    // The lookup settles on 1850 and sends nothing; the next date's lookup is the next request.
    await waitFor(() => expect(screen.getByTestId("lookup-date")).toHaveTextContent("1850-06-02"));
    fireEvent.change(input, { target: { value: "2026-10-11" } });
    await waitFor(() =>
      expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-04", "/lectionary/readings?date=2026-10-11"]),
    );
  });
});

describe("occasion and scripture lines (S UX items 4 and 5)", () => {
  it("captions the occasion by where it came from", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(lectionary) });
    const occasion = await screen.findByLabelText("Occasion");
    await waitFor(() => expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost"));
    expect(screen.getByText("From the Revised Common Lectionary: Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    expect(screen.getByLabelText("Scripture readings")).toHaveValue(ISAIAH.join("\n"));

    await user.type(occasion, " (Harvest)");
    expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost (Harvest)");
    expect(screen.getByText("Edited from the lectionary (Nineteenth Sunday after Pentecost)")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    expect(screen.getByText("Entered by you")).toBeInTheDocument();

    // After a refetch that lists the sets in another order, the caption follows the lines, not the stored index.
    const october4 = lectionary("2026-10-04");
    const reordered = { ...october4, reading_sets: [...october4.reading_sets].reverse() };
    const edited = editOccasion(applyReadingSet(testDraft(), october4, 0), "Harvest");
    expect(occasionCaption(edited, reordered)).toBe("Edited from the lectionary (Nineteenth Sunday after Pentecost)");
    expect(occasionCaption(applyReadingSet(testDraft(), october4, 1), reordered)).toBe(
      "From the Revised Common Lectionary: Resurrection of the Lord",
    );
  });

  it("says where archived fields came from, and shows no caption for empty ones", async () => {
    const archived = testDraft((d) => ({
      ...d,
      readings: { ...d.readings, fields_origin: "archive", occasion: "Harvest", scriptures: ["Joel 2:21-27"] },
    }));
    const { unmount } = renderStep({}, archived);
    expect(await screen.findByText("From the saved service")).toBeInTheDocument();
    unmount();
    window.localStorage.clear();
    renderStep();
    await screen.findByLabelText("Occasion");
    expect(screen.queryByText(/^From the|^Entered by you|^Edited from/)).toBeNull();
  });

  it("marks typed fields as the user's, shows the limits, and drops a stale pick only when the lines lose focus", async () => {
    const filled = setPick(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), "ot", "Isaiah 5:1-7");
    const { user } = renderStep({}, filled);
    const occasion = await screen.findByLabelText("Occasion");
    fireEvent.change(occasion, { target: { value: "x".repeat(301) } });
    expect(screen.getByText("Too long (max 300 characters).")).toBeInTheDocument();
    expect(occasion).toHaveAttribute("aria-invalid", "true");
    fireEvent.change(occasion, { target: { value: "Harvest Sunday" } });
    expect(screen.queryByText("Too long (max 300 characters).")).toBeNull();

    const lines = screen.getByLabelText("Scripture readings");
    fireEvent.change(lines, { target: { value: `Isaiah 5:1-7\n${"y".repeat(201)}` } });
    expect(screen.getByText("Line 2 is too long (max 200 characters).")).toBeInTheDocument();
    fireEvent.change(lines, { target: { value: Array.from({ length: 21 }, (_, i) => `Psalm ${i + 1}`).join("\n\n") } });
    expect(screen.getByText("Up to 20 readings.")).toBeInTheDocument();

    // Typing keeps the pick (retyping the line restores it); leaving the field drops it when it is no longer a line.
    await user.clear(lines);
    await user.type(lines, "Psalm 80:7-15");
    expect(probe()).toContain("/user/ot=Isaiah 5:1-7/");
    await user.click(occasion);
    expect(probe()).toContain("/user/ot=auto/");
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "^ FAIL|Error:|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/components/builder/readings/readings-step.test.tsx [ src/components/builder/readings/readings-step.test.tsx ]
Error: Failed to resolve import "./occasion-field" from "src/components/builder/readings/readings-step.test.tsx". Does the file exist?
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the three fields and the step**

Create `frontend/src/components/builder/readings/service-date-field.tsx`:

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  formatLongDate,
  formatShortDate,
  inSupportedRange,
  isSunday,
  isValidDateIso,
  nextSunday,
} from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { setDate } from "@/lib/draft/readings";

/**
 * The "Service date" card (S UX item 1). Every date is allowed; an empty or
 * impossible one is stored as "" and asks for a date, and a year outside
 * 1900-2199 is not looked up. "Use next Sunday" puts back the default date
 * (origin `default`, so it is not counted as the user's choice). `today` is
 * the church's calendar day.
 */
export function ServiceDateField({ today }: { today: string }) {
  const { draft, update } = useDraft();
  const iso = draft.readings.date_iso;
  const next = nextSunday(today);
  const valid = isValidDateIso(iso);
  const inRange = valid && inSupportedRange(iso);
  const problem = !valid ? "Choose a service date." : !inRange ? "Enter a date between 1900 and 2199." : null;

  return (
    <div className="grid gap-2 rounded-lg border p-4">
      <Label htmlFor="service-date">Service date</Label>
      <p id="service-date-help" className="text-sm text-muted-foreground">
        Readings and the occasion load automatically for this date.
      </p>
      <Input
        id="service-date"
        type="date"
        value={iso}
        min="1900-01-01"
        max="2199-12-31"
        aria-describedby={problem ? "service-date-help service-date-problem" : "service-date-help"}
        aria-invalid={problem ? true : undefined}
        onChange={(event) => {
          const value = event.target.value;
          update((d) => setDate(d, value));
        }}
        className="h-11 w-full sm:w-56"
      />
      {valid ? <p className="font-medium">{formatLongDate(iso)}</p> : null}
      {problem ? (
        <p id="service-date-problem" className="text-sm text-destructive">
          {problem}
        </p>
      ) : null}
      {inRange && iso < today ? <p className="text-sm text-muted-foreground">This date has passed.</p> : null}
      {inRange && !isSunday(iso) ? (
        <p className="text-sm">
          Not a Sunday. We&apos;ll look for this day&apos;s own readings, such as Ash Wednesday, Christmas Eve or Good
          Friday.
        </p>
      ) : null}
      {iso !== next ? (
        <div>
          <Button
            type="button"
            variant="link"
            className="h-11 px-0"
            onClick={() => update((d) => setDate(d, next, "default"))}
          >
            Use next Sunday ({formatShortDate(next)})
          </Button>
        </div>
      ) : null}
    </div>
  );
}
```

Create `frontend/src/components/builder/readings/occasion-field.tsx`:

```tsx
"use client";

import type { Ref } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { editOccasion, selectedSetIndex } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";

export const OCCASION_MAX = 300;

/**
 * The name of this date's set the draft shows (`selectedSetIndex`: the set
 * equal to its lines, else the stored index), when that date's lookup is
 * loaded. Found by the lines first, so a refetch that lists the sets in
 * another order never names the wrong one.
 */
export function readingSetName(d: DraftV1, lect: Lectionary | undefined): string | null {
  if (!lect) return null;
  const index = selectedSetIndex(d, lect);
  return index === null ? null : (lect.reading_sets[index]?.name ?? null);
}

/** The caption under Occasion (S UX item 4 table). */
export function occasionCaption(d: DraftV1, lect: Lectionary | undefined): string | null {
  const r = d.readings;
  switch (r.fields_origin) {
    case "lectionary":
      // Lectionary fields hold the set's own name as the occasion.
      return `From the Revised Common Lectionary: ${r.occasion}`;
    case "user": {
      if (r.reading_set?.date_iso !== r.date_iso) return "Entered by you";
      const name = readingSetName(d, lect);
      return name ? `Edited from the lectionary (${name})` : "Edited from the lectionary";
    }
    case "archive":
      return "From the saved service";
    default:
      return null;
  }
}

/** Occasion (S UX item 4): printed as the bulletin's title; 300 characters at most. */
export function OccasionField({ lect, inputRef }: { lect: Lectionary | undefined; inputRef?: Ref<HTMLInputElement> }) {
  const { draft, update } = useDraft();
  const value = draft.readings.occasion;
  const tooLong = value.length > OCCASION_MAX;
  const caption = occasionCaption(draft, lect);
  const describedBy = ["occasion-help", caption ? "occasion-caption" : null, tooLong ? "occasion-error" : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="grid gap-2">
      <Label htmlFor="occasion">Occasion</Label>
      <p id="occasion-help" className="text-sm text-muted-foreground">
        Printed as the bulletin&apos;s title. Filled from the lectionary; edit if needed.
      </p>
      <Input
        id="occasion"
        ref={inputRef}
        value={value}
        placeholder="e.g. Third Sunday of Easter"
        aria-describedby={describedBy}
        aria-invalid={tooLong ? true : undefined}
        onChange={(event) => {
          const next = event.target.value;
          update((d) => editOccasion(d, next));
        }}
        className="h-11"
      />
      {tooLong ? (
        <p id="occasion-error" className="text-sm text-destructive">
          Too long (max 300 characters).
        </p>
      ) : null}
      {caption ? (
        <p id="occasion-caption" className="text-xs text-muted-foreground">
          {caption}
        </p>
      ) : null}
    </div>
  );
}
```

Create `frontend/src/components/builder/readings/scripture-lines-field.tsx`:

```tsx
"use client";

import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useDraft } from "@/lib/draft/context";
import { commitScriptureLines, editScriptureLines } from "@/lib/draft/readings";

export const MAX_READINGS = 20;
export const MAX_LINE = 200;

/** The inline messages for the raw lines (S UX item 5); blank lines are allowed and not counted. */
export function scriptureProblems(lines: readonly string[]): string[] {
  const problems: string[] = [];
  if (lines.filter((line) => line.trim() !== "").length > MAX_READINGS) problems.push("Up to 20 readings.");
  const long = lines.findIndex((line) => line.length > MAX_LINE);
  if (long >= 0) problems.push(`Line ${long + 1} is too long (max 200 characters).`);
  return problems;
}

/**
 * Scripture readings (S UX item 5): one reference per line, raw lines kept
 * while typing. Leaving the field drops a bulletin pick that is no longer a
 * line (`commitScriptureLines`).
 */
export function ScriptureLinesField() {
  const { draft, update } = useDraft();
  const problems = scriptureProblems(draft.readings.scriptures);

  return (
    <div className="grid gap-2">
      <Label htmlFor="scriptures">Scripture readings</Label>
      <p id="scriptures-help" className="text-sm text-muted-foreground">
        One reference per line, for example Matthew 17:1-9. Filled from the lectionary; edit if needed.
      </p>
      <Textarea
        id="scriptures"
        rows={5}
        value={draft.readings.scriptures.join("\n")}
        placeholder="Matthew 17:1-9"
        aria-describedby={problems.length > 0 ? "scriptures-help scriptures-error" : "scriptures-help"}
        aria-invalid={problems.length > 0 ? true : undefined}
        onChange={(event) => {
          const raw = event.target.value;
          update((d) => editScriptureLines(d, raw));
        }}
        onBlur={() => update(commitScriptureLines)}
        className="min-h-32"
      />
      {problems.length > 0 ? (
        <div id="scriptures-error" className="grid gap-1 text-sm text-destructive">
          {problems.map((problem) => (
            <p key={problem}>{problem}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
```

Create `frontend/src/components/builder/readings/readings-step.tsx`:

```tsx
"use client";

import { useRef } from "react";

import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useChurch } from "@/lib/church-context";
import { todayIn } from "@/lib/dates";
import { churchZone } from "@/lib/draft/schema";
import { useChurchProfile } from "@/lib/queries/church";

import { OccasionField } from "./occasion-field";
import { ScriptureLinesField } from "./scripture-lines-field";
import { ServiceDateField } from "./service-date-field";

/**
 * Step 1, Date & readings (S UX "Step 1"): the service date, the lectionary
 * status, the occasion and scripture lines, the readings with their text, and
 * the bulletin's two readings. The shell's `<LectionarySync>` does the lookup
 * and the automatic fill; this step shows them.
 */
export function ReadingsStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { lookupDate, query } = useLectionaryLookup();
  const occasionRef = useRef<HTMLInputElement>(null);
  if (!profile) return null;
  const today = todayIn(churchZone(profile));
  const lect = query.data?.date === lookupDate ? query.data : undefined;

  return (
    <section aria-label="Date & readings" className="grid gap-6">
      <ServiceDateField today={today} />
      <OccasionField lect={lect} inputRef={occasionRef} />
      <ScriptureLinesField />
    </section>
  );
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  1 passed (1)`, `Tests  5 passed (5)`; the suite ` Test Files  55 passed (55)`, `      Tests  325 passed (325)`; `> tsc --noEmit` and `> eslint` with nothing after them; `?? frontend/src/components/builder/readings/`.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/components/builder/readings/service-date-field.tsx frontend/src/components/builder/readings/occasion-field.tsx frontend/src/components/builder/readings/scripture-lines-field.tsx frontend/src/components/builder/readings/readings-step.tsx frontend/src/components/builder/readings/readings-step.test.tsx
git commit -m "Readings step: the service date, the occasion and the scripture lines (S UX items 1, 4, 5)" -m "The Service date card takes any date, shows the long date, asks for one
when it is empty, refuses years outside 1900-2199 (no lookup), notes a
passed date and a weekday, and offers Use next Sunday, which puts the
default date back. Occasion and Scripture readings store typed text as
the user's, with their limits and the origin caption; leaving the lines
drops a bulletin pick that is no longer a line. Frontend 320 -> 325 tests
in 55 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 5 files changed; the push line.

**Review checkpoint (T6):** the reviewer checks the copy against "Messages", that "today" is the church's day (`todayIn(churchZone(profile))`), that nothing calls `new Date(` on a date-only value, that "Use next Sunday" stores `date_origin: "default"`, and that picks change only on blur.

### Task 7: The lectionary status: loading, no readings, unavailable, rate limited, partial and stale fields (S UX item 2; F §4.8; AC14 "never changes the fields", "never moves focus"; clarifications 5, 8, 9)

Directly under the date, exactly one of these shows: Loading (also while the date settles, with "Still working — this can take up to a minute." after 8 s), No readings (with "Enter readings", which moves focus to Occasion; focus never moves on its own), Unavailable (the lectionary's own sentence and "Try again"), or Rate limited ("Too many requests — try again in N s.", "Try again" disabled until N seconds pass); an answer with sets shows the partial note when a source failed (T8 adds the set switcher and the banner). Lectionary fields from another date stay, with "These readings are from … not …" and "Clear readings", next to No readings, Unavailable or Rate limited, and alone for a date the lookup refuses (the date field explains the date; with no valid date the sentence ends after the set). No readings is a `role="status"` callout, not an alert (clarification 21).

**Files:**
- Create: `frontend/src/components/builder/readings/lectionary-status.tsx`, `frontend/src/components/builder/readings/use-wait-over.ts`
- Modify: `frontend/src/components/builder/readings/readings-step.tsx` (renders `LectionaryStatus`)
- Test: `frontend/src/components/builder/readings/readings-step.test.tsx` (+5)

**Interfaces:**
- Consumes: `useLectionaryLookup` (T5), `canLookUp` (T2), `ErrorState` with `message`/`retryLabel`/`retryDisabled` (T4), `clearReadings`, `readingsStale` (2b), `Alert`, `Skeleton`, `Button`, `ApiError.retryAfterSeconds` (slice 1).
- Produces:
  - `use-wait-over.ts`: `retryAfter(error): number` (at least 1), `rateLimitMessage(error): string`, `useWaitOver(error: ApiError | null): boolean`. Later user: T9 (`PassageText`).
  - `lectionary-status.tsx`: `LECTIONARY_UNAVAILABLE`, `STILL_WORKING_MS = 8_000`, `LectionaryStatus({ onEnterReadings })`. T8 replaces the file with the set switcher and the banner added.

Counts after this task: frontend **330 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder/readings/lectionary-status.tsx && echo "no T7 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T7 files yet`; `Test Files  55 passed (55)`, `Tests  325 passed (325)`.

- [ ] **Step 2 (agent): Write the failing tests**

In `frontend/src/components/builder/readings/readings-step.test.tsx`, replace the import block (from the first line through `import { ReadingsStep } from "./readings-step";`) with:

```tsx
/**
 * The Date & readings step (S UX "Step 1", Testing `readings-step.test.tsx`;
 * AC14-AC16). The step renders inside the real builder layout against the fake
 * API. Only `Date` is faked (Tuesday, September 29, 2026 at noon in New York),
 * so a fresh draft is dated Sunday, October 4, and the 400 ms lookup delay and
 * the draft's writes run on real timers.
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setDate, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  lectionary,
  lectionaryRoute,
  me,
  noReadings,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { occasionCaption } from "./occasion-field";
import { ReadingsStep } from "./readings-step";
```

Append to `frontend/src/components/builder/readings/readings-step.test.tsx`:

```tsx

// --- lectionary status (S UX item 2; AC14) ---------------------------------------

const UNAVAILABLE = "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.";

/** Filled from October 4's lectionary, then moved to Tuesday, September 29. */
function staleDraft(): DraftV1 {
  return setDate(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), "2026-09-29");
}

/** A handler that gives each answer in turn, then repeats the last. */
function inTurn(...answers: FakeHandler[]): FakeHandler {
  let n = 0;
  return (req: RecordedRequest) => {
    const answer = answers[Math.min(n, answers.length - 1)];
    n += 1;
    return typeof answer === "function" ? (answer as (r: RecordedRequest) => unknown)(req) : answer;
  };
}

describe("lectionary status (S UX item 2)", () => {
  it("no readings: names the day, never moves focus, and Enter readings focuses Occasion", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(noReadings) });
    const date = await screen.findByLabelText("Service date");
    date.focus();
    fireEvent.change(date, { target: { value: "2026-09-29" } });
    const none = await screen.findByText("No lectionary readings for Tuesday, September 29, 2026.");
    expect(none.closest("[role=status]")).not.toBeNull(); // information, not an alert
    expect(screen.queryByRole("alert")).toBeNull();
    expect(screen.getByText("Enter the occasion and readings below.")).toBeInTheDocument();
    expect(date).toHaveFocus();
    await user.click(screen.getByRole("button", { name: "Enter readings" }));
    expect(screen.getByLabelText("Occasion")).toHaveFocus();
  });

  it("unavailable: the lectionary's own copy, the stale note, and Try again refetches", async () => {
    const { user, lookups } = renderStep(
      {
        lookup: inTurn(
          fakeError(502, "upstream_error", UNAVAILABLE),
          lectionaryRoute((date) => lectionary(date, { partial: true })),
        ),
      },
      staleDraft(),
    );
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(UNAVAILABLE);
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not September 29, 2026."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Occasion")).toHaveValue("Nineteenth Sunday after Pentecost"); // untouched

    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByText("One lectionary source didn't respond, so other reading options for this date may be missing."),
    ).toBeInTheDocument();
    expect(lookups()).toEqual(["/lectionary/readings?date=2026-09-29", "/lectionary/readings?date=2026-09-29"]);
    await waitFor(() => expect(screen.getByLabelText("Occasion")).toHaveValue("Nineteenth Sunday after Pentecost"));
    expect(screen.queryByText(/^These readings are from/)).toBeNull(); // refilled for September 29
  });

  it("rate limited: Try again waits for Retry-After, and typing still works meanwhile", async () => {
    const limited = fakeError(429, "rate_limited", "Too many requests. Try again in 1 seconds.", {
      details: { retry_after_seconds: 1 },
    });
    const { user, lookups } = renderStep(
      {
        lookup: inTurn({ ...limited, headers: { ...limited.headers, "Retry-After": "1" } }, lectionaryRoute(lectionary)),
      },
      staleDraft(),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Too many requests — try again in 1 s.");
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not September 29, 2026."),
    ).toBeInTheDocument(); // the stale note shows while rate limited too
    const retry = screen.getByRole("button", { name: "Try again" });
    expect(retry).toBeDisabled();
    await user.clear(screen.getByLabelText("Occasion"));
    await user.type(screen.getByLabelText("Occasion"), "Harvest");
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
    await waitFor(() => expect(retry).toBeEnabled(), { timeout: 3_000 });
    await user.click(retry);
    await waitFor(() => expect(lookups()).toHaveLength(2));
    await waitFor(() => expect(screen.queryByText(/^Too many requests/)).toBeNull());
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest"); // typed fields are never replaced
  });

  it("stale fields stay until Clear readings empties them", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(noReadings) }, staleDraft());
    const note = await screen.findByText(
      "These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not September 29, 2026.",
    );
    expect(screen.getByLabelText("Scripture readings")).toHaveValue(ISAIAH.join("\n"));
    // The note stays without a date, or with one the lookup refuses.
    const date = screen.getByLabelText("Service date");
    fireEvent.change(date, { target: { value: "" } });
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026)."),
    ).toBeInTheDocument();
    fireEvent.change(date, { target: { value: "1850-06-02" } });
    expect(
      screen.getByText("These readings are from Nineteenth Sunday after Pentecost (October 4, 2026), not June 2, 1850."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear readings" }));
    expect(screen.queryByText(/^These readings are from/)).toBeNull();
    expect(note).not.toBeInTheDocument();
    expect(screen.getByLabelText("Occasion")).toHaveValue("");
    expect(screen.getByLabelText("Scripture readings")).toHaveValue("");
    expect(probe()).toContain("/empty/");
  });

  it("shows Loading while the date settles and the lookup runs, and Still working after 8 s", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    renderStep({ lookup: () => new Promise(() => {}) });
    expect(await screen.findByText("Looking up the lectionary…")).toBeInTheDocument();
    expect(screen.queryByText("Still working — this can take up to a minute.")).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(screen.getByText("Still working — this can take up to a minute.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × lectionary status (S UX item 2) > no readings: names the day, never moves focus, and Enter readings focuses Occasion <t>ms
   × lectionary status (S UX item 2) > unavailable: the lectionary's own copy, the stale note, and Try again refetches <t>ms
   × lectionary status (S UX item 2) > rate limited: Try again waits for Retry-After, and typing still works meanwhile <t>ms
   × lectionary status (S UX item 2) > stale fields stay until Clear readings empties them <t>ms
   × lectionary status (S UX item 2) > shows Loading while the date settles and the lookup runs, and Still working after 8 s <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯
      Tests  5 failed | 5 passed (10)
```

- [ ] **Step 4 (agent): Write the status and the rate-limit wait, and show the status**

Create `frontend/src/components/builder/readings/use-wait-over.ts`:

```ts
"use client";

import { useEffect, useState } from "react";

import type { ApiError } from "@/lib/api/client";

/** The seconds a 429 asks to wait (its `Retry-After`), at least 1. */
export function retryAfter(error: ApiError): number {
  return Math.max(1, error.retryAfterSeconds ?? 1);
}

/** The F §4.8 rate-limit sentence the step shows. */
export function rateLimitMessage(error: ApiError): string {
  return `Too many requests — try again in ${retryAfter(error)} s.`;
}

/** True once `error`'s `Retry-After` has passed; each new error starts its own wait. */
export function useWaitOver(error: ApiError | null): boolean {
  const [overFor, setOverFor] = useState<ApiError | null>(null);
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setOverFor(error), retryAfter(error) * 1000);
    return () => clearTimeout(timer);
  }, [error]);
  return error !== null && overFor === error;
}
```

Create `frontend/src/components/builder/readings/lectionary-status.tsx`:

```tsx
"use client";

import { InfoIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/app/error-state";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError } from "@/lib/api/client";
import { formatLongDate, formatServiceDate, isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { clearReadings, readingsStale } from "@/lib/draft/readings";
import { canLookUp } from "@/lib/queries/lectionary";

import { rateLimitMessage, useWaitOver } from "./use-wait-over";

export const LECTIONARY_UNAVAILABLE =
  "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.";
/** After this long, Loading adds "Still working — this can take up to a minute." */
export const STILL_WORKING_MS = 8_000;

function Loading({ lookupDate }: { lookupDate: string }) {
  const [slowFor, setSlowFor] = useState<string | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setSlowFor(lookupDate), STILL_WORKING_MS);
    return () => clearTimeout(timer);
  }, [lookupDate]);
  return (
    <div role="status" className="grid gap-2">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <p className="text-sm text-muted-foreground">Looking up the lectionary…</p>
      {slowFor === lookupDate ? (
        <p className="text-sm text-muted-foreground">Still working — this can take up to a minute.</p>
      ) : null}
    </div>
  );
}

function RateLimited({ error, onRetry, retrying }: { error: ApiError; onRetry: () => void; retrying: boolean }) {
  const over = useWaitOver(error);
  return (
    <ErrorState
      error={error}
      message={rateLimitMessage(error)}
      retryLabel="Try again"
      retryDisabled={!over}
      retrying={retrying}
      onRetry={onRetry}
    />
  );
}

/**
 * "These readings are from …" with "Clear readings" (S UX item 2, stale
 * fields). Without a valid date to name, the sentence stops after the set.
 */
function StaleFields() {
  const { draft, update } = useDraft();
  const set = draft.readings.reading_set;
  if (!readingsStale(draft) || !set) return null;
  const dateIso = draft.readings.date_iso;
  const from = `${draft.readings.occasion} (${formatServiceDate(set.date_iso)})`;
  return (
    <div className="grid justify-items-start gap-2">
      <p className="text-sm">
        {isValidDateIso(dateIso)
          ? `These readings are from ${from}, not ${formatServiceDate(dateIso)}.`
          : `These readings are from ${from}.`}
      </p>
      <Button type="button" variant="outline" size="touch" onClick={() => update(clearReadings)}>
        Clear readings
      </Button>
    </div>
  );
}

/**
 * What the lectionary said about the draft's date (S UX item 2): exactly one
 * of Loading, the reading sets, No readings, Unavailable or Rate limited,
 * directly under the date, plus the partial note and the stale-fields note.
 * For a date the lookup refuses only the stale-fields note can show (the date
 * field explains the date). Focus never moves on its own; "Enter readings"
 * moves it to Occasion.
 */
export function LectionaryStatus({ onEnterReadings }: { onEnterReadings: () => void }) {
  const { draft } = useDraft();
  const { lookupDate, settled, query } = useLectionaryLookup();
  if (!canLookUp(draft.readings.date_iso)) return <StaleFields />;
  const retry = () => void query.refetch();

  if (!settled || query.isPending) return <Loading lookupDate={draft.readings.date_iso} />;

  // An answer already on screen wins over a failed background refetch.
  const lect = query.data;
  if (lect === undefined) {
    if (query.error?.code === "rate_limited") {
      return (
        <div className="grid gap-3">
          <RateLimited error={query.error} onRetry={retry} retrying={query.isFetching} />
          <StaleFields />
        </div>
      );
    }
    return (
      <div className="grid gap-3">
        <ErrorState
          error={query.error}
          message={LECTIONARY_UNAVAILABLE}
          retryLabel="Try again"
          retrying={query.isFetching}
          onRetry={retry}
        />
        <StaleFields />
      </div>
    );
  }

  if (lect.status === "no_readings" || lect.reading_sets.length === 0) {
    return (
      <div className="grid gap-3">
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>No lectionary readings for {formatLongDate(lookupDate)}.</AlertTitle>
          <AlertDescription>
            <p>Enter the occasion and readings below.</p>
            <Button type="button" variant="outline" size="touch" className="mt-2" onClick={onEnterReadings}>
              Enter readings
            </Button>
          </AlertDescription>
        </Alert>
        <StaleFields />
      </div>
    );
  }

  // One or more sets: the partial note. Task 8 adds the set switcher and the banner.
  return lect.partial ? (
    <p className="text-sm text-muted-foreground">
      One lectionary source didn&apos;t respond, so other reading options for this date may be missing.
    </p>
  ) : null;
}
```

Replace `frontend/src/components/builder/readings/readings-step.tsx` with:

```tsx
"use client";

import { useRef } from "react";

import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useChurch } from "@/lib/church-context";
import { todayIn } from "@/lib/dates";
import { churchZone } from "@/lib/draft/schema";
import { useChurchProfile } from "@/lib/queries/church";

import { LectionaryStatus } from "./lectionary-status";
import { OccasionField } from "./occasion-field";
import { ScriptureLinesField } from "./scripture-lines-field";
import { ServiceDateField } from "./service-date-field";

/**
 * Step 1, Date & readings (S UX "Step 1"): the service date, the lectionary
 * status, the occasion and scripture lines, the readings with their text, and
 * the bulletin's two readings. The shell's `<LectionarySync>` does the lookup
 * and the automatic fill; this step shows them.
 */
export function ReadingsStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { lookupDate, query } = useLectionaryLookup();
  const occasionRef = useRef<HTMLInputElement>(null);
  if (!profile) return null;
  const today = todayIn(churchZone(profile));
  const lect = query.data?.date === lookupDate ? query.data : undefined;

  return (
    <section aria-label="Date & readings" className="grid gap-6">
      <ServiceDateField today={today} />
      <LectionaryStatus onEnterReadings={() => occasionRef.current?.focus()} />
      <OccasionField lect={lect} inputRef={occasionRef} />
      <ScriptureLinesField />
    </section>
  );
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  1 passed (1)`, `Tests  10 passed (10)`; the suite ` Test Files  55 passed (55)`, `      Tests  330 passed (330)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `readings-step.tsx` and its test, `??` for the two new files.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/components/builder/readings/lectionary-status.tsx frontend/src/components/builder/readings/use-wait-over.ts frontend/src/components/builder/readings/readings-step.tsx frontend/src/components/builder/readings/readings-step.test.tsx
git commit -m "Readings step: what the lectionary said, with loading, no readings, unavailable, rate limited and stale fields (S UX item 2; AC14)" -m "Loading shows while the date settles and the lookup runs, with Still
working after 8 s. No readings names the day and offers Enter readings,
which focuses Occasion; focus never moves on its own. A failure shows the
lectionary's own sentence with Try again; a 429 waits for Retry-After
before Try again turns on. Lectionary fields from another date stay, with
a note and Clear readings. Frontend 325 -> 330 tests in 55 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 4 files changed; the push line.

**Review checkpoint (T7):** the reviewer checks that exactly one state shows, that a failed lookup never changes the fields (the test's occasion stays), that "Enter readings" is the only focus move, the copy against "Messages", and that the one test faking `setTimeout` calls `vi.useRealTimers()` first.

### Task 8: Several reading sets, the "available" banner and "Replace your readings?" (S UX items 2 and 3; F §4.6 "Never destroy typed input"; AC14, AC15; owner answer Q2; clarification 15)

When a date has more than one set, a radio group ("This date has more than one set of readings") shows one card per set, keyed by index (two sets with the same name stay distinct), selected by `selectedSetIndex` (2b). Over empty or lectionary fields a choice applies at once through `chooseReadingSet` (T1), unless the date moved meanwhile; over typed or archived fields it asks "Replace your readings?" first. After typing, a changed date shows "Readings for {date} are available." (a `role="status"` callout) with "Use them" (`showAvailableBanner`, 2b), which asks the same question; "Keep mine" hides the banner for that date until the date changes. An archived service on its own date keeps its fields and shows no banner. The partial note stays.

**Files:**
- Create: `frontend/src/components/builder/readings/reading-set-picker.tsx`, `frontend/src/components/builder/readings/replace-readings-dialog.tsx`
- Modify: `frontend/src/components/builder/readings/lectionary-status.tsx` (replaced: adds `ReadingSets`)
- Test: `frontend/src/components/builder/readings/readings-step.test.tsx` (+5)

**Interfaces:**
- Consumes: `RadioGroup`, `RadioGroupItem` (T4), `ConfirmDialog` with `cancelLabel` (T4), `chooseReadingSet` (T1), `applyReadingSet`, `selectedSetIndex`, `showAvailableBanner` (2b).
- Produces: `ReadingSetPicker({ lect, selected, onChoose })`, `ReplaceReadingsDialog({ setName, onConfirm, onKeep })` (closed while `setName` is null; Escape and the backdrop keep the readings), and `LectionaryStatus` rendering them.

Counts after this task: frontend **335 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder/readings/reading-set-picker.tsx && echo "no T8 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T8 files yet`; `Test Files  55 passed (55)`, `Tests  330 passed (330)`.

- [ ] **Step 2 (agent): Write the failing tests**

In `frontend/src/components/builder/readings/readings-step.test.tsx`, replace the import block (from the first line through `import { ReadingsStep } from "./readings-step";`) with:

```tsx
/**
 * The Date & readings step (S UX "Step 1", Testing `readings-step.test.tsx`;
 * AC14-AC16). The step renders inside the real builder layout against the fake
 * API. Only `Date` is faked (Tuesday, September 29, 2026 at noon in New York),
 * so a fresh draft is dated Sunday, October 4, and the 400 ms lookup delay and
 * the draft's writes run on real timers.
 */
import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setDate, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  lectionary,
  lectionaryRoute,
  me,
  noReadings,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { occasionCaption } from "./occasion-field";
import { ReadingsStep } from "./readings-step";
```

Append to `frontend/src/components/builder/readings/readings-step.test.tsx`:

```tsx

// --- reading sets and the available banner (S UX items 2 and 3; AC14, AC15) ------

const EASTER = ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"];

/** Two sets with the same name: only their index tells them apart. */
function twins(date: string): Lectionary {
  const answer = lectionary(date);
  return { ...answer, reading_sets: answer.reading_sets.map((set) => ({ ...set, name: "Nativity of the Lord" })) };
}

/** October 4 has the two fixture sets; October 11 and 18 have one set each, with their own lines. */
function october(date: string): Lectionary {
  const own: Record<string, [string, string[]]> = {
    "2026-10-11": ["Twentieth Sunday after Pentecost", ["Isaiah 25:1-9", "Psalm 23", "Philippians 4:1-9", "Matthew 22:1-14"]],
    "2026-10-18": ["Twenty-First Sunday after Pentecost", ["Isaiah 45:1-7", "Psalm 96:1-9", "1 Thessalonians 1:1-10", "Matthew 22:15-22"]],
  };
  const answer = lectionary(date);
  if (!own[date]) return answer;
  const [name, scriptures] = own[date];
  return { ...answer, reading_sets: [{ name, scriptures, source: "merged" }], default_index: 0 };
}

describe("reading sets and the available banner (S UX items 2 and 3)", () => {
  it("shows one card per set, keyed by index, and choosing another applies it and makes the date the user's", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(twins) });
    const group = await screen.findByRole("radiogroup", { name: "This date has more than one set of readings" });
    const cards = within(group).getAllByRole("radio");
    expect(cards).toHaveLength(2);
    await waitFor(() => expect(cards[0]).toBeChecked());
    expect(within(group).getByText(ISAIAH.join(" · "))).toBeInTheDocument();
    expect(within(group).getByText(EASTER.join(" · "))).toBeInTheDocument();
    expect(probe()).toMatch(/^default\/lectionary\//);

    await user.click(within(group).getByText(EASTER.join(" · ")));
    expect(screen.queryByRole("alertdialog")).toBeNull(); // lectionary fields: no question
    await waitFor(() => expect(cards[1]).toBeChecked());
    expect(screen.getByLabelText("Scripture readings")).toHaveValue(EASTER.join("\n"));
    expect(probe()).toMatch(/^user\/lectionary\//);
  });

  it("asks before a set replaces typed readings: Keep mine keeps them, Replace readings replaces them", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) }, testDraft((d) => editOccasion(d, "Harvest")));
    const group = await screen.findByRole("radiogroup", { name: "This date has more than one set of readings" });
    await user.click(within(group).getByText(EASTER.join(" · ")));
    let dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(dialog).toHaveAccessibleDescription(
      "Your occasion and scripture list will be replaced with “Resurrection of the Lord” from the lectionary.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");

    await user.click(within(group).getByText(EASTER.join(" · ")));
    dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(screen.getByLabelText("Occasion")).toHaveValue("Resurrection of the Lord"));
    expect(probe()).toMatch(/^user\/lectionary\//);
  });

  it("after typing, a new date shows the banner instead of replacing; Use them asks, then replaces", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) });
    const occasion = await screen.findByLabelText("Occasion");
    await waitFor(() => expect(occasion).toHaveValue("Nineteenth Sunday after Pentecost"));
    await user.clear(occasion);
    await user.type(occasion, "Harvest");
    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    const banner = await screen.findByText("Readings for October 11, 2026 are available.");
    expect(banner.closest("[role=status]")).not.toBeNull(); // an offer, not an alert
    expect(occasion).toHaveValue("Harvest");

    await user.click(screen.getByRole("button", { name: "Use them" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    expect(dialog).toHaveAccessibleDescription(
      "Your occasion and scripture list will be replaced with “Twentieth Sunday after Pentecost” from the lectionary.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Replace readings" }));
    await waitFor(() => expect(occasion).toHaveValue("Twentieth Sunday after Pentecost"));
    expect(screen.queryByText("Readings for October 11, 2026 are available.")).toBeNull();
  });

  it("deleting the Psalm line of this date's set raises no banner; Keep mine hides it until the date changes", async () => {
    const { user } = renderStep({ lookup: lectionaryRoute(october) });
    const lines = await screen.findByLabelText("Scripture readings");
    await waitFor(() => expect(lines).toHaveValue(ISAIAH.join("\n")));
    fireEvent.change(lines, { target: { value: [ISAIAH[0], ISAIAH[2], ISAIAH[3]].join("\n") } });
    expect(probe()).toMatch(/\/user\//);
    // Once the edit is written (400 ms later), still no banner.
    await waitFor(() => expect(JSON.parse(window.localStorage.getItem(KEY) ?? "{}").readings.scriptures).toHaveLength(3));
    expect(screen.queryByText(/are available\.$/)).toBeNull();

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    await user.click(await screen.findByRole("button", { name: "Use them" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your readings?" });
    await user.click(within(dialog).getByRole("button", { name: "Keep mine" }));
    await waitFor(() => expect(screen.queryByText("Readings for October 11, 2026 are available.")).toBeNull());

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-18" } });
    expect(await screen.findByText("Readings for October 18, 2026 are available.")).toBeInTheDocument();
  });

  it("an archived service keeps its fields on its own date, and is offered the readings after a date change", async () => {
    const archived = testDraft((d) => ({
      ...d,
      readings: {
        ...d.readings,
        date_origin: "archive",
        fields_origin: "archive",
        reading_set: null,
        occasion: "Harvest",
        scriptures: ["Joel 2:21-27"],
      },
    }));
    const { lookups } = renderStep({ lookup: lectionaryRoute(october) }, archived);
    const group = await screen.findByRole("radiogroup", { name: "This date has more than one set of readings" });
    for (const radio of within(group).getAllByRole("radio")) expect(radio).not.toBeChecked(); // neither set is these lines
    expect(lookups()).toEqual(["/lectionary/readings?date=2026-10-04"]);
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
    expect(screen.queryByText(/are available\.$/)).toBeNull();

    fireEvent.change(screen.getByLabelText("Service date"), { target: { value: "2026-10-11" } });
    expect(await screen.findByText("Readings for October 11, 2026 are available.")).toBeInTheDocument();
    expect(screen.getByLabelText("Occasion")).toHaveValue("Harvest");
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × reading sets and the available banner (S UX items 2 and 3) > shows one card per set, keyed by index, and choosing another applies it and makes the date the user's <t>ms
   × reading sets and the available banner (S UX items 2 and 3) > asks before a set replaces typed readings: Keep mine keeps them, Replace readings replaces them <t>ms
   × reading sets and the available banner (S UX items 2 and 3) > after typing, a new date shows the banner instead of replacing; Use them asks, then replaces <t>ms
   × reading sets and the available banner (S UX items 2 and 3) > deleting the Psalm line of this date's set raises no banner; Keep mine hides it until the date changes <t>ms
   × reading sets and the available banner (S UX items 2 and 3) > an archived service keeps its fields on its own date, and is offered the readings after a date change <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯
      Tests  5 failed | 10 passed (15)
```

- [ ] **Step 4 (agent): Write the switcher, the dialog and the banner**

Create `frontend/src/components/builder/readings/reading-set-picker.tsx`:

```tsx
"use client";

import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { Lectionary } from "@/lib/api/types";

/**
 * The set switcher (S UX item 2, "Several sets"): one card per set, keyed by
 * index, so two sets with the same name stay distinct. `selected` is
 * `selectedSetIndex` (the set equal to the draft's lines, else the stored
 * index for this date, else none).
 */
export function ReadingSetPicker({
  lect,
  selected,
  onChoose,
}: {
  lect: Lectionary;
  selected: number | null;
  onChoose: (index: number) => void;
}) {
  return (
    <div className="grid gap-2">
      <p id="reading-sets-legend" className="text-sm font-medium">
        This date has more than one set of readings
      </p>
      <RadioGroup
        aria-labelledby="reading-sets-legend"
        value={selected === null ? "" : String(selected)}
        onValueChange={(value) => onChoose(Number(value))}
      >
        {lect.reading_sets.map((set, index) => (
          <label
            key={index}
            className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border p-3 has-data-checked:border-primary"
          >
            <RadioGroupItem value={String(index)} className="mt-0.5" />
            <span className="grid min-w-0 gap-0.5">
              <span className="text-sm font-medium">{set.name}</span>
              <span className="text-sm break-words text-muted-foreground">{set.scriptures.join(" · ")}</span>
            </span>
          </label>
        ))}
      </RadioGroup>
    </div>
  );
}
```

Create `frontend/src/components/builder/readings/replace-readings-dialog.tsx`:

```tsx
"use client";

import { ConfirmDialog } from "@/components/app/confirm-dialog";

/**
 * "Replace your readings?" (S UX item 3): asked before a lectionary set
 * replaces typed or archived readings. "Keep mine", Escape and the backdrop
 * all keep them.
 */
export function ReplaceReadingsDialog({
  setName,
  onConfirm,
  onKeep,
}: {
  /** The set that would replace the readings; null keeps the dialog closed. */
  setName: string | null;
  onConfirm: () => void;
  onKeep: () => void;
}) {
  return (
    <ConfirmDialog
      open={setName !== null}
      onOpenChange={(open) => {
        if (!open) onKeep();
      }}
      title="Replace your readings?"
      description={`Your occasion and scripture list will be replaced with “${setName ?? ""}” from the lectionary.`}
      confirmLabel="Replace readings"
      cancelLabel="Keep mine"
      onConfirm={onConfirm}
    />
  );
}
```

Replace `frontend/src/components/builder/readings/lectionary-status.tsx` with:

```tsx
"use client";

import { InfoIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/app/error-state";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError } from "@/lib/api/client";
import type { Lectionary } from "@/lib/api/types";
import { formatLongDate, formatServiceDate, isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import {
  applyReadingSet,
  chooseReadingSet,
  clearReadings,
  readingsStale,
  selectedSetIndex,
  showAvailableBanner,
} from "@/lib/draft/readings";
import { canLookUp } from "@/lib/queries/lectionary";

import { ReadingSetPicker } from "./reading-set-picker";
import { ReplaceReadingsDialog } from "./replace-readings-dialog";
import { rateLimitMessage, useWaitOver } from "./use-wait-over";

export const LECTIONARY_UNAVAILABLE =
  "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.";
/** After this long, Loading adds "Still working — this can take up to a minute." */
export const STILL_WORKING_MS = 8_000;

function Loading({ lookupDate }: { lookupDate: string }) {
  const [slowFor, setSlowFor] = useState<string | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setSlowFor(lookupDate), STILL_WORKING_MS);
    return () => clearTimeout(timer);
  }, [lookupDate]);
  return (
    <div role="status" className="grid gap-2">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <p className="text-sm text-muted-foreground">Looking up the lectionary…</p>
      {slowFor === lookupDate ? (
        <p className="text-sm text-muted-foreground">Still working — this can take up to a minute.</p>
      ) : null}
    </div>
  );
}

function RateLimited({ error, onRetry, retrying }: { error: ApiError; onRetry: () => void; retrying: boolean }) {
  const over = useWaitOver(error);
  return (
    <ErrorState
      error={error}
      message={rateLimitMessage(error)}
      retryLabel="Try again"
      retryDisabled={!over}
      retrying={retrying}
      onRetry={onRetry}
    />
  );
}

/**
 * "These readings are from …" with "Clear readings" (S UX item 2, stale
 * fields). Without a valid date to name, the sentence stops after the set.
 */
function StaleFields() {
  const { draft, update } = useDraft();
  const set = draft.readings.reading_set;
  if (!readingsStale(draft) || !set) return null;
  const dateIso = draft.readings.date_iso;
  const from = `${draft.readings.occasion} (${formatServiceDate(set.date_iso)})`;
  return (
    <div className="grid justify-items-start gap-2">
      <p className="text-sm">
        {isValidDateIso(dateIso)
          ? `These readings are from ${from}, not ${formatServiceDate(dateIso)}.`
          : `These readings are from ${from}.`}
      </p>
      <Button type="button" variant="outline" size="touch" onClick={() => update(clearReadings)}>
        Clear readings
      </Button>
    </div>
  );
}

/**
 * This date's sets (S UX items 2 and 3): the switcher when there are several,
 * the partial note, and the "Readings … are available" banner. A set chosen
 * over empty or lectionary fields applies at once; over typed or archived
 * fields it asks first. "Keep mine" hides the banner for this date until the
 * date changes (component state, not stored).
 */
function ReadingSets({ lect }: { lect: Lectionary }) {
  const { draft, update } = useDraft();
  const [asking, setAsking] = useState<{ index: number; from: "switcher" | "banner" } | null>(null);
  const [keptFor, setKeptFor] = useState<string | null>(null);
  const dateIso = draft.readings.date_iso;
  const selected = selectedSetIndex(draft, lect);
  const banner = keptFor !== dateIso && showAvailableBanner(draft, lect);
  const origin = draft.readings.fields_origin;

  function choose(index: number) {
    if (origin === "empty" || origin === "lectionary") {
      // Like replace(): a choice that lands after the date moved does nothing.
      update((d) => (d.readings.date_iso !== lect.date ? d : chooseReadingSet(d, lect, index)));
    } else setAsking({ index, from: "switcher" });
  }

  function replace() {
    if (!asking) return;
    const { index, from } = asking;
    setAsking(null);
    update((d) => {
      if (d.readings.date_iso !== lect.date) return d; // the date moved while the dialog was open
      return from === "switcher" ? chooseReadingSet(d, lect, index) : applyReadingSet(d, lect, index);
    });
  }

  return (
    <div className="grid gap-3">
      {lect.reading_sets.length > 1 ? <ReadingSetPicker lect={lect} selected={selected} onChoose={choose} /> : null}
      {lect.partial ? (
        <p className="text-sm text-muted-foreground">
          One lectionary source didn&apos;t respond, so other reading options for this date may be missing.
        </p>
      ) : null}
      {banner ? (
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>Readings for {formatServiceDate(lect.date)} are available.</AlertTitle>
          <AlertDescription>
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="mt-2"
              onClick={() => setAsking({ index: selected ?? lect.default_index ?? 0, from: "banner" })}
            >
              Use them
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      <ReplaceReadingsDialog
        setName={asking ? (lect.reading_sets[asking.index]?.name ?? null) : null}
        onConfirm={replace}
        onKeep={() => {
          setAsking(null);
          setKeptFor(dateIso);
        }}
      />
    </div>
  );
}

/**
 * What the lectionary said about the draft's date (S UX item 2): exactly one
 * of Loading, the reading sets, No readings, Unavailable or Rate limited,
 * directly under the date, plus the partial note and the stale-fields note.
 * For a date the lookup refuses only the stale-fields note can show (the date
 * field explains the date). Focus never moves on its own; "Enter readings"
 * moves it to Occasion.
 */
export function LectionaryStatus({ onEnterReadings }: { onEnterReadings: () => void }) {
  const { draft } = useDraft();
  const { lookupDate, settled, query } = useLectionaryLookup();
  if (!canLookUp(draft.readings.date_iso)) return <StaleFields />;
  const retry = () => void query.refetch();

  if (!settled || query.isPending) return <Loading lookupDate={draft.readings.date_iso} />;

  // An answer already on screen wins over a failed background refetch.
  const lect = query.data;
  if (lect === undefined) {
    if (query.error?.code === "rate_limited") {
      return (
        <div className="grid gap-3">
          <RateLimited error={query.error} onRetry={retry} retrying={query.isFetching} />
          <StaleFields />
        </div>
      );
    }
    return (
      <div className="grid gap-3">
        <ErrorState
          error={query.error}
          message={LECTIONARY_UNAVAILABLE}
          retryLabel="Try again"
          retrying={query.isFetching}
          onRetry={retry}
        />
        <StaleFields />
      </div>
    );
  }

  if (lect.status === "no_readings" || lect.reading_sets.length === 0) {
    return (
      <div className="grid gap-3">
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>No lectionary readings for {formatLongDate(lookupDate)}.</AlertTitle>
          <AlertDescription>
            <p>Enter the occasion and readings below.</p>
            <Button type="button" variant="outline" size="touch" className="mt-2" onClick={onEnterReadings}>
              Enter readings
            </Button>
          </AlertDescription>
        </Alert>
        <StaleFields />
      </div>
    );
  }

  return <ReadingSets lect={lect} />;
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  1 passed (1)`, `Tests  15 passed (15)`; the suite ` Test Files  55 passed (55)`, `      Tests  335 passed (335)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `lectionary-status.tsx` and the test, `??` for the two new files.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/components/builder/readings/reading-set-picker.tsx frontend/src/components/builder/readings/replace-readings-dialog.tsx frontend/src/components/builder/readings/lectionary-status.tsx frontend/src/components/builder/readings/readings-step.test.tsx
git commit -m "Readings step: the set switcher, the available banner and Replace your readings? (S UX items 2, 3; AC14, AC15)" -m "A date with several sets shows one card per set, keyed by index. A
choice applies at once over lectionary or empty fields and makes a default
date the user's (owner answer Q2); over typed or archived fields it asks
Replace your readings? first. After typing, a new date's readings are
offered by a banner; Keep mine hides it until the date changes. An
archived service on its own date keeps its fields. Frontend 330 -> 335
tests in 55 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 4 files changed; the push line.

**Review checkpoint (T8):** the reviewer checks the index keys, that typed and archived fields change only through a confirmed dialog, that the banner rule is 2b's `showAvailableBanner` unchanged, and that a dialog confirmed, or a set chosen, after the date moved does nothing.

### Task 9: The readings list, passage text and the translation (S UX item 6, "Other states" translations row; F §4.8, §4.9 items 3, 6; AC16; clarifications 13, 14, 16)

Under "Readings", the "Bible translation" select (disabled, showing the church's translation, until the list loads or when it fails), "Passage text shown in {label}." and "Show all text"; then one row per cleaned line, 400 ms behind the textarea. Each row shows the reference, a badge per " or " alternative (OT, Psalm, NT, or "?" with "Book not recognized", 24 px on phones) and "Show text" / "Hide text" (named "Show text: {reference}" for screen readers, as is each row's "Try again"). Only open rows fetch, three at a time (T3); a line over 200 characters cannot be opened and is never sent; editing a line closes its row. The text follows S's table: loading, all loaded (one headed section per alternative), some text ("Couldn't load {reference}." and "Part of this passage couldn't be loaded.", with "Try again" when unavailable), not found, unavailable or a failed request, a 429 (wait, then "Try again"), a 422 (the server's message). Changing the translation refetches the open rows and stores the choice only when it differs from the church's.

**Files:**
- Create: `frontend/src/components/builder/readings/translation-select.tsx`, `passage-text.tsx`, `reading-row.tsx`, `readings-list.tsx`
- Modify: `frontend/src/components/builder/readings/readings-step.tsx` (renders `ReadingsList`)
- Test: `frontend/src/components/builder/readings/readings-step.test.tsx` (+7)

**Interfaces:**
- Consumes: `useTranslations` (T2), `usePassage` (T3), `useDebouncedValue` (T2), `useWaitOver`, `rateLimitMessage` (T7), `MAX_LINE` (T6), `Collapsible*`, `Tooltip*` (T4), `Select*`, `Badge`/`badgeVariants`, `Button`/`buttonVariants`, `cleanScriptures`, `effectiveTranslation`, `setTranslation` (2b), `classify`, `splitAlternatives` (2b).
- Produces: `TranslationSelect({ church, translations })`, `PassageText({ reference, translation })`, `ReadingRow({ reference, translation, open, onOpenChange })`, `LIST_DELAY_MS = 400`, `ReadingsList({ church })`.

Counts after this task: frontend **342 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder/readings/readings-list.tsx && echo "no T9 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T9 files yet`; `Test Files  55 passed (55)`, `Tests  335 passed (335)`.

- [ ] **Step 2 (agent): Write the failing tests**

Append to `frontend/src/components/builder/readings/readings-step.test.tsx`:

```tsx

// --- readings list and passage text (S UX item 6; AC16) -----------------------------

type Status = "ok" | "not_found" | "unavailable";
type PassageAnswer = { status: Status; sections: { reference: string; status: Status; text: string | null }[] };

/** One section per " or " alternative, all loaded. */
function okPassage(reference: string, translation = "web"): PassageAnswer {
  return {
    status: "ok",
    sections: reference.split(/\s+or\s+/i).map((alt) => ({ reference: alt, status: "ok", text: `${alt} (${translation}) text.` })),
  };
}

/** `POST /scripture/passages` answering each ref with `answer(ref, translation)` (or a `FakeResponse`). */
function passagesRoute(answer: (ref: string, translation: string) => PassageAnswer | ReturnType<typeof fakeError> = okPassage) {
  return (req: RecordedRequest) => {
    const { refs, translation } = req.body as { refs: string[]; translation: string };
    const result = answer(refs[0], translation);
    if ("status" in result && typeof result.status === "number") return result;
    return {
      translation,
      translation_label: translations().items.find((item) => item.id === translation)?.label ?? translation,
      passages: [{ reference: refs[0], ...(result as PassageAnswer) }],
    };
  };
}

function typedLines(lines: string[]): DraftV1 {
  return testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "user", occasion: "Harvest", scriptures: lines } }));
}

/** The row for `reference` in the Readings list. */
function row(reference: string) {
  const list = screen.getByRole("region", { name: "Readings" });
  const item = within(list)
    .getAllByRole("listitem")
    .find((li) => li.firstElementChild?.firstElementChild?.textContent === reference);
  if (!item) throw new Error(`no row for ${reference}`);
  return within(item);
}

async function findRow(reference: string) {
  await waitFor(() => row(reference));
  return row(reference);
}

describe("readings list and passage text (S UX item 6)", () => {
  it("fetches a passage only when its row opens: one reference, in the church's translation", async () => {
    const { user, api } = renderStep({ passages: passagesRoute() }, applyReadingSet(testDraft(), lectionary("2026-10-04"), 0));
    const isaiah = await findRow("Isaiah 5:1-7");
    expect(isaiah.getByText("OT")).toBeInTheDocument();
    expect(row("Psalm 80:7-15").getByText("Psalm")).toBeInTheDocument();
    expect(row("Matthew 21:33-46").getByText("NT")).toBeInTheDocument();
    expect(screen.getByText("Passage text shown in World English Bible (WEB).")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST")).toEqual([]);

    await user.click(isaiah.getByRole("button", { name: "Show text: Isaiah 5:1-7" }));
    expect(await isaiah.findByText("Isaiah 5:1-7 (web) text.")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST").map((r) => [r.path, r.body, r.headers["X-Church-Id"]])).toEqual([
      ["/scripture/passages", { refs: ["Isaiah 5:1-7"], translation: "web" }, undefined],
    ]);
    await user.click(isaiah.getByRole("button", { name: "Hide text: Isaiah 5:1-7" }));
    expect(isaiah.queryByText("Isaiah 5:1-7 (web) text.")).toBeNull();
  });

  it("shows not found, unavailable and partial answers with their copy, and Try again refetches", async () => {
    const PASSION = "Matthew 26:14-27:66 or Matthew 27:11-54";
    let isaiahCalls = 0;
    const { user, api } = renderStep(
      {
        passages: passagesRoute((ref, translation) => {
          if (ref === "Hezekiah 1:1") return { status: "not_found", sections: [{ reference: ref, status: "not_found", text: null }] };
          if (ref === "Isaiah 50:4-9a") {
            isaiahCalls += 1;
            return isaiahCalls === 1
              ? { status: "unavailable", sections: [{ reference: ref, status: "unavailable", text: null }] }
              : okPassage(ref, translation);
          }
          return {
            status: "unavailable",
            sections: [
              { reference: "Matthew 26:14-27:66", status: "unavailable", text: null },
              { reference: "Matthew 27:11-54", status: "ok", text: "Jesus stood before the governor." },
            ],
          };
        }),
      },
      typedLines(["Hezekiah 1:1", "Isaiah 50:4-9a", PASSION]),
    );
    const hezekiah = await findRow("Hezekiah 1:1");
    const unknown = hezekiah.getByRole("button", { name: "Book not recognized" });
    expect(unknown).toHaveTextContent("?");
    expect(unknown).toHaveClass("h-6", "min-w-6"); // a 24 px target on phones
    expect(row(PASSION).getAllByText("NT")).toHaveLength(2);

    await user.click(hezekiah.getByRole("button", { name: "Show text: Hezekiah 1:1" }));
    expect(
      await hezekiah.findByText("Couldn't find this passage. Check the reference, for example “Matthew 17:1-9”."),
    ).toBeInTheDocument();

    const isaiah = row("Isaiah 50:4-9a");
    await user.click(isaiah.getByRole("button", { name: "Show text: Isaiah 50:4-9a" }));
    expect(await isaiah.findByText("Passage text isn't available right now.")).toBeInTheDocument();
    await user.click(isaiah.getByRole("button", { name: "Try again: Isaiah 50:4-9a" }));
    expect(await isaiah.findByText("Isaiah 50:4-9a (web) text.")).toBeInTheDocument();

    const passion = row(PASSION);
    await user.click(passion.getByRole("button", { name: `Show text: ${PASSION}` }));
    expect(await passion.findByText("Jesus stood before the governor.")).toBeInTheDocument();
    expect(passion.getByText("Matthew 27:11-54")).toBeInTheDocument(); // each alternative under its own heading
    expect(passion.getByText("Couldn't load Matthew 26:14-27:66.")).toBeInTheDocument();
    expect(passion.getByText("Part of this passage couldn't be loaded.")).toBeInTheDocument();
    const before = api.requests.filter((r) => r.method === "POST").length;
    await user.click(passion.getByRole("button", { name: `Try again: ${PASSION}` }));
    await waitFor(() => expect(api.requests.filter((r) => r.method === "POST").length).toBe(before + 1));
  });

  it("a failed request says the text isn't available, a 429 waits for Retry-After, and a 422 shows the server's message", async () => {
    const limited = fakeError(429, "rate_limited", "Too many requests. Try again in 1 seconds.", {
      details: { retry_after_seconds: 1 },
    });
    let limitedCalls = 0;
    const { user } = renderStep(
      {
        passages: passagesRoute((ref, translation) => {
          if (ref === "John 3:16") return fakeError(500, "internal_error", "Something went wrong.");
          if (ref === "Romans 8:1") {
            limitedCalls += 1;
            return limitedCalls === 1 ? limited : okPassage(ref, translation);
          }
          return fakeError(422, "invalid_request", "Too many passages in one request.", {
            fields: { refs: "Too many passages in one request." },
          });
        }),
      },
      typedLines(["John 3:16", "Romans 8:1", "Psalm 1; Psalm 2; Psalm 3"]),
    );
    const john = await findRow("John 3:16");
    await user.click(john.getByRole("button", { name: "Show text: John 3:16" }));
    expect(await john.findByText("Passage text isn't available right now.")).toBeInTheDocument();
    expect(john.getByRole("button", { name: "Try again: John 3:16" })).toBeEnabled();

    const romans = row("Romans 8:1");
    await user.click(romans.getByRole("button", { name: "Show text: Romans 8:1" }));
    expect(await romans.findByText("Too many requests — try again in 1 s.")).toBeInTheDocument();
    const retry = romans.getByRole("button", { name: "Try again: Romans 8:1" });
    expect(retry).toBeDisabled();
    await waitFor(() => expect(retry).toBeEnabled(), { timeout: 3_000 });
    await user.click(retry);
    expect(await romans.findByText("Romans 8:1 (web) text.")).toBeInTheDocument();

    const psalms = row("Psalm 1; Psalm 2; Psalm 3");
    await user.click(psalms.getByRole("button", { name: "Show text: Psalm 1; Psalm 2; Psalm 3" }));
    expect(await psalms.findByText("Too many passages in one request.")).toBeInTheDocument();
  });

  it("never opens or sends a line over 200 characters, and editing a line closes its row", async () => {
    const long = `Genesis 1:1 ${"x".repeat(200)}`;
    const { user, api } = renderStep({ passages: passagesRoute() }, typedLines(["Mark 1:1-8", long]));
    const longRow = await findRow(long);
    // Base UI keeps a disabled trigger focusable, so it is aria-disabled rather than disabled.
    const longToggle = longRow.getByRole("button", { name: `Show text: ${long}` });
    expect(longToggle).toHaveAttribute("aria-disabled", "true");
    await user.click(longToggle);

    const mark = row("Mark 1:1-8");
    await user.click(mark.getByRole("button", { name: "Show text: Mark 1:1-8" }));
    await mark.findByText("Mark 1:1-8 (web) text.");
    fireEvent.change(screen.getByLabelText("Scripture readings"), { target: { value: `Mark 1:1-11\n${long}` } });
    const edited = await findRow("Mark 1:1-11");
    expect(edited.getByRole("button", { name: "Show text: Mark 1:1-11" })).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST").map((r) => (r.body as { refs: string[] }).refs[0])).toEqual([
      "Mark 1:1-8",
    ]);
  });

  it("Show all text opens every row with at most 3 requests in flight", async () => {
    let inFlight = 0;
    let most = 0;
    const lines = ["Genesis 1:1", "Exodus 3:1", "Psalm 23", "Romans 8:1", "John 1:1"];
    const { user, api } = renderStep(
      {
        passages: async (req: RecordedRequest) => {
          inFlight += 1;
          most = Math.max(most, inFlight);
          await new Promise((resolve) => setTimeout(resolve, 60));
          inFlight -= 1;
          return passagesRoute()(req);
        },
      },
      typedLines(lines),
    );
    await findRow("John 1:1");
    await user.click(screen.getByRole("button", { name: "Show all text" }));
    for (const line of lines) expect(await row(line).findByText(`${line} (web) text.`)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST")).toHaveLength(5);
    expect(most).toBe(3);
  });

  it("changing the translation refetches open rows in it and stores the choice", async () => {
    const { user, api } = renderStep({ passages: passagesRoute() }, typedLines(["Mark 1:1-8"]));
    const mark = await findRow("Mark 1:1-8");
    await user.click(mark.getByRole("button", { name: "Show text: Mark 1:1-8" }));
    await mark.findByText("Mark 1:1-8 (web) text.");

    await user.click(screen.getByRole("combobox", { name: "Bible translation" }));
    await user.click(await screen.findByRole("option", { name: "King James Version (KJV)" }));
    expect(await mark.findByText("Mark 1:1-8 (kjv) text.")).toBeInTheDocument();
    expect(screen.getByText("Passage text shown in King James Version (KJV).")).toBeInTheDocument();
    expect(api.requests.filter((r) => r.method === "POST").map((r) => (r.body as { translation: string }).translation)).toEqual([
      "web",
      "kjv",
    ]);
    expect(probe()).toMatch(/\/t=kjv$/);
  });

  it("with no readings it says what to do, and a failed translation list shows the church's translation", async () => {
    renderStep({ translations: fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByText("Add a reading above to see its text and choose the bulletin readings.")).toBeInTheDocument();
    const select = screen.getByRole("combobox", { name: "Bible translation" });
    await waitFor(() => expect(select).toHaveAttribute("data-disabled"));
    expect(select).toHaveTextContent("World English Bible (WEB)");
    expect(screen.getByText("Passage text shown in World English Bible (WEB).")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show all text" })).toBeDisabled();
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × readings list and passage text (S UX item 6) > fetches a passage only when its row opens: one reference, in the church's translation <t>ms
   × readings list and passage text (S UX item 6) > shows not found, unavailable and partial answers with their copy, and Try again refetches <t>ms
   × readings list and passage text (S UX item 6) > a failed request says the text isn't available, a 429 waits for Retry-After, and a 422 shows the server's message <t>ms
   × readings list and passage text (S UX item 6) > never opens or sends a line over 200 characters, and editing a line closes its row <t>ms
   × readings list and passage text (S UX item 6) > Show all text opens every row with at most 3 requests in flight <t>ms
   × readings list and passage text (S UX item 6) > changing the translation refetches open rows in it and stores the choice <t>ms
   × readings list and passage text (S UX item 6) > with no readings it says what to do, and a failed translation list shows the church's translation <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 7 ⎯⎯⎯⎯⎯⎯⎯
      Tests  7 failed | 15 passed (22)
```

- [ ] **Step 4 (agent): Write the list, the row, the passage text and the select, and show the list**

Create `frontend/src/components/builder/readings/translation-select.tsx`:

```tsx
"use client";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { ChurchProfile, Translations } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { effectiveTranslation, setTranslation } from "@/lib/draft/readings";

/**
 * "Bible translation" (S UX item 6; "Other states": translations list
 * failed). The choice is stored only when it differs from the church's
 * translation. Until the list loads, or when it fails, the select is
 * disabled and shows the church's translation.
 */
export function TranslationSelect({
  church,
  translations,
}: {
  church: Pick<ChurchProfile, "effective_translation" | "effective_translation_label">;
  translations: Translations | undefined;
}) {
  const { draft, update } = useDraft();
  const current = effectiveTranslation(draft, church, translations);
  const items: Record<string, string> = translations
    ? Object.fromEntries(translations.items.map((item) => [item.id, item.label]))
    : { [church.effective_translation]: church.effective_translation_label };
  const label = items[current] ?? church.effective_translation_label;

  return (
    <div className="grid gap-2">
      <Label id="translation-label">Bible translation</Label>
      <Select
        value={current}
        items={items}
        disabled={!translations}
        onValueChange={(value) => {
          if (typeof value === "string") update((d) => setTranslation(d, value, church.effective_translation));
        }}
      >
        <SelectTrigger
          aria-labelledby="translation-label"
          aria-describedby="translation-help"
          className="h-11 w-full sm:w-80 data-[size=default]:h-11"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(items).map(([id, text]) => (
            <SelectItem key={id} value={id}>
              {text}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p id="translation-help" className="text-sm text-muted-foreground">
        For the passage text shown here. The bulletin lists the references, not the verse text.
      </p>
      <p className="text-sm">Passage text shown in {label}.</p>
    </div>
  );
}
```

Create `frontend/src/components/builder/readings/passage-text.tsx`:

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { usePassage } from "@/lib/queries/passages";

import { rateLimitMessage, useWaitOver } from "./use-wait-over";

/** "Try again", named with the reference ("Try again: Mark 1:1-8"), since every open row can show one. */
function TryAgain({
  reference,
  onClick,
  disabled = false,
}: {
  reference: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <Button
      type="button"
      variant="outline"
      size="touch"
      disabled={disabled}
      aria-label={`Try again: ${reference}`}
      onClick={onClick}
    >
      Try again
    </Button>
  );
}

/**
 * An open row's passage text (S UX item 6 table): the first matching state of
 * loading, every section loaded, some text, not found, unavailable or a
 * failed request, a rate limit, or the server's 422. Text renders as React
 * text with its line breaks kept; " or " alternatives get one headed section
 * each.
 */
export function PassageText({ reference, translation }: { reference: string; translation: string }) {
  const query = usePassage(reference, translation, true);
  const limited = query.error?.code === "rate_limited" ? query.error : null;
  const waitOver = useWaitOver(limited);
  const retry = () => void query.refetch();

  if (query.isPending) return <p className="text-sm text-muted-foreground">Loading text…</p>;

  if (query.isError) {
    if (limited) {
      return (
        <div className="grid justify-items-start gap-2">
          <p className="text-sm">{rateLimitMessage(limited)}</p>
          <TryAgain reference={reference} onClick={retry} disabled={!waitOver || query.isFetching} />
        </div>
      );
    }
    if (query.error.status === 422) return <p className="text-sm">{query.error.message}</p>;
    return (
      <div className="grid justify-items-start gap-2">
        <p className="text-sm">Passage text isn&apos;t available right now.</p>
        <TryAgain reference={reference} onClick={retry} disabled={query.isFetching} />
      </div>
    );
  }

  const passage = query.data;
  const headed = passage.sections.length > 1;
  const anyText = passage.sections.some((section) => section.text);

  if (!anyText) {
    if (passage.status === "not_found") {
      return (
        <p className="text-sm">
          Couldn&apos;t find this passage. Check the reference, for example “Matthew 17:1-9”.
        </p>
      );
    }
    return (
      <div className="grid justify-items-start gap-2">
        <p className="text-sm">Passage text isn&apos;t available right now.</p>
        <TryAgain reference={reference} onClick={retry} disabled={query.isFetching} />
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {passage.sections.map((section, i) => (
        <div key={`${i}:${section.reference}`} className="grid gap-1">
          {headed ? <p className="text-xs font-medium text-muted-foreground">{section.reference}</p> : null}
          {section.text ? (
            <p className="text-sm whitespace-pre-wrap">{section.text}</p>
          ) : (
            <p className="text-sm">Couldn&apos;t load {section.reference}.</p>
          )}
        </div>
      ))}
      {passage.status !== "ok" ? (
        <div className="grid justify-items-start gap-2">
          <p className="text-sm text-muted-foreground">Part of this passage couldn&apos;t be loaded.</p>
          {passage.status === "unavailable" ? (
            <TryAgain reference={reference} onClick={retry} disabled={query.isFetching} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
```

Create `frontend/src/components/builder/readings/reading-row.tsx`:

```tsx
"use client";

import { Badge, badgeVariants } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { classify, splitAlternatives, type Classification, type Testament } from "@/lib/scripture-refs";
import { cn } from "@/lib/utils";

import { PassageText } from "./passage-text";
import { MAX_LINE } from "./scripture-lines-field";

const BADGE_TEXT: Record<Testament, string> = { ot: "OT", psalm: "Psalm", nt: "NT" };

/**
 * OT, Psalm or NT; an unknown book is "?" with the tooltip "Book not
 * recognized" (also its accessible name), at least 24 px square on phones.
 */
function TestamentBadge({ testament }: { testament: Classification }) {
  if (testament !== "unknown") return <Badge variant="secondary">{BADGE_TEXT[testament]}</Badge>;
  return (
    <Tooltip>
      <TooltipTrigger
        aria-label="Book not recognized"
        className={cn(badgeVariants({ variant: "outline" }), "h-6 min-w-6 sm:h-5 sm:min-w-0")}
      >
        ?
      </TooltipTrigger>
      <TooltipContent>Book not recognized</TooltipContent>
    </Tooltip>
  );
}

/**
 * One reading (S UX item 6): the reference, a badge per " or " alternative,
 * and "Show text" / "Hide text", named with the reference for screen readers
 * ("Show text: Mark 1:1-8"). The text loads only while the row is open. A
 * line over 200 characters cannot be opened and is never sent.
 */
export function ReadingRow({
  reference,
  translation,
  open,
  onOpenChange,
}: {
  reference: string;
  translation: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const tooLong = reference.length > MAX_LINE;
  const action = open && !tooLong ? "Hide text" : "Show text";
  return (
    <li className="grid gap-2 border-b py-3 last:border-b-0">
      <div className="flex flex-wrap items-start gap-2">
        <span className="min-w-0 flex-1 break-words">{reference}</span>
        <span className="flex flex-wrap gap-1">
          {splitAlternatives(reference).map((alternative, i) => (
            <TestamentBadge key={`${i}:${alternative}`} testament={classify(alternative)} />
          ))}
        </span>
      </div>
      <Collapsible open={open && !tooLong} onOpenChange={onOpenChange} disabled={tooLong}>
        <CollapsibleTrigger
          disabled={tooLong}
          aria-label={`${action}: ${reference}`}
          className={cn(
            buttonVariants({ variant: "outline", size: "touch" }),
            "justify-self-start aria-disabled:pointer-events-none aria-disabled:opacity-50",
          )}
        >
          {action}
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-2">
          <PassageText reference={reference} translation={translation} />
        </CollapsibleContent>
      </Collapsible>
    </li>
  );
}
```

Create `frontend/src/components/builder/readings/readings-list.tsx`:

```tsx
"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import type { ChurchProfile } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectiveTranslation } from "@/lib/draft/readings";
import { useTranslations } from "@/lib/queries/reference";
import { useDebouncedValue } from "@/lib/use-debounced-value";

import { ReadingRow } from "./reading-row";
import { MAX_LINE } from "./scripture-lines-field";
import { TranslationSelect } from "./translation-select";

/** How long the list trails the scripture lines, so typing does not rebuild it on every key. */
export const LIST_DELAY_MS = 400;

/**
 * "Readings" (S UX item 6): the translation, then one row per cleaned line,
 * 400 ms behind the textarea. Open rows are keyed by their reference text, so
 * editing a line closes its row. "Show all text" opens every row that can be
 * sent; the passage limiter keeps 3 requests in flight.
 */
export function ReadingsList({ church }: { church: ChurchProfile }) {
  const { draft } = useDraft();
  const translations = useTranslations();
  const translation = effectiveTranslation(draft, church, translations.data);
  const joined = useDebouncedValue(cleanScriptures(draft).join("\n"), LIST_DELAY_MS);
  const lines = joined === "" ? [] : joined.split("\n");
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set());

  function setRow(reference: string, next: boolean) {
    setOpen((current) => {
      const updated = new Set(current);
      if (next) updated.add(reference);
      else updated.delete(reference);
      return updated;
    });
  }

  return (
    <section aria-labelledby="readings-heading" className="grid gap-4">
      <h2 id="readings-heading" className="text-base font-medium">
        Readings
      </h2>
      <div className="grid gap-3">
        <TranslationSelect church={church} translations={translations.data} />
        <div>
          <Button
            type="button"
            variant="outline"
            size="touch"
            disabled={lines.length === 0}
            onClick={() => setOpen(new Set(lines.filter((line) => line.length <= MAX_LINE)))}
          >
            Show all text
          </Button>
        </div>
      </div>
      {lines.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Add a reading above to see its text and choose the bulletin readings.
        </p>
      ) : (
        <ul className="grid">
          {lines.map((reference, i) => (
            <ReadingRow
              key={`${i}:${reference}`}
              reference={reference}
              translation={translation}
              open={open.has(reference)}
              onOpenChange={(next) => setRow(reference, next)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
```

Replace `frontend/src/components/builder/readings/readings-step.tsx` with:

```tsx
"use client";

import { useRef } from "react";

import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useChurch } from "@/lib/church-context";
import { todayIn } from "@/lib/dates";
import { churchZone } from "@/lib/draft/schema";
import { useChurchProfile } from "@/lib/queries/church";

import { LectionaryStatus } from "./lectionary-status";
import { OccasionField } from "./occasion-field";
import { ReadingsList } from "./readings-list";
import { ScriptureLinesField } from "./scripture-lines-field";
import { ServiceDateField } from "./service-date-field";

/**
 * Step 1, Date & readings (S UX "Step 1"): the service date, the lectionary
 * status, the occasion and scripture lines, the readings with their text, and
 * the bulletin's two readings. The shell's `<LectionarySync>` does the lookup
 * and the automatic fill; this step shows them.
 */
export function ReadingsStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { lookupDate, query } = useLectionaryLookup();
  const occasionRef = useRef<HTMLInputElement>(null);
  if (!profile) return null;
  const today = todayIn(churchZone(profile));
  const lect = query.data?.date === lookupDate ? query.data : undefined;

  return (
    <section aria-label="Date & readings" className="grid gap-6">
      <ServiceDateField today={today} />
      <LectionaryStatus onEnterReadings={() => occasionRef.current?.focus()} />
      <OccasionField lect={lect} inputRef={occasionRef} />
      <ScriptureLinesField />
      <ReadingsList church={profile} />
    </section>
  );
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  1 passed (1)`, `Tests  22 passed (22)`; the suite ` Test Files  55 passed (55)`, `      Tests  342 passed (342)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `readings-step.tsx` and its test, `??` for the four new files.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/components/builder/readings/translation-select.tsx frontend/src/components/builder/readings/passage-text.tsx frontend/src/components/builder/readings/reading-row.tsx frontend/src/components/builder/readings/readings-list.tsx frontend/src/components/builder/readings/readings-step.tsx frontend/src/components/builder/readings/readings-step.test.tsx
git commit -m "Readings step: the readings with their passage text, and the translation (S UX item 6; AC16)" -m "Each line becomes a row with its testament badges and Show text. Only
open rows fetch, three at a time; a line over 200 characters is never
sent, and editing a line closes its row. Passage text shows every state
in the spec's table with its copy and Try again. The translation select
refetches open rows and stores only a choice that differs from the
church's; when the list fails it shows the church's translation. Frontend
335 -> 342 tests in 55 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 6 files changed; the push line.

**Review checkpoint (T9):** the reviewer checks that passage text renders as React text with `whitespace-pre-wrap` (no raw HTML), the precedence of the states against S's table, that a closed row sends nothing, that the Select uses `items` and no sentinel, and the 44 px toggles.

### Task 10: The bulletin readings (S UX item 7, Behavior change 15; spec decision 9; AC8 on screen)

"Bulletin readings" has an "Old Testament reading" select (options classified `ot`, `psalm` or `unknown`) and a "New Testament reading" select (`nt` only), from `pickerOptions` over the cleaned lines. No pick means automatic: the placeholder reads "Automatic: {ref}" from `effectivePicks` (the one `resolveReadings` rule the payload and, from 5a, the Word file use), or "None — choose one". A pick shows "Use automatic" (named "Use automatic Old Testament reading" or "… New Testament reading"), which clears it. A Psalm is never the automatic New Testament reading; with the Easter lines and the Old Testament pick "Psalm 118:1-2, 14-24", the automatic New Testament reading becomes "Acts 10:34-43".

**Files:**
- Create: `frontend/src/components/builder/readings/bulletin-readings-picker.tsx`
- Modify: `frontend/src/components/builder/readings/readings-step.tsx` (renders `BulletinReadingsPicker`)
- Test: `frontend/src/components/builder/readings/readings-step.test.tsx` (+3)

**Interfaces:**
- Consumes: `effectivePicks`, `setPick` (2b), `cleanLines`, `pickerOptions` (2b), `Select*`, `Label`, `Button`.
- Produces: `BulletinReadingsPicker()`.

Counts after this task: frontend **345 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder/readings/bulletin-readings-picker.tsx && echo "no T10 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T10 files yet`; `Test Files  55 passed (55)`, `Tests  342 passed (342)`.

- [ ] **Step 2 (agent): Write the failing tests**

Append to `frontend/src/components/builder/readings/readings-step.test.tsx`:

```tsx

// --- bulletin readings (S UX item 7; AC8 on screen) ----------------------------------

describe("bulletin readings (S UX item 7)", () => {
  it("offers only NT lines for NT, and the automatic NT is the epistle, never the Psalm", async () => {
    const { user } = renderStep({}, applyReadingSet(testDraft(), lectionary("2026-10-04"), 0));
    const ot = await screen.findByRole("combobox", { name: "Old Testament reading" });
    const nt = screen.getByRole("combobox", { name: "New Testament reading" });
    expect(ot).toHaveTextContent("Automatic: Isaiah 5:1-7");
    expect(nt).toHaveTextContent("Automatic: Philippians 3:4b-14");
    expect(screen.queryByRole("button", { name: /^Use automatic/ })).toBeNull();

    await user.click(nt);
    const options = await screen.findAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual(["Philippians 3:4b-14", "Matthew 21:33-46"]);
    await user.click(screen.getByRole("option", { name: "Matthew 21:33-46" }));
    await waitFor(() => expect(nt).toHaveTextContent("Matthew 21:33-46"));
    expect(probe()).toContain("/nt=Matthew 21:33-46/");
    expect(ot).toHaveTextContent("Automatic: Isaiah 5:1-7");
  });

  it("with the Easter lines, picking Psalm 118 as the OT makes the automatic NT Acts; Use automatic clears the pick", async () => {
    const { user } = renderStep({}, applyReadingSet(testDraft(), lectionary("2026-10-04"), 1));
    const ot = await screen.findByRole("combobox", { name: "Old Testament reading" });
    const nt = screen.getByRole("combobox", { name: "New Testament reading" });
    expect(ot).toHaveTextContent("Automatic: Acts 10:34-43");
    expect(nt).toHaveTextContent("Automatic: Colossians 3:1-4");

    await user.click(ot);
    await user.click(await screen.findByRole("option", { name: "Psalm 118:1-2, 14-24" }));
    await waitFor(() => expect(nt).toHaveTextContent("Automatic: Acts 10:34-43"));
    expect(ot).toHaveTextContent("Psalm 118:1-2, 14-24");
    expect(probe()).toContain("/ot=Psalm 118:1-2, 14-24/");

    await user.click(screen.getByRole("button", { name: "Use automatic Old Testament reading" }));
    await waitFor(() => expect(ot).toHaveTextContent("Automatic: Acts 10:34-43"));
    expect(nt).toHaveTextContent("Automatic: Colossians 3:1-4");
    expect(probe()).toContain("/ot=auto/");
  });

  it("says None — choose one when a side has no reading", async () => {
    renderStep({}, typedLines(["Isaiah 9:2-7", "Psalm 96"]));
    const nt = await screen.findByRole("combobox", { name: "New Testament reading" });
    expect(nt).toHaveTextContent("None — choose one");
    expect(screen.getByRole("combobox", { name: "Old Testament reading" })).toHaveTextContent("Automatic: Isaiah 9:2-7");
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × bulletin readings (S UX item 7) > offers only NT lines for NT, and the automatic NT is the epistle, never the Psalm <t>ms
   × bulletin readings (S UX item 7) > with the Easter lines, picking Psalm 118 as the OT makes the automatic NT Acts; Use automatic clears the pick <t>ms
   × bulletin readings (S UX item 7) > says None — choose one when a side has no reading <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 3 ⎯⎯⎯⎯⎯⎯⎯
      Tests  3 failed | 22 passed (25)
```

- [ ] **Step 4 (agent): Write the picker and show it**

Create `frontend/src/components/builder/readings/bulletin-readings-picker.tsx`:

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDraft } from "@/lib/draft/context";
import { effectivePicks, setPick } from "@/lib/draft/readings";
import { cleanLines, pickerOptions } from "@/lib/scripture-refs";

function PickSelect({
  side,
  label,
  options,
  pick,
  automatic,
}: {
  side: "ot" | "nt";
  label: string;
  options: string[];
  /** The explicit pick when it is still an option; "" means automatic. */
  pick: string;
  /** What automatic resolves to now, or null. */
  automatic: string | null;
}) {
  const { update } = useDraft();
  const id = `bulletin-${side}`;
  const items = Object.fromEntries(options.map((option) => [option, option]));
  return (
    <div className="grid gap-2">
      <Label id={`${id}-label`}>{label}</Label>
      <Select
        value={pick === "" ? null : pick}
        items={items}
        disabled={options.length === 0}
        onValueChange={(value) => {
          if (typeof value === "string") update((d) => setPick(d, side, value));
        }}
      >
        <SelectTrigger aria-labelledby={`${id}-label`} className="h-11 w-full min-w-0 data-[size=default]:h-11">
          <SelectValue placeholder={automatic ? `Automatic: ${automatic}` : "None — choose one"} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {pick !== "" ? (
        <div>
          <Button
            type="button"
            variant="link"
            className="h-11 px-0"
            aria-label={`Use automatic ${label}`}
            onClick={() => update((d) => setPick(d, side, ""))}
          >
            Use automatic
          </Button>
        </div>
      ) : null}
    </div>
  );
}

/**
 * "Bulletin readings" (S UX item 7): one Old Testament and one New Testament
 * reading. Options come from `pickerOptions` (OT: ot, psalm and unknown; NT:
 * nt only); "" is automatic, shown as "Automatic: {ref}" from the same
 * `resolveReadings` the payload and (from 5a) the Word file use, so a Psalm is
 * never the automatic NT and a stale pick counts as automatic.
 */
export function BulletinReadingsPicker() {
  const { draft } = useDraft();
  const options = pickerOptions(cleanLines(draft.readings.scriptures));
  const picks = effectivePicks(draft);
  return (
    <section aria-labelledby="bulletin-heading" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="bulletin-heading" className="text-base font-medium">
          Bulletin readings
        </h2>
        <p className="text-sm text-muted-foreground">
          The bulletin prints one Old Testament and one New Testament reading.
        </p>
      </div>
      <PickSelect
        side="ot"
        label="Old Testament reading"
        options={options.ot}
        pick={picks.otAuto ? "" : (picks.ot ?? "")}
        automatic={picks.otAuto ? picks.ot : null}
      />
      <PickSelect
        side="nt"
        label="New Testament reading"
        options={options.nt}
        pick={picks.ntAuto ? "" : (picks.nt ?? "")}
        automatic={picks.ntAuto ? picks.nt : null}
      />
    </section>
  );
}
```

Replace `frontend/src/components/builder/readings/readings-step.tsx` with:

```tsx
"use client";

import { useRef } from "react";

import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useChurch } from "@/lib/church-context";
import { todayIn } from "@/lib/dates";
import { churchZone } from "@/lib/draft/schema";
import { useChurchProfile } from "@/lib/queries/church";

import { BulletinReadingsPicker } from "./bulletin-readings-picker";
import { LectionaryStatus } from "./lectionary-status";
import { OccasionField } from "./occasion-field";
import { ReadingsList } from "./readings-list";
import { ScriptureLinesField } from "./scripture-lines-field";
import { ServiceDateField } from "./service-date-field";

/**
 * Step 1, Date & readings (S UX "Step 1"): the service date, the lectionary
 * status, the occasion and scripture lines, the readings with their text, and
 * the bulletin's two readings. The shell's `<LectionarySync>` does the lookup
 * and the automatic fill; this step shows them.
 */
export function ReadingsStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { lookupDate, query } = useLectionaryLookup();
  const occasionRef = useRef<HTMLInputElement>(null);
  if (!profile) return null;
  const today = todayIn(churchZone(profile));
  const lect = query.data?.date === lookupDate ? query.data : undefined;

  return (
    <section aria-label="Date & readings" className="grid gap-6">
      <ServiceDateField today={today} />
      <LectionaryStatus onEnterReadings={() => occasionRef.current?.focus()} />
      <OccasionField lect={lect} inputRef={occasionRef} />
      <ScriptureLinesField />
      <ReadingsList church={profile} />
      <BulletinReadingsPicker />
    </section>
  );
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/readings 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  1 passed (1)`, `Tests  25 passed (25)`; the suite ` Test Files  55 passed (55)`, `      Tests  345 passed (345)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for `readings-step.tsx` and its test, `?? frontend/src/components/builder/readings/bulletin-readings-picker.tsx`.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/components/builder/readings/bulletin-readings-picker.tsx frontend/src/components/builder/readings/readings-step.tsx frontend/src/components/builder/readings/readings-step.test.tsx
git commit -m "Readings step: the bulletin's Old and New Testament readings, never a Psalm as the automatic NT (S UX item 7; spec decision 9)" -m "The two selects offer the lines each side can hold, show Automatic: {ref}
from the same resolveReadings rule the payload uses (or None — choose
one), and Use automatic clears a pick. With the Easter lines, picking
Psalm 118 as the Old Testament reading makes Acts the automatic New
Testament reading. Frontend 342 -> 345 tests in 55 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 3 files changed; the push line.

**Review checkpoint (T10):** the reviewer checks that the placeholder comes from `effectivePicks` (never a second rule), that "no pick" is `null` plus a placeholder (no sentinel item, F §4.9.3), and that a stale pick shows as automatic.

### Task 11: Turn the step on: `"readings"` ships and its route renders the step (S steps.ts, Hand-offs "Builder shell", "Routes and files"; F §4.7; AC11, AC17; 2b build notes; clarification 18)

`SHIPPED_STEPS` gains `"readings"`, so 2b's shell (already built and tested behind it) shows Date & readings' status ("1 of 3", "Complete"), Review's "Still needed" rows and the summary's occasion and readings with their OT and NT marks. `/builder/readings` renders `ReadingsStep` instead of `StepPlaceholder`. Hymns, Liturgy and Review keep "Available soon" with no link. The shell tests change where the readings step is now real, answer `GET /translations`, and gain one test: the step turns "Complete" once the lectionary fills it.

**Files:**
- Modify: `frontend/src/lib/draft/steps.ts`, `frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx`, `frontend/src/components/builder/step-placeholder.tsx` (comment)
- Test: `frontend/src/lib/draft/status.test.ts` (two tests edited, 0 new), `frontend/src/components/builder/builder-shell.test.tsx` (+1, two tests edited)

**Interfaces:**
- Consumes: `ReadingsStep` (T6-T10), `SummaryPanel`, `StepProgress`, `StillNeeded` (2b, unchanged).
- Produces: `SHIPPED_STEPS = new Set(["readings"])`. Later users: slices 3, 4 and 5a add their steps (S Hand-offs).

Counts after this task: frontend **346 passed in 55 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>([]);`; `Test Files  55 passed (55)`, `Tests  345 passed (345)`.

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
    ('''  it("lists the four steps in order, ships none in 2b, and reads a step from its path", () => {''',
     '''  it("lists the four steps in order, ships Date & readings (2c), and reads a step from its path", () => {'''),
    ('''    expect([...SHIPPED_STEPS]).toEqual([]);''', '''    expect([...SHIPPED_STEPS]).toEqual(["readings"]);'''),
    ('''    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["soon", "soon", "soon", "not_in_archive"]);''',
     '''    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "soon", "soon", "not_in_archive"]);
    expect(stepStatus(d, "readings", new Set())).toEqual({ kind: "soon" });'''),
    ('''    expect(stillNeeded(fresh)).toEqual([]);''', '''    expect(stillNeeded(fresh, new Set())).toEqual([]);'''),
])

edit("frontend/src/components/builder/builder-shell.test.tsx", [
    ('import { church, churchProfile, DRAFT_NOW, lectionary, lectionaryRoute, me, testDraft, USER_ID } from "@/test/fixtures";',
     '''import {
  church,
  churchProfile,
  DRAFT_NOW,
  lectionary,
  lectionaryRoute,
  me,
  testDraft,
  translations,
  USER_ID,
} from "@/test/fixtures";'''),
    ('''function renderBuilder(page: ReactElement, path: string) {
  installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lectionaryRoute() });''',
     '''function renderBuilder(page: ReactElement, path: string, lookup = lectionaryRoute()) {
  installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lookup, "GET /translations": translations() });'''),
    ('''  it("renders each step route inside the shell: progress, the placeholder card and the footer links", async () => {''',
     '''  it("renders each step route inside the shell: progress, the step or its placeholder card, and the footer links", async () => {'''),
    ('''      expect(steps.map((link) => link.textContent)).toEqual([
        "1 Date & readings Soon",
        "2 Hymns Soon",''', '''      expect(steps.map((link) => link.textContent)).toEqual([
        "1 Date & readings 1 of 3", // shipped in 2c: a date, no occasion, no readings
        "2 Hymns Soon",'''),
    ('''      const card = screen.getByRole("region", { name: label });
      expect(within(card).getByRole("heading", { name: "Available soon" })).toBeInTheDocument();
      expect(within(card).getByText("Keep using the current app for this part.")).toBeInTheDocument();
      expect(within(card).queryByRole("link")).toBeNull(); // no link to the old app (owner answer Q2)
''', '''      const card = screen.getByRole("region", { name: label });
      if (number === 1) {
        // Date & readings is the real step from slice 2c.
        expect(within(card).getByLabelText("Service date")).toHaveValue("2026-10-04");
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else {
        expect(within(card).getByRole("heading", { name: "Available soon" })).toBeInTheDocument();
        expect(within(card).getByText("Keep using the current app for this part.")).toBeInTheDocument();
        expect(within(card).queryByRole("link")).toBeNull(); // no link to the old app (owner answer Q2)
      }
'''),
    ('''      expect(screen.queryByRole("heading", { name: "Still needed" })).toBeNull(); // nothing shipped yet
''', '''      // Review lists what the shipped step still needs; the other steps do not.
      if (number === 4) {
        const needed = screen.getByRole("region", { name: "Still needed" });
        expect(within(needed).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
          "No occasion — Add one",
          "No scripture readings — Add one",
        ]);
      } else {
        expect(screen.queryByRole("heading", { name: "Still needed" })).toBeNull();
      }
'''),
    ('''  it("shows the summary: the date, Available soon for the rest, and where the draft is kept", async () => {''',
     '''  it("shows the summary: the date and occasion, the readings, Available soon for the rest, and where the draft is kept", async () => {'''),
    ('''    expect(within(aside).getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    for (const block of ["Readings", "Hymns", "Liturgy"]) {''', '''    expect(within(aside).getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    expect(within(aside).getByText("No occasion yet")).toBeInTheDocument();
    const readings = within(aside).getByRole("link", { name: "Readings" }).closest("h3");
    expect(readings?.nextElementSibling).toHaveTextContent(/^No readings yet$/);
    for (const block of ["Hymns", "Liturgy"]) {'''),
    ('''    expect(within(aside).getByText("Draft saved on this device · Not in archive")).toBeInTheDocument();
    expect(within(aside).queryByText("No occasion yet")).toBeNull();
''', '''    expect(within(aside).getByText("Draft saved on this device · Not in archive")).toBeInTheDocument();
'''),
    ('''    installFakeApi({ "GET /church": async () => churchProfile(), "GET /lectionary/readings": lectionaryRoute() });''',
     '''    installFakeApi({
      "GET /church": async () => churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /translations": translations(),
    });'''),
    ('''describe("the shell once Date & readings ships (slice 2c turns this on)", () => {''',
     '''describe("the shell with Date & readings shipped (slice 2c)", () => {
  it("counts the step Complete once the lectionary fills it, and the summary shows the readings with their chips", async () => {
    renderBuilder(<ReadingsStepPage />, "/builder/readings", lectionaryRoute(lectionary));
    const progress = await screen.findByRole("navigation", { name: "Steps" });
    await waitFor(() =>
      expect(within(progress).getAllByRole("link")[0]).toHaveTextContent("1 Date & readings Complete"),
    );
    const aside = screen.getByRole("complementary", { name: "Summary" });
    expect(within(aside).getByText("Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    expect(within(aside).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "Isaiah 5:1-7OT (auto)",
      "Psalm 80:7-15",
      "Philippians 3:4b-14NT (auto)",
      "Matthew 21:33-46",
    ]);
  });
'''),
])
path = "frontend/src/components/builder/builder-shell.test.tsx"
text = Path(path).read_text(encoding="utf-8")
old = '''    installFakeApi({ "GET /church": churchProfile(), "GET /lectionary/readings": lectionaryRoute() });'''
assert text.count(old) == 2, text.count(old)
Path(path).write_text(
    text.replace(
        old,
        '''    installFakeApi({
      "GET /church": churchProfile(),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /translations": translations(),
    });''',
    ),
    encoding="utf-8",
)
print("T11 tests edited")
PYEOF
```

**Expected:** `T11 tests edited`.

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ +×|Tests ")
```

**Expected:**

```
   × steps (S steps.ts) > lists the four steps in order, ships Date & readings (2c), and reads a step from its path <t>ms
   × stepStatus (F §4.7) > shows Soon for unshipped steps and Not in archive for Review <t>ms
   × builder shell (F §4.7) > renders each step route inside the shell: progress, the step or its placeholder card, and the footer links <t>ms
   × builder shell (F §4.7) > shows the summary: the date and occasion, the readings, Available soon for the rest, and where the draft is kept <t>ms
   × the shell with Date & readings shipped (slice 2c) > counts the step Complete once the lectionary fills it, and the summary shows the readings with their chips <t>ms
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 5 ⎯⎯⎯⎯⎯⎯⎯
      Tests  5 failed | 12 passed (17)
```

- [ ] **Step 4 (agent): Ship the step**

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

edit("frontend/src/lib/draft/steps.ts", [
    (''' * `SHIPPED_STEPS` holds the steps whose content has shipped. An unshipped
 * step shows the "Available soon" card, the muted status "Soon" (Review: "Not
 * in archive"), and `stillNeeded` ignores it. Slice 2b ships none: owner
 * answer Q1 (2026-09-28) keeps Date & readings on the placeholder until 2c.
 * Slice 2c adds "readings", slice 3 "hymns", slice 4 "liturgy", 5a "review".''',
     ''' * `SHIPPED_STEPS` holds the steps whose content has shipped. An unshipped
 * step shows the "Available soon" card, the muted status "Soon" (Review: "Not
 * in archive"), and `stillNeeded` ignores it. Slice 2b shipped none (owner
 * answer Q1, 2026-09-28); slice 2c ships "readings". Slice 3 adds "hymns",
 * slice 4 "liturgy", 5a "review".'''),
    ('''export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>([]);''',
     '''export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);'''),
])

edit("frontend/src/components/builder/step-placeholder.tsx", [
    (''' * The card a step shows until its slice ships (S "Steps 2–4 (placeholders)";
 * F §4.7). Slice 2b also uses it for Date & readings (owner answer Q1,
 * 2026-09-28). Slices 2c, 3, 4 and 5a each replace their step's use, and 5a
 * deletes this component. No link to the old app (owner answer Q2).''',
     ''' * The card a step shows until its slice ships (S "Steps 2–4 (placeholders)";
 * F §4.7). Slice 2b also used it for Date & readings until slice 2c (owner
 * answer Q1, 2026-09-28). Slices 3, 4 and 5a each replace their step's use,
 * and 5a deletes this component. No link to the old app (owner answer Q2).'''),
])
print("T11 steps and placeholder edited")
PYEOF
```

**Expected:** `T11 steps and placeholder edited`.

Replace `frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx` with:

```tsx
"use client";

import { ReadingsStep } from "@/components/builder/readings/readings-step";

/** Step: Date & readings (slice 2c). */
export default function ReadingsStepPage() {
  return <ReadingsStep />;
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/components/builder 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  5 passed (5)`, `Tests  49 passed (49)` (8 status, 9 shell, 1 church switch, 6 sync, 25 step); the suite ` Test Files  55 passed (55)`, `      Tests  346 passed (346)`; `0`; `> tsc --noEmit` and `> eslint` with nothing after them; five ` M` files.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/lib/draft/steps.ts 'frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx' frontend/src/components/builder/step-placeholder.tsx frontend/src/lib/draft/status.test.ts frontend/src/components/builder/builder-shell.test.tsx
git commit -m "Builder: Date & readings ships; its route renders the step (F §4.7; S steps.ts; AC11, AC17)" -m "SHIPPED_STEPS holds \"readings\", so the step bar counts it (1 of 3,
Complete), Review lists what it still needs and the summary shows the
occasion and the readings with their OT and NT marks. /builder/readings
renders the Date & readings step. Hymns, Liturgy and Review keep the
Available soon card with no link. Frontend 345 -> 346 tests in 55 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 5 files changed; the push line.

**Review checkpoint (T11):** the reviewer checks that only `"readings"` is shipped, that the three other steps still show the card with no link, and that the shell tests assert the new Review rows and summary blocks rather than deleting the old checks.

### Task 12: Docs: the "(2c plan)" notes in S, one F amendment row, the slice 2 checklist and its heading pin (S top, UX items 1, 2, 4, 6, Frontend changes, Testing, Manual checks, open question 2; F Amendments, §4.7; owner answers Q1-Q3; clarifications 1-3, 8-10, 13, 19)

S and F are what slices 3, 4 and 5a will read, so they must say what 2c built. S gains eleven "(2c plan)" notes (plus the marker sentence at the top); F gains one amendment row and a note in §4.7. `docs/manual-verification.md` gains "## Slice 2" (S's thirteen checks, a Saturday in check 2, check 14 for "New service", and "(owner, after 2c)" on the items the guided check covers), and `backend/tests/test_slice1_docs.py`, which pinned the file's last two `##` headings, pins the last three. No code changes.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`
- Test: none new; `backend/tests/test_ops_workflows.py`, `test_slice1_docs.py` and `test_docs.py` must still pass (89).

**Interfaces:**
- Consumes: the clarifications above and the code of T1-T11.
- Produces: S and F as slices 3, 4 and 5a will read them; the checklist T14 runs from.

Counts after this task: frontend **346 passed in 55 files**; backend **971 passed, 9 skipped**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "(2c plan" docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
grep -c "^## Slice 2$" docs/manual-verification.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); `0` (grep exits 1); `89 passed in <t>s`.

- [ ] **Step 2 (agent): Apply the S, F and docs-test edits**

Each anchor must match exactly once, or the script stops before writing anything for that file. Run this edit script from the repo root:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path

S = Path("docs/superpowers/specs/2026-09-25-slice-2-readings-design.md")
F = Path("docs/superpowers/specs/2026-09-25-migration-foundations-design.md")
T1DOCS = Path("backend/tests/test_slice1_docs.py")


def edit(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


edit(S, [
    ('Corrections made during the 2b build (2026-09-29) are marked "(2b build)".\n',
     'Corrections made during the 2b build (2026-09-29) are marked "(2b build)". Corrections made while planning 2c '
     '(`docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md`, 2026-09-29) are marked "(2c plan)".\n'),
    ('   - When the date is not the next Sunday, a text button: **"Use next Sunday (October 4)"**.\n',
     '   - When the date is not the next Sunday, a text button: **"Use next Sunday (October 4)"**. (2c plan: it puts '
     'back the default date with `date_origin: "default"`, so it is not counted as the user\'s choice; owner answer '
     'Q2, 2026-09-29.)\n'),
    ("and a **\"Try again\"** button, which refetches.\n",
     "and a **\"Try again\"** button, which refetches. (2c plan: every failure other than a 429 shows it, and an "
     "answer already on screen wins over a failed background refetch.)\n"),
    ("then refetches. The fields are untouched and manual entry keeps working.\n",
     "then refetches. The fields are untouched and manual entry keeps working. (2c plan: N is the `Retry-After` "
     "value as sent; it does not count down.)\n"),
    ('     | `user`, with a reading set for this date | "Edited from the lectionary ({set name})" |\n',
     '     | `user`, with a reading set for this date | "Edited from the lectionary ({set name})" (2c plan: '
     '"Edited from the lectionary" while that date\'s lookup is not loaded) |\n'),
    ('or **?** with the tooltip "Book not recognized". A line',
     'or **?** with the tooltip "Book not recognized" (2c plan: phones do not open tooltips, so "Book not '
     'recognized" is also the badge\'s accessible name). A line'),
    ("`radio-group`, `collapsible` and `tooltip` are 2c's.)",
     "`radio-group`, `collapsible` and `tooltip` are 2c's.) (2c plan: the registry is still unreachable, so 2c "
     "rebuilds `radio-group`, `collapsible` and `tooltip` from the upstream source the same way.)"),
    ("returning `d` unchanged is a no-op.\n",
     "returning `d` unchanged is a no-op. (2c plan: only the tab on screen fills (`document.visibilityState === "
     "\"visible\"`); a hidden tab fills when it is shown, because a tab that adopts another tab's newer draft drops "
     "up to 400 ms of its own typing (2b build notes). A tab shown again first re-reads the stored draft and adopts it "
     "when newer (`DraftStore.syncFromStorage()`), so it never fills over typing another tab wrote as it was hidden. The hook lives in `components/builder/lectionary-sync.tsx`, "
     "and `<LectionarySync>` shares its lookup with the step.)\n"),
    ("    - readings: `fields_origin` is `empty` or `lectionary`; both picks `\"\"`;\n",
     "    - readings: `fields_origin` is `empty` or `lectionary`; both picks `\"\"`; (2c plan, owner answer Q2, "
     "2026-09-29: also `date_origin !== \"user\"` and `translation === null`. Choosing a set in the switcher makes a "
     "`default` date the user's (`chooseReadingSet`), so \"New service\" asks after a picked date, a chosen reading "
     "set or a translation, and the mount-time roll-forward keeps such a draft's date.)\n"),
    ("| `lib/use-debounced-value.test.ts` |",
     "| `lib/use-debounced-value.test.ts` (2c plan: `.test.tsx`, since it renders the hook in jsdom) |"),
    ("its after-merge look is the owner's short check in the 2b plan's Task 13.)\n",
     "its after-merge look is the owner's short check in the 2b plan's Task 13.) (2c plan: appended as "
     "\"## Slice 2\", with a Saturday added to check 2 and a check 14 for \"New service\"; `test_slice1_docs.py` "
     "now pins the last three `##` headings. The owner's guided check after the merge runs the items marked "
     "\"(owner, after 2c)\".)\n"),
    ("The default is no; it can be added later without changing the draft shape.\n",
     "The default is no; it can be added later without changing the draft shape. (2c plan: **closed: no**, owner "
     "answer Q1, 2026-09-29. A Saturday falls back to manual entry like any date without readings.)\n"),
])

edit(F, [
    ("a failed write is retried on the next flush. | 2b |\n",
     "a failed write is retried on the next flush. | 2b |\n"
     "| §4.6, §4.7, §4.8 | *(2026-09-29, slice 2c plan)* `isPristine` also counts a date the user picked, a reading "
     "set chosen in the switcher (which makes a default date the user's) and a translation override (owner answer "
     "Q2), so \"New service\" asks after them and the roll-forward keeps their date. The lectionary fills only in the "
     "tab on screen, and a tab shown again first re-reads the stored draft and adopts it when newer. Date & readings ships (`SHIPPED_STEPS` holds \"readings\"). `ErrorState` takes a screen's own "
     "`message`, `retryLabel` and `retryDisabled`, and `ConfirmDialog` a `cancelLabel`, for the slice spec's \"Try "
     "again\" and \"Keep mine\". | 2c |\n"),
    ("*(2026-09-28, slice 2b plan: step 1 too, until slice 2c.)*",
     "*(2026-09-28, slice 2b plan: step 1 too, until slice 2c.)* *(2026-09-29, slice 2c plan: step 1 ships in 2c.)*"),
])

edit(T1DOCS, [
    ('    assert re.findall(r"^## .+$", text, re.MULTILINE)[-2:] == ["## Ops slice", "## Slice 1"]\n',
     '    # Slice 2c appends "## Slice 2" after this section (slice 2 spec, Manual checks).\n'
     '    assert re.findall(r"^## .+$", text, re.MULTILINE)[-3:] == ["## Ops slice", "## Slice 1", "## Slice 2"]\n'),
])
print("docs edited")
PYEOF
```

**Expected:** `docs edited`. An `AssertionError` names the anchor that moved: read that part of the file, fix the anchor in this step (not the file's other text), and run the step again from a clean file (`git checkout -- <file>`).

- [ ] **Step 3 (agent): Append the slice 2 checklist**

Append to `docs/manual-verification.md`:

```markdown

## Slice 2

Run on the production URLs: https://worship-service-builder.vercel.app (at
375 px in Chrome device mode, iPhone SE, and on desktop) and
https://liturgy-frozen.streamlit.app, the production Streamlit app. These are
the slice 2 spec's manual checks 1-13 (slice 2 spec → Manual checks), with a
Saturday added to check 2 (owner answer Q1, 2026-09-29: no one-tap Sunday
readings) and check 14 for "New service" (owner answer Q2). After the 2c merge
the owner's guided check, one step at a time (owner answer Q3), covers the
items marked "(owner, after 2c)", some of them in part; its result goes into
`docs/ops-runbook.md` → "Slice 2c record", which says what ran. The rest can
be run at any time and recorded the same way. Reading texts and dates come from the live
lectionary and Bible sites, so record what the page shows, never an email
address or a church id.

- [ ] (owner, after 2c) **1.** A church with no draft on this device opens `/` → `/builder/readings`, dated next Sunday in the church's time zone, with the occasion and readings filled and the step bar showing Date & readings as Complete.
- [ ] (owner, after 2c) **2.** Change the date to a plain Tuesday: "No lectionary readings for …" with **Enter readings**, plus the note "These readings are from … not …" with **Clear readings**; focus stays on the date. A Saturday (for example 2026-10-10) also falls back to manual entry. Ash Wednesday 2027 (2027-02-10) shows "Ash Wednesday"; Good Friday 2027 (2027-03-26) finds readings; Thanksgiving (2026-11-26) shows four lines.
- [ ] (owner, after 2c) **3.** Palm Sunday 2027 (2027-03-21): two set cards under "This date has more than one set of readings", with the Passion set selected; tapping the Palms card changes the readings.
- [ ] (owner, after 2c) **4.** Type an occasion or a reading of your own: the caption reads "Entered by you" or "Edited from the lectionary (…)". Change the date: "Readings for … are available." appears; **Use them** asks "Replace your readings?" first. On a date whose readings filled themselves, delete the Psalm line: no banner.
- [ ] **5.** Easter Day 2026 (2026-04-05): choose the Easter Vigil set: 11 lines, no heading lines, no "too long" message; **Show text** on "Romans 6:3-11 and Psalm 114" loads both passages.
- [ ] **6.** On desktop, type a date digit by digit: one lookup in DevTools → Network, and focus never jumps to Occasion.
- [ ] **7.** Refresh on every step: the draft is kept. A second tab edits: the first tab shows "Updated from another tab." Switch church and back: the drafts are separate.
- [ ] (owner, after 2c) **8.** **Show text** on "Isaiah 50:4-9a": the text loads. Switch **Bible translation**: the text changes. ESV is offered (production has the key).
- [ ] (owner, after 2c) **9.** Bulletin readings: the automatic New Testament reading is the epistle, never the Psalm. With Easter-season lines, the automatic Old Testament reading is the first line (Acts) and the New Testament one the epistle; pick the Psalm as the Old Testament reading and the New Testament one becomes Acts; **Use automatic** undoes it. Edit a picked line and leave the field: the pick goes back to automatic. Edit a picked line and refresh without leaving the field: after the reload the pick is automatic.
- [ ] **10.** Go to Hymns, then open `/builder`: it lands on Hymns. With a second tab open, moving between steps in one tab shows no "Updated from another tab." in the other.
- [ ] **11.** With the network off (DevTools offline) on a new date: "The lectionary couldn't be reached. …" with **Try again**; back online, **Try again** recovers.
- [ ] (owner, after 2c) **12.** At 375 px: no sideways scroll; the footer stays at the bottom above the home indicator; inputs do not zoom on iOS. On desktop: the summary sits in the right column with the readings and their OT and NT marks.
- [ ] **13.** Regression: sign in, switch church, open the Builder nav item; the Streamlit smoke check on https://liturgy-frozen.streamlit.app (F §6.3).
- [ ] (owner, after 2c) **14.** After picking a date, choosing a reading set or choosing a translation, **New service** asks "Start a new service?"; on an untouched draft it starts over at once.
```

- [ ] **Step 4 (agent): Check the result**

```bash
grep -c "(2c plan" docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
grep -c "slice 2c plan" docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -cE "^- \[ \] (\(owner, after 2c\) )?\*\*[0-9]+\.\*\*" docs/manual-verification.md
grep -c "^- \[ \] (owner, after 2c) " docs/manual-verification.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git diff -U0 docs backend | grep '^+' | grep -v '^+++' | grep -c '—'
git diff --stat
```

**Expected:** `12`; `2`; `14` (slice 2's fourteen numbered checks; slice 1's carry an "(after 1a)" or "(after 1b)" marker, so the pattern skips them); `8`; `89 passed in <t>s`; `971 passed, 9 skipped in <t>s`; `2` (the only em dashes on added lines are S's existing copy "Too many requests — try again in N s." on the line that gains a note, and F §4.7's existing "Available soon — keep using the current app for this part"; the new prose has none); four files changed.

- [ ] **Step 5 (agent): Commit and back up**

```bash
git add docs/superpowers/specs/2026-09-25-slice-2-readings-design.md docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -m "Docs: slice 2c notes in S and F, and the slice 2 manual checklist (S Manual checks; F §4.6-§4.8)" -m "Marks \"(2c plan)\" in the slice 2 spec where 2c built something more
precisely than written: Use next Sunday keeps the default date, the
lectionary's failure and rate-limit copy, the caption before the lookup
loads, the ? badge on phones, the rebuilt Base UI components, the visible-
tab fill, what isPristine counts (owner answer Q2), the debounce test's
name, the checklist, and open question 2 closed as no (owner answer Q1).
F gains an amendment row and a §4.7 note. docs/manual-verification.md
gains \"## Slice 2\", and test_slice1_docs.py pins its last three headings.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T12):** every S note says "(2c plan)" and matches the code; nothing else in S or F changed; the checklist items read as the owner will run them; `git show --stat HEAD` lists the four files only.

### Task 13: Whole-branch verification and the slice 2c pull request (owner's yes before the PR is opened and before it is marked ready) (S Testing "Frontend", AC14-AC17; F §4.1, §4.3, §4.8, §4.9, §4.10, §5.2, §5.4; owner decisions 3, 4; owner answer Q4; clarifications 4, 20)

The whole branch is checked in one place before anyone reviews it: the frontend suite three times and twice more with the clock moved forward (so a clock- or timing-dependent test shows up here and not in CI), types, lint, the production build and its routes, the backend suite (unchanged), the generated API files (unchanged), the gates (client components, no link to the old app, no `apiFetch` in components, storage only through `lib/storage.ts`, no raw HTML, `SHIPPED_STEPS` holding `"readings"` only, no Python change but the docs test), the exact list of changed paths, and the exact list of commits against this plan. The branch is already on GitHub from the backup pushes (owner answer Q4), but no PR exists; on the owner's first yes the agent opens it as a **draft**, so CI runs. When CI is green, the agent reports and, on the owner's second yes, marks it ready. Merging is Task 14, with its own yes.

Below, `<scratch>` is the absolute path of the session's scratchpad directory, and `<N>` is the PR number Step 10 prints; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never run a bare `git push` or `--force`.

**Files:** none changed. A local or CI failure is fixed in its owning task's files (Step 14).

**Interfaces:**
- Consumes: everything from T1-T12, in particular each task's commit subject (Step 8 reads them from this plan between `### Task 1:` and `### Task 13:`), the cumulative counts (302, 309, 312, 314, 320, 325, 330, 335, 342, 345, 346, 346 after T1-T12), `SHIPPED_STEPS` (T11), and CI (`.github/workflows/ci.yml`, unchanged: `backend`, `backend-postgres`, `frontend` with lint, typecheck, `API types match the OpenAPI snapshot (F §5.4)`, test and build).
- Produces: PR `<N>` (`claude/slice-2-plan-4q33le` → `main`), titled `Slice 2c: the Date & readings step`, not a draft after Step 13, CI green on the branch head, its body holding the line `Tests: frontend 299 → 346 in 49 → 55 files; backend 971 → 971 passed, 9 → 9 skipped` and ending with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Later user: T14.

- [ ] **Step 1 (agent): Bring the branch up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD | tail -1
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected,** in order: nothing (or `?? .claude/`); the fetch prints nothing or only updated refs; `0`; `0f6fcbc Merge pull request #23 from bbrown62450/claude/slice-2-plan-4q33le` (or a later merge the owner made); the branch's oldest commit, `<sha> Plan: slice 2c Date & readings step (S slice 2; owner answers 2026-09-29)`; `0` (every commit was backed up).
- If the first count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 13)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. On a conflict, run `git merge --abort`, stop and tell the owner which files conflict. Without one, continue: Steps 2-8 run on the merged tree, and any new tests the merge brought change the totals by exactly those (name them in the Step 9 message).
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

**Expected:** three times ` Test Files  55 passed (55)` and `      Tests  346 passed (346)` (baseline 299 in 49; after T1-T12: 302, 309, 312, 314, 320, 325, 330, 335, 342, 345, 346, 346) and no `FAIL`; then `clock +8 days` and `clock +400 days`, each followed by the same two lines and no `FAIL` (+8 days is past Sunday, October 4, 2026, the test drafts' date; +400 days is past a year end); `0`; `> tsc --noEmit` and `> eslint` with nothing after. Any other number: find the task whose count drifted. A run that fails even once is a failure (Step 14): make the test deterministic (fake only `Date`, set to `DRAFT_NOW`; await the UI with `findBy`/`waitFor`) rather than retrying it.

- [ ] **Step 3 (agent): Run the backend suite and the Postgres marker count**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
```

**Expected:** `971 passed, 9 skipped in <t>s` (unchanged: T12 edits one assertion in a docs test); `9 skipped, 971 deselected in <t>s`.

- [ ] **Step 4 (agent): Build the frontend with CI's placeholder environment**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder")
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

**Expected:** `✓ Compiled successfully in <t>s`, the route table's five builder lines (`├ ○ /builder`, `├ ○ /builder/hymns`, `├ ○ /builder/liturgy`, `├ ○ /builder/readings`, `├ ○ /builder/review`) and no `Error` line; then exactly:

```
/ /_global-error /_not-found /auth/callback /builder /builder/hymns /builder/liturgy /builder/readings /builder/review /favicon.ico /join /login /welcome
```

(2c adds no route.) The build must run in the real checkout: Turbopack refuses a symlinked `node_modules`. If it fails only with `Failed to fetch` for a Geist font (no network), say so in the Step 9 message and rely on CI's `frontend` job.

- [ ] **Step 5 (agent): Check the generated API files did not change**

```bash
(cd frontend && npm run gen:api >/dev/null) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
git diff --name-only origin/main...HEAD -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | wc -l
git status --short
```

**Expected:** `schema diff exit 0`; `0` (2c changes no API; clarification 20); nothing (or `?? .claude/`).

- [ ] **Step 6 (agent): Run the gates**

```bash
find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) -exec sh -c 'head -1 "$1" | grep -qx "\"use client\";" || echo "not a client component: $1"' _ {} \; ; echo "client components checked: $(find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) | wc -l)"
grep -rniE "streamlit|liturgy-frozen" frontend/src --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "old app grep exit $?"
grep -rn "apiFetch" frontend/src/components frontend/src/app --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "apiFetch in UI grep exit $?"
grep -rnE "window\.(local|session)Storage|(local|session)Storage\.(getItem|setItem|removeItem|key|clear)" frontend/src --include=*.ts --include=*.tsx | grep -vE "^frontend/src/lib/storage\.ts:|\.test\.tsx?:|^frontend/src/test/"; echo "storage grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
grep -rn "Available soon" frontend/src --include=*.tsx | grep -v "\.test\.tsx:" | wc -l
git diff --name-only origin/main...HEAD -- '*.py' backend/requirements.txt requirements-dev.txt backend/migrations .github frontend/package.json frontend/package-lock.json docs/ops-runbook.md
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -qx 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected,** in order:
- `client components checked: 10` with no "not a client component" line before it (F §4.1; 2c adds no page file, it replaces the readings page's body);
- `old app grep exit 1` (no link to or mention of the old app in the shipped code; 2b owner answer Q2);
- `apiFetch in UI grep exit 1` (components use the query hooks, F §4.4);
- `storage grep exit 1` (F §4.3);
- `raw html grep exit 1`;
- `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);`;
- `2` (`wc` pads it; the "Available soon" copy lives in `step-placeholder.tsx` and `summary-panel.tsx` only, now for Hymns, Liturgy and Review);
- exactly `backend/tests/test_slice1_docs.py` (the only Python change, T12; no requirement, migration, workflow, package or runbook change);
- only `trailer check done`.

Any other output: stop, find the owning task (Step 14) and fix it there. A grep hit may be a false positive (a comment): read the line, and if it is harmless, say why in the Step 9 message rather than bending the code to silence it.

- [ ] **Step 7 (agent): Check the exact list of changed paths**

```bash
LC_ALL=C sort > "<scratch>/slice2c-expected-paths.txt" <<'EOF'
backend/tests/test_slice1_docs.py
docs/manual-verification.md
docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx
frontend/src/components/app/confirm-dialog.test.tsx
frontend/src/components/app/confirm-dialog.tsx
frontend/src/components/app/error-state.test.tsx
frontend/src/components/app/error-state.tsx
frontend/src/components/builder/builder-shell.test.tsx
frontend/src/components/builder/builder-shell.tsx
frontend/src/components/builder/church-switch.test.tsx
frontend/src/components/builder/lectionary-sync.test.tsx
frontend/src/components/builder/lectionary-sync.tsx
frontend/src/components/builder/readings/bulletin-readings-picker.tsx
frontend/src/components/builder/readings/lectionary-status.tsx
frontend/src/components/builder/readings/occasion-field.tsx
frontend/src/components/builder/readings/passage-text.tsx
frontend/src/components/builder/readings/reading-row.tsx
frontend/src/components/builder/readings/reading-set-picker.tsx
frontend/src/components/builder/readings/readings-list.tsx
frontend/src/components/builder/readings/readings-step.test.tsx
frontend/src/components/builder/readings/readings-step.tsx
frontend/src/components/builder/readings/replace-readings-dialog.tsx
frontend/src/components/builder/readings/scripture-lines-field.tsx
frontend/src/components/builder/readings/service-date-field.tsx
frontend/src/components/builder/readings/translation-select.tsx
frontend/src/components/builder/readings/use-wait-over.ts
frontend/src/components/builder/step-placeholder.tsx
frontend/src/components/ui/collapsible.tsx
frontend/src/components/ui/radio-group.tsx
frontend/src/components/ui/tooltip.tsx
frontend/src/lib/api/timeouts.ts
frontend/src/lib/api/types.ts
frontend/src/lib/draft/context.tsx
frontend/src/lib/draft/readings.test.ts
frontend/src/lib/draft/readings.ts
frontend/src/lib/draft/status.test.ts
frontend/src/lib/draft/status.ts
frontend/src/lib/draft/steps.ts
frontend/src/lib/draft/store.test.ts
frontend/src/lib/draft/store.ts
frontend/src/lib/queries/lectionary.test.tsx
frontend/src/lib/queries/lectionary.ts
frontend/src/lib/queries/passages.test.ts
frontend/src/lib/queries/passages.ts
frontend/src/lib/queries/reference.test.tsx
frontend/src/lib/queries/reference.ts
frontend/src/lib/use-debounced-value.test.tsx
frontend/src/lib/use-debounced-value.ts
frontend/src/test/fixtures/index.ts
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice2c-actual-paths.txt"
wc -l < "<scratch>/slice2c-expected-paths.txt"
wc -l < "<scratch>/slice2c-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice2c-expected-paths.txt" "<scratch>/slice2c-actual-paths.txt"
git diff --name-status --no-renames origin/main...HEAD | cut -c1 | sort | uniq -c
```

**Expected:** `52`; `52`; `comm` prints nothing; then `  28 A` and `  24 M`. These are the File Structure's paths: 28 created (the plan and 27 frontend files) and 24 modified (19 frontend files, the two specs, the checklist and the docs test). An indented `comm` line (changed, not listed) means a task touched a file its **Files:** does not name: find it with `git log --format='%h %s' origin/main..HEAD -- '<path>'`; anything under `backend/` other than `tests/test_slice1_docs.py`, `frontend/src/lib/api/openapi.json`, `schema.d.ts`, `package*.json` or `.github/` is a stop. An unindented line means a task's commit is missing.

- [ ] **Step 8 (agent): Check the exact list of commits against this plan**

```bash
.venv/bin/python - docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md > "<scratch>/slice2c-plan-subjects.txt" <<'EOF'
import pathlib, re, sys
text = "\n" + pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
lines = text.split("\n### Task 1:", 1)[1].split("\n### Task 13:", 1)[0].splitlines()
print("Plan: slice 2c Date & readings step (S slice 2; owner answers 2026-09-29)")
for line in lines:
    m = re.match(r'\s*git commit -m "((?:[^"\\]|\\.)*)"', line)
    if m:
        print(re.sub(r"\\(.)", r"\1", m.group(1)))
EOF
git log --reverse --no-merges --format=%s origin/main..HEAD > "<scratch>/slice2c-branch-subjects.txt"
wc -l < "<scratch>/slice2c-plan-subjects.txt"
diff "<scratch>/slice2c-plan-subjects.txt" "<scratch>/slice2c-branch-subjects.txt"; echo "commit list diff exit $?"
git log --reverse --format='%h %s' origin/main..HEAD
```

**Expected:** `13` (the plan, then one commit for each of T1-T12); `commit list diff exit 0` with no output before it; the thirteen commits oldest first (plus a Step 1 merge, if any), from `<sha> Plan: slice 2c Date & readings step (S slice 2; owner answers 2026-09-29)` to `<sha> Docs: slice 2c notes in S and F, and the slice 2 manual checklist (S Manual checks; F §4.6-§4.8)`. A `diff` line is a failure unless it is a `>` line `Fix: … (Task <n> review)` (a review fix, Global Constraints), `Fix: … (Task <n>, slice 2c final verification)` (Step 14) or `Plan: …` (a plan correction the controller committed), each named in the Step 9 message; then the first count differs from the branch's by exactly those lines.

- [ ] **Step 9 (agent → OWNER): Ask for the go-ahead to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
git rev-list --count origin/main..HEAD
```

**Expected:** one `✓ Logged in to github.com account <login> (keyring)` line; `[]` (no open PR from this branch; PRs #22 and #23 are merged); the Step 8 count (13, plus a merge or fixes). If `gh` is not logged in, ask the owner to run `gh auth login`. If an open PR exists, stop and ask.

Send the owner exactly this, with `<count>` filled in, and wait for a clear yes:

> Slice 2c is verified locally: frontend 346 tests in 55 files, passing three runs in a row and with the clock moved 8 and 400 days ahead (299 in 49 before); typecheck, lint and the production build are clean; the backend is unchanged at 971 passed, 9 skipped (one docs test now expects the new "Slice 2" checklist heading); the API types did not change; the checks are clean (every page is a client component, no link to the old app, the screens use the query hooks, the draft goes through the storage helper only, only Date & readings is switched on); changed files (52) and commits (<count>) are as planned, and every commit is already backed up on the branch. May I open the pull request as a **draft** titled "Slice 2c: the Date & readings step", so the checks run? I will come back with the results and ask again before marking it ready. Merging stays with you (Task 14).

Add one line per note from Steps 1-8 (a merge from `main`, a skipped font download, a `Fix:` commit, how the three Base UI components were made). A no leaves the branch as it is.

- [ ] **Step 10 (agent, on the owner's yes): Write the PR body and open the draft PR**

```bash
cat > "<scratch>/slice2c-pr-body.md" <<'EOF'
PR 2c of slice 2: the Date & readings step. After it merges, a signed-in member lands on step 1 with next Sunday's occasion and lectionary readings already filled in. Spec: docs/superpowers/specs/2026-09-25-slice-2-readings-design.md (2c). Plan: docs/superpowers/plans/2026-09-29-slice-2c-readings-step.md. No backend change (one docs test pins the new checklist heading), no migration, no API change.

The step
- Service date: any date; the long date; "Use next Sunday"; a passed date, a weekday and an out-of-range year are noted. The lectionary is looked up 400 ms after the date settles (one lookup when a date is typed digit by digit) and never moves focus.
- What the lectionary said: loading (and "Still working" after 8 s), several sets as cards (keyed by index), no readings with "Enter readings", unavailable and rate limited with "Try again", the partial note, and lectionary readings from another date kept with "Clear readings".
- Typed readings are never overwritten: a new date's readings are offered by a banner, and replacing typed or archived readings always asks "Replace your readings?".
- Occasion and scripture lines with their limits and origin caption; the readings list with testament badges and passage text on demand (three requests at a time), in a chosen translation; the bulletin's Old and New Testament readings, where a Psalm is never the automatic New Testament reading.
- The step bar, Review's "Still needed" and the summary now include Date & readings. Hymns, Liturgy and Review keep "Available soon" with no link.

Owner answers (2026-09-29): no Saturday one-tap (Q1); "New service" asks after a picked date, a chosen reading set or a chosen translation (Q2); a guided phone check after the merge (Q3). The lectionary fills only in the tab on screen (2b build notes). @@COMPONENTS_LINE@@

Tests: frontend 299 → 346 in 49 → 55 files; backend 971 → 971 passed, 9 → 9 skipped

After merge (Task 14): a guided check on the owner's phone (about six steps) and a quick look on a computer, then a short "Slice 2c record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

Replace `@@COMPONENTS_LINE@@` with `The radio group, collapsible and tooltip are generated from the base-nova registry.` or `The radio group, collapsible and tooltip are rebuilt from the upstream shadcn source (base-nova, pinned commit), because the build container cannot reach the registry (plan clarification 4).` (T4's commit body says which), then:

```bash
grep -c '@@COMPONENTS_LINE@@' "<scratch>/slice2c-pr-body.md"
grep -cx 'Tests: frontend 299 → 346 in 49 → 55 files; backend 971 → 971 passed, 9 → 9 skipped' "<scratch>/slice2c-pr-body.md"
git fetch origin && test "$(git rev-list --count HEAD..origin/main)" = 0 && test "$(git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD)" = 0 && echo "branch is current and backed up"
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 2c: the Date & readings step" \
  --body-file "<scratch>/slice2c-pr-body.md"
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

**Expected:** `run <id>`; `backend: success`, `backend-postgres: success`, `frontend: success`; frontend `Test Files  55 passed (55)`, `Tests  346 passed (346)`, `✓ Compiled successfully` and the five `/builder` route lines; backend `971 passed, 9 skipped in …s`; backend-postgres `pg_smoke: OK` and `9 passed, 971 deselected, 1 warning in …s`. If a required job failed on or after 2026-10-19, first check the runner image (`Image: ubuntu-24.04` expected; GitHub moves `ubuntu-latest` then) and report a setup failure on a new image to the owner before changing any 2c file.

- [ ] **Step 13 (agent → OWNER): Report CI and ask to mark the PR ready**

Send exactly this, with the values filled in, and wait for a clear yes:

> PR #<N> (<url>) is green (run <run id>): frontend 346 tests in 55 files, build OK; backend 971 passed, 9 skipped; the Postgres job clean; the Vercel preview built. May I mark it ready for review? Merging stays with you (Task 14).

On the yes:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft,state --jq '"draft=\(.isDraft) \(.state)"'
```

**Expected:** `✓ Pull request bbrown62450/church#<N> is marked as "ready for review"`, then `draft=false OPEN`. Tell the owner in one line: "PR #<N> is ready for review. Next: Task 14, the merge on your yes, then a guided check on your phone, one step at a time."

- [ ] **Step 14 (agent): Fix any failure in its owning task**

Read the failure (for CI: `gh run view <run-id> -R bbrown62450/church --log-failed | tail -80`), reproduce it locally, and fix it in the task that owns it:

| Failing check or test | Owning task |
|---|---|
| `draft/readings.test.ts`, `draft/status.test.ts` (the `isPristine` cases), `draft/store.test.ts` | T1 |
| `use-debounced-value.test.tsx`, `queries/lectionary.test.tsx`, `queries/reference.test.tsx`, `timeouts.ts`, the `translations()` fixture | T2 |
| `queries/passages.test.ts`, `lib/api/types.ts` | T3 |
| `error-state.test.tsx`, `confirm-dialog.test.tsx`, `radio-group.tsx`/`collapsible.tsx`/`tooltip.tsx` lint or types | T4 |
| `lectionary-sync.test.tsx`, the lookup answers in `builder-shell.test.tsx` or `church-switch.test.tsx`, the `noReadings`/`lectionaryRoute` fixtures | T5 |
| `readings-step.test.tsx` "service date" and "occasion and scripture lines" blocks | T6 |
| its "lectionary status" block | T7 |
| its "reading sets and the available banner" block | T8 |
| its "readings list and passage text" block | T9 |
| its "bulletin readings" block | T10 |
| `status.test.ts` (steps and stepStatus), `builder-shell.test.tsx` (routes, summary, the new test), the `SHIPPED_STEPS` gate, the readings route in the build | T11 |
| the spec or F text, `docs/manual-verification.md`, `test_slice1_docs.py` | T12 |
| a flaky run in Step 2, or a failure only with the clock moved | the task owning the test: fake only `Date` (set to `DRAFT_NOW`) for the calendar, await the UI with `findBy`/`waitFor`, never sleep in place of a condition |
| any other existing test, the backend suite, the Vercel preview only | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-8; commit with the subject `Fix: <what> (Task <n>, slice 2c final verification)` and the trailer; have that task re-reviewed; push with `git push origin claude/slice-2-plan-4q33le` (a backup before Step 10; after it, covered by the owner's first yes); after Step 10, repeat Steps 11-12 and send Step 13's message with the new run. An infrastructure failure with no test output gets one `gh run rerun <run-id> -R bbrown62450/church --failed` first.

Expected counts after this task: frontend `346 passed` in 55 files (CI the same); backend `971 passed, 9 skipped` (CI `backend-postgres`: `9 passed, 971 deselected, 1 warning`). No commit unless Step 14 needed a fix.

### Task 14: Merge and after (OWNER + agent): the merge, the deploy, a guided check on the phone and a look on a computer, the slice 2c record (S Manual checks, AC18; F §5.5; owner decisions 2, 3; owner answers Q3, Q4)

2c changes no backend code, no migration and no Python requirement, so the merge's Railway deploy builds the same API and its pre-deploy `alembic upgrade head` finds the database at head (`0004_invites_reusable`) and runs nothing; no Railway, Supabase or branch-protection setting changes. The Vercel production deploy is the one that matters: after it, members see the real Date & readings step. Merges never reach https://liturgy-frozen.streamlit.app/ (owner decision 2). Owner answer Q3: a guided check on the phone of six short steps, then a quick look on a computer, given **one at a time** (give one OWNER step, wait for the owner's report or "next", then give the next). The agent writes each result, with its date, into `<scratch>/slice2c-t14-results.md` (not committed); Step 11 fills the record from it. The readings come from the live lectionary and Bible sites, so names and texts may differ slightly from the examples; the owner reports what the page shows.

Below, `<N>` is the PR number (T13), `<merge sha>` the merge commit Step 2 prints, `<scratch>` the scratchpad path; write them out literally. Every `gh` command uses `-R bbrown62450/church`. Pushing, merging, and any settings change each need the owner's explicit yes, asked separately. No token, email address or church id is recorded anywhere.

**Files:**
- Merge (Steps 1-2): no file changes.
- Create (not committed): `<scratch>/slice2c-t14-results.md`.
- Modify (records PR, Step 11, on `claude/slice-2-plan-4q33le` fast-forwarded to `origin/main` after the merge): `docs/ops-runbook.md`: insert `### Slice 2c record` right after `### Slice 2b record`'s table (its last row starts `| Follow-ups | 2c: the Date & readings step;`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins the `##` list.
- Test: none new.

**Interfaces:**
- Consumes: PR `<N>` ready and green (T13); the production URLs (owner decision 5); the "## Slice 2" checklist (T12).
- Produces: 2c live on `main` and in production; the "Slice 2c record" in `docs/ops-runbook.md`. Later user: slice 3's plan (starts from `main` after this).

- [ ] **Step 1 (agent): Check the PR can merge**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,headRefOid --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus) \(.headRefOid)"'
git rev-parse HEAD
git rev-list --count HEAD..origin/main
```

**Expected:** `OPEN draft=false MERGEABLE CLEAN <sha>` with `<sha>` equal to `git rev-parse HEAD`; `0`. If `main` moved (count not `0`, or `BEHIND`): merge it as in T13 Step 1, rerun T13 Steps 2-3 (`346 passed` in 55 files, plus any tests the merge brought; `971 passed, 9 skipped`), push with the owner's yes, wait for green checks, and run this step again. `BLOCKED`: a required check is not green; fix it (T13 Step 14). Never merge with `--admin`.

- [ ] **Step 2 (agent → OWNER): Ask to merge, then merge**

Send: "PR #<N> is ready, green and up to date with main. May I merge it with a merge commit? After that members see the real Date & readings step (Hymns, Liturgy and Review stay 'Available soon'); the API and database do not change." On a clear yes:

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
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" --max-time 15 https://worship-service-builder.vercel.app/builder/readings || echo "vercel not reachable from here"
```

**Expected:** `run <id>` and `ci exit 0`; one deployment per environment (a Vercel `Production` one, and Railway's if it reports one) each ending `success` (a `pending` or `in_progress` state: wait a minute and run the loop again); the `curl` line either a redirect to sign-in (for example `307 https://worship-service-builder.vercel.app/login?next=%2Fbuilder%2Freadings`) or `vercel not reachable from here` (the container's network policy; then Step 4 is the check). A `failure` state or a `404`: stop and tell the owner (Step R if the site cannot serve).

- [ ] **Step 4 (OWNER, then agent): Phone, step 1 of 6: next Sunday fills in**

Send the owner this, and wait for the report:

> On your phone, open https://worship-service-builder.vercel.app (signed in). If you opened the builder before, tap the **⋮** button next to Summary and choose **New service** first. You should see **Service date** set to next Sunday, with the long date under it, and a moment later the **Occasion** (for example "Twentieth Sunday after Pentecost") and the **Scripture readings** filled in, with a caption "From the Revised Common Lectionary: …". The step bar at the top should show Date & readings as done. Does it?

Record the answer (and the phone and browser, and the occasion shown) in the results file. Anything wrong: note it, ask for a screenshot, and decide with the owner whether it is a follow-up or needs a fix before going on. "The lectionary couldn't be reached" here means the reading sites are down: record it, and try this step again later before going on.

- [ ] **Step 5 (OWNER, then agent): Phone, step 2 of 6: a date with two sets**

> Tap **Service date** and pick **March 21, 2027** (Palm Sunday). Under the date you should see "This date has more than one set of readings" with two cards, and the Passion set selected. Tap the other card (the Palms): the occasion and readings should change at once. Did they?

Record the answer.

- [ ] **Step 6 (OWNER, then agent): Phone, step 3 of 6: a weekday with no readings**

> Now pick a plain weekday, **Tuesday, October 6, 2026**. You should see "Not a Sunday. …", then "No lectionary readings for Tuesday, October 6, 2026." with an **Enter readings** button, and a note "These readings are from … not October 6, 2026." with **Clear readings**. The Palm Sunday readings stay until you clear them. Tap **Clear readings**: the occasion and readings empty. Is that what you see?

Record the answer.

- [ ] **Step 7 (OWNER, then agent): Phone, step 4 of 6: typing your own reading**

> Tap **Enter readings**: the cursor should jump to **Occasion**. Type "Harvest Service", then in **Scripture readings** type `Isaiah 50:4-9a` on one line and `Mark 1:1-8` on the next. Under Occasion the caption should read "Entered by you", and a moment later both lines should appear under **Readings** with an "OT" and an "NT" badge. Do they?

Record the answer.

- [ ] **Step 8 (OWNER, then agent): Phone, step 5 of 6: opening Bible text**

> Under **Readings**, tap **Show text** on "Isaiah 50:4-9a": after a moment the passage text appears. Now tap **Bible translation** and choose another one (for example King James Version, or ESV if you prefer it): the text should reload in that translation, and the line above should say "Passage text shown in …". Did the text load and change?

Record the answer.

- [ ] **Step 9 (OWNER, then agent): Phone, step 6 of 6: choosing the bulletin readings, and New service**

> Scroll to **Bulletin readings**. "New Testament reading" should say "Automatic: Mark 1:1-8" and "Old Testament reading" "Automatic: Isaiah 50:4-9a". Tap **New Testament reading** and choose Mark 1:1-8, then tap **Use automatic** under it: it goes back to "Automatic: …". Last, tap **⋮** then **New service**: because you picked a date and a translation, it should ask "Start a new service?" before clearing. Tap **Start new service**: you are back at next Sunday with its readings. Did all of that happen?

Record the answer.

- [ ] **Step 10 (OWNER, then agent): A quick look on a computer**

> On a computer, open the same address in a wide window. The summary on the right should show next Sunday's date and occasion and its readings, with "OT (auto)" and "NT (auto)" beside two of them, and the step bar should read "1 Date & readings Complete · 2 Hymns Soon · 3 Liturgy Soon · 4 Review & send Not in archive". Click **4 Review & send**: it should still say "Available soon" (there is nothing missing, so no "Still needed" list). Does it look right?

Record the answer. Optional, only if the owner offers: the liturgy-frozen smoke (sign in, the church and a saved service open). Otherwise record "Not run: 2c changes no backend code or data, and merges never reach liturgy-frozen."

- [ ] **Step 11 (agent): Write the slice 2c record**

```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
git log --oneline -1
grep -n '^### Slice 2b record$\|^| Follow-ups | 2c: the Date & readings step\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); `<merge sha> Merge pull request #<N> from bbrown62450/claude/slice-2-plan-4q33le`; three lines in that order (the 2b record's heading, its last table row, `## Backups`). Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Slice 2c record

Slice 2c (the Date & readings step: next Sunday's readings filled in, any
date, reading sets, typed readings never overwritten, passage text in a
chosen translation, the bulletin's two readings) merged as PR #<N>. No
backend, API or database change: production stays at
`0004_invites_reusable` (head). The owner's check was a guided check on a
phone and a look on a computer (owner answer Q3, 2026-09-29), covering the
"(owner, after 2c)" items of `docs/manual-verification.md` → "Slice 2" in
part. No token, email address or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` for the merge commit (run <run id>): success. Deployments: <Vercel Production success; Railway success / what the loop showed> | <date> |
| 1. Next Sunday fills in (phone: <phone and browser>) | <Next Sunday, <occasion>, readings filled, step bar done. / What the owner saw instead.> | <date> |
| 2. Two sets (2027-03-21) | <Two cards, Passion selected; Palms applied at once. / …> | <date> |
| 3. Weekday with no readings (2026-10-06) | <No readings prompt, the stale note, Clear readings emptied the fields. / …> | <date> |
| 4. Typing your own reading | <Enter readings focused Occasion; "Entered by you"; OT and NT badges. / …> | <date> |
| 5. Bible text | <Isaiah 50:4-9a loaded; <translation> changed it. / …> | <date> |
| 6. Bulletin readings and New service | <Automatic picks, pick and Use automatic; New service asked first. / …> | <date> |
| Computer | <Summary with readings and OT/NT marks; step bar Complete; Review still Available soon. / …> | <date> |
| Streamlit smoke on liturgy-frozen | <OK: sign-in, the church and a saved service. / Not run: 2c changes no backend code or data, and merges never reach liturgy-frozen.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Slice 3: the Hymns step (and whether card toggles, hymnal overrides and hymn alternatives count as unsaved work). 5a: the archived-service banner question. | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two (separated by ` / `). Then:

```bash
sed -n '/^### Slice 2c record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 2c record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git diff --stat
git add docs/ops-runbook.md
git commit -m "Runbook: slice 2c record (merged; the Date & readings step is live; owner's guided phone check)" -m "Records the slice 2c merge (PR #<N>): no backend, API or database change;
CI on main and the deployments; the owner's guided check on a phone
(next Sunday, two sets, a weekday, typed readings, Bible text, bulletin
readings and New service) and a look on a computer; the liturgy-frozen
smoke or why it was skipped. No token, email or church id is recorded.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** `0`; `0`; `89 passed in <t>s`; ` docs/ops-runbook.md | <n> +`; one commit.

- [ ] **Step 12 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 2c record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 2c record" \
  --body "Records slice 2c (PR #<N>) in docs/ops-runbook.md → Slice 2c record: the merge and deployments, and the owner's guided check on a phone and look on a computer. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the push; the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`, then `gh pr view claude/slice-2-plan-4q33le -R bbrown62450/church --json state --jq .state` → `MERGED`. Report: "Slice 2 is complete and recorded: the Date & readings step is live; no backend change; <n> follow-ups. Slice 3 can start from `main`."

- [ ] **Step R (only if the 2c release must come out): Revert**

Use this only when the production site cannot serve, or the builder breaks sign-in or the church pages, after the merge, and a fix would take too long. 2c wrote nothing to the database and changed no API, so a revert is code only; drafts in members' browsers stay valid for 2b's code (2c changed no draft field). On the owner's yes for each command that leaves this machine:

```bash
git fetch origin
git switch -c claude/revert-slice-2c origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 2c (PR #<N>): back to the 2b release" -m "The 2c merge <what failed>. 2c changed no backend code, API, database or
draft shape, so nothing else needs undoing.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
.venv/bin/python -m pytest -q | tail -1
git push -u origin claude/revert-slice-2c
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-2c --title "Revert slice 2c" \
  --body "Reverts the slice 2c merge (PR #<N>) because <what failed>. No backend or database change to undo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/revert-slice-2c -R bbrown62450/church --watch
```

**Expected:** Vitest `Test Files  49 passed (49)`, `Tests  299 passed (299)` (if anything else merged after 2c, it differs by exactly those tests); `971 passed, 9 skipped`; every check passes. Merge on the owner's yes, then the owner checks that the site signs in and shows the builder with "Available soon". Record the revert as a row of the slice 2c record (or its own records PR if Step 12 already merged).

Expected counts after this task: frontend `346 passed` in 55 files on `main`; backend `971 passed, 9 skipped` (CI `backend-postgres`: `9 passed, 971 deselected, 1 warning`). The records PR adds no test.

---

## Lessons carried from the 2a and 2b builds (P2a, P2b "Build notes")

- **The container restarts.** Uncommitted work can be lost: commit as soon as a task's checks pass, and back the branch up with `git push origin claude/slice-2-plan-4q33le` after every task's review. If `node_modules` is gone after a restart, `(cd frontend && npm ci)`.
- **The network is filtered.** The npm registry and raw.githubusercontent.com are reachable; ui.shadcn.com, Railway and the reading sites are not. No test may need the network (the fake API fails a test on any unhandled request, which is why T5 and T11 add lookup and translations answers to the 2b tests); T4 plans for the blocked registry, T13 Step 4 for a font fetch failure, and T14 Step 3 for an unreachable Vercel.
- **Tests that depend on the date fake `Date`** (`DRAFT_NOW`, Tuesday, September 29, 2026). T13 runs the suite with the real clock moved 8 and 400 days forward; in 2b that caught a test that forgot. Calling `vi.useFakeTimers` a second time keeps the first call's `toFake` list: call `vi.useRealTimers()` first (T7's "Still working" test).
- **Turbopack refuses a symlinked `node_modules`**; a throwaway worktree copies it with `cp -al`.
- **Grep gates exclude tests** and are judged, not obeyed blindly: a hit may be a comment or a test asserting absence; read the line and explain it in the report.
- **Counts are exact.** Every task states its cumulative count; a drift means a missing or extra test, found before moving on.
- **Owner steps one at a time, in plain words**, and every outward action (PR, ready, merge, settings) on its own yes.

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`; F = foundations. Items owned by later slices are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1-7, 9, 13 | Backend (lectionary, passages, translations, profile, rate limits, contract, platform) | 2a (done); 2c reads those bodies (T2, T3, T7, T9) |
| 8 | One `resolve_readings` rule on screen and in the payload; never a Psalm as the automatic NT; stale picks automatic | 2b (pure halves); T10 (the screen: placeholders from `effectivePicks`), T6 (picks drop on blur) |
| 10, 12 | Draft per user and church; next Sunday in the church's zone; the date guard | 2b; T6 ("today" in the church's zone), T13 (guard in the suite) |
| 11 | Four routes in the shell; no sideways scroll at 375 px | 2b; T11 (the readings route), T14 Steps 4-10 (phone) |
| 14 | Auto-fill only for `empty`/`lectionary` fields against the latest draft; the banner rule; failed or empty lookups never change fields; 400 ms debounce; focus never moves | T5 (fill, debounce, visible tab, failures), T7 (focus, stale fields), T8 (banner, confirmations) |
| 15 | Set switcher keyed by index, current date's sets; archived fields fetched, never overwritten | T8 |
| 16 | Passage text only for open rows, 3 in flight; translation changes the text; exact copy; "Try again" refetches | T3 (limiter), T9 |
| 17 | `/` → `/builder`, `last_step`, `AppNav`, `isPristine` with a default benediction | 2b; T1 (the Q2 additions keep the benediction case) |
| 18 | The manual checklist on production; Streamlit still loads | T12 (checklist), T14 (guided owner check, optional smoke) |

### S sections

| S item | Task(s) |
|---|---|
| Slice split lines 5 and 7 (2c) | T1-T11 (clarification 1) |
| UX item 1 (Service date) | T6 |
| UX item 2 (lectionary status: loading, sets, no readings, unavailable, rate limited, partial, stale) | T7, T8 |
| UX item 3 (banner and Replace dialog) | T8 |
| UX items 4, 5 (Occasion, Scripture readings) | T6 |
| UX item 6 (Readings list, passage text, translation) | T9 |
| UX item 7 (Bulletin readings) | T10 |
| UX item 8 (footer "Next: Hymns") | 2b (unchanged) |
| "Other states": translations list failed | T9 |
| Hand-offs row 3 (`passageText`, key `["passage", translation, ref]`) | T3 |
| Hand-offs row 5a "Readings" (`archive` fields with `reading_set: null`) | T8 (test), 2b (rules) |
| Frontend "Routes and files" readings components; Base UI list | T4, T6-T11 |
| `useLectionarySync()` | T5 |
| `status.ts` `isPristine` (with owner answer Q2) | T1 |
| Queries table; "Client timeouts" | T2, T3 |
| Behavior changes 3-6, 12-17 | T5-T10 |
| Testing "Frontend": `use-debounced-value`, `queries/passages`, `readings-step` | T2, T3, T5-T10 |
| Manual checks 1-13 | T12 (appended with 14), T14 (owner) |
| Open question 2 (Saturday vigil) | closed: no (owner answer Q1; T12) |

## Questions for the owner

The owner's answers of 2026-09-29 (Q1-Q4) are binding and already in the plan. These plan choices are visible to the owner; each has a recommendation, and the plan is written with it. Please confirm them together (or change any) before T1 starts.

1. **What makes "New service" ask (clarification 2).** Picking a date, choosing a reading set in the switcher, or choosing a translation other than the church's. "Use next Sunday" counts as putting the default back, so it does not make it ask. Such a draft also keeps its date after that Sunday passes, showing "This date has passed." instead of moving on. Recommended: as written.
2. **The rate-limit message shows a fixed number** ("Too many requests — try again in 12 s."), and "Try again" turns on after that many seconds, rather than a live countdown (clarification 9). Recommended: as written.
3. **Just after a refresh**, before the lectionary answers, an edited occasion's caption reads "Edited from the lectionary" without the set's name for a moment (clarification 10). Recommended: accept.
4. **The date picker stays within 1900-2199**; a typed year outside still gets its message (clarification 11). Recommended: accept.
5. **Only the first too-long scripture line is named** ("Line 3 is too long (max 200 characters)."), not every one (clarification 12). Recommended: accept.
6. **On a phone the unknown-book badge shows only "?"**: tooltips do not open on a tap, though screen readers say "Book not recognized" (clarification 13). Recommended: accept; a tap-to-explain could come later.
7. **Screens 2b built now include Date & readings** (clarification 18): the step bar counts it, Review lists "No occasion — Add one" and similar rows when something is missing, and the summary shows the occasion and the readings with OT and NT marks. Recommended: as written (this is what 2b's owner answer Q1 deferred to 2c).

### Review questions (asked 2026-09-29; answers pending)

The plan review raised six owner-visible questions. The plan is written as before on each until the owner answers; the answers are recorded here and folded into the tasks.

- **A.** Should the mount-time roll-forward ignore a translation override (move a passed default date anyway), and should "New service" keep the chosen translation?
- **B.** On a date with one reading set, after typing, is there a way back to the lectionary readings (the banner shows only after a date change, and the switcher only for two or more sets)?
- **C.** Should "Keep mine" be remembered per date for the session (not only while the step is on screen), and apply to the banner only (not to a declined switcher choice)?
- **D.** After a rate limit's wait ends, what should the text say (it still reads "try again in N s.")?
- **E.** Should Date & readings stop showing "Complete" while one of its fields shows an error (occasion too long, too many readings, a line too long)?
- **F.** While a date is typed: show "Enter a date between 1900 and 2199." only for the settled date (not while the year is half typed), and should a fifth year digit keep the field instead of emptying it?
