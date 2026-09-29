# Slice 2b: Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship PR 2b of slice 2, the frontend foundation, live. After it merges, a signed-in member who opens https://worship-service-builder.vercel.app lands on `/builder` (then the step they were last on), inside the four-step Service Builder shell: the title "Service Builder" with a "Summary" button and a "New service" menu, the step progress, a sticky footer with Back and Next, and the summary (a sticky column on desktop, a bottom sheet on a phone). All four steps, Date & readings included (owner answer Q1), show the "Available soon" card with "Keep using the current app for this part." and no link to the old app (owner answer Q2). Underneath: `lib/dates.ts` (date-only helpers and the `new Date("YYYY-MM-DD")` guard), `lib/scripture-refs.ts` (the TypeScript port that passes the shared fixture), and the whole draft store: the zod `DraftV1` schema, migrations, the per-user-per-church store with debounced writes, memory-only mode and cross-tab adoption, the readings transitions and selectors, the communion date effect, step status, the provisional payload and its fingerprint, and pruning after `/me`. The header gains `AppNav` with its one item, "Builder". The backend does not change (one shared JSON fixture is added under `backend/tests/fixtures/shared/`; no Python file changes), there is no migration, and production Streamlit (https://liturgy-frozen.streamlit.app/, branch `streamlit-frozen`) is untouched.

**Architecture:** Pure modules first, React last. `src/lib/dates.ts` and `src/lib/scripture-refs.ts` are pure. `src/lib/draft/` holds `schema.ts` (zod, `freshDraft`, the storage keys), `migrate.ts` (parse, migrate, validate), `readings.ts` and `date-effects.ts` (pure transitions that return the same object when nothing changes), `steps.ts` (`STEPS`, `SHIPPED_STEPS`, empty in 2b), `status.ts` (`stepStatus`, `isPristine`, `stillNeeded`), `mapping.ts` (the provisional `draftToServicePayload`, which 5a replaces), `fingerprint.ts` (FNV-1a, `isDirty`), `store.ts` (a plain `DraftStore` class: load, `update`, `replace`, `setLastStep`, debounced `flush`, `handleStorageEvent`; storage goes through `lib/storage.ts`), `context.tsx` (`DraftProvider`/`useDraft`: `useSyncExternalStore`, the browser listeners and the three toasts) and `prune.ts`. `src/components/builder/` holds the shell (`BuilderShell`, `StepHeader`, `StepProgress`, `StepFooter`, `SummaryPanel`, `SummarySheet`, `StepPlaceholder`, `StillNeeded`, `NewServiceMenuItem`), rendered by `src/app/(signed-in)/(church)/builder/layout.tsx` around the index page and the four step pages. `BuilderShell` reads the church profile the `(church)` layout already loaded and keys `DraftProvider` by user and church. `/` redirects to `/builder` in a client effect. `AppNav` is one element that `AppHeader` places as a segmented row below `md` and a link row from `md`. Every page is a client component (F §4.1).

**Tech Stack:** Next 16.3.6 (App Router, Turbopack), React 19.2.8, TypeScript 5, Tailwind 4, Base UI 1.8 (shadcn "base-nova"), TanStack Query 5, sonner, zod 4.6.5 (new direct dependency; already installed as a transitive one), Vitest 3.2.7 (`unit` node and `dom` jsdom projects) with Testing Library; the backend (Python 3.11, FastAPI) is not changed; GitHub Actions (`backend`, `backend-postgres`, `frontend`, all required on `main`), Vercel (frontend), Railway (API), Supabase Postgres.

**Source documents:**
- Slice spec ("S"): `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`. The 2b parts: the slice split at the top (line 5), Scope, Hand-offs, User experience "Builder shell" and "Other states and messages", Frontend changes ("Routes and files", "lib/dates.ts", "lib/scripture-refs.ts", "Draft store", "Queries"), Testing "Frontend", AC8 (TypeScript half), AC10, AC11, AC12, AC17, and the "(2a build)" corrections.
- Foundations ("F §n"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` (§4.1, §4.2, §4.4, §4.6, §4.7, §4.8, §4.9, §4.10, §4.11, §5.2, §5.3, §5.5, acceptance 10–12).
- Slice 2a plan ("P2a"): `docs/superpowers/plans/2026-09-28-slice-2a-backend.md` (structure, conventions and its "Build notes (2a build, 2026-09-28)"). Slice 1b plan ("P1b"): `docs/superpowers/plans/2026-09-28-slice-1b-onboarding.md` (frontend conventions). Slice 1a plan: `docs/superpowers/plans/2026-09-26-slice-1a-platform.md` (the Base UI generation fallback, its owner Q3).
- The shared fixture `backend/tests/fixtures/shared/scripture_refs.json` and its Python port `backend/scripture_refs.py` (2a build: the automatic OT skips the NT pick; the aliases revelations, mat, rm, php, jdg and eccles).
- Production facts: `docs/ops-runbook.md` ("Slice 2a record": `GET /church` already returns the profile fields; ESV is configured).
- Facts checked for this plan (tree `864ebcd`, slices 1a, 1b and 2a merged and live):
  - Frontend baseline `221 passed` in 34 files; `npm run typecheck` and `npm run lint` clean; backend baseline `971 passed, 9 skipped`.
  - `frontend/src/lib/api/schema.d.ts` already has `ChurchProfileOut`, `LectionaryOut`, `ReadingSetOut`, `TranslationsOut` and the passage types (2a).
  - `zod` 4.6.5 is in `node_modules` (through `eslint-config-next` and `shadcn`) but not in `package.json`.
  - The build container reaches registry.npmjs.org and Google Fonts, but not ui.shadcn.com (`CONNECT tunnel failed, response 403`, checked 2026-09-28), nor Railway or the three reading sites.
  - Every task's code below was written and run by the plan's writer in a throwaway worktree at `864ebcd` (hard-linked `node_modules`): the full suite ran three times at `299 passed` in 49 files, typecheck and lint were clean, `next build` listed the five new routes, and the backend suite stayed at `971 passed, 9 skipped`. Then T1–T11 were replayed from this document onto a second clean worktree at `864ebcd` (every "Create" and "Replace" block, and each described edit): after each task the suite gave exactly the count in the table below, the result was byte-identical to the tested code, and T11's script and T12's path, lockfile and API checks gave their stated outputs. Not run while planning: a successful `shadcn add` (the registry is blocked; its failure message was recorded), the pushes and CI (T12), and the OWNER steps (T13).
  - Where S and the code or F disagreed, the code and F won; each case is a numbered clarification below.

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run the frontend as `(cd frontend && …)` from the repo root; the working directory resets between commands. Use absolute paths when a tool asks. No foreground `sleep`.
- Run one test file with `(cd frontend && npx vitest run <path> 2>&1 | tail -15)`. Run the whole suite with `(cd frontend && npm test 2>&1 | tail -6)`, then `(cd frontend && npm run typecheck && npm run lint)`.
- Run the backend suite only where a step says so: `.venv/bin/python -m pytest -q | tail -1` (expected `971 passed, 9 skipped` at every point; 2b changes no Python file).
- `node_modules` exists. If it is missing after a container restart, run `(cd frontend && npm ci)` (the npm registry is reachable).
- Branch: `claude/slice-2-plan-4q33le`, cut from `origin/main` at `864ebcd`. The first commit is this plan, at `docs/superpowers/plans/2026-09-28-slice-2b-frontend.md`.
- Stage files by name (paths with parentheses in single quotes). `.claude/` stays untracked.
- `main` is protected: the `backend`, `backend-postgres` and `frontend` checks must pass and the branch must be up to date. Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Commits end with a blank line and `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Subjects read "Area: plain words (F §x, S …)". Use TDD: write the failing test first and quote its failure.
- **Backup push after every task** (owner answer Q3): right after each task's commit, `git push origin claude/slice-2-plan-4q33le` (never `--force`; there is no open PR, so the push asks nobody; Vercel may build a preview). A fix asked for by the task's review is a new commit, `Fix: <what> (Task <n> review)`, pushed the same way (never an amend of a pushed commit); T12 Step 8 lists it. The container can restart and lose uncommitted work, so commit as soon as a task's checks pass. If the push is refused because the remote moved, stop and ask the controller.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and includes the line "Tests: frontend 221 → 299 in 34 → 49 files; backend 971 → 971 passed, 9 → 9 skipped".
- New prose for the owner has no em dashes. Code strings copied from S (for example "No occasion — Add one", "Too many requests — try again in N s.") keep theirs.

### Baselines and counts
- Starting baselines: frontend **221 passed in 34 files**, typecheck and lint clean; backend **971 passed, 9 skipped**. If any baseline differs, stop and ask.
- Planned cumulative frontend counts. Each delta is exactly the number of `it(` blocks the task adds (a modified test that replaces another counts 0). If a count drifts, stop and find why.

  | After | Tests (delta) | Test files (delta) | Count |
  |---|---|---|---|
  | T1 | +9 (`dates.test.ts` 7, `dates.guard.test.ts` 2) | +2 | 230 in 36 |
  | T2 | +10 (`scripture-refs.test.ts`) | +1 | 240 in 37 |
  | T3 | +7 (`draft/schema.test.ts` 4, `draft/migrate.test.ts` 3) | +2 | 247 in 39 |
  | T4 | +9 (`draft/readings.test.ts`) | +1 | 256 in 40 |
  | T5 | +12 (`draft/status.test.ts` 7, `draft/mapping.test.ts` 3, `draft/fingerprint.test.ts` 2) | +3 | 268 in 43 |
  | T6 | +12 (`draft/store.test.ts` 11, `storage.test.ts` +1) | +1 | 280 in 44 |
  | T7 | +8 (`draft/context.test.tsx` 4, `draft/prune.test.ts` 3, `signed-in-layout.test.tsx` +1) | +2 | 288 in 46 |
  | T8 | +1 (`use-keyboard-open.test.tsx`) | +1 | 289 in 47 |
  | T9 | +8 (`builder/builder-shell.test.tsx`) | +1 | 297 in 48 |
  | T10 | +2 (`builder/church-switch.test.tsx` 1, `app-header.test.tsx` +1; `church-layout.test.tsx` replaces one test, 0) | +1 | 299 in 49 |
  | T11 | 0 | 0 | 299 in 49 |

- The backend stays at 971 passed, 9 skipped throughout (T1 adds only a JSON fixture). CI `backend-postgres` shows `9 passed, 971 deselected, 1 warning`.
- Fixture-driven tests loop over their cases inside one `it` (as in P2a), so 5a's later fixture cases do not change the counts.

### Code rules (F §4)
- Every file under `src/app/` that renders is a client component (`"use client"`, F §4.1). Pages never call `apiFetch` (F §4.4).
- Base UI rules (F §4.9): generated components only, hand edits limited to variants; no `asChild` (use `render`, or `buttonVariants` on a `Link`); `DropdownMenuLabel` inside a `DropdownMenuGroup`; toasts stay on sonner. The one recorded exception is clarification 3.
- Date-only values stay `YYYY-MM-DD` strings; nothing outside `lib/dates.ts` calls `new Date(` on a date-only literal or on an identifier ending in `date_iso`/`dateIso` (F §4.10, acceptance 12; T1's guard test enforces it).
- Browser storage goes through `lib/storage.ts` only (F §4.3); the draft store reads and writes `localStorage["wsb:draft:{userId}:{churchId}"]` (F §4.6).
- User and AI text renders as React text only (`react/no-danger` is an error).
- Links that look like buttons are `<Link className={buttonVariants(…)}>`, so they keep the link role; tests never click a Next.js `Link` (jsdom has no navigation) and assert its `href`.
- DOM tests that depend on "today" fake only `Date` (`vi.useFakeTimers({ toFake: ["Date"] })` plus `vi.setSystemTime(DRAFT_NOW)`), so user-event's timers keep running.

### Messages (verbatim, from S and F)
- Placeholder card: title "Available soon", body "Keep using the current app for this part." (no link; owner answer Q2).
- Header: "Service Builder"; button "Summary"; overflow trigger `aria-label` "More actions"; menu item "New service".
- New service confirm: title "Start a new service?", body "This clears the current draft on this device.", confirm "Start new service", cancel "Cancel".
- Progress: "Step {n} of 4 · {label}", labels "Date & readings", "Hymns", "Liturgy", "Review & send"; statuses "Complete", "{done} of {total}", "Soon", "Not in archive".
- Footer: "Back", "Next: Hymns", "Next: Liturgy", "Next: Review".
- Summary blocks: "Date", "Readings", "Hymns", "Liturgy"; "Sunday, October 4, 2026"; "No occasion yet"; "No readings yet"; "Available soon"; chips "OT", "OT (auto)", "NT", "NT (auto)"; status line "Draft saved on this device · Not in archive" or "Draft not saved on this device · Not in archive".
- Still needed: heading "Still needed"; rows "No service date — Choose one", "No occasion — Add one", "No scripture readings — Add one".
- Toasts: "We couldn't restore your unsaved draft." (error), "This browser isn't saving your draft. Don't refresh until you save." (warning), "Updated from another tab." (info).
- Nav: `aria-label` "Main", item "Builder".

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried over from 2a, owner answer Q3). Each one is recorded as a numbered clarification marked "(owner decision 1)".
2. **Production Streamlit** is https://liturgy-frozen.streamlit.app/ (branch `streamlit-frozen`), frozen; merges never reach it.
3. **`main` is branch-protected** (`backend`, `backend-postgres`, `frontend`; up to date).
4. **Spec decision 1:** the step builder with a desktop summary panel. 2b ships the shell; 2c, 3, 4 and 5a fill the steps.
5. **Production:** frontend https://worship-service-builder.vercel.app (Vercel), API https://church-production-74ca.up.railway.app (Railway). The build container cannot reach Railway or the reading sites; no frontend test needs the network.

### Owner answers (2026-09-28, binding for the plan)
- **Q1: ship the builder live after 2b.** `/` goes to `/builder`. Until 2c, Date & readings also shows the "Available soon" card, like steps 2–4. The plan keeps "readings" out of `SHIPPED_STEPS` until 2c adds it (clarification 2).
- **Q2: no link to the old Streamlit app anywhere.** The card keeps S's copy as plain text.
- **Q3: same process as 2a.** Subagent-driven, one task at a time with review, a backup push to `claude/slice-2-plan-4q33le` after each task, one PR; the owner is asked before the PR is opened, before it is marked ready, and before it is merged. The standing permission (owner decision 1) carries over; each use is recorded.
- **Q4: automated tests plus a short look by the owner after merge.** T13's owner steps are few and short (phone and desktop: the builder, the step bar, Summary, New service). There is no long manual checklist in 2b; `docs/manual-verification.md` is untouched (clarification 29).
- Also binding: the spec's open question 2 (Saturday vigil) stays with 2c.

### The 2b / 2c split (S line 5 is authoritative)
S line 5 gives 2b "`lib/dates.ts`, `lib/scripture-refs.ts`, the draft store, the builder shell with all four step routes, `/` → `/builder`", and 2c "the Date & readings step UI".

| Piece | Slice | Why |
|---|---|---|
| `lib/dates.ts`, `dates.guard.test.ts`, `shared/next_sunday.json` | 2b | S line 5; the fresh draft needs `nextSunday(todayIn(tz))` |
| `lib/scripture-refs.ts` and its fixture test | 2b | S line 5; `normalizePicks`, `effectivePicks` and the provisional payload use it |
| The whole `lib/draft/` folder: `schema`, `migrate`, `store`, `context`, `readings`, `date-effects`, `steps`, `status`, `mapping`, `fingerprint`, `prune` | 2b | "the draft store" (S line 5; S "Draft store" lists the readings transitions and date effects as part of it). They are pure and unit-tested here, so 2c only builds UI on them |
| `lib/storage.ts` `tryWriteLocal` and `localKeys`; `lib/use-keyboard-open.ts`; the `sheet` and `badge` components | 2b | the store and the shell need them |
| The builder shell, the four step routes, `/builder` → `last_step`, `/` → `/builder`, `AppNav`, pruning after `/me`, the church-switch test | 2b | S line 5 and Scope "Builder shell" |
| `lib/queries/lectionary.ts`, `reference.ts`, `passages.ts` (`useLectionary`, `useTranslations`, `usePassage`, `createLimiter`, `passageLimiter`, `passageText`), the `lib/api/timeouts.ts` entries, `lib/use-debounced-value.ts` | 2c | only the Date & readings step calls them; their tests (S "Queries", `passages.test.ts`, `use-debounced-value.test.ts`) go with it |
| `useLectionarySync()` (mounted in `BuilderShell` by 2c) | 2c | it fetches and auto-fills; with the step on the placeholder (Q1) it would fill fields nobody can see or edit, and its tests live in `readings-step.test.tsx` |
| `ReadingsStep` and its twelve components; `radio-group`, `collapsible`, `tooltip` | 2c | "the Date & readings step UI" |
| Adding "readings" to `SHIPPED_STEPS`, replacing the readings placeholder page, `readings-step.test.tsx` | 2c | turns on the step status, "Still needed" rows, the Readings summary block and the occasion line that 2b already renders behind `SHIPPED_STEPS` (T9 tests them with `shipped` passed in) |
| The slice 2 manual checklist in `docs/manual-verification.md` (and the matching update to `test_slice1_docs.py`) | 2c | S's thirteen checks are readings checks (clarification 29) |


## Spec clarifications

The code and F win over S's outline. Each item says whether the owner would notice it: **[owner-visible]** items are listed again in the controller's questions at the end; the rest are owner decision 1 (no owner-visible change) or plain readings of S.

1. **The 2b / 2c split** is the table above. S's Testing table names `readings-step.test.tsx`, `passages.test.ts` and `use-debounced-value.test.ts`; those are 2c's.
2. **[owner-visible] Date & readings in 2b (owner answer Q1).** `SHIPPED_STEPS` is empty in 2b, so every step shows the placeholder card; the progress reads "Soon" for Date & readings, Hymns and Liturgy and "Not in archive" for Review; Review's "Still needed" section is hidden (it lists only shipped steps, and none has shipped); the summary's Readings, Hymns and Liturgy blocks say "Available soon"; the Date block shows the draft's date ("Sunday, October 4, 2026", the next Sunday in the church's zone) without the occasion line. Reason: shipping "readings" with the placeholder would make "Still needed" say "No occasion — Add one" for a field nobody can reach, and it keeps 2c's hand-off the same one-line switch slices 3, 4 and 5a make (add the step to `SHIPPED_STEPS`, replace its page). The readings status, rows, occasion line and chips are already built and tested (T9) behind `SHIPPED_STEPS`.
3. **Base UI `sheet` and `badge` (a recorded exception to F §4.9.1, like 1a's owner Q3 combobox).** T8 first runs `npx shadcn@latest add sheet badge`. The container's network policy blocks ui.shadcn.com (checked 2026-09-28), so that is expected to fail with a network error; T8 then uses the hand-written files in this plan: thin wrappers over `@base-ui/react/dialog` and `@base-ui/react/use-render` with the base-nova exports, each headed by a comment naming this clarification. They look and behave like the generated ones, and a later `shadcn add` (from a machine that reaches the registry) can replace them. **Owner question A** asks for the yes the controller needs before T8 (recommended: yes). If the owner says no, T8 stops at its Step 3 and the owner generates the two files instead.
4. **`zod` is added by editing two lines** of `package.json` and `package-lock.json` (and dropping `"dev": true` from the `node_modules/zod` entry), not with `npm install`. The container's npm 10.9.7 rewrites the lockfile when it installs (it drops every `"libc"` field, about 130 lines), which could change which optional native packages CI and Vercel install. `npm ci --dry-run` confirms the edited lockfile is in sync. (Owner decision 1.)
5. **`DraftV1` in 2b is F §4.6's shape without 5a's two fields** (`save_key_fingerprint`, `editing.date_iso`). F §4.6 says 5a adds them with a `DRAFT_VERSION` bump and a tested migration; S's "the complete `DraftV1`" means the hymns and liturgy sections are included, which they are.
6. **`lib/storage.ts` gains `tryWriteLocal(key, value): boolean` and `localKeys()`.** S says every draft read and write goes through `lib/storage.ts` and that a storage exception switches to memory-only; the existing `writeLocal` swallows the exception, so the store could not tell. `prune.ts` needs to list keys. Both keep the try/catch rule.
7. **A stored draft whose `user_id` or `church_id` differs from its key is treated as unrestorable** (backed up, fresh draft, the toast), so a draft copied between keys on a shared device never shows under another person or church. (Owner decision 1.)
8. **A fresh or repaired draft is written 400 ms after the builder mounts**, not only after the first edit (S is silent). The save key then stays stable across a refresh, and blocked storage is noticed (and the one-time warning shown) even before an edit. Writes happen in effects (`DraftStore.start`, timers, listeners), never during a render. (Owner decision 1.)
9. **`replace(next)` sets `updated_at` to now** as well as normalizing the picks, so another open tab adopts a "New service" (it adopts only a strictly newer `updated_at`). (Owner decision 1.)
10. **"New service" asks first when `isDirty(draft)`** (F §4.6 item 1: "after a confirmation if it is dirty"), where S says "unless `isPristine`". The two are the same until 5a saves drafts (`isDirty` is `!isPristine` while `saved_fingerprint` is null); after 5a, a saved and unchanged draft resets without asking, which is F's rule. No difference in 2b.
11. **[owner-visible] Memory-only status line.** S gives "Draft not saved on this device" and F §4.7 keeps the device half and the archive half apart, so the line reads "Draft not saved on this device · Not in archive" (normally "Draft saved on this device · Not in archive").
12. **[owner-visible] Step status words.** S writes the complete state as "(✓)". The progress shows a check icon and the word "Complete" (screen readers and tests read "Complete"); the other states are "{done} of {total}", "Soon" and "Not in archive". Each progress link's name is "{n} {label} {status}", for example "2 Hymns Soon".
13. **`stepStatus` already computes the hymns and liturgy counts of F §4.7** (three slots; enabled cards with text), gated by `SHIPPED_STEPS`, so slices 3 and 4 add their step id rather than rewrite the function. Review stays "Not in archive" until 5a: its "Saved" / "Unsaved changes" rule needs `isDirty`, and `status.ts` cannot import `fingerprint.ts` (which imports `status.ts`) without a cycle; 5a changes it. `stillNeeded` has the readings rows only; 3 and 4 add theirs (S Hand-offs).
14. **A readings date counts only inside 1900–2199** (`hasServiceDate`), the range the lookup accepts and the one S's "Enter a date between 1900 and 2199." enforces.
15. **Desktop column or bottom sheet is decided by CSS** (`hidden lg:block` on the column, `lg:hidden` on the "Summary" button and the sheet), not by `matchMedia`. jsdom renders both, so tests scope by landmark ("Summary" complementary, "Summary" dialog). S's "(the `matchMedia` shim)" is not needed.
16. **[owner-visible] `AppNav` shows on church pages only** (with the church switcher), not on `/welcome`, and the header's content width grows from `max-w-3xl` to `max-w-6xl` so it lines up with the desktop builder. `AppNav` is one `<nav aria-label="Main">`, placed by the header's CSS grid under the switcher below `md` and between the switcher and the account menu from `md`.
17. **The `(church)` home test is replaced.** `church-layout.test.tsx`'s "the home page shows the confirmed church from useChurch()" checked the slice-0 placeholder cards; it becomes "the home page opens the Service Builder" (the count does not change).
18. **`church-switch.test.tsx` lives in `src/components/builder/`** (2b), not `builder/readings/`: it tests the store and the shell's keyed remount, not the readings step.
19. **`next_sunday.json`** is `backend/tests/fixtures/shared/next_sunday.json` (S, F §5.3) with S's four cases plus a leap-day case, in `{"_about", "cases": [{from, expected, why}]}`. No backend code or test reads it; `backend/tests/fixtures/README.md` is not edited (the recorder rewrites it from `record_fixtures.py`, which 2b does not change), and the file's `_about` says what it is.
20. **Set comparisons use `scriptureKey` per line** (`selectedSetIndex`, `showAvailableBanner`), so "Luke 2:1-14 (15-20)" and "Luke 2:1-14, (15-20)" count as the same reading; S says "equal".
21. **`pruneDrafts` keeps a draft whose `updated_at` cannot be read**; the store backs it up and starts fresh when that church's builder opens. It runs after every `/me` load (cheap and idempotent), not only the first.
22. **`useKeyboardOpen` counts text inputs, textareas and editable elements**; date, time, checkbox, radio, range, file and button inputs and read-only fields do not open a keyboard, so the footer stays.
23. **The mount-time roll-forward bumps `updated_at`** (it changes the draft) and is written with the first write.
24. **`BuilderShell` reads the profile with `useChurchProfile(church.id)`**, whose type widens from `Church` to `ChurchProfile` (`GET /church` has returned the profile since 2a). `useChurch()` stays `{id, name, role}` (S Hand-offs row 1). Until the query has data, a step-shaped skeleton shows (S "Builder first render").
25. **`DraftProvider` is keyed by `{userId}:{churchId}`** inside `BuilderShell`, on top of the `(church)` layout's keyed remount.
26. **Toast kinds and ids:** the restore failure is `toast.error`, memory-only `toast.warning`, adoption `toast.info`, each with a fixed id so StrictMode or a quick repeat never stacks two.
27. **`/builder` renders a skeleton and no progress or footer**; it only redirects to `last_step`. `/` redirects in a client effect (F §4.1), not with `next.config` redirects.
28. **`onDateChanged(d, prevIso)`** keeps `prevIso` (unused in 2b) for slice 3's hymn effect.
29. **`docs/manual-verification.md` is untouched in 2b.** `test_slice1_docs.py::test_manual_verification_has_the_slice_1_section` pins its last two `##` headings, and S's thirteen manual checks are about the Date & readings step, so 2c appends "## Slice 2" and updates that test. 2b's after-merge look is T13's short owner steps (owner answer Q4), recorded in the runbook.
30. **Links styled as buttons keep the link role** (`<Link className={buttonVariants(…)}>`, as `ChurchSwitcher` does), rather than `<Button render={<Link/>} nativeButton={false}>`, which gives a link the button role.
31. **The placeholder is a `<section>` named after the step** ("Date & readings", …) holding the `EmptyState`; `EmptyState` keeps its own `h2` "Available soon".
32. **`freshDraft` takes an optional `now`** (tests pass `DRAFT_NOW`); the store takes an injectable `now` and storage adapter, so `store.test.ts` runs in the node project without a browser.

### Risks carried into the plan
- **A live builder with nothing to fill in.** Members see four "Available soon" cards until 2c. Owner answer Q1 accepts this; the summary still shows next Sunday's date.
- **Drafts are now stored for every member who opens the builder.** Each is small (one fresh draft per user per church) and pruned after 30 days or when the member leaves the church.
- **Hand-written `sheet` and `badge`** (clarification 3): a later `shadcn add` may differ in class names; the tests do not depend on classes.
- **Clock-dependent tests** fake only `Date`; a test that forgets it would pass or fail with the calendar. T12 runs the suite three times.
- **Turbopack refuses a symlinked `node_modules`** (seen while planning); `npm run build` must run in the real checkout (T12 does).


## File Structure

All paths are from the repo root. "(church)" means `frontend/src/app/(signed-in)/(church)`.

**Created**

| Path | Responsibility | Task |
|---|---|---|
| `docs/superpowers/plans/2026-09-28-slice-2b-frontend.md` | this plan (first commit) | 0 |
| `backend/tests/fixtures/shared/next_sunday.json` | the TypeScript-only next-Sunday cases (F §5.3) | T1 |
| `frontend/src/lib/dates.ts` (+ `dates.test.ts`, `dates.guard.test.ts`) | date-only parsing, arithmetic, formatting, `todayIn`, `nextSunday`, `isFirstSundayOfMonth`, `inSupportedRange`; the F acceptance 12 source scan | T1 |
| `frontend/src/lib/scripture-refs.ts` (+ test) | the TypeScript port of `backend/scripture_refs.py` above its "Fetch only" line, plus `scriptureKey` | T2 |
| `frontend/src/lib/draft/schema.ts` (+ test) | the zod `DraftV1`, `DRAFT_VERSION`, `STEP_IDS`, `SLOTS`, `SECTION_KEYS`, `freshDraft`, `churchZone`, `draftKey`, `corruptDraftKey` | T3 |
| `frontend/src/lib/draft/migrate.ts` (+ test) | `migrations`, `migrate`, `parseStoredDraft`, `DraftRestoreError` | T3 |
| `frontend/src/lib/draft/date-effects.ts` | `onDateChanged` (the communion default) | T4 |
| `frontend/src/lib/draft/readings.ts` (+ test) | the readings transitions and selectors of S "readings.ts" | T4 |
| `frontend/src/lib/draft/steps.ts` | `STEPS`, `SHIPPED_STEPS` (empty), `stepById`, `stepFromPath` | T5 |
| `frontend/src/lib/draft/status.ts` (+ test, which also covers `steps.ts`) | `stepStatus`, `hasServiceDate`, `isPristine`, `stillNeeded` | T5 |
| `frontend/src/lib/draft/mapping.ts` (+ test) | the provisional `draftToServicePayload` and `ServiceDraftPayload` (5a replaces) | T5 |
| `frontend/src/lib/draft/fingerprint.ts` (+ test) | `stableStringify`, `fnv1a32`, `fingerprint`, `isDirty` | T5 |
| `frontend/src/lib/draft/store.ts` (+ test) | `DraftStore`, `rollForward`, `browserDraftStorage`, `WRITE_DELAY_MS` | T6 |
| `frontend/src/lib/draft/context.tsx` (+ `context.test.tsx`) | `DraftProvider`, `useDraft`, `DRAFT_MESSAGES` | T7 |
| `frontend/src/lib/draft/prune.ts` (+ test) | `pruneDrafts`, `PRUNE_AFTER_MS` | T7 |
| `frontend/src/components/ui/sheet.tsx`, `frontend/src/components/ui/badge.tsx` | Base UI sheet and badge (generated, or clarification 3's hand-written files) | T8 |
| `frontend/src/lib/use-keyboard-open.ts` (+ `.test.tsx`) | `useKeyboardOpen`, `isTextEntry` | T8 |
| `frontend/src/components/builder/step-placeholder.tsx` | the "Available soon" card | T9 |
| `frontend/src/components/builder/still-needed.tsx` | Review's "Still needed" list | T9 |
| `frontend/src/components/builder/step-progress.tsx` | `StepProgress`, `statusText` | T9 |
| `frontend/src/components/builder/step-footer.tsx` | Back and Next | T9 |
| `frontend/src/components/builder/summary-panel.tsx` | `SummaryPanel` | T9 |
| `frontend/src/components/builder/summary-sheet.tsx` | the bottom sheet below `lg` | T9 |
| `frontend/src/components/builder/new-service-menu-item.tsx` | `useNewService`, `NewServiceMenuItem` | T9 |
| `frontend/src/components/builder/step-header.tsx` | title, "Summary", the overflow menu | T9 |
| `frontend/src/components/builder/builder-shell.tsx` (+ `builder-shell.test.tsx`) | `BuilderShell`, `BuilderSkeleton` | T9 |
| `(church)/builder/layout.tsx`, `(church)/builder/page.tsx`, `(church)/builder/{readings,hymns,liturgy,review}/page.tsx` | the builder routes | T9 |
| `frontend/src/components/app/app-nav.tsx` | `AppNav`, `NAV_ITEMS` | T10 |
| `frontend/src/components/builder/church-switch.test.tsx` | one draft per church across a switch | T10 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `frontend/package.json`, `frontend/package-lock.json` | `zod` `^4.6.5` as a direct dependency (clarification 4) | T1 |
| `frontend/src/lib/api/types.ts` | `ChurchProfile`, `Lectionary`, `ReadingSet`, `Translations` | T3 |
| `frontend/src/test/fixtures/index.ts` | `churchProfile`, `DRAFT_NOW`, `testDraft` (T3); `lectionary` (T4) | T3, T4 |
| `frontend/src/lib/storage.ts`, `frontend/src/lib/storage.test.ts` | `tryWriteLocal`, `localKeys` (clarification 6) | T6 |
| `frontend/src/app/(signed-in)/layout.tsx`, `frontend/src/app/(signed-in)/signed-in-layout.test.tsx` | prune after `/me` | T7 |
| `frontend/src/lib/queries/church.ts` | `useChurchProfile` typed `ChurchProfile` (clarification 24) | T9 |
| `(church)/page.tsx`, `(church)/church-layout.test.tsx` | `/` → `/builder` (clarification 17) | T10 |
| `frontend/src/components/app/app-header.tsx`, `frontend/src/components/app/app-header.test.tsx` | renders `AppNav`; wider content (clarification 16) | T10 |
| `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md` | "(2b plan)" corrections | T11 |
| `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` | one amendment row | T11 |

**Untouched:** every Python file, `backend/requirements*.txt`, migrations, `frontend/src/lib/api/openapi.json` and `schema.d.ts` (no API change), `docs/manual-verification.md` (clarification 29), `docs/ops-runbook.md` until T13's record, Streamlit files, CI workflows.

**Task order and checkpoints:** T1 → T2 → … → T11 → T12 → T13. Each of T1–T11 ends in one commit, a review and a backup push (owner answer Q3). With the plan commit, the branch carries 12 commits before T12. The review checkpoints are stops for the controller, not merges: everything ships in the one 2b PR.

---

### Task 1: Preflight, zod, `lib/dates.ts`, the next-Sunday fixture and the `new Date` guard (F §4.10, §4.11, acceptance 12; S "lib/dates.ts", Testing `dates.test.ts`, `dates.guard.test.ts`; clarifications 4, 19)

This task checks the baselines, adds `zod` as a direct dependency (F §4.11; clarification 4), and adds the date-only helpers every later task uses. `nextSunday` is tested against the shared `next_sunday.json`, which this task creates (P2a clarification 22 left it to 2b). The guard test scans `src/` for `new Date(` on a date-only value (F acceptance 12). Nothing the user sees changes.

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json` (zod)
- Create: `backend/tests/fixtures/shared/next_sunday.json`
- Create: `frontend/src/lib/dates.ts`
- Test: `frontend/src/lib/dates.test.ts` (new, 7 tests), `frontend/src/lib/dates.guard.test.ts` (new, 2 tests)

**Interfaces:**
- Consumes: nothing from this plan. `backend/tests/fixtures/shared/` exists (2a Task 5).
- Produces (`frontend/src/lib/dates.ts`):
  - `type CalendarDate = { y: number; m: number; d: number }`
  - `parseIsoDate(s: string): CalendarDate | null`, `isValidDateIso(s: string): boolean`
  - `addDays(iso: string, n: number): string`, `weekday(iso: string): number` (0 = Sunday; both throw `RangeError` on an invalid date), `isSunday(iso: string): boolean`
  - `formatServiceDate(iso)` → "October 4, 2026", `formatLongDate(iso)` → "Sunday, October 4, 2026", `formatShortDate(iso)` → "October 4" (each "" for an invalid date)
  - `todayIn(tz: string | null | undefined, now?: Date): string`
  - `nextSunday(iso: string): string`, `isFirstSundayOfMonth(iso: string): boolean`, `inSupportedRange(iso: string): boolean`
  - Later users: T3 (`freshDraft`), T4 (`date-effects`), T5 (`status`), T6 (`rollForward`), T9 (`SummaryPanel`), 2c (the Date & readings step).

Counts after this task: frontend **230 passed in 36 files**; backend unchanged.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
git log --oneline -2
test ! -e frontend/src/lib/dates.ts && test ! -e backend/tests/fixtures/shared/next_sunday.json && echo "no T1 files yet"
grep -c '"zod"' frontend/package.json
(cd frontend && node -e 'console.log(require("zod/package.json").version)')
(cd frontend && npm test 2>&1 | tail -5)
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
.venv/bin/python -m pytest -q | tail -1
```

**Expected,** in order: nothing, or only `?? .claude/`; the plan commit `<sha> Plan: slice 2b frontend foundation (S slice 2; owner answers 2026-09-28)` above `864ebcd Merge pull request #21 from bbrown62450/claude/slice-2-plan-4q33le`; `no T1 files yet`; `0` (grep exits 1; zod is not a direct dependency yet); `4.6.5`; ` Test Files  34 passed (34)` and `      Tests  221 passed (221)`; `> tsc --noEmit` and `> eslint` with nothing after them; `971 passed, 9 skipped in <t>s`. If `node_modules` is missing, run `(cd frontend && npm ci)` first. Any other baseline: stop and ask.

- [ ] **Step 2 (agent): Add zod as a direct dependency (clarification 4)**

```bash
.venv/bin/python - <<'EOF'
from pathlib import Path
pkg = Path("frontend/package.json")
text = pkg.read_text(encoding="utf-8")
old = '"tw-animate-css": "^1.4.0"\n  },'
assert text.count(old) == 1, "package.json dependencies end has moved; add zod by hand"
pkg.write_text(text.replace(old, '"tw-animate-css": "^1.4.0",\n    "zod": "^4.6.5"\n  },'), encoding="utf-8")

lock = Path("frontend/package-lock.json")
text = lock.read_text(encoding="utf-8")
root = '        "tw-animate-css": "^1.4.0"\n      },'
assert text.count(root) == 1, "lockfile root dependencies have moved"
text = text.replace(root, '        "tw-animate-css": "^1.4.0",\n        "zod": "^4.6.5"\n      },')
entry = '    "node_modules/zod": {\n      "version": "4.6.5",\n'
start = text.index(entry)
end = text.index("\n    },", start)
block = text[start:end]
assert block.count('      "dev": true,\n') == 1, block
text = text[:start] + block.replace('      "dev": true,\n', "") + text[end:]
lock.write_text(text, encoding="utf-8")
print("zod added")
EOF
git diff --stat frontend/package.json frontend/package-lock.json
(cd frontend && npm ci --dry-run --ignore-scripts 2>&1 | tail -2)
(cd frontend && npm ls zod --depth=0 2>&1 | tail -1)
```

**Expected:** `zod added`; ` frontend/package-lock.json | 4 ++--`, ` frontend/package.json      | 3 ++-`, ` 2 files changed, 4 insertions(+), 3 deletions(-)`; the dry run ends `299 packages are looking for funding` / `  run \`npm fund\` for details` with no "can only install packages when your package.json and package-lock.json are in sync" error; `` `-- zod@4.6.5 ``. Do not run `npm install` (it rewrites the lockfile, clarification 4).

- [ ] **Step 3 (agent): Write the shared fixture**

Create `backend/tests/fixtures/shared/next_sunday.json`:

```json
{
  "_about": "nextSunday(from) in frontend/src/lib/dates.ts: the first Sunday strictly after `from` (a Sunday gives the following Sunday). TypeScript only (S Testing; F §5.3): the backend never computes it.",
  "cases": [
    {"from": "2026-09-25", "expected": "2026-09-27", "why": "a Friday"},
    {"from": "2026-09-26", "expected": "2026-09-27", "why": "a Saturday"},
    {"from": "2026-09-27", "expected": "2026-10-04", "why": "a Sunday gives the following Sunday"},
    {"from": "2026-12-31", "expected": "2027-01-03", "why": "across the year end"},
    {"from": "2028-02-28", "expected": "2028-03-05", "why": "across a leap day"}
  ]
}
```

- [ ] **Step 4 (agent): Write the failing tests**

Create `frontend/src/lib/dates.test.ts`:

```ts
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  addDays,
  formatLongDate,
  formatServiceDate,
  formatShortDate,
  inSupportedRange,
  isFirstSundayOfMonth,
  isSunday,
  isValidDateIso,
  nextSunday,
  parseIsoDate,
  todayIn,
  weekday,
} from "./dates";

// Shared with the backend fixtures folder (F §5.3); tests never run in the Vercel build.
const NEXT_SUNDAY = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/next_sunday.json", import.meta.url), "utf-8"),
) as { cases: { from: string; expected: string }[] };

