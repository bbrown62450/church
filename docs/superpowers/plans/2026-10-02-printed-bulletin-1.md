# Printed Bulletin PR 1: The Booklet From What the App Knows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first of the three printed bulletin PRs (owner answer 9, 2026-10-02): **the Sunday bulletin as a folded booklet, built from what the app already knows.** After it merges, a member on step 4 of the Service Builder (`/builder/review`) sees a new **Printed bulletin** card below the Word documents, with **Download printed bulletin** (a print-ready PDF: legal paper, landscape, two booklet pages per side, already in the order a folded booklet needs) and **Download Word version** (the same booklet in reading order, to change before printing). The booklet follows the owner's sample: a cover with the church's name, the picture's place with the sermon reading and the date, and the contact lines; "THE SERVICE FOR THE LORD'S DAY" with the order of worship under four section headings, each element in bold capitals with its leader right-aligned, the readings printed in full in the translation chosen on step 1 with a credit line, the Gloria Patri, the Apostles' Creed, the stars and "*Congregation stands if able"; and an announcements page on the back. What the app does not know yet (the church's address and contacts, the people who lead, the service time, the prelude and postlude, the cover picture, the announcements) prints as `[placeholders]`; PR 2 and PR 3 fill them. No database change (Alembic head stays `0005_services_extras`), no new variable; two new Python packages (reportlab, pypdf); production Streamlit (branch `streamlit-frozen`) is untouched.

**Architecture:** Backend first. `backend/printed_bulletin.py` (new, pure) turns a resolved service into the booklet's content as plain data (`Line`s of `Span`s for the cover, the order of worship and the back page), and holds the page order of a folded booklet (`booklet_positions`, `booklet_sides`), the date line and the filenames. `backend/printed_pdf.py` lays that content out with reportlab in reading order (7 x 8.5 in pages), counts the pages, renders again with the back page's number known, and imposes the pages onto legal landscape sheets with pypdf. `backend/printed_docx.py` writes the same content with python-docx in reading order. `usecases/documents.build_printed` cleans the input, reads the church's name and resolves the hymns in one short read, fetches the two readings' text through `usecases.passages` (charging the `scripture` bucket per part first), and renders. `POST /documents/printed` (church-scoped, plain `def`) answers the bytes with the 5a headers. Frontend: `printedRequest` and `printedFilename` beside the Word copies' helpers, `useDownloadPrinted` beside `useDownloadDocument`, and `PrintedCard` on the Review step.

**Tech Stack:** Python 3.11 (`.venv`), FastAPI 0.141, python-docx 1.2.0, **reportlab 5.0.1** (`reportlab>=5.0,<6`, BSD) and **pypdf 6.19.0** (`pypdf>=6.0,<7`, BSD-3-Clause), pytest; Next 16, React 19, TypeScript 5, Base UI, TanStack Query 5, sonner, Vitest 3 with Testing Library.

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-02-printed-bulletin-design.md` (owner answers 1-10; "The sample, read closely"; Decisions: layout and page order, PDF library, fonts, what prints where, scripture text, API; "Scope by PR" PR 1; Testing; Risks).
- The idea note `docs/superpowers/specs/2026-10-02-printed-bulletin-idea.md`; the owner's sample bulletin (September 27, 2026; shared in the session as a PDF, not committed; no name, address, phone or email from it enters the repo).
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md` §1.8 (timeouts, rate-limit buckets), §1.9 (file downloads), §2.2 (layers), §2.5 (logging), §4.5, §4.8, §4.9.
- Format models: `docs/superpowers/plans/2026-10-01-slice-5a1-documents.md` (the Word downloads this builds on) and `docs/superpowers/plans/2026-10-02-slice-5a3-save-services.md`.
- Facts checked for this plan (tree `0b7f5e2` = `origin/main` `3b1ed13` plus the 5a-3 runbook record, 2026-10-02): backend `1335 passed, 16 skipped`; frontend `655 passed` in 83 files; typecheck and lint clean; Alembic head `0005_services_extras` (5 revision files); 4 runbook owner markers. `POST /documents` (`api/routes/documents.py`) takes `{variant, service: ServiceDraft}`; `usecases.documents.build_document` cleans with `archive.clean_input`, resolves hymns in one `session_scope`, renders with `service_output.render_docx`. `ServiceDraft` carries no translation; the draft keeps `readings.translation` (null: the church's), and step 1 shows `effectiveTranslation` (the draft's when offered, else the church's). `usecases.passages` plans and loads passage text (part cache, 20 s deadline); `POST /scripture/passages` charges the `scripture` bucket (60 per user per 300 s) one token per part. `repos.churches.get_church` returns `{id, name, timezone, settings}`. `useApi().churchBlob` and `downloadBlob` exist (5a-1). LibreOffice in this container cannot open any `.docx` (5a-1's sample included), so the Word file was checked by reading it back with python-docx, not by rendering it.
- Every task's code was written and run by the planner in a throwaway worktree of `0b7f5e2`, and the plan's directives were then replayed onto a fresh worktree of the branch head (see "Build notes").

## Global Constraints

