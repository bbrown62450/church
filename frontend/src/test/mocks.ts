/**
 * Spies behind the module mocks that `setup-dom.ts` installs for every DOM test
 * (clarification 15): `next/navigation` and `@/lib/supabase/client`. The real
 * `lib/auth.ts` therefore runs under test, and tests assert on these spies.
 * `resetTestMocks()` runs before each DOM test (setup-dom.ts).
 */
import { vi } from "vitest";

/** The access token the default `getSession` spy hands out. */
export const TEST_ACCESS_TOKEN = "test-access-token";

/** What `useRouter()` returns in DOM tests (one stable object, like Next's). */
export const testRouter = {
  replace: vi.fn(),
  push: vi.fn(),
  refresh: vi.fn(),
  back: vi.fn(),
};

/** `createClient().auth` in DOM tests. */
export const supabaseAuth = {
  getSession: vi.fn(),
  signOut: vi.fn(),
  signInWithOAuth: vi.fn(),
};

let pathname = "/";
let searchParams = new URLSearchParams();

/** Sets what `usePathname()` and `useSearchParams()` return, e.g. "/welcome?tab=join". */
export function setTestPath(path: string): void {
  const url = new URL(path, "http://localhost");
  pathname = url.pathname;
  searchParams = url.searchParams;
}

/** `usePathname()` in DOM tests. */
export function testPathname(): string {
  return pathname;
}

/** `useSearchParams()` in DOM tests: the same object until the next `setTestPath`. */
export function testSearchParams(): URLSearchParams {
  return searchParams;
}

/**
 * Back to defaults: path "/", a signed-in session, a successful local sign-out and a
 * Google sign-in that starts without error (the real one then leaves the page).
 */
export function resetTestMocks(): void {
  for (const spy of Object.values(testRouter)) spy.mockReset();
  setTestPath("/");
  supabaseAuth.getSession.mockReset();
  supabaseAuth.getSession.mockResolvedValue({
    data: { session: { access_token: TEST_ACCESS_TOKEN } },
    error: null,
  });
  supabaseAuth.signOut.mockReset();
  supabaseAuth.signOut.mockResolvedValue({ error: null });
  supabaseAuth.signInWithOAuth.mockReset();
  supabaseAuth.signInWithOAuth.mockResolvedValue({ data: {}, error: null });
}
