# Service Reviewer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

(Work in progress: this plan is being written. Sections below are filled in task by task.)

**Goal:** Ship the service reviewer add-on as one PR (backend and frontend): a "Review service" button on the Liturgy step that leaves short notes under each prayer and in an "Across the service" box, "Revise with these notes" on AI-written cards, the code checks, the AI review, and the writer's new season guidance.

**Source documents:**
- Reviewer spec ("R"): `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`.
- Slice 4 spec ("S4"): `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, "Amendment 2026-09-26: service reviewer", and its 4a and 4b notes.
- Foundations ("F"): `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`.

Baselines checked on `3957d45` (2026-10-01): backend `1183 passed, 11 skipped`; frontend `539 passed` in 75 files.

---

### Task 1: The writer's new season guidance (R "Writer: new season guidance"; S4 reviewer amendment "Baseline change" and "Tests before and after"; owner answer 2; clarification 2)

The default system prompt's three "do not name the season" sentences are replaced with R's new sentence, exactly as R gives it (with R's `…`), kept in one constant, `SEASON_GUIDANCE`, that the reviewer's prompt (T3) quotes too. No `LEGACY_SYSTEM_PROMPT` and no wrapper (owner answer 2: the freeze contingency is off). The new test is the one S4 asks for: the constant contains the new sentence and none of the old ones. The existing tests already compare with `DEFAULT_SYSTEM_PROMPT` or `default_prompts()`, so none changes.

**Files:**
- Modify: `backend/liturgy_prompts.py`, `backend/tests/test_liturgy_prompts.py`

**Interfaces:**
- Produces: `liturgy_prompts.SEASON_GUIDANCE: str` (later user: T3's review prompt); `DEFAULT_SYSTEM_PROMPT` with it in place of the old sentences.

- [ ] **Step 1 (agent): Write the failing test**

**Append to `backend/tests/test_liturgy_prompts.py`:**

````python


# --- the service reviewer: the writer's new season guidance (reviewer spec,
# "Writer: new season guidance"; slice 4 spec, reviewer amendment, "Tests before and after") ---

NEW_SEASON_GUIDANCE = (
    "Let the season's themes come through when the time calls for it, and name the season or festival "
    "where it is natural; saying 'Easter' or 'Christmas' more than once is fine. Avoid canned or repetitive "
    "seasonal language: no stock phrases like 'in this season of…,' 'as we journey through…,' or "
    "'on this Nth Sunday…,' and never name Ordinary Time."
)
OLD_SEASON_SENTENCES = (
    "The occasion is given only to guide tone and theme — do not name or refer to the liturgical season or "
    "calendar in the text itself:",
    "no 'in this ordinary time,' 'in this season of...,' 'as we journey through...,' 'on this Nth Sunday...,' "
    "or similar.",
    "Exception: on a major festival (Christmas Eve/Day, Easter, Pentecost) you may name the day itself, at most "
    "once across the piece.",
)


def test_the_default_system_prompt_has_the_new_season_guidance_and_none_of_the_old():
    for prompt in (lp.DEFAULT_SYSTEM_PROMPT, lp.default_prompts()["system"]):
        assert NEW_SEASON_GUIDANCE in prompt
        for old in OLD_SEASON_SENTENCES:
            assert old not in prompt, old
    assert lp.SEASON_GUIDANCE == NEW_SEASON_GUIDANCE          # the reviewer's prompt quotes the same rule
    # The rest of the voice is unchanged: it still forbids citing passages and still varies openings.
    assert "Do not directly cite or name scripture passages" in lp.DEFAULT_SYSTEM_PROMPT
    assert "Vary how you address God" in lp.DEFAULT_SYSTEM_PROMPT
    assert lp.check_template("system", lp.DEFAULT_SYSTEM_PROMPT).ok
````

- [ ] **Step 2 (agent): Run it and see it fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_prompts.py 2>&1 | tail -2
```

**Expected:** `FAILED backend/tests/test_liturgy_prompts.py::test_the_default_system_prompt_has_the_new_season_guidance_and_none_of_the_old - assert "Let the season's themes ...` (the new sentence is not in the prompt yet), then `1 failed, 24 passed in <t>s`.

- [ ] **Step 3 (agent): Replace the sentences**

**In `backend/liturgy_prompts.py`, replace:**

