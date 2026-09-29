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


# --- the prompt (S Backend 3.6 step 7, 3.8 "Prompt") -------------------------------


def _clip(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text[:limit]


def _catalogue_line(token: str, record) -> str:
    number = record.number if record.number is not None else "–"
    facts = hymn_ranking.facts_note(record, year_of=_year, count_of=_count)
    return (f"{token} | {_clip(record.title, 80)} | #{number}"
            + (f" | {facts}" if facts else "")
            + f" | themes: {_clip(', '.join(parse_themes(record.theme)), 60)}"
            + f" | scripture: {_clip(record.scripture_refs or '', 60)}")


def _preferences(rubric: Mapping[str, Any]) -> str:
    """PR #4's PREFERENCES line, verbatim (worship_service.py:545-551)."""
    return (f"Prefer hymns written before {rubric['prefer_before_year']}"
            + (" and hymns found in many hymnals" if rubric["prefer_familiar"] else "")
            + "; choose a newer hymn only when it fits clearly better. Each candidate shows when "
              "its words were written and how many hymnals include it, when known.")


def _render(lists: Mapping[str, list], *, occasion: str, scriptures: Sequence[str],
            nt_ref: Optional[str], nt_text: Optional[str],
            rubric: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    tokens: dict[uuid.UUID, str] = {}
    token_map: dict[str, Any] = {}
    catalogue: list[str] = []
    for slot in SLOTS:
        for record in lists[slot]:
            if record.id not in tokens:
                token = f"H{len(tokens) + 1}"
                tokens[record.id] = token
                token_map[token] = record
                catalogue.append(_catalogue_line(token, record))
    readings = "\n".join(f"- {_clip(s, 200)}" for s in scriptures if (s or "").strip()) or "None"
    excerpt = _clip(nt_text or "", NT_EXCERPT_CHARS) or "(no text loaded)"
    checklists = "\n\n".join(
        service_rubric.format_checklist(service_rubric.HYMN_SLOT_LABELS[slot], rubric["hymns"][slot])
        for slot in service_rubric.HYMN_SLOTS)
    slot_lines = "\n".join(f"{slot.upper()} CANDIDATES: " + ", ".join(tokens[r.id] for r in lists[slot])
                           for slot in SLOTS)
    user = (f"OCCASION: {_clip(occasion, 300) or 'Not specified'}\n"
            f"SCRIPTURE READINGS:\n{readings}\n"
            f"NEW TESTAMENT READING (for the response hymn): {nt_ref or 'Not specified'}\n"
            f"NT PASSAGE TEXT (excerpt): {excerpt}\n\n"
            f"ROLE REQUIREMENTS (what makes a good hymn for each slot):\n\n{checklists}\n\n"
            f"PREFERENCES: {_preferences(rubric)}\n\n"
            "HYMNS:\n" + "\n".join(catalogue) + "\n\n"
            f"{slot_lines}\n\n{INSTRUCTION}")
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}, {"role": "user", "content": user}]
    return messages, token_map


def prompt_size(messages: Sequence[Mapping[str, str]]) -> int:
    return sum(len(m["content"]) for m in messages)


