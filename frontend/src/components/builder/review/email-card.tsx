"use client";

import { MailIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ErrorState } from "@/components/app/error-state";
import { PendingButton } from "@/components/app/pending-button";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { shouldCarry } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { hasReadingsError, hasServiceDate } from "@/lib/draft/status";
import {
  clearUncertainSend,
  defaultBulletinMessage,
  parseReopen,
  readEmailPrefs,
  readUncertainSend,
  writeEmailPrefs,
  writeUncertainSend,
  type EmailForm,
} from "@/lib/email";
import { REOPEN_EMAIL_KEY } from "@/lib/gmail";
import { createKeyTracker } from "@/lib/idempotency";
import { useMeContext } from "@/lib/me-context";
import { useGmailConnection, useStartGmailConnect } from "@/lib/queries/gmail";
import { usePreviousBulletin } from "@/lib/queries/services";
import { readSession, removeSession } from "@/lib/storage";

import { EmailDialog, people } from "./email-dialog";

export const EMAIL_SUMMARY = "Send the bulletin and a short message from your own Gmail.";
export const EMAIL_STATUS_ERROR = "Couldn't check your Gmail connection.";
export const EMAIL_NOT_CONFIGURED = "Emailing isn't set up on this deployment.";
export const EMAIL_CONNECT = "Connect your Gmail to email the bulletin from your own account.";
export const EMAIL_NEEDS_DATE = "Choose a service date on step 1 to email the bulletin.";
export const EMAIL_FIX_READINGS = "Fix the readings on step 1 to email the bulletin.";
const REVIEW_PATH = "/builder/review";

/**
 * The "Email the bulletin" card on Review (slice 5b spec, UX "Review step:
 * Email the bulletin card"; slice 5b-2), after the printed bulletin. It shows
 * the caller's Gmail connection: loading, a failed check (Retry), not set up
 * here, not connected (**Connect Gmail**, which comes back here), or
 * connected ("Sends from …" and **Email bulletin…**, which needs a service
 * date and readings without errors, as the downloads do; nothing else blocks
 * it). It keeps the dialog's form (closing and reopening keeps it, a sent
 * email resets the message), its Idempotency-Key tracker and a send that may
 * already have gone out (sessionStorage, so a reload keeps plain Send off).
 * After a connect from Review it reopens the dialog with what was in it, once
 * the status says connected, only in the church it was opened in, and only
 * after last week's bulletin has been carried in (the printed card's
 * `useBulletinCarry`), so a PDF sent at once has it.
 */
