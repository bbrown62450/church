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
 * (`useChurchMutation`) with no second message; any other error is a toast
 * with the server's message, from the mutation's own `onError` so it still
 * shows when the card has unmounted (the member left Review mid-download;
 * 5a-1 build review fix 5).
 */
import { toast } from "sonner";

import type { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import { documentRequest, printedRequest } from "@/lib/documents";
import { useDraft } from "@/lib/draft/context";
import { docxFilename, downloadBlob, printedFilename, type DocumentVariant, type PrintedFormat } from "@/lib/download";

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
    onError: (e) => {
      // A 401 or a lost church is handled globally (sign-in, the church's own message): no second message.
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}

/**
 * The printed bulletin (printed bulletin spec, PR 1): as `useDownloadDocument`,
 * one mutation per button, posting `printedRequest` to `/documents/printed`.
 */
export function useDownloadPrinted(format: PrintedFormat) {
  const api = useApi();
  const { peek } = useDraft();
  return useChurchMutation<string, ApiError, void>({
    mutationFn: async () => {
      const body = printedRequest(peek(), format);
      const { blob, filename } = await api.churchBlob("/documents/printed", { method: "POST", json: body });
      const name = filename ?? printedFilename(format, body.service.service_date_iso);
      downloadBlob(blob, name);
      return name;
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      toast.error(errorToastMessage(e));
    },
  });
}
