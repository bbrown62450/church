/**
 * The confirmed church for everything under the `(church)` layout (F §4.2).
 * The layout provides the `GET /church` result; `useApi().church` reads its id
 * for `X-Church-Id`.
 */
import { createContext, useContext, type ReactNode } from "react";

import type { Church } from "@/lib/api/types";

const ChurchContext = createContext<Church | null>(null);

export function ChurchProvider({ value, children }: { value: Church; children: ReactNode }) {
  return <ChurchContext value={value}>{children}</ChurchContext>;
}

/** The active church. Throws outside `ChurchProvider` (a church-scoped component rendered in the wrong place). */
export function useChurch(): Church {
  const church = useContext(ChurchContext);
  if (!church) throw new Error("useChurch() must be used inside ChurchProvider.");
  return church;
}

/** The active church, or null outside `ChurchProvider` (for code that also runs above it, like `useApi`). */
export function useOptionalChurch(): Church | null {
  return useContext(ChurchContext);
}
