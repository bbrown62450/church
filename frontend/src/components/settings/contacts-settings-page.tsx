"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type ReactNode, type RefObject } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { EmptyState } from "@/components/app/empty-state";
import { ErrorState } from "@/components/app/error-state";
import { LeaveGuard } from "@/components/app/leave-guard";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import type { Contact } from "@/lib/api/types";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import {
  contactFieldErrors,
  useContacts,
  useCreateContact,
  useDeleteContact,
  useUpdateContact,
  type ContactFieldErrors,
} from "@/lib/queries/contacts";
import {
  contactFormFrom,
  contactLabel,
  contactPatch,
  EMPTY_CONTACT,
  hasTyped,
  newContactBody,
  type ContactForm,
} from "@/lib/settings/contacts";

export const CONTACTS_INTRO = "People you can email the bulletin to. Emailing it from the Review step comes in a later update.";
export const ADMINS_ONLY = "Only admins can add or change contacts.";
export const INVALID_ADDRESS_ADMIN = "This address doesn't look valid. Edit it.";
export const INVALID_ADDRESS_MEMBER = "This address doesn't look valid. An admin can fix it.";
export const EMAIL_REQUIRED = "Email is required.";
const EMPTY_TITLE = "No contacts yet";
const EMPTY_ADMIN = "Add the people who receive the bulletin, like your church secretary.";
const EMPTY_MEMBER = "Ask an admin to add bulletin recipients.";
const DELETE_BODY = "They won't be offered as a bulletin recipient anymore.";

type Field = keyof ContactForm;
type FieldErrors = ContactFieldErrors;

/**
 * `/settings/contacts` (slice 5b-1; 6a spec "Contacts"): the people the
 * bulletin is emailed to. Every member reads the list (the name in bold with
 * the address under it, the address alone when there is no name, a note under
 * an address the send-time check refuses); owners and admins also edit and
 * delete each one and add new ones below the list. Leaving with something
 * typed in the add form asks first (`LeaveGuard`); the edit dialog's Cancel
 * discards its edits.
 */
export function ContactsSettingsPage() {
  const church = useChurch();
  const admin = isAdmin(church.role);
  const list = useContacts();
  const nameRef = useRef<HTMLInputElement>(null);
  const [editing, setEditing] = useState<Contact | null>(null);
  const [deleting, setDeleting] = useState<Contact | null>(null);
  // The confirmation's title keeps its contact while the dialog closes (deleting is null by then).
  const [deleteLabel, setDeleteLabel] = useState("");
  // Focus goes to Name only after a delete (the row and its bin are gone); otherwise back to the bin.
  const deleted = useRef(false);
  // After an edit finds its contact deleted elsewhere (a 404) the row and its pencil are gone, so focus
  // goes to the add form's Name once the dialog has closed, never to the page.
  const editGone = useRef(false);
  const remove = useDeleteContact();

  useEffect(() => {
    if (editing !== null || !editGone.current) return;
    editGone.current = false;
    nameRef.current?.focus();
  }, [editing]);

  let body: ReactNode;
  if (list.data) {
    body =
      list.data.items.length === 0 ? (
        <EmptyState title={EMPTY_TITLE} description={admin ? EMPTY_ADMIN : EMPTY_MEMBER} />
      ) : (
        <ul className="divide-y rounded-lg border" aria-label="Contacts">
          {list.data.items.map((contact) => (
            <ContactRow
              key={contact.id}
              contact={contact}
              admin={admin}
              onEdit={() => setEditing(contact)}
              onDelete={() => {
                deleted.current = false;
                setDeleteLabel(contactLabel(contact));
                setDeleting(contact);
              }}
            />
          ))}
        </ul>
      );
  } else if (list.isError) {
    body = <ErrorState error={list.error} onRetry={() => void list.refetch()} retrying={list.isFetching} />;
  } else {
    body = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-14 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  return (
    <section aria-labelledby="contacts-title" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="contacts-title" className="text-lg font-semibold">
          Contacts
        </h2>
        <p className="text-sm text-muted-foreground">{CONTACTS_INTRO}</p>
      </div>
      {admin ? null : (
        <Alert role="status">
          <AlertDescription>{ADMINS_ONLY}</AlertDescription>
        </Alert>
      )}
      {body}
      {admin ? <ContactAddForm nameRef={nameRef} /> : null}
      {admin && editing ? (
        <ContactEditDialog
          contact={editing}
          onClose={(gone) => {
            editGone.current = gone === true;
            setEditing(null);
          }}
        />
      ) : null}
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title={`Delete ${deleteLabel}?`}
        description={DELETE_BODY}
        confirmLabel="Delete contact"
        destructive
        pending={remove.isPending}
        finalFocus={() => (deleted.current ? nameRef.current : true)}
        onConfirm={() => {
          if (deleting === null) return;
          remove.mutate(deleting.id, {
            onSuccess: () => {
              deleted.current = true;
            },
            onError: (e) => {
              if (e.status === 404) deleted.current = true; // deleted elsewhere: gone all the same
            },
            onSettled: () => setDeleting(null),
          });
        }}
      />
    </section>
  );
}

function ContactRow({
  contact,
  admin,
  onEdit,
  onDelete,
}: {
  contact: Contact;
  admin: boolean;
  onEdit(): void;
  onDelete(): void;
}) {
  const label = contactLabel(contact);
  return (
    <li className="flex items-start gap-2 px-4 py-3">
      <div className="grid min-w-0 flex-1 gap-0.5">
        {contact.name !== null ? <p className="font-semibold break-words">{contact.name}</p> : null}
        <p className={contact.name !== null ? "text-sm text-muted-foreground break-all" : "text-sm break-all"}>
          {contact.email}
        </p>
        {contact.email_valid ? null : (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            {admin ? INVALID_ADDRESS_ADMIN : INVALID_ADDRESS_MEMBER}
          </p>
        )}
      </div>
      {admin ? (
        <div className="flex shrink-0 gap-1">
          <Button type="button" variant="ghost" size="icon" className="size-11 md:size-8" aria-label={`Edit ${label}`} onClick={onEdit}>
            <Pencil aria-hidden="true" />
          </Button>
          <Button type="button" variant="ghost" size="icon" className="size-11 md:size-8" aria-label={`Delete ${label}`} onClick={onDelete}>
            <Trash2 aria-hidden="true" />
          </Button>
        </div>
      ) : null}
    </li>
  );
}

/** One field of a contact form, with its error under it (`role="alert"`). */
function ContactField({
  id,
  label,
  field,
  value,
  error,
  inputRef,
  onChange,
}: {
  id: string;
  label: string;
  field: Field;
  value: string;
  error: string | undefined;
  inputRef?: RefObject<HTMLInputElement | null>;
  onChange(value: string): void;
}) {
  const email = field === "email";
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        ref={inputRef}
        value={value}
        maxLength={email ? 320 : 200}
        className="h-11"
        {...(email ? { inputMode: "email" as const, autoCapitalize: "none", autoCorrect: "off", spellCheck: false } : {})}
        autoComplete="off"
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(event) => onChange(event.target.value)}
      />
      {error ? (
        <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </div>
  );
}

/** Below the list, for admins: Name (optional), Email, **Add contact**. */
function ContactAddForm({ nameRef }: { nameRef: RefObject<HTMLInputElement | null> }) {
  const create = useCreateContact();
  const emailRef = useRef<HTMLInputElement>(null);
  const [form, setForm] = useState<ContactForm>(EMPTY_CONTACT);
  const [errors, setErrors] = useState<FieldErrors>({});

  const update = (field: Field, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };

  const focusFirst = (found: FieldErrors) => (found.name ? nameRef : emailRef).current?.focus();

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (create.isPending) return;
    if (form.email.trim() === "") {
      setErrors({ email: EMAIL_REQUIRED });
      emailRef.current?.focus();
      return;
    }
    create.mutate(newContactBody(form), {
      onSuccess: () => {
        setForm(EMPTY_CONTACT);
        setErrors({});
        nameRef.current?.focus();
      },
      onError: (e) => {
        const found = contactFieldErrors(e);
        if (found === null) return;
        setErrors(found);
        focusFirst(found);
      },
    });
  }

  return (
    <form onSubmit={onSubmit} noValidate aria-labelledby="contact-add-title" className="grid gap-4 rounded-lg border p-4">
      <h3 id="contact-add-title" className="text-base font-medium">
        Add a contact
      </h3>
      <ContactField id="contact-add-name" label="Name (optional)" field="name" value={form.name} error={errors.name} inputRef={nameRef} onChange={(v) => update("name", v)} />
      <ContactField id="contact-add-email" label="Email" field="email" value={form.email} error={errors.email} inputRef={emailRef} onChange={(v) => update("email", v)} />
      <PendingButton type="submit" size="touch" className="w-full sm:w-fit" pending={create.isPending}>
        Add contact
      </PendingButton>
      <LeaveGuard when={hasTyped(form)} />
    </form>
  );
}

