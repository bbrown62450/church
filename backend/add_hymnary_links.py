#!/usr/bin/env python3
"""
Script to add hymnary.org links to hymns that are missing them,
based on their hymn number and the pattern from existing URLs.
"""

import os
import sys
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from notion_hymns import NotionHymnsDB

load_dotenv()


def get_property_value(hymn: Dict[str, Any], prop_name: str) -> Any:
    """Get the value of a property from a hymn object."""
    props = hymn.get("properties", {})
    prop_data = props.get(prop_name, {})
    prop_type = prop_data.get("type")
    
    if prop_type == "title":
        return "".join([t.get("plain_text", "") for t in prop_data.get("title", [])])
    elif prop_type == "rich_text":
        text = "".join([t.get("plain_text", "") for t in prop_data.get("rich_text", [])])
        return text if text else None
    elif prop_type == "number":
        return prop_data.get("number")
    elif prop_type == "url":
        return prop_data.get("url")
    
    return None


def generate_hymnary_url(hymn_number: Optional[int]) -> Optional[str]:
    """
    Generate a hymnary.org URL based on the hymn number.
    Pattern: https://hymnary.org/hymn/GG2013/{hymn_number}
    """
    if hymn_number is None:
        return None
    return f"https://hymnary.org/hymn/GG2013/{hymn_number}"


def add_missing_links(dry_run: bool = True, limit: Optional[int] = None):
    """
    Add hymnary.org links to hymns that are missing them.
    
    Args:
        dry_run: If True, only show what would be updated (default: True)
        limit: Maximum number of hymns to process (None = all)
    """
    db = NotionHymnsDB()
    
    print(f"\n{'='*60}")
    print(f"Adding hymnary.org links to hymns missing them")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE UPDATE'}")
    print(f"{'='*60}\n")
    
    hymns = db.list_hymns()
    
    if limit:
        hymns = hymns[:limit]
    
    stats = {
        'processed': 0,
        'updated': 0,
        'skipped_no_number': 0,
        'skipped_has_link': 0,
        'errors': 0
    }
    
    print(f"Processing {len(hymns)} hymns...\n")
    
    for idx, hymn in enumerate(hymns, 1):
        stats['processed'] += 1
        
        # Progress indicator every 50 hymns
        if idx % 50 == 0:
            print(f"[Progress: {idx}/{len(hymns)} ({idx*100//len(hymns)}%)] Processed so far: {stats['processed']}, Updated: {stats['updated']}, Skipped: {stats['skipped_has_link'] + stats['skipped_no_number']}")
        
        page_id = hymn['id']
        title = get_property_value(hymn, "Hymn Title")
        hymn_number = get_property_value(hymn, "Hymn Number")
        existing_link = get_property_value(hymn, "Hymnary.org Link")
        
        # Skip if already has a link
        if existing_link:
            stats['skipped_has_link'] += 1
            if idx <= 10 or idx % 100 == 0:  # Show first 10 and every 100th
                print(f"[{idx}/{len(hymns)}] Skipping '{title}' - already has hymnary.org link")
            continue
        
        # Skip if no hymn number
        if hymn_number is None:
            stats['skipped_no_number'] += 1
            if idx <= 10 or idx % 100 == 0:  # Show first 10 and every 100th
                print(f"[{idx}/{len(hymns)}] Skipping '{title}' - no hymn number")
            continue
        
        # Generate the URL
        new_url = generate_hymnary_url(hymn_number)
        
        # Only print details for first 10 or when updating
        if idx <= 10:
            print(f"[{idx}/{len(hymns)}] Processing: {title}")
            print(f"  Hymn Number: {hymn_number}")
            print(f"  Generated URL: {new_url}")
        
        if dry_run:
            if idx <= 10:
                print(f"  [DRY RUN] Would add hymnary.org link")
            stats['updated'] += 1
        else:
            try:
                db.client.pages.update(
                    page_id=page_id,
                    properties={
                        "Hymnary.org Link": {
                            "url": new_url
                        }
                    }
                )
                if idx <= 10 or idx % 100 == 0:  # Show first 10 and every 100th update
                    print(f"[{idx}/{len(hymns)}] ✓ Added link to '{title}' (#{hymn_number})")
                stats['updated'] += 1
            except Exception as e:
                print(f"[{idx}/{len(hymns)}] ✗ Error updating '{title}': {e}")
                stats['errors'] += 1
        
        if idx <= 10:
            print()
    
    # Print summary
    print(f"{'='*60}")
    print("Summary:")
    print(f"  Processed: {stats['processed']}")
    print(f"  Updated: {stats['updated']}")
    print(f"  Skipped (has link): {stats['skipped_has_link']}")
    print(f"  Skipped (no number): {stats['skipped_no_number']}")
    print(f"  Errors: {stats['errors']}")
    print(f"{'='*60}")
    
    if dry_run:
        print("\nThis was a DRY RUN. No changes were made.")
        print("Run with --execute to apply changes.")


def main():
    """CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Add hymnary.org links to hymns missing them"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually update the database (default is dry-run)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Maximum number of hymns to process (for testing)'
    )
    
    args = parser.parse_args()
    
    add_missing_links(dry_run=not args.execute, limit=args.limit)


if __name__ == "__main__":
    main()

