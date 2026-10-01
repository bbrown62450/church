# Slice 4b: Liturgy Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 4b of slice 4, the Liturgy step, live. After it merges, a signed-in member who opens step 3 of the Service Builder (`/builder/liturgy`) sees the sermon title and the order of worship in the order the Word files print it: an editable card for each of the 8 liturgy sections (switch, status chip, text, hint), muted rows for the hymns, readings, sermon title and creed, the communion card after the Second Hymn, and custom elements in their printed places. Each card has **Generate** or **Regenerate** (which asks before replacing the member's own or a saved service's text, and offers Undo); **Generate empty sections** writes every switched-on empty card, 3 at a time, with Cancel, and runs keep going on the other steps. Errors show on the card and are never saved; without an AI key nothing is sent. The Benediction follows the church's default until it is changed; communion follows the first Sunday of the month until it is toggled. The step bar counts the liturgy, Review lists each empty section and a missing sermon title, and the summary shows the sections ready, communion and custom elements. Everything that ends up in the service is unsaved work; nothing transient is (owner answer 1). A section may take up to 100 s (owner answer 2). There is no backend change (one docs test aside), no API change and no migration, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** 4a built `GET /liturgy/config`, `POST /liturgy/generate` and `default_benediction` on `GET /church`, and generated their types; 4b adds the screen. Pure pieces live in `src/lib/liturgy/`: `sections.ts` (labels, default switches), `cards.ts` (the origin transitions, communion, the sermon title, custom elements, the selectors, the stale-result rule), `defaults.ts` (`applyLiturgyDefaults`: the church's default benediction and the first-Sunday communion rule, which moves out of `date-effects.ts`), `summary.ts` (`liturgyCounts`), `request.ts` (the request body and the sermon text), `errors.ts` (`cardErrorFrom`) and `queue.ts` (3 at a time). The draft (T1, T5): `isPristine` counts the switches and ignores blank text; `freshDraft` carries the church's default; the draft store keeps untouched cards on the defaults. `lib/queries/liturgy.ts` holds `useLiturgyConfig` and `generateSection` (100 s client timeout). `lib/liturgy/generation.tsx` is `LiturgyGenerationProvider`, mounted in the builder shell: runs, card errors and Undo in memory, one sermon-text fetch per batch, the stale rule inside the draft update, the 429 stop. `src/components/builder/liturgy/` holds the step: `LiturgyStep` composes `SermonTitleField`, `AiBar`, `SectionCard`s, `OutlineLandmark`s, `CommunionCard`, `CustomElementCard`s and `AddCustomElementDialog`. The kit gains `dialog.tsx`; `lib/use-autosize.ts` grows textareas where the browser does not. Last, `SHIPPED_STEPS` gains `"liturgy"`, the route renders the step, `stillNeeded` lists the liturgy's gaps and the summary shows `LiturgySummaryBlock`. Every page stays a client component (F §4.1).

**Tech Stack:** Next 16.3.6 (App Router, Turbopack), React 19.2.8, TypeScript 5, Tailwind 4, Base UI 1.8 (shadcn "base-nova"), TanStack Query 5, sonner 2.0.8, zod 4.6.5, Vitest 3.2.7 (`unit` node and `dom` jsdom projects) with Testing Library; Python 3.11, FastAPI, pytest (backend unchanged but for one docs test); GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Vercel (frontend), Railway (API), Supabase Postgres, OpenAI (`gpt-4.1-mini`).

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`. The 4b parts: "User experience" (all of it), "Frontend changes" (all of it), "Behavior changes vs Streamlit" (the screen halves), "Testing → Frontend", "Manual checklist", acceptance criteria 11-18 and 20 (client half), Risks 4 and 5, every "(4a plan)" and "(4a build)" note and "Notes from the slice 4a plan". Its "Amendment 2026-09-26: service reviewer" is out of scope (its own slice after 4b, owner answer of 2026-09-30); 4b leaves its hooks where they are cheap: the cards keep `{text, origin}` and the stale rule is a pure, reusable function (`captureCard`, `staleVerdict`), the runs and Undo live in a provider a sibling can sit next to, and the 100 s timeout is recorded for its routes.
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (§1.8 timeouts, §4.1-§4.10, decisions D16 and D17, the Amendments table).
- Format models: `docs/superpowers/plans/2026-09-29-slice-3b-hymns-step.md` (the closest analogue: a frontend step; its structure, Build notes and lessons) and `docs/superpowers/plans/2026-09-30-slice-4a-liturgy-backend.md` (the file-directive format this plan uses, its routes, schemas and clarifications, and its Build notes).
- Production facts: `docs/ops-runbook.md` "Slice 4a record": `GET /liturgy/config` answers 8 sections, 17 places, 16 outline items, 31 communion blocks and `ai_available` true; `default_benediction` "Halverson"; a short section about 3 s and Prayers of the People about 5 s; the owner's church is First Presbyterian Church and has a saved Benediction prompt.
- The real code at `4dfed3b` (slices 2a-4a merged): `frontend/src/lib/draft/*` (`schema.ts`, `status.ts` `isPristine`/`withoutTranslation`/`stepStatus`/`stillNeeded`, `fingerprint.ts` `isDirty`, `mapping.ts`, `store.ts` `update`/`autoUpdate`/`replace`/`rollForward`, `context.tsx`, `date-effects.ts`, `readings.ts` `effectivePicks`, `steps.ts`), `lib/queries/{client,keys,church,passages}.ts`, `lib/api/{client,errors,timeouts,types}.ts` and `schema.d.ts` (`LiturgyConfigOut`, `GenerateLiturgyIn`/`Out`, `SectionResult`, `SectionError`, `SermonText`, `HymnRef`, `ChurchProfileOut.default_benediction`), `lib/{dates,latest,storage,use-keyboard-open}.ts`, `components/builder/*` (`BuilderShell`, `StepFooter`, `SummaryPanel`, `StepProgress`, `StillNeeded`, `StepPlaceholder`, the hymns step and `use-undo-toasts.ts`), `components/app/*`, `components/ui/*`, `test/{fake-api,render,mocks,setup-dom}.ts(x)`, `test/fixtures/index.ts`; and `backend/api/routes/liturgy.py`, `backend/liturgy_config.py`, `backend/tests/fixtures/shared/*.json`.
- Facts checked for this plan (tree `4dfed3b`, 2026-09-30):
  - Backend baseline `1183 passed, 11 skipped`; frontend `442 passed` in 64 files; typecheck and lint clean.
  - `components/ui/` has `switch`, `textarea`, `badge`, `alert`, `collapsible`, `select`, `dropdown-menu`, `sheet` and `alert-dialog`, but no `dialog`; the registry (ui.shadcn.com) is blocked (`Request to https://ui.shadcn.com/r/styles/base-nova/dialog.json failed`); raw.githubusercontent.com is reachable.
  - 2b's `StepFooter` already hides below `md` while a text field has focus (`useKeyboardOpen`, focus-based), which owner answer 3 asks for.
  - `lib/api/timeouts.ts` keeps per-route timeouts in `ENDPOINT_TIMEOUTS`; there is no `TIMEOUTS` object and no liturgy row.
  - `isPristine` counts typed, AI and archived text, communion set by the user, a title and custom elements, but not a switch; it counts blank text and a blank title as work. `freshDraft` leaves the Benediction's text `""`, and nothing fills it. `date-effects.ts` holds the communion rule.
  - `keys.liturgyConfig()` exists (`["ref", "liturgy-config"]`); `usePassage`'s options are not exported; `handleAuthErrors` runs only from the query and mutation caches; `useUndoToasts` exists (3b); `SHIPPED_STEPS` holds "readings" and "hymns"; `schema.d.ts` already has every 4a type, so `npm run gen:api` changes nothing.
  - The build container reaches the npm registry, PyPI and raw.githubusercontent.com, but not ui.shadcn.com, Railway, OpenAI or Supabase. No test needs the network.
  - Where S and the code or F disagreed, the code and F won unless an owner answer says otherwise; each case is a numbered clarification below.
  - The whole plan was replayed on a fresh worktree of `4dfed3b` (2026-10-01; `npm ci`, no symlinked `node_modules`), copying every block by line number: all 160 directives matched exactly once, every "see it fail" output and every count matched, each task's typecheck and lint were clean, the production build passed, and T13 Steps 2-8 matched (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run the frontend as `(cd frontend && …)` from the repo root; the working directory resets between commands. Use absolute paths when a tool asks. No foreground `sleep`.
- Run one test file with `(cd frontend && npx vitest run <path> 2>&1 | tail -15)`. Run the whole suite with `(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")`, then `(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`, which prints `typecheck 0` and `lint 0` when both are clean.
- Run the backend suite with `.venv/bin/python -m pytest -q | tail -1` from the repo root.
- `node_modules` exists. If it is missing after a container restart, run `(cd frontend && npm ci)`. Turbopack refuses a symlinked `node_modules`: `npm run build` runs in the real checkout (T13); a throwaway worktree runs `npm ci` or copies it with `cp -al`, never `ln -s`.
- Branch: `claude/slice-2-plan-4q33le`, at `origin/main` `4dfed3b` plus this plan's commits (`WIP plan: slice 4b` commits, then `Plan: slice 4b liturgy step (S slice 4; owner answers 2026-09-30)`). The plan lives at `docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md`.
- Stage files by name (paths with parentheses in single quotes). `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body, and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- Commit subjects read "Area: plain words (S …, owner answer …)". Use TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller, not the task agent, backs the branch up after each task's commit and review with `git push origin claude/slice-2-plan-4q33le` (never `--force`; while no PR is open it asks nobody; Vercel may build a preview). A fix asked for by a task's review is a new commit, `Fix: <what> (Task <n> review)`, never an amend of a pushed commit; T13 lists it. The container can restart and lose uncommitted work, so commit as soon as a task's checks pass. If the push is refused because the remote moved, stop and ask the controller.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then the session link, and includes the line "Tests: frontend 442 → 517 in 64 → 75 files; backend 1183 → 1183 passed, 11 → 11 skipped".
- New prose for the owner has no em dashes and no flattery, and leads with the point. Copy quoted from S keeps its own punctuation (for example "Off — not in the service. Any text is kept.", "Still working — this can take up to a minute.", "Too many requests — try again in N s.", "Kept your edits — the new AI draft for {Label} was not used.", "{Card label} is empty — Write or generate it").
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action.

### How the file directives below read
Each file change is a bold directive followed by a fenced block, applied in the order written (as in the 4a plan):
- **Create `path`:** the block is the whole file.
- **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:** (a block may start or end with an empty line; it is part of the text).
A directive that does not match exactly once is a stop: the tree is not what the plan expects. Find why before changing anything.

### Baselines and counts
- Starting baselines: frontend **442 passed in 64 files**, typecheck and lint clean; backend **1183 passed, 11 skipped**. If any baseline differs, stop and ask.
- Planned cumulative counts. Each frontend delta is exactly the number of `it(` blocks the task adds (an edited test counts 0). If a count drifts, stop and find why.

  | After | Frontend tests (delta) | Test files (delta) | Frontend count | Backend |
  |---|---|---|---|---|
  | T1 | +4 (`lib/liturgy/sections.test.ts` 1, new; `draft/status.test.ts` +1, `draft/fingerprint.test.ts` +1, `draft/store.test.ts` +1) | +1 | 446 in 65 | 1183 passed, 11 skipped |
  | T2 | +9 (`cards.test.ts` 5, `defaults.test.ts` 3, `summary.test.ts` 1, all new in `lib/liturgy/`) | +3 | 455 in 68 | unchanged |
  | T3 | +9 (`request.test.ts` 3, `errors.test.ts` 2, `queue.test.ts` 4, all new in `lib/liturgy/`) | +3 | 464 in 71 | unchanged |
  | T4 | +4 (`lib/queries/liturgy.test.tsx` 3, new; `queries/client.test.ts` +1) | +1 | 468 in 72 | unchanged |
  | T5 | +3 (`draft/store.test.ts` +2, `draft/context.test.tsx` +1; `mapping.test.ts`, `schema.test.ts`, `status.test.ts` one test each edited, 0) | 0 | 471 in 72 | unchanged |
  | T6 | +5 (`lib/liturgy/generation.test.tsx`, new) | +1 | 476 in 73 | unchanged |
  | T7 | +3 (`lib/use-autosize.test.tsx`, new) | +1 | 479 in 74 | unchanged |
  | T8 | +11 (`components/builder/liturgy/liturgy-step.test.tsx`, new) | +1 | 490 in 75 | unchanged |
  | T9 | +16 (`liturgy-step.test.tsx`) | 0 | 506 in 75 | unchanged |
  | T10 | +9 (`liturgy-step.test.tsx`; T8's outline test edited, 0) | 0 | 515 in 75 | unchanged |
  | T11 | +2 (`draft/status.test.ts` +1, `builder-shell.test.tsx` +1; three status tests, two shell tests and the shell helper edited, 0) | 0 | 517 in 75 | unchanged |
  | T12 | 0 | 0 | 517 in 75 | 1183 passed, 11 skipped (one assertion in `test_slice1_docs.py` edited) |
  | T13, T14 | 0 | 0 | 517 in 75 | 1183 passed, 11 skipped |

- CI `backend-postgres` stays at `11 passed, 1183 deselected` (4b adds no Postgres test).
- The step tests fake only `Date` and wait on the app's real timers (the draft's 400 ms writes, the fake API's answers), so `liturgy-step.test.tsx` takes about 18 s; one test fakes `setTimeout` as well (the 8-second "Still working" line) and says why, and one waits out a real 1-second `Retry-After`. Six heavier tests carry `{ timeout: 10_000 }` with a comment.

### Code rules (F §4)
- Every file under `src/app/` that renders is a client component (`"use client"`, F §4.1). Pages and components never call `apiFetch` (F §4.4): the step uses `lib/queries/liturgy.ts`, and the provider calls `generateSection` from there.
- Base UI rules (F §4.9): generated components only, hand edits limited to variants (a use may pass classes, as the switch's larger touch area does); no `asChild` (use `render`, or `buttonVariants` on the element); a Select gets `items`; toasts stay on sonner. The one recorded exception is clarification 19 (the registry is blocked, as in 2b, 2c and 3b).
- Date-only values stay `YYYY-MM-DD` strings; nothing outside `lib/dates.ts` calls `new Date(` on a date-only value (`dates.guard.test.ts`, F acceptance 12).
- Browser storage goes through `lib/storage.ts` only (F §4.3); 4b adds no storage key. Runs, errors and Undo live in memory (owner answer 1).
- Card text, AI text, labels and server messages render as React text only (`react/no-danger` is an error).
- Inputs are `text-base md:text-sm` (the generated `Input` and `Textarea`) so iOS does not zoom; primary actions are 44 px (`size="touch"`), icon buttons `size-11` below `md`, menu items `min-h-11`, and each switch's touch area is 46 px (`after:-inset-y-3.5` on the use).
- DOM tests that depend on "today" fake only `Date` (`vi.useFakeTimers({ toFake: ["Date"] })` plus `vi.setSystemTime(DRAFT_NOW)`), so user-event's and the app's timers keep running. A test that must fake `setTimeout` too calls `vi.useRealTimers()` first and says why.
- A test never proves that something did not happen by sleeping: it first waits for a positive condition that comes after it, then checks the absence.
- sonner replays a toast still showing to the next `Toaster`, so the step tests call `toast.dismiss()` before each test.
- Grep gates exclude test files.

### Messages (verbatim, from S)
- Sermon title: "Sermon title"; placeholder "e.g. Living Water"; "Printed in the bulletin and the pastor's copy. If blank, both show “[Sermon title]”."
- AI bar: "Generate empty sections (n)"; "Only switched-on sections with no text are written. Text you typed is never changed."; "Every switched-on section has text. Use Regenerate on a card for a new AI draft."; "Cancel"; "Writing k of n…"; "Still working — this can take up to a minute."; toasts "Wrote n sections." and "Wrote k of n sections. The rest show what went wrong."; banner "AI writing isn't set up for this app. Type each section yourself — everything else works as usual."; "No occasion or readings yet, so AI text will be general. Add them in Date & readings."; "All liturgy sections are switched off. The Word files will list only hymns, readings, the sermon title and any custom elements."
- Section card: switch "Include {Label}"; chips "Empty", "Your text", "AI draft", "Church default", "From saved service", "Pastor's copy only"; placeholder "Type your own text, or tap Generate."; "Off — not in the service. Any text is kept."; "Waiting…", "Writing…", "Generate", "Regenerate", "AI isn't set up", "Try again"; "Replaced with a new AI draft. Undo", "Cleared. Undo"; counter "n / 20,000"; menu "Clear text", "Use church default"; dialog "Replace your text?", "Regenerate replaces the text in {Label} with a new AI draft. You can undo right after.", "Replace text", "Keep my text"; hints "Start lines with “Leader:” or “People:”. People lines print in bold.", "Printed in bold for everyone to read together.", "People: Thanks be to God! Amen." with "Added automatically after your text.", "Your church's default benediction. Admins can change it in Settings."
- Errors: "AI not configured. Type this section yourself."; "The AI service is busy. Try again in a minute."; "The AI took too long to answer. Try again."; "The AI service had a problem. Try again."; "The {Label} prompt in Settings has a problem: {reason} An admin can fix it under Settings → Liturgy prompts."; "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."; "Too many requests — try again in N s."; "This is taking too long. Try again."; "Can't reach the server. Check your connection and try again."; "Something went wrong. (Ref: {8 chars})"; stale toasts "The service changed, so the AI draft for {Label} was discarded." and "Kept your edits — the new AI draft for {Label} was not used."; and, not in S, a bulk run ended by a new service: "The service changed, so the AI drafts were discarded." (clarification 32)
- Communion: "Include communion liturgy (The Sacrament of the Lord's Supper)"; "On by default — {October 4, 2026} is the first Sunday of the month."; "Off by default — it's on by default only on the first Sunday of the month."; "You changed this."; "Set from the saved service."; "Use default"; "Show communion text"; "Printed after the Second Hymn. The same text is used for every service."
- Custom elements: "+ Add custom element" (the button reads "Add custom element" after a plus icon); dialog "Add custom element", "A heading and text printed in the Word files at the place you choose.", "Label" (placeholder "e.g. Children's Moment"), "Text (optional)" (placeholder "Words for the bulletin or order of service"), "Place", "Cancel", "Add"; "Label is required."; chip "Custom"; "Add a label, or remove this element — it won't be printed without one."; "Remove"; toast "Removed “{label}”." with "Undo"; "You can add up to 30 custom elements."
- Loading and errors: "Couldn't load the liturgy sections." with the server's message and "Retry".
- Shell: Liturgy status "{ready} of {enabled}" / "Complete"; Still needed "{Card label} is empty — Write or generate it" and "No sermon title — Add one"; summary "{ready} of {enabled} liturgy sections ready" (or "All liturgy sections switched off"), " · Writing n sections…", "Communion: Yes" / "Communion: No", "1 custom element" / "{k} custom elements" / "No custom elements".

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried over from 2a-4a). Each use is recorded as a numbered clarification.
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
3. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
4. **Slice 4 decisions** (S; F D17): typed text is never changed by the AI; generating works without a key (empty cards say so); custom elements get no AI Generate (owner answer of 2026-09-30); slice 4 ships as 4a and 4b; the service reviewer is its own slice after 4b; testing like slice 3.
5. **Production:** frontend https://worship-service-builder.vercel.app (Vercel), API https://church-production-74ca.up.railway.app (Railway), Supabase project `worship-staging`. The build container cannot reach Railway, OpenAI or Supabase; no test needs the network.

### Owner answers (2026-09-30, binding for the plan; "all recommended")
- **1. Unsaved work.** Everything that ends up in the service counts: section text, the section switches, the communion switch and its origin, custom elements and the sermon title. Transient UI state does not (AI errors, queued and writing states, Undo lines, "just replaced" notices). A Benediction card still following the church default (origin "default") does not count until changed (S Risks item 4). Checked on `4dfed3b`: `isPristine` missed the switches and counted blank text and a blank title; the transient state was never in the draft. T1 makes `isPristine` exact and pins every field (clarifications 2, 3). This also answers "whether card toggles count as unsaved work": they do, before the first save.
- **2. Timing.** The client timeout for `POST /liturgy/generate` is 100 000 ms (the server's 85 s worst case, plus margin for the server's own sign-in check, the network and the proxy; the client's timer starts only after it has the sign-in token, so the client's own sign-in is not in it), recorded as an F §1.8 amendment (T12); the reviewer slice reuses it. T4 adds the row to `ENDPOINT_TIMEOUTS` (clarification 11).
- **3. Phone keyboard.** Below `md` the sticky footer hides while a textarea or text input on this step has focus, and shows again on blur. 2b's footer already does this for every step (clarification 28); T8 pins it on this step.
- **4. Testing.** Automated tests, then a guided owner check on the phone one step at a time after the merge (generating a few sections, Regenerate with Undo, switching a section off and on, adding a custom element, "New service" asking first) and a quick desktop look (T14); then a records PR.
- **Standing rules:** one PR for 4b; backup pushes to the working branch after each task are done by the controller; every other outward action asks first; production Streamlit untouched.

### The 4b scope (S "Frontend changes")

| Piece | Task | Note |
|---|---|---|
| `isPristine` counts the switches and ignores blank text (owner answer 1); `lib/liturgy/sections.ts` | T1 | the only change to 2b's unsaved-work rule |
| `lib/liturgy/cards.ts`, `defaults.ts`, `summary.ts`; the communion rule moves | T2 | S "Card origin transitions", `defaults.ts`, `summary.ts` |
| `lib/liturgy/request.ts`, `errors.ts`, `queue.ts`; the type names | T3 | S `request.ts`, `errors.ts`, `queue.ts` |
| `lib/queries/liturgy.ts`, the 100 s row, `passageQuery`, `reportAuthErrors`, fixtures | T4 | S "API client usage"; owner answer 2 |
| The default benediction in the fresh draft and the draft store; `peek` | T5 | S "Draft store integration" |
| `LiturgyGenerationProvider` in the builder shell | T6 | S `generation.tsx`, "Sermon text" |
| `components/ui/dialog.tsx`, `useAutosize` | T7 | clarifications 19, 20 |
| `LiturgyStep`, `SectionCard`, `OutlineLandmark`, `SermonTitleField` | T8 | S Layout, Section card; owner answer 3 |
| `AiBar`, the cards' AI states | T9 | S AI bar, Generate and Regenerate |
| `CommunionCard`, `CustomElementCard`, `AddCustomElementDialog` | T10 | S Communion card, Custom elements |
| `"liturgy"` in `SHIPPED_STEPS`, the page, `LiturgySummaryBlock`, `stillNeeded` rows | T11 | S Builder shell |
| S and F notes, the F §1.8 row, "## Slice 4" checklist, heading pin | T12 | owner answers 1, 2, 4 |

## Spec clarifications

The code and F win over S's outline, and the owner's answers over both. **[owner-visible]** items are put to the owner in "Questions for the owner" at the end (confirm or change before or during the build; each is written as recommended); the rest are owner decision 1 (no owner-visible change) or plain readings of S.

1. **The 4b scope, files and tests.** The scope is the table above. Components are kebab-case files under `components/builder/liturgy/` (as 3b's are); S's PascalCase names are their exports, and `LiturgySummaryBlock` is `liturgy/liturgy-summary-block.tsx`. Files S does not list: `lib/liturgy/sections.ts` (the labels and default switches the pure status code needs), `components/builder/liturgy/use-still-working.ts` and `lib/use-autosize.ts`. S's dom cases live in `components/builder/liturgy/liturgy-step.test.tsx` (split across T8-T10 by block) and `builder-shell.test.tsx` (T11, as 3b did); `generation.test.tsx` holds S's sermon-text cases; the fresh-draft switches are pinned in `sections.test.ts` (S put them in `defaults.test.ts`).
2. **[owner-visible] What counts as unsaved work before any save (owner answer 1).** "New service" asks, and the mount-time roll-forward keeps the date, after any card text (typed, AI or saved), a section switched away from its default (a card off, or Prayers of the People on), communion set by the user, a sermon title or a custom element. Text or a title blank after trimming counts as nothing (it prints nothing). A Benediction still following the church default never counts, whatever the default says. Runs, errors and Undo are never in the draft.
3. **[owner-visible, from 5a on] After a save the fingerprint decides.** Once 5a saves drafts, "unsaved changes" means the saved payload differs: a switch on a card with text counts (its text leaves or joins the service), but a switch on an empty card does not, because switches are not saved (S BC-17: 5a derives them from the content). A changed church default on a still-following Benediction shows as unsaved (S Risks item 4). T1 pins both with the fingerprint that 2b built.
4. **One home for the communion rule.** It moves from `date-effects.ts` into `lib/liturgy/defaults.ts` (`applyCommunionDefault`), which `date-effects.ts` calls; S's `firstSundayOfMonth` is slice 2's `isFirstSundayOfMonth` in `lib/dates.ts`, run against `shared/first_sunday.json` in `defaults.test.ts`.
5. **Reducer names.** S's `useChurchDefault` is `restoreChurchDefault` (React's lint reads a `use…` name as a hook, and the menu calls it from a click); communion's switch and "Use default" are `setCommunion` and `restoreCommunionDefault`, and the sermon title `setSermonTitle`, all in `cards.ts` (S lists no reducer for them). `removeCustomElement` returns `{draft, element, index}` (or null).
6. **Unknown places.** `PLACEMENT_KEYS` (the 17) is pinned to the outline fixture's anchors. A stored element with an unknown place shows at the end, its Place reads "At the end (after Benediction)", and the draft keeps the stored value until the member edits Place (5a normalizes on load, as S says); a new element's place is normalized when it is added.
7. **A hymn id that is not a UUID goes as `null`.** The API validates `hymn_id` as a UUID and would reject the whole request with a 422; as a snapshot the pick's own title is used.
8. **What `cardErrorFrom` shows nothing for.** A cancel (the card returns to where it was), a 401 and a lost church (the app's handling signs out or falls back, F §4.4) show nothing on the card. A 429 without a wait uses the server's message. Everything else follows S's table.
9. **[owner-visible] The 404's link reads "Go to Hymns"** (S: "A link to /builder/hymns").
10. **`generateSection(call, section, body, signal)` takes the built body** (S passes the draft); `buildGenerateRequest` builds it, so the pure part is tested alone.
11. **[owner-visible] The 100 s timeout (owner answer 2).** `lib/api/timeouts.ts` has no `TIMEOUTS` object; its per-route table `ENDPOINT_TIMEOUTS` gains `"POST /liturgy/generate": 100_000`. S's "timeout (client, 90 s)" row reads 100 s; F §1.8 is amended (T12), with the reviewer's `/liturgy/review` and `/liturgy/revise` noted to reuse it. `apiFetch` starts the timer after `getAccessToken()`, so the 15 s above the server's 85 s cover the server's sign-in key fetch (at most 5 s), latency and the proxy, not the client's own sign-in (plan review fix M2).
12. **`reportAuthErrors(error, churchId)`.** The generation queue calls the API outside the query and mutation caches, so `lib/queries/client.ts` exports the logic `handleAuthErrors` already ran; the caches call it too.
13. **The default benediction in the draft.** `freshDraft` fills the Benediction from the profile's `default_benediction` ("Halverson" when an older API leaves it out), so a fresh draft is born with it and "New service" gets it. The draft store runs `applyLiturgyDefaults` on load, on every change and on replace (and in memory on an adopted draft). A load it changes is stamped 1 ms after the stored draft; a new default from a profile refetch is an automatic change, stamped 1 ms after the current draft (2c's `autoUpdate`), so neither ever outranks another tab's edit. Three existing tests change their expected values (a fresh draft now prints "Halverson").
14. **`useDraft().peek()`** returns the latest draft now, for the provider's code that runs outside a render (a request's start and its answer).
15. **[owner-visible] What a bulk run's toast counts.** Cancelled cards are not counted; a run cancelled whole ends with no toast; a result dropped by the stale rule counts as not written (its own toast says why), as does a card stopped by a 429.
16. **[owner-visible] Singulars.** "Wrote 1 section." and the summary's "Writing 1 section…" (S writes only the plural); "1 custom element" is S's.
17. **`sermonWaitMs`.** The provider takes the 10 s sermon-text wait as a prop (default `SERMON_WAIT_MS`), so a test can shorten it instead of faking every timer.
18. **The provider's interface.** `useLiturgyGeneration()` returns `{runs, errors, undo, bulk, generate(keys, {aiAvailable, bulk}), cancel(keys?), cancelBulk(), dismissError, setUndo, clearUndo, applyUndo}` (S: `{runs, undo, generate(keys), cancel(keys?), applyUndo(key), dismissError(key)}`). The step passes `aiAvailable` from the config, so the provider fetches nothing until asked and the other steps need no new route. Card errors live in the provider (S: "component state") so they survive a visit to another step; Undo lines go when the step unmounts, as S says.
19. **`components/ui/dialog.tsx` is rebuilt from the upstream shadcn source** (the registry is blocked), with the pipeline that reproduces the repo's `sheet.tsx` byte for byte (T7). The "Add custom element" dialog becomes a bottom sheet below `md` through classes on its use, not by editing the generated file. (Owner decision 1; the exception the owner accepted for 2b-3b.)
20. **`useAutosize`.** The kit's `Textarea` already sizes itself with `field-sizing: content`; the hook sets the height only where the browser cannot, capped at 60% of the window, and the cards cap the field at `max-h-[60vh]`. A card's minimum height is its config rows (`calc({rows}lh + …)`).
21. **[owner-visible] The step's heading.** The step opens with the heading "Liturgy" (as Hymns opens with "Hymns") and is a region by that name; the AI bar is a region named "Write with AI" (S names neither).
22. **[owner-visible] Try again stands in for the card's button.** While a retryable error shows, its alert's **Try again** is the card's action (it asks first, as Regenerate does, when it would replace the member's text); a non-retryable error (not configured, a prompt problem, a missing hymn) keeps Generate or Regenerate under the alert.
23. **[owner-visible] "Writing k of n…"** counts the sections finished plus one (the one being written), so a run of 5 starts at "Writing 1 of 5…" and ends at "Writing 5 of 5…" (S does not define k).
24. **[owner-visible] Landmark rows** read "First Hymn · {title}" (the title only, as S's layout shows), "First Reading · {reference} auto", "Sermon Title · [Sermon title]" and "Affirmation of Faith · Apostles' Creed"; an empty hymn slot or reading shows only its label.
25. **[owner-visible] A custom element with a blank label** is titled "Custom element" on its card and in its menu's name; the Remove toast names the label.
26. **[owner-visible] The communion card's header is its switch label**, "Include communion liturgy (The Sacrament of the Lord's Supper)"; "Show communion text" keeps its words when open (a chevron turns).
27. **[owner-visible] Still needed.** Each switched-on empty card's row links to `/builder/liturgy#card-{key}` and the step scrolls to it; "No sermon title — Add one" links to `/builder/liturgy`; the card rows come first, in section order (S: "to `#card-{key}` for the first").
28. **The phone keyboard (owner answer 3)** is already handled by 2b's `StepFooter` through `useKeyboardOpen()`, which watches focus (a text input, a writable textarea) rather than `visualViewport`, because the visual viewport is not reliable across mobile browsers. 4b adds no hook, only T8's test on this step. A card that is writing is read-only, so its keyboard does not open and the footer stays.
29. **The stale rule and the queue.** A draft's identity is its `created_at` (stable across 5a's saves; `save_key` rotates on save), so the "service changed" test moves the clock before "New service". The queue hands a task's outcome to the provider before the next queued task starts, and a task cancelled before its `run` was called never runs, so a 429 stops the waiting cards at once.
30. **[owner-visible] Small card rules.** The "Replaced with a new AI draft." line shows only when the AI replaced text (Generate on an empty card shows none); the ⋯ menu is disabled when it has nothing to offer (an empty card other than the Benediction) as well as while the card runs.
31. **The switch's touch area.** The generated switch is 18 px tall with a larger invisible hit area; the cards pass `after:-inset-y-3.5`, which makes it 46 px, instead of editing `switch.tsx`.
32. **[owner-visible] "New service" during a run** (plan review fix I1; S step 6). The provider watches the draft's `created_at`. When it changes ("New service", or another tab's new service adopted here) every run is cancelled silently, the cards' errors and Undo lines are cleared, and a bulk run ends with one toast, "The service changed, so the AI drafts were discarded." (no "Wrote…" toast, no per-card toasts). A single card's run ends with no toast. A result that arrives in the moment before the provider sees the change still meets S's per-result rule and its toast.
33. **The card is captured when the member asks** (plan review fix C1; S step 6). `generate()` captures each card at the click (or at "Replace text"), not when its request starts. A queued run checks `staleVerdict` against the current draft before it sends; if the card's text changed (Undo, another tab) or the service changed, it sends nothing, shows S's toast and counts as not written. While a card runs its Undo line is hidden. Owner decision 1.
34. **Focus stays on the card** (plan review fix I3; F §4.9). Section and custom-element headings take focus (`tabIndex={-1}`). After Cancel and Try again focus goes to the card's next control (Generate or the run's Cancel); after Replace text to the run's Cancel (the confirm dialog's `finalFocus`), after Keep my text back to the button that opened it; after Clear to "Undo"; after Undo to the heading; after a custom element's Remove to the next card's heading, or "Add custom element" when none follows. Owner decision 1.
35. **[owner-visible] The card header on a phone** (plan review fix I2). Below `sm` the chips ("Pastor's copy only", the status) sit on their own line under the title, so the switch, title and ⋯ menu always fit at 375 px; from `sm` they sit beside the title.
36. **Small reliability fixes** (plan review fixes M1, M3-M7, M9; owner decision 1). A result written over a blank card clears its "Cleared. Undo" line. Undo of a custom element's Remove refuses past 30 elements with the toast "You can add up to 30 custom elements." (`restoreCustomElement` takes the limit). A malformed `#…` address scrolls nowhere instead of throwing. `useAutosize` sizes a field again when its card is switched back on. The "Add custom element" sheet scrolls within 85 dvh on a phone. A 429 stores the moment its wait ends (`retryAt`): Try again and "Generate empty sections" wait until then, and leaving the step does not restart it. Each card's hint, Assurance line, counter and error are the textarea's description (`aria-describedby`); a bulk run's errors are announced politely, while a card's own run keeps `role="alert"`.
37. **[owner-visible] Clearing the church-default Benediction is not unsaved work** (plan review M8, left as is). Clear text on a Benediction that follows the default leaves it empty, which counts as nothing (clarification 2), so "New service" does not ask; a fresh draft brings the default back anyway.

### Risks carried into the plan
- **Live AI.** The drafts come from `gpt-4.1-mini` through Railway; the tests use fakes. The owner's check (T14 Steps 5-6) times a real run of 5 sections.
- **The sermon text.** A batch waits up to 10 s for the NT passage (bible-api.com for WEB); when it is slow the whole batch waits that long before sending. S accepts this; the owner's check reports the time.
- **Real-timer tests.** `liturgy-step.test.tsx` waits on real 400 ms writes and one real 1-second `Retry-After`. T9, T10 and T13 run the suite three times and with the clock moved forward; a flaky run is fixed by making the test deterministic, never by retrying.
- **Turbopack refuses a symlinked `node_modules`**; `npm run build` runs in the real checkout (T13).
- **The registry stays blocked**; T7 records the attempt and uses clarification 19's file.

## File Structure

All paths are from the repo root. "liturgy/" means `frontend/src/components/builder/liturgy/`; "lib/liturgy/" means `frontend/src/lib/liturgy/`.

**Created**

| Path | Responsibility | Task |
|---|---|---|
| `docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md` | this plan | 0 |
| `lib/liturgy/sections.ts` (+ `.test.ts`) | `SECTION_LABELS`, `DEFAULT_ENABLED` | T1 |
| `lib/liturgy/cards.ts` (+ `.test.ts`) | the transitions, selectors, `PLACEMENT_KEYS`, `captureCard`, `staleVerdict` | T2 |
| `lib/liturgy/defaults.ts` (+ `.test.ts`) | `applyLiturgyDefaults`, `applyCommunionDefault`, `DEFAULT_BENEDICTION_FALLBACK` | T2 |
| `lib/liturgy/summary.ts` (+ `.test.ts`) | `liturgyCounts` | T2 |
| `lib/liturgy/request.ts` (+ `.test.ts`) | `buildGenerateRequest`, `sermonSource`, `sermonText` | T3 |
| `lib/liturgy/errors.ts` (+ `.test.ts`) | `cardErrorFrom`, `localAiNotConfigured` | T3 |
| `lib/liturgy/queue.ts` (+ `.test.ts`) | `createTaskQueue` | T3 |
| `frontend/src/lib/queries/liturgy.ts` (+ `.test.tsx`) | `useLiturgyConfig`, `generateSection` | T4 |
| `lib/liturgy/generation.tsx` (+ `.test.tsx`) | `LiturgyGenerationProvider`, `useLiturgyGeneration` | T6 |
| `frontend/src/components/ui/dialog.tsx` | base-nova dialog (clarification 19) | T7 |
| `frontend/src/lib/use-autosize.ts` (+ `.test.tsx`) | `useAutosize` | T7 |
| `liturgy/liturgy-step.tsx` (+ `liturgy-step.test.tsx`) | `LiturgyStep` (grows in T9-T11) | T8 |
| `liturgy/section-card.tsx` | `SectionCard` (T9 adds the AI) | T8 |
| `liturgy/outline-landmark.tsx`, `liturgy/sermon-title-field.tsx` | `OutlineLandmark`, `SermonTitleField` | T8 |
| `liturgy/ai-bar.tsx`, `liturgy/use-still-working.ts` | `AiBar`, `useStillWorking` | T9 |
| `liturgy/communion-card.tsx`, `liturgy/custom-element-card.tsx`, `liturgy/add-custom-element-dialog.tsx` | the communion card, custom elements, the Add dialog | T10 |
| `liturgy/liturgy-summary-block.tsx` | `LiturgySummaryBlock` | T11 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `frontend/src/lib/draft/schema.ts` | `freshDraft` reads `DEFAULT_ENABLED` (T1) and the church's default benediction; `DraftChurch.default_benediction` (T5) | T1, T5 |
| `frontend/src/lib/draft/status.ts` (+ `status.test.ts`) | `isPristine` (T1); `stepStatus` from `liturgyCounts`, `NeededItem.href`, the liturgy rows (T11) | T1, T5 (test), T11 |
| `frontend/src/lib/draft/fingerprint.test.ts`, `store.test.ts` | owner answer 1 pinned (T1); the store's defaults (T5) | T1, T5 |
| `frontend/src/lib/draft/date-effects.ts` | calls `applyCommunionDefault` | T2 |
| `frontend/src/lib/api/types.ts` | the liturgy type names | T3 |
| `frontend/src/lib/api/timeouts.ts` | `"POST /liturgy/generate": 100_000` | T4 |
| `frontend/src/lib/queries/client.ts` (+ `client.test.ts`), `passages.ts` | `reportAuthErrors`; `passageQuery` | T4 |
| `frontend/src/test/fixtures/index.ts` | `liturgyConfig`, `sectionResult`, `sectionFailure`, `generateRoute` | T4 |
| `frontend/src/lib/draft/store.ts`, `context.tsx` (+ `context.test.tsx`), `mapping.test.ts`, `schema.test.ts` | the liturgy defaults, `peek`; three expected values | T5 |
| `frontend/src/components/builder/builder-shell.tsx` | mounts the provider | T6 |
| `frontend/src/lib/draft/steps.ts`, `components/builder/still-needed.tsx`, `summary-panel.tsx`, `step-placeholder.tsx` (comment), `builder-shell.test.tsx`, `(church)/builder/liturgy/page.tsx` | `"liturgy"` ships; the rows, the summary block and the page | T11 |
| `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | the 4b notes, two F rows, "## Slice 4", the heading pin | T12 |
| `docs/ops-runbook.md` | "Slice 4b record" (the records PR after the merge) | T14 |

**Counts:** 33 created (this plan and 32 frontend files) and 28 modified (24 frontend files, 1 backend test and 3 docs) in the 4b PR; T13 Step 7 checks the exact list. The runbook's "Slice 4b record" is its own records PR (T14).

**Untouched:** every backend source file, `backend/requirements*.txt`, migrations, `frontend/package.json` and `package-lock.json` (no new dependency: `@base-ui/react` has the dialog), `frontend/src/lib/api/openapi.json` and `schema.d.ts`, `frontend/src/lib/draft/{migrate,mapping,fingerprint,prune,readings}.ts`, `lib/use-keyboard-open.ts`, `components/builder/step-footer.tsx`, the Hymns and Date & readings steps, Streamlit files, CI workflows.

**Task order and review batches:** T1 → T12 each end in one commit, a review and a backup push; T13 verifies the branch, opens the draft PR (owner's yes) and marks it ready (owner's yes); T14 merges (owner's yes), runs the guided check and writes the record. The controller reviews in four batches:
- **Batch A (T1-T2):** unsaved work and the pure card rules.
- **Batch B (T3-T6):** the request, errors, queue, queries, the draft's defaults and the provider.
- **Batch C (T7-T10):** the kit pieces and the screen.
- **Batch D (T11-T12):** the shell and the docs.

---

### Task 1: Liturgy that prints is unsaved work; a card following the church default is not (owner answer 1; S "Draft store integration", Risks 4; F §4.6 "Unsaved changes"; clarifications 2, 3)

Owner answer 1 makes S exact: what "New service" asks about (`isDirty`, which is `!isPristine` until 5a saves drafts, then the fingerprint of `draftToServicePayload`) and what holds a passed default date back on load (`rollForward`, through `isPristine`) must count the card text, the section switches, communion, the sermon title and the custom elements, and never a Benediction still following the church default or any of the step's transient state (which never enters the draft). Checked on `4dfed3b`: `isPristine` already counts typed, AI and archived text, communion set by the user, a sermon title and any custom element, and treats `origin: "default"` as pristine; it does **not** count a switch (a card switched off, or the Prayers of the People switched on, looks pristine), and it counts whitespace-only text and a whitespace-only title as work although they print nothing. The fingerprint payload already holds every enabled card with text, the title, communion and the custom elements. So the code change is `isPristine`'s card and title conditions, plus one home for the default switches (`lib/liturgy/sections.ts`, pinned to the shared fixture, which `freshDraft` now reads). The fingerprint test passes before the change: it pins what 2b built, including S Risks item 4 (after a save, a Benediction following the default shows a changed default as unsaved) and that a switch on an empty card is not saved (switches are not archived; clarification 3).

**Files:**
- Create: `frontend/src/lib/liturgy/sections.ts` (`SECTION_LABELS`, `DEFAULT_ENABLED`)
- Modify: `frontend/src/lib/draft/schema.ts` (`freshDraft` reads `DEFAULT_ENABLED`), `frontend/src/lib/draft/status.ts` (`isPristine` and its comment)
- Test: `frontend/src/lib/liturgy/sections.test.ts` (new, 1), `frontend/src/lib/draft/status.test.ts` (+1), `frontend/src/lib/draft/fingerprint.test.ts` (+1), `frontend/src/lib/draft/store.test.ts` (+1)

**Interfaces:**
- Consumes: `SECTION_KEYS`, `freshDraft` (2b), `isPristine`, `isDirty`, `rollForward` (2b, 2c, 3b), `backend/tests/fixtures/shared/liturgy_sections.json` (4a).
- Produces: `SECTION_LABELS: Readonly<Record<SectionKey, string>>` and `DEFAULT_ENABLED: Readonly<Record<SectionKey, boolean>>`; `isPristine(draft)` is also false when a card's `enabled` differs from `DEFAULT_ENABLED`, and true for blank (after trimming) `empty` text and a blank title. Later users: T2 (`liturgyCounts`, `stillNeeded`'s labels), T6 (toast labels), T8-T11.

Counts after this task: frontend **446 passed in 65 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/lib/liturgy 2>&1 | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/lib/liturgy': No such file or directory`; ` Test Files  64 passed (64)`, `      Tests  442 passed (442)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/sections.test.ts`:**

```ts
/**
 * The TypeScript copy of the 8 sections (slice 4 spec, Testing `defaults.test.ts`
 * "fresh-draft card switches equal shared/liturgy_sections.json"): labels and
 * default switches equal the shared fixture that backend/liturgy_config.SECTIONS
 * also equals, and a fresh draft switches its cards on exactly as it says.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { SECTION_KEYS } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { DEFAULT_ENABLED, SECTION_LABELS } from "./sections";

type Fixture = { sections: { key: string; label: string; default_enabled: boolean }[] };

const fixture = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/liturgy_sections.json", import.meta.url), "utf-8"),
) as Fixture;

describe("liturgy sections (shared/liturgy_sections.json)", () => {
  it("has the fixture's keys, labels and default switches, and a fresh draft's cards follow them", () => {
    expect(fixture.sections.map((s) => s.key)).toEqual([...SECTION_KEYS]);
    expect(SECTION_KEYS.map((key) => SECTION_LABELS[key])).toEqual(fixture.sections.map((s) => s.label));
    expect(SECTION_KEYS.map((key) => DEFAULT_ENABLED[key])).toEqual(fixture.sections.map((s) => s.default_enabled));
    const cards = testDraft().liturgy.cards;
    expect(SECTION_KEYS.map((key) => cards[key].enabled)).toEqual(fixture.sections.map((s) => s.default_enabled));
  });
});
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts

describe("stillNeeded (S Review \"Still needed\")", () => {
```

**with:**

```ts

describe("isPristine and the liturgy step (owner answer 1, 2026-09-30)", () => {
  it("counts a switch moved from its default and text that prints, never a card following the church default", () => {
    // Everything that ends up in the service counts: text, the switches, communion, the title, custom elements.
    expect(isPristine(withCard("call_to_worship", { enabled: false }))).toBe(false);
    expect(isPristine(withCard("prayers_of_the_people", { enabled: true }))).toBe(false);
    expect(isPristine(withCard("benediction", { enabled: false }))).toBe(false);
    expect(isPristine(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }))).toBe(false);
    // A Benediction still following the church default is not the user's work, whatever the default says.
    expect(isPristine(withCard("benediction", { text: "Go in peace.", origin: "default" }))).toBe(true);
    expect(isPristine(withCard("benediction", { text: "", origin: "default" }))).toBe(true);
    // Text that prints nothing is not work: blank typing, a blank title.
    expect(isPristine(withCard("assurance", { text: "  \n ", origin: "empty" }))).toBe(true);
    expect(isPristine(withLiturgy({ sermon_title: "   " }))).toBe(true);
    // A card switched off and back on again is as it was.
    expect(isPristine(withCard("call_to_worship", { enabled: true }))).toBe(true);
  });
});

describe("stillNeeded (S Review \"Still needed\")", () => {
```

**In `frontend/src/lib/draft/fingerprint.test.ts`, replace:**

```ts
  });
});
```

**with:**

```ts
  });

  it("after a save, liturgy that prints is unsaved; a switch on an empty card is not (owner answer 1, 2026-09-30)", () => {
    const base = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: {
          ...d.liturgy.cards,
          call_to_worship: { enabled: true, text: "Come, let us worship.", origin: "typed" },
          benediction: { enabled: true, text: "Halverson", origin: "default" },
        },
      },
    }));
    const saved: DraftV1 = { ...base, saved_fingerprint: fingerprint(draftToServicePayload(base)) };
    const liturgy = (patch: Partial<DraftV1["liturgy"]>): DraftV1 => ({ ...saved, liturgy: { ...saved.liturgy, ...patch } });
    const card = (key: "call_to_worship" | "opening_prayer" | "benediction", patch: object): DraftV1 =>
      liturgy({ cards: { ...saved.liturgy.cards, [key]: { ...saved.liturgy.cards[key], ...patch } } });
    expect(isDirty(saved)).toBe(false);
    expect(isDirty(card("call_to_worship", { text: "Come, let us worship God.", origin: "typed" }))).toBe(true);
    expect(isDirty(card("call_to_worship", { enabled: false }))).toBe(true); // its text leaves the service
    expect(isDirty(liturgy({ include_communion: !saved.liturgy.include_communion, communion_origin: "user" }))).toBe(true);
    expect(isDirty(liturgy({ sermon_title: "Living Water" }))).toBe(true);
    expect(isDirty(liturgy({ custom_elements: [{ id: "c1", label: "Anthem", text: "", insert_after: "sermon" }] }))).toBe(true);
    // Slice 4 Risks item 4: a Benediction following the church default shows the new default as unsaved.
    expect(isDirty(card("benediction", { text: "Go in peace." }))).toBe(true);
    // Switches are not saved (slice 4 BC-17), so switching an empty card prints nothing new.
    expect(isDirty(card("opening_prayer", { enabled: false }))).toBe(false);
  });
});
```

**In `frontend/src/lib/draft/store.test.ts`, replace:**

```ts

describe("DraftStore changes (S store.ts)", () => {
```

**with:**

```ts

describe("DraftStore roll-forward and the liturgy step (owner answer 1, 2026-09-30)", () => {
  it("keeps a passed default date when a card was switched, and rolls one whose Benediction follows the default", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const card = (key: "prayers_of_the_people" | "benediction", patch: object) =>
      testDraft((d) => ({
        ...d,
        liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } },
      }));
    const load = (d: DraftV1) =>
      makeStore(memoryStorage({ [KEY]: JSON.stringify(d) }).storage, tenDaysLater.now).store.getSnapshot().draft;
    expect(load(card("prayers_of_the_people", { enabled: true })).readings.date_iso).toBe("2026-10-04");
    expect(load(card("benediction", { text: "Go in peace.", origin: "default" })).readings.date_iso).toBe("2026-10-11");
  });
});

describe("DraftStore changes (S store.ts)", () => {
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/sections.test.ts src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|Error: Cannot find|Tests ")
```

**Expected:**

```
 FAIL  |unit| src/lib/liturgy/sections.test.ts [ src/lib/liturgy/sections.test.ts ]
Error: Cannot find module './sections' imported from '<repo>/frontend/src/lib/liturgy/sections.test.ts'
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 2 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/draft/status.test.ts > isPristine and the liturgy step (owner answer 1, 2026-09-30) > counts a switch moved from its default and text that prints, never a card following the church default
AssertionError: expected true to be false // Object.is equality
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore roll-forward and the liturgy step (owner answer 1, 2026-09-30) > keeps a passed default date when a card was switched, and rolls one whose Benediction follows the default
AssertionError: expected '2026-10-11' to be '2026-10-04' // Object.is equality
      Tests  2 failed | 27 passed (29)
```

(`<repo>` is the checkout's absolute path. The new fingerprint test passes already: it pins the payload 2b built.)

- [ ] **Step 4 (agent): Count the switches and printed text in `isPristine`**

**Create `frontend/src/lib/liturgy/sections.ts`:**

```ts
/**
 * The 8 liturgy sections as the draft and the pure status code need them
 * (slice 4 spec, Backend 1 `SECTIONS`; F §4.6 "Fresh draft"): each section's
 * label and whether a fresh draft switches it on. This is the one TypeScript
 * copy; `sections.test.ts` pins it to backend/tests/fixtures/shared/
 * liturgy_sections.json, which backend/liturgy_config.SECTIONS also equals.
 * The step reads the rest (rows, hints, the order of worship) from
 * GET /liturgy/config.
 */
import type { SectionKey } from "@/lib/draft/schema";

export const SECTION_LABELS: Readonly<Record<SectionKey, string>> = {
  call_to_worship: "Call to Worship",
  opening_prayer: "Opening Prayer",
  prayer_of_confession: "Prayer of Confession",
  assurance: "Assurance of Pardon",
  prayer_for_illumination: "Prayer for Illumination",
  prayers_of_the_people: "Prayers of the People",
  offertory_prayer: "Offertory Prayer",
  benediction: "Benediction",
};

/** Every section starts switched on except the Prayers of the People (app.py:890 parity). */
export const DEFAULT_ENABLED: Readonly<Record<SectionKey, boolean>> = {
  call_to_worship: true,
  opening_prayer: true,
  prayer_of_confession: true,
  assurance: true,
  prayer_for_illumination: true,
  prayers_of_the_people: false,
  offertory_prayer: true,
  benediction: true,
};
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";

```

**with:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";

```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
      { enabled: key !== "prayers_of_the_people", text: "", origin: key === "benediction" ? "default" : "empty" },
```

**with:**

```ts
      { enabled: DEFAULT_ENABLED[key], text: "", origin: key === "benediction" ? "default" : "empty" },
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { cleanLines } from "@/lib/scripture-refs";
```

**with:**

```ts
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
import { cleanLines } from "@/lib/scripture-refs";
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
 * 2026-09-29, slice 3b; the same fields the fingerprint payload holds).
```

**with:**

```ts
 * 2026-09-29, slice 3b; the same fields the fingerprint payload holds). On
 * the Liturgy step everything that ends up in the service counts: card text,
 * a card switched away from its default, communion the user set, the sermon
 * title and custom elements; a Benediction still following the church
 * default (origin "default") and text that prints nothing (blank after
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b).
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
      return card.origin === "default" || (card.origin === "empty" && card.text === "");
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title === "" &&
```

**with:**

```ts
      const text = card.origin === "default" || (card.origin === "empty" && card.text.trim() === "");
      return card.enabled === DEFAULT_ENABLED[key] && text;
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title.trim() === "" &&
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy/sections.test.ts src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  4 passed (4)`, `      Tests  30 passed (30)`; the suite ` Test Files  65 passed (65)`, `      Tests  446 passed (446)`; `typecheck 0` and `lint 0`; ` M` for the five modified files and `??` for `frontend/src/lib/liturgy/`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/sections.ts frontend/src/lib/liturgy/sections.test.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/draft/fingerprint.test.ts frontend/src/lib/draft/store.test.ts
git commit -m "Draft: liturgy that prints is unsaved work; a card following the church default is not (owner answer 1)" -m "isPristine also counts a liturgy card switched away from its default
(SECTION_LABELS and DEFAULT_ENABLED in lib/liturgy/sections.ts, pinned to
shared/liturgy_sections.json, which freshDraft now reads), and no longer
counts blank text or a blank sermon title, which print nothing. A
Benediction following the church default still never counts. After a save
the fingerprint payload decides, as 2b built it (S Risks item 4 pinned).
Frontend 442 -> 446 tests in 64 -> 65 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

### Task 2: The cards' draft transitions, the liturgy defaults and the counts (S "Card origin transitions", Frontend `cards.ts`, `defaults.ts`, `summary.ts`; F §4.6; clarifications 4, 5, 6)

The pure half of the step. `cards.ts` holds every transition of S's origin table (typing, an AI result, Clear, "Use church default", Undo, the switch), the communion switch and "Use default", the sermon title, the custom elements (added trimmed, edited, removed and restored at their index, an unknown place read as "end"), the selectors "Generate empty sections" and Regenerate need, and the stale-result rule (`captureCard`, `staleVerdict`) that T6 applies and the service reviewer will reuse. `defaults.ts` keeps an untouched Benediction on the church default and untouched communion on the date's first-Sunday rule; the communion rule moves there from 2b's `date-effects.ts` (S: "that code moves into `applyLiturgyDefaults`, so there is one place for it"), which now calls it. `summary.ts` is the one count behind the step bar and the summary.

**Files:**
- Create: `frontend/src/lib/liturgy/cards.ts`, `frontend/src/lib/liturgy/defaults.ts`, `frontend/src/lib/liturgy/summary.ts`
- Modify: `frontend/src/lib/draft/date-effects.ts` (calls `applyCommunionDefault`)
- Test: `frontend/src/lib/liturgy/cards.test.ts` (new, 5), `frontend/src/lib/liturgy/defaults.test.ts` (new, 3), `frontend/src/lib/liturgy/summary.test.ts` (new, 1). 2c's `readings.test.ts` keeps pinning communion on a date change.

**Interfaces:**
- Consumes: `DraftV1`, `LiturgyCard`, `SECTION_KEYS` (2b), `isFirstSundayOfMonth` (2b `lib/dates.ts`), `setDate` (2c), `shared/first_sunday.json` and `shared/liturgy_outline.json` (4a).
- Produces:
  - `cards.ts`: `type CardOrigin`, `type CardSnapshot = {text, origin}`, `type CustomElement`, `PLACEMENT_KEYS` (the 17), `normalizePlacement(key)`, `editCardText(d, key, text)`, `setCardEnabled(d, key, enabled)`, `applyGenerated(d, key, text)`, `clearCard(d, key)`, `restoreChurchDefault(d, defaultText)` (S's `useChurchDefault`; clarification 5), `restoreCard(d, key, previous)`, `setSermonTitle(d, title)`, `setCommunion(d, include)`, `restoreCommunionDefault(d)`, `addCustomElement(d, {label, text, insert_after}, id)`, `updateCustomElement(d, id, patch)`, `removeCustomElement(d, id) → {draft, element, index} | null`, `restoreCustomElement(d, element, index, max)` (unchanged when the list already holds `max`; clarification 36), `sectionsNeedingAi(d)`, `needsRegenerateConfirm(card)`, `type CapturedCard = {createdAt, text, origin}`, `captureCard(d, key)`, `staleVerdict(d, key, captured) → "apply" | "service_changed" | "edited"`.
  - `defaults.ts`: `DEFAULT_BENEDICTION_FALLBACK = "Halverson"`, `type LiturgyDefaults = {defaultBenediction}`, `applyCommunionDefault(d)`, `applyLiturgyDefaults(d, defaults)`.
  - `summary.ts`: `type LiturgyCounts = {ready, enabled, communion, customCount}`, `liturgyCounts(d)`.
  - Later users: T5 (the store runs `applyLiturgyDefaults`), T6 (`captureCard`, `staleVerdict`, `applyGenerated`, `restoreCard`), T8-T10 (the step), T11 (`liturgyCounts`).

Counts after this task: frontend **455 passed in 68 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/lib/liturgy
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `sections.test.ts` and `sections.ts` (T1's files, one per line); ` Test Files  65 passed (65)`, `      Tests  446 passed (446)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/cards.test.ts`:**

```ts
/**
 * The Liturgy step's draft transitions (slice 4 spec, "Card origin
 * transitions", Frontend `cards.ts`; Testing `cards.test.ts`): every row of
 * the origin table, the selectors, the custom elements and the stale-result
 * rule the generation provider (and later the service reviewer) applies.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { DraftV1, SectionKey } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import {
  addCustomElement,
  applyGenerated,
  captureCard,
  clearCard,
  editCardText,
  needsRegenerateConfirm,
  normalizePlacement,
  PLACEMENT_KEYS,
  removeCustomElement,
  restoreCard,
  restoreChurchDefault,
  restoreCommunionDefault,
  restoreCustomElement,
  sectionsNeedingAi,
  setCardEnabled,
  setCommunion,
  setSermonTitle,
  staleVerdict,
  updateCustomElement,
} from "./cards";

type Outline = { outline: { anchors_after: string[] }[] };

const outline = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/liturgy_outline.json", import.meta.url), "utf-8"),
) as Outline;

function withCard(d: DraftV1, key: SectionKey, patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
}

const card = (d: DraftV1, key: SectionKey) => d.liturgy.cards[key];

describe("card origin transitions (S Frontend changes)", () => {
  it("follows every row of the table, and returns the same draft when nothing changes", () => {
    const d = testDraft();
    // User edits: typed when non-blank after trimming, else empty.
    const typed = editCardText(d, "call_to_worship", "Come, let us worship.");
    expect(card(typed, "call_to_worship")).toEqual({ enabled: true, text: "Come, let us worship.", origin: "typed" });
    expect(card(editCardText(typed, "call_to_worship", "  \n"), "call_to_worship")).toEqual({
      enabled: true,
      text: "  \n",
      origin: "empty",
    });
    expect(editCardText(typed, "call_to_worship", "Come, let us worship.")).toBe(typed);
    // An AI result applied.
    const ai = applyGenerated(typed, "call_to_worship", "Leader: Come!");
    expect(card(ai, "call_to_worship")).toEqual({ enabled: true, text: "Leader: Come!", origin: "ai" });
    // Clear.
    const cleared = clearCard(ai, "call_to_worship");
    expect(card(cleared, "call_to_worship")).toEqual({ enabled: true, text: "", origin: "empty" });
    expect(clearCard(cleared, "call_to_worship")).toBe(cleared);
    // Use church default (Benediction).
    const edited = editCardText(d, "benediction", "Go in peace.");
    expect(card(restoreChurchDefault(edited, "Halverson"), "benediction")).toEqual({
      enabled: true,
      text: "Halverson",
      origin: "default",
    });
    // Undo: previous text and origin.
    expect(card(restoreCard(ai, "call_to_worship", { text: "Come, let us worship.", origin: "typed" }), "call_to_worship")).toEqual(
      card(typed, "call_to_worship"),
    );
    // Switch toggled: text and origin unchanged.
    const off = setCardEnabled(ai, "call_to_worship", false);
    expect(card(off, "call_to_worship")).toEqual({ enabled: false, text: "Leader: Come!", origin: "ai" });
    expect(setCardEnabled(off, "call_to_worship", false)).toBe(off);
  });

  it("sends only switched-on cards with no text to the AI, and confirms before replacing typed or saved text", () => {
    let d = testDraft();
    d = editCardText(d, "call_to_worship", "Come.");
    d = editCardText(d, "opening_prayer", "   ");
    d = setCardEnabled(d, "assurance", false);
    d = withCard(d, "benediction", { text: "Halverson", origin: "default" });
    expect(sectionsNeedingAi(d)).toEqual(["opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"]);
    expect(needsRegenerateConfirm({ enabled: true, text: "Come.", origin: "typed" })).toBe(true);
    expect(needsRegenerateConfirm({ enabled: true, text: "Saved words", origin: "archive" })).toBe(true);
    expect(needsRegenerateConfirm({ enabled: true, text: "Leader: Come!", origin: "ai" })).toBe(false);
    expect(needsRegenerateConfirm({ enabled: true, text: "Halverson", origin: "default" })).toBe(false);
    expect(needsRegenerateConfirm({ enabled: true, text: "  ", origin: "typed" })).toBe(false);
  });
});

describe("the stale-result rule (S Generate and Regenerate, step 6)", () => {
  it("drops a result for a replaced draft or an edited card, and applies it to a card still following the default", () => {
    const d = withCard(testDraft(), "benediction", { text: "Halverson", origin: "default" });
    const captured = captureCard(d, "benediction");
    expect(captured).toEqual({ createdAt: d.created_at, text: "Halverson", origin: "default" });
    expect(staleVerdict(d, "benediction", captured)).toBe("apply");
    expect(staleVerdict({ ...d, created_at: "2026-09-30T12:00:00.000Z" }, "benediction", captured)).toBe("service_changed");
    // The church default changed mid-run: the user asked to replace the default, so apply.
    expect(staleVerdict(withCard(d, "benediction", { text: "Go in peace." }), "benediction", captured)).toBe("apply");
    // Edited in another tab.
    expect(staleVerdict(editCardText(d, "benediction", "My blessing"), "benediction", captured)).toBe("edited");
    const typed = editCardText(d, "opening_prayer", "Gracious God");
    const before = captureCard(typed, "opening_prayer");
    expect(staleVerdict(editCardText(typed, "opening_prayer", "Gracious God, hear us"), "opening_prayer", before)).toBe("edited");
  });
});

describe("communion, the sermon title and custom elements (S Communion card, Custom elements)", () => {
  it("toggles communion as the user's and restores the default, and stores the sermon title as typed", () => {
    const d = testDraft(); // Sunday, October 4, 2026: a first Sunday
    const off = setCommunion(d, false);
    expect(off.liturgy).toMatchObject({ include_communion: false, communion_origin: "user" });
    expect(restoreCommunionDefault(off).liturgy).toMatchObject({ include_communion: true, communion_origin: "default" });
    expect(restoreCommunionDefault(d)).toBe(d);
    expect(setSermonTitle(d, "Living Water").liturgy.sermon_title).toBe("Living Water");
    expect(setSermonTitle(d, "")).toBe(d);
  });

  it("adds, edits, removes and restores custom elements at their index, and normalizes unknown places to end", () => {
    const placements = new Set(outline.outline.flatMap((item) => item.anchors_after));
    expect(new Set(PLACEMENT_KEYS)).toEqual(placements);
    expect(PLACEMENT_KEYS).toHaveLength(17);
    expect(normalizePlacement("sermon")).toBe("sermon");
    expect(normalizePlacement("bogus")).toBe("end");

    let d = testDraft();
    d = addCustomElement(d, { label: "  Children's Moment ", text: " Come forward. ", insert_after: "opening_prayer" }, "a");
    d = addCustomElement(d, { label: "Anthem", text: "", insert_after: "sermon" }, "b");
    d = addCustomElement(d, { label: "Minute for Mission", text: "", insert_after: "bogus" }, "c");
    expect(d.liturgy.custom_elements).toEqual([
      { id: "a", label: "Children's Moment", text: "Come forward.", insert_after: "opening_prayer" },
      { id: "b", label: "Anthem", text: "", insert_after: "sermon" },
      { id: "c", label: "Minute for Mission", text: "", insert_after: "end" },
    ]);
    const moved = updateCustomElement(d, "b", { insert_after: "second_hymn", label: "Choir Anthem" });
    expect(moved.liturgy.custom_elements[1]).toEqual({ id: "b", label: "Choir Anthem", text: "", insert_after: "second_hymn" });
    expect(updateCustomElement(moved, "b", { label: "Choir Anthem" })).toBe(moved);
    const removed = removeCustomElement(moved, "b");
    expect(removed?.index).toBe(1);
    expect(removed?.element.label).toBe("Choir Anthem");
    expect(removed?.draft.liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "c"]);
    expect(removeCustomElement(moved, "zzz")).toBeNull();
    const restored = restoreCustomElement(removed!.draft, removed!.element, removed!.index, 30);
    expect(restored.liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "b", "c"]);
    expect(restoreCustomElement(restored, removed!.element, 1, 30)).toBe(restored); // already back
    expect(restoreCustomElement(removed!.draft, removed!.element, removed!.index, 2)).toBe(removed!.draft); // the list is full
  });
});
```

**Create `frontend/src/lib/liturgy/defaults.test.ts`:**

```ts
/**
 * The liturgy defaults (slice 4 spec, Frontend `defaults.ts`; Testing
 * `defaults.test.ts`): the first-Sunday rule against the shared fixture, and
 * `applyLiturgyDefaults`, which keeps an untouched Benediction on the church
 * default and untouched communion on the date's rule.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { isFirstSundayOfMonth } from "@/lib/dates";
import { setDate } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { editCardText, setCommunion } from "./cards";
import { applyLiturgyDefaults, DEFAULT_BENEDICTION_FALLBACK } from "./defaults";

type Cases = { cases: { date: string; expected: boolean; why: string }[] };

const firstSunday = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/first_sunday.json", import.meta.url), "utf-8"),
) as Cases;

describe("liturgy defaults (S Benediction and the church default; Communion card)", () => {
  it("puts communion on the first Sunday of the month, as the shared fixture says", () => {
    for (const { date, expected, why } of firstSunday.cases) expect(isFirstSundayOfMonth(date), why).toBe(expected);
  });

  it("keeps the Benediction on the church default only while it follows it, including an empty default", () => {
    expect(DEFAULT_BENEDICTION_FALLBACK).toBe("Halverson");
    const fresh = testDraft();
    const filled = applyLiturgyDefaults(fresh, { defaultBenediction: "Halverson" });
    expect(filled.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
    expect(applyLiturgyDefaults(filled, { defaultBenediction: "Halverson" })).toBe(filled);
    const changed = applyLiturgyDefaults(filled, { defaultBenediction: "The Lord bless you and keep you." });
    expect(changed.liturgy.cards.benediction.text).toBe("The Lord bless you and keep you.");
    expect(applyLiturgyDefaults(filled, { defaultBenediction: "" }).liturgy.cards.benediction).toEqual({
      enabled: true,
      text: "",
      origin: "default",
    });
    const edited = editCardText(filled, "benediction", "Go in peace.");
    expect(applyLiturgyDefaults(edited, { defaultBenediction: "Something else" })).toBe(edited);
  });

  it("recomputes communion from the date only while it is the default", () => {
    const d = testDraft(); // October 4, 2026: on
    const moved: DraftV1 = { ...d, readings: { ...d.readings, date_iso: "2026-10-11" } };
    expect(applyLiturgyDefaults(moved, { defaultBenediction: "" }).liturgy.include_communion).toBe(false);
    expect(setDate(d, "2026-10-11").liturgy.include_communion).toBe(false); // the date change applies the same rule
    const chosen = setCommunion(d, true);
    const chosenMoved: DraftV1 = { ...chosen, readings: { ...chosen.readings, date_iso: "2026-10-11" } };
    expect(applyLiturgyDefaults(chosenMoved, { defaultBenediction: "" }).liturgy.include_communion).toBe(true);
  });
});
```

**Create `frontend/src/lib/liturgy/summary.test.ts`:**

```ts
/**
 * `liturgyCounts` (slice 4 spec, Frontend "Builder shell"; Testing
 * `summary.test.ts`): the one count behind the step's status and the summary.
 */
import { describe, expect, it } from "vitest";

import { SECTION_KEYS } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { addCustomElement, editCardText, setCardEnabled, setCommunion } from "./cards";
import { applyLiturgyDefaults } from "./defaults";
import { liturgyCounts } from "./summary";

describe("liturgyCounts (S summary.ts)", () => {
  it("counts enabled cards, those with text, communion and custom elements", () => {
    const fresh = applyLiturgyDefaults(testDraft(), { defaultBenediction: "" }); // a church with no default
    expect(liturgyCounts(fresh)).toEqual({ ready: 0, enabled: 7, communion: true, customCount: 0 });
    // The Benediction following a non-blank church default counts as ready.
    const withDefault = applyLiturgyDefaults(fresh, { defaultBenediction: "Halverson" });
    expect(liturgyCounts(withDefault)).toMatchObject({ ready: 1, enabled: 7 });
    expect(liturgyCounts(editCardText(withDefault, "assurance", "  \n "))).toMatchObject({ ready: 1, enabled: 7 });
    const allOff = SECTION_KEYS.reduce((d, key) => setCardEnabled(d, key, false), withDefault);
    expect(liturgyCounts(allOff)).toMatchObject({ ready: 0, enabled: 0 });
    let d = addCustomElement(setCommunion(withDefault, false), { label: "Anthem", text: "", insert_after: "sermon" }, "a");
    d = addCustomElement(d, { label: "Minute for Mission", text: "", insert_after: "end" }, "b");
    expect(liturgyCounts(d)).toEqual({ ready: 1, enabled: 7, communion: false, customCount: 2 });
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/cards.test.ts src/lib/liturgy/defaults.test.ts src/lib/liturgy/summary.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|Error: Cannot find|Tests ")
```

**Expected:**

```
 FAIL  |unit| src/lib/liturgy/cards.test.ts [ src/lib/liturgy/cards.test.ts ]
Error: Cannot find module './cards' imported from '<repo>/frontend/src/lib/liturgy/cards.test.ts'
 FAIL  |unit| src/lib/liturgy/defaults.test.ts [ src/lib/liturgy/defaults.test.ts ]
Error: Cannot find module './cards' imported from '<repo>/frontend/src/lib/liturgy/defaults.test.ts'
 FAIL  |unit| src/lib/liturgy/summary.test.ts [ src/lib/liturgy/summary.test.ts ]
Error: Cannot find module './cards' imported from '<repo>/frontend/src/lib/liturgy/summary.test.ts'
      Tests  no tests
```

- [ ] **Step 4 (agent): Write `cards.ts`, `defaults.ts` and `summary.ts`, and move the communion rule**

**Create `frontend/src/lib/liturgy/cards.ts`:**

```ts
/**
 * The Liturgy step's draft transitions and selectors (slice 4 spec, Frontend
 * `cards.ts`, "Card origin transitions"; F §4.6 "Card text is the user's").
 * Pure: each transition takes the draft and returns the next one, or the
 * same object when nothing changes, so `update(recipe)` stays a no-op.
 *
 * - Typing sets the origin to "typed", or "empty" when the text is blank
 *   after trimming; an AI result sets "ai"; Clear sets "" and "empty"; "Use
 *   church default" sets the default and "default"; Undo restores the
 *   previous text and origin; a switch changes neither.
 * - `staleVerdict` is the rule for a result that arrives after its request
 *   started (S "Generate and Regenerate" step 6). The generation provider
 *   applies it, and the service reviewer (the slice after 4b) reuses it for
 *   review results: capture the card when the request starts, compare when
 *   the answer arrives.
 */
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
import { SECTION_KEYS } from "@/lib/draft/schema";

import { applyCommunionDefault } from "./defaults";

export type CardOrigin = LiturgyCard["origin"];
export type CardSnapshot = { text: string; origin: CardOrigin };
export type CustomElement = DraftV1["liturgy"]["custom_elements"][number];

/**
 * The 17 custom-element places (backend `liturgy_config.CUSTOM_PLACEMENTS`
 * keys, in order); `cards.test.ts` pins them to the outline fixture's
 * anchors. The labels come from GET /liturgy/config.
 */
export const PLACEMENT_KEYS = [
  "call_to_worship",
  "opening_prayer",
  "first_hymn",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "ot_reading",
  "nt_reading",
  "sermon",
  "affirmation_of_faith",
  "second_hymn",
  "communion",
  "prayers_of_the_people",
  "offertory_prayer",
  "third_hymn",
  "benediction",
  "end",
] as const;

const PLACEMENTS: ReadonlySet<string> = new Set(PLACEMENT_KEYS);

/** A known place unchanged; anything else "end" (never dropped; mirrors `liturgy_config.normalize_placement`). */
export function normalizePlacement(key: string): string {
  return PLACEMENTS.has(key) ? key : "end";
}

function withCard(d: DraftV1, key: SectionKey, next: LiturgyCard): DraftV1 {
  const current = d.liturgy.cards[key];
  if (current.enabled === next.enabled && current.text === next.text && current.origin === next.origin) return d;
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: next } } };
}

function withLiturgy(d: DraftV1, patch: Partial<DraftV1["liturgy"]>): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, ...patch } };
}

/** The user typed: "typed" when non-blank after trimming, else "empty". */
export function editCardText(d: DraftV1, key: SectionKey, text: string): DraftV1 {
  const card = d.liturgy.cards[key];
  return withCard(d, key, { ...card, text, origin: text.trim() === "" ? "empty" : "typed" });
}

export function setCardEnabled(d: DraftV1, key: SectionKey, enabled: boolean): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], enabled });
}

export function applyGenerated(d: DraftV1, key: SectionKey, text: string): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text, origin: "ai" });
}

export function clearCard(d: DraftV1, key: SectionKey): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text: "", origin: "empty" });
}

/** "Use church default" (Benediction): the default's text, following it again. */
export function restoreChurchDefault(d: DraftV1, defaultText: string): DraftV1 {
  return withCard(d, "benediction", { ...d.liturgy.cards.benediction, text: defaultText, origin: "default" });
}

/** Undo: the text and origin kept in memory before a Regenerate or Clear. */
export function restoreCard(d: DraftV1, key: SectionKey, previous: CardSnapshot): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text: previous.text, origin: previous.origin });
}

export function setSermonTitle(d: DraftV1, title: string): DraftV1 {
  return d.liturgy.sermon_title === title ? d : withLiturgy(d, { sermon_title: title });
}

/** The communion switch: the user's choice from now on. */
export function setCommunion(d: DraftV1, include: boolean): DraftV1 {
  const l = d.liturgy;
  if (l.include_communion === include && l.communion_origin === "user") return d;
  return withLiturgy(d, { include_communion: include, communion_origin: "user" });
}

/** "Use default": communion follows the first-Sunday rule for the date again. */
export function restoreCommunionDefault(d: DraftV1): DraftV1 {
  const next = d.liturgy.communion_origin === "default" ? d : withLiturgy(d, { communion_origin: "default" });
  return applyCommunionDefault(next);
}

/** Appends an element with its label and text trimmed and its place normalized (S "On Add"). */
export function addCustomElement(d: DraftV1, element: Omit<CustomElement, "id">, id: string): DraftV1 {
  const added: CustomElement = {
    id,
    label: element.label.trim(),
    text: element.text.trim(),
    insert_after: normalizePlacement(element.insert_after),
  };
  return withLiturgy(d, { custom_elements: [...d.liturgy.custom_elements, added] });
}

export function updateCustomElement(d: DraftV1, id: string, patch: Partial<Omit<CustomElement, "id">>): DraftV1 {
  const list = d.liturgy.custom_elements;
  const at = list.findIndex((e) => e.id === id);
  if (at < 0) return d;
  const next = { ...list[at], ...patch };
  if (next.label === list[at].label && next.text === list[at].text && next.insert_after === list[at].insert_after) return d;
  return withLiturgy(d, { custom_elements: list.map((e, i) => (i === at ? next : e)) });
}

/** Removes the element; null when it is not there. The element and its index are for Undo. */
export function removeCustomElement(
  d: DraftV1,
  id: string,
): { draft: DraftV1; element: CustomElement; index: number } | null {
  const list = d.liturgy.custom_elements;
  const index = list.findIndex((e) => e.id === id);
  if (index < 0) return null;
  return { draft: withLiturgy(d, { custom_elements: list.filter((e) => e.id !== id) }), element: list[index], index };
}

/** Undo of Remove: back at its index (or the end), unless it is already there or the list is full (`max`). */
export function restoreCustomElement(d: DraftV1, element: CustomElement, index: number, max: number): DraftV1 {
  const list = d.liturgy.custom_elements;
  if (list.some((e) => e.id === element.id) || list.length >= max) return d;
  const at = Math.min(Math.max(index, 0), list.length);
  return withLiturgy(d, { custom_elements: [...list.slice(0, at), element, ...list.slice(at)] });
}

// --- selectors ---------------------------------------------------------------

/** Switched-on cards with no text (after trimming), in section order: what "Generate empty sections" sends. */
export function sectionsNeedingAi(d: DraftV1): SectionKey[] {
  return SECTION_KEYS.filter((key) => {
    const card = d.liturgy.cards[key];
    return card.enabled && card.text.trim() === "";
  });
}

/** Regenerate asks first when it would replace the user's own or a saved service's text. */
export function needsRegenerateConfirm(card: LiturgyCard): boolean {
  return (card.origin === "typed" || card.origin === "archive") && card.text.trim() !== "";
}

export type CapturedCard = { createdAt: string; text: string; origin: CardOrigin };

/** What a run remembers when its request starts. */
export function captureCard(d: DraftV1, key: SectionKey): CapturedCard {
  const card = d.liturgy.cards[key];
  return { createdAt: d.created_at, text: card.text, origin: card.origin };
}

export type StaleVerdict = "apply" | "service_changed" | "edited";

/**
 * S step 6, first matching rule: the draft was replaced (New service, an
 * archive load) → "service_changed"; the card followed the church default
 * then and still does → "apply" (the default changed mid-run, and the user
 * asked to replace it); its text changed (an edit in another tab) →
 * "edited"; otherwise "apply".
 */
export function staleVerdict(d: DraftV1, key: SectionKey, captured: CapturedCard): StaleVerdict {
  if (d.created_at !== captured.createdAt) return "service_changed";
  const card = d.liturgy.cards[key];
  if (captured.origin === "default" && card.origin === "default") return "apply";
  if (card.text !== captured.text) return "edited";
  return "apply";
}
```

**Create `frontend/src/lib/liturgy/defaults.ts`:**

```ts
/**
 * The liturgy defaults (slice 4 spec, Frontend `defaults.ts`, "Draft store
 * integration"; F §4.6 "Defaults apply only while origin is `default`"):
 *
 * - A Benediction card whose origin is "default" shows the church's
 *   `default_benediction` (GET /church; "Halverson" when an older API leaves it
 *   out), including "" (no default: the card is empty).
 * - Communion whose origin is "default" follows the first-Sunday rule for the
 *   draft's date (`isFirstSundayOfMonth`, slice 2's port of
 *   `liturgy_config.is_first_sunday_of_month`, run against
 *   shared/first_sunday.json in `defaults.test.ts`). This is the one place for
 *   the rule: `date-effects.ts` calls `applyCommunionDefault` on a date change.
 *
 * Both return the same object when nothing changes, so the draft store can
 * run them after every change without writing.
 */
import { isFirstSundayOfMonth } from "@/lib/dates";
import type { DraftV1 } from "@/lib/draft/schema";

export const DEFAULT_BENEDICTION_FALLBACK = "Halverson";

export type LiturgyDefaults = { defaultBenediction: string };

export function applyCommunionDefault(d: DraftV1): DraftV1 {
  if (d.liturgy.communion_origin !== "default") return d;
  const include = isFirstSundayOfMonth(d.readings.date_iso);
  if (include === d.liturgy.include_communion) return d;
  return { ...d, liturgy: { ...d.liturgy, include_communion: include } };
}

export function applyLiturgyDefaults(d: DraftV1, { defaultBenediction }: LiturgyDefaults): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
  let next = d;
  if (benediction.origin === "default" && benediction.text !== defaultBenediction) {
    next = {
      ...d,
      liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { ...benediction, text: defaultBenediction } } },
    };
  }
  return applyCommunionDefault(next);
}
```

**Create `frontend/src/lib/liturgy/summary.ts`:**

```ts
/**
 * The liturgy counts behind the step bar's status and the summary (slice 4
 * spec, Frontend "Builder shell" `summary.ts`), one function so they cannot
 * disagree: `enabled` = cards switched on; `ready` = those whose text is
 * non-blank after trimming; `communion` = `include_communion`;
 * `customCount` = the custom elements.
 */
import { SECTION_KEYS, type DraftV1 } from "@/lib/draft/schema";

export type LiturgyCounts = { ready: number; enabled: number; communion: boolean; customCount: number };

export function liturgyCounts(d: DraftV1): LiturgyCounts {
  const enabled = SECTION_KEYS.map((key) => d.liturgy.cards[key]).filter((card) => card.enabled);
  return {
    ready: enabled.filter((card) => card.text.trim() !== "").length,
    enabled: enabled.length,
    communion: d.liturgy.include_communion,
    customCount: d.liturgy.custom_elements.length,
  };
}
```

**In `frontend/src/lib/draft/date-effects.ts`, replace:**

```ts
 * Slice 2: while `communion_origin` is `default`, `include_communion` follows
 * the first-Sunday rule for the new date (false for a weekday). Slice 3 adds
 * its hymn effect here (for example, dropping `alternatives` for another
 * date); slice 4 may move the communion rule into `applyLiturgyDefaults`.
 * Returns `d` itself when nothing changes.
 */
import { isFirstSundayOfMonth } from "@/lib/dates";

import type { DraftV1 } from "./schema";

// `prevIso` is kept in the signature for slice 3's hymn effect.
export function onDateChanged(d: DraftV1, prevIso: string): DraftV1 {
  void prevIso;
  if (d.liturgy.communion_origin !== "default") return d;
  const include = isFirstSundayOfMonth(d.readings.date_iso);
  if (include === d.liturgy.include_communion) return d;
  return { ...d, liturgy: { ...d.liturgy, include_communion: include } };
```

**with:**

```ts
 * While `communion_origin` is `default`, `include_communion` follows the
 * first-Sunday rule for the new date (false for a weekday). The rule lives in
 * `lib/liturgy/defaults.ts` (`applyCommunionDefault`, slice 4b), which the
 * draft store also runs after every change. Slice 3 adds no hymn effect here
 * (its ideas carry their own date). Returns `d` itself when nothing changes.
 */
import { applyCommunionDefault } from "@/lib/liturgy/defaults";

import type { DraftV1 } from "./schema";

// `prevIso` is kept in the signature for a later date effect.
export function onDateChanged(d: DraftV1, prevIso: string): DraftV1 {
  void prevIso;
  return applyCommunionDefault(d);
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy src/lib/draft 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  13 passed (13)`, `      Tests  66 passed (66)`; the suite ` Test Files  68 passed (68)`, `      Tests  455 passed (455)`; `typecheck 0` and `lint 0`; ` M frontend/src/lib/draft/date-effects.ts` and the six new files under `frontend/src/lib/liturgy/` as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/cards.ts frontend/src/lib/liturgy/cards.test.ts frontend/src/lib/liturgy/defaults.ts frontend/src/lib/liturgy/defaults.test.ts frontend/src/lib/liturgy/summary.ts frontend/src/lib/liturgy/summary.test.ts frontend/src/lib/draft/date-effects.ts
git commit -m "Liturgy: card transitions, the Benediction and communion defaults, and the counts (S cards.ts, defaults.ts, summary.ts)" -m "Pure draft transitions for every row of the slice 4 origin table, the
communion switch and Use default, the sermon title and custom elements
(trimmed, restored at their index, unknown places read as end), the
selectors for Generate empty sections and Regenerate, and the stale-result
rule. applyLiturgyDefaults keeps an untouched Benediction on the church
default and untouched communion on the first-Sunday rule, which moves out
of date-effects.ts. liturgyCounts backs the status and the summary.
Frontend 446 -> 455 tests in 65 -> 68 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

**Review checkpoint (T1-T2, batch A):** `isPristine` counts exactly owner answer 1's fields and nothing transient; every S origin row has a test; the stale rule's order matches S step 6; the communion rule has one home; counts match.

### Task 3: The request body, the card errors and the queue (S Frontend `request.ts`, `errors.ts`, `queue.ts`, "Sermon text", "Per-card error messages"; BC-24; clarifications 7, 8, 9, 29)

The rest of the pure half. `request.ts` builds one section's `POST /liturgy/generate` body from the draft exactly as S's `request.ts` row says (one section, no `overrides`, the ServiceDraft limits, the three slots as `HymnRef`s) and works out which passage is the sermon text (`sermonSource`: the effective NT reading, the draft's or church's translation, WEB for ESV) and its `{ref, text}` (`sermonText`); the fetch itself is T6's. An id that is not a UUID goes as `null`, because the API validates `hymn_id` as a UUID and would reject the whole request (clarification 7). `errors.ts` turns a section's failure or a failed request into what the card shows, with S's copy; a cancel, a 401 and a lost church show nothing on the card (clarification 8), and the 404's link is labelled "Go to Hymns" (clarification 9). `queue.ts` runs at most 3 tasks, first in first out; a cancelled task's outcome is never delivered, a task cancelled before its `run` was called never runs, and each outcome is delivered before the next task starts, so a 429 can stop the waiting ones (clarification 29). The generated type names join `lib/api/types.ts`.

**Files:**
- Create: `frontend/src/lib/liturgy/request.ts`, `frontend/src/lib/liturgy/errors.ts`, `frontend/src/lib/liturgy/queue.ts`
- Modify: `frontend/src/lib/api/types.ts` (the liturgy type names)
- Test: `frontend/src/lib/liturgy/request.test.ts` (new, 3), `frontend/src/lib/liturgy/errors.test.ts` (new, 2), `frontend/src/lib/liturgy/queue.test.ts` (new, 4)

**Interfaces:**
- Consumes: the generated `LiturgyConfigOut`, `GenerateLiturgyIn`/`Out`, `SectionResult`, `SectionError`, `SermonText`, `HymnRef` (4a's `schema.d.ts`, unchanged); `effectivePicks` (2c); `clipChars`, `cleanRefs`, `MAX_REFS`, `MAX_REF_LENGTH` (3b `lib/hymns/match-request.ts`); `passageText` (2c); `ApiError`, `describeError`, `isNoChurchAccess` (1, 2).
- Produces:
  - `lib/api/types.ts`: `LiturgyConfig`, `LiturgySection`, `OutlineItem`, `CommunionBlock`, `GenerateLiturgyBody`, `GenerateLiturgyResult`, `SectionResult`, `SectionError`, `SermonText`, `HymnRef`.
  - `request.ts`: `MAX_OCCASION`, `MAX_HYMN_TITLE`, `MAX_HYMNAL`, `MAX_SERMON_TEXT`, `buildGenerateRequest(draft, section, sermon: SermonText | null)`, `sermonSource(draft, churchTranslation) → {ref, translation} | null`, `sermonText(ref, passage | undefined) → SermonText | null`.
  - `errors.ts`: `type CardError = {code, message, retryable, retryAfterSeconds?, link?}`, `AI_NOT_CONFIGURED_MESSAGE`, `localAiNotConfigured()`, `cardErrorFrom(e) → CardError | null`.
  - `queue.ts`: `type TaskOutcome<T>`, `type TaskQueue = {push(key, run, done), cancel(key), cancelAll(), runningKeys(), waitingKeys()}`, `createTaskQueue({concurrency})` (the outcome before the next start).
  - Later users: T4 (the fixtures use the type names), T6 (all of it).

Counts after this task: frontend **464 passed in 71 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "LiturgyConfig" frontend/src/lib/api/types.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  68 passed (68)`, `      Tests  455 passed (455)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/request.test.ts`:**

```ts
/**
 * The `POST /liturgy/generate` body (slice 4 spec, Frontend `request.ts`,
 * "Sermon text"; Testing `request.test.ts`; port-ledger target for
 * streamlit_tests/test_app_helpers.py::test_sermon_text_*): one section, no
 * overrides, the ServiceDraft limits, slot-keyed hymns, and the sermon text
 * from the effective NT reading, never from an ESV passage.
 */
import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";
import { editScriptureLines, setPick, setTranslation } from "@/lib/draft/readings";
import type { DraftV1, HymnPick } from "@/lib/draft/schema";
import { hymnId, testDraft } from "@/test/fixtures";

import { buildGenerateRequest, MAX_SERMON_TEXT, sermonSource, sermonText } from "./request";

const OCT_4 = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

function withReadings(lines: string[], occasion = "Nineteenth Sunday after Pentecost"): DraftV1 {
  const d = editScriptureLines(testDraft(), lines.join("\n"));
  return { ...d, readings: { ...d.readings, occasion } };
}

function passage(ref: string, texts: (string | null)[]): Passage {
  return {
    reference: ref,
    status: texts.every((t) => t !== null) ? "ok" : "unavailable",
    sections: texts.map((text, i) => ({ reference: `${ref} (${i + 1})`, status: text === null ? "unavailable" : "ok", text })),
  };
}

describe("buildGenerateRequest (S request.ts)", () => {
  it("sends one section, no overrides, the readings within the limits and the three slots as HymnRefs", () => {
    const pick = (n: number, patch: Partial<HymnPick> = {}): HymnPick => ({
      hymn_id: hymnId(n),
      title: `Hymn ${n}`,
      number: n,
      hymnal: "GG2013",
      ...patch,
    });
    let d = withReadings(["  Isaiah 5:1-7  ", "", ...Array.from({ length: 21 }, (_, i) => `Psalm ${i + 1}`)], ` ${"o".repeat(305)} `);
    d = editScriptureLines(d, [...d.readings.scriptures.slice(0, 2), "x".repeat(205), ...d.readings.scriptures.slice(2)].join("\n"));
    d = {
      ...d,
      hymns: {
        ...d.hymns,
        slots: { opening: pick(403, { title: "t".repeat(301) }), response: null, closing: pick(0, { hymn_id: null, number: null, hymnal: null }) },
      },
    };
    const body = buildGenerateRequest(d, "call_to_worship", null);
    expect(body.sections).toEqual(["call_to_worship"]);
    expect(body).not.toHaveProperty("overrides");
    expect(body).not.toHaveProperty("sermon_text");
    expect(body.occasion).toBe("o".repeat(300));
    expect(body.scriptures).toHaveLength(20);
    expect(body.scriptures?.slice(0, 3)).toEqual(["Isaiah 5:1-7", "x".repeat(200), "Psalm 1"]);
    expect(body.hymns).toEqual({
      opening: { hymn_id: hymnId(403), title: "t".repeat(300), number: 403, hymnal: "GG2013" },
      response: null,
      closing: { hymn_id: null, title: "Hymn 0", number: null, hymnal: null },
    });
    // An id the API would reject (not a UUID) goes as a snapshot, with its own title.
    const odd = { ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, response: pick(12, { hymn_id: "h12" }) } } };
    expect(buildGenerateRequest(odd, "benediction", null).hymns?.response).toEqual({
      hymn_id: null,
      title: "Hymn 12",
      number: 12,
      hymnal: "GG2013",
    });
  });

  it("adds the sermon text when there is one, cut to 20 000 characters", () => {
    const d = withReadings(OCT_4);
    const body = buildGenerateRequest(d, "opening_prayer", { ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" });
    expect(body.sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" });
    expect(sermonText("Philippians 3:4b-14", passage("Philippians 3:4b-14", ["a".repeat(20_005)]))?.text).toHaveLength(MAX_SERMON_TEXT);
    expect(sermonText("Mark 4:35-41", passage("Mark 4:35-41", ["Waves.", null, "Wind."]))).toEqual({
      ref: "Mark 4:35-41",
      text: "Waves.\n\nWind.",
    });
    expect(sermonText("Mark 4:35-41", passage("Mark 4:35-41", [null]))).toBeNull();
    expect(sermonText("Mark 4:35-41", undefined)).toBeNull();
  });
});

describe("sermonSource (S Sermon text)", () => {
  it("is the effective NT reading, never a Psalm, in the draft's translation with WEB for ESV", () => {
    expect(sermonSource(testDraft(), "web")).toBeNull(); // no readings
    expect(sermonSource(withReadings(["Psalm 23"]), "web")).toBeNull(); // a Psalm is never the NT reading
    const d = withReadings(OCT_4);
    expect(sermonSource(d, "web")).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // the automatic pick
    expect(sermonSource(setPick(d, "nt", "Matthew 21:33-46"), "kjv")).toEqual({ ref: "Matthew 21:33-46", translation: "kjv" });
    expect(sermonSource(d, "esv")).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // Crossway's terms
    expect(sermonSource(setTranslation(d, "esv", "web"), "web")?.translation).toBe("web");
    expect(sermonSource(setTranslation(d, "kjv", "web"), "web")?.translation).toBe("kjv");
  });
});
```

**Create `frontend/src/lib/liturgy/errors.test.ts`:**

```ts
/**
 * The card's error for each code (slice 4 spec, "Per-card error messages";
 * Testing `errors.test.ts`): the server's section messages, the client's own,
 * which ones offer Try again, and the ones that show nothing on the card.
 */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { cardErrorFrom, localAiNotConfigured } from "./errors";

describe("cardErrorFrom (S errors.ts)", () => {
  it("shows the server's message for each section error, with Try again only where trying again can help", () => {
    const cases: [string, string, boolean][] = [
      ["ai_not_configured", "AI not configured. Type this section yourself.", false],
      ["ai_busy", "The AI service is busy. Try again in a minute.", true],
      ["ai_timeout", "The AI took too long to answer. Try again.", true],
      ["ai_upstream_error", "The AI service had a problem. Try again.", true],
      [
        "prompt_invalid",
        "The Call to Worship prompt in Settings has a problem: Placeholders need a name, such as {occasion}. An admin can fix it under Settings → Liturgy prompts.",
        false,
      ],
    ];
    for (const [code, message, retryable] of cases) {
      expect(cardErrorFrom({ code, message } as never), code).toEqual({ code, message, retryable });
    }
    // The local error used when the config says AI is off has exactly the server's text.
    expect(localAiNotConfigured()).toEqual({ code: "ai_not_configured", message: cases[0][1], retryable: false });
  });

  it("words the request errors as S's table, and shows nothing for a cancel, a sign-out or a lost church", () => {
    const hymn = cardErrorFrom(
      new ApiError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."),
    );
    expect(hymn).toEqual({
      code: "not_found",
      message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
      retryable: false,
      link: { href: "/builder/hymns", label: "Go to Hymns" },
    });
    expect(
      cardErrorFrom(new ApiError(429, "rate_limited", "Too many requests. Try again in 37 seconds.", { retryAfterSeconds: 37 })),
    ).toEqual({ code: "rate_limited", message: "Too many requests — try again in 37 s.", retryable: true, retryAfterSeconds: 37 });
    expect(cardErrorFrom(new ApiError(0, "timeout", "This is taking too long. Try again."))).toEqual({
      code: "timeout",
      message: "This is taking too long. Try again.",
      retryable: true,
    });
    expect(cardErrorFrom(new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again."))).toEqual({
      code: "network_error",
      message: "Can't reach the server. Check your connection and try again.",
      retryable: true,
    });
    expect(
      cardErrorFrom(new ApiError(500, "internal_error", "Something went wrong.", { requestId: "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4" })),
    ).toEqual({ code: "internal_error", message: "Something went wrong. (Ref: 4f9a2c1e)", retryable: true });
    expect(cardErrorFrom(new ApiError(0, "aborted", "The request was cancelled."))).toBeNull();
    expect(cardErrorFrom(new ApiError(401, "unauthenticated", "Sign in again."))).toBeNull();
    expect(
      cardErrorFrom(new ApiError(403, "forbidden", "No access.", { details: { reason: "no_church_access" } })),
    ).toBeNull();
    expect(cardErrorFrom(new Error("boom"))).toEqual({ code: "unknown", message: "Something went wrong.", retryable: true });
  });
});
```

**Create `frontend/src/lib/liturgy/queue.test.ts`:**

```ts
/**
 * The generation queue (slice 4 spec, Frontend `queue.ts`; Testing
 * `queue.test.ts`): at most 3 running, first in first out, and a cancelled
 * task's signal aborts and its outcome is never delivered.
 */
import { describe, expect, it } from "vitest";

import { createTaskQueue, type TaskOutcome } from "./queue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function tick(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

function harness(concurrency = 3) {
  const queue = createTaskQueue({ concurrency });
  const started: string[] = [];
  const signals = new Map<string, AbortSignal>();
  const tasks = new Map<string, ReturnType<typeof deferred<string>>>();
  const outcomes: [string, TaskOutcome<string>][] = [];
  const push = (key: string) => {
    const task = deferred<string>();
    tasks.set(key, task);
    queue.push(
      key,
      (signal) => {
        started.push(key);
        signals.set(key, signal);
        return task.promise;
      },
      (outcome) => outcomes.push([key, outcome]),
    );
  };
  return { queue, started, signals, tasks, outcomes, push };
}

describe("createTaskQueue (S queue.ts)", () => {
  it("runs at most 3 at once, in the order pushed, and delivers each outcome", async () => {
    const h = harness();
    for (const key of ["a", "b", "c", "d", "e"]) h.push(key);
    await tick();
    expect(h.started).toEqual(["a", "b", "c"]);
    expect(h.queue.runningKeys()).toEqual(["a", "b", "c"]);
    expect(h.queue.waitingKeys()).toEqual(["d", "e"]);
    h.tasks.get("b")!.resolve("B");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "d"]);
    h.tasks.get("a")!.reject(new Error("no"));
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "d", "e"]);
    expect(h.outcomes).toEqual([
      ["b", { ok: true, value: "B" }],
      ["a", { ok: false, error: new Error("no") }],
    ]);
  });

  it("cancel aborts a running task or drops a waiting one, and neither outcome is delivered", async () => {
    const h = harness();
    for (const key of ["a", "b", "c", "d"]) h.push(key);
    await tick();
    expect(h.queue.cancel("d")).toBe(true); // waiting: never starts
    expect(h.queue.cancel("b")).toBe(true); // running: its signal aborts
    expect(h.signals.get("b")?.aborted).toBe(true);
    expect(h.queue.cancel("zzz")).toBe(false);
    h.tasks.get("b")!.resolve("late");
    await tick();
    expect(h.outcomes).toEqual([]);
    expect(h.started).toEqual(["a", "b", "c"]);
    expect(h.queue.runningKeys()).toEqual(["a", "c"]);
    h.push("e");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "e"]); // b's slot freed at once
    // A task cancelled as soon as it got a slot, before its run was called, never runs.
    h.queue.cancel("c");
    h.push("f");
    h.queue.cancel("f");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "e"]);
  });

  it("delivers an outcome before the next task starts, so it can stop the waiting ones", async () => {
    const queue = createTaskQueue({ concurrency: 1 });
    const started: string[] = [];
    const run = (key: string) => () => {
      started.push(key);
      return key === "x" ? Promise.reject(new Error("429")) : new Promise<string>(() => {});
    };
    // As the provider does on a 429: the failed task's outcome cancels every waiting one.
    queue.push("x", run("x"), () => {
      for (const key of queue.waitingKeys()) queue.cancel(key);
    });
    queue.push("y", run("y"), () => {});
    await tick();
    expect(started).toEqual(["x"]);
    expect(queue.waitingKeys()).toEqual([]);
  });

  it("cancelAll aborts every running task and drops every waiting one", async () => {
    const h = harness(2);
    for (const key of ["a", "b", "c"]) h.push(key);
    await tick();
    h.queue.cancelAll();
    expect([h.signals.get("a")?.aborted, h.signals.get("b")?.aborted]).toEqual([true, true]);
    for (const task of h.tasks.values()) task.resolve("late");
    await tick();
    expect(h.outcomes).toEqual([]);
    expect(h.started).toEqual(["a", "b"]);
    expect([h.queue.runningKeys(), h.queue.waitingKeys()]).toEqual([[], []]);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/request.test.ts src/lib/liturgy/errors.test.ts src/lib/liturgy/queue.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|Error: Cannot find|Tests ")
```

**Expected:**

```
 FAIL  |unit| src/lib/liturgy/errors.test.ts [ src/lib/liturgy/errors.test.ts ]
Error: Cannot find module './errors' imported from '<repo>/frontend/src/lib/liturgy/errors.test.ts'
 FAIL  |unit| src/lib/liturgy/queue.test.ts [ src/lib/liturgy/queue.test.ts ]
Error: Cannot find module './queue' imported from '<repo>/frontend/src/lib/liturgy/queue.test.ts'
 FAIL  |unit| src/lib/liturgy/request.test.ts [ src/lib/liturgy/request.test.ts ]
Error: Cannot find module './request' imported from '<repo>/frontend/src/lib/liturgy/request.test.ts'
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the type names, `request.ts`, `errors.ts` and `queue.ts`**

**In `frontend/src/lib/api/types.ts`, replace:**

```ts
export type SuggestedHymn = components["schemas"]["SuggestedHymnOut"];

```

**with:**

```ts
export type SuggestedHymn = components["schemas"]["SuggestedHymnOut"];

/** `GET /liturgy/config` (slice 4a): the sections, custom places, order of worship, communion text, limits and `ai_available`. */
export type LiturgyConfig = components["schemas"]["LiturgyConfigOut"];
export type LiturgySection = components["schemas"]["SectionSpecOut"];
export type OutlineItem = components["schemas"]["OutlineItemOut"];
export type CommunionBlock = components["schemas"]["CommunionBlockOut"];
/** `POST /liturgy/generate` (slice 4a): the body the step sends (one section, no overrides) and the answer. */
export type GenerateLiturgyBody = components["schemas"]["GenerateLiturgyIn"];
export type GenerateLiturgyResult = components["schemas"]["GenerateLiturgyOut"];
export type SectionResult = components["schemas"]["SectionResult"];
/** A section's failure inside the 200 (the declared deviation from F §1.5). */
export type SectionError = components["schemas"]["SectionError"];
/** The effective NT reading and its text, never ESV (shared with the reviewer's routes). */
export type SermonText = components["schemas"]["SermonText"];
export type HymnRef = components["schemas"]["HymnRef"];

```

**Create `frontend/src/lib/liturgy/request.ts`:**

```ts
/**
 * The `POST /liturgy/generate` body (slice 4 spec, Frontend `request.ts`,
 * "Sermon text"; API §Schemas). Pure.
 *
 * - One section per request (the UI never batches sections into one call) and
 *   no `overrides`: typed cards are never sent at all.
 * - The occasion trimmed and cut to 300; the scriptures trimmed, blanks
 *   dropped, the first 20, each cut to 200 (the ServiceDraft limits); every
 *   cut counts characters as the server does (`clipChars`).
 * - `hymns`: the three slots as `HymnRef`s, each title cut to 300 and hymnal
 *   to 20. An id that is not a UUID (which the API would reject for the
 *   whole request) goes as `null`, so the pick's own title is used.
 * - `sermon_text`: the effective NT reading's passage, from `sermonSource`
 *   and the batch's one passage fetch (T6); left out when there is none.
 */
import type { GenerateLiturgyBody, HymnRef, Passage, SermonText } from "@/lib/api/types";
import { effectivePicks } from "@/lib/draft/readings";
import type { DraftV1, HymnPick, SectionKey } from "@/lib/draft/schema";
import { cleanRefs, clipChars, MAX_REF_LENGTH, MAX_REFS } from "@/lib/hymns/match-request";
import { passageText } from "@/lib/queries/passages";

export const MAX_OCCASION = 300;
export const MAX_HYMN_TITLE = 300;
export const MAX_HYMNAL = 20;
export const MAX_SERMON_TEXT = 20_000;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function hymnRef(pick: HymnPick | null): HymnRef | null {
  if (pick === null) return null;
  const number = pick.number !== null && pick.number >= 0 && pick.number <= 100_000 ? pick.number : null;
  return {
    hymn_id: pick.hymn_id !== null && UUID.test(pick.hymn_id) ? pick.hymn_id : null,
    title: clipChars(pick.title, MAX_HYMN_TITLE),
    number,
    hymnal: pick.hymnal === null ? null : clipChars(pick.hymnal, MAX_HYMNAL),
  };
}

export function buildGenerateRequest(draft: DraftV1, section: SectionKey, sermon: SermonText | null): GenerateLiturgyBody {
  const r = draft.readings;
  const slots = draft.hymns.slots;
  const body: GenerateLiturgyBody = {
    occasion: clipChars(r.occasion.trim(), MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
    hymns: { opening: hymnRef(slots.opening), response: hymnRef(slots.response), closing: hymnRef(slots.closing) },
    sections: [section],
  };
  if (sermon !== null) body.sermon_text = sermon;
  return body;
}

/**
 * Which passage the sermon text is: the effective NT reading (the explicit
 * pick, else the automatic one; never a Psalm), in the draft's translation or
 * the church's, with WEB instead of ESV (Crossway's terms: ESV text is never
 * sent to the AI). `ref` is the reading as the passage cache keys it.
 */
export function sermonSource(draft: DraftV1, churchTranslation: string): { ref: string; translation: string } | null {
  const nt = effectivePicks(draft).nt;
  if (nt === null || clipChars(nt.trim(), MAX_REF_LENGTH) === "") return null;
  const translation = draft.readings.translation ?? churchTranslation;
  return { ref: nt, translation: translation === "esv" ? "web" : translation };
}

/** `sermon_text` from a loaded passage: the reference cut to 200, the text to 20 000; null without text. */
export function sermonText(ref: string, passage: Passage | undefined): SermonText | null {
  const text = passage ? passageText(passage) : null;
  if (text === null) return null;
  return { ref: clipChars(ref.trim(), MAX_REF_LENGTH), text: clipChars(text, MAX_SERMON_TEXT) };
}
```

**Create `frontend/src/lib/liturgy/errors.ts`:**

```ts
/**
 * What a card shows when its section could not be written (slice 4 spec,
 * "Per-card error messages", Frontend `errors.ts`; F §1.5: the client chooses
 * by `code` only). Two sources funnel through `cardErrorFrom`: a section's
 * failure inside the 200 (`SectionError`, whose message the server wrote)
 * and a failed request (`ApiError`).
 *
 * `null` means the card shows nothing: a cancel (the card returns to where it
 * was), and a 401 or a lost church, which the app's global handling already
 * acts on (sign-out, another church).
 */
import { ApiError } from "@/lib/api/client";
import { describeError, isNoChurchAccess } from "@/lib/api/errors";
import type { SectionError } from "@/lib/api/types";

export type CardError = {
  code: string;
  message: string;
  /** Shows "Try again". */
  retryable: boolean;
  /** A 429's wait: Try again is enabled after it. */
  retryAfterSeconds?: number;
  link?: { href: string; label: string };
};

export const AI_NOT_CONFIGURED_MESSAGE = "AI not configured. Type this section yourself.";

const RETRYABLE_SECTION_CODES: ReadonlySet<string> = new Set(["ai_busy", "ai_timeout", "ai_upstream_error"]);

/** The error marked on a card locally when the config says AI is off; the same text as the server's. */
export function localAiNotConfigured(): CardError {
  return { code: "ai_not_configured", message: AI_NOT_CONFIGURED_MESSAGE, retryable: false };
}

function isSectionError(e: unknown): e is SectionError {
  return (
    typeof e === "object" && e !== null && !(e instanceof Error) && typeof (e as SectionError).code === "string" &&
    typeof (e as SectionError).message === "string"
  );
}

export function cardErrorFrom(e: unknown): CardError | null {
  if (isSectionError(e)) return { code: e.code, message: e.message, retryable: RETRYABLE_SECTION_CODES.has(e.code) };
  if (!(e instanceof ApiError)) return { code: "unknown", message: "Something went wrong.", retryable: true };
  if (e.code === "aborted" || e.status === 401 || isNoChurchAccess(e)) return null;
  switch (e.code) {
    case "not_found":
      return {
        code: e.code,
        message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        retryable: false,
        link: { href: "/builder/hymns", label: "Go to Hymns" },
      };
    case "rate_limited":
      return e.retryAfterSeconds === undefined
        ? { code: e.code, message: e.message, retryable: true }
        : {
            code: e.code,
            message: `Too many requests — try again in ${e.retryAfterSeconds} s.`,
            retryable: true,
            retryAfterSeconds: e.retryAfterSeconds,
          };
    case "ai_not_configured":
    case "prompt_invalid":
      return { code: e.code, message: e.message, retryable: false };
    default:
      // timeout and network_error carry their own full sentences; a 5xx reads "Something went wrong. (Ref: …)".
      return { code: e.code, message: e.status >= 500 ? describeError(e) : e.message, retryable: true };
  }
}
```

**Create `frontend/src/lib/liturgy/queue.ts`:**

```ts
/**
 * The generation queue (slice 4 spec, Frontend `queue.ts`; "Generate empty
 * sections": at most 3 in flight, which leaves one of the server's 4 AI slots
 * free). First in, first out; each task gets its own `AbortController`.
 * `cancel(key)` aborts a running task or drops a waiting one, frees its slot
 * at once, and its outcome is never delivered; a task cancelled before its
 * `run` was called never runs. A task's outcome is delivered before the next
 * task starts, so `done` can still cancel the waiting ones (S step 7: a 429
 * stops the queue).
 */
export type TaskOutcome<T> = { ok: true; value: T } | { ok: false; error: unknown };

export type TaskQueue = {
  push<T>(key: string, run: (signal: AbortSignal) => Promise<T>, done: (outcome: TaskOutcome<T>) => void): void;
  /** False when the key is neither waiting nor running. */
  cancel(key: string): boolean;
  cancelAll(): void;
  runningKeys(): string[];
  waitingKeys(): string[];
};

type Task = { key: string; start: () => void; controller: AbortController };

export function createTaskQueue({ concurrency }: { concurrency: number }): TaskQueue {
  const waiting: Task[] = [];
  const running = new Map<string, Task>();

  function pump(): void {
    while (running.size < concurrency && waiting.length > 0) {
      const task = waiting.shift() as Task;
      running.set(task.key, task);
      task.start();
    }
  }

  function cancel(key: string): boolean {
    const at = waiting.findIndex((t) => t.key === key);
    if (at >= 0) {
      waiting.splice(at, 1);
      return true;
    }
    const task = running.get(key);
    if (!task) return false;
    running.delete(key);
    task.controller.abort();
    pump();
    return true;
  }

  return {
    push<T>(key: string, run: (signal: AbortSignal) => Promise<T>, done: (outcome: TaskOutcome<T>) => void) {
      cancel(key);
      const controller = new AbortController();
      const task: Task = {
        key,
        controller,
        start: () => {
          const settle = (outcome: TaskOutcome<T>) => {
            if (controller.signal.aborted || running.get(key) !== task) return;
            running.delete(key);
            try {
              done(outcome);
            } finally {
              pump();
            }
          };
          Promise.resolve()
            .then(() => (controller.signal.aborted ? Promise.reject(controller.signal.reason) : run(controller.signal)))
            .then(
              (value: T) => settle({ ok: true, value }),
              (error: unknown) => settle({ ok: false, error }),
            );
        },
      };
      waiting.push(task);
      pump();
    },
    cancel,
    cancelAll() {
      waiting.length = 0;
      for (const task of running.values()) task.controller.abort();
      running.clear();
    },
    runningKeys: () => [...running.keys()],
    waitingKeys: () => waiting.map((t) => t.key),
  };
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  7 passed (7)`, `      Tests  19 passed (19)`; the suite ` Test Files  71 passed (71)`, `      Tests  464 passed (464)`; `typecheck 0` and `lint 0`; ` M frontend/src/lib/api/types.ts` and six new files under `frontend/src/lib/liturgy/` as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/liturgy/request.ts frontend/src/lib/liturgy/request.test.ts frontend/src/lib/liturgy/errors.ts frontend/src/lib/liturgy/errors.test.ts frontend/src/lib/liturgy/queue.ts frontend/src/lib/liturgy/queue.test.ts
git commit -m "Liturgy: the generate request, the card errors and the three-at-a-time queue (S request.ts, errors.ts, queue.ts)" -m "buildGenerateRequest sends one section and no overrides, within the
ServiceDraft limits, with the three slots as HymnRefs (a non-UUID id goes
as a snapshot). sermonSource picks the effective NT reading in the draft's
translation, WEB for ESV; sermonText cuts it to 20 000 characters.
cardErrorFrom words every code as the slice 4 table does and shows nothing
for a cancel, a 401 or a lost church. createTaskQueue runs at most 3,
first in first out, never delivers a cancelled task's outcome, and hands
each outcome over before the next task starts.
Frontend 455 -> 464 tests in 68 -> 71 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

### Task 4: The liturgy queries, the 100-second timeout, and the test fixtures (S "API client usage", "Sermon text" loading; F §4.4, §1.8; owner answer 2; clarifications 10, 11, 12)

The API side of the step. `lib/queries/liturgy.ts` holds `useLiturgyConfig()` (user-scoped reference data, never stale) and `generateSection()` (one church-scoped `POST /liturgy/generate`, returning that section's result; S passes the draft, this takes the built body, clarification 10). The client timeout for that route is 100 000 ms, owner answer 2: `lib/api/timeouts.ts` keeps per-route timeouts in its `ENDPOINT_TIMEOUTS` table (there is no `TIMEOUTS` object; clarification 11), so the row is `"POST /liturgy/generate": 100_000`. `passages.ts` exports `passageQuery()`, the options `usePassage` already used, so T6 can `fetchQuery` the sermon text through the same key, limiter and freshness. `client.ts` exports `reportAuthErrors(error, churchId)`, the logic `handleAuthErrors` runs for the caches, so a call made outside them (the generation queue) signs out on a 401 and falls back on a lost church the same way (clarification 12). The test fixtures gain `liturgyConfig()` (pinned to 4a's shared fixtures), `sectionResult()`, `sectionFailure()` and `generateRoute()`.

**Files:**
- Create: `frontend/src/lib/queries/liturgy.ts`
- Modify: `frontend/src/lib/api/timeouts.ts` (the 100 s row), `frontend/src/lib/queries/client.ts` (`reportAuthErrors`), `frontend/src/lib/queries/passages.ts` (`passageQuery`), `frontend/src/test/fixtures/index.ts` (the liturgy builders)
- Test: `frontend/src/lib/queries/liturgy.test.tsx` (new, 3), `frontend/src/lib/queries/client.test.ts` (+1). 2c's passage tests keep pinning `usePassage`.

**Interfaces:**
- Consumes: T3's type names; `keys.liturgyConfig()` (1; already `["ref", "liturgy-config"]`); `useApi`, `ApiCall`, `Api` (1); `passageLimiter`, `passageStaleTime`, `keys.passage` (2c); `authEvents`, `isSigningOut`, `isNoChurchAccess` (1); `SECTION_LABELS` (T1); `PLACEMENT_KEYS` (T2).
- Produces:
  - `useLiturgyConfig(): UseQueryResult<LiturgyConfig, ApiError>`; `generateSection(call: ApiCall, section: SectionKey, body: GenerateLiturgyBody, signal?: AbortSignal): Promise<SectionResult>` (an answer without that section is `ApiError(0, "unknown", "Something went wrong.")`).
  - `timeoutFor("POST", "/liturgy/generate") === 100_000`.
  - `passageQuery(api, translation, ref) → {queryKey, queryFn, staleTime}`.
  - `reportAuthErrors(error, churchId: string | null): void`.
  - Fixtures: `liturgyConfig(overrides?)`, `sectionResult(section, text)`, `sectionFailure(section, code, message)`, `generateRoute(answer?)` (a `POST /liturgy/generate` handler; by default each section comes back as "{Label} written by the AI.").
  - Later users: T6 (`generateSection`, `passageQuery`, `reportAuthErrors`), T8-T11 (`useLiturgyConfig`, the fixtures).

Counts after this task: frontend **468 passed in 72 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "liturgy" frontend/src/lib/api/timeouts.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  71 passed (71)`, `      Tests  464 passed (464)`.

- [ ] **Step 2 (agent): Write the fixtures and the failing tests**

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
  ChurchProfile,
  Hymn,
```

**with:**

```ts
  ChurchProfile,
  GenerateLiturgyBody,
  Hymn,
```

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
  ScriptureMatches,
```

**with:**

```ts
  LiturgyConfig,
  LiturgySection,
  OutlineItem,
  ScriptureMatches,
  SectionError,
  SectionResult,
```

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";

```

**with:**

```ts
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

```

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
    slots: { opening: out(slots.opening), response: out(slots.response), closing: out(slots.closing) },
    ...overrides,
  };
}

```

**with:**

```ts
    slots: { opening: out(slots.opening), response: out(slots.response), closing: out(slots.closing) },
    ...overrides,
  };
}

// --- slice 4b: the liturgy config and the generation answers --------------------

/**
 * `GET /liturgy/config` as 4a serves it (slice 4a record: 8 sections, 17
 * places, 16 outline items, `ai_available` true), with the communion text
 * shortened to its first seven blocks. `liturgy.test.tsx` pins the sections,
 * places and outline to the shared fixtures.
 */
export function liturgyConfig(overrides: Partial<LiturgyConfig> = {}): LiturgyConfig {
  const section = (
    key: LiturgySection["key"],
    label: string,
    hint: string | null = null,
    extra: Partial<LiturgySection> = {},
  ): LiturgySection => ({ key, label, default_enabled: true, rows: 4, pastor_copy_only: false, hint, ...extra });
  const landmark = (
    key: string,
    label: string,
    value_source: OutlineItem["value_source"],
    anchors: string[] = [key],
    fixed_text: string | null = null,
  ): OutlineItem => ({ kind: "landmark", key, label, value_source, fixed_text, anchors_after: anchors });
  const card = (key: string, label: string, anchors: string[] = [key]): OutlineItem => ({
    kind: "section",
    key,
    label,
    value_source: "none",
    fixed_text: null,
    anchors_after: anchors,
  });
  return {
    sections: [
      section("call_to_worship", "Call to Worship", "Start lines with “Leader:” or “People:”. People lines print in bold."),
      section("opening_prayer", "Opening Prayer"),
      section("prayer_of_confession", "Prayer of Confession", "Printed in bold for everyone to read together."),
      section("assurance", "Assurance of Pardon", "Added automatically after your text."),
      section("prayer_for_illumination", "Prayer for Illumination"),
      section("prayers_of_the_people", "Prayers of the People", null, { default_enabled: false, rows: 8, pastor_copy_only: true }),
      section("offertory_prayer", "Offertory Prayer"),
      section("benediction", "Benediction", "Your church's default benediction. Admins can change it in Settings."),
    ],
    custom_placements: [
      ["call_to_worship", "After Call to Worship"],
      ["opening_prayer", "After Opening Prayer"],
      ["first_hymn", "After First Hymn"],
      ["prayer_of_confession", "After Prayer of Confession"],
      ["assurance", "After Assurance of Pardon"],
      ["prayer_for_illumination", "After Prayer for Illumination"],
      ["ot_reading", "After First Reading"],
      ["nt_reading", "After New Testament Reading"],
      ["sermon", "After Sermon"],
      ["affirmation_of_faith", "After Affirmation of Faith"],
      ["second_hymn", "After Second Hymn"],
      ["communion", "After Communion"],
      ["prayers_of_the_people", "After Prayers of the People"],
      ["offertory_prayer", "After Offertory Prayer"],
      ["third_hymn", "After Third Hymn"],
      ["benediction", "Before Benediction"],
      ["end", "At the end (after Benediction)"],
    ].map(([key, label]) => ({ key, label })),
    outline: [
      card("call_to_worship", "Call to Worship"),
      card("opening_prayer", "Opening Prayer"),
      landmark("first_hymn", "First Hymn", "hymn_opening"),
      card("prayer_of_confession", "Prayer of Confession"),
      card("assurance", "Assurance of Pardon"),
      card("prayer_for_illumination", "Prayer for Illumination"),
      landmark("ot_reading", "First Reading", "reading_ot"),
      landmark("nt_reading", "New Testament Reading", "reading_nt"),
      landmark("sermon", "Sermon Title", "sermon_title"),
      landmark("affirmation_of_faith", "Affirmation of Faith", "fixed", ["affirmation_of_faith"], "Apostles' Creed"),
      landmark("second_hymn", "Second Hymn", "hymn_response"),
      {
        kind: "communion",
        key: "communion",
        label: "The Sacrament of the Lord's Supper",
        value_source: "none",
        fixed_text: null,
        anchors_after: ["communion"],
      },
      card("prayers_of_the_people", "Prayers of the People"),
      card("offertory_prayer", "Offertory Prayer"),
      landmark("third_hymn", "Third Hymn", "hymn_closing", ["third_hymn", "benediction"]),
      card("benediction", "Benediction", ["end"]),
    ],
    assurance_response: "People: Thanks be to God! Amen.",
    default_benediction_fallback: "Halverson",
    communion: {
      title: "The Sacrament of the Lord's Supper",
      toggle_label: "Include communion liturgy (The Sacrament of the Lord's Supper)",
      default_rule: "first_sunday_of_month",
      blocks: [
        { style: "heading1", text: "The Sacrament of the Lord's Supper" },
        { style: "blank", text: "" },
        { style: "heading2", text: "Invitation to the Table" },
        { style: "text", text: "This is the table of our Lord Jesus Christ." },
        { style: "heading2", text: "Great Thanksgiving" },
        { style: "text", text: "The Lord be with you." },
        { style: "response", text: "And also with you." },
      ],
    },
    limits: {
      max_section_text: 20_000,
      max_sermon_title: 300,
      max_custom_elements: 30,
      max_custom_label: 200,
      max_custom_text: 10_000,
      max_sections_per_request: 4,
    },
    ai_available: true,
    ...overrides,
  };
}

/** A section written by the AI (`status: "generated"`). */
export function sectionResult(section: SectionResult["section"], text: string): SectionResult {
  return { section, status: "generated", text, error: null };
}

/** A section's failure inside the 200 (`status: "error"`), with the server's message. */
export function sectionFailure(section: SectionResult["section"], code: SectionError["code"], message: string): SectionResult {
  return { section, status: "error", text: null, error: { code, message } };
}

/**
 * A fake-API handler for `POST /liturgy/generate`: `answer(section, body)`
 * gives the section's result (wrapped in `{results: [...]}`) or a whole
 * response (`fakeError(...)`); by default "{Label} written by the AI.".
 */
export function generateRoute(
  answer: (
    section: SectionResult["section"],
    body: GenerateLiturgyBody,
  ) => SectionResult | { status: number } | Promise<SectionResult | { status: number }> = (section) =>
    sectionResult(section, `${SECTION_LABELS[section]} written by the AI.`),
) {
  return async (req: { body: unknown }) => {
    const body = req.body as GenerateLiturgyBody;
    const out = await answer(body.sections[0], body);
    return "section" in out ? { results: [out] } : out;
  };
}

```

**In `frontend/src/lib/queries/client.test.ts`, replace:**

```ts
import { isRetryable, makeQueryClient } from "./client";
```

**with:**

```ts
import { isRetryable, makeQueryClient, reportAuthErrors } from "./client";
```

**In `frontend/src/lib/queries/client.test.ts`, replace:**

```ts

  it("emits nothing while signing out", async () => {
```

**with:**

```ts

  it("reportAuthErrors does the same for a call made outside the caches (slice 4b generation)", () => {
    reportAuthErrors(new ApiError(401, "unauthenticated", "Please sign in."), "c-3");
    reportAuthErrors(noChurchAccess(), "c-3");
    reportAuthErrors(new ApiError(403, "forbidden", "Only church admins can do this."), "c-3");
    reportAuthErrors(new ApiError(429, "rate_limited", "Too many requests."), "c-3");
    expect(events).toEqual(["signOutRequired", "churchAccessLost:c-3"]);
  });

  it("emits nothing while signing out", async () => {
```

**Create `frontend/src/lib/queries/liturgy.test.tsx`:**

```tsx
/**
 * The Liturgy step's API calls (slice 4 spec, "API client usage"; F §4.4,
 * §1.8): the config is user-scoped reference data fetched once; a section is
 * written by one church-scoped POST that may take up to 100 s (owner answer
 * 2, 2026-09-30) and can be cancelled. The test fixture's config is pinned to
 * the shared fixtures 4a's API is pinned to.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { PLACEMENT_KEYS } from "@/lib/liturgy/cards";
import { installFakeApi } from "@/test/fake-api";
import { church, CHURCH_IDS, liturgyConfig, sectionResult } from "@/test/fixtures";

import { makeQueryClient, useApi } from "./client";
import { keys } from "./keys";
import { generateSection, useLiturgyConfig } from "./liturgy";

/** A shared fixture, read from the repo (the tests run in `frontend/`). */
function shared<T>(name: string): T {
  return JSON.parse(readFileSync(`${process.cwd()}/../backend/tests/fixtures/shared/${name}`, "utf-8")) as T;
}

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

describe("liturgy queries (S API client usage)", () => {
  it("loads the config once as the user, and never counts it stale", async () => {
    const api = installFakeApi({ "GET /liturgy/config": liturgyConfig() });
    const { result, queryClient } = render(() => useLiturgyConfig());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.sections).toHaveLength(8);
    expect(api.requests.map((r) => [r.method, r.path, r.headers["X-Church-Id"]])).toEqual([
      ["GET", "/liturgy/config", undefined],
    ]);
    const query = queryClient.getQueryCache().find({ queryKey: keys.liturgyConfig() });
    expect(query?.isStale()).toBe(false);
    render(() => useLiturgyConfig(), queryClient);
    expect(api.requests).toHaveLength(1);
  });

  it("writes one section as the church, waiting up to 100 seconds, and a cancel rejects as aborted", async () => {
    expect(timeoutFor("POST", "/liturgy/generate")).toBe(100_000);
    const api = installFakeApi({
      "POST /liturgy/generate": { results: [sectionResult("call_to_worship", "Leader: Come!")] },
    });
    const { result } = render(() => useApi());
    const body = { occasion: "", scriptures: [], hymns: {}, sections: ["call_to_worship" as const] };
    await expect(generateSection(result.current.church, "call_to_worship", body)).resolves.toEqual(
      sectionResult("call_to_worship", "Leader: Come!"),
    );
    expect(api.requests[0]).toMatchObject({ method: "POST", path: "/liturgy/generate", body });
    expect(api.requests[0].headers["X-Church-Id"]).toBe(CHURCH_IDS.grace);
    const controller = new AbortController();
    controller.abort();
    await expect(generateSection(result.current.church, "call_to_worship", body, controller.signal)).rejects.toMatchObject(
      new ApiError(0, "aborted", "The request was cancelled."),
    );
  });

  it("uses a test config equal to the shared fixtures 4a's API is pinned to", () => {
    const config = liturgyConfig();
    const sections = shared<{ sections: { key: string; label: string; default_enabled: boolean }[] }>("liturgy_sections.json");
    expect(config.sections.map(({ key, label, default_enabled }) => ({ key, label, default_enabled }))).toEqual(sections.sections);
    expect(config.outline).toEqual(shared<{ outline: unknown[] }>("liturgy_outline.json").outline);
    expect(config.custom_placements.map((p) => p.key)).toEqual([...PLACEMENT_KEYS]);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/queries/liturgy.test.tsx src/lib/queries/client.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|TypeError|Error: Failed|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/lib/queries/liturgy.test.tsx [ src/lib/queries/liturgy.test.tsx ]
Error: Failed to resolve import "./liturgy" from "src/lib/queries/liturgy.test.tsx". Does the file exist?
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 1 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/queries/client.test.ts > handleAuthErrors (through makeQueryClient's caches) > reportAuthErrors does the same for a call made outside the caches (slice 4b generation)
TypeError: reportAuthErrors is not a function
      Tests  1 failed | 16 passed (17)
```

- [ ] **Step 4 (agent): Write the queries, the timeout row, `passageQuery` and `reportAuthErrors`**

**In `frontend/src/lib/api/timeouts.ts`, replace:**

```ts
  "POST /hymns/suggestions": 90_000,
};
```

**with:**

```ts
  "POST /hymns/suggestions": 90_000,
  // Slice 4 (F §1.8 amendment, owner answer 2, 2026-09-30): a section answers within
  // 85 s (4a's 80 s deadline plus a last connect). The timer starts after getAccessToken(),
  // so the other 15 s cover the server's sign-in key fetch (at most 5 s), latency and the proxy.
  // The service reviewer's routes (the slice after 4b) reuse this value.
  "POST /liturgy/generate": 100_000,
};
```

**In `frontend/src/lib/queries/client.ts`, replace:**

```ts
export function handleAuthErrors(error: unknown, source: AnyQuery | AnyMutation): void {
  if (isSigningOut()) return;
```

**with:**

```ts
export function handleAuthErrors(error: unknown, source: AnyQuery | AnyMutation): void {
  reportAuthErrors(error, churchIdOf(source));
}

/**
 * `handleAuthErrors` for a call made outside the caches (slice 4b: the
 * liturgy generation queue): a 401 asks for sign-out; a `no_church_access`
 * 403 reports `churchId` lost. Nothing while signing out.
 */
export function reportAuthErrors(error: unknown, churchId: string | null): void {
  if (isSigningOut()) return;
```

**In `frontend/src/lib/queries/client.ts`, replace:**

```ts
  if (isNoChurchAccess(error)) {
    const churchId = churchIdOf(source);
    if (churchId) authEvents.churchAccessLost(churchId);
  }
```

**with:**

```ts
  if (isNoChurchAccess(error) && churchId) authEvents.churchAccessLost(churchId);
```

**In `frontend/src/lib/queries/passages.ts`, replace:**

```ts
import { useApi } from "./client";
```

**with:**

```ts
import { useApi, type Api } from "./client";
```

**In `frontend/src/lib/queries/passages.ts`, replace:**

```ts
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
```

**with:**

```ts
    ...passageQuery(api, translation, ref),
    enabled,
```

**In `frontend/src/lib/queries/passages.ts`, replace:**

```ts
  });
}

```

**with:**

```ts
  });
}

/**
 * The key, fetch and freshness `usePassage` uses, for a fetch outside a
 * component: slice 4b's liturgy provider reads the sermon text with
 * `queryClient.fetchQuery(passageQuery(...))`, so a passage step 1 already
 * loaded is reused and concurrent reads share one request.
 */
export function passageQuery(api: Api, translation: string, ref: string) {
  return {
    queryKey: keys.passage(translation, ref),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      passageLimiter(async () => {
        const body = await api.user<Passages>("/scripture/passages", {
          method: "POST",
          json: { refs: [ref], translation },
          signal,
        });
        return body.passages[0];
      }, signal),
    staleTime: (query: { state: { data: Passage | undefined } }) => passageStaleTime(query.state.data),
  };
}

```

**Create `frontend/src/lib/queries/liturgy.ts`:**

```ts
/**
 * The Liturgy step's API calls (slice 4 spec, "API client usage"; F §4.4).
 *
 * - `useLiturgyConfig()`: `GET /liturgy/config`, user-scoped reference data
 *   under ["ref", "liturgy-config"], never stale. A key added to Railway later
 *   (`ai_available`) takes effect on the next page load.
 * - `generateSection(call, section, body, signal)`: one
 *   `POST /liturgy/generate`, church-scoped, returning that section's result.
 *   A plain async function, because the provider's per-section queue and
 *   cancel do not fit `useMutation`; it still lives here, so no page calls
 *   `apiFetch`. Its client timeout is 100 s (`lib/api/timeouts.ts`, owner
 *   answer 2, 2026-09-30).
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/client";
import type { GenerateLiturgyBody, GenerateLiturgyResult, LiturgyConfig, SectionResult } from "@/lib/api/types";
import type { SectionKey } from "@/lib/draft/schema";

import { useApi, type ApiCall } from "./client";
import { keys } from "./keys";

export function useLiturgyConfig(): UseQueryResult<LiturgyConfig, ApiError> {
  const api = useApi();
  return useQuery<LiturgyConfig, ApiError>({
    queryKey: keys.liturgyConfig(),
    queryFn: ({ signal }) => api.user<LiturgyConfig>("/liturgy/config", { signal }),
    staleTime: Infinity,
  });
}

export async function generateSection(
  call: ApiCall,
  section: SectionKey,
  body: GenerateLiturgyBody,
  signal?: AbortSignal,
): Promise<SectionResult> {
  const out = await call<GenerateLiturgyResult>("/liturgy/generate", { method: "POST", json: body, signal });
  const result = out.results.find((r) => r.section === section);
  if (!result) throw new ApiError(0, "unknown", "Something went wrong.");
  return result;
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/queries 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  9 passed (9)`, `      Tests  45 passed (45)`; the suite ` Test Files  72 passed (72)`, `      Tests  468 passed (468)`; `typecheck 0` and `lint 0`; ` M` for the five modified files and `??` for the two new ones.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/queries/liturgy.ts frontend/src/lib/queries/liturgy.test.tsx frontend/src/lib/api/timeouts.ts frontend/src/lib/queries/client.ts frontend/src/lib/queries/client.test.ts frontend/src/lib/queries/passages.ts frontend/src/test/fixtures/index.ts
git commit -m "Liturgy: the config and generate calls, a 100 s client timeout, and the test fixtures (S API client usage; owner answer 2)" -m "useLiturgyConfig loads GET /liturgy/config once as the user, never
stale; generateSection posts one section as the church and returns its
result, with a 100 s client timeout (owner answer 2: 4a answers within
85 s; the rest covers the server's sign-in key fetch, latency and the
proxy, since the timer starts after the token). passageQuery shares usePassage's key, limiter
and freshness for the sermon text; reportAuthErrors gives a call made
outside the caches the same 401 and lost-church handling. The fixtures'
liturgy config is pinned to 4a's shared fixtures.
Frontend 464 -> 468 tests in 71 -> 72 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

### Task 5: The draft follows the church's default benediction (S "Benediction and the church default", "Draft store integration"; F §4.6 "Fresh draft", "Defaults"; clarifications 13, 14)

S: a fresh draft's Benediction card is `{enabled: true, text: <church default>, origin: "default"}`, the card follows the default until it is edited, generated or cleared, and `DraftProvider` runs `applyLiturgyDefaults` after every change and whenever the profile's `default_benediction` changes. Checked on `4dfed3b`: `freshDraft` leaves the text `""` and nothing fills it; the profile the builder shell passes to `DraftProvider` already carries `default_benediction` (4a). This task:
- `freshDraft` fills the card from `church.default_benediction` ("Halverson" when an older API leaves it out), so a fresh draft is born with it; `DraftChurch` gains the optional field.
- `DraftStore` takes `liturgyDefaults` and runs `applyLiturgyDefaults` on load, on every `update`, `autoUpdate` and `replace`, and on an adopted draft (in memory). A stored draft the defaults change (one saved before 4b with an empty Benediction, or communion out of step with its date) is stamped 1 ms after the stored draft, like 2b's roll-forward; `setLiturgyDefaults` (a new default from a profile refetch) is an automatic change, stamped 1 ms after the current draft, so neither ever outranks another tab's edit (clarification 13).
- `DraftProvider` passes the profile's default and calls `setLiturgyDefaults` when it changes; `useDraft()` gains `peek()`, the latest draft now, for T6's code outside a render (clarification 14).

A fresh draft now prints the church default, so three existing tests change their expected values (0 new tests there): the provisional payload of a fresh draft holds `benediction: "Halverson"`, the fresh-draft shape test expects the text (and gains the empty-default and missing-field cases), and the liturgy status of a draft with one typed card is "2 of 7".

**Files:**
- Modify: `frontend/src/lib/draft/schema.ts` (`DraftChurch.default_benediction`, `freshDraft`), `frontend/src/lib/draft/store.ts` (`liturgyDefaults`, `setLiturgyDefaults`), `frontend/src/lib/draft/context.tsx` (the profile's default, `peek`)
- Test: `frontend/src/lib/draft/store.test.ts` (+2), `frontend/src/lib/draft/context.test.tsx` (+1); `mapping.test.ts`, `schema.test.ts`, `status.test.ts` (one test each edited, 0)

**Interfaces:**
- Consumes: `applyLiturgyDefaults`, `DEFAULT_BENEDICTION_FALLBACK`, `type LiturgyDefaults` (T2); `ChurchProfile.default_benediction` (4a).
- Produces: `type DraftChurch = {id; timezone?; timezone_valid?; default_benediction?: string}`; `new DraftStore({..., liturgyDefaults?: LiturgyDefaults})`, `store.setLiturgyDefaults(next)`; `DraftApi.peek: () => DraftV1`. Later users: T6 (`peek`), T8 (the Benediction card follows the default), every "New service" (its fresh draft carries the default).

Counts after this task: frontend **471 passed in 72 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "default_benediction" frontend/src/lib/draft/schema.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/context.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `frontend/src/lib/draft/schema.ts:0`, `frontend/src/lib/draft/store.ts:0`, `frontend/src/lib/draft/context.tsx:0`; ` Test Files  72 passed (72)`, `      Tests  468 passed (468)`.

- [ ] **Step 2 (agent): Write the failing tests and the new expected values**

**In `frontend/src/lib/draft/store.test.ts`, replace:**

```ts
import { corruptDraftKey, draftKey, type DraftV1 } from "./schema";
```

**with:**

```ts
import { corruptDraftKey, draftKey, freshDraft, type DraftV1 } from "./schema";
```

**In `frontend/src/lib/draft/store.test.ts`, replace:**

```ts

describe("DraftStore changes (S store.ts)", () => {
```

**with:**

```ts

describe("DraftStore and the liturgy defaults (slice 4 spec, Draft store integration)", () => {
  function defaultsStore(storage: DraftStorage, now = clock().now) {
    return new DraftStore({ userId: USER_ID, church: GRACE, storage, now, liturgyDefaults: { defaultBenediction: "Halverson" } });
  }

  it("fills a fresh draft's Benediction with the church default and follows a new default until the card is edited", () => {
    const { storage, data } = memoryStorage();
    const t = clock();
    const store = defaultsStore(storage, t.now);
    store.start();
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
    vi.advanceTimersByTime(WRITE_DELAY_MS);
    expect(stored(data).liturgy.cards.benediction.text).toBe("Halverson");

    // An admin changes the default (6a) and the profile refetches: an automatic change, 1 ms after the draft.
    const before = store.getSnapshot().draft.updated_at;
    t.advance(60_000);
    store.setLiturgyDefaults({ defaultBenediction: "The Lord bless you and keep you." });
    const followed = store.getSnapshot().draft;
    expect(followed.liturgy.cards.benediction.text).toBe("The Lord bless you and keep you.");
    expect(followed.updated_at).toBe(new Date(Date.parse(before) + 1).toISOString());
    store.setLiturgyDefaults({ defaultBenediction: "The Lord bless you and keep you." });
    expect(store.getSnapshot().draft).toBe(followed); // the same default: nothing to do

    // Every change keeps the defaults: New service's fresh draft gets the default too.
    store.update((d) => ({ ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Go in peace.", origin: "typed" } } } }));
    store.setLiturgyDefaults({ defaultBenediction: "Halverson" });
    expect(store.getSnapshot().draft.liturgy.cards.benediction.text).toBe("Go in peace.");
    store.replace(freshDraft({ church: GRACE, user: { id: USER_ID }, now: t.now() }));
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
  });

  it("loads a stored draft with today's default and the date's communion, stamped just after the stored draft", () => {
    const old = testDraft((d) => ({
      ...d,
      updated_at: "2026-09-29T15:00:00.000Z",
      liturgy: { ...d.liturgy, include_communion: false }, // stored before 4b: the rule says on for October 4
    }));
    const { storage } = memoryStorage({ [KEY]: JSON.stringify(old) });
    const draft = defaultsStore(storage).getSnapshot().draft;
    expect(draft.liturgy.cards.benediction.text).toBe("Halverson");
    expect(draft.liturgy.include_communion).toBe(true);
    expect(draft.updated_at).toBe("2026-09-29T15:00:00.001Z");
    // Without defaults (slice 2's tests), the store changes nothing.
    expect(makeStore(memoryStorage({ [KEY]: JSON.stringify(old) }).storage).store.getSnapshot().draft).toEqual(old);
  });
});

describe("DraftStore changes (S store.ts)", () => {
```

**In `frontend/src/lib/draft/context.test.tsx`, replace:**

```tsx
        Rename
      </button>
```

**with:**

```tsx
        Rename
      </button>
    </div>
  );
}

/** The Benediction card and the latest draft `peek` returns, for the liturgy defaults (slice 4b). */
function BenedictionProbe() {
  const { draft, peek } = useDraft();
  return (
    <div>
      <p>Benediction: {draft.liturgy.cards.benediction.text || "empty"}</p>
      <button type="button" onClick={() => window.alert(peek().liturgy.cards.benediction.text)}>
        Peek
      </button>
```

**In `frontend/src/lib/draft/context.test.tsx`, replace:**

```tsx
    vi.restoreAllMocks();
  });
```

**with:**

```tsx
    vi.restoreAllMocks();
  });

  it("fills the Benediction from the church profile, follows a new default, and peek reads the latest draft (slice 4b)", () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const view = render(
      <DraftProvider userId={USER_ID} church={churchProfile({ default_benediction: "Go in peace." })}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: Go in peace.")).toBeInTheDocument();
    view.rerender(
      <DraftProvider userId={USER_ID} church={churchProfile({ default_benediction: "" })}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: empty")).toBeInTheDocument();
    act(() => screen.getByRole("button", { name: "Peek" }).click());
    expect(alert).toHaveBeenCalledWith("");
    // An older API without the field: the fallback.
    view.rerender(
      <DraftProvider userId={USER_ID} church={{ id: GRACE.id, timezone: GRACE.timezone }}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: Halverson")).toBeInTheDocument();
  });
```

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

```ts
      liturgy: {},
```

**with:**

```ts
      liturgy: { benediction: "Halverson" }, // the church default (slice 4b)
```

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

```ts
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship." });
```

**with:**

```ts
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship.", benediction: "Halverson" });
```

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

```ts
import { churchProfile, testDraft, USER_ID } from "@/test/fixtures";
```

**with:**

```ts
import { CHURCH_IDS, churchProfile, DRAFT_NOW, testDraft, USER_ID } from "@/test/fixtures";
```

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

```ts
        text: "",
        origin: key === "benediction" ? "default" : "empty",
      });
    }
```

**with:**

```ts
        text: key === "benediction" ? "Halverson" : "", // the church default (slice 4b)
        origin: key === "benediction" ? "default" : "empty",
      });
    }
    const user = { id: USER_ID };
    const none = freshDraft({ church: churchProfile({ default_benediction: "" }), user, now: DRAFT_NOW });
    expect(none.liturgy.cards.benediction).toEqual({ enabled: true, text: "", origin: "default" });
    const older = freshDraft({ church: { id: CHURCH_IDS.grace, timezone: "America/New_York" }, user, now: DRAFT_NOW });
    expect(older.liturgy.cards.benediction.text).toBe("Halverson"); // an API without the field
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
      done: 1,
```

**with:**

```ts
      done: 2, // and the Benediction, following the church default (slice 4b)
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft 2>&1 | grep -E "^ FAIL|AssertionError|TestingLibraryElementError|Tests ")
```

**Expected:**

```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 7 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/draft/mapping.test.ts > draftToServicePayload (provisional; 5a replaces it) > maps a fresh draft to the ServiceDraft shape
AssertionError: expected { …(11) } to deeply equal { …(11) }
 FAIL  |unit| src/lib/draft/mapping.test.ts > draftToServicePayload (provisional; 5a replaces it) > trims and drops blank lines, keeps enabled non-empty cards, slot-keyed hymns and elements without ids
AssertionError: expected { Object (call_to_worship) } to deeply equal { …(2) }
 FAIL  |unit| src/lib/draft/schema.test.ts > draft schema and freshDraft (F §4.6) > a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults
AssertionError: benediction: expected { enabled: true, text: '', …(1) } to deeply equal { enabled: true, …(2) }
 FAIL  |unit| src/lib/draft/status.test.ts > stepStatus (F §4.7) > counts filled hymn slots and enabled liturgy cards with text once those steps ship
AssertionError: expected { kind: 'incomplete', done: 1, …(1) } to deeply equal { kind: 'incomplete', done: 2, …(1) }
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore and the liturgy defaults (slice 4 spec, Draft store integration) > fills a fresh draft's Benediction with the church default and follows a new default until the card is edited
AssertionError: expected { enabled: true, text: '', …(1) } to deeply equal { enabled: true, …(2) }
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore and the liturgy defaults (slice 4 spec, Draft store integration) > loads a stored draft with today's default and the date's communion, stamped just after the stored draft
AssertionError: expected '' to be 'Halverson' // Object.is equality
 FAIL  |dom| src/lib/draft/context.test.tsx > DraftProvider and useDraft (F §4.6 Persistence) > fills the Benediction from the church profile, follows a new default, and peek reads the latest draft (slice 4b)
TestingLibraryElementError: Unable to find an element with the text: Benediction: Go in peace.. This could be because the text is broken up by multiple elements. In this case, you can provide a function for your text matcher to make your matcher more flexible.
      Tests  7 failed | 52 passed (59)
```

- [ ] **Step 4 (agent): Fill the fresh draft, and run the defaults in the store and the provider**

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
```

**with:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
/** The profile fields `freshDraft` needs (`GET /church`, slice 2a). */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean };
```

**with:**

```ts
/**
 * The profile fields the draft needs (`GET /church`): the zone for
 * `freshDraft` (slice 2a) and the church's default benediction, which an
 * untouched Benediction card shows (slice 4a; an older API leaves it out).
 */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean; default_benediction?: string };
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
 * Prayers of the People, the benediction card `default`-origin (slice 4 fills
 * its text), communion on for a first Sunday, a new save key, on step 1.
```

**with:**

```ts
 * Prayers of the People, the benediction card `default`-origin with the
 * church's default benediction ("Halverson" when the profile has none; slice
 * 4b), communion on for a first Sunday, a new save key, on step 1.
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
      { enabled: DEFAULT_ENABLED[key], text: "", origin: key === "benediction" ? "default" : "empty" },
```

**with:**

```ts
      key === "benediction"
        ? { enabled: DEFAULT_ENABLED[key], text: church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK, origin: "default" }
        : { enabled: DEFAULT_ENABLED[key], text: "", origin: "empty" },
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
 * - A failed write switches to memory-only with one "memory_only" notice and
```

**with:**

```ts
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
 * - Liturgy defaults (slice 4b; slice 4 spec "Draft store integration"): with
 *   `liturgyDefaults`, every load, change and replace also runs
 *   `applyLiturgyDefaults`, so an untouched Benediction shows the church's
 *   default and untouched communion follows the date. A load it changes is
 *   stamped 1 ms after the stored draft, and `setLiturgyDefaults` (the
 *   profile refetched with a new default) is an automatic change, so neither
 *   outranks another tab's edit. An adopted draft gets the defaults in memory.
 * - A failed write switches to memory-only with one "memory_only" notice and
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
import { isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { readLocal, removeLocal, tryWriteLocal } from "@/lib/storage";
```

**with:**

```ts
import { isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { applyLiturgyDefaults, type LiturgyDefaults } from "@/lib/liturgy/defaults";
import { readLocal, removeLocal, tryWriteLocal } from "@/lib/storage";
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
  notify?: (notice: DraftNotice) => void;
};
```

**with:**

```ts
  notify?: (notice: DraftNotice) => void;
  /** The church's liturgy defaults; without them (slice 2's tests) the store changes no card. */
  liturgyDefaults?: LiturgyDefaults;
};
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts

  constructor({ userId, church, storage = browserDraftStorage, now = () => new Date(), notify = () => {} }: DraftStoreOptions) {
```

**with:**

```ts
  private defaults: LiturgyDefaults | null;

  constructor({
    userId,
    church,
    storage = browserDraftStorage,
    now = () => new Date(),
    notify = () => {},
    liturgyDefaults,
  }: DraftStoreOptions) {
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    this.notify = notify;

```

**with:**

```ts
    this.notify = notify;
    this.defaults = liturgyDefaults ?? null;

```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    const rolled = rollForward(draft, todayIn(churchZone(church), now()));
```

**with:**

```ts
    const rolled = this.withDefaults(rollForward(draft, todayIn(churchZone(church), now())));
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    const next = recipe(this.snapshot.draft);
```

**with:**

```ts
    const next = this.withDefaults(recipe(this.snapshot.draft));
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    const next = recipe(current);
```

**with:**

```ts
    const next = this.withDefaults(recipe(current));
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    this.set(normalizePicks({ ...next, updated_at: this.now().toISOString() }));
    this.schedule();
```

**with:**

```ts
    this.set(this.withDefaults(normalizePicks({ ...next, updated_at: this.now().toISOString() })));
    this.schedule();
  };

  /** The church's defaults changed (a profile refetch): an automatic change for a card still following them. */
  setLiturgyDefaults = (next: LiturgyDefaults): void => {
    if (this.defaults?.defaultBenediction === next.defaultBenediction) return;
    this.defaults = next;
    this.autoUpdate((d) => d);
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    this.set(normalizePicks(stored));
    this.notify("adopted");
    return true;
```

**with:**

```ts
    this.set(this.withDefaults(normalizePicks(stored)));
    this.notify("adopted");
    return true;
  }

  private withDefaults(d: DraftV1): DraftV1 {
    return this.defaults === null ? d : applyLiturgyDefaults(d, this.defaults);
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx

import type { DraftChurch, DraftV1, StepId } from "./schema";
```

**with:**

```tsx

import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

import type { DraftChurch, DraftV1, StepId } from "./schema";
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx
  setLastStep: (step: StepId) => void;
  persistence: Persistence;
```

**with:**

```tsx
  setLastStep: (step: StepId) => void;
  /** The latest draft now, for code that runs outside a render (slice 4b's generation provider). */
  peek: () => DraftV1;
  persistence: Persistence;
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx
  const [store] = useState(() => new DraftStore({ userId, church, notify }));
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
```

**with:**

```tsx
  const defaultBenediction = church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK;
  const [store] = useState(
    () => new DraftStore({ userId, church, notify, liturgyDefaults: { defaultBenediction } }),
  );
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);

  // The profile refetched with another default (6a's Settings): untouched Benediction cards follow it.
  useEffect(() => {
    store.setLiturgyDefaults({ defaultBenediction });
  }, [store, defaultBenediction]);
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx
      setLastStep: store.setLastStep,
    }),
```

**with:**

```tsx
      setLastStep: store.setLastStep,
      peek: () => store.getSnapshot().draft,
    }),
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  9 passed (9)`, `      Tests  59 passed (59)`; the suite ` Test Files  72 passed (72)`, `      Tests  471 passed (471)` (the builder, Hymns and Date & readings tests pass unchanged: their seeded drafts carry the default already); `typecheck 0` and `lint 0`; ` M` for the eight files named in **Files:**.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/draft/schema.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/context.tsx frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/context.test.tsx frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/status.test.ts
git commit -m "Draft: the Benediction follows the church's default until it is changed (S Draft store integration)" -m "freshDraft fills the Benediction from the profile's default_benediction
(Halverson when the API leaves it out). The draft store runs
applyLiturgyDefaults on load, on every change and on replace; a load it
changes is stamped 1 ms after the stored draft, and a new default from a
profile refetch is an automatic change, so neither outranks another
tab's edit. DraftProvider passes the default and useDraft gains peek().
Frontend 468 -> 471 tests in 72 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 8 files changed.

### Task 6: The generation provider in the builder shell (S Frontend `generation.tsx`, UX "Generate and Regenerate" steps 0-7, "Sermon text", BC-13, BC-21; F §1.8; clarifications 15, 16, 17, 18, 32, 33, 36)

`LiturgyGenerationProvider` holds the Liturgy step's AI runs, card errors and Undo in memory, and the builder shell mounts it inside `DraftProvider`, so a run started on the Liturgy step keeps going on the other steps and its result lands in the draft (BC-21). Leaving `/builder`, switching church (the keyed remount) or signing out unmounts it, which cancels everything. It sends nothing while it is idle, so the shell's other tests need no new route.

What it does, in S's order:
- **Step 0.** With `aiAvailable: false`, `generate()` sends nothing and marks each targeted switched-on empty card with `localAiNotConfigured()`.
- **Steps 1-3.** Each key is queued; the batch first reads the sermon text once (`sermonSource`, then `queryClient.fetchQuery(passageQuery(...))`, bounded at 10 s; a failure, a timeout or no text sends the batch without it, with no toast), then each section is one request through the 3-at-a-time queue. A card already running is not queued twice.
- **Step 4.** `cancel(keys)` and the AI bar's `cancelBulk()` drop the cards' runs (waiting for the sermon text, queued or writing); the cards return to where they were, silently.
- **Step 6.** The card is captured (`captureCard`) when the member asks: in `generate()`, at the click or at "Replace text" (clarification 33). Just before a queued request is sent, `staleVerdict` checks the current draft: anything but "apply" sends nothing, shows S's toast and counts as not written. When the answer arrives, `staleVerdict` decides again inside the draft update: "apply" writes the text with origin "ai" and keeps the previous `{text, origin}` for Undo when it replaced text (over a blank card it clears any "Cleared." Undo; clarification 36); "service_changed" and "edited" drop it with S's toasts ("The service changed, so the AI draft for {Label} was discarded." and "Kept your edits — the new AI draft for {Label} was not used.").
- **A new service** (clarification 32). The provider watches `draft.created_at`; when it changes, every run is cancelled silently, the errors and Undo entries are cleared, and a bulk run ends with one toast, "The service changed, so the AI drafts were discarded.", with no "Wrote…" toast.
- **Step 7.** A 429 stops the queue: that card and every card still waiting show "Too many requests — try again in N s.", with `retryAt`, the moment the wait ends, so the screen's wait survives leaving the step (clarification 36).
- **Errors.** A section's error or a failed request becomes the card's error (`cardErrorFrom`, kept as a `CardErrorState` with `retryAt` and `bulk`, true when it came from "Generate empty sections", so the card announces it politely); a 401 or a lost church goes to `reportAuthErrors` and shows nothing on the card.
- **Bulk.** A "Generate empty sections" run ends with one toast, "Wrote n sections." ("Wrote 1 section." for one; clarification 16) or "Wrote k of n sections. The rest show what went wrong."; cancelled cards are not counted, and a run cancelled whole shows none (clarification 15).
- The provider takes `sermonWaitMs` so a test can shorten the 10 s wait (clarification 17), and the Undo lines, errors and runs are exposed for T8-T10 (`runs`, `errors`, `undo`, `bulk`, `generate`, `cancel`, `cancelBulk`, `dismissError`, `setUndo`, `clearUndo`, `applyUndo`; clarification 18).

The provider's own tests are S's `generation.test.tsx` cases (the sermon text) and the two before-sending cases (Undo while "Waiting…", and another tab's edit while queued, each sends nothing); T9's step tests cover Generate, Regenerate, errors, the stale rule, navigation and the 429 through the screen.

**Files:**
- Create: `frontend/src/lib/liturgy/generation.tsx`
- Modify: `frontend/src/components/builder/builder-shell.tsx` (mounts the provider)
- Test: `frontend/src/lib/liturgy/generation.test.tsx` (new, 5)

**Interfaces:**
- Consumes: `useDraft().update`, `peek` (T5); `captureCard`, `staleVerdict`, `applyGenerated`, `restoreCard` (T2); `buildGenerateRequest`, `sermonSource`, `sermonText`, `cardErrorFrom`, `localAiNotConfigured`, `createTaskQueue` (T3); `generateSection`, `passageQuery`, `reportAuthErrors`, `useApi` (T4); `SECTION_LABELS` (T1); sonner's `toast.message`.
- Produces: `LiturgyGenerationProvider({church: {id, effective_translation}, sermonWaitMs?, children})`, `useLiturgyGeneration(): LiturgyGeneration`, `MAX_IN_FLIGHT = 3`, `SERMON_WAIT_MS = 10_000`, `type CardRun = {phase: "queued" | "writing", since}`, `type UndoEntry = {kind: "replaced" | "cleared", previous}`, `type BulkRun = {total, done}`, `type CardErrorState = CardError & {retryAt?, bulk?}`, `SERVICE_CHANGED_BULK`. Later users: T8-T10 (the step), T11 (`LiturgySummaryBlock` reads `runs`).

Counts after this task: frontend **476 passed in 73 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "LiturgyGenerationProvider" frontend/src/components/builder/builder-shell.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  72 passed (72)`, `      Tests  471 passed (471)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/generation.test.tsx`:**

```tsx
/**
 * The generation provider's sermon text (slice 4 spec, "Sermon text";
 * Testing `generation.test.tsx`, amendment 2026-09-26): a batch reads the
 * passage once and every request carries it; a fetch that fails or takes too
 * long still sends the batch, without it and with no toast; Cancel during the
 * wait sends nothing. And S step 6 before sending: a card whose text became
 * the member's while it waited in the queue (Undo, another tab) is not sent.
 * The step's own tests (T9) cover the rest of the flow.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { GenerateLiturgyBody } from "@/lib/api/types";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, generateRoute, me, sectionResult, testDraft, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyGenerationProvider, MAX_IN_FLIGHT, SERMON_WAIT_MS, useLiturgyGeneration, type LiturgyGeneration } from "./generation";

const KEY = draftKey(USER_ID, church().id);
const FOUR: SectionKey[] = ["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance"];
const PHILIPPIANS = {
  reference: "Philippians 3:4b-14",
  status: "ok",
  sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
};

/** The provider's latest value, for the test to call (set after each render). */
const handle: { current: LiturgyGeneration | null } = { current: null };
const generation = {
  generate: (...args: Parameters<LiturgyGeneration["generate"]>) => handle.current?.generate(...args),
  cancel: (...args: Parameters<LiturgyGeneration["cancel"]>) => handle.current?.cancel(...args),
  setUndo: (...args: Parameters<LiturgyGeneration["setUndo"]>) => handle.current?.setUndo(...args),
  applyUndo: (...args: Parameters<LiturgyGeneration["applyUndo"]>) => handle.current?.applyUndo(...args),
};

function Probe() {
  const g = useLiturgyGeneration();
  useEffect(() => {
    handle.current = g;
  });
  const { draft } = useDraft();
  return (
    <ul>
      {FOUR.map((key) => (
        <li key={key}>
          {key}: {draft.liturgy.cards[key].text || "empty"} / {g.runs[key]?.phase ?? "idle"}
        </li>
      ))}
    </ul>
  );
}

/** Pat's draft with October 4's readings (the NT reading is Philippians), in the providers the shell mounts. */
function renderProvider(routes: Record<string, FakeHandler>, sermonWaitMs?: number, recipe: (d: DraftV1) => DraftV1 = (d) => d) {
  window.localStorage.setItem(
    KEY,
    JSON.stringify(recipe(editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46"))),
  );
  const api = installFakeApi(routes);
  const profile = churchProfile();
  renderWithProviders(
    <>
      <DraftProvider userId={USER_ID} church={profile}>
        <LiturgyGenerationProvider church={profile} sermonWaitMs={sermonWaitMs}>
          <Probe />
        </LiturgyGenerationProvider>
      </DraftProvider>
      <Toaster />
    </>,
    { me: me(), church: church() },
  );
  return api;
}

const generateCalls = (requests: RecordedRequest[]) => requests.filter((r) => r.path === "/liturgy/generate");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the sermon text (S Sermon text)", () => {
  it("reads the passage once for a batch of 4, then sends 4 requests with the same sermon_text, 3 at a time", async () => {
    let open = 0;
    let most = 0;
    const api = renderProvider({
      "POST /scripture/passages": { passages: [PHILIPPIANS] },
      "POST /liturgy/generate": generateRoute(async (section) => {
        open += 1;
        most = Math.max(most, open);
        await new Promise((resolve) => setTimeout(resolve, 20));
        open -= 1;
        return { section, status: "generated", text: `${section} text`, error: null };
      }),
    });
    act(() => generation.generate(FOUR, { aiAvailable: true, bulk: true }));
    for (const key of FOUR) expect(await screen.findByText(`${key}: ${key} text / idle`)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/scripture/passages")).toHaveLength(1);
    expect(api.requests.find((r) => r.path === "/scripture/passages")?.body).toEqual({ refs: ["Philippians 3:4b-14"], translation: "web" });
    const calls = generateCalls(api.requests);
    expect(calls.map((r) => (r.body as GenerateLiturgyBody).sections)).toEqual(FOUR.map((key) => [key]));
    for (const call of calls) {
      expect((call.body as GenerateLiturgyBody).sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "I press on toward the goal." });
    }
    expect(most).toBeLessThanOrEqual(MAX_IN_FLIGHT);
    expect(await screen.findByText("Wrote 4 sections.")).toBeInTheDocument();
  });

  it("sends the batch without sermon_text, and no toast about it, when the passage fails or takes too long", async () => {
    expect(SERMON_WAIT_MS).toBe(10_000);
    const failing = renderProvider({
      "POST /scripture/passages": fakeError(500, "internal_error", "Something went wrong."),
      "POST /liturgy/generate": generateRoute(),
    });
    act(() => generation.generate(["call_to_worship"], { aiAvailable: true }));
    expect(await screen.findByText("call_to_worship: Call to Worship written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(failing.requests)[0].body).not.toHaveProperty("sermon_text");
    expect(screen.queryByText(/Something went wrong/)).toBeNull();
  });

  it("goes without the sermon text once the wait passes (shortened here), and Cancel during the wait sends nothing", async () => {
    const never = new Promise<never>(() => {});
    const api = renderProvider(
      { "POST /scripture/passages": () => never, "POST /liturgy/generate": generateRoute() },
      50,
    );
    act(() => generation.generate(["opening_prayer"], { aiAvailable: true }));
    expect(screen.getByText("opening_prayer: empty / queued")).toBeInTheDocument();
    expect(await screen.findByText("opening_prayer: Opening Prayer written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)[0].body).not.toHaveProperty("sermon_text");

    act(() => generation.generate(["assurance"], { aiAvailable: true }));
    expect(screen.getByText("assurance: empty / queued")).toBeInTheDocument();
    act(() => generation.cancel(["assurance"]));
    expect(screen.getByText("assurance: empty / idle")).toBeInTheDocument();
    // A later batch waits as long, so once its answer is in, the cancelled one would have been sent.
    act(() => generation.generate(["prayer_of_confession"], { aiAvailable: true }));
    expect(await screen.findByText("prayer_of_confession: Prayer of Confession written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests).map((r) => (r.body as GenerateLiturgyBody).sections)).toEqual([
      ["opening_prayer"],
      ["prayer_of_confession"],
    ]);
    expect(screen.getByText("assurance: empty / idle")).toBeInTheDocument();
  });
});

/** A generate route that holds every section until the test releases it, so the 4th card waits in the queue. */
function heldRoute() {
  const waiting = new Map<string, () => void>();
  const route = generateRoute(async (section) => {
    await new Promise<void>((resolve) => waiting.set(section, resolve));
    return sectionResult(section, `New ${section}`);
  });
  return { route, release: (key: SectionKey) => waiting.get(key)?.() };
}

const withAssurance = (text: string, origin: "ai" | "typed") => (d: DraftV1): DraftV1 => ({
  ...d,
  liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, assurance: { enabled: true, text, origin } } },
});

describe("a card that changed while it waited (S step 6, before sending)", () => {
  it("Undo while Waiting… sends nothing: the card keeps the text Undo brought back", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route }, undefined, withAssurance("You are forgiven (AI).", "ai"));
    act(() => generation.setUndo("assurance", { kind: "replaced", previous: { text: "You are forgiven.", origin: "typed" } }));
    act(() => generation.generate(FOUR, { aiAvailable: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(MAX_IN_FLIGHT));
    expect(screen.getByText("assurance: You are forgiven (AI). / queued")).toBeInTheDocument();
    act(() => generation.applyUndo("assurance"));
    for (const key of FOUR.slice(0, 3)) held.release(key);
    expect(await screen.findByText("Kept your edits — the new AI draft for Assurance of Pardon was not used.")).toBeInTheDocument();
    expect(screen.getByText("assurance: You are forgiven. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests).map((r) => (r.body as GenerateLiturgyBody).sections[0])).toEqual(FOUR.slice(0, 3));
  });

  it("an edit from another tab while the card waits sends nothing", async () => {
    const held = heldRoute();
    const api = renderProvider({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, "POST /liturgy/generate": held.route });
    act(() => generation.generate(FOUR, { aiAvailable: true }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(MAX_IN_FLIGHT));
    const theirs = withAssurance("From the other tab", "typed")(JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1);
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    expect(await screen.findByText("assurance: From the other tab / queued")).toBeInTheDocument();
    for (const key of FOUR.slice(0, 3)) held.release(key);
    expect(await screen.findByText("Kept your edits — the new AI draft for Assurance of Pardon was not used.")).toBeInTheDocument();
    expect(screen.getByText("assurance: From the other tab / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)).toHaveLength(3);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/generation.test.tsx 2>&1 | grep -E "^ FAIL|Error: Failed|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/lib/liturgy/generation.test.tsx [ src/lib/liturgy/generation.test.tsx ]
Error: Failed to resolve import "./generation" from "src/lib/liturgy/generation.test.tsx". Does the file exist?
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the provider and mount it in the shell**

**Create `frontend/src/lib/liturgy/generation.tsx`:**

```tsx
"use client";

/**
 * `LiturgyGenerationProvider` and `useLiturgyGeneration()` (slice 4 spec,
 * Frontend `generation.tsx`; UX "Generate and Regenerate"). Mounted in the
 * builder shell inside the draft provider, so a run keeps going while the
 * member moves between steps and its result lands in the draft; leaving
 * `/builder`, switching church (the keyed remount) or signing out unmounts it
 * and cancels everything.
 *
 * - Runs, card errors and Undo live here, in memory, never in the draft
 *   (owner answer 1, 2026-09-30: none of them is unsaved work).
 * - `generate(keys, {aiAvailable, bulk})`: with AI off it sends nothing and
 *   marks each switched-on empty card "AI not configured" (S step 0).
 *   Otherwise every key is queued; the batch first reads the sermon text once
 *   (the effective NT reading, WEB for ESV, `queryClient.fetchQuery` through
 *   `passageQuery`, at most 10 s; a failure or a timeout just leaves it out),
 *   then each section is one request, at most 3 in flight.
 * - The card is captured (`captureCard`) when the member asks (the click, or
 *   "Replace text"), not when the request starts. Before a queued request is
 *   sent, and again when its answer arrives, `staleVerdict` decides against
 *   the current draft: "apply" sends it, then writes the text (origin "ai",
 *   Undo when it replaced text, inside the draft update); otherwise nothing
 *   is sent or written and S's toast says why. So text that became the
 *   member's while the card waited (Undo, another tab) is never replaced
 *   without the confirm dialog.
 * - "New service" (a new `created_at`) cancels every run silently and clears
 *   the errors and Undo; a bulk run ends with one toast, "The service
 *   changed, so the AI drafts were discarded.". A result racing that change
 *   (another tab) still meets the stale rule.
 * - A 429 stops the queue: that card and every queued one show the retry
 *   message, with the moment the wait ends (`retryAt`), so leaving the step
 *   and coming back does not restart it. A 401 or a lost church goes to the app's handling
 *   (`reportAuthErrors`) and shows nothing on the card.
 * - A bulk run ends with one toast: "Wrote n sections." or "Wrote k of n
 *   sections. The rest show what went wrong." (cancelled cards not counted).
 */
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchProfile, SectionResult, SermonText } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { generateSection } from "@/lib/queries/liturgy";
import { passageQuery } from "@/lib/queries/passages";

import {
  applyGenerated,
  captureCard,
  restoreCard,
  staleVerdict,
  type CapturedCard,
  type CardSnapshot,
  type StaleVerdict,
} from "./cards";
import { cardErrorFrom, localAiNotConfigured, type CardError } from "./errors";
import { createTaskQueue, type TaskOutcome } from "./queue";
import { buildGenerateRequest, sermonSource, sermonText } from "./request";
import { SECTION_LABELS } from "./sections";

/** At most 3 requests in flight, leaving one of the server's 4 AI slots free (S step 3). */
export const MAX_IN_FLIGHT = 3;
/** How long a batch waits for the sermon text before going without it (S "Sermon text"). */
export const SERMON_WAIT_MS = 10_000;

export type CardRun = { phase: "queued" | "writing"; since: number };
export type UndoEntry = { kind: "replaced" | "cleared"; previous: CardSnapshot };
export type BulkRun = { total: number; done: number };
/**
 * A card's error as the step shows it: `retryAt` (ms since the epoch) is when
 * a 429's wait ends; `bulk` marks an error from "Generate empty sections",
 * announced politely rather than as one alert per card.
 */
export type CardErrorState = CardError & { retryAt?: number; bulk?: boolean };

export type LiturgyGeneration = {
  runs: Partial<Record<SectionKey, CardRun>>;
  errors: Partial<Record<SectionKey, CardErrorState>>;
  undo: Partial<Record<SectionKey, UndoEntry>>;
  /** "Generate empty sections" while it runs. */
  bulk: BulkRun | null;
  generate: (keys: SectionKey[], opts: { aiAvailable: boolean; bulk?: boolean }) => void;
  /** Cancels these cards' runs (every run when omitted); the cards return to where they were. */
  cancel: (keys?: SectionKey[]) => void;
  /** The AI bar's Cancel: the whole bulk run. */
  cancelBulk: () => void;
  dismissError: (key: SectionKey) => void;
  setUndo: (key: SectionKey, entry: UndoEntry | null) => void;
  clearUndo: () => void;
  applyUndo: (key: SectionKey) => void;
};

const GenerationContext = createContext<LiturgyGeneration | null>(null);

type Bulk = { keys: Set<SectionKey>; total: number; done: number; written: number };

/** A queued run that found its card changed before it was sent: nothing is sent. */
class StaleRun extends Error {
  constructor(readonly verdict: Exclude<StaleVerdict, "apply">) {
    super(verdict);
  }
}

export const SERVICE_CHANGED_BULK = "The service changed, so the AI drafts were discarded.";

function staleToast(key: SectionKey, verdict: Exclude<StaleVerdict, "apply">): void {
  const label = SECTION_LABELS[key];
  toast.message(
    verdict === "service_changed"
      ? `The service changed, so the AI draft for ${label} was discarded.`
      : `Kept your edits — the new AI draft for ${label} was not used.`,
  );
}

function errorState(error: CardError, bulk: boolean): CardErrorState {
  return error.retryAfterSeconds === undefined
    ? { ...error, bulk }
    : { ...error, bulk, retryAt: Date.now() + error.retryAfterSeconds * 1000 };
}

function without<T>(record: Partial<Record<SectionKey, T>>, keys: readonly SectionKey[]): Partial<Record<SectionKey, T>> {
  if (!keys.some((key) => key in record)) return record;
  const next = { ...record };
  for (const key of keys) delete next[key];
  return next;
}

function bulkToast(written: number, done: number): void {
  if (done === 0) return;
  if (written === done) toast.message(done === 1 ? "Wrote 1 section." : `Wrote ${done} sections.`);
  else toast.message(`Wrote ${written} of ${done} sections. The rest show what went wrong.`);
}

export function LiturgyGenerationProvider({
  church,
  sermonWaitMs = SERMON_WAIT_MS,
  children,
}: {
  church: Pick<ChurchProfile, "id" | "effective_translation">;
  /** Tests shorten the sermon-text wait. */
  sermonWaitMs?: number;
  children: ReactNode;
}) {
  const { draft, update, peek } = useDraft();
  const api = useApi();
  const queryClient = useQueryClient();
  const [queue] = useState(() => createTaskQueue({ concurrency: MAX_IN_FLIGHT }));
  const [runs, setRuns] = useState<Partial<Record<SectionKey, CardRun>>>({});
  const [errors, setErrors] = useState<Partial<Record<SectionKey, CardErrorState>>>({});
  const [undo, setUndoState] = useState<Partial<Record<SectionKey, UndoEntry>>>({});
  const [bulk, setBulk] = useState<BulkRun | null>(null);
  const mounted = useRef(true);
  /** Cards waiting for their batch's sermon text: key → batch id. */
  const pending = useRef(new Map<SectionKey, number>());
  /** Each batch's sermon-text wait, aborted when all of its cards are cancelled. */
  const batches = useRef(new Map<number, AbortController>());
  const captured = useRef(new Map<SectionKey, CapturedCard>());
  const bulkRef = useRef<Bulk | null>(null);
  const batchSeq = useRef(0);
  const service = useRef(draft.created_at);

  useEffect(() => {
    mounted.current = true;
    const waits = batches.current;
    return () => {
      mounted.current = false;
      queue.cancelAll();
      for (const controller of waits.values()) controller.abort();
    };
  }, [queue]);

  // "New service" (or a saved service loaded): the runs, errors and Undo belonged to the old draft.
  const createdAt = draft.created_at;
  useEffect(() => {
    if (service.current === createdAt) return;
    service.current = createdAt;
    queue.cancelAll();
    for (const controller of batches.current.values()) controller.abort();
    batches.current.clear();
    pending.current.clear();
    captured.current.clear();
    const hadBulk = bulkRef.current !== null;
    bulkRef.current = null;
    setRuns({});
    setErrors({});
    setUndoState({});
    setBulk(null);
    if (hadBulk) toast.message(SERVICE_CHANGED_BULK);
  }, [createdAt, queue]);

  const setError = useCallback((key: SectionKey, error: CardErrorState | null) => {
    setErrors((current) => (error === null ? without(current, [key]) : { ...current, [key]: error }));
  }, []);

  const setUndo = useCallback((key: SectionKey, entry: UndoEntry | null) => {
    setUndoState((current) => (entry === null ? without(current, [key]) : { ...current, [key]: entry }));
  }, []);

  /** A card left the bulk run: settled (counted, `wrote` when applied) or cancelled (not counted). */
  const leaveBulk = useCallback((key: SectionKey, how: "wrote" | "failed" | "cancelled") => {
    const b = bulkRef.current;
    if (b === null || !b.keys.has(key)) return;
    b.keys.delete(key);
    if (how === "cancelled") b.total -= 1;
    else b.done += 1;
    if (how === "wrote") b.written += 1;
    if (b.keys.size === 0) {
      bulkRef.current = null;
      setBulk(null);
      bulkToast(b.written, b.done);
    } else {
      setBulk({ total: b.total, done: b.done });
    }
  }, []);

  /** Drops a card's run: waiting for the sermon text, queued or writing. */
  const dropRun = useCallback(
    (key: SectionKey) => {
      const batch = pending.current.get(key);
      pending.current.delete(key);
      if (batch !== undefined && ![...pending.current.values()].includes(batch)) {
        batches.current.get(batch)?.abort();
        batches.current.delete(batch);
      }
      queue.cancel(key);
      captured.current.delete(key);
    },
    [queue],
  );

  const applyResult = useCallback(
    (key: SectionKey, text: string): boolean => {
      const cap = captured.current.get(key);
      captured.current.delete(key);
      if (!cap) return false;
      const out: { verdict: StaleVerdict; previous: CardSnapshot | null } = { verdict: "apply", previous: null };
      update((d) => {
        out.verdict = staleVerdict(d, key, cap);
        if (out.verdict !== "apply") return d;
        const card = d.liturgy.cards[key];
        out.previous = { text: card.text, origin: card.origin };
        return applyGenerated(d, key, text);
      });
      if (out.verdict !== "apply") {
        staleToast(key, out.verdict);
        return false;
      }
      // Over text: Undo brings it back. Over a blank card: any "Cleared." line is stale now.
      const replaced = out.previous !== null && out.previous.text.trim() !== "";
      setUndo(key, replaced && out.previous !== null ? { kind: "replaced", previous: out.previous } : null);
      return true;
    },
    [update, setUndo],
  );

  const settle = useCallback(
    (key: SectionKey, outcome: TaskOutcome<SectionResult>) => {
      if (!mounted.current) return;
      setRuns((current) => without(current, [key]));
      const inBulk = bulkRef.current?.keys.has(key) ?? false;
      if (!outcome.ok && outcome.error instanceof StaleRun) {
        captured.current.delete(key);
        staleToast(key, outcome.error.verdict);
        leaveBulk(key, "failed");
        return;
      }
      if (outcome.ok) {
        const result = outcome.value;
        if (result.status !== "error" && result.text !== null) {
          leaveBulk(key, applyResult(key, result.text) ? "wrote" : "failed");
          return;
        }
        captured.current.delete(key);
        const failure = cardErrorFrom(result.error ?? new Error("no text"));
        setError(key, failure === null ? null : errorState(failure, inBulk));
        leaveBulk(key, "failed");
        return;
      }
      captured.current.delete(key);
      const e = outcome.error;
      if (e instanceof ApiError && (e.status === 401 || isNoChurchAccess(e))) reportAuthErrors(e, church.id);
      const error = cardErrorFrom(e);
      setError(key, error === null ? null : errorState(error, inBulk));
      leaveBulk(key, error === null ? "cancelled" : "failed");
      if (error !== null && e instanceof ApiError && e.code === "rate_limited") {
        // S step 7: the whole queue stops, and every card still waiting shows the same message.
        const waiting = [...queue.waitingKeys(), ...pending.current.keys()] as SectionKey[];
        const stamped = errorState(error, inBulk);
        for (const other of waiting) {
          const otherInBulk = bulkRef.current?.keys.has(other) ?? false;
          dropRun(other);
          setError(other, { ...stamped, bulk: otherInBulk });
          leaveBulk(other, "failed");
        }
        setRuns((current) => without(current, waiting));
      }
    },
    [applyResult, church.id, dropRun, leaveBulk, queue, setError],
  );

  const loadSermon = useCallback(
    (signal: AbortSignal): Promise<SermonText | null> => {
      const source = sermonSource(peek(), church.effective_translation);
      if (source === null) return Promise.resolve(null);
      return new Promise((resolve) => {
        const done = (value: SermonText | null) => {
          clearTimeout(timer);
          signal.removeEventListener("abort", onAbort);
          resolve(value);
        };
        const onAbort = () => done(null);
        const timer = setTimeout(() => done(null), sermonWaitMs);
        signal.addEventListener("abort", onAbort, { once: true });
        queryClient.fetchQuery(passageQuery(api, source.translation, source.ref)).then(
          (passage) => done(sermonText(source.ref, passage)),
          () => done(null),
        );
      });
    },
    [api, church.effective_translation, peek, queryClient, sermonWaitMs],
  );

  const send = useCallback(
    (key: SectionKey, sermon: SermonText | null) => {
      queue.push(
        key,
        (signal) => {
          // S step 6 before sending: text that became the member's while the card waited is never replaced.
          const draft = peek();
          const cap = captured.current.get(key);
          const verdict = cap === undefined ? "service_changed" : staleVerdict(draft, key, cap);
          if (verdict !== "apply") return Promise.reject(new StaleRun(verdict));
          setRuns((current) => ({ ...current, [key]: { phase: "writing", since: Date.now() } }));
          return generateSection(api.church, key, buildGenerateRequest(draft, key, sermon), signal);
        },
        (outcome) => settle(key, outcome),
      );
    },
    [api, peek, queue, settle],
  );

  const generate = useCallback(
    (keys: SectionKey[], { aiAvailable, bulk: isBulk = false }: { aiAvailable: boolean; bulk?: boolean }) => {
      const draft = peek();
      if (!aiAvailable) {
        // S step 0: nothing is sent; each targeted switched-on empty card says so.
        const empty = keys.filter((key) => {
          const card = draft.liturgy.cards[key];
          return card.enabled && card.text.trim() === "";
        });
        const marked = errorState(localAiNotConfigured(), isBulk);
        setErrors((current) => ({ ...current, ...Object.fromEntries(empty.map((key) => [key, marked])) }));
        return;
      }
      const busy = new Set<SectionKey>([...pending.current.keys(), ...(queue.runningKeys() as SectionKey[]), ...(queue.waitingKeys() as SectionKey[])]);
      const fresh = keys.filter((key) => !busy.has(key));
      if (fresh.length === 0) return;
      const since = Date.now();
      // The card as the member saw it when they asked (the click, or "Replace text").
      for (const key of fresh) captured.current.set(key, captureCard(draft, key));
      setErrors((current) => without(current, fresh));
      setRuns((current) => ({ ...current, ...Object.fromEntries(fresh.map((key) => [key, { phase: "queued", since }])) }));
      if (isBulk) {
        bulkRef.current = { keys: new Set(fresh), total: fresh.length, done: 0, written: 0 };
        setBulk({ total: fresh.length, done: 0 });
      }
      const batch = ++batchSeq.current;
      const controller = new AbortController();
      batches.current.set(batch, controller);
      for (const key of fresh) pending.current.set(key, batch);
      void loadSermon(controller.signal).then((sermon) => {
        batches.current.delete(batch);
        if (!mounted.current) return;
        for (const key of fresh) {
          if (pending.current.get(key) !== batch) continue; // cancelled while waiting
          pending.current.delete(key);
          send(key, sermon);
        }
      });
    },
    [loadSermon, peek, queue, send],
  );

  const cancel = useCallback(
    (keys?: SectionKey[]) => {
      const targets =
        keys ?? ([...pending.current.keys(), ...queue.runningKeys(), ...queue.waitingKeys()] as SectionKey[]);
      for (const key of targets) {
        dropRun(key);
        leaveBulk(key, "cancelled");
      }
      setRuns((current) => without(current, targets));
    },
    [dropRun, leaveBulk, queue],
  );

  const cancelBulk = useCallback(() => {
    const b = bulkRef.current;
    if (b) cancel([...b.keys]);
  }, [cancel]);

  const dismissError = useCallback((key: SectionKey) => setError(key, null), [setError]);
  const clearUndo = useCallback(() => setUndoState({}), []);
  const applyUndo = useCallback(
    (key: SectionKey) => {
      const entry = undo[key];
      if (!entry) return;
      update((d) => restoreCard(d, key, entry.previous));
      setUndo(key, null);
    },
    [undo, update, setUndo],
  );

  const value = useMemo<LiturgyGeneration>(
    () => ({ runs, errors, undo, bulk, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo }),
    [runs, errors, undo, bulk, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo],
  );
  return <GenerationContext value={value}>{children}</GenerationContext>;
}

/** The generation state and actions. Throws outside `LiturgyGenerationProvider` (the builder shell mounts it). */
export function useLiturgyGeneration(): LiturgyGeneration {
  const value = useContext(GenerationContext);
  if (!value) throw new Error("useLiturgyGeneration() must be used inside <LiturgyGenerationProvider>.");
  return value;
}
```

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

```tsx
 * every step (slice 2c).
```

**with:**

```tsx
 * every step (slice 2c). `<LiturgyGenerationProvider>` holds the Liturgy
 * step's AI runs, so they keep going on the other steps (slice 4b).
```

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

```tsx
import { stepFromPath } from "@/lib/draft/steps";
import { useMeContext } from "@/lib/me-context";
```

**with:**

```tsx
import { stepFromPath } from "@/lib/draft/steps";
import { LiturgyGenerationProvider } from "@/lib/liturgy/generation";
import { useMeContext } from "@/lib/me-context";
```

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

```tsx
      <LectionarySync>
        <BuilderFrame church={profile.data}>{children}</BuilderFrame>
      </LectionarySync>
```

**with:**

```tsx
      <LiturgyGenerationProvider church={profile.data}>
        <LectionarySync>
          <BuilderFrame church={profile.data}>{children}</BuilderFrame>
        </LectionarySync>
      </LiturgyGenerationProvider>
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy/generation.test.tsx src/components/builder 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  7 passed (7)`, `      Tests  97 passed (97)` (the shell, Hymns and Date & readings tests pass with the provider mounted, sending nothing); the suite ` Test Files  73 passed (73)`, `      Tests  476 passed (476)`; `typecheck 0` and `lint 0`; ` M frontend/src/components/builder/builder-shell.tsx` and the two new files as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/generation.tsx frontend/src/lib/liturgy/generation.test.tsx frontend/src/components/builder/builder-shell.tsx
git commit -m "Liturgy: the generation provider, mounted in the builder shell (S generation.tsx; BC-13, BC-21)" -m "Runs, card errors and Undo live in memory in LiturgyGenerationProvider,
inside the builder shell, so a run keeps going on other steps and lands in
the draft. Without AI it sends nothing and marks empty cards. A batch
reads the sermon text once (WEB for ESV, at most 10 s, left out on
failure), then sends one section per request, 3 at a time; a result is
applied or dropped by the stale rule with its toast; a 429 stops the
queue; a bulk run ends with one toast. Unmounting cancels everything.
Frontend 471 -> 476 tests in 72 -> 73 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 3 files changed.

**Review checkpoint (T3-T6, batch B):** the request never sends `overrides` or ESV text; the timeout row is 100 000; the fixtures match 4a's shared files; the store's defaults never outrank another tab's edit; the provider sends nothing while idle, never delivers a cancelled result, and applies S step 6 inside the update; counts match.

### Task 7: The kit's dialog and the growing textarea (S "Frontend changes" shadcn list, UX "Layout"; F §4.9 items 1 and 6; clarifications 19, 20, 36)

Two small pieces the step needs. `components/ui/dialog.tsx` is the base-nova `Dialog` ("Add custom element", T10); the registry (ui.shadcn.com) is blocked from the container, so it is rebuilt from the upstream source exactly as 2b, 2c and 3b rebuilt theirs (clarification 19). S's other kit components exist already: `switch` (3b), `textarea`, `badge`, `alert`, `collapsible`, `select`, `dropdown-menu` (1-2c). `lib/use-autosize.ts` is S's `useAutosize`: the kit's `Textarea` already sizes itself to its content with `field-sizing: content` where the browser supports it, so the hook sets the height from the content only where it does not (older iOS Safari), capped at 60% of the window, and again when the field comes back with the same text (its third argument, `shown`: a card switched on; clarification 36); the cards cap the field with `max-h-[60vh]` so it scrolls past that (clarification 20).

Provenance of `dialog.tsx`: at shadcn-ui/ui commit `db2db460a26fa84fb65c8d903b213925fbdee9ed` (the commit 2b, 2c and 3b pinned), the plan's writer fetched `apps/v4/registry/bases/base/ui/dialog.tsx` (sha256 `aba6df6cbf51a1edcc22e415a3a46a666fc8cb66729e47b3ed2ecd97f166adff`) and `apps/v4/registry/styles/style-nova.css` (sha256 `5d5751579c015b61e77cf0822862a43ac79f3e6fed236a17624be8e6d1ebea1d`) from raw.githubusercontent.com, ran the file through the installed shadcn 4.21.0 CLI's `createStyleMap`, `transformStyle`, `transformIcons`, `transformFont` and `transformMenu`, mapped `@/registry/bases/base/ui/button` to `@/components/ui/button`, and formatted it with Prettier 3.9.9 and `prettier-plugin-tailwindcss` 0.8.1 (`semi: false`, `trailingComma: "es5"`, `tailwindFunctions: ["cn", "cva"]`, `tailwindStylesheet: src/app/globals.css`). The same pipeline reproduces the repo's `sheet.tsx` byte for byte after its header comment (checked while planning). The only change from that output is the header comment. Optional check that the upstream file is unchanged (skip it if the host is unreachable; the code below is the record):

```bash
curl -fsS "https://raw.githubusercontent.com/shadcn-ui/ui/db2db460a26fa84fb65c8d903b213925fbdee9ed/apps/v4/registry/bases/base/ui/dialog.tsx" | sha256sum | cut -c1-64
```

**Expected:** `aba6df6cbf51a1edcc22e415a3a46a666fc8cb66729e47b3ed2ecd97f166adff`.

**Files:**
- Create: `frontend/src/components/ui/dialog.tsx` (clarification 19's file, or the generated one), `frontend/src/lib/use-autosize.ts`
- Test: `frontend/src/lib/use-autosize.test.tsx` (new, 3). The dialog is exercised by T10.

**Interfaces:**
- Consumes: `@base-ui/react/dialog` (installed), `Button` (1), `XIcon` (lucide).
- Produces: `components/ui/dialog.tsx`: `Dialog`, `DialogClose`, `DialogContent` (`showCloseButton?`), `DialogDescription`, `DialogFooter`, `DialogHeader`, `DialogOverlay`, `DialogPortal`, `DialogTitle`, `DialogTrigger`. `lib/use-autosize.ts`: `useAutosize(ref: RefObject<HTMLTextAreaElement | null>, value: string, shown = true): void`, `AUTOSIZE_MAX_SHARE = 0.6`. Later users: T8 and T10 (the cards' textareas), T10 (the dialog).

Counts after this task: frontend **479 passed in 74 files**.

- [ ] **Step 1 (agent): Check the starting point, and try the registry**

```bash
git status --short
ls frontend/src/components/ui/ | tr '\n' ' '; echo
(cd frontend && timeout 120 npx shadcn@latest add dialog --yes 2>&1 | grep -m1 -o "Request to .* failed")
git status --short
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `alert-dialog.tsx alert.tsx avatar.tsx badge.tsx button.test.tsx button.tsx card.tsx collapsible.tsx combobox.tsx dropdown-menu.tsx input-group.tsx input.tsx label.tsx radio-group.tsx select.tsx sheet.tsx skeleton.tsx sonner.tsx switch.tsx tabs.tsx textarea.tsx tooltip.tsx` (no `dialog.tsx`); `Request to https://ui.shadcn.com/r/styles/base-nova/dialog.json failed` (the registry is blocked; shadcn 4.21 adds "Request was cancelled.") and `git status --short` still shows nothing new; ` Test Files  73 passed (73)`, `      Tests  476 passed (476)`. If the registry answers and writes `frontend/src/components/ui/dialog.tsx`, keep the generated file, skip its **Create** below, and say so in the commit body.

- [ ] **Step 2 (agent): Write the failing test**

**Create `frontend/src/lib/use-autosize.test.tsx`:**

```tsx
/**
 * `useAutosize` (slice 4 spec, UX "Layout": textareas grow with their content
 * up to 60 vh, then scroll): where the browser sizes a field to its content
 * itself (`field-sizing: content`) the hook does nothing; elsewhere it sets
 * the height from the content, capped at 60% of the window, and again when
 * the field comes back (a card switched on).
 */
import { render, screen } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useAutosize } from "./use-autosize";

function Field({ value }: { value: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value);
  return <textarea ref={ref} aria-label="Text" value={value} readOnly />;
}

/** A card's field, rendered only while the card is on. */
function Toggled({ on, value }: { on: boolean; value: string }) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value, on);
  return on ? <textarea ref={ref} aria-label="Text" value={value} readOnly /> : null;
}

function withScrollHeight(px: number) {
  vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(px);
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("useAutosize (S Layout)", () => {
  it("grows the field to its content and stops at 60% of the window, where the browser cannot", () => {
    vi.stubGlobal("CSS", { supports: () => false });
    vi.spyOn(window, "innerHeight", "get").mockReturnValue(1000);
    withScrollHeight(240);
    const view = render(<Field value="Leader: Come!" />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("242px");
    withScrollHeight(900);
    view.rerender(<Field value={"Leader: Come!\n".repeat(40)} />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("600px");
  });

  it("sizes the field again when it comes back with the same text", () => {
    vi.stubGlobal("CSS", { supports: () => false });
    vi.spyOn(window, "innerHeight", "get").mockReturnValue(1000);
    withScrollHeight(240);
    const view = render(<Toggled on value="Leader: Come!" />);
    view.rerender(<Toggled on={false} value="Leader: Come!" />);
    expect(screen.queryByRole("textbox")).toBeNull();
    view.rerender(<Toggled on value="Leader: Come!" />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("242px");
  });

  it("leaves the height to the browser when it sizes fields to their content", () => {
    vi.stubGlobal("CSS", { supports: (property: string, value: string) => property === "field-sizing" && value === "content" });
    withScrollHeight(240);
    render(<Field value="Leader: Come!" />);
    expect(screen.getByRole("textbox", { name: "Text" }).style.height).toBe("");
  });
});
```

- [ ] **Step 3 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/lib/use-autosize.test.tsx 2>&1 | grep -E "^ FAIL|Error: Failed|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/lib/use-autosize.test.tsx [ src/lib/use-autosize.test.tsx ]
Error: Failed to resolve import "./use-autosize" from "src/lib/use-autosize.test.tsx". Does the file exist?
      Tests  no tests
```

- [ ] **Step 4 (agent, clarifications 19 and 20): Write the dialog and `useAutosize`**

**Create `frontend/src/components/ui/dialog.tsx`:**

```tsx
"use client"

// Rebuilt from the upstream shadcn source (slice 4b plan clarification 19, as
// slices 2b, 2c and 3b did): shadcn-ui/ui@db2db460
// apps/v4/registry/bases/base/ui/dialog.tsx with
// apps/v4/registry/styles/style-nova.css, through the shadcn 4.21.0 CLI's own
// style, icon and font transforms and Prettier's Tailwind class order. The
// only change from that output is this comment. Replace it with the file
// `npx shadcn@latest add dialog` generates when the registry is reachable.

import * as React from "react"
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"
import { cn } from "cn"

import { Button } from "@/components/ui/button"
import { XIcon } from "lucide-react"

function Dialog({ ...props }: DialogPrimitive.Root.Props) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />
}

function DialogTrigger({ ...props }: DialogPrimitive.Trigger.Props) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />
}

function DialogPortal({ ...props }: DialogPrimitive.Portal.Props) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />
}

function DialogClose({ ...props }: DialogPrimitive.Close.Props) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />
}

function DialogOverlay({
  className,
  ...props
}: DialogPrimitive.Backdrop.Props) {
  return (
    <DialogPrimitive.Backdrop
      data-slot="dialog-overlay"
      className={cn(
        "fixed inset-0 isolate z-50 bg-black/10 duration-100 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0",
        className
      )}
      {...props}
    />
  )
}

function DialogContent({
  className,
  children,
  showCloseButton = true,
  ...props
}: DialogPrimitive.Popup.Props & {
  showCloseButton?: boolean
}) {
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Popup
        data-slot="dialog-content"
        className={cn(
          "fixed top-1/2 left-1/2 z-50 grid w-full max-w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 gap-4 rounded-xl bg-popover p-4 text-sm text-popover-foreground ring-1 ring-foreground/10 duration-100 outline-none sm:max-w-sm data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
          className
        )}
        {...props}
      >
        {children}
        {showCloseButton && (
          <DialogPrimitive.Close
            data-slot="dialog-close"
            render={
              <Button
                variant="ghost"
                className="absolute top-2 right-2"
                size="icon-sm"
              />
            }
          >
            <XIcon />
            <span className="sr-only">Close</span>
          </DialogPrimitive.Close>
        )}
      </DialogPrimitive.Popup>
    </DialogPortal>
  )
}

function DialogHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-header"
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  )
}

function DialogFooter({
  className,
  showCloseButton = false,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
}) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "-mx-4 -mb-4 flex flex-col-reverse gap-2 rounded-b-xl border-t bg-muted/50 p-4 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close render={<Button variant="outline" />}>
          Close
        </DialogPrimitive.Close>
      )}
    </div>
  )
}

function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn(
        "font-heading text-base leading-none font-medium",
        className
      )}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: DialogPrimitive.Description.Props) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn(
        "text-sm text-muted-foreground *:[a]:underline *:[a]:underline-offset-3 *:[a]:hover:text-foreground",
        className
      )}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}
```

**Create `frontend/src/lib/use-autosize.ts`:**

```ts
"use client";

/**
 * Textareas grow with their content up to 60 vh, then scroll (slice 4 spec,
 * UX "Layout"). The kit's `Textarea` already sizes itself to its content with
 * `field-sizing: content` where the browser supports it; this hook does the
 * same for a browser that does not (older iOS Safari), by setting the height
 * from `scrollHeight` whenever the value changes. The caller caps the field
 * with `max-h-[60vh]` so it scrolls past that.
 */
import { useLayoutEffect, type RefObject } from "react";

/** The share of the window a field may grow to. */
export const AUTOSIZE_MAX_SHARE = 0.6;

function sizesItself(): boolean {
  return typeof CSS !== "undefined" && typeof CSS.supports === "function" && CSS.supports("field-sizing", "content");
}

/** `shown`: false while the field is not rendered (a card switched off), so it is sized again when it comes back. */
export function useAutosize(ref: RefObject<HTMLTextAreaElement | null>, value: string, shown = true): void {
  useLayoutEffect(() => {
    const field = ref.current;
    if (field === null || sizesItself()) return;
    field.style.height = "auto";
    // scrollHeight leaves out the 1 px borders.
    const height = Math.min(field.scrollHeight + 2, Math.round(window.innerHeight * AUTOSIZE_MAX_SHARE));
    field.style.height = `${height}px`;
  }, [ref, value, shown]);
}
```

- [ ] **Step 5 (agent): Run the test, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/use-autosize.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  1 passed (1)`, `      Tests  3 passed (3)`; the suite ` Test Files  74 passed (74)`, `      Tests  479 passed (479)`; `typecheck 0` and `lint 0`; the three new files as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/ui/dialog.tsx frontend/src/lib/use-autosize.ts frontend/src/lib/use-autosize.test.tsx
git commit -m "Kit: the base-nova dialog and a textarea that grows to 60 vh (S Frontend changes; F §4.9)" -m "dialog.tsx is rebuilt from the upstream shadcn source (shadcn-ui/ui@db2db460,
base-nova, through the installed CLI's transforms and Prettier), because
the build container cannot reach the registry; only its header comment is
added. useAutosize sizes a textarea to its content where the browser
cannot (field-sizing: content), capped at 60% of the window.
Frontend 476 -> 479 tests in 73 -> 74 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 3 files changed.

### Task 8: The step: the order of worship, the section cards, the sermon title and the landmarks (S UX "Layout", "Sermon title", "Section card", "Benediction and the church default", "Loading, error and empty states"; BC-1, BC-3, BC-9, BC-15, BC-17, BC-18; owner answer 3; clarifications 1, 21, 24, 28, 31, 34, 35, 36)

The screen, without the AI yet (T9) and without communion and custom elements (T10). `LiturgyStep` loads `GET /liturgy/config` (a skeleton while it loads; "Couldn't load the liturgy sections." with the server's message and Retry when a first load fails, never when a background refetch fails), then lays out the heading "Liturgy" (clarification 21), the sermon title and the order of worship from the config's outline, in the Word files' order: a `SectionCard` for each section, an `OutlineLandmark` row for the hymns, the readings, the sermon title and the creed (clarification 24). The cards follow S's "Section card": the switch "Include {Label}" (its touch area grown to 46 px on the use, not in the generated file; clarification 31), the label, the status chip by origin, the "Pastor's copy only" chip (below `sm` the chips take their own line under the title; clarification 35), and a ⋯ menu with **Clear text** (with an Undo line) and, on the Benediction when it no longer follows the church default, **Use church default**; when on, a textarea growing to 60 vh with its placeholder, the 20 000-character limit and a counter past 18 000, and the section's hint (the Assurance's fixed "People: Thanks be to God! Amen." line and its hint; the Benediction's hint only while it follows the default); when off, only "Off — not in the service. Any text is kept." Typing makes the text the user's; the Benediction follows the church default until edited (T5 keeps it there). The hint, the Assurance's line and the counter are the textarea's description (`aria-describedby`). The card's heading can take focus (`tabIndex={-1}`): after Clear text focus goes to "Undo", after Undo to the heading (clarification 34). On mount the step scrolls to the card the address names (`#card-…`), for Review's links; a malformed address scrolls nowhere (clarification 36). The step's Undo lines go when it unmounts. Owner answer 3 needs no new code: 2b's `StepFooter` already hides below `md` while a text field has focus (`useKeyboardOpen`, focus-based rather than `visualViewport`; clarification 28), so this task adds its test on this step. The page still renders the placeholder until T11 turns the step on; these tests render `LiturgyStep` inside the real builder layout.

**Files:**
- Create: `frontend/src/components/builder/liturgy/liturgy-step.tsx`, `section-card.tsx`, `outline-landmark.tsx`, `sermon-title-field.tsx` (all in `frontend/src/components/builder/liturgy/`)
- Test: `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` (new, 11)

**Interfaces:**
- Consumes: `useLiturgyConfig` and the fixtures (T4); `useLiturgyGeneration().undo`, `setUndo`, `clearUndo`, `applyUndo`, `dismissError` (T6); `editCardText`, `setCardEnabled`, `clearCard`, `restoreChurchDefault`, `setSermonTitle` (T2); `useAutosize` (T7); `effectivePicks` (2c); `useChurchProfile` (2a); the kit (`Switch`, `Textarea`, `Badge`, `DropdownMenu`, `Input`, `Label`, `Skeleton`, `ErrorState`).
- Produces: `LiturgyStep()`; `SectionCard({spec, assuranceResponse, defaultBenediction, maxLength})` with `ORIGIN_CHIPS` and `COUNTER_FROM = 18_000`; `OutlineLandmark({item, draft})`; `SermonTitleField({maxLength})` and `SERMON_TITLE_ID = "sermon-title"`. DOM ids `card-{key}` (5a's Review links). Later users: T9 (the AI on the cards, the AI bar), T10 (communion, custom elements), T11 (the page).

Counts after this task: frontend **490 passed in 75 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/builder/liturgy 2>&1 | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/components/builder/liturgy': No such file or directory`; ` Test Files  74 passed (74)`, `      Tests  479 passed (479)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`:**

```tsx
/**
 * The Liturgy step (slice 4 spec, "User experience", Testing "dom"; F §4.6,
 * §4.8). The step runs inside the real builder layout against the fake API.
 * The clock is Tuesday, September 29, 2026 (only `Date` is faked), so a fresh
 * draft is dated Sunday, October 4, 2026 (a first Sunday), and the lectionary
 * answers "no readings", so the readings stay as each test seeds them.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import { editScriptureLines, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { editCardText } from "@/lib/liturgy/cards";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  gg2013,
  lectionaryRoute,
  liturgyConfig,
  me,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyStep } from "./liturgy-step";

const KEY = draftKey(USER_ID, church().id);
const [, , COME, , , , , , SENT] = gg2013();
const OCT_4 = "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46";

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function withCard(key: SectionKey, patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>, d: DraftV1 = testDraft()): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
}

/** The step in the builder layout, with a Toaster for toast text; `routes` replace the defaults. */
function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}, extra: ReactNode = null) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <LiturgyStep />
        {extra}
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/liturgy" },
  );
  return { ...view, api };
}

function card(label: string) {
  return screen.getByRole("region", { name: label });
}

/** Each outline row: a card's title, or a landmark row's text. */
function outline(): string[] {
  const list = screen.getByRole("list", { name: "Order of worship" });
  return within(list)
    .getAllByRole("listitem")
    .map((li) => li.querySelector("h3")?.textContent ?? li.textContent ?? "");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  window.location.hash = "";
});

describe("the Liturgy step (S User experience)", () => {
  it("shows the step's shape while the sections load, and Couldn't load the liturgy sections. with Retry when they fail", async () => {
    let fail = true;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user } = renderStep(testDraft(), {
      "GET /liturgy/config": async () => {
        await gate;
        return fail ? fakeError(500, "internal_error", "Something went wrong.") : liturgyConfig();
      },
    });
    expect(await screen.findByRole("status", { name: "Loading the liturgy" })).toBeInTheDocument();
    release();
    expect(await screen.findByText("Couldn't load the liturgy sections.")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("region", { name: "Call to Worship" })).toBeInTheDocument();
    expect(screen.queryByText("Couldn't load the liturgy sections.")).toBeNull();
  });

  it("lays out the order of worship as the Word files print it, with the draft's hymns, readings and title", async () => {
    const hymns = (d: DraftV1): DraftV1 => ({
      ...d,
      hymns: {
        ...d.hymns,
        slots: {
          opening: { hymn_id: COME.id, title: COME.title, number: COME.number, hymnal: "GG2013" },
          response: null,
          closing: { hymn_id: SENT.id, title: SENT.title, number: null, hymnal: "GG2013" },
        },
      },
    });
    const view = renderStep(hymns(editScriptureLines(testDraft(), OCT_4)));
    expect(await screen.findByRole("heading", { level: 2, name: "Liturgy" })).toBeInTheDocument();
    // No picks: the automatic readings, marked auto; the NT reading is never the Psalm.
    expect(outline()).toEqual([
      "Call to Worship",
      "Opening Prayer",
      "First Hymn · Come, Thou Almighty King",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "First Reading · Isaiah 5:1-7 auto",
      "New Testament Reading · Philippians 3:4b-14 auto",
      "Sermon Title · [Sermon title]",
      "Affirmation of Faith · Apostles' Creed",
      "Second Hymn",
      "Prayers of the People",
      "Offertory Prayer",
      "Third Hymn · Sent Forth by God's Blessing",
      "Benediction",
    ]);
    expect(screen.getByRole("link", { name: "First Hymn · Come, Thou Almighty King" })).toHaveAttribute("href", "/builder/hymns");
    expect(screen.getByRole("link", { name: "First Reading · Isaiah 5:1-7 auto" })).toHaveAttribute("href", "/builder/readings");
    view.unmount();

    // Explicit picks show without "auto"; a title shows as typed.
    const picked = setPick(setPick(editScriptureLines(testDraft(), OCT_4), "ot", "Isaiah 5:1-7"), "nt", "Matthew 21:33-46");
    renderStep({ ...picked, liturgy: { ...picked.liturgy, sermon_title: "Living Water" } });
    expect(await screen.findByRole("link", { name: "First Reading · Isaiah 5:1-7" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "New Testament Reading · Matthew 21:33-46" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sermon Title · Living Water" })).toBeInTheDocument();
  });

  it("writes what is typed to the draft as the user's text, and keeps it across a reload", async () => {
    const { user, unmount } = renderStep();
    const text = await screen.findByRole("textbox", { name: "Call to Worship" });
    expect(text).toHaveAttribute("placeholder", "Type your own text, or tap Generate.");
    expect(within(card("Call to Worship")).getByText("Empty")).toBeInTheDocument();
    await user.type(text, "Come, let us worship.");
    expect(within(card("Call to Worship")).getByText("Your text")).toBeInTheDocument();
    await waitFor(() =>
      expect(stored().liturgy.cards.call_to_worship).toEqual({ enabled: true, text: "Come, let us worship.", origin: "typed" }),
    );
    unmount();
    renderStep(stored());
    expect(await screen.findByRole("textbox", { name: "Call to Worship" })).toHaveValue("Come, let us worship.");
  });

  it("shows each section's hints and switches; a card switched off keeps its text and says so", async () => {
    const { user } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }));
    await screen.findByRole("region", { name: "Call to Worship" });
    expect(within(card("Call to Worship")).getByText("Start lines with “Leader:” or “People:”. People lines print in bold.")).toBeInTheDocument();
    expect(within(card("Prayer of Confession")).getByText("Printed in bold for everyone to read together.")).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByText("People: Thanks be to God! Amen.")).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByText("Added automatically after your text.")).toBeInTheDocument();
    // The hints are the fields' descriptions.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveAccessibleDescription(
      "Start lines with “Leader:” or “People:”. People lines print in bold.",
    );
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveAccessibleDescription(
      "People: Thanks be to God! Amen. Added automatically after your text.",
    );
    const prayers = card("Prayers of the People");
    expect(within(prayers).getByText("Pastor's copy only")).toBeInTheDocument();
    expect(within(prayers).getByRole("switch", { name: "Include Prayers of the People" })).not.toBeChecked();
    expect(within(prayers).getByText("Off — not in the service. Any text is kept.")).toBeInTheDocument();
    expect(within(prayers).queryByRole("textbox")).toBeNull();

    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(opening).queryByRole("textbox")).toBeNull();
    expect(within(opening).getByText("Off — not in the service. Any text is kept.")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.cards.opening_prayer).toEqual({ enabled: false, text: "Gracious God", origin: "typed" }));
    await user.click(within(opening).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(opening).getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God");
  });

  it("shows the church's default benediction and follows it until edited; Use church default follows it again", async () => {
    const { user, queryClient } = renderStep();
    const benediction = await screen.findByRole("region", { name: "Benediction" });
    const text = within(benediction).getByRole("textbox", { name: "Benediction" });
    expect(text).toHaveValue("Halverson");
    expect(within(benediction).getByText("Church default")).toBeInTheDocument();
    expect(within(benediction).getByText("Your church's default benediction. Admins can change it in Settings.")).toBeInTheDocument();
    // An admin changes the default (6a) and the profile refetches.
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "The Lord bless you." })));
    await waitFor(() => expect(text).toHaveValue("The Lord bless you."));
    await user.clear(text);
    await user.type(text, "Go in peace.");
    expect(within(benediction).getByText("Your text")).toBeInTheDocument();
    expect(within(benediction).queryByText(/Your church's default benediction/)).toBeNull();
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "Halverson" })));
    await user.click(within(benediction).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(text).toHaveValue("Halverson");
    expect(within(benediction).getByText("Church default")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" }));
  });

  it("Clear text empties a card with an Undo line; Undo brings the text back, and the line goes on the next edit", async () => {
    const { user } = renderStep(withCard("call_to_worship", { text: "Come.", origin: "typed" }));
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    expect(within(card("Opening Prayer")).getByRole("button", { name: "More actions for Opening Prayer" })).toBeDisabled();
    await user.click(within(cw).getByRole("button", { name: "More actions for Call to Worship" }));
    expect(screen.queryByRole("menuitem", { name: "Use church default" })).toBeNull();
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    const text = within(cw).getByRole("textbox", { name: "Call to Worship" });
    expect(text).toHaveValue("");
    expect(within(cw).getByText("Empty")).toBeInTheDocument();
    expect(within(cw).getByText("Cleared.")).toBeInTheDocument();
    await user.click(within(cw).getByRole("button", { name: "Undo" }));
    expect(text).toHaveValue("Come.");
    expect(within(cw).getByText("Your text")).toBeInTheDocument();
    expect(within(cw).queryByText("Cleared.")).toBeNull();
    await user.click(within(cw).getByRole("button", { name: "More actions for Call to Worship" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    await user.type(text, "Welcome");
    expect(within(cw).queryByText("Cleared.")).toBeNull();
    expect(within(cw).queryByRole("button", { name: "Undo" })).toBeNull();
  });

  it("writes the sermon title, shows it in the Sermon row, and the row focuses the field", async () => {
    const { user } = renderStep();
    const title = await screen.findByRole("textbox", { name: "Sermon title" });
    expect(title).toHaveAttribute("placeholder", "e.g. Living Water");
    expect(title).toHaveAttribute("maxLength", "300");
    expect(screen.getByText("Printed in the bulletin and the pastor's copy. If blank, both show “[Sermon title]”.")).toBeInTheDocument();
    await user.type(title, "Living Water");
    const row = screen.getByRole("button", { name: "Sermon Title · Living Water" });
    await waitFor(() => expect(stored().liturgy.sermon_title).toBe("Living Water"));
    await user.click(screen.getByRole("textbox", { name: "Call to Worship" }));
    await user.click(row);
    expect(title).toHaveFocus();
  });

  it("shows typed and AI text as text, never as markup, and counts characters past 18,000", async () => {
    let d = withCard("call_to_worship", { text: "<b>x</b>", origin: "typed" });
    d = withCard("opening_prayer", { text: "<i>AI</i> & more", origin: "ai" }, d);
    d = withCard("offertory_prayer", { text: "y".repeat(18_001), origin: "typed" }, d);
    d = withCard("prayer_of_confession", { text: "z".repeat(18_000), origin: "typed" }, d);
    renderStep({ ...d, liturgy: { ...d.liturgy, sermon_title: "<script>t</script>" } });
    expect(await screen.findByRole("textbox", { name: "Call to Worship" })).toHaveValue("<b>x</b>");
    expect(within(card("Opening Prayer")).getByRole("textbox")).toHaveValue("<i>AI</i> & more");
    expect(within(card("Opening Prayer")).getByText("AI draft")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sermon Title · <script>t</script>" })).toBeInTheDocument();
    expect(document.querySelector("b, i, script")).toBeNull();
    expect(within(card("Offertory Prayer")).getByText("18,001 / 20,000")).toBeInTheDocument();
    expect(within(card("Offertory Prayer")).getByRole("textbox")).toHaveAttribute("maxLength", "20000");
    expect(within(card("Prayer of Confession")).queryByText(/\/ 20,000/)).toBeNull();
  });

  it("hides the step footer below md while a text field has focus, and shows it again on blur (owner answer 3)", async () => {
    renderStep();
    const text = await screen.findByRole("textbox", { name: "Call to Worship" });
    const footer = screen.getByRole("navigation", { name: "Step navigation" });
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    act(() => text.focus());
    expect(footer).toHaveAttribute("data-keyboard-open");
    expect(footer.className).toContain("max-md:hidden");
    act(() => text.blur());
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    act(() => screen.getByRole("textbox", { name: "Sermon title" }).focus());
    expect(footer).toHaveAttribute("data-keyboard-open");
  });

  it("scrolls to the card the address names, as Review's links do", async () => {
    window.location.hash = "#card-assurance";
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    renderStep();
    await screen.findByRole("region", { name: "Assurance of Pardon" });
    await waitFor(() => expect(scroll).toHaveBeenCalled());
    expect(scroll.mock.contexts[0]).toBe(document.getElementById("card-assurance"));
  });
});

describe("the card's own draft (S Card origin transitions)", () => {
  it("never shows another card's edit, and a typed card keeps its origin when switched", async () => {
    const d = editCardText(testDraft(), "assurance", "You are forgiven.");
    const { user } = renderStep(d);
    const assurance = await screen.findByRole("region", { name: "Assurance of Pardon" });
    await user.click(within(assurance).getByRole("switch", { name: "Include Assurance of Pardon" }));
    await user.click(within(assurance).getByRole("switch", { name: "Include Assurance of Pardon" }));
    expect(within(assurance).getByText("Your text")).toBeInTheDocument();
    expect(within(card("Call to Worship")).getByText("Empty")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "^ FAIL|Error: Failed|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx [ src/components/builder/liturgy/liturgy-step.test.tsx ]
Error: Failed to resolve import "./liturgy-step" from "src/components/builder/liturgy/liturgy-step.test.tsx". Does the file exist?
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the step, the cards, the landmarks and the sermon title**

**Create `frontend/src/components/builder/liturgy/sermon-title-field.tsx`:**

```tsx
"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useDraft } from "@/lib/draft/context";
import { setSermonTitle } from "@/lib/liturgy/cards";

/** The field's id: the Sermon row in the order of worship focuses it. */
export const SERMON_TITLE_ID = "sermon-title";

/**
 * The sermon title (S UX "Sermon title"; BC-15): printed in the bulletin and
 * the pastor's copy, never sent to the AI; 300 characters at most.
 */
export function SermonTitleField({ maxLength }: { maxLength: number }) {
  const { draft, update } = useDraft();
  return (
    <div className="grid gap-2">
      <Label htmlFor={SERMON_TITLE_ID}>Sermon title</Label>
      <Input
        id={SERMON_TITLE_ID}
        value={draft.liturgy.sermon_title}
        placeholder="e.g. Living Water"
        maxLength={maxLength}
        aria-describedby="sermon-title-help"
        onChange={(event) => {
          const next = event.target.value;
          update((d) => setSermonTitle(d, next));
        }}
        className="h-11"
      />
      <p id="sermon-title-help" className="text-sm text-muted-foreground">
        Printed in the bulletin and the pastor&apos;s copy. If blank, both show “[Sermon title]”.
      </p>
    </div>
  );
}
```

**Create `frontend/src/components/builder/liturgy/outline-landmark.tsx`:**

```tsx
"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { OutlineItem } from "@/lib/api/types";
import { effectivePicks } from "@/lib/draft/readings";
import type { DraftV1, Slot } from "@/lib/draft/schema";
import { cn } from "@/lib/utils";

import { SERMON_TITLE_ID } from "./sermon-title-field";

const HYMN_SLOTS: Partial<Record<OutlineItem["value_source"], Slot>> = {
  hymn_opening: "opening",
  hymn_response: "response",
  hymn_closing: "closing",
};

const ROW = "flex min-h-11 w-full min-w-0 flex-wrap items-center gap-x-1 border-l-2 pl-3 text-left text-sm text-muted-foreground";

/**
 * One landmark of the order of worship (S UX "Landmark rows"): a single muted
 * line, not a card, with the value the Word files will print. Hymns show the
 * slot's title and open Hymns; the readings show `effectivePicks` (an
 * automatic one marked "auto") and open Date & readings; the Sermon row shows
 * the title, or "[Sermon title]" when blank, and focuses the sermon field;
 * the Affirmation row shows its fixed text.
 */
export function OutlineLandmark({ item, draft }: { item: OutlineItem; draft: DraftV1 }) {
  const label = <span className="font-medium text-foreground">{item.label}</span>;
  const value = (text: ReactNode) => <span className="min-w-0 wrap-anywhere"> · {text}</span>;
  const slot = HYMN_SLOTS[item.value_source];
  if (slot) {
    const pick = draft.hymns.slots[slot];
    return (
      <Link href="/builder/hymns" className={cn(ROW, "hover:text-foreground")}>
        {label}
        {pick ? value(pick.title) : null}
      </Link>
    );
  }
  if (item.value_source === "reading_ot" || item.value_source === "reading_nt") {
    const picks = effectivePicks(draft);
    const ref = item.value_source === "reading_ot" ? picks.ot : picks.nt;
    const auto = item.value_source === "reading_ot" ? picks.otAuto : picks.ntAuto;
    return (
      <Link href="/builder/readings" className={cn(ROW, "hover:text-foreground")}>
        {label}
        {ref
          ? value(
              <>
                {ref}
                {auto ? <span className="text-xs"> auto</span> : null}
              </>,
            )
          : null}
      </Link>
    );
  }
  if (item.value_source === "sermon_title") {
    const title = draft.liturgy.sermon_title.trim();
    return (
      <button
        type="button"
        className={cn(ROW, "hover:text-foreground")}
        onClick={() => document.getElementById(SERMON_TITLE_ID)?.focus()}
      >
        {label}
        {value(title === "" ? <span className="italic">[Sermon title]</span> : title)}
      </button>
    );
  }
  return (
    <div className={ROW}>
      {label}
      {item.fixed_text ? value(item.fixed_text) : null}
    </div>
  );
}
```

**Create `frontend/src/components/builder/liturgy/section-card.tsx`:**

```tsx
"use client";

import { EllipsisIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgySection } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { clearCard, editCardText, restoreChurchDefault, setCardEnabled, type CardOrigin } from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

/** The status chip for each origin (S "Section card"). */
export const ORIGIN_CHIPS: Record<CardOrigin, string> = {
  empty: "Empty",
  typed: "Your text",
  ai: "AI draft",
  default: "Church default",
  archive: "From saved service",
};

/** The counter shows past this many characters (S "Other card rules"). */
export const COUNTER_FROM = 18_000;

const UNDO_LINES = { replaced: "Replaced with a new AI draft.", cleared: "Cleared." } as const;

export type SectionCardProps = {
  spec: LiturgySection;
  /** "People: Thanks be to God! Amen." under the Assurance card. */
  assuranceResponse: string;
  /** The church's default benediction, for "Use church default". */
  defaultBenediction: string;
  maxLength: number;
};

/**
 * One liturgy section (S "Section card"): a switch named "Include {Label}",
 * the label, a status chip and a ⋯ menu; when on, the textarea (growing up to
 * 60 vh), the section's hint and the Undo line; when off, only "Off — not in
 * the service. Any text is kept." Typing makes the text the user's; Clear
 * text offers Undo; "Use church default" (Benediction) follows the default
 * again. The card's id is `card-{key}`, so Review can link to it.
 *
 * Focus never drops to the page: when the control that had it goes, focus
 * moves to a control that survives or to the card's heading (`tabIndex={-1}`).
 */
export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength }: SectionCardProps) {
  const { draft, update } = useDraft();
  const generation = useLiturgyGeneration();
  const key = spec.key;
  const card = draft.liturgy.cards[key];
  const undo = generation.undo[key];
  const textRef = useRef<HTMLTextAreaElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const undoRef = useRef<HTMLButtonElement>(null);
  /** Set by a handler whose control is about to go: where focus moves after the next render. */
  const focusNext = useRef<(() => HTMLElement | null) | null>(null);
  /** The ⋯ menu's item moved focus itself, so the closing menu leaves it there. */
  const menuMovedFocus = useRef(false);
  useAutosize(textRef, card.text, card.enabled);
  const headingId = `card-${key}-title`;
  const hasText = card.text.trim() !== "";
  const followsDefault = key === "benediction" && card.origin === "default";
  const hint = key === "benediction" ? (followsDefault ? spec.hint : null) : key === "assurance" ? null : spec.hint;
  const showCounter = card.text.length > COUNTER_FROM;
  const describedBy =
    [
      hint ? `card-${key}-hint` : null,
      key === "assurance" ? `card-${key}-response` : null,
      showCounter ? `card-${key}-count` : null,
    ]
      .filter(Boolean)
      .join(" ") || undefined;

  // A control that can take focus, or the card's heading.
  useEffect(() => {
    const target = focusNext.current;
    if (target === null) return;
    focusNext.current = null;
    const element = target();
    const usable = element !== null && element.isConnected && !(element as HTMLButtonElement).disabled;
    (usable ? element : headingRef.current)?.focus();
  });

  function edit(text: string) {
    update((d) => editCardText(d, key, text));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  function toggle(enabled: boolean) {
    update((d) => setCardEnabled(d, key, enabled));
    generation.dismissError(key);
  }

  function clear() {
    const previous = { text: card.text, origin: card.origin };
    update((d) => clearCard(d, key));
    generation.dismissError(key);
    generation.setUndo(key, { kind: "cleared", previous });
    // The ⋯ menu may be disabled now (an empty card); focus goes to "Cleared. Undo".
    menuMovedFocus.current = true;
    focusNext.current = () => undoRef.current;
  }

  function undoLast() {
    generation.applyUndo(key);
    focusNext.current = () => null;
  }

  function followDefault() {
    update((d) => restoreChurchDefault(d, defaultBenediction));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  const menuItems = [
    hasText ? (
      <DropdownMenuItem key="clear" onClick={clear} className="min-h-11 md:min-h-8">
        Clear text
      </DropdownMenuItem>
    ) : null,
    key === "benediction" && card.origin !== "default" ? (
      <DropdownMenuItem key="default" onClick={followDefault} className="min-h-11 md:min-h-8">
        Use church default
      </DropdownMenuItem>
    ) : null,
  ].filter(Boolean);

  return (
    <section
      id={`card-${key}`}
      aria-labelledby={headingId}
      className={cn("grid scroll-mt-24 gap-3 rounded-lg border p-4", !card.enabled && "bg-muted/40")}
    >
      {/* Below sm the chips take their own line under the title, so a long label never pushes the menu out. */}
      <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
        <Switch
          checked={card.enabled}
          onCheckedChange={(checked) => toggle(checked)}
          aria-label={`Include ${spec.label}`}
          className="after:-inset-y-3.5"
        />
        <h3
          ref={headingRef}
          id={headingId}
          tabIndex={-1}
          data-card-heading=""
          className="min-w-0 flex-1 text-base font-medium outline-none"
        >
          {spec.label}
        </h3>
        <div className="flex flex-wrap gap-1 max-sm:order-last max-sm:basis-full max-sm:pl-11 sm:justify-end">
          {spec.pastor_copy_only ? <Badge variant="outline">Pastor&apos;s copy only</Badge> : null}
          <Badge variant="secondary">{ORIGIN_CHIPS[card.origin]}</Badge>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`More actions for ${spec.label}`}
            disabled={menuItems.length === 0}
            className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "size-11 shrink-0 md:size-8")}
          >
            <EllipsisIcon aria-hidden="true" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-auto min-w-44"
            finalFocus={() => {
              const moved = menuMovedFocus.current;
              menuMovedFocus.current = false;
              return !moved;
            }}
          >
            {menuItems}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {card.enabled ? (
        <>
          <Textarea
            ref={textRef}
            aria-labelledby={headingId}
            aria-describedby={describedBy}
            value={card.text}
            placeholder="Type your own text, or tap Generate."
            maxLength={maxLength}
            rows={spec.rows}
            style={{ minHeight: `calc(${spec.rows}lh + 1rem + 2px)` }}
            className="max-h-[60vh] overflow-y-auto"
            onChange={(event) => edit(event.target.value)}
          />
          {showCounter ? (
            <p id={`card-${key}-count`} className="text-right text-xs text-muted-foreground">
              {card.text.length.toLocaleString("en-US")} / {maxLength.toLocaleString("en-US")}
            </p>
          ) : null}
          {key === "assurance" ? (
            <div id={`card-${key}-response`} className="grid gap-0.5 text-sm">
              <p className="font-medium">{assuranceResponse}</p>
              {spec.hint ? <p className="text-muted-foreground">{spec.hint}</p> : null}
            </div>
          ) : null}
          {hint ? (
            <p id={`card-${key}-hint`} className="text-sm text-muted-foreground">
              {hint}
            </p>
          ) : null}
          {undo ? (
            <p className="flex flex-wrap items-center gap-x-1 text-sm" aria-live="polite">
              {UNDO_LINES[undo.kind]}
              <Button ref={undoRef} variant="link" className="h-11 px-1 md:h-auto" onClick={undoLast}>
                Undo
              </Button>
            </p>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Off — not in the service. Any text is kept.</p>
      )}
    </section>
  );
}
```

**Create `frontend/src/components/builder/liturgy/liturgy-step.tsx`:**

```tsx
"use client";

import { Fragment, useEffect } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useChurchProfile } from "@/lib/queries/church";
import { useLiturgyConfig } from "@/lib/queries/liturgy";

import { OutlineLandmark } from "./outline-landmark";
import { SectionCard } from "./section-card";
import { SermonTitleField } from "./sermon-title-field";

/** The step's shape while `GET /liturgy/config` loads (S "Loading, error and empty states"). */
function LiturgySkeleton() {
  return (
    <div role="status" aria-label="Loading the liturgy" className="grid gap-4">
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

/**
 * Step 3, Liturgy (slice 4 spec, "User experience"): the sermon title, then
 * the order of worship from `GET /liturgy/config`'s outline, in the order the
 * Word files print it: a card for each section, muted landmark rows for the
 * hymns, readings, sermon and creed. It reads and writes only the draft (F
 * §4.6); the AI runs live in the builder shell's generation provider, and the
 * step's Undo lines go when it unmounts. On mount it scrolls to the card the
 * address names (`#card-…`, `#custom-…`).
 */
export function LiturgyStep() {
  const configQuery = useLiturgyConfig();
  const config = configQuery.data;
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { draft } = useDraft();
  const { clearUndo } = useLiturgyGeneration();
  const loaded = config !== undefined;

  // "Just replaced" and "Cleared" lines disappear when the step unmounts (S "Section card").
  useEffect(() => () => clearUndo(), [clearUndo]);

  useEffect(() => {
    if (!loaded) return;
    let id = "";
    try {
      id = decodeURIComponent(window.location.hash.slice(1));
    } catch {
      return; // a malformed address ("#card-%E0") scrolls nowhere
    }
    if (id !== "") document.getElementById(id)?.scrollIntoView({ block: "start" });
  }, [loaded]);

  if (config === undefined) {
    // A failed background refetch keeps the config (TanStack Query v5), so only a first load that failed shows this.
    return configQuery.isError ? (
      <ErrorState
        title="Couldn't load the liturgy sections."
        error={configQuery.error}
        onRetry={() => void configQuery.refetch()}
        retrying={configQuery.isFetching}
      />
    ) : (
      <LiturgySkeleton />
    );
  }

  const sections = new Map(config.sections.map((spec) => [spec.key as string, spec]));
  const defaultBenediction = profile?.default_benediction ?? config.default_benediction_fallback;

  return (
    <div className="grid gap-6">
      <h2 className="text-lg font-semibold">Liturgy</h2>
      <SermonTitleField maxLength={config.limits.max_sermon_title} />
      <section aria-labelledby="order-of-worship" className="grid gap-3">
        <h3 id="order-of-worship" className="text-base font-medium">
          Order of worship
        </h3>
        <ol aria-labelledby="order-of-worship" className="grid gap-3">
          {config.outline.map((item) => {
            const spec = sections.get(item.key);
            return (
              <Fragment key={item.key}>
                {item.kind === "section" && spec ? (
                  <li>
                    <SectionCard
                      spec={spec}
                      assuranceResponse={config.assurance_response}
                      defaultBenediction={defaultBenediction}
                      maxLength={config.limits.max_section_text}
                    />
                  </li>
                ) : item.kind === "landmark" ? (
                  <li>
                    <OutlineLandmark item={item} draft={draft} />
                  </li>
                ) : null}
              </Fragment>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  1 passed (1)`, `      Tests  11 passed (11)`; the suite ` Test Files  75 passed (75)`, `      Tests  490 passed (490)`; `typecheck 0` and `lint 0`; `?? frontend/src/components/builder/liturgy/`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/liturgy-step.tsx frontend/src/components/builder/liturgy/section-card.tsx frontend/src/components/builder/liturgy/outline-landmark.tsx frontend/src/components/builder/liturgy/sermon-title-field.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -m "Liturgy: the order of worship with editable section cards, the sermon title and the landmarks (S Section card, Layout; BC-1, BC-3, BC-9)" -m "LiturgyStep lays out GET /liturgy/config's outline in the Word files'
order: a card per section (switch, chip, menu with Clear text and Use
church default, a textarea growing to 60 vh with the hints and a counter
past 18,000, Off when switched off with the text kept) and muted rows for
the hymns, readings, sermon title and creed. Skeleton while loading;
Couldn't load the liturgy sections. with Retry. The footer already hides
while typing (owner answer 3); a test pins it here.
Frontend 479 -> 490 tests in 74 -> 75 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 5 files changed.

### Task 9: Generate, Regenerate and the AI bar (S UX "AI bar", "Generate and Regenerate", "Per-card error messages", Testing dom 4-12; BC-2, BC-5, BC-6, BC-13, BC-20, BC-21; clarifications 8, 9, 15, 22, 23, 29, 30, 32, 33, 34, 36)

The cards get their AI (S "Section card" states) and the step its AI bar. An empty card has **Generate**; a card with text has **Regenerate**, which asks "Replace your text?" ("Keep my text" / "Replace text") when the text is the user's or a saved service's and runs at once for an AI draft or a Benediction following the default, and is disabled with "AI isn't set up" when the config says AI is off. While queued the card shows a disabled "Waiting…" and while writing "Writing…" (then "Still working — this can take up to a minute." after 8 s), each with a Cancel button named "Cancel {Label}"; the ⋯ menu is disabled, and the text is read-only while writing. Typing in a queued card, or switching a running card off, cancels its run. An error shows in an alert under the text; a retryable one carries **Try again** (disabled until a 429's wait has passed), which stands in for the card's button (clarification 22), and the 404 carries "Go to Hymns" (clarification 9). The AI bar has **Generate empty sections (n)** (disabled at 0, with S's other caption), **Cancel** and "Writing k of n…" during a bulk run (clarification 23), the no-AI banner, the "general text" notice with its "Date & readings" link, and the all-off notice. The AI itself is T6's provider; this task wires the screen to it and tests S's dom cases 4-12 through it, including the stale rule (clarification 29), navigation to another step, the 429 and a 401 or a lost church. From the plan review: the Undo line is hidden while the card runs (clarification 33); "New service" during a bulk run ends it with one toast and clears the errors and Undo lines (clarification 32); focus moves to the run's Cancel after Replace text and Try again, back to Regenerate after Cancel and Keep my text (clarification 34); the 429's wait counts from `retryAt`, survives leaving the step, and holds "Generate empty sections" too; a bulk run's errors are announced politely (an `aria-live` line) rather than as alerts, and the error is part of the textarea's description (clarification 36).

**Files:**
- Create: `frontend/src/components/builder/liturgy/ai-bar.tsx`, `frontend/src/components/builder/liturgy/use-still-working.ts`
- Modify: `frontend/src/components/builder/liturgy/section-card.tsx` (the AI states, the confirm dialog, the error alert), `frontend/src/components/builder/liturgy/liturgy-step.tsx` (the AI bar, `aiAvailable`)
- Test: `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` (+16)

**Interfaces:**
- Consumes: `useLiturgyGeneration()` (T6); `sectionsNeedingAi`, `needsRegenerateConfirm` (T2); `type CardErrorState` (T6); `liturgyCounts` (T2); `ConfirmDialog` (`cancelLabel`, `finalFocus`, 2c), `PendingButton`, `Alert`; `authEvents` (1, in the tests).
- Produces: `AiBar({aiAvailable})` (a region named "Write with AI"); `SectionCard` gains `aiAvailable`; `useRetryWait(retryAt)` (exported from `section-card.tsx`, used by `AiBar`); `STILL_WORKING_MS = 8_000`, `STILL_WORKING`, `useStillWorking(active)`. Later users: T10, T11.

Counts after this task: frontend **506 passed in 75 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "aiAvailable" frontend/src/components/builder/liturgy/section-card.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  75 passed (75)`, `      Tests  490 passed (490)`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import { editScriptureLines, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { editCardText } from "@/lib/liturgy/cards";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
```

**with:**

```tsx
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { Toaster } from "@/components/ui/sonner";
import type { GenerateLiturgyBody } from "@/lib/api/types";
import { editOccasion, editScriptureLines, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { editCardText } from "@/lib/liturgy/cards";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type FakeResponse, type RecordedRequest } from "@/test/fake-api";
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
  DRAFT_NOW,
  gg2013,
```

**with:**

```tsx
  DRAFT_NOW,
  generateRoute,
  gg2013,
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
  me,
  testDraft,
```

**with:**

```tsx
  me,
  sectionFailure,
  sectionResult,
  testDraft,
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
import { LiturgyStep } from "./liturgy-step";

```

**with:**

```tsx
import { LiturgyStep } from "./liturgy-step";
import { STILL_WORKING } from "./use-still-working";

```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
  vi.setSystemTime(DRAFT_NOW);
});
```

**with:**

```tsx
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
});
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
    expect(within(card("Call to Worship")).getByText("Empty")).toBeInTheDocument();
  });
});

```

**with:**

```tsx
    expect(within(card("Call to Worship")).getByText("Empty")).toBeInTheDocument();
  });
});

// --- slice 4b T9: Generate, Regenerate and the AI bar ---------------------------------

/** A `POST /liturgy/generate` handler that answers each section only when the test releases it. */
function heldGenerate() {
  const waiting = new Map<string, (answer: FakeResponse | undefined) => void>();
  const sent: string[] = [];
  let open = 0;
  let most = 0;
  const handler = async (req: RecordedRequest) => {
    const section = (req.body as GenerateLiturgyBody).sections[0];
    sent.push(section);
    open += 1;
    most = Math.max(most, open);
    const answer = await new Promise<FakeResponse | undefined>((resolve) => waiting.set(section, resolve));
    open -= 1;
    return answer ?? { results: [sectionResult(section, `New ${section}`)] };
  };
  return {
    handler,
    sent,
    most: () => most,
    /** Answers `section` (by default "New {section}"), once its request has arrived. */
    release: async (section: SectionKey, answer?: FakeResponse) => {
      await waitFor(() => expect(waiting.has(section)).toBe(true));
      waiting.get(section)?.(answer);
      waiting.delete(section);
    },
  };
}

const generateCalls = (requests: RecordedRequest[]) => requests.filter((r) => r.path === "/liturgy/generate");

/**
 * A card's error, whether it came as an alert (the card's own run) or
 * quietly (a bulk run announces its errors politely, not as one alert each).
 */
function errorIn(label: string): HTMLElement | null {
  return card(label).querySelector<HTMLElement>('[data-slot="alert"]');
}

describe("Generate and Regenerate (S Generate and Regenerate, AI bar)", () => {
  it("Generate sends one section as the church, no overrides, and writes an AI draft with no toast", async () => {
    const { user, api } = renderStep();
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    api.set("POST /liturgy/generate", generateRoute());
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    expect(await within(cw).findByText("AI draft")).toBeInTheDocument();
    expect(within(cw).getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Call to Worship written by the AI.");
    const [call] = generateCalls(api.requests);
    expect(call.headers["X-Church-Id"]).toBe(church().id);
    expect(call.body).toEqual({ occasion: "", scriptures: [], hymns: { opening: null, response: null, closing: null }, sections: ["call_to_worship"] });
    expect(generateCalls(api.requests)).toHaveLength(1);
    expect(within(cw).queryByText(/Replaced/)).toBeNull(); // nothing was replaced
    expect(screen.queryByText(/^Wrote/)).toBeNull();
    await waitFor(() => expect(stored().liturgy.cards.call_to_worship.origin).toBe("ai"));
  });

  it("Generate empty sections writes only switched-on empty cards, 3 at a time, and ends with one toast", async () => {
    const held = heldGenerate();
    const d = withCard("call_to_worship", { text: "Come, let us worship.", origin: "typed" }, withCard("assurance", { enabled: false }));
    const { user } = renderStep(d, { "POST /liturgy/generate": held.handler });
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    expect(within(bar).getByText("Only switched-on sections with no text are written. Text you typed is never changed.")).toBeInTheDocument();
    await user.click(within(bar).getByRole("button", { name: "Generate empty sections (4)" }));
    expect(await within(bar).findByText("Writing 1 of 4…")).toBeInTheDocument();
    expect(within(bar).getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    await waitFor(() => expect(held.sent).toHaveLength(3));
    expect(within(card("Offertory Prayer")).getByRole("button", { name: "Waiting…" })).toBeDisabled();
    await held.release("opening_prayer");
    expect(await within(bar).findByText("Writing 2 of 4…")).toBeInTheDocument();
    for (const key of ["prayer_of_confession", "prayer_for_illumination", "offertory_prayer"] as const) await held.release(key);
    expect(await screen.findByText("Wrote 4 sections.")).toBeInTheDocument();
    expect(held.sent).toEqual(["opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"]);
    expect(held.most()).toBe(3);
    // Typed text, a card that is off and the Benediction's default are never sent or changed.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Come, let us worship.");
    expect(screen.getByRole("textbox", { name: "Benediction" })).toHaveValue("Halverson");
    expect(within(bar).getByRole("button", { name: "Generate empty sections (0)" })).toBeDisabled();
    expect(within(bar).getByText("Every switched-on section has text. Use Regenerate on a card for a new AI draft.")).toBeInTheDocument();
  });

  it("Regenerate on the user's text asks first; Keep my text sends nothing, Replace text replaces it with Undo", async () => {
    const { user, api } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }), {
      "POST /liturgy/generate": generateRoute(),
    });
    const op = await screen.findByRole("region", { name: "Opening Prayer" });
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Replace your text?" });
    expect(within(dialog).getByText("Regenerate replaces the text in Opening Prayer with a new AI draft. You can undo right after.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Keep my text" }));
    expect(generateCalls(api.requests)).toHaveLength(0);
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    const text = within(op).getByRole("textbox", { name: "Opening Prayer" });
    await waitFor(() => expect(text).toHaveValue("Opening Prayer written by the AI."));
    expect(within(op).getByText("Replaced with a new AI draft.")).toBeInTheDocument();
    await user.click(within(op).getByRole("button", { name: "Undo" }));
    expect(text).toHaveValue("Gracious God");
    expect(within(op).getByText("Your text")).toBeInTheDocument();
    // An AI draft is regenerated without asking.
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    await waitFor(() => expect(text).toHaveValue("Opening Prayer written by the AI."));
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await waitFor(() => expect(generateCalls(api.requests)).toHaveLength(3));
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  // Heavy: six cards answer in one run, then a retry; near Vitest's 5 s default on a busy machine.
  it("shows each error on its card only, never in the draft, with Try again where it can help", { timeout: 10_000 }, async () => {
    let timeoutOnce = true;
    const answers: Partial<Record<SectionKey, () => FakeResponse | ReturnType<typeof sectionResult>>> = {
      call_to_worship: () =>
        timeoutOnce
          ? ((timeoutOnce = false), sectionFailure("call_to_worship", "ai_timeout", "The AI took too long to answer. Try again."))
          : sectionResult("call_to_worship", "Leader: Come!"),
      opening_prayer: () =>
        sectionFailure(
          "opening_prayer",
          "prompt_invalid",
          "The Opening Prayer prompt in Settings has a problem: Placeholders need a name, such as {occasion}. An admin can fix it under Settings → Liturgy prompts.",
        ),
      prayer_of_confession: () =>
        fakeError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."),
      assurance: () => fakeError(500, "internal_error", "Something went wrong."),
      prayer_for_illumination: () => sectionFailure("prayer_for_illumination", "ai_not_configured", "AI not configured. Type this section yourself."),
    };
    const { user } = renderStep(testDraft(), {
      "POST /liturgy/generate": generateRoute((section) => answers[section]?.() ?? sectionResult(section, `New ${section}`)),
    });
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    await user.click(within(bar).getByRole("button", { name: "Generate empty sections (6)" }));
    expect(await screen.findByText("Wrote 1 of 6 sections. The rest show what went wrong.")).toBeInTheDocument();
    const alertIn = (label: string) => errorIn(label) as HTMLElement;
    expect(alertIn("Call to Worship")).toHaveTextContent("The AI took too long to answer. Try again.");
    // A bulk run's errors are announced politely, not as six alerts; each is linked to its card's text.
    expect(screen.queryByRole("alert")).toBeNull();
    expect(within(card("Call to Worship")).getByText("The AI took too long to answer. Try again.", { selector: "[aria-live=polite]" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveAccessibleDescription(/The AI took too long to answer\. Try again\./);
    expect(within(alertIn("Opening Prayer")).queryByRole("button", { name: "Try again" })).toBeNull();
    expect(within(alertIn("Prayer of Confession")).getByRole("link", { name: "Go to Hymns" })).toHaveAttribute("href", "/builder/hymns");
    expect(within(alertIn("Prayer of Confession")).queryByRole("button", { name: "Try again" })).toBeNull();
    expect(alertIn("Assurance of Pardon")).toHaveTextContent("Something went wrong. (Ref: 4f9a2c1e)");
    expect(alertIn("Prayer for Illumination")).toHaveTextContent("AI not configured. Type this section yourself.");
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue(""); // the text is unchanged
    await waitFor(() => expect(stored().liturgy.cards.offertory_prayer.text).toBe("New offertory_prayer"));
    expect(window.localStorage.getItem(KEY)).not.toMatch(/took too long|has a problem|no longer in your hymnal|went wrong|not configured/);
    await user.click(within(alertIn("Call to Worship")).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("Leader: Come!"));
    expect(errorIn("Call to Worship")).toBeNull();
  });

  it("without AI sends nothing: empty cards say so, Regenerate is off, and the banner explains", async () => {
    const d = withCard("opening_prayer", { text: "Gracious God", origin: "typed" }, withCard("assurance", { enabled: false }));
    const { user, api } = renderStep(d, { "GET /liturgy/config": liturgyConfig({ ai_available: false }) });
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    expect(within(bar).getByText("AI writing isn't set up for this app. Type each section yourself — everything else works as usual.")).toBeInTheDocument();
    await user.click(within(card("Call to Worship")).getByRole("button", { name: "Generate" }));
    expect(within(card("Call to Worship")).getByRole("alert")).toHaveTextContent("AI not configured. Type this section yourself.");
    await user.click(within(bar).getByRole("button", { name: "Generate empty sections (4)" }));
    const marked = ["Call to Worship", "Prayer of Confession", "Prayer for Illumination", "Offertory Prayer"];
    for (const label of marked) expect(errorIn(label)).toHaveTextContent("AI not configured. Type this section yourself.");
    for (const label of ["Opening Prayer", "Assurance of Pardon", "Prayers of the People", "Benediction"]) {
      expect(errorIn(label)).toBeNull();
    }
    const op = card("Opening Prayer");
    expect(within(op).getByRole("button", { name: "Regenerate" })).toBeDisabled();
    expect(within(op).getByText("AI isn't set up")).toBeInTheDocument();
    expect(within(op).getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God");
    expect(within(op).getByText("Your text")).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(generateCalls(api.requests)).toHaveLength(0);
    expect(screen.queryByText(/^Wrote/)).toBeNull();
  });

  // Heavy: three runs, one of them a bulk run of six with five answers; near Vitest's 5 s default on a busy machine.
  it("Cancel, switching a running card off, and typing in a queued card all stop it silently", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    expect(await within(cw).findByRole("button", { name: "Writing…" })).toBeDisabled();
    expect(within(cw).getByRole("textbox", { name: "Call to Worship" })).toHaveAttribute("readonly");
    expect(within(cw).getByRole("button", { name: "More actions for Call to Worship" })).toBeDisabled();
    await user.click(within(cw).getByRole("button", { name: "Cancel Call to Worship" }));
    expect(within(cw).getByRole("button", { name: "Generate" })).toBeEnabled();
    await held.release("call_to_worship");

    const op = card("Opening Prayer");
    await user.click(within(op).getByRole("button", { name: "Generate" }));
    await within(op).findByRole("button", { name: "Writing…" });
    await user.click(within(op).getByRole("switch", { name: "Include Opening Prayer" }));
    await user.click(within(op).getByRole("switch", { name: "Include Opening Prayer" }));
    expect(within(op).getByRole("button", { name: "Generate" })).toBeEnabled(); // not restarted
    await held.release("opening_prayer");

    await user.click(screen.getByRole("button", { name: "Generate empty sections (6)" }));
    const assurance = card("Assurance of Pardon");
    expect(await within(assurance).findByRole("button", { name: "Waiting…" })).toBeDisabled();
    await user.type(within(assurance).getByRole("textbox", { name: "Assurance of Pardon" }), "You are forgiven.");
    for (const key of ["call_to_worship", "opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"] as const) {
      await held.release(key);
    }
    expect(await screen.findByText("Wrote 5 sections.")).toBeInTheDocument();
    expect(held.sent).not.toContain("assurance");
    expect(within(assurance).getByRole("textbox", { name: "Assurance of Pardon" })).toHaveValue("You are forgiven.");
    // The cancelled runs' answers were never applied, and no card shows an error.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("New call_to_worship");
    expect(screen.queryByRole("alert")).toBeNull();
  });

  // Heavy: three runs, a New service, a 400 ms draft write and a profile change; near Vitest's 5 s default.
  it("drops a run for a replaced service or a result for an edit from another tab, and applies one to a card following the default", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user, queryClient } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    // New service while a run goes: the draft is replaced (a new created_at), and the run stops silently.
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await within(cw).findByRole("button", { name: "Writing…" });
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000)); // the new draft's created_at differs
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(await within(card("Call to Worship")).findByRole("button", { name: "Generate" })).toBeEnabled();
    await held.release("call_to_worship");
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("");

    // An edit from another tab while it writes.
    await user.click(within(card("Opening Prayer")).getByRole("button", { name: "Generate" }));
    await within(card("Opening Prayer")).findByRole("button", { name: "Writing…" });
    // The other tab edits the new service (written 400 ms after New service).
    await waitFor(() => expect(stored().created_at).toBe(new Date(DRAFT_NOW.getTime() + 60_000).toISOString()));
    const theirs = withCard("opening_prayer", { text: "From the other tab", origin: "typed" }, stored());
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", { key: KEY, newValue: JSON.stringify({ ...theirs, updated_at: "2026-09-29T17:00:00.000Z" }) }),
      );
    });
    await held.release("opening_prayer");
    expect(await screen.findByText("Kept your edits — the new AI draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("From the other tab");
    // The New service run was dropped without a toast, and its answer never landed.
    expect(screen.queryByText(/The service changed/)).toBeNull();
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveValue("");

    // Regenerate a Benediction following the default; the default changes mid-run.
    const bn = card("Benediction");
    await user.click(within(bn).getByRole("button", { name: "Regenerate" }));
    await within(bn).findByRole("button", { name: "Writing…" });
    act(() => queryClient.setQueryData(keys.churchProfile(church().id), churchProfile({ default_benediction: "Go in peace." })));
    await waitFor(() => expect(within(bn).getByRole("textbox", { name: "Benediction" })).toHaveValue("Go in peace."));
    await held.release("benediction");
    await waitFor(() => expect(within(bn).getByRole("textbox", { name: "Benediction" })).toHaveValue("New benediction"));
    expect(within(bn).getByText("AI draft")).toBeInTheDocument();
    await user.click(within(bn).getByRole("button", { name: "Undo" }));
    expect(within(bn).getByRole("textbox", { name: "Benediction" })).toHaveValue("Go in peace.");
    expect(within(bn).getByText("Church default")).toBeInTheDocument();
  });

  // Heavy: a bulk run of six, an error, New service and one more run; near Vitest's 5 s default on a busy machine.
  it("New service during a bulk run drops every run with one toast and clears the cards' errors and Undo", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user } = renderStep(withCard("call_to_worship", { text: "Come.", origin: "typed" }), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await user.click(within(cw).getByRole("button", { name: "More actions for Call to Worship" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(cw).getByText("Cleared.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate empty sections (6)" }));
    await waitFor(() => expect(held.sent).toHaveLength(3));
    // While the card runs its Undo is hidden, so Undo cannot change the text the run will replace.
    expect(within(cw).queryByText("Cleared.")).toBeNull();
    await held.release("call_to_worship", fakeError(500, "internal_error", "Something went wrong."));
    await waitFor(() => expect(errorIn("Call to Worship")).toHaveTextContent("Something went wrong. (Ref: 4f9a2c1e)"));
    expect(within(cw).getByText("Cleared.")).toBeInTheDocument(); // back once the run has ended
    await waitFor(() => expect(held.sent).toHaveLength(4));
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000)); // the new draft's created_at differs
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(await screen.findByText("The service changed, so the AI drafts were discarded.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate empty sections (6)" })).toBeEnabled();
    expect(errorIn("Call to Worship")).toBeNull();
    expect(within(card("Call to Worship")).queryByText("Cleared.")).toBeNull();
    // The answers still on their way land nowhere; a new run works as usual.
    await held.release("opening_prayer");
    await held.release("prayer_of_confession");
    await user.click(within(card("Offertory Prayer")).getByRole("button", { name: "Generate" }));
    await held.release("offertory_prayer");
    await waitFor(() => expect(screen.getByRole("textbox", { name: "Offertory Prayer" })).toHaveValue("New offertory_prayer"));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("");
    expect(screen.queryByText(/^Wrote/)).toBeNull();
    expect(screen.queryByText(/The service changed, so the AI draft for/)).toBeNull();
    expect(held.sent).toEqual(["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance", "offertory_prayer"]);
  });

  it("keeps focus on the card when its control goes: Replace text, Cancel, Keep my text, Try again, Clear and Undo", async () => {
    const held = heldGenerate();
    const { user } = renderStep(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }), { "POST /liturgy/generate": held.handler });
    const op = await screen.findByRole("region", { name: "Opening Prayer" });
    // Replace text: Regenerate is gone while the card runs, so the card's Cancel takes focus.
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Replace text" }));
    await waitFor(() => expect(within(op).getByRole("button", { name: "Cancel Opening Prayer" })).toHaveFocus());
    await user.click(within(op).getByRole("button", { name: "Cancel Opening Prayer" }));
    expect(within(op).getByRole("button", { name: "Regenerate" })).toHaveFocus();
    await user.click(within(op).getByRole("button", { name: "Regenerate" }));
    await user.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Keep my text" }));
    await waitFor(() => expect(within(op).getByRole("button", { name: "Regenerate" })).toHaveFocus());
    // Try again: its alert goes, so the card's Cancel.
    const cw = card("Call to Worship");
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await held.release("call_to_worship", {
      status: 200,
      body: { results: [sectionFailure("call_to_worship", "ai_timeout", "The AI took too long to answer. Try again.")] },
    });
    await user.click(within(await within(cw).findByRole("alert")).getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(within(cw).getByRole("button", { name: "Cancel Call to Worship" })).toHaveFocus());
    // Clear: the ⋯ menu is off on an empty card, so "Cleared. Undo"; Undo: the card's heading.
    await user.click(within(op).getByRole("button", { name: "More actions for Opening Prayer" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    await waitFor(() => expect(within(op).getByRole("button", { name: "Undo" })).toHaveFocus());
    await user.click(within(op).getByRole("button", { name: "Undo" }));
    expect(within(op).getByRole("heading", { name: "Opening Prayer" })).toHaveFocus();
  });

  it("keeps a 429's wait when the member leaves the step and comes back, and the AI bar waits too", async () => {
    const view = renderStep(testDraft(), {
      "POST /liturgy/generate": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", {
        details: { retry_after_seconds: 30 },
      }),
    });
    await view.user.click(within(await screen.findByRole("region", { name: "Offertory Prayer" })).getByRole("button", { name: "Generate" }));
    expect(within(await within(card("Offertory Prayer")).findByRole("alert")).getByRole("button", { name: "Try again" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Generate empty sections (6)" })).toBeDisabled();
    const page = (step: ReactNode) => (
      <>
        <BuilderLayout>{step}</BuilderLayout>
        <Toaster />
      </>
    );
    view.rerender(page(<ReviewStepPage />));
    expect(screen.queryByRole("region", { name: "Offertory Prayer" })).toBeNull();
    view.rerender(page(<LiturgyStep />));
    // Back at once: the wait goes on (it is not restarted, nor over).
    expect(within(await within(await screen.findByRole("region", { name: "Offertory Prayer" })).findByRole("alert")).getByRole("button", { name: "Try again" })).toBeDisabled();
    view.rerender(page(<ReviewStepPage />));
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 30_000)); // the 30 s pass while the member is away
    view.rerender(page(<LiturgyStep />));
    const offertory = await screen.findByRole("region", { name: "Offertory Prayer" });
    expect(within(within(offertory).getByRole("alert")).getByRole("button", { name: "Try again" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Generate empty sections (6)" })).toBeEnabled();
  });

  it("keeps writing while the member is on another step, and the result is there on return", async () => {
    const held = heldGenerate();
    const view = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    await view.user.click(within(cw).getByRole("button", { name: "Generate" }));
    await within(cw).findByRole("button", { name: "Writing…" });
    const page = (step: ReactNode) => (
      <>
        <BuilderLayout>{step}</BuilderLayout>
        <Toaster />
      </>
    );
    view.rerender(page(<ReviewStepPage />));
    expect(screen.queryByRole("region", { name: "Call to Worship" })).toBeNull();
    await held.release("call_to_worship");
    await waitFor(() => expect(stored().liturgy.cards.call_to_worship.text).toBe("New call_to_worship"));
    view.rerender(page(<LiturgyStep />));
    expect(await screen.findByRole("textbox", { name: "Call to Worship" })).toHaveValue("New call_to_worship");
  });

  // Heavy: a bulk run of six and four cards' alerts; near Vitest's 5 s default on a busy machine.
  it("stops the queue on a 429: that card and every waiting one show the wait", { timeout: 10_000 }, async () => {
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    await user.click(await screen.findByRole("button", { name: "Generate empty sections (6)" }));
    await waitFor(() => expect(held.sent).toHaveLength(3));
    await held.release(
      "call_to_worship",
      fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", { details: { retry_after_seconds: 30 } }),
    );
    for (const label of ["Call to Worship", "Assurance of Pardon", "Prayer for Illumination", "Offertory Prayer"]) {
      await waitFor(() => expect(errorIn(label)).toHaveTextContent("Too many requests — try again in 30 s."));
      expect(within(errorIn(label) as HTMLElement).getByRole("button", { name: "Try again" })).toBeDisabled();
    }
    await held.release("opening_prayer");
    await held.release("prayer_of_confession");
    expect(await screen.findByText("Wrote 2 of 6 sections. The rest show what went wrong.")).toBeInTheDocument();
    expect(held.sent).toEqual(["call_to_worship", "opening_prayer", "prayer_of_confession"]);
    // The AI bar waits as well.
    expect(screen.getByRole("button", { name: "Generate empty sections (4)" })).toBeDisabled();
  });

  it("enables Try again once a 429's wait has passed", async () => {
    const { user } = renderStep(testDraft(), {
      "POST /liturgy/generate": fakeError(429, "rate_limited", "Too many requests. Try again in 1 seconds.", {
        details: { retry_after_seconds: 1 },
      }),
    });
    await user.click(within(await screen.findByRole("region", { name: "Offertory Prayer" })).getByRole("button", { name: "Generate" }));
    const retry = within(await within(card("Offertory Prayer")).findByRole("alert")).getByRole("button", { name: "Try again" });
    expect(retry).toBeDisabled();
    await waitFor(() => expect(retry).toBeEnabled(), { timeout: 2_000 });
  });

  it("a 401 or a lost church goes to the app's handling and shows nothing on the card", async () => {
    const events: string[] = [];
    const off = [
      authEvents.onSignOutRequired(() => events.push("signOutRequired")),
      authEvents.onChurchAccessLost((id) => events.push(`lost:${id}`)),
    ];
    const { user, api } = renderStep();
    const cw = await screen.findByRole("region", { name: "Call to Worship" });
    api.set("POST /liturgy/generate", fakeError(401, "unauthenticated", "Please sign in."));
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(events).toEqual(["signOutRequired"]));
    api.set("POST /liturgy/generate", fakeError(403, "forbidden", "No access.", { details: { reason: "no_church_access" } }));
    await user.click(within(cw).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(events).toEqual(["signOutRequired", `lost:${church().id}`]));
    expect(within(cw).queryByRole("alert")).toBeNull();
    for (const stop of off) stop();
  });

  it("says Still working after 8 s on the card and in the bar", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const held = heldGenerate();
    const { user } = renderStep(testDraft(), { "POST /liturgy/generate": held.handler });
    await user.click(await screen.findByRole("button", { name: "Generate empty sections (6)" }));
    await within(card("Call to Worship")).findByRole("button", { name: "Writing…" });
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(within(card("Call to Worship")).getByText(STILL_WORKING)).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText(`Writing 1 of 6… ${STILL_WORKING}`)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("button", { name: "Generate empty sections (6)" })).toBeEnabled();
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
  });

  it("notes when AI text will be general, and when every section is off", async () => {
    const view = renderStep();
    const { user } = view;
    const bar = await screen.findByRole("region", { name: "Write with AI" });
    expect(within(bar).getByText(/No occasion or readings yet, so AI text will be general\./)).toBeInTheDocument();
    expect(within(bar).getByRole("link", { name: "Date & readings" })).toHaveAttribute("href", "/builder/readings");
    expect(within(bar).queryByText(/All liturgy sections are switched off/)).toBeNull();
    for (const label of ["Call to Worship", "Opening Prayer", "Prayer of Confession", "Assurance of Pardon", "Prayer for Illumination", "Offertory Prayer", "Benediction"]) {
      await user.click(within(card(label)).getByRole("switch", { name: `Include ${label}` }));
    }
    expect(
      within(bar).getByText(
        "All liturgy sections are switched off. The Word files will list only hymns, readings, the sermon title and any custom elements.",
      ),
    ).toBeInTheDocument();
    view.unmount();
    renderStep(editOccasion(testDraft(), "Harvest Home"));
    expect(await screen.findByRole("button", { name: "Generate empty sections (6)" })).toBeInTheDocument();
    expect(screen.queryByText(/No occasion or readings yet/)).toBeNull();
  });
});

```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "^ FAIL|Error: Failed|Tests ")
```

**Expected:**

```
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx [ src/components/builder/liturgy/liturgy-step.test.tsx ]
Error: Failed to resolve import "./use-still-working" from "src/components/builder/liturgy/liturgy-step.test.tsx". Does the file exist?
      Tests  no tests
```

- [ ] **Step 4 (agent): Write the AI bar and the cards' AI states**

**Create `frontend/src/components/builder/liturgy/use-still-working.ts`:**

```ts
"use client";

import { useEffect, useState } from "react";

/** After this long a running AI request adds "Still working — this can take up to a minute." (F §1.8, §4.8). */
export const STILL_WORKING_MS = 8_000;

export const STILL_WORKING = "Still working — this can take up to a minute.";

/** True once `active` has been true for `STILL_WORKING_MS`; false again as soon as it is not. */
export function useStillWorking(active: boolean): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => setSlow(true), STILL_WORKING_MS);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [active]);
  return active && slow;
}
```

**Create `frontend/src/components/builder/liturgy/ai-bar.tsx`:**

```tsx
"use client";

import { InfoIcon } from "lucide-react";
import Link from "next/link";

import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import { sectionsNeedingAi } from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { liturgyCounts } from "@/lib/liturgy/summary";
import { cleanLines } from "@/lib/scripture-refs";

import { useRetryWait } from "./section-card";
import { STILL_WORKING, useStillWorking } from "./use-still-working";

/**
 * The AI bar (S UX "AI bar"): "Generate empty sections (n)" for the
 * switched-on cards with no text that are not already running, Cancel and
 * "Writing k of n…" while a bulk run goes, the no-AI banner, and the two
 * notices (no context; every section off). With AI off the button still
 * marks the empty cards, and sends nothing (S step 0). After a 429 the
 * button waits as the cards' Try again does.
 */
export function AiBar({ aiAvailable }: { aiAvailable: boolean }) {
  const { draft } = useDraft();
  const generation = useLiturgyGeneration();
  const targets = sectionsNeedingAi(draft).filter((key) => generation.runs[key] === undefined);
  const bulk = generation.bulk;
  const still = useStillWorking(bulk !== null);
  const retryAt = Math.max(0, ...Object.values(generation.errors).map((e) => e?.retryAt ?? 0));
  const retryWaiting = useRetryWait(retryAt === 0 ? undefined : retryAt);
  const r = draft.readings;
  const noContext = r.occasion.trim() === "" && cleanLines(r.scriptures).length === 0;
  const allOff = liturgyCounts(draft).enabled === 0;

  return (
    <section aria-label="Write with AI" className="grid gap-3 rounded-lg border bg-muted/30 p-4">
      {aiAvailable ? null : (
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>AI writing isn&apos;t set up for this app. Type each section yourself — everything else works as usual.</AlertTitle>
        </Alert>
      )}
      <div>
        {bulk ? (
          <Button variant="outline" size="touch" onClick={() => generation.cancelBulk()}>
            Cancel
          </Button>
        ) : (
          <Button
            size="touch"
            disabled={targets.length === 0 || retryWaiting}
            onClick={() => generation.generate(targets, { aiAvailable, bulk: true })}
          >
            Generate empty sections ({targets.length})
          </Button>
        )}
      </div>
      {bulk ? (
        <p className="text-sm" aria-live="polite">
          Writing {Math.min(bulk.done + 1, bulk.total)} of {bulk.total}…{still ? ` ${STILL_WORKING}` : null}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          {targets.length === 0
            ? "Every switched-on section has text. Use Regenerate on a card for a new AI draft."
            : "Only switched-on sections with no text are written. Text you typed is never changed."}
        </p>
      )}
      {noContext ? (
        <p className="text-sm text-muted-foreground">
          No occasion or readings yet, so AI text will be general. Add them in{" "}
          <Link href="/builder/readings" className="font-medium underline underline-offset-4">
            Date &amp; readings
          </Link>
          .
        </p>
      ) : null}
      {allOff ? (
        <p className="text-sm text-muted-foreground">
          All liturgy sections are switched off. The Word files will list only hymns, readings, the sermon title and any
          custom elements.
        </p>
      ) : null}
    </section>
  );
}
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
import { EllipsisIcon } from "lucide-react";
import { useEffect, useRef } from "react";

```

**with:**

```tsx
import { CircleAlertIcon, EllipsisIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
import { clearCard, editCardText, restoreChurchDefault, setCardEnabled, type CardOrigin } from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";
```

**with:**

```tsx
import {
  clearCard,
  editCardText,
  needsRegenerateConfirm,
  restoreChurchDefault,
  setCardEnabled,
  type CardOrigin,
} from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

import { STILL_WORKING, useStillWorking } from "./use-still-working";
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
  maxLength: number;
};

```

**with:**

```tsx
  maxLength: number;
  /** `GET /liturgy/config`'s `ai_available`: when false nothing is sent, and Regenerate is disabled. */
  aiAvailable: boolean;
};

/**
 * A 429's wait (S "Per-card error messages"): true until `retryAt` (ms since
 * the epoch) passes. It counts from that moment, not from when the card
 * mounted, so leaving the step and coming back does not restart it.
 */
export function useRetryWait(retryAt: number | undefined): boolean {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (retryAt === undefined) return;
    const timer = setTimeout(() => setNow(Math.max(Date.now(), retryAt)), Math.max(retryAt - Date.now(), 0));
    return () => clearTimeout(timer);
  }, [retryAt]);
  return retryAt !== undefined && now < retryAt;
}

```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
 * again. The card's id is `card-{key}`, so Review can link to it.
 *
 * Focus never drops to the page: when the control that had it goes, focus
 * moves to a control that survives or to the card's heading (`tabIndex={-1}`).
 */
export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength }: SectionCardProps) {
```

**with:**

```tsx
 * again. The card's id is `card-{key}`, so Review can link to it.
 *
 * The AI (S "Generate and Regenerate"): an empty card has Generate; a card
 * with text has Regenerate, which asks "Replace your text?" first when the
 * text is the user's or a saved service's, and is disabled when AI is not set
 * up. While queued ("Waiting…") or writing ("Writing…", then "Still
 * working…" after 8 s) the card has a Cancel button and its ⋯ menu is off;
 * while writing the text is read-only. Typing in a queued card, or switching
 * a running card off, cancels its run. An error shows in an alert under the
 * text with Try again when trying again can help; the text never changes.
 * While the card runs its Undo line is hidden, so Undo cannot change the text
 * a queued run is about to replace.
 *
 * Focus never drops to the page: when the control that had it goes (Cancel,
 * Try again, Undo, Clear, the confirm dialog's Replace text), focus moves to
 * a control that survives or to the card's heading (`tabIndex={-1}`).
 */
export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength, aiAvailable }: SectionCardProps) {
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
  const undo = generation.undo[key];
  const textRef = useRef<HTMLTextAreaElement>(null);
```

**with:**

```tsx
  const undo = generation.undo[key];
  const run = generation.runs[key];
  const error = generation.errors[key];
  const still = useStillWorking(run?.phase === "writing");
  const retryWaiting = useRetryWait(error?.retryAt);
  const [confirming, setConfirming] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const actionRef = useRef<HTMLButtonElement>(null);
  /** "Replace text" was chosen, so the closing dialog sends focus to the running card. */
  const confirmed = useRef(false);
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
  function edit(text: string) {
    update((d) => editCardText(d, key, text));
```

**with:**

```tsx
  function edit(text: string) {
    // Typing in a queued card cancels its request, which was never sent; the typed text stays.
    if (run?.phase === "queued") generation.cancel([key]);
    update((d) => editCardText(d, key, text));
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
  function toggle(enabled: boolean) {
    update((d) => setCardEnabled(d, key, enabled));
```

**with:**

```tsx
  function toggle(enabled: boolean) {
    // Switching a running card off cancels it silently; switching it back on does not restart it.
    if (run !== undefined) generation.cancel([key]);
    update((d) => setCardEnabled(d, key, enabled));
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
    update((d) => restoreChurchDefault(d, defaultBenediction));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  const menuItems = [
```

**with:**

```tsx
    update((d) => restoreChurchDefault(d, defaultBenediction));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  function start() {
    generation.generate([key], { aiAvailable });
  }

  /** Generate, Regenerate and Try again: replacing the user's own or saved text asks first. */
  function write() {
    if (needsRegenerateConfirm(card)) {
      confirmed.current = false;
      setConfirming(true);
    } else {
      start();
      // Try again's alert goes; Generate becomes Waiting… (disabled): the card's Cancel takes focus.
      focusNext.current = () => actionRef.current;
    }
  }

  function cancelRun() {
    generation.cancel([key]);
    focusNext.current = () => actionRef.current;
  }

  const menuItems = [
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
            disabled={menuItems.length === 0}
```

**with:**

```tsx
            disabled={menuItems.length === 0 || run !== undefined}
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
            maxLength={maxLength}
            rows={spec.rows}
```

**with:**

```tsx
            maxLength={maxLength}
            readOnly={run?.phase === "writing"}
            rows={spec.rows}
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
      showCounter ? `card-${key}-count` : null,
    ]
```

**with:**

```tsx
      showCounter ? `card-${key}-count` : null,
      error ? `card-${key}-error` : null,
    ]
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
          {undo ? (
            <p className="flex flex-wrap items-center gap-x-1 text-sm" aria-live="polite">
              {UNDO_LINES[undo.kind]}
              <Button ref={undoRef} variant="link" className="h-11 px-1 md:h-auto" onClick={undoLast}>
                Undo
              </Button>
            </p>
          ) : null}
        </>
```

**with:**

```tsx
          {undo && run === undefined ? (
            <p className="flex flex-wrap items-center gap-x-1 text-sm" aria-live="polite">
              {UNDO_LINES[undo.kind]}
              <Button ref={undoRef} variant="link" className="h-11 px-1 md:h-auto" onClick={undoLast}>
                Undo
              </Button>
            </p>
          ) : null}
          {/* A bulk run's errors are announced politely here, not as one alert per card. */}
          <p className="sr-only" aria-live="polite">
            {error?.bulk ? error.message : null}
          </p>
          {error ? (
            <Alert id={`card-${key}-error`} variant="destructive" role={error.bulk ? undefined : "alert"}>
              <CircleAlertIcon aria-hidden="true" />
              <AlertTitle className="whitespace-normal">{error.message}</AlertTitle>
              {error.retryable || error.link ? (
                <AlertDescription className="flex flex-wrap gap-2 pt-2">
                  {error.retryable ? (
                    <Button variant="outline" size="touch" disabled={retryWaiting} onClick={write}>
                      Try again
                    </Button>
                  ) : null}
                  {error.link ? (
                    <Link href={error.link.href} className={buttonVariants({ variant: "outline", size: "touch" })}>
                      {error.link.label}
                    </Link>
                  ) : null}
                </AlertDescription>
              ) : null}
            </Alert>
          ) : null}
          {error?.retryable ? null : (
            <div className="flex flex-wrap items-center justify-end gap-2">
              {run ? (
                <>
                  {run.phase === "queued" ? (
                    <Button variant="outline" size="touch" disabled>
                      Waiting…
                    </Button>
                  ) : (
                    <PendingButton pending pendingLabel="Writing…" size="touch">
                      Writing…
                    </PendingButton>
                  )}
                  <Button
                    ref={actionRef}
                    variant="ghost"
                    size="icon-lg"
                    className="size-11 md:size-8"
                    aria-label={`Cancel ${spec.label}`}
                    onClick={cancelRun}
                  >
                    <XIcon aria-hidden="true" />
                  </Button>
                </>
              ) : hasText ? (
                <>
                  {aiAvailable ? null : <span className="text-sm text-muted-foreground">AI isn&apos;t set up</span>}
                  <Button ref={actionRef} variant="outline" size="touch" disabled={!aiAvailable} onClick={write}>
                    Regenerate
                  </Button>
                </>
              ) : (
                <Button ref={actionRef} size="touch" onClick={write}>
                  Generate
                </Button>
              )}
              <p className="w-full text-right text-sm text-muted-foreground" aria-live="polite">
                {still ? STILL_WORKING : null}
              </p>
            </div>
          )}
        </>
```

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

```tsx
      )}
    </section>
```

**with:**

```tsx
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Replace your text?"
        description={`Regenerate replaces the text in ${spec.label} with a new AI draft. You can undo right after.`}
        confirmLabel="Replace text"
        cancelLabel="Keep my text"
        onConfirm={() => {
          confirmed.current = true;
          setConfirming(false);
          start();
        }}
        // Keep my text: back to the button that opened it. Replace text: that button is gone, so the card's Cancel.
        finalFocus={() => {
          if (!confirmed.current) return true;
          const cancel = actionRef.current;
          return cancel !== null && cancel.isConnected ? cancel : headingRef.current;
        }}
      />
    </section>
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx

import { OutlineLandmark } from "./outline-landmark";
```

**with:**

```tsx

import { AiBar } from "./ai-bar";
import { OutlineLandmark } from "./outline-landmark";
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
      <SermonTitleField maxLength={config.limits.max_sermon_title} />
      <section aria-labelledby="order-of-worship" className="grid gap-3">
```

**with:**

```tsx
      <SermonTitleField maxLength={config.limits.max_sermon_title} />
      <AiBar aiAvailable={config.ai_available} />
      <section aria-labelledby="order-of-worship" className="grid gap-3">
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
                      maxLength={config.limits.max_section_text}
                    />
```

**with:**

```tsx
                      maxLength={config.limits.max_section_text}
                      aiAvailable={config.ai_available}
                    />
```

- [ ] **Step 5 (agent): Run the tests three times, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "Test Files|Tests |FAIL"); done
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** three times ` Test Files  1 passed (1)`, `      Tests  27 passed (27)` and no `FAIL`; the suite ` Test Files  75 passed (75)`, `      Tests  506 passed (506)`; `typecheck 0` and `lint 0`; ` M` for the three modified files and `??` for the two new ones. A run that fails even once is a failure: make the test wait for a condition (`findBy`, `waitFor`), never retry it.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/ai-bar.tsx frontend/src/components/builder/liturgy/use-still-working.ts frontend/src/components/builder/liturgy/section-card.tsx frontend/src/components/builder/liturgy/liturgy-step.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -m "Liturgy: Generate, Regenerate with confirm and Undo, the card errors and the AI bar (S Generate and Regenerate; BC-2, BC-5, BC-6, BC-13)" -m "Each card has Generate or Regenerate (asking first before replacing the
user's or a saved service's text; off without AI), Waiting and Writing
with Cancel and Still working after 8 s, and its error with Try again.
The AI bar writes every switched-on empty card, 3 at a time, with Cancel
and Writing k of n, and shows the no-AI banner and the two notices. Tests
cover S's dom cases 4-12: the stale rule, navigation, the 429 and a 401.
Frontend 490 -> 506 tests in 75 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 5 files changed.

### Task 10: The communion card and custom elements (S UX "Communion card", "Custom elements", Testing dom 14-15; BC-10, BC-11, BC-12; F D17; clarifications 6, 25, 26, 34, 36)

The rest of the outline. `CommunionCard` sits after the Second Hymn: its header is the switch with S's toggle label; the helper says why it is on or off ("On by default — {October 4, 2026} is the first Sunday of the month.", "Off by default — it's on by default only on the first Sunday of the month.", "You changed this." or "Set from the saved service.", the last two with **Use default**); **Show communion text** reveals the config's blocks read-only (headings, paragraphs, bold responses) and the caption (clarification 26). Custom elements render right after the outline item whose `anchors_after` holds their place (an unknown place reads as the end; clarification 6) as dashed cards with the "Custom" chip, inline Label, Text and Place, the "won't be printed" message for a blank label (the card is then titled "Custom element"; clarification 25), and ⋯ → **Remove**, which offers Undo in a toast ("Removed “{label}”.") through 3b's `useUndoToasts`, so it never outlives the step and is checked against the church. **Add custom element** opens the dialog (a bottom sheet below `md`): Label (required: "Label is required." and focus), Text (optional) and Place (first place by default); Add appends the element trimmed with a new id, closes, and scrolls to it; the fields are empty the next time; the sheet scrolls within 85 dvh on a phone. At 30 elements Add is disabled with "You can add up to 30 custom elements.", and Undo of a Remove refuses with that toast when another element has filled the place (clarification 36). After Remove, focus goes to the next card's heading, or to "Add custom element" when none follows (clarification 34). No custom element has Generate (owner answer of 2026-09-30, F D17). T8's outline test gains the communion row (edited, 0).

**Files:**
- Create: `frontend/src/components/builder/liturgy/communion-card.tsx`, `custom-element-card.tsx`, `add-custom-element-dialog.tsx` (in `frontend/src/components/builder/liturgy/`)
- Modify: `frontend/src/components/builder/liturgy/liturgy-step.tsx` (the communion row, the custom elements, Add, Remove with Undo)
- Test: `frontend/src/components/builder/liturgy/liturgy-step.test.tsx` (+9; T8's outline test edited, 0)

**Interfaces:**
- Consumes: `setCommunion`, `restoreCommunionDefault`, `addCustomElement`, `updateCustomElement`, `removeCustomElement`, `restoreCustomElement`, `normalizePlacement` (T2); `isFirstSundayOfMonth`, `formatServiceDate` (2b); `Dialog` (T7); `Select` with `items` (F §4.9 item 3), `Collapsible`, `useUndoToasts` and `UNDO_TOAST_MS` (3b `components/builder/hymns/use-undo-toasts.ts`).
- Produces: `CommunionCard({communion})` (region named by the toggle label, id `communion`); `CustomElementCard({element, placements, limits, onRemove})` (id `custom-{id}`); `AddCustomElementDialog({open, onOpenChange, placements, limits, onAdd})`. Later users: T11 (the page), 5a (the Review links).

Counts after this task: frontend **515 passed in 75 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/builder/liturgy | tr '\n' ' '; echo
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ai-bar.tsx liturgy-step.test.tsx liturgy-step.tsx outline-landmark.tsx section-card.tsx sermon-title-field.tsx use-still-working.ts`; ` Test Files  75 passed (75)`, `      Tests  506 passed (506)`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
import { editOccasion, editScriptureLines, setPick } from "@/lib/draft/readings";
```

**with:**

```tsx
import { useDraft } from "@/lib/draft/context";
import { editOccasion, editScriptureLines, setDate, setPick } from "@/lib/draft/readings";
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
  church,
  churchProfile,
```

**with:**

```tsx
  church,
  CHURCH_IDS,
  churchProfile,
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
import { LiturgyStep } from "./liturgy-step";
import { STILL_WORKING } from "./use-still-working";
```

**with:**

```tsx
import { LiturgyStep } from "./liturgy-step";
import { UNDO_TOAST_MS } from "../hymns/use-undo-toasts";

import { STILL_WORKING } from "./use-still-working";
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
      "Second Hymn",
      "Prayers of the People",
```

**with:**

```tsx
      "Second Hymn",
      "Include communion liturgy (The Sacrament of the Lord's Supper)",
      "Prayers of the People",
```

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

```tsx
    expect(screen.queryByText(/No occasion or readings yet/)).toBeNull();
  });
});

```

**with:**

```tsx
    expect(screen.queryByText(/No occasion or readings yet/)).toBeNull();
  });
});

// --- slice 4b T10: communion and custom elements ------------------------------------------

/** Moves the draft's date, as Date & readings would (the communion default follows it). */
function MoveDate() {
  const { update } = useDraft();
  return (
    <button type="button" onClick={() => update((d) => setDate(d, "2026-10-11"))}>
      Move to October 11
    </button>
  );
}

function withElements(elements: DraftV1["liturgy"]["custom_elements"], d: DraftV1 = testDraft()): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, custom_elements: elements } };
}

const COMMUNION = "Include communion liturgy (The Sacrament of the Lord's Supper)";

describe("the communion card (S Communion card)", () => {
  it("follows the first-Sunday rule until toggled, says why, restores the default, and shows the fixed text", async () => {
    const { user } = renderStep(testDraft(), {}, <MoveDate />);
    const communion = await screen.findByRole("region", { name: COMMUNION });
    const toggle = within(communion).getByRole("switch", { name: COMMUNION });
    expect(toggle).toBeChecked();
    expect(within(communion).getByText("On by default — October 4, 2026 is the first Sunday of the month.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Move to October 11" }));
    expect(toggle).not.toBeChecked();
    expect(within(communion).getByText("Off by default — it's on by default only on the first Sunday of the month.")).toBeInTheDocument();
    await user.click(toggle);
    expect(toggle).toBeChecked();
    expect(within(communion).getByText("You changed this.")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy).toMatchObject({ include_communion: true, communion_origin: "user" }));
    await user.click(within(communion).getByRole("button", { name: "Use default" }));
    expect(toggle).not.toBeChecked();
    expect(within(communion).queryByRole("button", { name: "Use default" })).toBeNull();
    // The fixed text, read-only, from the config.
    expect(within(communion).queryByText("And also with you.")).toBeNull();
    await user.click(within(communion).getByRole("button", { name: "Show communion text" }));
    expect(within(communion).getByRole("heading", { level: 4, name: "The Sacrament of the Lord's Supper" })).toBeInTheDocument();
    expect(within(communion).getByRole("heading", { level: 5, name: "Invitation to the Table" })).toBeInTheDocument();
    expect(within(communion).getByText("And also with you.")).toHaveClass("font-semibold");
    expect(within(communion).getByText("Printed after the Second Hymn. The same text is used for every service.")).toBeInTheDocument();
  });

  it("says when communion came from a saved service", async () => {
    const d = testDraft();
    renderStep({ ...d, liturgy: { ...d.liturgy, include_communion: false, communion_origin: "archive" } });
    const communion = await screen.findByRole("region", { name: COMMUNION });
    expect(within(communion).getByText("Set from the saved service.")).toBeInTheDocument();
    expect(within(communion).getByRole("button", { name: "Use default" })).toBeInTheDocument();
  });
});

describe("custom elements (S Custom elements)", () => {
  it("requires a label, adds after its place with the fields trimmed, scrolls to it, and opens empty next time", async () => {
    const scroll = vi.spyOn(Element.prototype, "scrollIntoView");
    const { user } = renderStep();
    await user.click(await screen.findByRole("button", { name: "Add custom element" }));
    const dialog = await screen.findByRole("dialog", { name: "Add custom element" });
    expect(within(dialog).getByText("A heading and text printed in the Word files at the place you choose.")).toBeInTheDocument();
    expect(within(dialog).getByRole("combobox", { name: "Place" })).toHaveTextContent("After Call to Worship");
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(within(dialog).getByText("Label is required.")).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Label" })).toHaveFocus();
    await user.type(within(dialog).getByRole("textbox", { name: "Label" }), "  Children's Moment ");
    expect(within(dialog).queryByText("Label is required.")).toBeNull();
    await user.type(within(dialog).getByRole("textbox", { name: "Text (optional)" }), "Come forward. ");
    await user.click(within(dialog).getByRole("combobox", { name: "Place" }));
    await user.click(await screen.findByRole("option", { name: "After Opening Prayer" }));
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    const added = await screen.findByRole("region", { name: "Children's Moment" });
    expect(outline().slice(0, 4)).toEqual(["Call to Worship", "Opening Prayer", "Children's Moment", "First Hymn"]);
    expect(within(added).getByText("Custom")).toBeInTheDocument();
    expect(within(added).getByRole("textbox", { name: "Text" })).toHaveValue("Come forward.");
    await waitFor(() =>
      expect(stored().liturgy.custom_elements).toEqual([
        { id: expect.any(String), label: "Children's Moment", text: "Come forward.", insert_after: "opening_prayer" },
      ]),
    );
    await waitFor(() => expect(scroll.mock.contexts).toContain(added));
    await user.click(screen.getByRole("button", { name: "Add custom element" }));
    const again = await screen.findByRole("dialog", { name: "Add custom element" });
    expect(within(again).getByRole("textbox", { name: "Label" })).toHaveValue("");
    expect(within(again).getByRole("combobox", { name: "Place" })).toHaveTextContent("After Call to Worship");
  });

  it("edits the label, text and place inline; a blank label says it won't print, and an unknown place is the end", async () => {
    const { user } = renderStep(
      withElements([
        { id: "a", label: "Anthem", text: "<b>Choir</b>", insert_after: "sermon" },
        { id: "b", label: "Minute for Mission", text: "", insert_after: "bogus" },
      ]),
    );
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    expect(within(anthem).getByRole("textbox", { name: "Text" })).toHaveValue("<b>Choir</b>");
    const rows = outline();
    expect(rows.indexOf("Anthem")).toBe(rows.indexOf("Sermon Title · [Sermon title]") + 1);
    expect(rows.at(-1)).toBe("Minute for Mission"); // an unknown place prints at the end
    expect(within(card("Minute for Mission")).getByRole("combobox", { name: "Place" })).toHaveTextContent("At the end (after Benediction)");
    await user.click(within(anthem).getByRole("combobox", { name: "Place" }));
    await user.click(await screen.findByRole("option", { name: "After Second Hymn" }));
    await waitFor(() => expect(outline().indexOf("Anthem")).toBe(outline().indexOf("Second Hymn") + 1));
    const label = within(card("Anthem")).getByRole("textbox", { name: "Label" });
    await user.clear(label);
    const blank = screen.getByRole("region", { name: "Custom element" });
    expect(within(blank).getByText("Add a label, or remove this element — it won't be printed without one.")).toBeInTheDocument();
    await user.type(label, "Choir Anthem");
    await waitFor(() =>
      expect(stored().liturgy.custom_elements[0]).toEqual({ id: "a", label: "Choir Anthem", text: "<b>Choir</b>", insert_after: "second_hymn" }),
    );
  });

  it("Remove offers Undo, which puts the element back at the same index", async () => {
    const { user } = renderStep(
      withElements([
        { id: "a", label: "Anthem", text: "", insert_after: "sermon" },
        { id: "b", label: "Children's Moment", text: "", insert_after: "sermon" },
      ]),
    );
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    await user.click(within(anthem).getByRole("button", { name: "More actions for Anthem" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    expect(screen.queryByRole("region", { name: "Anthem" })).toBeNull();
    const toastText = await screen.findByText("Removed “Anthem”.");
    await waitFor(() => expect(stored().liturgy.custom_elements.map((e) => e.id)).toEqual(["b"]));
    expect(UNDO_TOAST_MS).toBe(8000);
    await user.click(within(toastText.closest("li") as HTMLElement).getByRole("button", { name: "Undo" }));
    expect(await screen.findByRole("region", { name: "Anthem" })).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "b"]));
  });

  it("stops at 30 elements", async () => {
    const thirty = Array.from({ length: 30 }, (_, i) => ({ id: `e${i}`, label: `Element ${i}`, text: "", insert_after: "end" }));
    renderStep(withElements(thirty));
    expect(await screen.findByRole("button", { name: "Add custom element" })).toBeDisabled();
    expect(screen.getByText("You can add up to 30 custom elements.")).toBeInTheDocument();
  });

  it("after Remove, focus goes to the next card's heading, or to Add custom element when none follows", async () => {
    const { user } = renderStep(
      withElements([
        { id: "a", label: "Anthem", text: "", insert_after: "sermon" },
        { id: "b", label: "Minute for Mission", text: "", insert_after: "end" },
      ]),
    );
    const anthem = await screen.findByRole("region", { name: "Anthem" });
    await user.click(within(anthem).getByRole("button", { name: "More actions for Anthem" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    // After the Sermon row come two landmark rows and the communion card, then Prayers of the People.
    await waitFor(() => expect(within(card("Prayers of the People")).getByRole("heading", { name: "Prayers of the People" })).toHaveFocus());
    await user.click(within(card("Minute for Mission")).getByRole("button", { name: "More actions for Minute for Mission" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Add custom element" })).toHaveFocus());
  });

  // Heavy: 30 cards, a Remove and an Add through the dialog; near Vitest's 5 s default on a busy machine.
  it("Undo of Remove never goes past 30 elements", { timeout: 10_000 }, async () => {
    const thirty = Array.from({ length: 30 }, (_, i) => ({ id: `e${i}`, label: `Element ${i}`, text: "", insert_after: "end" }));
    const { user } = renderStep(withElements(thirty));
    const first = await screen.findByRole("region", { name: "Element 0" });
    await user.click(within(first).getByRole("button", { name: "More actions for Element 0" }));
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    const toastText = await screen.findByText("Removed “Element 0”.");
    await user.click(screen.getByRole("button", { name: "Add custom element" }));
    const dialog = await screen.findByRole("dialog", { name: "Add custom element" });
    await user.type(within(dialog).getByRole("textbox", { name: "Label" }), "Anthem");
    await user.click(within(dialog).getByRole("button", { name: "Add" }));
    expect(await screen.findByRole("region", { name: "Anthem" })).toBeInTheDocument();
    await user.click(within(toastText.closest("li") as HTMLElement).getByRole("button", { name: "Undo" }));
    // The toast and the step's own line.
    await waitFor(() => expect(screen.getAllByText("You can add up to 30 custom elements.")).toHaveLength(2));
    expect(screen.queryByRole("region", { name: "Element 0" })).toBeNull();
    await waitFor(() => expect(stored().liturgy.custom_elements).toHaveLength(30));
  });

  it("keeps each church's elements in its own draft (streamlit_tests/test_streamlit_tenancy.py)", async () => {
    const hope = church({ id: CHURCH_IDS.hope, name: "Hope" });
    window.localStorage.setItem(
      draftKey(USER_ID, hope.id),
      JSON.stringify({ ...withElements([{ id: "h", label: "Hope's Anthem", text: "", insert_after: "end" }]), church_id: hope.id }),
    );
    const grace = renderStep(withElements([{ id: "g", label: "Grace's Anthem", text: "", insert_after: "end" }]));
    expect(await screen.findByRole("region", { name: "Grace's Anthem" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Hope's Anthem" })).toBeNull();
    grace.unmount();
    installFakeApi({
      "GET /church": churchProfile({ ...hope }),
      "GET /lectionary/readings": lectionaryRoute(),
      "GET /liturgy/config": liturgyConfig(),
    });
    renderWithProviders(
      <BuilderLayout>
        <LiturgyStep />
      </BuilderLayout>,
      { me: me({ churches: [church(), hope] }), church: hope, path: "/builder/liturgy" },
    );
    expect(await screen.findByRole("region", { name: "Hope's Anthem" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Grace's Anthem" })).toBeNull();
  });
});

```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "^ FAIL|Tests ")
```

**Expected:**

```
⎯⎯⎯⎯⎯⎯ Failed Tests 10 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > the Liturgy step (S User experience) > lays out the order of worship as the Word files print it, with the draft's hymns, readings and title
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > the communion card (S Communion card) > follows the first-Sunday rule until toggled, says why, restores the default, and shows the fixed text
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > the communion card (S Communion card) > says when communion came from a saved service
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > requires a label, adds after its place with the fields trimmed, scrolls to it, and opens empty next time
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > edits the label, text and place inline; a blank label says it won't print, and an unknown place is the end
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > Remove offers Undo, which puts the element back at the same index
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > stops at 30 elements
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > after Remove, focus goes to the next card's heading, or to Add custom element when none follows
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > Undo of Remove never goes past 30 elements
 FAIL  |dom| src/components/builder/liturgy/liturgy-step.test.tsx > custom elements (S Custom elements) > keeps each church's elements in its own draft (streamlit_tests/test_streamlit_tenancy.py)
      Tests  10 failed | 26 passed (36)
```

- [ ] **Step 4 (agent): Write the communion card, the custom elements and the dialog**

**Create `frontend/src/components/builder/liturgy/communion-card.tsx`:**

```tsx
"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Switch } from "@/components/ui/switch";
import type { CommunionBlock, LiturgyConfig } from "@/lib/api/types";
import { formatServiceDate, isFirstSundayOfMonth } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { restoreCommunionDefault, setCommunion } from "@/lib/liturgy/cards";
import { cn } from "@/lib/utils";

function Block({ block }: { block: CommunionBlock }) {
  switch (block.style) {
    case "heading1":
      return <h4 className="font-semibold">{block.text}</h4>;
    case "heading2":
      return <h5 className="pt-2 font-medium">{block.text}</h5>;
    case "response":
      return <p className="font-semibold">{block.text}</p>;
    case "text":
      return <p>{block.text}</p>;
    default:
      return null;
  }
}

/**
 * The communion card (S UX "Communion card"; BC-10, BC-11): the switch, a
 * helper that says why it is on or off (the first-Sunday rule while it is the
 * default, "You changed this." or "Set from the saved service." with "Use
 * default"), and the fixed communion text, read-only, behind "Show communion
 * text". It sits in the outline after the Second Hymn.
 */
export function CommunionCard({ communion }: { communion: LiturgyConfig["communion"] }) {
  const { draft, update } = useDraft();
  const [open, setOpen] = useState(false);
  const l = draft.liturgy;
  const date = draft.readings.date_iso;
  const helper =
    l.communion_origin === "default"
      ? isFirstSundayOfMonth(date)
        ? `On by default — ${formatServiceDate(date)} is the first Sunday of the month.`
        : "Off by default — it's on by default only on the first Sunday of the month."
      : l.communion_origin === "user"
        ? "You changed this."
        : "Set from the saved service.";

  return (
    <section id="communion" aria-labelledby="communion-title" className="grid scroll-mt-24 gap-3 rounded-lg border p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Switch
          checked={l.include_communion}
          onCheckedChange={(checked) => update((d) => setCommunion(d, checked))}
          aria-labelledby="communion-title"
          className="after:-inset-y-3.5"
        />
        <h3 id="communion-title" className="min-w-0 flex-1 text-base font-medium">
          {communion.toggle_label}
        </h3>
      </div>
      <p className="flex flex-wrap items-center gap-x-1 text-sm text-muted-foreground">
        {helper}
        {l.communion_origin === "default" ? null : (
          <Button variant="link" className="h-11 px-1 md:h-auto" onClick={() => update(restoreCommunionDefault)}>
            Use default
          </Button>
        )}
      </p>
      <Collapsible open={open} onOpenChange={setOpen} className="grid gap-2">
        <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
          <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
          Show communion text
        </CollapsibleTrigger>
        <CollapsibleContent className="grid gap-2">
          <div className="grid gap-2 rounded-md bg-muted/40 p-3 text-sm">
            {communion.blocks.map((block, i) => (
              <Block key={i} block={block} />
            ))}
          </div>
          <p className="text-xs text-muted-foreground">Printed after the Second Hymn. The same text is used for every service.</p>
        </CollapsibleContent>
      </Collapsible>
    </section>
  );
}
```

**Create `frontend/src/components/builder/liturgy/custom-element-card.tsx`:**

```tsx
"use client";

import { EllipsisIcon } from "lucide-react";
import { useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgyConfig } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { normalizePlacement, updateCustomElement, type CustomElement } from "@/lib/liturgy/cards";
import { useAutosize } from "@/lib/use-autosize";

export type Placements = LiturgyConfig["custom_placements"];

/**
 * A custom element in its printed position (S UX "Custom elements"; BC-12):
 * a dashed card with the "Custom" chip and inline Label, Text and Place. A
 * blank label says the element will not be printed without one; ⋯ → Remove
 * takes it out (the step offers Undo). No AI Generate (F D17). The card's id
 * is `custom-{id}`.
 */
export function CustomElementCard({
  element,
  placements,
  limits,
  onRemove,
}: {
  element: CustomElement;
  placements: Placements;
  limits: LiturgyConfig["limits"];
  onRemove: () => void;
}) {
  const { update } = useDraft();
  const textRef = useRef<HTMLTextAreaElement>(null);
  useAutosize(textRef, element.text);
  const id = element.id;
  const name = element.label.trim() === "" ? "Custom element" : element.label.trim();
  const blank = element.label.trim() === "";
  const items = Object.fromEntries(placements.map((p) => [p.key, p.label]));
  const edit = (patch: Partial<Omit<CustomElement, "id">>) => update((d) => updateCustomElement(d, id, patch));

  return (
    <section
      id={`custom-${id}`}
      aria-labelledby={`custom-${id}-title`}
      className="grid scroll-mt-24 gap-3 rounded-lg border border-dashed p-4"
    >
      <div className="flex min-w-0 items-center gap-2">
        <h3
          id={`custom-${id}-title`}
          tabIndex={-1}
          data-card-heading=""
          className="min-w-0 flex-1 text-base font-medium wrap-anywhere outline-none"
        >
          {name}
        </h3>
        <Badge variant="outline">Custom</Badge>
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`More actions for ${name}`}
            className={`${buttonVariants({ variant: "ghost", size: "icon-lg" })} size-11 shrink-0 md:size-8`}
          >
            <EllipsisIcon aria-hidden="true" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-auto min-w-44">
            <DropdownMenuItem onClick={onRemove} className="min-h-11 md:min-h-8">
              Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor={`custom-${id}-label`}>Label</Label>
        <Input
          id={`custom-${id}-label`}
          value={element.label}
          maxLength={limits.max_custom_label}
          aria-invalid={blank ? true : undefined}
          aria-describedby={blank ? `custom-${id}-blank` : undefined}
          onChange={(event) => edit({ label: event.target.value })}
          className="h-11"
        />
        {blank ? (
          <p id={`custom-${id}-blank`} className="text-sm text-destructive">
            Add a label, or remove this element — it won&apos;t be printed without one.
          </p>
        ) : null}
      </div>
      <div className="grid gap-1.5">
        <Label htmlFor={`custom-${id}-text`}>Text</Label>
        <Textarea
          id={`custom-${id}-text`}
          ref={textRef}
          value={element.text}
          maxLength={limits.max_custom_text}
          className="max-h-[60vh] overflow-y-auto"
          onChange={(event) => edit({ text: event.target.value })}
        />
      </div>
      <div className="grid gap-1.5">
        <Label id={`custom-${id}-place`}>Place</Label>
        <Select
          value={normalizePlacement(element.insert_after)}
          items={items}
          onValueChange={(value) => {
            if (typeof value === "string") edit({ insert_after: value });
          }}
        >
          <SelectTrigger aria-labelledby={`custom-${id}-place`} className="h-11 w-full sm:w-80 data-[size=default]:h-11">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {placements.map((p) => (
              <SelectItem key={p.key} value={p.key}>
                {p.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </section>
  );
}
```

**Create `frontend/src/components/builder/liturgy/add-custom-element-dialog.tsx`:**

```tsx
"use client";

import { useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgyConfig } from "@/lib/api/types";
import type { CustomElement } from "@/lib/liturgy/cards";

/**
 * "Add custom element" (S UX "Custom elements"; BC-12): a dialog, a bottom
 * sheet below `md`, with a native form (F §4.8): Label (required), Text
 * (optional) and Place (defaulting to the first place, "After Call to
 * Worship", as app.py did). A blank label says "Label is required." and
 * focuses the field. After Add the fields are empty the next time it opens.
 */
export function AddCustomElementDialog({
  open,
  onOpenChange,
  placements,
  limits,
  onAdd,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  placements: LiturgyConfig["custom_placements"];
  limits: LiturgyConfig["limits"];
  onAdd: (element: Omit<CustomElement, "id">) => void;
}) {
  const first = placements[0]?.key ?? "end";
  const [label, setLabel] = useState("");
  const [text, setText] = useState("");
  const [place, setPlace] = useState(first);
  const [missing, setMissing] = useState(false);
  const labelRef = useRef<HTMLInputElement>(null);
  const items = Object.fromEntries(placements.map((p) => [p.key, p.label]));

  function reset() {
    setLabel("");
    setText("");
    setPlace(first);
    setMissing(false);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (label.trim() === "") {
      setMissing(true);
      labelRef.current?.focus();
      return;
    }
    onAdd({ label, text, insert_after: place });
    reset();
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) reset();
        onOpenChange(next);
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto max-md:pb-[calc(1rem+env(safe-area-inset-bottom))] md:max-w-lg"
      >
        <DialogHeader>
          <DialogTitle>Add custom element</DialogTitle>
          <DialogDescription>A heading and text printed in the Word files at the place you choose.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} noValidate className="grid gap-4">
          <div className="grid gap-1.5">
            <Label htmlFor="new-custom-label">Label</Label>
            <Input
              id="new-custom-label"
              ref={labelRef}
              value={label}
              maxLength={limits.max_custom_label}
              placeholder="e.g. Children's Moment"
              aria-invalid={missing ? true : undefined}
              aria-describedby={missing ? "new-custom-label-error" : undefined}
              onChange={(event) => {
                setLabel(event.target.value);
                setMissing(false);
              }}
              className="h-11"
            />
            {missing ? (
              <p id="new-custom-label-error" className="text-sm text-destructive">
                Label is required.
              </p>
            ) : null}
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="new-custom-text">Text (optional)</Label>
            <Textarea
              id="new-custom-text"
              value={text}
              maxLength={limits.max_custom_text}
              placeholder="Words for the bulletin or order of service"
              className="max-h-[40vh] overflow-y-auto"
              onChange={(event) => setText(event.target.value)}
            />
          </div>
          <div className="grid gap-1.5">
            <Label id="new-custom-place">Place</Label>
            <Select
              value={place}
              items={items}
              onValueChange={(value) => {
                if (typeof value === "string") setPlace(value);
              }}
            >
              <SelectTrigger aria-labelledby="new-custom-place" className="h-11 w-full data-[size=default]:h-11">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {placements.map((p) => (
                  <SelectItem key={p.key} value={p.key}>
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <DialogClose render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>Cancel</DialogClose>
            <Button type="submit" size="touch" className="md:h-8">
              Add
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
import { Fragment, useEffect } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
```

**with:**

```tsx
import { PlusIcon } from "lucide-react";
import { Fragment, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/app/error-state";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { useDraft } from "@/lib/draft/context";
import {
  addCustomElement,
  normalizePlacement,
  removeCustomElement,
  restoreCustomElement,
  type CustomElement,
} from "@/lib/liturgy/cards";
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
import { AiBar } from "./ai-bar";
```

**with:**

```tsx
import { useUndoToasts } from "../hymns/use-undo-toasts";

import { AddCustomElementDialog } from "./add-custom-element-dialog";
import { AiBar } from "./ai-bar";
import { CommunionCard } from "./communion-card";
import { CustomElementCard } from "./custom-element-card";
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
 * hymns, readings, sermon and creed. It reads and writes only the draft (F
```

**with:**

```tsx
 * hymns, readings, sermon and creed, the communion card after the Second
 * Hymn, and each custom element right after the item that owns its place (an
 * unknown place reads as the end), then "Add custom element" (at most 30;
 * Remove offers Undo in a toast that never outlives the step). It reads and
 * writes only the draft (F
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
  const { draft } = useDraft();
  const { clearUndo } = useLiturgyGeneration();
```

**with:**

```tsx
  const { draft, update, peek } = useDraft();
  const { clearUndo } = useLiturgyGeneration();
  const showUndo = useUndoToasts();
  const [adding, setAdding] = useState(false);
  const scrollTo = useRef<string | null>(null);
  /** After Remove: the id of the heading that takes focus (the next card's), or null for the Add button. */
  const focusAfterRemove = useRef<string | null | undefined>(undefined);
  const addRef = useRef<HTMLButtonElement>(null);
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
  }, [loaded]);

```

**with:**

```tsx
  }, [loaded]);

  // After Add, the page scrolls to the new card once it has rendered.
  useEffect(() => {
    if (scrollTo.current === null) return;
    const element = document.getElementById(`custom-${scrollTo.current}`);
    if (element === null) return;
    scrollTo.current = null;
    element.scrollIntoView({ block: "center" });
  });

  // After Remove the element's card is gone: focus goes to the next card's heading, or the Add button.
  useEffect(() => {
    const target = focusAfterRemove.current;
    if (target === undefined) return;
    focusAfterRemove.current = undefined;
    (target === null ? addRef.current : document.getElementById(target))?.focus();
  });

```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
  const defaultBenediction = profile?.default_benediction ?? config.default_benediction_fallback;

```

**with:**

```tsx
  const defaultBenediction = profile?.default_benediction ?? config.default_benediction_fallback;
  const customs = draft.liturgy.custom_elements;
  const maxCustom = config.limits.max_custom_elements;
  const full = customs.length >= maxCustom;

  function after(anchors: readonly string[]): CustomElement[] {
    return anchors.flatMap((anchor) => customs.filter((e) => normalizePlacement(e.insert_after) === anchor));
  }

  function add(element: Omit<CustomElement, "id">) {
    const id = crypto.randomUUID();
    update((d) => addCustomElement(d, element, id));
    scrollTo.current = id;
    setAdding(false);
  }

  function remove(element: CustomElement) {
    const found = removeCustomElement(draft, element.id);
    if (found === null) return;
    const headings = [...document.querySelectorAll<HTMLElement>("[data-card-heading]")];
    const at = headings.findIndex((h) => h.id === `custom-${element.id}-title`);
    focusAfterRemove.current = at >= 0 && at + 1 < headings.length ? headings[at + 1].id : null;
    update((d) => removeCustomElement(d, element.id)?.draft ?? d);
    const label = element.label.trim() === "" ? "Custom element" : element.label.trim();
    showUndo(`Removed “${label}”.`, () => {
      // Another element may have been added meanwhile: never past the limit.
      if (peek().liturgy.custom_elements.length >= maxCustom) {
        toast.message(`You can add up to ${maxCustom} custom elements.`);
        return;
      }
      update((d) => restoreCustomElement(d, found.element, found.index, maxCustom));
    });
  }

```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
                ) : null}
```

**with:**

```tsx
                ) : item.kind === "communion" ? (
                  <li>
                    <CommunionCard communion={config.communion} />
                  </li>
                ) : null}
                {after(item.anchors_after).map((element) => (
                  <li key={element.id}>
                    <CustomElementCard
                      element={element}
                      placements={config.custom_placements}
                      limits={config.limits}
                      onRemove={() => remove(element)}
                    />
                  </li>
                ))}
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
      </section>
```

**with:**

```tsx
        <div className="grid gap-1.5">
          <div>
            <Button ref={addRef} variant="outline" size="touch" disabled={full} onClick={() => setAdding(true)}>
              <PlusIcon aria-hidden="true" data-icon="inline-start" />
              Add custom element
            </Button>
          </div>
          {full ? (
            <p className="text-sm text-muted-foreground">
              You can add up to {maxCustom} custom elements.
            </p>
          ) : null}
        </div>
      </section>
      <AddCustomElementDialog
        open={adding}
        onOpenChange={setAdding}
        placements={config.custom_placements}
        limits={config.limits}
        onAdd={add}
      />
```

- [ ] **Step 5 (agent): Run the tests three times, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/liturgy 2>&1 | grep -E "Test Files|Tests |FAIL"); done
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** three times ` Test Files  1 passed (1)`, `      Tests  36 passed (36)` and no `FAIL`; the suite ` Test Files  75 passed (75)`, `      Tests  515 passed (515)`; `typecheck 0` and `lint 0`; ` M` for `liturgy-step.tsx` and `liturgy-step.test.tsx`, `??` for the three new files.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/communion-card.tsx frontend/src/components/builder/liturgy/custom-element-card.tsx frontend/src/components/builder/liturgy/add-custom-element-dialog.tsx frontend/src/components/builder/liturgy/liturgy-step.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -m "Liturgy: the communion card and custom elements in their printed places (S Communion card, Custom elements; BC-10, BC-11, BC-12)" -m "Communion follows the first-Sunday rule until toggled, says why, offers
Use default, and shows the fixed text read-only. Custom elements show
right after their place with inline label, text and place, a message for
a blank label, and Remove with Undo; Add custom element opens a dialog
(a bottom sheet on phones) that requires a label, trims, scrolls to the
new card and opens empty next time; at most 30. No AI for them (F D17).
Frontend 506 -> 515 tests in 75 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 5 files changed.

**Review checkpoint (T7-T10, batch C):** the dialog is the pinned upstream file plus a comment; every S card state, message and chip matches S's copy (or a numbered clarification); typed text is never replaced without the dialog; nothing is sent without AI; the stale, cancel and 429 rules are tested through the screen; the tests pass three runs in a row; counts match.

### Task 11: Turn the step on: `"liturgy"` ships, its route renders the step, the step bar, Still needed and the summary count it (S Frontend "Builder shell", Testing dom 17; F §4.7; AC16; clarifications 16, 27)

Slice 2's hand-off, as 3b did for Hymns: `SHIPPED_STEPS` gains `"liturgy"`, so the step bar shows "{ready} of {enabled}" (or "Complete") instead of "Soon", from `liturgyCounts` (T2), the one count the summary shares; `/builder/liturgy` renders `LiturgyStep` instead of the "Available soon" card; `stillNeeded` gains "{Card label} is empty — Write or generate it" for each switched-on card with no text, linking to `/builder/liturgy#card-{key}` (`NeededItem.href`), and "No sermon title — Add one", linking to `/builder/liturgy` (clarification 27); the summary's Liturgy block becomes `LiturgySummaryBlock`: "{ready} of {enabled} liturgy sections ready" (or "All liturgy sections switched off"), " · Writing n sections…" while the provider has runs ("Writing 1 section…" for one; clarification 16), "Communion: Yes/No" and the custom-element count. The step's root becomes a region named "Liturgy", as the shell test expects of every step. Existing tests change where the shell now shows the liturgy (edited, 0): the shipped-steps list, the unshipped-step statuses, 3b's hymn Still-needed rows (now with a hymns-only shipped set), and the shell tests' Liturgy status, step card, Still-needed rows and summary block.

**Files:**
- Create: `frontend/src/components/builder/liturgy/liturgy-summary-block.tsx`
- Modify: `frontend/src/lib/draft/steps.ts`, `frontend/src/lib/draft/status.ts` (`stepStatus`, `NeededItem.href`, `stillNeeded`), `frontend/src/components/builder/still-needed.tsx`, `frontend/src/components/builder/summary-panel.tsx`, `frontend/src/components/builder/step-placeholder.tsx` (comment), `frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx`, `frontend/src/components/builder/liturgy/liturgy-step.tsx` (a region)
- Test: `frontend/src/lib/draft/status.test.ts` (+1; three tests edited, 0), `frontend/src/components/builder/builder-shell.test.tsx` (+1; two tests and the helper edited, 0)

**Interfaces:**
- Consumes: `liturgyCounts` (T2), `SECTION_LABELS` (T1), `useLiturgyGeneration().runs` (T6), `LiturgyStep` (T8-T10), 2b's shell.
- Produces: `SHIPPED_STEPS = {"readings", "hymns", "liturgy"}`; `NeededItem.href?: string`; `LiturgySummaryBlock()`. Later users: 5a (Review reuses the rows and turns "review" on; its `missingItems` reuses the wording).

Counts after this task: frontend **517 passed in 75 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns"]);`; ` Test Files  75 passed (75)`, `      Tests  515 passed (515)`.

- [ ] **Step 2 (agent): Write the failing tests**

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
  it("lists the four steps in order, ships Date & readings (2c) and Hymns (3b), and reads a step from its path", () => {
```

**with:**

```ts
  it("lists the four steps in order, ships Date & readings (2c), Hymns (3b) and Liturgy (4b), and reads a step from its path", () => {
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns"]);
```

**with:**

```ts
    expect([...SHIPPED_STEPS]).toEqual(["readings", "hymns", "liturgy"]);
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "incomplete", "soon", "not_in_archive"]);
```

**with:**

```ts
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["incomplete", "incomplete", "incomplete", "not_in_archive"]);
    expect(stepStatus(d, "liturgy", READINGS)).toEqual({ kind: "soon" });
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
    expect(stillNeeded(filled)).toEqual([
```

**with:**

```ts
    const hymnsShipped = new Set<StepId>(["readings", "hymns"]); // the liturgy's rows are 4b's test below
    expect(stillNeeded(filled, hymnsShipped)).toEqual([
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
    expect(stillNeeded(withSlots({ response: HYMN }))).toEqual([
      { step: "hymns", message: "No Opening hymn", action: "Choose one" },
      { step: "hymns", message: "No Closing hymn", action: "Choose one" },
    ]);
    expect(stillNeeded(all)).toEqual([]);
    expect(stillNeeded(filled, READINGS)).toEqual([]); // before 3b: no hymn rows
    expect(stillNeeded(filled).some((item) => item.step === "liturgy")).toBe(false); // liturgy not shipped
```

**with:**

```ts
    expect(stillNeeded(withSlots({ response: HYMN }), hymnsShipped)).toEqual([
      { step: "hymns", message: "No Opening hymn", action: "Choose one" },
      { step: "hymns", message: "No Closing hymn", action: "Choose one" },
    ]);
    expect(stillNeeded(all, hymnsShipped)).toEqual([]);
    expect(stillNeeded(filled, READINGS)).toEqual([]); // before 3b: no hymn rows
    expect(stillNeeded(filled, hymnsShipped).some((item) => item.step === "liturgy")).toBe(false);
  });

  it("counts the liturgy's enabled cards with text and lists the empty ones and a missing title (slice 4b)", () => {
    const d = testDraft(); // the Benediction follows the church default: 1 of 7
    expect(stepStatus(d, "liturgy")).toEqual({ kind: "incomplete", done: 1, total: 7 });
    const allOff = withLiturgy({
      cards: Object.fromEntries(
        Object.entries(d.liturgy.cards).map(([key, card]) => [key, { ...card, enabled: false }]),
      ) as DraftV1["liturgy"]["cards"],
    });
    expect(stepStatus(allOff, "liturgy")).toEqual({ kind: "complete" }); // every card off
    const rows = stillNeeded(withCard("assurance", { enabled: false })).filter((item) => item.step === "liturgy");
    expect(rows).toEqual([
      { step: "liturgy", message: "Call to Worship is empty", action: "Write or generate it", href: "/builder/liturgy#card-call_to_worship" },
      { step: "liturgy", message: "Opening Prayer is empty", action: "Write or generate it", href: "/builder/liturgy#card-opening_prayer" },
      {
        step: "liturgy",
        message: "Prayer of Confession is empty",
        action: "Write or generate it",
        href: "/builder/liturgy#card-prayer_of_confession",
      },
      {
        step: "liturgy",
        message: "Prayer for Illumination is empty",
        action: "Write or generate it",
        href: "/builder/liturgy#card-prayer_for_illumination",
      },
      { step: "liturgy", message: "Offertory Prayer is empty", action: "Write or generate it", href: "/builder/liturgy#card-offertory_prayer" },
      { step: "liturgy", message: "No sermon title", action: "Add one" },
    ]);
    const titled = withLiturgy({ sermon_title: "Living Water" });
    expect(stillNeeded(titled).some((item) => item.message === "No sermon title")).toBe(false);
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
import { installFakeApi } from "@/test/fake-api";
```

**with:**

```tsx
import { addCustomElement, editCardText } from "@/lib/liturgy/cards";
import { installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
  me,
```

**with:**

```tsx
  liturgyConfig,
  me,
  sectionResult,
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
function renderBuilder(page: ReactElement, path: string, lookup = lectionaryRoute()) {
```

**with:**

```tsx
function renderBuilder(page: ReactElement, path: string, lookup = lectionaryRoute(), routes: Record<string, FakeHandler> = {}) {
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
    "GET /hymns": hymnListRoute(),
  });
```

**with:**

```tsx
    "GET /hymns": hymnListRoute(),
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
        "3 Liturgy Soon",
```

**with:**

```tsx
        "3 Liturgy 1 of 7", // shipped in 4b: the Benediction follows the church default
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
      const card = screen.getByRole("region", { name: label });
```

**with:**

```tsx
      const card = await screen.findByRole("region", { name: label }); // Liturgy's shows once its config loads
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
        expect(within(card).getByText("Choose an opening, response and closing hymn.")).toBeInTheDocument();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
```

**with:**

```tsx
        expect(within(card).getByText("Choose an opening, response and closing hymn.")).toBeInTheDocument();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
      } else if (number === 3) {
        // Liturgy is the real step from slice 4b.
        expect(await within(card).findByRole("textbox", { name: "Sermon title" })).toBeInTheDocument();
        expect(within(card).queryByRole("heading", { name: "Available soon" })).toBeNull();
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
        ]);
        const links = within(needed).getAllByRole("link").map((link) => link.getAttribute("href"));
        expect(links).toEqual(["/builder/readings", "/builder/readings", "/builder/hymns", "/builder/hymns", "/builder/hymns"]);
```

**with:**

```tsx
          "Call to Worship is empty — Write or generate it",
          "Opening Prayer is empty — Write or generate it",
          "Prayer of Confession is empty — Write or generate it",
          "Assurance of Pardon is empty — Write or generate it",
          "Prayer for Illumination is empty — Write or generate it",
          "Offertory Prayer is empty — Write or generate it",
          "No sermon title — Add one",
        ]);
        const links = within(needed).getAllByRole("link").map((link) => link.getAttribute("href"));
        expect(links).toEqual([
          "/builder/readings",
          "/builder/readings",
          "/builder/hymns",
          "/builder/hymns",
          "/builder/hymns",
          "/builder/liturgy#card-call_to_worship",
          "/builder/liturgy#card-opening_prayer",
          "/builder/liturgy#card-prayer_of_confession",
          "/builder/liturgy#card-assurance",
          "/builder/liturgy#card-prayer_for_illumination",
          "/builder/liturgy#card-offertory_prayer",
          "/builder/liturgy",
        ]);
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
  it("shows the summary: the date and occasion, the readings, the hymns, Available soon for liturgy, and where the draft is kept", async () => {
```

**with:**

```tsx
  it("shows the summary: the date and occasion, the readings, the hymns, the liturgy, and where the draft is kept", async () => {
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
    expect(liturgy?.nextElementSibling).toHaveTextContent(/^Available soon$/);
```

**with:**

```tsx
    expect(liturgy?.nextElementSibling).toHaveTextContent(/^1 of 7 liturgy sections readyCommunion: YesNo custom elements$/);
```

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

```tsx
    expect(within(sheet).getByText("Opening · #403 Come, Thou Almighty King")).toBeInTheDocument();
  });
});

```

**with:**

```tsx
    expect(within(sheet).getByText("Opening · #403 Come, Thou Almighty King")).toBeInTheDocument();
  });
});

describe("the shell with Liturgy shipped (slice 4b)", () => {
  it("counts the liturgy, lists it in the summary with the sections being written, and in Still needed", async () => {
    let d = editCardText(testDraft(), "call_to_worship", "Come, let us worship.");
    d = addCustomElement(d, { label: "Anthem", text: "", insert_after: "sermon" }, "a");
    seed({ ...d, liturgy: { ...d.liturgy, include_communion: false, communion_origin: "user" } });
    let release!: () => void;
    const held = new Promise<void>((resolve) => (release = resolve));
    const view = renderBuilder(<LiturgyStepPage />, "/builder/liturgy", lectionaryRoute(), {
      "POST /liturgy/generate": async (req: RecordedRequest) => {
        await held;
        return { results: [sectionResult((req.body as { sections: ["opening_prayer"] }).sections[0], "Gracious God")] };
      },
    });
    const progress = await screen.findByRole("navigation", { name: "Steps" });
    expect(within(progress).getAllByRole("link")[2]).toHaveTextContent("3 Liturgy 2 of 7");
    const aside = screen.getByRole("complementary", { name: "Summary" });
    const block = within(aside).getByRole("link", { name: "Liturgy" }).closest("h3")?.nextElementSibling as HTMLElement;
    expect(within(block).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "2 of 7 liturgy sections ready",
      "Communion: No",
      "1 custom element",
    ]);
    expect(within(aside).getByRole("link", { name: "Liturgy" })).toHaveAttribute("href", "/builder/liturgy");
    expect(block).not.toHaveTextContent("Available soon");

    // While a section is written the first line says so, and the line goes when it is done.
    const opening = await screen.findByRole("region", { name: "Opening Prayer" });
    await view.user.click(within(opening).getByRole("button", { name: "Generate" }));
    await waitFor(() => expect(block).toHaveTextContent("2 of 7 liturgy sections ready · Writing 1 section…"));
    release();
    await waitFor(() => expect(within(block).getAllByRole("listitem")[0]).toHaveTextContent(/^3 of 7 liturgy sections ready$/));
    expect(within(progress).getAllByRole("link")[2]).toHaveTextContent("3 Liturgy 3 of 7");
    view.unmount();

    renderBuilder(<ReviewStepPage />, "/builder/review");
    const needed = await screen.findByRole("region", { name: "Still needed" });
    const liturgyRows = within(needed)
      .getAllByRole("listitem")
      .map((li) => li.textContent)
      .filter((text) => /empty|sermon/.test(text ?? ""));
    expect(liturgyRows).toEqual([
      "Prayer of Confession is empty — Write or generate it",
      "Assurance of Pardon is empty — Write or generate it",
      "Prayer for Illumination is empty — Write or generate it",
      "Offertory Prayer is empty — Write or generate it",
      "No sermon title — Add one",
    ]);
    const hrefs = within(needed)
      .getAllByRole("link", { name: "Write or generate it" })
      .map((link) => link.getAttribute("href"));
    expect(hrefs[0]).toBe("/builder/liturgy#card-prayer_of_confession");
    expect(within(needed).getAllByRole("link", { name: "Add one" }).at(-1)).toHaveAttribute("href", "/builder/liturgy");
  });
});

```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "^ FAIL|Tests ")
```

**Expected:**

```
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 6 ⎯⎯⎯⎯⎯⎯⎯
 FAIL  |unit| src/lib/draft/status.test.ts > steps (S steps.ts) > lists the four steps in order, ships Date & readings (2c), Hymns (3b) and Liturgy (4b), and reads a step from its path
 FAIL  |unit| src/lib/draft/status.test.ts > stepStatus (F §4.7) > shows Soon for unshipped steps and Not in archive for Review
 FAIL  |unit| src/lib/draft/status.test.ts > stillNeeded (S Review "Still needed") > counts the liturgy's enabled cards with text and lists the empty ones and a missing title (slice 4b)
 FAIL  |dom| src/components/builder/builder-shell.test.tsx > builder shell (F §4.7) > renders each step route inside the shell: progress, the step or its placeholder card, and the footer links
 FAIL  |dom| src/components/builder/builder-shell.test.tsx > builder shell (F §4.7) > shows the summary: the date and occasion, the readings, the hymns, the liturgy, and where the draft is kept
 FAIL  |dom| src/components/builder/builder-shell.test.tsx > the shell with Liturgy shipped (slice 4b) > counts the liturgy, lists it in the summary with the sections being written, and in Still needed
      Tests  6 failed | 17 passed (23)
```

- [ ] **Step 4 (agent): Ship the step**

**In `frontend/src/lib/draft/steps.ts`, replace:**

```ts
 * answer Q1, 2026-09-28); slice 2c ships "readings" and slice 3b "hymns".
 * Slice 4 adds "liturgy", 5a "review".
```

**with:**

```ts
 * answer Q1, 2026-09-28); slice 2c ships "readings", slice 3b "hymns" and
 * slice 4b "liturgy". 5a adds "review".
```

**In `frontend/src/lib/draft/steps.ts`, replace:**

```ts
export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns"]);
```

**with:**

```ts
export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy"]);
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
```

**with:**

```ts
import { DEFAULT_ENABLED, SECTION_LABELS } from "@/lib/liturgy/sections";
import { liturgyCounts } from "@/lib/liturgy/summary";
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
  const enabled = SECTION_KEYS.map((key) => draft.liturgy.cards[key]).filter((card) => card.enabled);
  return counted(enabled.filter((card) => card.text.trim() !== "").length, enabled.length);
```

**with:**

```ts
  // Liturgy: the enabled cards with text, from the count the summary shows too (slice 4b); all off is complete.
  const { ready, enabled } = liturgyCounts(draft);
  return counted(ready, enabled);
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
  action: string;
};
```

**with:**

```ts
  action: string;
  /** Where the link goes when not the step's own page: "/builder/liturgy#card-call_to_worship" (slice 4b). */
  href?: string;
};
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
 * F §4.7's wording). Slice 4 adds the liturgy's rows.
```

**with:**

```ts
 * F §4.7's wording), then one row per switched-on liturgy card with no text,
 * linking to that card, and "No sermon title" (4b, the wording 5a's Review
 * checklist reuses).
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
  }
  return items;
```

**with:**

```ts
  }
  if (shipped.has("liturgy")) {
    for (const key of SECTION_KEYS) {
      const card = draft.liturgy.cards[key];
      if (!card.enabled || card.text.trim() !== "") continue;
      items.push({
        step: "liturgy",
        message: `${SECTION_LABELS[key]} is empty`,
        action: "Write or generate it",
        href: `/builder/liturgy#card-${key}`,
      });
    }
    if (draft.liturgy.sermon_title.trim() === "") {
      items.push({ step: "liturgy", message: "No sermon title", action: "Add one" });
    }
  }
  return items;
```

**In `frontend/src/components/builder/still-needed.tsx`, replace:**

```tsx
            <Link href={stepById(item.step).href} className="font-medium underline underline-offset-4">
```

**with:**

```tsx
            <Link href={item.href ?? stepById(item.step).href} className="font-medium underline underline-offset-4">
```

**Create `frontend/src/components/builder/liturgy/liturgy-summary-block.tsx`:**

```tsx
"use client";

import { useDraft } from "@/lib/draft/context";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { liturgyCounts } from "@/lib/liturgy/summary";

/**
 * The summary's Liturgy block (slice 4 spec, "Builder shell"; F §4.7): "{ready}
 * of {enabled} liturgy sections ready" (or "All liturgy sections switched
 * off"), with " · Writing n sections…" while the generation provider has runs;
 * "Communion: Yes/No"; and the custom-element count. It reads the draft and
 * the runs only, so the shell never fetches anything for it.
 */
export function LiturgySummaryBlock() {
  const { draft } = useDraft();
  const { runs } = useLiturgyGeneration();
  const counts = liturgyCounts(draft);
  const writing = Object.keys(runs).length;
  const ready =
    counts.enabled === 0 ? "All liturgy sections switched off" : `${counts.ready} of ${counts.enabled} liturgy sections ready`;
  const custom =
    counts.customCount === 0
      ? "No custom elements"
      : counts.customCount === 1
        ? "1 custom element"
        : `${counts.customCount} custom elements`;
  return (
    <ul className="grid gap-1">
      <li className="text-foreground">
        {ready}
        {writing > 0 ? ` · Writing ${writing} ${writing === 1 ? "section" : "sections"}…` : null}
      </li>
      <li>Communion: {counts.communion ? "Yes" : "No"}</li>
      <li>{custom}</li>
    </ul>
  );
}
```

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

```tsx

import { SummaryHymns } from "./summary-hymns";
```

**with:**

```tsx

import { LiturgySummaryBlock } from "./liturgy/liturgy-summary-block";
import { SummaryHymns } from "./summary-hymns";
```

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

```tsx
 * hymns once "hymns" ships (slice 3b); slice 4 replaces the Liturgy block, and
 * 5a wires the archive half of the status line.
```

**with:**

```tsx
 * hymns once "hymns" ships (slice 3b), the liturgy counts once "liturgy" ships
 * (slice 4b); 5a wires the archive half of the status line.
```

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

```tsx
  const hymnsShipped = shipped.has("hymns");
  const lines = cleanScriptures(draft);
```

**with:**

```tsx
  const hymnsShipped = shipped.has("hymns");
  const liturgyShipped = shipped.has("liturgy");
  const lines = cleanScriptures(draft);
```

**In `frontend/src/components/builder/summary-panel.tsx`, replace:**

```tsx
      <Block title="Liturgy" step="liturgy" onNavigate={onNavigate}>
        <Soon />
      </Block>
```

**with:**

```tsx
      <Block title="Liturgy" step="liturgy" onNavigate={onNavigate}>
        {liturgyShipped ? <LiturgySummaryBlock /> : <Soon />}
      </Block>
```

**In `frontend/src/components/builder/step-placeholder.tsx`, replace:**

```tsx
 * answer Q1, 2026-09-28), and Hymns used it until slice 3b. Slices 4 and 5a
 * replace their steps' use, and 5a deletes this component. No link to the old
 * app (owner answer Q2).
```

**with:**

```tsx
 * answer Q1, 2026-09-28), Hymns until slice 3b and Liturgy until slice 4b.
 * Only Review uses it now; 5a replaces that use and deletes this component.
 * No link to the old app (owner answer Q2).
```

**In `frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx`, replace:**

```tsx
import { StepPlaceholder } from "@/components/builder/step-placeholder";

/** Step: Liturgy. Slice 4 replaces the placeholder. */
export default function LiturgyStepPage() {
  return <StepPlaceholder step="liturgy" />;
```

**with:**

```tsx
import { LiturgyStep } from "@/components/builder/liturgy/liturgy-step";

/** Step: Liturgy (slice 4b). */
export default function LiturgyStepPage() {
  return <LiturgyStep />;
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
    <div className="grid gap-6">
      <h2 className="text-lg font-semibold">Liturgy</h2>
```

**with:**

```tsx
    <section aria-labelledby="liturgy-step-title" className="grid gap-6">
      <h2 id="liturgy-step-title" className="text-lg font-semibold">
        Liturgy
      </h2>
```

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

```tsx
      />
    </div>
  );
```

**with:**

```tsx
      />
    </section>
  );
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft src/components/builder 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  16 passed (16)`, `      Tests  189 passed (189)`; the suite ` Test Files  75 passed (75)`, `      Tests  517 passed (517)`; `typecheck 0` and `lint 0`; ` M` for the nine modified files and `??` for `liturgy-summary-block.tsx`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/liturgy-summary-block.tsx frontend/src/lib/draft/steps.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/components/builder/still-needed.tsx frontend/src/components/builder/summary-panel.tsx frontend/src/components/builder/step-placeholder.tsx 'frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx' frontend/src/components/builder/liturgy/liturgy-step.tsx frontend/src/components/builder/builder-shell.test.tsx
git commit -m "Builder: the Liturgy step ships in the step bar, Still needed and the summary (S Builder shell; F §4.7; AC16)" -m "SHIPPED_STEPS gains liturgy: the step bar shows ready of enabled sections
(from liturgyCounts), /builder/liturgy renders the step, Review lists each
empty switched-on card (linking to its card) and a missing sermon title,
and the summary's Liturgy block shows the sections ready, Writing n
sections while the AI runs, communion and the custom elements. Only
Review keeps Available soon.
Frontend 515 -> 517 tests in 75 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 10 files changed.

### Task 12: Docs: the "(4b plan)" notes in S, two F amendment rows and the §1.8 timeouts, the slice 4 checklist and its heading pin (owner answers 1, 2, 4; S Manual checklist; F Amendments, §1.8, §4.7; clarifications 1-31)

S and F are what 5a, 6a and the reviewer slice will read, so they say what 4b built. S gains three inline notes (the keyboard, owner answer 3; the 100-second timeout, owner answer 2, in two places) and a closing section "Notes from the slice 4b plan (2026-09-30)", as 4a added its own. F gains two amendment rows (§1.8: the 100 000 ms client timeout, which the reviewer's routes reuse; §4.6/§4.7: what counts as unsaved work, the default benediction, and Liturgy shipping), the timeouts in §1.8's table, and a §4.7 note. `docs/manual-verification.md` gains "## Slice 4" (S's checks, check 10 for "New service" and check 11 for a long section, and "(owner, after 4b)" on the items the guided check covers; S's check 2 says 6 sections, which with a typed Call to Worship and the Benediction's default is 5), and `backend/tests/test_slice1_docs.py`, which pins the file's last four `##` headings, pins the last five. No code changes.

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`
- Test: none new; `backend/tests/test_ops_workflows.py`, `test_slice1_docs.py` and `test_docs.py` must still pass (89).

**Interfaces:**
- Consumes: the clarifications above and the code of T1-T11.
- Produces: S and F as later slices read them; the checklist T14 runs from.

Counts after this task: frontend **517 passed in 75 files**; backend **1183 passed, 11 skipped**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "4b plan" docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md
grep -c "^## Slice 4$" docs/manual-verification.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); `0` (grep exits 1); `89 passed in <t>s`.

- [ ] **Step 2 (agent): Apply the S, F, checklist and docs-test edits**

**In `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, replace:**

```markdown
- Below `md`, while a textarea has focus, the sticky `StepFooter` hides, so the iOS keyboard does not stack on it. If slice 2's footer doesn't already do this, this slice adds it through a `useKeyboardOpen()` hook based on `visualViewport`.
```

**with:**

```markdown
- Below `md`, while a textarea has focus, the sticky `StepFooter` hides, so the iOS keyboard does not stack on it. If slice 2's footer doesn't already do this, this slice adds it through a `useKeyboardOpen()` hook based on `visualViewport`. (4b plan, owner answer 3: slice 2b's `StepFooter` already does this with `useKeyboardOpen()`, which watches focus rather than `visualViewport`; 4b adds only a test on this step.)
```

**In `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, replace:**

```markdown
| `timeout` (client, 90 s) | "This is taking too long. Try again." | Try again |
```

**with:**

```markdown
| `timeout` (client, 90 s; 4b plan: 100 s, owner answer 2) | "This is taking too long. Try again." | Try again |
```

**In `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, replace:**

```markdown
- Client timeouts: `/liturgy/config` uses the default 20 s. `/liturgy/generate` uses 90 s (F §1.8), so `TIMEOUTS.liturgyGenerate = 90_000`.
```

**with:**

```markdown
- Client timeouts: `/liturgy/config` uses the default 20 s. `/liturgy/generate` uses 90 s (F §1.8), so `TIMEOUTS.liturgyGenerate = 90_000`. (4b plan, owner answer 2 of 2026-09-30: 100 s. The client's timer starts after it has the sign-in token, so the 15 s above 4a's 85 s worst case cover the server's sign-in key fetch (at most 5 s), network latency and the proxy; the client keeps per-route timeouts in `lib/api/timeouts.ts`'s `ENDPOINT_TIMEOUTS`, so the row is `"POST /liturgy/generate": 100_000`; F §1.8 is amended, and the reviewer's routes reuse the value.)
```

**In `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, replace:**

```markdown
- **Risk 3's query** lists only an 8-character prefix of each church id: `select left(id::text, 8) as church, settings->'liturgy_prompts' as prompts from churches where settings->'liturgy_prompts' is not null and deleted_at is null`.

```

**with:**

```markdown
- **Risk 3's query** lists only an 8-character prefix of each church id: `select left(id::text, 8) as church, settings->'liturgy_prompts' as prompts from churches where settings->'liturgy_prompts' is not null and deleted_at is null`.

## Notes from the slice 4b plan (2026-09-30)

`docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md` builds the frontend half. Where it reads this spec more precisely, or the code and F win, it says so here (its clarifications give the reasons); the owner's answers of 2026-09-30 are its owner answers 1-4.

- **Unsaved work** (owner answer 1; Draft store integration, Risks 4): everything that ends up in the service counts, so "New service" asks and the mount-time roll-forward keeps the date after a card's text, a section switched away from its default, communion set by the user, a sermon title or a custom element; transient state (runs, errors, Undo lines) is never in the draft, and a Benediction still following the church default does not count. Text or a title that is blank after trimming counts as nothing. After a save (5a) the fingerprint decides: a switch on an empty card changes nothing that is saved, and Risks item 4 stands.
- **The default benediction** (Benediction and the church default): `freshDraft` fills the card from the profile's `default_benediction` ("Halverson" when missing); the draft store runs `applyLiturgyDefaults` on load, on every change and on replace, and on a profile refetch as an automatic change (stamped just after the current draft, like 2c's lectionary fill), so it never outranks another tab's edit. The communion rule moved into `lib/liturgy/defaults.ts`; `date-effects.ts` calls it.
- **Names and files** (Frontend changes): components are kebab-case files under `src/components/builder/liturgy/` (`liturgy-step.tsx`, `section-card.tsx`, `ai-bar.tsx`, `outline-landmark.tsx`, `sermon-title-field.tsx`, `communion-card.tsx`, `custom-element-card.tsx`, `add-custom-element-dialog.tsx`, `liturgy-summary-block.tsx`), as 3b's are; `useChurchDefault` is `restoreChurchDefault` (React's lint reads a `use…` name as a hook); the labels and default switches live in `lib/liturgy/sections.ts`, pinned to `shared/liturgy_sections.json`; `generateSection` takes the built body; the provider exposes `runs`, `errors`, `undo`, `bulk`, `generate(keys, {aiAvailable, bulk})`, `cancel`, `cancelBulk`, `dismissError`, `setUndo`, `clearUndo`, `applyUndo`, and fetches nothing until asked. `components/ui/dialog.tsx` is rebuilt from the upstream shadcn source (the registry is blocked), as 2b, 2c and 3b did.
- **Requests** (`request.ts`): a hymn id that is not a UUID goes as `null` (the API validates it as a UUID and would reject the whole request).
- **Errors** (Per-card error messages): a cancel, a 401 and a lost church show nothing on the card (the app's handling acts); the 404's link reads "Go to Hymns"; while a retryable error shows, its "Try again" stands in for the card's button. A 429 stops the queue at once: the answer is handled before the next queued section starts. The wait counts from the moment the 429 came, so leaving the step does not restart it, and "Generate empty sections" waits too. A bulk run's errors are announced politely, not as one alert per card.
- **Runs and the service** (Generate and Regenerate step 6): the card is captured when the member asks (the click, or "Replace text"), and the stale rule also runs just before a queued section is sent, so text that became the member's while it waited (Undo, another tab) is never sent or replaced; a card's Undo line is hidden while it runs. "New service" (a new `created_at`) cancels every run silently and clears the cards' errors and Undo lines; a bulk run then ends with one toast, "The service changed, so the AI drafts were discarded.", and no "Wrote…" toast. A result racing that change still meets the per-result rule.
- **Wording**: "Writing k of n…" counts the sections finished plus one; "Wrote 1 section." and the summary's "Writing 1 section…" are singular for one; a bulk run cancelled whole ends with no toast, and cancelled cards are not counted in "Wrote k of n sections."; the "Replaced with a new AI draft." line shows only when text was replaced. The step opens with the heading "Liturgy"; landmark rows read "First Hymn · {title}" (no number) and "First Reading · {reference} auto"; a custom element with a blank label is titled "Custom element".
- **Still needed** (Builder shell): each empty switched-on card links to `/builder/liturgy#card-{key}`, the sermon row to `/builder/liturgy`; the card rows come first.
- **Tests** (Testing → Frontend): the dom cases are in `components/builder/liturgy/liturgy-step.test.tsx` and `builder-shell.test.tsx`; `generation.test.tsx` holds the sermon-text cases; `sections.test.ts` pins the fresh-draft switches (S put that in `defaults.test.ts`).
- **Manual checklist**: appended as "## Slice 4"; the owner's guided phone check after the merge runs the items marked "(owner, after 4b)". Check 2's count is 5 (the Benediction has the default and the Call to Worship is typed), not 6.

```

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

```markdown
| §4.6, §4.7, §4.9 | *(2026-09-29, slice 3b plan)* `isPristine` also counts a chosen hymnal (owner answer 1), so "New service" asks after a hymn or a hymnal is chosen and the roll-forward keeps that draft's date; choosing the church's effective hymnal stores `null`. The Exclude switch and the AI's other ideas never count. Hymns ships (`SHIPPED_STEPS` holds "readings" and "hymns"): the step bar counts it, Review lists each empty slot, and the summary lists the three hymns. The generic long-list picker is `components/app/search-combobox.tsx` (slice 1's time-zone picker uses the Combobox directly), and the kit gains `switch`. | 3b |

```

**with:**

```markdown
| §4.6, §4.7, §4.9 | *(2026-09-29, slice 3b plan)* `isPristine` also counts a chosen hymnal (owner answer 1), so "New service" asks after a hymn or a hymnal is chosen and the roll-forward keeps that draft's date; choosing the church's effective hymnal stores `null`. The Exclude switch and the AI's other ideas never count. Hymns ships (`SHIPPED_STEPS` holds "readings" and "hymns"): the step bar counts it, Review lists each empty slot, and the summary lists the three hymns. The generic long-list picker is `components/app/search-combobox.tsx` (slice 1's time-zone picker uses the Combobox directly), and the kit gains `switch`. | 3b |
| §1.8 | *(2026-09-30, slice 4b plan, owner answer 2)* The client timeout for `POST /liturgy/generate` is 100 000 ms, not 90 000: a section answers within 85 s (4a's 80 s deadline plus a last connect), and the client's timer starts only after `getAccessToken()`, so the other 15 s cover the server's sign-in key fetch (at most 5 s, `JWKS_FETCH_TIMEOUT_S`), network latency and the proxy, not the client's own sign-in. The client keeps it in `lib/api/timeouts.ts`'s `ENDPOINT_TIMEOUTS`. The service reviewer's `POST /liturgy/review` and `/liturgy/revise` (the slice after 4b) reuse 100 000. | 4b |
| §4.6, §4.7 | *(2026-09-30, slice 4b plan, owner answer 1)* On the Liturgy step `isPristine` counts everything that ends up in the service: card text, a card switched away from its default, communion set by the user, the sermon title and custom elements; text or a title blank after trimming counts as nothing, and a Benediction following the church default never counts. A fresh draft's Benediction holds the church's `default_benediction`, and the draft store keeps untouched cards on the defaults (automatic changes, never outranking another tab's edit). Liturgy ships (`SHIPPED_STEPS` holds "readings", "hymns" and "liturgy"): the step bar counts it, Review lists each empty switched-on card and a missing sermon title, and the summary shows the liturgy counts. The kit gains `dialog`. | 4b |

```

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

```markdown
| `POST /liturgy/generate` (UI sends one section) | OpenAI (§2.8) + ≤ 15 s waiting for a concurrency slot | ~80 s | 90 000 |
| `POST /church/prayer-library/voice-profile-draft` (6a, PR #7; *amendment 2026-09-26*) | OpenAI inside a 75 s deadline passed to `complete(deadline=…)` | ~75 s | 90 000 |
| `POST /liturgy/review` (PR #8; *amendment 2026-09-26*) | code checks + OpenAI inside a 75 s deadline | ~75 s | 90 000 |
| `POST /liturgy/revise` (PR #8; *amendment 2026-09-26*) | OpenAI (§2.8), as `/liturgy/generate` for one section | ~80 s | 90 000 |
```

**with:**

```markdown
| `POST /liturgy/generate` (UI sends one section) | OpenAI (§2.8) + ≤ 15 s waiting for a concurrency slot | ~80 s | 90 000; *100 000 (2026-09-30, slice 4b plan, owner answer 2)* |
| `POST /church/prayer-library/voice-profile-draft` (6a, PR #7; *amendment 2026-09-26*) | OpenAI inside a 75 s deadline passed to `complete(deadline=…)` | ~75 s | 90 000 |
| `POST /liturgy/review` (PR #8; *amendment 2026-09-26*) | code checks + OpenAI inside a 75 s deadline | ~75 s | 90 000; *100 000, as `/liturgy/generate` (slice 4b plan)* |
| `POST /liturgy/revise` (PR #8; *amendment 2026-09-26*) | OpenAI (§2.8), as `/liturgy/generate` for one section | ~80 s | 90 000; *100 000, as `/liturgy/generate` (slice 4b plan)* |
```

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

```markdown
- **Slice 2 ships all four routes.** Steps 2-4 render an "Available soon — keep using the current app for this part" card inside the working shell until their slice fills them. *(2026-09-28, slice 2b plan: step 1 too, until slice 2c.)* *(2026-09-29, slice 2c plan: step 1 ships in 2c.)* *(2026-09-29, slice 3b plan: step 2 ships in 3b.)*
```

**with:**

```markdown
- **Slice 2 ships all four routes.** Steps 2-4 render an "Available soon — keep using the current app for this part" card inside the working shell until their slice fills them. *(2026-09-28, slice 2b plan: step 1 too, until slice 2c.)* *(2026-09-29, slice 2c plan: step 1 ships in 2c.)* *(2026-09-29, slice 3b plan: step 2 ships in 3b.)* *(2026-09-30, slice 4b plan: step 3 ships in 4b.)*
```

**In `docs/manual-verification.md`, replace:**

```markdown
- [ ] (owner, after 3b) **12.** After choosing a hymn or a hymnal, **New service** asks "Start a new service?". Turning Exclude on or off does not make it ask; Suggest fills empty slots, which does.

```

**with:**

```markdown
- [ ] (owner, after 3b) **12.** After choosing a hymn or a hymnal, **New service** asks "Start a new service?". Turning Exclude on or off does not make it ask; Suggest fills empty slots, which does.

## Slice 4

Run on the production URL https://worship-service-builder.vercel.app, at 375 px
(Chrome device mode, iPhone SE) and on desktop, and the Streamlit smoke on
https://liturgy-frozen.streamlit.app. These are the slice 4 spec's manual
checks (slice 4 spec → Manual checklist), with check 10 for "New service"
(owner answer 1, 2026-09-30) and check 11 for a long section (owner answer 2).
After the 4b merge the owner's guided check (owner answer 4: six short steps
on the phone, given one at a time, then a quick look on a computer) covers the
items marked "(owner, after 4b)", some of them in part; its result goes into
`docs/ops-runbook.md` → "Slice 4b record", which says what ran. The rest can
be run at any time and recorded the same way. The AI's words differ every
time, so record what the page shows, never an email address or a church id.

- [ ] (owner, after 4b) **1.** Open Liturgy on a fresh draft: the 8 cards in the order of worship, Prayers of the People off; Benediction "Halverson" with "Church default"; the landmark rows show the chosen hymns and readings.
- [ ] (owner, after 4b) **2.** Type a Call to Worship. Tap **Generate empty sections (5)**: the 5 empty switched-on sections fill within about a minute and one message says "Wrote 5 sections."; the Call to Worship is unchanged, character for character; the Benediction is untouched.
- [ ] (owner, after 4b) **3.** Regenerate the typed card: "Replace your text?" appears; **Replace text**, then **Undo** brings the typed text back.
- [ ] **4.** Start a bulk run, go to Hymns and back: the results are there. Cancel a run: the card is unchanged.
- [ ] **5.** Refresh mid-edit: the text is kept. Switch church and back: each church keeps its own liturgy.
- [ ] **6.** Communion is on for a first-Sunday date, off after changing the date, and stays as set after a toggle; **Use default** follows the date again. Its text shows under **Show communion text**.
- [ ] (owner, after 4b) **7.** Add, edit, move and remove (then **Undo**) a custom element. It shows right after its place.
- [ ] (owner, after 4b) **8.** At 375 px: no sideways scroll; the keyboard does not cover the focused text; the footer (Back, Next) hides while typing and comes back after; touch targets are at least 44 px. The Prayers of the People card's header fits: its switch, title and ⋯ on one line, and "Pastor's copy only" with the status chip (for example "Empty") on the line below. Switching a section off shows "Off — not in the service. Any text is kept." and switching it on shows the text again.
- [ ] **9.** Regression: sign in, switch church, open every shipped nav item; the Streamlit smoke check on https://liturgy-frozen.streamlit.app: load the church, load an archived service, open Settings (F §6.3).
- [ ] (owner, after 4b) **10.** **New service** asks "Start a new service?" after a card's text, a section switched on or off, a sermon title, a communion toggle or a custom element; on a fresh draft whose Benediction still shows the church default it does not ask.
- [ ] **11.** Switch on Prayers of the People and tap **Generate**: it fills (about 5 s in the 4a check; the page waits up to 100 s).

```

**In `backend/tests/test_slice1_docs.py`, replace:**

```python
    # Slices 2c and 3b append "## Slice 2" and "## Slice 3" after this section (their specs, Manual checks).
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-4:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3"]
```

**with:**

```python
    # Slices 2c, 3b and 4b append "## Slice 2", "## Slice 3" and "## Slice 4" after this section (their specs, Manual checks).
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-5:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4"]
```

- [ ] **Step 3 (agent): Check the result**

```bash
grep -c "4b plan" docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md
grep -c "slice 4b plan" docs/superpowers/specs/2026-09-25-migration-foundations-design.md
sed -n '/^## Slice 4$/,$p' docs/manual-verification.md | grep -cE "^- \[ \] "
grep -c "^- \[ \] (owner, after 4b) " docs/manual-verification.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git diff -U0 docs backend | grep '^+' | grep -v '^+++' | grep -c '—'
git diff --stat
```

**Expected:** `4`; `6`; `11`; `6`; `89 passed in <t>s`; `1183 passed, 11 skipped in <t>s`; `2` (the only em dashes on added lines are S's own copy "Off — not in the service. Any text is kept." in check 8 and F §4.7's existing "Available soon — keep using the current app for this part" on the line that gains a note; the new prose has none); ` 4 files changed, 53 insertions(+), 10 deletions(-)`.

- [ ] **Step 4 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -m "Docs: slice 4b notes in S and F, the 100 s timeout, and the slice 4 manual checklist (owner answers 1, 2, 4; F §1.8, §4.6, §4.7)" -m "The slice 4 spec gains its 4b notes (the keyboard footer already built,
the 100 s client timeout, and a closing section on what 4b built more
precisely: unsaved work, the default benediction, names and files,
requests, errors, wording, Still needed, tests and the checklist). F gains
two amendment rows and the timeouts in §1.8 (the reviewer's routes reuse
100 000 ms). docs/manual-verification.md gains \"## Slice 4\", and
test_slice1_docs.py pins its last five headings." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 4 files changed.

**Review checkpoint (T11-T12, batch D):** the shell shows Liturgy's status, rows and summary, and only Review keeps "Available soon"; every S note says "(4b plan)" or sits in the closing section and matches the code; F's rows match owner answers 1 and 2; the checklist reads as the owner will run it; `git show --stat HEAD` lists the four files only.

### Task 13: Whole-branch verification and the slice 4b pull request (owner's yes before the PR is opened and before it is marked ready) (S Testing "Frontend", AC11-AC17, AC20 client half; F §4.1, §4.3, §4.4, §4.8, §4.9, §4.10, §5.2, §5.4; owner answer 4; standing rules; clarifications 11, 19)

The whole branch is checked in one place before anyone reviews it: the frontend suite three times and twice more with the clock moved forward, types, lint, the production build and its routes, the backend suite, the generated API files (unchanged), the gates (client components, no link to the old app, no `apiFetch` in components, storage only through `lib/storage.ts`, no raw HTML, no date parsing in the step, `SHIPPED_STEPS` holding the three steps, only the planned Python change), the exact list of changed paths, and the exact list of commits against this plan. The branch is already on GitHub from the backup pushes, but no PR exists; on the owner's first yes the agent opens it as a **draft**, so CI runs. When CI is green, the agent reports and, on the owner's second yes, marks it ready. Merging is Task 14, with its own yes.

Below, `<scratch>` is the absolute path of the session's scratchpad directory, and `<N>` is the PR number Step 10 prints; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never run a bare `git push` or `--force`.

**Files:** none changed. A local or CI failure is fixed in its owning task's files (Step 14).

**Interfaces:**
- Consumes: everything from T1-T12, in particular each task's commit subject (Step 8 reads them from this plan between `### Task 1:` and `### Task 13:`), the cumulative counts (Baselines and counts), `SHIPPED_STEPS` (T11), and CI (`.github/workflows/ci.yml`, unchanged: `backend`, `backend-postgres`, `frontend` with lint, typecheck, `API types match the OpenAPI snapshot (F §5.4)`, test and build).
- Produces: PR `<N>` (`claude/slice-2-plan-4q33le` → `main`), titled `Slice 4b: the Liturgy step`, not a draft after Step 13, CI green on the branch head, its body holding the line `Tests: frontend 442 → 517 in 64 → 75 files; backend 1183 → 1183 passed, 11 → 11 skipped` and ending with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and the session link. Later user: T14.

- [ ] **Step 1 (agent): Bring the branch up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
git log --oneline --grep '^Plan: slice 4b liturgy step' -1
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected,** in order: nothing (or `?? .claude/`); the fetch prints nothing or only updated refs; `0`; `4dfed3b Merge pull request #31 from bbrown62450/claude/slice-2-plan-4q33le` (or a later merge the owner made); `<sha> Plan: slice 4b liturgy step (S slice 4; owner answers 2026-09-30)`; `0` (every commit was backed up).
- If the first count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 13)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"`. On a conflict, run `git merge --abort`, stop and tell the owner which files conflict. Without one, continue: Steps 2-8 run on the merged tree, and any new tests the merge brought change the totals by exactly those (name them in the Step 9 message).
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
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** three times ` Test Files  75 passed (75)` and `      Tests  517 passed (517)` (baseline 442 in 64; after T1-T11: 446, 455, 464, 468, 471, 476, 479, 490, 506, 515, 517) and no `FAIL`; then `clock +8 days` and `clock +400 days`, each followed by the same two lines and no `FAIL`; `0`; `typecheck 0` and `lint 0`. Any other number: find the task whose count drifted. A run that fails even once is a failure (Step 14): make the test deterministic (fake only `Date`, set to `DRAFT_NOW`; await the UI with `findBy`/`waitFor`) rather than retrying it.

- [ ] **Step 3 (agent): Run the backend suite and the Postgres marker count**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
```

**Expected:** `1183 passed, 11 skipped in <t>s` (T12 edits one assertion); `11 skipped, 1183 deselected in <t>s`.

- [ ] **Step 4 (agent): Build the frontend with CI's placeholder environment**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder")
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

**Expected:** `✓ Compiled successfully in <t>s`, the route table's five builder lines (`├ ○ /builder`, `├ ○ /builder/hymns`, `├ ○ /builder/liturgy`, `├ ○ /builder/readings`, `├ ○ /builder/review`) and no `Error` line; then exactly:

```
/ /_global-error /_not-found /auth/callback /builder /builder/hymns /builder/liturgy /builder/readings /builder/review /favicon.ico /join /login /welcome
```

(4b adds no route.) The build must run in the real checkout: Turbopack refuses a symlinked `node_modules`. If it fails only with `Failed to fetch` for a Geist font (no network), say so in the Step 9 message and rely on CI's `frontend` job.

- [ ] **Step 5 (agent): Check the generated API files did not change**

```bash
(cd frontend && npm run gen:api >/dev/null) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
git diff --name-only origin/main...HEAD -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | wc -l
.venv/bin/python -m pytest -q backend/tests/test_openapi_contract.py 2>&1 | tail -1
git status --short
```

**Expected:** `schema diff exit 0`; `0` (4b changes no API: 4a generated every type it uses); `<n> passed in <t>s`; nothing (or `?? .claude/`).

- [ ] **Step 6 (agent): Run the gates**

```bash
find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) -exec sh -c 'head -1 "$1" | grep -qx "\"use client\";" || echo "not a client component: $1"' _ {} \; ; echo "client components checked: $(find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) | wc -l)"
grep -rniE "streamlit|liturgy-frozen" frontend/src --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "old app grep exit $?"
grep -rn "apiFetch" frontend/src/components frontend/src/app --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "apiFetch in UI grep exit $?"
grep -rnE "window\.(local|session)Storage|(local|session)Storage\.(getItem|setItem|removeItem|key|clear)" frontend/src --include=*.ts --include=*.tsx | grep -vE "^frontend/src/lib/storage\.ts:|\.test\.tsx?:|^frontend/src/test/"; echo "storage grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
grep -rn "new Date(" frontend/src/components/builder/liturgy frontend/src/lib/liturgy --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "date grep exit $?"
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
grep -rln "Available soon" frontend/src --include=*.tsx | grep -v "\.test\.tsx$"
grep -n '"POST /liturgy/generate"' frontend/src/lib/api/timeouts.ts
git diff --name-only origin/main...HEAD -- '*.py' backend/requirements.txt requirements-dev.txt backend/migrations .github frontend/package.json frontend/package-lock.json docs/ops-runbook.md
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected,** in order:
- `client components checked: 10` with no "not a client component" line before it (F §4.1; 4b replaces the liturgy page's body);
- `old app grep exit 1`; `apiFetch in UI grep exit 1` (F §4.4: `generateSection` lives in `lib/queries`); `storage grep exit 1` (F §4.3; 4b adds no storage key); `raw html grep exit 1`; `date grep exit 1` (F §4.10: the step and `lib/liturgy` never parse a date; the provider stamps with `Date.now()`);
- `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy"]);`;
- `frontend/src/components/builder/step-placeholder.tsx` and `frontend/src/components/builder/summary-panel.tsx` (Review's card and the summary's unshipped-block fallback);
- one line ending `"POST /liturgy/generate": 100_000,` (owner answer 2; clarification 11);
- exactly one line: `backend/tests/test_slice1_docs.py` (T12; no requirement, migration, workflow, package or runbook change);
- only `trailer check done`.

Any other output: stop, find the owning task (Step 14) and fix it there. A grep hit may be a false positive (a comment): read the line, and if it is harmless, say why in the Step 9 message rather than bending the code to silence it.

- [ ] **Step 7 (agent): Check the exact list of changed paths**

```bash
LC_ALL=C sort > "<scratch>/slice4b-expected-paths.txt" <<'EOF'
backend/tests/test_slice1_docs.py
docs/manual-verification.md
docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md
frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx
frontend/src/components/builder/builder-shell.test.tsx
frontend/src/components/builder/builder-shell.tsx
frontend/src/components/builder/liturgy/add-custom-element-dialog.tsx
frontend/src/components/builder/liturgy/ai-bar.tsx
frontend/src/components/builder/liturgy/communion-card.tsx
frontend/src/components/builder/liturgy/custom-element-card.tsx
frontend/src/components/builder/liturgy/liturgy-step.test.tsx
frontend/src/components/builder/liturgy/liturgy-step.tsx
frontend/src/components/builder/liturgy/liturgy-summary-block.tsx
frontend/src/components/builder/liturgy/outline-landmark.tsx
frontend/src/components/builder/liturgy/section-card.tsx
frontend/src/components/builder/liturgy/sermon-title-field.tsx
frontend/src/components/builder/liturgy/use-still-working.ts
frontend/src/components/builder/step-placeholder.tsx
frontend/src/components/builder/still-needed.tsx
frontend/src/components/builder/summary-panel.tsx
frontend/src/components/ui/dialog.tsx
frontend/src/lib/api/timeouts.ts
frontend/src/lib/api/types.ts
frontend/src/lib/draft/context.test.tsx
frontend/src/lib/draft/context.tsx
frontend/src/lib/draft/date-effects.ts
frontend/src/lib/draft/fingerprint.test.ts
frontend/src/lib/draft/mapping.test.ts
frontend/src/lib/draft/schema.test.ts
frontend/src/lib/draft/schema.ts
frontend/src/lib/draft/status.test.ts
frontend/src/lib/draft/status.ts
frontend/src/lib/draft/steps.ts
frontend/src/lib/draft/store.test.ts
frontend/src/lib/draft/store.ts
frontend/src/lib/liturgy/cards.test.ts
frontend/src/lib/liturgy/cards.ts
frontend/src/lib/liturgy/defaults.test.ts
frontend/src/lib/liturgy/defaults.ts
frontend/src/lib/liturgy/errors.test.ts
frontend/src/lib/liturgy/errors.ts
frontend/src/lib/liturgy/generation.test.tsx
frontend/src/lib/liturgy/generation.tsx
frontend/src/lib/liturgy/queue.test.ts
frontend/src/lib/liturgy/queue.ts
frontend/src/lib/liturgy/request.test.ts
frontend/src/lib/liturgy/request.ts
frontend/src/lib/liturgy/sections.test.ts
frontend/src/lib/liturgy/sections.ts
frontend/src/lib/liturgy/summary.test.ts
frontend/src/lib/liturgy/summary.ts
frontend/src/lib/queries/client.test.ts
frontend/src/lib/queries/client.ts
frontend/src/lib/queries/liturgy.test.tsx
frontend/src/lib/queries/liturgy.ts
frontend/src/lib/queries/passages.ts
frontend/src/lib/use-autosize.test.tsx
frontend/src/lib/use-autosize.ts
frontend/src/test/fixtures/index.ts
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice4b-actual-paths.txt"
wc -l < "<scratch>/slice4b-expected-paths.txt"
wc -l < "<scratch>/slice4b-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice4b-expected-paths.txt" "<scratch>/slice4b-actual-paths.txt"
git diff --name-status --no-renames origin/main...HEAD | cut -c1 | sort | uniq -c
```

**Expected:** `61`; `61`; `comm` prints nothing; then `     33 A` and `     28 M`. These are the File Structure's paths: 33 created (the plan and 32 frontend files) and 28 modified (24 frontend files, 1 backend test and 3 docs: the two specs and the checklist). An indented `comm` line (changed, not listed) means a task touched a file its **Files:** does not name: find it with `git log --format='%h %s' origin/main..HEAD -- '<path>'`; anything under `backend/` other than T12's test, `frontend/src/lib/api/openapi.json`, `schema.d.ts`, `package*.json` or `.github/` is a stop. An unindented line means a task's commit is missing.

- [ ] **Step 8 (agent): Check the exact list of commits against this plan**

```bash
.venv/bin/python - docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md > "<scratch>/slice4b-plan-subjects.txt" <<'EOF'
import pathlib, re, sys
text = "\n" + pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
lines = text.split("\n### Task 1:", 1)[1].split("\n### Task 13:", 1)[0].splitlines()
for line in lines:
    m = re.match(r'\s*git commit -m "((?:[^"\\]|\\.)*)"', line)
    if m:
        print(re.sub(r"\\(.)", r"\1", m.group(1)))
EOF
PLAN=$(git log --format=%H --grep '^Plan: slice 4b liturgy step' -1)
git log --reverse --no-merges --format=%s "$PLAN"..HEAD > "<scratch>/slice4b-branch-subjects.txt"
wc -l < "<scratch>/slice4b-plan-subjects.txt"
diff "<scratch>/slice4b-plan-subjects.txt" "<scratch>/slice4b-branch-subjects.txt"; echo "commit list diff exit $?"
git log --reverse --format='%h %s' origin/main..HEAD
```

**Expected:** `12` (one commit for each of T1-T12); `commit list diff exit 0` with no output before it; the branch's commits oldest first: the plan's own commits (`WIP plan: slice 4b` several times, then `Plan: slice 4b liturgy step (S slice 4; owner answers 2026-09-30)`), then the twelve task commits from `<sha> Draft: liturgy that prints is unsaved work; a card following the church default is not (owner answer 1)` to `<sha> Docs: slice 4b notes in S and F, the 100 s timeout, and the slice 4 manual checklist (owner answers 1, 2, 4; F §1.8, §4.6, §4.7)` (plus a Step 1 merge, if any). A `diff` line is a failure unless it is a `>` line `Fix: … (Task <n> review)` (a review fix), `Fix: … (Task <n>, slice 4b final verification)` (Step 14) or `Plan: …` (a plan correction the controller committed), each named in the Step 9 message.

- [ ] **Step 9 (agent → OWNER): Ask for the go-ahead to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
git rev-list --count origin/main..HEAD
```

**Expected:** one `✓ Logged in to github.com account <login> (keyring)` line; `[]` (no open PR from this branch; PR #31 is merged); the branch's commit count. If `gh` is not logged in, ask the owner to run `gh auth login`. If an open PR exists, stop and ask.

Send the owner exactly this, with `<count>` filled in, and wait for a clear yes:

> Slice 4b is verified on this machine: 517 frontend tests in 75 files pass three runs in a row and with the clock moved 8 and 400 days ahead (442 in 64 before); typecheck, lint and the production build are clean; the backend is unchanged at 1183 passed, 11 skipped; the API types did not change; the checks are clean (every page is a client component, no link to the old app, the screens use the query hooks, no new browser storage, Date & readings, Hymns and Liturgy are the steps switched on, the AI waits up to 100 seconds); the changed files (61) and commits (<count>) are as planned, and every commit is already backed up on the branch. May I open the pull request as a **draft** titled "Slice 4b: the Liturgy step", so the checks run? I will come back with the results and ask again before marking it ready. Merging stays with you (Task 14).

Add one line per note from Steps 1-8 (a merge from `main`, a skipped font download, a `Fix:` commit, how the dialog was made). A no leaves the branch as it is.

- [ ] **Step 10 (agent, on the owner's yes): Write the PR body and open the draft PR**

```bash
cat > "<scratch>/slice4b-pr-body.md" <<'EOF'
PR 4b of slice 4: the Liturgy step. After it merges, a signed-in member builds the order of worship on step 3 of the Service Builder. Spec: docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md (4b). Plan: docs/superpowers/plans/2026-09-30-slice-4b-liturgy-step.md. No migration and no API change; 4a's routes are used as they are.

The step
- The sermon title, then the order of worship in the order the Word files print it: a card for each of the 8 sections (switch, status, typed or AI text, the section's hint), and rows for the hymns, readings, sermon title and creed.
- Generate on an empty card, Regenerate on one with text (it asks before replacing your own or a saved service's text, and offers Undo), and Generate empty sections for every switched-on empty card, 3 at a time, with Cancel. Errors show on the card and are never saved. Without an AI key nothing is sent and empty cards say so.
- The Benediction follows the church's default until it is changed; communion follows the first Sunday of the month until it is toggled; custom elements show in their printed place, with Undo on Remove (no AI for them, F D17).
- The step bar counts the liturgy, Review lists each empty section and a missing sermon title, and the summary shows the sections ready, communion and custom elements. Only Review keeps "Available soon".

Owner answers (2026-09-30): what counts as unsaved work (1); the AI waits up to 100 seconds, recorded in F §1.8 (2); the footer hides while typing on a phone (3; already built in 2b, now tested here); a guided phone check after the merge (4). @@DIALOG_LINE@@

Tests: frontend 442 → 517 in 64 → 75 files; backend 1183 → 1183 passed, 11 → 11 skipped

After merge (Task 14): a guided check on the owner's phone (six steps) and a quick look on a computer, then a short "Slice 4b record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
EOF
```

Replace `@@DIALOG_LINE@@` with `The dialog is generated from the base-nova registry.` or `The dialog is rebuilt from the upstream shadcn source (base-nova, pinned commit), because the build container cannot reach the registry (plan clarification 19).` (T7's commit body says which). Then:

```bash
grep -c '@@' "<scratch>/slice4b-pr-body.md"
grep -cx 'Tests: frontend 442 → 517 in 64 → 75 files; backend 1183 → 1183 passed, 11 → 11 skipped' "<scratch>/slice4b-pr-body.md"
git fetch origin && test "$(git rev-list --count HEAD..origin/main)" = 0 && test "$(git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD)" = 0 && echo "branch is current and backed up"
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 4b: the Liturgy step" \
  --body-file "<scratch>/slice4b-pr-body.md"
gh pr view claude/slice-2-plan-4q33le -R bbrown62450/church --json number,isDraft,headRefOid,url --jq '"#\(.number) draft=\(.isDraft) \(.headRefOid) \(.url)"'
git rev-parse HEAD
```

**Expected:** `0` (grep exits 1); `1`; `branch is current and backed up` (if not: ask the controller for a backup push, or go back to Step 1 if `main` moved); the PR URL; `#<N> draft=true <sha> https://github.com/bbrown62450/church/pull/<N>` with the same `<sha>` as `git rev-parse HEAD`.

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

**Expected:** `run <id>`; `backend: success`, `backend-postgres: success`, `frontend: success`; frontend `Test Files  75 passed (75)`, `Tests  517 passed (517)`, `✓ Compiled successfully` and the five `/builder` route lines; backend `1183 passed, 11 skipped in …s`; backend-postgres `pg_smoke: OK` and `11 passed, 1183 deselected` (with the one warning the 4a run showed). If a required job failed on or after 2026-10-19, first check the runner image (`Image: ubuntu-24.04` expected; GitHub moves `ubuntu-latest` then) and report a setup failure on a new image to the owner before changing any 4b file.

- [ ] **Step 13 (agent → OWNER): Report CI and ask to mark the PR ready**

Send exactly this, with the values filled in, and wait for a clear yes:

> PR #<N> (<url>) is green (run <run id>): 517 frontend tests in 75 files, the build is fine; the backend is at 1183 passed, 11 skipped; the Postgres job is clean; the Vercel preview built. May I mark it ready for review? Merging stays with you (Task 14).

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
| `lib/liturgy/sections.test.ts`, `draft/status.test.ts` (`isPristine`), `draft/fingerprint.test.ts`, `draft/store.test.ts` (roll-forward) | T1 |
| `lib/liturgy/{cards,defaults,summary}.test.ts`, `draft/date-effects.ts` | T2 |
| `lib/liturgy/{request,errors,queue}.test.ts`, `lib/api/types.ts` | T3 |
| `queries/liturgy.test.tsx`, `queries/client.test.ts` (`reportAuthErrors`), `timeouts.ts`, `passages.ts`, the liturgy fixtures | T4 |
| `draft/store.test.ts` (defaults), `draft/context.test.tsx`, `mapping.test.ts`, `schema.test.ts` | T5 |
| `lib/liturgy/generation.test.tsx`, `builder-shell.tsx` (the provider) | T6 |
| `use-autosize.test.tsx`, `dialog.tsx` lint or types | T7 |
| `liturgy-step.test.tsx` "the Liturgy step" and "the card's own draft" blocks | T8 |
| its "Generate and Regenerate" block | T9 |
| its "the communion card" and "custom elements" blocks | T10 |
| `status.test.ts` (steps, `stepStatus`, `stillNeeded`), `builder-shell.test.tsx`, the `SHIPPED_STEPS` gate, the liturgy route in the build | T11 |
| the spec or F text, `docs/manual-verification.md`, `test_slice1_docs.py` | T12 |
| a flaky run in Step 2, or a failure only with the clock moved | the task owning the test: fake only `Date` (set to `DRAFT_NOW`), await the UI with `findBy`/`waitFor`, never sleep in place of a condition |
| any other existing test, the Vercel preview only | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-8; commit with the subject `Fix: <what> (Task <n>, slice 4b final verification)` and both trailer lines; have that task re-reviewed; before Step 10, ask the controller for the backup push; after it, the branch is the PR's, so ask the owner first ("May I push the fix for <what> to PR #<N>?") and on the yes run `git push origin claude/slice-2-plan-4q33le`, then repeat Steps 11-12 and send Step 13's message with the new run. An infrastructure failure with no test output gets one `gh run rerun <run-id> -R bbrown62450/church --failed` first.

Expected counts after this task: frontend `517 passed` in 75 files (CI the same); backend `1183 passed, 11 skipped` (CI `backend-postgres`: `11 passed, 1183 deselected`). No commit unless Step 14 needed a fix.

### Task 14: Merge and after (OWNER + agent): the merge, the deploy, a guided check on the phone and a look on a computer, the slice 4b record (S Manual checklist, AC11-AC18; F §5.5; owner answers 1, 2, 4)

4b changes the frontend only (and one backend docs test), so the merge's Railway deploy rebuilds the same API and its pre-deploy `alembic upgrade head` finds the database at head (`0004_invites_reusable`) and runs nothing; no Railway, Supabase or branch-protection setting changes. The Vercel production deploy is the one members see: after it, step 3 of the builder is the real Liturgy step, and it calls 4a's `GET /liturgy/config` and `POST /liturgy/generate` (live since PR #30: 8 sections, 17 places, 16 outline items, 31 communion blocks, `ai_available` true; a short section about 3 s, Prayers of the People about 5 s; the church's default benediction "Halverson"; the owner's church, First Presbyterian Church, has a saved Benediction prompt, so the Benediction the AI writes follows it). Merges never reach https://liturgy-frozen.streamlit.app/. Owner answer 4: a guided check on the phone of six short steps, then a quick look on a computer, given **one at a time** (give one OWNER step, wait for the owner's report or "next", then give the next). The agent writes each result, with its date, into `<scratch>/slice4b-t14-results.md` (not committed); Step 11 fills the record from it. The AI's words differ every time; the owner reports what the page shows.

Below, `<N>` is the PR number (T13), `<merge sha>` the merge commit Step 2 prints, `<scratch>` the scratchpad path; write them out literally. Every `gh` command uses `-R bbrown62450/church`. Pushing, merging, and any settings change each need the owner's explicit yes, asked separately. No token, email address or church id is recorded anywhere.

**Files:**
- Merge (Steps 1-2): no file changes.
- Create (not committed): `<scratch>/slice4b-t14-results.md`.
- Modify (records PR, Step 11, on `claude/slice-2-plan-4q33le` fast-forwarded to `origin/main` after the merge): `docs/ops-runbook.md`: insert `### Slice 4b record` right after `### Slice 4a record`'s table (its last row starts `| Follow-ups | 4b: the Liturgy step,`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins the `##` list.
- Test: none new.

**Interfaces:**
- Consumes: PR `<N>` ready and green (T13); the production URLs; the "## Slice 4" checklist (T12).
- Produces: 4b live on `main` and in production; the "Slice 4b record" in `docs/ops-runbook.md`. Later user: the service reviewer slice (starts from `main` after this).

- [ ] **Step 1 (agent): Check the PR can merge**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,headRefOid --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus) \(.headRefOid)"'
git rev-parse HEAD
git rev-list --count HEAD..origin/main
```

**Expected:** `OPEN draft=false MERGEABLE CLEAN <sha>` with `<sha>` equal to `git rev-parse HEAD`; `0`. If `main` moved (count not `0`, or `BEHIND`): merge it as in T13 Step 1, rerun T13 Steps 2-3 (`517 passed` in 75 files, plus any tests the merge brought; `1183 passed, 11 skipped`), push with the owner's yes, wait for green checks, and run this step again. `BLOCKED`: a required check is not green; fix it (T13 Step 14). Never merge with `--admin`.

- [ ] **Step 2 (agent → OWNER): Ask to merge, then merge**

Send: "PR #<N> is ready, green and up to date with main. May I merge it with a merge commit? After that members see the real Liturgy step (Review stays 'Available soon'); the API and the database do not change." On a clear yes:

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
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" --max-time 15 https://worship-service-builder.vercel.app/builder/liturgy || echo "vercel not reachable from here"
```

**Expected:** `run <id>` and `ci exit 0`; one deployment per environment (a Vercel `Production` one, and Railway's if it reports one) each ending `success` (a `pending` or `in_progress` state: run the loop again a minute later); the `curl` line either a redirect to sign-in (for example `307 https://worship-service-builder.vercel.app/login?next=%2Fbuilder%2Fliturgy`) or `vercel not reachable from here` (the container's network policy; then Step 4 is the check). A `failure` state or a `404`: stop and tell the owner (Step R if the site cannot serve). Ask the owner, once, to glance at Railway's Deploy Logs for the merge's deploy: a health check 200, `AI: configured (model=gpt-4.1-mini)`, no `Running upgrade`, and no Traceback or ERROR line. Record the answer.

- [ ] **Step 4 (OWNER, then agent): Phone, step 1 of 6: the order of worship**

Send the owner this, and wait for the report:

> On your phone, open https://worship-service-builder.vercel.app (signed in, in First Presbyterian Church). Tap **⋮** next to Summary, choose **New service** (if it asks "Start a new service?", tap **Start new service**), then tap **3 Liturgy** in the step bar. You should see "Liturgy", a Sermon title box, a box with **Generate empty sections (6)**, then the order of worship: Call to Worship, Opening Prayer, First Hymn, and so on down to Benediction. Prayers of the People is switched off and says "Off — not in the service. Any text is kept." The Benediction says "Halverson" with "Church default". Is that what you see?

Record the answer (and the phone and browser). Anything wrong: note it, ask for a screenshot, and decide with the owner whether it is a follow-up or needs a fix before going on. "Couldn't load the liturgy sections." here means the API is not answering: record it, check Step 3's deploy, and try again before going on.

- [ ] **Step 5 (OWNER, then agent): Phone, step 2 of 6: writing the empty sections**

> In **Call to Worship**, type one line of your own, for example "Come, let us worship the Lord." While you type, the Back and Next buttons at the bottom should go away, and come back when you tap outside the box. Then tap **Generate empty sections (5)**. Each empty card shows "Writing…" (three at a time), then fills with a draft marked "AI draft"; at the end a message says "Wrote 5 sections." It should take well under a minute. Your Call to Worship stays exactly as you typed it, and the Benediction still says "Halverson". Is that right?

Record the answer, with how long it took (owner answer 2 set the page to wait up to 100 seconds; 4a measured about 3 s a section).

- [ ] **Step 6 (OWNER, then agent): Phone, step 3 of 6: Regenerate and Undo**

> On **Call to Worship**, tap **Regenerate**. It should ask "Replace your text?". Tap **Replace text**: a new draft appears with "Replaced with a new AI draft. Undo". Tap **Undo**: your own line comes back, marked "Your text". Did that work?

Record the answer.

- [ ] **Step 7 (OWNER, then agent): Phone, step 4 of 6: switching a section off and on**

> Switch **Opening Prayer** off with its switch: the text goes away and the card says "Off — not in the service. Any text is kept." Switch it on again: the same text is back. Did it keep the text?

Record the answer.

- [ ] **Step 8 (OWNER, then agent): Phone, step 5 of 6: a custom element**

> At the bottom, tap **Add custom element**. Type "Children's Moment" as the Label, leave Text empty, choose **After Opening Prayer** under Place, and tap **Add**. A dashed card "Children's Moment" marked "Custom" should appear right after Opening Prayer. Then tap its **⋯**, choose **Remove**, and tap **Undo** in the message at the bottom: it comes back in the same place. Did it?

Record the answer.

- [ ] **Step 9 (OWNER, then agent): Phone, step 6 of 6: New service asks first**

> Tap **⋮** next to Summary, then **New service**. Because the liturgy has your text and a custom element, it should ask "Start a new service?" before clearing anything. Tap **Cancel**: everything is still there. Did it ask?

Record the answer (owner answer 1).

- [ ] **Step 10 (OWNER, then agent): A quick look on a computer**

> On a computer, open the same address in a wide window and go to Liturgy. The summary on the right should say "… of 7 liturgy sections ready", "Communion: Yes" or "No", and the number of custom elements; the step bar should show "3 Liturgy" with a count or "Complete". Click **4 Review & send**: under "Still needed", any empty section says "… is empty — Write or generate it", and "No sermon title — Add one" shows if the title is blank; clicking one opens that card. Does it look right?

Record the answer. Optional, only if the owner offers: the liturgy-frozen smoke (sign in, the church and a saved service open). Otherwise record "Not run: 4b changes no data, and merges never reach liturgy-frozen."

- [ ] **Step 11 (agent): Write the slice 4b record**

```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
git log --oneline -1
grep -n '^### Slice 4a record$\|^| Follow-ups | 4b: the Liturgy step,\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); `<merge sha> Merge pull request #<N> from bbrown62450/claude/slice-2-plan-4q33le`; three lines in that order (the 4a record's heading, its last table row, `## Backups`). Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Slice 4b record

Slice 4b (the Liturgy step: the order of worship as editable cards, Generate
and Regenerate with Undo, Generate empty sections, the Benediction and
communion defaults, custom elements, and the step in the step bar, Review and
the summary) merged as PR #<N>. It changes no API and no database, so
production stays at `0004_invites_reusable` (head); the page waits up to
100 s for a section (owner answer 2). The owner's check was a guided check on
a phone and a look on a computer (owner answer 4, 2026-09-30), covering the
"(owner, after 4b)" items of `docs/manual-verification.md` → "Slice 4" in
part. No token, email address or church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` for the merge commit (run <run id>): success. Deployments: <Vercel Production success; Railway success / what the loop showed>. Deploy Logs: <health 200, AI configured (model=gpt-4.1-mini), no Traceback / what the owner saw> | <date> |
| 1. The order of worship (phone: <phone and browser>) | <8 cards in order; Prayers of the People off; Benediction "Halverson", Church default. / What the owner saw instead.> | <date> |
| 2. Generate empty sections | <5 sections written in <n> s; typed Call to Worship unchanged; Benediction untouched; the footer hid while typing. / …> | <date> |
| 3. Regenerate and Undo | <Asked first; replaced; Undo brought the typed line back. / …> | <date> |
| 4. Switching a section off and on | <Off kept the text; on showed it again. / …> | <date> |
| 5. A custom element | <Added after Opening Prayer; Remove and Undo put it back. / …> | <date> |
| 6. New service | <Asked first; Cancel kept the liturgy. / …> | <date> |
| Computer | <Summary counts; step bar; Still needed rows open their cards. / …> | <date> |
| Streamlit smoke on liturgy-frozen | <OK: sign-in, the church and a saved service. / Not run: 4b changes no data, and merges never reach liturgy-frozen.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: the service reviewer as its own slice (owner), reusing the 100 s client timeout and the cards' stale-result rule. 5a: Review, the Word files (the "First Reading" heading, custom elements, communion) and saving the liturgy. 6a: Settings for the default benediction, the liturgy prompts and the prayer library. | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two (separated by ` / `). Then:

```bash
sed -n '/^### Slice 4b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 4b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git diff --stat
git add docs/ops-runbook.md
git commit -m "Runbook: slice 4b record (merged; the Liturgy step is live; owner's guided phone check)" -m "Records the slice 4b merge (PR #<N>): no API or database change; CI on
main and the deployments; the owner's guided check on a phone (the order
of worship, Generate empty sections, Regenerate and Undo, a section off
and on, a custom element, New service) and a look on a computer; the
liturgy-frozen smoke or why it was skipped. No token, email or church id
is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `89 passed in <t>s`; ` docs/ops-runbook.md | <n> +`; one commit.

- [ ] **Step 12 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 4b record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 4b record" \
  --body "Records slice 4b (PR #<N>) in docs/ops-runbook.md → Slice 4b record: the merge and deployments, and the owner's guided check on a phone and look on a computer. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the push; the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`, then `gh pr view claude/slice-2-plan-4q33le -R bbrown62450/church --json state --jq .state` → `MERGED`. Report: "Slice 4 is complete and recorded: the Liturgy step is live; <n> follow-ups. The service reviewer slice can start from `main`."

- [ ] **Step R (only if the 4b release must come out): Revert**

Use this only when the production site cannot serve, or the builder breaks sign-in or the church pages, after the merge, and a fix would take too long. 4b wrote nothing to the database and changed no API or draft shape (liturgy fields a 4b tab wrote stay valid for 3b's code, which shows Liturgy as "Available soon"), so a revert is code only. On the owner's yes for each command that leaves this machine:

```bash
git fetch origin
git switch -c claude/revert-slice-4b origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 4b (PR #<N>): back to the 4a release" -m "The 4b merge <what failed>. 4b changed no database, API shape or draft
shape, so nothing else needs undoing; step 3 shows Available soon again." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
.venv/bin/python -m pytest -q | tail -1
git push -u origin claude/revert-slice-4b
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-4b --title "Revert slice 4b" \
  --body "Reverts the slice 4b merge (PR #<N>) because <what failed>. No database change to undo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/revert-slice-4b -R bbrown62450/church --watch
```

**Expected:** Vitest `Test Files  64 passed (64)`, `Tests  442 passed (442)` (if anything else merged after 4b, it differs by exactly those tests); `1183 passed, 11 skipped`; every check passes. Merge on the owner's yes, then the owner checks that the site signs in and shows the builder with Liturgy "Available soon". Record the revert as a row of the slice 4b record (or its own records PR if Step 12 already merged).

Expected counts after this task: frontend `517 passed` in 75 files on `main`; backend `1183 passed, 11 skipped` (CI `backend-postgres`: `11 passed, 1183 deselected`). The records PR adds no test.

---

## Lessons carried from the slice 2, 3 and 4a builds (P2c-P4a "Build notes")

- **The container restarts.** Uncommitted work can be lost: commit as soon as a task's checks pass; the controller backs the branch up after every task's review. If `node_modules` is gone after a restart, `(cd frontend && npm ci)`.
- **The network is filtered.** The npm registry, PyPI and raw.githubusercontent.com are reachable; ui.shadcn.com, Railway, OpenAI, Supabase and the reading sites are not. No test may need the network: the fake API fails a test on any unhandled request, which is why T11 adds `GET /liturgy/config` to the shell tests' routes. T7 plans for the blocked registry, T13 Step 4 for a font fetch failure, and T14 Step 3 for an unreachable Vercel.
- **Exact anchors.** Every Replace directive names text that occurs once; if one does not match, the tree differs from the plan: stop and find why rather than editing around it.
- **Tests that depend on the date fake `Date`** (`DRAFT_NOW`, Tuesday, September 29, 2026). T13 runs the suite with the real clock moved 8 and 400 days forward. Calling `vi.useFakeTimers` a second time keeps the first call's `toFake` list: call `vi.useRealTimers()` first (T9's "Still working" test). A test that needs a new draft identity moves the fake clock (T9's "service changed" case).
- **TanStack Query v5 keeps `data` with `isError`** after a failed background refetch: the step shows its error only when the config never loaded (T8).
- **Toasts outlive a test.** sonner replays a toast that is still showing to the next `Toaster`; the step tests call `toast.dismiss()` before each test, and Undo toasts last `UNDO_TOAST_MS` (8 s) and are dismissed when the step unmounts and checked against the church (3b's `useUndoToasts`, reused in T10).
- **Don't prove absence by sleeping.** Wait for a positive condition that comes after, then check the absence (T6's cancelled batch waits for a later batch's answer; T9's cancelled runs wait for the bulk toast).
- **Heavy tests near 5 s** carry `{ timeout: 10_000 }` with a comment saying why (T9).
- **Focus and touch.** 44 px targets (buttons `size="touch"`, icon buttons `size-11`, menu items `min-h-11`, the switch's hit area), and rows that wrap at 375 px instead of widening the page (the landmark rows and card headers use `flex-wrap`, `min-w-0` and `wrap-anywhere`).
- **Grep gates exclude tests** and are judged, not obeyed blindly: a hit may be a comment; read the line and explain it in the report.
- **Counts are exact.** Every task states its cumulative count; a drift means a missing or extra test, found before moving on.
- **Owner steps one at a time, in plain words**, and every outward action (PR, ready, merge, settings) on its own yes; then a records PR.

## Build notes (4b build)

Filled in while Tasks 1-12 are built: each change from the plan as written, its reason, and whether the owner saw it. Task 12 (or a follow-up docs commit before Task 13) writes those that alter S or F as "(4b build)" notes.

**Plan fixes made while writing this plan (2026-09-30, before the build):**
The plan was written in one session, building each task's code in a throwaway worktree of `4dfed3b` (hard-linked `node_modules`, one commit per task) and then generating each task's directives from that commit, so the code blocks are the code that ran. While writing it:
- **T3's queue delivers an outcome before the next task starts** (found by T9's 429 test): with the pump first, one queued section was sent after a 429 before the provider could stop the queue; and a task cancelled right after it got a slot still ran (found by T9's Cancel of a bulk run, which left "Writing…" on three cards). T3's `queue.ts` and its fourth test carry both rules (clarification 29); the counts include them.
- **T5 fills the fresh draft's Benediction** in `freshDraft`, not only in the store: with the store alone, every seeded pre-4b test draft changed on load (stamped 1 ms later) and three existing shell, Hymns and context tests failed on `updated_at`; a fresh draft born with the default loads unchanged (clarification 13). T2's summary test builds its "no default" draft with `applyLiturgyDefaults(..., "")` for the same reason.
- **The step tests dismiss toasts before each test** (sonner replays a toast still showing to the next `Toaster`), and the "service changed" case moves the fake clock before New service, since a fresh draft made in the same millisecond has the same `created_at` (clarification 29).
- **A stored draft written 400 ms after a change** is awaited before a test builds "another tab's" copy from `localStorage` (T9's cross-tab case).

**Plan review fixes (2026-10-01, before the build):**
A review of the finished plan found the issues below. Each fix was built and tested in a scratch worktree of `4dfed3b` with the plan's tasks applied, carried into the owning task's code blocks, and the plan replayed again (next paragraph). **[owner-visible]** marks the ones the owner will see; they are also "Questions for the owner" 7-9. The rest are owner decision 1.
- **C1, the card is captured at the click** (T6 `generation.tsx` `generate`/`send`/`settle`; T9 `section-card.tsx` Undo line; clarification 33). The card was captured when its request started, so text that became the member's while the card waited ("Undo" clicked during "Waiting…", or another tab's edit while queued) was replaced without the confirm dialog. Now `generate()` captures at the click or "Replace text"; the queue's run checks `staleVerdict` first and, when the card was edited or the service changed, sends nothing, shows S's toast and counts as not written; the Undo line is hidden while the card runs. Tests: T6 "Undo while Waiting… sends nothing" and "an edit from another tab while the card waits sends nothing" (+2); T9's New service test checks the hidden Undo line.
- **I1, "New service" during a run** **[owner-visible]** (T6 provider; T9 tests; clarification 32). Old errors, Undo lines and runs keyed by section stayed on the new draft. The provider now watches `draft.created_at`: a change cancels every run silently, clears errors and Undo, and ends a bulk run with one toast, "The service changed, so the AI drafts were discarded." (no "Wrote…" toast, no per-card toasts); a result racing the change keeps the per-result rule. T9's service-changed test now expects a silent stop for a single run; a new T9 test covers a bulk run (+1).
- **I2, the card header at 375 px** **[owner-visible]** (T8 `section-card.tsx`; clarification 35). The chips overflowed beside a long title. The header wraps, the chips take their own line below `sm` (`max-sm:basis-full`, `max-sm:order-last`) and lost `shrink-0`; T12's manual check 8 adds the 375 px look at Prayers of the People with "Pastor's copy only" and a status chip.
- **I3, focus never drops to the page** (T8, T9 `section-card.tsx`; T10 `liturgy-step.tsx`, `custom-element-card.tsx`; clarification 34). Card headings have `tabIndex={-1}`; the Regenerate `ConfirmDialog` gets `finalFocus`; after Cancel, Try again, Undo, Clear and Remove focus moves to a surviving control or a heading (Remove: the next card's heading, or "Add custom element"). Tests: T9 (Replace text, Cancel, Keep my text, Try again, Clear, Undo) and T10 (Remove), +1 each.
- **M1** (T6): a result applied over a blank card clears that card's "Cleared. Undo" entry.
- **M2** (T4 comment and commit body, T12's S note and F §1.8 row, owner answer 2's summary, clarification 11): the 100 s reasoning now says the client's timer starts after `getAccessToken()`, so the margin above 85 s covers the server's sign-in key fetch (at most 5 s), latency and the proxy, not the client's own sign-in.
- **M3** (T2 `restoreCustomElement(d, element, index, max)`, T10 `liturgy-step.tsx`): Undo of a Remove refuses past 30 elements with the toast "You can add up to 30 custom elements."; T2's custom-element test gains the full-list assertion (edited, 0) and T10 adds a test (+1).
- **M4** (T8): `decodeURIComponent(location.hash)` is wrapped in `try`/`catch`.
- **M5** (T7 `useAutosize(ref, value, shown)`; T8 passes `card.enabled`): a card switched back on is sized again; T7 adds a test (+1).
- **M6** (T10): the "Add custom element" bottom sheet is `max-md:max-h-[85dvh] max-md:overflow-y-auto`.
- **M7** (T6 `retryAt`; T9 `useRetryWait(retryAt)` exported from `section-card.tsx`, `AiBar`): a 429 stores the absolute moment its wait ends; "Generate empty sections" is disabled until then, and leaving and returning does not restart the wait. T9's 429 test checks the bar; a new T9 test moves the clock while the member is on Review (+1).
- **M8** **[owner-visible]**: left as is (clearing the default Benediction is not unsaved work; a fresh draft restores it); clarification 37.
- **M9** (T8, T9 `section-card.tsx`): the hint, the Assurance line, the counter and the error alert describe the textarea (`aria-describedby`); a bulk run's errors are announced by a polite `aria-live` line instead of one `role="alert"` each, and a card's own run keeps `role="alert"`. T8's hints test and T9's error, no-AI and 429 tests check this (edited, 0).
- Counts: +8 tests (T6 +2, T7 +1, T9 +3, T10 +2): frontend 442 → 517 in 64 → 75 files; the table, every task's expected output, the T10 red run, T11's focused run, T12's diff stat, T13's gates and PR-body line and T14 follow. T9 gained one directive (the error in the textarea's description): 160 in all.

**Replay of the finished plan (2026-10-01, before the build):**
A container restart interrupted the first replay, so the plan was replayed again from scratch on a fresh detached worktree of `4dfed3b` (`npm ci` in its `frontend`; the repo's `.venv` for Python), applying each task's directives and running each task's commands exactly as written, blocks copied by line number without their fence lines. Results:
- Baselines: frontend `442 passed` in 64 files, typecheck 0, lint 0; backend `1183 passed, 11 skipped`.
- All 160 file directives (`Create` and `In …, replace`) applied; every replace anchor occurred exactly once.
- Every "see it fail" output matched as quoted (T1-T11; the absolute path in place of `<repo>`), and every cumulative count matched the table: 446/65, 455/68, 464/71, 468/72, 471/72, 474/73, 476/74, 487/75, 500/75, 507/75, 509/75. Each task's focused run matched its stated file and test totals, and typecheck and lint were 0 after every task. T9 and T10 passed three runs in a row (24 and 31 tests; the step's file takes about 17 s). Each commit's file count matched.
- T7: the registry still answers `Request to https://ui.shadcn.com/r/styles/base-nova/dialog.json failed`; the pinned upstream `dialog.tsx` still hashes to `aba6df6c…66adff`.
- T12: the checks printed `4`, `6`, `11`, `6`, `89 passed`, `1183 passed, 11 skipped`, `2` and ` 4 files changed, 53 insertions(+), 10 deletions(-)`.
- T13 Steps 2-8: 509 in 75 three times and with the clock moved 8 and 400 days, 0 act warnings, typecheck and lint 0; `11 skipped, 1183 deselected`; `✓ Compiled successfully` with the five `/builder` routes and the exact route list; `gen:api` changed nothing; every gate as expected (10 client components, the greps exit 1, `SHIPPED_STEPS` with "liturgy", the two "Available soon" files, the 100 000 row, only `test_slice1_docs.py` among the guarded paths, every trailer present); 60 changed paths (`32 A`, `28 M`; the plan file is the 61st and 33rd `A` on the real branch); the 12 commit subjects equal the plan's (the plan's commit stood in by `4dfed3b`).
- No plan text needed a fix. T14's anchors were checked against the tree: the runbook's "Slice 4a record" heading, its `| Follow-ups | 4b: the Liturgy step,` row and `## Backups` exist in that order, and the outline's place label "After Opening Prayer" (T14 Step 8) is the config's.

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`; F = foundations. Items owned by 4a or later slices are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1-10, 19, 21 | The routes, the outline, generation, no AI, errors, prompts, guards, rate limit, `default_benediction`, no session during AI, rubric and voice | 4a (done) |
| 11 | Typing persists across refresh; Generate empty sections sends one request per enabled empty card, never for a card with text or off; at most 3 in flight | T8 (typing and reload), T9 (the bulk run, the deferred fake), T6 (the queue), T3 (`queue.test.ts`) |
| 12 | Regenerating `typed`/`archive` text asks first, Undo restores text and origin; with AI off nothing is sent, empty cards say so, Regenerate is disabled | T2 (`needsRegenerateConfirm`), T9 (the dialog, Undo, the no-AI test) |
| 13 | Errors only on the card; the draft never holds error text | T9 (the error test reads `localStorage`), T6 (errors in memory) |
| 14 | The Benediction and communion follow their defaults while untouched, stop once changed, and can be restored | T2 (`applyLiturgyDefaults`), T5 (the store and provider), T8 (the Benediction), T10 (communion) |
| 15 | Custom elements: a label required, after their anchor, edited, moved and removed with Undo, at most 30, separate per church | T2, T10 |
| 16 | The step is on in the shell: `SHIPPED_STEPS`, the step bar, the summary block, Still needed | T11 |
| 17 | A run finishes on another step; a replaced draft or another tab's edit drops the result with its toast; a Benediction following the default takes it | T2 (`staleVerdict`), T6 (the card captured at the click and checked before sending; a new service cancels the runs, clarifications 32, 33), T9 (the stale, New service and navigation tests) |
| 18 | Production at 375 px, the keyboard, 6 sections in about a minute | T8 (the footer test), T12 (checklist 8), T14 Steps 4-9 (deployed) |
| 20 | The client sends the effective NT reading's passage, never ESV, one fetch per batch, never blocking | T3 (`sermonSource`, `sermonText`), T4 (`passageQuery`), T6 (`generation.test.tsx`) |

### S sections

| S item | Task(s) |
|---|---|
| UX Layout (375 px, order, landmark rows, `text-base`, textareas to 60 vh, the footer while typing) | T7 (`useAutosize`), T8 (owner answer 3 test; clarifications 24, 28) |
| UX Sermon title | T8 |
| UX AI bar (button, captions, Cancel, "Writing k of n…", toasts, no-AI banner, notices) | T6, T9 (clarifications 15, 16, 23) |
| UX Section card (header, chips, states, hints, menu, other card rules) | T8, T9 (clarifications 21, 22, 30, 31) |
| UX Generate and Regenerate steps 0-7 | T6 (the provider), T9 (the screen), T3 (`queue.ts`; clarification 29) |
| UX Per-card error messages | T3 (`errors.ts`; clarifications 8, 9), T9 |
| UX Benediction and the church default | T2, T5, T8 (clarification 13) |
| UX Communion card | T2, T10 (clarification 26) |
| UX Custom elements | T2, T7 (the dialog), T10 (clarifications 6, 25) |
| UX Loading, error and empty states | T8 |
| Frontend Routes (the page, the hash scroll) | T8 (the scroll), T11 (the page) |
| Frontend Builder shell (`SHIPPED_STEPS`, `summary.ts`, `status.ts`, `SummaryPanel`, `LiturgySummaryBlock`) | T2 (`liturgyCounts`), T11 (clarification 27) |
| Frontend Components | T8-T11 (clarification 1) |
| Frontend Library (`cards.ts`, `defaults.ts`, `request.ts`, `errors.ts`, `queue.ts`, `generation.tsx`) | T2, T3, T6 (clarifications 5, 7, 10, 18) |
| Frontend Card origin transitions | T2 |
| Frontend Sermon text | T3, T4, T6 (clarification 17) |
| Frontend Draft store integration | T1, T5 (owner answer 1; clarifications 2, 3, 13, 14) |
| Frontend API client usage (the 100 s timeout) | T4 (owner answer 2; clarifications 10, 11, 12) |
| Behavior changes BC-1 to BC-5, BC-9 to BC-13, BC-15, BC-17, BC-18, BC-20, BC-21, BC-23, BC-24 (screen halves) | T8-T11; BC-6 T6/T9; BC-7, BC-8, BC-14, BC-16, BC-19, BC-22, BC-25 are 4a's |
| Testing → Frontend (unit and dom 1-17) | T1-T11 (clarification 1) |
| Manual checklist | T12 (appended with checks 10-11), T14 (owner) |
| Risks 4 (the default benediction and a saved draft) | T1 (pinned; clarification 3) |
| Risks 5 (cost with Regenerate) | accepted by S; the 429 path is T6 and T9 |
| Amendment 2026-09-26: service reviewer | its own slice after 4b (owner); 4b leaves the hooks: `captureCard`/`staleVerdict`, the provider's in-memory state beside which notes can live, the 100 s timeout (T12's F row) |

## Questions for the owner

The owner's answers of 2026-09-30 (1-4, "all recommended") are binding and already in the plan. These plan choices are visible to the owner; each has a recommendation. They do not hold up the build: the plan is written as recommended, and a different answer changes the named task before or during its build.

1. **What makes "New service" ask** (clarifications 2 and 3): any text, a section switched on or off, communion you set, a sermon title or a custom element; not blank text, and not a Benediction still showing the church default. Once 5a saves services, a switch on an empty section will no longer count after a save (switches are not saved; the Word file shows only sections with text). Recommended: as written (owner answer 1).
2. **Wording and counts** (clarifications 9, 15, 16, 23): the missing-hymn error's link reads "Go to Hymns"; the progress line counts the section being written ("Writing 1 of 5…" at the start); counts of one read "Wrote 1 section." and "Writing 1 section…"; cancelled sections are left out of the final message, and cancelling the whole run shows none. Recommended: accept.
3. **How the page looks** (clarifications 21, 24, 25, 26, 30): the step starts with the heading "Liturgy"; hymn rows show the title without its number ("First Hymn · Be Thou My Vision"), and readings the program chose say "auto"; a custom element with no label is titled "Custom element"; the communion card's heading is its switch label; the "Replaced…" line shows only when text was replaced; a card's ⋯ menu is greyed out when it has nothing to offer. Recommended: accept.
4. **Errors on a card** (clarifications 8, 22): a problem that trying again can fix shows **Try again** in place of the card's button; one it cannot fix (AI not set up, a prompt problem, a missing hymn) keeps Generate or Regenerate under the message; being signed out or losing access to the church shows nothing on the card, because the app already handles it. Recommended: accept.
5. **Review's "Still needed"** (clarification 27): each empty section's line opens its card; "No sermon title — Add one" opens the Liturgy step; the section lines come first. Recommended: as written.
6. **The manual checklist's count** (T12): with a typed Call to Worship and the church's default Benediction, "Generate empty sections" writes 5 sections, not the 6 the spec's check says. Recommended: accept (the spec's number assumed the Benediction was empty).
7. **"New service" while the AI is writing** (clarification 32, from the plan review): every section still being written is dropped quietly, error messages and Undo lines go, and a "Generate empty sections" run ends with one message, "The service changed, so the AI drafts were discarded." Recommended: accept.
8. **The card header on a phone** (clarification 35, from the plan review): below about 640 px the chips ("Pastor's copy only", "Empty") move to their own line under the section's name, so nothing is squeezed at 375 px. Recommended: accept.
9. **Clearing the church's default Benediction** (clarification 37, from the plan review): clearing it does not make "New service" ask, since a new service brings the default back. Recommended: leave as is.
