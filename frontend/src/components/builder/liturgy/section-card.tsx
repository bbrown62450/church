"use client";

import { CircleAlertIcon, EllipsisIcon, XIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { PendingButton } from "@/components/app/pending-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { LiturgySection } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import {
  clearCard,
  editCardText,
  needsRegenerateConfirm,
  restoreChurchDefault,
  setCardEnabled,
  type CardOrigin,
} from "@/lib/liturgy/cards";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { useLiturgyReview } from "@/lib/liturgy/review";
import { useAutosize } from "@/lib/use-autosize";
import { cn } from "@/lib/utils";

import { CardNotes, notesId, reviseId } from "./card-notes";
import { STILL_WORKING, useStillWorking } from "./use-still-working";

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

const UNDO_LINES = {
  replaced: "Replaced with a new AI draft.",
  cleared: "Cleared.",
  // The service reviewer's "Revise with these notes".
  revised: "Revised with these notes.",
} as const;

export type SectionCardProps = {
  spec: LiturgySection;
  /** "People: Thanks be to God! Amen." under the Assurance card. */
  assuranceResponse: string;
  /** The church's default benediction, for "Use church default". */
  defaultBenediction: string;
  maxLength: number;
  /** `GET /liturgy/config`'s `ai_available`: when false nothing is sent, and Regenerate is disabled. */
  aiAvailable: boolean;
};

/**
 * A 429's wait (S "Per-card error messages"): true until `retryAt` (ms since
 * the epoch) passes. It counts from that moment, not from when the card
 * mounted, so leaving the step and coming back does not restart it.
 */
export function useRetryWait(retryAt: number | undefined): boolean {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (retryAt === undefined) return;
    const timer = setTimeout(() => setNow(Math.max(Date.now(), retryAt)), Math.max(retryAt - Date.now(), 0));
    return () => clearTimeout(timer);
  }, [retryAt]);
  return retryAt !== undefined && now < retryAt;
}

/**
 * One liturgy section (S "Section card"): a switch named "Include {Label}",
 * the label, a status chip and a ⋯ menu; when on, the textarea (growing up to
 * 60 vh), the section's hint and the Undo line; when off, only "Off — not in
 * the service. Any text is kept." Typing makes the text the user's; Clear
 * text offers Undo; "Use church default" (Benediction) follows the default
 * again. The card's id is `card-{key}`, so Review can link to it.
 *
 * The AI (S "Generate and Regenerate"): an empty card has Generate; a card
 * with text has Regenerate, which asks "Replace your text?" first when the
 * text is the user's or a saved service's, and is disabled when AI is not set
 * up. While queued ("Waiting…") or writing ("Writing…", then "Still
 * working…" after 8 s) the card has a Cancel button and its ⋯ menu is off;
 * while writing the text is read-only. Typing in a queued card, or switching
 * a running card off, cancels its run. An error shows in an alert under the
 * text with Try again when trying again can help; the text never changes.
 * While the card runs its Undo line is hidden, so Undo cannot change the text
 * a queued run is about to replace; it also goes once the card no longer
 * holds the text the action left (another tab edited it). The line is
 * announced through a live region that is always there, as is a bulk run's
 * error (an error the AI bar's banner already explains is not announced).
 *
 * Focus never drops to the page: when the control that had it goes (Cancel,
 * Try again, Undo, Clear, the confirm dialog's Replace text), focus moves to
 * a control that survives or to the card's heading (`tabIndex={-1}`). A
 * retryable error replaces the action row: if focus was in it, it moves to
 * Try again (or the heading while a 429's wait keeps Try again off). A run
 * that ends with the card still empty and no Try again leaves focus on the
 * card's Generate (or its heading), not the page.
 *
 * The service reviewer's notes show under the text (`CardNotes`), and
 * describe the textarea while they show. While "Revise with these notes"
 * runs, the card is read-only and its Regenerate, Try again, ⋯ menu and Undo are off; switching
 * the card off cancels it silently; when it
 * ends, focus goes to the Undo line's button (the text was revised), the
 * Revise button (it failed or was cancelled) or the heading.
 */
/**
 * The Benediction's church-default hint ("… Admins can change it in
 * Settings.", from GET /liturgy/config) with its last "Settings" and what
 * follows it (the full stop) as a link to Settings → Church, where the
 * default lives (6a spec, hand-off from 4; slice 6a-1). The link ends the
 * sentence, so the card's description reads the hint unchanged. Every role
 * gets the link; a member lands on the read-only page. Below `md` the link
 * is a 44 px target (F §4.9) without moving the text around it.
 */
function withSettingsLink(hint: string): ReactNode {
  const at = hint.lastIndexOf("Settings");
  if (at < 0) return hint;
  return (
    <>
      {hint.slice(0, at)}
      <Link
        href="/settings/church"
        className="-my-3 inline-block py-3 underline underline-offset-2 hover:text-foreground md:my-0 md:py-0"
      >
        {hint.slice(at)}
      </Link>
    </>
  );
}

