/** `useDebouncedValue` (S Testing `use-debounced-value.test.ts`), with fake timers. */
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDebouncedValue } from "./use-debounced-value";

function renderDebounced(initial: string) {
  const seen: string[] = [];
  const hook = renderHook(
    ({ value }: { value: string }) => {
      const debounced = useDebouncedValue(value, 400);
      seen.push(debounced);
      return debounced;
    },
    { initialProps: { value: initial } },
  );
  return { ...hook, seen };
}

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useDebouncedValue", () => {
  it("starts at the current value with no delay", () => {
    const { result } = renderDebounced("2026-10-04");
    expect(result.current).toBe("2026-10-04");
  });

  it("trails a change by 400 ms", () => {
    const { result, rerender } = renderDebounced("2026-10-04");
    rerender({ value: "2026-10-11" });
    act(() => vi.advanceTimersByTime(399));
    expect(result.current).toBe("2026-10-04");
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("2026-10-11");
  });

  it("lets only the last of several quick changes through", () => {
    const { result, rerender, seen } = renderDebounced("2026-10-04");
    rerender({ value: "0002-10-18" });
    act(() => vi.advanceTimersByTime(200));
    rerender({ value: "0020-10-18" });
    act(() => vi.advanceTimersByTime(200));
    rerender({ value: "2026-10-18" });
    act(() => vi.advanceTimersByTime(399));
    expect(result.current).toBe("2026-10-04");
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe("2026-10-18");
    expect(new Set(seen)).toEqual(new Set(["2026-10-04", "2026-10-18"]));
  });
});
