/**
 * Settings → Rubric's form rules (slice 6a-3a; 6a spec "Pure helpers" `rubric.ts`;
 * the service rubric spec's limits). The form keeps a baseline (built from
 * the last rubric the server sent) and the current edits: one list of points
 * per checklist and one value per preference. A save sends one sparse
 * `PATCH /rubric` with only the items that changed, cleaned as the server
 * cleans them; an item put back to its default is sent as null, so the church
 * keeps following future improvements to the defaults.
 */
import { SECTION_KEYS, SLOTS, type SectionKey, type Slot } from "@/lib/draft/schema";
import type { RubricValues } from "@/lib/api/types";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

/** The hymn slots' titles (backend `service_rubric.HYMN_SLOT_LABELS`). */
export const HYMN_SLOT_LABELS: Readonly<Record<Slot, string>> = {
  opening: "Opening (Gathering) Hymn",
  response: "Response Hymn (after the sermon)",
  closing: "Closing (Sending) Hymn",
};

/** The server's limits (`service_rubric.MAX_ITEMS`, `MAX_ITEM_CHARS`, `MIN_YEAR`). */
export const MAX_POINTS = 12;
export const MAX_POINT_LENGTH = 300;
export const MIN_YEAR = 1500;
export const KEEP_ONE_POINT = "Keep at least one point, or use Reset to default.";
export const AT_MOST_POINTS = "A checklist can have at most 12 points.";

/** One checklist's name as `customized` and the form use it: "hymns.opening", "prayers.benediction". */
export type ChecklistKey = `hymns.${Slot}` | `prayers.${SectionKey}`;
export type Checklist = { key: ChecklistKey; group: "hymns" | "prayers"; item: string; label: string };

/** Every checklist in the page's order: the hymn slots, then the prayers in section order. */
export const CHECKLISTS: readonly Checklist[] = [
  ...SLOTS.map((slot): Checklist => ({ key: `hymns.${slot}`, group: "hymns", item: slot, label: HYMN_SLOT_LABELS[slot] })),
  ...SECTION_KEYS.map(
    (section): Checklist => ({ key: `prayers.${section}`, group: "prayers", item: section, label: SECTION_LABELS[section] }),
  ),
];

export type RubricForm = {
  checklists: Record<ChecklistKey, string[]>;
  prefer_before_year: string;
  prefer_familiar: boolean;
};

