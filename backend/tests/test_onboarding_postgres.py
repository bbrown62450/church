"""Onboarding on real Postgres (slice 1b; S Testing "Backend — onboarding (1b)",
AC8, Risk 3): the accept races and the 700-row seed timing.

Skipped without TEST_DATABASE_URL; CI's backend-postgres job runs them with
`python -m pytest -m postgres -q`. The SQLite fixtures (tmp_db, make_user,
make_church, seed_catalog) cannot be used here, since they bind SQLite: users
are created through GET /me, as a real sign-in does, and churches, invites and
catalog rows through the repos on pg_db's engine (session_scope).

Forcing the race: a barrier inside repos.invites.claim (single-use invites) or
repos.memberships.ensure_membership (reusable invites) holds each request until
both have passed the invite checks, so the second one really takes the
"claim updated 0 rows -> refresh" or "ON CONFLICT DO NOTHING inserted 0 rows"
path, not the sequential `used` / already-a-member path. usecases.onboarding
calls both through module attributes (`invites.claim(...)`), so patching the
module attribute reaches it. A request that never reaches the wrapper leaves
the other one waiting: after 10 s the barrier breaks, BrokenBarrierError
reaches the TestClient and the test errors instead of passing vacuously.
"""
import threading
import time
import uuid
import warnings
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import func, select

import repos.invites
import repos.memberships
from db import session_scope
from db.models import Hymn, HymnCatalog, Invite, Membership
from repos.churches import create_church
from repos.invites import create_invite
from tests.api_helpers import auth_headers

OWNER = "owner@example.com"
ANN = "ann@example.com"
BEN = "ben@example.com"
CATALOG_ROWS = 700
GRACE_MEMBER = {"name": "Grace", "role": "member"}


@pytest.fixture
def pg_client(pg_db):
    from tests.api_helpers import make_api_client

    return make_api_client()


def _user_id(client, email) -> uuid.UUID:
    """Sign `email` in through GET /me (creates the users row, caches the identity)."""
    r = client.get("/me", headers=auth_headers(email))
    assert r.status_code == 200, r.text
    return uuid.UUID(r.json()["user"]["id"])


def _church_with_invite(client, *, reusable: bool) -> tuple[uuid.UUID, str]:
    """Church "Grace" owned by OWNER, and one code-only member invite; returns (church id, code)."""
    owner_id = _user_id(client, OWNER)
    church_id = create_church(name="Grace", timezone="America/New_York", owner_user_id=owner_id)
    code = create_invite(church_id=church_id, created_by=owner_id, reusable=reusable)
    return church_id, code


def _accept_together(client, monkeypatch, module, name, emails, code):
    """POST /invites/accept once per email, both at once. Each request waits at a
    barrier inside `module.name` until the other arrives, then runs the real
    function. Returns (responses in `emails` order, the real function's results)."""
    real = getattr(module, name)
    barrier = threading.Barrier(2)
    results = []

    def together(*args, **kwargs):
        barrier.wait(timeout=10)
        result = real(*args, **kwargs)
        results.append(result)
        return result

    monkeypatch.setattr(module, name, together)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(
            lambda email: client.post("/invites/accept", json={"code": code},
                                      headers=auth_headers(email)),
            emails,
        ))
    return responses, results


def _memberships(church_id, *user_ids) -> list[tuple[uuid.UUID, str]]:
    with session_scope() as s:
        rows = s.execute(
            select(Membership.user_id, Membership.role)
            .where(Membership.church_id == church_id, Membership.user_id.in_(user_ids))
        ).all()
        return [(row.user_id, row.role) for row in rows]


def _invite_stamp(code) -> tuple:
    """(accepted_at, accepted_by) of the invite with `code`."""
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        return inv.accepted_at, inv.accepted_by


@pytest.mark.postgres
def test_two_users_race_single_use(pg_client, monkeypatch):
    """Two users accept one single-use invite at the same moment: exactly one
    joins; the other's claim waits on the row lock, updates 0 rows, and the
    refreshed row names someone else, so it gets 400 `used` (S Accept semantics,
    "Two users racing"; AC8)."""
    church_id, code = _church_with_invite(pg_client, reusable=False)
    ann_id, ben_id = _user_id(pg_client, ANN), _user_id(pg_client, BEN)

    responses, claims = _accept_together(pg_client, monkeypatch, repos.invites, "claim",
                                         [ANN, BEN], code)

    assert sorted(claims) == [False, True]      # both reached claim; one UPDATE matched 0 rows
    assert sorted(r.status_code for r in responses) == [200, 400]
    winner = next(r for r in responses if r.status_code == 200).json()
    loser = next(r for r in responses if r.status_code == 400).json()["error"]
    assert winner["already_member"] is False
    assert winner["message"] == "Joined Grace."
    assert winner["church"] == {"id": str(church_id), **GRACE_MEMBER}
    assert loser["code"] == "invite_rejected"
    assert loser["message"] == "This invite has already been used."
    assert loser["details"] == {"reason": "used"}
    assert "fields" not in loser
    winner_id = ann_id if responses[0].status_code == 200 else ben_id
    assert _memberships(church_id, ann_id, ben_id) == [(winner_id, "member")]
    accepted_at, accepted_by = _invite_stamp(code)
    assert accepted_at is not None
    assert accepted_by == winner_id


