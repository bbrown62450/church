// Theme PR 1: the teal app icon, the web manifest and the browser bar's colors.
import { readFileSync } from "node:fs";
import { join } from "node:path";

import * as staticInfo from "next/dist/build/analysis/get-page-static-info";
import { describe, expect, it } from "vitest";

import manifest from "@/app/manifest";
import { config } from "@/proxy";
import { committedTokens, FRONTEND, read } from "@/test/theme";

const MODES = committedTokens();
/** Next.js's own matcher compiler: exported at run time, not in its types. */
const { getMiddlewareMatchers } = staticInfo as unknown as {
  getMiddlewareMatchers: (matcher: string[], nextConfig: object) => { regexp: string }[];
};

function png(path: string): { width: number; height: number } {
  const b = readFileSync(join(FRONTEND, path));
  expect(b.subarray(1, 4).toString("latin1")).toBe("PNG");
  return { width: b.readUInt32BE(16), height: b.readUInt32BE(20) };
}

describe("the app icon and manifest (Theme PR 1)", () => {
  it("has the SVG favicon, a three-size favicon.ico and the Apple touch icon", () => {
    expect(read("src/app/icon.svg")).toContain('fill="#006A60"');
    const ico = readFileSync(join(FRONTEND, "src/app/favicon.ico"));
    expect([ico.readUInt16LE(2), ico.readUInt16LE(4)]).toEqual([1, 3]);
    expect(png("src/app/apple-icon.png")).toEqual({ width: 180, height: 180 });
  });

  it("lists the home-screen icons, which exist at their stated sizes, in the theme's colors", () => {
    const m = manifest();
    expect(m).toMatchObject({ name: "Worship Service Builder", short_name: "Worship", display: "browser", start_url: "/builder" });
    expect(m.theme_color).toBe(MODES.light.primary);
    expect(m.background_color).toBe(MODES.light.background);
    for (const icon of m.icons ?? []) {
      const [w, h] = icon.sizes!.split("x").map(Number);
      expect(png(`public${icon.src}`)).toEqual({ width: w, height: h });
    }
    expect((m.icons ?? []).map((i) => i.purpose)).toEqual(["any", "any", "maskable"]);
    expect(JSON.stringify(m)).not.toContain(String.fromCharCode(0x2014)); // no em dash in the copy
  });

  it("opens from the home screen in the browser, as before: no web-app mode and no Apple web-app meta (owner, 2026-10-22)", () => {
    expect(manifest().display).toBe("browser");
    const layout = read("src/app/layout.tsx");
    expect(layout).not.toMatch(/appleWebApp|mobile-web-app-capable|apple-mobile-web-app/);
  });

  it("colors the browser bar with each mode's surface", () => {
    const layout = read("src/app/layout.tsx");
    expect(layout).toContain(`{ media: "(prefers-color-scheme: light)", color: "${MODES.light.background}" }`);
    expect(layout).toContain(`{ media: "(prefers-color-scheme: dark)", color: "${MODES.dark.background}" }`);
  });

  it("serves the manifest and icons without the sign-in redirect, and still guards the pages", () => {
    // The matcher as Next.js compiles it (its own path-to-regexp step and the .rsc and data-route suffixes).
    const [compiled] = getMiddlewareMatchers(config.matcher, {});
    const matcher = new RegExp(compiled.regexp);
    expect(matcher.test("/manifest.webmanifest")).toBe(false);
    // Only the manifest itself skips: the dot is literal and the name ends there.
    expect(matcher.test("/manifestxwebmanifest")).toBe(true);
    expect(matcher.test("/manifest.webmanifest/builder")).toBe(true);
    expect(matcher.test("/manifest.webmanifest.rsc")).toBe(true);
    expect(matcher.test("/icons/icon-192.png")).toBe(false);
    expect(matcher.test("/apple-icon.png")).toBe(false);
    expect(matcher.test("/builder")).toBe(true);
    expect(matcher.test("/settings/church")).toBe(true);
  });
});
