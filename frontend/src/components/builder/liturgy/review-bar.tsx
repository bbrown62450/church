"use client";

import { CircleAlertIcon, Loader2Icon } from "lucide-react";

import { Alert, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useDraft } from "@/lib/draft/context";
import { QUICK_CHECKS_ONLY } from "@/lib/liturgy/notes";
import { reviewTargets } from "@/lib/liturgy/request";
import { useLiturgyReview } from "@/lib/liturgy/review";

import { STILL_WORKING, useStillWorking } from "./use-still-working";

/** The button's id: focus comes back here when the "Across the service" box loses its last note. */
export const REVIEW_BUTTON_ID = "review-service";

/**
 * "Review service" in the step's header (R "Review service"): on when at
 * least one switched-on card has text; while the review runs it reads
 * "Cancel" (named "Cancel review"). One button, `aria-disabled` rather than
 * `disabled` when there is nothing to review, so focus stays on it when a
 * review starts or ends.
 */
export function ReviewButton() {
  const { draft } = useDraft();
  const review = useLiturgyReview();
  const ready = reviewTargets(draft).length > 0;
  return (
    <Button
      id={REVIEW_BUTTON_ID}
      variant="outline"
      size="touch"
      focusableWhenDisabled
      disabled={!review.running && !ready}
      aria-label={review.running ? "Cancel review" : undefined}
      className="data-disabled:pointer-events-none data-disabled:opacity-50"
      onClick={() => (review.running ? review.cancel() : review.start())}
    >
      {review.running ? "Cancel" : "Review service"}
    </Button>
  );
}

/**
 * Under the header: while a review runs, a spinner with "Reviewing…" and,
 * after 8 s, "Still working — this can take up to a minute." (in a live
 * region that is always there, empty and visually hidden when idle); a review that
 * failed, its message; a review whose AI part is missing, the quiet "Only
 * quick checks ran…" line; and, read out politely, how many notes it left.
 */
export function ReviewStatus() {
  const review = useLiturgyReview();
  const still = useStillWorking(review.running);
  const quickOnly = !review.running && review.review !== null && review.review.aiStatus !== "ok";
  return (
    <>
      <p className="sr-only" aria-live="polite">
        {review.announcement}
      </p>
      {/* Always there, so "Reviewing…" is announced when it appears (a region inserted with its text often is not). */}
      <p className={review.running ? "flex flex-wrap items-center gap-x-2 text-sm" : "sr-only"} aria-live="polite">
        {review.running ? (
          <>
            <Loader2Icon className="size-4 animate-spin" aria-hidden="true" />
            Reviewing…{still ? ` ${STILL_WORKING}` : null}
          </>
        ) : null}
      </p>
      {!review.running && review.error ? (
        <Alert variant="destructive" role="alert">
          <CircleAlertIcon aria-hidden="true" />
          <AlertTitle className="whitespace-normal">{review.error}</AlertTitle>
        </Alert>
      ) : null}
      {quickOnly ? <p className="text-sm text-muted-foreground">{QUICK_CHECKS_ONLY}</p> : null}
    </>
  );
}
