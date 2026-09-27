/**
 * URL helpers (S "Storage and URL helpers"; F §4.3). Pure functions: anything that came
 * from a query string, a paste or the server goes through one of these before the app
 * navigates to it or renders it as a link.
 */

const MAX_INTERNAL_PATH_LENGTH = 512;

/** First path segments a post-login `next` may return to (F §4.3). */
const INTERNAL_PATH_ROOTS = new Set(["join", "builder", "services", "settings", "welcome"]);

function hasUnsafeCharacter(path: string): boolean {
  for (const ch of path) {
    const code = ch.codePointAt(0) ?? 0;
    if (code <= 0x1f || (code >= 0x7f && code <= 0x9f)) return true;
  }
  return /[\s\\?#]/.test(path);
}

/** `..`, including percent-encoded dots, which browsers also resolve. */
function isParentSegment(segment: string): boolean {
  return segment.replace(/%2e/gi, ".") === "..";
}

/**
 * `raw` if it is a same-site path the app may navigate to after sign-in, else null.
 * At most 512 characters; exactly one leading `/`; no `//`, `\`, whitespace, control
 * characters, `?`, `#` or `..` segment; first segment one of join, builder, services,
 * settings, welcome, matched whole (so `/joinx` is rejected).
 */
export function safeInternalPath(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  if (raw.length === 0 || raw.length > MAX_INTERNAL_PATH_LENGTH) return null;
  if (!raw.startsWith("/") || raw.includes("//")) return null;
  if (hasUnsafeCharacter(raw)) return null;
  const segments = raw.slice(1).split("/");
  if (segments.some(isParentSegment)) return null;
  if (!INTERNAL_PATH_ROOTS.has(segments[0])) return null;
  return raw;
}

function decodeParam(value: string): string {
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/**
 * The invite code in whatever the user pasted: a raw code, a full invite link, or a link
 * without its scheme (`example.com/join?code=…`). A link that carries no `code` gives "".
 */
export function extractInviteCode(input: string): string {
  const trimmed = input.trim();
  try {
    return (new URL(trimmed).searchParams.get("code") ?? "").trim();
  } catch {
    // Not an absolute URL: a raw code, or a link pasted without its scheme.
  }
  const match = /[?&]code=([^&#\s]*)/.exec(trimmed);
  return match ? decodeParam(match[1]).trim() : trimmed;
}

/** The shareable invite link for `code` (6b's Copy link button). */
export function buildInviteUrl(code: string, origin: string = window.location.origin): string {
  return `${origin}/join?code=${encodeURIComponent(code)}`;
}

/** The normalized URL when `raw` is an absolute `https:` URL, else null (slice 3 links). */
export function safeHttpsUrl(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  try {
    const url = new URL(raw);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}
