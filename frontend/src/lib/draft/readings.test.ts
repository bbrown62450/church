import { describe, expect, it } from "vitest";

import { churchProfile, lectionary, testDraft } from "@/test/fixtures";

import { onDateChanged } from "./date-effects";
import {
  applyReadingSet,
  clearReadings,
  commitScriptureLines,
  editOccasion,
  editScriptureLines,
  effectivePicks,
  effectiveTranslation,
  normalizePicks,
  readingsStale,
  selectedSetIndex,
  setDate,
  setPick,
  setTranslation,
  shouldAutoApply,
  showAvailableBanner,
} from "./readings";
import type { DraftV1 } from "./schema";

const ISAIAH = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];
const EASTER = ["Acts 10:34-43", "Psalm 118:1-2, 14-24", "Colossians 3:1-4", "John 20:1-18"];
const OCT_4 = "2026-10-04";
const OCT_11 = "2026-10-11";
/** October 11's own answer: one set, unlike October 4's lines. */
const OCT_11_LECT = lectionary(OCT_11, {
  reading_sets: [
    {
      name: "Twentieth Sunday after Pentecost",
      source: "merged",
      scriptures: ["Isaiah 25:1-9", "Psalm 23", "Philippians 4:1-9", "Matthew 22:1-14"],
    },
  ],
});

/** A draft filled from set 0 of October 4's lookup. */
function filled(): DraftV1 {
  return applyReadingSet(testDraft(), lectionary(OCT_4), 0);
}

function typed(lines: string[], date = OCT_4): DraftV1 {
  return editScriptureLines(editOccasion(setDate(testDraft(), date), "Harvest Sunday"), lines.join("\n"));
}

describe("readings transitions (S readings.ts)", () => {
  it("setDate sets the date and origin, keeps the fields, and follows communion only while it is a default", () => {
    const d = filled();
    const moved = setDate(d, OCT_11);
    expect(moved.readings).toMatchObject({ date_iso: OCT_11, date_origin: "user", occasion: d.readings.occasion });
    expect(moved.readings.scriptures).toEqual(ISAIAH);
    expect(moved.liturgy.include_communion).toBe(false); // October 11 is not a first Sunday
    expect(setDate(moved, "2026-11-01").liturgy.include_communion).toBe(true);
    expect(setDate(moved, "2026-11-03").liturgy.include_communion).toBe(false); // a Tuesday
    expect(setDate(d, OCT_4, "default")).toBe(d);

    const chosen: DraftV1 = { ...d, liturgy: { ...d.liturgy, include_communion: false, communion_origin: "user" } };
    expect(setDate(chosen, "2026-11-01").liturgy.include_communion).toBe(false);
    expect(onDateChanged(chosen, OCT_4)).toBe(chosen);
    expect(setDate(testDraft(), "").readings.date_iso).toBe("");
    // An impossible date is stored as "", so the draft always loads again (F §4.6).
    expect(setDate(testDraft(), "20261-10-04").readings.date_iso).toBe("");
  });

  it("applyReadingSet fills the fields for this date only and clears the picks", () => {
    const picked = setPick(setPick(testDraft(), "ot", "Psalm 80:7-15"), "nt", "Matthew 21:33-46");
    const d = applyReadingSet(picked, lectionary(OCT_4), 1);
    expect(d.readings).toMatchObject({
      occasion: "Resurrection of the Lord",
      scriptures: EASTER,
      fields_origin: "lectionary",
      reading_set: { date_iso: OCT_4, index: 1 },
      selected_ot_ref: "",
      selected_nt_ref: "",
    });
    expect(() => applyReadingSet(testDraft(), lectionary(OCT_11), 0)).toThrow();
    expect(() => applyReadingSet(testDraft(), lectionary(OCT_4), 5)).toThrow();
    const applied = applyReadingSet(testDraft(), lectionary(OCT_4), 0);
    expect(applyReadingSet(applied, lectionary(OCT_4), 0)).toBe(applied); // nothing changes
  });

  it("shouldAutoApply replaces empty fields and an old date's lectionary fields, never typed or archived ones", () => {
    const lect = lectionary(OCT_4);
    expect(shouldAutoApply(testDraft(), lect)).toBe(true);
    expect(shouldAutoApply(filled(), lect)).toBe(false); // already this date's set
    const oldDate = setDate(filled(), OCT_11);
    expect(shouldAutoApply(oldDate, lectionary(OCT_11))).toBe(true);
    expect(readingsStale(oldDate)).toBe(true);
    expect(readingsStale(filled())).toBe(false);
    expect(shouldAutoApply(typed(ISAIAH), lect)).toBe(false);
    const archived = testDraft((d) => ({ ...d, readings: { ...d.readings, fields_origin: "archive" } }));
    expect(shouldAutoApply(archived, lect)).toBe(false);
    expect(shouldAutoApply(testDraft(), lectionary(OCT_11))).toBe(false); // a late answer for another date
    expect(shouldAutoApply(testDraft(), lectionary(OCT_4, { status: "no_readings", reading_sets: [], default_index: null }))).toBe(false);
  });

  it("edits mark the fields as the user's and never touch the picks; commit and normalize clear only stale picks", () => {
    const picked = setPick(filled(), "ot", "Psalm 80:7-15");
    const edited = editScriptureLines(picked, "Isaiah 5:1-7\n\nPhilippians 3:4b-14");
    expect(edited.readings).toMatchObject({
      scriptures: ["Isaiah 5:1-7", "", "Philippians 3:4b-14"],
      fields_origin: "user",
      selected_ot_ref: "Psalm 80:7-15",
    });
    expect(editScriptureLines(edited, "Isaiah 5:1-7\n\nPhilippians 3:4b-14")).toBe(edited);
    expect(editOccasion(filled(), "Harvest").readings).toMatchObject({ occasion: "Harvest", fields_origin: "user" });

    const committed = commitScriptureLines(edited);
    expect(committed.readings.selected_ot_ref).toBe("");
    expect(commitScriptureLines(picked)).toBe(picked);
    expect(normalizePicks(picked)).toBe(picked);
    const wrongSide = setPick(filled(), "nt", "Psalm 80:7-15");
    expect(normalizePicks(wrongSide).readings.selected_nt_ref).toBe("");
  });

  it("clearReadings empties the fields; setPick and setTranslation store only changes", () => {
    const cleared = clearReadings(setPick(filled(), "nt", "Matthew 21:33-46"));
    expect(cleared.readings).toMatchObject({
      occasion: "",
      scriptures: [],
      fields_origin: "empty",
      reading_set: null,
      selected_ot_ref: "",
      selected_nt_ref: "",
    });
    expect(clearReadings(cleared)).toBe(cleared); // nothing changes
    const d = filled();
    expect(setPick(d, "ot", "")).toBe(d);
    expect(setTranslation(d, "web", "web")).toBe(d);
    const kjv = setTranslation(d, "kjv", "web");
    expect(kjv.readings.translation).toBe("kjv");
    expect(setTranslation(kjv, "web", "web").readings.translation).toBeNull();
  });
});

