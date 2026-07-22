"""Per-church hymn repository.

seed_church_from_catalog is implemented here (needed by repos.churches.create_church).
The read/CRUD surface (list_hymns, add_hymn, update_hymn, delete_hymn) and the
hymn_utils flat-dict change are added in Task 9.
"""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Hymn, HymnCatalog


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


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
