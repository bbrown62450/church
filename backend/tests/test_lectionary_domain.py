"""The pure lectionary domain (S Lectionary domain; decision A; AC1, AC4).

Task 6a: the calendar (Easter, Advent, the year file) and the occasion names.
Task 6b: the Vanderbilt and Lectio parsing, the draft-limit guard and the merge.
Task 6a's tests are date arithmetic; Task 6b's also read the recorded fixtures
(`tests.upstream_fixtures`). No network, no clock.
"""
import dataclasses
import functools
import json
import logging
import re
from datetime import date, timedelta

import pytest

from scripture_refs import scripture_key
from tests import upstream_fixtures
from vanderbilt_lectionary import (
    ORDINALS,
    LectionaryFormatError,
    LectioDay,
    LectioGroup,
    ReadingSet,
    VRow,
    _ordinary_time_name,
    advent_sunday,
    clean_cell,
    easter_date,
    fits_draft_limits,
    lectio_set_name,
    liturgical_year_for,
    merge,
    ordinal_word,
    parse_lectio_payload,
    parse_vanderbilt_csv,
    sunday_name,
    vanderbilt_sets_on,
    weekday_feast_name,
)

FIRST_YEAR, LAST_YEAR = 1900, 2199  # the API's date range (S Limits)


def _sundays(start: date, end: date):
    d = start + timedelta(days=(6 - start.weekday()) % 7)
    while d <= end:
        yield d
        d += timedelta(days=7)


# --- Dates ---


def test_easter_date_known_years():
    known = {
        1900: date(1900, 4, 15),
        1943: date(1943, 4, 25),
        2008: date(2008, 3, 23),
        2024: date(2024, 3, 31),
        2025: date(2025, 4, 20),
        2026: date(2026, 4, 5),
        2027: date(2027, 3, 28),
        2028: date(2028, 4, 16),
        2038: date(2038, 4, 25),
    }
    for year, expected in known.items():
        assert easter_date(year) == expected, year
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        e = easter_date(year)
        assert e.weekday() == 6, year
        assert date(year, 3, 22) <= e <= date(year, 4, 25), year


def test_advent_sunday_2025_to_2028():
    assert advent_sunday(2025) == date(2025, 11, 30)
    assert advent_sunday(2026) == date(2026, 11, 29)
    assert advent_sunday(2027) == date(2027, 11, 28)
    assert advent_sunday(2028) == date(2028, 12, 3)
    for year in range(FIRST_YEAR, LAST_YEAR + 1):
        a = advent_sunday(year)
        assert a.weekday() == 6, year
        assert date(year, 11, 27) <= a <= date(year, 12, 3), year


def test_liturgical_year_for_boundaries():
    cases = {
        date(2027, 11, 27): "2026-27",
        date(2027, 11, 28): "2027-28",  # AC4: Advent 1 2027 starts the new file
        date(2026, 11, 28): "2025-26",  # AC4: the day before Advent 1 2026 (the C2 bug)
        date(2026, 11, 29): "2026-27",
        date(2025, 12, 24): "2025-26",
        date(2099, 12, 25): "2099-00",  # the two-digit suffix wraps
        date(1900, 1, 1): "1899-00",
    }
    for d, expected in cases.items():
        assert liturgical_year_for(d) == expected, d


# --- Names ---


def test_sunday_name_table():
    table = {
        # S "Ordinary-time occasion names" fixture (all 11 rows)
        date(2026, 5, 24): "Day of Pentecost",
        date(2026, 5, 31): "Trinity Sunday",
        date(2026, 6, 7): "Second Sunday after Pentecost",
        date(2026, 10, 4): "Nineteenth Sunday after Pentecost",
        date(2026, 11, 1): "All Saints Day",
        date(2026, 11, 22): "Christ the King",
        date(2027, 11, 21): "Christ the King",
        date(2025, 11, 23): "Christ the King",
        date(2026, 1, 11): "Baptism of the Lord",
        date(2026, 1, 18): "Second Sunday after the Epiphany",
        date(2026, 2, 15): "Transfiguration Sunday",
        # the kept seasonal wording
        date(2025, 11, 30): "First Sunday of Advent",
        date(2025, 12, 21): "Fourth Sunday of Advent",
        date(2026, 2, 22): "First Sunday in Lent",
        date(2026, 3, 22): "Fifth Sunday in Lent",
        date(2026, 3, 29): "Palm Sunday",
        date(2026, 4, 5): "Easter Sunday",
        date(2026, 4, 12): "Second Sunday of Easter",
        date(2026, 5, 17): "Seventh Sunday of Easter",
        # the Christmas season (owner answer Q3)
        date(2025, 12, 28): "First Sunday after Christmas Day",
        date(2023, 1, 1): "First Sunday after Christmas Day",
        date(2026, 1, 4): "Second Sunday after Christmas Day",
        date(2022, 12, 25): None,  # a Sunday Christmas Day: the feast name comes from weekday_feast_name
        date(2019, 1, 6): None,  # a Sunday Epiphany: likewise
        date(2019, 1, 13): "Baptism of the Lord",  # Jan 6 was the Sunday, so the Baptism is a week later
    }
    for d, expected in table.items():
        assert sunday_name(d) == expected, d


def test_sunday_name_none_for_weekdays():
    assert sunday_name(date(2026, 5, 14)) is None  # Ascension Thursday, once "Sixth Sunday of Easter"
    assert sunday_name(date(2026, 2, 18)) is None  # Ash Wednesday
    assert sunday_name(date(2025, 12, 25)) is None  # Christmas Day on a Thursday
    d = date(2025, 11, 30)
    while d <= date(2028, 12, 2):
        if d.weekday() != 6:
            assert sunday_name(d) is None, d
        d += timedelta(days=1)


