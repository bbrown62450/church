"""Record the upstream test fixtures in backend/tests/fixtures/ (S Testing "Fixtures"; F §5).

Manual only: CI never runs this, and the test suite never touches the network.
Run it from the repo root, and only with the owner's permission, because it
makes GET requests to lectio-api.org, lectionary.library.vanderbilt.edu and
bible-api.com (never ESV, and no key is sent anywhere):

    .venv/bin/python backend/scripts/record_fixtures.py

Every fixture is a body file plus a sidecar `<name>.meta.json` holding
{"status", "content_type", "url", "recorded_at", "synthetic"}. The Vanderbilt
year files are trimmed to the fixture dates; the trim keeps the preamble, the
header line and the file's own row order, and copies each kept row verbatim.
Four fixtures are always synthetic, because they cannot be recorded (no ESV
key; Lectio cannot be made to send an HTML 200 or a 500): lectio/html_200,
lectio/error_500, esv/success and esv/empty. Every run writes them.

Each run prints one line per fixture:
  OK   <kind/name> ...  recorded as the tests expect;
  DIFF <kind/name> ...  recorded and written, but it differs from the spec's
                        upstream facts: report the line;
  FAIL <kind/name> ...  not written (site down, or the wrong status or shape);
  SYN  <kind/name> ...  written hand-built.
The exit status is 1 when any FAIL line was printed. For each FAIL, write the
hand-built version of just that fixture instead, built from the spec's
upstream facts and marked "synthetic": true:

    .venv/bin/python backend/scripts/record_fixtures.py --synthetic lectio/2026-03-29

`--synthetic all` writes every fixture hand-built (offline). `--only NAME ...`
records just those fixtures. `--list` prints every fixture name. Every run
rewrites backend/tests/fixtures/README.md from the sidecars.

This script imports nothing from backend/, so it runs without the app's settings.
"""
import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

# Kept in step with integrations/http.py and the fetchers (S Global constraints).
USER_AGENT = "WorshipServiceBuilder/1.0"
LECTIO_API_URL = "https://lectio-api.org/api/v1/readings"
VANDERBILT_YEAR_URL = "https://lectionary.library.vanderbilt.edu/calendar/{year}/?season=all&download=csv"
BIBLE_API_BASE = "https://bible-api.com"
ESV_API_BASE = "https://api.esv.org/v3/passage/text/"
# Generous: this is a manual run, not a request path.
TIMEOUT = httpx.Timeout(20.0, connect=5.0)

# The merge-table dates (S "Merge"). Lectio answers the first nine with data
# and the last four with a JSON 404 (S Upstream facts 1).
LECTIO_OK_DATES = (
    "2025-12-24", "2025-12-25", "2026-02-18", "2026-03-29", "2026-04-05",
    "2026-05-14", "2026-05-31", "2026-10-04", "2026-11-01",
)
LECTIO_404_DATES = ("2026-01-01", "2026-04-03", "2026-09-29", "2026-11-26")
LECTIO_DATES = tuple(sorted(LECTIO_OK_DATES + LECTIO_404_DATES))

# The rows each Vanderbilt year file keeps: every merge-table date in 2025-26,
# and the Advent 1 row of the next two years (the boundary tests' stubs).
VANDERBILT_KEEP = {
    "2025-26": LECTIO_DATES,
    "2026-27": ("2026-11-29",),
    "2027-28": ("2027-11-28",),
}

# How many Vanderbilt rows S's merge table expects on each date.
VANDERBILT_ROWS = {
    "2025-12-24": 1, "2025-12-25": 2, "2026-01-01": 2, "2026-02-18": 1,
    "2026-03-29": 2, "2026-04-03": 1, "2026-04-05": 3, "2026-05-14": 1,
    "2026-05-31": 2, "2026-09-29": 0, "2026-10-04": 1, "2026-11-01": 2,
    "2026-11-26": 1, "2026-11-29": 1, "2027-11-28": 1,
}

