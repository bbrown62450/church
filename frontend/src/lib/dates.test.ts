import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import {
  addDays,
  formatLongDate,
  formatServiceDate,
  formatShortDate,
  inSupportedRange,
  isFirstSundayOfMonth,
  isSunday,
  isValidDateIso,
  nextSunday,
  parseIsoDate,
  todayIn,
  weekday,
} from "./dates";

// Shared with the backend fixtures folder (F §5.3); tests never run in the Vercel build.
const NEXT_SUNDAY = JSON.parse(
  readFileSync(new URL("../../../backend/tests/fixtures/shared/next_sunday.json", import.meta.url), "utf-8"),
) as { cases: { from: string; expected: string }[] };

describe("lib/dates", () => {
  it("nextSunday passes every case in shared/next_sunday.json", () => {
    expect(NEXT_SUNDAY.cases.length).toBeGreaterThanOrEqual(4);
    for (const { from, expected } of NEXT_SUNDAY.cases) {
      expect(nextSunday(from), from).toBe(expected);
    }
  });

  it("todayIn reads the calendar day in the church's zone and falls back to the browser's zone", () => {
    const now = new Date(Date.UTC(2026, 8, 27, 2, 30)); // 2026-09-27T02:30Z
    expect(todayIn("America/Los_Angeles", now)).toBe("2026-09-26");
    expect(todayIn("UTC", now)).toBe("2026-09-27");
    const browser = todayIn(undefined, now);
    expect(browser).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(todayIn("Not/A_Zone", now)).toBe(browser);
    expect(todayIn("", now)).toBe(browser);
    expect(todayIn(null, now)).toBe(browser);
  });

  it("formats service dates without zero padding, and invalid input as empty", () => {
    expect(formatServiceDate("2026-10-04")).toBe("October 4, 2026");
    expect(formatLongDate("2026-10-04")).toBe("Sunday, October 4, 2026");
    expect(formatLongDate("2026-09-29")).toBe("Tuesday, September 29, 2026");
    expect(formatShortDate("2026-10-04")).toBe("October 4");
    for (const bad of ["", "2026-10-4", "2026-13-01", "not a date"]) {
      expect(formatServiceDate(bad)).toBe("");
      expect(formatLongDate(bad)).toBe("");
      expect(formatShortDate(bad)).toBe("");
    }
  });

  it("isFirstSundayOfMonth is true only for a Sunday on days 1-7", () => {
    expect(isFirstSundayOfMonth("2026-10-04")).toBe(true);
    expect(isFirstSundayOfMonth("2026-10-11")).toBe(false);
    expect(isFirstSundayOfMonth("2026-10-01")).toBe(false); // a Thursday
    expect(isFirstSundayOfMonth("")).toBe(false);
  });

  it("validates ISO strings by the calendar, not the shape alone", () => {
    expect(parseIsoDate("2026-10-04")).toEqual({ y: 2026, m: 10, d: 4 });
    expect(isValidDateIso("2028-02-29")).toBe(true);
    for (const bad of ["", "2026-02-29", "2026-02-30", "2026-04-31", "2026-00-10", "2026-9-4",
                       "2026-09-04T00:00:00", " 2026-09-04", "20260904", "0"]) {
      expect(isValidDateIso(bad), bad).toBe(false);
    }
  });

  it("does calendar arithmetic across month, year and leap-day edges", () => {
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2028-03-01", -1)).toBe("2028-02-29");
    expect(addDays("2026-10-04", 0)).toBe("2026-10-04");
    expect(weekday("2026-10-04")).toBe(0);
    expect(weekday("2026-09-29")).toBe(2);
    expect(isSunday("2026-10-04")).toBe(true);
    expect(isSunday("2026-10-05")).toBe(false);
    expect(isSunday("")).toBe(false);
    expect(() => addDays("2026-02-30", 1)).toThrow(RangeError);
  });

  it("inSupportedRange accepts years 1900-2199 only", () => {
    expect(inSupportedRange("1900-01-01")).toBe(true);
    expect(inSupportedRange("2199-12-31")).toBe(true);
    expect(inSupportedRange("1899-12-31")).toBe(false);
    expect(inSupportedRange("2200-01-01")).toBe(false);
    expect(inSupportedRange("")).toBe(false);
  });
});