describe("readings selectors (S readings.ts)", () => {
  it("effectivePicks never gives a Psalm as the NT, and follows the other side's pick", () => {
    expect(effectivePicks(filled())).toEqual({
      ot: "Isaiah 5:1-7",
      nt: "Philippians 3:4b-14",
      otAuto: true,
      ntAuto: true,
    });
    const easter = applyReadingSet(testDraft(), lectionary(OCT_4), 1);
    expect(effectivePicks(setPick(easter, "ot", "Psalm 118:1-2, 14-24"))).toEqual({
      ot: "Psalm 118:1-2, 14-24",
      nt: "Acts 10:34-43",
      otAuto: false,
      ntAuto: true,
    });
    // A stale stored pick is automatic even before normalizePicks runs.
    const stale = editScriptureLines(setPick(filled(), "ot", "Psalm 80:7-15"), "Isaiah 5:1-7\nPhilippians 3:4b-14");
    expect(effectivePicks(stale)).toMatchObject({ ot: "Isaiah 5:1-7", otAuto: true });
  });

  it("showAvailableBanner: only for typed fields not from this date's set, or archived fields after a date change", () => {
    const lect = OCT_11_LECT;
    // user, after a date change → shown
    const afterDateChange = setDate(editOccasion(filled(), "Harvest"), OCT_11);
    expect(showAvailableBanner(afterDateChange, lect)).toBe(true);
    // user, after deleting the Psalm line of this date's set → not shown
    const psalmDeleted = editScriptureLines(filled(), "Isaiah 5:1-7\nPhilippians 3:4b-14\nMatthew 21:33-46");
    expect(showAvailableBanner(psalmDeleted, lectionary(OCT_4))).toBe(false);
    // user typed with no reading set, sets for this date → shown
    expect(showAvailableBanner(typed(["John 3:16"]), lectionary(OCT_4))).toBe(true);
    // typed lines equal to a set → not shown
    expect(showAvailableBanner(typed(ISAIAH), lectionary(OCT_4))).toBe(false);
    // archive on its own date → not shown; after a date change → shown
    const archived = testDraft((d) => ({
      ...d,
      readings: { ...d.readings, date_origin: "archive", fields_origin: "archive", scriptures: ["John 3:16"] },
    }));
    expect(showAvailableBanner(archived, lectionary(OCT_4))).toBe(false);
    expect(showAvailableBanner(setDate(archived, OCT_11), lect)).toBe(true);
    // empty and lectionary → never; no lookup or another date's → never
    expect(showAvailableBanner(testDraft(), lectionary(OCT_4))).toBe(false);
    expect(showAvailableBanner(setDate(filled(), OCT_11), lect)).toBe(false);
    expect(showAvailableBanner(afterDateChange, undefined)).toBe(false);
    expect(showAvailableBanner(afterDateChange, lectionary(OCT_4))).toBe(false);
  });

  it("selectedSetIndex matches the scriptures first, then the stored index for this date", () => {
    const lect = lectionary(OCT_4);
    expect(selectedSetIndex(filled(), lect)).toBe(0);
    expect(selectedSetIndex(typed(EASTER), lect)).toBe(1);
    expect(selectedSetIndex(typed(["Luke 2:1-14, (15-20)"]), lect)).toBeNull();
    const editedSet1 = editScriptureLines(applyReadingSet(testDraft(), lect, 1), "Acts 10:34-43");
    expect(selectedSetIndex(editedSet1, lect)).toBe(1);
    expect(selectedSetIndex(filled(), lectionary(OCT_11))).toBeNull();
  });

  it("effectiveTranslation honours a stored override only when the loaded list offers it", () => {
    const church = churchProfile({ effective_translation: "web" });
    const list = { default: "web", esv_available: false, items: [{ id: "web", label: "WEB" }, { id: "kjv", label: "KJV" }] };
    const kjv = setTranslation(filled(), "kjv", "web");
    const esv = setTranslation(filled(), "esv", "web");
    expect(effectiveTranslation(kjv, church, list)).toBe("kjv");
    expect(effectiveTranslation(esv, church, list)).toBe("web");
    expect(effectiveTranslation(kjv, church, undefined)).toBe("web");
    expect(effectiveTranslation(filled(), churchProfile({ effective_translation: "kjv" }), list)).toBe("kjv");
  });
});
