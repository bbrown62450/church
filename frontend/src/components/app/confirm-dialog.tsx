"use client";

import type { AlertDialog as AlertDialogPrimitive } from "@base-ui/react/alert-dialog";
import type { ReactNode } from "react";

import { PendingButton } from "@/components/app/pending-button";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export type ConfirmDialogProps = {
  open: boolean;
  onOpenChange(open: boolean): void;
  title: string;
  description?: string;
  /** Names the action ("Delete service"), never "OK" (F §4.8). */
  confirmLabel: string;
  /** "Cancel" unless the screen's copy says otherwise ("Keep mine"). */
  cancelLabel?: string;
  onConfirm(): void;
  /** While true the confirm button is a disabled "Saving…"; the caller closes the dialog on success. */
  pending?: boolean;
  /** The confirm button's words while `pending` ("Removing…"; slice 6b-2a): "Saving…" unless given. */
  pendingLabel?: string;
  /** Keeps the confirm button off until the dialog's own condition holds (a typed name; slice 6b-2b). */
  confirmDisabled?: boolean;
  destructive?: boolean;
  /** Breaks the title and description anywhere (`[overflow-wrap:anywhere]`), for one that may hold a long email (slice 6b-2a). */
  wrapAnywhere?: boolean;
  /** Called by the cancel button only; Escape and a click outside just close. */
  onCancel?(): void;
  /**
   * Where focus goes when the dialog closes (Base UI `finalFocus`): pass one
   * when the element that opened it may be gone by then, so focus never
   * drops to the page.
   */
  finalFocus?: AlertDialogPrimitive.Popup.Props["finalFocus"];
  /** More of the dialog's body under the description (a sentence that depends on data, a checkbox; slice 6b-2a). */
  children?: ReactNode;
};

/**
 * F §4.8 "Destructive or lossy action": a Base UI AlertDialog, controlled with
 * open/onOpenChange (F §4.9 item 6). Confirm is a PendingButton rather than
 * AlertDialogAction so the dialog stays open while the mutation runs. Both
 * buttons are 44 px tall on phones (F §4.9), the usual 32 px from `md`.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel = "Cancel",
  onConfirm,
  pending = false,
  pendingLabel,
  confirmDisabled = false,
  destructive = false,
  wrapAnywhere = false,
  onCancel,
  finalFocus,
  children,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <AlertDialogContent {...(finalFocus === undefined ? {} : { finalFocus })}>
        <AlertDialogHeader>
          <AlertDialogTitle className={wrapAnywhere ? "[overflow-wrap:anywhere]" : undefined}>{title}</AlertDialogTitle>
          {description ? (
            <AlertDialogDescription className={wrapAnywhere ? "[overflow-wrap:anywhere]" : undefined}>
              {description}
            </AlertDialogDescription>
          ) : null}
        </AlertDialogHeader>
        {children}
        <AlertDialogFooter>
          <AlertDialogCancel size="touch" className="md:h-8" onClick={onCancel ? () => onCancel() : undefined}>
            {cancelLabel}
          </AlertDialogCancel>
          <PendingButton
            pending={pending}
            {...(pendingLabel === undefined ? {} : { pendingLabel })}
            disabled={confirmDisabled}
            size="touch"
            className="md:h-8"
            variant={destructive ? "destructive" : "default"}
            onClick={() => onConfirm()}
          >
            {confirmLabel}
          </PendingButton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
