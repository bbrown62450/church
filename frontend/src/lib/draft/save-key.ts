/**
 * The `Idempotency-Key` of a `POST /services` (slice 5a spec, "Save key rule";
 * F §1.6 "Frontend key rule"). Pure. The key lives in the draft, so it
 * survives a refresh: `save_key`, plus `save_key_fingerprint`, the
 * fingerprint of the payload last posted with it whose outcome is unknown.
 *
 * - `keyForPost(d, fp)` before each POST: a pending fingerprint that differs
 *   from `fp` means the uncertain attempt carried another body, so the key is
 *   replaced; then the fingerprint is recorded. An identical retry keeps the
 *   key, and the server replays its stored answer.
 * - `settlePost(d, outcome)` after it: a 2xx or a 4xx (other than a 429) is a
 *   definitive answer the server may have stored under the key, so the key is
 *   replaced and the fingerprint cleared; an unknown outcome (network error,
 *   timeout, cancel, 5xx, 429; `settleOutcome` in `lib/idempotency.ts`) keeps
 *   both. A PUT never uses the key.
 */
import type { SettleOutcome } from "@/lib/idempotency";

import type { DraftV1 } from "./schema";

export function keyForPost(d: DraftV1, fp: string): DraftV1 {
  if (d.save_key_fingerprint === fp) return d;
  const rotate = d.save_key_fingerprint !== null;
  return { ...d, save_key: rotate ? crypto.randomUUID() : d.save_key, save_key_fingerprint: fp };
}

export function settlePost(d: DraftV1, outcome: SettleOutcome): DraftV1 {
  if (outcome === "uncertain") return d;
  return { ...d, save_key: crypto.randomUUID(), save_key_fingerprint: null };
}
