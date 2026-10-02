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

Slice 5a-2 adds the archive (owner answers 4 and 6, 2026-10-01), each in one
transaction:
- create_service and replace_service: clean the input, resolve the hymns,
  write the row (3 slot entries, the display date, only the 8 sections, the
  custom elements, the hymnal: the church's effective hymnal when none is
  sent), then rebuild the date's hymn use. replace_service first locks the
  row and checks If-Match against saved_at (404, then 422, then 409, then
  the input's own errors); a PUT that moves a service to another date
  rebuilds both dates. What is sent is what is stored: a Benediction that
  followed the church default and the communion setting are kept as saved.
- get_service: the stored row normalized for the builder (hymns by slot,
  resolved by id, else by title and number; only the 8 sections without
  Streamlit's error texts; custom elements kept with an unknown place read
  as "end"; the date through normalize_date_iso).
- list_services: one page, newest service date first, undated last.
- delete_service: removes the row and rebuilds that date's hymn use from the
  services still saved for it (owner answer 6); an undated service changes
  no hymn use.

No FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).
"""
from __future__ import annotations

import datetime
import logging
import re
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Optional

from db import session_scope
from db.ids import as_uuid
from domain_errors import Conflict, InvalidInput, NotFound
from hymn_search import normalize_title
from hymn_usage import rebuild_usage_for_date
from liturgy_config import SECTION_ORDER, normalize_placement
from repos import hymns as hymn_repo
from repos import services as services_repo
from service_output import (SLOTS, CustomElement, ResolvedHymn, is_legacy_error_placeholder, normalize_date_iso,
                            service_date_display, slot_map, stored_hymns)
from usecases.hymns import resolve_default_hymnal
from usecases.liturgy import HYMN_GONE_MESSAGE, HymnRefData

logger = logging.getLogger(__name__)

CUSTOM_LABEL_MESSAGE = "Give each custom element a label."

# What XML 1.0 cannot hold, after a vertical tab or form feed becomes a line
# break: the other C0 controls (tab, newline and carriage return are allowed),
# U+FFFE, U+FFFF and lone surrogates. python-docx raises on them (a 500).
_XML_BAD = re.compile("[\x00-\x08\x0e-\x1f\ufffe\uffff\ud800-\udfff]")


def _xml_safe(s: str) -> str:
    """s as a Word file can hold it: a Windows or old-Mac line ending ("\\r\\n",
    "\\r") becomes one line break first (python-docx would print a carriage
    return as a second break; build review fix 1), a vertical tab (Word's soft
    line break, pasted) or a form feed becomes a line break, the rest of
    _XML_BAD goes."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
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


# --- slice 5a-2: saving, listing, opening and deleting services (5a spec, Backend "usecases/archive.py") ---

SERVICE_GONE_MESSAGE = "That service is no longer in the archive."
CONFLICT_MESSAGE = "This service was changed by someone else. Reload it to see their changes."
IF_MATCH_REQUIRED_MESSAGE = "If-Match is required."
IF_MATCH_INVALID_MESSAGE = "If-Match must be the service's saved_at timestamp."


@dataclass(frozen=True)
class Author:
    id: uuid.UUID
    name: str                                   # the member's name, else their email (owner decision 5)


@dataclass(frozen=True)
class ArchivedHymnData:
    hymn_id: Optional[uuid.UUID]
    title: str
    number: Optional[int]
    hymnal: Optional[str]
    in_hymnal: bool                             # the hymn is in the church's hymnal now


@dataclass(frozen=True)
class ServiceRecord:
    id: uuid.UUID
    service_date_iso: Optional[str]             # normalize_date_iso; None for an undated legacy row
    service_date: str                           # the stored display date ("October 04, 2026")
    occasion: str
    scriptures: list[str]
    hymns: dict[str, Optional[ArchivedHymnData]]
    hymnal: Optional[str]
    liturgy: dict[str, str]
    sermon_title: str
    selected_ot_ref: str
    selected_nt_ref: str
    include_communion: bool
    custom_elements: list[CustomElement]
    created_by: Optional[Author]
    saved_at: str                               # ISO 8601 in UTC, "+00:00"


@dataclass(frozen=True)
class ServiceSummaryData:
    id: uuid.UUID
    service_date_iso: Optional[str]
    service_date: str
    occasion: str
    sermon_title: str
    saved_at: str
    created_by: Optional[Author]


@dataclass(frozen=True)
class ServicePageData:
    items: list[ServiceSummaryData]
    total: int
    limit: int
    offset: int


def _utc(value: datetime.datetime) -> datetime.datetime:
    """A naive value (SQLite) is UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=datetime.timezone.utc)
    return value.astimezone(datetime.timezone.utc)


def saved_at_text(value: datetime.datetime) -> str:
    return _utc(value).isoformat()


def parse_if_match(value: Optional[str]) -> datetime.datetime:
    """The saved_at an If-Match header carries, in UTC: surrounding quotes and a
    W/ prefix are ignored; missing or blank is 422 "If-Match is required.",
    anything else that is not an ISO 8601 timestamp is 422 "If-Match must be
    the service's saved_at timestamp."."""
    if value is None or not value.strip():
        raise InvalidInput(IF_MATCH_REQUIRED_MESSAGE)
    text = value.strip()
    if text.startswith("W/"):
        text = text[2:].strip()
    text = text.strip('"').strip()
    try:
        return _utc(datetime.datetime.fromisoformat(text))
    except ValueError:
        raise InvalidInput(IF_MATCH_INVALID_MESSAGE) from None


