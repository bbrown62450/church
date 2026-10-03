/**
 * The church's standing bulletin settings (printed bulletin spec, PR 2a):
 * the parts of the order of worship they name, the form the Bulletin
 * settings page edits, and what the Printed bulletin card lists as not
 * filled in (PR 2 planning answer 3: a blank field prints nothing, so the
 * card says which are blank before anyone prints). The form follows 6a's
 * rule for settings forms: newer server data rebases it (a field not edited
 * takes the new value, an edited one keeps the edit), and the page warns
 * before leaving with unsaved edits.
 *
 * The limits mirror `backend/bulletin_settings.py` (`MAX_LENGTH`,
 * `MAX_ADDRESS_LINES`); the server checks them again.
 */
import type { BulletinSettings } from "@/lib/api/types";

export type ElementKey = BulletinSettings["starred"][number];
export type Role = NonNullable<BulletinSettings["leaders"][ElementKey]>;
export type TextField = Exclude<keyof BulletinSettings, "address_lines" | "starred" | "leaders">;

export const ROLES: readonly { key: Role; label: string }[] = [
  { key: "worship_leader", label: "Worship leader" },
  { key: "liturgist", label: "Liturgist" },
  { key: "organist", label: "Organist" },
];

/** The printed order of worship's parts, in its order (`bulletin_settings.ELEMENT_KEYS`). */
export const ELEMENTS: readonly { key: ElementKey; label: string }[] = [
  { key: "prelude", label: "Prelude" },
  { key: "welcome", label: "Welcome and Announcements" },
  { key: "call_to_worship", label: "Call to Worship" },
  { key: "opening_prayer", label: "Opening Prayer" },
  { key: "first_hymn", label: "Opening hymn" },
  { key: "prayer_of_confession", label: "Prayer of Confession" },
  { key: "assurance", label: "Assurance of Pardon" },
  { key: "gloria_patri", label: "Gloria Patri" },
  { key: "prayer_for_illumination", label: "Prayer for Illumination" },
  { key: "ot_reading", label: "First Reading" },
  { key: "nt_reading", label: "New Testament Reading" },
  { key: "sermon", label: "Sermon" },
  { key: "affirmation_of_faith", label: "Affirmation of Faith" },
  { key: "second_hymn", label: "Response hymn" },
  { key: "prayers_of_the_people", label: "Prayers of the People" },
  { key: "offering", label: "Offering" },
  { key: "doxology", label: "Doxology" },
  { key: "offertory_prayer", label: "Offertory Prayer" },
  { key: "third_hymn", label: "Closing hymn" },
  { key: "benediction", label: "Benediction" },
  { key: "postlude", label: "Postlude" },
];

export const MAX_ADDRESS_LINES = 3;
export const MAX_LENGTH: Record<TextField | "address_line", number> = {
  address_line: 60,
  phone: 40,
  email: 100,
  website: 100,
  facebook: 60,
  service_time: 40,
  worship_leader: 100,
  liturgist: 100,
  organist: 100,
  stand_note: 200,
  gloria_patri_words: 1000,
};

/** The page's form: the settings with the address as one text, a line each. */
export type BulletinForm = Omit<BulletinSettings, "address_lines"> & { address: string };
/** The form's text fields: the address and every other text. */
export type FormField = "address" | TextField;
const FORM_FIELDS: readonly FormField[] = [
  "address",
  "phone",
  "email",
  "website",
  "facebook",
  "service_time",
  "worship_leader",
  "liturgist",
  "organist",
  "stand_note",
  "gloria_patri_words",
];

export function formFromSettings(s: BulletinSettings): BulletinForm {
  const { address_lines, ...rest } = s;
  return { ...rest, address: address_lines.join("\n") };
}

/** The address's lines as the server stores them: trimmed, blank ones dropped. */
export function addressLines(address: string): string[] {
  return address
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "");
}

