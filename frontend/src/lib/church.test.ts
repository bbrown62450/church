import { describe, expect, it } from "vitest";

import { type Church, pickActiveChurch } from "./church";

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
});
