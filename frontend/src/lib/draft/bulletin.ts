/**
 * The Bulletin step's weekly fields in the draft (printed bulletin PR 2b;
 * spec "Data model", "The Bulletin step"): the prelude and postlude, this
 * week's people and part leaders, the announcements and the pasted reading
 * text. Pure.
 *
 * - Edits (`setMusic`, `setAnnouncement`, `setPerson`, `setPartLeader`,
 *   `setPastedText`, `keepCarried`). A box holding last week's text shows
 *   "From last week. Check before printing." until it is edited (its text
 *   changed in any way, cleared included) or kept as it is ("Keep as is").
 * - Carry forward (PR 2 planning answer 5): `shouldCarry` and `applyCarry`.
 *   A draft that is not a saved service (`editing` null), with a real date
 *   and no save whose outcome is still unknown (`save_key_fingerprint` null:
 *   a carry would change the body and so the save key, plan review fix I2),
 *   takes the music and the announcements of the church's latest service
 *   dated before its date (`GET /services/previous-bulletin`) into every box
 *   not yet typed in, edited, cleared or kept (`edited`, a box at a time),
 *   once per date (`carried_for`); a new date carries again into those
 *   boxes. The people, the part leaders and the pasted texts never carry.
 *   Opening a saved service never carries.
 * - "Save as new service" (`followSaveMode`, plan review fix I4): a saved
 *   service whose date now differs from the saved one is treated as a new
 *   week: every filled music and announcement box is marked "From last
 *   week", and this week's people, the part leaders and the pasted texts
 *   start empty (set aside, and put back if the date goes back to the
 *   saved one, even while a save's outcome is unknown).
 * - `bulletinPayload`: the draft's bulletin as `ServiceDraft.bulletin`, the
 *   texts trimmed, the pasted texts of the readings the files print, and
 *   the boxes still to check (`unchecked`, so the marks are saved with the
 *   service, plan review fix I3).
 * - `bulletinFromService`: a saved service's bulletin as the draft's, its
 *   unchecked boxes marked again.
 * - What the Printed bulletin card and the step bar say: `printedNotFilledIn`,
 *   `notChecked`, `bulletinStatus`.
 */
import type { BulletinSettings, PreviousBulletin, ServiceBulletin } from "@/lib/api/types";
import { ELEMENTS, notFilledIn } from "@/lib/bulletin-settings";
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { resolveReadings } from "@/lib/scripture-refs";

import { effectivePicks } from "./readings";
import {
  ANNOUNCEMENT_KEYS,
  CARRY_KEYS,
  PEOPLE,
  type AnnouncementKey,
  type CarryKey,
  type DraftBulletin,
  type DraftV1,
  type Person,
} from "./schema";

/** `service_bulletin.MAX_LENGTH`: the server refuses a longer text (422); `serviceBody` cuts to them. */
export const MAX_LENGTH = {
  title: 200,
  composer: 100,
  person: 100,
  ushers: 200,
  deacon: 100,
  coffee_hour: 200,
  activities: 4000,
  prayer_concerns: 4000,
  collection: 2000,
  other: 4000,
  reading_text: 10_000,
} as const;

export type Piece = "prelude" | "postlude";

function withBulletin(d: DraftV1, next: DraftBulletin): DraftV1 {
  return { ...d, bulletin: next };
}

/** The box `key` edited or kept: no longer to check, and last week's never carries into it again. */
function touched(b: DraftBulletin, key: CarryKey): Pick<DraftBulletin, "carried" | "edited"> {
  return {
    carried: b.carried.filter((k) => k !== key),
    edited: b.edited.includes(key) ? b.edited : CARRY_KEYS.filter((k) => k === key || b.edited.includes(k)),
  };
}

export function setMusic(d: DraftV1, piece: Piece, field: "title" | "composer", value: string): DraftV1 {
  const b = d.bulletin;
  if (b[piece][field] === value) return d;
  return withBulletin(d, { ...b, [piece]: { ...b[piece], [field]: value }, ...touched(b, piece) });
}