/** The address's problem, or null: at most 3 lines of at most 60 characters. */
export function addressError(address: string): string | null {
  const lines = addressLines(address);
  if (lines.length > MAX_ADDRESS_LINES || lines.some((line) => line.length > MAX_LENGTH.address_line)) {
    return `Use up to ${MAX_ADDRESS_LINES} lines of up to ${MAX_LENGTH.address_line} characters each.`;
  }
  return null;
}

/** `PUT /church/bulletin-settings`'s body: every field, the starred parts and the leaders in the printed order. */
export function settingsFromForm(f: BulletinForm): BulletinSettings {
  const { address, starred, leaders, ...text } = f;
  const order = ELEMENTS.map((e) => e.key);
  return {
    ...text,
    address_lines: addressLines(address),
    starred: order.filter((key) => starred.includes(key)),
    leaders: Object.fromEntries(order.filter((key) => leaders[key]).map((key) => [key, leaders[key]])),
  };
}

/**
 * 6a's rebase rule (one value per text, per part's leader and per part's star):
 * each value still equal to `baseline` (not edited) takes `next`'s; each edited
 * one keeps `current`'s. Used when newer server data arrives while the form is
 * open, and after a save (with the form as sent as the baseline, so what was
 * typed while saving is kept).
 */
export function rebaseForm(baseline: BulletinForm, current: BulletinForm, next: BulletinForm): BulletinForm {
  const out: BulletinForm = { ...next };
  for (const field of FORM_FIELDS) {
    if (current[field] !== baseline[field]) out[field] = current[field];
  }
  const starred = (f: BulletinForm, key: ElementKey) => f.starred.includes(key);
  out.starred = ELEMENTS.map((e) => e.key).filter((key) =>
    starred(current, key) !== starred(baseline, key) ? starred(current, key) : starred(next, key),
  );
  const leaders: BulletinForm["leaders"] = {};
  for (const { key } of ELEMENTS) {
    const role = current.leaders[key] !== baseline.leaders[key] ? current.leaders[key] : next.leaders[key];
    if (role) leaders[key] = role;
  }
  out.leaders = leaders;
  return out;
}

/** Whether the form has edits not yet saved (anything that differs from `baseline`). */
export function isDirty(baseline: BulletinForm, current: BulletinForm): boolean {
  return (
    FORM_FIELDS.some((field) => current[field] !== baseline[field]) ||
    ELEMENTS.some(
      ({ key }) =>
        current.leaders[key] !== baseline.leaders[key] || current.starred.includes(key) !== baseline.starred.includes(key),
    )
  );
}

/** A 422's `fields` ("phone", "address_lines.0", …) by the form field each names. */
export function formErrors(fields: Record<string, string>): Partial<Record<FormField, string>> {
  const errors: Partial<Record<FormField, string>> = {};
  for (const [name, message] of Object.entries(fields)) {
    const head = name.split(".")[0];
    const field = head === "address_lines" ? "address" : (FORM_FIELDS.find((f) => f === head) ?? null);
    if (field && !errors[field]) errors[field] = message;
  }
  return errors;
}

/** What a blank field is called in "Not filled in: …", in the page's order. */
const MISSING_LABELS: readonly [keyof BulletinSettings, string][] = [
  ["address_lines", "address"],
  ["phone", "phone"],
  ["email", "email"],
  ["website", "website"],
  ["facebook", "Facebook name"],
  ["service_time", "service time"],
  ["worship_leader", "worship leader"],
  ["liturgist", "liturgist"],
  ["organist", "organist"],
  ["stand_note", "stand note"],
  ["gloria_patri_words", "Gloria Patri words"],
];

/** The standing fields that are blank (and so print nothing), by their labels. */
export function notFilledIn(s: BulletinSettings): string[] {
  return MISSING_LABELS.filter(([field]) => {
    const value = s[field];
    return Array.isArray(value) ? value.length === 0 : typeof value === "string" && value.trim() === "";
  }).map(([, label]) => label);
}

/** "Not filled in: phone, organist." */
export function notFilledInLine(missing: readonly string[]): string {
  return `Not filled in: ${missing.join(", ")}.`;
}
