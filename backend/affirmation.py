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
