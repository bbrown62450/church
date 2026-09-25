#!/usr/bin/env python3
"""Database-backed, church-scoped worship service archive.

Every function is scoped to a validated `church_id` (derived server-side by the
active-church guard). Reads/updates/deletes for an id outside the caller's
church return "not found" (None / False) — the IDOR fix.
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select

from db import session_scope
from db.models import Service


def _as_uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _hymn_snapshot(hymns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{"title": h.get("title"), "number": h.get("number")} for h in (hymns or [])]


def _to_dict(s: Service) -> Dict[str, Any]:
    return {
        "id": str(s.id),
        "church_id": str(s.church_id),
        "created_by": str(s.created_by) if s.created_by else None,
        "service_date": s.service_date_display,
        "service_date_iso": s.service_date_iso,
        "occasion": s.occasion,
        "scriptures": s.scriptures or [],
        "hymns": s.hymns or [],
        "liturgy": s.liturgy or {},
        "sermon_title": s.sermon_title or "",
        "selected_ot_ref": s.selected_ot_ref or "",
        "selected_nt_ref": s.selected_nt_ref or "",
        "include_communion": bool(s.include_communion),
        "saved_at": s.saved_at.isoformat() if s.saved_at else None,
    }


def list_saved_services(church_id) -> List[Dict[str, Any]]:
    """All services for a church, most recent first (by saved_at)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        rows = (
            session.execute(
                select(Service)
                .where(Service.church_id == cid)
                .order_by(Service.saved_at.desc())
            )
            .scalars()
            .all()
        )
        return [_to_dict(s) for s in rows]


def save_service(
    church_id,
    *,
    created_by=None,
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
    """Insert a service for a church. Returns the saved dict (with id, saved_at)."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        s = Service(
            church_id=cid,
            created_by=_as_uuid(created_by) if created_by else None,
            service_date_display=service_date,
            service_date_iso=service_date_iso,
            occasion=occasion,
            scriptures=list(scriptures or []),
            hymns=_hymn_snapshot(hymns),
            liturgy=dict(liturgy or {}),
            sermon_title=sermon_title or "",
            selected_ot_ref=selected_ot_ref or "",
            selected_nt_ref=selected_nt_ref or "",
            include_communion=bool(include_communion),
        )
        session.add(s)
        session.flush()
        return _to_dict(s)


def get_service(service_id, church_id) -> Optional[Dict[str, Any]]:
    """Return one service only if it belongs to `church_id`. Else None."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        s = session.execute(
            select(Service).where(
                Service.id == _as_uuid(service_id), Service.church_id == cid
            )
        ).scalar_one_or_none()
        return _to_dict(s) if s is not None else None


def update_service(
    service_id,
    church_id,
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
    """Update a service only if it belongs to `church_id`. Cross-church -> None."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        s = session.execute(
            select(Service).where(
                Service.id == _as_uuid(service_id), Service.church_id == cid
            )
        ).scalar_one_or_none()
        if s is None:
            return None
        s.service_date_display = service_date
        s.service_date_iso = service_date_iso
        s.occasion = occasion
        s.scriptures = list(scriptures or [])
        s.hymns = _hymn_snapshot(hymns)
        s.liturgy = dict(liturgy or {})
        s.sermon_title = sermon_title or ""
        s.selected_ot_ref = selected_ot_ref or ""
        s.selected_nt_ref = selected_nt_ref or ""
        s.include_communion = bool(include_communion)
        s.saved_at = datetime.now(timezone.utc)
        session.flush()
        return _to_dict(s)


def delete_service(service_id, church_id) -> bool:
    """Delete a service only if it belongs to `church_id`. Cross-church -> False."""
    cid = _as_uuid(church_id)
    with session_scope() as session:
        result = session.execute(
            delete(Service).where(
                Service.id == _as_uuid(service_id), Service.church_id == cid
            )
        )
        return result.rowcount > 0
