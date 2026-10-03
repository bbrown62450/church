/**
 * Draft ↔ saved service (slice 5a spec, Frontend "mapping.ts"; F §4.6 "Draft
 * → API payload" and "Loading an archived service").
 *
 * - `draftToServicePayload(draft)`: the service as the draft holds it, in the
 *   `ServiceDraft` shape, from the draft alone (so a church setting never
 *   makes a draft look unsaved). The fingerprint behind "Unsaved changes"
 *   hashes it. Text is trimmed as the server trims it; the picks are
 *   `resolveReadings`' explicit values, so a pick that is no longer an option
 *   goes as "". The bodies sent to the server (`serviceBody`, `documents.ts`)
 *   start from it and keep it within the server's limits.
 * - `serviceToDraft(service, …)`: a saved service as a new draft, already
 *   "Saved" (its fingerprint stored), on Review, with a new `created_at`.
 * - `markSaved(draft, service, fp)`: the draft after a save (owner answer 4).
 *
 * Printed bulletin PR 2b: the payload holds the Bulletin step's fields as
 * `bulletin` (`bulletinPayload`) only when something is filled in, so a
 * draft saved before PR 2b keeps its fingerprint and stays "Saved" after the
 * draft v3 migration; the bodies sent always carry it (`serviceBody`).
 */
import type { ArchivedHymn, ServiceBulletin, ServiceOut } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { normalizePlacement } from "@/lib/liturgy/cards";
import { cleanLines } from "@/lib/scripture-refs";

import { bulletinFromService, bulletinPayload, emptyServiceBulletin, isBlankBulletin } from "./bulletin";
import { fingerprint } from "./fingerprint";
import { effectivePicks } from "./readings";
import {
  freshDraft,
  SECTION_KEYS,
  SLOTS,
  type DraftChurch,
  type DraftV1,
  type HymnPick,
  type LiturgyCard,
  type SectionKey,
  type Slot,
} from "./schema";

/** Inventory §2.1's `HymnRef`. */
export type HymnRefPayload = { hymn_id: string | null; title: string; number: number | null; hymnal: string | null };

/** The API's `ServiceDraft` (inventory §2.1 plus `hymnal`, F §1.3), every field present. */
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
  /** The Bulletin step's fields (printed bulletin PR 2b); left out when nothing is filled in. */
  bulletin?: ServiceBulletin;
};

function hymnRef(pick: HymnPick | null): HymnRefPayload | null {
  return pick ? { hymn_id: pick.hymn_id, title: pick.title, number: pick.number, hymnal: pick.hymnal } : null;
}

/**
 * The draft as a `ServiceDraft` (S "mapping.ts"): the date; the occasion
 * trimmed; the scripture lines trimmed with blanks dropped; the explicit
 * picks; the slot hymns; `hymnal` as the draft holds it (null = the church's
 * effective hymnal, filled in by the server); the switched-on cards with
 * text, trimmed; the sermon title trimmed; communion; the custom elements
 * with a label, trimmed, without their ids; the bulletin fields when any is
 * filled in (PR 2b).
 */
export function draftToServicePayload(draft: DraftV1): ServiceDraftPayload {
  const picks = effectivePicks(draft);
  const bulletin = bulletinPayload(draft);
  const liturgy: Partial<Record<SectionKey, string>> = {};
  for (const key of SECTION_KEYS) {
    const card = draft.liturgy.cards[key];
    const text = card.text.trim();
    if (card.enabled && text !== "") liturgy[key] = text;
  }
  return {
    service_date_iso: draft.readings.date_iso,
    occasion: draft.readings.occasion.trim(),
    scriptures: cleanLines(draft.readings.scriptures),
    hymns: Object.fromEntries(SLOTS.map((slot) => [slot, hymnRef(draft.hymns.slots[slot])])) as Record<
      Slot,
      HymnRefPayload | null
    >,
    liturgy,
    sermon_title: draft.liturgy.sermon_title.trim(),
    selected_ot_ref: picks.otAuto ? "" : (picks.ot ?? ""),
    selected_nt_ref: picks.ntAuto ? "" : (picks.nt ?? ""),
    include_communion: draft.liturgy.include_communion,
    custom_elements: draft.liturgy.custom_elements
      .filter((element) => element.label.trim() !== "")
      .map(({ label, text, insert_after }) => ({ label: label.trim(), text: text.trim(), insert_after })),
    hymnal: draft.hymns.hymnal,
    ...(isBlankBulletin(bulletin) ? {} : { bulletin }),
  };
}

