/**
 * The Hymns step's words (S Slot cards, notices, chips, "Newer-hymn year
 * label"). Pure; dates go through `lib/dates.ts`.
 */
import type { Hymn } from "@/lib/api/types";
import { formatAbbrevDate, formatServiceDate } from "@/lib/dates";
import type { Slot } from "@/lib/draft/schema";

export const SLOT_META: Record<Slot, { title: string; caption: string; name: string }> = {
  opening: { title: "Opening hymn", caption: "Gathering / call to worship", name: "Opening" },
  response: { title: "Response hymn", caption: "After the sermon — responds to the scripture (NT reading)", name: "Response" },
  closing: { title: "Closing hymn", caption: "Joyful / sending", name: "Closing" },
};

export const MISSING_NOTICE = "Not in your hymnal. Choose a replacement.";

/** "#403 Come, Thou Almighty King", or the title alone when the number is null. */
export function hymnText(h: { number: number | null; title: string }): string {
  return h.number === null ? h.title : `#${h.number} ${h.title}`;
}

/** The badge on a picker row or idea: "Used Sep 7" before the service, "Planned Oct 18" after it. */
export function recentUseLabel(dateIso: string, serviceDateIso: string): string {
  return `${dateIso < serviceDateIso ? "Used" : "Planned"} ${formatAbbrevDate(dateIso, serviceDateIso)}`;
}

/** The notice under a pick (only when the service date is valid). */
export function recentUseNotice(dateIso: string, serviceDateIso: string): string {
  const day = formatServiceDate(dateIso);
  return dateIso < serviceDateIso
    ? `Used on ${day} — within 12 weeks of this service.`
    : `Also planned for ${day} — within 12 weeks of this service.`;
}

/** "Also chosen as the Closing hymn." / "… the Opening and Closing hymns."; null when no other slot. */
export function duplicateNotice(others: readonly Slot[]): string | null {
  if (others.length === 0) return null;
  const names = others.map((slot) => SLOT_META[slot].name);
  return others.length === 1
    ? `Also chosen as the ${names[0]} hymn.`
    : `Also chosen as the ${names.slice(0, -1).join(", ")} and ${names.at(-1)} hymns.`;
}

/** "Written 1985" for a hymn the server flags as newer than the church prefers; else null (amendment 2026-09-26). */
export function newerYearLabel(h: Pick<Hymn, "newer_than_preferred" | "text_year">): string | null {
  return h.newer_than_preferred && h.text_year !== null ? `Written ${h.text_year}` : null;
}

/** An idea's accessible name: "Use {title} as the opening hymn", with ", written {year}," for a flagged hymn. */
export function chipName(h: Pick<Hymn, "title" | "newer_than_preferred" | "text_year">, slot: Slot): string {
  const year = newerYearLabel(h) === null ? "" : `, written ${h.text_year},`;
  return `Use ${h.title}${year} as the ${slot} hymn`;
}
