/**
 * The hymn picker's search (S Picker "Ranking"): pure, over one hymnal's list.
 *
 * - All digits: the exact number first, then numbers that start with the
 *   digits, then titles containing them.
 * - Otherwise: titles that start with the words, then titles with a word that
 *   starts with them, then titles containing them. Accents, case and
 *   punctuation are ignored ("come thou" finds "Come, Thou Almighty King";
 *   clarification 12).
 * - Within each group, hymnal order. Blank titles are never listed. With
 *   `excludeRecent`, hymns with a recent use are left out and counted.
 */
import type { Hymn } from "@/lib/api/types";

/** F §4.9 item 5: a long list renders at most this many matches. */
export const PICKER_LIMIT = 50;

export type FilterResult = {
  /** At most PICKER_LIMIT matches, best first. */
  shown: Hymn[];
  /** Every match after the exclusion. */
  totalMatches: number;
  /** Matches left out because they were used within 12 weeks. */
  hiddenRecent: number;
};

/** Lower case, accents removed, anything but letters and digits as one space. */
export function foldText(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/\p{M}+/gu, "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim();
}

function rank(h: Hymn, q: string, digits: boolean): number {
  if (digits) {
    const number = h.number === null ? "" : String(h.number);
    if (number === q) return 0;
    if (number.startsWith(q)) return 1;
    return foldText(h.title).includes(q) ? 2 : -1;
  }
  const title = foldText(h.title);
  if (title.startsWith(q)) return 0;
  if (title.includes(` ${q}`)) return 1;
  return title.includes(q) ? 2 : -1;
}

export function filterHymns(items: readonly Hymn[], query: string, { excludeRecent }: { excludeRecent: boolean }): FilterResult {
  const trimmed = query.trim();
  const digits = /^[0-9]+$/.test(trimmed);
  const q = digits ? trimmed : foldText(trimmed);
  const groups: Hymn[][] = [[], [], []];
  let hiddenRecent = 0;
  for (const h of items) {
    if (h.title.trim() === "") continue;
    const group = q === "" ? 0 : rank(h, q, digits);
    if (group < 0) continue;
    if (excludeRecent && h.recent_use_on !== null) {
      hiddenRecent += 1;
      continue;
    }
    groups[group].push(h);
  }
  const matches = groups.flat();
  return { shown: matches.slice(0, PICKER_LIMIT), totalMatches: matches.length, hiddenRecent };
}
