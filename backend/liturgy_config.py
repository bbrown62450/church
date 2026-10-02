"""The liturgy step's fixed data (slice 4 spec, Backend 1; F §2.3 step 2).

The one home of the constants the Streamlit app held (app.py:67, 148-166, the
four section-list copies and 969-971) and of the communion text that
worship_service's docx helper held (_add_communion_liturgy,
worship_service.py:68-135 at 9ab3fa6; the spec's "78-145" is an older
numbering of the same function):

- SECTIONS (and SECTION_ORDER, SECTION_LABELS): the 8 liturgy sections, their
  default switch states, textarea rows, hints and AI token budgets.
- CUSTOM_PLACEMENTS, PLACEMENT_KEYS, normalize_placement: where a custom
  element prints.
- OUTLINE: the order of worship exactly as build_docx prints it, the only
  encoding of that order (5a's orderOfWorship receives it from
  GET /liturgy/config; shared/liturgy_outline.json is generated from it).
- ASSURANCE_RESPONSE, COMMUNION_*, DEFAULT_BENEDICTION_FALLBACK, LIMITS.
- is_first_sunday_of_month, resolve_default_benediction.

Pure: standard library only, so every layer can import it
(tests/test_no_streamlit_in_core.py). app.py on main keeps its own frozen
copies; nothing is re-exported from Streamlit modules.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, Optional


@dataclass(frozen=True)
class SectionSpec:
    key: str
    label: str
    default_enabled: bool
    rows: int
    pastor_copy_only: bool
    hint: Optional[str]
    max_completion_tokens: int
    # A per-call override of OPENAI_TIMEOUT_SECONDS (S Risks 1): a long prayer
    # gets 60 s attempts. The usecase's 80 s deadline still caps each attempt
    # and allows a retry only when time is left (F §1.8). None: the setting.
    timeout_seconds: Optional[float] = None


# SECTION_ORDER order; labels as liturgy_prompts.py:29-38 had them. Hints mirror
# the docx formatting (worship_service.py _add_leader_people_paragraph, the bold
# confession, _add_assurance_paragraph); 4b shows Assurance's hint under the
# fixed ASSURANCE_RESPONSE line and Benediction's only while the card follows
# the church default.
SECTIONS: tuple[SectionSpec, ...] = (
    SectionSpec("call_to_worship", "Call to Worship", True, 4, False,
                "Start lines with “Leader:” or “People:”. People lines print in bold.", 1500),
    SectionSpec("opening_prayer", "Opening Prayer", True, 4, False, None, 1500),
    SectionSpec("prayer_of_confession", "Prayer of Confession", True, 4, False,
                "Printed in bold for everyone to read together.", 1500),
    SectionSpec("assurance", "Assurance of Pardon", True, 4, False,
                "Added automatically after your text.", 1500),
    SectionSpec("prayer_for_illumination", "Prayer for Illumination", True, 4, False, None, 1500),
    SectionSpec("prayers_of_the_people", "Prayers of the People", False, 8, True, None, 4000,
                timeout_seconds=60.0),
    SectionSpec("offertory_prayer", "Offertory Prayer", True, 4, False, None, 1500),
    SectionSpec("benediction", "Benediction", True, 4, False,
                "Your church's default benediction. Admins can change it in Settings.", 1500),
)

SECTION_ORDER: list[str] = [spec.key for spec in SECTIONS]
SECTION_LABELS: dict[str, str] = {spec.key: spec.label for spec in SECTIONS}
SECTIONS_BY_KEY: dict[str, SectionSpec] = {spec.key: spec for spec in SECTIONS}

# The 17 (key, label) pairs of app.py:148-166, in order. One label differs
# from app.py: owner decision B renames the first reading's heading to
# "First Reading" wherever the app shows it (slice 4a plan, clarification 3).
CUSTOM_PLACEMENTS: tuple[tuple[str, str], ...] = (
    ("call_to_worship", "After Call to Worship"),
    ("opening_prayer", "After Opening Prayer"),
    ("first_hymn", "After First Hymn"),
    ("prayer_of_confession", "After Prayer of Confession"),
    ("assurance", "After Assurance of Pardon"),
    ("prayer_for_illumination", "After Prayer for Illumination"),
    ("ot_reading", "After First Reading"),
    ("nt_reading", "After New Testament Reading"),
    ("sermon", "After Sermon"),
    ("affirmation_of_faith", "After Affirmation of Faith"),
    ("second_hymn", "After Second Hymn"),
    ("communion", "After Communion"),
    ("prayers_of_the_people", "After Prayers of the People"),
    ("offertory_prayer", "After Offertory Prayer"),
    ("third_hymn", "After Third Hymn"),
    ("benediction", "Before Benediction"),
    ("end", "At the end (after Benediction)"),
)
PLACEMENT_KEYS: frozenset[str] = frozenset(key for key, _label in CUSTOM_PLACEMENTS)


def normalize_placement(key: Any) -> str:
    """A known placement key unchanged; anything else "end" (never dropped: F §4.6)."""
    return key if isinstance(key, str) and key in PLACEMENT_KEYS else "end"


OutlineKind = Literal["section", "landmark", "communion"]
ValueSource = Literal["none", "hymn_opening", "hymn_response", "hymn_closing",
                      "reading_ot", "reading_nt", "sermon_title", "fixed"]


@dataclass(frozen=True)
class OutlineItem:
    kind: OutlineKind
    key: str
    label: str                          # identical to the docx heading (5a: "First Reading")
    value_source: ValueSource
    fixed_text: Optional[str]
    anchors_after: tuple[str, ...]      # placement keys whose custom elements follow this item


COMMUNION_TITLE = "The Sacrament of the Lord's Supper"
COMMUNION_TOGGLE_LABEL = "Include communion liturgy (The Sacrament of the Lord's Supper)"


def _section(key: str) -> OutlineItem:
    return OutlineItem("section", key, SECTION_LABELS[key], "none", None, (key,))


# build_docx's emission order (worship_service.py build_docx); every placement
# key appears exactly once across anchors_after.
OUTLINE: tuple[OutlineItem, ...] = (
    _section("call_to_worship"),
    _section("opening_prayer"),
    OutlineItem("landmark", "first_hymn", "First Hymn", "hymn_opening", None, ("first_hymn",)),
    _section("prayer_of_confession"),
    _section("assurance"),
    _section("prayer_for_illumination"),
    OutlineItem("landmark", "ot_reading", "First Reading", "reading_ot", None, ("ot_reading",)),
    OutlineItem("landmark", "nt_reading", "New Testament Reading", "reading_nt", None, ("nt_reading",)),
    OutlineItem("landmark", "sermon", "Sermon Title", "sermon_title", None, ("sermon",)),
    OutlineItem("landmark", "affirmation_of_faith", "Affirmation of Faith", "fixed", "Apostles' Creed",
                ("affirmation_of_faith",)),
    OutlineItem("landmark", "second_hymn", "Second Hymn", "hymn_response", None, ("second_hymn",)),
    OutlineItem("communion", "communion", COMMUNION_TITLE, "none", None, ("communion",)),
    _section("prayers_of_the_people"),
    _section("offertory_prayer"),
    OutlineItem("landmark", "third_hymn", "Third Hymn", "hymn_closing", None, ("third_hymn", "benediction")),
    OutlineItem("section", "benediction", "Benediction", "none", None, ("end",)),
)


def outline_as_json() -> list[dict[str, Any]]:
    """OUTLINE in GET /liturgy/config's OutlineItemOut shape (shared/liturgy_outline.json)."""
    return [{"kind": item.kind, "key": item.key, "label": item.label,
             "value_source": item.value_source, "fixed_text": item.fixed_text,
             "anchors_after": list(item.anchors_after)} for item in OUTLINE]


