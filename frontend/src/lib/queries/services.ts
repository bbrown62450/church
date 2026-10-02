/**
 * The archive (slice 5a spec, Frontend `lib/queries/services.ts`; F §4.4
 * keys and invalidations, §1.6 key rule, §1.7 `If-Match`). Every call is
 * church-scoped (`api.church`); a 401 or a lost church goes through the
 * caches' `handleAuthErrors` (`useChurchMutation`) and shows nothing more.
 *
 * - `useServices()`: the list, 20 a page, newest service date first (the
 *   server's order), "Show more" reading the next offset.
 * - `useSaveService(church)`: Save. "Save changes" PUTs with `If-Match` (the
 *   `saved_at` the draft holds); a 404 without `details.field` (the service
 *   was deleted) POSTs instead and says so. A 409 reads the archive's copy:
 *   when it is what this save sends (this device's earlier save went through
 *   but its answer was lost, a timeout), that is the save; otherwise the 409
 *   is left to the Save card (the conflict dialog). "Save to archive", "Save
 *   as new service" and the dialog's "Save mine as a new service" POST with
 *   the draft's save key (`save-key.ts`, kept through `autoUpdate`, so the
 *   bookkeeping never outranks an edit in another tab): replaced after any
 *   answer, kept for an identical retry after an unknown outcome, and one
 *   automatic retry with a new key after `idempotency_mismatch`. Success
 *   records the save in the draft (`markSaved`), caches the service, and
 *   refreshes the list and the hymns (a save rebuilds that date's hymn use,
 *   so `recently_used` changes).
 *   A replayed POST answer (the same key and body within 15 minutes) is the
 *   first answer; if that service was changed or deleted since, the next
 *   "Save changes" meets the 409 or the 404 above, which already handle it.
 * - `useOpenService(church)`: `GET /services/{id}` (always fetched), then the
 *   draft becomes `serviceToDraft(service)`. A 404 refreshes the list.
 * - `useDeleteService(church)`: `DELETE`, then the list and the hymns (a
 *   delete rebuilds that date's hymn use) are refreshed before it settles,
 *   so the row is gone when the dialog closes; deleting the service being
 *   edited resets the draft (F §4.6 rule 2), keeping the translation as New
 *   service does. A 404 refreshes the list.
 */
import { useInfiniteQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { DeletedOut, ServiceOut, ServicePage } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { savedCopyFingerprint, serviceBody } from "@/lib/documents";
import { useDraft } from "@/lib/draft/context";
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload, markSaved, serviceToDraft } from "@/lib/draft/mapping";
import { keyForPost, settlePost } from "@/lib/draft/save-key";
import { freshDraft, type DraftChurch } from "@/lib/draft/schema";
import { saveMode } from "@/lib/draft/status";
import { settleOutcome } from "@/lib/idempotency";
import { useMeContext } from "@/lib/me-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

export const SERVICES_PAGE_SIZE = 20;
export const SAVED_MESSAGE = "Service saved";
export const SAVED_AFTER_DELETE_MESSAGE = "The archived copy was deleted, so this was saved as a new service.";

/** A 401 or a lost church: the app's own handling already says it. */
function handledElsewhere(e: ApiError): boolean {
  return e.status === 401 || isNoChurchAccess(e);
}

/** `PUT /services/{id}`'s 409: someone else saved this service since it was saved or opened here. */
export function isConflict(e: unknown): boolean {
  return e instanceof ApiError && e.status === 409 && e.code === "conflict";
}

/** A hymn id the church no longer has: 404 with `details.field` "hymns.<slot>.hymn_id". */
function isHymnGone(e: ApiError): boolean {
  return e.status === 404 && typeof e.details?.field === "string";
}

function servicesKey(churchId: string) {
  return [...keys.church(churchId), "services"] as const;
}

function hymnsKey(churchId: string) {
  return [...keys.church(churchId), "hymns"] as const;
}

export function useServices() {
  const api = useApi();
  const church = useChurch();
  return useInfiniteQuery<ServicePage, ApiError>({
    queryKey: keys.services(church.id, { limit: SERVICES_PAGE_SIZE }),
    queryFn: ({ pageParam, signal }) =>
      api.church<ServicePage>(`/services?limit=${SERVICES_PAGE_SIZE}&offset=${pageParam as number}`, { signal }),
    initialPageParam: 0,
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length;
      return last.items.length > 0 && next < last.total ? next : undefined;
    },
  });
}

/** Save's mutation key, so a page with its own draft provider can tell when a save settles. */
export const SAVE_SERVICE_KEY = ["saveService"] as const;

/**
 * For `DraftProvider`'s `resync`: calls `sync` each time a save settles. A
 * save that finishes after the builder unmounted (Services opened while it
 * was in flight) records itself through the builder's store; the Services
 * page's provider then reads it from storage, so its rows show "Editing" and
 * opening another service asks nothing it should not (build review M1).
 */
export function resyncAfterSave(queryClient: QueryClient): (sync: () => void) => () => void {
  return (sync) =>
    queryClient.getMutationCache().subscribe((event) => {
      if (event.type !== "updated" || (event.action.type !== "success" && event.action.type !== "error")) return;
      const key = event.mutation.options.mutationKey;
      if (key?.[0] === SAVE_SERVICE_KEY[0]) sync();
    });
}

export type SaveVariables = { asNew?: boolean };
type Saved = { service: ServiceOut; fp: string; fellBack: boolean };

