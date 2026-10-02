/**
 * Reading a stored draft back (F §4.6 "Versioning"): parse the JSON, run
 * `migrations[v]` step by step up to `DRAFT_VERSION`, then validate with zod.
 * Any failure (corrupt JSON, invalid data, a *future* version after a
 * rollback, a draft stored under another user's or church's key) throws
 * `DraftRestoreError`; the store then backs the raw value up, starts fresh
 * and toasts. Every change to `DraftV1` bumps the version and adds a
 * migration here with a unit test.
 */
import { isValidDateIso } from "@/lib/dates";

import { DRAFT_VERSION, draftV1Schema, type DraftV1 } from "./schema";

export type StoredDraft = Record<string, unknown>;
/** Upgrades a version-v draft to version v + 1 (it need not set `version`). */
export type Migration = (draft: StoredDraft) => StoredDraft;

/**
 * `migrations[v]` upgrades version v to v + 1.
 *
 * 1 → 2 (slice 5a-3; F §4.6): `editing`, when set, gains `date_iso`, the
 * draft's own date (null when that is not a real date); `save_key_fingerprint`
 * starts null. No version 1 draft has `editing` set: nothing could save before
 * 5a-3.
 */
export const migrations: Readonly<Record<number, Migration>> = {
  1: (draft) => {
    const readings = isRecord(draft.readings) ? draft.readings : {};
    const date = typeof readings.date_iso === "string" && isValidDateIso(readings.date_iso) ? readings.date_iso : null;
    const editing = isRecord(draft.editing) ? { ...draft.editing, date_iso: date } : null;
    return { ...draft, editing, save_key_fingerprint: null };
  },
};

export class DraftRestoreError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DraftRestoreError";
  }
}

function isRecord(value: unknown): value is StoredDraft {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Brings a parsed draft up to `target`; throws on a missing, invalid or future version or a missing step. */
export function migrate(
  raw: unknown,
  table: Readonly<Record<number, Migration>> = migrations,
  target: number = DRAFT_VERSION,
): StoredDraft {
  if (!isRecord(raw)) throw new DraftRestoreError("The stored draft is not an object.");
  let version = raw.version;
  if (typeof version !== "number" || !Number.isInteger(version) || version < 1) {
    throw new DraftRestoreError("The stored draft has no valid version.");
  }
  if (version > target) {
    throw new DraftRestoreError(`The stored draft is version ${version}, newer than ${target}.`);
  }
  let draft = raw;
  while (version < target) {
    const step = table[version];
    if (!step) throw new DraftRestoreError(`No migration from version ${version}.`);
    let next: unknown;
    try {
      next = step(draft);
    } catch {
      throw new DraftRestoreError(`Migration from version ${version} failed.`);
    }
    if (!isRecord(next)) throw new DraftRestoreError(`Migration from version ${version} returned no object.`);
    version += 1;
    draft = { ...next, version };
  }
  return draft;
}

/**
 * The stored text as a valid current draft for this user and church, or
 * `DraftRestoreError`. `migrationTable` and `target` exist for tests.
 */
export function parseStoredDraft(
  text: string,
  owner: { userId: string; churchId: string },
  migrationTable: Readonly<Record<number, Migration>> = migrations,
  target: number = DRAFT_VERSION,
): DraftV1 {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    throw new DraftRestoreError("The stored draft is not JSON.");
  }
  const result = draftV1Schema.safeParse(migrate(raw, migrationTable, target));
  if (!result.success) throw new DraftRestoreError("The stored draft does not match the schema.");
  if (result.data.user_id !== owner.userId || result.data.church_id !== owner.churchId) {
    throw new DraftRestoreError("The stored draft belongs to another user or church.");
  }
  return result.data;
}
