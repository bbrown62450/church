"""The service a member builds, as the domain sees it (slice 5a spec, Backend
"usecases/archive.py"). Slice 5a-1 (Word downloads) adds the parts a document
needs; 5a-2 adds saving, listing, opening and deleting services here.

- ServiceInput: the domain copy of api.schemas.ServiceDraft, built by its
  to_input() in the route (usecases never import api/*). 5b's email takes it too.
- clean_input: takes out of every string the characters a Word file cannot
  hold (_xml_safe: python-docx refuses them), then strips every string, drops
  blank scriptures, and drops liturgy that is blank or one of Streamlit's
  stored error texts; a custom element whose label is blank after that is a
  422 on that field.
- resolve_hymn_refs: each slot's hymn, its id resolved within the church in
  one query (the database's title and number win over the client's copy, F
  §1.3); an id the church does not have is a 404 naming the slot; a null id
  keeps the snapshot sent; a blank title is an empty slot (the database's
  title goes through _xml_safe too). The same hymn in two slots is allowed
  (parity).

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import datetime
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Optional

from domain_errors import InvalidInput, NotFound
from repos import hymns as hymn_repo
from service_output import SLOTS, CustomElement, ResolvedHymn, is_legacy_error_placeholder
from usecases.liturgy import HYMN_GONE_MESSAGE, HymnRefData

CUSTOM_LABEL_MESSAGE = "Give each custom element a label."

# What XML 1.0 cannot hold, after a vertical tab or form feed becomes a line
# break: the other C0 controls (tab, newline and carriage return are allowed),
# U+FFFE, U+FFFF and lone surrogates. python-docx raises on them (a 500).
_XML_BAD = re.compile("[\x00-\x08\x0e-\x1f\ufffe\uffff\ud800-\udfff]")


def _xml_safe(s: str) -> str:
    """s as a Word file can hold it: a vertical tab (Word's soft line break,
    pasted) or a form feed becomes a line break, the rest of _XML_BAD goes."""
    return _XML_BAD.sub("", s.replace("\x0b", "\n").replace("\x0c", "\n"))


@dataclass(frozen=True)
class ServiceInput:
    service_date: datetime.date
    occasion: str = ""
    scriptures: tuple[str, ...] = ()
    hymns: Mapping[str, Optional[HymnRefData]] = field(default_factory=dict)
    hymnal: Optional[str] = None               # None: the church's effective hymnal (stored by 5a-2)
    liturgy: Mapping[str, str] = field(default_factory=dict)
    sermon_title: str = ""
    selected_ot_ref: str = ""
    selected_nt_ref: str = ""
    include_communion: bool = False
    custom_elements: tuple[CustomElement, ...] = ()


def clean_input(data: ServiceInput) -> ServiceInput:
    """The input with every string made Word-safe and trimmed, and nothing blank kept (see the module docstring)."""
    def clean(text: str) -> str:
        return _xml_safe(text).strip()

    for i, element in enumerate(data.custom_elements):
        if not clean(element.label):
            raise InvalidInput(CUSTOM_LABEL_MESSAGE, field=f"custom_elements.{i}.label")
    liturgy = {key: text for key, raw in data.liturgy.items()
               if (text := clean(raw)) and not is_legacy_error_placeholder(text)}
    hymns = {slot: None if (ref := data.hymns.get(slot)) is None else replace(
        ref, title=clean(ref.title), hymnal=clean(ref.hymnal) if ref.hymnal else ref.hymnal) for slot in SLOTS}
    return replace(
        data,
        occasion=clean(data.occasion),
        scriptures=tuple(text for line in data.scriptures if (text := clean(line))),
        hymns=hymns,
        hymnal=clean(data.hymnal or "") or None,
        liturgy=liturgy,
        sermon_title=clean(data.sermon_title),
        selected_ot_ref=clean(data.selected_ot_ref),
        selected_nt_ref=clean(data.selected_nt_ref),
        custom_elements=tuple(CustomElement(clean(e.label), clean(e.text), e.insert_after)
                              for e in data.custom_elements),
    )


def resolve_hymn_refs(session, church_id: uuid.UUID,
                      hymns: Mapping[str, Optional[HymnRefData]]) -> dict[str, Optional[ResolvedHymn]]:
    """Each slot's hymn as it prints, in one SELECT for the ids (see the module docstring)."""
    ids = [ref.hymn_id for ref in hymns.values() if ref is not None and ref.hymn_id is not None]
    found = hymn_repo.get_hymns_by_ids(church_id, ids, session=session) if ids else {}
    resolved: dict[str, Optional[ResolvedHymn]] = {}
    for slot in SLOTS:
        ref = hymns.get(slot)
        if ref is None:
            resolved[slot] = None
        elif ref.hymn_id is not None:
            record = found.get(ref.hymn_id)
            if record is None:
                raise NotFound(HYMN_GONE_MESSAGE, details={"field": f"hymns.{slot}.hymn_id"})
            title = _xml_safe(record.title or "").strip()
            resolved[slot] = ResolvedHymn(title, record.number, record.id, record.hymnal) if title else None
        else:
            title = ref.title.strip()
            resolved[slot] = ResolvedHymn(title, ref.number, None, ref.hymnal) if title else None
    return resolved
