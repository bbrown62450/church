import uuid
from datetime import datetime, timezone

from db import session_scope
from db.models import Church
from repos.churches import create_church
from tenancy import (
    validate_active_church, is_admin,
)


def test_validate_returns_role_for_member(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    assert validate_active_church(cid, owner) == {
        "church_id": cid, "name": "First", "role": "owner",
    }


def test_validate_rejects_non_member(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    outsider = make_user(email="out@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    assert validate_active_church(cid, outsider) is None


def test_validate_rejects_soft_deleted_church(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    with session_scope() as s:
        s.get(Church, cid).deleted_at = datetime.now(timezone.utc)
    assert validate_active_church(cid, owner) is None


def test_validate_rejects_forged_and_null_candidates(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    create_church(name="First", timezone="UTC", owner_user_id=owner)
    assert validate_active_church("not-a-uuid", owner) is None   # garbage string
    assert validate_active_church(uuid.uuid4(), owner) is None   # unknown id
    assert validate_active_church(None, owner) is None


def test_validate_accepts_string_uuid_of_real_membership(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    out = validate_active_church(str(cid), owner)   # e.g. from a ?church= param
    assert out["church_id"] == cid and out["role"] == "owner"


def test_is_admin():
    assert is_admin("owner") is True
    assert is_admin("admin") is True
    assert is_admin("member") is False
    assert is_admin(None) is False
