"use client";

/**
 * Carry forward (printed bulletin PR 2b; PR 2 planning answer 5), run by the
 * Bulletin step and Review & send, the two steps that show or print the
 * bulletin. While carrying is due for the draft (`shouldCarry`: not a saved
 * service, no save with an unknown outcome, a real date, a music or
 * announcement box not yet typed in or kept, not yet looked up for this
 * date), it reads last week's bulletin
 * (`GET /services/previous-bulletin?before=<date>`) and carries its music and
 * announcements into the untouched boxes through `autoUpdate` (stamped 1 ms
 * after the draft it changes, so it never outranks typing in another tab),
 * checking again inside the recipe against the latest draft. It applies
 * only an answer fetched after it mounted, never a cached one (2b-2 build
 * review I1). A failed lookup stays reported (`failed`) until a retry
 * succeeds, typing in a box included. It also applies "Save as new service" (`followSaveMode`): a
 * saved service on another date has its boxes marked to check and this
 * week's people, leaders and texts emptied. Only the visible tab changes the
 * draft, as the lectionary fill (`usePageVisible`).
 */
import { useEffect } from "react";

import { usePageVisible } from "@/components/builder/lectionary-sync";
import { applyCarry, followSaveMode, shouldCarry } from "@/lib/draft/bulletin";
import { useDraft } from "@/lib/draft/context";
import { usePreviousBulletin } from "@/lib/queries/services";

export function useBulletinCarry(): { failed: boolean; fetching: boolean; retry: () => void } {
  const { draft, autoUpdate } = useDraft();
  const date = draft.readings.date_iso;
  const due = shouldCarry(draft);
  const query = usePreviousBulletin(date, due);
  const visible = usePageVisible();
  // Only an answer fetched since this mount, and not being fetched again: a
  // cached one may be from before last week's service was saved again
  // (2b-2 build review I1).
  const data = query.isFetchedAfterMount && !query.isFetching ? query.data : undefined;
  const copyDue = followSaveMode(draft) !== draft;

  useEffect(() => {
    if (!due || !visible || data === undefined) return;
    autoUpdate((d) => applyCarry(d, data, date));
  }, [due, visible, data, date, autoUpdate]);

  useEffect(() => {
    if (copyDue && visible) autoUpdate(followSaveMode);
  }, [copyDue, visible, autoUpdate]);

  return { failed: due && query.isError, fetching: due && query.isFetching, retry: () => void query.refetch() };
}
