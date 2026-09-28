import { Loader2Icon } from "lucide-react";
import type { ComponentProps } from "react";

import { Button } from "@/components/ui/button";

export type PendingButtonProps = ComponentProps<typeof Button> & {
  /** True while the mutation is in flight: the button is disabled and shows pendingLabel. */
  pending: boolean;
  pendingLabel?: string;
};

/** F §4.8 "Mutation in flight": disabled, label changes to "Saving…"; the rest of the page stays usable. */
export function PendingButton({
  pending,
  pendingLabel = "Saving…",
  disabled,
  children,
  ...props
}: PendingButtonProps) {
  return (
    <Button {...props} disabled={pending || disabled} aria-busy={pending || undefined}>
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
