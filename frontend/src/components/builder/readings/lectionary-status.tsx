"use client";

import { InfoIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/app/error-state";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError } from "@/lib/api/client";
import { formatLongDate, formatServiceDate, isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { clearReadings, readingsStale } from "@/lib/draft/readings";
import { canLookUp } from "@/lib/queries/lectionary";

import { rateLimitMessage, useWaitOver } from "./use-wait-over";

export const LECTIONARY_UNAVAILABLE =
  "The lectionary couldn't be reached. Enter readings yourself, or try again in a few minutes.";
/** After this long, Loading adds "Still working — this can take up to a minute." */
export const STILL_WORKING_MS = 8_000;

function Loading({ lookupDate }: { lookupDate: string }) {
  const [slowFor, setSlowFor] = useState<string | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setSlowFor(lookupDate), STILL_WORKING_MS);
    return () => clearTimeout(timer);
  }, [lookupDate]);
  return (
    <div role="status" className="grid gap-2">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <p className="text-sm text-muted-foreground">Looking up the lectionary…</p>
      {slowFor === lookupDate ? (
        <p className="text-sm text-muted-foreground">Still working — this can take up to a minute.</p>
      ) : null}
    </div>
  );
}

function RateLimited({ error, onRetry, retrying }: { error: ApiError; onRetry: () => void; retrying: boolean }) {
  const over = useWaitOver(error);
  return (
    <ErrorState
      error={error}
      message={rateLimitMessage(error, over)}
      retryLabel="Try again"
      retryDisabled={!over}
      retrying={retrying}
      onRetry={onRetry}
    />
  );
}

/**
 * "These readings are from …" with "Clear readings" (S UX item 2, stale
 * fields). Without a valid date to name, the sentence stops after the set.
 */
function StaleFields() {
  const { draft, update } = useDraft();
  const set = draft.readings.reading_set;
  if (!readingsStale(draft) || !set) return null;
  const dateIso = draft.readings.date_iso;
  const from = `${draft.readings.occasion} (${formatServiceDate(set.date_iso)})`;
  return (
    <div className="grid justify-items-start gap-2">
      <p className="text-sm">
        {isValidDateIso(dateIso)
          ? `These readings are from ${from}, not ${formatServiceDate(dateIso)}.`
          : `These readings are from ${from}.`}
      </p>
      <Button type="button" variant="outline" size="touch" onClick={() => update(clearReadings)}>
        Clear readings
      </Button>
    </div>
  );
}

/**
 * What the lectionary said about the draft's date (S UX item 2): exactly one
 * of Loading, the reading sets, No readings, Unavailable or Rate limited,
 * directly under the date, plus the partial note and the stale-fields note.
 * For a date the lookup refuses only the stale-fields note can show (the date
 * field explains the date). Focus never moves on its own; "Enter readings"
 * moves it to Occasion.
 */
export function LectionaryStatus({ onEnterReadings }: { onEnterReadings: () => void }) {
  const { draft } = useDraft();
  const { lookupDate, settled, query } = useLectionaryLookup();
  if (!canLookUp(draft.readings.date_iso)) return <StaleFields />;
  const retry = () => void query.refetch();

  if (!settled || query.isPending) return <Loading lookupDate={draft.readings.date_iso} />;

  // An answer already on screen wins over a failed background refetch.
  const lect = query.data;
  if (lect === undefined) {
    if (query.error?.code === "rate_limited") {
      return (
        <div className="grid gap-3">
          <RateLimited error={query.error} onRetry={retry} retrying={query.isFetching} />
          <StaleFields />
        </div>
      );
    }
    return (
      <div className="grid gap-3">
        <ErrorState
          error={query.error}
          message={LECTIONARY_UNAVAILABLE}
          retryLabel="Try again"
          retrying={query.isFetching}
          onRetry={retry}
        />
        <StaleFields />
      </div>
    );
  }

  if (lect.status === "no_readings" || lect.reading_sets.length === 0) {
    return (
      <div className="grid gap-3">
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>No lectionary readings for {formatLongDate(lookupDate)}.</AlertTitle>
          <AlertDescription>
            <p>Enter the occasion and readings below.</p>
            <Button type="button" variant="outline" size="touch" className="mt-2" onClick={onEnterReadings}>
              Enter readings
            </Button>
          </AlertDescription>
        </Alert>
        <StaleFields />
      </div>
    );
  }

  // One or more sets: the partial note. Task 8 adds the set switcher and the banner.
  return lect.partial ? (
    <p className="text-sm text-muted-foreground">
      One lectionary source didn&apos;t respond, so other reading options for this date may be missing.
    </p>
  ) : null;
}
