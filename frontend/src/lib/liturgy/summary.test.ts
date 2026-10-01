/**
 * `liturgyCounts` (slice 4 spec, Frontend "Builder shell"; Testing
 * `summary.test.ts`): the one count behind the step's status and the summary.
 */
import { describe, expect, it } from "vitest";

import { SECTION_KEYS } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { addCustomElement, editCardText, setCardEnabled, setCommunion } from "./cards";
import { applyLiturgyDefaults } from "./defaults";
import { liturgyCounts } from "./summary";

describe("liturgyCounts (S summary.ts)", () => {
  it("counts enabled cards, those with text, communion and custom elements", () => {
    const fresh = applyLiturgyDefaults(testDraft(), { defaultBenediction: "" }); // a church with no default
    expect(liturgyCounts(fresh)).toEqual({ ready: 0, enabled: 7, communion: true, customCount: 0 });
    // The Benediction following a non-blank church default counts as ready.
    const withDefault = applyLiturgyDefaults(fresh, { defaultBenediction: "Halverson" });
    expect(liturgyCounts(withDefault)).toMatchObject({ ready: 1, enabled: 7 });
    expect(liturgyCounts(editCardText(withDefault, "assurance", "  \n "))).toMatchObject({ ready: 1, enabled: 7 });
    const allOff = SECTION_KEYS.reduce((d, key) => setCardEnabled(d, key, false), withDefault);
    expect(liturgyCounts(allOff)).toMatchObject({ ready: 0, enabled: 0 });
    let d = addCustomElement(setCommunion(withDefault, false), { label: "Anthem", text: "", insert_after: "sermon" }, "a");
    d = addCustomElement(d, { label: "Minute for Mission", text: "", insert_after: "end" }, "b");
    expect(liturgyCounts(d)).toEqual({ ready: 1, enabled: 7, communion: false, customCount: 2 });
  });
});
