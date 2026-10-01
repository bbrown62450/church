"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { OutlineItem } from "@/lib/api/types";
import { effectivePicks } from "@/lib/draft/readings";
import type { DraftV1, Slot } from "@/lib/draft/schema";
import { cn } from "@/lib/utils";

import { SERMON_TITLE_ID } from "./sermon-title-field";

const HYMN_SLOTS: Partial<Record<OutlineItem["value_source"], Slot>> = {
  hymn_opening: "opening",
  hymn_response: "response",
  hymn_closing: "closing",
};

const ROW = "flex min-h-11 w-full min-w-0 flex-wrap items-center gap-x-1 border-l-2 pl-3 text-left text-sm text-muted-foreground";

/**
 * One landmark of the order of worship (S UX "Landmark rows"): a single muted
 * line, not a card, with the value the Word files will print. Hymns show the
 * slot's title and open Hymns; the readings show `effectivePicks` (an
 * automatic one marked "auto") and open Date & readings; the Sermon row shows
 * the title, or "[Sermon title]" when blank, and focuses the sermon field;
 * the Affirmation row shows its fixed text.
 */
export function OutlineLandmark({ item, draft }: { item: OutlineItem; draft: DraftV1 }) {
  const label = <span className="font-medium text-foreground">{item.label}</span>;
  const value = (text: ReactNode) => <span className="min-w-0 wrap-anywhere"> · {text}</span>;
  const slot = HYMN_SLOTS[item.value_source];
  if (slot) {
    const pick = draft.hymns.slots[slot];
    return (
      <Link href="/builder/hymns" className={cn(ROW, "hover:text-foreground")}>
        {label}
        {pick ? value(pick.title) : null}
      </Link>
    );
  }
  if (item.value_source === "reading_ot" || item.value_source === "reading_nt") {
    const picks = effectivePicks(draft);
    const ref = item.value_source === "reading_ot" ? picks.ot : picks.nt;
    const auto = item.value_source === "reading_ot" ? picks.otAuto : picks.ntAuto;
    return (
      <Link href="/builder/readings" className={cn(ROW, "hover:text-foreground")}>
        {label}
        {ref
          ? value(
              <>
                {ref}
                {auto ? <span className="text-xs"> auto</span> : null}
              </>,
            )
          : null}
      </Link>
    );
  }
  if (item.value_source === "sermon_title") {
    const title = draft.liturgy.sermon_title.trim();
    return (
      <button
        type="button"
        className={cn(ROW, "hover:text-foreground")}
        onClick={() => document.getElementById(SERMON_TITLE_ID)?.focus()}
      >
        {label}
        {value(title === "" ? <span className="italic">[Sermon title]</span> : title)}
      </button>
    );
  }
  return (
    <div className={ROW}>
      {label}
      {item.fixed_text ? value(item.fixed_text) : null}
    </div>
  );
}
