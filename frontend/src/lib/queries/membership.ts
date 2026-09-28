/**
 * After a membership change (F §4.4 invalidation map: "create, join, leave or
 * delete church → ["me"], then a re-pick"; S "queries/membership.ts").
 */
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { storeChurchId } from "@/lib/church";

import { useApi } from "./client";
import { keys } from "./keys";
import { meQueryOptions } from "./me";

/** `selectChurchId`: the church to open next (create, join, open); `null` or left out stores nothing. */
export type MembershipChange = { selectChurchId?: string | null };

/**
 * Returns `changed({ selectChurchId })`, which a component awaits after a
 * create, join or open succeeded:
 * 1. stores `selectChurchId` as the active church when it is a church id;
 * 2. fetches `/me` again with `staleTime: 0` (even one loaded seconds ago; an
 *    in-flight `/me` is cancelled first, so it is never reused), so
 *    the new church is in `/me` **before** navigating; otherwise the `(church)`
 *    layout's `pickActiveChurch` would fall back and overwrite the stored id;
 * 3. `router.replace("/")`, or `"/welcome"` when `/me` lists no church.
 *
 * If that `/me` fetch fails (1b clarification 23), the cached `/me` is reset,
 * the stored id is kept and it still goes to `/`: the `(signed-in)` layout
 * shows its skeleton, then an ErrorState with Retry, until `/me` loads, so the
 * `(church)` layout never picks from the old list. It never throws: the change
 * itself succeeded, so the caller still shows its success toast.
 *
 * Slice 6b calls it with `selectChurchId: null` after a leave or delete, while
 * the `(church)` layout still shows the church just left. Any refetch of that
 * church's `GET /church` answers 403 `no_church_access`, and the layout's
 * lost-access toast would fire for a voluntary leave (1a T23-m1). So 6b must
 * have the new `/me` (step 2) before anything refetches that church, or leave
 * `(church)` first.
 */
export function useMembershipChanged(): (change: MembershipChange) => Promise<void> {
  const api = useApi();
  const queryClient = useQueryClient();
  const router = useRouter();
  return useCallback(
    async ({ selectChurchId }: MembershipChange) => {
      if (selectChurchId) storeChurchId(selectChurchId);
      let hasChurch = true;
      try {
        // A /me already in flight may predate the change; fetchQuery would reuse it.
        await queryClient.cancelQueries({ queryKey: keys.me() });
        const me = await queryClient.fetchQuery({ ...meQueryOptions(api), staleTime: 0 });
        hasChurch = me.churches.length > 0;
      } catch {
        void queryClient.resetQueries({ queryKey: keys.me() });
      }
      router.replace(hasChurch ? "/" : "/welcome");
    },
    [api, queryClient, router],
  );
}
