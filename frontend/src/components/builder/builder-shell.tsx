"use client";

/**
 * The builder around every step route (F §4.7; S "Builder shell"). It loads
 * the draft for the signed-in user and the active church, writes `last_step`
 * on every step route, and lays out: header, progress, the step, the footer,
 * and the summary (a sticky column from `lg`, a bottom sheet below it).
 * The frame grows to fill the `(church)` layout's column below the header
 * (`flex-1`), so it needs no hard-coded header height and the footer sits at
 * the bottom of a short step.
 * The church profile is already loaded by the `(church)` layout; until the
 * query has data (tests, a cold cache) a step-shaped skeleton shows.
 */
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { useChurch } from "@/lib/church-context";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import type { DraftChurch } from "@/lib/draft/schema";
import { stepFromPath } from "@/lib/draft/steps";
import { useMeContext } from "@/lib/me-context";
import { useChurchProfile } from "@/lib/queries/church";

import { useNewService } from "./new-service-menu-item";
import { StepFooter } from "./step-footer";
import { StepHeader } from "./step-header";
import { StepProgress } from "./step-progress";
import { SummaryPanel } from "./summary-panel";
import { SummarySheet } from "./summary-sheet";

export function BuilderShell({ children }: { children: ReactNode }) {
  const me = useMeContext();
  const church = useChurch();
  const profile = useChurchProfile(church.id);
  if (!profile.data) return <BuilderSkeleton />;
  return (
    <DraftProvider key={`${me.user.id}:${church.id}`} userId={me.user.id} church={profile.data}>
      <BuilderFrame church={profile.data}>{children}</BuilderFrame>
    </DraftProvider>
  );
}

function BuilderFrame({ church, children }: { church: DraftChurch; children: ReactNode }) {
  const current = stepFromPath(usePathname());
  const { setLastStep } = useDraft();
  const [summaryOpen, setSummaryOpen] = useState(false);
  const newService = useNewService(church);

  useEffect(() => {
    if (current) setLastStep(current);
  }, [current, setLastStep]);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 lg:grid lg:max-w-6xl lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-6">
      <div className="flex min-w-0 flex-1 flex-col">
        <StepHeader onOpenSummary={() => setSummaryOpen(true)} onNewService={newService.start} />
        {current ? <StepProgress current={current} /> : null}
        <main className="flex-1 py-4">{children}</main>
        {current ? <StepFooter current={current} /> : null}
      </div>
      <aside aria-label="Summary" className="hidden lg:block">
        <div className="sticky top-20 py-4">
          <SummaryPanel />
        </div>
      </aside>
      <SummarySheet open={summaryOpen} onOpenChange={setSummaryOpen} />
      {newService.dialog}
    </div>
  );
}

/** The builder's shape while the church profile loads (S "Builder first render"). */
export function BuilderSkeleton() {
  return (
    <div role="status" aria-label="Loading" className="mx-auto grid w-full max-w-2xl gap-4 px-4 py-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}
