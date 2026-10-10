import { skipToken, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchLeft, ChurchPatch, ChurchProfile, DeletedOut, MemberList } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { useExitChurch } from "@/lib/church-exit";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";
import { onWriteError } from "./people";

export const PROFILE_SAVED = "Profile saved.";

/**
 * `GET /church` for `id` (key ["church", id, "profile"]): the server confirms
 * the membership, and since slice 2a returns the profile (`ChurchProfileOut`:
 * timezone, translation). The `(church)` layout calls it above `ChurchProvider`, so it
 * sends the id through `forChurch`. No request while `id` is undefined or
 * `enabled` is false.
 */
export function useChurchProfile(
  id: string | undefined,
  opts: { enabled?: boolean } = {},
): UseQueryResult<ChurchProfile, ApiError> {
  const api = useApi();
  return useQuery<ChurchProfile, ApiError>({
    queryKey: keys.churchProfile(id ?? ""),
    queryFn: id ? ({ signal }) => api.forChurch(id)<ChurchProfile>("/church", { signal }) : skipToken,
    enabled: opts.enabled ?? true,
  });
}

/**
 * `PATCH /church` (slice 6a-1; admins): only the fields that change. Success
 * cancels a profile read in flight (it may predate the save), caches the
 * answer as the profile, so the header, the builder's translation and its
 * Benediction default follow at once, refreshes `/me` (the switcher's name)
 * and, when the default hymnal was sent, `GET /hymnals` (the Hymns step's
 * hymnal), and toasts "Profile saved.". A failure toasts the server's message,
 * except a 401 or a lost church, which the app already reports; a role 403
 * (an admin demoted meanwhile) also refetches the profile, so the page turns
 * read-only.
 */
export function useUpdateChurch() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<ChurchProfile, ApiError, ChurchPatch>({
    mutationFn: (patch) => api.church<ChurchProfile>("/church", { method: "PATCH", json: patch }),
    onSuccess: async (saved, patch) => {
      await queryClient.cancelQueries({ queryKey: keys.churchProfile(church.id) });
      queryClient.setQueryData(keys.churchProfile(church.id), saved);
      void queryClient.invalidateQueries({ queryKey: keys.me() });
      if (patch.default_hymnal !== undefined) void queryClient.invalidateQueries({ queryKey: keys.hymnals(church.id) });
      toast.success(PROFILE_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}

// --- Slice 6b-2b: transfer ownership, leave, delete (the routes are slice 6b-1's) ---------------------------

export const TRANSFERRED = "Ownership transferred. You are now an admin.";

/** "You left {church}." */
export function leftChurch(name: string): string {
  return `You left ${name}.`;
}

export const CHURCH_DELETED = "Church deleted.";

/**
 * `POST /church/transfer-ownership` (the owner): the answer, the member list
 * afterwards, goes in the cache; the members, the profile (which carries the
 * role, so the Danger zone turns to its admin form) and `/me` (the switcher's
 * role) refetch; "Ownership transferred. You are now an admin.". A role
 * refusal (ownership moved elsewhere) is toasted and refetches the role and
 * the members; a 404 (that person left meanwhile) is toasted and refetches
 * the members; a 401 or a lost church is the app's.
 */
export function useTransferOwnership() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.members(church.id);
  return useChurchMutation<MemberList, ApiError, string>({
    mutationFn: (userId) =>
      api.church<MemberList>("/church/transfer-ownership", { method: "POST", json: { user_id: userId } }),
    onSuccess: async (list) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData(key, list);
      void queryClient.invalidateQueries({ queryKey: key });
      void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
      void queryClient.invalidateQueries({ queryKey: keys.me() });
      toast.success(TRANSFERRED);
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}

/**
 * `POST /church/leave` (an admin or a member): "You left {church}.", then
 * `useExitChurch` (another church or `/welcome`, the draft gone, no "no
 * longer have access" toast). The mutation stays pending until the exit is
 * done, so the dialog keeps "Leaving…" until the page goes. A refusal (409:
 * the owner must transfer first, or the last admin of a church with no owner)
 * is toasted with the server's words; a 401 or a lost church is the app's.
 */
export function useLeaveChurch() {
  const api = useApi();
  const church = useChurch();
  const exit = useExitChurch();
  return useChurchMutation<ChurchLeft, ApiError, void>({
    mutationFn: () => api.church<ChurchLeft>("/church/leave", { method: "POST" }),
    onSuccess: async () => {
      toast.success(leftChurch(church.name));
      await exit(church.id);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}

/** A 422 naming `confirm_name` ("Church name did not match."): the Delete dialog shows it under the name. */
export function deleteNameError(e: unknown): string | null {
  return e instanceof ApiError && e.status === 422 && e.fields?.confirm_name ? e.fields.confirm_name : null;
}

/**
 * `DELETE /church` with `{confirm_name}` (the owner; sent as typed, the
 * server trims): "Church deleted.", then the same exit as Leave. A name
 * mismatch is the dialog's (`deleteNameError`), not toasted, and refetches
 * the profile, in case the church was renamed elsewhere; a role refusal
 * (ownership moved elsewhere) is toasted and refetches the role and the
 * members; a 401 or a lost church is the app's; anything else is toasted.
 */
export function useDeleteChurch() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const exit = useExitChurch();
  const writeError = onWriteError(queryClient, church.id, keys.members(church.id));
  return useChurchMutation<DeletedOut, ApiError, string>({
    mutationFn: (confirmName) =>
      api.church<DeletedOut>("/church", { method: "DELETE", json: { confirm_name: confirmName } }),
    onSuccess: async () => {
      toast.success(CHURCH_DELETED);
      await exit(church.id);
    },
    onError: (e) => {
      if (deleteNameError(e) === null) {
        writeError(e);
        return;
      }
      void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}
