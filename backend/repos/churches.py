import datetime as _dt
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from db import session_scope
from db.ids import as_uuid
from db.models import Church, Membership, Invite
from repos.invites import as_utc
from service_rubric import apply_patch, merge_rubric, validate_patch


def create_church(
    *, name, timezone, owner_user_id, session: Optional[Session] = None
) -> uuid.UUID:
    """Create a church, its creator's owner membership, and seed the per-church
    hymnal from the shared catalog — all in one transaction (atomic, so no admin
    ever sees a half-populated hymnal). Returns the new church id.

    Runs in the caller's `session` (no commit) or in its own scope.
    create_church_seeded also returns the number of hymns seeded.
    """
    church_id, _ = create_church_seeded(
        name=name, timezone=timezone, owner_user_id=owner_user_id, session=session
    )
    return church_id


def create_church_seeded(
    *, name, timezone, owner_user_id, session: Optional[Session] = None
) -> tuple[uuid.UUID, int]:
    """create_church, returning (church id, hymns seeded) for the
    `church_created ... hymns_seeded=` log line (usecases.onboarding).
    `owner_user_id` goes through as_uuid (a malformed id is NotFound)."""
    owner_id = as_uuid(owner_user_id)
    if session is not None:
        return _create_church(session, name, timezone, owner_id)
    with session_scope() as own:
        return _create_church(own, name, timezone, owner_id)


def _create_church(session, name, timezone, owner_id) -> tuple[uuid.UUID, int]:
    church = Church(name=name, timezone=timezone)
    session.add(church)
    session.flush()  # assign church.id (Python-side uuid default)
    session.add(Membership(church_id=church.id, user_id=owner_id, role="owner"))
    session.flush()  # the owner membership, before the hymn rows
    # Looked up at call time, so a test can monkeypatch
    # repos.hymns.seed_church_from_catalog (the atomicity test makes it raise).
    from repos.hymns import seed_church_from_catalog
    seeded = seed_church_from_catalog(church.id, session)
    return church.id, seeded


def get_church(church_id, *, session: Optional[Session] = None) -> Optional[dict]:
    """{"id", "name", "timezone", "settings"}, or None when the church is missing
    or soft-deleted. Reads in the caller's `session` or in its own scope.
    `church_id` goes through as_uuid (a malformed id is NotFound, F §2.2 item 5)."""
    church_id = as_uuid(church_id)
    if session is not None:
        return _get_church(session, church_id)
    with session_scope() as own:
        return _get_church(own, church_id)


def _get_church(session, church_id) -> Optional[dict]:
    church = session.get(Church, church_id)
    if church is None or church.deleted_at is not None:
        return None
    return {
        "id": church.id,
        "name": church.name,
        "timezone": church.timezone,
        "settings": church.settings,
    }


def recent_owned_creations(
    user_id, *, since: datetime, session: Optional[Session] = None
) -> list[datetime]:
    """created_at of every church `user_id` holds an owner membership in and
    that was created after `since`, oldest first, as aware UTC. Soft-deleted
    churches count, so deleting a church does not free a slot in the per-user
    create cap (usecases.onboarding.create_church)."""
    uid = as_uuid(user_id)
    since_utc = as_utc(since)  # SQLite compares naive UTC text
    if session is not None:
        return _recent_owned_creations(session, uid, since_utc)
    with session_scope() as own:
        return _recent_owned_creations(own, uid, since_utc)


def _recent_owned_creations(session, user_id, since) -> list[datetime]:
    stamps = session.execute(
        select(Church.created_at)
        .join(Membership, Membership.church_id == Church.id)
        .where(
            Membership.user_id == user_id,
            Membership.role == "owner",
            Church.created_at > since,
        )
        .order_by(Church.created_at)
    ).scalars().all()
    return [as_utc(stamp) for stamp in stamps]


def list_user_churches(user_id) -> list:
    with session_scope() as session:
        rows = session.execute(
            select(Church.id, Church.name, Membership.role)
            .join(Membership, Membership.church_id == Church.id)
            .where(Membership.user_id == user_id, Church.deleted_at.is_(None))
            .order_by(Church.name)
        ).all()
        return [{"id": r.id, "name": r.name, "role": r.role} for r in rows]


