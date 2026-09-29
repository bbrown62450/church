"use client";

import { ConfirmDialog } from "@/components/app/confirm-dialog";

/**
 * "Replace your readings?" (S UX item 3): asked before a lectionary set
 * replaces typed or archived readings. "Keep mine", Escape and the backdrop
 * all keep them.
 */
export function ReplaceReadingsDialog({
  setName,
  onConfirm,
  onKeep,
}: {
  /** The set that would replace the readings; null keeps the dialog closed. */
  setName: string | null;
  onConfirm: () => void;
  onKeep: () => void;
}) {
  return (
    <ConfirmDialog
      open={setName !== null}
      onOpenChange={(open) => {
        if (!open) onKeep();
      }}
      title="Replace your readings?"
      description={`Your occasion and scripture list will be replaced with “${setName ?? ""}” from the lectionary.`}
      confirmLabel="Replace readings"
      cancelLabel="Keep mine"
      onConfirm={onConfirm}
    />
  );
}
