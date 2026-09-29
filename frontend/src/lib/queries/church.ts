import { skipToken, useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { ChurchProfile } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/**
 * `GET /church` for `id` (key ["church", id, "profile"]): the server confirms
 * the membership, and since slice 2a returns the profile (`ChurchProfileOut`:
 * timezone, translation). The `(church)` layout calls it above `ChurchProvider`, so it
 * sends the id through `forChurch`. No request while `id` is undefined or
 * `enabled` is false.
 */
export function useChurchProfile(
  id: string | undefined,
  opts: { enabled?: boolean } = {},
): UseQueryResult<ChurchProfile, ApiError> {
  const api = useApi();
  return useQuery<ChurchProfile, ApiError>({
    queryKey: keys.churchProfile(id ?? ""),
    queryFn: id ? ({ signal }) => api.forChurch(id)<ChurchProfile>("/church", { signal }) : skipToken,
    enabled: opts.enabled ?? true,
  });
}
