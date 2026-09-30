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
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  4 passed (4)`, `      Tests  30 passed (30)`; the suite ` Test Files  65 passed (65)`, `      Tests  446 passed (446)`; `typecheck 0` and `lint 0`; ` M` for the five modified files and `??` for `frontend/src/lib/liturgy/`.

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
    const fresh = applyLiturgyDefaults(testDraft(), { defaultBenediction: "" }); // a church with no default
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
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  13 passed (13)`, `      Tests  66 passed (66)`; the suite ` Test Files  68 passed (68)`, `      Tests  455 passed (455)`; `typecheck 0` and `lint 0`; ` M frontend/src/lib/draft/date-effects.ts` and the six new files under `frontend/src/lib/liturgy/` as `??`.

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
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  7 passed (7)`, `      Tests  18 passed (18)`; the suite ` Test Files  71 passed (71)`, `      Tests  463 passed (463)`; `typecheck 0` and `lint 0`; ` M frontend/src/lib/api/types.ts` and six new files under `frontend/src/lib/liturgy/` as `??`.

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

### Task 4: The liturgy queries, the 100-second timeout, and the test fixtures (S "API client usage", "Sermon text" loading; F §4.4, §1.8; owner answer 2; clarifications 10, 11, 12)

The API side of the step. `lib/queries/liturgy.ts` holds `useLiturgyConfig()` (user-scoped reference data, never stale) and `generateSection()` (one church-scoped `POST /liturgy/generate`, returning that section's result; S passes the draft, this takes the built body, clarification 10). The client timeout for that route is 100 000 ms, owner answer 2: `lib/api/timeouts.ts` keeps per-route timeouts in its `ENDPOINT_TIMEOUTS` table (there is no `TIMEOUTS` object; clarification 11), so the row is `"POST /liturgy/generate": 100_000`. `passages.ts` exports `passageQuery()`, the options `usePassage` already used, so T6 can `fetchQuery` the sermon text through the same key, limiter and freshness. `client.ts` exports `reportAuthErrors(error, churchId)`, the logic `handleAuthErrors` runs for the caches, so a call made outside them (the generation queue) signs out on a 401 and falls back on a lost church the same way (clarification 12). The test fixtures gain `liturgyConfig()` (pinned to 4a's shared fixtures), `sectionResult()`, `sectionFailure()` and `generateRoute()`.

**Files:**
- Create: `frontend/src/lib/queries/liturgy.ts`
- Modify: `frontend/src/lib/api/timeouts.ts` (the 100 s row), `frontend/src/lib/queries/client.ts` (`reportAuthErrors`), `frontend/src/lib/queries/passages.ts` (`passageQuery`), `frontend/src/test/fixtures/index.ts` (the liturgy builders)
- Test: `frontend/src/lib/queries/liturgy.test.tsx` (new, 3), `frontend/src/lib/queries/client.test.ts` (+1). 2c's passage tests keep pinning `usePassage`.

**Interfaces:**
- Consumes: T3's type names; `keys.liturgyConfig()` (1; already `["ref", "liturgy-config"]`); `useApi`, `ApiCall`, `Api` (1); `passageLimiter`, `passageStaleTime`, `keys.passage` (2c); `authEvents`, `isSigningOut`, `isNoChurchAccess` (1); `SECTION_LABELS` (T1); `PLACEMENT_KEYS` (T2).
- Produces:
  - `useLiturgyConfig(): UseQueryResult<LiturgyConfig, ApiError>`; `generateSection(call: ApiCall, section: SectionKey, body: GenerateLiturgyBody, signal?: AbortSignal): Promise<SectionResult>` (an answer without that section is `ApiError(0, "unknown", "Something went wrong.")`).
  - `timeoutFor("POST", "/liturgy/generate") === 100_000`.
  - `passageQuery(api, translation, ref) → {queryKey, queryFn, staleTime}`.
  - `reportAuthErrors(error, churchId: string | null): void`.
  - Fixtures: `liturgyConfig(overrides?)`, `sectionResult(section, text)`, `sectionFailure(section, code, message)`, `generateRoute(answer?)` (a `POST /liturgy/generate` handler; by default each section comes back as "{Label} written by the AI.").
  - Later users: T6 (`generateSection`, `passageQuery`, `reportAuthErrors`), T8-T11 (`useLiturgyConfig`, the fixtures).

Counts after this task: frontend **467 passed in 72 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "liturgy" frontend/src/lib/api/timeouts.ts
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  71 passed (71)`, `      Tests  463 passed (463)`.

- [ ] **Step 2 (agent): Write the fixtures and the failing tests**

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
  ChurchProfile,
  Hymn,
```

**with:**

```ts
  ChurchProfile,
  GenerateLiturgyBody,
  Hymn,
```

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
  ScriptureMatches,
```

**with:**

```ts
  LiturgyConfig,
  LiturgySection,
  OutlineItem,
  ScriptureMatches,
  SectionError,
  SectionResult,
```

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";

```

**with:**

```ts
import { freshDraft, type DraftV1 } from "@/lib/draft/schema";
import { SECTION_LABELS } from "@/lib/liturgy/sections";

```

**In `frontend/src/test/fixtures/index.ts`, replace:**

```ts
    slots: { opening: out(slots.opening), response: out(slots.response), closing: out(slots.closing) },
    ...overrides,
  };
}

```

**with:**

```ts
    slots: { opening: out(slots.opening), response: out(slots.response), closing: out(slots.closing) },
    ...overrides,
  };
}

// --- slice 4b: the liturgy config and the generation answers --------------------

/**
 * `GET /liturgy/config` as 4a serves it (slice 4a record: 8 sections, 17
 * places, 16 outline items, `ai_available` true), with the communion text
 * shortened to its first seven blocks. `liturgy.test.tsx` pins the sections,
 * places and outline to the shared fixtures.
 */
export function liturgyConfig(overrides: Partial<LiturgyConfig> = {}): LiturgyConfig {
  const section = (
    key: LiturgySection["key"],
    label: string,
    hint: string | null = null,
    extra: Partial<LiturgySection> = {},
  ): LiturgySection => ({ key, label, default_enabled: true, rows: 4, pastor_copy_only: false, hint, ...extra });
  const landmark = (
    key: string,
    label: string,
    value_source: OutlineItem["value_source"],
    anchors: string[] = [key],
    fixed_text: string | null = null,
  ): OutlineItem => ({ kind: "landmark", key, label, value_source, fixed_text, anchors_after: anchors });
  const card = (key: string, label: string, anchors: string[] = [key]): OutlineItem => ({
    kind: "section",
    key,
    label,
    value_source: "none",
    fixed_text: null,
    anchors_after: anchors,
  });
  return {
    sections: [
      section("call_to_worship", "Call to Worship", "Start lines with “Leader:” or “People:”. People lines print in bold."),
      section("opening_prayer", "Opening Prayer"),
      section("prayer_of_confession", "Prayer of Confession", "Printed in bold for everyone to read together."),
      section("assurance", "Assurance of Pardon", "Added automatically after your text."),
      section("prayer_for_illumination", "Prayer for Illumination"),
      section("prayers_of_the_people", "Prayers of the People", null, { default_enabled: false, rows: 8, pastor_copy_only: true }),
      section("offertory_prayer", "Offertory Prayer"),
      section("benediction", "Benediction", "Your church's default benediction. Admins can change it in Settings."),
    ],
    custom_placements: [
      ["call_to_worship", "After Call to Worship"],
      ["opening_prayer", "After Opening Prayer"],
      ["first_hymn", "After First Hymn"],
      ["prayer_of_confession", "After Prayer of Confession"],
      ["assurance", "After Assurance of Pardon"],
      ["prayer_for_illumination", "After Prayer for Illumination"],
      ["ot_reading", "After First Reading"],
      ["nt_reading", "After New Testament Reading"],
      ["sermon", "After Sermon"],
      ["affirmation_of_faith", "After Affirmation of Faith"],
      ["second_hymn", "After Second Hymn"],
      ["communion", "After Communion"],
      ["prayers_of_the_people", "After Prayers of the People"],
      ["offertory_prayer", "After Offertory Prayer"],
      ["third_hymn", "After Third Hymn"],
      ["benediction", "Before Benediction"],
      ["end", "At the end (after Benediction)"],
    ].map(([key, label]) => ({ key, label })),
    outline: [
      card("call_to_worship", "Call to Worship"),
      card("opening_prayer", "Opening Prayer"),
      landmark("first_hymn", "First Hymn", "hymn_opening"),
      card("prayer_of_confession", "Prayer of Confession"),
      card("assurance", "Assurance of Pardon"),
      card("prayer_for_illumination", "Prayer for Illumination"),
      landmark("ot_reading", "First Reading", "reading_ot"),
      landmark("nt_reading", "New Testament Reading", "reading_nt"),
      landmark("sermon", "Sermon Title", "sermon_title"),
      landmark("affirmation_of_faith", "Affirmation of Faith", "fixed", ["affirmation_of_faith"], "Apostles' Creed"),
      landmark("second_hymn", "Second Hymn", "hymn_response"),
      {
        kind: "communion",
        key: "communion",
        label: "The Sacrament of the Lord's Supper",
        value_source: "none",
        fixed_text: null,
        anchors_after: ["communion"],
      },
      card("prayers_of_the_people", "Prayers of the People"),
      card("offertory_prayer", "Offertory Prayer"),
      landmark("third_hymn", "Third Hymn", "hymn_closing", ["third_hymn", "benediction"]),
      card("benediction", "Benediction", ["end"]),
    ],
    assurance_response: "People: Thanks be to God! Amen.",
    default_benediction_fallback: "Halverson",
    communion: {
      title: "The Sacrament of the Lord's Supper",
      toggle_label: "Include communion liturgy (The Sacrament of the Lord's Supper)",
      default_rule: "first_sunday_of_month",
      blocks: [
        { style: "heading1", text: "The Sacrament of the Lord's Supper" },
        { style: "blank", text: "" },
        { style: "heading2", text: "Invitation to the Table" },
        { style: "text", text: "This is the table of our Lord Jesus Christ." },
        { style: "heading2", text: "Great Thanksgiving" },
        { style: "text", text: "The Lord be with you." },
        { style: "response", text: "And also with you." },
      ],
    },
    limits: {
      max_section_text: 20_000,
      max_sermon_title: 300,
      max_custom_elements: 30,
      max_custom_label: 200,
      max_custom_text: 10_000,
      max_sections_per_request: 4,
    },
    ai_available: true,
    ...overrides,
  };
}

