/**
 * Settings → Prayers' queries (slice 6a-3b; 6a spec "Queries and mutations"
 * `prayer-library.ts`).
 *
 * - `usePrayerLibrary()`: `GET /church/prayer-library` under
 *   ["church", id, "prayer-library"]; any member.
 * - `useSavePrayerLibrary()`: `PUT` the whole library (admins). Success cancels
 *   a read in flight (it may predate the save), caches the answer and toasts
 *   "Prayer library saved.". Generation reads the library on the server each
 *   time, so nothing else is refreshed. Not optimistic (F §4.4).
 * - `useDraftVoiceProfile()`: `POST …/voice-profile-draft` (admins; one `ai`
 *   token), with the caller's `signal` for Cancel and the 90 s client timeout
 *   (`timeouts.ts`). The draft is not stored, so it touches no cache.
 *
 * Errors: a 401 or a lost church the app already reports. A role 403 (an
 * admin demoted meanwhile) is toasted and refetches the church profile, so the
 * page turns into the member's view. A save's 422 naming a row or the profile
 * (`namesLibraryField`) is the form's to show; any other save failure is
 * toasted. A draft's other failures are the card's to show (no toast).
 */
import { useQuery, useQueryClient, type QueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { PrayerLibrary, PrayerLibraryBody, VoiceProfileDraft } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { namesLibraryField } from "@/lib/settings/prayers";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const LIBRARY_SAVED = "Prayer library saved.";
const PATH = "/church/prayer-library";
export const DRAFT_PATH = "/church/prayer-library/voice-profile-draft";

export function usePrayerLibrary(): UseQueryResult<PrayerLibrary, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<PrayerLibrary, ApiError>({
    queryKey: keys.prayerLibrary(church.id),
    queryFn: ({ signal }) => api.church<PrayerLibrary>(PATH, { signal }),
  });
}

/** A role 403: toasted, and the church profile refetched so the page turns read-only. */
function roleRefused(e: ApiError, queryClient: QueryClient, churchId: string): boolean {
  if (e.status !== 403 || isNoChurchAccess(e)) return false;
  toast.error(errorToastMessage(e));
  void queryClient.invalidateQueries({ queryKey: keys.churchProfile(churchId) });
  return true;
}

export function useSavePrayerLibrary() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<PrayerLibrary, ApiError, PrayerLibraryBody>({
    mutationFn: (body) => api.church<PrayerLibrary>(PATH, { method: "PUT", json: body }),
    onSuccess: async (saved) => {
      // A read already in flight may predate the save; its answer must not replace what is now stored.
      await queryClient.cancelQueries({ queryKey: keys.prayerLibrary(church.id) });
      queryClient.setQueryData(keys.prayerLibrary(church.id), saved);
      toast.success(LIBRARY_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || roleRefused(e, queryClient, church.id)) return;
      if (!namesLibraryField(e)) toast.error(errorToastMessage(e));
    },
  });
}

export function useDraftVoiceProfile() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<VoiceProfileDraft, ApiError, { signal: AbortSignal }>({
    mutationFn: ({ signal }) => api.church<VoiceProfileDraft>(DRAFT_PATH, { method: "POST", signal }),
    onError: (e) => {
      if (e.status !== 401 && !isNoChurchAccess(e)) roleRefused(e, queryClient, church.id);
    },
  });
}
