/**
 * The `POST /documents` body (slice 5a spec, `useDownloadDocument`; Testing
 * `mapping.test.ts`'s payload rules as the documents use them).
 */
import { describe, expect, it } from "vitest";

import { editScriptureLines, setPick } from "@/lib/draft/readings";
import { pickFromHymn, setSlot } from "@/lib/hymns/picks";
import { addCustomElement, editCardText, setCardEnabled, setCommunion, setSermonTitle } from "@/lib/liturgy/cards";
import { gg2013, testDraft } from "@/test/fixtures";

import { documentRequest, wordSafe } from "./documents";

const OCT_4 = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

describe("documentRequest (slice 5a)", () => {
  it("sends the service as the Word file prints it: slot hymns, enabled cards with text, picks, communion, custom elements", () => {
    const [holy] = gg2013();
    let d = editScriptureLines(testDraft(), ["  Isaiah 5:1-7 ", "", ...OCT_4.slice(1)].join("\n"));
    d = { ...d, readings: { ...d.readings, occasion: "  World Communion Sunday " } };
    d = setPick(d, "nt", "Matthew 21:33-46");
    d = setSlot(d, "response", pickFromHymn(holy));
    d = editCardText(d, "call_to_worship", "Leader: Come. People: We come.");
    d = editCardText(setCardEnabled(d, "opening_prayer", false), "opening_prayer", "Switched off, so not sent.");
    d = editCardText(d, "prayer_of_confession", "   ");
    d = setSermonTitle(setCommunion(d, true), "  Living Water ");
    d = addCustomElement(d, { label: " Anthem ", text: "Choir", insert_after: "sermon" }, "a");
    d = addCustomElement(d, { label: "  ", text: "No label, never printed.", insert_after: "end" }, "b");
    d = addCustomElement(d, { label: "Old place", text: "", insert_after: "bogus" }, "c");

    expect(documentRequest(d, "pastor")).toEqual({
      variant: "pastor",
      service: {
        service_date_iso: "2026-10-04",
        occasion: "World Communion Sunday",
        scriptures: OCT_4,
        hymns: {
          opening: null,
          response: { hymn_id: holy.id, title: holy.title, number: holy.number, hymnal: holy.hymnal },
          closing: null,
        },
        hymnal: null,
        liturgy: { call_to_worship: "Leader: Come. People: We come.", benediction: "Halverson" },
        sermon_title: "Living Water",
        selected_ot_ref: "",
        selected_nt_ref: "Matthew 21:33-46",
        include_communion: true,
        custom_elements: [
          { label: "Anthem", text: "Choir", insert_after: "sermon" },
          { label: "Old place", text: "", insert_after: "end" },
        ],
      },
    });
    expect(documentRequest(d, "bulletin").variant).toBe("bulletin");
  });

  it("stays within the ServiceDraft limits, so a draft never meets a 422", () => {
    let d = editScriptureLines(testDraft(), Array.from({ length: 22 }, (_, i) => `Psalm ${i + 1}`).join("\n"));
    d = { ...d, readings: { ...d.readings, occasion: "o".repeat(320), selected_nt_ref: "Mark 1" } };
    d = setSlot(d, "opening", { hymn_id: "not-a-uuid", title: "t".repeat(310), number: 100_001, hymnal: "h".repeat(25) });
    d = { ...d, hymns: { ...d.hymns, hymnal: "x".repeat(30) } };
    d = editCardText(d, "call_to_worship", "c".repeat(20_005));
    d = setSermonTitle(d, "s".repeat(305));
    for (let i = 0; i < 32; i += 1) d = addCustomElement(d, { label: "L".repeat(205), text: "T".repeat(10_005), insert_after: "end" }, `e${i}`);

    const { service } = documentRequest(d, "bulletin");
    expect(service.occasion).toHaveLength(300);
    expect(service.scriptures).toHaveLength(20);
    expect(service.selected_nt_ref).toBe(""); // not one of the lines
    expect(service.hymns?.opening).toEqual({ hymn_id: null, title: "t".repeat(300), number: null, hymnal: "h".repeat(20) });
    expect(service.hymnal).toHaveLength(20);
    expect(service.liturgy?.call_to_worship).toHaveLength(20_000);
    expect(service.sermon_title).toHaveLength(300);
    expect(service.custom_elements).toHaveLength(30);
    expect(service.custom_elements?.[0]).toEqual({ label: "L".repeat(200), text: "T".repeat(10_000), insert_after: "end" });

    // A picked reading over 200 characters goes cut, as its line does, so the pick still names that line.
    const long = `Matthew 21:33-46 ${"x".repeat(190)}`;
    const picked = documentRequest(setPick(editScriptureLines(testDraft(), `Isaiah 5:1-7\n${long}`), "nt", long), "bulletin").service;
    expect(picked.scriptures).toEqual(["Isaiah 5:1-7", long.slice(0, 200)]);
    expect(picked.selected_nt_ref).toBe(long.slice(0, 200));
  });

  it("leaves out a label of only characters the server strips, so it never meets the blank-label 422 (build review fix 8)", () => {
    let d = testDraft();
    d = addCustomElement(d, { label: "\u0000", text: "NUL only", insert_after: "end" }, "a");
    d = addCustomElement(d, { label: " \u0001\u001f\r\n\u000b\u000c ", text: "Controls only", insert_after: "end" }, "b");
    d = addCustomElement(d, { label: "\ufffe\uffff\ud800", text: "Non-characters only", insert_after: "end" }, "c");
    d = addCustomElement(d, { label: "\u0000Anthem", text: "Kept", insert_after: "sermon" }, "d");

    const { service } = documentRequest(d, "bulletin");
    expect(service.custom_elements).toEqual([{ label: "\u0000Anthem", text: "Kept", insert_after: "sermon" }]);
  });

  it("wordSafe reads text as the server's _xml_safe does", () => {
    expect(wordSafe("a\r\nb\rc\u000bd\u000ce")).toBe("a\nb\nc\nd\ne");
    expect(wordSafe("a\u0000b\u0008c\u001fd\ufffee\uffff")).toBe("abcde");
    expect(wordSafe("tab\there")).toBe("tab\there");
    expect(wordSafe("lone \ud800 \udc00 pair \ud83d\ude00")).toBe("lone   pair \ud83d\ude00");
  });
});
