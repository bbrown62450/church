"use client";

import { useEffect, useState } from "react";

/** After this long a running AI request adds "Still working — this can take up to a minute." (F §1.8, §4.8). */
export const STILL_WORKING_MS = 8_000;

export const STILL_WORKING = "Still working — this can take up to a minute.";

/** True once `active` has been true for `STILL_WORKING_MS`; false again as soon as it is not. */
export function useStillWorking(active: boolean): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => setSlow(true), STILL_WORKING_MS);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [active]);
  return active && slow;
}