export function EmailCard() {
  const church = useChurch();
  const { user } = useMeContext();
  const { draft } = useDraft();
  const status = useGmailConnection();
  const start = useStartGmailConnect();
  const [tracker] = useState(() => createKeyTracker());
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<EmailForm | null>(null);
  const [uncertain, setUncertain] = useState(() => readUncertainSend(user.id, church.id));
  // Read only, never fetched here: the printed card's useBulletinCarry fetches and applies it.
  const carry = usePreviousBulletin(draft.readings.date_iso, false);
  const dateIso = draft.readings.date_iso;
  const dated = hasServiceDate(draft);
  const readingsError = hasReadingsError(draft);

  const freshForm = (): EmailForm => {
    const prefs = readEmailPrefs(user.id, church.id);
    return { contactIds: prefs.contact_ids, otherAddresses: "", message: defaultBulletinMessage(dateIso), attachments: prefs.attachments };
  };

  // Back from Google (flow B): the request is read once, when the card mounts, and decided once the
  // status has settled and, when it reopens the dialog, once last week's bulletin is carried in or its
  // lookup failed (during render, so no effect sets state); then it is forgotten either way.
  const [reopenRaw, setReopenRaw] = useState(() => readSession(REOPEN_EMAIL_KEY));
  const settled = !status.isPending;
  const reopen = reopenRaw !== null && settled ? parseReopen(reopenRaw, church.id) : null;
  const carrying = reopen !== null && status.data?.connected === true && shouldCarry(draft) && !carry.isError;
  if (reopenRaw !== null && settled && !carrying) {
    setReopenRaw(null);
    if (reopen !== null && status.data?.connected === true) {
      const prefs = readEmailPrefs(user.id, church.id);
      setForm({
        contactIds: reopen.contact_ids ?? prefs.contact_ids,
        otherAddresses: reopen.other_addresses ?? "",
        message: reopen.message ?? defaultBulletinMessage(dateIso),
        attachments: reopen.attachments && reopen.attachments.length > 0 ? reopen.attachments : prefs.attachments,
      });
      setOpen(true);
    }
  }
  useEffect(() => {
    if (settled && !carrying) removeSession(REOPEN_EMAIL_KEY);
  }, [settled, carrying]);

  let body;
  if (status.data) {
    const { configured, google_email } = status.data;
    if (!configured) {
      body = <p className="text-sm">{EMAIL_NOT_CONFIGURED}</p>;
    } else if (!status.data.connected || google_email === null) {
      body = (
        <>
          <p className="text-sm">{EMAIL_CONNECT}</p>
          <PendingButton
            size="touch"
            className="w-full sm:w-fit"
            pending={start.isPending}
            pendingLabel="Opening Google…"
            onClick={() => start.mutate({ returnTo: REVIEW_PATH, reopen: { church_id: church.id } })}
          >
            Connect Gmail
          </PendingButton>
        </>
      );
    } else {
      const disabled = !dated || readingsError;
      body = (
        <>
          <p className="text-sm break-all">Sends from {google_email}.</p>
          {!dated ? <p className="text-sm text-muted-foreground">{EMAIL_NEEDS_DATE}</p> : null}
          {dated && readingsError ? <p className="text-sm text-muted-foreground">{EMAIL_FIX_READINGS}</p> : null}
          <Button
            size="touch"
            className="w-full sm:w-fit"
            disabled={disabled}
            onClick={() => {
              setForm((current) => current ?? freshForm());
              setOpen(true);
            }}
          >
            <MailIcon data-icon="inline-start" aria-hidden="true" />
            Email bulletin…
          </Button>
          {open && form !== null ? (
            <EmailDialog
              googleEmail={google_email}
              form={form}
              onFormChange={(change) => {
                setForm((current) => (current ? { ...current, ...change } : current));
                if (change.attachments) writeEmailPrefs(user.id, church.id, { attachments: change.attachments });
              }}
              tracker={tracker}
              uncertain={uncertain}
              onUncertain={(message) => {
                setUncertain(message);
                if (message === null) clearUncertainSend(user.id, church.id);
                else writeUncertainSend(user.id, church.id, message);
              }}
              onClose={() => setOpen(false)}
              onSent={(count, contactIds) => {
                writeEmailPrefs(user.id, church.id, { contact_ids: contactIds });
                setForm((current) =>
                  current ? { ...current, otherAddresses: "", message: defaultBulletinMessage(dateIso) } : current,
                );
                setOpen(false);
                toast.success(`Email sent to ${people(count)}.`);
              }}
            />
          ) : null}
        </>
      );
    }
  } else if (status.isError) {
    body = (
      <ErrorState error={status.error} message={EMAIL_STATUS_ERROR} onRetry={() => void status.refetch()} retrying={status.isFetching} />
    );
  } else {
    body = (
      <>
        <Skeleton className="h-4 w-2/3" />
        <Button size="touch" className="w-full sm:w-fit" disabled>
          <MailIcon data-icon="inline-start" aria-hidden="true" />
          Email bulletin…
        </Button>
      </>
    );
  }

  return (
    <section aria-labelledby="email-title" className="grid gap-4 rounded-lg border p-4">
      <div className="grid gap-1">
        <h2 id="email-title" className="text-base font-medium">
          Email the bulletin
        </h2>
        <p className="text-sm text-muted-foreground">{EMAIL_SUMMARY}</p>
      </div>
      {body}
    </section>
  );
}
