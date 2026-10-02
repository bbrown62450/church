import { Loader2Icon } from "lucide-react";
import type { ComponentProps } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type PendingButtonProps = ComponentProps<typeof Button> & {
  /** True while the mutation is in flight: the button ignores clicks and shows pendingLabel. */
  pending: boolean;
  pendingLabel?: string;
};

/**
 * F §4.8 "Mutation in flight": disabled, label changes to "Saving…"; the rest of the page stays usable.
 * While pending the button stays focusable (aria-disabled, clicks and keys ignored by Base UI's
 * focusableWhenDisabled) so keyboard focus is not lost to the page body; it keeps the disabled look
 * (5a-1 build review fix 4). A plain `disabled` (not pending) is still the native attribute.
 */
export function PendingButton({
  pending,
  pendingLabel = "Saving…",
  disabled,
  className,
  children,
  ...props
}: PendingButtonProps) {
  return (
    <Button
      {...props}
      className={cn(pending && "pointer-events-none opacity-50", className)}
      disabled={pending || disabled}
      focusableWhenDisabled={pending}
      aria-busy={pending || undefined}
    >
      {pending ? (
        <>
          <Loader2Icon data-icon="inline-start" className="animate-spin" aria-hidden="true" />
          {pendingLabel}
        </>
      ) : (
        children
      )}
    </Button>
  );
}