def test_named_days_win_2025_to_2028():
    """AC4: each named day beats the computed ordinal in every fixture year."""
    all_saints_sundays = 0
    for year in range(2025, 2029):
        easter = easter_date(year)
        named = {
            easter + timedelta(days=56): ("Trinity Sunday", "First Sunday after Pentecost"),
            advent_sunday(year) - timedelta(days=7): ("Christ the King", " Sunday after Pentecost"),
            easter - timedelta(days=49): ("Transfiguration Sunday", " Sunday after the Epiphany"),
        }
        jan6 = date(year, 1, 6)
        baptism = jan6 + timedelta(days=(6 - jan6.weekday()) % 7 or 7)
        named[baptism] = ("Baptism of the Lord", "First Sunday after the Epiphany")
        nov1 = date(year, 11, 1)
        if nov1.weekday() == 6:
            all_saints_sundays += 1
            named[nov1] = ("All Saints Day", " Sunday after Pentecost")
        for d, (name, computed_suffix) in named.items():
            assert d.weekday() == 6, d
            assert sunday_name(d) == name, d
            computed = _ordinary_time_name(d)
            assert computed is not None and computed.endswith(computed_suffix), (d, computed)
    assert all_saints_sundays == 1  # 2026-11-01
    assert _ordinary_time_name(date(2026, 11, 1)) == "Twenty-Third Sunday after Pentecost"  # clarification 30
    assert _ordinary_time_name(date(2026, 11, 22)) == "Twenty-Sixth Sunday after Pentecost"
    assert _ordinary_time_name(date(2027, 11, 21)) == "Twenty-Seventh Sunday after Pentecost"
    assert _ordinary_time_name(date(2025, 11, 23)) == "Twenty-Fourth Sunday after Pentecost"
    assert _ordinary_time_name(date(2026, 5, 24)) is None  # the Day of Pentecost is not ordinary time
    assert _ordinary_time_name(date(2026, 12, 6)) is None  # Advent
    assert _ordinary_time_name(date(2026, 10, 6)) is None  # a Tuesday


def test_every_ordinary_sunday_named():
    """Every Sunday from 1900 to 2199 has a name; none says "Proper" (decision A).

    Only a Sunday Dec 25 or Jan 6 has no Sunday name, and those take the feast name
    (owner answer Q3). Within one liturgical year no Sunday name repeats.
    """
    for year in range(FIRST_YEAR, LAST_YEAR):
        start, end = advent_sunday(year), advent_sunday(year + 1) - timedelta(days=1)
        seen = set()
        for d in _sundays(start, end):
            name = sunday_name(d)
            if (d.month, d.day) in {(12, 25), (1, 6)}:
                assert name is None, d
                assert weekday_feast_name(d) in {"Nativity of the Lord", "Epiphany of the Lord"}, d
                continue
            assert name, d
            assert "Proper" not in name, (d, name)
            assert name not in seen, (d, name)
            seen.add(name)


def test_ordinal_words_reach_twenty_eighth():
    assert len(ORDINALS) == 28
    assert ORDINALS[0] == "First"
    assert ORDINALS[18] == "Nineteenth"
    assert ORDINALS[20] == "Twenty-First"
    assert ORDINALS[22] == "Twenty-Third"
    assert ORDINALS[27] == "Twenty-Eighth"
    assert ordinal_word(1) == "First"
    assert ordinal_word(28) == "Twenty-Eighth"
    for bad in (0, 29, -1):
        with pytest.raises(ValueError):
            ordinal_word(bad)
    # clarification 9: over 1900-2199 the largest n after Pentecost is 28, on Christ the King
    largest = max(
        (advent_sunday(y) - timedelta(days=7) - (easter_date(y) + timedelta(days=49))).days // 7
        for y in range(FIRST_YEAR, LAST_YEAR + 1)
    )
    assert largest == 28
    assert _ordinary_time_name(date(2008, 11, 23)) == "Twenty-Eighth Sunday after Pentecost"
    assert sunday_name(date(2008, 11, 23)) == "Christ the King"


def test_weekday_feast_name():
    feasts = {
        date(2026, 2, 18): "Ash Wednesday",
        date(2026, 4, 2): "Maundy Thursday",
        date(2026, 4, 3): "Good Friday",
        date(2026, 4, 4): "Holy Saturday",
        date(2026, 5, 14): "Ascension of the Lord",
        date(2025, 12, 24): "Christmas Eve",
        date(2025, 12, 25): "Nativity of the Lord",
        date(2026, 1, 1): "New Year's Day",
        date(2026, 1, 6): "Epiphany of the Lord",
        date(2025, 11, 1): "All Saints Day",
        date(2026, 11, 1): "All Saints Day",  # a Sunday: the fixed feasts are date-only
        date(2022, 12, 25): "Nativity of the Lord",  # a Sunday (owner answer Q3)
        date(2019, 1, 6): "Epiphany of the Lord",  # a Sunday (owner answer Q3)
    }
    for d, expected in feasts.items():
        assert weekday_feast_name(d) == expected, d
    for d in (date(2026, 9, 29), date(2026, 11, 26), date(2026, 4, 5), date(2026, 9, 14)):
        assert weekday_feast_name(d) is None, d


def test_lectio_set_name_precedence():
    group = LectioGroup(
        first="Acts 10:34-43",
        psalm="Psalm 118:1-2, 14-24",
        second="Colossians 3:1-4",
        gospel="John 20:1-18",
        scriptures=("Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"),
    )

    def day(season="Ordinary Time", year="A", day_name=None):
        return LectioDay(groups=(group,), season=season, year=year, day_name=day_name)

    # 1. dayName wins, even over a computed Sunday name; a blank one is ignored
    assert lectio_set_name(day(season="Easter", day_name="Resurrection of the Lord"), date(2026, 4, 5)) == (
        "Resurrection of the Lord"
    )
    assert lectio_set_name(day(season="Easter", day_name="  "), date(2026, 4, 5)) == "Easter Sunday"
    # a dayName that is only a Proper number is ignored: the Proper number is never shown (decision A)
    for proper in ("Proper 23", " proper 22 (27) ", "PROPER 5", "Proper 22\xa0(27)", "proper  22(27)"):
        assert lectio_set_name(day(day_name=proper), date(2026, 10, 4)) == "Nineteenth Sunday after Pentecost"
        assert lectio_set_name(day(day_name=proper), date(2026, 9, 29)) == "Ordinary Time — Year A"
    # 2. a Sunday takes sunday_name, never "{season} — Year {year}"
    assert lectio_set_name(day(), date(2026, 10, 4)) == "Nineteenth Sunday after Pentecost"
    # 2. a Sunday Dec 25 or Jan 6 falls back to the feast name (owner answer Q3)
    assert lectio_set_name(day(season="Christmas"), date(2022, 12, 25)) == "Nativity of the Lord"
    assert lectio_set_name(day(season="Christmas"), date(2019, 1, 6)) == "Epiphany of the Lord"
    # 2. the Sunday name wins over a fixed feast on the same Sunday
    assert lectio_set_name(day(season="Christmas"), date(2023, 1, 1)) == "First Sunday after Christmas Day"
    # 3. another day takes weekday_feast_name, never a Sunday name
    assert lectio_set_name(day(season="Easter"), date(2026, 5, 14)) == "Ascension of the Lord"
    # 4. otherwise "{season} — Year {year}", with an em dash
    assert lectio_set_name(day(), date(2026, 9, 29)) == "Ordinary Time — Year A"
    # 5. the weekday's name when season or year is missing
    assert lectio_set_name(day(season="", year=""), date(2026, 9, 29)) == "Tuesday"
    assert lectio_set_name(day(season="Ordinary Time", year=""), date(2026, 9, 29)) == "Tuesday"
    # the types are frozen
    with pytest.raises(AttributeError):
        group.first = "Genesis 1:1"


