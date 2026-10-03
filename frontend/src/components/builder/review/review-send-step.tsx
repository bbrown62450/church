"use client";

import { StillNeeded } from "@/components/builder/still-needed";
import { useChurch } from "@/lib/church-context";
import { useChurchProfile } from "@/lib/queries/church";

import { DocumentsCard } from "./documents-card";
import { EditingBanner } from "./editing-banner";
import { PrintedCard } from "./printed-card";
import { SaveCard } from "./save-card";

/**
 * Step 5, Review & send (slice 5a spec, UX "Review step"; owner answers 1 and
 * 2, 2026-10-01), top to bottom: the banner while the draft is a saved
 * service, "Still to do" (each gap a link to fix it), the Archive card (save,
 * start a new service; 5a-3), the Word documents, and the printed bulletin
 * (printed bulletin spec, PR 1). No order-of-worship
 * preview: the Liturgy step already shows the order. Email comes in 5b.
 */
export function ReviewSendStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  return (
    <section aria-label="Review & send" className="grid gap-6">
      <EditingBanner />
      <StillNeeded />
      {/* The builder shows a step only once the profile has loaded (BuilderShell). */}
      {profile.data ? <SaveCard church={profile.data} /> : null}
      <DocumentsCard />
      <PrintedCard />
    </section>
  );
}
