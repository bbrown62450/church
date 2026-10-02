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
import { hymnId, testDraft, translations } from "@/test/fixtures";

import { editCardText } from "./cards";
import {
  buildGenerateRequest,
  buildReviewRequest,
  buildReviseRequest,
  MAX_SERMON_TEXT,
  reviewTargets,
  sermonSource,
  sermonText,
} from "./request";

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
  const offered = translations();
  const church = (effective_translation: string) => ({ effective_translation });

  it("is the effective NT reading, never a Psalm, in the draft's translation with WEB for ESV", () => {
    expect(sermonSource(testDraft(), church("web"), offered)).toBeNull(); // no readings
    expect(sermonSource(withReadings(["Psalm 23"]), church("web"), offered)).toBeNull(); // a Psalm is never the NT reading
    const d = withReadings(OCT_4);
    expect(sermonSource(d, church("web"), offered)).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // the automatic pick
    expect(sermonSource(setPick(d, "nt", "Matthew 21:33-46"), church("kjv"), offered)).toEqual({
      ref: "Matthew 21:33-46",
      translation: "kjv",
    });
    expect(sermonSource(d, church("esv"), offered)).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // Crossway's terms
    expect(sermonSource(setTranslation(d, "esv", "web"), church("web"), offered)?.translation).toBe("web");
    expect(sermonSource(setTranslation(d, "kjv", "web"), church("web"), offered)?.translation).toBe("kjv");
  });

  it("uses the translation step 1 shows: the church's when the stored one is not offered or the list has not loaded", () => {
    const kjv = setTranslation(withReadings(OCT_4), "kjv", "web");
    const noKjv = translations({ items: [{ id: "web", label: "World English Bible (WEB)" }] });
    expect(sermonSource(kjv, church("web"), noKjv)?.translation).toBe("web");
    expect(sermonSource(kjv, church("web"), undefined)?.translation).toBe("web");
    // ESV dropped from the server (no key): the church's own translation, and never ESV text.
    const esv = setTranslation(withReadings(OCT_4), "esv", "kjv");
    expect(sermonSource(esv, church("kjv"), translations({ esv_available: false, items: offered.items.slice(0, 2) }))?.translation).toBe("kjv");
  });
});

describe("buildReviewRequest and buildReviseRequest (the service reviewer, R API)", () => {
  function withCard(d: DraftV1, key: keyof DraftV1["liturgy"]["cards"], patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>): DraftV1 {
    return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
  }

  it("sends every switched-on card with text, in section order, with its origin, and generation's context", () => {
    let d = withReadings([" Isaiah 5:1-7 ", "", "Matthew 21:33-46"], ` ${"o".repeat(305)} `);
    d = withCard(d, "benediction", { text: "Go in peace.", origin: "default" });
    d = editCardText(d, "call_to_worship", "Leader: Come!");
    d = withCard(d, "opening_prayer", { text: "   ", origin: "empty" });                       // blank: not sent
    d = withCard(d, "prayer_of_confession", { text: "Merciful God", origin: "archive", enabled: false }); // off: not sent
    d = withCard(d, "prayers_of_the_people", { text: "x".repeat(20_005), origin: "ai", enabled: true });
    d = withCard(d, "assurance", { text: "Leader: Friends,", origin: "empty" });             // defensive: never "empty"
    const keys = reviewTargets(d);
    expect(keys).toEqual(["call_to_worship", "assurance", "prayers_of_the_people"]); // the default Benediction: not reviewed
    const sermon = { ref: "Matthew 21:33-46", text: "Listen to another parable." };
    const body = buildReviewRequest(d, keys, sermon);
    expect(body).toEqual({
      occasion: "o".repeat(300),
      scriptures: ["Isaiah 5:1-7", "Matthew 21:33-46"],
      cards: [
        { section: "call_to_worship", origin: "typed", text: "Leader: Come!" },
        { section: "assurance", origin: "typed", text: "Leader: Friends," },
        { section: "prayers_of_the_people", origin: "ai", text: "x".repeat(20_000) },
      ],
      sermon_text: sermon,
    });
    const generate = buildGenerateRequest(d, "opening_prayer", sermon);
    expect([body.occasion, body.scriptures, body.sermon_text]).toEqual([generate.occasion, generate.scriptures, generate.sermon_text]);
    expect(buildReviewRequest(d, keys, null)).not.toHaveProperty("sermon_text");
  });

  it("leaves out a Benediction following the church default; a typed, AI or saved one is reviewed (owner, 2026-10-02)", () => {
    const d = withCard(withReadings(OCT_4), "benediction", { text: "Go in peace.", origin: "default", enabled: true });
    expect(reviewTargets(d)).toEqual([]); // the only card: nothing to review
    for (const origin of ["typed", "ai", "archive"] as const) {
      const other = withCard(d, "benediction", { origin });
      expect(reviewTargets(other)).toEqual(["benediction"]);
      expect(buildReviewRequest(other, reviewTargets(other), null).cards).toEqual([{ section: "benediction", origin, text: "Go in peace." }]);
    }
  });

  it("sends one card's text and its remaining notes to revise, with the same context", () => {
    const d = withCard(withReadings(OCT_4), "opening_prayer", { text: "Gracious God, as we journey, hear us.", origin: "ai" });
    const notes = ['Stock phrase "as we journey". Say it more naturally.', "Long.", "Third.", "Fourth."];
    expect(buildReviseRequest(d, "opening_prayer", notes, null)).toEqual({
      section: "opening_prayer",
      text: "Gracious God, as we journey, hear us.",
      notes: notes.slice(0, 3),
      occasion: "Nineteenth Sunday after Pentecost",
      scriptures: OCT_4,
    });
    const sermon = { ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" };
    expect(buildReviseRequest(d, "opening_prayer", notes, sermon).sermon_text).toEqual(sermon);
  });
});
