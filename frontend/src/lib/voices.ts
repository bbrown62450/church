/**
 * Which Gospel passage the Voices of the Church panel shows on step 1 (Voices V1 spec "Which
 * Gospel passage"; owner's planning answer 1, 2026-10-05): a bulletin reading from a Gospel wins
 * (the picked or automatic New Testament reading, then the Old Testament one); else the Sunday's
 * lectionary Gospel, from the set the draft uses (or the default set), labeled as such; else none.
 * A canticle from Luke in the set's psalm slot (the Magnificat, Luke 1:46b-55; the Benedictus,
 * Luke 1:68-79; the Nunc dimittis, Luke 2:29-32) is sung, not read as the Gospel: it never counts,
 * picked or automatic (Voices V1 build review I1; Advent 4, Year B, December 20, 2026).
 * Pure: the lectionary answer is the one step 1 already holds.
 */
import type { Lectionary } from "@/lib/api/types";
import { cleanScriptures, effectivePicks, selectedSetIndex } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { scriptureKey, splitAlternatives, splitBook } from "@/lib/scripture-refs";

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

function fromLine(line: string | null, fromLectionary: boolean, canticles: ReadonlySet<string>): VoicesPassage | null {
  if (!line || gospelOf(line) === null || canticles.has(scriptureKey(line))) return null;
  return { reference: splitAlternatives(line)[0], line, fromLectionary };
}

/**
 * The index of a set's Gospel line: the last line from a Gospel, since a set's lines run first
 * reading, psalm, second reading, Gospel. Searching from the start would find a canticle from Luke
 * in the psalm slot first.
 */
function gospelIndex(scriptures: readonly string[]): number {
  for (let i = scriptures.length - 1; i >= 0; i--) if (gospelOf(scriptures[i]) !== null) return i;
  return -1;
}

/**
 * The keys of a set's canticles: its lines from a Gospel before its Gospel line. The first and
 * second readings never come from a Gospel, so such a line is in the psalm slot.
 */
function canticleKeys(scriptures: readonly string[]): ReadonlySet<string> {
  const gospel = gospelIndex(scriptures);
  const gospelKey = gospel < 0 ? "" : scriptureKey(scriptures[gospel]);
  return new Set(
    scriptures
      .slice(0, Math.max(gospel, 0))
      .filter((line) => gospelOf(line) !== null)
      .map(scriptureKey)
      .filter((key) => key !== gospelKey),
  );
}

export function voicesPassage(d: DraftV1, lect: Lectionary | undefined): VoicesPassage | null {
  const usable = lect !== undefined && lect.status === "ok" && lect.date === d.readings.date_iso;
  const index = usable ? (selectedSetIndex(d, lect) ?? lect.default_index) : null;
  const scriptures = (index === null ? undefined : lect?.reading_sets[index])?.scriptures ?? [];
  // Lines filled from a set are that set's lines, so their canticles are known before the lookup
  // answers (the page asks nothing for the Magnificat while the lectionary loads).
  const filled = d.readings.fields_origin === "lectionary" ? cleanScriptures(d) : [];
  const canticles = new Set([...canticleKeys(scriptures), ...canticleKeys(filled)]);
  const picks = effectivePicks(d);
  const chosen = fromLine(picks.nt, false, canticles) ?? fromLine(picks.ot, false, canticles);
  if (chosen) return chosen;
  const gospel = gospelIndex(scriptures);
  return gospel < 0 ? null : fromLine(scriptures[gospel], true, new Set());
}
