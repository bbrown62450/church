#!/usr/bin/env python3
"""Database-backed, church-scoped hymn-usage tracking.

Drives the "exclude hymns used in the last 12 weeks" filter. All reads and
writes are scoped to a validated `church_id`; writes are idempotent per
(church_id, date_iso, hymn_number, hymn_title) so re-preparing a bulletin
never inflates the exclusion set.
"""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import HymnUsage
from hymn_search import usage_key

logger = logging.getLogger(__name__)


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse common date strings to YYYY-MM-DD. Returns None if unparseable."""
    s = (date_str or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%d %B %Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _coerce_number(num: Any) -> Optional[int]:
    if num is None or isinstance(num, int):
        return num
    try:
        return int(num)
    except (TypeError, ValueError):
        return None


def _hymn_key(number: Optional[int], title: str) -> Tuple[Optional[int], str]:
    """Normalized (number, title_lower) for matching."""
    return (number, (title or "").strip().lower())


def get_recently_used_identifiers(church_id, weeks: int = 12) -> Set[Tuple[Optional[int], str]]:
    """Set of (number, title_lower) used by THIS church in the last `weeks` weeks."""
    cid = _as_uuid(church_id)
    cutoff = (datetime.now(timezone.utc).date() - timedelta(weeks=weeks)).isoformat()
    with session_scope() as session:
        rows = session.execute(
            select(HymnUsage.hymn_number, HymnUsage.hymn_title).where(
                HymnUsage.church_id == cid,
                HymnUsage.date_iso >= cutoff,
            )
        ).all()
    return {_hymn_key(number, title) for number, title in rows}


def record_usage(church_id, date_str: str, hymns: List[Dict[str, Any]]) -> bool:
    """Record a service's hymns for a church. Idempotent per dedupe key.

    `date_str` may be e.g. "February 15, 2026" or "2026-02-15".
    Returns True if recorded (or nothing to record); False if date unparseable.
    """
    iso = _parse_date_to_iso(date_str)
    if not iso:
        return False
    cid = _as_uuid(church_id)

    payload: List[Tuple[Optional[int], str]] = []
    for h in hymns:
        title = (h.get("title") or "").strip()
        if not title:
            continue
        payload.append((_coerce_number(h.get("number")), title))
    if not payload:
        return True

    with session_scope() as session:
        existing = session.execute(
            select(HymnUsage.hymn_number, HymnUsage.hymn_title).where(
                HymnUsage.church_id == cid,
                HymnUsage.date_iso == iso,
            )
        ).all()
        seen = {(n, t) for n, t in existing}
        for num, title in payload:
            if (num, title) in seen:
                continue
            session.add(
                HymnUsage(
                    church_id=cid,
                    date_iso=iso,
                    hymn_number=num,
                    hymn_title=title,
                )
            )
            seen.add((num, title))
    return True


def is_hymn_recently_used(
    number: Optional[int],
    title: str,
    recent_set: Set[Tuple[Optional[int], str]],
) -> bool:
    """True if this hymn (number, title) is in the recent-usage set."""
    return _hymn_key(number, title) in recent_set


# --- slice 3a: the recent-use window around a service date (S Backend 3.4) --------

RECENT_WEEKS = 12


def _shifted(day: date, days: int) -> date:
    """day + days, clamped at date.min and date.max (owner decision 1)."""
    try:
        return day + timedelta(days=days)
    except OverflowError:
        return date.max if days > 0 else date.min


def usage_near(church_id, service_date: date, *, weeks: int = RECENT_WEEKS,
               session: Optional[Session] = None) -> Dict[str, date]:
    """{usage_key(title): the usage date nearest `service_date`} for the church's
    usage in [D - weeks, D + weeks], both ends inclusive, D itself excluded.

    The key is usage_key(title), the title alone with punctuation ignored
    (owner answers Q2 and A, 2026-09-29), so a hymn sung from one hymnal
    counts when it is picked from another. The window is clamped at the
    calendar's ends. Ties go
    to the earlier date. date_iso is not always YYYY-MM-DD (Notion imports
    stored "" or a datetime), so SQL keeps a deliberately wide string range and
    Python applies the exact window to date_iso[:10]; a value that still does
    not parse is skipped and counted at DEBUG. Nothing here raises on stored data.
    """
    cid = as_uuid(church_id)
    low = _shifted(service_date, -7 * weeks)
    high = _shifted(service_date, 7 * weeks)
    conditions = [HymnUsage.church_id == cid, HymnUsage.date_iso >= low.isoformat()]
    if high < date.max:                    # at date.max every later string is in range
        conditions.append(HymnUsage.date_iso < (high + timedelta(days=1)).isoformat())

    def work(s: Session):
        return s.execute(select(HymnUsage.date_iso, HymnUsage.hymn_title).where(*conditions)).all()

    if session is not None:
        rows = work(session)
    else:
        with session_scope() as own:
            rows = work(own)

    nearest: Dict[str, date] = {}
    skipped = 0
    for date_iso, title in rows:
        try:
            day = date.fromisoformat((date_iso or "")[:10])
        except ValueError:
            skipped += 1
            continue
        if not (low <= day <= high) or day == service_date:
            continue
        key = usage_key(title)
        if not key:
            continue
        best = nearest.get(key)
        distance = abs((day - service_date).days)
        if (best is None or distance < abs((best - service_date).days)
                or (distance == abs((best - service_date).days) and day < best)):
            nearest[key] = day
    if skipped:
        logger.debug("usage_near skipped %d usage rows with an unreadable date_iso", skipped)
    return nearest
