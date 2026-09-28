import { skipToken, useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Church } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/**
 * `GET /church` for `id` (key ["church", id, "profile"]): the server confirms
 * the membership. The `(church)` layout calls it above `ChurchProvider`, so it
 * sends the id through `forChurch`. No request while `id` is undefined or
 * `enabled` is false.
 */
export function useChurchProfile(
  id: string | undefined,
  opts: { enabled?: boolean } = {},
): UseQueryResult<Church, ApiError> {
  const api = useApi();
  return useQuery<Church, ApiError>({
    queryKey: keys.churchProfile(id ?? ""),
    queryFn: id ? ({ signal }) => api.forChurch(id)<Church>("/church", { signal }) : skipToken,
    enabled: opts.enabled ?? true,
  });
}
