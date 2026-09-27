import { screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { isSigningOut, type SignOutOptions, useSignOut } from "@/lib/auth";
import { readStoredChurchId, storeChurchId } from "@/lib/church";
import { useMeContext } from "@/lib/me-context";
import { keys } from "@/lib/queries/keys";
import { readSession, SESSION_KEYS, writeSession } from "@/lib/storage";
import { church, me } from "@/test/fixtures";
import { supabaseAuth, testRouter } from "@/test/mocks";
import { renderWithProviders } from "@/test/render";

/** Stands in for the account menu's "Log out": reads `/me` from `MeProvider`, signs out with `options`. */
function LogOut({ options }: { options?: SignOutOptions }) {
  const { user } = useMeContext();
  const signOut = useSignOut();
  return (
    <button type="button" onClick={() => void signOut(options)}>
      Log out {user.email}
    </button>
  );
}

/** What a signed-in tab holds: a stored church, a pending invite and a post-login path. */
function seedSignedInTab(): void {
  storeChurchId(church().id);
  writeSession(SESSION_KEYS.pendingInviteCode, "INVITE-CODE");
  writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path: "/welcome", at: 0 }));
}

/** The names of the cookies jsdom's `document` holds now. */
function cookieNames(): string[] {
  return document.cookie
    .split(";")
    .map((pair) => pair.split("=", 1)[0].trim())
    .filter(Boolean);
}

/** The chunked session cookies `@supabase/ssr`'s browser client writes, plus one that is not Supabase's. */
function seedAuthCookies(): void {
  document.cookie = "sb-testref-auth-token.0=base64-chunk-zero; path=/";
  document.cookie = "sb-testref-auth-token.1=chunk-one; path=/";
  document.cookie = "unrelated=keep; path=/";
}

afterEach(() => {
  for (const name of cookieNames()) document.cookie = `${name}=; path=/; max-age=0`;
});

describe("useSignOut", () => {
  it("raises the flag first, clears the cache, stored church and wsb: keys, signs out locally, then goes to /login", async () => {
    seedSignedInTab();
    const pat = me();
    const { user, queryClient } = renderWithProviders(<LogOut />, { me: pat });
    queryClient.setQueryData(keys.me(), pat);
    queryClient.setQueryData(keys.churchProfile(church().id), church());
    const clear = queryClient.clear.bind(queryClient);
    let signingOutWhenCleared: boolean | undefined;
    vi.spyOn(queryClient, "clear").mockImplementation(() => {
      signingOutWhenCleared = isSigningOut();
      clear();
    });

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(signingOutWhenCleared).toBe(true);
    expect(queryClient.getQueryCache().getAll()).toEqual([]);
    expect(readStoredChurchId()).toBeNull();
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBeNull();
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(supabaseAuth.signOut).toHaveBeenCalledTimes(1);
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(supabaseAuth.signOut.mock.invocationCallOrder[0]).toBeLessThan(
      testRouter.replace.mock.invocationCallOrder[0],
    );
    expect(testRouter.replace).toHaveBeenCalledTimes(1);
  });

  it("keeps the pending invite and returns to an allow-listed path when asked (the 401 path)", async () => {
    seedSignedInTab();
    const pat = me();
    const { user } = renderWithProviders(
      <LogOut options={{ keepPendingInvite: true, next: "/welcome" }} />,
      { me: pat, path: "/welcome" },
    );

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login?next=%2Fwelcome"));
    expect(readSession(SESSION_KEYS.pendingInviteCode)).toBe("INVITE-CODE");
    expect(readSession(SESSION_KEYS.postLoginPath)).toBeNull();
    expect(readStoredChurchId()).toBeNull();
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(isSigningOut()).toBe(true);
  });

  it("removes the Supabase auth cookies itself when signOut resolves with an error (owner-approved)", async () => {
    // auth-js returns `{ error }` without removing the session when it cannot load
    // it first, e.g. an expired access token whose refresh failed while offline.
    supabaseAuth.signOut.mockResolvedValue({ error: new Error("offline") });
    seedAuthCookies();
    expect(cookieNames()).toEqual(
      expect.arrayContaining(["sb-testref-auth-token.0", "sb-testref-auth-token.1"]),
    );
    const pat = me();
    const { user } = renderWithProviders(<LogOut />, { me: pat });

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(cookieNames().filter((name) => name.startsWith("sb-"))).toEqual([]);
    expect(cookieNames()).toContain("unrelated");
  });

  it("removes the Supabase auth cookies itself when signOut throws (owner-approved)", async () => {
    supabaseAuth.signOut.mockRejectedValue(new Error("Acquiring the auth lock timed out"));
    seedAuthCookies();
    const pat = me();
    const { user } = renderWithProviders(<LogOut />, { me: pat });

    await user.click(screen.getByRole("button", { name: `Log out ${pat.user.email}` }));

    await waitFor(() => expect(testRouter.replace).toHaveBeenCalledWith("/login"));
    expect(supabaseAuth.signOut).toHaveBeenCalledWith({ scope: "local" });
    expect(cookieNames().filter((name) => name.startsWith("sb-"))).toEqual([]);
    expect(cookieNames()).toContain("unrelated");
  });
});