describe("lib/dates", () => {
  it("nextSunday passes every case in shared/next_sunday.json", () => {
    expect(NEXT_SUNDAY.cases.length).toBeGreaterThanOrEqual(4);
    for (const { from, expected } of NEXT_SUNDAY.cases) {
      expect(nextSunday(from), from).toBe(expected);
    }
  });

  it("todayIn reads the calendar day in the church's zone and falls back to the browser's zone", () => {
    const now = new Date(Date.UTC(2026, 8, 27, 2, 30)); // 2026-09-27T02:30Z
    expect(todayIn("America/Los_Angeles", now)).toBe("2026-09-26");
    expect(todayIn("UTC", now)).toBe("2026-09-27");
    const browser = todayIn(undefined, now);
    expect(browser).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(todayIn("Not/A_Zone", now)).toBe(browser);
    expect(todayIn("", now)).toBe(browser);
    expect(todayIn(null, now)).toBe(browser);
  });

  it("formats service dates without zero padding, and invalid input as empty", () => {
    expect(formatServiceDate("2026-10-04")).toBe("October 4, 2026");
    expect(formatLongDate("2026-10-04")).toBe("Sunday, October 4, 2026");
    expect(formatLongDate("2026-09-29")).toBe("Tuesday, September 29, 2026");
    expect(formatShortDate("2026-10-04")).toBe("October 4");
    for (const bad of ["", "2026-10-4", "2026-13-01", "not a date"]) {
      expect(formatServiceDate(bad)).toBe("");
      expect(formatLongDate(bad)).toBe("");
      expect(formatShortDate(bad)).toBe("");
    }
  });

  it("isFirstSundayOfMonth is true only for a Sunday on days 1-7", () => {
    expect(isFirstSundayOfMonth("2026-10-04")).toBe(true);
    expect(isFirstSundayOfMonth("2026-10-11")).toBe(false);
    expect(isFirstSundayOfMonth("2026-10-01")).toBe(false); // a Thursday
    expect(isFirstSundayOfMonth("")).toBe(false);
  });

  it("validates ISO strings by the calendar, not the shape alone", () => {
    expect(parseIsoDate("2026-10-04")).toEqual({ y: 2026, m: 10, d: 4 });
    expect(isValidDateIso("2028-02-29")).toBe(true);
    for (const bad of ["", "2026-02-29", "2026-02-30", "2026-04-31", "2026-00-10", "2026-9-4",
                       "2026-09-04T00:00:00", " 2026-09-04", "20260904", "0"]) {
      expect(isValidDateIso(bad), bad).toBe(false);
    }
  });

  it("does calendar arithmetic across month, year and leap-day edges", () => {
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2028-03-01", -1)).toBe("2028-02-29");
    expect(addDays("2026-10-04", 0)).toBe("2026-10-04");
    expect(weekday("2026-10-04")).toBe(0);
    expect(weekday("2026-09-29")).toBe(2);
    expect(isSunday("2026-10-04")).toBe(true);
    expect(isSunday("2026-10-05")).toBe(false);
    expect(isSunday("")).toBe(false);
    expect(() => addDays("2026-02-30", 1)).toThrow(RangeError);
  });

  it("inSupportedRange accepts years 1900-2199 only", () => {
    expect(inSupportedRange("1900-01-01")).toBe(true);
    expect(inSupportedRange("2199-12-31")).toBe(true);
    expect(inSupportedRange("1899-12-31")).toBe(false);
    expect(inSupportedRange("2200-01-01")).toBe(false);
    expect(inSupportedRange("")).toBe(false);
  });
});
```

Create `frontend/src/lib/dates.guard.test.ts`:

```ts
import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * F acceptance 12 (F §4.10): no `new Date(` applied to a `YYYY-MM-DD` literal
 * or to an identifier ending in `date_iso` / `dateIso` anywhere in `src/`,
 * except `lib/dates.ts`, which owns date-only arithmetic.
 */
const SRC = fileURLToPath(new URL("..", import.meta.url));
const ALLOWED = new Set(["lib/dates.ts", "lib/dates.guard.test.ts"]);
const FORBIDDEN = /new\s+Date\(\s*(?:["'`]\d{4}-\d{2}-\d{2}["'`]|[\w$.?!\]\[]*?(?:date_iso|[dD]ateIso)\b)/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe("dates guard (F acceptance 12)", () => {
  it("the pattern catches the forbidden forms and allows timestamps", () => {
    for (const bad of [
      'new Date("2026-10-04")',
      "new Date('2026-10-04')",
      "new Date(`2026-10-04`)",
      "new Date(draft.readings.date_iso)",
      "new Date( dateIso )",
      "new Date(props.serviceDateIso)",
      "new Date(editing?.date_iso)",
    ]) {
      expect(FORBIDDEN.test(bad), bad).toBe(true);
    }
    for (const fine of ["new Date()", "new Date(0)", "new Date(Date.UTC(2026, 8, 27))", "new Date(updated_at)",
                        'new Date("2026-10-04T12:00:00Z")']) {
      expect(FORBIDDEN.test(fine), fine).toBe(false);
    }
  });

  it("no file in src/ outside lib/dates.ts builds a Date from a date-only value", () => {
    const offenders = sourceFiles(SRC)
      .map((path) => relative(SRC, path).split("\\").join("/"))
      .filter((rel) => !ALLOWED.has(rel))
      .filter((rel) => FORBIDDEN.test(readFileSync(join(SRC, rel), "utf-8")));
    expect(offenders).toEqual([]);
  });
});
```

- [ ] **Step 5 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/dates.test.ts src/lib/dates.guard.test.ts 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** ` FAIL  |unit| src/lib/dates.test.ts [ src/lib/dates.test.ts ]` with `Error: Cannot find module './dates' imported from …/frontend/src/lib/dates.test.ts`; the guard file passes (2 tests: nothing in `src/` offends yet). Then prove the guard can fail:

```bash
printf 'export const probe = new Date("2026-10-04");\n' > frontend/src/lib/guard-probe.ts
(cd frontend && npx vitest run src/lib/dates.guard.test.ts 2>&1 | grep -E "lib/guard-probe.ts|Tests ")
rm frontend/src/lib/guard-probe.ts
```

**Expected:** `AssertionError: expected [ 'lib/guard-probe.ts' ] to deeply equal []` and `Tests  1 failed | 1 passed (2)`; the probe file is removed.

- [ ] **Step 6 (agent): Write `lib/dates.ts`**

Create `frontend/src/lib/dates.ts`:

```ts
/**
 * Date-only values (F §4.10; S "lib/dates.ts"). A service date is a
 * `YYYY-MM-DD` string, and every helper here works on its calendar fields.
 * Nothing in `src/` may call `new Date("YYYY-MM-DD")` (it parses as UTC
 * midnight, the previous evening in US time zones); `dates.guard.test.ts`
 * scans for it. This file does its arithmetic on UTC calendar days.
 */

export type CalendarDate = { y: number; m: number; d: number };

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
] as const;

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] as const;

function daysInMonth(y: number, m: number): number {
  if (m === 2) return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28;
  return [4, 6, 9, 11].includes(m) ? 30 : 31;
}

/** The calendar fields of a real `YYYY-MM-DD` date, or null ("2026-02-30", "2026-9-4" and "" are null). */
export function parseIsoDate(s: string): CalendarDate | null {
  const match = ISO_DATE.exec(s);
  if (!match) return null;
  const [y, m, d] = [Number(match[1]), Number(match[2]), Number(match[3])];
  if (m < 1 || m > 12 || d < 1 || d > daysInMonth(y, m)) return null;
  return { y, m, d };
}

export function isValidDateIso(s: string): boolean {
  return parseIsoDate(s) !== null;
}

function pad(n: number, width: number): string {
  return String(n).padStart(width, "0");
}

function toIso({ y, m, d }: CalendarDate): string {
  return `${pad(y, 4)}-${pad(m, 2)}-${pad(d, 2)}`;
}

/** A UTC midnight for the calendar day; setUTCFullYear keeps years below 100 as written. */
function utcDay({ y, m, d }: CalendarDate): Date {
  const t = new Date(0);
  t.setUTCFullYear(y, m - 1, d);
  return t;
}

function fromUtcDay(t: Date): CalendarDate {
  return { y: t.getUTCFullYear(), m: t.getUTCMonth() + 1, d: t.getUTCDate() };
}

function mustParse(iso: string): CalendarDate {
  const parsed = parseIsoDate(iso);
  if (!parsed) throw new RangeError(`Not a YYYY-MM-DD date: ${JSON.stringify(iso)}`);
  return parsed;
}

/** `iso` moved by `n` calendar days (negative goes back). Throws on an invalid date. */
export function addDays(iso: string, n: number): string {
  const t = utcDay(mustParse(iso));
  t.setUTCDate(t.getUTCDate() + n);
  return toIso(fromUtcDay(t));
}

/** 0 = Sunday … 6 = Saturday. Throws on an invalid date. */
export function weekday(iso: string): number {
  return utcDay(mustParse(iso)).getUTCDay();
}

export function isSunday(iso: string): boolean {
  return isValidDateIso(iso) && weekday(iso) === 0;
}

/** "October 4, 2026"; "" for an invalid date. */
export function formatServiceDate(iso: string): string {
  const p = parseIsoDate(iso);
  return p ? `${MONTHS[p.m - 1]} ${p.d}, ${p.y}` : "";
}

/** "Sunday, October 4, 2026"; "" for an invalid date. */
export function formatLongDate(iso: string): string {
  return isValidDateIso(iso) ? `${WEEKDAYS[weekday(iso)]}, ${formatServiceDate(iso)}` : "";
}

/** "October 4"; "" for an invalid date. */
export function formatShortDate(iso: string): string {
  const p = parseIsoDate(iso);
  return p ? `${MONTHS[p.m - 1]} ${p.d}` : "";
}

function formatterFor(tz: string | null | undefined): Intl.DateTimeFormat {
  const options: Intl.DateTimeFormatOptions = { year: "numeric", month: "2-digit", day: "2-digit" };
  if (tz) {
    try {
      return new Intl.DateTimeFormat("en-CA", { ...options, timeZone: tz });
    } catch {
      // An unknown zone (RangeError): fall back to the browser's own zone (F §4.10).
    }
  }
  return new Intl.DateTimeFormat("en-CA", options);
}

/**
 * Today's date in `tz` as `YYYY-MM-DD`. A missing, empty or unknown zone falls
 * back to the browser's zone; callers pass `undefined` when the church
 * profile says `timezone_valid: false`.
 */
export function todayIn(tz: string | null | undefined, now: Date = new Date()): string {
  const parts = formatterFor(tz).formatToParts(now);
  const field = (type: Intl.DateTimeFormatPartTypes) => Number(parts.find((p) => p.type === type)?.value);
  return toIso({ y: field("year"), m: field("month"), d: field("day") });
}

/** The first Sunday strictly after `iso` (a Sunday gives the following Sunday). */
export function nextSunday(iso: string): string {
  return addDays(iso, 7 - weekday(iso));
}

/** A Sunday in the first seven days of its month (the communion default). */
export function isFirstSundayOfMonth(iso: string): boolean {
  const p = parseIsoDate(iso);
  return p !== null && weekday(iso) === 0 && p.d <= 7;
}

/** Years 1900–2199: the range the lectionary lookup accepts. */
export function inSupportedRange(iso: string): boolean {
  const p = parseIsoDate(iso);
  return p !== null && p.y >= 1900 && p.y <= 2199;
}
```

- [ ] **Step 7 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/dates.test.ts src/lib/dates.guard.test.ts 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | tail -5)
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** `Test Files  2 passed (2)`, `Tests  9 passed (9)`; the suite ` Test Files  36 passed (36)`, `      Tests  230 passed (230)`; `> tsc --noEmit` and `> eslint` with nothing after them; `git status` shows ` M frontend/package-lock.json`, ` M frontend/package.json`, `?? backend/tests/fixtures/shared/next_sunday.json`, `?? frontend/src/lib/dates.guard.test.ts`, `?? frontend/src/lib/dates.test.ts`, `?? frontend/src/lib/dates.ts` (and `?? .claude/` if present).

- [ ] **Step 8 (agent): Commit and back up**

```bash
git add frontend/package.json frontend/package-lock.json backend/tests/fixtures/shared/next_sunday.json frontend/src/lib/dates.ts frontend/src/lib/dates.test.ts frontend/src/lib/dates.guard.test.ts
git commit -m "Dates: date-only helpers, the next-Sunday fixture and the new Date guard (F §4.10, acceptance 12; S lib/dates.ts)" -m "Adds zod as a direct dependency (two lockfile lines; npm install would
rewrite the lockfile), lib/dates.ts (calendar-field parsing, arithmetic
and formatting, todayIn with the browser-zone fallback, nextSunday,
isFirstSundayOfMonth, inSupportedRange), backend/tests/fixtures/shared/
next_sunday.json, and a guard test that fails on new Date() applied to a
date-only value anywhere in src/ outside lib/dates.ts. Frontend 221 -> 230
tests in 36 files.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** one commit, 6 files changed; the push prints `<old>..<new>  claude/slice-2-plan-4q33le -> claude/slice-2-plan-4q33le`.

**Review checkpoint (T1):** the reviewer checks the lockfile diff is exactly the zod lines, `dates.ts` never builds a `Date` from a date-only string (it uses `setUTCFullYear` on `new Date(0)`), the guard's pattern list, and the counts.

### Task 2: `lib/scripture-refs.ts`, the TypeScript port that passes the shared fixture (S "lib/scripture-refs.ts"; F §5.3; spec decision 9; AC8 TypeScript half)

A line-for-line port of `backend/scripture_refs.py` above its "Fetch only" line: the 84-book table with the 2a-build aliases (revelations, mat, rm, php, jdg, eccles), `normalizeBookText`, `cleanLines`, `splitAlternatives`, `splitBook`, `classify`, `isNtRef`, `expandRefOptions`, `pickerOptions`, `resolveReadings` (the automatic OT skips the NT pick, 2a build), `defaultReadingPair`, `defaultNtRef`, and `scriptureKey`, which carries a private copy of Python's `normalize_for_fetch` (the other fetch-only helpers stay in Python, S). The test reads `backend/tests/fixtures/shared/scripture_refs.json` with `fs` and runs every section; the fixture keeps Python's snake_case pair keys, which the test maps (P2a clarification 40).

**Files:**
- Create: `frontend/src/lib/scripture-refs.ts`
- Test: `frontend/src/lib/scripture-refs.test.ts` (new, 10 tests)

**Interfaces:**
- Consumes: `backend/tests/fixtures/shared/scripture_refs.json` (2a Task 5 and its 2a-build update).
- Produces (`frontend/src/lib/scripture-refs.ts`):
  - `type Testament = "ot" | "psalm" | "nt"`, `type Classification = Testament | "unknown"`, `type Book = { name; testament; aliases: readonly string[] }`, `BOOKS: readonly Book[]`
  - `normalizeBookText(s)`, `cleanLines(lines): string[]`, `splitAlternatives(ref): string[]`, `splitBook(ref): { book: Book; rest: string } | null`, `classify(ref): Classification`, `isNtRef(ref): boolean`
  - `expandRefOptions(refs): string[]`, `pickerOptions(scriptures): { ot: string[]; nt: string[] }`
  - `type ReadingPair = { ot: string | null; nt: string | null; otAuto: boolean; ntAuto: boolean }`, `resolveReadings(scriptures, otPick?, ntPick?): ReadingPair`, `defaultReadingPair(scriptures)`, `defaultNtRef(scriptures): string | null`
  - `scriptureKey(ref): string`
  - Later users: T4 (`normalizePicks`, `effectivePicks`, set comparisons), T5 (`status`, `mapping`), T9 (`SummaryPanel`), 2c (badges and pickers), slice 3 (`defaultNtRef`), 5a (`resolveReadings` in `docReadings`).

Counts after this task: frontend **240 passed in 37 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/scripture-refs.ts && echo "no T2 files yet"
.venv/bin/python -c "import json; d = json.load(open('backend/tests/fixtures/shared/scripture_refs.json')); print({k: len(v) for k, v in d.items() if isinstance(v, list)})"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T2 files yet`; `{'books': 84, 'split_alternatives': 9, 'split_book': 40, 'classify': 50, 'is_nt_ref': 5, 'expand_ref_options': 5, 'clean_lines': 3, 'picker_options': 4, 'resolve_readings': 23, 'default_reading_pair': 3, 'default_nt_ref': 4, 'scripture_key': 12}` (if 2a's fixture has grown, the test still loops over every case: note the new numbers and go on); `Test Files  36 passed (36)`, `Tests  230 passed (230)`.

- [ ] **Step 2 (agent): Write the failing test**

Create `frontend/src/lib/scripture-refs.test.ts`:

```ts
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  BOOKS,
  classify,
  cleanLines,
  defaultNtRef,
  defaultReadingPair,
  expandRefOptions,
  isNtRef,
  normalizeBookText,
  pickerOptions,
  resolveReadings,
  scriptureKey,
  splitAlternatives,
  splitBook,
  type ReadingPair,
} from "./scripture-refs";

/**
 * AC8, TypeScript half (F §5.3): the shared fixture that backend
 * `test_scripture_refs.py` also runs. Each section loops inside one test, so
 * the count stays stable when 5a adds `resolve_readings` cases.
 */
type Pair = { ot: string | null; nt: string | null; ot_auto: boolean; nt_auto: boolean };
type Fixture = {
  _about: Record<string, string>;
  books: { name: string; testament: string; aliases: string[] }[];
  split_alternatives: { ref: string; expected: string[] }[];
  split_book: { ref: string; expected: { book: string; rest: string } | null }[];
  classify: { ref: string; expected: string }[];
  is_nt_ref: { ref: string; expected: boolean }[];
  expand_ref_options: { refs: string[]; expected: string[] }[];
  clean_lines: { lines: string[]; expected: string[] }[];
  picker_options: { scriptures: string[]; expected: { ot: string[]; nt: string[] } }[];
  resolve_readings: { name: string; scriptures: string[]; ot_pick: string; nt_pick: string; expected: Pair }[];
  default_reading_pair: { scriptures: string[]; expected: Pair }[];
  default_nt_ref: { scriptures: string[]; expected: string | null }[];
  scripture_key: { ref: string; expected: string }[];
};

const FIXTURE = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/scripture_refs.json", import.meta.url), "utf-8"),
) as Fixture;

/** The fixture keeps Python's snake_case keys (2a clarification 40). */
function camel(p: Pair): ReadingPair {
  return { ot: p.ot, nt: p.nt, otAuto: p.ot_auto, ntAuto: p.nt_auto };
}

describe("lib/scripture-refs against shared/scripture_refs.json", () => {
  it("has every section the Python suite runs", () => {
    for (const section of ["books", "split_alternatives", "split_book", "classify", "is_nt_ref",
                           "expand_ref_options", "clean_lines", "picker_options", "resolve_readings",
                           "default_reading_pair", "default_nt_ref", "scripture_key"] as const) {
      expect(FIXTURE[section].length, section).toBeGreaterThan(0);
      expect(FIXTURE._about[section], section).toBeTypeOf("string");
    }
  });

  it("BOOKS equals the fixture's books, in order, with normalized aliases", () => {
    expect(BOOKS.map((b) => ({ name: b.name, testament: b.testament, aliases: [...b.aliases] }))).toEqual(
      FIXTURE.books,
    );
    for (const b of BOOKS) for (const alias of b.aliases) expect(normalizeBookText(alias)).toBe(alias);
  });

  it("splitAlternatives", () => {
    for (const c of FIXTURE.split_alternatives) expect(splitAlternatives(c.ref), c.ref).toEqual(c.expected);
  });

  it("splitBook", () => {
    for (const c of FIXTURE.split_book) {
      const hit = splitBook(c.ref);
      expect(hit === null ? null : { book: hit.book.name, rest: hit.rest }, c.ref).toEqual(c.expected);
    }
  });

  it("classify and isNtRef", () => {
    for (const c of FIXTURE.classify) expect(classify(c.ref), c.ref).toBe(c.expected);
    for (const c of FIXTURE.is_nt_ref) expect(isNtRef(c.ref), c.ref).toBe(c.expected);
  });

  it("expandRefOptions and cleanLines", () => {
    for (const c of FIXTURE.expand_ref_options) expect(expandRefOptions(c.refs), c.refs.join("|")).toEqual(c.expected);
    for (const c of FIXTURE.clean_lines) expect(cleanLines(c.lines), c.lines.join("|")).toEqual(c.expected);
  });

  it("pickerOptions", () => {
    for (const c of FIXTURE.picker_options) {
      expect(pickerOptions(c.scriptures), c.scriptures.join("|")).toEqual(c.expected);
    }
  });

  it("resolveReadings, including the mixed and stale-pick cases; an automatic NT is never a Psalm", () => {
    for (const c of FIXTURE.resolve_readings) {
      const got = resolveReadings(c.scriptures, c.ot_pick, c.nt_pick);
      expect(got, c.name).toEqual(camel(c.expected));
      if (got.ntAuto && got.nt !== null) expect(isNtRef(splitAlternatives(got.nt)[0]), c.name).toBe(true);
    }
    expect(FIXTURE.resolve_readings.some((c) => c.name.startsWith("S mixed:"))).toBe(true);
    expect(FIXTURE.resolve_readings.some((c) => c.name.startsWith("S stale:"))).toBe(true);
  });

  it("defaultReadingPair and defaultNtRef", () => {
    for (const c of FIXTURE.default_reading_pair) {
      expect(defaultReadingPair(c.scriptures), c.scriptures.join("|")).toEqual(camel(c.expected));
    }
    for (const c of FIXTURE.default_nt_ref) expect(defaultNtRef(c.scriptures), c.scriptures.join("|")).toBe(c.expected);
  });

  it("scriptureKey", () => {
    for (const c of FIXTURE.scripture_key) expect(scriptureKey(c.ref), c.ref).toBe(c.expected);
  });
});
```

- [ ] **Step 3 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/lib/scripture-refs.test.ts 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** ` FAIL  |unit| src/lib/scripture-refs.test.ts [ src/lib/scripture-refs.test.ts ]`, `Error: Cannot find module './scripture-refs' imported from …`, `Tests  no tests`.

- [ ] **Step 4 (agent): Write the port**

Create `frontend/src/lib/scripture-refs.ts`. Port notes: Python's `(-len(key), key)` sort is `b.length - a.length` then the plain string order; `re.sub(r"\s+", …)` is `/\s+/g`; `s.replace(".", "")` is `split(".").join("")`; the lookbehinds `(?<=\d)` are ES2018 regex, which Node and every browser Next 16 supports (TypeScript accepts them at this `target`).

```ts
/**
 * Scripture references: the book table, the OT/NT classifier, the bulletin
 * pickers and the one bulletin-reading rule (S "lib/scripture-refs.ts";
 * spec decision 9; F §5.3).
 *
 * A line-for-line port of `backend/scripture_refs.py` (everything above its
 * "Fetch only" line, plus the private normalization `scriptureKey` needs).
 * Both ports run `backend/tests/fixtures/shared/scripture_refs.json`, which is
 * authoritative: change a case there first, then both ports.
 */

export type Testament = "ot" | "psalm" | "nt";
export type Classification = Testament | "unknown";

/** A canonical book; aliases are stored normalized (`normalizeBookText`). */
export type Book = { name: string; testament: Testament; aliases: readonly string[] };

function book(name: string, testament: Testament, aliases: readonly string[] = []): Book {
  return { name, testament, aliases };
}

export const BOOKS: readonly Book[] = [
  // Old Testament
  book("Genesis", "ot", ["gen"]),
  book("Exodus", "ot", ["ex", "exod"]),
  book("Leviticus", "ot", ["lev"]),
  book("Numbers", "ot", ["num"]),
  book("Deuteronomy", "ot", ["deut"]),
  book("Joshua", "ot", ["josh"]),
  book("Judges", "ot", ["jdg", "judg"]),
  book("Ruth", "ot"),
  book("1 Samuel", "ot", ["1 sam"]),
  book("2 Samuel", "ot", ["2 sam"]),
  book("1 Kings", "ot", ["1 kgs"]),
  book("2 Kings", "ot", ["2 kgs"]),
  book("1 Chronicles", "ot", ["1 chr", "1 chron"]),
  book("2 Chronicles", "ot", ["2 chr", "2 chron"]),
  book("Ezra", "ot"),
  book("Nehemiah", "ot", ["neh"]),
  book("Esther", "ot", ["esth"]),
  book("Job", "ot"),
  book("Psalms", "psalm", ["ps", "psa", "psalm", "pss"]),
  book("Proverbs", "ot", ["prov"]),
  book("Ecclesiastes", "ot", ["eccl", "eccles"]),
  book("Song of Songs", "ot", ["canticles", "song", "song of solomon"]),
  book("Isaiah", "ot", ["isa"]),
  book("Jeremiah", "ot", ["jer"]),
  book("Lamentations", "ot", ["lam"]),
  book("Ezekiel", "ot", ["ezek"]),
  book("Daniel", "ot", ["dan"]),
  book("Hosea", "ot", ["hos"]),
  book("Joel", "ot"),
  book("Amos", "ot"),
  book("Obadiah", "ot", ["obad"]),
  book("Jonah", "ot"),
  book("Micah", "ot", ["mic"]),
  book("Nahum", "ot", ["nah"]),
  book("Habakkuk", "ot", ["hab"]),
  book("Zephaniah", "ot", ["zeph"]),
  book("Haggai", "ot", ["hag"]),
  book("Zechariah", "ot", ["zech"]),
  book("Malachi", "ot", ["mal"]),
  // Deuterocanon: "ot", except Psalm 151, which is a psalm
  book("Tobit", "ot", ["tb", "tob"]),
  book("Judith", "ot", ["jdt", "jth"]),
  book("Additions to Esther", "ot", ["add esth"]),
  book("Wisdom of Solomon", "ot", ["wis", "wisdom", "ws"]),
  book("Sirach", "ot", ["ecclesiasticus", "ecclus", "sir"]),
  book("Baruch", "ot", ["bar"]),
  book("Letter of Jeremiah", "ot", ["ep jer"]),
  book("Song of the Three", "ot", ["pr azar", "prayer of azariah", "song of the three jews", "song of the three young men"]),
  book("Susanna", "ot", ["sus"]),
  book("Bel and the Dragon", "ot", ["bel"]),
  book("1 Maccabees", "ot", ["1 macc", "1 mc"]),
  book("2 Maccabees", "ot", ["2 macc", "2 mc"]),
  book("3 Maccabees", "ot", ["3 macc", "3 mc"]),
  book("4 Maccabees", "ot", ["4 macc", "4 mc"]),
  book("1 Esdras", "ot", ["1 esd"]),
  book("2 Esdras", "ot", ["2 esd"]),
  book("Prayer of Manasseh", "ot", ["pr man"]),
  book("Psalm 151", "psalm"),
  // New Testament
  book("Matthew", "nt", ["mat", "matt", "mt"]),
  book("Mark", "nt", ["mk"]),
  book("Luke", "nt", ["lk"]),
  book("John", "nt", ["jn"]),
  book("Acts", "nt"),
  book("Romans", "nt", ["rm", "rom"]),
  book("1 Corinthians", "nt", ["1 cor"]),
  book("2 Corinthians", "nt", ["2 cor"]),
  book("Galatians", "nt", ["gal"]),
  book("Ephesians", "nt", ["eph"]),
  book("Philippians", "nt", ["phil", "php"]),
  book("Colossians", "nt", ["col"]),
  book("1 Thessalonians", "nt", ["1 thess"]),
  book("2 Thessalonians", "nt", ["2 thess"]),
  book("1 Timothy", "nt", ["1 tim"]),
  book("2 Timothy", "nt", ["2 tim"]),
  book("Titus", "nt", ["tit"]),
  book("Philemon", "nt", ["philem", "phlm"]),
  book("Hebrews", "nt", ["heb"]),
  book("James", "nt", ["jas"]),
  book("1 Peter", "nt", ["1 pet"]),
  book("2 Peter", "nt", ["2 pet"]),
  book("1 John", "nt", ["1 jn"]),
  book("2 John", "nt", ["2 jn"]),
  book("3 John", "nt", ["3 jn"]),
  book("Jude", "nt"),
  book("Revelation", "nt", ["rev", "revelations"]),
];

const ORDINAL_PREFIX = /^(iii|ii|iv|i|first|second|third|fourth|1st|2nd|3rd|4th) /;
const ORDINAL_DIGIT: Record<string, string> = {
  i: "1", ii: "2", iii: "3", iv: "4",
  first: "1", second: "2", third: "3", fourth: "4",
  "1st": "1", "2nd": "2", "3rd": "3", "4th": "4",
};

/**
 * Lower-case; drop a leading "*" and whitespace; remove "."; collapse spaces;
 * map a roman or ordinal prefix followed by a space to 1-4; then put a space
 * after a leading 1-4 glued to a letter ("1john" → "1 john").
 */
export function normalizeBookText(s: string): string {
  let out = s.toLowerCase();
  out = out.replace(/^\s*\*?\s*/, "");
  out = out.split(".").join("");
  out = out.replace(/\s+/g, " ").trim();
  out = out.replace(ORDINAL_PREFIX, (_match, prefix: string) => `${ORDINAL_DIGIT[prefix]} `);
  out = out.replace(/^([1-4])(?=[a-z])/, "$1 ");
  return out;
}

/** Every lookup key (the normalized name and each alias), longest first; a key naming two books throws at import. */
function aliasIndex(): readonly (readonly [string, Book])[] {
  const index = new Map<string, Book>();
  for (const b of BOOKS) {
    for (const key of [normalizeBookText(b.name), ...b.aliases]) {
      const existing = index.get(key);
      if (existing) throw new Error(`alias ${JSON.stringify(key)} is used by ${existing.name} and ${b.name}`);
      index.set(key, b);
    }
  }
  return [...index.entries()].sort(([a], [b]) => b.length - a.length || (a < b ? -1 : a > b ? 1 : 0));
}

const ALIASES = aliasIndex();

/** Trim each line and drop the blank ones. */
export function cleanLines(lines: readonly string[]): string[] {
  return lines.map((line) => line.trim()).filter((line) => line !== "");
}

/** Split on " or " (any case, any whitespace around it) and trim; empty pieces are dropped. */
export function splitAlternatives(ref: string): string[] {
  return ref
    .split(/\s+or\s+/i)
    .map((piece) => piece.trim())
    .filter((piece) => piece !== "");
}

/**
 * The longest book name or alias at the start of the normalized text,
 * followed by the end, a space or a digit: the canonical book and the rest of
 * the normalized text, trimmed. Null when no book matches.
 */
export function splitBook(ref: string): { book: Book; rest: string } | null {
  const text = normalizeBookText(ref);
  for (const [key, b] of ALIASES) {
    if (text.startsWith(key)) {
      const after = text.slice(key.length);
      if (after === "" || after[0] === " " || /[0-9]/.test(after[0])) {
        return { book: b, rest: after.trim() };
      }
    }
  }
  return null;
}

/** The testament of one alternative's book, or "unknown". */
export function classify(ref: string): Classification {
  return splitBook(ref)?.book.testament ?? "unknown";
}

export function isNtRef(ref: string): boolean {
  return classify(ref) === "nt";
}

/** Clean the lines, expand every alternative, and de-duplicate in first-seen order. */
export function expandRefOptions(refs: readonly string[]): string[] {
  const out: string[] = [];
  for (const line of cleanLines(refs)) {
    for (const alt of splitAlternatives(line)) {
      if (!out.includes(alt)) out.push(alt);
    }
  }
  return out;
}

/** The two bulletin pickers: "nt" holds the NT options; "ot" everything else (ot, psalm and unknown). */
export function pickerOptions(scriptures: readonly string[]): { ot: string[]; nt: string[] } {
  const options = expandRefOptions(scriptures);
  return {
    ot: options.filter((o) => classify(o) !== "nt"),
    nt: options.filter((o) => classify(o) === "nt"),
  };
}

export type ReadingPair = { ot: string | null; nt: string | null; otAuto: boolean; ntAuto: boolean };

function firstAlternativeIsNt(line: string): boolean {
  const alternatives = splitAlternatives(line);
  return alternatives.length > 0 && isNtRef(alternatives[0]);
}

/**
 * The only bulletin-reading rule (spec decision 9). A pick counts only when it
 * is one of the current options for its side; otherwise that side is
 * automatic. The automatic OT is the first line that is not the NT pick; the
 * automatic NT is the first line other than the effective OT whose first
 * alternative is NT, so a Psalm is never the automatic NT. Lines are returned
 * as written.
 */
export function resolveReadings(
  scriptures: readonly string[],
  otPick: string | null = "",
  ntPick: string | null = "",
): ReadingPair {
  const entries = cleanLines(scriptures);
  const options = pickerOptions(entries);
  let ot = (otPick ?? "").trim();
  if (!options.ot.includes(ot)) ot = "";
  let nt = (ntPick ?? "").trim();
  if (!options.nt.includes(nt)) nt = "";
  const effectiveOt = ot || (entries.find((e) => e !== nt) ?? null);
  const effectiveNt = nt || (entries.find((e) => e !== effectiveOt && firstAlternativeIsNt(e)) ?? null);
  return { ot: effectiveOt, nt: effectiveNt, otAuto: !ot, ntAuto: !nt };
}

/** resolveReadings with no picks. */
export function defaultReadingPair(scriptures: readonly string[]): ReadingPair {
  return resolveReadings(scriptures, "", "");
}

/** The automatic NT reading (slice 3's hymn matching). */
export function defaultNtRef(scriptures: readonly string[]): string | null {
  return defaultReadingPair(scriptures).nt;
}

/** Python's `normalize_for_fetch`, used here only to build comparison keys. */
function normalizeForKey(ref: string): string {
  let s = ref.replace(/^\s*\*\s*/, "");
  s = s.replace(/[–—]/g, "-");
  s = s.replace(/(?<=\d)[A-Za-z](?![A-Za-z])/g, "");
  s = s.replace(/[()]/g, "");
  s = s.replace(/(?<=\d)\s+(?=\d)/g, ", ");
  s = s.replace(/,(\s*,)+/g, ",");
  return s.replace(/\s+/g, " ").trim();
}