````python
DEFAULT_SYSTEM_PROMPT = (
    "You are a thoughtful worship writer for Christian liturgy from a moderate Reformed perspective, "
````

**with:**

````python
# The season rule (service reviewer decision 6, 2026-09-26): seasonal themes are
# welcome and the season or festival may be named; canned or repetitive seasonal
# language is not. The reviewer's prompt quotes the same sentence.
SEASON_GUIDANCE = (
    "Let the season's themes come through when the time calls for it, and name the season or festival "
    "where it is natural; saying 'Easter' or 'Christmas' more than once is fine. Avoid canned or repetitive "
    "seasonal language: no stock phrases like 'in this season of…,' 'as we journey through…,' or "
    "'on this Nth Sunday…,' and never name Ordinary Time."
)

DEFAULT_SYSTEM_PROMPT = (
    "You are a thoughtful worship writer for Christian liturgy from a moderate Reformed perspective, "
````

**In `backend/liturgy_prompts.py`, replace:**

````python
    "The occasion is given only to guide tone and theme — do not name or refer to the liturgical season or calendar in the text itself: "
    "no 'in this ordinary time,' 'in this season of...,' 'as we journey through...,' 'on this Nth Sunday...,' or similar. "
    "Exception: on a major festival (Christmas Eve/Day, Easter, Pentecost) you may name the day itself, at most once across the piece. "
````

**with:**

````python
    + SEASON_GUIDANCE + " "
````

- [ ] **Step 4 (agent): Run the file, the Streamlit prompt test and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_liturgy_prompts.py streamlit_tests/test_settings_prompts_translation.py 2>&1 | tail -1
grep -c "do not name or refer to the liturgical season" backend/liturgy_prompts.py
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `<n> passed in <t>s` with no failure (the Streamlit test compares with the constant, so it follows the new text); `0`; `1184 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/liturgy_prompts.py backend/tests/test_liturgy_prompts.py
git commit -q -m "Liturgy prompts: the writer's new season guidance (R Writer; S4 reviewer amendment; owner answer 2)" -m "The default system prompt now lets seasonal themes come through and the
season or festival be named, and rules out only canned or repetitive
seasonal language and naming Ordinary Time, in R's exact words. The
sentence lives in SEASON_GUIDANCE, which the reviewer quotes. Churches
with a saved system prompt keep theirs; streamlit-frozen keeps the old
wording. No legacy copy: the freeze contingency is off." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 1: backend **1184 passed, 11 skipped**; frontend **539 in 75**.

### Task 2: `review_checks.py`, the code checks (R "Layer 1: code checks", Testing; S4 reviewer amendment "New modules"; clarifications 3, 4, 5)

Pure and free: the four checks of R's table, each note `Note(tag, text, source="code")` with R's exact text, plus a `match` (the quoted text) that T3's merge uses to drop an AI note that repeats it. Book names come only from `scripture_refs.BOOKS` (its normalized names and aliases, longest first, whole words, a chapter number after), and `scripture_refs.parse_refs` confirms each candidate, so "Psalm 1" is never "Psalm 119" and "Psalm 200" is no reference. The tests loop over their cases inside one function each, so counts stay stable.

**Files:**
- Create: `backend/review_checks.py`, `backend/tests/test_review_checks.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes: `scripture_refs.BOOKS`, `normalize_book_text`, `parse_refs` (slices 2 and 3).
- Produces (later users: T3, T4):
  - `Note(tag: str, text: str, source: str = "code", match: str = "")` (frozen; `match` is left out of equality)
  - `TAGS = ("checklist", "rules", "voice", "read_aloud", "theology", "repetition")`
  - `check_card(text) -> list[Note]`: stock phrases (in the order they appear), then Ordinary Time (once, outside a stock phrase that already named it), then references, each point once
  - `check_openings(texts) -> list[Note]`: one `repetition` note per opening pair shared by two or more cards, in order
  - `opening_words(text) -> list[str]`, `scripture_book_keys() -> tuple[str, ...]`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_review_checks.py`:**

````python
"""review_checks: the reviewer's code checks (reviewer spec, "Layer 1: code
checks" and Testing; slice 4 spec, reviewer amendment). Pure, so table-driven:
each test loops over its cases inside one function."""
import scripture_refs as sr
from review_checks import Note, check_card, check_openings, scripture_book_keys


def texts(notes):
    return [n.text for n in notes]


def test_stock_seasonal_phrases_are_flagged_whatever_their_case():
    cases = [
        ("Gather us in this season of waiting.", ['Stock phrase "in this season of". Say it more naturally.']),
        ("AS WE JOURNEY toward the cross, hold us.", ['Stock phrase "AS WE JOURNEY". Say it more naturally.']),
        ("On this Third Sunday of Easter we praise you.",
         ['Stock phrase "On this Third Sunday". Say it more naturally.']),
        ("on this twenty-first Sunday after Pentecost",
         ['Stock phrase "on this twenty-first Sunday". Say it more naturally.']),
        ("Meet us in this Ordinary Time.", ['Stock phrase "in this Ordinary Time". Say it more naturally.']),
        # Plain seasonal themes and an unadorned "this Sunday" are not stock phrases.
        ("Christ is risen! Easter joy fills us. Easter hope sends us.", []),
        ("We gather on this Sunday morning.", []),
        ("In this season, as we journey together", ['Stock phrase "as we journey". Say it more naturally.']),
    ]
    for text, expected in cases:
        notes = check_card(text)
        assert texts(notes) == expected, text
        assert all(n.tag == "rules" and n.source == "code" for n in notes)


def test_naming_ordinary_time_is_flagged_once_wherever_it_appears():
    cases = [
        ("Through these ordinary time days, keep us.", ["Names Ordinary Time. Leave the season unnamed."]),
        ("Ordinary Time teaches patience. In ORDINARY TIME we grow.",
         ["Names Ordinary Time. Leave the season unnamed."]),
        # Inside the stock phrase only the stock-phrase note shows (one point, one note).
        ("Walk with us in this ordinary time.", ['Stock phrase "in this ordinary time". Say it more naturally.']),
        ("In this ordinary time, and all ordinary time, keep us.",
         ['Stock phrase "In this ordinary time". Say it more naturally.',
          "Names Ordinary Time. Leave the season unnamed."]),
        ("An ordinary day, a quiet time.", []),
    ]
    for text, expected in cases:
        assert texts(check_card(text)) == expected, text
    (note,) = check_card("Ordinary Time is long.")
    assert note == Note("rules", "Names Ordinary Time. Leave the season unnamed.") and note.match == "Ordinary Time"


def test_every_book_name_and_alias_in_scripture_refs_books_is_caught_with_a_chapter():
    keys = scripture_book_keys()
    assert len(keys) == sum(1 + len(b.aliases) for b in sr.BOOKS)   # the one table, no second list
    for key in keys:
        cited = " ".join(word.capitalize() for word in key.split(" ")) + " 3"
        notes = check_card(f"As we read in {cited}, God is near.")
        assert texts(notes) == [f"Cites {cited}. Draw on the reading's themes without naming it."], key
        assert notes[0].match == cited
    cases = [
        ("Like the storm in Mark 4:35-41, calm us.", "Mark 4:35-41"),
        ("Speak, Lord (1 Sam 3:10), for we listen.", "1 Sam 3:10"),
        ("as 1 Sam. 3:10 tells", "1 Sam. 3:10"),
        ("Psalm 1 sings of trees by water.", "Psalm 1"),
        ("Psalm 119:105 is a lamp.", "Psalm 119:105"),
        ("Ps. 23 is a comfort.", "Ps. 23"),
        ("In 1 Corinthians 13 love is patient.", "1 Corinthians 13"),
    ]
    for text, cited in cases:
        assert texts(check_card(text)) == [f"Cites {cited}. Draw on the reading's themes without naming it."], text


def test_no_false_hit_on_ordinary_words():
    for text in (
        "We mark this day with joy.",
        "Mark the moment with silence.",
        "We mark 3 years together.",            # a verb, lower case
        "Write our names in the book of life.",
        "Isaiah's vision fills the temple.",    # a book with no chapter
        "There is 1 God, and Acts of mercy follow.",
        "A song 2 voices can share.",
        "Psalm 200 voices rise.",               # no book has 200 chapters: parse_refs reads no span
        "Remember Mark 4b.",                    # not a chapter number
        "Job 3s and Mark4 are not references.",
    ):
        assert check_card(text) == [], text


def test_a_card_s_notes_follow_the_table_s_order_once_each():
    text = ("Mark 4:35-41 again: as we journey, as we journey, through Ordinary Time, "
            "in this season of hope; Mark 4:35-41.")
    assert texts(check_card(text)) == [
        'Stock phrase "as we journey". Say it more naturally.',
        'Stock phrase "in this season of". Say it more naturally.',
        "Names Ordinary Time. Leave the season unnamed.",
        "Cites Mark 4:35-41. Draw on the reading's themes without naming it.",
    ]
    assert check_card("") == [] and check_card("   ") == []


def test_repeated_openings_across_cards_go_to_the_service_box():
    cards = [
        ("call_to_worship", "Leader: Gracious God, you call us.\nPeople: We come."),
        ("opening_prayer", "Gracious God, we praise you."),
        ("prayer_of_confession", "People: gracious   GOD! we confess."),
        ("prayer_for_illumination", "Holy Spirit, open our ears."),
        ("offertory_prayer", "Holy Spirit; bless these gifts."),
        ("benediction", "Go in peace."),
        ("assurance", "Leader:"),
    ]
    notes = check_openings([text for _section, text in cards])
    assert notes == [
        Note("repetition", 'Several prayers open with "Gracious God".'),
        Note("repetition", 'Several prayers open with "Holy Spirit".'),
    ]
    assert [n.match for n in notes] == ["Gracious God", "Holy Spirit"]
    assert check_openings(["Gracious God, hear us.", "Loving God, hear us."]) == []
    assert check_openings(["God", "God"]) == []              # one word is not an opening pair
    many = [f"Word{i} Two, a" for i in range(4) for _ in range(2)]
    assert len(check_openings(many)) == 4                    # the merge caps the box at 3, not the check
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy; "
````

**with:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks; "
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_review_checks.py 2>&1 | tail -2
```

**Expected:** `ERROR backend/tests/test_review_checks.py`, then `1 error in <t>s` (collection stops at `ModuleNotFoundError: No module named 'review_checks'`).

- [ ] **Step 3 (agent): Write the module**

**Create `backend/review_checks.py`:**

````python
"""The service reviewer's code checks (reviewer spec, "Layer 1: code checks";
slice 4 spec, "Amendment 2026-09-26: service reviewer").

Deterministic and free: they run on every review, even with no OpenAI key, and
their notes come first because they are certain. Each note is
Note(tag, text, source="code"); `match` is the quoted text an AI note repeats
(usecases.liturgy_review drops such a repeat).

- check_card(text), in the table's order, each point once:
  1. stock seasonal phrases, any case ("in this season of", "as we journey",
     "on this … Sunday" with one to four words between, "in this ordinary
     time"), in the order they appear;
  2. naming Ordinary Time, wherever it appears outside a stock phrase that
     already said so;
  3. a scripture reference: a book name or alias from scripture_refs.BOOKS
     (the one book table; no second list), written with a capital letter,
     followed by a chapter number ("Mark 4", "1 Sam 3:10"), and kept only
     when scripture_refs.parse_refs reads it as a passage (so "Psalm 1" is
     never "Psalm 119", and "Psalm 200" is no reference).
- check_openings(texts): the first two words of each card after any leading
  "Leader:" or "People:" label, any case, punctuation dropped; each pair two
  or more cards share is one "Across the service" note.

Pure: no I/O, no FastAPI, no AI (tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache

import scripture_refs

TAGS = ("checklist", "rules", "voice", "read_aloud", "theology", "repetition")


@dataclass(frozen=True)
class Note:
    tag: str                                         # one of TAGS
    text: str                                        # one sentence
    source: str = "code"                             # "code" or "ai"
    match: str = field(default="", compare=False)    # a code note's quoted text, for the merge


STOCK_PHRASE = re.compile(
    r"\b(?:in this season of|as we journey|on this (?:[\w'’-]+\s+){1,4}?sunday|in this ordinary time)\b",
    re.IGNORECASE,
)
ORDINARY_TIME = re.compile(r"\bordinary time\b", re.IGNORECASE)
STOCK_NOTE = 'Stock phrase "{match}". Say it more naturally.'
ORDINARY_NOTE = "Names Ordinary Time. Leave the season unnamed."
CITES_NOTE = "Cites {match}. Draw on the reading's themes without naming it."
OPENING_NOTE = 'Several prayers open with "{words}".'

_LABEL = re.compile(r"^\s*(?:leader|people)\s*:\s*", re.IGNORECASE)
_WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")


def scripture_book_keys() -> tuple[str, ...]:
    """Every BOOKS name (normalized) and alias, longest first: what a reference can start with."""
    keys = {scripture_refs.normalize_book_text(book.name) for book in scripture_refs.BOOKS}
    keys.update(alias for book in scripture_refs.BOOKS for alias in book.aliases)
    return tuple(sorted(keys, key=lambda k: (-len(k), k)))


def _key_pattern(key: str) -> str:
    """'1 sam' -> '1\\s*sam\\.?': a numeral may touch the name; words are spaced; an abbreviation may end in '.'."""
    first, *rest = key.split(" ")
    if first.isdigit() and rest:
        head = re.escape(first) + r"\s*" + re.escape(rest[0])
        rest = rest[1:]
    else:
        head = re.escape(first)
    return r"\s+".join([head, *(re.escape(word) for word in rest)]) + r"\.?"


@lru_cache(maxsize=1)
def _reference_pattern() -> re.Pattern[str]:
    books = "|".join(_key_pattern(key) for key in scripture_book_keys())
    return re.compile(
        r"(?<![\w])(?P<book>" + books + r")\s+"
        r"(?P<loc>\d{1,3}(?::\d{1,3}[a-d]?(?:[-–]\d{1,3}(?::\d{1,3})?[a-d]?)?)?)(?![\w:])",
        re.IGNORECASE,
    )


def _is_reference(match: re.Match[str]) -> bool:
    book = match.group("book")
    letter = next((c for c in book if c.isalpha()), "")
    if not letter.isupper():                         # "we mark 3 years" is a verb, not Mark 3
        return False
    parsed = scripture_refs.parse_refs(f"{book} {match.group('loc')}")
    return bool(parsed.spans) and not parsed.unparsed


def check_card(text: str) -> list[Note]:
    """The code notes for one card, in the table's order, each point once."""
    notes: list[Note] = []
    seen: set[str] = set()

    def add(note: Note) -> None:
        if note.text.lower() not in seen:
            seen.add(note.text.lower())
            notes.append(note)

    stock = list(STOCK_PHRASE.finditer(text or ""))
    for m in stock:
        add(Note("rules", STOCK_NOTE.format(match=m.group(0)), match=m.group(0)))
    inside = [(m.start(), m.end()) for m in stock if ORDINARY_TIME.search(m.group(0))]
    for m in ORDINARY_TIME.finditer(text or ""):
        if not any(start <= m.start() and m.end() <= end for start, end in inside):
            add(Note("rules", ORDINARY_NOTE, match=m.group(0)))
            break
    for m in _reference_pattern().finditer(text or ""):
        if _is_reference(m):
            cited = m.group(0).strip()
            add(Note("rules", CITES_NOTE.format(match=cited), match=cited))
    return notes


def opening_words(text: str) -> list[str]:
    """The first two words after any leading "Leader:" or "People:" label, punctuation dropped."""
    return _WORD.findall(_LABEL.sub("", text or "", count=1))[:2]


def check_openings(texts: Sequence[str]) -> list[Note]:
    """One "Across the service" note per opening pair that two or more cards share, in order."""
    first: dict[str, str] = {}
    counts: dict[str, int] = {}
    for text in texts:
        words = opening_words(text)
        if len(words) < 2:
            continue
        key = " ".join(w.lower() for w in words)
        first.setdefault(key, " ".join(words))
        counts[key] = counts.get(key, 0) + 1
    return [Note("repetition", OPENING_NOTE.format(words=words), match=words)
            for key, words in first.items() if counts[key] > 1]
````

- [ ] **Step 4 (agent): Run the file, the import gate and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_review_checks.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `9 passed in <t>s`; `1190 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/review_checks.py backend/tests/test_review_checks.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Reviewer: the code checks (R Layer 1; S4 reviewer amendment)" -m "Stock seasonal phrases, naming Ordinary Time, scripture references from
the one book table (scripture_refs.BOOKS, confirmed by parse_refs) and
repeated openings across cards, each with R's note text. Pure, no AI:
they run even without an OpenAI key." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 2: backend **1190 passed, 11 skipped**; frontend **539 in 75**.

### Task 3: The AI review, `usecases/liturgy_review.review_service` (R "Layer 2: AI review", API, Testing "Review usecase"; S4 reviewer amendment "Routes", "Timeouts", "Tenancy"; F §1.5, §1.8, §2.8; clarifications 6-11)

One call per request: the code checks on every card and across the cards; with AI off, those notes and `ai_status: "not_configured"`; otherwise the church's merged system prompt, rubric and voice profile read in one session closed before the AI call, one prompt built inside `MAX_PROMPT_CHARS` (profile, then sermon text, then the longest card), `charge(1)` (an empty bucket is `rate_limited`, no call), one `complete()` call (`json_mode`, 2 000 tokens, a 75 s deadline from the start of the usecase), tolerant parsing and the merge. Every failure keeps the code notes; the review never answers `prompt_invalid`.

**Files:**
- Create: `backend/usecases/liturgy_review.py`, `backend/tests/test_usecase_liturgy_review.py`
- Modify: `backend/tests/test_no_streamlit_in_core.py`

**Interfaces:**
- Consumes: `review_checks` (T2); `liturgy_prompts.merge_prompts`, `sermon_text_block`, `SEASON_GUIDANCE` (T1), `MAX_PROMPT_CHARS`; `service_rubric.merge_rubric`, `format_checklist`; `prayer_library.read_library`, `MAX_PROFILE_CHARS`; `repos.churches.get_church_prompts`, `get_church_rubric_overrides`, `get_church` (each with `session=`); `openai_client` and its errors; `domain_errors.RateLimited`; `db.session_scope`.
- Produces (later users: T4, T5):
  - `ReviewCard(section, origin, text)`, `CardNotes(section, notes: tuple[Note, ...])`, `ReviewOutcome(cards, service_notes, ai_status)`
  - `review_service(*, church_id, user_id, occasion, scriptures, cards, sermon: tuple[str, str] | None = None, charge=lambda n: None, ai=openai_client, clock=time.monotonic) -> ReviewOutcome`; raises only what the session or an unexpected bug raises (never an AI error, never `RateLimited`)
  - `build_review_prompt(...) -> ReviewPrompt | None`, `parse_review(raw, sections, *, voice)`, `merge_notes(code, ai, limit)`, `ReviewPrompt(messages, dropped)`, `_readings(scriptures)` (T4 reuses it)
  - `REVIEW_BUDGET_S = 75.0`, `REVIEW_MAX_COMPLETION_TOKENS = 2000`, `MAX_CARD_CHARS = 4000`, `MIN_CARD_CHARS = 200`, `MAX_NOTE_CHARS = 240`, `MAX_NOTES_PER_CARD = 3`, `MAX_SERVICE_NOTES = 3`, `AI_STATUSES`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_usecase_liturgy_review.py`:**

````python
"""usecases.liturgy_review.review_service (reviewer spec, "Layer 2: AI review"
and Testing; slice 4 spec, reviewer amendment). SQLite `tmp_db`, and a FakeAI
passed as `ai=`."""
import json
import logging
import re
import uuid

import pytest

import liturgy_prompts as lp
from db import get_engine, session_scope
from domain_errors import Busy, NotConfigured, RateLimited, UpstreamError, UpstreamTimeout
from integrations.openai_client import FakeAI
from repos import churches
from review_checks import Note
from usecases import liturgy_review
from usecases.liturgy_review import ReviewCard

SECRET = "sk-secret upstream detail"
STOCK = 'Stock phrase "as we journey". Say it more naturally.'


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def answer(cards=(), service=()):
    return json.dumps({"cards": [{"section": key, "notes": [{"tag": t, "text": s} for t, s in notes]}
                                 for key, notes in cards],
                       "service_notes": [{"tag": t, "text": s} for t, s in service]})


CARDS = [
    ReviewCard("call_to_worship", "typed", "Leader: Gracious God, as we journey, we gather.\nPeople: We come."),
    ReviewCard("opening_prayer", "ai", "Gracious God, we praise you. Amen."),
    ReviewCard("benediction", "default", "Go in peace."),
]


def run(church_id, cards=CARDS, ai=None, **kw):
    kw.setdefault("occasion", "Third Sunday of Easter")
    kw.setdefault("scriptures", ["Acts 9:1-6", "John 21:1-19"])
    return liturgy_review.review_service(church_id=church_id, user_id=uuid.uuid4(), cards=cards,
                                         ai=ai if ai is not None else FakeAI(reply=answer()), **kw)


def notes_of(outcome):
    return {c.section: [(n.tag, n.text, n.source) for n in c.notes] for c in outcome.cards}


def test_without_ai_the_code_notes_come_back_and_nothing_is_charged(church):
    ai = FakeAI(available=False)
    charged = []
    outcome = run(church, ai=ai, charge=charged.append)
    assert outcome.ai_status == "not_configured" and ai.calls == [] and charged == []
    assert notes_of(outcome) == {"call_to_worship": [("rules", STOCK, "code")], "opening_prayer": [],
                                 "benediction": []}
    assert outcome.service_notes == (Note("repetition", 'Several prayers open with "Gracious God".'),)


def test_the_prompt_carries_the_church_s_rules_present_checklists_profile_and_code_notes(church):
    churches.set_church_prompts(church, {"system": "Our church's own voice."})
    set_settings(church, rubric={"prayers": {"opening_prayer": ["names one hope"]}},
                 prayer_library={"prayers": [], "voice_profile": "  Plain, warm, short sentences.  "})
    ai = FakeAI(reply=answer())
    long_card = ReviewCard("prayers_of_the_people", "ai", "P" * 5000)
    run(church, cards=[*CARDS, long_card], ai=ai, clock=lambda: 1000.0,
        sermon=("Mark 4:35-41", "S" * 3000))
    (call,) = ai.calls
    system, user = (m["content"] for m in call["messages"])
    assert (call["json_mode"], call["max_completion_tokens"], call["deadline"]) == (True, 2000, 1075.0)
    assert system.startswith("You are a tough, fair liturgical editor for a moderate Reformed (PC(USA)) "
                             "congregation.")
    assert "You never rewrite the prayers" in system
    assert "standing rules, the church's instructions to its writer:\nOur church's own voice." in system
    assert lp.SEASON_GUIDANCE in system and "not seasonal themes" in system
    # The checklists of the sections present only, the church's override included.
    assert "A good Opening Prayer:\n- names one hope" in system
    assert "A good Call to Worship:" in system and "A good Prayers of the People:" in system
    assert "A good Benediction:" in system                    # a default card is reviewed like any other
    assert "A good Prayer of Confession:" not in system and "A good Offertory Prayer:" not in system
    assert "voice profile:\nPlain, warm, short sentences." in system and "skip the Voice check" not in system
    assert '{"cards": [{"section": key' in system and "240 characters or fewer" in system
    assert user.startswith("Occasion: Third Sunday of Easter\n\nReadings:\n- Acts 9:1-6\n- John 21:1-19\n\n")
    assert "Sermon text (Mark 4:35-41), for themes only; do not quote, cite, or name it:\n" + "S" * 2000 + "\n\n" in user
    assert ("[call_to_worship] Call to Worship (typed by the pastor):\nLeader: Gracious God, as we journey, "
            "we gather.\nPeople: We come.") in user
    assert "[opening_prayer] Opening Prayer (an AI draft):\nGracious God" in user
    assert "[benediction] Benediction (the church's default):\nGo in peace." in user
    assert "(an AI draft):\n" + "P" * 4000 + "\n\n" in user and "P" * 4001 not in user   # cut for review only
    assert user.endswith("Notes already found by code. Do not repeat them:\n"
                         f"- call_to_worship: {STOCK}\n"
                         '- across the service: Several prayers open with "Gracious God".')
    assert user.index("[call_to_worship]") < user.index("[opening_prayer]") < user.index("[prayers_of_the")


def test_without_a_voice_profile_the_voice_check_is_skipped_and_its_notes_dropped(church):
    ai = FakeAI(reply=answer([("opening_prayer", [("voice", "Sounds unlike the pastor."),
                                                  ("theology", "Says God needs our praise.")])]))
    outcome = run(church, ai=ai)
    system = ai.calls[0]["messages"][0]["content"]
    assert "There is no voice profile, so skip the Voice check: never use the voice tag." in system
    assert notes_of(outcome)["opening_prayer"] == [("theology", "Says God needs our praise.", "ai")]


def test_parsing_drops_unknown_sections_and_tags_trims_and_cuts(church):
    long_note = "word " * 70
    reply = json.dumps({
        "cards": [
            {"section": "opening_prayer", "notes": [
                {"tag": "Read aloud", "text": "  Hard   to say\naloud.  "},
                {"tag": "style", "text": "Unknown tag."},
                {"tag": "theology", "text": 5},
                {"tag": "rules", "text": "   "},
                {"tag": "checklist", "text": long_note},
                {"tag": "Read-Aloud", "text": "Second."},
                {"tag": "theology", "text": "Fourth, cut."},
            ]},
            {"section": "assurance", "notes": [{"tag": "rules", "text": "Not reviewed."}]},
            {"section": "nonsense", "notes": [{"tag": "rules", "text": "No such card."}]},
            "not an object",
            {"section": "benediction", "notes": "not a list"},
        ],
        "service_notes": [{"tag": "repetition", "text": f"Across {i}."} for i in range(5)],
    })
    outcome = run(church, cards=CARDS[1:], ai=FakeAI(reply=reply))      # no code notes here
    assert outcome.ai_status == "ok"
    assert notes_of(outcome) == {
        "opening_prayer": [("read_aloud", "Hard to say aloud.", "ai"),
                           ("checklist", long_note.strip()[:240].rstrip(), "ai"),
                           ("read_aloud", "Second.", "ai")],
        "benediction": [],
    }
    assert len(notes_of(outcome)["opening_prayer"][1][1]) <= 240
    assert [n.text for n in outcome.service_notes] == ["Across 0.", "Across 1.", "Across 2."]
    for reply in ("{}", '{"cards": null, "service_notes": {}}'):           # an object with nothing usable
        assert run(church, cards=CARDS[1:], ai=FakeAI(reply=reply)).ai_status == "ok"


def test_the_merge_puts_code_notes_first_and_drops_repeats(church):
    cards = [ReviewCard("prayer_of_confession", "ai",
                        "In this season of Lent, as we journey, we confess. Mark 1:15 calls us."),
             ReviewCard("assurance", "ai", "Leader: Holy God, you forgive."),
             ReviewCard("offertory_prayer", "ai", "Holy God, take these gifts.")]
    reply = answer(
        [("prayer_of_confession", [("rules", 'The phrase "AS WE JOURNEY" is canned.'),
                                   ("read_aloud", "The second sentence is long.")]),
         ("assurance", [("theology", "Grace comes before confession here."), ("rules", "Fine otherwise.")])],
        [("repetition", 'Two prayers open with "holy god".'), ("rules", "Both prayers mention Lent.")])
    outcome = run(church, cards=cards, ai=FakeAI(reply=reply))
    assert notes_of(outcome) == {
        "prayer_of_confession": [
            ("rules", 'Stock phrase "In this season of". Say it more naturally.', "code"),
            ("rules", STOCK, "code"),
            ("rules", "Cites Mark 1:15. Draw on the reading's themes without naming it.", "code"),
        ],                                                     # the AI's notes are past the 3
        "assurance": [("theology", "Grace comes before confession here.", "ai"), ("rules", "Fine otherwise.", "ai")],
        "offertory_prayer": [],
    }
    assert [(n.text, n.source) for n in outcome.service_notes] == [
        ('Several prayers open with "Holy God".', "code"), ("Both prayers mention Lent.", "ai")]


def test_ai_failures_keep_the_code_notes_with_the_right_status(church, caplog):
    cases = [
        (FakeAI(error=NotConfigured(SECRET, code="ai_not_configured")), "not_configured"),
        (FakeAI(error=Busy(SECRET, code="ai_busy")), "busy"),
        (FakeAI(error=UpstreamTimeout(SECRET, code="ai_timeout")), "timeout"),
        (FakeAI(error=UpstreamError(SECRET, code="ai_upstream_error")), "error"),
        (FakeAI(error=RuntimeError(SECRET)), "error"),
        (FakeAI(reply="not json at all"), "error"),
        (FakeAI(reply='["a list"]'), "error"),
        (FakeAI(reply="[" * 100_000), "error"),
    ]
    for ai, status in cases:
        outcome = run(church, ai=ai)
        assert outcome.ai_status == status, status
        assert notes_of(outcome)["call_to_worship"] == [("rules", STOCK, "code")]
        assert len(outcome.service_notes) == 1 and "secret" not in repr(outcome)
    assert "RuntimeError" in caplog.text                    # the unexpected one is logged with its stack


def test_the_ai_bucket_is_charged_once_only_when_the_ai_is_called(church):
    events = []
    ai = FakeAI(reply=lambda messages: events.append("complete") or answer())
    run(church, ai=ai, charge=lambda n: events.append(("charge", n)))
    assert events == [("charge", 1), "complete"]

    def empty(n):
        raise RateLimited("Too many requests. Try again in 15 seconds.", retry_after_seconds=15)

    ai = FakeAI(reply=answer())
    outcome = run(church, ai=ai, charge=empty)
    assert (outcome.ai_status, ai.calls) == ("rate_limited", [])
    assert notes_of(outcome)["call_to_worship"] == [("rules", STOCK, "code")]


def _big(church, system_chars=8000, checklist_items=12):
    churches.set_church_prompts(church, {"system": "s" * system_chars})
    set_settings(church, rubric={"prayers": {key: [f"{key[:3]}{i:02d}" + "c" * 294 for i in range(checklist_items)]
                                             for key in lp.SECTION_ORDER}},
                 prayer_library={"prayers": [], "voice_profile": "v" * 2000})


def test_the_budget_drops_the_profile_then_the_sermon_then_cuts_the_longest_card(church):
    _big(church, checklist_items=2)       # 8 000 system, 2 000 profile, two 300-character points a section
    sermon = ("Mark 4:35-41", "x" * 2000)
    cases = [
        ([ReviewCard("benediction", "ai", "b" * 4000)], (), "v" * 2000, True),
        ([ReviewCard(k, "ai", "t" * 4000) for k in lp.SECTION_ORDER[:2]] + [ReviewCard("assurance", "ai", "a" * 2000)],
         ("profile",), None, True),
        ([ReviewCard(k, "ai", "t" * 4000) for k in lp.SECTION_ORDER[:3]], ("profile", "sermon"), None, False),
        ([ReviewCard(k, "ai", "t" * 4000) for k in lp.SECTION_ORDER], ("profile", "sermon", "cards"), None, False),
    ]
    for cards, dropped, profile, has_sermon in cases:
        ai = FakeAI(reply=answer())
        outcome = run(church, cards=cards, ai=ai, sermon=sermon)
        assert outcome.ai_status == "ok", dropped
        system, user = (m["content"] for m in ai.calls[0]["messages"])
        assert len(system) + len(user) <= lp.MAX_PROMPT_CHARS, dropped
        assert ("v" * 2000 in system) is (profile is not None), dropped
        assert ("skip the Voice check" in system) is (profile is None), dropped
        assert ("Sermon text (Mark 4:35-41)" in user) is has_sermon, dropped
        if "cards" in dropped:                             # the longest card first, none below 200
            lengths = [len(m) for m in re.findall(r"\(an AI draft\):\n(t+)", user)]
            assert lengths[:6] == [200] * 6 and 200 < lengths[6] < 4000 and lengths[7] == 4000
        else:
            assert all(c.text in user for c in cards), dropped
    # The church's own text too long even with the shortest cards: no AI call, never prompt_invalid.
    _big(church, system_chars=20_000)
    ai = FakeAI(reply=answer())
    charged = []
    outcome = run(church, cards=[ReviewCard(k, "ai", "t" * 4000) for k in lp.SECTION_ORDER], ai=ai,
                  charge=charged.append)
    assert (outcome.ai_status, ai.calls, charged) == ("error", [], [])


def test_one_session_reads_everything_and_none_is_open_during_the_ai_call(church, monkeypatch):
    real = liturgy_review.session_scope
    state = {"opened": 0, "open": 0, "during_ai": []}

    class Counting:
        def __enter__(self):
            state["opened"] += 1
            state["open"] += 1
            self.inner = real()
            return self.inner.__enter__()

        def __exit__(self, *exc):
            state["open"] -= 1
            return self.inner.__exit__(*exc)

    set_settings(church, rubric={"prayers": {"benediction": ["is short"]}},
                 prayer_library={"prayers": [], "voice_profile": "Plain."})
    churches.set_church_prompts(church, {"system": "Our voice."})
    for module in (liturgy_review, churches):
        monkeypatch.setattr(module, "session_scope", Counting)
    pool = get_engine().pool

    def reply(messages):
        state["during_ai"].append((state["open"], pool.checkedout()))
        return answer()

    ai = FakeAI(reply=reply)
    run(church, ai=ai)
    assert state["opened"] == 1 and state["during_ai"] == [(0, 0)]
    system = ai.calls[0]["messages"][0]["content"]
    assert "Our voice." in system and "A good Benediction:\n- is short" in system and "profile:\nPlain." in system


def test_the_info_line_carries_no_prayer_text_or_notes(church, caplog):
    churches.set_church_prompts(church, {"system": "SECRET-PROMPT"})
    ai = FakeAI(reply=answer([("opening_prayer", [("theology", "SECRET-NOTE")])]))
    cards = [ReviewCard("opening_prayer", "typed", "SECRET-TEXT as we journey")]
    with caplog.at_level(logging.INFO, logger="usecases.liturgy_review"):
        run(church, cards=cards, ai=ai, occasion="SECRET-OCCASION", sermon=("Mark 4", "SECRET-SERMON"))
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.review" in info and " cards=1 code_notes=1 ai=1 " in info
    assert "ai_status=ok" in info and "notes=2" in info and "outcome=ok" in info
    assert "SECRET" not in info and "journey" not in info
````

**In `backend/tests/test_no_streamlit_in_core.py`, replace:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks; "
````

**with:**

````python
            "liturgy_config, prayer_library, liturgy_prompts, usecases.liturgy, review_checks, usecases.liturgy_review; "
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -2
```

**Expected:** `ERROR backend/tests/test_usecase_liturgy_review.py`, then `1 error in <t>s` (`ImportError: cannot import name 'liturgy_review' from 'usecases'`).

- [ ] **Step 3 (agent): Write the usecase**

**Create `backend/usecases/liturgy_review.py`:**

````python
"""The service reviewer (reviewer spec, "Layer 2: AI review", "Revise", API;
slice 4 spec, "Amendment 2026-09-26: service reviewer"; F §1.5, §1.8, §2.8).

review_service:
1. Runs the code checks (review_checks) on every card and across the cards.
   Their notes are certain, need no AI and come first.
2. With no AI configured: the code notes, ai_status "not_configured".
3. Otherwise reads, in one session that closes before the AI call (F §1.8),
   the church's merged system prompt, its rubric and its voice profile, fresh
   on every call and never from the client.
4. Builds one prompt (the role, the standing rules, the season guidance, the
   present sections' checklists, the voice profile or "skip Voice", the
   context, the cards in order with their labels and origins, the code notes
   not to repeat, and the output contract), each card cut to 4 000
   characters. Over MAX_PROMPT_CHARS: the voice profile goes first, then the
   sermon text, then the longest card is cut further (never below 200); if
   the church's own text alone is still too long, the AI is skipped
   ("error"), so the review never answers prompt_invalid.
5. Charges the `ai` bucket 1 through `charge` just before the call; an
   empty bucket skips the call: "rate_limited" (a declared deviation, F §1.5).
6. One complete() call, json_mode, 2 000 tokens, inside a 75 s deadline from
   the start of the usecase. AI failures and invalid JSON keep the code notes
   and say why in ai_status; upstream text is never returned.
7. Tolerant parsing (unknown sections and tags dropped, a note trimmed to 240
   characters, Voice dropped when there is no profile), then the merge: code
   notes first, an AI note that repeats a code note's quoted text dropped, at
   most 3 per card and 3 across the service.

Logs one `liturgy.review` INFO line per call; prompts, cards and answers only
at DEBUG (F §2.5). Writes nothing. No FastAPI, Starlette or Streamlit here
(tests/test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Optional

import liturgy_prompts
import prayer_library
import review_checks
import service_rubric
from db import session_scope
from domain_errors import Busy, DomainError, NotConfigured, RateLimited, UpstreamError, UpstreamTimeout
from integrations import openai_client
from liturgy_config import SECTION_LABELS, SECTION_ORDER
from repos import churches
from review_checks import Note

logger = logging.getLogger(__name__)

REVIEW_BUDGET_S = 75.0                 # F §1.8: the review's server deadline, from the start of the usecase
REVIEW_MAX_COMPLETION_TOKENS = 2000
MAX_CARD_CHARS = 4000                  # each card's text as the review sees it (the card is untouched)
MIN_CARD_CHARS = 200                   # the budget never cuts a card below this
MAX_NOTE_CHARS = 240
MAX_NOTES_PER_CARD = 3
MAX_SERVICE_NOTES = 3
AI_STATUSES = ("ok", "not_configured", "busy", "timeout", "rate_limited", "error")

ROLE = (
    "You are a tough, fair liturgical editor for a moderate Reformed (PC(USA)) congregation. "
    "You read a whole worship service and point out problems in its prayers. You never rewrite "
    "the prayers: you leave short notes, and the pastor decides what to do with them."
)
RULES_INTRO = "The prayers were written under these standing rules, the church's instructions to its writer:\n"
SEASON_INTRO = "Season language is judged by feel, not by count. The writer's rule: "
SEASON_FLAG = " Flag canned or repetitive seasonal language, not seasonal themes."
CHECKS = (
    "Check each prayer for: the church's checklist for its section, the standing rules, the pastor's voice, "
    "how it reads aloud, its theology, and repetition across the service."
)
CHECKLISTS_INTRO = "The church's checklists:\n"
VOICE_INTRO = "The pastor's voice, from the church's voice profile:\n"
NO_VOICE = "There is no voice profile, so skip the Voice check: never use the voice tag."
CONTRACT = (
    "Answer with one JSON object and nothing else: "
    '{"cards": [{"section": key, "notes": [{"tag": t, "text": s}]}], "service_notes": [{"tag": t, "text": s}]}. '
    "Each tag is one of checklist, rules, voice, read_aloud, theology, repetition. Give at most 3 notes per "
    "card, most important first, and at most 3 service_notes, for problems that involve more than one prayer. "
    "Each note is one sentence of 240 characters or fewer that names the specific phrase at issue. "
    "Give a card an empty notes list when it is fine."
)
ORIGIN_LABELS = {
    "ai": "an AI draft",
    "typed": "typed by the pastor",
    "archive": "from a saved service",
    "default": "the church's default",
}
CODE_NOTES_INTRO = "Notes already found by code. Do not repeat them:\n"
CARDS_INTRO = "The prayers, in service order:"


@dataclass(frozen=True)
class ReviewCard:
    section: str          # a SectionKey
    origin: str           # "ai", "typed", "archive" or "default"
    text: str


@dataclass(frozen=True)
class CardNotes:
    section: str
    notes: tuple[Note, ...]


@dataclass(frozen=True)
class ReviewOutcome:
    cards: tuple[CardNotes, ...]          # one per reviewed card, in request order
    service_notes: tuple[Note, ...]
    ai_status: str                        # one of AI_STATUSES


@dataclass(frozen=True)
class ReviewPrompt:
    messages: list[dict[str, str]]
    dropped: tuple[str, ...]              # "profile", "sermon", "cards": what the budget left out or cut


class _Unusable(Exception):
    """The AI's answer is not a JSON object: an AI failure ("error")."""


def _readings(scriptures: Sequence[str]) -> str:
    lines = [" ".join(s.split())[:200] for s in scriptures if s and s.strip()]
    return "Readings:\n" + "\n".join(f"- {line}" for line in lines) if lines else "Readings: None specified."


def build_review_prompt(cards: Sequence[ReviewCard], *, system_prompt: str, rubric: Mapping[str, Any],
                        profile: str, occasion: str, scriptures: Sequence[str],
                        sermon: Optional[tuple[str, str]],
                        code_notes: Mapping[str, Sequence[Note]],
                        service_notes: Sequence[Note]) -> Optional[ReviewPrompt]:
    """The review's [system, user] messages within MAX_PROMPT_CHARS, or None
    when even the church's own text and the shortest cards do not fit."""
    checklists = service_rubric.merge_rubric(dict(rubric) if rubric else None)["prayers"]
    present = [c.section for c in cards]
    blocks = [service_rubric.format_checklist(SECTION_LABELS[key], list(checklists[key]))
              for key in SECTION_ORDER if key in present and checklists.get(key)]
    profile = (profile or "").strip()[:prayer_library.MAX_PROFILE_CHARS]
    sermon_block = liturgy_prompts.sermon_text_block(*(sermon or (None, None)))
    texts = {c.section: (c.text or "")[:MAX_CARD_CHARS] for c in cards}
    noted = [f"- {key}: {n.text}" for key in present for n in code_notes.get(key, ())]
    noted += [f"- across the service: {n.text}" for n in service_notes]
    dropped: list[str] = []

    def build() -> list[dict[str, str]]:
        system = "\n\n".join(filter(None, [
            ROLE,
            RULES_INTRO + system_prompt,
            SEASON_INTRO + liturgy_prompts.SEASON_GUIDANCE + SEASON_FLAG,
            CHECKS,
            CHECKLISTS_INTRO + "\n\n".join(blocks) if blocks else "",
            VOICE_INTRO + profile if profile else NO_VOICE,
            CONTRACT,
        ]))
        listed = "\n\n".join(f"[{c.section}] {SECTION_LABELS[c.section]} ({ORIGIN_LABELS[c.origin]}):\n"
                             f"{texts[c.section]}" for c in cards)
        user = "\n\n".join(filter(None, [
            "Occasion: " + (" ".join(occasion.split())[:300] or "Not given."),
            _readings(scriptures),
            sermon_block,
            CARDS_INTRO + "\n\n" + listed,
            CODE_NOTES_INTRO + "\n".join(noted) if noted else "",
        ]))
        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def size(messages: list[dict[str, str]]) -> int:
        return sum(len(m["content"]) for m in messages)

    messages = build()
    if size(messages) > liturgy_prompts.MAX_PROMPT_CHARS and profile:
        profile = ""
        dropped.append("profile")
        messages = build()
    if size(messages) > liturgy_prompts.MAX_PROMPT_CHARS and sermon_block:
        sermon_block = ""
        dropped.append("sermon")
        messages = build()
    while (over := size(messages) - liturgy_prompts.MAX_PROMPT_CHARS) > 0:
        longest = max(texts, key=lambda key: len(texts[key]))
        if len(texts[longest]) <= MIN_CARD_CHARS:
            return None
        texts[longest] = texts[longest][:max(MIN_CARD_CHARS, len(texts[longest]) - over)]
        if "cards" not in dropped:
            dropped.append("cards")
        messages = build()
    return ReviewPrompt(messages=messages, dropped=tuple(dropped))


def _tag(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    tag = "_".join(value.strip().lower().replace("-", " ").split())
    return tag if tag in review_checks.TAGS else None


def _ai_note(raw: Any, *, voice: bool) -> Optional[Note]:
    if not isinstance(raw, Mapping):
        return None
    tag, text = _tag(raw.get("tag")), raw.get("text")
    if tag is None or (tag == "voice" and not voice) or not isinstance(text, str):
        return None
    text = " ".join(text.split())[:MAX_NOTE_CHARS].rstrip()
    return Note(tag, text, "ai") if text else None


def parse_review(raw: str, sections: Sequence[str], *, voice: bool) -> tuple[dict[str, list[Note]], list[Note]]:
    """The AI's notes per reviewed section and across the service. Raises
    _Unusable for an answer that is not a JSON object."""
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError, TypeError):
        raise _Unusable() from None
    if not isinstance(data, dict):
        raise _Unusable()
    per_card: dict[str, list[Note]] = {key: [] for key in sections}
    items = data.get("cards")
    for item in items if isinstance(items, list) else []:
        if isinstance(item, Mapping) and item.get("section") in per_card:
            notes = item.get("notes")
            for raw_note in notes if isinstance(notes, list) else []:
                note = _ai_note(raw_note, voice=voice)
                if note is not None:
                    per_card[item["section"]].append(note)
    service = data.get("service_notes")
    across = [n for n in (_ai_note(r, voice=voice) for r in (service if isinstance(service, list) else []))
              if n is not None]
    return per_card, across


def merge_notes(code: Sequence[Note], ai: Sequence[Note], limit: int) -> tuple[Note, ...]:
    """Code notes first; an AI note containing a code note's quoted text (any case) is a repeat."""
    matches = [n.match.lower() for n in code if n.match]
    kept = [n for n in ai if not any(m in n.text.lower() for m in matches)]
    return tuple([*code, *kept][:limit])


def review_service(*, church_id: uuid.UUID, user_id: uuid.UUID, occasion: str, scriptures: Sequence[str],
                   cards: Sequence[ReviewCard], sermon: Optional[tuple[str, str]] = None,
                   charge: Callable[[int], None] = lambda n: None, ai: Any = openai_client,
                   clock: Callable[[], float] = time.monotonic) -> ReviewOutcome:
    """The notes for each card and across the service (see the module docstring).
    user_id is for the rate limit only (the route's charge)."""
    started = clock()
    deadline = started + REVIEW_BUDGET_S
    sections = [c.section for c in cards]
    code = {c.section: review_checks.check_card(c.text) for c in cards}
    code_service = review_checks.check_openings([c.text for c in cards])
    facts: dict[str, Any] = {"church": church_id, "cards": len(cards),
                             "code_notes": sum(map(len, code.values())) + len(code_service), "ai": 0}
    ai_notes: dict[str, list[Note]] = {key: [] for key in sections}
    ai_service: list[Note] = []
    try:
        status = _ask_ai(church_id, occasion, scriptures, cards, sermon, code, code_service, charge, ai,
                         deadline, facts, ai_notes, ai_service)
    except DomainError as exc:
        _log(facts, started, clock, ai_status="-", outcome=exc.code)
        raise
    except Exception:
        _log(facts, started, clock, ai_status="-", outcome="internal_error")
        raise
    outcome = ReviewOutcome(
        cards=tuple(CardNotes(key, merge_notes(code[key], ai_notes[key], MAX_NOTES_PER_CARD)) for key in sections),
        service_notes=merge_notes(code_service, ai_service, MAX_SERVICE_NOTES),
        ai_status=status,
    )
    facts["notes"] = sum(len(c.notes) for c in outcome.cards) + len(outcome.service_notes)
    _log(facts, started, clock, ai_status=status, outcome="ok")
    return outcome


def _ask_ai(church_id, occasion, scriptures, cards, sermon, code, code_service, charge, ai, deadline,
            facts, ai_notes, ai_service) -> str:
    if not ai.ai_available():
        return "not_configured"
    with session_scope() as s:                                   # read, then close (F §1.8)
        stored = churches.get_church_prompts(church_id, session=s)
        rubric = churches.get_church_rubric_overrides(church_id, session=s)
        church = churches.get_church(church_id, session=s)
        library = prayer_library.read_library((church or {}).get("settings"))
    prompt = build_review_prompt(
        cards, system_prompt=liturgy_prompts.merge_prompts(stored)["system"], rubric=rubric,
        profile=library.voice_profile, occasion=occasion, scriptures=scriptures, sermon=sermon,
        code_notes=code, service_notes=code_service)
    facts.update(rubric="custom" if rubric else "default", sermon="yes" if sermon else "no",
                 voice="profile" if library.voice_profile.strip() else "none")
    if prompt is None:
        facts["dropped"] = "too_long"
        return "error"
    facts["dropped"] = ",".join(prompt.dropped) or "-"
    try:
        charge(1)                                                # only when the AI is called
    except RateLimited:
        return "rate_limited"
    facts["ai"] = 1
    if logger.isEnabledFor(logging.DEBUG):                       # prompts at DEBUG only (F §2.5)
        logger.debug("liturgy.review messages=%r", prompt.messages)
    try:
        raw = ai.complete(prompt.messages, max_completion_tokens=REVIEW_MAX_COMPLETION_TOKENS,
                          json_mode=True, deadline=deadline)
    except NotConfigured:
        return "not_configured"
    except Busy:
        return "busy"
    except UpstreamTimeout:
        return "timeout"
    except UpstreamError:
        return "error"
    except Exception:
        logger.exception("liturgy.review unexpected error")
        return "error"
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("liturgy.review answer=%r", raw)
    voice = "profile" not in prompt.dropped and bool(library.voice_profile.strip())
    try:
        per_card, across = parse_review(raw if isinstance(raw, str) else "", [c.section for c in cards],
                                        voice=voice)
    except _Unusable:
        logger.warning("liturgy.review unusable answer chars=%d", len(raw) if isinstance(raw, str) else 0)
        return "error"
    for key, notes in per_card.items():
        ai_notes[key].extend(notes)
    ai_service.extend(across)
    return "ok"


def _log(facts: Mapping[str, Any], started: float, clock: Callable[[], float], *, ai_status: str,
         outcome: str) -> None:
    """One line per call: never a prompt, a card's text, a note or an answer."""
    details = " ".join(f"{key}={value}" for key, value in facts.items())
    logger.info("liturgy.review %s ai_status=%s duration_ms=%d outcome=%s", details, ai_status,
                round((clock() - started) * 1000), outcome)
````

- [ ] **Step 4 (agent): Run the file three times, the import gate, and the suite**

```bash
for i in 1 2 3; do .venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -1; done
.venv/bin/python -m pytest -q backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `10 passed in <t>s` three times; `3 passed in <t>s`; `1200 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/usecases/liturgy_review.py backend/tests/test_usecase_liturgy_review.py backend/tests/test_no_streamlit_in_core.py
git commit -q -m "Reviewer: the AI review usecase (R Layer 2; S4 reviewer amendment; F 1.5, 1.8)" -m "Code notes always; the AI review when it can run, inside a 75 s deadline,
with the church's system prompt, the present sections' checklists and the
voice profile read in one session closed before the call. The prompt
stays under 24 000 characters (profile, then sermon text, then the longest
card). The ai bucket is charged 1 only when the AI is called; an empty
bucket, an AI failure or invalid JSON keeps the code notes and says why in
ai_status. Tolerant parsing, then code notes first and no repeats." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 3: backend **1200 passed, 11 skipped**; frontend **539 in 75**.

### Task 4: Revise with these notes, `usecases/liturgy_review.revise_section` (R "Revise" and its Budget, Testing "Revise"; S4 reviewer amendment "Revise input budget", "Timeouts"; F §2.8; owner answer 3; clarifications 12, 13)

One `complete()` call: the system message is the church's merged system prompt with the voice profile appended in the writer's words (PR #7); the user message is the section label, its checklist, the occasion and readings, the sermon text, the current draft, the notes and R's instruction. The section's slice 4 token budget (1 500, or 4 000 for Prayers of the People) and per-attempt timeout (60 s for Prayers of the People) apply, inside the same 80 s deadline as generation (`usecases.liturgy.GENERATE_BUDGET_S`; owner answer 3). Over the cap the profile goes first, then the sermon text, then the checklist; then 422 `prompt_invalid` "This prayer is too long to revise." with no AI call. AI failures are raised with this app's messages, so the route returns them as HTTP statuses.

**Files:**
- Create: `backend/tests/test_usecase_liturgy_revise.py`
- Modify: `backend/usecases/liturgy_review.py`

**Interfaces:**
- Consumes: T3's module (`ReviewPrompt`, `_readings`); `usecases.liturgy.GENERATE_BUDGET_S`; `liturgy_config.SECTIONS_BY_KEY` (`max_completion_tokens`, `timeout_seconds`), `LIMITS`; `liturgy_prompts.VOICE_PROFILE_INTRO`; `openai_client.NOT_CONFIGURED_MESSAGE`, `BUSY_MESSAGE`, `TIMEOUT_MESSAGE`, `UPSTREAM_MESSAGE`; `domain_errors.InvalidInput`.
- Produces (later user: T5):
  - `revise_section(*, church_id, user_id, section, text, notes, occasion, scriptures, sermon=None, ai=openai_client, clock=time.monotonic) -> str` (stripped); raises `NotConfigured` (503 `ai_not_configured`), `Busy` (503 `ai_busy`), `UpstreamTimeout` (504 `ai_timeout`), `UpstreamError` (502 `ai_upstream_error`, also for an empty answer, one over 20 000 characters, or any unexpected error, which is logged with its stack) and `InvalidInput(code="prompt_invalid")` (422)
  - `build_revise_prompt(...) -> ReviewPrompt`, `REVISE_INSTRUCTION`, `TOO_LONG_TO_REVISE`, `REVISE_BUDGET_S = 80.0`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_usecase_liturgy_revise.py`:**

````python
"""usecases.liturgy_review.revise_section (reviewer spec, "Revise" and its
Budget, Testing; slice 4 spec, reviewer amendment "Revise input budget").
SQLite `tmp_db`, and a FakeAI passed as `ai=`."""
import logging
import uuid

import pytest

import liturgy_prompts as lp
from domain_errors import Busy, DomainError, InvalidInput, NotConfigured, UpstreamError, UpstreamTimeout
from integrations.openai_client import FakeAI
from repos import churches
from usecases import liturgy_review

SECRET = "sk-secret upstream detail"
NOTES = ['Stock phrase "as we journey". Say it more naturally.', "The second line is hard to say aloud."]
INSTRUCTION = ("Revise this draft to address these notes only. Keep everything that works. Keep the same form "
               "(Leader/People lines where present) and about the same length. Output only the revised text.")


@pytest.fixture
def church(make_church):
    return make_church(name="Grace")


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def revise(church_id, section="opening_prayer", text="Gracious God, as we journey, hear us. Amen.", notes=NOTES,
           ai=None, **kw):
    kw.setdefault("occasion", "Third Sunday of Easter")
    kw.setdefault("scriptures", ["Acts 9:1-6", "John 21:1-19"])
    return liturgy_review.revise_section(church_id=church_id, user_id=uuid.uuid4(), section=section, text=text,
                                         notes=notes, ai=ai if ai is not None else FakeAI(reply=" Revised. "), **kw)


def test_the_messages_carry_the_draft_the_notes_and_the_section_s_checklist(church):
    churches.set_church_prompts(church, {"system": "Our voice."})
    set_settings(church, rubric={"prayers": {"opening_prayer": ["names one hope"]}},
                 prayer_library={"prayers": [], "voice_profile": " Plain and warm. "})
    ai = FakeAI(reply="  Gracious God, hear us. Amen.\n")
    text = revise(church, ai=ai, sermon=("Mark 4:35-41", "S" * 3000))
    assert text == "Gracious God, hear us. Amen."
    (call,) = ai.calls
    system, user = (m["content"] for m in call["messages"])
    assert system == "Our voice.\n\nWrite in the voice of this church's pastor, described here:\nPlain and warm."
    assert user == (
        "Section: Opening Prayer\n\n"
        "A good Opening Prayer:\n- names one hope\n\n"
        "Occasion: Third Sunday of Easter\n\n"
        "Readings:\n- Acts 9:1-6\n- John 21:1-19\n\n"
        "Sermon text (Mark 4:35-41), for themes only; do not quote, cite, or name it:\n" + "S" * 2000 + "\n\n"
        "Current draft:\nGracious God, as we journey, hear us. Amen.\n\n"
        "Notes:\n"
        '- Stock phrase "as we journey". Say it more naturally.\n'
        "- The second line is hard to say aloud.\n\n" + INSTRUCTION)
    assert call["json_mode"] is False
    # With the defaults (no prompts, rubric or profile saved) the system prompt is the default one.
    churches.set_church_prompts(church, {})
    set_settings(church, rubric={}, prayer_library={"prayers": [], "voice_profile": ""})
    revise(church, ai=ai)
    assert ai.calls[1]["messages"][0]["content"] == lp.DEFAULT_SYSTEM_PROMPT
    assert "A good Opening Prayer:\n- " in ai.calls[1]["messages"][1]["content"]


def test_each_section_gets_its_slice_4_token_budget_and_the_80_s_deadline(church):
    for section in lp.SECTION_ORDER:
        ai = FakeAI(reply="Revised.")
        revise(church, section=section, ai=ai, clock=lambda: 500.0)
        (call,) = ai.calls
        pop = section == "prayers_of_the_people"
        assert call["max_completion_tokens"] == (4000 if pop else 1500), section
        assert call["deadline"] == 580.0, section
        assert call.get("timeout_seconds") == (60.0 if pop else None), section


def test_ai_failures_raise_their_codes_with_this_app_s_messages(church, caplog):
    cases = [
        (FakeAI(available=False), "ai_not_configured", 503, "AI isn't set up on this app yet."),
        (FakeAI(error=NotConfigured(SECRET, code="ai_not_configured")), "ai_not_configured", 503,
         "AI isn't set up on this app yet."),
        (FakeAI(error=Busy(SECRET, code="ai_busy")), "ai_busy", 503, "The AI service is busy. Try again in a minute."),
        (FakeAI(error=UpstreamTimeout(SECRET, code="ai_timeout")), "ai_timeout", 504,
         "The AI took too long to answer. Try again."),
        (FakeAI(error=UpstreamError(SECRET, code="ai_upstream_error")), "ai_upstream_error", 502,
         "The AI service had a problem. Try again."),
        (FakeAI(error=RuntimeError(SECRET)), "ai_upstream_error", 502, "The AI service had a problem. Try again."),
        (FakeAI(reply="   "), "ai_upstream_error", 502, "The AI service had a problem. Try again."),
        (FakeAI(reply="x" * 20_001), "ai_upstream_error", 502, "The AI service had a problem. Try again."),
    ]
    for ai, code, status, message in cases:
        with pytest.raises(DomainError) as raised:
            revise(church, ai=ai)
        assert (raised.value.code, raised.value.status, raised.value.message) == (code, status, message), code
    assert "RuntimeError" in caplog.text and SECRET not in str(raised.value)
    assert revise(church, ai=FakeAI(reply="y" * 20_000)) == "y" * 20_000


def test_the_budget_drops_the_profile_then_the_sermon_then_the_checklist_then_refuses(church):
    churches.set_church_prompts(church, {"system": "s" * 8000})
    set_settings(church, rubric={"prayers": {"prayers_of_the_people": [f"{i:02d}" + "c" * 298 for i in range(12)]}},
                 prayer_library={"prayers": [], "voice_profile": "v" * 2000})
    sermon = ("Mark 4:35-41", "x" * 2000)
    # 8 000 system + 2 000 profile + about 3 700 checklist + 2 000 sermon + the draft: each case's draft
    # length leaves the prompt over the cap until the named blocks are gone.
    cases = [(6_000, ()), (8_000, ("profile",)), (10_000, ("profile", "sermon")),
             (13_000, ("profile", "sermon", "checklist"))]
    for draft_chars, dropped in cases:
        ai = FakeAI(reply="Revised.")
        revise(church, section="prayers_of_the_people", text="d" * draft_chars, ai=ai, sermon=sermon)
        system, user = (m["content"] for m in ai.calls[0]["messages"])
        assert len(system) + len(user) <= lp.MAX_PROMPT_CHARS, dropped
        assert ("v" * 2000 in system) is ("profile" not in dropped), dropped
        assert ("Sermon text (Mark 4:35-41)" in user) is ("sermon" not in dropped), dropped
        assert ("A good Prayers of the People:" in user) is ("checklist" not in dropped), dropped
        assert "d" * draft_chars in user and user.endswith(INSTRUCTION)
    # S4's example: an 8 000-character system prompt and a 20 000-character draft never reach the AI.
    ai = FakeAI(reply="Revised.")
    with pytest.raises(InvalidInput) as raised:
        revise(church, section="prayers_of_the_people", text="d" * 20_000, ai=ai, sermon=sermon)
    assert (raised.value.code, raised.value.status, raised.value.message) == (
        "prompt_invalid", 422, "This prayer is too long to revise.")
    assert ai.calls == []


def test_the_info_line_carries_no_prayer_text_or_notes(church, caplog):
    with caplog.at_level(logging.INFO, logger="usecases.liturgy_review"):
        revise(church, text="SECRET-TEXT", notes=["SECRET-NOTE"], ai=FakeAI(reply="SECRET-ANSWER"),
               occasion="SECRET-OCCASION")
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.revise" in info and " section=opening_prayer notes=1 " in info and "outcome=ok" in info
    assert "SECRET" not in info
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_revise.py 2>&1 | tail -2
```

**Expected:** `FAILED backend/tests/test_usecase_liturgy_revise.py::test_the_info_line_carries_no_prayer_text_or_notes - AttributeError: module 'usecases.liturgy_review' has no attribute 'revise_section'`, then `5 failed in <t>s`.

- [ ] **Step 3 (agent): Add Revise to the module**

**In `backend/usecases/liturgy_review.py`, replace:**

````python
Logs one `liturgy.review` INFO line per call; prompts, cards and answers only
at DEBUG (F §2.5). Writes nothing. No FastAPI, Starlette or Streamlit here
(tests/test_no_streamlit_in_core.py).
````

**with:**

````python
revise_section: one complete() call that edits an AI draft to address the
notes left on it and keeps the rest. The system message is the church's
merged system prompt with the voice profile appended (as the writer gets
it); the user message is the section, its checklist, the occasion and
readings, the sermon text, the draft, the notes and the instruction. The
section's slice 4 token budget and per-attempt timeout apply, inside the same
80 s deadline as generation (usecases.liturgy.GENERATE_BUDGET_S). Over
MAX_PROMPT_CHARS the voice profile goes first, then the sermon text, then the
checklist; a draft still too long with only the fixed instructions is 422
prompt_invalid "This prayer is too long to revise." with no AI call. AI
failures are raised as their HTTP errors (503, 504, 502) with this app's
messages, like /hymns/suggestions.

Logs one `liturgy.review` or `liturgy.revise` INFO line per call; prompts,
cards, notes and answers only at DEBUG (F §2.5). Writes nothing. No FastAPI,
Starlette or Streamlit here (tests/test_no_streamlit_in_core.py).
````

**In `backend/usecases/liturgy_review.py`, replace:**

````python
from domain_errors import Busy, DomainError, NotConfigured, RateLimited, UpstreamError, UpstreamTimeout
from integrations import openai_client
from liturgy_config import SECTION_LABELS, SECTION_ORDER
from repos import churches
from review_checks import Note
````

**with:**

````python
from domain_errors import (Busy, DomainError, InvalidInput, NotConfigured, RateLimited, UpstreamError,
                           UpstreamTimeout)
from integrations import openai_client
from liturgy_config import LIMITS, SECTION_LABELS, SECTION_ORDER, SECTIONS_BY_KEY
from repos import churches
from review_checks import Note
from usecases.liturgy import GENERATE_BUDGET_S
````

**Append to `backend/usecases/liturgy_review.py`:**

````python


# --- Revise with these notes (reviewer spec, "Revise" and its Budget) ---

REVISE_INSTRUCTION = (
    "Revise this draft to address these notes only. Keep everything that works. Keep the same form "
    "(Leader/People lines where present) and about the same length. Output only the revised text."
)
TOO_LONG_TO_REVISE = "This prayer is too long to revise."
REVISE_BUDGET_S = GENERATE_BUDGET_S       # 80 s from the start of the usecase, as a generated section
MAX_ANSWER_CHARS = LIMITS.max_section_text


def build_revise_prompt(section: str, text: str, notes: Sequence[str], *, system_prompt: str,
                        rubric: Mapping[str, Any], profile: str, occasion: str, scriptures: Sequence[str],
                        sermon: Optional[tuple[str, str]]) -> ReviewPrompt:
    """Revise's [system, user] messages within MAX_PROMPT_CHARS. Raises
    InvalidInput(prompt_invalid) when the draft and the fixed instructions alone are too long."""
    label = SECTION_LABELS[section]
    points = service_rubric.merge_rubric(dict(rubric) if rubric else None)["prayers"].get(section) or []
    blocks = {
        "profile": (profile or "").strip()[:prayer_library.MAX_PROFILE_CHARS],
        "sermon": liturgy_prompts.sermon_text_block(*(sermon or (None, None))),
        "checklist": service_rubric.format_checklist(label, list(points)) if points else "",
    }
    blocks = {name: block for name, block in blocks.items() if block}
    listed = "\n".join(f"- {' '.join(note.split())}" for note in notes)
    dropped: list[str] = []
    while True:
        system = system_prompt + ("\n\n" + liturgy_prompts.VOICE_PROFILE_INTRO + blocks["profile"]
                                  if "profile" in blocks else "")
        user = "\n\n".join(filter(None, [
            f"Section: {label}",
            blocks.get("checklist", ""),
            "Occasion: " + (" ".join(occasion.split())[:300] or "Not given."),
            _readings(scriptures),
            blocks.get("sermon", ""),
            "Current draft:\n" + text,
            "Notes:\n" + listed,
            REVISE_INSTRUCTION,
        ]))
        if len(system) + len(user) <= liturgy_prompts.MAX_PROMPT_CHARS:
            return ReviewPrompt(messages=[{"role": "system", "content": system},
                                          {"role": "user", "content": user}], dropped=tuple(dropped))
        name = next((n for n in ("profile", "sermon", "checklist") if n in blocks), None)
        if name is None:
            raise InvalidInput(TOO_LONG_TO_REVISE, code="prompt_invalid")
        del blocks[name]
        dropped.append(name)


def revise_section(*, church_id: uuid.UUID, user_id: uuid.UUID, section: str, text: str, notes: Sequence[str],
                   occasion: str, scriptures: Sequence[str], sermon: Optional[tuple[str, str]] = None,
                   ai: Any = openai_client, clock: Callable[[], float] = time.monotonic) -> str:
    """The revised draft, stripped (see the module docstring). user_id is for
    the rate limit only, which the route's dependency has already charged."""
    started = clock()
    facts: dict[str, Any] = {"church": church_id, "section": section, "notes": len(notes)}
    try:
        revised = _revise(church_id, section, text, notes, occasion, scriptures, sermon, ai,
                          started + REVISE_BUDGET_S, facts)
    except DomainError as exc:
        _log_revise(facts, started, clock, outcome=exc.code)
        raise
    except Exception:
        _log_revise(facts, started, clock, outcome="internal_error")
        raise
    _log_revise(facts, started, clock, outcome="ok")
    return revised


def _revise(church_id, section, text, notes, occasion, scriptures, sermon, ai, deadline, facts) -> str:
    if not ai.ai_available():
        raise NotConfigured(openai_client.NOT_CONFIGURED_MESSAGE, code="ai_not_configured")
    with session_scope() as s:                                   # read, then close (F §1.8)
        stored = churches.get_church_prompts(church_id, session=s)
        rubric = churches.get_church_rubric_overrides(church_id, session=s)
        church = churches.get_church(church_id, session=s)
        library = prayer_library.read_library((church or {}).get("settings"))
    facts.update(rubric="custom" if rubric else "default", sermon="yes" if sermon else "no",
                 voice="profile" if library.voice_profile.strip() else "none")
    prompt = build_revise_prompt(section, text, notes, system_prompt=liturgy_prompts.merge_prompts(stored)["system"],
                                 rubric=rubric, profile=library.voice_profile, occasion=occasion,
                                 scriptures=scriptures, sermon=sermon)
    facts["dropped"] = ",".join(prompt.dropped) or "-"
    spec = SECTIONS_BY_KEY[section]
    extra = {} if spec.timeout_seconds is None else {"timeout_seconds": spec.timeout_seconds}
    if logger.isEnabledFor(logging.DEBUG):                       # prompts at DEBUG only (F §2.5)
        logger.debug("liturgy.revise section=%s messages=%r", section, prompt.messages)
    try:
        answer = ai.complete(prompt.messages, max_completion_tokens=spec.max_completion_tokens,
                             deadline=deadline, **extra)
    except NotConfigured:
        raise NotConfigured(openai_client.NOT_CONFIGURED_MESSAGE, code="ai_not_configured") from None
    except Busy:
        raise Busy(openai_client.BUSY_MESSAGE, code="ai_busy") from None
    except UpstreamTimeout:
        raise UpstreamTimeout(openai_client.TIMEOUT_MESSAGE, code="ai_timeout") from None
    except UpstreamError:
        raise UpstreamError(openai_client.UPSTREAM_MESSAGE, code="ai_upstream_error") from None
    except Exception:
        logger.exception("liturgy.revise section=%s unexpected error", section)
        raise UpstreamError(openai_client.UPSTREAM_MESSAGE, code="ai_upstream_error") from None
    answer = answer.strip() if isinstance(answer, str) else ""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("liturgy.revise section=%s answer=%r", section, answer)
    if not answer or len(answer) > MAX_ANSWER_CHARS:
        logger.warning("liturgy.revise section=%s unusable answer chars=%d", section, len(answer))
        raise UpstreamError(openai_client.UPSTREAM_MESSAGE, code="ai_upstream_error")
    return answer


def _log_revise(facts: Mapping[str, Any], started: float, clock: Callable[[], float], *, outcome: str) -> None:
    """One line per call: never a prompt, the draft, a note or an answer."""
    details = " ".join(f"{key}={value}" for key, value in facts.items())
    logger.info("liturgy.revise %s duration_ms=%d outcome=%s", details, round((clock() - started) * 1000), outcome)
````

- [ ] **Step 4 (agent): Run both usecase files and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_usecase_liturgy_revise.py backend/tests/test_usecase_liturgy_review.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
```

**Expected:** `15 passed in <t>s`; `1205 passed, 11 skipped in <t>s`.

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/usecases/liturgy_review.py backend/tests/test_usecase_liturgy_revise.py
git commit -q -m "Reviewer: revise a draft with its notes (R Revise; S4 reviewer amendment; owner answer 3)" -m "One AI call with the church's system prompt and voice profile, the
section's checklist, the context, the draft, the notes and R's
instruction; the section's slice 4 token budget and attempt timeout inside
generation's 80 s deadline. Over 24 000 characters the profile, then the
sermon text, then the checklist go; still too long is 422 prompt_invalid
'This prayer is too long to revise.' with no AI call." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 4: backend **1205 passed, 11 skipped**; frontend **539 in 75**.

### Task 5: `POST /liturgy/review` and `POST /liturgy/revise` (R API, Testing "Routes"; S4 reviewer amendment "Routes", "Consistency with F", "Tenancy"; F §1.2, §1.3, §1.5, §1.8, §1.11; clarifications 14, 15, 16)

Two thin plain-`def` routes in `api/routes/liturgy_review.py`, request models at the top with `extra="forbid"` and the shared `SermonText`. Review is church-scoped with no rate-limit dependency: the usecase charges through `charge` only when it calls the AI, and always answers 200 once the body is valid. Revise is church-scoped with `rate_limit("ai")` (cost 1, charged before validation as on `/hymns/suggestions`) and returns AI failures as HTTP statuses. The OpenAPI snapshot and the frontend's generated types are regenerated (F §1.11), so T6 can name the new types. Neither route is user-scoped, so `test_route_guards.py` is unchanged.

**Files:**
- Create: `backend/api/routes/liturgy_review.py`, `backend/tests/test_api_liturgy_review.py`
- Modify: `backend/api/main.py`, `backend/tests/test_api_app.py`, `frontend/src/lib/api/openapi.json` and `frontend/src/lib/api/schema.d.ts` (regenerated, never hand-edited)

**Interfaces:**
- Consumes: T3 (`review_service`, `ReviewCard`), T4 (`revise_section`); `api.schemas.SectionKey`, `SermonText`; `api.ratelimit.consume`, `rate_limit`; `api.deps.require_church`, `get_current_user`; `api.errors.error_responses`.
- Produces (later users: T6 and the frontend):
  - `POST /liturgy/review`: body `ReviewIn {occasion ≤300 = "", scriptures ≤20 × ≤200 = [], sermon_text?: SermonText, cards: [ReviewCardIn {section: SectionKey, origin: "ai"|"typed"|"archive"|"default", text ≤20 000}] (1-8, one per section)}`; 200 `ReviewOut {cards: [CardNotesOut {section, notes: [NoteOut]}], service_notes: [NoteOut], ai_status}`; `NoteOut {tag, text, source: "code"|"ai"}`; errors 401, 403, 422, 503 (`auth_unavailable`), 500
  - `POST /liturgy/revise`: body `ReviseIn {section, text ≤20 000, notes: [≤240] (1-3), occasion, scriptures, sermon_text?}`; 200 `ReviseOut {text}`; errors 401, 403, 422 (`invalid_request`, or `prompt_invalid` "This prayer is too long to revise."), 429 (`Retry-After`), 502, 503, 504, 500

- [ ] **Step 1 (agent): Write the failing tests**

**Create `backend/tests/test_api_liturgy_review.py`:**

````python
"""POST /liturgy/review and POST /liturgy/revise (reviewer spec, API and Testing
"Routes"; slice 4 spec, reviewer amendment). The AI is a FakeAI
(integrations.openai_client.set_ai_for_tests)."""
import json
import logging
import uuid

import pytest

from api import ratelimit
from domain_errors import Busy, UpstreamError, UpstreamTimeout
from integrations import openai_client
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
STOCK = 'Stock phrase "as we journey". Say it more naturally.'
CARDS = [
    {"section": "call_to_worship", "origin": "typed", "text": "Leader: Gracious God, as we journey, we come."},
    {"section": "opening_prayer", "origin": "ai", "text": "Gracious God, we praise you. Amen."},
]
REVISE = {"section": "opening_prayer", "text": "Gracious God, as we journey, hear us.", "notes": [STOCK],
          "occasion": "Third Sunday of Easter", "scriptures": ["Acts 9:1-6"]}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Grace", owner_user_id=owner)


def install(reply='{"cards": [], "service_notes": []}', **kw):
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def set_settings(church_id, **values):
    settings = dict(churches.get_church(church_id)["settings"] or {})
    settings.update(values)
    churches.update_church(church_id, settings=settings)


def post(client, path, church_id, body, email=EMAIL, status=200):
    r = client.post(path, json=body, headers=church_headers(email, church_id))
    assert r.status_code == status, r.text
    return r.json()


def test_review_without_ai_returns_the_code_notes_in_a_200(client, church):
    body = post(client, "/liturgy/review", church, {"occasion": "Easter", "cards": CARDS})
    assert body == {
        "cards": [
            {"section": "call_to_worship", "notes": [{"tag": "rules", "text": STOCK, "source": "code"}]},
            {"section": "opening_prayer", "notes": []},
        ],
        "service_notes": [{"tag": "repetition", "text": 'Several prayers open with "Gracious God".', "source": "code"}],
        "ai_status": "not_configured",
    }


def test_review_with_the_ai_merges_its_notes_and_an_empty_bucket_is_still_a_200(client, church, owner,
                                                                                 limiter_clock):
    ai = install(json.dumps({"cards": [{"section": "opening_prayer",
                                        "notes": [{"tag": "theology", "text": "Praise is not a payment."}]}],
                             "service_notes": []}))
    for _ in range(39):                                          # one ai token left
        ratelimit.consume("ai", user_id=owner, church_id=church)
    body = post(client, "/liturgy/review", church, {"cards": CARDS})
    assert body["ai_status"] == "ok" and len(ai.calls) == 1
    assert body["cards"][1]["notes"] == [{"tag": "theology", "text": "Praise is not a payment.", "source": "ai"}]
    body = post(client, "/liturgy/review", church, {"cards": CARDS})         # the bucket is empty: no 429
    assert body["ai_status"] == "rate_limited" and len(ai.calls) == 1
    assert body["cards"][0]["notes"] == [{"tag": "rules", "text": STOCK, "source": "code"}]
    limiter_clock.advance(15)
    assert post(client, "/liturgy/review", church, {"cards": CARDS})["ai_status"] == "ok"


def test_both_routes_need_a_token_and_a_membership(client, church, isolation_world, make_user):
    install()
    for path, body in (("/liturgy/review", {"cards": CARDS}), ("/liturgy/revise", REVISE)):
        assert client.post(path, json=body).status_code == 401
        assert_church_isolated(client, "POST", path, world=isolation_world, json=body)
        for role in ("member", "admin"):
            email = f"{role}-{path[9:]}@example.com"
            add_membership(make_user(email=email), church, role)
            post(client, path, church, body, email=email)


def test_another_church_s_prompt_rubric_and_profile_never_reach_the_ai(client, isolation_world):
    world = isolation_world
    churches.set_church_prompts(world.church_b, {"system": "SECRET-B-VOICE"})
    set_settings(world.church_b, rubric={"prayers": {"opening_prayer": ["SECRET-B-POINT"]}},
                 prayer_library={"prayers": [], "voice_profile": "SECRET-B-PROFILE"})
    churches.set_church_prompts(world.church_a, {"system": "A-VOICE"})
    ai = install()
    post(client, "/liturgy/review", world.church_a, {"cards": CARDS}, email=world.a)
    ai.reply = "Revised."
    post(client, "/liturgy/revise", world.church_a, REVISE, email=world.a)
    sent = json.dumps([call["messages"] for call in ai.calls])
    assert len(ai.calls) == 2 and "A-VOICE" in sent and "SECRET-B" not in sent


def test_invalid_bodies_are_422_with_fields_and_never_reach_the_ai(client, church):
    ai = install()
    card = CARDS[0]
    review_cases = [
        ({}, "cards"),
        ({"cards": []}, "cards"),
        ({"cards": [dict(card, section=s) for s in
                    ("call_to_worship", "opening_prayer", "prayer_of_confession", "assurance",
                     "prayer_for_illumination", "prayers_of_the_people", "offertory_prayer", "benediction")]
                   + [card]}, "cards"),
        ({"cards": [card, dict(card, origin="ai")]}, "cards"),                  # one card per section
        ({"cards": [dict(card, section="offering")]}, "cards.0.section"),
        ({"cards": [dict(card, origin="empty")]}, "cards.0.origin"),
        ({"cards": [dict(card, text="x" * 20_001)]}, "cards.0.text"),
        ({"cards": [dict(card, extra=1)]}, "cards.0.extra"),
        ({"cards": [card], "church_id": str(uuid.uuid4())}, "church_id"),
        ({"cards": [card], "occasion": "o" * 301}, "occasion"),
        ({"cards": [card], "scriptures": ["Mark 1"] * 21}, "scriptures"),
        ({"cards": [card], "scriptures": ["r" * 201]}, "scriptures.0"),
        ({"cards": [card], "sermon_text": {"ref": "Mark 4", "text": "x" * 20_001}}, "sermon_text.text"),
        ({"cards": [card], "rubric": {}}, "rubric"),                            # never from the client
    ]
    revise_cases = [
        (dict(REVISE, notes=[]), "notes"),
        (dict(REVISE, notes=["a", "b", "c", "d"]), "notes"),
        (dict(REVISE, notes=["n" * 241]), "notes.0"),
        (dict(REVISE, text="x" * 20_001), "text"),
        (dict(REVISE, section="custom"), "section"),
        ({k: v for k, v in REVISE.items() if k != "text"}, "text"),
        (dict(REVISE, system_prompt="mine"), "system_prompt"),
        (dict(REVISE, sermon_text={"ref": "r" * 201, "text": "x"}), "sermon_text.ref"),
    ]
    for path, cases in (("/liturgy/review", review_cases), ("/liturgy/revise", revise_cases)):
        for body, field in cases:
            r = client.post(path, json=body, headers=church_headers(EMAIL, church))
            assert r.status_code == 422, (path, body, r.text)
            error = r.json()["error"]
            assert error["code"] == "invalid_request" and field in error["fields"], (path, field, error)
    assert ai.calls == []
    post(client, "/liturgy/review", church, {"cards": [card], "sermon_text": {"ref": "r" * 200, "text": "x" * 20_000}})
    post(client, "/liturgy/review", church, {"cards": [dict(card, text="")]})         # a blank card is allowed


def test_revise_returns_the_text_and_ai_failures_are_http_statuses(client, church):
    ai = install(reply="  Gracious God, hear us.  ")
    assert post(client, "/liturgy/revise", church, REVISE) == {"text": "Gracious God, hear us."}
    assert ai.calls[0]["max_completion_tokens"] == 1500
    cases = [
        (dict(available=False), 503, "ai_not_configured", "AI isn't set up on this app yet."),
        (dict(error=Busy("x", code="ai_busy")), 503, "ai_busy", "The AI service is busy. Try again in a minute."),
        (dict(error=UpstreamTimeout("x", code="ai_timeout")), 504, "ai_timeout",
         "The AI took too long to answer. Try again."),
        (dict(error=UpstreamError("x", code="ai_upstream_error")), 502, "ai_upstream_error",
         "The AI service had a problem. Try again."),
    ]
    for kw, status, code, message in cases:
        install(**kw)
        error = post(client, "/liturgy/revise", church, REVISE, status=status)["error"]
        assert (error["code"], error["message"]) == (code, message)
    churches.set_church_prompts(church, {"system": "s" * 8000})
    ai = install(reply="Revised.")
    error = post(client, "/liturgy/revise", church, dict(REVISE, text="d" * 20_000), status=422)["error"]
    assert (error["code"], error["message"], ai.calls) == ("prompt_invalid", "This prayer is too long to revise.", [])
    assert "fields" not in error


def test_revise_costs_one_ai_token_and_the_41st_is_429(client, church, owner, limiter_clock):
    install(reply="Revised.")
    for _ in range(39):
        ratelimit.consume("ai", user_id=owner, church_id=church)
    post(client, "/liturgy/revise", church, REVISE)                  # the 40th
    r = client.post("/liturgy/revise", json=REVISE, headers=church_headers(EMAIL, church))
    assert (r.status_code, r.json()["error"]["code"], r.headers["Retry-After"]) == (429, "rate_limited", "15")
    limiter_clock.advance(15)
    post(client, "/liturgy/revise", church, REVISE)


def test_info_logs_carry_no_prayer_text_or_notes(client, church, caplog):
    install(reply=json.dumps({"cards": [{"section": "opening_prayer",
                                         "notes": [{"tag": "theology", "text": "SECRET-NOTE"}]}]}))
    cards = [{"section": "opening_prayer", "origin": "ai", "text": "SECRET-TEXT"}]
    with caplog.at_level(logging.INFO):
        post(client, "/liturgy/review", church, {"occasion": "SECRET-OCCASION", "cards": cards,
                                                 "sermon_text": {"ref": "Mark 4", "text": "SECRET-SERMON"}})
        install(reply="SECRET-ANSWER")
        post(client, "/liturgy/revise", church, dict(REVISE, text="SECRET-DRAFT", notes=["SECRET-NOTE"]))
    info = "\n".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    assert "liturgy.review" in info and "ai_status=ok" in info and "liturgy.revise" in info
    assert "SECRET" not in info
````

**In `backend/tests/test_api_app.py`, replace:**

````python
        ("/liturgy/generate", "post"): {"401", "403", "404", "422", "429", "503"},
````

**with:**

````python
        ("/liturgy/generate", "post"): {"401", "403", "404", "422", "429", "503"},
        ("/liturgy/review", "post"): {"401", "403", "422", "503"},
        ("/liturgy/revise", "post"): {"401", "403", "422", "429", "502", "503", "504"},
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
.venv/bin/python -m pytest -q backend/tests/test_api_liturgy_review.py backend/tests/test_api_app.py 2>&1 | tail -2
```

**Expected:** `FAILED backend/tests/test_api_liturgy_review.py::test_info_logs_carry_no_prayer_text_or_notes - AssertionError: assert 404 == 200`, then `9 failed, <n> passed in <t>s` (the eight route tests get 404 or 405, and the error-documentation test finds no `/liturgy/review` path).

- [ ] **Step 3 (agent): Write the routes and mount them**

**Create `backend/api/routes/liturgy_review.py`:**

````python
"""The service reviewer's routes (reviewer spec, API; slice 4 spec, reviewer
amendment "Routes"; F §1.5, §1.8).

- POST /liturgy/review (church-scoped): the notes for each card and across
  the service. Always 200 once the request is valid: AI failures and an empty
  `ai` bucket come back as `ai_status` with the code notes (the declared
  deviation from F §1.5 and §1.8). The usecase charges the bucket 1 through
  `charge`, only when it calls the AI.
- POST /liturgy/revise (church-scoped, `rate_limit("ai")`, cost 1): an AI
  draft revised to address its notes. AI failures are HTTP statuses (503,
  504, 502), as on /hymns/suggestions; a draft too long to revise is 422
  prompt_invalid "This prayer is too long to revise.".

The rubric, the system prompt and the voice profile are read on the server,
never taken from the client. Plain `def` routes (F §1.8), no SQL and no
try/except (F §2.2 rule 1). Request models at the top, `extra="forbid"`.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator

from api import ratelimit
from api.deps import ActiveChurch, CurrentUser, get_current_user, require_church
from api.errors import error_responses
from api.ratelimit import rate_limit
from api.schemas import SectionKey, SermonText
from usecases import liturgy_review

router = APIRouter()

NoteTag = Literal["checklist", "rules", "voice", "read_aloud", "theology", "repetition"]
CardOrigin = Literal["ai", "typed", "archive", "default"]
Scriptures = list[Annotated[str, Field(max_length=200)]]


class ReviewCardIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: SectionKey
    origin: CardOrigin
    text: str = Field(max_length=20_000)


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occasion: str = Field("", max_length=300)
    scriptures: Scriptures = Field(default_factory=list, max_length=20)
    sermon_text: Optional[SermonText] = None     # the same resolved sermon text as generation, never ESV
    cards: list[ReviewCardIn] = Field(min_length=1, max_length=8)

    @field_validator("cards")
    @classmethod
    def one_card_per_section(cls, cards: list[ReviewCardIn]) -> list[ReviewCardIn]:
        if len({card.section for card in cards}) != len(cards):
            raise ValueError("Each section can be sent once.")
        return cards


class ReviseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: SectionKey
    text: str = Field(max_length=20_000)
    notes: list[Annotated[str, Field(max_length=240)]] = Field(min_length=1, max_length=3)
    occasion: str = Field("", max_length=300)
    scriptures: Scriptures = Field(default_factory=list, max_length=20)
    sermon_text: Optional[SermonText] = None


class NoteOut(BaseModel):
    tag: NoteTag
    text: str
    source: Literal["code", "ai"]


class CardNotesOut(BaseModel):
    section: SectionKey
    notes: list[NoteOut]          # at most 3, most important first (code notes first)


class ReviewOut(BaseModel):
    cards: list[CardNotesOut]     # one per card sent, in request order
    service_notes: list[NoteOut]  # the "Across the service" box, at most 3
    ai_status: Literal["ok", "not_configured", "busy", "timeout", "rate_limited", "error"]


class ReviseOut(BaseModel):
    text: str


def _sermon(sermon_text: Optional[SermonText]) -> Optional[tuple[str, str]]:
    return (sermon_text.ref, sermon_text.text) if sermon_text else None


def _note(note) -> NoteOut:
    return NoteOut(tag=note.tag, text=note.text, source=note.source)


@router.post("/liturgy/review", response_model=ReviewOut, responses=error_responses(401, 403, 422, 503))
def review_service(payload: ReviewIn, church: ActiveChurch = Depends(require_church),
                   user: CurrentUser = Depends(get_current_user)) -> ReviewOut:
    """Notes for every card sent and across the service: the code checks always,
    the AI review when it can run (75 s deadline; F §1.8). Charged 1 `ai` token
    only when the AI is called (40 per 10 min per user, 400 per day per church)."""
    outcome = liturgy_review.review_service(
        church_id=church.id, user_id=user.id, occasion=payload.occasion, scriptures=payload.scriptures,
        cards=[liturgy_review.ReviewCard(c.section, c.origin, c.text) for c in payload.cards],
        sermon=_sermon(payload.sermon_text),
        charge=lambda n: ratelimit.consume("ai", user_id=user.id, church_id=church.id, cost=n))
    return ReviewOut(cards=[CardNotesOut(section=c.section, notes=[_note(n) for n in c.notes])
                            for c in outcome.cards],
                     service_notes=[_note(n) for n in outcome.service_notes], ai_status=outcome.ai_status)


@router.post("/liturgy/revise", response_model=ReviseOut, dependencies=[Depends(rate_limit("ai"))],
             responses=error_responses(401, 403, 422, 429, 502, 503, 504))
def revise_section(payload: ReviseIn, church: ActiveChurch = Depends(require_church),
                   user: CurrentUser = Depends(get_current_user)) -> ReviseOut:
    """The draft revised to address these notes only; the rest is kept. Charged
    1 `ai` token per request (F §1.8)."""
    text = liturgy_review.revise_section(
        church_id=church.id, user_id=user.id, section=payload.section, text=payload.text, notes=payload.notes,
        occasion=payload.occasion, scriptures=payload.scriptures, sermon=_sermon(payload.sermon_text))
    return ReviseOut(text=text)
````

**In `backend/api/main.py`, replace:**

````python
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, liturgy, me, reference,
                        rubric, scripture)
````

**with:**

````python
from api.routes import (churches, health, hymnals, hymns, invites, lectionary, liturgy, liturgy_review, me,
                        reference, rubric, scripture)
````

**In `backend/api/main.py`, replace:**

````python
    app.include_router(liturgy.router)
````

**with:**

````python
    app.include_router(liturgy.router)
    app.include_router(liturgy_review.router)
````

- [ ] **Step 4 (agent): Regenerate the OpenAPI files, then run the tests and the suite**

```bash
.venv/bin/python backend/scripts/export_openapi.py && (cd frontend && npm run gen:api >/dev/null 2>&1) && (cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?")
git status --short -- frontend backend
.venv/bin/python -m pytest -q backend/tests/test_api_liturgy_review.py backend/tests/test_api_app.py backend/tests/test_openapi_contract.py backend/tests/test_route_guards.py backend/tests/test_no_streamlit_in_core.py 2>&1 | tail -1
.venv/bin/python -m pytest -q | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** `Wrote <repo>/frontend/src/lib/api/openapi.json` and `typecheck 0`; ` M backend/api/main.py`, ` M backend/tests/test_api_app.py`, ` M frontend/src/lib/api/openapi.json`, ` M frontend/src/lib/api/schema.d.ts`, `?? backend/api/routes/liturgy_review.py`, `?? backend/tests/test_api_liturgy_review.py`; `<n> passed in <t>s` with no failure; `1213 passed, 11 skipped in <t>s`; ` Test Files  75 passed (75)` and `      Tests  539 passed (539)` (generated types only).

- [ ] **Step 5 (agent): Commit**

```bash
git add backend/api/routes/liturgy_review.py backend/api/main.py backend/tests/test_api_liturgy_review.py backend/tests/test_api_app.py frontend/src/lib/api/openapi.json frontend/src/lib/api/schema.d.ts
git commit -q -m "Reviewer: POST /liturgy/review and /liturgy/revise (R API; S4 reviewer amendment; F 1.5, 1.8, 1.11)" -m "Review answers 200 with the code notes and ai_status whatever the AI
does, and is charged one ai token only when the AI runs. Revise is
charged one token per request and returns AI failures as HTTP statuses,
like /hymns/suggestions. Both are church-scoped; the rubric, system prompt
and voice profile are read on the server. OpenAPI and the frontend's
generated types are regenerated." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint (end of batch A) and backup push**

Review T1-T5 together against R's Layer 1, Layer 2, Revise, API and Testing, and S4's amendment: R's note texts verbatim; the season sentence verbatim; no AI text at INFO; one session, closed before the AI call; review never 429 and never `prompt_invalid`; revise's 422 message. Then `git push origin claude/slice-2-plan-4q33le` (standing permission for backup pushes).

Counts after Task 5: backend **1213 passed, 11 skipped**; frontend **539 in 75**.

### Task 6: The client's two calls, their 100 s timeouts, the request bodies and the test fixtures (R API; S4 reviewer amendment "Sermon text", "Timeouts"; F §1.8, §4.4, §4.5; owner answer 3; clarifications 17, 26)

T5 generated the types; this task names them in `lib/api/types.ts`, adds the two `ENDPOINT_TIMEOUTS` rows (100 000 ms each, owner answer 3), the two calls in `lib/queries/liturgy.ts` (plain async functions, like `generateSection`, so no page calls `apiFetch`), and the two request builders in `lib/liturgy/request.ts`, which send the same occasion, readings and resolved sermon text as `buildGenerateRequest` (one shared `readingsContext`). `reviewTargets` is every switched-on card with text after trimming, in section order; custom elements, hymns and readings are never sent (R "Out of scope"; F D17).

**Files:**
- Modify: `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/timeouts.ts`, `frontend/src/lib/queries/liturgy.ts`, `frontend/src/lib/liturgy/request.ts`, `frontend/src/test/fixtures/index.ts`; tests `frontend/src/lib/liturgy/request.test.ts`, `frontend/src/lib/queries/liturgy.test.tsx`

**Interfaces:**
- Consumes: T5's generated `ReviewIn`, `ReviewCardIn`, `ReviewOut`, `NoteOut`, `ReviseIn`, `ReviseOut`; 4b's `ApiCall`, `clipChars`, `cleanRefs`, `SECTION_KEYS`.
- Produces (later users: T7-T10):
  - types `ReviewBody`, `ReviewCardBody`, `ReviewResult`, `ReviewNote`, `AiStatus`, `ReviseBody`, `ReviseResult`
  - `reviewService(call, body, signal?) -> Promise<ReviewResult>`, `reviseSection(call, body, signal?) -> Promise<string>`
  - `reviewTargets(draft) -> SectionKey[]`, `buildReviewRequest(draft, keys, sermon) -> ReviewBody`, `buildReviseRequest(draft, key, notes, sermon) -> ReviseBody` (at most 3 notes), `MAX_CARD_TEXT = 20_000`
  - fixtures `reviewNote(tag, text, source = "ai")`, `reviewResult(overrides)`, `reviewRoute(answer)`, `reviseRoute(answer)`

- [ ] **Step 1 (agent): Write the failing tests and the fixtures**

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
  OutlineItem,
````

**with:**

````ts
  OutlineItem,
  ReviewBody,
  ReviewNote,
  ReviewResult,
  ReviseBody,
````

**In `frontend/src/test/fixtures/index.ts`, replace:**

````ts
    return "section" in out ? { results: [out] } : out;
  };
}
````

**with:**

````ts
    return "section" in out ? { results: [out] } : out;
  };
}

// --- the service reviewer: review and revise answers -------------------------------

/** One note as `POST /liturgy/review` returns it (an AI note unless `source` says "code"). */
export function reviewNote(tag: ReviewNote["tag"], text: string, source: ReviewNote["source"] = "ai"): ReviewNote {
  return { tag, text, source };
}

/** A review answer: by default the AI ran and found nothing. */
export function reviewResult(overrides: Partial<ReviewResult> = {}): ReviewResult {
  return { cards: [], service_notes: [], ai_status: "ok", ...overrides };
}

/**
 * A fake-API handler for `POST /liturgy/review`: `answer(body)` gives the
 * answer or a whole response (`fakeError(...)`); by default every card sent
 * comes back with no notes ("Looks good.").
 */
export function reviewRoute(
  answer: (body: ReviewBody) => ReviewResult | { status: number } | Promise<ReviewResult | { status: number }> = (body) =>
    reviewResult({ cards: body.cards.map((c) => ({ section: c.section, notes: [] })) }),
) {
  return async (req: { body: unknown }) => answer(req.body as ReviewBody);
}

/** A fake-API handler for `POST /liturgy/revise`: by default "{Label} revised with the notes.". */
export function reviseRoute(
  answer: (body: ReviseBody) => { text: string } | { status: number } | Promise<{ text: string } | { status: number }> = (body) => ({
    text: `${SECTION_LABELS[body.section]} revised with the notes.`,
  }),
) {
  return async (req: { body: unknown }) => answer(req.body as ReviseBody);
}
````

**In `frontend/src/lib/liturgy/request.test.ts`, replace:**

````ts
import { buildGenerateRequest, MAX_SERMON_TEXT, sermonSource, sermonText } from "./request";
````

**with:**

````ts
import { editCardText } from "./cards";
import {
  buildGenerateRequest,
  buildReviewRequest,
  buildReviseRequest,
  MAX_SERMON_TEXT,
  reviewTargets,
  sermonSource,
  sermonText,
} from "./request";
````

**In `frontend/src/lib/liturgy/request.test.ts`, replace:**

````ts
    expect(sermonSource(esv, church("kjv"), translations({ esv_available: false, items: offered.items.slice(0, 2) }))?.translation).toBe("kjv");
  });
});
````

**with:**

````ts
    expect(sermonSource(esv, church("kjv"), translations({ esv_available: false, items: offered.items.slice(0, 2) }))?.translation).toBe("kjv");
  });
});

describe("buildReviewRequest and buildReviseRequest (the service reviewer, R API)", () => {
  function withCard(d: DraftV1, key: keyof DraftV1["liturgy"]["cards"], patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>): DraftV1 {
    return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
  }

  it("sends every switched-on card with text, in section order, with its origin, and generation's context", () => {
    let d = withReadings([" Isaiah 5:1-7 ", "", "Matthew 21:33-46"], ` ${"o".repeat(305)} `);
    d = withCard(d, "benediction", { text: "Go in peace.", origin: "default" });
    d = editCardText(d, "call_to_worship", "Leader: Come!");
    d = withCard(d, "opening_prayer", { text: "   ", origin: "empty" });                       // blank: not sent
    d = withCard(d, "prayer_of_confession", { text: "Merciful God", origin: "archive", enabled: false }); // off: not sent
    d = withCard(d, "prayers_of_the_people", { text: "x".repeat(20_005), origin: "ai", enabled: true });
    d = withCard(d, "assurance", { text: "Leader: Friends,", origin: "empty" });             // defensive: never "empty"
    const keys = reviewTargets(d);
    expect(keys).toEqual(["call_to_worship", "assurance", "prayers_of_the_people", "benediction"]);
    const sermon = { ref: "Matthew 21:33-46", text: "Listen to another parable." };
    const body = buildReviewRequest(d, keys, sermon);
    expect(body).toEqual({
      occasion: "o".repeat(300),
      scriptures: ["Isaiah 5:1-7", "Matthew 21:33-46"],
      cards: [
        { section: "call_to_worship", origin: "typed", text: "Leader: Come!" },
        { section: "assurance", origin: "typed", text: "Leader: Friends," },
        { section: "prayers_of_the_people", origin: "ai", text: "x".repeat(20_000) },
        { section: "benediction", origin: "default", text: "Go in peace." },
      ],
      sermon_text: sermon,
    });
    const generate = buildGenerateRequest(d, "opening_prayer", sermon);
    expect([body.occasion, body.scriptures, body.sermon_text]).toEqual([generate.occasion, generate.scriptures, generate.sermon_text]);
    expect(buildReviewRequest(d, keys, null)).not.toHaveProperty("sermon_text");
  });

  it("sends one card's text and its remaining notes to revise, with the same context", () => {
    const d = withCard(withReadings(OCT_4), "opening_prayer", { text: "Gracious God, as we journey, hear us.", origin: "ai" });
    const notes = ['Stock phrase "as we journey". Say it more naturally.', "Long.", "Third.", "Fourth."];
    expect(buildReviseRequest(d, "opening_prayer", notes, null)).toEqual({
      section: "opening_prayer",
      text: "Gracious God, as we journey, hear us.",
      notes: notes.slice(0, 3),
      occasion: "Nineteenth Sunday after Pentecost",
      scriptures: OCT_4,
    });
    const sermon = { ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" };
    expect(buildReviseRequest(d, "opening_prayer", notes, sermon).sermon_text).toEqual(sermon);
  });
});
````

**In `frontend/src/lib/queries/liturgy.test.tsx`, replace:**

````tsx
import { church, CHURCH_IDS, liturgyConfig, sectionResult } from "@/test/fixtures";
````

**with:**

````tsx
import { church, CHURCH_IDS, liturgyConfig, reviewNote, reviewResult, sectionResult } from "@/test/fixtures";
````

**In `frontend/src/lib/queries/liturgy.test.tsx`, replace:**

````tsx
import { generateSection, useLiturgyConfig } from "./liturgy";
````

**with:**

````tsx
import { generateSection, reviewService, reviseSection, useLiturgyConfig } from "./liturgy";
````

**In `frontend/src/lib/queries/liturgy.test.tsx`, replace:**

````tsx

  it("uses a test config equal to the shared fixtures 4a's API is pinned to", () => {
````

**with:**

````tsx

  it("reviews the service and revises a card as the church, each waiting up to 100 seconds (owner answer 3)", async () => {
    expect(timeoutFor("POST", "/liturgy/review")).toBe(100_000);
    expect(timeoutFor("POST", "/liturgy/revise")).toBe(100_000);
    const answer = reviewResult({
      cards: [{ section: "opening_prayer", notes: [reviewNote("rules", "Names Ordinary Time. Leave the season unnamed.", "code")] }],
      ai_status: "not_configured",
    });
    const api = installFakeApi({ "POST /liturgy/review": answer, "POST /liturgy/revise": { text: "Revised." } });
    const { result } = render(() => useApi());
    const review = { occasion: "", scriptures: [], cards: [{ section: "opening_prayer" as const, origin: "ai" as const, text: "In Ordinary Time" }] };
    await expect(reviewService(result.current.church, review)).resolves.toEqual(answer);
    const revise = { section: "opening_prayer" as const, text: "In Ordinary Time", notes: ["Names Ordinary Time."], occasion: "" };
    await expect(reviseSection(result.current.church, revise)).resolves.toBe("Revised.");
    expect(api.requests.map((r) => [r.method, r.path, r.headers["X-Church-Id"], r.body])).toEqual([
      ["POST", "/liturgy/review", CHURCH_IDS.grace, review],
      ["POST", "/liturgy/revise", CHURCH_IDS.grace, revise],
    ]);
  });

  it("uses a test config equal to the shared fixtures 4a's API is pinned to", () => {
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/request.test.ts src/lib/queries/liturgy.test.tsx 2>&1 | grep -E "^ +(✓|×)|Tests ")
```

**Expected:** @@RED6@@

- [ ] **Step 3 (agent): The types, timeouts, calls and builders**

**Append to `frontend/src/lib/api/types.ts`:**

````ts

/** `POST /liturgy/review` (the service reviewer): every switched-on card with text, and the notes back. */
export type ReviewBody = components["schemas"]["ReviewIn"];
export type ReviewCardBody = components["schemas"]["ReviewCardIn"];
export type ReviewResult = components["schemas"]["ReviewOut"];
export type ReviewNote = components["schemas"]["NoteOut"];
/** Why the AI part of a review is missing ("ok" when it ran): a field, not an error code (F §1.5). */
export type AiStatus = ReviewResult["ai_status"];
/** `POST /liturgy/revise` (the service reviewer): one AI card's text and its remaining notes; the revised text. */
export type ReviseBody = components["schemas"]["ReviseIn"];
export type ReviseResult = components["schemas"]["ReviseOut"];
````

**In `frontend/src/lib/api/timeouts.ts`, replace:**

````ts
  "POST /liturgy/generate": 100_000,
````

**with:**

````ts
  "POST /liturgy/generate": 100_000,
  // The service reviewer (owner answer 3, 2026-10-01; F §1.8): a review answers within its 75 s
  // deadline plus a last connect, and a revision within generation's 85 s; the same margin.
  "POST /liturgy/review": 100_000,
  "POST /liturgy/revise": 100_000,
````

**In `frontend/src/lib/queries/liturgy.ts`, replace:**

````ts
 *   answer 2, 2026-09-30).
````

**with:**

````ts
 *   answer 2, 2026-09-30).
 * - `reviewService(call, body, signal)` and `reviseSection(call, body,
 *   signal)`: the service reviewer's two church-scoped POSTs, each with a
 *   100 s client timeout (owner answer 3, 2026-10-01). A review answers 200
 *   with the notes whatever the AI did (`ai_status`); a revision's AI
 *   failures arrive as `ApiError`s.
````

**In `frontend/src/lib/queries/liturgy.ts`, replace:**

````ts
import type { GenerateLiturgyBody, GenerateLiturgyResult, LiturgyConfig, SectionResult } from "@/lib/api/types";
````

**with:**

````ts
import type {
  GenerateLiturgyBody,
  GenerateLiturgyResult,
  LiturgyConfig,
  ReviewBody,
  ReviewResult,
  ReviseBody,
  ReviseResult,
  SectionResult,
} from "@/lib/api/types";
````

**In `frontend/src/lib/queries/liturgy.ts`, replace:**

````ts
  return result;
}
````