def soft_delete_church(church_id) -> None:
    """Soft-delete the church (excluded from every query afterward) and revoke
    all still-pending invites for it."""
    with session_scope() as session:
        church = session.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            return
        church.deleted_at = _dt.datetime.now(_dt.timezone.utc)
        session.execute(
            update(Invite)
            .where(
                Invite.church_id == church_id,
                Invite.revoked.is_(False),
                Invite.accepted_at.is_(None),
            )
            .values(revoked=True)
        )


def update_church(church_id, *, name=None, timezone=None, settings=None) -> None:
    with session_scope() as session:
        church = session.get(Church, church_id)
        if church is None or church.deleted_at is not None:
            return
        if name is not None:
            church.name = name
        if timezone is not None:
            church.timezone = timezone
        if settings is not None:
            church.settings = settings


def _lock_live_church(session, church_id) -> Optional[Church]:
    """Load the church row with SELECT ... FOR UPDATE (Postgres; SQLite ignores
    it), so a concurrent settings write waits for this transaction instead of
    overwriting it. None if the church is missing or soft-deleted."""
    church = session.get(Church, church_id, with_for_update=True)
    if church is None or church.deleted_at is not None:
        return None
    return church


def _merge_settings(church_id, patch: dict) -> None:
    """Shallow-merge `patch` into the church's settings JSON under a row lock
    (reassigns a new dict so SQLAlchemy detects the change)."""
    with session_scope() as session:
        church = _lock_live_church(session, church_id)
        if church is None:
            return
        church.settings = {**(church.settings or {}), **patch}


def get_church_prompts(church_id, *, session: Optional[Session] = None) -> dict:
    """Per-church liturgy prompt overrides ({} when the church uses all defaults,
    or when the stored value is not an object). Reads in the caller's `session`
    or in its own scope (slice 4, F §2.2 rule 3)."""
    church = get_church(church_id, session=session)
    if not church:
        return {}
    stored = (church.get("settings") or {}).get("liturgy_prompts")
    return dict(stored) if isinstance(stored, dict) else {}


def set_church_prompts(church_id, prompts: dict) -> None:
    """Store per-church prompt overrides. A blank value for a key means "reset to
    default" — it is dropped, so only real overrides are persisted."""
    from liturgy_prompts import PROMPT_KEYS

    cleaned = {
        k: v.strip()
        for k, v in (prompts or {}).items()
        if k in PROMPT_KEYS and (v or "").strip()
    }
    _merge_settings(church_id, {"liturgy_prompts": cleaned})


def get_church_rubric_overrides(church_id, *, session: Optional[Session] = None) -> dict:
    """The church's stored rubric overrides ({} when it uses all defaults).
    Reads in the caller's `session` or in its own scope (slice 3, F §2.2 rule 3)."""
    church = get_church(church_id, session=session)
    if not church:
        return {}
    stored = (church.get("settings") or {}).get("rubric")
    return dict(stored) if isinstance(stored, dict) else {}


def get_church_rubric(church_id) -> dict:
    """The church's full rubric: the defaults with its valid overrides applied."""
    return merge_rubric(get_church_rubric_overrides(church_id))


def update_church_rubric(church_id, patch: dict) -> dict:
    """Validate and apply a sparse rubric patch (None resets that checklist or
    setting to its default). Raises ValueError, storing nothing, on invalid
    input. Returns the merged rubric.

    The stored overrides are read from the row this transaction locks and then
    rewrites, so two admins patching at once cannot drop each other's change.
    """
    cleaned = validate_patch(patch)
    with session_scope() as session:
        church = _lock_live_church(session, church_id)
        settings = dict(church.settings or {}) if church is not None else {}
        stored = settings.get("rubric")
        overrides = apply_patch(stored if isinstance(stored, dict) else {}, cleaned)
        if church is not None:
            church.settings = {**settings, "rubric": overrides}
    return merge_rubric(overrides)


def get_church_translation(church_id) -> str | None:
    """The church's default Bible translation id, or None (falls back to app default)."""
    church = get_church(church_id)
    if not church:
        return None
    return (church.get("settings") or {}).get("bible_translation")


def set_church_translation(church_id, translation_id: str) -> None:
    _merge_settings(church_id, {"bible_translation": translation_id})
