"use client";

import { StillNeeded } from "@/components/builder/still-needed";

import { DocumentsCard } from "./documents-card";

/**
 * Step 4, Review & send, as slice 5a-1 ships it (owner answers 1 and 2,
 * 2026-10-01): "Still needed" (the shipped steps' gaps, each a link to fix
 * it), the Word documents, and a note that saving to the archive comes later
 * (5a-3 puts the Save card here). No order-of-worship preview: the Liturgy
 * step already shows the order.
 */
export function ReviewSendStep() {
  return (
    <section aria-label="Review & send" className="grid gap-6">
      <StillNeeded />
      <DocumentsCard />
      <section aria-labelledby="archive-title" className="grid gap-1 rounded-lg border border-dashed p-4">
        <h2 id="archive-title" className="text-base font-medium">
          Archive
        </h2>
        <p className="text-sm text-muted-foreground">Saving services to the archive is coming soon.</p>
      </section>
    </section>
  );
}