**with:**

````ts
  return result;
}

export function reviewService(call: ApiCall, body: ReviewBody, signal?: AbortSignal): Promise<ReviewResult> {
  return call<ReviewResult>("/liturgy/review", { method: "POST", json: body, signal });
}

/** The revised text of one AI card. */
export async function reviseSection(call: ApiCall, body: ReviseBody, signal?: AbortSignal): Promise<string> {
  const out = await call<ReviseResult>("/liturgy/revise", { method: "POST", json: body, signal });
  return out.text;
}
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
 */
import type { ChurchProfile, GenerateLiturgyBody, HymnRef, Passage, SermonText, Translations } from "@/lib/api/types";
import { effectivePicks, effectiveTranslation } from "@/lib/draft/readings";
import type { DraftV1, HymnPick, SectionKey } from "@/lib/draft/schema";
````

**with:**

````ts
 *
 * The service reviewer's bodies (`buildReviewRequest`, `buildReviseRequest`)
 * carry the same occasion, readings and resolved sermon text.
 */
import type {
  ChurchProfile,
  GenerateLiturgyBody,
  HymnRef,
  Passage,
  ReviewBody,
  ReviewCardBody,
  ReviseBody,
  SermonText,
  Translations,
} from "@/lib/api/types";
import { effectivePicks, effectiveTranslation } from "@/lib/draft/readings";
import { SECTION_KEYS, type DraftV1, type HymnPick, type SectionKey } from "@/lib/draft/schema";
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
export const MAX_SERMON_TEXT = 20_000;
````

