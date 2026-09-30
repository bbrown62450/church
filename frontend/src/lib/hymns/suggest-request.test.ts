import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";
import { editOccasion, editScriptureLines, setPick, setTranslation } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { hymn, testDraft } from "@/test/fixtures";

import { pickFromHymn, setSlot } from "./picks";
import { buildSuggestionRequest } from "./suggest-request";

const LINES = "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46";

function passage(ref: string, text: string | null): Passage {
  return { reference: ref, status: text ? "ok" : "unavailable", sections: [{ reference: ref, status: text ? "ok" : "unavailable", text }] };
}

/** A cache holding the Matthew text in `translation` only. */
function cache(translation: string) {
  return (t: string, ref: string) => (t === translation && ref === "Matthew 21:33-46" ? passage(ref, "The parable of the tenants.") : undefined);
}

function draft(recipe: (d: DraftV1) => DraftV1 = (d) => d): DraftV1 {
  return recipe(editScriptureLines(editOccasion(testDraft(), "Nineteenth Sunday after Pentecost"), LINES));
}

describe("buildSuggestionRequest (S buildSuggestionRequest)", () => {
  it("sends the cached NT text only with a chosen NT reading, a translation other than ESV and text in the cache", () => {
    const picked = draft((d) => setPick(d, "nt", "Matthew 21:33-46"));
    expect(buildSuggestionRequest(picked, "GG2013", cache("web"), "web").nt_text).toBe("The parable of the tenants.");
    expect(buildSuggestionRequest(draft(), "GG2013", cache("web"), "web").nt_text).toBeUndefined(); // automatic NT
    expect(buildSuggestionRequest(picked, "GG2013", cache("web"), "esv")).not.toHaveProperty("nt_text"); // church ESV
    const esv = setTranslation(picked, "esv", "web");
    expect(buildSuggestionRequest(esv, "GG2013", cache("esv"), "web").nt_text).toBeUndefined(); // chosen ESV
    const kjv = setTranslation(picked, "kjv", "web");
    expect(buildSuggestionRequest(kjv, "GG2013", cache("kjv"), "web").nt_text).toBe("The parable of the tenants.");
    expect(buildSuggestionRequest(kjv, "GG2013", cache("web"), "web").nt_text).toBeUndefined(); // not cached in KJV
    const failed = (_t: string, ref: string) => passage(ref, null);
    expect(buildSuggestionRequest(picked, "GG2013", failed, "web").nt_text).toBeUndefined();
    const long = (_t: string, ref: string) => passage(ref, "y".repeat(25_000));
    expect(buildSuggestionRequest(picked, "GG2013", long, "web").nt_text).toHaveLength(20_000);
  });

  it("trims and caps the readings, the occasion and the NT reading; a blank NT reading is null", () => {
    const lines = ["  Mark 1:9-15  ", "", ...Array.from({ length: 24 }, (_, i) => `Psalm ${i + 1}`)].join("\n");
    const d = editOccasion(editScriptureLines(testDraft(), lines), `  ${"o".repeat(400)}  `);
    const body = buildSuggestionRequest(d, "GG2013", () => undefined, "web");
    expect(body.scriptures).toHaveLength(20);
    expect(body.scriptures?.[0]).toBe("Mark 1:9-15");
    expect(body.occasion).toBe("o".repeat(300));
    expect(body.selected_nt_ref).toBeNull();
    const spaced = { ...d, readings: { ...d.readings, selected_nt_ref: "   " } };
    expect(buildSuggestionRequest(spaced, "GG2013", () => undefined, "web").selected_nt_ref).toBeNull();
    const longRef = { ...d, readings: { ...d.readings, selected_nt_ref: ` ${"M".repeat(250)} ` } };
    expect(buildSuggestionRequest(longRef, "GG2013", () => undefined, "web").selected_nt_ref).toBe("M".repeat(200));
  });

  it("sends the selected hymnal, the date, the Exclude switch and the slots' ids as exclusion hints", () => {
    const king = hymn({ number: 403 });
    const d = setSlot({ ...draft(), hymns: { ...draft().hymns, hymnal: "XX1900", exclude_recent: false } }, "response", pickFromHymn(king));
    expect(buildSuggestionRequest(d, "GG2013", () => undefined, "web")).toEqual({
      service_date_iso: "2026-10-04",
      occasion: "Nineteenth Sunday after Pentecost",
      scriptures: ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"],
      selected_nt_ref: null,
      hymnal: "GG2013",
      exclude_recent: false,
      current_picks: { opening: null, response: king.id, closing: null },
    });
  });

  it("cuts the occasion by characters, never splitting an emoji, and sends only UUID-shaped ids as hints", () => {
    const d = editOccasion(testDraft(), "🎄".repeat(301));
    expect(buildSuggestionRequest(d, "GG2013", () => undefined, "web").occasion).toBe("🎄".repeat(300));
    const odd = setSlot(setSlot(testDraft(), "opening", { ...pickFromHymn(hymn()), hymn_id: "not-a-uuid" }), "closing", pickFromHymn(hymn()));
    expect(buildSuggestionRequest(odd, "GG2013", () => undefined, "web").current_picks).toEqual({
      opening: null,
      response: null,
      closing: hymn().id,
    });
  });
});