"T<n>" means Task n of this plan.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Frontend as `(cd frontend && …)`. No foreground `sleep`.
- Backend: one or more files `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -3`; the suite `.venv/bin/python -m pytest -q | tail -1`. Frontend: one or more files `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "^ +× |\[ src/|Tests ")` (a file that cannot load shows as `FAIL … [ src/… ]`; the `×` lines may come in another order than quoted); the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`; then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`.
- The API changes (T3), so T3 regenerates the snapshot and the types in the same commit: `.venv/bin/python backend/scripts/export_openapi.py` then `(cd frontend && npm run gen:api)`. Never edit `openapi.json` or `schema.d.ts` by hand.
- Two new runtime packages (T2): `reportlab>=5.0,<6` and `pypdf>=6.0,<7` in `backend/requirements.txt` (CI and Railway install it; `requirements-dev.txt` includes it). T2 Step 1 installs them into `.venv`.
- Branch `claude/slice-2-plan-4q33le`, at `0b7f5e2` plus this plan's commits (`WIP spec/plan: printed bulletin` …, `Spec: printed bulletin (owner answers 2026-10-02)`, `Plan: printed bulletin PR 1 (owner answers 2026-10-02)`), then T1-T6. Stage files by name (paths with parentheses in single quotes); `.claude/` stays untracked.
- `main` is protected (`backend`, `backend-postgres`, `frontend`, up to date). Merge only with `gh pr merge <N> --merge -R bbrown62450/church`, only on the owner's explicit yes.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing test first and see it fail as quoted.
- **Backup push after every task** (standing rule): the controller runs `git push origin claude/slice-2-plan-4q33le` after each task's commit (never `--force`; on a network error retry after 2, 4, 8 and 16 s). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`. The container can restart and lose uncommitted work: commit as soon as a task's checks pass.
- The PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)` and then `https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`, and includes the line `Tests: backend 1335 → 1363 passed, 16 → 16 skipped; frontend 655 → 660 in 83 → 83 files`.
- New prose for the owner has no em dashes and no flattery. New user-facing copy is exactly the list in clarification 17 and has no em dashes; existing copy keeps its own punctuation.
- No church id, email address, token, database URL or real person's name, address, phone or email in any doc, commit, test or record (the tests use "Example Church" and `example.com`).
- Ask the owner before any push to a PR, PR creation, marking ready, merging, or any production or settings action. Owner steps go one at a time, in plain words.

### How the file directives below read
As in the 5a plans: **Create `path`:** the block is the whole file; **Append to `path`:** the block is added at the end of the file (a leading empty line in the block is part of it); **In `path`, replace:** the first block occurs exactly once in the file and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted.

### Baselines and counts
- Starting baselines: backend **1335 passed, 16 skipped**; frontend **655 passed in 83 files**, typecheck and lint clean; Alembic head **`0005_services_extras`** (5 revision files; no new revision); runbook owner markers `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` = **4**. If any differs, stop and ask.
- Planned cumulative counts (observed while planning and again in the replay). A backend delta is the number of new collected tests (a parametrized test counts each case); a frontend delta the number of new `it(`.

  | After | Backend (delta) | Backend | Frontend (delta) | Frontend |
  |---|---|---|---|---|
  | T1 | +13 (`test_printed_bulletin.py`, one test in five cases) | 1348 passed, 16 skipped | 0 | 655 in 83 |
  | T2 | +5 (`test_printed_render.py`; `test_no_streamlit_in_core.py` edited) | 1353 passed, 16 skipped | 0 | 655 in 83 |
  | T3 | +10 (`test_api_printed.py`, one test in four cases) | 1363 passed, 16 skipped | 0 | 655 in 83 |
  | T4 | 0 | 1363 passed, 16 skipped | +2 (`download.test.ts` 1, `documents.test.ts` 1) | 657 in 83 |
  | T5 | 0 | 1363 passed, 16 skipped | +3 (`review-send-step.test.tsx`; one case edited) | 660 in 83 |
  | T6 | 0 (`test_slice1_docs.py` edited) | 1363 passed, 16 skipped | 0 | 660 in 83 |

- CI `backend-postgres` goes from `16 passed, 1335 deselected` to `16 passed, 1363 deselected` (no new Postgres test: nothing here writes).

### Layering and code rules (carried)
- `printed_bulletin`, `printed_pdf`, `printed_docx` and `usecases/documents.py` import no FastAPI, Starlette or Streamlit (`test_no_streamlit_in_core.py` gains the three new modules, T2); the route is a plain `def` with no SQL and no try/except (F §2.2 rule 1); `build_printed` reads in one short `session_scope` that closes before the readings are fetched and the file is rendered.
- Logs carry ids, the format, the size and the duration, never a service's text (F §2.5).
- Pages and components never call `apiFetch` or `apiFetchBlob`: `lib/queries/documents.ts` uses `useApi()` (F §4.5).
- Touch targets 44 px below `md`; text wraps at 375 px; no raw HTML (F §4.8); nothing about a document is cached or stored.

## Owner decisions

1. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
2. **Production Streamlit** (branch `streamlit-frozen`) is frozen and retired for real use; merges never reach it.
3. **`main` is branch-protected**; Railway and Vercel deploy on merge.
4. **The spec's decisions** stand as written in S.

### Owner answers (Beau, 2026-10-02, "all recommended"; binding)
1. **Output:** a print-ready PDF in the folded legal-landscape booklet layout, plus an editable Word version.
2. **Standing church settings** (PR 2): church name, address, phone, email, website, Facebook name; the standing worship leader, liturgist, organist; the "*Congregation stands if able" note and which elements get the star; the Gloria Patri words. **Weekly** (PR 2): prelude and postlude (title, composer), per-element leader if different, announcements.
3. **Announcements** (PR 2): a simple form for ushers, deacon of the week, coffee hour, plus free-text boxes for activities, prayer concerns, collection items; each carries forward from last week.
4. **Cover picture** (PR 3): uploaded each week with the option to keep last week's; printed under the church name with the scripture reference and date over it.
5. **Scripture:** full text in the translation chosen on step 1 with a credit line (this PR); a way to paste your own text for a licensed translation the app can't fetch (PR 2).
6. **One version** (no separate mailing version) for now.
7. **Keep the pastor's and bulletin Word copies;** add a third download, "Download printed bulletin".
8. **Weekly fields on a new "Bulletin" step** between Liturgy and Review; standing church details in a small Bulletin settings panel now, folded into 6a later (PR 2).
9. **Three PRs:** (1) the booklet PDF (and Word) from what the app already knows, placeholders for the rest: **this plan**; (2) the weekly fields and announcements (and the standing settings panel); (3) the cover picture upload. PR 2 and PR 3 get their own plans.
10. **Checks:** a guided phone check after each PR, plus a print test on legal paper at the church after PR 1 (folds and margins): T8 here.

**Later, out of scope:** PR 2 (the Bulletin step, the settings panel, `churches.settings["bulletin"]`, `services.bulletin` with migration `0006_services_bulletin`, carry forward, pasted reading text), PR 3 (the cover picture, `bulletin_images`, migration `0007_bulletin_images`), Voices of the Church, 6a.

## Spec clarifications

The owner's answers win over S and F; the code wins over both where they disagree. **[owner-visible]** items are put to the owner in "Questions for the owner" (each written as recommended).

1. **[owner-visible] What PR 1 ships** (owner answer 9). The booklet's content, the PDF and the Word file, `POST /documents/printed`, and the Printed bulletin card. Not here: the Bulletin step, the settings panel, any stored bulletin field, the cover picture, pasted reading text, a migration. The Word documents card does not change.
2. **[owner-visible] The Review step's layout** (owner answer 7): "Still to do", the Archive card, the Word documents card (unchanged), then the new **Printed bulletin** card. The two Word copies keep their place and wording.
3. **[owner-visible] The Printed bulletin card** (clarification 17 has the strings): its heading, one sentence on what the booklet holds, one on the placeholders, then **Download printed bulletin** (filled; the PDF) with "Ready to print on legal paper: both sides, flipped on the short edge, then folded in half." and **Download Word version** (outlined) with "The same bulletin as a Word file, to change before printing.". Each button has its own "Preparing…" (then "Still working…" after 8 s) and a polite status line for screen readers ("Printed bulletin: Preparing…", "Word version: Preparing…"). Both are off without a service date ("Choose a service date on step 1 to download.") or while step 1 shows a message ("Fix the readings on step 1 to download."), as the Word copies. A failure is a toast with the server's message (none after a 401 or a lost church); after a download of an unsaved service the card shows the save tip, as the Word documents card does.
4. **[owner-visible] The PDF is the imposed booklet** (owner answers 1, 6; S "Layout and page order"). Booklet pages are 7 x 8.5 in with 0.5 in margins; the cover is unnumbered, the inside pages are numbered from 1 at the bottom center, and the announcements page is last. The page count rounds up to a multiple of 4 with blank pages just before the announcements page, so the announcements stay on the back cover. Each legal landscape side holds two pages in booklet order (sheet k's front: pages N-1-2k and 2k; its back: 2k+1 and N-2-2k, counting from 0). Printed on both sides, flipped on the short edge, and folded, the stack reads in order. On a phone the PDF reads in sheet order (the first side is the back page and the cover); the Word version reads in order. With the sample's content, 8 pages on 2 sheets.
5. **[owner-visible] What the order of worship prints** (S "What prints where"): `liturgy_config.OUTLINE`'s order with the sample's additions, under "GATHERING FOR WORSHIP", "RECEIVING THE WORD", "RESPONDING TO THE WORD" and "SENDING OUT TO SERVE": Prelude, Welcome and Announcements, Call to Worship, Opening Prayer, the opening hymn, Prayer of Confession (bold), Assurance of Pardon (the Leader line, then "People: Thanks be to God! Amen." in bold), Sung Response "Gloria Patri" with its words, Prayer for Illumination; First Reading and New Testament Reading with their text and the credit line; Sermon; Affirmation of Faith "The Apostles' Creed" with its text (bold); the response hymn; the communion liturgy when it is on; "PRAYERS OF THE PEOPLE/THE LORD'S PRAYER" as a heading only (the prayers are the pastor's to pray; the bulletin Word copy also leaves them out); Offering Our Gifts; Sung Response "Doxology"; Offertory Prayer; the closing hymn; Benediction (as the draft has it, so the church default prints with its quotation marks and "- Richard Halverson"); Postlude; "*Congregation stands if able". Custom elements print after their anchor; an empty hymn slot, a switched-off or blank section and a missing reading print nothing, as in the Word copies; a blank sermon title prints "[Sermon title]".
6. **[owner-visible] How elements look** (the sample): the label in bold capitals; a hymn as `*HYMN:  #409  "God Is Here!"` (number, then the title in bold italic quotation marks; no number, no "#"); a reading as `FIRST READING:  Psalm 25:1-9`; the sermon as `SERMON:  "Who Said?"`; the music as `PRELUDE:  '[Prelude title]'` with `- [Composer]` indented below; Leader lines in normal type and People lines in bold, each with a hanging indent; the leader's name right-aligned on the element's line.
7. **[owner-visible] Leaders until PR 2** (owner answer 2): `[Liturgist]` on Welcome, Call to Worship, Opening Prayer, Confession, Assurance, Prayer for Illumination and the First Reading; `[Worship leader]` on the New Testament Reading, the Sermon, Prayers of the People and the Offertory Prayer; `[Organist]` on the Prelude and Postlude (the sample's pattern). The hymns, sung responses, Affirmation, Offering and Benediction have none. The header reads "[Worship leader], Worship Leader", "[Liturgist], Liturgist", "[Organist], Organist" and the date line ends with "[Service time]". PR 2 makes the roles and the people settings.
8. **[owner-visible] Stars until PR 2:** the three hymns, both sung responses, the Affirmation of Faith and the Benediction (the sample's); "*Congregation stands if able" ends the service.
9. **[owner-visible] Fixed texts until PR 2:** the Gloria Patri "Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the beginning, is now, and ever shall be, world without end. Amen, amen." (the traditional words, as the sample; PR 2 makes them a setting); the Apostles' Creed in its traditional wording, as the sample prints it (public domain). The Doxology prints its title only, as the sample. The sample's offering note and "Please remain seated to the end of the Postlude" are church wording and wait for PR 2's settings.
10. **[owner-visible] The readings' text** (owner answer 5; S "Scripture text"). The two readings the Word copies print (`resolve_doc_readings`), fetched when the file is built, in the draft's translation when this deployment offers it, else the church's default when offered, else WEB (step 1's rule). The first alternative that comes back prints; verse line breaks become spaces; a blank line starts a paragraph. After the readings: "Scripture readings are from the {label}." (for example "the World English Bible (WEB)"). A reading whose text does not come back prints "[Reading text unavailable]"; the file never fails for it. Readings with more than 20 upstream parts in all are not fetched (both print the placeholder).
11. **The route** (S API). `POST /documents/printed`, church-scoped (`require_church`; any member), body `PrintedDocumentIn = {format: "pdf" | "docx", translation: string (trimmed, at most 20) | null, service: ServiceDraft}` (`extra="forbid"`), answer 200 with the bytes and `Content-Type: application/pdf` or the Word type, `Content-Disposition: attachment; filename="printed_bulletin_October_04_2026.pdf"; filename*=UTF-8''printed_bulletin_October_04_2026.pdf` (or `.docx`) and `Cache-Control: no-store`. A new route, not a third `variant` on `POST /documents`: its body and answer differ, and `DocumentIn` and its 22 tests stay as they are. No `Idempotency-Key` (a pure render that writes nothing). Errors stay JSON: the hymn 404 and the 422s as `/documents`; 429 `rate_limited` when the `scripture` bucket is empty (one token per upstream part, charged before any fetch, so a 429 fetches nothing; no readings, no charge); 403 for a church that is gone. OpenAPI declares a binary 200 under both types. The client waits up to 30 s (`timeouts.ts`), as for `/scripture/passages`.
12. **[owner-visible] Names and dates.** The booklet writes the date as "October 4, 2026" (no leading zero, as the sample's "September 27, 2026"); the Word copies keep "October 04, 2026". The files are `printed_bulletin_October_04_2026.pdf` and `printed_bulletin_October_04_2026.docx` (the Word copies' date form, so they sort together). The PDF's title is "Printed bulletin".
13. **[owner-visible] Fonts** (S "Fonts"): the PDF uses the standard Times family and Helvetica for the contact lines, not embedded (every viewer and printer has them; no font file in the repo); a character outside Windows-1252 prints as "?" after NFKC (a ligature becomes plain letters). The Word file uses Times New Roman 11 pt (Arial for the contact lines).
14. **[owner-visible] The Word version** (owner answer 1): the same content in reading order on 7 x 8.5 in pages, 0.5 in margins, each part (cover, service, announcements) starting a page, the leader at a right tab stop, page numbers from the first inside page (none on the cover), the picture's place as a bordered box. It does not set Word's Book fold; to print it as a booklet, use Word's Book fold or the printer's booklet setting (the card points to the PDF for printing).
15. **[owner-visible] The cover and the back page until PR 2 and PR 3:** the church's name (from the app), a bordered box with "[Cover picture]" and, over its lower part, the sermon reading (the New Testament reading, else the first reading) and the date; then "[Street address]", "[City, State ZIP]", "[Phone]", "[Email]", "[Website]", "FB: [Facebook name]". The back page: "ANNOUNCEMENTS", the date, "Ushers/Counters: [Names]", "Deacon of the Week: [Name]", "Coffee Hour: [Name]", "THIS WEEK'S ACTIVITIES AT A GLANCE" with "[Activities]", "PRAYERS AND CONCERNS" with "[Prayer concerns]", "ITEMS FOR COLLECTION" with "[Collection items]".
16. **Cleaning and safety.** The service is cleaned by `archive.clean_input` (as `/documents`); the church's name and each fetched text go through `_xml_safe` too, so the Word file never meets a character it cannot hold; the PDF escapes its markup. Nothing is stored or cached; downloads record no hymn use.
17. **[owner-visible] Every new user-facing string** (no em dashes). On the screen: "Printed bulletin"; "The folded booklet: the cover, the order of worship with the readings in full, and the announcements."; "For now, the church's details, the people who lead, the music and the announcements print as [placeholders]."; "Download printed bulletin"; "Ready to print on legal paper: both sides, flipped on the short edge, then folded in half."; "Download Word version"; "The same bulletin as a Word file, to change before printing."; for screen readers only "Printed bulletin: Preparing…", "Printed bulletin: Still working…", "Word version: Preparing…", "Word version: Still working…". Reused as they are: "Preparing…", "Still working…", "Choose a service date on step 1 to download.", "Fix the readings on step 1 to download.", "Tip: save this service so its hymns count as recently used.", and the existing error toasts (a 429 reads "Too many requests. Try again in {n} seconds."). In the files: "THE SERVICE FOR THE LORD'S DAY"; "[Worship leader], Worship Leader"; "[Liturgist], Liturgist"; "[Organist], Organist"; "[Service time]"; "GATHERING FOR WORSHIP"; "RECEIVING THE WORD"; "RESPONDING TO THE WORD"; "SENDING OUT TO SERVE"; "PRELUDE:", "POSTLUDE:", "'[Prelude title]'", "'[Postlude title]'", "- [Composer]"; "WELCOME AND ANNOUNCEMENTS"; the section labels in capitals ("CALL TO WORSHIP", "OPENING PRAYER", "PRAYER OF CONFESSION", "ASSURANCE OF PARDON", "PRAYER FOR ILLUMINATION", "OFFERTORY PRAYER", "*BENEDICTION"); "*HYMN:"; "*SUNG RESPONSE:" with "Gloria Patri" and "Doxology"; the Gloria Patri words; "FIRST READING:"; "NEW TESTAMENT READING:"; "[Reading text unavailable]"; "Scripture readings are from the {translation label}."; "SERMON:"; "[Sermon title]"; "*AFFIRMATION OF FAITH:" with "The Apostles' Creed" and its text; "PRAYERS OF THE PEOPLE/THE LORD'S PRAYER"; "OFFERING OUR GIFTS"; "*Congregation stands if able"; "[Liturgist]", "[Worship leader]", "[Organist]"; "[Cover picture]"; "[Street address]", "[City, State ZIP]", "[Phone]", "[Email]", "[Website]", "FB: [Facebook name]"; "ANNOUNCEMENTS"; "Ushers/Counters: [Names]"; "Deacon of the Week: [Name]"; "Coffee Hour: [Name]"; "THIS WEEK'S ACTIVITIES AT A GLANCE"; "[Activities]"; "PRAYERS AND CONCERNS"; "[Prayer concerns]"; "ITEMS FOR COLLECTION"; "[Collection items]"; the PDF title "Printed bulletin". The files use curly quotation marks and apostrophes, as the sample.
18. **Logging** (F §2.5): one INFO line per file, `documents.printed church=<id> format=<pdf|docx> bytes=<n> ms=<n>`; never a reading, a hymn or any text.
19. **Docs.** T6 appends "## Printed bulletin" to `docs/manual-verification.md` with items marked "(owner, after PR 1)" and "(owner, print test)" (the `##` pin in `test_slice1_docs.py` grows to eight). The runbook record is T8's.

### Risks
- **The printer's duplex.** "Flip on short edge" is the usual booklet setting for landscape sheets; a printer that flips the other way prints the backs upside down. T8's print test finds out; the fix (rotated backs, or a different instruction on the card) is a small follow-up.
- **Blank pages.** A short service pads with up to three blank pages before the back page. PR 2's announcements fill some of it; the print test asks whether the owner wants anything there.
- **Upstream text.** bible-api can be slow or missing a passage; the file still prints with "[Reading text unavailable]" within the passages' 20 s deadline, inside the client's 30 s.
- **Fonts not embedded.** A viewer substitutes its own Times; a reading with characters outside Windows-1252 shows "?". The print test and the phone check look at the readings; the fix is embedding Liberation Serif (S "Fonts").
- **iOS and a PDF download.** As for the Word copies (5a-1's check passed with the share sheet); T8 step 1 checks the PDF.

## File Structure

**Created**

| Path | What | Task |
|---|---|---|
| `backend/printed_bulletin.py` (+ `backend/tests/test_printed_bulletin.py`) | `Span`, `Line`, `Reading`, `PrintedService`; `order_of_worship`, `cover`, `announcements`; `booklet_positions`, `booklet_sides`; `printed_date`, `printed_filename`, `reading_paragraphs`; the placeholders and fixed texts | T1 |
| `backend/printed_pdf.py`, `backend/printed_docx.py` (+ `backend/tests/test_printed_render.py`) | `render_pdf` (reportlab, then pypdf imposition), `to_pdf_text`; `render_docx` | T2 |
| `backend/tests/test_api_printed.py` | the route, the readings, the bucket, access | T3 |
| `frontend/src/components/builder/review/printed-card.tsx` | the Printed bulletin card | T5 |

**Modified**

| Path | Change | Task |
|---|---|---|
| `backend/requirements.txt` | `reportlab>=5.0,<6`, `pypdf>=6.0,<7` | T2 |
| `backend/tests/test_no_streamlit_in_core.py` | the three new modules | T2 |
| `backend/usecases/documents.py` | `effective_translation`, `reading_texts`, `build_printed` | T3 |
| `backend/api/routes/documents.py` | `PrintedDocumentIn`, `POST /documents/printed` | T3 |
| `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` | regenerated | T3 |
| `frontend/src/lib/download.ts` (+ `.test.ts`), `frontend/src/lib/documents.ts` (+ `.test.ts`), `frontend/src/lib/queries/documents.ts`, `frontend/src/lib/api/timeouts.ts` | `PrintedFormat`, `printedFilename`; `PrintedBody`, `printedRequest`; `useDownloadPrinted`; 30 s | T4 |
| `frontend/src/components/builder/review/review-send-step.tsx` (+ `.test.tsx`) | the card in the step; the heading order | T5 |
| `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py` | "## Printed bulletin"; the pin | T6 |
| `docs/ops-runbook.md` | "### Printed bulletin PR 1 record" (the records PR, after the merge) | T8 |

**Counts in the PR:** <<PATHCOUNT>>. **Untouched:** migrations, `db/models.py`, `api/schemas.py`, `service_output.py`, `worship_service.py`, `liturgy_config.py`, `scripture_fetcher.py`, `usecases/passages.py`, `documents-card.tsx`, the draft schema, `app.py`, Streamlit.

**Task order and review batch:** T1 → T6, each one commit and a backup push; then one review of the whole batch with its fixes as `Fix: …` commits; T7 verifies and opens the draft PR on the owner's yes; T8 merges on the owner's yes, runs the phone check and the print test, and writes the record.

---

### Task 1: The booklet's content and page order: `printed_bulletin` (owner answers 1, 2, 5; S "Layout and page order", "What prints where"; clarifications 4-10, 12, 15)

**Files:**
- Create: `backend/tests/test_printed_bulletin.py`, `backend/printed_bulletin.py`

- [ ] **Step 1: Write the failing test**

**Create `backend/tests/test_printed_bulletin.py`:**

````python
"""The printed bulletin's content and page order (printed bulletin spec, PR 1;
printed_bulletin.py)."""
import datetime

import pytest

import printed_bulletin as pb
from liturgy_config import ASSURANCE_RESPONSE, DEFAULT_BENEDICTION_FALLBACK
from service_output import CustomElement, ResolvedHymn, ResolvedService

SUNDAY = datetime.date(2026, 10, 4)


def service(**changes) -> pb.PrintedService:
    resolved = ResolvedService(
        service_date=SUNDAY, occasion="World Communion Sunday", scriptures=("Psalm 80:7-15", "Matthew 21:33-46"),
        hymns={"opening": ResolvedHymn("God Is Here!", 409), "response": ResolvedHymn("Ride On", None),
               "closing": ResolvedHymn("Jesus Shall Reign", 265)},
        liturgy={"call_to_worship": "Leader: Lift up your hearts. People: We lift them up.",
                 "opening_prayer": "God of wisdom, hear us.", "prayer_of_confession": "Merciful God, forgive us.",
                 "assurance": "Leader: In Christ we are forgiven. People: Thanks be to God!",
                 "prayer_for_illumination": "Open our hearts.", "prayers_of_the_people": "We pray for all.",
                 "offertory_prayer": "Bless these gifts.", "benediction": DEFAULT_BENEDICTION_FALLBACK},
        sermon_title="Who Said?",
        custom_elements=(CustomElement("Anthem", "Chancel Choir", "sermon"), CustomElement("Ending", "", "end")))
    base = dict(church_name="Example Church", resolved=resolved,
                ot=pb.Reading("Psalm 80:7-15", "Turn us again, God.\nCause your face to shine.\n\nWe will be saved."),
                nt=pb.Reading("Matthew 21:33-46", None), translation_label="World English Bible (WEB)")
    base.update(changes)
    return pb.PrintedService(**base)


def texts(lines: list[pb.Line]) -> list[str]:
    return [line.text for line in lines]


@pytest.mark.parametrize("pages, positions", [
    (1, [None, None, None, 0]),
    (4, [0, 1, 2, 3]),
    (5, [0, 1, 2, 3, None, None, None, 4]),
    (6, [0, 1, 2, 3, 4, None, None, 5]),
    (9, [0, 1, 2, 3, 4, 5, 6, 7, None, None, None, 8]),
])
def test_the_booklet_pads_to_whole_sheets_with_blanks_before_the_back_page(pages, positions):
    assert pb.booklet_positions(pages) == positions


def test_the_sides_fold_into_reading_order():
    assert pb.booklet_sides(4) == [(3, 0), (1, 2)]
    assert pb.booklet_sides(8) == [(7, 0), (1, 6), (5, 2), (3, 4)]
    assert pb.booklet_sides(12) == [(11, 0), (1, 10), (9, 2), (3, 8), (7, 4), (5, 6)]
    for total in (4, 8, 12, 16):        # every page exactly once
        assert sorted(page for side in pb.booklet_sides(total) for page in side) == list(range(total))
    for bad in (0, 2, 6):
        with pytest.raises(ValueError):
            pb.booklet_sides(bad)
    with pytest.raises(ValueError):
        pb.booklet_positions(0)


def test_the_date_and_the_filenames():
    assert pb.printed_date(SUNDAY) == "October 4, 2026"
    assert pb.printed_date(datetime.date(2026, 9, 27)) == "September 27, 2026"
    assert pb.printed_filename("pdf", SUNDAY) == "printed_bulletin_October_04_2026.pdf"
    assert pb.printed_filename("docx", SUNDAY) == "printed_bulletin_October_04_2026.docx"


def test_a_reading_prints_as_paragraphs():
    assert pb.reading_paragraphs("Turn us again.\n Cause your face\n\tto shine.\n\n\nWe will be saved.\n") == [
        "Turn us again. Cause your face to shine.", "We will be saved."]
    assert pb.reading_paragraphs("  \n\n ") == []


def test_the_order_of_worship_follows_the_outline_with_the_sample_s_parts():
    lines = pb.order_of_worship(service())
    elements = [line.spans[0].text for line in lines if line.style in ("element", "section")]
    assert elements == [
        "October 4, 2026", "GATHERING FOR WORSHIP", "PRELUDE:", "WELCOME AND ANNOUNCEMENTS", "CALL TO WORSHIP",
        "OPENING PRAYER", "*HYMN:", "PRAYER OF CONFESSION", "ASSURANCE OF PARDON", "*SUNG RESPONSE:",
        "PRAYER FOR ILLUMINATION", "RECEIVING THE WORD", "FIRST READING:", "NEW TESTAMENT READING:", "SERMON:",
        "ANTHEM", "*AFFIRMATION OF FAITH:", "*HYMN:", "PRAYERS OF THE PEOPLE/THE LORD’S PRAYER",
        "RESPONDING TO THE WORD", "OFFERING OUR GIFTS", "*SUNG RESPONSE:", "OFFERTORY PRAYER",
        "SENDING OUT TO SERVE", "*HYMN:", "*BENEDICTION", "POSTLUDE:", "ENDING"]
    assert texts(lines[:5]) == ["THE SERVICE FOR THE LORD’S DAY", "Example Church",
                                "[Worship leader], Worship Leader", "[Liturgist], Liturgist", "[Organist], Organist"]
    assert lines[5].right == "[Service time]"
    assert lines[-1] == pb.Line("note", (pb.Span("*Congregation stands if able"),))


def test_each_element_prints_as_the_sample():
    lines = pb.order_of_worship(service())
    by_text = {line.text: line for line in lines}
    assert by_text["*HYMN:  #409  “God Is Here!”"].right == ""
    assert "*HYMN:  “Ride On”" in by_text                      # no number, no "#None"
    assert by_text["CALL TO WORSHIP"].right == "[Liturgist]"
    assert by_text["NEW TESTAMENT READING:  Matthew 21:33-46"].right == "[Worship leader]"
    assert by_text["PRELUDE:  ‘[Prelude title]’"].right == "[Organist]"
    assert by_text["SERMON:  “Who Said?”"].right == "[Worship leader]"
    leader, people = by_text["Leader: Lift up your hearts."], by_text["People: We lift them up."]
    assert (leader.style, [s.bold for s in leader.spans]) == ("hanging", [False, False])
    assert (people.style, [s.bold for s in people.spans]) == ("hanging", [True, True])
    assert by_text["Merciful God, forgive us."].spans[0].bold
    i = texts(lines).index("ASSURANCE OF PARDON")
    assert texts(lines[i + 1:i + 3]) == ["Leader: In Christ we are forgiven.", ASSURANCE_RESPONSE]
    i = texts(lines).index("FIRST READING:  Psalm 80:7-15")
    assert texts(lines[i + 1:i + 3]) == ["Turn us again, God. Cause your face to shine.", "We will be saved."]
    i = texts(lines).index("NEW TESTAMENT READING:  Matthew 21:33-46")
    assert texts(lines[i + 1:i + 3]) == ["[Reading text unavailable]",
                                         "Scripture readings are from the World English Bible (WEB)."]
    assert pb.APOSTLES_CREED in by_text and pb.GLORIA_PATRI in by_text and DEFAULT_BENEDICTION_FALLBACK in by_text
    assert "We pray for all." not in by_text                            # the prayers are the pastor's to pray
    assert "ANTHEM" in by_text and "Chancel Choir" in by_text and "ENDING" in by_text


def test_what_is_missing_is_left_out_or_a_placeholder():
    sparse = pb.PrintedService(church_name="Example Church", resolved=ResolvedService(
        service_date=SUNDAY, hymns={"opening": None, "response": None, "closing": None}),
        ot=None, nt=None, translation_label="World English Bible (WEB)")
    lines = texts(pb.order_of_worship(sparse))
    assert not any(line.startswith(("*HYMN", "FIRST READING", "NEW TESTAMENT", "CALL TO WORSHIP", "*BENEDICTION",
                                    "Scripture readings")) for line in lines)
    assert "SERMON:  “[Sermon title]”" in lines


def test_communion_prints_after_the_second_hymn():
    resolved = service().resolved
    with_communion = service(resolved=ResolvedService(**{**resolved.__dict__, "include_communion": True}))
    lines = texts(pb.order_of_worship(with_communion))
    second = lines.index("*HYMN:  “Ride On”")
    prayers = lines.index("PRAYERS OF THE PEOPLE/THE LORD’S PRAYER")
    assert "The Sacrament of the Lord's Supper" in lines[second + 1:prayers]
    assert "The Sacrament of the Lord's Supper" not in texts(pb.order_of_worship(service()))


def test_the_cover_and_the_back_page():
    assert texts(pb.cover(service())) == [
        "Example Church", "[Cover picture]", "Matthew 21:33-46", "October 4, 2026", "[Street address]",
        "[City, State ZIP]", "[Phone]", "[Email]", "[Website]", "FB: [Facebook name]"]
    assert texts(pb.cover(service(nt=None)))[2] == "Psalm 80:7-15"
    assert texts(pb.announcements(service())) == [
        "ANNOUNCEMENTS", "October 4, 2026", "Ushers/Counters: [Names]", "Deacon of the Week: [Name]",
        "Coffee Hour: [Name]", "THIS WEEK’S ACTIVITIES AT A GLANCE", "[Activities]", "PRAYERS AND CONCERNS",
        "[Prayer concerns]", "ITEMS FOR COLLECTION", "[Collection items]"]
````

- [ ] **Step 2: See it fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_printed_bulletin.py 2>&1 | tail -3`
**Expected:**
```
<<FAIL_T1>>
```

- [ ] **Step 3: Write `printed_bulletin`**

**Create `backend/printed_bulletin.py`:**

````python
"""The printed bulletin's content (printed bulletin spec, PR 1): what the
folded booklet prints, page by page, as plain data that printed_pdf and
printed_docx both render. Pure: no database, FastAPI, reportlab or
python-docx here.

- PrintedService: a service ready to print (the resolved service, the
  church's name, the readings with their text and the translation's label).
- cover, order_of_worship, announcements: the three parts of the booklet as
  Lines (one printed paragraph each). The order of worship follows
  liturgy_config.OUTLINE (the Word copies' order) with the parts the owner's
  sample bulletin adds (Prelude, Welcome and Announcements, the sung
  responses, the Offering, the Postlude) and its four section headings.
- Anything the app does not know yet (the church's address, the people who
  lead, the music, the announcements) prints as a [bracketed placeholder];
  PR 2 fills them from the Bulletin step and the bulletin settings.
- booklet_positions, booklet_sides: the page order of a folded booklet.
- printed_date, printed_filename, PDF_MIME.
"""
from __future__ import annotations

import datetime
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Optional

from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
from service_output import MONTHS, ResolvedHymn, ResolvedService, safe_date, service_date_display

PDF_MIME = "application/pdf"
Format = Literal["pdf", "docx"]

# The one page of the booklet: half a legal sheet (14 x 8.5 in) folded, 7 x 8.5 in.
PAGE_WIDTH = 504.0          # points
PAGE_HEIGHT = 612.0

# PR 1's placeholders: what PR 2's settings and Bulletin step fill in.
WORSHIP_LEADER = "[Worship leader]"
LITURGIST = "[Liturgist]"
ORGANIST = "[Organist]"
SERVICE_TIME = "[Service time]"
CONTACT_LINES = ("[Street address]", "[City, State ZIP]", "[Phone]", "[Email]", "[Website]",
                 "FB: [Facebook name]")
PRELUDE = ("[Prelude title]", "[Composer]")
POSTLUDE = ("[Postlude title]", "[Composer]")
COVER_PICTURE = "[Cover picture]"
TEXT_UNAVAILABLE = "[Reading text unavailable]"

# Who leads each element until PR 2's settings say (the owner's sample).
LEADERS: dict[str, str] = {
    "prelude": ORGANIST, "welcome": LITURGIST, "call_to_worship": LITURGIST, "opening_prayer": LITURGIST,
    "prayer_of_confession": LITURGIST, "assurance": LITURGIST, "prayer_for_illumination": LITURGIST,
    "ot_reading": LITURGIST, "nt_reading": WORSHIP_LEADER, "sermon": WORSHIP_LEADER,
    "prayers_of_the_people": WORSHIP_LEADER, "offertory_prayer": WORSHIP_LEADER, "postlude": ORGANIST,
}
# The elements printed with the star of STAND_NOTE (the owner's sample).
STARRED = frozenset({"first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology",
                     "third_hymn", "benediction"})
STAND_NOTE = "*Congregation stands if able"

GLORIA_PATRI = ("Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the "
                "beginning, is now, and ever shall be, world without end. Amen, amen.")
APOSTLES_CREED = (
    "I believe in God, the Father almighty, Maker of heaven and earth, and in Jesus Christ his only "
    "Son, our Lord; who was conceived by the Holy Ghost, born of the Virgin Mary, suffered under "
    "Pontius Pilate, was crucified, dead, and buried; he descended into hell; the third day he rose "
    "again from the dead; he ascended into heaven, and sitteth on the right hand of God the Father "
    "Almighty; from thence he shall come to judge the quick and the dead. I believe in the Holy "
    "Ghost; the holy catholic church; the communion of saints; the forgiveness of sins; the "
    "resurrection of the body; and the life everlasting. Amen.")

Style = Literal["header", "element", "section", "body", "bold", "hanging", "indent", "note", "credit",
                "title", "box", "contact", "center"]


@dataclass(frozen=True)
class Span:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class Line:
    """One printed paragraph. `right` prints right-aligned on the same line
    (an element's leader, or the service time)."""
    style: Style
    spans: tuple[Span, ...]
    right: str = ""

    @property
    def text(self) -> str:
        return "".join(span.text for span in self.spans)


@dataclass(frozen=True)
class Reading:
    reference: str
    text: Optional[str]            # None: the text could not be fetched (TEXT_UNAVAILABLE prints)


@dataclass(frozen=True)
class PrintedService:
    church_name: str
    resolved: ResolvedService
    ot: Optional[Reading] = None
    nt: Optional[Reading] = None
    translation_label: str = ""


def printed_date(d: datetime.date) -> str:
    """"October 4, 2026": the owner's bulletin writes the day without a leading zero."""
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}"


def printed_filename(fmt: Format, d: datetime.date) -> str:
    """printed_bulletin_October_04_2026.pdf (or .docx), the Word copies' date form."""
    return f"printed_bulletin_{safe_date(service_date_display(d))}.{fmt}"


# --- the booklet's page order ---

def booklet_positions(pages: int) -> list[Optional[int]]:
    """The booklet's pages in reading order as indexes of the rendered pages:
    `pages` rounded up to a multiple of 4 (one folded sheet holds 4), the
    blank pages (None) just before the last page, so the announcements stay
    on the back cover."""
    if pages < 1:
        raise ValueError("a booklet has at least one page")
    blanks = -pages % 4
    return [*range(pages - 1), *([None] * blanks), pages - 1]


def booklet_sides(total: int) -> list[tuple[int, int]]:
    """Each printed side as (left page, right page), 0-based booklet pages:
    sheet k's front is (total-1-2k, 2k), its back (2k+1, total-2-2k). Printed
    on both sides, flipped on the short edge, the stack folds into reading
    order. total=8: [(7, 0), (1, 6), (5, 2), (3, 4)]."""
    if total < 4 or total % 4:
        raise ValueError("a folded booklet has a multiple of 4 pages")
    sides = []
    for k in range(total // 4):
        sides.append((total - 1 - 2 * k, 2 * k))
        sides.append((2 * k + 1, total - 2 - 2 * k))
    return sides


# --- text helpers ---

_PEOPLE_LEADER = re.compile(r"\b(Leader|People):\s*", re.IGNORECASE)
_ASSURANCE_PEOPLE = re.compile(r"(?:^|(?<=\s))People:", re.IGNORECASE | re.MULTILINE)


def reading_paragraphs(text: str) -> list[str]:
    """A passage as printed paragraphs: a blank line starts a new paragraph;
    the verse line breaks inside one become spaces."""
    paragraphs = [" ".join(chunk.split()) for chunk in re.split(r"\n\s*\n", text)]
    return [p for p in paragraphs if p]


def _leader_people(text: str) -> list[Line]:
    """worship_service._add_leader_people_paragraph's reading: Leader lines in
    normal type, People lines in bold, each with a hanging indent."""
    matches = list(_PEOPLE_LEADER.finditer(text))
    if not matches:
        return [Line("body", (Span(text),))]
    lines = []
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        lines.append(Line("body", (Span(text[:matches[0].start()].strip()),)))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[m.end():end].strip()
        if m.group(1).lower() == "people":
            lines.append(Line("hanging", (Span("People: ", bold=True), Span(content, bold=True))))
        else:
            lines.append(Line("hanging", (Span("Leader: "), Span(content))))
    return lines


def _assurance(text: str) -> list[Line]:
    """worship_service._add_assurance_paragraph's reading: the text up to a
    typed "People:" label, then ASSURANCE_RESPONSE in bold, once."""
    leader = text.strip()
    people = _ASSURANCE_PEOPLE.search(leader)
    if people:
        leader = leader[: people.start()].strip()
    if leader.startswith("Leader:"):
        leader = leader[7:].strip()
    lines = [Line("hanging", (Span("Leader: "), Span(leader)))] if leader else []
    return [*lines, Line("bold", (Span(ASSURANCE_RESPONSE, bold=True),))]


def _star(key: str) -> str:
    return "*" if key in STARRED else ""


def _element(key: str, label: str, *value: Span) -> Line:
    """An element's heading: the label in capitals and bold, then its value,
    and the leader right-aligned."""
    return Line("element", (Span(f"{_star(key)}{label.upper()}", bold=True), *value), right=LEADERS.get(key, ""))


def _quoted(text: str) -> Span:
    return Span(f"“{text}”", bold=True, italic=True)


def _hymn(key: str, hymn: Optional[ResolvedHymn]) -> list[Line]:
    """*HYMN: #409 "God Is Here!"; an empty slot prints nothing (as the Word copies)."""
    if hymn is None or not hymn.title.strip():
        return []
    number = [] if hymn.number is None else [Span(f"#{hymn.number}  ", bold=True)]
    return [_element(key, "Hymn:", Span("  "), *number, _quoted(hymn.title))]


def _text_element(key: str, label: str, text: str, style: Style = "body") -> list[Line]:
    if not text:
        return []
    return [_element(key, label), Line(style, (Span(text, bold=style == "bold"),))]


def _custom(anchor: str, resolved: ResolvedService) -> list[Line]:
    lines = []
    for element in resolved.custom_elements:
        if element.insert_after == anchor and element.label:
            lines.append(_element("", element.label))
            if element.text:
                lines.append(Line("body", (Span(element.text),)))
    return lines


def _reading(key: str, label: str, reading: Optional[Reading]) -> list[Line]:
    if reading is None:
        return []
    lines = [_element(key, f"{label}:", Span(f"  {reading.reference}", bold=True))]
    if reading.text is None:
        return [*lines, Line("body", (Span(TEXT_UNAVAILABLE),))]
    return [*lines, *(Line("body", (Span(p),)) for p in reading_paragraphs(reading.text))]


def _communion() -> list[Line]:
    """liturgy_config.COMMUNION_BLOCKS, as the Word copies print them."""
    lines = []
    for block in COMMUNION_BLOCKS:
        if block.style == "heading1":
            lines.append(Line("section", (Span(block.text, bold=True, italic=True),)))
        elif block.style == "heading2":
            lines.append(_element("", block.text))
        elif block.style == "response":
            lines.append(Line("bold", (Span(block.text, bold=True),)))
        elif block.style == "text":
            lines.append(Line("body", (Span(block.text),)))
    return lines


def _section(title: str) -> Line:
    return Line("section", (Span(title, bold=True, italic=True),))


def _music(key: str, label: str, piece: tuple[str, str]) -> list[Line]:
    title, composer = piece
    return [_element(key, f"{label}:", Span("  "), Span(f"‘{title}’", bold=True, italic=True)),
            Line("indent", (Span(f"- {composer}"),))]


def order_of_worship(ps: PrintedService) -> list[Line]:
    """The inside pages: the service header, then the elements in OUTLINE
    order with the sample's additions, each custom element after its anchor."""
    r = ps.resolved
    lit: Mapping[str, str] = r.liturgy
    hymns = r.hymns
    sermon = r.sermon_title.strip() or "[Sermon title]"
    lines: list[Line] = [
        Line("header", (Span("THE SERVICE FOR THE LORD’S DAY", bold=True),)),
        Line("header", (Span(ps.church_name, bold=True),)),
        Line("header", (Span(f"{WORSHIP_LEADER}, Worship Leader", bold=True),)),
        Line("header", (Span(f"{LITURGIST}, Liturgist", bold=True),)),
        Line("header", (Span(f"{ORGANIST}, Organist", bold=True),)),
        Line("element", (Span(printed_date(r.service_date), bold=True),), right=SERVICE_TIME),
        _section("GATHERING FOR WORSHIP"),
        *_music("prelude", "Prelude", PRELUDE),
        _element("welcome", "Welcome and Announcements"),
    ]
    if lit.get("call_to_worship"):
        lines += [_element("call_to_worship", "Call to Worship"), *_leader_people(lit["call_to_worship"])]
    lines += _custom("call_to_worship", r)
    lines += _text_element("opening_prayer", "Opening Prayer", lit.get("opening_prayer", ""))
    lines += _custom("opening_prayer", r)
    lines += _hymn("first_hymn", hymns.get("opening"))
    lines += _custom("first_hymn", r)
    lines += _text_element("prayer_of_confession", "Prayer of Confession", lit.get("prayer_of_confession", ""), "bold")
    lines += _custom("prayer_of_confession", r)
    if lit.get("assurance"):
        lines += [_element("assurance", "Assurance of Pardon"), *_assurance(lit["assurance"])]
    lines += _custom("assurance", r)
    lines += [_element("gloria_patri", "Sung Response:", Span("  "), _quoted("Gloria Patri")),
              Line("bold", (Span(GLORIA_PATRI, bold=True, italic=True),))]
    lines += _text_element("prayer_for_illumination", "Prayer for Illumination", lit.get("prayer_for_illumination", ""))
    lines += _custom("prayer_for_illumination", r)
    lines.append(_section("RECEIVING THE WORD"))
    lines += _reading("ot_reading", "First Reading", ps.ot)
    lines += _custom("ot_reading", r)
    lines += _reading("nt_reading", "New Testament Reading", ps.nt)
    if (ps.ot or ps.nt) and ps.translation_label:
        lines.append(Line("credit", (Span(f"Scripture readings are from the {ps.translation_label}.", italic=True),)))
    lines += _custom("nt_reading", r)
    lines.append(_element("sermon", "Sermon:", Span("  "), _quoted(sermon)))
    lines += _custom("sermon", r)
    lines += [_element("affirmation_of_faith", "Affirmation of Faith:", Span("  "),
                       Span("“The Apostles’ Creed”", bold=True)),
              Line("bold", (Span(APOSTLES_CREED, bold=True),))]
    lines += _custom("affirmation_of_faith", r)
    lines += _hymn("second_hymn", hymns.get("response"))
    lines += _custom("second_hymn", r)
    if r.include_communion:
        lines += _communion()
    lines += _custom("communion", r)
    lines.append(_element("prayers_of_the_people", "Prayers of the People/The Lord’s Prayer"))
    lines += _custom("prayers_of_the_people", r)
    lines += [_section("RESPONDING TO THE WORD"),
              _element("offering", "Offering Our Gifts"),
              _element("doxology", "Sung Response:", Span("  "), _quoted("Doxology"))]
    lines += _text_element("offertory_prayer", "Offertory Prayer", lit.get("offertory_prayer", ""))
    lines += _custom("offertory_prayer", r)
    lines.append(_section("SENDING OUT TO SERVE"))
    lines += _hymn("third_hymn", hymns.get("closing"))
    lines += _custom("third_hymn", r)
    lines += _custom("benediction", r)
    lines += _text_element("benediction", "Benediction", lit.get("benediction", ""))
    lines += _music("postlude", "Postlude", POSTLUDE)
    lines += _custom("end", r)
    lines.append(Line("note", (Span(STAND_NOTE),)))
    return lines


def cover(ps: PrintedService) -> list[Line]:
    """The front page: the church's name, the picture's place with the
    sermon reading and the date over it, and the church's contact lines."""
    reading = ps.nt or ps.ot
    return [
        Line("title", (Span(ps.church_name, bold=True),)),
        Line("box", (Span(COVER_PICTURE),)),
        Line("box", (Span(reading.reference if reading else ""),)),
        Line("box", (Span(printed_date(ps.resolved.service_date)),)),
        *(Line("contact", (Span(text),)) for text in CONTACT_LINES),
    ]


def announcements(ps: PrintedService) -> list[Line]:
    """The back page: PR 2's announcements form, as placeholders for now."""
    return [
        Line("header", (Span("ANNOUNCEMENTS", bold=True),)),
        Line("header", (Span(printed_date(ps.resolved.service_date), bold=True),)),
        Line("center", (Span("Ushers/Counters: ", bold=True), Span("[Names]"))),
        Line("center", (Span("Deacon of the Week: ", bold=True), Span("[Name]"))),
        Line("center", (Span("Coffee Hour: ", bold=True), Span("[Name]"))),
        _section("THIS WEEK’S ACTIVITIES AT A GLANCE"),
        Line("center", (Span("[Activities]"),)),
        _section("PRAYERS AND CONCERNS"),
        Line("center", (Span("[Prayer concerns]"),)),
        _section("ITEMS FOR COLLECTION"),
        Line("center", (Span("[Collection items]"),)),
    ]
````

- [ ] **Step 4: See it pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_printed_bulletin.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `13 passed in <t>s`; `1348 passed, 16 skipped in <t>s`.

- [ ] **Step 5: Commit**

```bash
git add backend/printed_bulletin.py backend/tests/test_printed_bulletin.py
git commit -q -m "Printed bulletin PR 1: the booklet's content and page order" -m "printed_bulletin turns a resolved service into the folded booklet's
content as plain data: the cover, the order of worship in OUTLINE order
with the owner's sample's additions and section headings, and the
announcements page, with [placeholders] for what PR 2 and PR 3 bring. It
also holds the booklet's page order (blank pages before the back page;
sheet sides for printing on both sides), the date line and the filenames." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1348 passed, 16 skipped`; frontend `655 passed` in 83 files.

### Task 2: The PDF and the Word file: `printed_pdf`, `printed_docx` (owner answers 1, 6; S "PDF library", "Fonts", "Layout and page order"; clarifications 4, 13, 14)

**Files:**
- Create: `backend/tests/test_printed_render.py`, `backend/printed_pdf.py`, `backend/printed_docx.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`, `backend/requirements.txt`

- [ ] **Step 1: Install the two packages**

Run: `.venv/bin/pip install -q "reportlab>=5.0,<6" "pypdf>=6.0,<7" 2>&1 | grep -v notice; .venv/bin/python -c "import reportlab, pypdf; print(reportlab.Version, pypdf.__version__)"`
**Expected:** no error line; `5.0.1 6.19.0` (a later 5.x or 6.x is fine: say so). Both are pure-Python wheels (`py3-none-any`); reportlab brings Pillow and charset-normalizer wheels, so Railway needs no system library.

- [ ] **Step 2: Write the failing tests**

**Create `backend/tests/test_printed_render.py`:**

````python
"""The printed bulletin's two files (printed bulletin spec, PR 1): the
print-ready PDF (printed_pdf) and the Word file (printed_docx), read back
with pypdf and python-docx."""
import datetime
from io import BytesIO

from docx import Document
from docx.shared import Inches
from pypdf import PdfReader

import printed_bulletin as pb
import printed_docx
import printed_pdf
from service_output import ResolvedHymn, ResolvedService

VERSE = "And he answered, I will not; but afterward he repented and went. "


def service(verses: int = 20) -> pb.PrintedService:
    resolved = ResolvedService(
        service_date=datetime.date(2026, 9, 27), scriptures=("Psalm 25:1-9", "Matthew 21:23-32"),
        hymns={"opening": ResolvedHymn("God Is Here!", 409), "response": None,
               "closing": ResolvedHymn("Jesus Shall Reign Where’er the Sun", 265)},
        liturgy={"call_to_worship": "Leader: Lift up your hearts. People: We come, ready to listen and learn.",
                 "opening_prayer": "God of wisdom and truth, hear us. Amen",
                 "benediction": "Go in peace. - A Friend"},
        sermon_title="Who Said?")
    return pb.PrintedService("Example Church", resolved, pb.Reading("Psalm 25:1-9", "In you, Lord, I put my trust."),
                             pb.Reading("Matthew 21:23-32", VERSE * verses), "World English Bible (WEB)")


def sides(content: bytes) -> list[str]:
    return [" ".join(page.extract_text().split()) for page in PdfReader(BytesIO(content)).pages]


def test_the_pdf_is_legal_landscape_sheets_in_booklet_order():
    content = printed_pdf.render_pdf(service())
    assert content.startswith(b"%PDF-")
    reader = PdfReader(BytesIO(content))
    assert [(float(p.mediabox.width), float(p.mediabox.height)) for p in reader.pages] == [(1008.0, 612.0)] * 4
    text = sides(content)
    # Each side reads left page, then right page; a page's number comes first.
    # Side 1 (the outside of the folded sheets): the back page (7), then the cover (no number).
    assert text[0].startswith("7 ANNOUNCEMENTS September 27, 2026")
    assert text[0].index("ANNOUNCEMENTS") < text[0].index("Example Church") < text[0].index("FB: [Facebook name]")
    assert "Matthew 21:23-32 September 27, 2026" in text[0]
    # Sides 2-4: page 1 | blank, blank | page 2, page 3 | blank (5 pages padded to 8).
    assert text[1].startswith("1 THE SERVICE FOR THE LORD’S DAY Example Church [Worship leader], Worship Leader")
    assert text[2].startswith("2 NEW TESTAMENT READING: Matthew 21:23-32")
    assert text[3].startswith("3 POSTLUDE:") and text[3].endswith("*Congregation stands if able")


def test_the_pdf_prints_the_service_and_its_readings():
    text = " ".join(sides(printed_pdf.render_pdf(service())))
    for expected in ("*HYMN: #409 “God Is Here!”", "*HYMN: #265 “Jesus Shall Reign Where’er the Sun”",
                     "CALL TO WORSHIP [Liturgist]", "Leader: Lift up your hearts.",
                     "People: We come, ready to listen and learn.", "FIRST READING: Psalm 25:1-9",
                     "In you, Lord, I put my trust.", "NEW TESTAMENT READING: Matthew 21:23-32 [Worship leader]",
                     "Scripture readings are from the World English Bible (WEB).", "SERMON: “Who Said?”",
                     "I believe in God, the Father almighty", "*Congregation stands if able",
                     "POSTLUDE: ‘[Postlude title]’ [Organist]", "Go in peace. - A Friend"):
        assert expected in text, expected


def test_a_longer_service_takes_more_sheets_and_stays_a_multiple_of_four():
    short, long = printed_pdf.render_pdf(service()), printed_pdf.render_pdf(service(300))
    assert len(PdfReader(BytesIO(short)).pages) == 4                # 8 booklet pages: two sheets
    assert len(PdfReader(BytesIO(long)).pages) == 6                 # 12 booklet pages: three sheets
    assert sides(long)[0].startswith("11 ANNOUNCEMENTS")


def test_characters_the_standard_fonts_cannot_print_become_a_question_mark():
    assert printed_pdf.to_pdf_text("“Grace” – ﬁne ש") == "“Grace” – fine ?"
    resolved = ResolvedService(service_date=datetime.date(2026, 9, 27), sermon_title="Shalom שלום")
    text = " ".join(sides(printed_pdf.render_pdf(pb.PrintedService("Example Church", resolved))))
    assert "SERMON: “Shalom ????”" in text


def test_the_word_file_is_the_same_booklet_in_reading_order():
    doc = Document(BytesIO(printed_docx.render_docx(service())))
    section = doc.sections[0]
    assert (section.page_width, section.page_height) == (Inches(7), Inches(8.5))
    assert section.left_margin == Inches(0.5) and section.different_first_page_header_footer
    paragraphs = [p.text for p in doc.paragraphs]
    assert paragraphs[0] == "Example Church"
    assert doc.tables[0].cell(0, 0).paragraphs[1].text == "Matthew 21:23-32"
    starts = [p.text for p in doc.paragraphs if p.paragraph_format.page_break_before]
    assert starts == ["THE SERVICE FOR THE LORD’S DAY", "ANNOUNCEMENTS"]
    for expected in ("*HYMN:  #409  “God Is Here!”", "CALL TO WORSHIP\t[Liturgist]",
                     "People: We come, ready to listen and learn.", "FIRST READING:  Psalm 25:1-9\t[Liturgist]",
                     "Scripture readings are from the World English Bible (WEB).", "*Congregation stands if able",
                     "FB: [Facebook name]", "Coffee Hour: [Name]"):
        assert expected in paragraphs, expected
    people = next(p for p in doc.paragraphs if p.text.startswith("People: We come"))
    assert all(run.bold for run in people.runs)
    assert 'w:instrText xml:space="preserve">PAGE<' in section.footer._element.xml
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "service_output, worship_service, usecases.archive, usecases.documents, repos.services, hymn_usage; "
````

**with:**

````python
            "service_output, worship_service, usecases.archive, usecases.documents, repos.services, hymn_usage, "
            "printed_bulletin, printed_pdf, printed_docx; "
````

- [ ] **Step 3: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_printed_render.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -3`
**Expected:**
```
<<FAIL_T2>>
```

- [ ] **Step 4: Add the packages, write `printed_pdf` and `printed_docx`**

**In `backend/requirements.txt`, replace:**

````text
python-docx>=1.0.0
````

**with:**

````text
python-docx>=1.0.0
# The printed bulletin's PDF (printed bulletin spec): reportlab lays the booklet
# out and pypdf imposes it onto legal sheets. Both are pure Python wheels (BSD
# licenses) and need no system library on Railway; <next major until reviewed.
reportlab>=5.0,<6
pypdf>=6.0,<7
````

**Create `backend/printed_pdf.py`:**

````python
"""The printed bulletin as a print-ready PDF (printed bulletin spec, PR 1):
a folded booklet on legal paper, landscape, two pages per side.

render_pdf lays the booklet out in reading order with reportlab (cover,
order of worship, announcements; 7 x 8.5 in pages, Times), counts the pages,
renders again with the back page's number known, then imposes the pages
onto legal sheets with pypdf (printed_bulletin.booklet_positions and
booklet_sides): print on both sides, flipped on the short edge, and fold.
The fonts are the PDF standard Times family, which every viewer and printer
has, so nothing is embedded; a character outside their Windows-1252 set
prints as "?" (to_pdf_text). Pure: no database or FastAPI.
"""
from __future__ import annotations

import unicodedata
from io import BytesIO
from xml.sax.saxutils import escape

from pypdf import PageObject, PdfReader, PdfWriter, Transformation
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

import printed_bulletin as pb

SHEET_WIDTH = 2 * pb.PAGE_WIDTH        # legal, landscape: 14 x 8.5 in
MARGIN = 36.0                          # 0.5 in on every side
FOOTER = 20.0                          # the page number's baseline
RIGHT_COLUMN = 120.0                   # the leader's column on an element line

_GRAY = Color(0.45, 0.45, 0.45)


def to_pdf_text(text: str) -> str:
    """Text the standard fonts can print: NFKC first (a ligature or a
    full-width letter becomes plain letters), then any character outside
    Windows-1252 becomes "?"."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(ch if ch in "\n\t" or _cp1252(ch) else "?" for ch in text)


def _cp1252(ch: str) -> bool:
    try:
        ch.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def _style(name: str, **kw) -> ParagraphStyle:
    base = dict(fontName="Times-Roman", fontSize=11, leading=13)
    base.update(kw)
    return ParagraphStyle(name, **base)


STYLES = {
    "header": _style("header", alignment=TA_CENTER),
    "element": _style("element", spaceBefore=8),
    "section": _style("section", alignment=TA_CENTER, spaceBefore=12, spaceAfter=4),
    "body": _style("body"),
    "bold": _style("bold"),
    "hanging": _style("hanging", leftIndent=36, firstLineIndent=-36),
    "indent": _style("indent", leftIndent=36),
    "note": _style("note", spaceBefore=10),
    "credit": _style("credit", fontSize=9, leading=11, spaceBefore=4),
    "title": _style("title", fontSize=28, leading=34, alignment=TA_CENTER, spaceAfter=18),
    "box": _style("box", alignment=TA_CENTER),
    "contact": _style("contact", fontName="Helvetica", fontSize=12, leading=15, alignment=TA_CENTER),
    "center": _style("center", alignment=TA_CENTER, spaceBefore=3),
    "right": _style("right", alignment=TA_RIGHT),
    "page": _style("page", alignment=TA_CENTER),
}


def _markup(line: pb.Line) -> str:
    out = []
    for span in line.spans:
        text = escape(to_pdf_text(span.text)).replace("\n", "<br/>")
        if span.italic:
            text = f"<i>{text}</i>"
        if span.bold:
            text = f"<b>{text}</b>"
        out.append(text)
    return "".join(out)


def _flowable(line: pb.Line, width: float) -> Flowable:
    paragraph = Paragraph(_markup(line), STYLES[line.style])
    if not line.right:
        if line.style == "element":
            paragraph.keepWithNext = 1
        return paragraph
    right = Paragraph(escape(to_pdf_text(line.right)), STYLES["right"])
    table = Table([[paragraph, right]], colWidths=[width - RIGHT_COLUMN, RIGHT_COLUMN])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    table.spaceBefore = STYLES[line.style].spaceBefore
    table.keepWithNext = 1
    return table


class _CoverPicture(Flowable):
    """The cover picture's place (PR 3 prints the picture): a framed box with
    the sermon reading and the date over its lower part, as the sample."""

    def __init__(self, width: float, height: float, label: str, reference: str, date: str):
        super().__init__()
        self.width, self.height = width, height
        self.label, self.reference, self.date = label, reference, date

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setStrokeColor(_GRAY)
        c.rect(0, 0, self.width, self.height)
        c.setFillColor(_GRAY)
        c.setFont("Times-Italic", 11)
        c.drawCentredString(self.width / 2, self.height / 2 + 30, to_pdf_text(self.label))
        c.setFillColorRGB(0, 0, 0)
        for text, y in ((self.reference, 70), (self.date, 40)):
            if text:
                c.setFont("Times-Roman", 12)
                c.drawCentredString(self.width / 2, y, to_pdf_text(text))


def _story(ps: pb.PrintedService, width: float) -> list[Flowable]:
    cover = pb.cover(ps)
    title, label, reference, date, *contact = cover
    story: list[Flowable] = [
        Paragraph(_markup(title), STYLES["title"]),
        _CoverPicture(width - 60, 300, label.text, reference.text, date.text),
        Spacer(1, 30),
        *(Paragraph(_markup(line), STYLES["contact"]) for line in contact),
        NextPageTemplate("inside"),
        PageBreak(),
    ]
    story += [_flowable(line, width) for line in pb.order_of_worship(ps)]
    story += [NextPageTemplate("back"), PageBreak()]
    story += [_flowable(line, width) for line in pb.announcements(ps)]
    return story


def _reading_order(ps: pb.PrintedService, back_number: int | None) -> bytes:
    """The booklet in reading order, one 7 x 8.5 in page each: the cover
    unnumbered, the inside pages numbered from 1, the back page `back_number`."""
    buf = BytesIO()
    frame = Frame(MARGIN, MARGIN, pb.PAGE_WIDTH - 2 * MARGIN, pb.PAGE_HEIGHT - 2 * MARGIN,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def number(canvas, doc, value):
        if value is not None:
            canvas.setFont("Times-Bold", 10)
            canvas.drawCentredString(pb.PAGE_WIDTH / 2, FOOTER, str(value))

    doc = BaseDocTemplate(buf, pagesize=(pb.PAGE_WIDTH, pb.PAGE_HEIGHT), title="Printed bulletin",
                          leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN,
                          invariant=1)
    doc.addPageTemplates([
        PageTemplate("cover", [frame]),
        PageTemplate("inside", [frame], onPage=lambda c, d: number(c, d, c.getPageNumber() - 1)),
        PageTemplate("back", [frame], onPage=lambda c, d: number(c, d, back_number)),
    ])
    doc.build(_story(ps, pb.PAGE_WIDTH - 2 * MARGIN))
    return buf.getvalue()


def render_pdf(ps: pb.PrintedService) -> bytes:
    """The print-ready booklet: legal sheets, landscape, in booklet_sides order."""
    pages = len(PdfReader(BytesIO(_reading_order(ps, None))).pages)
    positions = pb.booklet_positions(pages)
    reader = PdfReader(BytesIO(_reading_order(ps, len(positions) - 1)))
    writer = PdfWriter()
    for left, right in pb.booklet_sides(len(positions)):
        sheet = PageObject.create_blank_page(width=SHEET_WIDTH, height=pb.PAGE_HEIGHT)
        for booklet_page, x in ((left, 0.0), (right, pb.PAGE_WIDTH)):
            index = positions[booklet_page]
            if index is not None:
                sheet.merge_transformed_page(reader.pages[index], Transformation().translate(tx=x, ty=0))
        writer.add_page(sheet)
    writer.add_metadata({"/Title": "Printed bulletin"})
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
````

**Create `backend/printed_docx.py`:**

````python
"""The printed bulletin as an editable Word file (printed bulletin spec, PR 1).

The same pages as printed_pdf in reading order, one 7 x 8.5 in page each
(half a legal sheet), 0.5 in margins, Times New Roman 11 pt: the cover, the
order of worship and the announcements, each starting a page, numbered from
the first inside page. An element's leader sits at a right tab stop. To print
a booklet from it, use Word's Book fold (Layout, Margins, Multiple pages) or
the printer's booklet setting; the PDF is already arranged for printing.
Pure: no database or FastAPI.
"""
from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

import printed_bulletin as pb

FONT = "Times New Roman"
TEXT_WIDTH = Inches(6)                   # 7 in less two 0.5 in margins

_ALIGN = {"header": WD_ALIGN_PARAGRAPH.CENTER, "section": WD_ALIGN_PARAGRAPH.CENTER,
          "title": WD_ALIGN_PARAGRAPH.CENTER, "box": WD_ALIGN_PARAGRAPH.CENTER,
          "contact": WD_ALIGN_PARAGRAPH.CENTER, "center": WD_ALIGN_PARAGRAPH.CENTER}
_SPACE_BEFORE = {"element": 8, "section": 12, "note": 10, "credit": 4, "center": 3}
_SIZE = {"title": 28, "credit": 9, "contact": 12}


def _add_line(doc, line: pb.Line):
    p = doc.add_paragraph()
    fmt = p.paragraph_format
    fmt.space_after = Pt(4 if line.style == "section" else 0)
    fmt.space_before = Pt(_SPACE_BEFORE.get(line.style, 0))
    if line.style in _ALIGN:
        p.alignment = _ALIGN[line.style]
    if line.style == "hanging":
        fmt.left_indent, fmt.first_line_indent = Inches(0.5), Inches(-0.5)
    elif line.style == "indent":
        fmt.left_indent = Inches(0.5)
    if line.style == "element":
        fmt.keep_with_next = True
    for span in line.spans:
        run = p.add_run(span.text)
        run.bold, run.italic = span.bold or None, span.italic or None
        if line.style in _SIZE:
            run.font.size = Pt(_SIZE[line.style])
        if line.style == "contact":
            run.font.name = "Arial"
    if line.right:
        fmt.tab_stops.add_tab_stop(TEXT_WIDTH, WD_TAB_ALIGNMENT.RIGHT)
        p.add_run("\t" + line.right)
    return p


def _page_number_footer(section) -> None:
    """A centered PAGE field; the cover (a different first page) shows none,
    and numbering starts at 0 there, so the first inside page is 1."""
    section.different_first_page_header_footer = True
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.bold = True
    for tag, text in (("w:fldChar", "begin"), ("w:instrText", "PAGE"), ("w:fldChar", "end")):
        el = OxmlElement(tag)
        if tag == "w:fldChar":
            el.set(qn("w:fldCharType"), text)
        else:
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)
    start = OxmlElement("w:pgNumType")
    start.set(qn("w:start"), "0")
    section._sectPr.append(start)


def render_docx(ps: pb.PrintedService) -> bytes:
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(0)
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(7), Inches(8.5)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(section, side, Inches(0.5))
    section.footer_distance = Inches(0.25)
    _page_number_footer(section)

    title, label, reference, date, *contact = pb.cover(ps)
    _add_line(doc, title)
    box = doc.add_table(rows=1, cols=1)
    box.style = "Table Grid"
    cell = box.cell(0, 0)
    cell.width = Inches(5.2)
    first = cell.paragraphs[0]
    first.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hint = first.add_run(label.text)
    hint.italic = True
    hint.font.color.rgb = RGBColor(0x73, 0x73, 0x73)
    for _ in range(8):
        first.add_run().add_break()
    for line in (reference, date):
        p = cell.add_paragraph(line.text)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cell.add_paragraph()
    doc.add_paragraph()
    for line in contact:
        _add_line(doc, line)

    for part in (pb.order_of_worship(ps), pb.announcements(ps)):
        first, *rest = part
        _add_line(doc, first).paragraph_format.page_break_before = True
        for line in rest:
            _add_line(doc, line)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()
````

- [ ] **Step 5: See them pass, and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_printed_render.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1`
**Expected:** `<<PASS_T2>>`; `1353 passed, 16 skipped in <t>s`.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/printed_pdf.py backend/printed_docx.py backend/tests/test_printed_render.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Printed bulletin PR 1: the PDF and the Word file (reportlab, pypdf)" -m "printed_pdf lays the booklet out with reportlab in reading order (7 x 8.5
in pages, Times), then imposes it onto legal landscape sheets with pypdf,
ready to print on both sides and fold. printed_docx writes the same pages
in reading order for editing. Both packages are pure-Python wheels with
BSD licenses." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1353 passed, 16 skipped`; frontend `655 passed` in 83 files.

### Task 3: `POST /documents/printed` with the readings' text (owner answers 5, 7; S API, "Scripture text"; clarifications 10, 11, 16, 18)

**Files:**
- Create: `backend/tests/test_api_printed.py`
- Modify: `backend/usecases/documents.py`, `backend/api/routes/documents.py`, `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts` (regenerated)

- [ ] **Step 1: Write the failing tests**

**Create `backend/tests/test_api_printed.py`:**

````python
"""POST /documents/printed (printed bulletin spec, PR 1): the printed
bulletin as a PDF or a Word file, with the readings' text fetched in the
translation step 1 shows. scripture_fetcher.fetch_part is replaced, so
nothing leaves the machine."""
import logging
from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfReader

import scripture_fetcher
from api import ratelimit
from db import session_scope
from db.models import Church
from repos.memberships import add_membership
from scripture_fetcher import Part
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
SERVICE = {
    "service_date_iso": "2026-10-04",
    "occasion": "World Communion Sunday",
    "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    "hymns": {"opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990"},
              "response": None, "closing": None},
    "hymnal": None,
    "liturgy": {"call_to_worship": "Leader: Come. People: We come.", "prayers_of_the_people": "We pray."},
    "sermon_title": "Living Water",
    "selected_ot_ref": "",
    "selected_nt_ref": "",
    "include_communion": False,
    "custom_elements": [],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Example Church", owner_user_id=owner)


@pytest.fixture
def calls(monkeypatch):
    """Every part fetched, as (part, translation); "Isaiah 5:1-7" is unavailable."""
    seen = []

    def fetch_part(part, translation):
        seen.append((part, translation))
        if part.startswith("Isaiah"):
            return Part(part, "unavailable", None)
        return Part(part, "ok", f"Text of {part} ({translation}).\nSecond verse.")

    monkeypatch.setattr(scripture_fetcher, "fetch_part", fetch_part)
    return seen


def post(client, church_id, body, email=EMAIL):
    return client.post("/documents/printed", json=body, headers=church_headers(email, church_id))


def pdf_text(content: bytes) -> str:
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(BytesIO(content)).pages)


def test_the_pdf_downloads_with_the_file_headers_and_the_readings_text(client, church, calls, caplog):
    caplog.set_level(logging.INFO, logger="usecases.documents")
    r = post(client, church, {"format": "pdf", "translation": "kjv", "service": SERVICE})
    assert r.status_code == 200, r.text
    name = "printed_bulletin_October_04_2026.pdf"
    assert r.headers["content-type"] == PDF
    assert r.headers["content-disposition"] == f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}"
    assert r.headers["cache-control"] == "no-store"
    text = pdf_text(r.content)
    assert "Example Church" in text and "*HYMN: #12 “Old Favorite”" in text
    assert "FIRST READING: Isaiah 5:1-7 [Liturgist] [Reading text unavailable] NEW TESTAMENT" in text
    assert "NEW TESTAMENT READING: Philippians 3:4b-14 [Worship leader] Text of Philippians 3:4-14 (kjv). Second verse." in text
    assert "Scripture readings are from the King James Version (KJV)." in text
    assert calls == [("Isaiah 5:1-7", "kjv"), ("Philippians 3:4-14", "kjv")]
    assert "We pray." not in text
    (record,) = [r for r in caplog.records if r.getMessage().startswith("documents.printed")]
    assert "format=pdf" in record.getMessage() and "Living Water" not in record.getMessage()


