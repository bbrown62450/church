#!/usr/bin/env python3
"""
Worship service generator: OpenAI liturgy and Word document export (the
hymn helpers moved to hymn_search, hymn_suggest and usecases.hymns in slice 3).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, Any, List, Optional
from io import BytesIO

import liturgy_prompts
import service_rubric

logger = logging.getLogger(__name__)

# Optional imports for docx and openai
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

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
    """Add The Sacrament of the Lord's Supper liturgy (invitation, great thanksgiving, etc.)."""
    doc.add_paragraph("The Sacrament of the Lord's Supper", style="Heading 1")
    doc.add_paragraph()

    doc.add_paragraph("Invitation to the Table", style="Heading 2")
    doc.add_paragraph(
        "This is the table of our Lord Jesus Christ. It is not a reward for the righteous, "
        "but nourishment for those who hunger; not a prize for the strong, but grace for those who are weary. "
        "Here, blessing is not earned but received. All who seek to walk humbly with God, and who trust in God's mercy, "
        "are welcome at this table."
    )
    doc.add_paragraph()

    doc.add_paragraph("Great Thanksgiving", style="Heading 2")
    doc.add_paragraph("The Lord be with you.")
    p = doc.add_paragraph()
    p.add_run("And also with you.").bold = True
    doc.add_paragraph("Lift up your hearts.")
    p = doc.add_paragraph()
    p.add_run("We lift them up to the Lord.").bold = True
    doc.add_paragraph("Let us give thanks to the Lord our God.")
    p = doc.add_paragraph()
    p.add_run("It is right to give our thanks and praise.").bold = True
    doc.add_paragraph(
        "It is truly right and our greatest joy to give you thanks and praise, O God, "
        "creator of heaven and earth, for you have made us and all things, and in your love you hold us in life. "
        "And so we join the everlasting song:"
    )
    p = doc.add_paragraph()
    p.add_run(
        "Holy, holy, holy Lord, God of power and might, heaven and earth are full of your glory. "
        "Hosanna in the highest. Blessed is the one who comes in the name of the Lord. Hosanna in the highest."
    ).bold = True
    doc.add_paragraph(
        "You are holy, O God of majesty, and blessed is Jesus Christ, your Son, our Lord, "
        "who by his life, death, and resurrection has reconciled the world to you. On the night in which he gave himself up "
        "he took bread, gave thanks, broke it, and gave it to his disciples. And likewise the cup after supper. "
        "Remembering his death and resurrection, we offer ourselves in praise and thanksgiving. Therefore we proclaim the mystery of faith:"
    )
    doc.add_paragraph("Christ has died.")
    doc.add_paragraph("Christ is risen.")
    doc.add_paragraph("Christ will come again.")
    doc.add_paragraph()

    doc.add_paragraph("Words of Institution", style="Heading 2")
    doc.add_paragraph("[Words of institution as printed or as used.]")
    doc.add_paragraph()

    doc.add_paragraph("The Lord's Prayer", style="Heading 2")
    doc.add_paragraph("[The Lord's Prayer as printed.]")
    doc.add_paragraph()

    doc.add_paragraph("Breaking of the Bread and Communion", style="Heading 2")
    doc.add_paragraph(
        "The bread that we break is a sharing in the body of Christ. "
        "The cup that we bless is a sharing in the blood of Christ. Come, for all is ready."
    )
    doc.add_paragraph()

    doc.add_paragraph("Prayer After Communion", style="Heading 2")
    doc.add_paragraph(
        "Gracious God, we give you thanks that you have fed us at this table of grace, "
        "strengthening us not to win our lives, but to live them faithfully. Send us out to do justice, "
        "to love kindness, and to walk humbly with you, bearing your blessing into a world still hungry for hope, "
        "through Jesus Christ our Lord. Amen."
    )
    doc.add_paragraph()


def _add_assurance_paragraph(doc, leader_text: str) -> None:
    """Add Assurance: Leader line then 'People: Thanks be to God! Amen.' in bold."""
    leader_clean = (leader_text or "").strip()
    if leader_clean.startswith("Leader:"):
        leader_clean = leader_clean[7:].strip()
    if leader_clean:
        doc.add_paragraph("Leader: " + leader_clean)
    # Always add the congregational response
    p = doc.add_paragraph()
    r = p.add_run("People: Thanks be to God! Amen.")
    r.bold = True


