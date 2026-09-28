import type { QueryClient, QueryKey } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { ApiErrorCode } from "@/lib/api/errors";
import { beginSignOut, resetSigningOutForTests } from "@/lib/auth";

import { authEvents } from "./auth-events";
import { isRetryable, makeQueryClient } from "./client";
import { keys } from "./keys";

// Node project: no setup-dom.ts here. lib/auth imports the Supabase client, which these tests never call.
vi.mock("@/lib/supabase/client", () => ({
  createClient: () => {
    throw new Error("queries/client.test.ts must not reach Supabase");
  },
}));

const noChurchAccess = () =>
  new ApiError(403, "forbidden", "You don't have access to this church.", {
    details: { reason: "no_church_access" },
  });

describe("isRetryable", () => {
  it.each<[number, ApiErrorCode]>([
    [0, "network_error"],
    [0, "timeout"],
    [500, "internal_error"],
    [502, "upstream_error"],
    [503, "db_unavailable"],
  ])("retries %i %s", (status, code) => {
    expect(isRetryable(new ApiError(status, code, "x"))).toBe(true);
  });

  it.each<[number, ApiErrorCode]>([
    [0, "aborted"],
    [400, "bad_request"],
    [401, "unauthenticated"],
    [403, "forbidden"],
    [422, "invalid_request"],
    [429, "rate_limited"],
  ])("never retries %i %s", (status, code) => {
    expect(isRetryable(new ApiError(status, code, "x"))).toBe(false);
  });
});

describe("handleAuthErrors (through makeQueryClient's caches)", () => {
  let client: QueryClient;
  let events: string[];
  let unsubscribe: Array<() => void>;

  beforeEach(() => {
    client = makeQueryClient();
    events = [];
    unsubscribe = [
      authEvents.onSignOutRequired(() => events.push("signOutRequired")),
      authEvents.onChurchAccessLost((id) => events.push(`churchAccessLost:${id}`)),
    ];
  });

  afterEach(() => {
    for (const off of unsubscribe) off();
    client.clear();
    resetSigningOutForTests();
  });

  async function failQuery(queryKey: QueryKey, error: ApiError): Promise<void> {
    await expect(client.fetchQuery({ queryKey, queryFn: () => Promise.reject(error) })).rejects.toBe(error);
  }

  async function failMutation(meta: Record<string, unknown> | undefined, error: ApiError): Promise<void> {
    const mutation = client.getMutationCache().build(client, { mutationFn: () => Promise.reject(error), meta });
    await expect(mutation.execute(undefined)).rejects.toBe(error);
  }

  it("asks for sign-out on a 401 from any query", async () => {
    await failQuery(keys.me(), new ApiError(401, "unauthenticated", "Please sign in."));
    expect(events).toEqual(["signOutRequired"]);
  });

  it("reports no_church_access with the church id from the query key", async () => {
    await failQuery(keys.churchProfile("c-1"), noChurchAccess());
    expect(events).toEqual(["churchAccessLost:c-1"]);
  });

  it("reports no_church_access with the church id from the mutation's meta", async () => {
    await failMutation({ churchId: "c-2" }, noChurchAccess());
    expect(events).toEqual(["churchAccessLost:c-2"]);
  });

  it("emits nothing for a role 403", async () => {
    const roleError = new ApiError(403, "forbidden", "Only church admins can do this.");
    await failQuery(keys.churchProfile("c-1"), roleError);
    await failMutation({ churchId: "c-1" }, roleError);
    expect(events).toEqual([]);
  });

  it("emits nothing while signing out", async () => {
    beginSignOut();
    await failQuery(keys.me(), new ApiError(401, "unauthenticated", "Please sign in."));
    await failQuery(keys.churchProfile("c-1"), noChurchAccess());
    await failMutation({ churchId: "c-1" }, noChurchAccess());
    expect(events).toEqual([]);
  });
});
