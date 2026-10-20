"use client";

import { CircleAlertIcon, Loader2Icon, XIcon } from "lucide-react";
import { useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { needsRegenerateConfirm } from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { revisable } from "@/lib/liturgy/notes";
import { KIND_LABELS, NO_REACTIONS, pewsWaitMessage, reactionCount, type ShownReaction } from "@/lib/liturgy/pews";
import { usePews } from "@/lib/liturgy/pews-provider";
import { reviewTargets } from "@/lib/liturgy/request";
import { useLiturgyReview } from "@/lib/liturgy/review";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

import { useRetryWait } from "./section-card";
import { useStillWorking } from "./use-still-working";

export const PEWS_BUTTON = "Hear it from the pews";
export const LISTENING = "Listening…";
/** "Still working" without the reviewer's em dash (pew voices spec: no em dashes in new copy). */
export const PEWS_STILL_WORKING = "Still working. This can take up to a minute.";
export const PEWS_BUTTON_ID = "hear-from-the-pews";

/**
 * "Hear it from the pews" beside "Review service" (pew voices spec, "The
 * liturgy step"): on when "Review service" would be (`reviewTargets`); while
 * the request runs it reads "Cancel" (named "Cancel hearing from the pews").
 * `aria-disabled` rather than `disabled`, so focus stays on it.
 */
export function PewsButton() {
  const { draft, defaultBenediction } = useDraft();
  const pews = usePews();
  const ready = reviewTargets(draft, defaultBenediction).length > 0;
  return (
    <Button
      id={PEWS_BUTTON_ID}
      variant="outline"
      size="touch"
      focusableWhenDisabled
      disabled={!pews.running && !ready}
      aria-label={pews.running ? "Cancel hearing from the pews" : undefined}
      className="data-disabled:pointer-events-none data-disabled:opacity-50"
      onClick={() => (pews.running ? pews.cancel() : pews.start())}
    >
      {pews.running ? "Cancel" : PEWS_BUTTON}
    </Button>
  );
}

/** Under the header: "Listening…" (and after 8 s the still-working line), a failure's message, the polite count. */
export function PewsStatus() {
  const pews = usePews();
  const still = useStillWorking(pews.running);
  return (
    <>
      <p className="sr-only" aria-live="polite">
        {pews.announcement}
      </p>
      <p className={pews.running ? "flex flex-wrap items-center gap-x-2 text-sm" : "sr-only"} aria-live="polite">
        {pews.running ? (
          <>
            <Loader2Icon className="size-4 animate-spin" aria-hidden="true" />
            {LISTENING}
            {still ? ` ${PEWS_STILL_WORKING}` : null}
          </>
        ) : null}
      </p>
      {!pews.running && pews.error ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{pews.error}</AlertTitle>
        </Alert>
      ) : null}
    </>
  );
}

/** A 429's wait beside "Revise with this", in the seconds left when it appeared (keyed by the wait, so a new one recounts). */
function PewsWaitLine({ until }: { until: number }) {
  const [seconds] = useState(() => Math.max(1, Math.ceil((until - Date.now()) / 1000)));
  return <span className="text-sm text-muted-foreground">{pewsWaitMessage(seconds)}</span>;
}

/**
 * The "From the pews" box at the top of the step: each voice that has
 * reactions, its description, then its reactions (a small "Helped" or "Didn't
 * land" by its kind, "About {Label}" when it is about one prayer, the
 * sentence, a dismiss ×). "No reactions this time." when the answer had none;
 * gone once every reaction is dismissed or cleared. "Revise with this" on a
 * reaction that did not land (never one that helped or has no kind) about a
 * prayer Revise can change, through the reviewer's Revise (its Undo, its
 * "Revising…" and Cancel on the card); typed or saved text asks first. Off
 * while the card is written or revised, or during a 429's wait, with the
 * wait beside it.
 */