/** A point as the server stores it: every run of whitespace (line breaks too) one space, trimmed. */
export function cleanPoint(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

/** A checklist as the server stores it: each point cleaned, blank points dropped. */
export function cleanPoints(points: readonly string[]): string[] {
  return points.map(cleanPoint).filter((p) => p !== "");
}

const samePoints = (a: readonly string[], b: readonly string[]) => {
  const x = cleanPoints(a);
  const y = cleanPoints(b);
  return x.length === y.length && x.every((p, i) => p === y[i]);
};

function points(values: RubricValues, list: Checklist): string[] {
  return [...(values[list.group][list.item] ?? [])];
}

/** The form a rubric starts at, and its baseline. */
export function rubricFormFrom(values: RubricValues): RubricForm {
  return {
    checklists: Object.fromEntries(CHECKLISTS.map((list) => [list.key, points(values, list)])) as Record<ChecklistKey, string[]>,
    prefer_before_year: String(values.prefer_before_year),
    prefer_familiar: values.prefer_familiar,
  };
}

/** The year typed, or null when it is not a whole number. */
function parseYear(text: string): number | null {
  const trimmed = text.trim();
  return /^\d{1,4}$/.test(trimmed) ? Number(trimmed) : null;
}

/** "The preferred year must be between 1500 and {thisYear}." (the server's words), or null. */
export function yearError(text: string, thisYear: number): string | null {
  const year = parseYear(text);
  return year !== null && year >= MIN_YEAR && year <= thisYear ? null : `The preferred year must be between ${MIN_YEAR} and ${thisYear}.`;
}

/** "Keep at least one point, or use Reset to default." when every point is blank or removed, else null. */
export function checklistError(list: readonly string[]): string | null {
  return cleanPoints(list).length === 0 ? KEEP_ONE_POINT : null;
}

/** Every message the form shows: per checklist, and the year's. */
export function rubricErrors(form: RubricForm, thisYear: number): Partial<Record<ChecklistKey | "prefer_before_year", string>> {
  const errors: Partial<Record<ChecklistKey | "prefer_before_year", string>> = {};
  for (const list of CHECKLISTS) {
    const message = checklistError(form.checklists[list.key]);
    if (message) errors[list.key] = message;
  }
  const year = yearError(form.prefer_before_year, thisYear);
  if (year) errors.prefer_before_year = year;
  return errors;
}

/** True when the checklist's cleaned points differ from the default's (its **Customized** badge). */
export function checklistCustomized(form: RubricForm, defaults: RubricValues, list: Checklist): boolean {
  return !samePoints(form.checklists[list.key], points(defaults, list));
}

/** The names of the items whose cleaned value differs between two forms. */
export function changedItems(a: RubricForm, b: RubricForm): string[] {
  const changed: string[] = CHECKLISTS.filter((list) => !samePoints(a.checklists[list.key], b.checklists[list.key])).map((l) => l.key);
  if (a.prefer_before_year.trim() !== b.prefer_before_year.trim()) changed.push("prefer_before_year");
  if (a.prefer_familiar !== b.prefer_familiar) changed.push("prefer_familiar");
  return changed;
}

export type RubricPatch = {
  hymns?: Partial<Record<Slot, string[] | null>>;
  prayers?: Partial<Record<SectionKey, string[] | null>>;
  prefer_before_year?: number | null;
  prefer_familiar?: boolean | null;
};

/**
 * `PATCH /rubric`'s body: only the items that changed from the baseline, each
 * cleaned; an item whose cleaned value equals its default is null. Call it
 * only when `rubricErrors` is empty (it never sends an empty checklist).
 */
export function rubricPatch(baseline: RubricForm, current: RubricForm, defaults: RubricValues): RubricPatch {
  const patch: RubricPatch = {};
  for (const list of CHECKLISTS) {
    const now = current.checklists[list.key];
    if (samePoints(now, baseline.checklists[list.key])) continue;
    const value = samePoints(now, points(defaults, list)) ? null : cleanPoints(now);
    if (list.group === "hymns") patch.hymns = { ...patch.hymns, [list.item]: value };
    else patch.prayers = { ...patch.prayers, [list.item]: value };
  }
  if (changedItems(baseline, current).includes("prefer_before_year")) {
    const year = parseYear(current.prefer_before_year);
    patch.prefer_before_year = year === defaults.prefer_before_year ? null : year;
  }
  if (current.prefer_familiar !== baseline.prefer_familiar) {
    patch.prefer_familiar = current.prefer_familiar === defaults.prefer_familiar ? null : current.prefer_familiar;
  }
  return patch;
}

/** Reset all's body: null for every item the church has customized (`customized`'s dotted names). */
export function resetAllPatch(customized: readonly string[]): RubricPatch {
  const patch: RubricPatch = {};
  for (const name of customized) {
    const list = CHECKLISTS.find((l) => l.key === name);
    if (list?.group === "hymns") patch.hymns = { ...patch.hymns, [list.item]: null };
    else if (list?.group === "prayers") patch.prayers = { ...patch.prayers, [list.item]: null };
    else if (name === "prefer_before_year") patch.prefer_before_year = null;
    else if (name === "prefer_familiar") patch.prefer_familiar = null;
  }
  return patch;
}

/**
 * 6a's rebase for the rubric: newer server data replaces each item the user
 * has not edited (its cleaned value still equal to the old baseline's), and
 * each edited item keeps the edit.
 */
export function rebaseRubric(oldBaseline: RubricForm, current: RubricForm, next: RubricForm): RubricForm {
  const edited = new Set(changedItems(oldBaseline, current));
  return {
    checklists: Object.fromEntries(
      CHECKLISTS.map((list) => [list.key, edited.has(list.key) ? current.checklists[list.key] : next.checklists[list.key]]),
    ) as Record<ChecklistKey, string[]>,
    prefer_before_year: edited.has("prefer_before_year") ? current.prefer_before_year : next.prefer_before_year,
    prefer_familiar: edited.has("prefer_familiar") ? current.prefer_familiar : next.prefer_familiar,
  };
}
