"use client";

import { InfoIcon, XIcon } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import type { Hymn } from "@/lib/api/types";
import type { HymnPick, Slot } from "@/lib/draft/schema";
import { SLOT_META } from "@/lib/hymns/labels";
import type { Reconciled } from "@/lib/hymns/picks";

import { HymnLabel } from "./hymn-label";
import { HymnPicker } from "./hymn-picker";

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
  /** Under the notices: "No suggestion for this slot." and the other ideas (slice 3b T10). */
  children?: ReactNode;
};

/**
 * One slot (S "Slot cards"): its title and caption; a filled slot shows the
 * hymn (live when its list has loaded, the draft's snapshot until then) with
 * its ▶ Listen link, ✕ and Change, which puts the focused picker in the row's
 * place until Escape or focus leaves (Change waits for the list, so it never
 * focuses a disabled field); an empty slot shows the picker. After ✕ focus
 * moves to the new picker, and after a choice from Change back to Change. The
 * notices sit under the pick.
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
  children,
}: SlotCardProps) {
  const meta = SLOT_META[slot];
  const [changing, setChanging] = useState(false);
  // Where focus goes once the row has re-rendered: the picker after ✕, Change after a choice from Change.
  const focusNext = useRef<"picker" | "change" | null>(null);
  const sectionRef = useRef<HTMLElement>(null);
  const changeRef = useRef<HTMLButtonElement>(null);
  const headingId = `slot-${slot}-title`;

  useEffect(() => {
    if (focusNext.current === null) return;
    const target =
      focusNext.current === "change"
        ? changeRef.current
        : (sectionRef.current?.querySelector<HTMLInputElement>("input[role=combobox]") ?? null);
    if (target === null) return;
    focusNext.current = null;
    target.focus();
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
      onDismiss={autoFocus ? () => setChanging(false) : undefined}
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
        <h3 id={headingId} className="text-base font-medium">
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
                focusNext.current = "picker";
                onRemove();
              }}
            >
              <XIcon aria-hidden="true" />
            </Button>
          </div>
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