**with:**

````ts
export const MAX_SERMON_TEXT = 20_000;
export const MAX_CARD_TEXT = 20_000;
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
export function buildGenerateRequest(draft: DraftV1, section: SectionKey, sermon: SermonText | null): GenerateLiturgyBody {
  const r = draft.readings;
  const slots = draft.hymns.slots;
  const body: GenerateLiturgyBody = {
    occasion: clipChars(r.occasion.trim(), MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
````

**with:**

````ts
/** The occasion and readings every liturgy request carries, within the ServiceDraft limits. */
function readingsContext(draft: DraftV1): { occasion: string; scriptures: string[] } {
  const r = draft.readings;
  return {
    occasion: clipChars(r.occasion.trim(), MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
  };
}

export function buildGenerateRequest(draft: DraftV1, section: SectionKey, sermon: SermonText | null): GenerateLiturgyBody {
  const slots = draft.hymns.slots;
  const body: GenerateLiturgyBody = {
    ...readingsContext(draft),
````

**In `frontend/src/lib/liturgy/request.ts`, replace:**

````ts
  return { ref: clipChars(ref.trim(), MAX_REF_LENGTH), text: clipChars(text, MAX_SERMON_TEXT) };
}
````

**with:**

````ts
  return { ref: clipChars(ref.trim(), MAX_REF_LENGTH), text: clipChars(text, MAX_SERMON_TEXT) };
}

/** What "Review service" sends: every switched-on card with text after trimming, in section order. */
export function reviewTargets(draft: DraftV1): SectionKey[] {
  return SECTION_KEYS.filter((key) => {
    const card = draft.liturgy.cards[key];
    return card.enabled && card.text.trim() !== "";
  });
}

/**
 * The `POST /liturgy/review` body (R API): `keys`' cards with their origins
 * and their text as the cards hold it (cut to 20 000; a card with text never
 * says "empty", and one that did would go as "typed"), plus the context.
 */
export function buildReviewRequest(draft: DraftV1, keys: SectionKey[], sermon: SermonText | null): ReviewBody {
  const cards: ReviewCardBody[] = keys.map((key) => {
    const card = draft.liturgy.cards[key];
    return { section: key, origin: card.origin === "empty" ? "typed" : card.origin, text: clipChars(card.text, MAX_CARD_TEXT) };
  });
  const body: ReviewBody = { ...readingsContext(draft), cards };
  if (sermon !== null) body.sermon_text = sermon;
  return body;
}

/** The `POST /liturgy/revise` body (R API): one card's text and its remaining notes (at most 3), plus the context. */
export function buildReviseRequest(draft: DraftV1, key: SectionKey, notes: string[], sermon: SermonText | null): ReviseBody {
  const body: ReviseBody = {
    section: key,
    text: clipChars(draft.liturgy.cards[key].text, MAX_CARD_TEXT),
    notes: notes.slice(0, 3),
    ...readingsContext(draft),
  };
  if (sermon !== null) body.sermon_text = sermon;
  return body;
}
````

- [ ] **Step 4 (agent): Run the files, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy/request.test.ts src/lib/queries/liturgy.test.tsx 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** ` Test Files  2 passed (2)`, `      Tests  11 passed (11)`; ` Test Files  75 passed (75)`, `      Tests  542 passed (542)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/api/timeouts.ts frontend/src/lib/queries/liturgy.ts frontend/src/lib/liturgy/request.ts frontend/src/test/fixtures/index.ts frontend/src/lib/liturgy/request.test.ts frontend/src/lib/queries/liturgy.test.tsx
git commit -q -m "Reviewer: the client's review and revise calls, 100 s each (R API; owner answer 3; F 1.8)" -m "Names the generated types, adds the two ENDPOINT_TIMEOUTS rows, the two
calls beside generateSection, and the request bodies: every switched-on
card with text in section order with its origin, or one card's text and
its remaining notes, each with generation's occasion, readings and sermon
text. Test fixtures for both answers." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 6: backend **1213 passed, 11 skipped**; frontend **542 in 75**.

### Task 7: The notes' rules, `lib/liturgy/notes.ts` (R "Notes", "Notes go away when the text changes", "Revise with these notes"; S4 reviewer amendment "UI hooks", Testing; clarifications 18-21)

Pure functions over the draft and a review answer, so the stale rule, the clearing rule, dismiss, "Looks good." and when Revise is offered are tested without a screen. A review result is kept for a card only while the card still holds the text and origin captured when "Review service" was pressed (slice 4's stale-results rule); any later change to a card's text or origin drops its notes; a new `created_at` drops them all.

**Files:**
- Create: `frontend/src/lib/liturgy/notes.ts`, `frontend/src/lib/liturgy/notes.test.ts`

**Interfaces:**
- Consumes: T6's `ReviewNote`, `ReviewResult`, `AiStatus`; 4b's `DraftV1`, `LiturgyCard`, and in the tests `editCardText`, `applyGenerated`, `clearCard`, `restoreChurchDefault`.
- Produces (later users: T8-T10):
  - `TAG_LABELS` (Checklist, Rules, Voice, Read aloud, Theology, Repetition), `LOOKS_GOOD`, `QUICK_CHECKS_ONLY`
  - types `Note` (a `ReviewNote` with an `id`), `ReviewedCard`, `CardReview {reviewed, notes, found}`, `ServiceReview {createdAt, cards, service, aiStatus}`, `ReviewAsk`
  - `captureReview(draft, keys)`, `applyReview(draft, ask, result) -> {review, dropped}`, `pruneReview(review, draft)` (the same object when nothing changed), `dismissNote(review, where, id)`, `canRevise(card, cardReview)`, `noteCount(review)`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/notes.test.ts`:**

````ts
/**
 * The service reviewer's notes (reviewer spec, "Notes", "Notes go away when
 * the text changes"; slice 4 spec, reviewer amendment Testing): stale results
 * dropped by text and origin, notes cleared by any change, dismiss, "Looks
 * good." and when Revise is offered.
 */
import { describe, expect, it } from "vitest";

import type { DraftV1, SectionKey } from "@/lib/draft/schema";
import { reviewNote, reviewResult, testDraft } from "@/test/fixtures";

import { applyGenerated, clearCard, editCardText, restoreChurchDefault } from "./cards";
import { applyReview, canRevise, captureReview, dismissNote, noteCount, pruneReview } from "./notes";

const STOCK = 'Stock phrase "as we journey". Say it more naturally.';

function withText(d: DraftV1, key: SectionKey, text: string, origin: DraftV1["liturgy"]["cards"]["benediction"]["origin"]): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], text, origin } } } };
}

