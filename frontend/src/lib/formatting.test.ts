/**
 * The preview's copy of the print rules (formatting spec, Testing): every case of
 * backend/tests/fixtures/shared/formatting.json and of the seeded random
 * shared/formatting_fuzz.json, which backend/tests/test_formatting.py checks
 * against the printed bulletin itself, so the preview shows what prints.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { hasMarks, parse, printedLines, type BoxKind, type PrintedLine } from "./formatting";

type Case = { name: string; box: BoxKind; text: string; lines: { style: string; marker: string; spans: [string, string][] }[] };
const read = (name: string) =>
  JSON.parse(readFileSync(new URL(`../../../backend/tests/fixtures/shared/${name}`, import.meta.url), "utf-8")) as {
    assurance_response: string;
    cases: Case[];
  };
const fixture = read("formatting.json");
const fuzz = read("formatting_fuzz.json");

const asFixture = (line: PrintedLine) => ({
  style: line.style,
  marker: line.marker,
  spans: line.spans.map((s) => [s.text, `${s.bold ? "b" : ""}${s.italic ? "i" : ""}`]),
});

describe("formatting (shared/formatting.json)", () => {
  it("prints every case as the printed bulletin does", () => {
    expect(fixture.cases).toHaveLength(35);
    for (const c of fixture.cases) {
      expect(printedLines(c.box, c.text, fixture.assurance_response).map(asFixture), c.name).toEqual(c.lines);
    }
  });

  it("prints every seeded random text as the printed bulletin does (formatting_fuzz.json)", () => {
    expect(fuzz.cases).toHaveLength(300);
    for (const c of fuzz.cases) {
      expect(printedLines(c.box, c.text, fuzz.assurance_response).map(asFixture), JSON.stringify(c.text)).toEqual(c.lines);
    }
  });

  it("finds no mark in text saved before formatting", () => {
    for (const text of ["Psalm 23:1*", "#1 hymn", "5 * 3 * 2", "2*3*4", "A lone ** pair", "a**b**c", "### three\n-x\n1) one", "* star"]) {
      expect(hasMarks(text), text).toBe(false);
    }
    expect(hasMarks("**b**")).toBe(true);
    expect(hasMarks("- item")).toBe(true);
    expect(hasMarks("- item", true)).toBe(false);
  });

  it("keeps what is typed as text, never markup", () => {
    const [block] = parse("<img src=x onerror=alert(1)> **<b>x</b>**");
    expect(block.spans).toEqual([
      { text: "<img src=x onerror=alert(1)> ", bold: false, italic: false },
      { text: "<b>x</b>", bold: true, italic: false },
    ]);
  });

  it("reads a long text of unclosed marks in linear time", () => {
    // Five times a box's 20,000-character limit: the linear scan takes a tenth of a second here; a scan that looks
    // for each mark's close from scratch takes about 0.3 s at the limit, so only a larger text tells them apart.
    const started = Date.now();
    for (const text of ["*a ".repeat(33_330), "**a ".repeat(25_000), "*".repeat(100_000), "**x* ".repeat(20_000)]) parse(text);
    expect(Date.now() - started).toBeLessThan(1000);
  });
});
