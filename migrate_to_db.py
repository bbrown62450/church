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
import json
import sys
from datetime import datetime, timezone as dtz

from sqlalchemy import func, select

from db import init_db, session_scope
from db.models import Contact, Hymn, HymnCatalog, HymnUsage, Service
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


def _iso_to_display(iso):
    """YYYY-MM-DD -> 'February 15, 2026' (blank/invalid pass through)."""
    if not iso:
        return ""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%B %d, %Y")
    except ValueError:
        return iso


def _parse_dt(value):
    """Parse a Notion date/timestamp string to an aware UTC datetime.

    Falls back to 'now' only when the source value is missing/unparseable.
    """
    if not value:
        return datetime.now(dtz.utc)
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return datetime.now(dtz.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dtz.utc)
    return parsed


def detect_truncated_liturgy(raw):
    """True when a stored liturgy rich-text is *likely truncated*.

    Notion capped the field at 2000 chars, so fully-generated bulletins were
    already cut off before this project. A value at/near the cap that no
    longer parses as JSON is treated as truncated. Pure; no I/O.
    """
    if raw is None:
        return False
    text = raw.strip()
    if len(text) < 1990:
        return False
    try:
        json.loads(text)
        return False
    except (ValueError, TypeError):
        return True


def extract_meta(liturgy):
    """Pull (sermon_title, include_communion) out of liturgy meta keys. Pure.

    sermon_title and include_communion are not Notion columns; they were
    embedded as `_sermon_title` / `_include_communion` in the liturgy JSON.
    """
    if not isinstance(liturgy, dict):
        return "", False
    sermon_title = liturgy.get("_sermon_title") or ""
    include_communion = bool(liturgy.get("_include_communion", False))
    return str(sermon_title), include_communion


def parse_archive_page(page):
    """Notion archive page -> service dict (Service shape). Pure."""
    props = page.get("properties", {})

    def rich(name):
        prop = props.get(name, {})
        if prop.get("type") != "rich_text":
            return ""
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))

    def date(name):
        prop = props.get(name, {})
        if prop.get("type") != "date":
            return ""
        value = prop.get("date")
        return value.get("start", "") if value else ""

    liturgy_raw = rich("Liturgy")
    truncated = detect_truncated_liturgy(liturgy_raw)
    liturgy = {}
    if liturgy_raw and not truncated:
        try:
            liturgy = json.loads(liturgy_raw)
        except (ValueError, TypeError):
            liturgy = {}
    if not isinstance(liturgy, dict):
        liturgy = {}
    sermon_title, include_communion = extract_meta(liturgy)
    liturgy_clean = {k: v for k, v in liturgy.items() if not k.startswith("_")}

    hymns_raw = rich("Hymns")
    hymns = []
    if hymns_raw:
        try:
            hymns = json.loads(hymns_raw)
        except (ValueError, TypeError):
            hymns = []

    service_date_iso = date("Service date")
    scriptures = [s for s in rich("Scriptures").splitlines() if s.strip()]
    return {
        "service_date_iso": service_date_iso,
        "service_date_display": _iso_to_display(service_date_iso),
        "occasion": rich("Occasion"),
        "scriptures": scriptures,
        "hymns": hymns,
        "liturgy": liturgy_clean,
        "sermon_title": sermon_title,
        "selected_ot_ref": rich("Selected OT"),
        "selected_nt_ref": rich("Selected NT"),
        "include_communion": include_communion,
        "saved_at": date("Saved at"),
        "truncated": truncated,
    }


