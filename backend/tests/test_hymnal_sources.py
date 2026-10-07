"""hymnal_sources (6a spec, `hymnal_sources.py`; slice 6a-2): the bundled CSV
under backend/, the BOM-safe loader, and the file and catalog sources."""
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

import hymnal_sources
from db import session_scope
from db.models import HymnCatalog

CODE_DIR = Path(__file__).resolve().parents[1]


def test_the_bundled_ph1990_ships_under_backend_and_loads_605_rows():
    path = CODE_DIR / "seed" / "hymnals" / "PH1990.csv"
    assert path == hymnal_sources.SEED_DIR / "PH1990.csv" and path.is_file()
    assert not (CODE_DIR.parent / "data" / "hymnals").exists()
    assert (CODE_DIR.parent / "data" / ".gitkeep").is_file()    # data/ stays for the local SQLite database
    rows = hymnal_sources.load_rows(path, "PH1990")
    assert len(rows) == 605
    assert rows[0] == {"number": "1", "title": "Come, Thou long-expected Jesus", "scripture_refs": None,
                       "theme": None, "hymnary_link": "https://hymnary.org/hymn/PH1990/1"}
    assert rows[-1]["hymnary_link"] == "https://hymnary.org/hymn/PH1990/605"


def test_a_byte_order_mark_does_not_hide_the_number_column(tmp_path):
    path = tmp_path / "X1.csv"
    path.write_bytes("\ufeffnumber,title,scripture_refs\n7,Be Thou My Vision,Psalm 16\n,No Number,\n,,\n"
                     .encode("utf-8"))
    rows = hymnal_sources.load_rows(path, "X1")
    assert [(r["number"], r["title"], r["scripture_refs"], r["hymnary_link"]) for r in rows] == [
        ("7", "Be Thou My Vision", "Psalm 16", "https://hymnary.org/hymn/X1/7"),
        (None, "No Number", None, None),
    ]
    stream = io.StringIO("\ufeffnumber,title,topics\n8,Here I Am,Call\n")
    assert hymnal_sources.load_rows(stream, "X1")[0]["number"] == "8"
    assert hymnal_sources.load_rows(io.StringIO("number,title,topics\n8,Here I Am,Call\n"), "X1")[0]["theme"] == "Call"


def test_file_sources_need_no_database():
    code = "import hymnal_sources; s = hymnal_sources.file_sources(); print(sorted(s), len(s['PH1990']))"
    env = {k: v for k, v in os.environ.items() if k not in ("DATABASE_URL", "TEST_DATABASE_URL")}
    result = subprocess.run([sys.executable, "-c", code], cwd=CODE_DIR, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "['PH1990'] 605"


def test_sources_list_files_and_catalog_hymnals_a_file_winning_its_code(tmp_db):
    with session_scope() as s:
        for n, refs in ((1, "Psalm 1"), (2, None), (3, "  ")):
            s.add(HymnCatalog(hymnal="GG2013", title=f"Catalog {n}", number=n, scripture_refs=refs))
        s.add(HymnCatalog(hymnal="PH1990", title="A catalog copy", number=1))
    with session_scope() as s:
        listed = hymnal_sources.list_bundled(session=s)
        assert listed == [
            hymnal_sources.BundledSource("GG2013", "Glory to God (2013)", 3, True),
            hymnal_sources.BundledSource("PH1990", "The Presbyterian Hymnal (1990)", 605, False),
        ]
        assert len(hymnal_sources.rows_for("PH1990", session=s)) == 605          # the file, not the catalog row
        assert [(r["number"], r["title"]) for r in sorted(hymnal_sources.rows_for("GG2013", session=s),
                                                           key=lambda r: r["number"])] == [
            (1, "Catalog 1"), (2, "Catalog 2"), (3, "Catalog 3")]
        with pytest.raises(KeyError):
            hymnal_sources.rows_for("XX2000", session=s)
