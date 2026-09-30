# Slice 4b: Liturgy Step Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** work in progress (written incrementally; the sections below are filled task by task).

**Goal:** Ship PR 4b of slice 4, the Liturgy step (step 3 of the Service Builder, `/builder/liturgy`), live, on top of 4a's `GET /liturgy/config`, `POST /liturgy/generate` and `default_benediction`.

### Task 1: Liturgy that prints is unsaved work; a card following the church default is not (owner answer 1; S "Draft store integration", Risks 4; F §4.6 "Unsaved changes"; clarifications 2, 3)

Owner answer 1 makes S exact: what "New service" asks about (`isDirty`, which is `!isPristine` until 5a saves drafts, then the fingerprint of `draftToServicePayload`) and what holds a passed default date back on load (`rollForward`, through `isPristine`) must count the card text, the section switches, communion, the sermon title and the custom elements, and never a Benediction still following the church default or any of the step's transient state (which never enters the draft). Checked on `4dfed3b`: `isPristine` already counts typed, AI and archived text, communion set by the user, a sermon title and any custom element, and treats `origin: "default"` as pristine; it does **not** count a switch (a card switched off, or the Prayers of the People switched on, looks pristine), and it counts whitespace-only text and a whitespace-only title as work although they print nothing. The fingerprint payload already holds every enabled card with text, the title, communion and the custom elements. So the code change is `isPristine`'s card and title conditions, plus one home for the default switches (`lib/liturgy/sections.ts`, pinned to the shared fixture, which `freshDraft` now reads). The fingerprint test passes before the change: it pins what 2b built, including S Risks item 4 (after a save, a Benediction following the default shows a changed default as unsaved) and that a switch on an empty card is not saved (switches are not archived; clarification 3).

**Files:**
- Create: `frontend/src/lib/liturgy/sections.ts` (`SECTION_LABELS`, `DEFAULT_ENABLED`)
- Modify: `frontend/src/lib/draft/schema.ts` (`freshDraft` reads `DEFAULT_ENABLED`), `frontend/src/lib/draft/status.ts` (`isPristine` and its comment)
- Test: `frontend/src/lib/liturgy/sections.test.ts` (new, 1), `frontend/src/lib/draft/status.test.ts` (+1), `frontend/src/lib/draft/fingerprint.test.ts` (+1), `frontend/src/lib/draft/store.test.ts` (+1)

**Interfaces:**
- Consumes: `SECTION_KEYS`, `freshDraft` (2b), `isPristine`, `isDirty`, `rollForward` (2b, 2c, 3b), `backend/tests/fixtures/shared/liturgy_sections.json` (4a).
- Produces: `SECTION_LABELS: Readonly<Record<SectionKey, string>>` and `DEFAULT_ENABLED: Readonly<Record<SectionKey, boolean>>`; `isPristine(draft)` is also false when a card's `enabled` differs from `DEFAULT_ENABLED`, and true for blank (after trimming) `empty` text and a blank title. Later users: T2 (`liturgyCounts`, `stillNeeded`'s labels), T6 (toast labels), T8-T11.

Counts after this task: frontend **446 passed in 65 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/lib/liturgy 2>&1 | tail -1
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `ls: cannot access 'frontend/src/lib/liturgy': No such file or directory`; ` Test Files  64 passed (64)`, `      Tests  442 passed (442)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/sections.test.ts`:**

```ts
/**
 * The TypeScript copy of the 8 sections (slice 4 spec, Testing `defaults.test.ts`
 * "fresh-draft card switches equal shared/liturgy_sections.json"): labels and
 * default switches equal the shared fixture that backend/liturgy_config.SECTIONS
 * also equals, and a fresh draft switches its cards on exactly as it says.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { SECTION_KEYS } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { DEFAULT_ENABLED, SECTION_LABELS } from "./sections";

type Fixture = { sections: { key: string; label: string; default_enabled: boolean }[] };

const fixture = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/liturgy_sections.json", import.meta.url), "utf-8"),
) as Fixture;

describe("liturgy sections (shared/liturgy_sections.json)", () => {
  it("has the fixture's keys, labels and default switches, and a fresh draft's cards follow them", () => {
    expect(fixture.sections.map((s) => s.key)).toEqual([...SECTION_KEYS]);
    expect(SECTION_KEYS.map((key) => SECTION_LABELS[key])).toEqual(fixture.sections.map((s) => s.label));
    expect(SECTION_KEYS.map((key) => DEFAULT_ENABLED[key])).toEqual(fixture.sections.map((s) => s.default_enabled));
    const cards = testDraft().liturgy.cards;
    expect(SECTION_KEYS.map((key) => cards[key].enabled)).toEqual(fixture.sections.map((s) => s.default_enabled));
  });
});
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts

describe("stillNeeded (S Review \"Still needed\")", () => {
```

**with:**

```ts

describe("isPristine and the liturgy step (owner answer 1, 2026-09-30)", () => {
  it("counts a switch moved from its default and text that prints, never a card following the church default", () => {
    // Everything that ends up in the service counts: text, the switches, communion, the title, custom elements.
    expect(isPristine(withCard("call_to_worship", { enabled: false }))).toBe(false);
    expect(isPristine(withCard("prayers_of_the_people", { enabled: true }))).toBe(false);
    expect(isPristine(withCard("benediction", { enabled: false }))).toBe(false);
    expect(isPristine(withCard("opening_prayer", { text: "Gracious God", origin: "typed" }))).toBe(false);
    // A Benediction still following the church default is not the user's work, whatever the default says.
    expect(isPristine(withCard("benediction", { text: "Go in peace.", origin: "default" }))).toBe(true);
    expect(isPristine(withCard("benediction", { text: "", origin: "default" }))).toBe(true);
    // Text that prints nothing is not work: blank typing, a blank title.
    expect(isPristine(withCard("assurance", { text: "  \n ", origin: "empty" }))).toBe(true);
    expect(isPristine(withLiturgy({ sermon_title: "   " }))).toBe(true);
    // A card switched off and back on again is as it was.
    expect(isPristine(withCard("call_to_worship", { enabled: true }))).toBe(true);
  });
});

describe("stillNeeded (S Review \"Still needed\")", () => {
```

**In `frontend/src/lib/draft/fingerprint.test.ts`, replace:**

```ts
  });
});
```

**with:**

```ts
  });

  it("after a save, liturgy that prints is unsaved; a switch on an empty card is not (owner answer 1, 2026-09-30)", () => {
    const base = testDraft((d) => ({
      ...d,
      liturgy: {
        ...d.liturgy,
        cards: {
          ...d.liturgy.cards,
          call_to_worship: { enabled: true, text: "Come, let us worship.", origin: "typed" },
          benediction: { enabled: true, text: "Halverson", origin: "default" },
        },
      },
    }));
    const saved: DraftV1 = { ...base, saved_fingerprint: fingerprint(draftToServicePayload(base)) };
    const liturgy = (patch: Partial<DraftV1["liturgy"]>): DraftV1 => ({ ...saved, liturgy: { ...saved.liturgy, ...patch } });
    const card = (key: "call_to_worship" | "opening_prayer" | "benediction", patch: object): DraftV1 =>
      liturgy({ cards: { ...saved.liturgy.cards, [key]: { ...saved.liturgy.cards[key], ...patch } } });
    expect(isDirty(saved)).toBe(false);
    expect(isDirty(card("call_to_worship", { text: "Come, let us worship God.", origin: "typed" }))).toBe(true);
    expect(isDirty(card("call_to_worship", { enabled: false }))).toBe(true); // its text leaves the service
    expect(isDirty(liturgy({ include_communion: !saved.liturgy.include_communion, communion_origin: "user" }))).toBe(true);
    expect(isDirty(liturgy({ sermon_title: "Living Water" }))).toBe(true);
    expect(isDirty(liturgy({ custom_elements: [{ id: "c1", label: "Anthem", text: "", insert_after: "sermon" }] }))).toBe(true);
    // Slice 4 Risks item 4: a Benediction following the church default shows the new default as unsaved.
    expect(isDirty(card("benediction", { text: "Go in peace." }))).toBe(true);
    // Switches are not saved (slice 4 BC-17), so switching an empty card prints nothing new.
    expect(isDirty(card("opening_prayer", { enabled: false }))).toBe(false);
  });
});
```

**In `frontend/src/lib/draft/store.test.ts`, replace:**

```ts

describe("DraftStore changes (S store.ts)", () => {
```

**with:**

```ts

describe("DraftStore roll-forward and the liturgy step (owner answer 1, 2026-09-30)", () => {
  it("keeps a passed default date when a card was switched, and rolls one whose Benediction follows the default", () => {
    const tenDaysLater = clock(new Date(DRAFT_NOW.getTime() + 10 * 86_400_000)); // Friday, October 9
    const card = (key: "prayers_of_the_people" | "benediction", patch: object) =>
      testDraft((d) => ({
        ...d,
        liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } },
      }));
    const load = (d: DraftV1) =>
      makeStore(memoryStorage({ [KEY]: JSON.stringify(d) }).storage, tenDaysLater.now).store.getSnapshot().draft;
    expect(load(card("prayers_of_the_people", { enabled: true })).readings.date_iso).toBe("2026-10-04");
    expect(load(card("benediction", { text: "Go in peace.", origin: "default" })).readings.date_iso).toBe("2026-10-11");
  });
});

describe("DraftStore changes (S store.ts)", () => {
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/sections.test.ts src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|Error: Cannot find|Tests ")
```

