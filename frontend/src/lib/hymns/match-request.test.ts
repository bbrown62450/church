import { describe, expect, it } from "vitest";

import { buildMatchRefs, cleanRefs, clipChars } from "./match-request";

describe("cleanRefs and buildMatchRefs (S buildMatchRefs)", () => {
  it("trims, drops blanks, cuts each line to 200 and keeps at most the first max", () => {
    expect(cleanRefs(["  Mark 1:9-15 ", "", "   ", "Psalm 25"], { max: 20, maxLen: 200 })).toEqual(["Mark 1:9-15", "Psalm 25"]);
    const long = "Isaiah 40:1-11 " + "x".repeat(485);
    expect(cleanRefs([long], { max: 20, maxLen: 200 })[0]).toHaveLength(200);
    const many = Array.from({ length: 25 }, (_, i) => `Psalm ${i + 1}`);
    expect(cleanRefs(many, { max: 20, maxLen: 200 })).toHaveLength(20);
  });

  it("puts the extra reference last, keeps it with 25 readings, and never sends it twice", () => {
    const many = Array.from({ length: 25 }, (_, i) => `Psalm ${i + 1}`);
    const refs = buildMatchRefs(many, "  Matthew 17 ");
    expect(refs).toHaveLength(20);
    expect(refs.at(-1)).toBe("Matthew 17");
    expect(refs[18]).toBe("Psalm 19");
    expect(buildMatchRefs(["Mark 1:9-15", "Psalm 25"], "Psalm 25")).toEqual(["Mark 1:9-15", "Psalm 25"]);
    expect(buildMatchRefs(["Mark 1:9-15"], "   ")).toEqual(["Mark 1:9-15"]);
    expect(buildMatchRefs([], "x".repeat(500))).toEqual(["x".repeat(200)]);
  });

  it("cuts by characters as the server counts them, never splitting an emoji", () => {
    const hearts = "💜".repeat(250); // 500 UTF-16 units, 250 characters
    const [cut] = cleanRefs([hearts], { max: 20, maxLen: 200 });
    expect(Array.from(cut)).toHaveLength(200);
    expect(cut).toBe("💜".repeat(200));
    expect(clipChars("Psalm 23 💜", 10)).toBe("Psalm 23 💜");
    expect(clipChars("a💜b", 2)).toBe("a💜");
  });
});
