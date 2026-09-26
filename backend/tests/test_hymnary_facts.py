import datetime
import sys
import uuid

import httpx
import pytest
from sqlalchemy import select

import backfill_hymn_facts
import hymnary_facts as hf
from db import session_scope
from db.models import Hymn, HymnCatalog


@pytest.mark.parametrize("record, year", [
    ({"date": "1826"}, 1826),
    ({"date": "c. 1200", "author": "Perronet, Edward, 1721-1792"}, 1200),   # date wins
    ({"author": "Perronet, Edward, 1721-1792"}, 1792),
    ({"author": "Heermann, Johann, 1585-1647", "translator": "Bridges, Robert, 1844-1930"}, 1930),
    ({"translator": "Seiss, Joseph A. (Joseph Augustus) 1823-1904"}, 1904),
    ({"author": "Wren, Brian, 1936-"}, 1936 + hf.BIRTH_ONLY_OFFSET),
    # Life dates written with an en dash, as in the live "Psalm 23" response.
    ({"author": "Franzén, Frans Michael, 1772-1847", "adapter": "Price, Charles P., 1920–1999"}, 1999),
    ({"author": "Wren, Brian, 1936—"}, 1936 + hf.BIRTH_ONLY_OFFSET),   # em dash
    # Roles qualified in parentheses, as in the live "Psalm 23" and "Isaiah 6:3" responses.
    ({"author (attributed to)": "Lyte, Henry Francis, 1793-1847"}, 1847),
    ({"author (st. 4, 5)": "Montgomery, James, 1771-1854", "author (st. 1, 2, 3)": "Anonymous"}, 1854),
    ({"translator (dutch)": "De Moor, Robert, 1950-"}, 1950 + hf.BIRTH_ONLY_OFFSET),
    ({"versifier": "Idle, Christopher M., 1938-"}, 1938 + hf.BIRTH_ONLY_OFFSET),
    # Only a death year, or only a birth year, marked "d." or "b.".
    ({"author": "Kethe, William, d. 1594"}, 1594),
    ({"author": "Tel, Martin, b. 1964"}, 1964 + hf.BIRTH_ONLY_OFFSET),
    ({"composer": "Smart, Henry, 1813-1879", "place of origin": "England"}, None),   # not a writer of words
    ({"author": "Latin hymn, 12th cent."}, None),
    ({}, None),
])
def test_text_year(record, year):
    assert hf.text_year(record) == year


def test_text_year_never_guesses_a_future_year_for_a_recent_writer():
    # Birth year + BIRTH_ONLY_OFFSET would land in the future for a writer born
    # recently, so the estimate stops at this year.
    this_year = datetime.date.today().year
    born = this_year - 10
    for value in (f"Smith, Jane, {born}-", f"Smith, Jane, {born}–", f"Smith, Jane, b. {born}"):
        assert hf.text_year({"author": value}) == this_year, value
    # An estimate that is already in the past is left alone.
    assert hf.text_year({"author": f"Smith, Jane, {this_year - 40}-"}) == this_year - 5


@pytest.mark.parametrize("record, count", [
    ({"number of hymnals": "3918"}, 3918),
    ({"number of hymnals": "1,322"}, 1322),
    ({"number of hymnals": ""}, None),
    ({}, None),
])
def test_hymnal_count(record, count):
    assert hf.hymnal_count(record) == count


def test_normalize_title_ignores_case_punctuation_and_leading_article():
    assert hf.normalize_title("Holy, Holy, Holy! Lord God Almighty") == \
        hf.normalize_title("holy holy holy lord god almighty")
    assert hf.normalize_title("The Church's One Foundation") == hf.normalize_title("Church's One Foundation")
    assert hf.normalize_title("O Come, All Ye Faithful") != hf.normalize_title("Come, All Ye Faithful")
    assert hf.normalize_title("  ") == ""


