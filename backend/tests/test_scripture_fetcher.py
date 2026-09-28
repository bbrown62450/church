"""scripture_fetcher: translations, planning, part fetching, statuses and
caching (S "Passages", Status rules, Testing "test_scripture_fetcher.py";
AC5 domain half; F §2.3.3, §2.7; 2a clarifications 13, 27, 33, 36, 39).

Replaces test_scripture_translations.py: its five tests come first, ported
from monkeypatching sf.httpx.get (no longer the call site) to the T2 seam.
Every upstream answer comes from an httpx.MockTransport installed behind
integrations.http's own client settings (set_http_for_tests), so nothing
leaves the process and the _no_network guard stays active (AC13). Recorded
bodies come from tests/fixtures/bible_api and tests/fixtures/esv (T1).

The autouse _fresh_passage_cache fixture gives each test a new part cache,
_fresh_rate_limits full upstream budgets, and _fresh_http_client the
default client back afterwards."""
import inspect
import json
import logging

import httpx

import scripture_fetcher as sf
from integrations import budget, http
from tests import upstream_fixtures
from tests.conftest import FakeClock

WEEK = 7 * 24 * 60 * 60

BIBLE_OK = upstream_fixtures.load("bible_api", "isaiah_50_4-9")
BIBLE_404 = upstream_fixtures.load("bible_api", "isaiah_50_4-9a")
BIBLE_COMMA = upstream_fixtures.load("bible_api", "luke_2_1-14_15-20")
ESV_OK = upstream_fixtures.load("esv", "success")
ESV_EMPTY = upstream_fixtures.load("esv", "empty")
ESV_PATH = "/v3/passage/text/"


def _replay(recorded):
    return httpx.Response(recorded.status, content=recorded.body,
                          headers={"Content-Type": recorded.content_type})


def _text_of(recorded):
    return json.loads(recorded.body)["text"].strip()


def _read_timeout(request):
    raise httpx.ReadTimeout("read timed out", request=request)


def _install(answers):
    """Answer every upstream call by its decoded URL path (for example
    "/genesis 2:15-17", or ESV_PATH). The value decides the answer:
    - a str: a bible-api 200 whose "text" is that string plus a newline;
    - a recorded fixture: replayed as recorded;
    - 404: bible-api's recorded 404; any other int: that status, no body;
    - a callable: called with the request (it may raise).
    The dict is read on every call, so a test can change an answer between
    calls. A path not in `answers` raises KeyError out of the call and fails
    the test. Returns the list of requests the transport saw, in order."""
    seen = []

    def handler(request):
        seen.append(request)
        answer = answers[request.url.path]
        if isinstance(answer, str):
            return httpx.Response(200, json={"reference": request.url.path, "text": answer + "\n"})
        if isinstance(answer, upstream_fixtures.Recorded):
            return _replay(answer)
        if answer == 404:
            return _replay(BIBLE_404)
        if isinstance(answer, int):
            return httpx.Response(answer)
        return answer(request)

    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(handler)))
    return seen


def _skips_and_failures(caplog):
    return [r.getMessage() for r in caplog.records
            if r.name == "scripture_fetcher" and r.getMessage().startswith("passage_part_")]


# --- ported from test_scripture_translations.py ---

def test_esv_excluded_without_key(monkeypatch):
    monkeypatch.delenv("ESV_API_KEY", raising=False)
    ids = [tid for tid, _ in sf.available_translations()]
    assert "web" in ids and "kjv" in ids
    assert "esv" not in ids            # hidden until a key is configured
    assert sf.esv_configured() is False


