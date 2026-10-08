/**
 * Settings → Prayers' form rules (slice 6a-3b; 6a spec "Pure helpers"
 * `prayers.ts`; prayer library spec "Prayers page (slice 6a)"). The form holds
 * the prayer rows (each with a client key: a saved prayer's id, or a made-up
 * key for a new one) and the voice profile. Texts are compared, checked and
 * sent close to the way the server stores them (`clean_text`: CRLF as LF,
 * trimmed; see `cleanText` for the few characters the two trims differ on) and
 * counted the way Python counts them (characters, not UTF-16 units), so the
 * page's checks and the server's agree for any ordinary text.
 */
import { ApiError } from "@/lib/api/client";
import type { PrayerLibrary, PrayerLibraryBody, PrayerType } from "@/lib/api/types";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

/** The types, in the server's order (`prayer_library.PRAYER_TYPES`): the eight sections, then Other. */
export const PRAYER_TYPES: readonly PrayerType[] = [
  "call_to_worship",
  "opening_prayer",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "prayers_of_the_people",
  "offertory_prayer",
  "benediction",
  "other",
];
export const PRAYER_TYPE_LABELS: Readonly<Record<PrayerType, string>> = { ...SECTION_LABELS, other: "Other" };

/** The server's limits (`prayer_library.MAX_PRAYERS`, `MAX_PRAYER_CHARS`, `MAX_PROFILE_CHARS`). */
export const MAX_PRAYERS = 30;
export const MAX_PRAYER_CHARS = 6_000;
export const MAX_PROFILE_CHARS = 2_000;

/** The server's messages (`usecases.prayer_library`), so the page and the server use one wording. */
export const TEXT_REQUIRED = "Prayer text is required.";
export const TEXT_TOO_LONG = "This prayer is too long (6,000 characters at most).";
export const TYPE_REQUIRED = "Choose a prayer type.";
export const TOO_MANY = "You can keep up to 30 prayers.";
export const PROFILE_TOO_LONG = "The voice profile is too long (2,000 characters at most).";

/** One row of the form. `type` is "" until one is chosen; `id` is null for a prayer not saved yet. */
export type PrayerRow = { key: string; id: string | null; type: PrayerType | ""; text: string };
export type LibraryForm = { rows: PrayerRow[]; profile: string };
export type RowErrors = { type?: string; text?: string };
export type LibraryErrors = { rows: Record<string, RowErrors>; profile?: string };

/**
 * A text as the server stores it, near enough: CRLF line ends as LF, trimmed. Close to `clean_text`, not
 * identical: JavaScript's trim also drops U+FEFF, and Python's strip also drops U+001C to U+001F and U+0085.
 * Those are rare in a pasted prayer; the server cleans again, and the form then shows what it stored.
 */
export function cleanText(text: string): string {
  return text.replace(/\r\n/g, "\n").trim();
}

/** Characters as Python counts them (code points), for the limits. */
export function charCount(text: string): number {
  return Array.from(text).length;
}

/** The first line with any text in it, trimmed (a row's summary). */
export function firstLine(text: string): string {
  return (
    text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .find((line) => line !== "") ?? ""
  );
}

/** A new, empty row. */
export function newRow(key: string): PrayerRow {
  return { key, id: null, type: "", text: "" };
}

/**
 * The form a read starts at, and its baseline. A row's key is its prayer's id, or `saved-<i>` when the
 * id is empty (slice 4's reader reads a stored non-string id as ""), so no two rows share a key.
 */
export function libraryFormFrom(out: PrayerLibrary): LibraryForm {
  return {
    rows: out.prayers.map((p, i) => ({ key: p.id || `saved-${i}`, id: p.id, type: p.type, text: p.text })),
    profile: out.voice_profile,
  };
}

/** `PUT`'s body: every row in order, cleaned, a saved one with its id; and the profile, cleaned. */
export function prayersPayload(form: LibraryForm): PrayerLibraryBody {
  return {
    prayers: form.rows.map((row) => ({ ...(row.id ? { id: row.id } : {}), type: row.type, text: cleanText(row.text) })),
    voice_profile: cleanText(form.profile),
  };
}

