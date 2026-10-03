/**
 * The church's bulletin settings (printed bulletin spec, PR 2a; F §4.4).
 *
 * - `useBulletinSettings()`: `GET /church/bulletin-settings` under
 *   ["church", id, "bulletin-settings"]; any member. The Printed bulletin
 *   card reads it for "Not filled in: …"; the Bulletin settings page shows it,
 *   with `{ fresh: true }`: fetched again on opening the page even when cached,
 *   so the form never starts from an older value.
 * - `useSaveBulletinSettings()`: `PUT` the whole object (admins). Success
 *   cancels a read in flight (it may predate the save), caches the answer
 *   (what is stored) and toasts "Bulletin settings saved";
 *   a failure toasts the server's message (a member's role 403 included),
 *   except a 401 or a lost church, which the app already reports.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { BulletinSettings } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const SETTINGS_SAVED = "Bulletin settings saved";
const PATH = "/church/bulletin-settings";

export function useBulletinSettings({ fresh = false }: { fresh?: boolean } = {}): UseQueryResult<
  BulletinSettings,
  ApiError
> {
  const api = useApi();
  const church = useChurch();
  return useQuery<BulletinSettings, ApiError>({
    queryKey: keys.bulletinSettings(church.id),
    queryFn: ({ signal }) => api.church<BulletinSettings>(PATH, { signal }),
    refetchOnMount: fresh ? "always" : true,
  });
}

export function useSaveBulletinSettings() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<BulletinSettings, ApiError, BulletinSettings>({
    mutationFn: (body) => api.church<BulletinSettings>(PATH, { method: "PUT", json: body }),
    onSuccess: async (saved) => {
      // A read already in flight may predate the save; its answer must not replace what is now stored.
      await queryClient.cancelQueries({ queryKey: keys.bulletinSettings(church.id) });
      queryClient.setQueryData(keys.bulletinSettings(church.id), saved);
      toast.success(SETTINGS_SAVED);
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}
