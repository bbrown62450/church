import { afterEach, describe, expect, it, vi } from "vitest";

import { resetExitedChurchesForTests, wasChurchExited } from "@/lib/church";
import type { MembershipChange } from "@/lib/queries/membership";

import { runChurchExit } from "./church-exit";

afterEach(() => resetExitedChurchesForTests());

/** A QueryClient, `membershipChanged` and `removeLocal` that write what they are asked into `log`. */
function spies(membershipChanged: (change: MembershipChange) => Promise<boolean> = async () => true) {
  const log: string[] = [];
  const queryClient = {
    cancelQueries: vi.fn(async (filters: { queryKey: readonly unknown[] }) => {
      log.push(`cancel ${JSON.stringify(filters.queryKey)} exited=${wasChurchExited("c1")}`);
    }),
    removeQueries: vi.fn((filters: { queryKey: readonly unknown[] }) => {
      log.push(`remove ${JSON.stringify(filters.queryKey)}`);
    }),
  };
  const changed = vi.fn(async (change: MembershipChange) => {
    log.push(`membershipChanged ${JSON.stringify(change)}`);
    return membershipChanged(change);
  });
  const removeLocal = vi.fn((key: string) => {
    log.push(`removeLocal ${key}`);
  });
  return { log, queryClient, changed, removeLocal };
}

describe("runChurchExit (slice 6b-2b)", () => {
  it("marks the church, cancels its requests, drops its draft keys, then /me, then its cache, in that order", async () => {
    const { log, queryClient, changed, removeLocal } = spies();
    const meLoaded = await runChurchExit({ churchId: "c1", userId: "u1", queryClient, membershipChanged: changed, removeLocal });
    expect(meLoaded).toBe(true);
    expect(log).toEqual([
      'cancel ["church","c1"] exited=true',
      "removeLocal wsb:draft:u1:c1",
      "removeLocal wsb:draft-corrupt:u1:c1",
      'membershipChanged {"selectChurchId":null}',
      'remove ["church","c1"]',
    ]);
    expect(wasChurchExited("c1")).toBe(true);
    expect(wasChurchExited("c2")).toBe(false);
  });

  it("still drops the draft keys and the cache when /me does not come back, and says so", async () => {
    const failed = spies(async () => false);
    expect(
      await runChurchExit({ churchId: "c1", userId: "u1", queryClient: failed.queryClient, membershipChanged: failed.changed, removeLocal: failed.removeLocal }),
    ).toBe(false);
    expect(failed.removeLocal.mock.calls.map(([key]) => key)).toEqual(["wsb:draft:u1:c1", "wsb:draft-corrupt:u1:c1"]);
    expect(failed.queryClient.removeQueries).toHaveBeenCalledWith({ queryKey: ["church", "c1"] });

    const threw = spies(async () => {
      throw new Error("offline");
    });
    expect(
      await runChurchExit({ churchId: "c1", userId: "u1", queryClient: threw.queryClient, membershipChanged: threw.changed, removeLocal: threw.removeLocal }),
    ).toBe(false);
    expect(threw.log.at(-1)).toBe('remove ["church","c1"]');
  });
});
