# Slice 6a-2: Hymns in Settings

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the second of slice 6a's three PRs (owner's 6a-2 planning answers of 2026-10-07, "all recommended"): **the Hymns page in Settings.** After it merges, the Settings sections are **Church**, **Hymns**, **Bulletin**, **Contacts** and **Account**. `/settings/hymns` shows two things. **Hymnals**: each of the church's hymnals with its name and hymn count and a **Default** badge on the one the builder opens with; owners and admins add a bundled hymnal (**Add a hymnal**: today the server bundles PH1990, 605 hymns, and the shared catalog's GG2013) and remove any hymnal except the only one and the default one (confirmed). **Hymn library**: every hymn of the church, 50 at a time with **Show more**, a search by title or number, hymnal chips when there are several; any member adds a hymn (**Add hymn**) and edits one (**Edit hymn**: title, number, hymnal, scripture references, themes, link); owners and admins also delete a hymn (confirmed) and set its "Year the words were written" and "Number of hymnals (familiarity)", which members see read-only. A duplicate (the same hymnal, number and title, in any capitals or spacing) is refused with "{hymnal} already has #{number} {title}.", even when two people add it at the same moment. Every change shows in the builder's hymn picker without a reload; an edit also shows in saved services that use the hymn, and the edit dialog says so. No "Fill from Hymnary.org" button (answer 6), no migration (Alembic head stays `0007_bulletin_images`), no new package or variable.

