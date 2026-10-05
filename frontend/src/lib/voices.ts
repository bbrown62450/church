/**
 * Which Gospel passage the Voices of the Church panel shows on step 1 (Voices V1 spec "Which
 * Gospel passage"; owner's planning answer 1, 2026-10-05): a bulletin reading from a Gospel wins
 * (the picked or automatic New Testament reading, then the Old Testament one); else the Sunday's
 * lectionary Gospel, from the set the draft uses (or the default set), labeled as such; else none.
 * Pure: the lectionary answer is the one step 1 already holds.
 */
import type { Lectionary } from "@/lib/api/types";
import { effectivePicks, selectedSetIndex } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { splitAlternatives, splitBook } from "@/lib/scripture-refs";

export const GOSPELS = ["Matthew", "Mark", "Luke", "John"] as const;
export type Gospel = (typeof GOSPELS)[number];

/** How long the panel trails the scripture lines: it asks once typing stops (Voices V1 review I3). */
export const VOICES_DELAY_MS = 600;

export type VoicesPassage = {
  /** The Gospel passage asked for (`GET /voices?reference=`): a line's first alternative. */
  reference: string;
  /** The scripture line it comes from: the panel sits under that line's row. */
  line: string;
  /** True when it is the Sunday's lectionary Gospel, not a bulletin reading ("From the Gospel for this Sunday"). */
  fromLectionary: boolean;
};

// One place in a book: "22", "22:15", "22:15-22", "26:14-27:66", "15:11b-32".
const ITEM = String.raw`\d+[a-d]?(?::\d+[a-d]?)?(?:-\d+[a-d]?(?::\d+[a-d]?)?)?`;
// The places of a reference after its book, parenthesized optional verses read as part of it
// ("2:(1-7) 8-20", "2:1-14 (15-20)"); never a half-typed "3:" or "3:16-".
const LOCATION = new RegExp(String.raw`^${ITEM}(?:(?:\s*,\s*|\s+)${ITEM})*$`);

/**
 * The Gospel a reference's first alternative is in, or null. It must name a chapter at least
 * and be complete ("John 3:16-21", "John 3"), so a whole book ("John") or a line half typed
 * ("John 3:") asks nothing.
 */
export function gospelOf(reference: string): Gospel | null {
  const first = splitAlternatives(reference)[0];
  const found = first ? splitBook(first) : null;
  if (!found) return null;
  const location = found.rest.replace(/[–—]/g, "-").replace(/[()]/g, "").replace(/\s+/g, " ").trim();
  if (!LOCATION.test(location)) return null;
  return GOSPELS.find((g) => g === found.book.name) ?? null;
}

function fromLine(line: string | null, fromLectionary: boolean): VoicesPassage | null {
  if (!line || gospelOf(line) === null) return null;
  return { reference: splitAlternatives(line)[0], line, fromLectionary };
}

export function voicesPassage(d: DraftV1, lect: Lectionary | undefined): VoicesPassage | null {
  const picks = effectivePicks(d);
  const chosen = fromLine(picks.nt, false) ?? fromLine(picks.ot, false);
  if (chosen) return chosen;
  if (!lect || lect.status !== "ok" || lect.date !== d.readings.date_iso) return null;
  const index = selectedSetIndex(d, lect) ?? lect.default_index;
  const set = index === null ? undefined : lect.reading_sets[index];
  for (const line of set?.scriptures ?? []) {
    const passage = fromLine(line, true);
    if (passage) return passage;
  }
  return null;
}
