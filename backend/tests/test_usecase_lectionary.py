"""usecases.lectionary and the lectionary fetchers and loaders (S "Fetchers",
"Loaders", `usecases/lectionary.py`; AC1–AC3; clarifications 18, 19, 31, 39).

respx answers from the T1 recordings (tests/fixtures/lectio, vanderbilt), so
nothing leaves the machine (F §5.3). The autouse _fresh_lectionary_caches
fixture gives every test a new pool and empty caches. Threaded tests block on
threading primitives, never time.sleep, and release them in `finally`.
"""
import json
import logging
import re
import threading
import types
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx

import usecases.lectionary as lectionary
import vanderbilt_lectionary as vl
from domain_errors import InvalidInput, UpstreamError, UpstreamTimeout
from integrations import http
from tests.conftest import FakeClock
from tests.upstream_fixtures import (
    LECTIO_URL,
    VANDERBILT_URL,
    as_response,
    load,
    route_lectio,
    route_vanderbilt,
)

PALM_SUNDAY = date(2026, 3, 29)
EASTER = date(2026, 4, 5)
GOOD_FRIDAY = date(2026, 4, 3)
TUESDAY = date(2026, 9, 29)
PROPER_22 = date(2026, 10, 4)
ADVENT_1_2026 = date(2026, 11, 29)
YEAR = "2025-26"
LECTIO_404 = "2026-09-29"          # a recorded Lectio 404, reused for dates with no recording
UNREACHABLE = ("The lectionary couldn't be reached. Enter readings yourself, "
               "or try again in a few minutes.")


@pytest.fixture
def router():
    with respx.mock(assert_all_called=False) as mock:
        yield mock


@pytest.fixture
def clock():
    """The lectionary caches rebuilt on a FakeClock (the autouse reset joined the pool)."""
    fake = FakeClock()
    lectionary.reset_for_tests(clock=fake.now)
    return fake


def _status(code):
    return lambda request: httpx.Response(code, text="")


def _expected(d, lectio_name=None, year=YEAR):
    """The sets and default the domain functions give for `d` from the recordings.
    T6b's tests own the domain rules; these tests own the orchestration."""
    day = None
    if lectio_name is not None:
        day = vl.parse_lectio_payload(json.loads(load("lectio", lectio_name).body))
    rows = vl.parse_vanderbilt_csv(as_response(load("vanderbilt", year)).text)
    v_sets = [s for s in vl.vanderbilt_sets_on(rows, d) if vl.fits_draft_limits(s)]
    return vl.merge(day, v_sets, d)


def _result(d, status, partial, sets, default_index):
    return lectionary.LectionaryResult(date=d, status=status, partial=partial,
                                       reading_sets=sets, default_index=default_index)


# --- outcomes -----------------------------------------------------------------

def test_both_ok_merged(router):
    lectio = route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR)
    result = lectionary.readings_for_date(PALM_SUNDAY)
    sets, default_index = _expected(PALM_SUNDAY, "2026-03-29")
    assert result == _result(PALM_SUNDAY, "ok", False, sets, default_index)
    assert [s.source for s in result.reading_sets] == ["vanderbilt", "merged"]
    assert result.default_index == 1
    assert (lectio.call_count, vanderbilt.call_count) == (1, 1)


def test_lectio_404_with_vanderbilt_row_ok_not_partial(router):
    route_lectio(router, GOOD_FRIDAY)                  # recorded 404
    route_vanderbilt(router, YEAR)
    result = lectionary.readings_for_date(GOOD_FRIDAY)
    sets, default_index = _expected(GOOD_FRIDAY)
    assert result == _result(GOOD_FRIDAY, "ok", False, sets, default_index)
    assert [s.source for s in result.reading_sets] == ["vanderbilt"]
    assert result.default_index == 0


def test_both_none_no_readings(router):
    route_lectio(router, TUESDAY)                      # recorded 404
    route_vanderbilt(router, YEAR)                     # no row on 2026-09-29
    assert lectionary.readings_for_date(TUESDAY) == _result(TUESDAY, "no_readings", False, [], None)