/** A comparison key: equal keys mean the same passage ("Luke 2:1-14 (15-20)" = "Luke 2:1-14, (15-20)"). */
export function scriptureKey(ref: string): string {
  return normalizeForKey(ref).toLowerCase().replace(/[\s,.()]/g, "");
}
```

- [ ] **Step 5 (agent): Run the test, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/scripture-refs.test.ts 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** `Tests  10 passed (10)`; `Test Files  37 passed (37)`, `Tests  240 passed (240)`; `> tsc --noEmit`, `> eslint`, nothing after. A fixture case that fails names its ref in the message (the second argument of `expect`): fix the port, never the fixture (it is authoritative and shared with the backend).

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/lib/scripture-refs.ts frontend/src/lib/scripture-refs.test.ts
git commit -m "Scripture refs: the TypeScript port passes the shared fixture (F §5.3; S lib/scripture-refs.ts; AC8)" -m "Ports backend/scripture_refs.py above its fetch-only helpers: the book
table with the 2a-build aliases, the classifier, the bulletin pickers,
resolveReadings (a Psalm is never the automatic NT; the automatic OT skips
the NT pick) and scriptureKey. The test runs every section of
backend/tests/fixtures/shared/scripture_refs.json. Frontend 230 -> 240.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T2):** the reviewer diffs `BOOKS` against `backend/scripture_refs.py` (the test also pins it against the fixture), and checks that `resolveReadings` mirrors the Python lines 1:1 (pick validity, the OT skipping the NT pick, the effective-OT comparison on whole lines).

### Task 3: The draft schema, the fresh draft and migrations (F §4.6 "Shape", "Fresh draft", "Versioning"; S "Draft store" `schema.ts`, `freshDraft`, `migrate.ts`; clarifications 5, 7, 32)

`schema.ts` is the zod schema of `DraftV1` (F §4.6 without 5a's two fields, clarification 5), with strings bounded at 20 000 and dates checked by `isValidDateIso`, plus `freshDraft` and the two storage keys. `migrate.ts` turns stored text back into a draft: JSON, then `migrate` through the (empty) `migrations` table, then zod, then an owner check (clarification 7); every failure is one `DraftRestoreError`, which the store (T6) turns into the backup, the fresh draft and the toast. The API type aliases and the test builders every later draft test uses arrive here too.

**Files:**
- Modify: `frontend/src/lib/api/types.ts` (four aliases), `frontend/src/test/fixtures/index.ts` (`churchProfile`, `DRAFT_NOW`, `testDraft`)
- Create: `frontend/src/lib/draft/schema.ts`, `frontend/src/lib/draft/migrate.ts`
- Test: `frontend/src/lib/draft/schema.test.ts` (new, 4 tests), `frontend/src/lib/draft/migrate.test.ts` (new, 3 tests)

**Interfaces:**
- Consumes: T1 `isFirstSundayOfMonth`, `isValidDateIso`, `nextSunday`, `todayIn`; `zod` (T1); `components["schemas"]` in `frontend/src/lib/api/schema.d.ts` (2a).
- Produces:
  - `frontend/src/lib/api/types.ts`: `ChurchProfile` (`ChurchProfileOut`), `Lectionary` (`LectionaryOut`), `ReadingSet` (`ReadingSetOut`), `Translations` (`TranslationsOut`).
  - `frontend/src/lib/draft/schema.ts`: `DRAFT_VERSION = 1`; `STEP_IDS`, `type StepId = "readings" | "hymns" | "liturgy" | "review"`; `SLOTS`, `type Slot`; `SECTION_KEYS` (the 8 in F's order), `type SectionKey`; `type HymnPick`, `type LiturgyCard`; `draftV1Schema`, `type DraftV1`, `type DraftReadings`; `type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean }`; `churchZone(church): string | undefined`; `freshDraft({ church, user, now? }): DraftV1`; `draftKey(userId, churchId)` → `wsb:draft:{userId}:{churchId}`; `corruptDraftKey(userId, churchId)` → `wsb:draft-corrupt:{userId}:{churchId}`.
  - `frontend/src/lib/draft/migrate.ts`: `type StoredDraft`, `type Migration`, `migrations` (empty; 5a adds `1`), `class DraftRestoreError`, `migrate(raw, table?, target?)`, `parseStoredDraft(text, { userId, churchId }, table?, target?): DraftV1`.
  - `frontend/src/test/fixtures/index.ts`: `churchProfile(overrides?)` (Grace, `America/New_York`, valid, WEB), `DRAFT_NOW` (Tuesday 2026-09-29 16:00 UTC, noon in New York), `testDraft(recipe?)` (Pat's fresh draft for Grace at `DRAFT_NOW`: dated 2026-10-04, a first Sunday).
  - Later users: every later task; 5a (`DRAFT_VERSION`, `migrations`, the two new fields).

Counts after this task: frontend **247 passed in 39 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/draft && echo "no draft folder yet"
grep -c "ChurchProfileOut: {" frontend/src/lib/api/schema.d.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no draft folder yet`; `1`; `Test Files  37 passed (37)`, `Tests  240 passed (240)`.

- [ ] **Step 2 (agent): Add the API type aliases**

Append to `frontend/src/lib/api/types.ts` (after `CreateChurchBody`, one blank line before):

```ts
/** `GET /church` (slice 2a): `ChurchOut` plus the profile fields. `/me`'s church items stay `Church`. */
export type ChurchProfile = components["schemas"]["ChurchProfileOut"];
/** `GET /lectionary/readings?date=` (slice 2a): the reading sets for exactly that date. */
export type Lectionary = components["schemas"]["LectionaryOut"];
export type ReadingSet = components["schemas"]["ReadingSetOut"];
/** `GET /translations` (slice 2a). */
export type Translations = components["schemas"]["TranslationsOut"];
```

- [ ] **Step 3 (agent): Add the test builders**

In `frontend/src/test/fixtures/index.ts`, replace the two import lines

```ts
import type { InviteAccepted, InvitePreview } from "@/lib/api/types";
import type { Church, Me } from "@/lib/church";
```

with

```ts
import type { ChurchProfile, InviteAccepted, InvitePreview } from "@/lib/api/types";
import type { Church, Me } from "@/lib/church";
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";
```

and append at the end of the file (one blank line before):

```ts
// --- slice 2b: the church profile, drafts and lectionary answers ------------------

/** `GET /church` for Grace (slice 2a's `ChurchProfileOut`): New York, WEB. */
export function churchProfile(overrides: Partial<ChurchProfile> = {}): ChurchProfile {
  return {
    ...church(),
    timezone: "America/New_York",
    timezone_valid: true,
    bible_translation: null,
    effective_translation: "web",
    effective_translation_label: "World English Bible (WEB)",
    ...overrides,
  };
}

/** Tuesday, September 29, 2026 at noon in New York: the next Sunday is October 4 (a first Sunday). */
export const DRAFT_NOW = new Date(Date.UTC(2026, 8, 29, 16, 0));

/** Pat's fresh draft for Grace at `DRAFT_NOW`, then `recipe` applied (the recipe may return a new object). */
export function testDraft(recipe: (d: DraftV1) => DraftV1 = (d) => d): DraftV1 {
  return recipe(freshDraft({ church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW }));
}
```

(`typecheck` fails until Step 6 creates `schema.ts`; that is expected.)

- [ ] **Step 4 (agent): Write the failing tests**

Create `frontend/src/lib/draft/schema.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { nextSunday, todayIn } from "@/lib/dates";
import { churchProfile, testDraft, USER_ID } from "@/test/fixtures";

import { corruptDraftKey, draftKey, draftV1Schema, DRAFT_VERSION, freshDraft, SECTION_KEYS } from "./schema";

describe("draft schema and freshDraft (F §4.6)", () => {
  it("a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults", () => {
    const d = testDraft();
    expect(DRAFT_VERSION).toBe(1);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 1,
      user_id: USER_ID,
      church_id: churchProfile().id,
      created_at: "2026-09-29T16:00:00.000Z",
      updated_at: "2026-09-29T16:00:00.000Z",
      last_step: "readings",
      editing: null,
      saved_fingerprint: null,
      readings: {
        date_iso: "2026-10-04",
        date_origin: "default",
        reading_set: null,
        fields_origin: "empty",
        occasion: "",
        scriptures: [],
        selected_ot_ref: "",
        selected_nt_ref: "",
        translation: null,
      },
      hymns: {
        hymnal: null,
        exclude_recent: true,
        slots: { opening: null, response: null, closing: null },
        alternatives: null,
      },
      liturgy: { sermon_title: "", include_communion: true, communion_origin: "default", custom_elements: [] },
    });
    expect(d.save_key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(testDraft().save_key).not.toBe(d.save_key);
    for (const key of SECTION_KEYS) {
      expect(d.liturgy.cards[key], key).toEqual({
        enabled: key !== "prayers_of_the_people",
        text: "",
        origin: key === "benediction" ? "default" : "empty",
      });
    }
  });

  it("uses the church's zone, strictly after today, and the browser's zone when the zone is not valid", () => {
    const now = new Date(Date.UTC(2026, 9, 4, 2, 30)); // Sat 22:30 in New York, Sun 02:30 UTC
    const user = { id: USER_ID };
    expect(freshDraft({ church: churchProfile(), user, now }).readings.date_iso).toBe("2026-10-04");
    expect(freshDraft({ church: churchProfile({ timezone: "UTC" }), user, now }).readings.date_iso).toBe(
      "2026-10-11",
    );
    const invalid = churchProfile({ timezone: "Eastern", timezone_valid: false });
    expect(freshDraft({ church: invalid, user, now }).readings.date_iso).toBe(nextSunday(todayIn(undefined, now)));
    const later = new Date(Date.UTC(2026, 9, 6, 16, 0)); // Tuesday October 6 → Sunday October 11
    expect(freshDraft({ church: churchProfile(), user, now: later }).liturgy.include_communion).toBe(false);
  });

  it("accepts an empty date and generous strings, and rejects impossible values", () => {
    const d = testDraft();
    expect(draftV1Schema.safeParse({ ...d, readings: { ...d.readings, date_iso: "" } }).success).toBe(true);
    const long = "x".repeat(20_000);
    expect(draftV1Schema.safeParse({ ...d, readings: { ...d.readings, occasion: long } }).success).toBe(true);
    for (const bad of [
      { ...d, readings: { ...d.readings, date_iso: "2026-02-30" } },
      { ...d, readings: { ...d.readings, occasion: `${long}x` } },
      { ...d, last_step: "summary" },
      { ...d, version: 2 },
      { ...d, readings: { ...d.readings, fields_origin: "typed" } },
      { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: undefined } } },
    ]) {
      expect(draftV1Schema.safeParse(bad).success).toBe(false);
    }
  });

  it("keys drafts by user and church", () => {
    expect(draftKey("u1", "c1")).toBe("wsb:draft:u1:c1");
    expect(corruptDraftKey("u1", "c1")).toBe("wsb:draft-corrupt:u1:c1");
  });
});
```

Create `frontend/src/lib/draft/migrate.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { CHURCH_IDS, churchProfile, testDraft, USER_ID } from "@/test/fixtures";

import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";

const OWNER = { userId: USER_ID, churchId: churchProfile().id };

describe("draft migrate and parseStoredDraft (F §4.6 Versioning)", () => {
  it("round-trips a stored draft", () => {
    const d = testDraft();
    expect(migrations).toEqual({});
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
  });

  it("rejects corrupt JSON, invalid data, a missing or future version, and another owner's draft", () => {
    const d = testDraft();
    const cases: [string, string][] = [
      ["corrupt JSON", "{not json"],
      ["not an object", "[1, 2]"],
      ["null", "null"],
      ["no version", JSON.stringify({ ...d, version: undefined })],
      ["version 0", JSON.stringify({ ...d, version: 0 })],
      ["a future version", JSON.stringify({ ...d, version: 2 })],
      ["schema-invalid", JSON.stringify({ ...d, readings: { ...d.readings, scriptures: "Psalm 23" } })],
      ["another user", JSON.stringify({ ...d, user_id: "someone-else" })],
      ["another church", JSON.stringify({ ...d, church_id: CHURCH_IDS.hope })],
    ];
    for (const [name, text] of cases) {
      expect(() => parseStoredDraft(text, OWNER), name).toThrow(DraftRestoreError);
    }
  });

  it("runs the migrations step by step up to the target, and a missing step is an error", () => {
    const seen: number[] = [];
    const table: Record<number, Migration> = {
      1: (draft) => {
        seen.push(draft.version as number);
        return { ...draft, added_in_2: null };
      },
      2: (draft) => {
        seen.push(draft.version as number);
        return { ...draft, added_in_3: [] };
      },
    };
    expect(migrate({ version: 1, kept: "yes" }, table, 3)).toEqual({
      version: 3,
      kept: "yes",
      added_in_2: null,
      added_in_3: [],
    });
    expect(seen).toEqual([1, 2]);
    expect(migrate({ version: 3 }, table, 3)).toEqual({ version: 3 });
    expect(() => migrate({ version: 1 }, { 2: table[2] }, 3)).toThrow(DraftRestoreError);
  });
});
```

- [ ] **Step 5 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** both files `FAIL` with `Error: Cannot find module '@/lib/draft/schema'` (the fixtures import it first) or `'./schema'` / `'./migrate'`; `Tests  no tests`.

- [ ] **Step 6 (agent): Write `schema.ts` and `migrate.ts`**

Create `frontend/src/lib/draft/schema.ts`:

```ts
/**
 * The per-church unsaved draft, version 1 (F §4.6; S "Draft store").
 *
 * This is F §4.6's `DraftV1` without the two fields slice 5a adds with its own
 * version bump (`save_key_fingerprint`, `editing.date_iso`). Strings are
 * bounded generously (20 000) so a stored draft is never rejected for
 * length; the UI limits live in the components. `readings.scriptures` holds
 * the raw lines, blanks included; `cleanLines()` derives everything else.
 */
import { z } from "zod";

import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";

export const DRAFT_VERSION = 1;

export const STEP_IDS = ["readings", "hymns", "liturgy", "review"] as const;
export type StepId = (typeof STEP_IDS)[number];

export const SLOTS = ["opening", "response", "closing"] as const;
export type Slot = (typeof SLOTS)[number];

export const SECTION_KEYS = [
  "call_to_worship",
  "opening_prayer",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "prayers_of_the_people",
  "offertory_prayer",
  "benediction",
] as const;
export type SectionKey = (typeof SECTION_KEYS)[number];

const text = z.string().max(20_000);
const dateIso = text.refine(isValidDateIso, "Not a YYYY-MM-DD date.");
const dateIsoOrEmpty = text.refine((s) => s === "" || isValidDateIso(s), "Not a YYYY-MM-DD date.");

const hymnPick = z.object({
  hymn_id: text.nullable(),
  title: text,
  number: z.number().int().nullable(),
  hymnal: text.nullable(),
});
export type HymnPick = z.infer<typeof hymnPick>;

function perSlot<T extends z.ZodType>(value: T) {
  return z.object({ opening: value, response: value, closing: value });
}

const card = z.object({
  enabled: z.boolean(),
  text,
  origin: z.enum(["empty", "typed", "ai", "default", "archive"]),
});
export type LiturgyCard = z.infer<typeof card>;

export const draftV1Schema = z.object({
  version: z.literal(DRAFT_VERSION),
  user_id: text,
  church_id: text,
  created_at: text,
  updated_at: text,
  last_step: z.enum(STEP_IDS),
  save_key: text,
  editing: z.object({ service_id: text, saved_at: text }).nullable(),
  saved_fingerprint: text.nullable(),
  readings: z.object({
    date_iso: dateIsoOrEmpty,
    date_origin: z.enum(["default", "user", "archive"]),
    reading_set: z.object({ date_iso: dateIso, index: z.number().int().min(0) }).nullable(),
    fields_origin: z.enum(["empty", "lectionary", "user", "archive"]),
    occasion: text,
    scriptures: z.array(text),
    selected_ot_ref: text,
    selected_nt_ref: text,
    translation: text.nullable(),
  }),
  hymns: z.object({
    hymnal: text.nullable(),
    exclude_recent: z.boolean(),
    slots: perSlot(hymnPick.nullable()),
    alternatives: z.object({ for_date_iso: dateIso, by_slot: perSlot(z.array(hymnPick)) }).nullable(),
  }),
  liturgy: z.object({
    sermon_title: text,
    include_communion: z.boolean(),
    communion_origin: z.enum(["default", "user", "archive"]),
    cards: z.object(
      Object.fromEntries(SECTION_KEYS.map((key) => [key, card])) as Record<SectionKey, typeof card>,
    ),
    custom_elements: z.array(z.object({ id: text, label: text, text, insert_after: text })),
  }),
});

export type DraftV1 = z.infer<typeof draftV1Schema>;
export type DraftReadings = DraftV1["readings"];

/** The profile fields `freshDraft` needs (`GET /church`, slice 2a). */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean };

/** The church's zone for `todayIn`, or undefined (the browser's zone) when the profile says it is not valid. */
export function churchZone(church: DraftChurch): string | undefined {
  return church.timezone_valid === false ? undefined : (church.timezone ?? undefined);
}

/**
 * A fresh draft (F §4.6 "Fresh draft"): dated the next Sunday strictly after
 * today in the church's zone, every field empty, the cards enabled except the
 * Prayers of the People, the benediction card `default`-origin (slice 4 fills
 * its text), communion on for a first Sunday, a new save key, on step 1.
 */
export function freshDraft({
  church,
  user,
  now = new Date(),
}: {
  church: DraftChurch;
  user: { id: string };
  now?: Date;
}): DraftV1 {
  const date_iso = nextSunday(todayIn(churchZone(church), now));
  const stamp = now.toISOString();
  const cards = Object.fromEntries(
    SECTION_KEYS.map((key) => [
      key,
      { enabled: key !== "prayers_of_the_people", text: "", origin: key === "benediction" ? "default" : "empty" },
    ]),
  ) as Record<SectionKey, LiturgyCard>;
  return {
    version: DRAFT_VERSION,
    user_id: user.id,
    church_id: church.id,
    created_at: stamp,
    updated_at: stamp,
    last_step: "readings",
    save_key: crypto.randomUUID(),
    editing: null,
    saved_fingerprint: null,
    readings: {
      date_iso,
      date_origin: "default",
      reading_set: null,
      fields_origin: "empty",
      occasion: "",
      scriptures: [],
      selected_ot_ref: "",
      selected_nt_ref: "",
      translation: null,
    },
    hymns: {
      hymnal: null,
      exclude_recent: true,
      slots: { opening: null, response: null, closing: null },
      alternatives: null,
    },
    liturgy: {
      sermon_title: "",
      include_communion: isFirstSundayOfMonth(date_iso),
      communion_origin: "default",
      cards,
      custom_elements: [],
    },
  };
}

/** `localStorage` key of one user's draft for one church (F §4.6). */
export function draftKey(userId: string, churchId: string): string {
  return `wsb:draft:${userId}:${churchId}`;
}

/** Where a draft that could not be restored is copied (one slot, overwritten). */
export function corruptDraftKey(userId: string, churchId: string): string {
  return `wsb:draft-corrupt:${userId}:${churchId}`;
}
```

Create `frontend/src/lib/draft/migrate.ts`:

```ts
/**
 * Reading a stored draft back (F §4.6 "Versioning"): parse the JSON, run
 * `migrations[v]` step by step up to `DRAFT_VERSION`, then validate with zod.
 * Any failure (corrupt JSON, invalid data, a *future* version after a
 * rollback, a draft stored under another user's or church's key) throws
 * `DraftRestoreError`; the store then backs the raw value up, starts fresh
 * and toasts. Every change to `DraftV1` bumps the version and adds a
 * migration here with a unit test.
 */
import { DRAFT_VERSION, draftV1Schema, type DraftV1 } from "./schema";

export type StoredDraft = Record<string, unknown>;
/** Upgrades a version-v draft to version v + 1 (it need not set `version`). */
export type Migration = (draft: StoredDraft) => StoredDraft;

/** `migrations[v]` upgrades version v to v + 1. Empty at version 1; slice 5a adds `1`. */
export const migrations: Readonly<Record<number, Migration>> = {};

export class DraftRestoreError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DraftRestoreError";
  }
}

function isRecord(value: unknown): value is StoredDraft {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Brings a parsed draft up to `target`; throws on a missing, invalid or future version or a missing step. */
export function migrate(
  raw: unknown,
  table: Readonly<Record<number, Migration>> = migrations,
  target: number = DRAFT_VERSION,
): StoredDraft {
  if (!isRecord(raw)) throw new DraftRestoreError("The stored draft is not an object.");
  let version = raw.version;
  if (typeof version !== "number" || !Number.isInteger(version) || version < 1) {
    throw new DraftRestoreError("The stored draft has no valid version.");
  }
  if (version > target) {
    throw new DraftRestoreError(`The stored draft is version ${version}, newer than ${target}.`);
  }
  let draft = raw;
  while (version < target) {
    const step = table[version];
    if (!step) throw new DraftRestoreError(`No migration from version ${version}.`);
    version += 1;
    draft = { ...step(draft), version };
  }
  return draft;
}

/**
 * The stored text as a valid current draft for this user and church, or
 * `DraftRestoreError`. `migrationTable` and `target` exist for tests.
 */
export function parseStoredDraft(
  text: string,
  owner: { userId: string; churchId: string },
  migrationTable: Readonly<Record<number, Migration>> = migrations,
  target: number = DRAFT_VERSION,
): DraftV1 {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new DraftRestoreError("The stored draft is not JSON.");
  }
  const result = draftV1Schema.safeParse(migrate(raw, migrationTable, target));
  if (!result.success) throw new DraftRestoreError("The stored draft does not match the schema.");
  if (result.data.user_id !== owner.userId || result.data.church_id !== owner.churchId) {
    throw new DraftRestoreError("The stored draft belongs to another user or church.");
  }
  return result.data;
}
```

- [ ] **Step 7 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** `Tests  7 passed (7)`; `Test Files  39 passed (39)`, `Tests  247 passed (247)` (the existing tests that import `@/test/fixtures` still pass: the new imports are side-effect free); `> tsc --noEmit`, `> eslint`, nothing after.

- [ ] **Step 8 (agent): Commit and back up**

```bash
git add frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/migrate.test.ts
git commit -m "Draft: the version 1 schema, the fresh draft and migrations (F §4.6; S Draft store)" -m "DraftV1 as a zod schema (F §4.6 without slice 5a's two fields; strings up
to 20 000 characters; dates checked), freshDraft (next Sunday in the
church's zone, or the browser's when the zone is not valid; cards on
except Prayers of the People; a default-origin benediction; communion on
for a first Sunday), the draft and corrupt-draft keys, and
parseStoredDraft: JSON, migrations, zod, and a check that the draft
belongs to the key's user and church. Adds the ChurchProfile, Lectionary,
ReadingSet and Translations type names and the churchProfile, DRAFT_NOW
and testDraft test builders. Frontend 240 -> 247.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T3):** the reviewer compares `draftV1Schema` field by field with F §4.6 (minus 5a's fields), checks `freshDraft` against F's "Fresh draft" and S's `freshDraft` bullet, and checks that every failure path in `parseStoredDraft` throws `DraftRestoreError` (never returns a partial draft).

### Task 4: Readings transitions and selectors, and the communion date effect (F §4.6 "Never destroy typed input", "Defaults"; S "readings.ts" table, `normalizePicks`, UX items 2, 3 and 7; AC14, AC15 pure halves; clarifications 20, 28)

S's `readings.ts` is pure and belongs to the draft store (S line 5), so it lands in 2b with every S test case; 2c's step calls it. Each transition returns the same object when nothing changes, which keeps `update(recipe)` a no-op (T6). `setDate` never touches the readings fields; its side effect lives in `date-effects.ts`, where slice 3 adds the hymn effect and slice 4 may take over the communion rule (S Hand-offs).

**Files:**
- Modify: `frontend/src/test/fixtures/index.ts` (`lectionary`)
- Create: `frontend/src/lib/draft/date-effects.ts`, `frontend/src/lib/draft/readings.ts`
- Test: `frontend/src/lib/draft/readings.test.ts` (new, 9 tests)

**Interfaces:**
- Consumes: T1 `isFirstSundayOfMonth`; T2 `cleanLines`, `pickerOptions`, `resolveReadings`, `scriptureKey`, `ReadingPair`; T3 `DraftV1`, `DraftReadings`, `ChurchProfile`, `Lectionary`, `Translations`, `testDraft`, `churchProfile`.
- Produces:
  - `date-effects.ts`: `onDateChanged(d: DraftV1, prevIso: string): DraftV1`.
  - `readings.ts` transitions: `setDate(d, iso, origin = "user")`, `applyReadingSet(d, lect, i)` (throws unless `lect.date === d.readings.date_iso` and set `i` exists), `shouldAutoApply(d, lect): boolean`, `editOccasion(d, s)`, `editScriptureLines(d, raw)`, `normalizePicks(d)`, `commitScriptureLines(d)`, `clearReadings(d)`, `setPick(d, "ot" | "nt", ref)`, `setTranslation(d, id, churchEffective)`.
  - `readings.ts` selectors: `cleanScriptures(d)`, `readingsStale(d)`, `selectedSetIndex(d, lect): number | null`, `showAvailableBanner(d, lect | undefined): boolean`, `effectivePicks(d): ReadingPair`, `effectiveTranslation(d, church, translations | undefined): string`.
  - `frontend/src/test/fixtures/index.ts`: `lectionary(date, overrides?)` (two sets: "Nineteenth Sunday after Pentecost" with the Isaiah lines, default; "Resurrection of the Lord" with the Easter lines).
  - Later users: T5 (`effectivePicks` in `mapping`), T6 (`normalizePicks`, `setDate`), T9 (`cleanScriptures`, `effectivePicks`), 2c (every transition; `useLectionarySync` runs `update(d => shouldAutoApply(d, data) ? applyReadingSet(d, data, data.default_index!) : d)`), 5a (`effectivePicks`).

Counts after this task: frontend **256 passed in 40 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/draft/readings.ts && echo "no T4 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T4 files yet`; `Test Files  39 passed (39)`, `Tests  247 passed (247)`.

- [ ] **Step 2 (agent): Add the `lectionary` builder**

In `frontend/src/test/fixtures/index.ts`, change the first import to

```ts
import type { ChurchProfile, InviteAccepted, InvitePreview, Lectionary } from "@/lib/api/types";
```

and append at the end of the file (one blank line before):

```ts
/** A `GET /lectionary/readings` answer for `date` (the Isaiah and Easter lines from S `scripture_refs.py`). */
export function lectionary(date: string, overrides: Partial<Lectionary> = {}): Lectionary {
  return {
    date,
    status: "ok",
    partial: false,
    reading_sets: [
      {
        name: "Nineteenth Sunday after Pentecost",
        source: "merged",
        scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
      },
      {
        name: "Resurrection of the Lord",
        source: "vanderbilt",
        scriptures: ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"],
      },
    ],
    default_index: 0,
    ...overrides,
  };
}
```

- [ ] **Step 3 (agent): Write the failing test**

Create `frontend/src/lib/draft/readings.test.ts`. It covers S Testing's `readings.test.ts` row: every transition and selector; `shouldAutoApply` for each origin; stale detection; auto-apply replaces an old date's lectionary fields but never `user` or `archive` fields; picks reset on apply; the communion effect only while its origin is `default`; `setTranslation` stores null for the default; `effectivePicks` never gives a Psalm as NT and gives Acts with the Easter lines and OT pick Psalm 118; `normalizePicks` / `commitScriptureLines` clear only stale picks and return the same object otherwise; `editScriptureLines` never clears picks; and the six `showAvailableBanner` cases.

```ts
import { describe, expect, it } from "vitest";

import { churchProfile, lectionary, testDraft } from "@/test/fixtures";

import { onDateChanged } from "./date-effects";
import {
  applyReadingSet,
  clearReadings,
  commitScriptureLines,
  editOccasion,
  editScriptureLines,
  effectivePicks,
  effectiveTranslation,
  normalizePicks,
  readingsStale,
  selectedSetIndex,
  setDate,
  setPick,
  setTranslation,
  shouldAutoApply,
  showAvailableBanner,
} from "./readings";
import type { DraftV1 } from "./schema";

const ISAIAH = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];
const EASTER = ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"];
const OCT_4 = "2026-10-04";
const OCT_11 = "2026-10-11";
/** October 11's own answer: one set, unlike October 4's lines. */
const OCT_11_LECT = lectionary(OCT_11, {
  reading_sets: [
    {
      name: "Twentieth Sunday after Pentecost",
      source: "merged",
      scriptures: ["Isaiah 25:1-9", "Psalm 23", "Philippians 4:1-9", "Matthew 22:1-14"],
    },
  ],
});

/** A draft filled from set 0 of October 4's lookup. */
function filled(): DraftV1 {
  return applyReadingSet(testDraft(), lectionary(OCT_4), 0);
}

function typed(lines: string[], date = OCT_4): DraftV1 {
  return editScriptureLines(editOccasion(setDate(testDraft(), date), "Harvest Sunday"), lines.join("\n"));
}

describe("readings transitions (S readings.ts)", () => {
  it("setDate sets the date and origin, keeps the fields, and follows communion only while it is a default", () => {
    const d = filled();
    const moved = setDate(d, OCT_11);
    expect(moved.readings).toMatchObject({ date_iso: OCT_11, date_origin: "user", occasion: d.readings.occasion });
    expect(moved.readings.scriptures).toEqual(ISAIAH);
    expect(moved.liturgy.include_communion).toBe(false); // October 11 is not a first Sunday
    expect(setDate(moved, "2026-11-01").liturgy.include_communion).toBe(true);
    expect(setDate(moved, "2026-11-03").liturgy.include_communion).toBe(false); // a Tuesday
    expect(setDate(d, OCT_4, "default")).toBe(d);

    const chosen: DraftV1 = { ...d, liturgy: { ...d.liturgy, include_communion: false, communion_origin: "user" } };
    expect(setDate(chosen, "2026-11-01").liturgy.include_communion).toBe(false);
    expect(onDateChanged(chosen, OCT_4)).toBe(chosen);
    expect(setDate(testDraft(), "").readings.date_iso).toBe("");
  });

  it("applyReadingSet fills the fields for this date only and clears the picks", () => {
    const picked = setPick(setPick(testDraft(), "ot", "Psalm 80:7-15"), "nt", "Matthew 21:33-46");
    const d = applyReadingSet(picked, lectionary(OCT_4), 1);
    expect(d.readings).toMatchObject({
      occasion: "Resurrection of the Lord",
      scriptures: EASTER,
      fields_origin: "lectionary",
      reading_set: { date_iso: OCT_4, index: 1 },
      selected_ot_ref: "",
      selected_nt_ref: "",
    });
    expect(() => applyReadingSet(testDraft(), lectionary(OCT_11), 0)).toThrow();
    expect(() => applyReadingSet(testDraft(), lectionary(OCT_4), 5)).toThrow();
  });

  it("shouldAutoApply replaces empty fields and an old date's lectionary fields, never typed or archived ones", () => {
    const lect = lectionary(OCT_4);
    expect(shouldAutoApply(testDraft(), lect)).toBe(true);
    expect(shouldAutoApply(filled(), lect)).toBe(false); // already this date's set
    const oldDate = setDate(filled(), OCT_11);
    expect(shouldAutoApply(oldDate, lectionary(OCT_11))).toBe(true);
    expect(readingsStale(oldDate)).toBe(true);
    expect(readingsStale(filled())).toBe(false);
    expect(shouldAutoApply(typed(ISAIAH), lect)).toBe(false);
    const archived = testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "archive" } }));
    expect(shouldAutoApply(archived, lect)).toBe(false);
    expect(shouldAutoApply(testDraft(), lectionary(OCT_11))).toBe(false); // a late answer for another date
    expect(shouldAutoApply(testDraft(), lectionary(OCT_4, { status: "no_readings", reading_sets: [], default_index: null }))).toBe(false);
  });

  it("edits mark the fields as the user's and never touch the picks; commit and normalize clear only stale picks", () => {
    const picked = setPick(filled(), "ot", "Psalm 80:7-15");
    const edited = editScriptureLines(picked, "Isaiah 5:1-7\n\nPhilippians 3:4b-14");
    expect(edited.readings).toMatchObject({
      scriptures: ["Isaiah 5:1-7", "", "Philippians 3:4b-14"],
      fields_origin: "user",
      selected_ot_ref: "Psalm 80:7-15",
    });
    expect(editScriptureLines(edited, "Isaiah 5:1-7\n\nPhilippians 3:4b-14")).toBe(edited);
    expect(editOccasion(filled(), "Harvest").readings).toMatchObject({ occasion: "Harvest", fields_origin: "user" });

    const committed = commitScriptureLines(edited);
    expect(committed.readings.selected_ot_ref).toBe("");
    expect(commitScriptureLines(picked)).toBe(picked);
    expect(normalizePicks(picked)).toBe(picked);
    const wrongSide = setPick(filled(), "nt", "Psalm 80:7-15");
    expect(normalizePicks(wrongSide).readings.selected_nt_ref).toBe("");
  });

  it("clearReadings empties the fields; setPick and setTranslation store only changes", () => {
    const cleared = clearReadings(setPick(filled(), "nt", "Matthew 21:33-46"));
    expect(cleared.readings).toMatchObject({
      occasion: "",
      scriptures: [],
      fields_origin: "empty",
      reading_set: null,
      selected_ot_ref: "",
      selected_nt_ref: "",
    });
    const d = filled();
    expect(setPick(d, "ot", "")).toBe(d);
    expect(setTranslation(d, "web", "web")).toBe(d);
    const kjv = setTranslation(d, "kjv", "web");
    expect(kjv.readings.translation).toBe("kjv");
    expect(setTranslation(kjv, "web", "web").readings.translation).toBeNull();
  });
});

describe("readings selectors (S readings.ts)", () => {
  it("effectivePicks never gives a Psalm as the NT, and follows the other side's pick", () => {
    expect(effectivePicks(filled())).toEqual({
      ot: "Isaiah 5:1-7",
      nt: "Philippians 3:4b-14",
      otAuto: true,
      ntAuto: true,
    });
    const easter = applyReadingSet(testDraft(), lectionary(OCT_4), 1);
    expect(effectivePicks(setPick(easter, "ot", "Psalm 118:1-2, 14-24"))).toEqual({
      ot: "Psalm 118:1-2, 14-24",
      nt: "Acts 10:34-43",
      otAuto: false,
      ntAuto: true,
    });
    // A stale stored pick is automatic even before normalizePicks runs.
    const stale = editScriptureLines(setPick(filled(), "ot", "Psalm 80:7-15"), "Isaiah 5:1-7\nPhilippians 3:4b-14");
    expect(effectivePicks(stale)).toMatchObject({ ot: "Isaiah 5:1-7", otAuto: true });
  });

  it("showAvailableBanner: only for typed fields not from this date's set, or archived fields after a date change", () => {
    const lect = OCT_11_LECT;
    // user, after a date change → shown
    const afterDateChange = setDate(editOccasion(filled(), "Harvest"), OCT_11);
    expect(showAvailableBanner(afterDateChange, lect)).toBe(true);
    // user, after deleting the Psalm line of this date's set → not shown
    const psalmDeleted = editScriptureLines(filled(), "Isaiah 5:1-7\nPhilippians 3:4b-14\nMatthew 21:33-46");
    expect(showAvailableBanner(psalmDeleted, lectionary(OCT_4))).toBe(false);
    // user typed with no reading set, sets for this date → shown
    expect(showAvailableBanner(typed(["John 3:16"]), lectionary(OCT_4))).toBe(true);
    // typed lines equal to a set → not shown
    expect(showAvailableBanner(typed(ISAIAH), lectionary(OCT_4))).toBe(false);
    // archive on its own date → not shown; after a date change → shown
    const archived = testDraft((d) => ({
      ...d,
      readings: { ...d.readings, date_origin: "archive", fields_origin: "archive", scriptures: ["John 3:16"] },
    }));
    expect(showAvailableBanner(archived, lectionary(OCT_4))).toBe(false);
    expect(showAvailableBanner(setDate(archived, OCT_11), lect)).toBe(true);
    // empty and lectionary → never; no lookup or another date's → never
    expect(showAvailableBanner(testDraft(), lectionary(OCT_4))).toBe(false);
    expect(showAvailableBanner(setDate(filled(), OCT_11), lect)).toBe(false);
    expect(showAvailableBanner(afterDateChange, undefined)).toBe(false);
    expect(showAvailableBanner(afterDateChange, lectionary(OCT_4))).toBe(false);
  });

  it("selectedSetIndex matches the scriptures first, then the stored index for this date", () => {
    const lect = lectionary(OCT_4);
    expect(selectedSetIndex(filled(), lect)).toBe(0);
    expect(selectedSetIndex(typed(EASTER), lect)).toBe(1);
    expect(selectedSetIndex(typed(["Luke 2:1-14, (15-20)"]), lect)).toBeNull();
    const editedSet1 = editScriptureLines(applyReadingSet(testDraft(), lect, 1), "Acts 10:34-43");
    expect(selectedSetIndex(editedSet1, lect)).toBe(1);
    expect(selectedSetIndex(filled(), lectionary(OCT_11))).toBeNull();
  });

  it("effectiveTranslation honours a stored override only when the loaded list offers it", () => {
    const church = churchProfile({ effective_translation: "web" });
    const list = { default: "web", esv_available: false, items: [{ id: "web", label: "WEB" }, { id: "kjv", label: "KJV" }] };
    const kjv = setTranslation(filled(), "kjv", "web");
    const esv = setTranslation(filled(), "esv", "web");
    expect(effectiveTranslation(kjv, church, list)).toBe("kjv");
    expect(effectiveTranslation(esv, church, list)).toBe("web");
    expect(effectiveTranslation(kjv, church, undefined)).toBe("web");
    expect(effectiveTranslation(filled(), churchProfile({ effective_translation: "kjv" }), list)).toBe("kjv");
  });
});
```

- [ ] **Step 4 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/lib/draft/readings.test.ts 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** ` FAIL  |unit| src/lib/draft/readings.test.ts`, `Error: Cannot find module './date-effects'` (or `'./readings'`), `Tests  no tests`.

- [ ] **Step 5 (agent): Write `date-effects.ts` and `readings.ts`**

Create `frontend/src/lib/draft/date-effects.ts`:

