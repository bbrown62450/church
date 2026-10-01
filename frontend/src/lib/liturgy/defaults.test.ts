/**
 * The liturgy defaults (slice 4 spec, Frontend `defaults.ts`; Testing
 * `defaults.test.ts`): the first-Sunday rule against the shared fixture, and
 * `applyLiturgyDefaults`, which keeps an untouched Benediction on the church
 * default and untouched communion on the date's rule.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { isFirstSundayOfMonth } from "@/lib/dates";
import { setDate } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { editCardText, setCommunion } from "./cards";
import { applyLiturgyDefaults, DEFAULT_BENEDICTION_FALLBACK } from "./defaults";

type Cases = { cases: { date: string; expected: boolean; why: string }[] };

const firstSunday = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/first_sunday.json", import.meta.url), "utf-8"),
) as Cases;

describe("liturgy defaults (S Benediction and the church default; Communion card)", () => {
  it("puts communion on the first Sunday of the month, as the shared fixture says", () => {
    for (const { date, expected, why } of firstSunday.cases) expect(isFirstSundayOfMonth(date), why).toBe(expected);
  });

  it("keeps the Benediction on the church default only while it follows it, including an empty default", () => {
    expect(DEFAULT_BENEDICTION_FALLBACK).toBe("Halverson");
    const fresh = testDraft();
    const filled = applyLiturgyDefaults(fresh, { defaultBenediction: "Halverson" });
    expect(filled.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
    expect(applyLiturgyDefaults(filled, { defaultBenediction: "Halverson" })).toBe(filled);
    const changed = applyLiturgyDefaults(filled, { defaultBenediction: "The Lord bless you and keep you." });
    expect(changed.liturgy.cards.benediction.text).toBe("The Lord bless you and keep you.");
    expect(applyLiturgyDefaults(filled, { defaultBenediction: "" }).liturgy.cards.benediction).toEqual({
      enabled: true,
      text: "",
      origin: "default",
    });
    const edited = editCardText(filled, "benediction", "Go in peace.");
    expect(applyLiturgyDefaults(edited, { defaultBenediction: "Something else" })).toBe(edited);
  });

  it("recomputes communion from the date only while it is the default", () => {
    const d = testDraft(); // October 4, 2026: on
    const moved: DraftV1 = { ...d, readings: { ...d.readings, date_iso: "2026-10-11" } };
    expect(applyLiturgyDefaults(moved, { defaultBenediction: "" }).liturgy.include_communion).toBe(false);
    expect(setDate(d, "2026-10-11").liturgy.include_communion).toBe(false); // the date change applies the same rule
    const chosen = setCommunion(d, true);
    const chosenMoved: DraftV1 = { ...chosen, readings: { ...chosen.readings, date_iso: "2026-10-11" } };
    expect(applyLiturgyDefaults(chosenMoved, { defaultBenediction: "" }).liturgy.include_communion).toBe(true);
  });
});
