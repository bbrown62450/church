/**
 * The service reviewer's notes (reviewer spec, "Notes", "Notes go away when
 * the text changes"; slice 4 spec, reviewer amendment Testing): stale results
 * dropped by text and origin, notes cleared by any change, dismiss, "Looks
 * good." and when Revise is offered.
 */
import { describe, expect, it } from "vitest";

import type { DraftV1, SectionKey } from "@/lib/draft/schema";
import { reviewNote, reviewResult, testDraft } from "@/test/fixtures";

import { applyGenerated, clearCard, editCardText, restoreChurchDefault } from "./cards";
import { applyReview, canRevise, captureReview, dismissNote, noteCount, pruneReview } from "./notes";

const STOCK = 'Stock phrase "as we journey". Say it more naturally.';

function withText(d: DraftV1, key: SectionKey, text: string, origin: DraftV1["liturgy"]["cards"]["benediction"]["origin"]): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], text, origin } } } };
}

function reviewed(): DraftV1 {
  let d = withText(testDraft(), "call_to_worship", "Leader: As we journey, come.", "typed");
  d = withText(d, "opening_prayer", "Gracious God, hear us.", "ai");
  return withText(d, "benediction", "Go in peace.", "default");
}

const ANSWER = reviewResult({
  cards: [
    { section: "call_to_worship", notes: [reviewNote("rules", STOCK, "code"), reviewNote("read_aloud", "Long line.")] },
    { section: "opening_prayer", notes: [reviewNote("theology", "Praise is not a payment.")] },
    { section: "benediction", notes: [] },
  ],
  service_notes: [reviewNote("repetition", 'Several prayers open with "Gracious God".', "code")],
});

describe("the reviewer's notes (R Notes)", () => {
  it("keeps the notes of each card that still holds what was reviewed, and drops the rest or the whole review", () => {
    const d = reviewed();
    const ask = captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]);
    const { review, dropped } = applyReview(d, ask, ANSWER);
    expect(dropped).toEqual([]);
    expect(review?.cards.call_to_worship?.notes.map((n) => [n.id, n.tag, n.text])).toEqual([
      ["call_to_worship-0", "rules", STOCK],
      ["call_to_worship-1", "read_aloud", "Long line."],
    ]);
    expect(review?.cards.benediction).toEqual({ reviewed: { text: "Go in peace.", origin: "default" }, notes: [], found: 0 });
    expect(review?.service.map((n) => n.id)).toEqual(["service-0"]);
    expect(review?.aiStatus).toBe("ok");
    expect(review && noteCount(review)).toBe(4);
    // Changed while the review ran: the text (typing, another tab) or only the origin (Use church default).
    let later = editCardText(d, "call_to_worship", "Leader: Come.");
    later = withText(later, "opening_prayer", "Gracious God, hear us.", "typed");
    const stale = applyReview(later, ask, ANSWER);
    expect(stale.dropped).toEqual(["call_to_worship", "opening_prayer"]);
    expect(Object.keys(stale.review?.cards ?? {})).toEqual(["benediction"]);
    // A card the review was not asked about is ignored; a new service drops everything.
    const extra = reviewResult({ cards: [{ section: "assurance", notes: [reviewNote("rules", "Not asked.")] }] });
    expect(applyReview(d, ask, extra).review?.cards).toEqual({});
    expect(applyReview({ ...d, created_at: "2026-09-29T16:00:01.000Z" }, ask, ANSWER)).toEqual({
      review: null,
      dropped: ["call_to_worship", "opening_prayer", "benediction"],
    });
  });

  it("clears a card's notes when its text or origin changes, and every note when the service changes", () => {
    const d = reviewed();
    const { review } = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER);
    expect(pruneReview(review, d)).toBe(review);                                    // nothing changed: the same object
    const changes: [string, DraftV1][] = [
      ["typing", editCardText(d, "opening_prayer", "Gracious God, hear us!")],
      ["Regenerate or Revise", applyGenerated(d, "opening_prayer", "A new draft.")],
      ["Clear text", clearCard(d, "opening_prayer")],
    ];
    for (const [what, next] of changes) {
      const pruned = pruneReview(review, next);
      expect(Object.keys(pruned?.cards ?? {}), what).toEqual(["call_to_worship", "benediction"]);
      expect(pruned?.service, what).toHaveLength(1);
    }
    // "Use church default" with the same words still changes the origin.
    const typed = withText(d, "benediction", "Go in peace.", "typed");
    const asked = applyReview(typed, captureReview(typed, ["benediction"]), ANSWER).review;
    expect(pruneReview(asked, restoreChurchDefault(typed, "Go in peace."))?.cards).toEqual({});
    expect(pruneReview(review, { ...d, created_at: "2026-09-29T16:00:01.000Z" })).toBeNull();
    expect(pruneReview(null, d)).toBeNull();
  });

  it("dismisses one note at a time, and Looks good is only for a card that came back with none", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    const one = dismissNote(review, "call_to_worship", "call_to_worship-0");
    expect(one.cards.call_to_worship?.notes.map((n) => n.text)).toEqual(["Long line."]);
    const none = dismissNote(one, "call_to_worship", "call_to_worship-1");
    expect(none.cards.call_to_worship).toMatchObject({ notes: [], found: 2 });     // shows nothing, not "Looks good."
    expect(review.cards.benediction).toMatchObject({ notes: [], found: 0 });       // "Looks good."
    expect(dismissNote(none, "service", "service-0").service).toEqual([]);
    expect(dismissNote(review, "opening_prayer", "nope")).toBe(review);
    expect(dismissNote(review, "assurance", "assurance-0")).toBe(review);
  });

  it("offers Revise only on an AI card with a note left", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    expect(canRevise(d.liturgy.cards.opening_prayer, review.cards.opening_prayer)).toBe(true);
    expect(canRevise(d.liturgy.cards.call_to_worship, review.cards.call_to_worship)).toBe(false);     // typed
    expect(canRevise(d.liturgy.cards.benediction, review.cards.benediction)).toBe(false);             // default
    const archive = { ...d.liturgy.cards.opening_prayer, origin: "archive" as const };
    expect(canRevise(archive, review.cards.opening_prayer)).toBe(false);
    const dismissed = dismissNote(review, "opening_prayer", "opening_prayer-0");
    expect(canRevise(d.liturgy.cards.opening_prayer, dismissed.cards.opening_prayer)).toBe(false);    // none left
    expect(canRevise(d.liturgy.cards.opening_prayer, undefined)).toBe(false);                          // not reviewed
  });
});
