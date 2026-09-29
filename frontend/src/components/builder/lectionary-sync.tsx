"use client";

/**
 * `useLectionarySync()` (S "useLectionarySync"; F §4.6 "Never destroy typed
 * input"), mounted by `BuilderShell` through `<LectionarySync>`, so it runs on
 * every step. It looks up the draft's date 400 ms after the date last changed
 * (a date typed segment by segment is looked up once) and, when the answer
 * arrives, fills empty fields or an older date's lectionary fields with the
 * default set. The fill goes through `autoUpdate`, stamped 1 ms after the
 * draft it changes, so it never outranks typing from another tab that has not
 * reached this one yet (two visible tabs, or a storage event that arrives
 * late). The check runs inside the recipe, against the latest draft, so a
 * keystroke in the same tick is never overwritten; typed and archived fields
 * are never touched.
 *
 * Only the visible tab fills (2b build notes): a fill in a hidden tab would
 * write a newer draft, and the visible tab adopting it would drop up to 400 ms
 * of its own unwritten typing. A hidden tab fills when it becomes visible,
 * after `DraftProvider` has re-read the stored draft on that same
 * `visibilitychange` (`syncFromStorage`), so the fill never acts on a stale
 * copy and outranks the other tab's just-written typing.
 *
 * `useLectionaryLookup()` gives the step the same lookup (one query, one
 * debounce) for its status area.
 */
import type { UseQueryResult } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useSyncExternalStore, type ReactNode } from "react";

import type { ApiError } from "@/lib/api/client";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { applyReadingSet, shouldAutoApply } from "@/lib/draft/readings";
import { useLectionary } from "@/lib/queries/lectionary";
import { useDebouncedValue } from "@/lib/use-debounced-value";

/** How long the date must stay unchanged before it is looked up. */
export const LOOKUP_DELAY_MS = 400;

export type LectionaryLookup = {
  /** The date the query is for: the draft's date, up to 400 ms behind while it changes. */
  lookupDate: string;
  /** False while the draft's date is ahead of `lookupDate`; the step shows Loading meanwhile. */
  settled: boolean;
  query: UseQueryResult<Lectionary, ApiError>;
};

function subscribeVisibility(onChange: () => void): () => void {
  document.addEventListener("visibilitychange", onChange);
  return () => document.removeEventListener("visibilitychange", onChange);
}

/** True while this tab is the one on screen (always true on the server). */
export function usePageVisible(): boolean {
  return useSyncExternalStore(
    subscribeVisibility,
    () => document.visibilityState === "visible",
    () => true,
  );
}

export function useLectionarySync(): LectionaryLookup {
  const { draft, autoUpdate } = useDraft();
  const dateIso = draft.readings.date_iso;
  const lookupDate = useDebouncedValue(dateIso, LOOKUP_DELAY_MS);
  const query = useLectionary(lookupDate);
  const visible = usePageVisible();
  const data = query.data;
  const due = data !== undefined && shouldAutoApply(draft, data);

  useEffect(() => {
    if (!due || !visible || data === undefined) return;
    autoUpdate((d) =>
      shouldAutoApply(d, data) && data.default_index !== null ? applyReadingSet(d, data, data.default_index) : d,
    );
  }, [due, visible, data, autoUpdate]);

  return { lookupDate, settled: lookupDate === dateIso, query };
}

const LectionaryContext = createContext<LectionaryLookup | null>(null);

/** Runs the sync for everything inside it and shares its lookup. Render it inside `DraftProvider`. */
export function LectionarySync({ children }: { children: ReactNode }) {
  const lookup = useLectionarySync();
  return <LectionaryContext value={lookup}>{children}</LectionaryContext>;
}

/** The builder's lookup for the draft's date. Throws outside `<LectionarySync>`. */
export function useLectionaryLookup(): LectionaryLookup {
  const lookup = useContext(LectionaryContext);
  if (!lookup) throw new Error("useLectionaryLookup() must be used inside <LectionarySync>.");
  return lookup;
}