/** A section written by the AI (`status: "generated"`). */
export function sectionResult(section: SectionResult["section"], text: string): SectionResult {
  return { section, status: "generated", text, error: null };
}

/** A section's failure inside the 200 (`status: "error"`), with the server's message. */
export function sectionFailure(section: SectionResult["section"], code: SectionError["code"], message: string): SectionResult {
  return { section, status: "error", text: null, error: { code, message } };
}

/**
 * A fake-API handler for `POST /liturgy/generate`: `answer(section, body)`
 * gives the section's result (wrapped in `{results: [...]}`) or a whole
 * response (`fakeError(...)`); by default "{Label} written by the AI.".
 */
export function generateRoute(
  answer: (
    section: SectionResult["section"],
    body: GenerateLiturgyBody,
  ) => SectionResult | { status: number } | Promise<SectionResult | { status: number }> = (section) =>
    sectionResult(section, `${SECTION_LABELS[section]} written by the AI.`),
) {
  return async (req: { body: unknown }) => {
    const body = req.body as GenerateLiturgyBody;
    const out = await answer(body.sections[0], body);
    return "section" in out ? { results: [out] } : out;
  };
}

```

**In `frontend/src/lib/queries/client.test.ts`, replace:**

```ts
import { isRetryable, makeQueryClient } from "./client";
```

**with:**

```ts
import { isRetryable, makeQueryClient, reportAuthErrors } from "./client";
```

**In `frontend/src/lib/queries/client.test.ts`, replace:**

```ts

  it("emits nothing while signing out", async () => {
```

**with:**

```ts

  it("reportAuthErrors does the same for a call made outside the caches (slice 4b generation)", () => {
    reportAuthErrors(new ApiError(401, "unauthenticated", "Please sign in."), "c-3");
    reportAuthErrors(noChurchAccess(), "c-3");
    reportAuthErrors(new ApiError(403, "forbidden", "Only church admins can do this."), "c-3");
    reportAuthErrors(new ApiError(429, "rate_limited", "Too many requests."), "c-3");
    expect(events).toEqual(["signOutRequired", "churchAccessLost:c-3"]);
  });

  it("emits nothing while signing out", async () => {
```

**Create `frontend/src/lib/queries/liturgy.test.tsx`:**

```tsx
/**
 * The Liturgy step's API calls (slice 4 spec, "API client usage"; F §4.4,
 * §1.8): the config is user-scoped reference data fetched once; a section is
 * written by one church-scoped POST that may take up to 100 s (owner answer
 * 2, 2026-09-30) and can be cancelled. The test fixture's config is pinned to
 * the shared fixtures 4a's API is pinned to.
 */
import { QueryClientProvider, type QueryClient } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import type { ReactNode } from "react";
import { describe, expect, it } from "vitest";

import { ApiError } from "@/lib/api/client";
import { timeoutFor } from "@/lib/api/timeouts";
import { ChurchProvider } from "@/lib/church-context";
import { PLACEMENT_KEYS } from "@/lib/liturgy/cards";
import { installFakeApi } from "@/test/fake-api";
import { church, CHURCH_IDS, liturgyConfig, sectionResult } from "@/test/fixtures";

import { makeQueryClient, useApi } from "./client";
import { keys } from "./keys";
import { generateSection, useLiturgyConfig } from "./liturgy";

/** A shared fixture, read from the repo (the tests run in `frontend/`). */
function shared<T>(name: string): T {
  return JSON.parse(readFileSync(`${process.cwd()}/../backend/tests/fixtures/shared/${name}`, "utf-8")) as T;
}

function render<T>(hook: () => T, queryClient: QueryClient = makeQueryClient({ queries: { retry: false } })) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <ChurchProvider value={church()}>{children}</ChurchProvider>
      </QueryClientProvider>
    );
  }
  return { ...renderHook(hook, { wrapper: Wrapper }), queryClient };
}

describe("liturgy queries (S API client usage)", () => {
  it("loads the config once as the user, and never counts it stale", async () => {
    const api = installFakeApi({ "GET /liturgy/config": liturgyConfig() });
    const { result, queryClient } = render(() => useLiturgyConfig());
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.sections).toHaveLength(8);
    expect(api.requests.map((r) => [r.method, r.path, r.headers["X-Church-Id"]])).toEqual([
      ["GET", "/liturgy/config", undefined],
    ]);
    const query = queryClient.getQueryCache().find({ queryKey: keys.liturgyConfig() });
    expect(query?.isStale()).toBe(false);
    render(() => useLiturgyConfig(), queryClient);
    expect(api.requests).toHaveLength(1);
  });

  it("writes one section as the church, waiting up to 100 seconds, and a cancel rejects as aborted", async () => {
    expect(timeoutFor("POST", "/liturgy/generate")).toBe(100_000);
    const api = installFakeApi({
      "POST /liturgy/generate": { results: [sectionResult("call_to_worship", "Leader: Come!")] },
    });
    const { result } = render(() => useApi());
    const body = { occasion: "", scriptures: [], hymns: {}, sections: ["call_to_worship" as const] };
    await expect(generateSection(result.current.church, "call_to_worship", body)).resolves.toEqual(
      sectionResult("call_to_worship", "Leader: Come!"),
    );
    expect(api.requests[0]).toMatchObject({ method: "POST", path: "/liturgy/generate", body });
    expect(api.requests[0].headers["X-Church-Id"]).toBe(CHURCH_IDS.grace);
    const controller = new AbortController();
    controller.abort();
    await expect(generateSection(result.current.church, "call_to_worship", body, controller.signal)).rejects.toMatchObject(
      new ApiError(0, "aborted", "The request was cancelled."),
    );
  });

  it("uses a test config equal to the shared fixtures 4a's API is pinned to", () => {
    const config = liturgyConfig();
    const sections = shared<{ sections: { key: string; label: string; default_enabled: boolean }[] }>("liturgy_sections.json");
    expect(config.sections.map(({ key, label, default_enabled }) => ({ key, label, default_enabled }))).toEqual(sections.sections);
    expect(config.outline).toEqual(shared<{ outline: unknown[] }>("liturgy_outline.json").outline);
    expect(config.custom_placements.map((p) => p.key)).toEqual([...PLACEMENT_KEYS]);
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/queries/liturgy.test.tsx src/lib/queries/client.test.ts 2>&1 | grep -E "^ FAIL|AssertionError|TypeError|Error: Failed|Tests ")
```

**Expected:**

```
(pending replay)
```
- [ ] **Step 4 (agent): Write the queries, the timeout row, `passageQuery` and `reportAuthErrors`**

**In `frontend/src/lib/api/timeouts.ts`, replace:**

```ts
  "POST /hymns/suggestions": 90_000,
};
```

**with:**

```ts
  "POST /hymns/suggestions": 90_000,
  // Slice 4 (F §1.8 amendment, owner answer 2, 2026-09-30): a section answers within
  // 85 s (4a's 80 s deadline plus a last connect); 100 s also covers a slow sign-in.
  // The service reviewer's routes (the slice after 4b) reuse this value.
  "POST /liturgy/generate": 100_000,
};
```

**In `frontend/src/lib/queries/client.ts`, replace:**

```ts
export function handleAuthErrors(error: unknown, source: AnyQuery | AnyMutation): void {
  if (isSigningOut()) return;
```

**with:**

```ts
export function handleAuthErrors(error: unknown, source: AnyQuery | AnyMutation): void {
  reportAuthErrors(error, churchIdOf(source));
}

/**
 * `handleAuthErrors` for a call made outside the caches (slice 4b: the
 * liturgy generation queue): a 401 asks for sign-out; a `no_church_access`
 * 403 reports `churchId` lost. Nothing while signing out.
 */
export function reportAuthErrors(error: unknown, churchId: string | null): void {
  if (isSigningOut()) return;
```

**In `frontend/src/lib/queries/client.ts`, replace:**

```ts
  if (isNoChurchAccess(error)) {
    const churchId = churchIdOf(source);
    if (churchId) authEvents.churchAccessLost(churchId);
  }
```

**with:**

```ts
  if (isNoChurchAccess(error) && churchId) authEvents.churchAccessLost(churchId);
```

**In `frontend/src/lib/queries/passages.ts`, replace:**

```ts
import { useApi } from "./client";
```

**with:**

```ts
import { useApi, type Api } from "./client";
```

**In `frontend/src/lib/queries/passages.ts`, replace:**

```ts
    queryKey: keys.passage(translation, ref),
    queryFn: ({ signal }) =>
      passageLimiter(async () => {
        const body = await api.user<Passages>("/scripture/passages", {
          method: "POST",
          json: { refs: [ref], translation },
          signal,
        });
        return body.passages[0];
      }, signal),
    enabled,
    staleTime: (query) => passageStaleTime(query.state.data),
```

**with:**

```ts
    ...passageQuery(api, translation, ref),
    enabled,
```

**In `frontend/src/lib/queries/passages.ts`, replace:**

```ts
  });
}

