/**
 * Settings → Rubric's queries (slice 6a-3a; 6a spec "Queries and mutations" `rubric.ts`).
 *
 * - `useRubric()`: `GET /rubric` under ["church", id, "rubric"]; any member.
 * - `useSaveRubric()`: one sparse `PATCH /rubric` (admins); `reset: true` for
 *   Reset all. Success cancels a read in flight (it may predate the save),
 *   caches the answer and toasts "Rubric saved." or "Rubric reset to
 *   defaults.". A patch that changes the preferred year also refreshes every
 *   hymn list (`newer_than_preferred` follows the year: the builder's picker
 *   relabels with no reload). Liturgy generation reads the rubric on the
 *   server, so nothing else is refreshed. Not optimistic (F §4.4).
 *
 * Errors: a 401 or a lost church the app already reports. A 422
 * `invalid_rubric` is the form's to show (above its footer). A role 403 (an
 * admin demoted meanwhile) is toasted and refetches the church profile, so the
 * page turns into the member's view. Anything else is toasted.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { Rubric } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import type { RubricPatch } from "@/lib/settings/rubric";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const RUBRIC_SAVED = "Rubric saved.";
export const RUBRIC_RESET = "Rubric reset to defaults.";

/** True for the server's 422 about the rubric's values: its message is shown above the form's footer. */
export function isInvalidRubric(e: unknown): boolean {
  return e instanceof ApiError && e.status === 422 && e.code === "invalid_rubric";
}

export function useRubric(): UseQueryResult<Rubric, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<Rubric, ApiError>({
    queryKey: keys.rubric(church.id),
    queryFn: ({ signal }) => api.church<Rubric>("/rubric", { signal }),
  });
}

export type SaveRubric = { patch: RubricPatch; reset?: boolean };

export function useSaveRubric() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<Rubric, ApiError, SaveRubric>({
    mutationFn: ({ patch }) => api.church<Rubric>("/rubric", { method: "PATCH", json: patch }),
    onSuccess: async (saved, { patch, reset }) => {
      // A read already in flight may predate the save; its answer must not replace what is now stored.
      await queryClient.cancelQueries({ queryKey: keys.rubric(church.id) });
      queryClient.setQueryData(keys.rubric(church.id), saved);
      if ("prefer_before_year" in patch) void queryClient.invalidateQueries({ queryKey: [...keys.church(church.id), "hymns"] });
      toast.success(reset ? RUBRIC_RESET : RUBRIC_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || isInvalidRubric(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}
