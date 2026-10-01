"use client";

import { ChevronDownIcon } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Switch } from "@/components/ui/switch";
import type { CommunionBlock, LiturgyConfig } from "@/lib/api/types";
import { formatServiceDate, isFirstSundayOfMonth } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { restoreCommunionDefault, setCommunion } from "@/lib/liturgy/cards";
import { cn } from "@/lib/utils";

function Block({ block }: { block: CommunionBlock }) {
  switch (block.style) {
    case "heading1":
      return <h4 className="font-semibold">{block.text}</h4>;
    case "heading2":
      return <h5 className="pt-2 font-medium">{block.text}</h5>;
    case "response":
      return <p className="font-semibold">{block.text}</p>;
    case "text":
      return <p>{block.text}</p>;
    default:
      return null;
  }
}

/**
 * The communion card (S UX "Communion card"; BC-10, BC-11): the switch, a
 * helper that says why it is on or off (the first-Sunday rule while it is the
 * default, "You changed this." or "Set from the saved service." with "Use
 * default"), and the fixed communion text, read-only, behind "Show communion
 * text". It sits in the outline after the Second Hymn. After "Use default"
 * (which then goes) focus moves to the switch. Its heading can take focus
 * (`data-card-heading`), like every card's, for Remove's focus move.
 */
export function CommunionCard({ communion }: { communion: LiturgyConfig["communion"] }) {
  const { draft, update } = useDraft();
  const [open, setOpen] = useState(false);
  const switchRef = useRef<HTMLButtonElement>(null);
  const l = draft.liturgy;
  const date = draft.readings.date_iso;
  const helper =
    l.communion_origin === "default"
      ? isFirstSundayOfMonth(date)
        ? `On by default — ${formatServiceDate(date)} is the first Sunday of the month.`
        : "Off by default — it's on by default only on the first Sunday of the month."
      : l.communion_origin === "user"
        ? "You changed this."
        : "Set from the saved service.";

  return (
    <section id="communion" aria-labelledby="communion-title" className="grid scroll-mt-24 gap-3 rounded-lg border p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Switch
          ref={switchRef}
          checked={l.include_communion}
          onCheckedChange={(checked) => update((d) => setCommunion(d, checked))}
          aria-labelledby="communion-title"
          className="after:-inset-y-3.5"
        />
        <h3 id="communion-title" tabIndex={-1} data-card-heading="" className="min-w-0 flex-1 text-base font-medium outline-none">
          {communion.toggle_label}
        </h3>
      </div>
      <p className="flex flex-wrap items-center gap-x-1 text-sm text-muted-foreground">
        {helper}
        {l.communion_origin === "default" ? null : (
          <Button
            variant="link"
            className="h-11 px-1 md:h-auto"
            onClick={() => {
              update(restoreCommunionDefault);
              switchRef.current?.focus(); // this button goes
            }}
          >
            Use default
          </Button>
        )}
      </p>
      <Collapsible open={open} onOpenChange={setOpen} className="grid gap-2">
        <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
          <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
          Show communion text
        </CollapsibleTrigger>
        <CollapsibleContent className="grid gap-2">
          <div className="grid gap-2 rounded-md bg-muted/40 p-3 text-sm">
            {communion.blocks.map((block, i) => (
              <Block key={i} block={block} />
            ))}
          </div>
          <p className="text-xs text-muted-foreground">Printed after the Second Hymn. The same text is used for every service.</p>
        </CollapsibleContent>
      </Collapsible>
    </section>
  );
}
