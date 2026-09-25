#!/usr/bin/env python3
"""Fetch full Bible passage text by reference.

Two sources:
  * bible-api.com — no key, several public-domain translations (default: WEB).
  * api.esv.org   — the ESV, when ESV_API_KEY is configured (register free at
                    https://api.esv.org). ESV text is © Crossway; the short
                    "(ESV)" copyright is kept on the returned text.
"""

import logging
import os
import re
from typing import Optional, Dict, Any, List, Tuple
import httpx

logger = logging.getLogger(__name__)

# bible-api.com: GET https://bible-api.com/{passage}?translation=web
BIBLE_API_BASE = "https://bible-api.com"
ESV_API_BASE = "https://api.esv.org/v3/passage/text/"

DEFAULT_TRANSLATION = "web"

# translation id -> (human label, source). Order here is the display order.
TRANSLATIONS: Dict[str, Tuple[str, str]] = {
    "web": ("World English Bible (WEB)", "bible-api"),
    "kjv": ("King James Version (KJV)", "bible-api"),
    "asv": ("American Standard Version (ASV)", "bible-api"),
    "ylt": ("Young's Literal Translation (YLT)", "bible-api"),
    "dra": ("Douay-Rheims 1899 (DRA)", "bible-api"),
    "darby": ("Darby Bible", "bible-api"),
    "bbe": ("Bible in Basic English (BBE)", "bible-api"),
    "oeb-us": ("Open English Bible, US (OEB)", "bible-api"),
    "webbe": ("World English Bible, British (WEBBE)", "bible-api"),
    "esv": ("English Standard Version (ESV)", "esv"),
}


def _esv_key() -> str:
    return os.getenv("ESV_API_KEY", "").strip()


def esv_configured() -> bool:
    return bool(_esv_key())


def available_translations() -> List[Tuple[str, str]]:
    """[(id, label), ...] usable on this deployment. ESV only when its key is set."""
    out = []
    for tid, (label, source) in TRANSLATIONS.items():
        if source == "esv" and not esv_configured():
            continue
        out.append((tid, label))
    return out


def translation_label(translation_id: Optional[str]) -> str:
    """Human label for a translation id (falls back gracefully)."""
    tid = (translation_id or DEFAULT_TRANSLATION)
    entry = TRANSLATIONS.get(tid)
    return entry[0] if entry else tid


def _reference_to_api_param(reference: str) -> str:
    """Convert a reference like '2 Kings 2:1-12' to URL path format."""
    s = reference.strip()
    # Already fine for URL: just lowercase and encode
    return s.lower().replace(" ", "%20")


def _fetch_bible_api(ref: str, translation: str) -> Optional[str]:
    ref_param = _reference_to_api_param(ref)
    url = f"{BIBLE_API_BASE}/{ref_param}"
    params = {"translation": translation}
    try:
        logger.debug("Fetching %s from bible-api (%s)", ref, translation)
        r = httpx.get(url, params=params, timeout=15.0)
        r.raise_for_status()
        data = r.json()
        return (data.get("text") or "").strip() or None
    except Exception as e:
        logger.warning("Failed to fetch %s from bible-api: %s", ref, e)
        return None


def _fetch_esv(ref: str) -> Optional[str]:
    key = _esv_key()
    if not key:
        return None
    params = {
        "q": ref,
        "include-headings": "false",
        "include-footnotes": "false",
        "include-verse-numbers": "false",
        "include-passage-references": "false",
        "include-short-copyright": "true",   # keeps the required "(ESV)" credit
    }
    try:
        logger.debug("Fetching %s from ESV API", ref)
        r = httpx.get(
            ESV_API_BASE,
            params=params,
            headers={"Authorization": f"Token {key}"},
            timeout=15.0,
        )
        r.raise_for_status()
        passages = r.json().get("passages") or []
        text = "\n\n".join(p.strip() for p in passages if p and p.strip())
        return text or None
    except Exception as e:
        logger.warning("Failed to fetch %s from ESV: %s", ref, e)
        return None


def _fetch_one_passage(ref: str, translation: str) -> Optional[str]:
    """Fetch text for a single passage (no semicolons), routed by translation."""
    source = (TRANSLATIONS.get(translation) or (None, "bible-api"))[1]
    if source == "esv":
        return _fetch_esv(ref)
    return _fetch_bible_api(ref, translation)


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


def fetch_passage(reference: str, translation: str = DEFAULT_TRANSLATION) -> Optional[Dict[str, Any]]:
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


def get_passage_text(reference: str, translation: str = DEFAULT_TRANSLATION) -> Optional[str]:
    """Return just the combined passage text, or None."""
    data = fetch_passage(reference, translation=translation)
    if not data:
        return None
    return (data.get("text") or "").strip() or None