```ts
/**
 * What a date change does outside the readings fields (S "readings.ts"
 * `setDate`; F §4.6 "Defaults apply only while origin is `default`").
 *
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
}
```

Create `frontend/src/lib/draft/readings.ts`:

```ts
/**
 * Readings transitions and selectors (S "readings.ts"; F §4.6 "Never destroy
 * typed input"). Pure: each takes a draft and returns the next one, or the
 * same object when nothing changes, so `update(recipe)` stays a no-op.
 * Slice 2c's Date & readings step calls them; slice 2b's store uses
 * `normalizePicks` and `setDate`.
 */
import type { ChurchProfile, Lectionary, Translations } from "@/lib/api/types";
import { cleanLines, pickerOptions, resolveReadings, scriptureKey, type ReadingPair } from "@/lib/scripture-refs";

import { onDateChanged } from "./date-effects";
import type { DraftReadings, DraftV1 } from "./schema";

function withReadings(d: DraftV1, patch: Partial<DraftReadings>): DraftV1 {
  return { ...d, readings: { ...d.readings, ...patch } };
}

/** Sets the date and its origin, then runs the date side effects. Never touches the readings fields. */
export function setDate(d: DraftV1, iso: string, origin: DraftReadings["date_origin"] = "user"): DraftV1 {
  if (d.readings.date_iso === iso && d.readings.date_origin === origin) return d;
  const prevIso = d.readings.date_iso;
  return onDateChanged(withReadings(d, { date_iso: iso, date_origin: origin }), prevIso);
}

/** Fills occasion and scriptures from set `i` of this date's lookup; clears both picks. */
export function applyReadingSet(d: DraftV1, lect: Lectionary, i: number): DraftV1 {
  if (lect.date !== d.readings.date_iso) {
    throw new Error(`applyReadingSet: lookup for ${lect.date}, draft dated ${d.readings.date_iso}`);
  }
  const set = lect.reading_sets[i];
  if (!set) throw new Error(`applyReadingSet: no reading set ${i}`);
  return withReadings(d, {
    occasion: set.name,
    scriptures: [...set.scriptures],
    fields_origin: "lectionary",
    reading_set: { date_iso: lect.date, index: i },
    selected_ot_ref: "",
    selected_nt_ref: "",
  });
}

/** Auto-fill applies only to empty fields, or to lectionary fields from another date. */
export function shouldAutoApply(d: DraftV1, lect: Lectionary): boolean {
  const r = d.readings;
  if (lect.date !== r.date_iso || lect.status !== "ok" || lect.reading_sets.length === 0) return false;
  return r.fields_origin === "empty" || (r.fields_origin === "lectionary" && r.reading_set?.date_iso !== r.date_iso);
}

export function editOccasion(d: DraftV1, occasion: string): DraftV1 {
  if (d.readings.occasion === occasion && d.readings.fields_origin === "user") return d;
  return withReadings(d, { occasion, fields_origin: "user" });
}

/** Stores the textarea's raw text as lines. Picks are left alone while the user types. */
export function editScriptureLines(d: DraftV1, raw: string): DraftV1 {
  const scriptures = raw.split("\n");
  const same =
    d.readings.fields_origin === "user" &&
    scriptures.length === d.readings.scriptures.length &&
    scriptures.every((line, i) => line === d.readings.scriptures[i]);
  return same ? d : withReadings(d, { scriptures, fields_origin: "user" });
}

/** Clears each pick that is no longer an option for its side; returns `d` when both are still valid. */
export function normalizePicks(d: DraftV1): DraftV1 {
  const options = pickerOptions(cleanLines(d.readings.scriptures));
  const ot = options.ot.includes(d.readings.selected_ot_ref.trim()) ? d.readings.selected_ot_ref : "";
  const nt = options.nt.includes(d.readings.selected_nt_ref.trim()) ? d.readings.selected_nt_ref : "";
  if (ot === d.readings.selected_ot_ref && nt === d.readings.selected_nt_ref) return d;
  return withReadings(d, { selected_ot_ref: ot, selected_nt_ref: nt });
}

/** When the scripture textarea loses focus. */
export function commitScriptureLines(d: DraftV1): DraftV1 {
  return normalizePicks(d);
}

export function clearReadings(d: DraftV1): DraftV1 {
  return withReadings(d, {
    occasion: "",
    scriptures: [],
    fields_origin: "empty",
    reading_set: null,
    selected_ot_ref: "",
    selected_nt_ref: "",
  });
}

/** An explicit bulletin pick, or "" for automatic. */
export function setPick(d: DraftV1, side: "ot" | "nt", ref: string): DraftV1 {
  const key = side === "ot" ? "selected_ot_ref" : "selected_nt_ref";
  return d.readings[key] === ref ? d : withReadings(d, { [key]: ref });
}

/** Stores null when the choice is the church's effective translation, so later default changes flow through. */
export function setTranslation(d: DraftV1, id: string, churchEffective: string): DraftV1 {
  const translation = id === churchEffective ? null : id;
  return d.readings.translation === translation ? d : withReadings(d, { translation });
}

// --- selectors ---------------------------------------------------------------

export function cleanScriptures(d: DraftV1): string[] {
  return cleanLines(d.readings.scriptures);
}

/** Lectionary fields that were filled for another date. */
export function readingsStale(d: DraftV1): boolean {
  return d.readings.fields_origin === "lectionary" && d.readings.reading_set?.date_iso !== d.readings.date_iso;
}

function sameScriptures(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((line, i) => scriptureKey(line) === scriptureKey(b[i]));
}

/** The set whose references equal the draft's cleaned scriptures; else the stored index for this date; else null. */
export function selectedSetIndex(d: DraftV1, lect: Lectionary): number | null {
  if (lect.date !== d.readings.date_iso) return null;
  const lines = cleanScriptures(d);
  const matching = lect.reading_sets.findIndex((set) => sameScriptures(set.scriptures, lines));
  if (matching >= 0) return matching;
  const stored = d.readings.reading_set;
  if (stored && stored.date_iso === lect.date && stored.index < lect.reading_sets.length) return stored.index;
  return null;
}

/**
 * The "Readings for {date} are available" banner (S UX item 3): sets for this
 * date, none equal to the cleaned scriptures, and typed fields not filled from
 * this date's lectionary, or archived fields whose date has changed.
 */
export function showAvailableBanner(d: DraftV1, lect: Lectionary | undefined): boolean {
  if (!lect || lect.date !== d.readings.date_iso || lect.reading_sets.length === 0) return false;
  const lines = cleanScriptures(d);
  if (lect.reading_sets.some((set) => sameScriptures(set.scriptures, lines))) return false;
  const r = d.readings;
  if (r.fields_origin === "user") return r.reading_set?.date_iso !== r.date_iso;
  if (r.fields_origin === "archive") return r.date_origin !== "archive";
  return false;
}

/** The bulletin readings as the screen, the payload and (from 5a) the docx show them. */
export function effectivePicks(d: DraftV1): ReadingPair {
  return resolveReadings(d.readings.scriptures, d.readings.selected_ot_ref, d.readings.selected_nt_ref);
}

/** The stored override when the loaded list offers it; else the church's effective translation. */
export function effectiveTranslation(
  d: DraftV1,
  church: Pick<ChurchProfile, "effective_translation">,
  translations: Translations | undefined,
): string {
  const chosen = d.readings.translation;
  if (chosen && translations?.items.some((item) => item.id === chosen)) return chosen;
  return church.effective_translation;
}
```

- [ ] **Step 6 (agent): Run the test, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/readings.test.ts 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** `Tests  9 passed (9)`; `Test Files  40 passed (40)`, `Tests  256 passed (256)`; `> tsc --noEmit`, `> eslint`, nothing after.

- [ ] **Step 7 (agent): Commit and back up**

```bash
git add frontend/src/test/fixtures/index.ts frontend/src/lib/draft/date-effects.ts frontend/src/lib/draft/readings.ts frontend/src/lib/draft/readings.test.ts
git commit -m "Draft: readings transitions and selectors, and the communion date effect (F §4.6; S readings.ts; AC14)" -m "The pure readings transitions of S readings.ts (setDate, applyReadingSet,
shouldAutoApply, the edits, normalizePicks, clearReadings, setPick,
setTranslation) and selectors (readingsStale, selectedSetIndex,
showAvailableBanner, effectivePicks, effectiveTranslation). Each returns
the same draft when nothing changes. setDate runs onDateChanged, which
keeps communion on the first-Sunday rule only while it is a default.
Slice 2c's Date & readings step calls them. Frontend 247 -> 256.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T4):** the reviewer walks S's `readings.ts` table and UX items 2, 3 and 7 against the code: `shouldAutoApply` never returns true for `user` or `archive` fields; `showAvailableBanner` follows UX item 3 exactly; `applyReadingSet` clears both picks; every transition returns `d` itself when nothing changes.

### Task 5: Steps, step status, the provisional payload and its fingerprint (F §4.6 "Unsaved changes", "Draft → API payload", §4.7 "StepProgress"; S "steps.ts", "status.ts", "mapping.ts", "fingerprint.ts"; AC8 payload half, AC17 `isPristine`; clarifications 2, 10, 13, 14)

`steps.ts` names the four steps and holds `SHIPPED_STEPS`, empty in 2b (owner answer Q1, clarification 2). `status.ts` gives each step its F §4.7 status, gated by `SHIPPED_STEPS`, plus `isPristine` (by origins, not text, so slice 4's default benediction never makes a fresh draft look edited) and `stillNeeded`. `mapping.ts` is the provisional `draftToServicePayload` (5a owns and replaces it): it sends only picks that are still options, the rule 5a must keep. `fingerprint.ts` hashes that payload and decides `isDirty`.

**Files:**
- Create: `frontend/src/lib/draft/steps.ts`, `frontend/src/lib/draft/status.ts`, `frontend/src/lib/draft/mapping.ts`, `frontend/src/lib/draft/fingerprint.ts`
- Test: `frontend/src/lib/draft/status.test.ts` (new, 7 tests; its first test covers `steps.ts`), `frontend/src/lib/draft/mapping.test.ts` (new, 3 tests), `frontend/src/lib/draft/fingerprint.test.ts` (new, 2 tests)

**Interfaces:**
- Consumes: T1 `inSupportedRange`, `isValidDateIso`; T2 `cleanLines`; T3 `DraftV1`, `StepId`, `SLOTS`, `SECTION_KEYS`, `HymnPick`, `SectionKey`, `Slot`; T4 `effectivePicks` and the transitions (tests).
- Produces:
  - `steps.ts`: `type Step = { id; number; label; short; href; previous; next }`; `STEPS` (in order; labels "Date & readings", "Hymns", "Liturgy", "Review & send"; `short` "Readings", "Hymns", "Liturgy", "Review"); `SHIPPED_STEPS: ReadonlySet<StepId>` (empty); `stepById(id)`; `stepFromPath(pathname): StepId | null`. Later users: T9, 2c (adds "readings"), 3, 4, 5a.
  - `status.ts`: `type StepStatus = { kind: "complete" } | { kind: "incomplete"; done; total } | { kind: "soon" } | { kind: "not_in_archive" }`; `hasServiceDate(d)`; `stepStatus(d, step, shipped = SHIPPED_STEPS)`; `isPristine(d)`; `type NeededItem = { step; message; action }`; `stillNeeded(d, shipped = SHIPPED_STEPS)`. Later users: T6 (`isPristine` in `rollForward`), T9, 3, 4, 5a.
  - `mapping.ts`: `type HymnRefPayload`, `type ServiceDraftPayload`, `draftToServicePayload(draft)`. Later user: 5a (replaces it).
  - `fingerprint.ts`: `stableStringify(value)`, `fnv1a32(text)`, `fingerprint(payload)`, `isDirty(draft)`. Later users: T9 (New service), 5a.

Counts after this task: frontend **268 passed in 43 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/draft/status.ts && echo "no T5 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T5 files yet`; `Test Files  40 passed (40)`, `Tests  256 passed (256)`.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/lib/draft/status.test.ts` (S Testing: "2 of 3"; `stillNeeded` limited to shipped steps; every `isPristine` case, including the benediction `{text: "Halverson", origin: "default"}`):

```ts
import { describe, expect, it } from "vitest";

import { lectionary, testDraft } from "@/test/fixtures";

import { applyReadingSet, editOccasion, editScriptureLines, setDate, setPick } from "./readings";
import type { DraftV1, HymnPick, StepId } from "./schema";
import { isPristine, stepStatus, stillNeeded } from "./status";
import { SHIPPED_STEPS, STEPS, stepById, stepFromPath } from "./steps";

const READINGS: ReadonlySet<StepId> = new Set<StepId>(["readings"]);
const ALL: ReadonlySet<StepId> = new Set<StepId>(["readings", "hymns", "liturgy", "review"]);
const HYMN: HymnPick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };

function withLiturgy(patch: Partial<DraftV1["liturgy"]>): DraftV1 {
  return testDraft((d) => ({ ...d, liturgy: { ...d.liturgy, ...patch } }));
}

function withCard(key: keyof DraftV1["liturgy"]["cards"], card: Partial<DraftV1["liturgy"]["cards"]["benediction"]>) {
  return testDraft((d) => ({
    ...d,
    liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...card } } },
  }));
}

describe("steps (S steps.ts)", () => {
  it("lists the four steps in order, ships none in 2b, and reads a step from its path", () => {
    expect(STEPS.map((s) => [s.number, s.label, s.href, s.previous, s.next])).toEqual([
      [1, "Date & readings", "/builder/readings", null, "hymns"],
      [2, "Hymns", "/builder/hymns", "readings", "liturgy"],
      [3, "Liturgy", "/builder/liturgy", "hymns", "review"],
      [4, "Review & send", "/builder/review", "liturgy", null],
    ]);
    expect([...SHIPPED_STEPS]).toEqual([]);
    expect(stepById("liturgy").label).toBe("Liturgy");
    expect(stepFromPath("/builder/hymns")).toBe("hymns");
    expect(stepFromPath("/builder/review/")).toBe("review");
    expect(stepFromPath("/builder")).toBeNull();
    expect(stepFromPath("/builder/summary")).toBeNull();
    expect(stepFromPath("/services")).toBeNull();
  });
});

describe("stepStatus (F §4.7)", () => {
  it("shows Soon for unshipped steps and Not in archive for Review", () => {
    const d = testDraft();
    expect(STEPS.map((s) => stepStatus(d, s.id).kind)).toEqual(["soon", "soon", "soon", "not_in_archive"]);
    expect(stepStatus(d, "review", ALL)).toEqual({ kind: "not_in_archive" });
  });

  it("counts the readings: a valid date, an occasion and a scripture (\"2 of 3\")", () => {
    const fresh = testDraft();
    expect(stepStatus(fresh, "readings", READINGS)).toEqual({ kind: "incomplete", done: 1, total: 3 });
    const occasion = editOccasion(fresh, "Harvest");
    expect(stepStatus(occasion, "readings", READINGS)).toEqual({ kind: "incomplete", done: 2, total: 3 });
    const blankLines = editScriptureLines(occasion, "\n  \n");
    expect(stepStatus(blankLines, "readings", READINGS)).toEqual({ kind: "incomplete", done: 2, total: 3 });
    const full = applyReadingSet(fresh, lectionary("2026-10-04"), 0);
    expect(stepStatus(full, "readings", READINGS)).toEqual({ kind: "complete" });
    expect(stepStatus(setDate(full, ""), "readings", READINGS)).toEqual({ kind: "incomplete", done: 2, total: 3 });
    expect(stepStatus(setDate(full, "2250-01-01"), "readings", READINGS)).toEqual({
      kind: "incomplete",
      done: 2,
      total: 3,
    });
  });

  it("counts filled hymn slots and enabled liturgy cards with text once those steps ship", () => {
    const oneHymn = testDraft((d) => ({ ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, opening: HYMN } } }));
    expect(stepStatus(oneHymn, "hymns", ALL)).toEqual({ kind: "incomplete", done: 1, total: 3 });
    expect(stepStatus(withCard("call_to_worship", { text: "Come" }), "liturgy", ALL)).toEqual({
      kind: "incomplete",
      done: 1,
      total: 7,
    });
  });
});

describe("isPristine (S status.ts)", () => {
  it("is true for a fresh draft, a lectionary fill and a default benediction with text", () => {
    expect(isPristine(testDraft())).toBe(true);
    expect(isPristine(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0))).toBe(true);
    expect(isPristine(withCard("benediction", { text: "Halverson", origin: "default" }))).toBe(true);
  });

  it("is false once anything the user would lose is there", () => {
    const cases: [string, DraftV1][] = [
      ["typed card", withCard("call_to_worship", { text: "Come", origin: "typed" })],
      ["ai card", withCard("call_to_worship", { text: "Come", origin: "ai" })],
      ["archive card", withCard("benediction", { text: "Go", origin: "archive" })],
      ["communion chosen", withLiturgy({ communion_origin: "user" })],
      ["sermon title", withLiturgy({ sermon_title: "Grace" })],
      ["custom element", withLiturgy({ custom_elements: [{ id: "1", label: "Anthem", text: "", insert_after: "assurance" }] })],
      ["a pick", setPick(testDraft(), "ot", "Isaiah 5:1-7")],
      ["a hymn", testDraft((d) => ({ ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, closing: HYMN } } }))],
      ["editing", testDraft((d) => ({ ...d, editing: { service_id: "s1", saved_at: "2026-09-29T16:00:00Z" } }))],
      ["user fields", editOccasion(testDraft(), "Harvest")],
      ["archive fields", testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "archive" } }))],
    ];
    for (const [name, d] of cases) expect(isPristine(d), name).toBe(false);
  });
});

describe("stillNeeded (S Review \"Still needed\")", () => {
  it("lists only shipped steps' gaps", () => {
    const fresh = setDate(testDraft(), "");
    expect(stillNeeded(fresh)).toEqual([]);
    expect(stillNeeded(fresh, READINGS)).toEqual([
      { step: "readings", message: "No service date", action: "Choose one" },
      { step: "readings", message: "No occasion", action: "Add one" },
      { step: "readings", message: "No scripture readings", action: "Add one" },
    ]);
    expect(stillNeeded(applyReadingSet(testDraft(), lectionary("2026-10-04"), 0), READINGS)).toEqual([]);
  });
});
```

Create `frontend/src/lib/draft/mapping.test.ts` (the payload trims and drops blanks and sends a stale pick as ""):

```ts
import { describe, expect, it } from "vitest";

import { lectionary, testDraft } from "@/test/fixtures";

import { draftToServicePayload } from "./mapping";
import { applyReadingSet, editScriptureLines, setPick } from "./readings";
import type { DraftV1 } from "./schema";

