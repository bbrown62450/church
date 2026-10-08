# Slice 6a-3a: Liturgy Prompts, the Service Rubric Page, and Bulletin Settings in Settings

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of slice 6a-3's two PRs (owner's 6a-3 planning answers of 2026-10-07, "all recommended"; binding): **three Settings pages.** After it merges, the Settings sections are **Church**, **Hymns**, **Liturgy**, **Rubric**, **Bulletin**, **Contacts** and **Account** (6a-3b later puts **Prayers** between Liturgy and Rubric). **Liturgy** (`/settings/liturgy`, "Liturgy prompts") shows the instructions the AI follows when it writes the liturgy: the "Overall voice (system prompt)" card first, then "Section prompts" with the placeholder help and the eight section cards; each card is collapsible, shows **Customized** when its text is the church's own, and offers **Reset to default** (unsaved until **Save prompts**); **Reset all to defaults** asks first. **Rubric** (`/settings/rubric`, "Service rubric") shows the two hymn preferences ("Prefer hymns written before", "Prefer familiar hymns") and the eleven checklists the AI follows (three hymn slots, eight prayers), each point a one-line box (Enter adds a point below, at most 12), with **Customized**, **Reset to default** per item, one **Save rubric** that sends only what changed, and a confirmed **Reset all to defaults**; the Opening and Closing cards carry the theme note (answer 5). Every member reads both pages; owners and admins edit them. **Bulletin settings** moves into Settings at `/settings/bulletin`; the old `/bulletin-settings` address forwards there, and the builder's two links point to the new one. Server: `GET`/`PUT /church/liturgy-prompts` (new) and the existing `GET`/`PATCH /rubric`, whose write now runs under the church-row lock with the caller's role re-read and whose answers gain `defaults`. No migration (Alembic head stays `0007_bulletin_images`), no new package or variable, no change to the frozen Streamlit files.

