"""The Word files, built on demand from the posted service (slice 5a spec,
Backend "usecases/documents.py"; owner decision 4: never stored, never cached).

build_document(church_id, data, variant) is the only way to build a file
(POST /documents now; 5b's bulletin email later): clean the input, resolve
the hymns in a short read that closes before rendering, render, and name the
file after the posted date. It writes nothing: hymn use is recorded when a
service is saved (5a-2), never on a download. It logs the variant, the church
id, the size and the duration, never the content (F §2.5). clean_input's
InvalidInput and resolve_hymn_refs' NotFound propagate; a missing python-docx
is a RuntimeError, which the API turns into a logged 500.

build_printed (the printed bulletin, PR 1) does the same for the printed
bulletin, as a PDF or a Word file, and adds what the booklet prints beyond the
Word copies: the church's name (read with the hymns) and the two readings'
text, fetched in the translation step 1 shows (the draft's when this
deployment offers it, else the church's: readings.ts effectiveTranslation).
The fetch charges `charge(parts)` first (the route's `scripture` bucket, one
token per upstream part, as POST /scripture/passages); a reading whose text
does not come back prints "[Reading text unavailable]", never an error.
PR 2a adds the church's bulletin settings (church_bulletin.read_settings of
the settings read with the name, every text Word-safe): the contact lines,
the people, the service time, the stars, the stand note and the Gloria Patri
words. PR 2b adds the week's own fields as posted (the draft's bulletin):
the music, this week's people and part leaders, the announcements, and a
pasted reading text, which prints instead of the fetched one and is neither
fetched nor charged; a body with no bulletin (a page from before PR 2b-2)
prints PR 1's placeholders. The log line never carries a bulletin's text.
PR 3a adds the week's cover picture: the church's picture the bulletin
points at, read with the name (none when it is not the church's or no
longer there: the reading and the date print alone).
"""
from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Optional

import printed_bulletin
import printed_docx
import printed_pdf
import scripture_fetcher
import service_output
from db import session_scope
from service_bulletin import ServiceBulletin
from domain_errors import Forbidden
from repos import bulletin_images as images_repo
from repos import churches
from usecases import archive, church_bulletin, passages

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DocumentResult:
    content: bytes
    filename: str


def build_document(church_id: uuid.UUID, data: archive.ServiceInput,
                   variant: service_output.Variant) -> DocumentResult:
    started = time.monotonic()
    clean = archive.clean_input(data)
    with session_scope() as s:                                  # read, then close before rendering
        hymns = archive.resolve_hymn_refs(s, church_id, clean.hymns)
    resolved = service_output.ResolvedService(
        service_date=clean.service_date, occasion=clean.occasion, scriptures=clean.scriptures, hymns=hymns,
        liturgy=clean.liturgy, sermon_title=clean.sermon_title, selected_ot_ref=clean.selected_ot_ref,
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements)
    content = service_output.render_docx(resolved, variant)
    logger.info("documents.build church=%s variant=%s bytes=%d ms=%d", church_id, variant, len(content),
                round((time.monotonic() - started) * 1000))
    return DocumentResult(content, service_output.docx_filename(variant, clean.service_date))


# --- the printed bulletin (printed bulletin spec, PR 1) ---

NO_ACCESS_MESSAGE = "You don't have access to this church."      # usecases.church_profile's


def effective_translation(requested: Optional[str], settings: object) -> str:
    """The translation the readings print in: `requested` (the draft's) when
    this deployment offers it, else the church's stored default when offered,
    else "web" (GET /church's effective_translation)."""
    offered = {tid for tid, _label in scripture_fetcher.available_translations()}
    if requested in offered:
        return requested
    stored = settings.get("bible_translation") if isinstance(settings, Mapping) else None
    return stored if stored in offered else scripture_fetcher.DEFAULT_TRANSLATION