def test_the_word_file_downloads_too(client, church, calls):
    r = post(client, church, {"format": "docx", "translation": None, "service": SERVICE})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == DOCX
    assert "printed_bulletin_October_04_2026.docx" in r.headers["content-disposition"]
    paragraphs = [p.text for p in Document(BytesIO(r.content)).paragraphs]
    assert "Text of Philippians 3:4-14 (web). Second verse." in paragraphs
    assert {translation for _part, translation in calls} == {"web"}


def test_a_translation_not_offered_here_prints_in_the_church_s(client, church, calls):
    with session_scope() as s:
        s.get(Church, church).settings = {"bible_translation": "asv"}
    for requested in ("esv", "nope", None):                  # no ESV key in tests
        calls.clear()
        r = post(client, church, {"format": "pdf", "translation": requested, "service": SERVICE})
        assert r.status_code == 200, r.text
        assert {translation for _part, translation in calls} == {"asv"}
        assert "American Standard Version (ASV)" in pdf_text(r.content)


def test_no_readings_fetch_nothing(client, church, calls):
    r = post(client, church, {"format": "pdf", "service": {**SERVICE, "scriptures": []}})
    assert r.status_code == 200, r.text
    assert calls == []
    assert "Scripture readings are from" not in pdf_text(r.content)


