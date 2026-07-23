#!/usr/bin/env python3
"""Import a hymnal CSV into a church's hymnal (idempotent, re-runnable).

CSV needs at least `number` and `title`; optional `scripture_refs`, `theme`.
A Hymnary.org link is constructed per hymn from --hymnal + number.

    python import_hymnal.py \
        --church-id <uuid> --hymnal PH1990 --csv data/hymnals/PH1990_hymns.csv
"""
import argparse
import csv

from dotenv import load_dotenv

load_dotenv()


def load_rows(csv_path: str, hymnal: str) -> list:
    rows = []
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import a hymnal CSV into a church.")
    parser.add_argument("--church-id", required=True)
    parser.add_argument("--hymnal", required=True, help="e.g. PH1990")
    parser.add_argument("--csv", required=True)
    args = parser.parse_args(argv)

    from db import init_db
    from repos.hymns import import_hymns, list_church_hymnals

    init_db()
    rows = load_rows(args.csv, args.hymnal)
    report = import_hymns(args.church_id, args.hymnal, rows)
    print(f"Imported {args.hymnal}: {report}")
    print(f"Church now has hymnals: {list_church_hymnals(args.church_id)}")


if __name__ == "__main__":
    main()
