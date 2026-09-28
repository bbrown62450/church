"""Onboarding usecases: create a church, preview an invite, accept an invite (S Modules added 1b).

Task 3 of slice 1b adds create_church and the per-user cap; Tasks 4 and 5 add
preview_invite and accept_invite. The layer rules are in usecases/__init__.py:
no FastAPI, Starlette or Streamlit here (test_no_streamlit_in_core.py).

Repos are called through their modules (churches.create_church_seeded, not a
from-import), so tests can patch one repo function (clarification 40).

Log lines carry ids, counts and reasons only: never a church name, an email
or an invite code (AC9).
"""
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, RateLimited
from repos import churches, invites, memberships  # noqa: F401  (invites, memberships: Tasks 4-5)
from timezones import is_valid_timezone

logger = logging.getLogger(__name__)

# The durable per-user cap on POST /churches (S Rate limits).
CREATE_CAP = 5
CREATE_WINDOW = timedelta(hours=24)
CAP_MESSAGE = "You've created 5 churches in the last 24 hours. Try again later."


@dataclass(frozen=True)
class ChurchSummary:
    id: uuid.UUID
    name: str
    role: str


@dataclass(frozen=True)
class InvitePreview:
    church_name: str
    role: str  # _clamp_role(invite.role): "member" or "admin"
    expires_at: datetime  # as_utc(invite.expires_at): always timezone-aware UTC
    email_bound: bool
    already_member: bool


@dataclass(frozen=True)
class InviteAccepted:
    church: ChurchSummary
    already_member: bool
    message: str


class InviteRejectReason(StrEnum):
    """details.reason of a 400 invite_rejected, in check order (S Invite checks)."""

    unknown = "unknown"
    revoked = "revoked"
    expired = "expired"
    used = "used"
    church_unavailable = "church_unavailable"
    email_mismatch = "email_mismatch"


def create_church(
    *, user_id: uuid.UUID, name: str, timezone: str, now: datetime | None = None
) -> ChurchSummary:
    """Create a church the caller owns, with its own copy of the hymn catalog.

    Both inputs are stripped first. The checks raise InvalidInput for the field
    they are about, in this order: name, blank timezone, unknown timezone. The
    per-user cap and the insert share one transaction, so a failed seed leaves
    no church and no membership. Returns the stored (trimmed) name.
    """
    user_id = as_uuid(user_id)
    name = (name or "").strip()
    timezone = (timezone or "").strip()
    if not name:
        raise InvalidInput("Church name is required.", field="name")
    if not timezone:
        raise InvalidInput("Timezone is required.", field="timezone")
    if not is_valid_timezone(timezone):
        raise InvalidInput("Unknown timezone.", field="timezone")
    now = now if now is not None else datetime.now(UTC)
    started = time.monotonic()
    with session_scope() as s:
        _enforce_create_cap(user_id, now, s)
        church_id, hymns_seeded = churches.create_church_seeded(
            name=name, timezone=timezone, owner_user_id=user_id, session=s
        )
    logger.info(
        "church_created church_id=%s user_id=%s hymns_seeded=%d duration_ms=%d",
        church_id, user_id, hymns_seeded, round((time.monotonic() - started) * 1000),
    )
    return ChurchSummary(id=church_id, name=name, role="owner")


def _enforce_create_cap(user_id: uuid.UUID, now: datetime, session) -> None:
    """Raise RateLimited when the caller owns CREATE_CAP or more churches created in the window.

    Soft-deleted churches count, so delete-and-recreate does not reset the cap;
    churches the caller only administers do not. Retry-After runs until the
    count would drop below the cap: the (count - 4)-th oldest turning 24 h old,
    which is the oldest when exactly five are counted (clarification 42).
    """
    created = churches.recent_owned_creations(
        user_id, since=now - CREATE_WINDOW, session=session
    )
    count = len(created)
    if count < CREATE_CAP:
        return
    frees_at = created[count - CREATE_CAP] + CREATE_WINDOW
    logger.info("church_create_limited user_id=%s count=%d", user_id, count)
    raise RateLimited(CAP_MESSAGE, retry_after_seconds=(frees_at - now).total_seconds())
