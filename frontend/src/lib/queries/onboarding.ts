/**
 * Onboarding mutations (S "API client and query layer", slice 1b). All three
 * are user-scoped (`useApi().user`: no `X-Church-Id`) plain `useMutation`s, so
 * `retry: false` and the mutation cache's `handleAuthErrors` apply (a 401 asks
 * the `(signed-in)` layout, or `/join`, to sign out). The invite code is a
 * secret: it travels only in a POST body, never in a query key, a path or a
 * query string (AC9). No hook shows a toast: each component chooses an inline
 * message or a toast (1b clarification 26).
 */
import { useMutation, type UseMutationResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Church, CreateChurchBody, InviteAccepted, InvitePreview } from "@/lib/api/types";

import { useApi } from "./client";

/** `useCreateChurch`'s variables: the body, and the key from the form's `createKeyTracker().keyFor(body)`. */
export type CreateChurchVariables = { body: CreateChurchBody; key: string };

/**
 * `POST /churches` with `Idempotency-Key: key`: 201 `ChurchOut` (role "owner").
 * The form owns the key (lib/idempotency.ts) and reuses it only to retry an
 * identical body after an uncertain outcome. Times out after 30 s
 * (lib/api/timeouts.ts).
 */
export function useCreateChurch(): UseMutationResult<Church, ApiError, CreateChurchVariables> {
  const api = useApi();
  return useMutation<Church, ApiError, CreateChurchVariables>({
    mutationFn: ({ body, key }) =>
      api.user<Church>("/churches", { method: "POST", json: body, idempotencyKey: key }),
  });
}

/** `POST /invites/preview {code}` (read-only). The variable is the invite code. */
export function usePreviewInvite(): UseMutationResult<InvitePreview, ApiError, string> {
  const api = useApi();
  return useMutation<InvitePreview, ApiError, string>({
    mutationFn: (code) => api.user<InvitePreview>("/invites/preview", { method: "POST", json: { code } }),
  });
}

/**
 * `POST /invites/accept {code}`: joins, or reports that the caller is already a
 * member. No Idempotency-Key: a repeat accept is safe by construction (S Idempotency).
 */
export function useAcceptInvite(): UseMutationResult<InviteAccepted, ApiError, string> {
  const api = useApi();
  return useMutation<InviteAccepted, ApiError, string>({
    mutationFn: (code) => api.user<InviteAccepted>("/invites/accept", { method: "POST", json: { code } }),
  });
}