def _author(user_id, name: Optional[str], email: Optional[str]) -> Optional[Author]:
    if user_id is None:
        return None
    return Author(user_id, (name or "").strip() or (email or ""))


def _fields(church_id: uuid.UUID, clean: ServiceInput, hymns: Mapping[str, Optional[ResolvedHymn]],
            session) -> dict:
    """The columns a save writes (F §6.2), saved_at included (it moves on every save)."""
    day = clean.service_date
    return {
        "service_date_iso": day.isoformat(),
        "service_date_display": service_date_display(day),
        "occasion": clean.occasion,
        "scriptures": list(clean.scriptures),
        "hymns": stored_hymns(hymns),
        # null = the hymnal the hymns step showed: the church's effective hymnal now.
        "hymnal": clean.hymnal or resolve_default_hymnal(church_id, session=session).effective_hymnal,
        "liturgy": {key: clean.liturgy[key] for key in SECTION_ORDER if key in clean.liturgy},
        "sermon_title": clean.sermon_title,
        "selected_ot_ref": clean.selected_ot_ref,
        "selected_nt_ref": clean.selected_nt_ref,
        "include_communion": clean.include_communion,
        "custom_elements": [{"label": e.label, "text": e.text, "insert_after": e.insert_after}
                            for e in clean.custom_elements],
        "saved_at": datetime.datetime.now(datetime.timezone.utc),
    }


def _hymn_from_record(record) -> ArchivedHymnData:
    return ArchivedHymnData(record.id, (record.title or "").strip(), record.number, record.hymnal, True)


def _best_match(entry, candidates, preferred: list[str]):
    """The church's hymn for a stored entry without a usable id: the same
    normalized title (and number, when the entry has one), from the first
    preferred hymnal that has it, else from the first other hymnal in code
    order; within a hymnal the lowest number (nulls last), then the lowest id,
    so the answer is the same on every run (PH1990 has 34 duplicate titles)."""
    key = normalize_title(entry.title)
    pool = [c for c in candidates
            if normalize_title(c.title) == key and (entry.number is None or c.number == entry.number)]
    if not pool:
        return None

    def rank(c):
        place = preferred.index(c.hymnal) if c.hymnal in preferred else len(preferred)
        return (place, c.hymnal, c.number is None, c.number or 0, c.id)

    return min(pool, key=rank)


def _archived_hymns(session, church_id: uuid.UUID, row) -> dict[str, Optional[ArchivedHymnData]]:
    by_slot = slot_map(row.hymns)
    ids: dict[str, uuid.UUID] = {}
    for slot, entry in by_slot.items():
        if entry is not None and entry.hymn_id is not None:
            try:
                ids[slot] = uuid.UUID(entry.hymn_id)
            except ValueError:
                pass
    found = hymn_repo.get_hymns_by_ids(church_id, list(ids.values()), session=session) if ids else {}
    result: dict[str, Optional[ArchivedHymnData]] = {}
    unmatched = {}
    for slot, entry in by_slot.items():
        record = found.get(ids.get(slot)) if entry is not None else None
        if entry is None:
            result[slot] = None
        elif record is not None and (record.title or "").strip():
            result[slot] = _hymn_from_record(record)
        else:
            unmatched[slot] = entry
    if unmatched:
        candidates = hymn_repo.find_hymns_by_titles(
            church_id, {normalize_title(e.title) for e in unmatched.values()}, session=session)
        effective = resolve_default_hymnal(church_id, session=session).effective_hymnal
        for slot, entry in unmatched.items():
            preferred = [h for h in (entry.hymnal, row.hymnal, effective) if h]
            match = _best_match(entry, candidates, preferred)
            result[slot] = (_hymn_from_record(match) if match is not None else
                            ArchivedHymnData(None, entry.title, entry.number, entry.hymnal, False))
    return {slot: result[slot] for slot in SLOTS}


def _archived_liturgy(raw) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {key: text.strip() for key in SECTION_ORDER
            if isinstance(text := raw.get(key), str) and text.strip() and not is_legacy_error_placeholder(text)}


def _archived_custom_elements(raw) -> list[CustomElement]:
    """Every stored element, in order; never dropped for its place (unknown or missing reads as "end")."""
    if not isinstance(raw, list):
        return []
    return [CustomElement(label if isinstance(label := e.get("label"), str) else "",
                          text if isinstance(text := e.get("text"), str) else "",
                          normalize_placement(e.get("insert_after")))
            for e in raw if isinstance(e, dict)]


