/**
 * What a date change does outside the readings fields (S "readings.ts"
 * `setDate`; F §4.6 "Defaults apply only while origin is `default`").
 *
 * Slice 2: while `communion_origin` is `default`, `include_communion` follows
 * the first-Sunday rule for the new date (false for a weekday). Slice 3 adds
 * its hymn effect here (for example, dropping `alternatives` for another
 * date); slice 4 may move the communion rule into `applyLiturgyDefaults`.
 * Returns `d` itself when nothing changes.
 */
import { isFirstSundayOfMonth } from "@/lib/dates";

import type { DraftV1 } from "./schema";

// `prevIso` is kept in the signature for slice 3's hymn effect.
export function onDateChanged(d: DraftV1, prevIso: string): DraftV1 {
  void prevIso;
  if (d.liturgy.communion_origin !== "default") return d;
  const include = isFirstSundayOfMonth(d.readings.date_iso);
  if (include === d.liturgy.include_communion) return d;
  return { ...d, liturgy: { ...d.liturgy, include_communion: include } };
}
