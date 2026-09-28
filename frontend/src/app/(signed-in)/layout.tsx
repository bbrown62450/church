"use client";

/**
 * Layout for every signed-in route (F §4.1, §4.2; S "Layouts (1a)").
 *
 * - Loads `/me` and shows the shell skeleton until it arrives.
 * - A first load that fails with anything but a 401 shows a full-page
 *   `ErrorState` with Retry. Once `/me` has loaded, a failed background refetch
 *   keeps the loaded shell: a network blip on window focus never replaces a
 *   working page.
 * - A 401 anywhere reaches `handleAuthErrors`, which emits
 *   `authEvents.signOutRequired()`. This layout, the event's only subscriber,
 *   answers with one local sign-out that keeps a pending invite and passes the
 *   current path as `next` (S Flow D "Session expired").
 * - While a sign-out runs (the signing-out flag in `lib/auth.ts`) it renders the
 *   skeleton and disables `/me`. That unmounts the `(church)` subtree and its
 *   `ChurchProvider`, so nothing refetches the cleared cache or stores a church
 *   again before `router.replace("/login")`.
 * - Pages below it read `/me` with `useMeContext()`.
 *
 * Slice 1b adds the post-login redirect here. A `"use client"` layout cannot
 * export `metadata`; the root layout's title applies.
 */
import { useEffect, type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { ErrorState } from "@/components/app/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { isSigningOut, useSignOut, useSigningOut } from "@/lib/auth";
import { MeProvider } from "@/lib/me-context";
import { authEvents } from "@/lib/queries/auth-events";
import { useMe } from "@/lib/queries/me";

export default function SignedInLayout({ children }: { children: ReactNode }) {
  const signingOut = useSigningOut();
  const me = useMe({ enabled: !signingOut });
  const signOut = useSignOut();
  const pathname = usePathname();

  useEffect(
    () =>
      authEvents.onSignOutRequired(() => {
        if (isSigningOut()) return;
        void signOut({ keepPendingInvite: true, next: pathname });
      }),
    [signOut, pathname],
  );

  if (signingOut) return <ShellSkeleton />;
  if (me.data) return <MeProvider value={me.data}>{children}</MeProvider>;
  if (me.isError && !isUnauthenticated(me.error)) {
    return (
      <main className="mx-auto flex min-h-dvh max-w-md flex-col justify-center p-4">
        <ErrorState error={me.error} onRetry={() => void me.refetch()} />
      </main>
    );
  }
  return <ShellSkeleton />;
}

/** A 401 is already handled: `handleAuthErrors` has started the sign-out. */
function isUnauthenticated(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}

/** The shell's shape while `/me` loads or a sign-out runs: a header bar and two cards. */
function ShellSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="min-h-dvh">
      <div className="border-b">
        <div className="mx-auto flex max-w-3xl items-center gap-3 px-4 py-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="ml-auto size-9 rounded-full" />
        </div>
      </div>
      <div className="mx-auto grid max-w-3xl gap-4 p-4">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    </div>
  );
}
