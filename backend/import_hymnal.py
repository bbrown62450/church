#!/usr/bin/env python3
"""Import a hymnal CSV into a church's hymnal (idempotent, re-runnable).

An ops tool with no role check, run only by the owner against the production
DATABASE_URL (6a spec, `import_hymnal.py`). Admins add bundled hymnals in the
app (Settings → Hymns); this CLI stays for other CSVs.

CSV needs at least `number` and `title`; optional `scripture_refs`, `theme`.
A Hymnary.org link is constructed per hymn from --hymnal + number. --csv may
be left out for a bundled hymnal (backend/seed/hymnals/<CODE>.csv):

    python import_hymnal.py --church-id <uuid> --hymnal PH1990
    python import_hymnal.py --church-id <uuid> --hymnal XX2000 --csv path/to/XX2000.csv
"""
import argparse

import hymnal_sources


def load_rows(csv_path: str, hymnal: str) -> list:
    return hymnal_sources.load_rows(csv_path, hymnal)


def main(argv=None):
    from dotenv import load_dotenv

    load_dotenv()
    parser = argparse.ArgumentParser(description="Import a hymnal CSV into a church.")
    parser.add_argument("--church-id", required=True)
    parser.add_argument("--hymnal", required=True, help="e.g. PH1990")
    parser.add_argument("--csv", help="the CSV to import; optional for a bundled hymnal")
    args = parser.parse_args(argv)
    bundled = hymnal_sources.file_sources()
    if args.csv is None and args.hymnal not in bundled:
        parser.error(f"--csv is required: {args.hymnal} is not a bundled hymnal ({', '.join(sorted(bundled))})")

    from db import init_db
    from repos.hymns import import_hymns, list_church_hymnals

    init_db()
    rows = load_rows(args.csv, args.hymnal) if args.csv else [dict(r) for r in bundled[args.hymnal]]
    report = import_hymns(args.church_id, args.hymnal, rows)
    print(f"Imported {args.hymnal}: {report}")
    print(f"Church now has hymnals: {list_church_hymnals(args.church_id)}")


if __name__ == "__main__":
    main()