```

**with:**

```ts
  });
}

/**
 * The key, fetch and freshness `usePassage` uses, for a fetch outside a
 * component: slice 4b's liturgy provider reads the sermon text with
 * `queryClient.fetchQuery(passageQuery(...))`, so a passage step 1 already
 * loaded is reused and concurrent reads share one request.
 */
export function passageQuery(api: Api, translation: string, ref: string) {
  return {
    queryKey: keys.passage(translation, ref),
    queryFn: ({ signal }: { signal: AbortSignal }) =>
      passageLimiter(async () => {
        const body = await api.user<Passages>("/scripture/passages", {
          method: "POST",
          json: { refs: [ref], translation },
          signal,
        });
        return body.passages[0];
      }, signal),
    staleTime: (query: { state: { data: Passage | undefined } }) => passageStaleTime(query.state.data),
  };
}

```

**Create `frontend/src/lib/queries/liturgy.ts`:**

```ts
/**
 * The Liturgy step's API calls (slice 4 spec, "API client usage"; F §4.4).
 *
 * - `useLiturgyConfig()`: `GET /liturgy/config`, user-scoped reference data
 *   under ["ref", "liturgy-config"], never stale. A key added to Railway later
 *   (`ai_available`) takes effect on the next page load.
 * - `generateSection(call, section, body, signal)`: one
 *   `POST /liturgy/generate`, church-scoped, returning that section's result.
 *   A plain async function, because the provider's per-section queue and
 *   cancel do not fit `useMutation`; it still lives here, so no page calls
 *   `apiFetch`. Its client timeout is 100 s (`lib/api/timeouts.ts`, owner
 *   answer 2, 2026-09-30).
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { ApiError } from "@/lib/api/client";
import type { GenerateLiturgyBody, GenerateLiturgyResult, LiturgyConfig, SectionResult } from "@/lib/api/types";
import type { SectionKey } from "@/lib/draft/schema";

import { useApi, type ApiCall } from "./client";
import { keys } from "./keys";

export function useLiturgyConfig(): UseQueryResult<LiturgyConfig, ApiError> {
  const api = useApi();
  return useQuery<LiturgyConfig, ApiError>({
    queryKey: keys.liturgyConfig(),
    queryFn: ({ signal }) => api.user<LiturgyConfig>("/liturgy/config", { signal }),
    staleTime: Infinity,
  });
}

export async function generateSection(
  call: ApiCall,
  section: SectionKey,
  body: GenerateLiturgyBody,
  signal?: AbortSignal,
): Promise<SectionResult> {
  const out = await call<GenerateLiturgyResult>("/liturgy/generate", { method: "POST", json: body, signal });
  const result = out.results.find((r) => r.section === section);
  if (!result) throw new ApiError(0, "unknown", "Something went wrong.");
  return result;
}
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/queries 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  9 passed (9)`, `      Tests  45 passed (45)`; the suite ` Test Files  72 passed (72)`, `      Tests  467 passed (467)`; `typecheck 0` and `lint 0`; ` M` for the five modified files and `??` for the two new ones.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/queries/liturgy.ts frontend/src/lib/queries/liturgy.test.tsx frontend/src/lib/api/timeouts.ts frontend/src/lib/queries/client.ts frontend/src/lib/queries/client.test.ts frontend/src/lib/queries/passages.ts frontend/src/test/fixtures/index.ts
git commit -m "Liturgy: the config and generate calls, a 100 s client timeout, and the test fixtures (S API client usage; owner answer 2)" -m "useLiturgyConfig loads GET /liturgy/config once as the user, never
stale; generateSection posts one section as the church and returns its
result, with a 100 s client timeout (owner answer 2: 4a answers within
85 s, plus a slow sign-in). passageQuery shares usePassage's key, limiter
and freshness for the sermon text; reportAuthErrors gives a call made
outside the caches the same 401 and lost-church handling. The fixtures'
liturgy config is pinned to 4a's shared fixtures.
Frontend 463 -> 467 tests in 71 -> 72 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 7 files changed.

### Task 5: The draft follows the church's default benediction (S "Benediction and the church default", "Draft store integration"; F §4.6 "Fresh draft", "Defaults"; clarifications 13, 14)

S: a fresh draft's Benediction card is `{enabled: true, text: <church default>, origin: "default"}`, the card follows the default until it is edited, generated or cleared, and `DraftProvider` runs `applyLiturgyDefaults` after every change and whenever the profile's `default_benediction` changes. Checked on `4dfed3b`: `freshDraft` leaves the text `""` and nothing fills it; the profile the builder shell passes to `DraftProvider` already carries `default_benediction` (4a). This task:
- `freshDraft` fills the card from `church.default_benediction` ("Halverson" when an older API leaves it out), so a fresh draft is born with it; `DraftChurch` gains the optional field.
- `DraftStore` takes `liturgyDefaults` and runs `applyLiturgyDefaults` on load, on every `update`, `autoUpdate` and `replace`, and on an adopted draft (in memory). A stored draft the defaults change (one saved before 4b with an empty Benediction, or communion out of step with its date) is stamped 1 ms after the stored draft, like 2b's roll-forward; `setLiturgyDefaults` (a new default from a profile refetch) is an automatic change, stamped 1 ms after the current draft, so neither ever outranks another tab's edit (clarification 13).
- `DraftProvider` passes the profile's default and calls `setLiturgyDefaults` when it changes; `useDraft()` gains `peek()`, the latest draft now, for T6's code outside a render (clarification 14).

A fresh draft now prints the church default, so three existing tests change their expected values (0 new tests there): the provisional payload of a fresh draft holds `benediction: "Halverson"`, the fresh-draft shape test expects the text (and gains the empty-default and missing-field cases), and the liturgy status of a draft with one typed card is "2 of 7".

**Files:**
- Modify: `frontend/src/lib/draft/schema.ts` (`DraftChurch.default_benediction`, `freshDraft`), `frontend/src/lib/draft/store.ts` (`liturgyDefaults`, `setLiturgyDefaults`), `frontend/src/lib/draft/context.tsx` (the profile's default, `peek`)
- Test: `frontend/src/lib/draft/store.test.ts` (+2), `frontend/src/lib/draft/context.test.tsx` (+1); `mapping.test.ts`, `schema.test.ts`, `status.test.ts` (one test each edited, 0)

**Interfaces:**
- Consumes: `applyLiturgyDefaults`, `DEFAULT_BENEDICTION_FALLBACK`, `type LiturgyDefaults` (T2); `ChurchProfile.default_benediction` (4a).
- Produces: `type DraftChurch = {id; timezone?; timezone_valid?; default_benediction?: string}`; `new DraftStore({..., liturgyDefaults?: LiturgyDefaults})`, `store.setLiturgyDefaults(next)`; `DraftApi.peek: () => DraftV1`. Later users: T6 (`peek`), T8 (the Benediction card follows the default), every "New service" (its fresh draft carries the default).

Counts after this task: frontend **470 passed in 72 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "default_benediction" frontend/src/lib/draft/schema.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/context.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `frontend/src/lib/draft/schema.ts:0`, `frontend/src/lib/draft/store.ts:0`, `frontend/src/lib/draft/context.tsx:0`; ` Test Files  72 passed (72)`, `      Tests  467 passed (467)`.

- [ ] **Step 2 (agent): Write the failing tests and the new expected values**

**In `frontend/src/lib/draft/store.test.ts`, replace:**

```ts
import { corruptDraftKey, draftKey, type DraftV1 } from "./schema";
```

**with:**

```ts
import { corruptDraftKey, draftKey, freshDraft, type DraftV1 } from "./schema";
```

**In `frontend/src/lib/draft/store.test.ts`, replace:**

```ts

describe("DraftStore changes (S store.ts)", () => {
```

**with:**

```ts

describe("DraftStore and the liturgy defaults (slice 4 spec, Draft store integration)", () => {
  function defaultsStore(storage: DraftStorage, now = clock().now) {
    return new DraftStore({ userId: USER_ID, church: GRACE, storage, now, liturgyDefaults: { defaultBenediction: "Halverson" } });
  }

  it("fills a fresh draft's Benediction with the church default and follows a new default until the card is edited", () => {
    const { storage, data } = memoryStorage();
    const t = clock();
    const store = defaultsStore(storage, t.now);
    store.start();
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
    vi.advanceTimersByTime(WRITE_DELAY_MS);
    expect(stored(data).liturgy.cards.benediction.text).toBe("Halverson");

    // An admin changes the default (6a) and the profile refetches: an automatic change, 1 ms after the draft.
    const before = store.getSnapshot().draft.updated_at;
    t.advance(60_000);
    store.setLiturgyDefaults({ defaultBenediction: "The Lord bless you and keep you." });
    const followed = store.getSnapshot().draft;
    expect(followed.liturgy.cards.benediction.text).toBe("The Lord bless you and keep you.");
    expect(followed.updated_at).toBe(new Date(Date.parse(before) + 1).toISOString());
    store.setLiturgyDefaults({ defaultBenediction: "The Lord bless you and keep you." });
    expect(store.getSnapshot().draft).toBe(followed); // the same default: nothing to do

    // Every change keeps the defaults: New service's fresh draft gets the default too.
    store.update((d) => ({ ...d, liturgy: { ...d.liturgy, cards: { ...d.liturgy.cards, benediction: { enabled: true, text: "Go in peace.", origin: "typed" } } } }));
    store.setLiturgyDefaults({ defaultBenediction: "Halverson" });
    expect(store.getSnapshot().draft.liturgy.cards.benediction.text).toBe("Go in peace.");
    store.replace(freshDraft({ church: GRACE, user: { id: USER_ID }, now: t.now() }));
    expect(store.getSnapshot().draft.liturgy.cards.benediction).toEqual({ enabled: true, text: "Halverson", origin: "default" });
  });

  it("loads a stored draft with today's default and the date's communion, stamped just after the stored draft", () => {
    const old = testDraft((d) => ({
      ...d,
      updated_at: "2026-09-29T15:00:00.000Z",
      liturgy: { ...d.liturgy, include_communion: false }, // stored before 4b: the rule says on for October 4
    }));
    const { storage } = memoryStorage({ [KEY]: JSON.stringify(old) });
    const draft = defaultsStore(storage).getSnapshot().draft;
    expect(draft.liturgy.cards.benediction.text).toBe("Halverson");
    expect(draft.liturgy.include_communion).toBe(true);
    expect(draft.updated_at).toBe("2026-09-29T15:00:00.001Z");
    // Without defaults (slice 2's tests), the store changes nothing.
    expect(makeStore(memoryStorage({ [KEY]: JSON.stringify(old) }).storage).store.getSnapshot().draft).toEqual(old);
  });
});

describe("DraftStore changes (S store.ts)", () => {
```

**In `frontend/src/lib/draft/context.test.tsx`, replace:**

```tsx
        Rename
      </button>
```

**with:**

```tsx
        Rename
      </button>
    </div>
  );
}

/** The Benediction card and the latest draft `peek` returns, for the liturgy defaults (slice 4b). */
function BenedictionProbe() {
  const { draft, peek } = useDraft();
  return (
    <div>
      <p>Benediction: {draft.liturgy.cards.benediction.text || "empty"}</p>
      <button type="button" onClick={() => window.alert(peek().liturgy.cards.benediction.text)}>
        Peek
      </button>
```

**In `frontend/src/lib/draft/context.test.tsx`, replace:**

```tsx
    vi.restoreAllMocks();
  });
