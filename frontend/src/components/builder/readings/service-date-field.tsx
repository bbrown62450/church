"use client";

import { useState } from "react";

import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  formatLongDate,
  formatShortDate,
  inSupportedRange,
  isSunday,
  isValidDateIso,
  nextSunday,
} from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { setDate } from "@/lib/draft/readings";

/**
 * The "Service date" card (S UX item 1). Every date is allowed; an empty or
 * impossible one is stored as "" and asks for a date, and a year outside
 * 1900-2199 is not looked up. "Use next Sunday" puts back the default date
 * (origin `default`, so it is not counted as the user's choice). `today` is
 * the church's calendar day.
 *
 * While a date is typed (owner answer F, 2026-09-29): the field shows what
 * was typed, even when it stores "" (a fifth year digit), so it never
 * empties under the user's fingers; it shows the draft's date again when the
 * date changes elsewhere ("Use next Sunday", another tab, "New service"). The
 * range message waits until the date has settled (the lookup's 400 ms).
 */
export function ServiceDateField({ today }: { today: string }) {
  const { draft, update } = useDraft();
  const { settled } = useLectionaryLookup();
  const iso = draft.readings.date_iso;
  // What the input shows, and the stored date it was typed for.
  const [typed, setTyped] = useState<{ raw: string; stored: string } | null>(null);
  const shown = typed !== null && typed.stored === iso ? typed.raw : iso;
  const next = nextSunday(today);
  const valid = isValidDateIso(iso);
  const inRange = valid && inSupportedRange(iso);
  const problem = !valid
    ? "Choose a service date."
    : !inRange && settled
      ? "Enter a date between 1900 and 2199."
      : null;

  return (
    <div className="grid gap-2 rounded-lg border p-4">
      <Label htmlFor="service-date">Service date</Label>
      <p id="service-date-help" className="text-sm text-muted-foreground">
        Readings and the occasion load automatically for this date.
      </p>
      <Input
        id="service-date"
        type="date"
        value={shown}
        min="1900-01-01"
        max="2199-12-31"
        aria-describedby={problem ? "service-date-help service-date-problem" : "service-date-help"}
        aria-invalid={problem ? true : undefined}
        onChange={(event) => {
          const raw = event.target.value;
          const stored = isValidDateIso(raw) ? raw : "";
          setTyped({ raw, stored });
          update((d) => setDate(d, stored));
        }}
        className="h-11 w-full sm:w-56"
      />
      {valid ? <p className="font-medium">{formatLongDate(iso)}</p> : null}
      {problem ? (
        <p id="service-date-problem" className="text-sm text-destructive">
          {problem}
        </p>
      ) : null}
      {inRange && iso < today ? <p className="text-sm text-muted-foreground">This date has passed.</p> : null}
      {inRange && !isSunday(iso) ? (
        <p className="text-sm">
          Not a Sunday. We&apos;ll look for this day&apos;s own readings, such as Ash Wednesday, Christmas Eve or Good
          Friday.
        </p>
      ) : null}
      {iso !== next ? (
        <div>
          <Button
            type="button"
            variant="link"
            className="h-11 px-0"
            onClick={() => update((d) => setDate(d, next, "default"))}
          >
            Use next Sunday ({formatShortDate(next)})
          </Button>
        </div>
      ) : null}
    </div>
  );
}
