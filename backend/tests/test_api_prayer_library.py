"""GET and PUT /church/prayer-library and POST
/church/prayer-library/voice-profile-draft over HTTP (prayer library spec
2026-09-26, "API (slice 6a)" and Testing; 6a spec, API rows; slice 6a-3b):
every member reads the library, owners and admins replace it and draft a
voice profile from it; the draft costs one `ai` token, after the role check;
the routes are church-isolated. The AI is a FakeAI (no test reaches OpenAI)."""
import typing

import pytest

import prayer_library
from api import ratelimit
from api.routes.prayer_library import PrayerType
from domain_errors import Busy, NotConfigured, UpstreamError, UpstreamTimeout
from integrations import openai_client
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

OWNER = "owner@example.com"
ADMIN = "admin@example.com"
MEMBER = "member@example.com"
PATH = "/church/prayer-library"
DRAFT = "/church/prayer-library/voice-profile-draft"
CONFESSION = "Merciful God, we confess that we have not loved you with our whole heart."


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def people(make_user):
    """Each user's id by email (the rate-limit tests charge a user's bucket)."""
    return {email: make_user(email=email) for email in (OWNER, ADMIN, MEMBER)}


@pytest.fixture
def church(people, make_church):
    cid = make_church(name="Grace", owner_user_id=people[OWNER])
    add_membership(people[ADMIN], cid, "admin")
    add_membership(people[MEMBER], cid, "member")
    return cid


def _error(r) -> dict:
    error = dict(r.json()["error"])
    error.pop("request_id")
    return error


def _install(reply="A warm, plain voice.", **kw) -> openai_client.FakeAI:
    fake = openai_client.FakeAI(reply=reply, **kw)
    openai_client.set_ai_for_tests(fake)
    return fake


def _put(client, church, prayers, profile="", email=ADMIN):
    return client.put(PATH, json={"prayers": prayers, "voice_profile": profile}, headers=church_headers(email, church))


def test_a_member_reads_the_library_and_may_not_change_it_or_draft(client, church):
    _put(client, church, [{"type": "prayer_of_confession", "text": CONFESSION}], "Warm and plain.")
    r = client.get(PATH, headers=church_headers(MEMBER, church))
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["can_edit"], body["voice_profile"]) == (False, "Warm and plain.")
    assert [(p["type"], p["text"]) for p in body["prayers"]] == [("prayer_of_confession", CONFESSION)]
    assert client.get(PATH, headers=church_headers(ADMIN, church)).json()["can_edit"] is True
    role_403 = (403, {"code": "forbidden", "message": "Only church admins can do this."})
    r = _put(client, church, [], email=MEMBER)
    assert (r.status_code, _error(r)) == role_403
    fake = _install()
    r = client.post(DRAFT, headers=church_headers(MEMBER, church))
    assert (r.status_code, _error(r)) == role_403
    assert fake.calls == []
    assert len(client.get(PATH, headers=church_headers(OWNER, church)).json()["prayers"]) == 1


def test_a_save_over_http_never_logs_a_prayer_or_the_profile(client, church, caplog):
    sentinel = "SENTINEL-PRAYER-WORDS"
    caplog.set_level("DEBUG")
    r = _put(client, church, [{"type": "benediction", "text": f"Go in peace. {sentinel} one."}], f"{sentinel} two.")
    assert r.status_code == 200, r.text
    assert client.get(PATH, headers=church_headers(MEMBER, church)).status_code == 200
    assert all(sentinel not in r.getMessage() and sentinel not in str(r.args) for r in caplog.records)


