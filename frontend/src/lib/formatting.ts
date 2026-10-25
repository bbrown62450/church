/**
 * Text formatting (formatting spec, 2026-10-25; owner decisions 3 to 5): the
 * TypeScript copy of backend/formatting.py and of how backend/printed_bulletin.py
 * prints a box's text (`formatted`, `_leader_people`, `_assurance`), for the
 * Review step's preview. `formatting.test.ts` pins both to
 * backend/tests/fixtures/shared/formatting.json, which the backend passes too.
 * Pure: the preview draws these lines as React text, never as HTML.
 */

export type Span = { text: string; bold: boolean; italic: boolean };
export type LineStyle = "body" | "bold" | "hanging" | "center" | "heading1" | "heading2" | "item" | "center_heading1" | "center_heading2";
/** `markerBold`: an item's marker in bold, in a box all bold (printed_bulletin.Line.marker_bold). */
export type PrintedLine = { style: LineStyle; spans: Span[]; marker: string; markerBold?: boolean };
/** Which printed rule a box follows: a prayer, the all-bold Prayer of Confession (and own Affirmation text), the
 * Call to Worship's Leader and People lines, the Assurance with its fixed response, a centered announcement. */
export type BoxKind = "prayer" | "confession" | "dialogue" | "assurance" | "announcement";

type Kind = "text" | "heading1" | "heading2" | "item";
type Block = { kind: Kind; spans: Span[]; marker: string };

