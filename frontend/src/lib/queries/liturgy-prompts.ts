/**
 * Settings → Liturgy prompts' queries (slice 6a-3a; 6a spec "Queries and mutations" `prompts.ts`).
 *
 * - `useLiturgyPrompts()`: `GET /church/liturgy-prompts` under
 *   ["church", id, "liturgy-prompts"]; any member.
 * - `useSaveLiturgyPrompts()`: `PUT` the church's own wording, whole (admins);
 *   `{ prompts: {} }` with `reset: true` is Reset all. Success cancels a read
 *   in flight (it may predate the save), caches the answer and toasts "Prompts
 *   saved." or "Prompts reset to defaults.". Generation reads the prompts on
 *   the server each time, so nothing else is refreshed. Not optimistic (F §4.4).
 *
 * Errors: a 401 or a lost church the app already reports. A 422 naming a
 * prompt (`promptFieldErrors`) is the form's to show under that prompt. A role
 * 403 (an admin demoted meanwhile) is toasted and refetches the church profile,
 * so the page turns into the member's view. Anything else is toasted.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { LiturgyPrompts, PromptKey } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { PROMPT_KEYS, promptFieldErrors } from "@/lib/settings/prompts";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const PROMPTS_SAVED = "Prompts saved.";
export const PROMPTS_RESET = "Prompts reset to defaults.";
const PATH = "/church/liturgy-prompts";

export function useLiturgyPrompts(): UseQueryResult<LiturgyPrompts, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<LiturgyPrompts, ApiError>({
    queryKey: keys.liturgyPrompts(church.id),
    queryFn: ({ signal }) => api.church<LiturgyPrompts>(PATH, { signal }),
  });
}

export type SavePrompts = { prompts: Partial<Record<PromptKey, string>>; reset?: boolean };

export function useSaveLiturgyPrompts() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<LiturgyPrompts, ApiError, SavePrompts>({
    mutationFn: ({ prompts }) => api.church<LiturgyPrompts>(PATH, { method: "PUT", json: { prompts } }),
    onSuccess: async (saved, { reset }) => {
      // A read already in flight may predate the save; its answer must not replace what is now stored.
      await queryClient.cancelQueries({ queryKey: keys.liturgyPrompts(church.id) });
      queryClient.setQueryData(keys.liturgyPrompts(church.id), saved);
      toast.success(reset ? PROMPTS_RESET : PROMPTS_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || promptFieldErrors(e, PROMPT_KEYS) !== null) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
    },
  });
}
