# Text formatting

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ] `) syntax for tracking.

**Goal:** Ship the owner's formatting decisions 3 to 5 of 2026-10-24 (binding): bold, italic, two heading sizes, line breaks and simple lists, typed as markdown, in the Word copies, the printed bulletin (PDF and Word) and so the emailed bulletin's attachments; a "Formatting" help line under each box; a text preview on the Review step; "People:" lines in the Call to Worship still bold. Text saved before the change prints exactly as before. **One PR** (S "Deploy order: one PR"): no API change, no migration, no new package.

**Architecture:** T1, the server: a pure module `backend/formatting.py` (the grammar: `parse`, `inline`, `has_marks`, `plain`), read by the printed bulletin's data (`printed_bulletin.formatted`, `_spans`, so `printed_pdf` and `printed_docx` with five new line styles), the Word copy (`worship_service._add_text`, `_runs`), the reviewer's and the pews' routes (`formatting.plain`) and Revise's instruction (keep the marks). The shared fixture `backend/tests/fixtures/shared/formatting.json` is the printed bulletin's own output for 26 cases. T2, the pages: `frontend/src/lib/formatting.ts` (the same grammar and the printed bulletin's rules, passing the same fixture), `FormattingHelp` under the boxes, and `TextPreviewCard` on the Review step. T3 planted violations, T4 verification, T5 the pre-merge note, the draft PR, CI, the merge, the after-deploy check, the phone check and the record.

**Tech Stack:** FastAPI, python-docx, reportlab, pytest (backend); Next.js 16, React 19, Tailwind 4, Base UI, Vitest with Testing Library (frontend).

**Source documents:**
- Spec ("S"): `docs/superpowers/specs/2026-10-25-formatting-design.md` (written with this plan).
- Decisions ("D"): `docs/superpowers/specs/2026-10-24-affirmation-and-formatting-decisions.md` 3 to 5 (binding).
- Model plans: `docs/superpowers/plans/2026-10-24-affirmation.md`, `docs/superpowers/plans/2026-10-20-pew-voices.md`.
- Facts checked for this plan (branch `claude/slice-2-plan-4q33le` at `158b3e6`, 2026-10-25; its code is `main`'s after PR #65): local `backend/tests` `2291 passed, 50 skipped`; frontend `1148 passed` in 122 files; CI on `main`: `backend` 2322 passed, 50 skipped (with `streamlit_tests`' 31), `backend-postgres` 50 passed, 2322 deselected, `frontend` 1148 in 122 files; production at `0010_services_affirmation`; `docs/ops-runbook.md` holds the Affirmation PR B record, not yet on `main` (it rides along in this PR).

## Global Constraints

"T<n>" means Task n. `<repo>` is the GitHub repository of this checkout's `origin` (owner/name), `<api>` the production API's address, `<app>` the production app's address, `<scratch>` the session's scratchpad path and `<N>` the PR's number; write each out when running a command, never into a committed file.

- Run commands from the repo root. Backend: `.venv/bin/python -m pytest -q <paths> 2>&1 | tail -1`. Frontend: one file `(cd frontend && npx vitest run <paths> 2>&1 | grep -E "Test Files|Tests ")`, the suite `(cd frontend && npx vitest run 2>&1 | grep -E "^ +× |FAIL|Test Files|Tests ")`, and `(cd frontend && npx tsc --noEmit >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")`. A time in an expected output is `<t>`. No foreground `sleep`.
- **One PR**, no migration, no new package, no new variable, no generated file changes (`openapi.json` and `schema.d.ts` stay as they are: T4 checks). Branch `claude/slice-2-plan-4q33le`. Stage files by name; never `git add -A`; nothing under `.claude/` is staged.
- Every commit message has a subject, a body and, as its last paragraph (a separate `-m`), these two lines:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS`
- TDD: write the failing tests first and see them fail as quoted.
- Backup push after every task: `git push origin claude/slice-2-plan-4q33le` (never `--force`, never a rebase; if rejected, `git pull --no-rebase origin claude/slice-2-plan-4q33le` and push again). A fix asked for by a review is a new commit, `Fix: <what> (Task <n> review)`.
- `main` is protected (`backend`, `backend-postgres`, `frontend`). Never open, mark ready or merge a PR without the owner's explicit yes for that step. Never touch production, its database or a secret. Never call the real OpenAI API (tests use `openai_client.FakeAI`).
- No em dashes in user-facing copy or in prose for the owner. No church id, email address, invite code, token, key, database URL or real person's name in any doc, commit, test or record. Never log a box's text.
- The frozen Streamlit files (`app.py`, `streamlit_views/`, `streamlit_auth.py`, `streamlit_tenancy.py`, `ui_helpers.py`, `streamlit_tests/`) are not edited.

### How the file directives read
As in the earlier plans: **Create `path`:** the block is the whole new file; **In `path`, replace:** the first block occurs exactly once in the file, as whole lines, and is replaced by the block after **with:**. Blocks are fenced with four backticks and applied in the order written. A directive that does not match exactly once is a stop: find why before changing anything. No file is deleted or moved.

### Baselines and counts
- Starting baseline: local `backend/tests` **2291 passed, 50 skipped**; frontend **1148 passed in 122 files**; typecheck and lint clean. If either differs, stop and ask.
- Local is `.venv/bin/python -m pytest -q backend/tests`; CI's `backend` job runs `python -m pytest -q` from the root (`backend/tests` and `streamlit_tests`, 31), and its `backend-postgres` job `python -m pytest -m postgres -q`.

  | After | Local `backend/tests` | Frontend |
  |---|---|---|
  | T1 | +76 (`test_formatting.py`, a new file) → **2367 passed, 50 skipped** | unchanged |
  | T2 | unchanged | +10 (`formatting.test.ts` 4, `formatting-help.test.tsx` 3, `text-preview-card.test.tsx` 3, new files) → **1158 passed in 125 files** |

  | CI on | `backend` job | `backend-postgres` job | `frontend` job |
  |---|---|---|---|
  | `main` before | 2322 passed, 50 skipped | 50 passed, 2322 deselected | 1148 in 122 files |
  | this PR | **2398 passed, 50 skipped** | **50 passed, 2398 deselected** | **1158 in 125 files** |

## Owner decisions

1. **The formatting decisions of 2026-10-24** (D 3 to 5; "all recommended"; binding): a chosen set, not full markdown (bold, italic, two heading sizes, line breaks, simple lists) in the Word file(s), the printed bulletin and the emailed bulletin; typed as markdown with a short help line under each box and a preview on the Review step (a toolbar may come later); a "People:" line still prints entirely in bold by default and `**...**` bolds part of a line; no links, images, tables or code blocks. This comes after the Affirmation of Faith (done: PR #64, #65) and before the em-dash follow-up PR and Theme PR 2 (D 6).
2. **Standing permission** for safety and reliability fixes with no owner-visible change (carried). Each use is a numbered clarification.

## Spec clarifications

The owner's decisions win over S; the code wins over both where they disagree. **[owner-visible]** items change what someone sees compared with a plain reading of the decisions.

1. **[owner-visible] "People:" bold where it is today.** D 5's "still" is read as: the Call to Worship keeps printing People lines in bold (the only box that splits them today); other boxes print a "People:" line as typed, as today (S Questions, 2).
2. **[owner-visible] The dialogue boxes take bold and italic only.** The Call to Worship and the Assurance of Pardon split Leader and People parts anywhere in the text, as today; a heading or list there would cut across a part, so `#` and `- ` print as typed in those two. Their help line says so by naming only bold and italic.
3. **[owner-visible] Headings are bold Times, 13 pt and 12 pt, never Word's Heading styles** (S "Headings and the section's own heading"; S Questions, 1).
4. **[owner-visible] Numbers stay as typed.** "3." prints "3."; nothing is renumbered.
5. **[owner-visible] Pasted reading text, names, music titles, the sermon title and Settings fields are not formatted** (S "Which boxes").
6. **The preview mirrors the printed bulletin** (its People label bold, the Affirmation's own text bold); the Word copy differs only where it already does (the People label plain, own Affirmation text plain).
7. **No library** (S "No migration, no new dependency").
8. **The reviewer and the pews read the words without marks; Revise keeps them; generation is unchanged** (S "AI interplay").
9. **Linear scan** (standing permission, safety): the first build's scan looked for each opener's close from scratch, quadratic on a 20,000-character line of unclosed marks; the plan's code finds each kind's next close in one pass, and a test holds it under a second.

### Assumptions that turned out false while planning
- "Line breaks" are not new: the Word copy and the printed bulletin already print a box's line breaks (python-docx turns `\n` into a break; the PDF turns it into `<br/>`). Formatting keeps that and adds blocks.
- The Word copy prints the People label plain and only its words in bold; the printed bulletin prints both in bold. Each keeps its own.
- "People:" lines are split only in the Call to Worship (and the Assurance drops a typed one); no other box ever bolded them.
- The Word copy's bytes are not stable run to run (the zip's file times), so "byte-identical" for Word means the document's body XML; the printed PDF is byte for byte (`invariant=1`).
- pypdf reads the standard fonts' bullet as `"\x7f"`; the PDF draws "•" (tests map it back).
- Revise is offered on typed and saved text, not only AI drafts, so marks do reach it.
- No API change is needed: the OpenAPI snapshot is unchanged, so one PR is safe.
- A Turbopack build fails when `frontend/node_modules` is a symlink; a hard-linked copy works (replay only).

### Risks
In S "Risks". For this plan: a reviewer may read old text with a typed "- " list printing as a list as a regression; it is the feature (D 3), and the record notes it if the owner sees it.

## File Structure

**Created:** `backend/formatting.py`, `backend/tests/test_formatting.py`, `backend/tests/fixtures/shared/formatting.json`, `frontend/src/lib/formatting.ts`, `frontend/src/lib/formatting.test.ts`, `frontend/src/components/builder/formatting-help.tsx`, `frontend/src/components/builder/formatting-help.test.tsx`, `frontend/src/components/builder/review/text-preview-card.tsx`, `frontend/src/components/builder/review/text-preview-card.test.tsx`.

**Modified:** backend `printed_bulletin.py`, `printed_pdf.py`, `printed_docx.py`, `worship_service.py`, `usecases/liturgy_review.py`, `api/routes/liturgy_review.py`, `tests/fixtures/README.md`, and the tests `test_no_streamlit_in_core.py`, `test_usecase_liturgy_revise.py`; frontend `components/builder/liturgy/section-card.tsx`, `custom-element-card.tsx`, `affirmation-card.tsx`, `components/builder/bulletin/bulletin-step.tsx`, `components/builder/review/review-send-step.tsx`, and the tests `affirmation-card.test.tsx`, `liturgy-step.test.tsx`, `review-step.test.tsx`, `review-send-step.test.tsx`. Riding along: the spec, this plan and `docs/ops-runbook.md` (the Affirmation PR B record).

### Task 1: The grammar and what prints (S "Grammar", "Which boxes", "What prints where", "Safety", "AI interplay", "Backward compatibility", "Limits")

**Files:** Create `backend/formatting.py`, `backend/tests/test_formatting.py`, `backend/tests/fixtures/shared/formatting.json`. Modify `backend/printed_bulletin.py`, `backend/printed_pdf.py`, `backend/printed_docx.py`, `backend/worship_service.py`, `backend/usecases/liturgy_review.py`, `backend/api/routes/liturgy_review.py`, `backend/tests/fixtures/README.md`, `backend/tests/test_no_streamlit_in_core.py`, `backend/tests/test_usecase_liturgy_revise.py`.

- [ ] **Step 1: Write the failing tests**

The fixture's `lines` are what `printed_bulletin` prints for each case (written from the build, then read case by case against S "Grammar"); the old-text tests compare with verbatim copies of today's helpers and the existing characterization test's Streamlit `build_docx`.

<!-- directives:T1_TESTS -->
**Create `backend/tests/fixtures/shared/formatting.json`:**

````
{
 "_about": "Formatting spec, 2026-10-25: each box's text as the printed bulletin prints it (printed_bulletin.formatted, _leader_people, _assurance); a span is [text, flags], flags \"b\" bold, \"i\" italic. backend/tests/test_formatting.py and frontend/src/lib/formatting.test.ts check every case; the Review step's preview draws these lines.",
 "assurance_response": "People: Thanks be to God! Amen.",
 "cases": [
  {"name": "plain text prints as one line, as typed", "box": "prayer", "text": "Gracious God,\nwe gather in your name.\n\nAmen.",
   "lines": [
    {"style": "body", "marker": "", "spans": [["Gracious God,\nwe gather in your name.\n\nAmen.", ""]]}]},
  {"name": "a lone asterisk after a verse", "box": "prayer", "text": "Psalm 23:1*",
   "lines": [
    {"style": "body", "marker": "", "spans": [["Psalm 23:1*", ""]]}]},
  {"name": "a hash before a number", "box": "prayer", "text": "#1 hymn: we sing it again",
   "lines": [
    {"style": "body", "marker": "", "spans": [["#1 hymn: we sing it again", ""]]}]},
  {"name": "asterisks with spaces round them", "box": "prayer", "text": "5 * 3 * 2 = 30 blessings",
   "lines": [
    {"style": "body", "marker": "", "spans": [["5 * 3 * 2 = 30 blessings", ""]]}]},
  {"name": "asterisks between digits", "box": "prayer", "text": "2*3*4 and a lone ** pair",
   "lines": [
    {"style": "body", "marker": "", "spans": [["2*3*4 and a lone ** pair", ""]]}]},
  {"name": "a mark touching a letter outside does not open or close", "box": "prayer", "text": "a**b**c and **God**s love",
   "lines": [
    {"style": "body", "marker": "", "spans": [["a**b**c and **God**s love", ""]]}]},
  {"name": "bold and italic", "box": "prayer", "text": "We praise you, **Holy One**, for *all* your gifts.",
   "lines": [
    {"style": "body", "marker": "", "spans": [["We praise you, ", ""], ["Holy One", "b"], [", for ", ""], ["all", "i"], [" your gifts.", ""]]}]},
  {"name": "italic inside bold, bold inside italic", "box": "prayer", "text": "**a *b* c** and *d **e** f*",
   "lines": [
    {"style": "body", "marker": "", "spans": [["a ", "b"], ["b", "bi"], [" c", "b"], [" and ", ""], ["d ", "i"], ["e", "bi"], [" f", "i"]]}]},
  {"name": "a backslash prints the mark itself", "box": "prayer", "text": "Not \\*italic\\*, not \\*\\*bold\\*\\*; a back\\slash stays",
   "lines": [
    {"style": "body", "marker": "", "spans": [["Not *italic*, not **bold**; a back\\slash stays", ""]]}]},
  {"name": "a mark never spans a line", "box": "prayer", "text": "**open\nclose**",
   "lines": [
    {"style": "body", "marker": "", "spans": [["**open\nclose**", ""]]}]},
  {"name": "headings, text and lists", "box": "prayer", "text": "# For the world\nWe pray for peace.\n## Near and far\n- the sick\n- the lonely\n\nHear us, O God.",
   "lines": [
    {"style": "heading1", "marker": "", "spans": [["For the world", "b"]]},
    {"style": "body", "marker": "", "spans": [["We pray for peace.", ""]]},
    {"style": "heading2", "marker": "", "spans": [["Near and far", "b"]]},
    {"style": "item", "marker": "•", "spans": [["the sick", ""]]},
    {"style": "item", "marker": "•", "spans": [["the lonely", ""]]},
    {"style": "body", "marker": "", "spans": [["Hear us, O God.", ""]]}]},
  {"name": "numbers stay as typed", "box": "prayer", "text": "3. Third\n10. Tenth\n1234. Not a list\n1) Not a list",
   "lines": [
    {"style": "item", "marker": "3.", "spans": [["Third", ""]]},
    {"style": "item", "marker": "10.", "spans": [["Tenth", ""]]},
    {"style": "body", "marker": "", "spans": [["1234. Not a list\n1) Not a list", ""]]}]},
  {"name": "not a heading or a list", "box": "prayer", "text": "### three\n#none\n-none\n* star\n# \n- ",
   "lines": [
    {"style": "body", "marker": "", "spans": [["### three\n#none\n-none\n* star\n# \n- ", ""]]}]},
  {"name": "blank lines round a block are dropped, inside text they stay", "box": "prayer", "text": "\n\nFirst\n\n\nSecond\n\n# Heading\n\n\n",
   "lines": [
    {"style": "body", "marker": "", "spans": [["First\n\n\nSecond", ""]]},
    {"style": "heading1", "marker": "", "spans": [["Heading", "b"]]}]},
  {"name": "marks inside a heading and an item", "box": "prayer", "text": "# The *Holy* Spirit\n- **all** who mourn",
   "lines": [
    {"style": "heading1", "marker": "", "spans": [["The ", "b"], ["Holy", "bi"], [" Spirit", "b"]]},
    {"style": "item", "marker": "•", "spans": [["all", "b"], [" who mourn", ""]]}]},
  {"name": "HTML and XML print as text", "box": "prayer", "text": "<b>x</b> & <script>alert(1)</script> **<i>y</i> & z**",
   "lines": [
    {"style": "body", "marker": "", "spans": [["<b>x</b> & <script>alert(1)</script> ", ""], ["<i>y</i> & z", "b"]]}]},
  {"name": "the confession is all bold, italic added", "box": "confession", "text": "We confess *our sin*.\n- pride\n# Mercy",
   "lines": [
    {"style": "bold", "marker": "", "spans": [["We confess ", "b"], ["our sin", "bi"], [".", "b"]]},
    {"style": "item", "marker": "•", "spans": [["pride", "b"]]},
    {"style": "heading1", "marker": "", "spans": [["Mercy", "b"]]}]},
  {"name": "dialogue as before", "box": "dialogue", "text": "Leader: The Lord be with you.\nPeople: And also with you.",
   "lines": [
    {"style": "hanging", "marker": "", "spans": [["Leader: ", ""], ["The Lord be with you.", ""]]},
    {"style": "hanging", "marker": "", "spans": [["People: ", "b"], ["And also with you.", "b"]]}]},
  {"name": "dialogue with marks", "box": "dialogue", "text": "Leader: Come, **all** who are weary.\nPeople: We come *gladly*.",
   "lines": [
    {"style": "hanging", "marker": "", "spans": [["Leader: ", ""], ["Come, ", ""], ["all", "b"], [" who are weary.", ""]]},
    {"style": "hanging", "marker": "", "spans": [["People: ", "b"], ["We come ", "b"], ["gladly", "bi"], [".", "b"]]}]},
  {"name": "dialogue takes no headings or lists", "box": "dialogue", "text": "# Not a heading\nLeader: - not a list\nPeople: 1. not a list",
   "lines": [
    {"style": "body", "marker": "", "spans": [["# Not a heading", ""]]},
    {"style": "hanging", "marker": "", "spans": [["Leader: ", ""], ["- not a list", ""]]},
    {"style": "hanging", "marker": "", "spans": [["People: ", "b"], ["1. not a list", "b"]]}]},
  {"name": "dialogue with no label", "box": "dialogue", "text": "Come and *worship*.",
   "lines": [
    {"style": "body", "marker": "", "spans": [["Come and ", ""], ["worship", "i"], [".", ""]]}]},
  {"name": "dialogue mid-line label", "box": "dialogue", "text": "Leader: Lift up your hearts. People: We lift them **up**.",
   "lines": [
    {"style": "hanging", "marker": "", "spans": [["Leader: ", ""], ["Lift up your hearts.", ""]]},
    {"style": "hanging", "marker": "", "spans": [["People: ", "b"], ["We lift them up.", "b"]]}]},
  {"name": "assurance as before", "box": "assurance", "text": "Leader: In Christ we are forgiven.",
   "lines": [
    {"style": "hanging", "marker": "", "spans": [["Leader: ", ""], ["In Christ we are forgiven.", ""]]},
    {"style": "bold", "marker": "", "spans": [["People: Thanks be to God! Amen.", "b"]]}]},
  {"name": "assurance with marks, typed People left out", "box": "assurance", "text": "Leader: In **Christ** we are *forgiven*. People: Thanks be to God!",
   "lines": [
    {"style": "hanging", "marker": "", "spans": [["Leader: ", ""], ["In ", ""], ["Christ", "b"], [" we are ", ""], ["forgiven", "i"], [".", ""]]},
    {"style": "bold", "marker": "", "spans": [["People: Thanks be to God! Amen.", "b"]]}]},
  {"name": "announcement as before", "box": "announcement", "text": "Tuesday: Bible study\nWednesday: Choir",
   "lines": [
    {"style": "center", "marker": "", "spans": [["Tuesday: Bible study\nWednesday: Choir", ""]]}]},
  {"name": "announcement with a heading and a list", "box": "announcement", "text": "# This week\n- Tuesday: **Bible study**\n2. Choir",
   "lines": [
    {"style": "center_heading1", "marker": "", "spans": [["This week", "b"]]},
    {"style": "center", "marker": "", "spans": [["• Tuesday: ", ""], ["Bible study", "b"]]},
    {"style": "center", "marker": "", "spans": [["2. Choir", ""]]}]}
 ]
}
````

**Create `backend/tests/test_formatting.py`:**

````
"""Text formatting (formatting spec, 2026-10-25; owner decisions 3 to 5):
the grammar (shared/formatting.json, which the frontend's preview passes
too), old text printing exactly as before in every file, the Word copy, the
printed bulletin (PDF and Word) and the email's attachments reading the
marks, nothing typed ever becoming markup, the limits, and the reviewer and
the pews reading the words without the marks."""
import dataclasses
import json
import time
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from docx.shared import Inches, Pt
from pypdf import PdfReader

import affirmation as af
import formatting
import printed_bulletin as pb
import printed_docx
import printed_pdf
import service_bulletin as sb
import worship_service
from integrations import openai_client
from liturgy_config import ASSURANCE_RESPONSE, LIMITS
from printed_bulletin import Line, Span
from service_output import CustomElement
from tests.api_helpers import church_headers, make_api_client
from tests.test_build_docx_characterization import body_xml, legacy_build_docx, legacy_kwargs, new_kwargs
from tests.test_printed_bulletin import service
from usecases import archive, documents
from usecases import email as email_usecase

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "shared" / "formatting.json").read_text("utf-8"))
CASES = FIXTURE["cases"]

