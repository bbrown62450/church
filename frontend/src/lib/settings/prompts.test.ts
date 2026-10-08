/** Settings → Liturgy prompts' form rules (slice 6a-3a; 6a spec "Pure helpers" `prompts.ts`). */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { keys } from "@/lib/queries/keys";
import { DEFAULT_PROMPTS, liturgyPrompts } from "@/test/fixtures";

import {
  cleanPrompt,
  hasPromptChanges,
  isCustomized,
  PROMPT_KEYS,
  promptFieldErrors,
  promptsPayload,
  promptValuesFrom,
  rebasePrompts,
} from "./prompts";

const OUT = liturgyPrompts({ benediction: "Go in peace." });
const FIELDS = OUT.fields;
const BENEDICTION = FIELDS.find((f) => f.key === "benediction")!;

describe("Settings → Liturgy prompts' form rules (slice 6a-3a)", () => {
  it("starts each card at the church's own wording, else the default", () => {
    const values = promptValuesFrom(OUT);
    expect(Object.keys(values)).toEqual([...PROMPT_KEYS]);
    expect(values.benediction).toBe("Go in peace.");
    expect(values.system).toBe(DEFAULT_PROMPTS.system);
  });

  it("reads a prompt as the server does: CRLF as LF and trimmed; blank or the default is not the church's own", () => {
    expect(cleanPrompt("  Go in peace.\r\nServe.\r\n ")).toBe("Go in peace.\nServe.");
    expect(isCustomized("Go in peace.", BENEDICTION)).toBe(true);
    expect(isCustomized(`  ${DEFAULT_PROMPTS.benediction}\r\n`, BENEDICTION)).toBe(false);
    expect(isCustomized("   ", BENEDICTION)).toBe(false);
  });

  it("sends only the church's own wording, cleaned; nothing changed is no change", () => {
    const baseline = promptValuesFrom(OUT);
    const current = {
      ...baseline,
      system: ` ${DEFAULT_PROMPTS.system}\r\n`,
      call_to_worship: "  Come, {occasion}.\r\nPraise.  ",
      assurance: "",
      benediction: "Go in peace. ",
    };
    expect(promptsPayload(current, FIELDS)).toEqual({ call_to_worship: "Come, {occasion}.\nPraise.", benediction: "Go in peace." });
    expect(hasPromptChanges(baseline, current, FIELDS)).toBe(true);
    expect(hasPromptChanges(baseline, { ...baseline, benediction: "Go in peace.\r\n", system: ` ${DEFAULT_PROMPTS.system}` }, FIELDS)).toBe(
      false,
    );
    expect(promptsPayload({ ...baseline, benediction: "" }, FIELDS)).toEqual({});
  });

  it("rebases on newer server wording: untouched cards take it, edited ones keep the edit", () => {
    const oldBaseline = promptValuesFrom(OUT);
    const current = { ...oldBaseline, system: "Our own voice.", benediction: "Go in peace. " };
    const next = promptValuesFrom(liturgyPrompts({ benediction: "Go and serve.", offertory_prayer: "Give thanks." }));
    expect(rebasePrompts(oldBaseline, current, next)).toEqual({
      ...next,
      system: "Our own voice.",
    });
  });

  it("finds a 422's messages for the cards, and nothing for a field the form has no card for", () => {
    const named = new ApiError(422, "prompt_invalid", "Benediction prompt: bad.", {
      fields: { "prompts.benediction": "Benediction prompt: bad." },
    });
    expect(promptFieldErrors(named, PROMPT_KEYS)).toEqual({ benediction: "Benediction prompt: bad." });
    const unknown = new ApiError(422, "invalid_request", "The request was not valid.", {
      fields: { "prompts.sermon.[key]": "Not a valid value." },
    });
    expect(promptFieldErrors(unknown, PROMPT_KEYS)).toBeNull();
    expect(promptFieldErrors(new ApiError(403, "forbidden", "Only church admins can do this."), PROMPT_KEYS)).toBeNull();
    expect(keys.liturgyPrompts("c-1")).toEqual(["church", "c-1", "liturgy-prompts"]);
  });
});