ASSURANCE_RESPONSE = "People: Thanks be to God! Amen."      # worship_service._add_assurance_paragraph prints it


CommunionStyle = Literal["heading1", "heading2", "text", "response", "blank"]


@dataclass(frozen=True)
class CommunionBlock:
    style: CommunionStyle     # heading1/heading2: a Heading 1/2 paragraph; response: one bold run
    text: str                 # "" for a blank paragraph


# worship_service._add_communion_liturgy's paragraphs as data, verbatim.
COMMUNION_BLOCKS: tuple[CommunionBlock, ...] = (
    CommunionBlock("heading1", COMMUNION_TITLE),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Invitation to the Table"),
    CommunionBlock("text",
                   "This is the table of our Lord Jesus Christ. It is not a reward for the righteous, "
                   "but nourishment for those who hunger; not a prize for the strong, but grace for those who are weary. "
                   "Here, blessing is not earned but received. All who seek to walk humbly with God, and who trust in God's mercy, "
                   "are welcome at this table."),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Great Thanksgiving"),
    CommunionBlock("text", "The Lord be with you."),
    CommunionBlock("response", "And also with you."),
    CommunionBlock("text", "Lift up your hearts."),
    CommunionBlock("response", "We lift them up to the Lord."),
    CommunionBlock("text", "Let us give thanks to the Lord our God."),
    CommunionBlock("response", "It is right to give our thanks and praise."),
    CommunionBlock("text",
                   "It is truly right and our greatest joy to give you thanks and praise, O God, "
                   "creator of heaven and earth, for you have made us and all things, and in your love you hold us in life. "
                   "And so we join the everlasting song:"),
    CommunionBlock("response",
                   "Holy, holy, holy Lord, God of power and might, heaven and earth are full of your glory. "
                   "Hosanna in the highest. Blessed is the one who comes in the name of the Lord. Hosanna in the highest."),
    CommunionBlock("text",
                   "You are holy, O God of majesty, and blessed is Jesus Christ, your Son, our Lord, "
                   "who by his life, death, and resurrection has reconciled the world to you. On the night in which he gave himself up "
                   "he took bread, gave thanks, broke it, and gave it to his disciples. And likewise the cup after supper. "
                   "Remembering his death and resurrection, we offer ourselves in praise and thanksgiving. Therefore we proclaim the mystery of faith:"),
    CommunionBlock("text", "Christ has died."),
    CommunionBlock("text", "Christ is risen."),
    CommunionBlock("text", "Christ will come again."),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Words of Institution"),
    CommunionBlock("text", "[Words of institution as printed or as used.]"),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "The Lord's Prayer"),
    CommunionBlock("text", "[The Lord's Prayer as printed.]"),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Breaking of the Bread and Communion"),
    CommunionBlock("text",
                   "The bread that we break is a sharing in the body of Christ. "
                   "The cup that we bless is a sharing in the blood of Christ. Come, for all is ready."),
    CommunionBlock("blank", ""),
    CommunionBlock("heading2", "Prayer After Communion"),
    CommunionBlock("text",
                   "Gracious God, we give you thanks that you have fed us at this table of grace, "
                   "strengthening us not to win our lives, but to live them faithfully. Send us out to do justice, "
                   "to love kindness, and to walk humbly with you, bearing your blessing into a world still hungry for hope, "
                   "through Jesus Christ our Lord. Amen."),
    CommunionBlock("blank", ""),
)

