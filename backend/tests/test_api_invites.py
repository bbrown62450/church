"""POST /invites/preview and POST /invites/accept over HTTP (S API, Testing
`test_api_invites.py`; AC7, AC9).

test_usecase_onboarding.py covers every check, their order, the role clamp and
the accept semantics. These tests pin the HTTP layer: the guard, the statuses,
the exact bodies, X-Church-Id being ignored, and that neither the invite code
nor the caller's email reaches a log line, including the traceback of an
unhandled database error (clarification 37).
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from db import get_engine, session_scope
from db.models import Church, Invite
from repos.invites import create_invite, get_invite_by_code
from repos.memberships import get_role
from tests.api_helpers import auth_headers, church_headers, make_api_client

OWNER = "owner@example.com"
JOINER = "joiner@example.com"
BOUND = "bound@example.com"
UNKNOWN_CODE = "no-such-invite-code"
BLANK = "Enter an invite code, or open your invite link again."
ROUTES = ["preview", "accept"]
REJECTIONS = [
    pytest.param("unknown", "Invalid invite code.", id="unknown"),
    pytest.param("revoked", "This invite has been revoked.", id="revoked"),
    pytest.param("expired", "This invite has expired.", id="expired"),
    pytest.param("used", "This invite has already been used.", id="used"),
    pytest.param("church_unavailable", "This church is no longer available.", id="church_unavailable"),
    pytest.param("email_mismatch", "This invite was issued for a different email address.",
                 id="email_mismatch"),
]


@dataclass(frozen=True)
class World:
    client: TestClient
    church_id: uuid.UUID          # "Grace", owned by OWNER
    owner_id: uuid.UUID
    joiner_id: uuid.UUID          # JOINER: signed up, a member of nothing

    def invite(self, **kwargs) -> str:
        """A Grace invite from OWNER (code-only and single-use unless kwargs say otherwise)."""
        return create_invite(church_id=self.church_id, created_by=self.owner_id, **kwargs)

    def post(self, route: str, code: str, *, headers: dict[str, str] | None = None):
        return self.client.post(f"/invites/{route}", headers=headers or auth_headers(JOINER),
                                json={"code": code})


@pytest.fixture
def world(tmp_db, make_user, make_church) -> World:
    owner_id = make_user(email=OWNER)
    church_id = make_church(name="Grace", owner_user_id=owner_id)
    joiner_id = make_user(email=JOINER)    # the token's email resolves to this same user id
    return World(client=make_api_client(), church_id=church_id, owner_id=owner_id, joiner_id=joiner_id)


def _rejected_code(reason: str, world: World, make_user) -> str:
    """A code that JOINER's preview or accept rejects with `reason` (checks 1-6)."""
    if reason == "unknown":
        return UNKNOWN_CODE
    if reason == "expired":
        return world.invite(ttl_days=-1)
    if reason == "email_mismatch":
        return world.invite(email=BOUND)
    first = make_user(email="first@example.com") if reason == "used" else None
    code = world.invite()
    with session_scope() as s:
        inv = s.execute(select(Invite).where(Invite.code == code)).scalar_one()
        if reason == "revoked":
            inv.revoked = True
        elif reason == "used":                   # another user accepted it first
            inv.accepted_at = datetime.now(timezone.utc)
            inv.accepted_by = first
        else:                                    # church_unavailable: soft-deleted, the invite left live
            s.get(Church, world.church_id).deleted_at = datetime.now(timezone.utc)
    return code


@pytest.mark.parametrize("route", ROUTES)
def test_requires_token(world, route):
    code = world.invite()
    r = world.client.post(f"/invites/{route}", json={"code": code})
    assert r.status_code == 401, r.text
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("unauthenticated", "Please sign in.")
    assert get_invite_by_code(code)["accepted_at"] is None


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("reason,message", REJECTIONS)
def test_rejection_over_http(world, make_user, route, reason, message):
    code = _rejected_code(reason, world, make_user)
    r = world.post(route, code)
    assert r.status_code == 400, r.text
    error = r.json()["error"]
    assert (error["code"], error["message"], error["details"]) == (
        "invite_rejected", message, {"reason": reason})
    assert "fields" not in error                 # fields only on a 422 (clarification 8)
    assert get_role(world.joiner_id, world.church_id) is None


@pytest.mark.parametrize("route", ROUTES)
def test_blank_code_422_fields_code(world, route):
    for body in ({"code": ""}, {"code": "   "}, {}):
        r = world.client.post(f"/invites/{route}", headers=auth_headers(JOINER), json=body)
        assert r.status_code == 422, (body, r.text)
        error = r.json()["error"]
        assert (error["code"], error["message"], error["fields"]) == (
            "invalid_request", BLANK, {"code": BLANK}), body