@pytest.mark.parametrize("refs, expected", [
    ("Isaiah 6:1-8; Revelation 4:8", ["Isaiah 6:1-8", "Revelation 4:8"]),
    ("Isaiah 6:1-8, Revelation 4:8", ["Isaiah 6:1-8", "Revelation 4:8"]),
    ("Romans 4:1-5, 13-17", ["Romans 4:1-5, 13-17"]),
    ("Psalm 23, 1 John 4:7", ["Psalm 23", "1 John 4:7"]),
    ("Psalm 23\nJohn 10:11", ["Psalm 23", "John 10:11"]),
    ("", []),
    (None, []),
])
def test_split_refs(refs, expected):
    assert hf.split_refs(refs) == expected


HOLY = {"title": "Holy, Holy, Holy! Lord God Almighty", "number of hymnals": "1322",
        "author": "Heber, Reginald, 1783-1826"}


class FakeFetch:
    """Stands in for the Hymnary API: {reference: json}. Counts calls per reference."""

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, ref):
        self.calls.append(ref)
        return self.responses.get(ref, [])


def test_find_facts_matches_by_title_and_caches_each_reference():
    fetch = FakeFetch({"Isaiah 6:3": {"x": {"title": "Other Hymn"}, "Holy": HOLY}})
    cache = {}
    facts = hf.find_facts("Holy, Holy, Holy", "Isaiah 6:3", fetch, cache)
    assert facts is None   # "Holy, Holy, Holy" is not the full Hymnary title
    facts = hf.find_facts("Holy, Holy, Holy! Lord God Almighty", "Isaiah 6:3", fetch, cache)
    assert facts == {"text_year": 1826, "hymnal_count": 1322}
    assert fetch.calls == ["Isaiah 6:3"]   # second lookup served from the cache


# Hymnary often gives one title to several texts. Under "Psalm 23" the API lists
# a modern "The Lord's My Shepherd" in 14 hymnals before the Rous metrical psalm
# in 769, and the Rous record carries no date or people fields.
SHEPHERD_MODERN = {"title": "The Lord's My Shepherd", "number of hymnals": "14",
                   "author": "Townend, Stuart, 1963-"}
SHEPHERD_ROUS = {"title": "The Lord's my Shepherd", "number of hymnals": "769"}
SHEPHERD_UNCOUNTED = {"title": "The Lord's My Shepherd", "number of hymnals": ""}


def test_find_facts_takes_the_most_published_text_when_titles_collide():
    fetch = FakeFetch({"Psalm 23": {"a": SHEPHERD_UNCOUNTED, "b": SHEPHERD_MODERN,
                                    "c": SHEPHERD_ROUS}})
    facts = hf.find_facts("The Lord's My Shepherd", "Psalm 23", fetch, {})
    # Both facts come from the one chosen text: the modern text's year is not borrowed.
    assert facts == {"text_year": None, "hymnal_count": 769}


def test_find_facts_compares_matches_across_all_references():
    fetch = FakeFetch({"John 10:11": {"a": SHEPHERD_MODERN},
                       "Psalm 23": {"a": SHEPHERD_MODERN, "b": SHEPHERD_ROUS}})
    facts = hf.find_facts("The Lord's My Shepherd", "John 10:11; Psalm 23", fetch, {})
    assert facts == {"text_year": None, "hymnal_count": 769}
    assert fetch.calls == ["John 10:11", "Psalm 23"]


def _capped(*records):
    """An API response at Hymnary's cap: `records` padded with unrelated texts
    to exactly RESULT_CAP entries, as the live API returns for "Psalm 23"."""
    filler = {f"filler {i}": {"title": f"Filler Hymn {i}", "number of hymnals": "5"}
              for i in range(hf.RESULT_CAP - len(records))}
    return {**{f"r{i}": r for i, r in enumerate(records)}, **filler}


def test_is_truncated_flags_a_response_at_the_cap():
    assert hf.is_truncated(_capped())
    assert hf.is_truncated(list(_capped().values()))
    assert not hf.is_truncated({"a": HOLY})
    assert not hf.is_truncated([])
    assert not hf.is_truncated(None)


