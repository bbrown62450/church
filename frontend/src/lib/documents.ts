/**
 * The `POST /documents` body (slice 5a spec, `useDownloadDocument`; F §4.6
 * "Draft → API payload"). Pure.
 *
 * The service is `draftToServicePayload(draft)` (the provisional mapping the
 * save will share, 5a-3), kept within the `ServiceDraft` limits so a draft
 * never meets a 422: the occasion and readings as every liturgy request sends
 * them (trimmed; the first 20 readings, each cut to 200; `request.ts`), the
 * two bulletin picks trimmed and cut to 200 as well, the hymns as `HymnRef`s (an id that is not a UUID goes as null, so the pick's own
 * title prints), each text cut to its limit (`liturgy_config.LIMITS`), custom
 * elements without a label left out (the Word file never printed them; a
 * label is blank as the server reads it, `wordSafe`) and each place read as
 * `normalizePlacement` does on the Liturgy step.
 */
import type { components } from "@/lib/api/schema";
import { draftToServicePayload } from "@/lib/draft/mapping";
import type { DraftV1 } from "@/lib/draft/schema";
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

export function documentRequest(draft: DraftV1, variant: DocumentVariant): DocumentBody {
  const payload = draftToServicePayload(draft);
  const slots = draft.hymns.slots;
  return {
    variant,
    service: {
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
    },
  };
}