export function useSaveService(church: DraftChurch) {
  const api = useApi();
  const queryClient = useQueryClient();
  const router = useRouter();
  const { peek, update, autoUpdate, flush } = useDraft();
  return useChurchMutation<Saved, ApiError, SaveVariables>({
    mutationKey: SAVE_SERVICE_KEY,
    mutationFn: async ({ asNew = false }) => {
      const draft = peek();
      const fp = fingerprint(draftToServicePayload(draft));
      const body = serviceBody(draft);

      async function post(retried: boolean): Promise<ServiceOut> {
        autoUpdate((d) => keyForPost(d, fp));
        try {
          const out = await api.church<ServiceOut>("/services", { method: "POST", json: body, idempotencyKey: peek().save_key });
          autoUpdate((d) => settlePost(d, "success"));
          return out;
        } catch (e) {
          autoUpdate((d) => settlePost(d, settleOutcome(e)));
          if (!retried && e instanceof ApiError && e.code === "idempotency_mismatch") return post(true);
          throw e;
        }
      }

      /**
       * The archive's copy when it is what this save sends, both read as the
       * archive keeps them (`savedCopyFingerprint`: a hymn the server resolved
       * by title, a text the body cut to its limit; a body that leaves the
       * hymnal to the church sends none); else null.
       */
      async function sameAsSent(serviceId: string): Promise<ServiceOut | null> {
        try {
          const theirs = await api.church<ServiceOut>(`/services/${serviceId}`);
          const withHymnal = body.hymnal != null;
          return savedCopyFingerprint(theirs, { withHymnal }) === savedCopyFingerprint(body, { withHymnal }) ? theirs : null;
        } catch {
          return null;
        }
      }

      const editing = draft.editing;
      if (!asNew && editing !== null && saveMode(draft) === "update") {
        try {
          const service = await api.church<ServiceOut>(`/services/${editing.service_id}`, {
            method: "PUT",
            json: body,
            ifMatch: editing.saved_at,
          });
          return { service, fp, fellBack: false };
        } catch (e) {
          // A 409 that answers this device's own earlier save (its answer was lost): already saved.
          if (isConflict(e)) {
            const theirs = await sameAsSent(editing.service_id);
            if (theirs !== null) return { service: theirs, fp, fellBack: false };
            throw e;
          }
          // The saved copy was deleted (a 404 with no field): save this one as a new service.
          if (!(e instanceof ApiError) || e.status !== 404 || e.details?.field !== undefined) throw e;
          return { service: await post(false), fp, fellBack: true };
        }
      }
      return { service: await post(false), fp, fellBack: false };
    },
    onSuccess: ({ service, fp, fellBack }) => {
      update((d) => markSaved(d, service, fp));
      queryClient.setQueryData(keys.service(church.id, service.id), service);
      void queryClient.invalidateQueries({ queryKey: servicesKey(church.id) });
      void queryClient.invalidateQueries({ queryKey: hymnsKey(church.id) });
      toast.success(fellBack ? SAVED_AFTER_DELETE_MESSAGE : SAVED_MESSAGE);
    },
    // Written now, not 400 ms later: the builder may have unmounted while the
    // save was in flight, and the Services page re-reads the stored draft as
    // this mutation settles (`resyncAfterSave`, build review M1).
    onSettled: () => flush(),
    onError: (e) => {
      if (handledElsewhere(e) || isConflict(e)) return;
      if (isHymnGone(e)) {
        toast.error(e.message, { action: { label: "Go to Hymns", onClick: () => router.push("/builder/hymns") } });
        return;
      }
      toast.error(errorToastMessage(e));
    },
  });
}

export function useOpenService(church: DraftChurch) {
  const api = useApi();
  const queryClient = useQueryClient();
  const me = useMeContext();
  const { replace } = useDraft();
  return useChurchMutation<ServiceOut, ApiError, string>({
    mutationFn: (serviceId) => api.church<ServiceOut>(`/services/${serviceId}`),
    onSuccess: (service) => {
      queryClient.setQueryData(keys.service(church.id, service.id), service);
      replace(serviceToDraft(service, { church, user: me.user }));
    },
    onError: (e) => {
      if (handledElsewhere(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 404) void queryClient.invalidateQueries({ queryKey: servicesKey(church.id) });
    },
  });
}

export function useDeleteService(church: DraftChurch) {
  const api = useApi();
  const queryClient = useQueryClient();
  const me = useMeContext();
  const { peek, replace } = useDraft();
  return useChurchMutation<DeletedOut, ApiError, string>({
    mutationFn: (serviceId) => api.church<DeletedOut>(`/services/${serviceId}`, { method: "DELETE" }),
    onSuccess: async (_out, serviceId) => {
      queryClient.removeQueries({ queryKey: keys.service(church.id, serviceId) });
      const draft = peek();
      if (draft.editing?.service_id === serviceId) {
        const fresh = freshDraft({ church, user: me.user });
        replace({ ...fresh, readings: { ...fresh.readings, translation: draft.readings.translation } });
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: servicesKey(church.id) }),
        queryClient.invalidateQueries({ queryKey: hymnsKey(church.id) }),
      ]);
    },
    onError: (e) => {
      if (handledElsewhere(e)) return;
      toast.error(errorToastMessage(e));
      if (e.status === 404) void queryClient.invalidateQueries({ queryKey: servicesKey(church.id) });
    },
  });
}
