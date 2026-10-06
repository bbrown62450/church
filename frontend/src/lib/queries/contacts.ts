/**
 * The church's contacts (slice 5b-1; 5b spec `useContacts`, 6a spec contact
 * mutations): `GET /contacts` under ["church", id, "contacts"], and the add,
 * edit and delete an admin makes on the Contacts page.
 *
 * Each write puts its answer in the cached list at once (the new row last, as
 * the server orders it; an edited row in its place; a deleted row gone) and
 * then refetches the list. A 409, or a 422 that names the name or the email
 * (`contactFieldErrors`), is the form's to show under its field, so it is not
 * toasted; a 401 or a lost church the app already reports; a role 403 (an
 * admin demoted meanwhile) is toasted and refetches the church profile, which
 * carries the role, so the page turns read-only; anything else (a 404 for a
 * contact deleted elsewhere, which also refetches the list, or a 422 that
 * names no field of the form) is toasted.
 */
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { errorToastMessage, isNoChurchAccess } from "@/lib/api/errors";
import type { Contact, ContactBody, ContactList, ContactPatch, DeletedOut } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import type { ContactForm } from "@/lib/settings/contacts";

import { useApi, useChurchMutation } from "./client";
import { keys } from "./keys";

/** A message under each field of a contact form that a failed add or edit names. */
export type ContactFieldErrors = Partial<Record<keyof ContactForm, string>>;

/**
 * A failed add or edit's message for its field: a 422's `fields.name` or
 * `fields.email`, or a 409 (the address is taken; it has no `fields`) under
 * the email. Null for any other failure, which the mutation toasts.
 */
export function contactFieldErrors(e: unknown): ContactFieldErrors | null {
  if (!(e instanceof ApiError)) return null;
  if (e.status === 409) return { email: e.message };
  if (e.status !== 422 || !e.fields) return null;
  const found: ContactFieldErrors = {};
  for (const field of ["name", "email"] as const) {
    if (e.fields[field]) found[field] = e.fields[field];
  }
  return Object.keys(found).length > 0 ? found : null;
}

/** `GET /contacts` for the active church. */
export function useContacts(): UseQueryResult<ContactList, ApiError> {
  const api = useApi();
  const church = useChurch();
  return useQuery<ContactList, ApiError>({
    queryKey: keys.contacts(church.id),
    queryFn: ({ signal }) => api.church<ContactList>("/contacts", { signal }),
  });
}

/** The cache work and the error handling every contact write shares. */
function useContactWrite<TData, TVariables>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  apply: (items: Contact[], data: TData, variables: TVariables) => Contact[],
) {
  const church = useChurch();
  const queryClient = useQueryClient();
  const key = keys.contacts(church.id);
  return useChurchMutation<TData, ApiError, TVariables>({
    mutationFn,
    onSuccess: async (data, variables) => {
      await queryClient.cancelQueries({ queryKey: key });
      queryClient.setQueryData<ContactList>(key, (list) => (list ? { items: apply(list.items, data, variables) } : list));
      void queryClient.invalidateQueries({ queryKey: key });
    },
    onError: (e) => {
      if (e.status === 401 || isNoChurchAccess(e) || contactFieldErrors(e) !== null) return;
      toast.error(errorToastMessage(e));
      if (e.status === 403) void queryClient.invalidateQueries({ queryKey: keys.churchProfile(church.id) });
      if (e.status === 404) void queryClient.invalidateQueries({ queryKey: key });
    },
  });
}

/** `POST /contacts` (admins). */
export function useCreateContact() {
  const api = useApi();
  return useContactWrite<Contact, ContactBody>(
    (body) => api.church<Contact>("/contacts", { method: "POST", json: body }),
    (items, added) => [...items, added],
  );
}

/** `PATCH /contacts/{id}` (admins): only the fields that change. */
export function useUpdateContact() {
  const api = useApi();
  return useContactWrite<Contact, { id: string; patch: ContactPatch }>(
    ({ id, patch }) => api.church<Contact>(`/contacts/${encodeURIComponent(id)}`, { method: "PATCH", json: patch }),
    (items, saved) => items.map((c) => (c.id === saved.id ? saved : c)),
  );
}

/** `DELETE /contacts/{id}` (admins). */
export function useDeleteContact() {
  const api = useApi();
  return useContactWrite<DeletedOut, string>(
    (id) => api.church<DeletedOut>(`/contacts/${encodeURIComponent(id)}`, { method: "DELETE" }),
    (items, _deleted, id) => items.filter((c) => c.id !== id),
  );
}