# Text saved before formatting, with characters a prayer may hold: none is a mark.
OLD = [
    "Psalm 23:1*", "#1 hymn: we sing it again", "5 * 3 * 2 = 30 blessings", "2*3*4", "A lone ** pair",
    "****", "a**b**c and **God**s love", "-dash first\n#hash first\n### three\n1.5 million\n1) one\n1234. four",
    "Line one\n\nLine three\n", "* not a list", "Back\\slash stays \\ here", "**open\nclose**", "# \n- ",
]


def _lines(box: str, text: str) -> list[Line]:
    if box == "prayer":
        return pb.formatted(text)
    if box == "confession":
        return pb.formatted(text, "bold", bold=True)
    if box == "dialogue":
        return pb._leader_people(text)
    if box == "assurance":
        return pb._assurance(text)
    return pb.formatted(text, "center")


def _as_fixture(line: Line) -> dict:
    return {"style": line.style, "marker": line.marker,
            "spans": [[s.text, ("b" if s.bold else "") + ("i" if s.italic else "")] for s in line.spans]}


# --- the grammar, shared with the frontend ---

def test_the_shared_fixture_covers_every_box_and_names_the_assurance_response():
    assert FIXTURE["assurance_response"] == ASSURANCE_RESPONSE
    assert {c["box"] for c in CASES} == {"prayer", "confession", "dialogue", "assurance", "announcement"}
    assert len(CASES) == 26 and len({c["name"] for c in CASES}) == 26


@pytest.mark.parametrize("case", CASES, ids=[c["name"] for c in CASES])
def test_the_printed_lines_are_the_shared_fixture_s(case):
    assert [_as_fixture(line) for line in _lines(case["box"], case["text"])] == case["lines"]


def test_the_marks():
    assert formatting.parse("**b** *i*") == [formatting.Block("text", (Span("b", True), Span(" "), Span("i", False, True)))]
    assert formatting.parse("# One\n## Two\n- three\n4. four") == [
        formatting.Block("heading1", (Span("One"),)), formatting.Block("heading2", (Span("Two"),)),
        formatting.Block("item", (Span("three"),), "•"), formatting.Block("item", (Span("four"),), "4.")]
    assert formatting.parse("# One\n- two", inline_only=True) == [formatting.Block("text", (Span("# One\n- two"),))]
    assert formatting.plain("# For all\n- **the** sick\n3. *the* lonely\n\\*") == "For all\n- the sick\n3. the lonely\n*"
    assert formatting.plain("Leader: **Come**.\n# x", inline_only=True) == "Leader: Come.\n# x"


@pytest.mark.parametrize("text", OLD)
def test_old_text_has_no_mark(text):
    assert not formatting.has_marks(text)
    assert formatting.plain(text) == text


def test_a_long_text_full_of_unclosed_marks_reads_quickly():
    for text in ("*a " * 6666, "**a " * 5000, "*" * LIMITS.max_section_text, "**x* " * 4000):
        started = time.monotonic()
        formatting.parse(text)
        assert time.monotonic() - started < 1.0


# --- old text prints exactly as before ---

def _legacy_formatted(text, style="body", *, bold=False):
    return [Line(style, (Span(text, bold=bold),))]


def _legacy_leader_people(text):
    """printed_bulletin._leader_people before formatting, verbatim."""
    import re
    matches = list(re.compile(r"\b(Leader|People):\s*", re.IGNORECASE).finditer(text))
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


def _legacy_assurance(text):
    """printed_bulletin._assurance before formatting, verbatim."""
    leader = text.strip()
    people = pb._ASSURANCE_PEOPLE.search(leader)
    if people:
        leader = leader[: people.start()].strip()
    if leader.startswith("Leader:"):
        leader = leader[7:].strip()
    lines = [Line("hanging", (Span("Leader: "), Span(leader)))] if leader else []
    return [*lines, Line("bold", (Span(ASSURANCE_RESPONSE, bold=True),))]


def _old_service(text: str) -> pb.PrintedService:
    ps = service()
    liturgy = {key: text for key in ps.resolved.liturgy}
    liturgy["call_to_worship"] = f"Leader: {text}\nPeople: {text}"
    liturgy["assurance"] = f"Leader: {text}"
    resolved = dataclasses.replace(ps.resolved, liturgy=liturgy, custom_elements=(CustomElement("Anthem", text, "sermon"),),
                                   affirmation=af.Affirmation(True, "own", text))
    week = sb.ServiceBulletin(announcements=sb.Announcements(activities=text, prayer_concerns=text,
                                                             collection=text, other=text))
    return dataclasses.replace(ps, resolved=resolved, bulletin=week)


@pytest.mark.parametrize("text", OLD)
def test_old_text_prints_in_the_printed_bulletin_exactly_as_before(text, monkeypatch):
    ps = _old_service(text)
    lines = pb.order_of_worship(ps) + pb.announcements(ps)
    pdf, word = printed_pdf.render_pdf(ps), Document(BytesIO(printed_docx.render_docx(ps))).element.body.xml
    monkeypatch.setattr(pb, "formatted", _legacy_formatted)
    monkeypatch.setattr(pb, "_leader_people", _legacy_leader_people)
    monkeypatch.setattr(pb, "_assurance", _legacy_assurance)
    assert lines == pb.order_of_worship(ps) + pb.announcements(ps)
    assert pdf == printed_pdf.render_pdf(ps)                      # byte for byte (the PDF is invariant)
    assert word == Document(BytesIO(printed_docx.render_docx(ps))).element.body.xml


@pytest.mark.parametrize("text", OLD)
def test_old_text_prints_in_the_word_copy_exactly_as_streamlit_did(text):
    liturgy = {key: text for key in new_kwargs()["liturgy"]}
    liturgy["call_to_worship"] = f"Leader: {text}\nPeople: {text}"
    liturgy["assurance"] = f"Leader: {text}"
    custom = [{"label": "Anthem", "text": text, "insert_after": "sermon"}]
    new = new_kwargs(include_sermon=True, include_prayers_of_the_people=True)
    old = legacy_kwargs(include_sermon=True, include_prayers_of_the_people=True)
    for kwargs in (new, old):
        kwargs.update(liturgy=dict(liturgy), custom_elements=custom)
    assert body_xml(worship_service.build_docx(**new)) == body_xml(legacy_build_docx(**old).getvalue()).replace(
        "Old Testament Reading", "First Reading")


def test_old_own_affirmation_text_prints_in_the_word_copy_as_one_paragraph():
    doc = Document(BytesIO(worship_service.build_docx(**new_kwargs(affirmation=af.Affirmation(True, "own", OLD[7])))))
    texts = [p.text for p in doc.paragraphs]
    assert texts[texts.index("Affirmation of Faith") + 1] == OLD[7]


# --- the Word copy ---

FORMATTED = "# For the world\nWe pray for **peace** and *justice*.\n## Near\n- the sick\n12. the lonely"


def _paragraph(doc, text):
    return next(p for p in doc.paragraphs if p.text == text)


def test_the_word_copy_reads_the_marks():
    liturgy = dict(new_kwargs()["liturgy"], opening_prayer=FORMATTED, prayer_of_confession="We confess *our sin*.",
                   call_to_worship="Leader: Come, **all**.\nPeople: We come *gladly*.")
    doc = Document(BytesIO(worship_service.build_docx(**{**new_kwargs(), "liturgy": liturgy})))
    heading = _paragraph(doc, "For the world")
    assert heading.style.name == "Normal" and heading.paragraph_format.keep_with_next
    assert [(r.bold, r.font.size) for r in heading.runs] == [(True, Pt(13))]
    assert [(r.bold, r.font.size) for r in _paragraph(doc, "Near").runs] == [(True, Pt(12))]
    text = _paragraph(doc, "We pray for peace and justice.")
    assert [(r.text, r.bold, r.italic) for r in text.runs] == [
        ("We pray for ", None, None), ("peace", True, None), (" and ", None, None), ("justice", None, True),
        (".", None, None)]
    for item, marker in (("•\tthe sick", "•\t"), ("12.\tthe lonely", "12.\t")):
        p = _paragraph(doc, item)
        assert p.runs[0].text == marker
        assert (p.paragraph_format.left_indent, p.paragraph_format.first_line_indent) == (Inches(0.25), Inches(-0.25))
    confession = _paragraph(doc, "We confess our sin.")
    assert [(r.text, r.bold, r.italic) for r in confession.runs] == [
        ("We confess ", True, None), ("our sin", True, True), (".", True, None)]
    people = _paragraph(doc, "People: We come gladly.")
    assert [(r.text, r.bold, r.italic) for r in people.runs] == [
        ("People: ", None, None), ("We come ", True, None), ("gladly", True, True), (".", True, None)]
    assert [(r.text, r.bold) for r in _paragraph(doc, "Leader: Come, all.").runs] == [
        ("Leader: Come, ", None), ("all", True), (".", None)]


# --- the printed bulletin and the email ---

@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email="pastor@example.com"))


def _input(**liturgy) -> archive.ServiceInput:
    return archive.ServiceInput(service_date=date(2026, 10, 4), liturgy=liturgy)


def _pdf_text(content: bytes) -> str:
    """The PDF's words; pypdf reads the standard fonts' bullet (WinAnsi code 0x7F) as "\x7f"."""
    pages = PdfReader(BytesIO(content)).pages
    return " ".join(" ".join(page.extract_text().replace("\x7f", "•").split()) for page in pages)


