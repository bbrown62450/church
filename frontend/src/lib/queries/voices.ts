import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Voices } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** The Catena changes only with a deploy (the server says `max-age=3600` too). */
export const VOICES_STALE_MS = 3_600_000;

/**
 * `GET /voices?reference=` (Voices V1): user-scoped reference data, so no `X-Church-Id`; key
 * `["ref", "voices", reference]`; nothing asked without a passage; never retried (the panel has
 * Try again).
 */
export function useVoices(reference: string | null): UseQueryResult<Voices, ApiError> {
  const api = useApi();
  return useQuery<Voices, ApiError>({
    queryKey: keys.voices(reference ?? ""),
    queryFn: ({ signal }) => api.user<Voices>(`/voices?reference=${encodeURIComponent(reference ?? "")}`, { signal }),
    enabled: reference !== null,
    staleTime: VOICES_STALE_MS,
    retry: 0,
  });
}
