/**
 * Draft cleanup (F §4.6 "When the draft is cleared or replaced", items 3 and
 * 4; S "prune.ts"). The `(signed-in)` layout calls it once `/me` has loaded:
 * for this user it removes drafts not updated for 30 days and drafts for
 * churches the user no longer belongs to, with their corrupt-draft backups,
 * and (slice 5b-2) the email dialog's remembered choices for those churches.
 * Another user's keys on a shared device are never touched.
 */
import { localKeys, readLocal, removeLocal } from "@/lib/storage";

export const PRUNE_AFTER_MS = 30 * 24 * 60 * 60 * 1000;

function updatedAt(raw: string | null): number {
  if (raw === null) return Number.NaN;
  try {
    const value = (JSON.parse(raw) as { updated_at?: unknown }).updated_at;
    return typeof value === "string" ? Date.parse(value) : Number.NaN;
  } catch {
    return Number.NaN;
  }
}

/** Returns the keys it removed (for tests and logs). */
export function pruneDrafts(userId: string, churchIds: readonly string[], now: Date = new Date()): string[] {
  const draftPrefix = `wsb:draft:${userId}:`;
  const corruptPrefix = `wsb:draft-corrupt:${userId}:`;
  const emailPrefix = `wsb:emailPrefs:${userId}:`;
  const members = new Set(churchIds);
  const removed: string[] = [];
  for (const key of localKeys()) {
    if (key.startsWith(draftPrefix)) {
      const churchId = key.slice(draftPrefix.length);
      const age = now.getTime() - updatedAt(readLocal(key));
      // A draft we cannot date is kept: the store backs it up and starts fresh when it is opened.
      if (!members.has(churchId) || age > PRUNE_AFTER_MS) {
        removeLocal(key);
        removeLocal(`${corruptPrefix}${churchId}`);
        removed.push(key);
      }
    } else if (key.startsWith(corruptPrefix) && !members.has(key.slice(corruptPrefix.length))) {
      removeLocal(key);
      removed.push(key);
    } else if (key.startsWith(emailPrefix) && !members.has(key.slice(emailPrefix.length))) {
      removeLocal(key);
      removed.push(key);
    }
  }
  return removed;
}