def test_the_scripture_bucket_is_charged_per_part_and_a_429_fetches_nothing(client, church, owner, calls):
    ratelimit.consume("scripture", user_id=owner, cost=59)
    r = post(client, church, {"format": "pdf", "service": SERVICE})       # two parts, one token left
    assert r.status_code == 429, r.text
    assert r.json()["error"]["code"] == "rate_limited"
    assert calls == []


def test_any_member_and_only_members(client, church, make_user, calls, isolation_world):
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    assert post(client, church, {"format": "docx", "service": SERVICE}, email="member@example.com").status_code == 200
    assert_church_isolated(client, "POST", "/documents/printed", world=isolation_world,
                           json={"format": "pdf", "service": SERVICE})


@pytest.mark.parametrize("change, field", [
    ({"format": "html"}, "format"),
    ({"translation": "x" * 21}, "translation"),
    ({"variant": "bulletin"}, "variant"),
    ({"service": {**SERVICE, "service_date_iso": "2026-02-30"}}, "service.service_date_iso"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, calls, change, field):
    r = post(client, church, {"format": "pdf", "service": SERVICE, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"], r.text
    assert calls == []
````

- [ ] **Step 2: See them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_printed.py 2>&1 | tail -3`
**Expected:**
```
<<FAIL_T3>>
```

- [ ] **Step 3: The usecase and the route**

**In `backend/usecases/documents.py`, replace:**

````python
is a RuntimeError, which the API turns into a logged 500.
````

**with:**

````python
is a RuntimeError, which the API turns into a logged 500.

build_printed (the printed bulletin, PR 1) does the same for the folded
booklet, as a PDF or a Word file, and adds what the booklet prints beyond the
Word copies: the church's name (read with the hymns) and the two readings'
text, fetched in the translation step 1 shows (the draft's when this
deployment offers it, else the church's: readings.ts effectiveTranslation).
The fetch charges `charge(parts)` first (the route's `scripture` bucket, one
token per upstream part, as POST /scripture/passages); a reading whose text
does not come back prints "[Reading text unavailable]", never an error.
````

**In `backend/usecases/documents.py`, replace:**

````python
import uuid
````

**with:**

````python
import uuid
from collections.abc import Callable, Mapping
````

**In `backend/usecases/documents.py`, replace:**

````python
from dataclasses import dataclass
````

**with:**

````python
from dataclasses import dataclass
from typing import Optional
````

**In `backend/usecases/documents.py`, replace:**

````python

import service_output
````

**with:**

````python

import printed_bulletin
import printed_docx
import printed_pdf
import scripture_fetcher
import service_output
````

**In `backend/usecases/documents.py`, replace:**

````python
from usecases import archive
````

**with:**

````python
from domain_errors import Forbidden
from repos import churches
from usecases import archive, passages
````

**Append to `backend/usecases/documents.py`:**

````python


# --- the printed bulletin (printed bulletin spec, PR 1) ---

NO_ACCESS_MESSAGE = "You don't have access to this church."      # usecases.church_profile's


def effective_translation(requested: Optional[str], settings: object) -> str:
    """The translation the readings print in: `requested` (the draft's) when
    this deployment offers it, else the church's stored default when offered,
    else "web" (GET /church's effective_translation)."""
    offered = {tid for tid, _label in scripture_fetcher.available_translations()}
    if requested in offered:
        return requested
    stored = settings.get("bible_translation") if isinstance(settings, Mapping) else None
    return stored if stored in offered else scripture_fetcher.DEFAULT_TRANSLATION


def _first_text(passage: scripture_fetcher.Passage) -> Optional[str]:
    """The first alternative that came back ("Psalm 23 or Psalm 100" prints Psalm 23)."""
    text = next((s.text for s in passage.sections if s.status == "ok" and s.text), None)
    return None if text is None else archive._xml_safe(text)


def reading_texts(refs: list[str], translation: str,
                  charge: Callable[[int], None]) -> dict[str, Optional[str]]:
    """Each reading's text, or None. A reading with no parts, or readings with
    more parts than one passages request allows, are not fetched. `charge` is
    called once, with the number of upstream parts, before any fetch."""
    texts: dict[str, Optional[str]] = {ref: None for ref in refs}
    fetchable = [ref for ref in refs if scripture_fetcher.plan_sections(ref)]
    parts = sum(len(section) for ref in fetchable for _alternative, section in scripture_fetcher.plan_sections(ref))
    if not fetchable or parts > passages.MAX_PARTS:
        return texts
    plan = passages.plan_passages(fetchable, translation)
    charge(len(plan.parts))
    for ref, passage in zip(fetchable, passages.load_passages(plan).passages, strict=True):
        texts[ref] = _first_text(passage)
    return texts


def build_printed(church_id: uuid.UUID, data: archive.ServiceInput, fmt: printed_bulletin.Format,
                  translation: Optional[str], *, charge: Callable[[int], None]) -> DocumentResult:
    started = time.monotonic()
    clean = archive.clean_input(data)
    with session_scope() as s:                                  # read, then close before fetching
        church = churches.get_church(church_id, session=s)
        if church is None:
            raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
        hymns = archive.resolve_hymn_refs(s, church_id, clean.hymns)
    resolved = service_output.ResolvedService(
        service_date=clean.service_date, occasion=clean.occasion, scriptures=clean.scriptures, hymns=hymns,
        liturgy=clean.liturgy, sermon_title=clean.sermon_title, selected_ot_ref=clean.selected_ot_ref,
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements)
    ot, nt = service_output.resolve_doc_readings(list(clean.scriptures), clean.selected_ot_ref,
                                                 clean.selected_nt_ref)
    tid = effective_translation(translation, church["settings"])
    refs = [ref for ref in (ot, nt) if ref]
    texts = reading_texts(refs, tid, charge) if refs else {}
    printed = printed_bulletin.PrintedService(
        church_name=archive._xml_safe(church["name"] or "").strip(), resolved=resolved,
        ot=None if ot is None else printed_bulletin.Reading(ot, texts.get(ot)),
        nt=None if nt is None else printed_bulletin.Reading(nt, texts.get(nt)),
        translation_label=scripture_fetcher.translation_label(tid))
    content = printed_pdf.render_pdf(printed) if fmt == "pdf" else printed_docx.render_docx(printed)
    logger.info("documents.printed church=%s format=%s bytes=%d ms=%d", church_id, fmt, len(content),
                round((time.monotonic() - started) * 1000))
    return DocumentResult(content, printed_bulletin.printed_filename(fmt, clean.service_date))
````

**In `backend/api/routes/documents.py`, replace:**

````python
try/except (F §2.2 rule 1).
````

**with:**

````python
try/except (F §2.2 rule 1).

POST /documents/printed (printed bulletin spec, PR 1): the printed bulletin,
a folded booklet, as a print-ready PDF or an editable Word file. Its own
route because its body (format, translation) and its answer differ; it
fetches the readings' text, so it charges the `scripture` bucket one token
per upstream part (a 429 before any fetch), as POST /scripture/passages.
````

**In `backend/api/routes/documents.py`, replace:**

````python
from typing import Literal
````

**with:**

````python
from typing import Annotated, Literal, Optional
````

**In `backend/api/routes/documents.py`, replace:**

````python
from pydantic import BaseModel, ConfigDict
````

**with:**

````python
from pydantic import BaseModel, ConfigDict, StringConstraints
````

**In `backend/api/routes/documents.py`, replace:**

````python

import service_output
````

**with:**

````python

import printed_bulletin
import service_output
````

**In `backend/api/routes/documents.py`, replace:**

````python
from api.deps import ActiveChurch, require_church
````

**with:**

````python
from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
````

**Append to `backend/api/routes/documents.py`:**

````python


class PrintedDocumentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["pdf", "docx"]
    # The draft's translation (null: the church's); one this deployment does not offer prints in the church's.
    translation: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]] = None
    service: ServiceDraft


PRINTED_RESPONSE = {200: {"description": "The printed bulletin (Content-Disposition names it).",
                          "content": {printed_bulletin.PDF_MIME: {"schema": {"type": "string", "format": "binary"}},
                                      service_output.DOCX_MIME: {"schema": {"type": "string", "format": "binary"}}}}}
MEDIA_TYPES = {"pdf": printed_bulletin.PDF_MIME, "docx": service_output.DOCX_MIME}


@router.post("/documents/printed", response_class=Response,
             responses={**PRINTED_RESPONSE, **error_responses(401, 403, 404, 422, 429, 503)})
def create_printed(payload: PrintedDocumentIn, church: ActiveChurch = Depends(require_church),
                   user: CurrentUser = Depends(get_current_user)) -> Response:
    """Built from the body every time; nothing is stored or cached."""
    result = documents.build_printed(
        church.id, payload.service.to_input(), payload.format, payload.translation,
        charge=lambda n: ratelimit.consume("scripture", user_id=user.id, cost=n))
    return Response(content=result.content, media_type=MEDIA_TYPES[payload.format], headers={
        "Content-Disposition": service_output.content_disposition(result.filename),
        "Cache-Control": "no-store",
    })
````

- [ ] **Step 4: Regenerate the API files; see them pass, and the suite**

Run: `.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null) && git diff --stat -- frontend/src/lib/api` then `grep -c '"#/components/schemas/PrintedDocumentIn"' frontend/src/lib/api/openapi.json` then `.venv/bin/python -m pytest -q backend/tests/test_api_printed.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py 2>&1 | tail -1` then `.venv/bin/python -m pytest -q | tail -1` then `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?")`
**Expected:** `Wrote …/frontend/src/lib/api/openapi.json`, then `<<OPENAPI_STAT>>`; `1`; `<<PASS_T3>>`; `1363 passed, 16 skipped in <t>s`; `typecheck 0`.

- [ ] **Step 5: Commit**

```bash
git add backend/usecases/documents.py backend/api/routes/documents.py backend/tests/test_api_printed.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Printed bulletin PR 1: POST /documents/printed with the readings' text" -m "The printed bulletin as a PDF or a Word file, built from the posted
service with the church's name and the two readings' text, fetched in
the draft's translation when this deployment offers it, else the
church's. The fetch charges the scripture bucket per part first, so a
429 fetches nothing; a reading that does not come back prints a
placeholder. Nothing is stored or cached." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1363 passed, 16 skipped`; frontend `655 passed` in 83 files.

### Task 4: The request, the filename and the download (S API; F §1.8, §1.9, §4.5; clarifications 3, 10-12)

**Files:**
- Modify: `frontend/src/lib/download.test.ts`, `frontend/src/lib/documents.test.ts`, `frontend/src/lib/download.ts`, `frontend/src/lib/documents.ts`, `frontend/src/lib/queries/documents.ts`, `frontend/src/lib/api/timeouts.ts`

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/lib/download.test.ts`, replace:**

````ts
import { docxFilename, downloadBlob, REVOKE_AFTER_MS, type DocumentVariant } from "./download";
````

**with:**

````ts
import { docxFilename, downloadBlob, printedFilename, REVOKE_AFTER_MS, type DocumentVariant } from "./download";
````

**In `frontend/src/lib/download.test.ts`, replace:**

````ts
    for (const c of cases) expect(docxFilename(c.variant, c.date), c.date).toBe(c.filename);
````

**with:**

````ts
    for (const c of cases) expect(docxFilename(c.variant, c.date), c.date).toBe(c.filename);
  });
});

describe("printedFilename (printed bulletin PR 1)", () => {
  it("names the printed bulletin as the server does (printed_bulletin.printed_filename)", () => {
    expect(printedFilename("pdf", "2026-10-04")).toBe("printed_bulletin_October_04_2026.pdf");
    expect(printedFilename("docx", "2026-12-25")).toBe("printed_bulletin_December_25_2026.docx");
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts
import { editScriptureLines, setPick } from "@/lib/draft/readings";
````

**with:**

````ts
import { editScriptureLines, setPick, setTranslation } from "@/lib/draft/readings";
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts
import { documentRequest, savedCopyFingerprint, wordSafe } from "./documents";
````

**with:**

````ts
import { documentRequest, printedRequest, savedCopyFingerprint, wordSafe } from "./documents";
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````ts

describe("savedCopyFingerprint (5a-3 build review M2)", () => {
````

**with:**

````ts

describe("printedRequest (printed bulletin PR 1)", () => {
  it("sends the format, the draft's translation (null: the church's) and the service the Word copies send", () => {
    const d = editScriptureLines(testDraft(), OCT_4.join("\n"));
    expect(printedRequest(d, "pdf")).toEqual({ format: "pdf", translation: null, service: documentRequest(d, "bulletin").service });
    expect(printedRequest(setTranslation(d, "kjv", "web"), "docx")).toMatchObject({ format: "docx", translation: "kjv" });
    // An id the server would refuse (over 20 characters) goes as null: the church's translation.
    const odd = { ...d, readings: { ...d.readings, translation: "x".repeat(21) } };
    expect(printedRequest(odd, "pdf").translation).toBeNull();
  });
});

describe("savedCopyFingerprint (5a-3 build review M2)", () => {
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/lib/download.test.ts src/lib/documents.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected:**
```
<<FAIL_T4>>
```

- [ ] **Step 3: Write the helpers and the mutation**

**In `frontend/src/lib/download.ts`, replace:**

````ts
 *   answer 7, 2026-10-01).
````

**with:**

````ts
 *   answer 7, 2026-10-01).
 * - `printedFilename(format, dateIso)`: the printed bulletin's name
 *   (`printed_bulletin.printed_filename`), for the same fallback.
````

**In `frontend/src/lib/download.ts`, replace:**

````ts
export type DocumentVariant = "bulletin" | "pastor";
````

**with:**

````ts
export type DocumentVariant = "bulletin" | "pastor";
/** The printed bulletin's two files (printed bulletin spec, PR 1). */
export type PrintedFormat = "pdf" | "docx";
````

**In `frontend/src/lib/download.ts`, replace:**

````ts

export function downloadBlob(blob: Blob, filename: string): void {
````

**with:**

````ts

/** "2026-10-04" → "printed_bulletin_October_04_2026.pdf" (`printed_bulletin.printed_filename`). */
export function printedFilename(format: PrintedFormat, dateIso: string): string {
  const [year, month, day] = dateIso.split("-");
  return `printed_bulletin_${MONTHS[Number(month) - 1]}_${day}_${year}.${format}`;
}

export function downloadBlob(blob: Blob, filename: string): void {
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
import type { DocumentVariant } from "@/lib/download";
````

**with:**

````ts
import type { DocumentVariant, PrintedFormat } from "@/lib/download";
````

**In `frontend/src/lib/documents.ts`, replace:**

````ts
export type DocumentBody = components["schemas"]["DocumentIn"];
````

**with:**

````ts
export type DocumentBody = components["schemas"]["DocumentIn"];
export type PrintedBody = components["schemas"]["PrintedDocumentIn"];
````

**Append to `frontend/src/lib/documents.ts`:**

````ts

/** The server's `PrintedDocumentIn.translation` limit. */
const MAX_TRANSLATION = 20;

/**
 * The `POST /documents/printed` body (printed bulletin spec, PR 1): the same
 * service, the format, and the draft's translation (null: the church's). The
 * server prints in it when it still offers it, else in the church's, as step
 * 1 shows the readings (`effectiveTranslation`).
 */
export function printedRequest(draft: DraftV1, format: PrintedFormat): PrintedBody {
  const translation = draft.readings.translation;
  return {
    format,
    translation: translation && translation.length <= MAX_TRANSLATION ? translation : null,
    service: serviceBody(draft),
  };
}
````

**In `frontend/src/lib/queries/documents.ts`, replace:**

````ts
import { documentRequest } from "@/lib/documents";
````

**with:**

````ts
import { documentRequest, printedRequest } from "@/lib/documents";
````

**In `frontend/src/lib/queries/documents.ts`, replace:**

````ts
import { docxFilename, downloadBlob, type DocumentVariant } from "@/lib/download";
````

**with:**

````ts
import { docxFilename, downloadBlob, printedFilename, type DocumentVariant, type PrintedFormat } from "@/lib/download";
````

**Append to `frontend/src/lib/queries/documents.ts`:**

````ts

/**
 * The printed bulletin (printed bulletin spec, PR 1): as `useDownloadDocument`,
 * one mutation per button, posting `printedRequest` to `/documents/printed`.
 */
export function useDownloadPrinted(format: PrintedFormat) {
  const api = useApi();
  const { peek } = useDraft();
  return useChurchMutation<string, ApiError, void>({
    mutationFn: async () => {
      const body = printedRequest(peek(), format);
      const { blob, filename } = await api.churchBlob("/documents/printed", { method: "POST", json: body });
      const name = filename ?? printedFilename(format, body.service.service_date_iso);
      downloadBlob(blob, name);
      return name;
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /documents": 30_000,
````

**with:**

````ts
  "POST /documents": 30_000,
  // The printed bulletin (printed bulletin spec): the readings' text within the passages' 20 s deadline, then the file.
  "POST /documents/printed": 30_000,
````

- [ ] **Step 4: See them pass, the suite, types and lint**

Run: `(cd frontend && npx vitest run src/lib/download.test.ts src/lib/documents.test.ts 2>&1 | grep -E "^ +× |\[ src/|Tests ")` then the suite, then typecheck and lint.
**Expected:** `      Tests  <<PASS_T4>> passed (<<PASS_T4>>)`; ` Test Files  83 passed (83)` and `      Tests  657 passed (657)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/download.ts frontend/src/lib/download.test.ts frontend/src/lib/documents.ts frontend/src/lib/documents.test.ts frontend/src/lib/queries/documents.ts frontend/src/lib/api/timeouts.ts
git commit -q -m "Printed bulletin PR 1: the request, the filename and the download" -m "printedRequest sends the format, the draft's translation and the same
service body as the Word copies; printedFilename names the file as the
server does; useDownloadPrinted posts to /documents/printed (30 s) and
saves the file, one mutation per button." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1363 passed, 16 skipped`; frontend `657 passed` in 83 files.

### Task 5: The Printed bulletin card on Review & send (owner answers 1, 7; clarifications 2, 3, 17; F §4.8, §4.9)

**Files:**
- Create: `frontend/src/components/builder/review/printed-card.tsx`
- Modify: `frontend/src/components/builder/review/review-send-step.test.tsx`, `frontend/src/components/builder/review/review-send-step.tsx`

- [ ] **Step 1: Write the failing tests**

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import { editOccasion, editScriptureLines, setDate } from "@/lib/draft/readings";
````

**with:**

````tsx
import { editOccasion, editScriptureLines, setDate, setTranslation } from "@/lib/draft/readings";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
import { FIX_READINGS, NEEDS_DATE, SAME_AS_BULLETIN, SAVE_HINT } from "./documents-card";
````

**with:**

````tsx
import { FIX_READINGS, NEEDS_DATE, SAME_AS_BULLETIN, SAVE_HINT } from "./documents-card";
import { PLACEHOLDERS_NOTE, PRINTED_SUMMARY } from "./printed-card";
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    expect(within(step).getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual(["Still to do", "Archive", "Word documents"]);
````

**with:**

````tsx
    expect(within(step).getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Still to do",
      "Archive",
      "Word documents",
      "Printed bulletin",
    ]);
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````tsx
    }
  });
