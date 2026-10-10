import { useSyncExternalStore } from "react";

import type { Church } from "@/lib/api/types";
import { ACTIVE_CHURCH_KEY, readLocal, removeLocal, writeLocal } from "@/lib/storage";

export type { Church, Me } from "@/lib/api/types";

/**
 * The remembered church if the user still belongs to it and it is not excluded, else
 * their first church by name; null when none is left. `excluded` holds churches the
 * user has just lost access to (the `(church)` layout's 403 fallback, F §4.2 step 2).
 */
export function pickActiveChurch(
  churches: Church[],
  storedId: string | null | undefined,
  excluded: ReadonlySet<string> = new Set(),
): Church | null {
  const available = churches.filter((c) => !excluded.has(c.id));
  const stored = available.find((c) => c.id === storedId);
  if (stored) return stored;
  return [...available].sort((a, b) => a.name.localeCompare(b.name))[0] ?? null;
}

const ROLE_LABELS = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
} as const satisfies Record<Church["role"], string>;

/** How a membership role reads in the UI (account menu, switcher). */
export function roleLabel(role: Church["role"]): "Owner" | "Admin" | "Member" {
  return ROLE_LABELS[role];
}

/** Owners and admins: who may edit the church's settings (the server's `require_admin`). */
export function isAdmin(role: Church["role"]): boolean {
  return role === "owner" || role === "admin";
}

export function readStoredChurchId(): string | null {
  return readLocal(ACTIVE_CHURCH_KEY);
}

// The stored church as this tab sees it. `undefined` = not read from localStorage yet.
// It changes only inside getSnapshot, storeChurchId and the test reset, never during a
// component render (react-hooks v7 rules).
let storedChurchId: string | null | undefined;
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): string | null {
  if (storedChurchId === undefined) storedChurchId = readStoredChurchId();
  return storedChurchId;
}

function getServerSnapshot(): undefined {
  return undefined;
}

/**
 * Remembers the active church (null forgets it) and tells this tab's `useStoredChurchId`
 * readers. Other tabs are not told: they keep their church until they reload.
 */
export function storeChurchId(id: string | null): void {
  if (id) writeLocal(ACTIVE_CHURCH_KEY, id);
  else removeLocal(ACTIVE_CHURCH_KEY);
  storedChurchId = id || null;
  for (const listener of listeners) listener();
}

/**
 * The stored church id: `undefined` on the server and during hydration ("not read yet",
 * so the layout shows its skeleton), then the id or null. It follows `storeChurchId` in
 * this tab and ignores `storage` events from other tabs (S Layouts step 1).
 */
export function useStoredChurchId(): string | null | undefined {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

/** Forget the cached id so the next read goes back to localStorage (test isolation). */
export function resetStoredChurchIdForTests(): void {
  storedChurchId = undefined;
}

// --- Slice 6b-2b: a church the user just left or deleted ------------------------------------------------------

/** How long `markChurchExited` lasts (6b spec "Change to slice 1's (church) layout"). */
export const EXITED_MARK_MS = 60_000;

// When each church was marked, by id. Module state: one tab, never stored.
const exitedAt = new Map<string, number>();

/**
 * Marks `id` as a church the user has just left or deleted here
 * (`runChurchExit`'s first step), so the `(church)` layout re-picks quietly
 * instead of saying "You no longer have access to {name}." for it.
 */
export function markChurchExited(id: string, at: number = Date.now()): void {
  exitedAt.set(id, at);
}

/**
 * True for 60 s after `markChurchExited(id)`. A later loss of the same church
 * (rejoined, then removed) shows the toast again.
 */
export function wasChurchExited(id: string, now: number = Date.now()): boolean {
  const at = exitedAt.get(id);
  if (at === undefined) return false;
  if (now - at < EXITED_MARK_MS) return true;
  exitedAt.delete(id);
  return false;
}

/** Forget every mark (test isolation). */
export function resetExitedChurchesForTests(): void {
  exitedAt.clear();
}
