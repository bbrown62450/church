"use client";

import { useCallback, useEffect, useRef } from "react";
import { toast } from "sonner";

import { useChurch } from "@/lib/church-context";

/**
 * Toasts with Undo that never outlive the step (S "Undo toasts never outlive
 * the step"). Sonner's toasts live outside the `(church)` layout, so a closure
 * over `update` could act after a church switch. Two guards: every toast this
 * step showed is dismissed when it unmounts, and each Undo checks that the step
 * is still mounted for the church it was shown in.
 */
export function useUndoToasts(): (message: string, undo: () => void) => void {
  const church = useChurch();
  const shown = useRef(new Set<string | number>());
  const mounted = useRef(false);
  const currentChurch = useRef(church.id);

  useEffect(() => {
    currentChurch.current = church.id;
  }, [church.id]);

  useEffect(() => {
    const ids = shown.current;
    mounted.current = true;
    return () => {
      mounted.current = false;
      for (const id of ids) toast.dismiss(id);
      ids.clear();
    };
  }, []);

  return useCallback(
    (message: string, undo: () => void) => {
      const captured = church.id;
      const id = toast.message(message, {
        action: {
          label: "Undo",
          onClick: () => {
            if (mounted.current && currentChurch.current === captured) undo();
          },
        },
      });
      shown.current.add(id);
    },
    [church.id],
  );
}
