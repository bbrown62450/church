import { EmptyState } from "@/components/app/empty-state";
import { stepById, type StepId } from "@/lib/draft/steps";

/**
 * The card a step shows until its slice ships (S "Steps 2–4 (placeholders)";
 * F §4.7). Slice 2b also used it for Date & readings until slice 2c (owner
 * answer Q1, 2026-09-28). Slices 3, 4 and 5a each replace their step's use,
 * and 5a deletes this component. No link to the old app (owner answer Q2).
 */
export function StepPlaceholder({ step }: { step: StepId }) {
  return (
    <section aria-label={stepById(step).label}>
      <EmptyState title="Available soon" description="Keep using the current app for this part." />
    </section>
  );
}
