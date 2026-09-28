"use client";

/**
 * The client part of `/join` (S Flow B steps 1-3 and 7; F §4.3). `page.tsx`
 * renders it in `<Suspense>`.
 *
 * - Mount effect, once (a ref, since StrictMode runs effects twice): a `?code=`
 *   goes to `sessionStorage["wsb:pendingInviteCode"]`, and
 *   `history.replaceState(null, "", "/join")` takes it out of the address bar and
 *   history. Next 16 syncs a native `replaceState` into the router, so
 *   `useSearchParams().get("code")` is null afterwards. The code is therefore read
 *   once, here, and "no code" is never worked out from the URL again (1b
 *   clarification 27). The effect also clears the stored post-login path: `/join`
 *   sits outside the `(signed-in)` layout that would follow it.
 * - Signed in or not comes from `getAccessToken()` (clarification 20): a token
 *   means signed in; a 401 shows the "You're invited" card; anything else (a token
 *   refresh that could not reach Supabase) shows `ErrorState` with Retry, never
 *   the sign-in card. A neutral skeleton shows until this is known.
 * - `/me` (for the email) loads only once signed in (clarification 47). An
 *   enabled-from-mount `/me` would 401 for a signed-out visitor and sign them
 *   straight out to `/login`, skipping the "You're invited" card.
 * - A 401 from `/me`, preview or accept reaches `handleAuthErrors`. Its usual
 *   answer comes from the `(signed-in)` layout, which is not mounted here, so this
 *   page subscribes itself: a local sign-out that keeps the pending code and comes
 *   back to `/join` (clarification 19).
 * - Signed in with a code: `JoinInvite` previews it at once (owner decision 1:
 *   the preview card, then a Join tap).
 */
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { JoinInvite } from "@/components/onboarding/join-invite";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { getAccessToken, isSigningOut, useSignOut, useSigningOut } from "@/lib/auth";
import { clearPostLoginPath } from "@/lib/post-login";
import { authEvents } from "@/lib/queries/auth-events";
import { useMe } from "@/lib/queries/me";
import { readSession, removeSession, SESSION_KEYS, writeSession } from "@/lib/storage";

/** Where "Sign in with Google" goes: `/login` stores `next` and Google brings the user back here. */
const SIGN_IN_HREF = `/login?next=${encodeURIComponent("/join")}`;

type View =
  | { kind: "checking" }
  | { kind: "incomplete" }
  | { kind: "signed-out" }
  | { kind: "session-error"; code: string; error: unknown }
  | { kind: "signed-in"; code: string };

/**
 * Flow B step 2: store a `?code=` and take it out of the address bar and history;
 * clear the post-login path. Returns the pending code (the URL's, else one stored
 * before sign-in), or null when there is none. A blank `?code=` removes any stored
 * code, so it shows "This invite link is incomplete." (Flow B step 7).
 */
function captureCode(fromUrl: string | null): string | null {
  if (fromUrl !== null) {
    const trimmed = fromUrl.trim();
    if (trimmed !== "") writeSession(SESSION_KEYS.pendingInviteCode, trimmed);
    // A blank ?code= (a truncated link) is incomplete; never preview an older stored code.
    else removeSession(SESSION_KEYS.pendingInviteCode);
    window.history.replaceState(null, "", "/join");
  }
  clearPostLoginPath();
  const pending = readSession(SESSION_KEYS.pendingInviteCode)?.trim();
  return pending ? pending : null;
}

/** What to show for `code`. Never rejects. */
async function resolveView(code: string | null): Promise<View> {
  if (code === null) return { kind: "incomplete" };
  try {
    await getAccessToken();
    return { kind: "signed-in", code };
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return { kind: "signed-out" };
    // A sign-out is under way (`aborted`); it ends on /login.
    if (e instanceof ApiError && e.code === "aborted") return { kind: "checking" };
    return { kind: "session-error", code, error: e };
  }
}

export function JoinClient() {
  const searchParams = useSearchParams();
  const signingOut = useSigningOut();
  const signOut = useSignOut();
  const [view, setView] = useState<View>({ kind: "checking" });
  const captured = useRef(false);
  const me = useMe({ enabled: view.kind === "signed-in" && !signingOut });

  useEffect(() => {
    if (captured.current) return;
    captured.current = true;
    // No cleanup flag: StrictMode's second run returns early, so the first run's
    // result is the only one and must land.
    void resolveView(captureCode(searchParams.get("code"))).then(setView);
  }, [searchParams]);

  useEffect(
    () =>
      authEvents.onSignOutRequired(() => {
        if (isSigningOut()) return;
        void signOut({ keepPendingInvite: true, next: "/join" });
      }),
    [signOut],
  );

  if (signingOut || view.kind === "checking") return <JoinSkeleton />;
  if (view.kind === "incomplete") return <IncompleteCard />;
  if (view.kind === "signed-out") return <SignInCard />;
  if (view.kind === "session-error") {
    const { code } = view;
    return (
      <JoinFrame>
        <ErrorState
          error={view.error}
          onRetry={() => {
            setView({ kind: "checking" });
            void resolveView(code).then(setView);
          }}
        />
      </JoinFrame>
    );
  }
  if (me.data) {
    return (
      <JoinFrame>
        <JoinInvite initialCode={view.code} autoPreview email={me.data.user.email} showEntry={false} />
      </JoinFrame>
    );
  }
  if (me.isError && !isUnauthenticated(me.error)) {
    return (
      <JoinFrame>
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </JoinFrame>
    );
  }
  return <JoinSkeleton />;
}

/** A 401 is already handled: `handleAuthErrors` emitted `signOutRequired`, which this page answers. */
function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/** The onboarding column: `max-w-md`, 16 px gutters, centred. */
function JoinFrame({ children }: { children: ReactNode }) {
  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center p-4">
      {children}
    </main>
  );
}

/** Neutral: shown before the page knows whether anyone is signed in. */
export function JoinSkeleton() {
  return (
    <JoinFrame>
      <div role="status" aria-label="Loading" className="grid gap-3 rounded-xl border p-4">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    </JoinFrame>
  );
}

/** Flow B step 3. */
function SignInCard() {
  return (
    <JoinFrame>
      <Card>
        <CardHeader>
          <CardTitle>{"You're invited"}</CardTitle>
          <CardDescription>
            Sign in with Google to see and accept your invite to Worship Service Builder.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button render={<Link href={SIGN_IN_HREF} />} nativeButton={false} size="touch" className="w-full">
            Sign in with Google
          </Button>
        </CardContent>
      </Card>
    </JoinFrame>
  );
}

/** Flow B step 7: no `code` in the URL and none stored. "Go to home" replaces, as in `JoinInvite`. */
function IncompleteCard() {
  const router = useRouter();
  return (
    <JoinFrame>
      <Card>
        <CardHeader>
          <CardTitle>This invite link is incomplete.</CardTitle>
          <CardDescription>Open the link from your invite again, or ask for a new one.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button size="touch" className="w-full" onClick={() => router.replace("/")}>
            Go to home
          </Button>
        </CardContent>
      </Card>
    </JoinFrame>
  );
}
