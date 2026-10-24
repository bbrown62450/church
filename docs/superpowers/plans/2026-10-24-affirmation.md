# Affirmation of Faith

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** Ship the owner's Affirmation of Faith decisions of 2026-10-24 (1, 2 and 6; binding): in the Liturgy step the Affirmation becomes a card with an "Include Affirmation of Faith" switch and a choice of the Apostles' Creed, the Nicene Creed or "Your own text" (a box like a prayer card's); off, nothing of it is printed or emailed; Settings → Liturgy holds the church's default (admins change it, members read it). Old drafts and saved services print exactly as today. Formatting is the next PR and is not built here. It ships as **two PRs** (owner answer A): **Affirmation PR A**, the server side with migration `0010_services_affirmation`, merged and confirmed live first; then **Affirmation PR B**, the pages.

**Architecture:**
- **Part 1, Affirmation PR A (T1-T6).** T1: a pure module `backend/affirmation.py` (the two creeds, ELLC's credit line, `Affirmation`, `read`, `resolve_default`) and what prints: `worship_service.build_docx`, `printed_bulletin.order_of_worship` (so the printed PDF and Word; the Nicene Creed one paragraph per sense line with a hanging indent), `service_output.ResolvedService`, `usecases.documents` (so the email's attachments), and the input's cleaning. T2: saving and the API: migration `0010_services_affirmation` (one nullable JSON column), the archive's storage (NULL is the Apostles' Creed; a PUT without it keeps the saved one), `ServiceDraft`/`ServiceOut.affirmation`, `GET /liturgy/config`'s `affirmation` (the card's data; the outline item stays the landmark it is today, so today's pages keep their row), the church default in `churches.settings` (`GET`/`PATCH /church`, admins only), the README routine, the OpenAPI snapshot, `schema.d.ts` and the frontend test fixtures (no page changes). T3: planted violations. T4: verification, including today's frontend against the new API types. T5: the owner's routine before the merge (migration). T6: the draft PR, CI, the merge, the after-deploy check, a minimal phone check and PR A's record.
- **Part 2, Affirmation PR B (T7-T11).** T7: the draft (version 5, its migration, the default, the transitions, the payload and fingerprints) and the card on the Liturgy step. T8: Settings → Liturgy's default card and the summary line. T9: planted violations. T10: verification. T11: the draft PR, CI, the merge, the after-deploy check, the phone check of the card and the record.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, python-docx, reportlab (backend, pytest); Next.js 16, React 19, Tailwind 4, shadcn on Base UI, zod, TanStack Query, Vitest (frontend).

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-24-affirmation-design.md` (written with this plan; the owner answered its "Questions for the owner" on 2026-10-24).
- Decisions ("D"): `docs/superpowers/specs/2026-10-24-affirmation-and-formatting-decisions.md` (binding; it records the decisions and the owner's answers A to D; rides along in PR A).
- Model plans: `docs/superpowers/plans/2026-10-20-pew-voices.md`, `docs/superpowers/plans/2026-10-22-theme-pr1.md`.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `f654dcf`, whose code is `4fdd605`'s, 2026-10-24): local `backend/tests` `2251 passed, 49 skipped`; CI's backend command (`python -m pytest -q`, which `pytest.ini` points at `backend/tests` and `streamlit_tests`) `2282 passed, 49 skipped` (`streamlit_tests` is 31); CI's Postgres command (`python -m pytest -m postgres -q`) collects 49 and deselects 2282; frontend `1122 passed` in 119 files; typecheck and lint clean; production at `0009_memberships_one_owner`; `docs/ops-runbook.md` holds the Theme PR 1 record, not yet on `main` (it rides along in PR A).

## Global Constraints

"T<n>" means Task n. `<repo>` is the GitHub repository of this checkout's `origin` (owner/name), `<api>` the production API's address, `<app>` the production app's address, `<scratch>` the session's scratchpad path and `<NA>`, `<NB>` the numbers of PR A and PR B; write each out when running a command, never into a committed file.

### Commands and process
- Run commands from the repo root; the working directory resets between commands. Backend: `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -1`. Frontend as `(cd frontend && …)`: one file `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "Test Files|Tests ")`, the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`, and `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. A time in an expected output is written `<t>`. No foreground `sleep`.
- **Two PRs from one branch** (owner answer A). Part 1's commits (T1, T2) are PR A. PR B is opened only after PR A is merged and its after-deploy check passed (T6): the branch is first fast-forwarded to `main` (T6 Step 8), and Part 2's commits (PR A's record, T7, T8) are PR B. Never open PR B while PR A is unmerged: the API from before PR A refuses a body with `affirmation` (`ServiceDraft` forbids unknown fields, 422), and PR B's pages always send it.
- **One migration, `0010_services_affirmation`**, in PR A (S "Why a migration"); no new package, no new variable, no new `components/ui` file.
- Generated files are never edited by hand: `frontend/src/lib/api/openapi.json` (`.venv/bin/python backend/scripts/export_openapi.py`) and `frontend/src/lib/api/schema.d.ts` (`(cd frontend && npm run gen:api)`; CI fails if it drifts), both regenerated in PR A (T2). `backend/tests/fixtures/shared/liturgy_outline.json` does not change: the outline does not.
- Branch `claude/slice-2-plan-4q33le`. Stage files by name (`git add <paths>`); never `git add -A`; nothing under `.claude/` is staged.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing tests first and see them fail as quoted.
- **Backup push after every task**: `git push origin claude/slice-2-plan-4q33le` (never `--force`, never a rebase; if rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`.
- `main` is protected (`backend`, `backend-postgres`, `frontend`). Never open, mark ready or merge a PR without the owner's explicit yes for that step. Never touch production, its database or a secret: the owner runs the SQL (T5, T6).
- **Migration SQL in chat** (owner rule): the agent never pastes SQL into the chat as a block. It says in plain words what a step does and points to its place in `backend/migrations/README.md` ("Before 0010_services_affirmation").
- No em dashes in user-facing copy or in prose for the owner. No church id, email address, invite code, token, key, database URL or real person's name in any doc, commit, test or record. Never log an Affirmation's text (only ids, sizes and durations are logged, as today).
- The frozen Streamlit files (`app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`, `streamlit_tests/`) are not edited.

### How the file directives below read
As in the earlier plans: **Create `path`:** the block is the whole new file; **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written (T1, T2, then T7, T8). A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted or moved.

### Baselines and counts
- Starting baseline: local `backend/tests` **2251 passed, 49 skipped**; frontend **1122 passed in 119 files**; typecheck and lint clean. If either differs, stop and ask.
- Two kinds of backend count, kept apart. **Local** is `.venv/bin/python -m pytest -q backend/tests` (what every task runs). **CI** is what GitHub runs from the repo root: the `backend` job's `python -m pytest -q` also runs `streamlit_tests` (31, unchanged here), and the `backend-postgres` job's `python -m pytest -m postgres -q` deselects every test of both folders that is not Postgres-only.
- Planned cumulative counts (observed in the replay):

  | After | Local `backend/tests` | Frontend |
  |---|---|---|
  | T1 | +20 (`test_affirmation.py`, a new file) → **2271 passed, 49 skipped** | unchanged |
  | T2 | +17 (`test_api_affirmation.py`, a new file, 12; `test_migrations.py` +5) and +1 Postgres-only (`test_migrations.py`, skipped here) → **2288 passed, 50 skipped** | unchanged: **1122 in 119 files** (only the test fixtures and the generated types change) |
  | T7 | unchanged | +15 (`affirmation.test.ts` 8 and `affirmation-card.test.tsx` 6, new files; `migrate.test.ts` +1) → **1137 in 121 files** |
  | T8 | unchanged | +4 (`affirmation-default-card.test.tsx`, a new file) → **1141 in 122 files** |

  | CI on | `backend` job | `backend-postgres` job | `frontend` job |
  |---|---|---|---|
  | `main` before | 2282 passed, 49 skipped | 49 passed, 2282 deselected | 1122 in 119 files |
  | PR A | **2319 passed, 50 skipped** | **50 passed, 2319 deselected** | **1122 in 119 files** |
  | PR B | **2319 passed, 50 skipped** (no backend change) | **50 passed, 2319 deselected** | **1141 in 122 files** |

## Owner decisions

1. **The Affirmation of Faith decisions of 2026-10-24** (D 1, 2 and 6; "all recommended"; binding): the card with the switch and the three choices; Settings → Liturgy holds the default; the Apostles' and Nicene Creeds built in, anything else pasted as own text; the copyright terms of the exact wordings checked and cited before they ship (S "Copyright findings"); this change comes after the Theme PR 1 phone check and before formatting.
2. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.
3. **The owner's answers of 2026-10-24** ("all recommended"; binding; recorded in D):
   - **A. Two PRs.** Affirmation PR A is the server side and migration `0010_services_affirmation` (T1-T2 and the README routine), merged and confirmed live first; Affirmation PR B is the pages (T7-T8). Each part has its own verification, pre-merge note, PR body, CI counts, merge, after-deploy check, phone check and runbook record; PR A's phone check is minimal (the app still saves and downloads as before), PR B's covers the card. PR A is safe with today's frontend (T4 Step 2 shows it); PR B is guarded if it ever runs ahead (clarification 10).
   - **B. The Apostles' Creed keeps today's traditional wording** (the 1662 Book of Common Prayer text: "Holy Ghost", "quick and the dead").
   - **C. The Nicene Creed says "and the Son"** ("who proceeds from the Father and the Son,"), without ELLC's brackets.
   - **D. No "leave it out" church default now.** The default is a creed or the church's own text, always included; a service switches it off.

## Spec clarifications

The owner's answers win over S; the code wins over both where they disagree. **[owner-visible]** items change what someone sees compared with a plain reading of the decisions.

1. **[owner-visible] The Word files print the creed's name, as today** ("Apostles' Creed", "Nicene Creed"), not its text; own text prints as typed. Only the printed bulletin (PDF and Word) prints a creed's words. This keeps an old service's Word file byte for byte as today (S "What prints").
2. **[owner-visible] Own text prints in bold** in the printed bulletin, like the Apostles' Creed today and the Prayer of Confession: it is read together. The Word files print it plain, as their other prayers.
3. **[owner-visible] Own text left blank prints nothing**, as switched off; the card says "Nothing prints until you type it." and the summary "(nothing typed yet)".
4. **The email follows its attachments.** `bulletin_email` composes a plain message and attaches the Word file and/or the printed PDF built by `usecases.documents`; the message never names the Affirmation, so the email needs no code of its own. A test builds the real attachments (`email._attachments`).
5. **A PUT without `affirmation` keeps the saved choice** (the bulletin's rule), so a page open from before PR B cannot erase a choice; PR B's pages always send it (`serviceBody`), and the fingerprint payload leaves out the Apostles' Creed switched on, so a draft saved before the change stays "Saved".
6. **The draft's 4 → 5 migration** gives the Apostles' Creed switched on: origin "archive" for a draft that is a saved service, "default" for an unsaved one (it follows the church default, the Apostles' Creed until an admin changes it).
7. **One leave guard on Settings → Liturgy.** `LeaveGuard` keeps one active guard per page, so the page now owns it and both forms report their unsaved state (`onDirtyChange`); `LiturgyPromptsPage` keeps its own guard when rendered alone.
8. **The default's toast** reads "Affirmation of Faith default saved." (`useUpdateChurch` takes a `savedMessage`; the Church page keeps "Profile saved.").
9. **The outline does not change** (owner answer A; this replaces the earlier draft's `kind: "affirmation"`). `GET /liturgy/config`'s `affirmation_of_faith` item stays `kind: "landmark"`, `value_source: "fixed"`, `fixed_text: "Apostles' Creed"`, so a page from before PR B still shows its row "Affirmation of Faith · Apostles' Creed" (today's Liturgy step renders nothing for an unknown kind). PR B's Liturgy step shows the card in that item's place whenever the config carries `affirmation`.
10. **[owner-visible only if PR B ran ahead of PR A] PR B's guards.** Built: the Liturgy step shows today's row instead of the card, and Settings → Liturgy leaves the default card out, when `GET /liturgy/config` has no `affirmation` (an API from before PR A); tests pin both. Not built: sending `affirmation` only when the config carries it. The four places that build a body (`serviceBody`, used by the Word files, the printed bulletin, the email and saving) take only the draft, and threading the config into each is not a small change; the order of the two PRs (Global Constraints) and T11 Step 1's check that production's `/openapi.json` names `ServiceAffirmation` stand in for it.
11. **[owner-visible] The Nicene Creed's sense lines wrap with a hanging indent** (review fix 6): in the printed bulletin (PDF and Word) each sense line is its own paragraph, indented 0.5 in after its first line (the existing "hanging" style the People and Leader lines use), so a line too long for the page wraps under itself; "Show creed text" on the phone does the same (`pl-4 -indent-4`). The Apostles' Creed stays one paragraph, exactly as today.

### Assumptions that turned out false while planning
- "Prefer no migration": a saved service needs somewhere to keep its choice; `services.liturgy` is filtered to the eight sections by every reader and the frozen Streamlit app reads it, so the 0006 pattern (a new nullable column) is the safe one. The church default needs no migration.
- The Word files do not print the Apostles' Creed's text, only its name; the printed bulletin prints the text.
- The emailed bulletin prints no liturgy in the message itself; only its attachments do.
- Settings → Liturgy holds only the AI prompts (`/church/liturgy-prompts`); church-wide values live in `churches.settings` through `PATCH /church`, so the default goes there and its card sits on the Liturgy page.
- The creed never went to the AI: neither "Review service" nor "Hear it from the pews" sends it, and this change keeps it so (S "AI interplay").
- A new outline kind is not safe for today's pages: the Liturgy step renders nothing for a kind it does not know, so the earlier draft's `kind: "affirmation"` would have dropped the Affirmation row from today's pages between PR A and PR B (clarification 9).
- PR A cannot leave the frontend untouched: CI regenerates `schema.d.ts` and fails on drift, and the frontend test fixtures are typed by it, so the new required response fields need the fixtures' three additions (T2). No page changes.
- ELLC's notice gives © 1998 while *Praying Together* is dated 1988; the app prints ELLC's own wording.
- A Turbopack build fails when `frontend/node_modules` is a symlink; a hard-linked copy works (replay only).

### Risks
- **The migration** (expand-only, one nullable column): T5's routine before PR A's merge; a failed `alembic upgrade head` leaves the previous release serving.
- **A creed's words** print in every bulletin that chooses it: `test_affirmation.py` pins both texts (line count, first, last and line 26 of the Nicene Creed, the Apostles' Creed's length and ends).
- **A stale page** (open from before PR B) sends no `affirmation`: its downloads print the Apostles' Creed, its PUT keeps the saved choice, and its outline keeps today's row.
- **PR B ahead of PR A** would fail every download and save with a 422 (clarification 10): the order of the PRs prevents it.

## File Structure

**Created (PR A):** `backend/affirmation.py`, `backend/migrations/versions/0010_services_affirmation.py`, `backend/tests/test_affirmation.py`, `backend/tests/test_api_affirmation.py`.

**Modified (PR A):** backend `worship_service.py`, `printed_bulletin.py`, `service_output.py`, `usecases/archive.py`, `usecases/documents.py`, `usecases/church_profile.py`, `usecases/church_admin.py`, `api/schemas.py`, `api/routes/liturgy.py`, `api/routes/me.py`, `db/models.py`, `migrations/README.md`, and the tests `test_no_streamlit_in_core.py`, `test_migrations.py`, `test_schema_check.py`, `test_api_app.py`, `test_services_postgres.py`, `test_api_me.py`, `test_api_invites.py`, `test_api_churches.py`, `test_api_church_profile.py`; frontend `test/fixtures/index.ts`; generated `frontend/src/lib/api/openapi.json`, `frontend/src/lib/api/schema.d.ts`. Riding along: this plan, the spec, the decisions doc and `docs/ops-runbook.md` (the Theme PR 1 record).

**Created (PR B):** `frontend/src/lib/liturgy/affirmation.test.ts`, `frontend/src/components/builder/liturgy/affirmation-card.tsx`, `frontend/src/components/builder/liturgy/affirmation-card.test.tsx`, `frontend/src/components/settings/affirmation-default-card.tsx`, `frontend/src/components/settings/affirmation-default-card.test.tsx`.

**Modified (PR B):** frontend `lib/api/types.ts`, `lib/draft/schema.ts`, `migrate.ts`, `mapping.ts`, `status.ts`, `store.ts`, `context.tsx`, `lib/liturgy/cards.ts`, `defaults.ts`, `summary.ts`, `lib/documents.ts`, `lib/queries/church.ts`, `components/builder/liturgy/liturgy-step.tsx`, `outline-landmark.tsx`, `liturgy-summary-block.tsx`, `components/settings/liturgy-prompts-page.tsx`, `app/(signed-in)/(church)/settings/liturgy/page.tsx`, and the tests `schema.test.ts`, `migrate.test.ts`, `store.test.ts`, `mapping.test.ts`, `documents.test.ts`, `liturgy-step.test.tsx`, `builder-shell.test.tsx`, `liturgy-prompts-page.test.tsx`; `docs/ops-runbook.md` (PR A's record, T6 Step 8).

# Part 1: Affirmation PR A (the server side and migration 0010)

### Task 1: The module and what prints (S "What prints", "Data shape", "Copyright findings"; clarifications 1-4, 11)

**Files:** Create `backend/affirmation.py`, `backend/tests/test_affirmation.py`. Modify `backend/tests/test_no_streamlit_in_core.py`, `backend/service_output.py`, `backend/worship_service.py`, `backend/printed_bulletin.py`, `backend/usecases/archive.py` (the input only), `backend/usecases/documents.py`.

- [ ] **Step 1: Write the failing tests**

<!-- directives:T1_TESTS -->
**Create `backend/tests/test_affirmation.py`:**

````
"""The Affirmation of Faith (affirmation spec, 2026-10-24): the module, and
what the Word files, the printed bulletin (PDF and Word) and the email's
attachments print for each choice, switched off, and for a service from
before the change (no affirmation sent): exactly as today."""
from datetime import date
from io import BytesIO

import pytest
from docx import Document
from docx.shared import Inches
from pypdf import PdfReader

import affirmation as af
import printed_bulletin as pb
import worship_service
from service_output import ResolvedService, render_docx
from usecases import archive, documents
from usecases import email as email_usecase

OWN = "We trust in God the Holy Spirit,\neverywhere the giver and renewer of life."
# Today's two printed lines, written out (printed_bulletin before this change).
TODAY_HEADING = "*AFFIRMATION OF FAITH:  “The Apostles’ Creed”"
TODAY_CREED_START = "I believe in God, the Father almighty, Maker of heaven and earth"


def test_the_creeds_are_the_texts_checked_for_this_change():
    assert af.APOSTLES_CREED.startswith(TODAY_CREED_START)
    assert af.APOSTLES_CREED.endswith("the resurrection of the body; and the life everlasting. Amen.")
    assert "\n" not in af.APOSTLES_CREED and len(af.APOSTLES_CREED) == 611
    lines = af.NICENE_CREED.split("\n")
    assert len(lines) == 32                                    # ELLC's 32 sense lines
    assert lines[0] == "We believe in one God," and lines[-1] == "and the life of the world to come. Amen."
    assert lines[25] == "who proceeds from the Father and the Son,"   # line 26, without ELLC's brackets
    assert "[" not in af.NICENE_CREED and "\u2014" not in af.NICENE_CREED
    assert af.NICENE_CREDIT == ("English translations of the Nicene Creed, © 1998 English Language Liturgical "
                                "Consultation (ELLC), and used by permission. www.englishtexts.org")
    assert pb.APOSTLES_CREED is af.APOSTLES_CREED


@pytest.mark.parametrize("raw, expected", [
    (None, af.Affirmation()),
    ("nicene", af.Affirmation()),
    ({}, af.Affirmation()),
    ({"include": False, "choice": "nicene", "text": "x"}, af.Affirmation(False, "nicene", "")),
    ({"include": "no", "choice": "own", "text": OWN}, af.Affirmation(True, "own", OWN)),
    ({"choice": "brief_statement", "text": OWN}, af.Affirmation(True, "apostles", "")),
    ({"choice": "own", "text": 5}, af.Affirmation(True, "own", "")),
])
def test_read_is_tolerant(raw, expected):
    assert af.read(raw) == expected


def test_to_json_prints_and_the_church_default():
    assert af.Affirmation().to_json() == {"include": True, "choice": "apostles", "text": ""}
    assert af.Affirmation(True, "nicene", "kept?").to_json() == {"include": True, "choice": "nicene", "text": ""}
    assert [a.prints() for a in (af.Affirmation(), af.Affirmation(False), af.Affirmation(True, "own", " \n"),
                                 af.Affirmation(True, "own", OWN))] == [True, False, False, True]
    assert af.resolve_default(None) == af.resolve_default({}) == af.resolve_default("x") == af.Affirmation()
    assert af.resolve_default({"default_affirmation": {"choice": "own", "text": OWN, "include": False}}) == \
        af.Affirmation(True, "own", OWN)


# --- the Word files ---

def _docx(affirmation=None) -> list[str]:
    kwargs = {} if affirmation is None else {"affirmation": affirmation}
    content = worship_service.build_docx(
        occasion="", date_display="October 04, 2026", hymns_by_slot={}, liturgy={}, ot_ref=None, nt_ref=None,
        custom_elements=[{"label": "Anthem", "text": "", "insert_after": "affirmation_of_faith"}], **kwargs)
    return [p.text for p in Document(BytesIO(content)).paragraphs]


def _after_sermon(paragraphs: list[str]) -> list[str]:
    return paragraphs[paragraphs.index("[Sermon title]") + 2:]


def test_the_word_file_for_each_choice():
    today = _after_sermon(_docx())
    assert today[:4] == ["Affirmation of Faith", "Apostles' Creed", "", "Anthem"]
    assert _docx(af.Affirmation()) == _docx()                                   # the default is today's file
    assert _after_sermon(_docx(af.Affirmation(True, "nicene")))[:4] == [
        "Affirmation of Faith", "Nicene Creed", "", "Anthem"]
    assert _after_sermon(_docx(af.Affirmation(True, "own", OWN)))[:4] == ["Affirmation of Faith", OWN, "", "Anthem"]


@pytest.mark.parametrize("off", [af.Affirmation(False, "apostles"), af.Affirmation(False, "own", OWN),
                                 af.Affirmation(True, "own", "  ")])
def test_switched_off_or_blank_own_text_prints_nothing_in_the_word_file(off):
    paragraphs = _docx(off)
    assert "Affirmation of Faith" not in paragraphs and "Apostles' Creed" not in paragraphs
    assert OWN not in paragraphs
    assert _after_sermon(paragraphs)[0] == "Anthem"                              # its custom element still prints


def test_both_word_copies_follow_the_choice():
    resolved = ResolvedService(service_date=date(2026, 10, 4), affirmation=af.Affirmation(False))
    for variant in ("bulletin", "pastor"):
        assert "Affirmation of Faith" not in [p.text for p in Document(BytesIO(render_docx(resolved, variant))).paragraphs]


# --- the printed bulletin ---

def _lines(a=None) -> list[pb.Line]:
    resolved = ResolvedService(service_date=date(2026, 10, 4), **({} if a is None else {"affirmation": a}))
    return pb.order_of_worship(pb.PrintedService(church_name="Grace", resolved=resolved))


def _affirmation_lines(lines: list[pb.Line]) -> list[tuple[str, str]]:
    start = next(i for i, line in enumerate(lines) if line.text.startswith("SERMON:")) + 1
    end = next(i for i, line in enumerate(lines) if "PRAYERS OF THE PEOPLE" in line.text)
    return [(line.style, line.text) for line in lines[start:end]]


def test_the_printed_bulletin_for_each_choice():
    assert _affirmation_lines(_lines()) == [("element", TODAY_HEADING), ("bold", af.APOSTLES_CREED)]
    assert _lines(af.Affirmation()) == _lines()
    # The Nicene Creed: one paragraph per sense line, with a hanging indent (a wrapped line reads as one).
    assert _affirmation_lines(_lines(af.Affirmation(True, "nicene"))) == [
        ("element", "*AFFIRMATION OF FAITH:  “The Nicene Creed”"),
        *[("hanging", sense) for sense in af.NICENE_CREED.split("\n")], ("credit", af.NICENE_CREDIT)]
    assert _affirmation_lines(_lines(af.Affirmation(True, "own", OWN))) == [
        ("element", "*AFFIRMATION OF FAITH:"), ("bold", OWN)]
    creed = [line for line in _lines(af.Affirmation(True, "nicene")) if line.style == "hanging"]
    assert len(creed) == 32 and all(span.bold for line in creed for span in line.spans)


def test_switched_off_prints_nothing_in_the_printed_bulletin_and_loses_its_star():
    for off in (af.Affirmation(False), af.Affirmation(True, "own", "")):
        assert _affirmation_lines(_lines(off)) == []
    on = pb.order_of_worship(pb.PrintedService(church_name="Grace", resolved=ResolvedService(
        service_date=date(2026, 10, 4)), settings=pb.BulletinSettings(starred=frozenset({"affirmation_of_faith"}),
                                                                       stand_note="Please stand.")))
    off = pb.order_of_worship(pb.PrintedService(church_name="Grace", resolved=ResolvedService(
        service_date=date(2026, 10, 4), affirmation=af.Affirmation(False)),
        settings=pb.BulletinSettings(starred=frozenset({"affirmation_of_faith"}), stand_note="Please stand.")))
    assert on[-1].text == "*Please stand." and all("Please stand." not in line.text for line in off)


# --- the files as the routes and the email build them ---

@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email="pastor@example.com"))


def _input(a=None) -> archive.ServiceInput:
    return archive.ServiceInput(service_date=date(2026, 10, 4), affirmation=a)


def _pdf_text(content: bytes) -> str:
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(BytesIO(content)).pages)


def _docx_text(content: bytes) -> str:
    return "\n".join(p.text for p in Document(BytesIO(content)).paragraphs)


def _printed(church, a, fmt):
    return documents.build_printed(church, _input(a), fmt, None, charge=lambda n: None).content


def test_the_downloads_for_each_choice(church):
    assert "Apostles' Creed" in _docx_text(documents.build_document(church, _input(), "bulletin").content)
    nicene = _pdf_text(_printed(church, af.Affirmation(True, "nicene"), "pdf"))
    assert "AFFIRMATION OF FAITH: “The Nicene Creed” We believe in one God," in nicene
    assert "Consultation (ELLC), and used by permission." in nicene
    own = _docx_text(_printed(church, af.Affirmation(True, "own", OWN), "docx"))
    assert OWN in own
    today = _pdf_text(_printed(church, None, "pdf"))
    assert "AFFIRMATION OF FAITH: “The Apostles’ Creed” I believe in God" in today


def test_the_printed_word_file_gives_each_nicene_sense_line_a_hanging_indent(church):
    paragraphs = Document(BytesIO(_printed(church, af.Affirmation(True, "nicene"), "docx"))).paragraphs
    first = next(p for p in paragraphs if p.text == "We believe in one God,")
    last = next(p for p in paragraphs if p.text == "and the life of the world to come. Amen.")
    for p in (first, last):
        fmt = p.paragraph_format
        assert (fmt.left_indent, fmt.first_line_indent) == (Inches(0.5), Inches(-0.5))
        assert all(run.bold for run in p.runs)


def test_switched_off_prints_nothing_in_any_download_or_the_email(church):
    off = af.Affirmation(False, "nicene")
    assert "Affirmation of Faith" not in _docx_text(documents.build_document(church, _input(off), "pastor").content)
    assert "AFFIRMATION OF FAITH" not in _pdf_text(_printed(church, off, "pdf"))
    assert "AFFIRMATION OF FAITH" not in _docx_text(_printed(church, off, "docx"))
    files = email_usecase._attachments(church, _input(off), ["docx", "pdf"], None, lambda n: None)
    assert [f.filename for f in files] == ["worship_October_04_2026.docx", "printed_bulletin_October_04_2026.pdf"]
    assert "Affirmation of Faith" not in _docx_text(files[0].content)
    assert "AFFIRMATION OF FAITH" not in _pdf_text(files[1].content) and "We believe" not in _pdf_text(files[1].content)


def test_own_text_is_made_word_safe_and_trimmed(church):
    clean = archive.clean_input(_input(af.Affirmation(True, "own", "  Line one\r\nLine\x00 two  ")))
    assert clean.affirmation == af.Affirmation(True, "own", "Line one\nLine two")
    assert archive.clean_input(_input()).affirmation is None
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search, hymn_suggest, usecases.hymns, "
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review, "
            "service_output, worship_service, usecases.archive, usecases.documents, repos.services, hymn_usage, "
````

**with:**

````
            "token_bucket, integrations.budget, scripture_refs, scripture_fetcher, integrations.openai_client, hymn_search, hymn_suggest, usecases.hymns, "
            "affirmation, liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review, "
            "service_output, worship_service, usecases.archive, usecases.documents, repos.services, hymn_usage, "
````
<!-- /directives:T1_TESTS -->

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_affirmation.py 2>&1 | grep -m1 "^E "; .venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`
**Expected:**
```
E   ModuleNotFoundError: No module named 'affirmation'
1 failed, 2 passed in <t>s
```

- [ ] **Step 3: Write the module and the printing**

The two creeds are copied exactly (S "Copyright findings"; owner answers B and C): the Apostles' Creed is today's `printed_bulletin.APOSTLES_CREED`, moved; the Nicene Creed is ELLC's text from https://www.englishtexts.org/the-nicene-creed (read 2026-10-24), one line per ELLC sense line, line 26 "and the Son" without its brackets. The printed bulletin prints each Nicene sense line as its own paragraph in the existing "hanging" style (clarification 11).

<!-- directives:T1_IMPL -->
**Create `backend/affirmation.py`:**

````
"""The Affirmation of Faith (affirmation spec, 2026-10-24): what a service
says there and what the church's default is. Pure: standard library only.

- APOSTLES_CREED: the traditional wording the printed bulletin has always
  printed (the 1662 Book of Common Prayer text, public domain in the United
  States), one paragraph, unchanged so saved services print as before.
- NICENE_CREED and NICENE_CREDIT: the ELLC text (Praying Together), in its
  sense lines, "[and the Son]" printed without brackets (ELLC's note on line
  26), and the acknowledgement ELLC's guidelines ask for.
- Affirmation: {include, choice, text}; the default is the Apostles' Creed,
  included, with no text. `read` takes any stored or sent value tolerantly
  (anything not understood is the default), `to_json` is what is stored and
  answered, `prints` says whether anything prints.
- resolve_default: the church's default from churches.settings
  ["default_affirmation"] ({choice, text}); always included.
Never log an Affirmation's text (F §2.5).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal, Optional

Choice = Literal["apostles", "nicene", "own"]
CHOICES: tuple[str, ...] = ("apostles", "nicene", "own")
CHOICE_LABELS: dict[str, str] = {"apostles": "Apostles' Creed", "nicene": "Nicene Creed", "own": "Your own text"}
TITLE = "Affirmation of Faith"
TOGGLE_LABEL = "Include Affirmation of Faith"
SETTINGS_KEY = "default_affirmation"
OWN_TEXT_REQUIRED = "Type your church's own text, or choose a creed."

APOSTLES_CREED = (
    "I believe in God, the Father almighty, Maker of heaven and earth, and in Jesus Christ his only "
    "Son, our Lord; who was conceived by the Holy Ghost, born of the Virgin Mary, suffered under "
    "Pontius Pilate, was crucified, dead, and buried; he descended into hell; the third day he rose "
    "again from the dead; he ascended into heaven, and sitteth on the right hand of God the Father "
    "Almighty; from thence he shall come to judge the quick and the dead. I believe in the Holy "
    "Ghost; the holy catholic church; the communion of saints; the forgiveness of sins; the "
    "resurrection of the body; and the life everlasting. Amen.")

# https://www.englishtexts.org/the-nicene-creed, copied 2026-10-24.
NICENE_CREED = "\n".join((
    "We believe in one God,",
    "the Father, the Almighty,",
    "maker of heaven and earth,",
    "of all that is, seen and unseen.",
    "We believe in one Lord, Jesus Christ,",
    "the only Son of God,",
    "eternally begotten of the Father,",
    "God from God, Light from Light,",
    "true God from true God,",
    "begotten, not made,",
    "of one Being with the Father;",
    "through him all things were made.",
    "For us and for our salvation",
    "he came down from heaven,",
    "was incarnate of the Holy Spirit and the Virgin Mary",
    "and became truly human.",
    "For our sake he was crucified under Pontius Pilate;",
    "he suffered death and was buried.",
    "On the third day he rose again",
    "in accordance with the Scriptures;",
    "he ascended into heaven",
    "and is seated at the right hand of the Father.",
    "He will come again in glory to judge the living and the dead,",
    "and his kingdom will have no end.",
    "We believe in the Holy Spirit, the Lord, the giver of life,",
    "who proceeds from the Father and the Son,",
    "who with the Father and the Son is worshiped and glorified,",
    "who has spoken through the prophets.",
    "We believe in one holy catholic and apostolic Church.",
    "We acknowledge one baptism for the forgiveness of sins.",
    "We look for the resurrection of the dead,",
    "and the life of the world to come. Amen.",
))

# ELLC, "Guidelines for Reproducing ELLC Texts" (July 2017), "Acknowledgement".
NICENE_CREDIT = ("English translations of the Nicene Creed, © 1998 English Language Liturgical "
                 "Consultation (ELLC), and used by permission. www.englishtexts.org")

CREED_TEXT: dict[str, str] = {"apostles": APOSTLES_CREED, "nicene": NICENE_CREED}
CREED_CREDIT: dict[str, str] = {"apostles": "", "nicene": NICENE_CREDIT}
# The printed bulletin's title after "AFFIRMATION OF FAITH:" (its curly quotes and apostrophe, as today).
PRINTED_TITLE: dict[str, str] = {"apostles": "“The Apostles’ Creed”", "nicene": "“The Nicene Creed”"}


@dataclass(frozen=True)
class Affirmation:
    include: bool = True
    choice: Choice = "apostles"
    text: str = ""                  # the church's or member's own text; "" unless choice is "own"

    def prints(self) -> bool:
        """Something prints: switched on, and a creed or own text that is not blank."""
        return self.include and (self.choice != "own" or bool(self.text.strip()))

    def to_json(self) -> dict[str, Any]:
        return {"include": self.include, "choice": self.choice, "text": self.text if self.choice == "own" else ""}


DEFAULT = Affirmation()


def read(raw: object) -> Affirmation:
    """A stored or sent value, tolerantly: not an object (NULL included) is
    the default; a missing or non-boolean include is True; an unknown choice
    is the Apostles' Creed; a text that is not a string is ""."""
    if not isinstance(raw, Mapping):
        return DEFAULT
    include = raw.get("include")
    choice = raw.get("choice")
    text = raw.get("text")
    choice = choice if choice in CHOICES else "apostles"
    return Affirmation(include=include if isinstance(include, bool) else True, choice=choice,
                       text=text if choice == "own" and isinstance(text, str) else "")


def resolve_default(settings: Optional[Mapping[str, Any]]) -> Affirmation:
    """The church's default (always included): settings["default_affirmation"]
    read as `read` reads it, else the Apostles' Creed."""
    stored = read(settings.get(SETTINGS_KEY) if isinstance(settings, Mapping) else None)
    return Affirmation(include=True, choice=stored.choice, text=stored.text)
````

**In `backend/service_output.py`, replace:**

````
import scripture_refs

````

**with:**

````
import scripture_refs
from affirmation import Affirmation

````

**In `backend/service_output.py`, replace:**

````
    custom_elements: tuple[CustomElement, ...] = ()

````

**with:**

````
    custom_elements: tuple[CustomElement, ...] = ()
    affirmation: Affirmation = Affirmation()        # the affirmation spec; the default prints as before it

````

**In `backend/service_output.py`, replace:**

````
        include_communion=resolved.include_communion,
        custom_elements=[{"label": e.label, "text": e.text, "insert_after": e.insert_after}
````

**with:**

````
        include_communion=resolved.include_communion,
        affirmation=resolved.affirmation,
        custom_elements=[{"label": e.label, "text": e.text, "insert_after": e.insert_after}
````

**In `backend/worship_service.py`, replace:**

````

from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
````

**with:**

````

from affirmation import CHOICE_LABELS, Affirmation
from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS
````

**In `backend/worship_service.py`, replace:**

````
    custom_elements: Sequence[Mapping[str, Any]] = (),
) -> bytes:
````

**with:**

````
    custom_elements: Sequence[Mapping[str, Any]] = (),
    affirmation: Optional[Affirmation] = None,
) -> bytes:
````

**In `backend/worship_service.py`, replace:**

````
    after their anchor, which is emitted even when its item is absent.
    Returns the .docx bytes.
````

**with:**

````
    after their anchor, which is emitted even when its item is absent.
    The Affirmation of Faith (affirmation spec; None is the Apostles' Creed,
    as before) prints the creed's name, or own text as typed, and nothing
    when switched off or own text is blank.
    Returns the .docx bytes.
````

**In `backend/worship_service.py`, replace:**

````

    # 10. Affirmation of Faith
    doc.add_paragraph("Affirmation of Faith", style="Heading 2")
    doc.add_paragraph("Apostles' Creed")
    doc.add_paragraph()
    _add_custom_elements_after(doc, "affirmation_of_faith", custom)
````

**with:**

````

    # 10. Affirmation of Faith (the affirmation spec: off or blank own text prints nothing)
    faith = affirmation or Affirmation()
    if faith.prints():
        doc.add_paragraph("Affirmation of Faith", style="Heading 2")
        doc.add_paragraph(faith.text if faith.choice == "own" else CHOICE_LABELS[faith.choice])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "affirmation_of_faith", custom)
````

**In `backend/printed_bulletin.py`, replace:**

````

from bulletin_settings import GLORIA_PATRI, BulletinSettings
````

**with:**

````

import affirmation as af
from affirmation import APOSTLES_CREED  # noqa: F401 (printed_bulletin.APOSTLES_CREED, as before)
from bulletin_settings import GLORIA_PATRI, BulletinSettings
````

**In `backend/printed_bulletin.py`, replace:**

````
ROLE_TITLES = {"worship_leader": "Worship Leader", "liturgist": "Liturgist", "organist": "Organist"}

APOSTLES_CREED = (
    "I believe in God, the Father almighty, Maker of heaven and earth, and in Jesus Christ his only "
    "Son, our Lord; who was conceived by the Holy Ghost, born of the Virgin Mary, suffered under "
    "Pontius Pilate, was crucified, dead, and buried; he descended into hell; the third day he rose "
    "again from the dead; he ascended into heaven, and sitteth on the right hand of God the Father "
    "Almighty; from thence he shall come to judge the quick and the dead. I believe in the Holy "
    "Ghost; the holy catholic church; the communion of saints; the forgiveness of sins; the "
    "resurrection of the body; and the life everlasting. Amen.")

````

**with:**

````
ROLE_TITLES = {"worship_leader": "Worship Leader", "liturgist": "Liturgist", "organist": "Organist"}

````

**In `backend/printed_bulletin.py`, replace:**

````

def _section(title: str) -> Line:
````

**with:**

````

def _affirmation(s: BulletinSettings, a: af.Affirmation) -> list[Line]:
    """The Affirmation of Faith (affirmation spec): nothing when switched off
    or own text left blank; a creed's title and its text in bold (the Nicene
    Creed one paragraph per sense line, each with a hanging indent so a line
    that wraps reads as one line, then ELLC's credit line); own text as typed,
    in bold. The Apostles' Creed prints exactly as before the change."""
    if not a.prints():
        return []
    if a.choice == "own":
        return [_element(s, "affirmation_of_faith", "Affirmation of Faith:"), Line("bold", (Span(a.text, bold=True),))]
    text = af.CREED_TEXT[a.choice]
    words = ([Line("bold", (Span(text, bold=True),))] if "\n" not in text
             else [Line("hanging", (Span(sense, bold=True),)) for sense in text.split("\n")])
    lines = [_element(s, "affirmation_of_faith", "Affirmation of Faith:", Span("  "),
                      Span(af.PRINTED_TITLE[a.choice], bold=True)), *words]
    credit = af.CREED_CREDIT[a.choice]
    return [*lines, Line("credit", (Span(credit, italic=True),))] if credit else lines


def _section(title: str) -> Line:
````

**In `backend/printed_bulletin.py`, replace:**

````
    lines += _custom(s, "sermon", r)
    lines += [_element(s, "affirmation_of_faith", "Affirmation of Faith:", Span("  "),
                       Span("“The Apostles’ Creed”", bold=True)),
              Line("bold", (Span(APOSTLES_CREED, bold=True),))]
    lines += _custom(s, "affirmation_of_faith", r)
````

**with:**

````
    lines += _custom(s, "sermon", r)
    lines += _affirmation(s, r.affirmation)
    lines += _custom(s, "affirmation_of_faith", r)
````

**In `backend/usecases/archive.py`, replace:**

````

from db import session_scope
````

**with:**

````

import affirmation as af
from db import session_scope
````

**In `backend/usecases/archive.py`, replace:**

````
    bulletin: Optional[ServiceBulletin] = None   # None: not sent (a client from before printed bulletin PR 2b)

````

**with:**

````
    bulletin: Optional[ServiceBulletin] = None   # None: not sent (a client from before printed bulletin PR 2b)
    affirmation: Optional[af.Affirmation] = None  # None: not sent (a client from before the affirmation spec)

````

**In `backend/usecases/archive.py`, replace:**

````
        bulletin=None if data.bulletin is None else data.bulletin.map_texts(clean),
    )
````

**with:**

````
        bulletin=None if data.bulletin is None else data.bulletin.map_texts(clean),
        affirmation=None if data.affirmation is None else replace(data.affirmation, text=clean(data.affirmation.text)),
    )
````

**In `backend/usecases/documents.py`, replace:**

````
longer there: the reading and the date print alone).
"""
````

**with:**

````
longer there: the reading and the date print alone).
The affirmation spec adds the Affirmation of Faith as posted; a body
without one (a page from before it) prints the Apostles' Creed, as before.
"""
````

**In `backend/usecases/documents.py`, replace:**

````
import service_output
from db import session_scope
````

**with:**

````
import service_output
from affirmation import Affirmation
from db import session_scope
````

**In `backend/usecases/documents.py`, replace:**

````
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements)
    content = service_output.render_docx(resolved, variant)
````

**with:**

````
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements, affirmation=clean.affirmation or Affirmation())
    content = service_output.render_docx(resolved, variant)
````

**In `backend/usecases/documents.py`, replace:**

````
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements)
    ot, nt = service_output.resolve_doc_readings(list(clean.scriptures), clean.selected_ot_ref,
````

**with:**

````
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements, affirmation=clean.affirmation or Affirmation())
    ot, nt = service_output.resolve_doc_readings(list(clean.scriptures), clean.selected_ot_ref,
````
<!-- /directives:T1_IMPL -->

- [ ] **Step 4: Run them and the suite**

Run: `.venv/bin/python -m pytest -q backend/tests/test_affirmation.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1`, then `.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1`
**Expected:** `23 passed in <t>s`, then `2271 passed, 49 skipped in <t>s`. `test_build_docx_characterization.py` and `test_printed_bulletin.py` pass unchanged: the default prints as today.

- [ ] **Step 5: Commit and push**

```bash
git add backend/affirmation.py backend/tests/test_affirmation.py backend/tests/test_no_streamlit_in_core.py backend/service_output.py backend/worship_service.py backend/printed_bulletin.py backend/usecases/archive.py backend/usecases/documents.py
git commit -q -m "Affirmation of Faith: the creeds and what prints" -m "affirmation.py holds the Apostles' Creed (today's wording, moved), the ELLC Nicene Creed and its credit line. The Word files print the creed's name or the own text, the printed bulletin the creed's words (the Nicene Creed one sense line per paragraph with a hanging indent, then ELLC's credit) or the own text in bold; switched off, or own text left blank, nothing prints. A service that says nothing prints as today." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

### Task 2: Saving, the API and the church default (S "Data shape", "Why a migration", "API changes"; clarifications 5, 9)

**Files:** Create `backend/migrations/versions/0010_services_affirmation.py`, `backend/tests/test_api_affirmation.py`. Modify `backend/db/models.py`, `backend/usecases/archive.py`, `backend/api/schemas.py`, `backend/api/routes/liturgy.py`, `backend/usecases/church_profile.py`, `backend/usecases/church_admin.py`, `backend/api/routes/me.py`, `backend/migrations/README.md`, `frontend/src/test/fixtures/index.ts` (test data only), the nine test files below; regenerate `frontend/src/lib/api/openapi.json` and `frontend/src/lib/api/schema.d.ts`.

- [ ] **Step 1: Write the failing tests**

The existing tests that know the head revision or the profile's fields change with them; `test_0006_adds_the_nullable_bulletin_column_and_keeps_rows` now stops at 0006 (it compared 0006's column against head). The README's 0010 queries are checked on Postgres in `test_migrations.py` (Step 4's check runs before and after the upgrade), and its deploy-log line against what Alembic logs.

<!-- directives:T2_TESTS -->
**Create `backend/tests/test_api_affirmation.py`:**

````
"""The Affirmation of Faith over HTTP (affirmation spec, "API changes",
"Data shape"): GET /liturgy/config, saving and opening a service (NULL is
the Apostles' Creed; a PUT without it keeps the saved one), the church
default on GET and PATCH /church (admins only), and the downloads."""
import logging
import uuid
from io import BytesIO

import pytest
from docx import Document
from sqlalchemy import select

import affirmation as af
from db import session_scope
from db.models import Church, Service
from repos.memberships import add_membership
from tests.api_helpers import church_headers, make_api_client

EMAIL = "pastor@example.com"
MEMBER = "member@example.com"
ADMIN = "admin@example.com"
SERVICE = {"service_date_iso": "2026-10-04", "occasion": "World Communion Sunday", "sermon_title": "Living Water"}
DEFAULT = {"include": True, "choice": "apostles", "text": ""}
OWN = "We trust in God the Holy Spirit."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    add_membership(make_user(email=MEMBER), cid, "member")
    add_membership(make_user(email=ADMIN), cid, "admin")
    return cid


def call(client, method, path, church_id, *, email=EMAIL, json=None, **headers):
    return client.request(method, path, json=json, headers={**church_headers(email, church_id), **headers})


def stored(service_id):
    with session_scope() as s:
        return s.execute(select(Service.affirmation).where(Service.id == uuid.UUID(service_id))).scalar_one()


def test_the_config_has_the_card_and_both_creeds(client, church):
    r = call(client, "GET", "/liturgy/config", church)
    assert r.status_code == 200, r.text
    body = r.json()
    # The outline item is unchanged, so a page from before the card (Affirmation PR B) keeps its row.
    item = next(i for i in body["outline"] if i["key"] == "affirmation_of_faith")
    assert item == {"kind": "landmark", "key": "affirmation_of_faith", "label": "Affirmation of Faith",
                    "value_source": "fixed", "fixed_text": "Apostles' Creed", "anchors_after": ["affirmation_of_faith"]}
    assert body["affirmation"] == {
        "title": "Affirmation of Faith", "toggle_label": "Include Affirmation of Faith",
        "choices": [{"key": "apostles", "label": "Apostles' Creed", "text": af.APOSTLES_CREED, "credit": ""},
                    {"key": "nicene", "label": "Nicene Creed", "text": af.NICENE_CREED, "credit": af.NICENE_CREDIT},
                    {"key": "own", "label": "Your own text", "text": "", "credit": ""}]}


def test_a_service_saved_without_it_opens_and_prints_as_today(client, church):
    created = call(client, "POST", "/services", church, json=SERVICE).json()
    assert stored(created["id"]) is None
    assert created["affirmation"] == DEFAULT
    assert call(client, "GET", f"/services/{created['id']}", church).json()["affirmation"] == DEFAULT


def test_save_open_and_a_put_without_it_keeps_the_saved_choice(client, church):
    nicene = {"include": True, "choice": "nicene", "text": "dropped"}
    created = call(client, "POST", "/services", church, json={**SERVICE, "affirmation": nicene}).json()
    assert created["affirmation"] == {"include": True, "choice": "nicene", "text": ""}
    assert stored(created["id"]) == {"include": True, "choice": "nicene", "text": ""}
    kept = call(client, "PUT", f"/services/{created['id']}", church, json=SERVICE, **{"If-Match": created["saved_at"]})
    assert kept.status_code == 200, kept.text
    assert kept.json()["affirmation"]["choice"] == "nicene"                     # a page from before: kept
    off = call(client, "PUT", f"/services/{created['id']}", church,
               json={**SERVICE, "affirmation": {"include": False, "choice": "own", "text": f"  {OWN}  "}},
               **{"If-Match": kept.json()["saved_at"]})
    assert off.json()["affirmation"] == {"include": False, "choice": "own", "text": OWN}


@pytest.mark.parametrize("bad, field", [
    ({"include": True, "choice": "brief", "text": ""}, "affirmation.choice"),
    ({"include": True, "choice": "own"}, "affirmation.text"),
    ({"include": True, "choice": "own", "text": "x" * 20_001}, "affirmation.text"),
    ({"include": True, "choice": "own", "text": "", "extra": 1}, "affirmation.extra"),
])
def test_a_bad_affirmation_is_a_422_on_its_field(client, church, bad, field):
    r = call(client, "POST", "/services", church, json={**SERVICE, "affirmation": bad})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"]


def test_the_word_file_follows_the_body_and_logs_no_text(client, church, caplog):
    caplog.set_level(logging.INFO)
    def paragraphs(body):
        r = call(client, "POST", "/documents", church, json={"variant": "pastor", "service": body})
        assert r.status_code == 200, r.text
        return [p.text for p in Document(BytesIO(r.content)).paragraphs]
    assert "Apostles' Creed" in paragraphs(SERVICE)                                  # no affirmation: as today
    assert "Affirmation of Faith" not in paragraphs({**SERVICE, "affirmation": {**DEFAULT, "include": False}})
    assert OWN in paragraphs({**SERVICE, "affirmation": {"include": True, "choice": "own", "text": OWN}})
    assert OWN not in caplog.text


def test_the_church_default_reads_as_the_apostles_creed_until_an_admin_sets_it(client, church):
    assert call(client, "GET", "/church", church, email=MEMBER).json()["default_affirmation"] == {
        "choice": "apostles", "text": ""}
    r = call(client, "PATCH", "/church", church, email=ADMIN,
             json={"default_affirmation": {"choice": "own", "text": f" {OWN}\r\n"}})
    assert r.status_code == 200, r.text
    assert r.json()["default_affirmation"] == {"choice": "own", "text": OWN}
    assert call(client, "GET", "/church", church, email=MEMBER).json()["default_affirmation"] == {
        "choice": "own", "text": OWN}
    r = call(client, "PATCH", "/church", church, json={"default_affirmation": {"choice": "nicene", "text": OWN}})
    assert r.json()["default_affirmation"] == {"choice": "nicene", "text": ""}


def test_a_member_cannot_change_the_church_default(client, church):
    call(client, "PATCH", "/church", church, json={"default_affirmation": {"choice": "nicene", "text": ""}})
    r = call(client, "PATCH", "/church", church, email=MEMBER,
             json={"default_affirmation": {"choice": "own", "text": OWN}})
    assert r.status_code == 403, r.text
    assert r.json()["error"]["message"] == "Only church admins can do this."
    with session_scope() as s:
        settings = s.get(Church, church).settings
    assert settings["default_affirmation"] == {"choice": "nicene", "text": ""}


def test_own_text_for_the_default_must_not_be_blank(client, church):
    r = call(client, "PATCH", "/church", church, json={"default_affirmation": {"choice": "own", "text": " \n "}})
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"default_affirmation.text": "Type your church's own text, or choose a creed."}


