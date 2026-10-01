/**
 * The liturgy defaults (slice 4 spec, Frontend `defaults.ts`, "Draft store
 * integration"; F §4.6 "Defaults apply only while origin is `default`"):
 *
 * - A Benediction card whose origin is "default" shows the church's
 *   `default_benediction` (GET /church; "Halverson" when an older API leaves it
 *   out), including "" (no default: the card is empty).
 * - Communion whose origin is "default" follows the first-Sunday rule for the
 *   draft's date (`isFirstSundayOfMonth`, slice 2's port of
 *   `liturgy_config.is_first_sunday_of_month`, run against
 *   shared/first_sunday.json in `defaults.test.ts`). This is the one place for
 *   the rule: `date-effects.ts` calls `applyCommunionDefault` on a date change.
 *
 * Both return the same object when nothing changes, so the draft store can
 * run them after every change without writing.
 */
import { isFirstSundayOfMonth } from "@/lib/dates";
import type { DraftV1 } from "@/lib/draft/schema";

export const DEFAULT_BENEDICTION_FALLBACK = "Halverson";

export type LiturgyDefaults = { defaultBenediction: string };

export function applyCommunionDefault(d: DraftV1): DraftV1 {
  if (d.liturgy.communion_origin !== "default") return d;
  const include = isFirstSundayOfMonth(d.readings.date_iso);
  if (include === d.liturgy.include_communion) return d;
  return { ...d, liturgy: { ...d.liturgy, include_communion: include } };
}

export function applyLiturgyDefaults(d: DraftV1, { defaultBenediction }: LiturgyDefaults): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
  let next = d;
  if (benediction.origin === "default" && benediction.text !== defaultBenediction) {
    next = {
      ...d,
      liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { ...benediction, text: defaultBenediction } } },
    };
  }
  return applyCommunionDefault(next);
}
