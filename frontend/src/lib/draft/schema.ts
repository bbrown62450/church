/**
 * The per-church unsaved draft, version 1 (F §4.6; S "Draft store").
 *
 * This is F §4.6's `DraftV1` without the two fields slice 5a adds with its own
 * version bump (`save_key_fingerprint`, `editing.date_iso`). Strings are
 * bounded generously (20 000) so a stored draft is never rejected for
 * length; the UI limits live in the components. `readings.scriptures` holds
 * the raw lines, blanks included; `cleanLines()` derives everything else.
 */
import { z } from "zod";

import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";

export const DRAFT_VERSION = 1;

export const STEP_IDS = ["readings", "hymns", "liturgy", "review"] as const;
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

export const draftV1Schema = z.object({
  version: z.literal(DRAFT_VERSION),
  user_id: text,
  church_id: text,
  created_at: timestamp,
  updated_at: timestamp,
  last_step: z.enum(STEP_IDS),
  save_key: text,
  editing: z.object({ service_id: text, saved_at: text }).nullable(),
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
});

export type DraftV1 = z.infer<typeof draftV1Schema>;
export type DraftReadings = DraftV1["readings"];

/** The profile fields `freshDraft` needs (`GET /church`, slice 2a). */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean };

/** The church's zone for `todayIn`, or undefined (the browser's zone) when the profile says it is not valid. */
export function churchZone(church: DraftChurch): string | undefined {
  return church.timezone_valid === false ? undefined : (church.timezone ?? undefined);
}

/**
 * A fresh draft (F §4.6 "Fresh draft"): dated the next Sunday strictly after
 * today in the church's zone, every field empty, the cards enabled except the
 * Prayers of the People, the benediction card `default`-origin (slice 4 fills
 * its text), communion on for a first Sunday, a new save key, on step 1.
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
      { enabled: key !== "prayers_of_the_people", text: "", origin: key === "benediction" ? "default" : "empty" },
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
