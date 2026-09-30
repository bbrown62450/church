/**
 * The Hymns step's queries (S Queries; F §4.4). All church-scoped
 * (`api.church`, so every request carries `X-Church-Id`), keyed under
 * ["church", id, "hymns"] or ["church", id, "hymnals"], with F §4.4's
 * defaults (30 s stale, refetch on focus, one retry for a retryable error).
 */
import { useQueries, useQuery, type UseQueryResult } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/api/client";
import type {
  Hymn,
  Hymnals,
  HymnPage,
  HymnSuggestionBody,
  HymnSuggestions,
  ScriptureMatchBody,
  ScriptureMatches,
} from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { createLatestTracker } from "@/lib/latest";

import { useApi, useChurchMutation, type Api } from "./client";
import { keys } from "./keys";

/** A whole hymnal in one page (the largest has about 1 000 hymns; S API). */
export const HYMN_LIST_LIMIT = 2000;
/** At most this many hymnal lists at once: the selected one plus the picks' (S Queries). */
export const MAX_LISTS = 4;
/** Match results asked for (S Queries). */
export const MATCH_RESULTS = 30;

/** `GET /hymnals`: the church's hymnals, the stored default and the effective one. */
export function useHymnals(): UseQueryResult<Hymnals, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<Hymnals, ApiError>({
    queryKey: keys.hymnals(church.id),
    queryFn: ({ signal }) => api.church<Hymnals>("/hymnals", { signal }),
  });
}

function hymnListQuery(api: Api, churchId: string, hymnal: string, recentForDate: string | null) {
  const params = { hymnal, limit: HYMN_LIST_LIMIT, recent_for_date: recentForDate };
  const search = new URLSearchParams({ hymnal, limit: String(HYMN_LIST_LIMIT) });
  if (recentForDate !== null) search.set("recent_for_date", recentForDate);
  return {
    queryKey: keys.hymns(churchId, params),
    queryFn: ({ signal }: { signal: AbortSignal }) => api.church<HymnPage>(`/hymns?${search}`, { signal }),
    select: (page: HymnPage): Hymn[] => page.items,
  };
}

/**
 * One hymnal's whole list (`GET /hymns?hymnal=…&limit=2000&recent_for_date=…`).
 * No request without a hymnal; `recentForDate` is null when the draft's date
 * is not valid, and is then left out (S Queries).
 */
export function useHymnList(hymnal: string | null, recentForDate: string | null): UseQueryResult<Hymn[], ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery({ ...hymnListQuery(api, church.id, hymnal ?? "", recentForDate), enabled: hymnal !== null });
}

export type HymnLists = {
  /** Each hymnal's list; undefined while it loads or when it failed. */
  lists: Map<string, Hymn[] | undefined>;
  /** The hymnals whose list failed. */
  failed: ReadonlySet<string>;
  /** True while any of them is being fetched (a Retry's spinner). */
  fetching: boolean;
  /** Asks again for every list that failed. */
  retry: () => void;
};

/**
 * Several hymnals' lists (the selected one and every pick's), each distinct
 * non-null code once, at most `MAX_LISTS`, so a pick from another hymnal can
 * show its live title and be checked. The same keys as `useHymnList`, so the
 * two share the cache.
 */
export function useHymnLists(hymnals: readonly (string | null)[], recentForDate: string | null): HymnLists {
  const api = useApi();
  const church = useChurch();
  const codes = [...new Set(hymnals.filter((code): code is string => code !== null))].slice(0, MAX_LISTS);
  const results = useQueries({ queries: codes.map((code) => hymnListQuery(api, church.id, code, recentForDate)) });
  return {
    lists: new Map(codes.map((code, i) => [code, results[i].data] as const)),
    failed: new Set(codes.filter((_, i) => results[i].isError)),
    fetching: results.some((r) => r.isFetching),
    retry: () => {
      for (const r of results) if (r.isError) void r.refetch();
    },
  };
}

export type MatchParams = {
  /** From `buildMatchRefs`, never the raw draft lines. */
  refs: string[];
  /** The selected hymnal. */
  hymnal: string | null;
  recentForDate: string | null;
  /** False for a hymnal with no scripture references. */
  enabled: boolean;
};

/**
 * `POST /hymns/scripture-matches` as a query (S Queries): it runs again
 * whenever the references, the hymnal or the date change; nothing is sent
 * without references or a hymnal, or when `enabled` is false.
 */
export function useScriptureMatches({ refs, hymnal, recentForDate, enabled }: MatchParams): UseQueryResult<ScriptureMatches, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<ScriptureMatches, ApiError>({
    queryKey: keys.hymnMatches(church.id, { refs, hymnal, recent_for_date: recentForDate }),
    queryFn: ({ signal }) => {
      const json: Omit<ScriptureMatchBody, "limit_per_ref"> = { refs, hymnal, recent_for_date: recentForDate, max_results: MATCH_RESULTS };
      return api.church<ScriptureMatches>("/hymns/scripture-matches", { method: "POST", json, signal });
    },
    enabled: enabled && refs.length > 0 && hymnal !== null,
  });
}

export type SuggestOutcome =
  | { status: "ok"; data: HymnSuggestions }
  | { status: "error"; error: ApiError }
  /** A newer request started, the step unmounted or the church changed: apply nothing, show nothing. */
  | { status: "superseded" };

/**
 * `POST /hymns/suggestions` (S "Stale and cross-church protection"): a 90 s
 * timeout (`timeouts.ts`) and the caller's signal (Cancel). Each call is
 * tracked with `createLatestTracker` and records the church it was sent for,
 * so an older answer never overwrites a newer one and no answer reaches a
 * step that unmounted (a church switch remounts it). The caller still checks
 * the draft's date before applying. Nothing is invalidated: it writes nothing.
 */
export function useSuggestHymns(): {
  suggest: (body: HymnSuggestionBody, signal?: AbortSignal) => Promise<SuggestOutcome>;
  isPending: boolean;
} {
  const api = useApi();
  const church = useChurch();
  const [tracker] = useState(createLatestTracker);
  const mounted = useRef(false);
  const currentChurch = useRef(church.id);
  const mutation = useChurchMutation<HymnSuggestions, ApiError, { body: HymnSuggestionBody; signal?: AbortSignal }>({
    mutationFn: ({ body, signal }) =>
      api.church<HymnSuggestions>("/hymns/suggestions", { method: "POST", json: body, signal }),
  });
  const { mutateAsync } = mutation;

  useEffect(() => {
    currentChurch.current = church.id;
  }, [church.id]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const suggest = useCallback(
    async (body: HymnSuggestionBody, signal?: AbortSignal): Promise<SuggestOutcome> => {
      const isLatest = tracker.begin();
      const sentFor = church.id;
      const current = () => mounted.current && isLatest() && currentChurch.current === sentFor;
      try {
        const data = await mutateAsync({ body, signal });
        return current() ? { status: "ok", data } : { status: "superseded" };
      } catch (e) {
        if (!current()) return { status: "superseded" };
        const error = e instanceof ApiError ? e : new ApiError(0, "unknown", "Something went wrong.");
        return { status: "error", error };
      }
    },
    [tracker, church.id, mutateAsync],
  );

  return { suggest, isPending: mutation.isPending };
}
