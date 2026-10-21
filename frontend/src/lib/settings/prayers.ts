/**
 * Settings → Prayers' form rules (slice 6a-3b; 6a spec "Pure helpers"
 * `prayers.ts`; prayer library spec "Prayers page (slice 6a)"). The form holds
 * the prayer rows (each with a client key: a saved prayer's id, or a made-up
 * key for a new one) and the voice profile. Texts are compared, checked and
 * sent close to the way the server stores them (`clean_text`: CRLF as LF,
 * trimmed; see `cleanText` for the few characters the two trims differ on) and
 * counted the way Python counts them (characters, not UTF-16 units), so the
 * page's checks and the server's agree for any ordinary text.
 *
 * The form also holds the pew voices (pew voices spec 2026-10-20, "Settings
 * → Prayers"), saved by the same Save: a description and an "on" switch per
 * row, each row keyed `voice-<i>` or a made-up key. `PUT` sends `pew_voices`
 * only when they changed from the baseline, so a save of prayers alone never
 * overwrites another admin's newer voices.
 */
import { ApiError } from "@/lib/api/client";
import type { PewVoice, PrayerLibrary, PrayerLibraryBody, PrayerType } from "@/lib/api/types";
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

/** The pew voices' limits and messages (`pew_voices.MAX_*`, `usecases.prayer_library`). */
export const MAX_VOICES = 12;
export const MAX_VOICES_ON = 6;
export const MAX_DESCRIPTION_CHARS = 300;
export const TOO_MANY_VOICES = "You can keep up to 12 voices.";
export const DESCRIPTION_REQUIRED = "Describe this voice.";
export const DESCRIPTION_TOO_LONG = "This description is too long (300 characters at most).";
export const TOO_MANY_ON = "Turn on at most 6 voices.";
/**
 * The owner's five (`pew_voices.DEFAULT_DESCRIPTIONS`), all on: what a church that never saved its voices reads,
 * and what "Restore the starter voices" puts back in the form. A church that saved its own list keeps it.
 */
export const STARTER_VOICES: readonly PewVoice[] = [
  { description: "Sharp, very conservative, reads every word", on: true },
  { description: "A teenager", on: true },
  { description: "A man who rarely comes to church", on: true },
  { description: "Parents of busy young kids", on: true },
  { description: "Someone deeply worried about their health", on: true },
];

/** One row of the form. `type` is "" until one is chosen; `id` is null for a prayer not saved yet. */
export type PrayerRow = { key: string; id: string | null; type: PrayerType | ""; text: string };
export type VoiceRow = { key: string; description: string; on: boolean };
export type LibraryForm = { rows: PrayerRow[]; profile: string; voices: VoiceRow[] };
export type RowErrors = { type?: string; text?: string };
/** `voices`: a description's message by row key; `voicesList`: the count of voices turned on. */
export type LibraryErrors = { rows: Record<string, RowErrors>; profile?: string; voices?: Record<string, string>; voicesList?: string };

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

/** A description as the server stores it: every run of whitespace as one space, trimmed. */
export function cleanDescription(text: string): string {
  return text.split(/\s+/).filter((part) => part !== "").join(" ");
}

/** The starter voices as form rows, keyed `<prefix>-<i>` (the form's other keys stay apart). */
export function starterVoiceRows(prefix: string): VoiceRow[] {
  return STARTER_VOICES.map((v, i) => ({ key: `${prefix}-${i}`, description: v.description, on: v.on }));
}

/** A new, empty, turned-on voice. */
export function newVoice(key: string): VoiceRow {
  return { key, description: "", on: true };
}

/** A new, empty row. */
export function newRow(key: string): PrayerRow {
  return { key, id: null, type: "", text: "" };
}

/**
 * The form a read starts at, and its baseline. A row's key is its prayer's id, or `saved-<i>` when the
 * id is empty (slice 4's reader reads a stored non-string id as "") or repeats an earlier row's (the
 * server gives that row a fresh id on the next save), so no two rows share a key.
 */
