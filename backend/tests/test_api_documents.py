"""POST /documents (slice 5a spec, API; Testing `test_api_documents.py`;
acceptance criteria 1, 2, 10; F §1.9)."""
import uuid
from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

import worship_service
from api import settings as settings_mod
from db import session_scope
from db.models import Hymn
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
ALLOWED_ORIGIN = "https://church.example.app"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
HYMN_GONE = "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."
SERVICE = {
    "service_date_iso": "2026-10-04",
    "occasion": "World Communion Sunday",
    "scriptures": ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
    "hymns": {"opening": {"hymn_id": None, "title": "Old Favorite", "number": 12, "hymnal": "PH1990"},
              "response": None, "closing": None},
    "hymnal": None,
    "liturgy": {"call_to_worship": "Leader: Come. People: We come.", "prayers_of_the_people": "We pray."},
    "sermon_title": "Living Water",
    "selected_ot_ref": "",
    "selected_nt_ref": "",
    "include_communion": True,
    "custom_elements": [{"label": "Anthem", "text": "Choir", "insert_after": "sermon"}],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def post(client, church_id, body, email=EMAIL, **headers):
    return client.post("/documents", json=body, headers={**church_headers(email, church_id), **headers})


def lines(content: bytes) -> list[str]:
    return [p.text for p in Document(BytesIO(content)).paragraphs]


def test_both_copies_download_with_the_file_headers(client, church):
    for variant, name in (("bulletin", "worship_October_04_2026.docx"),
                          ("pastor", "worship_pastor_October_04_2026.docx")):
        r = post(client, church, {"variant": variant, "service": SERVICE})
        assert r.status_code == 200, r.text
        assert r.content[:2] == b"PK"
        assert r.headers["content-type"] == DOCX
        assert r.headers["content-disposition"] == f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}"
        assert r.headers["cache-control"] == "no-store"
        text = lines(r.content)
        assert "Sermon Title" in text and "Living Water" in text
        assert ("Prayers of the People" in text) is (variant == "pastor")
        assert "First Reading" in text and "Old Testament Reading" not in text
        assert text[text.index("First Hymn") + 1] == "Old Favorite — #12"


def test_the_filename_header_is_readable_cross_origin(tmp_db, church, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    try:
        r = post(make_api_client(), church, {"variant": "bulletin", "service": SERVICE}, Origin=ALLOWED_ORIGIN)
    finally:
        settings_mod.get_settings.cache_clear()
    assert r.status_code == 200, r.text
    assert r.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "content-disposition" in {h.strip().lower() for h in r.headers["access-control-expose-headers"].split(",")}


def test_any_member_may_download(client, church, make_user):
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    r = post(client, church, {"variant": "pastor", "service": SERVICE}, email="member@example.com")
    assert r.status_code == 200, r.text


def test_only_members_and_only_the_church_s_hymns(client, isolation_world):
    world = isolation_world
    assert_church_isolated(client, "POST", "/documents", world=world, json={"variant": "bulletin", "service": SERVICE})
    with session_scope() as s:
        theirs = Hymn(church_id=world.church_b, hymnal="GG2013", title="Their Hymn", number=1)
        s.add(theirs)
        s.flush()
        theirs_id = str(theirs.id)
    for hymn_id in (theirs_id, str(uuid.uuid4())):
        body = {"variant": "bulletin", "service": {**SERVICE, "hymns": {
            "opening": None, "response": {"hymn_id": hymn_id, "title": "Their Hymn", "number": 1, "hymnal": None}}}}
        r = post(client, world.church_a, body, email=world.a)
        assert r.status_code == 404, r.text
        error = r.json()["error"]
        assert (error["code"], error["message"], error["details"]) == (
            "not_found", HYMN_GONE, {"field": "hymns.response.hymn_id"})


@pytest.mark.parametrize("change, field", [
    ({"variant": "secretary"}, "variant"),
    ({"service": {**SERVICE, "service_date_iso": "2026-02-30"}}, "service.service_date_iso"),
    ({"service": {**SERVICE, "service_date_iso": "2026-10-04T00:00:00"}}, "service.service_date_iso"),
    ({"service": {**SERVICE, "extra": 1}}, "service.extra"),
    ({"service": {**SERVICE, "custom_elements": [{"label": "A", "text": "", "insert_after": "bogus"}]}},
     "service.custom_elements.0.insert_after"),
    ({"service": {**SERVICE, "occasion": "x" * 301}}, "service.occasion"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, change, field):
    r = post(client, church, {"variant": "bulletin", "service": SERVICE, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"], r.text


def test_a_blank_custom_label_is_the_usecase_s_422(client, church):
    body = {"variant": "bulletin", "service": {**SERVICE, "custom_elements": [
        {"label": "  ", "text": "Words", "insert_after": "end"}]}}
    r = post(client, church, body)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"custom_elements.0.label": "Give each custom element a label."}


def test_characters_a_word_file_cannot_hold_are_cleaned_not_a_500(client, church):
    """A vertical tab (Word's soft line break, pasted) or a form feed becomes a
    line break; a NUL or another control character is dropped (clarification 19)."""
    service = {**SERVICE, "liturgy": {"opening_prayer": "a\x0bb\x00c"}, "sermon_title": "Living\x0cWater\x1f"}
    r = post(client, church, {"variant": "bulletin", "service": service})
    assert r.status_code == 200, r.text
    text = lines(r.content)
    assert text[text.index("Opening Prayer") + 1] == "a\nbc"
    assert text[text.index("Sermon Title") + 1] == "Living\nWater"


def test_a_label_of_only_a_nul_is_the_blank_label_422(client, church):
    body = {"variant": "bulletin", "service": {**SERVICE, "custom_elements": [
        {"label": "\x00", "text": "Words", "insert_after": "end"}]}}
    r = post(client, church, body)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"custom_elements.0.label": "Give each custom element a label."}


def test_without_python_docx_it_is_a_logged_500(tmp_db, church, monkeypatch):
    monkeypatch.setattr(worship_service, "Document", None)
    client = make_api_client()
    client = TestClient(client.app, raise_server_exceptions=False)
    r = post(client, church, {"variant": "bulletin", "service": SERVICE})
    assert r.status_code == 500
    error = r.json()["error"]
    assert (error["code"], error["message"]) == ("internal_error", "Something went wrong.")
    assert error["request_id"]
