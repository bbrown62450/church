"use client";

import { Button } from "@/components/ui/button";
import { usePassage } from "@/lib/queries/passages";

import { rateLimitMessage, useWaitOver } from "./use-wait-over";

/** "Try again", named with the reference ("Try again: Mark 1:1-8"), since every open row can show one. */
function TryAgain({
  reference,
  onClick,
  disabled = false,
}: {
  reference: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <Button
      type="button"
      variant="outline"
      size="touch"
      disabled={disabled}
      aria-label={`Try again: ${reference}`}
      onClick={onClick}
    >
      Try again
    </Button>
  );
}

/**
 * An open row's passage text (S UX item 6 table): the first matching state of
 * loading, every section loaded, some text, not found, unavailable or a
 * failed request, a rate limit, or the server's 422. Text renders as React
 * text with its line breaks kept; " or " alternatives get one headed section
 * each.
 */
export function PassageText({ reference, translation }: { reference: string; translation: string }) {
  const query = usePassage(reference, translation, true);
  const limited = query.error?.code === "rate_limited" ? query.error : null;
  const waitOver = useWaitOver(limited);
  const retry = () => void query.refetch();

  if (query.isPending) return <p className="text-sm text-muted-foreground">Loading text…</p>;

  if (query.isError) {
    if (limited) {
      return (
        <div className="grid justify-items-start gap-2">
          <p className="text-sm">{rateLimitMessage(limited, waitOver)}</p>
          <TryAgain reference={reference} onClick={retry} disabled={!waitOver || query.isFetching} />
        </div>
      );
    }
    if (query.error.status === 422) return <p className="text-sm">{query.error.message}</p>;
    return (
      <div className="grid justify-items-start gap-2">
        <p className="text-sm">Passage text isn&apos;t available right now.</p>
        <TryAgain reference={reference} onClick={retry} disabled={query.isFetching} />
      </div>
    );
  }

  const passage = query.data;
  const headed = passage.sections.length > 1;
  const anyText = passage.sections.some((section) => section.text);

  if (!anyText) {
    if (passage.status === "not_found") {
      return (
        <p className="text-sm">
          Couldn&apos;t find this passage. Check the reference, for example “Matthew 17:1-9”.
        </p>
      );
    }
    return (
      <div className="grid justify-items-start gap-2">
        <p className="text-sm">Passage text isn&apos;t available right now.</p>
        <TryAgain reference={reference} onClick={retry} disabled={query.isFetching} />
      </div>
    );
  }

  return (
    <div className="grid gap-3">
      {passage.sections.map((section, i) => (
        <div key={`${i}:${section.reference}`} className="grid gap-1">
          {headed ? <p className="text-xs font-medium text-muted-foreground">{section.reference}</p> : null}
          {section.text ? (
            <p className="text-sm whitespace-pre-wrap">{section.text}</p>
          ) : (
            <p className="text-sm">Couldn&apos;t load {section.reference}.</p>
          )}
        </div>
      ))}
      {passage.status !== "ok" ? (
        <div className="grid justify-items-start gap-2">
          <p className="text-sm text-muted-foreground">Part of this passage couldn&apos;t be loaded.</p>
          {passage.status === "unavailable" ? (
            <TryAgain reference={reference} onClick={retry} disabled={query.isFetching} />
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
