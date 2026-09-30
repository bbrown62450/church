"""Per-church hymn repository (database-backed, church-scoped, IDOR-safe).

Public hymn dicts use the flat Notion-property key shape so existing helpers
(hymn_utils.get_property_value, worship_service.*) consume them unchanged.
"""
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import case, delete, func, insert, or_, select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Hymn, HymnCatalog
from domain_errors import NotFound


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _hymn_to_dict(h: Hymn) -> Dict[str, Any]:
    """Map a Hymn row to the flat Notion-key dict the app consumes."""
    return {
        "id": str(h.id),
        "Hymnal": h.hymnal,
        "Hymn Title": h.title,
        "Hymn Number": h.number,
        "Scripture References": h.scripture_refs,
        "Theme": h.theme,
        "Hymnary.org Link": h.hymnary_link,
        "Audio": h.audio_url,
        "Text Year": h.text_year,
        "Hymnal Count": h.hymnal_count,
    }


def list_hymns(church_id, hymnal: Optional[str] = None) -> List[Dict[str, Any]]:
    """Hymns for a church (optionally one hymnal), ordered by number then title."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        stmt = select(Hymn).where(Hymn.church_id == cid)
        if hymnal:
            stmt = stmt.where(Hymn.hymnal == hymnal)
        rows = session.execute(stmt.order_by(Hymn.number, Hymn.title)).scalars().all()
        return [_hymn_to_dict(h) for h in rows]


def list_church_hymnals(church_id) -> List[str]:
    """Distinct hymnal names present in a church's hymnal, ordered."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = session.execute(
            select(Hymn.hymnal).where(Hymn.church_id == cid).distinct()
        ).scalars().all()
        return sorted(h for h in rows if h)


def add_hymn(
    church_id,
    *,
    title: str,
    number: Optional[int] = None,
    scripture_refs: Optional[str] = None,
    theme: Optional[str] = None,
    hymnary_link: Optional[str] = None,
    audio_url: Optional[str] = None,
    hymnal: str = "GG2013",
) -> Dict[str, Any]:
    """Insert a hymn for a church. Returns the flat-key dict (with new id)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        h = Hymn(
            church_id=cid,
            hymnal=hymnal,
            title=title,
            number=number,
            scripture_refs=scripture_refs,
            theme=theme,
            hymnary_link=hymnary_link,
            audio_url=audio_url,
        )
        session.add(h)
        session.flush()
        return _hymn_to_dict(h)


def import_hymns(church_id, hymnal: str, rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """Bulk-load a hymnal into a church. Idempotent per (church_id, hymnal, number,
    normalized title): re-running updates enrichment on matched rows instead of
    duplicating. `rows` keys: number, title (required), scripture_refs, theme,
    hymnary_link."""
    cid = _as_uuid(church_id)
    inserted = updated = 0
    with session_scope() as session:
        existing = session.execute(
            select(Hymn).where(Hymn.church_id == cid, Hymn.hymnal == hymnal)
        ).scalars().all()
        by_key = {(h.number, (h.title or "").strip().lower()): h for h in existing}
        for r in rows:
            title = (r.get("title") or "").strip()
            if not title:
                continue
            number = r.get("number")
            try:
                number = int(number) if number not in (None, "") else None
            except (TypeError, ValueError):
                number = None
            key = (number, title.lower())
            match = by_key.get(key)
            fields = dict(
                scripture_refs=r.get("scripture_refs") or None,
                theme=r.get("theme") or None,
                hymnary_link=r.get("hymnary_link") or None,
            )
            if match is None:
                h = Hymn(church_id=cid, hymnal=hymnal, title=title, number=number, **fields)
                session.add(h)
                session.flush()
                by_key[key] = h
                inserted += 1
            else:
                # only fill in enrichment we now have (don't wipe existing with blanks)
                changed = False
                for attr, val in fields.items():
                    if val and getattr(match, attr) != val:
                        setattr(match, attr, val)
                        changed = True
                if changed:
                    updated += 1
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}


def update_hymn(
    hymn_id,
    church_id,
    *,
    title: str,
    number: Optional[int] = None,
    scripture_refs: Optional[str] = None,
    theme: Optional[str] = None,
    hymnary_link: Optional[str] = None,
    audio_url: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update a hymn only if it belongs to `church_id`. Cross-church -> None."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        h = session.execute(
            select(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid)
        ).scalar_one_or_none()
        if h is None:
            return None
        h.title = title
        h.number = number
        h.scripture_refs = scripture_refs
        h.theme = theme
        h.hymnary_link = hymnary_link
        h.audio_url = audio_url
        session.flush()
        return _hymn_to_dict(h)


def delete_hymn(hymn_id, church_id) -> bool:
    """Delete a hymn only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid)
        )
        return result.rowcount > 0


