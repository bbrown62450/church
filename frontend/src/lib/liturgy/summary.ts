/**
 * The liturgy counts behind the step bar's status and the summary (slice 4
 * spec, Frontend "Builder shell" `summary.ts`), one function so they cannot
 * disagree: `enabled` = cards switched on; `ready` = those whose text is
 * non-blank after trimming; `communion` = `include_communion`;
 * `customCount` = the custom elements.
 */
import { SECTION_KEYS, type DraftV1 } from "@/lib/draft/schema";

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