def test_esv_included_last_with_key(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    ids = [tid for tid, _ in sf.available_translations()]
    assert ids == list(sf.TRANSLATIONS)          # display order, every translation
    assert ids[0] == sf.DEFAULT_TRANSLATION == "web"
    assert ids[-1] == "esv"


def test_translation_label():
    assert "World English Bible" in sf.translation_label("web")
    assert "ESV" in sf.translation_label("esv")
    assert sf.translation_label(None) == sf.translation_label("web")
    assert sf.translation_label("unknown-id") == "unknown-id"


def test_esv_routing_token_header(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = _install({ESV_PATH: ESV_OK})
    assert sf.get_passage_text("John 3:16", translation="esv") == "For God so loved the world. (ESV)"
    (request,) = seen
    assert str(request.url.copy_with(query=None)) == sf.ESV_API_BASE
    assert dict(request.url.params) == {
        "q": "John 3:16",
        "include-headings": "false",
        "include-footnotes": "false",
        "include-verse-numbers": "false",
        "include-passage-references": "false",
        "include-short-copyright": "true",
    }
    assert request.headers["Authorization"] == "Token test-key"
    assert request.headers["User-Agent"] == "WorshipServiceBuilder/1.0"
    assert request.extensions["timeout"]["read"] == sf.ESV_READ_TIMEOUT == 10.0


def test_bible_api_routing_translation_param():
    seen = _install({"/genesis 1:1": "In the beginning..."})
    assert sf.get_passage_text("Genesis 1:1", translation="kjv") == "In the beginning..."
    (request,) = seen
    assert str(request.url).startswith(sf.BIBLE_API_BASE + "/")
    assert dict(request.url.params) == {"translation": "kjv"}
    assert "Authorization" not in request.headers
    assert request.extensions["timeout"]["read"] == sf.BIBLE_API_READ_TIMEOUT == 10.0
    assert request.extensions["timeout"]["connect"] == 5.0


# --- planning and URLs ---

def test_url_quotes_normalized_part():
    seen = _install({"/isaiah 50:4-9": BIBLE_OK, "/luke 2:1-14, 15-20": BIBLE_COMMA})
    isaiah = sf.fetch_passage("Isaiah 50:4-9a", "web")
    luke = sf.fetch_passage("Luke 2:1-14, (15-20)", "web")
    assert [r.url.raw_path for r in seen] == [
        b"/isaiah%2050:4-9?translation=web",             # AC5: the "a" is dropped for the fetch
        b"/luke%202:1-14,%2015-20?translation=web",
    ]
    assert isaiah == sf.Passage("Isaiah 50:4-9a", "ok", (
        sf.Section("Isaiah 50:4-9a", "ok", _text_of(BIBLE_OK)),))   # the displayed text never changes
    assert luke.status == "ok" and luke.sections[0].text == _text_of(BIBLE_COMMA)


def test_plan_parts_alternatives_joined_semicolons():
    assert sf.plan_parts("Genesis 2:15-17; 3:1-7 or Matthew 4:1-11") == [
        ["Genesis 2:15-17", "Genesis 3:1-7"], ["Matthew 4:1-11"]]
    assert sf.plan_parts("John 3:1-17 OR Matthew 17:1-9") == [["John 3:1-17"], ["Matthew 17:1-9"]]
    assert sf.plan_parts("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26") == [
        ["Genesis 1:1-2:4", "Psalm 136:1-9, 23-26"]]
    assert sf.plan_parts("Isaiah 50:4-9a") == [["Isaiah 50:4-9"]]
    # Spellings only scripture_refs knows are sent under the book's name (owner 2026-09-28 aliases).
    assert sf.plan_parts("Revelations 21:1-6; Rm 8:1 or Mat 5:1-12") == [
        ["Revelation 21:1-6", "Romans 8:1"], ["Matthew 5:1-12"]]
    assert sf.plan_parts("Php 2:5-11 and Jdg 4:1-7") == [["Philippians 2:5-11", "Judges 4:1-7"]]
    assert sf.plan_parts("Eccles 3:1-13") == [["Ecclesiastes 3:1-13"]]
    assert sf.plan_sections("John 3:1-17 or Matthew 17:1-9") == [
        ("John 3:1-17", ["John 3:1-17"]), ("Matthew 17:1-9", ["Matthew 17:1-9"])]
    for empty in (";", " ; ", "", "   "):
        assert sf.plan_parts(empty) == []                 # 2a clarification 33
        assert sf.plan_sections(empty) == []


def test_alternatives_become_sections():
    seen = _install({"/john 3:1-17": "Nicodemus came by night.",
                     "/matthew 17:1-9": "Jesus was transfigured."})
    passage = sf.fetch_passage("  John 3:1-17 or Matthew 17:1-9 ", "web")
    assert passage == sf.Passage("John 3:1-17 or Matthew 17:1-9", "ok", (
        sf.Section("John 3:1-17", "ok", "Nicodemus came by night."),
        sf.Section("Matthew 17:1-9", "ok", "Jesus was transfigured."),
    ))
    text = sf.get_passage_text("John 3:1-17 or Matthew 17:1-9")
    assert text == "Nicodemus came by night.\n\nJesus was transfigured."   # no "--- alt ---" headers
    assert len(seen) == 2                                  # the second call came from the cache


def test_semicolon_parts_joined_with_blank_line():
    seen = _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": "The serpent."})
    passage = sf.fetch_passage("Genesis 2:15-17; 3:1-7", "web")
    assert [r.url.path for r in seen] == ["/genesis 2:15-17", "/genesis 3:1-7"]   # in order
    assert passage == sf.Passage("Genesis 2:15-17; 3:1-7", "ok", (
        sf.Section("Genesis 2:15-17; 3:1-7", "ok", "The garden.\n\nThe serpent."),))


def test_split_joined_parts_fetched_separately():
    seen = _install({"/genesis 1:1-2:4": "Creation.", "/psalm 136:1-9, 23-26": "His love endures.",
                     "/psalm 42 and 43": 404})
    vigil = sf.fetch_passage("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26", "web")
    assert [r.url.path for r in seen] == ["/genesis 1:1-2:4", "/psalm 136:1-9, 23-26"]
    assert vigil.sections == (
        sf.Section("Genesis 1:1-2:4a and Psalm 136:1-9, 23-26", "ok", "Creation.\n\nHis love endures."),)
    whole = sf.fetch_passage("Psalm 42 and 43", "web")   # "43" is not a book: one part, S :403
    assert [r.url.path for r in seen][2:] == ["/psalm 42 and 43"]
    assert whole.status == "not_found"


# --- statuses (S Status rules) ---

def test_status_all_ok():
    _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": "The serpent.",
              "/matthew 4:1-11": "The temptation."})
    assert sf.fetch_part("Genesis 2:15-17", "web") == sf.Part("Genesis 2:15-17", "ok", "The garden.")
    passage = sf.fetch_passage("Genesis 2:15-17; 3:1-7 or Matthew 4:1-11", "web")
    assert passage.status == "ok"
    assert [(s.reference, s.status) for s in passage.sections] == [
        ("Genesis 2:15-17; 3:1-7", "ok"), ("Matthew 4:1-11", "ok")]
    assert sf.get_passage_text("Genesis 2:15-17; 3:1-7 or Matthew 4:1-11") == (
        "The garden.\n\nThe serpent.\n\nThe temptation.")


