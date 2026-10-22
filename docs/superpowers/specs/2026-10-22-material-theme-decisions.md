# Material 3 theme: owner decisions

Status: decisions only (owner, 2026-10-22). The design spec and plan follow.

The app still wears the component kit's stock look (shadcn's near-black
primary, grey accents, Geist, small corners), which the owner finds generic.
The owner likes Material Design and wants it "a little bit more dazzling".

## Planning answers (2026-10-22, "all recommended"; binding)

1. Material 3 styling on the current components (Tailwind and the shadcn/Base UI kit stay); no switch to a Material component library.
2. One fixed seed color for the app (liturgical-season colors may come later).
3. Moderate dazzle: color, shape, type, depth and gentle motion on dialogs, panels and step changes, at phone speed.
4. A preview first: the owner compared three themes on a canvas and chose **Option B: teal, Figtree** (seed around `#006A60`; light roles as drawn: primary `#006A60`, on-primary `#FFFFFF`, primary container `#9FF2E2` / `#00201C`, secondary container `#CCE8E2` / `#051F1C`, tertiary container `#FFDCC3` / `#2F1500`, surface `#F4FBF8`, surface container `#E9EFEC`, on-surface `#161D1B`, on-surface-variant `#3F4946`, outline `#6F7976`, outline variant `#BEC9C5`). The build generates the real tonal palettes from the seed with Google's Material Color Utilities; the drawn values were hand-picked approximations.

## Follow-up answers (2026-10-22; binding)

1. A bottom navigation bar (Builder, Services, Settings) on phones; the header links stay on wider screens.
2. Keep the Settings Save bar and its tested behavior, restyled in Material 3 (no floating Save button).
3. The builder steps and the Settings sections become Material 3 chip rows (a restyle of today's links, same navigation).
4. **Dark mode now** (owner, overriding the recommendation to wait): it follows the phone's setting; Material 3 dark roles from the same seed. The printed bulletin preview and anything that stands for paper stay light.
5. **A simple teal app icon now** (owner, overriding the recommendation to wait): favicon, Apple touch icon and web manifest icons.
6. Two PRs: **Theme PR 1**: the Material 3 tokens (light and dark), Figtree, shapes, buttons, cards, chips, the restyled Save bar, dark mode and the icon, with no behavior change. **Theme PR 2**: the bottom navigation bar and gentle motion.

The preview canvas is private to the owner (claude.ai artifact "Worship app Material 3 themes").
