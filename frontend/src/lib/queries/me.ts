import { queryOptions, useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Me } from "@/lib/api/types";

import { useApi, type Api } from "./client";
import { keys } from "./keys";

/**
 * `GET /me`'s key and fetcher, for every caller (1b clarification 38).
 * `makeQueryClient` has no default `queryFn`, so a bare
 * `fetchQuery({ queryKey: keys.me() })` works only while a `useMe` observer
 * happens to be mounted; `useMembershipChanged` spreads these options instead.
 */
export function meQueryOptions(api: Api) {
  return queryOptions<Me, ApiError>({
    queryKey: keys.me(),
    queryFn: ({ signal }) => api.user<Me>("/me", { signal }),
  });
}

/** `GET /me` (user-scoped): the user and their churches, sorted by name. The `(signed-in)` layout passes `enabled: false` while signing out. */
export function useMe(opts: { enabled?: boolean } = {}): UseQueryResult<Me, ApiError> {
  const api = useApi();
  return useQuery({ ...meQueryOptions(api), enabled: opts.enabled ?? true });
}