def test_one_semicolon_part_404_section_not_found_keeps_text():
    _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": 404})
    passage = sf.fetch_passage("Genesis 2:15-17; 3:1-7", "web")
    assert sf.fetch_part("Genesis 3:1-7", "web") == sf.Part("Genesis 3:1-7", "not_found", None)
    assert passage == sf.Passage("Genesis 2:15-17; 3:1-7", "not_found", (
        sf.Section("Genesis 2:15-17; 3:1-7", "not_found", "The garden."),))


def test_one_part_500_section_unavailable_keeps_text(caplog):
    _install({"/genesis 2:15-17": "The garden.", "/genesis 3:1-7": 500, "/genesis 3:8-15": _read_timeout})
    with caplog.at_level(logging.INFO, logger="scripture_fetcher"):
        failed = sf.fetch_passage("Genesis 2:15-17; 3:1-7", "web")
        timed_out = sf.fetch_passage("Genesis 2:15-17; 3:8-15", "web")
    assert failed == sf.Passage("Genesis 2:15-17; 3:1-7", "unavailable", (
        sf.Section("Genesis 2:15-17; 3:1-7", "unavailable", "The garden."),))
    assert timed_out.sections == (
        sf.Section("Genesis 2:15-17; 3:8-15", "unavailable", "The garden."),)
    assert _skips_and_failures(caplog) == [
        "passage_part_failed reason=status_500 upstream=bible_api",
        "passage_part_failed reason=timeout upstream=bible_api",
    ]
    assert "Genesis" not in caplog.text and "genesis" not in caplog.text   # no reference in the logs


