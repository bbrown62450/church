/**
 * jsdom applies no stylesheet, so a test that cares where a Tailwind footer
 * sits at a given width reads it from the classes: `positionAt` resolves the
 * position utilities (`sticky`, `static`, ...) with their breakpoint variants
 * (`md:`, `max-md:`, ...) the way Tailwind's default breakpoints would at
 * `width`. A variant it does not know throws, so a new kind of rule is noticed
 * here rather than silently ignored. `setViewport` sets window's size and a
 * `matchMedia` that answers `min-width`/`max-width` queries for it.
 */
import { vi } from "vitest";

const BREAKPOINTS: Record<string, number> = { sm: 640, md: 768, lg: 1024, xl: 1280, "2xl": 1536 };
const POSITIONS = new Set(["static", "fixed", "absolute", "relative", "sticky"]);

function variantMatches(variant: string, width: number): boolean {
  if (variant.startsWith("max-") && variant.slice(4) in BREAKPOINTS) return width < BREAKPOINTS[variant.slice(4)];
  if (variant in BREAKPOINTS) return width >= BREAKPOINTS[variant];
  throw new Error(`positionAt: unknown variant "${variant}"`);
}

/** The CSS position the element's classes give it at `width` (static when none does). */
export function positionAt(element: Element, width: number = window.innerWidth): string {
  let base = "static";
  let responsive: string | null = null;
  for (const token of Array.from(element.classList)) {
    const parts = token.split(":");
    const utility = parts.pop()!;
    if (!POSITIONS.has(utility)) continue;
    if (parts.length === 0) base = utility;
    else if (parts.every((variant) => variantMatches(variant, width))) responsive = utility;
  }
  return responsive ?? base;
}

function lengthPx(value: string): number {
  const number = parseFloat(value);
  return value.endsWith("rem") || value.endsWith("em") ? number * 16 : number;
}

/**
 * Sets window's size, and a matchMedia that answers width queries for it.
 * Returns the undo: call it in a `finally`, so a failing test leaves no spy behind.
 */
export function setViewport(width: number, height: number): () => void {
  const saved = { innerWidth: window.innerWidth, innerHeight: window.innerHeight };
  Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: width });
  Object.defineProperty(window, "innerHeight", { configurable: true, writable: true, value: height });
  const media = vi.spyOn(window, "matchMedia").mockImplementation((query: string) => {
    const min = /min-width:\s*([\d.]+(?:px|rem|em))/.exec(query);
    const max = /max-width:\s*([\d.]+(?:px|rem|em))/.exec(query);
    const matches = Boolean(min || max) && (!min || width >= lengthPx(min[1])) && (!max || width <= lengthPx(max[1]));
    return {
      matches,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    } as MediaQueryList;
  });
  return () => {
    media.mockRestore();
    Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: saved.innerWidth });
    Object.defineProperty(window, "innerHeight", { configurable: true, writable: true, value: saved.innerHeight });
  };
}
