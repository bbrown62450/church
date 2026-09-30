/**
 * The selected hymnal (S Toolbar): resolved only from a loaded `GET /hymnals`
 * answer, never from missing data. The step never writes the result back to
 * the draft, so a vanished code never marks a service dirty on its own.
 */
import type { Hymnals } from "@/lib/api/types";

export type SelectedHymnal = {
  /** The hymnal the list, matches and suggestions use; null only when the church has no hymnals. */
  code: string | null;
  /** True when the stored code is no longer one of the church's hymnals. */
  stale: boolean;
};

export function selectHymnal(stored: string | null, hymnals: Hymnals): SelectedHymnal {
  if (stored !== null && hymnals.items.some((item) => item.code === stored)) return { code: stored, stale: false };
  return { code: hymnals.effective_hymnal, stale: stored !== null };
}
