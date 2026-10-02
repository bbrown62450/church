"use client";

import Link from "next/link";

import { useDraft } from "@/lib/draft/context";
import { stillNeeded } from "@/lib/draft/status";
import { SHIPPED_STEPS, stepById, type StepId } from "@/lib/draft/steps";

/**
 * Review's "Still needed" list (S "Steps 2–4"; F §4.7 "Review has no Next"):
 * one row per gap in a shipped step, each linking to that step. Nothing
 * renders while no step has shipped (slice 2b) or nothing is missing.
 */
export function StillNeeded({ shipped = SHIPPED_STEPS }: { shipped?: ReadonlySet<StepId> }) {
  const { draft } = useDraft();
  const items = stillNeeded(draft, shipped);
  if (items.length === 0) return null;
  return (
    <section aria-labelledby="still-needed-heading" className="grid gap-2">
      <h2 id="still-needed-heading" className="text-base font-medium">
        Still needed
      </h2>
      <ul className="grid gap-1 text-sm">
        {items.map((item) => (
          <li key={`${item.step}:${item.message}`}>
            {item.message} —{" "}
            <Link href={item.href ?? stepById(item.step).href} className="font-medium underline underline-offset-4">
              {item.action}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