export function SectionCard({ spec, assuranceResponse, defaultBenediction, maxLength, aiAvailable }: SectionCardProps) {
  const { draft, update } = useDraft();
  const generation = useLiturgyGeneration();
  const review = useLiturgyReview();
  const reviewed = review.review?.cards[spec.key];
  const revising = review.revising[spec.key] === true;
  const key = spec.key;
  const card = draft.liturgy.cards[key];
  const run = generation.runs[key];
  // Hidden while the card runs, and gone once its text is not what the action left.
  const undo = run === undefined && generation.undo[key]?.after === card.text ? generation.undo[key] : undefined;
  const error = generation.errors[key];
  const still = useStillWorking(run?.phase === "writing");
  const retryWaiting = useRetryWait(error?.retryAt);
  const [confirming, setConfirming] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const actionRef = useRef<HTMLButtonElement>(null);
  /** "Replace text" was chosen, so the closing dialog sends focus to the running card. */
  const confirmed = useRef(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const undoRef = useRef<HTMLButtonElement>(null);
  /** Set by a handler whose control is about to go: where focus moves after the next render. */
  const focusNext = useRef<(() => HTMLElement | null) | null>(null);
  /** The ⋯ menu's item moved focus itself, so the closing menu leaves it there. */
  const menuMovedFocus = useRef(false);
  const retryRef = useRef<HTMLButtonElement>(null);
  /** Focus is (or was, when its row went) in the action row: Generate, Regenerate, Waiting…, Cancel. */
  const rowHadFocus = useRef(false);
  const shownError = useRef(error);
  useAutosize(textRef, card.text, card.enabled);
  const headingId = `card-${key}-title`;
  const hasText = card.text.trim() !== "";
  const followsDefault = key === "benediction" && card.origin === "default";
  const hint = key === "benediction" ? (followsDefault ? spec.hint : null) : key === "assurance" ? null : spec.hint;
  const showCounter = card.text.length > COUNTER_FROM;
  const notesShown = reviewed !== undefined && (reviewed.notes.length > 0 || reviewed.found === 0);
  const describedBy =
    [
      hint ? `card-${key}-hint` : null,
      key === "assurance" ? `card-${key}-response` : null,
      showCounter ? `card-${key}-count` : null,
      notesShown ? notesId(key) : null,
      error ? `card-${key}-error` : null,
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

  // A revision ended: its Cancel went, so the Undo line (revised), the Revise button (failed, cancelled) or the heading.
  // An older Undo line (Replaced, Cleared) is not the revision's: focus skips it.
  const wasRevising = useRef(revising);
  const revised = undo?.kind === "revised";
  useEffect(() => {
    const before = wasRevising.current;
    wasRevising.current = revising;
    if (!before || revising) return;
    const active = document.activeElement;
    if (active !== null && active !== document.body) return; // focus already went somewhere on purpose
    ((revised ? undoRef.current : null) ?? document.getElementById(reviseId(key)) ?? headingRef.current)?.focus();
  }, [revising, revised, key]);

  // A retryable error took the action row's place while focus was in it: Try again (or the heading) takes it.
  useEffect(() => {
    const before = shownError.current;
    shownError.current = error;
    if (error === undefined || !error.retryable || error === before || !rowHadFocus.current) return;
    rowHadFocus.current = false;
    const active = document.activeElement;
    if (active !== null && active !== document.body) return; // focus already went somewhere on purpose
    const retry = retryRef.current;
    (retry !== null && !retry.disabled ? retry : headingRef.current)?.focus();
  }, [error]);

  // A run ended with the card still empty and no Try again (an error that trying again cannot fix, or a result
  // discarded because the card changed): Cancel went while it had focus, so the card's Generate (or heading) takes it.
  const hadRun = useRef(run !== undefined);
  useEffect(() => {
    const before = hadRun.current;
    hadRun.current = run !== undefined;
    if (!before || run !== undefined || hasText || error?.retryable || !rowHadFocus.current) return;
    const active = document.activeElement;
    if (active !== null && active !== document.body) return; // focus already went somewhere on purpose
    rowHadFocus.current = false;
    const generate = actionRef.current;
    (generate !== null && generate.isConnected && !generate.disabled ? generate : headingRef.current)?.focus();
  }, [run, hasText, error]);

  function edit(text: string) {
    // Typing in a queued card cancels its request, which was never sent; the typed text stays.
    if (run?.phase === "queued") generation.cancel([key]);
    update((d) => editCardText(d, key, text));
    generation.dismissError(key);
    generation.setUndo(key, null);
  }

  function toggle(enabled: boolean) {
    // Switching a running or revising card off cancels it silently; switching it back on does not restart it.
    if (run !== undefined) generation.cancel([key]);
    if (revising) review.cancelRevise(key);
    update((d) => setCardEnabled(d, key, enabled));
    generation.dismissError(key);
  }

  function clear() {
    const previous = { text: card.text, origin: card.origin };
    update((d) => clearCard(d, key));
    generation.dismissError(key);
    generation.setUndo(key, { kind: "cleared", previous, after: "" });
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

  function start() {
    generation.generate([key], { aiAvailable });
  }

  /** Generate, Regenerate and Try again: replacing the user's own or saved text asks first. */
  function write() {
    if (needsRegenerateConfirm(card)) {
      confirmed.current = false;
      setConfirming(true);
    } else {
      start();
      // Try again's alert goes; Generate becomes Waiting… (disabled): the card's Cancel takes focus.
      focusNext.current = () => actionRef.current;
    }
  }

  function cancelRun() {
    generation.cancel([key]);
    focusNext.current = () => actionRef.current;
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
            disabled={menuItems.length === 0 || run !== undefined || revising}
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
            readOnly={run?.phase === "writing" || revising}
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
              {followsDefault ? withSettingsLink(hint) : hint}
            </p>
          ) : null}
          <CardNotes sectionKey={key} label={spec.label} headingId={headingId} busy={run !== undefined} />
          {/* Always there, so the line is announced when it appears (a region inserted with its text often is not). */}
          <p className="sr-only" aria-live="polite">
            {undo ? `${spec.label}: ${UNDO_LINES[undo.kind]}` : null}
          </p>
          {undo ? (
            <p className="flex flex-wrap items-center gap-x-1 text-sm">
              {UNDO_LINES[undo.kind]}
              <Button ref={undoRef} variant="link" className="h-11 px-1 md:h-auto" disabled={revising} onClick={undoLast}>
                Undo
              </Button>
            </p>
          ) : null}
          {/* A bulk run's errors are announced politely here, not as one alert per card. */}
          <p className="sr-only" aria-live="polite">
            {error?.bulk && !error.quiet ? error.message : null}
          </p>
          {error ? (
            <Alert id={`card-${key}-error`} variant="destructive" role={error.bulk ? undefined : "alert"}>
              <CircleAlertIcon aria-hidden="true" />
              <AlertTitle className="whitespace-normal">{error.message}</AlertTitle>
              {error.retryable || error.link ? (
                <AlertDescription className="flex flex-wrap gap-2 pt-2">
                  {error.retryable ? (
                    <Button ref={retryRef} variant="outline" size="touch" disabled={retryWaiting || revising} onClick={write}>
                      Try again
                    </Button>
                  ) : null}
                  {error.link ? (
                    <Link href={error.link.href} className={buttonVariants({ variant: "outline", size: "touch" })}>
                      {error.link.label}
                    </Link>
                  ) : null}
                </AlertDescription>
              ) : null}
            </Alert>
          ) : null}
          {error?.retryable ? null : (
            <div
              className="flex flex-wrap items-center justify-end gap-2"
              onFocus={() => {
                rowHadFocus.current = true;
              }}
              onBlur={(event) => {
                // Focus moving elsewhere; a removed button (the row going) leaves the flag for the effect above.
                if (event.relatedTarget !== null && !event.currentTarget.contains(event.relatedTarget)) rowHadFocus.current = false;
              }}
            >
              {run ? (
                <>
                  {run.phase === "queued" ? (
                    <Button variant="outline" size="touch" disabled>
                      Waiting…
                    </Button>
                  ) : (
                    <PendingButton pending pendingLabel="Writing…" size="touch">
                      Writing…
                    </PendingButton>
                  )}
                  <Button
                    ref={actionRef}
                    variant="ghost"
                    size="icon-lg"
                    className="size-11 md:size-8"
                    aria-label={`Cancel ${spec.label}`}
                    onClick={cancelRun}
                  >
                    <XIcon aria-hidden="true" />
                  </Button>
                </>
              ) : hasText ? (
                <>
                  {aiAvailable ? null : <span className="text-sm text-muted-foreground">AI isn&apos;t set up</span>}
                  <Button ref={actionRef} variant="outline" size="touch" disabled={!aiAvailable || revising} onClick={write}>
                    Regenerate
                  </Button>
                </>
              ) : (
                <Button ref={actionRef} size="touch" onClick={write}>
                  Generate
                </Button>
              )}
              <p className="w-full text-right text-sm text-muted-foreground" aria-live="polite">
                {still ? STILL_WORKING : null}
              </p>
            </div>
          )}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Off — not in the service. Any text is kept.</p>
      )}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Replace your text?"
        description={`Regenerate replaces the text in ${spec.label} with a new AI draft. You can undo right after.`}
        confirmLabel="Replace text"
        cancelLabel="Keep my text"
        onConfirm={() => {
          confirmed.current = true;
          setConfirming(false);
          start();
        }}
        // Keep my text: back to the button that opened it. Replace text: that button is gone, so the card's Cancel.
        finalFocus={() => {
          if (!confirmed.current) return true;
          const cancel = actionRef.current;
          return cancel !== null && cancel.isConnected ? cancel : headingRef.current;
        }}
      />
    </section>
  );
}