def test_an_admin_replaces_the_library_and_a_retried_save_keeps_one_copy(client, church):
    r = _put(client, church, [{"type": "benediction", "text": " Go in peace.\r\n"},
                              {"type": "other", "text": "Bless this meal."}], " Warm. ")
    assert r.status_code == 200, r.text
    saved = r.json()
    assert [(p["type"], p["text"]) for p in saved["prayers"]] == [("benediction", "Go in peace."),
                                                                  ("other", "Bless this meal.")]
    assert (saved["voice_profile"], saved["can_edit"]) == ("Warm.", True)
    assert all(p["id"] and p["added_at"].endswith("Z") for p in saved["prayers"])
    assert client.get(PATH, headers=church_headers(MEMBER, church)).json()["prayers"] == saved["prayers"]
    kept, dropped = saved["prayers"]
    again = [{"id": kept["id"], "type": "benediction", "text": "Go in peace. Amen."},
             {"type": "opening_prayer", "text": "Gracious God."}]
    first, second = (_put(client, church, again, "Warm.", email=OWNER).json() for _ in range(2))
    assert [p["text"] for p in second["prayers"]] == ["Go in peace. Amen.", "Gracious God."]
    assert (second["prayers"][0]["id"], second["prayers"][0]["added_at"]) == (kept["id"], kept["added_at"])
    assert dropped["id"] not in {p["id"] for p in second["prayers"]}
    stored = churches.get_church(church)["settings"]["prayer_library"]
    assert stored == {"prayers": second["prayers"], "voice_profile": "Warm."}


@pytest.mark.parametrize("prayers, profile, field, message", [
    ([{"type": "benediction", "text": "  "}], "", "prayers.0.text", "Prayer text is required."),
    ([{"type": "benediction", "text": "x" * 6_001}], "", "prayers.0.text",
     "This prayer is too long (6,000 characters at most)."),
    ([{"type": "", "text": "Go."}], "", "prayers.0.type", "Choose a prayer type."),
    ([{"type": "benediction", "text": "Go."}] * 31, "", "prayers", "You can keep up to 30 prayers."),
    ([], "x" * 2_001, "voice_profile", "The voice profile is too long (2,000 characters at most)."),
])
def test_each_refusal_names_its_field_and_nothing_is_saved(client, church, prayers, profile, field, message):
    r = _put(client, church, prayers, profile)
    assert (r.status_code, _error(r)) == (422, {"code": "invalid_request", "message": message,
                                                "fields": {field: message}})
    assert "prayer_library" not in churches.get_church(church)["settings"]


@pytest.mark.parametrize("body, fields", [
    ({"prayers": []}, {"voice_profile": "Required."}),
    ({"prayers": [], "voice_profile": "", "extra": 1}, {"extra": "Not a valid value."}),
    ({"prayers": [{"type": "benediction", "text": "Go.", "added_at": "x"}], "voice_profile": ""},
     {"prayers.0.added_at": "Not a valid value."}),
    ({"prayers": [{"type": "benediction", "text": "x" * 20_001}], "voice_profile": ""},
     {"prayers.0.text": "Too long (max 20000 characters)."}),
    ({"prayers": [{"id": "x" * 65, "type": "benediction", "text": "Go."}], "voice_profile": ""},
     {"prayers.0.id": "Too long (max 64 characters)."}),
    ({"prayers": [{"type": "benediction", "text": "Go."}] * 101, "voice_profile": ""},
     {"prayers": "Not a valid value."}),
    ({"prayers": [], "voice_profile": "x" * 20_001}, {"voice_profile": "Too long (max 20000 characters)."}),
])
def test_a_malformed_body_is_pydantics_422(client, church, body, fields):
    r = client.put(PATH, json=body, headers=church_headers(ADMIN, church))
    assert (r.status_code, _error(r)) == (422, {"code": "invalid_request", "message": "The request was not valid.",
                                                "fields": fields})


def test_an_admin_drafts_a_profile_from_the_saved_prayers_and_it_is_not_stored(client, church):
    _put(client, church, [{"type": "prayer_of_confession", "text": CONFESSION}], "Mine.")
    fake = _install(reply=" A warm, plain voice. ")
    r = client.post(DRAFT, headers=church_headers(ADMIN, church))
    assert (r.status_code, r.json()) == (200, {"draft": "A warm, plain voice."})
    (call,) = fake.calls
    assert CONFESSION in call["messages"][1]["content"]
    assert client.get(PATH, headers=church_headers(ADMIN, church)).json()["voice_profile"] == "Mine."


