import { describe, expect, it } from "vitest";

import { nextSunday, todayIn } from "@/lib/dates";
import { CHURCH_IDS, churchProfile, DRAFT_NOW, testDraft, USER_ID } from "@/test/fixtures";

import { churchZone, corruptDraftKey, draftKey, draftV1Schema, DRAFT_VERSION, freshDraft, SECTION_KEYS } from "./schema";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

describe("draft schema and freshDraft (F §4.6)", () => {
  it("a fresh draft is dated next Sunday with every field empty and the F §4.6 defaults", () => {
    const d = testDraft();
    expect(DRAFT_VERSION).toBe(2);
    expect(draftV1Schema.parse(d)).toEqual(d);
    expect(d).toMatchObject({
      version: 2,
      user_id: USER_ID,
      church_id: churchProfile().id,
      created_at: "2026-09-29T16:00:00.000Z",
      updated_at: "2026-09-29T16:00:00.000Z",
      last_step: "readings",
      save_key_fingerprint: null,
      editing: null,
      saved_fingerprint: null,
      readings: {
        date_iso: "2026-10-04",
        date_origin: "default",
        reading_set: null,
        fields_origin: "empty",
        occasion: "",
        scriptures: [],
        selected_ot_ref: "",
        selected_nt_ref: "",
        translation: null,
      },
      hymns: {
        hymnal: null,
        exclude_recent: true,
        slots: { opening: null, response: null, closing: null },
        alternatives: null,
      },
      liturgy: { sermon_title: "", include_communion: true, communion_origin: "default", custom_elements: [] },
    });
    expect(d.save_key).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(testDraft().save_key).not.toBe(d.save_key);
    for (const key of SECTION_KEYS) {
      expect(d.liturgy.cards[key], key).toEqual({
        enabled: key !== "prayers_of_the_people",
        text: key === "benediction" ? DEFAULT_BENEDICTION_FALLBACK : "", // the church default (slice 4b)
        origin: key === "benediction" ? "default" : "empty",
      });
    }
    const user = { id: USER_ID };
    const none = freshDraft({ church: churchProfile({ default_benediction: "" }), user, now: DRAFT_NOW });
    expect(none.liturgy.cards.benediction).toEqual({ enabled: true, text: "", origin: "default" });
    const older = freshDraft({ church: { id: CHURCH_IDS.grace, timezone: "America/New_York" }, user, now: DRAFT_NOW });
    expect(older.liturgy.cards.benediction.text).toBe(DEFAULT_BENEDICTION_FALLBACK); // an API without the field
  });

  it("uses the church's zone, strictly after today, and the browser's zone when the zone is not valid", () => {
    const now = new Date(Date.UTC(2026, 9, 4, 2, 30)); // Sat 22:30 in New York, Sun 02:30 UTC
    const user = { id: USER_ID };
    expect(freshDraft({ church: churchProfile(), user, now }).readings.date_iso).toBe("2026-10-04");
    expect(freshDraft({ church: churchProfile({ timezone: "UTC" }), user, now }).readings.date_iso).toBe(
      "2026-10-11",
    );
    const invalid = churchProfile({ timezone: "Eastern", timezone_valid: false });
    expect(freshDraft({ church: invalid, user, now }).readings.date_iso).toBe(nextSunday(todayIn(undefined, now)));
    expect(churchZone(churchProfile({ timezone_valid: false }))).toBeUndefined();
    const later = new Date(Date.UTC(2026, 9, 6, 16, 0)); // Tuesday October 6 → Sunday October 11
    expect(freshDraft({ church: churchProfile(), user, now: later }).liturgy.include_communion).toBe(false);
  });

  it("accepts an empty date and generous strings, and rejects impossible values", () => {
    const d = testDraft();
    expect(draftV1Schema.safeParse({ ...d, readings: { ...d.readings, date_iso: "" } }).success).toBe(true);
    const long = "x".repeat(20_000);
    expect(draftV1Schema.safeParse({ ...d, readings: { ...d.readings, occasion: long } }).success).toBe(true);
    for (const bad of [
      { ...d, readings: { ...d.readings, date_iso: "2026-02-30" } },
      { ...d, readings: { ...d.readings, occasion: `${long}x` } },
      { ...d, last_step: "summary" },
      { ...d, version: 3 },
      { ...d, editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00" } }, // version 2 needs editing.date_iso
      { ...d, editing: { service_id: "s1", saved_at: "2026-10-01T14:42:00+00:00", date_iso: "2026-02-30" } },
      { ...d, readings: { ...d.readings, fields_origin: "typed" } },
      { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: undefined } } },
      { ...d, updated_at: "not a time" },
      { ...d, created_at: "" },
    ]) {
      expect(draftV1Schema.safeParse(bad).success).toBe(false);
    }
  });

  it("keys drafts by user and church", () => {
    expect(draftKey("u1", "c1")).toBe("wsb:draft:u1:c1");
    expect(corruptDraftKey("u1", "c1")).toBe("wsb:draft-corrupt:u1:c1");
  });
});