def test_the_printed_bulletin_reads_the_marks_in_pdf_and_word(church):
    pdf = _pdf_text(documents.build_printed(church, _input(opening_prayer=FORMATTED), "pdf", None,
                                            charge=lambda n: None).content)
    assert "For the world We pray for peace and justice. Near • the sick 12. the lonely" in pdf
    assert "**" not in pdf and "# " not in pdf
    word = Document(BytesIO(documents.build_printed(church, _input(opening_prayer=FORMATTED), "docx", None,
                                                    charge=lambda n: None).content))
    assert [(r.bold, r.font.size) for r in _paragraph(word, "For the world").runs] == [(True, Pt(13))]
    item = _paragraph(word, "•\tthe sick")
    assert (item.paragraph_format.left_indent, item.paragraph_format.first_line_indent) == (Inches(0.25),
                                                                                           Inches(-0.25))
    assert [(r.text, r.bold) for r in _paragraph(word, "We pray for peace and justice.").runs][1] == ("peace", True)


def test_the_announcements_keep_a_heading_and_a_list_centered():
    week = sb.ServiceBulletin(announcements=sb.Announcements(other="# This week\n- Choir **at seven**"))
    word = Document(BytesIO(printed_docx.render_docx(service(bulletin=week))))
    heading, item = _paragraph(word, "This week"), _paragraph(word, "• Choir at seven")
    assert heading.alignment == item.alignment == printed_docx.WD_ALIGN_PARAGRAPH.CENTER
    assert [(r.bold, r.font.size) for r in heading.runs] == [(True, Pt(13))]


def test_the_email_s_attachments_read_the_marks(church):
    files = email_usecase._attachments(church, _input(opening_prayer=FORMATTED), ["docx", "pdf"], None,
                                       lambda n: None)
    word = Document(BytesIO(files[0].content))
    assert [(r.bold, r.font.size) for r in _paragraph(word, "For the world").runs] == [(True, Pt(13))]
    assert "• the sick 12. the lonely" in _pdf_text(files[1].content)


def test_nothing_typed_becomes_markup(church):
    typed = "<b>x</b> & <font size=40>y</font> **<i>z</i> & <br/>**\n- <para>\n# </b>&amp;"
    pdf = _pdf_text(documents.build_printed(church, _input(opening_prayer=typed), "pdf", None,
                                            charge=lambda n: None).content)
    assert "<b>x</b> & <font size=40>y</font> <i>z</i> & <br/> • <para> </b>&amp;" in pdf
    for content in (documents.build_printed(church, _input(opening_prayer=typed), "docx", None,
                                            charge=lambda n: None).content,
                    documents.build_document(church, _input(opening_prayer=typed), "pastor").content):
        texts = [p.text for p in Document(BytesIO(content)).paragraphs]
        assert "<b>x</b> & <font size=40>y</font> <i>z</i> & <br/>" in texts and "</b>&amp;" in texts


def test_a_prayer_at_the_limit_full_of_marks_prints(church):
    text = ("- **a** *b*\n" * 2000)[: LIMITS.max_section_text]
    assert len(text) == LIMITS.max_section_text
    assert documents.build_printed(church, _input(prayers_of_the_people=text, opening_prayer=text), "pdf", None,
                                   charge=lambda n: None).content.startswith(b"%PDF")
    assert documents.build_document(church, _input(opening_prayer=text), "pastor").content.startswith(b"PK")


# --- the reviewer and the pews read the words, without the marks ---

def test_the_reviewer_and_the_pews_read_the_words_without_the_marks(tmp_db, make_user, make_church):
    owner = make_user(email="pastor@example.com")
    cid = make_church(name="Grace", owner_user_id=owner)
    client = make_api_client()
    cards = [{"section": "opening_prayer", "origin": "typed", "text": "# Gathering\nGracious God, as **we** journey, "
                                                                     "hear *us*.\n- all who mourn"},
             {"section": "call_to_worship", "origin": "typed", "text": "Leader: **Come**.\n# People: not a heading"}]
    r = client.post("/liturgy/review", json={"cards": cards}, headers=church_headers("pastor@example.com", cid))
    assert r.status_code == 200, r.text
    assert {"tag": "rules", "text": 'Stock phrase "as we journey". Say it more naturally.', "source": "code"} in \
        r.json()["cards"][0]["notes"]
    for path, reply in (("/liturgy/review", '{"cards": [], "service_notes": []}'), ("/liturgy/pews", '{"voices": []}')):
        fake = openai_client.FakeAI(reply=reply)
        openai_client.set_ai_for_tests(fake)
        r = client.post(path, json={"cards": cards}, headers=church_headers("pastor@example.com", cid))
        assert r.status_code == 200, r.text
        sent = fake.calls[0]["messages"][-1]["content"]
        assert "Gathering\nGracious God, as we journey, hear us.\n- all who mourn" in sent
        assert "Leader: Come.\n# People: not a heading" in sent
        assert "**" not in sent
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````
            "affirmation, liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review, "
````

**with:**

````
            "affirmation, formatting, liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review, "
````

**In `backend/tests/test_usecase_liturgy_revise.py`, replace:**

````
               "(Leader/People lines where present) and about the same length. Output only the revised text.")
````

**with:**

````
               "(Leader/People lines where present) and about the same length. Keep any formatting marks the draft "
               "has (**bold**, *italic*, lines starting # or ## for headings, - or 1. for lists) where they still "
               "fit, and add none. Output only the revised text.")
