import { afterEach, describe, expect, it } from "vitest";

import {
  type Church,
  isAdmin,
  markChurchExited,
  pickActiveChurch,
  resetExitedChurchesForTests,
  roleLabel,
  wasChurchExited,
} from "./church";

const churches: Church[] = [
  { id: "a", name: "Alpha", role: "owner" },
  { id: "b", name: "Beta", role: "member" },
];

describe("pickActiveChurch", () => {
  it("keeps the remembered church while the user still belongs to it", () => {
    expect(pickActiveChurch(churches, "b")?.id).toBe("b");
  });

  it("falls back to the first church when the remembered one is gone", () => {
    expect(pickActiveChurch(churches, "zzz")?.id).toBe("a");
  });

  it("falls back to the first church when nothing is remembered", () => {
    expect(pickActiveChurch(churches, null)?.id).toBe("a");
  });

  it("returns null when the user has no churches", () => {
    expect(pickActiveChurch([], "a")).toBeNull();
  });

  it("skips excluded churches and falls back to the first remaining one by name", () => {
    const three: Church[] = [
      { id: "g", name: "Grace", role: "admin" },
      { id: "b", name: "Beta", role: "member" },
      { id: "a", name: "Alpha", role: "owner" },
    ];
    expect(pickActiveChurch(three, "a", new Set(["a"]))?.id).toBe("b");
    expect(pickActiveChurch(three, "g", new Set(["a"]))?.id).toBe("g");
    expect(pickActiveChurch(three, undefined)?.id).toBe("a");
    expect(pickActiveChurch(three, "a", new Set(["a", "b", "g"]))).toBeNull();
  });
});

describe("roleLabel", () => {
  it("names each role for people", () => {
    expect((["owner", "admin", "member"] as const).map(roleLabel)).toEqual(["Owner", "Admin", "Member"]);
  });
});

describe("isAdmin", () => {
  it("lets owners and admins edit the church's settings (printed bulletin PR 2a)", () => {
    expect((["owner", "admin", "member"] as const).map(isAdmin)).toEqual([true, true, false]);
  });
});

describe("markChurchExited / wasChurchExited (slice 6b-2b)", () => {
  afterEach(() => resetExitedChurchesForTests());

  it("marks one church for 60 seconds, then forgets it", () => {
    markChurchExited("c1", 1_000);
    expect(wasChurchExited("c1", 1_000)).toBe(true);
    expect(wasChurchExited("c1", 60_999)).toBe(true);
    expect(wasChurchExited("c2", 1_000)).toBe(false);
    expect(wasChurchExited("c1", 61_000)).toBe(false);
    expect(wasChurchExited("c1", 1_000)).toBe(false); // the expired mark is gone
  });
});
