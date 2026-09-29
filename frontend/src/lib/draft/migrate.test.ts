import { describe, expect, it } from "vitest";

import { CHURCH_IDS, churchProfile, testDraft, USER_ID } from "@/test/fixtures";

import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";

const OWNER = { userId: USER_ID, churchId: churchProfile().id };

describe("draft migrate and parseStoredDraft (F §4.6 Versioning)", () => {
  it("round-trips a stored draft", () => {
    const d = testDraft();
    expect(migrations).toEqual({});
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
  });

  it("rejects corrupt JSON, invalid data, a missing or future version, and another owner's draft", () => {
    const d = testDraft();
    const cases: [string, string][] = [
      ["corrupt JSON", "{not json"],
      ["not an object", "[1, 2]"],
      ["null", "null"],
      ["no version", JSON.stringify({ ...d, version: undefined })],
      ["version 0", JSON.stringify({ ...d, version: 0 })],
      ["a future version", JSON.stringify({ ...d, version: 2 })],
      ["schema-invalid", JSON.stringify({ ...d, readings: { ...d.readings, scriptures: "Psalm 23" } })],
      ["another user", JSON.stringify({ ...d, user_id: "someone-else" })],
      ["another church", JSON.stringify({ ...d, church_id: CHURCH_IDS.hope })],
    ];
    for (const [name, text] of cases) {
      expect(() => parseStoredDraft(text, OWNER), name).toThrow(DraftRestoreError);
    }
  });

  it("runs the migrations step by step up to the target, and a missing step is an error", () => {
    const seen: number[] = [];
    const table: Record<number, Migration> = {
      1: (draft) => {
        seen.push(draft.version as number);
        return { ...draft, added_in_2: null };
      },
      2: (draft) => {
        seen.push(draft.version as number);
        return { ...draft, added_in_3: [] };
      },
    };
    expect(migrate({ version: 1, kept: "yes" }, table, 3)).toEqual({
      version: 3,
      kept: "yes",
      added_in_2: null,
      added_in_3: [],
    });
    expect(seen).toEqual([1, 2]);
    expect(migrate({ version: 3 }, table, 3)).toEqual({ version: 3 });
    expect(() => migrate({ version: 1 }, { 2: table[2] }, 3)).toThrow(DraftRestoreError);
  });
});
