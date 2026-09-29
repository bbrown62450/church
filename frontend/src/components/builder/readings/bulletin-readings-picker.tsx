"use client";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useDraft } from "@/lib/draft/context";
import { effectivePicks, setPick } from "@/lib/draft/readings";
import { cleanLines, pickerOptions } from "@/lib/scripture-refs";

function PickSelect({
  side,
  label,
  options,
  pick,
  automatic,
}: {
  side: "ot" | "nt";
  label: string;
  options: string[];
  /** The explicit pick when it is still an option; "" means automatic. */
  pick: string;
  /** What automatic resolves to now, or null. */
  automatic: string | null;
}) {
  const { update } = useDraft();
  const id = `bulletin-${side}`;
  const items = Object.fromEntries(options.map((option) => [option, option]));
  return (
    <div className="grid gap-2">
      <Label id={`${id}-label`}>{label}</Label>
      <Select
        value={pick === "" ? null : pick}
        items={items}
        disabled={options.length === 0}
        onValueChange={(value) => {
          if (typeof value === "string") update((d) => setPick(d, side, value));
        }}
      >
        <SelectTrigger aria-labelledby={`${id}-label`} className="h-11 w-full min-w-0 data-[size=default]:h-11">
          <SelectValue placeholder={automatic ? `Automatic: ${automatic}` : "None — choose one"} />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option}>
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {pick !== "" ? (
        <div>
          <Button
            type="button"
            variant="link"
            className="h-11 px-0"
            aria-label={`Use automatic ${label}`}
            onClick={() => update((d) => setPick(d, side, ""))}
          >
            Use automatic
          </Button>
        </div>
      ) : null}
    </div>
  );
}

/**
 * "Bulletin readings" (S UX item 7): one Old Testament and one New Testament
 * reading. Options come from `pickerOptions` (OT: ot, psalm and unknown; NT:
 * nt only); "" is automatic, shown as "Automatic: {ref}" from the same
 * `resolveReadings` the payload and (from 5a) the Word file use, so a Psalm is
 * never the automatic NT and a stale pick counts as automatic.
 */
export function BulletinReadingsPicker() {
  const { draft } = useDraft();
  const options = pickerOptions(cleanLines(draft.readings.scriptures));
  const picks = effectivePicks(draft);
  return (
    <section aria-labelledby="bulletin-heading" className="grid gap-4">
      <div className="grid gap-1">
        <h2 id="bulletin-heading" className="text-base font-medium">
          Bulletin readings
        </h2>
        <p className="text-sm text-muted-foreground">
          The bulletin prints one Old Testament and one New Testament reading.
        </p>
      </div>
      <PickSelect
        side="ot"
        label="Old Testament reading"
        options={options.ot}
        pick={picks.otAuto ? "" : (picks.ot ?? "")}
        automatic={picks.otAuto ? picks.ot : null}
      />
      <PickSelect
        side="nt"
        label="New Testament reading"
        options={options.nt}
        pick={picks.ntAuto ? "" : (picks.nt ?? "")}
        automatic={picks.ntAuto ? picks.nt : null}
      />
    </section>
  );
}
