/**
 * The references a scripture-match request sends (S `buildMatchRefs`), within
 * `ScriptureMatchIn`'s limits (at most 20, each at most 200 characters), so a
 * long typed line can never cause a 422 that Retry cannot clear.
 */
export const MAX_REFS = 20;
export const MAX_REF_LENGTH = 200;

/**
 * The first `n` characters of `s` as the server counts them (Unicode code
 * points, Python's `len`), so a cut never splits an emoji's surrogate pair
 * and never leaves a line the server finds too long.
 */
export function clipChars(s: string, n: number): string {
  return s.length <= n ? s : Array.from(s).slice(0, n).join("");
}

/** Each item trimmed, blanks dropped, each cut to `maxLen` characters, the first `max` kept. */
export function cleanRefs(list: readonly string[], { max, maxLen }: { max: number; maxLen: number }): string[] {
  return list
    .map((line) => clipChars(line.trim(), maxLen).trim())
    .filter((line) => line !== "")
    .slice(0, max);
}

/** The cleaned draft scriptures (19 at most when there is an extra reference), then the extra one, never twice. */
export function buildMatchRefs(scriptures: readonly string[], extraRef: string): string[] {
  const [extra] = cleanRefs([extraRef], { max: 1, maxLen: MAX_REF_LENGTH });
  if (extra === undefined) return cleanRefs(scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH });
  const base = cleanRefs(scriptures, { max: MAX_REFS - 1, maxLen: MAX_REF_LENGTH });
  return base.includes(extra) ? base : [...base, extra];
}
