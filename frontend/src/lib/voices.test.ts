/** Which Gospel passage the Voices of the Church panel shows (Voices V1 spec "Which Gospel passage"). */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { applyReadingSet, editScriptureLines, effectivePicks, setDate, setPick } from "@/lib/draft/readings";
import { lectionary, noReadings, testDraft } from "@/test/fixtures";

import { gospelOf, voicesPassage } from "./voices";

const DATE = "2026-10-04";
const lect = lectionary(DATE);

function lines(...scriptures: string[]) {
  return testDraft((d) => editScriptureLines(setDate(d, DATE), scriptures.join("\n")));
}

describe("gospelOf", () => {
  it("names the Gospel of a reference's first alternative, by any of its names", () => {
    expect(gospelOf("Matthew 22:15-22")).toBe("Matthew");
    expect(gospelOf("Jn 20:19-31")).toBe("John");
    expect(gospelOf("Mark 1:1-8 or Luke 3:1-6")).toBe("Mark");
    expect(gospelOf("1 John 3:1-3")).toBeNull();
    expect(gospelOf("Acts 2:1-21 or Luke 24:44-53")).toBeNull();
    expect(gospelOf("")).toBeNull();
  });

  it("reads optional verses in parentheses, and names nothing for a whole book or a line half typed", () => {
    expect(gospelOf("Luke 2:1-14 (15-20)")).toBe("Luke");
    expect(gospelOf("Luke 2:(1-7) 8-20")).toBe("Luke");
    expect(gospelOf("John 1:(1-9) 10-18")).toBe("John");
    expect(gospelOf("Luke 15:1-3, 11b-32")).toBe("Luke");
    expect(gospelOf("Matthew 26:14-27:66 or Matthew 27:11-54")).toBe("Matthew");
    expect(gospelOf("John 3")).toBe("John");
    for (const typing of ["John", "John ", "John 3:", "John 3:16-", "John 3:16,"]) expect(gospelOf(typing)).toBeNull();
  });
});

/** The cases backend/tests/test_catena.py runs against the server's reading (Voices V1 build review M3). */
const SHARED = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/voices_references.json", import.meta.url), "utf-8"),
) as { both: { ref: string; gospel: string }[]; neither: string[]; client_waits: string[] };

describe("gospelOf against shared/voices_references.json", () => {
  it("asks for every reference the server reads as a Gospel passage, ranges with ';' and spaced dashes included", () => {
    expect(SHARED.both.length).toBeGreaterThan(30);
    expect(Object.fromEntries(SHARED.both.map((c) => [c.ref, gospelOf(c.ref)]))).toEqual(
      Object.fromEntries(SHARED.both.map((c) => [c.ref, c.gospel])),
    );
  });

  it("never asks for a reference the server refuses, nor for a whole book or a part still being typed", () => {
    const waits = [...SHARED.neither, ...SHARED.client_waits];
    expect(Object.fromEntries(waits.map((ref) => [ref, gospelOf(ref)]))).toEqual(Object.fromEntries(waits.map((ref) => [ref, null])));
  });
});

describe("voicesPassage", () => {
  it("takes a bulletin reading from a Gospel first: the picked New Testament reading", () => {
    const d = setPick(testDraft((x) => applyReadingSet(setDate(x, DATE), lect, 0)), "nt", "Matthew 21:33-46");
    expect(voicesPassage(d, lect)).toEqual({ reference: "Matthew 21:33-46", line: "Matthew 21:33-46", fromLectionary: false });
  });

  it("takes the automatic New Testament reading when it is a Gospel", () => {
    expect(voicesPassage(lines("Isaiah 5:1-7", "Luke 15:1-3, 11b-32"), undefined)).toEqual({
      reference: "Luke 15:1-3, 11b-32",
      line: "Luke 15:1-3, 11b-32",
      fromLectionary: false,
    });
  });

  it("takes a Gospel alternative of a chosen line, and keeps the line to place the panel", () => {
    expect(voicesPassage(lines("Isaiah 40:1-11", "Mark 1:1-8 or Luke 3:1-6"), undefined)).toEqual({
      reference: "Mark 1:1-8",
      line: "Mark 1:1-8 or Luke 3:1-6",
      fromLectionary: false,
    });
  });

  it("else takes the Sunday's lectionary Gospel, from the set the draft uses or the default", () => {
    const d = testDraft((x) => applyReadingSet(setDate(x, DATE), lect, 0));
    expect(voicesPassage(d, lect)).toEqual({ reference: "Matthew 21:33-46", line: "Matthew 21:33-46", fromLectionary: true });
    const easter = testDraft((x) => applyReadingSet(setDate(x, DATE), lect, 1));
    expect(voicesPassage(easter, lect)).toEqual({ reference: "John 20:1-18", line: "John 20:1-18", fromLectionary: true });
    expect(voicesPassage(lines("Isaiah 5:1-7", "Philippians 3:4b-14"), lect)).toEqual({
      reference: "Matthew 21:33-46",
      line: "Matthew 21:33-46",
      fromLectionary: true,
    });
  });

  it("shows nothing without a Gospel: no lectionary answer, another date's, none for the date, or a set with no Gospel", () => {
    const d = lines("Isaiah 5:1-7", "Philippians 3:4b-14");
    expect(voicesPassage(d, undefined)).toBeNull();
    expect(voicesPassage(d, lectionary("2026-10-11"))).toBeNull();
    expect(voicesPassage(d, noReadings(DATE))).toBeNull();
    const noGospel = lectionary(DATE, { reading_sets: [{ name: "A feast", source: "vanderbilt", scriptures: ["Acts 2:1-21", "Psalm 104"] }] });
    expect(voicesPassage(d, noGospel)).toBeNull();
  });
});