# ---------------------------------------------------------------------------
# Task 6b: Vanderbilt and Lectio parsing, the draft-limit guard, the merge.
# ---------------------------------------------------------------------------

_PROPER_ROW = re.compile(r"Proper \d+ \(\d+\)")


def _rs(name="Set", lines=("Isaiah 5:1-7",), gospel="", source="vanderbilt"):
    return ReadingSet(
        name=name, first="", psalm="", second="", gospel=gospel, scriptures=tuple(lines), source=source
    )


def _group(first="", psalm="", second="", gospel=""):
    return LectioGroup(
        first=first,
        psalm=psalm,
        second=second,
        gospel=gospel,
        scriptures=tuple(s for s in (first, psalm, second, gospel) if s),
    )


def _vrow(liturgical_date, on, first="", psalm="", second="", gospel=""):
    return VRow(
        liturgical_date=liturgical_date, calendar_date=on, first=first, psalm=psalm, second=second, gospel=gospel
    )


def _text(recorded):
    """The body decoded as its Content-Type says (UTF-8 when it names no charset, as httpx does)."""
    charset = "utf-8"
    for param in recorded.content_type.split(";")[1:]:
        key, _, value = param.strip().partition("=")
        if key.lower() == "charset" and value.strip('"'):
            charset = value.strip('"')
    return recorded.body.decode(charset)


@functools.cache
def _fixture_rows():
    recorded = upstream_fixtures.load("vanderbilt", "2025-26")
    assert recorded.status == 200
    return tuple(parse_vanderbilt_csv(_text(recorded)))


def _fixture_lectio(on):
    recorded = upstream_fixtures.load("lectio", on.isoformat())
    if recorded.status == 404:
        return None
    assert recorded.status == 200
    return parse_lectio_payload(json.loads(recorded.body))


def _merge_on(on):
    """What usecases.lectionary (Task 7) does after fetching: drop what fails the limits, then merge."""
    v_sets = [s for s in vanderbilt_sets_on(list(_fixture_rows()), on) if fits_draft_limits(s)]
    lectio = _fixture_lectio(on)
    if lectio is not None:
        groups = tuple(g for g in lectio.groups if fits_draft_limits(g))
        lectio = dataclasses.replace(lectio, groups=groups) if groups else None
    return merge(lectio, v_sets, on)


def _name_matches(expected, actual):
    if isinstance(expected, re.Pattern):
        return expected.search(actual) is not None
    return expected == actual


def _has(text):
    return re.compile(text, re.IGNORECASE)


# S "Merge" table. A str is a name this code computes (exact); a pattern is Vanderbilt's own row text,
# matched loosely so a recorded apostrophe or suffix does not matter. The last column is the Lectio
# gospel that the merged set carries (S upstream facts), or None when nothing merges.
_MERGE_TABLE = [
    (date(2026, 10, 4), [("Nineteenth Sunday after Pentecost", "merged")], 0, "Matthew 21:33-46"),
    (date(2026, 3, 29), [(_has("palms"), "vanderbilt"), (_has("passion"), "merged")], 1, "Matthew 26:14-27:66"),
    (
        date(2026, 4, 5),
        [(_has("vigil"), "vanderbilt"), (_has("resurrection"), "merged"), (_has("evening"), "vanderbilt")],
        1,
        "John 20:1-18",
    ),
    (date(2026, 5, 31), [(_has("visitation"), "vanderbilt"), (_has("trinity"), "merged")], 1, "Matthew 28:16-20"),
    (date(2026, 5, 14), [(_has("ascension"), "vanderbilt")], 0, None),
    (date(2026, 2, 18), [(_has("ash wednesday"), "merged")], 0, "Matthew 6:1-6, 16-21"),
    (date(2025, 12, 24), [(_has(r"nativity.*proper i\b"), "merged")], 0, "Luke 2:1-14 (15-20)"),
    (date(2025, 12, 25), [(_has(r"proper ii\b"), "vanderbilt"), (_has(r"proper iii\b"), "merged")], 1, "John 1:1-14"),
    (date(2026, 4, 3), [(_has("good friday"), "vanderbilt")], 0, None),
    (date(2026, 1, 1), [(_has("holy name"), "vanderbilt"), (_has("new year"), "vanderbilt")], 1, None),
    (date(2026, 11, 26), [(_has("thanksgiving"), "vanderbilt")], 0, None),
    (
        date(2026, 11, 1),
        [(_has("all saints"), "vanderbilt"), ("Twenty-Third Sunday after Pentecost", "merged")],
        1,
        "Matthew 23:1-12",
    ),
    (date(2026, 9, 29), [], None, None),
]
_MERGE_DATES = [row[0] for row in _MERGE_TABLE]

