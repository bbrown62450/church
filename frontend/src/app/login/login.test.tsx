import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { beginSignOut, isSigningOut } from "@/lib/auth";
import { peekPostLoginPath, storePostLoginPath } from "@/lib/post-login";
import { readSession, SESSION_KEYS } from "@/lib/storage";
import { setTestPath, supabaseAuth } from "@/test/mocks";

import LoginPage from "./page";

/** Renders `/login` at `path` and taps "Sign in with Google". */
async function signInFrom(path: string): Promise<void> {
  setTestPath(path);
  const user = userEvent.setup();
  render(<LoginPage />);
  await user.click(screen.getByRole("button", { name: "Sign in with Google" }));
  await waitFor(() => expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledTimes(1));
}

function callbackUrl(): string {
  return `${window.location.origin}/auth/callback`;
}

describe("/login (S Routing, proxy and login)", () => {
  it("stores an allow-listed next before it starts the Google sign-in", async () => {
    let storedWhenGoogleStarted: string | null = null;
    supabaseAuth.signInWithOAuth.mockImplementation(async () => {
      storedWhenGoogleStarted = peekPostLoginPath();
      return { data: {}, error: null };
    });

    await signInFrom("/login?next=%2Fjoin");

    expect(storedWhenGoogleStarted).toBe("/join");
    expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: callbackUrl() },
    });
  });

  it("ignores a next that safeInternalPath rejects", async () => {
    await signInFrom("/login?next=%2F%2Fevil.example");

    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: callbackUrl() },
    });
  });

  it("asks Google for its account chooser when select_account=1", async () => {
    await signInFrom("/login?next=%2Fjoin&select_account=1");

    expect(supabaseAuth.signInWithOAuth).toHaveBeenCalledWith({
      provider: "google",
      options: { redirectTo: callbackUrl(), queryParams: { prompt: "select_account" } },
    });
    expect(peekPostLoginPath()).toBe("/join");
  });

  it("clears the signing-out flag when it mounts (clarification 21)", () => {
    beginSignOut();
    expect(isSigningOut()).toBe(true);

    render(<LoginPage />);

    expect(isSigningOut()).toBe(false);
  });

  it("keeps a stored /join when a failed sign-in comes back without next (clarification 39)", async () => {
    storePostLoginPath("/join");
    const stored = readSession(SESSION_KEYS.postLoginPath);
    expect(stored).not.toBeNull();

    await signInFrom("/login?error=auth");

    expect(screen.getByText("Sign-in didn't complete. Please try again.")).toBeInTheDocument();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBe(stored);
    expect(peekPostLoginPath()).toBe("/join");
  });
});