describe("draftToServicePayload (provisional; 5a replaces it)", () => {
  it("maps a fresh draft to the ServiceDraft shape", () => {
    expect(draftToServicePayload(testDraft())).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "",
      scriptures: [],
      hymns: { opening: null, response: null, closing: null },
      liturgy: {},
      sermon_title: "",
      selected_ot_ref: "",
      selected_nt_ref: "",
      include_communion: true,
      custom_elements: [],
      hymnal: null,
    });
  });

  it("trims and drops blank lines, keeps enabled non-empty cards, slot-keyed hymns and elements without ids", () => {
    const d: DraftV1 = testDraft((base) => {
      const lines = editScriptureLines(base, "  Isaiah 5:1-7 \n\n   \nPsalm 80:7-15");
      return {
        ...lines,
        hymns: {
          ...lines.hymns,
          hymnal: "GG2013",
          slots: { ...lines.hymns.slots, response: { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" } },
        },
        liturgy: {
          ...lines.liturgy,
          cards: {
            ...lines.liturgy.cards,
            call_to_worship: { enabled: true, text: "Come, let us worship.", origin: "typed" },
            opening_prayer: { enabled: false, text: "Hidden", origin: "typed" },
            assurance: { enabled: true, text: "   ", origin: "typed" },
          },
          custom_elements: [{ id: "x1", label: "Anthem", text: "Choir", insert_after: "assurance" }],
        },
      };
    });
    const payload = draftToServicePayload(d);
    expect(payload.scriptures).toEqual(["Isaiah 5:1-7", "Psalm 80:7-15"]);
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship." });
    expect(payload.hymns.response).toEqual({ hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" });
    expect(payload.hymns.opening).toBeNull();
    expect(payload.hymnal).toBe("GG2013");
    expect(payload.custom_elements).toEqual([{ label: "Anthem", text: "Choir", insert_after: "assurance" }]);
  });

  it("sends only picks that are still options, whatever the stored draft holds", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const picked = setPick(setPick(filled, "ot", "Psalm 80:7-15"), "nt", "Matthew 21:33-46");
    expect(draftToServicePayload(picked)).toMatchObject({
      selected_ot_ref: "Psalm 80:7-15",
      selected_nt_ref: "Matthew 21:33-46",
    });
    // The Psalm line deleted while the textarea had focus: the stored pick is stale.
    const stale = editScriptureLines(picked, "Isaiah 5:1-7\nPhilippians 3:4b-14\nMatthew 21:33-46");
    expect(stale.readings.selected_ot_ref).toBe("Psalm 80:7-15");
    expect(draftToServicePayload(stale)).toMatchObject({ selected_ot_ref: "", selected_nt_ref: "Matthew 21:33-46" });
  });
});
```

Create `frontend/src/lib/draft/fingerprint.test.ts` (stable under key order; the published FNV-1a vectors; `isDirty` with and without `saved_fingerprint`; a fresh draft with the default benediction text is not dirty):

```ts
import { describe, expect, it } from "vitest";

import { testDraft } from "@/test/fixtures";

import { fingerprint, fnv1a32, isDirty, stableStringify } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { editOccasion } from "./readings";
import type { DraftV1 } from "./schema";

describe("fingerprint and isDirty (F §4.6 Unsaved changes)", () => {
  it("is FNV-1a over stable JSON, so key order never changes it", () => {
    expect(stableStringify({ b: 1, a: { d: [2, { f: 1, e: 0 }], c: null } })).toBe(
      '{"a":{"c":null,"d":[2,{"e":0,"f":1}]},"b":1}',
    );
    expect(fingerprint({ a: 1, b: [1, 2] })).toBe(fingerprint({ b: [1, 2], a: 1 }));
    expect(fingerprint({ a: 1 })).not.toBe(fingerprint({ a: 2 }));
    // The published FNV-1a 32-bit test vectors.
    expect(fnv1a32("")).toBe("811c9dc5");
    expect(fnv1a32("a")).toBe("e40c292c");
    expect(fnv1a32("foobar")).toBe("bf9cf968");
    expect(fingerprint({ a: 1 })).toBe(fnv1a32('{"a":1}'));
  });

  it("isDirty: never saved means not pristine; saved means the payload changed", () => {
    const fresh = testDraft();
    expect(isDirty(fresh)).toBe(false);
    expect(isDirty(editOccasion(fresh, "Harvest"))).toBe(true);
    const withDefaultBenediction = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Halverson", origin: "default" } },
      },
    }));
    expect(isDirty(withDefaultBenediction)).toBe(false);

    const saved: DraftV1 = {
      ...editOccasion(fresh, "Harvest"),
      saved_fingerprint: fingerprint(draftToServicePayload(editOccasion(fresh, "Harvest"))),
    };
    expect(isDirty(saved)).toBe(false);
    expect(isDirty(editOccasion(saved, "Harvest Home"))).toBe(true);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/lib/draft/mapping.test.ts src/lib/draft/fingerprint.test.ts 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** three ` FAIL ` lines with `Error: Cannot find module './status'`, `'./mapping'` and `'./fingerprint'`; `Tests  no tests`.

- [ ] **Step 4 (agent): Write the four modules**

Create `frontend/src/lib/draft/steps.ts`:

```ts
/**
 * The four builder steps (F §4.7; S "steps.ts"). Every step has its own
 * route and is always reachable (F D9).
 *
 * `SHIPPED_STEPS` holds the steps whose content has shipped. An unshipped
 * step shows the "Available soon" card, the muted status "Soon" (Review: "Not
 * in archive"), and `stillNeeded` ignores it. Slice 2b ships none: owner
 * answer Q1 (2026-09-28) keeps Date & readings on the placeholder until 2c.
 * Slice 2c adds "readings", slice 3 "hymns", slice 4 "liturgy", 5a "review".
 */
import type { StepId } from "./schema";

export type { StepId } from "./schema";

export type Step = {
  id: StepId;
  /** 1-4, as shown in "Step 1 of 4". */
  number: number;
  label: string;
  /** The footer's "Next: …" name. */
  short: string;
  href: `/builder/${StepId}`;
  previous: StepId | null;
  next: StepId | null;
};

export const STEPS: readonly Step[] = [
  { id: "readings", number: 1, label: "Date & readings", short: "Readings", href: "/builder/readings", previous: null, next: "hymns" },
  { id: "hymns", number: 2, label: "Hymns", short: "Hymns", href: "/builder/hymns", previous: "readings", next: "liturgy" },
  { id: "liturgy", number: 3, label: "Liturgy", short: "Liturgy", href: "/builder/liturgy", previous: "hymns", next: "review" },
  { id: "review", number: 4, label: "Review & send", short: "Review", href: "/builder/review", previous: "liturgy", next: null },
];

export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>([]);

export function stepById(id: StepId): Step {
  const step = STEPS.find((s) => s.id === id);
  if (!step) throw new Error(`Unknown step ${id}`);
  return step;
}

/** The step a builder path belongs to ("/builder/hymns" → "hymns"); null for "/builder" and anything else. */
export function stepFromPath(pathname: string): StepId | null {
  const match = /^\/builder\/([a-z]+)\/?$/.exec(pathname);
  if (!match) return null;
  return STEPS.some((s) => s.id === match[1]) ? (match[1] as StepId) : null;
}
```

Create `frontend/src/lib/draft/status.ts`:

```ts
/**
 * Step status, "nothing to lose" and "Still needed" (F §4.7; S "status.ts").
 * Pure functions of the draft; the shell decides what an unshipped step shows.
 */
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { cleanLines } from "@/lib/scripture-refs";

import { SECTION_KEYS, SLOTS, type DraftV1, type StepId } from "./schema";
import { SHIPPED_STEPS } from "./steps";

export type StepStatus =
  | { kind: "complete" }
  | { kind: "incomplete"; done: number; total: number }
  /** A step whose content has not shipped: the muted "Soon". */
  | { kind: "soon" }
  /** Review before slice 5a (and a draft that was never saved). */
  | { kind: "not_in_archive" };

function counted(done: number, total: number): StepStatus {
  return done === total ? { kind: "complete" } : { kind: "incomplete", done, total };
}

/** A date the lectionary lookup and the archive accept. */
export function hasServiceDate(draft: DraftV1): boolean {
  return isValidDateIso(draft.readings.date_iso) && inSupportedRange(draft.readings.date_iso);
}

/**
 * F §4.7: readings count a valid date, a non-empty occasion and at least one
 * scripture ("n of 3"); hymns the three slots; liturgy the enabled cards that
 * have text. Review reads "Not in archive" until 5a adds "Saved" and
 * "Unsaved changes". An unshipped step (other than Review) is "Soon".
 */
export function stepStatus(
  draft: DraftV1,
  step: StepId,
  shipped: ReadonlySet<StepId> = SHIPPED_STEPS,
): StepStatus {
  if (step === "review") return { kind: "not_in_archive" };
  if (!shipped.has(step)) return { kind: "soon" };
  if (step === "readings") {
    const r = draft.readings;
    const done = [hasServiceDate(draft), r.occasion.trim() !== "", cleanLines(r.scriptures).length > 0];
    return counted(done.filter(Boolean).length, 3);
  }
  if (step === "hymns") {
    return counted(SLOTS.filter((slot) => draft.hymns.slots[slot] !== null).length, SLOTS.length);
  }
  const enabled = SECTION_KEYS.map((key) => draft.liturgy.cards[key]).filter((card) => card.enabled);
  return counted(enabled.filter((card) => card.text.trim() !== "").length, enabled.length);
}

/**
 * "Nothing the user would lose" (S "status.ts"), decided by origins rather
 * than text, so defaults that later slices fill in (slice 4's benediction)
 * never make a fresh draft look edited.
 */
export function isPristine(draft: DraftV1): boolean {
  const r = draft.readings;
  const l = draft.liturgy;
  return (
    (r.fields_origin === "empty" || r.fields_origin === "lectionary") &&
    r.selected_ot_ref === "" &&
    r.selected_nt_ref === "" &&
    SLOTS.every((slot) => draft.hymns.slots[slot] === null) &&
    SECTION_KEYS.every((key) => {
      const card = l.cards[key];
      return card.origin === "default" || (card.origin === "empty" && card.text === "");
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title === "" &&
    l.custom_elements.length === 0 &&
    draft.editing === null
  );
}

export type NeededItem = {
  step: StepId;
  /** "No service date" */
  message: string;
  /** The link text: "Choose one" */
  action: string;
};

/** What Review lists under "Still needed", from shipped steps only; slices 3 and 4 add their rows. */
export function stillNeeded(draft: DraftV1, shipped: ReadonlySet<StepId> = SHIPPED_STEPS): NeededItem[] {
  const items: NeededItem[] = [];
  if (shipped.has("readings")) {
    if (!hasServiceDate(draft)) items.push({ step: "readings", message: "No service date", action: "Choose one" });
    if (draft.readings.occasion.trim() === "") {
      items.push({ step: "readings", message: "No occasion", action: "Add one" });
    }
    if (cleanLines(draft.readings.scriptures).length === 0) {
      items.push({ step: "readings", message: "No scripture readings", action: "Add one" });
    }
  }
  return items;
}
```

Create `frontend/src/lib/draft/mapping.ts`:

```ts
/**
 * Draft → API payload, PROVISIONAL (S "mapping.ts"; F §4.6 "Draft → API
 * payload"). Slice 5a owns this file and replaces it with the real
 * `ServiceDraft` mapping and `serviceToDraft`. Slice 2 uses it only for
 * `fingerprint`, so `isDirty` has something stable to compare.
 *
 * One rule 5a's replacement must keep: the picks sent are the explicit values
 * of `resolveReadings`, so a pick that is no longer an option is sent as "",
 * whatever the stored draft says (S Hand-offs, 5a "Bulletin readings").
 */
import { cleanLines } from "@/lib/scripture-refs";

import { effectivePicks } from "./readings";
import { SECTION_KEYS, SLOTS, type DraftV1, type HymnPick, type SectionKey, type Slot } from "./schema";

/** Inventory §2.1's `HymnRef`. */
export type HymnRefPayload = { hymn_id: string | null; title: string; number: number | null; hymnal: string | null };

/** Inventory §2.1's `ServiceDraft` plus `hymnal` (F §1.3), written by hand until 5a adds the API model. */
export type ServiceDraftPayload = {
  service_date_iso: string;
  occasion: string;
  scriptures: string[];
  hymns: Record<Slot, HymnRefPayload | null>;
  liturgy: Partial<Record<SectionKey, string>>;
  sermon_title: string;
  selected_ot_ref: string;
  selected_nt_ref: string;
  include_communion: boolean;
  custom_elements: { label: string; text: string; insert_after: string }[];
  hymnal: string | null;
};

function hymnRef(pick: HymnPick | null): HymnRefPayload | null {
  return pick ? { hymn_id: pick.hymn_id, title: pick.title, number: pick.number, hymnal: pick.hymnal } : null;
}

export function draftToServicePayload(draft: DraftV1): ServiceDraftPayload {
  const picks = effectivePicks(draft);
  const liturgy: Partial<Record<SectionKey, string>> = {};
  for (const key of SECTION_KEYS) {
    const card = draft.liturgy.cards[key];
    if (card.enabled && card.text.trim() !== "") liturgy[key] = card.text;
  }
  return {
    service_date_iso: draft.readings.date_iso,
    occasion: draft.readings.occasion,
    scriptures: cleanLines(draft.readings.scriptures),
    hymns: Object.fromEntries(SLOTS.map((slot) => [slot, hymnRef(draft.hymns.slots[slot])])) as Record<
      Slot,
      HymnRefPayload | null
    >,
    liturgy,
    sermon_title: draft.liturgy.sermon_title,
    selected_ot_ref: picks.otAuto ? "" : (picks.ot ?? ""),
    selected_nt_ref: picks.ntAuto ? "" : (picks.nt ?? ""),
    include_communion: draft.liturgy.include_communion,
    custom_elements: draft.liturgy.custom_elements.map(({ label, text, insert_after }) => ({
      label,
      text,
      insert_after,
    })),
    hymnal: draft.hymns.hymnal,
  };
}
```

Create `frontend/src/lib/draft/fingerprint.ts`:

```ts
/**
 * Unsaved-changes detection (F §4.6 "Unsaved changes"; S "fingerprint.ts").
 * `fingerprint` is 32-bit FNV-1a over a stable JSON string (object keys
 * sorted at every level), as 8 hex digits.
 */
import { draftToServicePayload } from "./mapping";
import type { DraftV1 } from "./schema";
import { isPristine } from "./status";

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, stable((value as Record<string, unknown>)[key])]),
    );
  }
  return value;
}

/** JSON with every object's keys sorted, so key order never changes the fingerprint. */
export function stableStringify(value: unknown): string {
  return JSON.stringify(stable(value));
}

/** 32-bit FNV-1a of the UTF-16 code units, as 8 hex digits. */
export function fnv1a32(text: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function fingerprint(payload: unknown): string {
  return fnv1a32(stableStringify(payload));
}

/** Never saved: dirty means not pristine. Saved or loaded: the payload differs from what was saved. */
export function isDirty(draft: DraftV1): boolean {
  if (draft.saved_fingerprint === null) return !isPristine(draft);
  return fingerprint(draftToServicePayload(draft)) !== draft.saved_fingerprint;
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/status.test.ts src/lib/draft/mapping.test.ts src/lib/draft/fingerprint.test.ts 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** `Test Files  3 passed (3)`, `Tests  12 passed (12)`; `Test Files  43 passed (43)`, `Tests  268 passed (268)`; `> tsc --noEmit`, `> eslint`, nothing after.

- [ ] **Step 6 (agent): Commit and back up**

```bash
git add frontend/src/lib/draft/steps.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/draft/mapping.ts frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/fingerprint.ts frontend/src/lib/draft/fingerprint.test.ts
git commit -m "Draft: steps, step status, the provisional payload and its fingerprint (F §4.6, §4.7; S status.ts, mapping.ts; AC8)" -m "STEPS and SHIPPED_STEPS (empty until 2c: owner answer Q1), stepStatus per
F §4.7 behind SHIPPED_STEPS, isPristine by origins (a default benediction
never counts as an edit), stillNeeded for shipped steps, the provisional
draftToServicePayload (5a replaces it; a stale pick is sent as \"\"), and
FNV-1a fingerprint with isDirty. Frontend 256 -> 268.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T5):** `SHIPPED_STEPS` is empty; `isPristine` matches S "status.ts" item by item; the payload's picks come from `effectivePicks` (never the raw stored picks); `status.ts` does not import `fingerprint.ts` (no cycle; clarification 13).

### Task 6: The draft store: load, debounced writes, memory-only mode and cross-tab adoption (F §4.6 "Key", "Persistence", "Versioning", "Fresh draft"; S "store.ts / context.tsx", "Mount-time roll-forward", Testing `store.test.ts`; AC10; clarifications 6–9, 23, 32)

`DraftStore` is a plain class, so its rules are unit-tested in the node project with an in-memory storage and a hand-moved clock; T7 wires it to React and the browser. It reads the stored draft once in its constructor (safe during a render) and does every write in `start`, timers or `flush`. `lib/storage.ts` gains the two helpers the store and pruning need (clarification 6).

**Files:**
- Modify: `frontend/src/lib/storage.ts` (`tryWriteLocal`, `localKeys`), `frontend/src/lib/storage.test.ts` (+1 test)
- Create: `frontend/src/lib/draft/store.ts`
- Test: `frontend/src/lib/draft/store.test.ts` (new, 11 tests)

**Interfaces:**
- Consumes: T1 `isValidDateIso`, `nextSunday`, `todayIn`; T3 `freshDraft`, `churchZone`, `draftKey`, `corruptDraftKey`, `parseStoredDraft`, `DraftChurch`, `DraftV1`, `StepId`; T4 `normalizePicks`, `setDate` (and the transitions in tests); T5 `isPristine`, `draftToServicePayload` (test); `lib/storage.ts` `readLocal`, `removeLocal`.
- Produces:
  - `lib/storage.ts`: `tryWriteLocal(key, value): boolean` (false when storage is missing, blocked or full), `localKeys(): string[]` ([] when missing or blocked). Later user: T7 (`prune.ts`).
  - `lib/draft/store.ts`: `WRITE_DELAY_MS = 400`; `type Persistence = "ok" | "memory-only"`; `type DraftNotice = "restore_failed" | "memory_only" | "adopted"`; `type DraftSnapshot = { draft; persistence }`; `type DraftStorage = { read; write(key, value): boolean; remove }`; `browserDraftStorage`; `rollForward(draft, today)`; `class DraftStore` with `key`, `getSnapshot()`, `subscribe(listener)`, `start()`, `update(recipe)`, `replace(next)`, `setLastStep(step)`, `handleStorageEvent(key, newValue)`, `flush()` (the last five and the two store functions are bound arrow properties, safe to pass as callbacks). Later user: T7 (`DraftProvider`).

Counts after this task: frontend **280 passed in 44 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/draft/store.ts && echo "no T6 files yet"
grep -cE "export function (tryWriteLocal|localKeys)" frontend/src/lib/storage.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T6 files yet`; `0`; `Test Files  43 passed (43)`, `Tests  268 passed (268)`.

- [ ] **Step 2 (agent): Write the failing tests**

In `frontend/src/lib/storage.test.ts`, add `localKeys,` after `SESSION_KEYS,` and `tryWriteLocal,` after `removeSession,` in the import list, and add this test as the last one inside `describe("storage", …)`:

```ts
  it("tryWriteLocal says whether it stored the value, and localKeys lists keys (slice 2b drafts)", () => {
    vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
    expect(tryWriteLocal("wsb:draft:u:c", "{}")).toBe(true);
    writeLocal(ACTIVE_CHURCH_KEY, "c");
    writeSession("session-only", "x");
    expect(readLocal("wsb:draft:u:c")).toBe("{}");
    expect(localKeys().sort()).toEqual([ACTIVE_CHURCH_KEY, "wsb:draft:u:c"]);

    vi.stubGlobal("window", { sessionStorage: throwingStorage(), localStorage: throwingStorage() });
    expect(tryWriteLocal("k", "v")).toBe(false);
    expect(localKeys()).toEqual([]);

    vi.unstubAllGlobals();
    expect(tryWriteLocal("k", "v")).toBe(false);
    expect(localKeys()).toEqual([]);
  });
```

Create `frontend/src/lib/draft/store.test.ts` (S Testing `store.test.ts`: debounced write; the key includes the user and church; a newer `storage` event is adopted with its stale picks normalized and an equal one is not; a failed write → `memory-only`; roll-forward of a pristine past default date, including one whose benediction holds default text, and not of a non-pristine one; a recipe returning the same object neither bumps nor writes; the auto-apply recipe sees the latest draft; `setLastStep` writes without bumping `updated_at`; a stored stale `selected_ot_ref` loads as "" and the un-normalized payload already sends ""; `replace` normalizes picks. Corrupt, invalid and future-version drafts are backed up, replaced by a fresh draft and reported once. The flush on `pagehide` is the provider's and is tested in T7):

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CHURCH_IDS, churchProfile, DRAFT_NOW, lectionary, testDraft, USER_ID } from "@/test/fixtures";

import { draftToServicePayload } from "./mapping";
import { applyReadingSet, editOccasion, editScriptureLines, setPick, shouldAutoApply } from "./readings";
import { corruptDraftKey, draftKey, type DraftV1 } from "./schema";
import { DraftStore, WRITE_DELAY_MS, type DraftNotice, type DraftStorage } from "./store";

const GRACE = churchProfile();
const KEY = draftKey(USER_ID, GRACE.id);

/** A Map-backed storage that records writes; `failWrites` makes every write fail (quota). */
function memoryStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  const writes: string[] = [];
  const storage: DraftStorage & { failWrites: boolean } = {
    failWrites: false,
    read: (key) => data.get(key) ?? null,
    write: (key, value) => {
      writes.push(key);
      if (storage.failWrites) return false;
      data.set(key, value);
      return true;
    },
    remove: (key) => {
      data.delete(key);
    },
  };
  return { storage, data, writes };
}

/** A clock the test moves by hand, starting at DRAFT_NOW (Tuesday, September 29, 2026). */
function clock(start = DRAFT_NOW) {
  let t = start.getTime();
  return { now: () => new Date(t), advance: (ms: number) => (t += ms) };
}

function makeStore(storage: DraftStorage, now = clock().now) {
  const notices: DraftNotice[] = [];
  const store = new DraftStore({ userId: USER_ID, church: GRACE, storage, now, notify: (n) => notices.push(n) });
  return { store, notices };
}

function stored(data: Map<string, string>, key = KEY): DraftV1 {
  return JSON.parse(data.get(key) ?? "null") as DraftV1;
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("DraftStore load (F §4.6 Versioning)", () => {
  it("starts a fresh draft under the user and church key and writes it 400 ms after start", () => {
    const { storage, data } = memoryStorage();
    const { store, notices } = makeStore(storage);
    expect(store.key).toBe(`wsb:draft:${USER_ID}:${GRACE.id}`);
    expect(store.getSnapshot()).toMatchObject({ persistence: "ok", draft: { readings: { date_iso: "2026-10-04" } } });
    expect(data.size).toBe(0); // nothing is written during a render
    store.start();
    vi.advanceTimersByTime(WRITE_DELAY_MS - 1);
    expect(data.size).toBe(0);
    vi.advanceTimersByTime(1);
    expect(stored(data)).toEqual(store.getSnapshot().draft);
    expect(notices).toEqual([]);
  });

  it("loads a valid stored draft as it is and writes nothing", () => {
    const saved = editOccasion(testDraft(), "Harvest");
    const { storage, writes } = memoryStorage({ [KEY]: JSON.stringify(saved) });
    const { store } = makeStore(storage);
    store.start();
    vi.runAllTimers();
    expect(store.getSnapshot().draft).toEqual(saved);
    expect(writes).toEqual([]);
  });

  it("backs up a draft it cannot restore, starts fresh and reports it once", () => {
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 2 }), JSON.stringify({ version: 1 })]) {
      const { storage, data } = memoryStorage({ [KEY]: raw });
      const { store, notices } = makeStore(storage);
      store.start();
      store.start(); // StrictMode runs effects twice
      expect(data.get(corruptDraftKey(USER_ID, GRACE.id))).toBe(raw);
      expect(notices).toEqual(["restore_failed"]);
      vi.runAllTimers();
      expect(stored(data).readings.fields_origin).toBe("empty");
      expect(stored(data).save_key).toBe(store.getSnapshot().draft.save_key);
    }
  });

  it("normalizes a stale pick left by a refresh while the textarea had focus, and the payload already sends \"\"", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const stale = editScriptureLines(setPick(filled, "ot", "Psalm 80:7-15"), "Isaiah 5:1-7\nPhilippians 3:4b-14");
    expect(draftToServicePayload(stale).selected_ot_ref).toBe("");
    const { storage, data } = memoryStorage({ [KEY]: JSON.stringify(stale) });
    const { store } = makeStore(storage);
    expect(store.getSnapshot().draft.readings.selected_ot_ref).toBe("");
    store.start();
    vi.runAllTimers();
    expect(stored(data).readings.selected_ot_ref).toBe("");
  });

  it("rolls a pristine draft's passed default date forward, even with a default benediction, but not an edited one", () => {
    const pastPristine = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Halverson", origin: "default" } },
      },
    }));
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const rolled = makeStore(memoryStorage({ [KEY]: JSON.stringify(pastPristine) }).storage, tenDaysLater.now).store;
    expect(rolled.getSnapshot().draft.readings).toMatchObject({ date_iso: "2026-10-11", date_origin: "default" });
    expect(rolled.getSnapshot().draft.liturgy.include_communion).toBe(false);
    expect(rolled.getSnapshot().draft.updated_at).toBe(tenDaysLater.now().toISOString());

    const edited = editOccasion(pastPristine, "Harvest");
    const kept = makeStore(memoryStorage({ [KEY]: JSON.stringify(edited) }).storage, tenDaysLater.now).store;
    expect(kept.getSnapshot().draft.readings.date_iso).toBe("2026-10-04");
  });
});

describe("DraftStore changes (S store.ts)", () => {
  it("debounces writes, bumps updated_at, and ignores a recipe that returns the same draft", () => {
    const { storage, data, writes } = memoryStorage({ [KEY]: JSON.stringify(testDraft()) });
    const time = clock();
    const { store } = makeStore(storage, time.now);
    store.start();
    const listener = vi.fn();
    store.subscribe(listener);

    store.update((d) => d);
    vi.runAllTimers();
    expect(writes).toEqual([]);
    expect(listener).not.toHaveBeenCalled();

    time.advance(1_000);
    store.update((d) => editOccasion(d, "Harv"));
    vi.advanceTimersByTime(200);
    store.update((d) => editOccasion(d, "Harvest"));
    vi.advanceTimersByTime(WRITE_DELAY_MS - 1);
    expect(writes).toEqual([]);
    vi.advanceTimersByTime(1);
    expect(writes).toEqual([KEY]);
    expect(stored(data).readings.occasion).toBe("Harvest");
    expect(stored(data).updated_at).toBe(time.now().toISOString());
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("applies each recipe to the latest draft, so an edit in the same tick survives an auto-fill", () => {
    const { storage } = memoryStorage();
    const { store } = makeStore(storage);
    const lect = lectionary("2026-10-04");
    store.update((d) => editOccasion(d, "Harvest Sunday"));
    store.update((d) => (shouldAutoApply(d, lect) ? applyReadingSet(d, lect, 0) : d));
    expect(store.getSnapshot().draft.readings).toMatchObject({ occasion: "Harvest Sunday", fields_origin: "user" });
  });

  it("setLastStep writes the step but leaves updated_at alone", () => {
    const saved = testDraft();
    const { storage, data } = memoryStorage({ [KEY]: JSON.stringify(saved) });
    const { store } = makeStore(storage);
    store.setLastStep("readings");
    vi.runAllTimers();
    expect(data.get(KEY)).toBe(JSON.stringify(saved)); // unchanged: already "readings"
    store.setLastStep("hymns");
    vi.runAllTimers();
    expect(stored(data)).toMatchObject({ last_step: "hymns", updated_at: saved.updated_at });
  });

  it("replace stores the next draft with normalized picks and a new updated_at", () => {
    const { storage, data } = memoryStorage();
    const time = clock();
    const { store } = makeStore(storage, time.now);
    time.advance(5_000);
    const next = setPick(testDraft(), "nt", "Matthew 21:33-46"); // no scripture lines: a stale pick
    store.replace(next);
    vi.runAllTimers();
    expect(stored(data)).toMatchObject({
      save_key: next.save_key,
      updated_at: time.now().toISOString(),
      readings: { selected_nt_ref: "" },
    });
  });

  it("switches to memory-only when a write fails, and reports it once", () => {
    const { storage } = memoryStorage();
    storage.failWrites = true;
    const { store, notices } = makeStore(storage);
    store.start();
    vi.runAllTimers();
    expect(store.getSnapshot().persistence).toBe("memory-only");
    store.update((d) => editOccasion(d, "Harvest"));
    store.flush();
    expect(notices).toEqual(["memory_only"]);
    expect(store.getSnapshot().draft.readings.occasion).toBe("Harvest"); // still in memory
  });

  it("adopts another tab's strictly newer draft (normalized) and ignores equal, foreign or broken ones", () => {
    const base = testDraft();
    const { storage, writes } = memoryStorage({ [KEY]: JSON.stringify(base) });
    const { store, notices } = makeStore(storage);
    store.update((d) => editOccasion(d, "Mine")); // a pending write
    const mine = store.getSnapshot().draft;

    store.handleStorageEvent(KEY, JSON.stringify({ ...mine, readings: { ...mine.readings, occasion: "Same time" } }));
    store.handleStorageEvent(draftKey(USER_ID, CHURCH_IDS.hope), JSON.stringify({ ...mine, church_id: CHURCH_IDS.hope }));
    store.handleStorageEvent(KEY, "{broken");
    store.handleStorageEvent(KEY, null);
    expect(store.getSnapshot().draft).toBe(mine);

    const filled = applyReadingSet(base, lectionary("2026-10-04"), 0);
    const theirs = {
      ...setPick(editScriptureLines(filled, "Isaiah 5:1-7"), "nt", "Matthew 21:33-46"),
      updated_at: new Date(Date.parse(mine.updated_at) + 1).toISOString(),
    };
    store.handleStorageEvent(KEY, JSON.stringify(theirs));
    expect(store.getSnapshot().draft).toEqual({ ...theirs, readings: { ...theirs.readings, selected_nt_ref: "" } });
    expect(notices).toEqual(["adopted"]);
    vi.runAllTimers();
    expect(writes).toEqual([]); // my pending write was dropped: theirs is newer
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/storage.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "FAIL|Error|Tests ")
```

**Expected:** ` FAIL  |unit| src/lib/draft/store.test.ts` with `Error: Cannot find module './store'`; the new storage test fails with `TypeError: (0 , tryWriteLocal) is not a function`; `Tests  1 failed | 4 passed (5)`.

- [ ] **Step 4 (agent): Add the storage helpers**

Append to `frontend/src/lib/storage.ts`:

```ts

/**
 * Like `writeLocal`, but says whether the value was stored: false when storage
 * is missing, blocked or full. The draft store needs to know, so it can switch
 * to memory-only and warn once (F §4.6 "Persistence").
 */
export function tryWriteLocal(key: string, value: string): boolean {
  if (typeof window === "undefined") return false;
  try {
    window.localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

/** Every localStorage key, or [] when storage is missing or blocked (draft pruning). */
export function localKeys(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const storage = window.localStorage;
    const keys: string[] = [];
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      if (key !== null) keys.push(key);
    }
    return keys;
  } catch {
    return [];
  }
}
```

- [ ] **Step 5 (agent): Write the store**

Create `frontend/src/lib/draft/store.ts`:

```ts
/**
 * The draft store (F §4.6 "Persistence", "Versioning"; S "store.ts"): one
 * user's draft for one church, loaded from and written to
 * `localStorage["wsb:draft:{userId}:{churchId}"]` through `lib/storage.ts`.
 *
 * - Load: parse → migrate → validate → `normalizePicks`. A stored value that
 *   cannot be restored is copied to the corrupt-draft key, a fresh draft
 *   starts, and a "restore_failed" notice follows. A pristine draft whose
 *   default date has passed rolls forward to the next Sunday.
 * - `update(recipe)` applies the recipe to the latest draft, bumps
 *   `updated_at` and schedules a write 400 ms later; a recipe that returns the
 *   same object does nothing. `setLastStep` changes only `last_step` and
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
 * - A failed write switches to memory-only with one "memory_only" notice.
 * - Another tab's write for this key is adopted when its `updated_at` is
 *   strictly newer ("adopted").
 *
 * React wiring (listeners, toasts, flush on hide and unmount) is in
 * `context.tsx`. This class touches storage only in `start`, `flush` and the
 * constructor's single read, so it can be built during a render.
 */
import { isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { readLocal, removeLocal, tryWriteLocal } from "@/lib/storage";

import { parseStoredDraft } from "./migrate";
import { normalizePicks, setDate } from "./readings";
import { churchZone, corruptDraftKey, draftKey, freshDraft, type DraftChurch, type DraftV1, type StepId } from "./schema";
import { isPristine } from "./status";

export const WRITE_DELAY_MS = 400;

export type Persistence = "ok" | "memory-only";
export type DraftNotice = "restore_failed" | "memory_only" | "adopted";
export type DraftSnapshot = { readonly draft: DraftV1; readonly persistence: Persistence };

/** Where drafts live; the browser's is `lib/storage.ts`, tests pass a Map. */
export type DraftStorage = {
  read(key: string): string | null;
  /** False when the value could not be stored. */
  write(key: string, value: string): boolean;
  remove(key: string): void;
};

export const browserDraftStorage: DraftStorage = { read: readLocal, write: tryWriteLocal, remove: removeLocal };

export type DraftStoreOptions = {
  userId: string;
  church: DraftChurch;
  storage?: DraftStorage;
  now?: () => Date;
  notify?: (notice: DraftNotice) => void;
};

/** The pristine draft's passed default date moves to the next Sunday (S "Mount-time roll-forward"). */
export function rollForward(draft: DraftV1, today: string): DraftV1 {
  const r = draft.readings;
  if (r.date_origin !== "default" || !isValidDateIso(r.date_iso) || r.date_iso >= today || !isPristine(draft)) {
    return draft;
  }
  return setDate(draft, nextSunday(today), "default");
}

function isNewer(candidate: string, current: string): boolean {
  const a = Date.parse(candidate);
  const b = Date.parse(current);
  return Number.isFinite(a) && (!Number.isFinite(b) || a > b);
}

export class DraftStore {
  readonly key: string;
  private readonly corruptKey: string;
  private readonly userId: string;
  private readonly churchId: string;
  private readonly storage: DraftStorage;
  private readonly now: () => Date;
  private readonly notify: (notice: DraftNotice) => void;
  private snapshot: DraftSnapshot;
  private readonly listeners = new Set<() => void>();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private pendingWrite = false;
  private started = false;
  private warnedMemoryOnly = false;
  /** The raw value that could not be restored, backed up in `start`. */
  private corruptRaw: string | null = null;

  constructor({ userId, church, storage = browserDraftStorage, now = () => new Date(), notify = () => {} }: DraftStoreOptions) {
    this.userId = userId;
    this.churchId = church.id;
    this.key = draftKey(userId, church.id);
    this.corruptKey = corruptDraftKey(userId, church.id);
    this.storage = storage;
    this.now = now;
    this.notify = notify;

    const fresh = () => freshDraft({ church, user: { id: userId }, now: now() });
    const raw = storage.read(this.key);
    let draft: DraftV1;
    if (raw === null) {
      draft = fresh();
      this.pendingWrite = true;
    } else {
      try {
        const stored = parseStoredDraft(raw, { userId, churchId: church.id });
        draft = normalizePicks(stored);
        this.pendingWrite = draft !== stored;
      } catch {
        this.corruptRaw = raw;
        draft = fresh();
        this.pendingWrite = true;
      }
    }
    const rolled = rollForward(draft, todayIn(churchZone(church), now()));
    if (rolled !== draft) {
      draft = { ...rolled, updated_at: now().toISOString() };
      this.pendingWrite = true;
    }
    this.snapshot = { draft, persistence: "ok" };
  }

  getSnapshot = (): DraftSnapshot => this.snapshot;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  /** Once, after mount: back up a draft that could not be restored, report it, and write what load changed. */
  start(): void {
    if (this.started) return;
    this.started = true;
    if (this.corruptRaw !== null) {
      this.storage.write(this.corruptKey, this.corruptRaw);
      this.notify("restore_failed");
    }
    if (this.pendingWrite) this.schedule();
  }

  update = (recipe: (d: DraftV1) => DraftV1): void => {
    const next = recipe(this.snapshot.draft);
    if (next === this.snapshot.draft) return;
    this.set({ ...next, updated_at: this.now().toISOString() });
    this.schedule();
  };

  replace = (next: DraftV1): void => {
    this.set(normalizePicks({ ...next, updated_at: this.now().toISOString() }));
    this.schedule();
  };

  setLastStep = (step: StepId): void => {
    if (this.snapshot.draft.last_step === step) return;
    this.set({ ...this.snapshot.draft, last_step: step });
    this.schedule();
  };

  /** A `storage` event: adopt another tab's strictly newer draft for this key. */
  handleStorageEvent(key: string | null, newValue: string | null): void {
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
  }

  /** Writes a scheduled change now (hide, pagehide, unmount). */
  flush = (): void => {
    if (!this.pendingWrite) return;
    this.cancelWrite();
    const ok = this.storage.write(this.key, JSON.stringify(this.snapshot.draft));
    const persistence: Persistence = ok ? "ok" : "memory-only";
    if (persistence !== this.snapshot.persistence) {
      this.snapshot = { ...this.snapshot, persistence };
      this.emit();
    }
    if (!ok && !this.warnedMemoryOnly) {
      this.warnedMemoryOnly = true;
      this.notify("memory_only");
    }
  };

  private schedule(): void {
    this.pendingWrite = true;
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = setTimeout(this.flush, WRITE_DELAY_MS);
  }

  private cancelWrite(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.pendingWrite = false;
  }

  private set(draft: DraftV1): void {
    this.snapshot = { ...this.snapshot, draft };
    this.emit();
  }

  private emit(): void {
    for (const listener of this.listeners) listener();
  }
}
```

- [ ] **Step 6 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/storage.test.ts src/lib/draft/store.test.ts 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** `Test Files  2 passed (2)`, `Tests  16 passed (16)` (storage 5, store 11); `Test Files  44 passed (44)`, `Tests  280 passed (280)`; `> tsc --noEmit`, `> eslint`, nothing after.

- [ ] **Step 7 (agent): Commit and back up**

```bash
git add frontend/src/lib/storage.ts frontend/src/lib/storage.test.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/store.test.ts
git commit -m "Draft: the store, with debounced writes, memory-only mode and cross-tab adoption (F §4.6; S store.ts; AC10)" -m "DraftStore loads the user's draft for the church (parse, migrate,
validate, normalize picks; a draft it cannot restore is backed up to the
corrupt-draft key and replaced by a fresh one), rolls a pristine passed
default date forward, applies update recipes to the latest draft, writes
400 ms after the last change, never bumps updated_at for setLastStep,
switches to memory-only with one notice when a write fails, and adopts
another tab's strictly newer draft. lib/storage.ts gains tryWriteLocal and
localKeys. Frontend 268 -> 280.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T6):** nothing writes during construction (only `start`, timers and `flush`); `update` returns early on the same object; `setLastStep` never touches `updated_at`; adoption requires a strictly newer `updated_at`, cancels this tab's pending write and normalizes picks; the one memory-only notice.

### Task 7: `DraftProvider` and `useDraft`, the toasts, and pruning after `/me` (F §4.6 "Persistence", "When the draft is cleared or replaced" items 3 and 4; S "store.ts / context.tsx", "prune.ts", "Other states and messages", Testing `store.test.ts` flush half and `prune.test.ts`; AC10; clarifications 21, 25, 26)

`DraftProvider` builds one `DraftStore` for the user and church, exposes S's `DraftApi` through `useDraft()`, and connects the store to the browser: `storage` events from other tabs, a flush when the page is hidden or left, a flush on unmount (a church switch), and the three toasts. `pruneDrafts` removes this user's drafts older than 30 days and those for churches they left, with their backups; the `(signed-in)` layout calls it whenever `/me` loads.

**Files:**
- Create: `frontend/src/lib/draft/context.tsx`, `frontend/src/lib/draft/prune.ts`
- Modify: `frontend/src/app/(signed-in)/layout.tsx` (prune after `/me`)
- Test: `frontend/src/lib/draft/context.test.tsx` (new, 4 tests), `frontend/src/lib/draft/prune.test.ts` (new, 3 tests), `frontend/src/app/(signed-in)/signed-in-layout.test.tsx` (+1 test)

**Interfaces:**
- Consumes: T3 `DraftChurch`, `DraftV1`, `StepId`, `draftKey`, `corruptDraftKey`, `testDraft`, `churchProfile`; T4 `editOccasion` (tests); T6 `DraftStore`, `DraftNotice`, `Persistence`, `localKeys`; `lib/storage.ts` `readLocal`, `removeLocal`; sonner `toast`; `useMe` in the `(signed-in)` layout (1a/1b).
- Produces:
  - `lib/draft/context.tsx`: `type DraftApi = { draft; update(recipe); replace(next); setLastStep(step); persistence }` (S's signature), `DRAFT_MESSAGES`, `DraftProvider({ userId, church, children })`, `useDraft(): DraftApi` (throws outside the provider). Later users: T9 (`BuilderShell`, the shell components, the builder index page), 2c (every readings component, `useLectionarySync`), 3, 4, 5a.
  - `lib/draft/prune.ts`: `PRUNE_AFTER_MS` (30 days), `pruneDrafts(userId, churchIds, now?) → string[]` (the removed draft keys).

Counts after this task: frontend **288 passed in 46 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/lib/draft/context.tsx && test ! -e frontend/src/lib/draft/prune.ts && echo "no T7 files yet"
grep -c "pruneDrafts" 'frontend/src/app/(signed-in)/layout.tsx'
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T7 files yet`; `0`; `Test Files  44 passed (44)`, `Tests  280 passed (280)`.

- [ ] **Step 2 (agent): Write the failing tests**

Create `frontend/src/lib/draft/context.test.tsx`:

```tsx
import { act, render, renderHook, screen } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from "vitest";

import { churchProfile, testDraft, USER_ID } from "@/test/fixtures";

import { DRAFT_MESSAGES, DraftProvider, useDraft } from "./context";
import { editOccasion } from "./readings";
import { corruptDraftKey, draftKey, type DraftV1 } from "./schema";

const GRACE = churchProfile();
const KEY = draftKey(USER_ID, GRACE.id);

function Probe() {
  const { draft, update, persistence } = useDraft();
  return (
    <div>
      <p>Occasion: {draft.readings.occasion || "none"}</p>
      <p>Persistence: {persistence}</p>
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest"))}>
        Edit
      </button>
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest Home"))}>
        Rename
      </button>
    </div>
  );
}

function renderProbe() {
  return render(
    <DraftProvider userId={USER_ID} church={GRACE}>
      <Probe />
    </DraftProvider>,
  );
}

function storedOccasion(): string | undefined {
  const raw = window.localStorage.getItem(KEY);
  return raw === null ? undefined : (JSON.parse(raw) as DraftV1).readings.occasion;
}

describe("DraftProvider and useDraft (F §4.6 Persistence)", () => {
  let toastError: MockInstance<typeof toast.error>;
  let toastWarning: MockInstance<typeof toast.warning>;
  let toastInfo: MockInstance<typeof toast.info>;

  beforeEach(() => {
    toastError = vi.spyOn(toast, "error").mockImplementation(() => 0);
    toastWarning = vi.spyOn(toast, "warning").mockImplementation(() => 0);
    toastInfo = vi.spyOn(toast, "info").mockImplementation(() => 0);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("useDraft throws outside the provider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useDraft())).toThrow("useDraft() must be used inside <DraftProvider>.");
  });

  it("writes before the debounce when the page is hidden or left, and on unmount", () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    const { unmount } = renderProbe();
    const click = (name: string) => act(() => screen.getByRole("button", { name }).click());

    click("Edit");
    expect(screen.getByText("Occasion: Harvest")).toBeInTheDocument();
    expect(storedOccasion()).toBe(""); // the 400 ms write has not run yet
    act(() => window.dispatchEvent(new Event("pagehide")));
    expect(storedOccasion()).toBe("Harvest");

    click("Rename");
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
    expect(storedOccasion()).toBe("Harvest Home");

    click("Edit");
    unmount(); // a church switch unmounts the provider
    expect(storedOccasion()).toBe("Harvest");
  });

  it("adopts a newer draft from another tab and says so", () => {
    const mine = testDraft();
    window.localStorage.setItem(KEY, JSON.stringify(mine));
    renderProbe();
    const theirs = { ...editOccasion(mine, "From the other tab"), updated_at: "2026-09-29T17:00:00.000Z" };
    act(() => {
      window.dispatchEvent(new StorageEvent("storage", { key: KEY, newValue: JSON.stringify(theirs) }));
    });
    expect(screen.getByText("Occasion: From the other tab")).toBeInTheDocument();
    expect(toastInfo).toHaveBeenCalledWith(DRAFT_MESSAGES.adopted, expect.anything());
    expect(DRAFT_MESSAGES.adopted).toBe("Updated from another tab.");
  });

  it("backs up a draft it cannot restore and toasts; a full or blocked storage keeps the draft in memory", () => {
    window.localStorage.setItem(KEY, "{broken");
    const first = renderProbe();
    expect(window.localStorage.getItem(corruptDraftKey(USER_ID, GRACE.id))).toBe("{broken");
    expect(toastError).toHaveBeenCalledWith("We couldn't restore your unsaved draft.", expect.anything());
    first.unmount();

    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("The quota has been exceeded.", "QuotaExceededError");
    });
    renderProbe();
    act(() => screen.getByRole("button", { name: "Edit" }).click());
    act(() => window.dispatchEvent(new Event("pagehide")));
    expect(screen.getByText("Persistence: memory-only")).toBeInTheDocument();
    expect(screen.getByText("Occasion: Harvest")).toBeInTheDocument();
    expect(toastWarning).toHaveBeenCalledTimes(1);
    expect(toastWarning).toHaveBeenCalledWith(
      "This browser isn't saving your draft. Don't refresh until you save.",
      expect.anything(),
    );
  });
});
```

Create `frontend/src/lib/draft/prune.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PRUNE_AFTER_MS, pruneDrafts } from "./prune";

const NOW = new Date(Date.UTC(2026, 8, 29, 16, 0));
const DAY = 24 * 60 * 60 * 1000;

function draftJson(ageMs: number): string {
  return JSON.stringify({ version: 1, updated_at: new Date(NOW.getTime() - ageMs).toISOString() });
}

let data: Map<string, string>;

beforeEach(() => {
  data = new Map();
  const storage = {
    get length() {
      return data.size;
    },
    key: (i: number) => [...data.keys()][i] ?? null,
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
    clear: () => data.clear(),
  };
  vi.stubGlobal("window", { localStorage: storage, sessionStorage: storage });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("pruneDrafts (F §4.6 items 3 and 4)", () => {
  it("removes this user's drafts older than 30 days, with their backups, and keeps newer or undatable ones", () => {
    expect(PRUNE_AFTER_MS).toBe(30 * DAY);
    data.set("wsb:draft:u1:c-old", draftJson(31 * DAY));
    data.set("wsb:draft-corrupt:u1:c-old", "{broken");
    data.set("wsb:draft:u1:c-recent", draftJson(29 * DAY));
    data.set("wsb:draft:u1:c-broken", "{broken");
    const removed = pruneDrafts("u1", ["c-old", "c-recent", "c-broken"], NOW);
    expect(removed).toEqual(["wsb:draft:u1:c-old"]);
    expect([...data.keys()].sort()).toEqual(["wsb:draft:u1:c-broken", "wsb:draft:u1:c-recent"]);
  });

  it("removes drafts and backups for churches the user left, and never another user's keys", () => {
    data.set("wsb:draft:u1:c-left", draftJson(DAY));
    data.set("wsb:draft-corrupt:u1:c-left", "{broken");
    data.set("wsb:draft-corrupt:u1:c-gone", "{broken");
    data.set("wsb:draft:u1:c-member", draftJson(DAY));
    data.set("wsb:draft:u2:c-left", draftJson(90 * DAY));
    data.set("activeChurchId", "c-left");
    pruneDrafts("u1", ["c-member"], NOW);
    expect([...data.keys()].sort()).toEqual(["activeChurchId", "wsb:draft:u1:c-member", "wsb:draft:u2:c-left"]);
  });

  it("does nothing when storage is missing or blocked", () => {
    vi.stubGlobal("window", {
      get localStorage(): Storage {
        throw new Error("SecurityError");
      },
    });
    expect(pruneDrafts("u1", [], NOW)).toEqual([]);
  });
});
```

In `frontend/src/app/(signed-in)/signed-in-layout.test.tsx`, add `import { draftKey } from "@/lib/draft/schema";` above the `@/lib/me-context` import, change `import { me } from "@/test/fixtures";` to `import { CHURCH_IDS, me, USER_ID } from "@/test/fixtures";`, and add this test as the last one inside `describe("(signed-in) layout", …)`:

```tsx
  it("prunes the user's drafts for churches they left once /me loads (F §4.6 item 4)", async () => {
    const left = draftKey(USER_ID, CHURCH_IDS.hope); // Pat is a member of Grace only
    const kept = draftKey(USER_ID, CHURCH_IDS.grace);
    const draft = JSON.stringify({ version: 1, updated_at: new Date().toISOString() });
    window.localStorage.setItem(left, draft);
    window.localStorage.setItem(kept, draft);
    installFakeApi({ "GET /me": me() });
    renderLayout();

    expect(await screen.findByText("pat@example.com")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(left)).toBeNull());
    expect(window.localStorage.getItem(kept)).toBe(draft);
  });
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft/context.test.tsx src/lib/draft/prune.test.ts 'src/app/(signed-in)/signed-in-layout.test.tsx' 2>&1 | grep -E "FAIL|Error|Tests |×")
```

**Expected:** ` FAIL  |dom| src/lib/draft/context.test.tsx` with `Error: Failed to resolve import "./context"`; ` FAIL  |unit| src/lib/draft/prune.test.ts` with `Error: Cannot find module './prune'`; the layout's new test fails its `waitFor` with `expected '{"version":1,"updated_at":"…' to be null`; `Tests  1 failed | 7 passed (8)`.

- [ ] **Step 4 (agent): Write the provider and the pruning**

Create `frontend/src/lib/draft/context.tsx`:

```tsx
"use client";

/**
 * `DraftProvider` and `useDraft()` (F §4.6; S "store.ts / context.tsx").
 * `BuilderShell` renders the provider for the signed-in user and the active
 * church; the `(church)` layout's keyed remount already gives each church its
 * own provider. The provider wires the store to the browser: another tab's
 * writes (`storage` events), a flush when the page is hidden or left, a flush
 * on unmount (a church switch), and the three toasts.
 */
import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { toast } from "sonner";

import type { DraftChurch, DraftV1, StepId } from "./schema";
import { DraftStore, type DraftNotice, type Persistence } from "./store";

export type DraftApi = {
  draft: DraftV1;
  /** Applies the recipe to the latest draft; a recipe that returns the same object does nothing. */
  update: (recipe: (d: DraftV1) => DraftV1) => void;
  /** New service; slice 5a's archive load. */
  replace: (next: DraftV1) => void;
  /** Navigation only: never bumps `updated_at`. */
  setLastStep: (step: StepId) => void;
  persistence: Persistence;
};

export const DRAFT_MESSAGES = {
  restore_failed: "We couldn't restore your unsaved draft.",
  memory_only: "This browser isn't saving your draft. Don't refresh until you save.",
  adopted: "Updated from another tab.",
} as const satisfies Record<DraftNotice, string>;

function notify(notice: DraftNotice): void {
  const message = DRAFT_MESSAGES[notice];
  // An id per notice, so StrictMode or a quick repeat never stacks two toasts.
  if (notice === "restore_failed") toast.error(message, { id: `draft-${notice}` });
  else if (notice === "memory_only") toast.warning(message, { id: `draft-${notice}` });
  else toast.info(message, { id: `draft-${notice}` });
}

const DraftContext = createContext<DraftApi | null>(null);

export function DraftProvider({
  userId,
  church,
  children,
}: {
  userId: string;
  church: DraftChurch;
  children: ReactNode;
}) {
  const [store] = useState(() => new DraftStore({ userId, church, notify }));
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);

  useEffect(() => {
    store.start();
    const onStorage = (event: StorageEvent) => store.handleStorageEvent(event.key, event.newValue);
    const onVisibility = () => {
      if (document.visibilityState === "hidden") store.flush();
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("pagehide", store.flush);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("pagehide", store.flush);
      document.removeEventListener("visibilitychange", onVisibility);
      store.flush();
    };
  }, [store]);

  const value = useMemo<DraftApi>(
    () => ({
      draft: snapshot.draft,
      persistence: snapshot.persistence,
      update: store.update,
      replace: store.replace,
      setLastStep: store.setLastStep,
    }),
    [snapshot, store],
  );
  return <DraftContext value={value}>{children}</DraftContext>;
}

/** The draft for the active church. Throws outside `DraftProvider` (a builder component rendered in the wrong place). */
export function useDraft(): DraftApi {
  const api = useContext(DraftContext);
  if (!api) throw new Error("useDraft() must be used inside <DraftProvider>.");
  return api;
}
```

Create `frontend/src/lib/draft/prune.ts`:

```ts
/**
 * Draft cleanup (F §4.6 "When the draft is cleared or replaced", items 3 and
 * 4; S "prune.ts"). The `(signed-in)` layout calls it once `/me` has loaded:
 * for this user it removes drafts not updated for 30 days and drafts for
 * churches the user no longer belongs to, with their corrupt-draft backups.
 * Another user's keys on a shared device are never touched.
 */
import { localKeys, readLocal, removeLocal } from "@/lib/storage";

export const PRUNE_AFTER_MS = 30 * 24 * 60 * 60 * 1000;

function updatedAt(raw: string | null): number {
  if (raw === null) return Number.NaN;
  try {
    const value = (JSON.parse(raw) as { updated_at?: unknown }).updated_at;
    return typeof value === "string" ? Date.parse(value) : Number.NaN;
  } catch {
    return Number.NaN;
  }
}

/** Returns the keys it removed (for tests and logs). */
export function pruneDrafts(userId: string, churchIds: readonly string[], now: Date = new Date()): string[] {
  const draftPrefix = `wsb:draft:${userId}:`;
  const corruptPrefix = `wsb:draft-corrupt:${userId}:`;
  const members = new Set(churchIds);
  const removed: string[] = [];
  for (const key of localKeys()) {
    if (key.startsWith(draftPrefix)) {
      const churchId = key.slice(draftPrefix.length);
      const age = now.getTime() - updatedAt(readLocal(key));
      // A draft we cannot date is kept: the store backs it up and starts fresh when it is opened.
      if (!members.has(churchId) || age > PRUNE_AFTER_MS) {
        removeLocal(key);
        removeLocal(`${corruptPrefix}${churchId}`);
        removed.push(key);
      }
    } else if (key.startsWith(corruptPrefix) && !members.has(key.slice(corruptPrefix.length))) {
      removeLocal(key);
      removed.push(key);
    }
  }
  return removed;
}
```

- [ ] **Step 5 (agent): Prune from the `(signed-in)` layout**

In `frontend/src/app/(signed-in)/layout.tsx`, make three edits.

First, in the header comment, after the line that starts ` * - Pages below it read`, add:

```tsx
 * - Once `/me` has loaded (and after every refetch), it prunes this user's
 *   unsaved drafts: older than 30 days, or for churches they no longer belong
 *   to (F §4.6 items 3 and 4; slice 2b).
```

Second, add `import { pruneDrafts } from "@/lib/draft/prune";` above `import { MeProvider } from "@/lib/me-context";`.

Third, insert this just before the effect that begins `useEffect(() => {` followed by `const target = peekPostLoginPath();`, with one blank line after it:

```tsx
  const loaded = me.data;
  useEffect(() => {
    if (loaded) pruneDrafts(loaded.user.id, loaded.churches.map((church) => church.id));
  }, [loaded]);
```

- [ ] **Step 6 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft/context.test.tsx src/lib/draft/prune.test.ts 'src/app/(signed-in)/signed-in-layout.test.tsx' 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
(cd frontend && npm test 2>&1 | grep -E "Warning|not wrapped in act" | head -3)
```

**Expected:** `Test Files  3 passed (3)`, `Tests  15 passed (15)`; `Test Files  46 passed (46)`, `Tests  288 passed (288)`; `> tsc --noEmit`, `> eslint`, nothing after; no `act(` warning.

- [ ] **Step 7 (agent): Commit and back up**

```bash
git add frontend/src/lib/draft/context.tsx frontend/src/lib/draft/context.test.tsx frontend/src/lib/draft/prune.ts frontend/src/lib/draft/prune.test.ts 'frontend/src/app/(signed-in)/layout.tsx' 'frontend/src/app/(signed-in)/signed-in-layout.test.tsx'
git commit -m "Draft: provider, toasts, and pruning after /me (F §4.6; S context.tsx, prune.ts; AC10)" -m "DraftProvider and useDraft give the builder the draft API of S (draft,
update, replace, setLastStep, persistence). The provider writes at once
when the page is hidden or left and on unmount, adopts another tab's newer
draft (\"Updated from another tab.\"), and shows the restore and
memory-only toasts. The (signed-in) layout prunes the user's drafts older
than 30 days and for churches they left whenever /me loads. Frontend
280 -> 288.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T7):** the listeners are removed on unmount and the store flushes then; `start()` is idempotent under StrictMode; `pruneDrafts` never touches another user's keys or `activeChurchId`; the layout effect depends only on `me.data`.

### Task 8: The `sheet` and `badge` components, and the keyboard-open hook (F §4.8 "Mobile", §4.9 items 1, 6; S "Frontend changes" Base UI list, "Builder shell" `useKeyboardOpen()`; clarifications 3, 22; owner question A)

The summary's bottom sheet needs Base UI's `sheet`, and its bulletin chips need `badge` (S lists both among the components to generate; `radio-group`, `collapsible` and `tooltip` are 2c's). `useKeyboardOpen()` is the focus-based hook the step footer uses to hide below `md` while the iOS keyboard is up; slice 4 reuses it.

**Files:**
- Create: `frontend/src/components/ui/sheet.tsx`, `frontend/src/components/ui/badge.tsx` (generated, or clarification 3's hand-written files)
- Create: `frontend/src/lib/use-keyboard-open.ts`
- Test: `frontend/src/lib/use-keyboard-open.test.tsx` (new, 1 test). The sheet and badge are exercised by T9's shell tests.

**Interfaces:**
- Consumes: `@base-ui/react/dialog`, `@base-ui/react/use-render`, `@base-ui/react/merge-props` (installed), `buttonVariants`/`Button` (`components/ui/button.tsx`), `cn` from `"cn"` (as the other generated files import it).
- Produces:
  - `components/ui/sheet.tsx`: `Sheet`, `SheetTrigger`, `SheetClose`, `SheetContent` (`side?: "top" | "right" | "bottom" | "left"`, `showCloseButton?: boolean`, a "Close" button), `SheetHeader`, `SheetFooter`, `SheetTitle`, `SheetDescription`. Later users: T9 (`SummarySheet`).
  - `components/ui/badge.tsx`: `Badge` (`variant?: "default" | "secondary" | "destructive" | "outline" | "ghost" | "link"`), `badgeVariants`. Later users: T9 (`SummaryPanel` chips), 2c (testament badges).
  - `lib/use-keyboard-open.ts`: `isTextEntry(element): boolean`, `useKeyboardOpen(): boolean` (false on the server). Later users: T9 (`StepFooter`), slice 4.

Counts after this task: frontend **289 passed in 47 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/components/ui/
test ! -e frontend/src/lib/use-keyboard-open.ts && echo "no T8 files yet"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `alert-dialog.tsx alert.tsx avatar.tsx button.test.tsx button.tsx card.tsx combobox.tsx dropdown-menu.tsx input-group.tsx input.tsx label.tsx select.tsx skeleton.tsx sonner.tsx tabs.tsx textarea.tsx` (no `sheet.tsx`, no `badge.tsx`); `no T8 files yet`; `Test Files  46 passed (46)`, `Tests  288 passed (288)`.

- [ ] **Step 2 (agent): Try to generate `sheet` and `badge` (network)**

```bash
(cd frontend && timeout 120 npx shadcn@latest add sheet badge < /dev/null 2>&1 | tail -8)
git status --short
```

`< /dev/null` means no prompt can wait for input. Never pass `--overwrite` (F §4.9 item 1); an existing `button.tsx` is skipped or answered No.
- **It works** (the CLI lists `src/components/ui/sheet.tsx` and `src/components/ui/badge.tsx` as created, and `git status` shows exactly those two new files, perhaps plus `package.json` changes if it wanted a dependency; revert any change to an existing file with `git checkout -- <file>`): skip Step 3 and note "generated" for the commit.
- **Network failure** (expected: this container cannot reach ui.shadcn.com; while planning it printed `Request to https://ui.shadcn.com/r/styles/base-nova/sheet.json failed, reason: Request was cancelled.` and changed no file): go to Step 3.
- **Anything else** (the registry answers that an item does not exist, or the CLI changes other files): stop and ask the controller.

- [ ] **Step 3 (agent, with owner answer A = yes): Write the hand-written `sheet` and `badge` (clarification 3)**

Only after a network failure in Step 2, and only with the owner's yes to question A (the controller has it from the plan review). If the answer was no, stop here and tell the controller: the owner generates the two files instead.

Create `frontend/src/components/ui/sheet.tsx`:

```tsx
"use client"

// Hand-written thin wrapper over @base-ui/react/dialog, in the shape of the
// base-nova registry's `sheet`: the recorded exception to F §4.9.1 for slice
// 2b (plan clarification 3), used only when `npx shadcn@latest add sheet`
// cannot reach the registry. Replace it with the generated file when the
// registry is reachable; the exports and props below match it.

import * as React from "react"
import { Dialog as SheetPrimitive } from "@base-ui/react/dialog"
import { cn } from "cn"
import { XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"

function Sheet({ ...props }: SheetPrimitive.Root.Props) {
  return <SheetPrimitive.Root data-slot="sheet" {...props} />
}

function SheetTrigger({ ...props }: SheetPrimitive.Trigger.Props) {
  return <SheetPrimitive.Trigger data-slot="sheet-trigger" {...props} />
}

function SheetClose({ ...props }: SheetPrimitive.Close.Props) {
  return <SheetPrimitive.Close data-slot="sheet-close" {...props} />
}

function SheetPortal({ ...props }: SheetPrimitive.Portal.Props) {
  return <SheetPrimitive.Portal data-slot="sheet-portal" {...props} />
}

function SheetOverlay({ className, ...props }: SheetPrimitive.Backdrop.Props) {
  return (
    <SheetPrimitive.Backdrop
      data-slot="sheet-overlay"
      className={cn(
        "fixed inset-0 z-50 bg-black/10 duration-100 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0",
        className
      )}
      {...props}
    />
  )
}

function SheetContent({
  className,
  children,
  side = "right",
  showCloseButton = true,
  ...props
}: SheetPrimitive.Popup.Props & {
  side?: "top" | "right" | "bottom" | "left"
  showCloseButton?: boolean
}) {
  return (
    <SheetPortal>
      <SheetOverlay />
      <SheetPrimitive.Popup
        data-slot="sheet-content"
        data-side={side}
        className={cn(
          "fixed z-50 flex flex-col gap-4 bg-popover text-popover-foreground shadow-lg outline-none duration-200 data-open:animate-in data-closed:animate-out",
          "data-[side=bottom]:inset-x-0 data-[side=bottom]:bottom-0 data-[side=bottom]:max-h-[85dvh] data-[side=bottom]:rounded-t-xl data-[side=bottom]:border-t data-[side=bottom]:data-open:slide-in-from-bottom data-[side=bottom]:data-closed:slide-out-to-bottom",
          "data-[side=top]:inset-x-0 data-[side=top]:top-0 data-[side=top]:border-b data-[side=top]:data-open:slide-in-from-top data-[side=top]:data-closed:slide-out-to-top",
          "data-[side=left]:inset-y-0 data-[side=left]:left-0 data-[side=left]:h-full data-[side=left]:w-3/4 data-[side=left]:border-r data-[side=left]:sm:max-w-sm data-[side=left]:data-open:slide-in-from-left data-[side=left]:data-closed:slide-out-to-left",
          "data-[side=right]:inset-y-0 data-[side=right]:right-0 data-[side=right]:h-full data-[side=right]:w-3/4 data-[side=right]:border-l data-[side=right]:sm:max-w-sm data-[side=right]:data-open:slide-in-from-right data-[side=right]:data-closed:slide-out-to-right",
          className
        )}
        {...props}
      >
        {children}
        {showCloseButton && (
          <SheetPrimitive.Close
            data-slot="sheet-close"
            render={<Button variant="ghost" size="icon-sm" className="absolute top-3 right-3" />}
          >
            <XIcon />
            <span className="sr-only">Close</span>
          </SheetPrimitive.Close>
        )}
      </SheetPrimitive.Popup>
    </SheetPortal>
  )
}

function SheetHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-header"
      className={cn("flex flex-col gap-1 p-4", className)}
      {...props}
    />
  )
}

function SheetFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-footer"
      className={cn("mt-auto flex flex-col gap-2 p-4", className)}
      {...props}
    />
  )
}

function SheetTitle({ className, ...props }: SheetPrimitive.Title.Props) {
  return (
    <SheetPrimitive.Title
      data-slot="sheet-title"
      className={cn("font-heading text-base font-medium text-foreground", className)}
      {...props}
    />
  )
}

function SheetDescription({ className, ...props }: SheetPrimitive.Description.Props) {
  return (
    <SheetPrimitive.Description
      data-slot="sheet-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetFooter,
  SheetTitle,
  SheetDescription,
}
```

Create `frontend/src/components/ui/badge.tsx`:

```tsx
// Hand-written in the shape of the base-nova registry's `badge`: the recorded
// exception to F §4.9.1 for slice 2b (plan clarification 3), used only when
// `npx shadcn@latest add badge` cannot reach the registry. Replace it with the
// generated file when the registry is reachable.

import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "cn"

const badgeVariants = cva(
  "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground",
        secondary: "bg-secondary text-secondary-foreground",
        destructive: "bg-destructive/10 text-destructive dark:bg-destructive/20",
        outline: "border-border text-foreground",
        ghost: "hover:bg-muted hover:text-muted-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ className, variant })),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
```

- [ ] **Step 4 (agent): Write the failing hook test**

Create `frontend/src/lib/use-keyboard-open.test.tsx`:

```tsx
import { act, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useKeyboardOpen } from "./use-keyboard-open";

function Probe() {
  const open = useKeyboardOpen();
  return (
    <div>
      <p>Keyboard: {open ? "open" : "closed"}</p>
      <label>
        Occasion <input type="text" />
      </label>
      <label>
        Readings <textarea />
      </label>
      <label>
        Service date <input type="date" />
      </label>
      <button type="button">Next</button>
    </div>
  );
}

describe("useKeyboardOpen (S Builder shell)", () => {
  it("is open while a text input or textarea has focus, and closed for buttons, pickers and no focus", () => {
    render(<Probe />);
    const state = () => screen.getByText(/^Keyboard:/).textContent;
    expect(state()).toBe("Keyboard: closed");

    act(() => screen.getByRole("textbox", { name: "Occasion" }).focus());
    expect(state()).toBe("Keyboard: open");
    act(() => screen.getByRole("textbox", { name: "Readings" }).focus());
    expect(state()).toBe("Keyboard: open");
    act(() => screen.getByLabelText("Service date").focus());
    expect(state()).toBe("Keyboard: closed");
    act(() => screen.getByRole("textbox", { name: "Occasion" }).focus());
    act(() => screen.getByRole("button", { name: "Next" }).focus());
    expect(state()).toBe("Keyboard: closed");
    act(() => screen.getByRole("textbox", { name: "Readings" }).focus());
    act(() => (document.activeElement as HTMLElement).blur());
    expect(state()).toBe("Keyboard: closed");
  });
});
```

- [ ] **Step 5 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/lib/use-keyboard-open.test.tsx 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** ` FAIL  |dom| src/lib/use-keyboard-open.test.tsx`, `Error: Failed to resolve import "./use-keyboard-open" from "src/lib/use-keyboard-open.test.tsx". Does the file exist?`, `Tests  no tests`.

- [ ] **Step 6 (agent): Write the hook**

Create `frontend/src/lib/use-keyboard-open.ts`:

```ts
"use client";

/**
 * True while a text input, a textarea or an editable element has focus (S
 * "Builder shell": below `md` the step footer hides then, so the iOS keyboard
 * does not stack on it). Focus-based, because the visual viewport is not
 * reliable across mobile browsers. Slice 4 reuses it for the liturgy cards.
 */
import { useSyncExternalStore } from "react";

/** Input types that open a picker or no keyboard at all. */
const NO_KEYBOARD = new Set([
  "button", "checkbox", "color", "date", "datetime-local", "file", "hidden", "image",
  "month", "radio", "range", "reset", "submit", "time", "week",
]);

export function isTextEntry(element: Element | null): boolean {
  if (element instanceof HTMLTextAreaElement) return !element.readOnly;
  if (element instanceof HTMLInputElement) return !element.readOnly && !NO_KEYBOARD.has(element.type);
  return element instanceof HTMLElement && element.isContentEditable;
}

function subscribe(onChange: () => void): () => void {
  document.addEventListener("focusin", onChange);
  document.addEventListener("focusout", onChange);
  return () => {
    document.removeEventListener("focusin", onChange);
    document.removeEventListener("focusout", onChange);
  };
}

export function useKeyboardOpen(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => isTextEntry(document.activeElement),
    () => false,
  );
}
```

- [ ] **Step 7 (agent): Run the test, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/use-keyboard-open.test.tsx 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** `Tests  1 passed (1)`; `Test Files  47 passed (47)`, `Tests  289 passed (289)`; `> tsc --noEmit`, `> eslint`, nothing after (a generated `sheet.tsx` or `badge.tsx` that trips lint or types is a registry problem: report it to the controller rather than editing it beyond F §4.9 item 1).

- [ ] **Step 8 (agent): Commit and back up**

Replace `<how>` with `generated with npx shadcn@latest add sheet badge` or `hand-written (the registry was blocked; plan clarification 3, owner answer A)`:

```bash
git add frontend/src/components/ui/sheet.tsx frontend/src/components/ui/badge.tsx frontend/src/lib/use-keyboard-open.ts frontend/src/lib/use-keyboard-open.test.tsx
git commit -m "UI: sheet and badge, and the keyboard-open hook for the step footer (F §4.8, §4.9; S Builder shell)" -m "Sheet and badge: <how>. useKeyboardOpen is true while a text input,
textarea or editable element has focus (pickers, buttons and read-only
fields do not count), so the builder's footer can step aside for the
phone keyboard. Frontend 288 -> 289.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T8):** the commit body says how the two components were made; if hand-written, each file starts with the clarification 3 comment and imports only installed Base UI parts; the hook uses `useSyncExternalStore` (no state set inside an effect) and returns false on the server.

### Task 9: The builder shell and all four step routes (F §4.7, §4.8, acceptance 11; S "Builder shell", "Steps 2–4 (placeholders)", "SummaryPanel", "New service", "Other states and messages" first row, Testing `builder-shell.test.tsx`; AC11, AC17; owner answers Q1, Q2; clarifications 2, 10–16, 24, 25, 27, 30, 31)

This is the page members will see. `BuilderShell` (the builder layout) loads the draft for the signed-in user and the active church, writes `last_step` on every step route without touching `updated_at`, and lays out `StepHeader` ("Service Builder", "Summary" below `lg`, the "More actions" menu with "New service"), `StepProgress`, the step, the sticky `StepFooter`, and `SummaryPanel` (a sticky right column from `lg`, the `SummarySheet` below it). `/builder` redirects to `last_step`. The four step pages show `StepPlaceholder` (Date & readings too, owner answer Q1); Review adds `StillNeeded`, which stays empty until a step ships. The readings status, "Still needed" rows, occasion line and OT/NT chips are built now behind `SHIPPED_STEPS` and tested with `shipped` passed in, so 2c only switches them on.

**Files:**
- Modify: `frontend/src/lib/queries/church.ts` (`useChurchProfile` typed `ChurchProfile`, clarification 24)
- Create (`frontend/src/components/builder/`): `step-placeholder.tsx`, `still-needed.tsx`, `step-progress.tsx`, `step-footer.tsx`, `summary-panel.tsx`, `summary-sheet.tsx`, `new-service-menu-item.tsx`, `step-header.tsx`, `builder-shell.tsx`
- Create (`frontend/src/app/(signed-in)/(church)/builder/`): `layout.tsx`, `page.tsx`, `readings/page.tsx`, `hymns/page.tsx`, `liturgy/page.tsx`, `review/page.tsx`
- Test: `frontend/src/components/builder/builder-shell.test.tsx` (new, 8 tests)

**Interfaces:**
- Consumes: T1 `formatLongDate`; T2 `splitAlternatives`; T3 `freshDraft`, `DraftChurch`, `draftKey`, the fixtures; T4 `cleanScriptures`, `effectivePicks`, the transitions (tests), `lectionary`; T5 `STEPS`, `SHIPPED_STEPS`, `stepById`, `stepFromPath`, `stepStatus`, `StepStatus`, `stillNeeded`, `isDirty`; T7 `DraftProvider`, `useDraft`; T8 `Sheet*`, `Badge`, `useKeyboardOpen`; the kit (`EmptyState`, `ConfirmDialog`, `buttonVariants`, `DropdownMenu*`, `Skeleton`); `useMeContext`, `useChurch`, `useChurchProfile`.
- Produces:
  - `BuilderShell({ children })`, `BuilderSkeleton()` (`builder-shell.tsx`).
  - `StepHeader({ onOpenSummary, onNewService })`; `StepProgress({ current, shipped? })` and `statusText(status)`; `StepFooter({ current })`; `SummaryPanel({ shipped?, onNavigate? })`; `SummarySheet({ open, onOpenChange })`; `StepPlaceholder({ step })`; `StillNeeded({ shipped? })`; `useNewService(church) → { start, dialog }` and `NewServiceMenuItem({ onSelect })`.
  - Routes: `/builder` (redirects to `last_step`), `/builder/readings`, `/builder/hymns`, `/builder/liturgy`, `/builder/review`.
  - Later users: T10 (the church-switch test renders `BuilderLayout`); 2c (replaces `builder/readings/page.tsx`, adds "readings" to `SHIPPED_STEPS`, mounts `useLectionarySync()` in `BuilderFrame`); 3 and 4 (replace their pages and summary blocks); 5a (replaces the review page, wires the status line's archive half, deletes `StepPlaceholder`).

Counts after this task: frontend **297 passed in 48 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/builder && test ! -e 'frontend/src/app/(signed-in)/(church)/builder' && echo "no T9 files yet"
grep -n "UseQueryResult<" frontend/src/lib/queries/church.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T9 files yet`; `18:): UseQueryResult<Church, ApiError> {`; `Test Files  47 passed (47)`, `Tests  289 passed (289)`.

- [ ] **Step 2 (agent): Write the failing test**

Create `frontend/src/components/builder/builder-shell.test.tsx`. It covers S Testing's row: the four routes inside the shell; the progress statuses and "Soon"; the summary's blocks saying "Available soon"; the footer links; the Summary sheet; New service confirming only when there is something to lose; `/builder/hymns` then `/builder` redirecting to `/builder/hymns` with `updated_at` unchanged; the first-render skeleton; and, with "readings" passed as shipped, the readings status, "Still needed" rows, occasion line and chips. (`AppNav` is T10's.)

```tsx
/**
 * The builder shell (F §4.7, F acceptance 11; S "Builder shell", Testing
 * `builder-shell.test.tsx`; AC17). Every test fixes the clock at Tuesday,
 * September 29, 2026 (only `Date` is faked, so user-event's timers run), so a
 * fresh draft is dated Sunday, October 4, 2026.
 */
import { screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BuilderIndexPage from "@/app/(signed-in)/(church)/builder/page";
import HymnsStepPage from "@/app/(signed-in)/(church)/builder/hymns/page";
import LiturgyStepPage from "@/app/(signed-in)/(church)/builder/liturgy/page";
import ReadingsStepPage from "@/app/(signed-in)/(church)/builder/readings/page";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, editOccasion, setPick } from "@/lib/draft/readings";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, lectionary, me, testDraft, USER_ID } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { StepProgress } from "./step-progress";
import { StillNeeded } from "./still-needed";
import { SummaryPanel } from "./summary-panel";

const KEY = draftKey(USER_ID, church().id);
const READINGS_SHIPPED = new Set(["readings"] as const);

function seed(draft: DraftV1): DraftV1 {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  return draft;
}

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

/** Shows what the shell's draft holds, as a step page would. */
function DraftProbe() {
  const { draft } = useDraft();
  return (
    <p>
      Probe: {draft.readings.occasion || "no occasion"} / {draft.save_key}
    </p>
  );
}

function renderBuilder(page: ReactElement, path: string) {
  installFakeApi({ "GET /church": churchProfile() });
  return renderWithProviders(<BuilderLayout>{page}</BuilderLayout>, { me: me(), church: church(), path });
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("builder shell (F §4.7)", () => {
  it("renders each step route inside the shell: progress, the placeholder card and the footer links", async () => {
    const cases: [string, ReactElement, number, string, string[]][] = [
      ["/builder/readings", <ReadingsStepPage key="r" />, 1, "Date & readings", ["Next: Hymns"]],
      ["/builder/hymns", <HymnsStepPage key="h" />, 2, "Hymns", ["Back", "Next: Liturgy"]],
      ["/builder/liturgy", <LiturgyStepPage key="l" />, 3, "Liturgy", ["Back", "Next: Review"]],
      ["/builder/review", <ReviewStepPage key="v" />, 4, "Review & send", ["Back"]],
    ];
    for (const [path, page, number, label, footer] of cases) {
      const { unmount } = renderBuilder(page, path);
      expect(await screen.findByRole("heading", { level: 1, name: "Service Builder" })).toBeInTheDocument();
      expect(screen.getByText(`Step ${number} of 4 · ${label}`)).toBeInTheDocument();

      const steps = within(screen.getByRole("navigation", { name: "Steps" })).getAllByRole("link");
      expect(steps.map((link) => link.textContent)).toEqual([
        "1 Date & readings Soon",
        "2 Hymns Soon",
        "3 Liturgy Soon",
        "4 Review & send Not in archive",
      ]);
      expect(steps.map((link) => link.getAttribute("href"))).toEqual([
        "/builder/readings",
        "/builder/hymns",
        "/builder/liturgy",
        "/builder/review",
      ]);
      expect(steps.filter((link) => link.getAttribute("aria-current") === "step")).toEqual([steps[number - 1]]);

      const card = screen.getByRole("region", { name: label });
      expect(within(card).getByRole("heading", { name: "Available soon" })).toBeInTheDocument();
      expect(within(card).getByText("Keep using the current app for this part.")).toBeInTheDocument();
      expect(within(card).queryByRole("link")).toBeNull(); // no link to the old app (owner answer Q2)

      const links = within(screen.getByRole("navigation", { name: "Step navigation" })).getAllByRole("link");
      expect(links.map((link) => link.textContent)).toEqual(footer);
      expect(screen.queryByRole("heading", { name: "Still needed" })).toBeNull(); // nothing shipped yet
      unmount();
    }
  });

  it("shows the summary: the date, Available soon for the rest, and where the draft is kept", async () => {
    const { user } = renderBuilder(<HymnsStepPage />, "/builder/hymns");
    const aside = await screen.findByRole("complementary", { name: "Summary" });
    expect(within(aside).getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    for (const block of ["Readings", "Hymns", "Liturgy"]) {
      const heading = within(aside).getByRole("link", { name: block }).closest("h3");
      expect(heading?.nextElementSibling).toHaveTextContent(/^Available soon$/);
    }
    expect(within(aside).getByRole("link", { name: "Date" })).toHaveAttribute("href", "/builder/readings");
    expect(within(aside).getByText("Draft saved on this device · Not in archive")).toBeInTheDocument();
    expect(within(aside).queryByText("No occasion yet")).toBeNull();

    // Below lg the same panel opens in a bottom sheet from "Summary".
    await user.click(screen.getByRole("button", { name: "Summary" }));
    const sheet = await screen.findByRole("dialog", { name: "Summary" });
    expect(within(sheet).getByText("Sunday, October 4, 2026")).toBeInTheDocument();
    expect(within(sheet).getByText("Draft saved on this device · Not in archive")).toBeInTheDocument();
    await user.click(within(sheet).getByRole("button", { name: "Close" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("writes last_step on entry without touching updated_at, and /builder opens that step", async () => {
    const saved = seed(testDraft());
    const first = renderBuilder(<HymnsStepPage />, "/builder/hymns");
    await screen.findByRole("heading", { level: 1, name: "Service Builder" });
    await waitFor(() => expect(stored().last_step).toBe("hymns"));
    expect(stored().updated_at).toBe(saved.updated_at);
    first.unmount();

    renderBuilder(<BuilderIndexPage />, "/builder");
    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/builder/hymns"));
    expect(screen.queryByRole("navigation", { name: "Steps" })).toBeNull();
    expect(stored().updated_at).toBe(saved.updated_at);
  });

  it("New service resets a draft with nothing to lose at once, then opens Date & readings", async () => {
    const saved = seed(testDraft());
    const { user } = renderBuilder(<DraftProbe />, "/builder/liturgy");
    expect(await screen.findByText(`Probe: no occasion / ${saved.save_key}`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    expect(screen.queryByText(`Probe: no occasion / ${saved.save_key}`)).toBeNull();
    expect(screen.getByText(/^Probe: no occasion \//)).toBeInTheDocument();
  });

  it("New service asks first when the draft has something to lose; Cancel keeps it, confirming clears it", async () => {
    const saved = seed(editOccasion(testDraft(), "Harvest Sunday"));
    const { user } = renderBuilder(<DraftProbe />, "/builder/review");
    expect(await screen.findByText(`Probe: Harvest Sunday / ${saved.save_key}`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    let dialog = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    expect(within(dialog).getByText("This clears the current draft on this device.")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByText(`Probe: Harvest Sunday / ${saved.save_key}`)).toBeInTheDocument();
    expect(testRouter.push).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    dialog = await screen.findByRole("alertdialog", { name: "Start a new service?" });
    await user.click(within(dialog).getByRole("button", { name: "Start new service" }));
    expect(await screen.findByText(/^Probe: no occasion \//)).toBeInTheDocument();
    expect(testRouter.push).toHaveBeenCalledWith("/builder/readings");
    await waitFor(() => expect(stored().save_key).not.toBe(saved.save_key));
    expect(stored().readings.occasion).toBe("");
  });

  it("shows the builder skeleton until the church profile loads", async () => {
    installFakeApi({ "GET /church": async () => churchProfile() });
    renderWithProviders(
      <BuilderLayout>
        <ReadingsStepPage />
      </BuilderLayout>,
      { me: me(), church: church(), path: "/builder/readings" },
    );
    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Service Builder" })).toBeInTheDocument();
  });
});

describe("the shell once Date & readings ships (slice 2c turns this on)", () => {
  it("shows the readings status, Still needed rows, the occasion and the bulletin chips", async () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    seed(setPick(filled, "nt", "Matthew 21:33-46"));
    installFakeApi({ "GET /church": churchProfile() });
    renderWithProviders(
      <BuilderLayout>
        <StepProgress current="readings" shipped={READINGS_SHIPPED} />
        <StillNeeded shipped={READINGS_SHIPPED} />
        <section aria-label="Shipped summary">
          <SummaryPanel shipped={READINGS_SHIPPED} />
        </section>
      </BuilderLayout>,
      { me: me(), church: church(), path: "/builder/readings" },
    );

    const progress = (await screen.findAllByRole("navigation", { name: "Steps" }))[1];
    expect(within(progress).getAllByRole("link")[0]).toHaveTextContent("1 Date & readings Complete");
    expect(screen.queryByRole("heading", { name: "Still needed" })).toBeNull(); // nothing missing

    const summary = screen.getByRole("region", { name: "Shipped summary" });
    expect(within(summary).getByText("Nineteenth Sunday after Pentecost")).toBeInTheDocument();
    const rows = within(summary).getAllByRole("listitem").map((li) => li.textContent);
    expect(rows).toEqual(["Isaiah 5:1-7OT (auto)", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46NT"]);
  });

  it("lists what is missing, each linking to its step", async () => {
    seed(testDraft());
    installFakeApi({ "GET /church": churchProfile() });
    renderWithProviders(
      <BuilderLayout>
        <StillNeeded shipped={READINGS_SHIPPED} />
      </BuilderLayout>,
      { me: me(), church: church(), path: "/builder/review" },
    );
    const section = await screen.findByRole("region", { name: "Still needed" });
    expect(within(section).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "No occasion — Add one",
      "No scripture readings — Add one",
    ]);
    for (const link of within(section).getAllByRole("link")) expect(link).toHaveAttribute("href", "/builder/readings");
  });
});
```

- [ ] **Step 3 (agent): Run it and see it fail**

```bash
(cd frontend && npx vitest run src/components/builder/builder-shell.test.tsx 2>&1 | grep -E "FAIL|Error:|Tests ")
```

**Expected:** ` FAIL  |dom| src/components/builder/builder-shell.test.tsx`, `Error: Failed to resolve import "@/app/(signed-in)/(church)/builder/layout" from "src/components/builder/builder-shell.test.tsx". Does the file exist?`, `Tests  no tests`.

- [ ] **Step 4 (agent): Type the profile query as `ChurchProfile`**

In `frontend/src/lib/queries/church.ts`: change `import type { Church } from "@/lib/api/types";` to `import type { ChurchProfile } from "@/lib/api/types";`; in the doc comment, change "the server confirms\n * the membership." to "the server confirms\n * the membership, and since slice 2a returns the profile (`ChurchProfileOut`:\n * timezone, translation)."; and replace the three `Church` type arguments (`UseQueryResult<Church, ApiError>`, `useQuery<Church, ApiError>`, `api.forChurch(id)<Church>`) with `ChurchProfile`. The `(church)` layout keeps typing `confirmed` as `Church` (a profile is one).

- [ ] **Step 5 (agent): Write the shell components**

Create `frontend/src/components/builder/step-placeholder.tsx`:

```tsx
import { EmptyState } from "@/components/app/empty-state";
import { stepById, type StepId } from "@/lib/draft/steps";

/**
 * The card a step shows until its slice ships (S "Steps 2–4 (placeholders)";
 * F §4.7). Slice 2b also uses it for Date & readings (owner answer Q1,
 * 2026-09-28). Slices 2c, 3, 4 and 5a each replace their step's use, and 5a
 * deletes this component. No link to the old app (owner answer Q2).
 */
export function StepPlaceholder({ step }: { step: StepId }) {
  return (
    <section aria-label={stepById(step).label}>
      <EmptyState title="Available soon" description="Keep using the current app for this part." />
    </section>
  );
}
```

Create `frontend/src/components/builder/still-needed.tsx`:

```tsx
"use client";

import Link from "next/link";

import { useDraft } from "@/lib/draft/context";
import { stillNeeded } from "@/lib/draft/status";
import { SHIPPED_STEPS, stepById, type StepId } from "@/lib/draft/steps";

/**
 * Review's "Still needed" list (S "Steps 2–4"; F §4.7 "Review has no Next"):
 * one row per gap in a shipped step, each linking to that step. Nothing
 * renders while no step has shipped (slice 2b) or nothing is missing.
 */
export function StillNeeded({ shipped = SHIPPED_STEPS }: { shipped?: ReadonlySet<StepId> }) {
  const { draft } = useDraft();
  const items = stillNeeded(draft, shipped);
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="still-needed-heading" className="mt-6 grid gap-2">
      <h2 id="still-needed-heading" className="text-base font-medium">
        Still needed
      </h2>
      <ul className="grid gap-1 text-sm">
        {items.map((item) => (
          <li key={`${item.step}:${item.message}`}>
            {item.message} —{" "}
            <Link href={stepById(item.step).href} className="font-medium underline underline-offset-4">
              {item.action}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
```

Create `frontend/src/components/builder/step-progress.tsx`:

```tsx
"use client";

import { CheckIcon } from "lucide-react";
import Link from "next/link";

import { useDraft } from "@/lib/draft/context";
import { stepStatus, type StepStatus } from "@/lib/draft/status";
import { SHIPPED_STEPS, STEPS, stepById, type StepId } from "@/lib/draft/steps";
import { cn } from "@/lib/utils";

export function statusText(status: StepStatus): string {
  switch (status.kind) {
    case "complete":
      return "Complete";
    case "incomplete":
      return `${status.done} of ${status.total}`;
    case "soon":
      return "Soon";
    case "not_in_archive":
      return "Not in archive";
  }
}

/**
 * The four steps (F §4.7 "StepProgress"; S "Builder shell"): every step is a
 * link (F D9). Below `lg` a line "Step 1 of 4 · Date & readings" sits above
 * four segments; from `lg` each step shows its number, label and status. The
 * labels and statuses are in the DOM at every width (screen-reader text below
 * `lg`), so each link's name is "{n} {label} {status}".
 */
export function StepProgress({ current, shipped = SHIPPED_STEPS }: { current: StepId; shipped?: ReadonlySet<StepId> }) {
  const { draft } = useDraft();
  const step = stepById(current);
  return (
    <nav aria-label="Steps" className="grid gap-2 pb-2">
      <p className="text-sm font-medium lg:hidden" aria-hidden="true">
        Step {step.number} of {STEPS.length} · {step.label}
      </p>
      <ol className="grid grid-cols-4 gap-1.5 lg:gap-3">
        {STEPS.map((s) => {
          const status = stepStatus(draft, s.id, shipped);
          const isCurrent = s.id === current;
          const muted = status.kind === "soon" || status.kind === "not_in_archive";
          return (
            <li key={s.id}>
              <Link
                href={s.href}
                aria-current={isCurrent ? "step" : undefined}
                className="flex min-h-11 flex-col justify-center gap-1 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring lg:min-h-0 lg:py-1"
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "h-1.5 rounded-full bg-muted",
                    status.kind === "complete" && "bg-primary/60",
                    isCurrent && "bg-primary",
                  )}
                />
                <span className="sr-only lg:not-sr-only lg:text-sm lg:font-medium">
                  {s.number} {s.label}
                </span>{" "}
                <span
                  className={cn(
                    "sr-only lg:not-sr-only lg:flex lg:items-center lg:gap-1 lg:text-xs",
                    muted ? "lg:text-muted-foreground" : "lg:text-foreground",
                  )}
                >
                  {status.kind === "complete" ? <CheckIcon aria-hidden="true" className="size-3" /> : null}
                  {statusText(status)}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
```

Create `frontend/src/components/builder/step-footer.tsx`:

```tsx
"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { stepById, type StepId } from "@/lib/draft/steps";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

/**
 * Back and Next (S "Footer labels"; F §4.7): Date & readings has only "Next:
 * Hymns", Review only "Back". Below `lg` it is sticky at the bottom above the
 * home indicator; below `md` it hides while a text field has focus, so the
 * iOS keyboard does not stack on it.
 */
export function StepFooter({ current }: { current: StepId }) {
  const keyboardOpen = useKeyboardOpen();
  const step = stepById(current);
  const previous = step.previous ? stepById(step.previous) : null;
  const next = step.next ? stepById(step.next) : null;
  return (
    <nav
      aria-label="Step navigation"
      data-keyboard-open={keyboardOpen ? "" : undefined}
      className={cn(
        "sticky bottom-0 z-10 -mx-4 border-t bg-background/95 px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
        "lg:static lg:mx-0 lg:border-t-0 lg:bg-transparent lg:px-0 lg:pb-6 lg:backdrop-blur-none",
        keyboardOpen && "max-md:hidden",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        {previous ? (
          <Link href={previous.href} className={buttonVariants({ variant: "outline", size: "touch" })}>
            Back
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link href={next.href} className={buttonVariants({ size: "touch" })}>
            Next: {next.short}
          </Link>
        ) : null}
      </div>
    </nav>
  );
}
```

Create `frontend/src/components/builder/summary-panel.tsx`:

```tsx
"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { formatLongDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectivePicks } from "@/lib/draft/readings";
import { SHIPPED_STEPS, stepById, type StepId } from "@/lib/draft/steps";
import { splitAlternatives } from "@/lib/scripture-refs";

/** A pick matches a line when it is the line or one of its " or " alternatives. */
function holds(line: string, pick: string | null): boolean {
  return pick !== null && (line === pick || splitAlternatives(line).includes(pick));
}

function Block({ title, step, onNavigate, children }: { title: string; step: StepId; onNavigate?: () => void; children: ReactNode }) {
  return (
    <div className="grid gap-1">
      <h3 className="text-sm font-medium">
        <Link href={stepById(step).href} onClick={onNavigate} className="underline-offset-4 hover:underline">
          {title}
        </Link>
      </h3>
      <div className="text-sm text-muted-foreground">{children}</div>
    </div>
  );
}

function Soon() {
  return <p>Available soon</p>;
}

/**
 * The draft at a glance (S "SummaryPanel"; F §4.7): a sticky column from
 * `lg`, the bottom sheet below it. Each block links to its step. The Readings
 * block and the occasion line show once "readings" ships (slice 2c); slices 3
 * and 4 replace the Hymns and Liturgy blocks, and 5a wires the archive half
 * of the status line.
 */
export function SummaryPanel({ shipped = SHIPPED_STEPS, onNavigate }: { shipped?: ReadonlySet<StepId>; onNavigate?: () => void }) {
  const { draft, persistence } = useDraft();
  const readingsShipped = shipped.has("readings");
  const lines = cleanScriptures(draft);
  const picks = effectivePicks(draft);
  const saved = persistence === "ok" ? "Draft saved on this device" : "Draft not saved on this device";

  return (
    <div className="grid gap-4">
      <Block title="Date" step="readings" onNavigate={onNavigate}>
        <p className="text-foreground">{formatLongDate(draft.readings.date_iso) || "No service date"}</p>
        {readingsShipped ? <p>{draft.readings.occasion.trim() || "No occasion yet"}</p> : null}
      </Block>
      <Block title="Readings" step="readings" onNavigate={onNavigate}>
        {!readingsShipped ? (
          <Soon />
        ) : lines.length === 0 ? (
          <p>No readings yet</p>
        ) : (
          <ul className="grid gap-1">
            {lines.map((line, i) => (
              <li key={`${i}:${line}`} className="flex flex-wrap items-center gap-1.5 break-words text-foreground">
                <span className="min-w-0 break-words">{line}</span>
                {holds(line, picks.ot) ? <Badge variant="secondary">{picks.otAuto ? "OT (auto)" : "OT"}</Badge> : null}
                {holds(line, picks.nt) ? <Badge variant="secondary">{picks.ntAuto ? "NT (auto)" : "NT"}</Badge> : null}
              </li>
            ))}
          </ul>
        )}
      </Block>
      <Block title="Hymns" step="hymns" onNavigate={onNavigate}>
        <Soon />
      </Block>
      <Block title="Liturgy" step="liturgy" onNavigate={onNavigate}>
        <Soon />
      </Block>
      <p className="border-t pt-3 text-xs text-muted-foreground">{saved} · Not in archive</p>
    </div>
  );
}
```

Create `frontend/src/components/builder/summary-sheet.tsx`:

```tsx
"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import { SummaryPanel } from "./summary-panel";

/** The summary below `lg`, opened from the "Summary" button (S "Builder shell"; F §4.7, §4.9 item 6). */
export function SummarySheet({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Sheet open={open} onOpenChange={(next) => onOpenChange(next)}>
      <SheetContent side="bottom" className="lg:hidden">
        <SheetHeader>
          <SheetTitle>Summary</SheetTitle>
        </SheetHeader>
        <div className="overflow-y-auto px-4 pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <SummaryPanel onNavigate={() => onOpenChange(false)} />
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

Create `frontend/src/components/builder/new-service-menu-item.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { useDraft } from "@/lib/draft/context";
import { isDirty } from "@/lib/draft/fingerprint";
import { freshDraft, type DraftChurch } from "@/lib/draft/schema";
import { useMeContext } from "@/lib/me-context";

/**
 * "New service" (S "New service"; F §4.6 item 1): a draft with nothing to
 * lose resets at once; otherwise "Start a new service?" asks first. Either
 * way the builder then opens Date & readings.
 */
export function useNewService(church: DraftChurch): { start: () => void; dialog: ReactNode } {
  const { draft, replace } = useDraft();
  const me = useMeContext();
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);

  function reset() {
    replace(freshDraft({ church, user: me.user }));
    setConfirming(false);
    router.push("/builder/readings");
  }

  return {
    start: () => (isDirty(draft) ? setConfirming(true) : reset()),
    dialog: (
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Start a new service?"
        description="This clears the current draft on this device."
        confirmLabel="Start new service"
        onConfirm={reset}
        destructive
      />
    ),
  };
}

export function NewServiceMenuItem({ onSelect }: { onSelect: () => void }) {
  return <DropdownMenuItem onClick={() => onSelect()}>New service</DropdownMenuItem>;
}
```

Create `frontend/src/components/builder/step-header.tsx`:

```tsx
"use client";

import { EllipsisVerticalIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

import { NewServiceMenuItem } from "./new-service-menu-item";

/** "Service Builder", the "Summary" button (below `lg`) and the overflow menu (S "Builder shell"). */
export function StepHeader({ onOpenSummary, onNewService }: { onOpenSummary: () => void; onNewService: () => void }) {
  return (
    <div className="flex items-center gap-2 pt-4 pb-2">
      <h1 className="min-w-0 flex-1 text-xl font-semibold tracking-tight">Service Builder</h1>
      <button
        type="button"
        onClick={() => onOpenSummary()}
        className={cn(buttonVariants({ variant: "outline", size: "touch" }), "lg:hidden")}
      >
        Summary
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="More actions"
          className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "size-11")}
        >
          <EllipsisVerticalIcon aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-auto min-w-44">
          <NewServiceMenuItem onSelect={onNewService} />
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
```

Create `frontend/src/components/builder/builder-shell.tsx`:

```tsx
"use client";

/**
 * The builder around every step route (F §4.7; S "Builder shell"). It loads
 * the draft for the signed-in user and the active church, writes `last_step`
 * on every step route, and lays out: header, progress, the step, the footer,
 * and the summary (a sticky column from `lg`, a bottom sheet below it).
 * The church profile is already loaded by the `(church)` layout; until the
 * query has data (tests, a cold cache) a step-shaped skeleton shows.
 */
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import type { DraftChurch } from "@/lib/draft/schema";
import { stepFromPath } from "@/lib/draft/steps";
import { useMeContext } from "@/lib/me-context";
import { useChurchProfile } from "@/lib/queries/church";

import { useNewService } from "./new-service-menu-item";
import { StepFooter } from "./step-footer";
import { StepHeader } from "./step-header";
import { StepProgress } from "./step-progress";
import { SummaryPanel } from "./summary-panel";
import { SummarySheet } from "./summary-sheet";

export function BuilderShell({ children }: { children: ReactNode }) {
  const me = useMeContext();
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  if (!profile.data) return <BuilderSkeleton />;
  return (
    <DraftProvider key={`${me.user.id}:${church.id}`} userId={me.user.id} church={profile.data}>
      <BuilderFrame church={profile.data}>{children}</BuilderFrame>
    </DraftProvider>
  );
}

function BuilderFrame({ church, children }: { church: DraftChurch; children: ReactNode }) {
  const current = stepFromPath(usePathname());
  const { setLastStep } = useDraft();
  const [summaryOpen, setSummaryOpen] = useState(false);
  const newService = useNewService(church);

  useEffect(() => {
    if (current) setLastStep(current);
  }, [current, setLastStep]);

  return (
    <div className="mx-auto w-full max-w-2xl px-4 lg:grid lg:max-w-6xl lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-6">
      <div className="flex min-h-[calc(100dvh-3.5rem)] min-w-0 flex-col">
        <StepHeader onOpenSummary={() => setSummaryOpen(true)} onNewService={newService.start} />
        {current ? <StepProgress current={current} /> : null}
        <main className="flex-1 py-4">{children}</main>
        {current ? <StepFooter current={current} /> : null}
      </div>
      <aside aria-label="Summary" className="hidden lg:block">
        <div className="sticky top-20 py-4">
          <SummaryPanel />
        </div>
      </aside>
      <SummarySheet open={summaryOpen} onOpenChange={setSummaryOpen} />
      {newService.dialog}
    </div>
  );
}

/** The builder's shape while the church profile loads (S "Builder first render"). */
export function BuilderSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="mx-auto grid w-full max-w-2xl gap-4 px-4 py-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}
```

- [ ] **Step 6 (agent): Write the builder routes**

Create `frontend/src/app/(signed-in)/(church)/builder/layout.tsx`:

```tsx
"use client";

import type { ReactNode } from "react";

import { BuilderShell } from "@/components/builder/builder-shell";

/** Every `/builder` route renders inside the shell (F §4.7). */
export default function BuilderLayout({ children }: { children: ReactNode }) {
  return <BuilderShell>{children}</BuilderShell>;
}
```

Create `frontend/src/app/(signed-in)/(church)/builder/page.tsx`:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useDraft } from "@/lib/draft/context";

/** `/builder` opens the step the draft was last on (F §4.7 "Navigation"). */
export default function BuilderIndexPage() {
  const { draft } = useDraft();
  const router = useRouter();
  const target = `/builder/${draft.last_step}`;

  useEffect(() => {
    router.replace(target);
  }, [router, target]);

  return <Skeleton className="h-40 w-full" />;
}
```

Create `frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx`:

```tsx
"use client";

import { StepPlaceholder } from "@/components/builder/step-placeholder";

/** Step: Date & readings. Slice 2c replaces the placeholder with the step (owner answer Q1). */
export default function ReadingsStepPage() {
  return <StepPlaceholder step="readings" />;
}
```

Create `frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx`:

```tsx
"use client";

import { StepPlaceholder } from "@/components/builder/step-placeholder";

/** Step: Hymns. Slice 3 replaces the placeholder. */
export default function HymnsStepPage() {
  return <StepPlaceholder step="hymns" />;
}
```

Create `frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx`:

```tsx
"use client";

import { StepPlaceholder } from "@/components/builder/step-placeholder";

/** Step: Liturgy. Slice 4 replaces the placeholder. */
export default function LiturgyStepPage() {
  return <StepPlaceholder step="liturgy" />;
}
```

Create `frontend/src/app/(signed-in)/(church)/builder/review/page.tsx`:

```tsx
"use client";

import { StepPlaceholder } from "@/components/builder/step-placeholder";
import { StillNeeded } from "@/components/builder/still-needed";

/** Step: Review & send. Slice 5a replaces the placeholder; "Still needed" lists shipped steps' gaps. */
export default function ReviewStepPage() {
  return (
    <>
      <StepPlaceholder step="review" />
      <StillNeeded />
    </>
  );
}
```

- [ ] **Step 7 (agent): Run the test, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/components/builder/builder-shell.test.tsx 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
(cd frontend && npx vitest run src/components/builder 2>&1 | grep -E "Warning|not wrapped in act" | head -3)
```

**Expected:** `Tests  8 passed (8)`; `Test Files  48 passed (48)`, `Tests  297 passed (297)`; `> tsc --noEmit`, `> eslint`, nothing after; no `act(` warning.

- [ ] **Step 8 (agent): Commit and back up**

```bash
git add frontend/src/lib/queries/church.ts frontend/src/components/builder/step-placeholder.tsx frontend/src/components/builder/still-needed.tsx frontend/src/components/builder/step-progress.tsx frontend/src/components/builder/step-footer.tsx frontend/src/components/builder/summary-panel.tsx frontend/src/components/builder/summary-sheet.tsx frontend/src/components/builder/new-service-menu-item.tsx frontend/src/components/builder/step-header.tsx frontend/src/components/builder/builder-shell.tsx frontend/src/components/builder/builder-shell.test.tsx 'frontend/src/app/(signed-in)/(church)/builder/layout.tsx' 'frontend/src/app/(signed-in)/(church)/builder/page.tsx' 'frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx' 'frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx' 'frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx' 'frontend/src/app/(signed-in)/(church)/builder/review/page.tsx'
git commit -m "Builder: the shell and all four step routes, with the Available soon card (F §4.7, acceptance 11; S Builder shell; owner answers Q1, Q2)" -m "Every /builder route renders inside BuilderShell: Service Builder with a
Summary button and a New service menu, the step progress (every step a
link; Soon until a step ships), the sticky footer (Back and Next), and the
summary as a sticky column on desktop or a bottom sheet on a phone. The
four steps show \"Available soon\" with \"Keep using the current app for
this part.\" and no link to the old app. /builder opens the step last
visited; visiting a step records it without touching updated_at. New
service resets a draft with nothing to lose, or asks first. The readings
status, Still needed rows and summary lines are ready behind
SHIPPED_STEPS for 2c. Frontend 289 -> 297.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T9):** every page and layout starts with `"use client"`; the placeholder has no link; `setLastStep` runs only for step paths; New service uses `isDirty` (clarification 10) and pushes `/builder/readings`; the summary column and the sheet render the same `SummaryPanel`; the footer hides below `md` only while `useKeyboardOpen()` is true; text is React text only.

### Task 10: `/` opens the builder, `AppNav` in the header, and one draft per church (F §4.1, §4.2, §4.6 "Key", acceptance 10; S "Routes and files" first line, Hand-offs row 2 "AppNav", Testing `church-switch.test.tsx`; AC10, AC17; clarifications 16–18, 27)

The last code task. `/` stops showing the slice-0 placeholder cards and redirects to `/builder` (the `(signed-in)` layout has already followed any stored post-login path, so an invite link or `/login?next=` still wins). `AppNav` arrives with its one item, "Builder", placed by `AppHeader`'s grid: a segmented row under the header on a phone, a link row between the church switcher and the account menu from `md`. A church-switch test runs the real layouts around the builder to show each church keeps its own draft.

**Files:**
- Modify: `frontend/src/app/(signed-in)/(church)/page.tsx` (redirect), `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx` (one test replaced)
- Create: `frontend/src/components/app/app-nav.tsx`
- Modify: `frontend/src/components/app/app-header.tsx`, `frontend/src/components/app/app-header.test.tsx` (+1 test)
- Test: `frontend/src/components/builder/church-switch.test.tsx` (new, 1 test)

**Interfaces:**
- Consumes: T3 fixtures (`churchProfile`, `DRAFT_NOW`, `USER_ID`, `CHURCH_IDS`), `draftKey`; T4 `editOccasion`; T7 `useDraft`; T9 `BuilderLayout`; the `(signed-in)` and `(church)` layouts; `storeChurchId`; `setTestPath`, `testRouter`.
- Produces: `AppNav({ className? })` and `NAV_ITEMS` (`components/app/app-nav.tsx`); `/` → `/builder`. Later users: 5a adds "Services" to `NAV_ITEMS`, 5b or 6a "Settings".

Counts after this task: frontend **299 passed in 49 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
test ! -e frontend/src/components/app/app-nav.tsx && test ! -e frontend/src/components/builder/church-switch.test.tsx && echo "no T10 files yet"
grep -c "coming soon" 'frontend/src/app/(signed-in)/(church)/page.tsx'
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `no T10 files yet`; `1`; `Test Files  48 passed (48)`, `Tests  297 passed (297)`.

- [ ] **Step 2 (agent): Write the failing tests**

In `frontend/src/app/(signed-in)/(church)/church-layout.test.tsx`, replace the whole test `it("the home page shows the confirmed church from useChurch()", …)` (it asserted the slice-0 cards) with:

```tsx
  it("the home page opens the Service Builder (F §4.1: / redirects to /builder)", async () => {
    installFakeApi({ "GET /me": me(), "GET /church": GRACE });

    renderShell(<HomePage />);

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/builder"));
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/coming soon/)).toBeNull();
  });
```

(`waitFor`, `screen`, `testRouter`, `installFakeApi`, `me` and `GRACE` are already imported or defined in that file.)

In `frontend/src/components/app/app-header.test.tsx`, change `import { testRouter } from "@/test/mocks";` to `import { setTestPath, testRouter } from "@/test/mocks";` and add this test as the last one inside `describe("AppHeader", …)`:

```tsx
  it("shows the Builder nav item on church pages, current under /builder, and no nav without churches (F §4.2)", () => {
    setTestPath("/builder/hymns");
    const { unmount } = render(
      <AppHeader user={pat} churches={[graceAdmin]} active={graceAdmin} onSelectChurch={vi.fn()} onSignOut={vi.fn()} />,
    );
    const nav = screen.getByRole("navigation", { name: "Main" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((link) => [link.textContent, link.getAttribute("href")])).toEqual([["Builder", "/builder"]]);
    expect(links[0]).toHaveAttribute("aria-current", "page");
    unmount();

    setTestPath("/welcome");
    const { unmount: unmountWelcome } = render(
      <AppHeader user={pat} churches={[graceAdmin]} active={graceAdmin} onSelectChurch={vi.fn()} onSignOut={vi.fn()} />,
    );
    expect(screen.getByRole("link", { name: "Builder" })).not.toHaveAttribute("aria-current");
    unmountWelcome();

    render(<AppHeader user={pat} onSignOut={vi.fn()} />);
    expect(screen.queryByRole("navigation", { name: "Main" })).toBeNull();
  });
```

Create `frontend/src/components/builder/church-switch.test.tsx`:

```tsx
/**
 * One draft per church (F §4.6 key, F acceptance 10; S Testing
 * `church-switch.test.tsx`): the real `(signed-in)` and `(church)` layouts
 * around the builder, against the fake API. A switch remounts the builder
 * under the other church's key; switching back restores the first draft.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import SignedInLayout from "@/app/(signed-in)/layout";
import ChurchLayout from "@/app/(signed-in)/(church)/layout";
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { storeChurchId } from "@/lib/church";
import { useDraft } from "@/lib/draft/context";
import { editOccasion } from "@/lib/draft/readings";
import { draftKey } from "@/lib/draft/schema";
import { type RecordedRequest, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, churchProfile, DRAFT_NOW, me, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

const GRACE = churchProfile();
const HOPE = churchProfile({ id: CHURCH_IDS.hope, name: "Hope", role: "member", timezone: "America/Chicago" });

function OccasionProbe() {
  const { draft, update } = useDraft();
  return (
    <div>
      <p>Draft for {draft.church_id === GRACE.id ? "Grace" : "Hope"}: {draft.readings.occasion || "empty"}</p>
      <button type="button" onClick={() => update((d) => editOccasion(d, "Harvest at Grace"))}>
        Type an occasion
      </button>
    </div>
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("church switch keeps one draft per church", () => {
  it("shows the other church's own draft and restores the first on the way back", async () => {
    installFakeApi({
      "GET /me": me({ churches: [church(), church({ id: CHURCH_IDS.hope, name: "Hope", role: "member" })] }),
      "GET /church": (req: RecordedRequest) => (req.headers["X-Church-Id"] === HOPE.id ? HOPE : GRACE),
    });
    storeChurchId(GRACE.id);
    const { user } = renderWithProviders(
      <SignedInLayout>
        <ChurchLayout>
          <BuilderLayout>
            <OccasionProbe />
          </BuilderLayout>
        </ChurchLayout>
      </SignedInLayout>,
      { path: "/builder/readings" },
    );

    expect(await screen.findByText("Draft for Grace: empty")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Type an occasion" }));
    expect(screen.getByText("Draft for Grace: Harvest at Grace")).toBeInTheDocument();

    act(() => storeChurchId(HOPE.id));
    expect(await screen.findByText("Draft for Hope: empty")).toBeInTheDocument();
    // The switch unmounted Grace's builder, which wrote its draft at once.
    const graceStored = JSON.parse(window.localStorage.getItem(draftKey(USER_ID, GRACE.id)) ?? "null");
    expect(graceStored.readings.occasion).toBe("Harvest at Grace");

    act(() => storeChurchId(GRACE.id));
    expect(await screen.findByText("Draft for Grace: Harvest at Grace")).toBeInTheDocument();
    await waitFor(() => expect(window.localStorage.getItem(draftKey(USER_ID, HOPE.id))).not.toBeNull());
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run 'src/app/(signed-in)/(church)/church-layout.test.tsx' src/components/app/app-header.test.tsx src/components/builder/church-switch.test.tsx 2>&1 | grep -E "×|Tests ")
```

**Expected:** `×` on "the home page opens the Service Builder" (`expected "spy" to be called with arguments: [ '/builder' ]`) and on "shows the Builder nav item…" (`Unable to find an accessible element with the role "navigation" and name "Main"`); the church-switch test passes already (it tests T6, T7 and T9, which exist: it is the regression net for them); `Tests  2 failed | 20 passed (22)`.

- [ ] **Step 4 (agent): Redirect `/` to `/builder`**

Replace `frontend/src/app/(signed-in)/(church)/page.tsx` with:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/**
 * Home (`/`) opens the Service Builder (F §4.1; S "Routes and files"). The
 * `(signed-in)` layout has already followed any stored post-login path before
 * this page mounts.
 */
export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/builder");
  }, [router]);

  return (
    <main className="mx-auto grid max-w-2xl gap-4 p-4" aria-busy="true">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-40 w-full" />
    </main>
  );
}
```

- [ ] **Step 5 (agent): Add `AppNav` and place it in the header**

Create `frontend/src/components/app/app-nav.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

/** Nav items in order; each appears once its slice ships (F §4.2). 5a adds "Services", 5b or 6a "Settings". */
export const NAV_ITEMS = [{ href: "/builder", label: "Builder" }] as const;

/**
 * Primary navigation (F §4.2; S Hand-offs "AppNav"). One element for every
 * width: `AppHeader` places it as a segmented row under the header below
 * `md`, and as a link row inside the header from `md`.
 */
export function AppNav({ className }: { className?: string }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className={className}>
      <ul className="grid auto-cols-fr grid-flow-col gap-1 rounded-lg bg-muted p-1 md:flex md:bg-transparent md:p-0">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex h-9 items-center justify-center rounded-md px-3 text-sm font-medium text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  "aria-[current=page]:bg-background aria-[current=page]:text-foreground aria-[current=page]:shadow-sm",
                  "md:aria-[current=page]:bg-muted md:aria-[current=page]:shadow-none",
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
```

Replace `frontend/src/components/app/app-header.tsx` with:

```tsx
"use client";

import { AccountMenu } from "@/components/app/account-menu";
import { AppNav } from "@/components/app/app-nav";
import { ChurchSwitcher } from "@/components/app/church-switcher";
import type { Church, Me } from "@/lib/church";

type Props = {
  user: Me["user"];
  churches?: Church[];
  active?: Church | null;
  onSelectChurch?: (id: string) => void;
  onSignOut: () => void;
};

/**
 * The signed-in header (F §4.2). With `churches` and `onSelectChurch` it shows
 * the church switcher and the primary nav (`AppNav`, slice 2): a link row
 * between the switcher and the account menu from `md`, a segmented row under
 * them below `md`. Without them (`/welcome`) it shows the app name and no nav.
 * The account menu is always there, so every signed-in screen can log out (S A6).
 */
export function AppHeader({ user, churches, active = null, onSelectChurch, onSignOut }: Props) {
  const showSwitcher = churches !== undefined && churches.length > 0 && onSelectChurch !== undefined;

  return (
    <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto grid max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1 px-4 py-2 md:grid-cols-[minmax(0,1fr)_auto_auto]">
        <div className="min-w-0">
          {showSwitcher ? (
            <ChurchSwitcher churches={churches} activeId={active?.id ?? null} onSelect={onSelectChurch} />
          ) : (
            <span className="font-semibold">Worship Service Builder</span>
          )}
        </div>
        {showSwitcher ? (
          <AppNav className="col-span-2 row-start-2 md:col-span-1 md:col-start-2 md:row-start-1" />
        ) : null}
        <div className="col-start-2 row-start-1 md:col-start-3">
          <AccountMenu user={user} role={active?.role} onSignOut={onSignOut} />
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 6 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run 'src/app/(signed-in)/(church)/church-layout.test.tsx' src/components/app/app-header.test.tsx src/components/builder/church-switch.test.tsx 2>&1 | tail -4)
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
grep -rn "coming soon\|coming later" frontend/src --include=*.tsx; echo "placeholder copy grep exit $?"
```

**Expected:** `Test Files  3 passed (3)`, `Tests  22 passed (22)`; `Test Files  49 passed (49)`, `Tests  299 passed (299)`; `> tsc --noEmit`, `> eslint`, nothing after; `placeholder copy grep exit 1` (the slice-0 home copy is gone).

- [ ] **Step 7 (agent): Commit and back up**

```bash
git add 'frontend/src/app/(signed-in)/(church)/page.tsx' 'frontend/src/app/(signed-in)/(church)/church-layout.test.tsx' frontend/src/components/app/app-nav.tsx frontend/src/components/app/app-header.tsx frontend/src/components/app/app-header.test.tsx frontend/src/components/builder/church-switch.test.tsx
git commit -m "Builder: home opens the builder, AppNav in the header, one draft per church (F §4.1, §4.2, acceptance 10; S Routes; AC17)" -m "/ now redirects to /builder instead of showing the slice-0 placeholder
cards. The header gains AppNav with its first item, Builder: a segmented
row under the header on a phone, a link row next to the account menu from
md; it shows on church pages only, and the header content widens to match
the desktop builder. A test runs the real layouts around the builder to
show that switching church opens that church's own draft and switching
back restores the first. Frontend 297 -> 299.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T10):** the home page is a client component that only redirects; `AppNav` marks `aria-current="page"` for `/builder` and its sub-paths; `/welcome`'s header has no nav; the church-switch test really remounts (the probe shows each church's draft), and Grace's edit was written when its builder unmounted.

### Task 11: Docs: the "(2b plan)" corrections to S and one F amendment row (S top, Builder shell, Frontend changes, Draft store, Testing, Manual checks; F Amendments, §4.7; owner answers Q1, Q2; clarifications 1–5, 8–10, 18, 29)

S and F are the documents 2c, 3, 4 and 5a will read, so they must say what 2b actually built. S gains eleven short "(2b plan)" notes where the plan departs from or sharpens its text; F gains one amendment row (the index F keeps of slice changes) and a note in §4.7. No code changes, and no docs test pins these lines (`test_slice1_docs.py` reads other F sections; its count stays the same).

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`, `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`
- Test: none new; `backend/tests/test_ops_workflows.py`, `test_slice1_docs.py` and `test_docs.py` must still pass (89).

**Interfaces:**
- Consumes: the clarifications above and the code of T1–T10.
- Produces: S and F as 2c's plan will read them.

Counts after this task: frontend **299 passed in 49 files**; backend **971 passed, 9 skipped**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "(2b plan" docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); `89 passed in <t>s`.

- [ ] **Step 2 (agent): Apply the edits**

Each anchor must match exactly once, or the script stops before writing anything for that file:

```bash
.venv/bin/python - <<'PYEOF'
from pathlib import Path

S = Path("docs/superpowers/specs/2026-09-25-slice-2-readings-design.md")
F = Path("docs/superpowers/specs/2026-09-25-migration-foundations-design.md")


def edit(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        assert text.count(old) == 1, f"{path}: anchor not found exactly once: {old[:70]!r}"
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


edit(S, [
    ("- **2c** the Date & readings step UI.\n",
     "- **2c** the Date & readings step UI.\n"
     "- (2b plan) The split in detail: 2b also ships every pure draft module (`readings.ts`, `date-effects.ts`, "
     "`status.ts`, `mapping.ts`, `fingerprint.ts`, `prune.ts`), `useKeyboardOpen`, `AppNav` and the `sheet` and "
     "`badge` components; 2c ships the three query modules (`lectionary.ts`, `reference.ts`, `passages.ts`), "
     "`use-debounced-value.ts`, `useLectionarySync()`, the step's components, `radio-group`, `collapsible` and "
     "`tooltip`, and adds `\"readings\"` to `SHIPPED_STEPS`.\n"),
    ('are marked "(2a build)".\n',
     'are marked "(2a build)". Corrections made while planning 2b '
     '(`docs/superpowers/plans/2026-09-28-slice-2b-frontend.md`, 2026-09-28) are marked "(2b plan)".\n'),
    ("Slice 3 replaces the Hymns card, slice 4 the Liturgy card, and 5a the Review card, deleting `StepPlaceholder`.",
     "Slice 3 replaces the Hymns card, slice 4 the Liturgy card, and 5a the Review card, deleting `StepPlaceholder`. "
     "(2b plan: until 2c, Date & readings shows the same card and `\"readings\"` is not in `SHIPPED_STEPS`, owner "
     "answer Q1, 2026-09-28; the card has no link to the old app, owner answer Q2. With no step shipped, "
     "\"Still needed\" is hidden and the summary's Date block shows only the date.)"),
    ('in memory-only mode, "Draft not saved on this device".',
     'in memory-only mode, "Draft not saved on this device" (2b plan: followed by " · Not in archive", '
     'as F §4.7 keeps the two halves).'),
    ("  - If the draft is pristine (see `isPristine` below), it resets immediately.",
     "  - If the draft is pristine (see `isPristine` below), it resets immediately. (2b plan: the check is F §4.6's "
     "`isDirty(draft)`, which equals \"not pristine\" until 5a saves drafts.)"),
    ("`select`, `dropdown-menu` and `skeleton` already exist from slice 0.)",
     "`select`, `dropdown-menu` and `skeleton` already exist from slice 0.) (2b plan: 2b adds `sheet` and `badge`, "
     "hand-written thin wrappers over Base UI when the registry cannot be reached, a recorded exception to "
     "F §4.9.1; `textarea` exists from slice 1; `radio-group`, `collapsible` and `tooltip` are 2c's.)"),
    ("- **`schema.ts`:** the zod schema for `DraftV1` exactly as in F §4.6, with `DRAFT_VERSION = 1`.",
     "- **`schema.ts`:** the zod schema for `DraftV1` exactly as in F §4.6, with `DRAFT_VERSION = 1`. (2b plan: "
     "without 5a's `save_key_fingerprint` and `editing.date_iso`, which 5a adds with its version bump.)"),
    ("  - Every read and write goes through `lib/storage.ts` (slice 1).",
     "  - Every read and write goes through `lib/storage.ts` (slice 1). (2b plan: it gains `tryWriteLocal`, which "
     "reports a failed write, and `localKeys`. A fresh or repaired draft is written when the builder opens; "
     "`replace` also sets `updated_at`; a stored draft whose user or church differs from its key is treated as "
     "unrestorable.)"),
    ('and `SHIPPED_STEPS = new Set(["readings"])`.',
     "and `SHIPPED_STEPS`, empty in 2b (2b plan, owner answer Q1); 2c adds `\"readings\"`."),
    ("| `builder/readings/church-switch.test.tsx` |",
     "| `builder/church-switch.test.tsx` (2b plan: in 2b, since it tests the store and the shell) |"),
    ("### Manual checks (append to `docs/manual-verification.md`; at 375 px and on desktop, on the production URL)\n",
     "### Manual checks (append to `docs/manual-verification.md`; at 375 px and on desktop, on the production URL)\n\n"
     "(2b plan: 2c appends these, and updates `backend/tests/test_slice1_docs.py`, which pins the file's last two "
     "`##` headings. 2b adds none: its after-merge look is the owner's short check in the 2b plan's Task 13.)\n"),
])

edit(F, [
    ("Thread-pool log lines keep the request id. | 2a |\n",
     "Thread-pool log lines keep the request id. | 2a |\n"
     "| §4.2, §4.6, §4.7 | *(2026-09-28, slice 2b plan)* The builder ships live with every step on the \"Available "
     "soon\" card until its slice turns it on: `SHIPPED_STEPS` starts empty and slice 2c adds \"readings\" (owner "
     "answer Q1). The draft store writes through `lib/storage.ts`'s `tryWriteLocal`, which reports a failed write; "
     "a fresh draft is written when the builder opens; \"New service\" confirms when the draft `isDirty`. `AppNav` "
     "shows on church pages only. | 2b |\n"),
    ("Steps 2-4 render an \"Available soon — keep using the current app for this part\" card inside the working "
     "shell until their slice fills them.",
     "Steps 2-4 render an \"Available soon — keep using the current app for this part\" card inside the working "
     "shell until their slice fills them. *(2026-09-28, slice 2b plan: step 1 too, until slice 2c.)*"),
])
print("docs edited")
PYEOF
git diff --stat
```

**Expected:** `docs edited`; ` .../2026-09-25-migration-foundations-design.md |  3 ++-`, ` .../specs/2026-09-25-slice-2-readings-design.md | 21 ++++++++++++---------`, ` 2 files changed, 14 insertions(+), 10 deletions(-)`. An `AssertionError` names the anchor that moved: read that part of the spec, fix the anchor in this step (not the spec's other text), and run the step again from a clean file (`git checkout -- <file>`).

- [ ] **Step 3 (agent): Check the result**

```bash
grep -c "(2b plan" docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
grep -c "slice 2b plan" docs/superpowers/specs/2026-09-25-migration-foundations-design.md
grep -c 'new Set(\["readings"\])' docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
git diff -U0 docs | grep '^+' | grep -v '^+++' | grep -c '—'
```

**Expected:** `11`; `2`; `0` (grep exits 1: S no longer says `SHIPPED_STEPS = new Set(["readings"])`); `89 passed in <t>s`; `971 passed, 9 skipped in <t>s`; `1` (the only em dash on an added line is F §4.7's existing copy "Available soon — keep using the current app for this part", on the line that gains the note; the new prose has none).

- [ ] **Step 4 (agent): Commit and back up**

```bash
git add docs/superpowers/specs/2026-09-25-slice-2-readings-design.md docs/superpowers/specs/2026-09-25-migration-foundations-design.md
git commit -m "Docs: slice 2b corrections to S and an F amendment row (S Builder shell, Draft store; F §4.6, §4.7)" -m "Marks \"(2b plan)\" in the slice 2 spec where 2b built something more
precisely than written: the 2b/2c split, Date & readings on the Available
soon card until 2c (SHIPPED_STEPS empty; owner answers Q1 and Q2), the
memory-only status line, New service's isDirty check, sheet and badge,
DraftV1 without 5a's fields, the storage helpers and first write, the
church-switch test's place, and the manual checks left to 2c. F gains one
amendment row and a note in §4.7.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push origin claude/slice-2-plan-4q33le
```

**Review checkpoint (T11):** every note says "(2b plan)" and matches the code; nothing else in S or F changed (`git show --stat HEAD` lists the two files only).

### Task 12: Whole-branch verification and the slice 2b pull request (owner's yes before the PR is opened and before it is marked ready) (S Testing "Frontend", AC8, AC10–AC12, AC17; F §4.1, §4.3, §4.9, §4.10, §5.2, §5.4; owner decisions 3, 4; owner answers Q1–Q3; clarifications 3, 4, 29)

The whole branch is checked in one place before anyone reviews it: the frontend suite three times (so a clock- or timing-dependent test shows up here and not in CI), types, lint, the production build and its routes, the backend suite (unchanged), the generated API files (unchanged), the gates (client components, no link to the old app, storage only through `lib/storage.ts`, no raw HTML, `SHIPPED_STEPS` empty, no Python or workflow change), the exact list of changed paths, and the exact list of commits against this plan. The branch is already on GitHub from the backup pushes (owner answer Q3), but no PR exists; on the owner's first yes the agent opens it as a **draft**, so CI runs. When CI is green, the agent reports and, on the owner's second yes, marks it ready. Merging is Task 13, with its own yes.

Below, `<scratch>` is the absolute path of the session's scratchpad directory, and `<N>` is the PR number Step 10 prints; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never run a bare `git push` or `--force`.

**Files:** none changed. A local or CI failure is fixed in its owning task's files (Step 14).

**Interfaces:**
- Consumes: everything from T1–T11, in particular each task's commit subject (Step 8 reads them from this plan between `### Task 1:` and `### Task 12:`), the cumulative counts (230, 240, 247, 256, 268, 280, 288, 289, 297, 299, 299 after T1–T11), `SHIPPED_STEPS` (T5), the builder routes (T9, T10), and CI (`.github/workflows/ci.yml`, unchanged: `backend`, `backend-postgres`, `frontend` with lint, typecheck, `API types match the OpenAPI snapshot (F §5.4)`, test and build).
- Produces: PR `<N>` (`claude/slice-2-plan-4q33le` → `main`), titled `Slice 2b frontend foundation: builder shell, draft store, dates and scripture refs`, not a draft after Step 13, CI green on the branch head, its body holding the line `Tests: frontend 221 → 299 in 34 → 49 files; backend 971 → 971 passed, 9 → 9 skipped` and ending with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Later user: T13.

- [ ] **Step 1 (agent): Bring the branch up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git log --oneline -1 origin/main
git log --oneline origin/main..HEAD | tail -1
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
```

**Expected,** in order: nothing (or `?? .claude/`); the fetch prints nothing or only updated refs; `0`; `864ebcd Merge pull request #21 from bbrown62450/claude/slice-2-plan-4q33le` (or a later merge the owner made); the branch's oldest commit, `<sha> Plan: slice 2b frontend foundation (S slice 2; owner answers 2026-09-28)`; `0` (every commit was backed up).
- If the first count is not `0`: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 12)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"`. On a conflict, run `git merge --abort`, stop and tell the owner which files conflict. Without one, continue: Steps 2–8 run on the merged tree, and any new tests the merge brought change the totals by exactly those (name them in the Step 9 message).
- If `git status --short` shows anything else, stop: commit it in its owning task or ask.

- [ ] **Step 2 (agent): Run the frontend suite three times, then types and lint**

```bash
for i in 1 2 3; do (cd frontend && npm test 2>&1 | grep -E "Test Files|Tests |FAIL"); done
(cd frontend && npm test 2>&1 | grep -cE "Warning:|not wrapped in act")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
```

**Expected:** three times ` Test Files  49 passed (49)` and `      Tests  299 passed (299)` (baseline 221 in 34; after T1–T11: 230, 240, 247, 256, 268, 280, 288, 289, 297, 299, 299) and no `FAIL`; `0`; `> tsc --noEmit` and `> eslint` with nothing after. Any other number: find the task whose count drifted. A run that fails even once in three is a failure (Step 14): make the test deterministic rather than retrying it.

- [ ] **Step 3 (agent): Run the backend suite and the Postgres marker count**

```bash
.venv/bin/python -m pytest -q | tail -1
.venv/bin/python -m pytest -q -m postgres | tail -1
```

**Expected:** `971 passed, 9 skipped in <t>s` (unchanged: 2b changes no Python file and no test reads `next_sunday.json`); `9 skipped, 971 deselected in <t>s`.

- [ ] **Step 4 (agent): Build the frontend with CI's placeholder environment**

```bash
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/builder")
(cd frontend && node -e 'const m = require("./.next/app-path-routes-manifest.json"); console.log(Object.values(m).sort().join(" "))')
```

**Expected:** `✓ Compiled successfully in <t>s`, the route table's five builder lines (`├ ○ /builder`, `├ ○ /builder/hymns`, `├ ○ /builder/liturgy`, `├ ○ /builder/readings`, `├ ○ /builder/review`) and no `Error` line; then exactly:

```
/ /_global-error /_not-found /auth/callback /builder /builder/hymns /builder/liturgy /builder/readings /builder/review /favicon.ico /join /login /welcome
```

(1b's eight routes plus the five builder routes.) The build must run in the real checkout: Turbopack refuses a symlinked `node_modules`. If it fails only with `Failed to fetch` for a Geist font (no network), say so in the Step 9 message and rely on CI's `frontend` job.

- [ ] **Step 5 (agent): Check the generated API files did not change**

```bash
(cd frontend && npm run gen:api >/dev/null) && git diff --exit-code --stat frontend/src/lib/api/schema.d.ts; echo "schema diff exit $?"
git diff --name-only origin/main...HEAD -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts | wc -l
git status --short
```

**Expected:** `schema diff exit 0`; `0` (2b changes no API: 2a already generated the types it uses); nothing (or `?? .claude/`).

- [ ] **Step 6 (agent): Run the gates**

```bash
find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) -exec sh -c 'head -1 "$1" | grep -qx "\"use client\";" || echo "not a client component: $1"' _ {} \; ; echo "client components checked: $(find 'frontend/src/app/(signed-in)' \( -name page.tsx -o -name layout.tsx \) | wc -l)"
grep -rniE "streamlit|liturgy-frozen" frontend/src --include=*.ts --include=*.tsx | grep -vE "\.test\.tsx?:"; echo "old app grep exit $?"
grep -rnE "window\.(local|session)Storage|(local|session)Storage\.(getItem|setItem|removeItem|key|clear)" frontend/src --include=*.ts --include=*.tsx | grep -vE "^frontend/src/lib/storage\.ts:|\.test\.tsx?:|^frontend/src/test/"; echo "storage grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
grep -n "export const SHIPPED_STEPS" frontend/src/lib/draft/steps.ts
grep -rn "Available soon" frontend/src --include=*.tsx | grep -v "\.test\.tsx:" | wc -l
git diff --name-only origin/main...HEAD -- '*.py' backend/requirements.txt requirements-dev.txt backend/migrations .github docs/manual-verification.md docs/ops-runbook.md | wc -l
grep -c '"zod": "^4.6.5"' frontend/package.json frontend/package-lock.json
git diff origin/main...HEAD -- frontend/package-lock.json | grep -cE '^[-+] '
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -qx 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected,** in order:
- `client components checked: 10` with no "not a client component" line before it (F §4.1);
- `old app grep exit 1` (no link to or mention of the old app in the shipped code; owner answer Q2);
- `storage grep exit 1` (storage only through `lib/storage.ts`, F §4.3);
- `raw html grep exit 1`;
- `34:export const SHIPPED_STEPS: ReadonlySet<StepId> = new Set<StepId>([]);` (owner answer Q1);
- `2` (the "Available soon" copy lives in `step-placeholder.tsx` and `summary-panel.tsx` only);
- `0` (`wc` pads it: no Python, requirement, migration, workflow, manual-checklist or runbook change);
- `frontend/package.json:1` and `frontend/package-lock.json:1`;
- `4` (the lockfile diff: the `tw-animate-css` line gains a comma, the zod line, and the dropped `"dev": true`; clarification 4);
- only `trailer check done`.

Any other output: stop, find the owning task (Step 14) and fix it there.

- [ ] **Step 7 (agent): Check the exact list of changed paths**

```bash
LC_ALL=C sort > "<scratch>/slice2b-expected-paths.txt" <<'EOF'
backend/tests/fixtures/shared/next_sunday.json
docs/superpowers/plans/2026-09-28-slice-2b-frontend.md
docs/superpowers/specs/2026-09-25-migration-foundations-design.md
docs/superpowers/specs/2026-09-25-slice-2-readings-design.md
frontend/package-lock.json
frontend/package.json
frontend/src/app/(signed-in)/(church)/builder/hymns/page.tsx
frontend/src/app/(signed-in)/(church)/builder/layout.tsx
frontend/src/app/(signed-in)/(church)/builder/liturgy/page.tsx
frontend/src/app/(signed-in)/(church)/builder/page.tsx
frontend/src/app/(signed-in)/(church)/builder/readings/page.tsx
frontend/src/app/(signed-in)/(church)/builder/review/page.tsx
frontend/src/app/(signed-in)/(church)/church-layout.test.tsx
frontend/src/app/(signed-in)/(church)/page.tsx
frontend/src/app/(signed-in)/layout.tsx
frontend/src/app/(signed-in)/signed-in-layout.test.tsx
frontend/src/components/app/app-header.test.tsx
frontend/src/components/app/app-header.tsx
frontend/src/components/app/app-nav.tsx
frontend/src/components/builder/builder-shell.test.tsx
frontend/src/components/builder/builder-shell.tsx
frontend/src/components/builder/church-switch.test.tsx
frontend/src/components/builder/new-service-menu-item.tsx
frontend/src/components/builder/step-footer.tsx
frontend/src/components/builder/step-header.tsx
frontend/src/components/builder/step-placeholder.tsx
frontend/src/components/builder/step-progress.tsx
frontend/src/components/builder/still-needed.tsx
frontend/src/components/builder/summary-panel.tsx
frontend/src/components/builder/summary-sheet.tsx
frontend/src/components/ui/badge.tsx
frontend/src/components/ui/sheet.tsx
frontend/src/lib/api/types.ts
frontend/src/lib/dates.guard.test.ts
frontend/src/lib/dates.test.ts
frontend/src/lib/dates.ts
frontend/src/lib/draft/context.test.tsx
frontend/src/lib/draft/context.tsx
frontend/src/lib/draft/date-effects.ts
frontend/src/lib/draft/fingerprint.test.ts
frontend/src/lib/draft/fingerprint.ts
frontend/src/lib/draft/mapping.test.ts
frontend/src/lib/draft/mapping.ts
frontend/src/lib/draft/migrate.test.ts
frontend/src/lib/draft/migrate.ts
frontend/src/lib/draft/prune.test.ts
frontend/src/lib/draft/prune.ts
frontend/src/lib/draft/readings.test.ts
frontend/src/lib/draft/readings.ts
frontend/src/lib/draft/schema.test.ts
frontend/src/lib/draft/schema.ts
frontend/src/lib/draft/status.test.ts
frontend/src/lib/draft/status.ts
frontend/src/lib/draft/steps.ts
frontend/src/lib/draft/store.test.ts
frontend/src/lib/draft/store.ts
frontend/src/lib/queries/church.ts
frontend/src/lib/scripture-refs.test.ts
frontend/src/lib/scripture-refs.ts
frontend/src/lib/storage.test.ts
frontend/src/lib/storage.ts
frontend/src/lib/use-keyboard-open.test.tsx
frontend/src/lib/use-keyboard-open.ts
frontend/src/test/fixtures/index.ts
EOF
git diff --name-only --no-renames origin/main...HEAD | LC_ALL=C sort > "<scratch>/slice2b-actual-paths.txt"
wc -l < "<scratch>/slice2b-expected-paths.txt"
wc -l < "<scratch>/slice2b-actual-paths.txt"
LC_ALL=C comm -3 "<scratch>/slice2b-expected-paths.txt" "<scratch>/slice2b-actual-paths.txt"
git diff --name-status --no-renames origin/main...HEAD | cut -c1 | sort | uniq -c
```

**Expected:** `64`; `64`; `comm` prints nothing; then `  49 A` and `  15 M`. These are the File Structure's paths: 49 created (the plan, the fixture, 47 frontend files) and 15 modified (13 frontend files and the two specs). An indented `comm` line (changed, not listed) means a task touched a file its **Files:** does not name: find it with `git log --format='%h %s' origin/main..HEAD -- '<path>'`; anything under `backend/` other than the fixture, `frontend/src/lib/api/`, `.github/` or `docs/manual-verification.md` is a stop. An unindented line means a task's commit is missing.

- [ ] **Step 8 (agent): Check the exact list of commits against this plan**

```bash
.venv/bin/python - docs/superpowers/plans/2026-09-28-slice-2b-frontend.md > "<scratch>/slice2b-plan-subjects.txt" <<'EOF'
import pathlib, re, sys
text = "\n" + pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
lines = text.split("\n### Task 1:", 1)[1].split("\n### Task 12:", 1)[0].splitlines()
print("Plan: slice 2b frontend foundation (S slice 2; owner answers 2026-09-28)")
for line in lines:
    m = re.match(r'\s*git commit -m "((?:[^"\\]|\\.)*)"', line)
    if m:
        print(re.sub(r"\\(.)", r"\1", m.group(1)))
EOF
git log --reverse --no-merges --format=%s origin/main..HEAD > "<scratch>/slice2b-branch-subjects.txt"
wc -l < "<scratch>/slice2b-plan-subjects.txt"
diff "<scratch>/slice2b-plan-subjects.txt" "<scratch>/slice2b-branch-subjects.txt"; echo "commit list diff exit $?"
git log --reverse --format='%h %s' origin/main..HEAD
```

**Expected:** `12` (the plan, then one commit for each of T1–T11); `commit list diff exit 0` with no output before it; the twelve commits oldest first (plus a Step 1 merge, if any), from `<sha> Plan: slice 2b frontend foundation (S slice 2; owner answers 2026-09-28)` to `<sha> Docs: slice 2b corrections to S and an F amendment row (S Builder shell, Draft store; F §4.6, §4.7)`. A `diff` line is a failure unless it is a `>` line `Fix: … (Task <n> review)` (a review fix, Global Constraints), `Fix: … (Task <n>, slice 2b final verification)` (Step 14) or `Plan: …` (a plan correction the controller committed), each named in the Step 9 message; then the first count differs from the branch's by exactly those lines.

- [ ] **Step 9 (agent → OWNER): Ask for the go-ahead to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
git rev-list --count origin/main..HEAD
```

**Expected:** one `✓ Logged in to github.com account <login> (keyring)` line; `[]` (no open PR from this branch; PRs #20 and #21 are merged); the Step 8 count (12, plus a merge or fixes). If `gh` is not logged in, ask the owner to run `gh auth login`. If an open PR exists, stop and ask.

Send the owner exactly this message, with `<count>` filled in, and wait for a clear yes:

> Slice 2b is verified locally: frontend 299 tests in 49 files, passing three runs in a row (221 in 34 before); typecheck, lint and the production build are clean, and the build lists the five builder pages; the backend is unchanged at 971 passed, 9 skipped; the API types did not change; the checks are clean (every page is a client component, no link to the old app, the draft goes through the storage helper only, all four steps on "Available soon" until 2c); changed files (64) and commits (<count>) are as planned, and every commit is already backed up on the branch. May I open the pull request as a **draft** titled "Slice 2b frontend foundation: builder shell, draft store, dates and scripture refs", so the checks run? I will come back with the results and ask again before marking it ready. Merging stays with you (Task 13).

Add one line per note from Steps 1–8 (a merge from `main`, a skipped font download, a `Fix:` commit, how `sheet` and `badge` were made). A no leaves the branch as it is.

- [ ] **Step 10 (agent, on the owner's yes): Write the PR body and open the draft PR**

```bash
cat > "<scratch>/slice2b-pr-body.md" <<'EOF'
PR 2b of slice 2: the frontend foundation. After it merges, a signed-in member lands on the Service Builder instead of the old placeholder page. All four steps (Date & readings included, until 2c) show "Available soon" with "Keep using the current app for this part." and no link to the old app (owner answers Q1 and Q2, 2026-09-28). Spec: docs/superpowers/specs/2026-09-25-slice-2-readings-design.md (2b). Plan: docs/superpowers/plans/2026-09-28-slice-2b-frontend.md. No backend change (one shared JSON test fixture is added), no migration, no API change.

Builder
- `/` redirects to `/builder`, which opens the step last visited; `/builder/readings`, `/hymns`, `/liturgy` and `/review` render inside the shell.
- The shell: "Service Builder" with a "Summary" button (phones) and a "More actions" menu with "New service"; the step progress (every step a link; "Soon" until a step ships; Review "Not in archive"); a sticky footer with Back and Next that steps aside while the phone keyboard is up; the summary as a sticky right column on desktop and a bottom sheet on a phone (date, then "Available soon" blocks, and "Draft saved on this device · Not in archive").
- "New service" resets a draft with nothing to lose at once, and otherwise asks "Start a new service?".
- The header gains the primary nav with its first item, "Builder" (church pages only).

Draft store (`src/lib/draft/`)
- `DraftV1` as a zod schema (F §4.6, without slice 5a's two fields), the fresh draft (next Sunday in the church's time zone), migrations, and a store per user and church in `localStorage["wsb:draft:{user}:{church}"]`: writes 400 ms after a change and at once when the page is hidden or left; a draft that cannot be restored is backed up and replaced ("We couldn't restore your unsaved draft."); blocked storage keeps the draft in memory with one warning; another tab's newer draft is adopted ("Updated from another tab."); drafts older than 30 days or for churches the member left are removed after `/me` loads.
- The readings transitions and selectors, step status, "Still needed", the provisional payload and its fingerprint are pure, tested modules that 2c builds the Date & readings step on. `SHIPPED_STEPS` is empty; 2c adds "readings".

Libraries
- `src/lib/dates.ts` (date-only helpers; a test fails on `new Date("YYYY-MM-DD")` anywhere in `src/`).
- `src/lib/scripture-refs.ts`, the TypeScript port of `backend/scripture_refs.py`, passing every case of `backend/tests/fixtures/shared/scripture_refs.json`.
- `zod` becomes a direct dependency (two lockfile lines). `sheet` and `badge`: @SHEET_LINE@

Standing-permission choices (owner decision 1: no owner-visible change) that differ from the spec's text: a draft stored under another user's or church's key is treated as unrestorable; a fresh draft is written when the builder opens; `replace` also sets `updated_at`; `lib/storage.ts` gains `tryWriteLocal` and `localKeys`; zod added by editing the lockfile rather than `npm install`. Owner-visible choices the owner accepted with the plan: the memory-only status line reads "Draft not saved on this device · Not in archive"; a finished step reads "Complete" with a check; the header nav shows on church pages only and the header content is wider on desktop.

Not in 2b (slice 2c): the Date & readings step itself, the lectionary, translation and passage queries, the automatic lectionary fill, and the slice 2 manual checklist.

Tests: frontend 221 → 299 in 34 → 49 files; backend 971 → 971 passed, 9 → 9 skipped

After merge (Task 13): a short look by the owner on a phone and on desktop (the builder, the step bar, Summary, New service), then a short "Slice 2b record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
```

If the owner changed any answer to question B, adjust the "Owner-visible choices" sentence to match. Replace `@SHEET_LINE@` with `generated from the base-nova registry.` or `hand-written thin wrappers over Base UI, because the build container cannot reach the registry (plan clarification 3, owner answer A).` (T8's commit body says which), then:

```bash
grep -c '@SHEET_LINE@' "<scratch>/slice2b-pr-body.md"
grep -cx 'Tests: frontend 221 → 299 in 34 → 49 files; backend 971 → 971 passed, 9 → 9 skipped' "<scratch>/slice2b-pr-body.md"
git fetch origin && test "$(git rev-list --count HEAD..origin/main)" = 0 && test "$(git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD)" = 0 && echo "branch is current and backed up"
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 2b frontend foundation: builder shell, draft store, dates and scripture refs" \
  --body-file "<scratch>/slice2b-pr-body.md"
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

**Expected:** `run <id>`; `backend: success`, `backend-postgres: success`, `frontend: success`; frontend `Test Files  49 passed (49)`, `Tests  299 passed (299)`, `✓ Compiled successfully` and the five `/builder` route lines; backend `971 passed, 9 skipped in …s`; backend-postgres `pg_smoke: OK` and `9 passed, 971 deselected, 1 warning in …s`. If a required job failed on or after 2026-10-19, first check the runner image (`Image: ubuntu-24.04` expected; GitHub moves `ubuntu-latest` then) and report a setup failure on a new image to the owner before changing any 2b file.

- [ ] **Step 13 (agent → OWNER): Report CI and ask to mark the PR ready**

Send exactly this, with the values filled in, and wait for a clear yes:

> PR #<N> (<url>) is green (run <run id>): frontend 299 tests in 49 files, build OK with the five builder pages; backend 971 passed, 9 skipped; the Postgres job clean; the Vercel preview built. May I mark it ready for review? Merging stays with you (Task 13).

On the yes:

```bash
gh pr ready <N> -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json isDraft,state --jq '"draft=\(.isDraft) \(.state)"'
```

**Expected:** `✓ Pull request bbrown62450/church#<N> is marked as "ready for review"`, then `draft=false OPEN`. Tell the owner in one line: "PR #<N> is ready for review. Next: Task 13, the merge on your yes, then a two-minute look on your phone and desktop."

- [ ] **Step 14 (agent): Fix any failure in its owning task**

Read the failure (for CI: `gh run view <run-id> -R bbrown62450/church --log-failed | tail -80`), reproduce it locally, and fix it in the task that owns it:

| Failing check or test | Owning task |
|---|---|
| `dates.test.ts`, `dates.guard.test.ts` (or a new offender it names), `next_sunday.json`, the zod lines | T1 |
| `scripture-refs.test.ts` | T2 (fix the port, never the shared fixture) |
| `draft/schema.test.ts`, `draft/migrate.test.ts`, `lib/api/types.ts`, the `churchProfile`/`testDraft` builders | T3 |
| `draft/readings.test.ts`, the `lectionary` builder | T4 |
| `draft/status.test.ts`, `draft/mapping.test.ts`, `draft/fingerprint.test.ts`, the `SHIPPED_STEPS` line | T5 |
| `draft/store.test.ts`, `storage.test.ts`, the storage gate | T6 |
| `draft/context.test.tsx`, `draft/prune.test.ts`, `signed-in-layout.test.tsx` | T7 |
| `use-keyboard-open.test.tsx`, `sheet.tsx`/`badge.tsx` lint or types | T8 |
| `builder-shell.test.tsx`, the builder routes in the build, the client-component gate, the "Available soon" count | T9 |
| `church-layout.test.tsx`, `app-header.test.tsx`, `church-switch.test.tsx`, the old-app gate | T10 |
| the spec or F text, `test_slice1_docs.py` | T11 |
| a flaky run in Step 2 | the task owning the test: fake only `Date` for the calendar, await the UI with `findBy`/`waitFor`, never sleep |
| any other existing test, the backend suite, the Vercel preview only | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2–8; commit with the subject `Fix: <what> (Task <n>, slice 2b final verification)` and the trailer; have that task re-reviewed; push with `git push origin claude/slice-2-plan-4q33le` (a backup before Step 10; after it, covered by the owner's first yes); after Step 10, repeat Steps 11–12 and send Step 13's message with the new run. An infrastructure failure with no test output gets one `gh run rerun <run-id> -R bbrown62450/church --failed` first.

Expected counts after this task: frontend `299 passed` in 49 files (CI the same); backend `971 passed, 9 skipped` (CI `backend-postgres`: `9 passed, 971 deselected, 1 warning`). No commit unless Step 14 needed a fix.

### Task 13: Merge and after (OWNER + agent): the merge, the deploy, a short look on phone and desktop, the slice 2b record (S AC11, AC17 deployed halves; F acceptance 11; owner decisions 2, 3; owner answers Q3, Q4)

2b changes no backend code, no migration and no Python requirement, so the merge's Railway deploy builds the same API and its pre-deploy `alembic upgrade head` finds the database at head (`0004_invites_reusable`) and runs nothing; no Railway, Supabase or branch-protection setting changes. The Vercel production deploy is the one that matters: after it, every signed-in member lands on the builder. Merges never reach https://liturgy-frozen.streamlit.app/ (owner decision 2). Owner answer Q4: automated tests plus a short look, so the owner steps are three, each a minute or two, given **one at a time** (give one OWNER step, wait for the owner's report or "next", then give the next). The agent writes each result, with its date, into `<scratch>/slice2b-t13-results.md` (not committed); Step 7 fills the record from it. Nothing is appended to `docs/manual-verification.md` (clarification 29).

Below, `<N>` is the PR number (T12), `<merge sha>` the merge commit Step 2 prints, `<scratch>` the scratchpad path; write them out literally. Every `gh` command uses `-R bbrown62450/church`. Pushing, merging, and any settings change each need the owner's explicit yes, asked separately. No token, email address or church id is recorded anywhere.

**Files:**
- Merge (Steps 1–2): no file changes.
- Create (not committed): `<scratch>/slice2b-t13-results.md`.
- Modify (records PR, Step 7, on `claude/slice-2-plan-4q33le` fast-forwarded to `origin/main` after the merge): `docs/ops-runbook.md`: insert `### Slice 2b record` right after `### Slice 2a record`'s table (its last row starts `| Follow-ups | Run the liturgy-frozen smoke when convenient.`) and before `## Backups`. A `###` heading, because `test_ops_workflows.py::test_runbook_has_the_seven_sections_in_order` pins the `##` list.
- Test: none new.

**Interfaces:**
- Consumes: PR `<N>` ready and green (T12); the production URLs (owner decision 5).
- Produces: 2b live on `main` and in production; the "Slice 2b record" in `docs/ops-runbook.md`. Later user: 2c's plan (starts from `main` after this).

- [ ] **Step 1 (agent): Check the PR can merge**

```bash
git fetch origin
gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus,headRefOid --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus) \(.headRefOid)"'
git rev-parse HEAD
git rev-list --count HEAD..origin/main
```

**Expected:** `OPEN draft=false MERGEABLE CLEAN <sha>` with `<sha>` equal to `git rev-parse HEAD`; `0`. If `main` moved (count not `0`, or `BEHIND`): merge it as in T12 Step 1, rerun T12 Steps 2–3 (`299 passed` in 49 files, plus any tests the merge brought; `971 passed, 9 skipped`), push with the owner's yes, wait for green checks, and run this step again. `BLOCKED`: a required check is not green; fix it (T12 Step 14). Never merge with `--admin`.

- [ ] **Step 2 (agent → OWNER): Ask to merge, then merge**

Send: "PR #<N> is ready, green and up to date with main. May I merge it with a merge commit? After that every signed-in member lands on the new builder (all steps 'Available soon'); the API and database do not change." On a clear yes:

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
curl -sS -o /dev/null -w "%{http_code} %{redirect_url}\n" --max-time 15 https://worship-service-builder.vercel.app/builder || echo "vercel not reachable from here"
```

**Expected:** `run <id>` and `ci exit 0`; one deployment per environment (a Vercel `Production` one, and Railway's if it reports one) each ending `success` (a `pending` or `in_progress` state: wait a minute and run the loop again); the `curl` line either a redirect to sign-in (`307 https://worship-service-builder.vercel.app/login?next=%2Fbuilder` or similar: the signed-out proxy sends `/builder` to `/login` with `next`) or `vercel not reachable from here` (the container's network policy; then Step 4 is the check). A `failure` state or a `404`: stop and tell the owner (Step R if the site cannot serve).

- [ ] **Step 4 (OWNER, then agent): On your phone**

Send the owner this, and wait for the report:

> On your phone, open https://worship-service-builder.vercel.app (signed in). You should land on **Service Builder**, with "Step 1 of 4 · Date & readings" above four short bars, a card saying **Available soon** / "Keep using the current app for this part.", and a **Next: Hymns** button at the bottom. Tap **Summary**: a panel slides up showing next Sunday's date (for example "Sunday, October 4, 2026") and "Available soon" under Readings, Hymns and Liturgy. Close it. Does it look right, and can you scroll the page without it sliding sideways?

Record the answer (and the phone and browser) in the results file. Anything wrong: note it, ask for a screenshot, and decide with the owner whether it is a follow-up or needs a fix before going on.

- [ ] **Step 5 (OWNER, then agent): Still on your phone**

> Tap **Next: Hymns**, then tap **Builder** in the bar under the header: you should come back to **Hymns** (it remembers the last step). Now tap the **⋮** button next to Summary and choose **New service**: it should go straight back to step 1 without asking anything (there is nothing to lose yet). Did both happen?

Record the answer.

- [ ] **Step 6 (OWNER, then agent): On a computer**

> On a computer, open the same address in a wide window. The summary should sit in a column on the right (no Summary button), the header should show **Builder** next to your account picture, and the step bar should show the four steps by name ("1 Date & readings", "2 Hymns", "3 Liturgy", "4 Review & send") with "Soon" or "Not in archive" under each. Does it?

Record the answer. Optional, only if the owner offers: the liturgy-frozen smoke (sign in, the church and a saved service open). Otherwise record "Not run: 2b changes no backend code or data, and merges never reach liturgy-frozen."

- [ ] **Step 7 (agent): Write the slice 2b record**

```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
git log --oneline -1
grep -n '^### Slice 2a record$\|^| Follow-ups | Run the liturgy-frozen smoke when convenient\|^## Backups$' docs/ops-runbook.md
```

**Expected:** `Fast-forward` (or `Already up to date.`); `<merge sha> Merge pull request #<N> from bbrown62450/claude/slice-2-plan-4q33le`; three lines in that order (the 2a record's heading, its last table row, `## Backups`). Insert, between that last row and `## Backups` (one blank line on each side):

```markdown
### Slice 2b record

Slice 2b (the frontend foundation: the Service Builder shell with all four
steps on "Available soon", the draft kept on each device per member and
church, `/` opening the builder, and the "Builder" nav item) merged as PR
#<N>. No backend, API or database change: production stays at
`0004_invites_reusable` (head). The owner's check was a short look on a phone
and on a computer (owner answer Q4, 2026-09-28). No token, email address or
church id is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` for the merge commit (run <run id>): success. Deployments: <Vercel Production success; Railway success / what the loop showed> | <date> |
| Phone (<phone and browser>) | <Landed on Service Builder, step 1 of 4, the Available soon card and Next: Hymns; Summary showed <date> and Available soon; no sideways scroll. / What the owner saw instead.> | <date> |
| Last step and New service (phone) | <Next: Hymns, then Builder, came back to Hymns; New service went straight to step 1 with no question. / What happened instead.> | <date> |
| Desktop | <The summary column on the right, Builder in the header, the four named steps with Soon and Not in archive. / What the owner saw instead.> | <date> |
| Streamlit smoke on liturgy-frozen | <OK: sign-in, the church and a saved service. / Not run: 2b changes no backend code or data, and merges never reach liturgy-frozen.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Slice 2c: the Date & readings step (and the Saturday vigil question) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two (separated by ` / `). Then:

```bash
sed -n '/^### Slice 2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 2b record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep '\[owner' docs/ops-runbook.md | grep -vc 'An entry marked'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git diff --stat
git add docs/ops-runbook.md
git commit -m "Runbook: slice 2b record (merged; the builder is live; owner's phone and desktop look)" -m "Records the slice 2b merge (PR #<N>): no backend, API or database change;
CI on main and the deployments; the owner's short look on a phone and on
a computer (the builder, the step bar, Summary, the last step, New
service); the liturgy-frozen smoke or why it was skipped. No token, email
or church id is recorded.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

**Expected:** `0`; `0`; `4` (unchanged); `89 passed in <t>s`; ` docs/ops-runbook.md | <n> +`; one commit.

- [ ] **Step 8 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 2b record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes:

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 2b record" \
  --body "Records slice 2b (PR #<N>) in docs/ops-runbook.md → Slice 2b record: the merge and deployments, and the owner's short look on a phone and on a computer. No token, email or church id is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the push; the PR URL; `backend`, `backend-postgres`, `frontend` and the Vercel preview pass. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`, then `gh pr view claude/slice-2-plan-4q33le -R bbrown62450/church --json state --jq .state` → `MERGED`. Report: "Slice 2b is live and recorded: the builder shell, the draft store and the Builder nav item; no backend change; <n> follow-ups. Slice 2c can start from `main`."

- [ ] **Step R (only if the 2b release must come out): Revert**

Use this only when the production site cannot serve or breaks sign-in or the church pages after the merge, and a fix would take too long. 2b wrote nothing to the database and changed no API, so a revert is code only; drafts already stored in members' browsers stay there, harmlessly, until 2b returns. On the owner's yes for each command that leaves this machine:

```bash
git fetch origin
git switch -c claude/revert-slice-2b origin/main
git revert -m 1 --no-commit <merge sha>
git commit -m "Revert slice 2b (PR #<N>): back to the 2a release" -m "The 2b merge <what failed>. 2b changed no backend code, API or database,
so nothing else needs undoing; drafts stored in browsers are left alone.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
git push -u origin claude/revert-slice-2b
gh pr create -R bbrown62450/church --base main --head claude/revert-slice-2b --title "Revert slice 2b" \
  --body "Reverts the slice 2b merge (PR #<N>) because <what failed>. No backend or database change to undo.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr checks claude/revert-slice-2b -R bbrown62450/church --watch
```

**Expected:** Vitest `Test Files  34 passed (34)`, `Tests  221 passed (221)` (if anything else merged after 2b, it differs by exactly those tests); every check passes. Merge on the owner's yes, then the owner checks that the site signs in and shows the old home page. Record the revert as a row of the slice 2b record (or its own records PR if Step 8 already merged).

Expected counts after this task: frontend `299 passed` in 49 files on `main`; backend `971 passed, 9 skipped` (CI `backend-postgres`: `9 passed, 971 deselected, 1 warning`). The records PR adds no test.

---


## Lessons carried from the 2a build (P2a "Build notes")

- **The container restarts.** Uncommitted work can be lost: commit as soon as a task's checks pass, and back the branch up with `git push origin claude/slice-2-plan-4q33le` after every task's review (owner answer Q3). If `node_modules` is gone after a restart, `(cd frontend && npm ci)`.
- **The network is filtered.** The npm registry and Google Fonts are reachable; ui.shadcn.com, Railway and the three reading sites are not. No test may need the network (the fake API throws on any unhandled request); T8 plans for the blocked registry (clarification 3), T12 Step 4 for a font fetch failure, and T13 Step 3 for an unreachable Vercel.
- **Grep gates are judged, not obeyed blindly.** A gate that matches may be a false positive (a comment, a test's own fixture text): read the line, and if it is harmless, say why in the task's report rather than bending the code to silence it. The gates in T12 already exclude test files and comments where 2a's did not.
- **Counts are exact.** Every task states its cumulative count; a drift means a missing or extra test, found before moving on.
- **Owner steps one at a time, in plain words** (P2a Task 15), and every outward action (PR, ready, merge, settings) on its own yes.

## Build notes (2b build)

Left for the controller: what changed while Tasks 1 to 11 were built (as P2a did), with each change's reason and whether the owner saw it. T11 writes any that alter S or F.

## Spec coverage

S = `docs/superpowers/specs/2026-09-25-slice-2-readings-design.md`; F = foundations. Items owned by 2c or later slices are listed so nothing is dropped silently.

### Acceptance criteria

| AC | What it requires | Task(s) |
|---|---|---|
| 1–7, 9, 13 | Backend (lectionary, passages, translations, profile, rate limits, contract, platform) | 2a (done) |
| 8 | `scripture_refs` in Python and TypeScript pass one fixture; the payload never carries a stale pick | T2 (`scripture-refs.test.ts`), T5 (`mapping.test.ts`), T6 (the stored stale-pick case) |
| 10 | Draft persists per user and church, survives refresh, migrates or discards bad data with a backup and a toast, kept across church switch and logout, pruned after 30 days and for churches left | T3 (`migrate`), T6 (`store.test.ts`), T7 (`context.test.tsx`, `prune.test.ts`, the layout test), T10 (`church-switch.test.tsx`). Logout: F §4.2's sign-out never touches drafts (no 2b code clears them) |
| 11 | Four builder routes in the shell with progress, the sticky mobile footer and the desktop summary; no horizontal scroll at 375 px | T9 (`builder-shell.test.tsx`), T12 (build routes), T13 Steps 4 and 6 (deployed) |
| 12 | A fresh draft defaults to the next Sunday in the church's zone; `dates.guard.test.ts` passes | T1, T3 (`schema.test.ts`) |
| 14 | Auto-fill only for `empty`/`lectionary` fields against the latest draft; the banner rule; failed lookups never change fields; 400 ms debounce, no focus moves | T4 (`shouldAutoApply`, `showAvailableBanner`), T6 (the latest-draft recipe test); the lookup, debounce and focus halves are 2c |
| 15 | Set switcher keyed by index; archive fields never overwritten | T4 (`selectedSetIndex`, `shouldAutoApply` for `archive`); the switcher UI is 2c |
| 16 | Passage text for expanded rows only, 3 in flight, exact copy | 2c |
| 17 | `/` → `/builder`; `last_step` written on entry without bumping `updated_at`, `/builder` redirects to it; `AppNav` shows "Builder"; `isPristine` true with a default benediction | T10 (`/`, `AppNav`), T9 (`last_step`), T5 and T6 (`isPristine`, roll-forward) |
| 18 | The manual checklist on production; Streamlit still loads | 2c (the checklist); T13 Steps 4–6 (the owner's short look) and the optional liturgy-frozen smoke |

### S sections

| S item | Task(s) |
|---|---|
| Slice split line 5 (2b) | T1–T10 (clarification 1 for the detail) |
| Scope "Builder shell": routes, `StepHeader`, `StepProgress`, `StepFooter`, `SummaryPanel` + sheet, "Available soon" card, "New service", `/` redirect, `last_step`, `AppNav` | T9, T10 |
| Scope "Draft store": `DraftV1`, load, migrate, validate, persist, tab sync, prune, readings transitions, date side effects, `draftToServicePayload`, `fingerprint` | T3–T7 |
| Scope "Platform": `lib/dates.ts` and its guard test | T1 |
| Hand-offs rows for 3, 4 and 5a (`SHIPPED_STEPS`, `steps.ts`, `summary-panel.tsx`, `StepPlaceholder`, `useDraft`, `freshDraft`, `DRAFT_VERSION`, `migrations`, `fingerprint`, `isDirty`, `isPristine`, `status.ts`, `mapping.ts`, `lib/dates.ts`, `useKeyboardOpen`, `date-effects.ts`) | T1, T3–T9 (the interfaces those slices consume, as named in S) |
| Hand-offs rows for 3 and 5a on passages and `resolveReadings` | T2 (`resolveReadings`, `defaultNtRef`); `passageText` and the passage query are 2c |
| UX "Builder shell" (mobile, desktop, step status, footer labels, placeholders, Still needed, SummaryPanel, New service) | T9 (clarifications 2, 10–12, 15) |
| UX "Step 1 — Date & readings" | 2c |
| "Other states and messages": first render, restore failure, storage unavailable, another tab | T9 (skeleton), T6 and T7 (the three notices and toasts); the translations row is 2c |
| Frontend "Routes and files" | T9, T10 (readings components: 2c) |
| `lib/dates.ts`, `lib/scripture-refs.ts` | T1, T2 |
| Draft store (`schema`, `store`/`context`, `normalizePicks`, `freshDraft`, roll-forward, `prune`, `readings.ts`, `status.ts`, `steps.ts`, `mapping.ts`, `fingerprint.ts`) | T3–T7 |
| `useLectionarySync()`, Queries | 2c |
| Testing "Frontend": `dates`, `dates.guard`, `scripture-refs`, `draft/*`, `builder-shell`, `church-switch` | T1–T10 |
| Testing "Frontend": `use-debounced-value`, `queries/passages`, `readings-step` | 2c |
| Manual checks 1–13 | 2c (clarification 29) |
| Behavior changes 1 (step builder, draft per church) and 2 (default date) | T3, T6, T9, T10 |
| Behavior changes 5, 6, 13, 15 (UI halves), 16, 17 | 2c on T4's transitions |
| Open question 2 (Saturday vigil) | 2c (owner) |

## Questions for the owner (the controller asks these before T1)

- **A. Hand-written `sheet` and `badge` if the component registry stays blocked (clarification 3).** The build container cannot reach the shadcn registry. Recommended: yes, use the plan's hand-written versions (they look and behave the same and can be swapped for generated ones later). If no, you would run one command on your own computer during Task 8.
- **B. Please confirm these small visible choices (recommended: accept all):**
  1. Until 2c, the summary shows next Sunday's date and "Available soon" for Readings, Hymns and Liturgy; the step bar says "Soon" for the first three steps and "Not in archive" for Review; Review's "Still needed" list stays hidden (clarification 2).
  2. If a browser will not save the draft, the summary's last line reads "Draft not saved on this device · Not in archive" (clarification 11).
  3. A finished step will read "Complete" with a check mark (clarification 12; first seen in 2c).
  4. The "Builder" link shows on church pages only (not on the Join or create page), and the header's content spreads wider on a computer to line up with the builder (clarification 16).
- **C. A short "Slice 2b record" in the runbook after the merge (T13 Steps 7–8), as for 2a?** Recommended: yes (one docs-only PR, two yeses).
