/**
 * The path to return to after sign-in (S "Storage and URL helpers", F §4.3). `/login` stores a
 * validated `next` before OAuth; the `(signed-in)` layout reads it when it mounts and
 * clears it before following it (1b clarification 22); `/join` clears it on mount. It lives
 * in sessionStorage (`wsb:postLoginPath`, JSON `{path, at}`) for 10 minutes, and every read
 * goes back through `safeInternalPath`, so a stale, tampered or malformed value is ignored.
 */
import { SESSION_KEYS, readSession, removeSession, writeSession } from "@/lib/storage";
import { safeInternalPath } from "@/lib/urls";

export const POST_LOGIN_TTL_MS = 10 * 60_000;

/** Store `path` with the time it was stored. A path `safeInternalPath` rejects is not stored. */
export function storePostLoginPath(path: string, now: number = Date.now()): void {
  const safe = safeInternalPath(path);
  if (safe === null) return;
  writeSession(SESSION_KEYS.postLoginPath, JSON.stringify({ path: safe, at: now }));
}

/** The stored path if it is safe and less than 10 minutes old, else null. Never clears it. */
export function peekPostLoginPath(now: number = Date.now()): string | null {
  const raw = readSession(SESSION_KEYS.postLoginPath);
  if (raw === null) return null;
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null) return null;
  const { path, at } = parsed as { path?: unknown; at?: unknown };
  if (typeof at !== "number" || !Number.isFinite(at)) return null;
  const age = now - at;
  if (age < 0 || age >= POST_LOGIN_TTL_MS) return null;
  return safeInternalPath(path);
}

export function clearPostLoginPath(): void {
  removeSession(SESSION_KEYS.postLoginPath);
}
