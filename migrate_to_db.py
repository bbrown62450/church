#!/usr/bin/env python3
"""One-time migration: Notion + legacy JSON -> the multi-church app database.

Creates the founder user and their church (as owner), imports the enriched
Notion hymn database into `hymn_catalog`, and seeds the founder church's
`hymns` from that catalog. Safe to re-run to convergence (idempotent).

Usage:
    python migrate_to_db.py \
        --founder-email beau@example.com \
        --church-name "Conner Presbyterian" \
        --timezone America/New_York
"""

import argparse
import sys

from sqlalchemy import func, select

from db import init_db, session_scope
from db.models import Hymn, HymnCatalog
from repos.churches import create_church, list_user_churches
from repos.hymns import seed_church_from_catalog
from auth import upsert_from_claims
from hymn_utils import get_property_value

# Notion hymn property names carried verbatim into `props` (flat Notion keys).
_CATALOG_PROPERTY_NAMES = (
    "Hymn Title",
    "Hymn Number",
    "Hymnary.org Link",
    "Scripture References",
    "Theme",
    "Text",
    "Tune",
    "Tune Name",
    "Composer",
    "Lyricist",
    "Meter",
    "Music Date",
    "Lyrics Date",
)


def _norm_title(title):
    return (title or "").strip().lower()


def parse_hymn_page(page):
    """Notion hymn page -> flat catalog row {'number', 'title', 'props'}. Pure."""
    props = {}
    for name in _CATALOG_PROPERTY_NAMES:
        value = get_property_value(page, name)
        if value is not None and value != "":
            props[name] = value
    title = (props.get("Hymn Title") or "").strip()
    number = props.get("Hymn Number")
    if number is not None and not isinstance(number, int):
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = None
    return {"number": number, "title": title, "props": props}


def upsert_catalog_hymn(session, parsed):
    """Insert/update one hymn_catalog row keyed by (number, normalized title).

    Returns True if a new row was inserted, False if an existing row was
    updated. Idempotent -> safe to re-run to convergence. Duplicate-title
    settings with different numbers (e.g. multiple "Gloria") are not collapsed.
    """
    number = parsed.get("number")
    norm = _norm_title(parsed.get("title"))
    props = parsed.get("props") or {}
    stmt = select(HymnCatalog)
    if number is None:
        stmt = stmt.where(HymnCatalog.number.is_(None))
    else:
        stmt = stmt.where(HymnCatalog.number == number)
    match = next(
        (row for row in session.execute(stmt).scalars() if _norm_title(row.title) == norm),
        None,
    )
    if match is None:
        session.add(
            HymnCatalog(
                title=parsed.get("title") or "",
                number=number,
                scripture_refs=props.get("Scripture References"),
                theme=props.get("Theme"),
                hymnary_link=props.get("Hymnary.org Link"),
                audio_url=props.get("audio_url"),
            )
        )
        return True
    match.title = parsed.get("title") or ""
    match.scripture_refs = props.get("Scripture References")
    match.theme = props.get("Theme")
    match.hymnary_link = props.get("Hymnary.org Link")
    match.audio_url = props.get("audio_url")
    return False


def import_hymn_catalog(session, pages):
    """Load Notion hymn pages into hymn_catalog. Returns a count report."""
    inserted = updated = 0
    for page in pages:
        parsed = parse_hymn_page(page)
        if not parsed["title"]:
            continue
        if upsert_catalog_hymn(session, parsed):
            inserted += 1
        else:
            updated += 1
    return {"inserted": inserted, "updated": updated, "total": inserted + updated}


def ensure_founder_user(email, name):
    """Create/refresh the founder's users row (keyed on normalized email)."""
    claims = {
        "email": email,
        "name": name,
        "sub": None,
        "picture": None,
        "email_verified": True,
    }
    return upsert_from_claims(claims)


def ensure_founder_church(user_id, name, tz):
    """Return the founder's owned church of this name, creating it if absent.

    create_church atomically seeds the church's hymns from hymn_catalog, so
    the catalog must be imported *before* this call.
    """
    for church in list_user_churches(user_id):
        if church["name"] == name and church["role"] == "owner":
            return church["id"]
    return create_church(name=name, timezone=tz, owner_user_id=user_id)


def _ensure_church_seeded(session, church_id):
    """Seed the church from catalog only if it has no hymns yet (convergence
    after a partial run that created the church before the catalog existed)."""
    count = session.execute(
        select(func.count()).select_from(Hymn).where(Hymn.church_id == church_id)
    ).scalar_one()
    if count == 0:
        return seed_church_from_catalog(church_id, session)
    return count


def fetch_notion_hymns():
    """Read the enriched hymn database from Notion (real I/O; not unit-tested)."""
    from notion_hymns import NotionHymnsDB

    return NotionHymnsDB().list_hymns()


def run_migration(*, founder_email, church_name, timezone, hymn_pages=None):
    """Founder user + church + hymn catalog. Returns a report dict."""
    user_id = ensure_founder_user(founder_email, founder_email.split("@")[0])
    if hymn_pages is None:
        hymn_pages = fetch_notion_hymns()
    with session_scope() as session:
        catalog_report = import_hymn_catalog(session, hymn_pages)
    church_id = ensure_founder_church(user_id, church_name, timezone)
    with session_scope() as session:
        seeded = _ensure_church_seeded(session, church_id)
    return {
        "founder_user_id": str(user_id),
        "church_id": str(church_id),
        "catalog": catalog_report,
        "hymns_seeded": seeded,
    }


def _print_report(report):
    print("=== Migration report ===")
    for key, value in report.items():
        print(f"{key}: {value}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="One-time migration: Notion -> app database (founder church)."
    )
    parser.add_argument("--founder-email", required=True)
    parser.add_argument("--church-name", required=True)
    parser.add_argument("--timezone", default="America/New_York")
    args = parser.parse_args(argv)
    init_db()
    report = run_migration(
        founder_email=args.founder_email.strip().lower(),
        church_name=args.church_name,
        timezone=args.timezone,
    )
    _print_report(report)


if __name__ == "__main__":
    main()
