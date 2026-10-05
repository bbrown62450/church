/** `useVoices` (Voices V1 spec "The API", "The panel"): the key, the client, when it asks, how long it keeps. */
import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ChurchProvider } from "@/lib/church-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { church, voices, voicesRoute } from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { keys } from "./keys";
import { VOICES_STALE_MS, useVoices } from "./voices";

function renderVoices(reference: string | null, queryClient = makeQueryClient()) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return { ...renderHook(() => useVoices(reference), { wrapper: Wrapper }), queryClient };
}

describe("useVoices", () => {
  it("asks as the user, with no church header, under a reference key, and keeps the answer an hour", async () => {
    const api = installFakeApi({ "GET /voices": voicesRoute() });
    const { result, queryClient } = renderVoices("Luke 15:1-3, 11b-32");
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path)).toEqual(["/voices?reference=Luke%2015%3A1-3%2C%2011b-32"]);
    expect(api.requests[0].headers["X-Church-Id"]).toBeUndefined();
    expect(queryClient.getQueryData(keys.voices("Luke 15:1-3, 11b-32"))).toEqual(voices("Luke 15:1-3, 11b-32"));
    expect(keys.voices("Matthew 22:15-22")).toEqual(["ref", "voices", "Matthew 22:15-22"]);
    expect(VOICES_STALE_MS).toBe(3_600_000);
  });

  it("asks nothing without a passage", async () => {
    const api = installFakeApi({});
    const { result } = renderVoices(null);
    expect(result.current.fetchStatus).toBe("idle");
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.requests).toEqual([]);
  });

  it("asks once for a reference the server refuses, and never again this session, however it is written", async () => {
    // Voices V1 build review M4: the panel remounts as it moves between reading rows, and a query
    // in error asks again on each mount; a 422 is kept as "no passage" for the session instead.
    const api = installFakeApi({
      "GET /voices": () => fakeError(422, "invalid_request", "Matthew has 28 chapters. Check the chapter and verse."),
    });
    const queryClient = makeQueryClient();
    const first = renderVoices("Matthew 29:1", queryClient);
    await waitFor(() => expect(first.result.current.isSuccess).toBe(true));
    expect(first.result.current.data).toBeNull();
    first.unmount();
    const again = renderVoices("Matthew 29:1", queryClient);
    expect(again.result.current.data).toBeNull();
    again.unmount();
    queryClient.removeQueries();                       // even after the cache lets the query go
    const respelled = renderVoices("matthew 29 : 1", queryClient);
    expect(respelled.result.current.data).toBeNull();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.requests.map((r) => r.path)).toEqual(["/voices?reference=Matthew%2029%3A1"]);
  });

  it("keeps asking again after other failures (the panel's Try again)", async () => {
    const api = installFakeApi({ "GET /voices": () => fakeError(503, "auth_unavailable", "Down.") });
    const queryClient = makeQueryClient();
    const first = renderVoices("Matthew 22:15-22", queryClient);
    await waitFor(() => expect(first.result.current.isError).toBe(true));
    first.unmount();
    const again = renderVoices("Matthew 22:15-22", queryClient);
    await waitFor(() => expect(api.requests).toHaveLength(2));
    await waitFor(() => expect(again.result.current.isError).toBe(true));
  });
});
