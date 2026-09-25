#!/usr/bin/env python3
"""Fill in each hymn's year and familiarity from Hymnary.org's public API.

Fills blanks only (never overwrites), so it is safe to re-run and manual
corrections survive. Run AFTER migrate_add_hymn_facts.py. Requests are spaced
DELAY_SECONDS apart to be polite to Hymnary.org.

    python backfill_hymn_facts.py --dry-run
    python backfill_hymn_facts.py
"""
import argparse
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

from hymnary_facts import API_URL, run_backfill  # noqa: E402

DELAY_SECONDS = 1.0


def make_fetch(client: httpx.Client, delay: float = DELAY_SECONDS):
    def fetch(ref: str):
        time.sleep(delay)
        try:
            response = client.get(API_URL, params={"reference": ref})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"  ! {ref}: {exc}")
            return []
    return fetch


def _progress(done: int, total: int) -> None:
    if done % 50 == 0 or done == total:
        print(f"  {done}/{total} hymns checked")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill hymn year and familiarity from Hymnary.org.")
    parser.add_argument("--dry-run", action="store_true", help="report matches without writing")
    args = parser.parse_args()
    headers = {"User-Agent": "worship-service-builder hymn-facts backfill"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        stats = run_backfill(make_fetch(client), dry_run=args.dry_run, on_progress=_progress)
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}checked {stats['checked']}, matched {stats['matched']}, "
          f"updated {stats['updated']}, unknown {stats['unknown']}")


if __name__ == "__main__":
    main()
