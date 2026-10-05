import { useQuery, useQueryClient, type QueryClient, type UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/client";
import type { Voices } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** The Catena changes only with a deploy (the server says `max-age=3600` too). */
export const VOICES_STALE_MS = 3_600_000;

// The references the server refused (422) in this session, by query client (one per page load),
// each by its normalized spelling (Voices V1 build review M4).
const refused = new WeakMap<QueryClient, Set<string>>();

function refusedBy(queryClient: QueryClient): Set<string> {
  let found = refused.get(queryClient);
  if (!found) {
    found = new Set();
    refused.set(queryClient, found);
  }
  return found;
}

/** "matthew 29 : 1" and "Matthew 29:1" are one reference: case, dashes and spaces aside. */
export function refusalKey(reference: string): string {
  return reference
    .toLowerCase()
    .replace(/[–—]/g, "-")
    .replace(/\s+/g, " ")
    .replace(/\s*([:;,.()-])\s*/g, "$1")
    .trim();
}

/**
 * `GET /voices?reference=` (Voices V1): user-scoped reference data, so no `X-Church-Id`; key
 * `["ref", "voices", reference]`; nothing asked without a passage; never retried (the panel has
 * Try again). A 422 (no Gospel passage there) is the answer `null`, kept for the session under the
 * reference's normalized spelling: the panel moves between reading rows and remounts, and a query
 * in error would ask again on each mount.
 */
export function useVoices(reference: string | null): UseQueryResult<Voices | null, ApiError> {
  const api = useApi();
  const queryClient = useQueryClient();
  const known = reference !== null && refusedBy(queryClient).has(refusalKey(reference));
  return useQuery<Voices | null, ApiError>({
    queryKey: keys.voices(reference ?? ""),
    queryFn: async ({ signal }) => {
      try {
        return await api.user<Voices>(`/voices?reference=${encodeURIComponent(reference ?? "")}`, { signal });
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 422) throw error;
        refusedBy(queryClient).add(refusalKey(reference ?? ""));
        return null;
      }
    },
    enabled: reference !== null && !known,
    initialData: known ? null : undefined,
    staleTime: (query) => (query.state.data === null ? Infinity : VOICES_STALE_MS),
    retry: 0,
  });
}