export function setAnnouncement(d: DraftV1, key: AnnouncementKey, value: string): DraftV1 {
  const b = d.bulletin;
  if (b.announcements[key] === value) return d;
  return withBulletin(d, { ...b, announcements: { ...b.announcements, [key]: value }, ...touched(b, key) });
}

/** "Keep as is": last week's text stays, and the box no longer asks to be checked. */
export function keepCarried(d: DraftV1, key: CarryKey): DraftV1 {
  const b = d.bulletin;
  return b.carried.includes(key) ? withBulletin(d, { ...b, ...touched(b, key) }) : d;
}

/** This week's name for a person: null follows the bulletin settings, "" is no one this week. */
export function setPerson(d: DraftV1, person: Person, value: string | null): DraftV1 {
  const b = d.bulletin;
  if (b.people[person] === value) return d;
  return withBulletin(d, { ...b, people: { ...b.people, [person]: value } });
}

/** A part's leader this week; a blank one follows the part's standing leader. */
export function setPartLeader(d: DraftV1, key: string, value: string): DraftV1 {
  const b = d.bulletin;
  if ((b.leaders[key] ?? "") === value) return d;
  const leaders = { ...b.leaders };
  if (value === "") delete leaders[key];
  else leaders[key] = value;
  return withBulletin(d, { ...b, leaders });
}

/** The pasted text of the reading `reference` (kept by reference: a changed reading starts with an empty box). */
export function setPastedText(d: DraftV1, reference: string, value: string): DraftV1 {
  const b = d.bulletin;
  if ((b.pasted[reference] ?? "") === value) return d;
  const pasted = { ...b.pasted };
  if (value === "") delete pasted[reference];
  else pasted[reference] = value;
  return withBulletin(d, { ...b, pasted });
}

function filled(b: Pick<DraftBulletin, Piece | "announcements">, key: CarryKey): boolean {
  if (key === "prelude" || key === "postlude") return b[key].title.trim() !== "" || b[key].composer.trim() !== "";
  return b.announcements[key].trim() !== "";
}

/** Last week's bulletin should be looked up and carried in now (see the module comment). */
export function shouldCarry(d: DraftV1): boolean {
  const date = d.readings.date_iso;
  return (
    d.editing === null &&
    d.save_key_fingerprint === null &&
    isValidDateIso(date) &&
    inSupportedRange(date) &&
    d.bulletin.carried_for !== date &&
    d.bulletin.edited.length < CARRY_KEYS.length
  );
}

/**
 * Last week's music and announcements in every box not yet edited or kept,
 * each filled one marked "From last week", for `forDate`; the draft
 * unchanged when carrying is no longer due or the date moved meanwhile.
 */
export function applyCarry(d: DraftV1, previous: PreviousBulletin, forDate: string): DraftV1 {
  if (d.readings.date_iso !== forDate || !shouldCarry(d)) return d;
  const b = d.bulletin;
  const p = previous.bulletin;
  const open = (key: CarryKey) => !b.edited.includes(key);
  const next: DraftBulletin = {
    ...b,
    prelude: open("prelude") ? { ...p.prelude } : b.prelude,
    postlude: open("postlude") ? { ...p.postlude } : b.postlude,
    announcements: Object.fromEntries(
      ANNOUNCEMENT_KEYS.map((key) => [key, open(key) ? p.announcements[key] : b.announcements[key]]),
    ) as DraftBulletin["announcements"],
    carried_for: forDate,
  };
  return withBulletin(d, { ...next, carried: CARRY_KEYS.filter((key) => open(key) && filled(next, key)) });
}

const NO_ONE_CHANGED: DraftBulletin["people"] = { worship_leader: null, liturgist: null, organist: null };

