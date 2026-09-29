/**
 * Scripture references: the book table, the OT/NT classifier, the bulletin
 * pickers and the one bulletin-reading rule (S "lib/scripture-refs.ts";
 * spec decision 9; F §5.3).
 *
 * A line-for-line port of `backend/scripture_refs.py` (everything above its
 * "Fetch only" line, plus the private normalization `scriptureKey` needs).
 * Both ports run `backend/tests/fixtures/shared/scripture_refs.json`, which is
 * authoritative: change a case there first, then both ports.
 */

export type Testament = "ot" | "psalm" | "nt";
export type Classification = Testament | "unknown";

/** A canonical book; aliases are stored normalized (`normalizeBookText`). */
export type Book = { name: string; testament: Testament; aliases: readonly string[] };

function book(name: string, testament: Testament, aliases: readonly string[] = []): Book {
  return { name, testament, aliases };
}

export const BOOKS: readonly Book[] = [
  // Old Testament
  book("Genesis", "ot", ["gen"]),
  book("Exodus", "ot", ["ex", "exod"]),
  book("Leviticus", "ot", ["lev"]),
  book("Numbers", "ot", ["num"]),
  book("Deuteronomy", "ot", ["deut"]),
  book("Joshua", "ot", ["josh"]),
  book("Judges", "ot", ["jdg", "judg"]),
  book("Ruth", "ot"),
  book("1 Samuel", "ot", ["1 sam"]),
  book("2 Samuel", "ot", ["2 sam"]),
  book("1 Kings", "ot", ["1 kgs"]),
  book("2 Kings", "ot", ["2 kgs"]),
  book("1 Chronicles", "ot", ["1 chr", "1 chron"]),
  book("2 Chronicles", "ot", ["2 chr", "2 chron"]),
  book("Ezra", "ot"),
  book("Nehemiah", "ot", ["neh"]),
  book("Esther", "ot", ["esth"]),
  book("Job", "ot"),
  book("Psalms", "psalm", ["ps", "psa", "psalm", "pss"]),
  book("Proverbs", "ot", ["prov"]),
  book("Ecclesiastes", "ot", ["eccl", "eccles"]),
  book("Song of Songs", "ot", ["canticles", "song", "song of solomon"]),
  book("Isaiah", "ot", ["isa"]),
  book("Jeremiah", "ot", ["jer"]),
  book("Lamentations", "ot", ["lam"]),
  book("Ezekiel", "ot", ["ezek"]),
  book("Daniel", "ot", ["dan"]),
  book("Hosea", "ot", ["hos"]),
  book("Joel", "ot"),
  book("Amos", "ot"),
  book("Obadiah", "ot", ["obad"]),
  book("Jonah", "ot"),
  book("Micah", "ot", ["mic"]),
  book("Nahum", "ot", ["nah"]),
  book("Habakkuk", "ot", ["hab"]),
  book("Zephaniah", "ot", ["zeph"]),
  book("Haggai", "ot", ["hag"]),
  book("Zechariah", "ot", ["zech"]),
  book("Malachi", "ot", ["mal"]),
  // Deuterocanon: "ot", except Psalm 151, which is a psalm
  book("Tobit", "ot", ["tb", "tob"]),
  book("Judith", "ot", ["jdt", "jth"]),
  book("Additions to Esther", "ot", ["add esth"]),
  book("Wisdom of Solomon", "ot", ["wis", "wisdom", "ws"]),
  book("Sirach", "ot", ["ecclesiasticus", "ecclus", "sir"]),
  book("Baruch", "ot", ["bar"]),
  book("Letter of Jeremiah", "ot", ["ep jer"]),
  book("Song of the Three", "ot", ["pr azar", "prayer of azariah", "song of the three jews", "song of the three young men"]),
  book("Susanna", "ot", ["sus"]),
  book("Bel and the Dragon", "ot", ["bel"]),
  book("1 Maccabees", "ot", ["1 macc", "1 mc"]),
  book("2 Maccabees", "ot", ["2 macc", "2 mc"]),
  book("3 Maccabees", "ot", ["3 macc", "3 mc"]),
  book("4 Maccabees", "ot", ["4 macc", "4 mc"]),
  book("1 Esdras", "ot", ["1 esd"]),
  book("2 Esdras", "ot", ["2 esd"]),
  book("Prayer of Manasseh", "ot", ["pr man"]),
  book("Psalm 151", "psalm"),
  // New Testament
  book("Matthew", "nt", ["mat", "matt", "mt"]),
  book("Mark", "nt", ["mk"]),
  book("Luke", "nt", ["lk"]),
  book("John", "nt", ["jn"]),
  book("Acts", "nt"),
  book("Romans", "nt", ["rm", "rom"]),
  book("1 Corinthians", "nt", ["1 cor"]),
  book("2 Corinthians", "nt", ["2 cor"]),
  book("Galatians", "nt", ["gal"]),
  book("Ephesians", "nt", ["eph"]),
  book("Philippians", "nt", ["phil", "php"]),
  book("Colossians", "nt", ["col"]),
  book("1 Thessalonians", "nt", ["1 thess"]),
  book("2 Thessalonians", "nt", ["2 thess"]),
  book("1 Timothy", "nt", ["1 tim"]),
  book("2 Timothy", "nt", ["2 tim"]),
  book("Titus", "nt", ["tit"]),
  book("Philemon", "nt", ["philem", "phlm"]),
  book("Hebrews", "nt", ["heb"]),
  book("James", "nt", ["jas"]),
  book("1 Peter", "nt", ["1 pet"]),
  book("2 Peter", "nt", ["2 pet"]),
  book("1 John", "nt", ["1 jn"]),
  book("2 John", "nt", ["2 jn"]),
  book("3 John", "nt", ["3 jn"]),
  book("Jude", "nt"),
  book("Revelation", "nt", ["rev", "revelations"]),
];

