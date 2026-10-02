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

export const CONFLICT_TITLE = "Someone else changed this service";
export const RELOAD_REPLACES = "Reloading replaces your changes on this device.";

/**
 * The 409 dialog (slice 5a spec, UX "Save card" Conflict; F §1.7): the
 * server's message and that reloading replaces this device's changes, then
 * "Save mine as a new service" (the primary button: a POST; theirs stays),
 * "Reload their version" (the dialog is the confirmation: the draft becomes
 * their saved copy) and "Cancel" (nothing changes). Each action button shows
 * its own pending label; the dialog stays open until it ends.
 */
export function ConflictDialog({
  open,
  onOpenChange,
  message,
  onReload,
  reloading,
  onSaveAsNew,
  saving,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  message: string;
  onReload: () => void;
  reloading: boolean;
  onSaveAsNew: () => void;
  saving: boolean;
}) {
  const busy = reloading || saving;
  return (
    <AlertDialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{CONFLICT_TITLE}</AlertDialogTitle>
          <AlertDialogDescription className="grid gap-2">
            <span>{message}</span> <span>{RELOAD_REPLACES}</span>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel size="touch" className="md:h-8">
            Cancel
          </AlertDialogCancel>
          <PendingButton
            variant="outline"
            size="touch"
            className="md:h-8"
            pending={reloading}
            pendingLabel="Loading…"
            disabled={busy}
            onClick={() => onReload()}
          >
            Reload their version
          </PendingButton>
          <PendingButton size="touch" className="md:h-8" pending={saving} disabled={busy} onClick={() => onSaveAsNew()}>
            Save mine as a new service
          </PendingButton>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
