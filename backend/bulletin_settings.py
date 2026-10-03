"""The church's standing bulletin settings (printed bulletin spec, PR 2a):
what every week's printed bulletin prints the same way, stored in
churches.settings["bulletin"] (no column, no migration).

- BulletinSettings: the church's contact lines, the service time, the three
  people who lead (worship leader, liturgist, organist), which elements each
  of them leads, which elements carry the stand star, the stand note and the
  Gloria Patri words.
- read(settings): the stored value read tolerantly. A missing settings object,
  a missing "bulletin" key or a field of the wrong type is that field's
  default; unknown element keys and roles are dropped, and a text longer than
  its limit is cut to it (so GET always answers within PUT's limits). The defaults are PR 1's
  (the owner's sample): no contact lines, no names and no time (a blank field
  prints nothing, PR 2 planning answer 3), the sample's stars and leader roles,
  "Congregation stands if able" and the traditional Gloria Patri.
- to_json: the stored shape (what GET and PUT /church/bulletin-settings answer).
  PUT stores read({"bulletin": body}).to_json(), so the stored value is
  always clean: trimmed, blank address lines dropped, the stand note without
  its star, the starred keys and the leaders in ELEMENT_KEYS order.
Pure: no database, FastAPI or rendering here.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

Role = Literal["worship_leader", "liturgist", "organist"]
ROLES: tuple[Role, ...] = ("worship_leader", "liturgist", "organist")

# Every element the printed order of worship can star or give a leader, in its order.
ELEMENT_KEYS = (
    "prelude", "welcome", "call_to_worship", "opening_prayer", "first_hymn", "prayer_of_confession", "assurance",
    "gloria_patri", "prayer_for_illumination", "ot_reading", "nt_reading", "sermon", "affirmation_of_faith",
    "second_hymn", "prayers_of_the_people", "offering", "doxology", "offertory_prayer", "third_hymn",
    "benediction", "postlude",
)

# The longest value each field takes (PUT /church/bulletin-settings refuses longer). The cover's
# limits keep its contact lines short enough for the cover page (printed_pdf also shrinks them to fit).
MAX_ADDRESS_LINES = 3
MAX_LENGTH = {"address_line": 60, "phone": 40, "email": 100, "website": 100, "facebook": 60,
              "service_time": 40, "person": 100, "stand_note": 200, "gloria_patri_words": 1000}

# The owner's sample (PR 1's defaults).
DEFAULT_LEADERS: dict[str, Role] = {
    "prelude": "organist", "welcome": "liturgist", "call_to_worship": "liturgist", "opening_prayer": "liturgist",
    "prayer_of_confession": "liturgist", "assurance": "liturgist", "prayer_for_illumination": "liturgist",
    "ot_reading": "liturgist", "nt_reading": "worship_leader", "sermon": "worship_leader",
    "prayers_of_the_people": "worship_leader", "offertory_prayer": "worship_leader", "postlude": "organist",
}
DEFAULT_STARRED = frozenset({"first_hymn", "gloria_patri", "affirmation_of_faith", "second_hymn", "doxology",
                             "third_hymn", "benediction"})
DEFAULT_STAND_NOTE = "Congregation stands if able"
GLORIA_PATRI = ("Glory be to the Father, and to the Son, and to the Holy Ghost; as it was in the "
                "beginning, is now, and ever shall be, world without end. Amen, amen.")

_LIMIT = {"worship_leader": "person", "liturgist": "person", "organist": "person"}
_TEXT_FIELDS = ("phone", "email", "website", "facebook", "service_time", "worship_leader", "liturgist", "organist",
                "stand_note", "gloria_patri_words")


@dataclass(frozen=True)
class BulletinSettings:
    address_lines: tuple[str, ...] = ()
    phone: str = ""
    email: str = ""
    website: str = ""
    facebook: str = ""
    service_time: str = ""
    worship_leader: str = ""
    liturgist: str = ""
    organist: str = ""
    stand_note: str = DEFAULT_STAND_NOTE          # printed after a star: "*Congregation stands if able"
    starred: frozenset[str] = DEFAULT_STARRED
    gloria_patri_words: str = GLORIA_PATRI
    leaders: Mapping[str, Role] = field(default_factory=lambda: dict(DEFAULT_LEADERS))

    def leader(self, key: str) -> str:
        """The name of the person who leads element `key`; "" when no role or no name."""
        role = self.leaders.get(key)
        return getattr(self, role) if role in ROLES else ""

    def to_json(self) -> dict:
        """The stored shape; lists and the leaders in ELEMENT_KEYS order."""
        return {
            "address_lines": list(self.address_lines),
            **{name: getattr(self, name) for name in _TEXT_FIELDS},
            "starred": [key for key in ELEMENT_KEYS if key in self.starred],
            "leaders": {key: self.leaders[key] for key in ELEMENT_KEYS if key in self.leaders},
        }


def read(settings: object) -> BulletinSettings:
    """churches.settings["bulletin"], read tolerantly (see the module docstring)."""
    stored = settings.get("bulletin") if isinstance(settings, Mapping) else None
    if not isinstance(stored, Mapping):
        return BulletinSettings()
    values: dict = {}
    for name in _TEXT_FIELDS:
        value = stored.get(name)
        if isinstance(value, str):
            value = value.strip().lstrip("*").strip() if name == "stand_note" else value.strip()   # the star is printed
            values[name] = value[:MAX_LENGTH[_LIMIT.get(name, name)]]
    lines = stored.get("address_lines")
    if isinstance(lines, list):
        values["address_lines"] = tuple(line.strip()[:MAX_LENGTH["address_line"]] for line in lines
                                        if isinstance(line, str) and line.strip())[:MAX_ADDRESS_LINES]
    starred = stored.get("starred")
    if isinstance(starred, list):
        values["starred"] = frozenset(key for key in starred if key in ELEMENT_KEYS)
    leaders = stored.get("leaders")
    if isinstance(leaders, Mapping):
        values["leaders"] = {key: role for key, role in leaders.items() if key in ELEMENT_KEYS and role in ROLES}
    return BulletinSettings(**values)
