"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AppHeader } from "@/components/app-header";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, apiFetch } from "@/lib/api";
import {
  type Church,
  type Me,
  pickActiveChurch,
  readStoredChurchId,
  storeChurchId,
} from "@/lib/church";
import { createLatestTracker } from "@/lib/latest";
import { createClient } from "@/lib/supabase/client";

async function accessToken(): Promise<string | null> {
  const { data } = await createClient().auth.getSession();
  return data.session?.access_token ?? null;
}

export default function Home() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [active, setActive] = useState<Church | null>(null);
  const churchSelection = useRef(createLatestTracker());

  const signOut = useCallback(async () => {
    storeChurchId(null);
    await createClient().auth.signOut();
    router.replace("/login");
  }, [router]);

  const handleError = useCallback(
    async (err: unknown) => {
      if (err instanceof ApiError && err.status === 401) return signOut();
      toast.error(err instanceof Error ? err.message : "Something went wrong.");
    },
    [signOut],
  );

  // Ask the server to confirm the church; it re-checks membership every time.
  const selectChurch = useCallback(
    async (church: Church) => {
      const isLatest = churchSelection.current.begin();
      const token = await accessToken();
      if (!token) return signOut();
      try {
        const confirmed = await apiFetch<Church>("/church", { token, churchId: church.id });
        if (!isLatest()) return;
        storeChurchId(confirmed.id);
        setActive(confirmed);
      } catch (err) {
        if (!isLatest()) return;
        if (err instanceof ApiError && err.status === 403) {
          storeChurchId(null);
          setActive(null);
          toast.error("You no longer have access to that church. Pick another.");
          return;
        }
        await handleError(err);
      }
    },
    [signOut, handleError],
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const token = await accessToken();
      if (!token) return signOut();
      try {
        const result = await apiFetch<Me>("/me", { token });
        if (cancelled) return;
        setMe(result);
        const chosen = pickActiveChurch(result.churches, readStoredChurchId());
        if (chosen) await selectChurch(chosen);
      } catch (err) {
        if (!cancelled) await handleError(err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [signOut, handleError, selectChurch]);

  if (!me) return <HomeSkeleton />;

  return (
    <div className="min-h-dvh">
      <AppHeader
        user={me.user}
        churches={me.churches}
        active={active}
        onSelectChurch={selectChurch}
        onSignOut={signOut}
      />
      <main className="mx-auto grid max-w-3xl gap-4 p-4">
        {me.churches.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No church yet</CardTitle>
              <CardDescription>
                Creating or joining a church is coming in the next update.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            <Card>
              <CardHeader>
                <CardTitle>Service Builder</CardTitle>
                <CardDescription>
                  Readings, hymns, and liturgy for {active?.name ?? "your church"} are coming soon.
                  Until then, keep using the current app.
                </CardDescription>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Settings</CardTitle>
                <CardDescription>Church profile, members, and invites are coming later.</CardDescription>
              </CardHeader>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}

function HomeSkeleton() {
  return (
    <div className="mx-auto grid max-w-3xl gap-4 p-4">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-24 w-full" />
    </div>
  );
}
