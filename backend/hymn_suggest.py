"""Pure pieces of the AI hymn suggestions (slice 3 spec, Backend 3.6 steps 6-9
and 3.8; owner decision 3; owner answer Q1 of 2026-09-29: AI fills only empty
slots, a chosen hymn is never overwritten, filled slots get alternatives).

- build_candidates: each slot's candidate list, ranked by the church's
  rubric, cut to SLOT_CAP with NEWER_RESERVE places kept for newer and
  unknown-year hymns, and padded with an even sample of the hymnal.
- build_prompt: the messages and the H1..Hn token map, at most 24 000 characters.
- parse_suggestion_json, resolve_suggestions: the AI's answer as records.
- finalize_slots: distinct top picks for the empty slots and at least
  MIN_PER_SLOT hymns per slot when the candidates allow.

No I/O, no FastAPI, no Streamlit. Records are repos.hymns.HymnRecord.
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence

import hymn_ranking
import service_rubric
from domain_errors import InvalidInput, UpstreamError
from hymn_search import evenly_spaced, match_hymns, normalize_title, parse_themes
from scripture_refs import split_alternatives

SLOTS = ("opening", "response", "closing")
SLOT_CAP = 50               # candidates per slot shown to the AI
NEWER_RESERVE = 10          # of those, places kept for newer and unknown-year hymns (owner, 2026-09-26)
PAD_BELOW = 15              # a slot with fewer focused hymns than this ...
PAD_TO = 40                 # ... is padded to this many with an even sample of the hymnal
RESPONSE_LIMIT_PER_REF = 30  # parity: worship_service.py:460-464
MAX_PROMPT_CHARS = 24_000   # F §2.8
NT_EXCERPT_CHARS = 1_500    # parity: worship_service.py:497
MIN_PER_SLOT = 3            # a top pick plus 2 alternatives (owner decision 3)
MAX_PER_SLOT = 5

UNUSABLE_MESSAGE = "The AI gave an answer we couldn't use. Try again."
PROMPT_TOO_LONG_MESSAGE = "This prompt is too long."

# Theme keywords that pre-filter opening and closing candidates (moved from
# worship_service.py:367-368; matched at word starts, so "joy" finds
# "joyful" but not "enjoy"). They match the default slot checklists.
_OPENING_THEMES = {"gathering", "opening", "call to worship", "invitation", "welcome", "entrance"}
_CLOSING_THEMES = {"joy", "rejoice", "sending", "benediction", "mission", "dismissal", "praise",
                   "thanksgiving"}
_THEMES = {"opening": _OPENING_THEMES, "closing": _CLOSING_THEMES}

SYSTEM_MESSAGE = "You help a church choose hymns for a worship service. Reply with JSON only."
INSTRUCTION = ('Return {"opening": [ids], "response": [ids], "closing": [ids]}, with exactly 5 ids '
               "per slot (all of that slot's ids if it lists fewer than 5), best first, using only "
               "ids listed for that slot, and never the same hymn in two slots.")


def _year(record) -> Optional[int]:
    return record.text_year


def _count(record) -> Optional[int]:
    return record.hymnal_count


def matches_theme(record, keywords: set[str]) -> bool:
    text = " ".join(parse_themes(record.theme)).lower()
    return any(re.search(r"\b" + re.escape(keyword), text) for keyword in keywords)


def response_refs(nt_ref: Optional[str], scriptures: Sequence[str]) -> list[str]:
    """The NT reading's alternatives first, then every reading's, without repeats."""
    out: list[str] = []
    for ref in [*split_alternatives(nt_ref or ""),
                *(alt for line in scriptures for alt in split_alternatives(line or ""))]:
        if ref not in out:
            out.append(ref)
    return out


def _has_signal(records: Sequence[Any], prefer_familiar: bool) -> bool:
    """False when ranking could change nothing (no year known, and familiarity
    off or no count known): then lists are sampled, not ranked (S 3.8 item 3)."""
    return (any(r.text_year is not None for r in records)
            or (prefer_familiar and any(r.hymnal_count is not None for r in records)))


def _rank(records: list, rubric: Mapping[str, Any]) -> list:
    return hymn_ranking.rank_candidates(records, prefer_before_year=rubric["prefer_before_year"],
                                        prefer_familiar=rubric["prefer_familiar"],
                                        year_of=_year, count_of=_count)


@dataclass(frozen=True)
class Candidates:
    by_slot: dict[str, list]           # each at most SLOT_CAP focused hymns, then any pad
    modes: dict[str, str]              # "ranked" or "sampled" per slot (for the logs)


def build_candidates(eligible: Sequence[Any], scriptures: Sequence[str], *, nt_ref: Optional[str],
                     current_picks: Mapping[str, Optional[uuid.UUID]],
                     rubric: Mapping[str, Any]) -> Candidates:
    """S Backend 3.6 step 6 with 3.8's ranking. `eligible` is in hymnal order.
    Each slot's list leaves out the other two slots' current picks (a slot's
    own pick may stay), is ranked by the rubric and cut with shortlist when
    ranking has a signal, and otherwise truncated (response) or evenly sampled
    (opening, closing). A list with fewer than PAD_BELOW focused hymns gets an
    even sample of the rest, ranked, after the focused hymns, up to PAD_TO."""
    refs = response_refs(nt_ref, scriptures)
    by_slot: dict[str, list] = {}
    modes: dict[str, str] = {}
    for slot in SLOTS:
        others = {pick for other, pick in current_picks.items() if other != slot and pick is not None}
        pool = [h for h in eligible if h.id not in others]
        if slot == "response":
            focused = [m.record for m in match_hymns(pool, refs, limit_per_ref=RESPONSE_LIMIT_PER_REF,
                                                     max_results=200).items] if refs else []
        else:
            focused = [h for h in pool if matches_theme(h, _THEMES[slot])]
        if _has_signal(focused, rubric["prefer_familiar"]):
            modes[slot] = "ranked"
            focused = hymn_ranking.shortlist(_rank(focused, rubric), limit=SLOT_CAP,
                                             prefer_before_year=rubric["prefer_before_year"],
                                             reserve=NEWER_RESERVE, year_of=_year)
        else:
            modes[slot] = "sampled"
            if len(focused) > SLOT_CAP:
                focused = focused[:SLOT_CAP] if slot == "response" else evenly_spaced(focused, SLOT_CAP)
        if len(focused) < PAD_BELOW:
            chosen = {h.id for h in focused}
            rest = [h for h in pool if h.id not in chosen]
            pad = evenly_spaced(rest, PAD_TO - len(focused))
            if _has_signal(pad, rubric["prefer_familiar"]):
                pad = _rank(pad, rubric)
            focused = focused + pad
        by_slot[slot] = focused
    return Candidates(by_slot=by_slot, modes=modes)