def test_one_alternative_unavailable_passage_unavailable():
    _install({"/john 3:1-17": "Nicodemus came by night.", "/matthew 17:1-9": 503,
              "/hezekiah 1:1": 404})
    passage = sf.fetch_passage("John 3:1-17 or Matthew 17:1-9", "web")
    assert passage == sf.Passage("John 3:1-17 or Matthew 17:1-9", "unavailable", (
        sf.Section("John 3:1-17", "ok", "Nicodemus came by night."),
        sf.Section("Matthew 17:1-9", "unavailable", None),
    ))
    assert sf.get_passage_text("John 3:1-17 or Matthew 17:1-9") == "Nicodemus came by night."
    mixed = sf.fetch_passage("John 3:1-17 or Hezekiah 1:1", "web")
    assert (mixed.status, [s.status for s in mixed.sections]) == ("not_found", ["ok", "not_found"])
    # assemble_passage is the one derivation (T10 reuses it); nothing at all is not_found, never ok
    ok = sf.Part("John 3:1-17", "ok", "Nicodemus came by night.")
    gone = sf.Part("Matthew 17:1-9", "unavailable", None)
    assert sf.assemble_passage("R", ["A", "B"], [[ok], [ok, gone]]) == sf.Passage("R", "unavailable", (
        sf.Section("A", "ok", "Nicodemus came by night."),
        sf.Section("B", "unavailable", "Nicodemus came by night."),
    ))
    assert sf.assemble_passage(";", [], []) == sf.Passage(";", "not_found", ())


def test_all_404_not_found_text_none():
    seen = _install({"/hezekiah 1:1": 404, "/hezekiah 2:2": 404})
    passage = sf.fetch_passage("Hezekiah 1:1; 2:2", "web")
    assert [r.url.path for r in seen] == ["/hezekiah 1:1", "/hezekiah 2:2"]
    assert passage == sf.Passage("Hezekiah 1:1; 2:2", "not_found", (
        sf.Section("Hezekiah 1:1; 2:2", "not_found", None),))
    assert sf.get_passage_text("Hezekiah 1:1; 2:2") is None