````
<!-- /directives -->

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python -m pytest -q backend/tests/test_formatting.py backend/tests/test_no_streamlit_in_core.py backend/tests/test_usecase_liturgy_revise.py 2>&1 | tail -1`
**Expected:** @@T1_FAIL@@

- [ ] **Step 3: Write the module and the printing**

<!-- directives:T1_CODE -->
**Create `backend/formatting.py`:**

````
"""Text formatting (formatting spec, 2026-10-25; owner decisions 3 to 5 of
2026-10-24): the chosen set of markdown a text box takes, read the same way
by the Word files, the printed bulletin (PDF and Word) and so the emailed
bulletin's attachments. frontend/src/lib/formatting.ts mirrors it for the
Review step's preview; both pass tests/fixtures/shared/formatting.json.

The grammar (the spec's "Grammar" is the full statement):
- Inline, within one line: **bold**, *italic* (either may hold the other).
  The line is read left to right into marks (a backslash and one of
  ESCAPABLE, "**", "*") and other characters. A mark opens only before a
  character that is not a space and not after an ASCII letter or digit; it
  closes at the next mark of its kind after a character that is not a space
  and not before an ASCII letter or digit, with something between. A mark
  that never closes prints as typed, so "Psalm 23:1*", "5 * 3" and "2*3*4"
  print as typed. A backslash before *, #, - or . prints that character
  alone ("\\*").
- Blocks, a whole line starting at its first character: "# " a heading,
  "## " a smaller heading, "- " a bulleted item, "1. " (one to three digits)
  a numbered item, its number as typed. Anything else is text; text lines
  next to each other stay one paragraph with their line breaks, as today.
  "#1 hymn", "### x" and "-x" are text.
- Two boxes are dialogue (INLINE_ONLY): the Call to Worship and the
  Assurance of Pardon take bold and italic only, so their Leader and People
  lines read as today.

has_marks is the backward-compatibility switch: text without any mark
prints exactly as before this change (every renderer keeps its old path for
it). Pure: no python-docx, reportlab, database or FastAPI.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["text", "heading1", "heading2", "item"]

# The sections whose text is Leader/People dialogue: bold and italic only.
INLINE_ONLY = frozenset({"call_to_worship", "assurance"})
BULLET = "•"
ESCAPABLE = "*#-."
# "Whitespace" for the marks' rules: a space, a tab or a no-break space.
_SPACE = " \t\u00a0"
_ALNUM = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_HEADING = re.compile(r"(#{1,2}) (.*)")
_BULLET = re.compile(r"- (.*)")
_NUMBER = re.compile(r"([0-9]{1,3}\.) (.*)")


@dataclass(frozen=True)
class Span:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class Block:
    kind: Kind
    spans: tuple[Span, ...]
    marker: str = ""          # an item's BULLET or its number as typed ("3.")


def _strip(s: str) -> str:
    return s.strip(_SPACE)


def _tokens(line: str) -> list[tuple[str, int, int]]:
    """The line read left to right into (kind, start, end): "esc" (a backslash
    and an ESCAPABLE character), "**", "*", or "ch" (any other character)."""
    out, i = [], 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line) and line[i + 1] in ESCAPABLE:
            out.append(("esc", i, i + 2))
        elif line.startswith("**", i):
            out.append(("**", i, i + 2))
        elif line[i] == "*":
            out.append(("*", i, i + 1))
        else:
            out.append(("ch", i, i + 1))
        i = out[-1][2]
    return out


def _inline_line(line: str) -> list[Span]:
    """Bold and italic in one line, in one pass (linear in its length)."""
    toks = _tokens(line)
    n = len(toks)

    def before(t) -> str:
        return line[t[1] - 1] if t[1] > 0 else ""

    def after(t) -> str:
        return line[t[2]] if t[2] < len(line) else ""

    opens = [t[0] in ("*", "**") and after(t) not in ("", *_SPACE) and before(t) not in _ALNUM for t in toks]
    closes = [t[0] in ("*", "**") and before(t) not in _SPACE and after(t) not in _ALNUM for t in toks]
    # nxt[kind][i]: the first closing token of that kind at i or after it (n: none).
    nxt = {kind: [n] * (n + 1) for kind in ("*", "**")}
    for kind, table in nxt.items():
        for i in range(n - 1, -1, -1):
            table[i] = i if toks[i][0] == kind and closes[i] else table[i + 1]

    def walk(lo: int, hi: int, bold: bool, italic: bool) -> list[Span]:
        out: list[Span] = []
        buf: list[str] = []
        i = lo
        while i < hi:
            kind, a, b = toks[i]
            if kind == "esc":
                buf.append(line[a + 1])
                i += 1
                continue
            if kind in ("*", "**") and opens[i] and not (bold if kind == "**" else italic):
                j = nxt[kind][i + 2] if i + 2 <= n else n          # at least one token inside
                if j < hi:
                    if buf:
                        out.append(Span("".join(buf), bold, italic))
                        buf = []
                    out += walk(i + 1, j, bold or kind == "**", italic or kind == "*")
                    i = j + 1
                    continue
            buf.append(line[a:b])
            i += 1
        if buf:
            out.append(Span("".join(buf), bold, italic))
        return out

    return walk(0, n, False, False)


def merge(spans) -> tuple[Span, ...]:
    """Spans with neighbours of the same type joined, empty ones dropped."""
    out: list[Span] = []
    for span in spans:
        if not span.text:
            continue
        if out and (out[-1].bold, out[-1].italic) == (span.bold, span.italic):
            out[-1] = Span(out[-1].text + span.text, span.bold, span.italic)
        else:
            out.append(span)
    return tuple(out)


def inline(text: str) -> tuple[Span, ...]:
    """Bold and italic in `text`, line by line (a mark never spans a line break)."""
    spans: list[Span] = []
    for n, line in enumerate(text.split("\n")):
        if n:
            spans.append(Span("\n"))
        spans += _inline_line(line)
    return merge(spans)


def _block_of(line: str) -> tuple[Kind, str, str] | None:
    """A heading or an item line's kind, its content and its marker; None for text."""
    for pattern, kind in ((_HEADING, None), (_BULLET, "item"), (_NUMBER, "item")):
        m = pattern.fullmatch(line)
        if m is None:
            continue
        content = _strip(m.group(m.lastindex))
        if not content:
            return None
        if kind is None:
            return ("heading1" if m.group(1) == "#" else "heading2"), content, ""
        return "item", content, (BULLET if pattern is _BULLET else m.group(1))
    return None


def parse(text: str, *, inline_only: bool = False) -> list[Block]:
    """The text as printed blocks. Inline only: one text block."""
    if inline_only:
        return [Block("text", inline(text))] if text else []
    blocks: list[Block] = []
    lines: list[str] = []

    def flush() -> None:
        while lines and not _strip(lines[0]):
            lines.pop(0)
        while lines and not _strip(lines[-1]):
            lines.pop()
        if lines:
            blocks.append(Block("text", inline("\n".join(lines))))
        lines.clear()

    for line in text.split("\n"):
        found = _block_of(line)
        if found is None:
            lines.append(line)
            continue
        flush()
        kind, content, marker = found
        blocks.append(Block(kind, inline(content), marker))
    flush()
    return blocks


def has_marks(text: str, *, inline_only: bool = False) -> bool:
    """Whether any mark of the grammar is in `text`. False: it prints exactly as before formatting."""
    for line in text.split("\n"):
        if not inline_only and _block_of(line) is not None:
            return True
        if line and inline(line) != (Span(line),):
            return True
    return False


def plain(text: str, *, inline_only: bool = False) -> str:
    """The words as they print, without the marks: what the reviewer and the pews read.
    A heading's "#" goes; an item keeps "- " or its number, so the list still reads as one."""
    if not has_marks(text, inline_only=inline_only):
        return text
    out = []
    for line in text.split("\n"):
        found = None if inline_only else _block_of(line)
        if found is None:
            out.append("".join(s.text for s in inline(line)))
            continue
        kind, content, marker = found
        words = "".join(s.text for s in inline(content))
        out.append(words if kind != "item" else f"{'-' if marker == BULLET else marker} {words}")
    return "\n".join(out)
````

**In `backend/printed_bulletin.py`, replace:**

````
  from before PR 3b), so those pages print as before.
- printed_date, printed_filename, PDF_MIME.
````

**with:**

````
  from before PR 3b), so those pages print as before.
- Formatting (formatting spec): a box's text prints through `formatted`
  (headings, items, bold and italic as formatting.parse reads them) and the
  Call to Worship's and the Assurance's parts through `_spans` (bold and
  italic only); text without a mark prints exactly as before.
- printed_date, printed_filename, PDF_MIME.
````

**In `backend/printed_bulletin.py`, replace:**

````
from affirmation import APOSTLES_CREED  # noqa: F401 (printed_bulletin.APOSTLES_CREED, as before)
from bulletin_settings import GLORIA_PATRI, BulletinSettings
````

**with:**

````
import formatting as fmt
from affirmation import APOSTLES_CREED  # noqa: F401 (printed_bulletin.APOSTLES_CREED, as before)
from bulletin_settings import GLORIA_PATRI, BulletinSettings
from formatting import Span
````

**In `backend/printed_bulletin.py`, replace:**

````
                "title", "box", "contact", "center"]


@dataclass(frozen=True)
class Span:
    text: str
    bold: bool = False
    italic: bool = False
````

**with:**

````
                "title", "box", "contact", "center",
                # formatting (formatting spec): a box's headings and list items
                "heading1", "heading2", "item", "center_heading1", "center_heading2"]
````

**In `backend/printed_bulletin.py`, replace:**

````
    right: str = ""
    starred: bool = field(default=False, compare=False)   # a heading the settings star (the stand note's rule)
````

**with:**

````
    right: str = ""
    marker: str = ""           # an "item" line's bullet or typed number (formatting spec)
    starred: bool = field(default=False, compare=False)   # a heading the settings star (the stand note's rule)
````

**In `backend/printed_bulletin.py`, replace:**

````
def _leader_people(text: str) -> list[Line]:
    """worship_service._add_leader_people_paragraph's reading: Leader lines in
    normal type, People lines in bold, each with a hanging indent."""
    matches = list(_PEOPLE_LEADER.finditer(text))
    if not matches:
        return [Line("body", (Span(text),))]
    lines = []
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        lines.append(Line("body", (Span(text[:matches[0].start()].strip()),)))
````

**with:**

````
def _spans(text: str, bold: bool = False) -> tuple[Span, ...]:
    """A dialogue part's text: bold and italic only (formatting.INLINE_ONLY);
    without a mark, one span as before."""
    if not fmt.has_marks(text, inline_only=True):
        return (Span(text, bold=bold),)
    return fmt.merge(Span(s.text, bold or s.bold, s.italic) for s in fmt.inline(text))


def formatted(text: str, style: Style = "body", *, bold: bool = False) -> list[Line]:
    """A box's text as printed lines (formatting spec). Without a mark, one
    line in `style`, as before. Otherwise one line per block: text in
    `style`; a heading as "heading1" or "heading2" (always bold); an item as
    "item" with its marker; `style` "center" (the announcements) keeps them
    centered: "center_heading1", "center_heading2", and an item as a centered
    line starting with its marker. `bold` makes every span bold (the Prayer of
    Confession, the Affirmation's own text)."""
    if not fmt.has_marks(text):
        return [Line(style, (Span(text, bold=bold),))]
    center = style == "center"
    lines = []
    for block in fmt.parse(text):
        if block.kind in ("heading1", "heading2"):
            spans = fmt.merge(Span(s.text, True, s.italic) for s in block.spans)
            lines.append(Line(f"center_{block.kind}" if center else block.kind, spans))
            continue
        spans = fmt.merge(Span(s.text, bold or s.bold, s.italic) for s in block.spans)
        if block.kind == "text":
            lines.append(Line(style, spans))
        elif center:
            lines.append(Line(style, fmt.merge((Span(f"{block.marker} ", bold=bold), *spans))))
        else:
            lines.append(Line("item", spans, marker=block.marker))
    return lines


def _leader_people(text: str) -> list[Line]:
    """worship_service._add_leader_people_paragraph's reading: Leader lines in
    normal type, People lines in bold, each with a hanging indent; bold and
    italic marks inside a part (formatting spec)."""
    matches = list(_PEOPLE_LEADER.finditer(text))
    if not matches:
        return [Line("body", _spans(text))]
    lines = []
    if matches[0].start() > 0 and text[:matches[0].start()].strip():
        lines.append(Line("body", _spans(text[:matches[0].start()].strip())))
````

**In `backend/printed_bulletin.py`, replace:**

````
            lines.append(Line("hanging", (Span("People: ", bold=True), Span(content, bold=True))))
        else:
            lines.append(Line("hanging", (Span("Leader: "), Span(content))))
````

**with:**

````
            lines.append(Line("hanging", (Span("People: ", bold=True), *_spans(content, bold=True))))
        else:
            lines.append(Line("hanging", (Span("Leader: "), *_spans(content))))
````

**In `backend/printed_bulletin.py`, replace:**

````
    lines = [Line("hanging", (Span("Leader: "), Span(leader)))] if leader else []
````

**with:**

````
    lines = [Line("hanging", (Span("Leader: "), *_spans(leader)))] if leader else []
````

**In `backend/printed_bulletin.py`, replace:**

````
    return [_element(s, key, label), Line(style, (Span(text, bold=style == "bold"),))]
````

**with:**

````
    return [_element(s, key, label), *formatted(text, style, bold=style == "bold")]
````

**In `backend/printed_bulletin.py`, replace:**

````
                lines.append(Line("body", (Span(element.text),)))
````

**with:**

````
                lines += formatted(element.text)
````

**In `backend/printed_bulletin.py`, replace:**

````
        return [_element(s, "affirmation_of_faith", "Affirmation of Faith:"), Line("bold", (Span(a.text, bold=True),))]
````

**with:**

````
        return [_element(s, "affirmation_of_faith", "Affirmation of Faith:"), *formatted(a.text, "bold", bold=True)]
````

**In `backend/printed_bulletin.py`, replace:**

````
            lines += [_section(title), Line("center", (Span(getattr(a, key)),))]
````

**with:**

````
            lines += [_section(title), *formatted(getattr(a, key), "center")]
````

**In `backend/printed_pdf.py`, replace:**

````
KEEP = {"section": 60.0, "element": 47.0}
````

**with:**

````
KEEP = {"section": 60.0, "element": 47.0, "heading1": 44.0, "heading2": 42.0}
````

**In `backend/printed_pdf.py`, replace:**

````
    "page": _style("page", alignment=TA_CENTER),
}
````

**with:**

````
    "page": _style("page", alignment=TA_CENTER),
    # Formatting (formatting spec): a box's own headings, under the element's
    # heading and never above it in weight, and its list items.
    "heading1": _style("heading1", fontSize=13, leading=16, spaceBefore=6),
    "heading2": _style("heading2", fontSize=12, leading=15, spaceBefore=6),
    "item": _style("item", leftIndent=18, bulletIndent=0, bulletFontName="Times-Roman", bulletFontSize=11),
    "center_heading1": _style("center_heading1", fontSize=13, leading=16, spaceBefore=6, alignment=TA_CENTER),
    "center_heading2": _style("center_heading2", fontSize=12, leading=15, spaceBefore=6, alignment=TA_CENTER),
}
````

**In `backend/printed_pdf.py`, replace:**

````
    paragraph = Paragraph(_markup(line), STYLES[line.style])
````

**with:**

````
    # An item's marker is "•" or a typed number (formatting.parse), never the user's other text.
    bullet = {"bulletText": to_pdf_text(line.marker)} if line.marker else {}
    paragraph = Paragraph(_markup(line), STYLES[line.style], **bullet)
````

**In `backend/printed_docx.py`, replace:**

````
          "contact": WD_ALIGN_PARAGRAPH.CENTER, "center": WD_ALIGN_PARAGRAPH.CENTER}
_SPACE_BEFORE = {"element": 8, "section": 12, "note": 10, "credit": 4, "center": 3}
_SIZE = {"title": 28, "credit": 9, "contact": 12}
````

**with:**

````
          "contact": WD_ALIGN_PARAGRAPH.CENTER, "center": WD_ALIGN_PARAGRAPH.CENTER,
          "center_heading1": WD_ALIGN_PARAGRAPH.CENTER, "center_heading2": WD_ALIGN_PARAGRAPH.CENTER}
_SPACE_BEFORE = {"element": 8, "section": 12, "note": 10, "credit": 4, "center": 3,
                 "heading1": 6, "heading2": 6, "center_heading1": 6, "center_heading2": 6}
_SIZE = {"title": 28, "credit": 9, "contact": 12,
         "heading1": 13, "heading2": 12, "center_heading1": 13, "center_heading2": 12}
# Formatting (formatting spec): a heading stays with what follows it; an item hangs after its marker.
_KEEP_WITH_NEXT = {"element", "heading1", "heading2", "center_heading1", "center_heading2"}
````

**In `backend/printed_docx.py`, replace:**

````
    if line.style == "element":
        fmt.keep_with_next = True
````

**with:**

````
    elif line.style == "item":
        fmt.left_indent, fmt.first_line_indent = Inches(0.25), Inches(-0.25)
    if line.style in _KEEP_WITH_NEXT:
        fmt.keep_with_next = True
    if line.marker:
        p.add_run(line.marker + "\t")       # Word's hanging indent is the tab's stop
````

**In `backend/worship_service.py`, replace:**

````

from affirmation import CHOICE_LABELS, Affirmation
````

**with:**

````

import formatting
from affirmation import CHOICE_LABELS, Affirmation
````

**In `backend/worship_service.py`, replace:**

````
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    Document = None
````

**with:**

````
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    Document = None


# A box's own headings (formatting spec): bold Times, these sizes, never Word's
# Heading styles (the section's own heading is Heading 2).
HEADING_POINTS = {"heading1": 13, "heading2": 12}


def _runs(p, text: str, *, bold: bool = False) -> None:
    """text as runs of p: bold and italic marks read (formatting.inline); text
    without a mark is one run, as add_paragraph(text) makes."""
    spans = formatting.inline(text) if formatting.has_marks(text, inline_only=True) else (formatting.Span(text),)
    for span in spans:
        run = p.add_run(span.text)
        if bold or span.bold:
            run.bold = True
        if span.italic:
            run.italic = True


def _add_text(doc, text: str, *, bold: bool = False) -> None:
    """A box's text (formatting spec). Without a mark, one paragraph exactly
    as before (its line breaks kept); otherwise a paragraph per block: a
    heading bold at HEADING_POINTS, kept with the next; an item with its
    marker and a 0.25 in hanging indent; text with its line breaks."""
    if not formatting.has_marks(text):
        if bold:
            doc.add_paragraph().add_run(text).bold = True
        else:
            doc.add_paragraph(text)
        return
    for block in formatting.parse(text):
        p = doc.add_paragraph()
        heading = block.kind in HEADING_POINTS
        if heading:
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.keep_with_next = True
        if block.kind == "item":
            p.paragraph_format.left_indent, p.paragraph_format.first_line_indent = Inches(0.25), Inches(-0.25)
            p.add_run(block.marker + "\t").bold = bold or None
        for span in block.spans:
            run = p.add_run(span.text)
            if bold or heading or span.bold:
                run.bold = True
            if span.italic:
                run.italic = True
            if heading:
                run.font.size = Pt(HEADING_POINTS[block.kind])
````

**In `backend/worship_service.py`, replace:**

````
    if not parts:
        doc.add_paragraph(text)
````

**with:**

````
    # Bold and italic marks read in each part (formatting spec; _runs: without one, as before).
    if not parts:
        _runs(doc.add_paragraph(), text)
````

**In `backend/worship_service.py`, replace:**

````
            r = p.add_run(content)
            r.bold = True
        else:
            line = ("Leader: " + content) if role == "Leader" else content
            if line:
                doc.add_paragraph(line)
````

**with:**

````
            _runs(p, content, bold=True)
        else:
            line = ("Leader: " + content) if role == "Leader" else content
            if line:
                _runs(doc.add_paragraph(), line)
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph("Leader: " + leader_clean)
````

**with:**

````
        _runs(doc.add_paragraph(), "Leader: " + leader_clean)
````

**In `backend/worship_service.py`, replace:**

````
                doc.add_paragraph(ce["text"])
````

**with:**

````
                _add_text(doc, ce["text"])
````

**In `backend/worship_service.py`, replace:**

````
    when switched off or own text is blank.
    Returns the .docx bytes.
````

**with:**

````
    when switched off or own text is blank.
    Each box's text reads the formatting marks (formatting spec, _add_text,
    _runs); text without a mark prints exactly as before.
    Returns the .docx bytes.
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph(liturgy["opening_prayer"])
````

**with:**

````
        _add_text(doc, liturgy["opening_prayer"])
````

**In `backend/worship_service.py`, replace:**

````
        p = doc.add_paragraph()
        p.add_run(liturgy["prayer_of_confession"]).bold = True
````

**with:**

````
        _add_text(doc, liturgy["prayer_of_confession"], bold=True)
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph(liturgy["prayer_for_illumination"])
````

**with:**

````
        _add_text(doc, liturgy["prayer_for_illumination"])
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph(faith.text if faith.choice == "own" else CHOICE_LABELS[faith.choice])
````

**with:**

````
        if faith.choice == "own":
            _add_text(doc, faith.text)
        else:
            doc.add_paragraph(CHOICE_LABELS[faith.choice])
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph(liturgy["prayers_of_the_people"])
````

**with:**

````
        _add_text(doc, liturgy["prayers_of_the_people"])
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph(liturgy["offertory_prayer"])
````

**with:**

````
        _add_text(doc, liturgy["offertory_prayer"])
````

**In `backend/worship_service.py`, replace:**

````
        doc.add_paragraph(liturgy["benediction"])
````

**with:**

````
        _add_text(doc, liturgy["benediction"])
````

**In `backend/usecases/liturgy_review.py`, replace:**

````
    "(Leader/People lines where present) and about the same length. Output only the revised text."
````

**with:**

````
    "(Leader/People lines where present) and about the same length. Keep any formatting marks the draft "
    "has (**bold**, *italic*, lines starting # or ## for headings, - or 1. for lists) where they still fit, "
    "and add none. Output only the revised text."
````

**In `backend/api/routes/liturgy_review.py`, replace:**

````

The rubric, the system prompt and the voice profile are read on the server,
````

**with:**

````

The reviewer and the pews read each card's words as printed, without
formatting marks (formatting spec, "AI interplay"; `_cards`); Revise gets
the text as typed, marks and all.

The rubric, the system prompt and the voice profile are read on the server,
````

**In `backend/api/routes/liturgy_review.py`, replace:**

````

from api import ratelimit
````

**with:**

````

import formatting
from api import ratelimit
````

**In `backend/api/routes/liturgy_review.py`, replace:**

````

def _note(note) -> NoteOut:
````

**with:**

````

def _cards(payload: "ReviewIn") -> list[liturgy_review.ReviewCard]:
    return [liturgy_review.ReviewCard(c.section, c.origin,
                                      formatting.plain(c.text, inline_only=c.section in formatting.INLINE_ONLY))
            for c in payload.cards]


def _note(note) -> NoteOut:
````

**In `backend/api/routes/liturgy_review.py`, replace:**

````
    outcome = liturgy_review.review_service(
        church_id=church.id, user_id=user.id, occasion=payload.occasion, scriptures=payload.scriptures,
        cards=[liturgy_review.ReviewCard(c.section, c.origin, c.text) for c in payload.cards],
        sermon=_sermon(payload.sermon_text),
        charge=lambda n: ratelimit.consume("ai", user_id=user.id, church_id=church.id, cost=n))
    return ReviewOut(cards=[CardNotesOut(section=c.section, notes=[_note(n) for n in c.notes])
````

**with:**

````
    outcome = liturgy_review.review_service(
        church_id=church.id, user_id=user.id, occasion=payload.occasion, scriptures=payload.scriptures,
        cards=_cards(payload), sermon=_sermon(payload.sermon_text),
        charge=lambda n: ratelimit.consume("ai", user_id=user.id, church_id=church.id, cost=n))
    return ReviewOut(cards=[CardNotesOut(section=c.section, notes=[_note(n) for n in c.notes])
````

**In `backend/api/routes/liturgy_review.py`, replace:**

````
        cards=[liturgy_review.ReviewCard(c.section, c.origin, c.text) for c in payload.cards],
        sermon=_sermon(payload.sermon_text),
````

**with:**

````
        cards=_cards(payload), sermon=_sermon(payload.sermon_text),
````

**In `backend/tests/fixtures/README.md`, replace:**

````
- `shared/scripture_refs.json` is hand-written, not recorded, so it has no `.meta.json` sidecar. It is the authority for `backend/scripture_refs.py` and for 2b's `frontend/src/lib/scripture-refs.ts`: change a case here first, then both ports. `backend/tests/test_scripture_refs.py` runs it in pytest; 2b's `lib/scripture-refs.test.ts` reads it with `fs` from `../backend/tests/fixtures/shared/`. The top-level `"_about"` key documents each section's encoding. Slice 5a adds its `doc_readings` cases to the `resolve_readings` section.

````

**with:**

````
- `shared/scripture_refs.json` is hand-written, not recorded, so it has no `.meta.json` sidecar. It is the authority for `backend/scripture_refs.py` and for 2b's `frontend/src/lib/scripture-refs.ts`: change a case here first, then both ports. `backend/tests/test_scripture_refs.py` runs it in pytest; 2b's `lib/scripture-refs.test.ts` reads it with `fs` from `../backend/tests/fixtures/shared/`. The top-level `"_about"` key documents each section's encoding. Slice 5a adds its `doc_readings` cases to the `resolve_readings` section.
- `shared/formatting.json` is hand-written too (formatting spec, 2026-10-25): each case is a box's text and the lines the printed bulletin prints for it. It is the authority for `backend/formatting.py` with `backend/printed_bulletin.py` and for `frontend/src/lib/formatting.ts` (the Review step's preview): change a case here first, then both. `backend/tests/test_formatting.py` and `frontend/src/lib/formatting.test.ts` run every case.

````
<!-- /directives -->

- [ ] **Step 4: Run them and the suite**

Run: the Step 2 command, then `.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1`
**Expected:** @@T1_PASS@@, then `2367 passed, 50 skipped in <t>s`.

- [ ] **Step 5: Commit and push**

```bash
git add backend/formatting.py backend/tests/test_formatting.py backend/tests/fixtures/shared/formatting.json backend/printed_bulletin.py backend/printed_pdf.py backend/printed_docx.py backend/worship_service.py backend/usecases/liturgy_review.py backend/api/routes/liturgy_review.py backend/tests/fixtures/README.md backend/tests/test_no_streamlit_in_core.py backend/tests/test_usecase_liturgy_revise.py
git commit -q -m "Formatting: the grammar and what prints" -m "backend/formatting.py reads bold, italic, two headings and lists (formatting spec); the Word copy, the printed bulletin (PDF and Word) and so the email's attachments print them, and text without a mark prints exactly as before. The reviewer and the pews read the words without the marks; Revise keeps them. shared/formatting.json is the printed bulletin's output for 26 cases." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

