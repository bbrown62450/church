"use client";

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
  destructive?: boolean;
};

/**
 * F §4.8 "Destructive or lossy action": a Base UI AlertDialog, controlled with
 * open/onOpenChange (F §4.9 item 6). Confirm is a PendingButton rather than
 * AlertDialogAction so the dialog stays open while the mutation runs.
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
  destructive = false,
}: ConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          {description ? <AlertDialogDescription>{description}</AlertDialogDescription> : null}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{cancelLabel}</AlertDialogCancel>
          <PendingButton
            pending={pending}
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