````

**with:**

````tsx
    }
  });
});

// --- the printed bulletin (printed bulletin spec, PR 1) ------------------------------

const PDF_NAME = "printed_bulletin_October_04_2026.pdf";

function pdf() {
  return new Response(new Uint8Array([0x25, 0x50, 0x44, 0x46]), {
    status: 200,
    headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename="${PDF_NAME}"` },
  });
}

function printedRequests(api: { requests: RecordedRequest[] }) {
  return api.requests.filter((r) => r.method === "POST" && r.path === "/documents/printed");
}

describe("Review & send: the printed bulletin (printed bulletin PR 1)", () => {
  it("shows the card after the Word documents with what it prints and both files", async () => {
    renderReview();
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(PRINTED_SUMMARY)).toBeInTheDocument();
    expect(within(card).getByText(PLACEHOLDERS_NOTE)).toBeInTheDocument();
    const printed = within(card).getByRole("button", { name: "Download printed bulletin" });
    const word = within(card).getByRole("button", { name: "Download Word version" });
    expect(printed).toHaveAccessibleDescription(
      "Ready to print on legal paper: both sides, flipped on the short edge, then folded in half.",
    );
    expect(word).toHaveAccessibleDescription("The same bulletin as a Word file, to change before printing.");
    for (const button of [printed, word]) {
      expect(button).toBeEnabled();
      expect(button).toHaveClass("h-11");
    }
  });

  it("downloads the PDF with the draft's translation, and names the Word version itself when the header is missing", async () => {
    const d = setTranslation(editCardText(testDraft(), "call_to_worship", "Leader: Come. People: We come."), "kjv", "web");
    const { api, user } = renderReview(d, {
      "POST /documents/printed": (request: RecordedRequest) => ((request.body as { format: string }).format === "pdf" ? pdf() : docx({})),
    });
    const card = await screen.findByRole("region", { name: "Printed bulletin" });
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    await waitFor(() => expect(clicks).toEqual([{ download: PDF_NAME, href: "blob:test/1" }]));
    expect(printedRequests(api)[0].body).toMatchObject({
      format: "pdf",
      translation: "kjv",
      service: { service_date_iso: "2026-10-04", liturgy: { call_to_worship: "Leader: Come. People: We come." } },
    });
    expect(printedRequests(api)[0].headers["x-church-id"]).toBe(church().id);
    expect(await within(card).findByText(SAVE_HINT)).toBeInTheDocument();
    await user.click(within(card).getByRole("button", { name: "Download Word version" }));
    await waitFor(() => expect(clicks).toHaveLength(2));
    expect(clicks[1].download).toBe("printed_bulletin_October_04_2026.docx");
    expect((printedRequests(api)[1].body as { format: string }).format).toBe("docx");
  });

  it("turns both off without a service date, and shows the server's message when a download fails", async () => {
    const d = testDraft();
    const undated = renderReview({ ...d, readings: { ...d.readings, date_iso: "" } });
    let card = await screen.findByRole("region", { name: "Printed bulletin" });
    expect(within(card).getByText(NEEDS_DATE)).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Download printed bulletin" })).toBeDisabled();
    expect(within(card).getByRole("button", { name: "Download Word version" })).toBeDisabled();
    undated.unmount();
    window.localStorage.clear();

    const { user } = renderReview(testDraft(), {
      "POST /documents/printed": fakeError(404, "not_found", HYMN_GONE, { details: { field: "hymns.response.hymn_id" } }),
    });
    card = await screen.findByRole("region", { name: "Printed bulletin" });
    await user.click(within(card).getByRole("button", { name: "Download printed bulletin" }));
    expect(await screen.findByText(HYMN_GONE)).toBeInTheDocument();
    expect(clicks).toEqual([]);
  });
````

- [ ] **Step 2: See them fail**

Run: `(cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests ")`
**Expected:**
```
<<FAIL_T5>>
```

- [ ] **Step 3: Write the card and add it to the step**

**Create `frontend/src/components/builder/review/printed-card.tsx`:**

````tsx
"use client";

import { DownloadIcon } from "lucide-react";
import { useState } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { useDraft } from "@/lib/draft/context";
import { hasReadingsError, hasServiceDate, reviewStatus } from "@/lib/draft/status";
import type { PrintedFormat } from "@/lib/download";
import { useDownloadPrinted } from "@/lib/queries/documents";

import { FIX_READINGS, NEEDS_DATE, SAVE_HINT } from "./documents-card";

type PrintedFile = { format: PrintedFormat; name: string; description: string; action: string };

const FILES: readonly PrintedFile[] = [
  {
    format: "pdf",
    name: "Printed bulletin",
    description: "Ready to print on legal paper: both sides, flipped on the short edge, then folded in half.",
    action: "Download printed bulletin",
  },
  {
    format: "docx",
    name: "Word version",
    description: "The same bulletin as a Word file, to change before printing.",
    action: "Download Word version",
  },
];

export const PRINTED_SUMMARY =
  "The folded booklet: the cover, the order of worship with the readings in full, and the announcements.";
export const PLACEHOLDERS_NOTE =
  "For now, the church's details, the people who lead, the music and the announcements print as [placeholders].";

function FileRow({ file, disabled, onDownloaded }: { file: PrintedFile; disabled: boolean; onDownloaded: () => void }) {
  const download = useDownloadPrinted(file.format);
  const slow = useStillWorking(download.isPending);
  const pendingLabel = slow ? "Still working…" : "Preparing…";
  const id = `printed-${file.format}`;
  return (
    <li className="grid gap-2">
      <p id={`${id}-description`} className="text-sm text-muted-foreground">
        {file.description}
      </p>
      <PendingButton
        size="touch"
        variant={file.format === "pdf" ? "default" : "outline"}
        className="w-full sm:w-fit"
        pending={download.isPending}
        pendingLabel={pendingLabel}
        disabled={disabled}
        aria-describedby={`${id}-description`}
        onClick={() => download.mutate(undefined, { onSuccess: onDownloaded })}
      >
        <DownloadIcon data-icon="inline-start" aria-hidden="true" />
        {file.action}
      </PendingButton>
      <p role="status" className="sr-only">
        {download.isPending ? `${file.name}: ${pendingLabel}` : ""}
      </p>
    </li>
  );
}

/**
 * The printed bulletin card (printed bulletin spec, PR 1; owner answers 1 and
 * 7, 2026-10-02): the folded booklet as a print-ready PDF (primary) and as a
 * Word file to change, each built on the server from the draft at the tap,
 * with the readings in full in the translation step 1 shows. Pending labels,
 * errors, the date and readings gates and the save tip work as on the Word
 * documents card. PR 1 prints what the app does not know yet as
 * [placeholders], and the card says so.
 */
export function PrintedCard() {
  const { draft } = useDraft();
  const [downloaded, setDownloaded] = useState(false);
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);
  return (
    <section aria-labelledby="printed-title" className="grid gap-4 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="printed-title" className="text-base font-medium">
          Printed bulletin
        </h2>
        <p className="text-sm text-muted-foreground">{PRINTED_SUMMARY}</p>
        <p className="text-sm text-muted-foreground">{PLACEHOLDERS_NOTE}</p>
        {dated ? null : <p className="text-sm text-muted-foreground">{NEEDS_DATE}</p>}
        {readingsError ? <p className="text-sm text-muted-foreground">{FIX_READINGS}</p> : null}
      </div>
      <ul className="grid gap-6">
        {FILES.map((file) => (
          <FileRow key={file.format} file={file} disabled={!dated || readingsError} onDownloaded={() => setDownloaded(true)} />
        ))}
      </ul>
      {downloaded && reviewStatus(draft) !== "saved" ? <p className="text-sm text-muted-foreground">{SAVE_HINT}</p> : null}
    </section>
  );
}
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
import { EditingBanner } from "./editing-banner";
````

**with:**

````tsx
import { EditingBanner } from "./editing-banner";
import { PrintedCard } from "./printed-card";
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
 * start a new service; 5a-3), and the Word documents. No order-of-worship
````

**with:**

````tsx
 * start a new service; 5a-3), the Word documents, and the printed bulletin
 * (printed bulletin spec, PR 1). No order-of-worship
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````tsx
      <DocumentsCard />
````

**with:**

````tsx
      <DocumentsCard />
      <PrintedCard />
````

- [ ] **Step 4: See them pass (three runs), the suite, types and lint**

Run: `for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/review/review-send-step.test.tsx 2>&1 | grep -E "^ +× |\[ src/|Tests "); done` then the suite, then typecheck and lint, then `grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"`.
**Expected:** three times `      Tests  <<PASS_T5>> passed (<<PASS_T5>>)`; ` Test Files  83 passed (83)` and `      Tests  660 passed (660)`; `typecheck 0`, `lint 0`; `raw html grep exit 1`.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/builder/review/printed-card.tsx frontend/src/components/builder/review/review-send-step.tsx frontend/src/components/builder/review/review-send-step.test.tsx
git commit -q -m "Printed bulletin PR 1: the Printed bulletin card on Review & send" -m "A card below the Word documents with Download printed bulletin (the
PDF, ready to print on legal paper and fold) and Download Word version,
each built from the draft at the tap, with its own pending label, the
date and readings gates, error toasts and the save tip. A line says
what still prints as [placeholders]." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1363 passed, 16 skipped`; frontend `660 passed` in 83 files.

