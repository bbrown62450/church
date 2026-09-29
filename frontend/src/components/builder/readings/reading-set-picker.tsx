"use client";

import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { Lectionary } from "@/lib/api/types";

/**
 * The set switcher (S UX item 2, "Several sets"): one card per set, keyed by
 * index, so two sets with the same name stay distinct. `selected` is
 * `selectedSetIndex` (the set equal to the draft's lines, else the stored
 * index for this date, else none).
 */
export function ReadingSetPicker({
  lect,
  selected,
  onChoose,
}: {
  lect: Lectionary;
  selected: number | null;
  onChoose: (index: number) => void;
}) {
  return (
    <div className="grid gap-2">
      <p id="reading-sets-legend" className="text-sm font-medium">
        This date has more than one set of readings
      </p>
      <RadioGroup
        aria-labelledby="reading-sets-legend"
        value={selected === null ? "" : String(selected)}
        onValueChange={(value) => onChoose(Number(value))}
      >
        {lect.reading_sets.map((set, index) => (
          <label
            key={index}
            className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border p-3 has-data-checked:border-primary"
          >
            <RadioGroupItem value={String(index)} className="mt-0.5" />
            <span className="grid min-w-0 gap-0.5">
              <span className="text-sm font-medium">{set.name}</span>
              <span className="text-sm break-words text-muted-foreground">{set.scriptures.join(" · ")}</span>
            </span>
          </label>
        ))}
      </RadioGroup>
    </div>
  );
}
