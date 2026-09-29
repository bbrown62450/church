"use client";

/**
 * The builder around every step route (F §4.7; S "Builder shell"). It loads
 * the draft for the signed-in user and the active church, writes `last_step`
 * on every step route, and lays out: header, progress, the step, the footer,
 * and the summary (a sticky column from `lg`, a bottom sheet below it).
 * The frame grows to fill the `(church)` layout's column below the header
 * (`flex-1`), so it needs no hard-coded header height and the footer sits at
 * the bottom of a short step. The page's one `<main>` (the `(church)` layout
 * adds none around a loaded church) holds the header, progress and step; the
 * footer nav follows it.
 * The summary sheet closes when the window widens past `lg`.
 * The church profile is already loaded by the `(church)` layout; until the
 * query has data (tests, a cold cache) a step-shaped skeleton shows.
 * `<LectionarySync>` looks up the draft's date and fills the readings on
 * every step (slice 2c).
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

import { LectionarySync } from "./lectionary-sync";
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
      <LectionarySync>
        <BuilderFrame church={profile.data}>{children}</BuilderFrame>
      </LectionarySync>
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

  // The sheet is hidden from `lg` (64rem) but its backdrop is not: close it
  // when the window widens past `lg` while it is open.
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const wide = window.matchMedia("(min-width: 64rem)");
    const closeWhenWide = () => {
      if (wide.matches) setSummaryOpen(false);
    };
    wide.addEventListener("change", closeWhenWide);
    return () => wide.removeEventListener("change", closeWhenWide);
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col px-4 lg:grid lg:max-w-6xl lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-6">
      <div className="flex min-w-0 flex-1 flex-col">
        <main className="flex flex-1 flex-col">
          <StepHeader onOpenSummary={() => setSummaryOpen(true)} onNewService={newService.start} />
          {current ? <StepProgress current={current} /> : null}
          <div className="flex-1 py-4">{children}</div>
        </main>
        {current ? <StepFooter current={current} /> : null}
      </div>
      <aside aria-label="Summary" className="hidden lg:block">
        {/* Below the sticky AppHeader, whose measured height AppHeader publishes as --app-header-h. */}
        <div className="sticky top-[var(--app-header-h,4rem)] py-4">
          <h2 className="sr-only">Summary</h2>
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
