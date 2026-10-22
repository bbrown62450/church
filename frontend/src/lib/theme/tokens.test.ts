// Theme PR 1: the committed Material 3 tokens, their contrast in both modes, and the paper scope.
import { describe, expect, it } from "vitest";

import { committedTokens, contrast, over, read, themeBlock } from "@/test/theme";

import { SEED, themeCss, themeTokens } from "../../../scripts/generate-theme.mjs";

const MODES = committedTokens();
const SURFACES = ["background", "card", "popover", "muted", "surface-container"];
/** [text, background] pairs the components draw; each needs 4.5:1 (WCAG AA, normal text). */
const TEXT_PAIRS: [string, string][] = [
  ...SURFACES.flatMap((s) => [["foreground", s], ["muted-foreground", s], ["primary", s], ["destructive", s], ["warning", s]] as [string, string][]),
  ["accent-foreground", "accent"],
  ["primary-foreground", "primary"],
  ["secondary-foreground", "secondary"],
  ["primary-container-foreground", "primary-container"],
];
/** Field and outlined-button edges and focus rings (drawn at full strength; colors.test.ts bans a faded ring): 3:1 (WCAG 1.4.11). */
const EDGE_PAIRS: [string, string][] = SURFACES.flatMap((s) => [["input", s], ["ring", s]] as [string, string][]);

const below = (mode: "light" | "dark", pairs: [string, string][], min: number) =>
  pairs
    .map(([fg, bg]) => ({ pair: `${fg} on ${bg}`, ratio: contrast(MODES[mode][fg], MODES[mode][bg]) }))
    .filter((r) => !(r.ratio >= min));

describe("the Material 3 tokens (Theme PR 1)", () => {
  it("are what scripts/generate-theme.mjs makes from the seed (run it with --write after a change)", () => {
    expect(SEED).toBe("#006A60");
    expect(themeBlock()).toBe(themeCss());
    expect(MODES.light).toEqual(themeTokens(false));
    expect(MODES.dark).toEqual(themeTokens(true));
  });

  it("hold every token in light, dark and paper, with paper equal to light", () => {
    expect(Object.keys(MODES.light).length).toBeGreaterThan(30);
    expect(Object.keys(MODES.dark)).toEqual(Object.keys(MODES.light));
    expect(MODES.paper).toEqual(MODES.light);
    expect(MODES.dark.background).not.toBe(MODES.light.background);
  });

  it.each(["light", "dark"] as const)("reach WCAG AA (4.5:1) for every text pair in %s", (mode) => {
    expect(below(mode, TEXT_PAIRS, 4.5)).toEqual([]);
  });

  it.each(["light", "dark"] as const)("reach 3:1 for field edges and focus rings in %s", (mode) => {
    expect(below(mode, EDGE_PAIRS, 3)).toEqual([]);
  });

  it.each([
    ["light", 0.1],
    ["dark", 0.2],
  ] as const)("keep the destructive button's text readable on its tint in %s", (mode, alpha) => {
    const t = MODES[mode];
    expect(contrast(t.destructive, over(t.destructive, alpha, t.background))).toBeGreaterThanOrEqual(4.5);
    expect(contrast(t.destructive, over(t.destructive, alpha, t.popover))).toBeGreaterThanOrEqual(4.5);
  });

  it("follow the phone's setting, and nothing inside .paper turns dark", () => {
    const css = read("src/app/globals.css");
    expect(css).toMatch(/@custom-variant dark \{\s*@media \(prefers-color-scheme: dark\) \{\s*&:not\(\.paper, \.paper \*\) \{\s*@slot;/);
    expect(css).not.toContain(".dark {");
    expect(css).toMatch(/:root \{\s*--radius: 0\.75rem;\s*color-scheme: light dark;/);
    expect(css).toMatch(/\.paper \{\s*color-scheme: light;/);
  });

  it("give .paper its own light surface, so a transparent cover picture sits on light paper in dark mode", () => {
    const css = read("src/app/globals.css");
    expect(css).toMatch(/\.paper \{\s*color-scheme: light;\s*color: var\(--foreground\);\s*background-color: var\(--background\);\s*\}/);
    expect(MODES.paper.background).toBe(MODES.light.background); // var(--background) inside .paper is the light surface
  });
});
