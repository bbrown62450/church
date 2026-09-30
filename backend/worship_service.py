#!/usr/bin/env python3
"""
Worship service generator: the Word document export. The hymn helpers moved
to hymn_search, hymn_suggest and usecases.hymns in slice 3; liturgy generation
moved to liturgy_prompts and usecases.liturgy in slice 4.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

from liturgy_config import ASSURANCE_RESPONSE, COMMUNION_BLOCKS

logger = logging.getLogger(__name__)

# Optional import for docx
try:
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
except ImportError:
    Document = None


def _add_leader_people_paragraph(doc, text: str) -> None:
    """Add paragraph(s): each Leader: (normal), each People: (bold). Supports multiple Leader/People pairs."""
    if not text or not text.strip():
        return
    # Find all "Leader:" and "People:" in order (case-insensitive)
    pattern = re.compile(r"\b(Leader|People):\s*", re.IGNORECASE)
    pos = 0
    parts = []
    for m in pattern.finditer(text):
        if m.start() > pos:
            parts.append(("", text[pos : m.start()].strip()))  # preamble if any
        role = "Leader" if m.group(1).lower() == "leader" else "People"
        end = pattern.search(text, m.end())
        content_end = end.start() if end else len(text)
        content = text[m.end() : content_end].strip()
        parts.append((role, content))
        pos = content_end
    if not parts:
        doc.add_paragraph(text)
        return
    for role, content in parts:
        if not content and role == "":
            continue
        if role == "People":
            p = doc.add_paragraph()
            p.add_run("People: ")
            r = p.add_run(content)
            r.bold = True
        else:
            line = ("Leader: " + content) if role == "Leader" else content
            if line:
                doc.add_paragraph(line)


def _add_communion_liturgy(doc) -> None:
    """Add The Sacrament of the Lord's Supper liturgy: liturgy_config.COMMUNION_BLOCKS
    (the one copy of the text, which GET /liturgy/config also serves), one paragraph each."""
    for block in COMMUNION_BLOCKS:
        if block.style == "heading1":
            doc.add_paragraph(block.text, style="Heading 1")
        elif block.style == "heading2":
            doc.add_paragraph(block.text, style="Heading 2")
        elif block.style == "response":
            doc.add_paragraph().add_run(block.text).bold = True
        elif block.style == "text":
            doc.add_paragraph(block.text)
        else:                               # blank
            doc.add_paragraph()


def _add_assurance_paragraph(doc, leader_text: str) -> None:
    """Add Assurance: Leader line then liturgy_config.ASSURANCE_RESPONSE in bold
    (the one copy the 4b card shows too)."""
    leader_clean = (leader_text or "").strip()
    if leader_clean.startswith("Leader:"):
        leader_clean = leader_clean[7:].strip()
    if leader_clean:
        doc.add_paragraph("Leader: " + leader_clean)
    # Always add the congregational response
    p = doc.add_paragraph()
    r = p.add_run(ASSURANCE_RESPONSE)
    r.bold = True


def _add_custom_elements_after(
    doc,
    anchor: str,
    custom_elements: List[Dict[str, Any]],
) -> None:
    """Add any custom elements that are inserted after this anchor."""
    for ce in custom_elements:
        if ce.get("insert_after") == anchor and ce.get("label"):
            doc.add_paragraph(ce["label"], style="Heading 2")
            if ce.get("text"):
                doc.add_paragraph(ce["text"])
            doc.add_paragraph()


def build_docx(
    *,
    occasion: str,
    date: str,
    scriptures: List[str],
    hymns: List[Dict[str, str]],
    liturgy: Dict[str, str],
    include_placeholders: bool = True,
    sermon_title: Optional[str] = None,
    selected_ot_ref: Optional[str] = None,
    selected_nt_ref: Optional[str] = None,
    scripture_full_texts: Optional[Dict[str, str]] = None,
    include_sermon: bool = True,
    include_prayers_of_the_people: bool = True,
    include_communion: bool = False,
    custom_elements: Optional[List[Dict[str, Any]]] = None,
) -> BytesIO:
    """
    Build a Word document with the worship service order and generated liturgy.
    include_sermon: include Sermon Title section (for pastor copy; omit for secretary).
    include_prayers_of_the_people: include Prayers of the People (for pastor copy; omit for secretary).
    include_communion: include The Sacrament of the Lord's Supper liturgy (e.g. first Sunday of month).
    Returns a BytesIO buffer containing the .docx.
    """
    if not Document:
        raise RuntimeError("python-docx is required. pip install python-docx")

    custom = custom_elements or []
    doc = Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(11)
    style.font.name = "Times New Roman"

    # Title
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(f"Worship Service\n{occasion}")
    run.bold = True
    run.font.size = Pt(16)
    run.font.name = "Times New Roman"
    if date:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(date).font.size = Pt(12)
    doc.add_paragraph()

    # 1. Call to Worship (Leader / People, People in bold)
    if liturgy.get("call_to_worship"):
        doc.add_paragraph("Call to Worship", style="Heading 2")
        _add_leader_people_paragraph(doc, liturgy["call_to_worship"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "call_to_worship", custom)

    # 2. Opening Prayer
    if liturgy.get("opening_prayer"):
        doc.add_paragraph("Opening Prayer", style="Heading 2")
        doc.add_paragraph(liturgy["opening_prayer"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "opening_prayer", custom)

    # 3. First Hymn
    if hymns:
        doc.add_paragraph("First Hymn", style="Heading 2")
        h = hymns[0]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "first_hymn", custom)

    # 4. Prayer of Confession (bold)
    if liturgy.get("prayer_of_confession"):
        doc.add_paragraph("Prayer of Confession", style="Heading 2")
        p = doc.add_paragraph()
        p.add_run(liturgy["prayer_of_confession"]).bold = True
        doc.add_paragraph()
    _add_custom_elements_after(doc, "prayer_of_confession", custom)

    # 5. Assurance of Pardon (Leader: ... / ASSURANCE_RESPONSE in bold)
    if liturgy.get("assurance"):
        doc.add_paragraph("Assurance of Pardon", style="Heading 2")
        _add_assurance_paragraph(doc, liturgy["assurance"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "assurance", custom)

    # 6. Prayer for Illumination
    if liturgy.get("prayer_for_illumination"):
        doc.add_paragraph("Prayer for Illumination", style="Heading 2")
        doc.add_paragraph(liturgy["prayer_for_illumination"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "prayer_for_illumination", custom)

    # 7. Old Testament Reading (reference only)
    ot_ref = selected_ot_ref or (scriptures[0] if scriptures else None)
    if ot_ref:
        doc.add_paragraph("Old Testament Reading", style="Heading 2")
        doc.add_paragraph(ot_ref)
        doc.add_paragraph()
    _add_custom_elements_after(doc, "ot_reading", custom)

    # 8. New Testament Reading (reference only)
    nt_ref = selected_nt_ref or (scriptures[1] if len(scriptures) > 1 else None)
    if nt_ref:
        doc.add_paragraph("New Testament Reading", style="Heading 2")
        doc.add_paragraph(nt_ref)
        doc.add_paragraph()
    _add_custom_elements_after(doc, "nt_reading", custom)

    # 9. Sermon Title (optional; for pastor copy only)
    if include_sermon:
        doc.add_paragraph("Sermon Title", style="Heading 2")
        doc.add_paragraph(sermon_title.strip() if sermon_title and sermon_title.strip() else "[Sermon title]")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "sermon", custom)

    # 10. Affirmation of Faith
    doc.add_paragraph("Affirmation of Faith", style="Heading 2")
    doc.add_paragraph("Apostles' Creed")
    doc.add_paragraph()
    _add_custom_elements_after(doc, "affirmation_of_faith", custom)

    # 11. Second Hymn
    if len(hymns) > 1:
        doc.add_paragraph("Second Hymn", style="Heading 2")
        h = hymns[1]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "second_hymn", custom)

    # 11b. Communion liturgy (after second hymn when communion is included)
    if include_communion:
        _add_communion_liturgy(doc)
    _add_custom_elements_after(doc, "communion", custom)

    # 12. Prayers of the People (optional; for pastor copy only)
    if include_prayers_of_the_people and liturgy.get("prayers_of_the_people"):
        doc.add_paragraph("Prayers of the People", style="Heading 2")
        doc.add_paragraph(liturgy["prayers_of_the_people"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "prayers_of_the_people", custom)

    # 13. Offertory Prayer
    if liturgy.get("offertory_prayer"):
        doc.add_paragraph("Offertory Prayer", style="Heading 2")
        doc.add_paragraph(liturgy["offertory_prayer"])
        doc.add_paragraph()
    _add_custom_elements_after(doc, "offertory_prayer", custom)

    # 14. Third Hymn
    if len(hymns) > 2:
        doc.add_paragraph("Third Hymn", style="Heading 2")
        h = hymns[2]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()
    _add_custom_elements_after(doc, "third_hymn", custom)
    _add_custom_elements_after(doc, "benediction", custom)  # "Before Benediction"

    # Benediction
    if liturgy.get("benediction"):
        doc.add_paragraph("Benediction", style="Heading 2")
        doc.add_paragraph(liturgy["benediction"])

    _add_custom_elements_after(doc, "end", custom)  # At the end (after Benediction)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
