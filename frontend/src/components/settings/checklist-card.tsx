"use client";

import { ChevronDownIcon, XIcon } from "lucide-react";
import { useRef, type KeyboardEvent } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Textarea } from "@/components/ui/textarea";
import { AT_MOST_POINTS, MAX_POINT_LENGTH, MAX_POINTS, type Checklist } from "@/lib/settings/rubric";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

export const THEME_NOTE =
  "The builder first gathers opening and closing hymns by theme (gathering, praise, sending and similar). This checklist then guides which of them the AI suggests.";

/** The id of a checklist's point `index` (the page moves focus to it). */
export const pointId = (list: Checklist, index: number) => `rubric-${list.key}-${index}`;

/** A pasted or typed line break becomes a space: a point is one line (the server's whitespace rule). */
const oneLine = (text: string) => text.replace(/\r\n|\r|\n/g, " ");

function Point({
  list,
  index,
  value,
  onChange,
  onEnter,
  onRemove,
}: {
  list: Checklist;
  index: number;
  value: string;
  onChange: (value: string) => void;
  onEnter: () => void;
  onRemove: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);
  useAutosize(ref, value);
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
    event.preventDefault(); // Enter adds a point below instead of a line break
    onEnter();
  };
  return (
    <li className="flex items-start gap-1">
      <Textarea
        id={pointId(list, index)}
        ref={ref}
        rows={1}
        value={value}
        maxLength={MAX_POINT_LENGTH}
        aria-label={`Point ${index + 1} of ${list.label}`}
        className="min-h-11 flex-1 resize-none md:min-h-9"
        onChange={(e) => onChange(oneLine(e.target.value))}
        onKeyDown={onKeyDown}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-11 shrink-0 md:size-9"
        aria-label={`Remove point ${index + 1} from ${list.label}`}
        onClick={onRemove}
      >
        <XIcon aria-hidden="true" />
      </Button>
    </li>
  );
}

/**
 * One checklist of the rubric (slice 6a-3a; 6a spec UX §6): "A good
 * {Label}:" and its points. Owners and admins edit each point (Enter adds one
 * below, a line break becomes a space), remove one, add one (at most 12) and
 * put the default points back (unsaved until **Save rubric**); members read
 * the points as text. The **Customized** badge follows the points. A `note`
 * (the theme note) shows under the card, closed or open.
 */
export function ChecklistCard({
  list,
  points,
  defaultPoints,
  customized,
  admin,
  open,
  onOpenChange,
  onChange,
  onFocusPoint,
  error,
  note,
}: {
  list: Checklist;
  points: readonly string[];
  defaultPoints: readonly string[];
  customized: boolean;
  admin: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChange: (points: string[]) => void;
  /** Focus point `index` once it is on the page; null for the card's **Add a point** button. */
  onFocusPoint: (index: number | null) => void;
  error?: string;
  note?: string;
}) {
  const full = points.length >= MAX_POINTS;
  const errorId = `rubric-${list.key}-error`;
  const insert = (index: number) => {
    if (full) return;
    onChange([...points.slice(0, index), "", ...points.slice(index)]);
    onFocusPoint(index);
  };
  const remove = (index: number) => {
    const next = points.filter((_p, i) => i !== index);
    onChange(next);
    onFocusPoint(next.length === 0 ? null : Math.min(index, next.length - 1));
  };
  const card = (
    <Collapsible open={open} onOpenChange={onOpenChange} className="rounded-lg border">
      <CollapsibleTrigger className="flex min-h-11 w-full items-center gap-2 rounded-lg px-4 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
        <span className="min-w-0 flex-1 text-sm font-medium">{list.label}</span>
        {customized ? <Badge variant="secondary">Customized</Badge> : null}
        <ChevronDownIcon aria-hidden="true" className={cn("size-4 shrink-0 transition-transform", open && "rotate-180")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="grid gap-2 px-4 pb-4">
        <p id={`rubric-${list.key}-intro`} className="text-sm">{`A good ${list.label}:`}</p>
        {admin ? (
          <ol aria-labelledby={`rubric-${list.key}-intro`} aria-describedby={error ? errorId : undefined} className="grid gap-2">
            {points.map((point, index) => (
              <Point
                key={index}
                list={list}
                index={index}
                value={point}
                onChange={(value) => onChange(points.map((p, i) => (i === index ? value : p)))}
                onEnter={() => insert(index + 1)}
                onRemove={() => remove(index)}
              />
            ))}
          </ol>
        ) : (
          <ul aria-labelledby={`rubric-${list.key}-intro`} className="grid list-disc gap-1 pl-5 text-sm">
            {points.map((point, index) => (
              <li key={index} className="break-words">
                {point}
              </li>
            ))}
          </ul>
        )}
        {error ? (
          <p id={errorId} role="alert" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        {admin ? (
          <div className="flex flex-wrap items-center gap-x-4">
            <Button
              type="button"
              variant="link"
              id={`rubric-${list.key}-add`}
              className="h-11 px-0 md:h-auto"
              disabled={full}
              onClick={() => insert(points.length)}
            >
              Add a point
            </Button>
            <Button
              type="button"
              variant="link"
              className="h-11 px-0 md:h-auto"
              disabled={points.length === defaultPoints.length && points.every((p, i) => p === defaultPoints[i])}
              onClick={() => {
                onChange([...defaultPoints]);
                onFocusPoint(0); // the button is disabled now: focus goes to the first point
              }}
            >
              Reset to default
            </Button>
            {full ? <p className="w-full text-sm text-muted-foreground">{AT_MOST_POINTS}</p> : null}
          </div>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
  if (!note) return card;
  // The note sits under the card, outside the part that collapses, so a phone shows it while the card is closed.
  return (
    <div className="grid gap-2">
      {card}
      <p className="text-sm text-muted-foreground">{note}</p>
    </div>
  );
}
