"use client";

import Link from "next/link";

import { useDraft } from "@/lib/draft/context";
import { stillNeeded } from "@/lib/draft/status";
import { SHIPPED_STEPS, stepById, type StepId } from "@/lib/draft/steps";

/**
 * Review's checklist, "Still to do" (slice 5a spec, UX "Review step" item 2;
 * F §4.7 "Review has no Next"; renamed from 4b's "Still needed" in 5a-3): one
 * row per gap in a shipped step, each linking to where it is fixed, or
 * "Everything's ready." when nothing is missing. Nothing it lists blocks
 * Save or the downloads but the date (F D9).
 */
export function StillNeeded({ shipped = SHIPPED_STEPS }: { shipped?: ReadonlySet<StepId> }) {
  const { draft } = useDraft();
  const items = stillNeeded(draft, shipped);
  return (
    <section aria-labelledby="still-needed-heading" className="grid gap-2">
      <h2 id="still-needed-heading" className="text-base font-medium">
        Still to do
      </h2>
      {items.length === 0 ? <p className="text-sm">Everything&apos;s ready.</p> : null}
      <ul className="grid gap-1 text-sm empty:hidden">
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
