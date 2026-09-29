"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { stepById, type StepId } from "@/lib/draft/steps";
import { useKeyboardOpen } from "@/lib/use-keyboard-open";
import { cn } from "@/lib/utils";

/**
 * Back and Next (S "Footer labels"; F §4.7): Date & readings has only "Next:
 * Hymns", Review only "Back". Below `lg` it is sticky at the bottom above the
 * home indicator; below `md` it hides while a text field has focus, so the
 * iOS keyboard does not stack on it.
 */
export function StepFooter({ current }: { current: StepId }) {
  const keyboardOpen = useKeyboardOpen();
  const step = stepById(current);
  const previous = step.previous ? stepById(step.previous) : null;
  const next = step.next ? stepById(step.next) : null;
  return (
    <nav
      aria-label="Step navigation"
      data-keyboard-open={keyboardOpen ? "" : undefined}
      className={cn(
        "sticky bottom-0 z-10 -mx-4 border-t bg-background/95 px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur",
        "lg:static lg:mx-0 lg:border-t-0 lg:bg-transparent lg:px-0 lg:pb-6 lg:backdrop-blur-none",
        keyboardOpen && "max-md:hidden",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        {previous ? (
          <Link href={previous.href} className={buttonVariants({ variant: "outline", size: "touch" })}>
            Back
          </Link>
        ) : (
          <span />
        )}
        {next ? (
          <Link href={next.href} className={buttonVariants({ size: "touch" })}>
            Next: {next.short}
          </Link>
        ) : null}
      </div>
    </nav>
  );
}
