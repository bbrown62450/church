/**
 * The Hymns step's queries (S Queries, "Stale and cross-church protection";
 * F §4.4, §1.8): every request is church-scoped (`X-Church-Id`), every key
 * sits under ["church", id, "hymns"] or ["church", id, "hymnals"], the
 * suggestion call waits up to 90 s, and an older or orphaned answer is never
 * handed to the step.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { installFakeApi } from "@/test/fake-api";
import {
  church,
  CHURCH_IDS,
  gg2013,
  hymnals,
  hymnListRoute,
  hymnSuggestions,
  scriptureMatches,
} from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { useHymnals, useHymnList, useHymnLists, useScriptureMatches, useSuggestHymns } from "./hymns";
import { keys } from "./keys";

const GRACE = CHURCH_IDS.grace;
const BODY = { service_date_iso: "2026-10-04", occasion: "", exclude_recent: true };

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

/** A route that answers only when `release` is called. */
function held(answer: unknown) {
  let release!: () => void;
  const gate = new Promise<void>((resolve) => (release = resolve));
  return {
    handler: async () => {
      await gate;
      return answer;
    },
    release: () => release(),
  };
}

describe("hymn queries (S Queries)", () => {
  it("loads the hymnals and one hymnal's whole list for a service date, as the church", async () => {
    const api = installFakeApi({ "GET /hymnals": hymnals(), "GET /hymns": hymnListRoute() });
    const { result, queryClient } = render(() => ({ hymnals: useHymnals(), list: useHymnList("GG2013", "2026-10-04") }));
    await waitFor(() => expect(result.current.list.isSuccess && result.current.hymnals.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path).sort()).toEqual([
      "/hymnals",
      "/hymns?hymnal=GG2013&limit=2000&recent_for_date=2026-10-04",
    ]);
    expect(api.requests.every((r) => r.headers["X-Church-Id"] === GRACE)).toBe(true);
    expect(result.current.list.data).toEqual(gg2013());
    expect(queryClient.getQueryData(keys.hymnals(GRACE))).toEqual(hymnals());
    const listKey = keys.hymns(GRACE, { hymnal: "GG2013", limit: 2000, recent_for_date: "2026-10-04" });
    expect(queryClient.getQueryData(listKey)).toMatchObject({ total: gg2013().length });
  });

  it("sends no recent_for_date without a valid date, and nothing without a hymnal", async () => {
    const api = installFakeApi({ "GET /hymns": hymnListRoute() });
    const none = render(() => useHymnList(null, "2026-10-04"));
    expect(none.result.current.fetchStatus).toBe("idle");
    const { result } = render(() => useHymnList("GG2013", null));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests.map((r) => r.path)).toEqual(["/hymns?hymnal=GG2013&limit=2000"]);
  });

  it("useHymnLists loads each distinct hymnal once, at most four, sharing the single list's cache", async () => {
    const api = installFakeApi({ "GET /hymns": hymnListRoute({ GG2013: gg2013(), PH1990: [], A: [], B: [], C: [] }) });
    const { result } = render(() => ({
      lists: useHymnLists(["GG2013", "PH1990", null, "GG2013", "A", "B", "C"], "2026-10-04"),
      single: useHymnList("GG2013", "2026-10-04"),
    }));
    await waitFor(() => expect([...result.current.lists.lists.values()].every((l) => l !== undefined)).toBe(true));
    expect([...result.current.lists.lists.keys()]).toEqual(["GG2013", "PH1990", "A", "B"]);
    expect(api.requests.filter((r) => r.path.includes("hymnal=GG2013"))).toHaveLength(1);
    expect(result.current.single.data).toEqual(result.current.lists.lists.get("GG2013"));
    expect(result.current.lists.failed.size).toBe(0);
  });

  it("posts the scripture matches with 30 results, keyed under the hymns prefix, and not without references", async () => {
    const api = installFakeApi({ "POST /hymns/scripture-matches": scriptureMatches() });
    const idle = render(() => useScriptureMatches({ refs: [], hymnal: "GG2013", recentForDate: null, enabled: true }));
    expect(idle.result.current.fetchStatus).toBe("idle");
    const params = { refs: ["Isaiah 5:1-7"], hymnal: "GG2013", recentForDate: "2026-10-04", enabled: true };
    const { result, queryClient } = render(() => useScriptureMatches(params));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(api.requests).toHaveLength(1);
    expect(api.requests[0].body).toEqual({
      refs: ["Isaiah 5:1-7"],
      hymnal: "GG2013",
      recent_for_date: "2026-10-04",
      max_results: 30,
    });
    expect(api.requests[0].headers["X-Church-Id"]).toBe(GRACE);
    const key = keys.hymnMatches(GRACE, { refs: ["Isaiah 5:1-7"], hymnal: "GG2013", recent_for_date: "2026-10-04" });
    expect(key.slice(0, 3)).toEqual(["church", GRACE, "hymns"]);
    expect(queryClient.getQueryData(key)).toEqual(scriptureMatches());
  });

  it("posts a suggestion as the church with a 90-second timeout; Cancel's signal ends it as aborted", async () => {
    const answer = hymnSuggestions({ opening: [], response: [], closing: [] });
    const api = installFakeApi({ "POST /hymns/suggestions": answer });
    const { result } = render(() => useSuggestHymns());
    let outcome: unknown;
    await act(async () => {
      outcome = await result.current.suggest(BODY, new AbortController().signal);
    });
    expect(outcome).toEqual({ status: "ok", data: answer });
    expect(api.requests[0].body).toEqual(BODY);
    expect(api.requests[0].headers["X-Church-Id"]).toBe(GRACE);
    const cancelled = new AbortController();
    cancelled.abort();
    await act(async () => {
      outcome = await result.current.suggest(BODY, cancelled.signal);
    });
    expect(outcome).toMatchObject({ status: "error", error: { code: "aborted" } });
    expect(timeoutFor("POST", "/hymns/suggestions")).toBe(90_000);
    expect(timeoutFor("GET", "/hymns?hymnal=GG2013")).toBe(20_000);
  });

  it("never hands over an older answer after a newer request, or any answer after the step unmounts", async () => {
    const first = held(hymnSuggestions({ opening: gg2013().slice(0, 1), response: [], closing: [] }));
    const second = hymnSuggestions({ opening: gg2013().slice(2, 3), response: [], closing: [] });
    const api = installFakeApi({ "POST /hymns/suggestions": first.handler });
    const { result, unmount } = render(() => useSuggestHymns());
    let older!: Promise<unknown>;
    act(() => {
      older = result.current.suggest(BODY);
    });
    await waitFor(() => expect(result.current.isPending).toBe(true));
    api.set("POST /hymns/suggestions", second);
    let newer: unknown;
    await act(async () => {
      newer = await result.current.suggest(BODY);
    });
    expect(newer).toEqual({ status: "ok", data: second });
    first.release();
    await act(async () => {
      expect(await older).toEqual({ status: "superseded" });
    });

    const late = held(second);
    api.set("POST /hymns/suggestions", late.handler);
    let orphan!: Promise<unknown>;
    act(() => {
      orphan = result.current.suggest(BODY);
    });
    await waitFor(() => expect(api.requests).toHaveLength(3));
    unmount();
    late.release();
    expect(await orphan).toEqual({ status: "superseded" });
  });
});
