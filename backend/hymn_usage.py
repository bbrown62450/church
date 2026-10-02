#!/usr/bin/env python3
"""Database-backed, church-scoped hymn-usage tracking.

Drives the "exclude hymns used in the last 12 weeks" filter. All reads and
writes are scoped to a validated `church_id`; writes are idempotent per
(church_id, date_iso, hymn_number, hymn_title) so re-preparing a bulletin
never inflates the exclusion set.

Slice 5a-2: rebuild_usage_for_date replaces one date's rows with the hymns
of every service saved for that date; saving, re-dating and deleting a
service call it in their own transaction (owner answers 6, 2026-10-01).
record_usage stays for the frozen Streamlit branch's tests (slice 7).
"""
import logging
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import HymnUsage, Service
from db.upsert import insert_ignore
from hymn_search import usage_key
from service_output import normalize_date_iso, stored_hymn_entries

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


# --- slice 5a-2: hymn use follows the saved services (owner answer 6, 2026-10-01) ---------

def rebuild_usage_for_date(church_id, date_iso: str, *, session: Session) -> int:
    """Replace the church's hymn_usage rows for `date_iso` with the hymns of
    every service saved for that date (their union), in the caller's
    transaction; return the number of rows written. "Rows for the date" are
    those whose date_iso starts with it, so an imported row with a time part
    ("2026-10-04T00:00:00.000Z") goes too; a LIKE prefix is safe because
    date_iso is a validated YYYY-MM-DD (no wildcard can reach it).

    Saving a service rebuilds its date, and deleting one (or moving it to
    another date) rebuilds the date it leaves, so a date's rows always equal
    what the archive holds for it: a second service on the same date keeps
    its hymns, and rows nothing saved backs (frozen Streamlit's Prepare,
    imported history) go when that date is rebuilt (owner answer 6: Streamlit
    is retired). Hymns are deduped by hymn_search.usage_key (the title alone,
    as the 12-week window reads them); the first saved service's number and
    title are kept. Stored rows are read with service_output's tolerant
    parser, so a malformed legacy row is skipped, never raised on.

    `date_iso` must be a YYYY-MM-DD date (ValueError otherwise: a caller's
    bug), so the select can never gather undated services. On Postgres a
    transaction-level advisory lock per (church, date) makes a second save on
    the same date wait for the first to commit; its select then sees the
    first service, so the union is complete, and the rows go in sorted order,
    so two rebuilds never deadlock.
    """
    if not isinstance(date_iso, str) or normalize_date_iso(date_iso) != date_iso:
        raise ValueError(f"rebuild_usage_for_date needs a YYYY-MM-DD date, not {date_iso!r}")
    cid = as_uuid(church_id)
    if session.get_bind().dialect.name == "postgresql":
        session.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                        {"lock_key": f"hymn_usage:{cid}:{date_iso}"})
    rows = session.execute(
        select(Service.service_date_iso, Service.hymns)
        .where(Service.church_id == cid, Service.service_date_iso.like(f"{date_iso}%"))
        .order_by(Service.saved_at, Service.id)
    ).all()
    first_seen: Dict[str, Tuple[Optional[int], str]] = {}
    for stored_date, hymns in rows:
        if normalize_date_iso(stored_date) != date_iso:
            continue
        for entry in stored_hymn_entries(hymns):
            key = usage_key(entry.title) if entry is not None else ""
            if key and key not in first_seen:
                first_seen[key] = (entry.number, entry.title)
    session.execute(delete(HymnUsage).where(HymnUsage.church_id == cid, HymnUsage.date_iso.like(f"{date_iso}%")))
    values = [{"church_id": cid, "date_iso": date_iso, "hymn_number": number, "hymn_title": title}
              for _key, (number, title) in sorted(first_seen.items())]
    if values:
        session.execute(insert_ignore(HymnUsage.__table__).on_conflict_do_nothing(), values)
    return len(values)
