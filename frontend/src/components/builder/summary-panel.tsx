"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { formatLongDate } from "@/lib/dates";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectivePicks } from "@/lib/draft/readings";
import { SHIPPED_STEPS, stepById, type StepId } from "@/lib/draft/steps";
import { splitAlternatives } from "@/lib/scripture-refs";

/** A pick matches a line when it is the line or one of its " or " alternatives. */
function holds(line: string, pick: string | null): boolean {
  return pick !== null && (line === pick || splitAlternatives(line).includes(pick));
}

function Block({ title, step, onNavigate, children }: { title: string; step: StepId; onNavigate?: () => void; children: ReactNode }) {
  return (
    <div className="grid gap-1">
      <h3 className="text-sm font-medium">
        <Link href={stepById(step).href} onClick={onNavigate} className="underline-offset-4 hover:underline">
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

/**
 * The draft at a glance (S "SummaryPanel"; F §4.7): a sticky column from
 * `lg`, the bottom sheet below it. Each block links to its step. The Readings
 * block and the occasion line show once "readings" ships (slice 2c); slices 3
 * and 4 replace the Hymns and Liturgy blocks, and 5a wires the archive half
 * of the status line.
 */
export function SummaryPanel({ shipped = SHIPPED_STEPS, onNavigate }: { shipped?: ReadonlySet<StepId>; onNavigate?: () => void }) {
  const { draft, persistence } = useDraft();
  const readingsShipped = shipped.has("readings");
  const lines = cleanScriptures(draft);
  const picks = effectivePicks(draft);
  const saved = persistence === "ok" ? "Draft saved on this device" : "Draft not saved on this device";

  return (
    <div className="grid gap-4">
      <Block title="Date" step="readings" onNavigate={onNavigate}>
        <p className="text-foreground">{formatLongDate(draft.readings.date_iso) || "No service date"}</p>
        {readingsShipped ? <p>{draft.readings.occasion.trim() || "No occasion yet"}</p> : null}
      </Block>
      <Block title="Readings" step="readings" onNavigate={onNavigate}>
        {!readingsShipped ? (
          <Soon />
        ) : lines.length === 0 ? (
          <p>No readings yet</p>
        ) : (
          <ul className="grid gap-1">
            {lines.map((line, i) => (
              <li key={`${i}:${line}`} className="flex flex-wrap items-center gap-1.5 break-words text-foreground">
                <span className="min-w-0 break-words">{line}</span>
                {holds(line, picks.ot) ? <Badge variant="secondary">{picks.otAuto ? "OT (auto)" : "OT"}</Badge> : null}
                {holds(line, picks.nt) ? <Badge variant="secondary">{picks.ntAuto ? "NT (auto)" : "NT"}</Badge> : null}
              </li>
            ))}
          </ul>
        )}
      </Block>
      <Block title="Hymns" step="hymns" onNavigate={onNavigate}>
        <Soon />
      </Block>
      <Block title="Liturgy" step="liturgy" onNavigate={onNavigate}>
        <Soon />
      </Block>
      <p className="border-t pt-3 text-xs text-muted-foreground">{saved} · Not in archive</p>
    </div>
  );
}
