"use client";

import { InfoIcon } from "lucide-react";
import { useEffect, useRef, useState, type RefObject } from "react";

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
import type { DraftV1 } from "@/lib/draft/schema";
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
 * Clearing moves focus to Occasion, since the button goes with the note.
 */
function StaleFields({ focusOccasion }: { focusOccasion: () => void }) {
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
      <Button
        type="button"
        variant="outline"
        size="touch"
        onClick={() => {
          update(clearReadings);
          focusOccasion();
        }}
      >
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

function sameLines(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((line, i) => scriptureKey(line) === scriptureKey(b[i]));
}

/** Fields a lectionary set may replace without asking. */
function replaceable(d: DraftV1): boolean {
  return d.readings.fields_origin === "empty" || d.readings.fields_origin === "lectionary";
}

type Asking = { index: number; from: "switcher" | "banner" | "link" };

/**
 * This date's sets (S UX items 2 and 3): the switcher when there are several,
 * the partial note, the "Readings … are available" banner and "Use the
 * lectionary's readings" when the cleaned lines differ from the date's set
 * (its only set, or the one chosen; owner answers B and 3). A set chosen
 * over empty or lectionary fields applies at once; over typed or archived
 * fields it asks first. The check is made again inside the update, so fields
 * typed meanwhile (in another tab) are never replaced without asking.
 *
 * Only the banner question's "Keep mine" button hides the banner and the link
 * for that date until the tab closes (sessionStorage, not the draft; owner
 * answers C, 1 and 2); Escape, a click outside and the other questions' "Keep
 * mine" only close. The link waits while the fields are empty, since the
 * automatic fill takes care of them. When a question closes, focus goes back
 * to what opened it or, when that has gone (the banner, the link), to the
 * status area (Base UI focuses its first control, such as the checked set,
 * else the area itself).
 */
function ReadingSets({ lect, statusRef }: { lect: Lectionary; statusRef: RefObject<HTMLDivElement | null> }) {
  const church = useChurch();
  const { draft, update } = useDraft();
  const [asking, setAsking] = useState<Asking | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const [keptMine, setKeptMine] = useState<string[]>(() => readKeptMine(church.id));
  const dateIso = draft.readings.date_iso;
  const kept = keptMine.includes(dateIso);
  const selected = selectedSetIndex(draft, lect);
  const banner = !kept && showAvailableBanner(draft, lect);
  const origin = draft.readings.fields_origin;
  const target = lect.reading_sets.length === 1 ? 0 : selected;
  const targetSet = target === null ? undefined : lect.reading_sets[target];
  const offerSet =
    target !== null &&
    targetSet !== undefined &&
    origin !== "empty" &&
    !banner &&
    !kept &&
    !sameLines(targetSet.scriptures, cleanScriptures(draft));

  function ask(next: Asking) {
    opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setAsking(next);
  }

  function keepMine() {
    const next = [...readKeptMine(church.id).filter((date) => date !== dateIso), dateIso].slice(-50);
    writeSession(keptMineKey(church.id), JSON.stringify(next));
    setKeptMine(next);
  }

  function applyTarget() {
    if (target === null) return;
    if (origin === "empty" || origin === "lectionary") {
      update((d) => (d.readings.date_iso !== lect.date || !replaceable(d) ? d : applyReadingSet(d, lect, target)));
    } else ask({ index: target, from: "link" });
  }

  function choose(index: number) {
    if (origin === "empty" || origin === "lectionary") {
      // Like replace(): a choice that lands after the date moved, or after
      // fields were typed, does nothing.
      update((d) => (d.readings.date_iso !== lect.date || !replaceable(d) ? d : chooseReadingSet(d, lect, index)));
    } else ask({ index, from: "switcher" });
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
      {offerSet ? (
        <div>
          <Button type="button" variant="link" className="h-11 px-0" onClick={applyTarget}>
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
              onClick={() => ask({ index: selected ?? lect.default_index ?? 0, from: "banner" })}
            >
              Use them
            </Button>
          </AlertDescription>
        </Alert>
      ) : null}
      <ReplaceReadingsDialog
        setName={asking ? (lect.reading_sets[asking.index]?.name ?? null) : null}
        onConfirm={replace}
        onKeepMine={() => {
          if (asking?.from === "banner") keepMine();
        }}
        onClose={() => setAsking(null)}
        finalFocus={() => (opener.current?.isConnected ? opener.current : (statusRef.current ?? true))}
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
 * and "Clear readings" move it to Occasion, and a "Try again" that brings an
 * answer moves it to this area (`tabIndex={-1}`), since the button is gone.
 */
export function LectionaryStatus({ focusOccasion }: { focusOccasion: () => void }) {
  const { draft } = useDraft();
  const { lookupDate, settled, query } = useLectionaryLookup();
  const statusRef = useRef<HTMLDivElement>(null);
  const focusOnAnswer = useRef(false);
  const answered = query.isSuccess && !query.isFetching;
  const failed = query.isError && !query.isFetching;

  useEffect(() => {
    if (!focusOnAnswer.current || (!answered && !failed)) return;
    focusOnAnswer.current = false;
    // Only when focus went down with the button; never away from where the user is.
    if (answered && (document.activeElement === null || document.activeElement === document.body)) {
      statusRef.current?.focus();
    }
  }, [answered, failed]);

  const retry = () => {
    focusOnAnswer.current = true;
    void query.refetch();
  };

  return (
    <div ref={statusRef} tabIndex={-1} className="grid gap-3 outline-none empty:hidden">
      <StatusContent
        lookupDate={lookupDate}
        settled={settled}
        query={query}
        retry={retry}
        statusRef={statusRef}
        focusOccasion={focusOccasion}
        dateIso={draft.readings.date_iso}
      />
    </div>
  );
}

function StatusContent({
  lookupDate,
  settled,
  query,
  retry,
  statusRef,
  focusOccasion,
  dateIso,
}: ReturnType<typeof useLectionaryLookup> & {
  retry: () => void;
  statusRef: RefObject<HTMLDivElement | null>;
  focusOccasion: () => void;
  dateIso: string;
}) {
  if (!canLookUp(dateIso)) return <StaleFields focusOccasion={focusOccasion} />;
  if (!settled || query.isPending) return <Loading lookupDate={dateIso} />;

  // An answer already on screen wins over a failed background refetch.
  const lect = query.data;
  if (lect === undefined) {
    return (
      <>
        {query.error?.status === 429 ? (
          <RateLimited error={query.error} onRetry={retry} retrying={query.isFetching} />
        ) : (
          <ErrorState
            error={query.error}
            message={LECTIONARY_UNAVAILABLE}
            retryLabel="Try again"
            retrying={query.isFetching}
            onRetry={retry}
          />
        )}
        <StaleFields focusOccasion={focusOccasion} />
      </>
    );
  }

  if (lect.status === "no_readings" || lect.reading_sets.length === 0) {
    return (
      <>
        <Alert role="status">
          <InfoIcon aria-hidden="true" />
          <AlertTitle>No lectionary readings for {formatLongDate(lookupDate)}.</AlertTitle>
          <AlertDescription>
            <p>Enter the occasion and readings below.</p>
            <Button type="button" variant="outline" size="touch" className="mt-2" onClick={focusOccasion}>
              Enter readings
            </Button>
          </AlertDescription>
        </Alert>
        <StaleFields focusOccasion={focusOccasion} />
      </>
    );
  }

  return <ReadingSets lect={lect} statusRef={statusRef} />;
}
