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
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

import service_output
from db import session_scope
from usecases import archive

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