export const BULLET = "•";
const ESCAPABLE = "*#-.";
const SPACE = " \t\u00a0";
const ALNUM = /^[A-Za-z0-9]$/;
// [\s\S], not ".": Python's "." takes every character but "\n", and a line has none.
const HEADING = /^(#{1,2}) ([\s\S]*)$/;
const BULLET_LINE = /^- ([\s\S]*)$/;
const NUMBER = /^([0-9]{1,3}\.) ([\s\S]*)$/;

const span = (text: string, bold = false, italic = false): Span => ({ text, bold, italic });
const isSpace = (ch: string) => ch !== "" && SPACE.includes(ch);
const isAlnum = (ch: string) => ALNUM.test(ch);
const strip = (s: string) => {
  let a = 0;
  let b = s.length;
  while (a < b && isSpace(s[a])) a++;
  while (b > a && isSpace(s[b - 1])) b--;
  return s.slice(a, b);
};

type Token = { kind: "esc" | "**" | "*" | "ch"; start: number; end: number };

function tokens(line: string): Token[] {
  const out: Token[] = [];
  let i = 0;
  while (i < line.length) {
    let kind: Token["kind"] = "ch";
    let width = 1;
    if (line[i] === "\\" && i + 1 < line.length && ESCAPABLE.includes(line[i + 1])) [kind, width] = ["esc", 2];
    else if (line.startsWith("**", i)) [kind, width] = ["**", 2];
    else if (line[i] === "*") kind = "*";
    out.push({ kind, start: i, end: i + width });
    i += width;
  }
  return out;
}

function inlineLine(line: string): Span[] {
  const toks = tokens(line);
  const n = toks.length;
  const before = (t: Token) => (t.start > 0 ? line[t.start - 1] : "");
  const after = (t: Token) => (t.end < line.length ? line[t.end] : "");
  const mark = (t: Token) => t.kind === "*" || t.kind === "**";
  const opens = toks.map((t) => mark(t) && after(t) !== "" && !isSpace(after(t)) && !isAlnum(before(t)));
  const closes = toks.map((t) => mark(t) && !isSpace(before(t)) && !isAlnum(after(t)));
  const next = (kind: "*" | "**") => {
    const table = new Array<number>(n + 1).fill(n);
    for (let i = n - 1; i >= 0; i--) table[i] = toks[i].kind === kind && closes[i] ? i : table[i + 1];
    return table;
  };
  const nxt = { "*": next("*"), "**": next("**") };

  function walk(lo: number, hi: number, bold: boolean, italic: boolean): Span[] {
    const out: Span[] = [];
    let buf = "";
    let i = lo;
    while (i < hi) {
      const t = toks[i];
      if (t.kind === "esc") {
        buf += line[t.start + 1];
        i++;
        continue;
      }
      if ((t.kind === "*" || t.kind === "**") && opens[i] && !(t.kind === "**" ? bold : italic)) {
        const j = i + 2 <= n ? nxt[t.kind][i + 2] : n; // at least one token inside
        if (j < hi) {
          if (buf) out.push(span(buf, bold, italic));
          buf = "";
          out.push(...walk(i + 1, j, bold || t.kind === "**", italic || t.kind === "*"));
          i = j + 1;
          continue;
        }
      }
      buf += line.slice(t.start, t.end);
      i++;
    }
    if (buf) out.push(span(buf, bold, italic));
    return out;
  }

  return walk(0, n, false, false);
}

/** Spans with neighbours of the same type joined, empty ones dropped (`formatting.merge`). */
export function merge(spans: Iterable<Span>): Span[] {
  const out: Span[] = [];
  for (const s of spans) {
    if (!s.text) continue;
    const last = out[out.length - 1];
    if (last && last.bold === s.bold && last.italic === s.italic) out[out.length - 1] = span(last.text + s.text, s.bold, s.italic);
    else out.push(s);
  }
  return out;
}

/** Bold and italic, line by line (`formatting.inline`). */
export function inline(text: string): Span[] {
  const spans: Span[] = [];
  text.split("\n").forEach((line, n) => {
    if (n) spans.push(span("\n"));
    spans.push(...inlineLine(line));
  });
  return merge(spans);
}

function blockOf(line: string): { kind: Kind; content: string; marker: string } | null {
  const heading = HEADING.exec(line);
  if (heading) {
    const content = strip(heading[2]);
    return content ? { kind: heading[1] === "#" ? "heading1" : "heading2", content, marker: "" } : null;
  }
  const bullet = BULLET_LINE.exec(line);
  if (bullet) {
    const content = strip(bullet[1]);
    return content ? { kind: "item", content, marker: BULLET } : null;
  }
  const number = NUMBER.exec(line);
  if (number) {
    const content = strip(number[2]);
    return content ? { kind: "item", content, marker: number[1] } : null;
  }
  return null;
}

/** The text as printed blocks (`formatting.parse`). */
export function parse(text: string, inlineOnly = false): Block[] {
  if (inlineOnly) return text ? [{ kind: "text", spans: inline(text), marker: "" }] : [];
  const blocks: Block[] = [];
  let lines: string[] = [];
  const flush = () => {
    while (lines.length && !strip(lines[0])) lines.shift();
    while (lines.length && !strip(lines[lines.length - 1])) lines.pop();
    if (lines.length) blocks.push({ kind: "text", spans: inline(lines.join("\n")), marker: "" });
    lines = [];
  };
  for (const line of text.split("\n")) {
    const found = blockOf(line);
    if (found === null) {
      lines.push(line);
      continue;
    }
    flush();
    blocks.push({ kind: found.kind, spans: inline(found.content), marker: found.marker });
  }
  flush();
  return blocks;
}

/** Whether any mark is in `text` (`formatting.has_marks`); without one it prints exactly as before. */
export function hasMarks(text: string, inlineOnly = false): boolean {
  return text.split("\n").some((line) => {
    if (!inlineOnly && blockOf(line) !== null) return true;
    if (!line) return false;
    const spans = inline(line);
    return !(spans.length === 1 && spans[0].text === line && !spans[0].bold && !spans[0].italic);
  });
}

// --- How printed_bulletin prints a box ---

/** Python's `str.isspace` characters, so `pyStrip` trims as `str.strip()` does. */
const PY_SPACE = "\t\n\u000b\u000c\r\u001c\u001d\u001e\u001f \u0085\u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000";
const PY_SPACE_CLASS = "[\\t\\n\\u000b\\u000c\\r\\u001c-\\u001f \\u0085\\u00a0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000]";
function pyStrip(s: string): string {
  let a = 0;
  let b = s.length;
  while (a < b && PY_SPACE.includes(s[a])) a++;
  while (b > a && PY_SPACE.includes(s[b - 1])) b--;
  return s.slice(a, b);
}
// printed_bulletin._PEOPLE_LEADER (`\b(Leader|People):\s*`, ignoring case; Python's \w is a letter, a digit
// or "_") and _ASSURANCE_PEOPLE (a "People:" at the start or after a space). No lookbehind: older Safari has none.
const PEOPLE_LEADER = new RegExp(`(Leader|People):${PY_SPACE_CLASS}*`, "giu");
const WORD = /^[\p{L}\p{N}_]$/u;

function labels(text: string): { index: number; end: number; role: string }[] {
  return [...text.matchAll(PEOPLE_LEADER)]
    .filter((m) => m.index === 0 || !WORD.test(text[m.index - 1]))
    .map((m) => ({ index: m.index, end: m.index + m[0].length, role: m[1].toLowerCase() }));
}

function typedPeople(text: string): number {
  for (const m of text.matchAll(/People:/giu)) if (m.index === 0 || PY_SPACE.includes(text[m.index - 1])) return m.index;
  return -1;
}

const line = (style: LineStyle, spans: Span[], marker = "", markerBold = false): PrintedLine =>
  markerBold ? { style, spans, marker, markerBold } : { style, spans, marker };

/** printed_bulletin._spans: a dialogue part, bold and italic only. */
function dialogueSpans(text: string, bold = false): Span[] {
  if (!hasMarks(text, true)) return [span(text, bold)];
  return merge(inline(text).map((s) => span(s.text, bold || s.bold, s.italic)));
}

/** printed_bulletin.formatted. */
function formatted(text: string, style: LineStyle, bold = false): PrintedLine[] {
  if (!hasMarks(text)) return [line(style, [span(text, bold)])];
  const center = style === "center";
  return parse(text).map((block) => {
    if (block.kind === "heading1" || block.kind === "heading2") {
      const spans = merge(block.spans.map((s) => span(s.text, true, s.italic)));
      return line(center ? (`center_${block.kind}` as LineStyle) : block.kind, spans);
    }
    const spans = merge(block.spans.map((s) => span(s.text, bold || s.bold, s.italic)));
    if (block.kind === "text") return line(style, spans);
    if (center) return line(style, merge([span(`${block.marker} `, bold), ...spans]));
    return line("item", spans, block.marker, bold);
  });
}

/** printed_bulletin._leader_people. */
function leaderPeople(text: string): PrintedLine[] {
  const matches = labels(text);
  if (!matches.length) return [line("body", dialogueSpans(text))];
  const lines: PrintedLine[] = [];
  const first = matches[0].index;
  if (first > 0 && pyStrip(text.slice(0, first))) lines.push(line("body", dialogueSpans(pyStrip(text.slice(0, first)))));
  matches.forEach((m, i) => {
    const end = i + 1 < matches.length ? matches[i + 1].index : text.length;
    const content = pyStrip(text.slice(m.end, end));
    if (m.role === "people") lines.push(line("hanging", [span("People: ", true), ...dialogueSpans(content, true)]));
    else lines.push(line("hanging", [span("Leader: "), ...dialogueSpans(content)]));
  });
  return lines;
}

/** printed_bulletin._assurance. */
function assurance(text: string, response: string): PrintedLine[] {
  let leader = pyStrip(text);
  const people = typedPeople(leader);
  if (people >= 0) leader = pyStrip(leader.slice(0, people));
  if (leader.startsWith("Leader:")) leader = pyStrip(leader.slice(7));
  const lines = leader ? [line("hanging", [span("Leader: "), ...dialogueSpans(leader)])] : [];
  return [...lines, line("bold", [span(response, true)])];
}

/** A box's text as the printed bulletin prints it. `response` is the Assurance's fixed response
 * (`GET /liturgy/config`'s `assurance_response`). */
export function printedLines(box: BoxKind, text: string, response = ""): PrintedLine[] {
  switch (box) {
    case "prayer":
      return formatted(text, "body");
    case "confession":
      return formatted(text, "bold", true);
    case "dialogue":
      return leaderPeople(text);
    case "assurance":
      return assurance(text, response);
    case "announcement":
      return formatted(text, "center");
  }
}

/** The two dialogue boxes (`formatting.INLINE_ONLY`): bold and italic only, so Leader and People lines read as today. */
export const INLINE_ONLY: ReadonlySet<string> = new Set(["call_to_worship", "assurance"]);

/**
 * A box's text as the server prints it (`usecases.archive`: `_xml_safe`, then `str.strip()`): a Windows or
 * old-Mac line ending, a vertical tab or a form feed becomes a line break, what a Word file cannot hold
 * (`_XML_BAD`: other control characters, U+FFFE, U+FFFF, a lone surrogate) goes, and the ends are trimmed.
 */
export function serverStrip(raw: string): string {
  let out = "";
  for (const ch of raw.replace(/\r\n?/g, "\n")) {
    // By code point, as Python reads a string: a surrogate pair is one character, a lone surrogate its own.
    const c = ch.codePointAt(0) ?? 0;
    if (c === 0x0b || c === 0x0c) out += "\n";
    else if (!(c <= 0x08 || (c >= 0x0e && c <= 0x1f) || c === 0xfffe || c === 0xffff || (c >= 0xd800 && c <= 0xdfff))) out += ch;
  }
  return pyStrip(out);
}