### Task 6: Docs: the manual check items and their heading pin (owner answer 10; clarification 19)

**Files:**
- Modify: `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`

- [ ] **Step 1: Append the items and move the pin**

**Append to `docs/manual-verification.md`:**

````markdown

## Printed bulletin

Run on the production URL https://worship-service-builder.vercel.app, on an
iPhone with Safari at 375 px and on desktop Chrome. These are the printed
bulletin spec's manual checks for PR 1 (the booklet from what the app knows,
with [placeholders] for the rest). After the PR 1 merge the owner's guided
check (one step at a time on the phone) covers the items marked "(owner,
after PR 1)", and the print test at the church covers "(owner, print
test)"; the results go into `docs/ops-runbook.md` → "Printed bulletin PR 1
record". PR 2 and PR 3 add their own items here. Record what the page, the
file and the paper show, never an email address or a church id.

- [ ] (owner, after PR 1) **1.** Build a service with readings, hymns and liturgy and open **4 Review & send**. Under **Printed bulletin**, tap **Download printed bulletin**: "Preparing…", then the share or preview sheet with `printed_bulletin_October_04_2026.pdf` (for that date). The PDF's pages are wide (legal, landscape), two booklet pages each: the first has the announcements on the left and the cover (church name, the picture's box with the reading and the date) on the right; the next has "THE SERVICE FOR THE LORD'S DAY" on the left.
- [ ] (owner, after PR 1) **2.** In that PDF the readings are printed in full in the translation chosen on step 1, followed by "Scripture readings are from the …"; hymns read like `*HYMN: #409 "God Is Here!"`; the people lines are bold; the names, music and announcements show as [placeholders].
- [ ] (owner, after PR 1) **3.** Tap **Download Word version**: `printed_bulletin_October_04_2026.docx` opens in reading order (cover, the service, the announcements), on small pages.
- [ ] **4.** On step 1 choose another translation (for example KJV), then download again: the readings and the credit line change to it.
- [ ] (owner, after PR 1) **5.** At 375 px: no sideways scroll on **Review & send**; the two new buttons are full width and at least 44 px tall. Clear the service date: both are off with "Choose a service date on step 1 to download."
- [ ] (owner, print test) **6.** At the church, print the PDF on legal paper, both sides, flipped on the short edge. Fold the stack in half: the cover is on the front, the pages run 1, 2, 3 … in order, the announcements are on the back, nothing is upside down, and no text is cut off at the edges or the fold.
````

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
    # checks), the service reviewer "## Service reviewer", and slice 5a-1 "## Slice 5a".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-7:]
