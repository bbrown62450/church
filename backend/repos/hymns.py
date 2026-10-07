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
from hymn_search import normalize_title


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


def title_key(title: Optional[str]) -> str:
    """A title as the duplicate rule compares it: every run of whitespace one
    space (tabs, line breaks and no-break spaces included), trimmed, lower-cased."""
    return " ".join((title or "").split()).lower()


# What an import may fill in on a hymn it already has (never what makes it the same hymn).
_ENRICHMENT = ("scripture_refs", "theme", "hymnary_link", "audio_url", "text_year", "hymnal_count")


def import_hymns(church_id, hymnal: str, rows: List[Dict[str, Any]], *,
                 session: Optional[Session] = None) -> Dict[str, int]:
    """Bulk-load a hymnal into a church. Idempotent per (church_id, hymnal,
    number, title_key(title)): a row the church already has is not added
    again, and only its blank enrichment is filled in (a value an admin or
    member entered is kept; 6a spec, POST /hymnals). Never deletes. `rows`
    keys: number, title (required), scripture_refs, theme, hymnary_link, and
    optionally audio_url, text_year, hymnal_count.

    The new rows are flushed together at the end (no flush per row), so
    SQLAlchemy sends them as one batched INSERT (6a spec Risk 5)."""
    cid = _as_uuid(church_id)

    def work(s: Session) -> Dict[str, int]:
        inserted = updated = 0
        existing = s.execute(
            select(Hymn).where(Hymn.church_id == cid, Hymn.hymnal == hymnal)
        ).scalars().all()
        by_key = {(h.number, title_key(h.title)): h for h in existing}
        for r in rows:
            title = " ".join((r.get("title") or "").split())
            if not title:
                continue
            number = r.get("number")
            try:
                number = int(number) if number not in (None, "") else None
            except (TypeError, ValueError):
                number = None
            key = (number, title_key(title))
            match = by_key.get(key)
            fields = {attr: r.get(attr) for attr in _ENRICHMENT if r.get(attr) not in (None, "")}
            if match is None:
                h = Hymn(church_id=cid, hymnal=hymnal, title=title, number=number, **fields)
                s.add(h)
                by_key[key] = h
                inserted += 1
            else:
                blank = {attr: value for attr, value in fields.items()
                         if getattr(match, attr) is None or (isinstance(getattr(match, attr), str)
                                                             and not getattr(match, attr).strip())}
                for attr, value in blank.items():
                    setattr(match, attr, value)
                if blank:
                    updated += 1
        s.flush()
        return {"inserted": inserted, "updated": updated, "total": inserted + updated}

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


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


