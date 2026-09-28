"""usecases.passages: validation, planning, the shared pool and the deadline
(S "Passages", Testing "test_usecase_passages.py"; AC5; 2a clarifications 33, 39).

Every upstream call is answered by httpx.MockTransport through
integrations.http.set_http_for_tests, so nothing leaves the process (the
_no_network guard stays active). Threaded tests gate the transport on a
threading.Event, never on time.sleep, set it in `finally`, and join their
threads and the pool before they assert.
"""
import logging
import threading
import time

import httpx
import pytest

import scripture_fetcher
from domain_errors import InvalidInput
from integrations import budget, http
from usecases import passages

REFS_MESSAGE = "Enter a scripture reference."
TOO_MANY_MESSAGE = "Too many passages in one request."
TRANSLATION_MESSAGE = "Unknown or unavailable translation."


def _ref(book: str, n: int) -> str:
    """'{book} 1:1; 1:2; …; 1:n': n parts, the book carried into each (split_parts)."""
    return "; ".join([f"{book} 1:1"] + [f"1:{verse}" for verse in range(2, n + 1)])


def _install(handler) -> None:
    http.set_http_for_tests(http.build_client(transport=httpx.MockTransport(handler)))


def _text_of(request: httpx.Request) -> httpx.Response:
    """bible-api's shape: the decoded path, lower-cased by fetch_part, becomes the text."""
    return httpx.Response(200, json={"text": f"Text of {request.url.path[1:]}."})


@pytest.fixture(autouse=True)
def _no_esv_key(monkeypatch):
    """ESV is offered only with a key; these tests set one where they need it."""
    monkeypatch.delenv("ESV_API_KEY", raising=False)


def _invalid(refs, translation="web") -> InvalidInput:
    with pytest.raises(InvalidInput) as caught:
        passages.plan_passages(refs, translation)
    return caught.value


def test_empty_refs_and_blank_ref():
    for refs in ([], ["John 3:16", "   "], [""], [";"], [" ; "], ["John 3:16", "; ;"]):
        error = _invalid(refs)
        assert (error.field, error.message, error.code) == ("refs", REFS_MESSAGE, "invalid_request"), refs
    # refs are checked before the translation
    assert _invalid([], "klingon").field == "refs"


def test_twenty_one_parts_too_many():
    twenty = [_ref("Genesis", 5), _ref("Exodus", 5), _ref("Leviticus", 5), _ref("Numbers", 5)]
    assert len(passages.plan_passages(twenty, "web").parts) == passages.MAX_PARTS == 20
    twenty_one = twenty[:3] + [_ref("Numbers", 6)]
    error = _invalid(twenty_one)
    assert (error.field, error.message) == ("refs", TOO_MANY_MESSAGE)
    # alternatives count too: 20 parts plus one alternative's part
    error = _invalid(twenty[:3] + [_ref("Numbers", 5) + " or Mark 1:1"])
    assert (error.field, error.message) == ("refs", TOO_MANY_MESSAGE)


def test_unknown_or_unavailable_translation(monkeypatch):
    for translation in ("klingon", "esv", "WEB", ""):
        error = _invalid(["John 3:16"], translation)
        assert (error.field, error.message) == ("translation", TRANSLATION_MESSAGE), translation
    # the translation is checked before the part count
    too_many = [_ref("Genesis", 6), _ref("Exodus", 5), _ref("Leviticus", 5), _ref("Numbers", 5)]
    assert _invalid(too_many, "klingon").field == "translation"

    monkeypatch.setenv("ESV_API_KEY", "test-key")
    assert passages.plan_passages(["John 3:16"], "esv").translation == "esv"


def test_plan_parts_count():
    refs = ["  Romans 6:3-11 and Psalm 114 or Isaiah 50:4-9a; 51:1-3  ", "John 3:16", "Psalm 23 or ;"]
    plan = passages.plan_passages(refs, "kjv")

    assert plan.translation == "kjv"
    assert plan.refs == ("Romans 6:3-11 and Psalm 114 or Isaiah 50:4-9a; 51:1-3", "John 3:16", "Psalm 23 or ;")
    assert plan.alternatives == (
        ("Romans 6:3-11 and Psalm 114", "Isaiah 50:4-9a; 51:1-3"),
        ("John 3:16",),
        ("Psalm 23",),                       # the ";" alternative has no parts, so it is no section
    )
    assert plan.plans == (
        [["Romans 6:3-11", "Psalm 114"], ["Isaiah 50:4-9", "Isaiah 51:1-3"]],
        [["John 3:16"]],
        [["Psalm 23"]],
    )
    assert plan.plans == tuple(scripture_fetcher.plan_parts(ref) for ref in plan.refs)
    # alternatives × joined × ";" parts: the cost the route charges
    assert plan.parts == ("Romans 6:3-11", "Psalm 114", "Isaiah 50:4-9", "Isaiah 51:1-3", "John 3:16", "Psalm 23")


