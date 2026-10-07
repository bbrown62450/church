"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRef, useState, type FormEvent, type ReactNode } from "react";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { useStillWorking } from "@/components/builder/liturgy/use-still-working";
import { Button, buttonVariants } from "@/components/ui/button";
import { Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import { isAdmin } from "@/lib/church";
import { useChurch } from "@/lib/church-context";
import { docxFilename, printedFilename } from "@/lib/download";
import { useDraft } from "@/lib/draft/context";
import { isDirty, stillNeeded } from "@/lib/draft/status";
import {
  ATTACHMENT_KINDS,
  ATTACHMENT_LABELS,
  bulletinEmailBody,
  bulletinEmailSubject,
  countRecipients,
  fieldTarget,
  MAX_RECIPIENTS,
  MESSAGE_MAX_LENGTH,
  parseAddressList,
  type AttachmentKind,
  type EmailForm,
  type FieldTarget,
} from "@/lib/email";
import { gmailErrorMessage } from "@/lib/gmail";
import { settleOutcome, type KeyTracker } from "@/lib/idempotency";
import { useContacts } from "@/lib/queries/contacts";
import { useSendBulletinEmail } from "@/lib/queries/email";
import { useStartGmailConnect } from "@/lib/queries/gmail";
import { keys } from "@/lib/queries/keys";

import { NotFilledInLines } from "./printed-card";

export const BCC_NOTE = "Recipients won't see each other's addresses (sent as BCC).";
export const CHOOSE_RECIPIENT = "Choose at least one recipient.";
export const TOO_MANY = `You can email at most ${MAX_RECIPIENTS} people at once.`;
export const CHOOSE_ATTACHMENT = "Choose at least one attachment.";
export const NO_CONTACTS = "No saved contacts yet. Type addresses below.";
export const CONTACTS_ERROR = "Couldn't load your contacts.";
export const INVALID_CONTACT = "This address doesn't look valid. An admin can fix it in Settings → Contacts.";
export const NOT_SAVED_NOTE = "Not saved to the archive yet. The attachments use the service as it is on screen now.";
export const CONNECTION_LOST =
  "We lost the connection before Gmail confirmed, so the email may already have been sent. Check your Gmail Sent folder before sending again.";
const REVIEW_PATH = "/builder/review";

/** One failed send, shown in the dialog: a message per place, and what the user can do next. */
type Problem = Partial<Record<FieldTarget, string>> & {
  action?: "connect" | "reconnect" | "again" | "hymns";
  sendDisabled?: boolean;
};

/** "1 person", "2 people". */
export function people(n: number): string {
  return `${n} ${n === 1 ? "person" : "people"}`;
}

/** "Not finished yet: 2 items under Still to do." */
function unfinishedNote(count: number): string {
  return `Not finished yet: ${count} ${count === 1 ? "item" : "items"} under Still to do.`;
}

type Props = {
  googleEmail: string;
  form: EmailForm;
  onFormChange(change: Partial<EmailForm>): void;
  tracker: KeyTracker;
  /** A send that may already have gone out (kept by the card in sessionStorage), or null. */
  uncertain: string | null;
  onUncertain(message: string | null): void;
  onClose(): void;
  onSent(count: number, contactIds: string[]): void;
};

/**
 * The email dialog (slice 5b spec, UX "Email dialog", amended 2026-10-06;
 * slice 5b-2): From, To (the church's contacts; one whose saved address the
 * send-time rule refuses is shown but cannot be chosen), Other addresses, the
 * BCC note from two people on, the subject, the two attachments (at least
 * one), the message (prefilled, editable), notes when the service is not
 * finished or not saved, the printed bulletin's notes while its PDF is
 * ticked, and **Send to N people**. Below `md` it is a bottom sheet, as the
 * Contacts page's editor (5b-1): the whole sheet scrolls, its buttons with
 * it, so the iPhone keyboard never leaves Send out of reach; from `md` it is
 * centred, the fields scrolling above the buttons. The form lives in the
 * card, so closing and reopening keeps it. While a send runs the dialog
 * cannot be closed (abandoning the wait would not stop Gmail). Every failure
 * shows here, where it belongs, never as a toast. After a send that may
 * already have gone out (Gmail did not confirm it, or the connection was
 * lost), plain Send stays off, even after a reload, until **Send again
 * anyway** sends with a new key.
 */
export function EmailDialog({ googleEmail, form, onFormChange, tracker, uncertain, onUncertain, onClose, onSent }: Props) {
  const church = useChurch();
  const { draft, peek } = useDraft();
  const queryClient = useQueryClient();
  const contacts = useContacts();
  const send = useSendBulletinEmail();
  const start = useStartGmailConnect();
  const slow = useStillWorking(send.isPending);
  const [problem, setProblem] = useState<Problem | null>(null);
  const toRef = useRef<HTMLFieldSetElement>(null);
  const otherRef = useRef<HTMLInputElement>(null);
  const messageRef = useRef<HTMLTextAreaElement>(null);
  const attachmentsRef = useRef<HTMLFieldSetElement>(null);

  const dateIso = draft.readings.date_iso;
  const items = contacts.data?.items ?? [];
  const chosen = items.filter((c) => c.email_valid && form.contactIds.includes(c.id));
  const extras = parseAddressList(form.otherAddresses);
  const count = countRecipients(
    chosen.map((c) => c.email),
    extras,
  );
  const missing = stillNeeded(draft).length;
  const blocked =
    count === 0 ? CHOOSE_RECIPIENT : count > MAX_RECIPIENTS ? TOO_MANY : form.attachments.length === 0 ? CHOOSE_ATTACHMENT : null;

  const change = (target: FieldTarget, update: Partial<EmailForm>) => {
    onFormChange(update);
    if (problem?.[target]) setProblem((p) => (p ? { ...p, [target]: undefined } : p));
  };

  const focusFirst = (found: Problem) => {
    if (found.to) toRef.current?.querySelector("input")?.focus();
    else if (found.other) otherRef.current?.focus();
    else if (found.attachments) attachmentsRef.current?.querySelector("input")?.focus();
    else if (found.message) messageRef.current?.focus();
  };

  function failed(e: ApiError) {
    if (e.status === 401 || isNoChurchAccess(e) || e.code === "aborted") return;
    const details = e.details ?? {};
    let found: Problem;
    if (e.status === 0) {
      found = { top: CONNECTION_LOST, action: "again" };
      onUncertain(CONNECTION_LOST);
    } else if (e.status === 422 && e.fields && Object.keys(e.fields).length > 0) {
      found = {};
      for (const [key, message] of Object.entries(e.fields)) {
        const target = fieldTarget(key);
        found[target] ??= message;
      }
    } else if (e.status === 404 && details.field === "contact_ids") {
      found = { to: e.message };
      void queryClient.invalidateQueries({ queryKey: keys.contacts(church.id) });
    } else if (e.status === 404 && typeof details.field === "string" && details.field.startsWith("hymns.")) {
      found = { top: e.message, action: "hymns" };
    } else if (e.code === "gmail_not_connected") {
      found = { top: e.message, action: "connect" };
      void queryClient.invalidateQueries({ queryKey: keys.gmailConnection() });
    } else if (e.code === "gmail_send_failed" && details.disconnected === true) {
      found = { top: e.message, action: "reconnect" };
      void queryClient.invalidateQueries({ queryKey: keys.gmailConnection() });
    } else if (details.send_uncertain === true) {
      found = { top: e.message, action: "again" };
      onUncertain(e.message);
    } else if (e.code === "gmail_not_configured") {
      found = { top: e.message, sendDisabled: true };
      void queryClient.invalidateQueries({ queryKey: keys.gmailConnection() });
    } else {
      found = { top: gmailErrorMessage(e) };
    }
    setProblem(found);
    focusFirst(found);
  }

  function submit({ again = false }: { again?: boolean } = {}) {
    if (send.isPending || blocked !== null || (uncertain !== null && !again)) return;
    const body = bulletinEmailBody(peek(), { ...form, contactIds: chosen.map((c) => c.id) });
    if (again) tracker.rotate();
    const key = tracker.keyFor(body);
    setProblem(null);
    send.mutate(
      { body, key },
      {
        onSuccess: (sent) => {
          tracker.settle("success");
          onUncertain(null);
          onSent(sent.recipient_count, body.contact_ids ?? []);
        },
        onError: (e) => {
          tracker.settle(settleOutcome(e));
          if (again) onUncertain(null); // answered: an uncertain answer sets it again in `failed`
          failed(e);
        },
      },
    );
  }

  function connect() {
    start.mutate({
      returnTo: REVIEW_PATH,
      reopen: {
        church_id: church.id,
        contact_ids: form.contactIds,
        other_addresses: form.otherAddresses,
        message: form.message,
        attachments: form.attachments,
      },
    });
  }

  const toggleContact = (id: string, on: boolean) =>
    change("to", { contactIds: on ? [...form.contactIds, id] : form.contactIds.filter((c) => c !== id) });
  const toggleAttachment = (kind: AttachmentKind, on: boolean) =>
    change("attachments", {
      attachments: ATTACHMENT_KINDS.filter((k) => (k === kind ? on : form.attachments.includes(k))),
    });

  // A failure of this visit, else a send that may already have gone out (this visit or an earlier one).
  const shown: Problem | null = problem ?? (uncertain !== null ? { top: uncertain, action: "again" } : null);

  let toBody: ReactNode;
  if (contacts.data) {
    toBody =
      items.length === 0 ? (
        <div className="grid gap-1 text-sm">
          <p>{NO_CONTACTS}</p>
          {isAdmin(church.role) ? (
            <Link href="/settings/contacts" className="w-fit font-medium underline underline-offset-4">
              Manage contacts
            </Link>
          ) : null}
        </div>
      ) : (
        <ul className="grid gap-1">
          {items.map((contact) => (
            <li key={contact.id}>
              <label
                className={`flex min-h-11 items-start gap-3 rounded-md px-1 py-2 ${contact.email_valid ? "cursor-pointer" : "opacity-70"}`}
              >
                <input
                  type="checkbox"
                  className="mt-0.5 size-5 shrink-0 accent-primary"
                  checked={contact.email_valid && form.contactIds.includes(contact.id)}
                  disabled={!contact.email_valid || send.isPending}
                  onChange={(event) => toggleContact(contact.id, event.target.checked)}
                />
                <span className="grid min-w-0 gap-0.5">
                  {contact.name !== null ? <span className="break-words">{contact.name}</span> : null}
                  <span className={contact.name !== null ? "text-sm text-muted-foreground break-all" : "break-all"}>
                    {contact.email}
                  </span>
                  {contact.email_valid ? null : (
                    <span className="text-sm text-amber-700 dark:text-amber-400">{INVALID_CONTACT}</span>
                  )}
                </span>
              </label>
            </li>
          ))}
        </ul>
      );
  } else if (contacts.isError) {
    toBody = (
      <ErrorState error={contacts.error} message={CONTACTS_ERROR} onRetry={() => void contacts.refetch()} retrying={contacts.isFetching} />
    );
  } else {
    toBody = (
      <div role="status" aria-label="Loading" className="grid gap-2">
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
        <Skeleton className="h-11 w-full" />
      </div>
    );
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open && !send.isPending) onClose();
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:max-w-none! max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-b-none max-md:max-h-[85dvh] max-md:overflow-y-auto md:max-h-[calc(100dvh-2rem)] md:max-w-lg md:grid-rows-[auto_minmax(0,1fr)]"
      >
        <DialogHeader>
          <DialogTitle>Email the bulletin</DialogTitle>
        </DialogHeader>
        <form
          noValidate
          className="grid gap-4 md:min-h-0 md:grid-rows-[minmax(0,1fr)_auto]"
          onSubmit={(event: FormEvent) => {
            event.preventDefault();
            submit();
          }}
        >
          <div className="grid content-start gap-5 md:overflow-y-auto">
            <div aria-live="polite" className="empty:hidden">
              {shown?.top ? (
                <div role="alert" className="grid gap-2 rounded-md border border-destructive/40 p-3 text-sm">
                  <p>{shown.top}</p>
                  {shown.action === "hymns" ? (
                    <Link
                      href="/builder/hymns"
                      onClick={onClose}
                      className={buttonVariants({ variant: "outline", size: "touch", className: "w-full sm:w-fit" })}
                    >
                      Go to Hymns
                    </Link>
                  ) : null}
                  {shown.action === "connect" || shown.action === "reconnect" ? (
                    <PendingButton size="touch" className="w-full sm:w-fit" pending={start.isPending} pendingLabel="Opening Google…" onClick={connect}>
                      {shown.action === "connect" ? "Connect Gmail" : "Reconnect Gmail"}
                    </PendingButton>
                  ) : null}
                  {shown.action === "again" ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="touch"
                      className="w-full sm:w-fit"
                      disabled={send.isPending || blocked !== null}
                      onClick={() => submit({ again: true })}
                    >
                      Send again anyway
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
            <p className="text-sm">
              <span className="text-muted-foreground">From </span>
              <span className="break-all">{googleEmail}</span>
            </p>
            <fieldset ref={toRef} className="grid gap-2" aria-describedby={problem?.to ? "email-to-error" : undefined}>
              <legend className="mb-1 text-sm font-medium">To</legend>
              {toBody}
              {problem?.to ? (
                <p id="email-to-error" role="alert" className="text-sm text-destructive">
                  {problem.to}
                </p>
              ) : null}
            </fieldset>
            <div className="grid gap-1.5">
              <Label htmlFor="email-other">Other addresses</Label>
              <Input
                id="email-other"
                ref={otherRef}
                type="text"
                inputMode="email"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                autoComplete="off"
                placeholder="name@example.com"
                className="h-11"
                value={form.otherAddresses}
                aria-invalid={problem?.other ? true : undefined}
                aria-describedby={problem?.other ? "email-other-help email-other-error" : "email-other-help"}
                onChange={(event) => change("other", { otherAddresses: event.target.value })}
              />
              <p id="email-other-help" className="text-sm text-muted-foreground">
                Separate addresses with commas.
              </p>
              {problem?.other ? (
                <p id="email-other-error" role="alert" className="text-sm text-destructive">
                  {problem.other}
                </p>
              ) : null}
            </div>
            {count >= 2 ? <p className="text-sm text-muted-foreground">{BCC_NOTE}</p> : null}
            <p className="text-sm">
              <span className="text-muted-foreground">Subject </span>
              {bulletinEmailSubject(dateIso)}
            </p>
            <fieldset ref={attachmentsRef} className="grid gap-1">
              <legend className="mb-1 text-sm font-medium">Attachments</legend>
              {ATTACHMENT_KINDS.map((kind) => (
                <label key={kind} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-md px-1 py-2">
                  <input
                    type="checkbox"
                    className="mt-0.5 size-5 shrink-0 accent-primary"
                    checked={form.attachments.includes(kind)}
                    disabled={send.isPending}
                    onChange={(event) => toggleAttachment(kind, event.target.checked)}
                  />
                  <span className="grid min-w-0 gap-0.5">
                    <span>{ATTACHMENT_LABELS[kind]}</span>
                    <span className="text-sm text-muted-foreground break-all">
                      {kind === "docx" ? docxFilename("bulletin", dateIso) : printedFilename("pdf", dateIso)}
                    </span>
                  </span>
                </label>
              ))}
              {form.attachments.includes("pdf") ? (
                <div className="grid gap-1 px-1">
                  <NotFilledInLines />
                </div>
              ) : null}
              {problem?.attachments ? (
                <p role="alert" className="text-sm text-destructive">
                  {problem.attachments}
                </p>
              ) : null}
            </fieldset>
            <div className="grid gap-1.5">
              <Label htmlFor="email-message">Message</Label>
              <Textarea
                id="email-message"
                ref={messageRef}
                rows={4}
                maxLength={MESSAGE_MAX_LENGTH}
                value={form.message}
                aria-invalid={problem?.message ? true : undefined}
                aria-describedby={problem?.message ? "email-message-error" : undefined}
                onChange={(event) => change("message", { message: event.target.value })}
              />
              {problem?.message ? (
                <p id="email-message-error" role="alert" className="text-sm text-destructive">
                  {problem.message}
                </p>
              ) : null}
            </div>
            {missing > 0 || isDirty(draft) ? (
              <div className="grid gap-1 text-sm text-muted-foreground">
                {missing > 0 ? <p>{unfinishedNote(missing)}</p> : null}
                {isDirty(draft) ? <p>{NOT_SAVED_NOTE}</p> : null}
              </div>
            ) : null}
          </div>
          <DialogFooter className="max-md:rounded-none max-md:pb-[calc(1rem+env(safe-area-inset-bottom))]">
            {blocked !== null ? <p className="text-sm text-muted-foreground sm:mr-auto sm:self-center">{blocked}</p> : null}
            <DialogClose disabled={send.isPending} render={<Button type="button" variant="outline" size="touch" className="md:h-8" />}>
              Cancel
            </DialogClose>
            <PendingButton
              type="submit"
              size="touch"
              className="md:h-8"
              pending={send.isPending}
              pendingLabel={slow ? "Still working…" : "Sending…"}
              disabled={blocked !== null || problem?.sendDisabled === true || uncertain !== null}
            >
              {count === 0 ? "Send" : `Send to ${people(count)}`}
            </PendingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