function reviewed(): DraftV1 {
  let d = withText(testDraft(), "call_to_worship", "Leader: As we journey, come.", "typed");
  d = withText(d, "opening_prayer", "Gracious God, hear us.", "ai");
  return withText(d, "benediction", "Go in peace.", "default");
}

const ANSWER = reviewResult({
  cards: [
    { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code"), reviewNote("read_aloud", "Long line.")] },
    { section: "opening_prayer", notes: [reviewNote("theology", "Praise is not a payment.")] },
    { section: "benediction", notes: [] },
  ],
  service_notes: [reviewNote("repetition", 'Several prayers open with "Gracious God".', "code")],
});

describe("the reviewer's notes (R Notes)", () => {
  it("keeps the notes of each card that still holds what was reviewed, and drops the rest or the whole review", () => {
    const d = reviewed();
    const ask = captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]);
    const { review, dropped } = applyReview(d, ask, ANSWER);
    expect(dropped).toEqual([]);
    expect(review?.cards.call_to_worship?.notes.map((n) => [n.id, n.tag, n.text])).toEqual([
      ["call_to_worship-0", "rules", STOCK],
      ["call_to_worship-1", "read_aloud", "Long line."],
    ]);
    expect(review?.cards.benediction).toEqual({ reviewed: { text: "Go in peace.", origin: "default" }, notes: [], found: 0 });
    expect(review?.service.map((n) => n.id)).toEqual(["service-0"]);
    expect(review?.aiStatus).toBe("ok");
    expect(review && noteCount(review)).toBe(4);
    // Changed while the review ran: the text (typing, another tab) or only the origin (Use church default).
    let later = editCardText(d, "call_to_worship", "Leader: Come.");
    later = withText(later, "opening_prayer", "Gracious God, hear us.", "typed");
    const stale = applyReview(later, ask, ANSWER);
    expect(stale.dropped).toEqual(["call_to_worship", "opening_prayer"]);
    expect(Object.keys(stale.review?.cards ?? {})).toEqual(["benediction"]);
    // A card the review was not asked about is ignored; a new service drops everything.
    const extra = reviewResult({ cards: [{ section: "assurance", notes: [reviewNote("rules", "Not asked.")] }] });
    expect(applyReview(d, ask, extra).review?.cards).toEqual({});
    expect(applyReview({ ...d, created_at: "2026-09-29T16:00:01.000Z" }, ask, ANSWER)).toEqual({
      review: null,
      dropped: ["call_to_worship", "opening_prayer", "benediction"],
    });
  });

  it("clears a card's notes when its text or origin changes, and every note when the service changes", () => {
    const d = reviewed();
    const { review } = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER);
    expect(pruneReview(review, d)).toBe(review);                                    // nothing changed: the same object
    const changes: [string, DraftV1][] = [
      ["typing", editCardText(d, "opening_prayer", "Gracious God, hear us!")],
      ["Regenerate or Revise", applyGenerated(d, "opening_prayer", "A new draft.")],
      ["Clear text", clearCard(d, "opening_prayer")],
    ];
    for (const [what, next] of changes) {
      const pruned = pruneReview(review, next);
      expect(Object.keys(pruned?.cards ?? {}), what).toEqual(["call_to_worship", "benediction"]);
      expect(pruned?.service, what).toHaveLength(1);
    }
    // "Use church default" with the same words still changes the origin.
    const typed = withText(d, "benediction", "Go in peace.", "typed");
    const asked = applyReview(typed, captureReview(typed, ["benediction"]), ANSWER).review;
    expect(pruneReview(asked, restoreChurchDefault(typed, "Go in peace."))?.cards).toEqual({});
    expect(pruneReview(review, { ...d, created_at: "2026-09-29T16:00:01.000Z" })).toBeNull();
    expect(pruneReview(null, d)).toBeNull();
  });

  it("dismisses one note at a time, and Looks good is only for a card that came back with none", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    const one = dismissNote(review, "call_to_worship", "call_to_worship-0");
    expect(one.cards.call_to_worship?.notes.map((n) => n.text)).toEqual(["Long line."]);
    const none = dismissNote(one, "call_to_worship", "call_to_worship-1");
    expect(none.cards.call_to_worship).toMatchObject({ notes: [], found: 2 });     // shows nothing, not "Looks good."
    expect(review.cards.benediction).toMatchObject({ notes: [], found: 0 });       // "Looks good."
    expect(dismissNote(none, "service", "service-0").service).toEqual([]);
    expect(dismissNote(review, "opening_prayer", "nope")).toBe(review);
    expect(dismissNote(review, "assurance", "assurance-0")).toBe(review);
  });

  it("offers Revise only on an AI card with a note left", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    expect(canRevise(d.liturgy.cards.opening_prayer, review.cards.opening_prayer)).toBe(true);
    expect(canRevise(d.liturgy.cards.call_to_worship, review.cards.call_to_worship)).toBe(false);     // typed
    expect(canRevise(d.liturgy.cards.benediction, review.cards.benediction)).toBe(false);             // default
    const archive = { ...d.liturgy.cards.opening_prayer, origin: "archive" as const };
    expect(canRevise(archive, review.cards.opening_prayer)).toBe(false);
    const dismissed = dismissNote(review, "opening_prayer", "opening_prayer-0");
    expect(canRevise(d.liturgy.cards.opening_prayer, dismissed.cards.opening_prayer)).toBe(false);    // none left
    expect(canRevise(d.liturgy.cards.opening_prayer, undefined)).toBe(false);                          // not reviewed
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/notes.test.ts 2>&1 | grep -E "Failed to (load|resolve)|Test Files|Tests ")
```

**Expected:** @@RED7@@

- [ ] **Step 3 (agent): Write the module**

**Create `frontend/src/lib/liturgy/notes.ts`:**

````ts
/**
 * The service reviewer's notes (reviewer spec, "Notes", "Notes go away when
 * the text changes", "Revise with these notes"; slice 4 spec, reviewer
 * amendment). Pure; the review provider keeps the state in memory only, never
 * in the draft, the archive or `localStorage` (`DraftV1` is unchanged).
 *
 * - `captureReview` remembers each card's text and origin when "Review
 *   service" is pressed; `applyReview` keeps a card's notes only while the
 *   card still holds exactly that (slice 4's stale-results rule, comparing
 *   text and origin), and drops the whole review when the service changed
 *   (a new `created_at`).
 * - `pruneReview` runs on every draft change: a card whose text or origin no
 *   longer matches what was reviewed loses its notes (typing, Regenerate,
 *   Revise, Clear text, "Use church default", Undo, another tab's edit), and
 *   a new service loses the whole review.
 * - "Looks good." shows for a card that was reviewed and came back with no
 *   notes; a card whose notes were all dismissed shows nothing.
 * - Revise is offered only on a card whose origin is "ai" with a note left.
 */
import type { AiStatus, ReviewNote, ReviewResult } from "@/lib/api/types";
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";

/** The tag chips (R "Notes"). */
export const TAG_LABELS: Record<ReviewNote["tag"], string> = {
  checklist: "Checklist",
  rules: "Rules",
  voice: "Voice",
  read_aloud: "Read aloud",
  theology: "Theology",
  repetition: "Repetition",
};

export const LOOKS_GOOD = "Looks good.";
export const QUICK_CHECKS_ONLY = "Only quick checks ran. The full review isn't available right now.";

export type Note = ReviewNote & { id: string };
export type ReviewedCard = { text: string; origin: LiturgyCard["origin"] };
/** `found`: how many notes the card came back with ("Looks good." only when 0). */
export type CardReview = { reviewed: ReviewedCard; notes: Note[]; found: number };
export type ServiceReview = {
  createdAt: string;
  cards: Partial<Record<SectionKey, CardReview>>;
  service: Note[];
  aiStatus: AiStatus;
};
export type ReviewAsk = { createdAt: string; cards: Partial<Record<SectionKey, ReviewedCard>> };

/** The cards as they are when "Review service" is pressed. */
export function captureReview(d: DraftV1, keys: readonly SectionKey[]): ReviewAsk {
  const cards: Partial<Record<SectionKey, ReviewedCard>> = {};
  for (const key of keys) cards[key] = { text: d.liturgy.cards[key].text, origin: d.liturgy.cards[key].origin };
  return { createdAt: d.created_at, cards };
}

function holds(card: LiturgyCard, reviewed: ReviewedCard): boolean {
  return card.text === reviewed.text && card.origin === reviewed.origin;
}

/**
 * The review as the step shows it: the notes of each card that still holds
 * what was sent, and the service's notes. `dropped` lists the cards whose
 * notes were dropped because they changed; the review is null when the
 * service changed.
 */
export function applyReview(
  d: DraftV1,
  ask: ReviewAsk,
  result: ReviewResult,
): { review: ServiceReview | null; dropped: SectionKey[] } {
  const asked = Object.keys(ask.cards) as SectionKey[];
  if (d.created_at !== ask.createdAt) return { review: null, dropped: asked };
  const cards: Partial<Record<SectionKey, CardReview>> = {};
  const dropped: SectionKey[] = [];
  for (const { section, notes } of result.cards) {
    const reviewed = ask.cards[section];
    if (reviewed === undefined) continue;
    if (!holds(d.liturgy.cards[section], reviewed)) {
      dropped.push(section);
      continue;
    }
    cards[section] = { reviewed, notes: notes.map((n, i) => ({ ...n, id: `${section}-${i}` })), found: notes.length };
  }
  return {
    review: {
      createdAt: ask.createdAt,
      cards,
      service: result.service_notes.map((n, i) => ({ ...n, id: `service-${i}` })),
      aiStatus: result.ai_status,
    },
    dropped,
  };
}

/** The review after a draft change: the same object when nothing changed. */
export function pruneReview(review: ServiceReview | null, d: DraftV1): ServiceReview | null {
  if (review === null) return null;
  if (d.created_at !== review.createdAt) return null;
  const gone = (Object.keys(review.cards) as SectionKey[]).filter((key) => {
    const card = review.cards[key];
    return card !== undefined && !holds(d.liturgy.cards[key], card.reviewed);
  });
  if (gone.length === 0) return review;
  const cards = { ...review.cards };
  for (const key of gone) delete cards[key];
  return { ...review, cards };
}

/** Removes one note, from a card or from "Across the service". */
export function dismissNote(review: ServiceReview, where: SectionKey | "service", id: string): ServiceReview {
  if (where === "service") {
    const service = review.service.filter((n) => n.id !== id);
    return service.length === review.service.length ? review : { ...review, service };
  }
  const card = review.cards[where];
  if (card === undefined || !card.notes.some((n) => n.id === id)) return review;
  return { ...review, cards: { ...review.cards, [where]: { ...card, notes: card.notes.filter((n) => n.id !== id) } } };
}

/** "Revise with these notes": only an AI card with at least one note left. */
export function canRevise(card: LiturgyCard, review: CardReview | undefined): boolean {
  return card.origin === "ai" && review !== undefined && review.notes.length > 0;
}

/** How many notes the review shows in all (for the announcement when it ends). */
export function noteCount(review: ServiceReview): number {
  return Object.values(review.cards).reduce((n, card) => n + (card?.notes.length ?? 0), 0) + review.service.length;
}
````

- [ ] **Step 4 (agent): Run the file, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy/notes.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** ` Test Files  1 passed (1)`, `      Tests  4 passed (4)`; ` Test Files  76 passed (76)`, `      Tests  546 passed (546)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/notes.ts frontend/src/lib/liturgy/notes.test.ts
git commit -q -m "Reviewer: the notes' rules (R Notes; S4 reviewer amendment stale-results rule)" -m "A review's notes stay on a card only while it holds the text and origin
that were reviewed, go on any later change and all go with a new
service. Dismiss one at a time; Looks good only for a card that came back
with none; Revise only on an AI card with a note left. Pure, in memory." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 7: backend **1213 passed, 11 skipped**; frontend **546 in 76**.

### Task 8: The review provider, and one sermon loader for generation and the reviewer (R "User experience", API "sermon_text"; S4 reviewer amendment "UI hooks", "Sermon text"; F §1.8, §4.4; clarifications 17-21, 23)

`LiturgyReviewProvider` sits beside 4b's `LiturgyGenerationProvider` in the builder shell, so a review keeps going on the other steps and leaving `/builder`, switching church or signing out cancels it. It holds the review, the running state, a failed review's message, the polite announcement, and the revisions. The sermon loader moves unchanged out of `generation.tsx` into `lib/liturgy/sermon.ts` (`useSermonLoader`), so review and revise send exactly the sermon text generation sends (S4 "Sermon text"); 4b's generation tests pass unchanged. A revision's result goes through `applyGenerated` (origin "ai") inside the draft update, only while the card still holds what was sent, and its Undo is the generation provider's Undo line with a new kind, "revised".

**Files:**
- Create: `frontend/src/lib/liturgy/sermon.ts`, `frontend/src/lib/liturgy/review.tsx`, `frontend/src/lib/liturgy/review.test.tsx`
- Modify: `frontend/src/lib/liturgy/generation.tsx`, `frontend/src/components/builder/builder-shell.tsx`, `frontend/src/components/builder/liturgy/section-card.tsx` (the "revised" Undo line)

