"use client";

import { useEffect, useState } from "react";

import type { ApiError } from "@/lib/api/client";

/** The seconds a 429 asks to wait (its `Retry-After`), at least 1. */
export function retryAfter(error: ApiError): number {
  return Math.max(1, error.retryAfterSeconds ?? 1);
}

/** Shown once the wait has passed (owner answer D, 2026-09-29). */
export const TRY_AGAIN_NOW = "Try again now.";

/**
 * The F §4.8 rate-limit sentence the step shows while the wait runs, then
 * "Try again now." once it has passed (owner answer D).
 */
export function rateLimitMessage(error: ApiError, waitOver = false): string {
  return waitOver ? TRY_AGAIN_NOW : `Too many requests — try again in ${retryAfter(error)} s.`;
}

/** True once `error`'s `Retry-After` has passed; each new error starts its own wait. */
export function useWaitOver(error: ApiError | null): boolean {
  const [overFor, setOverFor] = useState<ApiError | null>(null);
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setOverFor(error), retryAfter(error) * 1000);
    return () => clearTimeout(timer);
  }, [error]);
  return error !== null && overFor === error;
}
