"""IANA time zone names: one check everywhere (F §7.4 "Church timezone"; S Modules added 1b).

A name is valid when it is exactly, case-sensitively, one of
zoneinfo.available_timezones(). It is not a ZoneInfo(name) lookup: on a
case-insensitive disk (macOS) ZoneInfo("america/new_york") loads, and
ZoneInfo("posixrules") loads a file that is not a zone name. The set merges
the system zoneinfo directory with the tzdata package, so a laptop and Railway
may differ at the edges; every name the browser offers (ICU) is in both.

No FastAPI, no Streamlit (tests/test_no_streamlit_in_core.py). Users:
usecases.onboarding.create_church (1b), GET /church timezone_valid (slice 2),
PATCH /church (6a).
"""
import zoneinfo
from functools import lru_cache


@lru_cache(maxsize=1)
def _zones() -> frozenset[str]:
    """Every IANA name this process knows, read once."""
    return frozenset(zoneinfo.available_timezones())


def is_valid_timezone(name: str) -> bool:
    """True when `name` is exactly an IANA zone name (case-sensitive)."""
    return name in _zones()
