/**
 * Emailing the bulletin (slice 5b spec, "Pure modules" `lib/email.ts`, amended
 * 2026-10-06; slice 5b-2). Pure, apart from the remembered choices in
 * localStorage (`readEmailPrefs`, `writeEmailPrefs`).
 *
 * - The subject and the default message, as the server writes them
 *   (`bulletin_email.py`; shared/bulletin_email.json keeps the two equal).
 * - `parseAddressList`: "Other addresses" as addresses (commas, semicolons or
 *   new lines, not inside a quoted name; the part inside <…> when a name
 *   comes with it).
 * - `countRecipients`: how many people the email goes to (an address chosen
 *   twice, in any capitals, counts once, as the server sends it once).
 * - `fieldTarget`: where a 422's field message goes in the dialog.
 * - The remembered choices (per user and church, on this device): the
 *   contacts of the last successful send and the attachments last chosen.
 * - `bulletinEmailBody`: the `POST /bulletin-emails` body.
 * - The uncertain send (`readUncertainSend`, `writeUncertainSend`,
 *   `clearUncertainSend`): a send that may already have gone out, kept in
 *   sessionStorage per user and church with its service date, so neither
 *   leaving Review nor a reload quietly allows a plain Send again for that
 *   service; only **Send again anyway** does.
 * - `ReopenEmail`: what the dialog keeps while the user is away at Google.
 */
import type { components } from "@/lib/api/schema";
import { formatServiceDate, formatShortDate, isSunday, isValidDateIso, weekday } from "@/lib/dates";
import { serviceBody } from "@/lib/documents";
import type { DraftV1 } from "@/lib/draft/schema";
import { readLocal, readSession, removeSession, writeLocal, writeSession } from "@/lib/storage";

export type BulletinEmailBody = components["schemas"]["BulletinEmailIn"];
export type AttachmentKind = BulletinEmailBody["attachments"][number];

export const MAX_RECIPIENTS = 50;
export const MESSAGE_MAX_LENGTH = 5000;
export const ATTACHMENT_KINDS: readonly AttachmentKind[] = ["docx", "pdf"];
export const ATTACHMENT_LABELS: Record<AttachmentKind, string> = {
  docx: "Bulletin copy (Word)",
  pdf: "Printed bulletin (PDF)",
};
export const DEFAULT_ATTACHMENTS: AttachmentKind[] = ["docx"];
export const SUNDAY_MESSAGE = "Hi! Here's the worship bulletin for this Sunday.";

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
/** The server's `PrintedDocumentIn.translation` and `BulletinEmailIn.translation` limit. */
const MAX_TRANSLATION = 20;

/** "2026-10-04" → "Worship service for October 4, 2026" (`bulletin_email.bulletin_email_subject`). */
export function bulletinEmailSubject(dateIso: string): string {
  return `Worship service for ${formatServiceDate(dateIso)}`;
}

/** The message the dialog starts with (`bulletin_email.default_bulletin_message`). */
export function defaultBulletinMessage(dateIso: string): string {
  if (!isValidDateIso(dateIso) || isSunday(dateIso)) return SUNDAY_MESSAGE;
  return `Hi! Here's the worship bulletin for ${WEEKDAYS[weekday(dateIso)]}, ${formatShortDate(dateIso)}.`;
}

