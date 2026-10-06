/**
 * The Contacts page's forms (slice 5b-1; 6a spec "Contacts"). The server
 * checks and cleans every address (the one rule 5b-2 sends with); the page
 * trims what it sends, as the server would, so an edit that only adds spaces
 * sends nothing.
 */
import type { Contact, ContactBody, ContactPatch } from "@/lib/api/types";

export type ContactForm = { name: string; email: string };

export const EMPTY_CONTACT: ContactForm = { name: "", email: "" };

/** How a contact is named on the page: its name, or its address when it has none. */
export function contactLabel(contact: Pick<Contact, "name" | "email">): string {
  return contact.name ?? contact.email;
}

/** The edit form a contact starts at, and its baseline. */
export function contactFormFrom(contact: Contact): ContactForm {
  return { name: contact.name ?? "", email: contact.email };
}

/** `POST /contacts`'s body: both fields trimmed; no name is null. */
export function newContactBody(form: ContactForm): ContactBody {
  const name = form.name.trim();
  return { name: name === "" ? null : name, email: form.email.trim() };
}

/** `PATCH /contacts/{id}`'s body: each field whose trimmed value differs from the baseline's; a cleared name is null. */
export function contactPatch(baseline: ContactForm, form: ContactForm): ContactPatch {
  const patch: ContactPatch = {};
  const name = form.name.trim();
  if (name !== baseline.name.trim()) patch.name = name === "" ? null : name;
  const email = form.email.trim();
  if (email !== baseline.email.trim()) patch.email = email;
  return patch;
}

/** True while the add form holds something a reload would lose. */
export function hasTyped(form: ContactForm): boolean {
  return form.name.trim() !== "" || form.email.trim() !== "";
}
