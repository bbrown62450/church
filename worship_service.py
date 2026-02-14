#!/usr/bin/env python3
"""
Worship service generator: hymn suggestions by scripture, OpenAI liturgy,
and Word document export.
"""

import logging
import os
import re
from typing import Dict, Any, List, Optional
from io import BytesIO
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv
from notion_hymns import NotionHymnsDB
from hymn_utils import get_property_value

load_dotenv()

logger = logging.getLogger(__name__)

# Cache for resolved Hymnary audio URLs (number -> url) to avoid re-fetching
_hymnary_audio_resolve_cache: Dict[int, Optional[str]] = {}

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


def hymns_by_scripture(
    db: NotionHymnsDB,
    scripture_ref: str,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """
    Return hymns whose Scripture References contain the given reference
    (e.g. "Matthew 17", "Psalm 99").
    """
    ref_clean = scripture_ref.strip()
    if not ref_clean:
        return []

    # Normalize for matching: "Matthew 17" matches "Matthew 17:1-8"
    ref_lower = ref_clean.lower()
    # Allow "Matt 17" -> "matthew 17"
    ref_lower = re.sub(r"\bmatt\b", "matthew", ref_lower)

    try:
        # Notion filter: rich_text contains (partial match)
        results = db.search_hymns(
            filter_property="Scripture References",
            filter_value=ref_clean,
        )
    except Exception:
        results = []

    # If Notion filter uses exact-ish match, also scan all hymns for partial ref
    if len(results) < 10:
        all_hymns = db.list_hymns()
        seen_ids = {h["id"] for h in results}
        for h in all_hymns:
            if h["id"] in seen_ids:
                continue
            scripture = get_property_value(h, "Scripture References")
            if scripture and ref_lower in scripture.lower():
                results.append(h)
                seen_ids.add(h["id"])
                if len(results) >= limit:
                    break

    return results[:limit]


def hymn_display_info(hymn: Dict[str, Any], *, resolve_audio: bool = False) -> Dict[str, Any]:
    """Extract title, number, and link for display/export.
    If resolve_audio is True, fetches the hymn page to get the real MP3 URL (used for scripture list players).
    """
    title = get_property_value(hymn, "Hymn Title") or "Unknown"
    number = get_property_value(hymn, "Hymn Number")
    link = get_property_value(hymn, "Hymnary.org Link")
    if number is not None:
        audio_url = (
            resolve_hymnary_audio_url(number, title)
            if resolve_audio
            else _hymnary_audio_url(number, title)
        )
    else:
        audio_url = None
    logger.info(
        "hymn_display_info hymn_id=%s number=%s title=%r audio_url=%s",
        hymn.get("id"),
        number,
        title,
        audio_url,
    )
    return {
        "title": title,
        "number": number,
        "link": link,
        "audio_url": audio_url,
    }


def _hymnary_audio_url(number: Optional[int], title: str) -> Optional[str]:
    """
    Build a possible Hymnary.org GG2013 audio MP3 URL. Pattern from hymnary:
    .../hymnary/audio/GG2013/{number:03d}-{slug}.mp3
    Slug is a short lowercase version of the title (spaces as %20). Not all hymns have audio.
    Some hymns use a different CDN (e.g. 150282) and slug format; use resolve_hymnary_audio_url() for those.
    """
    if number is None:
        logger.debug("_hymnary_audio_url number=None title=%r -> None", title)
        return None
    slug = re.sub(r"[^\w\s]", "", (title or "").lower())
    slug = re.sub(r"\s+", "%20", slug.strip())[:30]
    if not slug:
        slug = str(number)
    num_str = f"{int(number):03d}"
    url = f"https://hymnary.org/media/fetch/148542/hymnary/audio/GG2013/{num_str}-{slug}.mp3"
    logger.debug("_hymnary_audio_url number=%s title=%r -> %s", number, title, url)
    return url


def resolve_hymnary_audio_url(number: Optional[int], title: str) -> Optional[str]:
    """
    Resolve the real GG2013 audio URL by fetching the hymn page and parsing the MP3 link.
    Hymnary uses different CDN IDs and slug formats (e.g. 191 uses 150282 and WeHaveComeAt_accomp),
    so the constructed URL can point at the wrong file. Results are cached by hymn number.
    Never raises: on any error returns the constructed fallback URL so the hymn list still renders.
    """
    if number is None:
        return None
    num = int(number)
    if num in _hymnary_audio_resolve_cache:
        return _hymnary_audio_resolve_cache[num]
    fallback = _hymnary_audio_url(number, title)
    try:
        import httpx
        from bs4 import BeautifulSoup
    except ImportError:
        _hymnary_audio_resolve_cache[num] = fallback
        return fallback
    page_url = f"https://hymnary.org/hymn/GG2013/{num}"
    try:
        with httpx.Client(follow_redirects=True, timeout=8.0) as client:
            r = client.get(page_url)
            r.raise_for_status()
    except Exception as e:
        logger.debug("resolve_hymnary_audio_url fetch %s: %s", page_url, e)
        _hymnary_audio_resolve_cache[num] = fallback
        return fallback
    try:
        soup = BeautifulSoup(r.text, "lxml")
        found: Optional[str] = None
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or "hymnary/audio/GG2013" not in href or ".mp3" not in href:
                continue
            raw = href.split("?")[0]
            if not raw.endswith(".mp3"):
                continue
            if raw.startswith("/"):
                found = "https://hymnary.org" + raw
            else:
                parsed = urlparse(raw)
                found = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
            break
        url = found or fallback
    except Exception as e:
        logger.debug("resolve_hymnary_audio_url parse %s: %s", page_url, e)
        url = fallback
    _hymnary_audio_resolve_cache[num] = url
    if url != fallback:
        logger.debug("resolve_hymnary_audio_url number=%s -> %s", num, url)
    return url


def generate_liturgy(
    *,
    occasion: str,
    scriptures: List[str],
    hymns: List[Dict[str, str]],
    sections: List[str],
    api_key: Optional[str] = None,
    user_overrides: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """
    Use OpenAI to generate liturgy text for the requested sections.
    If user_overrides[section] is non-empty, that text is used instead of generating.
    Returns dict mapping section key -> plain text.
    """
    overrides = user_overrides or {}
    client = None
    if OpenAI:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if key:
            client = OpenAI(api_key=key)

    if not client:
        return {
            s: f"[Configure OPENAI_API_KEY to generate {s.replace('_', ' ')}.]"
            for s in sections
        }

    hymn_lines = "\n".join(
        f"- {h.get('title', '')} (GG2013 #{h.get('number', '')})" for h in hymns
    )
    scripture_lines = "\n".join(f"- {s}" for s in scriptures) if scriptures else "None specified."

    system = (
        "You are a thoughtful worship writer for Christian liturgy from a moderate Reformed perspective, "
        "in line with PC(USA) theology. Write in clear, inclusive language. "
        "Avoid exclusively male references to God: use 'God' by name, or varied language (e.g. 'God who is Father, Son, and Holy Spirit' when trinitarian language fits); "
        "do not use only 'he/him/his' or 'Lord' alone for God; you may use 'Lord' as one among other titles. "
        "Keep each piece concise and usable in worship. Output only the liturgy text, no meta-commentary or labels."
    )

    out = {}
    for section in sections:
        if overrides.get(section, "").strip():
            out[section] = overrides[section].strip()
            continue
        if section == "call_to_worship":
            prompt = (
                f"Write a Call to Worship for: {occasion}. "
                f"Scriptures: {scripture_lines}. Opening hymn: {hymns[0].get('title', '') if hymns else 'N/A'}. "
                "Use exactly this format with four parts: 'Leader: ' (2-3 lines), then 'People: ' (one short response), "
                "then 'Leader: ' again (2-3 lines), then 'People: ' again (one short response)."
            )
        elif section == "prayer_of_confession":
            prompt = (
                f"Write a Prayer of Confession for: {occasion}. "
                f"Scriptures: {scripture_lines}. "
                "One short paragraph. First person plural (we). End with a line inviting silence or a brief moment of confession."
            )
        elif section == "assurance":
            prompt = (
                f"Write only the Leader line for Assurance of Pardon for: {occasion}, "
                "grounded in God’s grace in Christ. One sentence. Do not include "
                "'People:' or 'Thanks be to God'—that will be added separately. "
                "Start your response with 'Leader: ' followed by the sentence."
            )
        elif section == "opening_prayer":
            prompt = (
                f"Write an Opening Prayer (collect) for: {occasion}. "
                f"Scriptures: {scripture_lines}. "
                "Around 100 words. Address God, thank or praise, and ask for one thing fitting the day. End with 'Amen.'"
            )
        elif section == "prayer_for_illumination":
            prompt = (
                f"Write a Prayer for Illumination for: {occasion}. "
                f"Scriptures: {scripture_lines}. "
                "Write 3-5 sentences asking God to open hearts and minds to the Scripture, "
                "that we may hear and respond. End with 'Amen.'"
            )
        elif section == "offertory_prayer":
            prompt = (
                f"Write a brief Offertory Prayer for: {occasion}. "
                "One or two sentences dedicating our gifts and ourselves to God's service. End with 'Amen.'"
            )
        elif section == "prayers_of_the_people":
            prompt = (
                f"Write Prayers of the People for: {occasion}. "
                f"Scriptures: {scripture_lines}. Hymns: {hymn_lines}. "
                "Write a substantial, full prayer (at least 10–15 paragraphs) in 'out to in' order: "
                "First, prayers for the world (nations, creation, peace, the suffering). "
                "Second, prayers for the Church universal and our denomination and congregation. "
                "Third, prayers for our country and our local community and leaders. "
                "Fourth, prayers for ourselves and our families. "
                "Then include an explicit invitation for the congregation to share joys and concerns aloud "
                "(e.g. 'Let us now lift up the joys and concerns of this congregation' or 'You are invited to name aloud...'). "
                "Then include a clear bid for a moment of silence—to lift up individuals or situations, or simply to sit in silence before God. "
                "Use 'we pray,' 'let us pray,' or similar. End with a closing that leads into the Lord's Prayer or a final amen. "
                "Write in full sentences and paragraphs; this should feel like a complete, unhurried pastoral prayer."
            )
        elif section == "benediction":
            prompt = (
                f"Write a Benediction (1–3 sentences) for: {occasion}. "
                f"Scriptures: {scripture_lines}. "
                "Send the people out to serve and share God’s love. You may invoke the Trinity. End with 'Amen.'"
            )
        else:
            out[section] = ""
            continue

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

    # 2. Opening Prayer
    if liturgy.get("opening_prayer"):
        doc.add_paragraph("Opening Prayer", style="Heading 2")
        doc.add_paragraph(liturgy["opening_prayer"])
        doc.add_paragraph()

    # 3. First Hymn
    if hymns:
        doc.add_paragraph("First Hymn", style="Heading 2")
        h = hymns[0]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()

    # 4. Prayer of Confession (bold)
    if liturgy.get("prayer_of_confession"):
        doc.add_paragraph("Prayer of Confession", style="Heading 2")
        p = doc.add_paragraph()
        p.add_run(liturgy["prayer_of_confession"]).bold = True
        doc.add_paragraph()

    # 5. Assurance of Pardon (Leader: ... / People: Thanks be to God! Amen. in bold)
    if liturgy.get("assurance"):
        doc.add_paragraph("Assurance of Pardon", style="Heading 2")
        _add_assurance_paragraph(doc, liturgy["assurance"])
        doc.add_paragraph()

    # 6. Prayer for Illumination
    if liturgy.get("prayer_for_illumination"):
        doc.add_paragraph("Prayer for Illumination", style="Heading 2")
        doc.add_paragraph(liturgy["prayer_for_illumination"])
        doc.add_paragraph()

    # 7. Old Testament Reading (reference only)
    ot_ref = selected_ot_ref or (scriptures[0] if scriptures else None)
    if ot_ref:
        doc.add_paragraph("Old Testament Reading", style="Heading 2")
        doc.add_paragraph(ot_ref)
        doc.add_paragraph()

    # 8. New Testament Reading (reference only)
    nt_ref = selected_nt_ref or (scriptures[1] if len(scriptures) > 1 else None)
    if nt_ref:
        doc.add_paragraph("New Testament Reading", style="Heading 2")
        doc.add_paragraph(nt_ref)
        doc.add_paragraph()

    # 9. Sermon Title (optional; for pastor copy only)
    if include_sermon:
        doc.add_paragraph("Sermon Title", style="Heading 2")
        doc.add_paragraph(sermon_title.strip() if sermon_title and sermon_title.strip() else "[Sermon title]")
        doc.add_paragraph()

    # 10. Affirmation of Faith
    doc.add_paragraph("Affirmation of Faith", style="Heading 2")
    doc.add_paragraph("Apostles' Creed (or as printed)")
    doc.add_paragraph()

    # 11. Second Hymn
    if len(hymns) > 1:
        doc.add_paragraph("Second Hymn", style="Heading 2")
        h = hymns[1]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()

    # 11b. Communion liturgy (after second hymn when communion is included)
    if include_communion:
        _add_communion_liturgy(doc)

    # 12. Prayers of the People (optional; for pastor copy only)
    if include_prayers_of_the_people and liturgy.get("prayers_of_the_people"):
        doc.add_paragraph("Prayers of the People", style="Heading 2")
        doc.add_paragraph(liturgy["prayers_of_the_people"])
        doc.add_paragraph()

    # 13. Offertory Prayer
    if liturgy.get("offertory_prayer"):
        doc.add_paragraph("Offertory Prayer", style="Heading 2")
        doc.add_paragraph(liturgy["offertory_prayer"])
        doc.add_paragraph()

    # 14. Third Hymn
    if len(hymns) > 2:
        doc.add_paragraph("Third Hymn", style="Heading 2")
        h = hymns[2]
        doc.add_paragraph(f"{h.get('title', '')} — #{h.get('number', '')}")
        doc.add_paragraph()

    # Benediction
    if liturgy.get("benediction"):
        doc.add_paragraph("Benediction", style="Heading 2")
        doc.add_paragraph(liturgy["benediction"])

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf
