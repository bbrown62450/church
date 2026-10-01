/**
 * The `POST /liturgy/generate` body (slice 4 spec, Frontend `request.ts`,
 * "Sermon text"; API §Schemas). Pure.
 *
 * - One section per request (the UI never batches sections into one call) and
 *   no `overrides`: typed cards are never sent at all.
 * - The occasion trimmed and cut to 300; the scriptures trimmed, blanks
 *   dropped, the first 20, each cut to 200 (the ServiceDraft limits); every
 *   cut counts characters as the server does (`clipChars`).
 * - `hymns`: the three slots as `HymnRef`s, each title cut to 300 and hymnal
 *   to 20. An id that is not a UUID (which the API would reject for the
 *   whole request) goes as `null`, so the pick's own title is used.
 * - `sermon_text`: the effective NT reading's passage, from `sermonSource`
 *   and the batch's one passage fetch (T6); left out when there is none.
 */
import type { ChurchProfile, GenerateLiturgyBody, HymnRef, Passage, SermonText, Translations } from "@/lib/api/types";
import { effectivePicks, effectiveTranslation } from "@/lib/draft/readings";
import type { DraftV1, HymnPick, SectionKey } from "@/lib/draft/schema";
import { cleanRefs, clipChars, MAX_REF_LENGTH, MAX_REFS } from "@/lib/hymns/match-request";
import { passageText } from "@/lib/queries/passages";

export const MAX_OCCASION = 300;
export const MAX_HYMN_TITLE = 300;
export const MAX_HYMNAL = 20;
export const MAX_SERMON_TEXT = 20_000;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function hymnRef(pick: HymnPick | null): HymnRef | null {
  if (pick === null) return null;
  const number = pick.number !== null && pick.number >= 0 && pick.number <= 100_000 ? pick.number : null;
  return {
    hymn_id: pick.hymn_id !== null && UUID.test(pick.hymn_id) ? pick.hymn_id : null,
    title: clipChars(pick.title, MAX_HYMN_TITLE),
    number,
    hymnal: pick.hymnal === null ? null : clipChars(pick.hymnal, MAX_HYMNAL),
  };
}

export function buildGenerateRequest(draft: DraftV1, section: SectionKey, sermon: SermonText | null): GenerateLiturgyBody {
  const r = draft.readings;
  const slots = draft.hymns.slots;
  const body: GenerateLiturgyBody = {
    occasion: clipChars(r.occasion.trim(), MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
    hymns: { opening: hymnRef(slots.opening), response: hymnRef(slots.response), closing: hymnRef(slots.closing) },
    sections: [section],
  };
  if (sermon !== null) body.sermon_text = sermon;
  return body;
}

/**
 * Which passage the sermon text is: the effective NT reading (the explicit
 * pick, else the automatic one; never a Psalm), in the translation step 1
 * shows (`effectiveTranslation`: the draft's when the server still offers it,
 * else the church's), with WEB instead of ESV (Crossway's terms: ESV text is
 * never sent to the AI). `ref` is the reading as the passage cache keys it.
 */
export function sermonSource(
  draft: DraftV1,
  church: Pick<ChurchProfile, "effective_translation">,
  translations: Translations | undefined,
): { ref: string; translation: string } | null {
  const nt = effectivePicks(draft).nt;
  if (nt === null || clipChars(nt.trim(), MAX_REF_LENGTH) === "") return null;
  const translation = effectiveTranslation(draft, church, translations);
  return { ref: nt, translation: translation === "esv" ? "web" : translation };
}

/** `sermon_text` from a loaded passage: the reference cut to 200, the text to 20 000; null without text. */
export function sermonText(ref: string, passage: Passage | undefined): SermonText | null {
  const text = passage ? passageText(passage) : null;
  if (text === null) return null;
  return { ref: clipChars(ref.trim(), MAX_REF_LENGTH), text: clipChars(text, MAX_SERMON_TEXT) };
}
