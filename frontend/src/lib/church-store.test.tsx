import { act, renderHook } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it } from "vitest";

import { resetStoredChurchIdForTests, storeChurchId, useStoredChurchId } from "./church";

function Probe() {
  const id = useStoredChurchId();
  return <span>{id === undefined ? "not-read" : String(id)}</span>;
}

// setup-dom.ts already does both after each test; doing them first as well keeps this
// file independent of hook order.
beforeEach(() => {
  window.localStorage.clear();
  resetStoredChurchIdForTests();
});

describe("useStoredChurchId", () => {
  it("is undefined in the server snapshot even when an id is stored", () => {
    window.localStorage.setItem("activeChurchId", "a");
    renderHook(() => useStoredChurchId()); // the client cache now holds "a"

    expect(renderToString(<Probe />)).toBe("<span>not-read</span>");
  });

  it("returns the stored id on the client, or null when nothing is stored", () => {
    const empty = renderHook(() => useStoredChurchId());
    expect(empty.result.current).toBeNull();
    empty.unmount();

    window.localStorage.setItem("activeChurchId", "a");
    resetStoredChurchIdForTests();
    const stored = renderHook(() => useStoredChurchId());
    expect(stored.result.current).toBe("a");
  });

  it("follows storeChurchId in the same tab", () => {
    const { result } = renderHook(() => useStoredChurchId());
    expect(result.current).toBeNull();

    act(() => storeChurchId("b"));
    expect(result.current).toBe("b");
    expect(window.localStorage.getItem("activeChurchId")).toBe("b");

    act(() => storeChurchId(null));
    expect(result.current).toBeNull();
    expect(window.localStorage.getItem("activeChurchId")).toBeNull();
  });

  it("ignores a storage event from another tab", () => {
    window.localStorage.setItem("activeChurchId", "a");
    const { result, rerender } = renderHook(() => useStoredChurchId());
    expect(result.current).toBe("a");

    act(() => {
      window.localStorage.setItem("activeChurchId", "b");
      window.dispatchEvent(
        new StorageEvent("storage", { key: "activeChurchId", oldValue: "a", newValue: "b" }),
      );
    });
    rerender();
    expect(result.current).toBe("a");
  });

  it("re-reads localStorage after resetStoredChurchIdForTests", () => {
    act(() => storeChurchId("a"));
    window.localStorage.setItem("activeChurchId", "b"); // written behind the cache's back

    expect(renderHook(() => useStoredChurchId()).result.current).toBe("a");
    resetStoredChurchIdForTests();
    expect(renderHook(() => useStoredChurchId()).result.current).toBe("b");
  });
});
