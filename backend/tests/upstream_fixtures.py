"""Load the recorded upstream answers in backend/tests/fixtures/ (S Testing "Fixtures").

`load("lectio", "2026-03-29")` returns the status, Content-Type and raw body
that backend/scripts/record_fixtures.py saved, ready to replay through respx
or httpx.MockTransport. Nothing here touches the network.
"""
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# The merge-table dates (S "Merge"): Lectio has data for nine of them and
# answers 404 for 2026-01-01, 2026-04-03, 2026-09-29 and 2026-11-26.
FIXTURE_DATES: tuple[date, ...] = tuple(date.fromisoformat(d) for d in (
    "2025-12-24", "2025-12-25", "2026-01-01", "2026-02-18", "2026-03-29",
    "2026-04-03", "2026-04-05", "2026-05-14", "2026-05-31", "2026-09-29",
    "2026-10-04", "2026-11-01", "2026-11-26",
))


@dataclass(frozen=True)
class Recorded:
    status: int
    content_type: str
    body: bytes


def load(kind: str, name: str | date) -> Recorded:
    """The fixture `<kind>/<name>`: its sidecar's status and Content-Type, and the body bytes."""
    stem = name.isoformat() if isinstance(name, date) else name
    folder = FIXTURES_DIR / kind
    meta = json.loads((folder / f"{stem}.meta.json").read_text(encoding="utf-8"))
    bodies = [p for p in folder.glob(f"{stem}.*") if not p.name.endswith(".meta.json")]
    if len(bodies) != 1:
        raise FileNotFoundError(f"{kind}/{stem}: expected one body file, found {sorted(p.name for p in bodies)}")
    return Recorded(status=meta["status"], content_type=meta["content_type"], body=bodies[0].read_bytes())


# --- respx routes over the recordings (slice 2a T7) --------------------------
# The imports sit here, beside the only code that needs them (`date` is T1's
# top-level import).
from typing import Callable, Optional  # noqa: E402

import httpx  # noqa: E402
import respx  # noqa: E402

LECTIO_URL = "https://lectio-api.org/api/v1/readings"
VANDERBILT_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/"


def as_response(recorded: Recorded) -> httpx.Response:
    """A new httpx.Response with the recording's status, Content-Type and body."""
    return httpx.Response(
        recorded.status, content=recorded.body, headers={"Content-Type": recorded.content_type}
    )


def answer(recorded: Recorded) -> Callable[[httpx.Request], httpx.Response]:
    """A respx side effect that answers every call with a new copy of `recorded`."""
    return lambda request: as_response(recorded)


def route_lectio(router: respx.MockRouter, d: date, name: Optional[str] = None) -> respx.Route:
    """Lectio for exactly `d` answers with lectio/<name>; by default d's own recording."""
    return router.get(LECTIO_URL, params={"date": d.isoformat()}).mock(
        side_effect=answer(load("lectio", name or d.isoformat()))
    )


def route_vanderbilt(router: respx.MockRouter, year: str, name: Optional[str] = None) -> respx.Route:
    """The Vanderbilt file for `year` ("2025-26") answers with vanderbilt/<name>;
    by default the year's own recording."""
    return router.get(VANDERBILT_URL.format(year=year)).mock(
        side_effect=answer(load("vanderbilt", name or year))
    )
