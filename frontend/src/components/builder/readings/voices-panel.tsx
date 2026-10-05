"use client";

import { Fragment, useId } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import type { VoiceComment, VoiceSection } from "@/lib/api/types";
import { useVoices } from "@/lib/queries/voices";
import { cn } from "@/lib/utils";
import type { VoicesPassage } from "@/lib/voices";

const LOADING = "Loading the fathers' comments…";
const FAILED = "The fathers' comments couldn't be loaded.";
const NOT_TRANSCRIBED = "Not yet transcribed for this passage.";
const LINKING = "Aquinas, linking the comments";

/** "19 quotations on these verses" (owner's planning answer 3); none checked: "Not yet transcribed". */
function countLine(count: number): string {
  if (count === 0) return NOT_TRANSCRIBED;
  return `${count} ${count === 1 ? "quotation" : "quotations"} on these verses`;
}

/** The text as printed: *...* is italic (the Gospel's words quoted in a comment), never raw HTML. */
function Printed({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\*[^*]+\*)/).map((part, i) =>
        part.startsWith("*") && part.endsWith("*") && part.length > 2 ? (
          <em key={i}>{part.slice(1, -1)}</em>
        ) : (
          <Fragment key={i}>{part}</Fragment>
        ),
      )}
    </>
  );
}

/** "the Gloss" heads its quotation as "The Gloss". */
function heading(father: string): string {
  return father.charAt(0).toUpperCase() + father.slice(1);
}

function Paragraphs({ text, muted = false }: { text: string; muted?: boolean }) {
  return text.split("\n\n").map((paragraph, i) => (
    <p key={i} className={cn("text-base leading-relaxed wrap-break-word", muted && "text-muted-foreground")}>
      <Printed text={paragraph} />
    </p>
  ));
}

function Margin({ notes }: { notes: string[] }) {
  // Each note as printed, with its own stop: "In the margin: ¹ alia re frui. ² al. bonum."
  return notes.length > 0 ? <p className="text-xs text-muted-foreground">In the margin: {notes.join(" ")}</p> : null;
}

function Quotation({ comment }: { comment: VoiceComment }) {
  // The Catena's own words linking the comments ("It follows, ..."): no father's, so no father's name.
  if (comment.father === null) {
    return (
      <li className="grid gap-2">
        <h4 className="text-sm text-muted-foreground">{LINKING}</h4>
        <Paragraphs text={comment.text} muted />
        <Margin notes={comment.notes} />
      </li>
    );
  }
  return (
    <li className="grid gap-2">
      <h4 className="text-sm">
        <span className="font-semibold">{heading(comment.father)}</span>
        {comment.work ? (
          <>
            {" "}
            <span className="text-muted-foreground">{comment.work}</span>
          </>
        ) : null}
      </h4>
      {comment.printed_label ? (
        <p className="text-xs text-muted-foreground">Corrected by the volume&apos;s errata: printed as {comment.printed_label}</p>
      ) : null}
      <Paragraphs text={comment.text} />
      <Margin notes={comment.notes} />
    </li>
  );
}

function Section({ section }: { section: VoiceSection }) {
  const headingId = useId();
  return (
    <section aria-labelledby={headingId} className="grid gap-3 border-t pt-3 first:border-t-0 first:pt-0">
      <div className="grid gap-0.5">
        <h3 id={headingId} className="text-sm font-medium wrap-anywhere">
          {section.reference}
        </h3>
        <a
          href={section.scan_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex min-h-11 items-center justify-self-start text-sm text-primary underline-offset-4 hover:underline md:min-h-0"
        >
          Printed pages {section.pages}, {section.volume}
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      </div>
      {section.status === "checked" ? (
        <ol className="grid gap-5">
          {section.comments.map((comment, i) => (
            <Quotation key={i} comment={comment} />
          ))}
        </ol>
      ) : (
        <p className="text-sm">{NOT_TRANSCRIBED}</p>
      )}
    </section>
  );
}

/**
 * Voices of the Church (Voices V1 spec "The panel"; owner's planning answers 1, 3 and 4, source
 * decision 2, 2026-10-05): under the Gospel's row on step 1, collapsed by default, its button
 * saying how many quotations the Catena Aurea has on these verses. Open, each section that shares
 * a verse with the passage: its verses, a link to its printed pages in the scan, and its
 * quotations exactly as printed (the father, the margin reference, the text with its italics), or
 * "Not yet transcribed for this passage." for a section no one has checked yet; then the credit.
 * Under the lectionary rule the line above says it is the Sunday's Gospel. The open state lives
 * with the caller, so moving the panel (a pick that changes the line) keeps it.
 */
export function VoicesPanel({
  passage,
  open,
  onOpenChange,
}: {
  passage: VoicesPassage;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const query = useVoices(passage.reference);
  // A line the server cannot read as a Gospel passage (its 422, kept as `null` for the session)
  // gets no panel: asking again would not help.
  if (query.data === null) return null;
  // Try again after a failure fetches with no data: that is loading too.
  const loading = query.isPending || (query.isFetching && !query.data);
  const summary = loading ? LOADING : query.data ? countLine(query.data.quotation_count) : FAILED;
  return (
    <div className="grid gap-2">
      {passage.fromLectionary ? (
        <p className="text-sm text-muted-foreground wrap-anywhere">From the Gospel for this Sunday: {passage.reference}</p>
      ) : null}
      <Collapsible open={open} onOpenChange={onOpenChange}>
        <CollapsibleTrigger
          className={cn(
            buttonVariants({ variant: "outline", size: "touch" }),
            "h-auto min-h-11 w-full flex-wrap justify-start gap-x-2 py-2 text-left whitespace-normal",
          )}
        >
          <span className="font-medium">Voices of the Church</span>{" "}
          <span className="font-normal text-muted-foreground">{summary}</span>
        </CollapsibleTrigger>
        <CollapsibleContent className="grid gap-4 pt-3">
          {loading ? (
            <p className="text-sm text-muted-foreground">{LOADING}</p>
          ) : query.data ? (
            <>
              {query.data.sections.map((section) => (
                <Section key={section.id} section={section} />
              ))}
              <p className="text-xs text-muted-foreground">{query.data.credit}</p>
            </>
          ) : (
            <div className="grid justify-items-start gap-2">
              <p className="text-sm">{FAILED}</p>
              <Button
                type="button"
                variant="outline"
                size="touch"
                aria-label="Try again: Voices of the Church"
                onClick={() => void query.refetch()}
              >
                Try again
              </Button>
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
