/**
 * Readings transitions and selectors (S "readings.ts"; F §4.6 "Never destroy
 * typed input"). Pure: each takes a draft and returns the next one, or the
 * same object when nothing changes, so `update(recipe)` stays a no-op.
 * Slice 2c's Date & readings step calls them; slice 2b's store uses
 * `normalizePicks` and `setDate`.
 */
import type { ChurchProfile, Lectionary, Translations } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { cleanLines, pickerOptions, resolveReadings, scriptureKey, type ReadingPair } from "@/lib/scripture-refs";

import { onDateChanged } from "./date-effects";
import type { DraftReadings, DraftV1 } from "./schema";

function withReadings(d: DraftV1, patch: Partial<DraftReadings>): DraftV1 {
  return { ...d, readings: { ...d.readings, ...patch } };
}

/** Sets the date and its origin, then runs the date side effects. Never touches the readings fields. */
export function setDate(d: DraftV1, iso: string, origin: DraftReadings["date_origin"] = "user"): DraftV1 {
  // An impossible date is stored as "", so the saved draft always loads again (F §4.6).
  const next = iso === "" || isValidDateIso(iso) ? iso : "";
  if (d.readings.date_iso === next && d.readings.date_origin === origin) return d;
  const prevIso = d.readings.date_iso;
  return onDateChanged(withReadings(d, { date_iso: next, date_origin: origin }), prevIso);
}

/** Fills occasion and scriptures from set `i` of this date's lookup; clears both picks. */
export function applyReadingSet(d: DraftV1, lect: Lectionary, i: number): DraftV1 {
  if (lect.date !== d.readings.date_iso) {
    throw new Error(`applyReadingSet: lookup for ${lect.date}, draft dated ${d.readings.date_iso}`);
  }
  const set = lect.reading_sets[i];
  if (!set) throw new Error(`applyReadingSet: no reading set ${i}`);
  const r = d.readings;
  if (
    r.fields_origin === "lectionary" &&
    r.occasion === set.name &&
    r.reading_set?.date_iso === lect.date &&
    r.reading_set.index === i &&
    r.selected_ot_ref === "" &&
    r.selected_nt_ref === "" &&
    r.scriptures.length === set.scriptures.length &&
    r.scriptures.every((line, n) => line === set.scriptures[n])
  ) {
    return d;
  }
  return withReadings(d, {
    occasion: set.name,
    scriptures: [...set.scriptures],
    fields_origin: "lectionary",
    reading_set: { date_iso: lect.date, index: i },
    selected_ot_ref: "",
    selected_nt_ref: "",
  });
}

/**
 * The set switcher's choice (S UX item 2): applies set `i` like
 * `applyReadingSet`, and a choice that changes the draft also makes a
 * `default` date the user's (owner answer Q2, 2026-09-29), so "New service"
 * asks first and the mount-time roll-forward keeps the date.
 */
export function chooseReadingSet(d: DraftV1, lect: Lectionary, i: number): DraftV1 {
  const next = applyReadingSet(d, lect, i);
  if (next === d || next.readings.date_origin !== "default") return next;
  return withReadings(next, { date_origin: "user" });
}

/** Auto-fill applies only to empty fields, or to lectionary fields from another date. */
export function shouldAutoApply(d: DraftV1, lect: Lectionary): boolean {
  const r = d.readings;
  if (lect.date !== r.date_iso || lect.status !== "ok" || lect.reading_sets.length === 0) return false;
  return r.fields_origin === "empty" || (r.fields_origin === "lectionary" && r.reading_set?.date_iso !== r.date_iso);
}

export function editOccasion(d: DraftV1, occasion: string): DraftV1 {
  if (d.readings.occasion === occasion && d.readings.fields_origin === "user") return d;
  return withReadings(d, { occasion, fields_origin: "user" });
}

/** Stores the textarea's raw text as lines. Picks are left alone while the user types. */
export function editScriptureLines(d: DraftV1, raw: string): DraftV1 {
  const scriptures = raw.split("\n");
  const same =
    d.readings.fields_origin === "user" &&
    scriptures.length === d.readings.scriptures.length &&
    scriptures.every((line, i) => line === d.readings.scriptures[i]);
  return same ? d : withReadings(d, { scriptures, fields_origin: "user" });
}

