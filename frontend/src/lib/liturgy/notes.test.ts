/**
 * The service reviewer's notes (reviewer spec, "Notes", "Notes go away when
 * the text changes"; slice 4 spec, reviewer amendment Testing; reviewer
 * follow-up 1): stale results dropped by text and origin, notes faded by any
 * later change and dropped by a new draft, dismiss, "Looks good." and when
 * Revise is offered.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { DraftV1, SectionKey } from "@/lib/draft/schema";
import { reviewNote, reviewResult, testDraft } from "@/test/fixtures";

import { applyGenerated, clearCard, editCardText, restoreChurchDefault } from "./cards";
import { DEFAULT_BENEDICTION_FALLBACK } from "./defaults";
import {
  acrossNote,
  acrossTargets,
  applyReview,
  canRevise,
  captureReview,
  dismissNote,
  forgetCard,
  listLabels,
  noteCount,
  openingWords,
  pruneReview,
  sharedOpening,
} from "./notes";

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
    expect(review?.cards.benediction).toEqual({ reviewed: { text: "Go in peace.", origin: "default" }, notes: [], found: 0, stale: false });
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

  it("fades a card's notes when its text or origin changes, drops a blank or noteless card's, and every note when the service changes", () => {
    const d = reviewed();
    const { review } = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER);
    expect(pruneReview(review, d)).toBe(review);                                    // nothing changed: the same object
    const changes: [string, DraftV1][] = [
      ["typing", editCardText(d, "opening_prayer", "Gracious God, hear us!")],
      ["another tab, or an Undo", withText(d, "opening_prayer", "Gracious God, hear us all.", "ai")],
      ["only the origin", withText(d, "opening_prayer", "Gracious God, hear us.", "typed")],
    ];
    for (const [what, next] of changes) {
      const pruned = pruneReview(review, next);
      expect(pruned?.cards.opening_prayer, what).toEqual({ ...review?.cards.opening_prayer, stale: true });
      expect(pruned?.cards.call_to_worship?.stale, what).toBe(false);
      expect(pruned?.service, what).toHaveLength(1);
      // Faded until the next review, even back at the reviewed words.
      const back = pruneReview(pruned, d);
      expect(back?.cards.opening_prayer?.stale, what).toBe(true);
      expect(pruneReview(back, d), what).toBe(back);
    }
    // Clear text: a blank card shows no notes; "Looks good." and a card with every note dismissed go after any edit.
    expect(Object.keys(pruneReview(review, clearCard(d, "opening_prayer"))?.cards ?? {})).toEqual(["call_to_worship", "benediction"]);
    expect(pruneReview(review, editCardText(d, "benediction", "Go in peace!"))?.cards.benediction).toBeUndefined();
    const dismissed = dismissNote(review!, "call_to_worship", "call_to_worship-0");
    expect(pruneReview(dismissed, editCardText(d, "call_to_worship", "Come."))?.cards.call_to_worship).toEqual({
      ...dismissed.cards.call_to_worship,
      stale: true,
    });
    const none = dismissNote(dismissed, "call_to_worship", "call_to_worship-1");
    expect(pruneReview(none, editCardText(d, "call_to_worship", "Come."))?.cards.call_to_worship).toBeUndefined();
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

  it("forgets a card's notes after a new AI draft or a revision lands; a faded AI card can still be revised", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    const written = applyGenerated(d, "opening_prayer", "A new draft.");
    const forgotten = forgetCard(pruneReview(review, written), "opening_prayer");
    expect(Object.keys(forgotten?.cards ?? {})).toEqual(["call_to_worship", "benediction"]);
    expect(forgotten?.service).toHaveLength(1);
    expect(forgetCard(review, "assurance")).toBe(review);
    expect(forgetCard(null, "opening_prayer")).toBeNull();
    const elsewhere = withText(d, "opening_prayer", "Gracious God, hear us all.", "ai");
    const faded = pruneReview(review, elsewhere)!;
    expect(canRevise(elsewhere.liturgy.cards.opening_prayer, faded.cards.opening_prayer)).toBe(true);
  });

  it("offers Revise on AI, typed and saved text with a note left, never on the church default or a blank card", () => {
    const d = reviewed();
    const review = applyReview(d, captureReview(d, ["call_to_worship", "opening_prayer", "benediction"]), ANSWER).review!;
    expect(canRevise(d.liturgy.cards.opening_prayer, review.cards.opening_prayer)).toBe(true);
    expect(canRevise(d.liturgy.cards.call_to_worship, review.cards.call_to_worship)).toBe(true);      // typed
    expect(canRevise(d.liturgy.cards.benediction, review.cards.benediction)).toBe(false);             // default, no notes
    const archive = { ...d.liturgy.cards.opening_prayer, origin: "archive" as const };
    expect(canRevise(archive, review.cards.opening_prayer)).toBe(true);
    const followsDefault = { ...d.liturgy.cards.opening_prayer, origin: "default" as const };
    expect(canRevise(followsDefault, review.cards.opening_prayer)).toBe(false);                       // even with notes
    const blank = { ...d.liturgy.cards.opening_prayer, text: "  ", origin: "typed" as const };
    expect(canRevise(blank, review.cards.opening_prayer)).toBe(false);
    const dismissed = dismissNote(review, "opening_prayer", "opening_prayer-0");
    expect(canRevise(d.liturgy.cards.opening_prayer, dismissed.cards.opening_prayer)).toBe(false);    // none left
    expect(canRevise(d.liturgy.cards.opening_prayer, undefined)).toBe(false);                          // not reviewed
  });
});

describe("Revise the other prayers (reviewer follow-up 2)", () => {
  type Fixture = {
    opening_note: string;
    cases: { text: string; words: string[] }[];
    groups: { texts: string[]; words: string | null }[];
  };
  const fixture = JSON.parse(
    readFileSync(new URL("../../../../backend/tests/fixtures/shared/opening_words.json", import.meta.url), "utf-8"),
  ) as Fixture;

  it("reads openings and the shared-opening note as the backend does (the shared fixture)", () => {
    for (const { text, words } of fixture.cases) expect(openingWords(text), text).toEqual(words);
    // The same openings, any case, as the backend groups them: every one is found from the note's words.
    const keys: SectionKey[] = ["call_to_worship", "opening_prayer", "prayer_of_confession"];
    for (const { texts, words } of fixture.groups) {
      const d = texts.reduce((acc, t, i) => withText(acc, keys[i], t, "typed"), testDraft());
      const found = acrossTargets(d, words ?? openingWords(texts[0]).join(" "), DEFAULT_BENEDICTION_FALLBACK);
      expect(found === null ? null : [found.first, ...found.others], texts.join(" / ")).toEqual(words === null ? null : keys.slice(0, texts.length));
    }
    const text = fixture.opening_note.replace("{words}", "Gracious God");
    expect(sharedOpening(reviewNote("repetition", text, "code"))).toBe("Gracious God");
    expect(sharedOpening(reviewNote("repetition", text))).toBeNull(); // an AI note: no button
    expect(sharedOpening(reviewNote("rules", text, "code"))).toBeNull();
    expect(sharedOpening(reviewNote("repetition", "Two prayers say journey.", "code"))).toBeNull();
    expect(acrossNote("Gracious God", "Call to Worship")).toBe('Opens with "Gracious God" like the Call to Worship; open differently.');
    // One at a time (owner decision A): each later note also names the openings the batch has produced so far.
    expect(acrossNote("Gracious God", "Call to Worship", ["Holy One"])).toBe(
      'Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy One".',
    );
    expect(acrossNote("Gracious God", "Call to Worship", ["Holy One", "Loving God"])).toBe(
      'Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy One" or "Loving God".',
    );
    expect(acrossNote("Gracious God", "Call to Worship", ["Holy One", "Loving God", "Merciful God"])).toBe(
      'Opens with "Gracious God" like the Call to Worship; open differently, not with "Holy One", "Loving God" or "Merciful God".',
    );
    // At most 240 characters (ReviseIn): the oldest extra openings go first.
    const long = ["a", "b", "c", "d", "e", "f"].map((c) => `${c.repeat(30)} ${c.repeat(30)}`);
    const capped = acrossNote("Gracious God", "Call to Worship", long);
    expect([...capped].length).toBeLessThanOrEqual(240);
    expect(capped).toBe(
      `Opens with "Gracious God" like the Call to Worship; open differently, not with "${long[4]}" or "${long[5]}".`,
    );
    expect([[], ["A"], ["A", "B"], ["A", "B", "C"]].map(listLabels)).toEqual(["", "A", "A and B", "A, B and C"]);
  });

  it("finds the prayers as the draft is now: the first kept, a default Benediction and switched-off cards left out", () => {
    let d = withText(testDraft(), "call_to_worship", "Leader: Gracious God, we gather.", "typed");
    d = withText(d, "opening_prayer", "gracious god! Hear us.", "ai");
    d = withText(d, "prayer_of_confession", "Gracious God, we confess.", "archive");
    d = { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, prayer_of_confession: { ...d.liturgy.cards.prayer_of_confession, enabled: false } } } };
    d = withText(d, "assurance", "People: Gracious   God, you forgive.", "archive");
    d = withText(d, "benediction", "Gracious God, go with us.", "default");
    expect(acrossTargets(d, "Gracious God", DEFAULT_BENEDICTION_FALLBACK)).toEqual({ words: "Gracious God", first: "call_to_worship", others: ["opening_prayer", "assurance"] });
    expect(acrossTargets(d, "Holy One", DEFAULT_BENEDICTION_FALLBACK)).toBeNull();
    // Only the first and a Benediction following the default share it: the default is not reviewed (owner, 2026-10-02), so no shared opening.
    const left = withText(withText(d, "opening_prayer", "Holy One, hear us.", "ai"), "assurance", "", "empty");
    expect(acrossTargets(left, "Gracious God", DEFAULT_BENEDICTION_FALLBACK)).toBeNull();
    // Once edited, the Benediction is typed text and is revised; a lone opening is no shared one.
    expect(acrossTargets(withText(left, "benediction", "Gracious God, go with us. Amen.", "typed"), "gracious god", DEFAULT_BENEDICTION_FALLBACK)?.others).toEqual(["benediction"]);
    expect(acrossTargets(withText(left, "benediction", "Go in peace.", "typed"), "Gracious God", DEFAULT_BENEDICTION_FALLBACK)).toBeNull();
  });
});