**Architecture:** Backend first. `repos/churches.py`: `_merge_settings` becomes `merge_settings(church_id, patch, *, session=None)` (S "Changed modules"), and `set_church_prompts` and `update_church_rubric` gain a keyword-only `session`, so a usecase can write inside the session that holds the lock (their positional callers, the frozen Streamlit pages among them, are unchanged). `usecases/church_admin.py` gains `get_prompts`/`save_prompts` (slice 4's `liturgy_prompts.clean_prompt_overrides` and `check_template`, imported, never copied) and `get_rubric`/`update_rubric` (`service_rubric`'s validation through `update_church_rubric`), each write in one session that starts with 6a-1's `lock_and_read_actor` and `require_admin_role`. A new `api/routes/church_prompts.py` serves `/church/liturgy-prompts`; `api/routes/rubric.py` calls the usecases; `RubricOut` gains `defaults`. Postgres tests prove the lock. Frontend: the generated types; `lib/settings/prompts.ts` and `lib/settings/rubric.ts` (the forms' pure rules); `lib/queries/liturgy-prompts.ts` and `lib/queries/rubric.ts`; `components/settings/liturgy-prompts-page.tsx`, `checklist-card.tsx` and `rubric-settings-page.tsx` with their routes; `SETTINGS_SECTIONS` in the final order less Prayers; the Bulletin settings page rendered inside the Settings layout at `/settings/bulletin`, a forwarding page at the old address, and the builder's links.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy, pytest; Next 16, React 19, TypeScript 5, Base UI (Collapsible, AlertDialog, Switch), TanStack Query 5, sonner, lucide-react, Vitest 3 with Testing Library.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md`, read with its amendments. **"Amendment 2026-10-07 (later): owner's 6a-3 planning answers"** is binding and wins where the older text differs: (1) two PRs, this is **6a-3a** (Liturgy prompts with `PUT /church/liturgy-prompts`, the Service rubric page over the existing `GET`/`PATCH /rubric`, Bulletin settings moved into Settings); (2) Prayers is 6a-3b's; (3) Bulletin settings moves to `/settings/bulletin`, the old address forwards, the builder's links point to the new one; (4) Liturgy prompts as designed, admins only, the system prompt included, with Reset to default per card and Reset all; (5) Open question 3 answered: keep the opening and closing theme keywords and show the note under those two rubric cards; (6) the final order Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, Account. From S: UX §3 "Liturgy prompts", UX §6 "Service rubric", "Settings nav", "Every page", "Losing a role mid-session", the API rows for `GET`/`PUT /church/liturgy-prompts` and `GET`/`PATCH /rubric`, the Models (`PromptKey`, `LiturgyPromptsIn`, `PromptFieldOut`, `LiturgyPromptsOut`), "Semantics" (PUT /church/liturgy-prompts, Locking and role re-read, PATCH /rubric), "Changed modules" (`repos/churches.py`, `api/routes/rubric.py`, `api/schemas.py`), "Pure helpers" (`prompts.ts`, `rubric.ts`), "Queries and mutations" (`prompts.ts`, `rubric.ts`), Testing (the prompt and rubric cases, the Postgres block, the DOM cases for both pages and the Settings layout) and acceptance 6, 7, 10, 17, 21 and 23.
- The rubric spec `docs/superpowers/specs/2026-09-25-service-rubric-design.md` (the checklists, the limits, `validate_patch`'s rules, the known limit of the theme keywords).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards), §1.5 (errors), §1.7 (the settings lock), §2.2 (layers), §4.4 (keys and invalidation), §4.8 and §4.9 (forms, 44 px, Base UI).
- The model plans `docs/superpowers/plans/2026-10-07-slice-6a2-hymns.md` (its plan review and build review fixes) and `docs/superpowers/plans/2026-10-06-slice-5b1-contacts.md` (its plan review and build review fixes); `docs/superpowers/plans/2026-10-05-slice-6a1-settings-church.md` (`lock_church`, `lock_and_read_actor`, `require_admin_role`, `LeaveGuard`, `rebaseForm`, the Settings shell), whose patterns are reused unchanged. "Lessons carried" below maps each of their review findings to this plan.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `f5bec40` = `origin/main` `00db7c6` (6a-2 merged as PR #56) plus the 6a-2 record `61a2f42` and the 6a-3 amendment `f5bec40`, then this plan's commits; 2026-10-08): backend `1885 passed, 31 skipped`; frontend `874 passed` in 103 files; typecheck and lint clean; Alembic head `0007_bulletin_images` (7 revision files); 4 runbook owner markers. What exists: `liturgy_prompts.py` (`PROMPT_KEYS` = `system` + `SECTION_ORDER`, `default_prompts()`, `PLACEHOLDER_HELP`, `check_template(key, template)` with the pinned reasons, `template_error`, `clean_prompt_overrides(prompts, defaults=None)` with the CRLF rule); `liturgy_config.SECTION_LABELS`; `repos/churches.py` (`lock_church`; `_merge_settings` with its own session; `get_church_prompts`/`set_church_prompts` (no session; the frozen `streamlit_views/settings.py` calls `set_church_prompts(church_id, cleaned)`); `get_church_rubric_overrides`/`get_church_rubric`; `update_church_rubric(church_id, patch)` with its own locked session, used by `api/routes/rubric.py` and by eleven calls in five test files); `service_rubric.py` (`DEFAULT_RUBRIC`, `validate_patch` and its messages, `apply_patch`, `merge_rubric`, `customized_keys`, `HYMN_SLOT_LABELS`, `MAX_ITEMS = 12`, `MAX_ITEM_CHARS = 300`, `MIN_YEAR = 1500`); `GET /rubric` (`require_church`) and `PATCH /rubric` (`require_admin`, `ApiError(422, "invalid_rubric", …)`, no lock and no role re-read in the route; `RubricOut {rubric, customized}`); `usecases/church_admin.py` (`require_admin_role`, `update_profile`) and `usecases/members.lock_and_read_actor`; `prompt_invalid` and `invalid_rubric` already in `domain_errors.ERROR_CODES`; `keys.liturgyPrompts` and `keys.rubric` already in `lib/queries/keys.ts`; the Bulletin settings page at `/bulletin-settings` (`components/bulletin-settings/bulletin-settings-page.tsx`, its own `<main>` and `PageHeader`, a "Back to Review & send" link), linked from the builder's Bulletin step (`bulletin-step.tsx`) and the Printed bulletin card (`printed-card.tsx`), and from `SETTINGS_SECTIONS` as `{ href: "/bulletin-settings", label: "Bulletin" }`; `SETTINGS_SECTIONS` = Church, Hymns, Bulletin, Contacts, Account. **No** prompts route, prompts or rubric page, `defaults` field or `lib/settings/prompts.ts`/`rubric.ts`. `streamlit_tests` (35 tests, still collected) reach `repos.churches` through the frozen pages.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -1`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted, and Vitest's run time after a test name is left out here); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. A time in an expected output is written `<t>`.
- The API changes (T3), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- No new package, no new variable, no migration.
- Branch `claude/slice-2-plan-4q33le`, at `f5bec40` plus this plan's commits (`WIP plan: slice 6a-3a skeleton …` and `Plan: slice 6a-3a (Liturgy prompts, Rubric, Bulletin settings in Settings)`, and any later plan commit), then T1-T10. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1885 → 1922 passed, 31 → 33 skipped; frontend 874 → 911 in 103 → 107 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 15 and has no em dashes (S's lines carry none; the shared default prompts and checklists are existing text and keep their own punctuation, owner question 6); existing copy keeps its own punctuation.
- No church id, email address, token, database URL or real person's name in any doc, commit, test or record. Tests use the fixtures' "Grace" and `@example.com` addresses (the rubric's PR #4 tests keep their `@x.org` ones); no prompt's or checklist's wording from the owner's church is recorded.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.
- Tests never reach the network: no route here calls the AI (prompts and the rubric are read by generation on the server, which these tests never run), and the Postgres tests skip without `TEST_DATABASE_URL`.

### How the file directives below read
As in the 6a-2 and 5b-1 plans: **Create `path`:** the block is the whole new file; **Replace `path`:** the block is the whole file, which already exists and is rewritten (used for `api/routes/rubric.py`, `sections.ts` and the old `/bulletin-settings` route, most of whose lines change); **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:** (a leading or trailing empty line in a block is part of it). Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is moved or deleted.

### Baselines and counts
- Starting baselines: backend **1885 passed, 31 skipped**; frontend **874 passed in 103 files**, typecheck and lint clean; Alembic head **`0007_bulletin_images`** (7 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new tests Vitest counts (an `it.each` row counts as one).

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +11 (`test_church_admin.py`: one test in 6 cases and 5 tests) | 1896 passed, 31 skipped | 0 | 874 in 103 |
  | T2 | +16 (`test_church_admin.py`: one test in 12 cases and 4 tests) | 1912 passed, 31 skipped | 0 | 874 in 103 |
  | T3 | +10 (`test_api_liturgy_prompts.py` 9: one test in 5 cases and 4 tests; `test_api_rubric.py` 1; `test_isolation.py` edited) | 1922 passed, 31 skipped | 0 | 874 in 103 |
  | T4 | +2 skipped (`test_church_admin_postgres.py`, skipped without `TEST_DATABASE_URL`) | 1922 passed, 33 skipped | 0 | 874 in 103 |
  | T5 | 0 | 1922 passed, 33 skipped | +5 (`prompts.test.ts`) | 879 in 104 |
  | T6 | 0 | 1922 passed, 33 skipped | +11 (`liturgy-prompts-page.test.tsx`) | 890 in 105 |
  | T7 | 0 | 1922 passed, 33 skipped | +6 (`rubric.test.ts`) | 896 in 106 |
  | T8 | 0 | 1922 passed, 33 skipped | +11 (`rubric-settings-page.test.tsx`) | 907 in 107 |
  | T9 | 0 | 1922 passed, 33 skipped | +4 (`settings-layout.test.tsx`: three `it.each` rows and one test; four other test files edited) | 911 in 107 |
  | T10 | 0 | 1922 passed, 33 skipped | 0 | 911 in 107 |

- CI `backend-postgres` goes from `31 passed, 1885 deselected` to `33 passed, 1922 deselected` (T4). Locally, without `TEST_DATABASE_URL`, those two tests are among the 33 skipped.

### Layering and code rules (carried)
- `usecases/church_admin.py` imports no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` already lists it); the routes are plain `def`s with no SQL and no try/except (F §2.2 rule 1), each one usecase call; the usecases write through `repos.churches` (no SQL in a usecase). `PATCH /rubric`'s `try/except ValueError` moves out of the route into the usecase.
- Logs carry ids, never a prompt's or a point's text (F §2.5). This PR adds no log line.
- Pages and components never call `apiFetch`: the queries use `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); inputs `text-base md:text-sm` (the kit's `Input` and `Textarea` already are).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it, so S's Streamlit compatibility notes and its manual check 10 do not apply. The frozen files on `main` are not edited, and `streamlit_tests` keep passing.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The 6a-3 planning answers of 2026-10-07** ("all recommended"; binding; S's amendment): (1) two PRs, this is **6a-3a**: Liturgy prompts (UX §3, with `PUT /church/liturgy-prompts`), the Service rubric page (UX §6, over the existing `GET`/`PATCH /rubric`) and Bulletin settings moved into Settings; (2) Prayers is built in 6a-3b; (3) **Bulletin settings moves to `/settings/bulletin`**, the old `/bulletin-settings` address forwards there, and the builder's links point to the new one; (4) **Liturgy prompts as designed, admins only, including the overall voice (system) prompt**, with Reset to default per card and Reset all; (5) **keep the opening and closing theme keywords** and show the note under those two rubric cards; (6) **Settings order once 6a is done: Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, Account**. No em dashes in user-facing copy.
5. **Earlier 6a answers** (binding, carried): admins change the church, the prompts and the rubric; everyone reads (2026-10-05 answer 4); 6a-1 merged as PR #52, 6a-2 as PR #56.

**Later, out of scope:** 6a-3b (Prayers and its voice-profile draft), 6b (People, Danger zone), the ESV key move and the other 6a hand-offs already done or dropped, slice 7.

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Owner questions" (each written as recommended) unless an answer already covers them.

1. **[owner-visible] What 6a-3a ships** (answers 1-6). The Liturgy prompts page and `GET`/`PUT /church/liturgy-prompts`; the Service rubric page over `GET`/`PATCH /rubric`, with the PATCH moved under the church-row lock and `defaults` added to both answers; Bulletin settings at `/settings/bulletin` with the old address forwarding; **Liturgy** and **Rubric** in the Settings nav and **Bulletin** pointing under `/settings`; the Postgres tests; the manual check items. Not here: Prayers (6a-3b), anything of 6b.
2. **[owner-visible] Where the pages sit** (answer 6, less Prayers). `SETTINGS_SECTIONS` becomes **Church**, **Hymns**, **Liturgy** (`/settings/liturgy`), **Rubric** (`/settings/rubric`), **Bulletin** (`/settings/bulletin`), **Contacts**, **Account**; 6a-3b inserts **Prayers** (`/settings/prayers`) after Liturgy. The nav labels are S's ("Liturgy", "Rubric"); the pages' headings are "Liturgy prompts", "Service rubric" and "Bulletin settings" (each an `h2`, as "Church profile" and "Hymns"). On a phone the section nav is a wrapping row of 44 px links: seven wrap to two or three rows at 375 px (T12 Step 6 checks it is easy to use; the horizontal-scroller follow-up is carried, owner question 5).
3. **[owner-visible] The Liturgy prompts page** (S UX §3; answer 4). The heading, then S's intro "These are the instructions the AI follows when it writes your liturgy. Edit any of them to shape the voice; leave a box on its default to use the shared wording."; members first see "Only admins can edit the prompts. You can read them below.". Nine cards in the server's order: **Overall voice (system prompt)** (under its box "Placeholders aren't filled in here; this text is sent as written."), then the small heading **Section prompts** with the server's placeholder help followed by "Use {{ or }} to print a brace." (never in the system card), then the eight sections by their labels. Each card is a collapsible (Base UI Collapsible; a 44 px header with the title and **Customized** while the text in the box would be stored as the church's own: not blank and, read as the server reads it, different from the default); all start closed on a phone and open from `md`. The box grows with its text up to 60 % of the window (`useAutosize`), 8 rows to start for the system prompt and Prayers of the People and 4 otherwise, at most 8,000 characters; members' boxes are read-only. Owners and admins also get **Reset to default** under each box (enabled while the text differs from the default: it puts the default text back, unsaved) and a sticky footer: **Save prompts** (disabled until a save would change what is stored; "Saving…") and, while the church has wording of its own saved, **Reset all to defaults** (owner question 2), which asks "Reset all prompts?", "Your church's custom wording will be removed and the shared defaults used.", **Reset all** (red), **Cancel**. A save sends every card whose cleaned text is the church's own (clarification 5) and toasts "Prompts saved."; Reset all sends `{"prompts": {}}` and toasts "Prompts reset to defaults.". After either, the form shows what the server stored, keeping only text typed while the save ran.
4. **Errors on the prompts page** (S "Errors"; the 6a-2 build review's I1). A 422 whose `fields` names a card (`prompt_invalid`'s `prompts.<key>`, or a Pydantic `prompts.<key>` such as "Too long (max 8000 characters).") opens that card, shows the message under its box (`role="alert"`, `aria-invalid`) and focuses the first such box; nothing is saved and nothing is toasted; typing in the box clears it. A 422 that names no card (an unknown key, `prompts.sermon.[key]`) is toasted with the server's message and the edits stay. A role 403 is toasted and refetches the church profile, so the page turns read-only (S "Losing a role mid-session"); a lost church or a 401 the app already handles. While Reset all runs its confirmation cannot be closed (Escape, a tap outside and **Cancel** are ignored) and **Save prompts** is disabled; a failure closes it (toasted); after a reset, focus goes to the page's heading (the button that opened it is gone).
5. **The prompts on the server** (S API, Models, Semantics → PUT /church/liturgy-prompts). `GET /church/liturgy-prompts` (`require_church`) answers `LiturgyPromptsOut {placeholder_help, can_edit, fields}`: `fields` in `PROMPT_KEYS` order, each `{key, label, default, override, customized}`, `label` "Overall voice" for `system` and `SECTION_LABELS` otherwise, `override` what `clean_prompt_overrides` keeps of the stored overrides (so a stored value blank, equal to its default or under an unknown key reads as not customized: generation's own rule), `can_edit` from the caller's role. `PUT` (`require_admin`; `LiturgyPromptsIn {prompts: {PromptKey: str(8000)}}`, `extra="forbid"`) replaces the overrides in `church_admin.save_prompts`: one session, `lock_and_read_actor`, `require_admin_role`, slice 4's `clean_prompt_overrides` (imported; no copy and no pre-processing), then `check_template(key, text)` for each kept prompt in `PROMPT_KEYS` order (the system prompt only for its length, since it is sent as written); the first failure is 422 `prompt_invalid` "<Label> prompt: <reason>" with `fields["prompts.<key>"]` and nothing is written; then `set_church_prompts(…, session=s)` merges the key (`merge_settings`, every other settings key kept) and the answer is the read. An unknown key, a value over 8,000 characters or a null value is Pydantic's 422 `invalid_request` ("Not a valid value.", "Too long (max 8000 characters)."); `{}` and a missing `prompts` are covered. Control characters are not refused: the settings column is JSON (it stores them) and only the AI reads the prompts.
6. **[owner-visible] The Rubric page** (S UX §6; answer 5). The heading, S's intro ("What makes a good hymn or prayer at your church. The AI follows these checklists when it suggests hymns and writes liturgy. How each prayer is laid out (Leader and People lines, length, “Amen”) stays in Liturgy prompts."), and for members "Only admins can edit the rubric. You can read it below.". **Hymn preferences**: "Prefer hymns written before" (a 44 px box, `inputMode="numeric"`, 4 digits; help "Hymns with older words are suggested first. This is a preference, not a filter: a newer hymn can still be suggested when it fits clearly better, and the builder shows its year.") and "Prefer familiar hymns" (a `Switch`; help "Hymns found in many hymnals are suggested first."), each with **Customized** and **Reset to default** while it differs from the default. Then the heading **Hymns** with the three slot cards ("Opening (Gathering) Hymn", "Response Hymn (after the sermon)", "Closing (Sending) Hymn") and **Prayers** with the eight section cards. Each card is a collapsible (closed on a phone, open from `md`; a card with an error stays open) showing "A good {Label}:" and its points; **Customized** while its cleaned points differ from the default's. For owners and admins each point is a one-line box (`maxLength` 300, growing with its text; "Point {n} of {Label}" to a screen reader): Enter adds an empty point below and moves into it, a typed or pasted line break becomes a space; ✕ ("Remove point {n} from {Label}") removes it and moves focus to the point now in its place, else the one before, else **Add a point**; **Add a point** adds one at the end (disabled at 12, with "A checklist can have at most 12 points."); **Reset to default** puts the default points back, unsaved. Members read the points as a plain list (owner question 3). Under the Opening and Closing cards: "The builder first gathers opening and closing hymns by theme (gathering, praise, sending and similar). This checklist then guides which of them the AI suggests." (answer 5). The sticky footer: **Save rubric** (disabled until something changed and nothing is wrong) and, while `customized` is not empty, **Reset all to defaults** ("Reset the rubric?", "Your church's checklists and preferences go back to the shared defaults.", **Reset all**). A save sends one sparse `PATCH /rubric` (clarification 8) and toasts "Rubric saved."; Reset all sends null for each `customized` item and toasts "Rubric reset to defaults.".
7. **Rubric checks and errors** (S "Validation copy"). Before sending, with the server's words: a card whose points are all blank or removed shows "Keep at least one point, or use Reset to default." (`role="alert"`) and blocks **Save rubric**; a year that is not a whole number from 1500 to this year shows "The preferred year must be between 1500 and {this year}." under the box (`aria-invalid`) and blocks Save; more than 12 points or 300 characters cannot be typed. A server 422 `invalid_rubric` (a pasted control character, for example) shows its message in an `Alert` just above the footer, which takes focus; the edits stay, nothing is toasted, and any edit clears it. A role 403, a lost church, a 401 and the confirmation's rules are as for the prompts (clarification 4).
8. **The rubric's body** (S UX §6, `rubric.ts`). Each checklist's points are cleaned as `service_rubric` cleans them (every run of whitespace one space, trimmed, blank points dropped); only items whose cleaned value differs from the baseline are sent; an item whose cleaned value equals its default is sent as `null` (the church keeps following the defaults); the year as a number; never an empty list. A year change also refreshes every hymn list (`["church", id, "hymns"]`: `newer_than_preferred` follows it, so the builder's picker relabels with no reload).
9. **The rubric on the server** (S Semantics → PATCH /rubric; "Changed modules"). `church_admin.update_rubric(church_id, actor_id, patch)`: one session, `lock_and_read_actor`, `require_admin_role` (a demoted admin's role 403 comes before any check of the patch), then `repos.churches.update_church_rubric(church_id, patch, session=s)` (validate, read the locked row's overrides, a non-dict as `{}`, `apply_patch`, write); a `ValueError` becomes `InvalidInput(message, code="invalid_rubric")`, PR #4's 422 body with no `fields`; the answer is `rubric_out` of what is stored: `{rubric, customized, defaults}` (S's additive `defaults`, the full default rubric, on `GET` too through `church_admin.get_rubric`). The route keeps its path, guards and body (`Body(...)` dict, so a non-object body is still Pydantic's `invalid_request`).
10. **Bulletin settings in Settings** (answer 3). A new route `settings/bulletin/page.tsx` renders the existing `BulletinSettingsPage`, which now renders as a Settings section: an `h2` "Bulletin settings" with its description and **Back to the builder** (`/builder`, which reopens the step the builder was last on: Bulletin or Review & send, the two places that link here) instead of its own `<main>`, `PageHeader` and "Back to Review & send" (owner question 1). The old `bulletin-settings/page.tsx` becomes a forward: `router.replace("/settings/bulletin")` with a skeleton, as `/settings` opens Church. The builder's Bulletin step and the Printed bulletin card link to `/settings/bulletin`; their tests, the Church page's leave-guard test and the page's own tests follow. The form, its rules, `useBulletinSettings` and the API are unchanged.
11. **6a's form rules** (S "Every page"). Both new forms keep a baseline and the current edits and rebase on newer server data (an untouched item takes it, an edited one keeps the edit; the prompts compare cleaned text, the rubric cleaned points), never send an untouched item, re-initialize from the save's answer, and use `LeaveGuard` while a save would change something. A member's view shows what is stored; an admin demoted meanwhile sees the stored values, read-only, once the profile refetch lands.
12. **Locking** (S Semantics → Locking; F §1.7). `repos.churches._merge_settings` becomes `merge_settings(church_id, patch, *, session=None)` (S's rename; its three callers are in the same file); `set_church_prompts(church_id, prompts, *, session=None)` and `update_church_rubric(church_id, patch, *, session=None)` write in the caller's session. Both writes therefore read and write the church row under the lock `lock_and_read_actor` took. T4 proves on Postgres that a profile save, a rubric save and a bulletin settings save wait for a prompts save and every key survives, and that two rubric saves on different checklists keep both (S's four-writer case without 6a-3b's prayer library).
13. **No database change** (no migration). The prompts and the rubric stay in `churches.settings` (`liturgy_prompts`, `rubric`) with the same shapes; nothing is backfilled.
14. **The frozen Streamlit code.** `streamlit_views/settings.py` calls `set_church_prompts(church_id, cleaned)` and `get_church_prompts`, and `app.py` `get_church_rubric`; their signatures only gain keyword-only parameters, so `streamlit_tests` pass unchanged (T1 Step 4).
15. **[owner-visible] Every new user-facing string** (no em dashes; owner question 7). Settings nav: "Liturgy", "Rubric". Liturgy: "Liturgy prompts"; "These are the instructions the AI follows when it writes your liturgy. Edit any of them to shape the voice; leave a box on its default to use the shared wording."; "Only admins can edit the prompts. You can read them below."; "Overall voice (system prompt)"; "Placeholders aren't filled in here; this text is sent as written."; "Section prompts"; "Use {{ or }} to print a brace."; "Customized"; "Reset to default"; "Save prompts"; "Reset all to defaults"; "Reset all prompts?"; "Your church's custom wording will be removed and the shared defaults used."; "Reset all"; "Prompts saved."; "Prompts reset to defaults.". Rubric: "Service rubric"; the intro (clarification 6); "Only admins can edit the rubric. You can read it below."; "Hymn preferences"; "Prefer hymns written before"; its help; "Prefer familiar hymns"; its help; "Hymns"; "Prayers"; "A good {Label}:"; "Add a point"; "A checklist can have at most 12 points."; "Keep at least one point, or use Reset to default."; the theme note; "Save rubric"; "Reset the rubric?"; "Your church's checklists and preferences go back to the shared defaults."; "Rubric saved."; "Rubric reset to defaults."; screen readers: "Point {n} of {Label}", "Remove point {n} from {Label}", "Reset to default: Prefer hymns written before", "Reset to default: Prefer familiar hymns". Bulletin: "Back to the builder". From the server: "Overall voice" (the system prompt's label); "<Label> prompt: <reason>" with slice 4's reasons; the rubric's `service_rubric` messages; "Only church admins can do this.". Reused: "Saving…", "Cancel", "Retry", the skeleton's "Loading", the section labels and the hymn slot titles, "The preferred year must be between 1500 and {year}." (the server's).
16. **Docs.** T10 adds the 6a-3a items 16-23 to `docs/manual-verification.md` → "## Slice 6a" (no new `##` heading, so `test_slice1_docs.py`'s pin is unchanged). The runbook record is T12's (`### Slice 6a-3a record` before `## Backups`, after `### Slice 6a-2 record`).
17. **Deviations from S** (each the lean choice for 6a-3a):
    - S deletes `repos.churches.update_church_rubric` and retargets its tests; the plan keeps it as the one write path, with a keyword-only `session` that `update_rubric` passes, because eleven calls in five test files use it as setup. There is still one write path.
    - S says PR #4's `test_api_rubric.py` "keeps passing unchanged"; it compares whole answers, so its three such assertions (and one in `test_isolation.py`) gain `"defaults": default_rubric()`. Nothing else in them changes.
    - S's `PromptFieldOut.label` for the system prompt is "Overall voice" (S: "Label comes from SECTION_LABELS, or "Overall voice" for system"); the page titles the card "Overall voice (system prompt)" (S UX §3).
    - `GET`'s `override` is what `clean_prompt_overrides` keeps of the stored value (clarification 5), so the page and generation agree on what is customized.
    - **Reset all to defaults** on the prompts page shows only while the church has wording of its own (S says so for the rubric only; owner question 2).
    - Members read the rubric's points as text, not as read-only boxes (owner question 3).
    - Below `md`, while the phone keyboard is open, each page's sticky footer sits after the last card instead (owner question 4).
    - The hymn slot titles live in the client too (`HYMN_SLOT_LABELS` in `lib/settings/rubric.ts`, beside `SECTION_LABELS`), since `GET /rubric` names the slots only by key.
    - The old address forwards in the browser (a client page, as `/settings` does), not with a server redirect.

### Risks
- **Last write wins for the prompts** (S Risk 6). `PUT` replaces all prompts, so two admins saving at once keep the later set; a refetch rebases untouched cards first, which narrows it. Accepted.
- **A prompt the old app saved can fail today's check.** It shows on the page, and the next save names it (422, its card opened) until it is fixed; generation already refuses it the same way (slice 4).
- **The theme keywords** (answer 5): kept, with the note under the Opening and Closing cards.
- **Seven section links on a phone** wrap to more rows (clarification 2).
- **SQLite ignores `FOR UPDATE`.** Only CI's `backend-postgres` proves the lock; T1 and T2 check that each write reads the church row with it in its own session.
- **The shared defaults' punctuation.** The default prompts and checklists are shown as they are (some carry dashes); they are the AI's instructions for every church, not new copy (owner question 6).
- **The old address** shows a skeleton for a moment before Settings → Bulletin opens.

### Lessons carried (the 5b-1 and 6a-2 review fixes)
- Whitespace and case compared the server's way, in one place (5b-1 plan review I2, build review M3): the prompts' `cleanPrompt` and the rubric's `cleanPoints` mirror `clean_prompt_overrides` and `service_rubric`, and the server cleans again.
- One rule for which 422s the form shows, and a toast for the rest (5b-1 plan review I3, 6a-2 build review I1): `promptFieldErrors`, `isInvalidRubric`; T6 "toasts a refusal that names no card".
- A dialog closes or stays deliberately (5b-1 plan review I4, build review M5): the Reset all confirmations ignore every close while their request runs and close on a failure; T6 and T8 hold the request and tap **Cancel** and Escape.
- Focus never drops to the page (5b-1 plan review M2, build review M4; 6a-2 plan review M1): the named card's box after a 422, the server's message after an `invalid_rubric`, the heading after a reset, the next point after a removal.
- Late answers touch only their own form (5b-1 build review M5): per-call callbacks on `mutate`, Save and Reset all disable each other, and a church switch remounts the page.
- The keyboard on a phone (5b-1 plan review M4, 6a-2 clarification 8): the footer goes static below `md` while a text box has focus (`useKeyboardOpen`; T6 checks it); T12 Step 6 checks it on the owner's phone. No bottom sheet here: the only dialogs are confirmations.
- The owner's real data is never at risk in the phone check (6a-2 plan review I2, M7): changes only on a card that is not **Customized**, put back with **Reset to default** and a save in the same step; **Reset all** is never tapped; the record notes which cards were customized, never their wording.
- The member's view is complete (6a-2 plan review M5): both pages are fully readable, with the note, and no control.
- Literal Unicode in code is written as escapes (5b-1 plan review M3): this plan's files hold no U+2028, U+2029, U+FFFE or U+FFFF.
- Frozen callers keep working (5b-1 build review M2): repo signatures only gain keyword-only parameters.

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/api/routes/church_prompts.py` (+ `backend/tests/test_api_liturgy_prompts.py`) | `GET`/`PUT /church/liturgy-prompts` | T3 |
| `frontend/src/lib/settings/prompts.ts` (+ `.test.ts`), `frontend/src/lib/queries/liturgy-prompts.ts` | the prompts form's rules; the read and the save | T5 |
| `frontend/src/components/settings/liturgy-prompts-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx` | the Liturgy prompts page and its route | T6 |
| `frontend/src/lib/settings/rubric.ts` (+ `.test.ts`), `frontend/src/lib/queries/rubric.ts` | the rubric form's rules; the read and the save | T7 |
| `frontend/src/components/settings/checklist-card.tsx`, `rubric-settings-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/rubric/page.tsx` | one checklist card; the Rubric page and its route | T8 |
| `frontend/src/app/(signed-in)/(church)/settings/bulletin/page.tsx` | Settings → Bulletin | T9 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/repos/churches.py`, `backend/usecases/church_admin.py`, `backend/tests/test_church_admin.py` | `merge_settings` and the sessions; `get_prompts`, `save_prompts` (T1); `get_rubric`, `update_rubric` (T2); their tests | T1, T2 |
| `backend/api/routes/rubric.py`, `backend/api/schemas.py`, `backend/api/main.py`, `backend/tests/test_api_rubric.py`, `backend/tests/test_isolation.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | the routes through the usecases; `defaults`; the router; regenerated | T3 |
| `backend/tests/test_church_admin_postgres.py` | the lock on Postgres | T4 |
| `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts` | the type names; `liturgyPrompts()`, `DEFAULT_PROMPTS` (T5), `defaultRubric()`, `rubric()` (T7) | T5, T7 |
| `frontend/src/components/settings/sections.ts`, `settings-layout.test.tsx`, `church-settings-page.test.tsx`, `frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx`, `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx` (+ `.test.tsx`), `frontend/src/components/builder/review/printed-card.tsx`, `review-send-step.test.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx` (+ `.test.tsx`) | the nav; Bulletin under `/settings`, the forward, the links | T9 |
| `docs/manual-verification.md` | the 6a-3a items | T10 |
| `docs/ops-runbook.md` | "### Slice 6a-3a record" (the records PR, after the merge) | T12 |

**Counts in the PR:** 43 paths: 17 added (this plan and the sixteen new code and test files above) and 26 modified (the twenty-three code, test and API paths above, `docs/manual-verification.md`, and the 6a spec (its amendment of 2026-10-07, later) and `docs/ops-runbook.md` (the 6a-2 record), which ride along until merged; the runbook's own T12 change goes in the records PR). **Untouched:** migrations, `db/models.py`, `api/deps.py`, `liturgy_prompts.py`, `liturgy_config.py`, `service_rubric.py`, `usecases/members.py`, `usecases/liturgy.py`, `lib/queries/keys.ts`, `lib/settings/profile.ts`, `components/app/leave-guard.tsx`, the draft schema, `app.py`, `streamlit_views`, `streamlit_tests`.

**Task order and review batch:** T1 → T10, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T11 verifies and opens the draft PR on the owner's yes; T12 merges on the owner's yes, runs the phone check and writes the record.

---

## The server (T1-T4)

### Task 1: The liturgy prompts' read and save, under the church-row lock (S Semantics → PUT /church/liturgy-prompts, Locking; clarifications 5, 12, 14)

**Files:**
- Modify: `backend/tests/test_church_admin.py`, `backend/repos/churches.py`, `backend/usecases/church_admin.py`

- [ ] **Step 1: Write the failing tests**

They pin S's prompt cases: the read lists all nine prompts in order with "Overall voice" for the system prompt, and reports as the church's own only what `clean_prompt_overrides` keeps of what is stored (a junk value, a blank one, one equal to its default with CRLF and spaces, an unknown key); a save keeps only wording that differs from the defaults, normalized, leaves every other settings key as it was, takes braces in the system prompt, and `{}` resets all; each bad section template (S's table plus `!r`) is a 422 `prompt_invalid` "Benediction prompt: <slice 4's reason>" naming `prompts.benediction`, with nothing saved; the first bad prompt in `PROMPT_KEYS` order wins; a demoted admin gets the role 403 and a removed member or a deleted church `no_church_access`, writing nothing; and the save reads and writes the church row under the lock, in one session.

**In `backend/tests/test_church_admin.py`, replace:**

````python
`usecases.church_admin` (slice 6a-1)."""
import pytest

````

**with:**

````python
`usecases.church_admin` (slices 6a-1 and 6a-3a)."""
import pytest

import liturgy_prompts
````

**Append to `backend/tests/test_church_admin.py`:**

````python


# --- Liturgy prompts: get_prompts and save_prompts (slice 6a-3a) ----------------------------------------------

DEFAULTS = liturgy_prompts.default_prompts()
PROMPT_ORDER = ["system", "call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]


def _stored_prompts(world) -> dict:
    return churches.get_church_prompts(world["church"])


def test_the_prompts_read_every_default_and_only_the_churchs_own_wording(world):
    churches.update_church(world["church"], settings={"liturgy_prompts": {
        "benediction": "Go in peace. {occasion}",
        "offertory_prayer": "  " + DEFAULTS["offertory_prayer"] + " \r\n",
        "assurance": "   ",
        "bogus": "x",
    }})
    read = church_admin.get_prompts(world["church"], can_edit=False)
    assert read["placeholder_help"] == liturgy_prompts.PLACEHOLDER_HELP
    assert read["can_edit"] is False
    assert [f["key"] for f in read["fields"]] == PROMPT_ORDER
    assert [f["label"] for f in read["fields"]] == [
        "Overall voice", "Call to Worship", "Opening Prayer", "Prayer of Confession", "Assurance of Pardon",
        "Prayer for Illumination", "Prayers of the People", "Offertory Prayer", "Benediction"]
    assert all(f["default"] == DEFAULTS[f["key"]] for f in read["fields"])
    assert {f["key"]: (f["override"], f["customized"]) for f in read["fields"] if f["override"] is not None} == {
        "benediction": ("Go in peace. {occasion}", True)}
    assert church_admin.get_prompts(world["church"], can_edit=True)["can_edit"] is True
    churches.update_church(world["church"], settings={"liturgy_prompts": ["not", "an", "object"]})
    assert not any(f["customized"] for f in church_admin.get_prompts(world["church"], can_edit=True)["fields"])


def test_a_save_keeps_only_wording_that_differs_from_the_defaults(world):
    churches.update_church(world["church"], settings=EVERY_SETTING)
    read = church_admin.save_prompts(world["church"], world["admin"], {
        "system": DEFAULTS["system"],
        "benediction": "  Go in peace.\r\nServe the Lord.\r\n",
        "assurance": "   ",
        "offertory_prayer": "\r\n " + DEFAULTS["offertory_prayer"] + "\r\n",
        "call_to_worship": "{{Leader}}: Come, {unknown_name}.",
    })
    stored = {"benediction": "Go in peace.\nServe the Lord.", "call_to_worship": "{{Leader}}: Come, {unknown_name}."}
    assert _stored_prompts(world) == stored
    assert read["can_edit"] is True
    assert {f["key"]: f["override"] for f in read["fields"] if f["customized"]} == stored
    assert _church(world)["settings"] == {**EVERY_SETTING, "liturgy_prompts": stored}

    church_admin.save_prompts(world["church"], world["owner"], {"system": "Our {own} voice {."})
    assert _stored_prompts(world) == {"system": "Our {own} voice {."}         # sent as written: braces are fine
    church_admin.save_prompts(world["church"], world["owner"], {})
    assert _stored_prompts(world) == {}
    assert _church(world)["settings"] == {**EVERY_SETTING, "liturgy_prompts": {}}


@pytest.mark.parametrize("template, reason", [
    ("{curly", liturgy_prompts.UNPAIRED_BRACE),
    ("{0}", liturgy_prompts.NO_NAME),
    ("Go }", liturgy_prompts.UNPAIRED_BRACE),
    ('{"a": 1}', liturgy_prompts.NOT_ONE_WORD),
    ("{foo.bar}", liturgy_prompts.NOT_PLAIN_NAME),
    ("{occasion!r}", liturgy_prompts.HAS_SPEC),
])
def test_a_section_template_that_cannot_be_filled_is_named_and_nothing_is_saved(world, template, reason):
    churches.set_church_prompts(world["church"], {"system": "Kept."})
    with pytest.raises(InvalidInput) as bad:
        church_admin.save_prompts(world["church"], world["owner"], {"system": "Changed.", "benediction": template})
    assert (bad.value.code, bad.value.field, bad.value.message) == (
        "prompt_invalid", "prompts.benediction", f"Benediction prompt: {reason}")
    assert _stored_prompts(world) == {"system": "Kept."}


def test_the_first_bad_prompt_in_order_is_named(world):
    with pytest.raises(InvalidInput) as bad:
        church_admin.save_prompts(world["church"], world["owner"],
                                  {"benediction": "{curly", "call_to_worship": "{0}"})
    assert (bad.value.field, bad.value.message) == (
        "prompts.call_to_worship", f"Call to Worship prompt: {liturgy_prompts.NO_NAME}")
    assert church_admin.prompt_label("system") == "Overall voice"


def test_a_demoted_admin_or_a_removed_member_saves_no_prompts(world):
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        church_admin.save_prompts(world["church"], world["admin"], {"benediction": "Go."})
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        church_admin.save_prompts(world["church"], world["member"], {"benediction": "Go."})
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        church_admin.save_prompts(world["church"], world["owner"], {"benediction": "Go."})
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert (s.get(Church, world["church"]).settings or {}) == {}


def test_the_prompts_are_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        church_admin.save_prompts(world["church"], world["owner"], {"benediction": "Go."})
    assert len(writes) == 1
    in_the_write = [locked for session, locked in reads if session is writes[0]]
    assert in_the_write and all(in_the_write)
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py 2>&1 | tail -1`
**Expected** (`church_admin` has no `get_prompts`, `save_prompts` or `prompt_label` yet; the 26 tests of 6a-1 pass):
```
11 failed, 26 passed in <t>s
```

- [ ] **Step 3: Give the repo writes a session and write the usecases**

`merge_settings` is S's public name for `_merge_settings`, now able to run in the caller's session; `set_church_prompts` passes its session on. The frozen Streamlit page calls `set_church_prompts(church_id, cleaned)`, which keeps working.

**In `backend/repos/churches.py`, replace:**

````python
def _merge_settings(church_id, patch: dict) -> None:
    """Shallow-merge `patch` into the church's settings JSON under a row lock
    (reassigns a new dict so SQLAlchemy detects the change)."""
    with session_scope() as session:
        church = lock_church(session, church_id)
        if church is None:
            return
        church.settings = {**(church.settings or {}), **patch}
````

**with:**

````python
def merge_settings(church_id, patch: dict, *, session: Optional[Session] = None) -> None:
    """Shallow-merge `patch` into the church's settings JSON under a row lock
    (reassigns a new dict so SQLAlchemy detects the change). Runs in the
    caller's `session` (a church write that already holds the lock, slice
    6a-3a) or in its own scope."""
    if session is not None:
        _merge_settings(session, church_id, patch)
        return
    with session_scope() as own:
        _merge_settings(own, church_id, patch)


def _merge_settings(session, church_id, patch: dict) -> None:
    church = lock_church(session, church_id)
    if church is None:
        return
    church.settings = {**(church.settings or {}), **patch}
````

**In `backend/repos/churches.py`, replace:**

````python
def set_church_prompts(church_id, prompts: dict) -> None:
    """Store per-church prompt overrides. A blank value for a key means "reset to
    default" — it is dropped, so only real overrides are persisted."""
````

**with:**

````python
def set_church_prompts(church_id, prompts: dict, *, session: Optional[Session] = None) -> None:
    """Store per-church prompt overrides. A blank value for a key means "reset to
    default" — it is dropped, so only real overrides are persisted."""
    # Runs in the caller's `session` (usecases.church_admin.save_prompts, under
    # the church-row lock, slice 6a-3a) or in its own scope.
````

**In `backend/repos/churches.py`, replace:**

````python
    _merge_settings(church_id, {"liturgy_prompts": cleaned})
````

**with:**

````python
    merge_settings(church_id, {"liturgy_prompts": cleaned}, session=session)
````

**In `backend/repos/churches.py`, replace:**

````python
    _merge_settings(church_id, {"bible_translation": translation_id})
````

**with:**

````python
    merge_settings(church_id, {"bible_translation": translation_id})
````

**In `backend/repos/churches.py`, replace:**

````python
    _merge_settings(church_id, {"bulletin": value})
````

**with:**

````python
    merge_settings(church_id, {"bulletin": value})
````

**In `backend/usecases/church_admin.py`, replace:**

````python
(PATCH /church); 6a-2, 6a-3 and 6b add their writes here.
````

**with:**

````python
(PATCH /church); 6a-3a the liturgy prompts (and their read); 6a-3b and 6b
add their writes here.
````

**In `backend/usecases/church_admin.py`, replace:**

````python

import scripture_fetcher
````

**with:**

````python

import liturgy_prompts
import scripture_fetcher
````

**In `backend/usecases/church_admin.py`, replace:**

````python
from domain_errors import Forbidden, InvalidInput
````

**with:**

````python
from domain_errors import Forbidden, InvalidInput
from liturgy_config import SECTION_LABELS
````

**Append to `backend/usecases/church_admin.py`:**

````python


# --- Liturgy prompts: GET and PUT /church/liturgy-prompts (slice 6a-3a; 6a spec UX §3, Semantics) ----------

# The system prompt's name in a message ("Overall voice prompt: …"); the page titles its card
# "Overall voice (system prompt)".
SYSTEM_PROMPT_LABEL = "Overall voice"


def prompt_label(key: str) -> str:
    """A prompt's name: "Overall voice" for the system prompt, else the section's label."""
    return SYSTEM_PROMPT_LABEL if key == "system" else SECTION_LABELS[key]


def get_prompts(church_id: uuid.UUID, *, can_edit: bool) -> dict:
    """GET /church/liturgy-prompts: every prompt in PROMPT_KEYS order (the
    system prompt first, then the sections), each with its default and the
    church's own wording when it has one. What counts as the church's own is
    what clean_prompt_overrides keeps of the stored overrides, the rule a save
    and generation use, so a stored value equal to its default (or blank, or
    under an unknown key) reads as not customized."""
    overrides = liturgy_prompts.clean_prompt_overrides(churches.get_church_prompts(church_id))
    defaults = liturgy_prompts.default_prompts()
    return {
        "placeholder_help": liturgy_prompts.PLACEHOLDER_HELP,
        "can_edit": can_edit,
        "fields": [{"key": key, "label": prompt_label(key), "default": defaults[key],
                    "override": overrides.get(key), "customized": key in overrides}
                   for key in liturgy_prompts.PROMPT_KEYS],
    }


def save_prompts(church_id: uuid.UUID, actor_id: uuid.UUID, prompts: Mapping[str, str]) -> dict:
    """PUT /church/liturgy-prompts (6a spec, Semantics): replace the church's
    prompt overrides, under the church-row lock with the caller's role re-read
    (an admin demoted meanwhile gets the role 403). Cleaning is slice 4's
    liturgy_prompts.clean_prompt_overrides, the one rule (no copy here): CRLF
    read as LF, trimmed, and a blank value or one equal to its default is not
    kept; so {} resets every prompt. Each kept prompt, in PROMPT_KEYS order,
    must pass liturgy_prompts.check_template (the system prompt is sent as
    written, so only its length is checked); the first that fails is a 422
    prompt_invalid "<Label> prompt: <reason>" naming prompts.<key>, and nothing
    is written. Returns the prompts as get_prompts does."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        cleaned = liturgy_prompts.clean_prompt_overrides(prompts)
        for key in liturgy_prompts.PROMPT_KEYS:
            reason = liturgy_prompts.check_template(key, cleaned[key]).message if key in cleaned else None
            if reason is not None:
                raise InvalidInput(f"{prompt_label(key)} prompt: {reason}", code="prompt_invalid",
                                   field=f"prompts.{key}")
        churches.set_church_prompts(church_id, cleaned, session=s)
    return get_prompts(church_id, can_edit=True)
````

- [ ] **Step 4: See them pass, with the repo's and the frozen app's tests, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py backend/tests/test_church_settings.py backend/tests/test_churches_repo.py backend/tests/test_usecase_liturgy.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q streamlit_tests 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
73 passed in <t>s
```
```
35 passed in <t>s
```
```
1896 passed, 31 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_church_admin.py backend/repos/churches.py backend/usecases/church_admin.py
git commit -q -m "Slice 6a-3a: the liturgy prompts' read and save under the church-row lock" -m "usecases.church_admin gains get_prompts (every prompt with its default,
and the church's own wording as clean_prompt_overrides keeps it) and
save_prompts (one session: the lock and the role re-read, slice 4's
clean_prompt_overrides, then check_template for each kept prompt, a
422 prompt_invalid naming the first bad one). repos.churches'
_merge_settings becomes merge_settings with an optional session, and
set_church_prompts passes one on." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1896 passed, 31 skipped`; frontend `874 passed` in 103 files.

### Task 2: The rubric's write under the church-row lock, with its defaults (S Semantics → PATCH /rubric; clarifications 9, 12, 17)

**Files:**
- Modify: `backend/tests/test_church_admin.py`, `backend/repos/churches.py`, `backend/usecases/church_admin.py`

- [ ] **Step 1: Write the failing tests**

They pin S's `update_rubric` cases: each `service_rubric` message comes back as a 422 `invalid_rubric` with that message and no field, and nothing is written; `customized` and `defaults` are right after a change and after a reset, and every other settings key (`liturgy_prompts`, `prayer_library`, `bulletin`, `{"foo": 1}`) survives; a stored rubric that is not an object reads as the defaults and is replaced cleanly; a demoted admin gets the role 403 (before the patch is looked at) and a removed member or a deleted church `no_church_access`, writing nothing; and the write reads and writes the church row under the lock, in one session.

**In `backend/tests/test_church_admin.py`, replace:**

````python
import pytest

import liturgy_prompts
````

**with:**

````python
import datetime

import pytest

import liturgy_prompts
import service_rubric
````

**Append to `backend/tests/test_church_admin.py`:**

````python


# --- The service rubric: get_rubric and update_rubric (slice 6a-3a) ---------------------------------------------

THIS_YEAR = datetime.date.today().year


@pytest.mark.parametrize("patch, message", [
    (["not", "an", "object"], "The rubric update must be an object."),
    ({"hymns": ["x"]}, "'hymns' must be an object of checklists."),
    ({"prayers": {"sermon": ["x"]}}, "Unknown prayers checklist: 'sermon'."),
    ({"hymns": {"closing": []}}, "A checklist must be a non-empty list of points."),
    ({"hymns": {"closing": ["x"] * 13}}, "A checklist can have at most 12 points."),
    ({"hymns": {"closing": ["x", "  "]}}, "Each checklist point must be non-empty text."),
    ({"prayers": {"benediction": ["Go\x07 in peace"]}}, "Checklist points cannot contain control characters."),
    ({"prayers": {"benediction": ["x" * 301]}}, "Each checklist point must be at most 300 characters."),
    ({"prefer_before_year": 1499}, f"The preferred year must be between 1500 and {THIS_YEAR}."),
    ({"prefer_before_year": THIS_YEAR + 1}, f"The preferred year must be between 1500 and {THIS_YEAR}."),
    ({"prefer_familiar": "yes"}, "prefer_familiar must be true or false."),
    ({"prefer_older": True}, "Unknown rubric setting: 'prefer_older'."),
])
def test_a_bad_rubric_patch_is_invalid_rubric_with_its_message_and_writes_nothing(world, patch, message):
    churches.update_church_rubric(world["church"], {"prefer_familiar": False})
    with pytest.raises(InvalidInput) as bad:
        church_admin.update_rubric(world["church"], world["owner"], patch)
    assert (bad.value.code, bad.value.field, bad.value.message) == ("invalid_rubric", None, message)
    assert churches.get_church_rubric_overrides(world["church"]) == {"prefer_familiar": False}


def test_a_rubric_change_and_a_reset_answer_what_is_stored_with_the_defaults(world):
    churches.update_church(world["church"], settings=EVERY_SETTING)
    out = church_admin.update_rubric(world["church"], world["admin"], {
        "prayers": {"benediction": ["  Sends   the people\nout. "]}, "prefer_before_year": 1900})
    assert out["defaults"] == service_rubric.default_rubric()
    assert out["rubric"]["prayers"]["benediction"] == ["Sends the people out."]
    assert (out["rubric"]["prefer_before_year"], out["rubric"]["prefer_familiar"]) == (1900, False)
    assert out["customized"] == ["prayers.benediction", "prefer_before_year", "prefer_familiar"]
    assert church_admin.get_rubric(world["church"]) == out
    assert _church(world)["settings"] == {**EVERY_SETTING, "rubric": {
        "prefer_familiar": False, "prayers": {"benediction": ["Sends the people out."]}, "prefer_before_year": 1900}}

    out = church_admin.update_rubric(world["church"], world["owner"], {
        "prayers": {"benediction": None}, "prefer_before_year": None, "prefer_familiar": None})
    assert out == {"rubric": service_rubric.default_rubric(), "customized": [],
                   "defaults": service_rubric.default_rubric()}
    assert _church(world)["settings"] == {**EVERY_SETTING, "rubric": {}}


def test_a_stored_rubric_that_is_not_an_object_reads_as_the_defaults(world):
    churches.update_church(world["church"], settings={"rubric": ["junk"], "foo": 1})
    assert church_admin.get_rubric(world["church"])["customized"] == []
    out = church_admin.update_rubric(world["church"], world["owner"], {"hymns": {"closing": ["Joyful."]}})
    assert out["customized"] == ["hymns.closing"]
    assert _church(world)["settings"] == {"rubric": {"hymns": {"closing": ["Joyful."]}}, "foo": 1}


def test_a_demoted_admin_or_a_removed_member_changes_no_rubric(world):
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    with pytest.raises(Forbidden) as demoted:
        church_admin.update_rubric(world["church"], world["admin"], {"prefer_familiar": False})
    assert (demoted.value.message, demoted.value.details) == ("Only church admins can do this.", None)
    with pytest.raises(Forbidden):                                  # the role first, before the patch is read
        church_admin.update_rubric(world["church"], world["admin"], {"prefer_before_year": 1})
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        church_admin.update_rubric(world["church"], world["member"], {"prefer_familiar": False})
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    with pytest.raises(Forbidden) as deleted:
        church_admin.update_rubric(world["church"], world["owner"], {"prefer_familiar": False})
    assert deleted.value.details == NO_ACCESS
    with session_scope() as s:
        assert (s.get(Church, world["church"]).settings or {}) == {}


def test_the_rubric_is_read_and_written_under_one_row_lock(world):
    with _record_church_row_access() as (reads, writes):
        church_admin.update_rubric(world["church"], world["owner"], {"prefer_familiar": False})
    assert len(writes) == 1
    in_the_write = [locked for session, locked in reads if session is writes[0]]
    assert in_the_write and all(in_the_write)
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py 2>&1 | tail -1`
**Expected** (`church_admin` has no `get_rubric` or `update_rubric` yet):
```
16 failed, 37 passed in <t>s
```

- [ ] **Step 3: Give `update_church_rubric` a session and write the usecases**

`update_church_rubric` stays the one write path (clarification 17): it gains a keyword-only `session`, so `update_rubric` writes in the session whose lock it already holds. Its other callers (the tests that use it as setup) are unchanged.

**In `backend/repos/churches.py`, replace:**

````python
def update_church_rubric(church_id, patch: dict) -> dict:
````

**with:**

````python
def update_church_rubric(church_id, patch: dict, *, session: Optional[Session] = None) -> dict:
````

**In `backend/repos/churches.py`, replace:**

````python
    """
    cleaned = validate_patch(patch)
    with session_scope() as session:
        church = lock_church(session, church_id)
        settings = dict(church.settings or {}) if church is not None else {}
        stored = settings.get("rubric")
        overrides = apply_patch(stored if isinstance(stored, dict) else {}, cleaned)
        if church is not None:
            church.settings = {**settings, "rubric": overrides}
````

**with:**

````python
    Runs in the caller's `session` (usecases.church_admin.update_rubric, which
    holds the lock already, slice 6a-3a) or in its own scope.
    """
    cleaned = validate_patch(patch)
    if session is not None:
        return _update_church_rubric(session, church_id, cleaned)
    with session_scope() as own:
        return _update_church_rubric(own, church_id, cleaned)


def _update_church_rubric(session, church_id, cleaned: dict) -> dict:
    church = lock_church(session, church_id)
    settings = dict(church.settings or {}) if church is not None else {}
    stored = settings.get("rubric")
    overrides = apply_patch(stored if isinstance(stored, dict) else {}, cleaned)
    if church is not None:
        church.settings = {**settings, "rubric": overrides}
````

**In `backend/usecases/church_admin.py`, replace:**

````python
(PATCH /church); 6a-3a the liturgy prompts (and their read); 6a-3b and 6b
add their writes here.
````

**with:**

````python
(PATCH /church); 6a-3a the liturgy prompts and the rubric (and their
reads); 6a-3b and 6b add their writes here.
````

**In `backend/usecases/church_admin.py`, replace:**

````python
import scripture_fetcher
````

**with:**

````python
import scripture_fetcher
import service_rubric
````

**Append to `backend/usecases/church_admin.py`:**

````python


# --- The service rubric: GET and PATCH /rubric (slice 6a-3a; 6a spec UX §6, Semantics → PATCH /rubric) -------


def rubric_out(overrides: object) -> dict:
    """GET and PATCH /rubric's answer (PR #4's, plus 6a's additive `defaults`):
    the merged rubric, the dotted names of the church's valid overrides, and
    the full default rubric, so the page can offer "Reset to default" and send
    null for an item put back to its default."""
    return {"rubric": service_rubric.merge_rubric(overrides),
            "customized": service_rubric.customized_keys(overrides),
            "defaults": service_rubric.default_rubric()}


def get_rubric(church_id: uuid.UUID) -> dict:
    """GET /rubric (any member)."""
    return rubric_out(churches.get_church_rubric_overrides(church_id))


def update_rubric(church_id: uuid.UUID, actor_id: uuid.UUID, patch: object) -> dict:
    """PATCH /rubric (6a spec, Semantics): one session that takes the
    church-row lock and re-reads the caller's role (lock_and_read_actor, then
    require_admin_role), then repos.churches.update_church_rubric in that
    session: service_rubric.validate_patch (a ValueError is a 422
    invalid_rubric with its message and no field, PR #4's body, and nothing
    is written), the stored overrides read from the locked row (a non-dict as
    {}), apply_patch (null removes an override) and the write. Returns
    rubric_out of what is stored."""
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        require_admin_role(role)
        try:
            churches.update_church_rubric(church_id, patch, session=s)
        except ValueError as exc:
            raise InvalidInput(str(exc), code="invalid_rubric") from None
        overrides = churches.get_church_rubric_overrides(church_id, session=s)
    return rubric_out(overrides)
````

- [ ] **Step 4: See them pass, with the repo's tests and the rubric's API tests, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin.py backend/tests/test_church_settings.py backend/tests/test_churches_repo.py backend/tests/test_api_rubric.py backend/tests/test_api_hymns.py backend/tests/test_api_hymn_suggestions.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected** (the route still calls the repo directly until T3, so PR #4's API tests pass as they are):
```
114 passed, 1 skipped in <t>s
```
```
1912 passed, 31 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_church_admin.py backend/repos/churches.py backend/usecases/church_admin.py
git commit -q -m "Slice 6a-3a: the rubric's write under the church-row lock, with its defaults" -m "usecases.church_admin gains get_rubric and update_rubric: one session
that takes the lock and re-reads the caller's role, then
repos.churches.update_church_rubric in that session (it gains an
optional session); a ValueError is a 422 invalid_rubric with its message
and no field. Both answer the merged rubric, the customized names and
the full defaults." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1912 passed, 31 skipped`; frontend `874 passed` in 103 files.

### Task 3: `GET`/`PUT /church/liturgy-prompts`, and `/rubric` through the usecases (S API, Models; clarifications 5, 9, 17)

**Files:**
- Create: `backend/tests/test_api_liturgy_prompts.py`, `backend/api/routes/church_prompts.py`
- Modify: `backend/tests/test_api_rubric.py`, `backend/tests/test_isolation.py`, `backend/api/routes/rubric.py` (rewritten), `backend/api/schemas.py`, `backend/api/main.py`, `frontend/src/lib/api/openapi.json` and `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

`test_api_liturgy_prompts.py` pins the API rows over HTTP: a member reads all nine prompts (`can_edit: false`; an admin `true`) and gets the role 403 on `PUT`, including `{"prompts": {}}`; an admin's save keeps only what differs from the defaults (S's "Prompt cleaning through the API" case: the default re-sent with CRLF and spaces is not stored, a blank is not stored, a changed value is stored trimmed with LF, and a following `GET` matches); `{"prompts": {}}` resets all; a bad template is 422 `prompt_invalid` with `fields["prompts.benediction"]` and nothing saved; an unknown key, a value over 8,000 characters, a null value, an extra field and a missing `prompts` are 422 `invalid_request` with Pydantic's messages; and both routes are church-isolated. It also ports `streamlit_tests/test_settings_prompts_translation.py`'s prompt assertions (a member cannot save prompts or reset them; a save with the default system prompt and a changed Benediction stores only the Benediction; `{}` stores `{}`). `test_api_rubric.py`'s whole-answer assertions and `test_isolation.py`'s gain `defaults`, and one new test checks both answers carry it.

**Create `backend/tests/test_api_liturgy_prompts.py`:**

````python
"""GET and PUT /church/liturgy-prompts over HTTP (6a spec, API rows; slice
6a-3a): every member reads the prompts, owners and admins replace them; the
cleaning is generation's own (`clean_prompt_overrides`), a bad section
template is a 422 naming it, and the routes are church-isolated. Ports
`streamlit_tests/test_settings_prompts_translation.py`'s prompt assertions
(F §5.1)."""
import pytest

import liturgy_prompts
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
ADMIN = "admin@example.com"
MEMBER = "member@example.com"
PATH = "/church/liturgy-prompts"
DEFAULTS = liturgy_prompts.default_prompts()


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=ADMIN), cid, "admin")
    add_membership(make_user(email=MEMBER), cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _overrides(body) -> dict:
    return {f["key"]: f["override"] for f in body["fields"] if f["customized"]}


def test_a_member_reads_every_prompt_and_may_not_change_them(client, church):
    r = client.get(PATH, headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["can_edit"] is False
    assert body["placeholder_help"] == liturgy_prompts.PLACEHOLDER_HELP
    assert body["fields"][0] == {"key": "system", "label": "Overall voice", "default": DEFAULTS["system"],
                                 "override": None, "customized": False}
    assert [f["key"] for f in body["fields"]] == liturgy_prompts.PROMPT_KEYS
    assert client.get(PATH, headers=church_headers(ADMIN, church)).json()["can_edit"] is True
    for payload in ({"prompts": {"benediction": "Go in peace."}}, {"prompts": {}}):
        r = client.put(PATH, json=payload, headers=church_headers(MEMBER, church))
        assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": "Only church admins can do this."})
    assert churches.get_church_prompts(church) == {}


def test_an_admin_saves_only_what_differs_from_the_defaults_and_resets_all(client, church):
    h = church_headers(ADMIN, church)
    r = client.put(PATH, json={"prompts": {
        "system": DEFAULTS["system"],
        "benediction": "  Go in peace.\r\nServe the Lord.\r\n",
        "offertory_prayer": "\r\n " + DEFAULTS["offertory_prayer"] + " \r\n",
        "assurance": "   ",
    }}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["can_edit"] is True
    assert _overrides(r.json()) == {"benediction": "Go in peace.\nServe the Lord."}
    assert client.get(PATH, headers=church_headers(MEMBER, church)).json()["fields"] == r.json()["fields"]
    assert churches.get_church_prompts(church) == {"benediction": "Go in peace.\nServe the Lord."}

    r = client.put(PATH, json={"prompts": {}}, headers=church_headers(OWNER, church))
    assert r.status_code == 200
    assert _overrides(r.json()) == {}
    assert churches.get_church_prompts(church) == {}


def test_a_bad_template_is_a_422_naming_its_prompt_and_nothing_is_saved(client, church):
    h = church_headers(OWNER, church)
    r = client.put(PATH, json={"prompts": {"system": "Changed.", "benediction": "Go in peace {"}}, headers=h)
    assert r.status_code == 422
    assert _error(r) == {
        "code": "prompt_invalid",
        "message": "Benediction prompt: It has a { or } without a partner. Use {{ or }} to print a brace.",
        "fields": {"prompts.benediction": "Benediction prompt: It has a { or } without a partner. "
                                          "Use {{ or }} to print a brace."},
    }
    assert churches.get_church_prompts(church) == {}


@pytest.mark.parametrize("payload, fields", [
    ({"prompts": {"sermon": "Preach."}}, {"prompts.sermon.[key]": "Not a valid value."}),
    ({"prompts": {"benediction": "x" * 8001}}, {"prompts.benediction": "Too long (max 8000 characters)."}),
    ({"prompts": {"benediction": None}}, {"prompts.benediction": "Not a valid value."}),
    ({"prompts": {}, "church_id": "elsewhere"}, {"church_id": "Not a valid value."}),
    ({}, {"prompts": "Required."}),
])
def test_an_unknown_key_a_long_prompt_or_an_extra_field_is_invalid_request(client, church, payload, fields):
    r = client.put(PATH, json=payload, headers=church_headers(OWNER, church))
    assert r.status_code == 422
    assert _error(r) == {"code": "invalid_request", "message": "The request was not valid.", "fields": fields}


def test_the_prompt_routes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    assert_church_isolated(client, "GET", PATH, world=world)
    assert_church_isolated(client, "PUT", PATH, world=world, json={"prompts": {"benediction": "Go."}})
    assert churches.get_church_prompts(world.church_b) == {}
    assert churches.get_church_prompts(world.church_a) == {"benediction": "Go."}
````

**In `backend/tests/test_api_rubric.py`, replace:**

````python
    assert r.status_code == 200
    assert r.json() == {"rubric": default_rubric(), "customized": []}

````

**with:**

````python
    assert r.status_code == 200
    assert r.json() == {"rubric": default_rubric(), "customized": [], "defaults": default_rubric()}

````

**In `backend/tests/test_api_rubric.py`, replace:**

````python
    r = client.patch("/rubric", json={"hymns": {"closing": None}}, headers=h)
    assert r.json() == {"rubric": default_rubric(), "customized": []}

````

**with:**

````python
    r = client.patch("/rubric", json={"hymns": {"closing": None}}, headers=h)
    assert r.json() == {"rubric": default_rubric(), "customized": [], "defaults": default_rubric()}

````

**In `backend/tests/test_api_rubric.py`, replace:**

````python
    assert r.json() == {"rubric": default_rubric(), "customized": []}
````

**with:**

````python
    assert r.json() == {"rubric": default_rubric(), "customized": [], "defaults": default_rubric()}


def test_both_answers_carry_the_defaults_slice_6a3a(client, church):
    h = _headers("owner@x.org", church)
    body = client.patch("/rubric", json={"prayers": {"benediction": ["Sends the people out."]}}, headers=h).json()
    assert body["defaults"] == default_rubric()
    assert body["rubric"]["prayers"]["benediction"] == ["Sends the people out."]
    assert client.get("/rubric", headers=_headers("member@x.org", church)).json() == body
````

**In `backend/tests/test_isolation.py`, replace:**

````python
    assert b.json() == {"rubric": default_rubric(), "customized": []}
````

**with:**

````python
    assert b.json() == {"rubric": default_rubric(), "customized": [], "defaults": default_rubric()}
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_liturgy_prompts.py backend/tests/test_api_rubric.py backend/tests/test_isolation.py 2>&1 | tail -1`
**Expected** (no route answers `/church/liturgy-prompts` yet, and `/rubric`'s answers have no `defaults`):
```
14 failed, 7 passed in <t>s
```

- [ ] **Step 3: Write the routes**

**Create `backend/api/routes/church_prompts.py`:**

````python
"""GET and PUT /church/liturgy-prompts (6a spec, API; slice 6a-3a): the
church's liturgy prompts, the "Overall voice" (system) prompt and one per
section.

Every member reads them (`require_church`; `can_edit` says whether the caller
may change them); owners and admins replace them (`require_admin`, then the
role re-read under the church-row lock in usecases.church_admin.save_prompts).
A prompt left out, blank or equal to its default goes back to the default, so
`{"prompts": {}}` is Reset all. Plain `def` routes that each make one usecase
call (F §2.2 rule 1), with no SQL and no try/except.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from tenancy import is_admin
from usecases import church_admin

router = APIRouter()

PromptKey = Literal["system", "call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                    "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction"]


class LiturgyPromptsIn(BaseModel):
    """The church's own wording, whole: a key left out goes back to its default."""

    model_config = ConfigDict(extra="forbid")

    prompts: dict[PromptKey, Annotated[str, Field(max_length=8000)]]


class PromptFieldOut(BaseModel):
    key: PromptKey
    label: str = Field(description='"Overall voice" for the system prompt, else the section\'s label')
    default: str
    override: Optional[str] = Field(description="the church's own wording, or null when it uses the default")
    customized: bool = Field(description="override is not null")


class LiturgyPromptsOut(BaseModel):
    placeholder_help: str = Field(description="the placeholders a section prompt may use (liturgy_prompts.PLACEHOLDER_HELP)")
    can_edit: bool = Field(description="the caller is an owner or admin")
    fields: list[PromptFieldOut] = Field(description="the system prompt first, then the sections in order")


@router.get("/church/liturgy-prompts", response_model=LiturgyPromptsOut,
            responses=error_responses(401, 403, 422, 503))
def read_prompts(church: ActiveChurch = Depends(require_church)) -> LiturgyPromptsOut:
    return LiturgyPromptsOut(**church_admin.get_prompts(church.id, can_edit=is_admin(church.role)))


@router.put("/church/liturgy-prompts", response_model=LiturgyPromptsOut,
            responses=error_responses(401, 403, 422, 503))
def save_prompts(payload: LiturgyPromptsIn, church: ActiveChurch = Depends(require_admin),
                 user: CurrentUser = Depends(get_current_user)) -> LiturgyPromptsOut:
    return LiturgyPromptsOut(**church_admin.save_prompts(church.id, user.id, payload.prompts))
````

**Replace `backend/api/routes/rubric.py`:**

````python
"""The church's service rubric: any member reads it; admins change it.

PATCH takes 6a's locking rule (slice 6a-3a; 6a spec, Semantics → PATCH
/rubric): usecases.church_admin.update_rubric takes the church-row lock and
re-reads the caller's role under it, so an admin demoted after require_admin
ran gets the role 403. Both answers carry the additive `defaults`.
"""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.schemas import RubricOut
from usecases import church_admin

router = APIRouter()


@router.get("/rubric", response_model=RubricOut, responses=error_responses(401, 403, 422, 503))
def read_rubric(church: ActiveChurch = Depends(require_church)) -> RubricOut:
    return RubricOut(**church_admin.get_rubric(church.id))


@router.patch("/rubric", response_model=RubricOut, responses=error_responses(401, 403, 422, 503))
def change_rubric(
    patch: Dict[str, Any] = Body(...),
    church: ActiveChurch = Depends(require_admin),
    user: CurrentUser = Depends(get_current_user),
) -> RubricOut:
    """Sparse update: send only what changes; null resets an item to its default."""
    return RubricOut(**church_admin.update_rubric(church.id, user.id, patch))
````

**In `backend/api/schemas.py`, replace:**

````python
    customized: list[str]
````

**with:**

````python
    customized: list[str]
    defaults: RubricModel = Field(description="the shared default rubric (slice 6a-3a, additive): "
                                              "the Rubric page's Reset to default")
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (bulletin_emails, bulletin_images, bulletin_settings, churches, contacts, documents, gmail,
                        health, hymnals, hymns, invites, lectionary, liturgy, liturgy_review, me, reference, rubric,
                        scripture, services)
````

**with:**

````python
from api.routes import (bulletin_emails, bulletin_images, bulletin_settings, church_prompts, churches, contacts,
                        documents, gmail, health, hymnals, hymns, invites, lectionary, liturgy, liturgy_review, me,
                        reference, rubric, scripture, services)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(rubric.router)
````

**with:**

````python
    app.include_router(rubric.router)
    app.include_router(church_prompts.router)
````

- [ ] **Step 4: Regenerate the API files, see the tests pass, and the suites**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git diff --stat -- frontend/src/lib/api | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_api_liturgy_prompts.py backend/tests/test_api_rubric.py backend/tests/test_isolation.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_error_registry.py 2>&1 | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `.venv/bin/python -m pytest -q | tail -1`
**Expected** (the snapshot and the types gain the prompts' path and models and `RubricOut.defaults`; the contract test now matches the live schema; the route-guard allowlists do not change):
```
 2 files changed, 508 insertions(+), 1 deletion(-)
```
```
34 passed in <t>s
```
```
typecheck 0
lint 0
```
```
1922 passed, 31 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_api_liturgy_prompts.py backend/tests/test_api_rubric.py backend/tests/test_isolation.py backend/api/routes/church_prompts.py backend/api/routes/rubric.py backend/api/schemas.py backend/api/main.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 6a-3a: GET and PUT /church/liturgy-prompts; /rubric through the usecases" -m "GET /church/liturgy-prompts (any member, can_edit for owners and
admins) and PUT (owners and admins; the church's own wording, whole, so
{} resets all) over usecases.church_admin. GET and PATCH /rubric call
get_rubric and update_rubric, so the write takes the church-row lock
and re-reads the role; RubricOut gains the additive defaults. The
OpenAPI snapshot and the generated types are regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 31 skipped`; frontend `874 passed` in 103 files.

### Task 4: The prompts' and the rubric's writes wait for the lock on real Postgres (S Testing → Postgres; clarification 12)

**Files:**
- Modify: `backend/tests/test_church_admin_postgres.py`

- [ ] **Step 1: Write the tests**

Two tests beside 6a-1's, in the same held-lock style (a write is held inside the lock by a monkeypatched module attribute it calls after taking the lock; a write that never gets there fails the test after 10 s instead of passing vacuously): while a prompts save holds the lock, a profile save, a rubric save and a bulletin settings save all wait, and afterwards every key is stored (S's four-writer case, less 6a-3b's prayer library); and while one rubric save holds the lock, a second one on another checklist waits and both checklists are kept (S's "Two concurrent `PATCH /rubric` calls on different checklists keep both overrides"). They are `@pytest.mark.postgres` (the module's `pytestmark`), so they skip here and run in CI's `backend-postgres` job.

**In `backend/tests/test_church_admin_postgres.py`, replace:**

````python
slice 6a-1): while a profile save holds the church-row lock, the other
````

**with:**

````python
slice 6a-1; slice 6a-3a adds the prompts and the rubric below): while a
profile save holds the church-row lock, the other
````

**Append to `backend/tests/test_church_admin_postgres.py`:**

````python


# --- slice 6a-3a: the prompts and the rubric take the same lock --------------------------------------------------


def test_the_other_settings_writers_wait_for_a_prompts_save_and_every_key_survives(world, monkeypatch):
    """PUT /church/liturgy-prompts' write (church_admin.save_prompts) holds the
    church-row lock from its role re-read to its commit: a profile save, a
    rubric save and a bulletin settings save started meanwhile wait, and every
    key is there afterwards (6a spec, Testing → Postgres, without 6a-3b's
    prayer library)."""
    owner, church_id = world
    inside, release = threading.Event(), threading.Event()
    clean = church_admin.liturgy_prompts.clean_prompt_overrides

    def held(*args, **kwargs):
        inside.set()                   # save_prompts holds the church-row lock here
        assert release.wait(10), "the test never released the prompts save"
        return clean(*args, **kwargs)

    monkeypatch.setattr(church_admin.liturgy_prompts, "clean_prompt_overrides", held)
    with ThreadPoolExecutor(4) as pool:
        prompts = pool.submit(church_admin.save_prompts, church_id, owner, {"benediction": "Go."})
        assert inside.wait(10), "the prompts save never took the lock"
        profile = pool.submit(church_admin.update_profile, church_id, owner, {"bible_translation": "kjv"})
        rubric = pool.submit(church_admin.update_rubric, church_id, owner, {"prefer_before_year": 1900})
        bulletin = pool.submit(churches.set_bulletin_settings, church_id, {"phone": "555-0100"})
        threading.Event().wait(1)      # time for any writer to finish if nothing held it
        waiting = [f for f in (profile, rubric, bulletin) if not f.done()]
        assert len(waiting) == 3, "the other settings writers did not wait for the lock"
        release.set()
        for future in (prompts, profile, rubric, bulletin):
            future.result(10)
    settings = churches.get_church(church_id)["settings"]
    assert settings["liturgy_prompts"] == {"benediction": "Go."}
    assert settings["bible_translation"] == "kjv"
    assert settings["rubric"] == {"prefer_before_year": 1900}
    assert settings["bulletin"] == {"phone": "555-0100"}


def test_two_rubric_saves_at_once_keep_both_checklists(world, monkeypatch):
    """Two PATCH /rubric writes on different checklists (church_admin.update_rubric):
    the second reads the stored overrides only after the first commits, so
    neither checklist is lost."""
    owner, church_id = world
    inside, release = threading.Event(), threading.Event()
    write = churches.update_church_rubric
    calls = []

    def held(church, patch, **kwargs):
        calls.append(patch)
        if len(calls) == 1:
            inside.set()               # the first update_rubric holds the church-row lock here
            assert release.wait(10), "the test never released the first rubric save"
        return write(church, patch, **kwargs)

    monkeypatch.setattr(church_admin.churches, "update_church_rubric", held)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(church_admin.update_rubric, church_id, owner, {"hymns": {"closing": ["Joyful."]}})
        assert inside.wait(10), "the first rubric save never took the lock"
        second = pool.submit(church_admin.update_rubric, church_id, owner,
                             {"prayers": {"benediction": ["Sends the people out."]}})
        threading.Event().wait(1)
        assert not second.done(), "the second rubric save did not wait for the lock"
        release.set()
        first.result(10)
        out = second.result(10)
    assert out["customized"] == ["hymns.closing", "prayers.benediction"]
    assert churches.get_church_rubric_overrides(church_id) == {
        "hymns": {"closing": ["Joyful."]}, "prayers": {"benediction": ["Sends the people out."]}}
````

- [ ] **Step 2: See them skip here**

Run: `.venv/bin/python -m pytest -q backend/tests/test_church_admin_postgres.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected** (no `TEST_DATABASE_URL`; on a throwaway Postgres they pass, and fail with the lock taken out: Build notes):
```
3 skipped in <t>s
```
```
1922 passed, 33 skipped in <t>s
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_church_admin_postgres.py
git commit -q -m "Slice 6a-3a: the prompts and rubric writes wait for the lock on Postgres" -m "While a prompts save holds the church-row lock, a profile save, a
rubric save and a bulletin settings save wait for it and every key
survives; while one rubric save holds it, a second on another
checklist waits and both are kept. Skipped without TEST_DATABASE_URL;
CI's backend-postgres job runs them." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `874 passed` in 103 files. CI's `backend-postgres`: `33 passed, 1922 deselected`.

## The app (T5-T9)

### Task 5: The prompts form's rules, the types and the queries (S "Pure helpers" `prompts.ts`, "Queries and mutations"; clarifications 3-5, 11)

**Files:**
- Create: `frontend/src/lib/settings/prompts.test.ts`, `frontend/src/lib/settings/prompts.ts`, `frontend/src/lib/queries/liturgy-prompts.ts`
- Modify: `frontend/src/lib/api/types.ts`, `frontend/src/test/fixtures/index.ts`

- [ ] **Step 1: Write the type names, the test data and the failing tests**

`types.ts` names the generated models (the prompts' and, for T7, the rubric's). The fixtures add short stand-ins for the nine default prompts and `liturgyPrompts(overrides, extra)`, an admin's `GET` answer. `prompts.test.ts` pins S's `promptsPayload` cases (a default-equal or blank card dropped, a whitespace-only difference dropped, CRLF read as LF), the start values, `isCustomized`, `hasPromptChanges`, the rebase, and which 422s name a card.

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/**
 * Settings → Liturgy prompts (slice 6a-3a): `GET`/`PUT /church/liturgy-prompts`'s
 * answer (`placeholder_help`, `can_edit` and every prompt, the system prompt
 * first), one prompt (`key`, `label`, `default`, the church's `override` or
 * null, `customized`), its key, and `PUT`'s body (the church's own wording,
 * whole: a key left out goes back to its default).
 */
export type LiturgyPrompts = components["schemas"]["LiturgyPromptsOut"];
export type PromptField = components["schemas"]["PromptFieldOut"];
export type PromptKey = PromptField["key"];
export type LiturgyPromptsBody = components["schemas"]["LiturgyPromptsIn"];

/**
 * Settings → Rubric (slice 6a-3a): `GET`/`PATCH /rubric`'s answer (the merged
 * `rubric`, the dotted names of the church's overrides in `customized`, and the
 * shared `defaults`) and one whole rubric.
 */
export type Rubric = components["schemas"]["RubricOut"];
export type RubricValues = components["schemas"]["RubricModel"];
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  LiturgySection,
  OutlineItem,
  PreviousBulletin,
````

**with:**

````ts
  LiturgyPrompts,
  LiturgySection,
  OutlineItem,
  PreviousBulletin,
  PromptKey,
````

**Append to `frontend/src/test/fixtures/index.ts`:**

````ts

// --- slice 6a-3a: Settings → Liturgy prompts and Rubric ------------------------------------------------

/** Short stand-ins for the shared default prompts, one per key (the real ones are long). */
export const DEFAULT_PROMPTS: Readonly<Record<PromptKey, string>> = {
  system: "You are a thoughtful worship writer.",
  call_to_worship: "Write a Call to Worship for: {occasion}.",
  opening_prayer: "Write an Opening Prayer for: {occasion}.",
  prayer_of_confession: "Write a Prayer of Confession for: {occasion}.",
  assurance: "Write the Assurance of Pardon for: {occasion}.",
  prayer_for_illumination: "Write a Prayer for Illumination for: {occasion}.",
  prayers_of_the_people: "Write Prayers of the People for: {occasion}. Hymns: {hymns}.",
  offertory_prayer: "Write an Offertory Prayer for: {occasion}.",
  benediction: "Write a Benediction for: {occasion}.",
};

/** `GET /church/liturgy-prompts` for an admin: every prompt on its default, except `overrides`. */
export function liturgyPrompts(
  overrides: Partial<Record<PromptKey, string>> = {},
  extra: Partial<LiturgyPrompts> = {},
): LiturgyPrompts {
  return {
    placeholder_help:
      "Placeholders you can use: {occasion}, {scriptures}, {opening_hymn}, {hymns}. Unknown placeholders are ignored (they render as blank).",
    can_edit: true,
    fields: (Object.keys(DEFAULT_PROMPTS) as PromptKey[]).map((key) => ({
      key,
      label: key === "system" ? "Overall voice" : SECTION_LABELS[key],
      default: DEFAULT_PROMPTS[key],
      override: overrides[key] ?? null,
      customized: key in overrides,
    })),
    ...extra,
  };
}
````

**Create `frontend/src/lib/settings/prompts.test.ts`:**

````ts
/** Settings → Liturgy prompts' form rules (slice 6a-3a; 6a spec "Pure helpers" `prompts.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { keys } from "@/lib/queries/keys";
import { DEFAULT_PROMPTS, liturgyPrompts } from "@/test/fixtures";

import {
  cleanPrompt,
  hasPromptChanges,
  isCustomized,
  PROMPT_KEYS,
  promptFieldErrors,
  promptsPayload,
  promptValuesFrom,
  rebasePrompts,
} from "./prompts";

const OUT = liturgyPrompts({ benediction: "Go in peace." });
const FIELDS = OUT.fields;
const BENEDICTION = FIELDS.find((f) => f.key === "benediction")!;

describe("Settings → Liturgy prompts' form rules (slice 6a-3a)", () => {
  it("starts each card at the church's own wording, else the default", () => {
    const values = promptValuesFrom(OUT);
    expect(Object.keys(values)).toEqual([...PROMPT_KEYS]);
    expect(values.benediction).toBe("Go in peace.");
    expect(values.system).toBe(DEFAULT_PROMPTS.system);
  });

  it("reads a prompt as the server does: CRLF as LF and trimmed; blank or the default is not the church's own", () => {
    expect(cleanPrompt("  Go in peace.\r\nServe.\r\n ")).toBe("Go in peace.\nServe.");
    expect(isCustomized("Go in peace.", BENEDICTION)).toBe(true);
    expect(isCustomized(`  ${DEFAULT_PROMPTS.benediction}\r\n`, BENEDICTION)).toBe(false);
    expect(isCustomized("   ", BENEDICTION)).toBe(false);
  });

  it("sends only the church's own wording, cleaned; nothing changed is no change", () => {
    const baseline = promptValuesFrom(OUT);
    const current = {
      ...baseline,
      system: ` ${DEFAULT_PROMPTS.system}\r\n`,
      call_to_worship: "  Come, {occasion}.\r\nPraise.  ",
      assurance: "",
      benediction: "Go in peace. ",
    };
    expect(promptsPayload(current, FIELDS)).toEqual({ call_to_worship: "Come, {occasion}.\nPraise.", benediction: "Go in peace." });
    expect(hasPromptChanges(baseline, current, FIELDS)).toBe(true);
    expect(hasPromptChanges(baseline, { ...baseline, benediction: "Go in peace.\r\n", system: ` ${DEFAULT_PROMPTS.system}` }, FIELDS)).toBe(
      false,
    );
    expect(promptsPayload({ ...baseline, benediction: "" }, FIELDS)).toEqual({});
  });

  it("rebases on newer server wording: untouched cards take it, edited ones keep the edit", () => {
    const oldBaseline = promptValuesFrom(OUT);
    const current = { ...oldBaseline, system: "Our own voice.", benediction: "Go in peace. " };
    const next = promptValuesFrom(liturgyPrompts({ benediction: "Go and serve.", offertory_prayer: "Give thanks." }));
    expect(rebasePrompts(oldBaseline, current, next)).toEqual({
      ...next,
      system: "Our own voice.",
    });
  });

  it("finds a 422's messages for the cards, and nothing for a field the form has no card for", () => {
    const named = new ApiError(422, "prompt_invalid", "Benediction prompt: bad.", {
      fields: { "prompts.benediction": "Benediction prompt: bad." },
    });
    expect(promptFieldErrors(named, PROMPT_KEYS)).toEqual({ benediction: "Benediction prompt: bad." });
    const unknown = new ApiError(422, "invalid_request", "The request was not valid.", {
      fields: { "prompts.sermon.[key]": "Not a valid value." },
    });
    expect(promptFieldErrors(unknown, PROMPT_KEYS)).toBeNull();
    expect(promptFieldErrors(new ApiError(403, "forbidden", "Only church admins can do this."), PROMPT_KEYS)).toBeNull();
    expect(keys.liturgyPrompts("c-1")).toEqual(["church", "c-1", "liturgy-prompts"]);
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/settings/prompts.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`lib/settings/prompts.ts` does not exist yet, so the file cannot load):
```
 FAIL  |unit| src/lib/settings/prompts.test.ts [ src/lib/settings/prompts.test.ts ]
      Tests  no tests
```

- [ ] **Step 3: Write the rules and the queries**

**Create `frontend/src/lib/settings/prompts.ts`:**

````ts
/**
 * Settings → Liturgy prompts' form rules (slice 6a-3a; 6a spec "Pure helpers"
 * `prompts.ts`). The form holds one text per prompt; a prompt counts as the
 * church's own only when its text, read as the server reads it
 * (`clean_prompt_overrides`: CRLF as LF, trimmed), is not blank and differs
 * from its default. So a save sends exactly what the server would keep, and a
 * card cleared or set back to its default text goes back to the default.
 */
import { ApiError } from "@/lib/api/client";
import type { LiturgyPrompts, PromptField, PromptKey } from "@/lib/api/types";

import { rebaseForm } from "./profile";

export type PromptValues = Record<PromptKey, string>;
export type PromptErrors = Partial<Record<PromptKey, string>>;

/** Every prompt, in the server's order: the system prompt, then the sections (`liturgy_prompts.PROMPT_KEYS`). */
export const PROMPT_KEYS: readonly PromptKey[] = [
  "system",
  "call_to_worship",
  "opening_prayer",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "prayers_of_the_people",
  "offertory_prayer",
  "benediction",
];

/** The longest prompt the server takes (`PUT`'s `max_length`). */
export const MAX_PROMPT_LENGTH = 8000;

/** A prompt's text as the server compares and stores it: CRLF line ends as LF, trimmed. */
export function cleanPrompt(text: string): string {
  return text.replace(/\r\n/g, "\n").trim();
}

/** The form a read starts at, and its baseline: the church's own wording, else the default. */
export function promptValuesFrom(out: LiturgyPrompts): PromptValues {
  return Object.fromEntries(out.fields.map((f) => [f.key, f.override ?? f.default])) as PromptValues;
}

/** True when this text would be stored as the church's own wording (the card's **Customized** badge). */
export function isCustomized(text: string, field: PromptField): boolean {
  const clean = cleanPrompt(text);
  return clean !== "" && clean !== cleanPrompt(field.default);
}

/** `PUT`'s `prompts`: every prompt whose cleaned text is the church's own, cleaned, in the server's order. */
export function promptsPayload(values: PromptValues, fields: readonly PromptField[]): Partial<PromptValues> {
  const payload: Partial<PromptValues> = {};
  for (const field of fields) {
    if (isCustomized(values[field.key], field)) payload[field.key] = cleanPrompt(values[field.key]);
  }
  return payload;
}

/** True while a save would change what is stored. */
export function hasPromptChanges(baseline: PromptValues, current: PromptValues, fields: readonly PromptField[]): boolean {
  return JSON.stringify(promptsPayload(baseline, fields)) !== JSON.stringify(promptsPayload(current, fields));
}

/**
 * 6a's rebase for the prompts: newer server wording replaces each card the
 * user has not edited (cleaned text still equal to the old baseline's) and
 * each edited card keeps the edit.
 */
export function rebasePrompts(oldBaseline: PromptValues, current: PromptValues, next: PromptValues): PromptValues {
  return rebaseForm(oldBaseline, current, next, (_key, a, b) => cleanPrompt(a) === cleanPrompt(b));
}

/** A failed save's messages for the cards (a 422's `fields` "prompts.<key>"), or null when it names none. */
export function promptFieldErrors(e: unknown, keys: readonly PromptKey[]): PromptErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const found: PromptErrors = {};
  for (const key of keys) {
    const message = e.fields[`prompts.${key}`];
    if (message) found[key] = message;
  }
  return Object.keys(found).length > 0 ? found : null;
}
````

**Create `frontend/src/lib/queries/liturgy-prompts.ts`:**

````ts
/**
 * Settings → Liturgy prompts' queries (slice 6a-3a; 6a spec "Queries and mutations" `prompts.ts`).
 *
 * - `useLiturgyPrompts()`: `GET /church/liturgy-prompts` under
 *   ["church", id, "liturgy-prompts"]; any member.
 * - `useSaveLiturgyPrompts()`: `PUT` the church's own wording, whole (admins);
 *   `{ prompts: {} }` with `reset: true` is Reset all. Success cancels a read
 *   in flight (it may predate the save), caches the answer and toasts "Prompts
 *   saved." or "Prompts reset to defaults.". Generation reads the prompts on
 *   the server each time, so nothing else is refreshed. Not optimistic (F §4.4).
 *
 * Errors: a 401 or a lost church the app already reports. A 422 naming a
 * prompt (`promptFieldErrors`) is the form's to show under that prompt. A role
 * 403 (an admin demoted meanwhile) is toasted and refetches the church profile,
 * so the page turns into the member's view. Anything else is toasted.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { LiturgyPrompts, PromptKey } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { PROMPT_KEYS, promptFieldErrors } from "@/lib/settings/prompts";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const PROMPTS_SAVED = "Prompts saved.";
export const PROMPTS_RESET = "Prompts reset to defaults.";
const PATH = "/church/liturgy-prompts";

export function useLiturgyPrompts(): UseQueryResult<LiturgyPrompts, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<LiturgyPrompts, ApiError>({
    queryKey: keys.liturgyPrompts(church.id),
    queryFn: ({ signal }) => api.church<LiturgyPrompts>(PATH, { signal }),
  });
}

export type SavePrompts = { prompts: Partial<Record<PromptKey, string>>; reset?: boolean };

export function useSaveLiturgyPrompts() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<LiturgyPrompts, ApiError, SavePrompts>({
    mutationFn: ({ prompts }) => api.church<LiturgyPrompts>(PATH, { method: "PUT", json: { prompts } }),
    onSuccess: async (saved, { reset }) => {
      // A read already in flight may predate the save; its answer must not replace what is now stored.
      await queryClient.cancelQueries({ queryKey: keys.liturgyPrompts(church.id) });
      queryClient.setQueryData(keys.liturgyPrompts(church.id), saved);
      toast.success(reset ? PROMPTS_RESET : PROMPTS_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || promptFieldErrors(e, PROMPT_KEYS) !== null) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/lib/settings/prompts.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  5 passed (5)
```
```
typecheck 0
lint 0
```
```
 Test Files  104 passed (104)
      Tests  879 passed (879)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/test/fixtures/index.ts frontend/src/lib/settings/prompts.test.ts frontend/src/lib/settings/prompts.ts frontend/src/lib/queries/liturgy-prompts.ts
git commit -q -m "Slice 6a-3a: the prompts form's rules and queries" -m "lib/settings/prompts.ts reads a prompt as the server does (CRLF as LF,
trimmed): the start values, Customized, the save's body (only the
church's own wording), whether a save would change anything, the
rebase on newer data, and the cards a 422 names.
lib/queries/liturgy-prompts.ts reads and saves the prompts (toasts,
the role 403's profile refetch). The type names for the prompts and the
rubric, and test data." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `879 passed` in 104 files.

### Task 6: The Liturgy prompts page (S UX §3; clarifications 3, 4, 11)

**Files:**
- Create: `frontend/src/components/settings/liturgy-prompts-page.test.tsx`, `frontend/src/components/settings/liturgy-prompts-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx`

- [ ] **Step 1: Write the failing tests**

Rendered inside the Settings layout, as the route is. They pin S's DOM cases for this page: the member's read-only view (the note, the nine titles in order, read-only boxes, the system card's note, the placeholder help with the brace sentence under "Section prompts" and not in the system card, no buttons); every card open from `md`; **Customized** following the text, **Reset to default**, and a save that sends only the church's own wording (with `X-Church-Id`); a 422 `prompt_invalid` that opens, marks and focuses its card even when it was closed, with no toast; a 422 naming no card toasted with the edits kept; **Reset all** confirmed, `PUT {prompts: {}}`, not closable while it runs (Escape and **Cancel** ignored), then the defaults shown and focus on the heading; the rebase; the role 403; the leave guard through the Settings nav; the footer going static while the keyboard is open; and the error state.

**Create `frontend/src/components/settings/liturgy-prompts-page.test.tsx`:**

````tsx
/**
 * Settings → Liturgy prompts (slice 6a-3a; 6a spec UX §3): every member reads
 * the prompts, owners and admins edit, reset and save them. Rendered inside
 * the Settings layout, as the route is, with a Toaster. Below `md` (jsdom's
 * matchMedia never matches) every card starts closed.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import LiturgySettingsRoute from "@/app/(signed-in)/(church)/settings/liturgy/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, PromptKey } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { PROMPTS_RESET, PROMPTS_SAVED } from "@/lib/queries/liturgy-prompts";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, DEFAULT_PROMPTS, liturgyPrompts, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY, BRACE_NOTE, PROMPTS_INTRO, RESET_ALL_TITLE, SYSTEM_NOTE } from "./liturgy-prompts-page";

afterEach(() => {
  toast.dismiss();
});

/** A fake `/church/liturgy-prompts`: `PUT` stores what it is sent, and `GET` answers with it, as the server does. */
function promptsServer(initial: Partial<Record<PromptKey, string>> = {}) {
  let stored = { ...initial };
  return {
    get: () => liturgyPrompts(stored),
    put: (req: RecordedRequest) => {
      stored = { ...(req.body as { prompts: Record<PromptKey, string> }).prompts };
      return liturgyPrompts(stored);
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /church/liturgy-prompts": liturgyPrompts(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <LiturgySettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/liturgy" },
  );
  return { ...view, api };
}

function puts(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PUT" && r.path === "/church/liturgy-prompts");
}

/** A card's header button: its title, then "Customized" when it is. */
function cardButton(title: string) {
  return screen.findByRole("button", { name: new RegExp(`^${title.replace(/[()]/g, "\\$&")}( Customized)?$`) });
}

/** Opens a card (they start closed on a phone) and returns its box. */
async function openCard(user: ReturnType<typeof renderPage>["user"], title: string) {
  await user.click(await cardButton(title));
  return screen.findByRole("textbox", { name: title });
}

describe("Settings → Liturgy prompts (slice 6a-3a)", () => {
  it("shows a member every prompt read-only, with the note, the help in its place and no controls", async () => {
    const { user } = renderPage("member", { "GET /church/liturgy-prompts": liturgyPrompts({ benediction: "Go in peace." }, { can_edit: false }) });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText(PROMPTS_INTRO)).toBeInTheDocument();
    const titles = screen.getAllByRole("button", { name: /./ }).map((b) => b.textContent);
    expect(titles).toEqual([
      "Overall voice (system prompt)",
      "Call to Worship",
      "Opening Prayer",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "Prayers of the People",
      "Offertory Prayer",
      "BenedictionCustomized",
    ]);
    const system = await openCard(user, "Overall voice (system prompt)");
    expect(system).toHaveAttribute("readonly");
    expect(system).toHaveValue(DEFAULT_PROMPTS.system);
    expect(system).toHaveAccessibleDescription(SYSTEM_NOTE);
    const benediction = await openCard(user, "Benediction");
    expect(benediction).toHaveValue("Go in peace.");
    expect(benediction).toHaveAttribute("readonly");
    const help = screen.getByText(/^Placeholders you can use/);
    expect(help.textContent).toMatch(new RegExp(`ignored \\(they render as blank\\)\\. ${BRACE_NOTE.replace(/[{}.]/g, "\\$&")}$`));
    expect(help.previousElementSibling).toHaveTextContent("Section prompts");
    expect(screen.queryByRole("button", { name: "Reset to default" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Save prompts" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
  });

  it("opens every card on a wide screen", async () => {
    const wide = vi.spyOn(window, "matchMedia").mockImplementation(
      (query) => ({ matches: true, media: query, addEventListener: () => {}, removeEventListener: () => {} }) as unknown as MediaQueryList,
    );
    renderPage("admin");
    await screen.findByRole("textbox", { name: "Overall voice (system prompt)" });
    expect(screen.getAllByRole("textbox")).toHaveLength(9);
    wide.mockRestore();
  });

  it("marks a changed card Customized, puts its default back, and saves only the church's own wording", async () => {
    const server = promptsServer();
    const { api, user } = renderPage("admin", { "GET /church/liturgy-prompts": server.get, "PUT /church/liturgy-prompts": server.put });
    const save = await screen.findByRole("button", { name: "Save prompts" });
    expect(save).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
    const benediction = await openCard(user, "Benediction");
    const reset = within(benediction.closest("[data-slot=collapsible]") as HTMLElement).getByRole("button", { name: "Reset to default" });
    expect(reset).toBeDisabled();
    await user.type(benediction, " Amen.");
    expect(screen.getByRole("button", { name: /^Benediction/ })).toHaveTextContent("BenedictionCustomized");
    await user.click(reset);
    expect(benediction).toHaveValue(DEFAULT_PROMPTS.benediction);
    expect(screen.getByRole("button", { name: /^Benediction/ })).toHaveTextContent(/^Benediction$/);
    expect(save).toBeDisabled();
    await user.clear(benediction);
    await user.type(benediction, "  Go in peace.  ");
    const confession = await openCard(user, "Prayer of Confession");
    await user.type(confession, " ");
    await user.click(save);
    expect(await screen.findByText(PROMPTS_SAVED)).toBeInTheDocument();
    expect(puts(api)).toHaveLength(1);
    expect(puts(api)[0].body).toEqual({ prompts: { benediction: "Go in peace." } });
    expect(puts(api)[0].headers["x-church-id"]).toBe(church().id);
    await waitFor(() => expect(save).toBeDisabled());
    expect(benediction).toHaveValue("Go in peace.");
    expect(screen.getByRole("button", { name: "Reset all to defaults" })).toBeInTheDocument();
  });

  it("opens and focuses the card a 422 names, with its message, and saves nothing", async () => {
    const message = "Benediction prompt: It has a { or } without a partner. Use {{ or }} to print a brace.";
    const { user } = renderPage("admin", {
      "PUT /church/liturgy-prompts": fakeError(422, "prompt_invalid", message, { fields: { "prompts.benediction": message } }),
    });
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " {{");
    await user.click(screen.getByRole("button", { name: /^Benediction/ })); // closed again before saving
    expect(screen.queryByRole("textbox", { name: "Benediction" })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    const box = await screen.findByRole("textbox", { name: "Benediction" });
    await waitFor(() => expect(box).toHaveFocus());
    expect(box).toHaveAttribute("aria-invalid", "true");
    expect(box).toHaveAccessibleDescription(message);
    expect(screen.queryByText(PROMPTS_SAVED)).toBeNull();
    await user.type(box, "x");
    expect(screen.queryByText(message)).toBeNull();
  });

  it("toasts a refusal that names no card, and keeps the edits", async () => {
    const { user } = renderPage("admin", {
      "PUT /church/liturgy-prompts": fakeError(422, "invalid_request", "The request was not valid.", {
        fields: { "prompts.sermon.[key]": "Not a valid value." },
      }),
    });
    const offertory = await openCard(user, "Offertory Prayer");
    await user.type(offertory, " Amen.");
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    expect(await screen.findByText("The request was not valid.")).toBeInTheDocument();
    expect(offertory).toHaveValue(`${DEFAULT_PROMPTS.offertory_prayer} Amen.`);
  });

  it("asks before resetting everything, cannot be closed while it runs, and then shows the defaults", async () => {
    let finish: (value: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      "GET /church/liturgy-prompts": liturgyPrompts({ system: "Our own voice.", benediction: "Go in peace." }),
      "PUT /church/liturgy-prompts": () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    });
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " Amen.");
    await user.click(screen.getByRole("button", { name: "Reset all to defaults" }));
    const dialog = await screen.findByRole("alertdialog", { name: RESET_ALL_TITLE });
    expect(dialog).toHaveTextContent("Your church's custom wording will be removed and the shared defaults used.");
    await user.click(within(dialog).getByRole("button", { name: "Reset all" }));
    await user.keyboard("{Escape}");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("alertdialog", { name: RESET_ALL_TITLE })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save prompts", hidden: true })).toBeDisabled();
    expect(puts(api)[0].body).toEqual({ prompts: {} });
    finish(liturgyPrompts());
    expect(await screen.findByText(PROMPTS_RESET)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(benediction).toHaveValue(DEFAULT_PROMPTS.benediction);
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Liturgy prompts" })).toHaveFocus());
  });

  it("rebases on newer data: another admin's change shows in an untouched card, and the edited card is kept", async () => {
    const { api, user, queryClient } = renderPage("admin", { "PUT /church/liturgy-prompts": promptsServer().put });
    const system = await openCard(user, "Overall voice (system prompt)");
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " Amen.");
    queryClient.setQueryData(keys.liturgyPrompts(church().id), liturgyPrompts({ system: "Another admin's voice." }));
    await waitFor(() => expect(system).toHaveValue("Another admin's voice."));
    expect(benediction).toHaveValue(`${DEFAULT_PROMPTS.benediction} Amen.`);
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    await screen.findByText(PROMPTS_SAVED);
    expect(puts(api)[0].body).toEqual({
      prompts: { system: "Another admin's voice.", benediction: `${DEFAULT_PROMPTS.benediction} Amen.` },
    });
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", {
      "PUT /church/liturgy-prompts": fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.type(await openCard(user, "Benediction"), " Amen.");
    await user.click(screen.getByRole("button", { name: "Save prompts" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("asks before leaving with unsaved edits, through the Settings nav", async () => {
    const { user } = renderPage("admin");
    const contacts = await screen.findByRole("link", { name: "Contacts" });
    const benediction = await openCard(user, "Benediction");
    await user.type(benediction, " Amen.");
    await user.click(contacts);
    let dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(benediction).toHaveValue(`${DEFAULT_PROMPTS.benediction} Amen.`);
    expect(testRouter.push).not.toHaveBeenCalled();
    await user.click(contacts);
    dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/contacts");
  });

  it("lets the footer sit after the cards while the phone keyboard is open", async () => {
    const { user } = renderPage("admin");
    const footer = (await screen.findByRole("button", { name: "Save prompts" })).parentElement!;
    expect(footer).toHaveClass("sticky", "bottom-0");
    expect(footer).not.toHaveAttribute("data-keyboard-open");
    await user.click(await openCard(user, "Benediction"));
    expect(footer).toHaveAttribute("data-keyboard-open");
    expect(footer).toHaveClass("max-md:static");
  });

  it("shows the error state with Retry when the prompts cannot be read", async () => {
    renderPage("admin", { "GET /church/liturgy-prompts": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/liturgy-prompts-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the route does not exist yet, so the file cannot load):
```
 FAIL  |dom| src/components/settings/liturgy-prompts-page.test.tsx [ src/components/settings/liturgy-prompts-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the page and its route**

**Create `frontend/src/components/settings/liturgy-prompts-page.tsx`:**

````tsx
"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgyPrompts, PromptField, PromptKey } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useLiturgyPrompts, useSaveLiturgyPrompts } from "@/lib/queries/liturgy-prompts";
import {
  hasPromptChanges,
  isCustomized,
  MAX_PROMPT_LENGTH,
  PROMPT_KEYS,
  promptFieldErrors,
  promptsPayload,
  promptValuesFrom,
  rebasePrompts,
  type PromptErrors,
  type PromptValues,
} from "@/lib/settings/prompts";
import { useAutosize } from "@/lib/use-autosize";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

export const PROMPTS_INTRO =
  "These are the instructions the AI follows when it writes your liturgy. Edit any of them to shape the voice; leave a box on its default to use the shared wording.";
export const ADMINS_ONLY = "Only admins can edit the prompts. You can read them below.";
export const SYSTEM_NOTE = "Placeholders aren't filled in here; this text is sent as written.";
export const BRACE_NOTE = "Use {{ or }} to print a brace.";
export const RESET_ALL_TITLE = "Reset all prompts?";
const RESET_ALL_BODY = "Your church's custom wording will be removed and the shared defaults used.";
const SYSTEM_TITLE = "Overall voice (system prompt)";
/** The two long prompts start taller (6a spec UX §3). */
const TALL: ReadonlySet<PromptKey> = new Set(["system", "prayers_of_the_people"]);

/** Open from `md` (48rem), closed below it, as the page first renders (6a spec UX §3; as the hymn matches). */
function openAtFirst(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(min-width: 48rem)").matches;
}

const allKeys = (open: boolean) => Object.fromEntries(PROMPT_KEYS.map((key) => [key, open])) as Record<PromptKey, boolean>;

/**
 * `/settings/liturgy` (slice 6a-3a; 6a spec UX §3): the instructions the AI
 * follows when it writes the liturgy, the overall voice (system) prompt and
 * one per section, each beside its shared default. Every member reads them;
 * owners and admins edit them, put one back to its default (unsaved until
 * **Save prompts**) and reset them all (confirmed). 6a's rules for settings
 * forms: newer server data rebases the form, and leaving with unsaved edits
 * asks first (`LeaveGuard`).
 */
export function LiturgyPromptsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const prompts = useLiturgyPrompts();
  const headingRef = useRef<HTMLHeadingElement>(null);
  let body: ReactNode;
  if (prompts.data) {
    body = <PromptsForm out={prompts.data} admin={admin} headingRef={headingRef} />;
  } else if (prompts.isError) {
    body = <ErrorState error={prompts.error} onRetry={() => void prompts.refetch()} retrying={prompts.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="prompts-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="prompts-title" ref={headingRef} tabIndex={-1} className="text-lg font-semibold outline-none">
          Liturgy prompts
        </h2>
        <p className="text-sm text-muted-foreground">{PROMPTS_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: LiturgyPrompts; baseline: PromptValues; form: PromptValues };

function PromptsForm({
  out,
  admin,
  headingRef,
}: {
  out: LiturgyPrompts;
  admin: boolean;
  headingRef: RefObject<HTMLHeadingElement | null>;
}) {
  const save = useSaveLiturgyPrompts();
  const reset = useSaveLiturgyPrompts();
  const keyboardOpen = useKeyboardOpen();
  const [state, setState] = useState<FormState>(() => {
    const form = promptValuesFrom(out);
    return { source: out, baseline: form, form };
  });
  const [errors, setErrors] = useState<PromptErrors>({});
  const [open, setOpen] = useState(() => allKeys(openAtFirst()));
  const focusKey = useRef<PromptKey | null>(null);
  const [confirming, setConfirming] = useState(false);
  const resetDone = useRef(false);
  const { form, baseline } = state;
  const pending = save.isPending || reset.isPending;
  const dirty = admin && hasPromptChanges(baseline, form, out.fields);
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : promptValuesFrom(out);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (out !== state.source) {
    const next = promptValuesFrom(out);
    setState({ source: out, baseline: next, form: rebasePrompts(baseline, form, next) });
  }

  // The first card a failed save named: opened by onError, focused once it is on the page.
  useEffect(() => {
    if (focusKey.current === null) return;
    document.getElementById(`prompt-${focusKey.current}`)?.focus();
    focusKey.current = null;
  });

  const update = (key: PromptKey, value: string) => {
    setState((s) => ({ ...s, form: { ...s.form, [key]: value } }));
    if (errors[key]) setErrors((e) => ({ ...e, [key]: undefined }));
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending || !dirty) return;
    const sent = form;
    save.mutate(
      { prompts: promptsPayload(sent, out.fields) },
      {
        // What was typed while saving stays; everything else shows what was stored.
        onSuccess: (saved) => {
          setErrors({});
          setState((s) => {
            const next = promptValuesFrom(saved);
            return { source: saved, baseline: next, form: rebasePrompts(sent, s.form, next) };
          });
        },
        onError: (e) => {
          const found = promptFieldErrors(e, PROMPT_KEYS);
          if (found === null) return;
          setErrors(found);
          setOpen((o) => ({ ...o, ...Object.fromEntries(Object.keys(found).map((key) => [key, true])) }));
          focusKey.current = PROMPT_KEYS.find((key) => found[key]) ?? null;
        },
      },
    );
  }

  function onResetAll() {
    if (pending) return;
    resetDone.current = false;
    reset.mutate(
      { prompts: {}, reset: true },
      {
        onSuccess: (saved) => {
          const next = promptValuesFrom(saved);
          setState({ source: saved, baseline: next, form: next });
          setErrors({});
          resetDone.current = true;
          setConfirming(false);
        },
        onError: () => setConfirming(false),
      },
    );
  }

  const card = (field: PromptField) => (
    <PromptCard
      key={field.key}
      field={field}
      value={shown[field.key]}
      admin={admin}
      open={open[field.key]}
      onOpenChange={(next) => setOpen((o) => ({ ...o, [field.key]: next }))}
      onChange={(value) => update(field.key, value)}
      error={admin ? errors[field.key] : undefined}
      note={field.key === "system" ? SYSTEM_NOTE : undefined}
    />
  );
  const [system, ...sections] = out.fields;

  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Liturgy prompts">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      {card(system)}
      <div className="grid gap-1">
        <h3 className="text-base font-medium">Section prompts</h3>
        <p className="text-sm text-muted-foreground">{`${out.placeholder_help} ${BRACE_NOTE}`}</p>
      </div>
      {sections.map(card)}
      {admin ? (
        <div
          data-keyboard-open={keyboardOpen ? "" : undefined}
          className={cn(
            "sticky bottom-0 z-10 flex flex-wrap gap-2 border-t bg-background/95 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
            // Below md with the iPhone keyboard open the footer sits after the last card, reachable and not covering the box.
            keyboardOpen && "max-md:static",
          )}
        >
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!dirty || reset.isPending}>
            Save prompts
          </PendingButton>
          {out.fields.some((f) => f.customized) ? (
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit"
              disabled={pending}
              onClick={() => setConfirming(true)}
            >
              Reset all to defaults
            </Button>
          ) : null}
        </div>
      ) : null}
      <ConfirmDialog
        open={confirming}
        onOpenChange={(next) => {
          if (!next && !reset.isPending) setConfirming(false);
        }}
        title={RESET_ALL_TITLE}
        description={RESET_ALL_BODY}
        confirmLabel="Reset all"
        destructive
        pending={reset.isPending}
        onConfirm={onResetAll}
        // After a reset the button that opened it is gone (nothing is customized): the page's heading takes focus.
        finalFocus={() => (resetDone.current ? headingRef.current : true)}
      />
      <LeaveGuard when={dirty} />
    </form>
  );
}

function PromptCard({
  field,
  value,
  admin,
  open,
  onOpenChange,
  onChange,
  error,
  note,
}: {
  field: PromptField;
  value: string;
  admin: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChange: (value: string) => void;
  error?: string;
  note?: string;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value, open);
  const id = `prompt-${field.key}`;
  const title = field.key === "system" ? SYSTEM_TITLE : field.label;
  const customized = isCustomized(value, field);
  const describedBy = [note && `${id}-note`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  return (
    <Collapsible open={open} onOpenChange={onOpenChange} className="rounded-lg border">
      <CollapsibleTrigger className="flex min-h-11 w-full items-center gap-2 rounded-lg px-4 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="min-w-0 flex-1 text-sm font-medium">{title}</span>
        {customized ? <Badge variant="secondary">Customized</Badge> : null}
        <ChevronDownIcon aria-hidden="true" className={cn("size-4 shrink-0 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-2 px-4 pb-4">
        <label htmlFor={id} className="sr-only">
          {title}
        </label>
        <Textarea
          id={id}
          ref={ref}
          value={value}
          readOnly={!admin}
          maxLength={MAX_PROMPT_LENGTH}
          rows={TALL.has(field.key) ? 8 : 4}
          className="max-h-[60vh] overflow-y-auto"
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          onChange={(e) => onChange(e.target.value)}
        />
        {note ? (
          <p id={`${id}-note`} className="text-sm text-muted-foreground">
            {note}
          </p>
        ) : null}
        {error ? (
          <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        {admin ? (
          <Button
            type="button"
            variant="link"
            className="h-11 justify-self-start px-0 md:h-auto"
            disabled={value === field.default}
            onClick={() => onChange(field.default)}
          >
            Reset to default
          </Button>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx`:**

````tsx
"use client";

import { LiturgyPromptsPage } from "@/components/settings/liturgy-prompts-page";

/** Settings → Liturgy: the instructions the AI follows when it writes the liturgy (slice 6a-3a; F §4.1). */
export default function LiturgySettingsRoute() {
  return <LiturgyPromptsPage />;
}
````

- [ ] **Step 4: See them pass (three runs), the types, lint and the suite**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/settings/liturgy-prompts-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected** (no flaky run):
```
      Tests  11 passed (11)
      Tests  11 passed (11)
      Tests  11 passed (11)
```
```
typecheck 0
lint 0
```
```
 Test Files  105 passed (105)
      Tests  890 passed (890)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/liturgy-prompts-page.test.tsx frontend/src/components/settings/liturgy-prompts-page.tsx 'frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx'
git commit -q -m "Slice 6a-3a: Settings → Liturgy prompts" -m "/settings/liturgy: the overall voice (system) prompt and the eight
section prompts, each a collapsible card with Customized and Reset to
default; a sticky footer with Save prompts and a confirmed Reset all to
defaults (owners and admins); read-only for members. A 422 opens and
focuses the card it names; newer data rebases the form; leaving with
unsaved edits asks first; the footer moves after the cards while the
phone keyboard is open." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `890 passed` in 105 files.

### Task 7: The rubric form's rules and queries (S "Pure helpers" `rubric.ts`, "Queries and mutations"; clarifications 6-8, 11)

**Files:**
- Create: `frontend/src/lib/settings/rubric.test.ts`, `frontend/src/lib/settings/rubric.ts`, `frontend/src/lib/queries/rubric.ts`
- Modify: `frontend/src/test/fixtures/index.ts`

- [ ] **Step 1: Write the test data and the failing tests**

The fixtures add `defaultRubric()` (the default rubric's shape, two short points a checklist) and `rubric(overrides)` (`GET /rubric`'s answer with `customized` and `defaults`). `rubric.test.ts` pins S's cases: `cleanPoints`, `rubricPatch` (unchanged is `{}`, an item equal to its default is `null`, never `[]`, the year as a number), `yearError`, `checklistError`, plus the checklists' order and titles, **Customized**, Reset all's body and the rebase.

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  ReviseBody,
````

**with:**

````ts
  ReviseBody,
  Rubric,
  RubricValues,
````

**Append to `frontend/src/test/fixtures/index.ts`:**

````ts

/** The shared default rubric (backend `service_rubric.DEFAULT_RUBRIC`), shortened to two points a checklist. */
export function defaultRubric(): RubricValues {
  const two = (label: string) => [`${label} point one`, `${label} point two`];
  return {
    hymns: { opening: two("Opening"), response: two("Response"), closing: two("Closing") },
    prayers: Object.fromEntries(Object.entries(SECTION_LABELS).map(([key, label]) => [key, two(label)])),
    prefer_before_year: 1970,
    prefer_familiar: true,
  };
}

/** `GET /rubric`: the defaults with `overrides` applied (hymns and prayers merged per checklist), and `customized`. */
export function rubric(overrides: Partial<RubricValues> = {}): Rubric {
  const defaults = defaultRubric();
  const merged: RubricValues = {
    ...defaults,
    ...overrides,
    hymns: { ...defaults.hymns, ...overrides.hymns },
    prayers: { ...defaults.prayers, ...overrides.prayers },
  };
  const customized = [
    ...Object.keys(overrides.hymns ?? {}).map((slot) => `hymns.${slot}`),
    ...Object.keys(overrides.prayers ?? {}).map((section) => `prayers.${section}`),
    ...(["prefer_before_year", "prefer_familiar"] as const).filter((key) => key in overrides),
  ];
  return { rubric: merged, customized, defaults };
}
````

**Create `frontend/src/lib/settings/rubric.test.ts`:**

````ts
/** Settings → Rubric's form rules (slice 6a-3a; 6a spec "Pure helpers" `rubric.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { isInvalidRubric } from "@/lib/queries/rubric";
import { defaultRubric, rubric } from "@/test/fixtures";

import {
  checklistCustomized,
  checklistError,
  CHECKLISTS,
  cleanPoints,
  rebaseRubric,
  resetAllPatch,
  rubricErrors,
  rubricFormFrom,
  rubricPatch,
  yearError,
} from "./rubric";

const DEFAULTS = defaultRubric();
const BENEDICTION = CHECKLISTS.find((l) => l.key === "prayers.benediction")!;

describe("Settings → Rubric's form rules (slice 6a-3a)", () => {
  it("lists the hymn slots, then the prayers in section order, with their titles", () => {
    expect(CHECKLISTS.map((l) => l.label)).toEqual([
      "Opening (Gathering) Hymn",
      "Response Hymn (after the sermon)",
      "Closing (Sending) Hymn",
      "Call to Worship",
      "Opening Prayer",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "Prayers of the People",
      "Offertory Prayer",
      "Benediction",
    ]);
    expect(CHECKLISTS[0].key).toBe("hymns.opening");
  });

  it("cleans points as the server does and says what is wrong with the server's words", () => {
    expect(cleanPoints(["  Sends   the people\nout. ", "", " \t ", "Amen"])).toEqual(["Sends the people out.", "Amen"]);
    expect(checklistError(["", "  "])).toBe("Keep at least one point, or use Reset to default.");
    expect(checklistError(["x"])).toBeNull();
    expect([yearError("1500", 2026), yearError(" 2026 ", 2026)]).toEqual([null, null]);
    for (const bad of ["1499", "2027", "", "19x0", "1900.5"]) {
      expect(yearError(bad, 2026)).toBe("The preferred year must be between 1500 and 2026.");
    }
    const form = rubricFormFrom(DEFAULTS);
    form.checklists["hymns.closing"] = [];
    form.prefer_before_year = "1400";
    expect(rubricErrors(form, 2026)).toEqual({
      "hymns.closing": "Keep at least one point, or use Reset to default.",
      prefer_before_year: "The preferred year must be between 1500 and 2026.",
    });
  });

  it("sends only what changed, cleaned; an item back on its default is null; never an empty list", () => {
    const baseline = rubricFormFrom(rubric({ prayers: { benediction: ["Ours."] } }).rubric);
    expect(rubricPatch(baseline, baseline, DEFAULTS)).toEqual({});
    const current = rubricFormFrom(rubric({ prayers: { benediction: ["Ours."] } }).rubric);
    current.checklists["hymns.closing"] = ["  Joyful\nand sending. ", ""];
    current.checklists["prayers.benediction"] = [...DEFAULTS.prayers.benediction, " "];
    current.checklists["prayers.assurance"] = [`${DEFAULTS.prayers.assurance[0]} `, DEFAULTS.prayers.assurance[1]];
    current.prefer_before_year = " 1900 ";
    current.prefer_familiar = false;
    expect(rubricPatch(baseline, current, DEFAULTS)).toEqual({
      hymns: { closing: ["Joyful and sending."] },
      prayers: { benediction: null },
      prefer_before_year: 1900,
      prefer_familiar: false,
    });
    const back = { ...current, prefer_before_year: "1970", prefer_familiar: true };
    const changed = rubricFormFrom(rubric({ prefer_before_year: 1900, prefer_familiar: false }).rubric);
    expect(rubricPatch(changed, back, DEFAULTS)).toMatchObject({ prefer_before_year: null, prefer_familiar: null });
  });

  it("marks a checklist Customized only when its cleaned points differ from the default", () => {
    const form = rubricFormFrom(DEFAULTS);
    expect(checklistCustomized(form, DEFAULTS, BENEDICTION)).toBe(false);
    form.checklists["prayers.benediction"] = [` ${DEFAULTS.prayers.benediction[0]}`, DEFAULTS.prayers.benediction[1], ""];
    expect(checklistCustomized(form, DEFAULTS, BENEDICTION)).toBe(false);
    form.checklists["prayers.benediction"] = [DEFAULTS.prayers.benediction[0]];
    expect(checklistCustomized(form, DEFAULTS, BENEDICTION)).toBe(true);
  });

  it("resets exactly the customized items, and rebases untouched items on newer data", () => {
    expect(resetAllPatch(["hymns.closing", "prayers.benediction", "prefer_before_year", "prefer_familiar"])).toEqual({
      hymns: { closing: null },
      prayers: { benediction: null },
      prefer_before_year: null,
      prefer_familiar: null,
    });
    expect(resetAllPatch([])).toEqual({});
    const oldBaseline = rubricFormFrom(DEFAULTS);
    const current = { ...rubricFormFrom(DEFAULTS), prefer_familiar: false };
    current.checklists["prayers.benediction"] = ["Ours."];
    const next = rubricFormFrom(rubric({ prefer_before_year: 1900, prayers: { benediction: ["Theirs."], assurance: ["Theirs too."] } }).rubric);
    const rebased = rebaseRubric(oldBaseline, current, next);
    expect(rebased.checklists["prayers.benediction"]).toEqual(["Ours."]);
    expect(rebased.checklists["prayers.assurance"]).toEqual(["Theirs too."]);
    expect([rebased.prefer_before_year, rebased.prefer_familiar]).toEqual(["1900", false]);
  });

  it("knows the server's 422 about the rubric", () => {
    expect(isInvalidRubric(new ApiError(422, "invalid_rubric", "Checklist points cannot contain control characters."))).toBe(true);
    expect(isInvalidRubric(new ApiError(422, "invalid_request", "The request was not valid."))).toBe(false);
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/settings/rubric.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`lib/settings/rubric.ts` does not exist yet):
```
 FAIL  |unit| src/lib/settings/rubric.test.ts [ src/lib/settings/rubric.test.ts ]
      Tests  no tests
```

- [ ] **Step 3: Write the rules and the queries**

**Create `frontend/src/lib/settings/rubric.ts`:**

````ts
/**
 * Settings → Rubric's form rules (slice 6a-3a; 6a spec "Pure helpers" `rubric.ts`;
 * the service rubric spec's limits). The form keeps a baseline (built from
 * the last rubric the server sent) and the current edits: one list of points
 * per checklist and one value per preference. A save sends one sparse
 * `PATCH /rubric` with only the items that changed, cleaned as the server
 * cleans them; an item put back to its default is sent as null, so the church
 * keeps following future improvements to the defaults.
 */
import { SECTION_KEYS, SLOTS, type SectionKey, type Slot } from "@/lib/draft/schema";
import type { RubricValues } from "@/lib/api/types";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

/** The hymn slots' titles (backend `service_rubric.HYMN_SLOT_LABELS`). */
export const HYMN_SLOT_LABELS: Readonly<Record<Slot, string>> = {
  opening: "Opening (Gathering) Hymn",
  response: "Response Hymn (after the sermon)",
  closing: "Closing (Sending) Hymn",
};

/** The server's limits (`service_rubric.MAX_ITEMS`, `MAX_ITEM_CHARS`, `MIN_YEAR`). */
export const MAX_POINTS = 12;
export const MAX_POINT_LENGTH = 300;
export const MIN_YEAR = 1500;
export const KEEP_ONE_POINT = "Keep at least one point, or use Reset to default.";
export const AT_MOST_POINTS = "A checklist can have at most 12 points.";

/** One checklist's name as `customized` and the form use it: "hymns.opening", "prayers.benediction". */
export type ChecklistKey = `hymns.${Slot}` | `prayers.${SectionKey}`;
export type Checklist = { key: ChecklistKey; group: "hymns" | "prayers"; item: string; label: string };

/** Every checklist in the page's order: the hymn slots, then the prayers in section order. */
export const CHECKLISTS: readonly Checklist[] = [
  ...SLOTS.map((slot): Checklist => ({ key: `hymns.${slot}`, group: "hymns", item: slot, label: HYMN_SLOT_LABELS[slot] })),
  ...SECTION_KEYS.map(
    (section): Checklist => ({ key: `prayers.${section}`, group: "prayers", item: section, label: SECTION_LABELS[section] }),
  ),
];

export type RubricForm = {
  checklists: Record<ChecklistKey, string[]>;
  prefer_before_year: string;
  prefer_familiar: boolean;
};

/** A point as the server stores it: every run of whitespace (line breaks too) one space, trimmed. */
export function cleanPoint(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** A checklist as the server stores it: each point cleaned, blank points dropped. */
export function cleanPoints(points: readonly string[]): string[] {
  return points.map(cleanPoint).filter((p) => p !== "");
}

const samePoints = (a: readonly string[], b: readonly string[]) => {
  const x = cleanPoints(a);
  const y = cleanPoints(b);
  return x.length === y.length && x.every((p, i) => p === y[i]);
};

function points(values: RubricValues, list: Checklist): string[] {
  return [...(values[list.group][list.item] ?? [])];
}

/** The form a rubric starts at, and its baseline. */
export function rubricFormFrom(values: RubricValues): RubricForm {
  return {
    checklists: Object.fromEntries(CHECKLISTS.map((list) => [list.key, points(values, list)])) as Record<ChecklistKey, string[]>,
    prefer_before_year: String(values.prefer_before_year),
    prefer_familiar: values.prefer_familiar,
  };
}

/** The year typed, or null when it is not a whole number. */
function parseYear(text: string): number | null {
  const trimmed = text.trim();
  return /^\d{1,4}$/.test(trimmed) ? Number(trimmed) : null;
}

/** "The preferred year must be between 1500 and {thisYear}." (the server's words), or null. */
export function yearError(text: string, thisYear: number): string | null {
  const year = parseYear(text);
  return year !== null && year >= MIN_YEAR && year <= thisYear ? null : `The preferred year must be between ${MIN_YEAR} and ${thisYear}.`;
}

/** "Keep at least one point, or use Reset to default." when every point is blank or removed, else null. */
export function checklistError(list: readonly string[]): string | null {
  return cleanPoints(list).length === 0 ? KEEP_ONE_POINT : null;
}

/** Every message the form shows: per checklist, and the year's. */
export function rubricErrors(form: RubricForm, thisYear: number): Partial<Record<ChecklistKey | "prefer_before_year", string>> {
  const errors: Partial<Record<ChecklistKey | "prefer_before_year", string>> = {};
  for (const list of CHECKLISTS) {
    const message = checklistError(form.checklists[list.key]);
    if (message) errors[list.key] = message;
  }
  const year = yearError(form.prefer_before_year, thisYear);
  if (year) errors.prefer_before_year = year;
  return errors;
}

/** True when the checklist's cleaned points differ from the default's (its **Customized** badge). */
export function checklistCustomized(form: RubricForm, defaults: RubricValues, list: Checklist): boolean {
  return !samePoints(form.checklists[list.key], points(defaults, list));
}

/** The names of the items whose cleaned value differs between two forms. */
export function changedItems(a: RubricForm, b: RubricForm): string[] {
  const changed: string[] = CHECKLISTS.filter((list) => !samePoints(a.checklists[list.key], b.checklists[list.key])).map((l) => l.key);
  if (a.prefer_before_year.trim() !== b.prefer_before_year.trim()) changed.push("prefer_before_year");
  if (a.prefer_familiar !== b.prefer_familiar) changed.push("prefer_familiar");
  return changed;
}

export type RubricPatch = {
  hymns?: Partial<Record<Slot, string[] | null>>;
  prayers?: Partial<Record<SectionKey, string[] | null>>;
  prefer_before_year?: number | null;
  prefer_familiar?: boolean | null;
};

/**
 * `PATCH /rubric`'s body: only the items that changed from the baseline, each
 * cleaned; an item whose cleaned value equals its default is null. Call it
 * only when `rubricErrors` is empty (it never sends an empty checklist).
 */
export function rubricPatch(baseline: RubricForm, current: RubricForm, defaults: RubricValues): RubricPatch {
  const patch: RubricPatch = {};
  for (const list of CHECKLISTS) {
    const now = current.checklists[list.key];
    if (samePoints(now, baseline.checklists[list.key])) continue;
    const value = samePoints(now, points(defaults, list)) ? null : cleanPoints(now);
    if (list.group === "hymns") patch.hymns = { ...patch.hymns, [list.item]: value };
    else patch.prayers = { ...patch.prayers, [list.item]: value };
  }
  if (changedItems(baseline, current).includes("prefer_before_year")) {
    const year = parseYear(current.prefer_before_year);
    patch.prefer_before_year = year === defaults.prefer_before_year ? null : year;
  }
  if (current.prefer_familiar !== baseline.prefer_familiar) {
    patch.prefer_familiar = current.prefer_familiar === defaults.prefer_familiar ? null : current.prefer_familiar;
  }
  return patch;
}

/** Reset all's body: null for every item the church has customized (`customized`'s dotted names). */
export function resetAllPatch(customized: readonly string[]): RubricPatch {
  const patch: RubricPatch = {};
  for (const name of customized) {
    const list = CHECKLISTS.find((l) => l.key === name);
    if (list?.group === "hymns") patch.hymns = { ...patch.hymns, [list.item]: null };
    else if (list?.group === "prayers") patch.prayers = { ...patch.prayers, [list.item]: null };
    else if (name === "prefer_before_year") patch.prefer_before_year = null;
    else if (name === "prefer_familiar") patch.prefer_familiar = null;
  }
  return patch;
}

/**
 * 6a's rebase for the rubric: newer server data replaces each item the user
 * has not edited (its cleaned value still equal to the old baseline's), and
 * each edited item keeps the edit.
 */
export function rebaseRubric(oldBaseline: RubricForm, current: RubricForm, next: RubricForm): RubricForm {
  const edited = new Set(changedItems(oldBaseline, current));
  return {
    checklists: Object.fromEntries(
      CHECKLISTS.map((list) => [list.key, edited.has(list.key) ? current.checklists[list.key] : next.checklists[list.key]]),
    ) as Record<ChecklistKey, string[]>,
    prefer_before_year: edited.has("prefer_before_year") ? current.prefer_before_year : next.prefer_before_year,
    prefer_familiar: edited.has("prefer_familiar") ? current.prefer_familiar : next.prefer_familiar,
  };
}
````

**Create `frontend/src/lib/queries/rubric.ts`:**

````ts
/**
 * Settings → Rubric's queries (slice 6a-3a; 6a spec "Queries and mutations" `rubric.ts`).
 *
 * - `useRubric()`: `GET /rubric` under ["church", id, "rubric"]; any member.
 * - `useSaveRubric()`: one sparse `PATCH /rubric` (admins); `reset: true` for
 *   Reset all. Success cancels a read in flight (it may predate the save),
 *   caches the answer and toasts "Rubric saved." or "Rubric reset to
 *   defaults.". A patch that changes the preferred year also refreshes every
 *   hymn list (`newer_than_preferred` follows the year: the builder's picker
 *   relabels with no reload). Liturgy generation reads the rubric on the
 *   server, so nothing else is refreshed. Not optimistic (F §4.4).
 *
 * Errors: a 401 or a lost church the app already reports. A 422
 * `invalid_rubric` is the form's to show (above its footer). A role 403 (an
 * admin demoted meanwhile) is toasted and refetches the church profile, so the
 * page turns into the member's view. Anything else is toasted.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { Rubric } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import type { RubricPatch } from "@/lib/settings/rubric";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const RUBRIC_SAVED = "Rubric saved.";
export const RUBRIC_RESET = "Rubric reset to defaults.";

/** True for the server's 422 about the rubric's values: its message is shown above the form's footer. */
export function isInvalidRubric(e: unknown): boolean {
  return e instanceof ApiError && e.status === 422 && e.code === "invalid_rubric";
}

export function useRubric(): UseQueryResult<Rubric, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<Rubric, ApiError>({
    queryKey: keys.rubric(church.id),
    queryFn: ({ signal }) => api.church<Rubric>("/rubric", { signal }),
  });
}

export type SaveRubric = { patch: RubricPatch; reset?: boolean };

export function useSaveRubric() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<Rubric, ApiError, SaveRubric>({
    mutationFn: ({ patch }) => api.church<Rubric>("/rubric", { method: "PATCH", json: patch }),
    onSuccess: async (saved, { patch, reset }) => {
      // A read already in flight may predate the save; its answer must not replace what is now stored.
      await queryClient.cancelQueries({ queryKey: keys.rubric(church.id) });
      queryClient.setQueryData(keys.rubric(church.id), saved);
      if ("prefer_before_year" in patch) void queryClient.invalidateQueries({ queryKey: [...keys.church(church.id), "hymns"] });
      toast.success(reset ? RUBRIC_RESET : RUBRIC_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || isInvalidRubric(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/lib/settings/rubric.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected:**
```
      Tests  6 passed (6)
```
```
typecheck 0
lint 0
```
```
 Test Files  106 passed (106)
      Tests  896 passed (896)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/test/fixtures/index.ts frontend/src/lib/settings/rubric.test.ts frontend/src/lib/settings/rubric.ts frontend/src/lib/queries/rubric.ts
git commit -q -m "Slice 6a-3a: the rubric form's rules and queries" -m "lib/settings/rubric.ts: the checklists in order with their titles, the
form and its baseline, points cleaned as the server cleans them, the
two client checks with the server's words, Customized, the sparse
PATCH body (null for an item back on its default, never an empty list),
Reset all's body and the rebase. lib/queries/rubric.ts reads and saves
the rubric; a year change refreshes every hymn list." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `896 passed` in 106 files.

### Task 8: The Service rubric page (S UX §6; clarifications 6-8, 11)

**Files:**
- Create: `frontend/src/components/settings/rubric-settings-page.test.tsx`, `frontend/src/components/settings/checklist-card.tsx`, `frontend/src/components/settings/rubric-settings-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/rubric/page.tsx`

- [ ] **Step 1: Write the failing tests**

Rendered inside the Settings layout. They pin S's DOM cases for this page: a member's read-only view (the note, the points as text, a read-only year and a disabled switch, no add, remove, reset or footer); one `PATCH` with only the edited Benediction checklist, cleaned, with the badge following the points; a checklist put back to its default sent as `null`, with **Reset to default** restoring the default points unsaved; the year alone sent, with `["church", id, "hymns"]` invalidated, and 1499 or next year shown inline with Save disabled; Enter adding a point below (focused), a pasted line break becoming a space, **Add a point** disabled at 12 with its helper, every point removed showing "Keep at least one point, or use Reset to default." with Save disabled and focus on **Add a point**; the theme note only under Opening and Closing; a 422 `invalid_rubric` shown (and focused) just above the footer with the edits kept and no toast; Reset all confirmed, sending `null` for exactly the `customized` items, not closable while it runs; the role 403; the rebase and the leave guard; and the error state.

**Create `frontend/src/components/settings/rubric-settings-page.test.tsx`:**

````tsx
/**
 * Settings → Rubric (slice 6a-3a; 6a spec UX §6): every member reads the
 * rubric, owners and admins edit its checklists and preferences and save one
 * sparse PATCH. Rendered inside the Settings layout, as the route is, with a
 * Toaster. Below `md` (jsdom's matchMedia never matches) every card starts closed.
 */
import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import RubricSettingsRoute from "@/app/(signed-in)/(church)/settings/rubric/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, RubricValues } from "@/lib/api/types";
import { authEvents } from "@/lib/queries/auth-events";
import { keys } from "@/lib/queries/keys";
import { RUBRIC_RESET, RUBRIC_SAVED } from "@/lib/queries/rubric";
import { KEEP_ONE_POINT } from "@/lib/settings/rubric";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, defaultRubric, me, rubric } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

import { THEME_NOTE } from "./checklist-card";
import { ADMINS_ONLY, RESET_ALL_TITLE, RUBRIC_INTRO } from "./rubric-settings-page";

afterEach(() => {
  toast.dismiss();
});

const DEFAULTS = defaultRubric();
const THIS_YEAR = new Date().getFullYear();

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({ "GET /rubric": rubric(), "PATCH /rubric": () => rubric(), ...routes });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <RubricSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/rubric" },
  );
  return { ...view, api };
}

function patches(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "PATCH" && r.path === "/rubric");
}

/** A card's header button: its title, then "Customized" when it is. */
function cardButton(title: string) {
  return screen.findByRole("button", { name: new RegExp(`^${title.replace(/[()]/g, "\\$&")}( Customized)?$`) });
}

/** Opens a card (they start closed on a phone) and returns it. */
async function openCard(user: ReturnType<typeof renderPage>["user"], title: string) {
  const button = await cardButton(title);
  await user.click(button);
  return button.closest("[data-slot=collapsible]") as HTMLElement;
}

function points(card: HTMLElement) {
  return within(card).getAllByRole("textbox").map((box) => (box as HTMLTextAreaElement).value);
}

describe("Settings → Rubric (slice 6a-3a)", () => {
  it("shows a member the rubric as text, with the note and no controls", async () => {
    const { user } = renderPage("member", { "GET /rubric": rubric({ prayers: { benediction: ["Sends the people out."] } }) });
    expect(await screen.findByText(ADMINS_ONLY)).toBeInTheDocument();
    expect(screen.getByText(RUBRIC_INTRO)).toBeInTheDocument();
    expect(screen.getByLabelText("Prefer hymns written before")).toHaveAttribute("readonly");
    expect(screen.getByRole("switch", { name: "Prefer familiar hymns" })).toHaveAttribute("aria-disabled", "true");
    const card = await openCard(user, "Benediction");
    expect(within(card).getByText("A good Benediction:")).toBeInTheDocument();
    expect(within(card).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["Sends the people out."]);
    expect(screen.getByRole("button", { name: "Benediction Customized" })).toBeInTheDocument();
    expect(within(card).queryAllByRole("textbox")).toEqual([]);
    for (const name of [/^Remove point/, "Add a point", /Reset to default/, "Save rubric", "Reset all to defaults"]) {
      expect(screen.queryByRole("button", { name })).toBeNull();
    }
  });

  it("saves one PATCH with only the changed checklist, cleaned, and the badge follows the points", async () => {
    const { api, user } = renderPage("admin", {
      "PATCH /rubric": () => rubric({ prayers: { benediction: ["Benediction point one", "Sends the people out."] } }),
    });
    const save = await screen.findByRole("button", { name: "Save rubric" });
    expect(save).toBeDisabled();
    const card = await openCard(user, "Benediction");
    const second = within(card).getByRole("textbox", { name: "Point 2 of Benediction" });
    await user.clear(second);
    await user.type(second, "  Sends the   people out. ");
    expect(screen.getByRole("button", { name: "Benediction Customized" })).toBeInTheDocument();
    await user.click(save);
    expect(await screen.findByText(RUBRIC_SAVED)).toBeInTheDocument();
    expect(patches(api)).toHaveLength(1);
    expect(patches(api)[0].body).toEqual({ prayers: { benediction: ["Benediction point one", "Sends the people out."] } });
    expect(patches(api)[0].headers["x-church-id"]).toBe(church().id);
    await waitFor(() => expect(save).toBeDisabled());
  });

  it("sends null for a checklist put back to its default, and Reset to default restores the default points unsaved", async () => {
    const { api, user } = renderPage("admin", { "GET /rubric": rubric({ prayers: { benediction: ["Ours."] } }) });
    const card = await openCard(user, "Benediction");
    expect(points(card)).toEqual(["Ours."]);
    await user.click(within(card).getByRole("button", { name: "Reset to default" }));
    expect(points(card)).toEqual(DEFAULTS.prayers.benediction);
    expect(screen.getByRole("button", { name: "Benediction" })).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Reset to default" })).toBeDisabled();
    expect(patches(api)).toHaveLength(0);
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    await screen.findByText(RUBRIC_SAVED);
    expect(patches(api)[0].body).toEqual({ prayers: { benediction: null } });
  });

  it("sends only the year and refreshes the hymn lists; a year out of range is named and blocks Save", async () => {
    const { api, user, queryClient } = renderPage("admin", { "PATCH /rubric": () => rubric({ prefer_before_year: 1900 }) });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const year = await screen.findByLabelText("Prefer hymns written before");
    const save = screen.getByRole("button", { name: "Save rubric" });
    for (const bad of ["1499", String(THIS_YEAR + 1)]) {
      await user.clear(year);
      await user.type(year, bad);
      expect(screen.getByText(`The preferred year must be between 1500 and ${THIS_YEAR}.`)).toBeInTheDocument();
      expect(year).toHaveAttribute("aria-invalid", "true");
      expect(save).toBeDisabled();
    }
    await user.clear(year);
    await user.type(year, "1900");
    expect(screen.queryByText(/The preferred year must be/)).toBeNull();
    await user.click(save);
    await screen.findByText(RUBRIC_SAVED);
    expect(patches(api)[0].body).toEqual({ prefer_before_year: 1900 });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["church", church().id, "hymns"] });
  });

  it("adds a point below on Enter, keeps a pasted line break as a space, stops at 12, and needs one point", async () => {
    const eleven: RubricValues["hymns"] = { closing: Array.from({ length: 11 }, (_, i) => `Point ${i + 1}`) };
    const { api, user } = renderPage("admin", { "GET /rubric": rubric({ hymns: eleven }) });
    const card = await openCard(user, "Closing (Sending) Hymn");
    expect(within(card).getByText(THEME_NOTE)).toBeInTheDocument();
    const first = within(card).getByRole("textbox", { name: "Point 1 of Closing (Sending) Hymn" });
    await user.click(first);
    await user.keyboard("{End}{Enter}");
    const added = within(card).getByRole("textbox", { name: "Point 2 of Closing (Sending) Hymn" });
    await waitFor(() => expect(added).toHaveFocus());
    expect(points(card)).toEqual(["Point 1", "", ...eleven.closing!.slice(1)]);
    fireEvent.change(added, { target: { value: "Joyful\nand sending" } });
    expect(added).toHaveValue("Joyful and sending");
    expect(within(card).getByRole("button", { name: "Add a point" })).toBeDisabled();
    expect(within(card).getByText("A checklist can have at most 12 points.")).toBeInTheDocument();
    await user.keyboard("{Enter}");
    expect(points(card)).toHaveLength(12);
    for (let n = 12; n >= 1; n -= 1) {
      await user.click(within(card).getByRole("button", { name: `Remove point ${n} from Closing (Sending) Hymn` }));
    }
    expect(within(card).getByText(KEEP_ONE_POINT)).toBeInTheDocument();
    await waitFor(() => expect(within(card).getByRole("button", { name: "Add a point" })).toHaveFocus());
    expect(screen.getByRole("button", { name: "Save rubric" })).toBeDisabled();
    await user.click(within(card).getByRole("button", { name: "Add a point" }));
    await user.keyboard("Ends in hope");
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    await screen.findByText(RUBRIC_SAVED);
    expect(patches(api)[0].body).toEqual({ hymns: { closing: ["Ends in hope"] } });
  });

  it("shows only the Opening and Closing cards' theme note", async () => {
    const { user } = renderPage("admin");
    for (const title of ["Opening (Gathering) Hymn", "Response Hymn (after the sermon)", "Benediction"]) await openCard(user, title);
    expect(screen.getAllByText(THEME_NOTE)).toHaveLength(1);
  });

  it("shows the server's 422 above the footer, keeps the edits and toasts nothing", async () => {
    const message = "Checklist points cannot contain control characters.";
    const { user } = renderPage("admin", { "PATCH /rubric": fakeError(422, "invalid_rubric", message) });
    const card = await openCard(user, "Benediction");
    await user.type(within(card).getByRole("textbox", { name: "Point 1 of Benediction" }), "!");
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    const alert = await screen.findByText(message);
    await waitFor(() => expect(alert.closest("[data-slot=alert]")).toHaveFocus());
    expect(alert.closest("[data-slot=alert]")!.nextElementSibling).toContainElement(screen.getByRole("button", { name: "Save rubric" }));
    expect(points(card)[0]).toBe("Benediction point one!");
    expect(document.querySelector("[data-sonner-toast]")).toBeNull();
  });

  it("asks before resetting everything, sends null for each customized item, cannot be closed while it runs", async () => {
    let finish: (value: unknown) => void = () => {};
    const { api, user } = renderPage("admin", {
      "GET /rubric": rubric({ hymns: { closing: ["Ours."] }, prefer_familiar: false }),
      "PATCH /rubric": () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    });
    await user.click(await screen.findByRole("button", { name: "Reset all to defaults" }));
    const dialog = await screen.findByRole("alertdialog", { name: RESET_ALL_TITLE });
    expect(dialog).toHaveTextContent("Your church's checklists and preferences go back to the shared defaults.");
    await user.click(within(dialog).getByRole("button", { name: "Reset all" }));
    await user.keyboard("{Escape}");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.getByRole("alertdialog", { name: RESET_ALL_TITLE })).toBeInTheDocument();
    expect(patches(api)[0].body).toEqual({ hymns: { closing: null }, prefer_familiar: null });
    finish(rubric());
    expect(await screen.findByText(RUBRIC_RESET)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByRole("switch", { name: "Prefer familiar hymns" })).toBeChecked();
    expect(screen.queryByRole("button", { name: "Reset all to defaults" })).toBeNull();
    await waitFor(() => expect(screen.getByRole("heading", { name: "Service rubric" })).toHaveFocus());
  });

  it("toasts a role 403, refetches the profile and does not report the church as lost", async () => {
    const lost = vi.fn();
    const off = authEvents.onChurchAccessLost(lost);
    const { user, queryClient } = renderPage("admin", { "PATCH /rubric": fakeError(403, "forbidden", "Only church admins can do this.") });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("switch", { name: "Prefer familiar hymns" }));
    await user.click(screen.getByRole("button", { name: "Save rubric" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    expect(invalidate).toHaveBeenCalledWith({ queryKey: keys.churchProfile(church().id) });
    expect(lost).not.toHaveBeenCalled();
    off();
  });

  it("rebases on newer data and asks before leaving with unsaved edits", async () => {
    const { user, queryClient } = renderPage("admin");
    const year = await screen.findByLabelText("Prefer hymns written before");
    await user.click(screen.getByRole("switch", { name: "Prefer familiar hymns" }));
    queryClient.setQueryData(keys.rubric(church().id), rubric({ prefer_before_year: 1900 }));
    await waitFor(() => expect(year).toHaveValue("1900"));
    expect(screen.getByRole("switch", { name: "Prefer familiar hymns" })).not.toBeChecked();
    await user.click(screen.getByRole("link", { name: "Contacts" }));
    const dialog = await screen.findByRole("alertdialog", { name: DISCARD_TITLE });
    await user.click(within(dialog).getByRole("button", { name: "Discard changes" }));
    expect(testRouter.push).toHaveBeenCalledWith("/settings/contacts");
  });

  it("shows the error state with Retry when the rubric cannot be read", async () => {
    renderPage("admin", { "GET /rubric": fakeError(500, "internal_error", "Something went wrong.") });
    expect(await screen.findByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/rubric-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the route does not exist yet):
```
 FAIL  |dom| src/components/settings/rubric-settings-page.test.tsx [ src/components/settings/rubric-settings-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the card, the page and its route**

**Create `frontend/src/components/settings/checklist-card.tsx`:**

````tsx
"use client";

import { ChevronDownIcon, XIcon } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Textarea } from "@/components/ui/textarea";
import { AT_MOST_POINTS, MAX_POINT_LENGTH, MAX_POINTS, type Checklist } from "@/lib/settings/rubric";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

export const THEME_NOTE =
  "The builder first gathers opening and closing hymns by theme (gathering, praise, sending and similar). This checklist then guides which of them the AI suggests.";

/** The id of a checklist's point `index` (the page moves focus to it). */
export const pointId = (list: Checklist, index: number) => `rubric-${list.key}-${index}`;

/** A pasted or typed line break becomes a space: a point is one line (the server's whitespace rule). */
const oneLine = (text: string) => text.replace(/\r\n|\r|\n/g, " ");

function Point({
  list,
  index,
  value,
  onChange,
  onEnter,
  onRemove,
}: {
  list: Checklist;
  index: number;
  value: string;
  onChange: (value: string) => void;
  onEnter: () => void;
  onRemove: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value);
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    event.preventDefault(); // Enter adds a point below instead of a line break
    onEnter();
  };
  return (
    <li className="flex items-start gap-1">
      <Textarea
        id={pointId(list, index)}
        ref={ref}
        rows={1}
        value={value}
        maxLength={MAX_POINT_LENGTH}
        aria-label={`Point ${index + 1} of ${list.label}`}
        className="min-h-11 flex-1 resize-none md:min-h-9"
        onChange={(e) => onChange(oneLine(e.target.value))}
        onKeyDown={onKeyDown}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-11 shrink-0 md:size-9"
        aria-label={`Remove point ${index + 1} from ${list.label}`}
        onClick={onRemove}
      >
        <XIcon aria-hidden="true" />
      </Button>
    </li>
  );
}

/**
 * One checklist of the rubric (slice 6a-3a; 6a spec UX §6): "A good
 * {Label}:" and its points. Owners and admins edit each point (Enter adds one
 * below, a line break becomes a space), remove one, add one (at most 12) and
 * put the default points back (unsaved until **Save rubric**); members read
 * the points as text. The **Customized** badge follows the points.
 */
export function ChecklistCard({
  list,
  points,
  defaultPoints,
  customized,
  admin,
  open,
  onOpenChange,
  onChange,
  onFocusPoint,
  error,
  note,
}: {
  list: Checklist;
  points: readonly string[];
  defaultPoints: readonly string[];
  customized: boolean;
  admin: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChange: (points: string[]) => void;
  /** Focus point `index` once it is on the page; null for the card's **Add a point** button. */
  onFocusPoint: (index: number | null) => void;
  error?: string;
  note?: string;
}) {
  const full = points.length >= MAX_POINTS;
  const errorId = `rubric-${list.key}-error`;
  const insert = (index: number) => {
    if (full) return;
    onChange([...points.slice(0, index), "", ...points.slice(index)]);
    onFocusPoint(index);
  };
  const remove = (index: number) => {
    const next = points.filter((_p, i) => i !== index);
    onChange(next);
    onFocusPoint(next.length === 0 ? null : Math.min(index, next.length - 1));
  };
  return (
    <Collapsible open={open} onOpenChange={onOpenChange} className="rounded-lg border">
      <CollapsibleTrigger className="flex min-h-11 w-full items-center gap-2 rounded-lg px-4 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="min-w-0 flex-1 text-sm font-medium">{list.label}</span>
        {customized ? <Badge variant="secondary">Customized</Badge> : null}
        <ChevronDownIcon aria-hidden="true" className={cn("size-4 shrink-0 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-2 px-4 pb-4">
        <p id={`rubric-${list.key}-intro`} className="text-sm">{`A good ${list.label}:`}</p>
        {admin ? (
          <ol aria-labelledby={`rubric-${list.key}-intro`} aria-describedby={error ? errorId : undefined} className="grid gap-2">
            {points.map((point, index) => (
              <Point
                key={index}
                list={list}
                index={index}
                value={point}
                onChange={(value) => onChange(points.map((p, i) => (i === index ? value : p)))}
                onEnter={() => insert(index + 1)}
                onRemove={() => remove(index)}
              />
            ))}
          </ol>
        ) : (
          <ul aria-labelledby={`rubric-${list.key}-intro`} className="grid list-disc gap-1 pl-5 text-sm">
            {points.map((point, index) => (
              <li key={index} className="break-words">
                {point}
              </li>
            ))}
          </ul>
        )}
        {error ? (
          <p id={errorId} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        {note ? <p className="text-sm text-muted-foreground">{note}</p> : null}
        {admin ? (
          <div className="flex flex-wrap items-center gap-x-4">
            <Button
              type="button"
              variant="link"
              id={`rubric-${list.key}-add`}
              className="h-11 px-0 md:h-auto"
              disabled={full}
              onClick={() => insert(points.length)}
            >
              Add a point
            </Button>
            <Button
              type="button"
              variant="link"
              className="h-11 px-0 md:h-auto"
              disabled={points.length === defaultPoints.length && points.every((p, i) => p === defaultPoints[i])}
              onClick={() => {
                onChange([...defaultPoints]);
              }}
            >
              Reset to default
            </Button>
            {full ? <p className="w-full text-sm text-muted-foreground">{AT_MOST_POINTS}</p> : null}
          </div>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
}
````

**Create `frontend/src/components/settings/rubric-settings-page.tsx`:**

````tsx
"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import type { Rubric } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { isInvalidRubric, useRubric, useSaveRubric } from "@/lib/queries/rubric";
import {
  changedItems,
  checklistCustomized,
  CHECKLISTS,
  rebaseRubric,
  resetAllPatch,
  rubricErrors,
  rubricFormFrom,
  rubricPatch,
  type Checklist,
  type ChecklistKey,
  type RubricForm,
} from "@/lib/settings/rubric";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

import { ChecklistCard, pointId, THEME_NOTE } from "./checklist-card";

export const RUBRIC_INTRO =
  "What makes a good hymn or prayer at your church. The AI follows these checklists when it suggests hymns and writes liturgy. How each prayer is laid out (Leader and People lines, length, “Amen”) stays in Liturgy prompts.";
export const ADMINS_ONLY = "Only admins can edit the rubric. You can read it below.";
export const YEAR_HELP =
  "Hymns with older words are suggested first. This is a preference, not a filter: a newer hymn can still be suggested when it fits clearly better, and the builder shows its year.";
export const FAMILIAR_HELP = "Hymns found in many hymnals are suggested first.";
export const RESET_ALL_TITLE = "Reset the rubric?";
const RESET_ALL_BODY = "Your church's checklists and preferences go back to the shared defaults.";

/** Open from `md` (48rem), closed below it, as the page first renders (6a spec UX §6). */
function openAtFirst(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function" && window.matchMedia("(min-width: 48rem)").matches;
}

/**
 * `/settings/rubric` (slice 6a-3a; 6a spec UX §6): the church's service
 * rubric, the checklists the AI follows when it suggests hymns and writes
 * liturgy, and two hymn preferences. Every member reads it; owners and admins
 * edit it and save one sparse `PATCH /rubric` (an item put back to its
 * default is sent as null), or reset it all (confirmed). 6a's rules for
 * settings forms: newer server data rebases the form, and leaving with
 * unsaved edits asks first (`LeaveGuard`).
 */
export function RubricSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const rubric = useRubric();
  const headingRef = useRef<HTMLHeadingElement>(null);
  let body: ReactNode;
  if (rubric.data) {
    body = <RubricFormView out={rubric.data} admin={admin} headingRef={headingRef} />;
  } else if (rubric.isError) {
    body = <ErrorState error={rubric.error} onRetry={() => void rubric.refetch()} retrying={rubric.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="rubric-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="rubric-title" ref={headingRef} tabIndex={-1} className="text-lg font-semibold outline-none">
          Service rubric
        </h2>
        <p className="text-sm text-muted-foreground">{RUBRIC_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: Rubric; baseline: RubricForm; form: RubricForm };

function RubricFormView({ out, admin, headingRef }: { out: Rubric; admin: boolean; headingRef: RefObject<HTMLHeadingElement | null> }) {
  const save = useSaveRubric();
  const reset = useSaveRubric();
  const keyboardOpen = useKeyboardOpen();
  const [thisYear] = useState(() => new Date().getFullYear());
  const [state, setState] = useState<FormState>(() => {
    const form = rubricFormFrom(out.rubric);
    return { source: out, baseline: form, form };
  });
  const [open, setOpen] = useState(
    () => Object.fromEntries(CHECKLISTS.map((list) => [list.key, openAtFirst()])) as Record<ChecklistKey, boolean>,
  );
  const [serverError, setServerError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const focusTarget = useRef<string | null>(null);
  const resetDone = useRef(false);
  const { form, baseline } = state;
  const pending = save.isPending || reset.isPending;
  const errors = admin ? rubricErrors(form, thisYear) : {};
  const dirty = admin && changedItems(baseline, form).length > 0;
  const canSave = dirty && Object.keys(errors).length === 0;
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : rubricFormFrom(out.rubric);
  const defaults = rubricFormFrom(out.defaults);

  // Newer server data (a refetch, or this page's own save in the cache): rebase (6a).
  if (out !== state.source) {
    const next = rubricFormFrom(out.rubric);
    setState({ source: out, baseline: next, form: rebaseRubric(baseline, form, next) });
  }

  // A point added or removed (or the server's message): focused once it is on the page.
  useEffect(() => {
    if (focusTarget.current === null) return;
    document.getElementById(focusTarget.current)?.focus();
    focusTarget.current = null;
  });

  const edit = (change: (f: RubricForm) => RubricForm) => {
    setState((s) => ({ ...s, form: change(s.form) }));
    setServerError(null);
  };
  const setPoints = (list: Checklist, points: string[]) =>
    edit((f) => ({ ...f, checklists: { ...f.checklists, [list.key]: points } }));

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending || !canSave) return;
    const sent = form;
    save.mutate(
      { patch: rubricPatch(baseline, sent, out.defaults) },
      {
        // What was typed while saving stays; everything else shows what was stored.
        onSuccess: (saved) =>
          setState((s) => {
            const next = rubricFormFrom(saved.rubric);
            return { source: saved, baseline: next, form: rebaseRubric(sent, s.form, next) };
          }),
        onError: (e) => {
          if (!isInvalidRubric(e)) return;
          setServerError(e.message);
          focusTarget.current = "rubric-server-error";
        },
      },
    );
  }

  function onResetAll() {
    if (pending) return;
    resetDone.current = false;
    reset.mutate(
      { patch: resetAllPatch(out.customized), reset: true },
      {
        onSuccess: (saved) => {
          const next = rubricFormFrom(saved.rubric);
          setState({ source: saved, baseline: next, form: next });
          setServerError(null);
          resetDone.current = true;
          setConfirming(false);
        },
        onError: () => setConfirming(false),
      },
    );
  }

  const yearCustomized = shown.prefer_before_year.trim() !== defaults.prefer_before_year;
  const familiarCustomized = shown.prefer_familiar !== defaults.prefer_familiar;
  const card = (list: Checklist) => (
    <ChecklistCard
      key={list.key}
      list={list}
      points={shown.checklists[list.key]}
      defaultPoints={defaults.checklists[list.key]}
      customized={checklistCustomized(shown, out.defaults, list)}
      admin={admin}
      open={open[list.key] || Boolean(errors[list.key])}
      onOpenChange={(next) => setOpen((o) => ({ ...o, [list.key]: next }))}
      onChange={(points) => setPoints(list, points)}
      onFocusPoint={(index) => {
        focusTarget.current = index === null ? `rubric-${list.key}-add` : pointId(list, index);
      }}
      error={errors[list.key]}
      note={list.key === "hymns.opening" || list.key === "hymns.closing" ? THEME_NOTE : undefined}
    />
  );

  return (
    <form onSubmit={onSubmit} className="grid gap-4" aria-label="Service rubric">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      <fieldset className="grid gap-4 rounded-lg border p-4">
        <legend className="px-1 text-base font-medium">Hymn preferences</legend>
        <div className="grid gap-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <Label htmlFor="rubric-year">Prefer hymns written before</Label>
            {yearCustomized ? <Badge variant="secondary">Customized</Badge> : null}
          </div>
          <Input
            id="rubric-year"
            inputMode="numeric"
            maxLength={4}
            value={shown.prefer_before_year}
            readOnly={!admin}
            className="h-11 w-28"
            aria-invalid={errors.prefer_before_year ? true : undefined}
            aria-describedby={["rubric-year-help", errors.prefer_before_year && "rubric-year-error"].filter(Boolean).join(" ")}
            onChange={(e) => edit((f) => ({ ...f, prefer_before_year: e.target.value }))}
          />
          <p id="rubric-year-help" className="text-sm text-muted-foreground">
            {YEAR_HELP}
          </p>
          {errors.prefer_before_year ? (
            <p id="rubric-year-error" role="alert" className="text-sm text-destructive">
              {errors.prefer_before_year}
            </p>
          ) : null}
          {admin && yearCustomized ? (
            <Button
              type="button"
              variant="link"
              className="h-11 justify-self-start px-0 md:h-auto"
              aria-label="Reset to default: Prefer hymns written before"
              onClick={() => edit((f) => ({ ...f, prefer_before_year: defaults.prefer_before_year }))}
            >
              Reset to default
            </Button>
          ) : null}
        </div>
        <div className="grid gap-1.5">
          <div className="flex flex-wrap items-center gap-3">
            <Switch
              id="rubric-familiar"
              checked={shown.prefer_familiar}
              disabled={!admin}
              aria-describedby="rubric-familiar-help"
              onCheckedChange={(checked) => edit((f) => ({ ...f, prefer_familiar: checked }))}
              className="after:-inset-y-3.5"
            />
            <Label htmlFor="rubric-familiar">Prefer familiar hymns</Label>
            {familiarCustomized ? <Badge variant="secondary">Customized</Badge> : null}
          </div>
          <p id="rubric-familiar-help" className="text-sm text-muted-foreground">
            {FAMILIAR_HELP}
          </p>
          {admin && familiarCustomized ? (
            <Button
              type="button"
              variant="link"
              className="h-11 justify-self-start px-0 md:h-auto"
              aria-label="Reset to default: Prefer familiar hymns"
              onClick={() => edit((f) => ({ ...f, prefer_familiar: defaults.prefer_familiar }))}
            >
              Reset to default
            </Button>
          ) : null}
        </div>
      </fieldset>
      <h3 className="text-base font-medium">Hymns</h3>
      {CHECKLISTS.filter((list) => list.group === "hymns").map(card)}
      <h3 className="text-base font-medium">Prayers</h3>
      {CHECKLISTS.filter((list) => list.group === "prayers").map(card)}
      {admin && serverError ? (
        <Alert id="rubric-server-error" tabIndex={-1} variant="destructive" className="outline-none">
          <AlertDescription>{serverError}</AlertDescription>
        </Alert>
      ) : null}
      {admin ? (
        <div
          data-keyboard-open={keyboardOpen ? "" : undefined}
          className={cn(
            "sticky bottom-0 z-10 flex flex-wrap gap-2 border-t bg-background/95 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
            // Below md with the iPhone keyboard open the footer sits after the last card, reachable and not covering the box.
            keyboardOpen && "max-md:static",
          )}
        >
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!canSave || reset.isPending}>
            Save rubric
          </PendingButton>
          {out.customized.length > 0 ? (
            <Button type="button" variant="outline" size="touch" className="w-full sm:w-fit" disabled={pending} onClick={() => setConfirming(true)}>
              Reset all to defaults
            </Button>
          ) : null}
        </div>
      ) : null}
      <ConfirmDialog
        open={confirming}
        onOpenChange={(next) => {
          if (!next && !reset.isPending) setConfirming(false);
        }}
        title={RESET_ALL_TITLE}
        description={RESET_ALL_BODY}
        confirmLabel="Reset all"
        destructive
        pending={reset.isPending}
        onConfirm={onResetAll}
        // After a reset the button that opened it is gone (nothing is customized): the page's heading takes focus.
        finalFocus={() => (resetDone.current ? headingRef.current : true)}
      />
      <LeaveGuard when={dirty} />
    </form>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/rubric/page.tsx`:**

````tsx
"use client";

import { RubricSettingsPage } from "@/components/settings/rubric-settings-page";

/** Settings → Rubric: what makes a good hymn or prayer at the church (slice 6a-3a; F §4.1). */
export default function RubricSettingsRoute() {
  return <RubricSettingsPage />;
}
````

- [ ] **Step 4: See them pass (three runs), the types, lint and the suite**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/settings/rubric-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected** (no flaky run):
```
      Tests  11 passed (11)
      Tests  11 passed (11)
      Tests  11 passed (11)
```
```
typecheck 0
lint 0
```
```
 Test Files  107 passed (107)
      Tests  907 passed (907)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/rubric-settings-page.test.tsx frontend/src/components/settings/checklist-card.tsx frontend/src/components/settings/rubric-settings-page.tsx 'frontend/src/app/(signed-in)/(church)/settings/rubric/page.tsx'
git commit -q -m "Slice 6a-3a: Settings → Rubric" -m "/settings/rubric: the two hymn preferences and the eleven checklists
(three hymn slots with the theme note under Opening and Closing, eight
prayers), each point a one-line box (Enter adds one below, at most 12),
Customized and Reset to default per item; one Save rubric sends only
what changed, null for an item back on its default; a confirmed Reset
all to defaults; read-only for members. The server's 422 shows above
the footer; newer data rebases the form; leaving with unsaved edits
asks first." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `907 passed` in 107 files.

### Task 9: Liturgy and Rubric in the Settings nav; Bulletin settings at `/settings/bulletin` (answers 3 and 6; clarifications 2, 10)

**Files:**
- Create: `frontend/src/app/(signed-in)/(church)/settings/bulletin/page.tsx`
- Modify: `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, `frontend/src/components/settings/church-settings-page.test.tsx`, `frontend/src/components/settings/sections.ts` (rewritten), `frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx` (rewritten), `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, `frontend/src/components/builder/review/printed-card.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx`

- [ ] **Step 1: Update the tests**

The Settings layout's test expects the seven sections in the new order, marks Liturgy, Rubric and Bulletin current on their pages, and checks that the old address opens `/settings/bulletin`. The Bulletin settings tests render the page inside the Settings layout at its new route, with **Back to the builder** (`/builder`). The builder's two links and the Church page's leave-guard test expect `/settings/bulletin`.

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
````

**with:**

````tsx

import OldBulletinSettingsRoute from "@/app/(signed-in)/(church)/bulletin-settings/page";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
      ["Bulletin", "/bulletin-settings"],
````

**with:**

````tsx
      ["Liturgy", "/settings/liturgy"],
      ["Rubric", "/settings/rubric"],
      ["Bulletin", "/settings/bulletin"],
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    ["/settings/contacts", "Contacts"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 6a-2, 5b-1, 5b-2): %s", (path, label) => {
````

**with:**

````tsx
    ["/settings/liturgy", "Liturgy"],
    ["/settings/rubric", "Rubric"],
    ["/settings/bulletin", "Bulletin"],
    ["/settings/contacts", "Contacts"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 6a-2, 6a-3a, 5b-1, 5b-2): %s", (path, label) => {
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(5);
    renderWithProviders(<SettingsHome />, { path: "/settings" });
    expect(testRouter.replace).toHaveBeenCalledWith("/settings/church");
  });
````

**with:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(7);
    renderWithProviders(<SettingsHome />, { path: "/settings" });
    expect(testRouter.replace).toHaveBeenCalledWith("/settings/church");
  });

  it("opens Settings → Bulletin from the old Bulletin settings address (slice 6a-3a)", () => {
    renderWithProviders(<OldBulletinSettingsRoute />, { path: "/bulletin-settings" });
    expect(testRouter.replace).toHaveBeenCalledWith("/settings/bulletin");
  });
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
 * The page renders as the route does, with a Toaster.
````

**with:**

````tsx
 * Since slice 6a-3a it is Settings → Bulletin, so it renders inside the
 * Settings layout, as the route does, with a Toaster.
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
import BulletinSettingsRoute from "@/app/(signed-in)/(church)/bulletin-settings/page";
````

**with:**

````tsx
import BulletinSettingsRoute from "@/app/(signed-in)/(church)/settings/bulletin/page";
import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
      <BulletinSettingsRoute />
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/bulletin-settings", queryClient },
````

**with:**

````tsx
      <SettingsLayout>
        <BulletinSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/bulletin", queryClient },
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("main")).getByRole("link", { name: "Back to Review & send" })).toHaveAttribute(
      "href",
      "/builder/review",
````

**with:**

````tsx
    expect(within(screen.getByRole("main")).getByRole("link", { name: "Back to the builder" })).toHaveAttribute(
      "href",
      "/builder",
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to Review & send" });
    expect(leaveWarned()).toBe(false);
````

**with:**

````tsx
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to the builder" });
    expect(leaveWarned()).toBe(false);
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
    expect(testRouter.push).toHaveBeenCalledWith("/builder/review");
````

**with:**

````tsx
    expect(testRouter.push).toHaveBeenCalledWith("/builder");
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx`, replace:**

````tsx
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to Review & send" });
````

**with:**

````tsx
    const back = within(screen.getByRole("main")).getByRole("link", { name: "Back to the builder" });
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(link).toHaveAttribute("href", "/bulletin-settings");
````

**with:**

````tsx
    expect(link).toHaveAttribute("href", "/settings/bulletin");
````

**In `frontend/src/components/builder/bulletin/bulletin-step.test.tsx`, replace:**

````tsx
    expect(within(step).getByRole("link", { name: "Bulletin settings" })).toHaveAttribute("href", "/bulletin-settings");
````

**with:**

````tsx
    expect(within(step).getByRole("link", { name: "Bulletin settings" })).toHaveAttribute("href", "/settings/bulletin");
````

**In `frontend/src/components/settings/church-settings-page.test.tsx`, replace:**

````tsx
    expect(testRouter.push).toHaveBeenCalledWith("/bulletin-settings");
````

**with:**

````tsx
    expect(testRouter.push).toHaveBeenCalledWith("/settings/bulletin");
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx src/components/bulletin-settings/bulletin-settings-page.test.tsx src/components/builder/review/review-send-step.test.tsx src/components/builder/bulletin/bulletin-step.test.tsx src/components/settings/church-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the Bulletin settings tests import the new route, which does not exist yet, so that file cannot load; the nav still has five sections and the links the old address):
```
   × Settings → Church (slice 6a-1) > asks before leaving with unsaved edits, through the Settings nav
   × the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 5b-1, 5b-2): /settings/liturgy
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 5b-1, 5b-2): /settings/rubric
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 6a-3a, 5b-1, 5b-2): /settings/bulletin
   × the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church
   × the Settings area (slice 6a-1) > opens Settings → Bulletin from the old Bulletin settings address (slice 6a-3a)
   × Review & send: the printed bulletin (printed bulletin PR 1) > lists the bulletin settings still blank and links to them (printed bulletin PR 2a)
   × the Bulletin step (printed bulletin PR 2b) > shows the music, who leads, the announcements and the reading text, all optional, and stores what is typed
 FAIL  |dom| src/components/bulletin-settings/bulletin-settings-page.test.tsx [ src/components/bulletin-settings/bulletin-settings-page.test.tsx ]
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 9 ⎯⎯⎯⎯⎯⎯⎯
      Tests  9 failed | 63 passed (72)
```

- [ ] **Step 3: Write the nav, the new route, the forward and the links**

**Replace `frontend/src/components/settings/sections.ts`:**

````ts
/**
 * The Settings area's pages, in the nav's order (6a spec "Settings nav"; slice
 * 6a-1). `/settings` opens the first. 6a-2 added Hymns after Church; 6a-3a
 * adds Liturgy (the prompts) and Rubric and moves Bulletin settings in under
 * /settings (owner's 6a-3 answers of 2026-10-07: once 6a is done the order is
 * Church, Hymns, Liturgy, Prayers, Rubric, Bulletin, Contacts, Account, so
 * 6a-3b puts Prayers between Liturgy and Rubric); 5b-1 added Contacts and
 * 5b-2 Account after it (6b's People will go between them).
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
  { href: "/settings/hymns", label: "Hymns" },
  { href: "/settings/liturgy", label: "Liturgy" },
  { href: "/settings/rubric", label: "Rubric" },
  { href: "/settings/bulletin", label: "Bulletin" },
  { href: "/settings/contacts", label: "Contacts" },
  { href: "/settings/account", label: "Account" },
] as const;
````

**Create `frontend/src/app/(signed-in)/(church)/settings/bulletin/page.tsx`:**

````tsx
"use client";

import { BulletinSettingsPage } from "@/components/bulletin-settings/bulletin-settings-page";

/** Settings → Bulletin: the church's standing printed bulletin details (printed bulletin spec, PR 2a; slice 6a-3a; F §4.1). */
export default function BulletinSettingsRoute() {
  return <BulletinSettingsPage />;
}
````

**Replace `frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx`:**

````tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Skeleton } from "@/components/ui/skeleton";

/** The old address of Bulletin settings: it opens Settings → Bulletin (slice 6a-3a; owner's 6a-3 answer 3). */
export default function OldBulletinSettingsRoute() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/settings/bulletin");
  }, [router]);

  return <Skeleton aria-busy="true" className="h-40 w-full" />;
}
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
import { PageHeader } from "@/components/app/page-header";
import { PendingButton } from "@/components/app/pending-button";
````

**with:**

````tsx
import { PendingButton } from "@/components/app/pending-button";
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
const BACK_HREF = "/builder/review";
````

**with:**

````tsx
/** The builder opens the step it was last on (Bulletin or Review & send, where the links to this page are). */
const BACK_HREF = "/builder";
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
 * `/bulletin-settings` (printed bulletin spec, PR 2a; PR 2 planning answers
 * 1-3): the church's standing bulletin settings, which every member's
 * printed bulletin uses. Admins and owners edit and save the whole form;
 * members read a plain summary, with a note that only admins can edit it.
 * Until 6a folds it into Settings, the Printed bulletin card on Review & send
 * links here.
````

**with:**

````tsx
 * `/settings/bulletin` (printed bulletin spec, PR 2a; PR 2 planning answers
 * 1-3; moved into Settings by slice 6a-3a, owner's 6a-3 answer 3, and the old
 * `/bulletin-settings` forwards here): the church's standing bulletin
 * settings, which every member's printed bulletin uses. Admins and owners
 * edit and save the whole form; members read a plain summary, with a note
 * that only admins can edit it. The builder's Bulletin step and the Printed
 * bulletin card on Review & send link here; **Back to the builder** returns
 * to the step the builder was on.
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
    <main className="mx-auto grid w-full max-w-2xl content-start gap-4 px-4 py-4">
      <PageHeader
        title="Bulletin settings"
        description={PAGE_DESCRIPTION}
        actions={
          <Link href={BACK_HREF} className={buttonVariants({ variant: "outline", size: "touch" })}>
            Back to Review &amp; send
          </Link>
        }
      />
````

**with:**

````tsx
    <section aria-labelledby="bulletin-settings-title" className="grid gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="grid min-w-0 gap-1">
          <h2 id="bulletin-settings-title" className="text-lg font-semibold">
            Bulletin settings
          </h2>
          <p className="text-sm text-muted-foreground">{PAGE_DESCRIPTION}</p>
        </div>
        <Link href={BACK_HREF} className={buttonVariants({ variant: "outline", size: "touch" })}>
          Back to the builder
        </Link>
      </div>
````

**In `frontend/src/components/bulletin-settings/bulletin-settings-page.tsx`, replace:**

````tsx
    </main>
````

**with:**

````tsx
    </section>
````

**In `frontend/src/components/builder/review/printed-card.tsx`, replace:**

````tsx
      <Link href="/bulletin-settings" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
````

**with:**

````tsx
      <Link href="/settings/bulletin" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````tsx
      <Link href="/bulletin-settings" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
````

**with:**

````tsx
      <Link href="/settings/bulletin" className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}>
````

- [ ] **Step 4: See them pass, the types, lint and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx src/components/bulletin-settings/bulletin-settings-page.test.tsx src/components/builder/review/review-send-step.test.tsx src/components/builder/bulletin/bulletin-step.test.tsx src/components/settings/church-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `grep -rn '"/bulletin-settings"' frontend/src --include=*.ts --include=*.tsx | grep -v 'settings-layout.test.tsx'; echo "old address grep exit $?"` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`
**Expected** (no link to the old address is left; only the layout test renders it, to check the forward):
```
      Tests  81 passed (81)
```
```
old address grep exit 1
```
```
typecheck 0
lint 0
```
```
 Test Files  107 passed (107)
      Tests  911 passed (911)
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/settings-layout.test.tsx frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx frontend/src/components/builder/review/review-send-step.test.tsx frontend/src/components/builder/bulletin/bulletin-step.test.tsx frontend/src/components/settings/church-settings-page.test.tsx frontend/src/components/settings/sections.ts 'frontend/src/app/(signed-in)/(church)/settings/bulletin/page.tsx' 'frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx' frontend/src/components/bulletin-settings/bulletin-settings-page.tsx frontend/src/components/builder/review/printed-card.tsx frontend/src/components/builder/bulletin/bulletin-step.tsx
git commit -q -m "Slice 6a-3a: Liturgy and Rubric in the Settings nav; Bulletin settings moves to /settings/bulletin" -m "SETTINGS_SECTIONS: Church, Hymns, Liturgy, Rubric, Bulletin, Contacts,
Account (6a-3b adds Prayers after Liturgy). Bulletin settings renders
inside the Settings layout at /settings/bulletin, with Back to the
builder; the old /bulletin-settings address forwards there, and the
builder's Bulletin step and Printed bulletin card link to it." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `911 passed` in 107 files.

## Docs, verification, the PR, the merge (T10-T12)

### Task 10: Docs: the manual check items (clarification 16)

**Files:**
- Modify: `docs/manual-verification.md`

- [ ] **Step 1: Add the items**

Under "## Slice 6a", after item 15 and before "## Slice 5b". Items 16-20 are the owner's phone check after the merge (T12), 21-23 the agent's (a member's sign-in and a test church are needed for 21 and 22).

**In `docs/manual-verification.md`, replace:**

````markdown

## Slice 5b
````

**with:**

````markdown

**6a-3a (Liturgy prompts, Rubric, Bulletin).** After the 6a-3a merge the
owner's guided check covers the items marked "(owner, after 6a-3a)", one step
at a time on the phone; the results go into `docs/ops-runbook.md` → "Slice
6a-3a record". A test change to a prompt or to the rubric is made only on a
card that does not say **Customized**, and is put back with **Reset to
default** and a save in the same step, so the church's prompts and rubric end
as they began; **Reset all to defaults** is never tapped on the church's own
page. Record what the page shows, never a church id or a prompt's wording.

- [ ] (owner, after 6a-3a) **16.** **Settings** lists **Church**, **Hymns**, **Liturgy**, **Rubric**, **Bulletin**, **Contacts** and **Account**. **Liturgy** shows "Liturgy prompts" with nine cards, "Overall voice (system prompt)" first and "Section prompts" with the placeholder help above the other eight; note which cards say **Customized**. **Rubric** shows "Service rubric" with **Hymn preferences**, three **Hymns** cards and eight **Prayers** cards; note which say **Customized** and the year in "Prefer hymns written before".
- [ ] (owner, after 6a-3a) **17.** On **Liturgy**, open a card that does not say **Customized** and type **{** at the end of its text; **Save prompts**: the card shows "{Card} prompt: It has a { or } without a partner. Use {{ or }} to print a brace." and nothing is saved. Replace the **{** with the word **Amen.**; **Save prompts**: "Prompts saved." and the card says **Customized**. Then **Reset to default** on that card and **Save prompts**: "Prompts saved." and **Customized** is gone.
- [ ] (owner, after 6a-3a) **18.** On **Rubric**, open a **Prayers** card that does not say **Customized**, tap at the end of its last point and press return: a new empty point appears below; type **Test point**; **Save rubric**: "Rubric saved." and the card says **Customized**. Then **Reset to default** on that card and **Save rubric**: "Rubric saved." and **Customized** is gone. In "Prefer hymns written before" type **1400**: "The preferred year must be between 1500 and {this year}." shows and **Save rubric** cannot be tapped; type the year it showed before, and the message goes.
- [ ] (owner, after 6a-3a) **19.** **Settings** → **Bulletin** shows the bulletin settings as before, with **Back to the builder**. In **Builder** → **Bulletin**, **Bulletin settings** opens **Settings** → **Bulletin**; **Back to the builder** returns to the Bulletin step. On **Review & send** the Printed bulletin card's **Bulletin settings** opens the same page.
- [ ] (owner, after 6a-3a) **20.** At 375 px: no sideways scroll on **Liturgy**, **Rubric** or **Bulletin**; the seven section links, the cards and the buttons are easy to tap. On **Liturgy** with a card open and the iPhone keyboard up, the box being typed in is not covered and **Save prompts** can be reached by scrolling down.
- [ ] **21.** Signed in as a plain member of the same church: **Liturgy** shows "Only admins can edit the prompts. You can read them below." with read-only cards and no buttons; **Rubric** shows "Only admins can edit the rubric. You can read it below." with the points as text and no buttons; **Bulletin** shows its summary.
- [ ] **22.** In a test church, as an admin: save a Benediction prompt and generate the Benediction in the builder: the text follows it; set "Prefer hymns written before" to 1900: the builder's picker labels hymns written in or after 1900 as newer with no reload; then **Reset all to defaults** on both pages.
- [ ] **23.** Signed in, open the old address `/bulletin-settings` on the production URL: it opens **Settings** → **Bulletin**.

## Slice 5b
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat | tail -1`
**Expected** (the docs tests pass, the owner markers are still 4, no em dash was added, one file changed):
```
89 passed in <t>s
```
```
4
```
```
0
```
```
 1 file changed, 18 insertions(+)
```

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: slice 6a-3a manual checks" -m "docs/manual-verification.md, under Slice 6a, gains the 6a-3a items: the
owner's phone check after the merge (finding the pages; a test change to
a prompt and to a rubric checklist, each on a card that is not
customized and put back in the same step; the year's check; Bulletin
settings under Settings and the builder's links; the pages at 375 px
with the keyboard open) and the agent's checks (a member, generation and
the picker's year label in a test church, the old address)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `911 passed` in 107 files.

### Task 11: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `7`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 11)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/settings|/bulletin-settings")
```

**Expected** (as in the replay: the suite; three runs of `Test Files  107 passed (107)` and `Tests  911 passed (911)` with no `×` or `FAIL` line, one naming a failing test: Step 6; typecheck and lint 0; the build with the three new Settings routes and no `Error`, a font `Failed to fetch` only: say so and rely on CI):
```
1922 passed, 33 skipped in <t>s
```
```
 Test Files  107 passed (107)
      Tests  911 passed (911)
 Test Files  107 passed (107)
      Tests  911 passed (911)
 Test Files  107 passed (107)
      Tests  911 passed (911)
```
```
typecheck 0
lint 0
```
```
✓ Compiled successfully in <t>s
├ ○ /bulletin-settings
├ ○ /settings
├ ○ /settings/account
├ ○ /settings/bulletin
├ ○ /settings/church
├ ○ /settings/contacts
├ ○ /settings/hymns
├ ○ /settings/liturgy
├ ○ /settings/rubric
```

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/usecases/church_admin.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff origin/main...HEAD -- backend frontend/src | grep '^+' | grep -c '—'
python3 -c "import pathlib,sys; t=pathlib.Path('docs/superpowers/plans/2026-10-08-slice-6a3a-prompts-rubric-bulletin.md').read_text(); print(sum(t.count(c) for c in ('\u2028','\u2029','\ufffe','\uffff')))"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests backend/liturgy_prompts.py backend/service_rubric.py | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; `0` (no em dash in an added line of code or tests); `0` (no U+2028, U+2029, U+FFFE or U+FFFF in this plan); exactly these 43 paths (the 6a-2 record in the runbook and the 6a spec's later amendment ride along until merged):
```
M	backend/api/main.py
A	backend/api/routes/church_prompts.py
M	backend/api/routes/rubric.py
M	backend/api/schemas.py
M	backend/repos/churches.py
A	backend/tests/test_api_liturgy_prompts.py
M	backend/tests/test_api_rubric.py
M	backend/tests/test_church_admin.py
M	backend/tests/test_church_admin_postgres.py
M	backend/tests/test_isolation.py
M	backend/usecases/church_admin.py
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-08-slice-6a3a-prompts-rubric-bulletin.md
M	docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md
M	frontend/src/app/(signed-in)/(church)/bulletin-settings/page.tsx
A	frontend/src/app/(signed-in)/(church)/settings/bulletin/page.tsx
A	frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx
A	frontend/src/app/(signed-in)/(church)/settings/rubric/page.tsx
M	frontend/src/components/builder/bulletin/bulletin-step.test.tsx
M	frontend/src/components/builder/bulletin/bulletin-step.tsx
M	frontend/src/components/builder/review/printed-card.tsx
M	frontend/src/components/builder/review/review-send-step.test.tsx
M	frontend/src/components/bulletin-settings/bulletin-settings-page.test.tsx
M	frontend/src/components/bulletin-settings/bulletin-settings-page.tsx
A	frontend/src/components/settings/checklist-card.tsx
M	frontend/src/components/settings/church-settings-page.test.tsx
A	frontend/src/components/settings/liturgy-prompts-page.test.tsx
A	frontend/src/components/settings/liturgy-prompts-page.tsx
A	frontend/src/components/settings/rubric-settings-page.test.tsx
A	frontend/src/components/settings/rubric-settings-page.tsx
M	frontend/src/components/settings/sections.ts
M	frontend/src/components/settings/settings-layout.test.tsx
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/types.ts
A	frontend/src/lib/queries/liturgy-prompts.ts
A	frontend/src/lib/queries/rubric.ts
A	frontend/src/lib/settings/prompts.test.ts
A	frontend/src/lib/settings/prompts.ts
A	frontend/src/lib/settings/rubric.test.ts
A	frontend/src/lib/settings/rubric.ts
M	frontend/src/test/fixtures/index.ts
```
`0`; the subjects oldest first: `Runbook: slice 6a-2 record (merged; owner's phone check)`, `Spec: slice 6a-3 planning answers (owner, 2026-10-08)`, the plan commits (`WIP plan: …` and `Plan: slice 6a-3a (Liturgy prompts, Rubric, Bulletin settings in Settings)`) and any later plan commit, then T1-T10's ten subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The Liturgy prompts, Rubric and Bulletin settings changes (slice 6a-3a) are verified on this machine: backend 1922 passed, 33 skipped (1885 and 31 before); frontend 911 tests in 107 files (874 in 103 before), three runs in a row; typecheck, lint and the production build are clean. There is no database change and no new package. Settings gets **Liturgy** and **Rubric** after **Hymns**, and **Bulletin** moves under Settings (the old address and the builder's buttons lead there). Everyone can read the prompts and the rubric; you (and any admin) can change them, put one back to its default, or reset them all after a confirmation. The pull request also carries the 6a-2 record and the 6a-3 planning notes. May I open the pull request as a **draft** titled "Slice 6a-3a: Liturgy prompts, the Service rubric and Bulletin settings in Settings", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/6a3a-pr-body.md" <<'BODY'
Slice 6a-3a: Liturgy prompts, the Service rubric and Bulletin settings in Settings (the first of slice 6a-3's two PRs; owner's 6a-3 planning answers of 2026-10-07). Spec: docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md (UX §3, UX §6 and its amendments). Plan: docs/superpowers/plans/2026-10-08-slice-6a3a-prompts-rubric-bulletin.md. No database change, no new package or variable.

- usecases/church_admin: get_prompts and save_prompts (slice 4's clean_prompt_overrides and check_template, imported), get_rubric and update_rubric (service_rubric's checks); each write under the church-row lock with the caller's role re-read (Postgres tests). repos/churches: merge_settings, and a session on set_church_prompts and update_church_rubric.
- GET and PUT /church/liturgy-prompts (members read, owners and admins save; {} resets all); GET and PATCH /rubric through the usecases, with the additive defaults.
- Settings → Liturgy prompts and Settings → Rubric (collapsible cards, Customized, Reset to default, a sticky Save, a confirmed Reset all, read-only for members). Settings → Bulletin at /settings/bulletin; /bulletin-settings forwards there; the builder's links follow. The Settings nav: Church, Hymns, Liturgy, Rubric, Bulletin, Contacts, Account.
- docs/manual-verification.md: the 6a-3a items under "Slice 6a".
- Rides along: the 6a-2 record in docs/ops-runbook.md and the 6a spec's 6a-3 amendment.

Later: 6a-3b (Prayers, between Liturgy and Rubric), 6b (People).

Tests: backend 1885 → 1922 passed, 31 → 33 skipped; frontend 874 → 911 in 103 → 107 files

After merge (Task 12): a short check on the owner's phone, then a "Slice 6a-3a record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 6a-3a: Liturgy prompts, the Service rubric and Bulletin settings in Settings" \
  --body-file "<scratch>/6a3a-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1922 passed, 33 skipped`, backend-postgres `33 passed, 1922 deselected`, frontend `911 passed` in 107 files. Then send: "PR #<N> is green: backend 1922 passed, 33 skipped (the two new Postgres tests passed in their own job); 911 frontend tests in 107 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_church_admin.py` (the prompts), `test_church_settings.py`, `test_churches_repo.py`, `streamlit_tests/` | T1 |
| `test_church_admin.py` (the rubric), `test_api_hymns.py`, `test_api_hymn_suggestions.py` | T2 |
| `test_api_liturgy_prompts.py`, `test_api_rubric.py`, `test_isolation.py`, `test_openapi_contract.py`, `test_route_guards.py` | T3 |
| `test_church_admin_postgres.py` (CI `backend-postgres`) | T4 (the lock itself: T1, T2) |
| `prompts.test.ts`, `typecheck` in `lib/queries/liturgy-prompts.ts` | T5 |
| `liturgy-prompts-page.test.tsx` | T6 |
| `rubric.test.ts`, `typecheck` in `lib/queries/rubric.ts` | T7 |
| `rubric-settings-page.test.tsx` | T8 |
| `settings-layout.test.tsx`, `bulletin-settings-page.test.tsx`, `review-send-step.test.tsx`, `bulletin-step.test.tsx`, `church-settings-page.test.tsx` | T9 |
| `test_slice1_docs.py`, `test_docs.py` | T10 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 6a-3a final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1922 passed, 33 skipped`; frontend `911 passed` in 107 files.

### Task 12: Merge, the owner's phone check (five steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0007_bulletin_images`); Railway serves the prompts route and the rubric's locked write, Vercel the pages. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church, signed in as its owner. **A test change to a prompt or to the rubric is made only on a card that does not say Customized, and is put back with Reset to default and a save in the same step, so the church's prompts and rubric end exactly as they began; Reset all to defaults is never tapped; the year is only mistyped and retyped, never saved.** If a step's put-back did not happen (the save failed, the owner stopped), the next message helps the owner put it back before anything else. The agent writes each result into `<scratch>/6a3a-t12-results.md` (not committed). Record which cards were customized and what the page showed, never a church id, an email address or the wording of a prompt or a point.

**Files:** Modify (the records PR, Step 9): `docs/ops-runbook.md`: insert `### Slice 6a-3a record` right before `## Backups` (after the last record above it, today `### Slice 6a-2 record`, whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 6a-3a: Liturgy prompts, the Service rubric and Bulletin settings in Settings) is ready, green and up to date with main. There is no database change; your prompts, rubric and bulletin settings stay exactly as they are until someone saves a change. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway and Vercel before Step 2; a failed deploy keeps the old version running (Step R).

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 5: finding the pages (manual-verification item 16)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Tap **Settings** at the top: are the sections **Church**, **Hymns**, **Liturgy**, **Rubric**, **Bulletin**, **Contacts** and **Account**? Tap **Liturgy**: does it say "Liturgy prompts", with nine cards ("Overall voice (system prompt)" first, then a "Section prompts" heading over the other eight)? Which cards say **Customized**? Now tap **Rubric**: does it say "Service rubric", with "Hymn preferences", three cards under **Hymns** and eight under **Prayers**? Which say **Customized**, and what year is in "Prefer hymns written before"? Please answer with the card names and the year only; do not change anything yet.

Record the sections, the customized cards on each page and the year. **Steps 3 and 4 use a card that is not customized; if every card on a page is customized, that step's save part is skipped.**

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 5: a prompt, changed and put back (item 17)**

Pick, from Step 2's answer, a **Liturgy** card that is not customized (the Offertory Prayer if it is not; else the first that is not), and fill in its name for `<card>`:

> On **Liturgy**, tap **<card>** to open it. Tap at the very end of its text and type a space and **{** (an opening curly brace). Tap **Save prompts** (at the bottom; scroll down if the keyboard hides it): does the card show "<card> prompt: It has a { or } without a partner. Use {{ or }} to print a brace." and nothing say "Prompts saved."? Now delete the **{** and type **Amen.** in its place, then tap **Save prompts**: does it say "Prompts saved.", and does the card say **Customized**? Last, put it back: tap **Reset to default** under that card's text, then **Save prompts**: does it say "Prompts saved." again, and is **Customized** gone from that card?

If the last save did not happen, help the owner tap **Reset to default** and **Save prompts** on that card before Step 4. Record the four answers.

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 5: a checklist, changed and put back, and the year (item 18)**

Pick a **Prayers** card on **Rubric** that is not customized (the Offertory Prayer if it is not), as `<card>`, and Step 2's year as `<year>`:

> On **Rubric**, tap **<card>** to open it. Tap at the end of its last point and press the return key: does a new empty point appear below, with the cursor in it? Type **Test point** and tap **Save rubric**: does it say "Rubric saved.", and does the card say **Customized**? Now put it back: tap **Reset to default** in that card, then **Save rubric**: "Rubric saved." again, and is **Customized** gone? Last, the year: in "Prefer hymns written before" replace the year with **1400**: does "The preferred year must be between 1500 and <this year>." show under it, and is **Save rubric** greyed out? Put **<year>** back in the box: does the message go? (Do not save; nothing has changed.)

If the put-back did not happen, help the owner tap **Reset to default** and **Save rubric** on that card before Step 5. Record the answers.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 5: Bulletin settings (item 19)**

> Tap **Bulletin** in Settings: are your bulletin settings there as before, with a **Back to the builder** button at the top? Tap **Builder**, go to the **Bulletin** step and tap **Bulletin settings** at its end: does it open **Settings** → **Bulletin**? Tap **Back to the builder**: are you back on the Bulletin step? Do not change anything on the page.

- [ ] **Step 6 (OWNER, then agent): Phone, step 5 of 5: the phone screen (item 20)**

> In **Settings**: are the seven section links easy to tap, with no sideways scrolling on **Liturgy**, **Rubric** or **Bulletin**? On **Liturgy**, open any card and tap inside its text so the keyboard opens, without typing: is the text you tapped in still visible above the keyboard, and can you reach **Save prompts** by scrolling down (it stays greyed out, since nothing changed)? Tap outside the text to close the keyboard.

- [ ] **Step 7 (agent): The agent's own checks (items 21-23)**

On the production URL. Item 23 (the old address `/bulletin-settings` opens Settings → Bulletin) needs only a signed-in session. Items 21 (a plain member's read-only pages) and 22 (generation and the picker's year label, then Reset all, in a test church the agent may change: one of the two slice 1 test churches the owner kept, never the owner's own church) need a test account; without one, record "not run" and why.

- [ ] **Step 8 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/6a3a-t12-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 9 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 6a-2 record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 6a-3a record

Slice 6a-3a (Liturgy prompts, the Service rubric and Bulletin settings in
Settings: Liturgy and Rubric in the Settings sections after Hymns, and
Bulletin moved under Settings at `/settings/bulletin`, the old address
forwarding there and the builder's links following; every member reads
the prompts and the rubric, owners and admins change them, put an item
back to its default or reset them all after a confirmation; `GET` and
`PUT /church/liturgy-prompts`, and `PATCH /rubric` now under the
church-row lock with the caller's role re-read and `defaults` in both
rubric answers) merged as PR #<N>, the first of slice 6a-3's two PRs
(owner's 6a-3 planning answers of 2026-10-07). No database change and no
new package; production stays at `0007_bulletin_images`. The owner's
check was five steps on a phone, covering the "(owner, after 6a-3a)"
items of `docs/manual-verification.md` → "Slice 6a". Each test change was
made on a card that was not customized and put back in the same step;
Reset all was never tapped, and the church's prompts and rubric ended as
they began. Kept (owner's answer 5): the opening and closing theme
keywords, with the note under those two rubric cards. No church id,
email address or prompt wording is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main`: backend, backend-postgres and frontend success | <date> |
| 1. Finding the pages (phone: <phone and browser>) | <The seven sections listed; Liturgy: nine cards, customized: <names or none>; Rubric: customized: <names or none>, year <year>. / …> | <date> |
| 2. A prompt | <On <card> (not customized): the stray brace refused in the card with nothing saved; Amen saved (Customized); Reset to default and saved (Customized gone). / …> | <date> |
| 3. A checklist and the year | <On <card> (not customized): return added a point below; saved (Customized); Reset to default and saved (Customized gone); 1400 refused in the box with Save greyed out, the year put back unsaved. / …> | <date> |
| 4. Bulletin settings | <Under Settings as before, with Back to the builder; the Bulletin step's button opened it and Back returned there. / …> | <date> |
| 5. The phone | <Easy to tap, no sideways scroll; the box stayed visible with the keyboard open and Save prompts was reachable. / …> | <date> |
| Agent checks | <Item 23: the old address opened Settings → Bulletin. Items 21 and 22: <results> / not run: <why>.> | <date> |
| Follow-ups | <None. / One line per follow-up.> Kept (answer 5): the theme keywords, with the note. Next: 6a-3b (Prayers, between Liturgy and Rubric), 6b (People), Hear it from the pews | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 6a-3a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 6a-3a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
sed -n '/^### Slice 6a-3a record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '—'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 6a-3a record (merged; owner's phone check)" -m "Records slice 6a-3a (PR #<N>): the merge and CI on main, the owner's
five-step phone check (finding the pages, a prompt and a checklist each
changed on a card that was not customized and put back in the same
step, the year's check, Bulletin settings under Settings, the phone
screen) and the kept theme keywords. No church id, email address or
prompt wording is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 10 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 6a-3a record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 6a-3a record" \
  --body "Records slice 6a-3a (PR #<N>) in docs/ops-runbook.md → Slice 6a-3a record: the merge and the owner's five-step phone check, every test change put back in its step. No church id, email address or prompt wording is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 6a-3a is live and recorded; <n> follow-ups. Next: 6a-3b's planning (Prayers), or 6b, in the order you pick."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no schema to undo). On the owner's yes for each outward command: a branch `claude/revert-6a3a` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 6a-3a (PR #<N>)" with the trailer, both suites (`1885 passed, 31 skipped`; `874 passed` in 103), a PR, CI, and the merge on the owner's yes; record it in the record. Prompts and rubric saved through the pages stay in `churches.settings` in the shapes the old code reads, and `/bulletin-settings` becomes the page again, so nothing needs undoing in the data.

Expected counts after this task: backend `1922 passed, 33 skipped` on `main`; frontend `911 passed` in 107 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-08).** Each task's code was built and run in a throwaway worktree of `6fddb8c` (the branch head `f5bec40` plus the plan's skeleton commit; the repo's `.venv` as a symlink; a hard-linked copy of `frontend/node_modules`, since Turbopack's production build refuses a `node_modules` symlink that points outside the project), one commit per task; the directives were then generated from those commits by a script (a new file as **Create**, a rewritten one as **Replace**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point, changes three or fewer lines apart in one block), which also checked that applying each file's directives to the file before the commit gives the file after it. No package, variable or migration was added. While building:
- **What S assumed and what exists.** 6a-1 built `lock_church`, `lock_and_read_actor`, `require_admin_role`, `LeaveGuard`, `rebaseForm` and the Settings shell, which this plan reuses as they are; slice 4 built `clean_prompt_overrides` (with the CRLF rule and its test) and `check_template`, imported here; `keys.liturgyPrompts` and `keys.rubric` were already in `keys.ts`, and `prompt_invalid` and `invalid_rubric` in `ERROR_CODES`. S's `update_church_rubric` deletion is not made (clarification 17). `test_isolation.py` already covers `GET` and `PATCH /rubric`'s isolation, so only its whole-answer assertion changes.
- **A held request and a dialog.** With the "not closable while it runs" guard taken out, pressing Escape alone did not make the Rubric test fail, so T6 and T8 also tap **Cancel** while the request is held; the guard must ignore both.
- **matchMedia in the tests.** One test widens the window with a `vi.spyOn(window, "matchMedia")`; it restores the spy itself, since a spy left in place opened every card in the tests after it.
- **Mutation checks** (each change made by hand in the build worktree with every task applied, the named tests run, the change undone): `save_prompts` without `require_admin_role` → `1 failed, 61 passed` (`test_church_admin.py`, `test_api_liturgy_prompts.py`); `update_rubric` without it → `1 failed, 61 passed` (`test_church_admin.py`, `test_api_rubric.py`); `get_prompts` reading the stored values raw instead of through `clean_prompt_overrides` → `1 failed, 61 passed`; the prompts page without its `LeaveGuard` → `1 failed, 10 passed`; without the footer's `max-md:static` → `1 failed, 10 passed`; `isCustomized` ignoring the default → `5 failed, 11 passed` (`prompts.test.ts` and the page); `rubricPatch` never sending `null` → `2 failed, 15 passed` (`rubric.test.ts` and the page); the year's save not refreshing the hymn lists → `1 failed, 10 passed`; either Reset all confirmation closable while its request runs → `1 failed, 10 passed` on its page.
- **The lock on Postgres.** On a throwaway local PG 16 cluster (initialised under `/var/lib/postgresql`, port 5442, never a real database, stopped and deleted afterwards; `TEST_DATABASE_URL=postgresql://postgres@localhost:5442/church_test`): `test_church_admin_postgres.py` `3 passed` (6a-1's test and T4's two). With `lock_church`'s `with_for_update=True` taken out, all three fail. All Postgres-marked tests on that cluster, at the end of the replay below: `33 passed, 1922 deselected, 1 warning` (CI's `backend-postgres` job runs the same set).
- **The production build** compiled with `○ /settings/liturgy`, `○ /settings/rubric` and `○ /settings/bulletin` beside the other Settings routes, and `○ /bulletin-settings` (the forward).

**Replay of the finished plan (2026-10-08).** The directives of T1-T10 were applied in order by a replay script that parses each step's **Create**, **Replace**, **Append** and **In … replace** blocks and its `bash` blocks (each commit), and runs every command on its "Run:" lines and compares the output with the quoted **Expected** blocks, onto a fresh detached worktree of the branch at `6fddb8c` (outside the repo directory and removed afterwards), with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules`:
- All 73 directives applied (T1 2 + 9, T2 2 + 5, T3 5 + 5, T4 2, T5 4 + 2, T6 1 + 2, T7 3 + 2, T8 1 + 3, T9 14 + 10, T10 1); every **In … replace** anchor occurred exactly once; all ten commit blocks ran, each commit with the trailer; afterwards the replayed `backend`, `frontend/src` and `docs` trees were identical to the build worktree's, and `git status` was clean.
- Baselines before T1: backend `1885 passed, 31 skipped`; frontend `874 passed` in 103 files; typecheck 0, lint 0.
- Every "see it fail" output and every count above is quoted from this replay (times as `<t>`, Vitest's per-test times left out), and every quoted block matched what the replay printed.
- Every count matched the table: backend 1896, 1912, 1922 passed with 31 skipped, then 33 skipped from T4; frontend 879 in 104, 890 in 105, 896 in 106, 907 in 107, 911 in 107; T1 Step 4 `73 passed` and `streamlit_tests` `35 passed`; T2 Step 4 `114 passed, 1 skipped`; T3 Step 4 ` 2 files changed, 508 insertions(+), 1 deletion(-)` and `34 passed`; T6's and T8's three runs `11 passed` each time, no flaky run; T9 `9 failed | 63 passed (72)` with the Bulletin settings file not loading, then `81 passed`; typecheck 0 and lint 0 after T3 and T5-T9; T10 `89 passed`, `4`, `0`, ` 1 file changed, 18 insertions(+)`. After T10, T11 Step 2's and Step 3's outputs (quoted there): `1922 passed, 33 skipped`, three runs of `911 passed` in 107 files, typecheck and lint 0, `✓ Compiled successfully` with `○ /settings/liturgy`, `○ /settings/rubric`, `○ /settings/bulletin` and `○ /bulletin-settings`, and the 43 paths; the Postgres runs above.
- Not run while planning: the pushes, the PR and CI, the merge, Railway's and Vercel's deploys and the owner's phone check (T12).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| Answer 1: 6a-3a is Liturgy prompts, the Rubric page and Bulletin settings moved in; one PR | T1-T10; T11 (one draft PR) |
| Answer 3: `/settings/bulletin`, the old address forwards, the builder's links | T9 `settings-layout.test.tsx` "opens Settings → Bulletin from the old Bulletin settings address", `bulletin-settings-page.test.tsx` (at the new route), `review-send-step.test.tsx`, `bulletin-step.test.tsx` |
| Answer 4: prompts as designed, admins only, the system prompt included, Reset to default and Reset all | T1 `test_a_save_keeps_only_wording_that_differs_from_the_defaults` (system braces), `test_a_demoted_admin_or_a_removed_member_saves_no_prompts`; T3 `test_a_member_reads_every_prompt_and_may_not_change_them`; T6 "marks a changed card Customized, puts its default back…", "asks before resetting everything…" |
| Answer 5: keep the theme keywords, the note under Opening and Closing | T8 "shows only the Opening and Closing cards' theme note", "adds a point below on Enter…" (the Closing card's note) |
| Answer 6: the order (less Prayers) | T9 `settings-layout.test.tsx` |
| S UX §3 (cards, order, Customized, Reset to default, the system note, the help under "Section prompts", collapsed on phones, the footer, Save sends only customized keys, Reset all confirmed, read-only for members, the 422 opening and focusing its card) | T6 every test; T5 `prompts.test.ts` |
| S UX §6 (the preferences, the checklists and their titles, "A good {Label}:", Enter, paste, ✕, 12 points, Customized, Reset to default, the footer, one sparse PATCH, null for a default, Reset all with null for `customized`, the validation copy, the inline 422, read-only for members) | T8 every test; T7 `rubric.test.ts` |
| S "Every page" (skeleton, ErrorState with Retry, PendingButton, toasts, inline 422s, baseline and rebase, re-initialization after a save, the leave guard) | T6 and T8 "rebases on newer data…", "asks before leaving…", "shows the error state with Retry…"; T5, T7 the rebase units |
| S "Losing a role mid-session" | T1, T2 the demoted-admin tests; T6, T8 "toasts a role 403, refetches the profile and does not report the church as lost" |
| S API rows and Models (`GET`/`PUT /church/liturgy-prompts`, `LiturgyPromptsIn` with `extra="forbid"` and 8,000 characters, `PromptFieldOut`, `LiturgyPromptsOut`; `GET`/`PATCH /rubric` with `defaults`) | T3 every test; `test_openapi_contract.py`, `test_route_guards.py` |
| S Semantics → PUT (full replace, `clean_prompt_overrides` imported, `check_template` in order, "<Label> prompt: <reason>", `{}` resets, the locked merge) | T1 every prompt test; T3 `test_an_admin_saves_only_what_differs…`, `test_a_bad_template_is_a_422…` |
| S Semantics → PATCH /rubric (lock, role, `validate_patch`'s messages as `invalid_rubric` with no field, a non-dict stored rubric as `{}`, `merge_settings`, the answer with `defaults`) | T2 every rubric test; T3 `test_api_rubric.py` |
| S Semantics → Locking; S Testing → Postgres (the four writers less prayers; two rubric saves) | T1 `test_the_prompts_are_read_and_written_under_one_row_lock`; T2 `test_the_rubric_is_read_and_written_under_one_row_lock`; T4 |
| S Testing: ported `test_settings_prompts_translation.py` prompt assertions | T3 `test_a_member_reads_every_prompt_and_may_not_change_them`, `test_an_admin_saves_only_what_differs_from_the_defaults_and_resets_all` |
| S Testing: PR #4's rubric tests keep passing; `assert_church_isolated` on `/rubric` and the prompts | T3 (`test_api_rubric.py` with `defaults`, `test_isolation.py`, `test_the_prompt_routes_are_isolated_between_churches`) |
| S Queries: `["church", id, "liturgy-prompts"]` and `["church", id, "rubric"]` set from the answers; a year change invalidates `["church", id, "hymns"]` | T5 `lib/queries/liturgy-prompts.ts`; T7 `lib/queries/rubric.ts`; T8 "sends only the year and refreshes the hymn lists…" |
| S Acceptance 17 (no horizontal scroll at 375 px, the leave guard, a refetch never sends an untouched field) | T6, T8; T12 Step 6 |
| The 5b-1 and 6a-2 lessons | "Lessons carried"; T6, T8 (dialogs, focus, toasts, the keyboard); T12 Steps 3-4 (changes only on cards not customized, put back in the step) |
| A guided phone check after the PR | T12 Steps 2-6; `docs/manual-verification.md` items 16-23 (T10) |

S items **not** in 6a-3a: Prayers and its routes and draft (6a-3b); the Church, Hymns and Contacts pages (6a-1, 6a-2, 5b-1, done); the ESV key move and its `streamlit_tests` deletion, the legacy note and the email hand-offs (not scheduled here); 6b.

## Follow-ups (not in 6a-3a)

- 6a-3b: Prayers between Liturgy and Rubric (`SETTINGS_SECTIONS` and the layout test), and the four-writer Postgres case with the prayer library.
- If the seven (later eight) section links wrap awkwardly on a phone, a horizontal scroller for the Settings nav (the 6a-1, 5b-1 and 6a-2 follow-up, carried; owner question 5).
- Choosing another church in the church menu still does not ask before discarding unsaved settings edits (6a-1 follow-up, carried; it now covers the prompts and the rubric).
- Dropping the opening and closing theme keyword pre-filter when a slot checklist is customized (S Open question 3's alternative; answer 5 keeps them for now).

## Owner questions

Your 6a-3 planning answers of 2026-10-07 (the six, all as recommended) and the earlier answers on Settings are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **The button at the top of Bulletin settings** (clarification 10). It now says **Back to the builder** and opens the builder on the step you were last on (the Bulletin step or Review & send, the two places with a **Bulletin settings** button), instead of always going to Review & send. Recommended: accept.
2. **When "Reset all to defaults" shows on Liturgy prompts** (clarification 3). Only while your church has wording of its own saved, as the spec says for the rubric; when every prompt is already the shared default there is nothing to reset. Recommended: accept.
3. **What a member sees on Rubric** (clarification 6). The points as a plain list of text (with the note "Only admins can edit the rubric. You can read it below."), rather than greyed-out boxes; the prompts stay in read-only boxes, since they are long texts a member may want to scroll and copy. Recommended: accept.
4. **The Save bar while typing on a phone** (clarifications 3, 6). The Save bar stays at the bottom of the screen, except while the phone keyboard is open: then it sits after the last card, so it never covers the text you are typing; you reach it by scrolling down. Recommended: accept.
5. **Seven section links on a phone** (clarification 2). They wrap onto two or three rows at the top of Settings (eight after Prayers). Recommended: keep the wrapping row for now and check it in the phone test; a sideways-scrolling row can come later if it feels crowded.
6. **The shared default prompts and checklists keep their own wording** (clarification 15). Some of the shared defaults (for example the overall voice prompt) contain dashes. They are the AI's instructions for every church, shown as they are; changing them changes what the AI is told. Recommended: leave them unchanged.
7. **The wording** (clarification 15): every new line on the two pages is the spec's own (none has a dash), and so are the save messages. New beyond the spec are the button **Back to the builder** and three labels only a screen reader speaks: "Point {n} of {Label}", "Reset to default: Prefer hymns written before" and "Reset to default: Prefer familiar hymns". Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T11); the merge on your yes, then five phone checks one at a time (every test change made on a card that is not customized and put back in the same step), and the records PR (T12).

## Self-review

- **Coverage.** Every binding constraint has a home: two PRs and this one's scope (clarification 1, T11); `/settings/bulletin` with the forward and the builder's links (clarification 10, T9); the prompts as designed with the system prompt, Reset to default and Reset all, admins only (clarifications 3-5, T1, T3, T6); the theme keywords kept with the note (clarification 6, T8); the order less Prayers (clarification 2, T9); the locking with the church-row lock and the role re-read (clarifications 5, 9, 12; T1, T2, T4); `clean_prompt_overrides` imported, never copied (T1); the rubric's sparse PATCH with null for a default (clarification 8, T7, T8); no migration (clarification 13); no em dash in new copy (clarification 15; T10 Step 2 and T11 Step 3 grep the added lines); no ids or real addresses in the docs (only `@example.com`, and PR #4's `@x.org` tests unchanged; the record's own grep, T12 Step 9); the frozen Streamlit files untouched and their tests passing (clarification 14; T1 Step 4 runs `streamlit_tests`; T11 Step 3's path check counts `app.py`, `streamlit_views` and `streamlit_tests` as 0); tests never reach the network (Global Constraints); the 5b and 6a lessons ("Lessons carried"). The second-to-last task opens a draft PR only on the owner's yes; the last merges only on a yes, runs a five-step phone check one step at a time (each test change on a card that is not customized and put back in its step; Reset all never tapped; the year never saved) and inserts "### Slice 6a-3a record" before "## Backups", after "### Slice 6a-2 record".
- **Placeholders.** None in T1-T10's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T11 and T12's runtime values (`<N>`, `<scratch>`, `<card>`, `<year>`, times, the owner's answers), as in the 6a-2 plan.
- **Consistency.** Names agree across tasks: `merge_settings`, the sessions on `set_church_prompts` and `update_church_rubric` (T1, T2) are used by `save_prompts` and `update_rubric`; `get_prompts`, `save_prompts`, `prompt_label`, `get_rubric`, `update_rubric`, `rubric_out` (T1, T2) by the routes (T3) and the Postgres tests (T4); `LiturgyPromptsOut`, `PromptFieldOut`, `LiturgyPromptsIn`, `RubricOut`, `RubricModel` (T3) by the type names (T5); `PROMPT_KEYS`, `promptValuesFrom`, `promptsPayload`, `promptFieldErrors`, `rebasePrompts` (T5) by the page (T6); `CHECKLISTS`, `rubricFormFrom`, `rubricPatch`, `resetAllPatch`, `rubricErrors`, `rebaseRubric`, `isInvalidRubric` (T7) by the card and the page (T8); `keys.liturgyPrompts`, `keys.rubric` (existing) by the queries. The counts in the table, each task's "Expected" and the PR line (`1885 → 1922`, `31 → 33`, `874 → 911`, `103 → 107`) agree.
- **Not verified while planning:** the pushes, the PR and CI (the two Postgres tests were run on a local throwaway Postgres instead), the merge, Railway's and Vercel's deploys, the owner's phone check, and the pages at 375 px in a real browser (the classes give 44 px targets; jsdom does not lay out).
- **Judgement calls to watch in review:** keeping `update_church_rubric` as the write path instead of deleting it; `GET`'s `override` read through `clean_prompt_overrides`; the footer going static while the keyboard is open; members reading the rubric as text; the hymn slot titles in the client; the client-side forward of the old address.
