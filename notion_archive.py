#!/usr/bin/env python3
"""
Notion-backed service archive. When NOTION_ARCHIVE_DATABASE_ID is set,
archive operations use this Notion database instead of local JSON.

Required Notion database properties (create a DB and add these):
- Title (title) — or set NOTION_ARCHIVE_TITLE_PROPERTY=Name if your DB uses "Name"
- Service date (date)
- Occasion (rich_text)
- Scriptures (rich_text) — one ref per line
- Hymns (rich_text) — JSON array of {number, title}
- Liturgy (rich_text) — JSON object
- Selected OT (rich_text)
- Selected NT (rich_text)
- Saved at (date) — for sorting

Optional (omit if not in your DB): Sermon title (rich_text), Include communion (checkbox).
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

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
    return os.getenv("NOTION_ARCHIVE_DATABASE_ID") or None


def _title_property() -> str:
    """Property name for the page title (Notion DBs use 'Name' or 'Title')."""
    return os.getenv("NOTION_ARCHIVE_TITLE_PROPERTY", "Title")


def _rich_text(content: str) -> List[Dict[str, Any]]:
    if not content:
        return []
    return [{"type": "text", "text": {"content": content[:2000]}}]


def _prop_rich_text(value: str) -> Dict[str, Any]:
    return {"rich_text": _rich_text(value or "")}


def _prop_date(iso_date: Optional[str]) -> Dict[str, Any]:
    if not iso_date:
        return {"date": None}
    return {"date": {"start": iso_date}}


def _prop_checkbox(value: bool) -> Dict[str, Any]:
    return {"checkbox": bool(value)}


def _iso_to_display(iso: str) -> str:
    """Format YYYY-MM-DD to e.g. February 15, 2026."""
    if not iso:
        return ""
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return d.strftime("%B %d, %Y")
    except ValueError:
        return iso


def _page_to_service(page: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Notion page to our service dict shape."""
    pid = page.get("id") or ""
    props = page.get("properties", {})

    def get_rich_text(name: str) -> str:
        p = props.get(name, {})
        if p.get("type") != "rich_text":
            return ""
        return "".join(
            t.get("plain_text", "") for t in p.get("rich_text", [])
        )

    def get_date(name: str) -> str:
        p = props.get(name, {})
        if p.get("type") != "date":
            return ""
        d = p.get("date")
        return d.get("start", "") if d else ""

    def get_title(name: str) -> str:
        p = props.get(name, {})
        if p.get("type") != "title":
            return ""
        return "".join(
            t.get("plain_text", "") for t in p.get("title", [])
        )

    def get_checkbox(name: str) -> bool:
        p = props.get(name, {})
        if p.get("type") != "checkbox":
            return False
        return bool(p.get("checkbox"))

    liturgy_raw = get_rich_text("Liturgy")
    liturgy = {}
    if liturgy_raw:
        try:
            liturgy = json.loads(liturgy_raw)
        except Exception:
            pass

    hymns_raw = get_rich_text("Hymns")
    hymns = []
    if hymns_raw:
        try:
            hymns = json.loads(hymns_raw)
        except Exception:
            pass

    service_date_iso = get_date("Service date") or ""
    title_str = get_title(_title_property()) or get_title("Name") or get_title("Title")
    return {
        "id": pid,
        "service_date": _iso_to_display(service_date_iso) or title_str,
        "service_date_iso": service_date_iso,
        "occasion": get_rich_text("Occasion") or title_str,
        "scriptures": (get_rich_text("Scriptures") or "").strip().splitlines(),
        "hymns": hymns,
        "liturgy": liturgy,
        "sermon_title": get_rich_text("Sermon title") or "",
        "selected_ot_ref": get_rich_text("Selected OT") or "",
        "selected_nt_ref": get_rich_text("Selected NT") or "",
        "include_communion": get_checkbox("Include communion"),
        "saved_at": get_date("Saved at") or "",
    }


def list_saved_services() -> List[Dict[str, Any]]:
    """Return all saved services from Notion, most recent first."""
    db = _db_id()
    if not db:
        return []
    with _client() as client:
        if not client:
            return []
        try:
            results = []
            cursor = None
            while True:
                body: Dict[str, Any] = {"page_size": 100, "sorts": [{"property": "Saved at", "direction": "descending"}]}
                if cursor:
                    body["start_cursor"] = cursor
                r = client.post(f"/databases/{db}/query", json=body)
                r.raise_for_status()
                data = r.json()
                for page in data.get("results", []):
                    results.append(_page_to_service(page))
                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")
            return results
        except Exception:
            return []


