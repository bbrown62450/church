"use client";

import { CheckIcon } from "lucide-react";
import Link from "next/link";

import { useDraft } from "@/lib/draft/context";
import { stepStatus, type StepStatus } from "@/lib/draft/status";
import { SHIPPED_STEPS, STEPS, stepById, type StepId } from "@/lib/draft/steps";
import { cn } from "@/lib/utils";

export function statusText(status: StepStatus): string {
  switch (status.kind) {
    case "complete":
      return "Complete";
    case "incomplete":
      return `${status.done} of ${status.total}`;
    case "soon":
      return "Soon";
    case "optional":
      return "Optional";
    case "to_check":
      return `${status.count} to check`;
    case "not_in_archive":
      return "Not in archive";
    case "saved":
      return "Saved";
    case "unsaved_changes":
      return "Unsaved changes";
  }
}

/**
 * The five steps (F §4.7 "StepProgress"; S "Builder shell"; the Bulletin
 * step from printed bulletin PR 2b): every step is a link (F D9). Below `lg`
 * a line "Step 1 of 5 · Date & readings" sits above five segments (each
 * 44 px tall, about 60 px wide at 375 px); from `lg` each step shows its
 * number, label and status. The
 * labels and statuses are in the DOM at every width (screen-reader text below
 * `lg`), so each link's name is "{n} {label} {status}".
 */
export function StepProgress({ current, shipped = SHIPPED_STEPS }: { current: StepId; shipped?: ReadonlySet<StepId> }) {
  const { draft } = useDraft();
  const step = stepById(current);
  return (
    <nav aria-label="Steps" className="grid gap-2 pb-2">
      <p className="text-sm font-medium lg:hidden" aria-hidden="true">
        Step {step.number} of {STEPS.length} · {step.label}
      </p>
      <ol className="grid grid-cols-5 gap-1.5 lg:gap-3">
        {STEPS.map((s) => {
          const status = stepStatus(draft, s.id, shipped);
          const isCurrent = s.id === current;
          const muted = status.kind === "soon" || status.kind === "not_in_archive" || status.kind === "optional";
          return (
            <li key={s.id}>
              <Link
                href={s.href}
                aria-current={isCurrent ? "step" : undefined}
                className="flex min-h-11 flex-col justify-center gap-1 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring lg:min-h-0 lg:py-1"
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "h-1.5 rounded-full bg-muted",
                    (status.kind === "complete" || status.kind === "saved") && "bg-primary/60",
                    isCurrent && "bg-primary",
                  )}
                />
                <span className="sr-only lg:not-sr-only lg:text-sm lg:font-medium">
                  {s.number} {s.label}
                </span>{" "}
                <span
                  className={cn(
                    "sr-only lg:not-sr-only lg:flex lg:items-center lg:gap-1 lg:text-xs",
                    muted ? "lg:text-muted-foreground" : "lg:text-foreground",
                  )}
                >
                  {status.kind === "complete" || status.kind === "saved" ? <CheckIcon aria-hidden="true" className="size-3" /> : null}
                  {statusText(status)}
                </span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