def test_find_facts_leaves_a_collision_unknown_when_a_response_hits_the_cap():
    # The cap may have dropped a same-title text in more hymnals than either
    # of these, so picking one would be a guess that re-runs could never fix.
    fetch = FakeFetch({"Psalm 23": _capped(SHEPHERD_MODERN, SHEPHERD_ROUS)})
    assert hf.find_facts("The Lord's My Shepherd", "Psalm 23", fetch, {}) is None


def test_find_facts_still_matches_in_a_capped_response_when_the_title_is_unique():
    fetch = FakeFetch({"Isaiah 6:3": _capped(HOLY)})
    assert hf.find_facts(HOLY["title"], "Isaiah 6:3", fetch, {}) == \
        {"text_year": 1826, "hymnal_count": 1322}


def test_find_facts_counts_one_text_seen_under_two_references_once():
    # The same text under two references is not a collision, even with a cap.
    fetch = FakeFetch({"John 10:11": {"a": SHEPHERD_ROUS},
                       "Psalm 23": _capped(SHEPHERD_ROUS)})
    assert hf.find_facts("The Lord's My Shepherd", "John 10:11; Psalm 23", fetch, {}) == \
        {"text_year": None, "hymnal_count": 769}


# The API keys each text by its first line, and "title" is often a short name or
# missing. Catalogs such as PH1990 list hymns by first line. Both records are
# from the live "Psalm 23" response.
GUIDE_ME = {"title": "Guide Me", "number of hymnals": "1997",
            "text link": "https://hymnary.org/text/guide_me_o_thou_great_jehovah",
            "author": "Williams, William, 1717-1791", "translator": "Williams, Peter, 1723-1796"}
DISMISS = {"number of hymnals": "1351",
           "text link": "https://hymnary.org/text/lord_dismiss_us_with_thy_blessing_fill"}
DISMISS_FIRST_LINE = "Lord, dismiss us with Thy blessing, Fill our hearts with joy and peace"


def test_find_facts_matches_the_first_line_when_the_title_differs_or_is_missing():
    fetch = FakeFetch({"Psalm 23": {"Guide me, O Thou great Jehovah": GUIDE_ME,
                                    DISMISS_FIRST_LINE: DISMISS}})
    cache = {}
    assert hf.find_facts("Guide me, O Thou great Jehovah", "Psalm 23", fetch, cache) == \
        {"text_year": 1796, "hymnal_count": 1997}
    assert hf.find_facts("Guide Me", "Psalm 23", fetch, cache) == \
        {"text_year": 1796, "hymnal_count": 1997}   # the title still matches
    assert hf.find_facts(DISMISS_FIRST_LINE, "Psalm 23", fetch, cache) == \
        {"text_year": None, "hymnal_count": 1351}


def test_find_facts_counts_a_text_matching_by_title_and_first_line_once():
    # One text is not a collision with itself, so the cap does not hide it.
    fetch = FakeFetch({"Isaiah 6:3": {HOLY["title"]: HOLY, **_capped()}})
    assert hf.find_facts(HOLY["title"], "Isaiah 6:3", fetch, {}) == \
        {"text_year": 1826, "hymnal_count": 1322}


def test_find_facts_weighs_first_line_and_title_matches_alike():
    # A text whose first line is the wanted title competes with a text whose
    # title is, and the one in more hymnals wins.
    fetch = FakeFetch({"Psalm 23": {"The Lord's my shepherd, I'll not want": SHEPHERD_ROUS,
                                    "The Lord's my shepherd": {**SHEPHERD_MODERN, "title": "Townend"}}})
    assert hf.find_facts("The Lord's My Shepherd", "Psalm 23", fetch, {}) == \
        {"text_year": None, "hymnal_count": 769}
    fetch = FakeFetch({"Psalm 23": {"The Lord's my shepherd, I'll not want": SHEPHERD_MODERN,
                                    "The Lord's my shepherd": {**SHEPHERD_ROUS, "title": "Rous"}}})
    assert hf.find_facts("The Lord's My Shepherd", "Psalm 23", fetch, {}) == \
        {"text_year": None, "hymnal_count": 769}