# Owner decision 2026-10-02: the built-in Benediction is the full Halverson text,
# with quotes and attribution as the owner's bulletin prints it (the Streamlit
# seed, app.py DEFAULT_BENEDICTION, was the shorthand "Halverson"). A saved
# default that is exactly "Halverson" (trimmed, any case) resolves to it too.
DEFAULT_BENEDICTION_FALLBACK = (
    "\u201cYou go nowhere by accident. Wherever you go, God is sending you. Wherever you are, "
    "God has put you there. God has a purpose in your being there. Christ lives in you and has "
    "something he wants to do through you where you are. Believe this and go in the grace and "
    "love and power of Jesus Christ.\u201d - Richard Halverson"
)
HALVERSON_SHORTHAND = "halverson"               # compared trimmed and casefolded


@dataclass(frozen=True)
class Limits:
    max_section_text: int
    max_sermon_title: int
    max_custom_elements: int
    max_custom_label: int
    max_custom_text: int
    max_sections_per_request: int


LIMITS = Limits(max_section_text=20_000, max_sermon_title=300, max_custom_elements=30,
                max_custom_label=200, max_custom_text=10_000, max_sections_per_request=4)


def is_first_sunday_of_month(d: date) -> bool:
    """The communion default (app.py:969-971): a Sunday in the month's first 7 days."""
    return d.day <= 7 and d.weekday() == 6


def resolve_default_benediction(settings: Optional[Mapping[str, Any]]) -> str:
    """settings["default_benediction"] when it is a string (including "", meaning
    "no default"), except that the shorthand "Halverson" (trimmed, any case: the
    old seed) is the full Halverson text; anything else, or no settings, is
    DEFAULT_BENEDICTION_FALLBACK (the full Halverson text)."""
    value = settings.get("default_benediction") if isinstance(settings, Mapping) else None
    if not isinstance(value, str):
        return DEFAULT_BENEDICTION_FALLBACK
    if value.strip().casefold() == HALVERSON_SHORTHAND:
        return DEFAULT_BENEDICTION_FALLBACK
    return value
