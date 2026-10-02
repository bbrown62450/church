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
 * `normalizePlacement` does on the Liturgy step.
 */
import type { components } from "@/lib/api/schema";
import { fingerprint } from "@/lib/draft/fingerprint";
import { draftToServicePayload } from "@/lib/draft/mapping";
import { SLOTS, type DraftV1, type Slot } from "@/lib/draft/schema";
import type { DocumentVariant } from "@/lib/download";
import { clipChars, MAX_REF_LENGTH } from "@/lib/hymns/match-request";
import { normalizePlacement } from "@/lib/liturgy/cards";
import { hymnRef, MAX_CARD_TEXT, MAX_HYMNAL, readingsContext } from "@/lib/liturgy/request";

export type DocumentBody = components["schemas"]["DocumentIn"];
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

/** Blank as the server reads a label: nothing left after `wordSafe` and trimming. */
function isBlankLabel(label: string): boolean {
  return wordSafe(label).trim() === "";
}

/**
 * The service as `POST /documents` and `POST`/`PUT /services` send it (slice
 * 5a-3: the Save card sends the same body as the downloads, so a save never
 * meets a 422 for a length either, a stored custom element longer than
 * today's limits included).
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
 * limit never looks like someone else's change (5a-3 build review M2).
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
  });
}

export function documentRequest(draft: DraftV1, variant: DocumentVariant): DocumentBody {
  return { variant, service: serviceBody(draft) };
}
