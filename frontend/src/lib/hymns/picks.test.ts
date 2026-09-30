import { describe, expect, it } from "vitest";

import type { Hymn, HymnSuggestions } from "@/lib/api/types";
import type { DraftV1, HymnPick } from "@/lib/draft/schema";
import { hymn, hymnals, suggested, testDraft } from "@/test/fixtures";

import { selectHymnal } from "./hymnal";
import {
  applySuggestions,
  clearSlot,
  duplicateSlots,
  pickFromHymn,
  reconcilePick,
  setExcludeRecent,
  setHymnal,
  setSlot,
  swapAlternative,
} from "./picks";

const HOLY = hymn({ number: 1, title: "Holy, Holy, Holy" });
const PRAISE = hymn({ number: 35, title: "Praise, My Soul, the King of Heaven" });
const GRACE = hymn({ number: 649, title: "Amazing Grace" });
const KING = hymn({ number: 403 });
const pick = (h: Hymn): HymnPick => pickFromHymn(h);

function answer(slots: Partial<HymnSuggestions["slots"]>): HymnSuggestions {
  return {
    hymnal: "GG2013",
    nt_ref: null,
    nt_text_used: false,
    excluded_recent_count: 0,
    slots: { opening: [], response: [], closing: [], ...slots },
  };
}

function withSlots(slots: Partial<DraftV1["hymns"]["slots"]>): DraftV1["hymns"] {
  const d = testDraft();
  return { ...d.hymns, slots: { ...d.hymns.slots, ...slots } };
}

describe("draft transitions (S Pure-function contracts)", () => {
  it("pickFromHymn keeps the id, title, number and hymnal; each setter returns the same draft when nothing changes", () => {
    expect(pickFromHymn(KING)).toEqual({
      hymn_id: KING.id,
      title: "Come, Thou Almighty King",
      number: 403,
      hymnal: "GG2013",
    });
    const d = testDraft();
    const opened = setSlot(d, "opening", pick(KING));
    expect(opened.hymns.slots.opening).toEqual(pick(KING));
    expect(setSlot(opened, "opening", pick(KING))).toBe(opened);
    expect(clearSlot(opened, "opening").hymns.slots.opening).toBeNull();
    expect(clearSlot(d, "closing")).toBe(d);
    // The church's effective hymnal is stored as null, so "New service" never counts it (clarification 2).
    expect(setHymnal(d, "GG2013", "GG2013")).toBe(d);
    const ph = setHymnal(d, "PH1990", "GG2013");
    expect(ph.hymns.hymnal).toBe("PH1990");
    expect(setHymnal(ph, "GG2013", "GG2013").hymns.hymnal).toBeNull();
    expect(setExcludeRecent(d, true)).toBe(d);
    expect(setExcludeRecent(d, false).hymns.exclude_recent).toBe(false);
    expect(setHymnal(opened, "PH1990", "GG2013").hymns.slots.opening).toEqual(pick(KING)); // picks are kept
  });
});

describe("applySuggestions (S AI suggestion flow; owner decision 3, F D16)", () => {
  it("fills only empty slots, gives filled slots ideas without their own pick, caps ideas at 4 and dates them", () => {
    const five = [HOLY, PRAISE, GRACE, KING, hymn({ number: 7 })].map((h) => suggested(h));
    const hymns = withSlots({ response: pick(GRACE) });
    const next = applySuggestions(hymns, answer({ opening: five, response: five, closing: [] }), "2026-10-04");
    expect(next.slots.opening).toEqual(pick(HOLY));
    expect(next.slots.response).toEqual(pick(GRACE)); // the member's pick stays
    expect(next.slots.closing).toBeNull(); // nothing returned for it
    expect(next.alternatives).toEqual({
      for_date_iso: "2026-10-04",
      by_slot: {
        opening: [PRAISE, GRACE, KING, hymn({ number: 7 })].map(pick),
        response: [HOLY, PRAISE, KING, hymn({ number: 7 })].map(pick),
        closing: [],
      },
    });
    expect(next.exclude_recent).toBe(hymns.exclude_recent);
  });

  it("gives at least 2 ideas from a 3-hymn answer: a pick plus 2 for an empty slot, 3 for a filled one", () => {
    const three = [HOLY, PRAISE, GRACE].map((h) => suggested(h));
    const next = applySuggestions(withSlots({ closing: pick(KING) }), answer({ opening: three, closing: three }), "2026-10-04");
    expect(next.slots.opening).toEqual(pick(HOLY));
    expect(next.alternatives?.by_slot.opening).toHaveLength(2);
    expect(next.alternatives?.by_slot.closing).toEqual([HOLY, PRAISE, GRACE].map(pick));
  });

  it("an empty slot takes the first hymn no other slot holds, so a slot emptied during the request repeats none", () => {
    // Opening was emptied while the request ran, so the server did not keep its list apart;
    // Response holds Amazing Grace.
    const hymns = withSlots({ response: pick(GRACE) });
    const next = applySuggestions(
      hymns,
      answer({ opening: [GRACE, HOLY, PRAISE].map((h) => suggested(h)), closing: [HOLY, KING].map((h) => suggested(h)) }),
      "2026-10-04",
    );
    expect(next.slots).toEqual({ opening: pick(HOLY), response: pick(GRACE), closing: pick(KING) });
    expect(next.alternatives?.by_slot.opening).toEqual([GRACE, PRAISE].map(pick));
    expect(next.alternatives?.by_slot.closing).toEqual([HOLY].map(pick));
    // Every hymn returned is held elsewhere: the slot stays empty and they are its ideas.
    const held = applySuggestions(hymns, answer({ opening: [suggested(GRACE)] }), "2026-10-04");
    expect(held.slots.opening).toBeNull();
    expect(held.alternatives?.by_slot.opening).toEqual([pick(GRACE)]);
  });
});

