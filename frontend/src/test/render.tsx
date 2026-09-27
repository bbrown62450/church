/**
 * `renderWithProviders` (F §5.2): renders `ui` the way the app does, inside a
 * `QueryClientProvider` (a fresh client per call, `retry: false`, with the app's
 * `handleAuthErrors`), a `MeProvider` when `me` is given and a `ChurchProvider`
 * when `church` is given. `path` sets what the mocked `usePathname()` returns
 * (`setup-dom.ts` resets it to "/" before each test).
 *
 * It renders no `<Toaster />`: a test that asserts toast text renders one
 * next to `ui`. Requests go through the real `apiFetch`, so stub `fetch` with
 * `installFakeApi` in the test.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement, ReactNode } from "react";

import type { Church, Me } from "@/lib/api/types";
import { ChurchProvider } from "@/lib/church-context";
import { MeProvider } from "@/lib/me-context";
import { makeQueryClient } from "@/lib/queries/client";

import { setTestPath } from "./mocks";

export type UserEvent = ReturnType<typeof userEvent.setup>;

export type RenderWithProvidersOptions = {
  me?: Me;
  church?: Church;
  path?: string;
  queryClient?: QueryClient;
};

export function renderWithProviders(
  ui: ReactElement,
  { me, church, path, queryClient = makeQueryClient({ queries: { retry: false } }) }: RenderWithProvidersOptions = {},
): RenderResult & { user: UserEvent; queryClient: QueryClient } {
  if (path !== undefined) setTestPath(path);

  function Wrapper({ children }: { children: ReactNode }) {
    let tree = children;
    if (church) tree = <ChurchProvider value={church}>{tree}</ChurchProvider>;
    if (me) tree = <MeProvider value={me}>{tree}</MeProvider>;
    return <QueryClientProvider client={queryClient}>{tree}</QueryClientProvider>;
  }

  const user = userEvent.setup();
  // Object.assign, not a spread: with `wrapper` tsc picks RTL's generic `render` overload,
  // and a spread of that result loses the bound queries' types (getByRole & co.).
  return Object.assign(render(ui, { wrapper: Wrapper }), { user, queryClient });
}
