/** Settings → Prayers' form rules (slice 6a-3b; 6a spec "Pure helpers" `prayers.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { prayer, prayerLibrary } from "@/test/fixtures";

import {
  afterSave,
  charCount,
  cleanText,
  firstLine,
  hasErrors,
  hasLibraryChanges,
  libraryErrors,
  libraryFieldErrors,
  libraryFormFrom,
  listChanged,
  namesLibraryField,
  newRow,
  PRAYER_TYPE_LABELS,
  PRAYER_TYPES,
  prayersPayload,
  rebaseLibrary,
  type LibraryForm,
} from "./prayers";

const OUT = prayerLibrary([prayer(1), prayer(2, { type: "benediction", text: "Go in peace." })], {
  voice_profile: "Warm and plain.",
});

describe("Settings → Prayers' form rules (slice 6a-3b)", () => {
  it("lists the eight sections in order, then Other, with their labels", () => {
    expect(PRAYER_TYPES.map((type) => PRAYER_TYPE_LABELS[type])).toEqual([
      "Call to Worship",
      "Opening Prayer",
      "Prayer of Confession",
      "Assurance of Pardon",
      "Prayer for Illumination",
      "Prayers of the People",
      "Offertory Prayer",
      "Benediction",
      "Other",
    ]);
  });

  it("reads text the server's way: the first line shown, CRLF as LF, trimmed, counted in characters", () => {
    expect(firstLine("\n \n  Holy God,  \nwe gather.")).toBe("Holy God,");
    expect(firstLine("   ")).toBe("");
    expect(cleanText("  Go in peace.\r\nAmen.\r\n ")).toBe("Go in peace.\nAmen.");
    expect(charCount("Amen \u{1F64F}")).toBe(6); // one character, as Python counts it, not two UTF-16 units
  });

  it("gives a stored prayer with an empty id its own row key, and sends it as a new prayer", () => {
    const form = libraryFormFrom(prayerLibrary([prayer(1, { id: "" }), prayer(2), prayer(3, { id: "" })]));
    expect(form.rows.map((r) => r.key)).toEqual(["saved-0", prayer(2).id, "saved-2"]);
    expect(prayersPayload(form).prayers.map((p) => p.id)).toEqual([undefined, prayer(2).id, undefined]);
    expect(rebaseLibrary(form, form, form).rows.map((r) => r.key)).toEqual(["saved-0", prayer(2).id, "saved-2"]);
  });

  it("starts at the saved library and sends it back whole: saved prayers with their ids, new ones without", () => {
    const form = libraryFormFrom(OUT);
    expect(form.rows.map((r) => [r.key, r.id, r.type])).toEqual([
      [prayer(1).id, prayer(1).id, "prayer_of_confession"],
      [prayer(2).id, prayer(2).id, "benediction"],
    ]);
    const edited: LibraryForm = {
      rows: [{ ...form.rows[1], text: " Go in peace.\r\nAmen. " }, { ...newRow("new-1"), type: "other", text: " Bless this meal. " }],
      profile: " Warm.\r\n",
    };
    expect(prayersPayload(edited)).toEqual({
      prayers: [
        { id: prayer(2).id, type: "benediction", text: "Go in peace.\nAmen." },
        { type: "other", text: "Bless this meal." },
      ],
      voice_profile: "Warm.",
    });
  });

  it("counts only a change the server would store", () => {
    const base = libraryFormFrom(OUT);
    const same = { ...base, rows: base.rows.map((r) => ({ ...r, text: `  ${r.text}\r\n` })), profile: "Warm and plain. " };
    expect(hasLibraryChanges(base, same)).toBe(false);
    expect(hasLibraryChanges(base, { ...base, profile: "Warm." })).toBe(true);
    expect(listChanged(base.rows, [base.rows[1], base.rows[0]])).toBe(true);
    expect(listChanged(base.rows, base.rows.slice(1))).toBe(true);
    expect(listChanged(base.rows, [...base.rows, newRow("new-1")])).toBe(true);
    expect(listChanged(base.rows, [{ ...base.rows[0], type: "other" }, base.rows[1]])).toBe(true);
  });

  it("checks the library with the server's words before sending", () => {
    const rows = [
      { ...newRow("a"), type: "other" as const, text: "  \n " },
      { ...newRow("b"), text: "Lord." },
      { ...newRow("c"), type: "benediction" as const, text: ` ${"x".repeat(6_000)} ` },
      { ...newRow("d"), type: "benediction" as const, text: "y".repeat(6_001) },
    ];
    const errors = libraryErrors({ rows, profile: "z".repeat(2_001) });
    expect(errors).toEqual({
      rows: {
        a: { text: "Prayer text is required." },
        b: { type: "Choose a prayer type." },
        d: { text: "This prayer is too long (6,000 characters at most)." },
      },
      profile: "The voice profile is too long (2,000 characters at most).",
    });
    expect(hasErrors(errors)).toBe(true);
    expect(hasErrors(libraryErrors(libraryFormFrom(OUT)))).toBe(false);
  });

  it("puts a refusal's fields on the rows that were sent, and leaves the rest to a toast", () => {
    const fields = { "prayers.1.text": "Prayer text is required.", "prayers.0.type": "Choose a prayer type.", voice_profile: "Too long." };
    expect(libraryFieldErrors(new ApiError(422, "invalid_request", "x", { fields }), ["k0", "k1"])).toEqual({
      rows: { k0: { type: "Choose a prayer type." }, k1: { text: "Prayer text is required." } },
      profile: "Too long.",
    });
    const pydantic = { "prayers.0.text": "Too long (max 20000 characters)." };
    expect(libraryFieldErrors(new ApiError(422, "invalid_request", "x", { fields: pydantic }), ["k0"])).toEqual({
      rows: { k0: { text: "Too long (max 20000 characters)." } },
    });
    expect(namesLibraryField(new ApiError(422, "invalid_request", "x", { fields }))).toBe(true);
    const count = { prayers: "You can keep up to 30 prayers." };
    expect(libraryFieldErrors(new ApiError(422, "invalid_request", "x", { fields: count }), ["k0"])).toBeNull();
    expect(namesLibraryField(new ApiError(422, "invalid_request", "x", { fields: count }))).toBe(false);
    expect(libraryFieldErrors(new ApiError(422, "invalid_request", "x", { fields: { "prayers.5.text": "x" } }), ["k0"])).toBeNull();
    expect(libraryFieldErrors(new ApiError(403, "forbidden", "x"), ["k0"])).toBeNull();
  });

  it("rebases on newer data: an untouched list or profile takes it, an edited one keeps the edit", () => {
    const base = libraryFormFrom(OUT);
    const newer = libraryFormFrom(prayerLibrary([prayer(3)], { voice_profile: "Another admin's profile." }));
    expect(rebaseLibrary(base, base, newer)).toEqual(newer);
    const typed = { ...base, profile: "Mine." };
    expect(rebaseLibrary(base, typed, newer)).toEqual({ rows: newer.rows, profile: "Mine." });
    const removed = { ...base, rows: base.rows.slice(1) };
    expect(rebaseLibrary(base, removed, newer)).toEqual({ rows: removed.rows, profile: "Another admin's profile." });
  });

  it("keeps each prayer's key through a save and a refetch, so an open row stays open", () => {
    const base = libraryFormFrom(OUT);
    const sent = { ...base, rows: [base.rows[0], { ...newRow("new-1"), type: "other" as const, text: "Bless." }] };
    const saved = prayerLibrary([prayer(1), prayer(9, { type: "other", text: "Bless." })], { voice_profile: "Warm and plain." });
    const { baseline, form } = afterSave(sent, sent, saved);
    expect(baseline.rows.map((r) => [r.key, r.id])).toEqual([
      [prayer(1).id, prayer(1).id],
      ["new-1", prayer(9).id],
    ]);
    expect(form).toEqual(baseline);
    expect(rebaseLibrary(baseline, form, libraryFormFrom(saved)).rows.map((r) => r.key)).toEqual([prayer(1).id, "new-1"]);
    const typing = { ...sent, profile: "Typed while saving." };
    expect(afterSave(sent, typing, saved).form.profile).toBe("Typed while saving.");
  });
});