/** **Edit** on a row: Name and Email, **Save changes**; only the fields that change are sent. */
function ContactEditDialog({ contact, onClose }: { contact: Contact; onClose(gone?: boolean): void }) {
  const save = useUpdateContact();
  const [baseline] = useState(() => contactFormFrom(contact));
  const [form, setForm] = useState<ContactForm>(baseline);
  const [errors, setErrors] = useState<FieldErrors>({});
  const nameRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  const update = (field: Field, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
    if (errors[field]) setErrors((e) => ({ ...e, [field]: undefined }));
  };

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (save.isPending) return;
    if (form.email.trim() === "") {
      setErrors({ email: EMAIL_REQUIRED });
      emailRef.current?.focus();
      return;
    }
    const patch = contactPatch(baseline, form);
    if (Object.keys(patch).length === 0) {
      onClose();
      return;
    }
    save.mutate(
      { id: contact.id, patch },
      {
        onSuccess: () => onClose(),
        onError: (e) => {
          if (e.status === 403 || e.status === 404) {
            onClose(e.status === 404); // toasted, and the role or the list refetched, by the mutation
            return;
          }
          const found = contactFieldErrors(e);
          if (found === null) return;
          setErrors(found);
          (found.name ? nameRef : emailRef).current?.focus();
        },
      },
    );
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-w-lg"
      >
        <DialogHeader>
          <DialogTitle>Edit contact</DialogTitle>
          <DialogDescription>{contactLabel(contact)}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} noValidate className="grid gap-4">
          <ContactField id="contact-edit-name" label="Name (optional)" field="name" value={form.name} error={errors.name} inputRef={nameRef} onChange={(v) => update("name", v)} />
          <ContactField id="contact-edit-email" label="Email" field="email" value={form.email} error={errors.email} inputRef={emailRef} onChange={(v) => update("email", v)} />
          <DialogFooter className="max-md:rounded-b-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            <DialogClose render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>Cancel</DialogClose>
            <PendingButton type="submit" size="touch" className="md:h-8" pending={save.isPending}>
              Save changes
            </PendingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