# The gospel S's merge table expects Lectio to send (the merge matches on it).
LECTIO_GOSPELS = {
    "2025-12-24": ("Luke 2:1-14 (15-20)",),
    "2025-12-25": ("John 1:1-14",),
    "2026-02-18": ("Matthew 6:1-6, 16-21",),
    "2026-03-29": ("Matthew 26:14-27:66",),
    "2026-04-05": ("John 20:1-18",),
    "2026-05-14": ("Matthew 28:16-20",),
    "2026-05-31": ("Matthew 7:21-29", "Matthew 28:16-20"),
    "2026-10-04": ("Matthew 21:33-46",),
    "2026-11-01": ("Matthew 23:1-12",),
}

VIGIL_HEADINGS = ("Old Testament Readings and Psalms", "New Testament Reading and Psalm", "Gospel")
CSV_HEADER = ("Liturgical Date", "Calendar Date", "First reading", "Psalm",
              "Second reading", "Gospel", "Art", "Prayer")

ALWAYS_SYNTHETIC = ("lectio/html_200", "lectio/error_500", "esv/success", "esv/empty")


@dataclass(frozen=True)
class Target:
    """One recordable fixture: where it is fetched from and what the tests expect."""
    key: str                 # "kind/name"
    ext: str                 # body file extension
    url: str
    params: dict | None
    status: int              # the status the tests expect


def _bible_api_url(part: str) -> str:
    # The request T9's fetcher sends: the lower-cased part, quoted with ":,-" kept.
    return f"{BIBLE_API_BASE}/{quote(part.lower(), safe=':,-')}"


def targets() -> list[Target]:
    out = [Target(f"lectio/{d}", ".json", LECTIO_API_URL, {"date": d, "tradition": "rcl"},
                  404 if d in LECTIO_404_DATES else 200) for d in LECTIO_DATES]
    out += [Target(f"vanderbilt/{y}", ".csv", VANDERBILT_YEAR_URL.format(year=y), None, 200)
            for y in VANDERBILT_KEEP]
    out += [
        Target("vanderbilt/404", ".html", VANDERBILT_YEAR_URL.format(year="1999-00"), None, 404),
        Target("vanderbilt/html_200", ".html", VANDERBILT_YEAR_URL.format(year="2045-46"), None, 200),
        Target("bible_api/isaiah_50_4-9", ".json", _bible_api_url("Isaiah 50:4-9"), {"translation": "web"}, 200),
        Target("bible_api/isaiah_50_4-9a", ".json", _bible_api_url("Isaiah 50:4-9a"), {"translation": "web"}, 404),
        Target("bible_api/luke_2_1-14_15-20", ".json", _bible_api_url("Luke 2:1-14, 15-20"),
               {"translation": "web"}, 200),
    ]
    return out


def all_names() -> list[str]:
    return [t.key for t in targets()] + list(ALWAYS_SYNTHETIC)


# --- helpers ---------------------------------------------------------------

def media_type(content_type: str) -> str:
    return content_type.split(";", 1)[0].strip().lower()


def _full_url(url: str, params: dict | None) -> str:
    return f"{url}?{urlencode(params)}" if params else url


def _parse_calendar_date(cell: str) -> date | None:
    text = cell.strip().strip('"')
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _records(lines: list[str]) -> list[list[str]]:
    """Group physical lines into CSV records: a quoted cell may hold a line break."""
    groups, current, quotes = [], [], 0
    for line in lines:
        current.append(line)
        quotes += line.count('"')
        if quotes % 2 == 0:
            groups.append(current)
            current, quotes = [], 0
    if current:
        groups.append(current)
    return groups


def trim_vanderbilt(text: str, keep: tuple[str, ...]) -> tuple[str, dict[str, list[list[str]]]]:
    """The preamble, the header line and the rows dated in `keep`, verbatim and in file order."""
    lines = text.splitlines(keepends=True)
    header_at = next((i for i, line in enumerate(lines)
                      if "Calendar Date" in line and "Liturgical Date" in line), None)
    if header_at is None:
        raise ValueError("no header line with 'Calendar Date' and 'Liturgical Date'")
    wanted = {date.fromisoformat(d): d for d in keep}
    kept = lines[: header_at + 1]
    rows: dict[str, list[list[str]]] = {d: [] for d in keep}
    for group in _records(lines[header_at + 1:]):
        raw = "".join(group)
        if not raw.strip():
            continue
        cells = next(csv.reader(io.StringIO(raw)), [])
        on = _parse_calendar_date(cells[1]) if len(cells) > 1 else None
        if on in wanted:
            kept.extend(group)
            rows[wanted[on]].append(cells)
    return "".join(kept), rows


