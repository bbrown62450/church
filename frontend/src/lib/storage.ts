/**
 * Browser storage behind try/catch (F §4.3). Storage can be missing (server render),
 * blocked (privacy settings throw on access) or full (quota errors on write); in every
 * case a read returns null and a write or remove does nothing, so callers never guard.
 */

/** Session keys use the `wsb:` prefix; sign-out removes them (S Flow D). */
export const SESSION_KEYS = {
  pendingInviteCode: "wsb:pendingInviteCode",
  postLoginPath: "wsb:postLoginPath",
} as const;

/** The remembered church (localStorage). Name kept from slice 0 so nobody loses their choice. */
export const ACTIVE_CHURCH_KEY = "activeChurchId";

type Area = "sessionStorage" | "localStorage";

function read(area: Area, key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window[area].getItem(key);
  } catch {
    return null;
  }
}

function write(area: Area, key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    window[area].setItem(key, value);
  } catch {
    // Blocked or full: the value just isn't remembered.
  }
}

function remove(area: Area, key: string): void {
  if (typeof window === "undefined") return;
  try {
    window[area].removeItem(key);
  } catch {
    // Blocked: there is nothing stored to remove.
  }
}

export function readSession(key: string): string | null {
  return read("sessionStorage", key);
}

export function writeSession(key: string, value: string): void {
  write("sessionStorage", key, value);
}

export function removeSession(key: string): void {
  remove("sessionStorage", key);
}

export function readLocal(key: string): string | null {
  return read("localStorage", key);
}

export function writeLocal(key: string, value: string): void {
  write("localStorage", key, value);
}

export function removeLocal(key: string): void {
  remove("localStorage", key);
}
