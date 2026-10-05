/**
 * The `POST /documents` body (slice 5a spec, `useDownloadDocument`; F §4.6
 * "Draft → API payload"). Pure.
 *
 * The service is `draftToServicePayload(draft)` (the mapping the save shares,
 * `serviceBody`, 5a-3), kept within the `ServiceDraft` limits so a draft
 * never meets a 422: the occasion and readings as every liturgy request sends
 * them (trimmed; the first 20 readings, each cut to 200; `request.ts`), the
 * two bulletin picks trimmed and cut to 200 as well, the hymns as `HymnRef`s (an id that is not a UUID goes as null, so the pick's own
 * title prints), each text cut to its limit (`liturgy_config.LIMITS`), custom
 * elements without a label left out (the Word file never printed them; a
 * label is blank as the server reads it, `wordSafe`) and each place read as
 * `normalizePlacement` does on the Liturgy step, and the Bulletin step's
 * fields (printed bulletin PR 2b) always, each text cut to its limit, with
 * the cover picture's id or null (PR 3b: a body that says nothing would keep
 * the saved picture and print PR 1's box).
 */
import type { components } from "@/lib/api/schema";
import type { ServiceBulletin } from "@/lib/api/types";
import { emptyServiceBulletin, MAX_LENGTH as BULLETIN_MAX } from "@/lib/draft/bulletin";
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload } from "@/lib/draft/mapping";
import { CARRY_KEYS, SLOTS, type DraftV1, type Slot } from "@/lib/draft/schema";
import type { DocumentVariant, PrintedFormat } from "@/lib/download";
import { clipChars, MAX_REF_LENGTH } from "@/lib/hymns/match-request";
import { normalizePlacement } from "@/lib/liturgy/cards";
import { hymnRef, MAX_CARD_TEXT, MAX_HYMNAL, readingsContext } from "@/lib/liturgy/request";

export type DocumentBody = components["schemas"]["DocumentIn"];
export type PrintedBody = components["schemas"]["PrintedDocumentIn"];
type Placement = components["schemas"]["CustomElementIn"]["insert_after"];

/** liturgy_config.LIMITS (slice 4a), the server's ServiceDraft limits. */
export const MAX_SERMON_TITLE = 300;
export const MAX_CUSTOM_ELEMENTS = 30;
export const MAX_CUSTOM_LABEL = 200;
export const MAX_CUSTOM_TEXT = 10_000;

/**
 * The server's `usecases.archive._xml_safe`: a Windows or old-Mac line ending,
 * a vertical tab or a form feed becomes a line break, and the other characters
 * a Word file cannot hold (C0 controls but tab, newline and carriage return;
 * U+FFFE, U+FFFF; lone surrogates) go. The blank-label filter reads labels
 * through it, so a label of only such characters is left out here instead of
 * meeting the server's 422 (5a-1 build review fix 8).
 */
