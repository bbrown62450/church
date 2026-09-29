"use client";

import { useRef } from "react";

import { useLectionaryLookup } from "@/components/builder/lectionary-sync";
import { useChurch } from "@/lib/church-context";
import { todayIn } from "@/lib/dates";
import { churchZone } from "@/lib/draft/schema";
import { useChurchProfile } from "@/lib/queries/church";

import { LectionaryStatus } from "./lectionary-status";
import { OccasionField } from "./occasion-field";
import { ReadingsList } from "./readings-list";
import { ScriptureLinesField } from "./scripture-lines-field";
import { ServiceDateField } from "./service-date-field";

/**
 * Step 1, Date & readings (S UX "Step 1"): the service date, the lectionary
 * status, the occasion and scripture lines, the readings with their text, and
 * the bulletin's two readings. The shell's `<LectionarySync>` does the lookup
 * and the automatic fill; this step shows them.
 */
export function ReadingsStep() {
  const church = useChurch();
  const profile = useChurchProfile(church.id).data;
  const { lookupDate, query } = useLectionaryLookup();
  const occasionRef = useRef<HTMLInputElement>(null);
  if (!profile) return null;
  const today = todayIn(churchZone(profile));
  const lect = query.data?.date === lookupDate ? query.data : undefined;

  return (
    <section aria-label="Date & readings" className="grid gap-6">
      <ServiceDateField today={today} />
      <LectionaryStatus onEnterReadings={() => occasionRef.current?.focus()} />
      <OccasionField lect={lect} inputRef={occasionRef} />
      <ScriptureLinesField />
      <ReadingsList church={profile} />
    </section>
  );
}
