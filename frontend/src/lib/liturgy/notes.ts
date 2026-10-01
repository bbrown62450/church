/**
 * The service reviewer's notes (reviewer spec, "Notes", "Notes go away when
 * the text changes", "Revise with these notes"; slice 4 spec, reviewer
 * amendment). Pure; the review provider keeps the state in memory only, never
 * in the draft, the archive or `localStorage` (`DraftV1` is unchanged).
 *
 * - `captureReview` remembers each card's text and origin when "Review
 *   service" is pressed; `applyReview` keeps a card's notes only while the
 *   card still holds exactly that (slice 4's stale-results rule, comparing
 *   text and origin), and drops the whole review when the service changed
 *   (a new `created_at`).
 * - `pruneReview` runs on every draft change (reviewer follow-up 1, owner
 *   answer 4 of 2026-10-01): a card whose text or origin no longer matches
 *   what was reviewed keeps its notes, marked `stale` ("From before your last
 *   edit.") until the next review (typing, Undo, "Use church default",
 *   another tab's edit; an Undo back to the reviewed words keeps them
 *   stale); a card left blank, or one with no notes left ("Looks good." or
 *   all dismissed), loses them; a new service loses the whole review. A
 *   successful Regenerate or Revise drops the card's notes (`forgetCard`,
 *   called by the providers), since the new text replaced or addressed them.
 * - "Looks good." shows for a card that was reviewed, came back with no
 *   notes and is unchanged since; a card whose notes were all dismissed
 *   shows nothing.
 * - Revise is offered on a card with text and a note left whose origin is
 *   "ai", "typed" or "archive" (owner answer 2 of 2026-10-01); never on the
 *   church default (owner answer 3). Typed and saved text asks first
 *   (`CardNotes`).
 */
import type { AiStatus, ReviewNote, ReviewResult } from "@/lib/api/types";
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";

/** The tag chips (R "Notes"). */
export const TAG_LABELS: Record<ReviewNote["tag"], string> = {
  checklist: "Checklist",
  rules: "Rules",
  voice: "Voice",
  read_aloud: "Read aloud",
  theology: "Theology",
  repetition: "Repetition",
};

export const LOOKS_GOOD = "Looks good.";
export const QUICK_CHECKS_ONLY = "Only quick checks ran. The full review isn't available right now.";

export type Note = ReviewNote & { id: string };
export type ReviewedCard = { text: string; origin: LiturgyCard["origin"] };
export const STALE_LINE = "From before your last edit.";

/**
 * `found`: how many notes the card came back with ("Looks good." only when 0).
 * `stale`: the card changed since it was reviewed; its notes show faded.
 */
export type CardReview = { reviewed: ReviewedCard; notes: Note[]; found: number; stale: boolean };
export type ServiceReview = {
  createdAt: string;
  cards: Partial<Record<SectionKey, CardReview>>;
  service: Note[];
  aiStatus: AiStatus;
};
export type ReviewAsk = { createdAt: string; cards: Partial<Record<SectionKey, ReviewedCard>> };

/** The cards as they are when "Review service" is pressed. */
export function captureReview(d: DraftV1, keys: readonly SectionKey[]): ReviewAsk {
  const cards: Partial<Record<SectionKey, ReviewedCard>> = {};
  for (const key of keys) cards[key] = { text: d.liturgy.cards[key].text, origin: d.liturgy.cards[key].origin };
  return { createdAt: d.created_at, cards };
}

function holds(card: LiturgyCard, reviewed: ReviewedCard): boolean {
  return card.text === reviewed.text && card.origin === reviewed.origin;
}

/**
 * The review as the step shows it: the notes of each card that still holds
 * what was sent, and the service's notes. `dropped` lists the cards whose
 * notes were dropped because they changed; the review is null when the
 * service changed.
 */
export function applyReview(
  d: DraftV1,
  ask: ReviewAsk,
  result: ReviewResult,
): { review: ServiceReview | null; dropped: SectionKey[] } {
  const asked = Object.keys(ask.cards) as SectionKey[];
  if (d.created_at !== ask.createdAt) return { review: null, dropped: asked };
  const cards: Partial<Record<SectionKey, CardReview>> = {};
  const dropped: SectionKey[] = [];
  for (const { section, notes } of result.cards) {
    const reviewed = ask.cards[section];
    if (reviewed === undefined) continue;
    if (!holds(d.liturgy.cards[section], reviewed)) {
      dropped.push(section);
      continue;
    }
    cards[section] = {
      reviewed,
      notes: notes.map((n, i) => ({ ...n, id: `${section}-${i}` })),
      found: notes.length,
      stale: false,
    };
  }
  return {
    review: {
      createdAt: ask.createdAt,
      cards,
      service: result.service_notes.map((n, i) => ({ ...n, id: `service-${i}` })),
      aiStatus: result.ai_status,
    },
    dropped,
  };
}

/**
 * The review after a draft change: a changed card's notes fade (`stale`),
 * a blank card's or a noteless card's go; the same object when nothing changed.
 */
export function pruneReview(review: ServiceReview | null, d: DraftV1): ServiceReview | null {
  if (review === null) return null;
  if (d.created_at !== review.createdAt) return null;
  let cards: Partial<Record<SectionKey, CardReview>> | null = null;
  for (const key of Object.keys(review.cards) as SectionKey[]) {
    const card = review.cards[key];
    const now = d.liturgy.cards[key];
    if (card === undefined) continue;
    const blank = now.text.trim() === "";
    if (!blank && (card.stale || holds(now, card.reviewed))) continue;
    cards ??= { ...review.cards };
    if (blank || card.notes.length === 0) delete cards[key];
    else cards[key] = { ...card, stale: true };
  }
  return cards === null ? review : { ...review, cards };
}

/** A successful Regenerate or Revise: the card's notes go (the new text replaced or addressed them). */
export function forgetCard(review: ServiceReview | null, key: SectionKey): ServiceReview | null {
  if (review === null || review.cards[key] === undefined) return review;
  const cards = { ...review.cards };
  delete cards[key];
  return { ...review, cards };
}

/** Removes one note, from a card or from "Across the service". */
export function dismissNote(review: ServiceReview, where: SectionKey | "service", id: string): ServiceReview {
  if (where === "service") {
    const service = review.service.filter((n) => n.id !== id);
    return service.length === review.service.length ? review : { ...review, service };
  }
  const card = review.cards[where];
  if (card === undefined || !card.notes.some((n) => n.id === id)) return review;
  return { ...review, cards: { ...review.cards, [where]: { ...card, notes: card.notes.filter((n) => n.id !== id) } } };
}

/** "Revise with these notes": a card with text and a note left, written by the AI, typed or from a saved service. */
export function canRevise(card: LiturgyCard, review: CardReview | undefined): boolean {
  const origin = card.origin === "ai" || card.origin === "typed" || card.origin === "archive";
  return origin && card.text.trim() !== "" && review !== undefined && review.notes.length > 0;
}

/** How many notes the review shows in all (for the announcement when it ends). */
export function noteCount(review: ServiceReview): number {
  return Object.values(review.cards).reduce((n, card) => n + (card?.notes.length ?? 0), 0) + review.service.length;
}