const ORDINAL_PREFIX = /^(iii|ii|iv|i|first|second|third|fourth|1st|2nd|3rd|4th) /;
const ORDINAL_DIGIT: Record<string, string> = {
  i: "1", ii: "2", iii: "3", iv: "4",
  first: "1", second: "2", third: "3", fourth: "4",
  "1st": "1", "2nd": "2", "3rd": "3", "4th": "4",
};

/**
 * Lower-case; drop a leading "*" and whitespace; remove "."; collapse spaces;
 * map a roman or ordinal prefix followed by a space to 1-4; then put a space
 * after a leading 1-4 glued to a letter ("1john" → "1 john").
 */
export function normalizeBookText(s: string): string {
  let out = s.toLowerCase();
  out = out.replace(/^\s*\*?\s*/, "");
  out = out.split(".").join("");
  out = out.replace(/\s+/g, " ").trim();
  out = out.replace(ORDINAL_PREFIX, (_match, prefix: string) => `${ORDINAL_DIGIT[prefix]} `);
  out = out.replace(/^([1-4])(?=[a-z])/, "$1 ");
  return out;
}

/** Every lookup key (the normalized name and each alias), longest first; a key naming two books throws at import. */
function aliasIndex(): readonly (readonly [string, Book])[] {
  const index = new Map<string, Book>();
  for (const b of BOOKS) {
    for (const key of [normalizeBookText(b.name), ...b.aliases]) {
      const existing = index.get(key);
      if (existing) throw new Error(`alias ${JSON.stringify(key)} is used by ${existing.name} and ${b.name}`);
      index.set(key, b);
    }
  }
  return [...index.entries()].sort(([a], [b]) => b.length - a.length || (a < b ? -1 : a > b ? 1 : 0));
}

const ALIASES = aliasIndex();

/** Trim each line and drop the blank ones. */
export function cleanLines(lines: readonly string[]): string[] {
  return lines.map((line) => line.trim()).filter((line) => line !== "");
}

/** Split on " or " (any case, any whitespace around it) and trim; empty pieces are dropped. */
export function splitAlternatives(ref: string): string[] {
  return ref
    .split(/\s+or\s+/i)
    .map((piece) => piece.trim())
    .filter((piece) => piece !== "");
}

