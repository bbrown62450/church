/**
 * The Liturgy step's draft transitions (slice 4 spec, "Card origin
 * transitions", Frontend `cards.ts`; Testing `cards.test.ts`): every row of
 * the origin table, the selectors, the custom elements and the stale-result
 * rule the generation provider (and later the service reviewer) applies.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { DraftV1, SectionKey } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import {
  addCustomElement,
  applyGenerated,
  captureCard,
  clearCard,
  editCardText,
  needsRegenerateConfirm,
  normalizePlacement,
  PLACEMENT_KEYS,
  removeCustomElement,
  restoreCard,
  restoreChurchDefault,
  restoreCommunionDefault,
  restoreCustomElement,
  sectionsNeedingAi,
  setCardEnabled,
  setCommunion,
  setSermonTitle,
  staleVerdict,
  updateCustomElement,
} from "./cards";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

type Outline = { outline: { anchors_after: string[] }[] };

const outline = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/liturgy_outline.json", import.meta.url), "utf-8"),
) as Outline;

function withCard(d: DraftV1, key: SectionKey, patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
}

const card = (d: DraftV1, key: SectionKey) => d.liturgy.cards[key];

describe("card origin transitions (S Frontend changes)", () => {
  it("follows every row of the table, and returns the same draft when nothing changes", () => {
    const d = testDraft();
    // User edits: typed when non-blank after trimming, else empty.
    const typed = editCardText(d, "call_to_worship", "Come, let us worship.");
    expect(card(typed, "call_to_worship")).toEqual({ enabled: true, text: "Come, let us worship.", origin: "typed" });
    expect(card(editCardText(typed, "call_to_worship", "  \n"), "call_to_worship")).toEqual({
      enabled: true,
      text: "  \n",
      origin: "empty",
    });
    expect(editCardText(typed, "call_to_worship", "Come, let us worship.")).toBe(typed);
    // An AI result applied.
    const ai = applyGenerated(typed, "call_to_worship", "Leader: Come!");
    expect(card(ai, "call_to_worship")).toEqual({ enabled: true, text: "Leader: Come!", origin: "ai" });
    // Clear.
    const cleared = clearCard(ai, "call_to_worship");
    expect(card(cleared, "call_to_worship")).toEqual({ enabled: true, text: "", origin: "empty" });
    expect(clearCard(cleared, "call_to_worship")).toBe(cleared);
    // Use church default (Benediction).
    const edited = editCardText(d, "benediction", "Go in peace.");
    expect(card(restoreChurchDefault(edited, DEFAULT_BENEDICTION_FALLBACK), "benediction")).toEqual({
      enabled: true,
      text: DEFAULT_BENEDICTION_FALLBACK,
      origin: "default",
    });
    // Undo: previous text and origin.
    expect(card(restoreCard(ai, "call_to_worship", { text: "Come, let us worship.", origin: "typed" }), "call_to_worship")).toEqual(
      card(typed, "call_to_worship"),
    );
    // Switch toggled: text and origin unchanged.
    const off = setCardEnabled(ai, "call_to_worship", false);
    expect(card(off, "call_to_worship")).toEqual({ enabled: false, text: "Leader: Come!", origin: "ai" });
    expect(setCardEnabled(off, "call_to_worship", false)).toBe(off);
  });

  it("sends only switched-on cards with no text to the AI, and confirms before replacing typed or saved text", () => {
    let d = testDraft();
    d = editCardText(d, "call_to_worship", "Come.");
    d = editCardText(d, "opening_prayer", "   ");
    d = setCardEnabled(d, "assurance", false);
    d = withCard(d, "benediction", { text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" });
    expect(sectionsNeedingAi(d)).toEqual(["opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"]);
    expect(needsRegenerateConfirm({ enabled: true, text: "Come.", origin: "typed" })).toBe(true);
    expect(needsRegenerateConfirm({ enabled: true, text: "Saved words", origin: "archive" })).toBe(true);
    expect(needsRegenerateConfirm({ enabled: true, text: "Leader: Come!", origin: "ai" })).toBe(false);
    expect(needsRegenerateConfirm({ enabled: true, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" })).toBe(false);
    expect(needsRegenerateConfirm({ enabled: true, text: "  ", origin: "typed" })).toBe(false);
  });
});

describe("the stale-result rule (S Generate and Regenerate, step 6)", () => {
  it("drops a result for a replaced draft or an edited card, and applies it to a card still following the default", () => {
    const d = withCard(testDraft(), "benediction", { text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" });
    const captured = captureCard(d, "benediction");
    expect(captured).toEqual({ createdAt: d.created_at, text: DEFAULT_BENEDICTION_FALLBACK, origin: "default" });
    expect(staleVerdict(d, "benediction", captured)).toBe("apply");
    expect(staleVerdict({ ...d, created_at: "2026-09-30T12:00:00.000Z" }, "benediction", captured)).toBe("service_changed");
    // The church default changed mid-run: the user asked to replace the default, so apply.
    expect(staleVerdict(withCard(d, "benediction", { text: "Go in peace." }), "benediction", captured)).toBe("apply");
    // Edited in another tab.
    expect(staleVerdict(editCardText(d, "benediction", "My blessing"), "benediction", captured)).toBe("edited");
    const typed = editCardText(d, "opening_prayer", "Gracious God");
    const before = captureCard(typed, "opening_prayer");
    expect(staleVerdict(editCardText(typed, "opening_prayer", "Gracious God, hear us"), "opening_prayer", before)).toBe("edited");
  });
});

describe("communion, the sermon title and custom elements (S Communion card, Custom elements)", () => {
  it("toggles communion as the user's and restores the default, and stores the sermon title as typed", () => {
    const d = testDraft(); // Sunday, October 4, 2026: a first Sunday
    const off = setCommunion(d, false);
    expect(off.liturgy).toMatchObject({ include_communion: false, communion_origin: "user" });
    expect(restoreCommunionDefault(off).liturgy).toMatchObject({ include_communion: true, communion_origin: "default" });
    expect(restoreCommunionDefault(d)).toBe(d);
    expect(setSermonTitle(d, "Living Water").liturgy.sermon_title).toBe("Living Water");
    expect(setSermonTitle(d, "")).toBe(d);
  });

  it("adds, edits, removes and restores custom elements at their index, and normalizes unknown places to end", () => {
    const placements = new Set(outline.outline.flatMap((item) => item.anchors_after));
    expect(new Set(PLACEMENT_KEYS)).toEqual(placements);
    expect(PLACEMENT_KEYS).toHaveLength(17);
    expect(normalizePlacement("sermon")).toBe("sermon");
    expect(normalizePlacement("bogus")).toBe("end");

    let d = testDraft();
    d = addCustomElement(d, { label: "  Children's Moment ", text: " Come forward. ", insert_after: "opening_prayer" }, "a");
    d = addCustomElement(d, { label: "Anthem", text: "", insert_after: "sermon" }, "b");
    d = addCustomElement(d, { label: "Minute for Mission", text: "", insert_after: "bogus" }, "c");
    expect(d.liturgy.custom_elements).toEqual([
      { id: "a", label: "Children's Moment", text: "Come forward.", insert_after: "opening_prayer" },
      { id: "b", label: "Anthem", text: "", insert_after: "sermon" },
      { id: "c", label: "Minute for Mission", text: "", insert_after: "end" },
    ]);
    const moved = updateCustomElement(d, "b", { insert_after: "second_hymn", label: "Choir Anthem" });
    expect(moved.liturgy.custom_elements[1]).toEqual({ id: "b", label: "Choir Anthem", text: "", insert_after: "second_hymn" });
    expect(updateCustomElement(moved, "b", { label: "Choir Anthem" })).toBe(moved);
    const removed = removeCustomElement(moved, "b");
    expect(removed?.index).toBe(1);
    expect(removed?.element.label).toBe("Choir Anthem");
    expect(removed?.draft.liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "c"]);
    expect(removeCustomElement(moved, "zzz")).toBeNull();
    const restored = restoreCustomElement(removed!.draft, removed!.element, removed!.index, 30);
    expect(restored.liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "b", "c"]);
    expect(restoreCustomElement(restored, removed!.element, 1, 30)).toBe(restored); // already back
    expect(restoreCustomElement(removed!.draft, removed!.element, removed!.index, 2)).toBe(removed!.draft); // the list is full
  });
});
