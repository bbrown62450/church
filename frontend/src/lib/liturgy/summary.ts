/**
 * The liturgy counts behind the step bar's status and the summary (slice 4
 * spec, Frontend "Builder shell" `summary.ts`), one function so they cannot
 * disagree: `enabled` = cards switched on; `ready` = those whose text is
 * non-blank after trimming; `communion` = `include_communion`;
 * `customCount` = the custom elements. `affirmationSummary` is the summary's
 * Affirmation of Faith line (the affirmation spec).
 */
import { SECTION_KEYS, type DraftAffirmation, type DraftV1 } from "@/lib/draft/schema";

const AFFIRMATION_NAMES = { apostles: "Apostles' Creed", nicene: "Nicene Creed", own: "Your own text" } as const;

export function affirmationSummary(a: DraftAffirmation): string {
  if (!a.include) return "Affirmation of Faith: Off";
  const blank = a.choice === "own" && a.text.trim() === "";
  return `Affirmation of Faith: ${AFFIRMATION_NAMES[a.choice]}${blank ? " (nothing typed yet)" : ""}`;
}

export type LiturgyCounts = { ready: number; enabled: number; communion: boolean; customCount: number };

export function liturgyCounts(d: DraftV1): LiturgyCounts {
  const enabled = SECTION_KEYS.map((key) => d.liturgy.cards[key]).filter((card) => card.enabled);
  return {
    ready: enabled.filter((card) => card.text.trim() !== "").length,
    enabled: enabled.length,
    communion: d.liturgy.include_communion,
    customCount: d.liturgy.custom_elements.length,
  };
}
