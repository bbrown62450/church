#!/usr/bin/env python3
"""
Fetch full Bible passage text by reference using bible-api.com (no API key).
"""

import logging
import re
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# bible-api.com: GET https://bible-api.com/{passage}?translation=web
BIBLE_API_BASE = "https://bible-api.com"


def _reference_to_api_param(reference: str) -> str:
    """Convert a reference like '2 Kings 2:1-12' to URL path format."""
    s = reference.strip()
    # Already fine for URL: just lowercase and encode
    return s.lower().replace(" ", "%20")


def _fetch_one_passage(ref: str, translation: str) -> Optional[str]:
    """Fetch text for a single passage (no semicolons). Returns None on failure."""
    ref_param = _reference_to_api_param(ref)
    url = f"{BIBLE_API_BASE}/{ref_param}"
    params = {"translation": translation}
    try:
        logger.debug("Fetching %s from bible-api", ref)
        r = httpx.get(url, params=params, timeout=15.0)
        r.raise_for_status()
        data = r.json()
        text = (data.get("text") or "").strip() or None
        logger.debug("Fetched %s: %s chars", ref, len(text) if text else 0)
        return text
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", ref, e)
        return None


def _book_name_from_ref(ref: str) -> Optional[str]:
    """Extract book name from a reference like 'Genesis 2:15-17' or '2 Kings 2:1-12'.
    Returns e.g. 'Genesis', '2 Kings'. Returns None if no chapter:verse pattern."""
    # Match optional leading digits (for 1 John, 2 Kings), then name, then space and chapter:verse
    m = re.match(r"^(.+?)\s+\d+:\d+", ref.strip())
    if not m:
        return None
    return m.group(1).strip()


def _expand_part(part: str, last_book: Optional[str]) -> str:
    """If part is just '3:1-7' (chapter:verse), prepend last_book to get 'Genesis 3:1-7'."""
    part = part.strip()
    # Looks like "3:1-7" or "3:1" (starts with digit and has colon)
    if re.match(r"^\d+:\d+", part) and last_book:
        return f"{last_book} {part}"
    return part


def fetch_passage(reference: str, translation: str = "web") -> Optional[Dict[str, Any]]:
    """
    Fetch passage text for a reference (e.g. '2 Kings 2:1-12', 'Genesis 2:15-17; 3:1-7',
    'John 3:1-17 or Matthew 17:1-9').
    Lectionary refs often use semicolons; later parts may omit the book name (e.g. '3:1-7').
    Gospel readings sometimes offer alternatives joined by " or "; we fetch each and combine.
    We carry the book name from the first part when a part looks like just chapter:verse.
    Returns dict with keys: reference, text (combined), or None on total failure.
    """
    ref = reference.strip()
    if not ref:
        return None
    # Handle " or " (alternative gospel choices) - split and process each separately
    if " or " in ref:
        alternatives = [p.strip() for p in ref.split(" or ") if p.strip()]
        logger.info("Fetching %d alternatives for '%s'", len(alternatives), ref)
        texts = []
        for alt in alternatives:
            result = fetch_passage(alt, translation=translation)
            if result and result.get("text"):
                texts.append(f"--- {alt} ---\n\n{result['text']}")
        logger.info("Alternatives fetched: %d/%d ok", len(texts), len(alternatives))
        if not texts:
            return None
        return {"reference": ref, "text": "\n\n".join(texts)}
    raw_parts = [p.strip() for p in ref.split(";") if p.strip()]
    if not raw_parts:
        return None
    last_book = None
    texts = []
    for part in raw_parts:
        full_ref = _expand_part(part, last_book)
        if not last_book:
            last_book = _book_name_from_ref(full_ref)
        t = _fetch_one_passage(full_ref, translation)
        if t:
            texts.append(t)
    if not texts:
        return None
    return {"reference": ref, "text": "\n\n".join(texts)}


def get_passage_text(reference: str, translation: str = "web") -> Optional[str]:
    """Return just the combined passage text, or None."""
    data = fetch_passage(reference, translation=translation)
    if not data:
        return None
    return (data.get("text") or "").strip() or None
