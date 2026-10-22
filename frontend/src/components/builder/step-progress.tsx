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
 * step from printed bulletin PR 2b): every step is a link (F D9), drawn as a
 * Material 3 chip (Theme PR 1): the current step filled, a done step with a
 * check. Below `lg` a line "Step 1 of 5 · Date & readings" sits above five
 * number chips (each 44 px tall, about 60 px wide at 375 px); from `lg` each
 * chip shows the number and label, with the status under it. The
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
          const done = status.kind === "complete" || status.kind === "saved";
          return (
            <li key={s.id}>
              <Link
                href={s.href}
                aria-current={isCurrent ? "step" : undefined}
                className="group flex min-h-11 flex-col justify-center gap-1 rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring lg:min-h-0"
              >
                <span
                  className={cn(
                    "flex h-11 min-w-0 items-center justify-center gap-1 rounded-full border border-border px-2 text-sm font-medium text-muted-foreground group-hover:bg-foreground/8 lg:h-9 lg:justify-start lg:px-3",
                    done && "border-primary/40 text-primary",
                    isCurrent && "border-transparent bg-secondary text-secondary-foreground group-hover:bg-secondary",
                  )}
                >
                  {done ? <CheckIcon aria-hidden="true" className="size-4 shrink-0" /> : null}
                  <span>{s.number}</span> <span className="sr-only lg:not-sr-only lg:truncate">{s.label}</span>
                </span>{" "}
                <span
                  className={cn(
                    "sr-only lg:not-sr-only lg:px-3 lg:text-xs",
                    muted ? "lg:text-muted-foreground" : "lg:text-foreground",
                  )}
                >
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
