/** Which Gospel passage the Voices of the Church panel shows (Voices V1 spec "Which Gospel passage"). */
import { describe, expect, it } from "vitest";

import { applyReadingSet, editScriptureLines, setDate, setPick } from "@/lib/draft/readings";
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
