"use client";

import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";

import { ConfirmDialog } from "@/components/app/confirm-dialog";
import { DropdownMenuItem } from "@/components/ui/dropdown-menu";
import { useDraft } from "@/lib/draft/context";
import { isDirty } from "@/lib/draft/fingerprint";
import { freshDraft, type DraftChurch } from "@/lib/draft/schema";
import { useMeContext } from "@/lib/me-context";

/**
 * "New service" (S "New service"; F §4.6 item 1): a draft with nothing to
 * lose resets at once; otherwise "Start a new service?" asks first. Either
 * way the builder then opens Date & readings. The fresh draft keeps the
 * chosen Bible translation (owner answer A, 2026-09-29).
 */
export function useNewService(church: DraftChurch): { start: () => void; dialog: ReactNode } {
  const { draft, replace } = useDraft();
  const me = useMeContext();
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);

  function reset() {
    const fresh = freshDraft({ church, user: me.user });
    replace({ ...fresh, readings: { ...fresh.readings, translation: draft.readings.translation } });
    setConfirming(false);
    router.push("/builder/readings");
  }

  return {
    start: () => (isDirty(draft) ? setConfirming(true) : reset()),
    dialog: (
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Start a new service?"
        description="This clears the current draft on this device."
        confirmLabel="Start new service"
        onConfirm={reset}
        destructive
      />
    ),
  };
}

export function NewServiceMenuItem({ onSelect }: { onSelect: () => void }) {
  return <DropdownMenuItem onClick={() => onSelect()}>New service</DropdownMenuItem>;
}
