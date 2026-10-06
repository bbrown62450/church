import { describe, expect, it } from "vitest";

import { contact } from "@/test/fixtures";

import { contactFormFrom, contactLabel, contactPatch, EMPTY_CONTACT, hasTyped, newContactBody } from "./contacts";

describe("the Contacts page's forms (slice 5b-1)", () => {
  it("names a contact by its name, or by its address when it has none", () => {
    expect(contactLabel(contact())).toBe("Mary Jones");
    expect(contactLabel(contact({ name: null, email: "office@example.org" }))).toBe("office@example.org");
  });

  it("sends a new contact trimmed, with no name as null", () => {
    expect(newContactBody({ name: " Mary Jones ", email: " mary@example.org " })).toEqual({
      name: "Mary Jones",
      email: "mary@example.org",
    });
    expect(newContactBody({ name: "   ", email: "office@example.org" })).toEqual({ name: null, email: "office@example.org" });
  });

  it("sends an edit's changed fields only, trimmed, and a cleared name as null", () => {
    const base = contactFormFrom(contact());
    expect(base).toEqual({ name: "Mary Jones", email: "mary@example.org" });
    expect(contactPatch(base, { ...base, name: " Mary Jones " })).toEqual({});
    expect(contactPatch(base, { ...base, name: "Mary Smith" })).toEqual({ name: "Mary Smith" });
    expect(contactPatch(base, { ...base, name: "" })).toEqual({ name: null });
    expect(contactPatch(base, { name: "Mary", email: "Mary@example.org" })).toEqual({ name: "Mary", email: "Mary@example.org" });
    expect(contactFormFrom(contact({ name: null }))).toEqual({ name: "", email: "mary@example.org" });
  });

  it("knows when the add form holds something", () => {
    expect(hasTyped(EMPTY_CONTACT)).toBe(false);
    expect(hasTyped({ name: "  ", email: " " })).toBe(false);
    expect(hasTyped({ name: "", email: "m" })).toBe(true);
  });
});
