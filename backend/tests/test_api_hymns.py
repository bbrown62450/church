"""GET /hymns (slice 3 spec, API row 2, Models `HymnOut`, API notes "ordering"
and `q`, Backend 3.3; Testing `test_api_hymns.py`, GZip, postgres; AC1, AC8,
AC16, AC20). Includes the `HymnOut` mapping test that 6b's port ledger names
for Streamlit's hymn_display_from_flat."""
import uuid

import pytest
from sqlalchemy import delete

from api import settings as settings_mod
from db import session_scope
from db.models import Church, Hymn, HymnUsage, User
from repos import churches
from repos.memberships import add_membership
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    auth_headers,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
ALLOWED_ORIGIN = "https://church.example.app"


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def church(make_user, make_church):
    return make_church(name="Grace", owner_user_id=make_user(email=EMAIL))


def add(church_id, title, number=None, hymnal="GG2013", **columns):
    with session_scope() as s:
        row = Hymn(church_id=church_id, hymnal=hymnal, title=title, number=number, **columns)
        s.add(row)
        s.flush()
        return str(row.id)


def get(client, church_id, email=EMAIL, **params):
    r = client.get("/hymns", params=params, headers=church_headers(email, church_id))
    assert r.status_code == 200, r.text
    return r.json()


def listed(body):
    return [(h["hymnal"], h["number"], h["title"]) for h in body["items"]]


def test_ordering_is_hymnal_number_nulls_last_title_id(client, church):
    add(church, "Zion", 5, hymnal="PH1990")
    add(church, "b no number")
    add(church, "Holy", 2)
    add(church, "A no number")
    add(church, "Abide", 10)
    body = get(client, church, limit=2000)
    assert listed(body) == [("GG2013", 2, "Holy"), ("GG2013", 10, "Abide"), ("GG2013", None, "A no number"),
                            ("GG2013", None, "b no number"), ("PH1990", 5, "Zion")]
    assert (body["total"], body["limit"], body["offset"]) == (5, 2000, 0)


def test_hymnal_filter_unknown_code_and_a_code_off_the_pattern(client, church):
    add(church, "Holy", 1)
    add(church, "Doxology", 1, hymnal="PH 1990")          # breaks HymnalCode's pattern
    assert listed(get(client, church, hymnal="PH 1990")) == [("PH 1990", 1, "Doxology")]
    assert get(client, church, hymnal="UNKNOWN") == {"items": [], "total": 0, "limit": 50, "offset": 0}


def test_q_matches_number_or_title_with_percent_and_underscore_escaped(client, church):
    add(church, "Joy to the World", 134)
    add(church, "Psalm 134", 900)
    add(church, "100% Sure", 1)
    add(church, "snake_case", 2)
    add(church, "snakeXcase", 3)
    assert {h["number"] for h in get(client, church, q="134")["items"]} == {134, 900}
    assert [h["title"] for h in get(client, church, q="JOY")["items"]] == ["Joy to the World"]
    assert [h["title"] for h in get(client, church, q="100%")["items"]] == ["100% Sure"]
    assert [h["title"] for h in get(client, church, q="e_c")["items"]] == ["snake_case"]


def test_a_30_digit_q_is_200_and_a_6_digit_q_still_matches_numbers(client, church):
    add(church, "Six digits", 123456)
    assert get(client, church, q="9" * 30)["total"] == 0          # the title branch only: no OverflowError
    assert [h["number"] for h in get(client, church, q="123456")["items"]] == [123456]
    # Owner decision 1: only ASCII digits match numbers ("²" and Arabic-Indic digits
    # pass str.isdigit but int() rejects "²"); both are title searches and 200.
    add(church, "Squared ²", 2)
    assert [h["title"] for h in get(client, church, q="²")["items"]] == ["Squared ²"]
    assert get(client, church, q="١٢٣٤٥٦")["total"] == 0


