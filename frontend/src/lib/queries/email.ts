/**
 * Emailing the bulletin (slice 5b spec, `useSendBulletinEmail`; slice 5b-2):
 * `POST /bulletin-emails` with the dialog's Idempotency-Key (90 s client
 * timeout, `lib/api/timeouts.ts`). The dialog shows every failure itself, so
 * nothing is toasted here; a 401 or a lost church still goes through the
 * cache's `handleAuthErrors` (`useChurchMutation`).
 */
import type { ApiError } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import type { BulletinEmailBody } from "@/lib/email";

import { useApi, useChurchMutation } from "./client";

export type BulletinEmailSent = components["schemas"]["BulletinEmailOut"];
export type SendBulletinEmail = { body: BulletinEmailBody; key: string };

export function useSendBulletinEmail() {
  const api = useApi();
  return useChurchMutation<BulletinEmailSent, ApiError, SendBulletinEmail>({
    mutationFn: ({ body, key }) =>
      api.church<BulletinEmailSent>("/bulletin-emails", { method: "POST", json: body, idempotencyKey: key }),
  });
}
