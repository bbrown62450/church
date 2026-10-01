/**
 * The card's error for each code (slice 4 spec, "Per-card error messages";
 * Testing `errors.test.ts`): the server's section messages, the client's own,
 * which ones offer Try again, and the ones that show nothing on the card.
 */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { cardErrorFrom, localAiNotConfigured } from "./errors";

describe("cardErrorFrom (S errors.ts)", () => {
  it("shows the server's message for each section error, with Try again only where trying again can help", () => {
    const cases: [string, string, boolean][] = [
      ["ai_not_configured", "AI not configured. Type this section yourself.", false],
      ["ai_busy", "The AI service is busy. Try again in a minute.", true],
      ["ai_timeout", "The AI took too long to answer. Try again.", true],
      ["ai_upstream_error", "The AI service had a problem. Try again.", true],
      [
        "prompt_invalid",
        "The Call to Worship prompt in Settings has a problem: Placeholders need a name, such as {occasion}. An admin can fix it under Settings → Liturgy prompts.",
        false,
      ],
    ];
    for (const [code, message, retryable] of cases) {
      expect(cardErrorFrom({ code, message } as never), code).toEqual({ code, message, retryable });
    }
    // The local error used when the config says AI is off has exactly the server's text.
    expect(localAiNotConfigured()).toEqual({ code: "ai_not_configured", message: cases[0][1], retryable: false });
  });

  it("words the request errors as S's table, and shows nothing for a cancel, a sign-out or a lost church", () => {
    const hymn = cardErrorFrom(
      new ApiError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."),
    );
    expect(hymn).toEqual({
      code: "not_found",
      message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
      retryable: false,
      link: { href: "/builder/hymns", label: "Go to Hymns" },
    });
    expect(
      cardErrorFrom(new ApiError(429, "rate_limited", "Too many requests. Try again in 37 seconds.", { retryAfterSeconds: 37 })),
    ).toEqual({ code: "rate_limited", message: "Too many requests — try again in 37 s.", retryable: true, retryAfterSeconds: 37 });
    expect(cardErrorFrom(new ApiError(0, "timeout", "This is taking too long. Try again."))).toEqual({
      code: "timeout",
      message: "This is taking too long. Try again.",
      retryable: true,
    });
    expect(cardErrorFrom(new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again."))).toEqual({
      code: "network_error",
      message: "Can't reach the server. Check your connection and try again.",
      retryable: true,
    });
    expect(
      cardErrorFrom(new ApiError(500, "internal_error", "Something went wrong.", { requestId: "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4" })),
    ).toEqual({ code: "internal_error", message: "Something went wrong. (Ref: 4f9a2c1e)", retryable: true });
    expect(cardErrorFrom(new ApiError(0, "aborted", "The request was cancelled."))).toBeNull();
    expect(cardErrorFrom(new ApiError(401, "unauthenticated", "Sign in again."))).toBeNull();
    expect(
      cardErrorFrom(new ApiError(403, "forbidden", "No access.", { details: { reason: "no_church_access" } })),
    ).toBeNull();
    expect(cardErrorFrom(new Error("boom"))).toEqual({ code: "unknown", message: "Something went wrong.", retryable: true });
  });

  it("offers no Try again for a 422, and keeps the server's sentence for a 503 auth_unavailable", () => {
    expect(cardErrorFrom(new ApiError(422, "invalid_request", "The request was not valid."))).toEqual({
      code: "invalid_request",
      message: "The request was not valid.",
      retryable: false,
    });
    expect(
      cardErrorFrom(
        new ApiError(503, "auth_unavailable", "Sign-in is temporarily unavailable. Try again shortly.", {
          requestId: "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4",
        }),
      ),
    ).toEqual({ code: "auth_unavailable", message: "Sign-in is temporarily unavailable. Try again shortly.", retryable: true });
  });
});