**Interfaces:**
- Consumes: T6 (`reviewService`, `reviseSection`, `reviewTargets`, `buildReviewRequest`, `buildReviseRequest`), T7 (the notes' rules); 4b's `useDraft` (`peek`, `update`), `useApi`, `reportAuthErrors`, `cardErrorFrom`, `applyGenerated`, `useLiturgyGeneration().setUndo`, `SECTION_LABELS`.
- Produces (later users: T9, T10):
  - `useSermonLoader(church, waitMs = SERMON_WAIT_MS) -> (signal) => Promise<SermonText | null>`; `generation.tsx` re-exports `SERMON_WAIT_MS`
  - `UndoEntry.kind` gains `"revised"`, shown as "Revised with these notes."
  - `LiturgyReviewProvider({church, sermonWaitMs?, children})`, `useLiturgyReview() -> {review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise}`, `reviewDoneMessage(n)`

- [ ] **Step 1 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/review.test.tsx`:**

````tsx
/**
 * The review provider (reviewer spec, "User experience", API; slice 4 spec,
 * reviewer amendment "UI hooks", "Sermon text" and Testing): one review of
 * every switched-on card with text, with generation's resolved sermon text
 * (WEB for an ESV church); notes in memory only; a card changed meanwhile
 * gets none; cancel, a failure and New service; Revise with its Undo and the
 * stale rule. The step's own tests (`review-step.test.tsx`) cover the screen.
 */
import { act, screen, waitFor } from "@testing-library/react";
import { useEffect } from "react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { ReviewBody, ReviseBody } from "@/lib/api/types";
import { DraftProvider, useDraft, type DraftApi } from "@/lib/draft/context";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  me,
  reviewNote,
  reviewResult,
  reviewRoute,
  reviseRoute,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { editCardText } from "./cards";
import { LiturgyGenerationProvider, useLiturgyGeneration } from "./generation";
import { LiturgyReviewProvider, reviewDoneMessage, useLiturgyReview, type LiturgyReview } from "./review";

const KEY = draftKey(USER_ID, church().id);
const STOCK = 'Stock phrase "as we journey". Say it more naturally.';
const PHILIPPIANS = {
  reference: "Philippians 3:4b-14",
  status: "ok",
  sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
};

const handle: { current: LiturgyReview | null } = { current: null };
const draftHandle: { current: DraftApi | null } = { current: null };
/** The generation provider, for Undo (as the card's Undo button calls it). */
const generationHandle: { current: ReturnType<typeof useLiturgyGeneration> | null } = { current: null };

function Probe() {
  const review = useLiturgyReview();
  const generation = useLiturgyGeneration();
  const api = useDraft();
  useEffect(() => {
    handle.current = review;
    draftHandle.current = api;
    generationHandle.current = generation;
  });
  const r = review.review;
  const cards = (["call_to_worship", "opening_prayer", "benediction"] as SectionKey[]).map((key) => {
    const notes = r?.cards[key];
    const shown = notes === undefined ? "none" : notes.notes.map((n) => n.text).join(" | ") || "looks good";
    return `${key}: ${api.draft.liturgy.cards[key].text} [${api.draft.liturgy.cards[key].origin}] notes ${shown}; revising ${review.revising[key] ? "yes" : "no"}; error ${review.reviseErrors[key]?.message ?? "none"}; undo ${generation.undo[key]?.kind ?? "none"}`;
  });
  return (
    <ul aria-label="review">
      <li>running: {review.running ? "yes" : "no"}</li>
      <li>status: {r?.aiStatus ?? "none"}; service: {r?.service.map((n) => n.text).join(" | ") || "none"}</li>
      <li>error: {review.error ?? "none"}</li>
      <li>said: {review.announcement || "nothing"}</li>
      {cards.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}

function card(d: DraftV1, key: SectionKey, text: string, origin: DraftV1["liturgy"]["cards"]["benediction"]["origin"], enabled = true): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { enabled, text, origin } } } };
}

/** October 4's readings (the NT reading is Philippians), a typed Call to Worship, an AI Opening Prayer, the default Benediction. */
function seeded(): DraftV1 {
  let d = editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46");
  d = card(d, "call_to_worship", "Leader: As we journey, come.", "typed");
  d = card(d, "opening_prayer", "Gracious God, as we journey, hear us.", "ai");
  return card(d, "prayer_of_confession", "Merciful God,", "archive", false);
}

function renderProvider(routes: Record<string, FakeHandler>, profile = churchProfile(), draft = seeded()) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({ "POST /scripture/passages": { passages: [PHILIPPIANS] }, ...routes });
  const view = renderWithProviders(
    <>
      <DraftProvider userId={USER_ID} church={profile}>
        <LiturgyGenerationProvider church={profile}>
          <LiturgyReviewProvider church={profile} sermonWaitMs={2_000}>
            <Probe />
          </LiturgyReviewProvider>
        </LiturgyGenerationProvider>
      </DraftProvider>
      <Toaster />
    </>,
    { me: me(), church: church() },
  );
  return Object.assign(api, { view });
}

const ANSWER = reviewResult({
  cards: [
    { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code")] },
    { section: "opening_prayer", notes: [reviewNote("rules", STOCK, "code"), reviewNote("read_aloud", "The prayer runs long.")] },
    { section: "benediction", notes: [] },
  ],
  service_notes: [reviewNote("repetition", "Two prayers say journey.")],
});

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the review (R User experience, API)", () => {
  it("reviews every switched-on card with text once, with generation's sermon text (WEB for ESV), notes in memory only", async () => {
    const api = renderProvider(
      { "POST /liturgy/review": reviewRoute(() => ANSWER) },
      churchProfile({ effective_translation: "esv", bible_translation: "esv" }),
    );
    act(() => handle.current?.start());
    expect(screen.getByText("running: yes")).toBeInTheDocument();
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    expect(screen.getByText("running: no")).toBeInTheDocument();
    expect(screen.getByText(`opening_prayer: Gracious God, as we journey, hear us. [ai] notes ${STOCK} | The prayer runs long.; revising no; error none; undo none`)).toBeInTheDocument();
    expect(screen.getByText(/^benediction: Halverson \[default\] notes looks good;/)).toBeInTheDocument();
    expect(screen.getByText("status: ok; service: Two prayers say journey.")).toBeInTheDocument();
    const passages = api.requests.filter((r) => r.path === "/scripture/passages");
    expect(passages.map((r) => r.body)).toEqual([{ refs: ["Philippians 3:4b-14"], translation: "web" }]);
    const reviews = api.requests.filter((r) => r.path === "/liturgy/review");
    expect(reviews).toHaveLength(1);
    const body = reviews[0].body as ReviewBody;
    expect(body.cards.map((c) => [c.section, c.origin])).toEqual([
      ["call_to_worship", "typed"],
      ["opening_prayer", "ai"],
      ["benediction", "default"],
    ]);
    expect(body.sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "I press on toward the goal." });
    // Never saved: the stored draft holds no note.
    await waitFor(() => expect(window.localStorage.getItem(KEY)).toContain("as we journey"));
    expect(window.localStorage.getItem(KEY)).not.toContain("runs long");
    expect(reviewDoneMessage(1)).toBe("Review finished. 1 note.");
    expect(reviewDoneMessage(0)).toBe("Review finished. No notes.");
  });

  it("gives no notes to a card edited while the review ran; Cancel and a failure keep the notes already shown", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const api = renderProvider({
      "POST /liturgy/review": reviewRoute(async () => {
        await gate;
        return ANSWER;
      }),
    });
    act(() => handle.current?.start());
    await waitFor(() => expect(api.requests.some((r) => r.path === "/liturgy/review")).toBe(true));
    act(() => draftHandle.current?.update((d) => editCardText(d, "call_to_worship", "Leader: Come, all.")));
    act(() => handle.current?.start()); // already running: nothing more is sent
    release();
    expect(await screen.findByText("said: Review finished. 3 notes.")).toBeInTheDocument();
    expect(screen.getByText(/^call_to_worship: Leader: Come, all\. \[typed\] notes none;/)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(1);

    // Cancel: nothing changes, and the next review can start.
    api.set("POST /liturgy/review", () => new Promise<never>(() => {}));
    act(() => handle.current?.start());
    expect(screen.getByText("running: yes")).toBeInTheDocument();
    act(() => handle.current?.cancel());
    expect(screen.getByText("running: no")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: .* notes Stock phrase/)).toBeInTheDocument();
    // A failure shows its message and keeps the notes.
    api.set("POST /liturgy/review", fakeError(500, "internal_error", "Something went wrong."));
    act(() => handle.current?.start());
    expect(await screen.findByText("error: Something went wrong. (Ref: 4f9a2c1e)")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: .* notes Stock phrase/)).toBeInTheDocument();
  });

  it("New service drops every note and stops a running review silently", async () => {
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER) });
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    api.set("POST /liturgy/review", () => new Promise<never>(() => {}));
    act(() => handle.current?.start());
    const current = draftHandle.current!.peek();
    act(() => draftHandle.current?.replace({ ...current, created_at: "2026-09-29T16:30:00.000Z" }));
    expect(screen.getByText("running: no")).toBeInTheDocument();
    expect(screen.getByText("status: none; service: none")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: .* notes none;/)).toBeInTheDocument();
  });
});

describe("Revise with these notes (R Revise)", () => {
  async function reviewed(routes: Record<string, FakeHandler>) {
    const api = renderProvider({ "POST /liturgy/review": reviewRoute(() => ANSWER), ...routes });
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    return api;
  }

  it("sends the card's text and remaining notes, then replaces it as an AI draft with Undo", async () => {
    const api = await reviewed({ "POST /liturgy/revise": reviseRoute(() => ({ text: "Gracious God, hear us." })) });
    act(() => handle.current?.dismiss("opening_prayer", "opening_prayer-1"));
    act(() => handle.current?.revise("call_to_worship")); // typed: never revised
    act(() => handle.current?.revise("opening_prayer"));
    expect(screen.getByText(/^opening_prayer: .*revising yes;/)).toBeInTheDocument();
    expect(await screen.findByText("opening_prayer: Gracious God, hear us. [ai] notes none; revising no; error none; undo revised")).toBeInTheDocument();
    const revisions = api.requests.filter((r) => r.path === "/liturgy/revise");
    expect(revisions).toHaveLength(1);
    expect(revisions[0].body as ReviseBody).toMatchObject({
      section: "opening_prayer",
      text: "Gracious God, as we journey, hear us.",
      notes: [STOCK],
      sermon_text: { ref: "Philippians 3:4b-14", text: "I press on toward the goal." },
    });
    act(() => generationHandle.current?.applyUndo("opening_prayer"));
    expect(await screen.findByText(/^opening_prayer: Gracious God, as we journey, hear us\. \[ai\] notes none;/)).toBeInTheDocument();
  });

  it("keeps a card edited meanwhile, and shows why a revision failed", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const api = await reviewed({
      "POST /liturgy/revise": reviseRoute(async () => {
        await gate;
        return { text: "Revised." };
      }),
    });
    act(() => handle.current?.revise("opening_prayer"));
    await waitFor(() => expect(api.requests.some((r) => r.path === "/liturgy/revise")).toBe(true));
    act(() => draftHandle.current?.update((d) => editCardText(d, "opening_prayer", "My own words.")));
    release();
    expect(await screen.findByText("Kept your edits, so the revised draft for Opening Prayer was not used.")).toBeInTheDocument();
    expect(screen.getByText(/^opening_prayer: My own words\. \[typed\] notes none; revising no;/)).toBeInTheDocument();

    act(() => draftHandle.current?.update((d) => card(d, "opening_prayer", "Holy One, as we journey.", "ai")));
    act(() => handle.current?.start());
    expect(await screen.findByText("said: Review finished. 4 notes.")).toBeInTheDocument();
    api.set("POST /liturgy/revise", fakeError(422, "prompt_invalid", "This prayer is too long to revise."));
    act(() => handle.current?.revise("opening_prayer"));
    expect(await screen.findByText(/^opening_prayer: Holy One, as we journey\. \[ai\] notes Stock phrase.*; revising no; error This prayer is too long to revise\.;/)).toBeInTheDocument();
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/review.test.tsx 2>&1 | grep -E "Failed to (load|resolve)|Test Files|Tests ")
```

**Expected:** @@RED8@@

- [ ] **Step 3 (agent): Move the sermon loader, write the provider, mount it**

**Create `frontend/src/lib/liturgy/sermon.ts`:**

````ts
"use client";

/**
 * The sermon text a liturgy request carries (slice 4 spec, "Sermon text";
 * reviewer spec, API: review and revise send the same resolved sermon text as
 * generation). One loader, used by the generation provider for each batch and
 * by the review provider for each review or revision.
 *
 * `useSermonLoader(church, waitMs)` returns `load(signal)`: the effective NT
 * reading in the translation step 1 shows (the draft's only while the server
 * still offers it), WEB instead of ESV (Crossway's terms), read through the
 * passage cache with `queryClient.fetchQuery` (a passage already cached is
 * reused), at most `waitMs` (10 s); a failure, a timeout or an abort resolves
 * to null, and the request goes without it.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import type { ChurchProfile, SermonText, Translations } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { useApi } from "@/lib/queries/client";
import { keys as queryKeys } from "@/lib/queries/keys";
import { passageQuery } from "@/lib/queries/passages";

import { sermonSource, sermonText } from "./request";

/** How long a request waits for the sermon text before going without it (S "Sermon text"). */
export const SERMON_WAIT_MS = 10_000;

export function useSermonLoader(
  church: Pick<ChurchProfile, "effective_translation">,
  waitMs: number = SERMON_WAIT_MS,
): (signal: AbortSignal) => Promise<SermonText | null> {
  const { peek } = useDraft();
  const api = useApi();
  const queryClient = useQueryClient();
  const churchTranslation = church.effective_translation;
  return useCallback(
    (signal: AbortSignal): Promise<SermonText | null> => {
      const draft = peek();
      return new Promise((resolve) => {
        let settled = false;
        const done = (value: SermonText | null) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          signal.removeEventListener("abort", onAbort);
          resolve(value);
        };
        const onAbort = () => done(null);
        const timer = setTimeout(() => done(null), waitMs);
        signal.addEventListener("abort", onAbort, { once: true });
        void (async () => {
          // The translation step 1 shows: the draft's only while the server still offers it (the list, cached or fetched once).
          const translations =
            draft.readings.translation === null
              ? undefined
              : await queryClient
                  .fetchQuery({
                    queryKey: queryKeys.translations(),
                    queryFn: ({ signal: s }) => api.user<Translations>("/translations", { signal: s }),
                    staleTime: Infinity,
                  })
                  .catch(() => undefined);
          const source = sermonSource(draft, { effective_translation: churchTranslation }, translations);
          if (source === null) return done(null);
          const passage = await queryClient.fetchQuery(passageQuery(api, source.translation, source.ref));
          done(sermonText(source.ref, passage));
        })().catch(() => done(null));
      });
    },
    [api, churchTranslation, peek, queryClient, waitMs],
  );
}
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
 *   (the effective NT reading in the translation step 1 shows, WEB for ESV,
 *   `queryClient.fetchQuery` through `passageQuery`, at most 10 s; a failure
 *   or a timeout just leaves it out), then each section is one request, at
 *   most 3 in flight.
````

**with:**

````tsx
 *   (`useSermonLoader` in `sermon.ts`, shared with the service reviewer: the
 *   effective NT reading in the translation step 1 shows, WEB for ESV, at
 *   most 10 s; a failure or a timeout just leaves it out), then each section
 *   is one request, at most 3 in flight.
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
 */
import { useQueryClient } from "@tanstack/react-query";
````

**with:**

````tsx
 *   The service reviewer's Revise sets the same kind of Undo ("revised").
 */
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
import type { ChurchProfile, SectionResult, SermonText, Translations } from "@/lib/api/types";
````

**with:**

````tsx
import type { ChurchProfile, SectionResult, SermonText } from "@/lib/api/types";
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
import { keys as queryKeys } from "@/lib/queries/keys";
import { generateSection } from "@/lib/queries/liturgy";
import { passageQuery } from "@/lib/queries/passages";
````

**with:**

````tsx
import { generateSection } from "@/lib/queries/liturgy";
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
import { buildGenerateRequest, sermonSource, sermonText } from "./request";
import { SECTION_LABELS } from "./sections";
````

**with:**

````tsx
import { buildGenerateRequest } from "./request";
import { SECTION_LABELS } from "./sections";
import { SERMON_WAIT_MS, useSermonLoader } from "./sermon";

export { SERMON_WAIT_MS } from "./sermon";
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
export const MAX_IN_FLIGHT = 3;
/** How long a batch waits for the sermon text before going without it (S "Sermon text"). */
export const SERMON_WAIT_MS = 10_000;
````

**with:**

````tsx
export const MAX_IN_FLIGHT = 3;
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
export type UndoEntry = { kind: "replaced" | "cleared"; previous: CardSnapshot; after: string };
````

**with:**

````tsx
export type UndoEntry = { kind: "replaced" | "cleared" | "revised"; previous: CardSnapshot; after: string };
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx
  const queryClient = useQueryClient();
  const churchTranslation = church.effective_translation;
````

**with:**

````tsx
  const loadSermon = useSermonLoader(church, sermonWaitMs);
````

**In `frontend/src/lib/liturgy/generation.tsx`, replace:**

````tsx

  const loadSermon = useCallback(
    (signal: AbortSignal): Promise<SermonText | null> => {
      const draft = peek();
      return new Promise((resolve) => {
        let settled = false;
        const done = (value: SermonText | null) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          signal.removeEventListener("abort", onAbort);
          resolve(value);
        };
        const onAbort = () => done(null);
        const timer = setTimeout(() => done(null), sermonWaitMs);
        signal.addEventListener("abort", onAbort, { once: true });
        void (async () => {
          // The translation step 1 shows: the draft's only while the server still offers it (the list, cached or fetched once).
          const translations =
            draft.readings.translation === null
              ? undefined
              : await queryClient
                  .fetchQuery({
                    queryKey: queryKeys.translations(),
                    queryFn: ({ signal: s }) => api.user<Translations>("/translations", { signal: s }),
                    staleTime: Infinity,
                  })
                  .catch(() => undefined);
          const source = sermonSource(draft, { effective_translation: churchTranslation }, translations);
          if (source === null) return done(null);
          const passage = await queryClient.fetchQuery(passageQuery(api, source.translation, source.ref));
          done(sermonText(source.ref, passage));
        })().catch(() => done(null));
      });
    },
    [api, churchTranslation, peek, queryClient, sermonWaitMs],
  );

  const send = useCallback(
````

**with:**

````tsx

  const send = useCallback(
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
const UNDO_LINES = { replaced: "Replaced with a new AI draft.", cleared: "Cleared." } as const;
````

**with:**

````tsx
const UNDO_LINES = {
  replaced: "Replaced with a new AI draft.",
  cleared: "Cleared.",
  // The service reviewer's "Revise with these notes".
  revised: "Revised with these notes.",
} as const;
````

**Create `frontend/src/lib/liturgy/review.tsx`:**

````tsx
"use client";

/**
 * `LiturgyReviewProvider` and `useLiturgyReview()` (reviewer spec, "User
 * experience"; slice 4 spec, reviewer amendment "UI hooks"). Mounted in the
 * builder shell inside the generation provider, beside it, so a review keeps
 * going while the member moves between steps; leaving `/builder`, switching
 * church or signing out unmounts it and cancels everything.
 *
 * - The notes live here, in memory only (`notes.ts`): never in the draft, the
 *   archive or `localStorage`.
 * - `start()`: every switched-on card with text (`reviewTargets`), captured
 *   when pressed, with the same resolved sermon text as generation
 *   (`useSermonLoader`), in one `POST /liturgy/review` (100 s). The answer
 *   replaces the last review; a card changed meanwhile gets no notes, and a
 *   new service drops the answer (`applyReview`). `cancel()` aborts the wait
 *   and keeps the notes already shown. A request-level failure (timeout, the
 *   network, a 5xx) keeps them too and shows its message in `error`; a 401 or
 *   a lost church goes to the app's handling and shows nothing.
 * - Every draft change prunes the notes of cards whose text or origin changed
 *   (`pruneReview`); a new service (a new `created_at`) cancels the review and
 *   every revision silently and drops all notes.
 * - `revise(key)`: an AI card with notes left; its text and remaining notes,
 *   with the sermon text, in one `POST /liturgy/revise` (100 s). The result
 *   replaces the card (origin "ai") only while the card still holds what was
 *   sent and the service is the same; then the generation provider's Undo
 *   line ("revised") keeps the previous text and origin. Otherwise nothing
 *   changes and a toast says why. A failure shows on the card's notes.
 * - `announcement`: the polite line read out when a review ends.
 */
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
import type { ChurchProfile } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { reviewService, reviseSection } from "@/lib/queries/liturgy";

import { applyGenerated, type CardSnapshot } from "./cards";
import { cardErrorFrom, type CardError } from "./errors";
import { useLiturgyGeneration } from "./generation";
import { applyReview, canRevise, captureReview, dismissNote, noteCount, pruneReview, type ServiceReview } from "./notes";
import { buildReviewRequest, buildReviseRequest, reviewTargets } from "./request";
import { SECTION_LABELS } from "./sections";
import { useSermonLoader } from "./sermon";

export type LiturgyReview = {
  review: ServiceReview | null;
  running: boolean;
  /** The last review's request-level failure (its message), or null. */
  error: string | null;
  /** Read out politely when a review ends. */
  announcement: string;
  start: () => void;
  cancel: () => void;
  dismiss: (where: SectionKey | "service", id: string) => void;
  /** Cards whose revision is running. */
  revising: Partial<Record<SectionKey, true>>;
  reviseErrors: Partial<Record<SectionKey, CardError>>;
  revise: (key: SectionKey) => void;
  cancelRevise: (key: SectionKey) => void;
};

const ReviewContext = createContext<LiturgyReview | null>(null);

/** The line read out when a review ends. */
export function reviewDoneMessage(notes: number): string {
  if (notes === 0) return "Review finished. No notes.";
  return notes === 1 ? "Review finished. 1 note." : `Review finished. ${notes} notes.`;
}

function without<T>(record: Partial<Record<SectionKey, T>>, key: SectionKey): Partial<Record<SectionKey, T>> {
  if (!(key in record)) return record;
  const next = { ...record };
  delete next[key];
  return next;
}

export function LiturgyReviewProvider({
  church,
  sermonWaitMs,
  children,
}: {
  church: Pick<ChurchProfile, "id" | "effective_translation">;
  /** Tests shorten the sermon-text wait. */
  sermonWaitMs?: number;
  children: ReactNode;
}) {
  const { draft, update, peek } = useDraft();
  const api = useApi();
  const { setUndo } = useLiturgyGeneration();
  const loadSermon = useSermonLoader(church, sermonWaitMs);
  const [review, setReview] = useState<ServiceReview | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [revising, setRevising] = useState<Partial<Record<SectionKey, true>>>({});
  const [reviseErrors, setReviseErrors] = useState<Partial<Record<SectionKey, CardError>>>({});
  const reviewRef = useRef<ServiceReview | null>(null);
  const active = useRef<AbortController | null>(null);
  const revisions = useRef(new Map<SectionKey, AbortController>());
  const mounted = useRef(true);
  const service = useRef(draft.created_at);

  useEffect(() => {
    reviewRef.current = review;
  }, [review]);

  useEffect(() => {
    mounted.current = true;
    const waits = revisions.current;
    return () => {
      mounted.current = false;
      active.current?.abort();
      for (const controller of waits.values()) controller.abort();
    };
  }, []);

  // Every draft change, during render: notes whose card changed go (typing, Regenerate, Revise, Clear text, the
  // church default, Undo), so they never show for a single frame, and an Undo never brings them back.
  const [pruned, setPruned] = useState(draft);
  if (pruned !== draft) {
    setPruned(draft);
    setReview((current) => pruneReview(current, draft));
  }

  // A new service (or a saved one loaded): the review and every revision belonged to the old draft.
  const createdAt = draft.created_at;
  useEffect(() => {
    if (service.current === createdAt) return;
    service.current = createdAt;
    active.current?.abort();
    active.current = null;
    for (const controller of revisions.current.values()) controller.abort();
    revisions.current.clear();
    setRunning(false);
    setRevising({});
    setReviseErrors({});
    setError(null);
    setReview(null);
  }, [createdAt]);

  const handleFailure = useCallback(
    (e: unknown): CardError | null => {
      if (e instanceof ApiError && (e.status === 401 || isNoChurchAccess(e))) reportAuthErrors(e, church.id);
      return cardErrorFrom(e);
    },
    [church.id],
  );

  const start = useCallback(() => {
    if (active.current !== null) return;
    const asked = peek();
    const keys = reviewTargets(asked);
    if (keys.length === 0) return;
    const ask = captureReview(asked, keys);
    const controller = new AbortController();
    active.current = controller;
    setRunning(true);
    setError(null);
    setAnnouncement("");
    setReviseErrors({});
    void (async () => {
      try {
        const sermon = await loadSermon(controller.signal);
        if (controller.signal.aborted) return;
        const result = await reviewService(api.church, buildReviewRequest(asked, keys, sermon), controller.signal);
        if (!mounted.current || active.current !== controller) return;
        const { review: next } = applyReview(peek(), ask, result);
        setReview(next);
        if (next !== null) setAnnouncement(reviewDoneMessage(noteCount(next)));
      } catch (e) {
        if (!mounted.current || active.current !== controller) return;
        setError(handleFailure(e)?.message ?? null);
      } finally {
        if (active.current === controller) {
          active.current = null;
          if (mounted.current) setRunning(false);
        }
      }
    })();
  }, [api, handleFailure, loadSermon, peek]);

  const cancel = useCallback(() => {
    active.current?.abort();
    active.current = null;
    setRunning(false);
  }, []);

  const dismiss = useCallback((where: SectionKey | "service", id: string) => {
    setReview((current) => (current === null ? null : dismissNote(current, where, id)));
  }, []);

  const revise = useCallback(
    (key: SectionKey) => {
      if (revisions.current.has(key)) return;
      const asked = peek();
      const card = asked.liturgy.cards[key];
      const notes = reviewRef.current?.cards[key];
      if (!canRevise(card, notes) || notes === undefined) return;
      const sent = { createdAt: asked.created_at, text: card.text, origin: card.origin };
      const controller = new AbortController();
      revisions.current.set(key, controller);
      setRevising((current) => ({ ...current, [key]: true }));
      setReviseErrors((current) => without(current, key));
      void (async () => {
        try {
          const sermon = await loadSermon(controller.signal);
          if (controller.signal.aborted) return;
          const body = buildReviseRequest(asked, key, notes.notes.map((n) => n.text), sermon);
          const text = await reviseSection(api.church, body, controller.signal);
          if (!mounted.current || revisions.current.get(key) !== controller) return;
          const out: { verdict: "apply" | "service_changed" | "edited"; previous: CardSnapshot | null } = {
            verdict: "apply",
            previous: null,
          };
          update((d) => {
            const now = d.liturgy.cards[key];
            if (d.created_at !== sent.createdAt) out.verdict = "service_changed";
            else if (now.text !== sent.text || now.origin !== sent.origin) out.verdict = "edited";
            if (out.verdict !== "apply") return d;
            out.previous = { text: now.text, origin: now.origin };
            return applyGenerated(d, key, text);
          });
          const label = SECTION_LABELS[key];
          if (out.verdict === "service_changed") toast.message(`The service changed, so the revised draft for ${label} was discarded.`);
          else if (out.verdict === "edited") toast.message(`Kept your edits, so the revised draft for ${label} was not used.`);
          else if (out.previous !== null) setUndo(key, { kind: "revised", previous: out.previous, after: text });
        } catch (e) {
          if (!mounted.current || revisions.current.get(key) !== controller) return;
          const failure = handleFailure(e);
          if (failure !== null) setReviseErrors((current) => ({ ...current, [key]: failure }));
        } finally {
          if (revisions.current.get(key) === controller) {
            revisions.current.delete(key);
            if (mounted.current) setRevising((current) => without(current, key));
          }
        }
      })();
    },
    [api, handleFailure, loadSermon, peek, setUndo, update],
  );

  const cancelRevise = useCallback((key: SectionKey) => {
    revisions.current.get(key)?.abort();
    revisions.current.delete(key);
    setRevising((current) => without(current, key));
  }, []);

  const value = useMemo<LiturgyReview>(
    () => ({ review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise }),
    [review, running, error, announcement, start, cancel, dismiss, revising, reviseErrors, revise, cancelRevise],
  );
  return <ReviewContext value={value}>{children}</ReviewContext>;
}

/** The review state and actions. Throws outside `LiturgyReviewProvider` (the builder shell mounts it). */
export function useLiturgyReview(): LiturgyReview {
  const value = useContext(ReviewContext);
  if (!value) throw new Error("useLiturgyReview() must be used inside <LiturgyReviewProvider>.");
  return value;
}
````

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

````tsx
 * step's AI runs, so they keep going on the other steps (slice 4b).
````

**with:**

````tsx
 * step's AI runs, so they keep going on the other steps (slice 4b), and
 * `<LiturgyReviewProvider>` the service reviewer's review, notes and
 * revisions, in memory only.
````

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

````tsx
import { LiturgyGenerationProvider } from "@/lib/liturgy/generation";
````

**with:**

````tsx
import { LiturgyGenerationProvider } from "@/lib/liturgy/generation";
import { LiturgyReviewProvider } from "@/lib/liturgy/review";
````

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

````tsx
        <LectionarySync>
          <BuilderFrame church={profile.data}>{children}</BuilderFrame>
        </LectionarySync>
````

**with:**

````tsx
        <LiturgyReviewProvider church={profile.data}>
          <LectionarySync>
            <BuilderFrame church={profile.data}>{children}</BuilderFrame>
          </LectionarySync>
        </LiturgyReviewProvider>
````

- [ ] **Step 4 (agent): Run the provider's file three times, generation's, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/lib/liturgy/review.test.tsx 2>&1 | grep -E "Tests "); done
(cd frontend && npx vitest run src/lib/liturgy/generation.test.tsx 2>&1 | grep -E "Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  5 passed (5)` three times; `      Tests  12 passed (12)` (4b's generation tests, unchanged); ` Test Files  77 passed (77)`, `      Tests  551 passed (551)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/sermon.ts frontend/src/lib/liturgy/review.tsx frontend/src/lib/liturgy/review.test.tsx frontend/src/lib/liturgy/generation.tsx frontend/src/components/builder/builder-shell.tsx frontend/src/components/builder/liturgy/section-card.tsx
git commit -q -m "Reviewer: the review provider and one sermon loader (R User experience; S4 reviewer amendment)" -m "LiturgyReviewProvider sits beside the generation provider: one review of
every switched-on card with text, the notes in memory only, pruned as
cards change and dropped with a new service; Revise applies its text only
over what was sent and keeps an Undo. The sermon loader moves to
lib/liturgy/sermon.ts so review and revise send generation's sermon text." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 6 (controller): Review checkpoint (end of batch B) and backup push**

Review T6-T8 together: the bodies send no custom element, hymn or reading text as a card; the 100 s rows; nothing the reviewer holds reaches `localStorage` (T8's first test reads it); the stale rule compares text and origin; 4b's generation tests unchanged. Then the backup push.

Counts after Task 8: backend **1213 passed, 11 skipped**; frontend **551 in 77**.

### Task 9: Review service on the step: the button, the notes, "Looks good.", "Across the service" and the quick-checks line (R "Review service", "Notes", "Other rules", Testing "Frontend"; S4 reviewer amendment "UI hooks"; F §1.8, §4.8, §4.9; clarifications 18-25)

The header gets "Review service" beside the "Liturgy" heading (it wraps under it at 375 px). One button: "Review service" when idle, `aria-disabled` while no switched-on card has text, and "Cancel" (named "Cancel review") while a review runs, so focus stays on it. Under the header: a spinner with "Reviewing…" (and the shared "Still working — this can take up to a minute." after 8 s), a failed review's message, the quiet "Only quick checks ran. The full review isn't available right now." when `ai_status` is not "ok", and a polite announcement of how many notes the review left. Then the "Across the service" box. Under each reviewed card's text: its notes (a tag chip, the sentence, a 44 px ×) or "Looks good."; the notes describe the textarea. Dismissing a note moves focus to the next note's ×, else the previous one's, else the card's heading (the Review button for the box).

**Files:**
- Create: `frontend/src/components/builder/liturgy/review-bar.tsx`, `frontend/src/components/builder/liturgy/card-notes.tsx`, `frontend/src/components/builder/liturgy/review-step.test.tsx`
- Modify: `frontend/src/components/builder/liturgy/liturgy-step.tsx`, `frontend/src/components/builder/liturgy/section-card.tsx`

**Interfaces:**
- Consumes: T7 (`TAG_LABELS`, `LOOKS_GOOD`, `QUICK_CHECKS_ONLY`, `Note`), T8 (`useLiturgyReview`), T6 (`reviewTargets`, the fixtures); 4b's `useStillWorking`, `STILL_WORKING`, `Badge`, `Button`, `Alert`.
- Produces (later user: T10): `ReviewButton`, `ReviewStatus`, `REVIEW_BUTTON_ID`; `CardNotes({sectionKey, label, headingId})`, `ServiceNotes`, `NoteList`, `notesId(key)`.

- [ ] **Step 1 (agent): Write the failing tests**

**Create `frontend/src/components/builder/liturgy/review-step.test.tsx`:**

````tsx
/**
 * The service reviewer on the Liturgy step (reviewer spec, "User experience"
 * and Testing "Frontend"; slice 4 spec, reviewer amendment "UI hooks" and
 * Testing). The step runs inside the real builder layout against the fake
 * API. The clock is Tuesday, September 29, 2026 (only `Date` is faked).
 */
import { act, screen, waitFor, within } from "@testing-library/react";
import { toast } from "sonner";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BuilderLayout from "@/app/(signed-in)/(church)/builder/layout";
import { Toaster } from "@/components/ui/sonner";
import type { ReviewBody } from "@/lib/api/types";
import { draftKey, type DraftV1, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler } from "@/test/fake-api";
import {
  church,
  churchProfile,
  DRAFT_NOW,
  generateRoute,
  lectionaryRoute,
  liturgyConfig,
  me,
  reviewNote,
  reviewResult,
  reviewRoute,
  testDraft,
  USER_ID,
} from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyStep } from "./liturgy-step";
import { STILL_WORKING } from "./use-still-working";

const KEY = draftKey(USER_ID, church().id);
const STOCK = 'Stock phrase "as we journey". Say it more naturally.';
const QUICK = "Only quick checks ran. The full review isn't available right now.";

type Origin = DraftV1["liturgy"]["cards"]["benediction"]["origin"];

function withCard(d: DraftV1, key: SectionKey, text: string, origin: Origin, enabled = true): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { enabled, text, origin } } } };
}