def test_one_failed_with_sets_partial(router):
    # Vanderbilt down: the Lectio group alone, named by lectio_set_name.
    route_lectio(router, PROPER_22)
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=_status(503))
    result = lectionary.readings_for_date(PROPER_22)
    assert (result.status, result.partial, result.default_index) == ("ok", True, 0)
    assert [(s.name, s.source) for s in result.reading_sets] == [
        ("Nineteenth Sunday after Pentecost", "lectio")]
    # Lectio down: the Vanderbilt sets alone (the 2026-27 stub's Advent 1 row).
    route_lectio(router, ADVENT_1_2026, "error_500")
    route_vanderbilt(router, "2026-27")
    result = lectionary.readings_for_date(ADVENT_1_2026)
    assert (result.status, result.partial, result.default_index) == ("ok", True, 0)
    assert [s.source for s in result.reading_sets] == ["vanderbilt"]


def test_both_failed_upstream_error(router):
    route_lectio(router, PALM_SUNDAY, "error_500")
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=_status(503))
    with pytest.raises(UpstreamError) as caught:
        lectionary.readings_for_date(PALM_SUNDAY)
    assert (caught.value.code, caught.value.message) == ("upstream_error", UNREACHABLE)
    assert lectionary.LECTIONARY_UNREACHABLE == UNREACHABLE


def test_all_timeouts_upstream_timeout(router):
    router.get(LECTIO_URL).mock(side_effect=httpx.ReadTimeout)
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=httpx.ConnectTimeout)
    with pytest.raises(UpstreamTimeout) as caught:
        lectionary.readings_for_date(PALM_SUNDAY)
    assert (caught.value.code, caught.value.message) == ("upstream_timeout", UNREACHABLE)


def test_timeout_plus_none_is_timeout(router):
    router.get(LECTIO_URL).mock(side_effect=httpx.ReadTimeout)
    route_vanderbilt(router, YEAR, "404")              # a definitive none
    with pytest.raises(UpstreamTimeout):
        lectionary.readings_for_date(PALM_SUNDAY)


def test_timeout_plus_error_is_upstream_error(router):
    router.get(LECTIO_URL).mock(side_effect=httpx.ReadTimeout)
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=_status(503))
    with pytest.raises(UpstreamError) as caught:
        lectionary.readings_for_date(PALM_SUNDAY)
    assert caught.value.code == "upstream_error"


def test_all_sets_over_limits_is_no_readings(router):
    # clean_cell splits on " - " only when a segment is a heading (the Easter Vigil shape).
    too_many = "Old Testament - " + " - ".join(f"Genesis {n}:1-5" for n in range(1, 22))
    assert len(vl.clean_cell(too_many)) == 21          # one line more than the draft allows
    body = ('"Revised Common Lectionary"\n'
            '"Liturgical Date","Calendar Date","First reading","Psalm","Second reading",'
            '"Gospel","Art","Prayer"\n'
            f'"Test Day","Sep 29, 2026","{too_many}","","","","",""\n')
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(
        side_effect=lambda request: httpx.Response(
            200, text=body, headers={"Content-Type": "text/csv; charset=utf-8"}))
    route_lectio(router, TUESDAY)                      # recorded 404
    assert lectionary.readings_for_date(TUESDAY) == _result(TUESDAY, "no_readings", False, [], None)


# --- failure classification -----------------------------------------------------

def test_lectio_html_200_failed(router):
    assert load("lectio", "html_200").status == 200
    route_lectio(router, PALM_SUNDAY, "html_200")
    with pytest.raises(vl.SourceFailed) as caught:
        vl.fetch_lectio(PALM_SUNDAY)
    assert caught.value.timeout is False
    with pytest.raises(vl.SourceFailed):
        vl.load_lectio(PALM_SUNDAY)


def test_lectio_undecodable_json_failed(router):
    route = router.get(LECTIO_URL).mock(side_effect=lambda request: httpx.Response(
        200, content=b'{"data": ', headers={"Content-Type": "application/json; charset=utf-8"}))
    with pytest.raises(vl.SourceFailed) as caught:
        vl.fetch_lectio(PALM_SUNDAY)
    assert caught.value.timeout is False
    with pytest.raises(vl.SourceFailed):
        vl.load_lectio(PALM_SUNDAY)
    # A "+json" media type with parameters is still JSON (clarification 19).
    route.mock(side_effect=lambda request: httpx.Response(
        200, content=b'{"data": null}',
        headers={"Content-Type": "application/vnd.api+json; charset=utf-8"}))
    assert vl.fetch_lectio(PALM_SUNDAY) == {"data": None}
    assert vl.load_lectio(PALM_SUNDAY) is None