def test_order_preserved():
    """The first ref's part answers last, yet it stays first."""
    last_seen = threading.Event()

    def handler(request):
        if "john" in request.url.path:
            last_seen.wait(timeout=5)
        if "psalm" in request.url.path:
            last_seen.set()
        return _text_of(request)

    _install(handler)
    plan = passages.plan_passages(["John 3:16", "Genesis 1:1", "Psalm 23"], "web")
    try:
        result = passages.load_passages(plan)
    finally:
        last_seen.set()

    assert (result.translation, result.translation_label) == ("web", "World English Bible (WEB)")
    assert [(p.reference, p.status, p.sections[0].text) for p in result.passages] == [
        ("John 3:16", "ok", "Text of john 3:16."),
        ("Genesis 1:1", "ok", "Text of genesis 1:1."),
        ("Psalm 23", "ok", "Text of psalm 23."),
    ]


def test_two_concurrent_requests_never_exceed_four_in_flight(monkeypatch):
    """24 distinct parts (so the part cache's single flight merges none) from
    two requests at once: the shared pool keeps at most 4 upstream calls in
    flight. The budget is patched open, or the process-wide 15 per 30 s
    bible-api budget would answer 9 parts `unavailable` without a call."""
    monkeypatch.setattr(budget, "try_acquire", lambda upstream: True)
    changed = threading.Condition()
    state = {"in_flight": 0, "peak": 0, "calls": 0}
    release = threading.Event()

    def handler(request):
        with changed:
            state["in_flight"] += 1
            state["calls"] += 1
            state["peak"] = max(state["peak"], state["in_flight"])
            changed.notify_all()
        try:
            release.wait(timeout=10)
            return _text_of(request)
        finally:
            with changed:
                state["in_flight"] -= 1

    _install(handler)
    plans = [
        passages.plan_passages([_ref(book, 3) for book in ("Genesis", "Exodus", "Leviticus", "Numbers")], "web"),
        passages.plan_passages([_ref(book, 3) for book in ("Joshua", "Judges", "Ruth", "Esther")], "web"),
    ]
    assert len(set(plans[0].parts + plans[1].parts)) == 24
    results: dict[int, passages.PassagesResult] = {}

    def run(index: int) -> None:
        results[index] = passages.load_passages(plans[index])

    threads = [threading.Thread(target=run, args=(index,)) for index in (0, 1)]
    try:
        for thread in threads:
            thread.start()
        with changed:
            assert changed.wait_for(lambda: state["in_flight"] == 4, timeout=5)
        release.set()
        for thread in threads:
            thread.join(timeout=10)
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=10)

    assert state["peak"] == 4
    assert state["calls"] == 24
    for index in (0, 1):
        assert [p.status for p in results[index].passages] == ["ok"] * 4
        assert [p.reference for p in results[index].passages] == list(plans[index].refs)


def test_deadline_unfinished_unavailable_and_cancelled(monkeypatch, caplog):
    """Two requests of 4 parts share 4 workers that never finish: at a 0.2 s
    deadline both answer, every part `unavailable`, and the 4 parts still
    queued are cancelled, so they never reach the transport."""
    monkeypatch.setattr(budget, "try_acquire", lambda upstream: True)
    caplog.set_level(logging.WARNING, logger="usecases.passages")
    release = threading.Event()
    calls: list[str] = []
    lock = threading.Lock()

    def handler(request):
        with lock:
            calls.append(request.url.path)
        release.wait(timeout=10)
        return _text_of(request)

    _install(handler)
    plans = [passages.plan_passages([_ref("Genesis", 4)], "web"),
             passages.plan_passages([_ref("Exodus", 4)], "web")]
    results: dict[int, passages.PassagesResult] = {}
    elapsed: dict[int, float] = {}

    def run(index: int) -> None:
        started = time.monotonic()
        results[index] = passages.load_passages(plans[index], deadline=0.2)
        elapsed[index] = time.monotonic() - started

    threads = [threading.Thread(target=run, args=(index,)) for index in (0, 1)]
    try:
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=5)
        passages.reset_for_tests()        # joins the pool: the 4 running parts finish, cancelled ones never run

    for index in (0, 1):
        assert elapsed[index] < 0.2 + 0.5
        passage = results[index].passages[0]
        assert (passage.status, passage.sections[0].status, passage.sections[0].text) == (
            "unavailable", "unavailable", None)
    assert len(calls) == 4
    assert [r.getMessage() for r in caplog.records if r.name == "usecases.passages"] == [
        "passages_deadline unfinished=4 of=4"] * 2


def test_translation_options(monkeypatch):
    options = passages.translation_options()
    assert (options.default, options.esv_available) == ("web", False)
    assert options.items == scripture_fetcher.available_translations()
    assert [tid for tid, _label in options.items] == [
        "web", "kjv", "asv", "ylt", "dra", "darby", "bbe", "oeb-us", "webbe"]

    monkeypatch.setenv("ESV_API_KEY", "test-key")
    options = passages.translation_options()
    assert options.esv_available is True
    assert options.items[-1] == ("esv", "English Standard Version (ESV)")


def test_get_passage_text_reexported():
    assert passages.get_passage_text is scripture_fetcher.get_passage_text

    def handler(request):
        if "nahum" in request.url.path:
            return httpx.Response(404, json={"error": "not found"})
        return _text_of(request)

    _install(handler)
    assert passages.get_passage_text("John 3:16", "web") == "Text of john 3:16."
    assert passages.get_passage_text("Nahum 9:9", "web") is None