**Architecture:** Backend first. The bundled CSV moves under `backend/` (`git mv data/hymnals/PH1990_hymns.csv backend/seed/hymnals/PH1990.csv`; Railway deploys only `backend/`), and a new `backend/hymnal_sources.py` lists what an admin can add: each `seed/hymnals/*.csv` (read once, `utf-8-sig`) and each hymnal of `hymn_catalog`, with `rows_for(code)`. `import_hymnal.py` (the ops CLI) uses it and no longer needs `--csv` for a bundled hymnal. `repos/hymns.py` gains `title_key`, `get_hymn`, `create_hymn`, `patch_hymn`, `find_duplicate` and `delete_hymnal`, a `session` on `import_hymns` and `delete_hymn`, and an `import_hymns` that flushes once and fills only blank details. A new `backend/usecases/hymn_library.py` holds the field rules and the six writes and reads (`create_hymn`, `update_hymn`, `delete_hymn`, `list_sources`, `add_hymnal`, `remove_hymnal`), each write in one session that starts with 6a-1's `lock_and_read_actor`, so the duplicate check and the write run under the church-row lock with the caller's role re-read (`require_admin_role` for deletes, hymnals and the two facts). Routes: `POST`, `PATCH`, `DELETE /hymns` in `routes/hymns.py`; `GET /hymnal-sources`, `POST /hymnals`, `DELETE /hymnals/{code}` and an additive `label` on `GET /hymnals` in `routes/hymnals.py`. Postgres tests prove the lock. Frontend: the generated types, `lib/settings/hymns.ts` (the forms' pure rules), `lib/queries/hymn-library.ts` (the library's infinite query, the sources and the five writes, each refreshing every key under `["church", id, "hymns"]`, which the builder's picker shares, plus hymnals, sources and the profile), `components/settings/hymnals-card.tsx`, `hymn-library.tsx`, `hymn-dialog.tsx` and `hymns-settings-page.tsx` with their route, **Hymns** in `SETTINGS_SECTIONS` after Church, and the two links 6a-1 and slice 3 left for this page.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, Pydantic 2, SQLAlchemy, pytest; Next 16, React 19, TypeScript 5, Base UI (Dialog, AlertDialog, Select), TanStack Query 5 (`useInfiniteQuery`), sonner, lucide-react, Vitest 3 with Testing Library.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md`, read with its amendments. **"Amendment 2026-10-07: owner's 6a-2 (Hymns) planning answers"** is binding and wins where the older text differs; so are the 2026-10-05 answers (only admins delete hymns; removing a whole hymnal is included, refused for the only or the default hymnal) and the 2026-09-26 one (the year and familiarity are admin-only). From S: UX §2 "Hymns", the API rows for `POST`/`PATCH`/`DELETE /hymns`, `GET /hymnal-sources`, `POST /hymnals` and `DELETE /hymnals/{code}`, the Models (`HymnIn`, `HymnPatchIn`, `HymnDetailOut`, `HymnalSourceOut`), "Semantics" (Locking, POST and PATCH /hymns, POST and DELETE /hymnals), Backend "New modules" (`hymnal_sources.py`, `usecases/hymn_library.py`, the seed file) and "Changed modules" (`repos/hymns.py`, `import_hymnal.py`), "Queries and mutations" (`hymns.ts`, `hymnals.ts` rows), Testing (`test_hymn_library.py`, `test_hymnal_sources.py`, `test_import_hymnal_cli.py`, the hymn API tests, the Postgres cases for hymns and hymnals, the Hymns DOM cases) and acceptance 8, 12-16 and 25.
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.2 (guards), §1.4 (list order), §1.5 (errors), §1.8 (timeouts), §2.2 (layers), §4.4 (keys and invalidation), §4.8 and §4.9 (forms, 44 px, Base UI Select).
- The model plans `docs/superpowers/plans/2026-10-06-slice-5b1-contacts.md` (closest in shape: a Settings page with a list, add, an edit dialog and confirmed deletes, its build review fixes) and `docs/superpowers/plans/2026-10-05-slice-6a1-settings-church.md` (`lock_church`, `lock_and_read_actor`, `require_admin_role`, the Settings shell), whose patterns are reused unchanged.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `446eaa3` = `origin/main` `a24b7b5` plus the 5b-2b record `94f7f3e` and the 6a-2 amendment `446eaa3`, then this plan's commits; 2026-10-07): backend `1825 passed, 27 skipped`; frontend `835 passed` in 100 files; typecheck and lint clean; Alembic head `0007_bulletin_images` (7 revision files); 4 runbook owner markers. What exists: the `hymns` table (`db/models.py` `Hymn`: `id`, `church_id` (cascade), `hymnal` not null, `title`, `number`, `scripture_refs`, `theme`, `hymnary_link`, `audio_url`, `text_year`, `hymnal_count`; three indexes; **no** unique constraint and no foreign key from any other table); `hymn_catalog` (GG2013 in production, 853 hymns, 795 with scripture references: slice 3a record); `data/hymnals/PH1990_hymns.csv` (605 rows, `number,title,tune`, every row numbered, no duplicates, no scripture references), read only by `import_hymnal.py` (`load_rows`, `load_dotenv()` at import time, `--csv` required); `repos/hymns.py` with `import_hymns` (no `session`, a `flush()` per new row, overwriting any non-blank value that differs), `add_hymn`, `update_hymn` (replaces every field), `delete_hymn` (no `session`), `list_church_hymnals`, slice 3's typed reads (`HymnRecord`, `hymnal_summaries`, `query_hymns`, `get_hymns_by_ids`) and **no** `get_hymn`; `usecases/hymns.py` (`resolve_default_hymnal`, `hymnal_overview`, `list_hymns_page`); `GET /hymns` (`q`, `hymnal`, `limit` up to 2000, `offset`) and `GET /hymnals` (no `label`); `repos.churches.lock_church`, `usecases.members.lock_and_read_actor`, `usecases.church_admin.require_admin_role` (6a-1); `api.schemas.DeletedOut`; `keys.hymns`, `keys.hymnMatches`, `keys.hymnals` and `keys.hymnalSources` already in `lib/queries/keys.ts`; the builder's `useHymnLists` and `useScriptureMatches` keyed under `["church", id, "hymns"]`; `SETTINGS_HYMNS_READY = false` in `lib/features.ts`; the Church page's "Your church has no hymns yet, so there is no default hymnal." with no link; `SETTINGS_SECTIONS` = Church, Bulletin, Contacts, Account. **No** hymn write route, hymnal route, `hymnal_sources.py`, `usecases/hymn_library.py` or Hymns page. The frozen Streamlit files call `add_hymn`, `delete_hymn` and `list_hymns` positionally; `streamlit_tests` (35 tests, still collected by pytest) pass through them.
- Every task's code was written and run by the planner in a throwaway worktree, and the plan's directives were then replayed onto a fresh worktree of the branch (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -1` (or `tail -3` where a collection error is expected); the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted, and Vitest's run time after a test name is left out here); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. A time in an expected output is written `<t>`.
- The API changes (T4), so T4 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- No new package, no new variable, no migration.
- Branch `claude/slice-2-plan-4q33le`, at `446eaa3` plus this plan's commits (`WIP plan: slice 6a-2 …` and `Plan: slice 6a-2 (Hymns in Settings)`, and any later plan commit), then T1-T10. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`, never a rebase; if the push is rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1825 → 1883 passed, 27 → 31 skipped; frontend 835 → 869 in 100 → 103 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 22 and has no em dashes (S's lines are taken without theirs: "Still working. This can take up to a minute.", and a hymn with no number shows its title alone instead of S's "—"); existing copy keeps its own punctuation.
- No church id, email address, token, database URL or real person's name in any doc, commit, test or record. Tests use the fixtures' "Grace" and `@example.com` / `@example.org` addresses only.
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.
- Tests never reach the network: the hymnal tests read the bundled CSV from disk, the backfill test uses `tests.test_hymnary_facts.FakeFetch`, and the CLI test turns `dotenv.load_dotenv` into a no-op.

### How the file directives below read
As in the 5b-1 and 6a-1 plans: **Create `path`:** the block is the whole new file; **Replace `path`:** the block is the whole file, which already exists and is rewritten (used for `import_hymnal.py` and `routes/hymnals.py`, most of whose lines change); **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:** (a leading or trailing empty line in a block is part of it). Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. One file is moved (T1 Step 3, with `git mv`) and one empty file added there (`data/.gitkeep`); none is deleted.

### Baselines and counts
- Starting baselines: backend **1825 passed, 27 skipped**; frontend **835 passed in 100 files**, typecheck and lint clean; Alembic head **`0007_bulletin_images`** (7 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(` (an `it.each` row counts as one).

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +7 (`test_hymnal_sources.py` 4, `test_import_hymnal_cli.py` 3; `test_no_streamlit_in_core.py` edited) | 1832 passed, 27 skipped | 0 | 835 in 100 |
  | T2 | +5 (`test_hymns_repo.py`, 15 → 20) | 1837 passed, 27 skipped | 0 | 835 in 100 |
  | T3 | +28 (`test_hymn_library.py`: one test in 13 cases and 15 tests; `test_no_streamlit_in_core.py` edited) | 1865 passed, 27 skipped | 0 | 835 in 100 |
  | T4 | +18 (`test_api_hymns_admin.py` 14: one test in 9 cases and 5 tests; `test_api_hymnals_admin.py` 4; `test_api_hymnals.py` edited) | 1883 passed, 27 skipped | 0 | 835 in 100 |
  | T5 | +4 skipped (`test_hymn_library_postgres.py`, skipped without `TEST_DATABASE_URL`) | 1883 passed, 31 skipped | 0 | 835 in 100 |
  | T6 | 0 | 1883 passed, 31 skipped | +7 (`hymns.test.ts`) | 842 in 101 |
  | T7 | 0 | 1883 passed, 31 skipped | +12 (`hymns-settings-page.test.tsx`) | 854 in 102 |
  | T8 | 0 | 1883 passed, 31 skipped | +13 (`hymn-library.test.tsx`) | 867 in 103 |
  | T9 | 0 | 1883 passed, 31 skipped | +2 (`settings-layout.test.tsx` 1, `church-settings-page.test.tsx` 1; `hymns-step.test.tsx` edited) | 869 in 103 |
  | T10 | 0 | 1883 passed, 31 skipped | 0 | 869 in 103 |

- CI `backend-postgres` goes from `27 passed, 1825 deselected` to `31 passed, 1883 deselected` (T5). Locally, without `TEST_DATABASE_URL`, those four tests are among the 31 skipped.

### Layering and code rules (carried)
- `hymnal_sources.py` and `usecases/hymn_library.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains both, T1 and T3); the routes are plain `def`s with no SQL and no try/except (F §2.2 rule 1), each one usecase call; the usecase writes through `repos.hymns` (no SQL in the usecase).
- Logs carry ids, never a hymn's title (F §2.5). This PR adds no log line.
- Pages and components never call `apiFetch`: the queries use `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); inputs `text-base md:text-sm` (the kit's `Input` already is).

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** is retired (branch `streamlit-frozen`, untouched); merges never reach it, so S's Streamlit compatibility notes and its manual check 10 do not apply.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The 6a-2 planning answers of 2026-10-07** ("all recommended"; binding; S's amendment): (1) build UX §2 as designed: the Hymnals card (counts, admin-only **Add a hymnal** and **Remove…**) and the Hymn library (search, hymnal filter, add, edit, admin-only delete, pages of 50 with **Show more**); the server bundles only PH1990 today, and Add stays for new churches and second hymnals; (2) **one PR**; (3) **Settings order after 6a-2: Church, Hymns, Bulletin, Contacts, Account**; (4) hymn edits reach saved services, and the edit dialog keeps "Changes also appear in saved services that use this hymn."; (5) **Risk 2 (renamed hymns and the 12-week recent-use rule) is accepted for now and noted in the runbook record** (T12); (6) no "Fill from Hymnary.org" button in 6a-2 (a possible follow-up). Earlier answers still apply: members add and edit hymns; only admins delete hymns (Open question 2), edit the year and familiarity (Open question 4) and remove a hymnal (Open question 1, never the only or the default). No em dashes in user-facing copy.
5. **The 6a answers of 2026-10-05** (binding, carried): admins change the church, everyone reads; three 6a PRs (6a-1 merged as PR #52; this is 6a-2).

**Later, out of scope:** 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved under `/settings`), 6b (People, Danger zone), "Fill from Hymnary.org" (answer 6), slice 7 (keying recent use by hymn id; the `hymn_catalog` seed export).

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Owner questions" (each written as recommended).

1. **[owner-visible] What 6a-2 ships** (answers 1, 2, 6). The Hymns page with both cards; `POST`, `PATCH` and `DELETE /hymns`; `GET /hymnal-sources`, `POST /hymnals`, `DELETE /hymnals/{code}`; `label` on `GET /hymnals`; the bundled CSV under `backend/` and `hymnal_sources.py`; the CLI's changes; the Postgres tests; the builder's empty-hymnal link and the Church page's link to Hymns (clarification 20). Not here: "Fill from Hymnary.org", anything in 6a-3 or 6b, keying recent use by hymn id.
2. **[owner-visible] Where Hymns sits** (answer 3). `SETTINGS_SECTIONS` becomes **Church** (`/settings/church`), **Hymns** (`/settings/hymns`), **Bulletin**, **Contacts**, **Account**. On a phone the section nav is a wrapping row of 44 px links; five may wrap to a second row at 375 px (T12 Step 5 checks it is easy to use).
3. **[owner-visible] The page** (S UX §2). Inside the Settings layout: the heading "Hymns" (an `h2`, as "Church profile" and "Contacts") with "The hymnals and hymns the builder offers when you choose hymns." under it (new: S has no intro; owner question 3), then the **Hymnals** card, then the **Hymn library** (each an `h3`). Every role sees both; what a member may not do is simply not offered.
4. **[owner-visible] The Hymnals card** (S UX §2a). A list (`aria-label="Hymnals"`), one row per hymnal in `GET /hymnals`' order: the code in bold with a **Default** badge on the effective default, and under it the label when known ("Glory to God (2013)", "The Presbyterian Hymnal (1990)"; `hymnal_sources.HYMNAL_LABELS`) and "{n} hymns" ("1 hymn"), joined by " · ". Under the list: "{total} hymns in {n} hymnals." ("in 1 hymnal"). With no hymnals: "Your church has no hymnals yet." Owners and admins: **Add a hymnal** under the card (full width on a phone), **Remove…** on every row but the default (`aria-label` "Remove {code}") and but a hymnal whose code `DELETE /hymnals/{code}` cannot take (anything but 2 to 20 letters, digits, `_` or `-`, which only the ops CLI or the old app could have made; its row simply has no **Remove…**, rather than a route widened to codes with spaces, dots or slashes; plan review M4), and on the default row "Default. Change it in Church profile." with "Church profile" a link to `/settings/church`. Members: no buttons, and "Admins can add bundled hymnals." The first load shows a skeleton row, a failed read `ErrorState` with **Retry**.
5. **[owner-visible] Add a hymnal** (S UX §2a). A dialog (a bottom sheet below `md`, as **Edit contact**): title "Add a hymnal", "Hymnals this app can add to your church, with their hymns.", then `GET /hymnal-sources` as a list (`aria-label="Bundled hymnals"`), each row "{code} · {label} · {n} hymns" and, when the source has no scripture references, "This hymnal has no scripture references, so “Hymns for the readings” and AI suggestions work less well with it." (S said "“Find hymns”"; the builder's button is "Hymns for the readings"; owner question 10). A source the church has shows a disabled **Added**; the others **Add** (`aria-label` "Add {code}"). An add sends `POST /hymnals {code}` (60 s, `timeouts.ts`, so the "up to a minute" below is true; plan review I3); its button reads "Adding…", the other Add buttons and **Done** are disabled, Escape and a tap outside are ignored, and after 8 s "Still working. This can take up to a minute." shows. On success the dialog stays open, the row turns to **Added**, and "Added {code} ({n} hymns)." is toasted, or "{code} is already added." when the add inserted and filled in nothing (another tab added it meanwhile; plan review I3); every hymn list refreshes (clarification 19). A failed add (a timeout among them) is toasted and also refreshes every list, since it may have finished on the server. **Done** closes it. With no sources: "No bundled hymnals are available on this server." In production the list is GG2013 (from the catalog; **Added**) and PH1990.
6. **[owner-visible] Remove a hymnal** (S UX §2a; answer of 2026-10-05). **Remove…** opens a confirmation: title "Remove {code}?", body "This deletes all {n} hymns in {code} from your church's hymnal, including hymns your church added to it. Saved services keep their hymns. Services in progress will ask you to choose replacements." followed, when the bundled list has loaded, by "You can add {code} again later, but edits you made to its hymns will be lost." (a bundled code) or "It can't be added back from the bundled list." (any other); for a hymnal with one hymn the body starts "This deletes the 1 hymn in {code} from your church's hymnal," (plan review M2); confirm **Remove {code}** (red), **Cancel**. While it runs it cannot be closed. Success: "Removed {code}." and focus moves to **Add a hymnal** (the row is gone); a refusal (the server's 404 or 409, for example a hymnal that became the default in another tab) is toasted with the server's message, the lists refresh and the confirmation closes; after a 404 (the hymnal was removed elsewhere, so its row goes too) focus also moves to **Add a hymnal** (plan review M1). The default row has no Remove; the server also refuses the only hymnal ("You can't remove your only hymnal.") and the effective default ("{code} is your default hymnal. Choose a different default in Church profile first.").
7. **[owner-visible] The Hymn library** (S UX §2b; answer 1). Caption "Anyone in your church can add and edit hymns. Only admins can delete them." (S's line predates the 2026-10-05 answer that only admins delete; owner question 4). **Add hymn** (primary, full width on a phone); a search box (`type="search"`, "Search by title or number") that searches 300 ms after typing stops, from the first page, with an × button "Clear search"; with more than one hymnal, toggle chips **All** and each code (`role="group"` "Hymnal", `aria-pressed`). The count line "{n} hymns" ("1 hymn"), or "{n} matching hymns" while searching or filtered. The list (`aria-label="Hymns"`): each row a button "#{number} {title}", or the title alone when there is no number (S's "—" would be an em dash; owner question 8), with a hymnal badge when the church has several; a tap opens **Edit hymn**. Pages of 50 in the server's order (hymnal, number with no-number hymns last, title); **Show more** loads the next 50 ("Loading…"). The search is S's slice 3 rule: 1 to 6 digits also match the number. Empty states: "No hymns yet" with "Add hymns one at a time, or add a bundled hymnal above." (admins) or "Add hymns one at a time, or ask an admin to add a bundled hymnal." (members), with no second **Add hymn** in it (the button is just above); a search with no result: "No hymns match “{q}”." with **Clear search**, which also puts focus back in the search box. A chip whose hymnal was removed meanwhile falls back to **All**.
8. **[owner-visible] Add hymn / Edit hymn** (S UX §2b; answers 1, 4). One dialog, a bottom sheet below `md` (the **Edit contact** sheet, `max-h-[85dvh]`, scrolling, its footer clear of the iPhone home bar) rather than S's full screen below `sm`, so the keyboard does not hide **Save changes** (T12 Step 5 checks it; owner question 7). Title "Add hymn" ("A hymn your church sings that is not in the list yet.") or "Edit hymn" ("#{number} {title}"). Fields, each 44 px below `md`: **Title**; **Number** (`inputMode="numeric"`); **Hymnal** (a Select of the church's hymnals, shown only with more than one; Add starts at the effective default); **Scripture references** ("e.g. Psalm 23; John 10:11-18"; help "Used by “Hymns for the readings” and AI suggestions."); **Themes** ("e.g. Advent, hope"; Edit starts at the hymn's themes joined by ", ", as S says); **Link** ("https://hymnary.org/…"); **Year the words were written** and **Number of hymnals (familiarity)** (`inputMode="numeric"`; for a member read-only with "Only admins can change this." under each, and never sent; owner question 6). Edit also shows "Changes also appear in saved services that use this hymn." (answer 4) and, for owners and admins, **Delete hymn** (red). Buttons **Cancel**, **Add hymn** ("Adding…") or **Save changes** ("Saving…"). Add sends every field (blank as null; the facts only for an admin); Edit sends only what changed (text trimmed, numbers compared as numbers, a cleared field as null), and nothing changed closes it with no request. Success toasts "Hymn added." or "Hymn updated." and closes. **Delete hymn** opens "Delete “{title}”?", "Saved services keep this hymn. Services in progress that use it will ask you to choose a replacement.", **Delete hymn** (red): success toasts "Hymn deleted.". While any of these requests runs the dialog cannot be closed (Cancel disabled, Escape and a tap outside ignored), and a late answer closes only the dialog it was sent from (the dialog is keyed by the hymn, and closes through `onClose(key)`). When the hymn is gone (deleted here, or a 404 because it was deleted elsewhere) focus goes to **Add hymn**, since the row that opened it is gone too.
9. **Client checks** (S "Pure helpers" `hymns.ts`). Before sending, in the form's order and with the server's words: "Hymn title is required." (blank), "Hymn number must be a whole number." (not 1 to 99999), "Links must start with https://." (a non-blank link not starting with `https://`, any case), and for an admin "Year must be a whole number from 1 to {this year}." and "Number of hymnals must be a whole number from 0 to 100000."; each shows under its field (`role="alert"`, `aria-invalid`), the first is focused, nothing is sent, and editing a field clears its message.
10. **Errors** (the 5b-1 policy, `lib/queries/hymn-library.ts`). A 401 or a lost church: nothing more (the app handles them). In the hymn dialog a 409 shows above the buttons (`role="alert"`) and the dialog stays open; a 422 whose `fields` names one of the form's fields shows under it and focuses the first (`theme` is the Themes box). A role 403 (an admin demoted meanwhile, for example on the facts) toasts "Only church admins can do this.", refetches the church profile (so the page turns into the member's view) and closes the dialog. A 404 in the dialog toasts "This hymn was already deleted.", refreshes the lists, closes the dialog and moves focus as in clarification 8; a delete's 404 is treated as done. Anything else, a 422 that names no field of the form among them, is toasted with the server's message (`errorToastMessage`). The hymnal writes toast every failure but a 401 or a lost church, and refresh every hymn list, the hymnals, the sources and the profile after any of them (a timed-out add may have finished on the server; plan review I3).
11. **[owner-visible] The field rules on the server** (S "Semantics" → POST and PATCH /hymns). In `usecases/hymn_library.py`, in the order title, number, hymnal, scripture references, themes, link, year, familiarity; the first failure is a 422 naming its field:
    - The title, scripture references and themes are each made one line: every control character becomes a space, every run of whitespace one space, trimmed (S: "trimmed"; a pasted line break or tab is tidied, not refused; owner question 1). A blank title (or an omitted or null one) is "Hymn title is required."; blank references or themes are stored as NULL.
    - The number: null, or 1 to 99999, else "Hymn number must be a whole number."; a JSON number that is not whole is Pydantic's "Not a valid value.".
    - The link: blank is NULL; one containing a space or control character is "Links can't contain spaces." (new; owner question 2); otherwise it must start with `https://` in any case and have something after it, else "Links must start with https://.".
    - The year: null, or 1 to the current year, else "Year must be a whole number from 1 to {year}."; the familiarity: null, or 0 to 100000, else "Number of hymnals must be a whole number from 0 to 100000.".
12. **The duplicate rule** (S Semantics; the 5b-1 lesson on whitespace and case). Two hymns are the same when they share the church, the hymnal, the number (or both have none) and `repos.hymns.title_key(title)`: every run of whitespace (tabs, line breaks and no-break spaces included) one space, trimmed, lower-cased. `find_duplicate` reads the candidates in SQL by hymnal and number and compares the titles in Python (SQL `trim` and `lower` treat tabs and some letters differently on SQLite and Postgres), and `import_hymns` uses the same key. Add: a duplicate is 409 "{hymnal} already has #{number} {title}." or, with no number, "{hymnal} already has {title}." (with the title as sent, tidied). Edit: the check runs only when the hymnal, the number or the title's words change and the resulting title is not blank (an old hymn's blank title, which the old app allowed, would give "{hymnal} already has #{number} ."; plan review M8), and leaves the hymn itself out, so editing only the references of a hymn that already has an old twin (Streamlit never checked) is not refused.
13. **The hymnal of a new hymn** (S Semantics). Null or blank: the effective default (`usecases.hymns.resolve_default_hymnal`), or `GG2013` for a church with no hymns (parity with `add_hymn`). Otherwise it must be one of the church's hymnals, compared trimmed; a church with no hymns may name any code of 2 to 20 letters, digits, `_` or `-`. Else "Choose one of your church's hymnals." An edit's hymnal must be one of the church's (null too is refused); moving a hymn to another hymnal is allowed (clarification 19 says what a draft then shows; owner question 11).
14. **Who may do what, and the lock** (answers; S Semantics → Locking). Members add and edit hymns (`require_church`). Owners and admins delete hymns (`DELETE /hymns/{id}` has `require_admin`, answer 5 of 2026-10-05), list sources, add and remove hymnals (`require_admin`), and set the facts. Every write opens one session and starts with `lock_and_read_actor` (a deleted church or a removed member: 403 `no_church_access`, nothing written); the admin writes then call `require_admin_role` on the re-read role (a demoted admin: 403 "Only church admins can do this.", no `reason`, nothing written); a hymn write that sets a fact does too, before any field is checked: on `POST` a non-null `text_year` or `hymnal_count`, on `PATCH` either key present, null included. An edit or a delete of an unknown id, or another church's, is 404 "Hymn not found." (after the role checks, before any field). The duplicate check and the write run under the lock; no `Idempotency-Key` (S: a retry gets the 409, and adding a hymnal twice inserts nothing). `GET /hymnal-sources` reads only (`require_admin`; no lock).
15. **Routes and models** (S API, Models). In `routes/hymns.py`: `POST /hymns` (`HymnIn`, 201 `HymnDetailOut`), `PATCH /hymns/{hymn_id}` (`HymnPatchIn`, only the keys sent, `model_fields_set`; 200 `HymnDetailOut`), `DELETE /hymns/{hymn_id}` (200 `DeletedOut`). In `routes/hymnals.py` (rewritten): `HymnalOut` gains `label: str | null = null` (additive), `GET /hymnal-sources` → `HymnalSourceList {items: HymnalSourceOut[]}`, `POST /hymnals` (`HymnalIn {code: str(20)}`, 200 `HymnalAddedOut {code, label, inserted, updated}`; an unknown code is 422 `fields.code` "That hymnal isn't available to add."), `DELETE /hymnals/{code}` (`code` must match `^[A-Za-z0-9_-]{2,20}$`, else 422; 404 "Your church doesn't have that hymnal."; 409 as in clarification 6; 200 `HymnalRemovedOut {deleted: true, hymns_deleted}`). All request models have `extra="forbid"`. One deviation: `HymnIn.title` is `str | None = None` (S: `str = ""`), so a JSON null title also gets "Hymn title is required." instead of Pydantic's generic message. The route-guard allowlists do not change.
16. **The bundled hymnals** (S "New modules" `hymnal_sources.py` and the seed file). `git mv data/hymnals/PH1990_hymns.csv backend/seed/hymnals/PH1990.csv` (content unchanged; the emptied `data/hymnals` is removed, and `data/` stays, kept by an empty `data/.gitkeep`, because the README and `backend/.env.example` put the local SQLite database at `sqlite:///../data/app.db` and `db/engine.py` falls back to `sqlite:///data/church.db`; plan review I1). `hymnal_sources.load_rows(source, hymnal)` (moved from `import_hymnal.py`, opening files as `utf-8-sig` and dropping a byte order mark from a stream too); `file_sources()` (cached, no database); `list_bundled(session=)` (each catalog hymnal counted in SQL, then the files; a file wins a shared code); `rows_for(code, session=)` (the file's rows, else the catalog's with their year, familiarity and audio; `KeyError` for neither); `HYMNAL_LABELS` and `label_for`. `list_sources` marks each `present` when the church has at least one hymn in it.
17. **The import** (S "Changed modules" `repos/hymns.py`; S Risk 5). `import_hymns(church_id, hymnal, rows, *, session=None)`: a row the church already has (same number and `title_key`) is not added again, and only its **blank** details are filled (S: "fills missing enrichment only"; the old code overwrote any differing value, so re-adding a hymnal would have undone a church's edits to its links or references; owner question 5); new rows are added without a flush each and flushed once at the end, so they go to Postgres as one batched INSERT (a 605-row add is timed under 10 s in T5). It also carries `audio_url`, `text_year` and `hymnal_count` (catalog rows have them). New titles are stored tidied. `slice 1`'s `test_hymnals.py` idempotency test keeps passing unchanged.
18. **The CLI** (S "Changed modules" `import_hymnal.py`). `load_rows` delegates to `hymnal_sources.load_rows`; `load_dotenv()` moves into `main()`; `--csv` may be left out for a bundled hymnal (`--hymnal PH1990`), and is required otherwise with a message naming the bundled ones. It stays an ops tool with no role check.
19. **What the builder sees** (S Queries; the task's "deletions and edits invalidate the builder's queries"). Every write's success invalidates the prefix `["church", id, "hymns"]` (the builder's `useHymnList`/`useHymnLists` lists, `useScriptureMatches`, and the library), `["church", id, "hymnals"]`, `["church", id, "hymnal-sources"]` and `["church", id, "profile"]` (whose `effective_hymnal` can change): the picker shows an added, renamed or deleted hymn with no reload, and a draft's pick of a deleted hymn shows "Not in your hymnal. Choose a replacement." (slice 3). Nothing else caches a hymn's title: a saved service is always fetched again when opened (`useOpenService`), and the services list has no hymns. A pick whose hymn is moved to another hymnal also shows "Not in your hymnal" (the draft keeps the hymnal it was picked from; `reconcilePick`), until another is chosen; accepted (risk below).
20. **Hand-offs** (S "Hand-off from 3"; the 6a-1 follow-up). `SETTINGS_HYMNS_READY` becomes `true`, so the builder's empty-hymnal state says "Add hymns on the Settings → Hymns page to choose hymns here." with **Open Settings → Hymns** (slice 3's own words). The Church page's no-hymns line gets a link under it, "Add hymns on the Hymns page", to `/settings/hymns`, for an admin (the form) and a member (the read-only summary; plan review M5) alike (owner question 9).
21. **[owner-visible] No database change** (no migration). Hymns and hymnals are rows of the existing `hymns` table; no other table points at a hymn, so deleting one or a whole hymnal touches nothing else: saved services keep their own copy of each hymn and recent use is kept by title and number (S Semantics). The duplicate rule is enforced by the locked check, not by a unique index: churches already have hymns that differ only in spacing or capitals (Streamlit never checked), on which a unique index's migration would fail (owner question 12).
22. **[owner-visible] Every new user-facing string** (no em dashes; owner question 13). Settings nav: "Hymns". Page: "Hymns"; "The hymnals and hymns the builder offers when you choose hymns."; "Hymnals"; "Default"; "{n} hymns" / "1 hymn"; "{total} hymns in {n} hymnals." / "… in 1 hymnal."; "Your church has no hymnals yet."; "Default. Change it in Church profile."; "Remove…"; "Add a hymnal"; "Admins can add bundled hymnals."; "Hymnals this app can add to your church, with their hymns."; "This hymnal has no scripture references, so “Hymns for the readings” and AI suggestions work less well with it."; "Add"; "Added"; "Adding…"; "Done"; "Still working. This can take up to a minute."; "No bundled hymnals are available on this server."; "Added {code} ({n} hymns)."; "{code} is already added." (plan review I3); "Remove {code}?"; the removal body (clarification 6, with "This deletes the 1 hymn in {code} …" for one hymn, plan review M2); "Remove {code}"; "Removed {code}."; "Hymn library"; "Anyone in your church can add and edit hymns. Only admins can delete them."; "Add hymn"; "Search by title or number"; "Clear search"; "All"; "{n} matching hymns" / "1 matching hymn"; "Show more"; "Loading…"; "No hymns yet"; "Add hymns one at a time, or add a bundled hymnal above."; "Add hymns one at a time, or ask an admin to add a bundled hymnal."; "No hymns match “{q}”."; "Edit hymn"; "A hymn your church sings that is not in the list yet."; "Title"; "Number"; "Hymnal"; "Scripture references"; "e.g. Psalm 23; John 10:11-18"; "Used by “Hymns for the readings” and AI suggestions."; "Themes"; "e.g. Advent, hope"; "Link"; "https://hymnary.org/…"; "Year the words were written"; "Number of hymnals (familiarity)"; "Only admins can change this."; "Changes also appear in saved services that use this hymn."; "Delete hymn"; "Save changes"; "Delete “{title}”?"; "Saved services keep this hymn. Services in progress that use it will ask you to choose a replacement."; "Hymn added."; "Hymn updated."; "Hymn deleted."; "This hymn was already deleted."; on the Church page "Add hymns on the Hymns page"; screen readers: "Remove {code}", "Add {code}", the lists' "Hymnals", "Bundled hymnals" and "Hymns", the chips' group "Hymnal". From the server: "Hymn title is required."; "Hymn number must be a whole number."; "Choose one of your church's hymnals."; "Links must start with https://."; "Links can't contain spaces." (new); "Year must be a whole number from 1 to {year}."; "Number of hymnals must be a whole number from 0 to 100000."; "{hymnal} already has #{number} {title}." / "{hymnal} already has {title}."; "Hymn not found."; "That hymnal isn't available to add."; "Your church doesn't have that hymnal."; "You can't remove your only hymnal."; "{code} is your default hymnal. Choose a different default in Church profile first."; "Only church admins can do this.". Reused: "Cancel", "Saving…", "Retry", the skeleton's "Loading", "Not in your hymnal. Choose a replacement.".
23. **Docs.** T10 adds the 6a-2 items 9-15 to `docs/manual-verification.md` → "## Slice 6a" (no new `##` heading, so `test_slice1_docs.py`'s pin is unchanged). The runbook record is T12's (`### Slice 6a-2 record` before `## Backups`, after `### Slice 5b-2b record`), with the accepted renamed-hymn risk (answer 5).
24. **Deviations from S** (each the lean choice for 6a-2):
    - The hymn writes are in `usecases/hymn_library.py` and use 6a-1's `lock_and_read_actor`/`require_admin_role` as they are; S's `repos.hymns.add_hymn` with a session is not needed: the new `create_hymn` returns the typed `HymnRecord`, and `add_hymn` stays for the frozen Streamlit callers.
    - `HymnIn.title` is nullable (clarification 15); `HymnalAddedOut`, `HymnalSourceList` and `HymnalRemovedOut` are named models.
    - Text is tidied onto one line, and a link with a space has its own message (clarification 11).
    - The duplicate check compares the title's words (clarification 12), and an edit runs it only when the key changes.
    - The import fills only blanks and carries the catalog's facts (clarification 17).
    - The library's caption mentions that only admins delete; the empty state has no second **Add hymn**; a hymn without a number shows its title alone; the dialogs are bottom sheets on phones; members see the facts read-only with a note (clarifications 7, 8).
    - S's `rebaseForm` and leave guard are not used: the hymn dialog is modal and its Cancel discards (the 5b-1 edit dialog's rule).
    - S's Postgres "under 10 s" check is its own test (T5), beside a held-lock test and S's barrier tests.

### Risks
- **Renamed hymns and the 12-week rule** (S Risk 2; answer 5: accepted, recorded in T12). Recent use is kept by title and number, so after a hymn is renamed or renumbered its past uses no longer match and it may be suggested again inside 12 weeks. A later fix keys use by hymn id (a schema change).
- **Hymn edits change saved services** (S Risk 3; answer 4): accepted, and the edit dialog says so. Deleting a hymn does not change them.
- **Removing a hymnal deletes the church's edits to its hymns**; adding it back brings the bundled rows. The confirmation says so.
- **A hymn moved to another hymnal** looks deleted to a draft that picked it (clarification 19).
- **PH1990 has no scripture references**, so "Hymns for the readings" and AI suggestions find little in it; the Add dialog says so.
- **SQLite ignores `FOR UPDATE`.** Only CI's `backend-postgres` proves the lock; T3 checks that each write reads the church row with it.
- **Import speed on the Supabase pooler** (S Risk 5). T5 times a 605-row add on CI's Postgres; if adding PH1990 is ever slow in production, switch the import to one Core `insert()` (as `seed_church_from_catalog` does).
- **Five section links on a phone** may wrap to two rows at 375 px (clarification 2).
- **The default hymnal can change without a word** (plan review M3; noted, not refused). The effective default is the stored one while the church has a hymn in it, else the first hymnal by code. Removing a whole hymnal refuses the effective default, but deleting its last hymn, or moving that hymn to another hymnal, is an ordinary hymn write, so the builder then opens with another hymnal and the Church page shows the stored code as "no longer in your hymnals". Refusing it would need a count per write and a new message; the record notes it (T12 Step 8) and the owner can set the default again in Church profile.
- **Adding a bundled hymnal again after a hymn of it was renamed** (plan review M6; noted). The import matches a church's hymn by number and title words, so a renamed bundled hymn ("Amazing Grace!" for "Amazing Grace") no longer matches its bundled row, and adding the hymnal again inserts the bundled title as a second hymn with the same number. Deleting the extra one in the library undoes it; the record notes it (T12 Step 8).

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/hymnal_sources.py` (+ `backend/tests/test_hymnal_sources.py`) | the bundled and catalog hymnals, `load_rows`, `rows_for` | T1 |
| `backend/seed/hymnals/PH1990.csv` (moved from `data/hymnals/PH1990_hymns.csv`) | the bundled PH1990 | T1 |
| `data/.gitkeep` (empty) | keeps `data/`, where the local SQLite database lives, once the CSV has left it | T1 |
| `backend/tests/test_import_hymnal_cli.py` | the CLI without `--csv`, and no `.env` read at import | T1 |
| `backend/usecases/hymn_library.py` (+ `backend/tests/test_hymn_library.py`) | the field rules, the duplicate rule, the six hymn and hymnal usecases | T3 |
| `backend/tests/test_api_hymns_admin.py`, `backend/tests/test_api_hymnals_admin.py` | the routes over HTTP | T4 |
| `backend/tests/test_hymn_library_postgres.py` | the lock on real Postgres, the 605-row timing | T5 |
| `frontend/src/lib/settings/hymns.ts` (+ `.test.ts`), `frontend/src/lib/queries/hymn-library.ts` | the forms' rules; the library query, the sources and the five writes | T6 |
| `frontend/src/components/settings/hymnals-card.tsx`, `hymns-settings-page.tsx` (+ `.test.tsx`), `frontend/src/app/(signed-in)/(church)/settings/hymns/page.tsx` | the Hymnals card, the page and its route | T7 |
| `frontend/src/components/settings/hymn-library.tsx` (+ `.test.tsx`), `hymn-dialog.tsx` | the Hymn library and the add and edit dialog | T8 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/import_hymnal.py`, `backend/tests/test_no_streamlit_in_core.py` | the CLI uses `hymnal_sources`; `hymnal_sources` (T1), `usecases.hymn_library` (T3) | T1, T3 |
| `backend/repos/hymns.py`, `backend/tests/test_hymns_repo.py` | `title_key`, the import, `get_hymn`, `create_hymn`, `patch_hymn`, `find_duplicate`, `delete_hymnal`, `delete_hymn`'s session; five tests | T2 |
| `backend/api/routes/hymns.py`, `backend/api/routes/hymnals.py`, `backend/tests/test_api_hymnals.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | the routes; `label`; regenerated | T4 |
| `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/timeouts.ts`, `frontend/src/test/fixtures/index.ts` | the type names; `POST /hymnals` 60 s; `hymnDetail()`, `hymnalSource()`, `hymnalSources()` | T6 |
| `frontend/src/components/settings/hymns-settings-page.tsx` | the library on the page | T8 |
| `frontend/src/components/settings/sections.ts`, `settings-layout.test.tsx`, `church-settings-page.tsx` (+ `.test.tsx`), `frontend/src/lib/features.ts`, `frontend/src/components/builder/hymns/hymns-step.test.tsx` | **Hymns** in the nav; the two links | T9 |
| `docs/manual-verification.md` | the 6a-2 items | T10 |
| `docs/ops-runbook.md` | "### Slice 6a-2 record" (the records PR, after the merge) | T12 |

**Counts in the PR:** 42 paths: 20 added (this plan, the eighteen new code and test files above and the empty `data/.gitkeep`), 21 modified (the nineteen code, test, API and docs paths above, `docs/manual-verification.md` among them, plus the 6a spec (its amendment of 2026-10-07) and `docs/ops-runbook.md` (the 5b-2b record), which ride along until merged) and 1 renamed (the CSV, listed once as `R100`). **Untouched:** migrations, `db/models.py`, `api/deps.py`, `api/schemas.py`, `usecases/hymns.py`, `usecases/church_admin.py`, `usecases/members.py`, `repos/churches.py`, `hymnary_facts.py`, `backfill_hymn_facts.py`, `lib/queries/hymns.ts`, `lib/queries/keys.ts`, the draft schema, `app.py`, `streamlit_views`, `streamlit_tests`.

**Task order and review batch:** T1 → T10, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T11 verifies and opens the draft PR on the owner's yes; T12 merges on the owner's yes, runs the phone check and writes the record.

---

## The server (T1-T5)

### Task 1: The bundled hymnals under `backend/`, `hymnal_sources.py` and the CLI (S "New modules" `hymnal_sources.py`, the seed file, "Changed modules" `import_hymnal.py`; clarifications 16, 18)

**Files:**
- Create: `backend/tests/test_hymnal_sources.py`, `backend/tests/test_import_hymnal_cli.py`, `backend/hymnal_sources.py`
- Move: `data/hymnals/PH1990_hymns.csv` → `backend/seed/hymnals/PH1990.csv`
- Create (empty): `data/.gitkeep`
- Modify: `backend/tests/test_no_streamlit_in_core.py`, `backend/import_hymnal.py` (rewritten)

- [ ] **Step 1: Write the failing tests**

`test_hymnal_sources.py` pins S's list: the file under `backend/` with 605 rows (`data/hymnals` gone, `data/` kept by its `.gitkeep`), a byte order mark that no longer hides `number`, Hymnary links built from the code, `file_sources()` with no database (in a subprocess without `DATABASE_URL`), and the catalog merged with the files (a file winning PH1990). `test_import_hymnal_cli.py` runs `main()` without `--csv` for PH1990 twice (605, then 0), with `--csv` for another code, and reads the module's source: no top-level `load_dotenv()` and no `data/hymnals` path; `dotenv.load_dotenv` is a no-op in it, so a developer's `.env` never reaches the tests.

**Create `backend/tests/test_hymnal_sources.py`:**

````python
"""hymnal_sources (6a spec, `hymnal_sources.py`; slice 6a-2): the bundled CSV
under backend/, the BOM-safe loader, and the file and catalog sources."""
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

import hymnal_sources
from db import session_scope
from db.models import HymnCatalog

CODE_DIR = Path(__file__).resolve().parents[1]


def test_the_bundled_ph1990_ships_under_backend_and_loads_605_rows():
    path = CODE_DIR / "seed" / "hymnals" / "PH1990.csv"
    assert path == hymnal_sources.SEED_DIR / "PH1990.csv" and path.is_file()
    assert not (CODE_DIR.parent / "data" / "hymnals").exists()
    assert (CODE_DIR.parent / "data" / ".gitkeep").is_file()    # data/ stays for the local SQLite database
    rows = hymnal_sources.load_rows(path, "PH1990")
    assert len(rows) == 605
    assert rows[0] == {"number": "1", "title": "Come, Thou long-expected Jesus", "scripture_refs": None,
                       "theme": None, "hymnary_link": "https://hymnary.org/hymn/PH1990/1"}
    assert rows[-1]["hymnary_link"] == "https://hymnary.org/hymn/PH1990/605"


def test_a_byte_order_mark_does_not_hide_the_number_column(tmp_path):
    path = tmp_path / "X1.csv"
    path.write_bytes("\ufeffnumber,title,scripture_refs\n7,Be Thou My Vision,Psalm 16\n,No Number,\n,,\n"
                     .encode("utf-8"))
    rows = hymnal_sources.load_rows(path, "X1")
    assert [(r["number"], r["title"], r["scripture_refs"], r["hymnary_link"]) for r in rows] == [
        ("7", "Be Thou My Vision", "Psalm 16", "https://hymnary.org/hymn/X1/7"),
        (None, "No Number", None, None),
    ]
    stream = io.StringIO("\ufeffnumber,title,topics\n8,Here I Am,Call\n")
    assert hymnal_sources.load_rows(stream, "X1")[0]["number"] == "8"
    assert hymnal_sources.load_rows(io.StringIO("number,title,topics\n8,Here I Am,Call\n"), "X1")[0]["theme"] == "Call"


def test_file_sources_need_no_database():
    code = "import hymnal_sources; s = hymnal_sources.file_sources(); print(sorted(s), len(s['PH1990']))"
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "TEST_DATABASE_URL")}
    result = subprocess.run([sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['PH1990'] 605"


def test_sources_list_files_and_catalog_hymnals_a_file_winning_its_code(tmp_db):
    with session_scope() as s:
        for n, refs in ((1, "Psalm 1"), (2, None), (3, "  ")):
            s.add(HymnCatalog(hymnal="GG2013", title=f"Catalog {n}", number=n, scripture_refs=refs))
        s.add(HymnCatalog(hymnal="PH1990", title="A catalog copy", number=1))
    with session_scope() as s:
        listed = hymnal_sources.list_bundled(session=s)
        assert listed == [
            hymnal_sources.BundledSource("GG2013", "Glory to God (2013)", 3, True),
            hymnal_sources.BundledSource("PH1990", "The Presbyterian Hymnal (1990)", 605, False),
        ]
        assert len(hymnal_sources.rows_for("PH1990", session=s)) == 605          # the file, not the catalog row
        assert [(r["number"], r["title"]) for r in sorted(hymnal_sources.rows_for("GG2013", session=s),
                                                           key=lambda r: r["number"])] == [
            (1, "Catalog 1"), (2, "Catalog 2"), (3, "Catalog 3")]
        with pytest.raises(KeyError):
            hymnal_sources.rows_for("XX2000", session=s)
````

**Create `backend/tests/test_import_hymnal_cli.py`:**

````python
"""import_hymnal.py, the ops CLI kept beside Settings → Hymns (6a spec;
slice 6a-2): a bundled hymnal needs no --csv, and importing the module reads
no .env file."""
import ast
from pathlib import Path

import pytest

import import_hymnal
from repos.hymns import list_hymns


@pytest.fixture(autouse=True)
def no_dotenv(monkeypatch):
    """main() reads a .env file; a developer's must not reach the tests."""
    monkeypatch.setattr("dotenv.load_dotenv", lambda *args, **kwargs: False)


def test_a_bundled_hymnal_imports_without_csv_and_again_adds_nothing(tmp_db, make_church, capsys):
    cid = make_church(name="Grace")
    import_hymnal.main(["--church-id", str(cid), "--hymnal", "PH1990"])
    assert len(list_hymns(cid, hymnal="PH1990")) == 605
    import_hymnal.main(["--church-id", str(cid), "--hymnal", "PH1990"])
    out = capsys.readouterr().out
    assert "Imported PH1990: {'inserted': 605, 'updated': 0, 'total': 605}" in out
    assert "Imported PH1990: {'inserted': 0, 'updated': 0, 'total': 0}" in out
    assert len(list_hymns(cid, hymnal="PH1990")) == 605


def test_a_csv_is_still_required_for_a_hymnal_that_is_not_bundled(tmp_db, make_church, tmp_path, capsys):
    cid = make_church(name="Grace")
    with pytest.raises(SystemExit):
        import_hymnal.main(["--church-id", str(cid), "--hymnal", "XX2000"])
    assert "--csv is required: XX2000 is not a bundled hymnal (PH1990)" in capsys.readouterr().err
    path = tmp_path / "XX2000.csv"
    path.write_text("number,title\n1,First Hymn\n", encoding="utf-8")
    import_hymnal.main(["--church-id", str(cid), "--hymnal", "XX2000", "--csv", str(path)])
    assert [h["Hymn Title"] for h in list_hymns(cid, hymnal="XX2000")] == ["First Hymn"]


def test_importing_the_module_does_not_load_a_dotenv_file():
    tree = ast.parse(Path(import_hymnal.__file__).read_text(encoding="utf-8"))
    top_level_calls = [node.value.func.id for node in tree.body
                       if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                       and isinstance(node.value.func, ast.Name)]
    assert "load_dotenv" not in top_level_calls
    assert "data/hymnals" not in Path(import_hymnal.__file__).read_text(encoding="utf-8")
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email, hymnal_sources; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymnal_sources.py backend/tests/test_import_hymnal_cli.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected** (`hymnal_sources` does not exist yet: `ModuleNotFoundError` above these lines, so pytest stops at collection; then the import check names the missing module):
```
ERROR backend/tests/test_hymnal_sources.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```
```
1 failed, 2 passed in <t>s
```

- [ ] **Step 3: Move the file, then write the module and the CLI**

Run first:

```bash
mkdir -p backend/seed/hymnals
git mv data/hymnals/PH1990_hymns.csv backend/seed/hymnals/PH1990.csv
rmdir data/hymnals
touch data/.gitkeep
```

`data/` itself stays: the README and `backend/.env.example` put the local SQLite database at `sqlite:///../data/app.db`, and `db/engine.py` falls back to `sqlite:///data/church.db`, so `data/.gitkeep` keeps the folder in a fresh checkout once the CSV has moved out of it.

**Create `backend/hymnal_sources.py`:**

````python
"""The hymnals a church can add from Settings → Hymns (6a spec, `hymnal_sources.py`;
slice 6a-2): the bundled CSV files and the shared catalog.

- File sources: one per `seed/hymnals/<CODE>.csv` (PH1990 today), read once
  and kept (`file_sources`, no database). A CSV needs `number` and `title`;
  `scripture_refs` and `theme` (or `topics`) are optional; a Hymnary.org
  link is built from the code and the number. Files are read as `utf-8-sig`,
  so a byte order mark does not hide the `number` column.
- Catalog sources: each hymnal in `hymn_catalog` (GG2013 in production), the
  rows a new church is seeded with. A file source wins over a catalog source
  with the same code.

`rows_for(code)` gives the rows `repos.hymns.import_hymns` takes. Railway
deploys only `backend/`, so the CSVs live under it. No FastAPI, Starlette or
Streamlit here.
"""
import csv
import functools
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO, Union

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from db.models import HymnCatalog

SEED_DIR = Path(__file__).parent / "seed" / "hymnals"

# Names shown beside a code; a code without one shows the code alone.
HYMNAL_LABELS = {
    "GG2013": "Glory to God (2013)",
    "PH1990": "The Presbyterian Hymnal (1990)",
}


@dataclass(frozen=True)
class BundledSource:
    code: str
    label: Optional[str]
    hymn_count: int
    has_scripture_refs: bool


def label_for(code: str) -> Optional[str]:
    return HYMNAL_LABELS.get(code)


def load_rows(source: Union[Path, str, TextIO], hymnal: str) -> list[dict]:
    """The rows of a hymnal CSV (a path or an open text stream), in file order;
    a row without a title is skipped. Each row: number (the text, or None),
    title, scripture_refs, theme, hymnary_link."""
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8-sig", newline="") as f:
            return load_rows(f, hymnal)
    text = source.read()
    if text.startswith("\ufeff"):              # a stream opened without utf-8-sig
        text = text[1:]
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        number = (r.get("number") or "").strip()
        title = (r.get("title") or "").strip()
        if not title:
            continue
        rows.append({
            "number": number or None,
            "title": title,
            "scripture_refs": (r.get("scripture_refs") or "").strip() or None,
            "theme": (r.get("theme") or r.get("topics") or "").strip() or None,
            "hymnary_link": f"https://hymnary.org/hymn/{hymnal}/{number}" if number else None,
        })
    return rows


@functools.lru_cache(maxsize=1)
def file_sources() -> dict[str, tuple[dict, ...]]:
    """Each bundled CSV's rows by code (the file name without `.csv`), read once."""
    return {path.stem: tuple(load_rows(path, path.stem)) for path in sorted(SEED_DIR.glob("*.csv"))}


def list_bundled(*, session: Session) -> list[BundledSource]:
    """Every hymnal a church can add, by code: the file sources and the
    catalog's hymnals (counted in SQL), a file winning a shared code."""
    has_refs = case((func.trim(func.coalesce(HymnCatalog.scripture_refs, "")) != "", 1), else_=0)
    found: dict[str, BundledSource] = {}
    for code, count, refs in session.execute(
        select(HymnCatalog.hymnal, func.count(), func.coalesce(func.sum(has_refs), 0))
        .where(HymnCatalog.hymnal != "")
        .group_by(HymnCatalog.hymnal)
    ).all():
        found[code] = BundledSource(code, label_for(code), int(count), int(refs) > 0)
    for code, rows in file_sources().items():
        found[code] = BundledSource(code, label_for(code), len(rows),
                                    any(r["scripture_refs"] for r in rows))
    return [found[code] for code in sorted(found)]


def rows_for(code: str, *, session: Session) -> list[dict]:
    """The rows to import for `code`: the file's, else the catalog's. KeyError
    when no source has that code."""
    files = file_sources()
    if code in files:
        return [dict(r) for r in files[code]]
    catalog = session.execute(
        select(HymnCatalog.title, HymnCatalog.number, HymnCatalog.scripture_refs, HymnCatalog.theme,
               HymnCatalog.hymnary_link, HymnCatalog.audio_url, HymnCatalog.text_year,
               HymnCatalog.hymnal_count)
        .where(HymnCatalog.hymnal == code)
    ).all()
    if not catalog:
        raise KeyError(code)
    return [{"number": c.number, "title": c.title, "scripture_refs": c.scripture_refs, "theme": c.theme,
             "hymnary_link": c.hymnary_link, "audio_url": c.audio_url, "text_year": c.text_year,
             "hymnal_count": c.hymnal_count} for c in catalog]
````

**Replace `backend/import_hymnal.py`:**

````python
#!/usr/bin/env python3
"""Import a hymnal CSV into a church's hymnal (idempotent, re-runnable).

An ops tool with no role check, run only by the owner against the production
DATABASE_URL (6a spec, `import_hymnal.py`). Admins add bundled hymnals in the
app (Settings → Hymns); this CLI stays for other CSVs.

CSV needs at least `number` and `title`; optional `scripture_refs`, `theme`.
A Hymnary.org link is constructed per hymn from --hymnal + number. --csv may
be left out for a bundled hymnal (backend/seed/hymnals/<CODE>.csv):

    python import_hymnal.py --church-id <uuid> --hymnal PH1990
    python import_hymnal.py --church-id <uuid> --hymnal XX2000 --csv path/to/XX2000.csv
"""
import argparse

import hymnal_sources


def load_rows(csv_path: str, hymnal: str) -> list:
    return hymnal_sources.load_rows(csv_path, hymnal)


def main(argv=None):
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(description="Import a hymnal CSV into a church.")
    parser.add_argument("--church-id", required=True)
    parser.add_argument("--hymnal", required=True, help="e.g. PH1990")
    parser.add_argument("--csv", help="the CSV to import; optional for a bundled hymnal")
    args = parser.parse_args(argv)
    bundled = hymnal_sources.file_sources()
    if args.csv is None and args.hymnal not in bundled:
        parser.error(f"--csv is required: {args.hymnal} is not a bundled hymnal ({', '.join(sorted(bundled))})")

    from db import init_db
    from repos.hymns import import_hymns, list_church_hymnals

    init_db()
    rows = load_rows(args.csv, args.hymnal) if args.csv else [dict(r) for r in bundled[args.hymnal]]
    report = import_hymns(args.church_id, args.hymnal, rows)
    print(f"Imported {args.hymnal}: {report}")
    print(f"Church now has hymnals: {list_church_hymnals(args.church_id)}")


if __name__ == "__main__":
    main()
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymnal_sources.py backend/tests/test_import_hymnal_cli.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_hymnals.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
13 passed in <t>s
```
```
1832 passed, 27 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/hymnal_sources.py backend/import_hymnal.py backend/seed/hymnals/PH1990.csv backend/tests/test_hymnal_sources.py backend/tests/test_import_hymnal_cli.py backend/tests/test_no_streamlit_in_core.py data/.gitkeep
git commit -q -m "Slice 6a-2: the bundled hymnals under backend/ and hymnal_sources" -m "The PH1990 CSV moves (unchanged) to backend/seed/hymnals/PH1990.csv,
since Railway deploys only backend/; data/.gitkeep keeps data/, where
the local SQLite database lives. hymnal_sources lists what an admin
can add: each seed CSV (read once, utf-8-sig so a byte order mark does
not hide the number column) and each hymn_catalog hymnal, a file winning
a shared code, with rows_for(code) and the hymnals' labels.
import_hymnal.py uses it, reads .env only in main(), and needs --csv
only for a hymnal that is not bundled." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1832 passed, 27 skipped`; frontend `835 passed` in 100 files.

### Task 2: The hymn repo: the import, the duplicate key, the typed writes (S "Changed modules" `repos/hymns.py`; clarifications 12, 17)

**Files:**
- Modify: `backend/tests/test_hymns_repo.py`, `backend/repos/hymns.py`

- [ ] **Step 1: Write the failing tests**

Five tests are appended; the fifteen existing ones stay. The import keeps a church's own values and fills only blanks (a year on a hymn with references and a link), matches a title by its words in any case and spacing, adds a repeated row once, and skips a blank title; a 605-row import into the caller's session flushes exactly once (the old import flushed after every new row). `create_hymn`, `get_hymn` and `patch_hymn` are church-scoped and keep what is not sent (`audio_url` among it); `find_duplicate` compares the number (or no number) and the title's words, inside one hymnal, leaving one id out; `delete_hymnal` and `delete_hymn` touch only the church, in the caller's session.

**Append to `backend/tests/test_hymns_repo.py`:**

````python


# --- slice 6a-2: the hymn library's writes and the import (6a spec, `repos/hymns.py`) ---

from repos import hymns as hymn_repo  # noqa: E402


def test_an_import_adds_once_fills_only_blanks_and_matches_titles_by_their_words(tmp_db, make_church):
    cid = make_church()
    mine = _hymn(cid, "PH1990", "Amazing Grace", 280, refs="John 9:25", hymnary_link="https://example.org/mine")
    blank = _hymn(cid, "PH1990", "Be Thou My Vision", 339, refs="  ")
    rows = [{"number": "280", "title": "  amazing \tGRACE ", "scripture_refs": "Ephesians 2:8",
             "hymnary_link": "https://hymnary.org/hymn/PH1990/280", "text_year": 1779},
            {"number": 339, "title": "Be Thou\nMy Vision", "scripture_refs": "Psalm 16:5"},
            {"number": "1", "title": "Come,  Thou long-expected Jesus", "theme": "Advent"},
            {"number": "1", "title": "come, thou long-expected jesus"},
            {"number": "", "title": "   "}]
    assert hymn_repo.import_hymns(cid, "PH1990", rows) == {"inserted": 1, "updated": 2, "total": 3}
    with session_scope() as s:
        kept = s.get(Hymn, mine)
        assert (kept.title, kept.scripture_refs, kept.hymnary_link, kept.text_year) == (
            "Amazing Grace", "John 9:25", "https://example.org/mine", 1779)    # only the blank year filled
        assert s.get(Hymn, blank).scripture_refs == "Psalm 16:5"
        new = s.execute(select(Hymn).where(Hymn.church_id == cid, Hymn.number == 1)).scalar_one()
        assert (new.title, new.theme) == ("Come, Thou long-expected Jesus", "Advent")
    assert hymn_repo.import_hymns(cid, "PH1990", rows) == {"inserted": 0, "updated": 0, "total": 0}


def test_an_import_flushes_once_in_the_callers_session(tmp_db, make_church):
    cid = make_church()
    flushes = []
    with session_scope() as s:
        event.listen(s, "before_flush", lambda *_args: flushes.append(1))
        report = hymn_repo.import_hymns(cid, "PH1990", [{"number": n, "title": f"Hymn {n}"} for n in range(1, 606)],
                                        session=s)
        assert report["inserted"] == 605 and len(flushes) == 1
    assert len(list_hymns(cid, hymnal="PH1990")) == 605


def test_create_get_and_patch_are_church_scoped_and_keep_what_is_not_sent(tmp_db, make_church):
    mine, other = make_church(), make_church(name="Other")
    created = hymn_repo.create_hymn(mine, {"title": "Holy, Holy, Holy", "number": 138, "hymnal": "GG2013",
                                           "scripture_refs": "Isaiah 6:3", "theme": "Trinity",
                                           "link": "https://hymnary.org/hymn/GG2013/138", "text_year": 1826,
                                           "hymnal_count": None})
    assert isinstance(created, HymnRecord)
    assert (created.title, created.number, created.link, created.text_year) == (
        "Holy, Holy, Holy", 138, "https://hymnary.org/hymn/GG2013/138", 1826)
    with session_scope() as s:
        s.get(Hymn, created.id).audio_url = "https://example.org/holy.mp3"
    patched = hymn_repo.patch_hymn(created.id, mine, {"number": None, "theme": None, "hymnal_count": 1322})
    assert (patched.title, patched.number, patched.theme, patched.scripture_refs, patched.hymnal_count) == (
        "Holy, Holy, Holy", None, None, "Isaiah 6:3", 1322)
    with session_scope() as s:
        assert s.get(Hymn, created.id).audio_url == "https://example.org/holy.mp3"
    assert hymn_repo.get_hymn(created.id, mine) == patched
    assert hymn_repo.get_hymn(created.id, other) is None
    assert hymn_repo.patch_hymn(created.id, other, {"title": "Theirs"}) is None
    assert hymn_repo.get_hymn(created.id, mine).title == "Holy, Holy, Holy"
    with pytest.raises(NotFound):
        hymn_repo.get_hymn("not-a-uuid", mine)


def test_find_duplicate_compares_the_number_and_the_titles_words_in_one_hymnal(tmp_db, make_church):
    mine, other = make_church(), make_church(name="Other")
    holy = _hymn(mine, "GG2013", "Holy,  Holy, Holy\t", 138)
    _hymn(mine, "GG2013", "No Number", None)
    _hymn(other, "GG2013", "Theirs", 1)
    assert hymn_repo.find_duplicate(mine, "GG2013", 138, " holy, holy,\u00a0HOLY ")
    assert not hymn_repo.find_duplicate(mine, "GG2013", 138, "holy, holy, holy", exclude_id=holy)
    assert not hymn_repo.find_duplicate(mine, "GG2013", 139, "Holy, Holy, Holy")
    assert not hymn_repo.find_duplicate(mine, "PH1990", 138, "Holy, Holy, Holy")
    assert hymn_repo.find_duplicate(mine, "GG2013", None, "no number")
    assert not hymn_repo.find_duplicate(mine, "GG2013", 5, "no number")
    assert not hymn_repo.find_duplicate(mine, "GG2013", 1, "Theirs")


def test_delete_hymnal_and_delete_hymn_touch_only_the_church(tmp_db, make_church):
    mine, other = make_church(), make_church(name="Other")
    for n in (1, 2, 3):
        _hymn(mine, "PH1990", f"Mine {n}", n)
    kept = _hymn(mine, "GG2013", "Kept", 1)
    theirs = _hymn(other, "PH1990", "Theirs", 1)
    with session_scope() as s:
        assert hymn_repo.delete_hymnal(mine, "PH1990", session=s) == 3
    assert hymn_repo.delete_hymnal(mine, "PH1990") == 0
    assert [h.code for h in hymnal_summaries(mine)] == ["GG2013"]
    assert [h.code for h in hymnal_summaries(other)] == ["PH1990"]
    with session_scope() as s:
        assert not hymn_repo.delete_hymn(theirs, mine, session=s)
        assert hymn_repo.delete_hymn(kept, mine, session=s)
    assert hymnal_summaries(mine) == [] and len(hymnal_summaries(other)) == 1
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymns_repo.py 2>&1 | tail -1`
**Expected** (the new functions do not exist and the import still overwrites and flushes per row):
```
5 failed, 15 passed in <t>s
```

- [ ] **Step 3: Write the repo functions**

**In `backend/repos/hymns.py`, replace:**

````python
def import_hymns(church_id, hymnal: str, rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """Bulk-load a hymnal into a church. Idempotent per (church_id, hymnal, number,
    normalized title): re-running updates enrichment on matched rows instead of
    duplicating. `rows` keys: number, title (required), scripture_refs, theme,
    hymnary_link."""
    cid = _as_uuid(church_id)
    inserted = updated = 0
    with session_scope() as session:
        existing = session.execute(
            select(Hymn).where(Hymn.church_id == cid, Hymn.hymnal == hymnal)
        ).scalars().all()
        by_key = {(h.number, (h.title or "").strip().lower()): h for h in existing}
        for r in rows:
            title = (r.get("title") or "").strip()
````

**with:**

````python
def title_key(title: Optional[str]) -> str:
    """A title as the duplicate rule compares it: every run of whitespace one
    space (tabs, line breaks and no-break spaces included), trimmed, lower-cased."""
    return " ".join((title or "").split()).lower()


# What an import may fill in on a hymn it already has (never what makes it the same hymn).
_ENRICHMENT = ("scripture_refs", "theme", "hymnary_link", "audio_url", "text_year", "hymnal_count")


def import_hymns(church_id, hymnal: str, rows: List[Dict[str, Any]], *,
                 session: Optional[Session] = None) -> Dict[str, int]:
    """Bulk-load a hymnal into a church. Idempotent per (church_id, hymnal,
    number, title_key(title)): a row the church already has is not added
    again, and only its blank enrichment is filled in (a value an admin or
    member entered is kept; 6a spec, POST /hymnals). Never deletes. `rows`
    keys: number, title (required), scripture_refs, theme, hymnary_link, and
    optionally audio_url, text_year, hymnal_count.

    The new rows are flushed together at the end (no flush per row), so
    SQLAlchemy sends them as one batched INSERT (6a spec Risk 5)."""
    cid = _as_uuid(church_id)

    def work(s: Session) -> Dict[str, int]:
        inserted = updated = 0
        existing = s.execute(
            select(Hymn).where(Hymn.church_id == cid, Hymn.hymnal == hymnal)
        ).scalars().all()
        by_key = {(h.number, title_key(h.title)): h for h in existing}
        for r in rows:
            title = " ".join((r.get("title") or "").split())
````

**In `backend/repos/hymns.py`, replace:**

````python
            key = (number, title.lower())
            match = by_key.get(key)
            fields = dict(
                scripture_refs=r.get("scripture_refs") or None,
                theme=r.get("theme") or None,
                hymnary_link=r.get("hymnary_link") or None,
            )
            if match is None:
                h = Hymn(church_id=cid, hymnal=hymnal, title=title, number=number, **fields)
                session.add(h)
                session.flush()
                by_key[key] = h
                inserted += 1
            else:
                # only fill in enrichment we now have (don't wipe existing with blanks)
                changed = False
                for attr, val in fields.items():
                    if val and getattr(match, attr) != val:
                        setattr(match, attr, val)
                        changed = True
                if changed:
                    updated += 1
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}
````

**with:**

````python
            key = (number, title_key(title))
            match = by_key.get(key)
            fields = {attr: r.get(attr) for attr in _ENRICHMENT if r.get(attr) not in (None, "")}
            if match is None:
                h = Hymn(church_id=cid, hymnal=hymnal, title=title, number=number, **fields)
                s.add(h)
                by_key[key] = h
                inserted += 1
            else:
                blank = {attr: value for attr, value in fields.items()
                         if getattr(match, attr) is None or (isinstance(getattr(match, attr), str)
                                                             and not getattr(match, attr).strip())}
                for attr, value in blank.items():
                    setattr(match, attr, value)
                if blank:
                    updated += 1
        s.flush()
        return {"inserted": inserted, "updated": updated, "total": inserted + updated}

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)
````

**In `backend/repos/hymns.py`, replace:**

````python
def delete_hymn(hymn_id, church_id) -> bool:
    """Delete a hymn only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid)
        )
        return result.rowcount > 0
````

**with:**

````python
def delete_hymn(hymn_id, church_id, *, session: Optional[Session] = None) -> bool:
    """Delete a hymn only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)

    def work(s: Session) -> bool:
        result = s.execute(delete(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid))
        return result.rowcount > 0

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)
````

**In `backend/repos/hymns.py`, replace:**

````python
        return [_record(row) for row in rows if normalize_title(row.title) in wanted]

    return _in(session, work)
````

**with:**

````python
        return [_record(row) for row in rows if normalize_title(row.title) in wanted]

    return _in(session, work)


# --- slice 6a-2: the hymn library's writes (6a spec, `repos/hymns.py`) --------------
# Each runs in the caller's session (usecases.hymn_library, under the
# church-row lock) or its own; every one is church-scoped.

# The columns a hymn write may set: HymnRecord's names, `link` for hymnary_link.
_WRITABLE = {"title": Hymn.title, "number": Hymn.number, "hymnal": Hymn.hymnal,
             "scripture_refs": Hymn.scripture_refs, "theme": Hymn.theme, "link": Hymn.hymnary_link,
             "text_year": Hymn.text_year, "hymnal_count": Hymn.hymnal_count}


def _attr(name: str) -> str:
    return _WRITABLE[name].key


def get_hymn(hymn_id, church_id, *, session: Optional[Session] = None) -> Optional[HymnRecord]:
    """The church's hymn, or None (another church's id, a deleted hymn)."""
    hid, cid = as_uuid(hymn_id), as_uuid(church_id)

    def work(s: Session) -> Optional[HymnRecord]:
        row = s.execute(select(*_RECORD_COLUMNS).where(Hymn.id == hid, Hymn.church_id == cid)).first()
        return _record(row) if row is not None else None

    return _in(session, work)


def create_hymn(church_id, values: Dict[str, Any], *, session: Optional[Session] = None) -> HymnRecord:
    """Insert a hymn from `values` (keys of _WRITABLE, already cleaned) and return it."""
    cid = as_uuid(church_id)

    def work(s: Session) -> HymnRecord:
        h = Hymn(church_id=cid, **{_attr(name): value for name, value in values.items()})
        s.add(h)
        s.flush()
        return get_hymn(h.id, cid, session=s)

    return _in(session, work)


def patch_hymn(hymn_id, church_id, changes: Dict[str, Any], *,
               session: Optional[Session] = None) -> Optional[HymnRecord]:
    """Set only the keys in `changes` (keys of _WRITABLE, already cleaned);
    every other column, audio_url among them, is kept. None when the church
    has no such hymn."""
    hid, cid = as_uuid(hymn_id), as_uuid(church_id)

    def work(s: Session) -> Optional[HymnRecord]:
        h = s.execute(select(Hymn).where(Hymn.id == hid, Hymn.church_id == cid)).scalar_one_or_none()
        if h is None:
            return None
        for name, value in changes.items():
            setattr(h, _attr(name), value)
        s.flush()
        return get_hymn(hid, cid, session=s)

    return _in(session, work)


def find_duplicate(church_id, hymnal: str, number: Optional[int], title: str, *, exclude_id=None,
                   session: Optional[Session] = None) -> bool:
    """True when the church already has a hymn in `hymnal` with this number
    (or, for None, with no number) whose title_key equals title_key(title),
    other than `exclude_id`. The titles are compared in Python, because SQL's
    trim and lower do not treat tabs, line breaks or every letter the same way
    on SQLite and Postgres (the import uses the same key)."""
    cid = as_uuid(church_id)
    wanted = title_key(title)
    conditions = [Hymn.church_id == cid, Hymn.hymnal == hymnal,
                  Hymn.number.is_(None) if number is None else Hymn.number == number]
    if exclude_id is not None:
        conditions.append(Hymn.id != as_uuid(exclude_id))

    def work(s: Session) -> bool:
        titles = s.execute(select(Hymn.title).where(*conditions)).scalars().all()
        return any(title_key(t) == wanted for t in titles)

    return _in(session, work)


def delete_hymnal(church_id, hymnal: str, *, session: Optional[Session] = None) -> int:
    """Delete every hymn of the church in `hymnal`; the number deleted."""
    cid = as_uuid(church_id)

    def work(s: Session) -> int:
        return s.execute(delete(Hymn).where(Hymn.church_id == cid, Hymn.hymnal == hymnal)).rowcount

    return _in(session, work)
````

- [ ] **Step 4: See them pass, and the suite**

`test_hymnals.py` (slice 1's import test), the CLI's tests, the backfill tests and the frozen Streamlit tests (which call `add_hymn`, `delete_hymn` and `list_hymns` positionally) run unchanged.

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymns_repo.py backend/tests/test_hymnals.py backend/tests/test_import_hymnal_cli.py backend/tests/test_hymnary_facts.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q streamlit_tests 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
93 passed in <t>s
```
```
35 passed in <t>s
```
```
1837 passed, 27 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/repos/hymns.py backend/tests/test_hymns_repo.py
git commit -q -m "Slice 6a-2: the hymn repo's writes, and an import that fills only blanks" -m "title_key (the title's words, any spacing, lower-cased) is the one
duplicate key: find_duplicate compares it in Python within a hymnal and
number, and import_hymns uses it too. The import takes a session, adds
new rows with one flush at the end (one batched INSERT on Postgres) and
fills only blank details on a hymn the church has, so a church's edits
survive adding a hymnal again; it carries a catalog row's year,
familiarity and audio. New: get_hymn, create_hymn, patch_hymn (only the
keys given) and delete_hymnal; delete_hymn takes a session." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1837 passed, 27 skipped`; frontend `835 passed` in 100 files.

### Task 3: The hymn library usecases: the rules, who may do what, the locked writes (S "Semantics"; clarifications 11-14, 16)

**Files:**
- Create: `backend/tests/test_hymn_library.py`, `backend/usecases/hymn_library.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

- [ ] **Step 1: Write the failing tests**

The tests follow S's Testing list for `test_hymn_library.py`: a member adds a hymn with its text tidied and blanks as NULL; each bad field is named with S's message and nothing is added (13 cases); the hymnal defaults to the effective one (alphabetical, then the stored default) and a church with no hymns may name a code (GG2013 when none); an admin sets the year and familiarity, a member gets the role 403 for either; the duplicate 409 with and without a number; an edit changes only what is sent and null clears; an edit's field, hymnal and duplicate checks (moving to another hymnal, and an old twin that does not block an edit of the references); an old hymn with a blank title (null, a space or empty) is never a duplicate on an edit (plan review M8); a member's facts, even null, are refused; a hand-entered year survives `hymnary_facts.run_backfill` (with S's faked Hymnary answer, `FakeFetch`); only admins delete, and another church's hymn is 404; PH1990 added once (605, then 0) and an unknown code refused; the catalog source and `present` in S's setup order; removing a hymnal (only this church's, never the only or the default, 404 for an unknown code); a member, a demoted admin, a removed member and a deleted church; and each write reading the church row under its lock, in one session (with `tests.test_church_settings._record_church_row_access`).

**Create `backend/tests/test_hymn_library.py`:**

````python
"""usecases.hymn_library (6a spec "Semantics" → POST and PATCH /hymns, POST and
DELETE /hymnals; slice 6a-2): the field rules, the duplicate rule, who may do
what, the bundled hymnals, and every write under the church-row lock with the
caller's role re-read under it."""
from datetime import date

import pytest
from sqlalchemy import select

import hymnary_facts
from db import session_scope
from db.models import Hymn, HymnCatalog
from domain_errors import Conflict, Forbidden, InvalidInput, NotFound
from repos import churches
from repos.hymns import hymnal_summaries, list_hymns
from repos.memberships import add_membership, remove_membership, set_role
from tests.test_church_settings import _record_church_row_access
from tests.test_hymnary_facts import HOLY, FakeFetch
from usecases import hymn_library

NO_ACCESS = {"reason": "no_church_access"}
THIS_YEAR = date.today().year
EMPTY = {"title": None, "number": None, "hymnal": None, "scripture_refs": None, "theme": None, "link": None,
         "text_year": None, "hymnal_count": None}


@pytest.fixture
def world(tmp_db, make_user, make_church):
    owner = make_user(email="owner@example.com")
    admin = make_user(email="admin@example.com")
    member = make_user(email="member@example.com")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(admin, cid, "admin")
    add_membership(member, cid, "member")
    with session_scope() as s:
        for n, title in ((1, "Holy, Holy, Holy"), (2, "Amazing Grace")):
            s.add(Hymn(church_id=cid, hymnal="GG2013", title=title, number=n))
    return {"church": cid, "owner": owner, "admin": admin, "member": member}


def _hymn(**fields) -> dict:
    return {**EMPTY, **fields}


def _add(world, who="member", **fields) -> dict:
    return hymn_library.create_hymn(world["church"], world[who], _hymn(**fields))


def _refused(call, field, message):
    with pytest.raises(InvalidInput) as bad:
        call()
    assert (bad.value.field, bad.value.message) == (field, message)


def _rows(world) -> list[tuple]:
    return [(h["Hymnal"], h["Hymn Number"], h["Hymn Title"]) for h in list_hymns(world["church"])]


def test_a_member_adds_a_hymn_with_tidy_fields_and_blanks_as_null(world):
    added = _add(world, title="  Be Thou\nMy\tVision ", number=339, scripture_refs="  Psalm 16:5;\n John 15:5 ",
                 theme=" ", link=" https://hymnary.org/hymn/GG2013/339 ")
    assert {k: v for k, v in added.items() if k != "id"} == {
        "hymnal": "GG2013", "title": "Be Thou My Vision", "number": 339, "scripture_refs": "Psalm 16:5; John 15:5",
        "theme": None, "link": "https://hymnary.org/hymn/GG2013/339", "text_year": None, "hymnal_count": None}
    bare = _add(world, title="No Number")
    assert (bare["number"], bare["link"], bare["scripture_refs"]) == (None, None, None)


@pytest.mark.parametrize("fields, field, message", [
    ({}, "title", "Hymn title is required."),
    ({"title": " \t\n"}, "title", "Hymn title is required."),
    ({"title": "X", "number": 0}, "number", "Hymn number must be a whole number."),
    ({"title": "X", "number": 100000}, "number", "Hymn number must be a whole number."),
    ({"title": "X", "hymnal": "PH1990"}, "hymnal", "Choose one of your church's hymnals."),
    ({"title": "X", "link": "http://hymnary.org/hymn/GG2013/1"}, "link", "Links must start with https://."),
    ({"title": "X", "link": "https://"}, "link", "Links must start with https://."),
    ({"title": "X", "link": "hymnary.org"}, "link", "Links must start with https://."),
    ({"title": "X", "link": "https://hymnary.org/a b"}, "link", "Links can't contain spaces."),
    ({"title": "X", "text_year": 0}, "text_year", f"Year must be a whole number from 1 to {THIS_YEAR}."),
    ({"title": "X", "text_year": THIS_YEAR + 1}, "text_year", f"Year must be a whole number from 1 to {THIS_YEAR}."),
    ({"title": "X", "hymnal_count": -1}, "hymnal_count", "Number of hymnals must be a whole number from 0 to 100000."),
    ({"title": "X", "hymnal_count": 100001}, "hymnal_count", "Number of hymnals must be a whole number from 0 to 100000."),
])
def test_a_bad_field_is_named_and_nothing_is_added(world, fields, field, message):
    _refused(lambda: _add(world, who="admin", **fields), field, message)
    assert len(_rows(world)) == 2


def test_the_hymnal_defaults_to_the_effective_one_and_a_church_with_none_may_name_one(world, make_church):
    with session_scope() as s:
        s.add(Hymn(church_id=world["church"], hymnal="AA2000", title="First by code", number=1))
    assert _add(world, title="Alphabetical")["hymnal"] == "AA2000"
    churches.update_profile(world["church"], settings_patch={"default_hymnal": "GG2013"})
    assert _add(world, title="Stored default")["hymnal"] == "GG2013"
    assert _add(world, title="Chosen", hymnal=" AA2000 ")["hymnal"] == "AA2000"

    empty = make_church(name="New", owner_user_id=world["owner"])
    assert hymn_library.create_hymn(empty, world["owner"], _hymn(title="First"))["hymnal"] == "GG2013"
    other = make_church(name="Newer", owner_user_id=world["owner"])
    assert hymn_library.create_hymn(other, world["owner"], _hymn(title="First", hymnal="XX_1990"))["hymnal"] == "XX_1990"
    _refused(lambda: hymn_library.create_hymn(make_church(name="N3", owner_user_id=world["owner"]), world["owner"],
                                              _hymn(title="First", hymnal="X")), "hymnal",
             "Choose one of your church's hymnals.")


def test_an_admin_sets_the_year_and_familiarity_and_a_member_may_not(world):
    added = _add(world, who="admin", title="Holy, Holy, Holy! Lord God Almighty", number=138, text_year=1826,
                 hymnal_count=1322)
    assert (added["text_year"], added["hymnal_count"]) == (1826, 1322)
    for facts in ({"text_year": 1826}, {"hymnal_count": 0}):
        with pytest.raises(Forbidden) as denied:
            _add(world, title="Member's", **facts)
        assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    assert _add(world, title="Member's", text_year=None, hymnal_count=None)["title"] == "Member's"
    assert len(_rows(world)) == 4


def test_the_same_hymnal_number_and_title_words_is_a_409(world):
    with pytest.raises(Conflict) as taken:
        _add(world, title="  holy,  HOLY, holy ", number=1)
    assert taken.value.message == "GG2013 already has #1 holy, HOLY, holy."
    _add(world, title="Untitled Tune")
    with pytest.raises(Conflict) as again:
        _add(world, title="untitled tune")
    assert again.value.message == "GG2013 already has untitled tune."
    assert _add(world, title="Holy, Holy, Holy", number=3)["number"] == 3        # another number is another hymn


def _first(world) -> dict:
    with session_scope() as s:
        h = s.execute(select(Hymn).where(Hymn.church_id == world["church"], Hymn.hymnal == "GG2013",
                                         Hymn.number == 1)).scalar_one()
        h.audio_url = "https://example.org/holy.mp3"
        h.scripture_refs, h.theme, h.hymnary_link = "Isaiah 6:3", "Trinity", "https://hymnary.org/hymn/GG2013/1"
        return {"id": h.id}


def test_an_edit_changes_only_what_is_sent_and_null_clears(world):
    hid = _first(world)["id"]
    edited = hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "Holy, Holy, Holy!"})
    assert (edited["title"], edited["number"], edited["scripture_refs"], edited["theme"], edited["link"]) == (
        "Holy, Holy, Holy!", 1, "Isaiah 6:3", "Trinity", "https://hymnary.org/hymn/GG2013/1")
    cleared = hymn_library.update_hymn(world["church"], world["member"], hid,
                                       {"number": None, "scripture_refs": "", "theme": None, "link": " "})
    assert (cleared["number"], cleared["scripture_refs"], cleared["theme"], cleared["link"]) == (None, None, None, None)
    facts = hymn_library.update_hymn(world["church"], world["admin"], hid, {"text_year": 1826, "hymnal_count": 1322})
    assert (facts["text_year"], facts["hymnal_count"]) == (1826, 1322)
    unknown = hymn_library.update_hymn(world["church"], world["owner"], hid, {"text_year": None})
    assert (unknown["text_year"], unknown["hymnal_count"]) == (None, 1322)
    with session_scope() as s:
        assert s.get(Hymn, hid).audio_url == "https://example.org/holy.mp3"


def test_an_edit_checks_its_fields_the_hymnal_and_duplicates_but_not_itself(world):
    hid = _first(world)["id"]
    for changes, field, message in (({"title": None}, "title", "Hymn title is required."),
                                    ({"title": "  "}, "title", "Hymn title is required."),
                                    ({"hymnal": None}, "hymnal", "Choose one of your church's hymnals."),
                                    ({"hymnal": "PH1990"}, "hymnal", "Choose one of your church's hymnals."),
                                    ({"number": 100000}, "number", "Hymn number must be a whole number.")):
        _refused(lambda: hymn_library.update_hymn(world["church"], world["member"], hid, changes), field, message)
    with pytest.raises(Conflict) as taken:
        hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "amazing grace", "number": 2})
    assert taken.value.message == "GG2013 already has #2 amazing grace."
    same = hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "HOLY, HOLY,  HOLY"})
    assert same["title"] == "HOLY, HOLY, HOLY"                                 # itself: no conflict
    with session_scope() as s:
        s.add(Hymn(church_id=world["church"], hymnal="PH1990", title="Holy, Holy, Holy", number=1))
        s.add(Hymn(church_id=world["church"], hymnal="GG2013", title="Holy, Holy, Holy", number=1))   # an old twin
    moved = hymn_library.update_hymn(world["church"], world["member"], hid, {"hymnal": "PH1990", "number": 5})
    assert (moved["hymnal"], moved["number"]) == ("PH1990", 5)
    twin = hymn_library.update_hymn(world["church"], world["member"], hid, {"scripture_refs": "Revelation 4:8"})
    assert twin["scripture_refs"] == "Revelation 4:8"                          # no key change: no duplicate check


def test_an_edit_of_an_old_hymn_with_a_blank_title_is_never_a_duplicate(world):
    with session_scope() as s:
        blank = [Hymn(church_id=world["church"], hymnal="GG2013", title=title, number=n)
                 for n, title in ((5, None), (6, " "), (7, ""))]
        s.add_all(blank)
        s.flush()
        ids = [h.id for h in blank]
    for hid in ids[1:]:
        moved = hymn_library.update_hymn(world["church"], world["member"], hid, {"number": 5})
        assert (moved["number"], moved["title"]) == (5, "")
    assert sorted(h["Hymn Number"] for h in list_hymns(world["church"]) if not (h["Hymn Title"] or "").strip()) == [
        5, 5, 5]


def test_a_member_may_not_send_the_year_or_familiarity_even_as_null(world):
    hid = _first(world)["id"]
    for changes in ({"text_year": 1826}, {"text_year": None}, {"hymnal_count": None, "title": "Renamed"}):
        with pytest.raises(Forbidden) as denied:
            hymn_library.update_hymn(world["church"], world["member"], hid, changes)
        assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    assert ("GG2013", 1, "Holy, Holy, Holy") in _rows(world)


def test_a_hand_entered_year_survives_the_backfill(world):
    hid = hymn_library.create_hymn(world["church"], world["admin"],
                                   _hymn(title=HOLY["title"], number=138, scripture_refs="Isaiah 6:3",
                                         text_year=1800))["id"]
    stats = hymnary_facts.run_backfill(FakeFetch({"Isaiah 6:3": {"Holy": HOLY}}))
    assert stats["updated"] == 1
    with session_scope() as s:
        holy = s.get(Hymn, hid)
        assert (holy.text_year, holy.hymnal_count) == (1800, 1322)


def test_only_admins_delete_a_hymn_and_an_unknown_or_another_churchs_is_not_found(world, make_church):
    hid = _first(world)["id"]
    with pytest.raises(Forbidden) as denied:
        hymn_library.delete_hymn(world["church"], world["member"], hid)
    assert denied.value.message == "Only church admins can do this."
    other = make_church(name="Other", owner_user_id=world["owner"])
    theirs = hymn_library.create_hymn(other, world["owner"], _hymn(title="Theirs"))["id"]
    for call in (lambda: hymn_library.delete_hymn(world["church"], world["owner"], theirs),
                 lambda: hymn_library.update_hymn(world["church"], world["owner"], theirs, {"text_year": 2000})):
        with pytest.raises(NotFound) as missing:
            call()
        assert missing.value.message == "Hymn not found."
    hymn_library.delete_hymn(world["church"], world["admin"], hid)
    with pytest.raises(NotFound):
        hymn_library.delete_hymn(world["church"], world["admin"], hid)
    assert _rows(world) == [("GG2013", 2, "Amazing Grace")]
    assert [h["Hymn Title"] for h in list_hymns(other)] == ["Theirs"]


def test_adding_ph1990_inserts_605_once_and_an_unknown_code_is_refused(world):
    assert hymn_library.add_hymnal(world["church"], world["admin"], "PH1990") == {
        "code": "PH1990", "label": "The Presbyterian Hymnal (1990)", "inserted": 605, "updated": 0}
    assert hymn_library.add_hymnal(world["church"], world["owner"], " PH1990 ")["inserted"] == 0
    assert [(h.code, h.hymn_count) for h in hymnal_summaries(world["church"])] == [("GG2013", 2), ("PH1990", 605)]
    _refused(lambda: hymn_library.add_hymnal(world["church"], world["owner"], "XX2000"), "code",
             "That hymnal isn't available to add.")


def test_catalog_hymnals_are_sources_and_present_follows_the_church(world, make_user, make_church):
    church_a = make_church(name="A", owner_user_id=world["owner"])
    with session_scope() as s:
        for n in (1, 2, 3):
            s.add(HymnCatalog(hymnal="GG2013", title=f"Catalog {n}", number=n, scripture_refs="Psalm 1",
                              text_year=1900 + n))
    church_b = churches.create_church(name="B", timezone="UTC", owner_user_id=make_user(email="b@example.com"))
    by_code = lambda church: {s["code"]: s for s in hymn_library.list_sources(church)}   # noqa: E731
    assert by_code(church_a)["GG2013"] == {"code": "GG2013", "label": "Glory to God (2013)", "hymn_count": 3,
                                           "has_scripture_refs": True, "present": False}
    assert by_code(church_a)["PH1990"] == {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)",
                                           "hymn_count": 605, "has_scripture_refs": False, "present": False}
    assert by_code(church_b)["GG2013"]["present"] is True
    assert hymn_library.add_hymnal(church_a, world["owner"], "GG2013")["inserted"] == 3
    assert by_code(church_a)["GG2013"]["present"] is True
    assert sorted(h["Hymn Number"] for h in list_hymns(church_a)) == [1, 2, 3]


def test_removing_a_hymnal_deletes_only_its_hymns_but_never_the_only_or_the_default(world, make_church):
    other = make_church(name="Other", owner_user_id=world["owner"])
    hymn_library.add_hymnal(other, world["owner"], "PH1990")
    with pytest.raises(Conflict) as only:
        hymn_library.remove_hymnal(other, world["owner"], "PH1990")
    assert only.value.message == "You can't remove your only hymnal."
    hymn_library.add_hymnal(world["church"], world["owner"], "PH1990")
    with pytest.raises(Conflict) as default:
        hymn_library.remove_hymnal(world["church"], world["owner"], "GG2013")            # alphabetical first
    assert default.value.message == ("GG2013 is your default hymnal. Choose a different default in Church "
                                     "profile first.")
    churches.update_profile(world["church"], settings_patch={"default_hymnal": "PH1990"})
    with pytest.raises(Conflict):
        hymn_library.remove_hymnal(world["church"], world["owner"], "PH1990")
    churches.update_profile(world["church"], settings_patch={"default_hymnal": "GG2013"})
    with pytest.raises(NotFound) as missing:
        hymn_library.remove_hymnal(world["church"], world["owner"], "XX2000")
    assert missing.value.message == "Your church doesn't have that hymnal."
    assert hymn_library.remove_hymnal(world["church"], world["admin"], "PH1990") == 605
    assert [h.code for h in hymnal_summaries(world["church"])] == ["GG2013"]
    assert [(h.code, h.hymn_count) for h in hymnal_summaries(other)] == [("PH1990", 605)]


def test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing(world):
    hymn_library.add_hymnal(world["church"], world["owner"], "PH1990")
    hid = _first(world)["id"]
    admin_writes = (lambda who: hymn_library.delete_hymn(world["church"], world[who], hid),
                    lambda who: hymn_library.add_hymnal(world["church"], world[who], "PH1990"),
                    lambda who: hymn_library.remove_hymnal(world["church"], world[who], "PH1990"),
                    lambda who: hymn_library.update_hymn(world["church"], world[who], hid, {"text_year": 1826}),
                    lambda who: _add(world, who=who, title="Facts", hymnal_count=5))
    set_role(world["admin"], world["church"], "member")            # after require_admin read "admin"
    for who in ("member", "admin"):
        for write in admin_writes:
            with pytest.raises(Forbidden) as denied:
                write(who)
            assert (denied.value.message, denied.value.details) == ("Only church admins can do this.", None)
    assert _add(world, who="admin", title="Still a member")["title"] == "Still a member"
    remove_membership(world["member"], world["church"])
    with pytest.raises(Forbidden) as removed:
        _add(world, title="Gone")
    assert removed.value.details == NO_ACCESS
    churches.soft_delete_church(world["church"])
    for write in (lambda: _add(world, who="owner", title="Deleted"),
                  lambda: hymn_library.update_hymn(world["church"], world["owner"], hid, {"title": "X"}),
                  lambda: hymn_library.remove_hymnal(world["church"], world["owner"], "PH1990")):
        with pytest.raises(Forbidden) as deleted:
            write()
        assert deleted.value.details == NO_ACCESS
    assert len(list_hymns(world["church"])) == 608


def test_each_write_reads_the_church_row_under_its_lock(world):
    hid = _first(world)["id"]
    for write in (lambda: _add(world, title="Locked"),
                  lambda: hymn_library.update_hymn(world["church"], world["member"], hid, {"title": "Locked 2"}),
                  lambda: hymn_library.add_hymnal(world["church"], world["owner"], "PH1990"),
                  lambda: hymn_library.remove_hymnal(world["church"], world["owner"], "PH1990"),
                  lambda: hymn_library.delete_hymn(world["church"], world["owner"], hid)):
        with _record_church_row_access() as (reads, _writes):
            write()
        assert reads and reads[0][1] is True, reads
        assert {session for session, _locked in reads} == {reads[0][0]}
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email, hymnal_sources; "
````

**with:**

````python
            "bulletin_image, usecases.bulletin_images, repos.bulletin_images, usecases.members, usecases.church_admin, email_addresses, usecases.contacts, google_oauth, usecases.email, bulletin_email, hymnal_sources, usecases.hymn_library; "
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymn_library.py 2>&1 | tail -3` then `.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected** (`usecases.hymn_library` does not exist yet: `ModuleNotFoundError` above these lines; then the import check names it):
```
ERROR backend/tests/test_hymn_library.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in <t>s
```
```
1 failed, 2 passed in <t>s
```

- [ ] **Step 3: Write the usecases**

**Create `backend/usecases/hymn_library.py`:**

````python
"""The church's hymn library in Settings → Hymns (6a spec, `usecases/hymn_library.py`;
slice 6a-2; owner's 6a-2 answers of 2026-10-07).

Any member adds and edits hymns; only owners and admins delete a hymn, set a
hymn's year or familiarity (`text_year`, `hymnal_count`), list the bundled
hymnals, add one, or remove a whole hymnal (never the only one or the
default). Every write opens one session and starts with
usecases.members.lock_and_read_actor (the church-row lock and the caller's
role re-read under it), so a removed member or a deleted church gets
`no_church_access`, an admin demoted meanwhile gets the role 403 on an admin
write, and the duplicate check and the write run under the lock: two members
adding the same hymn at once get one hymn and one 409.

Separate from usecases.hymns (the builder's reads and suggestions). No
FastAPI, Starlette or Streamlit here (usecases/__init__.py).
"""
import re
import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any, Optional

import hymnal_sources
from db import session_scope
from domain_errors import Conflict, InvalidInput, NotFound
from repos import hymns as hymn_repo
from repos.hymns import HymnRecord, title_key
from usecases import hymns
from usecases.church_admin import require_admin_role
from usecases.members import lock_and_read_actor

TITLE_REQUIRED = "Hymn title is required."
NUMBER_INVALID = "Hymn number must be a whole number."
HYMNAL_INVALID = "Choose one of your church's hymnals."
LINK_INVALID = "Links must start with https://."
LINK_SPACES = "Links can't contain spaces."
COUNT_INVALID = "Number of hymnals must be a whole number from 0 to 100000."
HYMN_NOT_FOUND = "Hymn not found."
SOURCE_UNAVAILABLE = "That hymnal isn't available to add."
HYMNAL_NOT_FOUND = "Your church doesn't have that hymnal."
ONLY_HYMNAL = "You can't remove your only hymnal."

MAX_NUMBER = 99999
MAX_COUNT = 100000
# A new church with no hymns adds to Streamlit's hymnal (repos/hymns.py add_hymn's default).
FIRST_HYMNAL = "GG2013"
HYMNAL_CODE = re.compile(r"[A-Za-z0-9_-]{2,20}")
# Control characters (C0, DEL, C1) and the two noncharacters a Word file cannot hold.
_CONTROL = re.compile("[\x00-\x1f\x7f-\x9f\ufffe\uffff]")
_FACTS = ("text_year", "hymnal_count")


def year_message(this_year: int) -> str:
    return f"Year must be a whole number from 1 to {this_year}."


def duplicate_message(hymnal: str, number: Optional[int], title: str) -> str:
    return (f"{hymnal} already has #{number} {title}." if number is not None
            else f"{hymnal} already has {title}.")


def default_message(code: str) -> str:
    return f"{code} is your default hymnal. Choose a different default in Church profile first."


def one_line(value: Optional[str]) -> str:
    """`value` on one line: each control character a space, every run of
    whitespace one space, trimmed ("" for None). A pasted line break or tab is
    tidied, not refused."""
    return " ".join(_CONTROL.sub(" ", value or "").split())


def clean_title(value: Optional[str]) -> str:
    title = one_line(value)
    if not title:
        raise InvalidInput(TITLE_REQUIRED, field="title")
    return title


def clean_number(value: Optional[int]) -> Optional[int]:
    if value is not None and not 1 <= value <= MAX_NUMBER:
        raise InvalidInput(NUMBER_INVALID, field="number")
    return value


def clean_text(value: Optional[str]) -> Optional[str]:
    """Scripture references and themes: one line, blank = None."""
    return one_line(value) or None


def clean_link(value: Optional[str]) -> Optional[str]:
    """Blank = None; otherwise https:// (any case) and something after it, with no space inside."""
    link = (value or "").strip()
    if not link:
        return None
    if any(ch.isspace() or _CONTROL.match(ch) for ch in link):
        raise InvalidInput(LINK_SPACES, field="link")
    if not link.lower().startswith("https://") or len(link) == len("https://"):
        raise InvalidInput(LINK_INVALID, field="link")
    return link


def clean_year(value: Optional[int], *, this_year: int) -> Optional[int]:
    if value is not None and not 1 <= value <= this_year:
        raise InvalidInput(year_message(this_year), field="text_year")
    return value


def clean_count(value: Optional[int]) -> Optional[int]:
    if value is not None and not 0 <= value <= MAX_COUNT:
        raise InvalidInput(COUNT_INVALID, field="hymnal_count")
    return value


def hymn_out(record: HymnRecord) -> dict:
    """HymnDetailOut's fields."""
    return {"id": record.id, "hymnal": record.hymnal, "title": (record.title or "").strip(),
            "number": record.number, "scripture_refs": record.scripture_refs, "theme": record.theme,
            "link": record.link, "text_year": record.text_year, "hymnal_count": record.hymnal_count}


def hymnal_label(code: str) -> Optional[str]:
    """The name shown beside a hymnal code (GET /hymnals' `label`), or None."""
    return hymnal_sources.label_for(code)


def _codes(church_id: uuid.UUID, s) -> list[str]:
    return [summary.code for summary in hymn_repo.hymnal_summaries(church_id, session=s)]


def _chosen_hymnal(church_id: uuid.UUID, requested: Optional[str], s) -> str:
    """POST's hymnal: null or blank = the effective default (FIRST_HYMNAL for a
    church with no hymns). It must be one of the church's hymnals, or, while
    the church has none, any code of 2-20 letters, digits, "_" or "-"."""
    codes = _codes(church_id, s)
    wanted = (requested or "").strip()
    if not wanted:
        return hymns.resolve_default_hymnal(church_id, session=s).effective_hymnal or FIRST_HYMNAL
    if wanted in codes or (not codes and HYMNAL_CODE.fullmatch(wanted)):
        return wanted
    raise InvalidInput(HYMNAL_INVALID, field="hymnal")


def _require_admin_for_facts(role: str, sent: Mapping[str, Any], *, present: bool) -> None:
    """The year and familiarity are admins' (owner, 2026-09-26): on POST a
    non-null value, on PATCH the key itself (null included)."""
    if any((name in sent) if present else (sent.get(name) is not None) for name in _FACTS):
        require_admin_role(role)


def create_hymn(church_id: uuid.UUID, actor_id: uuid.UUID, data: Mapping[str, Any]) -> dict:
    """POST /hymns: `data` has HymnIn's keys (None for each one not sent).
    Checks in the order title, number, hymnal, link, year, count; then the
    duplicate (the same hymnal, number and title words) is a 409."""
    this_year = date.today().year
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin_for_facts(role, data, present=False)
        values = {
            "title": clean_title(data.get("title")),
            "number": clean_number(data.get("number")),
            "hymnal": _chosen_hymnal(church_id, data.get("hymnal"), s),
            "scripture_refs": clean_text(data.get("scripture_refs")),
            "theme": clean_text(data.get("theme")),
            "link": clean_link(data.get("link")),
            "text_year": clean_year(data.get("text_year"), this_year=this_year),
            "hymnal_count": clean_count(data.get("hymnal_count")),
        }
        if hymn_repo.find_duplicate(church_id, values["hymnal"], values["number"], values["title"], session=s):
            raise Conflict(duplicate_message(values["hymnal"], values["number"], values["title"]))
        return hymn_out(hymn_repo.create_hymn(church_id, values, session=s))


def update_hymn(church_id: uuid.UUID, actor_id: uuid.UUID, hymn_id: uuid.UUID,
                changes: Mapping[str, Any]) -> dict:
    """PATCH /hymns/{id}: only the keys sent. A null title or hymnal is
    refused; a null number, refs, theme, link, year or count clears it. An
    unknown id, or another church's, is a 404 before any field is checked.
    The duplicate check runs only when the hymnal, number or title words
    change and the title is not blank, and leaves the hymn itself out."""
    this_year = date.today().year
    with session_scope() as s:
        role = lock_and_read_actor(s, church_id, actor_id)
        _require_admin_for_facts(role, changes, present=True)
        current = hymn_repo.get_hymn(hymn_id, church_id, session=s)
        if current is None:
            raise NotFound(HYMN_NOT_FOUND)
        clean: dict[str, Any] = {}
        if "title" in changes:
            clean["title"] = clean_title(changes["title"])
        if "number" in changes:
            clean["number"] = clean_number(changes["number"])
        if "hymnal" in changes:
            wanted = (changes["hymnal"] or "").strip()
            if wanted not in _codes(church_id, s):
                raise InvalidInput(HYMNAL_INVALID, field="hymnal")
            clean["hymnal"] = wanted
        for name in ("scripture_refs", "theme"):
            if name in changes:
                clean[name] = clean_text(changes[name])
        if "link" in changes:
            clean["link"] = clean_link(changes["link"])
        if "text_year" in changes:
            clean["text_year"] = clean_year(changes["text_year"], this_year=this_year)
        if "hymnal_count" in changes:
            clean["hymnal_count"] = clean_count(changes["hymnal_count"])
        hymnal = clean.get("hymnal", current.hymnal)
        number = clean.get("number", current.number)
        title = clean.get("title", current.title or "")
        # An old hymn with a blank title (the old app allowed one) is never a duplicate:
        # "GG2013 already has #5 ." would name nothing (plan review M8).
        if (title_key(title)
                and (hymnal, number, title_key(title)) != (current.hymnal, current.number, title_key(current.title))
                and hymn_repo.find_duplicate(church_id, hymnal, number, title, exclude_id=hymn_id, session=s)):
            raise Conflict(duplicate_message(hymnal, number, title))
        return hymn_out(hymn_repo.patch_hymn(hymn_id, church_id, clean, session=s))


def delete_hymn(church_id: uuid.UUID, actor_id: uuid.UUID, hymn_id: uuid.UUID) -> None:
    """DELETE /hymns/{id} (owners and admins; owner, 2026-10-05). Saved
    services keep the hymn as it was saved; a draft that picked it asks for a
    replacement."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        if not hymn_repo.delete_hymn(hymn_id, church_id, session=s):
            raise NotFound(HYMN_NOT_FOUND)


def list_sources(church_id: uuid.UUID) -> list[dict]:
    """GET /hymnal-sources: every hymnal an admin can add, with whether the
    church has it already (`present`)."""
    with session_scope() as s:
        codes = set(_codes(church_id, s))
        bundled = hymnal_sources.list_bundled(session=s)
    return [{"code": b.code, "label": b.label, "hymn_count": b.hymn_count,
             "has_scripture_refs": b.has_scripture_refs, "present": b.code in codes} for b in bundled]


def add_hymnal(church_id: uuid.UUID, actor_id: uuid.UUID, code: str) -> dict:
    """POST /hymnals: import a bundled hymnal (repos.hymns.import_hymns: a hymn
    the church has is kept, only its blanks filled). Adding it again is
    allowed and usually inserts nothing."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        wanted = code.strip()
        try:
            rows = hymnal_sources.rows_for(wanted, session=s)
        except KeyError:
            raise InvalidInput(SOURCE_UNAVAILABLE, field="code") from None
        report = hymn_repo.import_hymns(church_id, wanted, rows, session=s)
    return {"code": wanted, "label": hymnal_sources.label_for(wanted),
            "inserted": report["inserted"], "updated": report["updated"]}


def remove_hymnal(church_id: uuid.UUID, actor_id: uuid.UUID, code: str) -> int:
    """DELETE /hymnals/{code}: delete every hymn of the church in `code` and
    return how many. A code the church lacks is a 404; its only hymnal, or the
    effective default, a 409. Saved services, recent use and drafts are not
    touched."""
    with session_scope() as s:
        require_admin_role(lock_and_read_actor(s, church_id, actor_id))
        codes = _codes(church_id, s)
        if code not in codes:
            raise NotFound(HYMNAL_NOT_FOUND)
        if len(codes) == 1:
            raise Conflict(ONLY_HYMNAL)
        if hymns.resolve_default_hymnal(church_id, session=s).effective_hymnal == code:
            raise Conflict(default_message(code))
        return hymn_repo.delete_hymnal(church_id, code, session=s)
````

- [ ] **Step 4: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymn_library.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
31 passed in <t>s
```
```
1865 passed, 27 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/hymn_library.py backend/tests/test_hymn_library.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Slice 6a-2: the hymn library usecases under the church-row lock" -m "usecases/hymn_library: create_hymn, update_hymn and delete_hymn,
list_sources, add_hymnal and remove_hymnal. Every write takes the
church-row lock and re-reads the caller's role (lock_and_read_actor):
members add and edit; deleting a hymn, setting its year or familiarity,
and adding or removing a hymnal are for owners and admins. The title,
references and themes are tidied onto one line; the number, link, year
and familiarity are checked with the 6a spec's messages; the same
hymnal, number and title words is a 409. A hymnal is never removed when
it is the church's only one or its default." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1865 passed, 27 skipped`; frontend `835 passed` in 100 files.

### Task 4: `POST`, `PATCH`, `DELETE /hymns` and the hymnal routes (S API, Models; clarification 15)

**Files:**
- Create: `backend/tests/test_api_hymns_admin.py`, `backend/tests/test_api_hymnals_admin.py`
- Modify: `backend/tests/test_api_hymnals.py`, `backend/api/routes/hymns.py`, `backend/api/routes/hymnals.py` (rewritten), `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (both regenerated)

- [ ] **Step 1: Write the failing tests**

Over HTTP, with `tests.api_helpers`: a member adds and edits a hymn and `GET /hymns` lists it (the port of `streamlit_tests`' `test_member_can_add_hymn`); a member's delete and facts are 403 with the role body, an owner's go through, a second delete is 404; each bad field is a 422 naming it, an omitted or null title included and a non-whole number being Pydantic's "Not a valid value." (9 cases); the 409 on add and on edit; an unknown body field, a malformed id and an unknown id; and `assert_church_isolated` on the three writes. For hymnals: an admin sees PH1990 not present, adds it (605, then 0), sees it present and removes it; a member gets 403 on all three routes; the errors of adding and removing; and `assert_church_isolated` on all three, church B's hymns of the same code untouched. `test_api_hymnals.py`'s first test expects each hymnal's `label` (null for an unknown code).

**Create `backend/tests/test_api_hymns_admin.py`:**

````python
"""POST, PATCH and DELETE /hymns over HTTP (6a spec, API rows and Models;
slice 6a-2): who may do what (members add and edit, admins delete and set the
year and familiarity), the exact errors with their fields, the 409, and church
isolation. Ports streamlit_tests' test_member_can_add_hymn."""
from datetime import date

import pytest

from db import session_scope
from db.models import Hymn
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
MEMBER = "member@example.com"
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}
THIS_YEAR = date.today().year


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=MEMBER), cid, "member")
    with session_scope() as s:
        s.add(Hymn(church_id=cid, hymnal="GG2013", title="Holy, Holy, Holy", number=138))
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _add(client, church, body, email=MEMBER):
    return client.post("/hymns", headers=church_headers(email, church), json=body)


def _titles(client, church, q="") -> list[str]:
    r = client.get(f"/hymns?q={q}", headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    return [h["title"] for h in r.json()["items"]]


def test_a_member_adds_and_edits_a_hymn_and_it_is_listed(client, church):
    r = _add(client, church, {"title": " Be Thou My Vision ", "number": 339, "scripture_refs": "Psalm 16:5",
                              "theme": "Guidance, Vision", "link": "https://hymnary.org/hymn/GG2013/339"})
    assert r.status_code == 201, r.text
    added = r.json()
    assert set(added) == {"id", "hymnal", "title", "number", "scripture_refs", "theme", "link", "text_year",
                          "hymnal_count"}
    assert (added["hymnal"], added["title"], added["theme"], added["text_year"]) == (
        "GG2013", "Be Thou My Vision", "Guidance, Vision", None)
    assert _titles(client, church, "339") == ["Be Thou My Vision"]

    r = client.patch(f"/hymns/{added['id']}", headers=church_headers(MEMBER, church),
                     json={"title": "Be Thou My Vision!", "theme": None})
    assert r.status_code == 200, r.text
    assert (r.json()["title"], r.json()["theme"], r.json()["number"]) == ("Be Thou My Vision!", None, 339)
    assert _titles(client, church) == ["Holy, Holy, Holy", "Be Thou My Vision!"]


def test_only_admins_delete_a_hymn_or_send_its_year_or_familiarity(client, church):
    hid = _add(client, church, {"title": "Doomed", "number": 1}).json()["id"]
    for method, path, body in (("DELETE", f"/hymns/{hid}", None),
                               ("POST", "/hymns", {"title": "Facts", "text_year": 1826}),
                               ("POST", "/hymns", {"title": "Facts", "hymnal_count": 0}),
                               ("PATCH", f"/hymns/{hid}", {"text_year": None}),
                               ("PATCH", f"/hymns/{hid}", {"hymnal_count": 12})):
        r = client.request(method, path, headers=church_headers(MEMBER, church), json=body)
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY), f"{method} {path} {body}"
    r = client.patch(f"/hymns/{hid}", headers=church_headers(OWNER, church),
                     json={"text_year": 1826, "hymnal_count": 1322})
    assert (r.status_code, r.json()["text_year"], r.json()["hymnal_count"]) == (200, 1826, 1322)
    r = client.delete(f"/hymns/{hid}", headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()) == (200, {"deleted": True})
    r = client.delete(f"/hymns/{hid}", headers=church_headers(OWNER, church))
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Hymn not found."})
    assert _titles(client, church) == ["Holy, Holy, Holy"]


@pytest.mark.parametrize("body, field, message", [
    ({}, "title", "Hymn title is required."),
    ({"title": None}, "title", "Hymn title is required."),
    ({"title": "X", "number": 0}, "number", "Hymn number must be a whole number."),
    ({"title": "X", "number": 1.5}, "number", "Not a valid value."),
    ({"title": "X", "hymnal": "PH1990"}, "hymnal", "Choose one of your church's hymnals."),
    ({"title": "X", "link": "http://example.org"}, "link", "Links must start with https://."),
    ({"title": "X", "text_year": THIS_YEAR + 1}, "text_year", f"Year must be a whole number from 1 to {THIS_YEAR}."),
    ({"title": "X", "hymnal_count": 100001}, "hymnal_count",
     "Number of hymnals must be a whole number from 0 to 100000."),
    ({"title": "x" * 301}, "title", "Too long (max 300 characters)."),
])
def test_a_bad_field_is_a_422_naming_it(client, church, body, field, message):
    r = _add(client, church, body, email=OWNER)
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["code"], r.json()["error"]["fields"]) == ("invalid_request", {field: message})
    assert _titles(client, church) == ["Holy, Holy, Holy"]


def test_the_same_hymn_twice_is_a_409(client, church):
    r = _add(client, church, {"title": "holy, holy, HOLY", "number": 138})
    assert (r.status_code, _error(r)) == (409, {"code": "conflict",
                                               "message": "GG2013 already has #138 holy, holy, HOLY."})
    hid = _add(client, church, {"title": "Untitled"}).json()["id"]
    r = client.patch(f"/hymns/{hid}", headers=church_headers(MEMBER, church),
                     json={"title": "Holy, Holy, Holy", "number": 138})
    assert (r.status_code, _error(r)["message"]) == (409, "GG2013 already has #138 Holy, Holy, Holy.")


def test_unknown_fields_and_malformed_or_unknown_ids(client, church):
    r = _add(client, church, {"title": "X", "church_id": str(church)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.patch("/hymns/not-a-uuid", headers=church_headers(MEMBER, church), json={"title": "X"})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.patch("/hymns/00000000-0000-4000-8000-000000000000", headers=church_headers(MEMBER, church),
                     json={"title": "X"})
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Hymn not found."})


def test_hymn_writes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    theirs = _add(client, world.church_b, {"title": "Theirs"}, email=world.b).json()
    assert_church_isolated(client, "POST", "/hymns", world=world, json={"title": "Ours"})
    ours = _add(client, world.church_a, {"title": "Second"}, email=world.a).json()
    assert_church_isolated(client, "PATCH", f"/hymns/{ours['id']}", world=world, json={"title": "Ours 2"},
                           resource_path_b=f"/hymns/{theirs['id']}")
    assert_church_isolated(client, "DELETE", f"/hymns/{ours['id']}", world=world,
                           resource_path_b=f"/hymns/{theirs['id']}")
    r = client.get("/hymns", headers=church_headers(world.b, world.church_b))
    assert [h["title"] for h in r.json()["items"]] == ["Theirs"]
````

**Create `backend/tests/test_api_hymnals_admin.py`:**

````python
"""GET /hymnal-sources, POST /hymnals and DELETE /hymnals/{code} over HTTP (6a
spec, API rows; slice 6a-2): owners and admins only, the bundled PH1990 added
once, a hymnal removed but never the only or the default one, the exact errors,
and church isolation."""
import pytest

from db import session_scope
from db.models import Hymn
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
MEMBER = "member@example.com"
ADMINS_ONLY = {"code": "forbidden", "message": "Only church admins can do this."}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


def _seed(church_id, hymnal="GG2013", count=2):
    with session_scope() as s:
        for n in range(1, count + 1):
            s.add(Hymn(church_id=church_id, hymnal=hymnal, title=f"{hymnal} {n}", number=n))


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    add_membership(make_user(email=MEMBER), cid, "member")
    _seed(cid)
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _sources(client, church) -> dict:
    r = client.get("/hymnal-sources", headers=church_headers(OWNER, church))
    assert r.status_code == 200, r.text
    return {s["code"]: s for s in r.json()["items"]}


def _codes(client, church) -> list[tuple[str, int]]:
    r = client.get("/hymnals", headers=church_headers(MEMBER, church))
    return [(h["code"], h["hymn_count"]) for h in r.json()["items"]]


def test_an_admin_adds_ph1990_once_and_removes_it(client, church):
    assert _sources(client, church)["PH1990"] == {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)",
                                                  "hymn_count": 605, "has_scripture_refs": False, "present": False}
    r = client.post("/hymnals", headers=church_headers(OWNER, church), json={"code": "PH1990"})
    assert (r.status_code, r.json()) == (200, {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)",
                                               "inserted": 605, "updated": 0})
    r = client.post("/hymnals", headers=church_headers(OWNER, church), json={"code": "PH1990"})
    assert (r.status_code, r.json()["inserted"]) == (200, 0)
    assert _sources(client, church)["PH1990"]["present"] is True
    assert _codes(client, church) == [("GG2013", 2), ("PH1990", 605)]
    r = client.delete("/hymnals/PH1990", headers=church_headers(OWNER, church))
    assert (r.status_code, r.json()) == (200, {"deleted": True, "hymns_deleted": 605})
    assert _codes(client, church) == [("GG2013", 2)]


def test_a_member_may_not_list_add_or_remove_hymnals(client, church):
    _seed(church, "PH1990", 1)
    for method, path, body in (("GET", "/hymnal-sources", None), ("POST", "/hymnals", {"code": "PH1990"}),
                               ("DELETE", "/hymnals/PH1990", None)):
        r = client.request(method, path, headers=church_headers(MEMBER, church), json=body)
        assert (r.status_code, _error(r)) == (403, ADMINS_ONLY), f"{method} {path}"
    assert _codes(client, church) == [("GG2013", 2), ("PH1990", 1)]


def test_the_errors_of_adding_and_removing(client, church):
    owner = church_headers(OWNER, church)
    r = client.post("/hymnals", headers=owner, json={"code": "XX2000"})
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"code": "That hymnal isn't available to add."})
    r = client.post("/hymnals", headers=owner, json={"code": "X" * 21})
    assert (r.status_code, r.json()["error"]["fields"]) == (422, {"code": "Too long (max 20 characters)."})
    r = client.post("/hymnals", headers=owner, json={"code": "PH1990", "church_id": str(church)})
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.delete("/hymnals/G", headers=owner)
    assert (r.status_code, r.json()["error"]["code"]) == (422, "invalid_request")
    r = client.delete("/hymnals/XX2000", headers=owner)
    assert (r.status_code, _error(r)) == (404, {"code": "not_found", "message": "Your church doesn't have that hymnal."})
    r = client.delete("/hymnals/GG2013", headers=owner)
    assert (r.status_code, _error(r)) == (409, {"code": "conflict", "message": "You can't remove your only hymnal."})
    _seed(church, "PH1990", 1)
    r = client.delete("/hymnals/GG2013", headers=owner)
    assert (r.status_code, _error(r)["message"]) == (
        409, "GG2013 is your default hymnal. Choose a different default in Church profile first.")
    assert _codes(client, church) == [("GG2013", 2), ("PH1990", 1)]


def test_hymnal_routes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    _seed(world.church_a)
    _seed(world.church_a, "PH1990", 1)
    _seed(world.church_b)
    _seed(world.church_b, "PH1990", 3)
    assert_church_isolated(client, "GET", "/hymnal-sources", world=world)
    assert_church_isolated(client, "POST", "/hymnals", world=world, json={"code": "PH1990"})
    assert_church_isolated(client, "DELETE", "/hymnals/PH1990", world=world)
    r = client.get("/hymnals", headers=church_headers(world.b, world.church_b))
    assert [(h["code"], h["hymn_count"]) for h in r.json()["items"]] == [("GG2013", 2), ("PH1990", 3)]
    r = client.get("/hymnals", headers=church_headers(world.a, world.church_a))
    assert [h["code"] for h in r.json()["items"]] == ["GG2013"]
````

**In `backend/tests/test_api_hymnals.py`, replace:**

````python
    assert _get(client, cid) == {
        "items": [{"code": "GG2013", "hymn_count": 4, "scripture_ref_count": 2},
                  {"code": "PH1990", "hymn_count": 3, "scripture_ref_count": 0}],
````

**with:**

````python
    _hymns(cid, "XX2000", 1)
    assert _get(client, cid) == {      # each with its label (slice 6a-2), null for a code with no known name
        "items": [{"code": "GG2013", "label": "Glory to God (2013)", "hymn_count": 4, "scripture_ref_count": 2},
                  {"code": "PH1990", "label": "The Presbyterian Hymnal (1990)", "hymn_count": 3,
                   "scripture_ref_count": 0},
                  {"code": "XX2000", "label": None, "hymn_count": 1, "scripture_ref_count": 0}],
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_hymns_admin.py backend/tests/test_api_hymnals_admin.py backend/tests/test_api_hymnals.py 2>&1 | tail -1`
**Expected** (no route answers `POST /hymns` or the hymnal routes yet, and `GET /hymnals` has no `label`):
```
19 failed, 6 passed in <t>s
```

- [ ] **Step 3: Write the routes**

**In `backend/api/routes/hymns.py`, replace:**

````python
"""The Hymns step's church-scoped routes (slice 3 spec, API; Backend 4).
Plain `def` routes that each make one usecase call with church.id only
(F §1.2 rule 1, §2.2.1). Any member may call them."""
````

**with:**

````python
"""The Hymns step's church-scoped routes (slice 3 spec, API; Backend 4) and
Settings → Hymns' writes (6a spec, POST, PATCH and DELETE /hymns; slice
6a-2). Plain `def` routes that each make one usecase call with church.id only
(F §1.2 rule 1, §2.2.1). Any member may call them, except DELETE (owners and
admins); a hymn's year and familiarity are admins' too (usecases.hymn_library
checks the role re-read under the church-row lock). No Idempotency-Key: the
duplicate check runs under the lock, so a double tap gets a 409."""
````

**In `backend/api/routes/hymns.py`, replace:**

````python
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import IsoDate, Page
from usecases import hymns
````

**with:**

````python
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import DeletedOut, IsoDate, Page
from usecases import hymn_library, hymns
````

**In `backend/api/routes/hymns.py`, replace:**

````python

def hymn_out(view: hymns.HymnView) -> HymnOut:
````

**with:**

````python

class HymnIn(BaseModel):
    """POST /hymns. An omitted or null title is the usecase's "Hymn title is
    required."; a null hymnal is the church's default hymnal; the ranges of
    number, text_year and hymnal_count are the usecase's (friendly messages)."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=300)
    number: Optional[int] = None
    hymnal: Optional[str] = Field(None, max_length=20)
    scripture_refs: Optional[str] = Field(None, max_length=2000)
    theme: Optional[str] = Field(None, max_length=2000)
    link: Optional[str] = Field(None, max_length=500)
    text_year: Optional[int] = None          # admins only when not null
    hymnal_count: Optional[int] = None       # admins only when not null


class HymnPatchIn(BaseModel):
    """PATCH /hymns/{id}: omitted = unchanged (model_fields_set). A null title
    or hymnal is refused; a null number, scripture_refs, theme, link,
    text_year or hymnal_count clears it. Sending text_year or hymnal_count at
    all (null included) is for admins."""

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=300)
    number: Optional[int] = None
    hymnal: Optional[str] = Field(None, max_length=20)
    scripture_refs: Optional[str] = Field(None, max_length=2000)
    theme: Optional[str] = Field(None, max_length=2000)
    link: Optional[str] = Field(None, max_length=500)
    text_year: Optional[int] = None
    hymnal_count: Optional[int] = None


class HymnDetailOut(BaseModel):
    """A hymn as Settings → Hymns writes it: the stored theme text, not GET /hymns' parsed themes."""

    id: uuid.UUID
    hymnal: str
    title: str
    number: Optional[int]
    scripture_refs: Optional[str]
    theme: Optional[str]
    link: Optional[str]
    text_year: Optional[int]
    hymnal_count: Optional[int]


def hymn_out(view: hymns.HymnView) -> HymnOut:
````

**In `backend/api/routes/hymns.py`, replace:**

````python
                                for slot, views in result.slots.items()}))