def test_the_published_schema_shows_the_new_api_without_a_sign_in(client):
    """The after-deploy check (README "Before 0010_services_affirmation", step 4):
    /openapi.json needs no sign-in and names ServiceAffirmation."""
    r = client.get("/openapi.json")
    assert r.status_code == 200, r.text
    assert "ServiceAffirmation" in r.json()["components"]["schemas"]
````

**In `backend/tests/test_migrations.py`, replace:**

````
            kept = _insert_legacy_service(conn, church_id, user_id)
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "head")
        with engine.begin() as conn:
            at_head = _services_shape(conn)
````

**with:**

````
            kept = _insert_legacy_service(conn, church_id, user_id)
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "0006_services_bulletin")
        with engine.begin() as conn:
            at_head = _services_shape(conn)
````

**In `backend/tests/test_migrations.py`, replace:**

````
    assert check_after == {"version": "0009_memberships_one_owner", "one_owner_index": 1}
````

**with:**

````
    assert check_after == {"version": "0009_memberships_one_owner", "one_owner_index": 1}


# --- The affirmation spec: 0010_services_affirmation ---

# What `alembic upgrade 0009_memberships_one_owner:0010_services_affirmation --sql` prints on Postgres,
# comments and blank lines left out: the preview the owner reads before the merge
# (backend/migrations/README.md, "Before 0010_services_affirmation", step 3).
PREVIEW_0010 = [
    "BEGIN;",
    "SET LOCAL lock_timeout = '5s';",
    "SET LOCAL statement_timeout = '60s';",
    "ALTER TABLE services ADD COLUMN affirmation JSON;",
    "UPDATE alembic_version SET version_num='0010_services_affirmation' "
    "WHERE alembic_version.version_num = '0009_memberships_one_owner';",
    "COMMIT;",
]