```

**with:**

```tsx
    vi.restoreAllMocks();
  });

  it("fills the Benediction from the church profile, follows a new default, and peek reads the latest draft (slice 4b)", () => {
    window.localStorage.setItem(KEY, JSON.stringify(testDraft()));
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    const view = render(
      <DraftProvider userId={USER_ID} church={churchProfile({ default_benediction: "Go in peace." })}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: Go in peace.")).toBeInTheDocument();
    view.rerender(
      <DraftProvider userId={USER_ID} church={churchProfile({ default_benediction: "" })}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: empty")).toBeInTheDocument();
    act(() => screen.getByRole("button", { name: "Peek" }).click());
    expect(alert).toHaveBeenCalledWith("");
    // An older API without the field: the fallback.
    view.rerender(
      <DraftProvider userId={USER_ID} church={{ id: GRACE.id, timezone: GRACE.timezone }}>
        <BenedictionProbe />
      </DraftProvider>,
    );
    expect(screen.getByText("Benediction: Halverson")).toBeInTheDocument();
  });
```

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

```ts
      liturgy: {},
```

**with:**

```ts
      liturgy: { benediction: "Halverson" }, // the church default (slice 4b)
```

**In `frontend/src/lib/draft/mapping.test.ts`, replace:**

```ts
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship." });
```

**with:**

```ts
    expect(payload.liturgy).toEqual({ call_to_worship: "Come, let us worship.", benediction: "Halverson" });
```

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

```ts
import { churchProfile, testDraft, USER_ID } from "@/test/fixtures";
```

**with:**

```ts
import { CHURCH_IDS, churchProfile, DRAFT_NOW, testDraft, USER_ID } from "@/test/fixtures";
```

**In `frontend/src/lib/draft/schema.test.ts`, replace:**

```ts
        text: "",
        origin: key === "benediction" ? "default" : "empty",
      });
    }
```

**with:**

```ts
        text: key === "benediction" ? "Halverson" : "", // the church default (slice 4b)
        origin: key === "benediction" ? "default" : "empty",
      });
    }
    const user = { id: USER_ID };
    const none = freshDraft({ church: churchProfile({ default_benediction: "" }), user, now: DRAFT_NOW });
    expect(none.liturgy.cards.benediction).toEqual({ enabled: true, text: "", origin: "default" });
    const older = freshDraft({ church: { id: CHURCH_IDS.grace, timezone: "America/New_York" }, user, now: DRAFT_NOW });
    expect(older.liturgy.cards.benediction.text).toBe("Halverson"); // an API without the field
```

**In `frontend/src/lib/draft/status.test.ts`, replace:**

```ts
      done: 1,
```

**with:**

```ts
      done: 2, // and the Benediction, following the church default (slice 4b)
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/draft 2>&1 | grep -E "^ FAIL|AssertionError|TestingLibraryElementError|Tests ")
```

**Expected:**

```
(pending replay)
```
- [ ] **Step 4 (agent): Fill the fresh draft, and run the defaults in the store and the provider**

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
```

**with:**

```ts
import { isFirstSundayOfMonth, isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";
import { DEFAULT_ENABLED } from "@/lib/liturgy/sections";
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
/** The profile fields `freshDraft` needs (`GET /church`, slice 2a). */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean };
```

**with:**

```ts
/**
 * The profile fields the draft needs (`GET /church`): the zone for
 * `freshDraft` (slice 2a) and the church's default benediction, which an
 * untouched Benediction card shows (slice 4a; an older API leaves it out).
 */
export type DraftChurch = { id: string; timezone?: string | null; timezone_valid?: boolean; default_benediction?: string };
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
 * Prayers of the People, the benediction card `default`-origin (slice 4 fills
 * its text), communion on for a first Sunday, a new save key, on step 1.
```

**with:**

```ts
 * Prayers of the People, the benediction card `default`-origin with the
 * church's default benediction ("Halverson" when the profile has none; slice
 * 4b), communion on for a first Sunday, a new save key, on step 1.
```

**In `frontend/src/lib/draft/schema.ts`, replace:**

```ts
      { enabled: DEFAULT_ENABLED[key], text: "", origin: key === "benediction" ? "default" : "empty" },
```

**with:**

```ts
      key === "benediction"
        ? { enabled: DEFAULT_ENABLED[key], text: church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK, origin: "default" }
        : { enabled: DEFAULT_ENABLED[key], text: "", origin: "empty" },
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
 * - A failed write switches to memory-only with one "memory_only" notice and
```

**with:**

