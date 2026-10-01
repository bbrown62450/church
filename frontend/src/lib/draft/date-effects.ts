/**
 * What a date change does outside the readings fields (S "readings.ts"
 * `setDate`; F §4.6 "Defaults apply only while origin is `default`").
 *
 * While `communion_origin` is `default`, `include_communion` follows the
 * first-Sunday rule for the new date (false for a weekday). The rule lives in
 * `lib/liturgy/defaults.ts` (`applyCommunionDefault`, slice 4b), which the
 * draft store also runs after every change. Slice 3 adds no hymn effect here
 * (its ideas carry their own date). Returns `d` itself when nothing changes.
 */
import { applyCommunionDefault } from "@/lib/liturgy/defaults";

import type { DraftV1 } from "./schema";

// `prevIso` is kept in the signature for a later date effect.
export function onDateChanged(d: DraftV1, prevIso: string): DraftV1 {
  void prevIso;
  return applyCommunionDefault(d);
}
