// Test helpers for Theme PR 1: the committed color tokens as globals.css holds them, and WCAG contrast.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

/** The frontend directory. */
export const FRONTEND = fileURLToPath(new URL("../../", import.meta.url));
export const read = (path: string) => readFileSync(join(FRONTEND, path), "utf8");

export type Tokens = Record<string, string>;

const tokensOf = (section: string): Tokens =>
  Object.fromEntries([...section.matchAll(/--([\w-]+): (#[0-9a-f]{6});/g)].map((m) => [m[1], m[2]]));

/** The generated block of globals.css, from `/* theme:start` to `/* theme:end *\/`. */
export function themeBlock(): string {
  const css = read("src/app/globals.css");
  const end = "/* theme:end */";
  return css.slice(css.indexOf("/* theme:start"), css.indexOf(end) + end.length);
}

/** The committed tokens: light (:root), dark (on screen under prefers-color-scheme: dark) and paper (.paper). */
export function committedTokens(): Record<"light" | "dark" | "paper", Tokens> {
  const block = themeBlock();
  const darkAt = block.indexOf("@media screen and (prefers-color-scheme: dark)");
  const paperAt = block.indexOf(".paper {");
  return {
    light: tokensOf(block.slice(0, darkAt)),
    dark: tokensOf(block.slice(darkAt, paperAt)),
    paper: tokensOf(block.slice(paperAt)),
  };
}

function rgb(hex: string): number[] {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** `top` at `alpha` over `bottom`, as the browser paints a Tailwind `/10` color. */
export function over(top: string, alpha: number, bottom: string): string {
  const [a, b] = [rgb(top), rgb(bottom)];
  return "#" + a.map((c, i) => Math.round(c * alpha + b[i] * (1 - alpha)).toString(16).padStart(2, "0")).join("");
}

function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map((c) => {
    const s = c / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** The WCAG 2 contrast ratio of two `#rrggbb` colors. */
export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