```ts
 *   never bumps `updated_at`. `replace(next)` stores `normalizePicks(next)`.
 * - Liturgy defaults (slice 4b; slice 4 spec "Draft store integration"): with
 *   `liturgyDefaults`, every load, change and replace also runs
 *   `applyLiturgyDefaults`, so an untouched Benediction shows the church's
 *   default and untouched communion follows the date. A load it changes is
 *   stamped 1 ms after the stored draft, and `setLiturgyDefaults` (the
 *   profile refetched with a new default) is an automatic change, so neither
 *   outranks another tab's edit. An adopted draft gets the defaults in memory.
 * - A failed write switches to memory-only with one "memory_only" notice and
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
import { isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { readLocal, removeLocal, tryWriteLocal } from "@/lib/storage";
```

**with:**

```ts
import { isValidDateIso, nextSunday, todayIn } from "@/lib/dates";
import { applyLiturgyDefaults, type LiturgyDefaults } from "@/lib/liturgy/defaults";
import { readLocal, removeLocal, tryWriteLocal } from "@/lib/storage";
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
  notify?: (notice: DraftNotice) => void;
};
```

**with:**

```ts
  notify?: (notice: DraftNotice) => void;
  /** The church's liturgy defaults; without them (slice 2's tests) the store changes no card. */
  liturgyDefaults?: LiturgyDefaults;
};
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts

  constructor({ userId, church, storage = browserDraftStorage, now = () => new Date(), notify = () => {} }: DraftStoreOptions) {
```

**with:**

```ts
  private defaults: LiturgyDefaults | null;

  constructor({
    userId,
    church,
    storage = browserDraftStorage,
    now = () => new Date(),
    notify = () => {},
    liturgyDefaults,
  }: DraftStoreOptions) {
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    this.notify = notify;

```

**with:**

```ts
    this.notify = notify;
    this.defaults = liturgyDefaults ?? null;

```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    const rolled = rollForward(draft, todayIn(churchZone(church), now()));
```

**with:**

```ts
    const rolled = this.withDefaults(rollForward(draft, todayIn(churchZone(church), now())));
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    const next = recipe(this.snapshot.draft);
```

**with:**

```ts
    const next = this.withDefaults(recipe(this.snapshot.draft));
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    const next = recipe(current);
```

**with:**

```ts
    const next = this.withDefaults(recipe(current));
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    this.set(normalizePicks({ ...next, updated_at: this.now().toISOString() }));
    this.schedule();
```

**with:**

```ts
    this.set(this.withDefaults(normalizePicks({ ...next, updated_at: this.now().toISOString() })));
    this.schedule();
  };

  /** The church's defaults changed (a profile refetch): an automatic change for a card still following them. */
  setLiturgyDefaults = (next: LiturgyDefaults): void => {
    if (this.defaults?.defaultBenediction === next.defaultBenediction) return;
    this.defaults = next;
    this.autoUpdate((d) => d);
```

**In `frontend/src/lib/draft/store.ts`, replace:**

```ts
    this.set(normalizePicks(stored));
    this.notify("adopted");
    return true;
```

**with:**

```ts
    this.set(this.withDefaults(normalizePicks(stored)));
    this.notify("adopted");
    return true;
  }

  private withDefaults(d: DraftV1): DraftV1 {
    return this.defaults === null ? d : applyLiturgyDefaults(d, this.defaults);
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx

import type { DraftChurch, DraftV1, StepId } from "./schema";
```

**with:**

```tsx

import { DEFAULT_BENEDICTION_FALLBACK } from "@/lib/liturgy/defaults";

import type { DraftChurch, DraftV1, StepId } from "./schema";
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx
  setLastStep: (step: StepId) => void;
  persistence: Persistence;
```

**with:**

```tsx
  setLastStep: (step: StepId) => void;
  /** The latest draft now, for code that runs outside a render (slice 4b's generation provider). */
  peek: () => DraftV1;
  persistence: Persistence;
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx
  const [store] = useState(() => new DraftStore({ userId, church, notify }));
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
```

**with:**

```tsx
  const defaultBenediction = church.default_benediction ?? DEFAULT_BENEDICTION_FALLBACK;
  const [store] = useState(
    () => new DraftStore({ userId, church, notify, liturgyDefaults: { defaultBenediction } }),
  );
  const snapshot = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);

  // The profile refetched with another default (6a's Settings): untouched Benediction cards follow it.
  useEffect(() => {
    store.setLiturgyDefaults({ defaultBenediction });
  }, [store, defaultBenediction]);
```

**In `frontend/src/lib/draft/context.tsx`, replace:**

```tsx
      setLastStep: store.setLastStep,
    }),
```

**with:**

```tsx
      setLastStep: store.setLastStep,
      peek: () => store.getSnapshot().draft,
    }),
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/draft 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  9 passed (9)`, `      Tests  59 passed (59)`; the suite ` Test Files  72 passed (72)`, `      Tests  470 passed (470)` (the builder, Hymns and Date & readings tests pass unchanged: their seeded drafts carry the default already); `typecheck 0` and `lint 0`; ` M` for the eight files named in **Files:**.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/draft/schema.ts frontend/src/lib/draft/store.ts frontend/src/lib/draft/context.tsx frontend/src/lib/draft/store.test.ts frontend/src/lib/draft/context.test.tsx frontend/src/lib/draft/mapping.test.ts frontend/src/lib/draft/schema.test.ts frontend/src/lib/draft/status.test.ts
git commit -m "Draft: the Benediction follows the church's default until it is changed (S Draft store integration)" -m "freshDraft fills the Benediction from the profile's default_benediction
(Halverson when the API leaves it out). The draft store runs
applyLiturgyDefaults on load, on every change and on replace; a load it
changes is stamped 1 ms after the stored draft, and a new default from a
profile refetch is an automatic change, so neither outranks another
tab's edit. DraftProvider passes the default and useDraft gains peek().
Frontend 467 -> 470 tests in 72 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 8 files changed.

### Task 6: The generation provider in the builder shell (S Frontend `generation.tsx`, UX "Generate and Regenerate" steps 0-7, "Sermon text", BC-13, BC-21; F §1.8; clarifications 15, 16, 17, 18)

`LiturgyGenerationProvider` holds the Liturgy step's AI runs, card errors and Undo in memory, and the builder shell mounts it inside `DraftProvider`, so a run started on the Liturgy step keeps going on the other steps and its result lands in the draft (BC-21). Leaving `/builder`, switching church (the keyed remount) or signing out unmounts it, which cancels everything. It sends nothing while it is idle, so the shell's other tests need no new route.

What it does, in S's order:
- **Step 0.** With `aiAvailable: false`, `generate()` sends nothing and marks each targeted switched-on empty card with `localAiNotConfigured()`.
- **Steps 1-3.** Each key is queued; the batch first reads the sermon text once (`sermonSource`, then `queryClient.fetchQuery(passageQuery(...))`, bounded at 10 s; a failure, a timeout or no text sends the batch without it, with no toast), then each section is one request through the 3-at-a-time queue. A card already running is not queued twice.
- **Step 4.** `cancel(keys)` and the AI bar's `cancelBulk()` drop the cards' runs (waiting for the sermon text, queued or writing); the cards return to where they were, silently.
- **Step 6.** When a request starts, the card is captured (`captureCard`); when the answer arrives, `staleVerdict` decides inside the draft update: "apply" writes the text with origin "ai" and keeps the previous `{text, origin}` for Undo when it replaced text; "service_changed" and "edited" drop it with S's toasts ("The service changed, so the AI draft for {Label} was discarded." and "Kept your edits — the new AI draft for {Label} was not used.").
- **Step 7.** A 429 stops the queue: that card and every card still waiting show "Too many requests — try again in N s.".
- **Errors.** A section's error or a failed request becomes the card's error (`cardErrorFrom`); a 401 or a lost church goes to `reportAuthErrors` and shows nothing on the card.
- **Bulk.** A "Generate empty sections" run ends with one toast, "Wrote n sections." ("Wrote 1 section." for one; clarification 16) or "Wrote k of n sections. The rest show what went wrong."; cancelled cards are not counted, and a run cancelled whole shows none (clarification 15).
- The provider takes `sermonWaitMs` so a test can shorten the 10 s wait (clarification 17), and the Undo lines, errors and runs are exposed for T8-T10 (`runs`, `errors`, `undo`, `bulk`, `generate`, `cancel`, `cancelBulk`, `dismissError`, `setUndo`, `clearUndo`, `applyUndo`; clarification 18).

The provider's own tests are S's `generation.test.tsx` cases (the sermon text); T9's step tests cover Generate, Regenerate, errors, the stale rule, navigation and the 429 through the screen.

**Files:**
- Create: `frontend/src/lib/liturgy/generation.tsx`
- Modify: `frontend/src/components/builder/builder-shell.tsx` (mounts the provider)
- Test: `frontend/src/lib/liturgy/generation.test.tsx` (new, 3)

**Interfaces:**
- Consumes: `useDraft().update`, `peek` (T5); `captureCard`, `staleVerdict`, `applyGenerated`, `restoreCard` (T2); `buildGenerateRequest`, `sermonSource`, `sermonText`, `cardErrorFrom`, `localAiNotConfigured`, `createTaskQueue` (T3); `generateSection`, `passageQuery`, `reportAuthErrors`, `useApi` (T4); `SECTION_LABELS` (T1); sonner's `toast.message`.
- Produces: `LiturgyGenerationProvider({church: {id, effective_translation}, sermonWaitMs?, children})`, `useLiturgyGeneration(): LiturgyGeneration`, `MAX_IN_FLIGHT = 3`, `SERMON_WAIT_MS = 10_000`, `type CardRun = {phase: "queued" | "writing", since}`, `type UndoEntry = {kind: "replaced" | "cleared", previous}`, `type BulkRun = {total, done}`. Later users: T8-T10 (the step), T11 (`LiturgySummaryBlock` reads `runs`).

Counts after this task: frontend **473 passed in 73 files**.

- [ ] **Step 1 (agent): Check the starting point**

```bash
git status --short
grep -c "LiturgyGenerationProvider" frontend/src/components/builder/builder-shell.tsx
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
```

**Expected:** nothing (or `?? .claude/`); `0` (grep exits 1); ` Test Files  72 passed (72)`, `      Tests  470 passed (470)`.

- [ ] **Step 2 (agent): Write the failing tests**

**Create `frontend/src/lib/liturgy/generation.test.tsx`:**

```tsx
/**
 * The generation provider's sermon text (slice 4 spec, "Sermon text";
 * Testing `generation.test.tsx`, amendment 2026-09-26): a batch reads the
 * passage once and every request carries it; a fetch that fails or takes too
 * long still sends the batch, without it and with no toast; Cancel during the
 * wait sends nothing. The step's own tests (T9) cover the rest of the flow.
 */