````

**with:**

````python
                                for slot, views in result.slots.items()}))


@router.post("/hymns", status_code=201, response_model=HymnDetailOut,
             responses=error_responses(401, 403, 409, 422, 503))
def create_hymn(payload: HymnIn, church: ActiveChurch = Depends(require_church),
                user: CurrentUser = Depends(get_current_user)) -> HymnDetailOut:
    return HymnDetailOut(**hymn_library.create_hymn(church.id, user.id, payload.model_dump()))


@router.patch("/hymns/{hymn_id}", response_model=HymnDetailOut,
              responses=error_responses(401, 403, 404, 409, 422, 503))
def update_hymn(hymn_id: uuid.UUID, payload: HymnPatchIn, church: ActiveChurch = Depends(require_church),
                user: CurrentUser = Depends(get_current_user)) -> HymnDetailOut:
    return HymnDetailOut(**hymn_library.update_hymn(church.id, user.id, hymn_id,
                                                    payload.model_dump(include=payload.model_fields_set)))


@router.delete("/hymns/{hymn_id}", response_model=DeletedOut, responses=error_responses(401, 403, 404, 422, 503))
def delete_hymn(hymn_id: uuid.UUID, church: ActiveChurch = Depends(require_admin),
                user: CurrentUser = Depends(get_current_user)) -> DeletedOut:
    """Owners and admins only (owner, 2026-10-05)."""
    hymn_library.delete_hymn(church.id, user.id, hymn_id)
    return DeletedOut()
