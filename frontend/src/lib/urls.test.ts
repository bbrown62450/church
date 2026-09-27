import { afterEach, describe, expect, it, vi } from "vitest";

import { buildInviteUrl, extractInviteCode, safeHttpsUrl, safeInternalPath } from "./urls";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("safeInternalPath", () => {
  it.each(["/join", "/builder/hymns", "/settings/people"])("accepts %s", (path) => {
    expect(safeInternalPath(path)).toBe(path);
  });

  it.each<[string, unknown[]]>([
    ["a protocol-relative URL", ["//evil.com", "/join//evil.com"]],
    ["a backslash, whitespace or control character", ["/\\evil.com", "/join x", "/join\t", "/join\u0000"]],
    ["an absolute URL", ["https://evil.com", "http://localhost/join"]],
    ["a scheme", ["javascript:alert(1)", "data:text/html,x"]],
    ["a first segment outside the allow-list", ["/joinx", "/", "/login", "/auth/callback"]],
    ["a query or fragment", ["/join?code=x", "/welcome#create"]],
    ["a `..` segment", ["/settings/../x", "/settings/%2e%2E/x"]],
    ["an empty or non-string value", ["", null, undefined, 42]],
    ["a path over 512 characters", ["/join/" + "a".repeat(594)]],
  ])("rejects %s", (_rule, inputs) => {
    for (const input of inputs) {
      expect(safeInternalPath(input), String(input)).toBeNull();
    }
  });
});

describe("extractInviteCode", () => {
  it("returns a raw code unchanged", () => {
    expect(extractInviteCode("Abc123_-xyz")).toBe("Abc123_-xyz");
  });

  it("reads the code from a full invite link", () => {
    expect(extractInviteCode("https://wsb.example/join?code=Abc123")).toBe("Abc123");
    expect(extractInviteCode("https://wsb.example/join?ref=mail&code=Abc123#top")).toBe("Abc123");
    expect(extractInviteCode("https://wsb.example/join")).toBe("");
  });

  it("reads the code from a link pasted without its scheme", () => {
    expect(extractInviteCode("wsb.example/join?code=Abc123")).toBe("Abc123");
  });

  it("decodes an encoded code", () => {
    expect(extractInviteCode("https://wsb.example/join?code=a%2Bb%2Fc")).toBe("a+b/c");
    expect(extractInviteCode("wsb.example/join?code=a%2Bb%2Fc")).toBe("a+b/c");
  });

  it("trims surrounding whitespace", () => {
    expect(extractInviteCode("  Abc123 \n")).toBe("Abc123");
    expect(extractInviteCode("\thttps://wsb.example/join?code=Abc123  ")).toBe("Abc123");
  });
});

describe("buildInviteUrl", () => {
  it("builds a link that extractInviteCode reads back", () => {
    const url = buildInviteUrl("a b/c+d?", "https://wsb.example");
    expect(url).toBe("https://wsb.example/join?code=a%20b%2Fc%2Bd%3F");
    expect(extractInviteCode(url)).toBe("a b/c+d?");

    vi.stubGlobal("window", { location: { origin: "https://app.example" } });
    expect(buildInviteUrl("Abc123")).toBe("https://app.example/join?code=Abc123");
  });
});

describe("safeHttpsUrl", () => {
  it("accepts an https URL", () => {
    expect(safeHttpsUrl("https://example.com/a?b=1")).toBe("https://example.com/a?b=1");
  });

  it("rejects other schemes", () => {
    for (const raw of ["http://example.com", "javascript:alert(1)", "data:text/html,x", "mailto:a@b.c"]) {
      expect(safeHttpsUrl(raw), raw).toBeNull();
    }
  });

  it("rejects values that are not absolute URLs", () => {
    for (const raw of ["", "example.com", "/join", null, 42]) {
      expect(safeHttpsUrl(raw), String(raw)).toBeNull();
    }
  });
});
