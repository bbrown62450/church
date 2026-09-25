# Service Rubric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each church an editable rubric (a checklist for each hymn slot and each prayer, plus "prefer older" and "prefer familiar" settings) and make hymn suggestions and liturgy writing follow it.

**Architecture:** A pure module, `backend/service_rubric.py`, holds the defaults and the merge/validate logic. Each church stores sparse overrides in `churches.settings["rubric"]`, read and written through `repos/churches.py` and exposed by `GET`/`PATCH /rubric` in the FastAPI app. Two new hymn columns (`text_year`, `hymnal_count`) are filled from Hymnary.org's public API by a one-off backfill. A small `hymn_ranking.py` orders candidates by them. `worship_service.py` passes the checklists, preferences and sermon text to the AI, and the Streamlit app passes each church's rubric through without any new screens.

**Tech Stack:** Python 3.11, SQLAlchemy 2.x (SQLite in tests, Supabase Postgres in production), FastAPI + Pydantic v2, httpx, the OpenAI SDK (faked in tests), pytest.

**Spec:** `docs/superpowers/specs/2026-09-25-service-rubric-design.md`

## Global Constraints

- Run everything from the worktree root. The venv lives there: create it once with `/Users/beaubrown/.local/bin/python3.11 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`. Run tests with `.venv/bin/python -m pytest -q`. The baseline is 206 passed.
- `pytest.ini` puts both `.` and `backend` on `sys.path`, so backend modules import by bare name (`import service_rubric`, `from repos.churches import …`).
- Tests make no network calls and no real AI calls. Fake `worship_service.OpenAI` and the Hymnary fetch function.
- Every church-scoped API route depends on `require_church`. Routes that change data depend on `require_admin`.
- Checklist limits: at most **12** points, each a non-empty string of at most **300** characters after trimming. `prefer_before_year` is an int from **1500** to the current year (not a bool). `prefer_familiar` is a bool. An empty list is invalid; `null`/`None` means reset to default.
- Defaults: `prefer_before_year = 1970`, `prefer_familiar = True`. Checklist wording is copied verbatim from the spec (Task 1 holds the exact text).
- Nothing in `backend/` may import `streamlit`.
- **Deploy order:** `backend/migrate_add_hymn_facts.py` must run against Supabase **before** this branch merges, because both apps select every mapped column.
- End every commit message with a blank line and then `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `backend/service_rubric.py` | create | Default rubric; validate, merge and patch overrides; checklist formatting |
| `backend/repos/churches.py` | modify | Read and update a church's rubric overrides in `settings["rubric"]` |
| `backend/api/routes/rubric.py` | create | `GET /rubric`, `PATCH /rubric` |
| `backend/api/schemas.py` | modify | `RubricModel`, `RubricOut` |
| `backend/api/main.py` | modify | Register the rubric router |
| `backend/db/models.py` | modify | `text_year`, `hymnal_count` on `HymnCatalog` and `Hymn` |
| `backend/repos/hymns.py` | modify | Expose the new columns; copy them when seeding |
| `backend/migrate_add_hymn_facts.py` | create | Idempotent ALTER for existing databases |
| `backend/hymnary_facts.py` | create | Parse Hymnary API records; match hymns; backfill blanks |
| `backend/backfill_hymn_facts.py` | create | CLI: real HTTP fetch, throttling, `--dry-run` |
| `backend/hymn_ranking.py` | create | Order candidates older-then-familiar; the facts note |
| `backend/worship_service.py` | modify | Hymn picker and liturgy writer use the rubric and sermon text |
| `backend/liturgy_prompts.py` | modify | Two default prompts become "no more than 3 sentences" |
| `ui_helpers.py` | modify | `sermon_text_for()` for the Streamlit call site |
| `app.py` | modify | Pass the rubric and sermon text at the two call sites |
| `README.md` | modify | Deploy steps: migrate, then backfill |

Tests: `backend/tests/test_service_rubric.py`, `test_church_settings.py`, `test_api_rubric.py`, `test_hymns_repo.py`, `test_migrate_hymn_facts.py`, `test_hymnary_facts.py`, `test_hymn_ranking.py`, `test_suggest_hymns.py`, `test_generate_liturgy.py`, `test_liturgy_prompts.py`, and `streamlit_tests/test_app_helpers.py`.

---

### Task 1: Rubric module (defaults, validation, merge)

**Files:**
- Create: `backend/service_rubric.py`
- Test: `backend/tests/test_service_rubric.py`

**Interfaces:**
- Consumes: `liturgy_prompts.SECTION_ORDER` (the 8 section keys).
- Produces:
  - `HYMN_SLOTS: list[str]` = `["opening", "response", "closing"]`
  - `HYMN_SLOT_LABELS: dict[str, str]`
  - `DEFAULT_RUBRIC: dict`
  - `default_rubric() -> dict`: a deep copy
  - `merge_rubric(overrides) -> dict`: tolerant; ignores bad values
  - `validate_patch(patch) -> dict`: strict; raises `ValueError`
  - `apply_patch(overrides, cleaned_patch) -> dict`: new sparse overrides
  - `customized_keys(overrides) -> list[str]`: e.g. `["hymns.closing", "prefer_before_year"]`
  - `format_checklist(heading: str, items: list[str]) -> str`

  A rubric dict always has exactly these keys: `{"hymns": {slot: [str]}, "prayers": {section: [str]}, "prefer_before_year": int, "prefer_familiar": bool}`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_service_rubric.py`:

```python
import datetime as dt

import pytest

import liturgy_prompts as lp
import service_rubric as sr


def test_default_rubric_covers_every_slot_and_section():
    r = sr.default_rubric()
    assert set(r) == {"hymns", "prayers", "prefer_before_year", "prefer_familiar"}
    assert list(r["hymns"]) == sr.HYMN_SLOTS == ["opening", "response", "closing"]
    assert list(r["prayers"]) == lp.SECTION_ORDER
    assert r["prefer_before_year"] == 1970
    assert r["prefer_familiar"] is True
    for checklist in [*r["hymns"].values(), *r["prayers"].values()]:
        assert checklist and all(isinstance(i, str) and i.strip() for i in checklist)


def test_default_rubric_is_a_copy():
    r = sr.default_rubric()
    r["hymns"]["opening"].append("changed")
    r["prefer_before_year"] = 1800
    assert "changed" not in sr.default_rubric()["hymns"]["opening"]
    assert sr.default_rubric()["prefer_before_year"] == 1970


def test_defaults_carry_the_approved_wording():
    r = sr.default_rubric()
    assert "is joyful and upbeat" in r["hymns"]["closing"]
    assert "sends people out to serve others and share God's love" in r["hymns"]["closing"]
    assert any("common to all people" in i for i in r["prayers"]["prayer_of_confession"])
    assert any("New Testament reading (the sermon text)" in i for i in r["prayers"]["prayer_of_confession"])
    assert any("no more than 3 sentences" in i for i in r["prayers"]["prayer_for_illumination"])
    assert "is no more than 3 sentences" in r["prayers"]["offertory_prayer"]


def test_defaults_pass_their_own_validation():
    d = sr.default_rubric()
    assert sr.validate_patch(d) == d


def test_merge_none_or_junk_is_all_defaults():
    assert sr.merge_rubric(None) == sr.default_rubric()
    assert sr.merge_rubric("junk") == sr.default_rubric()
    assert sr.merge_rubric({}) == sr.default_rubric()


def test_merge_replaces_only_the_overridden_items():
    merged = sr.merge_rubric({"hymns": {"closing": ["Joyful."]}, "prefer_before_year": 1900})
    assert merged["hymns"]["closing"] == ["Joyful."]
    assert merged["hymns"]["opening"] == sr.default_rubric()["hymns"]["opening"]
    assert merged["prayers"] == sr.default_rubric()["prayers"]
    assert merged["prefer_before_year"] == 1900
    assert merged["prefer_familiar"] is True


def test_merge_ignores_unknown_keys_and_invalid_stored_values():
    merged = sr.merge_rubric({
        "bogus": 1,
        "hymns": {"closing": [], "interlude": ["x"]},
        "prayers": {"benediction": None},
        "prefer_before_year": "1900",
        "prefer_familiar": "yes",
    })
    assert merged == sr.default_rubric()


def test_validate_trims_points_and_passes_none_through():
    cleaned = sr.validate_patch({
        "prayers": {"benediction": ["  Go in peace.  "], "assurance": None},
        "prefer_familiar": None,
    })
    assert cleaned == {
        "prayers": {"benediction": ["Go in peace."], "assurance": None},
        "prefer_familiar": None,
    }


@pytest.mark.parametrize("patch, message", [
    ([], "must be an object"),
    ({"bogus": 1}, "Unknown rubric setting"),
    ({"hymns": ["x"]}, "must be an object of checklists"),
    ({"hymns": {"interlude": ["x"]}}, "Unknown hymns checklist"),
    ({"prayers": {"benediction": []}}, "non-empty list"),
    ({"prayers": {"benediction": "Go."}}, "non-empty list"),
    ({"prayers": {"benediction": ["x"] * 13}}, "at most 12"),
    ({"prayers": {"benediction": ["x" * 301]}}, "at most 300"),
    ({"prayers": {"benediction": ["  "]}}, "non-empty text"),
    ({"prayers": {"benediction": [7]}}, "non-empty text"),
    ({"prefer_before_year": 1499}, "between 1500"),
    ({"prefer_before_year": dt.date.today().year + 1}, "between 1500"),
    ({"prefer_before_year": True}, "between 1500"),
    ({"prefer_before_year": "1970"}, "between 1500"),
    ({"prefer_familiar": "yes"}, "true or false"),
])
def test_validate_rejects_bad_input(patch, message):
    with pytest.raises(ValueError, match=message):
        sr.validate_patch(patch)


def test_apply_patch_sets_resets_and_drops_empty_groups():
    overrides = {"hymns": {"closing": ["A."]}, "prefer_before_year": 1900}
    out = sr.apply_patch(overrides, {"hymns": {"opening": ["B."]}, "prefer_familiar": False})
    assert out == {"hymns": {"closing": ["A."], "opening": ["B."]},
                   "prefer_before_year": 1900, "prefer_familiar": False}
    out = sr.apply_patch(out, {"hymns": {"closing": None, "opening": None}, "prefer_before_year": None})
    assert out == {"prefer_familiar": False}
    assert overrides == {"hymns": {"closing": ["A."]}, "prefer_before_year": 1900}  # not mutated


def test_apply_patch_replaces_a_junk_stored_group():
    out = sr.apply_patch({"hymns": ["junk"]}, {"hymns": {"closing": ["A."]}})
    assert out == {"hymns": {"closing": ["A."]}}


def test_customized_keys_lists_only_applied_overrides_in_rubric_order():
    overrides = {
        "prefer_before_year": 1900,
        "prayers": {"benediction": ["Go."], "assurance": []},   # empty list is not applied
        "hymns": {"closing": ["Joy."]},
    }
    assert sr.customized_keys(overrides) == ["hymns.closing", "prayers.benediction", "prefer_before_year"]
    assert sr.customized_keys(None) == []


def test_format_checklist():
    assert sr.format_checklist("Benediction", ["one", "two"]) == "A good Benediction:\n- one\n- two"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_service_rubric.py -q`
