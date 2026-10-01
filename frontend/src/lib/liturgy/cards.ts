/**
 * The Liturgy step's draft transitions and selectors (slice 4 spec, Frontend
 * `cards.ts`, "Card origin transitions"; F §4.6 "Card text is the user's").
 * Pure: each transition takes the draft and returns the next one, or the
 * same object when nothing changes, so `update(recipe)` stays a no-op.
 *
 * - Typing sets the origin to "typed", or "empty" when the text is blank
 *   after trimming; an AI result sets "ai"; Clear sets "" and "empty"; "Use
 *   church default" sets the default and "default"; Undo restores the
 *   previous text and origin; a switch changes neither.
 * - `staleVerdict` is the rule for a result that arrives after its request
 *   started (S "Generate and Regenerate" step 6). The generation provider
 *   applies it, and the service reviewer (the slice after 4b) reuses it for
 *   review results: capture the card when the request starts, compare when
 *   the answer arrives.
 */
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
import { SECTION_KEYS } from "@/lib/draft/schema";

import { applyCommunionDefault } from "./defaults";

export type CardOrigin = LiturgyCard["origin"];
export type CardSnapshot = { text: string; origin: CardOrigin };
export type CustomElement = DraftV1["liturgy"]["custom_elements"][number];

/**
 * The 17 custom-element places (backend `liturgy_config.CUSTOM_PLACEMENTS`
 * keys, in order); `cards.test.ts` pins them to the outline fixture's
 * anchors. The labels come from GET /liturgy/config.
 */
export const PLACEMENT_KEYS = [
  "call_to_worship",
  "opening_prayer",
  "first_hymn",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "ot_reading",
  "nt_reading",
  "sermon",
  "affirmation_of_faith",
  "second_hymn",
  "communion",
  "prayers_of_the_people",
  "offertory_prayer",
  "third_hymn",
  "benediction",
  "end",
] as const;

const PLACEMENTS: ReadonlySet<string> = new Set(PLACEMENT_KEYS);

/** A known place unchanged; anything else "end" (never dropped; mirrors `liturgy_config.normalize_placement`). */
export function normalizePlacement(key: string): string {
  return PLACEMENTS.has(key) ? key : "end";
}

function withCard(d: DraftV1, key: SectionKey, next: LiturgyCard): DraftV1 {
  const current = d.liturgy.cards[key];
  if (current.enabled === next.enabled && current.text === next.text && current.origin === next.origin) return d;
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: next } } };
}

function withLiturgy(d: DraftV1, patch: Partial<DraftV1["liturgy"]>): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, ...patch } };
}

/** The user typed: "typed" when non-blank after trimming, else "empty". */
export function editCardText(d: DraftV1, key: SectionKey, text: string): DraftV1 {
  const card = d.liturgy.cards[key];
  return withCard(d, key, { ...card, text, origin: text.trim() === "" ? "empty" : "typed" });
}

export function setCardEnabled(d: DraftV1, key: SectionKey, enabled: boolean): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], enabled });
}

export function applyGenerated(d: DraftV1, key: SectionKey, text: string): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text, origin: "ai" });
}

export function clearCard(d: DraftV1, key: SectionKey): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text: "", origin: "empty" });
}

/** "Use church default" (Benediction): the default's text, following it again. */
export function restoreChurchDefault(d: DraftV1, defaultText: string): DraftV1 {
  return withCard(d, "benediction", { ...d.liturgy.cards.benediction, text: defaultText, origin: "default" });
}

/** Undo: the text and origin kept in memory before a Regenerate or Clear. */
export function restoreCard(d: DraftV1, key: SectionKey, previous: CardSnapshot): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text: previous.text, origin: previous.origin });
}

export function setSermonTitle(d: DraftV1, title: string): DraftV1 {
  return d.liturgy.sermon_title === title ? d : withLiturgy(d, { sermon_title: title });
}

/** The communion switch: the user's choice from now on. */
export function setCommunion(d: DraftV1, include: boolean): DraftV1 {
  const l = d.liturgy;
  if (l.include_communion === include && l.communion_origin === "user") return d;
  return withLiturgy(d, { include_communion: include, communion_origin: "user" });
}

