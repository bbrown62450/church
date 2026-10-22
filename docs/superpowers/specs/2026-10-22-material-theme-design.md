# Material 3 theme, Theme PR 1: design

Status: design for Theme PR 1 (2026-10-22). Decisions: `docs/superpowers/specs/2026-10-22-material-theme-decisions.md` (binding). Plan: `docs/superpowers/plans/2026-10-22-theme-pr1.md`.

## Goals

The app stops wearing the component kit's stock look and wears the owner's chosen Material 3 theme (Option B: teal, Figtree), in light and dark, with no change to what any page does.

1. Material 3 color roles, generated from the seed `#006A60` with Google's Material Color Utilities, in light and in dark (dark follows the phone's setting).
2. Figtree for all text; Material 3 shapes (full-round buttons and chips, rounder fields, cards and dialogs) and elevation.
3. Buttons, cards, fields and dialogs restyled; the builder's steps and the Settings sections drawn as Material 3 chip rows (same links, same order, same targets); the Settings Save bar restyled with its behavior unchanged.
4. A simple teal app icon, a white "W" in Figtree (owner, 2026-10-22): favicon, Apple touch icon and web manifest icons. The home-screen icon opens the app in the browser, as today.
5. Every text and background pair the components draw reaches WCAG AA in both modes, checked by a test.

## Scope

