import { afterEach, describe, expect, it, vi } from "vitest";

import { apiFetch } from "./client";

function jsonFetch(status: number, body: unknown, headers: Record<string, string> = {}) {
  return vi.fn<typeof fetch>(
    async () =>
      new Response(JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json", ...headers },
      }),
  );
}

/** A fetch that never answers; it rejects like the real one when its signal aborts. */
function hangingFetch() {
  return vi.fn<typeof fetch>(
    (_url, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("The operation was aborted.", "AbortError")),
        );
      }),
  );
}

afterEach(() => {
  vi.useRealTimers();
});

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
      code: "internal_error",
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

  it("sends a JSON body with the method and Content-Type", async () => {
    const f = jsonFetch(201, { id: "c-1", name: "Grace", role: "owner" });
    await apiFetch("/churches", {
      token: "t",
      baseUrl: "",
      method: "POST",
      json: { name: "Grace", timezone: "America/Chicago" },
      fetchImpl: f,
    });
    const [, init] = f.mock.calls[0];
    expect(init?.method).toBe("POST");
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(init?.body))).toEqual({ name: "Grace", timezone: "America/Chicago" });
  });

  it("sends the Idempotency-Key header when given", async () => {
    const f = jsonFetch(201, {});
    const key = "0b0e7a4e-3f7c-4f55-9a55-8d7f0f6b2c11";
    await apiFetch("/churches", { token: "t", baseUrl: "", method: "POST", json: {}, idempotencyKey: key, fetchImpl: f });
    const headers = new Headers(f.mock.calls[0][1]?.headers);
    expect(headers.get("Idempotency-Key")).toBe(key);
    expect(headers.has("If-Match")).toBe(false);
  });

  it("sends the If-Match header when given", async () => {
    const f = jsonFetch(200, {});
    await apiFetch("/rubric", { token: "t", churchId: "c-1", baseUrl: "", method: "PATCH", json: {}, ifMatch: '"v3"', fetchImpl: f });
    const headers = new Headers(f.mock.calls[0][1]?.headers);
    expect(headers.get("If-Match")).toBe('"v3"');
    expect(headers.has("Idempotency-Key")).toBe(false);
  });

  it("times out after 20 s by default and 30 s for POST /churches", async () => {
    vi.useFakeTimers();
    const timeout = { status: 0, code: "timeout", message: "This is taking too long. Try again." };

    const get = hangingFetch();
    const me = apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: get });
    const meFailed = expect(me).rejects.toMatchObject(timeout);
    await vi.advanceTimersByTimeAsync(19_999);
    expect(get.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await meFailed;

    const post = hangingFetch();
    const create = apiFetch("/churches", { token: "t", baseUrl: "", method: "POST", json: {}, fetchImpl: post });
    const createFailed = expect(create).rejects.toMatchObject(timeout);
    await vi.advanceTimersByTimeAsync(29_999);
    expect(post.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    await createFailed;
  });

  it("maps the caller's abort to aborted", async () => {
    const f = hangingFetch();
    const controller = new AbortController();
    const pending = apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: f, signal: controller.signal });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ status: 0, code: "aborted", message: "The request was cancelled." });
  });

  it("parses fields, details and request_id from the error body", async () => {
    const invalid = jsonFetch(
      422,
      {
        error: {
          code: "invalid_request",
          message: "The request was not valid.",
          request_id: "req-body-1",
          fields: { name: "Required." },
        },
      },
      { "X-Request-Id": "req-header-1" },
    );
    await expect(apiFetch("/churches", { token: "t", baseUrl: "", fetchImpl: invalid })).rejects.toMatchObject({
      status: 422,
      code: "invalid_request",
      requestId: "req-body-1",
      fields: { name: "Required." },
    });

    const lost = jsonFetch(403, {
      error: {
        code: "forbidden",
        message: "You don't have access to this church.",
        request_id: "req-body-2",
        details: { reason: "no_church_access" },
      },
    });
    await expect(apiFetch("/church", { token: "t", baseUrl: "", fetchImpl: lost })).rejects.toMatchObject({
      status: 403,
      code: "forbidden",
      details: { reason: "no_church_access" },
      requestId: "req-body-2",
    });
  });

  it("takes requestId from X-Request-Id when the body has none", async () => {
    const f = jsonFetch(404, { error: { code: "not_found", message: "Not found." } }, { "X-Request-Id": "abcdef0123456789" });
    await expect(apiFetch("/church", { token: "t", baseUrl: "", fetchImpl: f })).rejects.toMatchObject({
      status: 404,
      code: "not_found",
      requestId: "abcdef0123456789",
    });
  });

  it("gives a code-less body internal_error at 5xx and unknown below, with the header's requestId", async () => {
    const proxy = vi.fn<typeof fetch>(
      async () => new Response("<html>Bad gateway</html>", { status: 502, headers: { "X-Request-Id": "req-proxy-1" } }),
    );
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: proxy })).rejects.toMatchObject({
      status: 502,
      code: "internal_error",
      message: "Something went wrong.",
      requestId: "req-proxy-1",
    });

    const codeless = jsonFetch(400, { detail: "Bad request" });
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: codeless })).rejects.toMatchObject({
      status: 400,
      code: "unknown",
      message: "Something went wrong.",
    });
  });

  it("parses Retry-After into retryAfterSeconds, falling back to details", async () => {
    const body = {
      error: {
        code: "rate_limited",
        message: "Slow down.",
        request_id: "req-429",
        details: { retry_after_seconds: 42 },
      },
    };
    const withHeader = jsonFetch(429, body, { "Retry-After": "42" });
    await expect(apiFetch("/churches", { token: "t", baseUrl: "", fetchImpl: withHeader })).rejects.toMatchObject({
      status: 429,
      code: "rate_limited",
      retryAfterSeconds: 42,
      details: { retry_after_seconds: 42 },
    });

    const withoutHeader = jsonFetch(429, { error: { ...body.error, details: { retry_after_seconds: 7 } } });
    await expect(apiFetch("/churches", { token: "t", baseUrl: "", fetchImpl: withoutHeader })).rejects.toMatchObject({
      retryAfterSeconds: 7,
    });
  });

  it("returns undefined for 204 and for an empty 2xx body", async () => {
    const noContent = vi.fn<typeof fetch>(async () => new Response(null, { status: 204 }));
    await expect(apiFetch("/invites/x", { token: "t", baseUrl: "", method: "DELETE", fetchImpl: noContent })).resolves.toBeUndefined();

    const empty = vi.fn<typeof fetch>(async () => new Response("", { status: 200 }));
    await expect(apiFetch("/me", { token: "t", baseUrl: "", fetchImpl: empty })).resolves.toBeUndefined();
  });
});
