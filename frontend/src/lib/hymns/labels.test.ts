import { describe, expect, it } from "vitest";

import { hymn } from "@/test/fixtures";

import {
  chipName,
  duplicateNotice,
  hymnText,
  newerYearLabel,
  recentUseLabel,
  recentUseNotice,
  SLOT_META,
} from "./labels";

describe("hymn labels (S Slot cards, Newer-hymn year label)", () => {
  it("names the slots and shows a hymn as #number title", () => {
    expect(SLOT_META.opening).toEqual({ title: "Opening hymn", caption: "Gathering / call to worship", name: "Opening" });
    expect(SLOT_META.response.caption).toBe("After the sermon — responds to the scripture (NT reading)");
    expect(SLOT_META.closing).toEqual({ title: "Closing hymn", caption: "Joyful / sending", name: "Closing" });
    expect(hymnText({ number: 403, title: "Come, Thou Almighty King" })).toBe("#403 Come, Thou Almighty King");
    expect(hymnText({ number: null, title: "Were You There" })).toBe("Were You There");
  });

  it("says Used on for a date before the service and Also planned for after it", () => {
    expect(recentUseNotice("2026-09-07", "2026-10-04")).toBe("Used on September 7, 2026 — within 12 weeks of this service.");
    expect(recentUseNotice("2026-10-18", "2026-10-04")).toBe(
      "Also planned for October 18, 2026 — within 12 weeks of this service.",
    );
    expect(recentUseLabel("2026-09-07", "2026-10-04")).toBe("Used Sep 7");
    expect(recentUseLabel("2026-10-18", "2026-10-04")).toBe("Planned Oct 18");
    expect(recentUseLabel("2025-12-28", "2026-01-04")).toBe("Used Dec 28, 2025");
  });

  it("labels a newer hymn with its year, and names ideas for screen readers", () => {
    const newer = hymn({ title: "Here I Am, Lord", text_year: 1981, newer_than_preferred: true });
    expect(newerYearLabel(newer)).toBe("Written 1981");
    expect(newerYearLabel(hymn({ text_year: 1826 }))).toBeNull();
    expect(newerYearLabel(hymn({ text_year: null, newer_than_preferred: true }))).toBeNull();
    expect(chipName(newer, "response")).toBe("Use Here I Am, Lord, written 1981, as the response hymn");
    expect(chipName(hymn({ text_year: 1826 }), "opening")).toBe("Use Come, Thou Almighty King as the opening hymn");
  });

  it("names the other slots that hold the same hymn", () => {
    expect(duplicateNotice(["closing"])).toBe("Also chosen as the Closing hymn.");
    expect(duplicateNotice(["opening", "closing"])).toBe("Also chosen as the Opening and Closing hymns.");
    expect(duplicateNotice([])).toBeNull();
  });
});
