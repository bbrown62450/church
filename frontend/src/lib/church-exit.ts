/**
 * Leaving a church the user has just left or deleted (slice 6b-2b; 6b spec
 * "Frontend changes", `src/lib/church-exit.ts`). `runChurchExit` is the pure
 * order of steps, unit-tested; `useExitChurch` binds it to the app and is
 * what `useLeaveChurch` and `useDeleteChurch` call after the server said yes:
 *
 * 1. `markChurchExited(id)`: the `(church)` layout then re-picks quietly
 *    instead of saying "You no longer have access to {name}." for it;
 * 2. cancel every request for the church, so none finishes into a 403;
 * 3. remove this user's draft and corrupt-draft keys for it, so the dialogs'
 *    "Your unsaved draft … will be discarded" is true at once;
 * 4. slice 1's `useMembershipChanged({ selectChurchId: null })`: `/me` again
 *    (the server no longer lists the church), then `/` or `/welcome`; the
 *    layout re-picks from the new `/me`;
 * 5. remove the church's cached queries.
 *
 * If step 4's `/me` does not come back, `useExitChurch` says so; the
 * `(signed-in)` layout then shows its error state with Retry.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { toast } from "sonner";

import { markChurchExited } from "@/lib/church";
import { corruptDraftKey, draftKey } from "@/lib/draft/schema";
import { useMeContext } from "@/lib/me-context";
import { keys } from "@/lib/queries/keys";
import { type MembershipChange, useMembershipChanged } from "@/lib/queries/membership";
import { removeLocal } from "@/lib/storage";

/** The toast when `/me` did not come back after a leave or delete. */
export const EXIT_ME_FAILED = "Can't reach the server. Check your connection and try again.";

export type ChurchExit = {
  churchId: string;
  userId: string;
  /** The app's QueryClient, or a test's spies. */
  queryClient: {
    cancelQueries(filters: { queryKey: readonly unknown[] }): Promise<void>;
    removeQueries(filters: { queryKey: readonly unknown[] }): void;
  };
  membershipChanged(change: MembershipChange): Promise<boolean>;
  removeLocal(key: string): void;
};

/** The five steps above, in order. Resolves to whether `/me` came back; never throws. */
export async function runChurchExit({
  churchId,
  userId,
  queryClient,
  membershipChanged,
  removeLocal: remove,
}: ChurchExit): Promise<boolean> {
  markChurchExited(churchId);
  const queryKey = keys.church(churchId);
  await queryClient.cancelQueries({ queryKey });
  remove(draftKey(userId, churchId));
  remove(corruptDraftKey(userId, churchId));
  let meLoaded = false;
  try {
    meLoaded = await membershipChanged({ selectChurchId: null });
  } catch {
    meLoaded = false;
  }
  queryClient.removeQueries({ queryKey });
  return meLoaded;
}

/** `runChurchExit` for the signed-in user, with the toast when `/me` did not come back. */
export function useExitChurch(): (churchId: string) => Promise<void> {
  const queryClient = useQueryClient();
  const membershipChanged = useMembershipChanged();
  const userId = useMeContext().user.id;
  return useCallback(
    async (churchId: string) => {
      const meLoaded = await runChurchExit({ churchId, userId, queryClient, membershipChanged, removeLocal });
      if (!meLoaded) toast.error(EXIT_ME_FAILED);
    },
    [queryClient, membershipChanged, userId],
  );
}
