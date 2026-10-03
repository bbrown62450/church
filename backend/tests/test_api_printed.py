"""POST /documents/printed (printed bulletin spec, PR 1): the printed
bulletin as a PDF or a Word file, with the readings' text fetched in the
translation step 1 shows. scripture_fetcher.fetch_part is replaced, so
nothing leaves the machine."""
import logging
from io import BytesIO

import pytest
from docx import Document
from pypdf import PdfReader

import scripture_fetcher
from api import ratelimit
from db import session_scope
from db.models import Church
from repos.memberships import add_membership
from scripture_fetcher import Part
from tests.api_helpers import (  # noqa: F401 (isolation_world is a fixture)
    assert_church_isolated,
    church_headers,
    isolation_world,
    make_api_client,
)

EMAIL = "pastor@example.com"
PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
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
    "include_communion": False,
    "custom_elements": [],
}


@pytest.fixture
def client(tmp_db):
    return make_api_client()


@pytest.fixture
def owner(make_user):
    return make_user(email=EMAIL)


@pytest.fixture
def church(owner, make_church):
    return make_church(name="Example Church", owner_user_id=owner)


@pytest.fixture
def calls(monkeypatch):
    """Every part fetched, as (part, translation); "Isaiah 5:1-7" is unavailable."""
    seen = []

    def fetch_part(part, translation):
        seen.append((part, translation))
        if part.startswith("Isaiah"):
            return Part(part, "unavailable", None)
        return Part(part, "ok", f"Text of {part} ({translation}).\nSecond verse.")

    monkeypatch.setattr(scripture_fetcher, "fetch_part", fetch_part)
    return seen


def post(client, church_id, body, email=EMAIL):
    return client.post("/documents/printed", json=body, headers=church_headers(email, church_id))


def pdf_text(content: bytes) -> str:
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(BytesIO(content)).pages)


def test_the_pdf_downloads_with_the_file_headers_and_the_readings_text(client, church, calls, caplog):
    caplog.set_level(logging.INFO, logger="usecases.documents")
    r = post(client, church, {"format": "pdf", "translation": "kjv", "service": SERVICE})
    assert r.status_code == 200, r.text
    name = "printed_bulletin_October_04_2026.pdf"
    assert r.headers["content-type"] == PDF
    assert r.headers["content-disposition"] == f"attachment; filename=\"{name}\"; filename*=UTF-8''{name}"
    assert r.headers["cache-control"] == "no-store"
    text = pdf_text(r.content)
    assert "Example Church" in text and "*HYMN: #12 “Old Favorite”" in text
    assert "FIRST READING: Isaiah 5:1-7 [Reading text unavailable] NEW TESTAMENT" in text      # no names saved yet
    assert "NEW TESTAMENT READING: Philippians 3:4b-14 Text of Philippians 3:4-14 (kjv). Second verse." in text
    assert "Scripture readings are from the King James Version (KJV)." in text
    assert calls == [("Isaiah 5:1-7", "kjv"), ("Philippians 3:4-14", "kjv")]
    assert "We pray." not in text
    (record,) = [r for r in caplog.records if r.getMessage().startswith("documents.printed")]
    assert "format=pdf" in record.getMessage() and "Living Water" not in record.getMessage()


def test_the_word_file_downloads_too(client, church, calls):
    r = post(client, church, {"format": "docx", "translation": None, "service": SERVICE})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == DOCX
    assert "printed_bulletin_October_04_2026.docx" in r.headers["content-disposition"]
    paragraphs = [p.text for p in Document(BytesIO(r.content)).paragraphs]
    assert "Text of Philippians 3:4-14 (web). Second verse." in paragraphs
    assert {translation for _part, translation in calls} == {"web"}


def test_a_translation_not_offered_here_prints_in_the_church_s(client, church, calls):
    with session_scope() as s:
        s.get(Church, church).settings = {"bible_translation": "asv"}
    for requested in ("esv", "nope", None):                  # no ESV key in tests
        calls.clear()
        r = post(client, church, {"format": "pdf", "translation": requested, "service": SERVICE})
        assert r.status_code == 200, r.text
        assert {translation for _part, translation in calls} == {"asv"}
        assert "American Standard Version (ASV)" in pdf_text(r.content)


def test_no_readings_fetch_nothing(client, church, calls):
    r = post(client, church, {"format": "pdf", "service": {**SERVICE, "scriptures": []}})
    assert r.status_code == 200, r.text
    assert calls == []
    assert "Scripture readings are from" not in pdf_text(r.content)


def test_the_scripture_bucket_is_charged_per_part_and_a_429_fetches_nothing(client, church, owner, calls):
    ratelimit.consume("scripture", user_id=owner, cost=59)
    r = post(client, church, {"format": "pdf", "service": SERVICE})       # two parts, one token left
    assert r.status_code == 429, r.text
    assert r.json()["error"]["code"] == "rate_limited"
    assert calls == []


def test_any_member_and_only_members(client, church, make_user, calls, isolation_world):
    member = make_user(email="member@example.com")
    add_membership(member, church, "member")
    assert post(client, church, {"format": "docx", "service": SERVICE}, email="member@example.com").status_code == 200
    assert_church_isolated(client, "POST", "/documents/printed", world=isolation_world,
                           json={"format": "pdf", "service": SERVICE})


@pytest.mark.parametrize("change, field", [
    ({"format": "html"}, "format"),
    ({"translation": "x" * 21}, "translation"),
    ({"variant": "bulletin"}, "variant"),
    ({"service": {**SERVICE, "service_date_iso": "2026-02-30"}}, "service.service_date_iso"),
])
def test_a_bad_body_is_a_422_naming_the_field(client, church, calls, change, field):
    r = post(client, church, {"format": "pdf", "service": SERVICE, **change})
    assert r.status_code == 422, r.text
    assert field in r.json()["error"]["fields"], r.text
    assert calls == []
