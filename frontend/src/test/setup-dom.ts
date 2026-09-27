/**
 * Setup for the `dom` Vitest project (jsdom; F §5.2, §4.9 item 8).
 *
 * - jest-dom matchers (`toBeInTheDocument`, …) with their types.
 * - Base UI's jsdom gaps: PointerEvent, ResizeObserver, matchMedia,
 *   scrollIntoView, pointer capture and getAnimations.
 * - Module mocks for every DOM test (clarification 15): `next/navigation` and
 *   `@/lib/supabase/client`, backed by the spies in `./mocks`, so the real
 *   `lib/auth.ts` runs under test.
 * - Before each test the spies go back to their defaults; after each test the
 *   rendered tree is unmounted and both storages are cleared.
 */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, vi } from "vitest";
import { resetStoredChurchIdForTests } from "@/lib/church";
import { resetTestMocks } from "./mocks";

vi.mock("next/navigation", async () => {
  const mocks = await import("./mocks");
  return {
    useRouter: () => mocks.testRouter,
    usePathname: () => mocks.testPathname(),
    useSearchParams: () => mocks.testSearchParams(),
  };
});

vi.mock("@/lib/supabase/client", async () => {
  const mocks = await import("./mocks");
  return { createClient: () => ({ auth: mocks.supabaseAuth }) };
});

// --- jsdom shims (only where jsdom lacks the API) ---------------------------------

if (typeof window.PointerEvent !== "function") {
  class PointerEventShim extends MouseEvent {
    readonly pointerId: number;
    readonly pointerType: string;
    readonly isPrimary: boolean;
    readonly width: number;
    readonly height: number;
    readonly pressure: number;

    constructor(type: string, init: PointerEventInit = {}) {
      super(type, init);
      this.pointerId = init.pointerId ?? 1;
      this.pointerType = init.pointerType ?? "mouse";
      this.isPrimary = init.isPrimary ?? true;
      this.width = init.width ?? 1;
      this.height = init.height ?? 1;
      this.pressure = init.pressure ?? 0;
    }
  }
  window.PointerEvent = PointerEventShim as unknown as typeof PointerEvent;
}

if (typeof window.ResizeObserver !== "function") {
  class ResizeObserverShim {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  }
  window.ResizeObserver = ResizeObserverShim as unknown as typeof ResizeObserver;
}

if (typeof window.matchMedia !== "function") {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

Element.prototype.scrollIntoView ??= function scrollIntoView() {};
Element.prototype.hasPointerCapture ??= () => false;
Element.prototype.setPointerCapture ??= () => {};
Element.prototype.releasePointerCapture ??= () => {};
Element.prototype.getAnimations ??= () => [];

// --- per-test reset -----------------------------------------------------------------

beforeEach(() => {
  resetTestMocks();
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  window.sessionStorage.clear();
  resetStoredChurchIdForTests();
});
