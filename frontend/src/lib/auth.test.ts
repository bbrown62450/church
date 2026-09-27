import { AuthApiError, AuthRetryableFetchError } from "@supabase/supabase-js";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api/client";
import { isRetryable } from "@/lib/queries/client";

import { beginSignOut, getAccessToken, resetSigningOutForTests } from "./auth";

// Node project: no setup-dom.ts here, so this file mocks the Supabase client itself.
const { getSession } = vi.hoisted(() => ({ getSession: vi.fn() }));
vi.mock("@/lib/supabase/client", () => ({ createClient: () => ({ auth: { getSession } }) }));

function session(accessToken: string | null) {
  return { data: { session: accessToken ? { access_token: accessToken } : null }, error: null };
}

afterEach(() => {
  resetSigningOutForTests();
  getSession.mockReset();
});

describe("getAccessToken", () => {
  it("returns the session's access token", async () => {
    getSession.mockResolvedValue(session("tok-1"));
    await expect(getAccessToken()).resolves.toBe("tok-1");
  });

  it("throws 401 unauthenticated when there is no session", async () => {
    getSession.mockResolvedValue(session(null));
    const error = await getAccessToken().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 401, code: "unauthenticated", message: "Please sign in." });
  });

  it("throws a retryable network_error when the token refresh could not reach Supabase", async () => {
    // auth-js 2.117: an expired access token whose refresh fails with a network error
    // yields { session: null, error } but keeps the refresh token, so this is not a sign-out.
    getSession.mockResolvedValue({
      data: { session: null },
      error: new AuthRetryableFetchError("Failed to fetch", 0),
    });
    const error = await getAccessToken().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 0,
      code: "network_error",
      message: "Can't reach the server. Check your connection and try again.",
    });
    expect(isRetryable(error)).toBe(true);
  });

  it("still throws 401 unauthenticated when the refresh failed for a non-network reason", async () => {
    getSession.mockResolvedValue({
      data: { session: null },
      error: new AuthApiError("Invalid Refresh Token: Refresh Token Not Found", 400, "refresh_token_not_found"),
    });
    await expect(getAccessToken()).rejects.toMatchObject({ status: 401, code: "unauthenticated" });
  });

  it("rejects with aborted while signing out, even when the sign-out starts during getSession", async () => {
    getSession.mockResolvedValue(session("tok-1"));
    beginSignOut();
    await expect(getAccessToken()).rejects.toMatchObject({ status: 0, code: "aborted", message: "Signing out." });
    expect(getSession).not.toHaveBeenCalled();

    resetSigningOutForTests();
    getSession.mockImplementation(async () => {
      beginSignOut();
      return session("tok-1");
    });
    await expect(getAccessToken()).rejects.toMatchObject({ status: 0, code: "aborted" });
  });
});