def write_fixture(key: str, ext: str, *, status: int, content_type: str, url: str,
                  body: bytes, synthetic: bool) -> None:
    kind, name = key.split("/", 1)
    folder = FIXTURES / kind
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob(f"{name}.*"):
        old.unlink()
    (folder / f"{name}{ext}").write_bytes(body)
    meta = {
        "status": status,
        "content_type": content_type,
        "url": url,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "synthetic": synthetic,
    }
    (folder / f"{name}.meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n",
                                              encoding="utf-8")


# --- checks against the spec's upstream facts ---------------------------------

def _lectio_gospels(payload: dict) -> list[str]:
    readings = payload["data"]["readings"]
    return [r.get("citation", "").strip() for r in readings
            if r.get("type") == "gospel" and not r.get("isAlternative")]


def check(target: Target, response: httpx.Response) -> tuple[bytes, list[str], list[str]]:
    """Return (body to write, FAIL reasons, DIFF notes)."""
    fails: list[str] = []
    diffs: list[str] = []
    body = response.content
    ctype = media_type(response.headers.get("content-type", ""))
    kind, name = target.key.split("/", 1)
    if response.status_code != target.status:
        return body, [f"status {response.status_code}, expected {target.status}"], diffs
    if kind == "lectio" and target.status == 200:
        if ctype != "application/json" and not ctype.endswith("+json"):
            fails.append(f"content type {ctype!r} is not JSON")
            return body, fails, diffs
        try:
            payload = response.json()
            gospels = _lectio_gospels(payload)
        except (ValueError, KeyError, TypeError) as exc:
            return body, [f"unexpected JSON shape: {exc!r}"], diffs
        if gospels == []:
            fails.append("no readings")
        expected = list(LECTIO_GOSPELS[name])
        if gospels != expected:
            diffs.append(f"gospels {gospels}, S expects {expected}")
    elif kind == "vanderbilt" and name in VANDERBILT_KEEP:
        if ctype not in ("text/plain", "text/csv"):
            diffs.append(f"Content-Type {response.headers.get('content-type')!r}: "
                         "S's fetch_vanderbilt_year accepts only text/plain and text/csv")
        try:
            trimmed, rows = trim_vanderbilt(response.text, VANDERBILT_KEEP[name])
        except ValueError as exc:
            return body, [str(exc)], diffs
        body = trimmed.encode(response.encoding or "utf-8")
        for d, found in rows.items():
            if len(found) != VANDERBILT_ROWS[d]:
                names = [cells[0] for cells in found]
                diffs.append(f"{d}: {len(found)} rows {names}, S expects {VANDERBILT_ROWS[d]}")
        if name == "2025-26":
            vigil = [cells for cells in rows["2026-04-05"] if len(cells) > 5 and " - " in cells[2]]
            if len(vigil) != 1:
                diffs.append(f"2026-04-05: {len(vigil)} rows with a ' - ' First-reading cell, S expects 1")
            else:
                cell = vigil[0][2]
                missing = [h for h in VIGIL_HEADINGS if h not in cell]
                empty = all(not c.strip() for c in vigil[0][3:6])
                print(f"     Easter Vigil cell: {len(cell)} characters; headings missing: {missing}; "
                      f"other reading cells empty: {empty}")
                if not 513 <= len(cell) <= 517 or missing or not empty:
                    diffs.append("the Easter Vigil cell differs from S Upstream facts 5")
    elif target.key == "vanderbilt/html_200" and ctype != "text/html":
        fails.append(f"content type {ctype!r}, expected text/html")
    elif kind == "bible_api" and target.status == 200:
        try:
            text = (response.json().get("text") or "").strip()
        except ValueError as exc:
            return body, [f"body is not JSON: {exc!r}"], diffs
        if not text:
            fails.append("no 'text' in the body")
    return body, fails, diffs


