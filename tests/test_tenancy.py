import uuid
from datetime import datetime, timezone

from db import session_scope
from db.models import Church
from repos.churches import create_church
from tenancy import (
    validate_active_church, require_active_church, set_active_church,
    clear_all_church_state, is_admin,
    CHURCH_SCOPED_STATE_KEYS, CHURCH_SCOPED_STATE_PREFIXES,
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


def test_require_active_church_ignores_forged_session_value(tmp_db, make_user):
    owner = make_user(email="o@x.com")
    cid = create_church(name="First", timezone="UTC", owner_user_id=owner)
    state = {"active_church_id": uuid.uuid4()}       # forged: not the user's church
    out = require_active_church(owner, state=state)
    assert out["church_id"] == cid                   # fell back to real membership
    assert state["active_church_id"] == cid          # session corrected server-side
    assert state["active_church_role"] == "owner"


def test_require_active_church_zero_church_returns_none_and_clears(tmp_db, make_user):
    user = make_user(email="lonely@x.com")
    state = {"active_church_id": uuid.uuid4(), "_cached_all_hymns": {"x": 1}}
    out = require_active_church(user, state=state)
    assert out is None
    assert "_cached_all_hymns" not in state          # church-scoped state cleared


def test_set_active_church_writes_selector_keys():
    state = {}
    set_active_church(uuid.uuid4(), name="Grace", role="admin", state=state)
    assert state["active_church_name"] == "Grace"
    assert state["active_church_role"] == "admin"


def test_clear_all_church_state_pops_scoped_and_prefixed_keys():
    state = {
        "_cached_all_hymns": 1,
        "liturgy_opening": "x",   # prefix match
        "opening_man": "y",       # exact match
        "keep_me": "stays",
    }
    clear_all_church_state(state)
    assert state == {"keep_me": "stays"}


def test_is_admin():
    assert is_admin("owner") is True
    assert is_admin("admin") is True
    assert is_admin("member") is False
    assert is_admin(None) is False


def test_church_scoped_keys_cover_known_state():
    for k in ("_cached_all_hymns", "scripture_hymns", "custom_elements", "include_communion"):
        assert k in CHURCH_SCOPED_STATE_KEYS
    assert "liturgy_" in CHURCH_SCOPED_STATE_PREFIXES
