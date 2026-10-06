import { skipToken, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchPatch, ChurchProfile } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

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