import { act, screen } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/sonner";
import type { GenerateLiturgyBody } from "@/lib/api/types";
import { DraftProvider, useDraft } from "@/lib/draft/context";
import { editScriptureLines } from "@/lib/draft/readings";
import { draftKey, type SectionKey } from "@/lib/draft/schema";
import { fakeError, installFakeApi, type FakeHandler, type RecordedRequest } from "@/test/fake-api";
import { church, churchProfile, DRAFT_NOW, generateRoute, me, testDraft, USER_ID } from "@/test/fixtures";
import { renderWithProviders } from "@/test/render";

import { LiturgyGenerationProvider, MAX_IN_FLIGHT, SERMON_WAIT_MS, useLiturgyGeneration, type LiturgyGeneration } from "./generation";

const KEY = draftKey(USER_ID, church().id);
const FOUR: SectionKey[] = ["call_to_worship", "opening_prayer", "prayer_of_confession", "assurance"];
const PHILIPPIANS = {
  reference: "Philippians 3:4b-14",
  status: "ok",
  sections: [{ reference: "Philippians 3:4b-14", status: "ok", text: "I press on toward the goal." }],
};

/** The provider's latest value, for the test to call (set after each render). */
const handle: { current: LiturgyGeneration | null } = { current: null };
const generation = {
  generate: (...args: Parameters<LiturgyGeneration["generate"]>) => handle.current?.generate(...args),
  cancel: (...args: Parameters<LiturgyGeneration["cancel"]>) => handle.current?.cancel(...args),
};

function Probe() {
  const g = useLiturgyGeneration();
  useEffect(() => {
    handle.current = g;
  });
  const { draft } = useDraft();
  return (
    <ul>
      {FOUR.map((key) => (
        <li key={key}>
          {key}: {draft.liturgy.cards[key].text || "empty"} / {g.runs[key]?.phase ?? "idle"}
        </li>
      ))}
    </ul>
  );
}

/** Pat's draft with October 4's readings (the NT reading is Philippians), in the providers the shell mounts. */
function renderProvider(routes: Record<string, FakeHandler>, sermonWaitMs?: number) {
  window.localStorage.setItem(
    KEY,
    JSON.stringify(editScriptureLines(testDraft(), "Isaiah 5:1-7\nPsalm 80:7-15\nPhilippians 3:4b-14\nMatthew 21:33-46")),
  );
  const api = installFakeApi(routes);
  const profile = churchProfile();
  renderWithProviders(
    <>
      <DraftProvider userId={USER_ID} church={profile}>
        <LiturgyGenerationProvider church={profile} sermonWaitMs={sermonWaitMs}>
          <Probe />
        </LiturgyGenerationProvider>
      </DraftProvider>
      <Toaster />
    </>,
    { me: me(), church: church() },
  );
  return api;
}