def test_find_facts_handles_empty_results_and_missing_refs():
    fetch = FakeFetch({})
    assert hf.find_facts("Anything", "Jude 1:25", fetch, {}) is None   # API returns []
    assert hf.find_facts("Anything", "", fetch, {}) is None
    assert hf.find_facts("", "Jude 1:25", fetch, {}) is None


class FlakyFetch(FakeFetch):
    """A FakeFetch whose first request for each reference in `failing` fails."""

    def __init__(self, responses, failing):
        super().__init__(responses)
        self.failing = set(failing)

    def __call__(self, ref):
        if ref in self.failing:
            self.calls.append(ref)
            self.failing.discard(ref)
            raise hf.FetchError(ref)
        return super().__call__(ref)


def test_find_facts_leaves_a_hymn_unknown_when_a_reference_fails():
    # A failed request is not "nothing cites this reference": the failed
    # "Psalm 23" would have listed the Rous text in 769 hymnals, so taking the
    # 14-hymnal text from "John 10:11" alone would store a guess for good.
    fetch = FlakyFetch({"John 10:11": {"a": SHEPHERD_MODERN},
                        "Psalm 23": {"a": SHEPHERD_MODERN, "b": SHEPHERD_ROUS}},
                       failing=["Psalm 23"])
    cache = {}
    assert hf.find_facts("The Lord's My Shepherd", "John 10:11; Psalm 23", fetch, cache) is None
    assert "Psalm 23" not in cache   # the failure is not cached as an empty result
    assert hf.find_facts("The Lord's My Shepherd", "John 10:11; Psalm 23", fetch, cache) == \
        {"text_year": None, "hymnal_count": 769}
    assert fetch.calls == ["John 10:11", "Psalm 23", "Psalm 23"]


def test_find_facts_does_not_skip_a_capped_collision_when_a_reference_fails():
    # The failed reference hides a capped response, so a lone visible match
    # elsewhere must not be taken as unique.
    fetch = FlakyFetch({"John 10:11": {"a": SHEPHERD_MODERN},
                        "Psalm 23": _capped(SHEPHERD_MODERN, SHEPHERD_ROUS)},
                       failing=["Psalm 23"])
    assert hf.find_facts("The Lord's My Shepherd", "John 10:11; Psalm 23", fetch, {}) is None


def test_run_backfill_fills_blanks_without_overwriting(tmp_db, make_church):
    cid = make_church()
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs="Isaiah 6:3"))
        s.add(Hymn(church_id=cid, title=HOLY["title"], scripture_refs="Isaiah 6:3", text_year=1800))
        s.add(Hymn(church_id=cid, title="Unknown Hymn", scripture_refs="Isaiah 6:3"))
        s.add(Hymn(church_id=cid, title="No Refs"))
    fetch = FakeFetch({"Isaiah 6:3": {"Holy": HOLY}})

    stats = hf.run_backfill(fetch)

    assert stats == {"checked": 4, "matched": 2, "updated": 2, "unknown": 2}
    assert fetch.calls == ["Isaiah 6:3"]
    with session_scope() as s:
        cat = s.execute(select(HymnCatalog)).scalar_one()
        assert (cat.text_year, cat.hymnal_count) == (1826, 1322)
        holy = s.execute(select(Hymn).where(Hymn.title == HOLY["title"])).scalar_one()
        assert (holy.text_year, holy.hymnal_count) == (1800, 1322)   # 1800 kept
    assert hf.run_backfill(fetch)["checked"] == 2   # only the two unknowns remain blank


def test_run_backfill_dry_run_writes_nothing(tmp_db):
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs="Isaiah 6:3"))
    stats = hf.run_backfill(FakeFetch({"Isaiah 6:3": {"Holy": HOLY}}), dry_run=True)
    assert stats["updated"] == 1
    with session_scope() as s:
        assert s.execute(select(HymnCatalog)).scalar_one().text_year is None


# --- The CLI (backfill_hymn_facts.py), with the network replaced by httpx.MockTransport.

_REAL_CLIENT = httpx.Client   # the CLI test swaps httpx.Client out


