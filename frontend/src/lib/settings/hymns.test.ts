/** Settings → Hymns' form rules (slice 6a-2; 6a spec "Pure helpers" `hymns.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { timeoutFor } from "@/lib/api/timeouts";
import { hymnFieldErrors } from "@/lib/queries/hymn-library";
import { hymn } from "@/test/fixtures";

import {
  countLine,
  emptyHymnForm,
  hymnFormErrors,
  hymnFormFrom,
  hymnLabel,
  hymnPatch,
  newHymnBody,
  parseHymnalCount,
  parseHymnNumber,
  parseTextYear,
} from "./hymns";

const THIS_YEAR = 2026;
const ADMIN = { thisYear: THIS_YEAR, admin: true };
const MEMBER = { thisYear: THIS_YEAR, admin: false };

describe("Settings → Hymns' form rules (slice 6a-2)", () => {
  it("reads whole numbers in their ranges: blank is unknown, anything else is invalid", () => {
    expect([parseHymnNumber(""), parseHymnNumber(" 12 "), parseHymnNumber("99999")]).toEqual([null, 12, 99999]);
    for (const bad of ["12a", "0", "100000", "1.5", "-3", "1e3"]) expect(parseHymnNumber(bad)).toBe("invalid");
    expect([parseTextYear("", THIS_YEAR), parseTextYear("1826", THIS_YEAR), parseTextYear("2026", THIS_YEAR)]).toEqual([null, 1826, 2026]);
    for (const bad of ["0", "2027", "18a"]) expect(parseTextYear(bad, THIS_YEAR)).toBe("invalid");
    expect([parseHymnalCount(""), parseHymnalCount("0"), parseHymnalCount("1322")]).toEqual([null, 0, 1322]);
    for (const bad of ["-1", "100001"]) expect(parseHymnalCount(bad)).toBe("invalid");
  });

  it("starts the edit form from the hymn, and the add form empty in the default hymnal", () => {
    const h = hymn({ themes: ["Trinity", "Praise"], scripture_refs: "Isaiah 6:3", text_year: 1826, hymnal_count: null });
    expect(hymnFormFrom(h)).toEqual({
      title: "Come, Thou Almighty King",
      number: "403",
      hymnal: "GG2013",
      scripture_refs: "Isaiah 6:3",
      themes: "Trinity, Praise",
      link: "https://hymnary.org/hymn/GG2013/403",
      text_year: "1826",
      hymnal_count: "",
    });
    expect(hymnFormFrom(hymn({ number: null, link: null })).number).toBe("");
    expect(emptyHymnForm("PH1990")).toEqual({
      title: "", number: "", hymnal: "PH1990", scripture_refs: "", themes: "", link: "", text_year: "", hymnal_count: "",
    });
  });

  it("names each field the client can tell is wrong, with the server's words; a member's facts are not checked", () => {
    const bad = { ...emptyHymnForm("GG2013"), title: "  ", number: "0", link: "http://example.org", text_year: "2027", hymnal_count: "-1" };
    expect(hymnFormErrors(bad, ADMIN)).toEqual({
      title: "Hymn title is required.",
      number: "Hymn number must be a whole number.",
      link: "Links must start with https://.",
      text_year: "Year must be a whole number from 1 to 2026.",
      hymnal_count: "Number of hymnals must be a whole number from 0 to 100000.",
    });
    expect(Object.keys(hymnFormErrors(bad, MEMBER))).toEqual(["title", "number", "link"]);
    expect(hymnFormErrors({ ...emptyHymnForm("GG2013"), title: "X", link: " HTTPS://hymnary.org/x " }, ADMIN)).toEqual({});
  });

  it("builds the add body trimmed, blanks as null, and the facts only for an admin", () => {
    const form = { ...emptyHymnForm("GG2013"), title: " Be Thou My Vision ", number: " 339 ", themes: " Guidance ", text_year: "1905" };
    expect(newHymnBody(form, ADMIN)).toEqual({
      title: "Be Thou My Vision", number: 339, hymnal: "GG2013", scripture_refs: null, theme: "Guidance", link: null,
      text_year: 1905, hymnal_count: null,
    });
    expect(newHymnBody(form, MEMBER)).not.toHaveProperty("text_year");
    expect(newHymnBody(form, MEMBER)).not.toHaveProperty("hymnal_count");
  });

  it("sends only what changed in an edit, a cleared field as null, and never a member's facts", () => {
    const baseline = hymnFormFrom(hymn({ themes: ["Trinity"], text_year: 1826, hymnal_count: 12 }));
    expect(hymnPatch(baseline, { ...baseline, title: " Come, Thou Almighty King ", number: "0403" }, ADMIN)).toEqual({});
    expect(hymnPatch(baseline, { ...baseline, themes: "", link: " ", number: "" }, ADMIN)).toEqual({ theme: null, link: null, number: null });
    expect(hymnPatch(baseline, { ...baseline, text_year: "1830", hymnal_count: "" }, ADMIN)).toEqual({ text_year: 1830, hymnal_count: null });
    expect(hymnPatch(baseline, { ...baseline, text_year: "1830", hymnal_count: "", hymnal: "PH1990" }, MEMBER)).toEqual({ hymnal: "PH1990" });
  });

  it("labels a hymn and counts the list", () => {
    expect(hymnLabel({ number: 403, title: "Come, Thou Almighty King" })).toBe("#403 Come, Thou Almighty King");
    expect(hymnLabel({ number: null, title: "Untitled Tune" })).toBe("Untitled Tune");
    expect([countLine(853, false), countLine(1, false), countLine(12, true), countLine(1, true)]).toEqual([
      "853 hymns", "1 hymn", "12 matching hymns", "1 matching hymn",
    ]);
  });

  it("maps a 422's fields to the form's (theme is Themes) and gives adding a hymnal a minute", () => {
    const e = new ApiError(422, "invalid_request", "Links must start with https://.", {
      fields: { link: "Links must start with https://.", theme: "Too long (max 2000 characters).", church_id: "x" },
    });
    expect(hymnFieldErrors(e)).toEqual({ link: "Links must start with https://.", themes: "Too long (max 2000 characters)." });
    expect(hymnFieldErrors(new ApiError(409, "conflict", "GG2013 already has #403 X."))).toBeNull();
    expect(timeoutFor("POST", "/hymnals")).toBe(60_000);
    expect(timeoutFor("DELETE", "/hymnals/PH1990")).toBe(20_000);
  });
});
