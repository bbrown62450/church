import json

import pytest
from sqlalchemy import select

from migrate_to_db import (
    detect_truncated_liturgy,
    extract_meta,
    parse_archive_page,
    import_services,
    import_usage,
    import_contacts,
    validate_enrichment,
)
from db import session_scope
from db.models import Contact, Hymn, HymnUsage, Service


# ---- pure helpers -------------------------------------------------------

def test_detect_truncated_liturgy():
    assert detect_truncated_liturgy(None) is False
    assert detect_truncated_liturgy('{"call": "short"}') is False          # short + valid
    assert detect_truncated_liturgy('{"call": "short') is False            # short + invalid
    assert detect_truncated_liturgy('{"a":"' + "x" * 2000 + '"}') is False # long + valid
    assert detect_truncated_liturgy('{"a":"' + "x" * 2000) is True         # long + cut off


def test_extract_meta():
    assert extract_meta({"_sermon_title": "Grace", "_include_communion": True}) == ("Grace", True)
    assert extract_meta({"call": "x"}) == ("", False)
    assert extract_meta(None) == ("", False)


def _archive_page(occasion, saved_at, liturgy=None, service_date=None, truncate=False):
    if truncate:
        liturgy_text = '{"call": "' + "x" * 2100      # invalid JSON, over the 2000 cap
    else:
        liturgy_text = json.dumps(liturgy or {})
    props = {
        "Occasion": {"type": "rich_text", "rich_text": [{"plain_text": occasion}]},
        "Liturgy": {"type": "rich_text", "rich_text": [{"plain_text": liturgy_text}]},
        "Scriptures": {"type": "rich_text", "rich_text": [{"plain_text": "Isaiah 6:1-8"}]},
        "Hymns": {"type": "rich_text", "rich_text": [{"plain_text": "[]"}]},
        "Selected OT": {"type": "rich_text", "rich_text": []},
        "Selected NT": {"type": "rich_text", "rich_text": []},
        "Saved at": {"type": "date", "date": {"start": saved_at}},
    }
    if service_date:
        props["Service date"] = {"type": "date", "date": {"start": service_date}}
    return {"id": "pg", "properties": props}


def test_parse_archive_page_extracts_meta_and_keeps_saved_at():
    page = _archive_page(
        "Trinity Sunday",
        "2026-02-15T12:00:00Z",
        liturgy={"call": "Come", "_sermon_title": "Holy", "_include_communion": True},
        service_date="2026-02-15",
    )
    svc = parse_archive_page(page)
    assert svc["occasion"] == "Trinity Sunday"
    assert svc["sermon_title"] == "Holy"
    assert svc["include_communion"] is True
    assert svc["liturgy"] == {"call": "Come"}          # meta keys stripped
    assert svc["service_date_iso"] == "2026-02-15"
    assert svc["service_date_display"] == "February 15, 2026"
    assert svc["saved_at"] == "2026-02-15T12:00:00Z"   # carried verbatim
    assert svc["truncated"] is False


def test_parse_archive_page_flags_truncated():
    svc = parse_archive_page(_archive_page("Big Service", "2026-01-01T00:00:00Z", truncate=True))
    assert svc["truncated"] is True
    assert svc["liturgy"] == {}
    assert svc["sermon_title"] == ""


# ---- DB importers -------------------------------------------------------

def test_import_services_preserves_saved_at_and_dedupes(tmp_db, make_user, make_church):
    uid = make_user(email="beau@example.com")
    cid = make_church(name="First", owner_user_id=uid, timezone="America/New_York")
    pages = [_archive_page("Advent 1", "2025-11-30T15:00:00Z", liturgy={"call": "x"})]
    with session_scope() as session:
        first = import_services(session, cid, uid, pages)
    assert first["imported"] == 1
    with session_scope() as session:
        second = import_services(session, cid, uid, pages)
    assert second["imported"] == 0 and second["skipped"] == 1
    with session_scope() as session:
        rows = session.execute(select(Service).where(Service.church_id == cid)).scalars().all()
    assert len(rows) == 1
    assert rows[0].saved_at.year == 2025
    assert rows[0].saved_at.month == 11
    assert rows[0].saved_at.day == 30


def test_import_services_flags_truncated(tmp_db, make_user, make_church):
    uid = make_user(email="a@b.com")
    cid = make_church(name="Second", owner_user_id=uid, timezone="America/New_York")
    pages = [_archive_page("Truncated one", "2025-10-05T00:00:00Z", truncate=True)]
    with session_scope() as session:
        report = import_services(session, cid, uid, pages)
    assert report["flagged"] == 1
    assert report["flagged_rows"] == ["2025-10-05T00:00:00Z"]


def test_import_usage_dedupes(tmp_db, make_user, make_church):
    uid = make_user(email="c@d.com")
    cid = make_church(name="Third", owner_user_id=uid, timezone="America/New_York")
    page = {
        "id": "u1",
        "properties": {
            "Date": {"type": "date", "date": {"start": "2026-01-04"}},
            "Hymn number": {"type": "number", "number": 43},
            "Hymn title": {"type": "rich_text", "rich_text": [{"plain_text": "Holy, Holy, Holy"}]},
        },
    }
    with session_scope() as session:
        first = import_usage(session, cid, [page])
    with session_scope() as session:
        second = import_usage(session, cid, [page])
    assert first["imported"] == 1
    assert second["imported"] == 0 and second["skipped"] == 1
    with session_scope() as session:
        rows = session.execute(select(HymnUsage).where(HymnUsage.church_id == cid)).scalars().all()
    assert len(rows) == 1


def test_import_contacts_founder_only_and_dedupes(tmp_db, make_user, make_church):
    uid = make_user(email="e@f.com")
    cid = make_church(name="Fourth", owner_user_id=uid, timezone="America/New_York")
    contacts = [
        {"name": "Mary", "email": "Mary@example.com"},
        {"name": "Mary again", "email": "mary@example.com"},   # dup (case-insensitive)
        {"name": "No email", "email": ""},
    ]
    with session_scope() as session:
        report = import_contacts(session, cid, contacts)
    assert report["imported"] == 1 and report["skipped"] == 1
    with session_scope() as session:
        rows = session.execute(select(Contact).where(Contact.church_id == cid)).scalars().all()
    assert len(rows) == 1 and rows[0].email == "mary@example.com"


def test_validate_enrichment_passes(tmp_db, make_user, make_church):
    uid = make_user(email="g@h.com")
    cid = make_church(name="Fifth", owner_user_id=uid, timezone="America/New_York")
    with session_scope() as session:
        session.add(Hymn(
            church_id=cid, title="Amazing Grace", number=649,
            scripture_refs="John 9:25", theme="grace",
            hymnary_link=None, audio_url=None,
        ))
    with session_scope() as session:
        report = validate_enrichment(session, cid)
    assert report["with_scripture"] == 1
    assert report["sample_matches"] == 1


def test_validate_enrichment_aborts_when_empty(tmp_db, make_user, make_church):
    uid = make_user(email="i@j.com")
    cid = make_church(name="Sixth", owner_user_id=uid, timezone="America/New_York")
    with session_scope() as session:
        with pytest.raises(SystemExit) as excinfo:
            validate_enrichment(session, cid)
    assert excinfo.value.code == 2