Expected: collection error `ModuleNotFoundError: No module named 'service_rubric'`.

- [ ] **Step 3: Write the module**

Create `backend/service_rubric.py`:

```python
#!/usr/bin/env python3
"""The service rubric: what a good service looks like.

A checklist for each hymn slot and each liturgy section, plus two hymn
preferences. The defaults live here. Each church stores only its overrides in
churches.settings["rubric"], in the same shape but sparse, so a church that
never edits anything picks up improved defaults automatically.

Checklists describe quality. The per-section prompts in liturgy_prompts.py keep
describing format (Leader/People lines, length, "End with Amen"). They stay
separate so a future reviewer can grade a draft item by item.
"""
import copy
import datetime as _dt
from typing import Any, Callable, Dict, List

from liturgy_prompts import SECTION_ORDER

HYMN_SLOTS: List[str] = ["opening", "response", "closing"]

HYMN_SLOT_LABELS: Dict[str, str] = {
    "opening": "Opening (Gathering) Hymn",
    "response": "Response Hymn (after the sermon)",
    "closing": "Closing (Sending) Hymn",
}

MAX_ITEMS = 12
MAX_ITEM_CHARS = 300
MIN_YEAR = 1500

DEFAULT_RUBRIC: Dict[str, Any] = {
    "hymns": {
        "opening": [
            "gathers and welcomes people into worship",
            "turns attention toward God in praise, not toward the sermon topic",
            "is strong and confident, not quiet or reflective",
            "fits the season when possible (for example, an Advent hymn in Advent)",
        ],
        "response": [
            "reinforces the central message of the sermon, which is usually the New Testament reading",
            "gives the congregation a way to respond, such as commitment, trust or prayer",
            "may be more reflective than the opening or closing hymn",
            "connects to the reading's main theme, not just a single word that appears in it",
        ],
        "closing": [
            "is joyful and upbeat",
            "sends people out to serve others and share God's love",
            "looks outward to the world, not inward",
            "ends the service on a note of hope",
        ],
    },
    "prayers": {
        "call_to_worship": [
            "calls the people together to worship God",
            "keeps the People's lines short and easy to say together",
            "builds toward praise, ending with a strong People response",
            "hints at the day's themes without citing scripture",
        ],
        "opening_prayer": [
            "follows the classic collect shape",
            "addresses God",
            'names something God has done or is ("who…")',
            "asks for one thing that fits the day",
            'says why ("so that…")',
            'closes through Christ, then "Amen"',
        ],
        "prayer_of_confession": [
            'names real, specific failings that are common to all people, not vague "we have fallen short"',
            "connects to the themes of the New Testament reading (the sermon text), without citing it",
            "includes sins of omission (what we failed to do) as well as commission",
            'stays in "we," as one congregation confessing together',
            "is honest without piling on shame",
            "turns toward God's mercy at the end",
        ],
        "assurance": [
            'declares forgiveness as a sure fact ("In Jesus Christ, we are forgiven"), not a wish ("may God forgive us")',
            "is grounded in God's grace in Christ",
            "answers the confession by echoing its theme",
            "is brief and joyful",
        ],
        "prayer_for_illumination": [
            "asks the Holy Spirit to open hearts and minds to the Word",
            "asks that we both hear and respond, not just understand",
            "makes room for the preacher's words to be God's word for today",
            "is no more than 3 sentences, and quiets the room before the reading",
        ],
        "prayers_of_the_people": [
            "moves outward to inward: world, church, community, then ourselves",
            'names concrete needs (refugees, the grieving, people without work), not just "all who suffer"',
            "makes room for the congregation's joys and concerns, and a time of silence",
            "is unhurried but not wordy, with each petition saying one thing",
            "leads naturally into the Lord's Prayer",
        ],
        "offertory_prayer": [
            "thanks God as the giver of everything we have",
            "dedicates both our gifts and ourselves to God's work",
            "names, even briefly, what the gifts will do in the world",
            "is no more than 3 sentences",
        ],
        "benediction": [
            'speaks a blessing to the people ("May God go with you…"), rather than praying to God',
            "sends them out to serve and share God's love",
            "may name the Trinity",
            "is 1 to 3 sentences, confident and easy to remember",
        ],
    },
    "prefer_before_year": 1970,
    "prefer_familiar": True,
}

# Each checklist group and the keys it may hold.
_GROUP_KEYS: Dict[str, List[str]] = {"hymns": HYMN_SLOTS, "prayers": SECTION_ORDER}


def default_rubric() -> Dict[str, Any]:
    """The full default rubric (a deep copy; safe to mutate)."""
    return copy.deepcopy(DEFAULT_RUBRIC)


def _clean_checklist(value: Any) -> List[str]:
    if not isinstance(value, list) or not value:
        raise ValueError("A checklist must be a non-empty list of points.")
    if len(value) > MAX_ITEMS:
        raise ValueError(f"A checklist can have at most {MAX_ITEMS} points.")
    items = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("Each checklist point must be non-empty text.")
        item = item.strip()
        if len(item) > MAX_ITEM_CHARS:
            raise ValueError(f"Each checklist point must be at most {MAX_ITEM_CHARS} characters.")
        items.append(item)
    return items


def _clean_year(value: Any) -> int:
    this_year = _dt.date.today().year
    if isinstance(value, bool) or not isinstance(value, int) or not MIN_YEAR <= value <= this_year:
        raise ValueError(f"The preferred year must be between {MIN_YEAR} and {this_year}.")
    return value


def _clean_flag(value: Any) -> bool:
    if not isinstance(value, bool):
        raise ValueError("prefer_familiar must be true or false.")
    return value


_SETTING_CLEANERS: Dict[str, Callable[[Any], Any]] = {
    "prefer_before_year": _clean_year,
    "prefer_familiar": _clean_flag,
}


def _is_valid(clean: Callable[[Any], Any], value: Any) -> bool:
    try:
        clean(value)
    except ValueError:
        return False
    return True


def validate_patch(patch: Any) -> Dict[str, Any]:
    """Check a sparse rubric patch and return it cleaned (points trimmed).

    None for a checklist or setting means "reset to default" and passes
    through. Raises ValueError with a readable message on an unknown key or a
    bad value.
    """
    if not isinstance(patch, dict):
        raise ValueError("The rubric update must be an object.")
    cleaned: Dict[str, Any] = {}
    for key, value in patch.items():
        if key in _GROUP_KEYS:
            if not isinstance(value, dict):
                raise ValueError(f"'{key}' must be an object of checklists.")
            group = {}
            for sub, checklist in value.items():
                if sub not in _GROUP_KEYS[key]:
                    raise ValueError(f"Unknown {key} checklist: '{sub}'.")
                group[sub] = None if checklist is None else _clean_checklist(checklist)
            cleaned[key] = group
        elif key in _SETTING_CLEANERS:
            cleaned[key] = None if value is None else _SETTING_CLEANERS[key](value)
        else:
            raise ValueError(f"Unknown rubric setting: '{key}'.")
    return cleaned


def merge_rubric(overrides: Any) -> Dict[str, Any]:
    """The defaults with each valid override applied.

    Unknown keys and invalid stored values are ignored, so a bad stored value
    never breaks hymn suggestions or liturgy generation.
    """
    rubric = default_rubric()
    if not isinstance(overrides, dict):
        return rubric
    for group, subs in _GROUP_KEYS.items():
        stored = overrides.get(group)
        if not isinstance(stored, dict):
            continue
        for sub in subs:
            if sub in stored and _is_valid(_clean_checklist, stored[sub]):
                rubric[group][sub] = _clean_checklist(stored[sub])
    for key, clean in _SETTING_CLEANERS.items():
        if key in overrides and _is_valid(clean, overrides[key]):
            rubric[key] = clean(overrides[key])
    return rubric


def apply_patch(overrides: Any, patch: Dict[str, Any]) -> Dict[str, Any]:
    """New sparse overrides: `overrides` with a validated `patch` applied.

    None removes an override (back to the default). A group left empty is
    dropped. Neither argument is mutated.
    """
    result = copy.deepcopy(overrides) if isinstance(overrides, dict) else {}
    for key, value in patch.items():
        if key in _GROUP_KEYS:
            stored = result.get(key)
            group = dict(stored) if isinstance(stored, dict) else {}
            for sub, checklist in value.items():
                if checklist is None:
                    group.pop(sub, None)
                else:
                    group[sub] = list(checklist)
            if group:
                result[key] = group
            else:
                result.pop(key, None)
        elif value is None:
            result.pop(key, None)
        else:
            result[key] = value
    return result


def customized_keys(overrides: Any) -> List[str]:
    """Dotted names of the overrides merge_rubric would apply, in rubric order,
    e.g. ["hymns.closing", "prefer_before_year"]."""
    if not isinstance(overrides, dict):
        return []
    keys = []
    for group, subs in _GROUP_KEYS.items():
        stored = overrides.get(group)
        if isinstance(stored, dict):
            keys += [f"{group}.{sub}" for sub in subs
                     if sub in stored and _is_valid(_clean_checklist, stored[sub])]
    keys += [key for key, clean in _SETTING_CLEANERS.items()
             if key in overrides and _is_valid(clean, overrides[key])]
    return keys


def format_checklist(heading: str, items: List[str]) -> str:
    """'A good {heading}:' followed by one '- point' line per item."""
    return "\n".join([f"A good {heading}:"] + [f"- {item}" for item in items])
```

