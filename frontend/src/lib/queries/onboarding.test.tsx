import { QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, onTestFinished, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import { ChurchProvider } from "@/lib/church-context";
import { fakeError, installFakeApi } from "@/test/fake-api";
import { CHURCH_IDS, church, inviteAccepted, invitePreview } from "@/test/fixtures";

import { authEvents } from "./auth-events";
import { makeQueryClient } from "./client";
import { useAcceptInvite, useCreateChurch, usePreviewInvite } from "./onboarding";

const KEY = "0b9f8a52-3c1d-4e6f-9a7b-2c4d6e8f0a1b";

/** Renders `hook` inside a `ChurchProvider`, so a church header on a user-scoped call would show. */
function renderInChurch<T>(hook: () => T): { current: T } {
  const queryClient = makeQueryClient({ queries: { retry: false } });
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return renderHook(hook, { wrapper: Wrapper }).result;
}

describe("onboarding mutations", () => {
  it("useCreateChurch posts the body with the Idempotency-Key and no X-Church-Id", async () => {
    const created = church({ id: CHURCH_IDS.hope, name: "New Life", role: "owner" });
    const api = installFakeApi({ "POST /churches": { status: 201, body: created } });
    const result = renderInChurch(() => useCreateChurch());

    let data: unknown;
    await act(async () => {
      data = await result.current.mutateAsync({
        body: { name: "New Life", timezone: "America/Chicago" },
        key: KEY,
      });
    });

    expect(data).toEqual(created);
    expect(api.requests.map((req) => [req.method, req.path, req.body])).toEqual([
      ["POST", "/churches", { name: "New Life", timezone: "America/Chicago" }],
    ]);
    expect(api.requests[0].headers["Idempotency-Key"]).toBe(KEY);
    expect(api.requests[0].headers["X-Church-Id"]).toBeUndefined();
  });

  it("usePreviewInvite and useAcceptInvite post only {code}, with no key and no church header", async () => {
    const api = installFakeApi({
      "POST /invites/preview": invitePreview(),
      "POST /invites/accept": inviteAccepted(),
    });
    const preview = renderInChurch(() => usePreviewInvite());
    const accept = renderInChurch(() => useAcceptInvite());

    let previewed: unknown;
    let accepted: unknown;
    await act(async () => {
      previewed = await preview.current.mutateAsync("ABC123");
      accepted = await accept.current.mutateAsync("ABC123");
    });

    expect(previewed).toEqual(invitePreview());
    expect(accepted).toEqual(inviteAccepted());
    expect(api.requests.map((req) => [req.method, req.path, req.body])).toEqual([
      ["POST", "/invites/preview", { code: "ABC123" }],
      ["POST", "/invites/accept", { code: "ABC123" }],
    ]);
    for (const req of api.requests) {
      expect(req.headers["Idempotency-Key"]).toBeUndefined();
      expect(req.headers["X-Church-Id"]).toBeUndefined();
    }
  });

  it("a 401 from a mutation asks for sign-out (1a T18-m2)", async () => {
    installFakeApi({ "POST /invites/preview": fakeError(401, "unauthenticated", "Please sign in.") });
    const signOutRequired = vi.fn();
    onTestFinished(authEvents.onSignOutRequired(signOutRequired));
    const preview = renderInChurch(() => usePreviewInvite());

    let error: unknown;
    await act(async () => {
      error = await preview.current.mutateAsync("ABC123").catch((e: unknown) => e);
    });

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(401);
    expect(signOutRequired).toHaveBeenCalledTimes(1);
  });
});
