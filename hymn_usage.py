#!/usr/bin/env python3
"""
Track which hymns were used on which dates and exclude recently used hymns
(e.g. last 12 weeks) from selection.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

# Store in project data dir so it persists and can be committed if desired
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USAGE_FILE = os.path.join(DATA_DIR, "hymn_usage.json")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse common date strings to YYYY-MM-DD. Returns None if unparseable."""
    s = (date_str or "").strip()
    if not s:
        return None
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y", "%d %B %Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _load_log() -> List[Dict[str, Any]]:
    _ensure_data_dir()
    if not os.path.isfile(USAGE_FILE):
        return []
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_log(entries: List[Dict[str, Any]]) -> None:
    _ensure_data_dir()
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def _hymn_key(number: Optional[int], title: str) -> Tuple[Optional[int], str]:
    """Normalized (number, title_lower) for matching."""
    t = (title or "").strip().lower()
    return (number, t)


def get_recently_used_identifiers(weeks: int = 12) -> Set[Tuple[Optional[int], str]]:
    """
    Return a set of (number, title_lower) for every hymn used in the last `weeks` weeks.
    Use this to filter the hymn list: exclude any hymn whose (number, title.lower()) is in this set.
    """
    cutoff = datetime.now().date() - timedelta(weeks=weeks)
    log = _load_log()
    out = set()
    for entry in log:
        date_str = entry.get("date")
        if not date_str:
            continue
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if entry_date < cutoff:
            continue
        for h in entry.get("hymns", []):
            num = h.get("number")
            if num is not None and not isinstance(num, int):
                try:
                    num = int(num)
                except (TypeError, ValueError):
                    num = None
            title = (h.get("title") or "").strip()
            out.add(_hymn_key(num, title))
    return out


def record_usage(date_str: str, hymns: List[Dict[str, Any]]) -> bool:
    """
    Append a service to the usage log. `date_str` can be e.g. "February 15, 2026".
    `hymns` is a list of dicts with "title" and optionally "number" (e.g. from hymn_display_info).
    Returns True if recorded, False if date could not be parsed.
    """
    iso = _parse_date_to_iso(date_str)
    if not iso:
        return False
    payload = []
    for h in hymns:
        title = h.get("title") or ""
        if not title:
            continue
        num = h.get("number")
        if num is not None and not isinstance(num, int):
            try:
                num = int(num)
            except (TypeError, ValueError):
                num = None
        payload.append({"number": num, "title": title})
    if not payload:
        return True
    log = _load_log()
    log.append({"date": iso, "hymns": payload})
    _save_log(log)
    return True


def is_hymn_recently_used(
    number: Optional[int],
    title: str,
    recent_set: Set[Tuple[Optional[int], str]],
) -> bool:
    """True if this hymn (number, title) is in the recent-usage set."""
    return _hymn_key(number, (title or "").strip()) in recent_set
