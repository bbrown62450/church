/**
 * Draft → API payload, PROVISIONAL (S "mapping.ts"; F §4.6 "Draft → API
 * payload"). Slice 5a owns this file and replaces it with the real
 * `ServiceDraft` mapping and `serviceToDraft`. Slice 2 uses it only for
 * `fingerprint`, so `isDirty` has something stable to compare.
 *
 * One rule 5a's replacement must keep: the picks sent are the explicit values
 * of `resolveReadings`, so a pick that is no longer an option is sent as "",
 * whatever the stored draft says (S Hand-offs, 5a "Bulletin readings").
 */
import { cleanLines } from "@/lib/scripture-refs";

import { effectivePicks } from "./readings";
import { SECTION_KEYS, SLOTS, type DraftV1, type HymnPick, type SectionKey, type Slot } from "./schema";

/** Inventory §2.1's `HymnRef`. */
export type HymnRefPayload = { hymn_id: string | null; title: string; number: number | null; hymnal: string | null };

/** Inventory §2.1's `ServiceDraft` plus `hymnal` (F §1.3), written by hand until 5a adds the API model. */
export type ServiceDraftPayload = {
  service_date_iso: string;
  occasion: string;
  scriptures: string[];
  hymns: Record<Slot, HymnRefPayload | null>;
  liturgy: Partial<Record<SectionKey, string>>;
  sermon_title: string;
  selected_ot_ref: string;
  selected_nt_ref: string;
  include_communion: boolean;
  custom_elements: { label: string; text: string; insert_after: string }[];
  hymnal: string | null;
};

function hymnRef(pick: HymnPick | null): HymnRefPayload | null {
  return pick ? { hymn_id: pick.hymn_id, title: pick.title, number: pick.number, hymnal: pick.hymnal } : null;
}

export function draftToServicePayload(draft: DraftV1): ServiceDraftPayload {
  const picks = effectivePicks(draft);
  const liturgy: Partial<Record<SectionKey, string>> = {};
  for (const key of SECTION_KEYS) {
    const card = draft.liturgy.cards[key];
    if (card.enabled && card.text.trim() !== "") liturgy[key] = card.text;
  }
  return {
    service_date_iso: draft.readings.date_iso,
    occasion: draft.readings.occasion,
    scriptures: cleanLines(draft.readings.scriptures),
    hymns: Object.fromEntries(SLOTS.map((slot) => [slot, hymnRef(draft.hymns.slots[slot])])) as Record<
      Slot,
      HymnRefPayload | null
    >,
    liturgy,
    sermon_title: draft.liturgy.sermon_title,
    selected_ot_ref: picks.otAuto ? "" : (picks.ot ?? ""),
    selected_nt_ref: picks.ntAuto ? "" : (picks.nt ?? ""),
    include_communion: draft.liturgy.include_communion,
    custom_elements: draft.liturgy.custom_elements.map(({ label, text, insert_after }) => ({
      label,
      text,
      insert_after,
    })),
    hymnal: draft.hymns.hymnal,
  };
}
