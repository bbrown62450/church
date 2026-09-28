"""usecases.onboarding (S Modules added 1b, Rate limits, Testing; slice 1b).

Task 3: create_church and the per-user cap. Tasks 4 and 5 append the invite
preview and accept tests. The cap tests inject `now` and move each church's
created_at to a fixed offset from it, because the repo stamps the real clock.
"""
import dataclasses
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

import repos.churches
import repos.hymns
import repos.invites
from db import session_scope
from db.models import Church, Invite, Membership, User
from domain_errors import InvalidInput, RateLimited, Rejected
from repos.churches import get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
from repos.memberships import add_membership, get_role, remove_membership
from usecases import onboarding

NOW = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
TZ = "America/New_York"
CAP_TEXT = "You've created 5 churches in the last 24 hours. Try again later."


def _set_created_at(church_id, when):
    with session_scope() as s:
        s.execute(update(Church).where(Church.id == church_id).values(created_at=when))


def _owned_church(user_id, hours_ago, name="Earlier"):
    """A church the user owns, created `hours_ago` hours before NOW (repo call: no cap)."""
    church_id = repos.churches.create_church(name=name, timezone=TZ, owner_user_id=user_id)
    _set_created_at(church_id, NOW - timedelta(hours=hours_ago))
    return church_id


def _row_counts():
    """(churches, memberships) in the whole database."""
    with session_scope() as s:
        return (
            s.execute(select(func.count()).select_from(Church)).scalar_one(),
            s.execute(select(func.count()).select_from(Membership)).scalar_one(),
        )


# ---- create_church (Task 3) ----------------------------------------------------