def record(names: list[str]) -> int:
    failed = 0
    wanted = [t for t in targets() if t.key in names]
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": USER_AGENT}) as client:
        for target in wanted:
            url = _full_url(target.url, target.params)
            try:
                response = client.get(target.url, params=target.params)
            except httpx.HTTPError as exc:
                print(f"FAIL {target.key}: {type(exc).__name__}: {exc}")
                failed += 1
                continue
            body, fails, diffs = check(target, response)
            if fails:
                print(f"FAIL {target.key}: {'; '.join(fails)}")
                failed += 1
                continue
            content_type = response.headers.get("content-type", "")
            write_fixture(target.key, target.ext, status=response.status_code,
                          content_type=content_type, url=url, body=body, synthetic=False)
            for note in diffs:
                print(f"DIFF {target.key}: {note}")
            if not diffs:
                print(f"OK   {target.key}: {response.status_code} {content_type} {len(body)} bytes")
    return failed


# --- hand-built fixtures (S Upstream facts 1-6) -----------------------------

JSON_TYPE = "application/json; charset=utf-8"
HTML_TYPE = "text/html; charset=utf-8"
CSV_TYPE = "text/csv; charset=utf-8"

# date -> (season, groups of (first, psalm, second, gospel), alternatives)
LECTIO_SYNTHETIC = {
    "2025-12-24": ("Christmas", [("Isaiah 9:2-7", "Psalm 96", "Titus 2:11-14", "Luke 2:1-14 (15-20)")], []),
    "2025-12-25": ("Christmas", [("Isaiah 52:7-10", "Psalm 98", "Hebrews 1:1-4 (5-12)", "John 1:1-14")], []),
    "2026-02-18": ("Lent", [("Joel 2:1-2, 12-17", "Psalm 51:1-17", "2 Corinthians 5:20b-6:10",
                             "Matthew 6:1-6, 16-21")], [("first", "Isaiah 58:1-12")]),
    "2026-03-29": ("Lent", [("Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11",
                             "Matthew 26:14-27:66")], [("gospel", "Matthew 27:11-54")]),
    "2026-04-05": ("Easter", [("Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18")],
                   [("first", "Jeremiah 31:1-6"), ("gospel", "Matthew 28:1-10")]),
    "2026-05-14": ("Easter", [("Acts 1:1-11", "Psalm 47", "Ephesians 1:15-23", "Matthew 28:16-20")],
                   [("psalm", "Psalm 93")]),
    "2026-05-31": ("Ordinary Time", [
        ("Genesis 6:9-22; 7:24; 8:14-19", "Psalm 46", "Romans 1:16-17; 3:22b-28 (29-31)", "Matthew 7:21-29"),
        ("Genesis 1:1-2:4a", "Psalm 8", "2 Corinthians 13:11-13", "Matthew 28:16-20"),
    ], []),
    "2026-10-04": ("Ordinary Time", [("Exodus 20:1-4, 7-9, 12-20", "Psalm 19", "Philippians 3:4b-14",
                                      "Matthew 21:33-46")], [("first", "Isaiah 5:1-7")]),
    "2026-11-01": ("Ordinary Time", [("Joshua 3:7-17", "Psalm 107:1-7, 33-37", "1 Thessalonians 2:9-13",
                                      "Matthew 23:1-12")], [("first", "Micah 3:5-12")]),
}

VIGIL_CELL = " - ".join((
    "Old Testament Readings and Psalms",
    "Genesis 1:1-2:4a and Psalm 136:1-9, 23-26",
    "Genesis 7:1-5, 11-18; 8:6-18; 9:8-13 and Psalm 46",
    "Genesis 22:1-18 and Psalm 16",
    "Exodus 14:10-31; 15:20-21 and Exodus 15:1b-13, 17-18",
    "Isaiah 55:1-11 and Isaiah 12:2-6",
    "Baruch 3:9-15, 3:32-4:4 or Proverbs 8:1-8, 19-21; 9:4b-6 and Psalm 19",
    "Ezekiel 36:24-28 and Psalm 42 and 43",
    "Ezekiel 37:1-14 and Psalm 143",
    "Zephaniah 3:14-20 and Psalm 98",
    "New Testament Reading and Psalm",
    "Romans 6:3-11 and Psalm 114",
    "Gospel",
    "Matthew 28:1-10",
))

