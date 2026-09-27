import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** `GET /me` (user-scoped): the user and their churches, sorted by name. The `(signed-in)` layout passes `enabled: false` while signing out. */
export function useMe(opts: { enabled?: boolean } = {}): UseQueryResult<Me, ApiError> {
  const api = useApi();
  return useQuery<Me, ApiError>({
    queryKey: keys.me(),
    queryFn: ({ signal }) => api.user<Me>("/me", { signal }),
    enabled: opts.enabled ?? true,
  });
}
