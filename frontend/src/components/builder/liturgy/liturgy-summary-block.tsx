"use client";

import { useDraft } from "@/lib/draft/context";
import { useLiturgyGeneration } from "@/lib/liturgy/generation";
import { liturgyCounts } from "@/lib/liturgy/summary";

/**
 * The summary's Liturgy block (slice 4 spec, "Builder shell"; F §4.7): "{ready}
 * of {enabled} liturgy sections ready" (or "All liturgy sections switched
 * off"), with " · Writing n sections…" while the generation provider has runs;
 * "Communion: Yes/No"; and the custom-element count. It reads the draft and
 * the runs only, so the shell never fetches anything for it.
 */
export function LiturgySummaryBlock() {
  const { draft } = useDraft();
  const { runs } = useLiturgyGeneration();
  const counts = liturgyCounts(draft);
  const writing = Object.keys(runs).length;
  const ready =
    counts.enabled === 0 ? "All liturgy sections switched off" : `${counts.ready} of ${counts.enabled} liturgy sections ready`;
  const custom =
    counts.customCount === 0
      ? "No custom elements"
      : counts.customCount === 1
        ? "1 custom element"
        : `${counts.customCount} custom elements`;
  return (
    <ul className="grid gap-1">
      <li className="text-foreground">
        {ready}
        {writing > 0 ? ` · Writing ${writing} ${writing === 1 ? "section" : "sections"}…` : null}
      </li>
      <li>Communion: {counts.communion ? "Yes" : "No"}</li>
      <li>{custom}</li>
    </ul>
  );
}