def _record(session, church_id: uuid.UUID, row) -> ServiceRecord:
    found = services_repo.author(row.created_by, session=session)
    return ServiceRecord(
        id=row.id,
        service_date_iso=normalize_date_iso(row.service_date_iso),
        service_date=row.service_date_display or "",
        occasion=row.occasion or "",
        scriptures=[line for line in row.scriptures if isinstance(line, str)] if isinstance(row.scriptures, list) else [],
        hymns=_archived_hymns(session, church_id, row),
        hymnal=row.hymnal,
        liturgy=_archived_liturgy(row.liturgy),
        sermon_title=row.sermon_title or "",
        selected_ot_ref=row.selected_ot_ref or "",
        selected_nt_ref=row.selected_nt_ref or "",
        include_communion=bool(row.include_communion),
        custom_elements=_archived_custom_elements(row.custom_elements),
        created_by=None if found is None else _author(*found),
        saved_at=saved_at_text(row.saved_at),
    )


def _log(action: str, church_id: uuid.UUID, service_id: uuid.UUID, usage_rows: int, started: float) -> None:
    """Ids and counts only, never a service's text (F §2.5)."""
    logger.info("archive.%s church=%s service=%s usage_rows=%d ms=%d", action, church_id, service_id, usage_rows,
                round((time.monotonic() - started) * 1000))


def create_service(church_id: uuid.UUID, user_id: uuid.UUID, data: ServiceInput) -> ServiceRecord:
    """POST /services: save a new service and rebuild its date's hymn use, in one transaction."""
    started = time.monotonic()
    cid, uid = as_uuid(church_id), as_uuid(user_id)
    clean = clean_input(data)
    with session_scope() as s:
        hymns = resolve_hymn_refs(s, cid, clean.hymns)
        row = services_repo.insert_service(cid, uid, _fields(cid, clean, hymns, s), session=s)
        usage_rows = rebuild_usage_for_date(cid, row.service_date_iso, session=s)
        record = _record(s, cid, row)
    _log("create", cid, record.id, usage_rows, started)
    return record


def replace_service(church_id: uuid.UUID, service_id: uuid.UUID, data: ServiceInput, *,
                    if_match: Optional[str]) -> ServiceRecord:
    """PUT /services/{id}: the 5a spec's check order (the row, If-Match present
    and readable, If-Match equal to saved_at, the input), then a full replace
    (created_by kept, saved_at moved) and the hymn-use rebuild of the saved
    date and, when the date changed, of the date it left, in date order."""
    started = time.monotonic()
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.get_service(cid, service_id, session=s, for_update=True)
        if row is None:
            raise NotFound(SERVICE_GONE_MESSAGE)
        expected = parse_if_match(if_match)
        current = _utc(row.saved_at)
        if expected != current:
            raise Conflict(CONFLICT_MESSAGE, details={"current_saved_at": current.isoformat()})
        clean = clean_input(data)
        hymns = resolve_hymn_refs(s, cid, clean.hymns)
        old_date = normalize_date_iso(row.service_date_iso)
        services_repo.update_service(row, _fields(cid, clean, hymns, s), session=s)
        usage_rows = 0
        for date_iso in sorted({old_date, row.service_date_iso} - {None}):
            usage_rows += rebuild_usage_for_date(cid, date_iso, session=s)
        record = _record(s, cid, row)
    _log("replace", cid, record.id, usage_rows, started)
    return record


def get_service(church_id: uuid.UUID, service_id: uuid.UUID) -> ServiceRecord:
    """GET /services/{id}: the church's service, normalized (see the module docstring)."""
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.get_service(cid, service_id, session=s)
        if row is None:
            raise NotFound(SERVICE_GONE_MESSAGE)
        return _record(s, cid, row)


def list_services(church_id: uuid.UUID, *, limit: int, offset: int) -> ServicePageData:
    """GET /services: one page, newest service date first (undated last), then the latest save, then id."""
    rows, total = services_repo.list_page(as_uuid(church_id), limit=limit, offset=offset)
    items = [ServiceSummaryData(id=r.id, service_date_iso=normalize_date_iso(r.service_date_iso),
                                service_date=r.service_date_display or "", occasion=r.occasion or "",
                                sermon_title=r.sermon_title or "", saved_at=saved_at_text(r.saved_at),
                                created_by=_author(r.created_by, r.author_name, r.author_email))
             for r in rows]
    return ServicePageData(items=items, total=total, limit=limit, offset=offset)


def delete_service(church_id: uuid.UUID, service_id: uuid.UUID) -> None:
    """DELETE /services/{id}: remove the service and rebuild its date's hymn use
    from the services still saved for that date (owner answer 6), in one
    transaction. An undated service changes no hymn use."""
    started = time.monotonic()
    cid = as_uuid(church_id)
    with session_scope() as s:
        row = services_repo.get_service(cid, service_id, session=s, for_update=True)
        if row is None:
            raise NotFound(SERVICE_GONE_MESSAGE)
        deleted_id, date_iso = row.id, normalize_date_iso(row.service_date_iso)
        services_repo.delete_service(row, session=s)
        usage_rows = rebuild_usage_for_date(cid, date_iso, session=s) if date_iso else 0
    _log("delete", cid, deleted_id, usage_rows, started)
