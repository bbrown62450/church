"use client";

import type { Ref } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { editOccasion, selectedSetIndex } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { OCCASION_MAX } from "@/lib/draft/status";

/**
 * The name of this date's set the draft shows (`selectedSetIndex`: the set
 * equal to its lines, else the stored index), when that date's lookup is
 * loaded. Found by the lines first, so a refetch that lists the sets in
 * another order never names the wrong one.
 */
export function readingSetName(d: DraftV1, lect: Lectionary | undefined): string | null {
  if (!lect) return null;
  const index = selectedSetIndex(d, lect);
  return index === null ? null : (lect.reading_sets[index]?.name ?? null);
}

/** The caption under Occasion (S UX item 4 table). */
export function occasionCaption(d: DraftV1, lect: Lectionary | undefined): string | null {
  const r = d.readings;
  switch (r.fields_origin) {
    case "lectionary":
      // Lectionary fields hold the set's own name as the occasion.
      return `From the Revised Common Lectionary: ${r.occasion}`;
    case "user": {
      if (r.reading_set?.date_iso !== r.date_iso) return "Entered by you";
      const name = readingSetName(d, lect);
      return name ? `Edited from the lectionary (${name})` : "Edited from the lectionary";
    }
    case "archive":
      return "From the saved service";
    default:
      return null;
  }
}

/** Occasion (S UX item 4): printed as the bulletin's title; 300 characters at most. */
export function OccasionField({ lect, inputRef }: { lect: Lectionary | undefined; inputRef?: Ref<HTMLInputElement> }) {
  const { draft, update } = useDraft();
  const value = draft.readings.occasion;
  const tooLong = value.length > OCCASION_MAX;
  const caption = occasionCaption(draft, lect);
  const describedBy = ["occasion-help", caption ? "occasion-caption" : null, tooLong ? "occasion-error" : null]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="grid gap-2">
      <Label htmlFor="occasion">Occasion</Label>
      <p id="occasion-help" className="text-sm text-muted-foreground">
        Printed as the bulletin&apos;s title. Filled from the lectionary; edit if needed.
      </p>
      <Input
        id="occasion"
        ref={inputRef}
        value={value}
        placeholder="e.g. Third Sunday of Easter"
        aria-describedby={describedBy}
        aria-invalid={tooLong ? true : undefined}
        onChange={(event) => {
          const next = event.target.value;
          update((d) => editOccasion(d, next));
        }}
        className="h-11"
      />
      {tooLong ? (
        <p id="occasion-error" className="text-sm text-destructive">
          Too long (max 300 characters).
        </p>
      ) : null}
      {caption ? (
        <p id="occasion-caption" className="text-xs text-muted-foreground">
          {caption}
        </p>
      ) : null}
    </div>
  );
}
