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
# How Hymnary answers a reference it cannot read, such as "Isaiah 6:3 (st. 1)":
# HTTP 200, text/html, "Could not parse text reference 'Isaiah 6:3 (st. 1)'."
UNPARSEABLE = "Could not parse text reference"


def make_fetch(client: httpx.Client, delay: float = DELAY_SECONDS,
               truncated: Optional[List[str]] = None, failed: Optional[List[str]] = None,
               unparseable: Optional[List[str]] = None):
    """A throttled fetch for run_backfill. Each reference whose response hit
    Hymnary's RESULT_CAP is printed and, when given, appended to `truncated`.

    A failed request (timeout, HTTP error, a body that is not JSON) raises
    FetchError rather than returning [], which means "nothing cites this
    reference": hymns citing it then stay blank this run instead of matching on
    their other references alone. Each failure is printed and, when given,
    appended to `failed`.

    A reference Hymnary cannot parse is not a failure: the answer never
    changes, so a retry cannot help. It returns [] (hymns citing it match on
    their other references) and is printed and, when given, appended to
    `unparseable`, so the stored reference can be fixed by hand."""
    def failure(ref: str, reason: str) -> FetchError:
        print(f"  ! {ref}: {reason}")
        if failed is not None:
            failed.append(ref)
        return FetchError(f"{ref}: {reason}")

    def fetch(ref: str):
        time.sleep(delay)
        try:
            response = client.get(API_URL, params={"reference": ref})
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise failure(ref, str(exc)) from exc
        body = response.text.strip()
        if body.startswith(UNPARSEABLE):
            print(f"  ? {ref}: {body}")
            if unparseable is not None:
                unparseable.append(ref)
            return []
        try:
            data = response.json()
        except ValueError as exc:
            raise failure(ref, f"response is not JSON: {body[:80]!r}") from exc
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
    unparseable: List[str] = []
    headers = {"User-Agent": "worship-service-builder hymn-facts backfill"}
    with httpx.Client(timeout=30.0, headers=headers) as client:
        fetch = make_fetch(client, truncated=truncated, failed=failed, unparseable=unparseable)
        stats = run_backfill(fetch, dry_run=args.dry_run, on_progress=_progress)
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
    if unparseable:
        print(f"{len(unparseable)} reference(s) Hymnary could not parse were skipped, so hymns "
              f"cited only by them are unknown; fix the stored reference: {'; '.join(unparseable)}")


if __name__ == "__main__":
    main()
