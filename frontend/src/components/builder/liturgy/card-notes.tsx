"use client";

import { CheckIcon, CircleAlertIcon, XIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { canRevise, LOOKS_GOOD, TAG_LABELS, type Note } from "@/lib/liturgy/notes";
import { useLiturgyReview } from "@/lib/liturgy/review";

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
export function NoteList({ notes, label, onDismiss }: { notes: Note[]; label: string; onDismiss: (id: string) => void }) {
  return (
    <ul aria-label={label} className="grid gap-2">
      {notes.map((note) => (
        <li key={note.id} className="flex min-w-0 items-start gap-2">
          <Badge variant="outline" className="mt-0.5 shrink-0">
            {TAG_LABELS[note.tag]}
          </Badge>
          <p className="min-w-0 flex-1 text-sm wrap-anywhere">{note.text}</p>
          <Button
            id={`note-${note.id}-dismiss`}
            variant="ghost"
            size="icon-lg"
            className="-my-2 size-11 shrink-0 md:my-0 md:size-8"
            aria-label={`Dismiss note: ${note.text}`}
            onClick={() => onDismiss(note.id)}
          >
            <XIcon aria-hidden="true" />
          </Button>
        </li>
      ))}
    </ul>
  );
}

/** The id of a card's "Revise with these notes" button. */
export function reviseId(key: SectionKey): string {
  return `card-${key}-revise`;
}

/**
 * A card's notes under its text (R "Notes"): at most 3, most important
 * first; "Looks good." when the card was reviewed and came back with none;
 * nothing when it was not reviewed, its notes were all dismissed, or its text
 * changed since.
 *
 * "Revise with these notes" (R "Revise") shows only on an AI card with a note
 * left, and not while the card is being written; the card's heading
 * describes it. While it runs the button
 * reads "Revising…" beside a Cancel ×, which takes focus; a failure shows its
 * message here and leaves the button to try again. While a 429's wait
 * (Generate's or Revise's) is not over, the button is off but keeps focus. The card itself moves
 * focus when the revision ends (`SectionCard`).
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
  const revising = review.revising[sectionKey] === true;
  const failure = review.reviseErrors[sectionKey];
  const waiting = useRetryWait(useLiturgyGeneration().rateLimitedUntil ?? undefined);
  useEffect(() => {
    if (!focusCancel.current) return;
    focusCancel.current = false;
    cancelRef.current?.focus();
  });
  if (notes === undefined) return null;
  if (notes.notes.length === 0) {
    return notes.found === 0 ? (
      <p id={notesId(sectionKey)} className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <CheckIcon className="size-4" aria-hidden="true" />
        {LOOKS_GOOD}
      </p>
    ) : null;
  }
  const offered = canRevise(draft.liturgy.cards[sectionKey], notes) && !busy;
  return (
    <div id={notesId(sectionKey)} className="grid gap-2 rounded-md bg-muted/40 p-3">
      <NoteList
        notes={notes.notes}
        label={`Notes on ${label}`}
        onDismiss={(id) => {
          remember(notes.notes, id);
          review.dismiss(sectionKey, id);
        }}
      />
      {offered || revising ? (
        <div className="flex flex-wrap items-center justify-end gap-2">
          {revising ? (
            <>
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
            </>
          ) : (
            <Button
              id={reviseId(sectionKey)}
              variant="outline"
              size="touch"
              aria-describedby={headingId}
              focusableWhenDisabled
              disabled={waiting}
              className="data-disabled:pointer-events-none data-disabled:opacity-50"
              onClick={() => {
                // Focus moves to Cancel only when the revision started.
                if (review.revise(sectionKey)) focusCancel.current = true;
              }}
            >
              Revise with these notes
            </Button>
          )}
        </div>
      ) : null}
      {failure && !revising ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{failure.message}</AlertTitle>
        </Alert>
      ) : null}
    </div>
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
