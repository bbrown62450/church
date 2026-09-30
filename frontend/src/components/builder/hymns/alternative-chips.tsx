"use client";

import { Button } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import type { HymnPick, Slot } from "@/lib/draft/schema";
import { chipName, recentUseLabel } from "@/lib/hymns/labels";
import { reconcilePick } from "@/lib/hymns/picks";

import { HymnLabel } from "./hymn-label";

/**
 * "Other ideas" under a slot (S "Other ideas (AI chips)"): the AI's other
 * hymns for this date, each a touch-size chip. A chip shows its live hymn
 * once its hymnal's list has loaded (with "Used Sep 7" and "Written {year}"
 * badges), and is hidden when that list no longer has it. A tap swaps it with
 * the slot's pick, so a second tap swaps back.
 */
export function AlternativeChips({
  slot,
  ideas,
  lists,
  fallbackHymnal,
  serviceDateIso,
  showHymnal,
  onSwap,
}: {
  slot: Slot;
  ideas: readonly HymnPick[];
  lists: ReadonlyMap<string, readonly Hymn[] | undefined>;
  fallbackHymnal: string | null;
  serviceDateIso: string;
  showHymnal: boolean;
  onSwap: (hymnId: string) => void;
}) {
  const shown = ideas.flatMap((idea) => {
    const reconciled = reconcilePick(idea, lists, fallbackHymnal);
    if (reconciled.status === "missing" || idea.hymn_id === null) return [];
    return [{ idea, hymnId: idea.hymn_id, live: reconciled.status === "ok" ? reconciled.live : null }];
  });
  if (shown.length === 0) return null;
  return (
    <div className="grid gap-1.5">
      <p className="text-sm font-medium">Other ideas</p>
      <div role="group" aria-label={`Other ideas for the ${slot} hymn`} className="flex flex-wrap gap-2">
        {shown.map(({ idea, hymnId, live }) => (
          <Button
            key={hymnId}
            variant="secondary"
            size="touch"
            className="max-w-full min-w-0"
            aria-label={chipName(live ?? { title: idea.title, newer_than_preferred: false, text_year: null }, slot)}
            onClick={() => onSwap(hymnId)}
          >
            <HymnLabel
              hymn={live ?? idea}
              showHymnal={showHymnal}
              recentBadge={live?.recent_use_on ? recentUseLabel(live.recent_use_on, serviceDateIso) : null}
              truncate
            />
          </Button>
        ))}
      </div>
    </div>
  );
}
