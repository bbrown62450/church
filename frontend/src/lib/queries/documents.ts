/**
 * The Word files (slice 5a spec, `useDownloadDocument`; F §1.9; owner decision 4).
 *
 * `useDownloadDocument(variant)`: one mutation per button, so each has its own
 * pending state. On click it reads the latest draft (`peek`), builds the body
 * (`documentRequest`), posts it with `useApi().churchBlob` (30 s client
 * timeout, `lib/api/timeouts.ts`) and hands the file to `downloadBlob` under
 * the server's name, or `docxFilename` when the header is missing. Nothing is
 * cached or kept: each tap builds the file from the draft as it is then. A
 * 401 or a lost church goes through the cache's `handleAuthErrors`
 * (`useChurchMutation`); the caller shows any other error.
 */
import type { ApiError } from "@/lib/api/client";
import { documentRequest } from "@/lib/documents";
import { useDraft } from "@/lib/draft/context";
import { docxFilename, downloadBlob, type DocumentVariant } from "@/lib/download";

import { useApi, useChurchMutation } from "./client";

/** The mutation's result: the name the file was saved under. */
export function useDownloadDocument(variant: DocumentVariant) {
  const api = useApi();
  const { peek } = useDraft();
  return useChurchMutation<string, ApiError, void>({
    mutationFn: async () => {
      const body = documentRequest(peek(), variant);
      const { blob, filename } = await api.churchBlob("/documents", { method: "POST", json: body });
      const name = filename ?? docxFilename(variant, body.service.service_date_iso);
      downloadBlob(blob, name);
      return name;
    },
  });
}