def test_0010_adds_the_nullable_affirmation_column_and_keeps_rows(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0009_memberships_one_owner")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            kept = _insert_legacy_service(conn, church_id, user_id)
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "0010_services_affirmation")
        with engine.begin() as conn:
            after = _services_shape(conn)
            inserted = _insert_legacy_service(conn, church_id, user_id, date_iso="2026-10-04")
            rows = conn.execute(sa.text("SELECT id, occasion, affirmation FROM services ORDER BY service_date_iso")).all()
    finally:
        engine.dispose()
    assert after["columns"] == before["columns"] + [("affirmation", "JSON", True)]
    assert (after["pk"], after["fks"], after["indexes"]) == (before["pk"], before["fks"], before["indexes"])
    # The row from before keeps its data and reads NULL (the Apostles' Creed, included); so does a new one.
    assert [(uuid.UUID(str(r.id)), r.occasion, r.affirmation) for r in rows] == [
        (kept, "Pentecost 17", None), (inserted, "Pentecost 17", None)]


def test_0010_downgrade_gives_back_the_0009_services_table(sqlite_url):
    _alembic(sqlite_url, "upgrade", "0009_memberships_one_owner")
    engine = sa.create_engine(sqlite_url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            before = _services_shape(conn)
        _alembic(sqlite_url, "upgrade", "0010_services_affirmation")
        with engine.begin() as conn:
            user_id, church_id = _seed_owner_and_church(conn)
            _insert_legacy_service(conn, church_id, user_id)
            conn.execute(sa.text("""UPDATE services SET bulletin = '{}',
                                    affirmation = '{"include": false, "choice": "nicene", "text": ""}'"""))
        _alembic(sqlite_url, "downgrade", "0009_memberships_one_owner")
        with engine.connect() as conn:
            after = _services_shape(conn)
            rows = conn.execute(sa.text("SELECT occasion, bulletin FROM services")).all()
            version = conn.execute(sa.text("SELECT version_num FROM alembic_version")).scalar_one()
    finally:
        engine.dispose()
    assert after == before
    assert [tuple(r) for r in rows] == [("Pentecost 17", "{}")]
    assert version == "0009_memberships_one_owner"


def test_offline_sql_for_0010_is_one_column_add_under_the_timeouts():
    cfg = alembic_config(url="postgresql://preview@localhost:1/preview", configure_logger=False)
    cfg.output_buffer = buffer = io.StringIO()
    command.upgrade(cfg, "0009_memberships_one_owner:0010_services_affirmation", sql=True)
    lines = [line for line in buffer.getvalue().splitlines() if line.strip() and not line.startswith("--")]
    assert lines == PREVIEW_0010


def test_the_readme_shows_the_0010_preview_exactly_and_in_full():
    """README "Before 0010_services_affirmation", step 3: PREVIEW_0010, nothing
    shortened, and the step says it is for reading only (as 0009's)."""
    section = _readme().split("\n## Before 0010_services_affirmation (Affirmation of Faith)\n", 1)[1]
    step = section.split("\n### Step 3: Read the SQL the upgrade will run\n", 1)[1].split("\n### ", 1)[0]
    block = "BEGIN;" + step.split("\n```\nBEGIN;", 1)[1].split("\n```", 1)[0]
    assert block.splitlines() == PREVIEW_0010
    assert "**Read only. Do not run this.**" in step
    assert "Expected, exactly and in full" in step
    assert "..." not in step and "\u2026" not in step


def _readme_0010_sql(n: int) -> str:
    """The n-th ```sql block of README "Before 0010_services_affirmation": 0 is step 2's
    counts, 1 step 4's after-deploy check."""
    section = _readme().split("\n## Before 0010_services_affirmation (Affirmation of Faith)\n", 1)[1]
    return re.findall(r"```sql\n(.*?)```", section, re.S)[n]


def test_the_readme_s_0010_deploy_log_line_is_alembic_s(sqlite_url, caplog):
    """Step 4's deploy-log line is what `alembic upgrade head` logs for 0010."""
    section = _readme().split("\n## Before 0010_services_affirmation (Affirmation of Faith)\n", 1)[1]
    step = section.split("\n### Step 4: After the deploy (read-only)\n", 1)[1].split("\n### ", 1)[0]
    logged = step.split("\n```\n", 1)[1].split("\n```", 1)[0]
    _alembic(sqlite_url, "upgrade", "0009_memberships_one_owner")
    caplog.set_level(logging.INFO, logger="alembic.runtime.migration")
    _alembic(sqlite_url, "upgrade", "0010_services_affirmation")
    assert logged == "INFO  [alembic.runtime.migration] " + next(
        r.getMessage() for r in caplog.records if r.getMessage().startswith("Running upgrade 0009"))


@pytest.mark.postgres
def test_the_owner_s_read_only_queries_around_0010(pg_admin_url):
    """README "Before 0010_services_affirmation": step 2's counts before and after
    the upgrade, and step 4's check, which also answers before 0010 is applied."""
    with throwaway_database(pg_admin_url, role_bypassrls=True) as sandbox:
        _alembic(sandbox.role_url, "upgrade", "0009_memberships_one_owner")
        engine = _pg_engine(sandbox.role_url)
        try:
            with engine.begin() as conn:
                user_id, church_id = _seed_owner_and_church(conn)
                kept = _insert_legacy_service(conn, church_id, user_id)
                _insert_legacy_service(conn, church_id, user_id, date_iso="2026-10-04")
            with engine.connect() as conn:
                before = dict(conn.execute(text(_readme_0010_sql(0))).mappings().one())
                check_before = dict(conn.execute(text(_readme_0010_sql(1))).mappings().one())
            _alembic(sandbox.role_url, "upgrade", "0010_services_affirmation")
            with engine.begin() as conn:
                check_at_deploy = dict(conn.execute(text(_readme_0010_sql(1))).mappings().one())
                conn.execute(text("UPDATE services SET affirmation = CAST(:a AS json) WHERE id = :id"),
                             {"a": '{"include": false, "choice": "nicene", "text": ""}', "id": kept})
            with engine.connect() as conn:
                after = dict(conn.execute(text(_readme_0010_sql(0))).mappings().one())
                check_after = dict(conn.execute(text(_readme_0010_sql(1))).mappings().one())
        finally:
            engine.dispose()
    assert before == {"version": "0009_memberships_one_owner", "services": 2, "churches": 1}
    assert check_before == {"version": "0009_memberships_one_owner", "new_column": 0, "with_affirmation": 0}
    assert check_at_deploy == {"version": "0010_services_affirmation", "new_column": 1, "with_affirmation": 0}
    assert after == {**before, "version": "0010_services_affirmation"}
    assert check_after == {"version": "0010_services_affirmation", "new_column": 1, "with_affirmation": 1}
````

**In `backend/tests/test_schema_check.py`, replace:**

````

EXPECTED_HEAD = "0009_memberships_one_owner"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
````

**with:**

````

EXPECTED_HEAD = "0010_services_affirmation"
# What a database stamped at 0001_baseline lacks (runbook step 6, sorted):
````

**In `backend/tests/test_schema_check.py`, replace:**

````
# so its new uq_invites_pending_email is not listed here; Postgres lists it),
# then 0009's index (slice 6b-2a).
BASELINE_DRIFT = [
````

**with:**

````
# so its new uq_invites_pending_email is not listed here; Postgres lists it),
# then 0009's index (slice 6b-2a), then 0010's services column (the affirmation spec).
BASELINE_DRIFT = [
````

**In `backend/tests/test_schema_check.py`, replace:**

````
    "add_column invites.reusable",
    "add_column services.bulletin",
````

**with:**

````
    "add_column invites.reusable",
    "add_column services.affirmation",
    "add_column services.bulletin",
````

**In `backend/tests/test_schema_check.py`, replace:**

````

def test_head_is_0009_memberships_one_owner():
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
````

**with:**

````

def test_head_is_0010_services_affirmation():
    script = ScriptDirectory.from_config(alembic_config(configure_logger=False))
````

**In `backend/tests/test_schema_check.py`, replace:**

````

def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0009_changes(tmp_path):
    """0001_baseline stands in for production after `alembic stamp 0001_baseline`."""
````

**with:**

````

def test_schema_diff_at_baseline_lists_exactly_the_0004_to_0010_changes(tmp_path):
    """0001_baseline stands in for production after `alembic stamp 0001_baseline`."""
````

**In `backend/tests/test_api_app.py`, replace:**

````

SCHEMA_HEAD = "0009_memberships_one_owner"
BEHIND_WARNING = f"schema revision None != head {SCHEMA_HEAD}"
````

**with:**

````

SCHEMA_HEAD = "0010_services_affirmation"
BEHIND_WARNING = f"schema revision None != head {SCHEMA_HEAD}"
````

**In `backend/tests/test_services_postgres.py`, replace:**

````
    # The 5a-2 save has 3 slots; the other five are old-style; "", NULL and "Sept 13" are undated. The
    # test database is at head (0009_memberships_one_owner since slice 6b-2a).
    assert counts == {"version": "0009_memberships_one_owner", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0009_memberships_one_owner", "new_columns": 2, "new_index": 1}

````

**with:**

````
    # The 5a-2 save has 3 slots; the other five are old-style; "", NULL and "Sept 13" are undated. The
    # test database is at head (0010_services_affirmation since the affirmation spec).
    assert counts == {"version": "0010_services_affirmation", "services": 6, "undated": 3, "old_style_hymn_lists": 5}
    assert applied == {"version": "0010_services_affirmation", "new_columns": 2, "new_index": 1}

````

**In `backend/tests/test_services_postgres.py`, replace:**

````
        applied = dict(s.execute(text(readme_0006_sql(1))).mappings().one())
    assert counts == {"version": "0009_memberships_one_owner", "services": 3, "churches": 2}
    assert applied == {"version": "0009_memberships_one_owner", "new_column": 1, "with_bulletin": 1}

````

**with:**

````
        applied = dict(s.execute(text(readme_0006_sql(1))).mappings().one())
    assert counts == {"version": "0010_services_affirmation", "services": 3, "churches": 2}
    assert applied == {"version": "0010_services_affirmation", "new_column": 1, "with_bulletin": 1}

````

**In `backend/tests/test_services_postgres.py`, replace:**

````
    assert re.fullmatch(r"\d+ (bytes|kB|MB|GB)", counts.pop("database_size"))
    assert counts == {"version": "0009_memberships_one_owner", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0009_memberships_one_owner", "row_security": True, "open_grants": 0, "pictures": 1}
    assert re.fullmatch(r"\d+ (bytes|kB|MB|GB)", storage.pop("database_size"))
````

**with:**

````
    assert re.fullmatch(r"\d+ (bytes|kB|MB|GB)", counts.pop("database_size"))
    assert counts == {"version": "0010_services_affirmation", "services": 2, "with_bulletin": 1}
    assert applied == {"version": "0010_services_affirmation", "row_security": True, "open_grants": 0, "pictures": 1}
    assert re.fullmatch(r"\d+ (bytes|kB|MB|GB)", storage.pop("database_size"))
````

**In `backend/tests/test_api_me.py`, replace:**

````
        "default_benediction": DEFAULT_BENEDICTION_FALLBACK,  # slice 4: the full Halverson text
    }
````

**with:**

````
        "default_benediction": DEFAULT_BENEDICTION_FALLBACK,  # slice 4: the full Halverson text
        "default_affirmation": {"choice": "apostles", "text": ""},  # the affirmation spec
    }
````

**In `backend/tests/test_api_invites.py`, replace:**

````
        "default_benediction": DEFAULT_BENEDICTION_FALLBACK,  # slice 4: the full Halverson text
    }
````

**with:**

````
        "default_benediction": DEFAULT_BENEDICTION_FALLBACK,  # slice 4: the full Halverson text
        "default_affirmation": {"choice": "apostles", "text": ""},  # the affirmation spec
    }
````

**In `backend/tests/test_api_churches.py`, replace:**

````
        "default_benediction": DEFAULT_BENEDICTION_FALLBACK,   # slice 4: the full Halverson text
    }
````

**with:**

````
        "default_benediction": DEFAULT_BENEDICTION_FALLBACK,   # slice 4: the full Halverson text
        "default_affirmation": {"choice": "apostles", "text": ""},   # the affirmation spec
    }
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````
        "default_benediction": HALVERSON,
    }
````

**with:**

````
        "default_benediction": HALVERSON,
        "default_affirmation": {"choice": "apostles", "text": ""},
    }
````

**In `backend/tests/test_api_church_profile.py`, replace:**

````
        "effective_translation", "effective_translation_label", "default_hymnal", "effective_hymnal",
        "default_benediction"}

````

**with:**

````
        "effective_translation", "effective_translation_label", "default_hymnal", "effective_hymnal",
        "default_benediction", "default_affirmation"}

````
<!-- /directives:T2_TESTS -->

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_api_affirmation.py backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_api_me.py backend/tests/test_api_invites.py backend/tests/test_api_churches.py backend/tests/test_api_church_profile.py 2>&1 | tail -1`
**Expected:** `33 failed, 154 passed, 20 skipped in <t>s`.

- [ ] **Step 3: Write the migration, the storage, the API and the default**

<!-- directives:T2_IMPL -->
**Create `backend/migrations/versions/0010_services_affirmation.py`:**

````
"""Services: the Affirmation of Faith (affirmation spec, "Data shape")

Expand-only (F §3.4): one nullable JSON column, no backfill, no server
default, no index. Existing rows keep NULL, which the API reads as the
Apostles' Creed, included: every service saved before this change prints
exactly as before.
- services.affirmation JSON NULL: {include, choice, text} (affirmation.py).
  A new column rather than a key inside services.liturgy, which holds only
  the eight liturgy sections (0006's reason too); the frozen Streamlit app
  never reads it.

On Postgres env.py runs SET LOCAL lock_timeout = '5s' (and statement_timeout
'60s') first; adding a nullable column without a default changes only the
catalog. Both directions use op.batch_alter_table, as 0004 to 0006 do.

Revision ID: 0010_services_affirmation
Revises: 0009_memberships_one_owner
Create Date: 2026-10-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_services_affirmation"
down_revision = "0009_memberships_one_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("affirmation", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.drop_column("affirmation")
````

**In `backend/db/models.py`, replace:**

````
    bulletin = Column(JSON(none_as_null=True), nullable=True)

````

**with:**

````
    bulletin = Column(JSON(none_as_null=True), nullable=True)
    # Revision 0010_services_affirmation (the affirmation spec): {include,
    # choice, text}. NULL: saved before it (or a POST without one), read as
    # the Apostles' Creed, included.
    affirmation = Column(JSON(none_as_null=True), nullable=True)

````

**In `backend/usecases/archive.py`, replace:**

````

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
````

**with:**

````

The affirmation spec adds the Affirmation of Faith (affirmation.py):
clean_input makes its own text Word-safe and trims it; a save stores it in
services.affirmation, a POST without it stores NULL and a PUT without it
keeps the saved one (the bulletin's rule); opening reads it tolerantly
(NULL is the Apostles' Creed, included, as every service printed before).

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
````

**In `backend/usecases/archive.py`, replace:**

````
    bulletin: dict                              # service_bulletin's stored shape; empty when none was saved
    created_by: Optional[Author]
````

**with:**

````
    bulletin: dict                              # service_bulletin's stored shape; empty when none was saved
    affirmation: dict                           # affirmation.Affirmation.to_json(); the default when none was saved
    created_by: Optional[Author]
````

**In `backend/usecases/archive.py`, replace:**

````
        **({} if clean.bulletin is None else {"bulletin": clean.bulletin.to_json()}),
        "saved_at": datetime.datetime.now(datetime.timezone.utc),
````

**with:**

````
        **({} if clean.bulletin is None else {"bulletin": clean.bulletin.to_json()}),
        # Not sent (a page from before the affirmation spec): a POST stores NULL, a PUT keeps the saved one.
        **({} if clean.affirmation is None else {"affirmation": clean.affirmation.to_json()}),
        "saved_at": datetime.datetime.now(datetime.timezone.utc),
````

**In `backend/usecases/archive.py`, replace:**

````
        bulletin=read_bulletin(row.bulletin).to_json(),
        created_by=None if found is None else _author(*found),
````

**with:**

````
        bulletin=read_bulletin(row.bulletin).to_json(),
        affirmation=af.read(row.affirmation).to_json(),
        created_by=None if found is None else _author(*found),
````

**In `backend/api/schemas.py`, replace:**

````

import bulletin_settings
````

**with:**

````

import affirmation
import bulletin_settings
````

**In `backend/api/schemas.py`, replace:**

````
    picture: Optional[str] = None

````

**with:**

````
    picture: Optional[str] = None


AffirmationChoice = Literal["apostles", "nicene", "own"]


class ServiceAffirmation(BaseModel):
    """The Affirmation of Faith of one service (affirmation spec): switched on
    or off, the choice, and the own text ("" unless the choice is "own"; the
    server reads it so). Sent and answered alike."""

    model_config = ConfigDict(extra="forbid")

    include: bool
    choice: AffirmationChoice
    text: str = Field(max_length=liturgy_config.LIMITS.max_section_text)


class ChurchAffirmation(BaseModel):
    """The church's default Affirmation of Faith (affirmation spec; GET and
    PATCH /church): the choice and, for "own", the church's own text."""

    model_config = ConfigDict(extra="forbid")

    choice: AffirmationChoice
    text: str = Field(max_length=liturgy_config.LIMITS.max_section_text)

````

**In `backend/api/schemas.py`, replace:**

````
    default_benediction: str                # slice 4: the church's default; full Halverson text when unset or "Halverson"; "" = none

````

**with:**

````
    default_benediction: str                # slice 4: the church's default; full Halverson text when unset or "Halverson"; "" = none
    default_affirmation: ChurchAffirmation  # the affirmation spec: the Apostles' Creed when unset

````

**In `backend/api/schemas.py`, replace:**

````
    bulletin: Optional[ServiceBulletin] = None

````

**with:**

````
    bulletin: Optional[ServiceBulletin] = None
    # The affirmation spec. Left out (a page from before it): the files print the Apostles' Creed, a POST
    # stores none and a PUT keeps the saved one.
    affirmation: Optional[ServiceAffirmation] = None

````

**In `backend/api/schemas.py`, replace:**

````
            bulletin=None if self.bulletin is None else service_bulletin.read(self.bulletin.model_dump(
                exclude=None if "cover_image_id" in self.bulletin.model_fields_set else {"cover_image_id"})))

````

**with:**

````
            bulletin=None if self.bulletin is None else service_bulletin.read(self.bulletin.model_dump(
                exclude=None if "cover_image_id" in self.bulletin.model_fields_set else {"cover_image_id"})),
            affirmation=None if self.affirmation is None else affirmation.read(self.affirmation.model_dump()))

````

**In `backend/api/schemas.py`, replace:**

````
    bulletin: ServiceBulletin           # PR 2b; nothing filled in for a service saved without one
    created_by: Optional[AuthorOut]     # null when the author's account was removed
````

**with:**

````
    bulletin: ServiceBulletin           # PR 2b; nothing filled in for a service saved without one
    affirmation: ServiceAffirmation     # the affirmation spec; the Apostles' Creed, included, when none was saved
    created_by: Optional[AuthorOut]     # null when the author's account was removed
````

**In `backend/api/routes/liturgy.py`, replace:**

````

import liturgy_config
````

**with:**

````

import affirmation
import liturgy_config
````

**In `backend/api/routes/liturgy.py`, replace:**

````

class LiturgyLimitsOut(BaseModel):
````

**with:**

````

class AffirmationChoiceOut(BaseModel):
    key: Literal["apostles", "nicene", "own"]
    label: str                      # "Apostles' Creed", "Nicene Creed", "Your own text"
    text: str                       # the creed as the printed bulletin prints it; "" for own text
    credit: str                     # the acknowledgement printed under it (the Nicene Creed's, ELLC); "" for none


class AffirmationConfigOut(BaseModel):
    title: str                      # "Affirmation of Faith"
    toggle_label: str               # "Include Affirmation of Faith"
    choices: list[AffirmationChoiceOut]


class LiturgyLimitsOut(BaseModel):
````

**In `backend/api/routes/liturgy.py`, replace:**

````
    communion: CommunionOut
    limits: LiturgyLimitsOut
````

**with:**

````
    communion: CommunionOut
    # The affirmation spec. The outline's affirmation_of_faith item stays a landmark ("Apostles' Creed"), so a
    # page from before the card keeps its row; a page with the card shows it there when this is present.
    affirmation: AffirmationConfigOut
    limits: LiturgyLimitsOut
````

**In `backend/api/routes/liturgy.py`, replace:**

````
                               blocks=[CommunionBlockOut(style=b.style, text=b.text) for b in lc.COMMUNION_BLOCKS]),
        limits=LiturgyLimitsOut(**vars(lc.LIMITS)),
````

**with:**

````
                               blocks=[CommunionBlockOut(style=b.style, text=b.text) for b in lc.COMMUNION_BLOCKS]),
        affirmation=AffirmationConfigOut(
            title=affirmation.TITLE, toggle_label=affirmation.TOGGLE_LABEL,
            choices=[AffirmationChoiceOut(key=key, label=affirmation.CHOICE_LABELS[key],
                                          text=affirmation.CREED_TEXT.get(key, ""),
                                          credit=affirmation.CREED_CREDIT.get(key, ""))
                     for key in affirmation.CHOICES]),
        limits=LiturgyLimitsOut(**vars(lc.LIMITS)),
````

**In `backend/usecases/church_profile.py`, replace:**

````

import scripture_fetcher
````

**with:**

````

import affirmation
import scripture_fetcher
````

**In `backend/usecases/church_profile.py`, replace:**

````
    default_benediction: str             # slice 4: resolve_default_benediction (full Halverson text by default)

````

**with:**

````
    default_benediction: str             # slice 4: resolve_default_benediction (full Halverson text by default)
    default_affirmation: dict            # the affirmation spec: {choice, text}, the Apostles' Creed by default

````

**In `backend/usecases/church_profile.py`, replace:**

````
      the shorthand "Halverson" is the full Halverson text (owner, 2026-10-02).

````

**with:**

````
      the shorthand "Halverson" is the full Halverson text (owner, 2026-10-02).
    - default_affirmation: affirmation.resolve_default(settings) as {choice,
      text}: the Apostles' Creed when unset or not understood.

````

**In `backend/usecases/church_profile.py`, replace:**

````
        default_benediction=resolve_default_benediction(church["settings"]),
    )
````

**with:**

````
        default_benediction=resolve_default_benediction(church["settings"]),
        default_affirmation={k: v for k, v in affirmation.resolve_default(church["settings"]).to_json().items()
                             if k != "include"},
    )
````

**In `backend/usecases/church_admin.py`, replace:**

````
from collections.abc import Collection, Mapping

import liturgy_prompts
````

**with:**

````
from collections.abc import Collection, Mapping
from typing import Any

import affirmation
import liturgy_prompts
````

**In `backend/usecases/church_admin.py`, replace:**

````

def clean_profile_patch(changes: Mapping[str, str], *, translations: Collection[str],
                        church_hymnals: Collection[str]) -> tuple[dict[str, str], dict[str, str]]:
    """PATCH /church's provided fields, cleaned and checked (pure).
````

**with:**

````

def clean_profile_patch(changes: Mapping[str, Any], *, translations: Collection[str],
                        church_hymnals: Collection[str]) -> tuple[dict[str, str], dict[str, Any]]:
    """PATCH /church's provided fields, cleaned and checked (pure).
````

**In `backend/usecases/church_admin.py`, replace:**

````
    trimmed, and "" is kept (the church then has no default Benediction).
    Returns (columns, settings_patch).
````

**with:**

````
    trimmed, and "" is kept (the church then has no default Benediction).
    The default Affirmation of Faith (affirmation spec) is stored as {choice,
    text}: the text cleaned as the Benediction's and kept only for "own",
    which needs one (InvalidInput on default_affirmation.text).
    Returns (columns, settings_patch).
````

**In `backend/usecases/church_admin.py`, replace:**

````
    columns: dict[str, str] = {}
    settings: dict[str, str] = {}
    if "name" in changes:
````

**with:**

````
    columns: dict[str, str] = {}
    settings: dict[str, Any] = {}
    if "name" in changes:
````

**In `backend/usecases/church_admin.py`, replace:**

````
        settings["default_benediction"] = archive._xml_safe(changes["default_benediction"]).strip()
    return columns, settings
````

**with:**

````
        settings["default_benediction"] = archive._xml_safe(changes["default_benediction"]).strip()
    if "default_affirmation" in changes:
        wanted = changes["default_affirmation"]
        text = archive._xml_safe(wanted["text"]).strip() if wanted["choice"] == "own" else ""
        if wanted["choice"] == "own" and not text:
            raise InvalidInput(affirmation.OWN_TEXT_REQUIRED, field="default_affirmation.text")
        settings[affirmation.SETTINGS_KEY] = {"choice": wanted["choice"], "text": text}
    return columns, settings
````

**In `backend/usecases/church_admin.py`, replace:**

````

def update_profile(church_id: uuid.UUID, actor_id: uuid.UUID, changes: Mapping[str, str]) -> dict:
    """PATCH /church (6a spec, Semantics): write the provided fields, all or
````

**with:**

````

def update_profile(church_id: uuid.UUID, actor_id: uuid.UUID, changes: Mapping[str, Any]) -> dict:
    """PATCH /church (6a spec, Semantics): write the provided fields, all or
````

**In `backend/api/routes/me.py`, replace:**

````
from api.errors import error_responses
from api.schemas import ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
````

**with:**

````
from api.errors import error_responses
from api.schemas import ChurchAffirmation, ChurchOut, ChurchProfileOut, MeOut, UserOut
from repos.churches import list_user_churches
````

**In `backend/api/routes/me.py`, replace:**

````
    default_benediction: str | None = Field(None, max_length=4000)

````

**with:**

````
    default_benediction: str | None = Field(None, max_length=4000)
    default_affirmation: ChurchAffirmation | None = None     # the affirmation spec

````

**In `backend/migrations/README.md`, replace:**

````
- Revisions live in `migrations/versions/`, one file per revision, named
  `NNNN_short_slug.py`. Head is `0009_memberships_one_owner`.

````

**with:**

````
- Revisions live in `migrations/versions/`, one file per revision, named
  `NNNN_short_slug.py`. Head is `0010_services_affirmation`.

````

**In `backend/migrations/README.md`, replace:**

````
| `0009_memberships_one_owner` | Slice 6b-2a: unless a church has more than one owner (it refuses, naming the churches: "Church integrity" below), the partial unique index `uq_memberships_one_owner` on `memberships (church_id)` `WHERE role = 'owner'`: the database refuses a second owner. No column or data changes. Before it reaches production: "Before 0009_memberships_one_owner" below. |

````

**with:**

````
| `0009_memberships_one_owner` | Slice 6b-2a: unless a church has more than one owner (it refuses, naming the churches: "Church integrity" below), the partial unique index `uq_memberships_one_owner` on `memberships (church_id)` `WHERE role = 'owner'`: the database refuses a second owner. No column or data changes. Before it reaches production: "Before 0009_memberships_one_owner" below. |
| `0010_services_affirmation` | The Affirmation of Faith: `services.affirmation` (JSON), nullable with no default and no backfill: the service's Affirmation of Faith (`{include, choice, text}`); NULL reads as the Apostles' Creed, included, as every service printed before. Before it reaches production: "Before 0010_services_affirmation" below. |

````

**In `backend/migrations/README.md`, replace:**

````

## Church integrity (slice 6b)
````

**with:**

````

## Before 0010_services_affirmation (Affirmation of Faith)

Railway's Pre-deploy Command (`alembic upgrade head`) applies
`0010_services_affirmation` when Affirmation PR A (the server side of the
Affirmation of Faith; the pages are PR B, merged after it) merges. First,
the same routine as 0006: a backup, read-only counts of the saved services,
and a look at the SQL; after the deploy, one read-only check. One step at a
time. Nothing here changes data. The agent guides the owner and records the
results in `docs/ops-runbook.md` → "Affirmation PR A record", never with
an email address, a church id or a database URL.

### Step 1: Backup

Actions → db-backup → Run workflow (branch `main`), or
`gh workflow run db-backup --ref main`. It must finish green with an
artifact `db-backup`. Record the run URL.

### Step 2: Count the saved services (read-only)

Supabase → the project → SQL Editor → New query. Paste this and Run:

```sql
-- Read-only: what the archive holds before 0010. Changes nothing.
SELECT (SELECT version_num FROM alembic_version) AS version,
       count(*) AS services,
       count(DISTINCT church_id) AS churches