export function libraryFormFrom(out: PrayerLibrary): LibraryForm {
  const seen = new Set<string>();
  const rows = out.prayers.map((p, i) => {
    const key = p.id && !seen.has(p.id) ? p.id : `saved-${i}`;
    seen.add(p.id);
    return { key, id: p.id, type: p.type, text: p.text };
  });
  // A server deployed before the voices answers without them: the starter voices, unchanged, so never sent.
  const saved: readonly PewVoice[] = (out.pew_voices as PewVoice[] | undefined) ?? STARTER_VOICES;
  const voices = saved.map((v, i) => ({ key: `voice-${i}`, description: v.description, on: v.on }));
  return { rows, profile: out.voice_profile, voices };
}

function voicesSent(voices: readonly VoiceRow[]): PewVoice[] {
  return voices.map((v) => ({ description: cleanDescription(v.description), on: v.on }));
}

/** True when a save would store different voices. */
export function voicesChanged(a: readonly VoiceRow[], b: readonly VoiceRow[]): boolean {
  return JSON.stringify(voicesSent(a)) !== JSON.stringify(voicesSent(b));
}

/**
 * `PUT`'s body: every row in order, cleaned, a saved one with its id; the profile, cleaned; and, when they
 * changed from `baseline`, the voices, cleaned (left out, the server keeps the stored ones).
 */
export function prayersPayload(form: LibraryForm, baseline?: LibraryForm): PrayerLibraryBody {
  const body: PrayerLibraryBody = {
    prayers: form.rows.map((row) => ({ ...(row.id ? { id: row.id } : {}), type: row.type, text: cleanText(row.text) })),
    voice_profile: cleanText(form.profile),
  };
  if (baseline !== undefined && voicesChanged(baseline.voices, form.voices)) body.pew_voices = voicesSent(form.voices);
  return body;
}

/** True when a save would store a different list of prayers. */
export function listChanged(a: readonly PrayerRow[], b: readonly PrayerRow[]): boolean {
  const sent = (rows: readonly PrayerRow[]) => JSON.stringify(prayersPayload({ rows: [...rows], profile: "", voices: [] }).prayers);
  return sent(a) !== sent(b);
}

/** True when a save would change what is stored. */
export function hasLibraryChanges(baseline: LibraryForm, current: LibraryForm): boolean {
  return (
    listChanged(baseline.rows, current.rows) ||
    cleanText(baseline.profile) !== cleanText(current.profile) ||
    voicesChanged(baseline.voices, current.voices)
  );
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
  for (const voice of form.voices) {
    const description = cleanDescription(voice.description);
    const found = description === "" ? DESCRIPTION_REQUIRED : charCount(description) > MAX_DESCRIPTION_CHARS ? DESCRIPTION_TOO_LONG : null;
    if (found !== null) errors.voices = { ...errors.voices, [voice.key]: found };
  }
  if (form.voices.filter((v) => v.on).length > MAX_VOICES_ON) errors.voicesList = TOO_MANY_ON;
  return errors;
}

export function hasErrors(errors: LibraryErrors): boolean {
  return (
    Boolean(errors.profile) ||
    Object.keys(errors.rows).length > 0 ||
    Object.keys(errors.voices ?? {}).length > 0 ||
    Boolean(errors.voicesList)
  );
}

const ROW_FIELD = /^prayers\.(\d+)\.(type|text)$/;
const VOICE_FIELD = /^pew_voices\.(\d+)\.description$/;

/** True when a refusal names a row's type or text, the profile, or a voice: the form shows it, not a toast. */
export function namesLibraryField(e: unknown): boolean {
  if (!(e instanceof ApiError) || e.status !== 422) return false;
  return Object.keys(e.fields ?? {}).some(
    (field) => ROW_FIELD.test(field) || field === "voice_profile" || VOICE_FIELD.test(field) || field === "pew_voices",
  );
}