def test_thirty_prayers_of_six_thousand_characters_draft_with_no_422(client, church):
    prayers = [{"type": "other", "text": ("Holy God, hear us. " * 400)[:6_000]} for _ in range(30)]
    assert _put(client, church, prayers).status_code == 200
    fake = _install()
    r = client.post(DRAFT, headers=church_headers(OWNER, church))
    assert r.status_code == 200, r.text
    content = "".join(m["content"] for m in fake.calls[0]["messages"])
    assert len(content) <= 24_000 and content.count("<<<PRAYER ") == 30


def test_with_no_saved_prayers_the_draft_is_a_422(client, church):
    fake = _install()
    r = client.post(DRAFT, headers=church_headers(ADMIN, church))
    assert (r.status_code, _error(r)) == (422, {"code": "invalid_request",
                                                "message": "Add at least one prayer and save it first."})
    assert fake.calls == []


@pytest.mark.parametrize("fake_kw, status, code", [
    ({"available": False}, 503, "ai_not_configured"),
    ({"error": Busy("x", code="ai_busy")}, 503, "ai_busy"),
    ({"error": UpstreamTimeout("x", code="ai_timeout")}, 504, "ai_timeout"),
    ({"error": UpstreamError("x", code="ai_upstream_error")}, 502, "ai_upstream_error"),
    ({"error": NotConfigured("x", code="ai_not_configured")}, 503, "ai_not_configured"),
])
def test_each_ai_failure_has_its_status(client, church, fake_kw, status, code):
    _put(client, church, [{"type": "benediction", "text": "Go in peace."}])
    _install(**fake_kw)
    r = client.post(DRAFT, headers=church_headers(ADMIN, church))
    assert (r.status_code, r.json()["error"]["code"]) == (status, code)
    assert r.json()["error"]["message"] != "x"                         # this app's words, never upstream text


def test_the_draft_costs_one_ai_token_even_when_refused(client, church, people, limiter_clock):
    _put(client, church, [{"type": "benediction", "text": "Go in peace."}])
    fake = _install()
    for _ in range(38):
        ratelimit.consume("ai", user_id=people[ADMIN], church_id=church)
    assert client.post(DRAFT, headers=church_headers(ADMIN, church)).status_code == 200      # the 39th token
    _put(client, church, [])
    assert client.post(DRAFT, headers=church_headers(ADMIN, church)).status_code == 422      # the 40th
    r = client.post(DRAFT, headers=church_headers(ADMIN, church))
    assert (r.status_code, r.json()["error"]["code"], r.headers["Retry-After"]) == (429, "rate_limited", "15")
    assert len(fake.calls) == 1


def test_a_member_is_refused_before_a_token_is_spent(client, church, people, limiter_clock):
    for _ in range(40):
        ratelimit.consume("ai", user_id=people[MEMBER], church_id=church)
    r = client.post(DRAFT, headers=church_headers(MEMBER, church))
    assert (r.status_code, _error(r)) == (403, {"code": "forbidden", "message": "Only church admins can do this."})


def test_the_prayer_library_routes_are_isolated_between_churches(client, isolation_world):
    world = isolation_world
    _install()
    assert_church_isolated(client, "GET", PATH, world=world)
    assert_church_isolated(client, "PUT", PATH, world=world,
                           json={"prayers": [{"type": "benediction", "text": "Go."}], "voice_profile": ""})
    assert_church_isolated(client, "POST", DRAFT, world=world)
    assert "prayer_library" not in churches.get_church(world.church_b)["settings"]
    assert [p["text"] for p in churches.get_church(world.church_a)["settings"]["prayer_library"]["prayers"]] == ["Go."]


def test_the_prayer_types_are_the_readers_own():
    assert typing.get_args(PrayerType) == prayer_library.PRAYER_TYPES
