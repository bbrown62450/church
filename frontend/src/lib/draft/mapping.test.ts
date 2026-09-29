import { describe, expect, it } from "vitest";

import { lectionary, testDraft } from "@/test/fixtures";

import { draftToServicePayload } from "./mapping";
import { applyReadingSet, editScriptureLines, setPick } from "./readings";
import type { DraftV1 } from "./schema";

describe("draftToServicePayload (provisional; 5a replaces it)", () => {
  it("maps a fresh draft to the ServiceDraft shape", () => {
    expect(draftToServicePayload(testDraft())).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "",
      scriptures: [],
      hymns: { opening: null, response: null, closing: null },
      liturgy: {},
      sermon_title: "",
      selected_ot_ref: "",
      selected_nt_ref: "",
      include_communion: true,
      custom_elements: [],
      hymnal: null,
    });
  });

  it("trims and drops blank lines, keeps enabled non-empty cards, slot-keyed hymns and elements without ids", () => {
    const d: DraftV1 = testDraft((base) => {
      const lines = editScriptureLines(base, "  Isaiah 5:1-7 \n\n   \nPsalm 80:7-15");
      return {
        ...lines,
        hymns: {
          ...lines.hymns,
          hymnal: "GG2013",
          slots: { ...lines.hymns.slots, response: { hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" } },
        },
        liturgy: {
          ...lines.liturgy,
          cards: {
            ...lines.liturgy.cards,
            call_to_worship: { enabled: true, text: "Come, let us worship.", origin: "typed" },
            opening_prayer: { enabled: false, text: "Hidden", origin: "typed" },
            assurance: { enabled: true, text: "   ", origin: "typed" },
          },
          custom_elements: [{ id: "x1", label: "Anthem", text: "Choir", insert_after: "assurance" }],
        },
      };
    });
    const payload = draftToServicePayload(d);
    expect(payload.scriptures).toEqual(["Isaiah 5:1-7", "Psalm 80:7-15"]);
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship." });
    expect(payload.hymns.response).toEqual({ hymn_id: "h1", title: "Amazing Grace", number: 649, hymnal: "GG2013" });
    expect(payload.hymns.opening).toBeNull();
    expect(payload.hymnal).toBe("GG2013");
    expect(payload.custom_elements).toEqual([{ label: "Anthem", text: "Choir", insert_after: "assurance" }]);
  });

  it("sends only picks that are still options, whatever the stored draft holds", () => {
    const filled = applyReadingSet(testDraft(), lectionary("2026-10-04"), 0);
    const picked = setPick(setPick(filled, "ot", "Psalm 80:7-15"), "nt", "Matthew 21:33-46");
    expect(draftToServicePayload(picked)).toMatchObject({
      selected_ot_ref: "Psalm 80:7-15",
      selected_nt_ref: "Matthew 21:33-46",
    });
    // The Psalm line deleted while the textarea had focus: the stored pick is stale.
    const stale = editScriptureLines(picked, "Isaiah 5:1-7\nPhilippians 3:4b-14\nMatthew 21:33-46");
    expect(stale.readings.selected_ot_ref).toBe("Psalm 80:7-15");
    expect(draftToServicePayload(stale)).toMatchObject({ selected_ot_ref: "", selected_nt_ref: "Matthew 21:33-46" });
  });
});