````

**Replace `backend/api/routes/hymnals.py`:**

````python
"""GET /hymnals: the active church's hymnals and its default (slice 3 spec,
API row 1 and Models; Backend 3.1-3.2), and the bundled hymnals an admin adds
or a hymnal an admin removes in Settings → Hymns (6a spec, GET
/hymnal-sources, POST /hymnals, DELETE /hymnals/{code}; slice 6a-2). Thin
routes (F §2.2.1): GET /hymnals for any member, the rest for owners and
admins (usecases.hymn_library re-reads the role under the church-row lock)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field

from api.deps import ActiveChurch, CurrentUser, get_current_user, require_admin, require_church
from api.errors import error_responses
from usecases import hymn_library, hymns

router = APIRouter()


class HymnalOut(BaseModel):
    code: str                          # e.g. "GG2013"
    label: Optional[str] = None        # e.g. "Glory to God (2013)"; null for a code without a known name
    hymn_count: int
    scripture_ref_count: int           # hymns with non-blank scripture_refs


class HymnalListOut(BaseModel):
    items: list[HymnalOut]             # by code, in codepoint order
    default_hymnal: Optional[str]      # churches.settings["default_hymnal"] verbatim, or null
    effective_hymnal: Optional[str]    # default_hymnal if it is in items; else items[0].code; else null


class HymnalSourceOut(BaseModel):
    code: str
    label: Optional[str]
    hymn_count: int
    has_scripture_refs: bool           # false: "Hymns for the readings" and AI suggestions work less well
    present: bool                      # the church has at least one hymn in this hymnal


class HymnalSourceList(BaseModel):
    items: list[HymnalSourceOut]       # by code


class HymnalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=20)


class HymnalAddedOut(BaseModel):
    code: str
    label: Optional[str]
    inserted: int                      # hymns added; 0 when the church already had them all
    updated: int                       # hymns the church had whose blank details were filled in


class HymnalRemovedOut(BaseModel):
    deleted: Literal[True] = True
    hymns_deleted: int


@router.get("/hymnals", response_model=HymnalListOut, responses=error_responses(401, 403, 422, 503))
def list_hymnals(church: ActiveChurch = Depends(require_church)) -> HymnalListOut:
    overview = hymns.hymnal_overview(church.id)
    return HymnalListOut(
        items=[HymnalOut(code=i.code, label=hymn_library.hymnal_label(i.code), hymn_count=i.hymn_count,
                         scripture_ref_count=i.scripture_ref_count)
               for i in overview.items],
        default_hymnal=overview.default_hymnal,
        effective_hymnal=overview.effective_hymnal,
    )


@router.get("/hymnal-sources", response_model=HymnalSourceList, responses=error_responses(401, 403, 422, 503))
def list_hymnal_sources(church: ActiveChurch = Depends(require_admin)) -> HymnalSourceList:
    return HymnalSourceList(items=[HymnalSourceOut(**s) for s in hymn_library.list_sources(church.id)])


@router.post("/hymnals", response_model=HymnalAddedOut, responses=error_responses(401, 403, 422, 503))
def add_hymnal(payload: HymnalIn, church: ActiveChurch = Depends(require_admin),
               user: CurrentUser = Depends(get_current_user)) -> HymnalAddedOut:
    """Idempotent: adding a hymnal the church has again inserts nothing new (no Idempotency-Key)."""
    return HymnalAddedOut(**hymn_library.add_hymnal(church.id, user.id, payload.code))


@router.delete("/hymnals/{code}", response_model=HymnalRemovedOut,
               responses=error_responses(401, 403, 404, 409, 422, 503))
def remove_hymnal(code: str = Path(pattern=r"^[A-Za-z0-9_-]{2,20}$"),
                  church: ActiveChurch = Depends(require_admin),
                  user: CurrentUser = Depends(get_current_user)) -> HymnalRemovedOut:
    return HymnalRemovedOut(hymns_deleted=hymn_library.remove_hymnal(church.id, user.id, code))
````

- [ ] **Step 4: Regenerate the API files, see the tests pass, and the suites**

Run: `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git diff --stat -- frontend/src/lib/api | tail -1` then `.venv/bin/python -m pytest -q backend/tests/test_api_hymns_admin.py backend/tests/test_api_hymnals_admin.py backend/tests/test_api_hymnals.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py 2>&1 | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")` then `.venv/bin/python -m pytest -q | tail -1`
**Expected** (the snapshot and the types gain the new paths and models; the contract test now matches the live schema):
```
 2 files changed, 1933 insertions(+), 221 deletions(-)
```
```
33 passed in <t>s
```
```
typecheck 0
lint 0
```
```
1883 passed, 27 skipped in <t>s
```

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/hymns.py backend/api/routes/hymnals.py backend/tests/test_api_hymns_admin.py backend/tests/test_api_hymnals_admin.py backend/tests/test_api_hymnals.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Slice 6a-2: the hymn and hymnal write routes" -m "POST and PATCH /hymns (any member; the year and familiarity are an
admin's) and DELETE /hymns/{id} (owners and admins) answer
HymnDetailOut; GET /hymnal-sources, POST /hymnals and DELETE
/hymnals/{code} are for owners and admins; GET /hymnals gains each
hymnal's label. Thin routes over usecases.hymn_library; the OpenAPI
snapshot and the generated types are regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 27 skipped`; frontend `835 passed` in 100 files.

### Task 5: The lock on real Postgres (S Testing → Postgres; clarification 14)

**Files:**
- Create: `backend/tests/test_hymn_library_postgres.py`

- [ ] **Step 1: Write the tests**

As `test_contacts_postgres.py` (5b-1): the owner signs in through `GET /me`, the church comes from `repos.churches.create_church` on `pg_db`'s engine (an empty catalog, so no hymns). A held-lock test (the first add waits inside `find_duplicate`, which the usecase calls after taking the lock; the second must still be waiting a second later, then gets the 409); S's barrier test (two identical adds, the second in capitals, 20 rounds: one 201, one 409, one row); two adds of PH1990 at once (605 hymns, not 1210; `[0, 605]` inserted); and S's timing guard (a 605-row add under 10 s).

**Create `backend/tests/test_hymn_library_postgres.py`:**

````python
"""POST /hymns and POST /hymnals on real Postgres (slice 6a-2; 6a spec,
Testing → Postgres): two members adding the same hymn at the same moment get
one hymn and one 409, and two admins adding PH1990 at once get 605 hymns, not
1210, because the duplicate check and the inserts run under the church-row
lock (usecases.hymn_library, through lock_and_read_actor). Adding PH1990 is
also timed: under 10 s (a guard, not a benchmark).

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them. As in
test_contacts_postgres.py: the owner signs in through GET /me and the church
is made through repos.churches.create_church on pg_db's engine (the test
catalog is empty, so the church starts with no hymns).
"""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

from db import session_scope
from db.models import Hymn
from repos import hymns as hymn_repo
from repos.churches import create_church
from tests.api_helpers import auth_headers, church_headers
from usecases import hymn_library

pytestmark = pytest.mark.postgres

OWNER = "owner@example.com"


@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


def _church(client, name="Grace") -> uuid.UUID:
    r = client.get("/me", headers=auth_headers(OWNER))
    assert r.status_code == 200, r.text
    return create_church(name=name, timezone="America/New_York", owner_user_id=uuid.UUID(r.json()["user"]["id"]))


@pytest.fixture
def church(pg_client) -> uuid.UUID:
    return _church(pg_client)


def _post_hymn(client, church, title, number):
    return client.post("/hymns", headers=church_headers(OWNER, church), json={"title": title, "number": number})


def _add_hymnal(client, church):
    return client.post("/hymnals", headers=church_headers(OWNER, church), json={"code": "PH1990"})


def _count(church, **where) -> int:
    with session_scope() as s:
        return s.execute(select(func.count()).select_from(Hymn).where(
            Hymn.church_id == church, *[getattr(Hymn, k) == v for k, v in where.items()])).scalar_one()


def test_a_second_add_of_one_hymn_waits_for_the_first_and_gets_a_409(pg_client, church, monkeypatch):
    inside, release = threading.Event(), threading.Event()
    real = hymn_repo.find_duplicate
    calls = []

    def held(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            inside.set()                   # the first add holds the church-row lock here
            assert release.wait(10), "the test never released the first add"
        return real(*args, **kwargs)

    monkeypatch.setattr(hymn_repo, "find_duplicate", held)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(_post_hymn, pg_client, church, "Be Thou My Vision", 339)
        assert inside.wait(10), "the first add never took the lock"
        second = pool.submit(_post_hymn, pg_client, church, "be thou my vision", 339)
        threading.Event().wait(1)          # time for the second add to finish if nothing held it
        assert not second.done(), "the second add did not wait for the church-row lock"
        release.set()
        responses = [first.result(10), second.result(10)]
    assert [r.status_code for r in responses] == [201, 409]
    assert responses[1].json()["error"]["message"] == "GG2013 already has #339 be thou my vision."
    assert _count(church, number=339) == 1


def test_two_adds_of_one_hymn_at_once_make_one_hymn_twenty_times(pg_client, church, monkeypatch):
    barrier = threading.Barrier(2)
    real = hymn_library.lock_and_read_actor

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(hymn_library, "lock_and_read_actor", together)
    for round_ in range(20):
        title = f"Hymn {round_}"
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(lambda t: _post_hymn(pg_client, church, t, round_ + 1), [title, title.upper()]))
        assert sorted(r.status_code for r in responses) == [201, 409], f"round {round_}"
        assert _count(church, number=round_ + 1) == 1, f"round {round_}"


def test_two_adds_of_ph1990_at_once_make_605_hymns(pg_client, church, monkeypatch):
    barrier = threading.Barrier(2)
    real = hymn_library.lock_and_read_actor

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        return real(*args, **kwargs)

    monkeypatch.setattr(hymn_library, "lock_and_read_actor", together)
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: _add_hymnal(pg_client, church), range(2)))
    assert [r.status_code for r in responses] == [200, 200]
    assert sorted(r.json()["inserted"] for r in responses) == [0, 605]
    assert _count(church, hymnal="PH1990") == 605


def test_adding_ph1990_takes_under_ten_seconds(pg_client, church):
    started = time.monotonic()
    r = _add_hymnal(pg_client, church)
    elapsed = time.monotonic() - started
    assert (r.status_code, r.json()["inserted"]) == (200, 605)
    assert elapsed < 10, f"POST /hymnals took {elapsed:.1f} s"
````

- [ ] **Step 2: Run them**

They are skipped here (no `TEST_DATABASE_URL`); CI's `backend-postgres` runs them (`31 passed`). To run them before the PR, point `TEST_DATABASE_URL` at a local throwaway Postgres (Build notes).

Run: `.venv/bin/python -m pytest -q backend/tests/test_hymn_library_postgres.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:**
```
4 skipped in <t>s
```
```
1883 passed, 31 skipped in <t>s
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_hymn_library_postgres.py
git commit -q -m "Slice 6a-2: Postgres tests for the hymn library's lock" -m "On real Postgres (CI's backend-postgres): a second add of the same hymn
waits for the first's church-row lock and gets the 409; two identical
adds at once make one hymn, 20 rounds; two adds of PH1990 at once make
605 hymns; and adding PH1990 takes under 10 s." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `835 passed` in 100 files.

## The app (T6-T9)

### Task 6: The hymn forms' rules, the types and the queries (S "Pure helpers" `hymns.ts`, "Queries and mutations"; clarifications 9, 10, 19)

**Files:**
- Create: `frontend/src/lib/settings/hymns.test.ts`, `frontend/src/lib/settings/hymns.ts`, `frontend/src/lib/queries/hymn-library.ts`
- Modify: `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/timeouts.ts`, `frontend/src/test/fixtures/index.ts`

- [ ] **Step 1: Write the failing tests**

S's unit cases: `parseHymnNumber`, `parseTextYear`, `parseHymnalCount`; the forms' starting values (Themes joined by ", "); `hymnFormErrors` with the server's words (a member's facts unchecked); `newHymnBody` (trimmed, blanks null, the facts only for an admin); `hymnPatch` (only what changed, numbers as numbers, a cleared field null, never a member's facts); the labels and count lines; and `hymnFieldErrors` mapping a 422's `theme` to the Themes box, with the 60 s timeout of `POST /hymnals` (the dialog's "up to a minute"; plan review I3).

**Create `frontend/src/lib/settings/hymns.test.ts`:**

````ts
/** Settings → Hymns' form rules (slice 6a-2; 6a spec "Pure helpers" `hymns.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { timeoutFor } from "@/lib/api/timeouts";
import { hymnFieldErrors } from "@/lib/queries/hymn-library";
import { hymn } from "@/test/fixtures";

import {
  countLine,
  emptyHymnForm,
  hymnFormErrors,
  hymnFormFrom,
  hymnLabel,
  hymnPatch,
  newHymnBody,
  parseHymnalCount,
  parseHymnNumber,
  parseTextYear,
} from "./hymns";

const THIS_YEAR = 2026;
const ADMIN = { thisYear: THIS_YEAR, admin: true };
const MEMBER = { thisYear: THIS_YEAR, admin: false };

describe("Settings → Hymns' form rules (slice 6a-2)", () => {
  it("reads whole numbers in their ranges: blank is unknown, anything else is invalid", () => {
    expect([parseHymnNumber(""), parseHymnNumber(" 12 "), parseHymnNumber("99999")]).toEqual([null, 12, 99999]);
    for (const bad of ["12a", "0", "100000", "1.5", "-3", "1e3"]) expect(parseHymnNumber(bad)).toBe("invalid");
    expect([parseTextYear("", THIS_YEAR), parseTextYear("1826", THIS_YEAR), parseTextYear("2026", THIS_YEAR)]).toEqual([null, 1826, 2026]);
    for (const bad of ["0", "2027", "18a"]) expect(parseTextYear(bad, THIS_YEAR)).toBe("invalid");
    expect([parseHymnalCount(""), parseHymnalCount("0"), parseHymnalCount("1322")]).toEqual([null, 0, 1322]);
    for (const bad of ["-1", "100001"]) expect(parseHymnalCount(bad)).toBe("invalid");
  });

  it("starts the edit form from the hymn, and the add form empty in the default hymnal", () => {
    const h = hymn({ themes: ["Trinity", "Praise"], scripture_refs: "Isaiah 6:3", text_year: 1826, hymnal_count: null });
    expect(hymnFormFrom(h)).toEqual({
      title: "Come, Thou Almighty King",
      number: "403",
      hymnal: "GG2013",
      scripture_refs: "Isaiah 6:3",
      themes: "Trinity, Praise",
      link: "https://hymnary.org/hymn/GG2013/403",
      text_year: "1826",
      hymnal_count: "",
    });
    expect(hymnFormFrom(hymn({ number: null, link: null })).number).toBe("");
    expect(emptyHymnForm("PH1990")).toEqual({
      title: "", number: "", hymnal: "PH1990", scripture_refs: "", themes: "", link: "", text_year: "", hymnal_count: "",
    });
  });

  it("names each field the client can tell is wrong, with the server's words; a member's facts are not checked", () => {
    const bad = { ...emptyHymnForm("GG2013"), title: "  ", number: "0", link: "http://example.org", text_year: "2027", hymnal_count: "-1" };
    expect(hymnFormErrors(bad, ADMIN)).toEqual({
      title: "Hymn title is required.",
      number: "Hymn number must be a whole number.",
      link: "Links must start with https://.",
      text_year: "Year must be a whole number from 1 to 2026.",
      hymnal_count: "Number of hymnals must be a whole number from 0 to 100000.",
    });
    expect(Object.keys(hymnFormErrors(bad, MEMBER))).toEqual(["title", "number", "link"]);
    expect(hymnFormErrors({ ...emptyHymnForm("GG2013"), title: "X", link: " HTTPS://hymnary.org/x " }, ADMIN)).toEqual({});
  });

  it("builds the add body trimmed, blanks as null, and the facts only for an admin", () => {
    const form = { ...emptyHymnForm("GG2013"), title: " Be Thou My Vision ", number: " 339 ", themes: " Guidance ", text_year: "1905" };
    expect(newHymnBody(form, ADMIN)).toEqual({
      title: "Be Thou My Vision", number: 339, hymnal: "GG2013", scripture_refs: null, theme: "Guidance", link: null,
      text_year: 1905, hymnal_count: null,
    });
    expect(newHymnBody(form, MEMBER)).not.toHaveProperty("text_year");
    expect(newHymnBody(form, MEMBER)).not.toHaveProperty("hymnal_count");
  });

  it("sends only what changed in an edit, a cleared field as null, and never a member's facts", () => {
    const baseline = hymnFormFrom(hymn({ themes: ["Trinity"], text_year: 1826, hymnal_count: 12 }));
    expect(hymnPatch(baseline, { ...baseline, title: " Come, Thou Almighty King ", number: "0403" }, ADMIN)).toEqual({});
    expect(hymnPatch(baseline, { ...baseline, themes: "", link: " ", number: "" }, ADMIN)).toEqual({ theme: null, link: null, number: null });
    expect(hymnPatch(baseline, { ...baseline, text_year: "1830", hymnal_count: "" }, ADMIN)).toEqual({ text_year: 1830, hymnal_count: null });
    expect(hymnPatch(baseline, { ...baseline, text_year: "1830", hymnal_count: "", hymnal: "PH1990" }, MEMBER)).toEqual({ hymnal: "PH1990" });
  });

  it("labels a hymn and counts the list", () => {
    expect(hymnLabel({ number: 403, title: "Come, Thou Almighty King" })).toBe("#403 Come, Thou Almighty King");
    expect(hymnLabel({ number: null, title: "Untitled Tune" })).toBe("Untitled Tune");
    expect([countLine(853, false), countLine(1, false), countLine(12, true), countLine(1, true)]).toEqual([
      "853 hymns", "1 hymn", "12 matching hymns", "1 matching hymn",
    ]);
  });

  it("maps a 422's fields to the form's (theme is Themes) and gives adding a hymnal a minute", () => {
    const e = new ApiError(422, "invalid_request", "Links must start with https://.", {
      fields: { link: "Links must start with https://.", theme: "Too long (max 2000 characters).", church_id: "x" },
    });
    expect(hymnFieldErrors(e)).toEqual({ link: "Links must start with https://.", themes: "Too long (max 2000 characters)." });
    expect(hymnFieldErrors(new ApiError(409, "conflict", "GG2013 already has #403 X."))).toBeNull();
    expect(timeoutFor("POST", "/hymnals")).toBe(60_000);
    expect(timeoutFor("DELETE", "/hymnals/PH1990")).toBe(20_000);
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/settings/hymns.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`./hymns` does not exist yet):
```
 FAIL  |unit| src/lib/settings/hymns.test.ts [ src/lib/settings/hymns.test.ts ]
      Tests  no tests
```

- [ ] **Step 3: Write the types, the fixtures, the rules and the queries**

**In `frontend/src/lib/api/types.ts`, replace:**

````ts
/**
 * `/gmail-connection` (slice 5b-2): the caller's own Gmail connection
````

**with:**

````ts
/**
 * Settings → Hymns (slice 6a-2): the body of `POST /hymns` and of `PATCH
 * /hymns/{id}` (only the fields that change) and the hymn they answer (with the
 * stored `theme` text); `GET /hymnal-sources` (admins: the hymnals they can add,
 * `present` when the church has one); `POST /hymnals`'s body and answer; and
 * `DELETE /hymnals/{code}`'s answer.
 */
export type HymnBody = components["schemas"]["HymnIn"];
export type HymnPatch = components["schemas"]["HymnPatchIn"];
export type HymnDetail = components["schemas"]["HymnDetailOut"];
export type HymnalSource = components["schemas"]["HymnalSourceOut"];
export type HymnalSources = components["schemas"]["HymnalSourceList"];
export type HymnalAdded = components["schemas"]["HymnalAddedOut"];
export type HymnalRemoved = components["schemas"]["HymnalRemovedOut"];

/**
 * `/gmail-connection` (slice 5b-2): the caller's own Gmail connection
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /bulletin-emails": 90_000,
````

**with:**

````ts
  "POST /bulletin-emails": 90_000,
  // Slice 6a-2 (6a spec, API; F §1.8): adding a bundled hymnal inserts up to about a thousand hymns, and the
  // dialog says "This can take up to a minute." (plan review I3). Nothing on the server stops it sooner: uvicorn
  // sets no request deadline, the app sets no statement_timeout outside migrations, and routes behind Railway
  // already answer later than that (POST /liturgy/generate, an 80 s deadline). A timed-out add may still
  // finish on the server, so a failed hymnal write refreshes the lists (lib/queries/hymn-library.ts).
  "POST /hymnals": 60_000,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  Hymn,
````

**with:**

````ts
  Hymn,
  HymnalSource,
  HymnalSources,
  HymnDetail,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  return gmailConnection({ connected: false, google_email: null });
}
````

**with:**

````ts
  return gmailConnection({ connected: false, google_email: null });
}

// --- slice 6a-2: Settings → Hymns ------------------------------------------------------------------

/** One hymn as `POST`/`PATCH /hymns` answer it (`HymnDetailOut`): `hymn(overrides)` with its stored theme text. */
export function hymnDetail(overrides: Partial<HymnDetail> = {}): HymnDetail {
  const h = hymn();
  return {
    id: h.id,
    hymnal: h.hymnal,
    title: h.title,
    number: h.number,
    scripture_refs: h.scripture_refs,
    theme: null,
    link: h.link,
    text_year: null,
    hymnal_count: null,
    ...overrides,
  };
}

/** One bundled hymnal (`HymnalSourceOut`): PH1990, not yet added, unless overridden. */
export function hymnalSource(overrides: Partial<HymnalSource> = {}): HymnalSource {
  return {
    code: "PH1990",
    label: "The Presbyterian Hymnal (1990)",
    hymn_count: 605,
    has_scripture_refs: false,
    present: false,
    ...overrides,
  };
}

/** `GET /hymnal-sources` for Grace: GG2013 (which Grace has) and PH1990 (which it has not). */
export function hymnalSources(items: HymnalSource[] = [
  hymnalSource({ code: "GG2013", label: "Glory to God (2013)", hymn_count: 853, has_scripture_refs: true, present: true }),
  hymnalSource(),
]): HymnalSources {
  return { items };
}
````

**Create `frontend/src/lib/settings/hymns.ts`:**

````ts
/**
 * Settings → Hymns' forms (slice 6a-2; 6a spec UX §2, "Pure helpers" `hymns.ts`).
 * The client checks what it can with the server's own words, so a mistake
 * shows at once; the server checks everything again (and tidies line breaks
 * into spaces). A member's form never sends the year or the familiarity.
 */
import type { Hymn, HymnBody, HymnPatch } from "@/lib/api/types";

export type HymnForm = {
  title: string;
  number: string;
  hymnal: string;
  scripture_refs: string;
  themes: string;
  link: string;
  text_year: string;
  hymnal_count: string;
};

export type HymnFieldErrors = Partial<Record<keyof HymnForm, string>>;

export const TITLE_REQUIRED = "Hymn title is required.";
export const NUMBER_INVALID = "Hymn number must be a whole number.";
export const LINK_INVALID = "Links must start with https://.";
export const COUNT_INVALID = "Number of hymnals must be a whole number from 0 to 100000.";

export function yearInvalid(thisYear: number): string {
  return `Year must be a whole number from 1 to ${thisYear}.`;
}

/** `text` as a whole number from `min` to `max`: blank is null, anything else out of reach "invalid". */
function parseWhole(text: string, min: number, max: number): number | null | "invalid" {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  if (!/^\d{1,9}$/.test(trimmed)) return "invalid";
  const value = Number(trimmed);
  return value >= min && value <= max ? value : "invalid";
}

export function parseHymnNumber(text: string): number | null | "invalid" {
  return parseWhole(text, 1, 99999);
}

export function parseTextYear(text: string, thisYear: number): number | null | "invalid" {
  return parseWhole(text, 1, thisYear);
}

export function parseHymnalCount(text: string): number | null | "invalid" {
  return parseWhole(text, 0, 100000);
}

/** The add form, in `hymnal` (the church's default). */
export function emptyHymnForm(hymnal: string): HymnForm {
  return { title: "", number: "", hymnal, scripture_refs: "", themes: "", link: "", text_year: "", hymnal_count: "" };
}

/** The edit form a hymn starts at, and its baseline; Themes start at the parsed themes joined by ", ". */
export function hymnFormFrom(h: Hymn): HymnForm {
  const text = (n: number | null | undefined) => (n === null || n === undefined ? "" : String(n));
  return {
    title: h.title,
    number: text(h.number),
    hymnal: h.hymnal,
    scripture_refs: h.scripture_refs ?? "",
    themes: h.themes.join(", "),
    link: h.link ?? "",
    text_year: text(h.text_year),
    hymnal_count: text(h.hymnal_count),
  };
}

/** What the client can tell is wrong, in the form's order, with the server's messages. */
export function hymnFormErrors(form: HymnForm, { thisYear, admin }: { thisYear: number; admin: boolean }): HymnFieldErrors {
  const errors: HymnFieldErrors = {};
  if (form.title.trim() === "") errors.title = TITLE_REQUIRED;
  if (parseHymnNumber(form.number) === "invalid") errors.number = NUMBER_INVALID;
  const link = form.link.trim();
  if (link !== "" && !link.toLowerCase().startsWith("https://")) errors.link = LINK_INVALID;
  if (admin && parseTextYear(form.text_year, thisYear) === "invalid") errors.text_year = yearInvalid(thisYear);
  if (admin && parseHymnalCount(form.hymnal_count) === "invalid") errors.hymnal_count = COUNT_INVALID;
  return errors;
}

const blankToNull = (text: string): string | null => (text.trim() === "" ? null : text.trim());
const whole = (value: number | null | "invalid"): number | null => (value === "invalid" ? null : value);

/** `POST /hymns`'s body (check `hymnFormErrors` first). The year and familiarity only for an admin. */
export function newHymnBody(form: HymnForm, { thisYear, admin }: { thisYear: number; admin: boolean }): HymnBody {
  const body: HymnBody = {
    title: form.title.trim(),
    number: whole(parseHymnNumber(form.number)),
    hymnal: blankToNull(form.hymnal),
    scripture_refs: blankToNull(form.scripture_refs),
    theme: blankToNull(form.themes),
    link: blankToNull(form.link),
  };
  if (admin) {
    body.text_year = whole(parseTextYear(form.text_year, thisYear));
    body.hymnal_count = whole(parseHymnalCount(form.hymnal_count));
  }
  return body;
}

/**
 * `PATCH /hymns/{id}`'s body: each field whose value changed (text trimmed,
 * numbers compared as numbers); a cleared field is null. The year and
 * familiarity only for an admin, so a member's edit never sends them.
 */
export function hymnPatch(baseline: HymnForm, form: HymnForm, { thisYear, admin }: { thisYear: number; admin: boolean }): HymnPatch {
  const patch: HymnPatch = {};
  if (form.title.trim() !== baseline.title.trim()) patch.title = form.title.trim();
  const number = whole(parseHymnNumber(form.number));
  if (number !== whole(parseHymnNumber(baseline.number))) patch.number = number;
  if (form.hymnal !== baseline.hymnal) patch.hymnal = form.hymnal;
  if (form.scripture_refs.trim() !== baseline.scripture_refs.trim()) patch.scripture_refs = blankToNull(form.scripture_refs);
  if (form.themes.trim() !== baseline.themes.trim()) patch.theme = blankToNull(form.themes);
  if (form.link.trim() !== baseline.link.trim()) patch.link = blankToNull(form.link);
  if (admin) {
    const year = whole(parseTextYear(form.text_year, thisYear));
    if (year !== whole(parseTextYear(baseline.text_year, thisYear))) patch.text_year = year;
    const count = whole(parseHymnalCount(form.hymnal_count));
    if (count !== whole(parseHymnalCount(baseline.hymnal_count))) patch.hymnal_count = count;
  }
  return patch;
}

/** A hymn as the library lists it: "#403 Come, Thou Almighty King", or the title alone with no number. */
export function hymnLabel(h: Pick<Hymn, "number" | "title">): string {
  return h.number === null || h.number === undefined ? h.title : `#${h.number} ${h.title}`;
}

/** The library's count line: "853 hymns", "1 hymn", or "12 matching hymns" while searching or filtered. */
export function countLine(total: number, filtered: boolean): string {
  const noun = total === 1 ? "hymn" : "hymns";
  return filtered ? `${total} matching ${noun}` : `${total} ${noun}`;
}

/** "{n} hymns" / "1 hymn". */
export function hymnCount(n: number): string {
  return `${n} ${n === 1 ? "hymn" : "hymns"}`;
}
````

**Create `frontend/src/lib/queries/hymn-library.ts`:**

````ts
/**
 * Settings → Hymns' queries (slice 6a-2; 6a spec "Queries and mutations").
 *
 * - `useHymnLibrary({ hymnal, q })`: `GET /hymns` 50 at a time ("Show more"),
 *   keyed under ["church", id, "hymns"], so it shares the prefix with the
 *   builder's hymn lists and matches.
 * - `useHymnalSources(enabled)`: `GET /hymnal-sources` (admins).
 * - The writes: add, edit and delete a hymn; add and remove a hymnal. Each
 *   success refreshes every hymn list (the builder's picker among them, with
 *   no reload), the hymnals, the bundled list and the church profile (whose
 *   effective hymnal can change). Not optimistic (F §4.4).
 *
 * Errors: a 401 or a lost church the app already reports. A hymn form's own
 * errors (a 409, or a 422 naming one of its fields: `hymnFieldErrors`) are the
 * form's to show. A role 403 (an admin demoted meanwhile) is toasted and
 * refetches the church profile, so the page turns into the member's view. A
 * hymn deleted elsewhere (404) is toasted as "This hymn was already deleted."
 * and refetches the lists. Anything else is toasted. A hymnal write's failure
 * also refreshes every list, whatever it was: a timed-out add may still have
 * finished on the server (plan review I3).
 */
import { useInfiniteQuery, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type {
  DeletedOut,
  HymnalAdded,
  HymnalRemoved,
  HymnalSources,
  HymnBody,
  HymnDetail,
  HymnPage,
  HymnPatch,
} from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import type { HymnFieldErrors, HymnForm } from "@/lib/settings/hymns";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** Hymns per page in the library (6a spec UX §2b). */
export const LIBRARY_PAGE = 50;
export const HYMN_GONE = "This hymn was already deleted.";

/** The form field each server field name belongs to (`theme` is the Themes box). */
const FORM_FIELD: Record<string, keyof HymnForm> = {
  title: "title",
  number: "number",
  hymnal: "hymnal",
  scripture_refs: "scripture_refs",
  theme: "themes",
  link: "link",
  text_year: "text_year",
  hymnal_count: "hymnal_count",
};

/** A failed add or edit's messages for the hymn form's fields (a 422's `fields`), or null. */
export function hymnFieldErrors(e: unknown): HymnFieldErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const found: HymnFieldErrors = {};
  for (const [name, message] of Object.entries(e.fields)) {
    const field = FORM_FIELD[name];
    if (field) found[field] = message;
  }
  return Object.keys(found).length > 0 ? found : null;
}

/** True for the 409 "{hymnal} already has #{number} {title}." */
export function isDuplicateHymn(e: unknown): boolean {
  return e instanceof ApiError && e.status === 409;
}

/** Every query a hymn or hymnal change can make stale: the hymn lists (the builder's too), hymnals, sources, profile. */
export function refreshHymns(queryClient: QueryClient, churchId: string): void {
  for (const queryKey of [
    [...keys.church(churchId), "hymns"],
    keys.hymnals(churchId),
    keys.hymnalSources(churchId),
    keys.churchProfile(churchId),
  ]) {
    void queryClient.invalidateQueries({ queryKey });
  }
}

export type LibraryFilter = { hymnal: string | null; q: string };

/** `GET /hymns?hymnal=&q=&limit=50&offset=`: the library, in the server's order, a page at a time. */
export function useHymnLibrary({ hymnal, q }: LibraryFilter) {
  const api = useApi();
  const church = useChurch();
  return useInfiniteQuery<HymnPage, ApiError>({
    queryKey: keys.hymns(church.id, { view: "library", hymnal, q }),
    queryFn: ({ pageParam, signal }) => {
      const search = new URLSearchParams({ limit: String(LIBRARY_PAGE), offset: String(pageParam as number) });
      if (hymnal !== null) search.set("hymnal", hymnal);
      if (q !== "") search.set("q", q);
      return api.church<HymnPage>(`/hymns?${search}`, { signal });
    },
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length;
      return last.items.length > 0 && next < last.total ? next : undefined;
    },
  });
}

/** `GET /hymnal-sources` (admins only: a member's page never asks). */
export function useHymnalSources(enabled: boolean) {
  const api = useApi();
  const church = useChurch();
  return useQuery<HymnalSources, ApiError>({
    queryKey: keys.hymnalSources(church.id),
    queryFn: ({ signal }) => api.church<HymnalSources>("/hymnal-sources", { signal }),
    enabled,
  });
}

/** The refresh and the error policy every write shares; `formErrors` true for the hymn form's writes. */
function useHymnWrite<TData, TVariables>(mutationFn: (variables: TVariables) => Promise<TData>, formErrors: boolean) {
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<TData, ApiError, TVariables>({
    mutationFn,
    onSuccess: () => refreshHymns(queryClient, church.id),
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      if (formErrors && (isDuplicateHymn(e) || hymnFieldErrors(e) !== null)) return;
      if (e.status === 404 && formErrors) {
        toast.error(HYMN_GONE);
        refreshHymns(queryClient, church.id);
        return;
      }
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
      // A hymnal write refreshes after any failure: a timed-out add may still have finished on the server.
      if (!formErrors || e.status === 404 || e.status === 409) refreshHymns(queryClient, church.id);
    },
  });
}

/** `POST /hymns` (any member; the year and familiarity are an admin's). */
export function useCreateHymn() {
  const api = useApi();
  return useHymnWrite<HymnDetail, HymnBody>((body) => api.church<HymnDetail>("/hymns", { method: "POST", json: body }), true);
}

/** `PATCH /hymns/{id}`: only the fields that change. */
export function useUpdateHymn() {
  const api = useApi();
  return useHymnWrite<HymnDetail, { id: string; patch: HymnPatch }>(
    ({ id, patch }) => api.church<HymnDetail>(`/hymns/${encodeURIComponent(id)}`, { method: "PATCH", json: patch }),
    true,
  );
}

/** `DELETE /hymns/{id}` (admins). */
export function useDeleteHymn() {
  const api = useApi();
  return useHymnWrite<DeletedOut, string>(
    (id) => api.church<DeletedOut>(`/hymns/${encodeURIComponent(id)}`, { method: "DELETE" }),
    true,
  );
}

/** `POST /hymnals` (admins; 60 s, `timeouts.ts`). */
export function useAddHymnal() {
  const api = useApi();
  return useHymnWrite<HymnalAdded, string>(
    (code) => api.church<HymnalAdded>("/hymnals", { method: "POST", json: { code } }),
    false,
  );
}

/** `DELETE /hymnals/{code}` (admins). */
export function useRemoveHymnal() {
  const api = useApi();
  return useHymnWrite<HymnalRemoved, string>(
    (code) => api.church<HymnalRemoved>(`/hymnals/${encodeURIComponent(code)}`, { method: "DELETE" }),
    false,
  );
}
````

- [ ] **Step 4: See them pass, and the suite**

Run: `(cd frontend && npx vitest run src/lib/settings/hymns.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
```
      Tests  7 passed (7)
```
```
 Test Files  101 passed (101)
      Tests  842 passed (842)
```
```
typecheck 0
lint 0
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/settings/hymns.ts frontend/src/lib/settings/hymns.test.ts frontend/src/lib/queries/hymn-library.ts frontend/src/lib/api/types.ts frontend/src/lib/api/timeouts.ts frontend/src/test/fixtures/index.ts
git commit -q -m "Slice 6a-2: the hymn forms' rules and the hymn library queries" -m "lib/settings/hymns: the number, year and familiarity parsers, the forms'
starting values, the client checks with the server's words, the add
body and the edit patch (only what changed; a member's never has the
year or familiarity). lib/queries/hymn-library: the library 50 at a
time, the bundled hymnals, and the five writes, each refreshing every
hymn list (the builder's picker shares the key), the hymnals, the
sources and the church profile. POST /hymnals waits 60 s, and a failed
hymnal write refreshes the lists too." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `842 passed` in 101 files.

### Task 7: The Hymns page and its Hymnals card (S UX §2a; clarifications 3-6)

**Files:**
- Create: `frontend/src/components/settings/hymns-settings-page.test.tsx`, `frontend/src/components/settings/hymnals-card.tsx`, `frontend/src/components/settings/hymns-settings-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/hymns/page.tsx`

- [ ] **Step 1: Write the failing tests**

Rendered through the route inside the Settings layout, as the Contacts page's tests are, with `hymnalsServer` (a fake whose `GET` answers with what the adds and removals left, the 5b-1 lesson). A member reads the rows, the footer and the note and never asks for the sources; an admin gets Remove on every row but the default, whose hint links to Church profile; an admin adds PH1990 (the note, Added for GG2013, the toast, the row turning to Added, and the four keys invalidated); the add dialog cannot be closed while the add runs and says it is still working after 8 s (fake timers for `setTimeout` only); the empty sources line; the removal's confirmation (its full body), the toast, the row gone and focus on **Add a hymnal**; a refused removal toasted. After the plan review: an add that brings nothing new says "PH1990 is already added." and a failed add refreshes every list (I3); a removal answered 404 (removed in another tab) also moves focus to **Add a hymnal** (M1); a one-hymn hymnal's confirmation is singular, with the not-bundled ending (M2); a hymnal whose code the route cannot take has no **Remove…** (M4). `GET /hymns` has an empty answer here, for T8's library.

**Create `frontend/src/components/settings/hymns-settings-page.test.tsx`:**

````tsx
/**
 * Settings → Hymns, the Hymnals card (slice 6a-2; 6a spec UX §2a): every
 * member reads the hymnals, admins add a bundled one and remove any but the
 * default. Rendered inside the Settings layout, as the route is, with a Toaster.
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import HymnsSettingsRoute from "@/app/(signed-in)/(church)/settings/hymns/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Hymnals } from "@/lib/api/types";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, hymnals, hymnalSource, hymnalSources, me } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { MEMBER_HYMNALS_NOTE, NO_REFS_NOTE, STILL_WORKING } from "./hymnals-card";

afterEach(() => {
  toast.dismiss();
  vi.useRealTimers();
});

const GG = { code: "GG2013", label: "Glory to God (2013)", hymn_count: 853, scripture_ref_count: 795 };
const PH = { code: "PH1990", label: "The Presbyterian Hymnal (1990)", hymn_count: 605, scripture_ref_count: 0 };

/** A fake `/hymnals`: `GET` answers with what the adds and removals left, as the server would after a refetch. */
function hymnalsServer(items: Hymnals["items"] = [GG]) {
  let current = [...items];
  return {
    list: () => hymnals({ items: current }),
    sources: () => hymnalSources([
      hymnalSource({ code: "GG2013", label: "Glory to God (2013)", hymn_count: 853, has_scripture_refs: true, present: current.some((h) => h.code === "GG2013") }),
      hymnalSource({ present: current.some((h) => h.code === "PH1990") }),
    ]),
    add: () => {
      current = [...current, PH];
      return { code: "PH1990", label: PH.label, inserted: 605, updated: 0 };
    },
    remove: (code: string) => {
      current = current.filter((h) => h.code !== code);
      return { deleted: true, hymns_deleted: 605 };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const api = installFakeApi({
    "GET /hymnals": hymnals(),
    "GET /hymnal-sources": hymnalSources(),
    "GET /hymns": { items: [], total: 0, limit: 50, offset: 0 },
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <HymnsSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/hymns" },
  );
  return { ...view, api };
}

function hymnalRows() {
  return within(screen.getByRole("list", { name: "Hymnals" })).getAllByRole("listitem");
}

function requests(api: { requests: RecordedRequest[] }, method: string, prefix: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith(prefix));
}

describe("Settings → Hymns, the Hymnals card (slice 6a-2)", () => {
  it("shows a member the hymnals with their counts and the default, and no actions", async () => {
    const { api } = renderPage("member", { "GET /hymnals": hymnals({ items: [GG, PH], effective_hymnal: "GG2013" }) });
    await screen.findByText("Glory to God (2013) · 853 hymns");
    expect(hymnalRows().map((row) => row.textContent)).toEqual([
      "GG2013DefaultGlory to God (2013) · 853 hymns",
      "PH1990The Presbyterian Hymnal (1990) · 605 hymns",
    ]);
    expect(screen.getByText("1458 hymns in 2 hymnals.")).toBeInTheDocument();
    expect(screen.getByText(MEMBER_HYMNALS_NOTE)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^(Add a hymnal|Remove )/ })).toBeNull();
    expect(requests(api, "GET", "/hymnal-sources")).toHaveLength(0);
  });

  it("gives an admin Remove on every hymnal but the default, which says where to change it", async () => {
    renderPage("admin", { "GET /hymnals": hymnals({ items: [GG, PH], default_hymnal: "PH1990", effective_hymnal: "PH1990" }) });
    await screen.findByText("Glory to God (2013) · 853 hymns");
    const [gg, ph] = hymnalRows();
    expect(within(gg).getByRole("button", { name: "Remove GG2013" })).toHaveTextContent("Remove…");
    expect(within(ph).queryByRole("button")).toBeNull();
    expect(ph).toHaveTextContent("Default. Change it in Church profile.");
    expect(within(ph).getByRole("link", { name: "Church profile" })).toHaveAttribute("href", "/settings/church");
    expect(screen.queryByText(MEMBER_HYMNALS_NOTE)).toBeNull();
  });

  it("lets an admin add PH1990: the note, Added for a hymnal the church has, the toast, and every list refreshed", async () => {
    const server = hymnalsServer();
    const { api, user, queryClient } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "POST /hymnals": server.add,
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    const [gg, ph] = within(dialog).getAllByRole("listitem");
    expect(gg).toHaveTextContent("GG2013 · Glory to God (2013) · 853 hymns");
    expect(within(gg).getByRole("button", { name: "Added" })).toBeDisabled();
    expect(ph).toHaveTextContent(`PH1990 · The Presbyterian Hymnal (1990) · 605 hymns${NO_REFS_NOTE}`);
    await user.click(within(ph).getByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("Added PH1990 (605 hymns).")).toBeInTheDocument();
    expect(requests(api, "POST", "/hymnals")[0].body).toEqual({ code: "PH1990" });
    expect(within(ph).getByRole("button", { name: "Added" })).toBeDisabled();
    expect(screen.getByRole("dialog", { name: "Add a hymnal" })).toBeInTheDocument();
    for (const key of [["church", church().id, "hymns"], ["church", church().id, "hymnals"], ["church", church().id, "hymnal-sources"], ["church", church().id, "profile"]]) {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
    }
    await user.click(within(dialog).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(hymnalRows()).toHaveLength(2));
  });

  it("keeps the add dialog open while an add runs, and says it is still working after 8 s", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, toFake: ["setTimeout", "clearTimeout"] });
    let finish: (value: unknown) => void = () => {};
    const { user } = renderPage("admin", {
      "POST /hymnals": () => new Promise((resolve) => {
        finish = resolve;
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    await user.click(await within(dialog).findByRole("button", { name: "Add PH1990" }));
    expect(within(dialog).getByRole("button", { name: "Add PH1990" })).toHaveTextContent("Adding…");
    expect(within(dialog).getByRole("button", { name: "Done" })).toBeDisabled();
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(await screen.findByText(STILL_WORKING)).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Add a hymnal" })).toBeInTheDocument();
    finish({ code: "PH1990", label: PH.label, inserted: 605, updated: 0 });
    expect(await screen.findByText("Added PH1990 (605 hymns).")).toBeInTheDocument();
    expect(screen.queryByText(STILL_WORKING)).toBeNull();
  });

  it("says when no bundled hymnal is available", async () => {
    const { user } = renderPage("admin", { "GET /hymnal-sources": hymnalSources([]) });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    expect(await screen.findByText("No bundled hymnals are available on this server.")).toBeInTheDocument();
  });

  it("says a hymnal is already added when the add brings nothing new", async () => {
    const { user } = renderPage("admin", { "POST /hymnals": { code: "PH1990", label: PH.label, inserted: 0, updated: 0 } });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    await user.click(await within(dialog).findByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("PH1990 is already added.")).toBeInTheDocument();
    expect(screen.queryByText(/^Added PH1990/)).toBeNull();
    expect(within(dialog).getAllByRole("button", { name: "Added" })).toHaveLength(2);
  });

  it("toasts a failed add and refreshes every list, since the add may have finished on the server", async () => {
    const server = hymnalsServer();
    const { user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      // the server added PH1990, but its answer never arrived as a success
      "POST /hymnals": () => {
        server.add();
        return fakeError(500, "internal_error", "Internal server error.");
      },
    });
    await user.click(await screen.findByRole("button", { name: "Add a hymnal" }));
    const dialog = await screen.findByRole("dialog", { name: "Add a hymnal" });
    await user.click(await within(dialog).findByRole("button", { name: "Add PH1990" }));
    expect(await screen.findByText("Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getAllByRole("button", { name: "Added" })).toHaveLength(2));
    await user.click(within(dialog).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(hymnalRows()).toHaveLength(2));
  });

  it("asks before removing a hymnal, then removes it; focus goes to Add a hymnal", async () => {
    const server = hymnalsServer([GG, PH]);
    const { api, user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "DELETE /hymnals/PH1990": () => server.remove("PH1990"),
    });
    await screen.findByText("The Presbyterian Hymnal (1990) · 605 hymns");
    await waitFor(() => expect(requests(api, "GET", "/hymnal-sources")).toHaveLength(1));
    await user.click(screen.getByRole("button", { name: "Remove PH1990" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove PH1990?" });
    expect(confirm).toHaveTextContent(
      "This deletes all 605 hymns in PH1990 from your church's hymnal, including hymns your church added to it. " +
        "Saved services keep their hymns. Services in progress will ask you to choose replacements. " +
        "You can add PH1990 again later, but edits you made to its hymns will be lost.",
    );
    await user.click(within(confirm).getByRole("button", { name: "Remove PH1990" }));
    expect(await screen.findByText("Removed PH1990.")).toBeInTheDocument();
    await waitFor(() => expect(hymnalRows()).toHaveLength(1));
    expect(requests(api, "DELETE", "/hymnals/")).toHaveLength(1);
    await waitFor(() => expect(screen.getByRole("button", { name: "Add a hymnal" })).toHaveFocus());
  });

  it("toasts a refused removal and closes the confirmation", async () => {
    const { user } = renderPage("admin", {
      "GET /hymnals": hymnals({ items: [GG, PH] }),
      "DELETE /hymnals/PH1990": fakeError(409, "conflict", "PH1990 is your default hymnal. Choose a different default in Church profile first."),
    });
    await user.click(await screen.findByRole("button", { name: "Remove PH1990" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove PH1990?" });
    await user.click(within(confirm).getByRole("button", { name: "Remove PH1990" }));
    expect(await screen.findByText("PH1990 is your default hymnal. Choose a different default in Church profile first.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
  });

  it("moves focus to Add a hymnal when the hymnal was already removed elsewhere (404)", async () => {
    const server = hymnalsServer([GG, PH]);
    const { user } = renderPage("admin", {
      "GET /hymnals": server.list,
      "GET /hymnal-sources": server.sources,
      "DELETE /hymnals/PH1990": fakeError(404, "not_found", "Your church doesn't have that hymnal."),
    });
    await user.click(await screen.findByRole("button", { name: "Remove PH1990" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove PH1990?" });
    server.remove("PH1990"); // another tab removed it meanwhile
    await user.click(within(confirm).getByRole("button", { name: "Remove PH1990" }));
    expect(await screen.findByText("Your church doesn't have that hymnal.")).toBeInTheDocument();
    await waitFor(() => expect(hymnalRows()).toHaveLength(1));
    await waitFor(() => expect(screen.getByRole("button", { name: "Add a hymnal" })).toHaveFocus());
  });

  it("words the removal of a one-hymn hymnal in the singular, and says one outside the bundled list can't come back", async () => {
    const XX = { code: "XX2000", label: null, hymn_count: 1, scripture_ref_count: 0 };
    const { api, user } = renderPage("admin", { "GET /hymnals": hymnals({ items: [GG, XX] }) });
    await screen.findByText("1 hymn");
    await waitFor(() => expect(requests(api, "GET", "/hymnal-sources")).toHaveLength(1));
    await user.click(screen.getByRole("button", { name: "Remove XX2000" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Remove XX2000?" });
    expect(confirm).toHaveTextContent(
      "This deletes the 1 hymn in XX2000 from your church's hymnal, including hymns your church added to it. " +
        "Saved services keep their hymns. Services in progress will ask you to choose replacements. " +
        "It can't be added back from the bundled list.",
    );
  });

  it("offers no Remove for a hymnal whose code the removal route cannot take", async () => {
    const odd = [
      { code: "PH 1990", label: null, hymn_count: 3, scripture_ref_count: 0 },
      { code: "X", label: null, hymn_count: 2, scripture_ref_count: 0 },
    ];
    renderPage("admin", { "GET /hymnals": hymnals({ items: [GG, ...odd, PH] }) });
    await screen.findByText("The Presbyterian Hymnal (1990) · 605 hymns");
    expect(hymnalRows().map((row) => within(row).queryByRole("button")?.getAttribute("aria-label") ?? null)).toEqual([
      null, null, null, "Remove PH1990",
    ]);
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/hymns-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (the route does not exist yet):
```
 FAIL  |dom| src/components/settings/hymns-settings-page.test.tsx [ src/components/settings/hymns-settings-page.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the card, the page and the route**

**Create `frontend/src/components/settings/hymnals-card.tsx`:**

````tsx
"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Badge } from "@/components/ui/badge";
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
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError } from "@/lib/api/client";
import type { HymnalSource, Hymnals, HymnalSummary } from "@/lib/api/types";
import { useAddHymnal, useHymnalSources, useRemoveHymnal } from "@/lib/queries/hymn-library";
import { hymnCount } from "@/lib/settings/hymns";

export const MEMBER_HYMNALS_NOTE = "Admins can add bundled hymnals.";
export const NO_REFS_NOTE =
  "This hymnal has no scripture references, so “Hymns for the readings” and AI suggestions work less well with it.";
export const STILL_WORKING = "Still working. This can take up to a minute.";
export const NO_SOURCES = "No bundled hymnals are available on this server.";
/** How long an add runs before the dialog says it is still working (6a spec UX §2a). */
export const STILL_WORKING_AFTER_MS = 8_000;
/** The codes `DELETE /hymnals/{code}` takes; another (only the ops CLI or the old app made one) has no Remove (plan review M4). */
export const REMOVABLE_CODE = /^[A-Za-z0-9_-]{2,20}$/;

const SHEET =
  "max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-w-lg";

function hymnalsLine(items: HymnalSummary[]): string {
  const total = items.reduce((sum, h) => sum + h.hymn_count, 0);
  return `${hymnCount(total)} in ${items.length} ${items.length === 1 ? "hymnal" : "hymnals"}.`;
}

function removeBody(hymnal: HymnalSummary, bundled: boolean | null): string {
  const what = hymnal.hymn_count === 1 ? "the 1 hymn" : `all ${hymnCount(hymnal.hymn_count)}`;
  const first =
    `This deletes ${what} in ${hymnal.code} from your church's hymnal, including hymns your church added to it. ` +
    "Saved services keep their hymns. Services in progress will ask you to choose replacements.";
  if (bundled === null) return first;
  return bundled
    ? `${first} You can add ${hymnal.code} again later, but edits you made to its hymns will be lost.`
    : `${first} It can't be added back from the bundled list.`;
}

/**
 * Settings → Hymns' "Hymnals" card (slice 6a-2; 6a spec UX §2a): one row per
 * hymnal with its name, its count and a Default badge on the effective
 * default. Owners and admins add a bundled hymnal (`AddHymnalDialog`) and
 * remove any hymnal but the default one (confirmed); the default row says
 * where to change the default. A member reads the list.
 */
export function HymnalsCard({ admin, hymnals }: { admin: boolean; hymnals: UseQueryResult<Hymnals, ApiError> }) {
  const sources = useHymnalSources(admin);
  const remove = useRemoveHymnal();
  const addButton = useRef<HTMLButtonElement>(null);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<HymnalSummary | null>(null);
  // The confirmation keeps its words while it closes (removing is null by then).
  const [removeWords, setRemoveWords] = useState({ title: "", body: "", confirm: "" });
  // Focus goes to Add a hymnal after a removal (the row and its button are gone); otherwise back to Remove.
  const removed = useRef(false);

  const data = hymnals.data;
  let body;
  if (data) {
    body =
      data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">Your church has no hymnals yet.</p>
      ) : (
        <>
          <ul className="divide-y rounded-lg border" aria-label="Hymnals">
            {data.items.map((h) => {
              const isDefault = h.code === data.effective_hymnal;
              return (
                <li key={h.code} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3">
                  <div className="grid min-w-0 flex-1 gap-0.5">
                    <p className="flex items-center gap-2 font-medium">
                      {h.code}
                      {isDefault ? <Badge variant="secondary">Default</Badge> : null}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {h.label ? `${h.label} · ` : ""}
                      {hymnCount(h.hymn_count)}
                    </p>
                  </div>
                  {admin && isDefault ? (
                    <p className="text-sm text-muted-foreground">
                      Default. Change it in{" "}
                      <Link href="/settings/church" className="underline underline-offset-4">
                        Church profile
                      </Link>
                      .
                    </p>
                  ) : null}
                  {admin && !isDefault && REMOVABLE_CODE.test(h.code) ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="touch"
                      className="md:h-8"
                      aria-label={`Remove ${h.code}`}
                      onClick={() => {
                        const source = sources.data?.items.find((s) => s.code === h.code);
                        removed.current = false;
                        setRemoveWords({
                          title: `Remove ${h.code}?`,
                          body: removeBody(h, sources.data ? source !== undefined : null),
                          confirm: `Remove ${h.code}`,
                        });
                        setRemoving(h);
                      }}
                    >
                      Remove…
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <p className="text-sm text-muted-foreground">{hymnalsLine(data.items)}</p>
        </>
      );
  } else if (hymnals.isError) {
    body = <ErrorState error={hymnals.error} onRetry={() => void hymnals.refetch()} retrying={hymnals.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="hymnals-title" className="grid gap-3">
      <h3 id="hymnals-title" className="text-base font-medium">
        Hymnals
      </h3>
      {body}
      {admin ? (
        <Button ref={addButton} type="button" variant="outline" size="touch" className="w-full sm:w-fit md:h-8" onClick={() => setAdding(true)}>
          Add a hymnal
        </Button>
      ) : (
        <p className="text-sm text-muted-foreground">{MEMBER_HYMNALS_NOTE}</p>
      )}
      {admin && adding ? <AddHymnalDialog onClose={() => setAdding(false)} /> : null}
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => {
          // while the removal runs the confirmation stays open (Cancel, Escape and a tap outside are ignored)
          if (!open && !remove.isPending) setRemoving(null);
        }}
        title={removeWords.title}
        description={removeWords.body}
        confirmLabel={removeWords.confirm}
        destructive
        pending={remove.isPending}
        finalFocus={() => (removed.current ? addButton.current : true)}
        onConfirm={() => {
          if (removing === null) return;
          const code = removing.code;
          remove.mutate(code, {
            onSuccess: () => {
              removed.current = true;
              toast.success(`Removed ${code}.`);
            },
            // a 404: it was removed elsewhere, so its row goes too (toasted, and the lists refreshed, by the mutation)
            onError: (e) => {
              if (e.status === 404) removed.current = true;
            },
            // closes the confirmation only while it still asks about this hymnal
            onSettled: () => setRemoving((current) => (current?.code === code ? null : current)),
          });
        }}
      />
    </section>
  );
}

/**
 * **Add a hymnal** (6a spec UX §2a): the bundled hymnals, each "{code} ·
 * {label} · {n} hymns" with **Add**, or **Added** when the church has it. The
 * dialog stays open after an add (the row turns to Added) and cannot be closed
 * while one runs; after 8 s it says the add is still working.
 */
export function AddHymnalDialog({ onClose }: { onClose(): void }) {
  const sources = useHymnalSources(true);
  const add = useAddHymnal();
  const [addingCode, setAddingCode] = useState<string | null>(null);
  const [added, setAdded] = useState<ReadonlySet<string>>(new Set());
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    if (!add.isPending) return;
    const timer = setTimeout(() => setSlow(true), STILL_WORKING_AFTER_MS);
    return () => clearTimeout(timer);
  }, [add.isPending]);

  function addSource(source: HymnalSource) {
    if (add.isPending) return;
    setSlow(false);
    setAddingCode(source.code);
    add.mutate(source.code, {
      onSuccess: (answer) => {
        setAdded((codes) => new Set(codes).add(answer.code));
        // nothing inserted or filled in: the church had it all already (another tab added it meanwhile)
        toast.success(
          answer.inserted + answer.updated === 0
            ? `${answer.code} is already added.`
            : `Added ${answer.code} (${hymnCount(answer.inserted)}).`,
        );
      },
      onSettled: () => setAddingCode(null),
    });
  }

  let body;
  if (sources.data) {
    body =
      sources.data.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{NO_SOURCES}</p>
      ) : (
        <ul className="divide-y rounded-lg border" aria-label="Bundled hymnals">
          {sources.data.items.map((source) => {
            const present = source.present || added.has(source.code);
            return (
              <li key={source.code} className="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
                <div className="grid min-w-0 flex-1 gap-0.5">
                  <p className="text-sm font-medium">
                    {[source.code, source.label, hymnCount(source.hymn_count)].filter(Boolean).join(" · ")}
                  </p>
                  {source.has_scripture_refs ? null : <p className="text-sm text-muted-foreground">{NO_REFS_NOTE}</p>}
                </div>
                {present ? (
                  <Button type="button" variant="outline" size="touch" className="md:h-8" disabled>
                    Added
                  </Button>
                ) : (
                  <PendingButton
                    type="button"
                    size="touch"
                    className="md:h-8"
                    aria-label={`Add ${source.code}`}
                    pending={addingCode === source.code}
                    pendingLabel="Adding…"
                    disabled={add.isPending && addingCode !== source.code}
                    onClick={() => addSource(source)}
                  >
                    Add
                  </PendingButton>
                )}
              </li>
            );
          })}
        </ul>
      );
  } else if (sources.isError) {
    body = <ErrorState error={sources.error} onRetry={() => void sources.refetch()} retrying={sources.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        // while an add runs the dialog stays open (Escape and a tap outside are ignored; Done is disabled)
        if (!open && !add.isPending) onClose();
      }}
    >
      <DialogContent showCloseButton={false} className={SHEET}>
        <DialogHeader>
          <DialogTitle>Add a hymnal</DialogTitle>
          <DialogDescription>Hymnals this app can add to your church, with their hymns.</DialogDescription>
        </DialogHeader>
        {body}
        {slow && add.isPending ? (
          <p role="status" className="text-sm text-muted-foreground">
            {STILL_WORKING}
          </p>
        ) : null}
        <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
          <DialogClose disabled={add.isPending} render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>
            Done
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
````

**Create `frontend/src/components/settings/hymns-settings-page.tsx`:**

````tsx
"use client";

import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { useHymnals } from "@/lib/queries/hymns";

import { HymnalsCard } from "./hymnals-card";

export const HYMNS_INTRO = "The hymnals and hymns the builder offers when you choose hymns.";

/**
 * `/settings/hymns` (slice 6a-2; 6a spec UX §2; owner's 6a-2 answers of
 * 2026-10-07): the church's hymnals (`HymnalsCard`) and its hymn library.
 * Every member reads both and adds and edits hymns; owners and admins also
 * delete hymns, set a hymn's year and familiarity, and add or remove hymnals.
 */
export function HymnsSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const hymnals = useHymnals();
  return (
    <section aria-labelledby="hymns-title" className="grid gap-6">
      <div className="grid gap-1">
        <h2 id="hymns-title" className="text-lg font-semibold">
          Hymns
        </h2>
        <p className="text-sm text-muted-foreground">{HYMNS_INTRO}</p>
      </div>
      <HymnalsCard admin={admin} hymnals={hymnals} />
    </section>
  );
}
````

**Create `frontend/src/app/(signed-in)/(church)/settings/hymns/page.tsx`:**

````tsx
"use client";

import { HymnsSettingsPage } from "@/components/settings/hymns-settings-page";

/** Settings → Hymns: the church's hymnals and its hymn library (slice 6a-2; F §4.1). */
export default function HymnsSettingsRoute() {
  return <HymnsSettingsPage />;
}
````

- [ ] **Step 4: See them pass (three runs), and the suite**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/settings/hymns-settings-page.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
```
      Tests  12 passed (12)
      Tests  12 passed (12)
      Tests  12 passed (12)
```
```
 Test Files  102 passed (102)
      Tests  854 passed (854)
```
```
typecheck 0
lint 0
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/hymnals-card.tsx frontend/src/components/settings/hymns-settings-page.tsx frontend/src/components/settings/hymns-settings-page.test.tsx 'frontend/src/app/(signed-in)/(church)/settings/hymns/page.tsx'
git commit -q -m "Slice 6a-2: the Hymns page and its Hymnals card" -m "/settings/hymns shows the church's hymnals with their names, counts and
the default. Owners and admins add a bundled hymnal (the dialog stays
open, says when one has no scripture references, cannot be closed while
an add runs and says it is still working after 8 s) and remove any but
the default, after a confirmation that says what is lost." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `854 passed` in 102 files.

### Task 8: The Hymn library and the hymn dialog (S UX §2b; clarifications 7-10, 19)

**Files:**
- Create: `frontend/src/components/settings/hymn-library.test.tsx`, `frontend/src/components/settings/hymn-dialog.tsx`, `frontend/src/components/settings/hymn-library.tsx`
- Modify: `frontend/src/components/settings/hymns-settings-page.tsx`

- [ ] **Step 1: Write the failing tests**

With `hymnsServer` (a fake `/hymns` that filters, pages and remembers the writes). S's DOM cases: a member reads the rows in order (a hymn with no number shows its title alone), opens one, sees the facts read-only with the note and no **Delete hymn**, and saves only the field changed; the search waits 300 ms and starts from the first page, and an empty result offers **Clear search** (focus back in the box); **Show more** asks for `offset=50`; chips with two hymnals (badges on the rows, `aria-pressed`); an add sends the whole body and refreshes the hymn lists, the hymnals and the profile; the client checks; a server field error under its field and a 409 above the buttons; an admin's year and cleared familiarity; a delete, confirmed, which also marks the builder's cached picker list and matches stale and moves focus to **Add hymn**; an edit of a hymn deleted elsewhere; the dialog held open while a save runs; a role 403; both empty states.

**Create `frontend/src/components/settings/hymn-library.test.tsx`:**

````tsx
/**
 * Settings → Hymns, the Hymn library (slice 6a-2; 6a spec UX §2b): search,
 * hymnal chips, pages of 50 with Show more, and the add and edit dialog (any
 * member), with delete and the year and familiarity for admins. Rendered
 * inside the Settings layout, as the route is, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it, vi } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import HymnsSettingsRoute from "@/app/(signed-in)/(church)/settings/hymns/page";
import { Toaster } from "@/components/ui/sonner";
import type { Church, Hymn, HymnPage } from "@/lib/api/types";
import { keys } from "@/lib/queries/keys";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, hymn, hymnDetail, hymnals, hymnalSources, me } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { ADMINS_ONLY_FIELD, DELETE_BODY, SAVED_SERVICES_NOTE } from "./hymn-dialog";
import { EMPTY_ADMIN, EMPTY_MEMBER, LIBRARY_CAPTION } from "./hymn-library";

afterEach(() => {
  toast.dismiss();
});

const THIS_YEAR = new Date().getFullYear();
const HOLY = hymn({ number: 138, title: "Holy, Holy, Holy", themes: ["Trinity"], scripture_refs: "Isaiah 6:3", text_year: 1826, hymnal_count: 12 });
const UNNUMBERED = hymn({ number: null, title: "Untitled Tune", link: null });
const PH_ONE = hymn({ number: 1, hymnal: "PH1990", title: "Come, Thou long-expected Jesus" });

/** A fake `/hymns`: `GET` filters and pages what the writes left, as the server would. */
function hymnsServer(initial: Hymn[] = [HOLY, hymn(), UNNUMBERED]) {
  let items = [...initial];
  return {
    list: (req: RecordedRequest): HymnPage => {
      const query = new URL(req.path, "http://localhost").searchParams;
      const q = (query.get("q") ?? "").toLowerCase();
      const code = query.get("hymnal");
      const matched = items.filter(
        (h) => (code === null || h.hymnal === code) && (q === "" || h.title.toLowerCase().includes(q) || String(h.number) === q),
      );
      const limit = Number(query.get("limit"));
      const offset = Number(query.get("offset"));
      return { items: matched.slice(offset, offset + limit), total: matched.length, limit, offset };
    },
    add: (req: RecordedRequest) => {
      const body = req.body as { title: string; number: number | null };
      items = [...items, hymn({ number: body.number, title: body.title })];
      return { status: 201, body: hymnDetail({ number: body.number, title: body.title }) };
    },
    save: (id: string) => (req: RecordedRequest) => {
      items = items.map((h) => (h.id === id ? { ...h, ...(req.body as Partial<Hymn>) } : h));
      return hymnDetail({ id, ...(req.body as object) });
    },
    remove: (id: string) => () => {
      items = items.filter((h) => h.id !== id);
      return { deleted: true };
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const server = hymnsServer();
  const api = installFakeApi({
    "GET /hymnals": hymnals(),
    "GET /hymnal-sources": hymnalSources(),
    "GET /hymns": server.list,
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <SettingsLayout>
        <HymnsSettingsRoute />
      </SettingsLayout>
      <Toaster />
    </>,
    { me: me({ churches: [active] }), church: active, path: "/settings/hymns" },
  );
  return { ...view, api };
}

function hymnRows() {
  return within(screen.getByRole("list", { name: "Hymns" })).getAllByRole("button");
}

function listRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "GET" && r.path.startsWith("/hymns?")).map((r) => r.path);
}

function writes(api: { requests: RecordedRequest[] }, method: string) {
  return api.requests.filter((r) => r.method === method && r.path.startsWith("/hymns"));
}

async function openEdit(user: ReturnType<typeof renderPage>["user"], label: RegExp) {
  await user.click(await screen.findByRole("button", { name: label }));
  return screen.findByRole("dialog", { name: "Edit hymn" });
}

describe("Settings → Hymns, the Hymn library (slice 6a-2)", () => {
  it("lists the hymns in the server's order with the count, and a member edits one without the year or familiarity", async () => {
    const server = hymnsServer();
    const { api, user } = renderPage("member", { "GET /hymns": server.list, [`PATCH /hymns/${HOLY.id}`]: server.save(HOLY.id) });
    expect(await screen.findByText("3 hymns")).toBeInTheDocument();
    expect(screen.getByText(LIBRARY_CAPTION)).toBeInTheDocument();
    expect(hymnRows().map((row) => row.textContent)).toEqual(["#138 Holy, Holy, Holy", "#403 Come, Thou Almighty King", "Untitled Tune"]);
    expect(screen.queryByRole("group", { name: "Hymnal" })).toBeNull();
    expect(listRequests(api)[0]).toBe("/hymns?limit=50&offset=0");

    const dialog = await openEdit(user, /^#138 Holy/);
    expect(within(dialog).getByLabelText("Title")).toHaveValue("Holy, Holy, Holy");
    expect(within(dialog).getByLabelText("Themes")).toHaveValue("Trinity");
    expect(within(dialog).getByLabelText("Year the words were written")).toHaveAttribute("readonly");
    expect(within(dialog).getByLabelText("Number of hymnals (familiarity)")).toHaveValue("12");
    expect(within(dialog).getAllByText(ADMINS_ONLY_FIELD)).toHaveLength(2);
    expect(within(dialog).queryByRole("button", { name: "Delete hymn" })).toBeNull();
    expect(within(dialog).queryByLabelText("Hymnal")).toBeNull();
    expect(within(dialog).getByText(SAVED_SERVICES_NOTE)).toBeInTheDocument();
    await user.clear(within(dialog).getByLabelText("Scripture references"));
    await user.type(within(dialog).getByLabelText("Scripture references"), "Revelation 4:8");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Hymn updated.")).toBeInTheDocument();
    expect(writes(api, "PATCH")[0].body).toEqual({ scripture_refs: "Revelation 4:8" });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  });

  it("searches 300 ms after typing, from the first page, and offers Clear search when nothing matches", async () => {
    const { api, user } = renderPage("member");
    await screen.findByText("3 hymns");
    const search = screen.getByRole("searchbox", { name: "Search by title or number" });
    await user.type(search, "holy");
    expect(await screen.findByText("1 matching hymn")).toBeInTheDocument();
    expect(listRequests(api)).toContain("/hymns?limit=50&offset=0&q=holy");
    expect(listRequests(api)).not.toContain("/hymns?limit=50&offset=0&q=h");
    await user.clear(search);
    await user.type(search, "zzz");
    expect(await screen.findByText("No hymns match “zzz”.")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Clear search" })[1]);
    expect(await screen.findByText("3 hymns")).toBeInTheDocument();
    expect(search).toHaveValue("");
    expect(search).toHaveFocus();
  });

  it("loads the next 50 with Show more", async () => {
    const many = Array.from({ length: 60 }, (_, i) => hymn({ number: i + 1, title: `Hymn ${i + 1}` }));
    const server = hymnsServer(many);
    const { api, user } = renderPage("member", { "GET /hymns": server.list });
    expect(await screen.findByText("60 hymns")).toBeInTheDocument();
    expect(hymnRows()).toHaveLength(50);
    await user.click(screen.getByRole("button", { name: "Show more" }));
    await waitFor(() => expect(hymnRows()).toHaveLength(60));
    expect(listRequests(api)).toContain("/hymns?limit=50&offset=50");
    expect(screen.queryByRole("button", { name: "Show more" })).toBeNull();
  });

  it("filters by hymnal with chips when the church has several, and badges each row", async () => {
    const server = hymnsServer([HOLY, PH_ONE]);
    const { api, user } = renderPage("member", {
      "GET /hymns": server.list,
      "GET /hymnals": hymnals({ items: [{ code: "GG2013", hymn_count: 1, scripture_ref_count: 1 }, { code: "PH1990", hymn_count: 1, scripture_ref_count: 0 }] }),
    });
    const group = await screen.findByRole("group", { name: "Hymnal" });
    expect(within(group).getAllByRole("button").map((b) => [b.textContent, b.getAttribute("aria-pressed")])).toEqual([
      ["All", "true"], ["GG2013", "false"], ["PH1990", "false"],
    ]);
    await waitFor(() => expect(hymnRows().map((row) => row.textContent)).toEqual(["#138 Holy, Holy, HolyGG2013", "#1 Come, Thou long-expected JesusPH1990"]));
    await user.click(within(group).getByRole("button", { name: "PH1990" }));
    expect(await screen.findByText("1 matching hymn")).toBeInTheDocument();
    expect(listRequests(api)).toContain("/hymns?limit=50&offset=0&hymnal=PH1990");
    expect(within(group).getByRole("button", { name: "PH1990" })).toHaveAttribute("aria-pressed", "true");
  });

  it("adds a hymn in the default hymnal: the body, the toast, and every hymn list refreshed", async () => {
    const server = hymnsServer();
    const { api, user, queryClient } = renderPage("admin", { "GET /hymns": server.list, "POST /hymns": server.add });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    expect(within(dialog).queryByText(SAVED_SERVICES_NOTE)).toBeNull();
    await user.type(within(dialog).getByLabelText("Title"), " Be Thou My Vision ");
    await user.type(within(dialog).getByLabelText("Number"), "339");
    await user.type(within(dialog).getByLabelText("Year the words were written"), "1905");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await screen.findByText("Hymn added.")).toBeInTheDocument();
    expect(writes(api, "POST")[0].body).toEqual({
      title: "Be Thou My Vision", number: 339, hymnal: "GG2013", scripture_refs: null, theme: null, link: null, text_year: 1905, hymnal_count: null,
    });
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    for (const key of [["church", church().id, "hymns"], ["church", church().id, "hymnals"], ["church", church().id, "profile"]]) {
      expect(invalidate).toHaveBeenCalledWith({ queryKey: key });
    }
    expect(await screen.findByText("4 hymns")).toBeInTheDocument();
  });

  it("checks the form before sending: the server's words under each field, the first one focused", async () => {
    const { api, user } = renderPage("admin");
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    await user.type(within(dialog).getByLabelText("Number"), "12a");
    await user.type(within(dialog).getByLabelText("Year the words were written"), String(THIS_YEAR + 1));
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(within(dialog).getByText("Hymn title is required.")).toBeInTheDocument();
    expect(within(dialog).getByText("Hymn number must be a whole number.")).toBeInTheDocument();
    expect(within(dialog).getByText(`Year must be a whole number from 1 to ${THIS_YEAR}.`)).toBeInTheDocument();
    expect(within(dialog).getByLabelText("Title")).toHaveFocus();
    expect(writes(api, "POST")).toHaveLength(0);
  });

  it("shows the server's field error under its field, and a duplicate above the buttons", async () => {
    const { api, user } = renderPage("admin", {
      "POST /hymns": fakeError(422, "invalid_request", "Links can't contain spaces.", { fields: { link: "Links can't contain spaces." } }),
    });
    await screen.findByText("3 hymns");
    await user.click(screen.getByRole("button", { name: "Add hymn" }));
    const dialog = await screen.findByRole("dialog", { name: "Add hymn" });
    await user.type(within(dialog).getByLabelText("Title"), "Holy, Holy, Holy");
    await user.type(within(dialog).getByLabelText("Link"), "https://hymnary.org/a b");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await within(dialog).findByText("Links can't contain spaces.")).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getByLabelText("Link")).toHaveFocus());

    api.set("POST /hymns", fakeError(409, "conflict", "GG2013 already has #138 Holy, Holy, Holy."));
    await user.clear(within(dialog).getByLabelText("Link"));
    await user.type(within(dialog).getByLabelText("Number"), "138");
    await user.click(within(dialog).getByRole("button", { name: "Add hymn" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent("GG2013 already has #138 Holy, Holy, Holy.");
    expect(screen.getByRole("dialog", { name: "Add hymn" })).toBeInTheDocument();
  });

  it("lets an admin set the year and clear the familiarity, sending only those", async () => {
    const server = hymnsServer();
    const { api, user } = renderPage("admin", { "GET /hymns": server.list, [`PATCH /hymns/${HOLY.id}`]: server.save(HOLY.id) });
    const dialog = await openEdit(user, /^#138 Holy/);
    const year = within(dialog).getByLabelText("Year the words were written");
    expect(year).not.toHaveAttribute("readonly");
    await user.clear(year);
    await user.type(year, "1861");
    await user.clear(within(dialog).getByLabelText("Number of hymnals (familiarity)"));
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Hymn updated.")).toBeInTheDocument();
    expect(writes(api, "PATCH")[0].body).toEqual({ text_year: 1861, hymnal_count: null });
  });

  it("asks before an admin deletes a hymn, then deletes it, marks the builder's lists stale; focus goes to Add hymn", async () => {
    const server = hymnsServer();
    const { api, user, queryClient } = renderPage("admin", { "GET /hymns": server.list, [`DELETE /hymns/${HOLY.id}`]: server.remove(HOLY.id) });
    // what the builder's hymn picker and "Hymns for the readings" have cached (slice 3's keys)
    const picker = keys.hymns(church().id, { hymnal: "GG2013", limit: 2000, recent_for_date: null });
    const matches = keys.hymnMatches(church().id, { refs: ["Isaiah 6:1-8"], hymnal: "GG2013", recent_for_date: null });
    queryClient.setQueryData(picker, { items: [HOLY], total: 1, limit: 2000, offset: 0 });
    queryClient.setQueryData(matches, { hymnal: "GG2013", refs_used: [], unparsed_refs: [], total_matched: 0, items: [] });
    const dialog = await openEdit(user, /^#138 Holy/);
    await user.click(within(dialog).getByRole("button", { name: "Delete hymn" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Delete “Holy, Holy, Holy”?" });
    expect(confirm).toHaveTextContent(DELETE_BODY);
    await user.click(within(confirm).getByRole("button", { name: "Delete hymn" }));
    expect(await screen.findByText("Hymn deleted.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(writes(api, "DELETE")).toHaveLength(1);
    expect(queryClient.getQueryState(picker)?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(matches)?.isInvalidated).toBe(true);
    expect(await screen.findByText("2 hymns")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Add hymn" })).toHaveFocus());
  });

  it("closes the edit dialog when the hymn was deleted elsewhere, refetches, and focuses Add hymn", async () => {
    const server = hymnsServer();
    const { user } = renderPage("member", { "GET /hymns": server.list, [`PATCH /hymns/${HOLY.id}`]: fakeError(404, "not_found", "Hymn not found.") });
    const dialog = await openEdit(user, /^#138 Holy/);
    server.remove(HOLY.id)();
    await user.type(within(dialog).getByLabelText("Title"), "!");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("This hymn was already deleted.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(await screen.findByText("2 hymns")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Add hymn" })).toHaveFocus());
  });

  it("keeps the dialog open while a save runs", async () => {
    let finish: (value: unknown) => void = () => {};
    const { user } = renderPage("member", {
      [`PATCH /hymns/${HOLY.id}`]: () => new Promise((resolve) => {
        finish = resolve;
      }),
    });
    const dialog = await openEdit(user, /^#138 Holy/);
    await user.type(within(dialog).getByLabelText("Title"), "!");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeDisabled();
    await user.keyboard("{Escape}");
    expect(screen.getByRole("dialog", { name: "Edit hymn" })).toBeInTheDocument();
    finish(hymnDetail({ id: HOLY.id, title: "Holy, Holy, Holy!" }));
    expect(await screen.findByText("Hymn updated.")).toBeInTheDocument();
  });

  it("toasts a role 403, closes the dialog and refetches the church profile", async () => {
    const { user, queryClient } = renderPage("admin", {
      [`PATCH /hymns/${HOLY.id}`]: fakeError(403, "forbidden", "Only church admins can do this."),
    });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");
    const dialog = await openEdit(user, /^#138 Holy/);
    await user.clear(within(dialog).getByLabelText("Year the words were written"));
    await user.type(within(dialog).getByLabelText("Year the words were written"), "1830");
    await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
    expect(await screen.findByText("Only church admins can do this.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["church", church().id, "profile"] });
  });

  it("shows each role its empty state", async () => {
    const empty = { "GET /hymns": { items: [], total: 0, limit: 50, offset: 0 }, "GET /hymnals": hymnals({ items: [], effective_hymnal: null }) };
    const { unmount } = renderPage("admin", empty);
    expect(await screen.findByText("No hymns yet")).toBeInTheDocument();
    expect(screen.getByText(EMPTY_ADMIN)).toBeInTheDocument();
    unmount();
    renderPage("member", empty);
    expect(await screen.findByText(EMPTY_MEMBER)).toBeInTheDocument();
  });
});
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/hymn-library.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (`./hymn-library` does not exist yet):
```
 FAIL  |dom| src/components/settings/hymn-library.test.tsx [ src/components/settings/hymn-library.test.tsx ]
      Tests  no tests
```

- [ ] **Step 3: Write the dialog and the library, and put the library on the page**

**Create `frontend/src/components/settings/hymn-dialog.tsx`:**

````tsx
"use client";

import { useRef, useState, type FormEvent, type RefObject } from "react";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import type { ApiError } from "@/lib/api/client";
import type { Hymn } from "@/lib/api/types";
import { hymnFieldErrors, isDuplicateHymn, useCreateHymn, useDeleteHymn, useUpdateHymn } from "@/lib/queries/hymn-library";
import {
  emptyHymnForm,
  hymnFormErrors,
  hymnFormFrom,
  hymnLabel,
  hymnPatch,
  newHymnBody,
  type HymnFieldErrors,
  type HymnForm,
} from "@/lib/settings/hymns";

export const SAVED_SERVICES_NOTE = "Changes also appear in saved services that use this hymn.";
export const ADMINS_ONLY_FIELD = "Only admins can change this.";
export const REFS_HELP = "Used by “Hymns for the readings” and AI suggestions.";
export const DELETE_BODY = "Saved services keep this hymn. Services in progress that use it will ask you to choose a replacement.";

const SHEET =
  "max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-w-lg";

/** The order fields are checked and focused in. */
const ORDER: (keyof HymnForm)[] = ["title", "number", "hymnal", "scripture_refs", "themes", "link", "text_year", "hymnal_count"];

export type HymnDialogProps = {
  /** null: **Add hymn**; a hymn: **Edit hymn**. */
  hymn: Hymn | null;
  /** The church's hymnal codes; the Hymnal field shows only with more than one. */
  codes: string[];
  /** The add form's hymnal (the effective default), "" when the church has none. */
  defaultHymnal: string;
  admin: boolean;
  /** Where focus goes when the hymn is gone (deleted here or elsewhere): the row that opened it is gone too. */
  fallbackFocus: RefObject<HTMLElement | null>;
  /** Closes the dialog; `key` is "add" or the hymn's id, so a late answer never closes another one. */
  onClose(key: string): void;
};

/**
 * **Add hymn** / **Edit hymn** (slice 6a-2; 6a spec UX §2b): Title, Number,
 * Hymnal (with several), Scripture references, Themes, Link, and the year and
 * familiarity (an admin's; a member sees them read-only and never sends them).
 * An edit sends only what changed and notes that saved services follow it; an
 * admin may delete the hymn (confirmed). A 409 shows above the buttons, a field
 * error under its field; the dialog cannot be closed while a request runs. A
 * bottom sheet on phones, as Edit contact is.
 */
export function HymnDialog({ hymn, codes, defaultHymnal, admin, fallbackFocus, onClose }: HymnDialogProps) {
  const key = hymn?.id ?? "add";
  const thisYear = new Date().getFullYear();
  const create = useCreateHymn();
  const update = useUpdateHymn();
  const remove = useDeleteHymn();
  const [baseline] = useState<HymnForm>(() => (hymn ? hymnFormFrom(hymn) : emptyHymnForm(defaultHymnal)));
  const [form, setForm] = useState<HymnForm>(baseline);
  const [errors, setErrors] = useState<HymnFieldErrors>({});
  const [duplicate, setDuplicate] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const gone = useRef(false);
  const refs = useRef<Partial<Record<keyof HymnForm, HTMLElement | null>>>({});
  const pending = create.isPending || update.isPending || remove.isPending;
  const options = { thisYear, admin };

  const set = (field: keyof HymnForm, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
    setDuplicate(null);
  };

  const close = (isGone = false) => {
    gone.current = isGone;
    onClose(key);
  };

  function showErrors(found: HymnFieldErrors) {
    setErrors(found);
    const first = ORDER.find((field) => found[field]);
    if (first) refs.current[first]?.focus();
  }

  const handlers = {
    onError: (e: ApiError) => {
      if (e.status === 403 || e.status === 404) {
        close(e.status === 404); // toasted, and the role or the lists refetched, by the mutation
        return;
      }
      if (isDuplicateHymn(e)) {
        setDuplicate(e.message);
        return;
      }
      const found = hymnFieldErrors(e);
      if (found) showErrors(found);
    },
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (pending) return;
    const found = hymnFormErrors(form, options);
    if (Object.keys(found).length > 0) {
      showErrors(found);
      return;
    }
    if (hymn === null) {
      create.mutate(newHymnBody(form, options), {
        ...handlers,
        onSuccess: () => {
          toast.success("Hymn added.");
          close();
        },
      });
      return;
    }
    const patch = hymnPatch(baseline, form, options);
    if (Object.keys(patch).length === 0) {
      close();
      return;
    }
    update.mutate(
      { id: hymn.id, patch },
      {
        ...handlers,
        onSuccess: () => {
          toast.success("Hymn updated.");
          close();
        },
      },
    );
  }

  function field(
    name: keyof HymnForm,
    label: string,
    extra: { help?: string; placeholder?: string; numeric?: boolean; readOnly?: boolean; maxLength?: number } = {},
  ) {
    const id = `hymn-${name}`;
    const error = errors[name];
    const described = [extra.help ? `${id}-help` : null, error ? `${id}-error` : null].filter(Boolean).join(" ");
    return (
      <div className="grid gap-1.5">
        <Label htmlFor={id}>{label}</Label>
        <Input
          id={id}
          ref={(el) => {
            refs.current[name] = el;
          }}
          value={form[name]}
          className="h-11 md:h-9"
          placeholder={extra.placeholder}
          readOnly={extra.readOnly}
          maxLength={extra.maxLength}
          autoComplete="off"
          {...(extra.numeric ? { inputMode: "numeric" as const } : {})}
          aria-invalid={error ? true : undefined}
          aria-describedby={described || undefined}
          onChange={(event) => set(name, event.target.value)}
        />
        {extra.help ? (
          <p id={`${id}-help`} className="text-sm text-muted-foreground">
            {extra.help}
          </p>
        ) : null}
        {error ? (
          <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  const hymnalItems = Object.fromEntries(codes.map((code) => [code, code]));
  const factsHelp = admin ? undefined : ADMINS_ONLY_FIELD;

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        // while a request runs the dialog stays open (Escape and a tap outside are ignored; Cancel is disabled)
        if (!open && !pending) close();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className={SHEET}
        finalFocus={() => (gone.current ? fallbackFocus.current : true)}
      >
        <DialogHeader>
          <DialogTitle>{hymn ? "Edit hymn" : "Add hymn"}</DialogTitle>
          <DialogDescription>{hymn ? hymnLabel(hymn) : "A hymn your church sings that is not in the list yet."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} noValidate className="grid gap-4">
          {field("title", "Title", { maxLength: 300 })}
          {field("number", "Number", { numeric: true, maxLength: 5 })}
          {codes.length > 1 ? (
            <div className="grid gap-1.5">
              <Label htmlFor="hymn-hymnal">Hymnal</Label>
              <Select
                value={form.hymnal}
                items={hymnalItems}
                onValueChange={(value) => {
                  if (typeof value === "string") set("hymnal", value);
                }}
              >
                <SelectTrigger
                  id="hymn-hymnal"
                  ref={(el: HTMLElement | null) => {
                    refs.current.hymnal = el;
                  }}
                  className="h-11 w-full data-[size=default]:h-11 md:h-9"
                  aria-invalid={errors.hymnal ? true : undefined}
                  aria-describedby={errors.hymnal ? "hymn-hymnal-error" : undefined}
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {codes.map((code) => (
                    <SelectItem key={code} value={code}>
                      {code}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.hymnal ? (
                <p id="hymn-hymnal-error" role="alert" className="text-sm text-destructive">
                  {errors.hymnal}
                </p>
              ) : null}
            </div>
          ) : null}
          {field("scripture_refs", "Scripture references", { placeholder: "e.g. Psalm 23; John 10:11-18", help: REFS_HELP, maxLength: 2000 })}
          {field("themes", "Themes", { placeholder: "e.g. Advent, hope", maxLength: 2000 })}
          {field("link", "Link", { placeholder: "https://hymnary.org/…", maxLength: 500 })}
          {field("text_year", "Year the words were written", { numeric: true, readOnly: !admin, help: factsHelp })}
          {field("hymnal_count", "Number of hymnals (familiarity)", { numeric: true, readOnly: !admin, help: factsHelp })}
          {hymn ? <p className="text-sm text-muted-foreground">{SAVED_SERVICES_NOTE}</p> : null}
          {duplicate ? (
            <Alert variant="destructive" role="alert">
              <AlertDescription>{duplicate}</AlertDescription>
            </Alert>
          ) : null}
          <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            {hymn && admin ? (
              <Button
                type="button"
                variant="destructive"
                size="touch"
                className="sm:mr-auto md:h-8"
                disabled={pending}
                onClick={() => setConfirming(true)}
              >
                Delete hymn
              </Button>
            ) : null}
            <DialogClose disabled={pending} render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>
              Cancel
            </DialogClose>
            <PendingButton type="submit" size="touch" className="md:h-8" pending={create.isPending || update.isPending} pendingLabel={hymn ? "Saving…" : "Adding…"}>
              {hymn ? "Save changes" : "Add hymn"}
            </PendingButton>
          </DialogFooter>
        </form>
        {hymn && admin ? (
          <ConfirmDialog
            open={confirming}
            onOpenChange={(open) => {
              if (!open && !remove.isPending) setConfirming(false);
            }}
            title={`Delete “${hymn.title}”?`}
            description={DELETE_BODY}
            confirmLabel="Delete hymn"
            destructive
            pending={remove.isPending}
            onConfirm={() =>
              remove.mutate(hymn.id, {
                onSuccess: () => {
                  toast.success("Hymn deleted.");
                  setConfirming(false);
                  close(true);
                },
                onError: (e) => {
                  setConfirming(false);
                  if (e.status === 404) close(true); // deleted elsewhere: gone all the same (toasted)
                  if (e.status === 403) close();
                },
              })
            }
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
````

**Create `frontend/src/components/settings/hymn-library.tsx`:**

````tsx
"use client";

import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { Hymn, Hymnals } from "@/lib/api/types";
import { useHymnLibrary } from "@/lib/queries/hymn-library";
import { countLine, hymnLabel } from "@/lib/settings/hymns";

import { HymnDialog } from "./hymn-dialog";

export const LIBRARY_CAPTION = "Anyone in your church can add and edit hymns. Only admins can delete them.";
export const EMPTY_TITLE = "No hymns yet";
export const EMPTY_ADMIN = "Add hymns one at a time, or add a bundled hymnal above.";
export const EMPTY_MEMBER = "Add hymns one at a time, or ask an admin to add a bundled hymnal.";
/** How long typing waits before it searches (6a spec UX §2b). */
export const SEARCH_DEBOUNCE_MS = 300;

/** Which dialog is open: "add", or the hymn being edited. */
type Open = { key: "add" } | { key: string; hymn: Hymn };

/**
 * Settings → Hymns' "Hymn library" (slice 6a-2; 6a spec UX §2b): **Add hymn**,
 * a search by title or number (300 ms after typing stops), hymnal chips when
 * the church has several, the count, and the hymns 50 at a time in the
 * server's order with **Show more**. Each row opens **Edit hymn**.
 */
export function HymnLibrary({ admin, hymnals }: { admin: boolean; hymnals: Hymnals | undefined }) {
  const [text, setText] = useState("");
  const [q, setQ] = useState("");
  const [chosen, setChosen] = useState<string | null>(null);
  const [open, setOpen] = useState<Open | null>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const searchBox = useRef<HTMLInputElement>(null);
  const codes = hymnals?.items.map((h) => h.code) ?? [];
  // A hymnal removed meanwhile is no longer a filter.
  const hymnal = chosen !== null && codes.includes(chosen) ? chosen : null;
  const library = useHymnLibrary({ hymnal, q });

  useEffect(() => {
    const timer = setTimeout(() => setQ(text.trim()), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [text]);

  const clearSearch = () => {
    setText("");
    setQ("");
    searchBox.current?.focus();
  };

  const several = codes.length > 1;
  const pages = library.data?.pages;
  const items = pages?.flatMap((p) => p.items) ?? [];
  const total = pages?.[0]?.total ?? 0;

  let body;
  if (pages) {
    if (total === 0 && q !== "") {
      body = (
        <div className="grid justify-items-start gap-2">
          <p className="text-sm">{`No hymns match “${q}”.`}</p>
          <Button type="button" variant="outline" size="touch" className="md:h-8" onClick={clearSearch}>
            Clear search
          </Button>
        </div>
      );
    } else if (total === 0) {
      body = <EmptyState title={EMPTY_TITLE} description={admin ? EMPTY_ADMIN : EMPTY_MEMBER} />;
    } else {
      body = (
        <>
          <p className="text-sm text-muted-foreground">{countLine(total, q !== "" || hymnal !== null)}</p>
          <ul className="divide-y rounded-lg border" aria-label="Hymns">
            {items.map((h) => (
              <li key={h.id}>
                <button
                  type="button"
                  className="flex min-h-11 w-full items-center gap-2 px-4 py-2 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring md:min-h-9"
                  onClick={() => setOpen({ key: h.id, hymn: h })}
                >
                  <span className="min-w-0 flex-1 break-words">{hymnLabel(h)}</span>
                  {several ? <Badge variant="outline">{h.hymnal}</Badge> : null}
                </button>
              </li>
            ))}
          </ul>
          {library.hasNextPage ? (
            <PendingButton
              type="button"
              variant="outline"
              size="touch"
              className="w-full sm:w-fit md:h-8"
              pending={library.isFetchingNextPage}
              pendingLabel="Loading…"
              onClick={() => void library.fetchNextPage()}
            >
              Show more
            </PendingButton>
          ) : null}
        </>
      );
    }
  } else if (library.isError) {
    body = <ErrorState error={library.error} onRetry={() => void library.refetch()} retrying={library.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="hymn-library-title" className="grid gap-3">
      <div className="grid gap-1">
        <h3 id="hymn-library-title" className="text-base font-medium">
          Hymn library
        </h3>
        <p className="text-sm text-muted-foreground">{LIBRARY_CAPTION}</p>
      </div>
      <Button ref={addButton} type="button" size="touch" className="w-full sm:w-fit md:h-8" onClick={() => setOpen({ key: "add" })}>
        Add hymn
      </Button>
      <div className="relative">
        <Search aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          ref={searchBox}
          type="search"
          aria-label="Search by title or number"
          placeholder="Search by title or number"
          value={text}
          className="h-11 pr-11 pl-9 md:h-9 [&::-webkit-search-cancel-button]:appearance-none"
          autoComplete="off"
          onChange={(event) => setText(event.target.value)}
        />
        {text !== "" ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute top-1/2 right-0 size-11 -translate-y-1/2 md:size-9"
            aria-label="Clear search"
            onClick={clearSearch}
          >
            <X aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      {several ? (
        <div role="group" aria-label="Hymnal" className="flex flex-wrap gap-2">
          {[null, ...codes].map((code) => (
            <Button
              key={code ?? "all"}
              type="button"
              variant={hymnal === code ? "default" : "outline"}
              size="touch"
              className="md:h-8"
              aria-pressed={hymnal === code}
              onClick={() => setChosen(code)}
            >
              {code ?? "All"}
            </Button>
          ))}
        </div>
      ) : null}
      {body}
      {open ? (
        <HymnDialog
          key={open.key}
          hymn={"hymn" in open ? open.hymn : null}
          codes={codes}
          defaultHymnal={hymnals?.effective_hymnal ?? codes[0] ?? ""}
          admin={admin}
          fallbackFocus={addButton}
          onClose={(key) => setOpen((current) => (current?.key === key ? null : current))}
        />
      ) : null}
    </section>
  );
}
````

**In `frontend/src/components/settings/hymns-settings-page.tsx`, replace:**

````tsx

import { HymnalsCard } from "./hymnals-card";
````

**with:**

````tsx

import { HymnLibrary } from "./hymn-library";
import { HymnalsCard } from "./hymnals-card";
````

**In `frontend/src/components/settings/hymns-settings-page.tsx`, replace:**

````tsx
      <HymnalsCard admin={admin} hymnals={hymnals} />
````

**with:**

````tsx
      <HymnalsCard admin={admin} hymnals={hymnals} />
      <HymnLibrary admin={admin} hymnals={hymnals.data} />
````

- [ ] **Step 4: See them pass (three runs), and the suite**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/settings/hymn-library.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
```
      Tests  13 passed (13)
      Tests  13 passed (13)
      Tests  13 passed (13)
```
```
 Test Files  103 passed (103)
      Tests  867 passed (867)
```
```
typecheck 0
lint 0
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/hymn-dialog.tsx frontend/src/components/settings/hymn-library.tsx frontend/src/components/settings/hymn-library.test.tsx frontend/src/components/settings/hymns-settings-page.tsx
git commit -q -m "Slice 6a-2: the hymn library and the add and edit dialog" -m "The library lists the church's hymns 50 at a time with Show more, a
search by title or number and hymnal chips. Any member adds a hymn and
edits one (only what changed is sent; the dialog says saved services
follow an edit); owners and admins also delete one, after a
confirmation, and set its year and familiarity, which members see
read-only. A duplicate shows in the dialog; the dialog stays open while
a request runs; a hymn deleted elsewhere closes it with a toast." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `867 passed` in 103 files.

### Task 9: Hymns in the Settings nav, and the two links to it (answer 3; clarifications 2, 20)

**Files:**
- Modify: `frontend/src/components/settings/settings-layout.test.tsx`, `frontend/src/components/settings/church-settings-page.test.tsx`, `frontend/src/components/builder/hymns/hymns-step.test.tsx`, `frontend/src/components/settings/sections.ts`, `frontend/src/lib/features.ts`, `frontend/src/components/settings/church-settings-page.tsx`

- [ ] **Step 1: Change the tests**

The nav lists Church, Hymns, Bulletin, Contacts, Account (five links) and marks Hymns on its page; the Church page's no-hymns line has the link, in the admin's form and in the member's read-only summary (a new test; plan review M5); the builder's empty-hymnal state links to `/settings/hymns`.

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
      ["Church", "/settings/church"],
````

**with:**

````tsx
      ["Church", "/settings/church"],
      ["Hymns", "/settings/hymns"],
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    ["/settings/contacts", "Contacts"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 5b-1, 5b-2): %s", (path, label) => {
````

**with:**

````tsx
    ["/settings/hymns", "Hymns"],
    ["/settings/contacts", "Contacts"],
    ["/settings/account", "Account"],
  ])("marks the section current on its page (slices 6a-2, 5b-1, 5b-2): %s", (path, label) => {
````

**In `frontend/src/components/settings/settings-layout.test.tsx`, replace:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(4);
````

**with:**

````tsx
    expect(within(screen.getByRole("navigation", { name: "Settings sections" })).getAllByRole("link")).toHaveLength(5);
````

**In `frontend/src/components/settings/church-settings-page.test.tsx`, replace:**

````tsx
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Default hymnal" })).toBeNull();
````

**with:**

````tsx
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add hymns on the Hymns page" })).toHaveAttribute("href", "/settings/hymns"); // 6a-2
    expect(screen.queryByRole("combobox", { name: "Default hymnal" })).toBeNull();
````

**In `frontend/src/components/settings/church-settings-page.test.tsx`, replace:**

````tsx
    expect(screen.queryByText("HL1955")).toBeNull();
  });
````

**with:**

````tsx
    expect(screen.queryByText("HL1955")).toBeNull();
  });

  it("shows a member of a church with no hymns the link to the Hymns page (slice 6a-2)", async () => {
    renderPage("member", { default_hymnal: null, effective_hymnal: null });
    expect(await screen.findByText("Your church has no hymns yet, so there is no default hymnal.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add hymns on the Hymns page" })).toHaveAttribute("href", "/settings/hymns");
  });
````

**In `frontend/src/components/builder/hymns/hymns-step.test.tsx`, replace:**

````tsx
    expect(screen.getByText("Add hymns in the current app under Settings → Hymns.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Settings/ })).toBeNull(); // Settings → Hymns ships in 6a
````

**with:**

````tsx
    expect(screen.getByText("Add hymns on the Settings → Hymns page to choose hymns here.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Settings → Hymns" })).toHaveAttribute("href", "/settings/hymns"); // 6a-2
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx src/components/settings/church-settings-page.test.tsx src/components/builder/hymns/hymns-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected** (six `×`, in any order, and Vitest's `Failed Tests 6` banner, which the grep also matches):
```
   × the Settings area (slice 6a-1) > shows the heading, who you are in the church, and the sections with the current one marked
   × the Settings area (slice 6a-1) > marks the section current on its page (slices 6a-2, 5b-1, 5b-2): /settings/hymns
   × the Settings area (slice 6a-1) > shows a member the same sections, and /settings opens Church
   × Settings → Church (slice 6a-1) > shows a member of a church with no hymns the link to the Hymns page (slice 6a-2)
   × Settings → Church (slice 6a-1) > keeps a stale stored translation or hymnal selectable, sends a new hymnal, and says when there are no hymnals
   × the Hymns step (S User experience) > shows the empty-hymnal state instead of the pickers; a pick still shows, as not in the hymnal
⎯⎯⎯⎯⎯⎯⎯ Failed Tests 6 ⎯⎯⎯⎯⎯⎯⎯
      Tests  6 failed | 51 passed (57)
```

- [ ] **Step 3: Add the entry, flip the switch, add the link**

**In `frontend/src/components/settings/sections.ts`, replace:**

````ts
 * 6a-1). `/settings` opens the first. 6a-2 adds Hymns; 6a-3 Liturgy prompts,
 * Prayers and Rubric, and moves Bulletin settings in (its entry then points
 * under /settings); 5b-1 adds Contacts (the final order puts it after every
 * page about the church's services) and 5b-2 Account after it (6b's People
 * will go between them).
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
````

**with:**

````ts
 * 6a-1). `/settings` opens the first. 6a-2 adds Hymns after Church (owner's
 * 6a-2 answers of 2026-10-07); 6a-3 Liturgy prompts, Prayers and Rubric, and
 * moves Bulletin settings in (its entry then points under /settings); 5b-1
 * adds Contacts (the final order puts it after every page about the church's
 * services) and 5b-2 Account after it (6b's People will go between them).
 */
export const SETTINGS_SECTIONS = [
  { href: "/settings/church", label: "Church" },
  { href: "/settings/hymns", label: "Hymns" },
````

**In `frontend/src/lib/features.ts`, replace:**

````ts
/** Settings → Hymns (slice 6a). Until then the empty-hymnal state names the current app instead of linking. */
export const SETTINGS_HYMNS_READY = false;
````

**with:**

````ts
/** Settings → Hymns (slice 6a-2): the empty-hymnal state links to it. */
export const SETTINGS_HYMNS_READY = true;
````

**In `frontend/src/components/settings/church-settings-page.tsx`, replace:**

````tsx

import { useState, type FormEvent, type ReactNode } from "react";
````

**with:**

````tsx

import Link from "next/link";
import { useState, type FormEvent, type ReactNode } from "react";
````

**In `frontend/src/components/settings/church-settings-page.tsx`, replace:**

````tsx
            <p className="text-sm text-muted-foreground">{NO_HYMNALS}</p>
````

**with:**

````tsx
            <p className="text-sm text-muted-foreground">{NO_HYMNALS}</p>
            <AddHymnsLink />
````

**In `frontend/src/components/settings/church-settings-page.tsx`, replace:**

````tsx
function SummaryItem({ label, children }: { label: string; children: ReactNode }) {
````

**with:**

````tsx
/** Under "no hymns yet", for admins and members alike (slice 6a-2; plan review M5). */
function AddHymnsLink() {
  return (
    <Link href="/settings/hymns" className="w-fit text-sm underline underline-offset-4">
      Add hymns on the Hymns page
    </Link>
  );
}

function SummaryItem({ label, children }: { label: string; children: ReactNode }) {
````

**In `frontend/src/components/settings/church-settings-page.tsx`, replace:**

````tsx
        <SummaryItem label="Default hymnal">{hymnal ?? <span className="text-muted-foreground">{NO_HYMNALS}</span>}</SummaryItem>
````

**with:**

````tsx
        <SummaryItem label="Default hymnal">
          {hymnal ?? (
            <>
              <span className="block text-muted-foreground">{NO_HYMNALS}</span>
              <AddHymnsLink />
            </>
          )}
        </SummaryItem>
````

- [ ] **Step 4: See them pass, and the suite**

Run: `(cd frontend && npx vitest run src/components/settings/settings-layout.test.tsx src/components/settings/church-settings-page.test.tsx src/components/builder/hymns/hymns-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`
**Expected:**
```
      Tests  57 passed (57)
```
```
 Test Files  103 passed (103)
      Tests  869 passed (869)
```
```
typecheck 0
lint 0
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/settings/sections.ts frontend/src/components/settings/settings-layout.test.tsx frontend/src/lib/features.ts frontend/src/components/builder/hymns/hymns-step.test.tsx frontend/src/components/settings/church-settings-page.tsx frontend/src/components/settings/church-settings-page.test.tsx
git commit -q -m "Slice 6a-2: Hymns in the Settings nav, and the links to it" -m "The Settings sections are Church, Hymns, Bulletin, Contacts and
Account (owner's 6a-2 answer 3). SETTINGS_HYMNS_READY is true, so the
builder's empty-hymnal state links to Settings -> Hymns, and the Church
page's no-hymns line links to the Hymns page, for members too." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `869 passed` in 103 files.

## Docs, verification, the PR, the merge (T10-T12)

### Task 10: Docs: the manual check items (clarification 23)

**Files:**
- Modify: `docs/manual-verification.md`

- [ ] **Step 1: Add the items**

Under "## Slice 6a", after item 8 and before "## Slice 5b". Items 9-12 are the owner's phone check after the merge (T12), 13-15 the agent's (a member's sign-in and a test church are needed).

**In `docs/manual-verification.md`, replace:**

````markdown

## Slice 5b
````

**with:**

````markdown

**6a-2 (Hymns).** After the 6a-2 merge the owner's guided check covers the
items marked "(owner, after 6a-2)", one step at a time on the phone; the
results go into `docs/ops-runbook.md` → "Slice 6a-2 record". Any test hymn is
deleted in the same step that adds it; a hymnal is added (and then removed)
only when the church does not have it already, and a hymnal the church uses
is never removed. Record counts and what the page shows, never a church id.

- [ ] (owner, after 6a-2) **9.** **Settings** lists **Church**, **Hymns**, **Bulletin**, **Contacts** and **Account**. Tap **Hymns**: **Hymnals** lists each of the church's hymnals with its hymn count and **Default** on the default one; **Hymn library** says how many hymns there are. Search for **23**: hymn 23 and titles containing "23" are listed. Clear the search; at the end of the list **Show more** loads more hymns.
- [ ] (owner, after 6a-2) **10.** **Add hymn**: title **Test hymn**, no number, **Add hymn**: "Hymn added.". Search for it, tap it, change the title to **Test hymn 2**, **Save changes**: "Hymn updated." and the dialog says "Changes also appear in saved services that use this hymn.". Open **Builder** → **Hymns**, tap the Opening hymn's picker and type **Test hymn**: "Test hymn 2" is offered with no reload (do not choose it). Back in **Settings** → **Hymns**, **Add hymn** with the title **test hymn 2** and no number: "{hymnal} already has test hymn 2." (the default hymnal's code) shows in the dialog and nothing is added; **Cancel**. Then open "Test hymn 2", **Delete hymn**, **Delete hymn** again in "Delete “Test hymn 2”?": "Hymn deleted." and it is gone.
- [ ] (owner, after 6a-2) **11.** Only when **Add a hymnal** shows **Add** beside PH1990 (the church does not have it): **Add**: "Added PH1990 (605 hymns).", the row turns to **Added**; **Done**; PH1990 is listed with 605 hymns, and the library has the chips **All**, **GG2013** and **PH1990**. Then **Remove…** on PH1990, **Remove PH1990**: "Removed PH1990." and only the church's own hymnals are left. If PH1990 shows **Added**, the church has it already: skip this item and remove nothing.
- [ ] (owner, after 6a-2) **12.** At 375 px: no sideways scroll on **Hymns**; the five section links, the hymn rows, **Add hymn** and the search box are easy to tap. In **Edit hymn** with the iPhone keyboard open, **Save changes** can be reached and the box being typed in is not covered.
- [ ] **13.** Signed in as a plain member of the same church: **Hymns** shows "Admins can add bundled hymnals." with no **Add a hymnal** or **Remove…**; **Edit hymn** has no **Delete hymn**, and the year and familiarity are read-only ("Only admins can change this."); adding and editing a test hymn works (an admin deletes it).
- [ ] **14.** In a test church: pick a test hymn in the builder, then delete it in **Settings** → **Hymns**: the builder's slot shows "Not in your hymnal. Choose a replacement." with no reload.
- [ ] **15.** As an admin, set a hymn's "Year the words were written" to a year after the rubric's preferred year: the builder's picker labels it as newer with no reload.

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
 1 file changed, 15 insertions(+)
```

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md
git commit -q -m "Docs: slice 6a-2 manual checks" -m "docs/manual-verification.md, under Slice 6a, gains the 6a-2 items: the
owner's phone check after the merge (finding Hymns, a test hymn added,
renamed, seen in the builder, refused as a duplicate of itself and
deleted, PH1990
added and removed only if the church does not have it, the page at
375 px and the edit sheet with the keyboard open) and the agent's
checks (a member, a picked hymn deleted, a year)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `869 passed` in 103 files.


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
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error|/settings")
```

**Expected** (as in the replay: the suite; three runs of `Test Files  103 passed (103)` and `Tests  869 passed (869)` with no `×` or `FAIL` line, one naming a failing test: Step 6; typecheck and lint 0; the build with `/settings/hymns` and no `Error`, a font `Failed to fetch` only: say so and rely on CI):
```
1883 passed, 31 skipped in <t>s
```
```
 Test Files  103 passed (103)
      Tests  869 passed (869)
 Test Files  103 passed (103)
      Tests  869 passed (869)
 Test Files  103 passed (103)
      Tests  869 passed (869)
```
```
typecheck 0
lint 0
```
```
✓ Compiled successfully in <t>s
├ ○ /settings
├ ○ /settings/account
├ ○ /settings/church
├ ○ /settings/contacts
├ ○ /settings/hymns
```

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/hymnal_sources.py backend/usecases/hymn_library.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff origin/main...HEAD -- backend frontend/src | grep '^+' | grep -c '—'
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json backend/requirements.txt requirements-dev.txt app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; `0` (no em dash in an added line of code or tests); exactly these 42 paths (the 5b-2b record in the runbook and the 6a spec's amendment ride along until merged):
```
M	backend/api/routes/hymnals.py
M	backend/api/routes/hymns.py
A	backend/hymnal_sources.py
M	backend/import_hymnal.py
M	backend/repos/hymns.py
M	backend/tests/test_api_hymnals.py
A	backend/tests/test_api_hymnals_admin.py
A	backend/tests/test_api_hymns_admin.py
A	backend/tests/test_hymn_library.py
A	backend/tests/test_hymn_library_postgres.py
A	backend/tests/test_hymnal_sources.py
M	backend/tests/test_hymns_repo.py
A	backend/tests/test_import_hymnal_cli.py
M	backend/tests/test_no_streamlit_in_core.py
A	backend/usecases/hymn_library.py
A	data/.gitkeep
R100	data/hymnals/PH1990_hymns.csv	backend/seed/hymnals/PH1990.csv
M	docs/manual-verification.md
M	docs/ops-runbook.md
A	docs/superpowers/plans/2026-10-07-slice-6a2-hymns.md
M	docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md
A	frontend/src/app/(signed-in)/(church)/settings/hymns/page.tsx
M	frontend/src/components/builder/hymns/hymns-step.test.tsx
M	frontend/src/components/settings/church-settings-page.test.tsx
M	frontend/src/components/settings/church-settings-page.tsx
A	frontend/src/components/settings/hymn-dialog.tsx
A	frontend/src/components/settings/hymn-library.test.tsx
A	frontend/src/components/settings/hymn-library.tsx
A	frontend/src/components/settings/hymnals-card.tsx
A	frontend/src/components/settings/hymns-settings-page.test.tsx
A	frontend/src/components/settings/hymns-settings-page.tsx
M	frontend/src/components/settings/sections.ts
M	frontend/src/components/settings/settings-layout.test.tsx
M	frontend/src/lib/api/openapi.json
M	frontend/src/lib/api/schema.d.ts
M	frontend/src/lib/api/timeouts.ts
M	frontend/src/lib/api/types.ts
M	frontend/src/lib/features.ts
A	frontend/src/lib/queries/hymn-library.ts
A	frontend/src/lib/settings/hymns.test.ts
A	frontend/src/lib/settings/hymns.ts
M	frontend/src/test/fixtures/index.ts
```
`0`; the subjects oldest first: `Runbook: slice 5b-2b record (merged; owner's phone check)`, `Spec: slice 6a-2 (Hymns) planning answers (owner, 2026-10-07)`, the plan commits (`WIP plan: …` and `Plan: slice 6a-2 (Hymns in Settings)`) and any later plan commit, then T1-T10's ten subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** `[]`. Send the owner exactly this, and wait for a clear yes:

> The Hymns page (slice 6a-2) is verified on this machine: backend 1883 passed, 31 skipped (1825 and 27 before); frontend 869 tests in 103 files (835 before), three runs in a row; typecheck, lint and the production build are clean. It adds the hymn and hymnal routes, no database change and no new package. Settings gets **Hymns** after **Church**: everyone sees the church's hymnals and hymns, searches them, and adds and edits hymns; you (and any admin) also delete a hymn, set its year and familiarity, add a bundled hymnal and remove one that is neither your only nor your default hymnal. The builder's hymn list follows every change without a reload. The pull request also carries the 5b-2b record and today's 6a-2 planning notes. May I open the pull request as a **draft** titled "Slice 6a-2: Hymns in Settings", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/6a2-pr-body.md" <<'BODY'
Slice 6a-2: Hymns in Settings (the second of slice 6a's three PRs; owner's 6a-2 planning answers of 2026-10-07). Spec: docs/superpowers/specs/2026-09-25-slice-6a-settings-church-design.md (UX §2 and its amendments). Plan: docs/superpowers/plans/2026-10-07-slice-6a2-hymns.md. No database change, no new package or variable.

- The bundled PH1990 CSV moves to backend/seed/hymnals/PH1990.csv; hymnal_sources lists the bundled and catalog hymnals; import_hymnal.py needs --csv only for other hymnals.
- repos/hymns: one duplicate key (the title's words), an import that flushes once and fills only blanks, get_hymn, create_hymn, patch_hymn, find_duplicate, delete_hymnal.
- usecases/hymn_library and the routes: POST and PATCH /hymns (any member; the year and familiarity are an admin's), DELETE /hymns/{id}, GET /hymnal-sources, POST /hymnals and DELETE /hymnals/{code} (owners and admins; never the only or the default hymnal); each write under the church-row lock with the caller's role re-read (Postgres tests); GET /hymnals gains label.
- Settings → Hymns: the Hymnals card (add a bundled hymnal, remove one) and the Hymn library (search, chips, Show more, add, edit, delete), every change refreshing the builder's hymn list. The Settings nav: Church, Hymns, Bulletin, Contacts, Account. The builder's empty-hymnal state and the Church page link to Hymns.
- docs/manual-verification.md: the 6a-2 items under "Slice 6a".
- Rides along: the 5b-2b record in docs/ops-runbook.md and the 6a spec's amendment of 2026-10-07.

Later: 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), 6b (People), a possible "Fill from Hymnary.org".

Tests: backend 1825 → 1883 passed, 27 → 31 skipped; frontend 835 → 869 in 100 → 103 files

After merge (Task 12): a short check on the owner's phone, then a "Slice 6a-2 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Slice 6a-2: Hymns in Settings" \
  --body-file "<scratch>/6a2-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1883 passed, 31 skipped`, backend-postgres `31 passed, 1883 deselected`, frontend `869 passed` in 103 files. Then send: "PR #<N> is green: backend 1883 passed, 31 skipped (the four new Postgres tests passed in their own job, the 605-hymn add under 10 s among them); 869 frontend tests in 103 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_hymnal_sources.py`, `test_import_hymnal_cli.py`, `test_no_streamlit_in_core.py` (`hymnal_sources`) | T1 |
| `test_hymns_repo.py`, `test_hymnals.py`, `test_hymnary_facts.py`, `streamlit_tests/` | T2 |
| `test_hymn_library.py`, `test_no_streamlit_in_core.py` (`usecases.hymn_library`) | T3 |
| `test_api_hymns_admin.py`, `test_api_hymnals_admin.py`, `test_api_hymnals.py`, `test_openapi_contract.py`, `test_route_guards.py` | T4 |
| `test_hymn_library_postgres.py` (CI `backend-postgres`) | T5 (the lock itself: T3) |
| `hymns.test.ts`, `typecheck` in `lib/queries/hymn-library.ts` | T6 |
| `hymns-settings-page.test.tsx` | T7 |
| `hymn-library.test.tsx` | T8 |
| `settings-layout.test.tsx`, `church-settings-page.test.tsx`, `hymns-step.test.tsx` | T9 |
| `test_slice1_docs.py`, `test_docs.py` | T10 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, slice 6a-2 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1883 passed, 31 skipped`; frontend `869 passed` in 103 files.

### Task 12: Merge, the owner's phone check (four steps), the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0007_bulletin_images`); Railway serves the new routes and the bundled CSV, Vercel the page. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church, signed in as its owner. **Any test hymn the check adds is deleted in the same step. PH1990 is added (and then removed) only when the church does not have it already; a hymnal the church uses is never removed, and no real hymn is edited or retyped (the duplicate is tried on the test hymn itself).** The agent writes each result into `<scratch>/6a2-t12-results.md` (not committed). Record counts and what the page showed, never a church id or an email address.

**Files:** Modify (the records PR, Step 8): `docs/ops-runbook.md`: insert `### Slice 6a-2 record` right before `## Backups` (after the last record above it, today `### Slice 5b-2b record`, whose table's last row starts `| Follow-ups |`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (slice 6a-2: Hymns in Settings) is ready, green and up to date with main. There is no database change; your hymns stay exactly as they are until someone edits them. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway and Vercel before Step 2; a failed deploy keeps the old version running (Step R).

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 4: finding Hymns (manual-verification item 9)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it. Tap **Settings** at the top: are the sections **Church**, **Hymns**, **Bulletin**, **Contacts** and **Account**? Tap **Hymns**. Under **Hymnals**, which hymnals are listed, with how many hymns each, and which one says **Default**? Under **Hymn library**, how many hymns does it say? Type **23** in the search box: is hymn number 23 listed (with any titles containing "23")? Tap the × to clear the search, scroll to the end of the list and tap **Show more**: do more hymns appear? Please answer with the codes and numbers only.

Record the codes, counts and answers. **Whether PH1990 is listed decides Step 4.**

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 4: a test hymn, from add to delete (item 10)**

> Tap **Add hymn**. Type the title **Test hymn**, leave the number empty, and tap **Add hymn**: does it say "Hymn added."? Search for **Test hymn** and tap it: the box says "Edit hymn" and "Changes also appear in saved services that use this hymn." Change the title to **Test hymn 2** and tap **Save changes**: "Hymn updated."? Now open **Builder**, go to **Hymns**, tap the **Opening** hymn's box and type **Test hymn**: is "Test hymn 2" offered (without reloading)? Do not choose it; tap away. Back in **Settings** → **Hymns**, tap **Add hymn**, type the title **test hymn 2** in small letters, leave the number empty, and tap **Add hymn**: does the box say "… already has test hymn 2." (with your hymnal's code in front) and stay open? Tap **Cancel** (nothing is added). Last, search for **Test hymn**, tap "Test hymn 2", tap **Delete hymn** and then **Delete hymn** in "Delete “Test hymn 2”?": does it say "Hymn deleted." and is it gone from the list? (If the second add said "Hymn added." instead, there are two test hymns: delete both the same way.)

The duplicate is tried only on the test hymn, never by retyping one of the church's own hymns. If a test hymn could not be deleted, stop and help the owner delete it before going on (an admin's **Delete hymn**; it is in no saved service). Record the six answers.

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 4: adding and removing a hymnal, only if safe (item 11)**

Only when Step 2 did **not** list PH1990:

> Tap **Add a hymnal**. Next to **PH1990** (The Presbyterian Hymnal (1990), 605 hymns, with a note that it has no scripture references), tap **Add**: does it say "Added PH1990 (605 hymns)." and does the button turn to **Added**? (It can take a few seconds.) Tap **Done**: is PH1990 listed with 605 hymns, and does the library now show the buttons **All**, your hymnal and **PH1990** above the list? Now tap **Remove…** next to PH1990: the box asks "Remove PH1990?". Tap **Remove PH1990**: does it say "Removed PH1990." and is only your own hymnal left? (If PH1990 shows **Default** after it was added, so it has no **Remove…**, first open **Church**, set **Default hymnal** back to your own hymnal and tap **Save profile**, then come back and remove PH1990.)

Record whether the owner had to set the default hymnal back in **Church** before removing PH1990 (and to which code), and that **Default** is on the church's own hymnal again at the end (plan review M7).

When Step 2 listed PH1990 (the church has it): **skip this step**, send "Your church already has PH1990, so we skip adding and removing a hymnal (nothing is removed).", and record "Skipped: the church has PH1990". Never remove a hymnal the church had before this check. If the add took long, record roughly how long (S Risk 5).

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 4: the phone screen (item 12)**

> On **Settings** → **Hymns**: is the page easy to use on the phone, with no sideways scrolling, and are the five section links, the hymn rows, **Add hymn** and the search box easy to tap? Then tap any hymn and tap in its **Title** box so the keyboard opens: can you still see and tap **Save changes**, and is the box you are typing in visible above the keyboard? Tap **Cancel** (nothing is changed).

- [ ] **Step 6 (agent): The agent's own checks (items 13-15)**

On the production URL, in a test church the agent may change (one of the two slice 1 test churches the owner kept, never the owner's own church), signed in as its owner if the session has a test account, else skipped and recorded as "not run": item 14 (a picked test hymn deleted: "Not in your hymnal. Choose a replacement."; the test hymn is deleted) and item 15 (a test hymn's year set, then the hymn deleted). Item 13 needs a plain member's sign-in; record "not run" unless the owner offers one.

- [ ] **Step 7 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/6a2-t12-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it, `### Slice 5b-2b record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Slice 6a-2 record

Slice 6a-2 (Hymns in Settings: Hymns in the Settings sections after
Church; every member reads the church's hymnals and hymns, searches them,
and adds and edits hymns; owners and admins delete hymns, set a hymn's year
and familiarity, add a bundled hymnal and remove one that is neither the
only nor the default; `POST`, `PATCH` and `DELETE /hymns`, `GET
/hymnal-sources`, `POST /hymnals` and `DELETE /hymnals/{code}`, each write
under the church-row lock with the caller's role re-read; the PH1990 CSV
moved under `backend/`) merged as PR #<N>, the second of slice 6a's three
PRs (owner's 6a-2 planning answers of 2026-10-07). No database change and
no new package; production stays at `0007_bulletin_images`. The owner's
check was four steps on a phone, covering the "(owner, after 6a-2)" items
of `docs/manual-verification.md` → "Slice 6a". The test hymn was deleted in
the step that added it; PH1990 was added and removed only if the church did
not have it. Accepted risk (owner's answer 5): recent use is kept by title
and number, so a hymn renamed or renumbered in Settings no longer matches its
past uses and may be suggested again within 12 weeks; a later fix keys use by
hymn id. Noted (not refused): deleting, or moving to another hymnal, the last
hymn of the default hymnal makes another hymnal the default without a
warning (the builder then opens with the first of the others by code), and
adding a bundled hymnal again after one of its hymns was renamed adds the
bundled title back as a second hymn. No church id or email address is
recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main`: backend, backend-postgres and frontend success | <date> |
| 1. Finding Hymns (phone: <phone and browser>) | <Church, Hymns, Bulletin, Contacts and Account listed; hymnals <codes with counts>, default <code>; <n> hymns; search 23 <result>; Show more <result>. / …> | <date> |
| 2. A test hymn | <Added, renamed, offered in the builder's picker with no reload; a second "test hymn 2" refused in the dialog ("<code> already has test hymn 2."), nothing added; deleted (gone from the list). / …> | <date> |
| 3. A hymnal | <PH1990 added (605 hymns, about <n> s), shown with the chips, removed; only the church's own hymnal left. The default had to be set back to <code> in Church before the removal: <yes / no>; **Default** on <code> at the end. / Skipped: the church has PH1990.> | <date> |
| 4. The phone | <No sideways scroll, easy to tap; Edit hymn usable with the keyboard open (Save changes reachable, the box not covered). / …> | <date> |
| Agent checks | <Items 14 and 15 in a test church: <results>. / Not run: <why>.> Item 13 (a member): <result / not run> | <date> |
| Follow-ups | <None. / One line per follow-up.> Accepted: renamed hymns and the 12-week rule (above). Noted: the default hymnal changing silently when its last hymn goes, and a renamed bundled hymn coming back on a re-add (above). Possible: "Fill from Hymnary.org" (answer 6). Next: 6a-3 (Liturgy prompts, Prayers, Rubric, Bulletin settings moved in), 6b (People), Hear it from the pews | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Read the record once by eye. Then (not replayed):

```bash
sed -n '/^### Slice 6a-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Slice 6a-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
sed -n '/^### Slice 6a-2 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '—'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: slice 6a-2 record (merged; owner's phone check)" -m "Records slice 6a-2 (PR #<N>): the merge and CI on main, the owner's
four-step phone check (finding Hymns, a test hymn added and deleted, a
hymnal added and removed only if the church did not have it, the phone
screen) and the accepted renamed-hymn risk. No church id or email address
is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `4`; `89 passed in <t>s`; one commit.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The slice 6a-2 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: slice 6a-2 record" \
  --body "Records slice 6a-2 (PR #<N>) in docs/ops-runbook.md → Slice 6a-2 record: the merge, the owner's four-step phone check and the accepted renamed-hymn risk. No church id or email address is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Slice 6a-2 is live and recorded; <n> follow-ups. Next: 6a-3's planning, or 6b, in the order you pick."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no schema to undo). On the owner's yes for each outward command: a branch `claude/revert-6a2` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert slice 6a-2 (PR #<N>)" with the trailer, both suites (`1825 passed, 27 skipped`; `835 passed` in 100), a PR, CI, and the merge on the owner's yes; record it in the record. Hymns added, edited or deleted through the page stay as they are in the `hymns` table (the old app could make the same changes), and the CSV goes back to `data/hymnals/`, so nothing needs undoing in the data.

Expected counts after this task: backend `1883 passed, 31 skipped` on `main`; frontend `869 passed` in 103 files. The records PR adds no test.

---

## Build notes

**How this plan was written (2026-10-07).** Each task's code was built and run in a throwaway worktree of `1534767` (the branch head `446eaa3` plus the plan's skeleton commit; the repo's `.venv` as a symlink; a hard-linked copy of `frontend/node_modules`, since Turbopack's production build refuses a `node_modules` symlink that points outside the project), one commit per task; the directives were then generated from those commits (a new file as **Create**, a rewritten one as **Replace**, an addition at the end of a file as **Append**, every other change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point, changes three or fewer lines apart in one block) and checked by applying each to the file before the commit and comparing with the file after it. No package, variable or migration was added. While building:
- **What S assumed and what exists.** S's `get_hymn`, hymn write routes, hymnal routes, `hymnal_sources.py` and `usecases/hymn_library.py` were never built; S's `HymnOut` (with `themes`, not the stored theme), `GET /hymns`' `q` rule and `hymnal_summaries` are slice 3's as S assumed; 6a-1 built the lock helpers and the Settings shell. `keys.hymnalSources` was already in `keys.ts`. The `import_hymns` S calls "idempotent … fills missing enrichment only" in fact overwrote any differing value and flushed per row (clarification 17). No table points at `hymns`, so deleting needs no other change.
- **The empty `data/hymnals` folder.** `git mv` leaves the emptied folder on disk, and `test_the_bundled_ph1990_ships_under_backend_and_loads_605_rows` checks it is gone, so T1 Step 3 removes it (`rmdir data/hymnals`); a fresh checkout never has it. `data/` itself stays, kept by an empty `data/.gitkeep` (plan review I1), since the local SQLite database lives there.
- **The library in T7's tests.** T8 puts the library on the page, which reads `GET /hymns`; T7's page test answers it from the start (an empty page), so T8 does not edit it.
- **Lint.** React's lint refuses a `setState` called directly in an effect; the "still working" flag is reset when an add starts and shown only while the add is pending.
- **Mutation checks** (each change made by hand in a worktree with every directive applied, the named tests run, the change undone; rerun after the plan review fixes): the role check for the facts dropped from `update_hymn` → `3 failed, 39 passed` (`test_hymn_library.py` and `test_api_hymns_admin.py`); `find_duplicate` ignoring `exclude_id` → `1 failed, 61 passed` (the repo, usecase and API tests); the import overwriting differing values again → `1 failed, 22 passed` (`test_hymns_repo.py`, `test_hymnals.py`); `refreshHymns` without the `["church", id, "hymns"]` prefix → `4 failed, 21 passed` (the two page test files); **Delete hymn** shown to members → `1 failed, 12 passed` (`hymn-library.test.tsx`). The review fixes, each undone alone: the blank-title guard (M8) → `1 failed, 27 passed` (`test_hymn_library.py`); a hymnal write refreshing only after a 404 or 409 again (I3) → `1 failed, 11 passed` (`hymns-settings-page.test.tsx`), and likewise the "already added" toast (I3), the 404 focus (M1), the singular body (M2) and `REMOVABLE_CODE` (M4), each `1 failed, 11 passed`; the member's link (M5) → `1 failed, 12 passed` (`church-settings-page.test.tsx`); `POST /hymnals` back at 30 s → `1 failed, 6 passed` (`hymns.test.ts`).
- **The lock on Postgres.** On a throwaway local PG 16 cluster (initialised under `/var/lib/postgresql`, port 5441, never a real database, stopped and deleted afterwards; `TEST_DATABASE_URL=postgresql://postgres@localhost:5441/church_test`): `test_hymn_library_postgres.py` `4 passed`. With `lock_church`'s `with_for_update=True` turned off, three fail (the held-lock test, the barrier test and the two PH1990 adds) and the timing test passes. All Postgres-marked tests on that cluster, at the end of the final replay below: `31 passed, 1882 deselected, 1 warning` (CI's `backend-postgres` job runs the same set). After the plan review fixes, on a new throwaway cluster the same way (port 5441, stopped and deleted afterwards), with every directive applied: `test_hymn_library_postgres.py` `4 passed`, the same three failing with `with_for_update=False`, and all Postgres-marked tests `31 passed, 1883 deselected, 1 warning`.
- **The production build** compiled with `○ /settings/hymns` beside the other Settings routes.

**Replay of the finished plan (2026-10-07, after the plan review fixes).** The directives of T1-T10 were applied in order by a replay script that parses each step's **Create**, **Replace**, **Append** and **In … replace** blocks and its `bash` blocks (T1's move, each commit), and runs every command on its "Run:" lines, onto a fresh detached worktree of the branch at the plan's commit `d2c23a9` (the review fixes' code; the later plan commits change only expected outputs and prose), outside the repo directory and removed afterwards, with the repo's `.venv` (a symlink) and a hard-linked copy of `frontend/node_modules`:
- All 51 directives applied (T1 3 + 2, T2 1 + 4, T3 2 + 1, T4 3 + 5, T5 1, T6 1 + 6, T7 1 + 3, T8 1 + 4, T9 6 + 6, T10 1); every **In … replace** anchor occurred exactly once; T1's move (with `data/.gitkeep`) and all ten commit blocks ran, each commit with the trailer (T1's staging `data/.gitkeep`); afterwards the replayed `backend` and `frontend/src` trees were identical to a second worktree with the same directives applied, where the mutation checks above were run.
- Baselines before T1: backend `1825 passed, 27 skipped`; frontend `835 passed` in 100 files; typecheck 0, lint 0.
- Every "see it fail" output and every count above is quoted from this replay (times as `<t>`, Vitest's per-test times left out).
- Every count matched the table: backend 1832, 1837, 1865, 1883 passed with 27 skipped, then 31 skipped from T5; frontend 842 in 101, 854 in 102, 867 in 103, 869 in 103; T1 Step 4 `13 passed`; T2 Step 4 `93 passed` and `streamlit_tests` `35 passed`; T3 Step 4 `31 passed`; T4 Step 4 ` 2 files changed, 1933 insertions(+), 221 deletions(-)` and `33 passed`; T7's and T8's three runs `12 passed` and `13 passed` each time, no flaky run; T9 `6 failed | 51 passed (57)` then `57 passed`; typecheck 0 and lint 0 after T4, T6, T7, T8 and T9; T10 `89 passed`, `4`, `0`, ` 1 file changed, 15 insertions(+)`. After T10, T11 Step 2's and Step 3's outputs (quoted there): `1883 passed, 31 skipped`, three runs of `869 passed` in 103 files, typecheck and lint 0, `✓ Compiled successfully` with `○ /settings/hymns`, and the 42 paths. The replays before the review (at `5abe882`, and an earlier one) gave the outputs the plan then quoted (`1882` and `863`).
- Not run while planning: the pushes, the PR and CI, the merge, Railway's and Vercel's deploys and the owner's phone check (T12).

## Spec coverage

| Owner answer or spec item | Task(s) and tests |
|---|---|
| Answer 1: the Hymnals card (counts, admin-only Add a hymnal and Remove…) | T7 "shows a member the hymnals…", "gives an admin Remove on every hymnal but the default…", "lets an admin add PH1990…", "asks before removing a hymnal…"; T3 `test_adding_ph1990_inserts_605_once…`, `test_removing_a_hymnal_deletes_only_its_hymns_but_never_the_only_or_the_default`; T4 `test_an_admin_adds_ph1990_once_and_removes_it` |
| Answer 1: the Hymn library (search, hymnal filter, add, edit, admin-only delete, pages of 50 with Show more) | T8 every test; T4 `test_a_member_adds_and_edits_a_hymn_and_it_is_listed`, `test_only_admins_delete_a_hymn_or_send_its_year_or_familiarity` |
| Answer 2: one PR | T11 (one draft PR) |
| Answer 3: Church, Hymns, Bulletin, Contacts, Account | T9 `settings-layout.test.tsx` |
| Answer 4: edits reach saved services; the edit dialog's note | T8 "lists the hymns… a member edits one…" (the note), "adds a hymn…" (no note in Add); clarification 19 |
| Answer 5: the renamed-hymn / 12-week risk accepted and recorded | Risks; T12 Step 8 (the record's paragraph and its Follow-ups row) |
| Answer 6: no "Fill from Hymnary.org" | Out of scope; Follow-ups |
| Only admins delete hymns (2026-10-05) | T3 `test_only_admins_delete_a_hymn…`; T4 `test_only_admins_delete…`; T8 the member test (no **Delete hymn**) |
| Removing a hymnal, never the only or the default (2026-10-05) | T3 `test_removing_a_hymnal…`; T4 `test_the_errors_of_adding_and_removing`; T7 the default row and the refused removal |
| The year and familiarity, admin-only (2026-09-26) | T3 `test_an_admin_sets_the_year_and_familiarity_and_a_member_may_not`, `test_a_member_may_not_send_the_year_or_familiarity_even_as_null`, `test_a_hand_entered_year_survives_the_backfill`; T4; T6 `newHymnBody`/`hymnPatch`; T8 the member and admin tests |
| S API rows and models (`POST` 201, `PATCH` only what is sent, `DELETE` `{deleted: true}`, the hymnal routes, `label`, `extra="forbid"`, the path pattern) | T4 all tests; `test_api_hymnals.py`; `test_openapi_contract.py`, `test_route_guards.py` |
| S error contract (every message and field, an omitted title, a non-whole number, malformed and unknown ids) | T3 `test_a_bad_field_is_named_and_nothing_is_added`; T4 `test_a_bad_field_is_a_422_naming_it`, `test_unknown_fields_and_malformed_or_unknown_ids`, `test_the_errors_of_adding_and_removing` |
| S duplicate rule and its message (both variants), excluding self | T2 `test_find_duplicate_compares_the_number_and_the_titles_words_in_one_hymnal`; T3 `test_the_same_hymnal_number_and_title_words_is_a_409`, `test_an_edit_checks_its_fields_the_hymnal_and_duplicates_but_not_itself`; T4 `test_the_same_hymn_twice_is_a_409`; T8 the 409 in the dialog |
| S Semantics → POST /hymns hymnal default (stored, alphabetical, GG2013 with none, any code with none) | T3 `test_the_hymnal_defaults_to_the_effective_one_and_a_church_with_none_may_name_one`; T8 the add body (`hymnal: "GG2013"`) |
| S Semantics → PATCH merges, keeps `audio_url`, null clears | T2 `test_create_get_and_patch_are_church_scoped_and_keep_what_is_not_sent`; T3 `test_an_edit_changes_only_what_is_sent_and_null_clears` |
| S Semantics → Locking (the lock, the role re-read, `no_church_access`) | T3 `test_a_member_a_demoted_admin_or_a_removed_member_writes_nothing`, `test_each_write_reads_the_church_row_under_its_lock`; T5 |
| S Postgres: concurrent identical hymns, concurrent PH1990, 605 rows under 10 s | T5 (CI `backend-postgres`) |
| S `hymnal_sources.py`, the seed file under `backend/`, BOM, links, `has_scripture_refs`, `KeyError`, catalog merge | T1 `test_hymnal_sources.py` |
| S `import_hymns` idempotency kept after the flush removal; fills missing only | T2 `test_an_import_adds_once…`, `test_an_import_flushes_once_in_the_callers_session`; `test_hymnals.py` unchanged |
| S `import_hymnal.py` (no `--csv` for a bundled hymnal, no `.env` at import) | T1 `test_import_hymnal_cli.py` |
| S `assert_church_isolated` on every route; another church's hymnal code untouched | T4 `test_hymn_writes_are_isolated_between_churches`, `test_hymnal_routes_are_isolated_between_churches` |
| S Queries: the library's infinite query; writes invalidate `hymns`, `hymnals`, `hymnal-sources`, `profile`; the builder's picker without a reload (acceptance 14) | T6 `lib/queries/hymn-library.ts`; T7 "lets an admin add PH1990…" (the four keys); T8 "adds a hymn…", "asks before an admin deletes a hymn… marks the builder's lists stale…" |
| S UX §2 DOM cases (count, rows, search with debounce and offset, Show more, chips, add, edit only changed fields, the facts, delete confirmed, 409 in the dialog, Add a hymnal for admins only, PH1990 note, Added, no Remove on the default) | T7, T8 |
| The 5b-1 lessons: whitespace and case in the duplicate check; focus after a 404; dialogs not closable mid-request; late answers; bottom sheets with the keyboard; a 422 with no known field toasted | T2/T3 (`title_key`); T8 "closes the edit dialog when the hymn was deleted elsewhere…", "keeps the dialog open while a save runs"; T7 "keeps the add dialog open…"; clarifications 8, 10; T12 Step 5 |
| Hand-offs: `SETTINGS_HYMNS_READY`; the Church page's link | T9 `hymns-step.test.tsx`, `church-settings-page.test.tsx` |
| A guided phone check after the PR | T12 Steps 2-5; `docs/manual-verification.md` items 9-15 (T10) |
| The plan review fixes (I1-I3, M1-M8) | T1 `test_the_bundled_ph1990_ships_under_backend_and_loads_605_rows` (`data/.gitkeep`); T3 `test_an_edit_of_an_old_hymn_with_a_blank_title_is_never_a_duplicate`; T6 the 60 s timeout; T7 "says a hymnal is already added…", "toasts a failed add and refreshes every list…", "moves focus to Add a hymnal when the hymnal was already removed elsewhere (404)", "words the removal of a one-hymn hymnal in the singular…", "offers no Remove for a hymnal whose code the removal route cannot take"; T9 the member's link; Risks; T10 item 10 and T12 Steps 3, 4 and 8 |

S items **not** in 6a-2: Liturgy prompts, Prayers, Rubric and Bulletin settings moved in (6a-3); People and Danger zone (6b); S's `rebaseForm` and leave guard for the hymn dialog (clarification 24); S's Streamlit compatibility notes and manual check 10 (Streamlit retired); keying recent use by hymn id (answer 5, later).

## Follow-ups (not in 6a-2)

- "Fill from Hymnary.org" in the hymn dialog (answer 6), reusing `hymnary_facts.find_facts` outside the church-row lock.
- Recent use keyed by hymn id, so a renamed hymn keeps its 12-week history (answer 5; a schema change).
- A draft's pick of a hymn moved to another hymnal could follow it (look the id up in every hymnal's list) instead of asking for a replacement.
- If the five section links wrap awkwardly on a phone, a horizontal scroller for the Settings nav (the 6a-1 and 5b-1 follow-up, carried).
- Choosing another church in the church menu still does not ask before discarding unsaved settings edits (6a-1 follow-up, carried).

## Owner questions

Your 6a-2 planning answers of 2026-10-07 (the six, all as recommended) and the earlier answers on hymns are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **Pasted line breaks in a hymn's title, references or themes** (clarification 11). Recommended: the app quietly tidies them: a line break, a tab or an invisible control character becomes a space, and repeated spaces become one, so a title copied from a website saves as one clean line. (The other choice: refuse it with a message such as "Hymn title can't contain line breaks or control characters.", as contact names do.)
2. **A link with a space in it** (clarification 11). Recommended: refuse it with "Links can't contain spaces." (a link with a space never opens). Links must still start with https://, as the spec says.
3. **A short line under the page title** (clarification 3): "The hymnals and hymns the builder offers when you choose hymns." Recommended: accept.
4. **The library's caption** (clarification 7): "Anyone in your church can add and edit hymns. Only admins can delete them." (the spec's line was written before you decided only admins delete). Recommended: accept.
5. **Adding a hymnal your church already has** (clarification 17). Recommended: it adds only the hymns you are missing and fills in only details that are blank, so your own changes to its hymns (a corrected link, added scripture references) are kept. (The old import tool overwrote them with the bundled values.)
6. **What a member sees for the year and familiarity** (clarification 8). Recommended: both fields are shown but cannot be changed, with "Only admins can change this." under each; a member's save never sends them.
7. **The hymn box on a phone** (clarification 8). Recommended: it slides up from the bottom and scrolls, like **Edit contact**, so **Save changes** stays reachable with the keyboard open, rather than filling the whole screen.
8. **A hymn with no number in the list** (clarification 7). Recommended: just its title (the spec showed a dash, which the no-em-dash rule rules out); such hymns come last in their hymnal, and search finds them.
9. **A link from the Church page** (clarification 20). When your church has no hymns, the Church page's "Your church has no hymns yet, so there is no default hymnal." gets "Add hymns on the Hymns page" under it. Recommended: accept.
10. **The note in Add a hymnal** (clarification 5): "This hymnal has no scripture references, so “Hymns for the readings” and AI suggestions work less well with it." (the spec said "Find hymns"; the builder's button is called "Hymns for the readings"). Recommended: accept.
11. **Moving a hymn to another hymnal** (clarifications 13, 19). Recommended: allowed in **Edit hymn** (as the spec says); a service in progress that had picked that hymn then asks you to choose it again, as if it were deleted. It only matters once your church has two hymnals.
12. **No database rule for duplicates** (clarification 21). Recommended: keep the app's own check (the same hymnal, number and title, in any capitals or spacing, refused even when two people add it at the same moment), with no database change. A database rule would need a migration that fails if your hymnal already has two copies of a hymn differing only in spacing or capitals, which the old app allowed.
13. **The wording** (clarification 22): every new line on the page and in the dialogs, as listed there, including two lines added after the plan's review: "{code} is already added." (when adding a hymnal brings nothing new, for example because it was just added in another tab) and, for a hymnal with a single hymn, "This deletes the 1 hymn in {code} from your church's hymnal, …" instead of "This deletes all 1 hymns …". Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T11); the merge on your yes, then four phone checks one at a time (the test hymn deleted in the same step; PH1990 added and removed only if your church does not have it), and the records PR (T12).

## Plan review fixes (2026-10-07)

Each finding of the plan's review, and what changed. Every changed directive was replayed with the rest (Build notes); the counts and outputs above are that replay's.

- **I1 (T1 Step 3: `data/` must stay).** The README and `backend/.env.example` use `sqlite:///../data/app.db` and `db/engine.py` falls back to `sqlite:///data/church.db`, so T1 Step 3 now runs only `rmdir data/hymnals` and adds an empty `data/.gitkeep` (staged in T1's commit); `test_the_bundled_ph1990_ships_under_backend_and_loads_605_rows` also checks `data/.gitkeep` is there. Clarification 16, the directive rules, File Structure (42 paths: 20 added), T11 Step 3's list (`A	data/.gitkeep`) and the Build notes say so.
- **I2 (T12 Step 3, manual item 10: the duplicate tried on a real hymn).** The duplicate is now tried on the test hymn itself, before it is deleted: after the rename to **Test hymn 2**, **Add hymn** with the title **test hymn 2** and no number shows "{hymnal} already has test hymn 2." (`duplicate_message` with no number, the title as sent) and adds nothing; **Cancel**; then the test hymn is deleted. The owner is never asked to retype one of the church's hymns (T12's opening rule says so too); the record template's row 2 follows the new order.
- **I3 (the hymnal add's timeout, its failures and an add that brings nothing).** `POST /hymnals` now waits 60 s (`timeouts.ts`), so "Still working. This can take up to a minute." is true. The server side is fine with that: uvicorn sets no request deadline, the app sets no `statement_timeout` outside migrations, and routes behind Railway already answer later (`POST /liturgy/generate`, an 80 s deadline). `useHymnWrite` now refreshes every hymn list, the hymnals, the sources and the profile after **any** failure of a hymnal write except a 401 or a lost church (a timed-out add may have finished on the server). `AddHymnalDialog` toasts "{code} is already added." when `inserted + updated === 0`. Tests: T6's timeout case (60 000), T7 "says a hymnal is already added when the add brings nothing new" and "toasts a failed add and refreshes every list, since the add may have finished on the server" (the fake server adds PH1990 and answers 500; the row turns to **Added** and the card shows two hymnals). Clarifications 5, 10 and 22 and owner question 13 carry the new line.
- **M1 (T7: a removal answered 404).** The removal's `onError` marks the hymnal removed on a 404, so focus goes to **Add a hymnal** (its row is gone after the refresh). Test: T7 "moves focus to Add a hymnal when the hymnal was already removed elsewhere (404)". Clarification 6.
- **M2 (T7: one hymn).** `removeBody` says "This deletes the 1 hymn in {code} …" for a hymnal with one hymn. Test: T7 "words the removal of a one-hymn hymnal in the singular, and says one outside the bundled list can't come back" (which also covers the not-bundled ending). Clarifications 6 and 22, owner question 13.
- **M3 (Risks: the default hymnal changing silently).** Noted, not refused (refusing needs a count on every hymn write and a new message): a Risks entry, and the record's paragraph and Follow-ups row (T12 Step 8). No code change.
- **M4 (T4/T7: codes the route cannot take).** Hidden, not widened: a hymnal whose code does not match `^[A-Za-z0-9_-]{2,20}$` (made only by the ops CLI or the old app) has no **Remove…** (`REMOVABLE_CODE` in `hymnals-card.tsx`). Widening the route would have to admit spaces, dots and slashes in a path segment, and a `/` cannot travel in one; `DELETE /hymnals/{code}` keeps S's pattern. Test: T7 "offers no Remove for a hymnal whose code the removal route cannot take" (`PH 1990` and `X` have none, `PH1990` has one). Clarification 4.
- **M5 (T9: the member's summary).** The Church page's read-only summary shows "Add hymns on the Hymns page" under the no-hymns line too (one `AddHymnsLink` for both views). Test: T9's new "shows a member of a church with no hymns the link to the Hymns page (slice 6a-2)". Clarification 20.
- **M6 (Risks: re-adding after a rename).** A Risks entry: the import matches by number and title words, so adding a bundled hymnal again after one of its hymns was renamed inserts the bundled title as a second hymn; the record notes it.
- **M7 (T12 Step 4: the default set back).** Step 4 records whether the owner had to set the default hymnal back in **Church** before removing PH1990 (and to which code), and the record template's row 3 has a cell for it.
- **M8 (T3 `update_hymn`: a blank title).** The duplicate check is skipped when the resulting title is blank (an old hymn's: null, a space or empty), which would otherwise give "GG2013 already has #5 .". Test: T3 `test_an_edit_of_an_old_hymn_with_a_blank_title_is_never_a_duplicate` (two blank-titled hymns moved onto the number of a third). Clarification 12.

Counts after the fixes: backend `1883 passed, 31 skipped` (T3 +28, one new test); frontend `869 passed` in 103 files (T7 +12, five new tests; T9 +2, one new). Owner questions: still 13; only question 13 (the wording) changed, and now reads: "**The wording** (clarification 22): every new line on the page and in the dialogs, as listed there, including two lines added after the plan's review: "{code} is already added." (when adding a hymnal brings nothing new, for example because it was just added in another tab) and, for a hymnal with a single hymn, "This deletes the 1 hymn in {code} from your church's hymnal, …" instead of "This deletes all 1 hymns …". Recommended: accept."

## Self-review

- **Coverage.** Every binding constraint has a home: the nav order (clarification 2, T9); one PR (T11); the year and familiarity admin-only, delete admin-only, hymnal removal never the only or the default (clarification 14, T3-T4, T7-T8); the edit note (clarification 8, T8); the accepted 12-week risk in the record (T12 Step 8); no Hymnary button; no migration (clarification 21, owner question 12); no em dash in new copy (clarification 22; T10 Step 2 and T11 Step 3 grep the added lines; S's em dashes dropped, owner question 8); no ids or real addresses in the docs (only `@example.com`/`@example.org`; the record's own grep, T12 Step 8); the frozen Streamlit files untouched and their tests passing (T2 Step 4 runs `streamlit_tests`; T11 Step 3's path check counts `app.py`, `streamlit_views` and `streamlit_tests` as 0); tests never reach the network (Global Constraints); the 5b-1 lessons (the Spec coverage row); 6a-1's patterns reused as they are (`lock_and_read_actor`, `require_admin_role`, the Settings shell, the generated types). The second-to-last task opens a draft PR only on the owner's yes; the last merges only on a yes, runs a four-step phone check one step at a time (the test hymn deleted in its step; PH1990 added and removed only when the church lacks it; a hymnal the church uses never removed) and inserts "### Slice 6a-2 record" before "## Backups", after "### Slice 5b-2b record".
- **Placeholders.** None in T1-T10's code, tests, commands or expected outputs; every expected output is quoted from the replay. The `<…>` left are T11 and T12's runtime values (`<N>`, `<scratch>`, times, the owner's answers), as in the 5b-1 plan.
- **Consistency.** Names agree across tasks: `hymnal_sources.load_rows`, `file_sources`, `list_bundled`, `rows_for`, `label_for` (T1) are used by `hymn_library` (T3) and the CLI (T1); `title_key`, `get_hymn`, `create_hymn`, `patch_hymn`, `find_duplicate`, `delete_hymnal` and the import's `session` (T2) by T3; the six usecases (T3) by the routes (T4); `HymnDetailOut`, `HymnalSourceList`, `HymnalAddedOut`, `HymnalRemovedOut` (T4) by the type names (T6); `refreshHymns`, `hymnFieldErrors`, `isDuplicateHymn` and the hooks (T6) by the card and the dialog (T7, T8); `keys.hymns`, `keys.hymnalSources` (existing) by the queries. The counts in the table, each task's "Expected" and the PR line (`1825 → 1883`, `27 → 31`, `835 → 869`, `100 → 103`) agree.
- **Not verified while planning:** the pushes, the PR and CI (the four Postgres tests were run on a local throwaway Postgres instead), the merge, Railway's and Vercel's deploys, the owner's phone check, the import's speed over the Supabase pooler, and the page at 375 px in a real browser (the classes give 44 px targets; jsdom does not lay out).
- **Judgement calls to watch in review:** tidying text instead of refusing it; the import filling only blanks (a behavior change for the ops CLI too); the duplicate check running on an edit only when the key changes; `HymnIn.title` nullable; the library's empty state without a second **Add hymn**; the catalog's GG2013 listed as a source.
