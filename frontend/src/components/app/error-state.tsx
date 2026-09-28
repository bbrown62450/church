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
};

/** F §4.8 "Query failed": the message inline with a Retry button. An error is never shown as empty. */
export function ErrorState({ error, onRetry, title, retrying = false }: ErrorStateProps) {
  const message = describeError(error);
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
        pendingLabel="Retry"
        onClick={() => onRetry()}
      >
        Retry
      </PendingButton>
    </div>
  );
}