/** A saved slot as a pick: a hymn that is no longer in the hymnal keeps its title with no id ("Not in your hymnal"). */
function pickFromArchived(hymn: ArchivedHymn | null): HymnPick | null {
  if (hymn === null) return null;
  return { hymn_id: hymn.in_hymnal ? hymn.hymn_id : null, title: hymn.title, number: hymn.number, hymnal: hymn.hymnal };
}

/**
 * A saved service as the new draft (S `serviceToDraft`; F §4.6 "Loading an
 * archived service"): the readings from the service (`fields_origin`
 * "archive", so the lectionary never fills over them; no reading set; the
 * church's translation), dated as saved (`date_origin` "archive"), or, for an
 * undated service, the next Sunday (`date_origin` "default"); the slot hymns
 * and the hymnal as saved; each saved section switched on with its text
 * (origin "archive") and the others off and empty (no church Benediction
 * added); the sermon title; communion as saved (origin "archive"); the custom
 * elements with new ids and their places read as the Liturgy step reads
 * them; the bulletin fields as saved, with nothing to check and no carry
 * (PR 2b). `editing` names the service, its `saved_at` and its date; the
 * fingerprint of this draft is stored, so it opens "Saved"; a new save key;
 * a new `created_at` (the reviewer's notes and any AI run belong to the
 * draft it replaces); on Review.
 */
export function serviceToDraft(
  service: ServiceOut,
  { church, user, now = new Date() }: { church: DraftChurch; user: { id: string }; now?: Date },
): DraftV1 {
  const fresh = freshDraft({ church, user, now });
  const date = service.service_date_iso !== null && isValidDateIso(service.service_date_iso) ? service.service_date_iso : null;
  const cards = Object.fromEntries(
    SECTION_KEYS.map((key): [SectionKey, LiturgyCard] => {
      const text = service.liturgy[key] ?? "";
      return [key, text.trim() === "" ? { enabled: false, text: "", origin: "empty" } : { enabled: true, text, origin: "archive" }];
    }),
  ) as Record<SectionKey, LiturgyCard>;
  const draft: DraftV1 = {
    ...fresh,
    last_step: "review",
    editing: { service_id: service.id, saved_at: service.saved_at, date_iso: date },
    readings: {
      date_iso: date ?? fresh.readings.date_iso,
      date_origin: date === null ? "default" : "archive",
      reading_set: null,
      fields_origin: "archive",
      occasion: service.occasion,
      scriptures: [...service.scriptures],
      selected_ot_ref: service.selected_ot_ref,
      selected_nt_ref: service.selected_nt_ref,
      translation: null,
    },
    hymns: {
      hymnal: service.hymnal ?? null,
      exclude_recent: true,
      slots: {
        opening: pickFromArchived(service.hymns.opening),
        response: pickFromArchived(service.hymns.response),
        closing: pickFromArchived(service.hymns.closing),
      },
      alternatives: null,
    },
    liturgy: {
      sermon_title: service.sermon_title,
      include_communion: service.include_communion,
      communion_origin: "archive",
      cards,
      custom_elements: service.custom_elements.map((element) => ({
        id: crypto.randomUUID(),
        label: element.label,
        text: element.text,
        insert_after: normalizePlacement(element.insert_after),
      })),
    },
    // A server from before PR 2b-1 (only if it were reverted) sends none.
    bulletin: bulletinFromService(service.bulletin ?? emptyServiceBulletin(), service),
  };
  return { ...draft, saved_fingerprint: fingerprint(draftToServicePayload(draft)) };
}

/**
 * The draft after a save: `editing` names the saved service (its id,
 * `saved_at` and date), `saved_fingerprint` is the payload that was sent, and
 * what followed a default is now the service's own, as when a saved service
 * is opened (owner answer 4): a Benediction following the church default
 * keeps its text with origin "archive" ("empty" when it is blank), and
 * communion following the first-Sunday rule keeps its setting with origin
 * "archive". Neither changes the payload, so the draft is "Saved".
 */
export function markSaved(d: DraftV1, service: ServiceOut, fp: string): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
  const cards =
    benediction.origin === "default"
      ? { ...d.liturgy.cards, benediction: { ...benediction, origin: benediction.text.trim() === "" ? ("empty" as const) : ("archive" as const) } }
      : d.liturgy.cards;
  const communion_origin = d.liturgy.communion_origin === "default" ? "archive" : d.liturgy.communion_origin;
  return {
    ...d,
    editing: { service_id: service.id, saved_at: service.saved_at, date_iso: service.service_date_iso },
    saved_fingerprint: fp,
    liturgy: { ...d.liturgy, cards, communion_origin },
    // Saved: what "Save as new service" set aside belongs to the other service (PR 2b-2).
    bulletin: { ...d.bulletin, set_aside: null },
  };
}
