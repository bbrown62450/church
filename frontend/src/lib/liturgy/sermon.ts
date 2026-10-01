"use client";

/**
 * The sermon text a liturgy request carries (slice 4 spec, "Sermon text";
 * reviewer spec, API: review and revise send the same resolved sermon text as
 * generation). One loader, used by the generation provider for each batch and
 * by the review provider for each review or revision.
 *
 * `useSermonLoader(church, waitMs)` returns `load(signal)`: the effective NT
 * reading in the translation step 1 shows (the draft's only while the server
 * still offers it), WEB instead of ESV (Crossway's terms), read through the
 * passage cache with `queryClient.fetchQuery` (a passage already cached is
 * reused), at most `waitMs` (10 s); a failure, a timeout or an abort resolves
 * to null, and the request goes without it.
 */
import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import type { ChurchProfile, SermonText, Translations } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { useApi } from "@/lib/queries/client";
import { keys as queryKeys } from "@/lib/queries/keys";
import { passageQuery } from "@/lib/queries/passages";

import { sermonSource, sermonText } from "./request";

/** How long a request waits for the sermon text before going without it (S "Sermon text"). */
export const SERMON_WAIT_MS = 10_000;

export function useSermonLoader(
  church: Pick<ChurchProfile, "effective_translation">,
  waitMs: number = SERMON_WAIT_MS,
): (signal: AbortSignal) => Promise<SermonText | null> {
  const { peek } = useDraft();
  const api = useApi();
  const queryClient = useQueryClient();
  const churchTranslation = church.effective_translation;
  return useCallback(
    (signal: AbortSignal): Promise<SermonText | null> => {
      const draft = peek();
      return new Promise((resolve) => {
        let settled = false;
        const done = (value: SermonText | null) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          signal.removeEventListener("abort", onAbort);
          resolve(value);
        };
        const onAbort = () => done(null);
        const timer = setTimeout(() => done(null), waitMs);
        signal.addEventListener("abort", onAbort, { once: true });
        void (async () => {
          // The translation step 1 shows: the draft's only while the server still offers it (the list, cached or fetched once).
          const translations =
            draft.readings.translation === null
              ? undefined
              : await queryClient
                  .fetchQuery({
                    queryKey: queryKeys.translations(),
                    queryFn: ({ signal: s }) => api.user<Translations>("/translations", { signal: s }),
                    staleTime: Infinity,
                  })
                  .catch(() => undefined);
          const source = sermonSource(draft, { effective_translation: churchTranslation }, translations);
          if (source === null) return done(null);
          const passage = await queryClient.fetchQuery(passageQuery(api, source.translation, source.ref));
          done(sermonText(source.ref, passage));
        })().catch(() => done(null));
      });
    },
    [api, churchTranslation, peek, queryClient, waitMs],
  );
}
