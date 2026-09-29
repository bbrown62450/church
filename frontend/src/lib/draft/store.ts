/**
 * The draft store (F §4.6 "Persistence", "Versioning"; S "store.ts"): one
 * user's draft for one church, loaded from and written to
 * `localStorage["wsb:draft:{userId}:{churchId}"]` through `lib/storage.ts`.
 *
 * - Load: parse → migrate → validate → `normalizePicks`. A stored value that
 *   cannot be restored is copied to the corrupt-draft key, a fresh draft
 *   starts, and a "restore_failed" notice follows; when the copy cannot be
 *   written, the stored value is left in place until the user edits. A
 *   pristine draft (a translation override aside) whose default date has
 *   passed rolls forward to the next Sunday, stamped 1 ms after the stored `updated_at` so it never outranks a
 *   newer edit from another tab.
 * - `update(recipe)` applies the recipe to the latest draft, bumps
 *   `updated_at` and schedules a write 400 ms later; a recipe that returns the
 *   same object does nothing. `autoUpdate(recipe)` is the same for an
 *   automatic change (the lectionary fill), stamped 1 ms after the current
 *   `updated_at` instead of now, so it never outranks a real edit made in
 *   another tab on a copy this tab has not seen yet. `setLastStep` changes only `last_step` and
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
 * - A failed write switches to memory-only with one "memory_only" notice and
 *   stays pending, so the next flush (hide, pagehide) retries it.
 * - Another tab's write for this key is adopted when its `updated_at` is
 *   strictly newer ("adopted"), from its `storage` event or, when this tab is
 *   shown again, from a direct read (`syncFromStorage`, slice 2c). A flush
 *   that finds a strictly newer stored draft adopts it instead of writing.
 *
 * React wiring (listeners, toasts, flush on hide and unmount) is in
 * `context.tsx`. This class touches storage only in `start`, `flush`,
 * `syncFromStorage` and the constructor's single read, so it can be built
 * during a render.
 */
import { isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { readLocal, removeLocal, tryWriteLocal } from "@/lib/storage";

import { parseStoredDraft } from "./migrate";
import { normalizePicks, setDate } from "./readings";
import { churchZone, corruptDraftKey, draftKey, freshDraft, type DraftChurch, type DraftV1, type StepId } from "./schema";
import { isPristine } from "./status";

export const WRITE_DELAY_MS = 400;

export type Persistence = "ok" | "memory-only";
export type DraftNotice = "restore_failed" | "memory_only" | "adopted";
export type DraftSnapshot = { readonly draft: DraftV1; readonly persistence: Persistence };

/** Where drafts live; the browser's is `lib/storage.ts`, tests pass a Map. */
export type DraftStorage = {
  read(key: string): string | null;
  /** False when the value could not be stored. */
  write(key: string, value: string): boolean;
  remove(key: string): void;
};

export const browserDraftStorage: DraftStorage = { read: readLocal, write: tryWriteLocal, remove: removeLocal };

export type DraftStoreOptions = {
  userId: string;
  church: DraftChurch;
  storage?: DraftStorage;
  now?: () => Date;
  notify?: (notice: DraftNotice) => void;
};

/**
 * The pristine draft's passed default date moves to the next Sunday (S
 * "Mount-time roll-forward"). A translation override does not hold the date
 * back and is kept (owner answer A, 2026-09-29), though it still counts for
 * "New service" (`isPristine`).
 */
export function rollForward(draft: DraftV1, today: string): DraftV1 {
  const r = draft.readings;
  const pristine = isPristine({ ...draft, readings: { ...r, translation: null } });
  if (r.date_origin !== "default" || !isValidDateIso(r.date_iso) || r.date_iso >= today || !pristine) {
    return draft;
  }
  return setDate(draft, nextSunday(today), "default");
}

function isNewer(candidate: string, current: string): boolean {
  const a = Date.parse(candidate);
  const b = Date.parse(current);
  return Number.isFinite(a) && (!Number.isFinite(b) || a > b);
}

export class DraftStore {
  readonly key: string;
  private readonly corruptKey: string;
  private readonly userId: string;
  private readonly churchId: string;
  private readonly storage: DraftStorage;
  private readonly now: () => Date;
  private readonly notify: (notice: DraftNotice) => void;
  private snapshot: DraftSnapshot;
  private readonly listeners = new Set<() => void>();
  private timer: ReturnType<typeof setTimeout> | null = null;
  private pendingWrite = false;
  private started = false;
  private warnedMemoryOnly = false;
  /** The raw value that could not be restored, backed up in `start`. */
  private corruptRaw: string | null = null;

  constructor({ userId, church, storage = browserDraftStorage, now = () => new Date(), notify = () => {} }: DraftStoreOptions) {
    this.userId = userId;
    this.churchId = church.id;
    this.key = draftKey(userId, church.id);
    this.corruptKey = corruptDraftKey(userId, church.id);
    this.storage = storage;
    this.now = now;
    this.notify = notify;

    const fresh = () => freshDraft({ church, user: { id: userId }, now: now() });
    const raw = storage.read(this.key);
    let draft: DraftV1;
    if (raw === null) {
      draft = fresh();
      this.pendingWrite = true;
    } else {
      try {
        const stored = parseStoredDraft(raw, { userId, churchId: church.id });
        draft = normalizePicks(stored);
        this.pendingWrite = draft !== stored;
      } catch {
        this.corruptRaw = raw;
        draft = fresh();
        this.pendingWrite = true;
      }
    }
    const rolled = rollForward(draft, todayIn(churchZone(church), now()));
    if (rolled !== draft) {
      // Just after the stored stamp, not now: a newer unwritten edit from another tab still wins.
      const storedAt = Date.parse(draft.updated_at);
      const updatedAt = Number.isFinite(storedAt) ? new Date(storedAt + 1) : now();
      draft = { ...rolled, updated_at: updatedAt.toISOString() };
      this.pendingWrite = true;
    }
    this.snapshot = { draft, persistence: "ok" };
  }

  getSnapshot = (): DraftSnapshot => this.snapshot;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  /** Once, after mount: back up a draft that could not be restored, report it, and write what load changed. */
  start(): void {
    if (this.started) return;
    this.started = true;
    if (this.corruptRaw !== null) {
      // The old backup is being replaced anyway; removing it first frees its space.
      this.storage.remove(this.corruptKey);
      const backedUp = this.storage.write(this.corruptKey, this.corruptRaw);
      this.notify("restore_failed");
      // Without a backup, keep the unrestorable value in the main key until the user edits.
      if (!backedUp) this.pendingWrite = false;
    }
    if (this.pendingWrite) this.schedule();
  }

  update = (recipe: (d: DraftV1) => DraftV1): void => {
    const next = recipe(this.snapshot.draft);
    if (next === this.snapshot.draft) return;
    this.set({ ...next, updated_at: this.now().toISOString() });
    this.schedule();
  };

  /** An automatic change: stamped 1 ms after the current draft, so any real edit (here or in another tab) outranks it. */
  autoUpdate = (recipe: (d: DraftV1) => DraftV1): void => {
    const current = this.snapshot.draft;
    const next = recipe(current);
    if (next === current) return;
    const at = Date.parse(current.updated_at);
    this.set({ ...next, updated_at: (Number.isFinite(at) ? new Date(at + 1) : this.now()).toISOString() });
    this.schedule();
  };

  replace = (next: DraftV1): void => {
    this.set(normalizePicks({ ...next, updated_at: this.now().toISOString() }));
    this.schedule();
  };

  setLastStep = (step: StepId): void => {
    if (this.snapshot.draft.last_step === step) return;
    this.set({ ...this.snapshot.draft, last_step: step });
    this.schedule();
  };

  /** A `storage` event: adopt another tab's strictly newer draft for this key. */
  handleStorageEvent = (key: string | null, newValue: string | null): void => {
    if (key !== this.key) return;
    this.adoptIfNewer(newValue);
  };

  /**
   * The tab is shown again: read the stored draft now and adopt it when it is
   * strictly newer, before anything on screen (the lectionary fill) acts on
   * this tab's copy. The other tab's `storage` event may not have arrived yet,
   * and a fill stamped now would outrank that tab's just-written typing.
   */
  syncFromStorage = (): void => {
    this.adoptIfNewer(this.storage.read(this.key));
  };

  /** Writes a scheduled change now (hide, pagehide, unmount). */
  flush = (): void => {
    if (!this.pendingWrite) return;
    // Another tab's strictly newer draft whose storage event has not arrived yet: take it, never overwrite it.
    if (this.adoptIfNewer(this.storage.read(this.key))) return;
    this.cancelWrite();
    const ok = this.storage.write(this.key, JSON.stringify(this.snapshot.draft));
    const persistence: Persistence = ok ? "ok" : "memory-only";
    if (persistence !== this.snapshot.persistence) {
      this.snapshot = { ...this.snapshot, persistence };
      this.emit();
    }
    // A failed write stays pending (no timer), so the next flush retries it.
    if (!ok) this.pendingWrite = true;
    if (!ok && !this.warnedMemoryOnly) {
      this.warnedMemoryOnly = true;
      this.notify("memory_only");
    }
  };

  /** True when the stored draft was strictly newer and is now this tab's. */
  private adoptIfNewer(raw: string | null): boolean {
    if (raw === null) return false;
    let stored: DraftV1;
    try {
      stored = parseStoredDraft(raw, { userId: this.userId, churchId: this.churchId });
    } catch {
      return false;
    }
    if (!isNewer(stored.updated_at, this.snapshot.draft.updated_at)) return false;
    this.cancelWrite();
    this.set(normalizePicks(stored));
    this.notify("adopted");
    return true;
  }

  private schedule(): void {
    this.pendingWrite = true;
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = setTimeout(this.flush, WRITE_DELAY_MS);
  }

  private cancelWrite(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.pendingWrite = false;
  }

  private set(draft: DraftV1): void {
    this.snapshot = { ...this.snapshot, draft };
    this.emit();
  }

  private emit(): void {
    for (const listener of this.listeners) listener();
  }
}
