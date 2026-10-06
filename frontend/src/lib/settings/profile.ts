/**
 * The Church page's form (slice 6a-1; 6a spec "Church profile"). The form
 * keeps a baseline (built from the last profile the server sent) and the
 * current edits; a save sends only the fields that differ, trimmed as the
 * server trims them, so a field nobody touched is never written and another
 * admin's change to it is never put back.
 */
import type { ChurchPatch, ChurchProfile, Hymnals, Translations } from "@/lib/api/types";

export type ProfileForm = {
  name: string;
  timezone: string;
  bible_translation: string;
  default_hymnal: string;
  default_benediction: string;
};

const FIELDS = ["name", "timezone", "bible_translation", "default_hymnal", "default_benediction"] as const;

/**
 * The form a profile starts at, and the baseline: the stored translation and
 * hymnal when set (even one no longer offered), else the ones in effect; ""
 * for the hymnal when the church has none (the field is then not shown).
 */
export function profileFormFrom(p: ChurchProfile): ProfileForm {
  return {
    name: p.name,
    timezone: p.timezone,
    bible_translation: p.bible_translation ?? p.effective_translation,
    default_hymnal: p.default_hymnal ?? p.effective_hymnal ?? "",
    default_benediction: p.default_benediction,
  };
}

/** A field as the server stores it: trimmed, and the Benediction's line ends as "\n". */
function cleaned(field: keyof ProfileForm, value: string): string {
  return (field === "default_benediction" ? value.replace(/\r\n?/g, "\n") : value).trim();
}

/** `PATCH /church`'s body: each field whose cleaned value differs from the baseline's, cleaned. Never a "" hymnal. */
export function diffProfile(baseline: ProfileForm, current: ProfileForm): ChurchPatch {
  const patch: ChurchPatch = {};
  for (const field of FIELDS) {
    const value = cleaned(field, current[field]);
    if (value === cleaned(field, baseline[field])) continue;
    if (field === "default_hymnal" && value === "") continue;
    patch[field] = value;
  }
  return patch;
}

/** True while a save would send something. */
export function hasChanges(baseline: ProfileForm, current: ProfileForm): boolean {
  return Object.keys(diffProfile(baseline, current)).length > 0;
}

/**
 * 6a's rebase rule for a settings form: newer server data (`next`) replaces
 * each field the user has not edited (still equal to `oldBaseline` by
 * `same`, exact equality unless given), and each edited field keeps the edit.
 */
export function rebaseForm<T extends Record<string, string>>(
  oldBaseline: T,
  current: T,
  next: T,
  same: (key: keyof T, a: string, b: string) => boolean = (_key, a, b) => a === b,
): T {
  const out = { ...next };
  for (const key of Object.keys(next) as (keyof T)[]) {
    if (!same(key, current[key], oldBaseline[key])) out[key] = current[key];
  }
  return out;
}

/**
 * The Church form's rebase: a field counts as edited only when its cleaned
 * value differs (the comparison Save and the leave guard use), so an edit
 * that cleans away (a trailing space or line break) takes newer server data
 * instead of holding a stale value a later save would send.
 */
export function rebaseProfile(oldBaseline: ProfileForm, current: ProfileForm, next: ProfileForm): ProfileForm {
  return rebaseForm(oldBaseline, current, next, (key, a, b) => cleaned(key, a) === cleaned(key, b));
}

/** The translation select's items: the server's, plus a stored one no longer offered here, kept selectable. */
export function translationItems(translations: Translations | undefined, stored: string | null): Record<string, string> {
  const items: Record<string, string> = Object.fromEntries((translations?.items ?? []).map((t) => [t.id, t.label]));
  if (stored !== null && !(stored in items)) items[stored] = `${stored.toUpperCase()} (not available on this server)`;
  return items;
}

/** The hymnal select's items: the church's hymnals, plus a stored default it no longer has, kept selectable. */
export function hymnalItems(hymnals: Hymnals | undefined, stored: string | null): Record<string, string> {
  const items: Record<string, string> = Object.fromEntries((hymnals?.items ?? []).map((h) => [h.code, h.code]));
  if (stored !== null && !(stored in items)) items[stored] = `${stored} (no longer in your hymnals)`;
  return items;
}