/** A typed Call to Worship, an AI Opening Prayer and Assurance, an archived Confession, the default Benediction. */
function seeded(): DraftV1 {
  let d = withCard(testDraft(), "call_to_worship", "Leader: As we journey, come.", "typed");
  d = withCard(d, "opening_prayer", "Gracious God, as we journey, hear us.", "ai");
  d = withCard(d, "prayer_of_confession", "Merciful God, we confess.", "archive");
  d = withCard(d, "assurance", "Leader: In Christ we are forgiven.", "ai");
  return {
    ...d,
    liturgy: { ...d.liturgy, custom_elements: [{ id: "c1", label: "Children's Moment", text: "As we journey", insert_after: "opening_prayer" }] },
  };
}

const ANSWER = reviewResult({
  cards: [
    { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code")] },
    {
      section: "opening_prayer",
      notes: [reviewNote("rules", STOCK, "code"), reviewNote("read_aloud", "The second clause is hard to say aloud.")],
    },
    { section: "prayer_of_confession", notes: [reviewNote("theology", "Confession comes before any word of grace.")] },
    { section: "assurance", notes: [reviewNote("checklist", "Name Christ as the source of pardon.")] },
    { section: "benediction", notes: [] },
  ],
  service_notes: [reviewNote("repetition", 'Several prayers open with "Gracious God".', "code")],
});

function renderStep(draft: DraftV1 = seeded(), routes: Record<string, FakeHandler> = {}) {
  window.localStorage.setItem(KEY, JSON.stringify(draft));
  const api = installFakeApi({
    "GET /church": churchProfile(),
    "GET /lectionary/readings": lectionaryRoute(),
    "GET /liturgy/config": liturgyConfig(),
    "POST /liturgy/review": reviewRoute(() => ANSWER),
    ...routes,
  });
  const view = renderWithProviders(
    <>
      <BuilderLayout>
        <LiturgyStep />
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

function reviewButton() {
  return screen.getByRole("button", { name: "Review service" });
}

async function review(user: ReturnType<typeof renderStep>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Review service" }));
  await screen.findByText("Review finished. 6 notes.");
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
  toast.dismiss(); // sonner replays a toast still showing to the next Toaster
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Review service (R User experience)", () => {
  it("is off until a switched-on card has text, then shows each card's notes, Looks good. and Across the service", async () => {
    const empty = renderStep(testDraft((d) => withCard(d, "benediction", "Halverson", "default", false)));
    const off = await screen.findByRole("button", { name: "Review service" });
    expect(off).toHaveAttribute("aria-disabled", "true");
    await empty.user.click(off);
    expect(empty.api.requests.some((r) => r.path === "/liturgy/review")).toBe(false);
    empty.unmount();

    const { user, api } = renderStep();
    await review(user);
    // Every switched-on card with text, in order; never a custom element, hymn or reading.
    const sent = api.requests.find((r) => r.path === "/liturgy/review")?.body as ReviewBody;
    expect(sent.cards.map((c) => [c.section, c.origin])).toEqual([
      ["call_to_worship", "typed"],
      ["opening_prayer", "ai"],
      ["prayer_of_confession", "archive"],
      ["assurance", "ai"],
      ["benediction", "default"],
    ]);
    expect(JSON.stringify(sent)).not.toContain("Children's Moment");
    const opening = within(card("Opening Prayer")).getByRole("list", { name: "Notes on Opening Prayer" });
    expect(within(opening).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      `Rules${STOCK}`,
      "Read aloudThe second clause is hard to say aloud.",
    ]);
    expect(within(card("Benediction")).getByText("Looks good.")).toBeInTheDocument();
    expect(within(card("Offertory Prayer")).queryByText("Looks good.")).toBeNull(); // empty: not reviewed
    const box = screen.getByRole("region", { name: "Across the service" });
    expect(within(box).getByText('Several prayers open with "Gracious God".')).toBeInTheDocument();
    expect(within(box).getByText("Repetition")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Benediction" })).toHaveAccessibleDescription(
      "Your church's default benediction. Admins can change it in Settings. Looks good.",
    );
    expect(screen.queryByText(QUICK)).toBeNull();
    expect(reviewButton()).toHaveFocus(); // focus stays on the one button
  });

  it("dismisses one note at a time, moving focus to the next, then to the card; the box goes with its last note", async () => {
    const { user } = renderStep();
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: `Dismiss note: ${STOCK}` }));
    expect(within(opening).queryByText(STOCK)).toBeNull();
    expect(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." })).toHaveFocus();
    await user.click(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." }));
    expect(within(opening).queryByRole("list", { name: "Notes on Opening Prayer" })).toBeNull();
    expect(within(opening).queryByText("Looks good.")).toBeNull(); // dismissed, not "good"
    expect(within(opening).getByRole("heading", { name: "Opening Prayer" })).toHaveFocus();
    const box = screen.getByRole("region", { name: "Across the service" });
    await user.click(within(box).getByRole("button", { name: /^Dismiss note: Several prayers/ }));
    expect(screen.queryByRole("region", { name: "Across the service" })).toBeNull();
    expect(reviewButton()).toHaveFocus();
    expect(within(card("Call to Worship")).getByText(STOCK)).toBeInTheDocument(); // the others stay
  });

  it("clears a card's notes when it is typed in, regenerated, cleared or set to the church default", async () => {
    const draft = withCard(seeded(), "benediction", "Go in peace.", "typed");
    const { user } = renderStep(draft, {
      "POST /liturgy/review": reviewRoute((body) =>
        reviewResult({ cards: body.cards.map((c) => ({ section: c.section, notes: [reviewNote("theology", `About ${c.section}.`)] })) }),
      ),
      "POST /liturgy/generate": generateRoute(),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await screen.findByText("Review finished. 5 notes.");
    // Typing.
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), "!");
    expect(within(card("Call to Worship")).queryByText("About call_to_worship.")).toBeNull();
    // Regenerate on an AI card (no confirm), once its new draft lands.
    await user.click(within(card("Assurance of Pardon")).getByRole("button", { name: "Regenerate" }));
    await within(card("Assurance of Pardon")).findByText("Replaced with a new AI draft.");
    expect(within(card("Assurance of Pardon")).queryByText("About assurance.")).toBeNull();
    // Clear text.
    await user.click(within(card("Prayer of Confession")).getByRole("button", { name: "More actions for Prayer of Confession" }));
    await user.click(await screen.findByRole("menuitem", { name: "Clear text" }));
    expect(within(card("Prayer of Confession")).queryByText("About prayer_of_confession.")).toBeNull();
    // Use church default.
    await user.click(within(card("Benediction")).getByRole("button", { name: "More actions for Benediction" }));
    await user.click(await screen.findByRole("menuitem", { name: "Use church default" }));
    expect(within(card("Benediction")).queryByText("About benediction.")).toBeNull();
    expect(within(card("Opening Prayer")).getByText("About opening_prayer.")).toBeInTheDocument(); // untouched
  });

  it("drops the notes of a card edited while the review ran, and of every card after New service", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/review": reviewRoute(async () => {
        await gate;
        return ANSWER;
      }),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    await waitFor(() => expect(api.requests.some((r) => r.path === "/liturgy/review")).toBe(true));
    await user.type(screen.getByRole("textbox", { name: "Call to Worship" }), " Now.");
    release();
    expect(await screen.findByText("Review finished. 5 notes.")).toBeInTheDocument();
    expect(within(card("Call to Worship")).queryByText(STOCK)).toBeNull();
    expect(within(card("Opening Prayer")).getByText(STOCK)).toBeInTheDocument();
    // New service: no notes are left.
    vi.setSystemTime(new Date(DRAFT_NOW.getTime() + 60_000));
    await user.click(screen.getByRole("button", { name: "More actions" }));
    await user.click(await screen.findByRole("menuitem", { name: "New service" }));
    await user.click(await screen.findByRole("button", { name: "Start new service" }));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Across the service" })).toBeNull());
    expect(screen.queryByText("Looks good.")).toBeNull();
  });

  it("shows the quick checks with a quiet line when the AI part is missing, and a failed review's message", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/review": reviewRoute(() =>
        reviewResult({
          cards: [{ section: "opening_prayer", notes: [reviewNote("rules", STOCK, "code")] }],
          service_notes: [],
          ai_status: "not_configured",
        }),
      ),
    });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    expect(await screen.findByText(QUICK)).toBeInTheDocument();
    expect(within(card("Opening Prayer")).getByText(STOCK)).toBeInTheDocument();
    const reviews = () => api.requests.filter((r) => r.path === "/liturgy/review").length;
    for (const status of ["busy", "timeout", "rate_limited", "error"] as const) {
      api.set("POST /liturgy/review", reviewRoute(() => reviewResult({ ai_status: status })));
      const before = reviews();
      await user.click(reviewButton());
      await waitFor(() => expect(reviews()).toBe(before + 1));
      expect(await screen.findByText("Review finished. No notes.")).toBeInTheDocument();
      expect(screen.getByText(QUICK)).toBeInTheDocument();
    }
    api.set("POST /liturgy/review", reviewRoute(() => ANSWER));
    await review(user);
    expect(screen.queryByText(QUICK)).toBeNull();
    api.set("POST /liturgy/review", fakeError(500, "internal_error", "Something went wrong."));
    await user.click(reviewButton());
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong. (Ref: 4f9a2c1e)");
    expect(within(card("Opening Prayer")).getByText(STOCK)).toBeInTheDocument(); // the last notes stay
  });

  it("says Still working after 8 s, and Cancel stops the wait and keeps focus on the button", async () => {
    vi.useRealTimers(); // a second useFakeTimers call would keep beforeEach's Date-only fake
    vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"], shouldAdvanceTime: true });
    vi.setSystemTime(DRAFT_NOW);
    const { user, api } = renderStep(seeded(), { "POST /liturgy/review": () => new Promise<never>(() => {}) });
    await user.click(await screen.findByRole("button", { name: "Review service" }));
    const cancel = await screen.findByRole("button", { name: "Cancel review" });
    expect(cancel).toHaveTextContent("Cancel");
    expect(cancel).toHaveFocus();
    expect(screen.getByText("Reviewing…")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(8_000);
    });
    expect(screen.getByText(`Reviewing… ${STILL_WORKING}`)).toBeInTheDocument();
    await user.click(cancel);
    expect(reviewButton()).toHaveFocus();
    expect(screen.queryByText(/Reviewing…/)).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(1);
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "^ +(✓|×)|Tests ")
```

**Expected:** @@RED9@@

- [ ] **Step 3 (agent): The button, the status, the notes**

**Create `frontend/src/components/builder/liturgy/review-bar.tsx`:**

````tsx
"use client";

import { CircleAlertIcon, Loader2Icon } from "lucide-react";

import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import { QUICK_CHECKS_ONLY } from "@/lib/liturgy/notes";
import { reviewTargets } from "@/lib/liturgy/request";
import { useLiturgyReview } from "@/lib/liturgy/review";

import { STILL_WORKING, useStillWorking } from "./use-still-working";

/** The button's id: focus comes back here when the "Across the service" box loses its last note. */
export const REVIEW_BUTTON_ID = "review-service";

/**
 * "Review service" in the step's header (R "Review service"): on when at
 * least one switched-on card has text; while the review runs it reads
 * "Cancel" (named "Cancel review"). One button, `aria-disabled` rather than
 * `disabled` when there is nothing to review, so focus stays on it when a
 * review starts or ends.
 */
export function ReviewButton() {
  const { draft } = useDraft();
  const review = useLiturgyReview();
  const ready = reviewTargets(draft).length > 0;
  return (
    <Button
      id={REVIEW_BUTTON_ID}
      variant="outline"
      size="touch"
      focusableWhenDisabled
      disabled={!review.running && !ready}
      aria-label={review.running ? "Cancel review" : undefined}
      className="data-disabled:pointer-events-none data-disabled:opacity-50"
      onClick={() => (review.running ? review.cancel() : review.start())}
    >
      {review.running ? "Cancel" : "Review service"}
    </Button>
  );
}

/**
 * Under the header: while a review runs, a spinner with "Reviewing…" and,
 * after 8 s, "Still working — this can take up to a minute."; a review that
 * failed, its message; a review whose AI part is missing, the quiet "Only
 * quick checks ran…" line; and, read out politely, how many notes it left.
 */
export function ReviewStatus() {
  const review = useLiturgyReview();
  const still = useStillWorking(review.running);
  const quickOnly = !review.running && review.review !== null && review.review.aiStatus !== "ok";
  return (
    <>
      <p className="sr-only" aria-live="polite">
        {review.announcement}
      </p>
      {review.running ? (
        <p className="flex flex-wrap items-center gap-x-2 text-sm" aria-live="polite">
          <Loader2Icon className="size-4 animate-spin" aria-hidden="true" />
          Reviewing…{still ? ` ${STILL_WORKING}` : null}
        </p>
      ) : null}
      {!review.running && review.error ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{review.error}</AlertTitle>
        </Alert>
      ) : null}
      {quickOnly ? <p className="text-sm text-muted-foreground">{QUICK_CHECKS_ONLY}</p> : null}
    </>
  );
}
````

**Create `frontend/src/components/builder/liturgy/card-notes.tsx`:**

````tsx
"use client";

import { CheckIcon, XIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SectionKey } from "@/lib/draft/schema";
import { LOOKS_GOOD, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";

import { REVIEW_BUTTON_ID } from "./review-bar";

/** The id of a card's notes, which describe its textarea. */
export function notesId(key: SectionKey): string {
  return `card-${key}-notes`;
}

/**
 * Remembers where focus goes after a note is dismissed: the next note's ×,
 * else the previous one's, else `fallback` (the card's heading, or the
 * Review button when the "Across the service" box goes). The owner stays
 * mounted when its last note goes, so the move still happens.
 */
function useDismissFocus(fallback: () => HTMLElement | null) {
  const target = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    const id = target.current;
    if (id === undefined) return;
    target.current = undefined;
    const element = id === null ? null : document.getElementById(id);
    (element ?? fallback())?.focus();
  });
  return (notes: Note[], id: string) => {
    const at = notes.findIndex((n) => n.id === id);
    const next = notes[at + 1] ?? notes[at - 1];
    target.current = next ? `note-${next.id}-dismiss` : null;
  };
}

/** One list of notes: a tag chip, the sentence and a dismiss ×, wrapping at 375 px. */
export function NoteList({ notes, label, onDismiss }: { notes: Note[]; label: string; onDismiss: (id: string) => void }) {
  return (
    <ul aria-label={label} className="grid gap-2">
      {notes.map((note) => (
        <li key={note.id} className="flex min-w-0 items-start gap-2">
          <Badge variant="outline" className="mt-0.5 shrink-0">
            {TAG_LABELS[note.tag]}
          </Badge>
          <p className="min-w-0 flex-1 text-sm wrap-anywhere">{note.text}</p>
          <Button
            id={`note-${note.id}-dismiss`}
            variant="ghost"
            size="icon-lg"
            className="-my-2 size-11 shrink-0 md:my-0 md:size-8"
            aria-label={`Dismiss note: ${note.text}`}
            onClick={() => onDismiss(note.id)}
          >
            <XIcon aria-hidden="true" />
          </Button>
        </li>
      ))}
    </ul>
  );
}

/**
 * A card's notes under its text (R "Notes"): at most 3, most important
 * first; "Looks good." when the card was reviewed and came back with none;
 * nothing when it was not reviewed, its notes were all dismissed, or its text
 * changed since.
 */
export function CardNotes({ sectionKey, label, headingId }: { sectionKey: SectionKey; label: string; headingId: string }) {
  const review = useLiturgyReview();
  const notes = review.review?.cards[sectionKey];
  const remember = useDismissFocus(() => document.getElementById(headingId));
  if (notes === undefined) return null;
  if (notes.notes.length === 0) {
    return notes.found === 0 ? (
      <p id={notesId(sectionKey)} className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <CheckIcon className="size-4" aria-hidden="true" />
        {LOOKS_GOOD}
      </p>
    ) : null;
  }
  return (
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
      <NoteList
        notes={notes.notes}
        label={`Notes on ${label}`}
        onDismiss={(id) => {
          remember(notes.notes, id);
          review.dismiss(sectionKey, id);
        }}
      />
    </div>
  );
}

/** The "Across the service" box at the top of the step (R "Notes"): notes about more than one prayer, at most 3. */
export function ServiceNotes() {
  const review = useLiturgyReview();
  const notes = review.review?.service ?? [];
  const remember = useDismissFocus(() => document.getElementById(REVIEW_BUTTON_ID));
  if (notes.length === 0) return null;
  return (
    <section aria-labelledby="across-the-service" className="grid gap-2 rounded-lg border p-4">
      <h3 id="across-the-service" className="text-base font-medium">
        Across the service
      </h3>
      <NoteList
        notes={notes}
        label="Notes across the service"
        onDismiss={(id) => {
          remember(notes, id);
          review.dismiss("service", id);
        }}
      />
    </section>
  );
}
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
````

**with:**

````tsx
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useLiturgyReview } from "@/lib/liturgy/review";
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx

import { STILL_WORKING, useStillWorking } from "./use-still-working";
````

**with:**

````tsx

import { CardNotes, notesId } from "./card-notes";
import { STILL_WORKING, useStillWorking } from "./use-still-working";
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
 * card's Generate (or its heading), not the page.
````

**with:**

````tsx
 * card's Generate (or its heading), not the page.
 *
 * The service reviewer's notes show under the text (`CardNotes`), and
 * describe the textarea while they show.
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
  const generation = useLiturgyGeneration();
````

**with:**

````tsx
  const generation = useLiturgyGeneration();
  const reviewed = useLiturgyReview().review?.cards[spec.key];
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
  const showCounter = card.text.length > COUNTER_FROM;
````

**with:**

````tsx
  const showCounter = card.text.length > COUNTER_FROM;
  const notesShown = reviewed !== undefined && (reviewed.notes.length > 0 || reviewed.found === 0);
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
      showCounter ? `card-${key}-count` : null,
````

**with:**

````tsx
      showCounter ? `card-${key}-count` : null,
      notesShown ? notesId(key) : null,
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
          ) : null}
          {/* Always there, so the line is announced when it appears (a region inserted with its text often is not). */}
````

**with:**

````tsx
          ) : null}
          <CardNotes sectionKey={key} label={spec.label} headingId={headingId} />
          {/* Always there, so the line is announced when it appears (a region inserted with its text often is not). */}
````

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

````tsx
import { OutlineLandmark } from "./outline-landmark";
````

**with:**

````tsx
import { ServiceNotes } from "./card-notes";
import { OutlineLandmark } from "./outline-landmark";
import { ReviewButton, ReviewStatus } from "./review-bar";
````

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

````tsx
 * address names (`#card-…`, `#custom-…`).
````

**with:**

````tsx
 * address names (`#card-…`, `#custom-…`).
 *
 * The header holds the service reviewer's "Review service" button; its
 * progress, failure and "Only quick checks ran…" line follow, then the
 * "Across the service" box. Custom elements are never reviewed.
````

**In `frontend/src/components/builder/liturgy/liturgy-step.tsx`, replace:**

````tsx
      <h2 id="liturgy-step-title" className="text-lg font-semibold">
        Liturgy
      </h2>
````

**with:**

````tsx
      <div className="grid gap-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="liturgy-step-title" className="text-lg font-semibold">
            Liturgy
          </h2>
          <ReviewButton />
        </div>
        <ReviewStatus />
        <ServiceNotes />
      </div>
````

- [ ] **Step 4 (agent): Run the file three times, 4b's step tests, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/liturgy/review-step.test.tsx 2>&1 | grep -E "Tests "); done
(cd frontend && npx vitest run src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  6 passed (6)` three times; `      Tests  44 passed (44)` (4b's step, unchanged); ` Test Files  78 passed (78)`, `      Tests  557 passed (557)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/review-bar.tsx frontend/src/components/builder/liturgy/card-notes.tsx frontend/src/components/builder/liturgy/review-step.test.tsx frontend/src/components/builder/liturgy/liturgy-step.tsx frontend/src/components/builder/liturgy/section-card.tsx
git commit -q -m "Reviewer: Review service on the Liturgy step (R User experience; S4 reviewer amendment UI hooks)" -m "The header's Review service button (Cancel while it runs), the spinner
and Still working line, a failed review's message, the quick-checks-only
line, the Across the service box, and each card's notes (tag, sentence,
dismiss) or Looks good. Focus stays on the button and moves to the next
note, the card or the button after a dismiss." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 9: backend **1213 passed, 11 skipped**; frontend **557 in 78**.

