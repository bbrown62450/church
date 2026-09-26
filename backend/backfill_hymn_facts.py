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
from typing import List, Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

from db import get_engine  # noqa: E402
from hymnary_facts import API_URL, RESULT_CAP, FetchError, is_truncated, run_backfill  # noqa: E402

DELAY_SECONDS = 1.0


def make_fetch(client: httpx.Client, delay: float = DELAY_SECONDS,
               truncated: Optional[List[str]] = None, failed: Optional[List[str]] = None):
    """A throttled fetch for run_backfill. Each reference whose response hit
    Hymnary's RESULT_CAP is printed and, when given, appended to `truncated`.

    A failed request (timeout, HTTP error, bad JSON) raises FetchError rather
    than returning [], which means "nothing cites this reference": hymns citing
    it then stay blank this run instead of matching on their other references
    alone. Each failure is printed and, when given, appended to `failed`."""
    def fetch(ref: str):
        time.sleep(delay)
        try:
            response = client.get(API_URL, params={"reference": ref})
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            print(f"  ! {ref}: {exc}")
            if failed is not None:
                failed.append(ref)
            raise FetchError(f"{ref}: {exc}") from exc
        if is_truncated(data):
            print(f"  ~ {ref}: hit Hymnary's {RESULT_CAP}-text cap; texts past it are not seen")
            if truncated is not None:
                truncated.append(ref)
        return data
    return fetch


def _progress(done: int, total: int) -> None:
    if done % 50 == 0 or done == total:
        print(f"  {done}/{total} hymns checked")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill hymn year and familiarity from Hymnary.org.")
    parser.add_argument("--dry-run", action="store_true", help="report matches without writing")
    args = parser.parse_args()
    get_engine()   # bind the session to DATABASE_URL (not init_db: no create_all on Supabase)
    truncated: List[str] = []
    failed: List[str] = []
    headers = {"User-Agent": "worship-service-builder hymn-facts backfill"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        stats = run_backfill(make_fetch(client, truncated=truncated, failed=failed),
                             dry_run=args.dry_run, on_progress=_progress)
    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}checked {stats['checked']}, matched {stats['matched']}, "
          f"updated {stats['updated']}, unknown {stats['unknown']}")
    if truncated:
        print(f"{len(truncated)} reference(s) hit Hymnary's {RESULT_CAP}-text cap, so hymns cited "
              f"only by them may be unknown: {'; '.join(truncated)}")
    if failed:
        refs = list(dict.fromkeys(failed))   # a failed reference is retried, so it can repeat
        print(f"{len(refs)} reference(s) failed, so hymns citing them were left blank; "
              f"re-run to retry them: {'; '.join(refs)}")


if __name__ == "__main__":
    main()