def get_service(service_id: str) -> Optional[Dict[str, Any]]:
    """Return one saved service by Notion page id."""
    if not service_id:
        return None
    with _client() as client:
        if not client:
            return None
        try:
            r = client.get(f"/pages/{service_id}")
            r.raise_for_status()
            return _page_to_service(r.json())
        except Exception:
            return None


def save_service(
    *,
    service_date: str,
    service_date_iso: str,
    occasion: str,
    scriptures: List[str],
    hymns: List[Dict[str, Any]],
    liturgy: Dict[str, str],
    sermon_title: str = "",
    selected_ot_ref: str = "",
    selected_nt_ref: str = "",
    include_communion: bool = False,
) -> Optional[Dict[str, Any]]:
    """Create a new archive entry in Notion. Returns the saved service dict or None."""
    db = _db_id()
    if not db:
        return None
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    hymns_payload = [{"title": h.get("title"), "number": h.get("number")} for h in hymns]
    with _client() as client:
        if not client:
            return None
        try:
            title_key = _title_property()
            body = {
                "parent": {"database_id": db},
                "properties": {
                    title_key: {"title": _rich_text(occasion or service_date or "Service")},
                    "Service date": _prop_date(service_date_iso or None),
                    "Occasion": _prop_rich_text(occasion),
                    "Scriptures": _prop_rich_text("\n".join(scriptures or [])),
                    "Hymns": _prop_rich_text(json.dumps(hymns_payload)),
                    "Liturgy": _prop_rich_text(json.dumps(liturgy or {})),
                    "Selected OT": _prop_rich_text(selected_ot_ref),
                    "Selected NT": _prop_rich_text(selected_nt_ref),
                    "Saved at": _prop_date(now),
                },
            }
            r = client.post("/pages", json=body)
            if r.status_code >= 400:
                err = r.text
                try:
                    data = r.json()
                    err = data.get("message", data.get("code", err))
                except Exception:
                    pass
                raise RuntimeError(f"Notion archive save failed: {err}") from None
            page = r.json()
            out = _page_to_service(page)
            out["saved_at"] = now
            return out
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Notion archive save failed: {e}") from e


def update_service(
    service_id: str,
    *,
    service_date: str,
    service_date_iso: str,
    occasion: str,
    scriptures: List[str],
    hymns: List[Dict[str, Any]],
    liturgy: Dict[str, str],
    sermon_title: str = "",
    selected_ot_ref: str = "",
    selected_nt_ref: str = "",
    include_communion: bool = False,
) -> Optional[Dict[str, Any]]:
    """Update an existing archive entry in Notion."""
    if not service_id:
        return None
    hymns_payload = [{"title": h.get("title"), "number": h.get("number")} for h in hymns]
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with _client() as client:
        if not client:
            return None
        try:
            title_key = _title_property()
            body = {
                "properties": {
                    title_key: {"title": _rich_text(occasion or service_date or "Service")},
                    "Service date": _prop_date(service_date_iso or None),
                    "Occasion": _prop_rich_text(occasion),
                    "Scriptures": _prop_rich_text("\n".join(scriptures or [])),
                    "Hymns": _prop_rich_text(json.dumps(hymns_payload)),
                    "Liturgy": _prop_rich_text(json.dumps(liturgy or {})),
                    "Selected OT": _prop_rich_text(selected_ot_ref),
                    "Selected NT": _prop_rich_text(selected_nt_ref),
                    "Saved at": _prop_date(now),
                },
            }
            r = client.patch(f"/pages/{service_id}", json=body)
            r.raise_for_status()
            return _page_to_service(r.json())
        except Exception:
            return None


def delete_service(service_id: str) -> bool:
    """Archive (soft delete) the page in Notion. Returns True if successful."""
    if not service_id:
        return False
    with _client() as client:
        if not client:
            return False
        try:
            r = client.patch(f"/pages/{service_id}", json={"archived": True})
            r.raise_for_status()
            return True
        except Exception:
            return False
