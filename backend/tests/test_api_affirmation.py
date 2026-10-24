"""The Affirmation of Faith over HTTP (affirmation spec, "API changes",
"Data shape"): GET /liturgy/config, saving and opening a service (NULL is
the Apostles' Creed; a PUT without it keeps the saved one), the church
default on GET and PATCH /church (admins only), and the downloads."""
import logging
import uuid
from io import BytesIO

import pytest
from docx import Document
from sqlalchemy import select

import affirmation as af
from db import session_scope
from db.models import Church, Service
from repos.memberships import add_membership
from tests.api_helpers import church_headers, make_api_client

EMAIL = "pastor@example.com"
MEMBER = "member@example.com"
ADMIN = "admin@example.com"
SERVICE = {"service_date_iso": "2026-10-04", "occasion": "World Communion Sunday", "sermon_title": "Living Water"}
DEFAULT = {"include": True, "choice": "apostles", "text": ""}
OWN = "We trust in God the Holy Spirit."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    cid = make_church(name="Grace", owner_user_id=make_user(email=EMAIL))
    add_membership(make_user(email=MEMBER), cid, "member")
    add_membership(make_user(email=ADMIN), cid, "admin")
    return cid


def call(client, method, path, church_id, *, email=EMAIL, json=None, **headers):
    return client.request(method, path, json=json, headers={**church_headers(email, church_id), **headers})


def stored(service_id):
    with session_scope() as s:
        return s.execute(select(Service.affirmation).where(Service.id == uuid.UUID(service_id))).scalar_one()


def test_the_config_has_the_card_and_both_creeds(client, church):
    r = call(client, "GET", "/liturgy/config", church)
    assert r.status_code == 200, r.text
    body = r.json()
    # The outline item is unchanged, so a page from before the card (Affirmation PR B) keeps its row.
    item = next(i for i in body["outline"] if i["key"] == "affirmation_of_faith")
    assert item == {"kind": "landmark", "key": "affirmation_of_faith", "label": "Affirmation of Faith",
                    "value_source": "fixed", "fixed_text": "Apostles' Creed", "anchors_after": ["affirmation_of_faith"]}
    assert body["affirmation"] == {
        "title": "Affirmation of Faith", "toggle_label": "Include Affirmation of Faith",
        "choices": [{"key": "apostles", "label": "Apostles' Creed", "text": af.APOSTLES_CREED, "credit": ""},
                    {"key": "nicene", "label": "Nicene Creed", "text": af.NICENE_CREED, "credit": af.NICENE_CREDIT},
                    {"key": "own", "label": "Your own text", "text": "", "credit": ""}]}


def test_a_service_saved_without_it_opens_and_prints_as_today(client, church):
    created = call(client, "POST", "/services", church, json=SERVICE).json()
    assert stored(created["id"]) is None
    assert created["affirmation"] == DEFAULT
    assert call(client, "GET", f"/services/{created['id']}", church).json()["affirmation"] == DEFAULT


def test_save_open_and_a_put_without_it_keeps_the_saved_choice(client, church):
    nicene = {"include": True, "choice": "nicene", "text": "dropped"}
    created = call(client, "POST", "/services", church, json={**SERVICE, "affirmation": nicene}).json()
    assert created["affirmation"] == {"include": True, "choice": "nicene", "text": ""}
    assert stored(created["id"]) == {"include": True, "choice": "nicene", "text": ""}
    kept = call(client, "PUT", f"/services/{created['id']}", church, json=SERVICE, **{"If-Match": created["saved_at"]})
    assert kept.status_code == 200, kept.text
    assert kept.json()["affirmation"]["choice"] == "nicene"                     # a page from before: kept
    off = call(client, "PUT", f"/services/{created['id']}", church,
               json={**SERVICE, "affirmation": {"include": False, "choice": "own", "text": f"  {OWN}  "}},
               **{"If-Match": kept.json()["saved_at"]})
    assert off.json()["affirmation"] == {"include": False, "choice": "own", "text": OWN}


@pytest.mark.parametrize("bad, field", [
    ({"include": True, "choice": "brief", "text": ""}, "affirmation.choice"),
    ({"include": True, "choice": "own"}, "affirmation.text"),
    ({"include": True, "choice": "own", "text": "x" * 20_001}, "affirmation.text"),
    ({"include": True, "choice": "own", "text": "", "extra": 1}, "affirmation.extra"),
])
def test_a_bad_affirmation_is_a_422_on_its_field(client, church, bad, field):
    r = call(client, "POST", "/services", church, json={**SERVICE, "affirmation": bad})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"]


def test_the_word_file_follows_the_body_and_logs_no_text(client, church, caplog):
    caplog.set_level(logging.INFO)
    def paragraphs(body):
        r = call(client, "POST", "/documents", church, json={"variant": "pastor", "service": body})
        assert r.status_code == 200, r.text
        return [p.text for p in Document(BytesIO(r.content)).paragraphs]
    assert "Apostles' Creed" in paragraphs(SERVICE)                                  # no affirmation: as today
    assert "Affirmation of Faith" not in paragraphs({**SERVICE, "affirmation": {**DEFAULT, "include": False}})
    assert OWN in paragraphs({**SERVICE, "affirmation": {"include": True, "choice": "own", "text": OWN}})
    assert OWN not in caplog.text


def test_the_church_default_reads_as_the_apostles_creed_until_an_admin_sets_it(client, church):
    assert call(client, "GET", "/church", church, email=MEMBER).json()["default_affirmation"] == {
        "choice": "apostles", "text": ""}
    r = call(client, "PATCH", "/church", church, email=ADMIN,
             json={"default_affirmation": {"choice": "own", "text": f" {OWN}\r\n"}})
    assert r.status_code == 200, r.text
    assert r.json()["default_affirmation"] == {"choice": "own", "text": OWN}
    assert call(client, "GET", "/church", church, email=MEMBER).json()["default_affirmation"] == {
        "choice": "own", "text": OWN}
    r = call(client, "PATCH", "/church", church, json={"default_affirmation": {"choice": "nicene", "text": OWN}})
    assert r.json()["default_affirmation"] == {"choice": "nicene", "text": ""}


def test_a_member_cannot_change_the_church_default(client, church):
    call(client, "PATCH", "/church", church, json={"default_affirmation": {"choice": "nicene", "text": ""}})
    r = call(client, "PATCH", "/church", church, email=MEMBER,
             json={"default_affirmation": {"choice": "own", "text": OWN}})
    assert r.status_code == 403, r.text
    assert r.json()["error"]["message"] == "Only church admins can do this."
    with session_scope() as s:
        settings = s.get(Church, church).settings
    assert settings["default_affirmation"] == {"choice": "nicene", "text": ""}


def test_own_text_for_the_default_must_not_be_blank(client, church):
    r = call(client, "PATCH", "/church", church, json={"default_affirmation": {"choice": "own", "text": " \n "}})
    assert r.status_code == 422, r.text
    assert r.json()["error"]["fields"] == {"default_affirmation.text": "Type your church's own text, or choose a creed."}


def test_the_published_schema_shows_the_new_api_without_a_sign_in(client):
    """The after-deploy check (README "Before 0010_services_affirmation", step 4):
    /openapi.json needs no sign-in and names ServiceAffirmation."""
    r = client.get("/openapi.json")
    assert r.status_code == 200, r.text
    assert "ServiceAffirmation" in r.json()["components"]["schemas"]