_CSV_WITH_PREAMBLE = (
    "Revised Common Lectionary, Year A\n"
    "Vanderbilt Divinity Library\n"
    "\n"
    "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
    '"Liturgy of the Palms","Mar 29, 2026","","Psalm 118:1-2, 19-29","","Matthew 21:1-11",'
    '"https://example.org/art/1","Almighty God,\n\nwe praise you."\n'
    '"Thanksgiving Day","November 26, 2026","Deuteronomy 8:7-18 Psalm 65","","2 Corinthians 9:6-15",'
    '"Luke 17:11-19","",""\n'
)


def test_parse_csv_finds_header_after_preamble():
    # The Palms row's Prayer cell spans lines, blank line included: the next row still parses.
    assert parse_vanderbilt_csv(_CSV_WITH_PREAMBLE) == [
        VRow("Liturgy of the Palms", date(2026, 3, 29), "", "Psalm 118:1-2, 19-29", "", "Matthew 21:1-11"),
        VRow(
            "Thanksgiving Day",
            date(2026, 11, 26),
            "Deuteronomy 8:7-18 Psalm 65",
            "",
            "2 Corinthians 9:6-15",
            "Luke 17:11-19",
        ),
    ]
    header_only = "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
    assert parse_vanderbilt_csv(header_only) == []
    # The recorded file keeps Vanderbilt's preamble; every merge-table date with a row is found.
    recorded_dates = {row.calendar_date for row in _fixture_rows()}
    assert set(_MERGE_DATES) - recorded_dates == {date(2026, 9, 29)}


def test_parse_csv_html_raises():
    assert issubclass(LectionaryFormatError, ValueError)
    table = "<table><tr><th>Liturgical Date</th><th>Calendar Date</th></tr></table>\n"
    for text in ("<!DOCTYPE html>\n<html><body>Page not found</body></html>\n", table, "", "\n\n"):
        with pytest.raises(LectionaryFormatError):
            parse_vanderbilt_csv(text)
    # The recorded 404 page (1999-00) and the HTML served as 200 (2045-46) are not CSV either.
    for name in ("404", "html_200"):
        body = upstream_fixtures.load("vanderbilt", name).body.decode("utf-8", errors="replace")
        with pytest.raises(LectionaryFormatError):
            parse_vanderbilt_csv(body)
    header = "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
    malformed = (
        # an unbalanced quote makes one field longer than csv's 131,072-character limit
        header + '"X","Oct 04, 2026","' + "a" * 140_000 + '","","","","",""\n',
        # a reordered header shifts every column
        "Calendar Date,Liturgical Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
        '"Oct 04, 2026","X","Isaiah 5:1-7","","","","",""\n',
        # a header missing a column
        "Liturgical Date,Calendar Date,First reading,Psalm,Gospel,Art,Prayer\n"
        '"X","Oct 04, 2026","Isaiah 5:1-7","","","",""\n',
        # data rows, none of which parses: never an empty success
        header + '"X","Sept 27, 2026","Isaiah 5:1-7","","","","",""\n"Y","2026-10-04","","","","","",""\n',
    )
    for text in malformed:
        with pytest.raises(LectionaryFormatError):
            parse_vanderbilt_csv(text)
    # A BOM, quoted labels, CRLF and extra trailing header columns are still the header.
    ok = (
        '\ufeff"Liturgical Date", "Calendar Date","First reading","Psalm","Second reading","Gospel","Art",'
        '"Prayer","Extra"\r\n"X","Oct 04, 2026","Isaiah 5:1-7","","","Matthew 21:33-46","","",""\r\n'
    )
    assert parse_vanderbilt_csv(ok) == [VRow("X", date(2026, 10, 4), "Isaiah 5:1-7", "", "", "Matthew 21:33-46")]


def test_parse_csv_skips_unparseable_dates():
    text = (
        "Liturgical Date,Calendar Date,First reading,Psalm,Second reading,Gospel,Art,Prayer\n"
        '"Season of Lent","","","","","","",""\n'
        '"Undated","TBD","Isaiah 1:1","","","","",""\n'
        '"No such day","Feb 30, 2026","Isaiah 1:1","","","","",""\n'
        '"Ash Wednesday","Feb 18, 2026","Joel 2:1-2, 12-17","Psalm 51:1-17","2 Corinthians 5:20b-6:10",'
        '"Matthew 6:1-6, 16-21","",""\n'
        '"Epiphany of the Lord","January 06, 2027","Isaiah 60:1-6","Psalm 72:1-7, 10-14","Ephesians 3:1-12",'
        '"Matthew 2:1-12","",""\n'
    )
    rows = parse_vanderbilt_csv(text)
    assert [(row.liturgical_date, row.calendar_date) for row in rows] == [
        ("Ash Wednesday", date(2026, 2, 18)),
        ("Epiphany of the Lord", date(2027, 1, 6)),
    ]


