"""usecases.onboarding (S Modules added 1b, Rate limits, Testing; slice 1b).

Task 3: create_church and the per-user cap. Tasks 4 and 5 append the invite
preview and accept tests. The cap tests inject `now` and move each church's
created_at to a fixed offset from it, because the repo stamps the real clock.
"""
import logging
import re
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, update

import repos.churches
import repos.hymns
from db import session_scope
from db.models import Church, Membership
from domain_errors import InvalidInput, RateLimited
from repos.churches import get_church, list_user_churches, soft_delete_church
from repos.hymns import list_hymns
from repos.memberships import add_membership
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
