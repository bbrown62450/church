"""Per-church hymn repository (database-backed, church-scoped, IDOR-safe).

Public hymn dicts use the flat Notion-property key shape so existing helpers
(hymn_utils.get_property_value, worship_service.*) consume them unchanged.
"""
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db import session_scope
from db.models import Hymn, HymnCatalog


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _hymn_to_dict(h: Hymn) -> Dict[str, Any]:
    """Map a Hymn row to the flat Notion-key dict the app consumes."""
    return {
        "id": str(h.id),
        "Hymn Title": h.title,
        "Hymn Number": h.number,
        "Scripture References": h.scripture_refs,
        "Theme": h.theme,
        "Hymnary.org Link": h.hymnary_link,
        "Audio": h.audio_url,
    }


def list_hymns(church_id) -> List[Dict[str, Any]]:
    """All hymns for a church, ordered by number then title. Flat-key dicts."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Hymn)
                .where(Hymn.church_id == cid)
                .order_by(Hymn.number, Hymn.title)
            )
            .scalars()
            .all()
        )
        return [_hymn_to_dict(h) for h in rows]


def add_hymn(
    church_id,
    *,
    title: str,
    number: Optional[int] = None,
    scripture_refs: Optional[str] = None,
    theme: Optional[str] = None,
    hymnary_link: Optional[str] = None,
    audio_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Insert a hymn for a church. Returns the flat-key dict (with new id)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        h = Hymn(
            church_id=cid,
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

    Uses the caller-supplied session (part of create_church's transaction) and
    does NOT commit. Returns the number of hymns seeded.
    """
    cid = _as_uuid(church_id)
    rows = session.execute(select(HymnCatalog)).scalars().all()
    count = 0
    for c in rows:
        session.add(
            Hymn(
                church_id=cid,
                title=c.title,
                number=c.number,
                scripture_refs=c.scripture_refs,
                theme=c.theme,
                hymnary_link=c.hymnary_link,
                audio_url=c.audio_url,
            )
        )
        count += 1
    session.flush()
    return count
