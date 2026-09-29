"use client";

/**
 * Layout for every signed-in route (F §4.1, §4.2, §4.3; S "Layouts (1a)", Routing).
 *
 * - Loads `/me` and shows the shell skeleton until it arrives.
 * - Follows the post-login path (S Routing; AC14): the path `/login` stored
 *   before sign-in. It is read once, when the layout mounts, in a `useState`
 *   initializer; the server has no sessionStorage, and the hydration pass
 *   renders the skeleton either way because `/me` has not loaded yet, so the
 *   markup matches. A stored path other than the current one keeps the skeleton
 *   up until the pathname changes, so the page being left never mounts or sends
 *   a request; an effect clears the stored path first, then follows it with
 *   `router.replace`. A stored path equal to the current one is just cleared.
 *   Clearing before following means a stored path with no route yet
 *   (`/builder`) redirects once, not on every visit for ten minutes (slice 1b
 *   clarification 22), and StrictMode's repeated effect finds nothing to follow.
 * - A first load that fails with anything but a 401 shows a full-page
 *   `ErrorState` with Retry. While Retry runs, the error stays on screen with a
 *   busy, disabled Retry, so a repeat tap does nothing (a refetch of a query
 *   with no data resets it to pending, so the error Retry was pressed on is
 *   kept here). Once `/me` has loaded, a failed background refetch keeps the
 *   loaded shell: a network blip on window focus never replaces a working page.
 * - A 401 anywhere reaches `handleAuthErrors`, which emits
 *   `authEvents.signOutRequired()`. This layout, the event's only subscriber,
 *   answers with one local sign-out that keeps a pending invite and passes the
 *   current path as `next` (S Flow D "Session expired").
 * - While a sign-out runs (the signing-out flag in `lib/auth.ts`) it renders the
 *   skeleton and disables `/me`. That unmounts the `(church)` subtree and its
 *   `ChurchProvider`, so nothing refetches the cleared cache or stores a church
 *   again before `router.replace("/login")`.
 * - Pages below it read `/me` with `useMeContext()`.
 * - On `/me`'s first load and whenever its data changes, it prunes this
 *   user's unsaved drafts: older than 30 days, or for churches they no longer
 *   belong to (F §4.6 items 3 and 4; slice 2b).
 *
 * A `"use client"` layout cannot export `metadata`; the root layout's title applies.
 */
import { useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { ErrorState } from "@/components/app/error-state";
import { ShellSkeleton } from "@/components/app/shell-skeleton";
import { ApiError } from "@/lib/api/client";
import { isSigningOut, useSignOut, useSigningOut } from "@/lib/auth";
import { pruneDrafts } from "@/lib/draft/prune";
import { MeProvider } from "@/lib/me-context";
import { clearPostLoginPath, peekPostLoginPath } from "@/lib/post-login";
import { authEvents } from "@/lib/queries/auth-events";
import { useMe } from "@/lib/queries/me";

export default function SignedInLayout({ children }: { children: ReactNode }) {
  const signingOut = useSigningOut();
  const me = useMe({ enabled: !signingOut });
  const signOut = useSignOut();
  const pathname = usePathname();
  const router = useRouter();
  // The redirect this mount is making: from the current path to the stored one.
  const [leaving, setLeaving] = useState<{ from: string } | null>(() => {
    const target = peekPostLoginPath();
    return target !== null && target !== pathname ? { from: pathname } : null;
  });
  // The error Retry was pressed on, shown (with a busy Retry) while it runs.
  const [retriedError, setRetriedError] = useState<unknown>(null);
  // Arrived (or went anywhere else): the page below may render.
  if (leaving !== null && pathname !== leaving.from) setLeaving(null);

  useEffect(
    () =>
      authEvents.onSignOutRequired(() => {
        if (isSigningOut()) return;
        void signOut({ keepPendingInvite: true, next: pathname });
      }),
    [signOut, pathname],
  );

  const loaded = me.data;
  // On first load and whenever /me's data changes (TanStack Query keeps the
  // same object when a refetch returns equal data, so this does not rerun then).
  useEffect(() => {
    if (loaded) pruneDrafts(loaded.user.id, loaded.churches.map((church) => church.id));
  }, [loaded]);

  useEffect(() => {
    const target = peekPostLoginPath();
    if (target === null) return;
    clearPostLoginPath();
    if (target !== pathname) router.replace(target);
  }, [pathname, router]);

  if (signingOut || leaving !== null) return <ShellSkeleton />;
  if (me.data) return <MeProvider value={me.data}>{children}</MeProvider>;
  const error = me.isError ? me.error : me.isFetching ? retriedError : null;
  if (error !== null && !isUnauthenticated(error)) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center p-4">
        <ErrorState
          error={error}
          retrying={me.isFetching}
          onRetry={() => {
            setRetriedError(me.error);
            void me.refetch();
          }}
        />
      </main>
    );
  }
  return <ShellSkeleton />;
}

/** A 401 is already handled: `handleAuthErrors` has started the sign-out. */
function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
