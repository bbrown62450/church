#!/usr/bin/env python3
"""
Notion-backed hymn usage (for "last 12 weeks" exclusion). When NOTION_USAGE_DATABASE_ID is set,
usage is stored in this Notion database instead of local JSON.

Required Notion database properties:
- Title (title) — e.g. "336 We Gather Together" for display
- Date (date) — service date
- Hymn number (number)
- Hymn title (rich_text)
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import httpx
except ImportError:
    httpx = None

BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _client() -> Optional[httpx.Client]:
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key or not httpx:
        return None
    return httpx.Client(
        base_url=BASE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def _db_id() -> Optional[str]:
    return os.getenv("NOTION_USAGE_DATABASE_ID") or None


def _parse_date_to_iso(date_str: str) -> Optional[str]:
    """Parse common date strings to YYYY-MM-DD."""
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


def _hymn_key(number: Optional[int], title: str) -> Tuple[Optional[int], str]:
    """Normalized (number, title_lower) for matching."""
    t = (title or "").strip().lower()
    return (number, t)


def get_recently_used_identifiers(weeks: int = 12) -> Set[Tuple[Optional[int], str]]:
    """Return set of (number, title_lower) for hymns used in the last `weeks` weeks."""
    db = _db_id()
    if not db:
        return set()
    cutoff = (datetime.now().date() - timedelta(weeks=weeks)).isoformat()
    with _client() as client:
        if not client:
            return set()
        try:
            out: Set[Tuple[Optional[int], str]] = set()
            cursor = None
            while True:
                body: Dict[str, Any] = {
                    "page_size": 100,
                    "filter": {
                        "property": "Date",
                        "date": {"on_or_after": cutoff},
                    },
                }
                if cursor:
                    body["start_cursor"] = cursor
                r = client.post(f"/databases/{db}/query", json=body)
                r.raise_for_status()
                data = r.json()
                for page in data.get("results", []):
                    props = page.get("properties", {})
                    num = None
                    title = ""
                    if props.get("Hymn number", {}).get("type") == "number":
                        num = props["Hymn number"].get("number")
                    if props.get("Hymn title", {}).get("type") == "rich_text":
                        title = "".join(
                            t.get("plain_text", "")
                            for t in props["Hymn title"].get("rich_text", [])
                        )
                    if num is not None and not isinstance(num, int):
                        try:
                            num = int(num)
                        except (TypeError, ValueError):
                            num = None
                    out.add(_hymn_key(num, title))
                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")
            return out
        except Exception:
            return set()


def record_usage(date_str: str, hymns: List[Dict[str, Any]]) -> bool:
    """Append one Notion row per hymn for this service date. Returns True if recorded."""
    iso = _parse_date_to_iso(date_str)
    if not iso:
        return False
    payload: List[Dict[str, Any]] = []
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
    db = _db_id()
    if not db:
        return False
    with _client() as client:
        if not client:
            return False
        try:
            for h in payload:
                num = h.get("number")
                title = h.get("title", "")
                title_display = f"{num} {title}" if num is not None else title
                body = {
                    "parent": {"database_id": db},
                    "properties": {
                        "Title": {"title": [{"type": "text", "text": {"content": title_display[:2000]}}]},
                        "Date": {"date": {"start": iso}},
                        "Hymn number": {"number": num},
                        "Hymn title": {"rich_text": [{"type": "text", "text": {"content": (title or "")[:2000]}}]},
                    },
                }
                client.post("/pages", json=body)
            return True
        except Exception:
            return False
