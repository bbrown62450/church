/**
 * Idempotency keys for a POST that is safe to retry (F §1.6; S "API client and query layer").
 * A form holds one tracker per mount (in a ref), asks `keyFor(body)` on every submit and
 * reports how the request ended with `settle(...)`. The key is reused only while a request
 * with the identical body is in flight or its outcome is unknown (network error, timeout,
 * cancel, 5xx), so a retry replays the first response instead of creating a second church.
 * Any 2xx or 4xx, or a changed body, gets a new key. The bulletin email (slice 5b-2) uses
 * this tracker as the 5b spec's `createSendKeyTracker`: a send that may already have gone out
 * keeps its key, so a plain retry replays "check your Sent folder", and only **Send again
 * anyway** (`rotate`) sends with a new one.
 */
import { ApiError } from "@/lib/api/client";

/** How a request ended: `success` (2xx), `client_error` (4xx) or `uncertain` (anything else). */
export type SettleOutcome = "success" | "client_error" | "uncertain";

export type KeyTracker = {
  /** The key to send with `body`: the pending key when the body is unchanged, else a new UUID. */
  keyFor(body: unknown): string;
  /** `success` and `client_error` drop the pending key; `uncertain` keeps it for an identical retry. */
  settle(outcome: SettleOutcome): void;
  /** Drop the pending key now: the next request is a new one, even with the same body. */
  rotate(): void;
};

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** `JSON.stringify` with object keys sorted at every depth, so key order never changes a fingerprint. */
export function stableStringify(value: unknown): string {
  return JSON.stringify(value, (_key, inner: unknown) =>
    isPlainObject(inner)
      ? Object.fromEntries(Object.keys(inner).sort().map((key) => [key, inner[key]]))
      : inner,
  );
}

export function createKeyTracker({
  fingerprint = stableStringify,
}: { fingerprint?: (body: unknown) => string } = {}): KeyTracker {
  let pending: { key: string; print: string } | null = null;
  return {
    keyFor(body) {
      const print = fingerprint(body);
      if (pending === null || pending.print !== print) {
        pending = { key: crypto.randomUUID(), print };
      }
      return pending.key;
    },
    settle(outcome) {
      if (outcome !== "uncertain") pending = null;
    },
    rotate() {
      pending = null;
    },
  };
}

/**
 * The `settle` outcome for a failed request (1b clarification 46): a 4xx `ApiError` is a
 * `client_error` (the server answered and stored nothing that a new key could duplicate);
 * status 0 (network error, timeout, cancel), a 5xx or any other thrown value is `uncertain`.
 * A 429 is `uncertain` too (F §1.8: a 429 is never stored, so the same key is retried after
 * Retry-After). An earlier try with this key may have succeeded before the limiter refused a
 * retry, and a new key would then create a duplicate.
 */
export function settleOutcome(e: unknown): "client_error" | "uncertain" {
  return e instanceof ApiError && e.status >= 400 && e.status <= 499 && e.status !== 429
    ? "client_error"
    : "uncertain";
}
