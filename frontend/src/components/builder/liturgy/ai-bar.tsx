"use client";

import { InfoIcon } from "lucide-react";
import Link from "next/link";

import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import { sectionsNeedingAi } from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { liturgyCounts } from "@/lib/liturgy/summary";
import { cleanLines } from "@/lib/scripture-refs";

import { useRetryWait } from "./section-card";
import { STILL_WORKING, useStillWorking } from "./use-still-working";

/**
 * The AI bar (S UX "AI bar"): "Generate empty sections (n)" for the
 * switched-on cards with no text that are not already running, Cancel and
 * "Writing k of n…" while a bulk run goes, the no-AI banner, and the two
 * notices (no context; every section off). With AI off the button still
 * marks the empty cards, and sends nothing (S step 0). After a 429 the
 * button waits as the cards' Try again does.
 */
export function AiBar({ aiAvailable }: { aiAvailable: boolean }) {
  const { draft } = useDraft();
  const generation = useLiturgyGeneration();
  const targets = sectionsNeedingAi(draft).filter((key) => generation.runs[key] === undefined);
  const bulk = generation.bulk;
  const still = useStillWorking(bulk !== null);
  const retryAt = Math.max(0, ...Object.values(generation.errors).map((e) => e?.retryAt ?? 0));
  const retryWaiting = useRetryWait(retryAt === 0 ? undefined : retryAt);
  const r = draft.readings;
  const noContext = r.occasion.trim() === "" && cleanLines(r.scriptures).length === 0;
  const allOff = liturgyCounts(draft).enabled === 0;

  return (
    <section aria-label="Write with AI" className="grid gap-3 rounded-lg border bg-muted/30 p-4">
      {aiAvailable ? null : (
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>AI writing isn&apos;t set up for this app. Type each section yourself — everything else works as usual.</AlertTitle>
        </Alert>
      )}
      <div>
        {bulk ? (
          <Button variant="outline" size="touch" onClick={() => generation.cancelBulk()}>
            Cancel
          </Button>
        ) : (
          <Button
            size="touch"
            disabled={targets.length === 0 || retryWaiting}
            onClick={() => generation.generate(targets, { aiAvailable, bulk: true })}
          >
            Generate empty sections ({targets.length})
          </Button>
        )}
      </div>
      {bulk ? (
        <p className="text-sm" aria-live="polite">
          Writing {Math.min(bulk.done + 1, bulk.total)} of {bulk.total}…{still ? ` ${STILL_WORKING}` : null}
        </p>
      ) : (
        <p className="text-sm text-muted-foreground">
          {targets.length === 0
            ? "Every switched-on section has text. Use Regenerate on a card for a new AI draft."
            : "Only switched-on sections with no text are written. Text you typed is never changed."}
        </p>
      )}
      {noContext ? (
        <p className="text-sm text-muted-foreground">
          No occasion or readings yet, so AI text will be general. Add them in{" "}
          <Link href="/builder/readings" className="font-medium underline underline-offset-4">
            Date &amp; readings
          </Link>
          .
        </p>
      ) : null}
      {allOff ? (
        <p className="text-sm text-muted-foreground">
          All liturgy sections are switched off. The Word files will list only hymns, readings, the sermon title and any
          custom elements.
        </p>
      ) : null}
    </section>
  );
}