FROM services;
```

One row. Expected before the merge: `version` is `0009_memberships_one_owner`
(anything else: stop); `services` is the number of saved services in all
churches and `churches` the number of churches that saved at least one.

### Step 3: Read the SQL the upgrade will run

**Read only. Do not run this.** It is the SQL Railway runs when the PR
merges, shown here so the owner can read it; pasting it into the SQL
Editor would change the database. The agent renders it from the PR's code
without connecting to any database (from `backend/`):

```bash
DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0009_memberships_one_owner:0010_services_affirmation --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//'
```

Expected, exactly and in full (`backend/tests/test_migrations.py` pins it).
In the chat the agent does not paste it: it says in plain words what it
does and points to this step.

```
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '60s';
ALTER TABLE services ADD COLUMN affirmation JSON;
UPDATE alembic_version SET version_num='0010_services_affirmation' WHERE alembic_version.version_num = '0009_memberships_one_owner';
COMMIT;
```

One new empty column, in one transaction: no row is copied, changed or
deleted. If another connection holds a lock on `services` for more than
5 s, the deploy fails and the previous release keeps serving; run the
deploy again.

### Step 4: After the deploy (read-only)

First the owner opens Railway → the API service → the merge commit's
deployment → Deploy Logs and looks for the pre-deploy command's line:

```
INFO  [alembic.runtime.migration] Running upgrade 0009_memberships_one_owner -> 0010_services_affirmation, Services: the Affirmation of Faith (affirmation spec, "Data shape")
```

Then the agent checks that the new API is the one serving: `/health/ready`
says only that the API and the database answer, so the agent fetches the API's
published schema (`/openapi.json` on the API's address, no sign-in) and
looks for `"ServiceAffirmation"` in it (the API from before this PR has
none).

Then the SQL Editor (it only reads):

```sql
-- Read-only: is 0010 applied? Changes nothing.
-- Before 0010 is applied it still runs: 0009_memberships_one_owner, 0, 0.
SELECT (SELECT version_num FROM alembic_version) AS version,
       (SELECT count(*) FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'services'
           AND column_name = 'affirmation') AS new_column,
       (SELECT count(*) FROM services AS s
         WHERE to_jsonb(s) ->> 'affirmation' IS NOT NULL) AS with_affirmation;
```

Expected: `0010_services_affirmation`, `1`, `0`. (`with_affirmation` stays
`0` until the Affirmation of Faith pages, PR B, are live: the pages from
before them never send one.) `0009_memberships_one_owner`, `0`, `0` means
the deploy has not applied 0010 yet: wait a minute and run it again. Then
step 2's query again: the same `services` and `churches` (or more, by the
services saved since the deploy; never fewer).

### Reverting Affirmation PR A

If PR B (the pages) is merged, revert it first: its pages send
`affirmation`, which the API from before PR A refuses. The schema stays at
`0010_services_affirmation`: the column is nullable and the code before
this PR ignores it. Revert the merge commit, then restore
`backend/migrations/versions/0010_services_affirmation.py`, the `Service`
column in `backend/db/models.py`, this README and
`backend/tests/test_migrations.py` from the merge commit in the same PR, so
Railway's `alembic upgrade head` still finds the database at head and
`alembic check` stays clean. Never `alembic downgrade` production for this:
the choices saved since the merge stay in the column, unread (every service
then prints the Apostles' Creed again), and come back when the PR does.

## Church integrity (slice 6b)
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````
    default_benediction: DEFAULT_BENEDICTION_FALLBACK, // what the API resolves an unset or "Halverson" default to
    ...overrides,
````

**with:**

````
    default_benediction: DEFAULT_BENEDICTION_FALLBACK, // what the API resolves an unset or "Halverson" default to
    default_affirmation: { choice: "apostles", text: "" }, // the affirmation spec: what the API answers when unset
    ...overrides,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````
    },
    limits: {
````

**with:**

````
    },
    // The affirmation spec (the creeds shortened; the API sends them in full).
    affirmation: {
      title: "Affirmation of Faith",
      toggle_label: "Include Affirmation of Faith",
      choices: [
        { key: "apostles", label: "Apostles' Creed", text: "I believe in God, the Father almighty, Maker of heaven and earth.", credit: "" },
        {
          key: "nicene",
          label: "Nicene Creed",
          text: "We believe in one God,\nthe Father, the Almighty,",
          credit: "English translations of the Nicene Creed, \u00a9 1998 English Language Liturgical Consultation (ELLC), and used by permission. www.englishtexts.org",
        },
        { key: "own", label: "Your own text", text: "", credit: "" },
      ],
    },
    limits: {
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````
    bulletin: serviceBulletin(),
    created_by: { id: USER_ID, name: "Pat Pastor" },
````

**with:**

````
    bulletin: serviceBulletin(),
    affirmation: { include: true, choice: "apostles", text: "" },
    created_by: { id: USER_ID, name: "Pat Pastor" },
````
<!-- /directives:T2_IMPL -->

- [ ] **Step 4: Regenerate the OpenAPI snapshot and the API types**

Run: `.venv/bin/python backend/scripts/export_openapi.py; (cd frontend && npm run gen:api >/dev/null 2>&1; echo "gen $?"); git diff --stat -- frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts backend/tests/fixtures/shared/liturgy_outline.json | tail -1`
**Expected:** `Wrote <repo root>/frontend/src/lib/api/openapi.json`, `gen 0`, then ` 2 files changed, 208 insertions(+), 1 deletion(-)` (the outline fixture does not change). CI's `frontend` job regenerates `schema.d.ts` and fails on drift, so it is committed here, in PR A, although no page uses the new types until PR B.

- [ ] **Step 5: Run them, the SQL preview, the suite and today's pages against the new types**

Run: the Step 2 command; then `(cd backend && DATABASE_URL=postgresql://preview@localhost:1/preview ../.venv/bin/alembic upgrade 0009_memberships_one_owner:0010_services_affirmation --sql 2>/dev/null | grep -v -e '^--' -e '^$' | sed 's/ *$//')`; then `.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1`; then the frontend suite, typecheck and lint.
**Expected:** `187 passed, 20 skipped in <t>s`; the six lines of `backend/migrations/README.md` "Before 0010_services_affirmation" Step 3 exactly; `2288 passed, 50 skipped in <t>s`; then today's pages, unchanged, against PR A's types and fixtures:
```
 Test Files  119 passed (119)
      Tests  1122 passed (1122)
```
```
typecheck 0
lint 0
```

- [ ] **Step 6: Commit and push**

```bash
git add backend/migrations/versions/0010_services_affirmation.py backend/tests/test_api_affirmation.py backend/db/models.py backend/usecases/archive.py backend/api/schemas.py backend/api/routes/liturgy.py backend/usecases/church_profile.py backend/usecases/church_admin.py backend/api/routes/me.py backend/migrations/README.md frontend/src/test/fixtures/index.ts backend/tests/test_migrations.py backend/tests/test_schema_check.py backend/tests/test_api_app.py backend/tests/test_services_postgres.py backend/tests/test_api_me.py backend/tests/test_api_invites.py backend/tests/test_api_churches.py backend/tests/test_api_church_profile.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Affirmation of Faith: saving, the API and the church default" -m "Migration 0010_services_affirmation adds services.affirmation (nullable JSON; NULL reads as the Apostles' Creed, included). Saves store it, a PUT without it keeps the saved one. GET /liturgy/config gives the card's labels and both creeds; its outline is unchanged, so today's pages keep their Affirmation row. The church default lives in churches.settings: GET /church reads it, PATCH /church (admins only) sets it. The README has the routine before 0010. OpenAPI, schema.d.ts and the frontend test fixtures follow; no page changes." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

### Task 3: Planted violations, PR A (agent)

**Files:** none (each change is undone with `git checkout -- <file>`).

Each row breaks one rule the tests must hold. For each: make the change in the named file (the text occurs once, or the first of it where the row says so), run the test files, see them fail as listed, then `git checkout -- <file>` and `git status --short` (empty). Planting P5 changes two files; undo both. P9 needs Postgres and runs in T4 Step 3.

| # | Rule | Change | Run | Expected |
|---|---|---|---|---|
| P1 | switched off prints nothing in the Word files | `backend/worship_service.py`: `    if faith.prints():` → `    if True:` | `backend/tests/test_affirmation.py` | `5 failed, 15 passed` |
| P2 | switched off prints nothing in the printed bulletin (PDF, Word) and the email | `backend/printed_bulletin.py`: `    if not a.prints():` → `    if False:` | `backend/tests/test_affirmation.py` | `2 failed, 18 passed` |
| P3 | own text prints as typed | `backend/worship_service.py`: `faith.text if faith.choice == "own" else CHOICE_LABELS[faith.choice]` → `CHOICE_LABELS[faith.choice]` | `backend/tests/test_affirmation.py` | `1 failed, 19 passed` |
| P4 | a body without it prints as today | `backend/usecases/documents.py`, the first `affirmation=clean.affirmation or Affirmation())` → `affirmation=clean.affirmation or Affirmation(True, "nicene"))` | `backend/tests/test_affirmation.py backend/tests/test_api_affirmation.py` | `2 failed, 30 passed` |
| P5 | members cannot change the church default | `backend/api/routes/me.py`: `Depends(require_admin),` → `Depends(require_church),`, and in `backend/usecases/church_admin.py` `update_profile` delete the line `        require_admin_role(role)` | `backend/tests/test_api_affirmation.py` | `1 failed, 11 passed` (either guard alone still refuses) |
| P6 | a saved service without it keeps NULL, and a PUT without it keeps the saved choice | `backend/usecases/archive.py`: `        **({} if clean.affirmation is None else {"affirmation": clean.affirmation.to_json()}),` → `        "affirmation": (clean.affirmation or af.Affirmation()).to_json(),` | `backend/tests/test_api_affirmation.py` | `2 failed, 10 passed` |
| P7 | the outline is unchanged, so today's pages keep their row | `backend/liturgy_config.py`: `"fixed", "Apostles' Creed",` → `"none", None,` | `backend/tests/test_api_affirmation.py` | `1 failed, 11 passed` |
| P8 | each Nicene sense line wraps with a hanging indent (PDF and Word) | `backend/printed_bulletin.py`: `else [Line("hanging", (Span(sense, bold=True),))` → `else [Line("bold", (Span(sense, bold=True),))` | `backend/tests/test_affirmation.py` | `2 failed, 18 passed` |
| P9 | the after-deploy check runs before 0010 too | `backend/migrations/README.md`: `         WHERE to_jsonb(s) ->> 'affirmation' IS NOT NULL) AS with_affirmation;` → `         WHERE affirmation IS NOT NULL) AS with_affirmation;` | T4 Step 3's Postgres command with `backend/tests/test_migrations.py -k 0010` | `1 failed, 60 deselected` |

Backend rows: `.venv/bin/python -m pytest -q <files> 2>&1 | tail -1`.

### Task 4: Verification, PR A (agent)

**Files:** none.

- [ ] **Step 1: The suites, as run here and as CI runs them**

Run: `.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1`; then CI's `backend` command, from the repo root: `.venv/bin/python -m pytest -q 2>&1 | tail -1`
**Expected:** `2288 passed, 50 skipped in <t>s` (local); `2319 passed, 50 skipped in <t>s` (CI's: the same plus `streamlit_tests`' 31).

- [ ] **Step 2: Today's pages against PR A (owner answer A)**

PR A changes no page; it must not break the pages already live. What reaches them: `ServiceOut.affirmation`, `ChurchProfileOut.default_affirmation` and `LiturgyConfigOut.affirmation` are new fields in answers (today's pages read named fields only: `serviceToDraft`, `savedCopyFingerprint` and the Church settings form ignore the rest); the outline is unchanged (clarification 9); and today's pages never send `affirmation`, which `ServiceDraft` keeps optional (documents print the Apostles' Creed, a POST stores NULL, a PUT keeps the saved choice: `test_api_affirmation.py`, P4, P6).

Run: the frontend suite; typecheck and lint; `(cd frontend && npm run build 2>&1 | grep -cE "Compiled successfully")`; `(cd frontend && npm run gen:api >/dev/null 2>&1 && git diff --exit-code src/lib/api/schema.d.ts >/dev/null; echo "drift $?")`
**Expected:** `1122 passed` in 119 files (today's tests, unchanged, on PR A's types and fixtures); `typecheck 0`, `lint 0`; `1`; `drift 0`.

- [ ] **Step 3: Postgres, as CI's `backend-postgres` job**

On a throwaway local cluster (never production), as the `postgres` user under `/var/lib/postgresql/<new dir>`, port 55432, trust auth: CI's command from the repo root, `TEST_DATABASE_URL=postgresql://postgres@localhost:55432/postgres .venv/bin/python -m pytest -m postgres -q 2>&1 | tail -1`; then plant P9 (T3) and run `TEST_DATABASE_URL=postgresql://postgres@localhost:55432/postgres .venv/bin/python -m pytest -m postgres -q backend/tests/test_migrations.py -k 0010 2>&1 | tail -1`, and undo it; then, on a new database `ci_check` there, from `backend/` with `DATABASE_URL` pointing at it: `alembic upgrade head 2>&1 | grep "Running upgrade 0009"`, `alembic check`, `alembic downgrade base`, `alembic upgrade head`, `alembic current`. Stop the cluster and delete its directory afterwards.
**Expected:** `50 passed, 2319 deselected, 1 warning in <t>s`; P9: `1 failed, 60 deselected`; the upgrade prints the README's Step 4 line exactly (`INFO  [alembic.runtime.migration] Running upgrade 0009_memberships_one_owner -> 0010_services_affirmation, Services: the Affirmation of Faith (affirmation spec, "Data shape")`); each command exits 0, `check` prints `No new upgrade operations detected.`, `current` prints `0010_services_affirmation (head)`.

- [ ] **Step 4: No em dash added, nothing frozen touched, the branch's paths**

Run: `git diff origin/main...HEAD | grep '^+' | grep -c $'\xe2\x80\x94'`; `git diff --name-only origin/main...HEAD -- app.py streamlit_views streamlit_auth.py streamlit_tenancy.py ui_helpers.py streamlit_tests requirements.txt requirements-dev.txt .github | wc -l`; `git diff --name-status origin/main...HEAD | awk '{print $1}' | sort | uniq -c`
**Expected:** `0`; `0`; `7 A` and `25 M` (the four new backend files, the spec, this plan and the decisions doc; the modified files of T1-T2, the generated OpenAPI snapshot and types, the test fixtures and `docs/ops-runbook.md`, whose Theme PR 1 record rides along). Anything else: find why before the PR.

### Task 5: Before PR A's merge: the migration routine (OWNER + agent)

**Files:** none.

(not replayed: it needs the owner and production.) `0010_services_affirmation` reaches production through Railway's pre-deploy `alembic upgrade head` when PR A merges. Before the merge the owner follows `backend/migrations/README.md` → "Before 0010_services_affirmation", one step per message, and the agent records each result in `<scratch>/affirmation-a-results.md` (not committed). The agent never puts migration SQL in chat as a block (owner rule; 6b-2a record): it says in plain words what each step does and points to the README section.

- [ ] **Step 1 (OWNER): Backup.** "Please run the db-backup workflow on main (Actions, db-backup, Run workflow) and tell me when it is green." Record the run URL.
- [ ] **Step 2 (OWNER): Count the saved services.** "In Supabase's SQL Editor, please run the read-only query in Step 2 of 'Before 0010_services_affirmation' in backend/migrations/README.md and tell me the three numbers." Expected `version` `0009_memberships_one_owner`; anything else: stop.
- [ ] **Step 3 (agent): The SQL.** Render it as the README's Step 3 says (T2 Step 5 did) and check it is the README's block exactly. Tell the owner, in words only: "Step 3 of 'Before 0010_services_affirmation' is the SQL Railway will run, for reading only. It adds one empty column, affirmation, to the services table, in one transaction, and changes no row. If another connection holds the table for more than 5 seconds, the deploy fails safely and the old release keeps serving."

### Task 6: PR A: the draft PR, the merge, the after-deploy check, the phone check, the record (OWNER + agent)

**Files:** Modify (Step 8): `docs/ops-runbook.md`: insert `### Affirmation PR A record` right before `## Backups` (after `### Theme PR 1 record`, which rides along in PR A). A `###` heading, because `test_ops_workflows.py` pins the `##` list. The record rides along in PR B.

- [ ] **Step 1 (agent → OWNER): Ask to open PR A as a draft**

(not replayed) `gh pr list -R <repo> --head claude/slice-2-plan-4q33le --state open --json number,url` → `[]`. Send the owner exactly this, and wait for a clear yes:

> The first half of the Affirmation of Faith change, the server side, is verified on this machine: 2288 backend tests here (2251 before), today's 1122 frontend tests unchanged against it, typecheck, lint, the production build and the Postgres checks clean. It teaches the server the Affirmation card (the Apostles' Creed, the Nicene Creed or your own text, and your church's default) and adds one empty database column, so the backup and the read-only checks you did come first. You will see no change in the app yet: today's pages keep working exactly as now. The pages come in a second pull request once this one is live. May I open this one as a **draft** titled "Affirmation PR A: the server side", so the checks run? Merging stays with you.

