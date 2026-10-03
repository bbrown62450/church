import { describe, expect, it } from "vitest";

import { bulletinSettings, filledBulletinSettings } from "@/test/fixtures";

import {
  addressError,
  ELEMENTS,
  formErrors,
  formFromSettings,
  isDirty,
  notFilledIn,
  notFilledInLine,
  rebaseForm,
  settingsFromForm,
} from "./bulletin-settings";

describe("bulletin settings (printed bulletin PR 2a)", () => {
  it("edits the address as one text and sends it back as trimmed lines, the parts in the printed order", () => {
    const s = filledBulletinSettings({ starred: ["doxology", "prelude"], leaders: { sermon: "organist", prelude: "liturgist" } });
    const form = formFromSettings(s);
    expect(form.address).toBe("100 Example Street\nSpringfield, ST 00000");
    expect(settingsFromForm(form)).toEqual({ ...s, starred: ["prelude", "doxology"], leaders: { prelude: "liturgist", sermon: "organist" } });
    expect(settingsFromForm({ ...form, address: " 100 Example Street \n\n  \nSpringfield " }).address_lines).toEqual([
      "100 Example Street",
      "Springfield",
    ]);
    expect(ELEMENTS).toHaveLength(21);
  });

  it("allows up to three address lines of up to 60 characters, and names the field a 422 names", () => {
    expect(addressError("a\nb\n\nc")).toBeNull();
    expect(addressError("x".repeat(60))).toBeNull();
    expect(addressError("a\nb\nc\nd")).toBe("Use up to 3 lines of up to 60 characters each.");
    expect(addressError("x".repeat(61))).toBe("Use up to 3 lines of up to 60 characters each.");
    expect(formErrors({ "address_lines.0": "Not a valid value.", phone: "Too long (max 40 characters).", starred: "x" })).toEqual({
      address: "Not a valid value.",
      phone: "Too long (max 40 characters).",
    });
  });

  it("rebases the form on newer data: what was not edited takes the new value, what was edited stays", () => {
    const baseline = formFromSettings(bulletinSettings());
    const current = {
      ...baseline,
      phone: "(555) 010-0100",
      starred: baseline.starred.filter((key) => key !== "doxology"),
      leaders: { ...baseline.leaders, sermon: "organist" as const },
    };
    expect(isDirty(baseline, baseline)).toBe(false);
    expect(isDirty(baseline, current)).toBe(true);
    const next = formFromSettings(
      filledBulletinSettings({ phone: "(555) 999-0000", starred: ["prelude", "doxology"], leaders: { prelude: "liturgist" } }),
    );
    const rebased = rebaseForm(baseline, current, next);
    expect(rebased).toEqual({
      ...next,
      phone: "(555) 010-0100",
      starred: ["prelude"],
      leaders: { prelude: "liturgist", sermon: "organist" },
    });
    expect(isDirty(next, rebased)).toBe(true);
    expect(rebaseForm(baseline, baseline, next)).toEqual(next);
  });

  it("lists the blank standing fields in the page's order", () => {
    expect(notFilledIn(filledBulletinSettings())).toEqual([]);
    expect(notFilledIn(bulletinSettings())).toEqual([
      "address",
      "phone",
      "email",
      "website",
      "Facebook name",
      "service time",
      "worship leader",
      "liturgist",
      "organist",
    ]);
    const missing = notFilledIn(filledBulletinSettings({ phone: " ", organist: "", stand_note: "", gloria_patri_words: "" }));
    expect(notFilledInLine(missing)).toBe("Not filled in: phone, organist, stand note, Gloria Patri words.");
  });
});
