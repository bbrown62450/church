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
import unicodedata
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
        # One point prints as one "- point" line, so line breaks and other
        # whitespace runs become single spaces.
        item = " ".join(item.split())
        if any(unicodedata.category(ch) == "Cc" for ch in item):
            raise ValueError("Checklist points cannot contain control characters.")
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
    """Check a sparse rubric patch and return it cleaned (each point trimmed,
    with whitespace runs, line breaks included, collapsed to single spaces).

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
