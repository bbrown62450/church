import uuid

from repos.churches import create_church
from streamlit_tenancy import (
    require_active_church, set_active_church, clear_all_church_state,
    CHURCH_SCOPED_STATE_KEYS, CHURCH_SCOPED_STATE_PREFIXES,
)


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


def test_church_scoped_keys_cover_known_state():
    for k in ("_cached_all_hymns", "scripture_hymns", "custom_elements", "include_communion"):
        assert k in CHURCH_SCOPED_STATE_KEYS
    assert "liturgy_" in CHURCH_SCOPED_STATE_PREFIXES
