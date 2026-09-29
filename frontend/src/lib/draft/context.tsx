"use client";

/**
 * `DraftProvider` and `useDraft()` (F §4.6; S "store.ts / context.tsx").
 * `BuilderShell` renders the provider for the signed-in user and the active
 * church; the `(church)` layout's keyed remount already gives each church its
 * own provider. The provider wires the store to the browser: another tab's
 * writes (`storage` events, and a direct read when the page is shown again), a
 * flush when the page is hidden or left, a flush on unmount (a church switch),
 * and the three toasts.
 */
import { createContext, useContext, useEffect, useMemo, useState, useSyncExternalStore, type ReactNode } from "react";
import { toast } from "sonner";

import type { DraftChurch, DraftV1, StepId } from "./schema";
import { DraftStore, type DraftNotice, type Persistence } from "./store";

export type DraftApi = {
  draft: DraftV1;
  /** Applies the recipe to the latest draft; a recipe that returns the same object does nothing. */
  update: (recipe: (d: DraftV1) => DraftV1) => void;
  /** New service; slice 5a's archive load. */
  replace: (next: DraftV1) => void;
  /** Navigation only: never bumps `updated_at`. */
  setLastStep: (step: StepId) => void;
  persistence: Persistence;
};

export const DRAFT_MESSAGES = {
  restore_failed: "We couldn't restore your unsaved draft.",
  // Owner answer B6 (2026-09-29): F's "Don't refresh until you save." named a Save that 5a adds.
  memory_only: "This browser isn't saving your draft. Don't refresh or close this tab, or you'll lose your changes.",
  adopted: "Updated from another tab.",
} as const satisfies Record<DraftNotice, string>;

function notify(notice: DraftNotice): void {
  const message = DRAFT_MESSAGES[notice];
  // An id per notice, so StrictMode or a quick repeat never stacks two toasts.
  if (notice === "restore_failed") toast.error(message, { id: `draft-${notice}` });
  else if (notice === "memory_only") toast.warning(message, { id: `draft-${notice}` });
  else toast.info(message, { id: `draft-${notice}` });
}

const DraftContext = createContext<DraftApi | null>(null);

export function DraftProvider({
  userId,
  church,
  children,
}: {
  userId: string;
  church: DraftChurch;
  children: ReactNode;
}) {
  const [store] = useState(() => new DraftStore({ userId, church, notify }));
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);

  useEffect(() => {
    store.start();
    const onStorage = (event: StorageEvent) => store.handleStorageEvent(event.key, event.newValue);
    // Hidden: write now. Shown: take another tab's newer draft before this tab's
    // lectionary fill can act on a stale copy (its storage event may still be on the way).
    const onVisibility = () => {
      if (document.visibilityState === "hidden") store.flush();
      else store.syncFromStorage();
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener("pagehide", store.flush);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("pagehide", store.flush);
      document.removeEventListener("visibilitychange", onVisibility);
      store.flush();
    };
  }, [store]);

  const value = useMemo<DraftApi>(
    () => ({
      draft: snapshot.draft,
      persistence: snapshot.persistence,
      update: store.update,
      replace: store.replace,
      setLastStep: store.setLastStep,
    }),
    [snapshot, store],
  );
  return <DraftContext value={value}>{children}</DraftContext>;
}

/** The draft for the active church. Throws outside `DraftProvider` (a builder component rendered in the wrong place). */
export function useDraft(): DraftApi {
  const api = useContext(DraftContext);
  if (!api) throw new Error("useDraft() must be used inside <DraftProvider>.");
  return api;
}
