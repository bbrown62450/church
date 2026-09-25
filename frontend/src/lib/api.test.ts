import { describe, expect, it, vi } from "vitest";

import { apiFetch } from "./api";

function jsonFetch(status: number, body: unknown) {
  return vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  );
}

describe("apiFetch", () => {
  it("strips a trailing slash from baseUrl before joining the path", async () => {
    const f = jsonFetch(200, { ok: true });
    await apiFetch("/church", { token: "t", baseUrl: "https://api.test/", fetchImpl: f });
    const [url] = f.mock.calls[0];
    expect(url).toBe("https://api.test/church");
  });

  it("strips multiple trailing slashes from baseUrl", async () => {
    const f = jsonFetch(200, { ok: true });
    await apiFetch("/church", { token: "t", baseUrl: "https://api.test///", fetchImpl: f });
    const [url] = f.mock.calls[0];
    expect(url).toBe("https://api.test/church");
  });

  it("sends the bearer token and church id", async () => {
    const f = jsonFetch(200, { ok: true });
    await apiFetch("/church", { token: "t0k", churchId: "c-1", baseUrl: "https://api.test", fetchImpl: f });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("https://api.test/church");
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer t0k");
    expect(headers.get("X-Church-Id")).toBe("c-1");
  });

  it("omits X-Church-Id when no church is selected", async () => {
    const f = jsonFetch(200, {});
    await apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f });
    const headers = new Headers(f.mock.calls[0][1]?.headers);
    expect(headers.has("X-Church-Id")).toBe(false);
  });

  it("returns the parsed JSON body on success", async () => {
    const f = jsonFetch(200, { ok: true });
    await expect(apiFetch("/health", { token: "t", baseUrl: "", fetchImpl: f })).resolves.toEqual({ ok: true });
  });

  it("throws ApiError with the server's code and message", async () => {
    const f = jsonFetch(403, { error: { code: "forbidden", message: "No access" } });
    await expect(apiFetch("/church", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      name: "ApiError",
      status: 403,
      code: "forbidden",
      message: "No access",
    });
  });

  it("uses a generic error when the body isn't JSON", async () => {
    const f = vi.fn<typeof fetch>(async () => new Response("Bad gateway", { status: 502 }));
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      status: 502,
      code: "error",
      message: "Something went wrong.",
    });
  });

  it("maps network failures to status 0", async () => {
    const f = vi.fn<typeof fetch>(async () => {
      throw new TypeError("fetch failed");
    });
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      status: 0,
      code: "network_error",
    });
  });
});