def test_clean_cell_compound_star_and_http():
    assert clean_cell("Deuteronomy 8:7-18 Psalm 65") == ["Deuteronomy 8:7-18", "Psalm 65"]
    assert clean_cell("Genesis 12:1-9 Psalm 33:1-12") == ["Genesis 12:1-9", "Psalm 33:1-12"]
    assert clean_cell('"Hosea 5:15-6:6 Psalm 50:7-15"') == ["Hosea 5:15-6:6", "Psalm 50:7-15"]
    assert clean_cell("* Acts 2:14a, 22-32") == ["Acts 2:14a, 22-32"]
    assert clean_cell('  "* 1 Peter 1:3-9"  ') == ["1 Peter 1:3-9"]
    assert clean_cell("Luke 17:11-19") == ["Luke 17:11-19"]
    assert clean_cell("Psalm 23") == ["Psalm 23"]
    assert clean_cell("https://lectionary.library.vanderbilt.edu/art.php?id=1") == []
    for blank in ("", '""', "   "):
        assert clean_cell(blank) == []
    # Nothing is split unless the text before "Psalm <n>" starts with a book.
    assert clean_cell("See the note Psalm 23") == ["See the note Psalm 23"]
    # A joining " and" or "," is not part of the head; whitespace (newlines, NBSP) collapses to one space.
    assert clean_cell("Deuteronomy 8:7-18 and Psalm 65") == ["Deuteronomy 8:7-18", "Psalm 65"]
    assert clean_cell("Genesis 1:1-5, Psalm 8") == ["Genesis 1:1-5", "Psalm 8"]
    assert clean_cell("Exodus 1:8-2:10  Psalm\xa0124") == ["Exodus 1:8-2:10", "Psalm 124"]
    assert clean_cell("Isaiah 55:1-5 or\nPsalm 145:8-9") == ["Isaiah 55:1-5 or Psalm 145:8-9"]
    # " - " splits only a cell with a heading segment (the Vigil); a verse range with spaces stays whole.
    assert clean_cell("Luke 2:1 - 20") == ["Luke 2:1 - 20"]
    assert clean_cell("Isaiah 9:2-7 - Isaiah 62:6-12") == ["Isaiah 9:2-7 - Isaiah 62:6-12"]
    assert clean_cell("Old Testament - Isaiah 9:2-7 - Isaiah 62:6-12") == ["Isaiah 9:2-7", "Isaiah 62:6-12"]
    # S's Thanksgiving Day example: the cleaned cells, in column order.
    row = _vrow(
        "Thanksgiving Day",
        date(2026, 11, 26),
        first="Deuteronomy 8:7-18 Psalm 65",
        second="2 Corinthians 9:6-15",
        gospel="Luke 17:11-19",
    )
    (thanksgiving,) = vanderbilt_sets_on([row], date(2026, 11, 26))
    assert thanksgiving == ReadingSet(
        name="Thanksgiving Day",
        first="Deuteronomy 8:7-18 Psalm 65",
        psalm="",
        second="2 Corinthians 9:6-15",
        gospel="Luke 17:11-19",
        scriptures=("Deuteronomy 8:7-18", "Psalm 65", "2 Corinthians 9:6-15", "Luke 17:11-19"),
        source="vanderbilt",
    )


def test_clean_cell_alternative_psalm_kept_whole():
    # A two-track cell splits once, before the first "Psalm"; the alternative psalm stays whole.
    assert clean_cell("Genesis 29:15-28 Psalm 105:1-11, 45b or Psalm 128") == [
        "Genesis 29:15-28",
        "Psalm 105:1-11, 45b or Psalm 128",
    ]
    # A standalone alternative psalm is one line (its head is a Psalm), clarification 10.
    assert clean_cell("Psalm 105:1-11, 45b or Psalm 128") == ["Psalm 105:1-11, 45b or Psalm 128"]
    # A head ending in " or" is an alternative, not a reading followed by its psalm.
    assert clean_cell("Isaiah 55:1-5 or Psalm 145:8-9") == ["Isaiah 55:1-5 or Psalm 145:8-9"]


def test_clean_cell_easter_vigil_eleven_lines():
    rows = _fixture_rows()
    multi = [row for row in rows if any(" - " in cell for cell in (row.first, row.psalm, row.second, row.gospel))]
    assert len(multi) == 1  # S upstream fact 5: the Vigil's First-reading cell is the only " - " cell
    vigil = multi[0]
    assert vigil.calendar_date == date(2026, 4, 5)
    assert (vigil.psalm, vigil.second, vigil.gospel) == ("", "", "")
    lines = clean_cell(vigil.first)
    assert len(lines) == 11
    assert not any(line.startswith(("Old Testament", "New Testament", "Gospel")) for line in lines)
    longest = max(lines, key=len)
    assert longest == "Baruch 3:9-15, 3:32-4:4 or Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19"
    assert len(longest) == 69
    assert "Ezekiel 36:24-28 and Psalm 42 and 43" in lines
    assert "Genesis 1:1-2:4a and Psalm 136:1-9, 23-26" in lines
    assert "Romans 6:3-11 and Psalm 114" in lines
    (vigil_set,) = [s for s in vanderbilt_sets_on(list(rows), date(2026, 4, 5)) if s.name == vigil.liturgical_date]
    assert vigil_set.scriptures == tuple(lines)
    assert vigil_set.gospel == ""  # so the Vigil never matches a Lectio group


def test_fits_draft_limits(caplog):
    ok = ["Isaiah 5:1-7"]
    assert fits_draft_limits(_rs(lines=ok))
    assert fits_draft_limits(_rs(lines=["x" * 200] * 20))
    assert fits_draft_limits(_rs(name="n" * 300, lines=ok))
    assert fits_draft_limits(_group(first="Isaiah 5:1-7", gospel="Matthew 21:33-46"))
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert not fits_draft_limits(_rs(name="Too many", lines=["Psalm 1"] * 21))
        assert not fits_draft_limits(_rs(lines=["x" * 201]))
        assert not fits_draft_limits(_rs(lines=[]))
        assert not fits_draft_limits(_rs(lines=["Psalm 1", ""]))
        assert not fits_draft_limits(_rs(name="n" * 301, lines=ok))
        assert not fits_draft_limits(_rs(name="", lines=ok))
        assert not fits_draft_limits(_group())
        assert not fits_draft_limits(_group(first="x" * 201))
    dropped = [r.getMessage() for r in caplog.records if r.getMessage().startswith("reading_set_dropped ")]
    assert len(dropped) == 8
    assert dropped[0] == (
        "reading_set_dropped name='Too many' name_chars=8 lines=21 line_chars=[7, 7, 7, 7, 7, 7, 7, 7, 7, 7, "
        "7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7]"
    )
    assert dropped[1] == "reading_set_dropped name='Set' name_chars=3 lines=1 line_chars=[201]"
    assert f"name='{'n' * 80}' name_chars=301 " in dropped[4]
    assert dropped[7] == "reading_set_dropped name='(lectio group)' name_chars=0 lines=1 line_chars=[201]"
    # A long set logs the first 25 line lengths only.
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert not fits_draft_limits(_rs(name="Long", lines=["Psalm 1"] * 30))
    (long_line,) = [r.getMessage() for r in caplog.records]
    assert long_line == "reading_set_dropped name='Long' name_chars=4 lines=30 line_chars=" + str([7] * 25)


