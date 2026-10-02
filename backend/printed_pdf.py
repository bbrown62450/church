"""The printed bulletin as a print-ready PDF (printed bulletin spec, PR 1):
legal paper, landscape, two 7 x 8.5 in booklet pages side by side in reading
order (layout B, the owner's sample): side 1 is the cover and page 1, side 2
pages 2 and 3, and so on, with the announcements page last. Nothing is
folded or padded: an odd page count leaves the last side's right half blank.

render_pdf lays the bulletin out with reportlab in one pass: each legal side
has two frames, one per booklet page, so the text flows from the left half
to the right half and on to the next side (cover, order of worship,
announcements, each starting a new booklet page). The fonts are the PDF standard Times family, which every viewer and printer
has, so nothing is embedded; a character outside their Windows-1252 set
prints as "?" (to_pdf_text). Pure: no database or FastAPI.
"""
from __future__ import annotations

import unicodedata
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, FrameBreak, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

import printed_bulletin as pb

SHEET_WIDTH = 2 * pb.PAGE_WIDTH        # legal, landscape: 14 x 8.5 in
MARGIN = 36.0                          # 0.5 in on every side
FOOTER = 20.0                          # the page number's baseline
RIGHT_COLUMN = 120.0                   # the leader's column on an element line
# A heading starts the next booklet page when less than this is left below it
# (a section heading: itself, an element and a line; an element: itself and
# two lines), so no heading ends a page alone and a long reading still starts
# under its heading instead of leaving a gap (keepWithNext would move the
# whole reading to the next page).
KEEP = {"section": 60.0, "element": 47.0}

_GRAY = Color(0.45, 0.45, 0.45)


def to_pdf_text(text: str) -> str:
    """Text the standard fonts can print: a Windows-1252 character stays as
    it is ("½", "…"); any other is NFKC-normalized (a ligature or a full-width
    letter becomes plain letters), an invisible format character (a
    zero-width space or joiner, a byte order mark) is dropped, and what is
    still outside Windows-1252 becomes "?"."""
    out = []
    for ch in text:
        if ch in "\n\t" or _cp1252(ch):
            out.append(ch)
        elif unicodedata.category(ch) != "Cf":
            out += [c if _cp1252(c) else "?" for c in unicodedata.normalize("NFKC", ch)]
    return "".join(out)


def _cp1252(ch: str) -> bool:
    try:
        ch.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def _style(name: str, **kw) -> ParagraphStyle:
    base = dict(fontName="Times-Roman", fontSize=11, leading=13)
    base.update(kw)
    return ParagraphStyle(name, **base)


STYLES = {
    "header": _style("header", alignment=TA_CENTER),
    "element": _style("element", spaceBefore=8),
    "section": _style("section", alignment=TA_CENTER, spaceBefore=12, spaceAfter=4),
    "body": _style("body"),
    "bold": _style("bold"),
    "hanging": _style("hanging", leftIndent=36, firstLineIndent=-36),
    "indent": _style("indent", leftIndent=36),
    "note": _style("note", spaceBefore=10),
    "credit": _style("credit", fontSize=9, leading=11, spaceBefore=4),
    "title": _style("title", fontSize=28, leading=34, alignment=TA_CENTER, spaceAfter=18),
    "box": _style("box", alignment=TA_CENTER),
    "contact": _style("contact", fontName="Helvetica", fontSize=12, leading=15, alignment=TA_CENTER),
    "center": _style("center", alignment=TA_CENTER, spaceBefore=3),
    "right": _style("right", alignment=TA_RIGHT),
    "page": _style("page", alignment=TA_CENTER),
}


def _markup(line: pb.Line) -> str:
    out = []
    for span in line.spans:
        text = escape(to_pdf_text(span.text)).replace("\n", "<br/>")
        if span.italic:
            text = f"<i>{text}</i>"
        if span.bold:
            text = f"<b>{text}</b>"
        out.append(text)
    return "".join(out)


