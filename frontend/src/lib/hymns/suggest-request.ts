/**
 * The `POST /hymns/suggestions` body (S `buildSuggestionRequest`). Pure: the
 * step passes a reader of the passage cache (`queryClient.getQueryData`), so
 * building a request never fetches a passage.
 */
import type { HymnSuggestionBody, Passage } from "@/lib/api/types";
import type { DraftV1 } from "@/lib/draft/schema";
import { passageText } from "@/lib/queries/passages";

import { cleanRefs, clipChars, MAX_REF_LENGTH, MAX_REFS } from "./match-request";

export const MAX_OCCASION = 300;
export const MAX_NT_TEXT = 20_000;

/** A hymn id as the server's `SlotPicks` accepts it (a UUID). */
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** A slot's id as an exclusion hint, or null when there is none or it is not UUID-shaped (a 422 Retry could not clear). */
function hintId(pick: DraftV1["hymns"]["slots"]["opening"]): string | null {
  const id = pick?.hymn_id ?? null;
  return id !== null && UUID.test(id) ? id : null;
}

/**
 * `nt_text` goes only when all hold: an NT reading was chosen in step 1, the
 * translation shown (`draft.readings.translation ?? churchTranslation`) is
 * not ESV (Crossway's terms), and that reading's text is already cached under
 * `["passage", translation, ref]` with `ref` exactly as stored. Every cut
 * counts characters as the server does (`clipChars`); `current_picks` sends
 * only UUID-shaped ids.
 */
export function buildSuggestionRequest(
  draft: DraftV1,
  selectedHymnal: string,
  getCachedPassage: (translation: string, ref: string) => Passage | undefined,
  churchTranslation: string,
): HymnSuggestionBody {
  const r = draft.readings;
  const ntRef = clipChars(r.selected_nt_ref.trim(), MAX_REF_LENGTH);
  const body: HymnSuggestionBody = {
    service_date_iso: r.date_iso,
    occasion: clipChars(r.occasion.trim(), MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
    selected_nt_ref: ntRef === "" ? null : ntRef,
    hymnal: selectedHymnal,
    exclude_recent: draft.hymns.exclude_recent,
    current_picks: {
      opening: hintId(draft.hymns.slots.opening),
      response: hintId(draft.hymns.slots.response),
      closing: hintId(draft.hymns.slots.closing),
    },
  };
  const translation = r.translation ?? churchTranslation;
  if (ntRef !== "" && translation !== "esv") {
    const cached = getCachedPassage(translation, r.selected_nt_ref);
    const text = cached ? passageText(cached) : null;
    if (text) body.nt_text = clipChars(text, MAX_NT_TEXT);
  }
  return body;
}