def seed_church_from_catalog(church_id, session: Session) -> int:
    """CANONICAL seed: copy every hymn_catalog row into a church's hymns.

    One Core INSERT over the hymns table with a fresh id per row, in the
    caller-supplied session (part of create_church's transaction); does NOT
    commit. No Hymn object is built per row, and every row carries the same
    keys, None included, so the whole list is one executemany (psycopg2
    batches it with insertmanyvalues). The ORM form, insert(Hymn), leaves out
    None values and splits the rows into one statement per null pattern.
    An empty catalog inserts nothing: an empty parameter list would insert
    one all-defaults row. Returns the number of hymns seeded.
    """
    cid = _as_uuid(church_id)
    catalog = session.execute(
        select(
            HymnCatalog.hymnal,
            HymnCatalog.title,
            HymnCatalog.number,
            HymnCatalog.scripture_refs,
            HymnCatalog.theme,
            HymnCatalog.hymnary_link,
            HymnCatalog.audio_url,
            HymnCatalog.text_year,
            HymnCatalog.hymnal_count,
        )
    ).all()
    rows = [
        {
            "id": uuid.uuid4(),
            "church_id": cid,
            "hymnal": c.hymnal,
            "title": c.title,
            "number": c.number,
            "scripture_refs": c.scripture_refs,
            "theme": c.theme,
            "hymnary_link": c.hymnary_link,
            "audio_url": c.audio_url,
            "text_year": c.text_year,
            "hymnal_count": c.hymnal_count,
        }
        for c in catalog
    ]
    if rows:
        session.execute(insert(Hymn.__table__), rows)
    return len(rows)


# --- slice 3a: typed reads for the new app (S Backend 1 "repos/hymns.py") ----------
# Church-scoped, ids through db.ids.as_uuid (F §2.2 item 5), each in the
# caller's session or its own. list_hymns and list_church_hymnals above stay
# for the CLI and frozen Streamlit.


@dataclass(frozen=True)
class HymnRecord:
    id: uuid.UUID
    hymnal: str
    title: Optional[str]
    number: Optional[int]
    link: Optional[str]
    scripture_refs: Optional[str]
    theme: Optional[str]
    text_year: Optional[int]
    hymnal_count: Optional[int]


@dataclass(frozen=True)
class HymnalSummary:
    code: str
    hymn_count: int
    scripture_ref_count: int      # hymns whose scripture_refs is not blank


_RECORD_COLUMNS = (Hymn.id, Hymn.hymnal, Hymn.title, Hymn.number, Hymn.hymnary_link,
                   Hymn.scripture_refs, Hymn.theme, Hymn.text_year, Hymn.hymnal_count)

# hymnal, number (NULLs last on SQLite and Postgres alike), title, id (F §1.4).
_ORDER = (Hymn.hymnal.asc(), Hymn.number.asc().nulls_last(),
          func.lower(func.coalesce(Hymn.title, "")).asc(), Hymn.id.asc())


def _record(row) -> HymnRecord:
    return HymnRecord(id=row.id, hymnal=row.hymnal, title=row.title, number=row.number,
                      link=row.hymnary_link, scripture_refs=row.scripture_refs, theme=row.theme,
                      text_year=row.text_year, hymnal_count=row.hymnal_count)


