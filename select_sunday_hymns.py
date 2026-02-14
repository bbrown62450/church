#!/usr/bin/env python3
"""
Select hymns for a given Sunday from the Notion hymns database.
Suggests well-known hymns for opening/gathering, sermon response, and sending.
"""

import os
import sys
from typing import Dict, Any, List, Optional
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
    elif prop_type == "date":
        date_obj = prop_data.get("date")
        return date_obj.get("start") if date_obj else None

    return None


def find_hymn_by_title(hymns: List[Dict[str, Any]], candidates: List[str]) -> Optional[Dict[str, Any]]:
    """Return the first hymn whose title matches one of the candidate strings (case-insensitive).
    Prefers the first candidate in the list that has a match."""
    candidates_ordered = [c.strip().lower() for c in candidates if c and c.strip()]
    title_to_hymn = {}
    for hymn in hymns:
        title = get_property_value(hymn, "Hymn Title")
        if title:
            title_to_hymn[title.strip().lower()] = hymn
    for c in candidates_ordered:
        if c in title_to_hymn:
            return title_to_hymn[c]
    return None


def select_transfiguration_sunday_2026() -> None:
    """
    Select three hymns for Transfiguration Sunday, Feb 15, 2026:
    - Opening: welcome/gathering
    - After sermon: reinforces Transfiguration / "see Jesus clearly" / "listen to him"
    - Closing: upbeat, sending out to serve and share God's love
    """
    db = NotionHymnsDB()
    hymns = db.list_hymns()

    # Build a simple title list for fallback display
    all_titles = []
    for h in hymns:
        t = get_property_value(h, "Hymn Title")
        if t:
            all_titles.append(t.strip())

    # Traditional hymns (pre-1980): titles as in your Notion DB / GG2013
    # (Omitting "Come, Thou Almighty King", "Holy, Holy, Holy!" — used elsewhere;
    #  "Let Us Break Bread Together" — communion Sundays only)
    opening_candidates = [
        "O day of rest and gladness",
        "Praise ye the Lord, the Almighty, the King of creation",
        "We gather here in Jesus' name",
    ]

    transfiguration_candidates = [
        "Swiftly pass the clouds of glory",  # 1969, James Quinn
        "O Wondrous Sight! O Vision Fair",
        "How good, Lord, to be here",
        "Christ upon the mountain peak",
    ]

    sending_candidates = [
        "Lead on, O King eternal!",
        "Now thank we all our God",
        "Praise God, from whom all blessings flow",
        "God be with you till we meet again",
        "Lord, dismiss us with thy blessing",
    ]

    opening = find_hymn_by_title(hymns, opening_candidates)
    transfiguration = find_hymn_by_title(hymns, transfiguration_candidates)
    sending = find_hymn_by_title(hymns, sending_candidates)

    # Print service info and selections
    print()
    print("=" * 70)
    print("  February 15, 2026 – Transfiguration Sunday")
    print("  Movement: Awakening Attention")
    print("  “This is my Son… listen to him.”")
    print("  Selections: traditional hymns (pre-1980)")
    print("=" * 70)
    print()

    def print_hymn(slot: str, hymn: Optional[Dict[str, Any]], candidates: List[str]) -> None:
        print(f"  {slot}")
        if hymn:
            title = get_property_value(hymn, "Hymn Title")
            number = get_property_value(hymn, "Hymn Number")
            link = get_property_value(hymn, "Hymnary.org Link")
            print(f"    → {title}")
            if number is not None:
                print(f"      Hymn # {number}")
            if link:
                print(f"      {link}")
            print(f"      Notion ID: {hymn['id']}")
        else:
            print(f"    (None of these found in your database: {', '.join(candidates[:3])} …)")
            print(f"    Consider adding one of: {', '.join(candidates[:4])}")
        print()

    print("  1. OPENING (welcome / gathering)")
    print_hymn("     Selected:", opening, opening_candidates)

    print("  2. AFTER SERMON (reinforce Transfiguration / see Jesus clearly / listen)")
    print_hymn("     Selected:", transfiguration, transfiguration_candidates)

    print("  3. CLOSING (upbeat / sending out to serve and share God's love)")
    print_hymn("     Selected:", sending, sending_candidates)

    print("=" * 70)
    print(f"  Total hymns in database: {len(hymns)}")
    print("=" * 70)
    print()


def main():
    """CLI: run Transfiguration Sunday selection (or extend for other Sundays)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Select hymns for Transfiguration Sunday from your Notion hymns database"
    )
    parser.add_argument(
        "--list-all",
        action="store_true",
        help="List all hymn titles in the database (for reference)",
    )
    args = parser.parse_args()

    try:
        db = NotionHymnsDB()
    except ValueError as e:
        print(f"Error: {e}")
        print("\nSet NOTION_API_KEY and NOTION_DATABASE_ID (e.g. in .env).")
        sys.exit(1)

    if args.list_all:
        hymns = db.list_hymns()
        print(f"\nHymns in database ({len(hymns)}):\n")
        for h in hymns:
            title = get_property_value(h, "Hymn Title")
            number = get_property_value(h, "Hymn Number")
            if title:
                print(f"  {number or '—'}  {title}")
        print()
        return

    select_transfiguration_sunday_2026()


if __name__ == "__main__":
    main()
