"""Text formatting (formatting spec, 2026-10-25; owner decisions 3 to 5 of
2026-10-24): the chosen set of markdown a text box takes, read the same way
by the Word files, the printed bulletin (PDF and Word) and so the emailed
bulletin's attachments. frontend/src/lib/formatting.ts mirrors it for the
Review step's preview; both pass tests/fixtures/shared/formatting.json.

The grammar (the spec's "Grammar" is the full statement):
- Inline, within one line: **bold**, *italic* (either may hold the other).
  The line is read left to right into marks (a backslash and one of
  ESCAPABLE, "**", "*") and other characters. A mark opens only before a
  character that is not a space and not after an ASCII letter or digit; it
  closes at the next mark of its kind after a character that is not a space
  and not before an ASCII letter or digit, with something between. A mark
  that never closes prints as typed, so "Psalm 23:1*", "5 * 3" and "2*3*4"
  print as typed. A backslash before *, #, - or . prints that character
  alone ("\\*").
- Blocks, a whole line starting at its first character: "# " a heading,
  "## " a smaller heading, "- " a bulleted item, "1. " (one to three digits)
  a numbered item, its number as typed. Anything else is text; text lines
  next to each other stay one paragraph with their line breaks, as today.
  "#1 hymn", "### x" and "-x" are text.
- Two boxes are dialogue (INLINE_ONLY): the Call to Worship and the
  Assurance of Pardon take bold and italic only, so their Leader and People
  lines read as today.

has_marks is the backward-compatibility switch: text without any mark
prints exactly as before this change (every renderer keeps its old path for
it). Pure: no python-docx, reportlab, database or FastAPI.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Kind = Literal["text", "heading1", "heading2", "item"]

# The sections whose text is Leader/People dialogue: bold and italic only.
INLINE_ONLY = frozenset({"call_to_worship", "assurance"})
BULLET = "•"
ESCAPABLE = "*#-."
# "Whitespace" for the marks' rules: a space, a tab or a no-break space.
_SPACE = " \t\u00a0"
_ALNUM = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
_HEADING = re.compile(r"(#{1,2}) (.*)")
_BULLET = re.compile(r"- (.*)")
_NUMBER = re.compile(r"([0-9]{1,3}\.) (.*)")


def hanging_points(marker: str) -> float:
    """An item's hanging indent in points, in every file: 18 (0.25 in) after BULLET; 27 (0.375 in) after a number,
    so the widest one ("999.", 19.25 pt in 11 pt Times, plus the PDF's bullet gap of 6.6 pt) still fits and a
    list's words line up from "1." to "100." (fix agent, finding 6)."""
    return 18.0 if marker == BULLET else 27.0


@dataclass(frozen=True)
class Span:
    text: str
    bold: bool = False
    italic: bool = False


@dataclass(frozen=True)
class Block:
    kind: Kind
    spans: tuple[Span, ...]
    marker: str = ""          # an item's BULLET or its number as typed ("3.")


def _strip(s: str) -> str:
    return s.strip(_SPACE)


def _tokens(line: str) -> list[tuple[str, int, int]]:
    """The line read left to right into (kind, start, end): "esc" (a backslash
    and an ESCAPABLE character), "**", "*", or "ch" (any other character)."""
    out, i = [], 0
    while i < len(line):
        if line[i] == "\\" and i + 1 < len(line) and line[i + 1] in ESCAPABLE:
            out.append(("esc", i, i + 2))
        elif line.startswith("**", i):
            out.append(("**", i, i + 2))
        elif line[i] == "*":
            out.append(("*", i, i + 1))
        else:
            out.append(("ch", i, i + 1))
        i = out[-1][2]
    return out


def _inline_line(line: str) -> list[Span]:
    """Bold and italic in one line, in one pass (linear in its length)."""
    toks = _tokens(line)
    n = len(toks)

    def before(t) -> str:
        return line[t[1] - 1] if t[1] > 0 else ""

    def after(t) -> str:
        return line[t[2]] if t[2] < len(line) else ""

    opens = [t[0] in ("*", "**") and after(t) not in ("", *_SPACE) and before(t) not in _ALNUM for t in toks]
    closes = [t[0] in ("*", "**") and before(t) not in _SPACE and after(t) not in _ALNUM for t in toks]
    # nxt[kind][i]: the first closing token of that kind at i or after it (n: none).
    nxt = {kind: [n] * (n + 1) for kind in ("*", "**")}
    for kind, table in nxt.items():
        for i in range(n - 1, -1, -1):
            table[i] = i if toks[i][0] == kind and closes[i] else table[i + 1]

    def walk(lo: int, hi: int, bold: bool, italic: bool) -> list[Span]:
        out: list[Span] = []
        buf: list[str] = []
        i = lo
        while i < hi:
            kind, a, b = toks[i]
            if kind == "esc":
                buf.append(line[a + 1])
                i += 1
                continue
            if kind in ("*", "**") and opens[i] and not (bold if kind == "**" else italic):
                j = nxt[kind][i + 2] if i + 2 <= n else n          # at least one token inside
                if j < hi:
                    if buf:
                        out.append(Span("".join(buf), bold, italic))
                        buf = []
                    out += walk(i + 1, j, bold or kind == "**", italic or kind == "*")
                    i = j + 1
                    continue
            buf.append(line[a:b])
            i += 1
        if buf:
            out.append(Span("".join(buf), bold, italic))
        return out

    return walk(0, n, False, False)


def merge(spans) -> tuple[Span, ...]:
    """Spans with neighbours of the same type joined, empty ones dropped."""
    out: list[Span] = []
    for span in spans:
        if not span.text:
            continue
        if out and (out[-1].bold, out[-1].italic) == (span.bold, span.italic):
            out[-1] = Span(out[-1].text + span.text, span.bold, span.italic)
        else:
            out.append(span)
    return tuple(out)


def inline(text: str) -> tuple[Span, ...]:
    """Bold and italic in `text`, line by line (a mark never spans a line break)."""
    spans: list[Span] = []
    for n, line in enumerate(text.split("\n")):
        if n:
            spans.append(Span("\n"))
        spans += _inline_line(line)
    return merge(spans)


def _block_of(line: str) -> tuple[Kind, str, str] | None:
    """A heading or an item line's kind, its content and its marker; None for text."""
    for pattern, kind in ((_HEADING, None), (_BULLET, "item"), (_NUMBER, "item")):
        m = pattern.fullmatch(line)
        if m is None:
            continue
        content = _strip(m.group(m.lastindex))
        if not content:
            return None
        if kind is None:
            return ("heading1" if m.group(1) == "#" else "heading2"), content, ""
        return "item", content, (BULLET if pattern is _BULLET else m.group(1))
    return None


def parse(text: str, *, inline_only: bool = False) -> list[Block]:
    """The text as printed blocks. Inline only: one text block."""
    if inline_only:
        return [Block("text", inline(text))] if text else []
    blocks: list[Block] = []
    lines: list[str] = []

    def flush() -> None:
        while lines and not _strip(lines[0]):
            lines.pop(0)
        while lines and not _strip(lines[-1]):
            lines.pop()
        if lines:
            blocks.append(Block("text", inline("\n".join(lines))))
        lines.clear()

    for line in text.split("\n"):
        found = _block_of(line)
        if found is None:
            lines.append(line)
            continue
        flush()
        kind, content, marker = found
        blocks.append(Block(kind, inline(content), marker))
    flush()
    return blocks


def has_marks(text: str, *, inline_only: bool = False) -> bool:
    """Whether any mark of the grammar is in `text`. False: it prints exactly as before formatting."""
    for line in text.split("\n"):
        if not inline_only and _block_of(line) is not None:
            return True
        if line and inline(line) != (Span(line),):
            return True
    return False


def plain(text: str, *, inline_only: bool = False) -> str:
    """The words as they print, without the marks: what the reviewer and the pews read.
    A heading's "#" goes; an item keeps "- " or its number, so the list still reads as one."""
    if not has_marks(text, inline_only=inline_only):
        return text
    out = []
    for line in text.split("\n"):
        found = None if inline_only else _block_of(line)
        if found is None:
            out.append("".join(s.text for s in inline(line)))
            continue
        kind, content, marker = found
        words = "".join(s.text for s in inline(content))
        out.append(words if kind != "item" else f"{'-' if marker == BULLET else marker} {words}")
    return "\n".join(out)
