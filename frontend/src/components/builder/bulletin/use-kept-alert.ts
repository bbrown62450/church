"use client";

import { useEffect, useState } from "react";

/**
 * A failed load's alert with Try again on the Bulletin step (2b-2 build
 * review M2). A retry of a load that has no data puts the query back to
 * pending, so an alert shown only on error would unmount with the focused
 * Try again in it and focus would fall to the page. The alert is `shown`
 * while it failed, and while a retry from it runs; once a retry succeeds and
 * the alert goes, focus moves to `focusId` (unless it already moved
 * elsewhere). A retry that fails again keeps the alert and its button.
 */
export function useKeptAlert(
  failed: boolean,
  fetching: boolean,
  refetch: () => unknown,
  focusId: string,
): { shown: boolean; retry: () => void } {
  const [retrying, setRetrying] = useState(false);
  const [recovered, setRecovered] = useState(0);
  if (retrying && !fetching) {
    // The retry settled: adjusted while rendering, not in an effect.
    setRetrying(false);
    if (!failed) setRecovered((n) => n + 1);
  }
  useEffect(() => {
    if (recovered === 0) return;
    const active = document.activeElement;
    if (active === null || active === document.body) document.getElementById(focusId)?.focus();
  }, [recovered, focusId]);
  return {
    shown: failed || (retrying && fetching),
    retry: () => {
      setRetrying(true);
      void refetch();
    },
  };
}