def test_create_church_trims_and_returns_owner_summary(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    summary = onboarding.create_church(
        user_id=user, name="  New Life  ", timezone=" America/Chicago ", now=NOW
    )
    assert isinstance(summary.id, uuid.UUID)
    assert summary == onboarding.ChurchSummary(id=summary.id, name="New Life", role="owner")
    church = get_church(summary.id)
    assert (church["name"], church["timezone"]) == ("New Life", "America/Chicago")
    assert list_user_churches(user) == [{"id": summary.id, "name": "New Life", "role": "owner"}]


@pytest.mark.parametrize(
    ("name", "timezone", "field", "message"),
    [
        ("   ", TZ, "name", "Church name is required."),
        ("Grace", "  ", "timezone", "Timezone is required."),
        ("Grace", "america/new_york", "timezone", "Unknown timezone."),
    ],
    ids=["name-blank", "tz-blank", "tz-unknown"],
)
def test_create_church_rejects(tmp_db, make_user, name, timezone, field, message):
    user = make_user(email="founder@b.org")
    with pytest.raises(InvalidInput) as exc:
        onboarding.create_church(user_id=user, name=name, timezone=timezone, now=NOW)
    assert (exc.value.message, exc.value.field, exc.value.code) == (
        message, field, "invalid_request"
    )
    assert _row_counts() == (0, 0)


def test_create_church_seeds_catalog_with_identical_values(tmp_db, make_user, seed_catalog):
    # Port of streamlit_tests/test_onboarding.py::test_create_church_makes_owner_and_seeds_hymnal.
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    summary = onboarding.create_church(user_id=user, name="New Life", timezone=TZ, now=NOW)
    assert any(c["id"] == summary.id and c["role"] == "owner" for c in list_user_churches(user))
    hymns = list_hymns(summary.id)
    assert len(hymns) == 5  # seeded atomically from the catalog
    assert [
        (h["Hymnal"], h["Hymn Title"], h["Hymn Number"], h["Scripture References"],
         h["Theme"], h["Hymnary.org Link"], h["Audio"], h["Text Year"], h["Hymnal Count"])
        for h in hymns
    ] == [
        ("GG2013", f"Hymn {i}", i, f"John {i}:1-{i + 2}",
         "praise, grace", f"https://hymnary.org/hymn/{i}", None, None, None)
        for i in range(1, 6)
    ]


def test_create_church_is_atomic_when_seed_fails(tmp_db, make_user, seed_catalog, monkeypatch):
    seed_catalog(3)
    user = make_user(email="founder@b.org")

    def boom(*args, **kwargs):
        raise RuntimeError("seed failed")

    # The church repo resolves the seed from repos.hymns at call time; the second
    # patch keeps the test valid if that import ever moves to module level.
    monkeypatch.setattr(repos.hymns, "seed_church_from_catalog", boom)
    monkeypatch.setattr(repos.churches, "seed_church_from_catalog", boom, raising=False)
    with pytest.raises(RuntimeError, match="seed failed"):
        onboarding.create_church(user_id=user, name="New Life", timezone=TZ, now=NOW)
    assert _row_counts() == (0, 0)  # no church, no owner membership


# ---- the per-user cap (S Rate limits; clarification 42) --------------------------


def test_sixth_create_in_24h_is_rate_limited(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    made = [
        onboarding.create_church(user_id=user, name=f"Church {i}", timezone=TZ, now=NOW)
        for i in range(1, 6)
    ]
    for summary, hours_ago in zip(made, [23, 20, 15, 10, 1]):
        _set_created_at(summary.id, NOW - timedelta(hours=hours_ago))
    with pytest.raises(RateLimited) as exc:
        onboarding.create_church(user_id=user, name="Church 6", timezone=TZ, now=NOW)
    assert (exc.value.message, exc.value.code) == (CAP_TEXT, "rate_limited")
    assert exc.value.retry_after_seconds == 3600  # the oldest turns 24 h old in one hour
    assert exc.value.details == {"retry_after_seconds": 3600}
    assert _row_counts() == (5, 5)


def test_retry_after_uses_the_fifth_newest_when_over_cap(tmp_db, make_user):
    # Six counted (the frozen Streamlit app has no cap, and two concurrent creates
    # can both pass at four): when the oldest ages out five remain, so Retry-After
    # runs until the second oldest is 24 h old.
    user = make_user(email="founder@b.org")
    for hours_ago in [23.5, 22, 20, 15, 10, 1]:
        _owned_church(user, hours_ago)
    with pytest.raises(RateLimited) as exc:
        onboarding.create_church(user_id=user, name="Seventh", timezone=TZ, now=NOW)
    assert exc.value.retry_after_seconds == 2 * 3600


def test_cap_ignores_churches_older_than_24h(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    for hours_ago in [25, 20, 15, 10, 1]:
        _owned_church(user, hours_ago)
    summary = onboarding.create_church(user_id=user, name="Another", timezone=TZ, now=NOW)
    assert summary.role == "owner"


def test_cap_counts_soft_deleted(tmp_db, make_user):
    user = make_user(email="founder@b.org")
    church_ids = [_owned_church(user, hours_ago) for hours_ago in [20, 15, 10, 5, 1]]
    soft_delete_church(church_ids[0])  # delete-and-recreate does not reset the cap
    with pytest.raises(RateLimited) as exc:
        onboarding.create_church(user_id=user, name="Again", timezone=TZ, now=NOW)
    assert exc.value.retry_after_seconds == 4 * 3600


def test_cap_ignores_admin_only_churches(tmp_db, make_user, make_church):
    user = make_user(email="helper@b.org")
    for i in range(1, 6):
        church_id = make_church(name=f"Other {i}")  # owned by a fresh user each time
        add_membership(user, church_id, "admin")
        _set_created_at(church_id, NOW - timedelta(hours=1))
    summary = onboarding.create_church(user_id=user, name="My Own", timezone=TZ, now=NOW)
    assert summary.role == "owner"


def test_create_logs_ids_only(tmp_db, make_user, seed_catalog, caplog):
    seed_catalog(5)
    user = make_user(email="founder@b.org")
    for hours_ago in [20, 15, 10, 5]:
        _owned_church(user, hours_ago)
    caplog.set_level(logging.INFO, logger="usecases.onboarding")
    summary = onboarding.create_church(
        user_id=user, name="Secret Name Church", timezone=TZ, now=NOW
    )
    _set_created_at(summary.id, NOW - timedelta(hours=1))
    with pytest.raises(RateLimited):
        onboarding.create_church(user_id=user, name="Secret Name Two", timezone=TZ, now=NOW)
    created, limited = [r.getMessage() for r in caplog.records if r.name == "usecases.onboarding"]
    assert re.fullmatch(
        rf"church_created church_id={summary.id} user_id={user} hymns_seeded=5 duration_ms=\d+",
        created,
    )
    assert limited == f"church_create_limited user_id={user} count=5"
    assert "Secret Name" not in caplog.text
    assert "founder@b.org" not in caplog.text


# ---- invite checks and preview_invite (Task 4; Task 5 adds accept) ----------------

# The injected clock for every invite test, and the expiry every test invite
# gets: midday UTC, stored naive because SQLite hands back naive UTC anyway.
INVITE_NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
INVITE_EXPIRES = datetime(2026, 10, 8, 12, 0)

JOINER_EMAIL = "joiner@example.com"

# Every action that runs the shared checks. T5 adds "accept": onboarding.accept_invite.
INVITE_ACTIONS = {"preview": onboarding.preview_invite}

REJECTIONS = {
    "unknown": "Invalid invite code.",
    "revoked": "This invite has been revoked.",
    "expired": "This invite has expired.",
    "used": "This invite has already been used.",
    "church_unavailable": "This church is no longer available.",
    "email_mismatch": "This invite was issued for a different email address.",
}


def _update_invite(code, **values):
    with session_scope() as s:
        s.execute(update(Invite).where(Invite.code == code).values(**values))


def _invite(church_id, created_by, **kwargs) -> str:
    """repos.invites.create_invite, then pin expires_at to INVITE_EXPIRES."""
    code = repos.invites.create_invite(church_id=church_id, created_by=created_by, **kwargs)
    _update_invite(code, expires_at=INVITE_EXPIRES)
    return code


def _invite_id(code):
    with session_scope() as s:
        return s.execute(select(Invite.id).where(Invite.code == code)).scalar_one()


def _all_row_counts() -> dict:
    with session_scope() as s:
        return {
            model.__tablename__: s.execute(select(func.count()).select_from(model)).scalar_one()
            for model in (User, Church, Membership, Invite)
        }


@pytest.fixture
def invite_world(make_user, make_church):
    """An owner, a joiner, a third user, and the church "Grace" (no hymns)."""
    owner = make_user(email="owner@example.com")
    joiner = make_user(email=JOINER_EMAIL)
    other = make_user(email="other@example.com")
    church_id = make_church(name="Grace", timezone="America/New_York", owner_user_id=owner)
    return {"owner": owner, "joiner": joiner, "other": other, "church_id": church_id}


def _rejected_code(reason, world) -> str:
    """An invite that fails exactly check `reason` for the joiner at INVITE_NOW."""
    cid, owner = world["church_id"], world["owner"]
    if reason == "unknown":
        return "no-such-invite-code"
    if reason == "email_mismatch":
        return _invite(cid, owner, email="someone.else@example.com")
    code = _invite(cid, owner)
    if reason == "revoked":
        _update_invite(code, revoked=True)
    elif reason == "expired":
        _update_invite(code, expires_at=datetime(2026, 10, 1, 11, 59))
    elif reason == "used":
        _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=world["other"])
    elif reason == "church_unavailable":
        # Soft-delete the church directly, leaving the invite live (soft_delete_church
        # would revoke it, and check 2 would win).
        with session_scope() as s:
            s.execute(update(Church).where(Church.id == cid).values(deleted_at=INVITE_NOW))
    return code


@pytest.mark.parametrize("reason", list(REJECTIONS))
@pytest.mark.parametrize("action", list(INVITE_ACTIONS))
def test_invite_rejections(action, reason, invite_world, caplog):
    code = _rejected_code(reason, invite_world)
    before = _all_row_counts()
    caplog.set_level(logging.INFO, logger="usecases.onboarding")

    with pytest.raises(Rejected) as exc:
        INVITE_ACTIONS[action](
            user_id=invite_world["joiner"], user_email=JOINER_EMAIL,
            code=f"  {code}\n", now=INVITE_NOW,  # stripped before lookup
        )

    assert exc.value.status == 400
    assert exc.value.code == "invite_rejected"
    assert exc.value.message == REJECTIONS[reason]
    assert exc.value.details == {"reason": reason}
    assert exc.value.field is None
    invite_id = "none" if reason == "unknown" else str(_invite_id(code))
    assert [r.getMessage() for r in caplog.records if r.getMessage().startswith("invite_rejected")] == [
        f"invite_rejected reason={reason} invite_id={invite_id}"
    ]
    assert code not in caplog.text and JOINER_EMAIL not in caplog.text
    assert _all_row_counts() == before


@pytest.mark.parametrize("action", list(INVITE_ACTIONS))
def test_blank_code_is_invalid_input(action, invite_world):
    for blank in ("", "   ", "\t\n"):
        with pytest.raises(InvalidInput) as exc:
            INVITE_ACTIONS[action](
                user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=blank, now=INVITE_NOW,
            )
        assert exc.value.status == 422
        assert exc.value.code == "invalid_request"
        assert exc.value.message == "Enter an invite code, or open your invite link again."
        assert exc.value.field == "code"


def _preview_reason(world, code) -> str:
    with pytest.raises(Rejected) as exc:
        onboarding.preview_invite(
            user_id=world["joiner"], user_email=JOINER_EMAIL, code=code, now=INVITE_NOW,
        )
    return exc.value.details["reason"]


def test_order_revoked_beats_church_unavailable(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    soft_delete_church(invite_world["church_id"])   # also revokes pending invites
    assert get_church(invite_world["church_id"]) is None
    assert repos.invites.get_invite_by_code(code)["revoked"] is True
    assert _preview_reason(invite_world, code) == "revoked"


def test_order_expired_beats_used(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    _update_invite(
        code, expires_at=datetime(2026, 10, 1, 11, 59),
        accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=invite_world["other"],
    )
    assert _preview_reason(invite_world, code) == "expired"


def test_order_used_beats_email_mismatch(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"], email="other@example.com")
    _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=invite_world["other"])
    assert _preview_reason(invite_world, code) == "used"


def test_consumer_sees_church_unavailable_after_soft_delete(invite_world):
    # Check 4's exception looks up the caller's membership in the invite's
    # church, live or not, so the consumer (still a member) reaches check 5.
    cid, owner, joiner = invite_world["church_id"], invite_world["owner"], invite_world["joiner"]
    code = _invite(cid, owner, email=JOINER_EMAIL)
    _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=joiner)
    add_membership(joiner, cid, "member")
    soft_delete_church(cid)   # revokes only pending invites; this one was consumed
    assert get_church(cid) is None
    assert repos.invites.get_invite_by_code(code)["revoked"] is False
    assert get_role(joiner, cid) == "member"

    def preview(user_id, email):
        with pytest.raises(Rejected) as exc:
            onboarding.preview_invite(user_id=user_id, user_email=email, code=code, now=INVITE_NOW)
        return exc.value.message, exc.value.details["reason"]

    assert preview(joiner, JOINER_EMAIL) == ("This church is no longer available.", "church_unavailable")
    # Anyone else still gets "used": check 4 beats check 5, and beats the
    # email mismatch (the invite is bound to the joiner's address).
    assert preview(invite_world["other"], "other@example.com") == (
        "This invite has already been used.", "used",
    )
    # Revoked still beats church_unavailable for the consumer.
    _update_invite(code, revoked=True)
    assert preview(joiner, JOINER_EMAIL) == ("This invite has been revoked.", "revoked")


@pytest.mark.parametrize(("stored", "granted"), [("owner", "admin"), ("foo", "member")])
def test_clamp_role(stored, granted, caplog):
    invite_id = uuid.uuid4()
    caplog.set_level(logging.WARNING, logger="usecases.onboarding")
    assert onboarding._clamp_role("member", invite_id=invite_id) == "member"
    assert onboarding._clamp_role("admin", invite_id=invite_id) == "admin"
    assert caplog.records == []                                   # no clamp, no warning

    assert onboarding._clamp_role(stored, invite_id=invite_id) == granted

    [record] = caplog.records
    assert record.levelno == logging.WARNING
    assert record.getMessage() == f"invite_role_clamped invite_id={invite_id} granted={granted}"


def test_naive_expires_at_is_utc_with_injected_now(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    _update_invite(code, expires_at=datetime(2026, 10, 1, 12, 0))   # naive: 12:00 UTC

    def preview_at(now):
        return onboarding.preview_invite(
            user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=code, now=now,
        )

    # 06:59 at UTC-5 is 11:59 UTC: one minute before expiry, still good.
    assert preview_at(datetime.fromisoformat("2026-10-01T06:59:00-05:00")).church_name == "Grace"
    # Exactly the expiry instant is not "expires_at < now".
    assert preview_at(datetime(2026, 10, 1, 12, 0, tzinfo=UTC)).church_name == "Grace"
    # 07:01 at UTC-5 is 12:01 UTC: expired.
    with pytest.raises(Rejected) as exc:
        preview_at(datetime.fromisoformat("2026-10-01T07:01:00-05:00"))
    assert exc.value.details == {"reason": "expired"}


def test_preview_writes_nothing_and_has_five_fields(invite_world):
    cid, owner, joiner = invite_world["church_id"], invite_world["owner"], invite_world["joiner"]
    code = _invite(cid, owner)
    bound = _invite(cid, owner, email="Joiner@Example.com", role="admin")
    before = _all_row_counts()

    preview = onboarding.preview_invite(user_id=joiner, user_email=JOINER_EMAIL, code=code, now=INVITE_NOW)
    bound_preview = onboarding.preview_invite(user_id=joiner, user_email=JOINER_EMAIL, code=bound, now=INVITE_NOW)

    assert dataclasses.asdict(preview) == {
        "church_name": "Grace",
        "role": "member",
        "expires_at": datetime(2026, 10, 8, 12, 0, tzinfo=UTC),
        "email_bound": False,
        "already_member": False,
    }
    assert (bound_preview.role, bound_preview.email_bound) == ("admin", True)
    assert _all_row_counts() == before
    for c in (code, bound):
        row = repos.invites.get_invite_by_code(c)
        assert (row["accepted_at"], row["revoked"]) == (None, False)
    assert get_role(joiner, cid) is None


@pytest.mark.parametrize(("stored", "granted"), [
    pytest.param("owner", "admin", id="owner"),
    pytest.param("foo", "member", id="foo"),
])
def test_preview_clamps_role(stored, granted, invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"], role=stored)
    preview = onboarding.preview_invite(
        user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=code, now=INVITE_NOW,
    )
    assert preview.role == granted
    assert repos.invites.get_invite_by_code(code)["role"] == stored   # the row is not repaired


def test_preview_expires_at_is_aware_utc(invite_world):
    code = _invite(invite_world["church_id"], invite_world["owner"])
    with session_scope() as s:
        assert repos.invites.find_by_code(code, session=s).expires_at.tzinfo is None   # SQLite: naive

    preview = onboarding.preview_invite(
        user_id=invite_world["joiner"], user_email=JOINER_EMAIL, code=code, now=INVITE_NOW,
    )

    assert preview.expires_at.tzinfo is not None
    assert preview.expires_at.utcoffset() == timedelta(0)
    assert preview.expires_at == datetime(2026, 10, 8, 12, 0, tzinfo=UTC)


def test_preview_already_member_flag(invite_world):
    cid, owner, joiner = invite_world["church_id"], invite_world["owner"], invite_world["joiner"]
    code = _invite(cid, owner)

    def preview(user_id, email):
        return onboarding.preview_invite(user_id=user_id, user_email=email, code=code, now=INVITE_NOW)

    assert preview(joiner, JOINER_EMAIL).already_member is False
    assert preview(owner, "owner@example.com").already_member is True

    # Consumed by the joiner, who is a member: check 4's exception, previews normally.
    _update_invite(code, accepted_at=datetime(2026, 9, 30, 12, 0), accepted_by=joiner)
    add_membership(joiner, cid, "member")
    assert preview(joiner, JOINER_EMAIL).already_member is True

    # Removed from the church: the old link is "used", so a removal cannot be undone with it.
    remove_membership(joiner, cid)
    with pytest.raises(Rejected) as exc:
        preview(joiner, JOINER_EMAIL)
    assert exc.value.details == {"reason": "used"}