def test_preview_keys_exact(world):
    code = world.invite()
    r = world.post("preview", code)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "church_name": "Grace",
        "role": "member",
        "expires_at": r.json()["expires_at"],
        "email_bound": False,
        "already_member": False,
    }
    invite = get_invite_by_code(code)
    for withheld in (code, str(invite["id"]), str(world.church_id), str(world.owner_id), OWNER):
        assert withheld not in r.text            # F §7.4: no id, code, church id or creator
    assert invite["accepted_at"] is None         # read-only
    assert get_role(world.joiner_id, world.church_id) is None

    bound = world.post("preview", world.invite(email=JOINER.upper()))
    assert bound.status_code == 200, bound.text
    assert bound.json()["email_bound"] is True
    assert JOINER not in bound.text.lower()      # nor the bound email


def test_accept_body_shape(world):
    code = world.invite()
    r = world.post("accept", code)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "church": {"id": str(world.church_id), "name": "Grace", "role": "member"},
        "already_member": False,
        "message": "Joined Grace.",
    }
    assert get_role(world.joiner_id, world.church_id) == "member"

    again = world.post("accept", code)           # the same user repeats: a 200 that changes nothing
    assert again.status_code == 200, again.text
    assert again.json() == {
        "church": {"id": str(world.church_id), "name": "Grace", "role": "member"},
        "already_member": True,
        "message": "You're already a member of Grace.",
    }


def test_preview_owner_role_is_admin(world):
    code = world.invite(role="owner")            # no CHECK on invites.role until 6b
    r = world.post("preview", code)
    assert r.status_code == 200, r.text          # clamped, not a response-validation 500
    assert r.json()["role"] == "admin"
    joined = world.post("accept", code)
    assert joined.status_code == 200, joined.text
    assert joined.json()["church"]["role"] == "admin"
    assert get_role(world.joiner_id, world.church_id) == "admin"


def test_preview_expires_at_has_offset(world):
    r = world.post("preview", world.invite())
    assert r.status_code == 200, r.text
    expires_at = r.json()["expires_at"]
    assert expires_at.endswith("Z") or expires_at.endswith("+00:00"), expires_at
    assert timedelta(days=6) < datetime.fromisoformat(expires_at) - datetime.now(timezone.utc) <= timedelta(days=7)


def test_x_church_id_ignored(world, make_church):
    elsewhere = make_church(name="Elsewhere")    # JOINER belongs to neither church
    headers = church_headers(JOINER, elsewhere)
    code = world.invite()
    preview = world.post("preview", code, headers=headers)
    assert preview.status_code == 200, preview.text
    assert preview.json()["church_name"] == "Grace"
    joined = world.post("accept", code, headers=headers)
    assert joined.status_code == 200, joined.text
    assert joined.json()["church"]["id"] == str(world.church_id)
    assert get_role(world.joiner_id, elsewhere) is None


def test_after_accept_get_church_200(world):
    before = world.client.get("/church", headers=church_headers(JOINER, world.church_id))
    assert before.status_code == 403, before.text
    church_id = world.post("accept", world.invite()).json()["church"]["id"]
    r = world.client.get("/church", headers=church_headers(JOINER, uuid.UUID(church_id)))
    assert r.status_code == 200, r.text
    assert r.json() == {"id": church_id, "name": "Grace", "role": "member"}


def test_logs_hold_no_code_or_email(world, caplog):
    caplog.set_level(logging.INFO)
    code = world.invite()
    mismatch = world.invite(email=BOUND)
    assert world.post("preview", code).status_code == 200
    assert world.post("accept", code).status_code == 200
    assert world.post("accept", UNKNOWN_CODE).status_code == 400
    assert world.post("preview", mismatch).status_code == 400
    assert "invite_accepted invite_id=" in caplog.text           # the lines really were captured
    assert "invite_rejected reason=unknown invite_id=none" in caplog.text
    assert "invite_rejected reason=email_mismatch invite_id=" in caplog.text
    for secret in (code, mismatch, UNKNOWN_CODE, JOINER, BOUND):
        assert secret not in caplog.text, secret


def test_db_error_logs_hold_no_code_or_email(world, caplog, monkeypatch):
    """A database error while looking the code up is a 500 whose logged traceback
    carries neither the code nor the email: the engine hides bound parameters
    (clarification 37), and the app logs the method and path only."""
    import repos.invites

    def find_by_code_db_down(code, *_args, **_kwargs):
        with get_engine().connect() as conn:     # a real driver error with the code bound
            conn.execute(text("SELECT id FROM invites_gone WHERE code = :code"), {"code": code})

    monkeypatch.setattr(repos.invites, "find_by_code", find_by_code_db_down)
    caplog.set_level(logging.INFO)
    code = world.invite()
    client = TestClient(world.client.app, raise_server_exceptions=False)
    r = client.post("/invites/accept", headers=auth_headers(JOINER), json={"code": code})
    assert r.status_code == 500, r.text
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert "Unhandled error on POST /invites/accept" in caplog.text
    assert "invites_gone" in caplog.text         # the driver's error text is in the log
    assert "[SQL parameters hidden due to hide_parameters=True]" in caplog.text
    assert code not in caplog.text and JOINER not in caplog.text
    assert get_role(world.joiner_id, world.church_id) is None
