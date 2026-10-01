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

  it("after a save, a slot or hymnal change is unsaved; the Exclude switch and other ideas are not (owner answer 1)", () => {
    const pick = { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" };
    const base = testDraft();
    const saved: DraftV1 = { ...base, saved_fingerprint: fingerprint(draftToServicePayload(base)) };
    const hymns = (patch: Partial<DraftV1["hymns"]>): DraftV1 => ({ ...saved, hymns: { ...saved.hymns, ...patch } });
    expect(isDirty(hymns({ slots: { ...saved.hymns.slots, closing: pick } }))).toBe(true);
    expect(isDirty(hymns({ hymnal: "PH1990" }))).toBe(true);
    expect(isDirty(hymns({ exclude_recent: false }))).toBe(false);
    const ideas = { for_date_iso: "2026-10-04", by_slot: { opening: [pick], response: [], closing: [] } };
    expect(isDirty(hymns({ alternatives: ideas }))).toBe(false);
  });

  it("after a save, liturgy that prints is unsaved; a switch on an empty card is not (owner answer 1, 2026-09-30)", () => {
    const base = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: {
          ...d.liturgy.cards,
          call_to_worship: { enabled: true, text: "Come, let us worship.", origin: "typed" },
          benediction: { enabled: true, text: "Halverson", origin: "default" },
        },
      },
    }));
    const saved: DraftV1 = { ...base, saved_fingerprint: fingerprint(draftToServicePayload(base)) };
    const liturgy = (patch: Partial<DraftV1["liturgy"]>): DraftV1 => ({ ...saved, liturgy: { ...saved.liturgy, ...patch } });
    const card = (key: "call_to_worship" | "opening_prayer" | "benediction", patch: object): DraftV1 =>
      liturgy({ cards: { ...saved.liturgy.cards, [key]: { ...saved.liturgy.cards[key], ...patch } } });
    expect(isDirty(saved)).toBe(false);
    expect(isDirty(card("call_to_worship", { text: "Come, let us worship God.", origin: "typed" }))).toBe(true);
    expect(isDirty(card("call_to_worship", { enabled: false }))).toBe(true); // its text leaves the service
    expect(isDirty(liturgy({ include_communion: !saved.liturgy.include_communion, communion_origin: "user" }))).toBe(true);
    expect(isDirty(liturgy({ sermon_title: "Living Water" }))).toBe(true);
    expect(isDirty(liturgy({ custom_elements: [{ id: "c1", label: "Anthem", text: "", insert_after: "sermon" }] }))).toBe(true);
    // Slice 4 Risks item 4: a Benediction following the church default shows the new default as unsaved.
    expect(isDirty(card("benediction", { text: "Go in peace." }))).toBe(true);
    // Switches are not saved (slice 4 BC-17), so switching an empty card prints nothing new.
    expect(isDirty(card("opening_prayer", { enabled: false }))).toBe(false);
  });
});