def build_prompt(candidates: Candidates, *, occasion: str, scriptures: Sequence[str],
                 nt_ref: Optional[str], nt_text: Optional[str],
                 rubric: Mapping[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    """(messages, {"H1": record, ...}), at most MAX_PROMPT_CHARS in all. While
    it is longer, the last candidate of the longest slot list (the first such
    slot on a tie) is dropped, with its catalogue line when no other list uses
    it. Checklist points are never dropped. Deterministic."""
    lists = {slot: list(candidates.by_slot[slot]) for slot in SLOTS}
    while True:
        messages, token_map = _render(lists, occasion=occasion, scriptures=scriptures,
                                      nt_ref=nt_ref, nt_text=nt_text, rubric=rubric)
        if prompt_size(messages) <= MAX_PROMPT_CHARS:
            return messages, token_map
        longest = max(SLOTS, key=lambda slot: len(lists[slot]))
        if not lists[longest]:
            raise InvalidInput(PROMPT_TOO_LONG_MESSAGE, code="prompt_invalid")
        lists[longest].pop()


# --- the answer (S Backend 3.6 step 9) ---------------------------------------------


def parse_suggestion_json(raw: str) -> dict[str, list]:
    """The AI's JSON object, code fences stripped (parity, worship_service.py:531-535).
    Each slot's value must be a list; a missing slot is []. Anything else is
    UpstreamError ai_upstream_error "The AI gave an answer we couldn't use. Try again."."""
    content = (raw or "").strip()
    if "```" in content:
        content = content.split("```")[1]
        if content.lower().startswith("json"):
            content = content[4:]
    try:
        data = json.loads(content.strip())
    except (ValueError, TypeError):
        raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error") from None
    if not isinstance(data, dict):
        raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error")
    out: dict[str, list] = {}
    for slot in SLOTS:
        value = data.get(slot, [])
        if not isinstance(value, list):
            raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error")
        out[slot] = value
    return out


_TOKEN = re.compile(r"^H\d+$", re.IGNORECASE)


def _number_key(record) -> tuple[int, int]:
    return (record.number is None, record.number or 0)


def resolve_suggestions(parsed: Mapping[str, list], token_map: Mapping[str, Any],
                        eligible: Sequence[Any], candidates: Candidates) -> dict[str, list]:
    """Each slot's answer as records, in AI order, without repeats. "H12" (any
    case) is a candidate token; any other string counts only on an exact
    normalized-title match within `eligible` (no substring or fuzzy match),
    preferring that slot's candidates, then the lowest number. Unknown values
    are dropped. Nothing resolved in any slot is UpstreamError."""
    by_title: dict[str, list] = {}
    for record in eligible:
        by_title.setdefault(normalize_title(record.title), []).append(record)
    resolved: dict[str, list] = {}
    for slot in SLOTS:
        in_slot = {r.id for r in candidates.by_slot.get(slot, [])}
        out: list = []
        for value in parsed.get(slot, []):
            if not isinstance(value, str) or not value.strip():
                continue
            text = value.strip()
            if _TOKEN.match(text):
                record = token_map.get(text.upper())
            else:
                matches = by_title.get(normalize_title(text), [])
                record = min(matches, key=lambda r: (r.id not in in_slot, *_number_key(r)),
                             default=None)
            if record is not None and all(r.id != record.id for r in out):
                out.append(record)
        resolved[slot] = out
    if not any(resolved.values()):
        raise UpstreamError(UNUSABLE_MESSAGE, code="ai_upstream_error")
    return resolved


@dataclass(frozen=True)
class Suggested:
    record: Any
    source: str                         # "ai", or "candidates" when added by the minimum top-up


def finalize_slots(resolved: Mapping[str, list], current_picks: Mapping[str, Optional[uuid.UUID]],
                   candidates: Candidates) -> dict[str, list[Suggested]]:
    """S Backend 3.6 step 9 (owner decision 3; owner answer Q1: only empty
    slots get a top pick). Top picks are distinct and never another slot's
    current pick; each slot then lists its AI hymns and, when that leaves
    fewer than MIN_PER_SLOT hymns other than its own pick, the next hymns of
    its own candidate list; at most MAX_PER_SLOT."""
    reserved = {pick for pick in current_picks.values() if pick is not None}
    tops: dict[str, Optional[Suggested]] = {}
    for slot in SLOTS:
        tops[slot] = None
        if current_picks.get(slot) is not None:
            continue
        top = next((Suggested(r, "ai") for r in resolved.get(slot, []) if r.id not in reserved), None)
        if top is None:
            top = next((Suggested(r, "candidates") for r in candidates.by_slot.get(slot, [])
                        if r.id not in reserved), None)
        if top is not None:
            tops[slot] = top
            reserved.add(top.record.id)
    final: dict[str, list[Suggested]] = {}
    for slot in SLOTS:
        own = current_picks.get(slot)
        top = tops[slot]
        blocked = reserved - {own, top.record.id if top else None}
        listed: list[Suggested] = [top] if top else []
        seen = {s.record.id for s in listed}
        for record in resolved.get(slot, []):
            if record.id not in blocked and record.id not in seen:
                listed.append(Suggested(record, "ai"))
                seen.add(record.id)
        for record in candidates.by_slot.get(slot, []):
            if sum(1 for s in listed if s.record.id != own) >= MIN_PER_SLOT:
                break
            if record.id not in blocked and record.id not in seen:
                listed.append(Suggested(record, "candidates"))
                seen.add(record.id)
        final[slot] = listed[:MAX_PER_SLOT]
    return final