def _flowables(line: pb.Line, width: float) -> list[Flowable]:
    keep = [CondPageBreak(KEEP[line.style])] if line.style in KEEP else []
    return [*keep, _flowable(line, width)]


def _flowable(line: pb.Line, width: float) -> Flowable:
    paragraph = Paragraph(_markup(line), STYLES[line.style])
    if not line.right:
        return paragraph
    right = Paragraph(escape(to_pdf_text(line.right)), STYLES["right"])
    table = Table([[paragraph, right]], colWidths=[width - RIGHT_COLUMN, RIGHT_COLUMN])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    table.spaceBefore = STYLES[line.style].spaceBefore
    return table


class _CoverPicture(Flowable):
    """The cover picture's place (PR 3 prints the picture): a framed box with
    the sermon reading and the date over its lower part, as the sample."""

    def __init__(self, width: float, height: float, label: str, reference: str, date: str):
        super().__init__()
        self.width, self.height = width, height
        self.label, self.reference, self.date = label, reference, date

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setStrokeColor(_GRAY)
        c.rect(0, 0, self.width, self.height)
        c.setFillColor(_GRAY)
        c.setFont("Times-Italic", 11)
        c.drawCentredString(self.width / 2, self.height / 2 + 30, to_pdf_text(self.label))
        c.setFillColorRGB(0, 0, 0)
        for text, y in ((self.reference, 70), (self.date, 40)):
            if text:
                c.setFont("Times-Roman", 12)
                c.drawCentredString(self.width / 2, y, to_pdf_text(text))


def _story(ps: pb.PrintedService, width: float) -> list[Flowable]:
    cover = pb.cover(ps)
    title, label, reference, date, *contact = cover
    story: list[Flowable] = [
        Paragraph(_markup(title), STYLES["title"]),
        _CoverPicture(width - 60, 300, label.text, reference.text, date.text),
        Spacer(1, 30),
        *(Paragraph(_markup(line), STYLES["contact"]) for line in contact),
        FrameBreak(),
    ]
    story += [f for line in pb.order_of_worship(ps) for f in _flowables(line, width)]
    story.append(FrameBreak())
    story += [f for line in pb.announcements(ps) for f in _flowables(line, width)]
    return story


class _TwoUp(BaseDocTemplate):
    """Legal landscape sides, each two booklet pages (a frame each) in reading
    order. A booklet page's number is drawn when its frame begins, so a half
    that nothing flows into (the last side's right half when the page count
    is odd) stays blank; the cover (booklet page 0) has none."""

    def handle_frameBegin(self, resume=0, pageTopFlowables=None):
        super().handle_frameBegin(resume, pageTopFlowables)
        half = self.pageTemplate.frames.index(self.frame)
        number = 2 * (self.page - 1) + half
        if number:
            self.canv.setFont("Times-Bold", 10)
            self.canv.drawCentredString(half * pb.PAGE_WIDTH + pb.PAGE_WIDTH / 2, FOOTER, str(number))


def render_pdf(ps: pb.PrintedService) -> bytes:
    """The print-ready bulletin: legal sides, landscape, two pages to a side in reading order."""
    buf = BytesIO()
    frames = [Frame(x + MARGIN, MARGIN, pb.PAGE_WIDTH - 2 * MARGIN, pb.PAGE_HEIGHT - 2 * MARGIN,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id=f"half{x:.0f}")
              for x in (0.0, pb.PAGE_WIDTH)]
    doc = _TwoUp(buf, pagesize=(SHEET_WIDTH, pb.PAGE_HEIGHT), title="Printed bulletin", invariant=1,
                 leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=MARGIN)
    doc.addPageTemplates([PageTemplate("side", frames)])
    doc.build(_story(ps, pb.PAGE_WIDTH - 2 * MARGIN))
    return buf.getvalue()