/** `text` split on commas, semicolons and new lines outside double quotes (all of them when a quote is left open). */
function splitAddresses(text: string): string[] {
  const parts: string[] = [];
  let current = "";
  let quoted = false;
  for (const ch of text) {
    if (ch === '"') quoted = !quoted;
    if (!quoted && (ch === "," || ch === ";" || ch === "\n")) {
      parts.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  if (quoted) return text.split(/[,;\n]/);
  parts.push(current);
  return parts;
}

/**
 * "Other addresses" as a list: split on commas, semicolons and new lines (not inside a quoted name,
 * so `"Jones, Pat" <pat@example.org>` is one), trimmed, `Name <a@b.org>` read as `a@b.org`.
 */
export function parseAddressList(text: string): string[] {
  return splitAddresses(text)
    .map((part) => {
      const inside = /<([^<>]*)>/.exec(part);
      return (inside ? inside[1] : part).trim();
    })
    .filter((address) => address !== "");
}

/** How many people get the email: every address once, ignoring capitals and spaces around it. */
export function countRecipients(contactEmails: readonly string[], extras: readonly string[]): number {
  return new Set([...contactEmails, ...extras].map((address) => address.trim().toLowerCase())).size;
}

/** Where a 422's field message shows in the dialog (5b spec, "Send outcomes"). */
export type FieldTarget = "to" | "other" | "message" | "attachments" | "top";

export function fieldTarget(key: string): FieldTarget {
  const head = key.split(".")[0];
  if (head === "additional_emails") return "other";
  if (head === "message") return "message";
  if (head === "attachments") return "attachments";
  if (head === "recipients" || head === "contact_ids") return "to";
  return "top";
}

/** What the dialog remembers for this user in this church, on this device. */
export type EmailPrefs = { version: 1; contact_ids: string[]; attachments: AttachmentKind[] };

export function emailPrefsKey(userId: string, churchId: string): string {
  return `wsb:emailPrefs:${userId}:${churchId}`;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function attachmentList(value: unknown): AttachmentKind[] {
  const chosen = stringList(value);
  return ATTACHMENT_KINDS.filter((kind) => chosen.includes(kind));
}

/** The remembered choices; none (or unreadable): no contacts, the bulletin copy. */
export function readEmailPrefs(userId: string, churchId: string): EmailPrefs {
  const fallback: EmailPrefs = { version: 1, contact_ids: [], attachments: DEFAULT_ATTACHMENTS };
  const raw = readLocal(emailPrefsKey(userId, churchId));
  if (raw === null) return fallback;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed?.version !== 1) return fallback;
    const attachments = attachmentList(parsed.attachments);
    return {
      version: 1,
      contact_ids: stringList(parsed.contact_ids),
      attachments: attachments.length > 0 ? attachments : DEFAULT_ATTACHMENTS,
    };
  } catch {
    return fallback;
  }
}

/** Remember `changes` (the last send's contacts, or the attachments just chosen) on top of what is kept. */
export function writeEmailPrefs(userId: string, churchId: string, changes: Partial<Omit<EmailPrefs, "version">>): void {
  const next = { ...readEmailPrefs(userId, churchId), ...changes, version: 1 };
  writeLocal(emailPrefsKey(userId, churchId), JSON.stringify(next));
}

/** Where this tab keeps a send that may already have gone out, for this user in this church. */
export function uncertainSendKey(userId: string, churchId: string): string {
  return `wsb:emailUncertain:${userId}:${churchId}`;
}

/** What is kept: the message to show and the service date of the email that may have gone out. */
type UncertainSend = { version: 2; message: string; date_iso: string };

/**
 * The message of a send that may already have gone out for the service on `dateIso`, or null
 * (none, unreadable, or another service's: last week's email does not hold this week's back).
 */
export function readUncertainSend(userId: string, churchId: string, dateIso: string): string | null {
  const raw = readSession(uncertainSendKey(userId, churchId));
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    return parsed?.version === 2 &&
      typeof parsed.message === "string" &&
      parsed.message !== "" &&
      parsed.date_iso === dateIso
      ? parsed.message
      : null;
  } catch {
    return null;
  }
}

export function writeUncertainSend(userId: string, churchId: string, message: string, dateIso: string): void {
  const stored: UncertainSend = { version: 2, message, date_iso: dateIso };
  writeSession(uncertainSendKey(userId, churchId), JSON.stringify(stored));
}

export function clearUncertainSend(userId: string, churchId: string): void {
  removeSession(uncertainSendKey(userId, churchId));
}

/** The dialog's form. */
export type EmailForm = { contactIds: string[]; otherAddresses: string; message: string; attachments: AttachmentKind[] };

/** `POST /bulletin-emails`: the service as the downloads send it, the choices, and the draft's translation for the PDF. */
export function bulletinEmailBody(draft: DraftV1, form: EmailForm): BulletinEmailBody {
  const translation = draft.readings.translation;
  return {
    service: serviceBody(draft),
    contact_ids: [...form.contactIds],
    additional_emails: parseAddressList(form.otherAddresses),
    message: form.message,
    attachments: ATTACHMENT_KINDS.filter((kind) => form.attachments.includes(kind)),
    translation: translation && translation.length <= MAX_TRANSLATION ? translation : null,
  };
}

/** What the dialog keeps in `wsb:reopenEmailDialog` while the user connects Gmail at Google. */
export type ReopenEmail = { church_id: string } & Partial<{
  contact_ids: string[];
  other_addresses: string;
  message: string;
  attachments: AttachmentKind[];
}>;

/** The stored reopen request for this church, or null (none, unreadable, or another church's). */
export function parseReopen(raw: string | null, churchId: string): ReopenEmail | null {
  if (raw === null) return null;
  try {
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed?.church_id !== churchId) return null;
    const reopen: ReopenEmail = { church_id: churchId };
    if (Array.isArray(parsed.contact_ids)) reopen.contact_ids = stringList(parsed.contact_ids);
    if (typeof parsed.other_addresses === "string") reopen.other_addresses = parsed.other_addresses;
    if (typeof parsed.message === "string") reopen.message = parsed.message;
    if (Array.isArray(parsed.attachments)) reopen.attachments = attachmentList(parsed.attachments);
    return reopen;
  } catch {
    return null;
  }
}
