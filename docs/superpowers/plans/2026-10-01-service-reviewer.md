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