def import_services(session, church_id, created_by, pages):
    """Import archive pages under one church, preserving saved_at verbatim;
    dedupe by (church_id, saved_at, occasion). Flags truncated-liturgy rows."""
    imported = skipped = flagged = 0
    flagged_rows = []
    for page in pages:
        svc = parse_archive_page(page)
        if svc["truncated"]:
            flagged += 1
            flagged_rows.append(svc.get("saved_at") or svc.get("occasion") or "?")
        saved_at = _parse_dt(svc["saved_at"])
        exists = session.execute(
            select(Service.id).where(
                Service.church_id == church_id,
                Service.saved_at == saved_at,
                Service.occasion == svc["occasion"],
            )
        ).first()
        if exists:
            skipped += 1
            continue
        session.add(
            Service(
                church_id=church_id,
                created_by=created_by,
                service_date_iso=svc["service_date_iso"],
                service_date_display=svc["service_date_display"],
                occasion=svc["occasion"],
                scriptures=svc["scriptures"],
                hymns=svc["hymns"],
                liturgy=svc["liturgy"],
                sermon_title=svc["sermon_title"],
                selected_ot_ref=svc["selected_ot_ref"],
                selected_nt_ref=svc["selected_nt_ref"],
                include_communion=svc["include_communion"],
                saved_at=saved_at,
            )
        )
        session.flush()  # make the pending row visible to later dedup queries
        imported += 1
    return {
        "imported": imported,
        "skipped": skipped,
        "flagged": flagged,
        "flagged_rows": flagged_rows,
    }


def parse_usage_page(page):
    """Notion usage page -> {'date_iso','hymn_number','hymn_title'}. Pure."""
    props = page.get("properties", {})
    number = None
    num_prop = props.get("Hymn number", {})
    if num_prop.get("type") == "number":
        number = num_prop.get("number")
    if number is not None and not isinstance(number, int):
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = None
    title = ""
    title_prop = props.get("Hymn title", {})
    if title_prop.get("type") == "rich_text":
        title = "".join(t.get("plain_text", "") for t in title_prop.get("rich_text", []))
    date_iso = ""
    date_prop = props.get("Date", {})
    if date_prop.get("type") == "date":
        value = date_prop.get("date")
        date_iso = value.get("start", "") if value else ""
    return {"date_iso": date_iso, "hymn_number": number, "hymn_title": title}


def import_usage(session, church_id, pages):
    """Import hymn usage under one church; dedupe by
    (church_id, date_iso, hymn_number, hymn_title)."""
    imported = skipped = 0
    for page in pages:
        row = parse_usage_page(page)
        if not row["hymn_title"]:
            continue
        filters = [
            HymnUsage.church_id == church_id,
            HymnUsage.date_iso == row["date_iso"],
            HymnUsage.hymn_title == row["hymn_title"],
        ]
        if row["hymn_number"] is None:
            filters.append(HymnUsage.hymn_number.is_(None))
        else:
            filters.append(HymnUsage.hymn_number == row["hymn_number"])
        if session.execute(select(HymnUsage.id).where(*filters)).first():
            skipped += 1
            continue
        session.add(
            HymnUsage(
                church_id=church_id,
                date_iso=row["date_iso"],
                hymn_number=row["hymn_number"],
                hymn_title=row["hymn_title"],
            )
        )
        session.flush()  # make the pending row visible to later dedup queries
        imported += 1
    return {"imported": imported, "skipped": skipped}


def import_contacts(session, church_id, contacts):
    """Import saved contacts into the founder church only; dedupe by email."""
    imported = skipped = 0
    for contact in contacts:
        email = (contact.get("email") or "").strip().lower()
        if not email:
            continue
        exists = session.execute(
            select(Contact.id).where(
                Contact.church_id == church_id,
                func.lower(Contact.email) == email,
            )
        ).first()
        if exists:
            skipped += 1
            continue
        session.add(
            Contact(
                church_id=church_id,
                name=(contact.get("name") or "").strip(),
                email=email,
            )
        )
        session.flush()  # make the pending row visible to later dedup queries
        imported += 1
    return {"imported": imported, "skipped": skipped}


