// The app icon (Theme PR 1): a white "W" in Figtree on the theme's teal
// (owner, 2026-10-22). Writes the SVG favicon, favicon.ico, the Apple touch
// icon and the web manifest's icons, all from the geometry below, with sharp
// (installed with Next.js). No network and no font file at run time: the W
// below is Figtree's own glyph at weight 700, converted once to an SVG path
// (fontTools, from the Figtree file next/font fetched while planning) and
// placed 216 px tall in the middle of the 512 px box, inside the maskable safe
// circle. Run `node scripts/generate-icons.mjs` after changing it and commit
// the files it writes.
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import sharp from "sharp";

const TEAL = "#006A60"; // the seed, the light primary
const W = '<path fill="#FFFFFF" d="M170.5 364 106.6 148H149.5L193.1 299.1L235 148H277L318.9 297.1L362.5 148H405.4L340.9 364H296.7L256 214.2L214.7 364Z"/>';

/** `rounded`: the favicon and the manifest's "any" icons; full bleed for the Apple and maskable icons (the system rounds them). */
export function iconSvg(rounded) {
  const rx = rounded ? ' rx="112"' : "";
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512"${rx} fill="${TEAL}"/>${W}</svg>\n`;
}

const at = (path) => fileURLToPath(new URL(`../${path}`, import.meta.url));
const png = (svg, size) => sharp(Buffer.from(svg)).resize(size, size).png().toBuffer();

/** An .ico holding PNG images (every current browser reads these). */
function ico(images) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0);
  header.writeUInt16LE(1, 2);
  header.writeUInt16LE(images.length, 4);
  let offset = 6 + 16 * images.length;
  const entries = images.map(({ size, data }) => {
    const e = Buffer.alloc(16);
    e.writeUInt8(size % 256, 0);
    e.writeUInt8(size % 256, 1);
    e.writeUInt16LE(1, 4);
    e.writeUInt16LE(32, 6);
    e.writeUInt32LE(data.length, 8);
    e.writeUInt32LE(offset, 12);
    offset += data.length;
    return e;
  });
  return Buffer.concat([header, ...entries, ...images.map((i) => i.data)]);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const rounded = iconSvg(true);
  const full = iconSvg(false);
  writeFileSync(at("src/app/icon.svg"), rounded);
  writeFileSync(at("src/app/favicon.ico"), ico(await Promise.all([16, 32, 48].map(async (size) => ({ size, data: await png(rounded, size) })))));
  writeFileSync(at("src/app/apple-icon.png"), await png(full, 180));
  writeFileSync(at("public/icons/icon-192.png"), await png(rounded, 192));
  writeFileSync(at("public/icons/icon-512.png"), await png(rounded, 512));
  writeFileSync(at("public/icons/icon-maskable-512.png"), await png(full, 512));
  console.log("icons written: icon.svg, favicon.ico, apple-icon.png, icons/icon-192.png, icons/icon-512.png, icons/icon-maskable-512.png");
}
