import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import type { ApiError } from "@/lib/api/client";
import type { Translations } from "@/lib/api/types";

import { useApi } from "./client";
import { keys } from "./keys";

/** `GET /translations` (S Queries): user-scoped reference data, key `["ref", "translations"]`, never stale. */
export function useTranslations(): UseQueryResult<Translations, ApiError> {
  const api = useApi();
  return useQuery<Translations, ApiError>({
    queryKey: keys.translations(),
    queryFn: ({ signal }) => api.user<Translations>("/translations", { signal }),
    staleTime: Infinity,
  });
}
