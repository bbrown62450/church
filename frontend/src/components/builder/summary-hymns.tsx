"use client";

import { useDraft } from "@/lib/draft/context";
import { SLOTS } from "@/lib/draft/schema";
import { hymnText, SLOT_META } from "@/lib/hymns/labels";

/**
 * The summary's Hymns block (slice 3 S "Builder shell"; F §4.7): the three
 * slots in order, "Opening · #403 Come, Thou Almighty King" or, muted, "No
 * Opening hymn". It reads only the draft's snapshot, so the shell never loads
 * a hymnal on other steps.
 */
export function SummaryHymns() {
  const { draft } = useDraft();
  return (
    <ul className="grid gap-1">
      {SLOTS.map((slot) => {
        const pick = draft.hymns.slots[slot];
        const name = SLOT_META[slot].name;
        return pick ? (
          <li key={slot} className="wrap-anywhere text-foreground">
            {name} · {hymnText(pick)}
          </li>
        ) : (
          <li key={slot}>No {name} hymn</li>
        );
      })}
    </ul>
  );
}
