/** Settings → Rubric's form rules (slice 6a-3a; 6a spec "Pure helpers" `rubric.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { isInvalidRubric } from "@/lib/queries/rubric";
import { defaultRubric, rubric } from "@/test/fixtures";

import {
  checklistCustomized,
  checklistError,
  CHECKLISTS,
  cleanPoints,
  rebaseRubric,
  resetAllPatch,
  rubricErrors,
  rubricFormFrom,
  rubricPatch,
  yearError,
} from "./rubric";

const DEFAULTS = defaultRubric();
const BENEDICTION = CHECKLISTS.find((l) => l.key === "prayers.benediction")!;

describe("Settings → Rubric's form rules (slice 6a-3a)", () => {
  it("lists the hymn slots, then the prayers in section order, with their titles", () => {
    expect(CHECKLISTS.map((l) => l.label)).toEqual([
      "Opening (Gathering) Hymn",
      "Response Hymn (after the sermon)",
      "Closing (Sending) Hymn",
      "Call to Worship",
      "Opening Prayer",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "Prayers of the People",
      "Offertory Prayer",
      "Benediction",
    ]);
    expect(CHECKLISTS[0].key).toBe("hymns.opening");
  });

  it("cleans points as the server does and says what is wrong with the server's words", () => {
    expect(cleanPoints(["  Sends   the people\nout. ", "", " \t ", "Amen"])).toEqual(["Sends the people out.", "Amen"]);
    expect(checklistError(["", "  "])).toBe("Keep at least one point, or use Reset to default.");
    expect(checklistError(["x"])).toBeNull();
    expect([yearError("1500", 2026), yearError(" 2026 ", 2026)]).toEqual([null, null]);
    for (const bad of ["1499", "2027", "", "19x0", "1900.5"]) {
      expect(yearError(bad, 2026)).toBe("The preferred year must be between 1500 and 2026.");
    }
    const form = rubricFormFrom(DEFAULTS);
    form.checklists["hymns.closing"] = [];
    form.prefer_before_year = "1400";
    expect(rubricErrors(form, 2026)).toEqual({
      "hymns.closing": "Keep at least one point, or use Reset to default.",
      prefer_before_year: "The preferred year must be between 1500 and 2026.",
    });
  });

  it("sends only what changed, cleaned; an item back on its default is null; never an empty list", () => {
    const baseline = rubricFormFrom(rubric({ prayers: { benediction: ["Ours."] } }).rubric);
    expect(rubricPatch(baseline, baseline, DEFAULTS)).toEqual({});
    const current = rubricFormFrom(rubric({ prayers: { benediction: ["Ours."] } }).rubric);
    current.checklists["hymns.closing"] = ["  Joyful\nand sending. ", ""];
    current.checklists["prayers.benediction"] = [...DEFAULTS.prayers.benediction, " "];
    current.checklists["prayers.assurance"] = [`${DEFAULTS.prayers.assurance[0]} `, DEFAULTS.prayers.assurance[1]];
    current.prefer_before_year = " 1900 ";
    current.prefer_familiar = false;
    expect(rubricPatch(baseline, current, DEFAULTS)).toEqual({
      hymns: { closing: ["Joyful and sending."] },
      prayers: { benediction: null },
      prefer_before_year: 1900,
      prefer_familiar: false,
    });
    const back = { ...current, prefer_before_year: "1970", prefer_familiar: true };
    const changed = rubricFormFrom(rubric({ prefer_before_year: 1900, prefer_familiar: false }).rubric);
    expect(rubricPatch(changed, back, DEFAULTS)).toMatchObject({ prefer_before_year: null, prefer_familiar: null });
  });

  it("marks a checklist Customized only when its cleaned points differ from the default", () => {
    const form = rubricFormFrom(DEFAULTS);
    expect(checklistCustomized(form, DEFAULTS, BENEDICTION)).toBe(false);
    form.checklists["prayers.benediction"] = [` ${DEFAULTS.prayers.benediction[0]}`, DEFAULTS.prayers.benediction[1], ""];
    expect(checklistCustomized(form, DEFAULTS, BENEDICTION)).toBe(false);
    form.checklists["prayers.benediction"] = [DEFAULTS.prayers.benediction[0]];
    expect(checklistCustomized(form, DEFAULTS, BENEDICTION)).toBe(true);
  });

  it("resets exactly the customized items, and rebases untouched items on newer data", () => {
    expect(resetAllPatch(["hymns.closing", "prayers.benediction", "prefer_before_year", "prefer_familiar"])).toEqual({
      hymns: { closing: null },
      prayers: { benediction: null },
      prefer_before_year: null,
      prefer_familiar: null,
    });
    expect(resetAllPatch([])).toEqual({});
    const oldBaseline = rubricFormFrom(DEFAULTS);
    const current = { ...rubricFormFrom(DEFAULTS), prefer_familiar: false };
    current.checklists["prayers.benediction"] = ["Ours."];
    const next = rubricFormFrom(rubric({ prefer_before_year: 1900, prayers: { benediction: ["Theirs."], assurance: ["Theirs too."] } }).rubric);
    const rebased = rebaseRubric(oldBaseline, current, next);
    expect(rebased.checklists["prayers.benediction"]).toEqual(["Ours."]);
    expect(rebased.checklists["prayers.assurance"]).toEqual(["Theirs too."]);
    expect([rebased.prefer_before_year, rebased.prefer_familiar]).toEqual(["1900", false]);
  });

  it("knows the server's 422 about the rubric", () => {
    expect(isInvalidRubric(new ApiError(422, "invalid_rubric", "Checklist points cannot contain control characters."))).toBe(true);
    expect(isInvalidRubric(new ApiError(422, "invalid_request", "The request was not valid."))).toBe(false);
  });
});
