/** `useLectionary` (S Queries; F §4.4): the key, the client, when it asks, and how long an answer keeps. */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { church, lectionary } from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { keys } from "./keys";
import { LECTIONARY_STALE_MS, PARTIAL_LECTIONARY_STALE_MS, lectionaryStaleTime, useLectionary } from "./lectionary";

/** Inside a church, so the test also shows the lookup never sends X-Church-Id. The app's own retry default. */
function renderLectionary(dateIso: string, queryClient: QueryClient = makeQueryClient()) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return { ...renderHook(() => useLectionary(dateIso), { wrapper: Wrapper }), queryClient };
}

describe("useLectionary", () => {
  it("looks the date up as the user, with no church header, under the lectionary key and a 25 s timeout", async () => {
    const api = installFakeApi({ "GET /lectionary/readings": lectionary("2026-10-04") });
    const { result, queryClient } = renderLectionary("2026-10-04");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path)).toEqual(["/lectionary/readings?date=2026-10-04"]);
    expect(api.requests[0].headers["X-Church-Id"]).toBeUndefined();
    expect(queryClient.getQueryData(keys.lectionary("2026-10-04"))).toEqual(lectionary("2026-10-04"));
    expect(timeoutFor("GET", "/lectionary/readings?date=2026-10-04")).toBe(25_000);
    expect(timeoutFor("POST", "/scripture/passages")).toBe(30_000);
  });

  it("sends nothing for an empty, impossible or out-of-range date", async () => {
    const api = installFakeApi({});
    for (const date of ["", "2026-02-30", "1899-12-31", "2200-01-01"]) {
      const { result, unmount } = renderLectionary(date);
      expect(result.current.fetchStatus).toBe("idle");
      unmount();
    }
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.requests).toEqual([]);
  });

  it("never retries a failure, and keeps a full answer a day but a partial one 5 minutes", async () => {
    const api = installFakeApi({
      "GET /lectionary/readings": fakeError(502, "upstream_error", "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes."),
    });
    const { result } = renderLectionary("2026-10-04");
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.code).toBe("upstream_error");
    expect(api.requests).toHaveLength(1);

    expect(lectionaryStaleTime(lectionary("2026-10-04"))).toBe(LECTIONARY_STALE_MS);
    expect(lectionaryStaleTime(lectionary("2026-10-04", { partial: true }))).toBe(PARTIAL_LECTIONARY_STALE_MS);
    expect(lectionaryStaleTime(undefined)).toBe(LECTIONARY_STALE_MS);
    expect([LECTIONARY_STALE_MS, PARTIAL_LECTIONARY_STALE_MS]).toEqual([86_400_000, 300_000]);
  });

  it("after a 429, a second screen looking up the same date waits for Retry-After instead of asking again", async () => {
    const api = installFakeApi({
      "GET /lectionary/readings": fakeError(429, "rate_limited", "Too many requests. Try again in 30 seconds.", {
        details: { retry_after_seconds: 30 },
      }),
    });
    const first = renderLectionary("2026-10-04");
    await waitFor(() => expect(first.result.current.error?.status).toBe(429));
    const second = renderLectionary("2026-10-04", first.queryClient);
    expect(second.result.current.error?.status).toBe(429);
    // A later lookup's request comes after anything the second mount would have sent.
    renderLectionary("2026-10-11", first.queryClient);
    await waitFor(() => expect(api.requests.map((r) => r.path)).toContain("/lectionary/readings?date=2026-10-11"));
    expect(api.requests.map((r) => r.path)).toEqual([
      "/lectionary/readings?date=2026-10-04",
      "/lectionary/readings?date=2026-10-11",
    ]);
  });
});

