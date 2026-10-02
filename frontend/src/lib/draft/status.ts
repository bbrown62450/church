/**
 * Step status, "nothing to lose" and "Still needed" (F §4.7; S "status.ts").
 * Pure functions of the draft; the shell decides what an unshipped step shows.
 */
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { DEFAULT_ENABLED, SECTION_LABELS } from "@/lib/liturgy/sections";
import { liturgyCounts } from "@/lib/liturgy/summary";
import { cleanLines } from "@/lib/scripture-refs";

import { SECTION_KEYS, SLOTS, type DraftV1, type Slot, type StepId } from "./schema";
import { SHIPPED_STEPS } from "./steps";

export type StepStatus =
  | { kind: "complete" }
  | { kind: "incomplete"; done: number; total: number }
  /** A step whose content has not shipped: the muted "Soon". */
  | { kind: "soon" }
  /** Review before slice 5a (and a draft that was never saved). */
  | { kind: "not_in_archive" };

function counted(done: number, total: number): StepStatus {
  return done === total ? { kind: "complete" } : { kind: "incomplete", done, total };
}

/**
 * Date & readings' field limits (S UX items 4 and 5); the step shows a message
 * past each. A scripture line is measured trimmed, as its row sends it.
 */
export const OCCASION_MAX = 300;
export const MAX_READINGS = 20;
export const MAX_LINE = 200;

/** The inline messages for the raw scripture lines (S UX item 5); blank lines are allowed and not counted, and a line is measured trimmed. */
export function scriptureProblems(lines: readonly string[]): string[] {
  const problems: string[] = [];
  if (lines.filter((line) => line.trim() !== "").length > MAX_READINGS) problems.push("Up to 20 readings.");
  const long = lines.findIndex((line) => line.trim().length > MAX_LINE);
  if (long >= 0) problems.push(`Line ${long + 1} is too long (max 200 characters).`);
  return problems;
}

/**
 * True while a Date & readings field shows its message for a value it holds
 * (an occasion over 300 characters, more than 20 readings or a line over
 * 200): the Word documents card blocks downloads until it is fixed (5a-1
 * build review fix 6). A missing or bad date has its own message there.
 */
export function hasReadingsError(draft: DraftV1): boolean {
  return draft.readings.occasion.length > OCCASION_MAX || scriptureProblems(draft.readings.scriptures).length > 0;
}

/** A date the lectionary lookup and the archive accept. */
export function hasServiceDate(draft: DraftV1): boolean {
  return isValidDateIso(draft.readings.date_iso) && inSupportedRange(draft.readings.date_iso);
}

/**
 * F §4.7: readings count a valid date, a non-empty occasion and at least one
 * scripture ("n of 3"), and a field whose message shows (an occasion over 300
 * characters; more than 20 readings or a line over 200) does not count, so
 * the step is never "Complete" with an error on screen (owner answer E,
 * 2026-09-29); hymns the three slots; liturgy the enabled cards that
 * have text. Review reads "Not in archive" until 5a adds "Saved" and
 * "Unsaved changes". An unshipped step (other than Review) is "Soon".
 */
export function stepStatus(
  draft: DraftV1,
  step: StepId,
  shipped: ReadonlySet<StepId> = SHIPPED_STEPS,
): StepStatus {
  if (step === "review") return { kind: "not_in_archive" };
  if (!shipped.has(step)) return { kind: "soon" };
  if (step === "readings") {
    const r = draft.readings;
    const scripturesOk = cleanLines(r.scriptures).length > 0 && scriptureProblems(r.scriptures).length === 0;
    const done = [hasServiceDate(draft), r.occasion.trim() !== "" && r.occasion.length <= OCCASION_MAX, scripturesOk];
    return counted(done.filter(Boolean).length, 3);
  }
  if (step === "hymns") {
    return counted(SLOTS.filter((slot) => draft.hymns.slots[slot] !== null).length, SLOTS.length);
  }
  // Liturgy: the enabled cards with text, from the count the summary shows too (slice 4b); all off is complete.
  const { ready, enabled } = liturgyCounts(draft);
  return counted(ready, enabled);
}

