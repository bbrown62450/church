"""The pure lectionary domain (S Lectionary domain; decision A; AC1, AC4).

Task 6a: the calendar (Easter, Advent, the year file) and the occasion names.
Task 6b appends the Vanderbilt and Lectio parsing and the merge tests.
Everything here is date arithmetic: no fixtures, no network, no clock.
"""
from datetime import date, timedelta

import pytest

from vanderbilt_lectionary import (
    ORDINALS,
    LectioDay,
    LectioGroup,
    _ordinary_time_name,
    advent_sunday,
    easter_date,
    lectio_set_name,
    liturgical_year_for,
    ordinal_word,
    sunday_name,
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
        date(2026, 11, 22): "Reign of Christ",
        date(2027, 11, 21): "Reign of Christ",
        date(2025, 11, 23): "Reign of Christ",
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
            advent_sunday(year) - timedelta(days=7): ("Reign of Christ", " Sunday after Pentecost"),
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
    # clarification 9: over 1900-2199 the largest n after Pentecost is 28, on Reign of Christ
    largest = max(
        (advent_sunday(y) - timedelta(days=7) - (easter_date(y) + timedelta(days=49))).days // 7
        for y in range(FIRST_YEAR, LAST_YEAR + 1)
    )
    assert largest == 28
    assert _ordinary_time_name(date(2008, 11, 23)) == "Twenty-Eighth Sunday after Pentecost"
    assert sunday_name(date(2008, 11, 23)) == "Reign of Christ"


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