def _mock_client(responses, seen=None):
    """An httpx.Client whose requests never leave the process: `responses`
    maps a reference to the JSON the fake Hymnary API returns."""
    def handler(request):
        ref = request.url.params["reference"]
        if seen is not None:
            seen.append(ref)
        return httpx.Response(200, json=responses.get(ref, []))
    return _REAL_CLIENT(transport=httpx.MockTransport(handler))


def test_make_fetch_reports_references_that_hit_the_cap(capsys):
    truncated = []
    with _mock_client({"Psalm 23": _capped(), "Isaiah 6:3": {"Holy": HOLY}}) as client:
        fetch = backfill_hymn_facts.make_fetch(client, delay=0, truncated=truncated)
        assert fetch("Isaiah 6:3") == {"Holy": HOLY}
        assert len(fetch("Psalm 23")) == hf.RESULT_CAP
    assert truncated == ["Psalm 23"]
    out = capsys.readouterr().out
    assert "Psalm 23" in out and "Isaiah 6:3" not in out


def _failing_client(fail, responses):
    """A mock client that answers `responses`, except that a reference in
    `fail` gets the failure it names ("503", "timeout" or "not json")."""
    def handler(request):
        ref = request.url.params["reference"]
        kind = fail.get(ref)
        if kind == "503":
            return httpx.Response(503, text="busy")
        if kind == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if kind == "not json":
            return httpx.Response(200, text="<html>challenge</html>")
        return httpx.Response(200, json=responses.get(ref, []))
    return _REAL_CLIENT(transport=httpx.MockTransport(handler))


def test_make_fetch_raises_on_a_failed_request_and_records_it(capsys):
    failed = []
    fail = {"Psalm 23": "503", "John 10:11": "timeout", "Psalm 100": "not json"}
    with _failing_client(fail, {"Jude 1:25": []}) as client:
        fetch = backfill_hymn_facts.make_fetch(client, delay=0, failed=failed)
        for ref in fail:
            with pytest.raises(hf.FetchError):
                fetch(ref)
        assert fetch("Jude 1:25") == []   # an empty result is still just empty
    assert failed == list(fail)
    out = capsys.readouterr().out
    assert "Jude 1:25" not in out
    assert "challenge" in out   # a body that is not JSON is shown, not just the parse error


def _unparseable(ref):
    """Hymnary's answer to a reference it cannot parse, exactly as the live API
    sends it for "Isaiah 6:3 (st. 1)": HTTP 200, text/html, one sentence."""
    return httpx.Response(200, headers={"content-type": "text/html; charset=UTF-8"},
                          text=f"Could not parse text reference '{ref}'.")


def test_make_fetch_treats_an_unparseable_reference_as_citing_nothing(capsys):
    # Hymnary gives the same answer every time, so it is not a failure to retry:
    # the reference simply finds no texts.
    failed, unparseable = [], []

    def handler(request):
        return _unparseable(request.url.params["reference"])

    with _REAL_CLIENT(transport=httpx.MockTransport(handler)) as client:
        fetch = backfill_hymn_facts.make_fetch(client, delay=0, failed=failed,
                                               unparseable=unparseable)
        assert fetch("Isaiah 6:3 (st. 1)") == []
    assert (failed, unparseable) == ([], ["Isaiah 6:3 (st. 1)"])
    assert "Could not parse text reference 'Isaiah 6:3 (st. 1)'" in capsys.readouterr().out