/**
 * "Save as new service" (plan review fix I4): a saved service whose date
 * now differs from its saved date is a new week. Its people, part leaders,
 * pasted texts and marks are set aside, this week's start empty, and every
 * filled music and announcement box is marked "From last week. Check before
 * printing.". Back on the saved date, what was set aside returns: a name or
 * text typed meanwhile wins, and a saved mark returns only on a box not
 * edited or kept meanwhile. Nothing is set aside while a save's outcome
 * is unknown (`save_key_fingerprint`: it would change the body of the POST
 * that may be retried), but what was set aside always returns on the saved
 * date, a pending key included: the next save there is a PUT of the saved
 * service, which uses no key, and without them it would blank the saved
 * people, leaders and texts (2b-2 build review C1). An undated saved
 * service (from before dates were kept) is never set aside: its date was
 * not changed, only filled in (2b-2 build review M5). The draft unchanged
 * when nothing is due.
 */
export function followSaveMode(d: DraftV1): DraftV1 {
  const editing = d.editing;
  const date = d.readings.date_iso;
  const b = d.bulletin;
  if (editing === null) return d;
  if (
    d.save_key_fingerprint === null &&
    editing.date_iso !== null &&
    date !== editing.date_iso &&
    isValidDateIso(date) &&
    b.set_aside === null
  ) {
    return withBulletin(d, {
      ...b,
      people: NO_ONE_CHANGED,
      leaders: {},
      pasted: {},
      carried: CARRY_KEYS.filter((key) => filled(b, key)),
      edited: [],
      set_aside: { people: b.people, leaders: b.leaders, pasted: b.pasted, carried: b.carried, edited: b.edited },
    });
  }
  if (date === editing.date_iso && b.set_aside !== null) {
    const aside = b.set_aside;
    return withBulletin(d, {
      ...b,
      people: Object.fromEntries(PEOPLE.map((p) => [p, b.people[p] ?? aside.people[p]])) as DraftBulletin["people"],
      leaders: { ...aside.leaders, ...b.leaders },
      pasted: { ...aside.pasted, ...b.pasted },
      carried: aside.carried.filter((key) => b.carried.includes(key)),
      edited: CARRY_KEYS.filter((key) => aside.edited.includes(key) || b.edited.includes(key)),
      set_aside: null,
    });
  }
  return d;
}

/** `ServiceDraft.bulletin` with nothing filled in. */
export function emptyServiceBulletin(): ServiceBulletin {
  return {
    prelude: { title: "", composer: "" },
    postlude: { title: "", composer: "" },
    people: { worship_leader: null, liturgist: null, organist: null },
    leaders: {},
    announcements: { ushers: "", deacon: "", coffee_hour: "", activities: "", prayer_concerns: "", collection: "", other: "" },
    reading_text: { ot: "", nt: "" },
    unchecked: [],
  };
}

/**
 * The draft's bulletin as `ServiceDraft.bulletin`: every text trimmed; the
 * people as set (null: the settings' name); the part leaders with a name, in
 * the printed order; the pasted texts of the two readings the files print
 * (`effectivePicks`), so a text pasted for a reading no longer chosen is not
 * sent; the boxes still to check, in the step's order.
 */
export function bulletinPayload(d: DraftV1): ServiceBulletin {
  const b = d.bulletin;
  const picks = effectivePicks(d);
  const pasted = (ref: string | null) => (ref === null ? "" : (b.pasted[ref] ?? "").trim());
  return {
    prelude: { title: b.prelude.title.trim(), composer: b.prelude.composer.trim() },
    postlude: { title: b.postlude.title.trim(), composer: b.postlude.composer.trim() },
    people: Object.fromEntries(PEOPLE.map((p) => [p, b.people[p]?.trim() ?? null])) as ServiceBulletin["people"],
    leaders: Object.fromEntries(
      ELEMENTS.map(({ key }) => [key, (b.leaders[key] ?? "").trim()]).filter(([, name]) => name !== ""),
    ),
    announcements: Object.fromEntries(
      ANNOUNCEMENT_KEYS.map((key) => [key, b.announcements[key].trim()]),
    ) as ServiceBulletin["announcements"],
    reading_text: { ot: pasted(picks.ot), nt: pasted(picks.nt) },
    unchecked: CARRY_KEYS.filter((key) => b.carried.includes(key)),
  };
}

