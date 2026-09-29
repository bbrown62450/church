import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ACTIVE_CHURCH_KEY,
  SESSION_KEYS,
  localKeys,
  readLocal,
  readSession,
  removeLocal,
  removeSession,
  tryWriteLocal,
  writeLocal,
  writeSession,
} from "./storage";

function memoryStorage(): Storage {
  const data = new Map<string, string>();
  return {
    get length() {
      return data.size;
    },
    clear: () => data.clear(),
    getItem: (key) => data.get(key) ?? null,
    key: (index) => [...data.keys()][index] ?? null,
    removeItem: (key) => {
      data.delete(key);
    },
    setItem: (key, value) => {
      data.set(key, String(value));
    },
  };
}

function throwingStorage(): Storage {
  const fail = () => {
    throw new Error("QuotaExceededError");
  };
  return { length: 0, clear: fail, getItem: fail, key: fail, removeItem: fail, setItem: fail };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("storage", () => {
  it("round-trips session and local values in their own areas", () => {
    vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
    expect(SESSION_KEYS).toEqual({
      pendingInviteCode: "wsb:pendingInviteCode",
      postLoginPath: "wsb:postLoginPath",
    });
    expect(ACTIVE_CHURCH_KEY).toBe("activeChurchId");

    writeSession(SESSION_KEYS.pendingInviteCode, "XYZ");
    writeLocal(ACTIVE_CHURCH_KEY, "church-1");

    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe("XYZ");
    expect(readLocal(ACTIVE_CHURCH_KEY)).toBe("church-1");
    expect(readLocal(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(readSession(ACTIVE_CHURCH_KEY)).toBeNull();
  });

  it("removes a value from one area only", () => {
    vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
    writeSession("k", "session");
    writeLocal("k", "local");

    removeSession("k");
    expect(readSession("k")).toBeNull();
    expect(readLocal("k")).toBe("local");

    removeLocal("k");
    expect(readLocal("k")).toBeNull();
  });

  it("returns null and never throws when storage is blocked or full", () => {
    vi.stubGlobal("window", {
      get sessionStorage(): Storage {
        throw new Error("SecurityError");
      },
      localStorage: throwingStorage(),
    });

    expect(readSession("k")).toBeNull();
    expect(() => writeSession("k", "v")).not.toThrow();
    expect(() => removeSession("k")).not.toThrow();
    expect(readLocal("k")).toBeNull();
    expect(() => writeLocal("k", "v")).not.toThrow();
    expect(() => removeLocal("k")).not.toThrow();
  });

  it("does nothing on the server, where there is no window", () => {
    expect(typeof window).toBe("undefined");

    expect(readSession("k")).toBeNull();
    expect(readLocal("k")).toBeNull();
    expect(() => writeSession("k", "v")).not.toThrow();
    expect(() => writeLocal("k", "v")).not.toThrow();
    expect(() => removeSession("k")).not.toThrow();
    expect(() => removeLocal("k")).not.toThrow();
  });

  it("tryWriteLocal says whether it stored the value, and localKeys lists keys (slice 2b drafts)", () => {
    vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
    expect(tryWriteLocal("wsb:draft:u:c", "{}")).toBe(true);
    writeLocal(ACTIVE_CHURCH_KEY, "c");
    writeSession("session-only", "x");
    expect(readLocal("wsb:draft:u:c")).toBe("{}");
    expect(localKeys().sort()).toEqual([ACTIVE_CHURCH_KEY, "wsb:draft:u:c"]);

    vi.stubGlobal("window", { sessionStorage: throwingStorage(), localStorage: throwingStorage() });
    expect(tryWriteLocal("k", "v")).toBe(false);
    expect(localKeys()).toEqual([]);

    vi.unstubAllGlobals();
    expect(tryWriteLocal("k", "v")).toBe(false);
    expect(localKeys()).toEqual([]);
  });
});