def test_run_backfill_matches_on_other_references_when_one_is_unparseable(tmp_db, make_church):
    cid = make_church()
    refs = "Revelation 4:8; Isaiah 6:3 (st. 1)"
    with session_scope() as s:
        s.add(HymnCatalog(title=HOLY["title"], scripture_refs=refs))
        s.add(Hymn(church_id=cid, title=HOLY["title"], scripture_refs=refs))
    seen = []

    def handler(request):
        ref = request.url.params["reference"]
        seen.append(ref)
        if ref == "Revelation 4:8":
            return httpx.Response(200, json={"Holy, holy, holy! Lord God Almighty": HOLY})
        return _unparseable(ref)

    failed, unparseable = [], []
    with _REAL_CLIENT(transport=httpx.MockTransport(handler)) as client:
        fetch = backfill_hymn_facts.make_fetch(client, delay=0, failed=failed,
                                               unparseable=unparseable)
        stats = hf.run_backfill(fetch)

    assert stats == {"checked": 2, "matched": 2, "updated": 2, "unknown": 0}
    assert seen == ["Revelation 4:8", "Isaiah 6:3 (st. 1)"]   # the bad reference is asked once
    assert (failed, unparseable) == ([], ["Isaiah 6:3 (st. 1)"])
    with session_scope() as s:
        assert s.execute(select(HymnCatalog.text_year, HymnCatalog.hymnal_count)).one() == (1826, 1322)
        assert s.execute(select(Hymn.text_year, Hymn.hymnal_count)).one() == (1826, 1322)


def test_run_backfill_stores_no_guess_when_a_request_fails(tmp_db, make_church):
    # The review case end to end: "Psalm 23" fails once (503). The first row
    # citing it stays blank rather than taking the 14-hymnal text from
    # "John 10:11"; the next row retries "Psalm 23" and gets the 769.
    cid = make_church()
    refs = "John 10:11; Psalm 23"
    with session_scope() as s:
        s.add(HymnCatalog(title="The Lord's My Shepherd", scripture_refs=refs))
        s.add(Hymn(church_id=cid, title="The Lord's My Shepherd", scripture_refs=refs))
    responses = {"John 10:11": {"a": SHEPHERD_MODERN},
                 "Psalm 23": {"a": SHEPHERD_MODERN, "b": SHEPHERD_ROUS}}
    fail = {"Psalm 23": "503"}
    seen = []

    def handler(request):
        ref = request.url.params["reference"]
        seen.append(ref)
        if fail.pop(ref, None):
            return httpx.Response(503, text="busy")
        return httpx.Response(200, json=responses.get(ref, []))

    failed = []
    with _REAL_CLIENT(transport=httpx.MockTransport(handler)) as client:
        fetch = backfill_hymn_facts.make_fetch(client, delay=0, failed=failed)
        stats = hf.run_backfill(fetch)

    assert stats == {"checked": 2, "matched": 1, "updated": 1, "unknown": 1}
    assert seen == ["John 10:11", "Psalm 23", "Psalm 23"]
    assert failed == ["Psalm 23"]
    with session_scope() as s:
        cat = s.execute(select(HymnCatalog)).scalar_one()
        assert (cat.text_year, cat.hymnal_count) == (None, None)   # no guess stored
        hymn = s.execute(select(Hymn)).scalar_one()
        assert (hymn.text_year, hymn.hymnal_count) == (None, 769)

    with _REAL_CLIENT(transport=httpx.MockTransport(handler)) as client:
        hf.run_backfill(backfill_hymn_facts.make_fetch(client, delay=0))   # a re-run fills it
    with session_scope() as s:
        assert s.execute(select(HymnCatalog.hymnal_count)).scalar_one() == 769


@pytest.fixture
def unbound_engine(tmp_db, monkeypatch):
    """The database state a fresh CLI process starts in: tables exist, but no
    engine is bound yet and DATABASE_URL names the database."""
    import db.engine as engine_mod

    monkeypatch.setenv("DATABASE_URL", tmp_db.url.render_as_string(hide_password=False))
    monkeypatch.setattr(engine_mod, "_engine", None)
    engine_mod.SessionLocal.configure(bind=None)
    yield
    if engine_mod._engine is not None:   # the engine the CLI created
        engine_mod._engine.dispose()
    engine_mod.SessionLocal.configure(bind=tmp_db)


