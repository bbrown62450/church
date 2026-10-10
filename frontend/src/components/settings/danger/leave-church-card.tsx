"use client";

import { useRef, useState } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { Button } from "@/components/ui/button";
import { useLeaveChurch } from "@/lib/queries/church";
import type { leaveBlock } from "@/lib/settings/people";

/** A Danger zone card: a bordered box; a destructive one is outlined in red (6b spec UX 2). */
export const CARD = "grid gap-3 rounded-lg border p-4";
export const DESTRUCTIVE_CARD = `${CARD} border-destructive/40`;

export const OWNER_MUST_TRANSFER = "You're the owner. Transfer ownership below before you leave.";

export function leaveText(church: string): string {
  return `You'll lose access to ${church}'s services, hymns and settings. To come back you'll need a new invite.`;
}

export function ownerAloneText(church: string): string {
  return `You're the only person in ${church}. To stop using it, delete the church below.`;
}

/**
 * Leave {church} (6b spec UX 2a), for everyone. A member or an admin leaves
 * after a confirmation; the owner's button is off, with why: transfer first
 * or, alone, delete the church.
 */
export function LeaveChurchCard({
  churchName,
  block,
}: {
  churchName: string;
  block: ReturnType<typeof leaveBlock>;
}) {
  const leave = useLeaveChurch();
  const [open, setOpen] = useState(false);
  // One leave per confirmation, even if the button is tapped twice before it says "Leaving…".
  const sent = useRef(false);
  let text: string;
  if (block === "owner_with_others") text = OWNER_MUST_TRANSFER;
  else if (block === "owner_alone") text = ownerAloneText(churchName);
  else text = leaveText(churchName);
  return (
    <section aria-labelledby="leave-title" className={DESTRUCTIVE_CARD}>
      <h3 id="leave-title" className="text-base font-medium [overflow-wrap:anywhere]">
        Leave {churchName}
      </h3>
      <p id="leave-why" className="text-sm text-muted-foreground [overflow-wrap:anywhere]">
        {text}
      </p>
      <div>
        <Button
          type="button"
          variant="outline"
          size="touch"
          className="md:h-8"
          disabled={block !== null}
          // the owner's button is off: the sentence above says why
          aria-describedby={block !== null ? "leave-why" : undefined}
          onClick={() => {
            sent.current = false;
            setOpen(true);
          }}
        >
          Leave church…
        </Button>
      </div>
      <ConfirmDialog
        open={open}
        onOpenChange={(next) => {
          // while the leave runs the confirmation stays open
          if (!next && leave.isPending) return;
          setOpen(next);
        }}
        title={`Leave ${churchName}?`}
        description={`You'll lose access right away. Your unsaved draft for ${churchName} on this device will be discarded.`}
        confirmLabel="Leave church"
        pending={leave.isPending}
        pendingLabel="Leaving…"
        destructive
        wrapAnywhere
        onConfirm={() => {
          if (sent.current) return;
          sent.current = true;
          leave.mutate(undefined, {
            onError: () => {
              sent.current = false;
              setOpen(false);
            },
          });
        }}
      />
    </section>
  );
}