def _first_text(passage: scripture_fetcher.Passage) -> Optional[str]:
    """The first alternative that came back ("Psalm 23 or Psalm 100" prints Psalm 23)."""
    text = next((s.text for s in passage.sections if s.status == "ok" and s.text), None)
    return None if text is None else archive._xml_safe(text)


def reading_texts(refs: list[str], translation: str,
                  charge: Callable[[int], None]) -> dict[str, Optional[str]]:
    """Each reading's text, or None. A reading with no parts, or readings with
    more parts than one passages request allows, are not fetched. `charge` is
    called once, with the number of upstream parts, before any fetch."""
    texts: dict[str, Optional[str]] = {ref: None for ref in refs}
    fetchable = [ref for ref in refs if scripture_fetcher.plan_sections(ref)]
    parts = sum(len(section) for ref in fetchable for _alternative, section in scripture_fetcher.plan_sections(ref))
    if not fetchable or parts > passages.MAX_PARTS:
        return texts
    plan = passages.plan_passages(fetchable, translation)
    charge(len(plan.parts))
    for ref, passage in zip(fetchable, passages.load_passages(plan).passages, strict=True):
        texts[ref] = _first_text(passage)
    return texts


def build_printed(church_id: uuid.UUID, data: archive.ServiceInput, fmt: printed_bulletin.Format,
                  translation: Optional[str], *, charge: Callable[[int], None]) -> DocumentResult:
    started = time.monotonic()
    clean = archive.clean_input(data)
    with session_scope() as s:                                  # read, then close before fetching
        church = churches.get_church(church_id, session=s)
        if church is None:
            raise Forbidden(NO_ACCESS_MESSAGE, details={"reason": "no_church_access"})
        hymns = archive.resolve_hymn_refs(s, church_id, clean.hymns)
        cover_id = clean.bulletin.cover_image_id if clean.bulletin is not None else None
        stored = images_repo.get_picture(church_id, cover_id, session=s) if cover_id else None
    resolved = service_output.ResolvedService(
        service_date=clean.service_date, occasion=clean.occasion, scriptures=clean.scriptures, hymns=hymns,
        liturgy=clean.liturgy, sermon_title=clean.sermon_title, selected_ot_ref=clean.selected_ot_ref,
        selected_nt_ref=clean.selected_nt_ref, include_communion=clean.include_communion,
        custom_elements=clean.custom_elements)
    ot, nt = service_output.resolve_doc_readings(list(clean.scriptures), clean.selected_ot_ref,
                                                 clean.selected_nt_ref)
    tid = effective_translation(translation, church["settings"])
    week = ServiceBulletin() if clean.bulletin is None else clean.bulletin
    pasted = ((ot, week.ot_text), (nt, week.nt_text))
    refs = [ref for ref, text in pasted if ref and not text]           # a pasted reading is not fetched
    texts = reading_texts(refs, tid, charge) if refs else {}

    def reading(ref: Optional[str], text: str) -> Optional[printed_bulletin.Reading]:
        if ref is None:
            return None
        return printed_bulletin.Reading(ref, text, pasted=True) if text else printed_bulletin.Reading(
            ref, texts.get(ref))

    printed = printed_bulletin.PrintedService(
        church_name=archive._xml_safe(church["name"] or "").strip(), resolved=resolved,
        ot=reading(*pasted[0]), nt=reading(*pasted[1]),
        translation_label=scripture_fetcher.translation_label(tid),
        settings=church_bulletin.read_settings(church["settings"]),
        bulletin=clean.bulletin,                        # None (a page from before PR 2b-2): PR 1's placeholders
        cover_picture=None if stored is None else stored.content)
    content = printed_pdf.render_pdf(printed) if fmt == "pdf" else printed_docx.render_docx(printed)
    logger.info("documents.printed church=%s format=%s bytes=%d ms=%d", church_id, fmt, len(content),
                round((time.monotonic() - started) * 1000))
    return DocumentResult(content, printed_bulletin.printed_filename(fmt, clean.service_date))
