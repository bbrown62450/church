/**
 * The browser session for API calls, and the signing-out flag (F §4.5, §4.2).
 *
 * The flag is module state: set once by `beginSignOut()` (Task 19's `useSignOut`
 * calls it first) and cleared only by a full page load, since every sign-in
 * comes back through the Google OAuth redirect. While it is set, no new API
 * request starts (`getAccessToken` rejects with `aborted`), `handleAuthErrors`
 * stays quiet, and the `(signed-in)` layout shows its skeleton, so nothing
 * refetches or re-stores a church during sign-out.
 */
import { isAuthRetryableFetchError } from "@supabase/supabase-js";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback, useSyncExternalStore } from "react";

import { ApiError, NETWORK_MESSAGE } from "@/lib/api/client";
import { storeChurchId } from "@/lib/church";
import { removeSession, SESSION_KEYS } from "@/lib/storage";
import { createClient } from "@/lib/supabase/client";
import { safeInternalPath } from "@/lib/urls";

let signingOut = false;
const listeners = new Set<() => void>();

function notify(): void {
  for (const listener of [...listeners]) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function signingOutError(): ApiError {
  return new ApiError(0, "aborted", "Signing out.");
}

/** True from `beginSignOut()` until the next full page load. */
export function isSigningOut(): boolean {
  return signingOut;
}

/** Marks this tab as signing out. Idempotent. */
export function beginSignOut(): void {
  if (signingOut) return;
  signingOut = true;
  notify();
}

/** `isSigningOut()` for rendering; the server snapshot is `false`. */
export function useSigningOut(): boolean {
  return useSyncExternalStore(subscribe, isSigningOut, () => false);
}

/** Tests only: clears the flag (setup-dom.ts runs it after every DOM test). */
export function resetSigningOutForTests(): void {
  signingOut = false;
  notify();
}

/**
 * The Supabase access token for the API's `Authorization` header.
 * Rejects with `ApiError(401, "unauthenticated")` when there is no session and
 * with `ApiError(0, "aborted")` while signing out, including a sign-out that
 * starts while the session is being read.
 *
 * A token refresh that could not reach Supabase (auth-js returns no session
 * with an `AuthRetryableFetchError` but keeps the refresh token, e.g. a laptop
 * waking offline) rejects with a retryable `ApiError(0, "network_error")`
 * instead, so it does not sign the user out (owner-approved, 2026-09-27).
 */
export async function getAccessToken(): Promise<string> {
  if (signingOut) throw signingOutError();
  const { data, error } = await createClient().auth.getSession();
  if (signingOut) throw signingOutError();
  if (isAuthRetryableFetchError(error)) throw new ApiError(0, "network_error", NETWORK_MESSAGE);
  const token = data.session?.access_token;
  if (!token) throw new ApiError(401, "unauthenticated", "Please sign in.");
  return token;
}

export type SignOutOptions = {
  /** Keep `wsb:pendingInviteCode` (the automatic 401 path), so an invite survives the new sign-in. */
  keepPendingInvite?: boolean;
  /** Where to return after sign-in; used only when `safeInternalPath` accepts it. */
  next?: string;
};

/**
 * Flow D sign-out (S "Log out" and "Session expired"; F §4.2). The signing-out
 * flag goes up first, so while the cache is torn down nothing refetches, no 401
 * starts a second sign-out and no layout re-stores a church (clarification 27).
 * Then: cancel and clear every query, forget the stored church and the `wsb:`
 * session keys (the pending invite only when not asked to keep it), end this
 * browser's Supabase session (`scope: "local"`, never the global default) and
 * go to `/login`, with `?next=` when `next` is an allow-listed path. Needs no
 * `ChurchProvider`, so the `/welcome` header can use it.
 */
export function useSignOut(): (opts?: SignOutOptions) => Promise<void> {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(
    async ({ keepPendingInvite = false, next }: SignOutOptions = {}) => {
      beginSignOut();
      await queryClient.cancelQueries();
      queryClient.clear();
      storeChurchId(null);
      removeSession(SESSION_KEYS.postLoginPath);
      if (!keepPendingInvite) removeSession(SESSION_KEYS.pendingInviteCode);
      try {
        await createClient().auth.signOut({ scope: "local" });
      } catch {
        // supabase-js reports failures as `{ error }` after removing the local
        // session; a throw here is unexpected, and /login is still the right place.
      }
      const back = next === undefined ? null : safeInternalPath(next);
      router.replace(back ? `/login?next=${encodeURIComponent(back)}` : "/login");
    },
    [queryClient, router],
  );
}
