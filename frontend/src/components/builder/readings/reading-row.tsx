"use client";

import { Badge, badgeVariants } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { classify, splitAlternatives, type Classification, type Testament } from "@/lib/scripture-refs";
import { cn } from "@/lib/utils";

import { PassageText } from "./passage-text";
import { MAX_LINE } from "./scripture-lines-field";

const BADGE_TEXT: Record<Testament, string> = { ot: "OT", psalm: "Psalm", nt: "NT" };

/**
 * OT, Psalm or NT; an unknown book is "?" with the tooltip "Book not
 * recognized" (also its accessible name), at least 24 px square on phones.
 */
function TestamentBadge({ testament }: { testament: Classification }) {
  if (testament !== "unknown") return <Badge variant="secondary">{BADGE_TEXT[testament]}</Badge>;
  return (
    <Tooltip>
      <TooltipTrigger
        aria-label="Book not recognized"
        className={cn(badgeVariants({ variant: "outline" }), "h-6 min-w-6 sm:h-5 sm:min-w-0")}
      >
        ?
      </TooltipTrigger>
      <TooltipContent>Book not recognized</TooltipContent>
    </Tooltip>
  );
}

/**
 * One reading (S UX item 6): the reference, a badge per " or " alternative,
 * and "Show text" / "Hide text", named with the reference for screen readers
 * ("Show text: Mark 1:1-8"). The text loads only while the row is open. A
 * line over 200 characters cannot be opened and is never sent.
 */
export function ReadingRow({
  reference,
  translation,
  open,
  onOpenChange,
}: {
  reference: string;
  translation: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const tooLong = reference.length > MAX_LINE;
  const action = open && !tooLong ? "Hide text" : "Show text";
  return (
    <li className="grid gap-2 border-b py-3 last:border-b-0">
      <div className="flex flex-wrap items-start gap-2">
        <span className="min-w-0 flex-1 wrap-anywhere">{reference}</span>
        <span className="flex flex-wrap gap-1">
          {splitAlternatives(reference).map((alternative, i) => (
            <TestamentBadge key={`${i}:${alternative}`} testament={classify(alternative)} />
          ))}
        </span>
      </div>
      <Collapsible open={open && !tooLong} onOpenChange={onOpenChange} disabled={tooLong}>
        <CollapsibleTrigger
          disabled={tooLong}
          aria-label={`${action}: ${reference}`}
          className={cn(
            buttonVariants({ variant: "outline", size: "touch" }),
            "justify-self-start aria-disabled:pointer-events-none aria-disabled:opacity-50",
          )}
        >
          {action}
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-2 wrap-anywhere">
          <PassageText reference={reference} translation={translation} />
        </CollapsibleContent>
      </Collapsible>
    </li>
  );
}
