"use client";

/**
 * The church-scoped shell: every page that works on one church lives under it
 * (S Layouts steps 1-7, Flow D; F §4.2, §4.4).
 *
 * 1. `useStoredChurchId()` is `undefined` until the client has read
 *    `activeChurchId`, so the server render and the hydration pass show the
 *    shell skeleton and no church is picked before the stored one is known.
 * 2. The candidate is the stored church when it is still in `/me` and not
 *    excluded, else the first by name. No candidate → `/welcome`.
 * 3. `GET /church` confirms the candidate while the header shows its name. The
 *    confirmed id is stored only when it is the candidate's and differs from
 *    the stored id (the fallback pick), and never while signing out.
 * 4. The children render under `ChurchProvider`, keyed by the church id, so a
 *    switch remounts the whole subtree.
 * 5. `churchAccessLost` for the candidate (`no_church_access` from any church
 *    query): toast, exclude it, refetch `/me`, which picks the next church.
 *    A `/me` refetch that no longer lists the shown church (it can answer
 *    before the 403 on refocus) toasts the same message once.
 * 6. A switch stores the new id. Once the old church is no longer shown, its
 *    `["church", oldId]` queries are cancelled and removed.
 */
import { Fragment, useEffect, useRef, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AppHeader } from "@/components/app/app-header";
import { ErrorState } from "@/components/app/error-state";
import { ShellSkeleton } from "@/components/app/shell-skeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { isSigningOut, useSignOut } from "@/lib/auth";
import { type Church, pickActiveChurch, storeChurchId, useStoredChurchId } from "@/lib/church";
import { ChurchProvider } from "@/lib/church-context";
import { useMeContext } from "@/lib/me-context";
import { authEvents } from "@/lib/queries/auth-events";
import { useChurchProfile } from "@/lib/queries/church";
import { keys } from "@/lib/queries/keys";

export default function ChurchLayout({ children }: { children: ReactNode }) {
  const me = useMeContext();
  const router = useRouter();
  const queryClient = useQueryClient();
  const signOut = useSignOut();
  const activeId = useStoredChurchId();
  const [excluded, setExcluded] = useState<ReadonlySet<string>>(() => new Set());

  // Step 2: nothing is picked until the stored id has been read.
  const candidate = activeId === undefined ? null : pickActiveChurch(me.churches, activeId, excluded);
  const candidateId = candidate?.id ?? null;
  const candidateName = candidate?.name ?? "";
  const noChurch = activeId !== undefined && candidate === null;

  // Step 3: only the candidate's own profile confirms it; cached data for any
  // other church never does.
  const profile = useChurchProfile(candidate?.id, { enabled: candidate !== null });
  const confirmed: Church | null =
    candidate !== null && profile.data?.id === candidate.id ? profile.data : null;
  const confirmedId = confirmed?.id ?? null;

  useEffect(() => {
    if (noChurch) router.replace("/welcome");
  }, [noChurch, router]);

  useEffect(() => {
    if (confirmedId !== null && confirmedId !== activeId && !isSigningOut()) {
      storeChurchId(confirmedId);
    }
  }, [confirmedId, activeId]);

  // Step 5: one toast and one /me refetch per lost church.
  useEffect(() => {
    if (candidateId === null) return;
    let handled = false;
    return authEvents.onChurchAccessLost((lostId) => {
      if (lostId !== candidateId || handled) return;
      handled = true;
      toast.error(`You no longer have access to ${candidateName}.`);
      setExcluded((previous) => new Set(previous).add(lostId));
      void queryClient.invalidateQueries({ queryKey: keys.me() });
    });
  }, [candidateId, candidateName, queryClient]);

  // The church last shown ({id, name}); read and written only inside effects.
  const shownRef = useRef<{ id: string; name: string } | null>(null);
  const confirmedName = confirmed?.name ?? "";

  // Step 5, second path: a /me refetch that no longer lists the church being
  // shown is lost access too. On refocus /me can answer before GET /church's
  // 403, and step 6 then cancels that request, so no churchAccessLost event
  // would come. Declared before step 6, so it still sees the church last shown.
  useEffect(() => {
    const shown = shownRef.current;
    if (shown === null || isSigningOut()) return;
    if (!me.churches.some((c) => c.id === shown.id)) {
      toast.error(`You no longer have access to ${shown.name}.`);
    }
  }, [me.churches]);

  // Step 6: runs after the render that stopped showing the old church, so no
  // mounted observer can rebuild its queries. The ref keeps StrictMode's
  // repeated effect from removing the shown church.
  useEffect(() => {
    const previous = shownRef.current;
    shownRef.current = confirmedId === null ? null : { id: confirmedId, name: confirmedName };
    if (previous === null || previous.id === confirmedId) return;
    const queryKey = keys.church(previous.id);
    void queryClient.cancelQueries({ queryKey });
    queryClient.removeQueries({ queryKey });
  }, [confirmedId, confirmedName, queryClient]);

  if (candidate === null) return <ShellSkeleton />;

  let body: ReactNode;
  if (confirmed !== null) {
    // Step 4.
    body = (
      <ChurchProvider value={confirmed}>
        <Fragment key={confirmed.id}>{children}</Fragment>
      </ChurchProvider>
    );
  } else if (profile.isError && !isHandledElsewhere(profile.error)) {
    body = (
      <main className="mx-auto max-w-3xl p-4">
        <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />
      </main>
    );
  } else {
    body = <BodySkeleton />;
  }

  return (
    <div className="min-h-dvh">
      <AppHeader
        user={me.user}
        churches={me.churches.filter((church) => !excluded.has(church.id))}
        active={confirmed ?? candidate}
        onSelectChurch={(id) => storeChurchId(id)}
        onSignOut={() => void signOut()}
      />
      {body}
    </div>
  );
}

/**
 * Errors another handler owns, so the body keeps its skeleton: lost access
 * (step 5 picks the next church) and 401 or a sign-out in progress (the
 * `(signed-in)` layout signs out and unmounts this subtree).
 */
function isHandledElsewhere(error: unknown): boolean {
  return (
    isNoChurchAccess(error) ||
    (error instanceof ApiError && (error.status === 401 || error.code === "aborted"))
  );
}

function BodySkeleton() {
  return (
    <main className="mx-auto grid max-w-3xl gap-4 p-4" aria-busy="true">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </main>
  );
}