SERMON_TEXT_LIMIT = 2000


def _sermon_text_block(sermon_text: Optional[tuple]) -> str:
    """The sermon-text context appended to each liturgy prompt, or '' when the
    reference or text is missing, or the passage failed to load."""
    if not sermon_text:
        return ""
    ref, text = sermon_text
    text = (text or "").strip()
    if not (ref or "").strip() or not text or "[Could not load text]" in text:
        return ""
    return (
        f"Sermon text ({ref.strip()}), for themes only; do not quote, cite, or name it:\n"
        f"{text[:SERMON_TEXT_LIMIT]}"
    )


def generate_liturgy(
    *,
    occasion: str,
    scriptures: List[str],
    hymns: List[Dict[str, str]],
    sections: List[str],
    api_key: Optional[str] = None,
    user_overrides: Optional[Dict[str, str]] = None,
    prompt_overrides: Optional[Dict[str, str]] = None,
    rubric: Optional[Dict[str, Any]] = None,
    sermon_text: Optional[tuple] = None,
) -> Dict[str, str]:
    """
    Use OpenAI to generate liturgy text for the requested sections.
    If user_overrides[section] is non-empty, that text is used instead of generating.
    prompt_overrides (per church) replaces the default AI instructions for the
    "system" voice and/or any section; missing keys fall back to the defaults.
    Returns dict mapping section key -> plain text.
    rubric adds each section's quality checklist to its prompt. It is merged over
    the defaults, so None, a church's sparse overrides or a full rubric all
    work. sermon_text, as (reference, passage text), is
    added to every prompt for themes; it is skipped when missing or when the
    passage failed to load. Both are appended in code, so churches with edited
    prompts get them too.
    """
    overrides = user_overrides or {}
    prompts = liturgy_prompts.merge_prompts(prompt_overrides)
    rubric = service_rubric.merge_rubric(rubric)
    sermon_block = _sermon_text_block(sermon_text)
    client = None
    if OpenAI:
        key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        if key and not key.isascii():
            # A pasted key sometimes arrives with Unicode look-alike characters
            # (e.g. from a rich-text copy path); the HTTP layer then fails with a
            # cryptic 'ascii codec' error. Say what actually happened instead.
            return {
                s: "[Your OPENAI_API_KEY contains invalid (non-ASCII) characters — "
                   "it was likely mangled when pasted. Re-paste it in Settings → Secrets.]"
                for s in sections
            }
        if key:
            client = OpenAI(api_key=key)

    if not client:
        return {
            s: f"[Configure OPENAI_API_KEY to generate {s.replace('_', ' ')}.]"
            for s in sections
        }

    hymn_lines = "\n".join(
        f"- {h.get('title', '')} (#{h.get('number', '')})" for h in hymns
    )
    scripture_lines = "\n".join(f"- {s}" for s in scriptures) if scriptures else "None specified."

    system = prompts["system"]
    opening_hymn = hymns[0].get("title", "") if hymns else "N/A"

    out = {}
    for section in sections:
        if overrides.get(section, "").strip():
            out[section] = overrides[section].strip()
            continue
        template = prompts.get(section)
        if not template:
            out[section] = ""
            continue
        prompt = liturgy_prompts.render(
            template,
            occasion=occasion,
            scriptures=scripture_lines,
            opening_hymn=opening_hymn,
            hymns=hymn_lines,
        )
        checklist = rubric["prayers"].get(section)
        if checklist:
            label = liturgy_prompts.SECTION_LABELS.get(section, section)
            prompt += "\n\n" + service_rubric.format_checklist(label, checklist)
        if sermon_block:
            prompt += "\n\n" + sermon_block

        model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        try:
            r = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1024,
            )
            text = (r.choices[0].message.content or "").strip()
            out[section] = text
        except Exception as e:
            out[section] = f"[Error generating {section}: {e}]"

    return out


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

    # 5. Assurance of Pardon (Leader: ... / People: Thanks be to God! Amen. in bold)
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
