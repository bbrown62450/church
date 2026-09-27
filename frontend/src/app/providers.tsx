"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { getQueryClient } from "@/lib/queries/client";

/**
 * Client-side providers for the whole app (F §4.4): one QueryClient for the
 * life of the browser tab, a new one per server render (Next's "TanStack
 * Query" guide). The root layout stays a Server Component and renders this.
 */
export function Providers({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={getQueryClient()}>{children}</QueryClientProvider>;
}
