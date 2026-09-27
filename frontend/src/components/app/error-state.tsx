import { CircleAlertIcon } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { describeError } from "@/lib/api/errors";

export type ErrorStateProps = {
  /** The failed query's error; describeError picks the sentence (F §4.8, ops handoff Ref). */
  error: unknown;
  /** Usually the query's refetch; called with no arguments. */
  onRetry: () => void;
  /** Optional heading above the sentence. */
  title?: string;
};

/** F §4.8 "Query failed": the message inline with a Retry button. An error is never shown as empty. */
export function ErrorState({ error, onRetry, title }: ErrorStateProps) {
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
      <Button variant="outline" size="touch" onClick={() => onRetry()}>
        Retry
      </Button>
    </div>
  );
}
