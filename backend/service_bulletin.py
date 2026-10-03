"""A service's weekly bulletin fields (printed bulletin spec, "Data model";
PR 2b): what the Bulletin step fills in for one week's printed bulletin,
stored in services.bulletin (migration 0006_services_bulletin).

- ServiceBulletin: the prelude and postlude (title, composer); this week's
  worship leader, liturgist and organist (None: the standing name from the
  bulletin settings; "": no one this week); a part's leader this week by
  element key (bulletin_settings.ELEMENT_KEYS); the announcements (ushers and
  counters, deacon of the week, coffee hour, activities, prayers and
  concerns, collection items, other announcements; PR 2 planning answer 4);
  the pasted text of the two readings (pasted wins over fetched); and the
  boxes whose text came from last week and are not checked yet
  (`unchecked`, so "From last week. Check before printing." comes back when
  the service is opened again; plan review fix I3).
- read(raw): a stored or posted value read tolerantly: anything that is not
  an object, a missing key or a value of the wrong type is blank (a person
  None); an unknown element key and a blank part leader are dropped; every
  text is trimmed and cut to its limit, and every one-line text (the music,
  the people, the part leaders, the ushers, the deacon and the coffee hour)
  has each run of line breaks, tabs or other control characters made one
  space. The free texts (activities, prayers and concerns, collection items,
  other announcements, the pasted readings) keep their lines, every line
  break as "\n" (a Windows or old-Mac ending, a vertical tab, a form feed,
  U+0085, U+2028 and U+2029 included, which the PDF would print as "?"), and
  a pasted reading's runs of blank lines become one paragraph break.
  `unchecked` keeps the known boxes, once each, in the step's order.
- to_json: the stored shape (what GET /services/{id} answers as `bulletin`).
- carried(): what a new week starts from (PR 2 planning answer 5): the music
  and the announcements; the people, the part leaders, the pasted texts and
  `unchecked` start empty.
- map_texts(fn): the same bulletin with fn applied to every text
  (usecases.archive makes them Word-safe with it).
Pure: no database, FastAPI or rendering here. Prayer concerns can hold names
and health news: nothing here logs, and no caller logs a bulletin's text.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from typing import Optional

from bulletin_settings import ELEMENT_KEYS, NOT_ONE_LINE, ROLES

ANNOUNCEMENT_KEYS = ("ushers", "deacon", "coffee_hour", "activities", "prayer_concerns", "collection", "other")
ONE_LINE_ANNOUNCEMENTS = ("ushers", "deacon", "coffee_hour")
# The boxes that carry forward to the next week (PR 2 planning answer 5), in the Bulletin step's order.
CARRY_KEYS = ("prelude", "postlude", *ANNOUNCEMENT_KEYS)

# The longest value each text takes; ServiceDraft refuses longer (422), and read() cuts a stored one.
MAX_LENGTH = {"title": 200, "composer": 100, "person": 100, "ushers": 200, "deacon": 100, "coffee_hour": 200,
              "activities": 4000, "prayer_concerns": 4000, "collection": 2000, "other": 4000,
              "reading_text": 10_000}

_NOT_ONE_LINE_RUN = re.compile(f" *[{NOT_ONE_LINE}][{NOT_ONE_LINE} ]*")
# Every way a pasted text can break a line, as one "\n" (U+2028 and U+2029 would print as "?" in the PDF).
_LINE_BREAK = re.compile(r"\r\n?|[\x0b\x0c\x85\u2028\u2029]")
# A run of blank lines (spaces allowed) in a pasted reading: one paragraph break.
_BLANK_LINES = re.compile(r"\n(?:[ \t]*\n)+")


@dataclass(frozen=True)
class Music:
    title: str = ""
    composer: str = ""


@dataclass(frozen=True)
class Announcements:
    ushers: str = ""                # Ushers/Counters
    deacon: str = ""                # Deacon of the Week
    coffee_hour: str = ""
    activities: str = ""            # This week's activities at a glance
    prayer_concerns: str = ""
    collection: str = ""            # Items for collection
    other: str = ""                 # Other announcements


def _no_one_changed() -> dict[str, Optional[str]]:
    return {role: None for role in ROLES}


@dataclass(frozen=True)
class ServiceBulletin:
    prelude: Music = Music()
    postlude: Music = Music()
    # This week's people: None prints the standing name (bulletin settings), "" no one.
    people: Mapping[str, Optional[str]] = field(default_factory=_no_one_changed)
    # A part's leader this week (element key -> name), over its standing role's name.
    leaders: Mapping[str, str] = field(default_factory=dict)
    announcements: Announcements = Announcements()
    ot_text: str = ""               # pasted text of the first reading (wins over the fetched text)
    nt_text: str = ""               # pasted text of the New Testament reading
    # The boxes (CARRY_KEYS) holding last week's text, not checked yet; saved so the marks come back on open.
    unchecked: tuple[str, ...] = ()

    def is_blank(self) -> bool:
        return self == ServiceBulletin()

    def carried(self) -> ServiceBulletin:
        """What the next week starts from: the music and the announcements."""
        return ServiceBulletin(prelude=self.prelude, postlude=self.postlude, announcements=self.announcements)

    def map_texts(self, fn: Callable[[str], str]) -> ServiceBulletin:
        """Every text through fn; a person left to the settings (None) stays None."""
        return ServiceBulletin(
            prelude=Music(fn(self.prelude.title), fn(self.prelude.composer)),
            postlude=Music(fn(self.postlude.title), fn(self.postlude.composer)),
            people={role: None if name is None else fn(name) for role, name in self.people.items()},
            leaders={key: fn(name) for key, name in self.leaders.items()},
            announcements=Announcements(**{f.name: fn(getattr(self.announcements, f.name))
                                           for f in fields(Announcements)}),
            ot_text=fn(self.ot_text), nt_text=fn(self.nt_text), unchecked=self.unchecked)

    def to_json(self) -> dict:
        return {
            "prelude": {"title": self.prelude.title, "composer": self.prelude.composer},
            "postlude": {"title": self.postlude.title, "composer": self.postlude.composer},
            "people": {role: self.people.get(role) for role in ROLES},
            "leaders": {key: self.leaders[key] for key in ELEMENT_KEYS if key in self.leaders},
            "announcements": {key: getattr(self.announcements, key) for key in ANNOUNCEMENT_KEYS},
            "reading_text": {"ot": self.ot_text, "nt": self.nt_text},
            "unchecked": list(self.unchecked),
        }


def _object(value: object) -> Mapping:
    return value if isinstance(value, Mapping) else {}


def _text(value: object, limit: int, *, one_line: bool, paragraphs: bool = False) -> str:
    if not isinstance(value, str):
        return ""
    if one_line:
        value = _NOT_ONE_LINE_RUN.sub(" ", value)
    else:
        value = _LINE_BREAK.sub("\n", value)
        if paragraphs:
            value = _BLANK_LINES.sub("\n\n", value)
    return value.strip()[:limit].strip()


def _unchecked(value: object) -> tuple[str, ...]:
    keys = {key for key in value if isinstance(key, str)} if isinstance(value, list) else set()
    return tuple(key for key in CARRY_KEYS if key in keys)


def _music(value: object) -> Music:
    raw = _object(value)
    return Music(_text(raw.get("title"), MAX_LENGTH["title"], one_line=True),
                 _text(raw.get("composer"), MAX_LENGTH["composer"], one_line=True))


def read(raw: object) -> ServiceBulletin:
    """A stored or posted bulletin, read tolerantly (see the module docstring)."""
    stored = _object(raw)
    people = _object(stored.get("people"))
    leaders = _object(stored.get("leaders"))
    announcements = _object(stored.get("announcements"))
    reading_text = _object(stored.get("reading_text"))
    return ServiceBulletin(
        prelude=_music(stored.get("prelude")),
        postlude=_music(stored.get("postlude")),
        people={role: _text(people[role], MAX_LENGTH["person"], one_line=True)
                if isinstance(people.get(role), str) else None for role in ROLES},
        leaders={key: name for key in ELEMENT_KEYS
                 if (name := _text(leaders.get(key), MAX_LENGTH["person"], one_line=True))},
        announcements=Announcements(**{key: _text(announcements.get(key), MAX_LENGTH[key],
                                                  one_line=key in ONE_LINE_ANNOUNCEMENTS)
                                       for key in ANNOUNCEMENT_KEYS}),
        ot_text=_text(reading_text.get("ot"), MAX_LENGTH["reading_text"], one_line=False, paragraphs=True),
        nt_text=_text(reading_text.get("nt"), MAX_LENGTH["reading_text"], one_line=False, paragraphs=True),
        unchecked=_unchecked(stored.get("unchecked")),
    )
