/**
 * The 8 liturgy sections as the draft and the pure status code need them
 * (slice 4 spec, Backend 1 `SECTIONS`; F §4.6 "Fresh draft"): each section's
 * label and whether a fresh draft switches it on. This is the one TypeScript
 * copy; `sections.test.ts` pins it to backend/tests/fixtures/shared/
 * liturgy_sections.json, which backend/liturgy_config.SECTIONS also equals.
 * The step reads the rest (rows, hints, the order of worship) from
 * GET /liturgy/config.
 */
import type { SectionKey } from "@/lib/draft/schema";

export const SECTION_LABELS: Readonly<Record<SectionKey, string>> = {
  call_to_worship: "Call to Worship",
  opening_prayer: "Opening Prayer",
  prayer_of_confession: "Prayer of Confession",
  assurance: "Assurance of Pardon",
  prayer_for_illumination: "Prayer for Illumination",
  prayers_of_the_people: "Prayers of the People",
  offertory_prayer: "Offertory Prayer",
  benediction: "Benediction",
};

/** Every section starts switched on except the Prayers of the People (app.py:890 parity). */
export const DEFAULT_ENABLED: Readonly<Record<SectionKey, boolean>> = {
  call_to_worship: true,
  opening_prayer: true,
  prayer_of_confession: true,
  assurance: true,
  prayer_for_illumination: true,
  prayers_of_the_people: false,
  offertory_prayer: true,
  benediction: true,
};
