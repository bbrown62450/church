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
  // Slice 4 (F §1.8 amendment, owner answer 2, 2026-09-30): a section answers within
  // 85 s (4a's 80 s deadline plus a last connect). The timer starts after getAccessToken(),
  // so the other 15 s cover the server's sign-in key fetch (at most 5 s), latency and the proxy.
  // The service reviewer's routes (the slice after 4b) reuse this value.
  "POST /liturgy/generate": 100_000,
  // The service reviewer (owner answer 3, 2026-10-01; F §1.8): a review answers within its 75 s
  // deadline plus a last connect, and a revision within generation's 85 s; the same margin.
  "POST /liturgy/review": 100_000,
  "POST /liturgy/revise": 100_000,
  // Slice 5a (F §1.8): a Word file is local work on the server, well under 3 s; 30 s covers a slow phone network.
  "POST /documents": 30_000,
  // The printed bulletin (printed bulletin spec): the readings' text within the passages' 20 s deadline, then the file.
  "POST /documents/printed": 30_000,
  // The cover picture (printed bulletin PR 3b): up to 10 MB up from a phone, then a second or two on the server.
  // 10 MB at about 1 Mbps up takes 80 s; a timed-out upload the server finished still counts toward the
  // church's pictures, so the wait is generous (build review M8).
  "POST /bulletin-images": 120_000,
  // Slice 5b-2 (F §1.8): the code exchange, then the address lookup (and, for a refused grant, a revoke).
  // Google's timeouts are per phase (5 s to connect, then 15 s for each wait), not a deadline for the call:
  // two slow but steady calls can take well over 40 s, so the browser waits 75 s (5b-2a build review M3).
  // This is the overall limit; a connect it stops waiting for shows an error, and connecting again starts afresh.
  "POST /gmail-connection": 75_000,
  // Slice 5b-2: the printed bulletin's readings (their 20 s deadline), then Google's refresh and the send,
  // whose timeouts are per phase (15 s and 30 s for each wait), not deadlines. This is the overall limit: a
  // send still unanswered then is shown as possibly sent ("We lost the connection…"), never as failed.
  "POST /bulletin-emails": 90_000,
  // Slice 6a-2 (6a spec, API; F §1.8): adding a bundled hymnal inserts up to about a thousand hymns, and the
  // dialog says "This can take up to a minute." (plan review I3). Nothing on the server stops it sooner: uvicorn
  // sets no request deadline, the app sets no statement_timeout outside migrations, and routes behind Railway
  // already answer later than that (POST /liturgy/generate, an 80 s deadline). A timed-out add may still
  // finish on the server, so a failed hymnal write refreshes the lists (lib/queries/hymn-library.ts).
  "POST /hymnals": 60_000,
  // Slice 6a-3b (6a spec, API "Client timeouts"; F §1.8): the voice-profile draft answers within its 75 s server
  // deadline, as /hymns/suggestions does, plus a last connect. Cancel stops the wait sooner; the draft is not
  // stored, so a wait given up on changes nothing.
  "POST /church/prayer-library/voice-profile-draft": 90_000,
};

export function timeoutFor(method: string, path: string): number {
  const key = `${method.toUpperCase()} ${path.split("?")[0]}`;
  return ENDPOINT_TIMEOUTS[key] ?? DEFAULT_TIMEOUT_MS;
}