/**
 * "Nothing the user would lose" (S "status.ts"), decided by origins rather
 * than text, so defaults that later slices fill in (slice 4's benediction)
 * never make a fresh draft look edited. A date the user picked, a reading set
 * chosen in the switcher (which makes the date the user's, `chooseReadingSet`)
 * and a translation override count as work here (owner answer Q2,
 * 2026-09-29). "New service" and the mount-time roll-forward both keep the
 * translation, so they look past it with `withoutTranslation` (owner answer
 * A, 2026-09-29). A hymn in any slot and a chosen hymnal count too; the
 * Exclude switch and the AI's other ideas never do (owner answer 1,
 * 2026-09-29, slice 3b; the same fields the fingerprint payload holds). On
 * the Liturgy step everything that ends up in the service counts: card text,
 * a card switched away from its default, communion the user set, the sermon
 * title and custom elements; a Benediction still following the church
 * default (origin "default") and text that prints nothing (blank after
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b).
 */
export function isPristine(draft: DraftV1): boolean {
  const r = draft.readings;
  const l = draft.liturgy;
  return (
    r.date_origin !== "user" &&
    r.translation === null &&
    (r.fields_origin === "empty" || r.fields_origin === "lectionary") &&
    r.selected_ot_ref === "" &&
    r.selected_nt_ref === "" &&
    SLOTS.every((slot) => draft.hymns.slots[slot] === null) &&
    draft.hymns.hymnal === null &&
    SECTION_KEYS.every((key) => {
      const card = l.cards[key];
      const text = card.origin === "default" || (card.origin === "empty" && card.text.trim() === "");
      return card.enabled === DEFAULT_ENABLED[key] && text;
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title.trim() === "" &&
    l.custom_elements.length === 0 &&
    draft.editing === null
  );
}

/**
 * A copy of the draft with the translation override cleared, for the checks
 * that keep the translation and so never count it as something to lose:
 * "New service" (`isDirty`) and the roll-forward (`isPristine`).
 */
export function withoutTranslation(draft: DraftV1): DraftV1 {
  return { ...draft, readings: { ...draft.readings, translation: null } };
}

/** The slot names in "No Opening hymn" (the same words as `lib/hymns/labels.ts` `SLOT_META`). */
const SLOT_NAMES: Record<Slot, string> = { opening: "Opening", response: "Response", closing: "Closing" };

export type NeededItem = {
  step: StepId;
  /** "No service date" */
  message: string;
  /** The link text: "Choose one" */
  action: string;
  /** Where the link goes when not the step's own page: "/builder/liturgy#card-call_to_worship" (slice 4b). */
  href?: string;
};

/**
 * What Review lists under "Still needed", from shipped steps only: the
 * readings' gaps (2c), then one row per empty hymn slot in slot order (3b,
 * F §4.7's wording), then one row per switched-on liturgy card with no text,
 * linking to that card, and "No sermon title" (4b, the wording 5a's Review
 * checklist reuses).
 */
export function stillNeeded(draft: DraftV1, shipped: ReadonlySet<StepId> = SHIPPED_STEPS): NeededItem[] {
  const items: NeededItem[] = [];
  if (shipped.has("readings")) {
    if (!hasServiceDate(draft)) items.push({ step: "readings", message: "No service date", action: "Choose one" });
    if (draft.readings.occasion.trim() === "") {
      items.push({ step: "readings", message: "No occasion", action: "Add one" });
    }
    if (cleanLines(draft.readings.scriptures).length === 0) {
      items.push({ step: "readings", message: "No scripture readings", action: "Add one" });
    }
  }
  if (shipped.has("hymns")) {
    for (const slot of SLOTS) {
      if (draft.hymns.slots[slot] !== null) continue;
      items.push({ step: "hymns", message: `No ${SLOT_NAMES[slot]} hymn`, action: "Choose one" });
    }
  }
  if (shipped.has("liturgy")) {
    for (const key of SECTION_KEYS) {
      const card = draft.liturgy.cards[key];
      if (!card.enabled || card.text.trim() !== "") continue;
      items.push({
        step: "liturgy",
        message: `${SECTION_LABELS[key]} is empty`,
        action: "Write or generate it",
        href: `/builder/liturgy#card-${key}`,
      });
    }
    if (draft.liturgy.sermon_title.trim() === "") {
      items.push({ step: "liturgy", message: "No sermon title", action: "Add one" });
    }
  }
  return items;
}