def test_vanderbilt_html_200_failed(router):
    assert load("vanderbilt", "html_200").status == 200
    route = route_vanderbilt(router, YEAR, "html_200")
    with pytest.raises(vl.SourceFailed) as caught:
        vl.fetch_vanderbilt_year(YEAR)
    assert caught.value.timeout is False
    # An HTML page served as text/plain passes the type check, then fails for its missing header.
    route.mock(side_effect=lambda request: httpx.Response(200, text="<html><body>Gone</body></html>"))
    assert vl.fetch_vanderbilt_year(YEAR).startswith("<html>")
    with pytest.raises(vl.SourceFailed) as caught:
        vl.load_vanderbilt_year(YEAR)
    assert isinstance(caught.value.__cause__, vl.LectionaryFormatError)
    # The real Content-Type is unrecorded, so other CSV-ish types pass the check; the parser decides.
    csv_body = load("vanderbilt", YEAR).body
    for media_type in ("application/csv", "text/comma-separated-values", "application/octet-stream"):
        route.mock(side_effect=lambda request, t=media_type: httpx.Response(
            200, content=csv_body, headers={"Content-Type": t}))
        assert vl.fetch_vanderbilt_year(YEAR) == csv_body.decode("utf-8")


def test_vanderbilt_404_none(router):
    route_vanderbilt(router, "1999-00", "404")
    assert vl.fetch_vanderbilt_year("1999-00") is None
    assert vl.load_vanderbilt_year("1999-00") == []


# --- caching ---------------------------------------------------------------------

def test_second_call_within_24h_no_request(router, clock):
    lectio = route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR)
    first = lectionary.readings_for_date(PALM_SUNDAY)
    clock.advance(86_399)
    assert lectionary.readings_for_date(PALM_SUNDAY) == first
    assert (lectio.call_count, vanderbilt.call_count) == (1, 1)
    clock.advance(2)
    lectionary.readings_for_date(PALM_SUNDAY)
    assert (lectio.call_count, vanderbilt.call_count) == (2, 2)


def test_vanderbilt_404_cached_24h(router, clock):
    route_lectio(router, TUESDAY)
    vanderbilt = route_vanderbilt(router, YEAR, "404")
    lectionary.readings_for_date(TUESDAY)
    clock.advance(86_399)
    assert lectionary.readings_for_date(TUESDAY).status == "no_readings"
    assert vanderbilt.call_count == 1
    clock.advance(2)
    lectionary.readings_for_date(TUESDAY)
    assert vanderbilt.call_count == 2


def test_vanderbilt_html_cached_5_min(router, clock):
    route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR, "html_200")
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    clock.advance(299)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    assert vanderbilt.call_count == 1
    clock.advance(2)
    lectionary.readings_for_date(PALM_SUNDAY)
    assert vanderbilt.call_count == 2


def test_lectio_500_cached_5_min_then_retried(router, clock):
    lectio = route_lectio(router, PALM_SUNDAY, "error_500")
    route_vanderbilt(router, YEAR)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    clock.advance(299)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is True
    assert lectio.call_count == 1
    lectio.mock(side_effect=lambda request: as_response(load("lectio", "2026-03-29")))
    clock.advance(2)
    assert lectionary.readings_for_date(PALM_SUNDAY).partial is False
    assert lectio.call_count == 2


def test_lectio_404_cached_24h(router, clock):
    lectio = route_lectio(router, GOOD_FRIDAY)         # recorded 404
    route_vanderbilt(router, YEAR)
    lectionary.readings_for_date(GOOD_FRIDAY)
    clock.advance(86_399)
    lectionary.readings_for_date(GOOD_FRIDAY)
    assert lectio.call_count == 1
    clock.advance(2)
    lectionary.readings_for_date(GOOD_FRIDAY)
    assert lectio.call_count == 2


def test_unexpected_loader_exception_not_cached(router, clock):
    lectio = router.get(LECTIO_URL).mock(side_effect=RuntimeError("bug"))
    route_vanderbilt(router, YEAR)
    for _ in range(2):
        with pytest.raises(RuntimeError, match="bug"):
            lectionary.readings_for_date(PALM_SUNDAY)
    assert lectio.call_count == 2                      # nothing was cached between the calls


def test_two_dates_same_year_one_vanderbilt_request(router):
    palm = route_lectio(router, PALM_SUNDAY)
    easter = route_lectio(router, EASTER)
    vanderbilt = route_vanderbilt(router, YEAR)
    lectionary.readings_for_date(PALM_SUNDAY)
    lectionary.readings_for_date(EASTER)
    assert vanderbilt.call_count == 1                  # keyed by liturgical year, not by date
    assert (palm.call_count, easter.call_count) == (1, 1)