describe("a canticle from Luke in the psalm slot is sung, never the Gospel (Voices V1 build review I1)", () => {
  // Advent 4, Year B (Sunday, December 20, 2026), as the RCL prints it: the psalm cell is the
  // Magnificat or Psalm 89, before the second reading and the Gospel.
  const ADVENT_4 = "2026-12-20";
  const MAGNIFICAT = "Luke 1:46b-55 or Psalm 89:1-4, 19-26";
  const advent4 = lectionary(ADVENT_4, {
    reading_sets: [
      {
        name: "Fourth Sunday of Advent",
        source: "vanderbilt",
        scriptures: ["2 Samuel 7:1-11, 16", MAGNIFICAT, "Romans 16:25-27", "Luke 1:26-38"],
      },
    ],
  });
  const GOSPEL = { reference: "Luke 1:26-38", line: "Luke 1:26-38", fromLectionary: true };
  const applied = () => testDraft((x) => applyReadingSet(setDate(x, ADVENT_4), advent4, 0));

  it("with no picks the bulletin's automatic reading is the Magnificat, and the panel follows the set's Gospel", () => {
    const d = applied();
    expect(effectivePicks(d).nt).toBe(MAGNIFICAT);
    expect(voicesPassage(d, advent4)).toEqual(GOSPEL);
    // Before the lookup answers, the lines filled from the set already mark the canticle: nothing yet.
    expect(voicesPassage(d, undefined)).toBeNull();
  });

  it("with 2 Samuel and Romans picked, the lectionary's Gospel is the set's last Gospel line, not the canticle", () => {
    const d = setPick(setPick(applied(), "ot", "2 Samuel 7:1-11, 16"), "nt", "Romans 16:25-27");
    expect(voicesPassage(d, advent4)).toEqual(GOSPEL);
  });

  it("a canticle picked by hand is still not the Gospel", () => {
    expect(voicesPassage(setPick(applied(), "nt", MAGNIFICAT), advent4)).toEqual(GOSPEL);
  });

  it("the Benedictus and the Nunc dimittis likewise", () => {
    for (const canticle of ["Luke 1:68-79", "Luke 2:29-32"]) {
      const set = lectionary(ADVENT_4, {
        reading_sets: [{ name: "A Sunday", source: "vanderbilt", scriptures: ["Malachi 3:1-4", canticle, "Philippians 1:3-11", "Luke 3:1-6"] }],
      });
      const d = testDraft((x) => applyReadingSet(setDate(x, ADVENT_4), set, 0));
      expect(voicesPassage(d, set)).toEqual({ reference: "Luke 3:1-6", line: "Luke 3:1-6", fromLectionary: true });
    }
  });

  it("a Gospel line the pastor chose that is not the set's canticle still wins", () => {
    const d = testDraft((x) => editScriptureLines(setDate(x, ADVENT_4), "2 Samuel 7:1-11, 16\nLuke 1:39-45 (46-55)"));
    expect(voicesPassage(d, advent4)).toEqual({
      reference: "Luke 1:39-45 (46-55)",
      line: "Luke 1:39-45 (46-55)",
      fromLectionary: false,
    });
  });
});
