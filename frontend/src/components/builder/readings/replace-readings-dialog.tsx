"use client";

import { ConfirmDialog, type ConfirmDialogProps } from "@/components/app/confirm-dialog";

/**
 * "Replace your readings?" (S UX item 3): asked before a lectionary set
 * replaces typed or archived readings. "Keep mine", Escape and the backdrop
 * all keep them; only the "Keep mine" button calls `onKeepMine` (owner
 * answer 1), and every close calls `onClose`.
 */
export function ReplaceReadingsDialog({
  setName,
  onConfirm,
  onKeepMine,
  onClose,
  finalFocus,
}: {
  /** The set that would replace the readings; null keeps the dialog closed. */
  setName: string | null;
  onConfirm: () => void;
  onKeepMine: () => void;
  onClose: () => void;
  finalFocus?: ConfirmDialogProps["finalFocus"];
}) {
  return (
    <ConfirmDialog
      open={setName !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title="Replace your readings?"
      description={`Your occasion and scripture list will be replaced with “${setName ?? ""}” from the lectionary.`}
      confirmLabel="Replace readings"
      cancelLabel="Keep mine"
      onConfirm={onConfirm}
      onCancel={onKeepMine}
      finalFocus={finalFocus}
    />
  );
}