Note: the spec phrases the opening prayer as "A good opening prayer follows the classic collect shape:" followed by five points. Here "follows the classic collect shape" is the first point, so the checklist reads correctly under the generic "A good Opening Prayer:" heading.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_service_rubric.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/service_rubric.py backend/tests/test_service_rubric.py
git commit -m "Add the service rubric: default checklists, validation, merge

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Store each church's rubric

**Files:**
- Modify: `backend/repos/churches.py`: add three functions after `set_church_prompts`, plus an import
- Test: `backend/tests/test_church_settings.py`: append tests

**Interfaces:**
- Consumes: `service_rubric.validate_patch`, `apply_patch`, `merge_rubric`, `default_rubric` (Task 1).
- Produces:
  - `get_church_rubric_overrides(church_id) -> dict`: `{}` when there are none or the church is missing/deleted
  - `get_church_rubric(church_id) -> dict`: the merged, full rubric
  - `update_church_rubric(church_id, patch: dict) -> dict`: validates, stores and returns the merged rubric; raises `ValueError` on bad input and stores nothing

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_church_settings.py`:

```python
import pytest

from repos.churches import (
    get_church_rubric, get_church_rubric_overrides, update_church_rubric,
)
from service_rubric import default_rubric


def test_rubric_defaults_until_edited(tmp_db, make_user):
    cid = create_church(name="R", timezone="UTC", owner_user_id=make_user(email="r@x.org"))
    assert get_church_rubric_overrides(cid) == {}
    assert get_church_rubric(cid) == default_rubric()


def test_rubric_update_stores_only_overrides_and_resets(tmp_db, make_user):
    cid = create_church(name="R2", timezone="UTC", owner_user_id=make_user(email="r2@x.org"))
    merged = update_church_rubric(cid, {"hymns": {"closing": [" Joyful. "]}, "prefer_before_year": 1900})
    assert merged["hymns"]["closing"] == ["Joyful."]
    assert merged["prefer_before_year"] == 1900
    assert get_church_rubric_overrides(cid) == {"hymns": {"closing": ["Joyful."]}, "prefer_before_year": 1900}

    update_church_rubric(cid, {"hymns": {"closing": None}})
    assert get_church_rubric_overrides(cid) == {"prefer_before_year": 1900}
    assert get_church_rubric(cid)["hymns"]["closing"] == default_rubric()["hymns"]["closing"]


def test_rubric_invalid_update_raises_and_stores_nothing(tmp_db, make_user):
    cid = create_church(name="R3", timezone="UTC", owner_user_id=make_user(email="r3@x.org"))
    with pytest.raises(ValueError):
        update_church_rubric(cid, {"prefer_before_year": 1400})
    assert get_church_rubric_overrides(cid) == {}


def test_rubric_does_not_clobber_other_settings(tmp_db, make_user):
    cid = create_church(name="R4", timezone="UTC", owner_user_id=make_user(email="r4@x.org"))
    set_church_translation(cid, "nrsvue")
    set_church_prompts(cid, {"benediction": "Go in peace."})
    update_church_rubric(cid, {"prefer_familiar": False})
    assert get_church_translation(cid) == "nrsvue"
    assert get_church_prompts(cid) == {"benediction": "Go in peace."}
    assert get_church_rubric(cid)["prefer_familiar"] is False


def test_rubric_edits_stay_in_their_church(tmp_db, make_user):
    a = create_church(name="A", timezone="UTC", owner_user_id=make_user(email="a@x.org"))
    b = create_church(name="B", timezone="UTC", owner_user_id=make_user(email="b@x.org"))
    update_church_rubric(a, {"prayers": {"benediction": ["Only in A."]}})
    assert get_church_rubric(b) == default_rubric()
    assert get_church_rubric_overrides(b) == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_church_settings.py -q`
Expected: `ImportError: cannot import name 'get_church_rubric'`.

- [ ] **Step 3: Implement**

In `backend/repos/churches.py`, add this import below `from db.models import Church, Membership, Invite`:

```python
from service_rubric import apply_patch, merge_rubric, validate_patch
```

Then add these functions right after `set_church_prompts`:

```python
def get_church_rubric_overrides(church_id) -> dict:
    """The church's stored rubric overrides ({} when it uses all defaults)."""
    church = get_church(church_id)
    if not church:
        return {}
    stored = (church.get("settings") or {}).get("rubric")
    return dict(stored) if isinstance(stored, dict) else {}


def get_church_rubric(church_id) -> dict:
    """The church's full rubric: the defaults with its valid overrides applied."""
    return merge_rubric(get_church_rubric_overrides(church_id))


def update_church_rubric(church_id, patch: dict) -> dict:
    """Validate and apply a sparse rubric patch (None resets that checklist or
    setting to its default). Raises ValueError, storing nothing, on invalid
    input. Returns the merged rubric."""
    cleaned = validate_patch(patch)
    overrides = apply_patch(get_church_rubric_overrides(church_id), cleaned)
    _merge_settings(church_id, {"rubric": overrides})
    return merge_rubric(overrides)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_church_settings.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/repos/churches.py backend/tests/test_church_settings.py
git commit -m "Store each church's rubric overrides in its settings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `GET` and `PATCH /rubric`

**Files:**
- Create: `backend/api/routes/rubric.py`
- Modify: `backend/api/schemas.py` (append models), `backend/api/main.py` (register the router)
- Test: `backend/tests/test_api_rubric.py`

**Interfaces:**
- Consumes: `get_church_rubric_overrides`, `update_church_rubric` (Task 2); `merge_rubric`, `customized_keys` (Task 1); `require_church`, `require_admin` from `api.deps`; `ApiError` from `api.errors`.
- Produces:
  - `GET /rubric` → `200 {"rubric": {...}, "customized": [...]}`
  - `PATCH /rubric` (admin) → the same shape. Bad values return `422 {"error": {"code": "invalid_rubric", "message": ...}}`. A body that isn't a JSON object returns `422` with code `invalid_request`. A member gets `403 forbidden`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_api_rubric.py`:

```python
import pytest
from fastapi.testclient import TestClient

from api.deps import get_verifier
from api.main import create_app
from api.security import TokenVerifier
from repos.memberships import add_membership
from service_rubric import default_rubric
from tests.jwt_helpers import ISSUER, SIGNING_KEY, make_token


@pytest.fixture
def client(tmp_db):
    app = create_app()
    app.dependency_overrides[get_verifier] = lambda: TokenVerifier(
        lambda _token: SIGNING_KEY.public_key(), issuer=ISSUER
    )
    return TestClient(app)


def _headers(email, church_id):
    return {"Authorization": f"Bearer {make_token(email=email)}", "X-Church-Id": str(church_id)}


@pytest.fixture
def church(make_user, make_church):
    """A church owned by owner@x.org with member@x.org as a plain member."""
    owner = make_user(email="owner@x.org")
    cid = make_church(name="Grace", owner_user_id=owner)
    add_membership(make_user(email="member@x.org"), cid, "member")
    return cid


def test_member_reads_the_default_rubric(client, church):
    r = client.get("/rubric", headers=_headers("member@x.org", church))
    assert r.status_code == 200
    assert r.json() == {"rubric": default_rubric(), "customized": []}


def test_reading_requires_membership(client, church, make_user):
    make_user(email="stranger@x.org")
    r = client.get("/rubric", headers=_headers("stranger@x.org", church))
    assert r.status_code == 403


def test_member_cannot_change_the_rubric(client, church):
    r = client.patch("/rubric", json={"prefer_familiar": False}, headers=_headers("member@x.org", church))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_owner_changes_then_resets_an_item(client, church):
    h = _headers("owner@x.org", church)
    r = client.patch("/rubric", json={"hymns": {"closing": ["Joyful and sending."]}}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["rubric"]["hymns"]["closing"] == ["Joyful and sending."]
    assert body["customized"] == ["hymns.closing"]
    assert client.get("/rubric", headers=h).json() == body

    r = client.patch("/rubric", json={"hymns": {"closing": None}}, headers=h)
    assert r.json() == {"rubric": default_rubric(), "customized": []}


def test_invalid_values_return_a_readable_422(client, church):
    r = client.patch("/rubric", json={"prefer_before_year": 1400}, headers=_headers("owner@x.org", church))
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "invalid_rubric"
    assert "between 1500" in r.json()["error"]["message"]


def test_non_object_body_is_rejected(client, church):
    r = client.patch("/rubric", json=["x"], headers=_headers("owner@x.org", church))
    assert r.status_code == 422


def test_edits_stay_in_their_church(client, church, make_church, make_user):
    other = make_church(name="Other", owner_user_id=make_user(email="other@x.org"))
    client.patch("/rubric", json={"prefer_familiar": False}, headers=_headers("owner@x.org", church))
    r = client.get("/rubric", headers=_headers("other@x.org", other))
    assert r.json() == {"rubric": default_rubric(), "customized": []}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_api_rubric.py -q`
Expected: failures with `404` on `/rubric`.

- [ ] **Step 3: Implement**

Append to `backend/api/schemas.py`:

