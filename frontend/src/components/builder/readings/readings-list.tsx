"use client";

import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import type { ChurchProfile, Lectionary } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import { cleanScriptures, effectiveTranslation } from "@/lib/draft/readings";
import { MAX_LINE } from "@/lib/draft/status";
import { useTranslations } from "@/lib/queries/reference";
import { useDebouncedValue } from "@/lib/use-debounced-value";
import { VOICES_DELAY_MS, voicesPassage, type VoicesPassage } from "@/lib/voices";

import { ReadingRow } from "./reading-row";
import { TranslationSelect } from "./translation-select";
import { VoicesPanel } from "./voices-panel";

/** How long the list trails the scripture lines, so typing does not rebuild it on every key. */
export const LIST_DELAY_MS = 400;

/**
 * "Readings" (S UX item 6): the translation, then one row per cleaned line,
 * 400 ms behind the textarea. Open rows are keyed by their reference text, so
 * editing a line closes its row, and one typed back later starts closed. "Show all text" opens every row that can be
 * sent; the passage limiter keeps 3 requests in flight. The Voices of the
 * Church panel (Voices V1) sits under the Gospel's row: the bulletin reading
 * from a Gospel, else the Sunday's lectionary Gospel (`lect`, this date's
 * lookup), after the list when that line is not among the rows; 600 ms behind
 * the lines, so typing a reference asks for it once.
 */
export function ReadingsList({ church, lect }: { church: ChurchProfile; lect?: Lectionary }) {
  const { draft } = useDraft();
  // The panel trails the lines a little more than the list does, so it asks once typing stops and
  // finds its row among the list's lines.
  const live = voicesPassage(draft, lect);
  const settled = useDebouncedValue(live ? JSON.stringify(live) : "", VOICES_DELAY_MS);
  const passage = useMemo<VoicesPassage | null>(() => (settled ? JSON.parse(settled) : null), [settled]);
  const [voicesOpen, setVoicesOpen] = useState(false);
  const translations = useTranslations();
  const translation = effectiveTranslation(draft, church, translations.data);
  const joined = useDebouncedValue(cleanScriptures(draft).join("\n"), LIST_DELAY_MS);
  const lines = joined === "" ? [] : joined.split("\n");
  const [open, setOpen] = useState<ReadonlySet<string>>(() => new Set());
  // When the lines change, forget open rows whose line is gone, during render
  // (not in an effect), so a line typed back later starts closed and a
  // reopened row never renders, even once, to fetch its text again.
  const [openFor, setOpenFor] = useState(joined);
  if (openFor !== joined) {
    setOpenFor(joined);
    const kept = [...open].filter((reference) => lines.includes(reference));
    if (kept.length !== open.size) setOpen(new Set(kept));
  }

  const voices = passage ? <VoicesPanel passage={passage} open={voicesOpen} onOpenChange={setVoicesOpen} /> : null;
  const voicesRow = passage ? lines.indexOf(passage.line) : -1;

  function setRow(reference: string, next: boolean) {
    setOpen((current) => {
      const updated = new Set(current);
      if (next) updated.add(reference);
      else updated.delete(reference);
      return updated;
    });
  }

  return (
    <section aria-labelledby="readings-heading" className="grid gap-4">
      <h2 id="readings-heading" className="text-base font-medium">
        Readings
      </h2>
      <div className="grid gap-3">
        <TranslationSelect church={church} translations={translations.data} />
        <div>
          <Button
            type="button"
            variant="outline"
            size="touch"
            disabled={lines.length === 0}
            onClick={() => setOpen(new Set(lines.filter((line) => line.length <= MAX_LINE)))}
          >
            Show all text
          </Button>
        </div>
      </div>
      {lines.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Add a reading above to see its text and choose the bulletin readings.
        </p>
      ) : (
        <ul className="grid">
          {lines.map((reference, i) => (
            <ReadingRow
              key={`${i}:${reference}`}
              reference={reference}
              translation={translation}
              open={open.has(reference)}
              onOpenChange={(next) => setRow(reference, next)}
            >
              {i === voicesRow ? voices : null}
            </ReadingRow>
          ))}
        </ul>
      )}
      {voicesRow < 0 ? voices : null}
    </section>
  );
}
