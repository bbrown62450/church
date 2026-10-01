/**
 * The Liturgy step's API calls (slice 4 spec, "API client usage"; F §4.4,
 * §1.8): the config is user-scoped reference data fetched once; a section is
 * written by one church-scoped POST that may take up to 100 s (owner answer
 * 2, 2026-09-30) and can be cancelled. The test fixture's config is pinned to
 * the shared fixtures 4a's API is pinned to.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { PLACEMENT_KEYS } from "@/lib/liturgy/cards";
import { installFakeApi } from "@/test/fake-api";
import { church, CHURCH_IDS, liturgyConfig, sectionResult } from "@/test/fixtures";

import { makeQueryClient, useApi } from "./client";
import { keys } from "./keys";
import { generateSection, useLiturgyConfig } from "./liturgy";

/** A shared fixture, read from the repo (the tests run in `frontend/`). */
function shared<T>(name: string): T {
  return JSON.parse(readFileSync(`${process.cwd()}/../backend/tests/fixtures/shared/${name}`, "utf-8")) as T;
}

function render<T>(hook: () => T, queryClient: QueryClient = makeQueryClient({ queries: { retry: false } })) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return { ...renderHook(hook, { wrapper: Wrapper }), queryClient };
}

describe("liturgy queries (S API client usage)", () => {
  it("loads the config once as the user, and never counts it stale", async () => {
    const api = installFakeApi({ "GET /liturgy/config": liturgyConfig() });
    const { result, queryClient } = render(() => useLiturgyConfig());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.sections).toHaveLength(8);
    expect(api.requests.map((r) => [r.method, r.path, r.headers["X-Church-Id"]])).toEqual([
      ["GET", "/liturgy/config", undefined],
    ]);
    const query = queryClient.getQueryCache().find({ queryKey: keys.liturgyConfig() });
    expect(query?.isStale()).toBe(false);
    render(() => useLiturgyConfig(), queryClient);
    expect(api.requests).toHaveLength(1);
  });

  it("writes one section as the church, waiting up to 100 seconds, and a cancel rejects as aborted", async () => {
    expect(timeoutFor("POST", "/liturgy/generate")).toBe(100_000);
    const api = installFakeApi({
      "POST /liturgy/generate": { results: [sectionResult("call_to_worship", "Leader: Come!")] },
    });
    const { result } = render(() => useApi());
    const body = { occasion: "", scriptures: [], hymns: {}, sections: ["call_to_worship" as const] };
    await expect(generateSection(result.current.church, "call_to_worship", body)).resolves.toEqual(
      sectionResult("call_to_worship", "Leader: Come!"),
    );
    expect(api.requests[0]).toMatchObject({ method: "POST", path: "/liturgy/generate", body });
    expect(api.requests[0].headers["X-Church-Id"]).toBe(CHURCH_IDS.grace);
    const controller = new AbortController();
    controller.abort();
    await expect(generateSection(result.current.church, "call_to_worship", body, controller.signal)).rejects.toMatchObject(
      new ApiError(0, "aborted", "The request was cancelled."),
    );
  });

  it("uses a test config equal to the shared fixtures 4a's API is pinned to", () => {
    const config = liturgyConfig();
    const sections = shared<{ sections: { key: string; label: string; default_enabled: boolean }[] }>("liturgy_sections.json");
    expect(config.sections.map(({ key, label, default_enabled }) => ({ key, label, default_enabled }))).toEqual(sections.sections);
    expect(config.outline).toEqual(shared<{ outline: unknown[] }>("liturgy_outline.json").outline);
    expect(config.custom_placements.map((p) => p.key)).toEqual([...PLACEMENT_KEYS]);
  });
});