### Task 2: The help line and the Review preview (S "The Review preview", "Help copy")

**Files:** Create `frontend/src/lib/formatting.ts`, `frontend/src/lib/formatting.test.ts`, `frontend/src/components/builder/formatting-help.tsx`, `frontend/src/components/builder/formatting-help.test.tsx`, `frontend/src/components/builder/review/text-preview-card.tsx`, `frontend/src/components/builder/review/text-preview-card.test.tsx`. Modify `frontend/src/components/builder/liturgy/section-card.tsx`, `custom-element-card.tsx`, `affirmation-card.tsx`, `frontend/src/components/builder/bulletin/bulletin-step.tsx`, `frontend/src/components/builder/review/review-send-step.tsx`, and the tests `affirmation-card.test.tsx`, `liturgy-step.test.tsx`, `review-step.test.tsx`, `review-send-step.test.tsx` (each box's description now ends with the help line; the Review step's headings add "Text preview").

- [ ] **Step 1: Write the failing tests**

<!-- directives:T2_TESTS -->
**Create `frontend/src/lib/formatting.test.ts`:**

````
/**
 * The preview's copy of the print rules (formatting spec, Testing): every case of
 * backend/tests/fixtures/shared/formatting.json, which backend/tests/test_formatting.py
 * checks against the printed bulletin itself, so the preview shows what prints.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { hasMarks, parse, printedLines, type BoxKind, type PrintedLine } from "./formatting";

type Case = { name: string; box: BoxKind; text: string; lines: { style: string; marker: string; spans: [string, string][] }[] };
const fixture = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/formatting.json", import.meta.url), "utf-8"),
) as { assurance_response: string; cases: Case[] };

const asFixture = (line: PrintedLine) => ({
  style: line.style,
  marker: line.marker,
  spans: line.spans.map((s) => [s.text, `${s.bold ? "b" : ""}${s.italic ? "i" : ""}`]),
});

describe("formatting (shared/formatting.json)", () => {
  it("prints every case as the printed bulletin does", () => {
    expect(fixture.cases).toHaveLength(26);
    for (const c of fixture.cases) {
      expect(printedLines(c.box, c.text, fixture.assurance_response).map(asFixture), c.name).toEqual(c.lines);
    }
  });

  it("finds no mark in text saved before formatting", () => {
    for (const text of ["Psalm 23:1*", "#1 hymn", "5 * 3 * 2", "2*3*4", "A lone ** pair", "a**b**c", "### three\n-x\n1) one", "* star"]) {
      expect(hasMarks(text), text).toBe(false);
    }
    expect(hasMarks("**b**")).toBe(true);
    expect(hasMarks("- item")).toBe(true);
    expect(hasMarks("- item", true)).toBe(false);
  });

  it("keeps what is typed as text, never markup", () => {
    const [block] = parse("<img src=x onerror=alert(1)> **<b>x</b>**");
    expect(block.spans).toEqual([
      { text: "<img src=x onerror=alert(1)> ", bold: false, italic: false },
      { text: "<b>x</b>", bold: true, italic: false },
    ]);
  });

  it("reads a long text of unclosed marks quickly", () => {
    const started = Date.now();
    for (const text of ["*a ".repeat(6666), "**a ".repeat(5000), "*".repeat(20_000)]) parse(text);
    expect(Date.now() - started).toBeLessThan(1000);
  });
});
````

**Create `frontend/src/components/builder/formatting-help.test.tsx`:**

````
/**
 * The "Formatting help" line under each text box (formatting spec, "Help
 * copy"; owner decision 4), as each box's description: the prayer cards (bold
 * and italic only in the two dialogue cards), a custom element, the
 * Affirmation's own text and the four free-text announcements; never a name
 * box. In the real builder layout against the fake API.
 */
import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import BulletinStepPage from "@/app/(signed-in)/(church)/builder/bulletin/page";
import { LiturgyStep } from "@/components/builder/liturgy/liturgy-step";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi } from "@/test/fake-api";
import {
  bulletinSettings,
  church,
  churchProfile,
  DRAFT_NOW,
  filledBulletinSettings,
  gmailConnection,
  lectionaryRoute,
  liturgyConfig,
  me,
  previousBulletin,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { DIALOGUE_HELP, FORMATTING_HELP } from "./formatting-help";

const KEY = draftKey(USER_ID, church().id);

function render(page: "liturgy" | "bulletin", draft: DraftV1) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": page === "bulletin" ? filledBulletinSettings() : bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
  });
  return renderWithProviders(<BuilderLayout>{page === "liturgy" ? <LiturgyStep /> : <BulletinStepPage />}</BuilderLayout>, {
    me: me(),
    church: church(),
    path: `/builder/${page}`,
  });
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

describe("the formatting help line (formatting spec)", () => {
  it("is in each box's description on the Liturgy step, bold and italic only for the dialogue cards", async () => {
    const draft = testDraft();
    draft.liturgy.custom_elements = [{ id: "c1", label: "Anthem", text: "", insert_after: "sermon" }];
    draft.liturgy.affirmation = { include: true, choice: "own", text: "We trust.", origin: "user" };
    render("liturgy", draft);
    const prayer = await screen.findByRole("textbox", { name: "Opening Prayer" });
    expect(prayer).toHaveAccessibleDescription(expect.stringContaining(FORMATTING_HELP));
    for (const name of ["Call to Worship", "Assurance of Pardon"]) {
      const box = screen.getByRole("textbox", { name });
      expect(box).toHaveAccessibleDescription(expect.stringContaining(DIALOGUE_HELP));
      expect(box).not.toHaveAccessibleDescription(expect.stringContaining(FORMATTING_HELP));
    }
    expect(screen.getByRole("textbox", { name: "Text" })).toHaveAccessibleDescription(FORMATTING_HELP);
    expect(screen.getByRole("textbox", { name: "Your own text" })).toHaveAccessibleDescription(
      expect.stringContaining(FORMATTING_HELP),
    );
  });

  it("is under the free-text announcements, not the names", async () => {
    render("bulletin", testDraft());
    for (const name of ["This week's activities", "Prayers and concerns", "Items for collection", "Other announcements"]) {
      expect(await screen.findByRole("textbox", { name })).toHaveAccessibleDescription(FORMATTING_HELP);
    }
    expect(screen.getByRole("textbox", { name: "Ushers and counters" })).not.toHaveAccessibleDescription(
      expect.stringContaining("Formatting"),
    );
  });

  it("names the marks without an em dash", () => {
    for (const copy of [FORMATTING_HELP, DIALOGUE_HELP]) expect(copy).not.toContain("—");
    expect(FORMATTING_HELP).toContain("**bold**");
    expect(FORMATTING_HELP).toContain("# Heading");
  });
});
````

**Create `frontend/src/components/builder/review/text-preview-card.test.tsx`:**

````
/**
 * The Review step's text preview (formatting spec, "The Review preview"):
 * closed at first; open, each box with text as the printed bulletin prints it
 * (the rules shared/formatting.json pins for both sides), what is typed always
 * shown as text, a 44 px toggle and no em dash. In the real builder layout
 * against the fake API.
 */
import { screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { draftKey, type DraftV1 } from "@/lib/draft/schema";
import { installFakeApi } from "@/test/fake-api";
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

import { PREVIEW_EMPTY, PREVIEW_INTRO, PREVIEW_TITLE, TextPreviewCard } from "./text-preview-card";

const KEY = draftKey(USER_ID, church().id);

function render(draft: DraftV1) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "GET /church/bulletin-settings": bulletinSettings(),
    "GET /services/previous-bulletin": previousBulletin(),
    "GET /gmail-connection": gmailConnection(),
  });
  return renderWithProviders(
    <BuilderLayout>
      <TextPreviewCard />
    </BuilderLayout>,
    { me: me(), church: church(), path: "/builder/review" },
  );
}

function filled(): DraftV1 {
  const draft = testDraft();
  const cards = draft.liturgy.cards;
  const set = (key: keyof typeof cards, text: string) => (cards[key] = { ...cards[key], enabled: true, text, origin: "typed" });
  set("opening_prayer", "# For the world\nWe pray for **peace** and *justice*.\n- the sick\n12. the lonely");
  set("call_to_worship", "Leader: Come.\nPeople: We come *gladly*.");
  set("assurance", "Leader: In Christ we are forgiven.");
  set("offertory_prayer", "<img src=x onerror=alert(1)> **<b>bold</b>**");
  set("benediction", "   ");
  draft.liturgy.custom_elements = [{ id: "c1", label: "Anthem", text: "Sung by the *choir*", insert_after: "sermon" }];
  draft.bulletin.announcements.other = "# This week\n- Choir";
  return draft;
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

async function open(draft: DraftV1) {
  const { user } = render(draft);
  const card = await screen.findByRole("region", { name: PREVIEW_TITLE });
  expect(within(card).getByText(PREVIEW_INTRO)).toBeInTheDocument();
  const toggle = within(card).getByRole("button", { name: "Show text preview" });
  expect(toggle).toHaveClass("min-h-11"); // 44 px on a phone
  expect(within(card).queryByRole("region", { name: "Opening Prayer" })).toBeNull();
  await user.click(toggle);
  return card;
}

const style = (element: HTMLElement) => element.closest("p")?.getAttribute("data-style");

describe("the text preview (formatting spec)", () => {
  it("shows each box as it prints: headings, bold, italic, lists, People lines and the fixed response", async () => {
    const card = await open(filled());
    const prayer = within(card).getByRole("region", { name: "Opening Prayer" });
    expect(style(within(prayer).getByText("For the world"))).toBe("heading1");
    expect(within(prayer).getByText("peace")).toHaveClass("font-bold");
    expect(within(prayer).getByText("justice")).toHaveClass("italic");
    expect(style(within(prayer).getByText("the sick"))).toBe("item");
    expect(within(prayer).getByText("•")).toBeInTheDocument();
    expect(within(prayer).getByText("12.")).toBeInTheDocument();
    const call = within(card).getByRole("region", { name: "Call to Worship" });
    expect(within(call).getByText("People:", { exact: false })).toHaveClass("font-bold");
    expect(within(call).getByText("gladly")).toHaveClass("font-bold", "italic");
    const assurance = within(card).getByRole("region", { name: "Assurance of Pardon" });
    expect(within(assurance).getByText("People: Thanks be to God! Amen.")).toHaveClass("font-bold");
    expect(within(within(card).getByRole("region", { name: "Anthem" })).getByText("choir")).toHaveClass("italic");
    const other = within(card).getByRole("region", { name: "Other announcements" });
    expect(style(within(other).getByText("This week"))).toBe("center_heading1");
    expect(within(card).queryByRole("region", { name: "Benediction" })).toBeNull(); // blank: nothing prints
    expect(card.textContent).not.toContain("—");
  });

  it("shows what is typed as text, never as markup", async () => {
    const card = await open(filled());
    const offertory = within(card).getByRole("region", { name: "Offertory Prayer" });
    expect(within(offertory).getByText("<img src=x onerror=alert(1)>", { exact: false })).toBeInTheDocument();
    expect(within(offertory).getByText("<b>bold</b>")).toHaveClass("font-bold");
    expect(card.querySelector("img, b, script")).toBeNull();
  });

  it("says so when no box has text", async () => {
    const draft = testDraft();
    for (const card of Object.values(draft.liturgy.cards)) Object.assign(card, { text: "", origin: "typed" });
    const card = await open(draft);
    expect(within(card).getByText(PREVIEW_EMPTY)).toBeInTheDocument();
  });
});
````

**In `frontend/src/components/builder/liturgy/affirmation-card.test.tsx`, replace:**

````
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
````

**with:**

````
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { FORMATTING_HELP } from "@/components/builder/formatting-help";
import { Toaster } from "@/components/ui/sonner";
````

**In `frontend/src/components/builder/liturgy/affirmation-card.test.tsx`, replace:**

````
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} ${OWN_TEXT_BLANK}`);
    expect(box).toHaveAttribute("maxlength", "20000");
    await user.type(box, OWN);
    expect(box).toHaveAccessibleDescription(OWN_TEXT_HINT);
````

**with:**

````
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} ${OWN_TEXT_BLANK} ${FORMATTING_HELP}`);
    expect(box).toHaveAttribute("maxlength", "20000");
    await user.type(box, OWN);
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} ${FORMATTING_HELP}`);
````

**In `frontend/src/components/builder/liturgy/affirmation-card.test.tsx`, replace:**

````
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} 18,001 / 20,000`);
````

**with:**

````
    expect(box).toHaveAccessibleDescription(`${OWN_TEXT_HINT} 18,001 / 20,000 ${FORMATTING_HELP}`);
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
````

**with:**

````
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { DIALOGUE_HELP } from "@/components/builder/formatting-help";
import ReviewStepPage from "@/app/(signed-in)/(church)/builder/review/page";
````

**In `frontend/src/components/builder/liturgy/liturgy-step.test.tsx`, replace:**