/** Clears each pick that is no longer an option for its side; returns `d` when both are still valid. */
export function normalizePicks(d: DraftV1): DraftV1 {
  const options = pickerOptions(cleanLines(d.readings.scriptures));
  const ot = options.ot.includes(d.readings.selected_ot_ref.trim()) ? d.readings.selected_ot_ref : "";
  const nt = options.nt.includes(d.readings.selected_nt_ref.trim()) ? d.readings.selected_nt_ref : "";
  if (ot === d.readings.selected_ot_ref && nt === d.readings.selected_nt_ref) return d;
  return withReadings(d, { selected_ot_ref: ot, selected_nt_ref: nt });
}

/** When the scripture textarea loses focus. */
export function commitScriptureLines(d: DraftV1): DraftV1 {
  return normalizePicks(d);
}

export function clearReadings(d: DraftV1): DraftV1 {
  const r = d.readings;
  if (
    r.fields_origin === "empty" &&
    r.occasion === "" &&
    r.scriptures.length === 0 &&
    r.reading_set === null &&
    r.selected_ot_ref === "" &&
    r.selected_nt_ref === ""
  ) {
    return d;
  }
  return withReadings(d, {
    occasion: "",
    scriptures: [],
    fields_origin: "empty",
    reading_set: null,
    selected_ot_ref: "",
    selected_nt_ref: "",
  });
}

/** An explicit bulletin pick, or "" for automatic. */
export function setPick(d: DraftV1, side: "ot" | "nt", ref: string): DraftV1 {
  const key = side === "ot" ? "selected_ot_ref" : "selected_nt_ref";
  return d.readings[key] === ref ? d : withReadings(d, { [key]: ref });
}

/** Stores null when the choice is the church's effective translation, so later default changes flow through. */
export function setTranslation(d: DraftV1, id: string, churchEffective: string): DraftV1 {
  const translation = id === churchEffective ? null : id;
  return d.readings.translation === translation ? d : withReadings(d, { translation });
}

// --- selectors ---------------------------------------------------------------

export function cleanScriptures(d: DraftV1): string[] {
  return cleanLines(d.readings.scriptures);
}

/** Lectionary fields that were filled for another date. */
export function readingsStale(d: DraftV1): boolean {
  return d.readings.fields_origin === "lectionary" && d.readings.reading_set?.date_iso !== d.readings.date_iso;
}

function sameScriptures(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((line, i) => scriptureKey(line) === scriptureKey(b[i]));
}

/** The set whose references equal the draft's cleaned scriptures; else the stored index for this date; else null. */
export function selectedSetIndex(d: DraftV1, lect: Lectionary): number | null {
  if (lect.date !== d.readings.date_iso) return null;
  const lines = cleanScriptures(d);
  const matching = lect.reading_sets.findIndex((set) => sameScriptures(set.scriptures, lines));
  if (matching >= 0) return matching;
  const stored = d.readings.reading_set;
  if (stored && stored.date_iso === lect.date && stored.index < lect.reading_sets.length) return stored.index;
  return null;
}

/**
 * The "Readings for {date} are available" banner (S UX item 3): sets for this
 * date, none equal to the cleaned scriptures, and typed fields not filled from
 * this date's lectionary, or archived fields whose date has changed.
 */
export function showAvailableBanner(d: DraftV1, lect: Lectionary | undefined): boolean {
  if (!lect || lect.date !== d.readings.date_iso || lect.reading_sets.length === 0) return false;
  const lines = cleanScriptures(d);
  if (lect.reading_sets.some((set) => sameScriptures(set.scriptures, lines))) return false;
  const r = d.readings;
  if (r.fields_origin === "user") return r.reading_set?.date_iso !== r.date_iso;
  if (r.fields_origin === "archive") return r.date_origin !== "archive";
  return false;
}

/** The bulletin readings as the screen, the payload and (from 5a) the docx show them. */
export function effectivePicks(d: DraftV1): ReadingPair {
  return resolveReadings(d.readings.scriptures, d.readings.selected_ot_ref, d.readings.selected_nt_ref);
}

/** The stored override when the loaded list offers it; else the church's effective translation. */
export function effectiveTranslation(
  d: DraftV1,
  church: Pick<ChurchProfile, "effective_translation">,
  translations: Translations | undefined,
): string {
  const chosen = d.readings.translation;
  if (chosen && translations?.items.some((item) => item.id === chosen)) return chosen;
  return church.effective_translation;
}
