"""POST /bulletin-emails over HTTP (slice 5b spec, API, §Errors and Testing
"test_api_bulletin_emails.py"; slice 5b-2): any member sends; the
Idempotency-Key replays successes, refusals and uncertain sends, never a
second email; the checks run in the spec's order; only requests that reach
Gmail use the `email` bucket; church isolation; the shared address fixture.
Google is tests.fake_google; the files are fixed bytes (the usecase tests
build real ones)."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest

import email_contacts
import google_oauth
from api.deps import get_google_config
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)
from tests.fake_google import REFRESH_TOKEN, FakeGoogle, gmail_error, google_error
from usecases import documents

OWNER = "owner@example.com"
MEMBER = "member@example.com"
CONFIG = google_oauth.GoogleOAuthConfig("client-123", "secret-456", "https://app.example.org/gmail/callback")
SERVICE = {"service_date_iso": "2026-10-04", "occasion": "World Communion Sunday"}
ADDRESSES = json.loads((Path(__file__).parent / "fixtures" / "shared" / "email_addresses.json").read_text(encoding="utf-8"))
SENT = {"sent": True, "recipient_count": 2}


@pytest.fixture
def config():
    return {"value": CONFIG}


@pytest.fixture
def client(tmp_db, config, monkeypatch):
    monkeypatch.setattr(documents, "build_document",
                        lambda *args: documents.DocumentResult(b"FIXED-DOCX", "worship_October_04_2026.docx"))
    monkeypatch.setattr(documents, "build_printed",
                        lambda *args, charge: documents.DocumentResult(b"%PDF-FIXED", "printed_bulletin_October_04_2026.pdf"))
    client = make_api_client()
    client.app.dependency_overrides[get_google_config] = lambda: config["value"]
    return client


@pytest.fixture
def world(client, make_user, make_church):
    church = make_church(name="Grace", owner_user_id=make_user(email=OWNER))
    member = make_user(email=MEMBER)
    add_membership(member, church, "member")
    mary = email_contacts.add_contact(church, name="Mary", email="mary@example.org")["id"]
    office = email_contacts.add_contact(church, name="", email="office@example.org")["id"]
    google_oauth.save_user_token(member, MEMBER, REFRESH_TOKEN)
    return {"church": church, "member": member, "mary": mary, "office": office,
            "google": FakeGoogle(email=MEMBER).install()}


def _body(world, **overrides):
    return {"service": SERVICE, "contact_ids": [world["mary"], world["office"]], "attachments": ["docx"],
            **overrides}


def _post(client, world, body=None, *, key=None, email=MEMBER, church=None):
    headers = church_headers(email, church or world["church"])
    if key is not False:
        headers["Idempotency-Key"] = key or str(uuid.uuid4())
    return client.post("/bulletin-emails", headers=headers, json=_body(world) if body is None else body)


def _error(r) -> tuple:
    error = r.json()["error"]
    return r.status_code, error["code"], error["message"], error.get("fields"), error.get("details")


def _sends(world) -> int:
    return len(world["google"].calls(google_oauth.GMAIL_SEND_URI))


def test_a_member_emails_the_bulletin(client, world):
    r = _post(client, world, _body(world, attachments=["pdf", "docx"], message="See you Sunday.",
                                   translation="nrsvue"))
    assert (r.status_code, r.json()) == (200, SENT)
    (sent,) = world["google"].sent()
    assert (sent["To"], sent["Bcc"]) == (MEMBER, "mary@example.org, office@example.org")
    assert [p.get_filename() for p in sent.iter_attachments()] == [
        "worship_October_04_2026.docx", "printed_bulletin_October_04_2026.pdf"]


def test_the_key_is_required_and_must_be_a_uuid(client, world):
    assert _error(_post(client, world, key=False)) == (422, "invalid_request", "Missing Idempotency-Key header.",
                                                       None, None)
    assert _error(_post(client, world, key="not-a-uuid"))[:3] == (422, "invalid_request",
                                                                 "Idempotency-Key must be a UUID.")
    assert _sends(world) == 0


def test_a_retry_with_the_same_key_replays_and_sends_once(client, world):
    key = str(uuid.uuid4())
    first, again = _post(client, world, key=key), _post(client, world, key=key)
    assert (first.status_code, first.json(), again.status_code, again.json()) == (200, SENT, 200, SENT)
    assert again.headers["Idempotent-Replayed"] == "true"
    r = _post(client, world, _body(world, message="Changed."), key=key)
    assert _error(r)[:2] == (422, "idempotency_mismatch")
    assert _sends(world) == 1


def test_two_requests_with_one_key_at_once_send_once(client, world):
    key = str(uuid.uuid4())
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(lambda _: _post(client, world, key=key), range(2)))
    assert [(r.status_code, r.json()) for r in responses] == [(200, SENT), (200, SENT)]
    assert _sends(world) == 1


@pytest.mark.parametrize("answer, status, code", [
    (httpx.ReadTimeout("slow"), 504, "upstream_timeout"),
    (httpx.Response(503), 502, "gmail_send_failed"),
], ids=["read-timeout", "gmail-5xx"])
def test_an_uncertain_send_is_replayed_never_sent_again(client, world, answer, status, code):
    world["google"].send = answer
    key = str(uuid.uuid4())
    first = _post(client, world, key=key)
    world["google"].send = httpx.Response(200, json={"id": "m"})
    again = _post(client, world, key=key)
    assert (first.status_code, first.json()["error"]["code"]) == (status, code)
    assert first.json()["error"]["details"]["send_uncertain"] is True
    assert (again.status_code, again.json()) == (status, first.json())
    assert again.headers["Idempotent-Replayed"] == "true"
    assert _sends(world) == 1
    assert _post(client, world).status_code == 200                 # a new key ("Send again anyway") sends
    assert _sends(world) == 2


def test_a_send_that_never_left_or_a_slow_refresh_runs_again_with_the_same_key(client, world):
    key = str(uuid.uuid4())
    world["google"].send = httpx.ConnectError("down")
    first = _post(client, world, key=key)
    assert _error(first)[:2] == (502, "gmail_send_failed")
    assert first.json()["error"]["details"] == {"disconnected": False, "send_uncertain": False}
    world["google"].send = httpx.Response(200, json={"id": "m"})
    assert (_post(client, world, key=key).json(), _sends(world)) == (SENT, 2)
    key = str(uuid.uuid4())
    world["google"].refresh = httpx.ReadTimeout("slow")
    assert _error(_post(client, world, key=key))[:4] == (
        504, "upstream_timeout", "Google took too long to respond. Nothing was sent. Try again.", None)
    world["google"].refresh = httpx.Response(200, json={"access_token": "a"})
    assert _post(client, world, key=key).json() == SENT


def test_the_checks_run_in_the_specs_order(client, world):
    r = client.post("/bulletin-emails", json={"nonsense": True})
    assert _error(r)[:2] == (401, "unauthenticated")
    r = _post(client, world, {"service": {}}, key=False)
    assert _error(r)[:3] == (422, "invalid_request", "Missing Idempotency-Key header.")
    r = _post(client, world, _body(world, message="x" * 5001))
    assert _error(r)[3] == {"message": "Too long (max 5000 characters)."}
    r = _post(client, world, _body(world, contact_ids=[str(uuid.uuid4()) for _ in range(201)]))
    assert _error(r)[3] == {"contact_ids": "Not a valid value."}
    many = [email_contacts.add_contact(world["church"], name="", email=f"p{i}@example.org")["id"] for i in range(60)]
    r = _post(client, world, _body(world, contact_ids=many))
    assert _error(r)[:4] == (422, "invalid_request", "You can email at most 50 people at once.",
                             {"recipients": "You can email at most 50 people at once."})
    assert _sends(world) == 0


def test_the_body_and_its_attachments(client, world):
    r = _post(client, world, {**_body(world), "sender": "someone@example.org"})
    assert _error(r)[:2] == (422, "invalid_request")
    body = _body(world)
    del body["attachments"]
    assert _error(_post(client, world, body))[3] == {"attachments": "Required."}
    assert _error(_post(client, world, _body(world, attachments=["zip"])))[3] == {"attachments.0": "Not a valid value."}
    assert _error(_post(client, world, _body(world, attachments=[])))[2:4] == (
        "Choose at least one attachment.", {"attachments": "Choose at least one attachment."})
    assert _sends(world) == 0


def test_only_requests_that_reach_gmail_use_the_hourly_limit(client, world):
    for _ in range(5):
        assert _post(client, world, _body(world, additional_emails=["not an address"])).status_code == 422
        assert _post(client, world, _body(world, contact_ids=[str(uuid.uuid4())])).status_code == 404
    google_oauth.delete_connection(world["member"])
    for _ in range(5):
        assert _post(client, world).status_code == 409                 # not connected
    google_oauth.save_user_token(world["member"], MEMBER, REFRESH_TOKEN)
    key = str(uuid.uuid4())
    for _ in range(5):
        assert _post(client, world, key=key).status_code == 200      # one send, four replays
    for _ in range(9):
        assert _post(client, world).status_code == 200
    r = _post(client, world)
    assert _error(r)[:2] == (429, "rate_limited")
    assert int(r.headers["Retry-After"]) >= 1
    assert _sends(world) == 10


def test_another_churchs_contact_is_not_found_and_nothing_is_sent(client, world, make_church, make_user):
    other = make_church(name="Other", owner_user_id=make_user(email="other@example.com"))
    theirs = email_contacts.add_contact(other, name="Theirs", email="theirs@example.org")["id"]
    r = _post(client, world, _body(world, contact_ids=[world["mary"], theirs]))
    assert _error(r) == (404, "not_found", "One of the selected contacts no longer exists. Refresh the list and try "
                                           "again.", None, {"field": "contact_ids"})
    assert _sends(world) == 0


def test_a_hymn_the_church_no_longer_has_is_not_found(client, world, monkeypatch):
    monkeypatch.undo()                                             # the real build_document
    service = {**SERVICE, "hymns": {"response": {"hymn_id": str(uuid.uuid4()), "title": "Gone", "number": 1}}}
    r = _post(client, world, _body(world, service=service))
    assert _error(r)[:3] + (_error(r)[4],) == (
        404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        {"field": "hymns.response.hymn_id"})
    assert _sends(world) == 0


def test_the_route_is_church_scoped(client, isolation_world):
    assert_church_isolated(client, "POST", "/bulletin-emails", world=isolation_world,
                           json={"service": SERVICE, "additional_emails": ["a@example.org"], "attachments": ["docx"]})


def test_the_shared_address_cases(client, world):
    for raw in ADDRESSES["invalid"]:
        r = _post(client, world, _body(world, contact_ids=[], additional_emails=[raw]))
        assert r.status_code == 422, raw
        assert list(r.json()["error"]["fields"]) == ["additional_emails"], raw
    r = _post(client, world, _body(world, contact_ids=[], additional_emails=[c["raw"] for c in ADDRESSES["valid"]]))
    assert (r.status_code, r.json()["recipient_count"]) == (200, len(ADDRESSES["valid"]))
    assert world["google"].sent()[0]["Bcc"] == ", ".join(c["normalized"] for c in ADDRESSES["valid"])


@pytest.mark.parametrize("setup, expected", [
    (lambda w, c: google_oauth.delete_connection(w["member"]),
     (409, "gmail_not_connected", "Connect your Gmail first, then try again.", None, None)),
    (lambda w, c: setattr(w["google"], "refresh", google_error(400, "invalid_grant")),
     (502, "gmail_send_failed", "Your Gmail connection has expired or was removed. Reconnect Gmail and try again.",
      None, {"disconnected": True, "send_uncertain": False})),
    (lambda w, c: setattr(w["google"], "send", gmail_error(403, "dailyLimitExceeded")),
     (502, "gmail_send_failed", "Gmail's sending limit has been reached. Nothing was sent. Try again later.",
      None, {"disconnected": False, "send_uncertain": False})),
    (lambda w, c: c.update(value=google_oauth.GoogleOAuthConfig("", "", "")),
     (503, "gmail_not_configured", "Per-user Gmail sending isn't configured on this deployment.", None, None)),
], ids=["not-connected", "expired", "limit", "not-configured"])
def test_gmail_errors_never_carry_googles_text(client, world, config, setup, expected):
    setup(world, config)
    r = _post(client, world)
    assert _error(r) == expected
    assert "SECRET-GOOGLE-TEXT" not in r.text


def test_signed_out_is_401(client):
    r = client.post("/bulletin-emails", headers=auth_headers(MEMBER) | {"Authorization": "Bearer nope"}, json={})
    assert _error(r)[:2] == (401, "unauthenticated")
