/**
 * Step status, "nothing to lose" and "Still needed" (F §4.7; S "status.ts").
 * Pure functions of the draft; the shell decides what an unshipped step shows.
 */
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { cleanLines } from "@/lib/scripture-refs";

import { SECTION_KEYS, SLOTS, type DraftV1, type StepId } from "./schema";
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

/** A date the lectionary lookup and the archive accept. */
export function hasServiceDate(draft: DraftV1): boolean {
  return isValidDateIso(draft.readings.date_iso) && inSupportedRange(draft.readings.date_iso);
}

/**
 * F §4.7: readings count a valid date, a non-empty occasion and at least one
 * scripture ("n of 3"); hymns the three slots; liturgy the enabled cards that
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
    const done = [hasServiceDate(draft), r.occasion.trim() !== "", cleanLines(r.scriptures).length > 0];
    return counted(done.filter(Boolean).length, 3);
  }
  if (step === "hymns") {
    return counted(SLOTS.filter((slot) => draft.hymns.slots[slot] !== null).length, SLOTS.length);
  }
  const enabled = SECTION_KEYS.map((key) => draft.liturgy.cards[key]).filter((card) => card.enabled);
  return counted(enabled.filter((card) => card.text.trim() !== "").length, enabled.length);
}

/**
 * "Nothing the user would lose" (S "status.ts"), decided by origins rather
 * than text, so defaults that later slices fill in (slice 4's benediction)
 * never make a fresh draft look edited.
 */
export function isPristine(draft: DraftV1): boolean {
  const r = draft.readings;
  const l = draft.liturgy;
  return (
    (r.fields_origin === "empty" || r.fields_origin === "lectionary") &&
    r.selected_ot_ref === "" &&
    r.selected_nt_ref === "" &&
    SLOTS.every((slot) => draft.hymns.slots[slot] === null) &&
    SECTION_KEYS.every((key) => {
      const card = l.cards[key];
      return card.origin === "default" || (card.origin === "empty" && card.text === "");
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title === "" &&
    l.custom_elements.length === 0 &&
    draft.editing === null
  );
}

export type NeededItem = {
  step: StepId;
  /** "No service date" */
  message: string;
  /** The link text: "Choose one" */
  action: string;
};

/** What Review lists under "Still needed", from shipped steps only; slices 3 and 4 add their rows. */
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
  return items;
}
