/**
 * The caller's Gmail connection (slice 5b spec, "Query hooks"; slice 5b-2).
 * User-scoped (`api.user`, no church header), under ["gmail-connection"].
 *
 * - `useGmailConnection()`: `GET /gmail-connection`.
 * - `useStartGmailConnect()`: `POST /gmail-connection/auth-url`, then
 *   `startGmailRedirect` to Google in the same tab; a URL that is not Google's
 *   is refused with "Something went wrong.".
 * - `useDisconnectGmail()`: `DELETE /gmail-connection`; its answer (not
 *   connected) goes straight into the cache.
 * A 401 is the app's (`handleAuthErrors`); any other failure is toasted
 * (`gmailErrorMessage`).
 */
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import type { GmailAuthUrl, GmailConnection } from "@/lib/api/types";
import { gmailErrorMessage, startGmailRedirect } from "@/lib/gmail";

import { useApi } from "./client";
import { keys } from "./keys";

export const SOMETHING_WRONG = "Something went wrong.";

export function useGmailConnection(): UseQueryResult<GmailConnection, ApiError> {
  const api = useApi();
  return useQuery<GmailConnection, ApiError>({
    queryKey: keys.gmailConnection(),
    queryFn: ({ signal }) => api.user<GmailConnection>("/gmail-connection", { signal }),
  });
}

/** Where to come back to after Google, and (from the email dialog, 5b-2b) what to reopen. */
export type StartGmailConnect = { returnTo: string; reopen?: object };

export function useStartGmailConnect() {
  const api = useApi();
  return useMutation<GmailAuthUrl, ApiError, StartGmailConnect>({
    mutationFn: () => api.user<GmailAuthUrl>("/gmail-connection/auth-url", { method: "POST" }),
    onSuccess: (data, { returnTo, reopen }) => {
      if (!startGmailRedirect(data.auth_url, returnTo, reopen)) toast.error(SOMETHING_WRONG);
    },
    onError: (e) => {
      if (e.status === 401) return;
      toast.error(gmailErrorMessage(e));
    },
  });
}

export function useDisconnectGmail() {
  const api = useApi();
  const queryClient = useQueryClient();
  return useMutation<GmailConnection, ApiError, void>({
    mutationFn: () => api.user<GmailConnection>("/gmail-connection", { method: "DELETE" }),
    onSuccess: (data) => queryClient.setQueryData(keys.gmailConnection(), data),
    onError: (e) => {
      if (e.status === 401) return;
      toast.error(gmailErrorMessage(e));
    },
  });
}