def test_advent_boundary_fetches_next_year_file(router):
    saturday, advent_1_2027 = date(2026, 11, 28), date(2027, 11, 28)
    for d in (saturday, ADVENT_1_2026, advent_1_2027):
        route_lectio(router, d, LECTIO_404)
    y2526 = route_vanderbilt(router, "2025-26")
    y2627 = route_vanderbilt(router, "2026-27")
    y2728 = route_vanderbilt(router, "2027-28")
    assert lectionary.readings_for_date(saturday).status == "no_readings"
    assert (y2526.call_count, y2627.call_count, y2728.call_count) == (1, 0, 0)
    advent_1 = lectionary.readings_for_date(ADVENT_1_2026)
    assert (advent_1.status, [s.source for s in advent_1.reading_sets]) == ("ok", ["vanderbilt"])
    assert (y2526.call_count, y2627.call_count, y2728.call_count) == (1, 1, 0)
    assert lectionary.readings_for_date(advent_1_2027).status == "ok"
    assert (y2526.call_count, y2627.call_count, y2728.call_count) == (1, 1, 1)


# --- concurrency -------------------------------------------------------------------

class _SpyCache:
    """Wraps a TTLCache; `entered` is set once `calls` lookups have begun."""

    def __init__(self, inner, calls):
        self.inner, self.calls, self.count = inner, calls, 0
        self.entered, self.lock = threading.Event(), threading.Lock()

    def get_or_load(self, key, loader):
        with self.lock:
            self.count += 1
            if self.count == self.calls:
                self.entered.set()
        return self.inner.get_or_load(key, loader)


def test_single_flight_two_threads_one_call(router, monkeypatch):
    started, release = threading.Event(), threading.Event()
    recorded = load("lectio", "2026-03-29")

    def held(request):
        started.set()
        release.wait(5)
        return as_response(recorded)

    lectio = router.get(LECTIO_URL).mock(side_effect=held)
    vanderbilt = route_vanderbilt(router, YEAR)
    spy = _SpyCache(lectionary._LECTIO, calls=2)
    monkeypatch.setattr(lectionary, "_LECTIO", spy)
    results = []
    threads = [threading.Thread(target=lambda: results.append(lectionary.readings_for_date(PALM_SUNDAY)))
               for _ in range(2)]
    try:
        threads[0].start()
        assert started.wait(5)                         # the first lookup is inside Lectio
        threads[1].start()
        assert spy.entered.wait(5)                     # the second has reached the cache
    finally:
        release.set()
        for t in threads:
            if t.ident is not None:
                t.join(10)
    assert len(results) == 2 and results[0] == results[1]
    assert (lectio.call_count, vanderbilt.call_count) == (1, 1)


def test_sources_requested_concurrently(router):
    both_in_flight = threading.Barrier(2, timeout=5)   # breaks if the sources run one after the other

    def meet(recorded):
        def side_effect(request):
            both_in_flight.wait()
            return as_response(recorded)
        return side_effect

    router.get(LECTIO_URL).mock(side_effect=meet(load("lectio", "2026-03-29")))
    router.get(VANDERBILT_URL.format(year=YEAR)).mock(side_effect=meet(load("vanderbilt", YEAR)))
    result = lectionary.readings_for_date(PALM_SUNDAY)
    assert (result.status, result.partial) == ("ok", False)


def test_source_unfinished_at_deadline_is_timeout(router, monkeypatch):
    release = threading.Event()

    def held(request):
        release.wait(10)
        return httpx.Response(404, json={"error": "not found"})

    router.get(LECTIO_URL).mock(side_effect=held)
    route_vanderbilt(router, YEAR)
    router.get(VANDERBILT_URL.format(year="2026-27")).mock(side_effect=held)
    # Warm the 2025-26 file under the real deadline, so only Lectio is slow below.
    lectionary._VANDERBILT.get_or_load(YEAR, lambda: vl.load_vanderbilt_year(YEAR))
    monkeypatch.setattr(lectionary, "DEADLINE_SECONDS", 0.5)   # margin for a cold pool on a busy CI runner
    try:
        partial = lectionary.readings_for_date(GOOD_FRIDAY)
        assert (partial.status, partial.partial) == ("ok", True)
        assert [s.source for s in partial.reading_sets] == ["vanderbilt"]
        with pytest.raises(UpstreamTimeout) as caught:
            lectionary.readings_for_date(ADVENT_1_2026)   # both sources held
        assert caught.value.code == "upstream_timeout"
    finally:
        release.set()
        lectionary.reset_for_tests()                   # join the held workers while respx answers


# --- other ---------------------------------------------------------------------------