/** "Use default": communion follows the first-Sunday rule for the date again. */
export function restoreCommunionDefault(d: DraftV1): DraftV1 {
  const next = d.liturgy.communion_origin === "default" ? d : withLiturgy(d, { communion_origin: "default" });
  return applyCommunionDefault(next);
}

/** Appends an element with its label and text trimmed and its place normalized (S "On Add"). */
export function addCustomElement(d: DraftV1, element: Omit<CustomElement, "id">, id: string): DraftV1 {
  const added: CustomElement = {
    id,
    label: element.label.trim(),
    text: element.text.trim(),
    insert_after: normalizePlacement(element.insert_after),
  };
  return withLiturgy(d, { custom_elements: [...d.liturgy.custom_elements, added] });
}

export function updateCustomElement(d: DraftV1, id: string, patch: Partial<Omit<CustomElement, "id">>): DraftV1 {
  const list = d.liturgy.custom_elements;
  const at = list.findIndex((e) => e.id === id);
  if (at < 0) return d;
  const next = { ...list[at], ...patch };
  if (next.label === list[at].label && next.text === list[at].text && next.insert_after === list[at].insert_after) return d;
  return withLiturgy(d, { custom_elements: list.map((e, i) => (i === at ? next : e)) });
}

/** Removes the element; null when it is not there. The element and its index are for Undo. */
export function removeCustomElement(
  d: DraftV1,
  id: string,
): { draft: DraftV1; element: CustomElement; index: number } | null {
  const list = d.liturgy.custom_elements;
  const index = list.findIndex((e) => e.id === id);
  if (index < 0) return null;
  return { draft: withLiturgy(d, { custom_elements: list.filter((e) => e.id !== id) }), element: list[index], index };
}

/** Undo of Remove: back at its index (or the end), unless it is already there or the list is full (`max`). */
export function restoreCustomElement(d: DraftV1, element: CustomElement, index: number, max: number): DraftV1 {
  const list = d.liturgy.custom_elements;
  if (list.some((e) => e.id === element.id) || list.length >= max) return d;
  const at = Math.min(Math.max(index, 0), list.length);
  return withLiturgy(d, { custom_elements: [...list.slice(0, at), element, ...list.slice(at)] });
}

// --- selectors ---------------------------------------------------------------

/** Switched-on cards with no text (after trimming), in section order: what "Generate empty sections" sends. */
export function sectionsNeedingAi(d: DraftV1): SectionKey[] {
  return SECTION_KEYS.filter((key) => {
    const card = d.liturgy.cards[key];
    return card.enabled && card.text.trim() === "";
  });
}

/** Regenerate asks first when it would replace the user's own or a saved service's text. */
export function needsRegenerateConfirm(card: LiturgyCard): boolean {
  return (card.origin === "typed" || card.origin === "archive") && card.text.trim() !== "";
}

export type CapturedCard = { createdAt: string; text: string; origin: CardOrigin };

/** What a run remembers when its request starts. */
export function captureCard(d: DraftV1, key: SectionKey): CapturedCard {
  const card = d.liturgy.cards[key];
  return { createdAt: d.created_at, text: card.text, origin: card.origin };
}

export type StaleVerdict = "apply" | "service_changed" | "edited";

/**
 * S step 6, first matching rule: the draft was replaced (New service, an
 * archive load) → "service_changed"; the card followed the church default
 * then and still does → "apply" (the default changed mid-run, and the user
 * asked to replace it); its text changed (an edit in another tab) →
 * "edited"; otherwise "apply".
 */
export function staleVerdict(d: DraftV1, key: SectionKey, captured: CapturedCard): StaleVerdict {
  if (d.created_at !== captured.createdAt) return "service_changed";
  const card = d.liturgy.cards[key];
  if (captured.origin === "default" && card.origin === "default") return "apply";
  if (card.text !== captured.text) return "edited";
  return "apply";
}
