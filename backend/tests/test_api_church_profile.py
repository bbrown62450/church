"""GET /church's profile fields over HTTP (S API row 4, `usecases/church_profile.py`,
Testing `test_api_church_profile.py`; AC6).

GET /church returns ChurchProfileOut: ChurchOut's id, name and role (from
require_church) plus timezone, timezone_valid, bible_translation,
effective_translation and effective_translation_label (from
usecases.church_profile). /me's church items stay ChurchOut.
"""
import pytest

from api.main import create_app
from liturgy_config import DEFAULT_BENEDICTION_FALLBACK as HALVERSON
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    NO_CHURCH_ACCESS,
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
WEB = ("web", "World English Bible (WEB)")


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def no_esv_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)


def _profile(client, church_id, email=EMAIL) -> dict:
    r = client.get("/church", headers=church_headers(email, church_id))
    assert r.status_code == 200, r.text
    return r.json()


def _effective(body: dict) -> tuple[str, str]:
    return body["effective_translation"], body["effective_translation_label"]


def test_new_fields_including_label(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", timezone="America/Chicago",
                      owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "kjv")
    assert _profile(client, cid) == {
        "id": str(cid),
        "name": "Grace",
        "role": "owner",
        "timezone": "America/Chicago",
        "timezone_valid": True,
        "bible_translation": "kjv",
        "effective_translation": "kjv",
        "effective_translation_label": "King James Version (KJV)",
        "default_hymnal": None,
        "effective_hymnal": None,
        "default_benediction": HALVERSON,
    }


def test_timezone_valid_exact_and_case_sensitive(client, make_user, make_church):
    owner = make_user(email=EMAIL)
    cases = [("Eastern", False), ("america/new_york", False), ("America/New_York", True)]
    for timezone, valid in cases:
        cid = make_church(name=f"Church {timezone}", timezone=timezone, owner_user_id=owner)
        body = _profile(client, cid)
        assert (body["timezone"], body["timezone_valid"]) == (timezone, valid), timezone


def test_stored_esv_without_key_effective_web(client, make_user, make_church, monkeypatch):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "esv")
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    body = _profile(client, cid)
    assert body["bible_translation"] == "esv"                # the stored value, unchanged
    assert _effective(body) == WEB

    churches.set_church_translation(cid, "klingon")           # never offered anywhere
    body = _profile(client, cid)
    assert (body["bible_translation"], _effective(body)) == ("klingon", WEB)

    churches.set_church_translation(cid, "esv")
    monkeypatch.setenv("ESV_API_KEY", "test-key")            # control: offered once configured
    body = _profile(client, cid)
    assert _effective(body) == ("esv", "English Standard Version (ESV)")
    assert "test-key" not in str(body)


def test_unset_translation_null_effective_web(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    body = _profile(client, cid)                               # settings == {}: never set
    assert (body["bible_translation"], _effective(body)) == (None, WEB)

    for stored in ("", 7, None):                               # not a non-empty string: unset
        churches.update_church(cid, settings={"bible_translation": stored})
        body = _profile(client, cid)
        assert (body["bible_translation"], _effective(body)) == (None, WEB), stored


def test_assert_church_isolated(client, isolation_world):
    assert_church_isolated(client, "GET", "/church", world=isolation_world)


def test_every_role_200(client, make_user, make_church, no_esv_key):
    cid = make_church(name="Grace", timezone="America/Denver",
                      owner_user_id=make_user(email="owner@example.com"))
    add_membership(make_user(email="admin@example.com"), cid, "admin")
    add_membership(make_user(email="member@example.com"), cid, "member")
    for role in ("owner", "admin", "member"):
        body = _profile(client, cid, email=f"{role}@example.com")
        assert (body["role"], body["timezone"], body["timezone_valid"]) == (
            role, "America/Denver", True), role
        assert _effective(body) == WEB, role


def test_me_church_items_unchanged(client, make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    churches.set_church_translation(cid, "kjv")
    r = client.get("/me", headers=auth_headers(EMAIL))
    assert r.status_code == 200, r.text
    assert r.json()["churches"] == [{"id": str(cid), "name": "Grace", "role": "owner"}]

    schema = create_app().openapi()
    components = schema["components"]["schemas"]
    assert components["MeOut"]["properties"]["churches"]["items"] == {
        "$ref": "#/components/schemas/ChurchOut"}
    assert set(components["ChurchOut"]["properties"]) == {"id", "name", "role"}
    ok = schema["paths"]["/church"]["get"]["responses"]["200"]["content"]["application/json"]
    assert ok["schema"] == {"$ref": "#/components/schemas/ChurchProfileOut"}
    assert set(components["ChurchProfileOut"]["required"]) == {
        "id", "name", "role", "timezone", "timezone_valid", "bible_translation",
        "effective_translation", "effective_translation_label", "default_hymnal", "effective_hymnal",
        "default_benediction"}


def test_church_deleted_after_guard_is_403(client, make_user, make_church, monkeypatch):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    real_get_church = churches.get_church

    def deleted_then_read(church_id, **kwargs):
        churches.soft_delete_church(church_id)       # after require_church passed, before the read
        return real_get_church(church_id, **kwargs)

    monkeypatch.setattr(churches, "get_church", deleted_then_read)
    r = client.get("/church", headers=church_headers(EMAIL, cid))
    assert r.status_code == 403, r.text
    error = dict(r.json()["error"])
    error.pop("request_id")
    assert error == NO_CHURCH_ACCESS


def test_default_benediction_is_the_church_s_or_halverson(client, make_user, make_church):
    """Slice 4 (S API; Backend 5; AC9): "" is a stored value meaning no default.
    Owner, 2026-10-02: the fallback is the full Halverson text, and a saved
    shorthand "Halverson" (the old seed) prints it too."""
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    assert _profile(client, cid)["default_benediction"] == HALVERSON
    assert HALVERSON.startswith("\u201cYou go nowhere by accident.") and HALVERSON.endswith("- Richard Halverson")
    for stored, expected in (("May the Lord bless you and keep you.", "May the Lord bless you and keep you."),
                             ("", ""), (5, HALVERSON), ("Halverson", HALVERSON), (" halverson ", HALVERSON)):
        churches.update_church(cid, settings={"default_benediction": stored})
        assert _profile(client, cid)["default_benediction"] == expected, stored
