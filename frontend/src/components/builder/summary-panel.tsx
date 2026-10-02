"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { formatLongDate, formatSavedAt } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectivePicks } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { reviewStatus } from "@/lib/draft/status";
import { SHIPPED_STEPS, stepById, type StepId } from "@/lib/draft/steps";
import { splitAlternatives } from "@/lib/scripture-refs";

import { LiturgySummaryBlock } from "./liturgy/liturgy-summary-block";
import { SummaryHymns } from "./summary-hymns";

/** A pick matches a line when it is the line or one of its " or " alternatives. */
function holds(line: string, pick: string | null): boolean {
  return pick !== null && (line === pick || splitAlternatives(line).includes(pick));
}

function Block({ title, step, onNavigate, children }: { title: string; step: StepId; onNavigate?: () => void; children: ReactNode }) {
  return (
    <div className="grid gap-1">
      <h3 className="text-sm font-medium">
        <Link href={stepById(step).href} onClick={onNavigate} className="inline-flex min-h-11 min-w-11 items-center underline-offset-4 hover:underline lg:min-h-0 lg:min-w-0">
          {title}
        </Link>
      </h3>
      <div className="text-sm text-muted-foreground">{children}</div>
    </div>
  );
}

function Soon() {
  return <p>Available soon</p>;
}

/** The archive half of the status line (S "Step status and summary panel"; slice 5a-3). */
export function archiveSummary(draft: DraftV1): string {
  if (draft.editing === null) return "Not in archive";
  const saved = `In archive (saved ${formatSavedAt(draft.editing.saved_at)})`;
  return reviewStatus(draft) === "saved" ? saved : `${saved} · Unsaved changes`;
}

/**
 * The draft at a glance (S "SummaryPanel"; F §4.7): a sticky column from
 * `lg`, the bottom sheet below it. Each block links to its step. The Readings
 * block and the occasion line show once "readings" ships (slice 2c), the three
 * hymns once "hymns" ships (slice 3b), the liturgy counts once "liturgy" ships
 * (slice 4b); 5a-3 wires the archive half of the status line, which (alone) links to Review.
 */
export function SummaryPanel({ shipped = SHIPPED_STEPS, onNavigate }: { shipped?: ReadonlySet<StepId>; onNavigate?: () => void }) {
  const { draft, persistence } = useDraft();
  const readingsShipped = shipped.has("readings");
  const hymnsShipped = shipped.has("hymns");
  const liturgyShipped = shipped.has("liturgy");
  const lines = cleanScriptures(draft);
  const picks = effectivePicks(draft);
  const saved = persistence === "ok" ? "Draft saved on this device" : "Draft not saved on this device";

  return (
    <div className="grid gap-4">
      <Block title="Date" step="readings" onNavigate={onNavigate}>
        <p className="text-foreground">{formatLongDate(draft.readings.date_iso) || "No service date"}</p>
        {readingsShipped ? <p className="wrap-anywhere">{draft.readings.occasion.trim() || "No occasion yet"}</p> : null}
      </Block>
      <Block title="Readings" step="readings" onNavigate={onNavigate}>
        {!readingsShipped ? (
          <Soon />
        ) : lines.length === 0 ? (
          <p>No readings yet</p>
        ) : (
          <ul className="grid gap-1">
            {lines.map((line, i) => (
              <li key={`${i}:${line}`} className="flex flex-wrap items-center gap-1.5 wrap-anywhere text-foreground">
                <span className="min-w-0 wrap-anywhere">{line}</span>
                {holds(line, picks.ot) ? <Badge variant="secondary">{picks.otAuto ? "OT (auto)" : "OT"}</Badge> : null}
                {holds(line, picks.nt) ? <Badge variant="secondary">{picks.ntAuto ? "NT (auto)" : "NT"}</Badge> : null}
              </li>
            ))}
          </ul>
        )}
      </Block>
      <Block title="Hymns" step="hymns" onNavigate={onNavigate}>
        {hymnsShipped ? <SummaryHymns /> : <Soon />}
      </Block>
      <Block title="Liturgy" step="liturgy" onNavigate={onNavigate}>
        {liturgyShipped ? <LiturgySummaryBlock /> : <Soon />}
      </Block>
      <p className="border-t pt-3 text-xs text-muted-foreground">
        {saved} ·{" "}
        <Link
          href={stepById("review").href}
          onClick={onNavigate}
          className="inline-flex min-h-11 items-center underline-offset-4 hover:underline lg:min-h-0"
        >
          {archiveSummary(draft)}
        </Link>
      </p>
    </div>
  );
}
