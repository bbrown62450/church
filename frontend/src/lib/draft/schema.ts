/**
 * The per-church unsaved draft, version 4 (F §4.6; S "Draft store").
 *
 * This is F §4.6's draft shape. Version 2 (slice 5a-3) added the two fields
 * slice 5a brings with its own version bump: `editing.date_iso` (the saved
 * service's date; null for an undated saved service) and
 * `save_key_fingerprint` (`save-key.ts`). Version 3 (printed bulletin PR 2b)
 * adds `bulletin`, the Bulletin step's weekly fields (`bulletin.ts`), and the
 * step id "bulletin". Version 4 (printed bulletin PR 3b) adds the week's
 * cover picture, `bulletin.cover_image_id`, and its box to check ("cover",
 * first in `CARRY_KEYS`). The names `DraftV1` and
 * `draftV1Schema` stay, so no importer changes. Strings are
 * bounded generously (20 000) so a stored draft is never rejected for
 * length; the UI limits live in the components. `readings.scriptures` holds
 * the raw lines, blanks included; `cleanLines()` derives everything else.
 */
import { z } from "zod";

import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";

export const DRAFT_VERSION = 4;

export const STEP_IDS = ["readings", "hymns", "liturgy", "bulletin", "review"] as const;
export type StepId = (typeof STEP_IDS)[number];

export const SLOTS = ["opening", "response", "closing"] as const;
export type Slot = (typeof SLOTS)[number];

export const SECTION_KEYS = [
  "call_to_worship",
  "opening_prayer",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "prayers_of_the_people",
  "offertory_prayer",
  "benediction",
] as const;
export type SectionKey = (typeof SECTION_KEYS)[number];

const text = z.string().max(20_000);
// Timestamps must parse, so prune and cross-tab adoption can compare them (owner decision 1).
const timestamp = z.iso.datetime({ offset: true });
const dateIso = text.refine(isValidDateIso, "Not a YYYY-MM-DD date.");
const dateIsoOrEmpty = text.refine((s) => s === "" || isValidDateIso(s), "Not a YYYY-MM-DD date.");

const hymnPick = z.object({
  hymn_id: text.nullable(),
  title: text,
  number: z.number().int().nullable(),
  hymnal: text.nullable(),
});
export type HymnPick = z.infer<typeof hymnPick>;

function perSlot<T extends z.ZodType>(value: T) {
  return z.object({ opening: value, response: value, closing: value });
}

const card = z.object({
  enabled: z.boolean(),
  text,
  origin: z.enum(["empty", "typed", "ai", "default", "archive"]),
});
export type LiturgyCard = z.infer<typeof card>;

/** The three people the Bulletin step can change for one week (`bulletin_settings.ROLES`). */
export const PEOPLE = ["worship_leader", "liturgist", "organist"] as const;
export type Person = (typeof PEOPLE)[number];
/** The announcements (PR 2 planning answer 4), in the printed order. */
export const ANNOUNCEMENT_KEYS = ["ushers", "deacon", "coffee_hour", "activities", "prayer_concerns", "collection", "other"] as const;
export type AnnouncementKey = (typeof ANNOUNCEMENT_KEYS)[number];
/**
 * The boxes that carry forward from last week (PR 2 planning answer 5; PR 3
 * planning answer 7): the cover picture, the music and each announcement.
 */
export const CARRY_KEYS = ["cover", "prelude", "postlude", ...ANNOUNCEMENT_KEYS] as const;
export type CarryKey = (typeof CARRY_KEYS)[number];

const music = z.object({ title: text, composer: text });
const carryKeys = z.array(z.enum(CARRY_KEYS));
/** This week's name for each person; null follows the bulletin settings, "" is no one this week. */
const people = z.object(Object.fromEntries(PEOPLE.map((key) => [key, text.nullable()])) as Record<Person, z.ZodNullable<typeof text>>);
const bulletin = z.object({
  /** The week's cover picture (`POST /bulletin-images`), or null for none (printed bulletin PR 3b). */
  cover_image_id: text.nullable(),
  prelude: music,
  postlude: music,
  people,
  /** A part's leader this week, by element key (`bulletin_settings.ELEMENT_KEYS`). */
  leaders: z.record(text, text),
  announcements: z.object(Object.fromEntries(ANNOUNCEMENT_KEYS.map((key) => [key, text])) as Record<AnnouncementKey, typeof text>),
  /** Pasted reading text by the reading's reference, so a changed reading starts with an empty box. */
  pasted: z.record(text, text),
  /** The boxes still holding last week's text, not edited or kept since (saved with the service as `unchecked`). */
  carried: carryKeys,
  /** The boxes typed in, edited or kept: last week's never carries into them again (a box at a time). */
  edited: carryKeys,
  /** The date last week's bulletin was looked up for; null: not yet. */
  carried_for: dateIso.nullable(),
  /**
   * A saved service on another date ("Save as new service"): its people,
   * part leaders, pasted texts and marks, set aside while the date differs
   * from the saved one and put back if it is the saved date again; null
   * otherwise (`bulletin.ts` `followSaveMode`).
   */
  set_aside: z
    .object({ people, leaders: z.record(text, text), pasted: z.record(text, text), carried: carryKeys, edited: carryKeys })
    .nullable(),
});
export type DraftBulletin = z.infer<typeof bulletin>;

