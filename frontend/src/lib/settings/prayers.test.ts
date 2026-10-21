/** Settings → Prayers' form rules (slice 6a-3b; 6a spec "Pure helpers" `prayers.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import type { PrayerLibrary } from "@/lib/api/types";
import { DEFAULT_PEW_VOICES, prayer, prayerLibrary } from "@/test/fixtures";

import {
  afterSave,
  charCount,
  cleanText,
  DESCRIPTION_REQUIRED,
  DESCRIPTION_TOO_LONG,
  firstLine,
  hasErrors,
  hasLibraryChanges,
  libraryErrors,
  libraryFieldErrors,
  libraryFormFrom,
  listChanged,
  MAX_DESCRIPTION_CHARS,
  MAX_VOICES,
  MAX_VOICES_ON,
  namesLibraryField,
  newRow,
  newVoice,
  PRAYER_TYPE_LABELS,
  PRAYER_TYPES,
  prayersPayload,
  rebaseLibrary,
  STARTER_VOICES,
  starterVoiceRows,
  TOO_MANY_ON,
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

  it("gives a repeated stored id its own row key, and never carries a key over by a repeated id", () => {
    const copy = prayer(1, { text: "A copy." });
    const form = libraryFormFrom(prayerLibrary([prayer(1), prayer(2), copy]));
    expect(form.rows.map((r) => r.key)).toEqual([prayer(1).id, prayer(2).id, "saved-2"]);
    expect(rebaseLibrary(form, form, form).rows.map((r) => r.key)).toEqual([prayer(1).id, prayer(2).id, "saved-2"]);
    const open = [{ ...newRow("new-1"), id: prayer(1).id, type: "other" as const, text: "Bless." }];
    const keys = rebaseLibrary({ rows: open, profile: "", voices: [] }, { rows: open, profile: "", voices: [] }, form).rows.map((r) => r.key);
    expect(new Set(keys).size).toBe(3);
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
      voices: form.voices,
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
    const errors = libraryErrors({ rows, profile: "z".repeat(2_001), voices: [] });
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
    expect(rebaseLibrary(base, typed, newer)).toEqual({ rows: newer.rows, profile: "Mine.", voices: newer.voices });
    const removed = { ...base, rows: base.rows.slice(1) };
    expect(rebaseLibrary(base, removed, newer)).toEqual({ rows: removed.rows, profile: "Another admin's profile.", voices: newer.voices });
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

  describe("the pew voices (pew voices spec 2026-10-20)", () => {
    it("starts at the owner's five, and sends the voices only when they changed", () => {
      const base = libraryFormFrom(prayerLibrary());
      expect(base.voices.map((v) => [v.key, v.description, v.on])).toEqual(
        DEFAULT_PEW_VOICES.map((v, i) => [`voice-${i}`, v.description, true]),
      );
      expect(prayersPayload(base, base)).not.toHaveProperty("pew_voices");
      const same = { ...base, voices: base.voices.map((v) => ({ ...v, description: ` ${v.description}\n` })) };
      expect(hasLibraryChanges(base, same)).toBe(false);
      const edited = { ...base, voices: [{ ...base.voices[0], on: false }, { ...newVoice("new-voice-1"), description: " A  nurse\non nights " }] };
      expect(hasLibraryChanges(base, edited)).toBe(true);
      expect(prayersPayload(edited, base).pew_voices).toEqual([
        { description: "Sharp, very conservative, reads every word", on: false },
        { description: "A nurse on nights", on: true },
      ]);
      expect(prayersPayload({ ...base, voices: [] }, base).pew_voices).toEqual([]);
    });

    it("reads the starter voices from a server that answers without them, and never sends them unchanged", () => {
      const older: Partial<PrayerLibrary> = { ...prayerLibrary() };
      delete older.pew_voices; // a backend deployed before the voices
      const form = libraryFormFrom(older as PrayerLibrary);
      expect(form.voices.map((v) => ({ description: v.description, on: v.on }))).toEqual(DEFAULT_PEW_VOICES);
      expect(prayersPayload(form, form)).not.toHaveProperty("pew_voices");
      expect(STARTER_VOICES).toEqual(DEFAULT_PEW_VOICES);
      expect(starterVoiceRows("s").map((v) => [v.key, v.on])).toEqual([0, 1, 2, 3, 4].map((i) => [`s-${i}`, true]));
    });

    it("checks the voices with the server's words: a blank or long description, more than 6 on", () => {
      const voices = [
        { ...newVoice("a"), description: "  " },
        { ...newVoice("b"), description: "x".repeat(301) },
        ...[1, 2, 3, 4, 5].map((n) => ({ ...newVoice(`on-${n}`), description: `Voice ${n}` })),
      ];
      const errors = libraryErrors({ rows: [], profile: "", voices });
      expect(errors).toEqual({
        rows: {},
        voices: { a: DESCRIPTION_REQUIRED, b: DESCRIPTION_TOO_LONG },
        voicesList: TOO_MANY_ON,
      });
      expect(hasErrors({ rows: {}, voicesList: TOO_MANY_ON })).toBe(true);
      const six = voices.slice(1).map((v) => ({ ...v, description: "Fine." }));
      expect(hasErrors(libraryErrors({ rows: [], profile: "", voices: six }))).toBe(false);
      expect([MAX_VOICES, MAX_VOICES_ON, MAX_DESCRIPTION_CHARS]).toEqual([12, 6, 300]);
    });

    it("puts a refusal's voice fields on the voices that were sent", () => {
      const fields = { "pew_voices.1.description": DESCRIPTION_TOO_LONG, pew_voices: TOO_MANY_ON };
      const e = new ApiError(422, "invalid_request", "x", { fields });
      expect(namesLibraryField(e)).toBe(true);
      expect(libraryFieldErrors(e, [], ["v0", "v1"])).toEqual({ rows: {}, voices: { v1: DESCRIPTION_TOO_LONG }, voicesList: TOO_MANY_ON });
    });

    it("rebases the voices as their own part and keeps their keys through a save", () => {
      const base = libraryFormFrom(prayerLibrary());
      const newer = libraryFormFrom(prayerLibrary([], { pew_voices: [{ description: "A nurse", on: true }] }));
      expect(rebaseLibrary(base, base, newer).voices).toEqual(newer.voices);
      const mine = { ...base, voices: [...base.voices, newVoice("new-voice-1")] };
      expect(rebaseLibrary(base, mine, newer).voices).toEqual(mine.voices);
      const sent = { ...base, voices: [{ ...newVoice("new-voice-1"), description: "A nurse" }] };
      const { baseline } = afterSave(sent, sent, prayerLibrary([], { pew_voices: [{ description: "A nurse", on: true }] }));
      expect(baseline.voices).toEqual([{ key: "new-voice-1", description: "A nurse", on: true }]);
    });
  });
});
