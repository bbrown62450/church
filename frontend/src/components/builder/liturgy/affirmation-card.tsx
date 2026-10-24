"use client";

import { ChevronDownIcon } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { AffirmationConfig } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { AffirmationChoice } from "@/lib/draft/schema";
import {
  editAffirmationText,
  restoreAffirmationDefault,
  setAffirmationChoice,
  setAffirmationInclude,
} from "@/lib/liturgy/cards";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

import { COUNTER_FROM } from "./section-card";

export const AFFIRMATION_OFF = "Not printed or emailed.";
export const OWN_TEXT_HINT = "Printed in bold for everyone to read together.";
export const OWN_TEXT_BLANK = "Nothing prints until you type it.";
const HELPER = { default: "Your church's default.", user: "You changed this.", archive: "Set from the saved service." } as const;

/**
 * A creed as the printed bulletin prints it: one paragraph (the Apostles'
 * Creed), or one line per sense line (the Nicene Creed), each with a hanging
 * indent so a line that wraps on a phone still reads as one line.
 */
export function CreedText({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="grid rounded-md bg-muted/40 p-3 text-sm">
      {lines.length === 1 ? (
        <p>{text}</p>
      ) : (
        lines.map((line, index) => (
          <p key={index} className="pl-4 -indent-4">
            {line}
          </p>
        ))
      )}
    </div>
  );
}

/**
 * The Affirmation of Faith card (affirmation spec, "The Affirmation card"):
 * the switch ("Include Affirmation of Faith"); while it is on, the choice of
 * the Apostles' Creed, the Nicene Creed or your own text, the chosen creed's
 * text (and credit) behind "Show creed text", or a box for your own text,
 * like a prayer card's; a helper line that says whether it follows the
 * church's default, with "Use church default" when it does not (focus then
 * moves to the switch, as on the communion card). It sits after the Sermon
 * Title. Its heading can take focus (`data-card-heading`), like every card's.
 */
export function AffirmationCard({ config, maxLength }: { config: AffirmationConfig; maxLength: number }) {
  const { draft, update, defaultAffirmation } = useDraft();
  const [open, setOpen] = useState(false);
  const switchRef = useRef<HTMLButtonElement>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const a = draft.liturgy.affirmation;
  const own = a.include && a.choice === "own";
  useAutosize(textRef, a.text, own);
  const chosen = config.choices.find((choice) => choice.key === a.choice);
  // A prayer card's counter (S "Other card rules"): past 18,000 characters, against the limit.
  const showCounter = a.text.length > COUNTER_FROM;

  return (
    <section id="affirmation" aria-labelledby="affirmation-title" className="grid scroll-mt-24 gap-3 rounded-lg border p-4">
      <div className="flex min-w-0 items-center gap-3">
        <Switch
          ref={switchRef}
          checked={a.include}
          onCheckedChange={(checked) => update((d) => setAffirmationInclude(d, checked))}
          aria-labelledby="affirmation-title"
          className="after:-inset-y-3.5"
        />
        <h3 id="affirmation-title" tabIndex={-1} data-card-heading="" className="min-w-0 flex-1 text-base font-medium outline-none">
          {config.toggle_label}
        </h3>
      </div>
      <p className="flex flex-wrap items-center gap-x-1 text-sm text-muted-foreground">
        {a.include ? HELPER[a.origin] : `${AFFIRMATION_OFF} ${HELPER[a.origin]}`}
        {a.origin === "default" ? null : (
          <Button
            variant="link"
            className="h-11 px-1 md:h-auto"
            onClick={() => {
              update((d) => restoreAffirmationDefault(d, defaultAffirmation));
              switchRef.current?.focus(); // this button goes
            }}
          >
            Use church default
          </Button>
        )}
      </p>
      {a.include ? (
        <>
          <RadioGroup
            aria-label={config.title}
            value={a.choice}
            onValueChange={(value) => update((d) => setAffirmationChoice(d, value as AffirmationChoice))}
            className="gap-0"
          >
            {config.choices.map((choice) => (
              <label key={choice.key} className="flex min-h-11 cursor-pointer items-center gap-3 text-sm">
                <RadioGroupItem value={choice.key} />
                {choice.label}
              </label>
            ))}
          </RadioGroup>
          {own ? (
            <div className="grid gap-1.5">
              <label htmlFor="affirmation-text" className="sr-only">
                Your own text
              </label>
              <Textarea
                id="affirmation-text"
                ref={textRef}
                value={a.text}
                maxLength={maxLength}
                rows={4}
                className="max-h-[60vh] overflow-y-auto"
                aria-describedby={showCounter ? "affirmation-hint affirmation-count" : "affirmation-hint"}
                onChange={(e) => update((d) => editAffirmationText(d, e.target.value))}
              />
              {showCounter ? (
                <p id="affirmation-count" className="text-right text-xs text-muted-foreground">
                  {a.text.length.toLocaleString("en-US")} / {maxLength.toLocaleString("en-US")}
                </p>
              ) : null}
              <p id="affirmation-hint" className="text-sm text-muted-foreground">
                {a.text.trim() === "" ? `${OWN_TEXT_HINT} ${OWN_TEXT_BLANK}` : OWN_TEXT_HINT}
              </p>
            </div>
          ) : chosen ? (
            <Collapsible open={open} onOpenChange={setOpen} className="grid gap-2">
              <CollapsibleTrigger className="flex min-h-11 items-center gap-2 text-left text-sm font-medium">
                <ChevronDownIcon aria-hidden="true" className={cn("size-4 transition-transform", !open && "-rotate-90")} />
                Show creed text
              </CollapsibleTrigger>
              <CollapsibleContent className="grid gap-2">
                <CreedText text={chosen.text} />
                {chosen.credit ? <p className="text-xs text-muted-foreground">{chosen.credit}</p> : null}
              </CollapsibleContent>
            </Collapsible>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