````

**with:**

````python
    # checks), the service reviewer "## Service reviewer", slice 5a-1 "## Slice 5a", and the printed bulletin's
    # PR 1 "## Printed bulletin".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-8:]
````

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
                        "## Slice 5a"]
````

**with:**

````python
                        "## Slice 5a", "## Printed bulletin"]
````

- [ ] **Step 2: Check the docs**

Run: `.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py backend/tests/test_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1` then `grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l` then `git diff -U0 docs/manual-verification.md | grep '^+' | grep -c '—'` then `git diff --stat`
**Expected:** `89 passed in <t>s`; `4`; `0`; `<<T6_STAT>>`.

- [ ] **Step 3: Commit**

```bash
git add docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -q -m "Docs: printed bulletin PR 1 manual checks" -m "docs/manual-verification.md gains \"## Printed bulletin\": the owner's
phone check after PR 1 (the PDF, its content, the Word version, the
layout) and the print test at the church (both sides, short edge, fold,
margins). The heading pin in test_slice1_docs.py grows to eight." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

Expected counts after this task: backend `1363 passed, 16 skipped`; frontend `660 passed` in 83 files.

### Task 7: Verification and the draft PR (owner's yes before the PR is opened and before it is marked ready)

Below, `<scratch>` is the session's scratchpad path and `<N>` the PR number; write both out literally. Every `gh` command uses `-R bbrown62450/church`. Never a bare `git push` or `--force`.

**Files:** none changed. A failure is fixed in its owning task's files (Step 6).

- [ ] **Step 1 (agent): Up to date with `origin/main`**

```bash
git status --short
git fetch origin
git rev-list --count HEAD..origin/main
git rev-list --count origin/claude/slice-2-plan-4q33le..HEAD
git merge-base --is-ancestor 0b7f5e2 origin/main; echo "5a-3 record on main: $?"
ls backend/migrations/versions | grep -c '^0'
```

**Expected:** nothing (or `?? .claude/`); `0`; `0`; `5a-3 record on main: 1` (it rides along: Step 3's list has `M docs/ops-runbook.md`; `0` if a records PR merged it meanwhile, and then that line is absent); `5`. If `main` moved: `git merge origin/main -m "Merge origin/main into claude/slice-2-plan-4q33le (Task 7)"` with the trailer as a second `-m`; on a conflict, `git merge --abort` and tell the owner.

- [ ] **Step 2 (agent): Both suites, the frontend three times, types, lint, the build, a sample booklet**

```bash
.venv/bin/python -m pytest -q | tail -1
for i in 1 2 3; do (cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests "); done
(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
(cd frontend && NEXT_PUBLIC_SUPABASE_URL=https://ci-placeholder.supabase.co NEXT_PUBLIC_SUPABASE_ANON_KEY=ci-placeholder NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build 2>&1 | grep -E "Compiled successfully|Error")
(cd backend && ../.venv/bin/python -c "
import datetime, printed_bulletin as pb, printed_pdf, printed_docx
from service_output import ResolvedService, ResolvedHymn
r = ResolvedService(service_date=datetime.date(2026, 10, 4), hymns={'opening': ResolvedHymn('God Is Here!', 409), 'response': None, 'closing': None}, liturgy={'call_to_worship': 'Leader: Lift up your hearts. People: We lift them up.'}, sermon_title='Who Said?')
ps = pb.PrintedService('Example Church', r, pb.Reading('Psalm 25:1-9', 'In you, Lord, I put my trust. ' * 30), pb.Reading('Matthew 21:23-32', 'And he answered. ' * 120), 'World English Bible (WEB)')
open('<scratch>/printed-sample.pdf', 'wb').write(printed_pdf.render_pdf(ps)); open('<scratch>/printed-sample.docx', 'wb').write(printed_docx.render_docx(ps)); print('sample written')
")
```

**Expected:** `1363 passed, 16 skipped in <t>s`; three times ` Test Files  83 passed (83)` and `      Tests  660 passed (660)` with no `×` or `FAIL` line (one names the failing test: Step 6); `typecheck 0`, `lint 0`; `✓ Compiled successfully in <t>s` and no `Error` (a font `Failed to fetch` only: say so and rely on CI); `sample written`. Open the sample PDF and look at it: four legal landscape sides, the first with the announcements left and the cover right; attach both samples to the owner's message in Step 4 if the channel allows files, else describe them.

- [ ] **Step 3 (agent): The API files match, the gates, the paths, the commits**

```bash
.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null) && git status --short -- frontend backend
grep -nE "^(import|from) (fastapi|starlette|streamlit)" backend/printed_bulletin.py backend/printed_pdf.py backend/printed_docx.py backend/usecases/documents.py; echo "imports grep exit $?"
grep -rn "dangerouslySetInnerHTML" frontend/src --include=*.tsx; echo "raw html grep exit $?"
git diff --name-status origin/main...HEAD | LC_ALL=C sort -k2
git diff --name-only origin/main...HEAD -- backend/migrations backend/db .github frontend/package.json frontend/package-lock.json app.py streamlit_views streamlit_tests | wc -l
git log --reverse --no-merges --format=%s origin/main..HEAD
for c in $(git rev-list origin/main..HEAD); do git show -s --format=%B "$c" | grep -q '^Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>$' || echo "no trailer: $(git show -s --format='%h %s' "$c")"; done; echo "trailer check done"
```

**Expected:** nothing from `git status` (the committed snapshot and types are current); `imports grep exit 1`; `raw html grep exit 1`; exactly these paths (without `M docs/ops-runbook.md` when Step 1 printed `0`):
```
<<PATHS>>
```
`0`; the subjects oldest first: `Runbook: slice 5a-3 record (merged; owner's five-step phone check)` (when it rides along), the spec and plan commits (`WIP spec/plan: printed bulletin` …, `Spec: printed bulletin (owner answers 2026-10-02)`, `Plan: printed bulletin PR 1 (owner answers 2026-10-02)`), then T1-T6's six subjects as written above, then any `Fix: …` lines; only `trailer check done`.

- [ ] **Step 4 (agent → OWNER): Ask to open the draft PR**

```bash
gh auth status 2>&1 | grep -E "Logged in to github.com"
gh pr list -R bbrown62450/church --head claude/slice-2-plan-4q33le --state open --json number,url
```

**Expected:** one `✓ Logged in` line; `[]`. Send the owner exactly this, and wait for a clear yes:

> The printed bulletin's first PR is verified on this machine: backend 1363 passed, 16 skipped (1335 before); frontend 660 tests in 83 files (655 before), three runs in a row; typecheck, lint and the production build are clean. It adds one API route, `POST /documents/printed`, two Python packages (reportlab and pypdf, both free to use), and no database change. On step 4 a new "Printed bulletin" card gives you the folded booklet as a PDF ready to print on legal paper, and as a Word file. Names, music, the church's details and the announcements print as [placeholders] until the next PR. May I open the pull request as a **draft** titled "Printed bulletin PR 1: the booklet from what the app knows", so the checks run? Merging stays with you.

- [ ] **Step 5 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/printed1-pr-body.md" <<'BODY'
Printed bulletin PR 1: the Sunday bulletin as a folded booklet, built from what the app already knows (the first of three printed bulletin PRs; owner answers of 2026-10-02). Spec: docs/superpowers/specs/2026-10-02-printed-bulletin-design.md. Plan: docs/superpowers/plans/2026-10-02-printed-bulletin-1.md. No database change, no new variable; one new route; two new Python packages.

- POST /documents/printed (church-scoped, any member): {format: pdf | docx, translation, service: ServiceDraft} in, the file out, with Content-Disposition (printed_bulletin_October_04_2026.pdf) and Cache-Control: no-store. The readings' text is fetched in the draft's translation (else the church's) and charged to the scripture bucket per part first.
- printed_bulletin (pure): the cover, the order of worship (OUTLINE order with the sample's additions and four section headings; leaders right-aligned; stars) and the announcements page, with [placeholders] for what PR 2 and PR 3 bring; the booklet's page order.
- printed_pdf: reportlab lays out 7 x 8.5 in pages; pypdf imposes them onto legal landscape sheets (blank pages before the back page). printed_docx: the same pages in reading order. reportlab (BSD) and pypdf (BSD-3-Clause) are pure-Python wheels.
- Review & send: a Printed bulletin card after the Word documents, with Download printed bulletin (PDF) and Download Word version.
- docs/manual-verification.md: "## Printed bulletin" (the phone check and the print test).

Later: PR 2 (the Bulletin step, the settings panel, announcements, services.bulletin), PR 3 (the cover picture).

Tests: backend 1335 → 1363 passed, 16 → 16 skipped; frontend 655 → 660 in 83 → 83 files

After merge (Task 8): a short check on the owner's phone, a print test at the church, then a "Printed bulletin PR 1 record" in docs/ops-runbook.md.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R bbrown62450/church --draft --base main --head claude/slice-2-plan-4q33le \
  --title "Printed bulletin PR 1: the booklet from what the app knows" \
  --body-file "<scratch>/printed1-pr-body.md"
gh pr checks <N> -R bbrown62450/church --watch --interval 30
```

Run the last line with `run_in_background: true`. **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's numbers: backend `1363 passed, 16 skipped` (CI installs reportlab and pypdf from `requirements-dev.txt`), backend-postgres `16 passed, 1363 deselected`, frontend `660 passed` in 83 files. Then send: "PR #<N> is green: backend 1363 passed, 16 skipped; 660 frontend tests in 83 files; the build and the Vercel preview are fine. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R bbrown62450/church`.

- [ ] **Step 6: Fix any failure in its owning task**

| Failing check or test | Owning task |
|---|---|
| `test_printed_bulletin.py` | T1 |
| `test_printed_render.py`, `test_no_streamlit_in_core.py`, a missing package on CI | T2 |
| `test_api_printed.py`, `test_openapi_contract.py`, `test_route_guards.py` | T3 |
| `download.test.ts`, `documents.test.ts` | T4 |
| `review-send-step.test.tsx` | T5 |
| `test_slice1_docs.py`, `test_docs.py` | T6 |
| a flaky run | its task: wait with `findBy`/`waitFor`, never sleep |
| anything else | report to the owner before changing anything |

For each fix: change only the owning task's files; rerun Steps 2-3; commit `Fix: <what> (Task <n>, printed bulletin PR 1 final verification)` with the trailer; after the PR exists, ask the owner before pushing it.

Expected counts after this task: backend `1363 passed, 16 skipped`; frontend `660 passed` in 83 files.

### Task 8: Merge, the owner's phone check (four steps), the print test, the record (OWNER + agent)

No schema change, so Railway's deploy has nothing to migrate (production stays at `0005_services_extras`); Railway installs the two new packages from `backend/requirements.txt` and serves the new route, Vercel the new card. The owner's check is **one step at a time** (send one, wait for the report or "next"), on the phone, on the production URL, in the owner's own church; then the print test at the church, when the owner is there. The agent writes each result into `<scratch>/printed1-t8-results.md` (not committed). Record what the page, the files and the paper showed, never a token, an email address, a church id or a church member's name.

**Files:** Modify (the records PR, Step 9): `docs/ops-runbook.md`: insert `### Printed bulletin PR 1 record` right before `## Backups` (after the last record above it, today the "Slice 5a-3 record" table, whose last row starts `| Follow-ups | 5a is complete.`). A `###` heading, because `test_ops_workflows.py` pins the `##` list.

- [ ] **Step 1 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R bbrown62450/church --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "PR #<N> (printed bulletin PR 1) is ready, green and up to date with main. There is no database change; Railway installs two new packages on its deploy. Then I will ask you for four short checks on your phone, one at a time, and later a print test at the church. May I merge it with a merge commit?" On a clear yes:

(not replayed)
```bash
gh pr merge <N> --merge -R bbrown62450/church
gh pr view <N> -R bbrown62450/church --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R bbrown62450/church --workflow ci.yml --branch main --commit "$(gh pr view <N> -R bbrown62450/church --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R bbrown62450/church --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (run it in the background). Record both. Wait about three minutes for Railway (it installs the packages) and Vercel before Step 2. If the owner can see Railway's deploy log, a line installing `reportlab` and `pypdf` and a clean startup are expected; a failed deploy keeps the old version running (Step R).

- [ ] **Step 2 (OWNER, then agent): Phone, step 1 of 4: the PDF downloads and opens (manual-verification item 1)**

> On your phone, open https://worship-service-builder.vercel.app and pull down to reload it, so the phone runs the new version. Build a service as you normally would, or keep the one you have: a date, readings, hymns, liturgy and a sermon title. Tap **4 Review & send**. Below **Word documents** there is a new card, **Printed bulletin**. Tap **Download printed bulletin**. The button says "Preparing…" for a few seconds (it fetches the readings); then your phone should show its share or preview sheet for a file named like `printed_bulletin_October_04_2026.pdf` (with your date). Open it. The pages are wide, each with two booklet pages side by side. Is the first page the announcements on the left and the cover on the right (your church's name, a box with the reading and the date, then the address lines in brackets)? Is the next page "THE SERVICE FOR THE LORD'S DAY" on the left?

Record whether the sheet appeared, the filename, how long "Preparing…" showed, and each answer. **If no download started or the file is empty**, record it and stop: it is a follow-up for the owner to decide; the Word copies are unaffected.

- [ ] **Step 3 (OWNER, then agent): Phone, step 2 of 4: what the PDF prints (item 2)**

> In that PDF: are both readings printed in full, in the translation you chose on step 1, followed by "Scripture readings are from the …"? Do the hymns read like `*HYMN: #409 "God Is Here!"`, are the People lines of the Call to Worship in bold, and are the Gloria Patri and the Apostles' Creed there? Names, the music and the announcements show as [placeholders] for now; is anything else missing or wrong compared with your bulletin?

Record the answers and any difference the owner names (each a follow-up for the record, PR 2's list or the owner to decide).

- [ ] **Step 4 (OWNER, then agent): Phone, step 3 of 4: the Word version (item 3)**

> Back on **4 Review & send**, tap **Download Word version**. The file is `printed_bulletin_October_04_2026.docx`. Open it in Word (or Files): does it read in order, the cover first, then the service, then the announcements, on small pages? If you can, change a word in it, to see that it edits.

- [ ] **Step 5 (OWNER, then agent): Phone, step 4 of 4: the page on the phone (item 5)**

> On **4 Review & send**: does the page fit the screen with no sideways scrolling, and are the two new buttons full width and easy to tap? Then go to **1 Date & readings**, clear the date, and come back: both printed bulletin buttons should be off, with "Choose a service date on step 1 to download." Put the date back.

- [ ] **Step 6 (OWNER at the church, then agent): The print test (owner answer 10; item 6)**

> When you are at the church: download the printed bulletin for this Sunday (or use the file from step 1), and print it on **legal** paper, **both sides**, with **flip on short edge** (some printers call it "short-edge binding" or "tablet"). Fold the stack in half. Please check: is the cover on the front and the announcements on the back; do the pages run 1, 2, 3 … in order with nothing upside down; is any text cut off at the edges or at the fold; are the page numbers there; is the type easy to read? If there are blank pages before the back, would you rather have something there (for example "Notes")? A photo of the folded booklet, if you like.

Record the printer's duplex setting used, each answer, and any change the owner asks for (a follow-up: rotated backs, different margins, a font size, notes pages).

- [ ] **Step 7 (agent): Fill the results**

Write each step's result, with the date, into `<scratch>/printed1-t8-results.md`. A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

- [ ] **Step 8 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (or `Already up to date.`); one `## Backups` line; the last `###` heading above it (today `### Slice 5a-3 record`). Insert, right before `## Backups` (one blank line on each side):

```markdown
### Printed bulletin PR 1 record

Printed bulletin PR 1 (the Sunday bulletin as a folded booklet from what the
app knows: `POST /documents/printed`, the print-ready PDF on legal paper and
the Word version, the Printed bulletin card on Review & send, with
[placeholders] for the church's details, the people, the music and the
announcements) merged as PR #<N>, the first of three printed bulletin PRs
(owner answers of 2026-10-02). No database change and no new variable;
production stays at `0005_services_extras`; two new Python packages
(reportlab, pypdf). The owner's check was four steps on a phone and a print
test at the church, covering the "(owner, after PR 1)" and "(owner, print
test)" items of `docs/manual-verification.md` → "Printed bulletin". No token,
email address, church id or member's name is recorded here.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success | <date> |
| 1. The PDF (phone: <phone and browser>) | <The share sheet opened with printed_bulletin_<date>.pdf after about <n> s; the first side had the announcements and the cover, the next "THE SERVICE FOR THE LORD'S DAY". / …> | <date> |
| 2. What it prints | <Both readings in full in <translation> with the credit line; hymns, People lines, Gloria Patri and the Creed as the sample; placeholders as expected. / Differences: …> | <date> |
| 3. Word version | <Opened in reading order on small pages and edited. / …> | <date> |
| 4. The page on the phone | <No sideways scroll; full-width buttons; off without a date with the message. / …> | <date> |
| 5. Print test (<printer>, legal, both sides, <duplex setting>) | <Folded in order with the cover front and announcements back; nothing upside down or cut off; page numbers present; <blank pages: owner's wish>. / …> | <date> |
| Follow-ups | <None. / One line per follow-up.> Next: printed bulletin PR 2 (the Bulletin step, the settings panel, announcements, `services.bulletin` with migration `0006_services_bulletin`), then PR 3 (the cover picture), Voices of the Church, 6a. Still open: the screen-reader copy for "Revise the other prayers", first-line matching research (Hymnary.org), the NUL-character 500 outside `/documents`, and the two slice 1 test churches (kept for now, owner) | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then (not replayed):

```bash
sed -n '/^### Printed bulletin PR 1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Printed bulletin PR 1 record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: printed bulletin PR 1 record (merged; owner's phone check and print test)" -m "Records printed bulletin PR 1 (PR #<N>): the merge and CI on main, the
owner's four-step phone check (the PDF, what it prints, the Word version,
the page) and the print test on legal paper at the church. No token, email,
church id or member's name is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `4`; `89 passed in <t>s`; one commit. If the print test has not happened when the phone steps are done, ask the owner whether to wait for it or to record the phone check now (without row 5) and add the print test row in a second records PR.

- [ ] **Step 9 (agent, on the owner's yes): Push, open and merge the records PR**

Ask: "The printed bulletin PR 1 record is written (docs/ops-runbook.md only). May I push it and open its PR?" On the yes (not replayed):

```bash
git push origin claude/slice-2-plan-4q33le
gh pr create -R bbrown62450/church --base main --head claude/slice-2-plan-4q33le \
  --title "Runbook: printed bulletin PR 1 record" \
  --body "Records printed bulletin PR 1 (PR #<N>) in docs/ops-runbook.md → Printed bulletin PR 1 record: the merge, the owner's four-step phone check and the print test. No token, email, church id or member's name is recorded. Docs only.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
gh pr checks claude/slice-2-plan-4q33le -R bbrown62450/church --watch
```

**Expected:** the PR URL; every check passes. Then ask: "The records PR is green. May I merge it with a merge commit?" On the yes: `gh pr merge claude/slice-2-plan-4q33le --merge -R bbrown62450/church`. Report: "Printed bulletin PR 1 is live and recorded; <n> follow-ups. Next: the PR 2 plan (the Bulletin step and the settings)."

- [ ] **Step R (only if the release must come out): Revert**

Code only (no data or schema to undo; nothing was stored). On the owner's yes for each outward command: a branch `claude/revert-printed-1` from `origin/main`, `git revert -m 1 --no-commit <merge sha>`, a commit "Revert printed bulletin PR 1 (PR #<N>)" with the trailer, both suites (`1335 passed, 16 skipped`; `655 passed` in 83), a PR, CI, and the merge on the owner's yes; record it in the record. Review then shows the Word documents card only. The two packages stay installed on Railway until its next deploy from the reverted requirements, which removes them; harmless either way.

Expected counts after this task: backend `1363 passed, 16 skipped` on `main`; frontend `660 passed` in 83 files. The records PR adds no test.

---
## Build notes

<<BUILDNOTES>>

## Spec coverage

| Owner answer or S item | Task(s) and tests |
|---|---|
| 1. Print-ready PDF in the folded legal-landscape booklet layout | T2 `test_the_pdf_is_legal_landscape_sheets_in_booklet_order`, `test_a_longer_service_takes_more_sheets_and_stays_a_multiple_of_four`; T1 `test_the_booklet_pads_to_whole_sheets_with_blanks_before_the_back_page` (5 cases), `test_the_sides_fold_into_reading_order`; T8 steps 1 and the print test |
| 1. An editable Word version | T2 `test_the_word_file_is_the_same_booklet_in_reading_order`; T3 `test_the_word_file_downloads_too`; T5 "downloads the PDF … names the Word version itself …"; T8 step 3 |
| 2. Standing and weekly fields (PR 2): placeholders now, the sample's leaders and stars as defaults | T1 `test_the_order_of_worship_follows_the_outline_with_the_sample_s_parts`, `test_each_element_prints_as_the_sample`, `test_the_cover_and_the_back_page`; clarifications 7-9, 15 |
| 3. Announcements (PR 2) | the back page's placeholders (T1 `test_the_cover_and_the_back_page`); S "Data model" |
| 4. Cover picture (PR 3) | the picture's place with the reading and the date (T1, T2 side 1 text); S "Data model" |
| 5. Full text in step 1's translation with a credit line | T3 `test_the_pdf_downloads_with_the_file_headers_and_the_readings_text`, `test_a_translation_not_offered_here_prints_in_the_church_s` (3 requests), `test_no_readings_fetch_nothing`; T1 `test_a_reading_prints_as_paragraphs`, the unavailable text in `test_each_element_prints_as_the_sample`; T4 `printedRequest` (the draft's translation); T5 (the body's translation) |
| 5. Pasting licensed text (PR 2) | S "Scripture text"; out of scope |
| 6. One version | clarification 4 (the PDF is the imposed booklet; no mailing variant) |
| 7. Keep both Word copies; a third download | T5 "shows the card after the Word documents …" (the heading order, the Word documents card unchanged); 5a-1's documents tests unchanged and passing |
| 8. The Bulletin step and the settings panel (PR 2) | out of scope (S "Scope by PR") |
| 9. Three PRs; this one from what the app knows | the plan's scope; T7 Step 3 (no migration or `backend/db` path; 5 revisions) |
| 10. A guided phone check and a print test | T8 Steps 2-6; `docs/manual-verification.md` "## Printed bulletin" (T6) |
| S API (route, body, headers, 429, isolation, 422s, log) | T3 the ten tests; `test_route_guards.py` and `test_openapi_contract.py` unchanged and passing |
| S "Fonts" (standard Times, "?" outside Windows-1252) | T2 `test_characters_the_standard_fonts_cannot_print_become_a_question_mark` |
| S "What prints where" (order, Leader/People, Assurance, communion, custom elements, empty slots) | T1 `test_each_element_prints_as_the_sample`, `test_what_is_missing_is_left_out_or_a_placeholder`, `test_communion_prints_after_the_second_hymn`; T2 `test_the_pdf_prints_the_service_and_its_readings` |
| Layering (no FastAPI or Streamlit below the API) | T2 `test_no_streamlit_in_core.py` (three modules added); T7 imports grep |
| OpenAPI and types regenerated | T3 Step 4; T7 Step 3; `test_openapi_contract.py` |
| F §4.8, §4.9 (44 px, descriptions, status lines) | T5 "shows the card …" (`h-11`, descriptions); the status lines as the Word documents card's |

S items **not** in PR 1 (owner answer 9): the Bulletin step, the settings panel and its route, `churches.settings["bulletin"]`, the draft's `bulletin` (v3), `services.bulletin` and migration `0006_services_bulletin`, carry forward, pasted reading text, the cover picture, `bulletin_images` and migration `0007_bulletin_images`.

## Questions for the owner

Your answers of 2026-10-02 (1-10) are binding and already in the plan. These are the choices this plan makes where you did not say; each is written as recommended.

1. **Where the new card goes** (clarification 2): Review & send keeps "Still to do", the Archive card and the Word documents card as they are; the new **Printed bulletin** card comes last. Recommended: accept.
2. **The card's wording** (clarifications 3, 17): heading "Printed bulletin"; "The folded booklet: the cover, the order of worship with the readings in full, and the announcements."; "For now, the church's details, the people who lead, the music and the announcements print as [placeholders]."; **Download printed bulletin** (filled) with "Ready to print on legal paper: both sides, flipped on the short edge, then folded in half."; **Download Word version** (outlined) with "The same bulletin as a Word file, to change before printing."; "Preparing…", then "Still working…" after 8 seconds; off without a date or with a readings problem, with the existing messages; the existing save tip after a download. Recommended: accept.
3. **The PDF is arranged for printing** (clarification 4): each legal page holds two booklet pages in the order the fold needs, so on your phone the first page shows the announcements and the cover side by side. Extra pages needed to fill the last sheet are blank and sit just before the announcements, which stay on the back. The Word version reads in order. Recommended: accept (one version, your answer 6).
4. **What the service prints, and in what order** (clarification 5): the app's order of worship with your sample's additions (Prelude; Welcome and Announcements; Gloria Patri after the Assurance; Offering Our Gifts and the Doxology before the Offertory Prayer; Postlude) under "GATHERING FOR WORSHIP", "RECEIVING THE WORD", "RESPONDING TO THE WORD" and "SENDING OUT TO SERVE"; "PRAYERS OF THE PEOPLE/THE LORD'S PRAYER" as a heading only, without the prayers' text; the communion liturgy after the second hymn when it is on. Recommended: accept.
5. **The readings are "FIRST READING" and "NEW TESTAMENT READING"** (clarification 6), as in the Word copies since 5a, not "OLD TESTAMENT READING" as in your sample (the first reading is sometimes not from the Old Testament). Recommended: accept.
6. **Who leads, until your settings arrive in PR 2** (clarification 7): "[Liturgist]" from the Welcome through the First Reading, "[Worship leader]" from the New Testament Reading through the Offertory Prayer, "[Organist]" on the Prelude and Postlude; the header reads "[Worship leader], Worship Leader", "[Liturgist], Liturgist", "[Organist], Organist", with "[Service time]" across from the date. Recommended: accept.
7. **Stars and fixed texts until PR 2** (clarifications 8, 9): stars on the three hymns, both sung responses, the Affirmation of Faith and the Benediction, and "*Congregation stands if able" at the end; the Gloria Patri in its traditional words ("Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the beginning, is now, and ever shall be, world without end. Amen, amen."); the Apostles' Creed in the traditional wording your sample uses; the Doxology by name only; your offering note and "Please remain seated to the end of the Postlude" wait for PR 2's settings. Recommended: accept.
8. **The readings' text** (clarification 10): printed in full in the translation chosen on step 1 (if this app no longer offers it, your church's default), followed by "Scripture readings are from the {translation}." (for example "the World English Bible (WEB)"); a reading the Bible service cannot supply prints "[Reading text unavailable]" and the file still downloads (PR 2 adds a box to paste your own). Recommended: accept.
9. **The date and the file names** (clarification 12): the booklet writes "October 4, 2026" (as your sample), the files are `printed_bulletin_October_04_2026.pdf` and `printed_bulletin_October_04_2026.docx`. Recommended: accept.
10. **The cover and the back page until PR 2 and PR 3** (clarification 15): your church's name, a framed box for the picture with the sermon reading and the date in it, then "[Street address]", "[City, State ZIP]", "[Phone]", "[Email]", "[Website]", "FB: [Facebook name]"; the back page has "ANNOUNCEMENTS", the date, "Ushers/Counters: [Names]", "Deacon of the Week: [Name]", "Coffee Hour: [Name]", "THIS WEEK'S ACTIVITIES AT A GLANCE" with "[Activities]", "PRAYERS AND CONCERNS" with "[Prayer concerns]", and "ITEMS FOR COLLECTION" with "[Collection items]". Recommended: accept.
11. **Type** (clarifications 13, 14): Times 11 point with the contact lines in a plain sans type, as your sample; the PDF uses the fonts every printer has rather than carrying its own (a rare character outside them prints as "?"). The Word version uses Times New Roman on 7 x 8.5 inch pages; to print it as a booklet use Word's "Book fold" or the printer's booklet setting, or print the PDF. Recommended: accept.
12. **Printed bulletin downloads count toward the Bible text limit** (clarification 11): each download fetches the two readings, which counts like opening them on step 1 (60 passage parts per person every 5 minutes, far above normal use); past it, the existing "Too many requests. Try again in {n} seconds." message shows. Recommended: accept.

Owner steps still to come: the plan's approval; the draft PR on your yes and ready on your yes (T7); the merge on your yes, then four phone checks one at a time, the print test at the church, and the records PR (T8).