def test_rejected_set_dropped_before_merge_default_without_it():
    on = date(2026, 3, 29)
    palms = _rs(
        name="Liturgy of the Palms", lines=["Psalm 118:1-2, 19-29", "Matthew 21:1-11"], gospel="Matthew 21:1-11"
    )
    passion = _rs(
        name="Liturgy of the Passion", lines=["Isaiah 50:4-9a"] * 21, gospel="Matthew 26:14-27:66 or Matthew 27:11-54"
    )
    lectio = LectioDay(
        groups=(_group("Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11", "Matthew 26:14-27:66"),),
        season="Lent",
        year="A",
        day_name=None,
    )
    # Unfiltered, the Passion set would take the Lectio readings and be the default.
    assert merge(lectio, [palms, passion], on)[1] == 1
    kept = [s for s in (palms, passion) if fits_draft_limits(s)]
    assert kept == [palms]
    # Filtered first: the Lectio group matches nothing left, and the default is computed without Passion.
    assert merge(lectio, kept, on) == ([palms], 0)


def test_vanderbilt_sets_on_exact_date_only():
    rows = [
        _vrow("Holy Name of Jesus", date(2026, 1, 1), gospel="Luke 2:15-21"),
        _vrow("New Year's Day", date(2026, 1, 1), gospel="Matthew 25:31-46"),
        _vrow("Liturgy of the Palms", date(2026, 3, 29), psalm="Psalm 118:1-2, 19-29", gospel="Matthew 21:1-11"),
        _vrow("Nativity of the Lord - Proper I", date(2025, 12, 24), gospel="Luke 2:1-14, (15-20)"),
    ]
    assert [s.name for s in vanderbilt_sets_on(rows, date(2026, 1, 1))] == ["Holy Name of Jesus", "New Year's Day"]
    # A row after later-dated rows is still found (the file is not in date order).
    assert [s.name for s in vanderbilt_sets_on(rows, date(2025, 12, 24))] == ["Nativity of the Lord - Proper I"]
    # No row on the date: [] (no nearest-previous fallback), weekday or Sunday alike.
    assert vanderbilt_sets_on(rows, date(2026, 3, 31)) == []
    assert vanderbilt_sets_on(rows, date(2026, 4, 12)) == []
    assert vanderbilt_sets_on([], date(2026, 3, 29)) == []
    # S upstream fact 4: the recorded file is not in date order (Nativity rows after January rows).
    recorded = [row.calendar_date for row in _fixture_rows()]
    assert recorded != sorted(recorded)


def test_proper_row_renamed_named_rows_kept():
    rows = [
        _vrow("Proper 22 (27)", date(2026, 10, 4), gospel="Matthew 21:33-46"),
        _vrow("Proper 22 (27), alternate", date(2026, 10, 4), gospel="Matthew 21:33-46"),
        _vrow("Visitation", date(2026, 5, 31), gospel="Luke 1:39-57"),
        _vrow("Trinity Sunday", date(2026, 5, 31), gospel="Matthew 28:16-20"),
        _vrow("All Saints Day", date(2026, 11, 1), gospel="Matthew 5:1-12"),
        _vrow("Proper 26 (31)", date(2026, 11, 1), gospel="Matthew 23:1-12"),
        _vrow("Proper 29 (34)", date(2026, 11, 22), gospel="Matthew 25:31-46"),
        _vrow("Proper 22 (27)", date(2026, 10, 6), gospel="Matthew 21:33-46"),
    ]

    def names(on):
        return [s.name for s in vanderbilt_sets_on(rows, on)]

    # The whole cell must be "Proper N (M)"; anything else is kept as written.
    assert names(date(2026, 10, 4)) == ["Nineteenth Sunday after Pentecost", "Proper 22 (27), alternate"]
    assert names(date(2026, 5, 31)) == ["Visitation", "Trinity Sunday"]
    # The All Saints row keeps its name; the Proper row takes the computed ordinal (clarification 30).
    assert names(date(2026, 11, 1)) == ["All Saints Day", "Twenty-Third Sunday after Pentecost"]
    # Christ the King is the rename's intended result for the last Proper.
    assert names(date(2026, 11, 22)) == ["Christ the King"]
    # Sundays only: a weekday Proper row keeps its text.
    assert names(date(2026, 10, 6)) == ["Proper 22 (27)"]
    # Any spelling of a bare Proper number is renamed; repeated names get " (2)", " (3)".
    variants = [
        _vrow(text, date(2026, 10, 4), gospel="Matthew 21:33-46")
        for text in ("Proper 22", "proper 22 (27)", "Proper 22\xa0(27)", " Proper  22(27) ")
    ]
    assert [s.name for s in vanderbilt_sets_on(variants, date(2026, 10, 4))] == [
        "Nineteenth Sunday after Pentecost",
        "Nineteenth Sunday after Pentecost (2)",
        "Nineteenth Sunday after Pentecost (3)",
        "Nineteenth Sunday after Pentecost (4)",
    ]
    trinity = [
        _vrow("Proper 4 (9)", date(2026, 5, 31), gospel="Matthew 7:21-29"),
        _vrow("Trinity Sunday", date(2026, 5, 31), gospel="Matthew 28:16-20"),
    ]
    assert [s.name for s in vanderbilt_sets_on(trinity, date(2026, 5, 31))] == ["Trinity Sunday", "Trinity Sunday (2)"]
    # The suffixed name is checked again: a 300-character name fits, with " (2)" it does not.
    long_rows = [_vrow("n" * 300, date(2026, 10, 4), gospel="John 1:1-5")] * 2
    assert [s.name for s in vanderbilt_sets_on(long_rows, date(2026, 10, 4))] == ["n" * 300]


