import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  BOOKS,
  classify,
  cleanLines,
  defaultNtRef,
  defaultReadingPair,
  expandRefOptions,
  isNtRef,
  normalizeBookText,
  pickerOptions,
  resolveReadings,
  scriptureKey,
  splitAlternatives,
  splitBook,
  type ReadingPair,
} from "./scripture-refs";

/**
 * AC8, TypeScript half (F §5.3): the shared fixture that backend
 * `test_scripture_refs.py` also runs. Each section loops inside one test, so
 * the count stays stable when 5a adds `resolve_readings` cases.
 */
type Pair = { ot: string | null; nt: string | null; ot_auto: boolean; nt_auto: boolean };
type Fixture = {
  _about: Record<string, string>;
  books: { name: string; testament: string; aliases: string[] }[];
  split_alternatives: { ref: string; expected: string[] }[];
  split_book: { ref: string; expected: { book: string; rest: string } | null }[];
  classify: { ref: string; expected: string }[];
  is_nt_ref: { ref: string; expected: boolean }[];
  expand_ref_options: { refs: string[]; expected: string[] }[];
  clean_lines: { lines: string[]; expected: string[] }[];
  picker_options: { scriptures: string[]; expected: { ot: string[]; nt: string[] } }[];
  resolve_readings: { name: string; scriptures: string[]; ot_pick: string; nt_pick: string; expected: Pair }[];
  default_reading_pair: { scriptures: string[]; expected: Pair }[];
  default_nt_ref: { scriptures: string[]; expected: string | null }[];
  scripture_key: { ref: string; expected: string }[];
};

const FIXTURE = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/scripture_refs.json", import.meta.url), "utf-8"),
) as Fixture;

/** The fixture keeps Python's snake_case keys (2a clarification 40). */
function camel(p: Pair): ReadingPair {
  return { ot: p.ot, nt: p.nt, otAuto: p.ot_auto, ntAuto: p.nt_auto };
}

describe("lib/scripture-refs against shared/scripture_refs.json", () => {
  it("has every section the Python suite runs", () => {
    for (const section of ["books", "split_alternatives", "split_book", "classify", "is_nt_ref",
                           "expand_ref_options", "clean_lines", "picker_options", "resolve_readings",
                           "default_reading_pair", "default_nt_ref", "scripture_key"] as const) {
      expect(FIXTURE[section].length, section).toBeGreaterThan(0);
      expect(FIXTURE._about[section], section).toBeTypeOf("string");
    }
  });

  it("BOOKS equals the fixture's books, in order, with normalized aliases", () => {
    expect(BOOKS.map((b) => ({ name: b.name, testament: b.testament, aliases: [...b.aliases] }))).toEqual(
      FIXTURE.books,
    );
    for (const b of BOOKS) for (const alias of b.aliases) expect(normalizeBookText(alias)).toBe(alias);

    // The 19 cases of backend/tests/test_scripture_refs.py::test_normalize_book_text, pinned here too.
    const normalizeCases: [string, string][] = [
      ["  *1 John 3:1-3", "1 john 3:1-3"],
      ["* Acts 2:14a", "acts 2:14a"],
      ["Gen.  1:1", "gen 1:1"],
      ["I Cor. 13:1", "1 cor 13:1"],
      ["II Kings 2:1-12", "2 kings 2:1-12"],
      ["III John 1", "3 john 1"],
      ["IV Maccabees 1:1", "4 maccabees 1:1"],
      ["First Samuel 3", "1 samuel 3"],
      ["Second Corinthians 5", "2 corinthians 5"],
      ["Third John", "3 john"],
      ["Fourth Maccabees", "4 maccabees"],
      ["1st Peter 2", "1 peter 2"],
      ["2nd Timothy", "2 timothy"],
      ["3rd John", "3 john"],
      ["4th Maccabees", "4 maccabees"],
      ["1john 3:16", "1 john 3:16"],
      ["Isaiah 9:2", "isaiah 9:2"],
      ["Iv", "iv"],
      ["  Psalm   23  ", "psalm 23"],
    ];
    expect(normalizeCases).toHaveLength(19);
    for (const [raw, expected] of normalizeCases) expect(normalizeBookText(raw), raw).toBe(expected);
  });

  it("splitAlternatives", () => {
    for (const c of FIXTURE.split_alternatives) expect(splitAlternatives(c.ref), c.ref).toEqual(c.expected);
  });

  it("splitBook", () => {
    for (const c of FIXTURE.split_book) {
      const hit = splitBook(c.ref);
      expect(hit === null ? null : { book: hit.book.name, rest: hit.rest }, c.ref).toEqual(c.expected);
    }
  });

  it("classify and isNtRef", () => {
    for (const c of FIXTURE.classify) expect(classify(c.ref), c.ref).toBe(c.expected);
    for (const c of FIXTURE.is_nt_ref) expect(isNtRef(c.ref), c.ref).toBe(c.expected);
  });

  it("expandRefOptions and cleanLines", () => {
    for (const c of FIXTURE.expand_ref_options) expect(expandRefOptions(c.refs), c.refs.join("|")).toEqual(c.expected);
    for (const c of FIXTURE.clean_lines) expect(cleanLines(c.lines), c.lines.join("|")).toEqual(c.expected);
  });

  it("pickerOptions", () => {
    for (const c of FIXTURE.picker_options) {
      expect(pickerOptions(c.scriptures), c.scriptures.join("|")).toEqual(c.expected);
    }
  });

  it("resolveReadings, including the mixed and stale-pick cases; an automatic NT is never a Psalm", () => {
    for (const c of FIXTURE.resolve_readings) {
      const got = resolveReadings(c.scriptures, c.ot_pick, c.nt_pick);
      expect(got, c.name).toEqual(camel(c.expected));
      if (got.ntAuto && got.nt !== null) expect(isNtRef(splitAlternatives(got.nt)[0]), c.name).toBe(true);
    }
    expect(FIXTURE.resolve_readings.some((c) => c.name.startsWith("S mixed:"))).toBe(true);
    expect(FIXTURE.resolve_readings.some((c) => c.name.startsWith("S stale:"))).toBe(true);
  });

  it("defaultReadingPair and defaultNtRef", () => {
    for (const c of FIXTURE.default_reading_pair) {
      expect(defaultReadingPair(c.scriptures), c.scriptures.join("|")).toEqual(camel(c.expected));
    }
    for (const c of FIXTURE.default_nt_ref) expect(defaultNtRef(c.scriptures), c.scriptures.join("|")).toBe(c.expected);
  });

  it("scriptureKey", () => {
    for (const c of FIXTURE.scripture_key) expect(scriptureKey(c.ref), c.ref).toBe(c.expected);
  });
});
