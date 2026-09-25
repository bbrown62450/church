import { describe, expect, it } from "vitest";

import { createLatestTracker } from "@/lib/latest";

describe("createLatestTracker", () => {
  it("treats a single request as latest", () => {
    const tracker = createLatestTracker();
    const isLatest = tracker.begin();
    expect(isLatest()).toBe(true);
  });

  it("marks the first request stale once a second one begins", () => {
    const tracker = createLatestTracker();
    const first = tracker.begin();
    const second = tracker.begin();
    expect(first()).toBe(false);
    expect(second()).toBe(true);
  });

  it("keeps only the most recently started request latest when resolved out of order", async () => {
    const tracker = createLatestTracker();

    const first = tracker.begin();
    const firstResult = new Promise<string>((resolve) => setTimeout(() => resolve("A"), 20));

    const second = tracker.begin();
    const secondResult = new Promise<string>((resolve) => setTimeout(() => resolve("B"), 5));

    const [, secondValue] = await Promise.all([firstResult, secondResult]);
    expect(second()).toBe(true);
    expect(secondValue).toBe("B");

    const firstValue = await firstResult;
    expect(firstValue).toBe("A");
    expect(first()).toBe(false);
  });
});