def test_lectio_alternatives_skipped():
    payload = {
        "data": {
            "season": "Ordinary Time",
            "year": "A",
            "dayName": None,
            "readings": [
                {"type": "first", "citation": "Exodus 20:1-4, 7-9, 12-20", "isAlternative": False},
                {"type": "first", "citation": "Isaiah 5:1-7", "isAlternative": True},
                {"type": "psalm", "citation": "Psalm 19", "isAlternative": False},
                {"type": "psalm", "citation": "Psalm 80:7-15", "isAlternative": True},
                {"type": "second", "citation": "Philippians 3:4b-14"},
                {"type": "gospel", "citation": " Matthew 21:33-46 ", "isAlternative": False},
            ],
        }
    }
    assert parse_lectio_payload(payload) == LectioDay(
        groups=(
            LectioGroup(
                first="Exodus 20:1-4, 7-9, 12-20",
                psalm="Psalm 19",
                second="Philippians 3:4b-14",
                gospel="Matthew 21:33-46",
                scriptures=("Exodus 20:1-4, 7-9, 12-20", "Psalm 19", "Philippians 3:4b-14", "Matthew 21:33-46"),
            ),
        ),
        season="Ordinary Time",
        year="A",
        day_name=None,
    )
    # A missing type leaves a blank field and no line; dayName is kept, trimmed.
    day = parse_lectio_payload(
        {
            "data": {
                "dayName": " Holy Cross ",
                "readings": [{"type": "first", "citation": "Numbers 21:4b-9"}, {"type": "gospel", "citation": "John 3:13-17"}],
            }
        }
    )
    assert day.groups == (_group(first="Numbers 21:4b-9", gospel="John 3:13-17"),)
    assert (day.season, day.year, day.day_name) == ("", "", "Holy Cross")
    # The recorded 2026-10-04 response: one group, S's gospel.
    recorded = _fixture_lectio(date(2026, 10, 4))
    assert len(recorded.groups) == 1
    assert scripture_key(recorded.groups[0].gospel) == scripture_key("Matthew 21:33-46")


def test_lectio_trinity_two_groups(caplog):
    payload = {
        "data": {
            "season": "Ordinary Time",
            "year": "A",
            "dayName": None,
            "readings": [
                {"type": "first", "citation": "Genesis 6:9-22; 7:24; 8:14-19"},
                {"type": "psalm", "citation": "Psalm 46"},
                {"type": "second", "citation": "Romans 1:16-17; 3:22b-28, (29-31)"},
                {"type": "gospel", "citation": "Matthew 7:21-29"},
                {"type": "first", "citation": "Genesis 1:1-2:4a"},
                {"type": "psalm", "citation": "Psalm 8"},
                {"type": "second", "citation": "2 Corinthians 13:11-13"},
                {"type": "gospel", "citation": "Matthew 28:16-20"},
            ],
        }
    }
    day = parse_lectio_payload(payload)
    assert [g.gospel for g in day.groups] == ["Matthew 7:21-29", "Matthew 28:16-20"]
    assert day.groups[1].scriptures == ("Genesis 1:1-2:4a", "Psalm 8", "2 Corinthians 13:11-13", "Matthew 28:16-20")
    # At most 10 groups are kept; the rest are dropped with one warning that carries counts only.
    many = {"data": {"readings": [{"type": "gospel", "citation": f"John {n}:1-5"} for n in range(1, 13)]}}
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        day = parse_lectio_payload(many)
    assert [g.gospel for g in day.groups] == [f"John {n}:1-5" for n in range(1, 11)]
    (capped,) = [r.getMessage() for r in caplog.records]
    assert "12" in capped and "10" in capped and "John" not in capped
    # S upstream fact 3: the recorded Trinity response carries Proper 4 then Trinity.
    recorded = _fixture_lectio(date(2026, 5, 31))
    assert [scripture_key(g.gospel) for g in recorded.groups] == [
        scripture_key("Matthew 7:21-29"),
        scripture_key("Matthew 28:16-20"),
    ]


def test_lectio_empty_is_none():
    for payload in (
        {},
        {"data": None},
        {"data": {}},
        {"data": {"readings": []}},
        {"data": {"readings": None}},
        {"data": {"readings": [{"type": "gospel", "citation": "John 3:16", "isAlternative": True}]}},
    ):
        assert parse_lectio_payload(payload) is None, payload


def test_lectio_bad_shape_raises():
    for payload in (
        [],
        "text",
        None,
        {"data": "x"},
        {"data": ["x"]},
        {"data": {"readings": "x"}},
        {"data": {"readings": ["x"]}},
        {"data": {"readings": [{"type": "gospel", "citation": 316}]}},
    ):
        with pytest.raises((TypeError, ValueError)):
            parse_lectio_payload(payload)
    # A number for season or year is coerced, not an error (clarification 15).
    day = parse_lectio_payload(
        {"data": {"season": 7, "year": 2026, "readings": [{"type": "gospel", "citation": "John 3:16"}]}}
    )
    assert (day.season, day.year, day.day_name) == ("7", "2026", None)
    # Only a string or a (non-bool) int is text; anything else is blank, never its repr.
    day = parse_lectio_payload(
        {
            "data": {
                "season": 1.5,
                "year": True,
                "dayName": {"a": 1},
                "readings": [{"type": "gospel", "citation": "John 3:16"}],
            }
        }
    )
    assert (day.season, day.year, day.day_name) == ("", "", None)
    day = parse_lectio_payload({"data": {"dayName": ["Proper 4"], "readings": [{"type": "gospel", "citation": "J"}]}})
    assert day.day_name is None
    # Only isAlternative true skips a reading; the type is matched case-insensitively.
    day = parse_lectio_payload(
        {
            "data": {
                "readings": [
                    {"type": "First", "citation": "Isaiah 5:1-7", "isAlternative": "false"},
                    {"type": "GOSPEL", "citation": "John 3:16", "isAlternative": 1},
                    {"type": ["gospel"], "citation": "John 4:1"},
                ]
            }
        }
    )
    assert day.groups == (_group(first="Isaiah 5:1-7", gospel="John 3:16"),)


def test_lectio_names_deduplicated():
    on = date(2026, 5, 31)
    g1 = _group(first="Genesis 6:9-22", gospel="Matthew 7:21-29")
    g2 = _group(first="Genesis 1:1-2:4a", gospel="Matthew 28:16-20")
    g3 = _group(first="Isaiah 6:1-8", gospel="John 3:1-17")
    day = LectioDay(groups=(g1, g2, g3), season="Ordinary Time", year="A", day_name=None)
    sets, default = merge(day, [], on)
    assert [(s.name, s.source) for s in sets] == [
        ("Trinity Sunday", "lectio"),
        ("Trinity Sunday (2)", "lectio"),
        ("Trinity Sunday (3)", "lectio"),
    ]
    assert default == 2
    assert (sets[1].first, sets[1].gospel, sets[1].scriptures) == (g2.first, g2.gospel, g2.scriptures)
    named = dataclasses.replace(day, groups=(g1, g2), day_name="Holy Trinity")
    assert [s.name for s in merge(named, [], on)[0]] == ["Holy Trinity", "Holy Trinity (2)"]
    # Each named set is checked again (clarification 34): a 300-character name fits, " (2)" does not.
    long_name = dataclasses.replace(day, groups=(g1, g2), day_name="n" * 300)
    sets, default = merge(long_name, [], on)
    assert [s.name for s in sets] == ["n" * 300]
    assert default == 0
    too_long = dataclasses.replace(day, groups=(g1,), day_name="n" * 301)
    assert merge(too_long, [], on) == ([], None)


