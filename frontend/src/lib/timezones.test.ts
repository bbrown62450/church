import { afterEach, describe, expect, it, vi } from "vitest";

import { FALLBACK_TIMEZONE, browserTimezone, defaultTimezone, listTimezones, timezoneLabel } from "./timezones";

// Never depend on the runner's zone (CI's is UTC, a laptop's is local): stub both Intl calls.
const REAL_OPTIONS = new Intl.DateTimeFormat().resolvedOptions();
const LIST = ["America/Chicago", "America/New_York", "Asia/Calcutta", "Europe/London"];

function stubBrowserZone(timeZone: string): void {
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockReturnValue({ ...REAL_OPTIONS, timeZone });
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("time zones", () => {
  it("defaults to the browser zone when it is listed", () => {
    vi.spyOn(Intl, "supportedValuesOf").mockReturnValue(LIST);
    stubBrowserZone("America/Chicago");
    expect(listTimezones()).toEqual(LIST);
    expect(browserTimezone()).toBe("America/Chicago");
    expect(defaultTimezone(listTimezones())).toBe("America/Chicago");
  });

  it("falls back to America/New_York when the browser zone is not listed or unknown", () => {
    expect(FALLBACK_TIMEZONE).toBe("America/New_York");
    // ICU's list has no UTC, which is what CI's runner reports.
    stubBrowserZone("UTC");
    expect(defaultTimezone(LIST)).toBe("America/New_York");
    // No list (the text-input fallback): nothing is listed, so the fallback.
    expect(defaultTimezone(null)).toBe("America/New_York");
    vi.restoreAllMocks();
    vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockImplementation(() => {
      throw new RangeError("no zone");
    });
    expect(browserTimezone()).toBeNull();
    expect(defaultTimezone(LIST)).toBe("America/New_York");
  });

  it("returns null when Intl.supportedValuesOf is missing, throws or lists nothing", () => {
    vi.stubGlobal("Intl", { DateTimeFormat: Intl.DateTimeFormat });
    expect(listTimezones()).toBeNull();
    vi.unstubAllGlobals();

    vi.spyOn(Intl, "supportedValuesOf").mockImplementation(() => {
      throw new RangeError("Invalid key : timeZone");
    });
    expect(listTimezones()).toBeNull();

    vi.spyOn(Intl, "supportedValuesOf").mockReturnValue([]);
    expect(listTimezones()).toBeNull();
  });

  it("labels a zone by its id with underscores as spaces", () => {
    expect(timezoneLabel("America/New_York")).toBe("America/New York");
    expect(timezoneLabel("America/Argentina/Buenos_Aires")).toBe("America/Argentina/Buenos Aires");
    expect(timezoneLabel("Europe/London")).toBe("Europe/London");
  });
});
