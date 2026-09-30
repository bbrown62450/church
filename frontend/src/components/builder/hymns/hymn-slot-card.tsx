"use client";

import { InfoIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { PendingButton } from "@/components/app/pending-button";
import { Button } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import type { HymnPick, Slot } from "@/lib/draft/schema";
import { SLOT_META } from "@/lib/hymns/labels";
import type { Reconciled } from "@/lib/hymns/picks";

import { HymnLabel } from "./hymn-label";
import { HymnPicker } from "./hymn-picker";

/**
 * Where focus goes after ✕: the card's heading, so a phone's keyboard does not
 * pop up (owner answer 2026-09-30); "picker" would focus the slot's new picker,
 * with the heading as the fallback while it is not there or still loading.
 * Either way focus never falls to the page.
 */
export const FOCUS_AFTER_REMOVE: "picker" | "heading" = "heading";

export type SlotCardProps = {
  slot: Slot;
  /** The draft's snapshot. */
  pick: HymnPick | null;
  /** The pick against the loaded lists (`reconcilePick`); the live hymn wins when found. */
  reconciled: Reconciled | null;
  /** The selected hymnal's list for the picker; undefined while it loads. */
  list: readonly Hymn[] | undefined;
  /** False when an error or the empty hymnal replaces the pickers. */
  pickerAvailable: boolean;
  excludeRecent: boolean;
  serviceDateIso: string;
  showHymnal: boolean;
  onChoose: (h: Hymn) => void;
  /** ✕: the step clears the slot and offers Undo. */
  onRemove: () => void;
  /** Under the pick, in muted text; none changes the pick (S "Notices"). */
  notices: readonly string[];
  /**
   * The pick's own hymnal (not the selected one) whose list failed: "Couldn't
   * load {code}." with Retry, instead of waiting for it forever.
   */
  listFailed?: { code: string; retrying: boolean; retry: () => void } | null;
  /** Under the notices: "No suggestion for this slot." and the other ideas (slice 3b T10). */
  children?: ReactNode;
};

/**
 * One slot (S "Slot cards"): its title and caption; a filled slot shows the
 * hymn (live when its list has loaded, the draft's snapshot until then) with
 * its ▶ Listen link, ✕ and Change, which puts the focused picker in the row's
 * place until Escape or focus leaves the picker (Change waits for the list, so
 * it never focuses a disabled field); an empty slot shows the picker. After ✕
 * focus moves to the card's heading (`FOCUS_AFTER_REMOVE`); after a choice
 * from Change, or Escape, back to Change. Tab from Change's picker moves to
 * its ▾ button and then on, closing it; focus is never taken back from where
 * Tab put it. The notices sit under the pick; a pick whose own hymnal failed
 * to load says so, with Retry.
 */
export function HymnSlotCard({
  slot,
  pick,
  reconciled,
  list,
  pickerAvailable,
  excludeRecent,
  serviceDateIso,
  showHymnal,
  onChoose,
  onRemove,
  notices,
  listFailed = null,
  children,
}: SlotCardProps) {
  const meta = SLOT_META[slot];
  const [changing, setChanging] = useState(false);
  // A pick cleared elsewhere (another tab, Undo) ends Change, so a later pick shows its row.
  if (changing && pick === null) setChanging(false);
  // Where focus goes once the row has re-rendered: the picker (or heading) after ✕, Change after Change's picker.
  const focusNext = useRef<"picker" | "heading" | "change" | null>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const changeRef = useRef<HTMLButtonElement>(null);
  const headingId = `slot-${slot}-title`;

  useEffect(() => {
    const want = focusNext.current;
    if (want === null) return;
    // Wait for the render that shows the change: the empty slot after ✕, the row after Change.
    if (want === "change" ? changing : pick !== null) return;
    focusNext.current = null;
    const section = sectionRef.current;
    const active = document.activeElement;
    // Focus that Tab (or a click) moved elsewhere stays there.
    if (active !== null && active !== document.body && !(section?.contains(active) ?? false)) return;
    const input = section?.querySelector<HTMLInputElement>("input[role=combobox]") ?? null;
    const target =
      want === "change" ? changeRef.current : want === "picker" && input !== null && !input.disabled ? input : null;
    (target ?? headingRef.current)?.focus();
  });

  const live = reconciled?.status === "ok" ? reconciled.live : null;
  const picker = (autoFocus: boolean) => (
    <HymnPicker
      label={meta.title}
      list={list}
      excludeRecent={excludeRecent}
      serviceDateIso={serviceDateIso}
      showHymnal={showHymnal}
      autoFocus={autoFocus}
      onDismiss={
        autoFocus
          ? () => {
              focusNext.current = "change";
              setChanging(false);
            }
          : undefined
      }
      onChoose={(h) => {
        if (changing) focusNext.current = "change";
        setChanging(false);
        onChoose(h);
      }}
    />
  );

  return (
    <section ref={sectionRef} aria-labelledby={headingId} className="grid gap-3 rounded-lg border p-4">
      <div>
        <h3 id={headingId} ref={headingRef} tabIndex={-1} className="text-base font-medium">
          {meta.title}
        </h3>
        <p className="text-sm text-muted-foreground">{meta.caption}</p>
      </div>
      {pick === null ? (
        pickerAvailable ? picker(false) : null
      ) : changing && pickerAvailable ? (
        picker(true)
      ) : (
        <div className="grid gap-2">
          <div className="flex min-w-0 items-center gap-1">
            <div className="min-w-0 flex-1 font-medium">
              <HymnLabel hymn={live ?? pick} showHymnal={showHymnal} listen />
            </div>
            <Button
              variant="ghost"
              size="icon-lg"
              className="size-11 shrink-0 md:size-8"
              aria-label={`Remove ${(live ?? pick).title}`}
              onClick={() => {
                focusNext.current = FOCUS_AFTER_REMOVE;
                onRemove();
              }}
            >
              <XIcon aria-hidden="true" />
            </Button>
          </div>
          {listFailed ? (
            <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
              <span>Couldn&apos;t load {listFailed.code}.</span>
              <PendingButton
                variant="outline"
                size="touch"
                pending={listFailed.retrying}
                pendingLabel="Retry"
                aria-label={`Retry loading ${listFailed.code}`}
                onClick={() => listFailed.retry()}
              >
                Retry
              </PendingButton>
            </div>
          ) : null}
          {pickerAvailable ? (
            <div>
              <Button
                ref={changeRef}
                variant="outline"
                size="touch"
                disabled={list === undefined}
                onClick={() => setChanging(true)}
              >
                Change
              </Button>
            </div>
          ) : null}
        </div>
      )}
      {notices.length > 0 ? (
        <ul className="grid gap-1 text-sm text-muted-foreground">
          {notices.map((notice) => (
            <li key={notice} className="flex gap-1.5">
              <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span>{notice}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {children}
    </section>
  );
}