- [ ] **Step 2 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/affirmation-pr-a-body.md" <<'BODY'
Affirmation PR A: the server side of the Affirmation of Faith (owner's decisions 1, 2 and 6 of 2026-10-24; answers A to D). Spec: docs/superpowers/specs/2026-10-24-affirmation-design.md. Plan: docs/superpowers/plans/2026-10-24-affirmation.md (Part 1). Decisions: docs/superpowers/specs/2026-10-24-affirmation-and-formatting-decisions.md. One migration (0010_services_affirmation), no new package, no new variable. The pages are PR B, opened after this one is live.

- What prints: the Word files print the creed's name (as today) or the own text; the printed bulletin prints the creed's words (the Apostles' Creed exactly as today; the ELLC Nicene Creed, "and the Son" without brackets, one sense line per paragraph with a hanging indent, then ELLC's acknowledgement) or the own text in bold. Switched off, or own text left blank: nothing prints in the Word files, the printed bulletin (PDF and Word) or the email's attachments.
- Data: services.affirmation (nullable JSON, NULL reads as the Apostles' Creed, included); a POST without it stores NULL, a PUT without it keeps the saved choice. The church default in churches.settings (GET /church; PATCH /church, admins only).
- API: ServiceDraft.affirmation (optional), ServiceOut.affirmation, GET /liturgy/config's affirmation (the card's data); the outline is unchanged, so today's pages keep their Affirmation row. OpenAPI, schema.d.ts and the frontend test fixtures regenerated or extended; no page changes.
- Safe with today's frontend: it never sends affirmation (optional here), it reads only the fields it knows, and its 1122 tests pass unchanged against the new types (plan T4 Step 2).
- Copyright: ELLC's texts may be used freely with acknowledgement (englishtexts.org permissions and guidelines, cited in the spec); the Apostles' Creed keeps today's public-domain traditional wording (owner answer B).
- Not sent to the AI (Review service, Hear it from the pews, generation), never logged.
- Tests: planted violations P1-P9 in the plan's Task 3 (switched off prints nothing, each choice and own text print right, a body without it prints as today, members cannot change the default, NULL kept and a PUT keeps the choice, the outline unchanged, the hanging indent, the after-deploy query before 0010).
- Rides along: the decisions doc and the Theme PR 1 record in docs/ops-runbook.md.

Before the merge: backend/migrations/README.md "Before 0010_services_affirmation" (backup, counts, the SQL; done). After the merge: its Step 4 (the deploy log line, the live /openapi.json, the read-only check), a minimal phone check, an "Affirmation PR A record" in docs/ops-runbook.md.

Tests: backend/tests 2251 → 2288 passed (49 → 50 Postgres-only skipped here); CI backend job 2282 → 2319 passed (with streamlit_tests' 31), 49 → 50 skipped; CI Postgres job 49 → 50 passed, 2282 → 2319 deselected; frontend unchanged, 1122 in 119 files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R <repo> --draft --base main --head claude/slice-2-plan-4q33le --title "Affirmation PR A: the server side" --body-file "<scratch>/affirmation-pr-a-body.md"
gh pr checks <NA> -R <repo> --watch --interval 30
```

Run the last line with `run_in_background: true` (or the session's GitHub tools, to the same effect). **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's `backend` job `2319 passed, 50 skipped`, its `backend-postgres` job `50 passed, 2319 deselected`, its `frontend` job `1122 passed` in 119 files. Then send: "PR #<NA> is green: backend 2319 in CI (2288 plus the 31 old Streamlit tests), Postgres 50, frontend 1122 in 119 files unchanged, and the Vercel preview builds. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <NA> -R <repo>`.

- [ ] **Step 3 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <NA> -R <repo> --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`, and T5's three results recorded. Send: "May I merge PR #<NA> with a merge commit? Railway then adds the empty column and starts the new server; the app's pages stay as they are. I will tell you when it is live, then ask you to look at one log line, run one read-only check and do a short phone check, one step at a time." On a clear yes (not replayed):

```bash
gh pr merge <NA> --merge -R <repo>
gh pr view <NA> -R <repo> --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R <repo> --workflow ci.yml --branch main --commit "$(gh pr view <NA> -R <repo> --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R <repo> --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (in the background). Record both.

- [ ] **Step 4 (agent, then OWNER): The after-deploy check (README "Before 0010_services_affirmation", Step 4)**

About three minutes after the merge (not replayed):

```bash
curl -s <api>/health/ready; echo
curl -s <api>/openapi.json | python3 -c 'import json, sys; print("ServiceAffirmation" in json.load(sys.stdin)["components"]["schemas"])'
```

**Expected:** `{"ok":true,"db":"ok"}`; `True`. `/health/ready` cannot tell the new API from the old one; the published schema can: `False` means the old release is still serving (Railway has not finished, or the deploy failed and the previous release kept serving): ask again a minute later, and after five minutes ask the owner for the deployment's status. Then ask the owner, one message each:
1. "In Railway, please open the API service, then the newest deployment, then Deploy Logs. Is there a line that says Running upgrade 0009_memberships_one_owner -> 0010_services_affirmation?" **Expected:** yes (the README's Step 4 line). No such line and a failed deployment: stop and follow the README's Step 3 note (the lock timeout; run the deploy again).
2. "Please run the read-only query in Step 4 of 'Before 0010_services_affirmation' and tell me the three numbers, then Step 2's query again." **Expected:** `0010_services_affirmation`, `1`, `0`; Step 2's counts the same as before (or more). `0009_memberships_one_owner`, `0`, `0`: not applied yet; the query answers before 0010 too, so ask again a minute later.

(not replayed: Steps 5-7 need the owner's phone and production.) One short action per message; send the next only after the answer. PR A changes no page, so the phone check only confirms the app saves and downloads as before.

- [ ] **Step 5 (OWNER, then agent): Phone A1: the Liturgy step as before**

> On your phone, open the builder's **Liturgy** step. After the Sermon Title, is the row "Affirmation of Faith · Apostles' Creed" there, as before?

- [ ] **Step 6 (OWNER, then agent): Phone A2: the downloads as before**

> On the **Review** step, download the bulletin Word file and the printed bulletin (PDF). Do both download, with the Affirmation of Faith and the Apostles' Creed where they always are?

- [ ] **Step 7 (OWNER, then agent): Phone A3: saving as before**

> Save the service (Save to archive, or Save changes if it is already saved). Does it say it is saved?

Write each step's result, with the date, into `<scratch>/affirmation-a-results.md` (not committed). A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

**What PR A's phone check cannot show.** The new choices (no page offers them until PR B: `test_affirmation.py` and `test_api_affirmation.py` cover them), the email's attachments (the same files as the downloads), a member's refused change (P5) and the exact creed texts (`test_affirmation.py`).

- [ ] **Step 8 (agent): Bring the branch to `main` and write PR A's record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward` (the branch was merged as it stood); one `## Backups` line; the last `###` heading above it, `### Theme PR 1 record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Affirmation PR A record

Affirmation PR A, the server side of the Affirmation of Faith (the card's
data, saving it with a service, the church default; owner's decisions and
answers of 2026-10-24), merged as PR #<NA> with migration
`0010_services_affirmation`. The owner followed "Before
0010_services_affirmation" in `backend/migrations/README.md`. The pages are
PR B.

| Step | Result | Date |
|---|---|---|
| 1. Backup | db-backup run <run URL>: success | <date> |
| 2. Counts before | `0009_memberships_one_owner`, <n> services, <n> churches | <date> |
| 3. The SQL | rendered from the PR's code: one empty column added in one transaction, no row changed | <date> |
| Merge and deploy | PR #<NA> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. `/health/ready` `{"ok":true,"db":"ok"}`; `/openapi.json` names `ServiceAffirmation` | <date> |
| 4. After the deploy | Deploy Logs: <the `Running upgrade 0009_memberships_one_owner -> 0010_services_affirmation` line seen / …>. `0010_services_affirmation`, new column 1, with_affirmation <n>; counts again <n> services, <n> churches | <date> |
| Phone A1. The Liturgy step | <The row "Affirmation of Faith · Apostles' Creed" as before. / …> | <date> |
| Phone A2. The downloads | <Both downloaded, the Apostles' Creed as before. / …> | <date> |
| Phone A3. Saving | <Saved. / …> | <date> |
| Not on the phone | The new choices, the email's attachments, a member's refused change and the exact creed texts: tests only (T6 "What PR A's phone check cannot show") | <date> |
| Follow-ups | <None. / One line per follow-up.> | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then (not replayed):

```bash
sed -n '/^### Affirmation PR A record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Affirmation PR A record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|sk-|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
sed -n '/^### Affirmation PR A record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c $'\xe2\x80\x94'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: Affirmation PR A record" -m "Records PR #<NA>: the migration routine, the merge and deploy, the after-deploy check and the owner's phone check. No church id, email address, token or database URL is recorded. Rides along in PR B." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** `0`; `0`; `0`; `89 passed in <t>s`; one commit, pushed. Part 1 is done; Part 2 starts from here.

# Part 2: Affirmation PR B (the pages)


Part 2 starts only after T6: PR A merged, its after-deploy check passed and its record committed on the branch, which T6 Step 8 fast-forwarded to `main`. The API types (`schema.d.ts`) already carry the new fields (T2).

### Task 7: The draft and the card (S "The Affirmation card", "Data shape", "Backward compatibility"; clarifications 3, 5, 6, 9-11)

**Files:** Create `frontend/src/lib/liturgy/affirmation.test.ts`, `frontend/src/components/builder/liturgy/affirmation-card.tsx`, `frontend/src/components/builder/liturgy/affirmation-card.test.tsx`. Modify `frontend/src/lib/api/types.ts`, `frontend/src/lib/draft/schema.ts`, `migrate.ts`, `mapping.ts`, `status.ts`, `store.ts`, `context.tsx`, `frontend/src/lib/liturgy/defaults.ts`, `cards.ts`, `summary.ts`, `frontend/src/lib/documents.ts`, `frontend/src/components/builder/liturgy/liturgy-step.tsx`, `outline-landmark.tsx`, and the tests below.

- [ ] **Step 1: Write the failing tests**

Besides the card itself, the tests pin "Save as new service" from a saved Nicene service (it posts the Nicene Creed, review fix 5), the sense lines' hanging indent (clarification 11) and the run-ahead guard (today's row when the config has no `affirmation`, clarification 10).

<!-- directives:T7_TESTS -->
**Create `frontend/src/lib/liturgy/affirmation.test.ts`:**

````
/**
 * The Affirmation of Faith in the draft (affirmation spec, "Data shape"): the
 * card's transitions, following the church default, what is sent and
 * fingerprinted (the Apostles' Creed switched on is left out of the payload,
 * so a draft saved before the change stays "Saved"), opening and saving a
 * service, "Nothing the user would lose" and the summary line.
 */
import { describe, expect, it } from "vitest";

import { documentRequest, savedCopyFingerprint, serviceBody } from "@/lib/documents";
import { followSaveMode } from "@/lib/draft/bulletin";
import { draftToServicePayload, markSaved, serviceToDraft } from "@/lib/draft/mapping";
import { setDate } from "@/lib/draft/readings";
import { isPristine, reviewStatus, saveMode } from "@/lib/draft/status";
import { churchProfile, DRAFT_NOW, savedService, testDraft, USER_ID } from "@/test/fixtures";

import {
  editAffirmationText,
  restoreAffirmationDefault,
  setAffirmationChoice,
  setAffirmationInclude,
} from "./cards";
import { applyLiturgyDefaults, DEFAULT_BENEDICTION_FALLBACK } from "./defaults";
import { affirmationSummary } from "./summary";

const OWN = "We trust in God the Holy Spirit.";
const NICENE_DEFAULT = { choice: "nicene", text: "" } as const;
const defaults = (defaultAffirmation = NICENE_DEFAULT) => ({ defaultBenediction: DEFAULT_BENEDICTION_FALLBACK, defaultAffirmation });

describe("the Affirmation of Faith card (affirmation spec)", () => {
  it("makes the card the member's own on any change, and Use church default follows the default again", () => {
    const d = testDraft();
    const off = setAffirmationInclude(d, false);
    expect(off.liturgy.affirmation).toEqual({ include: false, choice: "apostles", text: "", origin: "user" });
    expect(setAffirmationInclude(off, false)).toBe(off); // nothing changes: the same draft
    const own = editAffirmationText(setAffirmationChoice(d, "own"), OWN);
    expect(own.liturgy.affirmation).toEqual({ include: true, choice: "own", text: OWN, origin: "user" });
    // The own text stays in the draft while a creed is picked, so switching back finds it.
    expect(setAffirmationChoice(setAffirmationChoice(own, "nicene"), "own").liturgy.affirmation.text).toBe(OWN);
    expect(restoreAffirmationDefault(own, { choice: "own", text: "Church text." }).liturgy.affirmation).toEqual({
      include: true, choice: "own", text: "Church text.", origin: "default" });
  });

  it("follows the church default while the origin is default, and never after a change", () => {
    const d = testDraft();
    expect(applyLiturgyDefaults(d, defaults()).liturgy.affirmation).toEqual({
      include: true, choice: "nicene", text: "", origin: "default" });
    const followed = applyLiturgyDefaults(d, defaults());
    expect(applyLiturgyDefaults(followed, defaults())).toBe(followed);
    const mine = setAffirmationChoice(d, "own");
    expect(applyLiturgyDefaults(mine, defaults()).liturgy.affirmation).toEqual(mine.liturgy.affirmation);
    expect(applyLiturgyDefaults(d, { defaultBenediction: DEFAULT_BENEDICTION_FALLBACK })).toBe(d); // no default given
  });

  it("leaves the Apostles' Creed switched on out of the payload, and always sends it in the body", () => {
    const d = testDraft();
    expect("affirmation" in draftToServicePayload(d)).toBe(false);
    expect(documentRequest(d, "bulletin").service.affirmation).toEqual({ include: true, choice: "apostles", text: "" });
    expect(draftToServicePayload(setAffirmationInclude(d, false)).affirmation).toEqual({ include: false, choice: "apostles", text: "" });
    expect(draftToServicePayload(setAffirmationChoice(d, "nicene")).affirmation).toEqual({ include: true, choice: "nicene", text: "" });
    const own = editAffirmationText(setAffirmationChoice(d, "own"), `  ${OWN}\n`);
    expect(draftToServicePayload(own).affirmation).toEqual({ include: true, choice: "own", text: OWN });
    // Own text typed, then a creed picked: the text is not sent.
    expect(draftToServicePayload(setAffirmationChoice(own, "nicene")).affirmation?.text).toBe("");
  });

  it("opens a saved service with its Affirmation, a service without one as the Apostles' Creed, and a save keeps it Saved", () => {
    const at = { church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW };
    const old = serviceToDraft(savedService({ affirmation: undefined }), at);
    expect(old.liturgy.affirmation).toEqual({ include: true, choice: "apostles", text: "", origin: "archive" });
    expect(reviewStatus(old)).toBe("saved");
    const off = serviceToDraft(savedService({ affirmation: { include: false, choice: "nicene", text: "" } }), at);
    expect(off.liturgy.affirmation).toEqual({ include: false, choice: "nicene", text: "", origin: "archive" });
    expect(reviewStatus(off)).toBe("saved");
    expect(reviewStatus(setAffirmationInclude(off, true))).toBe("unsaved_changes");
    // A save makes a card that followed the default the service's own.
    const fresh = applyLiturgyDefaults(testDraft(), defaults());
    const saved = markSaved(fresh, savedService(), "fp");
    expect(saved.liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "archive" });
  });

  it("posts a saved service's Nicene Creed when it is saved as a new service on another date", () => {
    const at = { church: churchProfile(), user: { id: USER_ID }, now: DRAFT_NOW };
    const opened = serviceToDraft(savedService({ affirmation: { include: true, choice: "nicene", text: "" } }), at);
    const copy = followSaveMode(setDate(opened, "2026-10-11", "user"));
    expect(saveMode(copy)).toBe("copy");
    expect(copy.liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "archive" });
    expect(serviceBody(copy).affirmation).toEqual({ include: true, choice: "nicene", text: "" });
  });

  it("fingerprints the archive's copy the way the body is sent (a missing Affirmation is the Apostles' Creed)", () => {
    const body = documentRequest(testDraft(), "bulletin").service;
    const fromServer = { ...body, affirmation: undefined };
    expect(savedCopyFingerprint(fromServer)).toBe(savedCopyFingerprint(body));
    const own = documentRequest(editAffirmationText(setAffirmationChoice(testDraft(), "own"), OWN), "bulletin").service;
    expect(savedCopyFingerprint({ ...own, affirmation: { include: true, choice: "own", text: ` ${OWN} ` } })).toBe(savedCopyFingerprint(own));
    expect(savedCopyFingerprint(own)).not.toBe(savedCopyFingerprint(body));
  });

  it("counts a changed Affirmation as work, and one following the default as none", () => {
    const d = testDraft();
    expect(isPristine(d)).toBe(true);
    expect(isPristine(applyLiturgyDefaults(d, defaults()))).toBe(true);
    expect(isPristine(setAffirmationInclude(d, true))).toBe(false); // the same value, but the member's own now
  });

  it("names the Affirmation in the summary", () => {
    const d = testDraft();
    expect(affirmationSummary(d.liturgy.affirmation)).toBe("Affirmation of Faith: Apostles' Creed");
    expect(affirmationSummary(setAffirmationChoice(d, "nicene").liturgy.affirmation)).toBe("Affirmation of Faith: Nicene Creed");
    expect(affirmationSummary(setAffirmationChoice(d, "own").liturgy.affirmation)).toBe("Affirmation of Faith: Your own text (nothing typed yet)");
    expect(affirmationSummary(editAffirmationText(setAffirmationChoice(d, "own"), OWN).liturgy.affirmation)).toBe(
      "Affirmation of Faith: Your own text");
    expect(affirmationSummary(setAffirmationInclude(d, false).liturgy.affirmation)).toBe("Affirmation of Faith: Off");
  });
});
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````
    const d = testDraft();
    expect(DRAFT_VERSION).toBe(4);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 4,
      user_id: USER_ID,
````

**with:**

````
    const d = testDraft();
    expect(DRAFT_VERSION).toBe(5);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 5,
      user_id: USER_ID,
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````
      },
      liturgy: { sermon_title: "", include_communion: true, communion_origin: "default", custom_elements: [] },
      bulletin: {
````

**with:**

````
      },
      liturgy: {
        sermon_title: "",
        include_communion: true,
        communion_origin: "default",
        custom_elements: [],
        affirmation: { include: true, choice: "apostles", text: "", origin: "default" }, // the affirmation spec
      },
      bulletin: {
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````
    expect(older.liturgy.cards.benediction.text).toBe(DEFAULT_BENEDICTION_FALLBACK); // an API without the field
  });
````

**with:**

````
    expect(older.liturgy.cards.benediction.text).toBe(DEFAULT_BENEDICTION_FALLBACK); // an API without the field
    expect(older.liturgy.affirmation).toEqual({ include: true, choice: "apostles", text: "", origin: "default" });
    const own = freshDraft({ church: churchProfile({ default_affirmation: { choice: "own", text: "We trust in God." } }), user, now: DRAFT_NOW });
    expect(own.liturgy.affirmation).toEqual({ include: true, choice: "own", text: "We trust in God.", origin: "default" });
    const nicene = freshDraft({ church: churchProfile({ default_affirmation: { choice: "nicene", text: "stale" } }), user, now: DRAFT_NOW });
    expect(nicene.liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "default" });
  });
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````
      { ...d, last_step: "summary" },
      { ...d, version: 5 },
      { ...d, bulletin: undefined }, // version 3 needs the bulletin (PR 2b)
````

**with:**

````
      { ...d, last_step: "summary" },
      { ...d, version: 6 },
      { ...d, bulletin: undefined }, // version 3 needs the bulletin (PR 2b)
````

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

````
      { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: undefined } } },
      { ...d, updated_at: "not a time" },
````

**with:**

````
      { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: undefined } } },
      { ...d, liturgy: { ...d.liturgy, affirmation: undefined } }, // version 5 needs the Affirmation (affirmation spec)
      { ...d, liturgy: { ...d.liturgy, affirmation: { ...d.liturgy.affirmation, choice: "brief_statement" } } },
      { ...d, liturgy: { ...d.liturgy, affirmation: { ...d.liturgy.affirmation, origin: "typed" } } },
      { ...d, updated_at: "not a time" },
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````
const OWNER = { userId: USER_ID, churchId: churchProfile().id };

````

**with:**

````
const OWNER = { userId: USER_ID, churchId: churchProfile().id };
/** What 4 → 5 gives a saved service's draft (the affirmation spec). */
const ARCHIVED_APOSTLES = { include: true, choice: "apostles", text: "", origin: "archive" } as const;

````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````
    const d = testDraft();
    expect(Object.keys(migrations)).toEqual(["1", "2", "3"]);
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
````

**with:**

````
    const d = testDraft();
    expect(Object.keys(migrations)).toEqual(["1", "2", "3", "4"]);
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 4,
      save_key_fingerprint: null,
````

**with:**

````
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 5,
      save_key_fingerprint: null,
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````
    const migrated = parseStoredDraft(JSON.stringify(saved), OWNER);
    expect(migrated).toEqual({ ...testDraft(), ...saved, version: 4, bulletin: freshBulletin() });
    expect(reviewStatus(migrated)).toBe("saved");
````

**with:**

````
    const migrated = parseStoredDraft(JSON.stringify(saved), OWNER);
    expect(migrated).toEqual({
      ...testDraft(),
      ...saved,
      version: 5,
      bulletin: freshBulletin(),
      liturgy: { ...saved.liturgy, affirmation: ARCHIVED_APOSTLES },
    });
    expect(reviewStatus(migrated)).toBe("saved");
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````
    const migrated = parseStoredDraft(JSON.stringify(v3), OWNER);
    expect(migrated).toEqual({ ...v3, version: 4, bulletin: { ...bulletin, cover_image_id: null } });
    expect(reviewStatus(migrated)).toBe("saved");
  });
````

**with:**

````
    const migrated = parseStoredDraft(JSON.stringify(v3), OWNER);
    expect(migrated).toEqual({
      ...v3,
      version: 5,
      bulletin: { ...bulletin, cover_image_id: null },
      liturgy: { ...v3.liturgy, affirmation: ARCHIVED_APOSTLES },
    });
    expect(reviewStatus(migrated)).toBe("saved");
  });

  it("migrates a version 4 draft: the Apostles' Creed, switched on, following the default unless saved, and a saved draft stays Saved (affirmation spec)", () => {
    const d = testDraft();
    const { affirmation, ...liturgy } = d.liturgy;
    expect(affirmation).toEqual({ include: true, choice: "apostles", text: "", origin: "default" });
    const v4 = { ...d, version: 4, liturgy };
    expect(parseStoredDraft(JSON.stringify(v4), OWNER)).toEqual(d);
    // The payload leaves out the Apostles' Creed switched on, so 3b's fingerprint is today's.
    const payload = draftToServicePayload(d);
    expect("affirmation" in payload).toBe(false);
    const editing = { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" };
    const saved = { ...v4, editing, saved_fingerprint: fingerprint(payload), last_step: "review" };
    const migrated = parseStoredDraft(JSON.stringify(saved), OWNER);
    expect(migrated.liturgy).toEqual({ ...liturgy, affirmation: ARCHIVED_APOSTLES });
    expect(reviewStatus(migrated)).toBe("saved");
    expect(() => parseStoredDraft(JSON.stringify({ ...v4, liturgy: "none" }), OWNER)).toThrow(DraftRestoreError);
  });
````

**In `frontend/src/lib/draft/migrate.test.ts`, replace:**

````
      ["version 0", JSON.stringify({ ...d, version: 0 })],
      ["a future version", JSON.stringify({ ...d, version: 5 })],
      ["schema-invalid", JSON.stringify({ ...d, readings: { ...d.readings, scriptures: "Psalm 23" } })],
````

**with:**

````
      ["version 0", JSON.stringify({ ...d, version: 0 })],
      ["a future version", JSON.stringify({ ...d, version: 6 })],
      ["schema-invalid", JSON.stringify({ ...d, readings: { ...d.readings, scriptures: "Psalm 23" } })],
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````
  it("backs up a draft it cannot restore, starts fresh and reports it once", () => {
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 5 }), JSON.stringify({ version: 1 })]) {
      const { storage, data } = memoryStorage({ [KEY]: raw });
````

**with:**

````
  it("backs up a draft it cannot restore, starts fresh and reports it once", () => {
    for (const raw of ["{not json", JSON.stringify({ ...testDraft(), version: 6 }), JSON.stringify({ version: 1 })]) {
      const { storage, data } = memoryStorage({ [KEY]: raw });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````
    // The backup cannot be written (quota): the unrestorable draft stays in the main key until the user edits.
    const raw = JSON.stringify({ ...testDraft(), version: 5 });
    const { storage, data } = memoryStorage({ [KEY]: raw, [corruptDraftKey(USER_ID, GRACE.id)]: "older backup" });
````

**with:**

````
    // The backup cannot be written (quota): the unrestorable draft stays in the main key until the user edits.
    const raw = JSON.stringify({ ...testDraft(), version: 6 });
    const { storage, data } = memoryStorage({ [KEY]: raw, [corruptDraftKey(USER_ID, GRACE.id)]: "older backup" });
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````
    store.flush();
    expect(stored(data)).toMatchObject({ version: 4, readings: { occasion: "Mine" } });
    expect(notices).toEqual([]);
````

**with:**

````
    store.flush();
    expect(stored(data)).toMatchObject({ version: 5, readings: { occasion: "Mine" } });
    expect(notices).toEqual([]);
````

**In `frontend/src/lib/draft/store.test.ts`, replace:**

````
    builder.flush(); // ...then the builder unmounts and flushes,
    expect(stored(data)).toMatchObject({ version: 4, readings: { occasion: "Mine" } });
    services.store.syncFromStorage({ quiet: true }); // and Services reads it back once mounted.
````

**with:**

````
    builder.flush(); // ...then the builder unmounts and flushes,
    expect(stored(data)).toMatchObject({ version: 5, readings: { occasion: "Mine" } });
    services.store.syncFromStorage({ quiet: true }); // and Services reads it back once mounted.
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````
      save_key_fingerprint: null,
      version: 4,
      editing: { service_id: SERVICE_ID, saved_at: "2026-10-01T14:42:00.123456+00:00", date_iso: "2026-10-04" },
````

**with:**

````
      save_key_fingerprint: null,
      version: 5,
      editing: { service_id: SERVICE_ID, saved_at: "2026-10-01T14:42:00.123456+00:00", date_iso: "2026-10-04" },
````

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

````
      },
      liturgy: { sermon_title: "Living Water", include_communion: true, communion_origin: "archive" },
    });
````

**with:**

````
      },
      liturgy: {
        sermon_title: "Living Water",
        include_communion: true,
        communion_origin: "archive",
        affirmation: { include: true, choice: "apostles", text: "", origin: "archive" },
      },
    });
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { addCustomElement, editCardText, setCardEnabled, setCommunion, setSermonTitle } from "@/lib/liturgy/cards";
import { setAnnouncement, setCover, setPerson } from "@/lib/draft/bulletin";
````

**with:**

````
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import {
  addCustomElement,
  editAffirmationText,
  editCardText,
  setAffirmationChoice,
  setCardEnabled,
  setCommunion,
  setSermonTitle,
} from "@/lib/liturgy/cards";
import { setAnnouncement, setCover, setPerson } from "@/lib/draft/bulletin";
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````
        bulletin: serviceBulletin(), // always sent (printed bulletin PR 2b), here with nothing filled in
      },
````

**with:**

````
        bulletin: serviceBulletin(), // always sent (printed bulletin PR 2b), here with nothing filled in
        affirmation: { include: true, choice: "apostles", text: "" }, // always sent (the affirmation spec)
      },
````

**In `frontend/src/lib/documents.test.ts`, replace:**

````
    expect(service.custom_elements?.[0]).toEqual({ label: "L".repeat(200), text: "T".repeat(10_000), insert_after: "end" });

````

**with:**

````
    expect(service.custom_elements?.[0]).toEqual({ label: "L".repeat(200), text: "T".repeat(10_000), insert_after: "end" });
    const own = setAffirmationChoice(editAffirmationText(d, "a".repeat(20_005)), "own");
    expect(documentRequest(own, "bulletin").service.affirmation).toEqual({ include: true, choice: "own", text: "a".repeat(20_000) });

````

**Create `frontend/src/components/builder/liturgy/affirmation-card.test.tsx`:**

````
/**
 * The Affirmation of Faith card on the Liturgy step (affirmation spec, "The
 * Affirmation card"), in the real builder layout against the fake API, as
 * liturgy-step.test.tsx renders it. The clock is Tuesday, September 29, 2026.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  gmailConnection,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { AFFIRMATION_OFF, OWN_TEXT_BLANK, OWN_TEXT_HINT } from "./affirmation-card";
import { LiturgyStep } from "./liturgy-step";

const KEY = draftKey(USER_ID, church().id);
const TITLE = "Include Affirmation of Faith";
const OWN = "We trust in God the Holy Spirit.";

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

function renderStep(draft: DraftV1 = testDraft(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
    ...routes,
  });
  return renderWithProviders(
    <>
      <BuilderLayout>
        <LiturgyStep />
      </BuilderLayout>
      <Toaster />
    </>,
    { me: me(), church: church(), path: "/builder/liturgy" },
  );
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss();
});

afterEach(() => {
  vi.useRealTimers();
});

async function card() {
  return screen.findByRole("region", { name: TITLE });
}

describe("the Affirmation of Faith card (affirmation spec)", () => {
  it("starts on, with the church's default chosen, and shows the creed and its credit behind Show creed text", async () => {
    const { user } = renderStep();
    const region = await card();
    expect(within(region).getByRole("switch", { name: TITLE })).toBeChecked();
    expect(within(region).getByText("Your church's default.")).toBeInTheDocument();
    const choices = within(region).getAllByRole("radio");
    expect(choices.map((radio) => radio.closest("label")?.textContent)).toEqual(["Apostles' Creed", "Nicene Creed", "Your own text"]);
    expect(within(region).getByRole("radio", { name: "Apostles' Creed" })).toBeChecked();
    // 44 px rows at every width (375 px included).
    for (const radio of choices) expect(radio.closest("label")).toHaveClass("min-h-11");
    await user.click(within(region).getByRole("radio", { name: "Nicene Creed" }));
    await user.click(within(region).getByRole("button", { name: "Show creed text" }));
    // One line per sense line, each with a hanging indent (a line that wraps on a phone reads as one).
    for (const line of ["We believe in one God,", "the Father, the Almighty,"]) {
      expect(within(region).getByText(line)).toHaveClass("pl-4", "-indent-4");
    }
    expect(within(region).getByText(/Consultation \(ELLC\), and used by permission\./)).toBeInTheDocument();
    expect(within(region).getByText("You changed this.")).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.affirmation).toEqual({ include: true, choice: "nicene", text: "", origin: "user" }));
    expect(region.textContent).not.toContain("\u2014");
  });

  it("switched off hides the choices and says it is not printed or emailed", async () => {
    const { user } = renderStep();
    const region = await card();
    await user.click(within(region).getByRole("switch", { name: TITLE }));
    expect(within(region).queryAllByRole("radio")).toEqual([]);
    expect(within(region).getByText(`${AFFIRMATION_OFF} You changed this.`)).toBeInTheDocument();
    await waitFor(() => expect(stored().liturgy.affirmation.include).toBe(false));
    expect(region.textContent).not.toContain("\u2014");
  });

  it("takes own text in a box like a prayer card's, and Use church default puts the default back with focus on the switch", async () => {
    const { user } = renderStep();
    const region = await card();
    await user.click(within(region).getByRole("radio", { name: "Your own text" }));
    const box = within(region).getByRole("textbox", { name: "Your own text" });
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} ${OWN_TEXT_BLANK}`);
    expect(box).toHaveAttribute("maxlength", "20000");
    await user.type(box, OWN);
    expect(box).toHaveAccessibleDescription(OWN_TEXT_HINT);
    await waitFor(() => expect(stored().liturgy.affirmation).toEqual({ include: true, choice: "own", text: OWN, origin: "user" }));
    await user.click(within(region).getByRole("button", { name: "Use church default" }));
    await waitFor(() => expect(within(region).getByRole("switch", { name: TITLE })).toHaveFocus());
    expect(within(region).getByRole("radio", { name: "Apostles' Creed" })).toBeChecked();
    expect(within(region).queryByRole("button", { name: "Use church default" })).toBeNull();
    await waitFor(() => expect(stored().liturgy.affirmation).toEqual({ include: true, choice: "apostles", text: "", origin: "default" }));
  });

  it("follows a church whose default is its own text, and says so for a saved service", async () => {
    const own = churchProfile({ default_affirmation: { choice: "own", text: OWN } });
    renderStep(testDraft(), { "GET /church": own });
    const region = await card();
    await waitFor(() => expect(within(region).getByRole("textbox", { name: "Your own text" })).toHaveValue(OWN));
    expect(within(region).getByRole("radio", { name: "Your own text" })).toBeChecked();
  });

  it("keeps the Affirmation row when the API sends no card data (the pages ahead of the server side)", async () => {
    const older = { ...liturgyConfig(), affirmation: undefined } as unknown as ReturnType<typeof liturgyConfig>;
    renderStep(testDraft(), { "GET /liturgy/config": older });
    const order = await screen.findByRole("list", { name: "Order of worship" });
    await waitFor(() =>
      expect(within(order).getAllByRole("listitem").map((li) => li.textContent)).toContain("Affirmation of Faith · Apostles' Creed"),
    );
    expect(screen.queryByRole("region", { name: TITLE })).toBeNull();
  });

  it("shows a saved service's choice as set from the saved service", async () => {
    const d = testDraft();
    renderStep({ ...d, liturgy: { ...d.liturgy, affirmation: { include: false, choice: "nicene", text: "", origin: "archive" } } });
    const region = await card();
    expect(within(region).getByRole("switch", { name: TITLE })).not.toBeChecked();
    expect(within(region).getByText(`${AFFIRMATION_OFF} Set from the saved service.`)).toBeInTheDocument();
    expect(within(region).getByRole("button", { name: "Use church default" })).toBeInTheDocument();
  });
});
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````
      "Sermon Title · [Sermon title]",
      "Affirmation of Faith · Apostles' Creed",
      "Second Hymn",
