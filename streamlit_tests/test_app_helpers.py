import logging
from datetime import date, timedelta

import pytest
from hymn_usage import get_recently_used_identifiers, record_usage
from ui_helpers import (
    capture_query_params,
    clear_oauth_query_params,
    hymn_display_from_flat,
    build_title_to_info,
    coerce_selectbox_value,
    hymn_options_excluding_recent,
    picked_hymn_keys,
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


# --- inv D5: "Exclude hymns used in the last 12 weeks" must never drop a pick ---

def _hymnal(*titles_and_numbers):
    """title_to_info for a hymnal given as (title, number) pairs."""
    return build_title_to_info([
        {"id": str(number), "Hymn Title": title, "Hymn Number": number, "Hymnary.org Link": None}
        for title, number in titles_and_numbers
    ])


def test_excluding_recent_keeps_a_recent_hymn_that_is_already_picked():
    title_to_info = _hymnal(("A", 1), ("B", 2), ("C", 3))
    recent_used = {(1, "a"), (2, "b")}
    assert hymn_options_excluding_recent(title_to_info, recent_used, {"a"}) == ["a", "c"]


def test_excluding_recent_with_nothing_picked_hides_every_recent_hymn():
    title_to_info = _hymnal(("A", 1), ("B", 2), ("C", 3))
    recent_used = {(1, "a"), (2, "b")}
    assert hymn_options_excluding_recent(title_to_info, recent_used, set()) == ["c"]


def test_excluding_recent_always_offers_a_hymn_that_is_not_recent():
    title_to_info = _hymnal(("A", 1), ("B", 2), ("C", 3))
    assert hymn_options_excluding_recent(title_to_info, set(), set()) == ["a", "b", "c"]
    assert "c" in hymn_options_excluding_recent(title_to_info, {(1, "a")}, {"b"})


def test_excluding_recent_never_adds_a_kept_key_missing_from_the_hymnal():
    # A pick whose hymn was renamed or deleted in Settings is not brought back.
    title_to_info = _hymnal(("A", 1), ("C", 3))
    assert hymn_options_excluding_recent(title_to_info, {(1, "a")}, {"a", "gone"}) == ["a", "c"]


def test_d5_picks_survive_prepare_with_exclude_recent_ticked(tmp_db, make_church):
    """The D5 flow: Prepare records the three picks as used today and reruns. The
    rebuilt options must still contain the picks, or safe_hymn_selectbox resets
    them to '' and the next Prepare or Save stores the service without hymns."""
    church_id = make_church()
    title_to_info = _hymnal(
        ("Holy, Holy, Holy", 1), ("Amazing Grace", 378), ("Be Thou My Vision", 339),
        ("O God, Our Help in Ages Past", 210), ("Come, Thou Fount", 356),
    )
    picks = ["holy, holy, holy", "amazing grace", "be thou my vision"]
    # Prepare bulletin copy: record_usage(church_id, service_date_str, hymns_ordered)
    assert record_usage(church_id, date.today().isoformat(), [title_to_info[p] for p in picks])
    # A hymn used last week and not picked this time.
    assert record_usage(church_id, (date.today() - timedelta(weeks=1)).isoformat(),
                        [title_to_info["o god, our help in ages past"]])

    recent_used = get_recently_used_identifiers(church_id, weeks=12)
    # app.py builds `keep` as picked_hymn_keys(st.session_state); a dict stands in for it.
    session = {"opening": picks[0], "response": picks[1], "closing": picks[2], "sermon_title": "x"}
    keep = picked_hymn_keys(session)
    assert keep == set(picks)
    assert picked_hymn_keys({"opening": picks[0], "response": ""}) == {picks[0]}   # empty or missing slot
    options = hymn_options_excluding_recent(title_to_info, recent_used, keep)

    for pick in picks:
        assert coerce_selectbox_value(pick, [""] + options) == pick
    assert "o god, our help in ages past" not in options   # recent, not picked: still hidden
    assert "come, thou fount" in options                    # never used: offered

    # Without the picks in `keep` (the old app.py filter) every pick resets: the bug.
    old_options = hymn_options_excluding_recent(title_to_info, recent_used, set())
    for pick in picks:
        assert coerce_selectbox_value(pick, [""] + old_options) == ""


from ui_helpers import sermon_text_for


def test_sermon_text_uses_the_cached_passage():
    assert sermon_text_for("John 21:1-19", {"John 21:1-19": "Text."}) == ("John 21:1-19", "Text.")


def test_sermon_text_fetches_when_not_cached_or_failed():
    fetched = []

    def fetch(ref):
        fetched.append(ref)
        return "Fetched."

    assert sermon_text_for("John 21:1-19", {}, fetch) == ("John 21:1-19", "Fetched.")
    assert sermon_text_for("John 21:1-19", {"John 21:1-19": "[Could not load text]"}, fetch) == \
        ("John 21:1-19", "Fetched.")
    assert fetched == ["John 21:1-19", "John 21:1-19"]


def test_sermon_text_is_none_without_a_reference_or_any_text():
    assert sermon_text_for("", {"": "x"}) is None
    assert sermon_text_for(None, {}) is None
    assert sermon_text_for("John 21:1-19", {}) is None   # no cache, no fetcher

    def broken(_ref):
        raise RuntimeError("network down")

    assert sermon_text_for("John 21:1-19", None, broken) is None


def test_sermon_text_keeps_a_fetched_passage_for_the_session():
    fetched = []

    def fetch(ref):
        fetched.append(ref)
        return "  Fetched.  "

    # The selected half of an "X or Y" reading is not a key the page loaded.
    cache = {"John 21:1-19 or Luke 5:1-11": "Both."}
    assert sermon_text_for("John 21:1-19", cache, fetch) == ("John 21:1-19", "Fetched.")
    assert cache["John 21:1-19"] == "Fetched."
    # The next click uses the kept text instead of fetching again.
    assert sermon_text_for("John 21:1-19", cache, fetch) == ("John 21:1-19", "Fetched.")
    assert fetched == ["John 21:1-19"]

    # A fetched passage replaces a failed load.
    cache = {"John 21:1-19": "[Could not load text]"}
    sermon_text_for("John 21:1-19", cache, fetch)
    assert cache == {"John 21:1-19": "Fetched."}


def test_sermon_text_logs_a_failed_fetch_and_keeps_nothing(caplog):
    def broken(_ref):
        raise RuntimeError("network down")

    cache = {}
    with caplog.at_level(logging.WARNING, logger="ui_helpers"):
        assert sermon_text_for("John 21:1-19", cache, broken) is None
    assert cache == {}   # the next click tries again
    assert any("John 21:1-19" in r.getMessage() and r.levelno == logging.WARNING
               for r in caplog.records)

    # An empty answer is not kept either.
    assert sermon_text_for("John 21:1-19", cache, lambda _ref: None) is None
    assert sermon_text_for("John 21:1-19", cache, lambda _ref: "[Could not load text]") is None
    assert cache == {}
