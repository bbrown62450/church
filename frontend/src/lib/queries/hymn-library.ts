/**
 * Settings → Hymns' queries (slice 6a-2; 6a spec "Queries and mutations").
 *
 * - `useHymnLibrary({ hymnal, q })`: `GET /hymns` 50 at a time ("Show more"),
 *   keyed under ["church", id, "hymns"], so it shares the prefix with the
 *   builder's hymn lists and matches.
 * - `useHymnalSources(enabled)`: `GET /hymnal-sources` (admins).
 * - The writes: add, edit and delete a hymn; add and remove a hymnal. Each
 *   success refreshes every hymn list (the builder's picker among them, with
 *   no reload), the hymnals, the bundled list and the church profile (whose
 *   effective hymnal can change). Not optimistic (F §4.4).
 *
 * Errors: a 401 or a lost church the app already reports. A hymn form's own
 * errors (a 409, or a 422 naming one of its fields: `hymnFieldErrors`) are the
 * form's to show. A role 403 (an admin demoted meanwhile) is toasted and
 * refetches the church profile, so the page turns into the member's view. A
 * hymn deleted elsewhere (404) is toasted as "This hymn was already deleted."
 * and refetches the lists. Anything else is toasted. A hymnal write's failure
 * also refreshes every list, whatever it was: a timed-out add may still have
 * finished on the server (plan review I3).
 */
import { useInfiniteQuery, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type {
  DeletedOut,
  HymnalAdded,
  HymnalRemoved,
  HymnalSources,
  HymnBody,
  HymnDetail,
  HymnPage,
  HymnPatch,
} from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import type { HymnFieldErrors, HymnForm } from "@/lib/settings/hymns";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** Hymns per page in the library (6a spec UX §2b). */
export const LIBRARY_PAGE = 50;
export const HYMN_GONE = "This hymn was already deleted.";

/** The form field each server field name belongs to (`theme` is the Themes box). */
const FORM_FIELD: Record<string, keyof HymnForm> = {
  title: "title",
  number: "number",
  hymnal: "hymnal",
  scripture_refs: "scripture_refs",
  theme: "themes",
  link: "link",
  text_year: "text_year",
  hymnal_count: "hymnal_count",
};

/** A failed add or edit's messages for the hymn form's fields (a 422's `fields`), or null. */
export function hymnFieldErrors(e: unknown): HymnFieldErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const found: HymnFieldErrors = {};
  for (const [name, message] of Object.entries(e.fields)) {
    const field = FORM_FIELD[name];
    if (field) found[field] = message;
  }
  return Object.keys(found).length > 0 ? found : null;
}

/** True for the 409 "{hymnal} already has #{number} {title}." */
export function isDuplicateHymn(e: unknown): boolean {
  return e instanceof ApiError && e.status === 409;
}

/** Every query a hymn or hymnal change can make stale: the hymn lists (the builder's too), hymnals, sources, profile. */
export function refreshHymns(queryClient: QueryClient, churchId: string): void {
  for (const queryKey of [
    [...keys.church(churchId), "hymns"],
    keys.hymnals(churchId),
    keys.hymnalSources(churchId),
    keys.churchProfile(churchId),
  ]) {
    void queryClient.invalidateQueries({ queryKey });
  }
}

export type LibraryFilter = { hymnal: string | null; q: string };

/** `GET /hymns?hymnal=&q=&limit=50&offset=`: the library, in the server's order, a page at a time. */
export function useHymnLibrary({ hymnal, q }: LibraryFilter) {
  const api = useApi();
  const church = useChurch();
  return useInfiniteQuery<HymnPage, ApiError>({
    queryKey: keys.hymns(church.id, { view: "library", hymnal, q }),
    queryFn: ({ pageParam, signal }) => {
      const search = new URLSearchParams({ limit: String(LIBRARY_PAGE), offset: String(pageParam as number) });
      if (hymnal !== null) search.set("hymnal", hymnal);
      if (q !== "") search.set("q", q);
      return api.church<HymnPage>(`/hymns?${search}`, { signal });
    },
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length;
      return last.items.length > 0 && next < last.total ? next : undefined;
    },
  });
}

/** `GET /hymnal-sources` (admins only: a member's page never asks). */
export function useHymnalSources(enabled: boolean) {
  const api = useApi();
  const church = useChurch();
  return useQuery<HymnalSources, ApiError>({
    queryKey: keys.hymnalSources(church.id),
    queryFn: ({ signal }) => api.church<HymnalSources>("/hymnal-sources", { signal }),
    enabled,
  });
}

/** The refresh and the error policy every write shares; `formErrors` true for the hymn form's writes. */
function useHymnWrite<TData, TVariables>(mutationFn: (variables: TVariables) => Promise<TData>, formErrors: boolean) {
  const church = useChurch();
  const queryClient = useQueryClient();
  return useChurchMutation<TData, ApiError, TVariables>({
    mutationFn,
    onSuccess: () => refreshHymns(queryClient, church.id),
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e)) return;
      if (formErrors && (isDuplicateHymn(e) || hymnFieldErrors(e) !== null)) return;
      if (e.status === 404 && formErrors) {
        toast.error(HYMN_GONE);
        refreshHymns(queryClient, church.id);
        return;
      }
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
      // A hymnal write refreshes after any failure: a timed-out add may still have finished on the server.
      if (!formErrors || e.status === 404 || e.status === 409) refreshHymns(queryClient, church.id);
    },
  });
}

/** `POST /hymns` (any member; the year and familiarity are an admin's). */
export function useCreateHymn() {
  const api = useApi();
  return useHymnWrite<HymnDetail, HymnBody>((body) => api.church<HymnDetail>("/hymns", { method: "POST", json: body }), true);
}

/** `PATCH /hymns/{id}`: only the fields that change. */
export function useUpdateHymn() {
  const api = useApi();
  return useHymnWrite<HymnDetail, { id: string; patch: HymnPatch }>(
    ({ id, patch }) => api.church<HymnDetail>(`/hymns/${encodeURIComponent(id)}`, { method: "PATCH", json: patch }),
    true,
  );
}

/** `DELETE /hymns/{id}` (admins). */
export function useDeleteHymn() {
  const api = useApi();
  return useHymnWrite<DeletedOut, string>(
    (id) => api.church<DeletedOut>(`/hymns/${encodeURIComponent(id)}`, { method: "DELETE" }),
    true,
  );
}

/** `POST /hymnals` (admins; 60 s, `timeouts.ts`). */
export function useAddHymnal() {
  const api = useApi();
  return useHymnWrite<HymnalAdded, string>(
    (code) => api.church<HymnalAdded>("/hymnals", { method: "POST", json: { code } }),
    false,
  );
}

/** `DELETE /hymnals/{code}` (admins). */
export function useRemoveHymnal() {
  const api = useApi();
  return useHymnWrite<HymnalRemoved, string>(
    (code) => api.church<HymnalRemoved>(`/hymnals/${encodeURIComponent(code)}`, { method: "DELETE" }),
    false,
  );
}