def test_cli_binds_the_database_and_reports_coverage(tmp_db, unbound_engine, monkeypatch, capsys):
    engine = tmp_db
    with engine.begin() as conn:   # insert without a session: SessionLocal is unbound
        conn.execute(HymnCatalog.__table__.insert(), [
            {"id": uuid.uuid4(), "title": HOLY["title"], "scripture_refs": "Isaiah 6:3"},
            {"id": uuid.uuid4(), "title": "Unknown Hymn", "scripture_refs": "Psalm 23"},
        ])
    seen = []
    monkeypatch.setattr(backfill_hymn_facts.httpx, "Client", lambda **kw: _mock_client(
        {"Isaiah 6:3": {"Holy": HOLY}, "Psalm 23": _capped()}, seen))
    monkeypatch.setattr(backfill_hymn_facts.time, "sleep", lambda _s: None)

    monkeypatch.setattr(sys, "argv", ["backfill_hymn_facts.py", "--dry-run"])
    backfill_hymn_facts.main()

    out = capsys.readouterr().out
    assert "[DRY RUN] checked 2, matched 1, updated 1, unknown 1" in out
    assert "1 reference" in out and "Psalm 23" in out.splitlines()[-1]
    assert sorted(seen) == ["Isaiah 6:3", "Psalm 23"]
    with engine.connect() as conn:
        assert conn.execute(select(HymnCatalog.text_year)).scalars().all() == [None, None]

    monkeypatch.setattr(sys, "argv", ["backfill_hymn_facts.py"])
    backfill_hymn_facts.main()
    with engine.connect() as conn:
        rows = conn.execute(select(HymnCatalog.title, HymnCatalog.text_year,
                                   HymnCatalog.hymnal_count)).all()
    assert sorted(rows) == [(HOLY["title"], 1826, 1322), ("Unknown Hymn", None, None)]


def test_cli_names_references_whose_requests_failed(tmp_db, unbound_engine, monkeypatch, capsys):
    with tmp_db.begin() as conn:
        conn.execute(HymnCatalog.__table__.insert(), [
            {"id": uuid.uuid4(), "title": HOLY["title"], "scripture_refs": "Isaiah 6:3"},
            {"id": uuid.uuid4(), "title": "Other Hymn", "scripture_refs": "Psalm 23"},
        ])
    monkeypatch.setattr(backfill_hymn_facts.httpx, "Client", lambda **kw: _failing_client(
        {"Psalm 23": "503"}, {"Isaiah 6:3": {"Holy": HOLY}}))
    monkeypatch.setattr(backfill_hymn_facts.time, "sleep", lambda _s: None)
    monkeypatch.setattr(sys, "argv", ["backfill_hymn_facts.py", "--dry-run"])

    backfill_hymn_facts.main()

    out = capsys.readouterr().out
    assert "[DRY RUN] checked 2, matched 1, updated 1, unknown 1" in out
    last = out.splitlines()[-1]
    assert "1 reference" in last and "failed" in last and "Psalm 23" in last


def test_cli_names_unparseable_references_apart_from_failed_ones(tmp_db, unbound_engine,
                                                               monkeypatch, capsys):
    with tmp_db.begin() as conn:
        conn.execute(HymnCatalog.__table__.insert(), [
            {"id": uuid.uuid4(), "title": HOLY["title"], "scripture_refs": "Revelation 4:8; Isaiah 6:3 (st. 1)"},
        ])

    def handler(request):
        ref = request.url.params["reference"]
        if ref == "Revelation 4:8":
            return httpx.Response(200, json={"Holy": HOLY})
        return _unparseable(ref)

    monkeypatch.setattr(backfill_hymn_facts.httpx, "Client",
                        lambda **kw: _REAL_CLIENT(transport=httpx.MockTransport(handler)))
    monkeypatch.setattr(backfill_hymn_facts.time, "sleep", lambda _s: None)
    monkeypatch.setattr(sys, "argv", ["backfill_hymn_facts.py", "--dry-run"])

    backfill_hymn_facts.main()

    out = capsys.readouterr().out
    assert "[DRY RUN] checked 1, matched 1, updated 1, unknown 0" in out
    last = out.splitlines()[-1]
    assert "1 reference" in last and "could not parse" in last and "Isaiah 6:3 (st. 1)" in last
    assert "failed" not in out and "re-run" not in out   # a re-run would get the same answer
