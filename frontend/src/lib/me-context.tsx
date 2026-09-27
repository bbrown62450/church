"use client";

/**
 * The signed-in user's `/me` for everything under the `(signed-in)` layout
 * (S Layouts): `useMeContext().user.id` keys slice 2's drafts and
 * `.churches` feeds the church switcher and draft pruning.
 */
import { createContext, useContext, type ReactNode } from "react";

import type { Me } from "@/lib/api/types";

const MeContext = createContext<Me | null>(null);

export function MeProvider({ value, children }: { value: Me; children: ReactNode }) {
  return <MeContext value={value}>{children}</MeContext>;
}

/** The current `/me`. Throws outside `MeProvider` (a layout bug, not a user error). */
export function useMeContext(): Me {
  const me = useContext(MeContext);
  if (!me) throw new Error("useMeContext() must be used inside <MeProvider>.");
  return me;
}
