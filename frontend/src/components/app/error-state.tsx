import { CircleAlertIcon } from "lucide-react";

import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { describeError } from "@/lib/api/errors";

export type ErrorStateProps = {
  /** The failed query's error; describeError picks the sentence (F §4.8, ops handoff Ref). */
  error: unknown;
  /** Usually the query's refetch; called with no arguments. */
  onRetry: () => void;
  /** Optional heading above the sentence. */
  title?: string;
  /** True while the retry runs: Retry is disabled, busy and spinning, so a repeat tap does nothing. */
  retrying?: boolean;
  /** A screen's own sentence instead of `describeError`'s (slice 2c: the lectionary's copy). */
  message?: string;
  /** The button's label: "Retry" unless the screen's copy names it ("Try again"). */
  retryLabel?: string;
  /** Disables the button without the spinner, for example while a rate limit's wait runs. */
  retryDisabled?: boolean;
};

/** F §4.8 "Query failed": the message inline with a Retry button. An error is never shown as empty. */
export function ErrorState({
  error,
  onRetry,
  title,
  retrying = false,
  message: ownMessage,
  retryLabel = "Retry",
  retryDisabled = false,
}: ErrorStateProps) {
  const message = ownMessage ?? describeError(error);
  return (
    <div data-slot="error-state" className="flex flex-col items-start gap-3">
      <Alert variant="destructive">
        <CircleAlertIcon aria-hidden="true" />
        {title ? (
          <>
            <AlertTitle>{title}</AlertTitle>
            <AlertDescription>{message}</AlertDescription>
          </>
        ) : (
          <AlertTitle>{message}</AlertTitle>
        )}
      </Alert>
      <PendingButton
        variant="outline"
        size="touch"
        pending={retrying}
        pendingLabel={retryLabel}
        disabled={retryDisabled}
        onClick={() => onRetry()}
      >
        {retryLabel}
      </PendingButton>
    </div>
  );
}
