import pytest
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    hymn_display_from_flat,
    build_title_to_info,
)


def test_capture_query_params_copies_invite_and_church():
    session = {}
    qp = {"invite": "ABC123", "church": "11111111-1111-1111-1111-111111111111"}
    capture_query_params(qp, session)
    assert session["pending_invite_code"] == "ABC123"
    assert session["active_church_id"] == "11111111-1111-1111-1111-111111111111"


def test_capture_query_params_ignores_missing_and_keeps_prior():
    session = {"pending_invite_code": "OLD"}
    capture_query_params({}, session)
    assert session["pending_invite_code"] == "OLD"
    assert "active_church_id" not in session


def test_clear_oauth_query_params_is_targeted_not_blanket():
    qp = {"code": "x", "state": "y", "scope": "z", "invite": "KEEP", "church": "KEEP2"}
    clear_oauth_query_params(qp)
    assert "code" not in qp and "state" not in qp and "scope" not in qp
    # invite/church survive the OAuth round-trip (spec §4 query-param hygiene)
    assert qp["invite"] == "KEEP"
    assert qp["church"] == "KEEP2"


def test_hymn_display_from_flat_maps_notion_keys_and_trims():
    row = {"id": "h1", "Hymn Title": "  Amazing Grace ", "Hymn Number": 378,
           "Hymnary.org Link": "https://hymnary.org/x"}
    assert hymn_display_from_flat(row) == {
        "title": "Amazing Grace", "number": 378, "link": "https://hymnary.org/x"}


def test_build_title_to_info_lowercases_skips_blank_and_handles_empty():
    rows = [
        {"id": "1", "Hymn Title": "Holy, Holy, Holy", "Hymn Number": 1, "Hymnary.org Link": None},
        {"id": "2", "Hymn Title": "", "Hymn Number": None, "Hymnary.org Link": None},
    ]
    m = build_title_to_info(rows)
    assert set(m.keys()) == {"holy, holy, holy"}
    assert m["holy, holy, holy"]["number"] == 1
    # empty hymnal -> empty map: this is what drives the explicit empty-hymnal message
    assert build_title_to_info([]) == {}