/** True when a save would store a different list of prayers. */
export function listChanged(a: readonly PrayerRow[], b: readonly PrayerRow[]): boolean {
  const sent = (rows: readonly PrayerRow[]) => JSON.stringify(prayersPayload({ rows: [...rows], profile: "" }).prayers);
  return sent(a) !== sent(b);
}

/** True when a save would change what is stored. */
export function hasLibraryChanges(baseline: LibraryForm, current: LibraryForm): boolean {
  return listChanged(baseline.rows, current.rows) || cleanText(baseline.profile) !== cleanText(current.profile);
}

/** The page's own checks before a save, with the server's words (the count is held at 30 by Add a prayer). */
export function libraryErrors(form: LibraryForm): LibraryErrors {
  const errors: LibraryErrors = { rows: {} };
  for (const row of form.rows) {
    const found: RowErrors = {};
    if (row.type === "") found.type = TYPE_REQUIRED;
    const text = cleanText(row.text);
    if (text === "") found.text = TEXT_REQUIRED;
    else if (charCount(text) > MAX_PRAYER_CHARS) found.text = TEXT_TOO_LONG;
    if (found.type || found.text) errors.rows[row.key] = found;
  }
  if (charCount(cleanText(form.profile)) > MAX_PROFILE_CHARS) errors.profile = PROFILE_TOO_LONG;
  return errors;
}

export function hasErrors(errors: LibraryErrors): boolean {
  return Boolean(errors.profile) || Object.keys(errors.rows).length > 0;
}

const ROW_FIELD = /^prayers\.(\d+)\.(type|text)$/;

/** True when a refusal names a row's type or text, or the profile: the form shows it, not a toast. */
export function namesLibraryField(e: unknown): boolean {
  if (!(e instanceof ApiError) || e.status !== 422) return false;
  return Object.keys(e.fields ?? {}).some((field) => ROW_FIELD.test(field) || field === "voice_profile");
}

/**
 * A failed save's messages for the form: each 422 field "prayers.<i>.type" or
 * "prayers.<i>.text" on the row that was sent i-th (`sentKeys`), and
 * "voice_profile" on the profile; null when the refusal names none of them
 * (the count, or anything else), for a toast.
 */
export function libraryFieldErrors(e: unknown, sentKeys: readonly string[]): LibraryErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const errors: LibraryErrors = { rows: {} };
  for (const [field, message] of Object.entries(e.fields)) {
    const match = ROW_FIELD.exec(field);
    const key = match ? sentKeys[Number(match[1])] : undefined;
    if (match && key !== undefined) errors.rows[key] = { ...errors.rows[key], [match[2]]: message };
    else if (field === "voice_profile") errors.profile = message;
  }
  return hasErrors(errors) ? errors : null;
}

/** The newer rows, each saved prayer keeping the key `current` gives it, so an open row stays open. */
function keepKeys(next: readonly PrayerRow[], current: readonly PrayerRow[]): PrayerRow[] {
  const keyOf = new Map(current.filter((row) => row.id).map((row) => [row.id, row.key]));
  return next.map((row) => ({ ...row, key: (row.id && keyOf.get(row.id)) || row.key }));
}

/**
 * 6a's rebase, with the prayer list and the profile as its two parts: newer
 * server data replaces a part the user has not changed (compared as the
 * server compares it) and an edited part keeps the edit.
 */
export function rebaseLibrary(oldBaseline: LibraryForm, current: LibraryForm, next: LibraryForm): LibraryForm {
  return {
    rows: listChanged(oldBaseline.rows, current.rows) ? current.rows : keepKeys(next.rows, current.rows),
    profile: cleanText(oldBaseline.profile) !== cleanText(current.profile) ? current.profile : next.profile,
  };
}

/**
 * After a save: the new baseline is what was stored, each row keeping the key
 * it was sent with (a new prayer now has its id, and stays open); the form is
 * the rebase of what was typed while the save ran onto it.
 */
export function afterSave(sent: LibraryForm, current: LibraryForm, saved: PrayerLibrary): { baseline: LibraryForm; form: LibraryForm } {
  const stored = libraryFormFrom(saved);
  const baseline = { ...stored, rows: stored.rows.map((row, i) => ({ ...row, key: sent.rows[i]?.key ?? row.key })) };
  return { baseline, form: rebaseLibrary(sent, current, baseline) };
}
