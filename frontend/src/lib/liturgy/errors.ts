/**
 * What a card shows when its section could not be written (slice 4 spec,
 * "Per-card error messages", Frontend `errors.ts`; F §1.5: the client chooses
 * by `code` only). Two sources funnel through `cardErrorFrom`: a section's
 * failure inside the 200 (`SectionError`, whose message the server wrote)
 * and a failed request (`ApiError`).
 *
 * `null` means the card shows nothing: a cancel (the card returns to where it
 * was), and a 401 or a lost church, which the app's global handling already
 * acts on (sign-out, another church).
 */
import { ApiError } from "@/lib/api/client";
import { describeError, isNoChurchAccess } from "@/lib/api/errors";
import type { SectionError } from "@/lib/api/types";

export type CardError = {
  code: string;
  message: string;
  /** Shows "Try again". */
  retryable: boolean;
  /** A 429's wait: Try again is enabled after it. */
  retryAfterSeconds?: number;
  link?: { href: string; label: string };
};

export const AI_NOT_CONFIGURED_MESSAGE = "AI not configured. Type this section yourself.";

/** A 429's card message, with the seconds left to wait. */
export function rateLimitMessage(seconds: number): string {
  return `Too many requests — try again in ${seconds} s.`;
}

const RETRYABLE_SECTION_CODES: ReadonlySet<string> = new Set(["ai_busy", "ai_timeout", "ai_upstream_error"]);

/** The error marked on a card locally when the config says AI is off; the same text as the server's. */
export function localAiNotConfigured(): CardError {
  return { code: "ai_not_configured", message: AI_NOT_CONFIGURED_MESSAGE, retryable: false };
}

function isSectionError(e: unknown): e is SectionError {
  return (
    typeof e === "object" && e !== null && !(e instanceof Error) && typeof (e as SectionError).code === "string" &&
    typeof (e as SectionError).message === "string"
  );
}

export function cardErrorFrom(e: unknown): CardError | null {
  if (isSectionError(e)) return { code: e.code, message: e.message, retryable: RETRYABLE_SECTION_CODES.has(e.code) };
  if (!(e instanceof ApiError)) return { code: "unknown", message: "Something went wrong.", retryable: true };
  if (e.code === "aborted" || e.status === 401 || isNoChurchAccess(e)) return null;
  switch (e.code) {
    case "not_found":
      return {
        code: e.code,
        message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        retryable: false,
        link: { href: "/builder/hymns", label: "Go to Hymns" },
      };
    case "rate_limited":
      return e.retryAfterSeconds === undefined
        ? { code: e.code, message: e.message, retryable: true }
        : {
            code: e.code,
            message: rateLimitMessage(e.retryAfterSeconds),
            retryable: true,
            retryAfterSeconds: e.retryAfterSeconds,
          };
    case "ai_not_configured":
    case "prompt_invalid":
    // A 422 is the same request each time: trying again cannot help.
    case "invalid_request":
      return { code: e.code, message: e.message, retryable: false };
    case "auth_unavailable":
      // The server's own sentence ("Sign-in is temporarily unavailable. Try again shortly.") says what happened.
      return { code: e.code, message: e.message, retryable: true };
    default:
      // timeout and network_error carry their own full sentences; a 5xx reads "Something went wrong. (Ref: …)".
      return { code: e.code, message: e.status >= 500 ? describeError(e) : e.message, retryable: true };
  }
}