```python
class RubricModel(BaseModel):
    hymns: dict[str, list[str]]
    prayers: dict[str, list[str]]
    prefer_before_year: int
    prefer_familiar: bool


class RubricOut(BaseModel):
    rubric: RubricModel
    customized: list[str]
```

Create `backend/api/routes/rubric.py`:

```python
"""The church's service rubric: any member reads it; admins change it."""
from typing import Any, Dict

from fastapi import APIRouter, Body, Depends

from api.deps import ActiveChurch, require_admin, require_church
from api.errors import ApiError
from api.schemas import RubricOut
from repos.churches import get_church_rubric_overrides, update_church_rubric
from service_rubric import customized_keys, merge_rubric

router = APIRouter()


def _rubric_out(church_id) -> RubricOut:
    overrides = get_church_rubric_overrides(church_id)
    return RubricOut(rubric=merge_rubric(overrides), customized=customized_keys(overrides))


@router.get("/rubric", response_model=RubricOut)
def read_rubric(church: ActiveChurch = Depends(require_church)) -> RubricOut:
    return _rubric_out(church.id)


@router.patch("/rubric", response_model=RubricOut)
def change_rubric(
    patch: Dict[str, Any] = Body(...),
    church: ActiveChurch = Depends(require_admin),
) -> RubricOut:
    """Sparse update: send only what changes; null resets an item to its default."""
    try:
        update_church_rubric(church.id, patch)
    except ValueError as exc:
        raise ApiError(422, "invalid_rubric", str(exc)) from None
    return _rubric_out(church.id)
```

In `backend/api/main.py`, change `from api.routes import health, me` to `from api.routes import health, me, rubric`, and add `app.include_router(rubric.router)` after `app.include_router(me.router)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_api_rubric.py backend/tests/test_api_app.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/api/routes/rubric.py backend/api/schemas.py backend/api/main.py backend/tests/test_api_rubric.py
git commit -m "Add GET and PATCH /rubric: members read, admins change

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Hymn year and familiarity columns

**Files:**
- Modify: `backend/db/models.py`: add two columns to `HymnCatalog` and `Hymn`
- Modify: `backend/repos/hymns.py`: `_hymn_to_dict` and `seed_church_from_catalog`
- Create: `backend/migrate_add_hymn_facts.py`
- Test: `backend/tests/test_migrate_hymn_facts.py` (create); `backend/tests/test_hymns_repo.py` (append)

**Interfaces:**
- Produces:
  - `HymnCatalog.text_year`, `HymnCatalog.hymnal_count`, `Hymn.text_year`, `Hymn.hymnal_count`: nullable `Integer`
  - flat hymn dicts gain the keys `"Text Year"` and `"Hymnal Count"` (values may be `None`)
  - `migrate_add_hymn_facts.run(engine=None) -> list[str]`: the `"table.column"` names it added

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_migrate_hymn_facts.py`:

```python
from sqlalchemy import create_engine, inspect, text

import migrate_add_hymn_facts


def _columns(engine, table):
    return {c["name"] for c in inspect(engine).get_columns(table)}


def test_adds_missing_columns_once(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with engine.begin() as conn:  # the pre-feature schema, trimmed to what matters
        conn.execute(text("CREATE TABLE hymns (id VARCHAR PRIMARY KEY, title VARCHAR)"))
        conn.execute(text("CREATE TABLE hymn_catalog (id VARCHAR PRIMARY KEY, title VARCHAR)"))

    added = migrate_add_hymn_facts.run(engine)
    assert sorted(added) == [
        "hymn_catalog.hymnal_count", "hymn_catalog.text_year",
        "hymns.hymnal_count", "hymns.text_year",
    ]
    for table in ("hymns", "hymn_catalog"):
        assert {"text_year", "hymnal_count"} <= _columns(engine, table)

    assert migrate_add_hymn_facts.run(engine) == []   # idempotent


def test_noop_on_a_current_database(tmp_db):
    assert migrate_add_hymn_facts.run(tmp_db) == []
```

Append to `backend/tests/test_hymns_repo.py`:

```python
def test_hymn_dicts_expose_year_and_familiarity(tmp_db, make_user, make_church):
    cid = make_church(owner_user_id=make_user(email="facts@grace.org"))
    created = add_hymn(cid, title="Holy, Holy, Holy", number=138)
    assert created["Text Year"] is None
    assert created["Hymnal Count"] is None


def test_seed_copies_year_and_familiarity(tmp_db, make_user, make_church):
    from db.models import HymnCatalog

    cid = make_church(owner_user_id=make_user(email="seedfacts@grace.org"))
    with session_scope() as session:
        session.add(HymnCatalog(title="Holy, Holy, Holy", number=138, text_year=1826, hymnal_count=1322))
    with session_scope() as session:
        seed_church_from_catalog(cid, session)
    [hymn] = list_hymns(cid)
    assert hymn["Text Year"] == 1826
    assert hymn["Hymnal Count"] == 1322
```

