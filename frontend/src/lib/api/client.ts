import type { ApiErrorCode } from "./errors";
import { timeoutFor } from "./timeouts";

export type ApiErrorExtra = {
  fields?: Record<string, string>;
  requestId?: string;
  retryAfterSeconds?: number;
  details?: Record<string, unknown>;
};

/** A failed API call: the server's error body (F §1.5), or a client code with status 0. */
export class ApiError extends Error {
  status: number;
  code: ApiErrorCode;
  fields?: Record<string, string>;
  requestId?: string;
  retryAfterSeconds?: number;
  details?: Record<string, unknown>;

  constructor(status: number, code: ApiErrorCode, message: string, extra: ApiErrorExtra = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = extra.fields;
    this.requestId = extra.requestId;
    this.retryAfterSeconds = extra.retryAfterSeconds;
    this.details = extra.details;
  }
}

export type ApiOptions = {
  token: string;
  churchId?: string | null;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Sent as JSON.stringify(json) with Content-Type: application/json. */
  json?: unknown;
  idempotencyKey?: string;
  ifMatch?: string;
  /** Default: timeoutFor(method, path) from ./timeouts (20 s; POST /churches 30 s). */
  timeoutMs?: number;
  signal?: AbortSignal;
  init?: RequestInit;
  baseUrl?: string;
  fetchImpl?: typeof fetch;
};

const GENERIC_MESSAGE = "Something went wrong.";
/** Also used by `getAccessToken` when a token refresh cannot reach Supabase. */
export const NETWORK_MESSAGE = "Can't reach the server. Check your connection and try again.";
const TIMEOUT_MESSAGE = "This is taking too long. Try again.";
const ABORTED_MESSAGE = "The request was cancelled.";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function retryAfterSeconds(res: Response, details: Record<string, unknown> | undefined): number | undefined {
  const header = res.headers.get("Retry-After");
  if (header !== null && /^\d+$/.test(header.trim())) return Number(header.trim());
  const fromBody = details?.retry_after_seconds;
  return typeof fromBody === "number" ? fromBody : undefined;
}

/** The ApiError for a non-2xx response whose body has been read as text. */
function errorFromResponse(res: Response, text: string): ApiError {
  let error: Record<string, unknown> = {};
  try {
    const parsed: unknown = JSON.parse(text);
    if (isRecord(parsed) && isRecord(parsed.error)) error = parsed.error;
  } catch {
    // Non-JSON error body (e.g. a proxy's HTML page); keep the generic message.
  }
  const code =
    typeof error.code === "string"
      ? (error.code as ApiErrorCode)
      : res.status >= 500
        ? "internal_error"
        : "unknown";
  const message = typeof error.message === "string" ? error.message : GENERIC_MESSAGE;
  const details = isRecord(error.details) ? error.details : undefined;
  return new ApiError(res.status, code, message, {
    fields: isRecord(error.fields) ? (error.fields as Record<string, string>) : undefined,
    requestId: typeof error.request_id === "string" ? error.request_id : (res.headers.get("X-Request-Id") ?? undefined),
    retryAfterSeconds: retryAfterSeconds(res, details),
    details,
  });
}

/**
 * Sends one request with the shared headers, timeout and abort (F §4.5) and
 * reads the body with `read` before the timer stops, so a stalled body also
 * times out. A failure to send or read is `timeout`, `aborted` or
 * `network_error` (status 0).
 */
async function send<B>(path: string, opts: ApiOptions, read: (res: Response) => Promise<B>): Promise<{ res: Response; body: B }> {
  const {
    token,
    churchId,
    json,
    idempotencyKey,
    ifMatch,
    init,
    baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "",
    fetchImpl = fetch,
  } = opts;
  const method = opts.method ?? init?.method ?? "GET";
  const timeoutMs = opts.timeoutMs ?? timeoutFor(method, path);
  const callerSignal = opts.signal ?? init?.signal ?? undefined;

  const headers = new Headers(init?.headers);
  headers.set("Authorization", `Bearer ${token}`);
  if (churchId) headers.set("X-Church-Id", churchId);
  if (idempotencyKey) headers.set("Idempotency-Key", idempotencyKey);
  if (ifMatch) headers.set("If-Match", ifMatch);
  let body = init?.body;
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(json);
  }

  // One controller serves the timeout and the caller's signal, combined by hand:
  // older iOS Safari has no AbortSignal.any (F §4.5).
  const controller = new AbortController();
  let timedOut = false;
  const timer = setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);
  const onCallerAbort = () => controller.abort();
  if (callerSignal?.aborted) controller.abort();
  else callerSignal?.addEventListener("abort", onCallerAbort);

  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  try {
    const res = await fetchImpl(`${normalizedBaseUrl}${path}`, {
      ...init,
      method,
      headers,
      body,
      signal: controller.signal,
    });
    return { res, body: await read(res) };
  } catch {
    if (timedOut) throw new ApiError(0, "timeout", TIMEOUT_MESSAGE);
    if (controller.signal.aborted) throw new ApiError(0, "aborted", ABORTED_MESSAGE);
    throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  } finally {
    clearTimeout(timer);
    callerSignal?.removeEventListener("abort", onCallerAbort);
  }
}

/** Call the FastAPI backend. The server re-checks the church on every request. */
export async function apiFetch<T>(path: string, opts: ApiOptions): Promise<T> {
  const { res, body: text } = await send(path, opts, (r) => (r.status === 204 ? Promise.resolve("") : r.text()));
  if (res.ok) {
    if (!text) return undefined as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      // A proxy or captive portal answering 200 with HTML: still an ApiError.
      throw new ApiError(res.status, "internal_error", GENERIC_MESSAGE, {
        requestId: res.headers.get("X-Request-Id") ?? undefined,
      });
    }
  }
  throw errorFromResponse(res, text);
}

/** A file from the API (`POST /documents`, slice 5a) and the name its `Content-Disposition` gives, if any. */
export type BlobResult = { blob: Blob; filename: string | null };

/**
 * `apiFetch` for a route that answers with a file (F §1.9, §4.5): the same
 * headers, timeout, abort and error mapping; a 2xx returns the bytes and the
 * server's filename; an error body is read as JSON into an `ApiError`.
 */
export async function apiFetchBlob(path: string, opts: ApiOptions): Promise<BlobResult> {
  const { res, body } = await send<Blob | string>(path, opts, (r) => (r.ok ? r.blob() : r.text()));
  if (!res.ok) throw errorFromResponse(res, typeof body === "string" ? body : "");
  return { blob: body as Blob, filename: parseContentDispositionFilename(res.headers.get("Content-Disposition")) };
}

/**
 * The filename in a `Content-Disposition` header: `filename*=UTF-8''…` decoded
 * first, else `filename="…"` (or unquoted), else null.
 */
export function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;
  const encoded = /filename\*\s*=\s*UTF-8''([^;\s]+)/i.exec(header);
  if (encoded) {
    try {
      return decodeURIComponent(encoded[1]);
    } catch {
      // A malformed escape: fall back to the plain name.
    }
  }
  const plain = /filename\s*=\s*(?:"([^"]*)"|([^;\s]+))/i.exec(header);
  const name = (plain?.[1] ?? plain?.[2] ?? "").trim();
  return name === "" ? null : name;
}
