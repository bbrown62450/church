"use client";

import { CheckIcon, CircleAlertIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { needsRegenerateConfirm } from "@/lib/liturgy/cards";
import { rateLimitMessage } from "@/lib/liturgy/errors";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { canRevise, LOOKS_GOOD, STALE_LINE, TAG_LABELS, type CardReview, type Note } from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";
import { cn } from "@/lib/utils";

import { REVIEW_BUTTON_ID } from "./review-bar";
import { useRetryWait } from "./section-card";

/** The id of a card's notes, which describe its textarea. */
export function notesId(key: SectionKey): string {
  return `card-${key}-notes`;
}

/**
 * Remembers where focus goes after a note is dismissed: the next note's ×,
 * else the previous one's, else `fallback` (the card's heading, or the
 * Review button when the "Across the service" box goes). The owner stays
 * mounted when its last note goes, so the move still happens.
 */
function useDismissFocus(fallback: () => HTMLElement | null) {
  const target = useRef<string | null | undefined>(undefined);
  useEffect(() => {
    const id = target.current;
    if (id === undefined) return;
    target.current = undefined;
    const element = id === null ? null : document.getElementById(id);
    (element ?? fallback())?.focus();
  });
  return (notes: Note[], id: string) => {
    const at = notes.findIndex((n) => n.id === id);
    const next = notes[at + 1] ?? notes[at - 1];
    target.current = next ? `note-${next.id}-dismiss` : null;
  };
}

/** One list of notes: a tag chip, the sentence and a dismiss ×, wrapping at 375 px. */
export function NoteList({
  notes,
  label,
  onDismiss,
  disabled = false,
  faded = false,
  describedBy,
}: {
  notes: Note[];
  label: string;
  onDismiss: (id: string) => void;
  /** The card is being revised with these notes: none can go meanwhile. */
  disabled?: boolean;
  /** The card changed since its review: the chips and sentences are dimmed, still readable. */
  faded?: boolean;
  /** The id of the line that says why they are dimmed. */
  describedBy?: string;
}) {
  return (
    <ul aria-label={label} aria-describedby={describedBy} className="grid gap-2">
      {notes.map((note) => (
        <li key={note.id} className="flex min-w-0 items-start gap-2">
          <Badge variant="outline" className={cn("mt-0.5 shrink-0", faded && "text-muted-foreground")}>
            {TAG_LABELS[note.tag]}
          </Badge>
          <p className={cn("min-w-0 flex-1 text-sm wrap-anywhere", faded && "text-muted-foreground")}>{note.text}</p>
          <Button
            id={`note-${note.id}-dismiss`}
            variant="ghost"
            size="icon-lg"
            className="-my-2 size-11 shrink-0 md:my-0 md:size-8"
            aria-label={`Dismiss note: ${note.text}`}
            disabled={disabled}
            onClick={() => onDismiss(note.id)}
          >
            <XIcon aria-hidden="true" />
          </Button>
        </li>
      ))}
    </ul>
  );
}

/** A 429's wait beside a disabled Revise, in the seconds left when it appeared (keyed by the wait, so a new one recounts). */
function WaitLine({ until }: { until: number }) {
  const [seconds] = useState(() => Math.max(1, Math.ceil((until - Date.now()) / 1000)));
  return <span className="text-sm text-muted-foreground">{rateLimitMessage(seconds)}</span>;
}

/** The id of a card's "From before your last edit." line, which describes its faded notes. */
function staleId(key: SectionKey): string {
  return `card-${key}-stale`;
}

/** The id of a card's "Revise with these notes" button. */
export function reviseId(key: SectionKey): string {
  return `card-${key}-revise`;
}

/**
 * A card's notes under its text (R "Notes"): at most 3, most important
 * first; "Looks good." when the card was reviewed and came back with none;
 * nothing when it was not reviewed, its notes were all dismissed, or it was
 * "Looks good." and has changed since. When the card changed after its review
 * (reviewer follow-up 1) the notes stay, dimmed, under "From before your last
 * edit.", which is plain text inside the notes, so it is read with them, is
 * part of the textarea's description and describes the list; it is not
 * announced as it appears (it appears as the member types).
 *
 * "Revise with these notes" (R "Revise") shows on a card with text and a note
 * left, written by the AI, typed or from a saved service (reviewer follow-up
 * 1; never the church default), and not while the card is being written; the
 * card's heading describes it. On typed or saved text it asks first ("Replace
 * your text?", the same rule as Regenerate's): "Keep my text" returns focus to
 * the button, "Revise text" starts it and the closing dialog sends focus to its
 * Cancel. The dialog closes, sending nothing, when this card's notes or text
 * change while it asks (Revise no longer offered, a new review, another tab's
 * edit) or a 429's wait begins (the wait shows beside Revise), and focus goes
 * to Revise, else the heading; other cards' changes leave it open. While it runs the button
 * reads "Revising…" beside a Cancel ×, which takes focus, and the notes' ×
 * are off; the row stays while it runs even if the notes go (another tab
 * edited the card), so Cancel stays reachable. A failure shows its message
 * here and leaves the button to try again. While a 429's wait (Generate's or
 * Revise's) is not over, the button is off but keeps focus, with the wait
 * beside it; a 429's own alert goes when its wait ends. The card itself
 * moves focus when the revision ends (`SectionCard`).
 */
export function CardNotes({
  sectionKey,
  label,
  headingId,
  busy = false,
}: {
  sectionKey: SectionKey;
  label: string;
  headingId: string;
  /** The card is being written by the AI: no Revise. */
  busy?: boolean;
}) {
  const review = useLiturgyReview();
  const { draft } = useDraft();
  const notes = review.review?.cards[sectionKey];
  const remember = useDismissFocus(() => document.getElementById(headingId));
  const cancelRef = useRef<HTMLButtonElement>(null);
  const focusCancel = useRef(false);
  const [confirming, setConfirming] = useState(false);
  /** This card's own review entry, and its text, when the confirm was opened. */
  const [askedOn, setAskedOn] = useState<{ notes: CardReview | undefined; text: string } | null>(null);
  /** "Revise text" was chosen, so the closing dialog sends focus to the revision's Cancel. */
  const confirmed = useRef(false);
  const revising = review.revising[sectionKey] === true;
  const failure = review.reviseErrors[sectionKey];
  const limitedUntil = useLiturgyGeneration().rateLimitedUntil ?? undefined;
  const waiting = useRetryWait(limitedUntil);
  const failureWaiting = useRetryWait(failure?.retryAt);
  useEffect(() => {
    if (!focusCancel.current) return;
    focusCancel.current = false;
    cancelRef.current?.focus();
  });
  const revisingRow = revising ? (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <PendingButton pending pendingLabel="Revising…" size="touch">
        Revising…
      </PendingButton>
      <Button
        ref={cancelRef}
        variant="ghost"
        size="icon-lg"
        className="size-11 md:size-8"
        aria-label={`Cancel revising ${label}`}
        onClick={() => review.cancelRevise(sectionKey)}
      >
        <XIcon aria-hidden="true" />
      </Button>
    </div>
  ) : null;
  const card = draft.liturgy.cards[sectionKey];
  const offered = canRevise(card, notes) && !busy;
  // The confirm closes once Revise is no longer offered, this card's notes changed (a new review, the card went
  // stale or lost its notes), its text changed (another tab's edit, even to a card already faded) or a 429's wait
  // began, so it never revises with notes or text the member is not looking at. Other cards' changes leave it open.
  if (confirming && (!offered || waiting || notes !== askedOn?.notes || card.text !== askedOn?.text)) {
    setConfirming(false);
  }
  // Rendered after the notes in every branch below, so it stays mounted (and sends focus back) as the notes go.
  const dialog = (
    <ConfirmDialog
      open={confirming}
      onOpenChange={setConfirming}
      title="Replace your text?"
      description={`Revise replaces the text in ${label} with a version that addresses these notes. You can undo right after.`}
      confirmLabel="Revise text"
      cancelLabel="Keep my text"
      onConfirm={() => {
        confirmed.current = true;
        setConfirming(false);
        review.revise(sectionKey);
      }}
      // Keep my text: back to Revise. Revise text: Revise is gone, so the revision's Cancel (Revise if it did not
      // start). The heading when neither is there (the notes went while it asked).
      finalFocus={() => {
        const cancel = confirmed.current ? cancelRef.current : null;
        if (cancel !== null && cancel.isConnected) return cancel;
        return document.getElementById(reviseId(sectionKey)) ?? document.getElementById(headingId);
      }}
    />
  );
  if (notes === undefined || notes.notes.length === 0) {
    // The notes went while the card revises (another tab edited it): Cancel stays.
    const rest =
      revisingRow ??
      (notes?.found === 0 ? (
        <p id={notesId(sectionKey)} className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <CheckIcon className="size-4" aria-hidden="true" />
          {LOOKS_GOOD}
        </p>
      ) : null);
    return (
      <>
        {rest}
        {dialog}
      </>
    );
  }
  // A 429's alert shows until its wait ends.
  const failureShown = failure !== undefined && !revising && (failure.retryAt === undefined || failureWaiting);
  // The wait, beside the disabled Revise, unless its own alert already says it.
  const waitShown = offered && !revising && waiting && limitedUntil !== undefined && !(failureShown && failure.code === "rate_limited");
  const shown = (
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
      {notes.stale ? (
        <p id={staleId(sectionKey)} className="text-sm font-medium text-muted-foreground">
          {STALE_LINE}
        </p>
      ) : null}
      <NoteList
        notes={notes.notes}
        label={`Notes on ${label}`}
        disabled={revising}
        faded={notes.stale}
        describedBy={notes.stale ? staleId(sectionKey) : undefined}
        onDismiss={(id) => {
          remember(notes.notes, id);
          review.dismiss(sectionKey, id);
        }}
      />
      {revisingRow ??
        (offered ? (
          <div className="flex flex-wrap items-center justify-end gap-2">
            {waitShown ? (
              <WaitLine key={limitedUntil} until={limitedUntil} />
            ) : null}
            <Button
              id={reviseId(sectionKey)}
              variant="outline"
              size="touch"
              aria-describedby={headingId}
              focusableWhenDisabled
              disabled={waiting}
              className="data-disabled:pointer-events-none data-disabled:opacity-50"
              onClick={() => {
                if (needsRegenerateConfirm(card)) {
                  confirmed.current = false;
                  setAskedOn({ notes, text: card.text });
                  setConfirming(true);
                  return;
                }
                // Focus moves to Cancel only when the revision started.
                if (review.revise(sectionKey)) focusCancel.current = true;
              }}
            >
              Revise with these notes
            </Button>
          </div>
        ) : null)}
      {failureShown ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{failure.message}</AlertTitle>
        </Alert>
      ) : null}
    </div>
  );
  return (
    <>
      {shown}
      {dialog}
    </>
  );
}

/** The "Across the service" box at the top of the step (R "Notes"): notes about more than one prayer, at most 3. */
export function ServiceNotes() {
  const review = useLiturgyReview();
  const notes = review.review?.service ?? [];
  const remember = useDismissFocus(() => document.getElementById(REVIEW_BUTTON_ID));
  if (notes.length === 0) return null;
  return (
    <section aria-labelledby="across-the-service" className="grid gap-2 rounded-lg border p-4">
      <h3 id="across-the-service" className="text-base font-medium">
        Across the service
      </h3>
      <NoteList
        notes={notes}
        label="Notes across the service"
        onDismiss={(id) => {
          remember(notes, id);
          review.dismiss("service", id);
        }}
      />
    </section>
  );
}
