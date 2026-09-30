/** Request timeouts (F §1.8, §4.5). apiFetch uses timeoutFor unless the caller passes timeoutMs. */
export const DEFAULT_TIMEOUT_MS = 20_000;

/** Endpoints slower than the default, keyed "METHOD /path" (path without the query string). */
const ENDPOINT_TIMEOUTS: Record<string, number> = {
  // Creating a church copies the whole hymn catalog into it (slice 1b).
  "POST /churches": 30_000,
  // Slice 2 (S "Client timeouts"): the lectionary's two sources answer within its 20 s deadline;
  // passages have a 20 s server deadline per request, and the clock starts when the limiter sends it.
  "GET /lectionary/readings": 25_000,
  "POST /scripture/passages": 30_000,
  // Slice 3 (S API; F §1.8): the server answers within its 75 s deadline.
  "POST /hymns/suggestions": 90_000,
};

export function timeoutFor(method: string, path: string): number {
  const key = `${method.toUpperCase()} ${path.split("?")[0]}`;
  return ENDPOINT_TIMEOUTS[key] ?? DEFAULT_TIMEOUT_MS;
}