def _in(session: Optional[Session], work):
    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


def hymnal_summaries(church_id, *, session: Optional[Session] = None) -> list[HymnalSummary]:
    """Each hymnal code in the church (blank codes left out), in codepoint order.

    Sorted in Python, as Streamlit's sorted(), so the effective-hymnal fallback
    agrees on Postgres, whose collation may not order by codepoint (owner
    decision 1); SQLite has no "C" collation to ask for."""
    cid = as_uuid(church_id)
    has_refs = case((func.trim(func.coalesce(Hymn.scripture_refs, "")) != "", 1), else_=0)

    def work(s: Session) -> list[HymnalSummary]:
        rows = s.execute(
            select(Hymn.hymnal, func.count(), func.coalesce(func.sum(has_refs), 0))
            .where(Hymn.church_id == cid, Hymn.hymnal != "")
            .group_by(Hymn.hymnal)
        ).all()
        return sorted((HymnalSummary(code, int(count), int(refs)) for code, count, refs in rows),
                      key=lambda summary: summary.code)

    return _in(session, work)


def query_hymns(church_id, *, hymnal: Optional[str] = None, q: Optional[str] = None,
                limit: int = 50, offset: int = 0,
                session: Optional[Session] = None) -> tuple[list[HymnRecord], int]:
    """One page of the church's hymns and the total matching the filter.

    `hymnal` filters exactly. `q` (trimmed; empty = no filter) of 1-6 digits
    also matches `number`; otherwise, and always as well, lower(title)
    contains lower(q), with % and _ escaped. Blank titles are included.
    """
    cid = as_uuid(church_id)
    conditions = [Hymn.church_id == cid]
    if hymnal is not None:
        conditions.append(Hymn.hymnal == hymnal)
    text = (q or "").strip()
    if text:
        title_match = func.lower(Hymn.title).contains(text.lower(), autoescape=True)
        # ASCII digits only: "²" and Arabic-Indic digits pass isdigit() (owner decision 1).
        if text.isascii() and text.isdigit() and len(text) <= 6:   # 7+ could overflow an integer bind
            conditions.append(or_(Hymn.number == int(text), title_match))
        else:
            conditions.append(title_match)

    def work(s: Session) -> tuple[list[HymnRecord], int]:
        total = s.execute(select(func.count()).select_from(Hymn).where(*conditions)).scalar_one()
        rows = s.execute(select(*_RECORD_COLUMNS).where(*conditions)
                         .order_by(*_ORDER).limit(limit).offset(offset)).all()
        return [_record(r) for r in rows], int(total)

    return _in(session, work)


def list_hymnal_records(church_id, hymnal: str, *,
                        session: Optional[Session] = None) -> list[HymnRecord]:
    """Every hymn of one hymnal of the church, in hymnal order."""
    cid = as_uuid(church_id)

    def work(s: Session) -> list[HymnRecord]:
        rows = s.execute(select(*_RECORD_COLUMNS)
                         .where(Hymn.church_id == cid, Hymn.hymnal == hymnal)
                         .order_by(*_ORDER)).all()
        return [_record(r) for r in rows]

    return _in(session, work)


def get_hymns_by_ids(church_id, ids, *, session: Optional[Session] = None) -> dict[uuid.UUID, HymnRecord]:
    """The church's hymns among `ids`, keyed by id, in one SELECT (slice 4:
    a liturgy request's slot picks). An id of another church, a deleted hymn or
    a malformed id is simply absent; the caller decides what that means."""
    cid = as_uuid(church_id)
    wanted = set()
    for value in ids:
        try:
            wanted.add(as_uuid(value))
        except NotFound:
            continue
    if not wanted:
        return {}

    def work(s: Session) -> dict[uuid.UUID, HymnRecord]:
        rows = s.execute(select(*_RECORD_COLUMNS)
                         .where(Hymn.church_id == cid, Hymn.id.in_(sorted(wanted)))).all()
        return {row.id: _record(row) for row in rows}

    return _in(session, work)
