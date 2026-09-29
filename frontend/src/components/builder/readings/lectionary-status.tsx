"use client";

import { InfoIcon } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState } from "@/components/app/error-state";
import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { ApiError } from "@/lib/api/client";
import type { Lectionary } from "@/lib/api/types";
import { useChurch } from "@/lib/church-context";
import { formatLongDate, formatServiceDate, isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import {
  applyReadingSet,
  chooseReadingSet,
  cleanScriptures,
  clearReadings,
  readingsStale,
  selectedSetIndex,
  showAvailableBanner,
} from "@/lib/draft/readings";
import { canLookUp } from "@/lib/queries/lectionary";
import { scriptureKey } from "@/lib/scripture-refs";
import { readSession, writeSession } from "@/lib/storage";

import { ReadingSetPicker } from "./reading-set-picker";
import { ReplaceReadingsDialog } from "./replace-readings-dialog";
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

/** The dates whose banner "Keep mine" hid, for this church, until the tab closes (owner answer C). */
function keptMineKey(churchId: string): string {
  return `wsb:readingsKeptMine:${churchId}`;
}

function readKeptMine(churchId: string): string[] {
  try {
    const value: unknown = JSON.parse(readSession(keptMineKey(churchId)) ?? "[]");
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

/**
 * This date's sets (S UX items 2 and 3): the switcher when there are several,
 * the partial note, the "Readings … are available" banner and, on a date with
 * one set whose lines differ from the draft's, "Use the lectionary's
 * readings" (owner answer B). A set chosen over empty or lectionary fields
 * applies at once; over typed or archived fields it asks first. The banner's
 * "Keep mine" hides it for that date until the tab closes (sessionStorage, not
 * the draft; owner answer C); "Keep mine" in the switcher's or the one-set
 * link's question only closes it.
 */
function ReadingSets({ lect }: { lect: Lectionary }) {
  const church = useChurch();
  const { draft, update } = useDraft();
  const [asking, setAsking] = useState<{ index: number; from: "switcher" | "banner" | "link" } | null>(null);
  const [keptMine, setKeptMine] = useState<string[]>(() => readKeptMine(church.id));
  const dateIso = draft.readings.date_iso;
  const selected = selectedSetIndex(draft, lect);
  const banner = !keptMine.includes(dateIso) && showAvailableBanner(draft, lect);
  const origin = draft.readings.fields_origin;
  const lines = cleanScriptures(draft);
  const only = lect.reading_sets.length === 1 ? lect.reading_sets[0] : null;
  const offerOnly =
    only !== null &&
    !banner &&
    (only.scriptures.length !== lines.length ||
      only.scriptures.some((line, i) => scriptureKey(line) !== scriptureKey(lines[i])));

  function keepMine() {
    const next = [...readKeptMine(church.id).filter((date) => date !== dateIso), dateIso].slice(-50);
    writeSession(keptMineKey(church.id), JSON.stringify(next));
    setKeptMine(next);
  }

  function applyOnly() {
    if (origin === "empty" || origin === "lectionary") {
      update((d) => (d.readings.date_iso !== lect.date ? d : applyReadingSet(d, lect, 0)));
    } else setAsking({ index: 0, from: "link" });
  }

  function choose(index: number) {
    if (origin === "empty" || origin === "lectionary") {
      // Like replace(): a choice that lands after the date moved does nothing.
      update((d) => (d.readings.date_iso !== lect.date ? d : chooseReadingSet(d, lect, index)));
    } else setAsking({ index, from: "switcher" });
  }

  function replace() {
    if (!asking) return;
    const { index, from } = asking;
    setAsking(null);
    update((d) => {
      if (d.readings.date_iso !== lect.date) return d; // the date moved while the dialog was open
      return from === "switcher" ? chooseReadingSet(d, lect, index) : applyReadingSet(d, lect, index);
    });
  }

  return (
    <div className="grid gap-3">
      {lect.reading_sets.length > 1 ? <ReadingSetPicker lect={lect} selected={selected} onChoose={choose} /> : null}
      {lect.partial ? (
        <p className="text-sm text-muted-foreground">
          One lectionary source didn&apos;t respond, so other reading options for this date may be missing.
        </p>
      ) : null}
      {offerOnly ? (
        <div>
          <Button type="button" variant="link" className="h-11 px-0" onClick={applyOnly}>
            Use the lectionary&apos;s readings
          </Button>
        </div>
      ) : null}
      {banner ? (
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>Readings for {formatServiceDate(lect.date)} are available.</AlertTitle>
          <AlertDescription>
            <Button
              type="button"
              variant="outline"
              size="touch"
              className="mt-2"
              onClick={() => setAsking({ index: selected ?? lect.default_index ?? 0, from: "banner" })}
            >
              Use them
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      <ReplaceReadingsDialog
        setName={asking ? (lect.reading_sets[asking.index]?.name ?? null) : null}
        onConfirm={replace}
        onKeep={() => {
          if (asking?.from === "banner") keepMine();
          setAsking(null);
        }}
      />
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

  return <ReadingSets lect={lect} />;
}