# Year file -> rows in file order. The Nativity rows come after the January
# rows, as in the real 2025-26 file (S Upstream facts 4).
VANDERBILT_SYNTHETIC = {
    "2025-26": [
        ("Holy Name of Jesus", "Jan 01, 2026", "Numbers 6:22-27", "Psalm 8",
         "Galatians 4:4-7 or Philippians 2:5-11", "Luke 2:15-21"),
        ("New Year's Day", "Jan 01, 2026", "Ecclesiastes 3:1-13", "Psalm 8", "Revelation 21:1-6a",
         "Matthew 25:31-46"),
        ("Nativity of the Lord - Proper I", "Dec 24, 2025", "Isaiah 9:2-7", "Psalm 96", "Titus 2:11-14",
         "Luke 2:1-14 (15-20)"),
        ("Nativity of the Lord - Proper II", "Dec 25, 2025", "Isaiah 62:6-12", "Psalm 97", "Titus 3:4-7",
         "Luke 2:(1-7) 8-20"),
        ("Nativity of the Lord - Proper III", "Dec 25, 2025", "Isaiah 52:7-10", "Psalm 98",
         "Hebrews 1:1-4 (5-12)", "John 1:1-14"),
        ("Ash Wednesday", "Feb 18, 2026", "Joel 2:1-2, 12-17 or Isaiah 58:1-12", "Psalm 51:1-17",
         "2 Corinthians 5:20b-6:10", "Matthew 6:1-6, 16-21"),
        ("Liturgy of the Palms", "Mar 29, 2026", "", "Psalm 118:1-2, 19-29", "", "Matthew 21:1-11"),
        ("Liturgy of the Passion", "Mar 29, 2026", "Isaiah 50:4-9a", "Psalm 31:9-16", "Philippians 2:5-11",
         "Matthew 26:14-27:66 or Matthew 27:11-54"),
        ("Good Friday", "Apr 03, 2026", "Isaiah 52:13-53:12", "Psalm 22",
         "Hebrews 10:16-25 or Hebrews 4:14-16; 5:7-9", "John 18:1-19:42"),
        ("Easter Vigil", "Apr 05, 2026", VIGIL_CELL, "", "", ""),
        ("Resurrection of the Lord", "Apr 05, 2026", "* Acts 10:34-43 or Jeremiah 31:1-6",
         "* Psalm 118:1-2, 14-24", "* Colossians 3:1-4 or Acts 10:34-43", "* John 20:1-18 or Matthew 28:1-10"),
        ("Easter Evening", "Apr 05, 2026", "* Isaiah 25:6-9", "* Psalm 114", "* 1 Corinthians 5:6b-8",
         "* Luke 24:13-49"),
        ("Ascension of the Lord", "May 14, 2026", "* Acts 1:1-11", "* Psalm 47 or Psalm 93",
         "* Ephesians 1:15-23", "* Luke 24:44-53"),
        ("Visitation", "May 31, 2026", "1 Samuel 2:1-10", "Psalm 113", "Romans 12:9-16b", "Luke 1:39-57"),
        ("Trinity Sunday", "May 31, 2026", "Genesis 1:1-2:4a", "Psalm 8", "2 Corinthians 13:11-13",
         "Matthew 28:16-20"),
        ("Proper 22 (27)", "Oct 04, 2026", "Exodus 20:1-4, 7-9, 12-20 Psalm 19", "Isaiah 5:1-7 Psalm 80:7-15",
         "Philippians 3:4b-14", "Matthew 21:33-46"),
        ("All Saints Day", "Nov 01, 2026", "Revelation 7:9-17", "Psalm 34:1-10, 22", "1 John 3:1-3",
         "Matthew 5:1-12"),
        ("Proper 26 (31)", "Nov 01, 2026", "Joshua 3:7-17 Psalm 107:1-7, 33-37", "Micah 3:5-12 Psalm 43",
         "1 Thessalonians 2:9-13", "Matthew 23:1-12"),
        ("Thanksgiving Day", "Nov 26, 2026", "Deuteronomy 8:7-18 Psalm 65", "", "2 Corinthians 9:6-15",
         "Luke 17:11-19"),
    ],
    "2026-27": [
        ("First Sunday of Advent", "Nov 29, 2026", "Isaiah 64:1-9", "Psalm 80:1-7, 17-19",
         "1 Corinthians 1:3-9", "Mark 13:24-37"),
    ],
    "2027-28": [
        ("First Sunday of Advent", "Nov 28, 2027", "Jeremiah 33:14-16", "Psalm 25:1-10",
         "1 Thessalonians 3:9-13", "Luke 21:25-36"),
    ],
}

