/**
 * The "From the pews" panel's rules (pew voices spec 2026-10-20, "The liturgy
 * step"). Pure. The panel lives in client memory only (`PewsProvider`).
 *
 * - `applyPews(draft, ask, result)`: the answer as the panel shows it, or
 *   null when the service is no longer the one asked about. A reaction about
 *   a prayer whose text or origin changed while the request ran is dropped
 *   (slice 4's stale rule, as the review's `applyReview`); each kept one
 *   remembers the prayer's text it was about.
 * - `prunePews(panel, draft)`: on every draft change, a reaction whose
 *   prayer's text changed goes; a new service drops the panel.
 * - `dismissReaction`, `reactionCount`, `pewsDoneMessage`.
 * - `PEWS_UNAVAILABLE`: a 404's message (a page newer than the server it
 *   talks to), in place of the cards' hymn message for "not_found".
 */
import type { PewsResult } from "@/lib/api/types";
import type { DraftV1, SectionKey } from "@/lib/draft/schema";

import type { ReviewAsk } from "./notes";

export type ShownReaction = {
  id: string;
  text: string;
  section: SectionKey | null;
  /** The prayer's text the reaction was about (null for the whole service). */
  about: string | null;
};
export type ShownVoice = { description: string; reactions: ShownReaction[] };
/** `found`: how many reactions the answer had once stale ones were dropped (0 shows "No reactions this time."). */
export type PewsPanel = { createdAt: string; voices: ShownVoice[]; found: number };

export const NO_REACTIONS = "No reactions this time.";
export const PEWS_UNAVAILABLE = "Hear it from the pews is not available yet. Try again in a few minutes.";

/** `prefix` keeps each answer's reaction ids apart from the last one's. */
export function applyPews(d: DraftV1, ask: ReviewAsk, result: PewsResult, prefix = "pews"): PewsPanel | null {
  if (d.created_at !== ask.createdAt) return null;
  let n = 0;
  const voices = result.voices.map((voice) => ({
    description: voice.description,
    reactions: voice.reactions.flatMap((r): ShownReaction[] => {
      n += 1;
      const id = `${prefix}-${n}`;
      if (r.section === null || r.section === undefined) return [{ id, text: r.text, section: null, about: null }];
      const was = ask.cards[r.section];
      const card = d.liturgy.cards[r.section];
      if (was === undefined || card.text !== was.text || card.origin !== was.origin) return [];
      return [{ id, text: r.text, section: r.section, about: card.text }];
    }),
  }));
  return { createdAt: ask.createdAt, voices, found: voices.reduce((sum, v) => sum + v.reactions.length, 0) };
}

export function prunePews(panel: PewsPanel | null, d: DraftV1): PewsPanel | null {
  if (panel === null) return null;
  if (d.created_at !== panel.createdAt) return null;
  let changed = false;
  const voices = panel.voices.map((voice) => {
    const reactions = voice.reactions.filter((r) => r.section === null || d.liturgy.cards[r.section].text === r.about);
    if (reactions.length !== voice.reactions.length) changed = true;
    return reactions.length === voice.reactions.length ? voice : { ...voice, reactions };
  });
  return changed ? { ...panel, voices } : panel;
}

export function dismissReaction(panel: PewsPanel, id: string): PewsPanel {
  return { ...panel, voices: panel.voices.map((v) => ({ ...v, reactions: v.reactions.filter((r) => r.id !== id) })) };
}

export function reactionCount(panel: PewsPanel): number {
  return panel.voices.reduce((sum, v) => sum + v.reactions.length, 0);
}

/** The polite line read out when an answer arrives. */
export function pewsDoneMessage(n: number): string {
  return n === 0 ? "From the pews: no reactions." : n === 1 ? "From the pews: 1 reaction." : `From the pews: ${n} reactions.`;
}