export const draftV1Schema = z.object({
  version: z.literal(DRAFT_VERSION),
  user_id: text,
  church_id: text,
  created_at: timestamp,
  updated_at: timestamp,
  last_step: z.enum(STEP_IDS),
  save_key: text,
  save_key_fingerprint: text.nullable(),
  editing: z.object({ service_id: text, saved_at: text, date_iso: dateIso.nullable() }).nullable(),
  saved_fingerprint: text.nullable(),
  readings: z.object({
    date_iso: dateIsoOrEmpty,
    date_origin: z.enum(["default", "user", "archive"]),
    reading_set: z.object({ date_iso: dateIso, index: z.number().int().min(0) }).nullable(),
    fields_origin: z.enum(["empty", "lectionary", "user", "archive"]),
    occasion: text,
    scriptures: z.array(text),
    selected_ot_ref: text,
    selected_nt_ref: text,
    translation: text.nullable(),
  }),
  hymns: z.object({
    hymnal: text.nullable(),
    exclude_recent: z.boolean(),
    slots: perSlot(hymnPick.nullable()),
    alternatives: z.object({ for_date_iso: dateIso, by_slot: perSlot(z.array(hymnPick)) }).nullable(),
  }),
  liturgy: z.object({
    sermon_title: text,
    include_communion: z.boolean(),
    communion_origin: z.enum(["default", "user", "archive"]),
    cards: z.object(
      Object.fromEntries(SECTION_KEYS.map((key) => [key, card])) as Record<SectionKey, typeof card>,
    ),
    custom_elements: z.array(z.object({ id: text, label: text, text, insert_after: text })),
  }),
  bulletin,
});

export type DraftV1 = z.infer<typeof draftV1Schema>;
export type DraftReadings = DraftV1["readings"];

/**
 * The profile fields the draft needs (`GET /church`): the zone for
 * `freshDraft` (slice 2a) and the church's default benediction, which an
 * untouched Benediction card shows (slice 4a; an older API leaves it out).
 */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean; default_benediction?: string };

/** The church's zone for `todayIn`, or undefined (the browser's zone) when the profile says it is not valid. */
export function churchZone(church: DraftChurch): string | undefined {
  return church.timezone_valid === false ? undefined : (church.timezone ?? undefined);
}

/**
 * A fresh draft (F §4.6 "Fresh draft"): dated the next Sunday strictly after
 * today in the church's zone, every field empty, the cards enabled except the
 * Prayers of the People, the benediction card `default`-origin with the
 * church's default benediction (DEFAULT_BENEDICTION_FALLBACK, the full
 * Halverson text, when the profile has none; slice 4b), communion on for a
 * first Sunday, an empty Bulletin step (PR 2b; last week's carries in when
 * the Bulletin step or Review shows it), a new save key with no pending
 * fingerprint, on step 1.
 */
export function freshDraft({
  church,
  user,
  now = new Date(),
}: {
  church: DraftChurch;
  user: { id: string };
  now?: Date;
}): DraftV1 {
  const date_iso = nextSunday(todayIn(churchZone(church), now));
  const stamp = now.toISOString();
  const cards = Object.fromEntries(
    SECTION_KEYS.map((key) => [
      key,
      key === "benediction"
        ? { enabled: DEFAULT_ENABLED[key], text: church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK, origin: "default" }
        : { enabled: DEFAULT_ENABLED[key], text: "", origin: "empty" },
    ]),
  ) as Record<SectionKey, LiturgyCard>;
  return {
    version: DRAFT_VERSION,
    user_id: user.id,
    church_id: church.id,
    created_at: stamp,
    updated_at: stamp,
    last_step: "readings",
    save_key: crypto.randomUUID(),
    save_key_fingerprint: null,
    editing: null,
    saved_fingerprint: null,
    readings: {
      date_iso,
      date_origin: "default",
      reading_set: null,
      fields_origin: "empty",
      occasion: "",
      scriptures: [],
      selected_ot_ref: "",
      selected_nt_ref: "",
      translation: null,
    },
    hymns: {
      hymnal: null,
      exclude_recent: true,
      slots: { opening: null, response: null, closing: null },
      alternatives: null,
    },
    liturgy: {
      sermon_title: "",
      include_communion: isFirstSundayOfMonth(date_iso),
      communion_origin: "default",
      cards,
      custom_elements: [],
    },
    bulletin: freshBulletin(),
  };
}

/** An empty Bulletin step: nothing filled in, the settings' people, no carry looked up yet. */
export function freshBulletin(): DraftBulletin {
  return {
    cover_image_id: null,
    prelude: { title: "", composer: "" },
    postlude: { title: "", composer: "" },
    people: { worship_leader: null, liturgist: null, organist: null },
    leaders: {},
    announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
    pasted: {},
    carried: [],
    edited: [],
    carried_for: null,
    set_aside: null,
  };
}

/** `localStorage` key of one user's draft for one church (F §4.6). */
export function draftKey(userId: string, churchId: string): string {
  return `wsb:draft:${userId}:${churchId}`;
}

/** Where a draft that could not be restored is copied (one slot, overwritten). */
export function corruptDraftKey(userId: string, churchId: string): string {
  return `wsb:draft-corrupt:${userId}:${churchId}`;
}
