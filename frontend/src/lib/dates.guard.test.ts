import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

/**
 * F acceptance 12 (F §4.10): no `new Date(` applied to a `YYYY-MM-DD` literal
 * or to an identifier ending in `date_iso` / `dateIso` anywhere in `src/`,
 * except `lib/dates.ts`, which owns date-only arithmetic.
 */
const SRC = fileURLToPath(new URL("..", import.meta.url));
const ALLOWED = new Set(["lib/dates.ts", "lib/dates.guard.test.ts"]);
const FORBIDDEN = /new\s+Date\(\s*(?:["'`]\d{4}-\d{2}-\d{2}["'`]|[\w$.?!\]\[]*?(?:date_iso|[dD]ateIso)\b)/;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx)$/.test(entry.name) ? [path] : [];
  });
}

describe("dates guard (F acceptance 12)", () => {
  it("the pattern catches the forbidden forms and allows timestamps", () => {
    for (const bad of [
      'new Date("2026-10-04")',
      "new Date('2026-10-04')",
      "new Date(`2026-10-04`)",
      "new Date(draft.readings.date_iso)",
      "new Date( dateIso )",
      "new Date(props.serviceDateIso)",
      "new Date(editing?.date_iso)",
    ]) {
      expect(FORBIDDEN.test(bad), bad).toBe(true);
    }
    for (const fine of ["new Date()", "new Date(0)", "new Date(Date.UTC(2026, 8, 27))", "new Date(updated_at)",
                        'new Date("2026-10-04T12:00:00Z")']) {
      expect(FORBIDDEN.test(fine), fine).toBe(false);
    }
  });

  it("no file in src/ outside lib/dates.ts builds a Date from a date-only value", () => {
    const offenders = sourceFiles(SRC)
      .map((path) => relative(SRC, path).split("\\").join("/"))
      .filter((rel) => !ALLOWED.has(rel))
      .filter((rel) => FORBIDDEN.test(readFileSync(join(SRC, rel), "utf-8")));
    expect(offenders).toEqual([]);
  });
});
