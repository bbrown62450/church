/**
 * Tracks overlapping async requests so only the most recent one may apply its result.
 * Call begin() when a request starts; the returned function reports whether that
 * request is still the latest.
 */
export function createLatestTracker() {
  let current = 0;
  return {
    begin(): () => boolean {
      const id = ++current;
      return () => id === current;
    },
  };
}
