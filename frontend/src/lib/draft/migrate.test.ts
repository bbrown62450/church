import { describe, expect, it } from "vitest";

import { CHURCH_IDS, churchProfile, testDraft, USER_ID } from "@/test/fixtures";

import { DraftRestoreError, migrate, migrations, parseStoredDraft, type Migration } from "./migrate";
import { fingerprint } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { freshBulletin } from "./schema";
import { reviewStatus } from "./status";

const OWNER = { userId: USER_ID, churchId: churchProfile().id };

describe("draft migrate and parseStoredDraft (F §4.6 Versioning)", () => {
  it("round-trips a stored draft", () => {
    const d = testDraft();
    expect(Object.keys(migrations)).toEqual(["1", "2"]);
    expect(parseStoredDraft(JSON.stringify(d), OWNER)).toEqual(d);
  });

  it("migrates a version 1 draft: editing gains the draft's date, and save_key_fingerprint starts null (slice 5a-3)", () => {
    const { save_key_fingerprint, ...v1 } = { ...testDraft(), version: 1 };
    expect(save_key_fingerprint).toBeNull();
    const editing = { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00" };
    expect(parseStoredDraft(JSON.stringify(v1), OWNER)).toEqual({ ...testDraft(), save_key: v1.save_key });
    expect(parseStoredDraft(JSON.stringify({ ...v1, editing }), OWNER)).toMatchObject({
      version: 3,
      save_key_fingerprint: null,
      editing: { ...editing, date_iso: "2026-10-04" },
    });
    const undated = { ...v1, editing, readings: { ...v1.readings, date_iso: "" } };
    expect(parseStoredDraft(JSON.stringify(undated), OWNER).editing).toEqual({ ...editing, date_iso: null });
  });

  it("migrates a version 2 draft: an empty bulletin, nothing else changed, and a saved draft stays Saved (PR 2b)", () => {
    const { bulletin, ...v2 } = { ...testDraft(), version: 2 };
    expect(bulletin).toEqual(freshBulletin());
    // 5a-3's fingerprint: the payload had no bulletin, as today's has none while nothing is filled in.
    const payload = draftToServicePayload(testDraft());
    expect("bulletin" in payload).toBe(false);
    const editing = { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-10-04" };
    const saved = { ...v2, editing, saved_fingerprint: fingerprint(payload), last_step: "review" };
    const migrated = parseStoredDraft(JSON.stringify(saved), OWNER);
    expect(migrated).toEqual({ ...testDraft(), ...saved, version: 3, bulletin: freshBulletin() });
    expect(reviewStatus(migrated)).toBe("saved");
  });

  it("rejects corrupt JSON, invalid data, a missing or future version, and another owner's draft", () => {
    const d = testDraft();
    const cases: [string, string][] = [
      ["corrupt JSON", "{not json"],
      ["not an object", "[1, 2]"],
      ["null", "null"],
      ["no version", JSON.stringify({ ...d, version: undefined })],
      ["version 0", JSON.stringify({ ...d, version: 0 })],
      ["a future version", JSON.stringify({ ...d, version: 4 })],
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
    // A migration that throws, or returns no object, is a restore error too.
    const broken: Record<number, Migration> = {
      1: () => {
        throw new TypeError("boom");
      },
    };
    expect(() => migrate({ version: 1 }, broken, 2)).toThrow(DraftRestoreError);
    expect(() => migrate({ version: 1 }, { 1: () => null as never }, 2)).toThrow(DraftRestoreError);
  });
});
