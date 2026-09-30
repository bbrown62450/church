"use client";

import { useQueryClient } from "@tanstack/react-query";
import { SparklesIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { PendingButton } from "@/components/app/pending-button";
import { rateLimitMessage, useWaitOver } from "@/components/builder/readings/use-wait-over";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import type { ApiError } from "@/lib/api/client";
import { errorToastMessage } from "@/lib/api/errors";
import type { HymnSuggestions, Passage } from "@/lib/api/types";
import { isValidDateIso } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { SLOTS, type Slot } from "@/lib/draft/schema";
import { applySuggestions } from "@/lib/hymns/picks";
import { buildSuggestionRequest } from "@/lib/hymns/suggest-request";
import { useSuggestHymns } from "@/lib/queries/hymns";
import { keys } from "@/lib/queries/keys";
import { cleanLines } from "@/lib/scripture-refs";

/** After this long the pending button adds "Still working — this can take up to a minute." (F §4.8). */
export const STILL_WORKING_MS = 8_000;

export const DATE_CHANGED = "The date changed while suggestions were loading. Try again.";
export const NOTHING_PICKED = "The AI didn't pick any hymns from this hymnal. Try again, or choose hymns yourself.";
export const NEWER_NOTE =
  "Suggestions favor older and familiar hymns. Newer hymns show the year their words were written.";

/**
 * The inline copy for a failed suggestion (S "AI suggestion flow" 5), keyed on
 * the error code; null for the errors the app handles globally (network, 500:
 * a toast, F §4.8). A cancel never reaches here.
 */
export function suggestErrorMessage(e: ApiError, waitOver = false): string | null {
  switch (e.code) {
    case "ai_not_configured":
      return "AI suggestions aren't set up on this app yet. You can still choose hymns yourself.";
    case "ai_busy":
      return "The AI service is busy. Try again in a minute.";
    case "ai_timeout":
      return "The AI took too long to answer. Try again.";
    case "ai_upstream_error":
      return "The AI service had a problem. Try again in a moment.";
    case "invalid_request":
      return e.message;
    case "rate_limited":
      return rateLimitMessage(e, waitOver);
    case "timeout":
      return "This is taking too long. Try again.";
    default:
      return null;
  }
}

type Outcome =
  | { kind: "ready"; text: string; newer: boolean }
  | { kind: "none" }
  | { kind: "date_changed" }
  | { kind: "error"; error: ApiError };

/** "Suggestions ready…", with " {n} recently used hymns were left out." (plan clarification 13 for one). */
function readyText(resp: HymnSuggestions): string {
  const n = resp.excluded_recent_count;
  const left = n === 0 ? "" : n === 1 ? " 1 recently used hymn was left out." : ` ${n} recently used hymns were left out.`;
  return `Suggestions ready. Tap an idea under a hymn to swap it in.${left}`;
}

function SuggestError({ error }: { error: ApiError }) {
  const over = useWaitOver(error.code === "rate_limited" ? error : null);
  return (
    <Alert variant="destructive">
      <AlertTitle>{suggestErrorMessage(error, over)}</AlertTitle>
    </Alert>
  );
}

/**
 * "Suggest hymns" (S "AI suggestion flow"). The answer is applied with a
 * functional update of the latest draft (`applySuggestions`: only empty slots
 * are filled, F D16), so a pick made during the wait counts. It is dropped when
 * `useSuggestHymns` reports it superseded (a newer request, the step
 * unmounted, another church) or the draft's date changed meanwhile. Cancel
 * aborts the wait; the server finishes and discards it (F §1.8). Messages and
 * errors live in component state, never in the draft.
 */
export function SuggestHymnsButton({
  selectedHymnal,
  hymnalEmpty,
  churchTranslation,
  onNoSuggestion,
}: {
  selectedHymnal: string;
  /** The selected hymnal has no hymns. */
  hymnalEmpty: boolean;
  churchTranslation: string;
  /** The slots the answer left empty, for "No suggestion for this slot." ([] when a request starts). */
  onNoSuggestion: (slots: Slot[], dateIso: string) => void;
}) {
  const { draft, update } = useDraft();
  const queryClient = useQueryClient();
  const { suggest, isPending } = useSuggestHymns();
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [slow, setSlow] = useState(false);
  const latest = useRef(draft);
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    latest.current = draft;
  }, [draft]);

  useEffect(() => () => controller.current?.abort(), []);

  useEffect(() => {
    if (!isPending) return;
    const timer = setTimeout(() => setSlow(true), STILL_WORKING_MS);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [isPending]);

  const dateValid = isValidDateIso(draft.readings.date_iso);
  const noReadings = cleanLines(draft.readings.scriptures).length === 0 && draft.readings.occasion.trim() === "";

  async function run() {
    const body = buildSuggestionRequest(
      latest.current,
      selectedHymnal,
      (translation, ref) => queryClient.getQueryData<Passage>(keys.passage(translation, ref)),
      churchTranslation,
    );
    const date = body.service_date_iso;
    const own = new AbortController();
    controller.current = own;
    setOutcome(null);
    onNoSuggestion([], date);
    const result = await suggest(body, own.signal);
    if (controller.current === own) controller.current = null;
    if (result.status === "superseded") return;
    if (result.status === "error") {
      if (result.error.code === "aborted") return;
      if (suggestErrorMessage(result.error) === null) toast.error(errorToastMessage(result.error));
      else setOutcome({ kind: "error", error: result.error });
      return;
    }
    const resp = result.data;
    if (latest.current.readings.date_iso !== date) {
      setOutcome({ kind: "date_changed" });
      return;
    }
    update((d) => (d.readings.date_iso === date ? { ...d, hymns: applySuggestions(d.hymns, resp, date) } : d));
    const empty = SLOTS.filter((slot) => resp.slots[slot].length === 0);
    if (empty.length === SLOTS.length) {
      setOutcome({ kind: "none" });
      return;
    }
    onNoSuggestion(empty, date);
    const newer = SLOTS.some((slot) => resp.slots[slot].some((h) => h.newer_than_preferred));
    setOutcome({ kind: "ready", text: readyText(resp), newer });
  }

  return (
    <div className="grid gap-2">
      <PendingButton
        size="touch"
        className="w-full"
        pending={isPending}
        pendingLabel="Suggesting…"
        disabled={hymnalEmpty || !dateValid}
        onClick={() => void run()}
      >
        <SparklesIcon data-icon="inline-start" aria-hidden="true" />
        Suggest hymns
      </PendingButton>
      {isPending ? (
        <div className="flex flex-wrap items-center gap-x-3 text-sm text-muted-foreground">
          <p aria-live="polite">{slow ? "Still working — this can take up to a minute." : null}</p>
          <Button variant="link" className="h-11 px-0" onClick={() => controller.current?.abort()}>
            Cancel
          </Button>
        </div>
      ) : null}
      <p className="text-sm text-muted-foreground">Fills empty slots and shows other ideas under each hymn.</p>
      {noReadings ? (
        <p className="text-sm text-muted-foreground">Tip: add the readings in step 1 first — suggestions use them.</p>
      ) : null}
      <div role="status" className="grid gap-1 text-sm">
        {outcome?.kind === "ready" ? <p>{outcome.text}</p> : null}
        {outcome?.kind === "ready" && outcome.newer ? <p className="text-muted-foreground">{NEWER_NOTE}</p> : null}
        {outcome?.kind === "none" ? <p>{NOTHING_PICKED}</p> : null}
        {outcome?.kind === "date_changed" ? <p>{DATE_CHANGED}</p> : null}
      </div>
      {outcome?.kind === "error" ? <SuggestError error={outcome.error} /> : null}
    </div>
  );
}
