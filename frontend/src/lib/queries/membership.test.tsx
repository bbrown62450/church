import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import type { Me } from "@/lib/api/types";
import { storeChurchId } from "@/lib/church";
import { ACTIVE_CHURCH_KEY } from "@/lib/storage";
import { type FakeApi, fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, me } from "@/test/fixtures";
import { testRouter } from "@/test/mocks";

import { makeQueryClient } from "./client";
import { keys } from "./keys";
import { useMembershipChanged } from "./membership";

const GRACE = church();
const HOPE = church({ id: CHURCH_IDS.hope, name: "Hope", role: "owner" });

/**
 * The hook on its own: no `useMe` observer is mounted, so nothing lends `["me"]`
 * a `queryFn` (the hook must bring its own, `meQueryOptions`).
 */
function renderMembershipChanged(queryClient: QueryClient = makeQueryClient({ queries: { retry: false } })) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  }
  const { result } = renderHook(() => useMembershipChanged(), { wrapper: Wrapper });
  return { changed: result.current, queryClient };
}

function meRequestCount(api: FakeApi): number {
  return api.requests.filter((req) => req.method === "GET" && req.path === "/me").length;
}

function storedChurchId(): string | null {
  return window.localStorage.getItem(ACTIVE_CHURCH_KEY);
}

describe("useMembershipChanged", () => {
  it("with no useMe mounted, stores the id and has the new /me before replace('/')", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [GRACE, HOPE] }) });
    const { changed, queryClient } = renderMembershipChanged();
    let atReplace: { meRequests: number; stored: string | null; cached: Me | undefined } | undefined;
    testRouter.replace.mockImplementation(() => {
      atReplace = {
        meRequests: meRequestCount(api),
        stored: storedChurchId(),
        cached: queryClient.getQueryData<Me>(keys.me()),
      };
    });

    await act(() => changed({ selectChurchId: CHURCH_IDS.hope }));

    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
    expect(atReplace).toEqual({
      meRequests: 1,
      stored: CHURCH_IDS.hope,
      cached: me({ churches: [GRACE, HOPE] }),
    });
  });

  it("refetches a /me cached moments ago (staleTime: 0)", async () => {
    const api = installFakeApi({ "GET /me": me({ churches: [GRACE, HOPE] }) });
    const queryClient = makeQueryClient({ queries: { retry: false } });
    queryClient.setQueryData(keys.me(), me()); // just loaded: well inside the 30 s staleTime
    const { changed } = renderMembershipChanged(queryClient);

    await act(() => changed({ selectChurchId: CHURCH_IDS.hope }));

    expect(meRequestCount(api)).toBe(1);
    expect(queryClient.getQueryData<Me>(keys.me())?.churches.map((c) => c.name)).toEqual(["Grace", "Hope"]);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("goes to /welcome when /me lists no church", async () => {
    installFakeApi({ "GET /me": me({ churches: [] }) });
    const { changed } = renderMembershipChanged();

    await act(() => changed({}));

    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/welcome");
    expect(storedChurchId()).toBeNull();
  });

  it("selectChurchId: null stores nothing and keeps the stored church", async () => {
    const api = installFakeApi({ "GET /me": me() });
    storeChurchId(CHURCH_IDS.grace);
    const { changed } = renderMembershipChanged();

    await act(() => changed({ selectChurchId: null }));

    expect(storedChurchId()).toBe(CHURCH_IDS.grace);
    expect(meRequestCount(api)).toBe(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });

  it("a failed /me resets the cached /me, keeps the stored id and still goes to /", async () => {
    const api = installFakeApi({ "GET /me": fakeError(500, "internal_error", "Something went wrong.") });
    const queryClient = makeQueryClient({ queries: { retry: false } });
    queryClient.setQueryData(keys.me(), me()); // the old list, without Hope
    const { changed } = renderMembershipChanged(queryClient);

    await act(() => changed({ selectChurchId: CHURCH_IDS.hope })); // resolves: the change itself succeeded

    expect(meRequestCount(api)).toBe(1);
    expect(queryClient.getQueryData(keys.me())).toBeUndefined();
    expect(storedChurchId()).toBe(CHURCH_IDS.hope);
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
    expect(testRouter.replace).toHaveBeenCalledWith("/");
  });
});
