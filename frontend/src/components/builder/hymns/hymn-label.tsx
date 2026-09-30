"use client";

import { PlayIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { Hymn } from "@/lib/api/types";
import { hymnText, newerYearLabel } from "@/lib/hymns/labels";
import { safeHttpsUrl } from "@/lib/urls";
import { cn } from "@/lib/utils";

/** What a label needs: a live hymn, or a draft snapshot (no link, no year). */
export type LabelHymn = Pick<Hymn, "title" | "number"> & { hymnal: string | null } &
  Partial<Pick<Hymn, "link" | "text_year" | "newer_than_preferred">>;

/**
 * One hymn as the step shows it everywhere (S "Filled slot", "Newer-hymn year
 * label"): "#n Title", then small badges that never shrink (the hymnal when
 * the church has 2+, the recent use, "Written {year}" for a flagged hymn). The
 * row wraps, so at 375 px a long title breaks and the badges move to a second
 * line; only a chip (`truncate`) stays on one line, its title truncating first.
 * With `listen`, a ▶ link to the hymn's Hymnary.org page when the link is
 * https (`safeHttpsUrl`), else none.
 */
export function HymnLabel({
  hymn,
  showHymnal = false,
  recentBadge = null,
  listen = false,
  truncate = false,
}: {
  hymn: LabelHymn;
  showHymnal?: boolean;
  recentBadge?: string | null;
  listen?: boolean;
  truncate?: boolean;
}) {
  const year =
    hymn.newer_than_preferred !== undefined && hymn.text_year !== undefined
      ? newerYearLabel({ newer_than_preferred: hymn.newer_than_preferred, text_year: hymn.text_year })
      : null;
  const href = listen ? safeHttpsUrl(hymn.link) : null;
  return (
    <span className={cn("flex min-w-0 items-center gap-1.5", !truncate && "flex-wrap")}>
      <span className={cn("min-w-0", truncate ? "truncate" : "wrap-anywhere")}>{hymnText(hymn)}</span>
      {showHymnal && hymn.hymnal ? (
        <Badge variant="outline" className="shrink-0">
          {hymn.hymnal}
        </Badge>
      ) : null}
      {recentBadge ? (
        <Badge variant="secondary" className="shrink-0">
          {recentBadge}
        </Badge>
      ) : null}
      {year ? (
        <Badge variant="outline" className="shrink-0 text-muted-foreground">
          {year}
        </Badge>
      ) : null}
      {href ? (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`Listen to ${hymn.title} on Hymnary.org`}
          className="inline-flex size-11 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:text-foreground md:size-8"
        >
          <PlayIcon aria-hidden="true" className="size-4" />
        </a>
      ) : null}
    </span>
  );
}
