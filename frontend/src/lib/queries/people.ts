/**
 * Settings → People's queries (slice 6b-2a; 6b spec "Queries and mutations"):
 * `GET /members` under ["church", id, "members"], `GET /invites` under
 * ["church", id, "invites"] (owners and admins only; never cached as fresh,
 * since its codes are secrets and a revoked link must not linger), and the
 * role change, removal, invite and revoke an owner or admin makes.
 *
 * A role 403 (an admin demoted elsewhere; no `details.reason`) is toasted and
 * refetches the church profile, which carries the role, and the member list,
 * so the page turns read-only and the user stays in the church (6a's way:
 * each hook handles it, not a cache-wide `forbiddenIsRole` meta). A 401 or a
 * lost church (`no_church_access`) is the app's: it signs out or falls back
 * to another church. Writes are not optimistic: each puts the answer in the
 * cache, then refetches.
 */
import { useQuery, useQueryClient, type QueryClient, type UseQueryResult } from "@tanstack/react-query";
import { useEffect } from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type {
  Invite,
  InviteBody,
  InviteList,
  InviteRevoked,
  Member,
  MemberList,
  MemberRemoved,
} from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** A 403 that is about the role, not the church: the server's role refusal. */
export function isRoleRefusal(e: unknown): boolean {
  return e instanceof ApiError && e.status === 403 && !isNoChurchAccess(e);
}

/** A role refusal's toast and refetches: the page re-renders for the role the user has now. */
function onRoleRefused(queryClient: QueryClient, churchId: string, e: ApiError): void {
  toast.error(errorToastMessage(e));
  void queryClient.invalidateQueries({ queryKey: keys.churchProfile(churchId) });
  void queryClient.invalidateQueries({ queryKey: keys.members(churchId) });
}

/**
 * A failed write's handling: nothing for a 401 or a lost church (the app's),
 * nothing for a failure `isForm` says the form shows under a field, a role
 * refusal as above, and any other message toasted (a 404 also refetches
 * `refetchKey`, the list the missing row came from).
 */
function onWriteError(queryClient: QueryClient, churchId: string, refetchKey: readonly unknown[],
                      isForm: (e: ApiError) => boolean = () => false) {
  return (e: ApiError) => {
    if (e.status === 401 || isNoChurchAccess(e) || isForm(e)) return;
    if (isRoleRefusal(e)) {
      onRoleRefused(queryClient, churchId, e);
      return;
    }
    toast.error(errorToastMessage(e));
    if (e.status === 404) void queryClient.invalidateQueries({ queryKey: refetchKey });
  };
}

/** `GET /members`: everyone in the church, with emails (every role). */
export function useMembers(): UseQueryResult<MemberList, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<MemberList, ApiError>({
    queryKey: keys.members(church.id),
    queryFn: ({ signal }) => api.church<MemberList>("/members", { signal }),
  });
}

/**
 * `GET /invites` (owners and admins; no request otherwise): the live links,
 * newest first. A role refusal is handled as for a write, here in the query,
 * so a demoted admin's page turns read-only. Once the role no longer allows
 * it (`enabled` false), the cached list and its codes are removed. Not at the
 * refusal itself: the page's queries are still enabled then, so they would
 * fetch the list again and be refused again until the new role arrives.
 */
export function useInvites({ enabled }: { enabled: boolean }): UseQueryResult<InviteList, ApiError> {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!enabled) queryClient.removeQueries({ queryKey: keys.invites(church.id) });
  }, [enabled, church.id, queryClient]);
  return useQuery<InviteList, ApiError>({
    queryKey: keys.invites(church.id),
    queryFn: async ({ signal }) => {
      try {
        return await api.church<InviteList>("/invites", { signal });
      } catch (e) {
        if (e instanceof ApiError && isRoleRefusal(e)) onRoleRefused(queryClient, church.id, e);
        throw e;
      }
    },
    enabled,
    staleTime: 0,
  });
}

/** `PATCH /members/{user_id}` (owners and admins): make a member an admin or an admin a member. */
export function useChangeRole() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.members(church.id);
  return useChurchMutation<Member, ApiError, { userId: string; role: "member" | "admin" }>({
    mutationFn: ({ userId, role }) =>
      api.church<Member>(`/members/${encodeURIComponent(userId)}`, { method: "PATCH", json: { role } }),
    onSuccess: async (saved) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<MemberList>(key, (list) =>
        list ? { items: list.items.map((m) => (m.user_id === saved.user_id ? saved : m)) } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}

/**
 * `DELETE /members/{user_id}?revoke_reusable=` (owners and admins): the
 * removal also revokes the invites the person made, and with
 * `revokeReusable` every live reusable link, so both lists refetch.
 */
export function useRemoveMember() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.members(church.id);
  return useChurchMutation<MemberRemoved, ApiError, { userId: string; revokeReusable: boolean }>({
    mutationFn: ({ userId, revokeReusable }) =>
      api.church<MemberRemoved>(`/members/${encodeURIComponent(userId)}?revoke_reusable=${revokeReusable}`, {
        method: "DELETE",
      }),
    onSuccess: async (_removed, { userId }) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<MemberList>(key, (list) =>
        list ? { items: list.items.filter((m) => m.user_id !== userId) } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
      void queryClient.invalidateQueries({ queryKey: keys.invites(church.id) });
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}

/**
 * A failed invite's message for the form (409 `invite_exists` or `conflict`,
 * or a 422 naming the email or the reusable box): `{field, message}`, or null
 * for anything else, which the mutation toasts.
 */
export function inviteFieldError(e: unknown): { field: "email" | "reusable"; message: string } | null {
  if (!(e instanceof ApiError)) return null;
  if (e.status === 409) return { field: "email", message: e.message };
  if (e.status !== 422) return null;
  if (e.fields?.email) return { field: "email", message: e.fields.email };
  if (e.fields?.reusable) return { field: "reusable", message: e.fields.reusable };
  return null;
}

/**
 * `POST /invites` (owners and admins), with a new `Idempotency-Key` for every
 * click (6b spec), so a repeat of the same request is never a second link.
 * The new invite goes first in the cached list, then the list refetches.
 */
export function useCreateInvite() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.invites(church.id);
  return useChurchMutation<Invite, ApiError, InviteBody>({
    mutationFn: (body) =>
      api.church<Invite>("/invites", { method: "POST", json: body, idempotencyKey: crypto.randomUUID() }),
    onSuccess: async (created) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<InviteList>(key, (list) =>
        list ? { items: [created, ...list.items.filter((i) => i.id !== created.id)] } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: onWriteError(queryClient, church.id, key, (e) => inviteFieldError(e) !== null),
  });
}

/** `DELETE /invites/{invite_id}` (owners and admins): the link stops working. */
export function useRevokeInvite() {
  const api = useApi();
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.invites(church.id);
  return useChurchMutation<InviteRevoked, ApiError, string>({
    mutationFn: (inviteId) => api.church<InviteRevoked>(`/invites/${encodeURIComponent(inviteId)}`, { method: "DELETE" }),
    onSuccess: async (_revoked, inviteId) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<InviteList>(key, (list) =>
        list ? { items: list.items.filter((i) => i.id !== inviteId) } : list,
      );
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: onWriteError(queryClient, church.id, key),
  });
}
