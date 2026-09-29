import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Passage, Passages } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** Passage text keeps for a day, except an `unavailable` answer, which is asked again on the next expand or focus. */
export const PASSAGE_STALE_MS = 24 * 3_600_000;

export function passageStaleTime(data: Passage | undefined): number {
  return data?.status === "unavailable" ? 0 : PASSAGE_STALE_MS;
}

/**
 * A promise queue that runs at most `max` tasks at once (S Queries
 * `passageLimiter`). A task starts when a slot frees; one whose `signal`
 * aborts while it waits never starts and rejects with the signal's reason.
 * A settled task, fulfilled or rejected, frees its slot.
 */
export function createLimiter(max: number) {
  let active = 0;
  const waiting: (() => void)[] = [];

  function pump(): void {
    while (active < max && waiting.length > 0) waiting.shift()?.();
  }

  return function limit<T>(task: () => Promise<T>, signal?: AbortSignal): Promise<T> {
    return new Promise<T>((resolve, reject) => {
      const abortReason = () => signal?.reason ?? new DOMException("This operation was aborted", "AbortError");
      if (signal?.aborted) {
        reject(abortReason());
        return;
      }
      const start = () => {
        signal?.removeEventListener("abort", onAbort);
        active += 1;
        Promise.resolve()
          .then(task)
          .then(resolve, reject)
          .finally(() => {
            active -= 1;
            pump();
          });
      };
      const onAbort = () => {
        const at = waiting.indexOf(start);
        if (at >= 0) waiting.splice(at, 1);
        reject(abortReason());
      };
      signal?.addEventListener("abort", onAbort, { once: true });
      waiting.push(start);
      pump();
    });
  };
}

/** At most 3 passage requests in flight from this tab, so "Show all text" on 20 rows never floods the server's pool. */
export const passageLimiter = createLimiter(3);

/** The text of the sections that loaded (`ok`), joined with blank lines; null when none did. For slice 3's `nt_text`. */
export function passageText(p: Passage): string | null {
  const texts = p.sections.filter((s) => s.status === "ok" && s.text).map((s) => s.text as string);
  return texts.length > 0 ? texts.join("\n\n") : null;
}

/**
 * `POST /scripture/passages` for one reference (S Queries): key
 * `["passage", translation, ref]`, user-scoped, through `passageLimiter`, so
 * the 30 s timeout starts when the request is sent. Every 200 is data, even
 * a `not_found` or `unavailable` passage; the row shows it (S UX item 6).
 * Real request errors (network, timeout, 5xx, 429, 422) keep the defaults.
 */
export function usePassage(ref: string, translation: string, enabled: boolean): UseQueryResult<Passage, ApiError> {
  const api = useApi();
  return useQuery<Passage, ApiError>({
    queryKey: keys.passage(translation, ref),
    queryFn: ({ signal }) =>
      passageLimiter(async () => {
        const body = await api.user<Passages>("/scripture/passages", {
          method: "POST",
          json: { refs: [ref], translation },
          signal,
        });
        return body.passages[0];
      }, signal),
    enabled,
    staleTime: (query) => passageStaleTime(query.state.data),
  });
}