def test_limit_offset_and_total(client, church):
    for n in range(1, 8):
        add(church, f"Hymn {n}", n)
    assert get(client, church, limit=2000)["total"] == 7
    assert get(client, church, offset=1_000_000)["items"] == []     # the cap itself (owner decision 1)
    page = get(client, church, limit=3, offset=3)
    assert ([h["number"] for h in page["items"]], page["total"]) == ([4, 5, 6], 7)
    r = client.get("/hymns", params={"limit": 2001}, headers=church_headers(EMAIL, church))
    assert r.status_code == 422, r.text
    assert (r.json()["error"]["message"], r.json()["error"]["fields"]) == (
        "The request was not valid.", {"limit": "Not a valid value."})
    for bad in ({"limit": 0}, {"offset": -1}, {"recent_for_date": "2026-10-4"},
                {"recent_for_date": "2026-02-30"}, {"q": "x" * 101}, {"hymnal": "H" * 21},
                {"offset": 1_000_001}):
        r = client.get("/hymns", params=bad, headers=church_headers(EMAIL, church))
        assert r.status_code == 422, (bad, r.text)
        assert r.json()["error"]["fields"], bad


def test_recent_for_date_sets_recent_use_on_and_tolerates_bad_stored_dates(client, church):
    add(church, "Come, Thou Almighty King", 403)
    add(church, "Holy", 1)
    with session_scope() as s:
        for date_iso, title in (("2026-09-27", "come, thou almighty KING"), ("2026-10-1", "Holy"),
                                ("", "Holy"), ("2026-08-02T10:00:00.000-05:00", "Holy")):
            s.add(HymnUsage(church_id=church, date_iso=date_iso, hymn_number=None, hymn_title=title))
    body = get(client, church, recent_for_date="2026-10-04")
    assert {h["title"]: h["recent_use_on"] for h in body["items"]} == {
        "Come, Thou Almighty King": "2026-09-27", "Holy": "2026-08-02"}
    assert all(h["recent_use_on"] is None for h in get(client, church)["items"])
    # Owner decision 1: the window is clamped at the calendar's ends, not a 500.
    for edge in ("9999-12-31", "0001-01-01"):
        assert all(h["recent_use_on"] is None for h in get(client, church, recent_for_date=edge)["items"])


def test_hymn_out_mapping(client, church):
    """Port-ledger target for Streamlit's hymn_display_from_flat (S Testing)."""
    add(church, "  Amazing Grace  ", 378, scripture_refs="Eph 2:8",
        theme='{Grace,"Call to Worship"}', hymnary_link="javascript:alert(1)")
    add(church, None, None)
    items = get(client, church)["items"]
    grace = items[0]
    assert grace == {
        "id": grace["id"], "hymnal": "GG2013", "title": "Amazing Grace", "number": 378,
        "link": "javascript:alert(1)",                   # verbatim: the client decides what is safe
        "scripture_refs": "Eph 2:8", "themes": ["Grace", "Call to Worship"], "recent_use_on": None,
        "text_year": None, "hymnal_count": None, "newer_than_preferred": False,
    }
    blank = items[1]
    assert (blank["title"], blank["number"], blank["themes"], blank["link"]) == ("", None, [], None)


def test_newer_than_preferred_follows_the_church_rubric(client, church):
    add(church, "Newer", 1, text_year=1985, hymnal_count=40)
    add(church, "Older", 2, text_year=1826, hymnal_count=1322)
    add(church, "Unknown", 3)

    def flags():
        return {h["title"]: (h["text_year"], h["hymnal_count"], h["newer_than_preferred"])
                for h in get(client, church)["items"]}

    assert flags() == {"Newer": (1985, 40, True), "Older": (1826, 1322, False),
                       "Unknown": (None, None, False)}
    churches.update_church_rubric(church, {"prefer_before_year": 1800})
    assert flags()["Older"] == (1826, 1322, True)
    stored = churches.get_church(church)["settings"]
    churches.update_church(church, settings={**stored, "rubric": {"prefer_before_year": "x"}})
    assert flags()["Newer"][2] is True and flags()["Older"][2] is False     # invalid: the default 1970