### Task 10: Revise with these notes on the card, with Undo (R "Revise with these notes", Testing "Revise with Undo", "Revise hidden on typed, archive and default cards"; S4 reviewer amendment "UI hooks"; clarifications 23-25, 27)

On an AI card with a note left (and not while the AI is writing it), the notes end with **Revise with these notes**. While it runs the button reads "Revising…" beside a Cancel × (named "Cancel revising {Label}"), which takes focus; the card is read-only and its Regenerate and ⋯ menu are off. When the revised text lands the notes go with the old text, "Revised with these notes. Undo" shows and its Undo takes focus; Undo brings back the draft and origin. A failure shows its message under the notes and leaves Revise to try again (focus goes to it). Revise's AI failures arrive as HTTP statuses, so `cardErrorFrom` shows the server's sentence for `ai_busy`, `ai_timeout` and `ai_upstream_error` (as it already did for `ai_not_configured` and `prompt_invalid`), never "Something went wrong.".

**Files:**
- Modify: `frontend/src/components/builder/liturgy/card-notes.tsx`, `frontend/src/components/builder/liturgy/section-card.tsx`, `frontend/src/lib/liturgy/errors.ts`; tests `frontend/src/components/builder/liturgy/review-step.test.tsx`, `frontend/src/lib/liturgy/errors.test.ts`

**Interfaces:**
- Consumes: T7 (`canRevise`), T8 (`revise`, `cancelRevise`, `revising`, `reviseErrors`), T9 (`CardNotes`); 4b's `PendingButton`, the card's `undoRef` and `headingRef`.
- Produces: `CardNotes`'s `busy` prop, `reviseId(key)`; `cardErrorFrom` maps an `ApiError` with `ai_busy`, `ai_timeout` or `ai_upstream_error` to the server's message, with Try again.

- [ ] **Step 1 (agent): Write the failing tests**

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
import type { ReviewBody } from "@/lib/api/types";
````

**with:**

````tsx
import type { ReviewBody, ReviseBody } from "@/lib/api/types";
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
  reviewRoute,
````

**with:**

````tsx
  reviewRoute,
  reviseRoute,
````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
  service_notes: [reviewNote("repetition", 'Several prayers open with "Gracious God".', "code")],
});

````

**with:**

````tsx
  service_notes: [reviewNote("repetition", 'Several prayers open with "Gracious God".', "code")],
});

function stored(): DraftV1 {
  return JSON.parse(window.localStorage.getItem(KEY) ?? "null") as DraftV1;
}

````

**In `frontend/src/components/builder/liturgy/review-step.test.tsx`, replace:**

````tsx
    expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(1);
  });
});
````

**with:**

````tsx
    expect(api.requests.filter((r) => r.path === "/liturgy/review")).toHaveLength(1);
  });
});

describe("Revise with these notes (R Revise)", () => {
  it("is offered only on AI cards with a note left; typed, archived and default cards get notes but no Revise", async () => {
    const { user } = renderStep();
    await review(user);
    expect(within(card("Opening Prayer")).getByRole("button", { name: "Revise with these notes" })).toBeInTheDocument();
    expect(within(card("Assurance of Pardon")).getByRole("button", { name: "Revise with these notes" })).toBeInTheDocument();
    expect(within(card("Call to Worship")).getByText(STOCK)).toBeInTheDocument();
    expect(within(card("Call to Worship")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
    expect(within(card("Prayer of Confession")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
    expect(within(card("Benediction")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
    // Its last note dismissed, an AI card has nothing to revise with.
    await user.click(within(card("Assurance of Pardon")).getByRole("button", { name: /^Dismiss note:/ }));
    expect(within(card("Assurance of Pardon")).queryByRole("button", { name: "Revise with these notes" })).toBeNull();
  });

  it("sends the card's text and remaining notes, replaces it as an AI draft with Undo, and Undo brings the draft back", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": reviseRoute(() => ({ text: "Gracious God, hear us now." })),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Dismiss note: The second clause is hard to say aloud." }));
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, hear us now.");
    expect(within(opening).getByText("AI draft")).toBeInTheDocument();
    expect(within(opening).queryByRole("list", { name: "Notes on Opening Prayer" })).toBeNull(); // the notes went with the text
    expect(within(opening).getByRole("button", { name: "Undo" })).toHaveFocus();
    const sent = api.requests.find((r) => r.path === "/liturgy/revise")?.body as ReviseBody;
    expect(sent).toMatchObject({ section: "opening_prayer", text: "Gracious God, as we journey, hear us.", notes: [STOCK] });
    await waitFor(() => expect(stored().liturgy.cards.opening_prayer).toEqual({ enabled: true, text: "Gracious God, hear us now.", origin: "ai" }));
    await user.click(within(opening).getByRole("button", { name: "Undo" }));
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    expect(within(opening).queryByText("Revised with these notes.")).toBeNull();
    expect(within(card("Call to Worship")).getByText(STOCK)).toBeInTheDocument(); // other cards keep theirs
  });

  it("keeps the card read-only while it revises; Cancel keeps the text and notes and returns focus to Revise", async () => {
    const { user } = renderStep(seeded(), { "POST /liturgy/revise": () => new Promise<never>(() => {}) });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    const cancel = within(opening).getByRole("button", { name: "Cancel revising Opening Prayer" });
    expect(cancel).toHaveFocus();
    expect(within(opening).getByRole("button", { name: "Revising…" })).toBeDisabled();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveAttribute("readonly");
    expect(within(opening).getByRole("button", { name: "Regenerate" })).toBeDisabled();
    expect(within(opening).getByRole("button", { name: "More actions for Opening Prayer" })).toBeDisabled();
    await user.click(cancel);
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toHaveFocus();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).not.toHaveAttribute("readonly");
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    expect(within(opening).getByText(STOCK)).toBeInTheDocument();
  });

  it("shows why a revision failed under the notes, keeps the text, and Revise tries again", async () => {
    const { user, api } = renderStep(seeded(), {
      "POST /liturgy/revise": fakeError(422, "prompt_invalid", "This prayer is too long to revise."),
    });
    await review(user);
    const opening = card("Opening Prayer");
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByRole("alert")).toHaveTextContent("This prayer is too long to revise.");
    expect(within(opening).getByRole("button", { name: "Revise with these notes" })).toHaveFocus();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Gracious God, as we journey, hear us.");
    api.set("POST /liturgy/revise", fakeError(503, "ai_busy", "The AI service is busy. Try again in a minute."));
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByText("The AI service is busy. Try again in a minute.")).toBeInTheDocument();
    api.set("POST /liturgy/revise", reviseRoute());
    await user.click(within(opening).getByRole("button", { name: "Revise with these notes" }));
    expect(await within(opening).findByText("Revised with these notes.")).toBeInTheDocument();
    expect(within(opening).queryByRole("alert")).toBeNull();
    expect(screen.getByRole("textbox", { name: "Opening Prayer" })).toHaveValue("Opening Prayer revised with the notes.");
  });
});
````

**In `frontend/src/lib/liturgy/errors.test.ts`, replace:**

````ts
    ).toEqual({ code: "auth_unavailable", message: "Sign-in is temporarily unavailable. Try again shortly.", retryable: true });
  });
});
````

**with:**

````ts
    ).toEqual({ code: "auth_unavailable", message: "Sign-in is temporarily unavailable. Try again shortly.", retryable: true });
  });

  it("shows the server's sentence for the AI codes Revise gets as HTTP statuses (the service reviewer)", () => {
    const cases: [number, string, string, boolean][] = [
      [503, "ai_not_configured", "AI isn't set up on this app yet.", false],
      [503, "ai_busy", "The AI service is busy. Try again in a minute.", true],
      [504, "ai_timeout", "The AI took too long to answer. Try again.", true],
      [502, "ai_upstream_error", "The AI service had a problem. Try again.", true],
      [422, "prompt_invalid", "This prayer is too long to revise.", false],
    ];
    for (const [status, code, message, retryable] of cases) {
      expect(cardErrorFrom(new ApiError(status, code as never, message)), code).toEqual({ code, message, retryable });
    }
  });
});
````

- [ ] **Step 2 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/components/builder/liturgy/review-step.test.tsx src/lib/liturgy/errors.test.ts 2>&1 | grep -E "^ +(✓|×)|Tests ")
```

**Expected:** @@RED10@@

- [ ] **Step 3 (agent): Revise on the card**

**In `frontend/src/lib/liturgy/errors.ts`, replace:**

````ts
 * acts on (sign-out, another church).
````

**with:**

````ts
 * acts on (sign-out, another church).
 *
 * The service reviewer's Revise gets the AI codes as HTTP statuses (503, 504,
 * 502, as /hymns/suggestions): they show the server's own sentence, as they
 * do inside generation's 200.
````

**In `frontend/src/lib/liturgy/errors.ts`, replace:**

````ts
      return { code: e.code, message: e.message, retryable: true };
````

**with:**

````ts
      return { code: e.code, message: e.message, retryable: true };
    case "ai_busy":
    case "ai_timeout":
    case "ai_upstream_error":
      // Revise (the service reviewer): the server's sentence, as inside generation's 200.
      return { code: e.code, message: e.message, retryable: true };
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
import { CheckIcon, XIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SectionKey } from "@/lib/draft/schema";
import { LOOKS_GOOD, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
````

**with:**

````tsx
import { CheckIcon, CircleAlertIcon, XIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { canRevise, LOOKS_GOOD, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
}

/**
 * A card's notes under its text (R "Notes"): at most 3, most important
````

**with:**

````tsx
}

/** The id of a card's "Revise with these notes" button. */
export function reviseId(key: SectionKey): string {
  return `card-${key}-revise`;
}

/**
 * A card's notes under its text (R "Notes"): at most 3, most important
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
 */
export function CardNotes({ sectionKey, label, headingId }: { sectionKey: SectionKey; label: string; headingId: string }) {
  const review = useLiturgyReview();
  const notes = review.review?.cards[sectionKey];
  const remember = useDismissFocus(() => document.getElementById(headingId));
````

**with:**

````tsx
 *
 * "Revise with these notes" (R "Revise") shows only on an AI card with a note
 * left, and not while the card is being written. While it runs the button
 * reads "Revising…" beside a Cancel ×, which takes focus; a failure shows its
 * message here and leaves the button to try again. The card itself moves
 * focus when the revision ends (`SectionCard`).
 */
export function CardNotes({
  sectionKey,
  label,
  headingId,
  busy = false,
}: {
  sectionKey: SectionKey;
  label: string;
  headingId: string;
  /** The card is being written by the AI: no Revise. */
  busy?: boolean;
}) {
  const review = useLiturgyReview();
  const { draft } = useDraft();
  const notes = review.review?.cards[sectionKey];
  const remember = useDismissFocus(() => document.getElementById(headingId));
  const cancelRef = useRef<HTMLButtonElement>(null);
  const focusCancel = useRef(false);
  const revising = review.revising[sectionKey] === true;
  const failure = review.reviseErrors[sectionKey];
  useEffect(() => {
    if (!focusCancel.current) return;
    focusCancel.current = false;
    cancelRef.current?.focus();
  });
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
  }
  return (
````

**with:**

````tsx
  }
  const offered = canRevise(draft.liturgy.cards[sectionKey], notes) && !busy;
  return (
````

**In `frontend/src/components/builder/liturgy/card-notes.tsx`, replace:**

````tsx
      />
    </div>
````

**with:**

````tsx
      />
      {offered || revising ? (
        <div className="flex flex-wrap items-center justify-end gap-2">
          {revising ? (
            <>
              <PendingButton pending pendingLabel="Revising…" size="touch">
                Revising…
              </PendingButton>
              <Button
                ref={cancelRef}
                variant="ghost"
                size="icon-lg"
                className="size-11 md:size-8"
                aria-label={`Cancel revising ${label}`}
                onClick={() => review.cancelRevise(sectionKey)}
              >
                <XIcon aria-hidden="true" />
              </Button>
            </>
          ) : (
            <Button
              id={reviseId(sectionKey)}
              variant="outline"
              size="touch"
              onClick={() => {
                focusCancel.current = true;
                review.revise(sectionKey);
              }}
            >
              Revise with these notes
            </Button>
          )}
        </div>
      ) : null}
      {failure && !revising ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{failure.message}</AlertTitle>
        </Alert>
      ) : null}
    </div>
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
import { CardNotes, notesId } from "./card-notes";
````

**with:**

````tsx
import { CardNotes, notesId, reviseId } from "./card-notes";
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
 * describe the textarea while they show.
````

**with:**

````tsx
 * describe the textarea while they show. While "Revise with these notes"
 * runs, the card is read-only and its Regenerate and ⋯ menu are off; when it
 * ends, focus goes to the Undo line's button (the text was revised), the
 * Revise button (it failed or was cancelled) or the heading.
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
  const reviewed = useLiturgyReview().review?.cards[spec.key];
````

**with:**

````tsx
  const review = useLiturgyReview();
  const reviewed = review.review?.cards[spec.key];
  const revising = review.revising[spec.key] === true;
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
    (usable ? element : headingRef.current)?.focus();
  });

````

**with:**

````tsx
    (usable ? element : headingRef.current)?.focus();
  });

  // A revision ended: its Cancel went, so the Undo line (revised), the Revise button (failed, cancelled) or the heading.
  const wasRevising = useRef(revising);
  useEffect(() => {
    const before = wasRevising.current;
    wasRevising.current = revising;
    if (!before || revising) return;
    const active = document.activeElement;
    if (active !== null && active !== document.body) return; // focus already went somewhere on purpose
    (undoRef.current ?? document.getElementById(reviseId(key)) ?? headingRef.current)?.focus();
  }, [revising, key]);

````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
            disabled={menuItems.length === 0 || run !== undefined}
````

**with:**

````tsx
            disabled={menuItems.length === 0 || run !== undefined || revising}
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
            readOnly={run?.phase === "writing"}
````

**with:**

````tsx
            readOnly={run?.phase === "writing" || revising}
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
          <CardNotes sectionKey={key} label={spec.label} headingId={headingId} />
````

**with:**

````tsx
          <CardNotes sectionKey={key} label={spec.label} headingId={headingId} busy={run !== undefined} />
````

**In `frontend/src/components/builder/liturgy/section-card.tsx`, replace:**

````tsx
                  <Button ref={actionRef} variant="outline" size="touch" disabled={!aiAvailable} onClick={write}>
````

**with:**

````tsx
                  <Button ref={actionRef} variant="outline" size="touch" disabled={!aiAvailable || revising} onClick={write}>
````

- [ ] **Step 4 (agent): Run the files three times, 4b's step tests, the suite, types and lint**

```bash
for i in 1 2 3; do (cd frontend && npx vitest run src/components/builder/liturgy/review-step.test.tsx src/lib/liturgy/errors.test.ts 2>&1 | grep -E "Tests "); done
(cd frontend && npx vitest run src/components/builder/liturgy/liturgy-step.test.tsx 2>&1 | grep -E "Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
```

**Expected:** `      Tests  14 passed (14)` three times; `      Tests  44 passed (44)`; ` Test Files  78 passed (78)`, `      Tests  562 passed (562)`; `typecheck 0`, `lint 0`.

- [ ] **Step 5 (agent): Commit**

```bash
git add frontend/src/components/builder/liturgy/card-notes.tsx frontend/src/components/builder/liturgy/section-card.tsx frontend/src/lib/liturgy/errors.ts frontend/src/components/builder/liturgy/review-step.test.tsx frontend/src/lib/liturgy/errors.test.ts
git commit -q -m "Reviewer: Revise with these notes, with Undo (R Revise; S4 reviewer amendment)" -m "Only on AI cards with a note left. While it runs the card is read-only,
with Revising and a Cancel that takes focus; the revised text replaces the
card with Revised with these notes and Undo, which takes focus. A failure
shows the server's sentence under the notes and Revise stays." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

Counts after Task 10: backend **1213 passed, 11 skipped**; frontend **562 in 78**.

### Task 11: Docs: F's §1.8 row, the plan notes in S4 and R, the manual check and its heading pin (owner answers 1-4; R Testing "Append a manual check at 375 px"; clarifications 1-31)

**Files:**
- Modify: `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`, `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`, `docs/manual-verification.md`, `backend/tests/test_slice1_docs.py`

- [ ] **Step 1 (agent): Pin the new checklist heading (the failing test)**

**In `backend/tests/test_slice1_docs.py`, replace:**

````python
    # Slices 2c, 3b and 4b append "## Slice 2", "## Slice 3" and "## Slice 4" after this section (their specs, Manual checks).
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-5:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4"]
````

**with:**

````python
    # Slices 2c, 3b and 4b append "## Slice 2", "## Slice 3" and "## Slice 4" after this section (their specs, Manual
    # checks), and the service reviewer "## Service reviewer".
    headings = re.findall(r"^## .+$", text, re.MULTILINE)[-6:]
    assert headings == ["## Ops slice", "## Slice 1", "## Slice 2", "## Slice 3", "## Slice 4", "## Service reviewer"]
````

```bash
.venv/bin/python -m pytest -q backend/tests/test_slice1_docs.py 2>&1 | tail -2
```

**Expected:** `FAILED backend/tests/test_slice1_docs.py::test_manual_verification_has_the_slice_1_section - AssertionError: assert ['## Slice 0 ...`, then `1 failed, <n> passed in <t>s`.

- [ ] **Step 2 (agent): Write the docs**

**In `docs/superpowers/specs/2026-09-25-migration-foundations-design.md`, replace:**

````markdown
| §4.6, §4.7 | *(2026-09-30, slice 4b plan, owner answer 1)* On the Liturgy step `isPristine` counts everything that ends up in the service: card text, a card switched away from its default, communion set by the user, the sermon title and custom elements; text or a title blank after trimming counts as nothing, and a Benediction following the church default never counts. A fresh draft's Benediction holds the church's `default_benediction`, and the draft store keeps untouched cards on the defaults (automatic changes, never outranking another tab's edit). Liturgy ships (`SHIPPED_STEPS` holds "readings", "hymns" and "liturgy"): the step bar counts it, Review lists each empty switched-on card and a missing sermon title, and the summary shows the liturgy counts. The kit gains `dialog`. | 4b |
````

**with:**

````markdown
| §4.6, §4.7 | *(2026-09-30, slice 4b plan, owner answer 1)* On the Liturgy step `isPristine` counts everything that ends up in the service: card text, a card switched away from its default, communion set by the user, the sermon title and custom elements; text or a title blank after trimming counts as nothing, and a Benediction following the church default never counts. A fresh draft's Benediction holds the church's `default_benediction`, and the draft store keeps untouched cards on the defaults (automatic changes, never outranking another tab's edit). Liturgy ships (`SHIPPED_STEPS` holds "readings", "hymns" and "liturgy"): the step bar counts it, Review lists each empty switched-on card and a missing sermon title, and the summary shows the liturgy counts. The kit gains `dialog`. | 4b |
| §1.8, §2.8 | *(2026-10-01, service reviewer plan, owner answer 3)* The client timeouts for `POST /liturgy/review` and `POST /liturgy/revise` are 100 000 ms (`ENDPOINT_TIMEOUTS`), as the 4b row said. Review passes a 75 s deadline from the start of its usecase to its one `complete()` call, so it answers within about 80 s; revise reuses generation's 80 s deadline and the section's attempt timeout (60 s for Prayers of the People), so it answers within 85 s. Revise's prompt-size 422 has no `fields`; a review whose church text is too long even with every card cut to 200 characters skips the AI and answers `ai_status: "error"`, never `prompt_invalid`. | reviewer |
````

**Append to `docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md`:**

````markdown

## Notes from the service reviewer plan (2026-10-01)

`docs/superpowers/plans/2026-10-01-service-reviewer.md` builds the reviewer add-on (amendment 2026-09-26, PR #8) as one PR, backend first (owner answer 1 of 2026-10-01). Where it reads the reviewer spec or this amendment more precisely, or the code and F win, it says so here (its numbered clarifications give the reasons); the owner's answers of 2026-10-01 ("all recommended") are its owner answers 1-4.

- **Season guidance** (owner answer 2): `liturgy_prompts.DEFAULT_SYSTEM_PROMPT` carries the reviewer spec's new sentence verbatim, kept in `SEASON_GUIDANCE`, which the review prompt quotes. The freeze contingency is off (F §6.1, amendment of 2026-09-28), so there is no `LEGACY_SYSTEM_PROMPT`, no `legacy_default_prompts()` and no wrapper; `streamlit-frozen` keeps the old wording.
- **Code checks**: "on this … Sunday" is "on this" plus one to four words plus "Sunday"; "in this ordinary time" gives the stock-phrase note only; a reference's book word starts with a capital letter, its name or alias comes from `scripture_refs.BOOKS` only (not `PARSE_ALIASES`), and an abbreviation may end with a period.
- **AI review**: the settings are read only when the AI is configured; a church whose own text is too long even with every card cut to 200 characters gets the code notes and `ai_status: "error"`; Voice notes are dropped when there is no profile; tags are read loosely ("Read aloud" is `read_aloud`).
- **Timeouts** (owner answer 3; F §1.8 row of 2026-10-01): both routes 100 000 ms on the client; review 75 s on the server; revise generation's 80 s deadline and the section's attempt timeout.
- **Revise**: AI failures carry the OpenAI client's sentences ("AI isn't set up on this app yet." and the busy, timeout and problem sentences), which the card shows.
- **Screen**: notes live in `LiturgyReviewProvider` (`lib/liturgy/review.tsx`), beside the generation provider; the sermon loader moved to `lib/liturgy/sermon.ts`, shared by both. A card's notes go when its text or origin changes in any way (and do not come back on Undo); "Across the service" stays until the next review or New service; Cancel and a failed review keep the notes shown. "Looks good." is only for a card that came back with no notes. The new strings (owner-visible) are listed in the plan's clarifications.
- **Tests**: the screen's cases are in `components/builder/liturgy/review-step.test.tsx`, the provider's in `lib/liturgy/review.test.tsx`, the pure rules in `lib/liturgy/notes.test.ts`; the manual checks are "## Service reviewer" in `docs/manual-verification.md`.
````

**Append to `docs/superpowers/specs/2026-09-26-service-reviewer-design.md`:**

````markdown

## Notes from the implementation plan (2026-10-01)

`docs/superpowers/plans/2026-10-01-service-reviewer.md` builds this add-on as one PR. The owner's answers of 2026-10-01 set the client timeout for both routes to 100 000 ms (not 90 000; F §1.8) and confirm the writer's new season guidance ships with it. The slice 4 spec's "Notes from the service reviewer plan" lists where the plan reads this spec more precisely.
````

**Append to `docs/manual-verification.md`:**

````markdown

## Service reviewer

Run on the production URL https://worship-service-builder.vercel.app, at 375 px
(Chrome device mode, iPhone SE) and on desktop. These are the reviewer spec's
manual check (Testing) and the owner's guided check (owner answer 4,
2026-10-01): after the merge the owner runs the items marked "(owner, after
the reviewer)" on a phone, one step at a time, and takes a quick look on a
computer; the result goes into `docs/ops-runbook.md` → "Service reviewer
record". The AI's words differ every time, so record what the page shows,
never an email address or a church id.

- [ ] (owner, after the reviewer) **1.** On a liturgy with a typed Call to Worship and a few AI sections, tap **Review service**: a spinner and "Reviewing…", then notes under the cards (a tag such as "Rules" or "Read aloud", one sentence, an ×), "Looks good." on a card with none, and, when prayers repeat each other, an "Across the service" box at the top.
- [ ] (owner, after the reviewer) **2.** Dismiss one note with its ×: only that note goes.
- [ ] (owner, after the reviewer) **3.** On an AI card with a note, tap **Revise with these notes**: the text is replaced, "Revised with these notes. Undo" shows, and **Undo** brings the draft back.
- [ ] (owner, after the reviewer) **4.** The typed card has notes but no **Revise with these notes** button.
- [ ] (owner, after the reviewer) **5.** Type in a card that has notes: its notes go at once; the other cards keep theirs.
- [ ] **6.** With the AI unavailable (or after a review that says so), the quick checks still show with "Only quick checks ran. The full review isn't available right now."
- [ ] (owner, after the reviewer) **7.** At 375 px: no sideways scroll; the Review service button sits beside or under "Liturgy"; note chips and sentences wrap; every × and button is at least 44 px.
- [ ] **8.** Start a review and tap **Cancel**: the spinner goes and nothing changes. Start one and choose **New service**: no notes remain.
````

- [ ] **Step 3 (agent): Check the docs tests and the suite**

```bash
.venv/bin/python -m pytest -q backend/tests/test_docs.py backend/tests/test_slice1_docs.py backend/tests/test_ops_workflows.py 2>&1 | tail -1
grep -n '\[owner' docs/ops-runbook.md | grep -v 'An entry marked' | wc -l
.venv/bin/python -m pytest -q | tail -1
git diff --stat
```

**Expected:** `89 passed in <t>s`; `4`; `1213 passed, 11 skipped in <t>s`; five files changed, about 41 insertions and 3 deletions.

- [ ] **Step 4 (agent): Commit**

```bash
git add docs/superpowers/specs/2026-09-25-migration-foundations-design.md docs/superpowers/specs/2026-09-25-slice-4-liturgy-design.md docs/superpowers/specs/2026-09-26-service-reviewer-design.md docs/manual-verification.md backend/tests/test_slice1_docs.py
git commit -q -m "Docs: the reviewer's F row, plan notes in S4 and R, the manual check (owner answers 2026-10-01)" -m "F records the reviewer's timeouts and server deadlines. The slice 4 spec
and the reviewer spec gain the plan's notes where it reads them more
precisely. docs/manual-verification.md gains Service reviewer, with the
owner's guided phone check marked, and its heading pin follows." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
git log --oneline -1
```

- [ ] **Step 5 (controller): Review checkpoint (end of batch C) and backup push**

Review T9-T11 together: R's strings verbatim ("Looks good.", "Only quick checks ran. The full review isn't available right now.", the six tags, "Across the service", "Revise with these notes"); the new strings exactly as clarification 22 lists them; 44 px targets and wrapping at 375 px (classes: `size-11` below `md`, `flex-wrap`, `min-w-0`, `wrap-anywhere`); focus never drops to the page; the docs match the clarifications. Then the backup push.

Counts after Task 11: backend **1213 passed, 11 skipped**; frontend **562 in 78**.

