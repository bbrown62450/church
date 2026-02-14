#!/usr/bin/env python3
"""
Save and load worship services to/from a local archive so you can
revisit or restore a service's final state in the app.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARCHIVE_FILE = os.path.join(DATA_DIR, "saved_services.json")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_archive() -> List[Dict[str, Any]]:
    _ensure_data_dir()
    if not os.path.isfile(ARCHIVE_FILE):
        return []
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_archive(services: List[Dict[str, Any]]) -> None:
    _ensure_data_dir()
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
        json.dump(services, f, indent=2)


def list_saved_services() -> List[Dict[str, Any]]:
    """Return all saved services, most recent first (by saved_at)."""
    services = _load_archive()
    services.sort(key=lambda s: s.get("saved_at") or "", reverse=True)
    return services


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
) -> Dict[str, Any]:
    """
    Append the current service to the archive. Returns the saved service dict (with id, saved_at).
    """
    services = _load_archive()
    entry = {
        "id": str(uuid.uuid4()),
        "service_date": service_date,
        "service_date_iso": service_date_iso,
        "occasion": occasion,
        "scriptures": scriptures,
        "hymns": [{"title": h.get("title"), "number": h.get("number")} for h in hymns],
        "liturgy": liturgy,
        "sermon_title": sermon_title or "",
        "selected_ot_ref": selected_ot_ref or "",
        "selected_nt_ref": selected_nt_ref or "",
        "include_communion": include_communion,
        "saved_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    services.append(entry)
    _save_archive(services)
    return entry


def get_service(service_id: str) -> Optional[Dict[str, Any]]:
    """Return one saved service by id, or None."""
    for s in _load_archive():
        if s.get("id") == service_id:
            return s
    return None


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
    """
    Update an existing archive entry by id. Returns the updated service dict, or None if not found.
    """
    services = _load_archive()
    for i, s in enumerate(services):
        if s.get("id") == service_id:
            services[i] = {
                "id": service_id,
                "service_date": service_date,
                "service_date_iso": service_date_iso,
                "occasion": occasion,
                "scriptures": scriptures,
                "hymns": [{"title": h.get("title"), "number": h.get("number")} for h in hymns],
                "liturgy": liturgy,
                "sermon_title": sermon_title or "",
                "selected_ot_ref": selected_ot_ref or "",
                "selected_nt_ref": selected_nt_ref or "",
                "include_communion": include_communion,
                "saved_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            _save_archive(services)
            return services[i]
    return None


def delete_service(service_id: str) -> bool:
    """Remove a service from the archive. Returns True if removed."""
    services = [s for s in _load_archive() if s.get("id") != service_id]
    if len(services) == len(_load_archive()):
        return False
    _save_archive(services)
    return True