@pytest.mark.postgres
@pytest.mark.parametrize("reusable", [False, True], ids=["single_use", "reusable"])
def test_same_user_double_accept(pg_client, monkeypatch, reusable):
    """A double tap: one user sends two accepts at once. Both get 200, one
    membership exists, and exactly one response says `already_member: false`
    (S Accept semantics, "Idempotent for the same user"; AC8).
    Single-use: the second claim updates 0 rows, the refreshed row names the
    caller, and its INSERT ... ON CONFLICT DO NOTHING inserts nothing.
    Reusable (never claimed): the second INSERT waits on the primary key, then
    inserts nothing."""
    church_id, code = _church_with_invite(pg_client, reusable=reusable)
    ann_id = _user_id(pg_client, ANN)
    if reusable:
        module, name = repos.memberships, "ensure_membership"
    else:
        module, name = repos.invites, "claim"

    responses, results = _accept_together(pg_client, monkeypatch, module, name, [ANN, ANN], code)

    if reusable:
        assert sorted(inserted for _role, inserted in results) == [False, True]
    else:
        assert sorted(results) == [False, True]
    assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
    bodies = [r.json() for r in responses]
    assert sorted(b["already_member"] for b in bodies) == [False, True]
    assert sorted(b["message"] for b in bodies) == [
        "Joined Grace.",
        "You're already a member of Grace.",
    ]
    assert [b["church"] for b in bodies] == [{"id": str(church_id), **GRACE_MEMBER}] * 2
    assert _memberships(church_id, ann_id) == [(ann_id, "member")]
    accepted_at, accepted_by = _invite_stamp(code)
    if reusable:
        assert (accepted_at, accepted_by) == (None, None)    # reusable invites are never stamped
    else:
        assert accepted_at is not None
        assert accepted_by == ann_id


def _seed_catalog_rows(n: int) -> None:
    """`n` hymn_catalog rows with every column filled, like the real catalog."""
    with session_scope() as s:
        s.add_all([
            HymnCatalog(
                hymnal="GG2013",
                title=f"Hymn {i}",
                number=i,
                scripture_refs="Psalm 23; John 3:16",
                theme="Praise and thanksgiving",
                hymnary_link=f"https://hymnary.org/text/hymn_{i}",
                audio_url=f"https://example.org/audio/{i}.mp3",
                text_year=1700 + i % 300,
                hymnal_count=i % 60,
            )
            for i in range(1, n + 1)
        ])


@pytest.mark.postgres
def test_create_church_700_row_catalog_under_3s(pg_client):
    """S Risk 3: POST /churches copies the whole catalog (Core bulk insert,
    slice 1b T2) within 3 s on CI Postgres. The time covers the whole request,
    so it is an upper bound on the seed. It is also emitted as a UserWarning:
    `pytest -m postgres -q` captures a print, but prints warnings in its
    "warnings summary", where the PR copies it from (clarification 41).
    Production above 5 s -> switch the Postgres path to INSERT ... SELECT."""
    _seed_catalog_rows(CATALOG_ROWS)
    headers = auth_headers(OWNER)
    assert pg_client.get("/me", headers=headers).status_code == 200   # users row + identity cache

    start = time.perf_counter()
    r = pg_client.post(
        "/churches",
        json={"name": "Timing Church", "timezone": "America/New_York"},
        headers={**headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    elapsed = time.perf_counter() - start

    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["name"], body["role"]) == ("Timing Church", "owner")
    with session_scope() as s:
        n = s.execute(
            select(func.count()).select_from(Hymn).where(Hymn.church_id == uuid.UUID(body["id"]))
        ).scalar_one()
    ms = round(elapsed * 1000)
    warnings.warn(f"hymn seed: {n} rows in {ms} ms", UserWarning)
    assert n == CATALOG_ROWS
    assert elapsed < 3.0, f"POST /churches with a {CATALOG_ROWS}-row catalog took {ms} ms (budget 3000 ms)"