def delete_hymn(hymn_id, church_id, *, session: Optional[Session] = None) -> bool:
    """Delete a hymn only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)

    def work(s: Session) -> bool:
        result = s.execute(delete(Hymn).where(Hymn.id == _as_uuid(hymn_id), Hymn.church_id == cid))
        return result.rowcount > 0

    if session is not None:
        return work(session)
    with session_scope() as own:
        return work(own)


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


def find_hymns_by_titles(church_id, title_keys, *, session: Optional[Session] = None) -> list[HymnRecord]:
    """The church's hymns whose hymn_search.normalize_title(title) is in
    `title_keys`, ordered by hymnal, number (nulls last), id (slice 5a-2:
    opening a saved service whose hymn has no id that still resolves). The
    filter runs in Python, because SQL cannot collapse whitespace the same way
    on SQLite and Postgres; a church has a few thousand hymns at most, and the
    caller asks only when some slot needs it."""
    wanted = {key for key in title_keys if key}
    if not wanted:
        return []
    cid = as_uuid(church_id)

    def work(s: Session) -> list[HymnRecord]:
        rows = s.execute(select(*_RECORD_COLUMNS).where(Hymn.church_id == cid)
                         .order_by(Hymn.hymnal.asc(), Hymn.number.asc().nulls_last(), Hymn.id.asc())).all()
        return [_record(row) for row in rows if normalize_title(row.title) in wanted]

    return _in(session, work)


# --- slice 6a-2: the hymn library's writes (6a spec, `repos/hymns.py`) --------------
# Each runs in the caller's session (usecases.hymn_library, under the
# church-row lock) or its own; every one is church-scoped.

# The columns a hymn write may set: HymnRecord's names, `link` for hymnary_link.
_WRITABLE = {"title": Hymn.title, "number": Hymn.number, "hymnal": Hymn.hymnal,
             "scripture_refs": Hymn.scripture_refs, "theme": Hymn.theme, "link": Hymn.hymnary_link,
             "text_year": Hymn.text_year, "hymnal_count": Hymn.hymnal_count}


def _attr(name: str) -> str:
    return _WRITABLE[name].key


def get_hymn(hymn_id, church_id, *, session: Optional[Session] = None) -> Optional[HymnRecord]:
    """The church's hymn, or None (another church's id, a deleted hymn)."""
    hid, cid = as_uuid(hymn_id), as_uuid(church_id)

    def work(s: Session) -> Optional[HymnRecord]:
        row = s.execute(select(*_RECORD_COLUMNS).where(Hymn.id == hid, Hymn.church_id == cid)).first()
        return _record(row) if row is not None else None

    return _in(session, work)


def create_hymn(church_id, values: Dict[str, Any], *, session: Optional[Session] = None) -> HymnRecord:
    """Insert a hymn from `values` (keys of _WRITABLE, already cleaned) and return it."""
    cid = as_uuid(church_id)

    def work(s: Session) -> HymnRecord:
        h = Hymn(church_id=cid, **{_attr(name): value for name, value in values.items()})
        s.add(h)
        s.flush()
        return get_hymn(h.id, cid, session=s)

    return _in(session, work)


def patch_hymn(hymn_id, church_id, changes: Dict[str, Any], *,
               session: Optional[Session] = None) -> Optional[HymnRecord]:
    """Set only the keys in `changes` (keys of _WRITABLE, already cleaned);
    every other column, audio_url among them, is kept. None when the church
    has no such hymn."""
    hid, cid = as_uuid(hymn_id), as_uuid(church_id)

    def work(s: Session) -> Optional[HymnRecord]:
        h = s.execute(select(Hymn).where(Hymn.id == hid, Hymn.church_id == cid)).scalar_one_or_none()
        if h is None:
            return None
        for name, value in changes.items():
            setattr(h, _attr(name), value)
        s.flush()
        return get_hymn(hid, cid, session=s)

    return _in(session, work)


def find_duplicate(church_id, hymnal: str, number: Optional[int], title: str, *, exclude_id=None,
                   session: Optional[Session] = None) -> bool:
    """True when the church already has a hymn in `hymnal` with this number
    (or, for None, with no number) whose title_key equals title_key(title),
    other than `exclude_id`. The titles are compared in Python, because SQL's
    trim and lower do not treat tabs, line breaks or every letter the same way
    on SQLite and Postgres (the import uses the same key)."""
    cid = as_uuid(church_id)
    wanted = title_key(title)
    conditions = [Hymn.church_id == cid, Hymn.hymnal == hymnal,
                  Hymn.number.is_(None) if number is None else Hymn.number == number]
    if exclude_id is not None:
        conditions.append(Hymn.id != as_uuid(exclude_id))

    def work(s: Session) -> bool:
        titles = s.execute(select(Hymn.title).where(*conditions)).scalars().all()
        return any(title_key(t) == wanted for t in titles)

    return _in(session, work)


def delete_hymnal(church_id, hymnal: str, *, session: Optional[Session] = None) -> int:
    """Delete every hymn of the church in `hymnal`; the number deleted."""
    cid = as_uuid(church_id)

    def work(s: Session) -> int:
        return s.execute(delete(Hymn).where(Hymn.church_id == cid, Hymn.hymnal == hymnal)).rowcount

    return _in(session, work)