(`test_hymns_repo.py` already imports `session_scope`, `add_hymn`, `list_hymns` and `seed_church_from_catalog` at the top, so no import changes are needed.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_migrate_hymn_facts.py backend/tests/test_hymns_repo.py -q`
Expected: `ModuleNotFoundError: No module named 'migrate_add_hymn_facts'`, and `KeyError: 'Text Year'` / `TypeError: 'text_year' is an invalid keyword argument`.

- [ ] **Step 3: Implement**

In `backend/db/models.py`, add these two lines after `audio_url = Column(Text)` in **both** `HymnCatalog` and `Hymn`:

```python
    text_year = Column(Integer)      # year the words were written (Hymnary.org); None = unknown
    hymnal_count = Column(Integer)   # hymnals that include the text: familiarity; None = unknown
```

In `backend/repos/hymns.py`, add to the dict returned by `_hymn_to_dict`, after `"Audio": h.audio_url,`:

```python
        "Text Year": h.text_year,
        "Hymnal Count": h.hymnal_count,
```

In `seed_church_from_catalog`, add to the `Hymn(...)` constructor, after `audio_url=c.audio_url,`:

```python
                text_year=c.text_year,
                hymnal_count=c.hymnal_count,
```

Create `backend/migrate_add_hymn_facts.py`:

```python
#!/usr/bin/env python3
"""One-off migration: add `text_year` and `hymnal_count` to hymns and
hymn_catalog on an existing database.

Fresh databases get the columns from Base.metadata.create_all. Run this against
the deployed Postgres BEFORE merging code that maps these columns: the
Streamlit app and the API both select every mapped column and would fail
without them. Idempotent: it adds only the missing columns, so it is safe to
re-run and also works on SQLite (which lacks ADD COLUMN IF NOT EXISTS).

    python migrate_add_hymn_facts.py
"""
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import inspect, text  # noqa: E402

from db import get_engine  # noqa: E402

TABLES = ("hymns", "hymn_catalog")
COLUMNS = {"text_year": "INTEGER", "hymnal_count": "INTEGER"}


def run(engine=None) -> list:
    """Add any missing columns. Returns the "table.column" names added."""
    engine = engine or get_engine()
    added = []
    with engine.begin() as conn:
        inspector = inspect(conn)
        for table in TABLES:
            existing = {c["name"] for c in inspector.get_columns(table)}
            for column, sql_type in COLUMNS.items():
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
                    added.append(f"{table}.{column}")
    return added


if __name__ == "__main__":
    added = run()
    print("Added: " + ", ".join(added) if added else "OK — columns already present.")
```

- [ ] **Step 4: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: everything passes. Other tests build their tables with `create_all`, so they get the new columns automatically.

- [ ] **Step 5: Commit**

```bash
git add backend/db/models.py backend/repos/hymns.py backend/migrate_add_hymn_facts.py backend/tests/test_migrate_hymn_facts.py backend/tests/test_hymns_repo.py
git commit -m "Add hymn year and familiarity columns with an idempotent migration

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Backfill year and familiarity from Hymnary.org

**Files:**
- Create: `backend/hymnary_facts.py` (pure parsing and matching, plus backfill with an injected fetch)
- Create: `backend/backfill_hymn_facts.py` (the CLI with real HTTP)
- Test: `backend/tests/test_hymnary_facts.py`

**Interfaces:**
- Consumes: the `HymnCatalog`/`Hymn` columns from Task 4; `db.session_scope`.
- Produces (in `hymnary_facts`):
  - `API_URL = "https://hymnary.org/api/scripture"`
  - `text_year(record: dict) -> int | None`
  - `hymnal_count(record: dict) -> int | None`
  - `normalize_title(title: str) -> str`
  - `split_refs(refs: str) -> list[str]`
  - `find_facts(title, refs, fetch, cache) -> dict | None`: returns `{"text_year": ..., "hymnal_count": ...}`
  - `run_backfill(fetch, *, dry_run=False, on_progress=None) -> dict`: returns `{"checked", "matched", "updated", "unknown"}`
  - `fetch` is `Callable[[str], dict | list]`: it takes a scripture reference and returns the API's JSON (a dict keyed by title, or `[]` when there are no results).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_hymnary_facts.py`:

```python
import pytest
from sqlalchemy import select

import hymnary_facts as hf
from db import session_scope
from db.models import Hymn, HymnCatalog


@pytest.mark.parametrize("record, year", [
    ({"date": "1826"}, 1826),
    ({"date": "c. 1200", "author": "Perronet, Edward, 1721-1792"}, 1200),   # date wins
    ({"author": "Perronet, Edward, 1721-1792"}, 1792),
    ({"author": "Heermann, Johann, 1585-1647", "translator": "Bridges, Robert, 1844-1930"}, 1930),
    ({"translator": "Seiss, Joseph A. (Joseph Augustus) 1823-1904"}, 1904),
    ({"author": "Wren, Brian, 1936-"}, 1936 + hf.BIRTH_ONLY_OFFSET),
    ({"author": "Latin hymn, 12th cent."}, None),
    ({}, None),
])
def test_text_year(record, year):
    assert hf.text_year(record) == year


@pytest.mark.parametrize("record, count", [
    ({"number of hymnals": "3918"}, 3918),
    ({"number of hymnals": "1,322"}, 1322),
    ({"number of hymnals": ""}, None),
    ({}, None),
])
def test_hymnal_count(record, count):
    assert hf.hymnal_count(record) == count


def test_normalize_title_ignores_case_punctuation_and_leading_article():
    assert hf.normalize_title("Holy, Holy, Holy! Lord God Almighty") == \
        hf.normalize_title("holy holy holy lord god almighty")
    assert hf.normalize_title("The Church's One Foundation") == hf.normalize_title("Church's One Foundation")
    assert hf.normalize_title("O Come, All Ye Faithful") != hf.normalize_title("Come, All Ye Faithful")
    assert hf.normalize_title("  ") == ""


@pytest.mark.parametrize("refs, expected", [
    ("Isaiah 6:1-8; Revelation 4:8", ["Isaiah 6:1-8", "Revelation 4:8"]),
    ("Isaiah 6:1-8, Revelation 4:8", ["Isaiah 6:1-8", "Revelation 4:8"]),
    ("Romans 4:1-5, 13-17", ["Romans 4:1-5, 13-17"]),
    ("Psalm 23, 1 John 4:7", ["Psalm 23", "1 John 4:7"]),
    ("Psalm 23\nJohn 10:11", ["Psalm 23", "John 10:11"]),
    ("", []),
    (None, []),
])
def test_split_refs(refs, expected):
    assert hf.split_refs(refs) == expected


HOLY = {"title": "Holy, Holy, Holy! Lord God Almighty", "number of hymnals": "1322",
        "author": "Heber, Reginald, 1783-1826"}


class FakeFetch:
    """Stands in for the Hymnary API: {reference: json}. Counts calls per reference."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, ref):
        self.calls.append(ref)
        return self.responses.get(ref, [])


def test_find_facts_matches_by_title_and_caches_each_reference():
    fetch = FakeFetch({"Isaiah 6:3": {"x": {"title": "Other Hymn"}, "Holy": HOLY}})
    cache = {}
    facts = hf.find_facts("Holy, Holy, Holy", "Isaiah 6:3", fetch, cache)
    assert facts is None   # "Holy, Holy, Holy" is not the full Hymnary title
    facts = hf.find_facts("Holy, Holy, Holy! Lord God Almighty", "Isaiah 6:3", fetch, cache)
    assert facts == {"text_year": 1826, "hymnal_count": 1322}
    assert fetch.calls == ["Isaiah 6:3"]   # second lookup served from the cache


def test_find_facts_handles_empty_results_and_missing_refs():
    fetch = FakeFetch({})
    assert hf.find_facts("Anything", "Jude 1:25", fetch, {}) is None   # API returns []
    assert hf.find_facts("Anything", "", fetch, {}) is None
    assert hf.find_facts("", "Jude 1:25", fetch, {}) is None


def test_run_backfill_fills_blanks_without_overwriting(tmp_db, make_church):
    cid = make_church()
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs="Isaiah 6:3"))
        s.add(Hymn(church_id=cid, title=HOLY["title"], scripture_refs="Isaiah 6:3", text_year=1800))
        s.add(Hymn(church_id=cid, title="Unknown Hymn", scripture_refs="Isaiah 6:3"))
        s.add(Hymn(church_id=cid, title="No Refs"))
    fetch = FakeFetch({"Isaiah 6:3": {"Holy": HOLY}})

    stats = hf.run_backfill(fetch)

    assert stats == {"checked": 4, "matched": 2, "updated": 2, "unknown": 2}
    assert fetch.calls == ["Isaiah 6:3"]
    with session_scope() as s:
        cat = s.execute(select(HymnCatalog)).scalar_one()
        assert (cat.text_year, cat.hymnal_count) == (1826, 1322)
        holy = s.execute(select(Hymn).where(Hymn.title == HOLY["title"])).scalar_one()
        assert (holy.text_year, holy.hymnal_count) == (1800, 1322)   # 1800 kept
    assert hf.run_backfill(fetch)["checked"] == 2   # only the two unknowns remain blank


def test_run_backfill_dry_run_writes_nothing(tmp_db):
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs="Isaiah 6:3"))
    stats = hf.run_backfill(FakeFetch({"Isaiah 6:3": {"Holy": HOLY}}), dry_run=True)
    assert stats["updated"] == 1
    with session_scope() as s:
        assert s.execute(select(HymnCatalog)).scalar_one().text_year is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_hymnary_facts.py -q`
Expected: `ModuleNotFoundError: No module named 'hymnary_facts'`.

- [ ] **Step 3: Implement the module**

Create `backend/hymnary_facts.py`:

```python
#!/usr/bin/env python3
"""Hymn year and familiarity from Hymnary.org's public scripture API.

Hymnary.org's website sits behind a bot challenge, so we never scrape it. The
public API (API_URL?reference=...) answers plain requests and returns, for
each text that cites the reference: its title, "number of hymnals" (our
familiarity signal), often "date", and people fields with life dates such as
"Perronet, Edward, 1721-1792".

The fetch function is injected so tests never touch the network; the CLI in
backfill_hymn_facts.py supplies the real, throttled one.
"""
import re
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import or_, select

from db import session_scope
from db.models import Hymn, HymnCatalog

API_URL = "https://hymnary.org/api/scripture"
PEOPLE_FIELDS = ("author", "translator", "paraphraser", "adapter", "alterer")
BIRTH_ONLY_OFFSET = 35   # a living writer born in 1936 counts as writing around 1971
WRITE_BATCH = 50

Fetch = Callable[[str], Any]

_YEAR = re.compile(r"\b(1\d{3}|20\d{2})\b")
_LIFE = re.compile(r"(\d{4})\s*-\s*(\d{4})?")
_REF_BREAK = re.compile(r"\s*(?:;|\n|,(?=\s*[1-3]?\s?[A-Za-z]))\s*")
_ARTICLE = re.compile(r"^(the|a|an) ")


def _person_year(value: str) -> Optional[int]:
    """Latest year a writer could have written: the death year, or the birth
    year + BIRTH_ONLY_OFFSET when only a birth year is known."""
    years = [int(died) if died else int(born) + BIRTH_ONLY_OFFSET
             for born, died in _LIFE.findall(value)]
    return max(years) if years else None


def text_year(record: Dict[str, Any]) -> Optional[int]:
    """The year the words were written: the first 4-digit year in `date`, else
    the latest year implied by the writers' life dates. None when unknown."""
    match = _YEAR.search(str(record.get("date") or ""))
    if match:
        return int(match.group(1))
    years = [y for field in PEOPLE_FIELDS
             if (y := _person_year(str(record.get(field) or ""))) is not None]
    return max(years) if years else None


def hymnal_count(record: Dict[str, Any]) -> Optional[int]:
    digits = re.sub(r"\D", "", str(record.get("number of hymnals") or ""))
    return int(digits) if digits else None


def normalize_title(title: str) -> str:
    """Lowercase, punctuation dropped, a leading "the/a/an" removed."""
    t = re.sub(r"[^\w\s]", " ", (title or "").lower())
    t = re.sub(r"\s+", " ", t).strip()
    return _ARTICLE.sub("", t)


def split_refs(refs: Optional[str]) -> List[str]:
    """Split stored scripture references on ';', newlines, and commas that
    start a new book ("Isaiah 6:1-8, Revelation 4:8"), but not on commas
    inside one reference ("Romans 4:1-5, 13-17")."""
    return [r for r in _REF_BREAK.split((refs or "").strip()) if r]


def find_facts(title: str, refs: Optional[str], fetch: Fetch,
               cache: Dict[str, Any]) -> Optional[Dict[str, Optional[int]]]:
    """Look up one hymn: query each of its references (cached per reference)
    and return the facts from the first record whose title matches, or None."""
    want = normalize_title(title)
    if not want:
        return None
    for ref in split_refs(refs):
        if ref not in cache:
            cache[ref] = fetch(ref)
        results = cache[ref]
        records = results.values() if isinstance(results, dict) else (results or [])
        for record in records:
            if isinstance(record, dict) and normalize_title(record.get("title", "")) == want:
                return {"text_year": text_year(record), "hymnal_count": hymnal_count(record)}
    return None


def _write(updates: List[tuple]) -> None:
    """Fill blanks only: a value set since we read the row is kept."""
    with session_scope() as session:
        for model, row_id, values in updates:
            row = session.get(model, row_id)
            if row is None:
                continue
            for attr, value in values.items():
                if getattr(row, attr) is None:
                    setattr(row, attr, value)


def run_backfill(fetch: Fetch, *, dry_run: bool = False,
                 on_progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, int]:
    """Fill blank text_year / hymnal_count on hymn_catalog and hymns rows.

    Never overwrites a value, so re-runs are safe and manual corrections
    survive. Network calls happen outside any database transaction; writes go
    in batches of WRITE_BATCH.
    """
    targets = []
    with session_scope() as session:
        for model in (HymnCatalog, Hymn):
            rows = session.execute(
                select(model.id, model.title, model.scripture_refs, model.text_year, model.hymnal_count)
                .where(or_(model.text_year.is_(None), model.hymnal_count.is_(None)))
            ).all()
            targets += [(model, *row) for row in rows]

    cache: Dict[str, Any] = {}
    stats = {"checked": 0, "matched": 0, "updated": 0, "unknown": 0}
    pending: List[tuple] = []
    for model, row_id, title, refs, year, count in targets:
        stats["checked"] += 1
        facts = find_facts(title or "", refs, fetch, cache)
        if facts is None:
            stats["unknown"] += 1
        else:
            stats["matched"] += 1
            current = {"text_year": year, "hymnal_count": count}
            values = {k: v for k, v in facts.items() if v is not None and current[k] is None}
            if values:
                stats["updated"] += 1
                pending.append((model, row_id, values))
        if not dry_run and len(pending) >= WRITE_BATCH:
            _write(pending)
            pending = []
        if on_progress:
            on_progress(stats["checked"], len(targets))
    if not dry_run and pending:
        _write(pending)
    return stats
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_hymnary_facts.py -q`
Expected: all pass.

- [ ] **Step 5: Add the CLI**

Create `backend/backfill_hymn_facts.py`:

```python
#!/usr/bin/env python3
"""Fill in each hymn's year and familiarity from Hymnary.org's public API.

Fills blanks only (never overwrites), so it is safe to re-run and manual
corrections survive. Run AFTER migrate_add_hymn_facts.py. Requests are spaced
DELAY_SECONDS apart to be polite to Hymnary.org.

    python backfill_hymn_facts.py --dry-run
    python backfill_hymn_facts.py
"""
import argparse
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

from hymnary_facts import API_URL, run_backfill  # noqa: E402

DELAY_SECONDS = 1.0


def make_fetch(client: httpx.Client, delay: float = DELAY_SECONDS):
    def fetch(ref: str):
        time.sleep(delay)
        try:
            response = client.get(API_URL, params={"reference": ref})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"  ! {ref}: {exc}")
            return []
    return fetch


def _progress(done: int, total: int) -> None:
    if done % 50 == 0 or done == total:
        print(f"  {done}/{total} hymns checked")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill hymn year and familiarity from Hymnary.org.")
    parser.add_argument("--dry-run", action="store_true", help="report matches without writing")
    args = parser.parse_args()
    headers = {"User-Agent": "worship-service-builder hymn-facts backfill"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        stats = run_backfill(make_fetch(client), dry_run=args.dry_run, on_progress=_progress)
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}checked {stats['checked']}, matched {stats['matched']}, "
          f"updated {stats['updated']}, unknown {stats['unknown']}")


if __name__ == "__main__":
    main()
```

Smoke-check that it imports (this makes no network calls):

Run: `cd backend && ../.venv/bin/python -c "import backfill_hymn_facts; print('ok')"; cd ..`
Expected: `ok`

- [ ] **Step 6: Commit**

```bash
git add backend/hymnary_facts.py backend/backfill_hymn_facts.py backend/tests/test_hymnary_facts.py
git commit -m "Backfill hymn year and familiarity from Hymnary.org's public API

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Rank hymn candidates

**Files:**
- Create: `backend/hymn_ranking.py`
- Test: `backend/tests/test_hymn_ranking.py`

**Interfaces:**
- Consumes: flat hymn dicts with `"Text Year"` / `"Hymnal Count"` (Task 4); `hymn_utils.get_property_value`.
- Produces:
  - `rank_candidates(hymns, *, prefer_before_year: int, prefer_familiar: bool) -> list[dict]`: a new list; the input is not mutated
  - `facts_note(hymn) -> str`: `"(written 1826, in 1,322 hymnals)"`, a partial version, or `""`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_hymn_ranking.py`:

```python
from hymn_ranking import facts_note, rank_candidates


def h(name, year=None, count=None):
    return {"id": name, "Hymn Title": name, "Text Year": year, "Hymnal Count": count}


def titles(hymns):
    return [x["Hymn Title"] for x in hymns]


def test_older_first_then_unknown_then_newer():
    hymns = [h("new", 1990), h("unknown"), h("old", 1826), h("edge", 1970)]
    ranked = rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=False)
    assert titles(ranked) == ["old", "unknown", "new", "edge"]   # 1970 is not "before 1970"


def test_familiar_first_within_each_era():
    hymns = [h("old-rare", 1800, 10), h("old-famous", 1850, 3000), h("new-famous", 1990, 900)]
    ranked = rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=True)
    assert titles(ranked) == ["old-famous", "old-rare", "new-famous"]


def test_unknown_count_ranks_as_the_median():
    hymns = [h("low", 1800, 10), h("unknown", 1800), h("high", 1800, 1000), h("mid", 1800, 100)]
    ranked = rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=True)
    # median of known counts (10, 100, 1000) is 100; ties keep input order
    assert titles(ranked) == ["high", "unknown", "mid", "low"]


def test_familiarity_off_keeps_input_order_within_era():
    hymns = [h("b", 1800, 10), h("a", 1800, 3000)]
    assert titles(rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=False)) == ["b", "a"]


def test_does_not_mutate_input_and_handles_empty():
    hymns = [h("new", 1990), h("old", 1800)]
    rank_candidates(hymns, prefer_before_year=1970, prefer_familiar=True)
    assert titles(hymns) == ["new", "old"]
    assert rank_candidates([], prefer_before_year=1970, prefer_familiar=True) == []


def test_facts_note():
    assert facts_note(h("x", 1826, 1322)) == "(written 1826, in 1,322 hymnals)"
    assert facts_note(h("x", 1826)) == "(written 1826)"
    assert facts_note(h("x", None, 84)) == "(in 84 hymnals)"
    assert facts_note(h("x")) == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_hymn_ranking.py -q`
Expected: `ModuleNotFoundError: No module named 'hymn_ranking'`.

- [ ] **Step 3: Implement**

Create `backend/hymn_ranking.py`:

```python
#!/usr/bin/env python3
"""Order hymn candidates by the rubric's preferences: older first, then more
familiar. Preferences, not filters: nothing is ever removed."""
import statistics
from typing import Any, Dict, List

from hymn_utils import get_property_value

_OLDER, _UNKNOWN, _NEWER = 0, 1, 2


def _era(hymn: Dict[str, Any], before_year: int) -> int:
    year = get_property_value(hymn, "Text Year")
    if year is None:
        return _UNKNOWN
    return _OLDER if year < before_year else _NEWER


def rank_candidates(hymns: List[Dict[str, Any]], *, prefer_before_year: int,
                    prefer_familiar: bool) -> List[Dict[str, Any]]:
    """A new list: hymns written before `prefer_before_year` first, then
    unknown years, then newer ones. Within each group, when `prefer_familiar`
    is on, hymns in more hymnals come first. An unknown count ranks as the
    median of the known counts, so it is neither pushed up nor down. The sort
    is stable, so ties keep their original order."""
    counts = [c for x in hymns if (c := get_property_value(x, "Hymnal Count")) is not None]
    median = statistics.median(counts) if counts else 0

    def key(hymn):
        era = _era(hymn, prefer_before_year)
        if not prefer_familiar:
            return (era, 0)
        count = get_property_value(hymn, "Hymnal Count")
        return (era, -(median if count is None else count))

    return sorted(hymns, key=key)


def facts_note(hymn: Dict[str, Any]) -> str:
    """'(written 1826, in 1,322 hymnals)' with whichever facts are known, or ''."""
    year = get_property_value(hymn, "Text Year")
    count = get_property_value(hymn, "Hymnal Count")
    parts = []
    if year is not None:
        parts.append(f"written {year}")
    if count is not None:
        parts.append(f"in {count:,} hymnals")
    return f"({', '.join(parts)})" if parts else ""
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_hymn_ranking.py -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/hymn_ranking.py backend/tests/test_hymn_ranking.py
git commit -m "Rank hymn candidates older-first, then by familiarity

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The hymn picker follows the rubric

**Files:**
- Modify: `backend/worship_service.py`: imports; `suggest_hymns_for_service` (currently lines 380–579); `hymn_display_info` (currently lines 582–609)
- Test: `backend/tests/test_suggest_hymns.py`

**Interfaces:**
- Consumes: `service_rubric.default_rubric`, `HYMN_SLOTS`, `HYMN_SLOT_LABELS`, `format_checklist` (Task 1); `hymn_ranking.rank_candidates`, `facts_note` (Task 6).
- Produces:
  - `suggest_hymns_for_service(..., rubric: dict | None = None)`, where `None` means the defaults. Other parameters are unchanged.
  - `hymn_display_info(hymn, *, resolve_audio=False, prefer_before_year: int | None = None)` now also returns `"year"`, `"hymnal_count"` and `"newer_than_preferred"`. The last is `True` only when the year and `prefer_before_year` are both known and `year >= prefer_before_year`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_suggest_hymns.py`:

```python
import json
from types import SimpleNamespace

import pytest

import worship_service
from service_rubric import default_rubric


class FakeOpenAI:
    """Stands in for openai.OpenAI: records each request and returns `reply`."""

    def __init__(self, reply):
        self.reply = reply
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        message = SimpleNamespace(content=self.reply)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def hymn(title, number, theme, year=None, count=None):
    return {"id": title, "Hymn Title": title, "Hymn Number": number, "Theme": theme,
            "Scripture References": "Isaiah 6:3", "Hymnary.org Link": None,
            "Text Year": year, "Hymnal Count": count}


HYMNS = [
    hymn("Newer Gathering Song", 1, "gathering", 1995, 40),
    hymn("Holy, Holy, Holy", 2, "gathering, praise", 1826, 1322),
    hymn("Go Forth Rejoicing", 3, "sending, joy", 1985, 20),
    hymn("Rejoice, the Lord Is King", 4, "joy, praise", 1744, 900),
]


@pytest.fixture
def fake(monkeypatch):
    reply = json.dumps({"opening": ["Holy, Holy, Holy"], "response": ["Holy, Holy, Holy"],
                        "closing": ["Go Forth Rejoicing", "Rejoice, the Lord Is King"]})
    client = FakeOpenAI(reply)
    monkeypatch.setattr(worship_service, "OpenAI", lambda api_key: client)
    return client


def suggest(**kwargs):
    return worship_service.suggest_hymns_for_service(
        db=None, occasion="Trinity Sunday", scriptures=["Isaiah 6:1-8"],
        api_key="test-key", all_hymns=HYMNS, **kwargs,
    )


def prompt_of(fake):
    return fake.requests[0]["messages"][0]["content"]


def test_prompt_uses_the_default_slot_checklists_and_preferences(fake):
    suggest()
    prompt = prompt_of(fake)
    assert "A good Closing (Sending) Hymn:\n- is joyful and upbeat" in prompt
    assert "- sends people out to serve others and share God's love" in prompt
    assert "A good Opening (Gathering) Hymn:" in prompt
    assert "Must be joyful, upbeat, or sending" not in prompt   # old hard-coded roles are gone
    assert ("Prefer hymns written before 1970 and hymns found in many hymnals; "
            "choose a newer hymn only when it fits clearly better.") in prompt


def test_candidates_show_facts_and_rank_older_familiar_first(fake):
    suggest()
    prompt = prompt_of(fake)
    assert "Holy, Holy, Holy (#2) (written 1826, in 1,322 hymnals)" in prompt
    opening = prompt.split("OPENING CANDIDATES")[1].split("RESPONSE CANDIDATES")[0]
    assert opening.index("Holy, Holy, Holy") < opening.index("Newer Gathering Song")


def test_a_church_rubric_changes_the_prompt(fake):
    rubric = default_rubric()
    rubric["hymns"]["closing"] = ["ends with a rousing doxology"]
    rubric["prefer_before_year"] = 1900
    rubric["prefer_familiar"] = False
    suggest(rubric=rubric)
    prompt = prompt_of(fake)
    assert "A good Closing (Sending) Hymn:\n- ends with a rousing doxology" in prompt
    assert "is joyful and upbeat" not in prompt
    assert "Prefer hymns written before 1900; choose a newer hymn" in prompt
    assert "hymns found in many hymnals" not in prompt


def test_results_carry_year_and_newer_flag(fake):
    result = suggest()
    closing = {info["title"]: info for info in result["closing"]}
    assert closing["Go Forth Rejoicing"]["year"] == 1985
    assert closing["Go Forth Rejoicing"]["newer_than_preferred"] is True
    assert closing["Rejoice, the Lord Is King"]["newer_than_preferred"] is False
    assert closing["Rejoice, the Lord Is King"]["hymnal_count"] == 900


def test_hymn_display_info_without_a_preference_never_flags():
    info = worship_service.hymn_display_info(HYMNS[0])
    assert info["year"] == 1995
    assert info["newer_than_preferred"] is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_suggest_hymns.py -q`
Expected: failures (for example, `TypeError: suggest_hymns_for_service() got an unexpected keyword argument 'rubric'`, and assertion errors on the prompt text).

- [ ] **Step 3: Implement**

In `backend/worship_service.py`, change the import line `import liturgy_prompts` to:

```python
import hymn_ranking
import liturgy_prompts
import service_rubric
```

In `suggest_hymns_for_service`'s signature, add `rubric: Optional[Dict[str, Any]] = None,` after `all_hymns: Optional[List[Dict[str, Any]]] = None,`. Add this to the end of the docstring: `*rubric* (a merged service rubric; None means the defaults) supplies the slot checklists and the older/familiar preferences.`

Right after `scripture_full_texts = scripture_full_texts or {}` at the top of the body, add:

```python
    if rubric is None:
        rubric = service_rubric.default_rubric()
```

Replace the candidate-building block (from `opening_candidates = [h for h in all_hymns if _hymn_matches_theme(h, _OPENING_THEMES)]` through `response_candidates = scripture_hymns if scripture_hymns else all_hymns[:80]`) with:

```python
    def _rank(hymns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return hymn_ranking.rank_candidates(
            hymns,
            prefer_before_year=rubric["prefer_before_year"],
            prefer_familiar=rubric["prefer_familiar"],
        )

    # A slot with no theme-matched hymns falls back to the whole ranked hymnal.
    opening_candidates = _rank(
        [h for h in all_hymns if _hymn_matches_theme(h, _OPENING_THEMES)] or all_hymns
    )
    closing_candidates = _rank(
        [h for h in all_hymns if _hymn_matches_theme(h, _CLOSING_THEMES)] or all_hymns
    )
    response_candidates = _rank(scripture_hymns or all_hymns)
```

In `_hymn_summary`, replace its `return` line with:

```python
        facts = hymn_ranking.facts_note(h)
        return (
            f"- {title} (#{num})"
            + (f" {facts}" if facts else "")
            + (f" [themes: {themes_str}]" if themes_str else "")
            + (f" [scripture: {script[:60]}...]" if len(script) > 60 else f" [scripture: {script}]" if script else "")
        )
```

Just before `prompt = f"""You are helping plan a worship service...`, add:

```python
    slot_checklists = "\n\n".join(
        service_rubric.format_checklist(service_rubric.HYMN_SLOT_LABELS[slot], rubric["hymns"][slot])
        for slot in service_rubric.HYMN_SLOTS
    )
    preference = (
        f"Prefer hymns written before {rubric['prefer_before_year']}"
        + (" and hymns found in many hymnals" if rubric["prefer_familiar"] else "")
        + "; choose a newer hymn only when it fits clearly better."
    )
```

In the prompt f-string, replace the whole `ROLE REQUIREMENTS:` block (the heading plus its three `- OPENING/RESPONSE/CLOSING` lines) with:

```
ROLE REQUIREMENTS (what makes a good hymn for each slot):

{slot_checklists}

PREFERENCES: {preference} Each candidate shows when its words were written and how many hymnals include it, when known.
```

In `_resolve`, change both `info = hymn_display_info(title_to_hymn[key])` and `info = hymn_display_info(h)` to pass the preference:

```python
                    info = hymn_display_info(title_to_hymn[key], prefer_before_year=rubric["prefer_before_year"])
```

```python
                            info = hymn_display_info(h, prefer_before_year=rubric["prefer_before_year"])
```

Replace `hymn_display_info`'s signature and return statement:

```python
def hymn_display_info(
    hymn: Dict[str, Any],
    *,
    resolve_audio: bool = False,
    prefer_before_year: Optional[int] = None,
) -> Dict[str, Any]:
```

```python
    year = get_property_value(hymn, "Text Year")
    return {
        "title": title,
        "number": number,
        "link": link,
        "audio_url": audio_url,
        "year": year,
        "hymnal_count": get_property_value(hymn, "Hymnal Count"),
        "newer_than_preferred": (
            year is not None and prefer_before_year is not None and year >= prefer_before_year
        ),
    }
```

Add this sentence to its docstring: `newer_than_preferred is True when the words were written in or after prefer_before_year, so a UI can label the hymn with its year.`

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_suggest_hymns.py -q && .venv/bin/python -m pytest -q`
Expected: the new tests pass, and the full suite passes.

- [ ] **Step 5: Commit**

```bash
git add backend/worship_service.py backend/tests/test_suggest_hymns.py
git commit -m "Hymn suggestions follow the rubric: slot checklists, older and familiar first

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The liturgy writer follows the rubric

**Files:**
- Modify: `backend/worship_service.py`: `generate_liturgy` (currently lines 686–766), plus a new helper just above it
- Modify: `backend/liturgy_prompts.py`: the `prayer_for_illumination` and `offertory_prayer` defaults
- Test: `backend/tests/test_generate_liturgy.py` (create); `backend/tests/test_liturgy_prompts.py` (append)

**Interfaces:**
- Consumes: `service_rubric.default_rubric`, `format_checklist` (Task 1); `liturgy_prompts.SECTION_LABELS`.
- Produces:
  - `generate_liturgy(..., rubric: dict | None = None, sermon_text: tuple[str, str] | None = None)`. `sermon_text` is `(reference, passage_text)`. Other parameters are unchanged.
  - `SERMON_TEXT_LIMIT = 2000`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_generate_liturgy.py`:

```python
from types import SimpleNamespace

import pytest

import liturgy_prompts
import worship_service
from service_rubric import default_rubric


class FakeOpenAI:
    """Stands in for openai.OpenAI: records each request and returns a fixed text."""

    def __init__(self):
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Draft."))])


@pytest.fixture
def fake(monkeypatch):
    client = FakeOpenAI()
    monkeypatch.setattr(worship_service, "OpenAI", lambda api_key: client)
    return client


def generate(sections, **kwargs):
    return worship_service.generate_liturgy(
        occasion="Third Sunday of Easter", scriptures=["Acts 9:1-6", "John 21:1-19"],
        hymns=[{"title": "Holy, Holy, Holy", "number": 138}], sections=sections,
        api_key="test-key", **kwargs,
    )


def user_message(request):
    return request["messages"][1]["content"]


def test_each_section_gets_its_default_checklist(fake):
    out = generate(["benediction", "prayer_of_confession"])
    assert out == {"benediction": "Draft.", "prayer_of_confession": "Draft."}
    benediction, confession = (user_message(r) for r in fake.requests)
    assert "A good Benediction:\n- speaks a blessing to the people" in benediction
    assert "A good Prayer of Confession:\n- names real, specific failings that are common to all people" in confession
    assert fake.requests[0]["messages"][0]["content"] == liturgy_prompts.DEFAULT_SYSTEM_PROMPT


def test_a_church_rubric_replaces_the_checklist(fake):
    rubric = default_rubric()
    rubric["prayers"]["benediction"] = ["ends with the Aaronic blessing"]
    generate(["benediction"], rubric=rubric)
    text = user_message(fake.requests[0])
    assert "A good Benediction:\n- ends with the Aaronic blessing" in text
    assert "speaks a blessing to the people" not in text


def test_edited_prompts_still_get_the_checklist(fake):
    generate(["benediction"], prompt_overrides={"benediction": "My own benediction instruction."})
    text = user_message(fake.requests[0])
    assert text.startswith("My own benediction instruction.")
    assert "A good Benediction:" in text


def test_sermon_text_is_appended_for_themes_only(fake):
    generate(["prayer_of_confession"], sermon_text=("John 21:1-19", "Simon Peter said, I am going fishing."))
    text = user_message(fake.requests[0])
    assert ("Sermon text (John 21:1-19), for themes only; do not quote, cite, or name it:\n"
            "Simon Peter said, I am going fishing.") in text


def test_sermon_text_is_truncated(fake):
    generate(["benediction"], sermon_text=("John 21:1-19", "x" * 5000))
    text = user_message(fake.requests[0])
    assert "x" * worship_service.SERMON_TEXT_LIMIT in text
    assert "x" * (worship_service.SERMON_TEXT_LIMIT + 1) not in text


@pytest.mark.parametrize("sermon_text", [
    None, ("John 21:1-19", "[Could not load text]"), ("John 21:1-19", "  "), ("", "Some text."),
])
def test_missing_or_failed_sermon_text_is_skipped(fake, sermon_text):
    generate(["benediction"], sermon_text=sermon_text)
    assert "Sermon text" not in user_message(fake.requests[0])


def test_user_written_sections_are_not_sent_to_the_ai(fake):
    out = generate(["benediction"], user_overrides={"benediction": "Go in peace."})
    assert out == {"benediction": "Go in peace."}
    assert fake.requests == []
```

Append to `backend/tests/test_liturgy_prompts.py`:

```python
def test_short_prayers_default_to_three_sentences_at_most():
    assert "no more than 3 sentences" in lp.DEFAULT_SECTION_PROMPTS["prayer_for_illumination"]
    assert "3-5" not in lp.DEFAULT_SECTION_PROMPTS["prayer_for_illumination"]
    assert lp.DEFAULT_SECTION_PROMPTS["offertory_prayer"].startswith(
        "Write an Offertory Prayer for: {occasion}. No more than three sentences:"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest backend/tests/test_generate_liturgy.py backend/tests/test_liturgy_prompts.py -q`
Expected: failures (the checklist is not in the prompt, `rubric`/`sermon_text` are unexpected keyword arguments, and the defaults still say 3–5 sentences).

- [ ] **Step 3: Implement**

In `backend/liturgy_prompts.py`:

- In `prayer_for_illumination`, change `"Write 3-5 sentences asking God to open hearts and minds to the Word, that we may hear and respond. End with 'Amen.' "` to `"Write no more than 3 sentences asking God to open hearts and minds to the Word, that we may hear and respond. End with 'Amen.' "`.
- In `offertory_prayer`, change `"Three to five sentences: thank God for provision, dedicate our gifts and ourselves to God's service, "` to `"No more than three sentences: thank God for provision, dedicate our gifts and ourselves to God's service, "`.

In `backend/worship_service.py`, add this directly above `def generate_liturgy(`:

```python
SERMON_TEXT_LIMIT = 2000


def _sermon_text_block(sermon_text: Optional[tuple]) -> str:
    """The sermon-text context appended to each liturgy prompt, or '' when the
    reference or text is missing, or the passage failed to load."""
    if not sermon_text:
        return ""
    ref, text = sermon_text
    text = (text or "").strip()
    if not (ref or "").strip() or not text or "[Could not load text]" in text:
        return ""
    return (
        f"Sermon text ({ref.strip()}), for themes only; do not quote, cite, or name it:\n"
        f"{text[:SERMON_TEXT_LIMIT]}"
    )
```

Add two parameters to the end of `generate_liturgy`'s signature:

```python
    rubric: Optional[Dict[str, Any]] = None,
    sermon_text: Optional[tuple] = None,
```

Add this to the end of its docstring: `rubric (a merged service rubric; None means the defaults) adds each section's quality checklist to its prompt. sermon_text, as (reference, passage text), is added to every prompt for themes; it is skipped when missing or when the passage failed to load. Both are appended in code, so churches with edited prompts get them too.`

Right after `prompts = liturgy_prompts.merge_prompts(prompt_overrides)`, add:

```python
    if rubric is None:
        rubric = service_rubric.default_rubric()
    sermon_block = _sermon_text_block(sermon_text)
```

In the per-section loop, directly after the `prompt = liturgy_prompts.render(...)` call, add:

```python
        checklist = rubric["prayers"].get(section)
        if checklist:
            label = liturgy_prompts.SECTION_LABELS.get(section, section)
            prompt += "\n\n" + service_rubric.format_checklist(label, checklist)
        if sermon_block:
            prompt += "\n\n" + sermon_block
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest backend/tests/test_generate_liturgy.py backend/tests/test_liturgy_prompts.py -q && .venv/bin/python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/worship_service.py backend/liturgy_prompts.py backend/tests/test_generate_liturgy.py backend/tests/test_liturgy_prompts.py
git commit -m "Liturgy follows the rubric: per-prayer checklists and the sermon text

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Streamlit passes each church's rubric; deploy notes

**Files:**
- Modify: `ui_helpers.py`: add `sermon_text_for`
- Modify: `app.py`: imports (lines 20–40); the `suggest_hymns_for_service(...)` call (about line 764); the `generate_liturgy(...)` call (about line 936)
- Modify: `README.md`: add deploy steps
- Test: `streamlit_tests/test_app_helpers.py`: append

**Interfaces:**
- Consumes: `get_church_rubric` (Task 2); the `rubric=` parameter (Task 7) and the `rubric=`/`sermon_text=` parameters (Task 8).
- Produces: `ui_helpers.sermon_text_for(ref, cached_texts, fetch=None) -> tuple[str, str] | None`

- [ ] **Step 1: Write the failing tests**

Append to `streamlit_tests/test_app_helpers.py`:

```python
from ui_helpers import sermon_text_for


def test_sermon_text_uses_the_cached_passage():
    assert sermon_text_for("John 21:1-19", {"John 21:1-19": "Text."}) == ("John 21:1-19", "Text.")


def test_sermon_text_fetches_when_not_cached_or_failed():
    fetched = []

    def fetch(ref):
        fetched.append(ref)
        return "Fetched."

    assert sermon_text_for("John 21:1-19", {}, fetch) == ("John 21:1-19", "Fetched.")
    assert sermon_text_for("John 21:1-19", {"John 21:1-19": "[Could not load text]"}, fetch) == \
        ("John 21:1-19", "Fetched.")
    assert fetched == ["John 21:1-19", "John 21:1-19"]


def test_sermon_text_is_none_without_a_reference_or_any_text():
    assert sermon_text_for("", {"": "x"}) is None
    assert sermon_text_for(None, {}) is None
    assert sermon_text_for("John 21:1-19", {}) is None   # no cache, no fetcher

    def broken(_ref):
        raise RuntimeError("network down")

    assert sermon_text_for("John 21:1-19", None, broken) is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest streamlit_tests/test_app_helpers.py -q`
Expected: `ImportError: cannot import name 'sermon_text_for'`.

- [ ] **Step 3: Implement the helper**

Append to `ui_helpers.py`:

```python
_FAILED_TEXT = "[Could not load text]"


def sermon_text_for(ref, cached_texts, fetch=None):
    """(reference, passage text) for the liturgy writer, or None.

    Uses the passage already loaded on the page when there is one; otherwise
    asks `fetch(ref)`. A failed or empty load yields None, so liturgy generation
    never breaks on a missing sermon text."""
    ref = (ref or "").strip()
    if not ref:
        return None
    text = (cached_texts or {}).get(ref) or ""
    if (not text or text == _FAILED_TEXT) and fetch is not None:
        try:
            text = fetch(ref) or ""
        except Exception:
            text = ""
    text = text.strip()
    if not text or text == _FAILED_TEXT:
        return None
    return (ref, text)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest streamlit_tests/test_app_helpers.py -q`
Expected: all pass.

- [ ] **Step 5: Wire up `app.py`**

In the `from repos.churches import (...)` block, add `get_church_rubric`:

```python
from repos.churches import (
    list_user_churches, create_church, get_church_prompts, get_church_translation,
    get_church_rubric,
)
```

In the `from ui_helpers import (...)` block, add `sermon_text_for,` after `coerce_selectbox_value,`.

In the `suggest_hymns_for_service(...)` call, add after `all_hymns=all_hymns,`:

```python
                rubric=get_church_rubric(church_id),
```

In the `generate_liturgy(...)` call, add after `prompt_overrides=get_church_prompts(church_id),`:

```python
                    rubric=get_church_rubric(church_id),
                    sermon_text=sermon_text_for(
                        st.session_state.get("selected_nt_ref"),
                        st.session_state.get("scripture_full_texts"),
                        lambda ref: get_passage_text(
                            ref, translation=st.session_state.get("bible_translation", DEFAULT_TRANSLATION)
                        ),
                    ),
```

Verify that the app module still compiles:

Run: `.venv/bin/python -m py_compile app.py && echo ok`
Expected: `ok`

- [ ] **Step 6: Document the deploy steps**

Add this section to `README.md`, directly after the existing migration instructions (search for `python migrate_to_db.py`):

````markdown
### Service rubric: hymn year and familiarity

Hymns carry two facts from Hymnary.org: the year the words were written and how
many hymnals include them (familiarity). They drive the rubric's "prefer older"
and "prefer familiar" hymn suggestions.

1. **Before merging** code that maps these columns, add them to the deployed
   database. Both apps select every mapped column and would fail without them:

   ```bash
   cd backend && python migrate_add_hymn_facts.py
   ```

2. Fill them in from Hymnary.org's public API. This fills blanks only, so it is
   safe to re-run. It takes about a second per scripture reference:

   ```bash
   cd backend && python backfill_hymn_facts.py --dry-run
   cd backend && python backfill_hymn_facts.py
   ```
````

- [ ] **Step 7: Run the whole suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass (the 206 baseline plus the new tests).

- [ ] **Step 8: Commit**

```bash
git add ui_helpers.py app.py README.md streamlit_tests/test_app_helpers.py
git commit -m "Streamlit passes each church's rubric and the sermon text; document deploy order

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## After the tasks (for Beau, not the implementer)

1. Run `migrate_add_hymn_facts.py` against Supabase, then open the PR.
2. After merging, run `backfill_hymn_facts.py --dry-run` to see coverage, then run it for real.
3. The rubric editor screen comes in migration slice 6; the "newer hymn" year label comes in slice 3.