/**
 * The longest book name or alias at the start of the normalized text,
 * followed by the end, a space or a digit: the canonical book and the rest of
 * the normalized text, trimmed. Null when no book matches.
 */
export function splitBook(ref: string): { book: Book; rest: string } | null {
  const text = normalizeBookText(ref);
  for (const [key, b] of ALIASES) {
    if (text.startsWith(key)) {
      const after = text.slice(key.length);
      if (after === "" || after[0] === " " || /[0-9]/.test(after[0])) {
        return { book: b, rest: after.trim() };
      }
    }
  }
  return null;
}

/** The testament of one alternative's book, or "unknown". */
export function classify(ref: string): Classification {
  return splitBook(ref)?.book.testament ?? "unknown";
}

export function isNtRef(ref: string): boolean {
  return classify(ref) === "nt";
}

/** Clean the lines, expand every alternative, and de-duplicate in first-seen order. */
export function expandRefOptions(refs: readonly string[]): string[] {
  const out: string[] = [];
  for (const line of cleanLines(refs)) {
    for (const alt of splitAlternatives(line)) {
      if (!out.includes(alt)) out.push(alt);
    }
  }
  return out;
}

/** The two bulletin pickers: "nt" holds the NT options; "ot" everything else (ot, psalm and unknown). */
export function pickerOptions(scriptures: readonly string[]): { ot: string[]; nt: string[] } {
  const options = expandRefOptions(scriptures);
  return {
    ot: options.filter((o) => classify(o) !== "nt"),
    nt: options.filter((o) => classify(o) === "nt"),
  };
}

export type ReadingPair = { ot: string | null; nt: string | null; otAuto: boolean; ntAuto: boolean };

function firstAlternativeIsNt(line: string): boolean {
  const alternatives = splitAlternatives(line);
  return alternatives.length > 0 && isNtRef(alternatives[0]);
}

/**
 * The only bulletin-reading rule (spec decision 9). A pick counts only when it
 * is one of the current options for its side; otherwise that side is
 * automatic. The automatic OT is the first line that is not the NT pick; the
 * automatic NT is the first line other than the effective OT whose first
 * alternative is NT, so a Psalm is never the automatic NT. Lines are returned
 * as written.
 */
export function resolveReadings(
  scriptures: readonly string[],
  otPick: string | null = "",
  ntPick: string | null = "",
): ReadingPair {
  const entries = cleanLines(scriptures);
  const options = pickerOptions(entries);
  let ot = (otPick ?? "").trim();
  if (!options.ot.includes(ot)) ot = "";
  let nt = (ntPick ?? "").trim();
  if (!options.nt.includes(nt)) nt = "";
  const effectiveOt = ot || (entries.find((e) => e !== nt) ?? null);
  const effectiveNt = nt || (entries.find((e) => e !== effectiveOt && firstAlternativeIsNt(e)) ?? null);
  return { ot: effectiveOt, nt: effectiveNt, otAuto: !ot, ntAuto: !nt };
}

/** resolveReadings with no picks. */
export function defaultReadingPair(scriptures: readonly string[]): ReadingPair {
  return resolveReadings(scriptures, "", "");
}

/** The automatic NT reading (slice 3's hymn matching). */
export function defaultNtRef(scriptures: readonly string[]): string | null {
  return defaultReadingPair(scriptures).nt;
}

/** Python's `normalize_for_fetch`, used here only to build comparison keys. */
function normalizeForKey(ref: string): string {
  let s = ref.replace(/^\s*\*\s*/, "");
  s = s.replace(/[–—]/g, "-");
  s = s.replace(/(?<=\d)[A-Za-z](?![A-Za-z])/g, "");
  s = s.replace(/[()]/g, "");
  s = s.replace(/(?<=\d)\s+(?=\d)/g, ", ");
  s = s.replace(/,(\s*,)+/g, ",");
  return s.replace(/\s+/g, " ").trim();
}

/** A comparison key: equal keys mean the same passage ("Luke 2:1-14 (15-20)" = "Luke 2:1-14, (15-20)"). */
export function scriptureKey(ref: string): string {
  return normalizeForKey(ref).toLowerCase().replace(/[\s,.()]/g, "");
}
