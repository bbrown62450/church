"use client";

/**
 * `value`, trailing its changes by `delayMs` (S "useLectionarySync"): it
 * starts at the current value, with no delay on mount, and only the last of
 * several quick changes comes through. The builder looks up the lectionary
 * for the debounced date, so a date typed segment by segment is looked up
 * (and charged to the rate limit) once.
 */
import { useEffect, useState } from "react";

export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}
