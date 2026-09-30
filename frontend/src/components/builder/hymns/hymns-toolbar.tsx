"use client";

import type { ReactNode } from "react";

import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import type { Hymnals } from "@/lib/api/types";

/** "4 hymns are hidden." (S Toolbar); "1 hymn is hidden." for one (plan clarification 13). */
export function hiddenCountText(n: number): string {
  return n === 1 ? "1 hymn is hidden." : `${n} hymns are hidden.`;
}

/** The toolbar while `GET /hymnals` loads (S "Whole-step states": skeletons, no spinner; plan clarification 7). */
export function ToolbarSkeleton() {
  return (
    <div role="status" aria-label="Loading the hymnal" className="grid gap-3">
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-11 w-full" />
    </div>
  );
}

/**
 * The Hymnal select, shown only with 2+ hymnals, and the notes that go with
 * the selected hymnal (S Toolbar): a stored code the church no longer has
 * (shown even when the select is hidden), and a hymnal with no scripture
 * references. Choosing writes the draft's hymnal; picks keep their own.
 */
export function HymnalPicker({
  hymnals,
  selected,
  stale,
  storedCode,
  onChange,
}: {
  hymnals: Hymnals;
  selected: string;
  stale: boolean;
  storedCode: string | null;
  onChange: (code: string) => void;
}) {
  const items: Record<string, string> = Object.fromEntries(
    hymnals.items.map((h) => [h.code, `${h.code} · ${h.hymn_count} hymns`]),
  );
  const current = hymnals.items.find((h) => h.code === selected);
  return (
    <div className="grid gap-2">
      {hymnals.items.length >= 2 ? (
        <>
          <Label id="hymnal-label">Hymnal</Label>
          <Select
            value={selected}
            items={items}
            onValueChange={(value) => {
              if (typeof value === "string") onChange(value);
            }}
          >
            <SelectTrigger
              aria-labelledby="hymnal-label"
              aria-describedby="hymnal-help"
              className="h-11 w-full sm:w-80 data-[size=default]:h-11"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {hymnals.items.map((h) => (
                <SelectItem key={h.code} value={h.code}>
                  {items[h.code]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p id="hymnal-help" className="text-sm text-muted-foreground">
            Which hymnal to choose hymns from for this service.
          </p>
        </>
      ) : null}
      {stale && storedCode ? (
        <p className="text-sm">
          {storedCode} is no longer in your church&apos;s hymnals. Showing {selected} instead.
        </p>
      ) : null}
      {current && current.scripture_ref_count === 0 ? (
        <p className="text-sm text-muted-foreground">
          {current.code} has no scripture references, so scripture matches and AI response picks will be weaker.
        </p>
      ) : null}
    </div>
  );
}

/**
 * "Exclude hymns used within 12 weeks" (S Toolbar). It writes only
 * `exclude_recent`; it never changes a slot or an idea (AC12). Disabled when
 * the draft's date is not valid.
 */
export function ExcludeSwitch({
  on,
  hidden,
  dateValid,
  onChange,
}: {
  on: boolean;
  /** Hymns in the selected hymnal used within 12 weeks of the service. */
  hidden: number;
  dateValid: boolean;
  onChange: (on: boolean) => void;
}) {
  return (
    <div className="grid gap-1">
      <div className="flex min-h-11 items-center gap-3">
        <Switch
          id="exclude-recent"
          checked={on}
          disabled={!dateValid}
          onCheckedChange={(checked) => onChange(checked)}
          aria-describedby="exclude-recent-help"
        />
        <Label htmlFor="exclude-recent">Exclude hymns used within 12 weeks</Label>
      </div>
      <p id="exclude-recent-help" className="text-sm text-muted-foreground">
        {dateValid
          ? "Hides hymns sung in the 12 weeks before this service or planned in the 12 weeks after it."
          : "Pick a valid date in step 1 to check recent use."}
        {dateValid && on && hidden > 0 ? ` ${hiddenCountText(hidden)}` : null}
      </p>
    </div>
  );
}

/** The toolbar's frame: the hymnal, the switch, then Suggest (slice 3b T10). */
export function HymnsToolbar({ children }: { children: ReactNode }) {
  return <div className="grid gap-4 rounded-lg border p-4">{children}</div>;
}
