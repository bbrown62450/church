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
import { useSyncExternalStore } from "react";

import { ApiError, NETWORK_MESSAGE } from "@/lib/api/client";
import { createClient } from "@/lib/supabase/client";

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