````

**with:**

````
      "Sermon Title · [Sermon title]",
      "Include Affirmation of Faith",
      "Second Hymn",
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    // After the Sermon row come two landmark rows, then the communion card, whose heading takes focus.
    await waitFor(() => expect(within(card(COMMUNION)).getByRole("heading", { name: COMMUNION })).toHaveFocus());
    await user.click(within(card("Minute for Mission")).getByRole("button", { name: "More actions for Minute for Mission" }));
````

**with:**

````
    await user.click(await screen.findByRole("menuitem", { name: "Remove" }));
    // After the Sermon row comes the Affirmation of Faith card (affirmation spec), whose heading takes focus.
    const affirmation = "Include Affirmation of Faith";
    await waitFor(() => expect(within(card(affirmation)).getByRole("heading", { name: affirmation })).toHaveFocus());
    await user.click(within(card("Minute for Mission")).getByRole("button", { name: "More actions for Minute for Mission" }));
````
<!-- /directives:T7_TESTS -->

- [ ] **Step 2: Run them and see them fail**

Run: `(cd frontend && npx vitest run src/lib/liturgy/affirmation.test.ts src/lib/draft/schema.test.ts src/lib/draft/migrate.test.ts src/lib/draft/store.test.ts src/lib/draft/mapping.test.ts src/lib/documents.test.ts src/components/builder/liturgy/affirmation-card.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "Test Files|Tests ")`
**Expected:**
```
@@T7FAIL@@
```
(The two new files fail to load: their imports do not exist yet.)

- [ ] **Step 3: Write the draft and the card**

<!-- directives:T7_IMPL -->
**In `frontend/src/lib/api/types.ts`, replace:**

````
export type CommunionBlock = components["schemas"]["CommunionBlockOut"];
/** `POST /liturgy/generate` (slice 4a): the body the step sends (one section, no overrides) and the answer. */
````

**with:**

````
export type CommunionBlock = components["schemas"]["CommunionBlockOut"];
/** The affirmation spec: the Affirmation card's labels and choices (`GET /liturgy/config`), a service's and the church's. */
export type AffirmationConfig = components["schemas"]["AffirmationConfigOut"];
export type ServiceAffirmation = components["schemas"]["ServiceAffirmation"];
export type ChurchAffirmation = components["schemas"]["ChurchAffirmation"];
/** `POST /liturgy/generate` (slice 4a): the body the step sends (one section, no overrides) and the answer. */
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````
 * cover picture, `bulletin.cover_image_id`, and its box to check ("cover",
 * first in `CARRY_KEYS`). The names `DraftV1` and
 * `draftV1Schema` stay, so no importer changes. Strings are
````

**with:**

````
 * cover picture, `bulletin.cover_image_id`, and its box to check ("cover",
 * first in `CARRY_KEYS`). Version 5 (the affirmation spec, 2026-10-24) adds
 * `liturgy.affirmation`, the Affirmation of Faith card. The names `DraftV1` and
 * `draftV1Schema` stay, so no importer changes. Strings are
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````

export const DRAFT_VERSION = 4;

````

**with:**

````

export const DRAFT_VERSION = 5;

````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````
export type LiturgyCard = z.infer<typeof card>;

````

**with:**

````
export type LiturgyCard = z.infer<typeof card>;

/** The Affirmation of Faith's choices (`affirmation.CHOICES`). */
export const AFFIRMATION_CHOICES = ["apostles", "nicene", "own"] as const;
export type AffirmationChoice = (typeof AFFIRMATION_CHOICES)[number];
/**
 * The Affirmation of Faith card (affirmation spec): switched on or off, the
 * choice, the own text (kept while another choice is picked; sent only for
 * "own") and whether it follows the church's default.
 */
const affirmation = z.object({
  include: z.boolean(),
  choice: z.enum(AFFIRMATION_CHOICES),
  text,
  origin: z.enum(["default", "user", "archive"]),
});
export type DraftAffirmation = z.infer<typeof affirmation>;
/** The church's default (`GET /church`'s `default_affirmation`). */
export type AffirmationDefault = { choice: AffirmationChoice; text: string };
/** What every service printed before the change, and a church's default until an admin sets one. */
export const APOSTLES_DEFAULT: AffirmationDefault = { choice: "apostles", text: "" };

/** A card following the church's default: switched on, its choice, and its text for "own". */
export function affirmationFromDefault(def: AffirmationDefault): DraftAffirmation {
  return { include: true, choice: def.choice, text: def.choice === "own" ? def.text : "", origin: "default" };
}

````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````
    custom_elements: z.array(z.object({ id: text, label: text, text, insert_after: text })),
  }),
````

**with:**

````
    custom_elements: z.array(z.object({ id: text, label: text, text, insert_after: text })),
    affirmation,
  }),
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````
 * `freshDraft` (slice 2a) and the church's default benediction, which an
 * untouched Benediction card shows (slice 4a; an older API leaves it out).
 */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean; default_benediction?: string };

````

**with:**

````
 * `freshDraft` (slice 2a) and the church's default benediction, which an
 * untouched Benediction card shows (slice 4a; an older API leaves it out),
 * and its default Affirmation of Faith (affirmation spec; likewise).
 */
export type DraftChurch = {
  id: string;
  timezone?: string | null;
  timezone_valid?: boolean;
  default_benediction?: string;
  default_affirmation?: AffirmationDefault;
};

````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````
 * Halverson text, when the profile has none; slice 4b), communion on for a
 * first Sunday, an empty Bulletin step (PR 2b; last week's carries in when
 * the Bulletin step or Review shows it), a new save key with no pending
````

**with:**

````
 * Halverson text, when the profile has none; slice 4b), communion on for a
 * first Sunday, the Affirmation of Faith following the church's default
 * (the Apostles' Creed when the profile has none), an empty Bulletin step
 * (PR 2b; last week's carries in when
 * the Bulletin step or Review shows it), a new save key with no pending
````

**In `frontend/src/lib/draft/schema.ts`, replace:**

````
      custom_elements: [],
    },
````

**with:**

````
      custom_elements: [],
      affirmation: affirmationFromDefault(church.default_affirmation ?? APOSTLES_DEFAULT),
    },
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````
 * payload leaves out a null picture).
 */
````

**with:**

````
 * payload leaves out a null picture).
 *
 * 4 → 5 (the affirmation spec): `liturgy.affirmation` is the Apostles' Creed,
 * switched on, as every draft printed before: "archive" for a saved service
 * (it prints as saved, and stays "Saved": the payload leaves that value
 * out), "default" otherwise (it follows the church's default, which is the
 * Apostles' Creed until an admin changes it).
 */
````

**In `frontend/src/lib/draft/migrate.ts`, replace:**

````
  3: (draft) => ({ ...draft, bulletin: isRecord(draft.bulletin) ? { ...draft.bulletin, cover_image_id: null } : draft.bulletin }),
};
````

**with:**

````
  3: (draft) => ({ ...draft, bulletin: isRecord(draft.bulletin) ? { ...draft.bulletin, cover_image_id: null } : draft.bulletin }),
  4: (draft) => {
    if (!isRecord(draft.liturgy)) return draft;
    const origin = isRecord(draft.editing) ? "archive" : "default";
    return { ...draft, liturgy: { ...draft.liturgy, affirmation: { include: true, choice: "apostles", text: "", origin } } };
  },
};
````

**In `frontend/src/lib/liturgy/defaults.ts`, replace:**

````
 *
 * Both return the same object when nothing changes, so the draft store can
 * run them after every change without writing.
````

**with:**

````
 *
 * - An Affirmation of Faith card whose origin is "default" follows the
 *   church's `default_affirmation` (affirmation spec): switched on, its
 *   choice and, for "own", its text.
 *
 * They return the same object when nothing changes, so the draft store can
 * run them after every change without writing.
````

**In `frontend/src/lib/liturgy/defaults.ts`, replace:**

````
import { isFirstSundayOfMonth } from "@/lib/dates";
import type { DraftV1 } from "@/lib/draft/schema";

````

**with:**

````
import { isFirstSundayOfMonth } from "@/lib/dates";
import { affirmationFromDefault, type AffirmationDefault, type DraftV1 } from "@/lib/draft/schema";

````

**In `frontend/src/lib/liturgy/defaults.ts`, replace:**

````

export type LiturgyDefaults = { defaultBenediction: string };

````

**with:**

````

/** `defaultAffirmation` left out (a caller from before the affirmation spec): the card is left as it is. */
export type LiturgyDefaults = { defaultBenediction: string; defaultAffirmation?: AffirmationDefault };

````

**In `frontend/src/lib/liturgy/defaults.ts`, replace:**

````

export function applyLiturgyDefaults(d: DraftV1, { defaultBenediction }: LiturgyDefaults): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
````

**with:**

````

export function applyAffirmationDefault(d: DraftV1, def: AffirmationDefault): DraftV1 {
  const a = d.liturgy.affirmation;
  if (a.origin !== "default") return d;
  const next = affirmationFromDefault(def);
  if (a.include === next.include && a.choice === next.choice && a.text === next.text) return d;
  return { ...d, liturgy: { ...d.liturgy, affirmation: next } };
}

export function applyLiturgyDefaults(d: DraftV1, { defaultBenediction, defaultAffirmation }: LiturgyDefaults): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
````

**In `frontend/src/lib/liturgy/defaults.ts`, replace:**

````
  }
  return applyCommunionDefault(next);
}
````

**with:**

````
  }
  next = applyCommunionDefault(next);
  return defaultAffirmation === undefined ? next : applyAffirmationDefault(next, defaultAffirmation);
}
````

**In `frontend/src/lib/liturgy/cards.ts`, replace:**

````
 */
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
import { SECTION_KEYS } from "@/lib/draft/schema";

````

**with:**

````
 */
import type { AffirmationChoice, AffirmationDefault, DraftAffirmation, DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
import { affirmationFromDefault, SECTION_KEYS } from "@/lib/draft/schema";

````

**In `frontend/src/lib/liturgy/cards.ts`, replace:**

````

/** Appends an element with its label and text trimmed and its place normalized (S "On Add"). */
````

**with:**

````

function withAffirmation(d: DraftV1, next: DraftAffirmation): DraftV1 {
  const a = d.liturgy.affirmation;
  if (a.include === next.include && a.choice === next.choice && a.text === next.text && a.origin === next.origin) return d;
  return withLiturgy(d, { affirmation: next });
}

/** The Affirmation of Faith switch, choice and own text (affirmation spec): each makes the card the member's own. */
export function setAffirmationInclude(d: DraftV1, include: boolean): DraftV1 {
  return withAffirmation(d, { ...d.liturgy.affirmation, include, origin: "user" });
}

export function setAffirmationChoice(d: DraftV1, choice: AffirmationChoice): DraftV1 {
  return withAffirmation(d, { ...d.liturgy.affirmation, choice, origin: "user" });
}

export function editAffirmationText(d: DraftV1, text: string): DraftV1 {
  return withAffirmation(d, { ...d.liturgy.affirmation, text, origin: "user" });
}

/** "Use church default": the church's default, followed again. */
export function restoreAffirmationDefault(d: DraftV1, def: AffirmationDefault): DraftV1 {
  return withAffirmation(d, affirmationFromDefault(def));
}

/** Appends an element with its label and text trimmed and its place normalized (S "On Add"). */
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
 * draft v3 migration; the bodies sent always carry it (`serviceBody`).
 */
````

**with:**

````
 * draft v3 migration; the bodies sent always carry it (`serviceBody`).
 *
 * The affirmation spec: the payload holds `affirmation` only when it is not
 * the Apostles' Creed switched on (what every service printed before), so a
 * draft saved before the change stays "Saved" after the v5 migration; the
 * bodies sent always carry it (`serviceBody`), so a save never leaves an
 * older choice in place.
 */
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
  SLOTS,
  type DraftChurch,
````

**with:**

````
  SLOTS,
  type AffirmationChoice,
  type DraftAffirmation,
  type DraftChurch,
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
  bulletin?: ServiceBulletin;
};

````

**with:**

````
  bulletin?: ServiceBulletin;
  /** The Affirmation of Faith (affirmation spec); left out when it is the Apostles' Creed, switched on. */
  affirmation?: AffirmationPayload;
};

/** The API's `ServiceAffirmation`. */
export type AffirmationPayload = { include: boolean; choice: AffirmationChoice; text: string };
/** What a service prints when it says nothing: the Apostles' Creed, switched on. */
export const TODAYS_AFFIRMATION: AffirmationPayload = { include: true, choice: "apostles", text: "" };

/** The card as sent: the own text trimmed, and only for "own". */
export function affirmationPayload(a: DraftAffirmation): AffirmationPayload {
  return { include: a.include, choice: a.choice, text: a.choice === "own" ? a.text.trim() : "" };
}

````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
  const bulletin = bulletinPayload(draft);
  const liturgy: Partial<Record<SectionKey, string>> = {};
````

**with:**

````
  const bulletin = bulletinPayload(draft);
  const affirmation = affirmationPayload(draft.liturgy.affirmation);
  const today = affirmation.include && affirmation.choice === "apostles";
  const liturgy: Partial<Record<SectionKey, string>> = {};
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
    ...(isBlankBulletin(bulletin) ? {} : { bulletin }),
  };
````

**with:**

````
    ...(isBlankBulletin(bulletin) ? {} : { bulletin }),
    ...(today ? {} : { affirmation }),
  };
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
      })),
    },
````

**with:**

````
      })),
      // A server from before the affirmation spec (only if it were reverted) sends none: the Apostles' Creed.
      affirmation: { ...(service.affirmation ?? TODAYS_AFFIRMATION), origin: "archive" },
    },
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
 * is opened (owner answer 4): a Benediction following the church default
 * keeps its text with origin "archive" ("empty" when it is blank), and
 * communion following the first-Sunday rule keeps its setting with origin
 * "archive". Neither changes the payload, so the draft is "Saved".
 */
````

**with:**

````
 * is opened (owner answer 4): a Benediction following the church default
 * keeps its text with origin "archive" ("empty" when it is blank),
 * communion following the first-Sunday rule keeps its setting with origin
 * "archive", and so does an Affirmation of Faith following the church
 * default (affirmation spec). None changes the payload, so the draft is "Saved".
 */
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
  const communion_origin = d.liturgy.communion_origin === "default" ? "archive" : d.liturgy.communion_origin;
  return {
````

**with:**

````
  const communion_origin = d.liturgy.communion_origin === "default" ? "archive" : d.liturgy.communion_origin;
  const affirmation =
    d.liturgy.affirmation.origin === "default" ? { ...d.liturgy.affirmation, origin: "archive" as const } : d.liturgy.affirmation;
  return {
````

**In `frontend/src/lib/draft/mapping.ts`, replace:**

````
    saved_fingerprint: fp,
    liturgy: { ...d.liturgy, cards, communion_origin },
    // Saved as a different service (a POST): what "Save as new service" set
````

**with:**

````
    saved_fingerprint: fp,
    liturgy: { ...d.liturgy, cards, communion_origin, affirmation },
    // Saved as a different service (a POST): what "Save as new service" set
````

**In `frontend/src/lib/documents.ts`, replace:**

````
 * the cover picture's id or null (PR 3b: a body that says nothing would keep
 * the saved picture and print PR 1's box).
 */
````

**with:**

````
 * the cover picture's id or null (PR 3b: a body that says nothing would keep
 * the saved picture and print PR 1's box), and the Affirmation of Faith
 * always (the affirmation spec: a body that says nothing would keep the
 * saved choice), its own text cut to the section limit.
 */
````

**In `frontend/src/lib/documents.ts`, replace:**

````
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload } from "@/lib/draft/mapping";
import { CARRY_KEYS, SLOTS, type DraftV1, type Slot } from "@/lib/draft/schema";
````

**with:**

````
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload, TODAYS_AFFIRMATION, type AffirmationPayload } from "@/lib/draft/mapping";
import { CARRY_KEYS, SLOTS, type DraftV1, type Slot } from "@/lib/draft/schema";
````

**In `frontend/src/lib/documents.ts`, replace:**

````
    bulletin: clipBulletin(payload.bulletin ?? emptyServiceBulletin()),
  };
````

**with:**

````
    bulletin: clipBulletin(payload.bulletin ?? emptyServiceBulletin()),
    affirmation: { ...(payload.affirmation ?? TODAYS_AFFIRMATION), text: clipChars(payload.affirmation?.text ?? "", MAX_CARD_TEXT) },
  };
````

**In `frontend/src/lib/documents.ts`, replace:**

````
  bulletin?: ServiceBulletin | null;
};
````

**with:**

````
  bulletin?: ServiceBulletin | null;
  /** The affirmation spec; missing reads as the Apostles' Creed, switched on. */
  affirmation?: AffirmationPayload | null;
};
````

**In `frontend/src/lib/documents.ts`, replace:**

````
 * bulletin fields count too (printed bulletin PR 2b): another device's
 * change to the announcements is someone else's change.
 * `withHymnal` false leaves the hymnal out: a body with none takes the
````

**with:**

````
 * bulletin fields count too (printed bulletin PR 2b): another device's
 * change to the announcements is someone else's change, and so is the
 * Affirmation of Faith (the affirmation spec; missing is the Apostles' Creed).
 * `withHymnal` false leaves the hymnal out: a body with none takes the
````

**In `frontend/src/lib/documents.ts`, replace:**

````
    bulletin: savedBulletin(s.bulletin ?? emptyServiceBulletin(), clean),
  });
}
````

**with:**

````
    bulletin: savedBulletin(s.bulletin ?? emptyServiceBulletin(), clean),
    affirmation: savedAffirmation(s.affirmation ?? TODAYS_AFFIRMATION, clean),
  });
}

/** An Affirmation of Faith as the archive keeps it (`affirmation.read`, then Word-safe and trimmed): text only for "own". */
function savedAffirmation(a: AffirmationPayload, clean: (text: string) => string) {
  return { include: a.include, choice: a.choice, text: a.choice === "own" ? clean(a.text) : "" };
}
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````
 * default (origin "default") and text that prints nothing (blank after
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b). On the Bulletin
 * step (printed bulletin PR 2b) a box typed, edited or kept counts, and so
````

**with:**

````
 * default (origin "default") and text that prints nothing (blank after
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b). An Affirmation of
 * Faith changed in any way counts; one following the church default does not
 * (the affirmation spec). On the Bulletin
 * step (printed bulletin PR 2b) a box typed, edited or kept counts, and so
````

**In `frontend/src/lib/draft/status.ts`, replace:**

````
    l.communion_origin === "default" &&
    l.sermon_title.trim() === "" &&
````

**with:**

````
    l.communion_origin === "default" &&
    l.affirmation.origin === "default" &&
    l.sermon_title.trim() === "" &&
````

**In `frontend/src/lib/liturgy/summary.ts`, replace:**

````
 * non-blank after trimming; `communion` = `include_communion`;
 * `customCount` = the custom elements.
 */
import { SECTION_KEYS, type DraftV1 } from "@/lib/draft/schema";

````

**with:**

````
 * non-blank after trimming; `communion` = `include_communion`;
 * `customCount` = the custom elements. `affirmationSummary` is the summary's
 * Affirmation of Faith line (the affirmation spec).
 */
import { SECTION_KEYS, type DraftAffirmation, type DraftV1 } from "@/lib/draft/schema";

const AFFIRMATION_NAMES = { apostles: "Apostles' Creed", nicene: "Nicene Creed", own: "Your own text" } as const;

export function affirmationSummary(a: DraftAffirmation): string {
  if (!a.include) return "Affirmation of Faith: Off";
  const blank = a.choice === "own" && a.text.trim() === "";
  return `Affirmation of Faith: ${AFFIRMATION_NAMES[a.choice]}${blank ? " (nothing typed yet)" : ""}`;
}

````

**In `frontend/src/lib/draft/store.ts`, replace:**

````
  setLiturgyDefaults = (next: LiturgyDefaults): void => {
    if (this.defaults?.defaultBenediction === next.defaultBenediction) return;
    this.defaults = next;
````

**with:**

````
  setLiturgyDefaults = (next: LiturgyDefaults): void => {
    const same = this.defaults?.defaultAffirmation;
    if (
      this.defaults?.defaultBenediction === next.defaultBenediction &&
      same?.choice === next.defaultAffirmation?.choice &&
      same?.text === next.defaultAffirmation?.text
    ) {
      return;
    }
    this.defaults = next;
````

**In `frontend/src/lib/draft/context.tsx`, replace:**

````

import type { DraftChurch, DraftV1, StepId } from "./schema";
import { DraftStore, type DraftNotice, type Persistence } from "./store";
````

**with:**

````

import { APOSTLES_DEFAULT, type AffirmationDefault, type DraftChurch, type DraftV1, type StepId } from "./schema";
import { DraftStore, type DraftNotice, type Persistence } from "./store";
````

**In `frontend/src/lib/draft/context.tsx`, replace:**

````
  defaultBenediction: string;
};
````

**with:**

````
  defaultBenediction: string;
  /** The church's default Affirmation of Faith (the Apostles' Creed when the profile has none), as the store applies it. */
  defaultAffirmation: AffirmationDefault;
};
````

**In `frontend/src/lib/draft/context.tsx`, replace:**

