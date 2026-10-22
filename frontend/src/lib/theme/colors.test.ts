// Theme PR 1: the components draw with the tokens, in Figtree.
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { FRONTEND, read } from "@/test/theme";

/** Fixed colors that stay: the dialog scrims (Material's scrim is black) and the printed cover's band over a photo. */
const ALLOWED = new Map([
  ["src/components/ui/dialog.tsx", ["bg-black/10"]],
  ["src/components/ui/alert-dialog.tsx", ["bg-black/10"]],
  ["src/components/ui/sheet.tsx", ["bg-black/10"]],
  ["src/components/builder/bulletin/bulletin-step.tsx", ["bg-black/55", "text-white"]],
]);
const PALETTE =
  /\b(?:bg|text|border|ring|fill|stroke|from|to|via|divide|outline|shadow|decoration|placeholder|caret|accent)-(?:white|black|(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\d{2,3})(?:\/\d+)?\b/g;
/** An arbitrary color in a class, such as `bg-[#ffffff]/95`, `text-[rgb(0,0,0)]` or `border-[oklch(0.5_0_0)]`. */
const ARBITRARY = /[\w:-]+-\[[^\]\s]*(?:#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\(|oklch\(|oklab\(|lab\(|lch\()[^\]\s]*\](?:\/\d+)?/g;
/** A color property in an inline style, or a literal color value there; a `var(--token)` value is fine. */
const STYLE_COLOR = /\b(?:color|background|backgroundColor|backgroundImage|borderColor|outlineColor|fill|stroke)\s*:|#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab)\(/g;
/** A focus ring drawn faded (`ring-ring/50` reaches only about 2.2:1 in light mode); rings are drawn at full strength. */
const FADED_RING = /\bring-ring\/\d+|\bfocus-visible:ring-[\w-]+\/\d+/g;
/** Text drawn faded (`text-foreground/60` on the muted surface is about 4.2:1); text uses a token at full strength, `muted-foreground` for quiet text. */
const FADED_TEXT = /\btext-[\w-]+\/\d+/g;

function sources(dir: string): string[] {
  return readdirSync(join(FRONTEND, dir)).flatMap((name) => {
    const path = `${dir}/${name}`;
    if (statSync(join(FRONTEND, path)).isDirectory()) return sources(path);
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}
const FILES = ["src/components", "src/app"].flatMap(sources);

/** Each `style={...}` attribute's expression, braces balanced. */
function styles(text: string): string[] {
  return [...text.matchAll(/\bstyle=\{/g)].map((m) => {
    let depth = 1;
    let i = m.index + m[0].length;
    for (; depth > 0 && i < text.length; i++) {
      if (text[i] === "{") depth++;
      else if (text[i] === "}") depth--;
    }
    return text.slice(m.index, i);
  });
}

const hits = (pattern: RegExp, of: (text: string) => string[] = (t) => [t]) =>
  FILES.flatMap((path) => of(read(path)).flatMap((part) => [...part.matchAll(pattern)].map((m) => `${path}: ${m[0]}`)));

describe("colors and type (Theme PR 1)", () => {
  it("leave no fixed palette color in a component or page outside the allow-list", () => {
    const found = FILES.flatMap((path) =>
      [...read(path).matchAll(PALETTE)]
        .map((m) => m[0])
        .filter((c) => !(ALLOWED.get(path) ?? []).includes(c))
        .map((c) => `${path}: ${c}`),
    );
    expect(found).toEqual([]);
  });

  it("leave no arbitrary color class and no inline color style in a component or page", () => {
    expect(hits(ARBITRARY)).toEqual([]);
    expect(hits(STYLE_COLOR, styles)).toEqual([]);
    expect(styles('<div style={{ minHeight: "2lh" }} /> <p style={{ background: "#fff" }} />')).toEqual([
      'style={{ minHeight: "2lh" }}',
      'style={{ background: "#fff" }}',
    ]); // the scanner itself
  });

  it("draw every focus ring at full strength", () => {
    expect(hits(FADED_RING)).toEqual([]);
  });

  it("draw all text at full strength, so its contrast is the tokens' (checked in tokens.test.ts)", () => {
    expect(hits(FADED_TEXT)).toEqual([]);
    expect("hover:text-foreground/80 *:data-[slot=x]:text-destructive/90 text-sm/6".match(FADED_TEXT)).toEqual([
      "text-foreground/80",
      "text-destructive/90",
      "text-sm/6",
    ]); // the pattern itself (a line height such as text-sm/6 is not used either)
  });

  it("set the app in Figtree", () => {
    const layout = read("src/app/layout.tsx");
    expect(layout).toContain('Figtree({ variable: "--font-sans", subsets: ["latin"] })');
    expect(layout).not.toMatch(/\bGeist\(/);
  });
});