def test_year_out_of_range_invalid_input(router):
    for d in (date(1899, 12, 31), date(2200, 1, 1)):
        with pytest.raises(InvalidInput) as caught:
            lectionary.readings_for_date(d)
        assert (caught.value.code, caught.value.field, caught.value.message) == (
            "invalid_request", "date", "Enter a date between 1900 and 2199.")
    assert router.calls.call_count == 0
    router.get(LECTIO_URL).respond(404)
    router.get(url__startswith="https://lectionary.library.vanderbilt.edu/").respond(404)
    for d in (date(1900, 1, 1), date(2199, 12, 31)):
        assert lectionary.readings_for_date(d).status == "no_readings"


def test_fetch_urls_params_and_read_timeouts(router, monkeypatch):
    lectio = route_lectio(router, PALM_SUNDAY)
    vanderbilt = route_vanderbilt(router, YEAR)
    seen = []
    real_get = http.get

    def spy(url, **kwargs):
        seen.append((url, kwargs.get("params"), kwargs["read_timeout"]))
        return real_get(url, **kwargs)

    monkeypatch.setattr(http, "get", spy)
    lectionary.readings_for_date(PALM_SUNDAY)
    assert {url: (params, read) for url, params, read in seen} == {
        "https://lectio-api.org/api/v1/readings": ({"date": "2026-03-29", "tradition": "rcl"}, 10.0),
        "https://lectionary.library.vanderbilt.edu/calendar/2025-26/?season=all&download=csv": (None, 15.0),
    }
    assert (vl.LECTIO_READ_TIMEOUT, vl.VANDERBILT_READ_TIMEOUT) == (10.0, 15.0)
    sent = lectio.calls.last.request
    assert (sent.url.scheme, sent.url.host, sent.url.path) == ("https", "lectio-api.org", "/api/v1/readings")
    assert dict(sent.url.params) == {"date": "2026-03-29", "tradition": "rcl"}
    assert sent.headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    got = vanderbilt.calls.last.request
    assert (got.url.path, dict(got.url.params)) == ("/calendar/2025-26/", {"season": "all", "download": "csv"})


def test_old_names_and_dict_cache_gone():
    # AC3 as a test: the old lookups and the module-level dict cache are gone.
    for name in ("_cache", "fetch_lectionary_year", "get_readings_for_date",
                 "_normalize_date_for_match", "_liturgical_year_for_date",
                 "_liturgical_sunday_name", "get_readings_for_date_string",
                 "_get_readings_from_lectio", "_row_to_reading", "_ordinal_sunday_label",
                 "_easter_date"):
        assert not hasattr(vl, name), name
    module_state = {n: v for n, v in vars(vl).items() if not n.startswith("__")}
    assert not [n for n, v in module_state.items() if isinstance(v, (dict, list, set)) and not v]
    assert not [n for n, v in module_state.items()           # a cache is data, not a class
                if "cache" in n.lower() and not callable(v) and not isinstance(v, types.ModuleType)]
    source = Path(vl.__file__).read_text()
    assert "httpx.get(" not in source and "TTLCache" not in source


def test_log_line_outcomes_no_payload(router, caplog):
    route_lectio(router, PALM_SUNDAY, "error_500")
    route_vanderbilt(router, YEAR)
    route_lectio(router, TUESDAY)                      # recorded 404
    caplog.set_level(logging.INFO, logger="usecases.lectionary")

    def lines():
        found = [r.getMessage() for r in caplog.records if r.name == "usecases.lectionary"]
        caplog.clear()
        return found

    result = lectionary.readings_for_date(PALM_SUNDAY)
    (first,) = lines()
    assert first.startswith(
        "lectionary_lookup date=2026-03-29 lectio=failed vanderbilt=ok lectio_cached=False "
        f"vanderbilt_cached=False sets={len(result.reading_sets)} duration_ms=")
    assert re.fullmatch(r".* duration_ms=\d+", first)
    lectionary.readings_for_date(PALM_SUNDAY)
    (again,) = lines()
    assert " lectio=failed vanderbilt=ok lectio_cached=True vanderbilt_cached=True " in again
    lectionary.readings_for_date(TUESDAY)
    (none,) = lines()
    assert " lectio=none vanderbilt=none lectio_cached=False vanderbilt_cached=True sets=0 " in none
    for line in (first, again, none):                  # never a payload, a URL or a query string
        assert "http" not in line and "tradition" not in line
        for s in result.reading_sets:
            for ref in s.scriptures:
                assert ref not in line