````
  const defaultBenediction = church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK;
  const [store] = useState(
    () => new DraftStore({ userId, church, notify, liturgyDefaults: { defaultBenediction } }),
  );
````

**with:**

````
  const defaultBenediction = church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK;
  const affirmationChoice = church.default_affirmation?.choice ?? APOSTLES_DEFAULT.choice;
  const affirmationText = church.default_affirmation?.text ?? APOSTLES_DEFAULT.text;
  const defaultAffirmation = useMemo<AffirmationDefault>(
    () => ({ choice: affirmationChoice, text: affirmationText }),
    [affirmationChoice, affirmationText],
  );
  const [store] = useState(
    () => new DraftStore({ userId, church, notify, liturgyDefaults: { defaultBenediction, defaultAffirmation } }),
  );
````

**In `frontend/src/lib/draft/context.tsx`, replace:**

````

  // The profile refetched with another default (6a's Settings): untouched Benediction cards follow it.
  useEffect(() => {
    store.setLiturgyDefaults({ defaultBenediction });
  }, [store, defaultBenediction]);

````

**with:**

````

  // The profile refetched with another default (6a's Settings): untouched Benediction and Affirmation cards follow it.
  useEffect(() => {
    store.setLiturgyDefaults({ defaultBenediction, defaultAffirmation });
  }, [store, defaultBenediction, defaultAffirmation]);

````

**In `frontend/src/lib/draft/context.tsx`, replace:**

````
      defaultBenediction,
    }),
    [snapshot, store, peek, sync, defaultBenediction],
  );
````

**with:**

````
      defaultBenediction,
      defaultAffirmation,
    }),
    [snapshot, store, peek, sync, defaultBenediction, defaultAffirmation],
  );
````

**Create `frontend/src/components/builder/liturgy/affirmation-card.tsx`:**

````
"use client";

import { ChevronDownIcon } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { AffirmationConfig } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { AffirmationChoice } from "@/lib/draft/schema";
import {
  editAffirmationText,
  restoreAffirmationDefault,
  setAffirmationChoice,
  setAffirmationInclude,
} from "@/lib/liturgy/cards";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

export const AFFIRMATION_OFF = "Not printed or emailed.";
export const OWN_TEXT_HINT = "Printed in bold for everyone to read together.";
export const OWN_TEXT_BLANK = "Nothing prints until you type it.";
const HELPER = { default: "Your church's default.", user: "You changed this.", archive: "Set from the saved service." } as const;

/**
 * A creed as the printed bulletin prints it: one paragraph (the Apostles'
 * Creed), or one line per sense line (the Nicene Creed), each with a hanging
 * indent so a line that wraps on a phone still reads as one line.
 */
export function CreedText({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="grid rounded-md bg-muted/40 p-3 text-sm">
      {lines.length === 1 ? (
        <p>{text}</p>
      ) : (
        lines.map((line, index) => (
          <p key={index} className="pl-4 -indent-4">
            {line}
          </p>
        ))
      )}
    </div>
  );
}

/**
 * The Affirmation of Faith card (affirmation spec, "The Affirmation card"):
 * the switch ("Include Affirmation of Faith"); while it is on, the choice of
 * the Apostles' Creed, the Nicene Creed or your own text, the chosen creed's
 * text (and credit) behind "Show creed text", or a box for your own text,
 * like a prayer card's; a helper line that says whether it follows the
 * church's default, with "Use church default" when it does not (focus then
 * moves to the switch, as on the communion card). It sits after the Sermon
 * Title. Its heading can take focus (`data-card-heading`), like every card's.
 */