/**
 * A failed save's messages for the form: each 422 field "prayers.<i>.type" or
 * "prayers.<i>.text" on the row that was sent i-th (`sentKeys`), and
 * "voice_profile" on the profile; "pew_voices.<i>.description" on the voice
 * sent i-th (`sentVoiceKeys`) and "pew_voices" on the voices' list; null when
 * the refusal names none of them (the count, or anything else), for a toast.
 */
export function libraryFieldErrors(
  e: unknown,
  sentKeys: readonly string[],
  sentVoiceKeys: readonly string[] = [],
): LibraryErrors | null {
  if (!(e instanceof ApiError) || e.status !== 422 || !e.fields) return null;
  const errors: LibraryErrors = { rows: {} };
  for (const [field, message] of Object.entries(e.fields)) {
    const match = ROW_FIELD.exec(field);
    const key = match ? sentKeys[Number(match[1])] : undefined;
    const voice = VOICE_FIELD.exec(field);
    const voiceKey = voice ? sentVoiceKeys[Number(voice[1])] : undefined;
    if (match && key !== undefined) errors.rows[key] = { ...errors.rows[key], [match[2]]: message };
    else if (field === "voice_profile") errors.profile = message;
    else if (voice && voiceKey !== undefined) errors.voices = { ...errors.voices, [voiceKey]: message };
    else if (field === "pew_voices") errors.voicesList = message;
  }
  return hasErrors(errors) ? errors : null;
}

/** The ids that appear on exactly one of these rows. */
function uniqueIds(rows: readonly PrayerRow[]): Set<string> {
  const counts = new Map<string, number>();
  for (const row of rows) if (row.id) counts.set(row.id, (counts.get(row.id) ?? 0) + 1);
  return new Set([...counts].filter(([, n]) => n === 1).map(([id]) => id));
}

/**
 * The newer rows, each saved prayer keeping the key `current` gives it, so an open row stays open. Only
 * an id found once on each side is matched (a repeated id names no one row); a row whose own key is
 * already taken by a matched one gets `<key>-<i>`, so no two rows share a key.
 */
function keepKeys(next: readonly PrayerRow[], current: readonly PrayerRow[]): PrayerRow[] {
  const once = uniqueIds(next);
  const onceNow = uniqueIds(current);
  const keyOf = new Map(current.filter((row) => row.id && onceNow.has(row.id)).map((row) => [row.id, row.key]));
  const matched = next.map((row) => (row.id && once.has(row.id) ? keyOf.get(row.id) : undefined));
  const taken = new Set(matched.filter((key) => key !== undefined));
  return next.map((row, i) => ({ ...row, key: matched[i] ?? (taken.has(row.key) ? `${row.key}-${i}` : row.key) }));
}

/**
 * 6a's rebase, with the prayer list, the profile and the voices as its three
 * parts: newer server data replaces a part the user has not changed
 * (compared as the server compares it) and an edited part keeps the edit.
 */
export function rebaseLibrary(oldBaseline: LibraryForm, current: LibraryForm, next: LibraryForm): LibraryForm {
  return {
    rows: listChanged(oldBaseline.rows, current.rows) ? current.rows : keepKeys(next.rows, current.rows),
    profile: cleanText(oldBaseline.profile) !== cleanText(current.profile) ? current.profile : next.profile,
    voices: voicesChanged(oldBaseline.voices, current.voices) ? current.voices : next.voices,
  };
}

/**
 * After a save: the new baseline is what was stored, each row keeping the key
 * it was sent with (a new prayer now has its id, and stays open); the form is
 * the rebase of what was typed while the save ran onto it.
 */
export function afterSave(sent: LibraryForm, current: LibraryForm, saved: PrayerLibrary): { baseline: LibraryForm; form: LibraryForm } {
  const stored = libraryFormFrom(saved);
  const baseline = {
    ...stored,
    rows: stored.rows.map((row, i) => ({ ...row, key: sent.rows[i]?.key ?? row.key })),
    voices: stored.voices.map((voice, i) => ({ ...voice, key: sent.voices[i]?.key ?? voice.key })),
  };
  return { baseline, form: rebaseLibrary(sent, current, baseline) };
}
