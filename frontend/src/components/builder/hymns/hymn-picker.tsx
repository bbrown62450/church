"use client";

import { SearchCombobox, type SearchResult } from "@/components/app/search-combobox";
import type { Hymn } from "@/lib/api/types";
import { filterHymns, PICKER_LIMIT } from "@/lib/hymns/filter";
import { hymnText, recentUseLabel } from "@/lib/hymns/labels";

import { HymnLabel } from "./hymn-label";

/** The picker's rows and the hints in its footer (S Picker "Hints in the list footer"). */
export function pickerSearch(items: readonly Hymn[], query: string, excludeRecent: boolean): SearchResult<Hymn> {
  const result = filterHymns(items, query, { excludeRecent });
  const q = query.trim();
  const footer: string[] = [];
  if (q === "") footer.push(`Type to search ${result.totalMatches} hymns.`);
  else if (result.totalMatches === 0) footer.push(`No hymns match “${q}”.`);
  else if (result.totalMatches > PICKER_LIMIT) {
    footer.push(`Showing ${PICKER_LIMIT} of ${result.totalMatches} — keep typing to narrow.`);
  }
  if (result.hiddenRecent === 1) footer.push("1 more used within 12 weeks is hidden.");
  else if (result.hiddenRecent > 1) footer.push(`${result.hiddenRecent} more used within 12 weeks are hidden.`);
  return { shown: result.shown, footer };
}

/**
 * A slot's hymn picker (S "Picker"): the selected hymnal's list through
 * `SearchCombobox`, ranked by `filterHymns`. Rows show "#n Title", the year
 * badge of a newer hymn and, when Exclude is off, a "Used Sep 7" or "Planned
 * Oct 18" badge. While the list loads the input is disabled with "Loading hymnal…".
 */
export function HymnPicker({
  label,
  list,
  excludeRecent,
  serviceDateIso,
  showHymnal,
  onChoose,
  autoFocus = false,
  onDismiss,
}: {
  label: string;
  /** The selected hymnal's hymns; undefined while they load. */
  list: readonly Hymn[] | undefined;
  excludeRecent: boolean;
  serviceDateIso: string;
  showHymnal: boolean;
  onChoose: (h: Hymn) => void;
  autoFocus?: boolean;
  onDismiss?: () => void;
}) {
  const loading = list === undefined;
  return (
    <SearchCombobox<Hymn>
      label={label}
      labelHidden
      items={list ?? []}
      search={(query) => pickerSearch(list ?? [], query, excludeRecent)}
      itemKey={(h) => h.id}
      itemText={hymnText}
      renderItem={(h) => (
        <HymnLabel
          hymn={h}
          showHymnal={showHymnal}
          recentBadge={!excludeRecent && h.recent_use_on ? recentUseLabel(h.recent_use_on, serviceDateIso) : null}
        />
      )}
      value={null}
      onValueChange={onChoose}
      placeholder={loading ? "Loading hymnal…" : "Search by title or number"}
      disabled={loading}
      autoFocus={autoFocus}
      onDismiss={onDismiss}
    />
  );
}
