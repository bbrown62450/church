"use client";

import { EllipsisIcon } from "lucide-react";
import { useEffect, useRef } from "react";

import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgySection } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { clearCard, editCardText, restoreChurchDefault, setCardEnabled, type CardOrigin } from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

/** The status chip for each origin (S "Section card"). */
export const ORIGIN_CHIPS: Record<CardOrigin, string> = {
  empty: "Empty",
  typed: "Your text",
  ai: "AI draft",
  default: "Church default",
  archive: "From saved service",
};

/** The counter shows past this many characters (S "Other card rules"). */
export const COUNTER_FROM = 18_000;

const UNDO_LINES = { replaced: "Replaced with a new AI draft.", cleared: "Cleared." } as const;

export type SectionCardProps = {
  spec: LiturgySection;
  /** "People: Thanks be to God! Amen." under the Assurance card. */
  assuranceResponse: string;
  /** The church's default benediction, for "Use church default". */
  defaultBenediction: string;
  maxLength: number;
};

/**
 * One liturgy section (S "Section card"): a switch named "Include {Label}",
 * the label, a status chip and a ⋯ menu; when on, the textarea (growing up to
 * 60 vh), the section's hint and the Undo line; when off, only "Off — not in
 * the service. Any text is kept." Typing makes the text the user's; Clear
 * text offers Undo; "Use church default" (Benediction) follows the default
 * again. The card's id is `card-{key}`, so Review can link to it.
 *
 * Focus never drops to the page: when the control that had it goes, focus
 * moves to a control that survives or to the card's heading (`tabIndex={-1}`).
 */
export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength }: SectionCardProps) {
  const { draft, update } = useDraft();
  const generation = useLiturgyGeneration();
  const key = spec.key;
  const card = draft.liturgy.cards[key];
  const undo = generation.undo[key];
  const textRef = useRef<HTMLTextAreaElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const undoRef = useRef<HTMLButtonElement>(null);
  /** Set by a handler whose control is about to go: where focus moves after the next render. */
  const focusNext = useRef<(() => HTMLElement | null) | null>(null);
  /** The ⋯ menu's item moved focus itself, so the closing menu leaves it there. */
  const menuMovedFocus = useRef(false);
  useAutosize(textRef, card.text, card.enabled);
  const headingId = `card-${key}-title`;
  const hasText = card.text.trim() !== "";
  const followsDefault = key === "benediction" && card.origin === "default";
  const hint = key === "benediction" ? (followsDefault ? spec.hint : null) : key === "assurance" ? null : spec.hint;
  const showCounter = card.text.length > COUNTER_FROM;
  const describedBy =
    [
      hint ? `card-${key}-hint` : null,
      key === "assurance" ? `card-${key}-response` : null,
      showCounter ? `card-${key}-count` : null,
    ]
      .filter(Boolean)
      .join(" ") || undefined;

  // A control that can take focus, or the card's heading.
  useEffect(() => {
    const target = focusNext.current;
    if (target === null) return;
    focusNext.current = null;
    const element = target();
    const usable = element !== null && element.isConnected && !(element as HTMLButtonElement).disabled;
    (usable ? element : headingRef.current)?.focus();
  });

  function edit(text: string) {
    update((d) => editCardText(d, key, text));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  function toggle(enabled: boolean) {
    update((d) => setCardEnabled(d, key, enabled));
    generation.dismissError(key);
  }

  function clear() {
    const previous = { text: card.text, origin: card.origin };
    update((d) => clearCard(d, key));
    generation.dismissError(key);
    generation.setUndo(key, { kind: "cleared", previous });
    // The ⋯ menu may be disabled now (an empty card); focus goes to "Cleared. Undo".
    menuMovedFocus.current = true;
    focusNext.current = () => undoRef.current;
  }

  function undoLast() {
    generation.applyUndo(key);
    focusNext.current = () => null;
  }

  function followDefault() {
    update((d) => restoreChurchDefault(d, defaultBenediction));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  const menuItems = [
    hasText ? (
      <DropdownMenuItem key="clear" onClick={clear} className="min-h-11 md:min-h-8">
        Clear text
      </DropdownMenuItem>
    ) : null,
    key === "benediction" && card.origin !== "default" ? (
      <DropdownMenuItem key="default" onClick={followDefault} className="min-h-11 md:min-h-8">
        Use church default
      </DropdownMenuItem>
    ) : null,
  ].filter(Boolean);

  return (
    <section
      id={`card-${key}`}
      aria-labelledby={headingId}
      className={cn("grid scroll-mt-24 gap-3 rounded-lg border p-4", !card.enabled && "bg-muted/40")}
    >
      {/* Below sm the chips take their own line under the title, so a long label never pushes the menu out. */}
      <div className="flex min-w-0 flex-wrap items-center gap-x-3 gap-y-1">
        <Switch
          checked={card.enabled}
          onCheckedChange={(checked) => toggle(checked)}
          aria-label={`Include ${spec.label}`}
          className="after:-inset-y-3.5"
        />
        <h3
          ref={headingRef}
          id={headingId}
          tabIndex={-1}
          data-card-heading=""
          className="min-w-0 flex-1 text-base font-medium outline-none"
        >
          {spec.label}
        </h3>
        <div className="flex flex-wrap gap-1 max-sm:order-last max-sm:basis-full max-sm:pl-11 sm:justify-end">
          {spec.pastor_copy_only ? <Badge variant="outline">Pastor&apos;s copy only</Badge> : null}
          <Badge variant="secondary">{ORIGIN_CHIPS[card.origin]}</Badge>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`More actions for ${spec.label}`}
            disabled={menuItems.length === 0}
            className={cn(buttonVariants({ variant: "ghost", size: "icon-lg" }), "size-11 shrink-0 md:size-8")}
          >
            <EllipsisIcon aria-hidden="true" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="w-auto min-w-44"
            finalFocus={() => {
              const moved = menuMovedFocus.current;
              menuMovedFocus.current = false;
              return !moved;
            }}
          >
            {menuItems}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {card.enabled ? (
        <>
          <Textarea
            ref={textRef}
            aria-labelledby={headingId}
            aria-describedby={describedBy}
            value={card.text}
            placeholder="Type your own text, or tap Generate."
            maxLength={maxLength}
            rows={spec.rows}
            style={{ minHeight: `calc(${spec.rows}lh + 1rem + 2px)` }}
            className="max-h-[60vh] overflow-y-auto"
            onChange={(event) => edit(event.target.value)}
          />
          {showCounter ? (
            <p id={`card-${key}-count`} className="text-right text-xs text-muted-foreground">
              {card.text.length.toLocaleString("en-US")} / {maxLength.toLocaleString("en-US")}
            </p>
          ) : null}
          {key === "assurance" ? (
            <div id={`card-${key}-response`} className="grid gap-0.5 text-sm">
              <p className="font-medium">{assuranceResponse}</p>
              {spec.hint ? <p className="text-muted-foreground">{spec.hint}</p> : null}
            </div>
          ) : null}
          {hint ? (
            <p id={`card-${key}-hint`} className="text-sm text-muted-foreground">
              {hint}
            </p>
          ) : null}
          {undo ? (
            <p className="flex flex-wrap items-center gap-x-1 text-sm" aria-live="polite">
              {UNDO_LINES[undo.kind]}
              <Button ref={undoRef} variant="link" className="h-11 px-1 md:h-auto" onClick={undoLast}>
                Undo
              </Button>
            </p>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Off — not in the service. Any text is kept.</p>
      )}
    </section>
  );
}