def test_isolation_and_every_role(client, isolation_world, make_user):
    world = isolation_world
    add(world.church_a, "A's hymn", 1)
    add(world.church_b, "B's hymn", 1)
    assert_church_isolated(client, "GET", "/hymns", world=world)
    add(world.church_b, "B's own hymnal", 2, hymnal="BONLY")
    own_code = client.get("/hymns", params={"hymnal": "BONLY"}, headers=church_headers(world.a, world.church_a))
    no_code = client.get("/hymns", params={"hymnal": "NOSUCH"}, headers=church_headers(world.a, world.church_a))
    assert (own_code.status_code, own_code.json()) == (no_code.status_code, no_code.json()) == (
        200, {"items": [], "total": 0, "limit": 50, "offset": 0})
    assert [h["title"] for h in get(client, world.church_a, email=world.a)["items"]] == ["A's hymn"]
    for role in ("admin", "member"):
        email = f"{role}@example.com"
        add_membership(make_user(email=email), world.church_a, role)
        assert get(client, world.church_a, email=email)["total"] == 1
    assert client.get("/hymns").status_code == 401


def test_a_whole_hymnal_is_gzipped_with_cors_and_request_id(tmp_db, church, monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", ALLOWED_ORIGIN)
    settings_mod.get_settings.cache_clear()
    try:
        client = make_api_client()
        for n in range(1, 301):
            add(church, f"A long enough hymn title number {n}", n, scripture_refs="Psalm 23")
        r = client.get("/hymns", params={"limit": 2000},
                       headers={**church_headers(EMAIL, church), "Accept-Encoding": "gzip",
                                "Origin": ALLOWED_ORIGIN})
        assert r.status_code == 200
        assert r.headers["content-encoding"] == "gzip"
        assert r.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
        assert r.headers["x-request-id"]
        assert r.json()["total"] == 300                          # the client decoded it
        small = client.get("/hymns", params={"limit": 1}, headers={**church_headers(EMAIL, church),
                                                                  "Accept-Encoding": "gzip"})
        assert "content-encoding" not in small.headers           # under 1024 bytes
    finally:
        settings_mod.get_settings.cache_clear()


@pytest.mark.postgres
def test_ordering_and_q_escaping_on_postgres(pg_db):
    user_id, church_id = uuid.uuid4(), uuid.uuid4()
    with session_scope() as s:
        s.add(User(id=user_id, email=EMAIL))
        s.add(Church(id=church_id, name="PG", timezone="America/New_York", settings={}))
    add_membership(user_id, church_id, "owner")
    add(church_id, "b no number")
    add(church_id, "Holy", 2)
    add(church_id, "A no number")
    add(church_id, "100% Sure", 1)
    add(church_id, "100 Sure", 3)
    client = make_api_client()
    assert client.get("/me", headers=auth_headers(EMAIL)).status_code == 200
    body = get(client, church_id, limit=2000)
    assert listed(body) == [("GG2013", 1, "100% Sure"), ("GG2013", 2, "Holy"), ("GG2013", 3, "100 Sure"),
                            ("GG2013", None, "A no number"), ("GG2013", None, "b no number")]
    assert [h["title"] for h in get(client, church_id, q="100%")["items"]] == ["100% Sure"]
    assert get(client, church_id, q="9" * 30)["total"] == 0
    # Hymnal codes in codepoint order, as Streamlit's sorted(), whatever the
    # database collation (owner decision 1): "Zz" before "ab", so "Zz" is the fallback.
    add(church_id, "Upper", 1, hymnal="Zz")
    add(church_id, "Lower", 1, hymnal="ab")
    with session_scope() as s:
        s.execute(delete(Hymn).where(Hymn.church_id == church_id, Hymn.hymnal == "GG2013"))
    hymnals = client.get("/hymnals", headers=church_headers(EMAIL, church_id)).json()
    assert ([h["code"] for h in hymnals["items"]], hymnals["effective_hymnal"]) == (["Zz", "ab"], "Zz")
