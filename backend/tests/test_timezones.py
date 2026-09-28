"""One IANA check everywhere (F §7.4 "Church timezone"; S Modules added 1b):
exact, case-sensitive membership in zoneinfo.available_timezones()."""
import pytest

from timezones import is_valid_timezone


@pytest.mark.parametrize("name", ["America/New_York", "UTC", "Europe/London"])
def test_valid_timezones(name):
    assert is_valid_timezone(name) is True


@pytest.mark.parametrize("name", ["america/new_york", "Mars/Olympus", "../etc/passwd", ""])
def test_invalid_timezones(name):
    assert is_valid_timezone(name) is False
