"use client";

import { ChevronDownIcon } from "lucide-react";
import Link from "next/link";
import { useState, type FormEvent } from "react";

import { ErrorState } from "@/components/app/error-state";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import type { HymnalSummary, HymnMatch } from "@/lib/api/types";
import { SLOTS, type Slot } from "@/lib/draft/schema";
import { recentUseLabel, SLOT_META } from "@/lib/hymns/labels";
import { buildMatchRefs, MAX_REF_LENGTH } from "@/lib/hymns/match-request";
import { useScriptureMatches } from "@/lib/queries/hymns";
import { cn } from "@/lib/utils";

import { HymnLabel } from "./hymn-label";

/** Open from `md` (48rem), closed below it, as the section first renders (S; plan clarification 19). */
function openAtFirst(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(min-width: 48rem)").matches
  );
}

/**
 * "{k} recently used matches are hidden." (S), or "… are shown." once shown;
 * "1 recently used match is hidden." for one (plan clarification 13).
 */
function recentMatchesText(k: number, shown: boolean): string {
  const state = shown ? "shown" : "hidden";
  return k === 1 ? `1 recently used match is ${state}.` : `${k} recently used matches are ${state}.`;
}

/** One match: its label (with "Used Sep 7" when it is shown although recently used), what it matched, and Add. */
function MatchRow({
  match,
  serviceDateIso,
  showHymnal,
  onAdd,
}: {
  match: HymnMatch;
  serviceDateIso: string;
  showHymnal: boolean;
  onAdd: (slot: Slot) => void;
}) {
  const recent = match.recent_use_on ? recentUseLabel(match.recent_use_on, serviceDateIso) : null;
  return (
    <li className="flex items-center gap-2 py-1.5">
      <div className="grid min-w-0 flex-1 gap-0.5">
        <HymnLabel hymn={match} showHymnal={showHymnal} recentBadge={recent} listen />
        <p className="text-xs text-muted-foreground wrap-anywhere">Matches {match.matched_refs.join(", ")}</p>
      </div>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Add ${match.title}`}
          className={cn(buttonVariants({ variant: "outline", size: "touch" }), "shrink-0")}
        >
          Add
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-auto min-w-44">
          {SLOTS.map((slot) => (
            <DropdownMenuItem key={slot} onClick={() => onAdd(slot)} className="min-h-11 md:min-h-8">
              {SLOT_META[slot].title}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </li>
  );
}

/**
 * "Hymns for the readings" (S `ScriptureMatches`): the draft's scriptures and
 * an extra reference typed here (component state only), matched in the
 * selected hymnal. The request runs by itself whenever the references, the
 * hymnal or the date change, also while the section is closed, so its count
 * shows. Results come in two groups; each row's Add puts the hymn in a slot.
 * With Exclude on, recently used matches are hidden behind "Show them", a
 * local toggle ("Hide them" puts them away again).
 */
export function ScriptureMatches({
  scriptures,
  hymnal,
  recentForDate,
  serviceDateIso,
  excludeRecent,
  showHymnal,
  onAdd,
}: {
  scriptures: readonly string[];
  /** The selected hymnal, with its scripture count. */
  hymnal: HymnalSummary;
  recentForDate: string | null;
  serviceDateIso: string;
  excludeRecent: boolean;
  showHymnal: boolean;
  onAdd: (slot: Slot, match: HymnMatch) => void;
}) {
  const [open, setOpen] = useState(openAtFirst);
  const [typed, setTyped] = useState("");
  const [extra, setExtra] = useState("");
  const [showRecent, setShowRecent] = useState(false);
  const refs = buildMatchRefs(scriptures, extra);
  const searchable = hymnal.scripture_ref_count > 0;
  const query = useScriptureMatches({ refs, hymnal: hymnal.code, recentForDate, enabled: searchable });
  const data = searchable && refs.length > 0 ? query.data : undefined;
  const hideRecent = excludeRecent && !showRecent;
  const all = data?.items ?? [];
  const items = hideRecent ? all.filter((m) => m.recent_use_on === null) : all;
  const recentCount = excludeRecent ? all.filter((m) => m.recent_use_on !== null).length : 0;
  const groups = [
    { title: "Matches the readings", items: items.filter((m) => m.strength === "passage") },
    { title: "Same chapter", items: items.filter((m) => m.strength === "chapter") },
  ].filter((g) => g.items.length > 0);

  function submit(event: FormEvent) {
    event.preventDefault();
    setExtra(typed);
  }

  let body;
  if (!searchable) {
    body = (
      <p className="text-sm text-muted-foreground">
        {hymnal.code} has no scripture references, so it can&apos;t be searched by scripture.
      </p>
    );
  } else if (refs.length === 0) {
    body = (
      <p className="text-sm text-muted-foreground">
        Add the readings in step 1, or type a scripture reference here.{" "}
        <Link
          href="/builder/readings"
          className="inline-flex min-h-11 items-center font-medium text-foreground underline underline-offset-4"
        >
          Go to readings
        </Link>
      </p>
    );
  } else if (query.isError && !data) {
    body = (
      <ErrorState
        error={query.error}
        message="Couldn't search the hymnal."
        retrying={query.isFetching}
        onRetry={() => void query.refetch()}
      />
    );
  } else if (!data) {
    body = (
      <div role="status" aria-label="Searching the hymnal" className="grid gap-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    );
  } else {
    body = (
      <div className="grid gap-3">
        {data.unparsed_refs.map((ref) => (
          <p key={ref} className="text-sm text-muted-foreground wrap-anywhere">
            Couldn&apos;t read “{ref}” as a scripture reference.
          </p>
        ))}
        {all.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No hymns in {hymnal.code} match these readings. Try a shorter reference, such as “Matthew 17”.
          </p>
        ) : null}
        {groups.map((group) => (
          <div key={group.title} className="grid gap-1">
            <h3 className="text-sm font-medium">{group.title}</h3>
            <ul className="divide-y">
              {group.items.map((match) => (
                <MatchRow
                  key={match.id}
                  match={match}
                  serviceDateIso={serviceDateIso}
                  showHymnal={showHymnal}
                  onAdd={(slot) => onAdd(slot, match)}
                />
              ))}
            </ul>
          </div>
        ))}
        {recentCount > 0 ? (
          <p className="text-sm text-muted-foreground">
            {recentMatchesText(recentCount, showRecent)}{" "}
            <Button variant="link" className="h-11 px-0" onClick={() => setShowRecent((shown) => !shown)}>
              {showRecent ? "Hide them" : "Show them"}
            </Button>
          </p>
        ) : null}
      </div>
    );
  }

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="grid gap-3 rounded-lg border p-4">
      <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-base font-medium">
        <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
        <span>Hymns for the readings</span>
        {data ? (
          <>
            <Badge variant="secondary">{items.length}</Badge>
            <span className="sr-only">{items.length === 1 ? " match" : " matches"}</span>
          </>
        ) : null}
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-3">
        <form onSubmit={submit} className="grid gap-1.5">
          <Label htmlFor="extra-scripture">Additional scripture</Label>
          <div className="flex gap-2">
            <Input
              id="extra-scripture"
              value={typed}
              maxLength={MAX_REF_LENGTH}
              placeholder="e.g. Matthew 17"
              className="h-11"
              onChange={(event) => setTyped(event.target.value)}
            />
            <Button type="submit" variant="outline" size="touch">
              Search
            </Button>
          </div>
        </form>
        {body}
      </CollapsibleContent>
    </Collapsible>
  );
}
