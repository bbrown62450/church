/**
 * The Liturgy step's API calls (slice 4 spec, "API client usage"; F §4.4).
 *
 * - `useLiturgyConfig()`: `GET /liturgy/config`, user-scoped reference data
 *   under ["ref", "liturgy-config"], never stale. A key added to Railway later
 *   (`ai_available`) takes effect on the next page load.
 * - `generateSection(call, section, body, signal)`: one
 *   `POST /liturgy/generate`, church-scoped, returning that section's result.
 *   A plain async function, because the provider's per-section queue and
 *   cancel do not fit `useMutation`; it still lives here, so no page calls
 *   `apiFetch`. Its client timeout is 100 s (`lib/api/timeouts.ts`, owner
 *   answer 2, 2026-09-30).
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/client";
import type { GenerateLiturgyBody, GenerateLiturgyResult, LiturgyConfig, SectionResult } from "@/lib/api/types";
import type { SectionKey } from "@/lib/draft/schema";

import { useApi, type ApiCall } from "./client";
import { keys } from "./keys";

export function useLiturgyConfig(): UseQueryResult<LiturgyConfig, ApiError> {
  const api = useApi();
  return useQuery<LiturgyConfig, ApiError>({
    queryKey: keys.liturgyConfig(),
    queryFn: ({ signal }) => api.user<LiturgyConfig>("/liturgy/config", { signal }),
    staleTime: Infinity,
  });
}

export async function generateSection(
  call: ApiCall,
  section: SectionKey,
  body: GenerateLiturgyBody,
  signal?: AbortSignal,
): Promise<SectionResult> {
  const out = await call<GenerateLiturgyResult>("/liturgy/generate", { method: "POST", json: body, signal });
  const result = out.results.find((r) => r.section === section);
  if (!result) throw new ApiError(0, "unknown", "Something went wrong.");
  return result;
}