YEAR_LETTER = {"2025-26": "A", "2026-27": "B", "2027-28": "C"}


def _lectio_payload(d: str) -> bytes:
    season, groups, alternatives = LECTIO_SYNTHETIC[d]
    readings = []
    for group in groups:
        readings += [{"type": t, "citation": c, "isAlternative": False}
                     for t, c in zip(("first", "psalm", "second", "gospel"), group)]
    readings += [{"type": t, "citation": c, "isAlternative": True} for t, c in alternatives]
    payload = {"data": {"date": d, "tradition": "rcl", "season": season, "year": "A",
                        "dayName": None, "readings": readings}}
    return (json.dumps(payload, indent=2) + "\n").encode("utf-8")


def _vanderbilt_csv(year: str) -> bytes:
    out = io.StringIO()
    out.write(f"Revised Common Lectionary, Year {YEAR_LETTER[year]} ({year})\r\n")
    out.write("Vanderbilt Divinity Library\r\n\r\n")
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for row in VANDERBILT_SYNTHETIC[year]:
        writer.writerow(row + ("", ""))
    return out.getvalue().encode("utf-8")


def _bible_api_body(reference: str) -> bytes:
    text = f"Synthetic verse text for {reference}.\n"
    body = {"reference": reference, "text": text, "translation_id": "web",
            "translation_name": "World English Bible", "verses": []}
    return (json.dumps(body, indent=2) + "\n").encode("utf-8")


def synthetic(key: str) -> tuple[str, int, str, str, bytes]:
    """(ext, status, content_type, url, body) for one hand-built fixture."""
    kind, name = key.split("/", 1)
    target = {t.key: t for t in targets()}.get(key)
    url = _full_url(target.url, target.params) if target else ""
    if key == "lectio/html_200":
        body = b"<!DOCTYPE html>\n<html><head><title>Maintenance</title></head>" \
               b"<body><p>This site is down for maintenance.</p></body></html>\n"
        return ".html", 200, HTML_TYPE, _full_url(LECTIO_API_URL, {"date": "2026-03-29", "tradition": "rcl"}), body
    if key == "lectio/error_500":
        body = b'{"error": "Internal Server Error"}\n'
        return ".json", 500, JSON_TYPE, _full_url(LECTIO_API_URL, {"date": "2026-03-29", "tradition": "rcl"}), body
    if key == "esv/success":
        body = {"query": "John 3:16", "canonical": "John 3:16",
                "passages": ["For God so loved the world. (ESV)"]}
        return ".json", 200, JSON_TYPE, _full_url(ESV_API_BASE, {"q": "John 3:16"}), \
            (json.dumps(body, indent=2) + "\n").encode("utf-8")
    if key == "esv/empty":
        return ".json", 200, JSON_TYPE, _full_url(ESV_API_BASE, {"q": "Hezekiah 1:1"}), b'{"passages": []}\n'
    if kind == "lectio" and name in LECTIO_404_DATES:
        body = {"success": False, "error": {"code": "NOT_FOUND", "message": f"No readings found for {name}"}}
        return ".json", 404, JSON_TYPE, url, (json.dumps(body) + "\n").encode("utf-8")
    if kind == "lectio":
        return ".json", 200, JSON_TYPE, url, _lectio_payload(name)
    if kind == "vanderbilt" and name in VANDERBILT_SYNTHETIC:
        return ".csv", 200, CSV_TYPE, url, _vanderbilt_csv(name)
    if key == "vanderbilt/404":
        body = b"<!DOCTYPE html>\n<html><head><title>404 Not Found</title></head>" \
               b"<body><h1>Not Found</h1></body></html>\n"
        return ".html", 404, HTML_TYPE, url, body
    if key == "vanderbilt/html_200":
        body = b"<!DOCTYPE html>\n<html><head><title>Lectionary Calendar</title></head>" \
               b"<body><p>No calendar is available for this year.</p></body></html>\n"
        return ".html", 200, HTML_TYPE, url, body
    if key == "bible_api/isaiah_50_4-9":
        return ".json", 200, JSON_TYPE, url, _bible_api_body("Isaiah 50:4-9")
    if key == "bible_api/isaiah_50_4-9a":
        return ".json", 404, JSON_TYPE, url, b'{"error": "not found"}\n'
    if key == "bible_api/luke_2_1-14_15-20":
        return ".json", 200, JSON_TYPE, url, _bible_api_body("Luke 2:1-14, 15-20")
    raise KeyError(key)