def test_merge_table():
    for on, expected, default, lectio_gospel in _MERGE_TABLE:
        sets, got_default = _merge_on(on)
        assert len(sets) == len(expected), (on, [s.name for s in sets])
        for reading_set, (name, source) in zip(sets, expected):
            assert _name_matches(name, reading_set.name), (on, reading_set.name)
            assert reading_set.source == source, (on, reading_set.name, reading_set.source)
            assert not _PROPER_ROW.fullmatch(reading_set.name), (on, reading_set.name)
        assert got_default == default, on
        merged = [s for s in sets if s.source == "merged"]
        if lectio_gospel is None:
            assert merged == [], on
            continue
        (merged_set,) = merged
        assert sets.index(merged_set) == default, on
        group = next(
            g for g in _fixture_lectio(on).groups if scripture_key(g.gospel) == scripture_key(lectio_gospel)
        )
        assert (merged_set.gospel, merged_set.scriptures) == (group.gospel, group.scriptures), on
    by_date = {on: _merge_on(on)[0] for on in _MERGE_DATES}
    # Easter: the Vigil keeps 11 lines and no headings.
    assert len(by_date[date(2026, 4, 5)][0].scriptures) == 11
    # Ascension: Lectio's Matthew 28 matches nothing, so Vanderbilt's Luke 24:44-53 stays.
    assert scripture_key("Luke 24:44-53") in {scripture_key(s) for s in by_date[date(2026, 5, 14)][0].scriptures}
    # Thanksgiving Day: the compound cell is split (S's example).
    assert by_date[date(2026, 11, 26)][0].scriptures == (
        "Deuteronomy 8:7-18",
        "Psalm 65",
        "2 Corinthians 9:6-15",
        "Luke 17:11-19",
    )
    # Each Lectio group replaces at most one set: a second set with the same gospel stays Vanderbilt's.
    twin_a = _rs(name="A", gospel="John 20:1-18 or Matthew 28:1-10")
    twin_b = _rs(name="B", gospel="John 20:1-18")
    one_group = LectioDay(groups=(_group(gospel="John 20:1-18"),), season="", year="", day_name=None)
    sets, default = merge(one_group, [twin_a, twin_b], date(2026, 4, 5))
    assert [(s.name, s.source) for s in sets] == [("A", "merged"), ("B", "vanderbilt")]
    assert default == 0


def test_merge_empty_and_single_source_defaults():
    on = date(2026, 10, 4)
    no_groups = LectioDay(groups=(), season="Ordinary Time", year="A", day_name=None)
    assert merge(None, [], on) == ([], None)
    assert merge(no_groups, [], on) == ([], None)
    # Vanderbilt down: the Lectio group alone, named by lectio_set_name, source "lectio", default last.
    group = _group("Exodus 20:1-4, 7-9, 12-20", "Psalm 19", "Philippians 3:4b-14", "Matthew 21:33-46")
    lectio = LectioDay(groups=(group,), season="Ordinary Time", year="A", day_name=None)
    sets, default = merge(lectio, [], on)
    assert [(s.name, s.source, s.scriptures) for s in sets] == [
        ("Nineteenth Sunday after Pentecost", "lectio", group.scriptures)
    ]
    assert default == 0
    # Lectio none (404) or no groups: the Vanderbilt sets as they are, default last (parity).
    holy_name = _rs(name="Holy Name of Jesus", lines=["Luke 2:15-21"], gospel="Luke 2:15-21")
    new_year = _rs(name="New Year's Day", lines=["Matthew 25:31-46"], gospel="Matthew 25:31-46")
    assert merge(None, [holy_name, new_year], date(2026, 1, 1)) == ([holy_name, new_year], 1)
    assert merge(no_groups, [holy_name, new_year], date(2026, 1, 1)) == ([holy_name, new_year], 1)
    # A Lectio group without a gospel never matches; unmatched groups are dropped.
    no_gospel = LectioDay(groups=(_group(first="Isaiah 5:1-7"),), season="", year="", day_name=None)
    assert merge(no_gospel, [holy_name, new_year], date(2026, 1, 1)) == ([holy_name, new_year], 1)
    # At most 10 sets come out; a match past the tenth is dropped with them.
    many = [_rs(name=f"S{n}", gospel=f"John {n}:1-5") for n in range(1, 13)]
    sets, default = merge(None, many, on)
    assert (sets, default) == (many[:10], 9)
    late = LectioDay(groups=(_group(gospel="John 12:1-5"),), season="", year="", day_name=None)
    assert merge(late, many, on) == (many[:10], 9)
    early = LectioDay(groups=(_group(gospel="John 3:1-5"),), season="", year="", day_name=None)
    sets, default = merge(early, many, on)
    assert (len(sets), default, sets[2].source) == (10, 2, "merged")


def test_every_fixture_date_fits_limits():
    assert sorted(_MERGE_DATES) == sorted(upstream_fixtures.FIXTURE_DATES)
    rows = list(_fixture_rows())
    for on in _MERGE_DATES:
        for reading_set in vanderbilt_sets_on(rows, on):
            assert fits_draft_limits(reading_set), (on, reading_set.name)
        lectio = _fixture_lectio(on)
        for group in lectio.groups if lectio else ():
            assert fits_draft_limits(group), (on, group.gospel)
        sets, default = _merge_on(on)
        assert (default is None) == (sets == [])
        for reading_set in sets:
            assert 1 <= len(reading_set.name) <= 300, (on, reading_set.name)
            assert 1 <= len(reading_set.scriptures) <= 20, (on, reading_set.name)
            assert all(1 <= len(line) <= 200 for line in reading_set.scriptures), (on, reading_set.name)
