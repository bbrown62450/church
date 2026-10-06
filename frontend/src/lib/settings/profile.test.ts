import { describe, expect, it } from "vitest";

import { churchProfile, hymnals, translations } from "@/test/fixtures";

import { diffProfile, hasChanges, hymnalItems, profileFormFrom, rebaseForm, rebaseProfile, translationItems } from "./profile";

describe("the Church page's form (slice 6a-1)", () => {
  it("starts at the stored values, or the ones in effect, and sends only what changed, cleaned", () => {
    const base = profileFormFrom(churchProfile({ bible_translation: null, default_hymnal: null }));
    expect(base).toMatchObject({ name: "Grace", timezone: "America/New_York", bible_translation: "web", default_hymnal: "GG2013" });
    expect(diffProfile(base, base)).toEqual({});
    expect(hasChanges(base, { ...base, name: " Grace " })).toBe(false);
    expect(diffProfile(base, { ...base, name: " Example Church " })).toEqual({ name: "Example Church" });
    expect(diffProfile(base, { ...base, default_benediction: "" })).toEqual({ default_benediction: "" });
    expect(diffProfile(base, { ...base, default_benediction: " Go in peace.\r\nAmen. " })).toEqual({
      default_benediction: "Go in peace.\nAmen.",
    });
    expect(diffProfile(base, { ...base, bible_translation: "kjv", default_hymnal: "PH1990" })).toEqual({
      bible_translation: "kjv",
      default_hymnal: "PH1990",
    });
  });

  it("keeps a stale stored translation or hymnal, and never sends a hymnal when the church has none", () => {
    const stale = profileFormFrom(churchProfile({ bible_translation: "esv", default_hymnal: "PH1990" }));
    expect([stale.bible_translation, stale.default_hymnal]).toEqual(["esv", "PH1990"]);
    expect(diffProfile(stale, { ...stale, name: "Renamed" })).toEqual({ name: "Renamed" });
    const none = profileFormFrom(churchProfile({ default_hymnal: null, effective_hymnal: null }));
    expect(none.default_hymnal).toBe("");
    expect(diffProfile({ ...none, default_hymnal: "GG2013" }, none)).toEqual({});
  });

  it("rebases on newer data: untouched fields take it, edited ones keep the edit", () => {
    const base = profileFormFrom(churchProfile());
    const edited = { ...base, default_benediction: "Go in peace." };
    const next = profileFormFrom(churchProfile({ name: "Grace Renamed" }));
    const rebased = rebaseForm(base, edited, next);
    expect(rebased).toEqual({ ...next, default_benediction: "Go in peace." });
    expect(diffProfile(next, rebased)).toEqual({ default_benediction: "Go in peace." });
  });

  it("rebases a field whose edit cleans away (a trailing line break) onto newer data, so a later save cannot revert it", () => {
    // Review m1: Save and the leave guard compare cleaned values, so the rebase must too.
    const base = { ...profileFormFrom(churchProfile()), default_benediction: "Go in peace." };
    const form = { ...base, default_benediction: "Go in peace.\n", name: "Grace " };
    expect(hasChanges(base, form)).toBe(false);
    const next = { ...base, default_benediction: "The Lord bless you and keep you." };
    const rebased = rebaseProfile(base, form, next);
    expect(rebased.default_benediction).toBe("The Lord bless you and keep you.");
    expect(hasChanges(next, rebased)).toBe(false);
    expect(diffProfile(next, rebased)).toEqual({});
    // A real edit still keeps the edit.
    expect(rebaseProfile(base, { ...base, default_benediction: "Go now." }, next).default_benediction).toBe("Go now.");
    // A stored "\r\n" the textarea reports as "\n" is not an edit either.
    const crlf = { ...base, default_benediction: "Go.\r\nAmen." };
    expect(rebaseProfile(crlf, { ...crlf, default_benediction: "Go.\nAmen." }, next).default_benediction).toBe(
      "The Lord bless you and keep you.",
    );
  });

  it("lists a stored translation or hymnal that is no longer offered, and nothing more", () => {
    expect(translationItems(translations(), "kjv")).toEqual({
      web: "World English Bible (WEB)",
      kjv: "King James Version (KJV)",
      esv: "English Standard Version (ESV)",
    });
    expect(translationItems(translations({ items: [{ id: "web", label: "World English Bible (WEB)" }] }), "esv")).toEqual({
      web: "World English Bible (WEB)",
      esv: "ESV (not available on this server)",
    });
    expect(hymnalItems(hymnals(), null)).toEqual({ GG2013: "GG2013" });
    expect(hymnalItems(hymnals(), "PH1990")).toEqual({ GG2013: "GG2013", PH1990: "PH1990 (no longer in your hymnals)" });
  });
});