def write_synthetic(names: list[str]) -> None:
    for key in names:
        ext, status, content_type, url, body = synthetic(key)
        write_fixture(key, ext, status=status, content_type=content_type, url=url, body=body, synthetic=True)
        print(f"SYN  {key}: {status} {content_type} {len(body)} bytes")


# --- README ------------------------------------------------------------------

README_HEAD = """# Upstream test fixtures

Recorded or hand-built answers from the four upstreams the lectionary and
passage code calls. Tests replay them with respx or `httpx.MockTransport`
(`backend/tests/upstream_fixtures.py`); no test touches the network.

Each fixture is a body file plus `<name>.meta.json`:
`{"status", "content_type", "url", "recorded_at", "synthetic"}`.
The Vanderbilt year files are trimmed to the fixture dates (preamble, header
and file order kept; each kept row verbatim).

`shared/` holds the hand-written Python/TypeScript cases (not recorded).

This file is rewritten by the recorder. To refresh the fixtures (network;
owner's permission; never in CI), from the repo root:

    .venv/bin/python backend/scripts/record_fixtures.py

and for any fixture it reports as FAIL, the hand-built version:

    .venv/bin/python backend/scripts/record_fixtures.py --synthetic <kind/name>

| Fixture | Status | Content-Type | Made |
|---|---|---|---|
"""

# Kept in the recorder so a re-recording never drops it (Task 5 checks for it).
README_SHARED = """
## shared/

- `shared/scripture_refs.json` is hand-written, not recorded, so it has no `.meta.json` sidecar. It is the authority for `backend/scripture_refs.py` and for 2b's `frontend/src/lib/scripture-refs.ts`: change a case here first, then both ports. `backend/tests/test_scripture_refs.py` runs it in pytest; 2b's `lib/scripture-refs.test.ts` reads it with `fs` from `../backend/tests/fixtures/shared/`. The top-level `"_about"` key documents each section's encoding. Slice 5a adds its `doc_readings` cases to the `resolve_readings` section.
"""


def write_readme() -> None:
    lines = [README_HEAD]
    for meta_path in sorted(FIXTURES.glob("*/*.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        key = f"{meta_path.parent.name}/{meta_path.name.removesuffix('.meta.json')}"
        made = "synthetic" if meta["synthetic"] else f"recorded {meta['recorded_at'][:10]}"
        lines.append(f"| `{key}` | {meta['status']} | `{meta['content_type']}` | {made} |\n")
    lines.append(README_SHARED)
    (FIXTURES / "README.md").write_text("".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--only", nargs="+", metavar="KIND/NAME", help="record just these fixtures")
    group.add_argument("--synthetic", nargs="+", metavar="KIND/NAME",
                       help="write the hand-built version of these fixtures ('all' for every one)")
    group.add_argument("--list", action="store_true", help="print every fixture name")
    args = parser.parse_args(argv)
    names = all_names()
    if args.list:
        print("\n".join(names))
        return 0
    chosen = args.synthetic or args.only or []
    if chosen == ["all"]:
        chosen = names
    unknown = [n for n in chosen if n not in names]
    if unknown:
        parser.error(f"unknown fixture(s): {', '.join(unknown)}; see --list")
    if args.synthetic:
        write_synthetic(chosen)
        failed = 0
    else:
        recordable = [t.key for t in targets()]
        failed = record(chosen or recordable)
        write_synthetic([n for n in ALWAYS_SYNTHETIC if not chosen or n in chosen])
    write_readme()
    if failed:
        print(f"{failed} fixture(s) failed: write each with --synthetic <kind/name>.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
