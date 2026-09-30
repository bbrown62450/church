import { describe, expect, it } from "vitest";

import type { Hymn } from "@/lib/api/types";
import { hymn, hymnId } from "@/test/fixtures";

import { filterHymns, PICKER_LIMIT } from "./filter";

const numbers = (r: { shown: Hymn[] }) => r.shown.map((h) => h.number);

describe("filterHymns (S Picker ranking)", () => {
  it("ranks an exact number first, then numbers that start with the digits, then titles containing them", () => {
    const items = [
      hymn({ number: 1403, title: "Lord, Speak to Me" }),
      hymn({ number: 40, title: "Hymn of Promise" }),
      hymn({ number: 403, title: "Come, Thou Almighty King" }),
      hymn({ number: 12, title: "Psalm 40: I Waited Patiently" }),
      hymn({ number: 4030, title: "Another" }),
    ];
    expect(numbers(filterHymns(items, "403", { excludeRecent: false }))).toEqual([403, 4030]);
    expect(numbers(filterHymns(items, "#403", { excludeRecent: false }))).toEqual([403, 4030]);
    expect(numbers(filterHymns(items, " 40 ", { excludeRecent: false }))).toEqual([40, 403, 4030, 12]);
  });

  it("matches titles by start, then word start, then anywhere, ignoring accents, case and punctuation", () => {
    const items = [
      hymn({ number: 1, title: "Now Thank We All Our God" }),
      hymn({ number: 2, title: "Thanks to God Whose Word Was Spoken" }),
      hymn({ number: 3, title: "Unthankful Hearts" }),
      hymn({ number: 4, title: "Jésus, Joy of Our Desiring" }),
      hymn({ number: 5, title: "Come, Thou Almighty King" }),
    ];
    expect(numbers(filterHymns(items, "THANK", { excludeRecent: false }))).toEqual([2, 1, 3]);
    expect(numbers(filterHymns(items, "jesus", { excludeRecent: false }))).toEqual([4]);
    expect(numbers(filterHymns(items, "come thou", { excludeRecent: false }))).toEqual([5]);
    expect(numbers(filterHymns(items, "", { excludeRecent: false }))).toEqual([1, 2, 3, 4, 5]); // hymnal order
  });

  it("shows at most 50 and counts every match", () => {
    const items = Array.from({ length: 120 }, (_, i) => hymn({ number: i + 1, title: `Grace ${i + 1}` }));
    const all = filterHymns(items, "grace", { excludeRecent: false });
    expect(PICKER_LIMIT).toBe(50);
    expect(all.shown).toHaveLength(50);
    expect(all.totalMatches).toBe(120);
    expect(all.shown[0].number).toBe(1);
  });

  it("blank titles never listed", () => {
    const items = [hymn({ number: 1, title: "" }), hymn({ number: 2, title: "   " }), hymn({ number: 3, title: "Amazing Grace" })];
    expect(numbers(filterHymns(items, "", { excludeRecent: false }))).toEqual([3]);
    expect(numbers(filterHymns(items, "1", { excludeRecent: false }))).toEqual([]);
  });

  it("same title stays distinct by id", () => {
    const items = [
      hymn({ id: hymnId(9001), number: 188, title: "Jesus Loves Me" }),
      hymn({ id: hymnId(9002), number: 189, title: "Jesus Loves Me" }),
    ];
    const r = filterHymns(items, "jesus loves", { excludeRecent: false });
    expect(r.shown.map((h) => [h.id, h.number])).toEqual([
      [hymnId(9001), 188],
      [hymnId(9002), 189],
    ]);
  });

  it("with excludeRecent, hides recently used hymns and counts them", () => {
    const items = [
      hymn({ number: 1, title: "Holy, Holy, Holy", recent_use_on: "2026-09-06" }),
      hymn({ number: 2, title: "Holy Spirit, Truth Divine" }),
      hymn({ number: 3, title: "Holy God, We Praise Your Name", recent_use_on: "2026-10-18" }),
    ];
    const hidden = filterHymns(items, "holy", { excludeRecent: true });
    expect(numbers(hidden)).toEqual([2]);
    expect(hidden).toMatchObject({ totalMatches: 1, hiddenRecent: 2 });
    expect(filterHymns(items, "holy", { excludeRecent: false })).toMatchObject({ totalMatches: 3, hiddenRecent: 0 });
  });
});
