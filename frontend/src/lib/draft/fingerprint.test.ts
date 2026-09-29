import { describe, expect, it } from "vitest";

import { testDraft } from "@/test/fixtures";

import { fingerprint, fnv1a32, isDirty, stableStringify } from "./fingerprint";
import { draftToServicePayload } from "./mapping";
import { editOccasion } from "./readings";
import type { DraftV1 } from "./schema";

describe("fingerprint and isDirty (F §4.6 Unsaved changes)", () => {
  it("is FNV-1a over stable JSON, so key order never changes it", () => {
    expect(stableStringify({ b: 1, a: { d: [2, { f: 1, e: 0 }], c: null } })).toBe(
      '{"a":{"c":null,"d":[2,{"e":0,"f":1}]},"b":1}',
    );
    expect(fingerprint({ a: 1, b: [1, 2] })).toBe(fingerprint({ b: [1, 2], a: 1 }));
    expect(fingerprint({ a: 1 })).not.toBe(fingerprint({ a: 2 }));
    // The published FNV-1a 32-bit test vectors.
    expect(fnv1a32("")).toBe("811c9dc5");
    expect(fnv1a32("a")).toBe("e40c292c");
    expect(fnv1a32("foobar")).toBe("bf9cf968");
    // UTF-8 bytes, so a server-side FNV-1a over the same JSON would match.
    expect(fnv1a32("é")).toBe("1e9de8c1");
    expect(fingerprint({ a: 1 })).toBe(fnv1a32('{"a":1}'));
  });

  it("isDirty: never saved means not pristine; saved means the payload changed", () => {
    const fresh = testDraft();
    expect(isDirty(fresh)).toBe(false);
    expect(isDirty(editOccasion(fresh, "Harvest"))).toBe(true);
    const withDefaultBenediction = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Halverson", origin: "default" } },
      },
    }));
    expect(isDirty(withDefaultBenediction)).toBe(false);

    const saved: DraftV1 = {
      ...editOccasion(fresh, "Harvest"),
      saved_fingerprint: fingerprint(draftToServicePayload(editOccasion(fresh, "Harvest"))),
    };
    expect(isDirty(saved)).toBe(false);
    expect(isDirty(editOccasion(saved, "Harvest Home"))).toBe(true);
  });
});