export function AffirmationCard({ config, maxLength }: { config: AffirmationConfig; maxLength: number }) {
  const { draft, update, defaultAffirmation } = useDraft();
  const [open, setOpen] = useState(false);
  const switchRef = useRef<HTMLButtonElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const a = draft.liturgy.affirmation;
  const own = a.include && a.choice === "own";
  useAutosize(textRef, a.text, own);
  const chosen = config.choices.find((choice) => choice.key === a.choice);

  return (
    <section id="affirmation" aria-labelledby="affirmation-title" className="grid scroll-mt-24 gap-3 rounded-lg border p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Switch
          ref={switchRef}
          checked={a.include}
          onCheckedChange={(checked) => update((d) => setAffirmationInclude(d, checked))}
          aria-labelledby="affirmation-title"
          className="after:-inset-y-3.5"
        />
        <h3 id="affirmation-title" tabIndex={-1} data-card-heading="" className="min-w-0 flex-1 text-base font-medium outline-none">
          {config.toggle_label}
        </h3>
      </div>
      <p className="flex flex-wrap items-center gap-x-1 text-sm text-muted-foreground">
        {a.include ? HELPER[a.origin] : `${AFFIRMATION_OFF} ${HELPER[a.origin]}`}
        {a.origin === "default" ? null : (
          <Button
            variant="link"
            className="h-11 px-1 md:h-auto"
            onClick={() => {
              update((d) => restoreAffirmationDefault(d, defaultAffirmation));
              switchRef.current?.focus(); // this button goes
            }}
          >
            Use church default
          </Button>
        )}
      </p>
      {a.include ? (
        <>
          <RadioGroup
            aria-label={config.title}
            value={a.choice}
            onValueChange={(value) => update((d) => setAffirmationChoice(d, value as AffirmationChoice))}
            className="gap-0"
          >
            {config.choices.map((choice) => (
              <label key={choice.key} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                <RadioGroupItem value={choice.key} />
                {choice.label}
              </label>
            ))}
          </RadioGroup>
          {own ? (
            <div className="grid gap-1.5">
              <label htmlFor="affirmation-text" className="sr-only">
                Your own text
              </label>
              <Textarea
                id="affirmation-text"
                ref={textRef}
                value={a.text}
                maxLength={maxLength}
                rows={4}
                className="max-h-[60vh] overflow-y-auto"
                aria-describedby="affirmation-hint"
                onChange={(e) => update((d) => editAffirmationText(d, e.target.value))}
              />
              <p id="affirmation-hint" className="text-sm text-muted-foreground">
                {a.text.trim() === "" ? `${OWN_TEXT_HINT} ${OWN_TEXT_BLANK}` : OWN_TEXT_HINT}
              </p>
            </div>
          ) : chosen ? (
            <Collapsible open={open} onOpenChange={setOpen} className="grid gap-2">
              <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
                <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
                Show creed text
              </CollapsibleTrigger>
              <CollapsibleContent className="grid gap-2">
                <CreedText text={chosen.text} />
                {chosen.credit ? <p className="text-xs text-muted-foreground">{chosen.credit}</p> : null}
              </CollapsibleContent>
            </Collapsible>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
````

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

````
import { AddCustomElementDialog } from "./add-custom-element-dialog";
import { AiBar } from "./ai-bar";
````

**with:**

````
import { AddCustomElementDialog } from "./add-custom-element-dialog";
import { AffirmationCard } from "./affirmation-card";
import { AiBar } from "./ai-bar";
````

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

````
 * Word files print it: a card for each section, muted landmark rows for the
 * hymns, readings, sermon and creed, the communion card after the Second
 * Hymn, and each custom element right after the item that owns its place (an
````

**with:**

````
 * Word files print it: a card for each section, muted landmark rows for the
 * hymns, readings and sermon, the Affirmation of Faith card in the
 * Affirmation's place after the Sermon Title (affirmation spec; its muted
 * row when the API sends no card data), the communion card after the Second
 * Hymn, and each custom element right after the item that owns its place (an
````

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

````
                  </li>
                ) : item.kind === "landmark" ? (
````

**with:**

````
                  </li>
                ) : item.key === "affirmation_of_faith" && config.affirmation ? (
                  // The affirmation spec: the card in the Affirmation's place. An API from before it sends no
                  // card data, and the row stays as it was.
                  <li>
                    <AffirmationCard config={config.affirmation} maxLength={config.limits.max_section_text} />
                  </li>
                ) : item.kind === "landmark" ? (
````

**In `frontend/src/components/builder/liturgy/outline-landmark.tsx`, replace:**

````
 * the title, or "[Sermon title]" when blank, and focuses the sermon field;
 * the Affirmation row shows its fixed text.
 */
````

**with:**

````
 * the title, or "[Sermon title]" when blank, and focuses the sermon field;
 * the Affirmation row shows its fixed text (only when the API sends no
 * Affirmation card: the affirmation spec).
 */
````
<!-- /directives:T7_IMPL -->

- [ ] **Step 4: Run them, the suite, typecheck and lint**

Run: the Step 2 command; then the suite; then typecheck and lint.
**Expected:**
```
@@T7PASS@@
```
```
 Test Files  121 passed (121)
      Tests  1137 passed (1137)
```
```
typecheck 0
lint 0
```

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/migrate.ts frontend/src/lib/draft/mapping.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/context.tsx frontend/src/lib/liturgy/defaults.ts frontend/src/lib/liturgy/cards.ts frontend/src/lib/liturgy/summary.ts frontend/src/lib/documents.ts frontend/src/components/builder/liturgy/liturgy-step.tsx frontend/src/components/builder/liturgy/outline-landmark.tsx frontend/src/components/builder/liturgy/affirmation-card.tsx frontend/src/components/builder/liturgy/affirmation-card.test.tsx frontend/src/lib/liturgy/affirmation.test.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/migrate.test.ts frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/mapping.test.ts frontend/src/lib/documents.test.ts frontend/src/components/builder/liturgy/liturgy-step.test.tsx
git commit -q -m "Affirmation of Faith: the draft and the Liturgy step card" -m "Draft version 5 holds the card (switch, choice, own text, origin), following the church default until changed; old drafts become the Apostles' Creed, switched on, and a saved one stays Saved. The body always sends it; the fingerprint leaves out the Apostles' Creed switched on. The card takes the Affirmation row's place after the Sermon Title when the API sends its data (else the row stays); the Nicene Creed's sense lines wrap with a hanging indent." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

### Task 8: Settings → Liturgy's default and the summary (S "Settings → Liturgy: the church default", "Review step and summary"; clarifications 7, 8, 10)

**Files:** Create `frontend/src/components/settings/affirmation-default-card.tsx`, `frontend/src/components/settings/affirmation-default-card.test.tsx`. Modify `frontend/src/components/builder/liturgy/liturgy-summary-block.tsx`, `frontend/src/lib/queries/church.ts`, `frontend/src/components/settings/liturgy-prompts-page.tsx`, `frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx`, `frontend/src/components/builder/builder-shell.test.tsx`, `frontend/src/components/settings/liturgy-prompts-page.test.tsx`.

- [ ] **Step 1: Write the failing tests**

<!-- directives:T8_TESTS -->
**Create `frontend/src/components/settings/affirmation-default-card.test.tsx`:**

````
/**
 * Settings → Liturgy's Affirmation of Faith default (affirmation spec,
 * "Settings → Liturgy: the church default"): owners and admins change and
 * save it with PATCH /church; members read it and cannot change it. Rendered
 * as the route is, inside the Settings layout, with a Toaster.
 */
import { screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, describe, expect, it } from "vitest";

import SettingsLayout from "@/app/(signed-in)/(church)/settings/layout";
import LiturgySettingsRoute from "@/app/(signed-in)/(church)/settings/liturgy/page";
import { DISCARD_TITLE } from "@/components/app/leave-guard";
import { Toaster } from "@/components/ui/sonner";
import type { Church, ChurchAffirmation, ChurchProfile } from "@/lib/api/types";
import { installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, liturgyConfig, liturgyPrompts, me } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { AFFIRMATION_ADMINS_ONLY, AFFIRMATION_SAVED, OWN_TEXT_HELP, OWN_TEXT_REQUIRED } from "./affirmation-default-card";

const OWN = "We trust in God the Holy Spirit.";

afterEach(() => {
  toast.dismiss();
});

/** A fake `/church` whose PATCH stores the default, as the server does. */
function churchServer(role: Church["role"]) {
  let profile: ChurchProfile = churchProfile({ role });
  return {
    get: () => profile,
    patch: (req: RecordedRequest) => {
      const sent = (req.body as { default_affirmation: ChurchAffirmation }).default_affirmation;
      profile = { ...profile, default_affirmation: sent };
      return profile;
    },
  };
}

function renderPage(role: Church["role"] = "admin", routes: Record<string, FakeHandler> = {}) {
  const active = church({ role });
  const server = churchServer(role);
  const api = installFakeApi({
    "GET /church": server.get,
    "PATCH /church": server.patch,
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/liturgy-prompts": liturgyPrompts({}, { can_edit: role !== "member" }),
    ...routes,
  });
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

const patches = (api: { requests: RecordedRequest[] }) => api.requests.filter((r) => r.method === "PATCH" && r.path === "/church");

async function form() {
  return screen.findByRole("form", { name: "Affirmation of Faith default" });
}

describe("Settings → Liturgy: the Affirmation of Faith default (affirmation spec)", () => {
  it("lets an admin choose the church's own text and save it", async () => {
    const { user, api } = renderPage("admin");
    const card = await form();
    expect(within(card).getByRole("radio", { name: "Apostles' Creed" })).toBeChecked();
    const save = within(card).getByRole("button", { name: "Save default" });
    expect(save).toBeDisabled();
    await user.click(within(card).getByRole("radio", { name: "Your own text" }));
    const box = within(card).getByRole("textbox", { name: "Your church's own text" });
    expect(box).toHaveAccessibleDescription(OWN_TEXT_REQUIRED);
    expect(save).toBeDisabled(); // own text with a blank box cannot be saved
    await user.type(box, `${OWN}  `);
    expect(box).toHaveAccessibleDescription(OWN_TEXT_HELP);
    await user.click(save);
    expect(await screen.findByText(AFFIRMATION_SAVED)).toBeInTheDocument();
    expect(patches(api).map((r) => r.body)).toEqual([{ default_affirmation: { choice: "own", text: OWN } }]);
    await waitFor(() => expect(save).toBeDisabled());
    expect(card.textContent).not.toContain("\u2014");
  });

  it("shows a creed's text and credit, and asks before leaving with an unsaved change", async () => {
    const { user, api } = renderPage("owner");
    const card = await form();
    await user.click(within(card).getByRole("radio", { name: "Nicene Creed" }));
    await user.click(within(card).getByRole("button", { name: "Show creed text" }));
    expect(within(card).getByText(/Consultation \(ELLC\), and used by permission\./)).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Church" }));
    expect(await screen.findByRole("alertdialog", { name: DISCARD_TITLE })).toBeInTheDocument();
    expect(patches(api)).toEqual([]);
  });

  it("leaves the card out when the API sends no card data (the pages ahead of the server side)", async () => {
    const older = { ...liturgyConfig(), affirmation: undefined } as unknown as ReturnType<typeof liturgyConfig>;
    renderPage("admin", { "GET /liturgy/config": older });
    expect(await screen.findByRole("form", { name: "Liturgy prompts" })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Affirmation of Faith" })).toBeNull());
    expect(screen.queryByRole("form", { name: "Affirmation of Faith default" })).toBeNull();
  });

  it("shows a member the default read-only, with the note, and no way to change it", async () => {
    const { user, api } = renderPage("member", {
      "GET /church": churchProfile({ role: "member", default_affirmation: { choice: "own", text: OWN } }),
    });
    const card = await form();
    expect(within(card).getByText(AFFIRMATION_ADMINS_ONLY)).toBeInTheDocument();
    expect(within(card).getByRole("radio", { name: "Your own text" })).toBeChecked();
    for (const radio of within(card).getAllByRole("radio")) expect(radio).toHaveAttribute("aria-disabled", "true");
    const box = within(card).getByRole("textbox", { name: "Your church's own text" });
    expect(box).toHaveValue(OWN);
    expect(box).toHaveAttribute("readonly");
    expect(within(card).queryByRole("button", { name: "Save default" })).toBeNull();
    await user.click(within(card).getByRole("radio", { name: "Nicene Creed" }));
    expect(within(card).getByRole("radio", { name: "Your own text" })).toBeChecked();
    expect(patches(api)).toEqual([]);
  });
});
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````
    const liturgy = within(aside).getByRole("link", { name: "Liturgy" }).closest("h3");
    expect(liturgy?.nextElementSibling).toHaveTextContent(/^1 of 7 liturgy sections readyCommunion: YesNo custom elements$/);
    expect(within(aside).getByRole("link", { name: "Date" })).toHaveAttribute("href", "/builder/readings");
````

**with:**

````
    const liturgy = within(aside).getByRole("link", { name: "Liturgy" }).closest("h3");
    expect(liturgy?.nextElementSibling).toHaveTextContent(/^1 of 7 liturgy sections readyCommunion: YesAffirmation of Faith: Apostles' CreedNo custom elements$/);
    expect(within(aside).getByRole("link", { name: "Date" })).toHaveAttribute("href", "/builder/readings");
````

**In `frontend/src/components/builder/builder-shell.test.tsx`, replace:**

````
      "Communion: No",
      "1 custom element",
````

**with:**

````
      "Communion: No",
      "Affirmation of Faith: Apostles' Creed",
      "1 custom element",
````

**In `frontend/src/components/settings/liturgy-prompts-page.test.tsx`, replace:**

````
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, DEFAULT_PROMPTS, liturgyPrompts, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
````

**with:**

````
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, DEFAULT_PROMPTS, liturgyConfig, liturgyPrompts, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";
````

**In `frontend/src/components/settings/liturgy-prompts-page.test.tsx`, replace:**

````
  const active = church({ role });
  const api = installFakeApi({ "GET /church/liturgy-prompts": liturgyPrompts(), ...routes });
  const view = renderWithProviders(
````

**with:**

````
  const active = church({ role });
  // The Affirmation of Faith card above the prompts (affirmation spec) reads the profile and the config.
  const api = installFakeApi({
    "GET /church/liturgy-prompts": liturgyPrompts(),
    "GET /church": churchProfile({ role }),
    "GET /liturgy/config": liturgyConfig(),
    ...routes,
  });
  const view = renderWithProviders(
````

**In `frontend/src/components/settings/liturgy-prompts-page.test.tsx`, replace:**

````
    expect(screen.getByText(PROMPTS_INTRO)).toBeInTheDocument();
    const titles = screen.getAllByRole("button", { name: /./ }).map((b) => b.textContent);
    expect(titles).toEqual([
````

**with:**

````
    expect(screen.getByText(PROMPTS_INTRO)).toBeInTheDocument();
    const form = screen.getByRole("form", { name: "Liturgy prompts" });
    const titles = within(form).getAllByRole("button", { name: /./ }).map((b) => b.textContent);
    expect(titles).toEqual([
````
<!-- /directives:T8_TESTS -->

- [ ] **Step 2: Run them and see them fail**

Run: `(cd frontend && npx vitest run src/components/settings/affirmation-default-card.test.tsx src/components/builder/builder-shell.test.tsx src/components/settings/liturgy-prompts-page.test.tsx 2>&1 | grep -E "Test Files|Tests ")`
**Expected:**
```
@@T8FAIL@@
```

- [ ] **Step 3: Write the Settings card and the summary line**

<!-- directives:T8_IMPL -->
**In `frontend/src/components/builder/liturgy/liturgy-summary-block.tsx`, replace:**

````
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { liturgyCounts } from "@/lib/liturgy/summary";

````

**with:**

````
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { affirmationSummary, liturgyCounts } from "@/lib/liturgy/summary";

````

**In `frontend/src/components/builder/liturgy/liturgy-summary-block.tsx`, replace:**

````
 * off"), with " · Writing n sections…" while the generation provider has runs;
 * "Communion: Yes/No"; and the custom-element count. It reads the draft and
 * the runs only, so the shell never fetches anything for it.
````

**with:**

````
 * off"), with " · Writing n sections…" while the generation provider has runs;
 * "Communion: Yes/No"; the Affirmation of Faith (`affirmationSummary`); and
 * the custom-element count. It reads the draft and
 * the runs only, so the shell never fetches anything for it.
````

**In `frontend/src/components/builder/liturgy/liturgy-summary-block.tsx`, replace:**

````
      <li>Communion: {counts.communion ? "Yes" : "No"}</li>
      <li>{custom}</li>
````

**with:**

````
      <li>Communion: {counts.communion ? "Yes" : "No"}</li>
      <li>{affirmationSummary(draft.liturgy.affirmation)}</li>
      <li>{custom}</li>
````

**In `frontend/src/lib/queries/church.ts`, replace:**

````
 * and, when the default hymnal was sent, `GET /hymnals` (the Hymns step's
 * hymnal), and toasts "Profile saved.". A failure toasts the server's message,
 * except a 401 or a lost church, which the app already reports; a role 403
````

**with:**

````
 * and, when the default hymnal was sent, `GET /hymnals` (the Hymns step's
 * hymnal), and toasts "Profile saved." (or `savedMessage`: Settings → Liturgy's
 * Affirmation of Faith default, the affirmation spec). A failure toasts the server's message,
 * except a 401 or a lost church, which the app already reports; a role 403
````

**In `frontend/src/lib/queries/church.ts`, replace:**

````
 */
export function useUpdateChurch() {
  const api = useApi();
````

**with:**

````
 */
export function useUpdateChurch({ savedMessage = PROFILE_SAVED }: { savedMessage?: string } = {}) {
  const api = useApi();
````

**In `frontend/src/lib/queries/church.ts`, replace:**

````
      if (patch.default_hymnal !== undefined) void queryClient.invalidateQueries({ queryKey: keys.hymnals(church.id) });
      toast.success(PROFILE_SAVED);
    },
````

**with:**

````
      if (patch.default_hymnal !== undefined) void queryClient.invalidateQueries({ queryKey: keys.hymnals(church.id) });
      toast.success(savedMessage);
    },
````

**Create `frontend/src/components/settings/affirmation-default-card.tsx`:**

````
"use client";

import { ChevronDownIcon } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { ErrorState } from "@/components/app/error-state";
import { CreedText } from "@/components/builder/liturgy/affirmation-card";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type { AffirmationConfig, ChurchAffirmation, ChurchProfile } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { APOSTLES_DEFAULT, type AffirmationChoice } from "@/lib/draft/schema";
import { useChurchProfile, useUpdateChurch } from "@/lib/queries/church";
import { useLiturgyConfig } from "@/lib/queries/liturgy";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

export const AFFIRMATION_INTRO = "What the Liturgy step starts with for a new service. Each service can still change it or switch it off.";
export const AFFIRMATION_ADMINS_ONLY = "Only admins can change the default. You can read it below.";
export const OWN_TEXT_HELP = "Paste your church's own text, for example A Brief Statement of Faith.";
export const OWN_TEXT_REQUIRED = "Type your church's own text, or choose a creed.";
export const AFFIRMATION_SAVED = "Affirmation of Faith default saved.";

/** The form as the server stores it: the text trimmed with "\n" line ends, and only for "own". */
function cleaned(form: ChurchAffirmation): ChurchAffirmation {
  return { choice: form.choice, text: form.choice === "own" ? form.text.replace(/\r\n?/g, "\n").trim() : "" };
}

function same(a: ChurchAffirmation, b: ChurchAffirmation): boolean {
  const x = cleaned(a);
  const y = cleaned(b);
  return x.choice === y.choice && x.text === y.text;
}

function fromProfile(profile: ChurchProfile): ChurchAffirmation {
  return profile.default_affirmation ?? APOSTLES_DEFAULT;
}

/**
 * Settings → Liturgy's Affirmation of Faith card (affirmation spec, "Settings
 * → Liturgy: the church default"): the church's default choice and, for
 * "Your own text", its text. Owners and admins change it and press **Save
 * default** (`PATCH /church`); members read it. 6a's settings rules: newer
 * server data replaces the form unless it was edited, and `onDirtyChange`
 * tells the page, whose one leave guard covers both of its forms.
 */
export function AffirmationDefaultCard({ onDirtyChange }: { onDirtyChange: (dirty: boolean) => void }) {
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  const config = useLiturgyConfig();
  // An API from before the affirmation spec sends no card data (and would refuse the default): no card.
  if (config.data && !config.data.affirmation) return null;
  let body;
  if (profile.data && config.data) {
    body = <AffirmationForm profile={profile.data} config={config.data.affirmation} onDirtyChange={onDirtyChange} />;
  } else if (profile.isError || config.isError) {
    const failed = profile.isError ? profile : config;
    body = <ErrorState error={failed.error} onRetry={() => void failed.refetch()} retrying={failed.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-3">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }
  return (
    <section aria-labelledby="affirmation-default-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="affirmation-default-title" className="text-lg font-semibold">
          Affirmation of Faith
        </h2>
        <p className="text-sm text-muted-foreground">{AFFIRMATION_INTRO}</p>
      </div>
      {body}
    </section>
  );
}

type FormState = { source: ChurchProfile; baseline: ChurchAffirmation; form: ChurchAffirmation };

function AffirmationForm({
  profile,
  config,
  onDirtyChange,
}: {
  profile: ChurchProfile;
  config: AffirmationConfig;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const admin = isAdmin(profile.role);
  const save = useUpdateChurch({ savedMessage: AFFIRMATION_SAVED });
  const textRef = useRef<HTMLTextAreaElement>(null);
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<FormState>(() => {
    const form = fromProfile(profile);
    return { source: profile, baseline: form, form };
  });
  const { form, baseline } = state;
  // A member (or an admin demoted meanwhile) reads what is stored, never an unsaved edit.
  const shown = admin ? form : fromProfile(profile);
  const dirty = admin && !same(baseline, form);
  const ownBlank = shown.choice === "own" && shown.text.trim() === "";
  useAutosize(textRef, shown.text, shown.choice === "own");

  // Newer server data (a refetch, or this form's own save): the form follows it unless it was edited (6a).
  if (profile !== state.source) {
    const next = fromProfile(profile);
    setState({ source: profile, baseline: next, form: same(baseline, form) ? next : form });
  }

  useEffect(() => onDirtyChange(dirty), [dirty, onDirtyChange]);

  const chosen = config.choices.find((choice) => choice.key === shown.choice);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending || !dirty || ownBlank) return;
    save.mutate({ default_affirmation: cleaned(form) });
  }

  return (
    <form onSubmit={onSubmit} className="grid gap-3 rounded-lg border p-4" aria-label="Affirmation of Faith default">
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{AFFIRMATION_ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      <RadioGroup
        aria-label="Default Affirmation of Faith"
        value={shown.choice}
        disabled={!admin}
        onValueChange={(value) => setState((s) => ({ ...s, form: { ...s.form, choice: value as AffirmationChoice } }))}
        className="gap-0"
      >
        {config.choices.map((choice) => (
          <label key={choice.key} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
            <RadioGroupItem value={choice.key} />
            {choice.label}
          </label>
        ))}
      </RadioGroup>
      {shown.choice === "own" ? (
        <div className="grid gap-1.5">
          <label htmlFor="affirmation-default-text" className="sr-only">
            Your church&apos;s own text
          </label>
          <Textarea
            id="affirmation-default-text"
            ref={textRef}
            value={shown.text}
            readOnly={!admin}
            rows={6}
            className="max-h-[60vh] overflow-y-auto"
            aria-describedby="affirmation-default-help"
            aria-invalid={admin && ownBlank && dirty ? true : undefined}
            onChange={(e) => setState((s) => ({ ...s, form: { ...s.form, text: e.target.value } }))}
          />
          <p id="affirmation-default-help" className="text-sm text-muted-foreground">
            {admin && ownBlank ? OWN_TEXT_REQUIRED : OWN_TEXT_HELP}
          </p>
        </div>
      ) : chosen ? (
        <Collapsible open={open} onOpenChange={setOpen} className="grid gap-2">
          <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
            <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
            Show creed text
          </CollapsibleTrigger>
          <CollapsibleContent className="grid gap-2">
            <CreedText text={chosen.text} />
            {chosen.credit ? <p className="text-xs text-muted-foreground">{chosen.credit}</p> : null}
          </CollapsibleContent>
        </Collapsible>
      ) : null}
      {admin ? (
        <div>
          <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={save.isPending} disabled={!dirty || ownBlank}>
            Save default
          </PendingButton>
        </div>
      ) : null}
    </form>
  );
}
````

**In `frontend/src/components/settings/liturgy-prompts-page.tsx`, replace:**

````
 * forms: newer server data rebases the form, and leaving with unsaved edits
 * asks first (`LeaveGuard`).
 */
export function LiturgyPromptsPage() {
  const church = useChurch();
````

**with:**

````
 * forms: newer server data rebases the form, and leaving with unsaved edits
 * asks first (`LeaveGuard`; with `onDirtyChange`, the page's own guard, which
 * also covers the Affirmation of Faith default above it: affirmation spec).
 */
export function LiturgyPromptsPage({ onDirtyChange }: { onDirtyChange?: (dirty: boolean) => void } = {}) {
  const church = useChurch();
````

**In `frontend/src/components/settings/liturgy-prompts-page.tsx`, replace:**

````
  if (prompts.data) {
    body = <PromptsForm out={prompts.data} admin={admin} headingRef={headingRef} />;
  } else if (prompts.isError) {
````

**with:**

````
  if (prompts.data) {
    body = <PromptsForm out={prompts.data} admin={admin} headingRef={headingRef} onDirtyChange={onDirtyChange} />;
  } else if (prompts.isError) {
````

**In `frontend/src/components/settings/liturgy-prompts-page.tsx`, replace:**

````
  headingRef,
}: {
````

**with:**

````
  headingRef,
  onDirtyChange,
}: {
````

**In `frontend/src/components/settings/liturgy-prompts-page.tsx`, replace:**

````
  headingRef: RefObject<HTMLHeadingElement | null>;
}) {
````

**with:**

````
  headingRef: RefObject<HTMLHeadingElement | null>;
  onDirtyChange?: (dirty: boolean) => void;
}) {
````

**In `frontend/src/components/settings/liturgy-prompts-page.tsx`, replace:**

````
    setState({ source: out, baseline: next, form: rebasePrompts(baseline, form, next) });
  }

  // The first card a failed save named: opened by onError, focused once it is on the page.
````

**with:**

````
    setState({ source: out, baseline: next, form: rebasePrompts(baseline, form, next) });
  }

  useEffect(() => onDirtyChange?.(dirty), [dirty, onDirtyChange]);

  // The first card a failed save named: opened by onError, focused once it is on the page.
````

**In `frontend/src/components/settings/liturgy-prompts-page.tsx`, replace:**

````
      />
      <LeaveGuard when={dirty} />
    </form>
````

**with:**

````
      />
      {onDirtyChange ? null : <LeaveGuard when={dirty} />}
    </form>
````

**In `frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx`, replace:**

````

import { LiturgyPromptsPage } from "@/components/settings/liturgy-prompts-page";

/** Settings → Liturgy: the instructions the AI follows when it writes the liturgy (slice 6a-3a; F §4.1). */
export default function LiturgySettingsRoute() {
  return <LiturgyPromptsPage />;
}
````

**with:**

````

import { useState } from "react";

import { LeaveGuard } from "@/components/app/leave-guard";
import { AffirmationDefaultCard } from "@/components/settings/affirmation-default-card";
import { LiturgyPromptsPage } from "@/components/settings/liturgy-prompts-page";

/**
 * Settings → Liturgy: the church's default Affirmation of Faith (affirmation
 * spec), then the instructions the AI follows when it writes the liturgy
 * (slice 6a-3a; F §4.1). Each saves on its own; one leave guard covers both.
 */
export default function LiturgySettingsRoute() {
  const [affirmationDirty, setAffirmationDirty] = useState(false);
  const [promptsDirty, setPromptsDirty] = useState(false);
  return (
    <div className="grid gap-8">
      <AffirmationDefaultCard onDirtyChange={setAffirmationDirty} />
      <LiturgyPromptsPage onDirtyChange={setPromptsDirty} />
      <LeaveGuard when={affirmationDirty || promptsDirty} />
    </div>
  );
}
````
<!-- /directives:T8_IMPL -->

- [ ] **Step 4: Run them, the suite, typecheck and lint**

Run: the Step 2 command; then the suite; then typecheck and lint.
**Expected:**
```
@@T8PASS@@
```
```
 Test Files  122 passed (122)
      Tests  1141 passed (1141)
```
```
typecheck 0
lint 0
```

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/components/settings/affirmation-default-card.tsx frontend/src/components/settings/affirmation-default-card.test.tsx frontend/src/components/builder/liturgy/liturgy-summary-block.tsx frontend/src/lib/queries/church.ts frontend/src/components/settings/liturgy-prompts-page.tsx "frontend/src/app/(signed-in)/(church)/settings/liturgy/page.tsx" frontend/src/components/builder/builder-shell.test.tsx frontend/src/components/settings/liturgy-prompts-page.test.tsx
git commit -q -m "Affirmation of Faith: the church default on Settings, Liturgy" -m "Owners and admins choose the default (a creed, or the church's own text) and save it with PATCH /church; members read it; an API without the card's data leaves the card out. One leave guard covers the page's two forms. The builder's summary names the Affirmation." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

### Task 9: Planted violations, PR B (agent)

**Files:** none (each change is undone with `git checkout -- <file>`).

As T3. Frontend rows: `(cd frontend && npx vitest run <files> 2>&1 | grep -E "Tests ")`.

| # | Rule | Change | Run | Expected |
|---|---|---|---|---|
| F1 | no em dash in user-facing copy | `frontend/src/components/builder/liturgy/affirmation-card.tsx`: `"Not printed or emailed."` → `"Not printed \u2014 or emailed."` | `src/components/builder/liturgy/affirmation-card.test.tsx` | `@@F1@@` |
| F2 | 44 px rows at 375 px | same file: `className="flex min-h-11 cursor-pointer items-center gap-3 text-sm"` → `className="flex cursor-pointer items-center gap-3 text-sm"` | `src/components/builder/liturgy/affirmation-card.test.tsx` | `@@F2@@` |
| F3 | an old saved draft stays Saved (the payload leaves out today's value) | `frontend/src/lib/draft/mapping.ts`: `    ...(today ? {} : { affirmation }),` → `    affirmation,` | `src/lib/draft/migrate.test.ts src/lib/liturgy/affirmation.test.ts` | `@@F3@@` |
| F4 | an old saved service's draft prints as saved | `frontend/src/lib/draft/migrate.ts`: `isRecord(draft.editing) ? "archive" : "default"` → `"default"` | `src/lib/draft/migrate.test.ts` | `@@F4@@` |
| F5 | members read the default, never change it | `frontend/src/components/settings/affirmation-default-card.tsx`: `        disabled={!admin}` → `        disabled={false}` | `src/components/settings/affirmation-default-card.test.tsx` | `@@F5@@` |
| F6 | the body always carries it (a PUT never keeps an older choice by accident) | `frontend/src/lib/documents.ts`: delete the line starting `    affirmation: { ...(payload.affirmation ?? TODAYS_AFFIRMATION)` | `src/lib/documents.test.ts src/lib/liturgy/affirmation.test.ts` | `@@F6@@` |
| F7 | "Save as new service" from a saved Nicene service posts the Nicene Creed (review fix 5) | `frontend/src/lib/draft/bulletin.ts`, the first `    return withBulletin(d, {` (in `followSaveMode`) → `    return withBulletin({ ...d, liturgy: { ...d.liturgy, affirmation: { include: true, choice: "apostles", text: "", origin: "default" } } }, {` | `src/lib/liturgy/affirmation.test.ts src/lib/draft/bulletin.test.ts` | `@@F7@@` |
| F8 | ahead of PR A, the Liturgy step keeps today's row | `frontend/src/components/builder/liturgy/liturgy-step.tsx`: `item.key === "affirmation_of_faith" && config.affirmation ? (` → `item.key === "affirmation_of_faith" ? (` | `src/components/builder/liturgy/affirmation-card.test.tsx` | `@@F8@@` |
| F9 | ahead of PR A, Settings leaves the default card out | `frontend/src/components/settings/affirmation-default-card.tsx`: delete the line `  if (config.data && !config.data.affirmation) return null;` | `src/components/settings/affirmation-default-card.test.tsx` | `@@F9@@` |
| F10 | the Nicene sense lines wrap with a hanging indent on the phone | `frontend/src/components/builder/liturgy/affirmation-card.tsx`: `<p key={index} className="pl-4 -indent-4">` → `<p key={index}>` | `src/components/builder/liturgy/affirmation-card.test.tsx` | `@@F10@@` |

### Task 10: Verification, PR B (agent)

**Files:** none.

- [ ] **Step 1: The suites, typecheck, lint and the build**

Run: `.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1`; the frontend suite; typecheck and lint; `(cd frontend && npm run build 2>&1 | grep -cE "Compiled successfully")`; `(cd frontend && npm run gen:api >/dev/null 2>&1 && git diff --exit-code src/lib/api/schema.d.ts >/dev/null; echo "drift $?")`
**Expected:** `2288 passed, 50 skipped in <t>s` (no backend change: CI's jobs give PR A's `2319 passed, 50 skipped` and `50 passed, 2319 deselected`); `1141 passed` in 122 files; `typecheck 0`, `lint 0`; `1`; `drift 0`.

- [ ] **Step 2: No em dash added, nothing frozen touched, the branch's paths**

Run: T4 Step 4's three commands (with PR A merged, `origin/main...HEAD` is PR B alone).
**Expected:** `0`; `0`; `@@PATHSB@@` (the five new frontend files; the modified files of T7-T8 and `docs/ops-runbook.md`, PR A's record). No backend file, no migration, no generated file. Anything else: find why before the PR.

### Task 11: PR B: the draft PR, the merge, the after-deploy check, the phone check, the record (OWNER + agent)

**Files:** Modify (Step 12, the records PR): `docs/ops-runbook.md`: insert `### Affirmation PR B record` right before `## Backups` (after `### Affirmation PR A record`).

- [ ] **Step 1 (agent → OWNER): Check PR A is live, then ask to open PR B as a draft**

(not replayed) `gh pr view <NA> -R <repo> --json state --jq .state` → `MERGED`; `curl -s <api>/openapi.json | python3 -c 'import json, sys; print("ServiceAffirmation" in json.load(sys.stdin)["components"]["schemas"])'` → `True` (PR B's pages send `affirmation`, which only PR A's API accepts: clarification 10); `gh pr list -R <repo> --head claude/slice-2-plan-4q33le --state open --json number,url` → `[]`. Send the owner exactly this, and wait for a clear yes:

> The second half of the Affirmation of Faith change, the pages, is verified on this machine: frontend 1141 tests in 122 files (1122 in 119 before), typecheck, lint and the production build clean; the server side is live since PR #<NA>. In the Liturgy step the Affirmation becomes a card: a switch to include it, and a choice of the Apostles' Creed, the Nicene Creed or your own text. Switched off, nothing of it prints or goes in the email. Settings, Liturgy holds your church's default; admins change it, members read it. Old services print exactly as before. No database change this time. May I open the pull request as a **draft** titled "Affirmation PR B: the pages", so the checks run? Merging stays with you.

- [ ] **Step 2 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/affirmation-pr-b-body.md" <<'BODY'
Affirmation PR B: the pages of the Affirmation of Faith (owner's decisions 1, 2 and 6 of 2026-10-24; answers A to D). Spec: docs/superpowers/specs/2026-10-24-affirmation-design.md. Plan: docs/superpowers/plans/2026-10-24-affirmation.md (Part 2). The server side is PR #<NA>, live since <date>. No migration, no backend change, no new package, no new variable.

- The Liturgy step's Affirmation is a card in the Affirmation row's place: "Include Affirmation of Faith", then the Apostles' Creed, the Nicene Creed or your own text (a box like a prayer card's). "Show creed text" shows the creed as the printed bulletin prints it (the Nicene Creed's sense lines with a hanging indent, and ELLC's acknowledgement). Off, or own text left blank: nothing prints in the Word files, the printed bulletin (PDF and Word) or the email's attachments.
- Settings, Liturgy: the church's default (PATCH /church, admins only; members read it). New drafts follow it until changed. The builder's summary names the Affirmation.
- Data: draft version 5 (old drafts become the Apostles' Creed, switched on; a saved one stays Saved). Every body sends affirmation; "Save as new service" keeps the saved service's choice.
- Guarded if it ever ran ahead of PR A: with no affirmation in GET /liturgy/config the Liturgy step keeps today's row and Settings leaves the default card out.
- Tests: planted violations F1-F10 in the plan's Task 9 (no em dash, 44 px rows, old drafts stay Saved and print as saved, members cannot change the default, the body always carries it, Save as new service keeps the Nicene Creed, the two guards, the hanging indent).
- Rides along: the Affirmation PR A record in docs/ops-runbook.md.
- Next: formatting (decisions 3 to 5).

Before the merge: nothing (no migration). After the merge: the after-deploy check, a phone check of the card, an "Affirmation PR B record" in docs/ops-runbook.md.

Tests: frontend 1122 → 1141 in 119 → 122 files; backend unchanged (backend/tests 2288 passed, 50 skipped; CI backend job 2319 passed, 50 skipped; CI Postgres job 50 passed, 2319 deselected)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R <repo> --draft --base main --head claude/slice-2-plan-4q33le --title "Affirmation PR B: the pages" --body-file "<scratch>/affirmation-pr-b-body.md"
gh pr checks <NB> -R <repo> --watch --interval 30
```

Run the last line with `run_in_background: true` (or the session's GitHub tools, to the same effect). **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's `backend` job `2319 passed, 50 skipped`, its `backend-postgres` job `50 passed, 2319 deselected` (both as on `main` after PR A), its `frontend` job `1141 passed` in 122 files. Then send: "PR #<NB> is green: frontend 1141 in 122 files, the backend as on main (2319 in CI, Postgres 50), and the Vercel preview builds. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <NB> -R <repo>`.

- [ ] **Step 3 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <NB> -R <repo> --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "May I merge PR #<NB> with a merge commit? There is no database or server change; Vercel publishes the new pages. I will tell you when they are live, then ask for a short phone check, one step at a time." On a clear yes (not replayed): T6 Step 3's three commands with `<NB>`. **Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (in the background). Record both.

- [ ] **Step 4 (agent): The after-deploy check**

About three minutes after the merge (not replayed):

```bash
curl -s <api>/health/ready; echo
ID=$(gh api "repos/<repo>/deployments?sha=<merge sha>&environment=Production" --jq '.[0].id'); gh api "repos/<repo>/deployments/$ID/statuses" --jq '.[0].state'
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' <app>/settings/liturgy
```

**Expected:** `{"ok":true,"db":"ok"}`; `success` (Vercel published the merge commit to Production); `307 <app>/login?next=%2Fsettings%2Fliturgy` (the page is there, signed in only). No deployment yet, or `pending`: ask again a minute later. Nothing for the owner to run.

(not replayed: Steps 5-11 need the owner's phone and production.) One short action per message; send the next only after the answer.

- [ ] **Step 5 (OWNER, then agent): Phone 1: the card**

> On your phone, open the builder's **Liturgy** step (pull down to refresh it first). After the Sermon Title, is there a card "Include Affirmation of Faith", switched on, with the Apostles' Creed chosen?

- [ ] **Step 6 (OWNER, then agent): Phone 2: the Nicene Creed**

> Tap **Nicene Creed**, then **Show creed text**. Does the creed show line by line, a line too long for the screen continuing indented under itself, with a line about the English Language Liturgical Consultation under it?

- [ ] **Step 7 (OWNER, then agent): Phone 3: the printed bulletin**

> On the Review step, download the printed bulletin (PDF). After the sermon, is the Nicene Creed printed in bold, line by line, with that line under it?

- [ ] **Step 8 (OWNER, then agent): Phone 4: switched off**

> Back on the Liturgy step, switch the Affirmation off, then download the bulletin Word file. Is the Affirmation of Faith gone from it?

- [ ] **Step 9 (OWNER, then agent): Phone 5: the church default**

> Open **Settings**, then **Liturgy**. Choose **Your own text**, paste a short text, and tap **Save default**. Does it say "Affirmation of Faith default saved."?

- [ ] **Step 10 (OWNER, then agent): Phone 6: an old service**

> Open **Services** and open a service saved before today. On its Liturgy step, does the card show the Apostles' Creed, "Set from the saved service."?

- [ ] **Step 11 (OWNER, then agent): Phone 7: put the default back**

> In Settings, Liturgy, choose the creed your church usually says and tap **Save default**. (The test service from Phone 2 to 4 can be left unsaved or deleted.)

Write each step's result, with the date, into `<scratch>/affirmation-b-results.md` (not committed). A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

**What PR B's phone check cannot show.** The email's attachments (the same files as the downloads; `test_affirmation.py` builds them), a member's refused change (`test_api_affirmation.py`, P5; F5), old drafts in other browsers (`migrate.test.ts`, F3, F4), "Save as new service" (`affirmation.test.ts`, F7), the guards ahead of PR A (F8, F9) and the exact creed texts (`test_affirmation.py`).

- [ ] **Step 12 (agent): Write the record**

(not replayed) As T6 Step 8: fetch, switch, `git merge --ff-only origin/main` (**Expected:** `Fast-forward`); the last `###` heading above `## Backups` is now `### Affirmation PR A record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Affirmation PR B record

Affirmation PR B, the pages of the Affirmation of Faith (the Liturgy step's
card: include or not, the Apostles' Creed, the Nicene Creed or the church's
own text; the church default on Settings, Liturgy), merged as PR #<NB>
(owner's decisions and answers of 2026-10-24), after PR A (see "Affirmation
PR A record"). No migration.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<NB> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. Vercel Production for the merge commit: success; `/settings/liturgy` 307 to sign-in | <date> |
| Phone 1. The card | <On, Apostles' Creed chosen, after the Sermon Title. / …> | <date> |
| Phone 2. The Nicene Creed | <Text line by line, wrapped lines indented, the ELLC line shown. / …> | <date> |
| Phone 3. The printed bulletin | <Nicene Creed in bold, line by line, with the ELLC line. / …> | <date> |
| Phone 4. Switched off | <No Affirmation in the Word file. / …> | <date> |
| Phone 5. The default | <Saved, with the toast. / …> | <date> |
| Phone 6. An old service | <Apostles' Creed, "Set from the saved service." / …> | <date> |
| Phone 7. Default back | <Saved. / …> | <date> |
| Not on the phone | The email's attachments, a member's refused change, old drafts, Save as new service, the guards ahead of PR A and the exact creed texts: tests only (T11 "What PR B's phone check cannot show") | <date> |
| Follow-ups | <None. / One line per follow-up.> | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then (not replayed) T6 Step 8's three checks with `### Affirmation PR B record`, the docs tests, and:

```bash
git add docs/ops-runbook.md
git commit -q -m "Runbook: Affirmation PR B record" -m "Records PR #<NB>: the merge and deploy and the owner's phone check of the card. No church id, email address, token or database URL is recorded." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** `0`; `0`; `0`; `89 passed in <t>s`; one commit.

- [ ] **Step 13 (agent, on the owner's yes): Push, open and merge the records PR**

(not replayed) Push; ask the owner for a yes before opening a draft PR "Runbook: Affirmation PR B record" (body: the record's one-line summary, then the attribution lines), then for a yes before marking it ready and merging, as Steps 1-3.

## Build notes

**How this plan was written (2026-10-24).** The code was built and run in a throwaway worktree (in the session scratchpad, outside the repo directory; the repo's `.venv` linked in, a hard-linked copy of `frontend/node_modules`, because Turbopack refuses a symlinked one). The directives were generated from that worktree by a script (a new file as **Create**; every change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point; files split across tasks by hunk), and the script checked that applying them in order gives the worktree's files exactly. The plan was then **replayed**.

**Plan review fixes (2026-10-24).** An independent review of the plan at `f654dcf` found six things; the owner answered the open questions the same day ("all recommended", answers A to D, recorded in D and in "Owner decisions"). Fixed here:
1. **Two PRs** (answer A). The plan is now Part 1 (PR A: T1-T6) and Part 2 (PR B: T7-T11), each with its own planted violations, verification, pre-merge note, PR body, CI counts, merge, after-deploy check, phone check and record. Making PR A safe with today's frontend changed three things: the outline stays as it is (today's Liturgy step renders nothing for an unknown kind, so `kind: "affirmation"` would have dropped the row; clarification 9, P7); `schema.d.ts` and the frontend test fixtures move into PR A (CI's drift check, and the fixtures are typed by it); T4 Step 2 runs today's frontend suite, unchanged, against PR A's types (1122 pass, typecheck and lint clean). A probe on PR A's API with bodies shaped like today's (no `affirmation`) got 200 from `POST /documents` and `/documents/printed`, 201 and 200 from `POST` and `PUT /services` (the answer's `affirmation` the Apostles' Creed), 200 from `PATCH /church` and `GET /liturgy/config` (the item still `landmark`, `fixed_text` "Apostles' Creed"). PR B's guards: clarification 10 (two built and tested, F8 and F9; the third, sending `affirmation` only when the config has it, not built, with the reason).
2. **README 0010 Step 3** now has 0009's "**Read only. Do not run this.**" paragraph and "Expected, exactly and in full"; in chat the agent describes the SQL in words and points to the step (Global Constraints). `test_the_readme_shows_the_0010_preview_exactly_and_in_full` pins both.
3. **CI counts.** CI's backend job runs `python -m pytest -q`, which `pytest.ini` points at `backend/tests` and `streamlit_tests` (31), and the Postgres job deselects both folders' other tests. Local `backend/tests` counts and CI counts are now separate and labelled (Baselines and counts), per PR, in every CI expectation and PR body.
4. **After-deploy check.** README Step 4's query now runs before and after 0010 (`information_schema` for the column, `to_jsonb(s) ->> 'affirmation'` for the rows), pinned on Postgres before the upgrade, right after it and after a save (`test_the_owner_s_read_only_queries_around_0010`, moved from `test_services_postgres.py` to `test_migrations.py`; P9); the owner reads Railway's Deploy Logs for the 0009 → 0010 line (pinned against what Alembic logs); and `/openapi.json`, public, names `ServiceAffirmation` only on the new API (`test_the_published_schema_shows_the_new_api_without_a_sign_in`), since `/health/ready` cannot tell.
5. **"Save as new service"** from a saved Nicene service posts the Nicene Creed (`affirmation.test.ts`); planting the reset in `followSaveMode` fails it (F7).
6. **Hanging indent** (small, so built; clarification 11): the printed bulletin's Nicene Creed is one paragraph per sense line in the existing "hanging" style (PDF and Word; P8, and a test reads the Word file's indents), and "Show creed text" does the same (`CreedText`, F10). The Apostles' Creed stays one paragraph, as today.

**Replay result.** @@REPLAY@@

**While building:**
- The first frontend split put the card in its own task after the Settings card; the replay showed the liturgy queries test (`uses a test config equal to the shared fixtures`) failing once the shared outline changed. With the outline now unchanged (clarification 9) that coupling is gone; the card stays with the draft in T7.
- Test sources spell the em dash as an escape (`"\u2014"`), so the em-dash counts find none in the added lines.
- `test_0006_adds_the_nullable_bulletin_column_and_keeps_rows` compared 0006's new column against head; it now upgrades to `0006_services_bulletin` (T2 Step 1).
- The member check holds at two layers (`require_admin` on the route and `require_admin_role` under the church-row lock); P5 removes both to show the test catches it.

## Follow-ups

- Formatting (D 3 to 5) next: the own text is stored as typed, so the formatting PR can read it as markdown (bold, italic, two headings, lists) in all three formats.
- A contemporary (ELLC) Apostles' Creed, if ever wanted, would be a fourth choice (old services keep the traditional one; owner answer B); a "Leave it out" church default is a small addition (answer D: not now).
- Sending `affirmation` only when the API knows it (clarification 10), if PRs are ever deployed out of order.
- "Still to do" on Review could name own text left blank; not asked for.
