#!/usr/bin/env python3
"""
Fix hymn titles in Notion database by scraping the actual title from hymnary.org.
Some hymns have the "first line" instead of the real title (e.g. "Thou art the King
of Israel" instead of "All Glory, Laud, and Honor").
"""

import os
import re
import time
import argparse
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from notion_hymns import NotionHymnsDB
from hymn_utils import get_property_value
import httpx
from bs4 import BeautifulSoup

load_dotenv()


def scrape_hymn_title(hymnary_url: str) -> Optional[str]:
    """Scrape the real hymn title from a hymnary.org page.
    Looks for the 'Title:' metadata field (hy_infoLabel), which has the
    canonical title rather than the first-line identifier some hymnals use.
    """
    try:
        r = httpx.get(
            hymnary_url,
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HymnTitleFixer/1.0)"},
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Look for "Title" label in metadata spans
        for label_span in soup.find_all("span", class_="hy_infoLabel"):
            label = label_span.get_text(strip=True).lower()
            if label == "title":
                parent_td = label_span.find_parent("td")
                if not parent_td:
                    continue
                value_td = parent_td.find_next_sibling("td")
                if value_td:
                    # Title may be in a link
                    link = value_td.find("a")
                    if link:
                        return link.get_text(strip=True)
                    return value_td.get_text(strip=True)

        # Fallback: look for the heading pattern "196. Title Here"
        for heading in soup.find_all(["h1", "h2", "h3"]):
            text = heading.get_text(strip=True)
            m = re.match(r"^\d+\.\s+(.+)$", text)
            if m:
                return m.group(1)

    except Exception as e:
        print(f"  Warning: Could not scrape {hymnary_url}: {e}")
    return None


def fix_titles(dry_run: bool = True, limit: Optional[int] = None, hymn_numbers: list = None):
    """Check and fix hymn titles by comparing with hymnary.org."""
    db = NotionHymnsDB()

    print(f"\n{'=' * 60}")
    print(f"Fixing hymn titles from hymnary.org")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"{'=' * 60}\n")

    print("Loading hymns from Notion...")
    hymns = db.list_hymns()
    if limit:
        hymns = hymns[:limit]
    total = len(hymns)
    print(f"Loaded {total} hymns.\n")

    mismatches = []
    processed = 0
    skipped = 0
    errors = 0
    matched = 0

    for hymn in hymns:
        number = get_property_value(hymn, "Hymn Number")
        current_title = get_property_value(hymn, "Hymn Title") or ""
        hymnary_url = get_property_value(hymn, "Hymnary.org Link")

        # Filter to specific hymn numbers if provided
        if hymn_numbers and number not in hymn_numbers:
            continue

        if not hymnary_url:
            skipped += 1
            continue

        processed += 1
        print(f"  [{processed}/{total}] #{number}: checking...", end="", flush=True)

        real_title = scrape_hymn_title(hymnary_url)
        if not real_title:
            errors += 1
            print(" ERROR (could not scrape)")
            continue

        # Compare (case-insensitive, strip whitespace)
        if real_title.strip().lower() != current_title.strip().lower():
            mismatches.append({
                "page_id": hymn["id"],
                "number": number,
                "current": current_title,
                "correct": real_title,
                "url": hymnary_url,
            })
            print(f" MISMATCH")
            print(f"         was: \"{current_title}\"")
            print(f"         fix: \"{real_title}\"")
        else:
            matched += 1
            print(f" OK")

        # Rate limit
        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"Checked: {processed} | Matched: {matched} | Mismatched: {len(mismatches)} | Errors: {errors} | Skipped (no URL): {skipped}")
    print(f"{'=' * 60}\n")

    if not mismatches:
        print("All titles match!")
        return

    if dry_run:
        print("DRY RUN — no changes made. Run with --execute to apply fixes.")
        return

    # Apply fixes
    print(f"Updating {len(mismatches)} titles in Notion...\n")
    updated = 0
    update_errors = 0
    for i, m in enumerate(mismatches, 1):
        try:
            db.client.pages.update(
                page_id=m["page_id"],
                properties={
                    "Hymn Title": {
                        "title": [{"text": {"content": m["correct"]}}]
                    }
                },
            )
            print(f"  [{i}/{len(mismatches)}] Updated #{m['number']}: \"{m['correct']}\"")
            updated += 1
            time.sleep(0.3)
        except Exception as e:
            update_errors += 1
            print(f"  [{i}/{len(mismatches)}] ERROR #{m['number']}: {e}")

    print(f"\n{'=' * 60}")
    print(f"Done! Updated: {updated} | Errors: {update_errors}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="Fix hymn titles using hymnary.org")
    parser.add_argument("--execute", action="store_true", help="Apply changes (default is dry-run)")
    parser.add_argument("--limit", type=int, help="Max hymns to check")
    parser.add_argument("--numbers", nargs="+", type=int, help="Only check specific hymn numbers (e.g. --numbers 196 491)")
    args = parser.parse_args()

    fix_titles(dry_run=not args.execute, limit=args.limit, hymn_numbers=args.numbers)


if __name__ == "__main__":
    main()
