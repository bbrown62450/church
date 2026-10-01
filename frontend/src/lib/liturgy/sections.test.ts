/**
 * The TypeScript copy of the 8 sections (slice 4 spec, Testing `defaults.test.ts`
 * "fresh-draft card switches equal shared/liturgy_sections.json"): labels and
 * default switches equal the shared fixture that backend/liturgy_config.SECTIONS
 * also equals, and a fresh draft switches its cards on exactly as it says.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { SECTION_KEYS } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { DEFAULT_ENABLED, SECTION_LABELS } from "./sections";

type Fixture = { sections: { key: string; label: string; default_enabled: boolean }[] };

const fixture = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/liturgy_sections.json", import.meta.url), "utf-8"),
) as Fixture;

describe("liturgy sections (shared/liturgy_sections.json)", () => {
  it("has the fixture's keys, labels and default switches, and a fresh draft's cards follow them", () => {
    expect(fixture.sections.map((s) => s.key)).toEqual([...SECTION_KEYS]);
    expect(SECTION_KEYS.map((key) => SECTION_LABELS[key])).toEqual(fixture.sections.map((s) => s.label));
    expect(SECTION_KEYS.map((key) => DEFAULT_ENABLED[key])).toEqual(fixture.sections.map((s) => s.default_enabled));
    const cards = testDraft().liturgy.cards;
    expect(SECTION_KEYS.map((key) => cards[key].enabled)).toEqual(fixture.sections.map((s) => s.default_enabled));
  });
});