/** Nothing filled in: what a service saved without a bulletin reads as. */
export function isBlankBulletin(p: ServiceBulletin): boolean {
  return JSON.stringify(p) === JSON.stringify(emptyServiceBulletin());
}

/**
 * A saved service's bulletin as the draft's (`serviceToDraft`): the boxes
 * saved as not checked yet marked "From last week" again (plan review fix
 * I3), no carry (a saved service never carries); each pasted text kept
 * under the reference of the reading it was saved for.
 */
export function bulletinFromService(
  saved: ServiceBulletin,
  readings: { scriptures: readonly string[]; selected_ot_ref: string; selected_nt_ref: string },
): DraftBulletin {
  const picks = resolveReadings(readings.scriptures, readings.selected_ot_ref, readings.selected_nt_ref);
  const pasted: Record<string, string> = {};
  if (picks.ot !== null && saved.reading_text.ot !== "") pasted[picks.ot] = saved.reading_text.ot;
  if (picks.nt !== null && saved.reading_text.nt !== "") pasted[picks.nt] = saved.reading_text.nt;
  return {
    prelude: { ...saved.prelude },
    postlude: { ...saved.postlude },
    people: { ...saved.people },
    leaders: { ...saved.leaders },
    announcements: { ...saved.announcements },
    pasted,
    carried: CARRY_KEYS.filter((key) => (saved.unchecked ?? []).includes(key)),
    edited: [],
    carried_for: null,
    set_aside: null,
  };
}

/** What "From last week, not checked yet: …" calls each box. */
const CARRY_LABELS: Record<CarryKey, string> = {
  prelude: "prelude",
  postlude: "postlude",
  ushers: "ushers and counters",
  deacon: "deacon of the week",
  coffee_hour: "coffee hour",
  activities: "activities",
  prayer_concerns: "prayers and concerns",
  collection: "collection items",
  other: "other announcements",
};

/** The boxes still holding last week's text, unchecked, by label, in the step's order. */
export function notChecked(d: DraftV1): string[] {
  return CARRY_KEYS.filter((key) => d.bulletin.carried.includes(key)).map((key) => CARRY_LABELS[key]);
}

/** "From last week, not checked yet: coffee hour, activities." */
export function notCheckedLine(labels: readonly string[]): string {
  return `From last week, not checked yet: ${labels.join(", ")}.`;
}

/**
 * What the printed bulletin leaves out this week (PR 2 planning answer 3), in
 * the card's "Not filled in" order: the standing fields from the settings,
 * the three people as this week has them (when the settings are loaded), then
 * the prelude, the postlude and the announcements (all of them blank).
 */
export function printedNotFilledIn(settings: BulletinSettings | undefined, d: DraftV1): string[] {
  const p = bulletinPayload(d);
  const standing =
    settings === undefined
      ? []
      : notFilledIn({ ...settings, ...Object.fromEntries(PEOPLE.map((r) => [r, p.people[r] ?? settings[r]])) });
  const weekly = [
    ...(filled(p, "prelude") ? [] : ["prelude"]),
    ...(filled(p, "postlude") ? [] : ["postlude"]),
    ...(ANNOUNCEMENT_KEYS.some((key) => filled(p, key)) ? [] : ["announcements"]),
  ];
  return [...standing, ...weekly];
}

/** The step bar's status for the optional Bulletin step: "Optional", or how many boxes from last week to check. */
export function bulletinStatus(d: DraftV1): { kind: "optional" } | { kind: "to_check"; count: number } {
  const count = d.bulletin.carried.length;
  return count === 0 ? { kind: "optional" } : { kind: "to_check", count };
}