**Expected:**

```
 FAIL  |unit| src/lib/liturgy/sections.test.ts [ src/lib/liturgy/sections.test.ts ]
Error: Cannot find module './sections' imported from '<repo>/frontend/src/lib/liturgy/sections.test.ts'
 FAIL  |unit| src/lib/draft/status.test.ts > isPristine and the liturgy step (owner answer 1, 2026-09-30) > counts a switch moved from its default and text that prints, never a card following the church default
AssertionError: expected true to be false // Object.is equality
 FAIL  |unit| src/lib/draft/store.test.ts > DraftStore roll-forward and the liturgy step (owner answer 1, 2026-09-30) > keeps a passed default date when a card was switched, and rolls one whose Benediction follows the default
AssertionError: expected '2026-10-11' to be '2026-10-04' // Object.is equality
      Tests  2 failed | 27 passed (29)
```

(`<repo>` is the checkout's absolute path. The new fingerprint test passes already: it pins the payload 2b built.)

- [ ] **Step 4 (agent): Count the switches and printed text in `isPristine`**

**Create `frontend/src/lib/liturgy/sections.ts`:**

```ts
/**
 * The 8 liturgy sections as the draft and the pure status code need them
 * (slice 4 spec, Backend 1 `SECTIONS`; F §4.6 "Fresh draft"): each section's
 * label and whether a fresh draft switches it on. This is the one TypeScript
 * copy; `sections.test.ts` pins it to backend/tests/fixtures/shared/
 * liturgy_sections.json, which backend/liturgy_config.SECTIONS also equals.
 * The step reads the rest (rows, hints, the order of worship) from
 * GET /liturgy/config.
 */
import type { SectionKey } from "@/lib/draft/schema";

export const SECTION_LABELS: Readonly<Record<SectionKey, string>> = {
  call_to_worship: "Call to Worship",
  opening_prayer: "Opening Prayer",
  prayer_of_confession: "Prayer of Confession",
  assurance: "Assurance of Pardon",
  prayer_for_illumination: "Prayer for Illumination",
  prayers_of_the_people: "Prayers of the People",
  offertory_prayer: "Offertory Prayer",
  benediction: "Benediction",
};

/** Every section starts switched on except the Prayers of the People (app.py:890 parity). */
export const DEFAULT_ENABLED: Readonly<Record<SectionKey, boolean>> = {
  call_to_worship: true,
  opening_prayer: true,
  prayer_of_confession: true,
  assurance: true,
  prayer_for_illumination: true,
  prayers_of_the_people: false,
  offertory_prayer: true,
  benediction: true,
};
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";

```

**with:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";

```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
      { enabled: key !== "prayers_of_the_people", text: "", origin: key === "benediction" ? "default" : "empty" },
```

**with:**

```ts
      { enabled: DEFAULT_ENABLED[key], text: "", origin: key === "benediction" ? "default" : "empty" },
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { cleanLines } from "@/lib/scripture-refs";
```

**with:**

```ts
import { inSupportedRange, isValidDateIso } from "@/lib/dates";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
import { cleanLines } from "@/lib/scripture-refs";
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
 * 2026-09-29, slice 3b; the same fields the fingerprint payload holds).
```

**with:**

```ts
 * 2026-09-29, slice 3b; the same fields the fingerprint payload holds). On
 * the Liturgy step everything that ends up in the service counts: card text,
 * a card switched away from its default, communion the user set, the sermon
 * title and custom elements; a Benediction still following the church
 * default (origin "default") and text that prints nothing (blank after
 * trimming) do not (owner answer 1, 2026-09-30, slice 4b).
```

**In `frontend/src/lib/draft/status.ts`, replace:**

```ts
      return card.origin === "default" || (card.origin === "empty" && card.text === "");
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title === "" &&
```

**with:**

```ts
      const text = card.origin === "default" || (card.origin === "empty" && card.text.trim() === "");
      return card.enabled === DEFAULT_ENABLED[key] && text;
    }) &&
    l.communion_origin === "default" &&
    l.sermon_title.trim() === "" &&
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy/sections.test.ts src/lib/draft/status.test.ts src/lib/draft/fingerprint.test.ts src/lib/draft/store.test.ts 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  4 passed (4)`, `      Tests  30 passed (30)`; the suite ` Test Files  65 passed (65)`, `      Tests  446 passed (446)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M` for the five modified files and `??` for `frontend/src/lib/liturgy/`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/sections.ts frontend/src/lib/liturgy/sections.test.ts frontend/src/lib/draft/schema.ts frontend/src/lib/draft/status.ts frontend/src/lib/draft/status.test.ts frontend/src/lib/draft/fingerprint.test.ts frontend/src/lib/draft/store.test.ts
git commit -m "Draft: liturgy that prints is unsaved work; a card following the church default is not (owner answer 1)" -m "isPristine also counts a liturgy card switched away from its default
(SECTION_LABELS and DEFAULT_ENABLED in lib/liturgy/sections.ts, pinned to
shared/liturgy_sections.json, which freshDraft now reads), and no longer
counts blank text or a blank sermon title, which print nothing. A
Benediction following the church default still never counts. After a save
the fingerprint payload decides, as 2b built it (S Risks item 4 pinned).
Frontend 442 -> 446 tests in 64 -> 65 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

### Task 2: The cards' draft transitions, the liturgy defaults and the counts (S "Card origin transitions", Frontend `cards.ts`, `defaults.ts`, `summary.ts`; F §4.6; clarifications 4, 5, 6)

The pure half of the step. `cards.ts` holds every transition of S's origin table (typing, an AI result, Clear, "Use church default", Undo, the switch), the communion switch and "Use default", the sermon title, the custom elements (added trimmed, edited, removed and restored at their index, an unknown place read as "end"), the selectors "Generate empty sections" and Regenerate need, and the stale-result rule (`captureCard`, `staleVerdict`) that T6 applies and the service reviewer will reuse. `defaults.ts` keeps an untouched Benediction on the church default and untouched communion on the date's first-Sunday rule; the communion rule moves there from 2b's `date-effects.ts` (S: "that code moves into `applyLiturgyDefaults`, so there is one place for it"), which now calls it. `summary.ts` is the one count behind the step bar and the summary.

**Files:**
- Create: `frontend/src/lib/liturgy/cards.ts`, `frontend/src/lib/liturgy/defaults.ts`, `frontend/src/lib/liturgy/summary.ts`
- Modify: `frontend/src/lib/draft/date-effects.ts` (calls `applyCommunionDefault`)
- Test: `frontend/src/lib/liturgy/cards.test.ts` (new, 5), `frontend/src/lib/liturgy/defaults.test.ts` (new, 3), `frontend/src/lib/liturgy/summary.test.ts` (new, 1). 2c's `readings.test.ts` keeps pinning communion on a date change.

**Interfaces:**
- Consumes: `DraftV1`, `LiturgyCard`, `SECTION_KEYS` (2b), `isFirstSundayOfMonth` (2b `lib/dates.ts`), `setDate` (2c), `shared/first_sunday.json` and `shared/liturgy_outline.json` (4a).
- Produces:
  - `cards.ts`: `type CardOrigin`, `type CardSnapshot = {text, origin}`, `type CustomElement`, `PLACEMENT_KEYS` (the 17), `normalizePlacement(key)`, `editCardText(d, key, text)`, `setCardEnabled(d, key, enabled)`, `applyGenerated(d, key, text)`, `clearCard(d, key)`, `restoreChurchDefault(d, defaultText)` (S's `useChurchDefault`; clarification 5), `restoreCard(d, key, previous)`, `setSermonTitle(d, title)`, `setCommunion(d, include)`, `restoreCommunionDefault(d)`, `addCustomElement(d, {label, text, insert_after}, id)`, `updateCustomElement(d, id, patch)`, `removeCustomElement(d, id) → {draft, element, index} | null`, `restoreCustomElement(d, element, index)`, `sectionsNeedingAi(d)`, `needsRegenerateConfirm(card)`, `type CapturedCard = {createdAt, text, origin}`, `captureCard(d, key)`, `staleVerdict(d, key, captured) → "apply" | "service_changed" | "edited"`.
  - `defaults.ts`: `DEFAULT_BENEDICTION_FALLBACK = "Halverson"`, `type LiturgyDefaults = {defaultBenediction}`, `applyCommunionDefault(d)`, `applyLiturgyDefaults(d, defaults)`.
  - `summary.ts`: `type LiturgyCounts = {ready, enabled, communion, customCount}`, `liturgyCounts(d)`.
  - Later users: T5 (the store runs `applyLiturgyDefaults`), T6 (`captureCard`, `staleVerdict`, `applyGenerated`, `restoreCard`), T8-T10 (the step), T11 (`liturgyCounts`).

Counts after this task: frontend **455 passed in 68 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
ls frontend/src/lib/liturgy
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `sections.test.ts` and `sections.ts` (T1's files, one per line); ` Test Files  65 passed (65)`, `      Tests  446 passed (446)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/cards.test.ts`:**

```ts
/**
 * The Liturgy step's draft transitions (slice 4 spec, "Card origin
 * transitions", Frontend `cards.ts`; Testing `cards.test.ts`): every row of
 * the origin table, the selectors, the custom elements and the stale-result
 * rule the generation provider (and later the service reviewer) applies.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import type { DraftV1, SectionKey } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import {
  addCustomElement,
  applyGenerated,
  captureCard,
  clearCard,
  editCardText,
  needsRegenerateConfirm,
  normalizePlacement,
  PLACEMENT_KEYS,
  removeCustomElement,
  restoreCard,
  restoreChurchDefault,
  restoreCommunionDefault,
  restoreCustomElement,
  sectionsNeedingAi,
  setCardEnabled,
  setCommunion,
  setSermonTitle,
  staleVerdict,
  updateCustomElement,
} from "./cards";

type Outline = { outline: { anchors_after: string[] }[] };

const outline = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/liturgy_outline.json", import.meta.url), "utf-8"),
) as Outline;

function withCard(d: DraftV1, key: SectionKey, patch: Partial<DraftV1["liturgy"]["cards"]["benediction"]>): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: { ...d.liturgy.cards[key], ...patch } } } };
}

const card = (d: DraftV1, key: SectionKey) => d.liturgy.cards[key];

describe("card origin transitions (S Frontend changes)", () => {
  it("follows every row of the table, and returns the same draft when nothing changes", () => {
    const d = testDraft();
    // User edits: typed when non-blank after trimming, else empty.
    const typed = editCardText(d, "call_to_worship", "Come, let us worship.");
    expect(card(typed, "call_to_worship")).toEqual({ enabled: true, text: "Come, let us worship.", origin: "typed" });
    expect(card(editCardText(typed, "call_to_worship", "  \n"), "call_to_worship")).toEqual({
      enabled: true,
      text: "  \n",
      origin: "empty",
    });
    expect(editCardText(typed, "call_to_worship", "Come, let us worship.")).toBe(typed);
    // An AI result applied.
    const ai = applyGenerated(typed, "call_to_worship", "Leader: Come!");
    expect(card(ai, "call_to_worship")).toEqual({ enabled: true, text: "Leader: Come!", origin: "ai" });
    // Clear.
    const cleared = clearCard(ai, "call_to_worship");
    expect(card(cleared, "call_to_worship")).toEqual({ enabled: true, text: "", origin: "empty" });
    expect(clearCard(cleared, "call_to_worship")).toBe(cleared);
    // Use church default (Benediction).
    const edited = editCardText(d, "benediction", "Go in peace.");
    expect(card(restoreChurchDefault(edited, "Halverson"), "benediction")).toEqual({
      enabled: true,
      text: "Halverson",
      origin: "default",
    });
    // Undo: previous text and origin.
    expect(card(restoreCard(ai, "call_to_worship", { text: "Come, let us worship.", origin: "typed" }), "call_to_worship")).toEqual(
      card(typed, "call_to_worship"),
    );
    // Switch toggled: text and origin unchanged.
    const off = setCardEnabled(ai, "call_to_worship", false);
    expect(card(off, "call_to_worship")).toEqual({ enabled: false, text: "Leader: Come!", origin: "ai" });
    expect(setCardEnabled(off, "call_to_worship", false)).toBe(off);
  });

  it("sends only switched-on cards with no text to the AI, and confirms before replacing typed or saved text", () => {
    let d = testDraft();
    d = editCardText(d, "call_to_worship", "Come.");
    d = editCardText(d, "opening_prayer", "   ");
    d = setCardEnabled(d, "assurance", false);
    d = withCard(d, "benediction", { text: "Halverson", origin: "default" });
    expect(sectionsNeedingAi(d)).toEqual(["opening_prayer", "prayer_of_confession", "prayer_for_illumination", "offertory_prayer"]);
    expect(needsRegenerateConfirm({ enabled: true, text: "Come.", origin: "typed" })).toBe(true);
    expect(needsRegenerateConfirm({ enabled: true, text: "Saved words", origin: "archive" })).toBe(true);
    expect(needsRegenerateConfirm({ enabled: true, text: "Leader: Come!", origin: "ai" })).toBe(false);
    expect(needsRegenerateConfirm({ enabled: true, text: "Halverson", origin: "default" })).toBe(false);
    expect(needsRegenerateConfirm({ enabled: true, text: "  ", origin: "typed" })).toBe(false);
  });
});

describe("the stale-result rule (S Generate and Regenerate, step 6)", () => {
  it("drops a result for a replaced draft or an edited card, and applies it to a card still following the default", () => {
    const d = withCard(testDraft(), "benediction", { text: "Halverson", origin: "default" });
    const captured = captureCard(d, "benediction");
    expect(captured).toEqual({ createdAt: d.created_at, text: "Halverson", origin: "default" });
    expect(staleVerdict(d, "benediction", captured)).toBe("apply");
    expect(staleVerdict({ ...d, created_at: "2026-09-30T12:00:00.000Z" }, "benediction", captured)).toBe("service_changed");
    // The church default changed mid-run: the user asked to replace the default, so apply.
    expect(staleVerdict(withCard(d, "benediction", { text: "Go in peace." }), "benediction", captured)).toBe("apply");
    // Edited in another tab.
    expect(staleVerdict(editCardText(d, "benediction", "My blessing"), "benediction", captured)).toBe("edited");
    const typed = editCardText(d, "opening_prayer", "Gracious God");
    const before = captureCard(typed, "opening_prayer");
    expect(staleVerdict(editCardText(typed, "opening_prayer", "Gracious God, hear us"), "opening_prayer", before)).toBe("edited");
  });
});

describe("communion, the sermon title and custom elements (S Communion card, Custom elements)", () => {
  it("toggles communion as the user's and restores the default, and stores the sermon title as typed", () => {
    const d = testDraft(); // Sunday, October 4, 2026: a first Sunday
    const off = setCommunion(d, false);
    expect(off.liturgy).toMatchObject({ include_communion: false, communion_origin: "user" });
    expect(restoreCommunionDefault(off).liturgy).toMatchObject({ include_communion: true, communion_origin: "default" });
    expect(restoreCommunionDefault(d)).toBe(d);
    expect(setSermonTitle(d, "Living Water").liturgy.sermon_title).toBe("Living Water");
    expect(setSermonTitle(d, "")).toBe(d);
  });

  it("adds, edits, removes and restores custom elements at their index, and normalizes unknown places to end", () => {
    const placements = new Set(outline.outline.flatMap((item) => item.anchors_after));
    expect(new Set(PLACEMENT_KEYS)).toEqual(placements);
    expect(PLACEMENT_KEYS).toHaveLength(17);
    expect(normalizePlacement("sermon")).toBe("sermon");
    expect(normalizePlacement("bogus")).toBe("end");

    let d = testDraft();
    d = addCustomElement(d, { label: "  Children's Moment ", text: " Come forward. ", insert_after: "opening_prayer" }, "a");
    d = addCustomElement(d, { label: "Anthem", text: "", insert_after: "sermon" }, "b");
    d = addCustomElement(d, { label: "Minute for Mission", text: "", insert_after: "bogus" }, "c");
    expect(d.liturgy.custom_elements).toEqual([
      { id: "a", label: "Children's Moment", text: "Come forward.", insert_after: "opening_prayer" },
      { id: "b", label: "Anthem", text: "", insert_after: "sermon" },
      { id: "c", label: "Minute for Mission", text: "", insert_after: "end" },
    ]);
    const moved = updateCustomElement(d, "b", { insert_after: "second_hymn", label: "Choir Anthem" });
    expect(moved.liturgy.custom_elements[1]).toEqual({ id: "b", label: "Choir Anthem", text: "", insert_after: "second_hymn" });
    expect(updateCustomElement(moved, "b", { label: "Choir Anthem" })).toBe(moved);
    const removed = removeCustomElement(moved, "b");
    expect(removed?.index).toBe(1);
    expect(removed?.element.label).toBe("Choir Anthem");
    expect(removed?.draft.liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "c"]);
    expect(removeCustomElement(moved, "zzz")).toBeNull();
    const restored = restoreCustomElement(removed!.draft, removed!.element, removed!.index);
    expect(restored.liturgy.custom_elements.map((e) => e.id)).toEqual(["a", "b", "c"]);
    expect(restoreCustomElement(restored, removed!.element, 1)).toBe(restored); // already back
  });
});
```

**Create `frontend/src/lib/liturgy/defaults.test.ts`:**

```ts
/**
 * The liturgy defaults (slice 4 spec, Frontend `defaults.ts`; Testing
 * `defaults.test.ts`): the first-Sunday rule against the shared fixture, and
 * `applyLiturgyDefaults`, which keeps an untouched Benediction on the church
 * default and untouched communion on the date's rule.
 */
import { readFileSync } from "node:fs";

import { describe, expect, it } from "vitest";

import { isFirstSundayOfMonth } from "@/lib/dates";
import { setDate } from "@/lib/draft/readings";
import type { DraftV1 } from "@/lib/draft/schema";
import { testDraft } from "@/test/fixtures";

import { editCardText, setCommunion } from "./cards";
import { applyLiturgyDefaults, DEFAULT_BENEDICTION_FALLBACK } from "./defaults";

type Cases = { cases: { date: string; expected: boolean; why: string }[] };

const firstSunday = JSON.parse(
  readFileSync(new URL("../../../../backend/tests/fixtures/shared/first_sunday.json", import.meta.url), "utf-8"),
) as Cases;

describe("liturgy defaults (S Benediction and the church default; Communion card)", () => {
  it("puts communion on the first Sunday of the month, as the shared fixture says", () => {
    for (const { date, expected, why } of firstSunday.cases) expect(isFirstSundayOfMonth(date), why).toBe(expected);
  });

  it("keeps the Benediction on the church default only while it follows it, including an empty default", () => {
    expect(DEFAULT_BENEDICTION_FALLBACK).toBe("Halverson");
    const fresh = testDraft();
    const filled = applyLiturgyDefaults(fresh, { defaultBenediction: "Halverson" });
    expect(filled.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
    expect(applyLiturgyDefaults(filled, { defaultBenediction: "Halverson" })).toBe(filled);
    const changed = applyLiturgyDefaults(filled, { defaultBenediction: "The Lord bless you and keep you." });
    expect(changed.liturgy.cards.benediction.text).toBe("The Lord bless you and keep you.");
    expect(applyLiturgyDefaults(filled, { defaultBenediction: "" }).liturgy.cards.benediction).toEqual({
      enabled: true,
      text: "",
      origin: "default",
    });
    const edited = editCardText(filled, "benediction", "Go in peace.");
    expect(applyLiturgyDefaults(edited, { defaultBenediction: "Something else" })).toBe(edited);
  });

  it("recomputes communion from the date only while it is the default", () => {
    const d = testDraft(); // October 4, 2026: on
    const moved: DraftV1 = { ...d, readings: { ...d.readings, date_iso: "2026-10-11" } };
    expect(applyLiturgyDefaults(moved, { defaultBenediction: "" }).liturgy.include_communion).toBe(false);
    expect(setDate(d, "2026-10-11").liturgy.include_communion).toBe(false); // the date change applies the same rule
    const chosen = setCommunion(d, true);
    const chosenMoved: DraftV1 = { ...chosen, readings: { ...chosen.readings, date_iso: "2026-10-11" } };
    expect(applyLiturgyDefaults(chosenMoved, { defaultBenediction: "" }).liturgy.include_communion).toBe(true);
  });
});
```

**Create `frontend/src/lib/liturgy/summary.test.ts`:**

```ts
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
    const fresh = testDraft();
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
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/cards.test.ts src/lib/liturgy/defaults.test.ts src/lib/liturgy/summary.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|Error: Cannot find|Tests ")
```

**Expected:**

```
(pending replay)
```
- [ ] **Step 4 (agent): Write `cards.ts`, `defaults.ts` and `summary.ts`, and move the communion rule**

**Create `frontend/src/lib/liturgy/cards.ts`:**

```ts
/**
 * The Liturgy step's draft transitions and selectors (slice 4 spec, Frontend
 * `cards.ts`, "Card origin transitions"; F §4.6 "Card text is the user's").
 * Pure: each transition takes the draft and returns the next one, or the
 * same object when nothing changes, so `update(recipe)` stays a no-op.
 *
 * - Typing sets the origin to "typed", or "empty" when the text is blank
 *   after trimming; an AI result sets "ai"; Clear sets "" and "empty"; "Use
 *   church default" sets the default and "default"; Undo restores the
 *   previous text and origin; a switch changes neither.
 * - `staleVerdict` is the rule for a result that arrives after its request
 *   started (S "Generate and Regenerate" step 6). The generation provider
 *   applies it, and the service reviewer (the slice after 4b) reuses it for
 *   review results: capture the card when the request starts, compare when
 *   the answer arrives.
 */
import type { DraftV1, LiturgyCard, SectionKey } from "@/lib/draft/schema";
import { SECTION_KEYS } from "@/lib/draft/schema";

import { applyCommunionDefault } from "./defaults";

export type CardOrigin = LiturgyCard["origin"];
export type CardSnapshot = { text: string; origin: CardOrigin };
export type CustomElement = DraftV1["liturgy"]["custom_elements"][number];

/**
 * The 17 custom-element places (backend `liturgy_config.CUSTOM_PLACEMENTS`
 * keys, in order); `cards.test.ts` pins them to the outline fixture's
 * anchors. The labels come from GET /liturgy/config.
 */
export const PLACEMENT_KEYS = [
  "call_to_worship",
  "opening_prayer",
  "first_hymn",
  "prayer_of_confession",
  "assurance",
  "prayer_for_illumination",
  "ot_reading",
  "nt_reading",
  "sermon",
  "affirmation_of_faith",
  "second_hymn",
  "communion",
  "prayers_of_the_people",
  "offertory_prayer",
  "third_hymn",
  "benediction",
  "end",
] as const;

const PLACEMENTS: ReadonlySet<string> = new Set(PLACEMENT_KEYS);

/** A known place unchanged; anything else "end" (never dropped; mirrors `liturgy_config.normalize_placement`). */
export function normalizePlacement(key: string): string {
  return PLACEMENTS.has(key) ? key : "end";
}

function withCard(d: DraftV1, key: SectionKey, next: LiturgyCard): DraftV1 {
  const current = d.liturgy.cards[key];
  if (current.enabled === next.enabled && current.text === next.text && current.origin === next.origin) return d;
  return { ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, [key]: next } } };
}

function withLiturgy(d: DraftV1, patch: Partial<DraftV1["liturgy"]>): DraftV1 {
  return { ...d, liturgy: { ...d.liturgy, ...patch } };
}

/** The user typed: "typed" when non-blank after trimming, else "empty". */
export function editCardText(d: DraftV1, key: SectionKey, text: string): DraftV1 {
  const card = d.liturgy.cards[key];
  return withCard(d, key, { ...card, text, origin: text.trim() === "" ? "empty" : "typed" });
}

export function setCardEnabled(d: DraftV1, key: SectionKey, enabled: boolean): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], enabled });
}

export function applyGenerated(d: DraftV1, key: SectionKey, text: string): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text, origin: "ai" });
}

export function clearCard(d: DraftV1, key: SectionKey): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text: "", origin: "empty" });
}

/** "Use church default" (Benediction): the default's text, following it again. */
export function restoreChurchDefault(d: DraftV1, defaultText: string): DraftV1 {
  return withCard(d, "benediction", { ...d.liturgy.cards.benediction, text: defaultText, origin: "default" });
}

/** Undo: the text and origin kept in memory before a Regenerate or Clear. */
export function restoreCard(d: DraftV1, key: SectionKey, previous: CardSnapshot): DraftV1 {
  return withCard(d, key, { ...d.liturgy.cards[key], text: previous.text, origin: previous.origin });
}

export function setSermonTitle(d: DraftV1, title: string): DraftV1 {
  return d.liturgy.sermon_title === title ? d : withLiturgy(d, { sermon_title: title });
}

/** The communion switch: the user's choice from now on. */
export function setCommunion(d: DraftV1, include: boolean): DraftV1 {
  const l = d.liturgy;
  if (l.include_communion === include && l.communion_origin === "user") return d;
  return withLiturgy(d, { include_communion: include, communion_origin: "user" });
}

/** "Use default": communion follows the first-Sunday rule for the date again. */
export function restoreCommunionDefault(d: DraftV1): DraftV1 {
  const next = d.liturgy.communion_origin === "default" ? d : withLiturgy(d, { communion_origin: "default" });
  return applyCommunionDefault(next);
}

/** Appends an element with its label and text trimmed and its place normalized (S "On Add"). */
export function addCustomElement(d: DraftV1, element: Omit<CustomElement, "id">, id: string): DraftV1 {
  const added: CustomElement = {
    id,
    label: element.label.trim(),
    text: element.text.trim(),
    insert_after: normalizePlacement(element.insert_after),
  };
  return withLiturgy(d, { custom_elements: [...d.liturgy.custom_elements, added] });
}

export function updateCustomElement(d: DraftV1, id: string, patch: Partial<Omit<CustomElement, "id">>): DraftV1 {
  const list = d.liturgy.custom_elements;
  const at = list.findIndex((e) => e.id === id);
  if (at < 0) return d;
  const next = { ...list[at], ...patch };
  if (next.label === list[at].label && next.text === list[at].text && next.insert_after === list[at].insert_after) return d;
  return withLiturgy(d, { custom_elements: list.map((e, i) => (i === at ? next : e)) });
}

/** Removes the element; null when it is not there. The element and its index are for Undo. */
export function removeCustomElement(
  d: DraftV1,
  id: string,
): { draft: DraftV1; element: CustomElement; index: number } | null {
  const list = d.liturgy.custom_elements;
  const index = list.findIndex((e) => e.id === id);
  if (index < 0) return null;
  return { draft: withLiturgy(d, { custom_elements: list.filter((e) => e.id !== id) }), element: list[index], index };
}

/** Undo of Remove: back at its index (or the end), unless it is already there. */
export function restoreCustomElement(d: DraftV1, element: CustomElement, index: number): DraftV1 {
  const list = d.liturgy.custom_elements;
  if (list.some((e) => e.id === element.id)) return d;
  const at = Math.min(Math.max(index, 0), list.length);
  return withLiturgy(d, { custom_elements: [...list.slice(0, at), element, ...list.slice(at)] });
}

// --- selectors ---------------------------------------------------------------

/** Switched-on cards with no text (after trimming), in section order: what "Generate empty sections" sends. */
export function sectionsNeedingAi(d: DraftV1): SectionKey[] {
  return SECTION_KEYS.filter((key) => {
    const card = d.liturgy.cards[key];
    return card.enabled && card.text.trim() === "";
  });
}

/** Regenerate asks first when it would replace the user's own or a saved service's text. */
export function needsRegenerateConfirm(card: LiturgyCard): boolean {
  return (card.origin === "typed" || card.origin === "archive") && card.text.trim() !== "";
}

export type CapturedCard = { createdAt: string; text: string; origin: CardOrigin };

/** What a run remembers when its request starts. */
export function captureCard(d: DraftV1, key: SectionKey): CapturedCard {
  const card = d.liturgy.cards[key];
  return { createdAt: d.created_at, text: card.text, origin: card.origin };
}

export type StaleVerdict = "apply" | "service_changed" | "edited";

/**
 * S step 6, first matching rule: the draft was replaced (New service, an
 * archive load) → "service_changed"; the card followed the church default
 * then and still does → "apply" (the default changed mid-run, and the user
 * asked to replace it); its text changed (an edit in another tab) →
 * "edited"; otherwise "apply".
 */
export function staleVerdict(d: DraftV1, key: SectionKey, captured: CapturedCard): StaleVerdict {
  if (d.created_at !== captured.createdAt) return "service_changed";
  const card = d.liturgy.cards[key];
  if (captured.origin === "default" && card.origin === "default") return "apply";
  if (card.text !== captured.text) return "edited";
  return "apply";
}
```

**Create `frontend/src/lib/liturgy/defaults.ts`:**

```ts
/**
 * The liturgy defaults (slice 4 spec, Frontend `defaults.ts`, "Draft store
 * integration"; F §4.6 "Defaults apply only while origin is `default`"):
 *
 * - A Benediction card whose origin is "default" shows the church's
 *   `default_benediction` (GET /church; "Halverson" when an older API leaves it
 *   out), including "" (no default: the card is empty).
 * - Communion whose origin is "default" follows the first-Sunday rule for the
 *   draft's date (`isFirstSundayOfMonth`, slice 2's port of
 *   `liturgy_config.is_first_sunday_of_month`, run against
 *   shared/first_sunday.json in `defaults.test.ts`). This is the one place for
 *   the rule: `date-effects.ts` calls `applyCommunionDefault` on a date change.
 *
 * Both return the same object when nothing changes, so the draft store can
 * run them after every change without writing.
 */
import { isFirstSundayOfMonth } from "@/lib/dates";
import type { DraftV1 } from "@/lib/draft/schema";

export const DEFAULT_BENEDICTION_FALLBACK = "Halverson";

export type LiturgyDefaults = { defaultBenediction: string };

export function applyCommunionDefault(d: DraftV1): DraftV1 {
  if (d.liturgy.communion_origin !== "default") return d;
  const include = isFirstSundayOfMonth(d.readings.date_iso);
  if (include === d.liturgy.include_communion) return d;
  return { ...d, liturgy: { ...d.liturgy, include_communion: include } };
}

export function applyLiturgyDefaults(d: DraftV1, { defaultBenediction }: LiturgyDefaults): DraftV1 {
  const benediction = d.liturgy.cards.benediction;
  let next = d;
  if (benediction.origin === "default" && benediction.text !== defaultBenediction) {
    next = {
      ...d,
      liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { ...benediction, text: defaultBenediction } } },
    };
  }
  return applyCommunionDefault(next);
}
```

**Create `frontend/src/lib/liturgy/summary.ts`:**

```ts
/**
 * The liturgy counts behind the step bar's status and the summary (slice 4
 * spec, Frontend "Builder shell" `summary.ts`), one function so they cannot
 * disagree: `enabled` = cards switched on; `ready` = those whose text is
 * non-blank after trimming; `communion` = `include_communion`;
 * `customCount` = the custom elements.
 */
import { SECTION_KEYS, type DraftV1 } from "@/lib/draft/schema";

export type LiturgyCounts = { ready: number; enabled: number; communion: boolean; customCount: number };

export function liturgyCounts(d: DraftV1): LiturgyCounts {
  const enabled = SECTION_KEYS.map((key) => d.liturgy.cards[key]).filter((card) => card.enabled);
  return {
    ready: enabled.filter((card) => card.text.trim() !== "").length,
    enabled: enabled.length,
    communion: d.liturgy.include_communion,
    customCount: d.liturgy.custom_elements.length,
  };
}
```

**In `frontend/src/lib/draft/date-effects.ts`, replace:**

```ts
 * Slice 2: while `communion_origin` is `default`, `include_communion` follows
 * the first-Sunday rule for the new date (false for a weekday). Slice 3 adds
 * its hymn effect here (for example, dropping `alternatives` for another
 * date); slice 4 may move the communion rule into `applyLiturgyDefaults`.
 * Returns `d` itself when nothing changes.
 */
import { isFirstSundayOfMonth } from "@/lib/dates";

import type { DraftV1 } from "./schema";

// `prevIso` is kept in the signature for slice 3's hymn effect.
export function onDateChanged(d: DraftV1, prevIso: string): DraftV1 {
  void prevIso;
  if (d.liturgy.communion_origin !== "default") return d;
  const include = isFirstSundayOfMonth(d.readings.date_iso);
  if (include === d.liturgy.include_communion) return d;
  return { ...d, liturgy: { ...d.liturgy, include_communion: include } };
```

**with:**

```ts
 * While `communion_origin` is `default`, `include_communion` follows the
 * first-Sunday rule for the new date (false for a weekday). The rule lives in
 * `lib/liturgy/defaults.ts` (`applyCommunionDefault`, slice 4b), which the
 * draft store also runs after every change. Slice 3 adds no hymn effect here
 * (its ideas carry their own date). Returns `d` itself when nothing changes.
 */
import { applyCommunionDefault } from "@/lib/liturgy/defaults";

import type { DraftV1 } from "./schema";

// `prevIso` is kept in the signature for a later date effect.
export function onDateChanged(d: DraftV1, prevIso: string): DraftV1 {
  void prevIso;
  return applyCommunionDefault(d);
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy src/lib/draft 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  13 passed (13)`, `      Tests  66 passed (66)`; the suite ` Test Files  68 passed (68)`, `      Tests  455 passed (455)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M frontend/src/lib/draft/date-effects.ts` and the six new files under `frontend/src/lib/liturgy/` as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/cards.ts frontend/src/lib/liturgy/cards.test.ts frontend/src/lib/liturgy/defaults.ts frontend/src/lib/liturgy/defaults.test.ts frontend/src/lib/liturgy/summary.ts frontend/src/lib/liturgy/summary.test.ts frontend/src/lib/draft/date-effects.ts
git commit -m "Liturgy: card transitions, the Benediction and communion defaults, and the counts (S cards.ts, defaults.ts, summary.ts)" -m "Pure draft transitions for every row of the slice 4 origin table, the
communion switch and Use default, the sermon title and custom elements
(trimmed, restored at their index, unknown places read as end), the
selectors for Generate empty sections and Regenerate, and the stale-result
rule. applyLiturgyDefaults keeps an untouched Benediction on the church
default and untouched communion on the first-Sunday rule, which moves out
of date-effects.ts. liturgyCounts backs the status and the summary.
Frontend 446 -> 455 tests in 65 -> 68 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

**Review checkpoint (T1-T2, batch A):** `isPristine` counts exactly owner answer 1's fields and nothing transient; every S origin row has a test; the stale rule's order matches S step 6; the communion rule has one home; counts match.

### Task 3: The request body, the card errors and the queue (S Frontend `request.ts`, `errors.ts`, `queue.ts`, "Sermon text", "Per-card error messages"; BC-24; clarifications 7, 8, 9, 10)

The rest of the pure half. `request.ts` builds one section's `POST /liturgy/generate` body from the draft exactly as S's `request.ts` row says (one section, no `overrides`, the ServiceDraft limits, the three slots as `HymnRef`s) and works out which passage is the sermon text (`sermonSource`: the effective NT reading, the draft's or church's translation, WEB for ESV) and its `{ref, text}` (`sermonText`); the fetch itself is T6's. An id that is not a UUID goes as `null`, because the API validates `hymn_id` as a UUID and would reject the whole request (clarification 7). `errors.ts` turns a section's failure or a failed request into what the card shows, with S's copy; a cancel, a 401 and a lost church show nothing on the card (clarification 8), and the 404's link is labelled "Go to Hymns" (clarification 9). `queue.ts` runs at most 3 tasks, first in first out, and a cancelled task's outcome is never delivered. The generated type names join `lib/api/types.ts`.

**Files:**
- Create: `frontend/src/lib/liturgy/request.ts`, `frontend/src/lib/liturgy/errors.ts`, `frontend/src/lib/liturgy/queue.ts`
- Modify: `frontend/src/lib/api/types.ts` (the liturgy type names)
- Test: `frontend/src/lib/liturgy/request.test.ts` (new, 3), `frontend/src/lib/liturgy/errors.test.ts` (new, 2), `frontend/src/lib/liturgy/queue.test.ts` (new, 3)

**Interfaces:**
- Consumes: the generated `LiturgyConfigOut`, `GenerateLiturgyIn`/`Out`, `SectionResult`, `SectionError`, `SermonText`, `HymnRef` (4a's `schema.d.ts`, unchanged); `effectivePicks` (2c); `clipChars`, `cleanRefs`, `MAX_REFS`, `MAX_REF_LENGTH` (3b `lib/hymns/match-request.ts`); `passageText` (2c); `ApiError`, `describeError`, `isNoChurchAccess` (1, 2).
- Produces:
  - `lib/api/types.ts`: `LiturgyConfig`, `LiturgySection`, `OutlineItem`, `CommunionBlock`, `GenerateLiturgyBody`, `GenerateLiturgyResult`, `SectionResult`, `SectionError`, `SermonText`, `HymnRef`.
  - `request.ts`: `MAX_OCCASION`, `MAX_HYMN_TITLE`, `MAX_HYMNAL`, `MAX_SERMON_TEXT`, `buildGenerateRequest(draft, section, sermon: SermonText | null)`, `sermonSource(draft, churchTranslation) → {ref, translation} | null`, `sermonText(ref, passage | undefined) → SermonText | null`.
  - `errors.ts`: `type CardError = {code, message, retryable, retryAfterSeconds?, link?}`, `AI_NOT_CONFIGURED_MESSAGE`, `localAiNotConfigured()`, `cardErrorFrom(e) → CardError | null`.
  - `queue.ts`: `type TaskOutcome<T>`, `type TaskQueue = {push(key, run, done), cancel(key), cancelAll(), runningKeys(), waitingKeys()}`, `createTaskQueue({concurrency})`.
  - Later users: T4 (the fixtures use the type names), T6 (all of it).

Counts after this task: frontend **463 passed in 71 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "LiturgyConfig" frontend/src/lib/api/types.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  68 passed (68)`, `      Tests  455 passed (455)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/request.test.ts`:**

```ts
/**
 * The `POST /liturgy/generate` body (slice 4 spec, Frontend `request.ts`,
 * "Sermon text"; Testing `request.test.ts`; port-ledger target for
 * streamlit_tests/test_app_helpers.py::test_sermon_text_*): one section, no
 * overrides, the ServiceDraft limits, slot-keyed hymns, and the sermon text
 * from the effective NT reading, never from an ESV passage.
 */
import { describe, expect, it } from "vitest";

import type { Passage } from "@/lib/api/types";
import { editScriptureLines, setPick, setTranslation } from "@/lib/draft/readings";
import type { DraftV1, HymnPick } from "@/lib/draft/schema";
import { hymnId, testDraft } from "@/test/fixtures";

import { buildGenerateRequest, MAX_SERMON_TEXT, sermonSource, sermonText } from "./request";

const OCT_4 = ["Isaiah 5:1-7", "Psalm 80:7-15", "Philippians 3:4b-14", "Matthew 21:33-46"];

function withReadings(lines: string[], occasion = "Nineteenth Sunday after Pentecost"): DraftV1 {
  const d = editScriptureLines(testDraft(), lines.join("\n"));
  return { ...d, readings: { ...d.readings, occasion } };
}

function passage(ref: string, texts: (string | null)[]): Passage {
  return {
    reference: ref,
    status: texts.every((t) => t !== null) ? "ok" : "unavailable",
    sections: texts.map((text, i) => ({ reference: `${ref} (${i + 1})`, status: text === null ? "unavailable" : "ok", text })),
  };
}

describe("buildGenerateRequest (S request.ts)", () => {
  it("sends one section, no overrides, the readings within the limits and the three slots as HymnRefs", () => {
    const pick = (n: number, patch: Partial<HymnPick> = {}): HymnPick => ({
      hymn_id: hymnId(n),
      title: `Hymn ${n}`,
      number: n,
      hymnal: "GG2013",
      ...patch,
    });
    let d = withReadings(["  Isaiah 5:1-7  ", "", ...Array.from({ length: 21 }, (_, i) => `Psalm ${i + 1}`)], ` ${"o".repeat(305)} `);
    d = editScriptureLines(d, [...d.readings.scriptures.slice(0, 2), "x".repeat(205), ...d.readings.scriptures.slice(2)].join("\n"));
    d = {
      ...d,
      hymns: {
        ...d.hymns,
        slots: { opening: pick(403, { title: "t".repeat(301) }), response: null, closing: pick(0, { hymn_id: null, number: null, hymnal: null }) },
      },
    };
    const body = buildGenerateRequest(d, "call_to_worship", null);
    expect(body.sections).toEqual(["call_to_worship"]);
    expect(body).not.toHaveProperty("overrides");
    expect(body).not.toHaveProperty("sermon_text");
    expect(body.occasion).toBe("o".repeat(300));
    expect(body.scriptures).toHaveLength(20);
    expect(body.scriptures?.slice(0, 3)).toEqual(["Isaiah 5:1-7", "x".repeat(200), "Psalm 1"]);
    expect(body.hymns).toEqual({
      opening: { hymn_id: hymnId(403), title: "t".repeat(300), number: 403, hymnal: "GG2013" },
      response: null,
      closing: { hymn_id: null, title: "Hymn 0", number: null, hymnal: null },
    });
    // An id the API would reject (not a UUID) goes as a snapshot, with its own title.
    const odd = { ...d, hymns: { ...d.hymns, slots: { ...d.hymns.slots, response: pick(12, { hymn_id: "h12" }) } } };
    expect(buildGenerateRequest(odd, "benediction", null).hymns?.response).toEqual({
      hymn_id: null,
      title: "Hymn 12",
      number: 12,
      hymnal: "GG2013",
    });
  });

  it("adds the sermon text when there is one, cut to 20 000 characters", () => {
    const d = withReadings(OCT_4);
    const body = buildGenerateRequest(d, "opening_prayer", { ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" });
    expect(body.sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "Yet whatever gains I had…" });
    expect(sermonText("Philippians 3:4b-14", passage("Philippians 3:4b-14", ["a".repeat(20_005)]))?.text).toHaveLength(MAX_SERMON_TEXT);
    expect(sermonText("Mark 4:35-41", passage("Mark 4:35-41", ["Waves.", null, "Wind."]))).toEqual({
      ref: "Mark 4:35-41",
      text: "Waves.\n\nWind.",
    });
    expect(sermonText("Mark 4:35-41", passage("Mark 4:35-41", [null]))).toBeNull();
    expect(sermonText("Mark 4:35-41", undefined)).toBeNull();
  });
});

describe("sermonSource (S Sermon text)", () => {
  it("is the effective NT reading, never a Psalm, in the draft's translation with WEB for ESV", () => {
    expect(sermonSource(testDraft(), "web")).toBeNull(); // no readings
    expect(sermonSource(withReadings(["Psalm 23"]), "web")).toBeNull(); // a Psalm is never the NT reading
    const d = withReadings(OCT_4);
    expect(sermonSource(d, "web")).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // the automatic pick
    expect(sermonSource(setPick(d, "nt", "Matthew 21:33-46"), "kjv")).toEqual({ ref: "Matthew 21:33-46", translation: "kjv" });
    expect(sermonSource(d, "esv")).toEqual({ ref: "Philippians 3:4b-14", translation: "web" }); // Crossway's terms
    expect(sermonSource(setTranslation(d, "esv", "web"), "web")?.translation).toBe("web");
    expect(sermonSource(setTranslation(d, "kjv", "web"), "web")?.translation).toBe("kjv");
  });
});
```

**Create `frontend/src/lib/liturgy/errors.test.ts`:**

```ts
/**
 * The card's error for each code (slice 4 spec, "Per-card error messages";
 * Testing `errors.test.ts`): the server's section messages, the client's own,
 * which ones offer Try again, and the ones that show nothing on the card.
 */
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";

import { cardErrorFrom, localAiNotConfigured } from "./errors";

describe("cardErrorFrom (S errors.ts)", () => {
  it("shows the server's message for each section error, with Try again only where trying again can help", () => {
    const cases: [string, string, boolean][] = [
      ["ai_not_configured", "AI not configured. Type this section yourself.", false],
      ["ai_busy", "The AI service is busy. Try again in a minute.", true],
      ["ai_timeout", "The AI took too long to answer. Try again.", true],
      ["ai_upstream_error", "The AI service had a problem. Try again.", true],
      [
        "prompt_invalid",
        "The Call to Worship prompt in Settings has a problem: Placeholders need a name, such as {occasion}. An admin can fix it under Settings → Liturgy prompts.",
        false,
      ],
    ];
    for (const [code, message, retryable] of cases) {
      expect(cardErrorFrom({ code, message } as never), code).toEqual({ code, message, retryable });
    }
    // The local error used when the config says AI is off has exactly the server's text.
    expect(localAiNotConfigured()).toEqual({ code: "ai_not_configured", message: cases[0][1], retryable: false });
  });

  it("words the request errors as S's table, and shows nothing for a cancel, a sign-out or a lost church", () => {
    const hymn = cardErrorFrom(
      new ApiError(404, "not_found", "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step."),
    );
    expect(hymn).toEqual({
      code: "not_found",
      message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
      retryable: false,
      link: { href: "/builder/hymns", label: "Go to Hymns" },
    });
    expect(
      cardErrorFrom(new ApiError(429, "rate_limited", "Too many requests. Try again in 37 seconds.", { retryAfterSeconds: 37 })),
    ).toEqual({ code: "rate_limited", message: "Too many requests — try again in 37 s.", retryable: true, retryAfterSeconds: 37 });
    expect(cardErrorFrom(new ApiError(0, "timeout", "This is taking too long. Try again."))).toEqual({
      code: "timeout",
      message: "This is taking too long. Try again.",
      retryable: true,
    });
    expect(cardErrorFrom(new ApiError(0, "network_error", "Can't reach the server. Check your connection and try again."))).toEqual({
      code: "network_error",
      message: "Can't reach the server. Check your connection and try again.",
      retryable: true,
    });
    expect(
      cardErrorFrom(new ApiError(500, "internal_error", "Something went wrong.", { requestId: "4f9a2c1e8b7d4e6fa0c3b5d7e9f1a2b4" })),
    ).toEqual({ code: "internal_error", message: "Something went wrong. (Ref: 4f9a2c1e)", retryable: true });
    expect(cardErrorFrom(new ApiError(0, "aborted", "The request was cancelled."))).toBeNull();
    expect(cardErrorFrom(new ApiError(401, "unauthenticated", "Sign in again."))).toBeNull();
    expect(
      cardErrorFrom(new ApiError(403, "forbidden", "No access.", { details: { reason: "no_church_access" } })),
    ).toBeNull();
    expect(cardErrorFrom(new Error("boom"))).toEqual({ code: "unknown", message: "Something went wrong.", retryable: true });
  });
});
```

**Create `frontend/src/lib/liturgy/queue.test.ts`:**

```ts
/**
 * The generation queue (slice 4 spec, Frontend `queue.ts`; Testing
 * `queue.test.ts`): at most 3 running, first in first out, and a cancelled
 * task's signal aborts and its outcome is never delivered.
 */
import { describe, expect, it } from "vitest";

import { createTaskQueue, type TaskOutcome } from "./queue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function tick(): Promise<void> {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

function harness(concurrency = 3) {
  const queue = createTaskQueue({ concurrency });
  const started: string[] = [];
  const signals = new Map<string, AbortSignal>();
  const tasks = new Map<string, ReturnType<typeof deferred<string>>>();
  const outcomes: [string, TaskOutcome<string>][] = [];
  const push = (key: string) => {
    const task = deferred<string>();
    tasks.set(key, task);
    queue.push(
      key,
      (signal) => {
        started.push(key);
        signals.set(key, signal);
        return task.promise;
      },
      (outcome) => outcomes.push([key, outcome]),
    );
  };
  return { queue, started, signals, tasks, outcomes, push };
}

describe("createTaskQueue (S queue.ts)", () => {
  it("runs at most 3 at once, in the order pushed, and delivers each outcome", async () => {
    const h = harness();
    for (const key of ["a", "b", "c", "d", "e"]) h.push(key);
    await tick();
    expect(h.started).toEqual(["a", "b", "c"]);
    expect(h.queue.runningKeys()).toEqual(["a", "b", "c"]);
    expect(h.queue.waitingKeys()).toEqual(["d", "e"]);
    h.tasks.get("b")!.resolve("B");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "d"]);
    h.tasks.get("a")!.reject(new Error("no"));
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "d", "e"]);
    expect(h.outcomes).toEqual([
      ["b", { ok: true, value: "B" }],
      ["a", { ok: false, error: new Error("no") }],
    ]);
  });

  it("cancel aborts a running task or drops a waiting one, and neither outcome is delivered", async () => {
    const h = harness();
    for (const key of ["a", "b", "c", "d"]) h.push(key);
    await tick();
    expect(h.queue.cancel("d")).toBe(true); // waiting: never starts
    expect(h.queue.cancel("b")).toBe(true); // running: its signal aborts
    expect(h.signals.get("b")?.aborted).toBe(true);
    expect(h.queue.cancel("zzz")).toBe(false);
    h.tasks.get("b")!.resolve("late");
    await tick();
    expect(h.outcomes).toEqual([]);
    expect(h.started).toEqual(["a", "b", "c"]);
    expect(h.queue.runningKeys()).toEqual(["a", "c"]);
    h.push("e");
    await tick();
    expect(h.started).toEqual(["a", "b", "c", "e"]); // b's slot freed at once
  });

  it("cancelAll aborts every running task and drops every waiting one", async () => {
    const h = harness(2);
    for (const key of ["a", "b", "c"]) h.push(key);
    await tick();
    h.queue.cancelAll();
    expect([h.signals.get("a")?.aborted, h.signals.get("b")?.aborted]).toEqual([true, true]);
    for (const task of h.tasks.values()) task.resolve("late");
    await tick();
    expect(h.outcomes).toEqual([]);
    expect(h.started).toEqual(["a", "b"]);
    expect([h.queue.runningKeys(), h.queue.waitingKeys()]).toEqual([[], []]);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/request.test.ts src/lib/liturgy/errors.test.ts src/lib/liturgy/queue.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|Error: Cannot find|Tests ")
```

**Expected:**

```
(pending replay)
```
- [ ] **Step 4 (agent): Write the type names, `request.ts`, `errors.ts` and `queue.ts`**

**In `frontend/src/lib/api/types.ts`, replace:**

```ts
export type SuggestedHymn = components["schemas"]["SuggestedHymnOut"];

```

**with:**

```ts
export type SuggestedHymn = components["schemas"]["SuggestedHymnOut"];

/** `GET /liturgy/config` (slice 4a): the sections, custom places, order of worship, communion text, limits and `ai_available`. */
export type LiturgyConfig = components["schemas"]["LiturgyConfigOut"];
export type LiturgySection = components["schemas"]["SectionSpecOut"];
export type OutlineItem = components["schemas"]["OutlineItemOut"];
export type CommunionBlock = components["schemas"]["CommunionBlockOut"];
/** `POST /liturgy/generate` (slice 4a): the body the step sends (one section, no overrides) and the answer. */
export type GenerateLiturgyBody = components["schemas"]["GenerateLiturgyIn"];
export type GenerateLiturgyResult = components["schemas"]["GenerateLiturgyOut"];
export type SectionResult = components["schemas"]["SectionResult"];
/** A section's failure inside the 200 (the declared deviation from F §1.5). */
export type SectionError = components["schemas"]["SectionError"];
/** The effective NT reading and its text, never ESV (shared with the reviewer's routes). */
export type SermonText = components["schemas"]["SermonText"];
export type HymnRef = components["schemas"]["HymnRef"];

```

**Create `frontend/src/lib/liturgy/request.ts`:**

```ts
/**
 * The `POST /liturgy/generate` body (slice 4 spec, Frontend `request.ts`,
 * "Sermon text"; API §Schemas). Pure.
 *
 * - One section per request (the UI never batches sections into one call) and
 *   no `overrides`: typed cards are never sent at all.
 * - The occasion trimmed and cut to 300; the scriptures trimmed, blanks
 *   dropped, the first 20, each cut to 200 (the ServiceDraft limits); every
 *   cut counts characters as the server does (`clipChars`).
 * - `hymns`: the three slots as `HymnRef`s, each title cut to 300 and hymnal
 *   to 20. An id that is not a UUID (which the API would reject for the
 *   whole request) goes as `null`, so the pick's own title is used.
 * - `sermon_text`: the effective NT reading's passage, from `sermonSource`
 *   and the batch's one passage fetch (T6); left out when there is none.
 */
import type { GenerateLiturgyBody, HymnRef, Passage, SermonText } from "@/lib/api/types";
import { effectivePicks } from "@/lib/draft/readings";
import type { DraftV1, HymnPick, SectionKey } from "@/lib/draft/schema";
import { cleanRefs, clipChars, MAX_REF_LENGTH, MAX_REFS } from "@/lib/hymns/match-request";
import { passageText } from "@/lib/queries/passages";

export const MAX_OCCASION = 300;
export const MAX_HYMN_TITLE = 300;
export const MAX_HYMNAL = 20;
export const MAX_SERMON_TEXT = 20_000;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function hymnRef(pick: HymnPick | null): HymnRef | null {
  if (pick === null) return null;
  const number = pick.number !== null && pick.number >= 0 && pick.number <= 100_000 ? pick.number : null;
  return {
    hymn_id: pick.hymn_id !== null && UUID.test(pick.hymn_id) ? pick.hymn_id : null,
    title: clipChars(pick.title, MAX_HYMN_TITLE),
    number,
    hymnal: pick.hymnal === null ? null : clipChars(pick.hymnal, MAX_HYMNAL),
  };
}

export function buildGenerateRequest(draft: DraftV1, section: SectionKey, sermon: SermonText | null): GenerateLiturgyBody {
  const r = draft.readings;
  const slots = draft.hymns.slots;
  const body: GenerateLiturgyBody = {
    occasion: clipChars(r.occasion.trim(), MAX_OCCASION),
    scriptures: cleanRefs(r.scriptures, { max: MAX_REFS, maxLen: MAX_REF_LENGTH }),
    hymns: { opening: hymnRef(slots.opening), response: hymnRef(slots.response), closing: hymnRef(slots.closing) },
    sections: [section],
  };
  if (sermon !== null) body.sermon_text = sermon;
  return body;
}

/**
 * Which passage the sermon text is: the effective NT reading (the explicit
 * pick, else the automatic one; never a Psalm), in the draft's translation or
 * the church's, with WEB instead of ESV (Crossway's terms: ESV text is never
 * sent to the AI). `ref` is the reading as the passage cache keys it.
 */
export function sermonSource(draft: DraftV1, churchTranslation: string): { ref: string; translation: string } | null {
  const nt = effectivePicks(draft).nt;
  if (nt === null || clipChars(nt.trim(), MAX_REF_LENGTH) === "") return null;
  const translation = draft.readings.translation ?? churchTranslation;
  return { ref: nt, translation: translation === "esv" ? "web" : translation };
}

/** `sermon_text` from a loaded passage: the reference cut to 200, the text to 20 000; null without text. */
export function sermonText(ref: string, passage: Passage | undefined): SermonText | null {
  const text = passage ? passageText(passage) : null;
  if (text === null) return null;
  return { ref: clipChars(ref.trim(), MAX_REF_LENGTH), text: clipChars(text, MAX_SERMON_TEXT) };
}
```

**Create `frontend/src/lib/liturgy/errors.ts`:**

```ts
/**
 * What a card shows when its section could not be written (slice 4 spec,
 * "Per-card error messages", Frontend `errors.ts`; F §1.5: the client chooses
 * by `code` only). Two sources funnel through `cardErrorFrom`: a section's
 * failure inside the 200 (`SectionError`, whose message the server wrote)
 * and a failed request (`ApiError`).
 *
 * `null` means the card shows nothing: a cancel (the card returns to where it
 * was), and a 401 or a lost church, which the app's global handling already
 * acts on (sign-out, another church).
 */
import { ApiError } from "@/lib/api/client";
import { describeError, isNoChurchAccess } from "@/lib/api/errors";
import type { SectionError } from "@/lib/api/types";

export type CardError = {
  code: string;
  message: string;
  /** Shows "Try again". */
  retryable: boolean;
  /** A 429's wait: Try again is enabled after it. */
  retryAfterSeconds?: number;
  link?: { href: string; label: string };
};

export const AI_NOT_CONFIGURED_MESSAGE = "AI not configured. Type this section yourself.";

const RETRYABLE_SECTION_CODES: ReadonlySet<string> = new Set(["ai_busy", "ai_timeout", "ai_upstream_error"]);

/** The error marked on a card locally when the config says AI is off; the same text as the server's. */
export function localAiNotConfigured(): CardError {
  return { code: "ai_not_configured", message: AI_NOT_CONFIGURED_MESSAGE, retryable: false };
}

function isSectionError(e: unknown): e is SectionError {
  return (
    typeof e === "object" && e !== null && !(e instanceof Error) && typeof (e as SectionError).code === "string" &&
    typeof (e as SectionError).message === "string"
  );
}

export function cardErrorFrom(e: unknown): CardError | null {
  if (isSectionError(e)) return { code: e.code, message: e.message, retryable: RETRYABLE_SECTION_CODES.has(e.code) };
  if (!(e instanceof ApiError)) return { code: "unknown", message: "Something went wrong.", retryable: true };
  if (e.code === "aborted" || e.status === 401 || isNoChurchAccess(e)) return null;
  switch (e.code) {
    case "not_found":
      return {
        code: e.code,
        message: "A chosen hymn is no longer in your hymnal. Choose it again on the Hymns step.",
        retryable: false,
        link: { href: "/builder/hymns", label: "Go to Hymns" },
      };
    case "rate_limited":
      return e.retryAfterSeconds === undefined
        ? { code: e.code, message: e.message, retryable: true }
        : {
            code: e.code,
            message: `Too many requests — try again in ${e.retryAfterSeconds} s.`,
            retryable: true,
            retryAfterSeconds: e.retryAfterSeconds,
          };
    case "ai_not_configured":
    case "prompt_invalid":
      return { code: e.code, message: e.message, retryable: false };
    default:
      // timeout and network_error carry their own full sentences; a 5xx reads "Something went wrong. (Ref: …)".
      return { code: e.code, message: e.status >= 500 ? describeError(e) : e.message, retryable: true };
  }
}
```

**Create `frontend/src/lib/liturgy/queue.ts`:**

```ts
/**
 * The generation queue (slice 4 spec, Frontend `queue.ts`; "Generate empty
 * sections": at most 3 in flight, which leaves one of the server's 4 AI slots
 * free). First in, first out; each task gets its own `AbortController`.
 * `cancel(key)` aborts a running task or drops a waiting one, frees its slot
 * at once, and its outcome is never delivered.
 */
export type TaskOutcome<T> = { ok: true; value: T } | { ok: false; error: unknown };

export type TaskQueue = {
  push<T>(key: string, run: (signal: AbortSignal) => Promise<T>, done: (outcome: TaskOutcome<T>) => void): void;
  /** False when the key is neither waiting nor running. */
  cancel(key: string): boolean;
  cancelAll(): void;
  runningKeys(): string[];
  waitingKeys(): string[];
};

type Task = { key: string; start: () => void; controller: AbortController };

export function createTaskQueue({ concurrency }: { concurrency: number }): TaskQueue {
  const waiting: Task[] = [];
  const running = new Map<string, Task>();

  function pump(): void {
    while (running.size < concurrency && waiting.length > 0) {
      const task = waiting.shift() as Task;
      running.set(task.key, task);
      task.start();
    }
  }

  function cancel(key: string): boolean {
    const at = waiting.findIndex((t) => t.key === key);
    if (at >= 0) {
      waiting.splice(at, 1);
      return true;
    }
    const task = running.get(key);
    if (!task) return false;
    running.delete(key);
    task.controller.abort();
    pump();
    return true;
  }

  return {
    push<T>(key: string, run: (signal: AbortSignal) => Promise<T>, done: (outcome: TaskOutcome<T>) => void) {
      cancel(key);
      const controller = new AbortController();
      const task: Task = {
        key,
        controller,
        start: () => {
          const settle = (outcome: TaskOutcome<T>) => {
            if (controller.signal.aborted || running.get(key) !== task) return;
            running.delete(key);
            pump();
            done(outcome);
          };
          Promise.resolve()
            .then(() => run(controller.signal))
            .then(
              (value: T) => settle({ ok: true, value }),
              (error: unknown) => settle({ ok: false, error }),
            );
        },
      };
      waiting.push(task);
      pump();
    },
    cancel,
    cancelAll() {
      waiting.length = 0;
      for (const task of running.values()) task.controller.abort();
      running.clear();
    },
    runningKeys: () => [...running.keys()],
    waitingKeys: () => waiting.map((t) => t.key),
  };
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck 2>&1 | tail -1 && npm run lint 2>&1 | tail -1)
git status --short
```

**Expected:** ` Test Files  7 passed (7)`, `      Tests  18 passed (18)`; the suite ` Test Files  71 passed (71)`, `      Tests  463 passed (463)`; `> tsc --noEmit` and `> eslint` with nothing after them; ` M frontend/src/lib/api/types.ts` and six new files under `frontend/src/lib/liturgy/` as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/api/types.ts frontend/src/lib/liturgy/request.ts frontend/src/lib/liturgy/request.test.ts frontend/src/lib/liturgy/errors.ts frontend/src/lib/liturgy/errors.test.ts frontend/src/lib/liturgy/queue.ts frontend/src/lib/liturgy/queue.test.ts
git commit -m "Liturgy: the generate request, the card errors and the three-at-a-time queue (S request.ts, errors.ts, queue.ts)" -m "buildGenerateRequest sends one section and no overrides, within the
ServiceDraft limits, with the three slots as HymnRefs (a non-UUID id goes
as a snapshot). sermonSource picks the effective NT reading in the draft's
translation, WEB for ESV; sermonText cuts it to 20 000 characters.
cardErrorFrom words every code as the slice 4 table does and shows nothing
for a cancel, a 401 or a lost church. createTaskQueue runs at most 3,
first in first out, and never delivers a cancelled task's outcome.
Frontend 455 -> 463 tests in 68 -> 71 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.
