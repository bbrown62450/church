import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST_LOGIN_TTL_MS, clearPostLoginPath, peekPostLoginPath, storePostLoginPath } from "./post-login";
import { SESSION_KEYS, readSession, writeSession } from "./storage";

/** A plain in-memory Storage: the unit project runs in Node, which has no sessionStorage. */
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

/** Midday UTC on 2026-09-28, in milliseconds. */
const AT = Date.UTC(2026, 8, 28, 12, 0, 0);

beforeEach(() => {
  vi.stubGlobal("window", { sessionStorage: memoryStorage(), localStorage: memoryStorage() });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("post-login path", () => {
  it("stores {path, at}, peeks without clearing, and clears", () => {
    storePostLoginPath("/join", AT);
    expect(readSession(SESSION_KEYS.postLoginPath)).toBe(JSON.stringify({ path: "/join", at: AT }));

    expect(peekPostLoginPath(AT + 60_000)).toBe("/join");
    expect(peekPostLoginPath(AT + 60_000)).toBe("/join");

    clearPostLoginPath();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(peekPostLoginPath(AT + 60_000)).toBeNull();
  });

  it("expires 10 minutes after it was stored, and ignores a time in the future", () => {
    expect(POST_LOGIN_TTL_MS).toBe(600_000);
    storePostLoginPath("/welcome", AT);
    expect(peekPostLoginPath(AT)).toBe("/welcome");
    expect(peekPostLoginPath(AT + POST_LOGIN_TTL_MS - 1)).toBe("/welcome");
    expect(peekPostLoginPath(AT + POST_LOGIN_TTL_MS)).toBeNull();
    expect(peekPostLoginPath(AT - 1)).toBeNull();
  });

  it("ignores a stored path that safeInternalPath rejects, and never stores one", () => {
    for (const path of ["//evil.example/x", "/joinx", "/join?code=abc", "https://evil.example/join"]) {
      writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path, at: AT }));
      expect(peekPostLoginPath(AT + 1_000), path).toBeNull();
    }

    clearPostLoginPath();
    storePostLoginPath("https://evil.example/join", AT);
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
  });

  it("ignores malformed JSON and a value of the wrong shape", () => {
    // "/builder" is the raw string 1a's church-layout test seeds (church-layout.test.tsx:302).
    for (const raw of ["/builder", "{", "null", "[]", '"/join"', '{"path":"/join"}', '{"path":"/join","at":"0"}']) {
      writeSession(SESSION_KEYS.postLoginPath, raw);
      expect(peekPostLoginPath(AT), raw).toBeNull();
    }
  });
});