In: tokens (light and dark), Figtree, shapes, elevation, buttons, cards, fields, dialogs, chips (builder steps, Settings sections, the main nav's current item), the Save bar (Liturgy, Prayers and Rubric settings pages) and the builder's step footer, warning text, dark mode, the printed cover preview kept light, the icon, the manifest and the browser bar color.

Out (Theme PR 2 or later): the bottom navigation bar, motion (dialogs, panels, step changes), season colors, a light/dark toggle, any new component library, the Streamlit app, the backend, the Word and PDF documents.

## How the colors are made

- `frontend/scripts/generate-theme.mjs` builds a `SchemeTonalSpot` (Material's default scheme, standard contrast) from the seed, maps each Material role to the shadcn variable the components already use (table below), and writes one marked block into `frontend/src/app/globals.css` (`/* theme:start ... */` to `/* theme:end */`): light on `:root`, dark under `@media (prefers-color-scheme: dark)`, and the light values again on `.paper`. The values are committed as plain hex, so the page loads no color library.
- **One devDependency, pinned: `@material/material-color-utilities` `0.3.0`** (Apache-2.0, no dependencies of its own). It is needed by the script and by `tokens.test.ts`, which regenerates the block and fails if the committed CSS differs, so a hand edit or a stale block cannot ship. `0.4.0` (the newest) is not used: its files import each other without the `.js` extension, which plain Node refuses. The lockfile entry is added by a directive and checked with `npm ci`, because this machine's npm rewrites unrelated lines of the lockfile.
- Warning text (three places use it) gets its own token: amber `#B45309` harmonized toward the seed (Material's custom-color recipe), tone 40 in light and 80 in dark.
- The generated values match the owner's drawn preview closely: primary `#006a60`, primary container `#9ef2e4` (drawn `#9FF2E2`), secondary container `#cce8e2`, surface `#f4fbf8`, on-surface `#161d1c`, on-surface-variant `#3f4947`, outline `#6f7977`, outline variant `#bec9c6`. Two differ: the text on containers is tone 30 (`#005048`) where the drawing used tone 10 (`#00201C`), and the generated tertiary is a blue (`#466179`, container `#cce5ff`) where the drawing showed a peach (`#FFDCC3`). Theme PR 1 uses no tertiary color, so nothing on screen shows the difference.

### Token mapping

| shadcn variable | Material 3 role | Light | Dark |
|---|---|---|---|
| `--background` | surface | #f4fbf8 | #0e1513 |
| `--foreground` | on surface | #161d1c | #dde4e1 |
| `--card` | surface container low | #eff5f2 | #161d1c |
| `--card-foreground` | on surface | #161d1c | #dde4e1 |
| `--popover` (menus, dialogs, toasts) | surface container | #e9efed | #1a2120 |
| `--popover-foreground` | on surface | #161d1c | #dde4e1 |
| `--primary` | primary | #006a60 | #82d5c8 |
| `--primary-foreground` | on primary | #ffffff | #003732 |
| `--primary-container` (new) | primary container | #9ef2e4 | #005048 |
| `--primary-container-foreground` (new) | on primary container | #005048 | #9ef2e4 |
| `--secondary` (tonal buttons, selected chips) | secondary container | #cce8e2 | #334b47 |
| `--secondary-foreground` | on secondary container | #334b47 | #cce8e2 |
| `--muted` | surface container high | #e3eae7 | #252b2a |
| `--muted-foreground` | on surface variant | #3f4947 | #bec9c6 |
| `--accent` (menu item highlight) | surface container highest | #dde4e1 | #303635 |
| `--accent-foreground` | on surface | #161d1c | #dde4e1 |
| `--destructive` | error | #ba1a1a | #ffb4ab |
| `--border` | outline variant | #bec9c6 | #3f4947 |
| `--input` (field and outlined button edges) | outline | #6f7977 | #899390 |
| `--ring` | primary | #006a60 | #82d5c8 |
| `--surface-container` (new; Save bar, step footer) | surface container | #e9efed | #1a2120 |
| `--warning` (new) | harmonized amber, tone 40 / 80 | #8c5000 | #ffb874 |

The `--chart-*` and `--sidebar-*` variables (unused today) are mapped to matching roles so a kit component added later is not grey.

## Type

Figtree through `next/font/google` as `--font-sans` (replacing Geist; `next/font` self-hosts it, so the page fetches nothing from Google). Geist Mono stays for the two invite-link fields. The existing Tailwind steps already sit on the Material 3 scale and are kept: `text-sm` 14/20 body medium, `text-base` 16/24 body large and title medium, `text-lg` 18/28 and `text-xl` 20/28 for page and step titles (title large), `text-xs` 12/16 label small.

## Shape and elevation

- Radius steps (fixed values, not multiples): `sm` 8 px, `md` 10, `lg` 12 (fields, menus, fieldsets: Material medium), `xl` 16 (cards: large), `2xl` 28 (dialogs and the phone's bottom-sheet dialogs: extra large); buttons, chips and the main nav are full round.
- Tailwind's `shadow-xs` to `shadow-xl` become Material elevation levels 1 to 4. Cards sit at level 1 on their own surface tone (no outline ring); dialogs at level 3. In dark mode shadows barely show, so the surface tones carry the depth, as Material intends.

## Components

- **Button**: full round. Default: filled primary, lighter with level 1 on hover. Secondary: tonal (secondary container). Outline: transparent, `--input` edge, primary label. Ghost: an 8% on-surface state layer on hover. Destructive and link keep their shapes with the new colors. Sizes (`touch` 44 px and the rest) unchanged.
- **Card**: `rounded-xl` (16 px), level 1 shadow, surface container low.
- **Dialog and alert dialog**: 28 px corners, level 3, footers rounded to match.
- **Input and textarea**: the outline edge; the dark-only grey fill dropped (Material outlined fields are clear).
- **Chips**: Settings sections are outlined chips (44 px tall on phones, 36 from `md`); the current section is filled with the secondary container. From `md` the column keeps its place beside the page, with clear edges (a navigation-drawer look). The builder's five steps become chips in the same grid: below `lg` each shows its number (and a check when done) under the existing "Step 1 of 5" line; from `lg` the number and label, with the status under the chip. Each link's text and name stay "{n} {label} {status}". The main nav's current item uses the same filled look.
- **Save bar** (Liturgy prompts, Prayers, Rubric settings): the surface container color, 16 px top corners, side padding; still sticky, still static while a field has focus, same buttons. The builder's step footer takes the same color.
- **Warnings**: the three amber lines use `text-warning`.
- **Toasts**: sonner already reads `--popover`, `--border` and `--radius`; `richColors` keeps sonner's own success and error colors; with no theme provider it follows the system setting.

## Dark mode

- `@custom-variant dark` becomes `@media (prefers-color-scheme: dark)`, excluding anything inside `.paper`. Before this PR the kit's `dark:` classes keyed on a `.dark` class that nothing set, so they never applied; from now they apply when the phone is dark. No toggle.
- `:root` declares `color-scheme: light dark` so native controls and scrollbars follow; the viewport's `theme-color` is the surface color of each mode.
- **What stays light**: the app has no rendered bulletin page (the Word and PDF files are downloads). The one thing on screen that stands for paper is the cover picture preview on the Bulletin step (the picture with its printed band), which gets `class="paper"`: it re-declares the light tokens and `color-scheme: light`, and the dark variant skips it. `.paper` also paints its own light surface (`background-color: var(--background)`, which inside `.paper` is the light surface), so a cover picture with transparent parts sits on light paper in dark mode, not on the dark page. Any later paper-like view uses the same class.

## The icon

A white "W" in Figtree on the seed teal (owner, 2026-10-22), in `frontend/scripts/generate-icons.mjs` as SVG geometry. The W is Figtree's own glyph at weight 700, converted once, while planning, from the Figtree file that `next/font` fetched, to one SVG path (fontTools; Figtree's W is all straight lines, so the path is 13 points) and placed 216 px tall in the middle of a 512 px box. Nothing fetches or reads a font when the icons are generated or tested. The script writes `src/app/icon.svg` (rounded square, the SVG favicon), `src/app/favicon.ico` (16, 32 and 48 px PNGs inside an ICO, replacing Next's default), `src/app/apple-icon.png` (180 px, full bleed; iOS rounds it) and `public/icons/icon-192.png`, `icon-512.png` and `icon-maskable-512.png` (full bleed; the W sits inside the maskable safe circle). It renders with `sharp`, which is already installed with Next.js, so there is no network and no new package. `src/app/manifest.ts` names the app "Worship Service Builder" (short "Worship"), starts at `/builder`, theme color primary, background surface, and `display: "browser"`: the home-screen icon opens the app in the browser, as today (owner, 2026-10-22). The layout sets no `appleWebApp` metadata, so the page carries no `apple-mobile-web-app-capable` or `mobile-web-app-capable` tag; a test checks the source and the build is checked for the tags.

The sign-in proxy's matcher already skips `.svg`, `.png` and `favicon.ico`; it now also skips `manifest.webmanifest`, which browsers fetch without the session cookie and which would otherwise be redirected to `/login`.

## Accessibility

- `tokens.test.ts` computes WCAG contrast for every text pair the components draw (foreground, muted foreground, primary, destructive and warning on background, card, popover, muted and surface container; each "on" color on its container; the destructive button's text on its 10% (light) or 20% (dark) tint), at least 4.5:1 in both modes, and field edges and focus rings at least 3:1. Focus rings are drawn at full strength (`ring-ring`, the destructive button's `ring-destructive`), not at the kit's 50%: a half-strength teal ring reaches only about 2.2:1 in light mode. `colors.test.ts` fails on any faded focus ring in a component.
- Results (light / dark): the lowest text pair is 5.27 / 7.24 (warning on muted; secondary chip text on its container); foreground on background 16.31 / 14.32; on-primary on primary 6.50 / 7.72; primary on background 6.19 / 10.83; muted foreground on muted 7.62 / 8.48; field edges at least 3.68 / 4.56.
- Unselected chips have a light outline-variant edge (below 3:1, as in Material 3); their label text identifies them and meets 4.5:1, so the edge is decoration, not the control's only boundary.
- Tap targets stay 44 px on phones (the existing class tests still pass; new tests pin each builder step link at `min-h-11` with its chip at `h-11`, and the Settings chips at `h-11`).
- Every builder step chip shows its number at every width, nothing in a chip is faded with opacity, and the current step is filled while the others are outlined (tests).

## Testing

New: `src/lib/theme/tokens.test.ts` (the committed block equals the generator's output, paper equals light, contrast in both modes, the dark variant skips `.paper`), `colors.test.ts` (no fixed palette color in `src/components` or `src/app` outside an allow-list of the three dialog scrims and the printed cover band; no arbitrary color class such as `bg-[#ffffff]` and no color in an inline `style`; no faded focus ring; Figtree), `icons.test.ts` (the icon files exist at their sizes, the manifest's icons, colors and `browser` display, no Apple web-app metadata, the browser bar colors, the matcher). Added to existing files: the builder step chips (`builder-shell.test.tsx`: 44 px, number shown, nothing faded, focus ring, current filled), the Settings chips (`settings-layout.test.tsx`), the button's focus ring (`button.test.tsx`). Changed: the cover preview carries `paper` (`bulletin-step.test.tsx`); the outline button is recognized by `border-input` (`review-send-step.test.tsx`). Plus a visual check of the real pages, signed in through a fake sign-in and a fake API built from the test fixtures: sign-in, the five builder steps, Services and Settings (Church, Liturgy, Prayers, People) at 375 px, light and dark, with the pre-installed Chromium (screenshots to the scratchpad only), and a short phone check after the deploy.

## Risks

- **A color the eye dislikes in dark mode** that the tests cannot judge (for example the kit's dark-only field tints on selects and switches, kept as the kit drew them). The visual check and the phone check look; a fix is a small follow-up.
- **The build fetches Figtree from Google Fonts**, as it fetched Geist; a Google outage during a Vercel build fails that build, not the live site.
- **Lockfile drift**: if a later `npm install` rewrites the lockfile's unrelated `libc` lines, that is the newer npm's format, not this PR's.
- **Safari before version 26 ignores SVG favicons**; it takes `favicon.ico`.
- **Shapes change the feel of every page at once.** Nothing moves or changes size (the class tests on 44 px targets still pass), but corners and colors do; Theme PR 2 adds motion on top.

## Answered questions

1. **The icon's mark** (owner, 2026-10-22): a "W" in Figtree on the teal, not a cross; made offline.
2. **What the home-screen icon opens** (owner, 2026-10-22): the app in the browser, as today (manifest `display: "browser"`, no web-app meta).

## Follow-ups (not Theme PR 1)

- **Dark mode's grey-filled menus and comboboxes**: the kit's dark-only fills on selects, comboboxes and their menus read as flat grey next to the teal surfaces. Kept as the kit drew them in this PR; a small follow-up restyles them.
- **Em dashes in existing user-facing copy**, to be fixed in the em-dash follow-up PR together with the plan reviewer's two strings: for example "Off — not in the service. Any text is kept." (a liturgy section switched off), "Off by default — it's on by default only on the first Sunday of the month." (communion), "Still working — this can take up to a minute.", "Too many requests — try again in … s." and the Still to do lines ("… is empty — Write or generate it"). About a dozen strings in all (`grep -rn "—" frontend/src/components frontend/src/app`). This PR adds no new one.
