import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PRUNE_AFTER_MS, pruneDrafts } from "./prune";

const NOW = new Date(Date.UTC(2026, 8, 29, 16, 0));
const DAY = 24 * 60 * 60 * 1000;

function draftJson(ageMs: number): string {
  return JSON.stringify({ version: 1, updated_at: new Date(NOW.getTime() - ageMs).toISOString() });
}

let data: Map<string, string>;

beforeEach(() => {
  data = new Map();
  const storage = {
    get length() {
      return data.size;
    },
    key: (i: number) => [...data.keys()][i] ?? null,
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
    removeItem: (k: string) => void data.delete(k),
    clear: () => data.clear(),
  };
  vi.stubGlobal("window", { localStorage: storage, sessionStorage: storage });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("pruneDrafts (F §4.6 items 3 and 4)", () => {
  it("removes this user's drafts older than 30 days, with their backups, and keeps newer or undatable ones", () => {
    expect(PRUNE_AFTER_MS).toBe(30 * DAY);
    data.set("wsb:draft:u1:c-old", draftJson(31 * DAY));
    data.set("wsb:draft-corrupt:u1:c-old", "{broken");
    data.set("wsb:draft:u1:c-recent", draftJson(29 * DAY));
    data.set("wsb:draft:u1:c-broken", "{broken");
    const removed = pruneDrafts("u1", ["c-old", "c-recent", "c-broken"], NOW);
    expect(removed).toEqual(["wsb:draft:u1:c-old"]);
    expect([...data.keys()].sort()).toEqual(["wsb:draft:u1:c-broken", "wsb:draft:u1:c-recent"]);
  });

  it("removes drafts and backups for churches the user left, and never another user's keys", () => {
    data.set("wsb:draft:u1:c-left", draftJson(DAY));
    data.set("wsb:draft-corrupt:u1:c-left", "{broken");
    data.set("wsb:draft-corrupt:u1:c-gone", "{broken");
    data.set("wsb:draft:u1:c-member", draftJson(DAY));
    data.set("wsb:draft:u2:c-left", draftJson(90 * DAY));
    data.set("activeChurchId", "c-left");
    pruneDrafts("u1", ["c-member"], NOW);
    expect([...data.keys()].sort()).toEqual(["activeChurchId", "wsb:draft:u1:c-member", "wsb:draft:u2:c-left"]);
  });

  it("removes the email dialog's remembered choices for churches the user left (slice 5b-2)", () => {
    data.set("wsb:emailPrefs:u1:c-left", "{}");
    data.set("wsb:emailPrefs:u1:c-member", "{}");
    data.set("wsb:emailPrefs:u2:c-left", "{}");
    expect(pruneDrafts("u1", ["c-member"], NOW)).toEqual(["wsb:emailPrefs:u1:c-left"]);
    expect([...data.keys()].sort()).toEqual(["wsb:emailPrefs:u1:c-member", "wsb:emailPrefs:u2:c-left"]);
  });

  it("does nothing when storage is missing or blocked", () => {
    vi.stubGlobal("window", {
      get localStorage(): Storage {
        throw new Error("SecurityError");
      },
    });
    expect(pruneDrafts("u1", [], NOW)).toEqual([]);
  });
});