export function wordSafe(text: string): string {
  return text
    .replace(/\r\n?/g, "\n")
    .replace(/[\v\f]/g, "\n")
    .replace(/[\x00-\x08\x0e-\x1f\ufffe\uffff]|[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/g, "");
}

/** The bulletin fields within the server's limits (`service_bulletin.MAX_LENGTH`). */
function clipBulletin(b: ServiceBulletin): ServiceBulletin {
  const person = (name: string | null) => (name === null ? null : clipChars(name, BULLETIN_MAX.person));
  return {
    prelude: { title: clipChars(b.prelude.title, BULLETIN_MAX.title), composer: clipChars(b.prelude.composer, BULLETIN_MAX.composer) },
    postlude: { title: clipChars(b.postlude.title, BULLETIN_MAX.title), composer: clipChars(b.postlude.composer, BULLETIN_MAX.composer) },
    people: { worship_leader: person(b.people.worship_leader), liturgist: person(b.people.liturgist), organist: person(b.people.organist) },
    leaders: Object.fromEntries(Object.entries(b.leaders).map(([key, name]) => [key, clipChars(name, BULLETIN_MAX.person)])),
    announcements: {
      ushers: clipChars(b.announcements.ushers, BULLETIN_MAX.ushers),
      deacon: clipChars(b.announcements.deacon, BULLETIN_MAX.deacon),
      coffee_hour: clipChars(b.announcements.coffee_hour, BULLETIN_MAX.coffee_hour),
      activities: clipChars(b.announcements.activities, BULLETIN_MAX.activities),
      prayer_concerns: clipChars(b.announcements.prayer_concerns, BULLETIN_MAX.prayer_concerns),
      collection: clipChars(b.announcements.collection, BULLETIN_MAX.collection),
      other: clipChars(b.announcements.other, BULLETIN_MAX.other),
    },
    reading_text: { ot: clipChars(b.reading_text.ot, BULLETIN_MAX.reading_text), nt: clipChars(b.reading_text.nt, BULLETIN_MAX.reading_text) },
    unchecked: [...b.unchecked],
    cover_image_id: b.cover_image_id ?? null,
  };
}

/** `service_bulletin.read`'s one-line fields: each run of control characters (and the spaces around it) is one space. */
const NOT_ONE_LINE_RUN = / *[\x00-\x1f\x7f-\x9f\u2028\u2029][\x00-\x1f\x7f-\x9f\u2028\u2029 ]*/g;
/** `service_bulletin.read`'s free texts: every line break is "\n" (U+2028 and U+2029 would print as "?"). */
const LINE_BREAK = /\r\n?|[\v\f\x85\u2028\u2029]/g;
/** `service_bulletin.read`'s pasted readings: a run of blank lines is one paragraph break. */
const BLANK_LINES = /\n(?:[ \t]*\n)+/g;

/** What a Word file cannot hold (`wordSafe`'s last rule): `service_bulletin.read` deletes it first (2b-1 build review M1). */
const WORD_BAD = /[\x00-\x08\x0e-\x1f\ufffe\uffff]|[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/g;
/** `service_bulletin.read`'s free texts: the C1 controls go once U+0085 is a line break (2b-1 build review M2). */
const C1 = /[\x7f-\x9f]/g;

const oneLine = (text: string) => text.replace(NOT_ONE_LINE_RUN, " ").replace(WORD_BAD, "");
const lines = (text: string) => text.replace(WORD_BAD, "").replace(LINE_BREAK, "\n").replace(C1, "");
const paragraphs = (text: string) => lines(text).replace(BLANK_LINES, "\n\n");

/** Blank as the server reads a label: nothing left after `wordSafe` and trimming. */
function isBlankLabel(label: string): boolean {
  return wordSafe(label).trim() === "";
}

/**
 * The service as `POST /documents` and `POST`/`PUT /services` send it (slice
 * 5a-3: the Save card sends the same body as the downloads, so a save never
 * meets a 422 for a length either, a stored custom element longer than
 * today's limits included). The bulletin is always sent (printed bulletin
 * PR 2b), so a save that clears every bulletin field clears the saved ones;
 * only a client from before 2b sends none (and a PUT then keeps them).
 */
export function serviceBody(draft: DraftV1): DocumentBody["service"] {
  const payload = draftToServicePayload(draft);
  const slots = draft.hymns.slots;
  return {
    ...payload,
    ...readingsContext(draft),
    selected_ot_ref: clipChars(payload.selected_ot_ref.trim(), MAX_REF_LENGTH),
    selected_nt_ref: clipChars(payload.selected_nt_ref.trim(), MAX_REF_LENGTH),
    hymns: { opening: hymnRef(slots.opening), response: hymnRef(slots.response), closing: hymnRef(slots.closing) },
    hymnal: payload.hymnal === null ? null : clipChars(payload.hymnal, MAX_HYMNAL),
    liturgy: Object.fromEntries(Object.entries(payload.liturgy).map(([key, text]) => [key, clipChars(text, MAX_CARD_TEXT)])),
    sermon_title: clipChars(payload.sermon_title.trim(), MAX_SERMON_TITLE),
    custom_elements: payload.custom_elements
      .filter((element) => !isBlankLabel(element.label))
      .slice(0, MAX_CUSTOM_ELEMENTS)
      .map((element) => ({
        label: clipChars(element.label.trim(), MAX_CUSTOM_LABEL),
        text: clipChars(element.text, MAX_CUSTOM_TEXT),
        insert_after: normalizePlacement(element.insert_after) as Placement,
      })),
    bulletin: clipBulletin(payload.bulletin ?? emptyServiceBulletin()),
  };
}

/** A service as the archive keeps it, for `savedCopyFingerprint`: a body sent (`serviceBody`) or a `ServiceOut` read back. */
export type SavedCopy = {
  service_date_iso: string | null;
  occasion: string;
  scriptures?: string[];
  hymns?: Partial<Record<Slot, { title: string } | null>>;
  hymnal?: string | null;
  liturgy?: { [key: string]: string };
  sermon_title: string;
  selected_ot_ref: string;
  selected_nt_ref: string;
  include_communion: boolean;
  custom_elements?: { label: string; text: string; insert_after: string }[];
  /** Printed bulletin PR 2b; missing reads as nothing filled in. */
  bulletin?: ServiceBulletin | null;
};

/** The server's `hymn_search.normalize_title`: NFKC, whitespace collapsed, trimmed, case-folded. */
function titleKey(title: string): string {
  return title.normalize("NFKC").replace(/\s+/g, " ").trim().toLowerCase();
}

/**
 * A fingerprint of `s` as the archive would store and read it back
 * (`usecases.archive.clean_input`, `resolve_hymn_refs`, `get_service`):
 * every string Word-safe and trimmed, blank scriptures and sections left
 * out, each place read as `normalizePlacement` does, and each hymn by its
 * normalized title alone (the server fills in the id, number and title of a
 * hymn sent without an id when the church has it). Save's "is the 409 my own
 * earlier save?" compares the body it sends with the archive's copy through
 * it, so a hymn resolved by title or a text the body already cut to its
 * limit never looks like someone else's change (5a-3 build review M2). The
 * bulletin fields count too (printed bulletin PR 2b): another device's
 * change to the announcements is someone else's change.
 * `withHymnal` false leaves the hymnal out: a body with none takes the
 * church's.
 */
export function savedCopyFingerprint(s: SavedCopy, { withHymnal = true }: { withHymnal?: boolean } = {}): string {
  const clean = (text: string) => wordSafe(text).trim();
  return fingerprint({
    service_date_iso: s.service_date_iso,
    occasion: clean(s.occasion),
    scriptures: (s.scriptures ?? []).map(clean).filter((line) => line !== ""),
    hymns: SLOTS.map((slot) => {
      const hymn = s.hymns?.[slot] ?? null;
      return hymn === null ? null : titleKey(wordSafe(hymn.title)) || null;
    }),
    hymnal: withHymnal ? clean(s.hymnal ?? "") || null : null,
    liturgy: Object.fromEntries(
      Object.entries(s.liturgy ?? {})
        .map(([key, text]) => [key, clean(text)])
        .filter(([, text]) => text !== ""),
    ),
    sermon_title: clean(s.sermon_title),
    selected_ot_ref: clean(s.selected_ot_ref),
    selected_nt_ref: clean(s.selected_nt_ref),
    include_communion: s.include_communion,
    custom_elements: (s.custom_elements ?? []).map((element) => ({
      label: clean(element.label),
      text: clean(element.text),
      insert_after: normalizePlacement(element.insert_after),
    })),
    bulletin: savedBulletin(s.bulletin ?? emptyServiceBulletin(), clean),
  });
}

/**
 * A bulletin as the archive keeps it (`service_bulletin.read`, then Word-safe
 * and trimmed): what Word cannot hold deleted first, a one-line field's
 * control characters one space, a free text's line breaks "\n" and its
 * other controls deleted, a pasted reading's blank lines one paragraph
 * break, blank part leaders left out, the unchecked boxes in order (plan
 * review fix M3: a tab pasted into a title is not someone else's change;
 * 2b-1 build review M1, M2: a control character between blank lines or a C1
 * control is not either).
 */
function savedBulletin(b: ServiceBulletin, clean: (text: string) => string) {
  const line = (text: string) => clean(oneLine(text));
  const music = (m: ServiceBulletin["prelude"]) => ({ title: line(m.title), composer: line(m.composer) });
  const free = new Set<string>(["activities", "prayer_concerns", "collection", "other"]);
  return {
    prelude: music(b.prelude),
    postlude: music(b.postlude),
    people: Object.fromEntries(Object.entries(b.people).map(([role, name]) => [role, name === null ? null : line(name)])),
    leaders: Object.fromEntries(Object.entries(b.leaders).map(([key, name]) => [key, line(name)]).filter(([, name]) => name !== "")),
    announcements: Object.fromEntries(
      Object.entries(b.announcements).map(([key, text]) => [key, free.has(key) ? clean(lines(text)) : line(text)]),
    ),
    reading_text: { ot: clean(paragraphs(b.reading_text.ot)), nt: clean(paragraphs(b.reading_text.nt)) },
    unchecked: CARRY_KEYS.filter((key) => (b.unchecked ?? []).includes(key)),
    cover_image_id: b.cover_image_id ?? null,
  };
}

export function documentRequest(draft: DraftV1, variant: DocumentVariant): DocumentBody {
  return { variant, service: serviceBody(draft) };
}

/** The server's `PrintedDocumentIn.translation` limit. */
const MAX_TRANSLATION = 20;

/**
 * The `POST /documents/printed` body (printed bulletin spec, PR 1): the same
 * service, the format, and the draft's translation (null: the church's). The
 * server prints in it when it still offers it, else in the church's, as step
 * 1 shows the readings (`effectiveTranslation`).
 */
export function printedRequest(draft: DraftV1, format: PrintedFormat): PrintedBody {
  const translation = draft.readings.translation;
  return {
    format,
    translation: translation && translation.length <= MAX_TRANSLATION ? translation : null,
    service: serviceBody(draft),
  };
}
