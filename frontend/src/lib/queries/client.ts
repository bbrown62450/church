/**
 * TanStack Query setup (F §4.4) and the bound API clients (F §4.5).
 * Pages and components never call `apiFetch` directly: hooks in
 * `src/lib/queries/<area>.ts` use `useApi()`.
 */
import {
  isServer,
  MutationCache,
  QueryCache,
  QueryClient,
  useMutation,
  type DefaultOptions,
  type Mutation,
  type Query,
  type UseMutationOptions,
  type UseMutationResult,
} from "@tanstack/react-query";
import { useMemo } from "react";

import { ApiError, apiFetch, type ApiOptions } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { getAccessToken, isSigningOut } from "@/lib/auth";
import { useChurch, useOptionalChurch } from "@/lib/church-context";

import { authEvents } from "./auth-events";

/**
 * Worth one automatic retry: the request may never have reached the server
 * (`network_error`, `timeout`) or the server failed (5xx). Never a 4xx, and
 * never `aborted` (the caller or a sign-out cancelled it).
 */
export function isRetryable(e: unknown): boolean {
  if (!(e instanceof ApiError)) return false;
  return e.code === "network_error" || e.code === "timeout" || e.status >= 500;
}

type AnyQuery = Query<unknown, unknown, unknown>;
type AnyMutation = Mutation<unknown, unknown, unknown>;

/** The church a failed query or mutation was for: key ["church", id, …] or `meta.churchId`. */
function churchIdOf(source: AnyQuery | AnyMutation): string | null {
  if ("queryKey" in source) {
    const [scope, id] = source.queryKey;
    return scope === "church" && typeof id === "string" ? id : null;
  }
  const id = source.meta?.churchId;
  return typeof id === "string" ? id : null;
}

/**
 * The caches' `onError` (F §4.4): a 401 asks the `(signed-in)` layout to sign
 * out; a 403 `no_church_access` tells the `(church)` layout which church was
 * lost. A role 403 (no `reason`) emits nothing. While signing out it does
 * nothing, so one sign-out is ever in flight.
 */
export function handleAuthErrors(error: unknown, source: AnyQuery | AnyMutation): void {
  if (isSigningOut()) return;
  if (error instanceof ApiError && error.status === 401) {
    authEvents.signOutRequired();
    return;
  }
  if (isNoChurchAccess(error)) {
    const churchId = churchIdOf(source);
    if (churchId) authEvents.churchAccessLost(churchId);
  }
}

/** A client with the F §4.4 defaults; `overrides` replace single defaults (tests pass `{ queries: { retry: false } }`). */
export function makeQueryClient(overrides: DefaultOptions = {}): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({ onError: handleAuthErrors }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _onMutateResult, mutation) => handleAuthErrors(error, mutation),
    }),
    defaultOptions: {
      ...overrides,
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: true,
        retry: (failureCount, error) => failureCount < 1 && isRetryable(error),
        ...overrides.queries,
      },
      mutations: { retry: false, ...overrides.mutations },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

/** A new client per server render; one client for the life of the browser tab (Next "TanStack Query" guide). */
export function getQueryClient(): QueryClient {
  if (isServer) return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}

/**
 * `useMutation` for a church-scoped call: sets `meta.churchId` to the active
 * church, so `handleAuthErrors` can report a `no_church_access` 403 for it.
 * Use it inside `ChurchProvider` only (it calls `useChurch()`).
 */
export function useChurchMutation<TData = unknown, TError = ApiError, TVariables = void, TOnMutateResult = unknown>(
  options: UseMutationOptions<TData, TError, TVariables, TOnMutateResult>,
): UseMutationResult<TData, TError, TVariables, TOnMutateResult> {
  const church = useChurch();
  return useMutation({ ...options, meta: { ...options.meta, churchId: church.id } });
}

/** `apiFetch` with the token (and, for church calls, `X-Church-Id`) filled in. */
export type ApiCall = <T>(path: string, opts?: Omit<ApiOptions, "token" | "churchId">) => Promise<T>;

export type Api = {
  /** User-scoped routes (`/me`, 1b's `/churches`, `/invites/*`): no church header. */
  user: ApiCall;
  /** Church-scoped routes: `X-Church-Id` from `ChurchProvider`. Throws when called outside it. */
  church: ApiCall;
  /** A church-scoped call for a church that is not (yet) provided: the `(church)` layout's `GET /church`. */
  forChurch(churchId: string): ApiCall;
};

function boundCall(churchId: string | null): ApiCall {
  return async <T>(path: string, opts: Omit<ApiOptions, "token" | "churchId"> = {}) =>
    apiFetch<T>(path, { ...opts, token: await getAccessToken(), churchId });
}

const churchOutsideProvider: ApiCall = () => {
  throw new Error("useApi().church needs a ChurchProvider; use useApi().user or forChurch(id).");
};

/** The bound API clients (F §4.5). Stable while the active church stays the same. */
export function useApi(): Api {
  const churchId = useOptionalChurch()?.id ?? null;
  return useMemo(
    () => ({
      user: boundCall(null),
      church: churchId ? boundCall(churchId) : churchOutsideProvider,
      forChurch: (id: string) => boundCall(id),
    }),
    [churchId],
  );
}
