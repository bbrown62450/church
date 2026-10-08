"""The hymnals a church can add from Settings → Hymns (6a spec, `hymnal_sources.py`;
slice 6a-2): the bundled CSV files and the shared catalog.

- File sources: one per `seed/hymnals/<CODE>.csv` (PH1990 today), read once
  and kept (`file_sources`, no database). A CSV needs `number` and `title`;
  `scripture_refs` and `theme` (or `topics`) are optional; a Hymnary.org
  link is built from the code and the number. Files are read as `utf-8-sig`,
  so a byte order mark does not hide the `number` column.
- Catalog sources: each hymnal in `hymn_catalog` (GG2013 in production), the
  rows a new church is seeded with. A file source wins over a catalog source
  with the same code.

`rows_for(code)` gives the rows `repos.hymns.import_hymns` takes. Railway
deploys only `backend/`, so the CSVs live under it. No FastAPI, Starlette or
Streamlit here.
"""
import csv
import functools
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TextIO, Union

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from db.models import HymnCatalog

SEED_DIR = Path(__file__).parent / "seed" / "hymnals"

# Names shown beside a code; a code without one shows the code alone.
HYMNAL_LABELS = {
    "GG2013": "Glory to God (2013)",
    "PH1990": "The Presbyterian Hymnal (1990)",
}


@dataclass(frozen=True)
class BundledSource:
    code: str
    label: Optional[str]
    hymn_count: int
    has_scripture_refs: bool


def label_for(code: str) -> Optional[str]:
    return HYMNAL_LABELS.get(code)


def load_rows(source: Union[Path, str, TextIO], hymnal: str) -> list[dict]:
    """The rows of a hymnal CSV (a path or an open text stream), in file order;
    a row without a title is skipped. Each row: number (the text, or None),
    title, scripture_refs, theme, hymnary_link."""
    if isinstance(source, (str, Path)):
        with open(source, encoding="utf-8-sig", newline="") as f:
            return load_rows(f, hymnal)
    text = source.read()
    if text.startswith("\ufeff"):              # a stream opened without utf-8-sig
        text = text[1:]
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        number = (r.get("number") or "").strip()
        title = (r.get("title") or "").strip()
        if not title:
            continue
        rows.append({
            "number": number or None,
            "title": title,
            "scripture_refs": (r.get("scripture_refs") or "").strip() or None,
            "theme": (r.get("theme") or r.get("topics") or "").strip() or None,
            "hymnary_link": f"https://hymnary.org/hymn/{hymnal}/{number}" if number else None,
        })
    return rows


@functools.lru_cache(maxsize=1)
def file_sources() -> dict[str, tuple[dict, ...]]:
    """Each bundled CSV's rows by code (the file name without `.csv`), read once."""
    return {path.stem: tuple(load_rows(path, path.stem)) for path in sorted(SEED_DIR.glob("*.csv"))}


def list_bundled(*, session: Session) -> list[BundledSource]:
    """Every hymnal a church can add, by code: the file sources and the
    catalog's hymnals (counted in SQL), a file winning a shared code."""
    has_refs = case((func.trim(func.coalesce(HymnCatalog.scripture_refs, "")) != "", 1), else_=0)
    found: dict[str, BundledSource] = {}
    for code, count, refs in session.execute(
        select(HymnCatalog.hymnal, func.count(), func.coalesce(func.sum(has_refs), 0))
        .where(HymnCatalog.hymnal != "")
        .group_by(HymnCatalog.hymnal)
    ).all():
        found[code] = BundledSource(code, label_for(code), int(count), int(refs) > 0)
    for code, rows in file_sources().items():
        found[code] = BundledSource(code, label_for(code), len(rows),
                                    any(r["scripture_refs"] for r in rows))
    return [found[code] for code in sorted(found)]


def rows_for(code: str, *, session: Session) -> list[dict]:
    """The rows to import for `code`: the file's, else the catalog's. KeyError
    when no source has that code."""
    files = file_sources()
    if code in files:
        return [dict(r) for r in files[code]]
    catalog = session.execute(
        select(HymnCatalog.title, HymnCatalog.number, HymnCatalog.scripture_refs, HymnCatalog.theme,
               HymnCatalog.hymnary_link, HymnCatalog.audio_url, HymnCatalog.text_year,
               HymnCatalog.hymnal_count)
        .where(HymnCatalog.hymnal == code)
    ).all()
    if not catalog:
        raise KeyError(code)
    return [{"number": c.number, "title": c.title, "scripture_refs": c.scripture_refs, "theme": c.theme,
             "hymnary_link": c.hymnary_link, "audio_url": c.audio_url, "text_year": c.text_year,
             "hymnal_count": c.hymnal_count} for c in catalog]
