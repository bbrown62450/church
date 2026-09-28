import { ApiError } from "./client";

// Re-exported so a caller can import the class next to the helpers below.
export { ApiError };

/**
 * Server error codes: exactly the keys of backend `domain_errors.ERROR_CODES`
 * (F §1.5, 29 codes, grouped by status). backend/tests/test_error_registry.py
 * reads this union as text and fails when the two differ, so keep one quoted
 * code per line and no quotes or semicolons in the comments inside it.
 */
export type ServerErrorCode =
  // 400
  | "bad_request"
  | "invite_rejected"
  | "gmail_state_invalid"
  | "gmail_connect_failed"
  // 401
  | "unauthenticated"
  // 403
  | "forbidden"
  // 404
  | "not_found"
  // 405
  | "method_not_allowed"
  // 409
  | "conflict"
  | "last_admin"
  | "owner_must_transfer"
  | "invite_exists"
  | "gmail_not_connected"
  // 422
  | "invalid_request"
  | "prompt_invalid"
  | "idempotency_mismatch"
  | "invalid_rubric"
  // 429
  | "rate_limited"
  // 500
  | "internal_error"
  // 502
  | "upstream_error"
  | "ai_upstream_error"
  | "gmail_send_failed"
  // 503
  | "auth_unavailable"
  | "ai_not_configured"
  | "ai_busy"
  | "gmail_not_configured"
  | "db_unavailable"
  // 504
  | "upstream_timeout"
  | "ai_timeout";

/**
 * Codes only the client produces: network_error, timeout and aborted (status 0),
 * and unknown for an error body without a code below 500 (500 and up get
 * internal_error).
 */
export type ClientErrorCode = "network_error" | "timeout" | "aborted" | "unknown";

export type ApiErrorCode = ServerErrorCode | ClientErrorCode;

/** `details.reason` of a 400 `invite_rejected` (backend `InviteRejectReason`, slice 1b). */
export type InviteRejectReason =
  | "unknown"
  | "revoked"
  | "expired"
  | "used"
  | "church_unavailable"
  | "email_mismatch";

/** A `require_church` 403: the user is not (or no longer) a member of the church sent in X-Church-Id. */
export function isNoChurchAccess(e: unknown): boolean {
  return e instanceof ApiError && e.code === "forbidden" && e.details?.reason === "no_church_access";
}

/** The sentence an error state shows for any thrown value. */
export function describeError(e: unknown): string {
  if (!(e instanceof ApiError)) return "Something went wrong.";
  if (e.code === "network_error") return "Can't reach the server.";
  if (e.status >= 500) {
    return e.requestId ? `Something went wrong. (Ref: ${e.requestId.slice(0, 8)})` : "Something went wrong.";
  }
  return e.message;
}