def test_esv_empty_passages_not_found(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = _install({ESV_PATH: ESV_EMPTY})
    passage = sf.fetch_passage("Hezekiah 1:1", "esv")
    assert passage == sf.Passage("Hezekiah 1:1", "not_found", (
        sf.Section("Hezekiah 1:1", "not_found", None),))
    assert len(seen) == 1
    # An ESV 200 of the wrong shape is unreadable, not "not found" (owner decision 1).
    for odd in (["a"], {"x": 1}, {"passages": None}):
        _install({ESV_PATH: lambda request, body=odd: httpx.Response(200, json=body)})
        assert sf.fetch_part("John 3:16", "esv") == sf.Part("John 3:16", "unavailable", None)
    monkeypatch.delenv("ESV_API_KEY")
    seen = _install({ESV_PATH: ESV_EMPTY})
    assert sf.fetch_part("John 3:16", "esv") == sf.Part("John 3:16", "unavailable", None)
    assert seen == []                                      # no key: nothing is sent


# --- budget and caching ---

def test_budget_exhausted_unavailable_not_sent_not_cached_cache_hit_served(budget_clock, caplog, monkeypatch):
    seen = _install({"/isaiah 50:4-9": BIBLE_OK, "/isaiah 51:1-3": "Listen to me."})
    assert sf.fetch_part("Isaiah 50:4-9", "web").status == "ok"          # 1 of the 15 tokens
    for _ in range(14):
        assert budget.try_acquire("bible_api")
    with caplog.at_level(logging.INFO, logger="scripture_fetcher"):
        skipped = sf.fetch_part("Isaiah 51:1-3", "web")
    assert skipped == sf.Part("Isaiah 51:1-3", "unavailable", None)
    assert [r.url.path for r in seen] == ["/isaiah 50:4-9"]              # not sent
    assert _skips_and_failures(caplog) == ["passage_part_skipped reason=budget upstream=bible_api"]
    assert sf.fetch_part("Isaiah 50:4-9", "web") == sf.Part("Isaiah 50:4-9", "ok", _text_of(BIBLE_OK))
    assert len(seen) == 1                                                # a cache hit takes no token
    budget_clock.advance(2)                                              # 15 per 30 s: one token back
    assert sf.fetch_part("Isaiah 51:1-3", "web") == sf.Part("Isaiah 51:1-3", "ok", "Listen to me.")
    assert [r.url.path for r in seen] == ["/isaiah 50:4-9", "/isaiah 51:1-3"]   # the miss was not cached
    # ESV draws on its own budget, through the module attribute T10 patches
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    monkeypatch.setattr(budget, "try_acquire", lambda upstream: False)
    assert sf.fetch_part("John 3:16", "esv") == sf.Part("John 3:16", "unavailable", None)
    assert len(seen) == 2


def test_bible_api_cached_7_days():
    assert (sf.PART_CACHE_MAXSIZE, sf.PART_CACHE_TTL_SECONDS) == (2000, 604_800)
    clock = FakeClock()
    before = sf._PART_CACHE
    sf.reset_for_tests(clock.now)
    assert sf._PART_CACHE is not before                  # a new object (2a clarification 39)
    seen = _install({"/isaiah 50:4-9": BIBLE_OK})
    first = sf.fetch_part("Isaiah 50:4-9", "web")
    assert first == sf.Part("Isaiah 50:4-9", "ok", _text_of(BIBLE_OK))
    clock.advance(WEEK - 1)
    assert sf.fetch_part("Isaiah 50:4-9", "web") == first
    assert len(seen) == 1
    assert sf.fetch_part("Isaiah 50:4-9", "kjv").status == "ok"   # keyed by translation too
    assert len(seen) == 2
    clock.advance(1)                                     # 7 days after the first fetch
    assert sf.fetch_part("Isaiah 50:4-9", "web") == first
    assert len(seen) == 3


def test_not_found_cached():
    clock = FakeClock()
    sf.reset_for_tests(clock.now)
    seen = _install({"/hezekiah 1:1": 404, "/hezekiah 2:2": ""})
    assert sf.fetch_part("Hezekiah 1:1", "web") == sf.Part("Hezekiah 1:1", "not_found", None)
    assert sf.fetch_part("Hezekiah 2:2", "web") == sf.Part("Hezekiah 2:2", "not_found", None)  # empty text
    clock.advance(WEEK - 1)
    assert sf.fetch_part("Hezekiah 1:1", "web").status == "not_found"
    assert sf.fetch_part("Hezekiah 2:2", "web").status == "not_found"
    assert len(seen) == 2


def test_transient_failure_not_cached():
    answers = {"/isaiah 50:4-9": 500}
    seen = _install(answers)
    failures = [500, 429, 403, _read_timeout,
                lambda request: httpx.Response(200, text="<html>busy</html>"),
                lambda request: httpx.Response(200, json=["not", "an", "object"]),
                lambda request: httpx.Response(200, json={"reference": "x"}),        # no "text"
                lambda request: httpx.Response(200, json={"text": 5})]
    for failure in failures:
        answers["/isaiah 50:4-9"] = failure
        assert sf.fetch_part("Isaiah 50:4-9", "web") == sf.Part("Isaiah 50:4-9", "unavailable", None)
    assert len(seen) == len(failures)                    # every failure was asked again
    answers["/isaiah 50:4-9"] = BIBLE_OK
    assert sf.fetch_part("Isaiah 50:4-9", "web").status == "ok"
    assert sf.fetch_part("Isaiah 50:4-9", "web").status == "ok"
    assert len(seen) == len(failures) + 1                # only the success was stored


def test_esv_never_cached(monkeypatch):
    monkeypatch.setenv("ESV_API_KEY", "test-key")
    seen = _install({ESV_PATH: ESV_OK})
    for _ in range(2):
        assert sf.fetch_part("John 3:16", "esv") == sf.Part(
            "John 3:16", "ok", "For God so loved the world. (ESV)")
    assert len(seen) == 2


def test_get_passage_text_none_never_sentinel_ignores_non_ok():
    seen = _install({"/hezekiah 1:1": 404, "/john 3:16": "For God so loved the world.",
                     "/matthew 17:1-9": 503, "/genesis 2:15-17": "The garden.", "/genesis 3:1-7": 404})
    assert sf.get_passage_text("Hezekiah 1:1") is None
    assert sf.get_passage_text("") is None and sf.get_passage_text(";") is None
    assert sf.get_passage_text("John 3:16 or Matthew 17:1-9") == "For God so loved the world."
    assert sf.get_passage_text("Genesis 2:15-17; 3:1-7") is None      # a not_found section's text is left out
    assert {r.url.params["translation"] for r in seen} == {"web"}     # the default translation
    assert "[Could not load text]" not in inspect.getsource(sf)
    assert repr(sf.NOT_FOUND) == "NOT_FOUND"
