import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { ApiCall } from "@/lib/queries/client";

import { connectGmailOnce, DEFAULT_RETURN, gmailErrorMessage, isGoogleAuthUrl, parseCallbackParams, returnToFrom } from "./gmail";

describe("connecting Gmail (slice 5b-2)", () => {
  it("accepts only Google's consent page", () => {
    expect(isGoogleAuthUrl("https://accounts.google.com/o/oauth2/v2/auth?state=s")).toBe(true);
    for (const url of ["http://accounts.google.com/o/oauth2/v2/auth", "https://accounts.google.com.evil.example/",
      "https://evil.example/?https://accounts.google.com/", "javascript:alert(1)", "/o/oauth2/v2/auth", ""]) {
      expect(isGoogleAuthUrl(url), url).toBe(false);
    }
  });

  it("returns only to a page of the app, else Settings → Account", () => {
    expect(returnToFrom("/builder/review")).toBe("/builder/review");
    expect(returnToFrom("/settings/account")).toBe("/settings/account");
    for (const raw of ["//evil.com", "https://evil.com/builder", "/login", "/gmail/callback?x", null, 42]) {
      expect(returnToFrom(raw), String(raw)).toBe(DEFAULT_RETURN);
    }
  });

  it("reads Google's answer from the query string", () => {
    expect(parseCallbackParams("?code=4%2F0Ab&state=s1&scope=email")).toEqual({ code: "4/0Ab", state: "s1", error: null });
    expect(parseCallbackParams("?error=access_denied&state=s1")).toEqual({ code: null, state: "s1", error: "access_denied" });
    expect(parseCallbackParams("")).toEqual({ code: null, state: null, error: null });
    expect(parseCallbackParams("?code=&state=%20")).toEqual({ code: null, state: null, error: null });
  });

  it("posts each state once, however often it is asked", async () => {
    const answer = { configured: true, connected: true, google_email: "owner@example.com" };
    const call = vi.fn(async () => answer) as unknown as ApiCall;
    const first = connectGmailOnce(call, { code: "c", state: "state-once" });
    const second = connectGmailOnce(call, { code: "c", state: "state-once" });
    expect(second).toBe(first);
    await expect(first).resolves.toEqual(answer);
    expect(call).toHaveBeenCalledTimes(1);
    expect(call).toHaveBeenCalledWith("/gmail-connection", { method: "POST", json: { code: "c", state: "state-once" } });
    connectGmailOnce(call, { code: "c", state: "state-other" });
    expect(call).toHaveBeenCalledTimes(2);
  });

  it("says what Google's or Gmail's failure was, and anything else as every toast does", () => {
    const own = "Couldn't reach Google. Try connecting again in a minute.";
    expect(gmailErrorMessage(new ApiError(502, "upstream_error", own))).toBe(own);
    expect(gmailErrorMessage(new ApiError(503, "gmail_not_configured", "Not set up."))).toBe("Not set up.");
    expect(gmailErrorMessage(new ApiError(500, "internal_error", "boom", { requestId: "abcdef123456" }))).toBe(
      "Something went wrong. (Ref: abcdef12)",
    );
    expect(gmailErrorMessage(new ApiError(400, "gmail_state_invalid", "Expired."))).toBe("Expired.");
  });
});
