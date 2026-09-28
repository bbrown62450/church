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
from typing import NoReturn

from db import session_scope
from db.ids import as_uuid
from domain_errors import InvalidInput, RateLimited, Rejected
from repos import churches, invites, memberships
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


# --- Invites: the shared checks and the preview (S "Invite checks", "Preview semantics") ---

BLANK_CODE_MESSAGE = "Enter an invite code, or open your invite link again."

REJECT_MESSAGES: dict[InviteRejectReason, str] = {
    InviteRejectReason.unknown: "Invalid invite code.",
    InviteRejectReason.revoked: "This invite has been revoked.",
    InviteRejectReason.expired: "This invite has expired.",
    InviteRejectReason.used: "This invite has already been used.",
    InviteRejectReason.church_unavailable: "This church is no longer available.",
    InviteRejectReason.email_mismatch: "This invite was issued for a different email address.",
}

_GRANTABLE_ROLES = ("member", "admin")


def _strip_code(code: str) -> str:
    """Check 0: the code, stripped before lookup; blank is the 422 with fields.code."""
    stripped = (code or "").strip()
    if not stripped:
        raise InvalidInput(BLANK_CODE_MESSAGE, field="code")
    return stripped


def _load_invite(s, code: str, user_id: uuid.UUID) -> tuple:
    """The three reads preview and accept both start from (S accept_invite flow).

    Returns (inv, church, member_role): the Invite row or None; its church as
    repos.churches.get_church's dict, None when missing or soft-deleted; and
    the caller's role in the invite's church, None when not a member. The
    role is keyed on the invite, not the live church, so check 4's exception
    still holds after a soft delete and the consumer gets church_unavailable
    rather than used. Callers read it for already_member only once check 5
    has passed.
    """
    inv = invites.find_by_code(code, session=s)
    church = churches.get_church(inv.church_id, session=s) if inv is not None else None
    member_role = (
        memberships.get_role(user_id, inv.church_id, session=s) if inv is not None else None
    )
    return inv, church, member_role


def _clamp_role(role: str | None, *, invite_id) -> str:
    """The role an invite grants: member/admin as stored, owner -> admin (the
    F §6.2 repair), anything else -> member. A clamp logs one WARNING with the
    invite id (never the code), so the bad row can be found and fixed."""
    if role in _GRANTABLE_ROLES:
        return role
    granted = "admin" if role == "owner" else "member"
    logger.warning("invite_role_clamped invite_id=%s granted=%s", invite_id, granted)
    return granted


def _evaluate(inv, church: dict | None, user_id: uuid.UUID, user_email: str,
              member_role: str | None, now: datetime) -> InviteRejectReason | None:
    """Checks 1-6 of S "Invite checks", in that order; None when the invite is good.

    `church` is repos.churches.get_church's dict (None when missing or
    soft-deleted), `member_role` the caller's role in it (None when not a
    member), `user_email` CurrentUser.email, `now` an aware datetime.
    """
    if inv is None:
        return InviteRejectReason.unknown
    if inv.revoked:
        return InviteRejectReason.revoked
    if invites.as_utc(inv.expires_at) < now:  # naive (SQLite) == UTC
        return InviteRejectReason.expired
    if not inv.reusable and inv.accepted_at is not None:
        # Consumed: only the user who consumed it, while still a member, may
        # open it again (it then previews and accepts as already_member). A
        # removed member, another user, or a legacy stamp with accepted_by
        # NULL gets "used" (clarification 14).
        if not (inv.accepted_by == user_id and member_role is not None):
            return InviteRejectReason.used
    if church is None:
        return InviteRejectReason.church_unavailable
    if inv.email is not None and inv.email.strip().lower() != (user_email or "").strip().lower():
        return InviteRejectReason.email_mismatch
    return None


def _reject(reason: InviteRejectReason, invite_id) -> NoReturn:
    """Log one invite_rejected line (ids only: no code, no email) and raise the 400."""
    logger.info(
        "invite_rejected reason=%s invite_id=%s",
        reason.value, invite_id if invite_id is not None else "none",
    )
    raise Rejected(
        REJECT_MESSAGES[reason], code="invite_rejected", details={"reason": reason.value}
    )


def preview_invite(*, user_id: uuid.UUID, user_email: str, code: str,
                   now: datetime | None = None) -> InvitePreview:
    """What an invite offers the caller, without using it (S "Preview semantics").

    Read-only: one session_scope, no membership, no stamp. Runs checks 0-6
    and returns only the five InvitePreview fields, never the invite id, the
    code, the church id, the creator or the bound email (F §7.4).
    """
    user_id = as_uuid(user_id)
    code = _strip_code(code)
    now = now if now is not None else datetime.now(UTC)
    with session_scope() as s:
        inv, church, member_role = _load_invite(s, code, user_id)
        reason = _evaluate(inv, church, user_id, user_email, member_role, now)
        if reason is not None:
            _reject(reason, inv.id if inv is not None else None)
        return InvitePreview(
            church_name=church["name"],
            role=_clamp_role(inv.role, invite_id=inv.id),
            expires_at=invites.as_utc(inv.expires_at),
            email_bound=inv.email is not None,
            already_member=member_role is not None,
        )