````
    // The hints are the fields' descriptions.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveAccessibleDescription(
      "Start lines with “Leader:” or “People:”. People lines print in bold.",
    );
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveAccessibleDescription(
      "People: Thanks be to God! Amen. Added automatically after your text.",
````

**with:**

````
    // The hints, then the formatting help (formatting spec), are the fields' descriptions.
    expect(screen.getByRole("textbox", { name: "Call to Worship" })).toHaveAccessibleDescription(
      `Start lines with “Leader:” or “People:”. People lines print in bold. ${DIALOGUE_HELP}`,
    );
    expect(screen.getByRole("textbox", { name: "Assurance of Pardon" })).toHaveAccessibleDescription(
      `People: Thanks be to God! Amen. Added automatically after your text. ${DIALOGUE_HELP}`,
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
````

**with:**

````
import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { FORMATTING_HELP } from "@/components/builder/formatting-help";
import { Toaster } from "@/components/ui/sonner";
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````
      "Your church's default benediction. Admins can change it in Settings.",
````

**with:**

````
      `Your church's default benediction. Admins can change it in Settings. ${FORMATTING_HELP}`,
````

**In `frontend/src/components/builder/review/review-send-step.test.tsx`, replace:**

````
      "Archive",
      "Word documents",
````

**with:**

````
      "Archive",
      "Text preview",
      "Word documents",
````
<!-- /directives -->

- [ ] **Step 2: Run them and see them fail**

Run: `(cd frontend && npx vitest run src/lib/formatting.test.ts src/components/builder/formatting-help.test.tsx src/components/builder/review/text-preview-card.test.tsx src/components/builder/liturgy/affirmation-card.test.tsx src/components/builder/liturgy/liturgy-step.test.tsx src/components/builder/liturgy/review-step.test.tsx src/components/builder/review/review-send-step.test.tsx 2>&1 | grep -E "Test Files|Tests ")`
**Expected:** @@T2_FAIL@@

- [ ] **Step 3: Write the mirror, the help line and the preview**

<!-- directives:T2_CODE -->
**Create `frontend/src/lib/formatting.ts`:**

````
/**
 * Text formatting (formatting spec, 2026-10-25; owner decisions 3 to 5): the
 * TypeScript copy of backend/formatting.py and of how backend/printed_bulletin.py
 * prints a box's text (`formatted`, `_leader_people`, `_assurance`), for the
 * Review step's preview. `formatting.test.ts` pins both to
 * backend/tests/fixtures/shared/formatting.json, which the backend passes too.
 * Pure: the preview draws these lines as React text, never as HTML.
 */

export type Span = { text: string; bold: boolean; italic: boolean };
export type LineStyle = "body" | "bold" | "hanging" | "center" | "heading1" | "heading2" | "item" | "center_heading1" | "center_heading2";
export type PrintedLine = { style: LineStyle; spans: Span[]; marker: string };
/** Which printed rule a box follows: a prayer, the all-bold Prayer of Confession (and own Affirmation text), the
 * Call to Worship's Leader and People lines, the Assurance with its fixed response, a centered announcement. */
export type BoxKind = "prayer" | "confession" | "dialogue" | "assurance" | "announcement";

type Kind = "text" | "heading1" | "heading2" | "item";
type Block = { kind: Kind; spans: Span[]; marker: string };

export const BULLET = "•";
const ESCAPABLE = "*#-.";
const SPACE = " \t ";
const ALNUM = /^[A-Za-z0-9]$/;
// [\s\S], not ".": Python's "." takes every character but "\n", and a line has none.
const HEADING = /^(#{1,2}) ([\s\S]*)$/;
const BULLET_LINE = /^- ([\s\S]*)$/;
const NUMBER = /^([0-9]{1,3}\.) ([\s\S]*)$/;

const span = (text: string, bold = false, italic = false): Span => ({ text, bold, italic });
const isSpace = (ch: string) => ch !== "" && SPACE.includes(ch);
const isAlnum = (ch: string) => ALNUM.test(ch);
const strip = (s: string) => {
  let a = 0;
  let b = s.length;
  while (a < b && isSpace(s[a])) a++;
  while (b > a && isSpace(s[b - 1])) b--;
  return s.slice(a, b);
};

type Token = { kind: "esc" | "**" | "*" | "ch"; start: number; end: number };

function tokens(line: string): Token[] {
  const out: Token[] = [];
  let i = 0;
  while (i < line.length) {
    let kind: Token["kind"] = "ch";
    let width = 1;
    if (line[i] === "\\" && i + 1 < line.length && ESCAPABLE.includes(line[i + 1])) [kind, width] = ["esc", 2];
    else if (line.startsWith("**", i)) [kind, width] = ["**", 2];
    else if (line[i] === "*") kind = "*";
    out.push({ kind, start: i, end: i + width });
    i += width;
  }
  return out;
}

function inlineLine(line: string): Span[] {
  const toks = tokens(line);
  const n = toks.length;
  const before = (t: Token) => (t.start > 0 ? line[t.start - 1] : "");
  const after = (t: Token) => (t.end < line.length ? line[t.end] : "");
  const mark = (t: Token) => t.kind === "*" || t.kind === "**";
  const opens = toks.map((t) => mark(t) && after(t) !== "" && !isSpace(after(t)) && !isAlnum(before(t)));
  const closes = toks.map((t) => mark(t) && !isSpace(before(t)) && !isAlnum(after(t)));
  const next = (kind: "*" | "**") => {
    const table = new Array<number>(n + 1).fill(n);
    for (let i = n - 1; i >= 0; i--) table[i] = toks[i].kind === kind && closes[i] ? i : table[i + 1];
    return table;
  };
  const nxt = { "*": next("*"), "**": next("**") };

  function walk(lo: number, hi: number, bold: boolean, italic: boolean): Span[] {
    const out: Span[] = [];
    let buf = "";
    let i = lo;
    while (i < hi) {
      const t = toks[i];
      if (t.kind === "esc") {
        buf += line[t.start + 1];
        i++;
        continue;
      }
      if ((t.kind === "*" || t.kind === "**") && opens[i] && !(t.kind === "**" ? bold : italic)) {
        const j = i + 2 <= n ? nxt[t.kind][i + 2] : n; // at least one token inside
        if (j < hi) {
          if (buf) out.push(span(buf, bold, italic));
          buf = "";
          out.push(...walk(i + 1, j, bold || t.kind === "**", italic || t.kind === "*"));
          i = j + 1;
          continue;
        }
      }
      buf += line.slice(t.start, t.end);
      i++;
    }
    if (buf) out.push(span(buf, bold, italic));
    return out;
  }

  return walk(0, n, false, false);
}

/** Spans with neighbours of the same type joined, empty ones dropped (`formatting.merge`). */
export function merge(spans: Iterable<Span>): Span[] {
  const out: Span[] = [];
  for (const s of spans) {
    if (!s.text) continue;
    const last = out[out.length - 1];
    if (last && last.bold === s.bold && last.italic === s.italic) out[out.length - 1] = span(last.text + s.text, s.bold, s.italic);
    else out.push(s);
  }
  return out;
}

/** Bold and italic, line by line (`formatting.inline`). */
export function inline(text: string): Span[] {
  const spans: Span[] = [];
  text.split("\n").forEach((line, n) => {
    if (n) spans.push(span("\n"));
    spans.push(...inlineLine(line));
  });
  return merge(spans);
}

function blockOf(line: string): { kind: Kind; content: string; marker: string } | null {
  const heading = HEADING.exec(line);
  if (heading) {
    const content = strip(heading[2]);
    return content ? { kind: heading[1] === "#" ? "heading1" : "heading2", content, marker: "" } : null;
  }
  const bullet = BULLET_LINE.exec(line);
  if (bullet) {
    const content = strip(bullet[1]);
    return content ? { kind: "item", content, marker: BULLET } : null;
  }
  const number = NUMBER.exec(line);
  if (number) {
    const content = strip(number[2]);
    return content ? { kind: "item", content, marker: number[1] } : null;
  }
  return null;
}

/** The text as printed blocks (`formatting.parse`). */
export function parse(text: string, inlineOnly = false): Block[] {
  if (inlineOnly) return text ? [{ kind: "text", spans: inline(text), marker: "" }] : [];
  const blocks: Block[] = [];
  let lines: string[] = [];
  const flush = () => {
    while (lines.length && !strip(lines[0])) lines.shift();
    while (lines.length && !strip(lines[lines.length - 1])) lines.pop();
    if (lines.length) blocks.push({ kind: "text", spans: inline(lines.join("\n")), marker: "" });
    lines = [];
  };
  for (const line of text.split("\n")) {
    const found = blockOf(line);
    if (found === null) {
      lines.push(line);
      continue;
    }
    flush();
    blocks.push({ kind: found.kind, spans: inline(found.content), marker: found.marker });
  }
  flush();
  return blocks;
}

/** Whether any mark is in `text` (`formatting.has_marks`); without one it prints exactly as before. */
export function hasMarks(text: string, inlineOnly = false): boolean {
  return text.split("\n").some((line) => {
    if (!inlineOnly && blockOf(line) !== null) return true;
    if (!line) return false;
    const spans = inline(line);
    return !(spans.length === 1 && spans[0].text === line && !spans[0].bold && !spans[0].italic);
  });
}

// --- How printed_bulletin prints a box ---

/** Python's `str.isspace` characters, so `pyStrip` trims as `str.strip()` does. */
const PY_SPACE = "\t\n\u000b\u000c\r\u001c\u001d\u001e\u001f \u0085                 　";
const PY_SPACE_CLASS = "[\\t\\n\\u000b\\u000c\\r\\u001c-\\u001f \\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]";
function pyStrip(s: string): string {
  let a = 0;
  let b = s.length;
  while (a < b && PY_SPACE.includes(s[a])) a++;
  while (b > a && PY_SPACE.includes(s[b - 1])) b--;
  return s.slice(a, b);
}
// printed_bulletin._PEOPLE_LEADER (`\b(Leader|People):\s*`, ignoring case; Python's \w is a letter, a digit
// or "_") and _ASSURANCE_PEOPLE (a "People:" at the start or after a space). No lookbehind: older Safari has none.
const PEOPLE_LEADER = new RegExp(`(Leader|People):${PY_SPACE_CLASS}*`, "giu");
const WORD = /^[\p{L}\p{N}_]$/u;

function labels(text: string): { index: number; end: number; role: string }[] {
  return [...text.matchAll(PEOPLE_LEADER)]
    .filter((m) => m.index === 0 || !WORD.test(text[m.index - 1]))
    .map((m) => ({ index: m.index, end: m.index + m[0].length, role: m[1].toLowerCase() }));
}

function typedPeople(text: string): number {
  for (const m of text.matchAll(/People:/giu)) if (m.index === 0 || PY_SPACE.includes(text[m.index - 1])) return m.index;
  return -1;
}

const line = (style: LineStyle, spans: Span[], marker = ""): PrintedLine => ({ style, spans, marker });

/** printed_bulletin._spans: a dialogue part, bold and italic only. */
function dialogueSpans(text: string, bold = false): Span[] {
  if (!hasMarks(text, true)) return [span(text, bold)];
  return merge(inline(text).map((s) => span(s.text, bold || s.bold, s.italic)));
}

/** printed_bulletin.formatted. */
function formatted(text: string, style: LineStyle, bold = false): PrintedLine[] {
  if (!hasMarks(text)) return [line(style, [span(text, bold)])];
  const center = style === "center";
  return parse(text).map((block) => {
    if (block.kind === "heading1" || block.kind === "heading2") {
      const spans = merge(block.spans.map((s) => span(s.text, true, s.italic)));
      return line(center ? (`center_${block.kind}` as LineStyle) : block.kind, spans);
    }
    const spans = merge(block.spans.map((s) => span(s.text, bold || s.bold, s.italic)));
    if (block.kind === "text") return line(style, spans);
    if (center) return line(style, merge([span(`${block.marker} `, bold), ...spans]));
    return line("item", spans, block.marker);
  });
}

/** printed_bulletin._leader_people. */
function leaderPeople(text: string): PrintedLine[] {
  const matches = labels(text);
  if (!matches.length) return [line("body", dialogueSpans(text))];
  const lines: PrintedLine[] = [];
  const first = matches[0].index;
  if (first > 0 && pyStrip(text.slice(0, first))) lines.push(line("body", dialogueSpans(pyStrip(text.slice(0, first)))));
  matches.forEach((m, i) => {
    const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
    const content = pyStrip(text.slice(m.end, end));
    if (m.role === "people") lines.push(line("hanging", [span("People: ", true), ...dialogueSpans(content, true)]));
    else lines.push(line("hanging", [span("Leader: "), ...dialogueSpans(content)]));
  });
  return lines;
}

/** printed_bulletin._assurance. */
function assurance(text: string, response: string): PrintedLine[] {
  let leader = pyStrip(text);
  const people = typedPeople(leader);
  if (people >= 0) leader = pyStrip(leader.slice(0, people));
  if (leader.startsWith("Leader:")) leader = pyStrip(leader.slice(7));
  const lines = leader ? [line("hanging", [span("Leader: "), ...dialogueSpans(leader)])] : [];
  return [...lines, line("bold", [span(response, true)])];
}

/** A box's text as the printed bulletin prints it. `response` is the Assurance's fixed response
 * (`GET /liturgy/config`'s `assurance_response`). */
export function printedLines(box: BoxKind, text: string, response = ""): PrintedLine[] {
  switch (box) {
    case "prayer":
      return formatted(text, "body");
    case "confession":
      return formatted(text, "bold", true);
    case "dialogue":
      return leaderPeople(text);
    case "assurance":
      return assurance(text, response);
    case "announcement":
      return formatted(text, "center");
  }
}

/** The two dialogue boxes (`formatting.INLINE_ONLY`): bold and italic only, so Leader and People lines read as today. */
export const INLINE_ONLY: ReadonlySet<string> = new Set(["call_to_worship", "assurance"]);

/** Trims as the server's `str.strip()` does before printing (`usecases.archive`). */
export const serverStrip = pyStrip;
````

**Create `frontend/src/components/builder/formatting-help.tsx`:**

````
/**
 * The "Formatting help" line under a text box (formatting spec, "Help copy";
 * owner decision 4): the marks the box takes and where to see them. The two
 * dialogue boxes (the Call to Worship and the Assurance of Pardon) take bold
 * and italic only.
 */
export const FORMATTING_HELP = "Formatting: **bold**, *italic*, # Heading, ## Smaller heading, - or 1. for a list. Preview on the Review step.";
export const DIALOGUE_HELP = "Formatting: **bold**, *italic*. Preview on the Review step.";

export function FormattingHelp({ id, dialogue = false }: { id: string; dialogue?: boolean }) {
  return (
    <p id={id} className="text-sm text-muted-foreground">
      {dialogue ? DIALOGUE_HELP : FORMATTING_HELP}
    </p>
  );
}
````

**Create `frontend/src/components/builder/review/text-preview-card.tsx`:**

````
"use client";

import { ChevronDownIcon } from "lucide-react";
import { useState } from "react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useDraft } from "@/lib/draft/context";
import { SECTION_KEYS, type DraftV1 } from "@/lib/draft/schema";
import { printedLines, serverStrip, type BoxKind, type PrintedLine } from "@/lib/formatting";
import { SECTION_LABELS } from "@/lib/liturgy/sections";
import { useLiturgyConfig } from "@/lib/queries/liturgy";
import { cn } from "@/lib/utils";

export const PREVIEW_TITLE = "Text preview";
export const PREVIEW_INTRO = "Your text as the bulletin prints it, with its bold, italic, headings and lists.";
export const PREVIEW_EMPTY = "No text to preview yet.";
const PASTORS_COPY = "Prayers of the People (pastor's copy)";

/** The free-text announcements, in the printed order, with their printed headings' words. */
const ANNOUNCEMENT_BOXES = [
  ["activities", "This week's activities"],
  ["prayer_concerns", "Prayers and concerns"],
  ["collection", "Items for collection"],
  ["other", "Other announcements"],
] as const;

export type PreviewBox = { id: string; label: string; box: BoxKind; text: string };

const SECTION_BOX: Partial<Record<string, BoxKind>> = {
  call_to_worship: "dialogue",
  assurance: "assurance",
  prayer_of_confession: "confession",
};

/** Every box that prints text, as the server receives it (trimmed): the prayers in service order, the
 * Affirmation's own text, the custom elements, then the announcements. */
export function previewBoxes(draft: DraftV1): PreviewBox[] {
  const boxes: PreviewBox[] = [];
  const add = (id: string, label: string, box: BoxKind, raw: string) => {
    const text = serverStrip(raw);
    if (text) boxes.push({ id, label, box, text });
  };
  for (const key of SECTION_KEYS) {
    const card = draft.liturgy.cards[key];
    if (!card.enabled) continue;
    add(key, key === "prayers_of_the_people" ? PASTORS_COPY : SECTION_LABELS[key], SECTION_BOX[key] ?? "prayer", card.text);
  }
  const a = draft.liturgy.affirmation;
  if (a.include && a.choice === "own") add("affirmation", "Affirmation of Faith", "confession", a.text);
  for (const element of draft.liturgy.custom_elements) {
    if (serverStrip(element.label)) add(`custom-${element.id}`, serverStrip(element.label), "prayer", element.text);
  }
  for (const [key, label] of ANNOUNCEMENT_BOXES) add(key, label, "announcement", draft.bulletin.announcements[key]);
  return boxes;
}

const LINE_CLASS: Record<PrintedLine["style"], string> = {
  body: "",
  bold: "",
  hanging: "pl-8 -indent-8",
  center: "text-center",
  heading1: "pt-1 text-lg",
  heading2: "pt-1 text-base",
  item: "grid grid-cols-[2rem_1fr]",
  center_heading1: "pt-1 text-center text-lg",
  center_heading2: "pt-1 text-center text-base",
};

/** One box's printed lines, as React text (never HTML): a span's bold and italic, a line's style. */
export function PrintedText({ lines }: { lines: PrintedLine[] }) {
  return (
    <div className="grid gap-1 font-serif text-sm whitespace-pre-line wrap-anywhere">
      {lines.map((line, n) => {
        const spans = line.spans.map((s, i) => (
          <span key={i} className={cn(s.bold && "font-bold", s.italic && "italic")}>
            {s.text}
          </span>
        ));
        return (
          <p key={n} data-style={line.style} className={LINE_CLASS[line.style]}>
            {line.marker ? (
              <>
                <span>{line.marker}</span>
                <span>{spans}</span>
              </>
            ) : (
              spans
            )}
          </p>
        );
      })}
    </div>
  );
}

/**
 * The Review step's text preview (formatting spec, "The Review preview"; owner
 * decision 4): closed at first; open, each box with text as the printed
 * bulletin prints it (the rules of shared/formatting.json): the prayers, the
 * Affirmation's own text, the custom elements and the announcements. The
 * Prayers of the People print only in the pastor's Word copy, as a prayer.
 */
export function TextPreviewCard() {
  const { draft } = useDraft();
  const config = useLiturgyConfig();
  const [open, setOpen] = useState(false);
  const boxes = previewBoxes(draft);
  const response = config.data?.assurance_response ?? "";
  return (
    <section aria-labelledby="text-preview-title" className="grid gap-3 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="text-preview-title" className="text-base font-medium">
          {PREVIEW_TITLE}
        </h2>
        <p className="text-sm text-muted-foreground">{PREVIEW_INTRO}</p>
      </div>
      <Collapsible open={open} onOpenChange={setOpen} className="grid gap-3">
        <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
          <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
          Show text preview
        </CollapsibleTrigger>
        <CollapsibleContent className="grid gap-4">
          {boxes.length === 0 ? <p className="text-sm text-muted-foreground">{PREVIEW_EMPTY}</p> : null}
          {boxes.map((b) => (
            <section key={b.id} aria-label={b.label} className="grid gap-1">
              <h3 className="text-sm font-medium text-muted-foreground">{b.label}</h3>
              <PrintedText lines={printedLines(b.box, b.text, response)} />
            </section>
          ))}
        </CollapsibleContent>
      </Collapsible>
    </section>
  );
}
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
````

**with:**

````
import { PendingButton } from "@/components/app/pending-button";
import { FormattingHelp } from "@/components/builder/formatting-help";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````
} from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
````

**with:**

````
} from "@/lib/liturgy/cards";
import { INLINE_ONLY } from "@/lib/formatting";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````
      showCounter ? `card-${key}-count` : null,
      notesShown ? notesId(key) : null,
````

**with:**

````
      showCounter ? `card-${key}-count` : null,
      `card-${key}-formatting`,
      notesShown ? notesId(key) : null,
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````
          ) : null}
          {key === "assurance" ? (
````

**with:**

````
          ) : null}
          <FormattingHelp id={`card-${key}-formatting`} dialogue={INLINE_ONLY.has(key)} />
          {key === "assurance" ? (
````

**In `frontend/src/components/builder/liturgy/custom-element-card.tsx`, replace:**

````

import { Badge } from "@/components/ui/badge";
````

**with:**

````

import { FormattingHelp } from "@/components/builder/formatting-help";
import { Badge } from "@/components/ui/badge";
````

**In `frontend/src/components/builder/liturgy/custom-element-card.tsx`, replace:**

````
          onChange={(event) => edit({ text: event.target.value })}
        />
````

**with:**

````
          aria-describedby={`custom-${id}-formatting`}
          onChange={(event) => edit({ text: event.target.value })}
        />
        <FormattingHelp id={`custom-${id}-formatting`} />
````

**In `frontend/src/components/builder/liturgy/affirmation-card.tsx`, replace:**

````

import { Button } from "@/components/ui/button";
````

**with:**

````

import { FormattingHelp } from "@/components/builder/formatting-help";
import { Button } from "@/components/ui/button";
````

**In `frontend/src/components/builder/liturgy/affirmation-card.tsx`, replace:**

````
                aria-describedby={showCounter ? "affirmation-hint affirmation-count" : "affirmation-hint"}
````

**with:**

````
                aria-describedby={
                  showCounter ? "affirmation-hint affirmation-count affirmation-formatting" : "affirmation-hint affirmation-formatting"
                }
````

**In `frontend/src/components/builder/liturgy/affirmation-card.tsx`, replace:**

````
              </p>
            </div>
````

**with:**

````
              </p>
              <FormattingHelp id="affirmation-formatting" />
            </div>
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````
import { PendingButton } from "@/components/app/pending-button";
import { Button, buttonVariants } from "@/components/ui/button";
````

**with:**

````
import { PendingButton } from "@/components/app/pending-button";
import { FormattingHelp } from "@/components/builder/formatting-help";
import { Button, buttonVariants } from "@/components/ui/button";
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````
        const note = `bulletin-${key}-carried`;
        return (
````

**with:**

````
        const note = `bulletin-${key}-carried`;
        // The free texts read formatting marks (formatting spec); the names do not.
        const help = long ? `bulletin-${key}-formatting` : null;
        const describedBy = [draft.bulletin.carried.includes(key) ? note : null, help].filter(Boolean).join(" ");
        return (
````

**In `frontend/src/components/builder/bulletin/bulletin-step.tsx`, replace:**

````
              describedBy={draft.bulletin.carried.includes(key) ? note : undefined}
              onChange={(v) => update((d) => setAnnouncement(d, key, v))}
            />
````

**with:**

````
              describedBy={describedBy || undefined}
              onChange={(v) => update((d) => setAnnouncement(d, key, v))}
            />
            {help ? <FormattingHelp id={help} /> : null}
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````
import { SaveCard } from "./save-card";

````

**with:**

````
import { SaveCard } from "./save-card";
import { TextPreviewCard } from "./text-preview-card";

````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````
 * order-of-worship preview: the Liturgy step already shows the order.
````

**with:**

````
 * order-of-worship preview: the Liturgy step already shows the order; the
 * text preview (formatting spec) shows each box's text as it prints, before
 * the downloads.
````

**In `frontend/src/components/builder/review/review-send-step.tsx`, replace:**

````
      {profile.data ? <SaveCard church={profile.data} /> : null}
      <DocumentsCard />
````

**with:**

````
      {profile.data ? <SaveCard church={profile.data} /> : null}
      <TextPreviewCard />
      <DocumentsCard />
````
<!-- /directives -->

- [ ] **Step 4: Run them, the suite, typecheck and lint**

Run: the Step 2 command; the frontend suite; typecheck and lint.
**Expected:** @@T2_PASS@@; `1158 passed (1158)` in `125 passed (125)` files; `typecheck 0`, `lint 0`.

- [ ] **Step 5: Commit and push**

```bash
git add frontend/src/lib/formatting.ts frontend/src/lib/formatting.test.ts frontend/src/components/builder/formatting-help.tsx frontend/src/components/builder/formatting-help.test.tsx frontend/src/components/builder/review/text-preview-card.tsx frontend/src/components/builder/review/text-preview-card.test.tsx frontend/src/components/builder/liturgy/section-card.tsx frontend/src/components/builder/liturgy/custom-element-card.tsx frontend/src/components/builder/liturgy/affirmation-card.tsx frontend/src/components/builder/bulletin/bulletin-step.tsx frontend/src/components/builder/review/review-send-step.tsx frontend/src/components/builder/liturgy/affirmation-card.test.tsx frontend/src/components/builder/liturgy/liturgy-step.test.tsx frontend/src/components/builder/liturgy/review-step.test.tsx frontend/src/components/builder/review/review-send-step.test.tsx
git commit -q -m "Formatting: the help line and the Review preview" -m "A Formatting line under each box that reads the marks (bold and italic only in the Call to Worship and the Assurance), and a Text preview on the Review step drawing each box as the printed bulletin prints it (lib/formatting.ts passes shared/formatting.json too). React text only, never HTML." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

### Task 3: Planted violations (agent)

**Files:** none (each change is undone with `git checkout -- <file>`).

Each row: make the change (the quoted text occurs once in the file unless the row says otherwise), run, see the expected failure, undo, run again (it passes), then `git status --short` is empty. Backend rows run `.venv/bin/python -m pytest -q <files> 2>&1 | tail -1`; frontend rows `(cd frontend && npx vitest run <files> 2>&1 | grep -E "Tests ")`.

In the Change column, `⏎` is a line break in the quoted text.

| # | Rule | Change | Run | Expected (planted) |
|---|---|---|---|---|
| B1 | old text prints exactly as before (printed bulletin) | `backend/printed_bulletin.py`: `        return [Line(style, (Span(text, bold=bold),))]⏎    center = style == "center"` → `        return [Line(style, (Span(text.strip(), bold=bold),))]⏎    center = style == "center"` | `backend/tests/test_formatting.py` | `3 failed, 73 passed` |
| B2 | old text prints exactly as before (Word copy) | `backend/worship_service.py`: `    if not formatting.has_marks(text):⏎        if bold:` → `    if False:⏎        if bold:` | same | `1 failed, 75 passed` |
| B3 | People lines still bold | `backend/printed_bulletin.py`: `(Span("People: ", bold=True), *_spans(content, bold=True))` → `(Span("People: ", bold=True), *_spans(content))` | same | `17 failed, 59 passed` |
| B4 | `**x**` is bold | `backend/formatting.py`: `walk(i + 1, j, bold or kind == "**", italic or kind == "*")` → `walk(i + 1, j, bold, italic or kind == "*")` | same | `10 failed, 66 passed` |
| B5 | `*x*` is italic | same line → `walk(i + 1, j, bold or kind == "**", italic)` | same | `9 failed, 67 passed` |
| B6 | only `#` and `##` are headings | `backend/formatting.py`: `_HEADING = re.compile(r"(#{1,2}) (.*)")` → `_HEADING = re.compile(r"(#{1,3}) (.*)")` | same | `5 failed, 71 passed` |
| B7 | a list line needs "- " | `backend/formatting.py`: `_BULLET = re.compile(r"- (.*)")` → `_BULLET = re.compile(r"- ?(.*)")` | same | `5 failed, 71 passed` |
| B8 | a literal `*` in normal text is unaffected ("5 * 3 * 2") | `backend/formatting.py`: `_SPACE = " \t "` → `_SPACE = "\t"` | same | `4 failed, 72 passed` |
| B9 | no HTML or XML injection in the PDF | `backend/printed_pdf.py`: `        text = escape(to_pdf_text(span.text)).replace("\n", "<br/>")` → `        text = to_pdf_text(span.text).replace("\n", "<br/>")` | same | `1 failed, 75 passed` |
| B10 | the reviewer and the pews read the words without the marks | `backend/api/routes/liturgy_review.py`: `                                      formatting.plain(c.text, inline_only=c.section in formatting.INLINE_ONLY))` → `                                      c.text)` | same | `1 failed, 75 passed` |
| B11 | the limit's 20,000 characters read quickly (linear scan) | `backend/formatting.py`: `                j = nxt[kind][i + 2] if i + 2 <= n else n          # at least one token inside` → `                j = next((k for k in range(i + 2, n) if toks[k][0] == kind and closes[k]), n)` | same | `1 failed, 75 passed` |
| F1 | the preview follows the print rules (the shared fixture) | `frontend/src/lib/formatting.ts`: `const ALNUM = /^[A-Za-z0-9]$/;` → `const ALNUM = /^[A-Za-z]$/;` | `src/lib/formatting.test.ts` | `2 failed \| 2 passed (4)` |
| F2 | People lines bold in the preview | `frontend/src/lib/formatting.ts`: `[span("People: ", true), ...dialogueSpans(content, true)]` → `[span("People: ", true), ...dialogueSpans(content)]` | `src/lib/formatting.test.ts src/components/builder/review/text-preview-card.test.tsx` | `2 failed \| 5 passed (7)` |
| F3 | no HTML injection in the preview | `frontend/src/components/builder/review/text-preview-card.tsx`: `          <span key={i} className={cn(s.bold && "font-bold", s.italic && "italic")}>⏎            {s.text}⏎          </span>` → `          <span key={i} className={cn(s.bold && "font-bold", s.italic && "italic")} dangerouslySetInnerHTML={{ __html: s.text }} />` | `src/components/builder/review/text-preview-card.test.tsx` | `1 failed \| 2 passed (3)` |
| F4 | the help line under each prayer card | `frontend/src/components/builder/liturgy/section-card.tsx`: delete the line `          <FormattingHelp id={`card-${key}-formatting`} dialogue={INLINE_ONLY.has(key)} />` | `src/components/builder/formatting-help.test.tsx` | `1 failed \| 2 passed (3)` |
| F5 | 44 px at 375 px (the preview's toggle) | `frontend/src/components/builder/review/text-preview-card.tsx`: `<CollapsibleTrigger className="flex min-h-11 items-center` → `<CollapsibleTrigger className="flex items-center` | `src/components/builder/review/text-preview-card.test.tsx` | `3 failed (3)` |
| F6 | no em dash in user-facing copy | `frontend/src/components/builder/formatting-help.tsx`: `for a list. Preview on the Review step.";` → `for a list — preview on the Review step.";` | `src/components/builder/formatting-help.test.tsx` | `1 failed \| 2 passed (3)` |
| F7 | no help line under a name box | `frontend/src/components/builder/bulletin/bulletin-step.tsx`: `        const help = long ? `bulletin-${key}-formatting` : null;` → `        const help = `bulletin-${key}-formatting`;` | `src/components/builder/formatting-help.test.tsx` | `1 failed \| 2 passed (3)` |
| F8 | a blank box is left out of the preview (it prints nothing) | `frontend/src/components/builder/review/text-preview-card.tsx`: `    if (text) boxes.push({ id, label, box, text });` → `    boxes.push({ id, label, box, text });` | `src/components/builder/review/text-preview-card.test.tsx` | `2 failed \| 1 passed (3)` |

Once undone, each run passes again: `76 passed` (B rows), `4 passed (4)` (F1), `7 passed (7)` (F2), `3 passed (3)` (F3-F8).

### Task 4: Verification (agent)

**Files:** none.

- [ ] **Step 1: The suites, as here and as CI runs them**

Run: `.venv/bin/python -m pytest -q backend/tests 2>&1 | tail -1`; `.venv/bin/python -m pytest -q 2>&1 | tail -1` (the root, as CI's `backend` job); `.venv/bin/python -m pytest -m postgres -q --collect-only 2>&1 | tail -1`; the frontend suite; typecheck and lint; `(cd frontend && npm run build 2>&1 | grep -cE "Compiled successfully")`; `.venv/bin/python backend/scripts/export_openapi.py >/dev/null && (cd frontend && npm run gen:api >/dev/null 2>&1) && git diff --exit-code frontend/src/lib/api >/dev/null; echo "drift $?"`
**Expected:** @@T4_S1@@

- [ ] **Step 2: No em dash added, nothing frozen touched, the branch's paths**

Run:
```bash
git diff origin/main...HEAD -U0 -- . ':(exclude)docs' | grep '^+' | grep -v '^+++' | grep -c $'\xe2\x80\x94'
git diff --name-only origin/main...HEAD | grep -cE '^(app\.py|streamlit_views/|streamlit_auth\.py|streamlit_tenancy\.py|ui_helpers\.py|streamlit_tests/|\.github/)'
git diff --name-status origin/main...HEAD | cut -f1 | sort | uniq -c
```
**Expected:** @@T4_S2@@

### Task 5: The PR, the merge, the after-deploy check, the phone check, the record (OWNER + agent)

**Files:** Modify (Step 14, after the merge): `docs/ops-runbook.md`: insert `### Formatting record` right before `## Backups` (after `### Affirmation PR B record`, which rides along in this PR). A `###` heading, because `test_ops_workflows.py` pins the `##` list. The Formatting record rides along in the next PR (the em-dash follow-up).

- [ ] **Step 1 (agent): The pre-merge note**

(not replayed: no commands.) This PR changes no table, column, index or row shape and adds no migration; text is stored as typed, as today. Railway's pre-deploy `alembic upgrade head` finds nothing to do. So there is **no backup, no count query and no SQL to read before this merge**, and nothing of the kind is sent to the owner; the daily `db-backup` run stands. If anything here turns out to change the database, stop and tell the owner before going on.

- [ ] **Step 2 (agent → OWNER): Ask to open the PR as a draft**

(not replayed) `gh pr list -R <repo> --head claude/slice-2-plan-4q33le --state open --json number,url` → `[]`. Send the owner exactly this, and wait for a clear yes:

> Text formatting is verified on this machine: 2367 backend tests here (2291 before), 1158 frontend tests in 125 files (1148 in 122), typecheck, lint and the production build clean. The text boxes take **bold**, *italic*, two heading sizes and simple lists, typed as `**bold**`, `*italic*`, `#`, `##`, `- ` and `1. `; they print in the Word files, the printed bulletin and the email's attachments. Each box has a short Formatting line under it, and the Review step has a text preview. Old services print exactly as before. No database change. May I open the pull request as a **draft** titled "Text formatting", so the checks run? Merging stays with you.

- [ ] **Step 3 (agent, on the owner's yes): Open the draft PR, watch CI, ask to mark it ready**

(not replayed)
```bash
cat > "<scratch>/formatting-pr-body.md" <<'BODY'
Text formatting (owner's decisions 3 to 5 of 2026-10-24). Spec: docs/superpowers/specs/2026-10-25-formatting-design.md. Plan: docs/superpowers/plans/2026-10-25-formatting.md. No migration, no API change (the OpenAPI snapshot is unchanged), no new package, no new variable. One PR: either deploy order is safe.

- The grammar (backend/formatting.py; frontend/src/lib/formatting.ts mirrors it): **bold**, *italic* (a mark opens and closes only next to a non-space, never inside a word, so "Psalm 23:1*", "5 * 3" and "2*3*4" print as typed; \* escapes), "# " and "## " headings, "- " and "1. " list lines (numbers as typed), one level. No links, images, tables or code. The Call to Worship and the Assurance take bold and italic only, so their Leader and People lines split as today.
- What prints: the liturgy cards, custom elements, the Affirmation's own text and the four free-text announcements, in the Word copies and the printed bulletin (PDF and Word), so the email's attachments. Headings bold Times 13 and 12 pt under the section's own heading, never Word's Heading styles; items with a hanging indent. People lines in the Call to Worship bold as before. Names, music, the sermon title, pasted readings and Settings stay as typed.
- Old text prints exactly as before: text without a mark takes each renderer's old path (tests: the printed bulletin's lines and PDF bytes and Word XML against verbatim copies of the old helpers; the Word copy against the Streamlit characterization).
- Safety: every span escaped in the PDF, runs as XML text in Word, React text in the preview; typed <b>, <script>, <img> and &amp; print and show as text. The scan is linear (20,000 characters of unclosed marks in milliseconds).
- Pages: a Formatting line under each box (part of its description), and a Text preview on the Review step, closed at first, drawing each box as the printed bulletin prints it. shared/formatting.json (26 cases, the printed bulletin's own output) is checked by both sides, so the preview matches print.
- AI: generation unchanged (plain text with Leader and People lines); the reviewer and the pews read the words without the marks; Revise keeps them.
- Tests: planted violations B1-B11 and F1-F8 in the plan's Task 3.
- Rides along: the Affirmation PR B record in docs/ops-runbook.md.

Before the merge: nothing (no migration). After the merge: the after-deploy check, a phone check, a "Formatting record" in docs/ops-runbook.md.

Tests: backend/tests 2291 → 2367 passed (50 skipped); CI backend job 2322 → 2398 passed (with streamlit_tests' 31), 50 skipped; CI Postgres job 50 passed, 2322 → 2398 deselected; frontend 1148 → 1158 in 122 → 125 files

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS
BODY
gh pr create -R <repo> --draft --base main --head claude/slice-2-plan-4q33le --title "Text formatting" --body-file "<scratch>/formatting-pr-body.md"
gh pr checks <N> -R <repo> --watch --interval 30
```

Run the last line with `run_in_background: true` (or the session's GitHub tools, to the same effect). **Expected:** the PR URL; every check `pass` (`backend`, `backend-postgres`, `frontend`, the Vercel preview); CI's `backend` job `2398 passed, 50 skipped`, its `backend-postgres` job `50 passed, 2398 deselected`, its `frontend` job `1158 passed` in 125 files. Then send: "PR #<N> is green: backend 2398 in CI (2367 plus the 31 old Streamlit tests), Postgres 50, frontend 1158 in 125 files, and the Vercel preview builds. May I mark it ready for review? Merging stays with you." On the yes: `gh pr ready <N> -R <repo>`.

- [ ] **Step 4 (agent → OWNER): Ask to merge, then merge**

Check first (not replayed): `gh pr view <N> -R <repo> --json state,isDraft,mergeable,mergeStateStatus --jq '"\(.state) draft=\(.isDraft) \(.mergeable) \(.mergeStateStatus)"'` → `OPEN draft=false MERGEABLE CLEAN`. Send: "May I merge PR #<N> with a merge commit? There is no database change; Railway restarts the server with nothing to migrate and Vercel publishes the pages, a few minutes apart (either order is safe). I will tell you when both are live, then ask for a short phone check, one step at a time." On a clear yes (not replayed):

```bash
gh pr merge <N> --merge -R <repo>
gh pr view <N> -R <repo> --json state,mergeCommit,mergedAt --jq '"\(.state) \(.mergeCommit.oid) \(.mergedAt)"'
RUN=$(gh run list -R <repo> --workflow ci.yml --branch main --commit "$(gh pr view <N> -R <repo> --json mergeCommit --jq .mergeCommit.oid)" --limit 1 --json databaseId --jq '.[0].databaseId'); gh run watch "$RUN" -R <repo> --exit-status --interval 30 >/dev/null; echo "ci exit $?"
```

**Expected:** `MERGED <merge sha> <UTC time>`; `ci exit 0` (in the background). Record both.

- [ ] **Step 5 (agent): The after-deploy check**

About three minutes after the merge (not replayed):

```bash
curl -s <api>/health/ready; echo
ID=$(gh api "repos/<repo>/deployments?sha=<merge sha>&environment=Production" --jq '.[0].id'); gh api "repos/<repo>/deployments/$ID/statuses" --jq '.[0].state'
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' <app>/builder/review
```

**Expected:** `{"ok":true,"db":"ok"}`; `success` (Vercel published the merge commit to Production); `307 <app>/login?next=%2Fbuilder%2Freview`. No deployment yet, or `pending`: ask again a minute later. `/health/ready` cannot tell the new server from the old one (no API change); Phone 3 does (a bold word in the PDF comes only from the new server). Nothing for the owner to run.

(not replayed: Steps 6-13 need the owner's phone and production.) One short action per message; send the next only after the answer.

- [ ] **Step 6 (OWNER, then agent): Phone 1: the help line**

> On your phone, open the builder's **Liturgy** step (pull down to refresh it first). Under the Opening Prayer's box, is there a line starting "Formatting: **bold**, *italic*, # Heading"?

- [ ] **Step 7 (OWNER, then agent): Phone 2: a heading**

> In the Opening Prayer, add this as a new first line: `# Gathering` (a hash, a space, then the word). Done?

- [ ] **Step 8 (OWNER, then agent): Phone 3: a bold word in a list**

> Add this as a new last line: `- **all** who are weary` (a dash and a space, then two asterisks on each side of "all"). Done?

- [ ] **Step 9 (OWNER, then agent): Phone 4: the preview**

> Open the **Review** step and tap **Show text preview**. Under Opening Prayer, is "Gathering" larger and bold, and the last line a bullet with "all" in bold?

- [ ] **Step 10 (OWNER, then agent): Phone 5: the printed bulletin**

> Download the printed bulletin (PDF). Under OPENING PRAYER, is it printed the same way, with no asterisks or # showing?

- [ ] **Step 11 (OWNER, then agent): Phone 6: the Word file**

> Download the bulletin Word file. Is the Opening Prayer formatted the same way there?

- [ ] **Step 12 (OWNER, then agent): Phone 7: an old service**

> Open **Services**, open a service saved before today and download its printed bulletin. Does it look as it always has?

- [ ] **Step 13 (OWNER, then agent): Phone 8: tidy up**

> Back on the Liturgy step, take the two test lines out of the Opening Prayer (or leave the service unsaved). Done?

Write each step's result, with the date, into `<scratch>/formatting-results.md` (not committed). A problem the owner reports is a follow-up for the record (and for the owner to decide), not a change made now.

**What the phone check cannot show.** The email's attachments (the same files as the downloads; `test_the_email_s_attachments_read_the_marks`), the dialogue boxes' rules, typed HTML (`test_nothing_typed_becomes_markup`, F3), old text byte for byte (B1, B2), the reviewer's and the pews' plain words (B10) and the preview's parity with print in every case (the shared fixture, F1).

- [ ] **Step 14 (agent): Write the record**

(not replayed)
```bash
git fetch origin
git switch claude/slice-2-plan-4q33le
git merge --ff-only origin/main
grep -n '^## Backups$' docs/ops-runbook.md
grep -n '^### ' docs/ops-runbook.md | awk -F: '$1 < '"$(grep -n '^## Backups$' docs/ops-runbook.md | cut -d: -f1)" | tail -1
```

**Expected:** `Fast-forward`; one `## Backups` line; the last `###` heading above it, `### Affirmation PR B record`. Insert, right before `## Backups` (one blank line on each side):

```markdown
### Formatting record

Text formatting (bold, italic, two heading sizes, line breaks and simple
lists, typed as markdown, in the Word files, the printed bulletin and the
email's attachments; a help line under each box and a text preview on the
Review step), merged as PR #<N> (owner's decisions 3 to 5 of 2026-10-24).
No migration and no API change.

| Step | Result | Date |
|---|---|---|
| Merge and deploy | PR #<N> merged <UTC time> (<Eastern time>), merge commit `<short sha>`. CI on `main` (run <run id>): success. Vercel Production for the merge commit: success; `/health/ready` `{"ok":true,"db":"ok"}` | <date> |
| Phone 1. The help line | <Under the Opening Prayer. / …> | <date> |
| Phone 2. A heading | <Typed. / …> | <date> |
| Phone 3. A bold word in a list | <Typed. / …> | <date> |
| Phone 4. The preview | <Heading larger and bold, a bullet with the word in bold. / …> | <date> |
| Phone 5. The printed bulletin | <The same in the PDF, no marks showing. / …> | <date> |
| Phone 6. The Word file | <The same in the Word file. / …> | <date> |
| Phone 7. An old service | <Printed as before. / …> | <date> |
| Phone 8. Tidy up | <Test lines removed. / …> | <date> |
| Not on the phone | The email's attachments, the dialogue boxes, typed HTML, old text byte for byte, the reviewer's plain words and the preview's parity in every case: tests only (T5 "What the phone check cannot show") | <date> |
| Follow-ups | <None. / One line per follow-up.> | <date> |
```

Replace every `<…>` from the results file, keeping one alternative where a cell offers two. Then (not replayed):

```bash
sed -n '/^### Formatting record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c '<'
sed -n '/^### Formatting record$/,/^## Backups$/p' docs/ops-runbook.md | grep -Eic '@|bearer|eyJ|sk-|postgres(ql)?://|[0-9a-f]{8}-[0-9a-f]{4}-'
sed -n '/^### Formatting record$/,/^## Backups$/p' docs/ops-runbook.md | grep -c $'\xe2\x80\x94'
.venv/bin/python -m pytest -q backend/tests/test_ops_workflows.py backend/tests/test_slice1_docs.py backend/tests/test_docs.py 2>&1 | tail -1
git add docs/ops-runbook.md
git commit -q -m "Runbook: Formatting record" -m "Records PR #<N>: the merge and deploy and the owner's phone check. No church id, email address, token or database URL is recorded. Rides along in the next PR." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git push origin claude/slice-2-plan-4q33le
```

**Expected:** `0`; `0`; `0`; `89 passed in <t>s`; one commit, pushed. Next in the owner's order: the em-dash follow-up PR, then Theme PR 2 (D 6).

## Build notes

**How this plan was written (2026-10-22).** Each task's code was built and run in a throwaway worktree of `07826aa` (in the session scratchpad, outside the repo directory; a hard-linked copy of `frontend/node_modules`). The directives were generated from that worktree by a script (a new file as **Create**; every change as **In … replace** with just enough whole-line context to occur once in the file as it stands at that point), and the plan was then **replayed**.

**Replay result: green.** On a fresh worktree of the plan's commit `18dfbbf` (in the session scratchpad), all 45 directives of T1-T3 were applied from this file by the replay script (none failed to match once), every "Run:" of T1-T3 and T5 was run, and its output is pasted above as the step's **Expected** (absolute paths as `<frontend>`). Each Step 2 failed as quoted and each later check passed as quoted. The replayed frontend was byte-identical to the build worktree's. Counts: frontend 1084 in 116 files → **1093** in 117 (T1) → **1095** in 118 (T2) → **1099** in 119 (T3); typecheck and lint clean after each task; `npm ci` with the new lockfile entry exited 0; the production build compiled with `/apple-icon.png`, `/icon.svg` and `/manifest.webmanifest`. The three commits of T1-T3 (by the plan's `git add` lists) left the worktree clean; T5 gave `0` (no backend, Streamlit or CI file), `0` em dashes, and `15 A`, `26 M`. The backend docs tests that T7 Step 11 runs: `89 passed`. T4 was replayed too: the harness built, the manifest answered `200` with no redirect, `/builder` `307` to sign in, and all 12 screenshots had no sideways scroll. **Not replayed:** T6 (no commands) and T7 (GitHub, the owner, production).

**The visual check (T4) as seen while planning.** Light and dark at 375 px and 1280 px: Figtree throughout; filled, tonal, outlined, text, destructive and link buttons readable; the selected chip filled, the rest outlined (from `md` the Settings column reads as a navigation drawer); cards raised; fields with a clear edge; warning and error lines readable; the cover frame light in dark mode; the Save bar on its own surface; `/login` and `/join` centered on the surface. Nothing needed fixing.

**Contrast (from `tokens.test.ts`'s pairs; light / dark).** Lowest text pair 5.27 / 7.24; foreground on background 16.31 / 14.32; on-primary on primary 6.50 / 7.72; secondary chip text on its container 7.24 / 7.24; primary on background 6.19 / 10.83; muted text on muted 7.62 / 8.48; warning on background 6.13 / 10.89; destructive on background 6.15 / 10.89; field edges at least 3.68 / 4.56. Every pair passes in both modes.

**While building:**
- `@material/material-color-utilities` 0.4.0 imports its own files without `.js`, so plain Node cannot load it; 0.3.0 loads and its tonal-spot scheme reproduces the owner's drawn values to within a step or two (S "How the colors are made").
- `npm install --save-dev` on this machine rewrote about 150 unrelated lockfile lines (npm dropped the `libc` fields); the plan adds the two lockfile entries by directive and checks them with `npm ci`.
- One existing test recognized the outline button by `bg-background`; it now reads `border-input` (clarification 8). No other existing test changed: the 44 px class checks (`h-11`, `md:h-9`, `min-h-11`) and the step links' text ("1 Date & readings 1 of 3") are kept by design.
- TypeScript inferred the generator's token object as `{ warning: string }`; JSDoc types on `themeTokens` fixed it.
- A literal em dash in a test source would trip T5 Step 3, so the manifest test builds the character with `String.fromCharCode(0x2014)`.

**Planted violations** (each planted in the build worktree with T1-T3 applied, the named test file run, the change undone; all 11 were caught):

| # | Planted violation | Test file | Result |
|---|---|---|---|
| P1 | a hand edit of `--primary` in the generated block | `tokens.test.ts` | caught: 4 failed |
| P2 | `--muted-foreground` set to the outline color by hand | `tokens.test.ts` | caught: 3 failed |
| P3 | the role map changed to `muted-foreground: outline` and the block regenerated (so only contrast can catch it) | `tokens.test.ts` | caught: 1 failed (light text pairs) |
| P4 | the dark variant no longer skips `.paper` | `tokens.test.ts` | caught: 1 failed |
| P5 | `.paper` given the dark background | `tokens.test.ts` | caught: 2 failed |
| P6 | the cover preview without `paper` | `bulletin-step.test.tsx` | caught: 1 failed |
| P7 | `bg-white/95` on the step footer | `colors.test.ts` | caught: 1 failed |
| P8 | `manifest.webmanifest` dropped from the proxy matcher | `icons.test.ts` | caught: 1 failed |
| P9 | the 192 px icon declared as 196x196 | `icons.test.ts` | caught: 1 failed |
| P10 | the dark `theme-color` set to black | `icons.test.ts` | caught: 1 failed |
| P11 | the outline button back to the kit's `border-border bg-background` | `review-send-step.test.tsx` | caught: 1 failed |

## Follow-ups

1. Theme PR 2: the bottom navigation bar on phones and gentle motion (D follow-up 1 and planning answer 3).
2. If the owner prefers a different icon mark (S "Questions for the owner"), change the geometry in `scripts/generate-icons.mjs`, run it, and commit its files; the tests need no change.

## Follow-ups

- A toolbar for the marks (D 4: may come later).
- A plain-text line in the default voice prompt, if AI drafts start carrying marks (S "AI interplay").
- "People:" lines in bold outside the Call to Worship, if the owner wants it (S Questions, 2).