const generateCalls = (requests: RecordedRequest[]) => requests.filter((r) => r.path === "/liturgy/generate");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(DRAFT_NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("the sermon text (S Sermon text)", () => {
  it("reads the passage once for a batch of 4, then sends 4 requests with the same sermon_text, 3 at a time", async () => {
    let open = 0;
    let most = 0;
    const api = renderProvider({
      "POST /scripture/passages": { passages: [PHILIPPIANS] },
      "POST /liturgy/generate": generateRoute(async (section) => {
        open += 1;
        most = Math.max(most, open);
        await new Promise((resolve) => setTimeout(resolve, 20));
        open -= 1;
        return { section, status: "generated", text: `${section} text`, error: null };
      }),
    });
    act(() => generation.generate(FOUR, { aiAvailable: true, bulk: true }));
    for (const key of FOUR) expect(await screen.findByText(`${key}: ${key} text / idle`)).toBeInTheDocument();
    expect(api.requests.filter((r) => r.path === "/scripture/passages")).toHaveLength(1);
    expect(api.requests.find((r) => r.path === "/scripture/passages")?.body).toEqual({ refs: ["Philippians 3:4b-14"], translation: "web" });
    const calls = generateCalls(api.requests);
    expect(calls.map((r) => (r.body as GenerateLiturgyBody).sections)).toEqual(FOUR.map((key) => [key]));
    for (const call of calls) {
      expect((call.body as GenerateLiturgyBody).sermon_text).toEqual({ ref: "Philippians 3:4b-14", text: "I press on toward the goal." });
    }
    expect(most).toBeLessThanOrEqual(MAX_IN_FLIGHT);
    expect(await screen.findByText("Wrote 4 sections.")).toBeInTheDocument();
  });

  it("sends the batch without sermon_text, and no toast about it, when the passage fails or takes too long", async () => {
    expect(SERMON_WAIT_MS).toBe(10_000);
    const failing = renderProvider({
      "POST /scripture/passages": fakeError(500, "internal_error", "Something went wrong."),
      "POST /liturgy/generate": generateRoute(),
    });
    act(() => generation.generate(["call_to_worship"], { aiAvailable: true }));
    expect(await screen.findByText("call_to_worship: Call to Worship written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(failing.requests)[0].body).not.toHaveProperty("sermon_text");
    expect(screen.queryByText(/Something went wrong/)).toBeNull();
  });

  it("goes without the sermon text once the wait passes (shortened here), and Cancel during the wait sends nothing", async () => {
    const never = new Promise<never>(() => {});
    const api = renderProvider(
      { "POST /scripture/passages": () => never, "POST /liturgy/generate": generateRoute() },
      50,
    );
    act(() => generation.generate(["opening_prayer"], { aiAvailable: true }));
    expect(screen.getByText("opening_prayer: empty / queued")).toBeInTheDocument();
    expect(await screen.findByText("opening_prayer: Opening Prayer written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests)[0].body).not.toHaveProperty("sermon_text");

    act(() => generation.generate(["assurance"], { aiAvailable: true }));
    expect(screen.getByText("assurance: empty / queued")).toBeInTheDocument();
    act(() => generation.cancel(["assurance"]));
    expect(screen.getByText("assurance: empty / idle")).toBeInTheDocument();
    // A later batch waits as long, so once its answer is in, the cancelled one would have been sent.
    act(() => generation.generate(["prayer_of_confession"], { aiAvailable: true }));
    expect(await screen.findByText("prayer_of_confession: Prayer of Confession written by the AI. / idle")).toBeInTheDocument();
    expect(generateCalls(api.requests).map((r) => (r.body as GenerateLiturgyBody).sections)).toEqual([
      ["opening_prayer"],
      ["prayer_of_confession"],
    ]);
    expect(screen.getByText("assurance: empty / idle")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3 (agent): Run them and see them fail**

```bash
(cd frontend && npx vitest run src/lib/liturgy/generation.test.tsx 2>&1 | grep -E "^ FAIL|Error: Failed|Tests ")
```

**Expected:**

```
(pending replay)
```
- [ ] **Step 4 (agent): Write the provider and mount it in the shell**

**Create `frontend/src/lib/liturgy/generation.tsx`:**

```tsx
"use client";

/**
 * `LiturgyGenerationProvider` and `useLiturgyGeneration()` (slice 4 spec,
 * Frontend `generation.tsx`; UX "Generate and Regenerate"). Mounted in the
 * builder shell inside the draft provider, so a run keeps going while the
 * member moves between steps and its result lands in the draft; leaving
 * `/builder`, switching church (the keyed remount) or signing out unmounts it
 * and cancels everything.
 *
 * - Runs, card errors and Undo live here, in memory, never in the draft
 *   (owner answer 1, 2026-09-30: none of them is unsaved work).
 * - `generate(keys, {aiAvailable, bulk})`: with AI off it sends nothing and
 *   marks each switched-on empty card "AI not configured" (S step 0).
 *   Otherwise every key is queued; the batch first reads the sermon text once
 *   (the effective NT reading, WEB for ESV, `queryClient.fetchQuery` through
 *   `passageQuery`, at most 10 s; a failure or a timeout just leaves it out),
 *   then each section is one request, at most 3 in flight.
 * - When a request starts the card is captured (`captureCard`); when its
 *   answer arrives `staleVerdict` decides, inside the draft update, whether it
 *   applies ("apply": the text, origin "ai", Undo when it replaced text) or
 *   is dropped with S's toast.
 * - A 429 stops the queue: that card and every queued one show the retry
 *   message. A 401 or a lost church goes to the app's handling
 *   (`reportAuthErrors`) and shows nothing on the card.
 * - A bulk run ends with one toast: "Wrote n sections." or "Wrote k of n
 *   sections. The rest show what went wrong." (cancelled cards not counted).
 */
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { toast } from "sonner";

import { ApiError } from "@/lib/api/client";
import { isNoChurchAccess } from "@/lib/api/errors";
import type { ChurchProfile, SectionResult, SermonText } from "@/lib/api/types";
import { useDraft } from "@/lib/draft/context";
import type { SectionKey } from "@/lib/draft/schema";
import { reportAuthErrors, useApi } from "@/lib/queries/client";
import { generateSection } from "@/lib/queries/liturgy";
import { passageQuery } from "@/lib/queries/passages";

import {
  applyGenerated,
  captureCard,
  restoreCard,
  staleVerdict,
  type CapturedCard,
  type CardSnapshot,
  type StaleVerdict,
} from "./cards";
import { cardErrorFrom, localAiNotConfigured, type CardError } from "./errors";
import { createTaskQueue, type TaskOutcome } from "./queue";
import { buildGenerateRequest, sermonSource, sermonText } from "./request";
import { SECTION_LABELS } from "./sections";

/** At most 3 requests in flight, leaving one of the server's 4 AI slots free (S step 3). */
export const MAX_IN_FLIGHT = 3;
/** How long a batch waits for the sermon text before going without it (S "Sermon text"). */
export const SERMON_WAIT_MS = 10_000;

export type CardRun = { phase: "queued" | "writing"; since: number };
export type UndoEntry = { kind: "replaced" | "cleared"; previous: CardSnapshot };
export type BulkRun = { total: number; done: number };

export type LiturgyGeneration = {
  runs: Partial<Record<SectionKey, CardRun>>;
  errors: Partial<Record<SectionKey, CardError>>;
  undo: Partial<Record<SectionKey, UndoEntry>>;
  /** "Generate empty sections" while it runs. */
  bulk: BulkRun | null;
  generate: (keys: SectionKey[], opts: { aiAvailable: boolean; bulk?: boolean }) => void;
  /** Cancels these cards' runs (every run when omitted); the cards return to where they were. */
  cancel: (keys?: SectionKey[]) => void;
  /** The AI bar's Cancel: the whole bulk run. */
  cancelBulk: () => void;
  dismissError: (key: SectionKey) => void;
  setUndo: (key: SectionKey, entry: UndoEntry | null) => void;
  clearUndo: () => void;
  applyUndo: (key: SectionKey) => void;
};

const GenerationContext = createContext<LiturgyGeneration | null>(null);

type Bulk = { keys: Set<SectionKey>; total: number; done: number; written: number };

function without<T>(record: Partial<Record<SectionKey, T>>, keys: readonly SectionKey[]): Partial<Record<SectionKey, T>> {
  if (!keys.some((key) => key in record)) return record;
  const next = { ...record };
  for (const key of keys) delete next[key];
  return next;
}

function bulkToast(written: number, done: number): void {
  if (done === 0) return;
  if (written === done) toast.message(done === 1 ? "Wrote 1 section." : `Wrote ${done} sections.`);
  else toast.message(`Wrote ${written} of ${done} sections. The rest show what went wrong.`);
}

export function LiturgyGenerationProvider({
  church,
  sermonWaitMs = SERMON_WAIT_MS,
  children,
}: {
  church: Pick<ChurchProfile, "id" | "effective_translation">;
  /** Tests shorten the sermon-text wait. */
  sermonWaitMs?: number;
  children: ReactNode;
}) {
  const { update, peek } = useDraft();
  const api = useApi();
  const queryClient = useQueryClient();
  const [queue] = useState(() => createTaskQueue({ concurrency: MAX_IN_FLIGHT }));
  const [runs, setRuns] = useState<Partial<Record<SectionKey, CardRun>>>({});
  const [errors, setErrors] = useState<Partial<Record<SectionKey, CardError>>>({});
  const [undo, setUndoState] = useState<Partial<Record<SectionKey, UndoEntry>>>({});
  const [bulk, setBulk] = useState<BulkRun | null>(null);
  const mounted = useRef(true);
  /** Cards waiting for their batch's sermon text: key → batch id. */
  const pending = useRef(new Map<SectionKey, number>());
  /** Each batch's sermon-text wait, aborted when all of its cards are cancelled. */
  const batches = useRef(new Map<number, AbortController>());
  const captured = useRef(new Map<SectionKey, CapturedCard>());
  const bulkRef = useRef<Bulk | null>(null);
  const batchSeq = useRef(0);

  useEffect(() => {
    mounted.current = true;
    const waits = batches.current;
    return () => {
      mounted.current = false;
      queue.cancelAll();
      for (const controller of waits.values()) controller.abort();
    };
  }, [queue]);

  const setError = useCallback((key: SectionKey, error: CardError | null) => {
    setErrors((current) => (error === null ? without(current, [key]) : { ...current, [key]: error }));
  }, []);

  const setUndo = useCallback((key: SectionKey, entry: UndoEntry | null) => {
    setUndoState((current) => (entry === null ? without(current, [key]) : { ...current, [key]: entry }));
  }, []);

  /** A card left the bulk run: settled (counted, `wrote` when applied) or cancelled (not counted). */
  const leaveBulk = useCallback((key: SectionKey, how: "wrote" | "failed" | "cancelled") => {
    const b = bulkRef.current;
    if (b === null || !b.keys.has(key)) return;
    b.keys.delete(key);
    if (how === "cancelled") b.total -= 1;
    else b.done += 1;
    if (how === "wrote") b.written += 1;
    if (b.keys.size === 0) {
      bulkRef.current = null;
      setBulk(null);
      bulkToast(b.written, b.done);
    } else {
      setBulk({ total: b.total, done: b.done });
    }
  }, []);

  /** Drops a card's run: waiting for the sermon text, queued or writing. */
  const dropRun = useCallback(
    (key: SectionKey) => {
      const batch = pending.current.get(key);
      pending.current.delete(key);
      if (batch !== undefined && ![...pending.current.values()].includes(batch)) {
        batches.current.get(batch)?.abort();
        batches.current.delete(batch);
      }
      queue.cancel(key);
      captured.current.delete(key);
    },
    [queue],
  );

  const applyResult = useCallback(
    (key: SectionKey, text: string): boolean => {
      const cap = captured.current.get(key);
      captured.current.delete(key);
      if (!cap) return false;
      const out: { verdict: StaleVerdict; previous: CardSnapshot | null } = { verdict: "apply", previous: null };
      update((d) => {
        out.verdict = staleVerdict(d, key, cap);
        if (out.verdict !== "apply") return d;
        const card = d.liturgy.cards[key];
        out.previous = { text: card.text, origin: card.origin };
        return applyGenerated(d, key, text);
      });
      const label = SECTION_LABELS[key];
      if (out.verdict === "service_changed") {
        toast.message(`The service changed, so the AI draft for ${label} was discarded.`);
      } else if (out.verdict === "edited") {
        toast.message(`Kept your edits — the new AI draft for ${label} was not used.`);
      } else if (out.previous !== null && out.previous.text.trim() !== "") {
        setUndo(key, { kind: "replaced", previous: out.previous });
      }
      return out.verdict === "apply";
    },
    [update, setUndo],
  );

  const settle = useCallback(
    (key: SectionKey, outcome: TaskOutcome<SectionResult>) => {
      if (!mounted.current) return;
      setRuns((current) => without(current, [key]));
      if (outcome.ok) {
        const result = outcome.value;
        if (result.status !== "error" && result.text !== null) {
          leaveBulk(key, applyResult(key, result.text) ? "wrote" : "failed");
          return;
        }
        captured.current.delete(key);
        setError(key, result.error ? cardErrorFrom(result.error) : cardErrorFrom(new Error("no text")));
        leaveBulk(key, "failed");
        return;
      }
      captured.current.delete(key);
      const e = outcome.error;
      if (e instanceof ApiError && (e.status === 401 || isNoChurchAccess(e))) reportAuthErrors(e, church.id);
      const error = cardErrorFrom(e);
      setError(key, error);
      leaveBulk(key, error === null ? "cancelled" : "failed");
      if (e instanceof ApiError && e.code === "rate_limited") {
        // S step 7: the whole queue stops, and every card still waiting shows the same message.
        const waiting = [...queue.waitingKeys(), ...pending.current.keys()] as SectionKey[];
        for (const other of waiting) {
          dropRun(other);
          setError(other, error);
          leaveBulk(other, "failed");
        }
        setRuns((current) => without(current, waiting));
      }
    },
    [applyResult, church.id, dropRun, leaveBulk, queue, setError],
  );

  const loadSermon = useCallback(
    (signal: AbortSignal): Promise<SermonText | null> => {
      const source = sermonSource(peek(), church.effective_translation);
      if (source === null) return Promise.resolve(null);
      return new Promise((resolve) => {
        const done = (value: SermonText | null) => {
          clearTimeout(timer);
          signal.removeEventListener("abort", onAbort);
          resolve(value);
        };
        const onAbort = () => done(null);
        const timer = setTimeout(() => done(null), sermonWaitMs);
        signal.addEventListener("abort", onAbort, { once: true });
        queryClient.fetchQuery(passageQuery(api, source.translation, source.ref)).then(
          (passage) => done(sermonText(source.ref, passage)),
          () => done(null),
        );
      });
    },
    [api, church.effective_translation, peek, queryClient, sermonWaitMs],
  );

  const send = useCallback(
    (key: SectionKey, sermon: SermonText | null) => {
      queue.push(
        key,
        (signal) => {
          const draft = peek();
          captured.current.set(key, captureCard(draft, key));
          setRuns((current) => ({ ...current, [key]: { phase: "writing", since: Date.now() } }));
          return generateSection(api.church, key, buildGenerateRequest(draft, key, sermon), signal);
        },
        (outcome) => settle(key, outcome),
      );
    },
    [api, peek, queue, settle],
  );

  const generate = useCallback(
    (keys: SectionKey[], { aiAvailable, bulk: isBulk = false }: { aiAvailable: boolean; bulk?: boolean }) => {
      const draft = peek();
      if (!aiAvailable) {
        // S step 0: nothing is sent; each targeted switched-on empty card says so.
        const empty = keys.filter((key) => {
          const card = draft.liturgy.cards[key];
          return card.enabled && card.text.trim() === "";
        });
        setErrors((current) => ({ ...current, ...Object.fromEntries(empty.map((key) => [key, localAiNotConfigured()])) }));
        return;
      }
      const busy = new Set<SectionKey>([...pending.current.keys(), ...(queue.runningKeys() as SectionKey[]), ...(queue.waitingKeys() as SectionKey[])]);
      const fresh = keys.filter((key) => !busy.has(key));
      if (fresh.length === 0) return;
      const since = Date.now();
      setErrors((current) => without(current, fresh));
      setRuns((current) => ({ ...current, ...Object.fromEntries(fresh.map((key) => [key, { phase: "queued", since }])) }));
      if (isBulk) {
        bulkRef.current = { keys: new Set(fresh), total: fresh.length, done: 0, written: 0 };
        setBulk({ total: fresh.length, done: 0 });
      }
      const batch = ++batchSeq.current;
      const controller = new AbortController();
      batches.current.set(batch, controller);
      for (const key of fresh) pending.current.set(key, batch);
      void loadSermon(controller.signal).then((sermon) => {
        batches.current.delete(batch);
        if (!mounted.current) return;
        for (const key of fresh) {
          if (pending.current.get(key) !== batch) continue; // cancelled while waiting
          pending.current.delete(key);
          send(key, sermon);
        }
      });
    },
    [loadSermon, peek, queue, send],
  );

  const cancel = useCallback(
    (keys?: SectionKey[]) => {
      const targets =
        keys ?? ([...pending.current.keys(), ...queue.runningKeys(), ...queue.waitingKeys()] as SectionKey[]);
      for (const key of targets) {
        dropRun(key);
        leaveBulk(key, "cancelled");
      }
      setRuns((current) => without(current, targets));
    },
    [dropRun, leaveBulk, queue],
  );

  const cancelBulk = useCallback(() => {
    const b = bulkRef.current;
    if (b) cancel([...b.keys]);
  }, [cancel]);

  const dismissError = useCallback((key: SectionKey) => setError(key, null), [setError]);
  const clearUndo = useCallback(() => setUndoState({}), []);
  const applyUndo = useCallback(
    (key: SectionKey) => {
      const entry = undo[key];
      if (!entry) return;
      update((d) => restoreCard(d, key, entry.previous));
      setUndo(key, null);
    },
    [undo, update, setUndo],
  );

  const value = useMemo<LiturgyGeneration>(
    () => ({ runs, errors, undo, bulk, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo }),
    [runs, errors, undo, bulk, generate, cancel, cancelBulk, dismissError, setUndo, clearUndo, applyUndo],
  );
  return <GenerationContext value={value}>{children}</GenerationContext>;
}

/** The generation state and actions. Throws outside `LiturgyGenerationProvider` (the builder shell mounts it). */
export function useLiturgyGeneration(): LiturgyGeneration {
  const value = useContext(GenerationContext);
  if (!value) throw new Error("useLiturgyGeneration() must be used inside <LiturgyGenerationProvider>.");
  return value;
}
```

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

```tsx
 * every step (slice 2c).
```

**with:**

```tsx
 * every step (slice 2c). `<LiturgyGenerationProvider>` holds the Liturgy
 * step's AI runs, so they keep going on the other steps (slice 4b).
```

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

```tsx
import { stepFromPath } from "@/lib/draft/steps";
import { useMeContext } from "@/lib/me-context";
```

**with:**

```tsx
import { stepFromPath } from "@/lib/draft/steps";
import { LiturgyGenerationProvider } from "@/lib/liturgy/generation";
import { useMeContext } from "@/lib/me-context";
```

**In `frontend/src/components/builder/builder-shell.tsx`, replace:**

```tsx
      <LectionarySync>
        <BuilderFrame church={profile.data}>{children}</BuilderFrame>
      </LectionarySync>
```

**with:**

```tsx
      <LiturgyGenerationProvider church={profile.data}>
        <LectionarySync>
          <BuilderFrame church={profile.data}>{children}</BuilderFrame>
        </LectionarySync>
      </LiturgyGenerationProvider>
```

- [ ] **Step 5 (agent): Run the tests, the suite, types and lint**

```bash
(cd frontend && npx vitest run src/lib/liturgy/generation.test.tsx src/components/builder 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm test 2>&1 | grep -E "Test Files|Tests ")
(cd frontend && npm run typecheck >/dev/null 2>&1; echo "typecheck $?"; npm run lint >/dev/null 2>&1; echo "lint $?")
git status --short
```

**Expected:** ` Test Files  7 passed (7)`, `      Tests  95 passed (95)` (the shell, Hymns and Date & readings tests pass with the provider mounted, sending nothing); the suite ` Test Files  73 passed (73)`, `      Tests  473 passed (473)`; `typecheck 0` and `lint 0`; ` M frontend/src/components/builder/builder-shell.tsx` and the two new files as `??`.

- [ ] **Step 6 (agent): Commit**

```bash
git add frontend/src/lib/liturgy/generation.tsx frontend/src/lib/liturgy/generation.test.tsx frontend/src/components/builder/builder-shell.tsx
git commit -m "Liturgy: the generation provider, mounted in the builder shell (S generation.tsx; BC-13, BC-21)" -m "Runs, card errors and Undo live in memory in LiturgyGenerationProvider,
inside the builder shell, so a run keeps going on other steps and lands in
the draft. Without AI it sends nothing and marks empty cards. A batch
reads the sermon text once (WEB for ESV, at most 10 s, left out on
failure), then sends one section per request, 3 at a time; a result is
applied or dropped by the stale rule with its toast; a 429 stops the
queue; a bulk run ends with one toast. Unmounting cancels everything.
Frontend 470 -> 473 tests in 72 -> 73 files." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LhHxTA5m6dKphy5MuKjHCS"
```

**Expected:** one commit, 3 files changed.

**Review checkpoint (T3-T6, batch B):** the request never sends `overrides` or ESV text; the timeout row is 100 000; the fixtures match 4a's shared files; the store's defaults never outrank another tab's edit; the provider sends nothing while idle, never delivers a cancelled result, and applies S step 6 inside the update; counts match.