export function PewsPanel() {
  const pews = usePews();
  const review = useLiturgyReview();
  const { draft } = useDraft();
  const { runs, rateLimitedUntil } = useLiturgyGeneration();
  const waiting = useRetryWait(rateLimitedUntil ?? undefined);
  const [asking, setAsking] = useState<{ reaction: ShownReaction; key: SectionKey } | null>(null);
  const panel = pews.panel;
  // The confirm closes, sending nothing, once its reaction is gone (the prayer changed, or it was dismissed).
  const stillShown = asking !== null && panel !== null && panel.voices.some((v) => v.reactions.some((r) => r.id === asking.reaction.id));
  if (asking !== null && !stillShown) setAsking(null);
  const dialog = (
    <ConfirmDialog
      open={asking !== null}
      onOpenChange={(open) => {
        if (!open) setAsking(null);
      }}
      title="Replace your text?"
      description={
        asking === null ? "" : `Revise replaces the text in ${SECTION_LABELS[asking.key]} with a version that answers this reaction. You can undo right after.`
      }
      confirmLabel="Revise text"
      cancelLabel="Keep my text"
      onConfirm={() => {
        const ask = asking;
        setAsking(null);
        if (ask !== null) review.reviseWith(ask.key, [ask.reaction.text]);
      }}
      finalFocus={() => (asking === null ? true : (document.getElementById(`${asking.reaction.id}-revise`) ?? true))}
    />
  );
  if (panel === null || (panel.found > 0 && reactionCount(panel) === 0)) return dialog;
  const voices = panel.voices.filter((v) => v.reactions.length > 0);
  return (
    <section aria-labelledby="from-the-pews" className="grid min-w-0 gap-3 rounded-lg border p-4">
      <h3 id="from-the-pews" className="text-base font-medium">
        From the pews
      </h3>
      {panel.found === 0 ? <p className="text-sm text-muted-foreground">{NO_REACTIONS}</p> : null}
      {voices.map((voice, i) => (
        <div key={`${i}-${voice.description}`} className="grid min-w-0 gap-2">
          <h4 className="text-sm font-medium [overflow-wrap:anywhere]">{voice.description}</h4>
          <ul aria-label={`Reactions from ${voice.description}`} className="grid gap-2">
            {voice.reactions.map((reaction) => {
              const key = reaction.section;
              const card = key === null ? null : draft.liturgy.cards[key];
              // Only a reaction that did not land is offered to Revise; one that helped, or has no kind, is not.
              const offered = reaction.kind === "missed" && key !== null && card !== null && card.enabled && revisable(card);
              const busy = key !== null && (runs[key] !== undefined || review.revising[key] === true);
              return (
                <li key={reaction.id} className="grid min-w-0 gap-2">
                  <div className="flex min-w-0 items-start gap-2">
                    <div className="grid min-w-0 flex-1 gap-1">
                      {reaction.kind === null && key === null ? null : (
                        <div className="flex flex-wrap items-center gap-2">
                          {reaction.kind === null ? null : (
                            <span className="text-xs font-medium text-muted-foreground">{KIND_LABELS[reaction.kind]}</span>
                          )}
                          {key === null ? null : (
                            <Badge variant="outline" className="w-fit">
                              {`About ${SECTION_LABELS[key]}`}
                            </Badge>
                          )}
                        </div>
                      )}
                      <p id={`${reaction.id}-text`} className="min-w-0 text-sm [overflow-wrap:anywhere]">
                        {reaction.text}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon-lg"
                      className="-my-2 size-11 shrink-0 md:my-0 md:size-8"
                      aria-label={`Dismiss reaction: ${reaction.text}`}
                      onClick={() => pews.dismiss(reaction.id)}
                    >
                      <XIcon aria-hidden="true" />
                    </Button>
                  </div>
                  {offered && key !== null && card !== null ? (
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      {waiting && !busy && rateLimitedUntil !== null ? <PewsWaitLine key={rateLimitedUntil} until={rateLimitedUntil} /> : null}
                      <Button
                        id={`${reaction.id}-revise`}
                        variant="outline"
                        size="touch"
                        aria-describedby={`${reaction.id}-text`}
                        focusableWhenDisabled
                        disabled={busy || waiting}
                        className="data-disabled:pointer-events-none data-disabled:opacity-50"
                        onClick={() => {
                          if (needsRegenerateConfirm(card)) {
                            setAsking({ reaction, key });
                            return;
                          }
                          review.reviseWith(key, [reaction.text]);
                        }}
                      >
                        Revise with this
                      </Button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
      {dialog}
    </section>
  );
}