def validate_enrichment(session, church_id):
    """Sample-check that the founder church's hymns are enriched.

    Empty results (no hymns, none with scripture references, or a scripture
    lookup that returns nothing) are a migration *failure*, not user error:
    print a report to stderr and exit non-zero.
    """
    hymns = session.execute(
        select(Hymn).where(Hymn.church_id == church_id)
    ).scalars().all()

    def scripture_of(hymn):
        return (hymn.scripture_refs or "").strip()

    total = len(hymns)
    with_scripture = sum(1 for h in hymns if scripture_of(h))
    sample_ref = ""
    sample_matches = 0
    for hymn in hymns:
        ref = scripture_of(hymn)
        if ref:
            sample_ref = ref
            token = ref.split()[0].lower()
            sample_matches = sum(1 for h in hymns if token in scripture_of(h).lower())
            break
    report = {
        "total_hymns": total,
        "with_scripture": with_scripture,
        "sample_ref": sample_ref,
        "sample_matches": sample_matches,
    }
    if total == 0 or with_scripture == 0 or sample_matches == 0:
        print(f"MIGRATION VALIDATION FAILED: {report}", file=sys.stderr)
        sys.exit(2)
    return report


def _notion_query_all(database_id):
    """Page through a Notion database, returning raw page dicts (real I/O)."""
    import os

    import httpx

    api_key = os.getenv("NOTION_API_KEY")
    if not api_key or not database_id:
        return []
    client = httpx.Client(
        base_url="https://api.notion.com/v1",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    results = []
    cursor = None
    with client:
        while True:
            body = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            response = client.post(f"/databases/{database_id}/query", json=body)
            response.raise_for_status()
            data = response.json()
            results.extend(data.get("results", []))
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
    return results


def fetch_notion_archive_pages():
    import os

    return _notion_query_all(os.getenv("NOTION_ARCHIVE_DATABASE_ID") or "")


def fetch_notion_usage_pages():
    import os

    return _notion_query_all(os.getenv("NOTION_USAGE_DATABASE_ID") or "")


def fetch_legacy_contacts():
    """Read the founder's saved recipients from the legacy JSON (one-time).

    Returns [] when absent — DEFAULT_CONTACTS is removed from the app, so no
    other church can inherit those personal/office emails.
    """
    import os

    path = os.path.join(os.path.dirname(__file__), "data", "email_contacts.json")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (ValueError, OSError):
        return []
    contacts = data.get("contacts", [])
    return contacts if isinstance(contacts, list) else []


def run_migration(
    *,
    founder_email,
    church_name,
    timezone,
    hymn_pages=None,
    archive_pages=None,
    usage_pages=None,
    contacts=None,
):
    """Full founder migration: user, catalog, church seed, archive, usage,
    contacts, then enrichment validation. Returns a report dict. Re-runnable
    to convergence via the stable dedupe keys in each importer."""
    user_id = ensure_founder_user(founder_email, founder_email.split("@")[0])
    if hymn_pages is None:
        hymn_pages = fetch_notion_hymns()
    with session_scope() as session:
        catalog_report = import_hymn_catalog(session, hymn_pages)
    church_id = ensure_founder_church(user_id, church_name, timezone)
    with session_scope() as session:
        seeded = _ensure_church_seeded(session, church_id)
    if archive_pages is None:
        archive_pages = fetch_notion_archive_pages()
    if usage_pages is None:
        usage_pages = fetch_notion_usage_pages()
    if contacts is None:
        contacts = fetch_legacy_contacts()
    with session_scope() as session:
        services_report = import_services(session, church_id, user_id, archive_pages)
        usage_report = import_usage(session, church_id, usage_pages)
        contacts_report = import_contacts(session, church_id, contacts)
    with session_scope() as session:
        enrichment = validate_enrichment(session, church_id)
    return {
        "founder_user_id": str(user_id),
        "church_id": str(church_id),
        "catalog": catalog_report,
        "hymns_seeded": seeded,
        "services": services_report,
        "usage": usage_report,
        "contacts": contacts_report,
        "enrichment": enrichment,
    }


def _print_report(report):
    print("=== Migration report ===")
    for key, value in report.items():
        print(f"{key}: {value}")


def main(argv=None):
    # CLI-only: load .env so DATABASE_URL / NOTION_* are set (the Streamlit app
    # does the same in app.py). Kept out of module import so tests stay hermetic.
    from dotenv import load_dotenv

    load_dotenv()

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