describe("swapAlternative (S Other ideas)", () => {
  it("swaps an idea into the slot and the previous pick into its place, so a second tap swaps back", () => {
    const base = applySuggestions(
      withSlots({ opening: pick(KING) }),
      answer({ opening: [HOLY, PRAISE, GRACE].map((h) => suggested(h)) }),
      "2026-10-04",
    );
    const once = swapAlternative(base, "opening", HOLY.id);
    expect(once.slots.opening).toEqual(pick(HOLY));
    expect(once.alternatives?.by_slot.opening).toEqual([KING, PRAISE, GRACE].map(pick));
    const twice = swapAlternative(once, "opening", KING.id);
    expect(twice).toEqual(base);
    // Into an empty slot the idea just moves up; an unknown id or no ideas changes nothing.
    const empty = { ...base, slots: { ...base.slots, opening: null } };
    const moved = swapAlternative(empty, "opening", PRAISE.id);
    expect(moved.slots.opening).toEqual(pick(PRAISE));
    expect(moved.alternatives?.by_slot.opening).toEqual([HOLY, GRACE].map(pick));
    expect(swapAlternative(base, "opening", "nope")).toBe(base);
    const none = withSlots({});
    expect(swapAlternative(none, "opening", HOLY.id)).toBe(none);
  });
});

describe("reconcilePick and duplicateSlots (S Live data, notices)", () => {
  it("finds the live hymn, waits for a list still loading, and reports a missing one", () => {
    const lists = new Map<string, readonly Hymn[] | undefined>([
      ["GG2013", [KING, HOLY]],
      ["PH1990", undefined],
    ]);
    const renamed = { ...pick(KING), title: "Come, Thou Almighty King (old title)" };
    expect(reconcilePick(renamed, lists, "GG2013")).toEqual({ status: "ok", live: KING });
    expect(reconcilePick({ ...pick(KING), hymnal: "PH1990" }, lists, "GG2013")).toEqual({ status: "loading" });
    expect(reconcilePick({ ...pick(KING), hymn_id: null }, lists, "GG2013")).toEqual({ status: "missing" });
    expect(reconcilePick(pick(GRACE), lists, "GG2013")).toEqual({ status: "missing" });
    // A pick with no hymnal (an archived one, 5a) is looked up in the selected hymnal.
    expect(reconcilePick({ ...pick(HOLY), hymnal: null }, lists, "GG2013")).toEqual({ status: "ok", live: HOLY });
    expect(reconcilePick({ ...pick(HOLY), hymnal: "XX" }, lists, "GG2013")).toEqual({ status: "loading" });
  });

  it("names the other slots that hold the same hymn", () => {
    expect(duplicateSlots({ opening: pick(KING), response: pick(HOLY), closing: pick(KING) })).toEqual({
      opening: ["closing"],
      response: [],
      closing: ["opening"],
    });
    const archived = { ...pick(KING), hymn_id: null };
    expect(duplicateSlots({ opening: archived, response: archived, closing: null })).toEqual({
      opening: [],
      response: [],
      closing: [],
    });
  });
});

describe("selectHymnal (S Toolbar)", () => {
  it("uses the stored code when it is listed, the effective hymnal for null, and marks a vanished code stale", () => {
    const two = hymnals({
      items: [
        { code: "GG2013", hymn_count: 853, scripture_ref_count: 795 },
        { code: "PH1990", hymn_count: 605, scripture_ref_count: 0 },
      ],
    });
    expect(selectHymnal("PH1990", two)).toEqual({ code: "PH1990", stale: false });
    expect(selectHymnal(null, two)).toEqual({ code: "GG2013", stale: false });
    expect(selectHymnal("XX1900", two)).toEqual({ code: "GG2013", stale: true });
    expect(selectHymnal(null, hymnals({ items: [], effective_hymnal: null }))).toEqual({ code: null, stale: false });
  });
});
