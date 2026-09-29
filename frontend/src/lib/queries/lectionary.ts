import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Lectionary } from "@/lib/api/types";
import { inSupportedRange, isValidDateIso } from "@/lib/dates";

import { useApi } from "./client";
import { keys } from "./keys";

/** A complete answer keeps for a day; a partial one (a source failed) is looked up again after 5 minutes. */
export const LECTIONARY_STALE_MS = 24 * 3_600_000;
export const PARTIAL_LECTIONARY_STALE_MS = 5 * 60_000;

export function lectionaryStaleTime(data: Lectionary | undefined): number {
  return data?.partial ? PARTIAL_LECTIONARY_STALE_MS : LECTIONARY_STALE_MS;
}

/** A date the lookup accepts: a real `YYYY-MM-DD` in 1900-2199 (S UX item 1). */
export function canLookUp(dateIso: string): boolean {
  return isValidDateIso(dateIso) && inSupportedRange(dateIso);
}

/**
 * `GET /lectionary/readings?date=` (S Queries; F §4.4): user-scoped, so no
 * `X-Church-Id`; key `["lectionary", dateIso]`; no request for a date the
 * lookup refuses; never retried (a failure shows "Try again", and the server
 * caches a failed source for 5 minutes); a 25 s timeout (`timeouts.ts`).
 */
export function useLectionary(dateIso: string): UseQueryResult<Lectionary, ApiError> {
  const api = useApi();
  return useQuery<Lectionary, ApiError>({
    queryKey: keys.lectionary(dateIso),
    queryFn: ({ signal }) => api.user<Lectionary>(`/lectionary/readings?date=${encodeURIComponent(dateIso)}`, { signal }),
    enabled: canLookUp(dateIso),
    staleTime: (query) => lectionaryStaleTime(query.state.data),
    retry: 0,
  });
}
