/** `useTranslations` (S Queries): user-scoped reference data that never goes stale. */
import { QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ChurchProvider } from "@/lib/church-context";
import { installFakeApi } from "@/test/fake-api";
import { church, translations } from "@/test/fixtures";

import { makeQueryClient } from "./client";
import { useTranslations } from "./reference";

describe("useTranslations", () => {
  it("asks once, as the user, and a second reader uses the cached list", async () => {
    const api = installFakeApi({ "GET /translations": translations() });
    const queryClient = makeQueryClient();
    function Wrapper({ children }: { children: ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>
          <ChurchProvider value={church()}>{children}</ChurchProvider>
        </QueryClientProvider>
      );
    }
    const first = renderHook(() => useTranslations(), { wrapper: Wrapper });
    await waitFor(() => expect(first.result.current.data).toEqual(translations()));
    const second = renderHook(() => useTranslations(), { wrapper: Wrapper });
    expect(second.result.current.data).toEqual(translations());
    expect(second.result.current.isStale).toBe(false);
    expect(api.requests.map((r) => [r.method, r.path, r.headers["X-Church-Id"]])).toEqual([["GET", "/translations", undefined]]);
  });
});
