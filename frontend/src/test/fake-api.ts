/**
 * A fake API server for tests (F §5.2): `installFakeApi({ "GET /me": me(), ... })`
 * stubs global `fetch` for the current test.
 *
 * - Routes are "METHOD /path". A request matches its exact path with the query
 *   string first, then the path without it.
 * - A handler is either a response body (sent as 200 JSON) or a function of the
 *   recorded request that returns a body or a `FakeResponse`, possibly after an
 *   `await` (a delayed response). A `FakeResponse` is a plain object with a numeric
 *   `status` and no keys other than `status`, `body` and `headers`; build error
 *   responses with `fakeError`. A real `Response` (a file, slice 5a) is returned
 *   as it is.
 * - Every request is recorded (at call time, before any delay) with lower-case
 *   header names; header lookups on a recorded request ignore case.
 * - An aborted `signal` rejects the call with the signal's reason, as `fetch` does.
 * - A request with no handler rejects, and fails the test when it finishes, even
 *   if the UI swallowed the error. The stub is removed when the test finishes.
 */
import { onTestFinished, vi } from "vitest";

export type RecordedRequest = {
  method: string;
  path: string;
  headers: Record<string, string>;
  body: unknown;
};

export type FakeResponse = {
  status: number;
  body?: unknown;
  headers?: Record<string, string>;
};

/** A body (sent as 200 JSON), or a function returning a body or a `FakeResponse`. */
export type FakeHandler =
  | unknown
  | ((req: RecordedRequest) => FakeResponse | Promise<FakeResponse> | unknown);

export type FakeApi = {
  /** Every request so far, in call order. */
  requests: RecordedRequest[];
  /** Adds or replaces the handler for a route, e.g. `api.set("GET /me", fakeError(...))`. */
  set(route: string, handler: FakeHandler): void;
};

/** The `request_id` `fakeError` uses unless told otherwise (a uuid4 hex, like the API's). */
export const FAKE_REQUEST_ID = "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4";

/** An error response in the API's error body shape (F §1.4), with its `X-Request-Id` header. */
export function fakeError(
  status: number,
  code: string,
  message: string,
  extra: { details?: Record<string, unknown>; fields?: Record<string, string>; request_id?: string } = {},
): FakeResponse {
  const { request_id = FAKE_REQUEST_ID, fields, details } = extra;
  const error: Record<string, unknown> = { code, message, request_id };
  if (fields) error.fields = fields;
  if (details) error.details = details;
  return { status, body: { error }, headers: { "X-Request-Id": request_id } };
}

const RESPONSE_KEYS = new Set(["status", "body", "headers"]);

function isFakeResponse(value: unknown): value is FakeResponse {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return false;
  const keys = Object.keys(value);
  return (
    keys.includes("status") &&
    typeof (value as { status: unknown }).status === "number" &&
    keys.every((key) => RESPONSE_KEYS.has(key))
  );
}

function caseInsensitive(headers: Record<string, string>): Record<string, string> {
  return new Proxy(headers, {
    get: (target, prop) =>
      typeof prop === "string" ? target[prop.toLowerCase()] : Reflect.get(target, prop),
    has: (target, prop) =>
      typeof prop === "string" ? prop.toLowerCase() in target : Reflect.has(target, prop),
    getOwnPropertyDescriptor: (target, prop) =>
      Reflect.getOwnPropertyDescriptor(target, typeof prop === "string" ? prop.toLowerCase() : prop),
  });
}

function record(input: RequestInfo | URL, init: RequestInit | undefined): RecordedRequest {
  const request = input instanceof Request ? input : undefined;
  const url = new URL(request ? request.url : String(input), "http://localhost");
  const headers: Record<string, string> = {};
  new Headers(init?.headers ?? request?.headers).forEach((value, name) => {
    headers[name] = value;
  });
  let body: unknown = init?.body ?? undefined;
  if (typeof body === "string") {
    try {
      body = JSON.parse(body);
    } catch {
      // Not JSON: keep the raw string.
    }
  }
  return {
    method: (init?.method ?? request?.method ?? "GET").toUpperCase(),
    path: url.pathname + url.search,
    headers: caseInsensitive(headers),
    body,
  };
}

function toResponse(result: unknown): Response {
  if (result instanceof Response) return result;
  const { status, body, headers = {} } = isFakeResponse(result) ? result : { status: 200, body: result };
  const empty = body === undefined || status === 204 || status === 205 || status === 304;
  return new Response(empty ? null : JSON.stringify(body), {
    status,
    headers: empty ? headers : { "Content-Type": "application/json", ...headers },
  });
}

function abortReason(signal: AbortSignal): unknown {
  return signal.reason ?? new DOMException("This operation was aborted", "AbortError");
}

export function installFakeApi(handlers: Record<string, FakeHandler>): FakeApi {
  const routes = new Map<string, FakeHandler>(Object.entries(handlers));
  const requests: RecordedRequest[] = [];
  const unhandled: string[] = [];

  async function fakeFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const req = record(input, init);
    requests.push(req);
    const signal = init?.signal ?? (input instanceof Request ? input.signal : undefined);
    if (signal?.aborted) throw abortReason(signal);

    const pathOnly = req.path.split("?")[0];
    const route = [`${req.method} ${req.path}`, `${req.method} ${pathOnly}`].find((key) => routes.has(key));
    if (route === undefined) {
      unhandled.push(`${req.method} ${req.path}`);
      throw new TypeError(`installFakeApi: no handler for ${req.method} ${req.path}`);
    }
    const handler = routes.get(route);
    const pending = Promise.resolve(typeof handler === "function" ? handler(req) : handler);
    if (!signal) return toResponse(await pending);
    return new Promise<Response>((resolve, reject) => {
      const onAbort = () => reject(abortReason(signal));
      signal.addEventListener("abort", onAbort, { once: true });
      pending.then(
        (result) => {
          signal.removeEventListener("abort", onAbort);
          if (signal.aborted) reject(abortReason(signal));
          else resolve(toResponse(result));
        },
        (error: unknown) => {
          signal.removeEventListener("abort", onAbort);
          reject(error);
        },
      );
    });
  }

  vi.stubGlobal("fetch", vi.fn(fakeFetch));
  onTestFinished(() => {
    vi.unstubAllGlobals();
    if (unhandled.length > 0) {
      throw new Error(`installFakeApi: requests without a handler: ${unhandled.join(", ")}`);
    }
  });

  return {
    requests,
    set(route, handler) {
      routes.set(route, handler);
    },
  };
}
