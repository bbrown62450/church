/**
 * The `POST /liturgy/generate` body (slice 4 spec, Frontend `request.ts`,
 * "Sermon text"; Testing `request.test.ts`; port-ledger target for
 * streamlit_tests/test_app_helpers.py::test_sermon_text_*): one section, no
 * overrides, the ServiceDraft limits, slot-keyed hymns, and the sermon text
 * from the effective NT reading, never from an ESV passage.
 */
import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";
import { editScriptureLines, setPick, setTranslation } from "@/lib/draft/readings";
import type { DraftV1, HymnPick } from "@/lib/draft/schema";
import { hymnId, testDraft } from "@/test/fixtures";

import { buildGenerateRequest, MAX_SERMON_TEXT, sermonSource, sermonText } from "./request";

const OCT_4 = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

function withReadings(lines: string[], occasion = "Nineteenth Sunday after Pentecost"): DraftV1 {
  const d = editScriptureLines(testDraft(), lines.join("\n"));
  return { ...d, readings: { ...d.readings, occasion } };
}

function passage(ref: string, texts: (string | null)[]): Passage {
  return {
    reference: ref,
    status: texts.every((t) => t !== null) ? "ok" : "unavailable",
    sections: texts.map((text, i) => ({ reference: `${ref} (${i + 1})`, status: text === null ? "unavailable" : "ok", text })),
  };
}

describe("buildGenerateRequest (S request.ts)", () => {
  it("sends one section, no overrides, the readings within the limits and the three slots as HymnRefs", () => {
    const pick = (n: number, patch: Partial<HymnPick> = {}): HymnPick => ({
      hymn_id: hymnId(n),
      title: `Hymn ${n}`,
      number: n,
      hymnal: "GG2013",
      ...patch,
    });
    let d = withReadings(["  Isaiah 5:1-7  ", "", ...Array.from({ length: 21 }, (_, i) => `Psalm ${i + 1}`)], ` ${"o".repeat(305)} `);
    d = editScriptureLines(d, [...d.readings.scriptures.slice(0, 2), "x".repeat(205), ...d.readings.scriptures.slice(2)].join("\n"));
    d = {
      ...d,
      hymns: {
        ...d.hymns,
        slots: { opening: pick(403, { title: "t".repeat(301) }), response: null, closing: pick(0, { hymn_id: null, number: null, hymnal: null }) },
      },
    };
    const body = buildGenerateRequest(d, "call_to_worship", null);
    expect(body.sections).toEqual(["call_to_worship"]);
    expect(body).not.toHaveProperty("overrides");
    expect(body).not.toHaveProperty("sermon_text");
    expect(body.occasion).toBe("o".repeat(300));
    expect(body.scriptures).toHaveLength(20);
    expect(body.scriptures?.slice(0, 3)).toEqual(["Isaiah 5:1-7", "x".repeat(200), "Psalm 1"]);
    expect(body.hymns).toEqual({
      opening: { hymn_id: hymnId(403), title: "t".repeat(300), number: 403, hymnal: "GG2013" },
      response: null,
      closing: { hymn_id: null, title: "Hymn 0", number: null, hymnal: null },
    });
    // An id the API would reject (not a UUID) goes as a snapshot, with its own title.
    const odd = { ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, response: pick(12, { hymn_id: "h12" }) } } };
    expect(buildGenerateRequest(odd, "benediction", null).hymns?.response).toEqual({
      hymn_id: null,
      title: "Hymn 12",
      number: 12,
      hymnal: "GG2013",
    });
  });

  it("adds the sermon text when there is one, cut to 20 000 characters", () => {
    const d = withReadings(OCT_4);
    const body = buildGenerateRequest(d, "opening_prayer", { ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" });
    expect(body.sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" });
    expect(sermonText("Philippians 3:4b-14", passage("Philippians 3:4b-14", ["a".repeat(20_005)]))?.text).toHaveLength(MAX_SERMON_TEXT);
    expect(sermonText("Mark 4:35-41", passage("Mark 4:35-41", ["Waves.", null, "Wind."]))).toEqual({
      ref: "Mark 4:35-41",
      text: "Waves.\n\nWind.",
    });
    expect(sermonText("Mark 4:35-41", passage("Mark 4:35-41", [null]))).toBeNull();
    expect(sermonText("Mark 4:35-41", undefined)).toBeNull();
  });
});

describe("sermonSource (S Sermon text)", () => {
  it("is the effective NT reading, never a Psalm, in the draft's translation with WEB for ESV", () => {
    expect(sermonSource(testDraft(), "web")).toBeNull(); // no readings
    expect(sermonSource(withReadings(["Psalm 23"]), "web")).toBeNull(); // a Psalm is never the NT reading
    const d = withReadings(OCT_4);
    expect(sermonSource(d, "web")).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // the automatic pick
    expect(sermonSource(setPick(d, "nt", "Matthew 21:33-46"), "kjv")).toEqual({ ref: "Matthew 21:33-46", translation: "kjv" });
    expect(sermonSource(d, "esv")).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // Crossway's terms
    expect(sermonSource(setTranslation(d, "esv", "web"), "web")?.translation).toBe("web");
    expect(sermonSource(setTranslation(d, "kjv", "web"), "web")?.translation).toBe("kjv");
  });
});
