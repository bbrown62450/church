/**
 * The browser session for API calls, and the signing-out flag (F §4.5, §4.2).
 *
 * The flag is module state: set once by `beginSignOut()` (`useSignOut` calls it
 * first) and cleared by `endSignOut()` when `/login` mounts, or by a full page
 * load. Every sign-out ends on `/login`, so a browser Back into a cached
 * signed-in page finds the flag down and loads `/me` again (slice 1b
 * clarification 21). While it is set, no new API
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

/** True from `beginSignOut()` until `endSignOut()` or the next full page load. */
export function isSigningOut(): boolean {
  return signingOut;
}

/** Marks this tab as signing out. Idempotent. */
export function beginSignOut(): void {
  if (signingOut) return;
  signingOut = true;
  notify();
}

/**
 * Ends a sign-out in this tab: clears the flag. `/login` calls it when it
 * mounts, after `useSignOut` has finished and the signed-in layouts are gone.
 * Idempotent.
 */
export function endSignOut(): void {
  if (!signingOut) return;
  signingOut = false;
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

/** The session cookies `@supabase/ssr`'s browser client writes: `sb-<ref>-auth-token`, chunked `.0`, `.1`, … */
const AUTH_COOKIE = /^sb-.+-auth-token(\.\d+)?$/;

/** Expires this browser's Supabase session cookies at `path=/`, where `@supabase/ssr` writes them. */
function removeAuthCookies(): void {
  for (const pair of document.cookie.split(";")) {
    const name = pair.split("=", 1)[0].trim();
    if (AUTH_COOKIE.test(name)) document.cookie = `${name}=; path=/; max-age=0`;
  }
}

export type SignOutOptions = {
  /** Keep `wsb:pendingInviteCode` (the automatic 401 path), so an invite survives the new sign-in. */
  keepPendingInvite?: boolean;
  /** Where to return after sign-in; used only when `safeInternalPath` accepts it. */
  next?: string;
  /** Adds `select_account=1`, so `/login` asks Google for its account chooser (S Flow B email mismatch). */
  selectAccount?: boolean;
};

/**
 * Flow D sign-out (S "Log out" and "Session expired"; F §4.2). The signing-out
 * flag goes up first, so while the cache is torn down nothing refetches, no 401
 * starts a second sign-out and no layout re-stores a church (clarification 27).
 * Then: cancel and clear every query, forget the stored church and the `wsb:`
 * session keys (the pending invite only when not asked to keep it), end this
 * browser's Supabase session (`scope: "local"`, never the global default; if
 * that fails, its auth cookies are expired directly) and go to `/login`, with
 * `?next=` when `next` is an allow-listed path and `select_account=1` when
 * `selectAccount` is set. Never rejects. Needs no
 * `ChurchProvider`, so the `/welcome` header can use it.
 */
export function useSignOut(): (opts?: SignOutOptions) => Promise<void> {
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(
    async ({ keepPendingInvite = false, next, selectAccount = false }: SignOutOptions = {}) => {
      beginSignOut();
      await queryClient.cancelQueries();
      queryClient.clear();
      storeChurchId(null);
      removeSession(SESSION_KEYS.postLoginPath);
      if (!keepPendingInvite) removeSession(SESSION_KEYS.pendingInviteCode);
      // auth-js can fail without removing the session: when it cannot load the
      // session first (an expired access token whose refresh failed offline or on a
      // 5xx) it returns `{ error }` and keeps the refresh-token cookies, and an
      // unexpected auth-js throw keeps them too. Left alone, the next full
      // load's proxy `getUser()` would refresh and sign this browser back in as the
      // same user, so on any failure the cookies go here (owner-approved, 2026-09-27).
      let signedOut = false;
      try {
        const { error } = await createClient().auth.signOut({ scope: "local" });
        signedOut = !error;
      } catch {
        // Handled below with the `{ error }` case; /login is still the right place.
      }
      if (!signedOut) removeAuthCookies();
      const back = next === undefined ? null : safeInternalPath(next);
      const query = new URLSearchParams();
      if (back) query.set("next", back);
      if (selectAccount) query.set("select_account", "1");
      const search = query.toString();
      router.replace(search ? `/login?${search}` : "/login");
    },
    [queryClient, router],
  );
}
