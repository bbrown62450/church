/** Request timeouts (F §1.8, §4.5). apiFetch uses timeoutFor unless the caller passes timeoutMs. */
export const DEFAULT_TIMEOUT_MS = 20_000;

/** Endpoints slower than the default, keyed "METHOD /path" (path without the query string). */
const ENDPOINT_TIMEOUTS: Record<string, number> = {
  // Creating a church copies the whole hymn catalog into it (slice 1b).
  "POST /churches": 30_000,
};

export function timeoutFor(method: string, path: string): number {
  const key = `${method.toUpperCase()} ${path.split("?")[0]}`;
  return ENDPOINT_TIMEOUTS[key] ?? DEFAULT_TIMEOUT_MS;
}
